"""Command-line entry point for the canonical-spec generator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generate import HARNESSES, generate, generate_mcp_registration
from .schema import CanonicalSpec, load_spec


def _write_output(text: str, out_dir: Path, harness: str, name: str) -> Path:
    dest = out_dir / harness / name / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def _assets_root(spec_path: Path, name: str) -> Path:
    """The authored bundle-source dir: ``<repo>/skills/<name>/`` beside ``specs/``."""
    return spec_path.resolve().parent.parent / "skills" / name


def _copy_bundle(spec: CanonicalSpec, spec_path: Path, out_dir: Path, harness: str) -> list[Path]:
    """Copy each bundle path verbatim into ``out/<harness>/<name>/`` and return them."""
    src_root = _assets_root(spec_path, spec.name)
    dest_root = out_dir / harness / spec.name
    written: list[Path] = []
    for rel in spec.bundle:
        src = src_root / rel
        dest = dest_root / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(src.read_bytes())
        written.append(dest)
    return written


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
    registration = generate_mcp_registration(spec)
    for harness in HARNESSES:
        dest = _write_output(generate(spec, harness), args.out, harness, spec.name)
        sys.stdout.write(f"wrote {dest}\n")
        for copied in _copy_bundle(spec, args.spec, args.out, harness):
            sys.stdout.write(f"wrote {copied}\n")
        if harness == "hermes" and registration is not None:
            snip = args.out / harness / spec.name / "mcp_servers.snippet.yaml"
            snip.write_text(registration, encoding="utf-8")
            sys.stdout.write(f"wrote {snip}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
