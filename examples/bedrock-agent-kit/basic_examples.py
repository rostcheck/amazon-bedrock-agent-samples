from bedrock_agent_kit import *

# Minimal agent
agent = Agent.create('test-agent', 'You are an assistant helping the user')
print(agent.invoke('Please write me a poem about Amazon Web Services'))

# Add code interpretation and solve a math problem
agent.enable_code_interpretation()
print(agent.invoke("What is sin(37) times 2.77?"))

# Delete the agent
agent.delete()


