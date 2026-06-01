"""Parse YAML frontmatter from markdown files."""

from __future__ import annotations

import re
from typing import Any

import yaml

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


def parse_frontmatter(text: str) -> dict[str, Any]:
    """Extract YAML frontmatter from markdown text.

    Args:
        text: full file contents.

    Returns:
        Parsed frontmatter mapping, or an empty dict if absent or empty.
    """
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}
    return yaml.safe_load(match.group(1)) or {}
