# Video engagement optimizer

The video engagements optimizer constructs a team of social media expert agents who work together 
to optimize the title, description, and hashtags for a social media video. The output is a short
document containing the optimized title, description, and hashtags.

It demo uses a generic driver  architecture that can easily be changed to create new agent teams 
and change the tasks, ie. to solve completely different problems, by changing only YAML file 
configuration changes without making code changes.

## Example Output
TITLE:
🚀 AWS Bedrock Agents Mastery: Build Intelligent Agents with Python & Lambda in 2024

DESCRIPTION:
Learn how to supercharge your AWS Bedrock Agents with powerful tool capabilities in this comprehensive 19-minute tutorial. Join AWS Senior Developer Advocate Mike Chambers as he demonstrates how to create and configure Bedrock Agents using Action Groups and Lambda Functions.

🔧 What You'll Learn:
- Step-by-step creation of Bedrock Agents
- Implementing tool access through Action Groups
- Building Lambda Functions with Python
- Enabling agents to perform time queries and calculations
- Hands-on AWS Console demonstration

Perfect for intermediate developers looking to enhance their AI agent development skills. Watch as Mike shows you how to build agents that can interact with external tools and solve real-world problems.

⏱️ Length: 19 minutes
🎯 Level: Intermediate
🛠️ Technologies: AWS Bedrock, Lambda, Python

HASHTAGS:
#AWBedrock #AWSLambda #PythonDevelopment #AIAgents #CloudComputing

## Prerequisites

1. Insure your AWS cloud environment is accessible from the command line:

The command `aws s3 ls` should run without error from a shell prompt. If not, you must set up your 
command line; refer to the [documentation](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html).

2. Clone and install repository

```bash
git clone https://github.com/awslabs/amazon-bedrock-agent-samples

cd amazon-bedrock-agent-samples

python3 -m venv .venv

source .venv/bin/activate

pip3 install -r src/requirements.txt
```

3. Deploy the working_memory tool (provides `set_value_for_key` and `get_value_for_key`)

Follow instructions [here](/src/shared/working_memory/).

## Usage & Sample Prompts

1. Deploy Amazon Bedrock Agents

```bash
python3 examples/multi_agent_collaboration/video_engagement_optimizer/main.py --recreate_agents "true"
```

2. Invoke

```bash
python3 examples/multi_agent_collaboration/video_engagement_optimizer/main.py \
--recreate_agents "false"
```

3. Cleanup

```bash
python3 examples/multi_agent_collaboration/video_engagement_optimizer/main.py --clean_up "true"
```


## Generic driver

The code provided in `main.py` has been genericized to create a team of agents defined in `agents.yaml`
and execute the tasks from `tasks.yaml` replacing any replacement variables in both with the 
values from `inputs.yaml` as needed. For example:

from `agents.yaml` this configuration:
```yaml
video_description_copywriter:
  role: "Video description copywriter"
  goal: > 
    Write the most descriptive and succinct description for a YouTube video to help the algorithm to understand 
    the most appropriate audience to target .
  instructions: >
    You are an expert copywriter and SEO optimizer, deeply experienced at crafting YouTube video descriptions
    to obtain maximum click-through engagement with the most relevant audience.
  tools:
    - set_value_for_key
    - get_key_value
  llm: "anthropic.claude-3-5-haiku-20241022-v1:0"
```
defines the copywriter agent, sets it to use Claude 3.5 Haiku, and attaches the `get_value_for_key` 
and `set_value_for_key` tools, which the Agents use to communicate internally via a DynamoDB table.
The tools must exist and have definition files (see Tools, below).

From `tasks.yaml` this configuration:
```yaml
video_description_task:
  description: >
    Here is a terse description of the video, with the user's answers to your earlier clarifying questions
    Use your team to build a compelling description, title, and tags to help get the highest views
    and connect most effectively with its audience on YouTube:
    
    initial terse description: {initial_video_description} 
    channel url: {channel_url}
    creators: {creator_names}
    video_channel: {video_channel}
    
    Additional information:
    {response_to_questions}
  additional_information: >
    An easy to copy-and-paste final output of the title, description, and hashtags for the user
    to use in their YouTube video description.
````
defines the task to optimize the video description. Note that here the task is using replacement variables 
from `inputs.yaml`:

```yaml
video_channel: "AWS Developers"
creator_names: "AWS Sr. Developer Advocate Mike Chambers"
channel_url: "https://www.youtube.com/@awsdevelopers"
initial_video_description: >
  In this video Mike demonstrates how to create agents that can use tools using Bedrock Agents. This coding 
  walkthrough shows how to create an Agent step by step.
additional_information:
  1. The video focuses on Bedrock Agents and how to give them tool access by attaching Action Groups backed by Lambda Functions
  2. It is targeted at intermediate software developers
  3. In the video, Mike creates lambda functions using Python
  4. Giving agents access to tools allows them to solve problems that they otherwise can’t, such as telling the time or 
     doing accurate math
  5. The video is 19 minutes long
  6. Most of the video is a coding demonstration with Mike building a Bedrock Agent in the AWS console
```

## Optimizing different videos
Changing the values in `inputs.yaml` is sufficient to optimize a different video, without changing the
`agents.yaml` or `tasks.yaml`. 

## Changing the example to solve different problems
For more involved changes, You can change the agent team by changing the entries in`agents.yaml` and alter the tasks in 
`tasks.yaml` to make the team do different work. By doing these, you can create completely different agentic
solutions without writing code.

## Tools

The Tools used by the Agents are backed by lambda functions. The lambdas must be installed into the active
cloud environment (the one configured with `aws --configure`) as described in Prerequisites. Additionally, to make them 
usable by Agents, the generic driver needs metadata configuration describing the arguments and their types, 
which it reads from files in the `tools` directory named like `<tool_name>_definition.json`. 

See `src/shared` for other tools you can install and use.

## License

This project is licensed under the Apache-2.0 License.