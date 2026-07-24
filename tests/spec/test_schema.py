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


VALID_CLI = textwrap.dedent(
    """
    name: policy-form-lister
    spec_version: 0
    version: 0.1.0
    description: List insurance form numbers found in a policy document.
    triggers: ["list forms"]
    invokes:
      - kind: cli
        exec: python {skill_root}/scripts/list_forms.py --input policy.txt
    bundle:
      - scripts/list_forms.py
      - references/form-glossary.md
    usage: Run list_forms.py against the policy text and report the form numbers.
    harnesses:
      hermes: {category: insure}
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


# --- Phase 2: cli invokes, bundle, usage, mixed invokes ------------------------


def test_load_valid_cli_spec(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, VALID_CLI))
    assert spec.name == "policy-form-lister"
    inv = spec.invokes[0]
    assert inv.kind == "cli"
    assert inv.exec == "python {skill_root}/scripts/list_forms.py --input policy.txt"
    # cli invokes need no server/transport/tools
    assert inv.server == ""
    assert inv.transport == ""
    assert inv.tools == []
    assert spec.bundle == ["scripts/list_forms.py", "references/form-glossary.md"]
    assert spec.usage == "Run list_forms.py against the policy text and report the form numbers."
    assert spec.harnesses["hermes"]["category"] == "insure"


def test_cli_without_exec_raises(tmp_path: Path) -> None:
    bad = VALID_CLI.replace(
        "    exec: python {skill_root}/scripts/list_forms.py --input policy.txt\n", ""
    )
    with pytest.raises(SpecError, match="exec"):
        load_spec(_write(tmp_path, bad))


def test_usage_absent_is_none(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, VALID))
    assert spec.usage is None


def test_bundle_absent_is_empty(tmp_path: Path) -> None:
    spec = load_spec(_write(tmp_path, VALID))
    assert spec.bundle == []


def test_bundle_parent_traversal_raises(tmp_path: Path) -> None:
    bad = VALID_CLI.replace("scripts/list_forms.py", "../evil.py")
    with pytest.raises(SpecError, match="bundle"):
        load_spec(_write(tmp_path, bad))


def test_bundle_absolute_path_raises(tmp_path: Path) -> None:
    bad = VALID_CLI.replace("- scripts/list_forms.py", "- /etc/passwd")
    with pytest.raises(SpecError, match="bundle"):
        load_spec(_write(tmp_path, bad))


def test_mixed_invokes_type_d_loads(tmp_path: Path) -> None:
    """A skill with both an MCP and a CLI invoke (type D) is valid."""
    mixed = textwrap.dedent(
        """
        name: type-d-skill
        spec_version: 0
        version: 0.1.0
        description: Both an MCP server and a helper script.
        invokes:
          - kind: mcp
            server: type-d-server
            transport: stdio
            launch: python -m type_d.server
            tools: [health]
          - kind: cli
            exec: python {skill_root}/scripts/helper.py
        bundle: [scripts/helper.py]
        harnesses:
          hermes: {}
        """
    )
    spec = load_spec(_write(tmp_path, mixed))
    assert [i.kind for i in spec.invokes] == ["mcp", "cli"]
    assert spec.invokes[0].tools == ["health"]
    assert spec.invokes[1].exec == "python {skill_root}/scripts/helper.py"
