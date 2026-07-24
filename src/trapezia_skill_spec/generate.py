"""Render per-harness SKILL.md wrappers from a canonical spec."""

from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from .schema import CanonicalSpec

HARNESSES = ("hermes", "openclaw", "claude_code")
_TEMPLATES = Path(__file__).parent / "templates"
_WS = re.compile(r"\s+")


def _oneline(text: str) -> str:
    """Collapse internal whitespace/newlines to single spaces and strip ends."""
    return _WS.sub(" ", text).strip()


def build_context(spec: CanonicalSpec) -> dict:
    """Flatten a spec into the plain dict the templates consume.

    Args:
        spec: the canonical spec.

    Returns:
        A dict with primitive fields (name, description, tools, guardrails, ...).
    """
    tools: list[str] = []
    required_env: list[str] = []
    server = transport = None
    for inv in spec.invokes:
        server = server or inv.server
        transport = transport or inv.transport
        for t in inv.tools:
            if t not in tools:
                tools.append(t)
        for e in inv.required_env:
            if e not in required_env:
                required_env.append(e)
    return {
        "name": spec.name,
        "description": _oneline(spec.description),
        "version": spec.version,
        "triggers": list(spec.triggers),
        "server": server,
        "transport": transport,
        "tools": tools,
        "required_env": required_env,
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
    return template.render(**build_context(spec))
