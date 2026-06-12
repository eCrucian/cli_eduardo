from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cli_eduardo.domain.findings import Severity, ValidationFinding
from cli_eduardo.use_cases.gateway import AgentResult
from cli_eduardo.use_cases.validate_lgd_report import validate_lgd_report


def _runner(output: str, success: bool = True) -> MagicMock:
    r = MagicMock()
    r.run.return_value = AgentResult(success=success, output=output)
    return r


def test_returns_findings(tmp_path: Path) -> None:
    payload = json.dumps([
        {"description": "LGD underestimates tail risk", "severity": "high",
         "flagged_for_review": True},
        {"description": "Backtesting period too short", "severity": "medium",
         "flagged_for_review": False},
    ])
    results = validate_lgd_report(tmp_path, "LGD-001", _runner(payload))

    assert len(results) == 2
    assert results[0] == ValidationFinding(
        model_id="LGD-001",
        description="LGD underestimates tail risk",
        severity=Severity.HIGH,
        flagged_for_review=True,
    )
    assert results[1].severity == Severity.MEDIUM
    assert not results[1].flagged_for_review


def test_empty_findings(tmp_path: Path) -> None:
    assert validate_lgd_report(tmp_path, "LGD-001", _runner("[]")) == []


def test_runner_failure_raises_runtime_error(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Agent run failed"):
        validate_lgd_report(tmp_path, "LGD-001", _runner("network error", success=False))


def test_malformed_json_raises_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid JSON"):
        validate_lgd_report(tmp_path, "LGD-001", _runner("not json"))


def test_invalid_severity_raises_value_error(tmp_path: Path) -> None:
    payload = json.dumps(
        [{"description": "x", "severity": "critical", "flagged_for_review": False}]
    )
    with pytest.raises(ValueError):
        validate_lgd_report(tmp_path, "LGD-001", _runner(payload))


def test_runner_called_with_read_only_tools(tmp_path: Path) -> None:
    runner = _runner("[]")
    validate_lgd_report(tmp_path, "LGD-001", runner)
    runner.run.assert_called_once()
    call = runner.run.call_args
    allowed = call.kwargs.get("allowed_tools") or call.args[2]
    assert allowed == ["Read"]


def test_cwd_scoped_to_sandbox(tmp_path: Path) -> None:
    runner = _runner("[]")
    validate_lgd_report(tmp_path, "LGD-001", runner)
    call = runner.run.call_args
    cwd = call.kwargs.get("cwd") or call.args[1]
    assert cwd == str(tmp_path)
