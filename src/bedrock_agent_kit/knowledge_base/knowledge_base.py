class KnowledgeBase:
    """A knowledge base that can be attached to an agent."""
    def __init__(self, knowledge_base_id: str, name: str):
        self.knowledge_base_id = knowledge_base_id
        self.name = name

    @classmethod
    def create(cls, name: str, description: str = None):
        """Create a new knowledge base."""
        # TODO: Implement knowledge base creation via Bedrock API
        pass

    def delete(self):
        """Delete this knowledge base."""
        # TODO: Implement knowledge base deletion via Bedrock API
        pass
