"""Command-line entry point for the canonical-spec generator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generate import HARNESSES, generate
from .schema import load_spec


def _write_output(text: str, out_dir: Path, harness: str, name: str) -> Path:
    dest = out_dir / harness / name / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    """Generate per-harness SKILL.md wrappers from a canonical spec.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 2 on usage error).
    """
    parser = argparse.ArgumentParser(
        prog="trapezia-skill-gen",
        description="Generate per-harness SKILL.md wrappers from a canonical spec.",
    )
    parser.add_argument("spec", type=Path, help="path to the canonical spec YAML")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--harness", choices=HARNESSES, help="emit one harness to stdout")
    group.add_argument("--all", action="store_true", help="emit all harnesses to --out")
    parser.add_argument(
        "--out", type=Path, default=Path("generated"), help="output root for --all (default: generated/)"
    )
    args = parser.parse_args(argv)

    spec = load_spec(args.spec)
    if args.harness:
        sys.stdout.write(generate(spec, args.harness))
        return 0
    for harness in HARNESSES:
        dest = _write_output(generate(spec, harness), args.out, harness, spec.name)
        sys.stdout.write(f"wrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
