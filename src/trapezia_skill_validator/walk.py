"""Shared filesystem-walk helpers: which directories to skip when scanning a skill."""

from __future__ import annotations

from pathlib import Path
from typing import Iterator

# Directories never relevant to conformance: VCS, caches, virtualenvs, vendored deps.
SKIP_DIRS = frozenset({".git", "__pycache__", ".venv", "venv", "node_modules", "site-packages"})


def is_skipped(rel: Path) -> bool:
    """True if any path component of ``rel`` is a skip directory."""
    return any(part in SKIP_DIRS for part in rel.parts)


def iter_files(root: Path) -> Iterator[tuple[Path, Path]]:
    """Yield (absolute_path, relative_path) for files under ``root``, skipping SKIP_DIRS."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_skipped(rel):
            continue
        yield path, rel
