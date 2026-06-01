"""trapezia-skill-validator: deterministic conformance checks for Trapezia skills."""

from __future__ import annotations

from .models import AuditReport, CheckResult, Severity, Status
from .runner import render_markdown, run_audit
from .tiers import SkillTier, classify

__version__ = "0.1.0"

__all__ = [
    "AuditReport",
    "CheckResult",
    "Severity",
    "Status",
    "SkillTier",
    "classify",
    "render_markdown",
    "run_audit",
    "__version__",
]
