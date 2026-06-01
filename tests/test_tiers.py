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
