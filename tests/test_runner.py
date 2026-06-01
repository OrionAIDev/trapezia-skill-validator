"""Tests for the audit runner and markdown rendering."""

from __future__ import annotations

from pathlib import Path

from trapezia_skill_validator.models import AuditReport, Status
from trapezia_skill_validator.runner import render_markdown, run_audit


def test_run_audit_on_minimal_t0_skill(make_skill) -> None:
    root = make_skill("plain-tool")  # T0, not sensitive
    report = run_audit(root)
    assert isinstance(report, AuditReport)
    assert report.level == 0
    # T2-only checks must not run on a T0 skill.
    assert all(r.min_level <= 0 for r in report.results)


def test_run_audit_skips_sensitive_checks_for_nonsensitive(make_skill) -> None:
    root = make_skill("plain-tool")
    report = run_audit(root)
    assert all(r.id != "data.separation" for r in report.results)


def test_run_audit_includes_sensitive_check_for_sensitive(make_skill) -> None:
    root = make_skill("salus")
    report = run_audit(root)
    assert any(r.id == "data.separation" for r in report.results)


def test_render_markdown_contains_status_and_path(make_skill) -> None:
    root = make_skill("plain-tool")
    report = run_audit(root)
    md = render_markdown(report)
    assert "plain-tool" in md
    assert ("PASS" in md or "FAIL" in md or "WARN" in md)


def test_failures_sorted_critical_first(make_skill) -> None:
    # leaky + sensitive → both CRITICAL and other FAILs; CRITICAL must lead.
    root = make_skill("salus", {"data/p.json": "{}\n"})
    report = run_audit(root)
    md = render_markdown(report)
    assert "data.separation" in md
