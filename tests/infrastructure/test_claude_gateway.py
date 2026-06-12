from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import anthropic
import pytest
from anthropic.types import TextBlock

from cli_eduardo.infrastructure.claude_gateway import ClaudeGateway


@pytest.fixture()
def gateway() -> ClaudeGateway:
    with patch("cli_eduardo.infrastructure.claude_gateway.anthropic.Anthropic"):
        return ClaudeGateway()


def _text_block(text: str) -> TextBlock:
    return TextBlock(type="text", text=text)


def test_run_returns_text_content(tmp_path: Path, gateway: ClaudeGateway) -> None:
    mock_msg = MagicMock()
    mock_msg.content = [_text_block('["finding"]')]
    gateway._client.messages.create.return_value = mock_msg  # type: ignore[attr-defined]

    result = gateway.run("prompt", str(tmp_path), [])

    assert result.success
    assert result.output == '["finding"]'


def test_run_injects_files_for_read_tool(tmp_path: Path, gateway: ClaudeGateway) -> None:
    (tmp_path / "report.txt").write_text("report content", encoding="utf-8")
    mock_msg = MagicMock()
    mock_msg.content = [_text_block("[]")]
    gateway._client.messages.create.return_value = mock_msg  # type: ignore[attr-defined]

    gateway.run("my prompt", str(tmp_path), ["Read"])

    call_kwargs = gateway._client.messages.create.call_args[1]  # type: ignore[attr-defined]
    sent_content = call_kwargs["messages"][0]["content"]
    assert "report content" in sent_content


def test_run_no_injection_without_read_tool(tmp_path: Path, gateway: ClaudeGateway) -> None:
    (tmp_path / "secret.txt").write_text("sensitive", encoding="utf-8")
    mock_msg = MagicMock()
    mock_msg.content = [_text_block("[]")]
    gateway._client.messages.create.return_value = mock_msg  # type: ignore[attr-defined]

    gateway.run("my prompt", str(tmp_path), [])

    call_kwargs = gateway._client.messages.create.call_args[1]  # type: ignore[attr-defined]
    sent_content = call_kwargs["messages"][0]["content"]
    assert "sensitive" not in sent_content


def test_run_empty_output_when_no_text_block(tmp_path: Path, gateway: ClaudeGateway) -> None:
    mock_msg = MagicMock()
    mock_msg.content = []
    gateway._client.messages.create.return_value = mock_msg  # type: ignore[attr-defined]

    result = gateway.run("prompt", str(tmp_path), [])

    assert result.success
    assert result.output == ""


def test_run_returns_failure_on_api_error(tmp_path: Path, gateway: ClaudeGateway) -> None:
    gateway._client.messages.create.side_effect = anthropic.APIError(  # type: ignore[attr-defined]
        message="quota exceeded", request=MagicMock(), body=None
    )

    result = gateway.run("prompt", str(tmp_path), [])

    assert not result.success
    assert "quota exceeded" in result.output
