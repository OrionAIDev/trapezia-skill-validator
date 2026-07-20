# Canonical Spec + Per-Harness Generator (Phase 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This is a **TDD code** plan — every code step shows the actual code and the exact test command with expected output.

**Goal:** Prove the portability thesis — one canonical YAML spec emits working thin `SKILL.md` wrappers for Hermes, OpenClaw, and Claude Code, guarded by a CI regeneration check and a new additive canonical-spec linter in `trapezia-skill-validator`.

**Architecture:** A new, self-contained `trapezia_skill_spec` package (schema + jinja2-based generator + per-harness templates + CLI) lives alongside the existing `trapezia_skill_validator` package in this repo. The canonical spec is the only authored surface; per-harness `SKILL.md` files are generated, committed, and drift-checked in CI. The validator gains a canonical-spec linter as a **new module + new entry point** — it does not touch `run_audit`/`CHECKS` (the API that `skill-template` self-test and `trapezia-skill-audit` consume).

**Tech Stack:** Python 3.13, `pyyaml` (schema/loader), `jinja2` (templates — a Trapezia-preferred lib already used by policy-check), `pytest` + the existing `make_skill` fixture, GitHub Actions.

**Branch:** `multi-harness-poc` in the `trapezia-skill-validator-poc` worktree. Master and all production consumers stay untouched.

---

## Guardrails (from spec §4/§6 + trapezia-disciplines)

- **Additive only in the validator.** The canonical-spec linter is a new `spec_lint.py` module + a new `trapezia-canonical-spec-lint` entry point. Do **not** change `runner.run_audit`, `registry.CHECKS`, or the existing `trapezia-skill-validator` CLI signature.
- **Generated files are never hand-edited.** The canonical spec YAML is the only authored artifact; `generated/**` is machine output, protected by the CI regeneration check.
- **`jinja2` stays an optional extra**, not a core dependency — validator consumers (skill-template, trapezia-skill-audit) must not be forced to install it. `schema.py` is jinja2-free so the linter can import it without pulling jinja2.
- **OQ-3 resolved:** Hermes does not honor per-skill model tiers. `model_tier` stays in the schema as **advisory** — emitted as a body note by the CC/OpenClaw templates, and **omitted** by the Hermes template.
- **Graduation decision (§4.5)** is recorded at the end (Task 11); the worktree deliberately defers merge-vs-extract.

---

## File & artifact map

**New generator package (future-extractable as `trapezia-skill-spec`):**
- Create: `src/trapezia_skill_spec/__init__.py`
- Create: `src/trapezia_skill_spec/schema.py` — dataclasses + `load_spec()` + `SpecError` (pyyaml only; **no jinja2**).
- Create: `src/trapezia_skill_spec/generate.py` — `generate(spec, harness)`, `HARNESSES`, context builder (imports jinja2).
- Create: `src/trapezia_skill_spec/templates/hermes.md.j2`
- Create: `src/trapezia_skill_spec/templates/openclaw.md.j2`
- Create: `src/trapezia_skill_spec/templates/claude_code.md.j2`
- Create: `src/trapezia_skill_spec/cli.py` — `trapezia-skill-gen` entry point.

**Canonical spec + generated outputs:**
- Create: `specs/trapezia-commercial-policy-check.yaml`
- Create (generated): `generated/hermes/trapezia-commercial-policy-check/SKILL.md`
- Create (generated): `generated/openclaw/trapezia-commercial-policy-check/SKILL.md`
- Create (generated): `generated/claude_code/trapezia-commercial-policy-check/SKILL.md`

**Validator addition (additive):**
- Create: `src/trapezia_skill_validator/spec_lint.py` — `lint_spec()`, `render_spec_report()`, `main()` for the new entry point.

