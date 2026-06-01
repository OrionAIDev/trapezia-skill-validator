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
