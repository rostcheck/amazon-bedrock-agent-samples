import uuid
from textwrap import dedent
from typing import Optional, List
import boto3
from botocore.exceptions import ClientError
from .event_stream_processor import EventStreamProcessor, StandardEventProcessor
from src.utils.bedrock_agent_helper import AgentsForAmazonBedrock
from .output_formatter import OutputFormatter, BasicOutputFormatter
from ..tool import Tool
from .task import Task
from ..knowledge_base import KnowledgeBase
import time

MAX_DESCR_SIZE = 200  # Due to max size enforced by Agents for description

agent_foundation_models = [
    "us.anthropic.claude-3-haiku-20240307-v1:0",
    "us.anthropic.claude-3-sonnet-20240307-v1:0",
    "us.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "us.anthropic.claude-3-5-haiku-20241022-v1:0",
    "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
]

DEFAULT_AGENT_MODEL = "us.anthropic.claude-3-5-sonnet-20240620-v1:0"
DEFAULT_SUPERVISOR_MODEL = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"


class Agent:
    """Represents a Bedrock Agent with associated tools and knowledge bases."""

    class Status:
        NOT_PREPARED = "NOT_PREPARED"
        CREATING = "CREATING"
        PREPARING = "PREPARING"
        PREPARED = "PREPARED"
        DELETING = "DELETING"
        FAILED = "FAILED"
        VERSIONING = "VERSIONING"
        UPDATING = "UPDATING"

    def __init__(self, agent_id: str,
                 name: str,
                 agent_alias_id: str = "TSTALIASID",
                 agent_alias_arn: str = None,
                 event_processor: Optional[EventStreamProcessor] = None,
                 output_formatter: Optional[OutputFormatter] = None,
                 session=None):
        # Store internal variables
        self.agent_id = agent_id
        self.name = name
        self._status = self.Status.NOT_PREPARED
        self._collaboration_mode = "DISABLED"
        self._agent_alias_id = agent_alias_id
        self._agent_alias_arn = agent_alias_arn
        self._event_processor = event_processor or StandardEventProcessor()
        self._f = output_formatter or BasicOutputFormatter()

        # Initialize clients with default configurations
        self.session = session or boto3.Session()
        self._bedrock_client = self.session.client('bedrock')
        self._bedrock_runtime = self.session.client('bedrock-runtime')
        self._bedrock_agent_client = self.session.client('bedrock-agent')
        self._bedrock_agent_runtime = self.session.client('bedrock-agent-runtime')
        self._agent_helper = AgentsForAmazonBedrock()

    @classmethod
    def create(cls,
               name: str,
               instructions: str,
               model: str = DEFAULT_AGENT_MODEL,
               event_processor: Optional[EventStreamProcessor] = None,
               output_formatter: Optional[OutputFormatter] = None) -> "Agent":
        """Create a new Bedrock Agent."""

        event_processor = event_processor or StandardEventProcessor()
        f = output_formatter or BasicOutputFormatter()
        f.output(f"Creating agent {name}...")

        trimmed_instructions = dedent(instructions[0: MAX_DESCR_SIZE - 1])

        agents_helper = AgentsForAmazonBedrock()
        (agent_id, agent_alias_id, agent_alias_arn) = (
            agents_helper.create_agent(
                name,
                trimmed_instructions,
                trimmed_instructions,  # Instructions as description
                [model],
                code_interpretation=False,
                guardrail_id=None,
                verbose=True,
            )
        )
        f.output(f"Created agent, id: {agent_id}, alias id: {agent_alias_id}\n")

        # Create an instance of the Agent class attached to the agent
        agent = cls(agent_id=agent_id,
                    name=name,
                    agent_alias_id=agent_alias_id,
                    agent_alias_arn=agent_alias_arn,
                    event_processor=event_processor,
                    output_formatter=output_formatter)
        return agent

    def _wait_until_prepared(self):
        # Wait until the agent state is 'PREPARED'
        self._agent_helper.wait_agent_status_update(self.agent_id)
        # _agent_helper doesn't actually return the status, get it via lower level API
        status = self.status
        if status != Agent.Status.PREPARED:
            raise RuntimeError(f"Agent {self.agent_id} is not prepared. Status: {status}")

    def prepare(self):
        """Prepares the agent for use (creates an alias). Most operations will do this implicitly if it's not done"""
        self._agent_helper.prepare(self.name)
        self._wait_until_prepared()
        response = self._bedrock_agent_client.create_agent_alias(
            agentAliasName="with-code-ag", agentId=self.agent_id
        )
        self._agent_alias_id = response["agentAlias"]["agentAliasId"]
        self._agent_alias_arn = response["agentAlias"]["agentAliasArn"]
        self._agent_helper.wait_agent_alias_status_update(self.agent_id, self._agent_alias_id)

    def invoke(self, prompt: str, session_id=str(uuid.uuid1())) -> str:
        """Send a prompt to the agent and get response."""
        # If the agent is not prepared, prepare it before invoking
        if self.status != Agent.Status.PREPARED:
            self.prepare()

        response = self._bedrock_agent_runtime.invoke_agent(
            agentId=self.agent_id,
            agentAliasId=self._agent_alias_id,
            sessionId=session_id,
            inputText=prompt,
            enableTrace=True
        )

        # Process the event stream
        event_stream = response['completion']
        for event in event_stream:
            self._event_processor.on_event(event)
        return self._event_processor.get_response()

    def invoke_with_tasks(self,
                          tasks: List[Task],
                          additional_instructions: str = "",
                          processing_type: str = "sequential",
                          enable_trace: bool = False,
                          trace_level: str = "none",
                          verbose: bool = False):
        if self.status != Agent.Status.PREPARED:
            self.prepare()
        prompt = ""
        if processing_type == "sequential":
            prompt += """Please perform the following tasks sequentially. Be sure you do not 
                         perform any of them in parallel. If a task will require information produced from a prior 
                         task, be sure to include the details as input to the task.\n\n"""
            task_num = 1
            for t in tasks:
                prompt += f"Task {task_num}. {t}\n"
                task_num += 1

            prompt += ("\nBefore returning the final answer, review whether you have achieved the expected "
                       "output for each task.")

            if additional_instructions != "":
                prompt += f"\n{additional_instructions}"
        elif processing_type == "allow_parallel":
            prompt += """Please perform as many of the following tasks in parallel where possible.
                      When a dependency between tasks is clear, execute those tasks in sequential order. 
                      If a task will require information produced from a prior task,
                      be sure to include the details as input to the task.\n\n"""
            task_num = 1
            for t in tasks:
                prompt += f"Task {task_num}. {t}\n"
                task_num += 1

            prompt += ("\nBefore returning the final answer, review whether you have achieved the expected output "
                       "for each task.")

            if additional_instructions != "":
                prompt += f"\n{additional_instructions}"

        if verbose and enable_trace and trace_level == "core":
            print(f"Here is the prompt being sent to the supervisor:\n{prompt}\n")

        # make a session id with a prefix of current time to make the
        # id's sortable when looking at session logs or metrics or storage outputs.
        timestamp = int(time.time())
        session_id = self.name + "-" + str(timestamp) + "-" + str(uuid.uuid1())
        if verbose:
            print(f"Session id: {session_id}")

        # finally, invoke the supervisor request
        result = self.invoke(
            prompt=dedent(prompt),
            session_id=session_id,
            # enable_trace=enable_trace,
            # trace_level=trace_level,
            # multi_agent_names=self.multi_agent_names,
        )
        return result

    @classmethod
    def attach_by_id(cls, agent_id: str, output_formatter: Optional[OutputFormatter] = None) -> "Agent":
        """Attach to existing Bedrock Agent by ID."""
        f = output_formatter or BasicOutputFormatter()
        try:
            # Create a temporary client to get agent details
            client = boto3.client('bedrock-agent')
            response = client.get_agent(agentId=agent_id)
            agent_details = response["agent"]

            agents_helper = AgentsForAmazonBedrock()

            # Create agent instance with retrieved details
            agent_alias_id = agents_helper.get_agent_latest_alias_id(agent_id)
            agent_alias_arn = agents_helper.get_agent_alias_arn(agent_id, agent_alias_id)
            name = agent_details.get("agentName", "")
            return cls(agent_id=agent_id, name=name, agent_alias_arn=agent_alias_arn,
                       agent_alias_id=agent_alias_id, output_formatter=output_formatter)

        except ClientError as e:
            f.output(f"Couldn't connect to agent {agent_id}. {e}")
            raise

    @classmethod
    def attach_by_arn(cls, agent_arn: str, output_formatter: Optional[OutputFormatter] = None) -> "Agent":
        """Attach to existing Bedrock Agent by ARN."""
        # ARN format: arn:aws:bedrock:<region>:<account>:agent/<agent_id>
        agent_id = agent_arn.split('/')[-1]
        return cls.attach_by_id(agent_id, output_formatter)

    @classmethod
    def attach_by_name(cls, agent_name: str, output_formatter: Optional[OutputFormatter] = None) -> "Agent":
        """Attach to existing Bedrock Agent by name."""
        client = boto3.client('bedrock-agent')
        agents = client.list_agents()['agentSummaries']
        matching = [a for a in agents if a['agentName'] == agent_name]
        if not matching:
            raise ValueError(f"No agent found with name {agent_name}")
        return cls.attach_by_id(matching[0]['agentId'], output_formatter)

    def enable_code_interpretation(self) -> None:
        """Enable code interpretation on this Agent."""
        self._agent_helper.add_code_interpreter(self.name)
        self._status = Agent.Status.NOT_PREPARED  # Force preparation on next invoke

    def attach_tool(self, tool: Tool) -> None:
        """Attach a tool to this agent."""
        # add_action_group_with_lambda() doesn't check if the lambda already exists
        # For now, we check if it does and delete it, although this isn't optimal behavior #TODO: review
        lambda_client = boto3.client('lambda')
        try:
            lambda_client.get_function(FunctionName=tool.name)
            lambda_client.delete_function(FunctionName=tool.name)
            self._f.output(f"Deleted existing lambda {tool.name}")
        except lambda_client.exceptions.ResourceNotFoundException:
            pass  # Lambda doesn't exist, no need to delete

        tool_defs = [tool.to_action_group_definition()]
        self._agent_helper.add_action_group_with_lambda(
            self.name,
            tool.name,
            tool.code_file,
            tool_defs,  # One function for now, generalize to handle groups later
            tool.name,  # Using tool name as the action group name
            f"actions for {tool.description}"
        )
        self._status = Agent.Status.NOT_PREPARED  # Force preparation on next invoke

    def attach_knowledge_base(self, kb: "KnowledgeBase") -> None:
        """Attach a knowledge base to this agent."""
        pass

    def set_as_supervisor(self, collaboration_mode: str = "SUPERVISOR") -> None:
        """Set this agent as a supervisor.

        Args:
            collaboration_mode: The collaboration mode for the supervisor agent:
                - SUPERVISOR: Coordinates responses from collaborator agents
                - SUPERVISOR_WITH_ROUTING: Routes information to appropriate collaborator agent for final response
        """
        if collaboration_mode not in ["SUPERVISOR", "SUPERVISOR_WITH_ROUTING"]:
            raise ValueError("Collaboration mode must be either 'SUPERVISOR' or 'SUPERVISOR_WITH_ROUTING'")

        # Get updated agent info
        response = self._bedrock_agent_client.get_agent(agentId=self.agent_id)
        agent_resource_role_arn = response["agent"]["agentResourceRoleArn"]
        foundation_model = response["agent"]["foundationModel"]
        agent_name = response["agent"]["agentName"]

        # Update the agent with the collaboration mode
        self._bedrock_agent_client.update_agent(
            agentId=self.agent_id,
            agentResourceRoleArn=agent_resource_role_arn,
            foundationModel=foundation_model,
            agentName=agent_name,
            agentCollaboration=collaboration_mode
        )
        self._status = Agent.Status.NOT_PREPARED  # Force preparation on next invoke

    def attach_agent(self, agent: "Agent") -> None:
        """Attach a sub-agent to this agent."""
        self.attach_agents([agent])

    def attach_agents(self, agents: list["Agent"]) -> None:
        """Attach multiple sub-agents to this agent."""
        sub_agent_list = self._agent_helper.build_sub_agent_list([a.name for a in agents])
        for name in sub_agent_list:
            sub_agent = Agent.attach_by_name(name)
            if sub_agent.status != Agent.Status.PREPARED:
                self._f.output(f"Preparing sub-agent {name}")
                sub_agent.prepare()
            self._f.output(f"Attaching sub-agent {name}")
        self._agent_helper.associate_sub_agents(self.agent_id, sub_agent_list)
        self._status = Agent.Status.NOT_PREPARED  # Force preparation on next invoke

    def delete(self, knowledge_bases=True, lambdas=True, sub_agents=True) -> None:
        """Delete the agent and cleanup resources."""
        # for tool in agents_helper.get_tools(self.name): # TODO: Delete tools
        #    tool.delete()
        self._agent_helper.delete_agent(self.name)

    @property
    def status(self) -> str:
        response = self._bedrock_agent_client.get_agent(agentId=self.agent_id)
        self._status = response["agent"]["agentStatus"]
        """Get current agent status."""
        return self._status
