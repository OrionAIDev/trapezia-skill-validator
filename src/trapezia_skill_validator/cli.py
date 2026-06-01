"""Command-line entrypoint for the validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import render_markdown, run_audit


def main(argv: list[str] | None = None) -> int:
    """Audit a skill directory and print a report.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 if the audit passed, 1 if any check FAILed.
    """
    parser = argparse.ArgumentParser(
        prog="trapezia-skill-validator",
        description="Run deterministic conformance checks against a skill directory.",
    )
    parser.add_argument("skill_path", type=Path, help="path to the skill directory")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    report = run_audit(args.skill_path)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_markdown(report), end="")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
