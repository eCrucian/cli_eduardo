from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import cast

from cli_eduardo.domain.findings import Severity, ValidationFinding
from cli_eduardo.use_cases.gateway import AgentRunner

_PROMPT = textwrap.dedent("""\
    You are a model validation analyst. Read the LGD validation report in
    "report.txt" and extract every finding.

    Return ONLY a JSON array — no prose, no markdown fences. Each element:
    {
      "description": "<concise description>",
      "severity": "low" | "medium" | "high",
      "flagged_for_review": true | false
    }

    Policy: set flagged_for_review=true when evidence is weak or ambiguous.
    Do not invent findings not present in the report.
""")


def validate_lgd_report(
    sandbox_dir: Path,
    model_id: str,
    runner: AgentRunner,
) -> list[ValidationFinding]:
    """Extract ValidationFindings from an LGD report placed in sandbox_dir/report.txt."""
    result = runner.run(
        prompt=_PROMPT,
        cwd=str(sandbox_dir),
        allowed_tools=["Read"],
    )
    if not result.success:
        raise RuntimeError(f"Agent run failed for model {model_id!r}: {result.output}")

    try:
        raw = cast(list[dict[str, object]], json.loads(result.output))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Agent returned invalid JSON for model {model_id!r}: {exc}"
        ) from exc

    return [
        ValidationFinding(
            model_id=model_id,
            description=str(item["description"]),
            severity=Severity(str(item["severity"])),
            flagged_for_review=bool(item["flagged_for_review"]),
        )
        for item in raw
    ]
