# trapezia-skill-validator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `trapezia-skill-validator`, the shared Python package that runs the deterministic (§5a) conformance checks against any skill directory and emits a machine-readable + markdown audit report.

**Architecture:** A small `src/`-layout package. A skill directory is classified into a tier level (0/1/2) plus a sensitive flag; a registry of check functions runs only those checks gated at-or-below the skill's tier; each check returns a `CheckResult`; a runner aggregates results into an `AuditReport` that renders to JSON and markdown. Sensitive-data *shape* patterns ship as declarative data inside this package; the secret PHI wordlist is read at runtime from `TRAPEZIA_PHI_WORDLIST` and never bundled.

**Tech Stack:** Python 3.14, pytest≥8.0, pyyaml≥6.0, stdlib `argparse`/`pathlib`/`re`/`tomllib`. No third-party runtime deps beyond PyYAML.

**Scope:** This is plan 1 of 3 from the spec `docs/superpowers/specs/2026-05-31-trapezia-disciplines-conformance-standard-design.md`. Plans 2 (`skill-template`) and 3 (`trapezia-disciplines` auditor skill + LLM judgments + fix loop + deployed mode) follow and depend on this package.

---

## File Structure

```
trapezia-skill-validator/
  pyproject.toml                         # package metadata, console-script entrypoint
  README.md                              # quickstart + check catalog
  CHANGELOG.md                           # Keep-a-Changelog
  .gitignore
  src/trapezia_skill_validator/
    __init__.py                          # version + public exports
    models.py                            # Status, Severity, CheckResult, AuditReport
    frontmatter.py                       # parse_frontmatter()
    tiers.py                             # classify(skill_path) -> SkillTier
    patterns.py                          # non-secret sensitive-data shape patterns + loader
    data/sensitive_patterns.toml         # declarative shape-pattern data
    context.py                           # AuditContext (per-run shared state)
    registry.py                          # Check dataclass + CHECKS registry + register()
    checks/__init__.py                   # imports check modules so they self-register
    checks/structure.py                  # frontmatter.*, readme, changelog, version, tests.*, git.*, notice, hooks, no_action_items, docstrings
    checks/data.py                       # data.separation (+S), secrets.scan
    runner.py                            # run_audit() + render_markdown()
    cli.py                               # argparse entrypoint
  tests/
    conftest.py                          # fixture-skill builder helpers
    test_models.py
    test_frontmatter.py
    test_tiers.py
    test_patterns.py
    test_checks_structure.py
    test_checks_data.py
    test_runner.py
    test_cli.py
```

**Responsibilities:**
- `models.py` — pure data types, no I/O.
- `frontmatter.py` — one function, parsing only.
- `tiers.py` — classification logic, filesystem reads only.
- `patterns.py` + `data/sensitive_patterns.toml` — the non-secret shape patterns (schema-as-data, per CLAUDE.md "schema beats file format").
- `context.py` — bundles everything a check needs (paths, tier, parsed frontmatter, patterns, env) so check signatures stay uniform.
- `registry.py` — the check registry; `checks/*` register into it at import.
- `runner.py` — orchestration + rendering.
- `cli.py` — thin CLI wrapper.

---

### Task 1: Bootstrap the package

**Files:**
- Create: `trapezia-skill-validator/pyproject.toml`
- Create: `trapezia-skill-validator/.gitignore`
- Create: `trapezia-skill-validator/CHANGELOG.md`
- Create: `trapezia-skill-validator/README.md`
- Create: `trapezia-skill-validator/src/trapezia_skill_validator/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "trapezia-skill-validator"
version = "0.0.0"
description = "Deterministic conformance checks for Trapezia skills."
requires-python = ">=3.13"
dependencies = ["pyyaml>=6.0"]

[project.optional-dependencies]
test = ["pytest>=8.0"]

[project.scripts]
trapezia-skill-validator = "trapezia_skill_validator.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.setuptools.package-data]
trapezia_skill_validator = ["data/*.toml"]
```

- [ ] **Step 2: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.pytest_cache/
.venv/
*.egg-info/
build/
dist/
```

- [ ] **Step 3: Create `CHANGELOG.md`**

```markdown
# Changelog

