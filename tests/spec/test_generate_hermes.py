"""Hermes emitter: required frontmatter + sections, model_tier omitted."""

from __future__ import annotations

import textwrap
from pathlib import Path

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

SPEC = "specs/trapezia-commercial-policy-check.yaml"

TYPE_A_SPEC = textwrap.dedent(
    """
    name: connect-example
    spec_version: 0
    version: 1.0.0
    description: Link an example account.
    invokes: []
    guardrails:
      - id: always-live
        text: Always call the status check live.
    body: |
      ### Step 1 -- Check status

      ```python
      print("hello")
      ```
    harnesses:
      hermes: {category: connectors}
    """
)


def _load_type_a(tmp_path: Path):
    p = tmp_path / "spec.yaml"
    p.write_text(TYPE_A_SPEC, encoding="utf-8")
    return load_spec(p)


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


def test_hermes_type_a_renders_body_verbatim(tmp_path: Path) -> None:
    """A type-A skill's ``body`` renders un-collapsed (unlike ``usage``)."""
    out = generate(_load_type_a(tmp_path), "hermes")
    assert "### Step 1 -- Check status" in out
    assert '```python\nprint("hello")\n```' in out
    # No mcp/cli invoke -> no auto-generated wraps/run-script sections.
    assert "This skill wraps" not in out
    assert "Run the bundled script(s)" not in out
