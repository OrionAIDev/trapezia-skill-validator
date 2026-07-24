"""Render per-harness SKILL.md wrappers from a canonical spec."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .schema import CanonicalSpec

HARNESSES = ("hermes", "openclaw", "claude_code")
_TEMPLATES = Path(__file__).parent / "templates"
_WS = re.compile(r"\s+")
_DEFAULT_CATEGORY = "general"


def _oneline(text: str) -> str:
    """Collapse internal whitespace/newlines to single spaces and strip ends."""
    return _WS.sub(" ", text).strip()


def _category(spec: CanonicalSpec) -> str:
    """The Hermes category for ``spec`` (from ``harnesses.hermes.category``)."""
    return str(spec.harnesses.get("hermes", {}).get("category", _DEFAULT_CATEGORY))


def skill_root(harness: str, spec: CanonicalSpec) -> str:
    """Return the deployed skill-root path for ``spec`` under ``harness``.

    This is the value substituted for the ``{skill_root}`` token in a cli
    invoke's ``exec`` command.

    Args:
        harness: one of :data:`HARNESSES`.
        spec: the canonical spec (supplies name and Hermes category).

    Returns:
        The harness-correct skill-root path.

    Raises:
        ValueError: if ``harness`` is unknown.
    """
    if harness == "hermes":
        return f"~/.hermes/skills/{_category(spec)}/{spec.name}"
    if harness == "openclaw":
        return f"/home/node/.openclaw/workspace/skills/{spec.name}"
    if harness == "claude_code":
        return f"~/.claude/skills/{spec.name}"
    raise ValueError(f"unknown harness: {harness!r} (expected one of {HARNESSES})")


def build_context(spec: CanonicalSpec, harness: str) -> dict[str, Any]:
    """Flatten a spec into the plain dict the ``harness`` template consumes.

    Args:
        spec: the canonical spec.
        harness: one of :data:`HARNESSES` (selects the ``{skill_root}`` value).

    Returns:
        A dict with ``mcp_servers`` (structured list), ``cli_cmds`` (exec
        strings with ``{skill_root}`` resolved), and the shared metadata fields.
    """
    root = skill_root(harness, spec)
    required_env: list[str] = []
    mcp_servers: list[dict[str, Any]] = []
    cli_cmds: list[str] = []
    for inv in spec.invokes:
        for e in inv.required_env:
            if e not in required_env:
                required_env.append(e)
        if inv.kind == "mcp":
            mcp_servers.append(
                {
                    "server": inv.server,
                    "transport": inv.transport,
                    "tools": list(inv.tools),
                    "required_env": list(inv.required_env),
                }
            )
        elif inv.kind == "cli" and inv.exec is not None:
            cli_cmds.append(inv.exec.replace("{skill_root}", root))
    return {
        "name": spec.name,
        "description": _oneline(spec.description),
        "version": spec.version,
        "triggers": list(spec.triggers),
        "category": _category(spec),
        "mcp_servers": mcp_servers,
        "cli_cmds": cli_cmds,
        "required_env": required_env,
        "usage": _oneline(spec.usage) if spec.usage else None,
        "guardrails": [{"id": g.id, "text": _oneline(g.text)} for g in spec.guardrails],
        "model_tier": spec.model_tier,
    }


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_TEMPLATES)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )


def generate(spec: CanonicalSpec, harness: str) -> str:
    """Render the SKILL.md text for ``harness`` from ``spec``.

    Args:
        spec: the canonical spec.
        harness: one of :data:`HARNESSES`.

    Returns:
        The rendered SKILL.md content.

    Raises:
        ValueError: if ``harness`` is unknown.
    """
    if harness not in HARNESSES:
        raise ValueError(f"unknown harness: {harness!r} (expected one of {HARNESSES})")
    template = _env().get_template(f"{harness}.md.j2")
    return template.render(**build_context(spec, harness))
