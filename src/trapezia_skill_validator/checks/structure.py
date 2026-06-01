"""Deterministic structural conformance checks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ..context import AuditContext
from ..models import CheckResult, Severity, Status
from ..registry import register
from ..walk import is_skipped

_TRIGGER_RE = re.compile(r"\buse\b[^.]{0,40}?\bwhen(ever)?\b", re.IGNORECASE)
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
    found = [
        p.name
        for p in ctx.root.rglob("*.md")
        if p.name in _ACTION_ITEM_NAMES and not is_skipped(p.relative_to(ctx.root))
    ]
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
        if (rel.parts and rel.parts[0] == "tests") or is_skipped(rel):
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