**Tests / CI / packaging:**
- Create: `tests/spec/__init__.py`, `tests/spec/test_schema.py`, `tests/spec/test_generate_hermes.py`, `tests/spec/test_generate_openclaw.py`, `tests/spec/test_generate_claude_code.py`, `tests/spec/test_cli.py`, `tests/spec/test_regeneration.py`
- Create: `tests/test_spec_lint.py`
- Create: `.github/workflows/ci.yml`
- Modify: `pyproject.toml` (add `jinja2` extra, entry points, package data, extra package under `src`)

---

### Task 1: Packaging — new package skeleton + deps + entry points

**Files:**
- Create: `src/trapezia_skill_spec/__init__.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the package init.**

```python
# src/trapezia_skill_spec/__init__.py
"""Canonical skill-spec: one manifest -> per-harness SKILL.md wrappers."""

from __future__ import annotations

__version__ = "0.1.0"
```

- [ ] **Step 2: Update `pyproject.toml`** — add the `spec` optional extra (jinja2), pull it into `test`, register the two new entry points, ensure both `src` packages are found, and bundle the templates as package data.

```toml
[project.optional-dependencies]
spec = ["jinja2>=3"]
test = ["pytest>=8.0", "jinja2>=3"]

[project.scripts]
trapezia-skill-validator = "trapezia_skill_validator.cli:main"
trapezia-canonical-spec-lint = "trapezia_skill_validator.spec_lint:main"
trapezia-skill-gen = "trapezia_skill_spec.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
trapezia_skill_validator = ["data/*.toml"]
trapezia_skill_spec = ["templates/*.j2"]
```

- [ ] **Step 3: Install the package editable with the test extra and confirm import.**

Run: `pip install -e ".[test]" && python -c "import trapezia_skill_spec, jinja2; print(trapezia_skill_spec.__version__)"`
Expected: prints `0.1.0`, no ImportError.

- [ ] **Step 4: Commit.**

```bash
git add src/trapezia_skill_spec/__init__.py pyproject.toml
git commit -m "chore(spec): scaffold trapezia_skill_spec package + entry points"
```

---

### Task 2: Canonical-spec schema + loader (jinja2-free)

**Files:**
- Create: `src/trapezia_skill_spec/schema.py`
- Test: `tests/spec/__init__.py`, `tests/spec/test_schema.py`

- [ ] **Step 1: Write the failing schema test.**

```python
# tests/spec/test_schema.py
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
```

Also create empty `tests/spec/__init__.py`.

- [ ] **Step 2: Run to verify it fails.**

Run: `pytest tests/spec/test_schema.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'trapezia_skill_spec.schema'`.

- [ ] **Step 3: Write the schema + loader.**

```python
# src/trapezia_skill_spec/schema.py
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
```

- [ ] **Step 4: Run to verify it passes.**

Run: `pytest tests/spec/test_schema.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/trapezia_skill_spec/schema.py tests/spec/__init__.py tests/spec/test_schema.py
git commit -m "feat(spec): canonical-spec schema + validating loader"
```

---

### Task 3: The policy-check canonical spec (the real manifest)

**Files:**
- Create: `specs/trapezia-commercial-policy-check.yaml`

- [ ] **Step 1: Write the manifest** (grounded in the real MCP surface: server name `trapezia-commercial-policy-check`, stdio launch `python -m trapezia_commercial_policy_check.mcp_server`, tools `health`/`run_policy_check`/`get_run_status`/`get_run_report`, needs Anthropic + Google).

```yaml
# specs/trapezia-commercial-policy-check.yaml
name: trapezia-commercial-policy-check
spec_version: 0
version: 0.1.0
description: >-
  Run an automated commercial-insurance policy check and produce a coverage/gap
  report. Use when the user asks to "check a policy", "run a policy check", or
  "review coverage", or drops a commercial policy document expecting analysis.
triggers:
  - "policy check"
  - "check this policy"
  - "review coverage"
