"""Tests for the canonical-spec schema and loader."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from trapezia_skill_spec.schema import CanonicalSpec, SpecError, load_spec

VALID = textwrap.dedent(
    """
    name: trapezia-commercial-policy-check
    spec_version: 0
    version: 0.1.0
    description: Run a commercial policy check.
    triggers: ["policy check"]
    invokes:
      - kind: mcp
        server: trapezia-commercial-policy-check
        transport: stdio
        launch: python -m trapezia_commercial_policy_check.mcp_server
        tools: [health, run_policy_check]
        required_env: [ANTHROPIC_API_KEY]
    guardrails:
      - id: service-unreachable
        text: Surface errors verbatim.
    model_tier: sonnet
    harnesses:
      hermes: {}
      openclaw: {}
      claude_code: {}
    """
)


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "spec.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_load_valid_spec(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, VALID))
    assert isinstance(spec, CanonicalSpec)
    assert spec.name == "trapezia-commercial-policy-check"
    assert spec.spec_version == 0
    assert spec.invokes[0].tools == ["health", "run_policy_check"]
    assert spec.invokes[0].required_env == ["ANTHROPIC_API_KEY"]
    assert spec.guardrails[0].id == "service-unreachable"
    assert spec.model_tier == "sonnet"


def test_missing_required_field_raises(tmp_path: Path) -> None:
    bad = VALID.replace("description: Run a commercial policy check.\n", "")
    with pytest.raises(SpecError, match="description"):
        load_spec(_write(tmp_path, bad))


def test_bad_model_tier_raises(tmp_path: Path) -> None:
    bad = VALID.replace("model_tier: sonnet", "model_tier: turbo")
    with pytest.raises(SpecError, match="model_tier"):
        load_spec(_write(tmp_path, bad))


def test_bad_transport_raises(tmp_path: Path) -> None:
    bad = VALID.replace("transport: stdio", "transport: carrier-pigeon")
    with pytest.raises(SpecError, match="transport"):
        load_spec(_write(tmp_path, bad))


def test_non_kebab_name_raises(tmp_path: Path) -> None:
    bad = VALID.replace("name: trapezia-commercial-policy-check", "name: Not_Kebab")
    with pytest.raises(SpecError, match="kebab"):
        load_spec(_write(tmp_path, bad))
