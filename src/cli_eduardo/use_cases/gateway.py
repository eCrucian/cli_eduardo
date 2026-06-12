from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class AgentResult:
    success: bool
    output: str


class AgentRunner(Protocol):
    """Interchangeable LLM gateway — Claude and Azure OpenAI implement this interface."""

    def run(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str],
    ) -> AgentResult:
        ...
