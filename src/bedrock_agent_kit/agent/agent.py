import uuid
from textwrap import dedent
from typing import List, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from .event_stream_processor import EventStreamProcessor, StandardEventProcessor
from src.utils.bedrock_agent_helper import AgentsForAmazonBedrock
from ..tool import Tool
from ..knowledge_base import KnowledgeBase

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
        UNINITIALIZED = "UNINITIALIZED"
        CREATING = "CREATING"
        READY = "READY"
        FAILED = "FAILED"
        DELETING = "DELETING"

    def __init__(self, agent_id: str, name: str, event_processor: Optional[EventStreamProcessor] = None, session=None):
        self.agent_id = agent_id
        self.name = name
        self._tools = []
        self._knowledge_bases = []
        self._event_processor = event_processor or StandardEventProcessor()
        self._alias_id = None
        self._status = Agent.Status.UNINITIALIZED

        # Initialize session and clients
        self.session = session or boto3.Session()
        self._bedrock_client = None
        self._bedrock_runtime = None
        self._bedrock_agent_client = None
        self._bedrock_agent_runtime = None

    @property
    def bedrock_client(self):
        """Lazy initialization of bedrock client with retry configuration."""
        if self._bedrock_client is None:
            self._bedrock_client = self.session.client(
                'bedrock',
                config=Config(
                    retries={'max_attempts': 3},
                    connect_timeout=5,
                    read_timeout=60
                )
            )
        return self._bedrock_client

    @property
    def bedrock_runtime(self):
        """Lazy initialization of bedrock runtime client."""
        if self._bedrock_runtime is None:
            self._bedrock_runtime = self.session.client(
                'bedrock-runtime',
                config=Config(
                    retries={'max_attempts': 3},
                    connect_timeout=5,
                    read_timeout=300  # Longer timeout for model inference
                )
            )
        return self._bedrock_runtime

    @property
    def bedrock_agent_client(self):
        """Lazy initialization of bedrock agent client."""
        if self._bedrock_agent_client is None:
            self._bedrock_agent_client = self.session.client(
                'bedrock-agent',
                config=Config(
                    retries={'max_attempts': 3},
                    connect_timeout=5,
                    read_timeout=60
                )
            )
        return self._bedrock_agent_client

    @property
    def bedrock_agent_runtime(self):
        """Lazy initialization of bedrock agent runtime client."""
        if self._bedrock_agent_runtime is None:
            self._bedrock_agent_runtime = self.session.client(
                'bedrock-agent-runtime',
                config=Config(
                    retries={'max_attempts': 3},
                    connect_timeout=5,
                    read_timeout=300  # Longer timeout for agent operations
                )
            )
        return self._bedrock_agent_runtime

    def _handle_client_error(self, error: ClientError, operation: callable, *args, **kwargs):
        """Handle client errors and retry once if credentials are expired."""
        if self._is_expired_credentials_error(error):
            # Reset relevant client based on the operation's __self__ attribute
            client_instance = operation.__self__
            if client_instance is self._bedrock_client:
                self._bedrock_client = None
            elif client_instance is self._bedrock_runtime:
                self._bedrock_runtime = None
            elif client_instance is self._bedrock_agent_client:
                self._bedrock_agent_client = None
            elif client_instance is self._bedrock_agent_runtime:
                self._bedrock_agent_runtime = None

            # Retry the operation once
            return operation(*args, **kwargs)
        raise error

    @staticmethod
    def _is_expired_credentials_error(error: ClientError) -> bool:
        """Check if the error is related to expired credentials."""
        error_code = error.response.get('Error', {}).get('Code')
        return error_code in ['ExpiredToken', 'RequestExpired', 'InvalidClientTokenId']

    @classmethod
    def create(cls,
               name: str,
               instructions: str,
               model: str = DEFAULT_AGENT_MODEL,
               idle_time_ttl: int = 3600,
               event_processor: Optional[EventStreamProcessor] = None) -> "Agent":
        """Create a new Bedrock Agent."""

        event_processor = event_processor or StandardEventProcessor()
        print(f"Creating agent {name}...")

        trimmed_instructions = dedent(instructions[0: MAX_DESCR_SIZE - 1])
        # instructions = f"Role: {self.role}, \nGoal: {self.goal}, \nInstructions: {self.instructions}"

        # add workaround in instructions, since default prompts can yield hallucinations for tool use calls
        # if self.tool_code is None and self.tool_defs is None:
        # if tools is None and self.tool_code is None and self.tool_defs is None:
        #     self.instructions += (
        #         "\nYou have no available tools. Rely only on your own knowledge."
        #     )

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

        print(
            f"Created agent, id: {agent_id}, alias id: {agent_alias_id}\n"
        )
        # Create an instance of the Agent class attached to the agent
        agent = cls(agent_id=agent_id, name=name, event_processor=event_processor)
        agent._alias_id = agent_alias_id
        return agent

    def invoke(self, prompt: str, session_id=str(uuid.uuid1())) -> str:
        """Send a prompt to the agent and get response."""
        try:
            # If the agent is not prepared, prepare it before invoking
            if self.status != Agent.Status.READY:
                agents_helper = AgentsForAmazonBedrock()
                agents_helper.prepare(self.name)

            response = self.bedrock_agent_runtime.invoke_agent(
                agentId=self.agent_id,
                agentAliasId=self._alias_id,
                sessionId=session_id,
                inputText=prompt,
                enableTrace=True
            )
        except ClientError as e:
            response = self._handle_client_error(e, self.bedrock_agent_runtime.invoke_agent,
                                                 agentId=self.agent_id,
                                                 agentAliasId=self._alias_id,
                                                 sessionId=session_id,
                                                 inputText=prompt,
                                                 enableTrace=True)

        # Process the event stream
        event_stream = response['completion']
        for event in event_stream:
            self._event_processor.on_event(event)
        return self._event_processor.get_response()

    @classmethod
    def attach_by_id(cls, agent_id: str) -> "Agent":
        """Attach to existing Bedrock Agent by ID."""
        try:
            # Create a temporary client to get agent details
            client = boto3.client('bedrock-agent')
            response = client.get_agent(agentId=agent_id)
            agent_details = response["agent"]

            # Create agent instance with retrieved details
            return cls(agent_id=agent_id, name=agent_details.get("agentName", ""))

        except ClientError as e:
            print(f"Couldn't connect to agent {agent_id}. {e}")
            raise

    @classmethod
    def attach_by_arn(cls, agent_arn: str) -> "Agent":
        """Attach to existing Bedrock Agent by ARN."""
        # ARN format: arn:aws:bedrock:<region>:<account>:agent/<agent_id>
        agent_id = agent_arn.split('/')[-1]
        return cls.attach_by_id(agent_id)

    @classmethod
    def attach_by_name(cls, agent_name: str) -> "Agent":
        """Attach to existing Bedrock Agent by name."""
        client = boto3.client('bedrock-agent')
        agents = client.list_agents()['agentSummaries']
        matching = [a for a in agents if a['agentName'] == agent_name]
        if not matching:
            raise ValueError(f"No agent found with name {agent_name}")
        return cls.attach_by_id(matching[0]['agentId'])

    def attach_tool(self, tool: Tool) -> None:
        """Attach a tool to this agent."""
        pass

    def attach_knowledge_base(self, kb: "KnowledgeBase") -> None:
        """Attach a knowledge base to this agent."""
        pass

    def delete(self) -> None:
        """Delete the agent and cleanup resources."""
        agents_helper = AgentsForAmazonBedrock()
        agents_helper.delete_agent(self.name)

    @property
    def status(self) -> str:
        """Get current agent status."""
        return self._status

    @property
    def tools(self) -> List["Tool"]:
        """Get list of attached tools."""
        return self._tools.copy()

    @property
    def knowledge_bases(self) -> List["KnowledgeBase"]:
        """Get list of attached knowledge bases."""
        return self._knowledge_bases.copy()

    def _prepare(self) -> None:
        """Internal method to prepare agent for use."""
        pass
