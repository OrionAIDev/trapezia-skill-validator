#!/usr/bin/env python3
"""Extract declarations-page fields from raw commercial policy text.

Deterministic and stdlib-only: regex-scans a policy document's declarations
page for the subset of ``PolicyDocument`` fields (per the Trapezia
commercial policy-check engine's input schema) that a page-level scan can
reliably recover -- policy number, carrier, named insured, policy period,
GL occurrence/aggregate limits, and the forms schedule. Prints a
``{"policy": {...}}`` JSON object shaped to drop straight into a
``PolicyCheckingRun`` payload. Fields not found in the text are omitted,
never guessed. No network, no LLM.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# Same ISO/ACORD form matching as policy-form-lister's list_forms.py, but
# normalized per PolicyDocument.forms_schedule's documented convention:
# uppercase, spaces stripped, edition suffix dropped (e.g. "CG0001").
_ISO_FORM = re.compile(r"\b([A-Z]{2})\s+(\d{2})\s+(\d{2})(?:\s+\d{2})*\b")
_ACORD_FORM = re.compile(r"\bACORD\s+(\d{1,3})\b")
_LINE_PREFIXES = frozenset(
    {"CG", "CP", "IL", "CA", "WC", "BP", "CR", "CU", "GL", "CM", "MP"}
)

_POLICY_NUMBER = re.compile(r"Policy\s+Number:\s*(\S+)", re.IGNORECASE)
_CARRIER = re.compile(r"Carrier:\s*(.+)", re.IGNORECASE)
_NAMED_INSURED = re.compile(r"Named\s+Insured:\s*(.+)", re.IGNORECASE)
_POLICY_PERIOD = re.compile(
    r"Policy\s+Period:\s*(\d{2})/(\d{2})/(\d{4})\s*(?:to|-|–)\s*"
    r"(\d{2})/(\d{2})/(\d{4})",
    re.IGNORECASE,
)
_GL_EACH_OCCURRENCE = re.compile(
    r"Each\s+Occurrence\s+Limit:\s*\$?([\d,]+)", re.IGNORECASE
)
_GL_GENERAL_AGGREGATE = re.compile(
    r"General\s+Aggregate\s+Limit:\s*\$?([\d,]+)", re.IGNORECASE
)


def _iso_date(mm: str, dd: str, yyyy: str) -> str:
    """Normalize an ``MM/DD/YYYY`` capture to ``YYYY-MM-DD``."""
    return f"{yyyy}-{mm}-{dd}"


def _forms_schedule(text: str) -> list[str]:
    """Return the sorted unique form numbers found in ``text``.

    Args:
        text: policy document text.

    Returns:
        Sorted list of form ids normalized per ``PolicyDocument`` convention
        (uppercase, spaces stripped, edition suffix dropped).
    """
    forms: set[str] = set()
    for m in _ISO_FORM.finditer(text):
        prefix = m.group(1)
        if prefix in _LINE_PREFIXES:
            forms.add(f"{prefix}{m.group(2)}{m.group(3)}")
    for m in _ACORD_FORM.finditer(text):
        forms.add(f"ACORD{m.group(1)}")
    return sorted(forms)


def extract_declarations(text: str) -> dict[str, Any]:
    """Extract the recoverable ``PolicyDocument`` fields from ``text``.

    Args:
        text: raw policy declarations-page text.

    Returns:
        A ``policy`` dict containing only the fields actually found in
        ``text``; absent fields are omitted, never guessed.
    """
    policy: dict[str, Any] = {}

    if m := _POLICY_NUMBER.search(text):
        policy["policy_number"] = m.group(1)
    if m := _CARRIER.search(text):
        policy["carrier_name"] = m.group(1).strip()
    if m := _NAMED_INSURED.search(text):
        policy["named_insureds"] = [m.group(1).strip()]
    if m := _POLICY_PERIOD.search(text):
        eff_mm, eff_dd, eff_yyyy, exp_mm, exp_dd, exp_yyyy = m.groups()
        policy["policy_effective_date"] = _iso_date(eff_mm, eff_dd, eff_yyyy)
        policy["policy_expiration_date"] = _iso_date(exp_mm, exp_dd, exp_yyyy)
    if m := _GL_EACH_OCCURRENCE.search(text):
        policy["gl_each_occurrence"] = int(m.group(1).replace(",", ""))
    if m := _GL_GENERAL_AGGREGATE.search(text):
        policy["gl_general_aggregate"] = int(m.group(1).replace(",", ""))
    forms = _forms_schedule(text)
    if forms:
        policy["forms_schedule"] = forms

    return policy


def main(argv: list[str] | None = None) -> int:
    """Extract and print declarations fields from the ``--input`` document.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 2 if the input file is missing).
    """
    parser = argparse.ArgumentParser(
        description="Extract declarations-page fields from a policy document."
    )
    parser.add_argument(
        "--input", required=True, type=Path, help="path to the policy text file"
    )
    args = parser.parse_args(argv)
    if not args.input.is_file():
        sys.stderr.write(f"input not found: {args.input}\n")
        return 2
    policy = extract_declarations(args.input.read_text(encoding="utf-8"))
    json.dump({"policy": policy}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
