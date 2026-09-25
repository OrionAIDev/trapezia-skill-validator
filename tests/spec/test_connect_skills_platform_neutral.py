"""Platform-neutral MCP contract for the six connect/disconnect canonical specs.

Roadmap: OrionAIDev/trapezia-roadmap#287, platform-neutral-trapezia-user-id design chunk 6
(docs/superhuman/specs/2026-09-24-platform-neutral-trapezia-user-id-design.md §4.4/4.5/4.7c,
trapezia-auth-server). These six specs used to build an ``auth.trapezia.ai`` URL from a
Discord ``sender_id`` read out of message metadata (F1, the exact thing the design forbids).
They are now MCP-invoking specs: a Hermes gateway plugin stamps a signed sender principal on
every tool call, so the skill body never sees or supplies an identity.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

REPO = Path(__file__).resolve().parents[2]

# name -> (mcp server, exactly the tools this skill must declare, in either order)
EXPECTED = {
    "connect-outlook": ("trapezia-m365", {"outlook_status", "outlook_connect"}),
    "connect-onedrive": ("trapezia-m365", {"onedrive_status", "onedrive_connect"}),
    "connect-google": ("trapezia-google", {"google_status", "google_connect"}),
    "disconnect-outlook": ("trapezia-m365", {"outlook_status", "outlook_disconnect"}),
    "disconnect-onedrive": ("trapezia-m365", {"onedrive_status", "onedrive_disconnect"}),
    "disconnect-google": ("trapezia-google", {"google_status", "google_disconnect"}),
}

# Substrings that must never reappear -- the model-supplied-identity pattern this chunk removes.
FORBIDDEN = (
    "discord",
    "Discord",
    "sender_id",
    "platform=",
    "env=",
    "INSTANCE_NAME",
    "auth.trapezia.ai",
)


def _ids(name: str) -> str:
    return name


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=_ids)
def test_spec_validates(name: str) -> None:
    """Each of the six specs loads and validates against the canonical schema."""
    load_spec(REPO / "specs" / f"{name}.yaml")


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=_ids)
def test_spec_declares_exactly_one_mcp_invoke_of_the_right_server(name: str) -> None:
    spec = load_spec(REPO / "specs" / f"{name}.yaml")
    mcp_invokes = [inv for inv in spec.invokes if inv.kind == "mcp"]
    assert len(mcp_invokes) == 1, f"{name}: expected exactly one mcp invoke, got {len(mcp_invokes)}"
    inv = mcp_invokes[0]
    expected_server, expected_tools = EXPECTED[name]
    assert inv.server == expected_server
    assert inv.transport == "http"
    assert set(inv.tools) == expected_tools


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=_ids)
def test_spec_has_no_cli_invoke(name: str) -> None:
    """These are pure MCP-invoking skills now -- no leftover cli/web_fetch port."""
    spec = load_spec(REPO / "specs" / f"{name}.yaml")
    assert not any(inv.kind == "cli" for inv in spec.invokes)


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=_ids)
def test_spec_never_supplies_identity(name: str) -> None:
    """A guardrail must tell the model to leave principal/user_id empty."""
    spec = load_spec(REPO / "specs" / f"{name}.yaml")
    text = " ".join(g.text for g in spec.guardrails) + (spec.body or "")
    assert "principal" in text
    assert "user_id" in text


@pytest.mark.parametrize("name", ["disconnect-outlook", "disconnect-onedrive", "disconnect-google"], ids=_ids)
def test_disconnect_spec_confirms_before_disconnecting(name: str) -> None:
    """Disconnect is destructive -- a guardrail must require confirmation, not a bare warning."""
    spec = load_spec(REPO / "specs" / f"{name}.yaml")
    ids = {g.id for g in spec.guardrails}
    assert "confirm-before-disconnect" in ids
    assert "warn-before-disconnect" not in ids
    combined = " ".join(g.text for g in spec.guardrails) + (spec.body or "")
    assert "affected_environments" not in combined
    assert "tier-wide" not in combined


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=_ids)
@pytest.mark.parametrize("forbidden", FORBIDDEN)
def test_spec_file_has_no_forbidden_strings(name: str, forbidden: str) -> None:
    raw = (REPO / "specs" / f"{name}.yaml").read_text(encoding="utf-8")
    assert forbidden not in raw, f"{name}.yaml still contains {forbidden!r}"


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=_ids)
@pytest.mark.parametrize("forbidden", FORBIDDEN)
def test_generated_hermes_skill_md_has_no_forbidden_strings(name: str, forbidden: str) -> None:
    spec = load_spec(REPO / "specs" / f"{name}.yaml")
    out = generate(spec, "hermes")
    assert forbidden not in out, f"generated hermes/{name}/SKILL.md still contains {forbidden!r}"


@pytest.mark.parametrize("name", sorted(EXPECTED), ids=_ids)
def test_generated_hermes_skill_md_declares_the_mcp_server(name: str) -> None:
    spec = load_spec(REPO / "specs" / f"{name}.yaml")
    out = generate(spec, "hermes")
    expected_server, expected_tools = EXPECTED[name]
    assert f"`{expected_server}`" in out
    for tool in expected_tools:
        assert f"`{tool}`" in out
