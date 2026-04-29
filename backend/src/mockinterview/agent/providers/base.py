from abc import ABC, abstractmethod
from typing import Any

from mockinterview.schemas.provider import ProviderTestResult


class LLMProvider(ABC):
    """Abstract interface for any LLM provider that can answer with structured JSON."""

    @abstractmethod
    def call_json(
        self,
        system: str,
        messages: list[dict[str, Any]],
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Send a system + messages prompt; return parsed JSON dict.

        Each provider handles its own caching / output format / SDK-specific shape.
        Caller passes a plain string for `system` (NOT the Anthropic block list).
        """
        ...

    @abstractmethod
    def test_connection(self) -> ProviderTestResult:
        """Minimal-cost test: verify HTTP reachability + key validity + JSON output.

        Implemented independently of call_json() to guarantee max_tokens=30 and
        deterministic prompt. Must NOT raise — all errors are mapped to a
        ProviderTestResult with the appropriate category.
        """
        ...
