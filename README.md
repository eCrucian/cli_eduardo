# cli_eduardo — Model Validation Orchestrator

CLI-only orchestration tool for automating model validation workflows (Market Risk,
Liquidity, Credit Risk Capital, BDPO). All output is plain text to stdout. No web UI.

---

## Setup

```bash
# Create venv (requires uv — installed at ~/.local/bin/uv)
uv venv --python 3.12 .venv
source .venv/bin/activate          # Linux/Mac
# .venv\Scripts\activate           # Windows

# Install
pip install -e .
pip install -r requirements-dev.txt
```

### Required environment variables

| Variable | Used by | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude gateway | API key for the corporate proxy |
| `ANTHROPIC_BASE_URL` | Claude gateway | Corporate proxy endpoint (e.g. `https://ai-gateway.corp/anthropic`) |
| `AZURE_TENANT_ID` | Azure gateway | Service Principal tenant |
| `AZURE_CLIENT_ID` | Azure gateway | Service Principal client ID |
| `AZURE_CLIENT_SECRET` | Azure gateway | Service Principal secret |
| `AZURE_OPENAI_ENDPOINT` | Azure gateway | Azure OpenAI resource URL |
| `AZURE_OPENAI_DEPLOYMENT` | Azure gateway | Deployment / model name |

Never hardcode these. Inject from the environment or a secrets manager.

---

## CLI usage

```
python -m cli_eduardo.cli --help
python -m cli_eduardo.cli <command> --help
```

### `validate` — extract findings from a model validation report

```bash
python -m cli_eduardo.cli validate <report> --model-id <id> [options]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `report` | yes | — | Path to the report file |
| `--model-id` | yes | — | Model identifier (e.g. `LGD-2024-01`) |
| `--gateway` | no | `claude` | LLM gateway: `claude` or `azure` |
| `--encoding` | no | `utf-8-sig` | File encoding; use `cp1252` for legacy Office files |

**Examples:**

```bash
# Validate an LGD report using the Claude gateway
python -m cli_eduardo.cli validate \\server\share\modelos\lgd_report.txt \
    --model-id LGD-2024-01

# Use the Azure OpenAI gateway with a cp1252-encoded file
python -m cli_eduardo.cli validate report.txt \
    --model-id MR-2024-05 \
    --gateway azure \
    --encoding cp1252
```

**Output** — one line per finding, written to stdout:

```
[HIGH] [FLAGGED] LGD underestimates tail risk in the 99th percentile scenario
[MEDIUM] Backtesting window covers only 24 months; 36 recommended
[LOW] Documentation references superseded BCB circular
```

`[FLAGGED]` marks findings where evidence was weak or ambiguous (per validation policy).
Exit code `0` on success, `1` on any error (message on stderr).

---

## Development

```bash
pytest -q                              # run tests
pytest --cov=src --cov-fail-under=90   # coverage gate (must stay ≥ 90%)
mypy --strict src/                     # type check
ruff check src/ tests/                 # lint
bandit -r src/                         # SAST (no medium/high findings allowed)
radon cc src/ -n C                     # complexity (no function rated C or worse)
python -m cli_eduardo.cli --help       # smoke test
```

---

## Adding a new command (skill)

Each command follows the same four-layer pattern. Here is the complete recipe,
using a hypothetical `summarize` command as an example.

### 1. Domain model (`src/cli_eduardo/domain/`)

Add the output type the command produces. Pure Python — no I/O, no third-party imports.

```python
# src/cli_eduardo/domain/summary.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ValidationSummary:
    model_id: str
    open_findings: int
    executive_text: str
```

### 2. Use case (`src/cli_eduardo/use_cases/`)

Implement the business logic. Depends only on `domain/` and the `AgentRunner` protocol.
The use case never reads files, opens sockets, or imports SDK packages.

```python
# src/cli_eduardo/use_cases/summarize_report.py
from __future__ import annotations
from pathlib import Path
from cli_eduardo.domain.summary import ValidationSummary
from cli_eduardo.use_cases.gateway import AgentRunner

_PROMPT = "Summarize the findings in report.txt into one action-oriented paragraph."

def summarize_report(
    sandbox_dir: Path,
    model_id: str,
    open_findings: int,
    runner: AgentRunner,
) -> ValidationSummary:
    result = runner.run(
        prompt=_PROMPT,
        cwd=str(sandbox_dir),
        allowed_tools=["Read"],   # minimum privilege — Read only
    )
    if not result.success:
        raise RuntimeError(f"Agent failed for {model_id!r}: {result.output}")
    return ValidationSummary(
        model_id=model_id,
        open_findings=open_findings,
        executive_text=result.output.strip(),
    )
