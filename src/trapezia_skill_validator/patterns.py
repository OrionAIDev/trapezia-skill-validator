"""Load the non-secret sensitive-data shape patterns shipped with the package."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files


@dataclass(frozen=True)
class ShapePatterns:
    """Non-secret sensitive-data shape patterns.

    Args:
        path_globs: globs for files that must never be committed.
        content_regexes: raw regex strings indicating PII/PHI content.
    """

    path_globs: tuple[str, ...]
    content_regexes: tuple[str, ...]

    def matches_content(self, text: str) -> bool:
        """Return True if any content regex matches ``text``."""
        return any(re.search(rx, text) for rx in self.content_regexes)


@lru_cache(maxsize=1)
def load_shape_patterns() -> ShapePatterns:
    """Load and cache the bundled shape patterns.

    Returns:
        ShapePatterns parsed from ``data/sensitive_patterns.toml``.
    """
    raw = (
        files("trapezia_skill_validator")
        .joinpath("data/sensitive_patterns.toml")
        .read_text(encoding="utf-8")
    )
    data = tomllib.loads(raw)
    return ShapePatterns(
        path_globs=tuple(data.get("path_globs", [])),
        content_regexes=tuple(data.get("content_regexes", [])),
    )
