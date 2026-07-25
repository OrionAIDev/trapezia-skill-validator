"""Type-B (scripts) rendering: spec-driven context, {skill_root} templating."""

from __future__ import annotations

import textwrap
from pathlib import Path

from trapezia_skill_spec.generate import build_context, generate, skill_root
from trapezia_skill_spec.schema import load_spec

CLI_SPEC = textwrap.dedent(
    """
    name: policy-form-lister
    spec_version: 0
    version: 0.1.0
    description: List insurance form numbers found in a policy document.
    triggers: ["list forms"]
    invokes:
      - kind: cli
        exec: python {skill_root}/scripts/list_forms.py --input policy.txt
    bundle: [scripts/list_forms.py]
    usage: Run list_forms.py against the policy text.
    harnesses:
      hermes: {category: insure}
      openclaw: {}
      claude_code: {}
    """
)

MCP_SPEC = textwrap.dedent(
    """
    name: trapezia-commercial-policy-check
    spec_version: 0
    version: 0.1.0
    description: Run a commercial policy check.
    invokes:
      - kind: mcp
        server: trapezia-commercial-policy-check
        transport: stdio
        launch: python -m x.server
        tools: [health, run_policy_check]
    harnesses:
      hermes: {category: insure}
    """
)


def _spec(tmp_path: Path, text: str):  # type: ignore[no-untyped-def]
    p = tmp_path / "spec.yaml"
    p.write_text(text, encoding="utf-8")
    return load_spec(p)


def test_skill_root_per_harness(tmp_path: Path) -> None:
    spec = _spec(tmp_path, CLI_SPEC)
    assert skill_root("hermes", spec) == "~/.hermes/skills/insure/policy-form-lister"
    assert skill_root("openclaw", spec) == "/opt/openclaw-workspace/skills/policy-form-lister"
    assert skill_root("claude_code", spec) == "~/.claude/skills/policy-form-lister"


def test_cli_command_resolved_per_harness(tmp_path: Path) -> None:
    spec = _spec(tmp_path, CLI_SPEC)
    hermes = build_context(spec, "hermes")
    assert hermes["mcp_servers"] == []
    assert hermes["cli_cmds"] == [
        "python ~/.hermes/skills/insure/policy-form-lister/scripts/list_forms.py --input policy.txt"
    ]
    assert hermes["usage"] == "Run list_forms.py against the policy text."

    cc = build_context(spec, "claude_code")
    assert cc["cli_cmds"] == [
        "python ~/.claude/skills/policy-form-lister/scripts/list_forms.py --input policy.txt"
    ]


def test_mcp_context_structured(tmp_path: Path) -> None:
    spec = _spec(tmp_path, MCP_SPEC)
    ctx = build_context(spec, "hermes")
    assert ctx["cli_cmds"] == []
    assert len(ctx["mcp_servers"]) == 1
    server = ctx["mcp_servers"][0]
    assert server["server"] == "trapezia-commercial-policy-check"
    assert server["tools"] == ["health", "run_policy_check"]


def test_scripts_output_has_no_mcp_section(tmp_path: Path) -> None:
    spec = _spec(tmp_path, CLI_SPEC)
    for harness in ("hermes", "openclaw", "claude_code"):
        out = generate(spec, harness)
        assert "list_forms.py" in out
        assert "MCP server" not in out
