"""Claude Code emitter: name/description frontmatter + model-tier body note."""

from __future__ import annotations

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

SPEC = "specs/trapezia-commercial-policy-check.yaml"


def test_cc_frontmatter_is_name_description_only() -> None:
    out = generate(load_spec(SPEC), "claude_code")
    head = out.split("---\n", 2)[1]
    assert "name: trapezia-commercial-policy-check" in head
    assert "description:" in head
    assert "version:" not in head


def test_cc_surfaces_model_tier_as_note() -> None:
    out = generate(load_spec(SPEC), "claude_code")
    assert "Model tier: sonnet" in out


def test_cc_carries_tools_and_guardrails() -> None:
    out = generate(load_spec(SPEC), "claude_code")
    assert "get_run_report" in out
    assert "commercial (business) insurance policies only" in out
