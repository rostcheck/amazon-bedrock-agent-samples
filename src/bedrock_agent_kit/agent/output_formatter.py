from abc import ABC, abstractmethod
from termcolor import colored
from rich.console import Console
from enum import Enum, auto
from typing import Literal

UNDECIDABLE_CLASSIFICATION = "undecidable"
TRACE_TRUNCATION_LENGTH = 300

TermColor = Literal["black", "red", "green", "yellow", "blue", "magenta", "cyan", "white"]


class Activity(Enum):
    GENERIC = auto()
    ROUTING_DECISIONS = auto()  # Magenta
    PERFORMANCE_METRICS = auto()  # Yellow
    ERROR_REPORTING = auto()  # Red
    TOOL_INVOCATION = auto()  # Magenta
    TOOL_ERROR = auto()  # Red
    TOOL_OUTPUT = auto()  # Magenta
    COLLABORATOR_INVOCATION = auto()  # Magenta
    COLLABORATOR_OUTPUT = auto()  # Magenta
    CODE_INTERPRETER = auto()  # Magenta
    KNOWLEDGE_BASE = auto()  # Magenta
    KNOWLEDGE_BASE_OUTPUT = auto()  # Magenta
    FINAL_RESPONSE = auto()  # Cyan
    STEP_MARKER = auto()  # Green
    PRE_PROCESSING = auto()  # Yellow
    POST_PROCESSING = auto()  # Yellow
    SUMMARY_STATS = auto()  # Yellow
    RETURN_VALUE = auto()  # White (default)

    @property
    def color(self) -> TermColor:
        """Get the standard color for this activity type"""
        color_map: dict[Activity, TermColor] = {
            Activity.ROUTING_DECISIONS: "magenta",
            Activity.PERFORMANCE_METRICS: "yellow",
            Activity.ERROR_REPORTING: "red",
            Activity.TOOL_INVOCATION: "magenta",
            Activity.TOOL_ERROR: "red",
            Activity.TOOL_OUTPUT: "magenta",
            Activity.COLLABORATOR_INVOCATION: "magenta",
            Activity.COLLABORATOR_OUTPUT: "magenta",
            Activity.CODE_INTERPRETER: "magenta",
            Activity.KNOWLEDGE_BASE: "magenta",
            Activity.KNOWLEDGE_BASE_OUTPUT: "magenta",
            Activity.FINAL_RESPONSE: "cyan",
            Activity.STEP_MARKER: "green",
            Activity.PRE_PROCESSING: "yellow",
            Activity.POST_PROCESSING: "yellow",
            Activity.SUMMARY_STATS: "yellow",
            Activity.RETURN_VALUE: "white",
            Activity.GENERIC: "white"
        }
        return color_map.get(self, "white")


class OutputFormatter(ABC):
    """Base class for formatting output. Default implementation does nothing."""

    @abstractmethod
    def output(self, message: str, activity: Activity) -> None:
        """Format and output a message.

        Args:
            message: The message to output
            activity: Optional type of activity for formatting
        """
        pass


class NullOutputFormatter(OutputFormatter):
    """A do-nothing implementation of OutputFormatter."""
    def output(self, message: str, activity: Activity = Activity.GENERIC) -> None:
        pass


class BasicOutputFormatter(OutputFormatter):
    def output(self, message: str, activity: Activity = Activity.GENERIC) -> None:
        print(message)


class ColoredOutputFormatter(OutputFormatter):
    def __init__(self):
        self._console = Console()

    @staticmethod
    def __get_color(activity: Activity) -> TermColor:
        """Get the color for the given activity"""
        return activity.color

    def output(self, message: str, activity: Activity = Activity.GENERIC) -> None:
        print(colored(message, self.__get_color(activity)))
