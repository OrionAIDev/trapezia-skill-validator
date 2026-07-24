"""Hermes emitter: required frontmatter + sections, model_tier omitted."""

from __future__ import annotations

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

SPEC = "specs/trapezia-commercial-policy-check.yaml"


def test_hermes_frontmatter_required_fields() -> None:
    out = generate(load_spec(SPEC), "hermes")
    assert out.startswith("---\n")
    assert "name: trapezia-commercial-policy-check" in out
    assert "version: 0.1.0" in out
    assert "description:" in out


def test_hermes_lists_required_env() -> None:
    out = generate(load_spec(SPEC), "hermes")
    assert "required_environment_variables:" in out
    assert "- GOOGLE_API_KEY" in out
    # Direct-Anthropic is deprecated (FR-7.5) — must not leak into the wrapper.
    assert "ANTHROPIC_API_KEY" not in out


def test_hermes_has_standard_sections() -> None:
    out = generate(load_spec(SPEC), "hermes")
    for section in ("## When to Use", "## Procedure", "## Pitfalls", "## Verification"):
        assert section in out


def test_hermes_omits_model_tier() -> None:
    # OQ-3: Hermes does not honor per-skill model tiers -> never emitted.
    out = generate(load_spec(SPEC), "hermes")
    assert "model_tier" not in out
    assert "Model tier" not in out


def test_hermes_carries_guardrails_verbatim() -> None:
    out = generate(load_spec(SPEC), "hermes")
    assert "surface the error verbatim" in out
