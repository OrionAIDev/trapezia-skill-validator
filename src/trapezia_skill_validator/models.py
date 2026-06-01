"""Data models for audit checks and reports. Pure data, no I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Status(str, Enum):
    """Outcome of a single check."""

    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


class Severity(str, Enum):
    """How much a failure matters, for ordering the fix list."""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class CheckResult:
    """Result of one conformance check.

    Args:
        id: dotted check identifier, e.g. ``frontmatter.valid``.
        status: PASS / WARN / FAIL.
        severity: relative importance for fix ordering.
        message: human-readable explanation.
        min_level: tier level (0/1/2) at which the check applies.
    """

    id: str
    status: Status
    severity: Severity
    message: str
    min_level: int

    @property
    def ok(self) -> bool:
        """True unless the check FAILed."""
        return self.status is not Status.FAIL


@dataclass
class AuditReport:
    """Aggregated results of an audit run.

    Args:
        skill_path: path to the audited skill.
        level: detected tier level (0/1/2).
        sensitive: whether the skill handles sensitive data (+S).
        results: per-check results.
    """

    skill_path: str
    level: int
    sensitive: bool
    results: list[CheckResult] = field(default_factory=list)

    @property
    def failures(self) -> list[CheckResult]:
        """All FAIL results."""
        return [r for r in self.results if r.status is Status.FAIL]

    @property
    def warnings(self) -> list[CheckResult]:
        """All WARN results."""
        return [r for r in self.results if r.status is Status.WARN]

    @property
    def passed(self) -> bool:
        """True when there are no FAIL results."""
        return not self.failures

    def to_dict(self) -> dict:
        """Return a JSON-serializable representation."""
        return {
            "skill_path": self.skill_path,
            "level": self.level,
            "sensitive": self.sensitive,
            "results": [
                {
                    "id": r.id,
                    "status": r.status.value,
                    "severity": r.severity.value,
                    "message": r.message,
                    "min_level": r.min_level,
                }
                for r in self.results
            ],
        }
