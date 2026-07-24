#!/usr/bin/env python3
"""List insurance form numbers found in a policy text document.

Deterministic and stdlib-only: reads a policy document as text and extracts ISO
commercial-lines form numbers (e.g. ``CG 00 01``) and ACORD form numbers
(e.g. ``ACORD 25``), printing the sorted unique set as JSON. No network, no LLM.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# ISO commercial form: a two-letter line prefix + two or more 2-digit groups
# (an edition suffix like " 04 13" may follow; only the base id is reported).
_ISO = re.compile(r"\b([A-Z]{2})\s+(\d{2})\s+(\d{2})(?:\s+\d{2})*\b")
_ACORD = re.compile(r"\bACORD\s+(\d{1,3})\b")

# Recognized ISO commercial-lines prefixes (gates the 2-letter match so arbitrary
# capitalized pairs followed by digits are not mistaken for form numbers).
_LINE_PREFIXES = frozenset(
    {"CG", "CP", "IL", "CA", "WC", "BP", "CR", "CU", "GL", "CM", "MP"}
)


def extract_forms(text: str) -> list[str]:
    """Return the sorted unique insurance form numbers found in ``text``.

    Args:
        text: policy document text.

    Returns:
        Sorted list of normalized form ids (e.g. ``["ACORD 25", "CG 00 01"]``).
    """
    forms: set[str] = set()
    for m in _ISO.finditer(text):
        prefix = m.group(1)
        if prefix in _LINE_PREFIXES:
            forms.add(f"{prefix} {m.group(2)} {m.group(3)}")
    for m in _ACORD.finditer(text):
        forms.add(f"ACORD {m.group(1)}")
    return sorted(forms)


def main(argv: list[str] | None = None) -> int:
    """Extract and print the form numbers in the ``--input`` policy document.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 2 if the input file is missing).
    """
    parser = argparse.ArgumentParser(
        description="List insurance form numbers in a policy document."
    )
    parser.add_argument(
        "--input", required=True, type=Path, help="path to the policy text file"
    )
    args = parser.parse_args(argv)
    if not args.input.is_file():
        sys.stderr.write(f"input not found: {args.input}\n")
        return 2
    forms = extract_forms(args.input.read_text(encoding="utf-8"))
    json.dump({"forms": forms, "count": len(forms)}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
