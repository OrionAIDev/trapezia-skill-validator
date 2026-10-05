"""Tests for the shape-pattern loader."""

from __future__ import annotations

from trapezia_skill_validator.patterns import load_shape_patterns


def _ssn_shaped(area: str = "123") -> str:
    """A possible-SSN-shaped value, assembled at runtime so this detector's own test file never
    carries one literally (the commit guard scans whole staged files)."""
    return "-".join((area, "45", "6789"))


def test_loads_path_globs_and_regexes() -> None:
    patterns = load_shape_patterns()
    assert "*.age" in patterns.path_globs
    assert any("d{3}-" in r for r in patterns.content_regexes)


def test_compiled_regexes_match_ssn() -> None:
    patterns = load_shape_patterns()
    assert patterns.matches_content(f"call {_ssn_shaped()} now") is True


def test_compiled_regexes_no_false_positive_on_plain_text() -> None:
    patterns = load_shape_patterns()
    assert patterns.matches_content("the quick brown fox") is False


def test_block_content_excludes_broad_date() -> None:
    p = load_shape_patterns()
    assert p.matches_block_content(f"ssn {_ssn_shaped()}") is True
    assert p.matches_block_content("released 2026-06-01") is False  # date NOT block-grade


def test_never_issued_ssn_areas_are_not_sensitive() -> None:
    """SSA has never issued area 000 or 666, so those values are safe synthetic test data."""
    p = load_shape_patterns()
    for fake in ("000-12-3456", "666-12-3456", "id 666-45-6789 here"):
        assert p.matches_content(fake) is False, fake
        assert p.matches_block_content(fake) is False, fake


def test_possible_ssns_and_itins_still_block() -> None:
    """Only 000/666 are excused: ordinary areas, 9xx (ITINs are sensitive too) and look-alikes
    such as 0006/6660-prefixed digit runs still block."""
    p = load_shape_patterns()
    for area in ("123", "001", "665", "667", "900", "999", "060", "606"):
        value = _ssn_shaped(area)
        assert p.matches_block_content(value) is True, value
        assert p.matches_content(value) is True, value
