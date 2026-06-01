"""Check registry. Check modules register their functions here at import time."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .context import AuditContext
from .models import CheckResult

CheckFn = Callable[[AuditContext], CheckResult]


@dataclass(frozen=True)
class Check:
    """A registered check.

    Args:
        id: dotted identifier.
        fn: callable taking an AuditContext and returning a CheckResult.
        min_level: tier level at/above which the check runs.
        sensitive_only: if True, runs only for +S skills.
    """

    id: str
    fn: CheckFn
    min_level: int
    sensitive_only: bool


CHECKS: list[Check] = []


def register(id: str, min_level: int, sensitive_only: bool = False):
    """Decorator that registers a check function into ``CHECKS``.

    Args:
        id: dotted check identifier.
        min_level: minimum tier level at which the check applies.
        sensitive_only: restrict to +S skills.

    Returns:
        The undecorated function (registration is the side effect).
    """

    def _wrap(fn: CheckFn) -> CheckFn:
        CHECKS.append(Check(id=id, fn=fn, min_level=min_level, sensitive_only=sensitive_only))
        return fn

    return _wrap


def applicable(check: Check, ctx: AuditContext) -> bool:
    """Return True if ``check`` should run against ``ctx``'s skill."""
    if check.sensitive_only and not ctx.tier.sensitive:
        return False
    return ctx.tier.level >= check.min_level
