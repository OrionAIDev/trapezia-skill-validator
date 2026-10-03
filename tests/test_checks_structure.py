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


def test_mypy_strict_passes_with_no_scripts_dir(make_skill) -> None:
    root = make_skill("noscripts")
    assert _run("mypy.strict", root).status is Status.PASS


def test_mypy_strict_passes_on_clean_typed_code(make_skill) -> None:
    root = make_skill(
        "typed",
        {"scripts/main.py": "from __future__ import annotations\n\n\ndef add(a: int, b: int) -> int:\n    return a + b\n"},
    )
    assert _run("mypy.strict", root).status is Status.PASS


def test_mypy_strict_fails_on_untyped_def(make_skill) -> None:
    root = make_skill(
        "untyped",
        {"scripts/main.py": "def add(a, b):\n    return a + b\n"},
    )
    assert _run("mypy.strict", root).status is Status.FAIL


def test_mypy_strict_passes_on_scripts_dir_with_no_python(make_skill) -> None:
    """A scripts/ dir holding only shell scripts has nothing for mypy to check."""
    root = make_skill("shellonly", {"scripts/run.sh": "#!/bin/sh\necho hi\n"})
    assert _run("mypy.strict", root).status is Status.PASS


def test_mypy_strict_runs_under_sys_executable(make_skill, monkeypatch) -> None:
    """mypy runs under the validator's own interpreter, not PATH's `python`."""
    import subprocess
    import sys

    from trapezia_skill_validator.checks import structure as mod

    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(mod.subprocess, "run", fake_run)
    root = make_skill("typed_exe", {"scripts/main.py": "x: int = 1\n"})

    assert _run("mypy.strict", root).status is Status.PASS
    assert len(calls) == 1
    assert calls[0][0] == sys.executable
    assert calls[0][1:3] == ["-m", "mypy"]


def test_mypy_strict_missing_mypy_warns_without_subprocess_sys_executable(
    make_skill, monkeypatch
) -> None:
    """Absence is detected with find_spec up front, never by running anything."""
    from trapezia_skill_validator.checks import structure as mod

    def fail_run(*args, **kwargs):
        raise AssertionError("subprocess.run must not be called when mypy is absent")

    monkeypatch.setattr(mod.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(mod.subprocess, "run", fail_run)
    root = make_skill("nomypy", {"scripts/main.py": "x: int = 1\n"})

    result = _run("mypy.strict", root)
    assert result.status is Status.WARN
    assert "mypy not installed" in result.message


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
