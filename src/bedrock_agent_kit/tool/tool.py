from .parameter_schema import ParameterSchema


class Tool:
    """A tool that can be attached to an agent."""
    def __init__(self, name: str, description: str, code_file_or_arn: str, schema: ParameterSchema):
        self.name = name
        self.code_file = code_file_or_arn
        self.schema = schema
        self.description = description

    @classmethod
    def create(cls, name: str, code_file: str, schema: ParameterSchema, description: str = None):
        return cls(name, description, code_file, schema)

    def delete(self):
        """Delete this tool."""
        # TODO: Implement tool deletion via Bedrock API
        pass

    def to_action_group_definition(self) -> dict:
        """
        Converts the Tool instance into the format required for action group creation.
        Returns a dictionary compatible with add_action_group_with_lambda's tool_defs parameter.
        """
        return {
            "name":  self.name,
            "description": self.description,
            "parameters": self.schema.to_dict()
        }
