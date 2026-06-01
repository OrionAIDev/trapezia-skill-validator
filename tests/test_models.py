"""Tests for the result/report data models."""

from __future__ import annotations

from trapezia_skill_validator.models import (
    AuditReport,
    CheckResult,
    Severity,
    Status,
)


def test_checkresult_fields() -> None:
    r = CheckResult(
        id="frontmatter.valid",
        status=Status.PASS,
        severity=Severity.HIGH,
        message="ok",
        min_level=0,
    )
    assert r.id == "frontmatter.valid"
    assert r.status is Status.PASS
    assert r.ok is True


def test_checkresult_ok_false_on_fail() -> None:
    r = CheckResult("x", Status.FAIL, Severity.HIGH, "bad", 0)
    assert r.ok is False


def test_report_aggregates() -> None:
    results = [
        CheckResult("a", Status.PASS, Severity.LOW, "", 0),
        CheckResult("b", Status.FAIL, Severity.CRITICAL, "", 0),
        CheckResult("c", Status.WARN, Severity.MEDIUM, "", 1),
    ]
    report = AuditReport(skill_path="/tmp/s", level=2, sensitive=False, results=results)
    assert [r.id for r in report.failures] == ["b"]
    assert [r.id for r in report.warnings] == ["c"]
    assert report.passed is False


def test_report_passed_true_when_no_failures() -> None:
    results = [CheckResult("a", Status.PASS, Severity.LOW, "", 0)]
    report = AuditReport(skill_path="/tmp/s", level=0, sensitive=False, results=results)
    assert report.passed is True


def test_report_to_dict_roundtrips_status_names() -> None:
    report = AuditReport(
        skill_path="/tmp/s",
        level=1,
        sensitive=True,
        results=[CheckResult("a", Status.WARN, Severity.LOW, "msg", 1)],
    )
    d = report.to_dict()
    assert d["skill_path"] == "/tmp/s"
    assert d["level"] == 1
    assert d["sensitive"] is True
    assert d["results"][0] == {
        "id": "a",
        "status": "WARN",
        "severity": "LOW",
        "message": "msg",
        "min_level": 1,
    }