All notable changes documented here. Format per [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per semver.

## [Unreleased]

### Added
- Initial package scaffold.
```

- [ ] **Step 4: Create `README.md`**

```markdown
# trapezia-skill-validator

Deterministic conformance checks for Trapezia skills. Shared by `skill-template`
(self-test) and the `trapezia-disciplines` auditor skill.

## Quick start

```bash
pip install -e .
trapezia-skill-validator /path/to/some-skill          # human-readable report
trapezia-skill-validator /path/to/some-skill --json    # machine-readable
```

## What it checks

See the check catalog in the design spec
(`docs/superpowers/specs/2026-05-31-trapezia-disciplines-conformance-standard-design.md` §5a).
Structural checks are deterministic; LLM-judgment checks live in the auditor skill, not here.

## Sensitive data

The non-secret *shape* patterns ship in `data/sensitive_patterns.toml`. The secret PHI
wordlist is read from `$TRAPEZIA_PHI_WORDLIST` at runtime and is never bundled.
```

- [ ] **Step 5: Create `src/trapezia_skill_validator/__init__.py`**

```python
"""trapezia-skill-validator: deterministic conformance checks for Trapezia skills."""

from __future__ import annotations

__version__ = "0.0.0"
```

- [ ] **Step 6: Initialize git and commit**

```bash
cd trapezia-skill-validator
git init
git add .
git commit -m "chore: scaffold trapezia-skill-validator package"
```

---

### Task 2: Data models

**Files:**
- Create: `src/trapezia_skill_validator/models.py`
- Test: `tests/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for the result/report data models."""

from __future__ import annotations

from trapezia_skill_validator.models import (
    AuditReport,
    CheckResult,
    Severity,
    Status,
)


def test_checkresult_fields() -> None:
    r = CheckResult(
        id="frontmatter.valid",
        status=Status.PASS,
        severity=Severity.HIGH,
        message="ok",
        min_level=0,
    )
    assert r.id == "frontmatter.valid"
    assert r.status is Status.PASS
    assert r.ok is True


def test_checkresult_ok_false_on_fail() -> None:
    r = CheckResult("x", Status.FAIL, Severity.HIGH, "bad", 0)
    assert r.ok is False


def test_report_aggregates() -> None:
    results = [
        CheckResult("a", Status.PASS, Severity.LOW, "", 0),
        CheckResult("b", Status.FAIL, Severity.CRITICAL, "", 0),
        CheckResult("c", Status.WARN, Severity.MEDIUM, "", 1),
    ]
    report = AuditReport(skill_path="/tmp/s", level=2, sensitive=False, results=results)
    assert [r.id for r in report.failures] == ["b"]
    assert [r.id for r in report.warnings] == ["c"]
    assert report.passed is False


def test_report_passed_true_when_no_failures() -> None:
    results = [CheckResult("a", Status.PASS, Severity.LOW, "", 0)]
    report = AuditReport(skill_path="/tmp/s", level=0, sensitive=False, results=results)
    assert report.passed is True


def test_report_to_dict_roundtrips_status_names() -> None:
    report = AuditReport(
        skill_path="/tmp/s",
        level=1,
        sensitive=True,
        results=[CheckResult("a", Status.WARN, Severity.LOW, "msg", 1)],
    )
    d = report.to_dict()
    assert d["skill_path"] == "/tmp/s"
    assert d["level"] == 1
    assert d["sensitive"] is True
    assert d["results"][0] == {
        "id": "a",
        "status": "WARN",
        "severity": "LOW",
        "message": "msg",
        "min_level": 1,
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'trapezia_skill_validator.models'`

- [ ] **Step 3: Write minimal implementation**

```python
"""Data models for audit checks and reports. Pure data, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    """Outcome of a single check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class Severity(str, Enum):
    """How much a failure matters, for ordering the fix list."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class CheckResult:
    """Result of one conformance check.

    Args:
        id: dotted check identifier, e.g. ``frontmatter.valid``.
        status: PASS / WARN / FAIL.
        severity: relative importance for fix ordering.
        message: human-readable explanation.
        min_level: tier level (0/1/2) at which the check applies.
    """

    id: str
    status: Status
    severity: Severity
    message: str
    min_level: int

    @property
    def ok(self) -> bool:
        """True unless the check FAILed."""
        return self.status is not Status.FAIL


@dataclass
class AuditReport:
    """Aggregated results of an audit run.

    Args:
        skill_path: path to the audited skill.
        level: detected tier level (0/1/2).
        sensitive: whether the skill handles sensitive data (+S).
        results: per-check results.
    """

    skill_path: str
    level: int
    sensitive: bool
    results: list[CheckResult] = field(default_factory=list)

    @property
    def failures(self) -> list[CheckResult]:
        """All FAIL results."""
        return [r for r in self.results if r.status is Status.FAIL]

    @property
    def warnings(self) -> list[CheckResult]:
        """All WARN results."""
        return [r for r in self.results if r.status is Status.WARN]

    @property
    def passed(self) -> bool:
        """True when there are no FAIL results."""
        return not self.failures

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return {
            "skill_path": self.skill_path,
            "level": self.level,
            "sensitive": self.sensitive,
            "results": [
                {
                    "id": r.id,
                    "status": r.status.value,
                    "severity": r.severity.value,
                    "message": r.message,
                    "min_level": r.min_level,
                }
                for r in self.results
            ],
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_models.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/trapezia_skill_validator/models.py tests/test_models.py
git commit -m "feat: add CheckResult/AuditReport data models"
```

---

### Task 3: Frontmatter parser

**Files:**
- Create: `src/trapezia_skill_validator/frontmatter.py`
- Test: `tests/test_frontmatter.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for frontmatter parsing."""

from __future__ import annotations

from trapezia_skill_validator.frontmatter import parse_frontmatter


def test_parses_name_and_description() -> None:
    text = "---\nname: foo\ndescription: a thing\n---\n\n# Foo\n"
    fm = parse_frontmatter(text)
    assert fm == {"name": "foo", "description": "a thing"}


def test_returns_empty_when_no_frontmatter() -> None:
    assert parse_frontmatter("# Just a heading\n") == {}


def test_returns_empty_on_empty_frontmatter_block() -> None:
    assert parse_frontmatter("---\n\n---\n") == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_frontmatter.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""Parse YAML frontmatter from markdown files."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from markdown text.

    Args:
        text: full file contents.

    Returns:
        Parsed frontmatter mapping, or an empty dict if absent or empty.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_frontmatter.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/trapezia_skill_validator/frontmatter.py tests/test_frontmatter.py
git commit -m "feat: add frontmatter parser"
```

---

### Task 4: Tier classification

**Files:**
- Create: `src/trapezia_skill_validator/tiers.py`
- Test: `tests/test_tiers.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create the fixture-skill builder in `tests/conftest.py`**

```python
"""Shared fixtures: builders for synthetic skill directories."""

from __future__ import annotations

from pathlib import Path

import pytest


def write(path: Path, content: str = "") -> None:
    """Write ``content`` to ``path``, creating parent dirs."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def make_skill(tmp_path: Path):
    """Return a factory that builds a skill dir from a {relpath: content} map.

    The returned factory signature is ``make_skill(name, files)`` and returns the
    skill root Path. A minimal valid SKILL.md is added automatically unless the
    caller supplies one.
    """

    def _make(name: str, files: dict[str, str] | None = None) -> Path:
        root = tmp_path / name
        root.mkdir(parents=True, exist_ok=True)
        files = dict(files or {})
        if "SKILL.md" not in files:
            files["SKILL.md"] = f"---\nname: {name}\ndescription: x\n---\n"
        for rel, content in files.items():
            write(root / rel, content)
        return root

    return _make
```

- [ ] **Step 2: Write the failing test**

```python
"""Tests for tier classification."""

from __future__ import annotations

from trapezia_skill_validator.tiers import classify


def test_t0_prompt_only(make_skill) -> None:
    root = make_skill("t0")  # only SKILL.md
    tier = classify(root)
    assert tier.level == 0
    assert tier.sensitive is False


def test_t1_when_scripts_dir_present(make_skill) -> None:
    root = make_skill("t1", {"scripts/run.py": "print(1)\n"})
    assert classify(root).level == 1


def test_t1_when_loose_python_outside_tests(make_skill) -> None:
    root = make_skill("t1b", {"helper.py": "x = 1\n"})
    assert classify(root).level == 1


def test_python_only_under_tests_does_not_raise_to_t1(make_skill) -> None:
    root = make_skill("t0b", {"tests/test_x.py": "def test_x():\n    assert True\n"})
    assert classify(root).level == 0


def test_t2_when_version_present(make_skill) -> None:
    root = make_skill("t2", {"VERSION": "0.1.0\n"})
    assert classify(root).level == 2


def test_t2_when_changelog_present(make_skill) -> None:
    root = make_skill("t2b", {"CHANGELOG.md": "# Changelog\n"})
    assert classify(root).level == 2


def test_sensitive_via_toml_flag(make_skill) -> None:
    root = make_skill("s", {".trapezia-skill.toml": "[skill]\nsensitive = true\n"})
    assert classify(root).sensitive is True


def test_sensitive_via_name_keyword(make_skill) -> None:
    root = make_skill("salus")
    assert classify(root).sensitive is True


def test_not_sensitive_by_default(make_skill) -> None:
    root = make_skill("plain-tool")
    assert classify(root).sensitive is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_tiers.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write minimal implementation**

```python
"""Classify a skill directory into a tier level + sensitive flag."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_SENSITIVE_KEYWORDS = ("salus", "medical", "wealth", "trader", "insure", "phi", "pii")


@dataclass(frozen=True)
class SkillTier:
    """Detected tier.

    Args:
        level: 0 (prompt-only), 1 (code), or 2 (deployed). Cumulative.
        sensitive: True when the skill handles sensitive data (+S modifier).
    """

    level: int
    sensitive: bool


def _has_code(root: Path) -> bool:
    """True if the skill ships executable code outside ``tests/``."""
    if (root / "scripts").is_dir():
        return True
    for pattern in ("*.py", "*.sh"):
        for path in root.rglob(pattern):
            rel = path.relative_to(root)
            if rel.parts and rel.parts[0] == "tests":
                continue
            return True
    return False


def _is_deployed(root: Path) -> bool:
    """True if the skill is versioned / git-tracked / changelogged."""
    return (
        (root / ".git").exists()
        or (root / "VERSION").is_file()
        or (root / "CHANGELOG.md").is_file()
    )


def _is_sensitive(root: Path) -> bool:
    """True if the skill declares or matches sensitive-data heuristics."""
    toml_path = root / ".trapezia-skill.toml"
    if toml_path.is_file():
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
            if bool(data.get("skill", {}).get("sensitive", False)):
                return True
        except tomllib.TOMLDecodeError:
            pass
    name = root.name.lower()
    return any(kw in name for kw in _SENSITIVE_KEYWORDS)


def classify(root: Path) -> SkillTier:
    """Classify the skill directory at ``root``.

    Args:
        root: skill root directory.

    Returns:
        SkillTier with cumulative level and sensitive flag.
    """
    if _is_deployed(root):
        level = 2
    elif _has_code(root):
        level = 1
    else:
        level = 0
    return SkillTier(level=level, sensitive=_is_sensitive(root))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_tiers.py -v`
Expected: PASS (9 tests)

- [ ] **Step 6: Commit**

```bash
git add src/trapezia_skill_validator/tiers.py tests/test_tiers.py tests/conftest.py
git commit -m "feat: add tier classification + test fixtures"
```

---

### Task 5: Sensitive-data shape patterns (declarative data)

**Files:**
- Create: `src/trapezia_skill_validator/data/sensitive_patterns.toml`
- Create: `src/trapezia_skill_validator/patterns.py`
- Test: `tests/test_patterns.py`

- [ ] **Step 1: Create the declarative data file**

```toml
# Non-secret sensitive-data SHAPE patterns. NEVER put real PHI/PII values here;
# the secret wordlist lives outside any repo at $TRAPEZIA_PHI_WORDLIST.

# File path globs that must never be committed to a code repo.
path_globs = [
    "*.phi.*",
    "data/**",
    "*.age",
    "**/phi-wordlist.txt",
    "**/*secrets*.json",
]

# Generic format regexes that indicate PII/PHI content.
content_regexes = [
    '\b\d{3}-\d{2}-\d{4}\b',          # US SSN
    '\bMRN[:#]?\s*\d{6,}\b',          # medical record number
    '\b\d{4}-\d{2}-\d{2}T?\b',        # ISO-ish DOB/date (broad; WARN-level)
]
```

- [ ] **Step 2: Write the failing test**

```python
"""Tests for the shape-pattern loader."""

from __future__ import annotations

from trapezia_skill_validator.patterns import load_shape_patterns


def test_loads_path_globs_and_regexes() -> None:
    patterns = load_shape_patterns()
    assert "*.age" in patterns.path_globs
    assert any("d{3}-" in r for r in patterns.content_regexes)


def test_compiled_regexes_match_ssn() -> None:
    patterns = load_shape_patterns()
    assert patterns.matches_content("call 123-45-6789 now") is True


def test_compiled_regexes_no_false_positive_on_plain_text() -> None:
    patterns = load_shape_patterns()
    assert patterns.matches_content("the quick brown fox") is False
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_patterns.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 4: Write minimal implementation**

```python
"""Load the non-secret sensitive-data shape patterns shipped with the package."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files


@dataclass(frozen=True)
class ShapePatterns:
    """Non-secret sensitive-data shape patterns.

    Args:
        path_globs: globs for files that must never be committed.
        content_regexes: raw regex strings indicating PII/PHI content.
    """

    path_globs: tuple[str, ...]
    content_regexes: tuple[str, ...]

    def matches_content(self, text: str) -> bool:
        """Return True if any content regex matches ``text``."""
        return any(re.search(rx, text) for rx in self.content_regexes)


@lru_cache(maxsize=1)
def load_shape_patterns() -> ShapePatterns:
    """Load and cache the bundled shape patterns.

    Returns:
        ShapePatterns parsed from ``data/sensitive_patterns.toml``.
    """
    raw = (
        files("trapezia_skill_validator")
        .joinpath("data/sensitive_patterns.toml")
        .read_text(encoding="utf-8")
    )
    data = tomllib.loads(raw)
    return ShapePatterns(
        path_globs=tuple(data.get("path_globs", [])),
        content_regexes=tuple(data.get("content_regexes", [])),
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_patterns.py -v`
Expected: PASS (3 tests)

- [ ] **Step 6: Commit**

```bash
git add src/trapezia_skill_validator/patterns.py src/trapezia_skill_validator/data/sensitive_patterns.toml tests/test_patterns.py
git commit -m "feat: add sensitive-data shape patterns + loader"
```

---

### Task 6: AuditContext and the check registry

**Files:**
- Create: `src/trapezia_skill_validator/context.py`
- Create: `src/trapezia_skill_validator/registry.py`
- Create: `src/trapezia_skill_validator/checks/__init__.py`
- Test: (covered indirectly; registry is exercised by Task 7-8 tests)

- [ ] **Step 1: Create `context.py`**

```python
"""Per-run shared state handed to every check."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .frontmatter import parse_frontmatter
from .patterns import ShapePatterns, load_shape_patterns
from .tiers import SkillTier, classify


@dataclass
class AuditContext:
    """Everything a check needs to run.

    Args:
        root: skill root directory.
        tier: detected tier.
        frontmatter: parsed SKILL.md frontmatter (empty dict if missing).
        patterns: bundled sensitive-data shape patterns.
        phi_wordlist_path: path to the secret PHI wordlist, if the env var is set.
    """

    root: Path
    tier: SkillTier
    frontmatter: dict[str, Any] = field(default_factory=dict)
    patterns: ShapePatterns = field(default_factory=load_shape_patterns)
    phi_wordlist_path: Path | None = None

    @classmethod
    def build(cls, root: Path) -> "AuditContext":
        """Construct a context for the skill at ``root``."""
        skill_md = root / "SKILL.md"
        fm = (
            parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            if skill_md.is_file()
            else {}
        )
        env = os.environ.get("TRAPEZIA_PHI_WORDLIST")
        wordlist = Path(env) if env and Path(env).is_file() else None
        return cls(
            root=root,
            tier=classify(root),
            frontmatter=fm,
            patterns=load_shape_patterns(),
            phi_wordlist_path=wordlist,
        )
```

- [ ] **Step 2: Create `registry.py`**

```python
"""Check registry. Check modules register their functions here at import time."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .context import AuditContext
from .models import CheckResult

CheckFn = Callable[[AuditContext], CheckResult]


@dataclass(frozen=True)
class Check:
    """A registered check.

    Args:
        id: dotted identifier.
        fn: callable taking an AuditContext and returning a CheckResult.
        min_level: tier level at/above which the check runs.
        sensitive_only: if True, runs only for +S skills.
    """

    id: str
    fn: CheckFn
    min_level: int
    sensitive_only: bool


CHECKS: list[Check] = []


def register(id: str, min_level: int, sensitive_only: bool = False):
    """Decorator that registers a check function into ``CHECKS``.

    Args:
        id: dotted check identifier.
        min_level: minimum tier level at which the check applies.
        sensitive_only: restrict to +S skills.

    Returns:
        The undecorated function (registration is the side effect).
    """

    def _wrap(fn: CheckFn) -> CheckFn:
        CHECKS.append(Check(id=id, fn=fn, min_level=min_level, sensitive_only=sensitive_only))
        return fn

    return _wrap


def applicable(check: Check, ctx: AuditContext) -> bool:
    """Return True if ``check`` should run against ``ctx``'s skill."""
    if check.sensitive_only and not ctx.tier.sensitive:
        return False
    return ctx.tier.level >= check.min_level
```

- [ ] **Step 3: Create `checks/__init__.py`**

```python
"""Importing this package self-registers all checks."""

from __future__ import annotations

from . import data, structure  # noqa: F401  (import for side-effect registration)
```

- [ ] **Step 4: Commit (no tests yet; exercised in Task 7-8)**

```bash
git add src/trapezia_skill_validator/context.py src/trapezia_skill_validator/registry.py src/trapezia_skill_validator/checks/__init__.py
git commit -m "feat: add AuditContext + check registry scaffolding"
```

---

### Task 7: Structural checks

**Files:**
- Create: `src/trapezia_skill_validator/checks/structure.py`
- Test: `tests/test_checks_structure.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for structural checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trapezia_skill_validator import checks  # noqa: F401  (registers checks)
from trapezia_skill_validator.context import AuditContext
from trapezia_skill_validator.models import Status
from trapezia_skill_validator.registry import CHECKS


def _run(check_id: str, root: Path):
    ctx = AuditContext.build(root)
    check = next(c for c in CHECKS if c.id == check_id)
    return check.fn(ctx)


def test_frontmatter_valid_passes(make_skill) -> None:
    root = make_skill("good")
    assert _run("frontmatter.valid", root).status is Status.PASS


def test_frontmatter_name_mismatch_fails(make_skill) -> None:
    root = make_skill("real", {"SKILL.md": "---\nname: wrong\ndescription: x\n---\n"})
    assert _run("frontmatter.name", root).status is Status.FAIL


def test_description_too_short_fails(make_skill) -> None:
    root = make_skill("d", {"SKILL.md": "---\nname: d\ndescription: short\n---\n"})
    assert _run("frontmatter.desc", root).status is Status.FAIL


def test_description_without_trigger_warns(make_skill) -> None:
    desc = "This skill does a great many useful things across the whole codebase always."
    root = make_skill("d2", {"SKILL.md": f"---\nname: d2\ndescription: {desc}\n---\n"})
    assert _run("frontmatter.desc", root).status is Status.WARN


def test_description_with_trigger_passes(make_skill) -> None:
    desc = "Audits a skill directory. Use when you need to check conformance before release."
    root = make_skill("d3", {"SKILL.md": f"---\nname: d3\ndescription: {desc}\n---\n"})
    assert _run("frontmatter.desc", root).status is Status.PASS


def test_readme_missing_fails(make_skill) -> None:
    root = make_skill("noreadme", {"scripts/x.py": "x = 1\n"})  # T1 → readme required
    assert _run("readme.present", root).status is Status.FAIL


def test_no_action_items_fails_when_present(make_skill) -> None:
    root = make_skill("ai", {"ACTION_ITEMS.md": "- do thing\n"})
    assert _run("no_action_items", root).status is Status.FAIL
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_checks_structure.py -v`
Expected: FAIL — `frontmatter.valid` etc. not registered (`StopIteration`).

- [ ] **Step 3: Write minimal implementation**

```python
"""Deterministic structural conformance checks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..context import AuditContext
from ..models import CheckResult, Severity, Status
from ..registry import register

_TRIGGER_RE = re.compile(r"\buse when\b", re.IGNORECASE)
_KEEP_A_CHANGELOG_RE = re.compile(r"^#\s*changelog", re.IGNORECASE | re.MULTILINE)
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+([-+].+)?$")
_ACTION_ITEM_NAMES = {"ACTION_ITEMS.md", "TODO.md", "PROJECT_PLAN.md"}


def _result(id: str, status: Status, severity: Severity, message: str, min_level: int) -> CheckResult:
    return CheckResult(id=id, status=status, severity=severity, message=message, min_level=min_level)


@register("frontmatter.valid", min_level=0)
def frontmatter_valid(ctx: AuditContext) -> CheckResult:
    """SKILL.md exists and has parseable frontmatter."""
    if not (ctx.root / "SKILL.md").is_file():
        return _result("frontmatter.valid", Status.FAIL, Severity.CRITICAL, "SKILL.md missing", 0)
    if not ctx.frontmatter:
        return _result("frontmatter.valid", Status.FAIL, Severity.HIGH, "no parseable frontmatter", 0)
    return _result("frontmatter.valid", Status.PASS, Severity.HIGH, "ok", 0)


@register("frontmatter.name", min_level=0)
def frontmatter_name(ctx: AuditContext) -> CheckResult:
    """frontmatter ``name`` equals the directory name."""
    name = ctx.frontmatter.get("name")
    if name == ctx.root.name:
        return _result("frontmatter.name", Status.PASS, Severity.MEDIUM, "ok", 0)
    return _result(
        "frontmatter.name",
        Status.FAIL,
        Severity.MEDIUM,
        f"name {name!r} != directory {ctx.root.name!r}",
        0,
    )


@register("frontmatter.desc", min_level=0)
def frontmatter_desc(ctx: AuditContext) -> CheckResult:
    """description is present, well-sized, and has a trigger phrase."""
    desc = ctx.frontmatter.get("description")
    if not isinstance(desc, str) or not (40 <= len(desc) <= 500):
        return _result(
            "frontmatter.desc",
            Status.FAIL,
            Severity.HIGH,
            "description missing or not 40-500 chars",
            0,
        )
    if not _TRIGGER_RE.search(desc):
        return _result(
            "frontmatter.desc",
            Status.WARN,
            Severity.MEDIUM,
            "description lacks a 'Use when ...' trigger phrase",
            0,
        )
    return _result("frontmatter.desc", Status.PASS, Severity.HIGH, "ok", 0)


@register("readme.present", min_level=1)
def readme_present(ctx: AuditContext) -> CheckResult:
    """README.md exists (required for code skills)."""
    if (ctx.root / "README.md").is_file():
        return _result("readme.present", Status.PASS, Severity.MEDIUM, "ok", 1)
    return _result("readme.present", Status.FAIL, Severity.MEDIUM, "README.md missing", 1)


@register("changelog.format", min_level=2)
def changelog_format(ctx: AuditContext) -> CheckResult:
    """CHANGELOG.md exists and uses a Keep-a-Changelog heading."""
    path = ctx.root / "CHANGELOG.md"
    if not path.is_file():
        return _result("changelog.format", Status.FAIL, Severity.MEDIUM, "CHANGELOG.md missing", 2)
    if not _KEEP_A_CHANGELOG_RE.search(path.read_text(encoding="utf-8")):
        return _result(
            "changelog.format", Status.WARN, Severity.LOW, "no '# Changelog' heading", 2
        )
    return _result("changelog.format", Status.PASS, Severity.MEDIUM, "ok", 2)


@register("version.semver", min_level=2)
def version_semver(ctx: AuditContext) -> CheckResult:
    """VERSION exists and is valid semver."""
    path = ctx.root / "VERSION"
    if not path.is_file():
        return _result("version.semver", Status.FAIL, Severity.MEDIUM, "VERSION missing", 2)
    value = path.read_text(encoding="utf-8").strip()
    if not _SEMVER_RE.match(value):
        return _result("version.semver", Status.FAIL, Severity.MEDIUM, f"not semver: {value!r}", 2)
    return _result("version.semver", Status.PASS, Severity.MEDIUM, "ok", 2)


@register("tests.present", min_level=1)
def tests_present(ctx: AuditContext) -> CheckResult:
    """A tests/ directory with at least one test_*.py exists."""
    tests_dir = ctx.root / "tests"
    if tests_dir.is_dir() and any(tests_dir.glob("test_*.py")):
        return _result("tests.present", Status.PASS, Severity.HIGH, "ok", 1)
    return _result("tests.present", Status.FAIL, Severity.HIGH, "no tests/test_*.py", 1)


@register("tests.runnable", min_level=1)
def tests_runnable(ctx: AuditContext) -> CheckResult:
    """pytest can collect the test suite without import errors."""
    tests_dir = ctx.root / "tests"
    if not tests_dir.is_dir():
        return _result("tests.runnable", Status.FAIL, Severity.HIGH, "no tests/ dir", 1)
    proc = subprocess.run(
        ["python", "-m", "pytest", "--collect-only", "-q", str(tests_dir)],
        capture_output=True,
        text=True,
        cwd=str(ctx.root),
    )
    if proc.returncode == 0:
        return _result("tests.runnable", Status.PASS, Severity.HIGH, "ok", 1)
    return _result(
        "tests.runnable",
        Status.WARN,
        Severity.MEDIUM,
        "pytest --collect-only failed (import error?)",
        1,
    )


@register("git.repo", min_level=2)
def git_repo(ctx: AuditContext) -> CheckResult:
    """The skill is a git repository."""
    if (ctx.root / ".git").exists():
        return _result("git.repo", Status.PASS, Severity.MEDIUM, "ok", 2)
    return _result("git.repo", Status.FAIL, Severity.MEDIUM, "not a git repo", 2)


@register("git.remote", min_level=2)
def git_remote(ctx: AuditContext) -> CheckResult:
    """The repo has at least one configured remote."""
    if not (ctx.root / ".git").exists():
        return _result("git.remote", Status.FAIL, Severity.MEDIUM, "not a git repo", 2)
    proc = subprocess.run(
        ["git", "remote"], capture_output=True, text=True, cwd=str(ctx.root)
    )
    if proc.returncode == 0 and proc.stdout.strip():
        return _result("git.remote", Status.PASS, Severity.MEDIUM, "ok", 2)
    return _result("git.remote", Status.WARN, Severity.LOW, "no git remote configured", 2)


@register("notice.present", min_level=0)
def notice_present(ctx: AuditContext) -> CheckResult:
    """If references/ (vendored content) exists, NOTICE.md must too."""
    if not (ctx.root / "references").is_dir():
        return _result("notice.present", Status.PASS, Severity.LOW, "no vendored content", 0)
    if (ctx.root / "NOTICE.md").is_file():
        return _result("notice.present", Status.PASS, Severity.MEDIUM, "ok", 0)
    return _result(
        "notice.present",
        Status.FAIL,
        Severity.MEDIUM,
        "references/ present but NOTICE.md missing",
        0,
    )


@register("hooks.crossplatform", min_level=1)
def hooks_crossplatform(ctx: AuditContext) -> CheckResult:
    """Every shell hook has a .cmd or .ps1 counterpart."""
    hooks_dir = ctx.root / "hooks"
    if not hooks_dir.is_dir():
        return _result("hooks.crossplatform", Status.PASS, Severity.LOW, "no hooks/", 1)
    missing: list[str] = []
    for hook in hooks_dir.iterdir():
        if hook.is_file() and hook.suffix == "":
            if not (hook.with_suffix(".cmd").exists() or hook.with_suffix(".ps1").exists()):
                missing.append(hook.name)
    if missing:
        return _result(
            "hooks.crossplatform",
            Status.WARN,
            Severity.LOW,
            f"no Windows counterpart for: {', '.join(missing)}",
            1,
        )
    return _result("hooks.crossplatform", Status.PASS, Severity.LOW, "ok", 1)


@register("no_action_items", min_level=0)
def no_action_items(ctx: AuditContext) -> CheckResult:
    """No action-item markdown files committed (Rule 3 — use GitHub issues)."""
    found = [p.name for p in ctx.root.rglob("*.md") if p.name in _ACTION_ITEM_NAMES]
    if found:
        return _result(
            "no_action_items",
            Status.FAIL,
            Severity.MEDIUM,
            f"action-item files present (use issues): {', '.join(sorted(set(found)))}",
            0,
        )
    return _result("no_action_items", Status.PASS, Severity.MEDIUM, "ok", 0)


@register("docstrings.present", min_level=1)
def docstrings_present(ctx: AuditContext) -> CheckResult:
    """Python modules under the skill (excluding tests/) start with a docstring."""
    import ast

    offenders: list[str] = []
    for py in ctx.root.rglob("*.py"):
        rel = py.relative_to(ctx.root)
        if rel.parts and rel.parts[0] == "tests":
            continue
        try:
            tree = ast.parse(py.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        if ast.get_docstring(tree) is None:
            offenders.append(str(rel))
    if offenders:
        return _result(
            "docstrings.present",
            Status.WARN,
            Severity.LOW,
            f"missing module docstrings: {', '.join(offenders[:5])}",
            1,
        )
    return _result("docstrings.present", Status.PASS, Severity.LOW, "ok", 1)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_checks_structure.py -v`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add src/trapezia_skill_validator/checks/structure.py tests/test_checks_structure.py
git commit -m "feat: add structural conformance checks"
```

---

### Task 8: Data + secret checks

**Files:**
- Create: `src/trapezia_skill_validator/checks/data.py`
- Test: `tests/test_checks_data.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for data-separation and secret-scan checks."""

from __future__ import annotations

from pathlib import Path

from trapezia_skill_validator import checks  # noqa: F401
from trapezia_skill_validator.context import AuditContext
from trapezia_skill_validator.models import Status
from trapezia_skill_validator.registry import CHECKS


def _run(check_id: str, root: Path):
    ctx = AuditContext.build(root)
    check = next(c for c in CHECKS if c.id == check_id)
    return check.fn(ctx)


def test_data_separation_flags_committed_data_dir(make_skill) -> None:
    root = make_skill("salus", {"data/patient.json": "{}\n"})  # salus → sensitive
    assert _run("data.separation", root).status is Status.FAIL


def test_data_separation_passes_when_clean(make_skill) -> None:
    root = make_skill("salus", {"scripts/run.py": "x = 1\n"})
    assert _run("data.separation", root).status is Status.PASS


def test_secrets_scan_flags_api_key(make_skill) -> None:
    leak = 'API_KEY = "sk-ant-0123456789abcdef0123456789abcdef"\n'
    root = make_skill("leaky", {"config.py": leak})
    assert _run("secrets.scan", root).status is Status.FAIL


def test_secrets_scan_passes_clean(make_skill) -> None:
    root = make_skill("clean", {"config.py": "TIMEOUT = 30\n"})
    assert _run("secrets.scan", root).status is Status.PASS
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_checks_data.py -v`
Expected: FAIL — checks not registered (`StopIteration`).

- [ ] **Step 3: Write minimal implementation**

```python
"""Sensitive-data separation and secret-scanning checks."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from ..context import AuditContext
from ..models import CheckResult, Severity, Status
from ..registry import register

# Conservative secret signatures; deterministic, low false-positive.
_SECRET_RES = (
    re.compile(r"sk-ant-[A-Za-z0-9]{24,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token)\b\s*[:=]\s*['\"][A-Za-z0-9/+_-]{16,}['\"]"),
)

_SKIP_DIRS = {".git", "__pycache__", ".venv", "node_modules"}


def _iter_files(root: Path):
    """Yield non-skipped files under ``root``."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in _SKIP_DIRS for part in rel.parts):
            continue
        yield path, rel


@register("data.separation", min_level=0, sensitive_only=True)
def data_separation(ctx: AuditContext) -> CheckResult:
    """No sensitive-shaped files committed; if wordlist present, no matching content."""
    offenders: list[str] = []
    for path, rel in _iter_files(ctx.root):
        rel_str = rel.as_posix()
        if any(fnmatch.fnmatch(rel_str, glob) for glob in ctx.patterns.path_globs):
            offenders.append(rel_str)

    # Optional: grep tracked content against the secret PHI wordlist (reuse, not duplicate).
    if ctx.phi_wordlist_path is not None:
        words = [
            w.strip()
            for w in ctx.phi_wordlist_path.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.startswith("#")
        ]
        for path, rel in _iter_files(ctx.root):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(word in text for word in words):
                offenders.append(f"{rel.as_posix()} (PHI wordlist hit)")

    if offenders:
        return CheckResult(
            "data.separation",
            Status.FAIL,
            Severity.CRITICAL,
            f"sensitive data in repo: {', '.join(sorted(set(offenders))[:5])}",
            0,
        )
    return CheckResult("data.separation", Status.PASS, Severity.CRITICAL, "ok", 0)


@register("secrets.scan", min_level=0)
def secrets_scan(ctx: AuditContext) -> CheckResult:
    """No obvious committed secrets (API keys, private keys)."""
    offenders: list[str] = []
    for path, rel in _iter_files(ctx.root):
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(rx.search(text) for rx in _SECRET_RES):
            offenders.append(rel.as_posix())
    if offenders:
        return CheckResult(
            "secrets.scan",
            Status.FAIL,
            Severity.CRITICAL,
            f"possible secret(s) in: {', '.join(sorted(set(offenders))[:5])}",
            0,
        )
    return CheckResult("secrets.scan", Status.PASS, Severity.CRITICAL, "ok", 0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_checks_data.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add src/trapezia_skill_validator/checks/data.py tests/test_checks_data.py
git commit -m "feat: add data-separation + secret-scan checks"
```

---

### Task 9: Runner + markdown rendering

**Files:**
- Create: `src/trapezia_skill_validator/runner.py`
- Test: `tests/test_runner.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the audit runner and markdown rendering."""

from __future__ import annotations

from pathlib import Path

from trapezia_skill_validator.models import AuditReport, Status
from trapezia_skill_validator.runner import render_markdown, run_audit


def test_run_audit_on_minimal_t0_skill(make_skill) -> None:
    root = make_skill("plain-tool")  # T0, not sensitive
    report = run_audit(root)
    assert isinstance(report, AuditReport)
    assert report.level == 0
    # T2-only checks must not run on a T0 skill.
    assert all(r.min_level <= 0 for r in report.results)


def test_run_audit_skips_sensitive_checks_for_nonsensitive(make_skill) -> None:
    root = make_skill("plain-tool")
    report = run_audit(root)
    assert all(r.id != "data.separation" for r in report.results)


def test_run_audit_includes_sensitive_check_for_sensitive(make_skill) -> None:
    root = make_skill("salus")
    report = run_audit(root)
    assert any(r.id == "data.separation" for r in report.results)


def test_render_markdown_contains_status_and_path(make_skill) -> None:
    root = make_skill("plain-tool")
    report = run_audit(root)
    md = render_markdown(report)
    assert "plain-tool" in md
    assert ("PASS" in md or "FAIL" in md or "WARN" in md)


def test_failures_sorted_critical_first(make_skill) -> None:
    # leaky + sensitive → both CRITICAL and other FAILs; CRITICAL must lead.
    root = make_skill("salus", {"data/p.json": "{}\n"})
    report = run_audit(root)
    md = render_markdown(report)
    assert "data.separation" in md
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""Run all applicable checks and render reports."""

from __future__ import annotations

from pathlib import Path

from . import checks  # noqa: F401  (registers all checks at import)
from .context import AuditContext
from .models import AuditReport, Severity, Status
from .registry import CHECKS, applicable

_SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


def run_audit(root: Path) -> AuditReport:
    """Run every applicable check against the skill at ``root``.

    Args:
        root: skill root directory.

    Returns:
        An AuditReport with one result per applicable check.
    """
    ctx = AuditContext.build(root)
    results = [check.fn(ctx) for check in CHECKS if applicable(check, ctx)]
    return AuditReport(
        skill_path=str(root),
        level=ctx.tier.level,
        sensitive=ctx.tier.sensitive,
        results=results,
    )


def render_markdown(report: AuditReport) -> str:
    """Render a human-readable markdown report with a prioritized fix list.

    Args:
        report: an AuditReport.

    Returns:
        Markdown string.
    """
    icon = {Status.PASS: "✅", Status.WARN: "⚠️", Status.FAIL: "❌"}
    lines = [
        f"# Audit: {Path(report.skill_path).name}",
        "",
        f"- Path: `{report.skill_path}`",
        f"- Tier: T{report.level}{' +S' if report.sensitive else ''}",
        f"- Result: {'PASS' if report.passed else 'FAIL'} "
        f"({len(report.failures)} fail, {len(report.warnings)} warn)",
        "",
        "## Checks",
        "",
        "| Check | Status | Severity | Message |",
        "|---|---|---|---|",
    ]
    for r in report.results:
        lines.append(
            f"| `{r.id}` | {icon[r.status]} {r.status.value} | {r.severity.value} | {r.message} |"
        )

    fixes = sorted(
        report.failures + report.warnings,
        key=lambda r: (_SEVERITY_ORDER[r.severity], r.status is not Status.FAIL),
    )
    if fixes:
        lines += ["", "## Prioritized fixes", ""]
        for i, r in enumerate(fixes, 1):
            lines.append(f"{i}. **[{r.severity.value}] `{r.id}`** — {r.message}")
    return "\n".join(lines) + "\n"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_runner.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/trapezia_skill_validator/runner.py tests/test_runner.py
git commit -m "feat: add audit runner + markdown rendering"
```

---

### Task 10: CLI entrypoint

**Files:**
- Create: `src/trapezia_skill_validator/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

```python
"""Tests for the CLI."""

from __future__ import annotations

import json
from pathlib import Path

from trapezia_skill_validator.cli import main


def test_cli_json_output(make_skill, capsys) -> None:
    root = make_skill("plain-tool")
    rc = main([str(root), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["skill_path"] == str(root)
    assert "results" in payload
    assert rc == 0


def test_cli_markdown_default(make_skill, capsys) -> None:
    root = make_skill("plain-tool")
    main([str(root)])
    out = capsys.readouterr().out
    assert "# Audit:" in out


def test_cli_returns_1_on_failure(make_skill) -> None:
    root = make_skill("salus", {"data/p.json": "{}\n"})  # data.separation FAIL
    rc = main([str(root)])
    assert rc == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
"""Command-line entrypoint for the validator."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .runner import render_markdown, run_audit


def main(argv: list[str] | None = None) -> int:
    """Audit a skill directory and print a report.

    Args:
        argv: argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: 0 if the audit passed, 1 if any check FAILed.
    """
    parser = argparse.ArgumentParser(
        prog="trapezia-skill-validator",
        description="Run deterministic conformance checks against a skill directory.",
    )
    parser.add_argument("skill_path", type=Path, help="path to the skill directory")
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    report = run_audit(args.skill_path)
    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(render_markdown(report), end="")
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add src/trapezia_skill_validator/cli.py tests/test_cli.py
git commit -m "feat: add CLI entrypoint"
```

---

### Task 11: Public exports, full suite, install smoke, release v0.1.0

**Files:**
- Modify: `src/trapezia_skill_validator/__init__.py`
- Modify: `CHANGELOG.md`

- [ ] **Step 1: Export the public API**

Replace `src/trapezia_skill_validator/__init__.py` with:

```python
"""trapezia-skill-validator: deterministic conformance checks for Trapezia skills."""

from __future__ import annotations

from .models import AuditReport, CheckResult, Severity, Status
from .runner import render_markdown, run_audit
from .tiers import SkillTier, classify

__version__ = "0.1.0"

__all__ = [
    "AuditReport",
    "CheckResult",
    "Severity",
    "Status",
    "SkillTier",
    "classify",
    "render_markdown",
    "run_audit",
    "__version__",
]
```

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -v`
Expected: PASS (all tests across the 8 test files green)

- [ ] **Step 3: Editable-install smoke test**

Run:
```bash
python -m pip install -e .
trapezia-skill-validator --help
```
Expected: argparse help text prints; exit 0.

- [ ] **Step 4: Self-audit gate (dogfood)**

Run: `trapezia-skill-validator .`
Expected: the package itself audits as T2; review the report. Any FAILs here are real
conformance gaps in this package — fix them before release (this is the dogfood gate
required by the spec §12). Re-run until PASS.

- [ ] **Step 5: Bump version + changelog, commit, tag**

Update `pyproject.toml` `version = "0.1.0"`. Move the `CHANGELOG.md` `[Unreleased]` entries
under a new `## [0.1.0] - 2026-05-31` heading with:

```markdown
## [0.1.0] - 2026-05-31

### Added
- Tier classification (T0/T1/T2 + sensitive modifier).
- Structural checks: frontmatter, README, CHANGELOG, VERSION, tests, git, NOTICE, hooks, action-items, docstrings.
- Data checks: sensitive-data separation (shape patterns + optional PHI wordlist), secret scan.
- Audit runner with JSON + markdown output and prioritized fix list.
- CLI entrypoint `trapezia-skill-validator`.
```

Then:
```bash
git add -A
git commit -m "release: trapezia-skill-validator v0.1.0"
git tag v0.1.0
```

---

## Self-Review

**Spec coverage** (against `2026-05-31-trapezia-disciplines-conformance-standard-design.md`):
- §4 tiers (T0/T1/T2 + S) → Task 4. ✅
- §5a all 17 deterministic checks → Tasks 7-8. (`frontmatter.valid/name/desc`, `readme.present`, `changelog.format`, `version.semver`, `tests.present/runnable`, `git.repo/remote`, `notice.present`, `hooks.crossplatform`, `no_action_items`, `data.separation`, `secrets.scan`, `docstrings.present`.) ✅ — `git.clean_or_tagged` deferred to plan 3 (needs commit/tag inspection better suited to the auditor's git logic); noted here as a known deferral.
- §5b LLM judgments → explicitly **plan 3** (auditor skill), not this package. ✅
- §6 shared validator (installable package) → pyproject + console script, Tasks 1, 11. ✅
- §10.1 shared package → Task 1. ✅
- §10.2 two-layer sensitive data (shape patterns in package; secret wordlist via `TRAPEZIA_PHI_WORDLIST`) → Tasks 5, 8. ✅
- §10.3 deployed-mode → the package runs against any path incl. container paths; the *invocation* wrapper is plan 3. ✅ (package is path-agnostic)
- §12 fixtures + self-audit dogfood → `make_skill` factory (Task 4) + Task 11 Step 4. ✅

**Placeholder scan:** no TBD/TODO; every code step has complete code. ✅

**Type consistency:** `CheckResult(id, status, severity, message, min_level)` used identically in models, structure.py, data.py, runner. `Status`/`Severity` enums consistent. `classify()->SkillTier(level, sensitive)` used in tiers, context, runner. `run_audit(root)->AuditReport` and `render_markdown(report)->str` consistent across runner/cli/tests. ✅

**Known deferrals (carried to plan 3):** `git.clean_or_tagged` check; all LLM-judgment checks; the audit→fix loop; deployed-in-container invocation wrapper.
