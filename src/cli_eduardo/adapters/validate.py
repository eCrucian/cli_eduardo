from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from cli_eduardo.domain.findings import ValidationFinding
from cli_eduardo.use_cases.gateway import AgentRunner
from cli_eduardo.use_cases.validate_lgd_report import validate_lgd_report


def _format_finding(finding: ValidationFinding) -> str:
    flag = " [FLAGGED]" if finding.flagged_for_review else ""
    return f"[{finding.severity.value.upper()}]{flag} {finding.description}"


def run_validate(
    report_path: Path,
    model_id: str,
    runner: AgentRunner,
    *,
    encoding: str = "utf-8-sig",
) -> int:
    try:
        report_text = report_path.read_text(encoding=encoding)
    except FileNotFoundError:
        print(f"error: report not found: {report_path}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"error: cannot read: {report_path}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox = Path(tmpdir)
        (sandbox / "report.txt").write_text(report_text, encoding="utf-8")
        try:
            findings = validate_lgd_report(sandbox, model_id, runner)
        except (RuntimeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    for finding in findings:
        print(_format_finding(finding))
    return 0
