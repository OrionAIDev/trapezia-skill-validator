"""Command-line entrypoint for the validator."""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

from .runner import render_markdown, run_audit


def _safe_print(text: str) -> None:
    """Print text to stdout, falling back to UTF-8 binary write on narrow consoles.

    On Windows the default console encoding is often cp1252, which cannot
    represent the emoji characters used in the markdown report.  When stdout
    has an underlying binary buffer and its current encoding cannot handle the
    text, write directly to the buffer as UTF-8.
    """
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except (UnicodeEncodeError, UnicodeTranslateError):
        buf = getattr(sys.stdout, "buffer", None)
        if buf is not None:
            buf.write(text.encode("utf-8", errors="replace"))
            buf.flush()
        else:
            sys.stdout.write(text.encode("utf-8", errors="replace").decode("ascii", errors="replace"))
            sys.stdout.flush()


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
        _safe_print(json.dumps(report.to_dict(), indent=2) + "\n")
    else:
        _safe_print(render_markdown(report))
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
