# Amazon Bedrock Agents API Design Principles

## Core Objectives

### 1. Simplified Lifecycle Management
- Create, invoke, evolve, and clean up agents with minimal code
- Abstract away complex infrastructure operations
- Provide intuitive interfaces for common operations
- Handle resource dependencies automatically

### 2. Infrastructure State Management
- Act as synchronized control layer for Bedrock's configuration state
- Handle creation and management of IAM roles and policies
- Manage associated AWS resources (Lambda functions, S3 buckets, etc.)
- Support attaching to existing Bedrock infrastructure
- Enable clean deletion of all associated resources
- Maintain object state consistent with Bedrock's component relationships (Agent ↔ Knowledge Base ↔ IAM roles)

### 3. Resource Discovery and Attachment
```python
# Discovery: Find existing agent
agent = Agent.from_name("existing-agent-name")
# or
agent = Agent.from_arn("arn:aws:bedrock-agent:...")

# Attachment: Now we can work with it
agent.add_tool(some_tool)  # Modify configuration
response = agent.invoke("Do something")  # Use it
agent.cleanup()  # Clean up when done
```

### 4. Component Relationships
- Tools (action groups) are strictly owned by their Agent and are deleted with the Agent. Agents can have multiple Tools. 
- Knowledge Bases have independent lifecycle management, and can be associated with Agents.
- IAM permissions are treated as integral parts of their parent resources
- Cleanup behavior is predictable and hierarchical

## API Design Guidelines

### 1. Progressive Disclosure
- Simple operations should be simple
- Complex operations should be possible 
- Default configurations should be sensible
- Advanced configurations should use named parameters
```python
# Simple case
agent = Agent.create("my-agent", "Help customers with banking")

# Advanced case
agent = Agent.create(
    name="my-agent",
    instructions="Help customers with banking",
    model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0",
    custom_role_arn="arn:aws:iam::...",
    tags={"Environment": "prod"}
)
```

### 2. Resource Lifecycle Management
- Automatic cleanup of all Agent-owned resources on Agent deletion
- Individual Tools can be removed from an Agent
- Optional preservation of associated Knowledge Bases during cleanup
- Cleanup implementation should skip any dependent resources that are already deleted without error.
```python
# Remove specific Tool
agent.remove_tool("deprecated-tool-name")

# Full cleanup including Knowledge Bases
agent.cleanup()

# Preserve Knowledge Bases during cleanup
agent.cleanup(preserve_knowledge_bases=True)
```

### 3. Stateful Operations
- Creation operations should fail if the resource already exists
- Deletion/cleanup operations should be idempotent and ignore any missing dependent resources
- Update operations should fail if the resource doesn't exist

### 4. Error Handling
- Provide clear, actionable error messages
- Use strongly typed parameters when possible 
- Surface underlying service errors with appropriate context

### 5. Versioning
The agent_kit library uses semantic versioning (MAJOR.MINOR.PATCH):
- MAJOR: Breaking changes to the API
- MINOR: New features, backwards compatible
- PATCH: Bug fixes, backwards compatible
The library abstracts Bedrock API changes where possible to maintain consistent behavior across Bedrock versions. New Bedrock features may be exposed through new optional capabilities in minor version updates.

### 6. Prefer Structured Data Over Raw JSON
- Prefer strongly typed Python objects over JSON string manipulation
- Convert JSON responses from Bedrock into proper Python classes
- Use dataclasses or similar structures to represent configuration (but favor composable API calls over those)
- Hide JSON serialization/deserialization details from API users
- Provide helper methods that accept and return native Python types

Example:
Instead of:
```json
{
  "topics_definition": "{\"topics\": [...]}",
  "blocked_response": "{\"message\": \"Access denied\"}"
}
```
Prefer:
```python
class TopicDefinition:
    def __init__(self, topics: List[Topic]):
        self.topics = topics

class GuardrailConfig:
    def __init__(self, topics: TopicDefinition, response: str):
        self.topics = topics
        self.response = response
```
This approach:
- Makes the API more type-safe
- Enables better IDE autocomplete
- Reduces error-prone string manipulation
- Makes the code more maintainable
- Provides better validation at compile time

## Component Relationships

### Agent
- Primary interface for interaction
- Uses tools and knowledge bases
- Controls lifecycle of dependent resources (ex. Tools)

### Tools (Action Groups)
- Represent Lambda functions
- Internally create needed IAM roles and permissions
- Are owned by and scoped to their parent Agent

### Knowledge Bases
- Can exist independently of agents
- Can be attached to agents
- May be shared between agents
- Have their own lifecycle
- Require S3 and OpenSearch resources (internally created as needed)

### Guardrails 
- provide content filtering and safety boundaries for agent interactions.
- Optional components that can be attached to Agents
- Independent of other components (KnowledgeBases, Tools)
- Configured through Topics that define allowed/blocked content
- Reusable across multiple Agents
- An Agent can have at most 1 Guardrail; a Guardrail can have multiple Topics

## Implementation Patterns

### 1. Factory Methods
```python
# Create new
agent = Agent.create(config)

# Attach to existing
agent = Agent.from_name(name)
agent = Agent.from_arn(arn)

# Create from configuration
agent = Agent.create_from_json(json_agent_config)
```

### 2. Resource Management
```python
class Agent:
    def __init__(self):
        self.tools = []
        self.knowledge_bases = []
        
    def attach_tool(self, tool: Tool):
        self.tools.append(tool)
        
    def attach_knowledge_base(self, kb: KnowledgeBase):
        self.knowledge_bases.append(kb)
        
    def cleanup(self):
        for tool in self.tools:
            tool.delete()
        self.tools.clear()
        
        for kb in self.knowledge_bases:
            kb.detach()
        self.knowledge_bases.clear()
```

### 3. Cleanup on failure
Note that cleanup should be enabled by default, but is here set explicitly for illustration.
```python
try:
    agent = Agent.create("test-agent", 
                        instructions="...", 
                        cleanup_on_failure=True)
    agent.attach_tool(tool)
except Exception as e:
    # With cleanup_on_failure=True (default), any created resources 
    # would be automatically deleted before re-raising
    if cleanup_on_failure:
        # clean up dependent resources here
    raise
```

## Best Practices

### 1. Error Handling
- Provide clear error messages
- Clean up on failures
- Provide a parameter to optionally suppress rollback cleanup on creation failure 

### 2. Documentation
- Clear examples for common operations
- Document resource relationships
- Explain cleanup behavior

## Example Usage Flow
```python
# Create agent
agent = Agent.create("customer-service", "Help customers with banking")

# Create and attach knowledge base
kb = KnowledgeBase.create("banking-faq")
kb.add_data_source("s3://banking-faqs")
agent.attach_knowledge_base(kb)

# Alternative: attach existing knowledge base
existing_kb = KnowledgeBase.from_name("existing-faq")
agent.attach_knowledge_base(existing_kb)

# Create and attach tool
tool = Tool.create("account-lookup", {
    "function_name": "lookup_account",
    "description": "Looks up account balance"
})
agent.attach_tool(tool)

# Use agent
response = agent.invoke("What's the balance for account 12345?")

# Clean up everything
agent.cleanup()
```


