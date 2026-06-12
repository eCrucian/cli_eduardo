# CLAUDE.md — Model Validation Orchestrator

## 1. What This Is

CLI-only, MCP-enabled orchestration system automating model validation (Market Risk,
Liquidity, Credit Risk Capital, BDPO) and management workflows, running inside a
restricted corporate Windows environment.

**Hard constraints (never violate):**
- **No web frontend. No UI components. No HTML output.** All output goes to stdout
  (plain text, DOS-terminal friendly) or plain-text automated dispatches (e.g., daily
  digest emails).
- **LLM traffic only through sanctioned channels.** Exactly two are approved:
  (1) the corporate Azure OpenAI endpoint, and (2) the embedded Claude Code / Agent
  SDK runtime (see section 9). No other LLM endpoint, ever. Risk documentation,
  formulas, model code, and analyst reports go only through these channels.
  <!-- TODO: confirm with security/compliance which endpoint the Claude channel uses
       (Anthropic API direct, Bedrock/Vertex, or corporate gateway via ANTHROPIC_BASE_URL) -->.
- **No hardcoded credentials.** Auth is Service Principal / Client Secret, injected
  from the environment. <!-- TODO: list exact env var names, e.g. AZ_TENANT_ID, AZ_CLIENT_ID, AZ_CLIENT_SECRET -->

## 2. Commands

<!-- TODO: verify these match the repo; the agent should run them before claiming work is done -->
```bash
pytest -q                          # run test suite
pytest --cov=src --cov-fail-under=90   # coverage gate (use cases must be fully covered)
mypy --strict src/                 # type check — must pass with zero errors
ruff check src/ tests/             # lint
bandit -r src/                     # SAST — must report no medium/high findings
radon cc src/ -n C                 # complexity — no function may rate C or worse (CC > 10); target A/B
python -m cli_eduardo.cli --help   # smoke-test the CLI entrypoint
```

Environment: Python 3.12, dependencies via `pip` (`requirements.txt` / `requirements-dev.txt`).
Note: package installs may require the corporate proxy/index — ask before adding new
dependencies; prefer the standard library.

## 3. Architecture (Clean Architecture, strict dependency rule)

Outer layers depend on inner layers. Inner layers know nothing about outer layers.
A change that makes `domain/` import from `adapters/` or `infrastructure/` is wrong
by definition — stop and restructure.

```text
src/
├── domain/          # Enterprise business rules: Risk Findings, Validation Constraints. Pure Python, zero I/O, zero third-party imports.
├── use_cases/       # Application logic: ValidateLGDReport, SummarizeTeamsFeed. Depends only on domain/.
├── adapters/        # Controllers & gateways: CLI parser, MCP server implementation.
└── infrastructure/  # External I/O: UNC paths, Azure OpenAI HTTP, SharePoint APIs. The only layer allowed to use `Any` (untyped corporate APIs), isolated behind typed interfaces.
tests/               # Pytest suite mirroring src/ structure.
```

## 4. Agent Behavior

### 4.1 Think before coding
- State your interpretation of the task before implementing. If a request is ambiguous
  (e.g., which regulatory framework, which report format, which network share), ask —
  do not pick an interpretation silently.
- Never invent regulatory thresholds, BCB rule numbers, statistical cutoffs, or model
  parameters. If a value isn't in the codebase or the request, flag it as
  `# TODO(human): confirm value` and say so in your summary.
- Surface tradeoffs and inconsistencies instead of papering over them.

### 4.2 Simplicity first
- Implement exactly what was asked. No speculative configurability, no abstractions
  for single-use code, no handling of impossible scenarios.
- Prefer pure, stateless functions in `domain/` over class hierarchies. Add a class
  only when state or polymorphism is genuinely required.
- Functions stay small and flat: if `radon` rates a function C or worse, decompose it.

### 4.3 Surgical changes
- Touch only files required by the task. Every changed line must trace to the request.
- Do not reformat, rename, or "clean up" code orthogonal to the task. If you notice
  dead code or problems you didn't cause, mention them — don't fix them unasked.
- Never delete or weaken an existing test to make a change pass.

### 4.4 Goal-driven execution
- A task is done only when: tests pass, `mypy --strict` is clean, `ruff` and `bandit`
  are clean, and new logic has tests covering its edge cases (boundary values, empty
  inputs, malformed analyst reports, network failures).
- Run the verification commands yourself; don't claim success without evidence.

## 5. Code Standards

