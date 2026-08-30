"""Claude Code emitter: name/description frontmatter + model-tier body note."""

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
    body: |
      ### Step 1 -- Check status

      ```python
      print("hello")
      ```
    harnesses:
      claude_code: {}
    """
)


def _load_type_a(tmp_path: Path):
    p = tmp_path / "spec.yaml"
    p.write_text(TYPE_A_SPEC, encoding="utf-8")
    return load_spec(p)


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


def test_cc_type_a_renders_body_verbatim(tmp_path: Path) -> None:
    out = generate(_load_type_a(tmp_path), "claude_code")
    assert "### Step 1 -- Check status" in out
    assert '```python\nprint("hello")\n```' in out
    assert "Wraps" not in out
