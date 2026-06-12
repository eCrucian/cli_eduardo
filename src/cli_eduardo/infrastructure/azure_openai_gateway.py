from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

import openai
from azure.identity import ClientSecretCredential
from openai import AzureOpenAI

from cli_eduardo.infrastructure.sandbox import read_sandbox_files
from cli_eduardo.use_cases.gateway import AgentResult

# TODO(human): confirm AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT env var names
_DEFAULT_API_VERSION = "2024-02-01"


def _make_token_provider(credential: ClientSecretCredential) -> Callable[[], str]:
    def _get_token() -> str:
        return credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token

    return _get_token


class AzureOpenAIGateway:
    """LLM gateway using Azure OpenAI with Service Principal authentication."""

    def __init__(
        self,
        endpoint: str,
        deployment: str,
        api_version: str = _DEFAULT_API_VERSION,
    ) -> None:
        credential = ClientSecretCredential(
            tenant_id=os.environ["AZURE_TENANT_ID"],
            client_id=os.environ["AZURE_CLIENT_ID"],
            client_secret=os.environ["AZURE_CLIENT_SECRET"],
        )
        self._client = AzureOpenAI(
            azure_endpoint=endpoint,
            azure_ad_token_provider=_make_token_provider(credential),
            api_version=api_version,
        )
        self._deployment = deployment

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
            response = self._client.chat.completions.create(
                model=self._deployment,
                messages=[{"role": "user", "content": content}],
            )
        except openai.OpenAIError as exc:
            return AgentResult(success=False, output=str(exc))

        text = response.choices[0].message.content or ""
        return AgentResult(success=True, output=text)
