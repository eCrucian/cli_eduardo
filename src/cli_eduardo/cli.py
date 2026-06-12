from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from pathlib import Path
from typing import cast

from cli_eduardo.use_cases.gateway import AgentRunner


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="cli_eduardo",
        description="Model Validation Orchestrator",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    p = subparsers.add_parser("validate", help="Extract findings from a model validation report")
    p.add_argument("report", type=Path, help="Path to the report file")
    p.add_argument("--model-id", required=True, help="Model identifier")
    p.add_argument(
        "--gateway",
        choices=["claude", "azure"],
        default="claude",
        help="LLM gateway to use (default: claude)",
    )
    p.add_argument(
        "--encoding",
        default="utf-8-sig",
        help="Report file encoding (default: utf-8-sig; use cp1252 for legacy files)",
    )
    p.set_defaults(func=_run_validate)

    args = parser.parse_args()
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        sys.exit(0)
    sys.exit(cast(Callable[[argparse.Namespace], int], func)(args))


def _make_runner(gateway: str) -> AgentRunner:
    if gateway == "claude":
        from cli_eduardo.infrastructure.claude_gateway import ClaudeGateway

        return ClaudeGateway()
    from cli_eduardo.infrastructure.azure_openai_gateway import AzureOpenAIGateway

    return AzureOpenAIGateway(
        endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],  # TODO(human): confirm env var name
        deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],  # TODO(human): confirm env var name
    )


def _run_validate(args: argparse.Namespace) -> int:
    from cli_eduardo.adapters.validate import run_validate

    runner = _make_runner(args.gateway)
    return run_validate(
        report_path=args.report,
        model_id=args.model_id,
        runner=runner,
        encoding=args.encoding,
    )


if __name__ == "__main__":
    main()
