"""Importing this package self-registers all checks."""

from __future__ import annotations

from . import data, structure  # noqa: F401  (import for side-effect registration)
