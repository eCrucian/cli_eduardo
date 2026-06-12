from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cli_eduardo.use_cases.gateway import AgentResult


@pytest.fixture()
def mock_agent_runner() -> MagicMock:
    """Stub AgentRunner — replaces real LLM calls in all unit tests."""
    runner = MagicMock()
    runner.run.return_value = AgentResult(success=True, output="")
    return runner
