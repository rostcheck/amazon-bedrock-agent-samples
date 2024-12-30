from typing import Dict, Any
from datetime import timedelta


class StatsCollector:
    """Collects and aggregates execution statistics"""

    def __init__(self):
        self._total_in_tokens = 0
        self._total_out_tokens = 0
        self._total_llm_calls = 0
        self._total_duration = timedelta(0)

    def record_llm_usage(self, input_tokens: int, output_tokens: int):
        self._total_in_tokens += input_tokens
        self._total_out_tokens += output_tokens
        self._total_llm_calls += 1

    def record_duration(self, duration: timedelta):
        self._total_duration += duration

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_in_tokens": self._total_in_tokens,
            "total_out_tokens": self._total_out_tokens,
            "total_llm_calls": self._total_llm_calls,
            "total_duration": self._total_duration,
        }
    
    def reset(self) -> None:
        """Reset all statistics to initial state"""
        self.__init__()

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output) used"""
        return self._total_in_tokens + self._total_out_tokens
