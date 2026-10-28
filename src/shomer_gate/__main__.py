"""Command-line entry point.

Subcommands:

- ``shomer check "<prompt>"``: evaluate one prompt and print the decision.
- ``shomer eval [--data PATH]``: score the baseline against ground truth.
- ``shomer serve``: start the FastAPI app (requires the ``api`` extra).

The ``check`` and ``eval`` paths import only the zero-dependency engine, so they
run on a clean interpreter with nothing installed.
"""

from __future__ import annotations

import argparse
import json
import sys

from shomer_gate import __version__
from shomer_gate.config import get_settings
from shomer_gate.guardrail.engine import GuardrailEngine
from shomer_gate.metrics.evaluator import evaluate, load_ground_truth


def _build_engine() -> GuardrailEngine:
    settings = get_settings()
    return GuardrailEngine(
        block_threshold=settings.block_threshold,
        review_threshold=settings.review_threshold,
    )


def _cmd_check(args: argparse.Namespace) -> int:
    decision = _build_engine().evaluate(args.prompt)
    print(json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))
    return 0 if decision.verdict.value != "block" else 3


def _cmd_eval(args: argparse.Namespace) -> int:
    settings = get_settings()
    path = args.data or settings.ground_truth_path
    cases = load_ground_truth(path)
    report = evaluate(cases, _build_engine())
    print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    # Gate semantics for CI: a weak baseline fails the command.
    if report.recall < args.min_recall or report.false_positive_rate > args.max_fpr:
        print(
            f"\nGATE FAILED: recall={report.recall:.3f} (min {args.min_recall}) "
            f"fpr={report.false_positive_rate:.3f} (max {args.max_fpr})",
            file=sys.stderr,
        )
        return 1
    print(
        f"\nGATE PASSED: recall={report.recall:.3f} fpr={report.false_positive_rate:.3f} "
        f"coverage={report.coverage:.3f}"
    )
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ModuleNotFoundError:
        print("The 'api' extra is required to serve. Install: pip install -e '.[api]'",
              file=sys.stderr)
        return 2
    settings = get_settings()
    uvicorn.run(
        "shomer_gate.api.app:app",
        host=args.host or settings.host,
        port=args.port or settings.port,
        reload=args.reload,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shomer", description="shomer-gate CLI")
    parser.add_argument("--version", action="version", version=f"shomer-gate {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="evaluate a single prompt")
    p_check.add_argument("prompt")
    p_check.set_defaults(func=_cmd_check)

    p_eval = sub.add_parser("eval", help="score the baseline against ground truth")
    p_eval.add_argument("--data", default=None, help="path to ground_truth.json")
    p_eval.add_argument("--min-recall", type=float, default=0.80)
    p_eval.add_argument("--max-fpr", type=float, default=0.05)
    p_eval.set_defaults(func=_cmd_eval)

    p_serve = sub.add_parser("serve", help="start the API (needs the api extra)")
    p_serve.add_argument("--host", default=None)
    p_serve.add_argument("--port", type=int, default=None)
    p_serve.add_argument("--reload", action="store_true")
    p_serve.set_defaults(func=_cmd_serve)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
