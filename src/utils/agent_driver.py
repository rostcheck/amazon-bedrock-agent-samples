#!/usr/bin/env python
import json
# Copyright 2024 Amazon.com and its affiliates; all rights reserved.
# This file is AWS Content and may not be duplicated or distributed without permission
import sys
from pathlib import Path
import datetime
import traceback
from ruamel.yaml import YAML
import uuid
from textwrap import dedent
import os
import argparse
from typing import Dict, List
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
from src.utils.bedrock_agent import Agent, SupervisorAgent, Task, region, account_id

current_dir = os.path.dirname(os.path.abspath(__file__))
task_yaml_path = os.path.join(current_dir, "tasks.yaml")
agent_yaml_path = os.path.join(current_dir, "agents.yaml")
inputs_yaml_path = os.path.join(current_dir, "inputs.yaml")
tool_def_path = os.path.join(current_dir, "")  # Use local tool files
yaml = YAML()


def read_yaml_file(file_path) -> Dict:
    """Read a YAML file and return its content as a dictionary"""
    if not os.path.exists(file_path):
        print(f"File {file_path} does not exist.")
        sys.exit(1)
    with open(file_path, 'r') as file:
        return yaml.load(file)


def get_supervisor_name(yaml_content: Dict) -> str:
    """Get the supervisor agent name from the agent config"""
    supervisor_name = None
    for name, agent in yaml_content.items():
        if "collaboration_type" in agent and agent["collaboration_type"] == "SUPERVISOR":
            supervisor_name = name
    return supervisor_name


def get_tool_names(yaml_content: Dict) -> List[str]:
    """Get a list of the tool names used across the agents"""
    tool_names = set()  # using a set to avoid duplicates
    for name, agent in yaml_content.items():
        if "tools" in agent:
            tool_names.update(agent["tools"])  # add all tools from this agent
    return list(tool_names)  # convert back to list


def get_tool_definitions(tool_def_path: str, agents_config: Dict) -> Dict:
    """Read all the tool definitions from local files"""
    tool_definitions = {}
    tool_names = get_tool_names(agents_config)
    for tool_name in tool_names:
        # Create the full path to the tool definition file (using os independence)
        tool_def_file = os.path.join(tool_def_path, f"{tool_name}_definition.json")
        if not Path(tool_def_file).exists():
            print(f"Tool {tool_name} does not have a definition file. Please create one.")
            sys.exit(1)
        # Read the tool def from the JSON file and replace 'region' and 'account_id' placeholders
        with open(tool_def_file, 'r') as file:
            tool_def = file.read().replace('{region}', region).replace('{account_id}', account_id)
            # Parse the JSON content and store it in the tool_definitions dictionary
            tool_definitions[tool_name] = json.loads(tool_def)
    return tool_definitions


def main(args):
    agents_config = read_yaml_file(agent_yaml_path)
    tasks_config = read_yaml_file(task_yaml_path)
    inputs = read_yaml_file(inputs_yaml_path)
    if args.recreate_agents == "false":
        Agent.set_force_recreate_default(False)
    else:
        Agent.set_force_recreate_default(True)
        Agent.delete_by_name("startup_advisor", verbose=True)
    if args.clean_up == "true":
        for name in agents_config.keys():
            Agent.delete_by_name(name, verbose=True)
    else:
        if args.tool_definition_dir:
            tool_def_path = args.tool_definition_dir
        supervisor_name = get_supervisor_name(agents_config)

        # Create the tasks
        task_names = tasks_config.keys()
        tasks = []
        for task in task_names:
            task = Task(task, read_yaml_file(task_yaml_path), inputs)
            tasks.append(task)

        # Load tool definitions
        tool_definitions = get_tool_definitions(tool_def_path, agents_config)

        # Create the Agents
        agents = {}
        for agent_name in agents_config.keys():
            print(f"Creating agent: {agent_name}")
            agent_yaml_content = agents_config[agent_name]
            tools = []
            if "tools" in agent_yaml_content:
                for tool_name in agent_yaml_content["tools"]:
                    tools.append(tool_definitions[tool_name])
            agent = Agent(agent_name, agents_config, tools=tools)
            agents[agent_name] = agent

        print(f"\n\nCreating {supervisor_name} as a supervisor agent...\n\n")
        supervisor_agent = SupervisorAgent(supervisor_name, agents_config,
                                           list(agents.values()),
                                           verbose=False)

        if args.recreate_agents == "false":
            print("\n\nInvoking supervisor agent...\n\n")

            time_before_call = datetime.datetime.now()
            print(f"time before call: {time_before_call}\n")
            try:
                folder_name = supervisor_agent.name.replace(" ", "-") + "-" + str(uuid.uuid4())[:4]
                result = supervisor_agent.invoke_with_tasks(tasks,
                    additional_instructions=dedent(f"""
                                Use a single Working Memory table for this entire set of tasks, with 
                                table name: {folder_name}. Tell your collaborators this table name as part of 
                                every request, so that they are not confused and they share state effectively.
                                The keys they use in that table will allow them to keep track of any number 
                                of state items they require. When you have completed all tasks, summarize 
                                your work, and share the table name so that all the results can be used and 
                                analyzed."""),
                    processing_type="sequential",
                    enable_trace=True, trace_level=args.trace_level,
                    verbose=True)
                print(result)
            except Exception as e:
                print(e)
                traceback.print_exc()
                pass

            duration = datetime.datetime.now() - time_before_call
            print(f"\nTime taken: {duration.total_seconds():,.1f} seconds")
        else:
            print("Recreated agents.")


if __name__ == '__main__':

    parser = argparse.ArgumentParser()

    parser.add_argument("--recreate_agents", required=False, default='true', help="False if reusing existing agents.")
    parser.add_argument("--trace_level", required=False, default="core",
                        help="The level of trace, 'core', 'outline', 'all'.")
    parser.add_argument("--tool_definition_dir", required=False, default='tools',
                        help="Directory to find tool definition files in")

    parser.add_argument(
        "--clean_up",
        required=False,
        default="false",
        help="Cleanup all infrastructure.",
    )
    args = parser.parse_args()
    main(args)
