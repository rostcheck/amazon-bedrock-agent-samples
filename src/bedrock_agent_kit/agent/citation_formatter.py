import re
from dataclasses import dataclass
from typing import List, Optional
from .output_formatter import OutputFormatter


@dataclass
class Citation:
    """Structured citation data extracted from event stream"""
    start: int
    end: int
    reference_url: Optional[str]
    text: Optional[str] = None  # The actual text being cited, if needed


class CitationFormatter:
    """Formats text with citations from source documents"""

    def __init__(self, formatter: OutputFormatter, enable_trace: bool = False,
                 trace_level: str = "none"):
        self.formatter = formatter
        self.enable_trace = enable_trace
        self.trace_level = trace_level

    def format_with_citations(self, text: str, citations: List[Citation]) -> str:
        """Add citations to text based on citation information

        Args:
            text: Original text to add citations to
            citations: List of Citation objects with span and reference information

        Returns:
            Text with citations added
        """
        if not citations:
            return text

        if self.enable_trace:
            self.formatter.output(f"got {len(citations)} citations\n", "trace")

        # Clean source tags
        cleaned_text = self._clean_source_tags(text)

        fully_cited = ""
        curr_citation_idx = 0

        for citation in citations:
            if self.enable_trace and self.trace_level == "all":
                self.formatter.output(f"Processing citation {curr_citation_idx + 1}", "trace")

            # Calculate adjusted spans (matching original logic exactly)
            start = citation.start - (curr_citation_idx + 1)
            end = citation.end - (curr_citation_idx + 2) + 4

            # Add cited text segment
            cited_text = cleaned_text[start:end]

            # Handle reference URL
            if citation.reference_url:
                fully_cited += f"{cited_text} [{citation.reference_url}] "
            else:
                fully_cited += cited_text

            # Add prefix for first citation
            if curr_citation_idx == 0:
                answer_prefix = cleaned_text[:start]
                fully_cited = answer_prefix + fully_cited

            if self.enable_trace and self.trace_level == "all":
                self._output_citation_trace(citation, curr_citation_idx, cited_text)

            curr_citation_idx += 1

        # Add any remaining text after the last citation
        if citations:
            last_citation = citations[-1]
            last_end = last_citation.end - (len(citations) + 1) + 4
            if last_end < len(cleaned_text):
                fully_cited += cleaned_text[last_end:]

        return fully_cited

    @staticmethod
    def _clean_source_tags(text: str) -> str:
        patterns = [
            r"\n\n<sources>\n\d+\n</sources>\n\n",
            r"<sources><REDACTED></sources>",
            r"<sources></sources>"
        ]

        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, "", cleaned)

        return cleaned

    def _output_citation_trace(self, citation: Citation, idx: int,
                               span_text: str) -> None:
        """Output trace information for a citation

        Args:
            citation: Citation object containing span and reference information
            idx: Index of the current citation
            span_text: The actual text being cited
        """
        self.formatter.output(f"\n\ncitation {idx + 1}:", "trace")
        self.formatter.output(
            f"citation span... start: {citation.start}, end: {citation.end}",
            "trace"
        )
        self.formatter.output(
            f"citation based on span:====\n{span_text}\n====",
            "trace"
        )
        self.formatter.output(
            f"citation url: {citation.reference_url}\n============",
            "trace"
        )
