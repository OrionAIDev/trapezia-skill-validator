"""Committed generated/** must match a fresh generation of the spec (no drift)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trapezia_skill_spec.generate import HARNESSES, generate
from trapezia_skill_spec.schema import load_spec

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "specs" / "trapezia-commercial-policy-check.yaml"


@pytest.mark.parametrize("harness", HARNESSES)
def test_committed_output_matches_generation(harness: str) -> None:
    spec = load_spec(SPEC)
    committed = REPO / "generated" / harness / spec.name / "SKILL.md"
    assert committed.is_file(), f"missing committed output: {committed}"
    expected = generate(spec, harness)
    actual = committed.read_text(encoding="utf-8")
    assert actual == expected, (
        f"{committed} is stale — run "
        f"`python -m trapezia_skill_spec.cli {SPEC.relative_to(REPO)} --all` and commit."
    )