invokes:
  - kind: mcp
    server: trapezia-commercial-policy-check
    transport: stdio
    launch: python -m trapezia_commercial_policy_check.mcp_server
    tools:
      - health
      - run_policy_check
      - get_run_status
      - get_run_report
    # Only GOOGLE_API_KEY: direct-Anthropic is deprecated (FR-7.5); the real provider is
    # selected by a "<provider>/<model>" id (google/... or claude-cli/...). A bare model
    # name resolves to the hermetic stub. Confirmed on the live OrionLab deployment 2026-07-20.
    required_env:
      - GOOGLE_API_KEY
guardrails:
  - id: service-unreachable
    text: >-
      If the policy-check MCP service is unreachable or a tool returns an error,
      surface the error verbatim and do not improvise a coverage verdict.
  - id: commercial-only
    text: >-
      This capability is for commercial (business) insurance policies only and
      handles no personal health information.
model_tier: sonnet
harnesses:
  hermes: {}
  openclaw: {}
  claude_code: {}
```

- [ ] **Step 2: Validate it loads.**

Run: `python -c "from trapezia_skill_spec.schema import load_spec; s=load_spec('specs/trapezia-commercial-policy-check.yaml'); print(s.name, [i.transport for i in s.invokes])"`
Expected: `trapezia-commercial-policy-check ['stdio']`.

- [ ] **Step 3: Commit.**

```bash
git add specs/trapezia-commercial-policy-check.yaml
git commit -m "feat(spec): canonical manifest for trapezia-commercial-policy-check"
```

---

### Task 4: Generator core + context builder + templates dir

**Files:**
- Create: `src/trapezia_skill_spec/generate.py`
- Create: `src/trapezia_skill_spec/templates/` (templates added in Tasks 5–7)

- [ ] **Step 1: Write `generate.py`** (the context builder is pure/testable; rendering uses jinja2 with `trim_blocks`/`lstrip_blocks` for clean output).

```python
# src/trapezia_skill_spec/generate.py
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
```

- [ ] **Step 2: Verify import + context builder** (no template yet, so only test the pure helper).

Run: `python -c "from trapezia_skill_spec.generate import build_context, HARNESSES; from trapezia_skill_spec.schema import load_spec; print(build_context(load_spec('specs/trapezia-commercial-policy-check.yaml'))['tools'])"`
Expected: `['health', 'run_policy_check', 'get_run_status', 'get_run_report']`.

- [ ] **Step 3: Commit.**

```bash
git add src/trapezia_skill_spec/generate.py
git commit -m "feat(spec): generator core + context builder (templates follow)"
```

---

### Task 5: Hermes emitter (template + test)

**Files:**
- Create: `src/trapezia_skill_spec/templates/hermes.md.j2`
- Test: `tests/spec/test_generate_hermes.py`

- [ ] **Step 1: Write the failing Hermes test.**

```python
# tests/spec/test_generate_hermes.py
"""Hermes emitter: required frontmatter + sections, model_tier omitted."""

from __future__ import annotations

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

SPEC = "specs/trapezia-commercial-policy-check.yaml"


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
```

- [ ] **Step 2: Run to verify it fails.**

Run: `pytest tests/spec/test_generate_hermes.py -q`
Expected: FAIL — `jinja2.exceptions.TemplateNotFound: hermes.md.j2`.

- [ ] **Step 3: Write `hermes.md.j2`.**

```jinja
---
name: {{ name }}
description: {{ description }}
version: {{ version }}
{% if required_env %}
required_environment_variables:
{% for e in required_env %}
  - {{ e }}
{% endfor %}
{% endif %}
metadata:
  hermes:
    category: insure
    tags: [insurance, policy-check, trapezia]
---

# {{ name }}

## When to Use

{{ description }}
{% if triggers %}

Trigger phrases: {{ triggers | join(", ") }}.
{% endif %}

## Procedure

This skill wraps the `{{ server }}` MCP server (transport: {{ transport }}). Available tools:
{% for t in tools %}
- `{{ t }}`
{% endfor %}

Call `run_policy_check` with the policy payload, then poll `get_run_status` and fetch `get_run_report`.

## Pitfalls

{% for g in guardrails %}
- {{ g.text }}
{% endfor %}

