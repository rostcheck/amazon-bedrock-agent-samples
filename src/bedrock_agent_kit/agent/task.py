import dataclasses


@dataclasses.dataclass
class Task:
    """A task that can be performed by an Agent. Contains a description of expected output, so supervisor
    agents can validate that work is performed correctly"""
    def __init__(self, task_description: str, output_description: str = None):
        self.task_description = task_description
        self.output_description = output_description

    @classmethod
    def create(cls, task_description, output_description) -> "Task":
        return cls(task_description, output_description)
