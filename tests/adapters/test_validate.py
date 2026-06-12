from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from cli_eduardo.adapters.validate import run_validate
from cli_eduardo.use_cases.gateway import AgentResult


def _runner(output: str, success: bool = True) -> MagicMock:
    r = MagicMock()
    r.run.return_value = AgentResult(success=success, output=output)
    return r


def _findings_json(*items: dict[str, object]) -> str:
    return json.dumps(list(items))


def test_success_prints_findings(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    report = tmp_path / "report.txt"
    report.write_text("test report", encoding="utf-8")
    payload = _findings_json(
        {"description": "High risk finding", "severity": "high", "flagged_for_review": True},
        {"description": "Low risk note", "severity": "low", "flagged_for_review": False},
    )

    code = run_validate(report, "LGD-001", _runner(payload))

    assert code == 0
    out = capsys.readouterr().out
    assert "[HIGH] [FLAGGED] High risk finding" in out
    assert "[LOW] Low risk note" in out


def test_file_not_found_returns_1(tmp_path: Path) -> None:
    code = run_validate(tmp_path / "missing.txt", "LGD-001", MagicMock())
    assert code == 1


def test_runner_failure_returns_1(tmp_path: Path) -> None:
    report = tmp_path / "report.txt"
    report.write_text("content", encoding="utf-8")
    code = run_validate(report, "LGD-001", _runner("agent error", success=False))
    assert code == 1


def test_malformed_json_returns_1(tmp_path: Path) -> None:
    report = tmp_path / "report.txt"
    report.write_text("content", encoding="utf-8")
    code = run_validate(report, "LGD-001", _runner("not json"))
    assert code == 1


def test_encoding_parameter_used(tmp_path: Path) -> None:
    report = tmp_path / "report.txt"
    report.write_bytes("caf\xe9".encode("cp1252"))
    code = run_validate(report, "LGD-001", _runner("[]"), encoding="cp1252")
    assert code == 0


def test_flagged_finding_includes_flag_marker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "report.txt"
    report.write_text("report", encoding="utf-8")
    payload = _findings_json(
        {"description": "Weak evidence", "severity": "medium", "flagged_for_review": True}
    )

    run_validate(report, "LGD-001", _runner(payload))

    assert "[FLAGGED]" in capsys.readouterr().out


def test_unflagged_finding_has_no_flag_marker(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    report = tmp_path / "report.txt"
    report.write_text("report", encoding="utf-8")
    payload = _findings_json(
        {"description": "Clear finding", "severity": "low", "flagged_for_review": False}
    )

    run_validate(report, "LGD-001", _runner(payload))

    assert "[FLAGGED]" not in capsys.readouterr().out
