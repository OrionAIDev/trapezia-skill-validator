"""Classify a skill directory into a tier level + sensitive flag."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

_SENSITIVE_KEYWORDS = ("salus", "medical", "wealth", "trader", "insure", "phi", "pii")


@dataclass(frozen=True)
class SkillTier:
    """Detected tier.

    Args:
        level: 0 (prompt-only), 1 (code), or 2 (deployed). Cumulative.
        sensitive: True when the skill handles sensitive data (+S modifier).
    """

    level: int
    sensitive: bool


def _has_code(root: Path) -> bool:
    """True if the skill ships executable code outside ``tests/``."""
    if (root / "scripts").is_dir():
        return True
    for pattern in ("*.py", "*.sh"):
        for path in root.rglob(pattern):
            rel = path.relative_to(root)
            if rel.parts and rel.parts[0] == "tests":
                continue
            return True
    return False


def _is_deployed(root: Path) -> bool:
    """True if the skill is versioned / git-tracked / changelogged."""
    return (
        (root / ".git").exists()
        or (root / "VERSION").is_file()
        or (root / "CHANGELOG.md").is_file()
    )


def _is_sensitive(root: Path) -> bool:
    """True if the skill declares or matches sensitive-data heuristics."""
    toml_path = root / ".trapezia-skill.toml"
    if toml_path.is_file():
        try:
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
            if bool(data.get("skill", {}).get("sensitive", False)):
                return True
        except tomllib.TOMLDecodeError:
            pass
    name = root.name.lower()
    return any(kw in name for kw in _SENSITIVE_KEYWORDS)


def classify(root: Path) -> SkillTier:
    """Classify the skill directory at ``root``.

    Args:
        root: skill root directory.

    Returns:
        SkillTier with cumulative level and sensitive flag.
    """
    if _is_deployed(root):
        level = 2
    elif _has_code(root):
        level = 1
    else:
        level = 0
    return SkillTier(level=level, sensitive=_is_sensitive(root))
