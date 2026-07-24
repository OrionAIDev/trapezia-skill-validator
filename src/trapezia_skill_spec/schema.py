"""Canonical skill-spec data model and YAML loader. No templating here (jinja2-free)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

SPEC_VERSIONS = {0}
MODEL_TIERS = {"opus", "sonnet", "haiku"}
INVOKE_KINDS = {"mcp", "cli"}
TRANSPORTS = {"stdio", "http"}
_KEBAB = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


class SpecError(ValueError):
    """Raised when a canonical spec is malformed or violates a schema rule."""


@dataclass(frozen=True)
class Invocation:
    """One capability-core port the wrapper calls."""

    kind: str
    server: str
    transport: str
    tools: list[str]
    launch: str | None = None
    required_env: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Guardrail:
    """A verbatim guardrail block the adapter must carry."""

    id: str
    text: str


@dataclass(frozen=True)
class CanonicalSpec:
    """The single source of truth for a capability's per-harness wrappers."""

    name: str
    spec_version: int
    version: str
    description: str
    triggers: list[str]
    invokes: list[Invocation]
    guardrails: list[Guardrail]
    model_tier: str | None
    harnesses: dict[str, dict]


def _require(data: dict, key: str) -> object:
    if key not in data or data[key] in (None, ""):
        raise SpecError(f"missing required field: {key}")
    return data[key]


def load_spec(path: str | Path) -> CanonicalSpec:
    """Load and validate a canonical spec from ``path``.

    Args:
        path: path to the YAML manifest.

    Returns:
        A validated :class:`CanonicalSpec`.

    Raises:
        SpecError: if any required field is missing or a value is invalid.
    """
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise SpecError("spec must be a YAML mapping")

    name = str(_require(raw, "name"))
    if not _KEBAB.match(name):
        raise SpecError(f"name must be kebab-case: {name!r}")

    spec_version = int(_require(raw, "spec_version"))
    if spec_version not in SPEC_VERSIONS:
        raise SpecError(f"unknown spec_version: {spec_version}")

    model_tier = raw.get("model_tier")
    if model_tier is not None and model_tier not in MODEL_TIERS:
        raise SpecError(f"model_tier must be one of {sorted(MODEL_TIERS)} or omitted: {model_tier!r}")

    invokes_raw = _require(raw, "invokes")
    if not isinstance(invokes_raw, list) or not invokes_raw:
        raise SpecError("invokes must be a non-empty list")
    invokes: list[Invocation] = []
    for i, inv in enumerate(invokes_raw):
        kind = str(_require(inv, "kind"))
        if kind not in INVOKE_KINDS:
            raise SpecError(f"invokes[{i}].kind must be one of {sorted(INVOKE_KINDS)}: {kind!r}")
        transport = str(_require(inv, "transport"))
        if transport not in TRANSPORTS:
            raise SpecError(f"invokes[{i}].transport must be one of {sorted(TRANSPORTS)}: {transport!r}")
        tools = _require(inv, "tools")
        if not isinstance(tools, list) or not tools:
            raise SpecError(f"invokes[{i}].tools must be a non-empty list")
        invokes.append(
            Invocation(
                kind=kind,
                server=str(_require(inv, "server")),
                transport=transport,
                tools=[str(t) for t in tools],
                launch=inv.get("launch"),
                required_env=[str(e) for e in inv.get("required_env", [])],
            )
        )

    guardrails: list[Guardrail] = []
    seen_ids: set[str] = set()
    for g in raw.get("guardrails", []):
        gid = str(_require(g, "id"))
        if gid in seen_ids:
            raise SpecError(f"duplicate guardrail id: {gid}")
        seen_ids.add(gid)
        guardrails.append(Guardrail(id=gid, text=str(_require(g, "text"))))

    return CanonicalSpec(
        name=name,
        spec_version=spec_version,
        version=str(_require(raw, "version")),
        description=str(_require(raw, "description")),
        triggers=[str(t) for t in raw.get("triggers", [])],
        invokes=invokes,
        guardrails=guardrails,
        model_tier=model_tier,
        harnesses=dict(raw.get("harnesses", {})),
    )
