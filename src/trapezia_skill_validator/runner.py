"""Run all applicable checks and render reports."""

from __future__ import annotations

from pathlib import Path

from . import checks  # noqa: F401  (registers all checks at import)
from .context import AuditContext
from .models import AuditReport, Severity, Status
from .registry import CHECKS, applicable

_SEVERITY_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
}


def run_audit(root: Path) -> AuditReport:
    """Run every applicable check against the skill at ``root``.

    Args:
        root: skill root directory.

    Returns:
        An AuditReport with one result per applicable check.
    """
    ctx = AuditContext.build(root)
    results = [check.fn(ctx) for check in CHECKS if applicable(check, ctx)]
    return AuditReport(
        skill_path=str(ctx.root),  # use ctx.root (resolved absolute path)
        level=ctx.tier.level,
        sensitive=ctx.tier.sensitive,
        results=results,
    )


def render_markdown(report: AuditReport) -> str:
    """Render a human-readable markdown report with a prioritized fix list.

    Args:
        report: an AuditReport.

    Returns:
        Markdown string.
    """
    icon = {Status.PASS: "✅", Status.WARN: "⚠️", Status.FAIL: "❌"}
    lines = [
        f"# Audit: {Path(report.skill_path).name}",
        "",
        f"- Path: `{report.skill_path}`",
        f"- Tier: T{report.level}{' +S' if report.sensitive else ''}",
        f"- Result: {'PASS' if report.passed else 'FAIL'} "
        f"({len(report.failures)} fail, {len(report.warnings)} warn)",
        "",
        "## Checks",
        "",
        "| Check | Status | Severity | Message |",
        "|---|---|---|---|",
    ]
    for r in report.results:
        lines.append(
            f"| `{r.id}` | {icon[r.status]} {r.status.value} | {r.severity.value} | {r.message} |"
        )

    fixes = sorted(
        report.failures + report.warnings,
        key=lambda r: (_SEVERITY_ORDER[r.severity], r.status is not Status.FAIL),
    )
    if fixes:
        lines += ["", "## Prioritized fixes", ""]
        for i, r in enumerate(fixes, 1):
            lines.append(f"{i}. **[{r.severity.value}] `{r.id}`** — {r.message}")
    return "\n".join(lines) + "\n"
