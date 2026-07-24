"""The Hermes config.yaml `mcp_servers.<name>` registration snippet (Gap 2)."""

from __future__ import annotations

import textwrap
from pathlib import Path

import yaml

from trapezia_skill_spec.generate import generate_mcp_registration
from trapezia_skill_spec.schema import load_spec

POLICY_CHECK = "specs/trapezia-commercial-policy-check.yaml"

CLI_ONLY = textwrap.dedent(
    """
    name: policy-form-lister
    spec_version: 0
    version: 0.1.0
    description: List insurance form numbers.
    invokes:
      - kind: cli
        exec: python {skill_root}/scripts/list_forms.py
    bundle: [scripts/list_forms.py]
    harnesses:
      hermes: {category: insure}
    """
)


def test_registration_for_policy_check() -> None:
    snippet = generate_mcp_registration(load_spec(POLICY_CHECK))
    assert snippet is not None
    # Must be valid YAML that parses back to the expected structure.
    doc = yaml.safe_load(snippet)
    block = doc["mcp_servers"]["trapezia-commercial-policy-check"]
    assert block["command"] == "python"
    assert block["args"] == ["-m", "trapezia_commercial_policy_check.mcp_server"]
    assert block["env"]["GOOGLE_API_KEY"] == "${GOOGLE_API_KEY}"


def test_registration_is_none_without_mcp(tmp_path: Path) -> None:
    p = tmp_path / "spec.yaml"
    p.write_text(CLI_ONLY, encoding="utf-8")
    assert generate_mcp_registration(load_spec(p)) is None


def test_registration_has_operator_guidance() -> None:
    snippet = generate_mcp_registration(load_spec(POLICY_CHECK))
    assert snippet is not None
    # A leading comment tells the operator this is a merge fragment.
    assert snippet.lstrip().startswith("#")
    assert "mcp_servers" in snippet
