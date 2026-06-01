"""Tests for data-separation and secret-scan checks."""

from __future__ import annotations

from pathlib import Path

from trapezia_skill_validator import checks  # noqa: F401
from trapezia_skill_validator.context import AuditContext
from trapezia_skill_validator.models import Status
from trapezia_skill_validator.registry import CHECKS


def _run(check_id: str, root: Path):
    ctx = AuditContext.build(root)
    check = next(c for c in CHECKS if c.id == check_id)
    return check.fn(ctx)


def test_data_separation_flags_committed_data_dir(make_skill) -> None:
    root = make_skill("salus", {"data/patient.json": "{}\n"})  # salus → sensitive
    assert _run("data.separation", root).status is Status.FAIL


def test_data_separation_passes_when_clean(make_skill) -> None:
    root = make_skill("salus", {"scripts/run.py": "x = 1\n"})
    assert _run("data.separation", root).status is Status.PASS


def test_secrets_scan_flags_api_key(make_skill) -> None:
    leak = 'API_KEY = "sk-ant-0123456789abcdef0123456789abcdef"\n'
    root = make_skill("leaky", {"config.py": leak})
    assert _run("secrets.scan", root).status is Status.FAIL


def test_secrets_scan_passes_clean(make_skill) -> None:
    root = make_skill("clean", {"config.py": "TIMEOUT = 30\n"})
    assert _run("secrets.scan", root).status is Status.PASS
