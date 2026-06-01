"""Per-run shared state handed to every check."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .frontmatter import parse_frontmatter
from .patterns import ShapePatterns, load_shape_patterns
from .tiers import SkillTier, classify


@dataclass
class AuditContext:
    """Everything a check needs to run.

    Args:
        root: skill root directory.
        tier: detected tier.
        frontmatter: parsed SKILL.md frontmatter (empty dict if missing).
        patterns: bundled sensitive-data shape patterns.
        phi_wordlist_path: path to the secret PHI wordlist, if the env var is set.
    """

    root: Path
    tier: SkillTier
    frontmatter: dict[str, Any] = field(default_factory=dict)
    patterns: ShapePatterns = field(default_factory=load_shape_patterns)
    phi_wordlist_path: Path | None = None

    @classmethod
    def build(cls, root: Path) -> "AuditContext":
        """Construct a context for the skill at ``root``."""
        root = Path(root).resolve()
        skill_md = root / "SKILL.md"
        fm = (
            parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            if skill_md.is_file()
            else {}
        )
        env = os.environ.get("TRAPEZIA_PHI_WORDLIST")
        wordlist = Path(env) if env and Path(env).is_file() else None
        return cls(
            root=root,
            tier=classify(root),
            frontmatter=fm,
            patterns=load_shape_patterns(),
            phi_wordlist_path=wordlist,
        )
