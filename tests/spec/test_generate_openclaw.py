"""OpenClaw emitter: name/description frontmatter + model-tier body note."""

from __future__ import annotations

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

SPEC = "specs/trapezia-commercial-policy-check.yaml"


def test_openclaw_frontmatter_is_name_description_only() -> None:
    out = generate(load_spec(SPEC), "openclaw")
    head = out.split("---\n", 2)[1]  # frontmatter block
    assert "name: trapezia-commercial-policy-check" in head
    assert "description:" in head
    assert "version:" not in head  # OpenClaw frontmatter is name+description


def test_openclaw_surfaces_model_tier_as_note() -> None:
    out = generate(load_spec(SPEC), "openclaw")
    assert "Model tier: sonnet" in out


def test_openclaw_carries_tools_and_guardrails() -> None:
    out = generate(load_spec(SPEC), "openclaw")
    assert "run_policy_check" in out
    assert "surface the error verbatim" in out
