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


def test_description_with_use_whenever_passes(make_skill) -> None:
    """'Use whenever the user asks…' is a valid trigger — must PASS, not WARN."""
    desc = "Use whenever the user asks to check a skill for conformance issues before publishing."
    root = make_skill("d4", {"SKILL.md": f"---\nname: d4\ndescription: '{desc}'\n---\n"})
    assert _run("frontmatter.desc", root).status is Status.PASS


def test_description_with_use_this_skill_when_passes(make_skill) -> None:
    """'Use this skill when you need…' is a valid trigger — must PASS, not WARN."""
    desc = "Use this skill when you need to audit a Trapezia skill directory for conformance."
    root = make_skill("d5", {"SKILL.md": f"---\nname: d5\ndescription: '{desc}'\n---\n"})
    assert _run("frontmatter.desc", root).status is Status.PASS


def test_description_with_use_this_when_passes(make_skill) -> None:
    """'Use this when…' is a valid trigger — must PASS, not WARN."""
    desc = "Use this when the codebase needs a full structural conformance scan before release."
    root = make_skill("d6", {"SKILL.md": f"---\nname: d6\ndescription: '{desc}'\n---\n"})
    assert _run("frontmatter.desc", root).status is Status.PASS


def test_description_with_no_trigger_still_warns(make_skill) -> None:
    """A description with no 'use…when' phrase at all must still WARN."""
    desc = "This does many things across the codebase always, comprehensively, and thoroughly."
    root = make_skill("d7", {"SKILL.md": f"---\nname: d7\ndescription: '{desc}'\n---\n"})
    assert _run("frontmatter.desc", root).status is Status.WARN


def test_readme_missing_fails(make_skill) -> None:
    root = make_skill("noreadme", {"scripts/x.py": "x = 1\n"})  # T1 → readme required
    assert _run("readme.present", root).status is Status.FAIL


def test_no_action_items_fails_when_present(make_skill) -> None:
    root = make_skill("ai", {"ACTION_ITEMS.md": "- do thing\n"})
    assert _run("no_action_items", root).status is Status.FAIL


def test_docstrings_ignores_venv_and_vendored(make_skill) -> None:
    """docstrings.present must not walk into .venv/site-packages."""
    root = make_skill(
        "venvskill",
        {
            "scripts/main.py": '"""Has a docstring."""\nx = 1\n',
            ".venv/Lib/site-packages/vendored.py": "x = 1\n",  # no docstring, must be ignored
        },
    )
    assert _run("docstrings.present", root).status is Status.PASS


def test_no_action_items_ignores_venv_and_vendored(make_skill) -> None:
    """no_action_items must not flag TODO.md shipped inside .venv."""
    root = make_skill(
        "venvskill2",
        {
            "scripts/main.py": '"""Has a docstring."""\nx = 1\n',
            ".venv/Lib/site-packages/somepkg/TODO.md": "- vendored todo\n",  # must be ignored
        },
    )
    assert _run("no_action_items", root).status is Status.PASS
