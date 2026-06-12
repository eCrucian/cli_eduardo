from __future__ import annotations

from pathlib import Path

import anthropic
from anthropic.types import TextBlock

from cli_eduardo.infrastructure.sandbox import read_sandbox_files
from cli_eduardo.use_cases.gateway import AgentResult

# TODO(human): confirm the approved model name for the corporate gateway
_DEFAULT_MODEL = "claude-sonnet-4-6"
_DEFAULT_MAX_TOKENS = 4096


class ClaudeGateway:
    """LLM gateway using the Anthropic SDK via corporate proxy (ANTHROPIC_BASE_URL env var)."""

    def __init__(
        self,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        # Reads ANTHROPIC_API_KEY and ANTHROPIC_BASE_URL from the environment
        self._client = anthropic.Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def run(
        self,
        prompt: str,
        cwd: str,
        allowed_tools: list[str],
    ) -> AgentResult:
        content = prompt
        if "Read" in allowed_tools:
            files = read_sandbox_files(Path(cwd))
            if files:
                content = f"{prompt}\n\n{files}"

        try:
            message = self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                messages=[{"role": "user", "content": content}],
            )
        except anthropic.APIError as exc:
            return AgentResult(success=False, output=str(exc))

        text = next((b.text for b in message.content if isinstance(b, TextBlock)), "")
        return AgentResult(success=True, output=text)
