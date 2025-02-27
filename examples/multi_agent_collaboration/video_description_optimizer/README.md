# Voyage Vituoso Agent

Dream big with the Voyage Virtuoso, a supervisor agent that is built for high net worth individuals that need help picking the most expensive and elaborate destinations given a theme ("I want to ski on expert slopes, but need ski-on/ski-off resort with great night life").

## Architecture Diagram

![architecture](./architecture.png)

## Prerequisites

1. Clone and install repository

```bash
git clone https://github.com/awslabs/amazon-bedrock-agent-samples

cd amazon-bedrock-agent-samples

python3 -m venv .venv

source .venv/bin/activate

pip3 install -r src/requirements.txt
```

2. Deploy web_seach tool

Follow instructions [here](/src/shared/web_search/).

## Usage & Sample Prompts


1. Deploy Amazon Bedrock Agents

```bash
python3 examples/multi_agent_collaboration/voyage_virtuoso_agent/main.py --recreate_agents "true"
```

2. Invoke

```bash
python3 examples/multi_agent_collaboration/voyage_virtuoso_agent/main.py \
--recreate_agents "false" \
--voyage ""Give me some great options for skip trip for an expert and with ski-on/ski-off townhouse"
```

3. Cleanup

```bash
python3 examples/multi_agent_collaboration/voyage_virtuoso_agent/main.py --clean_up "true"
```


## License

This project is licensed under the Apache-2.0 License.