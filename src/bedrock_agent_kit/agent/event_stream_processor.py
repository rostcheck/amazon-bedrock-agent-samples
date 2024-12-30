from typing import List, Dict, Any
from .output_formatter import *
from .citation_formatter import Citation, CitationFormatter
from .stats_collector import StatsCollector
from .file_handler import FileHandler


class EventStreamProcessor(ABC):
    """Interface for receiving and processing events from the Agent event stream."""
    def __init__(self, formatter: OutputFormatter = None):
        self._formatter = formatter or NullOutputFormatter()

    @abstractmethod
    def on_event(self, event: Dict[str, Any]) -> None:
        """Called when an event is received from the event stream during agent execution."""
        pass


class StandardEventProcessor(EventStreamProcessor):
    def __init__(self, formatter: OutputFormatter = None,
                 stats_collector: StatsCollector = None,
                 file_handler: FileHandler = None,
                 citation_formatter: CitationFormatter = None):
        super().__init__(formatter)
        self._formatter = formatter or BasicOutputFormatter()
        self._stats_collector = stats_collector or StatsCollector()
        self._file_handler = file_handler or FileHandler()
        self._citation_formatter = citation_formatter or CitationFormatter(formatter)
        self._response_chunks = []

    def on_event(self, event: Dict[str, Any]) -> None:
        """Process events from the agent execution stream."""
        if "chunk" in event:
            chunk = event.get("chunk", {})
            if "bytes" in chunk:
                content = chunk["bytes"]
                content = content.decode("utf8")
                citations = self._extract_citations(event)
                if citations:
                    content = self._citation_formatter.format_with_citations(content, citations)
                self._response_chunks.append(content)
                self._formatter.output(content, Activity.FINAL_RESPONSE)

        # if event_type == "trace":
        #     trace = event.get("trace", {})
        #     trace_type = trace.get("type")
        #
        #     # Handle different trace types
        #     if trace_type == "llmTokens":
        #         input_tokens = trace.get("inputTokenCount", 0)
        #         output_tokens = trace.get("outputTokenCount", 0)
        #         self._stats_collector.record_llm_usage(input_tokens, output_tokens)
        #         self._formatter.output(
        #             f"Tokens - Input: {input_tokens}, Output: {output_tokens}", Activity.PERFORMANCE_METRICS
        #         )
        #     elif trace_type == "agentThought":
        #         thought = trace.get("thought", "")
        #         self._formatter.output(thought, Activity.GENERIC)
        #     elif trace_type == "error":
        #         error = trace.get("error", "")
        #         self._formatter.output(f"Error: {error}", Activity.ERROR_REPORTING)
        #     else:
        #         # General trace output
        #         self._formatter.output(str(trace), Activity.GENERIC)
        #
        # elif event_type == "response":
        #     chunk = event.get("chunk", {})
        #     if "bytes" in chunk:
        #         content = chunk["bytes"]
        #         citations = self._extract_citations(event)
        #         if citations:
        #             content = self._citation_formatter.format_with_citations(content, citations)
        #         self._response_chunks.append(content)
        #         self._formatter.output(content, Activity.COLLABORATOR_OUTPUT)
        #
        # elif event_type == "files":
        #     self._file_handler.process_file_event(event)

    def get_response(self) -> str:
        """Get the accumulated response."""
        return "".join(self._response_chunks)

    @staticmethod
    def _extract_citations(event: Dict[str, Any]) -> List[Citation]:
        """Extract citations from event data."""
        citations = []
        chunk = event.get("chunk", {})
        attribution = chunk.get("attribution", {})

        for citation_data in attribution.get("citations", []):
            span = citation_data["generatedResponsePart"]["textResponsePart"]["span"]
            refs = citation_data.get("retrievedReferences", [])
            url = None
            if refs:
                url = (refs[0].get("location", {})
                       .get("s3Location", {})
                       .get("uri"))

            citations.append(Citation(
                start=span["start"],
                end=span["end"],
                reference_url=url
            ))

        return citations
