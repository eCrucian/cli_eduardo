from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import openai
import pytest

from cli_eduardo.infrastructure.azure_openai_gateway import AzureOpenAIGateway


@pytest.fixture()
def mock_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_TENANT_ID", "tenant-id")
    monkeypatch.setenv("AZURE_CLIENT_ID", "client-id")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "secret")


@pytest.fixture()
def gateway(mock_env: None) -> AzureOpenAIGateway:
    with (
        patch("cli_eduardo.infrastructure.azure_openai_gateway.ClientSecretCredential"),
        patch("cli_eduardo.infrastructure.azure_openai_gateway.AzureOpenAI"),
    ):
        return AzureOpenAIGateway(
            endpoint="https://example.openai.azure.com", deployment="gpt-4o"
        )


def _chat_response(text: str | None) -> MagicMock:
    response = MagicMock()
    response.choices[0].message.content = text
    return response


def test_run_returns_completion_text(tmp_path: Path, gateway: AzureOpenAIGateway) -> None:
    gateway._client.chat.completions.create.return_value = _chat_response('["finding"]')

    result = gateway.run("prompt", str(tmp_path), [])

    assert result.success
    assert result.output == '["finding"]'


def test_run_injects_files_for_read_tool(tmp_path: Path, gateway: AzureOpenAIGateway) -> None:
    (tmp_path / "report.txt").write_text("report content", encoding="utf-8")
    gateway._client.chat.completions.create.return_value = _chat_response("[]")

    gateway.run("my prompt", str(tmp_path), ["Read"])

    call_kwargs = gateway._client.chat.completions.create.call_args[1]
    sent_content = call_kwargs["messages"][0]["content"]
    assert "report content" in sent_content


def test_run_returns_failure_on_api_error(tmp_path: Path, gateway: AzureOpenAIGateway) -> None:
    gateway._client.chat.completions.create.side_effect = openai.APIConnectionError(
        request=MagicMock()
    )

    result = gateway.run("prompt", str(tmp_path), [])

    assert not result.success


def test_run_handles_none_content(tmp_path: Path, gateway: AzureOpenAIGateway) -> None:
    gateway._client.chat.completions.create.return_value = _chat_response(None)

    result = gateway.run("prompt", str(tmp_path), [])

    assert result.success
    assert result.output == ""
