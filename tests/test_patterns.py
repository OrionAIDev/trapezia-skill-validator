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
