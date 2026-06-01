"""Sensitive-data separation and secret-scanning checks."""

from __future__ import annotations

import fnmatch
import re

from ..context import AuditContext
from ..models import CheckResult, Severity, Status
from ..registry import register
from ..walk import iter_files

# Conservative secret signatures; deterministic, low false-positive.
_SECRET_RES = (
    re.compile(r"sk-ant-[A-Za-z0-9]{24,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:api[_-]?key|secret|token)\b\s*[:=]\s*['\"][A-Za-z0-9/+_-]{16,}['\"]"),
)


@register("data.separation", min_level=0, sensitive_only=True)
def data_separation(ctx: AuditContext) -> CheckResult:
    """No sensitive-shaped files committed; if wordlist present, no matching content."""
    offenders: list[str] = []
    for path, rel in iter_files(ctx.root):
        rel_str = rel.as_posix()
        if any(fnmatch.fnmatch(rel_str, glob) for glob in ctx.patterns.path_globs):
            offenders.append(rel_str)

    # Optional: grep tracked content against the secret PHI wordlist (reuse, not duplicate).
    if ctx.phi_wordlist_path is not None:
        words = [
            w.strip()
            for w in ctx.phi_wordlist_path.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.startswith("#")
        ]
        for path, rel in iter_files(ctx.root):
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(word in text for word in words):
                offenders.append(f"{rel.as_posix()} (PHI wordlist hit)")

    if offenders:
        return CheckResult(
            "data.separation",
            Status.FAIL,
            Severity.CRITICAL,
            f"sensitive data in repo: {', '.join(sorted(set(offenders))[:5])}",
            0,
        )
    return CheckResult("data.separation", Status.PASS, Severity.CRITICAL, "ok", 0)


@register("secrets.scan", min_level=0)
def secrets_scan(ctx: AuditContext) -> CheckResult:
    """No obvious committed secrets (API keys, private keys)."""
    offenders: list[str] = []
    for path, rel in iter_files(ctx.root):
        if path.suffix in {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".zip"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(rx.search(text) for rx in _SECRET_RES):
            offenders.append(rel.as_posix())
    if offenders:
        return CheckResult(
            "secrets.scan",
            Status.FAIL,
            Severity.CRITICAL,
            f"possible secret(s) in: {', '.join(sorted(set(offenders))[:5])}",
            0,
        )
    return CheckResult("secrets.scan", Status.PASS, Severity.CRITICAL, "ok", 0)
