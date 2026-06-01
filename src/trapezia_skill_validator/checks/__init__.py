"""Importing this package self-registers all checks."""

from __future__ import annotations

from . import structure  # noqa: F401  (import for side-effect registration)

try:
    from . import data  # noqa: F401  (Task 8 — not yet implemented)
except ImportError:
    pass
