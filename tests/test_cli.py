from __future__ import annotations

from unittest.mock import patch

import pytest

from cli_eduardo.cli import _make_runner, main


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc, patch("sys.argv", ["cli_eduardo", "--help"]):
        main()
    assert exc.value.code == 0


def test_no_subcommand_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exc, patch("sys.argv", ["cli_eduardo"]):
        main()
    assert exc.value.code == 0


def test_make_runner_returns_claude_gateway() -> None:
    with patch("cli_eduardo.infrastructure.claude_gateway.anthropic.Anthropic"):
        runner = _make_runner("claude")
    from cli_eduardo.infrastructure.claude_gateway import ClaudeGateway

    assert isinstance(runner, ClaudeGateway)


def test_make_runner_returns_azure_gateway(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_TENANT_ID", "t")
    monkeypatch.setenv("AZURE_CLIENT_ID", "c")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "s")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    with (
        patch("cli_eduardo.infrastructure.azure_openai_gateway.ClientSecretCredential"),
        patch("cli_eduardo.infrastructure.azure_openai_gateway.AzureOpenAI"),
    ):
        runner = _make_runner("azure")
    from cli_eduardo.infrastructure.azure_openai_gateway import AzureOpenAIGateway

    assert isinstance(runner, AzureOpenAIGateway)
