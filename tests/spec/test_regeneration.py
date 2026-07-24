"""Committed generated/** must match a fresh generation of every spec (no drift).

Covers all three per-harness outputs for each spec: the SKILL.md wrapper, the
copied bundle files (byte-exact), and the hermes-only mcp_servers snippet.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from trapezia_skill_spec.generate import HARNESSES, generate, generate_mcp_registration
from trapezia_skill_spec.schema import load_spec

REPO = Path(__file__).resolve().parents[2]
SPECS = sorted((REPO / "specs").glob("*.yaml"))
_STALE = "stale — run `python -m trapezia_skill_spec.cli <spec> --all` and commit."


def _ids(p: Path) -> str:
    return p.stem


@pytest.mark.parametrize("spec_path", SPECS, ids=_ids)
def test_committed_skill_md_matches(spec_path: Path) -> None:
    spec = load_spec(spec_path)
    for harness in HARNESSES:
        committed = REPO / "generated" / harness / spec.name / "SKILL.md"
        assert committed.is_file(), f"missing committed output: {committed}"
        assert committed.read_text(encoding="utf-8") == generate(spec, harness), f"{committed} {_STALE}"


@pytest.mark.parametrize("spec_path", SPECS, ids=_ids)
def test_committed_bundle_matches(spec_path: Path) -> None:
    spec = load_spec(spec_path)
    src_root = REPO / "skills" / spec.name
    for harness in HARNESSES:
        for rel in spec.bundle:
            committed = REPO / "generated" / harness / spec.name / rel
            assert committed.is_file(), f"missing committed bundle file: {committed}"
            assert committed.read_bytes() == (src_root / rel).read_bytes(), f"{committed} {_STALE}"


@pytest.mark.parametrize("spec_path", SPECS, ids=_ids)
def test_committed_mcp_snippet_matches(spec_path: Path) -> None:
    spec = load_spec(spec_path)
    snip = REPO / "generated" / "hermes" / spec.name / "mcp_servers.snippet.yaml"
    reg = generate_mcp_registration(spec)
    if reg is None:
        assert not snip.exists(), f"unexpected snippet for cli-only skill: {snip}"
    else:
        assert snip.is_file(), f"missing committed snippet: {snip}"
        assert snip.read_text(encoding="utf-8") == reg, f"{snip} {_STALE}"