- Strict type hints everywhere (`mypy --strict`). `Any` only at the corporate-API
  boundary in `infrastructure/`, wrapped immediately in typed models.
- Numerical correctness: use `decimal.Decimal` for monetary/capital figures; never
  compare floats with `==` — use explicit tolerances. Seed all randomness in tests.
- Errors: catch specific exceptions (`PermissionError`, `FileNotFoundError`,
  `TimeoutError`); never bare `except:`. Log errors to **stderr** with enough context
  to locate the failing share/file; results go to stdout.
- DRY: shared logic becomes a pure domain function, not copy-paste across use cases.

## 6. Windows / Corporate Environment

- Use `pathlib.PureWindowsPath` / `Path` for all paths; UNC paths like
  `\\server\share\modelos` are the norm. Never assume POSIX (`/tmp`, `os.fork`,
  POSIX signals).
- Network shares are slow and flaky: wrap I/O with explicit timeouts and retries
  (bounded, logged); degrade gracefully, never hang.
- Encodings: never rely on the platform default. Read corporate files with an
  explicit `encoding=` (expect `cp1252` or `utf-8-sig`); write UTF-8.
- SharePoint-synced folders may hold lock/temp files (`~$*.xlsx`) — skip them.

## 7. Domain Notes: Model Validation

- Validation use cases must check statistical adherence, stress-testing coverage,
  and regulatory alignment (BCB guidelines). When extracting findings from analyst
  reports, prefer "flagged for review" over silent acceptance when evidence is weak.
- Executive summaries: concise, plain text, action-oriented — lead with methodological
  deviations and open findings, not boilerplate.
- Tests for quantitative logic must include known-answer cases (hand-computed
  expected values), not just self-referential assertions.

## 8. CI/CD

- Keep `infrastructure/` components injectable/mockable so the suite runs in GitHub
  Actions without network access to corporate shares.
- Any new external dependency or endpoint must be mockable in tests by construction.
- CI must never invoke the embedded agent runtime (section 9) against real corporate
  data; agent gateways are mocked in tests like any other external service.

## 9. Embedded Claude Code Runtime (Agent SDK)

The CLI invokes Claude Code programmatically at runtime as a sanctioned LLM channel.
This is an architectural decision; treat it like any other external service.

**Placement.** All invocation lives in `infrastructure/` behind a typed gateway
interface (e.g., `AgentRunner` protocol) defined in `use_cases/` boundaries.
Domain and use-case code never imports SDK packages or spawns subprocesses.
The Azure OpenAI gateway and the Claude gateway implement the same interface and
must be interchangeable (LSP) — a use case must not know or care which one runs.

**Invocation rules (non-negotiable):**
- Always headless: `claude -p "<prompt>"` (or the Python Agent SDK equivalent).
  Never spawn an interactive session from the orchestrator.
- Always `--output-format json` (or SDK message objects). Parse the result status
  before trusting the payload; a non-success status is an error path, never silently
  swallowed.
- Always pass an explicit `--allowedTools` whitelist — the minimum set the task
  needs. Default for analysis tasks: `"Read"` only. Grant `Edit`/`Bash` only for
  tasks that explicitly require them, and document why in the use case.
- Always scope the working directory (`--cwd`) to a dedicated sandbox folder
  containing only the files the task needs. Never run against `\\server\share`
  roots or folders with documents beyond the task's scope.
- `--dangerously-skip-permissions` is forbidden outside an isolated sandbox
  directory with a read-only or disposable copy of inputs.
- Every invocation has a hard timeout and bounded retries; on breach, log to
  stderr and fail the step — never hang the pipeline.
- Budgets: enforce per-step and per-run token/cost ceilings in config (not in
  prompts). Exceeding a ceiling halts the run and logs the breach.

**Credentials.** The agent runtime authenticates via environment-injected
credentials only (e.g., `ANTHROPIC_API_KEY` or corporate gateway equivalent),
same hygiene as the Azure Service Principal. Never written to disk, never logged.
<!-- TODO: confirm auth mechanism and whether ANTHROPIC_BASE_URL points to a corporate gateway -->

**Prompt discipline.** Prompts sent to the agent include only the minimum
necessary excerpt of internal documents, not whole shares. Prefer passing file
paths inside the sandboxed `--cwd` over inlining large documents.

**Testing.** The Claude gateway is mocked in all unit tests. Integration tests
that hit the real runtime are opt-in (marker `@pytest.mark.agent`), excluded
from CI, and run only against synthetic fixtures — never real model documentation.

