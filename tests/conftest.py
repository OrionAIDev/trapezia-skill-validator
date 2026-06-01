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
            files["SKILL.md"] = (
                f"---\n"
                f"name: {name}\n"
                f"description: 'Use when you need a placeholder skill for testing. "
                f"Validates that the audit runner works end-to-end on a minimal skill.'\n"
                f"---\n"
            )
        for rel, content in files.items():
            write(root / rel, content)
        return root

    return _make