```

**Rules:**
- `allowed_tools` should be `["Read"]` for analysis tasks.
  Only grant `["Read", "Edit"]` or `["Bash"]` if the task genuinely requires writes,
  and document why in a comment.
- The `cwd` passed to `runner.run` must be a dedicated sandbox directory containing
  only the files the task needs — never a raw network share root.
- Raise `RuntimeError` on agent failure; raise `ValueError` on malformed output.
  Never swallow errors silently.

### 3. CLI adapter (`src/cli_eduardo/adapters/`)

Handles file I/O, creates the sandbox, calls the use case, formats output.

```python
# src/cli_eduardo/adapters/summarize.py
from __future__ import annotations
import sys, tempfile
from pathlib import Path
from cli_eduardo.use_cases.gateway import AgentRunner
from cli_eduardo.use_cases.summarize_report import summarize_report

def run_summarize(
    report_path: Path,
    model_id: str,
    open_findings: int,
    runner: AgentRunner,
    *,
    encoding: str = "utf-8-sig",
) -> int:
    try:
        text = report_path.read_text(encoding=encoding)
    except FileNotFoundError:
        print(f"error: not found: {report_path}", file=sys.stderr)
        return 1
    except PermissionError:
        print(f"error: cannot read: {report_path}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory() as tmpdir:
        sandbox = Path(tmpdir)
        (sandbox / "report.txt").write_text(text, encoding="utf-8")
        try:
            summary = summarize_report(sandbox, model_id, open_findings, runner)
        except (RuntimeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1

    print(f"Model: {summary.model_id}  Open findings: {summary.open_findings}")
    print(summary.executive_text)
    return 0
```

### 4. Register the subcommand (`src/cli_eduardo/cli.py`)

Wire the argument parser to the adapter inside `main()`:

```python
# In main(), after the existing "validate" block:
p = subparsers.add_parser("summarize", help="Generate executive summary of a report")
p.add_argument("report", type=Path)
p.add_argument("--model-id", required=True)
p.add_argument("--open-findings", type=int, required=True)
p.add_argument("--gateway", choices=["claude", "azure"], default="claude")
p.set_defaults(func=_run_summarize)

# Add the handler function:
def _run_summarize(args: argparse.Namespace) -> int:
    from cli_eduardo.adapters.summarize import run_summarize
    return run_summarize(
        report_path=args.report,
        model_id=args.model_id,
        open_findings=args.open_findings,
        runner=_make_runner(args.gateway),
    )
```

### 5. Tests (`tests/`)

Mirror the `src/` structure. Every use case needs:

- **Known-answer cases** — hand-compute the expected output and assert exactly.
- **Failure paths** — runner failure, malformed output, file not found.
- **Minimum-privilege assertion** — confirm `allowed_tools=["Read"]` (or whatever
  the documented minimum is) is what actually gets passed.

```python
# tests/use_cases/test_summarize_report.py
def test_returns_summary(tmp_path):
    runner = MagicMock()
    runner.run.return_value = AgentResult(success=True, output="Key risk: model drift.")
    result = summarize_report(tmp_path, "LGD-001", 3, runner)
    assert result.model_id == "LGD-001"
    assert result.open_findings == 3
    assert "Key risk" in result.executive_text

def test_runner_failure_raises(tmp_path):
    runner = MagicMock()
    runner.run.return_value = AgentResult(success=False, output="timeout")
    with pytest.raises(RuntimeError, match="Agent failed"):
        summarize_report(tmp_path, "LGD-001", 0, runner)
```

Infrastructure tests (gateway classes) must mock the SDK client — never call the
real endpoint in unit tests. Use `@pytest.mark.agent` for opt-in integration tests
that hit the real runtime; these are excluded from CI.

---

## Architecture

```
src/cli_eduardo/
├── domain/           Pure business rules. No I/O. No third-party imports.
├── use_cases/        Orchestration logic. Imports domain/ and gateway Protocol only.
│   └── gateway.py    AgentRunner Protocol — implemented by both gateways.
├── adapters/         File I/O, sandbox setup, stdout formatting.
└── infrastructure/   SDK calls, network I/O, SP auth. The only layer allowed to
                      import anthropic / openai / azure.identity.
```

**Dependency rule:** each layer may only import from layers listed to its left.
`domain` ← `use_cases` ← `adapters` ← `infrastructure` ← `cli.py` (composition root).
A PR that makes `domain/` or `use_cases/` import from `infrastructure/` is wrong by
construction — restructure before merging.

The `AgentRunner` protocol (`use_cases/gateway.py`) is the seam between business logic
and LLM I/O. `ClaudeGateway` and `AzureOpenAIGateway` are interchangeable at runtime;
a `MagicMock()` satisfying the protocol is used in all unit tests.
