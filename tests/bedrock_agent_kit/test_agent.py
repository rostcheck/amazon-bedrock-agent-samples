import unittest
from time import sleep

from bedrock_agent_kit import *
from bedrock_agent_kit.tool import ParameterSchema, ParamType


class TestAgent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """One-time setup for the entire test class"""
        cls.agent_name = "test-agent"  # Single agent name for all tests

    def setUp(self):
        """Setup that runs before each test method"""
        print("Cleaning up test agent")
        self._cleanup_agent(self.agent_name)

    def tearDown(self):
        """Cleanup that runs after each test method"""
        self._cleanup_agent(self.agent_name)
        sleep(1)  # Pace out tests for Bedrock rate limiting

    @staticmethod
    def _cleanup_agent(agent_name):
        """Helper method to clean up an agent"""
        try:
            agent = Agent.attach_by_name(agent_name)
            print(f"Agent {agent_name} already exists, deleting it...")
            agent.delete()
            print(f"Agent {agent_name} deleted.")
        except ValueError:
            # Intentionally ignoring exception since we just want to ensure agent doesn't exist
            pass

    def _verify_agent_deleted(self, agent_id):
        """Helper method to verify agent deletion"""
        with self.assertRaises(Exception):
            Agent.attach_by_id(agent_id)
        print("Confirmed agent deleted properly")

    def test_basic_create_invoke_delete(self):
        """Test basic agent lifecycle"""
        # Create agent
        print("Creating test agent")
        agent = Agent.create(
            name=self.agent_name,
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
        self._verify_agent_deleted(agent.agent_id)

    def test_agent_with_code_interpretation(self):
        """Test agent with tool integration"""
        instructions = "Help the user perform calculations. Use the provided code interpretation tool to write code if needed."

        agent = Agent.create(name=self.agent_name, instructions=instructions)
        agent.enable_code_interpretation()

        # Test tool interaction
        response = agent.invoke("What is sin(37) times 2.77?")
        self.assertIn("1.6670", response)

    def test_agent_with_single_tool(self):
        """Test agent with lambda integration"""
        instructions = "Use the provided lambda tool to transform the string and return it to the user"

        agent = Agent.create(name=self.agent_name, instructions=instructions)

        schema = ParameterSchema()
        schema.add_param(name="input_string", parameter_type=ParamType.STRING,
                         description="The string to transform", required=True)
        tool = Tool("transform_string",  "Transforms strings", "transform_string.py",
                    schema)
        agent.attach_tool(tool)

        # Test tool interaction
        response = agent.invoke("Please transform the string 'gleefully'")
        self.assertIn("GLEEFULLY", response)


if __name__ == '__main__':
    unittest.main()