## Verification

Call `health` and confirm `status: ok` before running a check.
```

- [ ] **Step 4: Run to verify it passes.**

Run: `pytest tests/spec/test_generate_hermes.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/trapezia_skill_spec/templates/hermes.md.j2 tests/spec/test_generate_hermes.py
git commit -m "feat(spec): Hermes SKILL.md emitter"
```

---

### Task 6: OpenClaw emitter (template + test)

**Files:**
- Create: `src/trapezia_skill_spec/templates/openclaw.md.j2`
- Test: `tests/spec/test_generate_openclaw.py`

- [ ] **Step 1: Write the failing OpenClaw test.** OpenClaw/ClawHub `SKILL.md` uses `name`/`description` frontmatter (same shape as CC); `model_tier` is surfaced as a **body note** (advisory, honored where supported).

```python
# tests/spec/test_generate_openclaw.py
"""OpenClaw emitter: name/description frontmatter + model-tier body note."""

from __future__ import annotations

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

SPEC = "specs/trapezia-commercial-policy-check.yaml"


def test_openclaw_frontmatter_is_name_description_only() -> None:
    out = generate(load_spec(SPEC), "openclaw")
    head = out.split("---\n", 2)[1]  # frontmatter block
    assert "name: trapezia-commercial-policy-check" in head
    assert "description:" in head
    assert "version:" not in head  # OpenClaw frontmatter is name+description


def test_openclaw_surfaces_model_tier_as_note() -> None:
    out = generate(load_spec(SPEC), "openclaw")
    assert "Model tier: sonnet" in out


def test_openclaw_carries_tools_and_guardrails() -> None:
    out = generate(load_spec(SPEC), "openclaw")
    assert "run_policy_check" in out
    assert "surface the error verbatim" in out
```

- [ ] **Step 2: Run to verify it fails.**

Run: `pytest tests/spec/test_generate_openclaw.py -q`
Expected: FAIL — `TemplateNotFound: openclaw.md.j2`.

- [ ] **Step 3: Write `openclaw.md.j2`.**

```jinja
---
name: {{ name }}
description: {{ description }}
---

# {{ name }}

{{ description }}
{% if triggers %}

Trigger phrases: {{ triggers | join(", ") }}.
{% endif %}

## Procedure

Wraps the `{{ server }}` MCP server (transport: {{ transport }}). Tools:
{% for t in tools %}
- `{{ t }}`
{% endfor %}

Call `run_policy_check`, then poll `get_run_status` and fetch `get_run_report`.
{% if model_tier %}

**Model tier: {{ model_tier }}** (advisory — apply where the harness supports per-task model selection).
{% endif %}

## Guardrails

{% for g in guardrails %}
- {{ g.text }}
{% endfor %}
```

- [ ] **Step 4: Run to verify it passes.**

Run: `pytest tests/spec/test_generate_openclaw.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/trapezia_skill_spec/templates/openclaw.md.j2 tests/spec/test_generate_openclaw.py
git commit -m "feat(spec): OpenClaw SKILL.md emitter"
```

---

### Task 7: Claude Code emitter (template + test)

**Files:**
- Create: `src/trapezia_skill_spec/templates/claude_code.md.j2`
- Test: `tests/spec/test_generate_claude_code.py`

- [ ] **Step 1: Write the failing CC test.** CC `SKILL.md` frontmatter is `name`/`description`; `model_tier` surfaces as a body note (CC honors tiers via agent dispatch, not frontmatter).

```python
# tests/spec/test_generate_claude_code.py
"""Claude Code emitter: name/description frontmatter + model-tier body note."""

from __future__ import annotations

from trapezia_skill_spec.generate import generate
from trapezia_skill_spec.schema import load_spec

SPEC = "specs/trapezia-commercial-policy-check.yaml"


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
```

- [ ] **Step 2: Run to verify it fails.**

Run: `pytest tests/spec/test_generate_claude_code.py -q`
Expected: FAIL — `TemplateNotFound: claude_code.md.j2`.

- [ ] **Step 3: Write `claude_code.md.j2`.**

```jinja
---
name: {{ name }}
description: {{ description }}
---

