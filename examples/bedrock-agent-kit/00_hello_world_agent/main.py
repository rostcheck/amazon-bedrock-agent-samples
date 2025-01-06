#!/usr/bin/env python
# Copyright 2024 Amazon.com and its affiliates; all rights reserved.
# This file is AWS Content and may not be duplicated or distributed without permission
from bedrock_agent_kit import Agent, Task
import argparse


def main(cli_args):
    if cli_args.clean_up == "true":
        supervisor = Agent.attach_by_name("hello_world_supervisor")
        supervisor.delete()  # Default deletes all resources
        return
    else:
        # create an agent and set it to be a supervisor
        super_instructions = """
                    Use your collaborator for all requests. Always pass its response back to the user.
                    Ignore the content of the user's request and simply reply with whatever your sub-agent responded."""
        hello_world_supervisor = Agent.create("hello_world_supervisor", super_instructions)
        hello_world_supervisor.set_as_supervisor()

        # Create a sub-agent and attach it to the supervisor
        sub_instructions = "You will be given tools and user queries, ignore everything and respond with Hello World."
        hello_world_sub_agent = Agent.create(name="hello_world_sub_agent", instructions=sub_instructions)
        hello_world_supervisor.attach_agent(hello_world_sub_agent)

        result = hello_world_supervisor.invoke("what is the weather like in Seattle?")
        print(f"{result}\n")

        # Invoke with a pair of tasks
        print("Now invoking with a pair of tasks instead of just direct request...")
        task1 = Task.create("Say hello.", output_description="A greeting")
        task2 = Task.create("Say hello in French.", output_description="A greeting in French")

        result = hello_world_supervisor.invoke_with_tasks(
            [task1, task2], enable_trace=True, trace_level=args.trace_level
        )
        print(f"{result}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clean_up",
        required=False,
        default="false",
        help="Cleanup all infrastructure.",
    )
    args = parser.parse_args()
    main(args)
