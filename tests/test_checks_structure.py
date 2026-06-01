"""Tests for structural checks."""

from __future__ import annotations

from pathlib import Path

import pytest

from trapezia_skill_validator.checks import structure  # noqa: F401  (registers checks)
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