# {{ name }}

{{ description }}
{% if triggers %}

Use when the user says: {{ triggers | join(", ") }}.
{% endif %}

## Procedure

Wraps the `{{ server }}` MCP server (transport: {{ transport }}). Tools:
{% for t in tools %}
- `{{ t }}`
{% endfor %}

Call `run_policy_check`, then poll `get_run_status` and fetch `get_run_report`.
{% if model_tier %}

**Model tier: {{ model_tier }}** (advisory — dispatch judgment-heavy steps to a `{{ model_tier }}`-tier agent).
{% endif %}

## Guardrails

{% for g in guardrails %}
- {{ g.text }}
{% endfor %}
```

- [ ] **Step 4: Run to verify it passes.**

Run: `pytest tests/spec/test_generate_claude_code.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit.**

```bash
git add src/trapezia_skill_spec/templates/claude_code.md.j2 tests/spec/test_generate_claude_code.py
git commit -m "feat(spec): Claude Code SKILL.md emitter"
```

---

### Task 8: Generator CLI (`trapezia-skill-gen`)

**Files:**
- Create: `src/trapezia_skill_spec/cli.py`
- Test: `tests/spec/test_cli.py`

- [ ] **Step 1: Write the failing CLI test.**

```python
# tests/spec/test_cli.py
"""CLI: generate one harness, or --all into generated/<harness>/<name>/SKILL.md."""

from __future__ import annotations

from pathlib import Path

from trapezia_skill_spec.cli import main

SPEC = "specs/trapezia-commercial-policy-check.yaml"


def test_generate_single_harness_to_stdout(capsys) -> None:
    rc = main([SPEC, "--harness", "hermes"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "name: trapezia-commercial-policy-check" in out


def test_generate_all_writes_three_files(tmp_path: Path) -> None:
    rc = main([SPEC, "--all", "--out", str(tmp_path)])
    assert rc == 0
    for harness in ("hermes", "openclaw", "claude_code"):
        p = tmp_path / harness / "trapezia-commercial-policy-check" / "SKILL.md"
        assert p.is_file(), f"missing {p}"
        assert "trapezia-commercial-policy-check" in p.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run to verify it fails.**

Run: `pytest tests/spec/test_cli.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'trapezia_skill_spec.cli'`.

- [ ] **Step 3: Write `cli.py`.**

```python
# src/trapezia_skill_spec/cli.py
"""Command-line entry point for the canonical-spec generator."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .generate import HARNESSES, generate
from .schema import load_spec


def _write_output(text: str, out_dir: Path, harness: str, name: str) -> Path:
    dest = out_dir / harness / name / "SKILL.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(text, encoding="utf-8")
    return dest


def main(argv: list[str] | None = None) -> int:
    """Generate per-harness SKILL.md wrappers from a canonical spec.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success, 2 on usage error).
    """
    parser = argparse.ArgumentParser(
        prog="trapezia-skill-gen",
        description="Generate per-harness SKILL.md wrappers from a canonical spec.",
    )
    parser.add_argument("spec", type=Path, help="path to the canonical spec YAML")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--harness", choices=HARNESSES, help="emit one harness to stdout")
    group.add_argument("--all", action="store_true", help="emit all harnesses to --out")
    parser.add_argument(
        "--out", type=Path, default=Path("generated"), help="output root for --all (default: generated/)"
    )
    args = parser.parse_args(argv)

    spec = load_spec(args.spec)
    if args.harness:
        sys.stdout.write(generate(spec, args.harness))
        return 0
    for harness in HARNESSES:
        dest = _write_output(generate(spec, harness), args.out, harness, spec.name)
        sys.stdout.write(f"wrote {dest}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify it passes.**

Run: `pytest tests/spec/test_cli.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Generate and commit the real committed outputs.**

```bash
python -m trapezia_skill_spec.cli specs/trapezia-commercial-policy-check.yaml --all --out generated
git add src/trapezia_skill_spec/cli.py tests/spec/test_cli.py generated/
git commit -m "feat(spec): generator CLI + committed policy-check wrappers"
```

Expected: `generated/{hermes,openclaw,claude_code}/trapezia-commercial-policy-check/SKILL.md` all exist and are staged.

---

### Task 9: CI regeneration (drift) check

**Files:**
- Test: `tests/spec/test_regeneration.py`

- [ ] **Step 1: Write the regeneration test** — regenerate in-memory and assert byte-equality with the committed `generated/**` files. This is the guard that fails CI if someone hand-edits generated output or forgets to regenerate after a spec change.

```python
# tests/spec/test_regeneration.py
"""Committed generated/** must match a fresh generation of the spec (no drift)."""

from __future__ import annotations

from pathlib import Path

import pytest

from trapezia_skill_spec.generate import HARNESSES, generate
from trapezia_skill_spec.schema import load_spec

REPO = Path(__file__).resolve().parents[2]
SPEC = REPO / "specs" / "trapezia-commercial-policy-check.yaml"


@pytest.mark.parametrize("harness", HARNESSES)
def test_committed_output_matches_generation(harness: str) -> None:
    spec = load_spec(SPEC)
    committed = REPO / "generated" / harness / spec.name / "SKILL.md"
    assert committed.is_file(), f"missing committed output: {committed}"
    expected = generate(spec, harness)
    actual = committed.read_text(encoding="utf-8")
    assert actual == expected, (
        f"{committed} is stale — run "
        f"`python -m trapezia_skill_spec.cli {SPEC.relative_to(REPO)} --all` and commit."
    )
```

- [ ] **Step 2: Run to verify it passes** (outputs were committed in Task 8).

Run: `pytest tests/spec/test_regeneration.py -q`
Expected: PASS (3 passed). If it fails, regenerate and re-commit as the assertion message says.

- [ ] **Step 3: Add the GitHub Actions workflow** (none exists yet).

```yaml
# .github/workflows/ci.yml
name: CI
on:
  push:
    branches: ["**"]
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -e ".[test]"
      - run: pytest -q
```

- [ ] **Step 4: Verify the full suite passes locally.**

Run: `pytest -q`
Expected: PASS — existing validator tests + all `tests/spec/**` + `test_spec_lint` (Task 10) green.

- [ ] **Step 5: Commit.**

```bash
git add tests/spec/test_regeneration.py .github/workflows/ci.yml
git commit -m "ci(spec): regeneration drift check + GitHub Actions workflow"
```

---

### Task 10: Canonical-spec linter in trapezia-skill-validator (additive)

**Files:**
- Create: `src/trapezia_skill_validator/spec_lint.py`
- Test: `tests/test_spec_lint.py`

- [ ] **Step 1: Write the failing linter test.** The linter reuses the existing `CheckResult`/`Status`/`Severity` models and imports `trapezia_skill_spec.schema` (jinja2-free) — it must **not** import or alter `runner`/`registry`.

```python
# tests/test_spec_lint.py
"""Additive canonical-spec linter: does not touch run_audit/CHECKS."""

from __future__ import annotations

import textwrap
from pathlib import Path

from trapezia_skill_validator.models import Status
from trapezia_skill_validator.spec_lint import lint_spec, main

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
        tools: [health]
    guardrails:
      - id: g1
        text: Be careful.
    model_tier: sonnet
    harnesses: {hermes: {}}
    """
)


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "spec.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_valid_spec_passes(tmp_path: Path) -> None:
    results = lint_spec(_write(tmp_path, VALID))
    assert all(r.status is Status.PASS for r in results)


def test_invalid_spec_fails_not_raises(tmp_path: Path) -> None:
    bad = VALID.replace("model_tier: sonnet", "model_tier: turbo")
    results = lint_spec(_write(tmp_path, bad))
    assert any(r.status is Status.FAIL for r in results)


def test_missing_guardrails_warns(tmp_path: Path) -> None:
    no_g = VALID.replace(
        "    guardrails:\n      - id: g1\n        text: Be careful.\n", "    guardrails: []\n"
    )
    results = lint_spec(_write(tmp_path, no_g))
    assert any(r.status is Status.WARN and r.id == "spec.guardrails" for r in results)


def test_cli_returns_nonzero_on_invalid(tmp_path: Path) -> None:
    bad = VALID.replace("transport: stdio", "transport: pigeon")
    assert main([str(_write(tmp_path, bad))]) == 1


def test_existing_check_api_untouched() -> None:
    # Guard: the additive linter must not change the run_audit/CHECKS contract.
    from trapezia_skill_validator.runner import run_audit  # noqa: F401
    from trapezia_skill_validator.registry import CHECKS  # noqa: F401
    assert callable(run_audit)
```

- [ ] **Step 2: Run to verify it fails.**

Run: `pytest tests/test_spec_lint.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'trapezia_skill_validator.spec_lint'`.

- [ ] **Step 3: Write `spec_lint.py`.**

```python
# src/trapezia_skill_validator/spec_lint.py
"""Additive canonical-spec linter.

Separate from the skill-directory audit (``runner.run_audit`` / ``registry.CHECKS``)
so the existing check API consumed by skill-template self-test and
trapezia-skill-audit stays untouched. Exposed via the ``trapezia-canonical-spec-lint``
console script.
"""

from __future__ import annotations

import sys
from pathlib import Path

from trapezia_skill_spec.schema import SpecError, load_spec

from .models import CheckResult, Severity, Status


def lint_spec(path: str | Path) -> list[CheckResult]:
    """Lint a canonical spec, returning one CheckResult per rule.

    Args:
        path: path to the canonical spec YAML.

    Returns:
        A list of CheckResult (never raises for spec content problems — a
        malformed spec becomes a FAIL result).
    """
    results: list[CheckResult] = []
    try:
        spec = load_spec(path)
    except SpecError as exc:
        return [
            CheckResult(
                id="spec.valid",
                status=Status.FAIL,
                severity=Severity.CRITICAL,
                message=f"spec invalid: {exc}",
                min_level=0,
            )
        ]

    results.append(
        CheckResult("spec.valid", Status.PASS, Severity.CRITICAL, "spec parses and validates", 0)
    )
    if spec.guardrails:
        results.append(
            CheckResult("spec.guardrails", Status.PASS, Severity.MEDIUM, "guardrails present", 0)
        )
    else:
        results.append(
            CheckResult(
                "spec.guardrails",
                Status.WARN,
                Severity.MEDIUM,
                "no guardrails declared — capability ships with no adapter-carried guardrail prose",
                0,
            )
        )
    return results


def main(argv: list[str] | None = None) -> int:
    """Lint a canonical spec and print results.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        0 if no FAIL results, else 1.
    """
    import argparse

    parser = argparse.ArgumentParser(
        prog="trapezia-canonical-spec-lint",
        description="Lint a Trapezia canonical skill-spec YAML.",
    )
    parser.add_argument("spec_path", type=Path, help="path to the canonical spec YAML")
    args = parser.parse_args(argv)

    results = lint_spec(args.spec_path)
    icon = {Status.PASS: "PASS", Status.WARN: "WARN", Status.FAIL: "FAIL"}
    for r in results:
        sys.stdout.write(f"[{icon[r.status]}] {r.id}: {r.message}\n")
    return 0 if all(r.status is not Status.FAIL for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run to verify it passes.**

Run: `pytest tests/test_spec_lint.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Lint the real manifest end-to-end.**

Run: `trapezia-canonical-spec-lint specs/trapezia-commercial-policy-check.yaml`
Expected: `[PASS] spec.valid: ...` and `[PASS] spec.guardrails: ...`, exit 0.

- [ ] **Step 6: Commit.**

```bash
git add src/trapezia_skill_validator/spec_lint.py tests/test_spec_lint.py
git commit -m "feat(validator): additive canonical-spec linter + entry point"
```

---

### Task 11: Deploy/validate the three wrappers + graduation decision

**Files:** `docs/superhuman/notes/2026-07-17-phase1-validation.md` (new evidence doc)

These are validation checkpoints, not code. Hermes validation depends on Phase 0 (HermesLab live).

- [ ] **Step 1: CC wrapper on the laptop.** Copy `generated/claude_code/trapezia-commercial-policy-check/SKILL.md` into a throwaway `~/.claude/skills/trapezia-commercial-policy-check-poc/SKILL.md`, start a CC session, confirm the skill is discoverable and its description triggers appropriately. Record the result. (No container.)

- [ ] **Step 2: OpenClaw wrapper in OrionLab** (existing Lab tier — normal Lab-tier activity, no promotion gate). Deploy `generated/openclaw/trapezia-commercial-policy-check/SKILL.md` into OrionLab's skills dir via the orion-compose `skill_deploy.sh` path; confirm it loads and registers. Record the result. (Policy-check MCP must be reachable from OrionLab — it already is per its OrionLab deployment.)

- [ ] **Step 3: Hermes wrapper in HermesLab** (requires Phase 0 complete). Place `generated/hermes/trapezia-commercial-policy-check/SKILL.md` into `/opt/hermeslab/data/skills/insure/trapezia-commercial-policy-check/SKILL.md`; confirm it registers as the `/trapezia-commercial-policy-check` slash command and can drive a check. Record the result. **Do not hand-edit the deployed file** — it is generated output.

- [ ] **Step 4: Record the Phase 1 exit / graduation decision (spec §4.5).** With evidence in hand, decide and document whether the generator stays in `trapezia-skill-validator` (merge branch → master) or extracts to its own repo (`trapezia-skill-spec`, carrying history). Deciding factors: whether jinja2 + per-harness format knowledge should live in a package validator consumers install, and whether the generator has become a product tool. Commit the note and summarize the decision on roadmap #128.

```bash
git add docs/superhuman/notes/2026-07-17-phase1-validation.md
git commit -m "docs(poc): Phase 1 validation evidence + graduation decision"
```

---

## Self-review

**1. Spec coverage (§4):**
- §4.1 canonical skill-spec → Tasks 2, 3.
- §4.2 generator emits Hermes/OpenClaw/CC → Tasks 4–8; committed outputs + CI regeneration check → Tasks 8, 9.
- §4.3 validator canonical-spec linter (additive) → Task 10; incubation on branch → whole plan on `multi-harness-poc`.
- §4.4 deploy wrappers (Hermes/OrionLab/laptop) → Task 11.
- §4.5 graduation decision → Task 11 Step 4.
- OQ-3 (model_tier advisory; Hermes omits) → Tasks 5–7 (tests `test_hermes_omits_model_tier`, `test_*_surfaces_model_tier_as_note`).

**2. Placeholder scan:** every code step shows complete code; every run step shows the command + expected output. No TBD/"add error handling"/"similar to Task N". Clear.

**3. Type consistency:** `CanonicalSpec`/`Invocation`/`Guardrail` fields defined in Task 2 are used unchanged in `build_context` (Task 4) and `lint_spec` (Task 10). `generate(spec, harness)` and `HARNESSES` (Task 4) are used identically in Tasks 5–9. `CheckResult(id, status, severity, message, min_level)` matches the existing `models.py` signature. The generated output path `generated/<harness>/<name>/SKILL.md` is identical in `cli._write_output` (Task 8) and `test_regeneration` (Task 9). Consistent.

**Dependency ordering note:** Task 10's `test_spec_lint.py` and Task 9's `test_regeneration.py` both require earlier tasks' artifacts (the spec, the committed outputs). The full-suite green check is at Task 9 Step 4 and re-confirmed after Task 10 — run tasks in order.
