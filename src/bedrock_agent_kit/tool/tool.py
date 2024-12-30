class Tool:
    """A tool that can be attached to an agent."""
    def __init__(self, tool_id: str, name: str):
        self.tool_id = tool_id
        self.name = name

    @classmethod
    def create(cls, name: str, description: str = None):
        """Create a new tool."""
        # TODO: Implement tool creation via Bedrock API
        pass

    def delete(self):
        """Delete this tool."""
        # TODO: Implement tool deletion via Bedrock API
        pass
