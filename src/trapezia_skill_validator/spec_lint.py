"""Additive canonical-spec linter.

Separate from the skill-directory audit (``runner.run_audit`` / ``registry.CHECKS``)
so the existing check API consumed by skill-template self-test and
trapezia-skill-audit stays untouched. Exposed via the ``trapezia-canonical-spec-lint``
console script.
"""

from __future__ import annotations

import sys
from pathlib import Path

from trapezia_skill_spec.schema import SpecError, load_spec

from .models import CheckResult, Severity, Status


def lint_spec(path: str | Path) -> list[CheckResult]:
    """Lint a canonical spec, returning one CheckResult per rule.

    Args:
        path: path to the canonical spec YAML.

    Returns:
        A list of CheckResult (never raises for spec content problems — a
        malformed spec becomes a FAIL result).
    """
    results: list[CheckResult] = []
    try:
        spec = load_spec(path)
    except SpecError as exc:
        return [
            CheckResult(
                id="spec.valid",
                status=Status.FAIL,
                severity=Severity.CRITICAL,
                message=f"spec invalid: {exc}",
                min_level=0,
            )
        ]

    results.append(
        CheckResult("spec.valid", Status.PASS, Severity.CRITICAL, "spec parses and validates", 0)
    )
    if spec.guardrails:
        results.append(
            CheckResult("spec.guardrails", Status.PASS, Severity.MEDIUM, "guardrails present", 0)
        )
    else:
        results.append(
            CheckResult(
                "spec.guardrails",
                Status.WARN,
                Severity.MEDIUM,
                "no guardrails declared — capability ships with no adapter-carried guardrail prose",
                0,
            )
        )
    return results


def main(argv: list[str] | None = None) -> int:
    """Lint a canonical spec and print results.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        0 if no FAIL results, else 1.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="trapezia-canonical-spec-lint",
        description="Lint a Trapezia canonical skill-spec YAML.",
    )
    parser.add_argument("spec_path", type=Path, help="path to the canonical spec YAML")
    args = parser.parse_args(argv)

    results = lint_spec(args.spec_path)
    icon = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL"}
    for r in results:
        sys.stdout.write(f"[{icon[r.status]}] {r.id}: {r.message}\n")
    return 0 if all(r.status is not Status.FAIL for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
