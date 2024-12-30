import unittest
from bedrock_agent_kit import *

"""Tests for the bedrock_agent_kit Agent class"""


class TestAgent(unittest.TestCase):
    def test_basic_create_and_delete(self):
        print("Cleaning up test agent")
        # Clean up the agent if it exists
        agent_name = "test-agent"
        try:
            agent = Agent.attach_by_name(agent_name)
            print(f"Agent {agent_name} already exists, deleting it...")
            agent.delete()
            print(f"Agent {agent_name} deleted.")
        except Exception:
            # Intentionally ignoring exception since we just want to ensure agent doesn't exist
            pass

        """Test basic agent lifecycle"""
        # Create agent
        print("Creating test agent")
        agent = Agent.create(
            name="test-agent",
            instructions="You are a poet bot. Help the user to compose poems."
        )

        # Verify creation
        print("Verifying agent created...")
        self.assertIsNotNone(agent.agent_id)

        # Verify can be found
        found_agent = Agent.attach_by_id(agent.agent_id)
        self.assertEqual(found_agent.agent_id, agent.agent_id)

        # The agent will not be prepared but should prepare when we try to invoke it
        print(f"Created agent w/ status {agent.status}")

        # Test invoking agent
        print("Invoking agent...")
        response = agent.invoke("Compose a poem about apples.")
        print(response)
        self.assertIsNotNone(response)
        print("Agent invoked successfully")
        # Delete
        print("Deleting test agent")
        agent.delete()

        # Verify gone
        with self.assertRaises(Exception):
            Agent.attach_by_id(agent.agent_id)
        print("Confirmed agent deleted properly")

    def test_agent_with_tool(self):
        agent_name = "test-tool-agent"
        # Clean up the agent if it exists
        try:
            agent = Agent.attach_by_name(agent_name)
            agent.delete()
        except Exception:
            pass

        """Test agent with tool integration"""
        instructions = "Help the user perform calculations. Use the provided code interpretation tool to write code if needed."

        agent = Agent.create(name="test-tool-agent", instructions=instructions)
        # Create and attach tool
        tool = Tool.create(...)
        agent.attach_tool(tool)

        # Test tool interaction
        response = agent.invoke("Use the tool to...")
        self.assertIn("tool_response", response)

        # Cleanup
        agent.delete()


if __name__ == '__main__':
    unittest.main()
