"""Additive canonical-spec linter: does not touch run_audit/CHECKS."""

from __future__ import annotations

import textwrap
from pathlib import Path

from trapezia_skill_validator.models import Status
from trapezia_skill_validator.spec_lint import lint_spec, main

VALID = textwrap.dedent(
    """
    name: trapezia-commercial-policy-check
    spec_version: 0
    version: 0.1.0
    description: Run a commercial policy check.
    triggers: ["policy check"]
    invokes:
      - kind: mcp
        server: trapezia-commercial-policy-check
        transport: stdio
        tools: [health]
    guardrails:
      - id: g1
        text: Be careful.
    model_tier: sonnet
    harnesses: {hermes: {}}
    """
)


def _write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "spec.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_valid_spec_passes(tmp_path: Path) -> None:
    results = lint_spec(_write(tmp_path, VALID))
    assert all(r.status is Status.PASS for r in results)


def test_invalid_spec_fails_not_raises(tmp_path: Path) -> None:
    bad = VALID.replace("model_tier: sonnet", "model_tier: turbo")
    results = lint_spec(_write(tmp_path, bad))
    assert any(r.status is Status.FAIL for r in results)


def test_missing_guardrails_warns(tmp_path: Path) -> None:
    no_g = VALID.replace(
        "guardrails:\n  - id: g1\n    text: Be careful.\n", "guardrails: []\n"
    )
    results = lint_spec(_write(tmp_path, no_g))
    assert any(r.status is Status.WARN and r.id == "spec.guardrails" for r in results)


def test_cli_returns_nonzero_on_invalid(tmp_path: Path) -> None:
    bad = VALID.replace("transport: stdio", "transport: pigeon")
    assert main([str(_write(tmp_path, bad))]) == 1


def test_existing_check_api_untouched() -> None:
    # Guard: the additive linter must not change the run_audit/CHECKS contract.
    from trapezia_skill_validator.runner import run_audit  # noqa: F401
    from trapezia_skill_validator.registry import CHECKS  # noqa: F401
    assert callable(run_audit)


# --- Phase 2: cli / bundle rules ----------------------------------------------

CLI_B = textwrap.dedent(
    """
    name: policy-form-lister
    spec_version: 0
    version: 0.1.0
    description: List insurance form numbers.
    invokes:
      - kind: cli
        exec: python {skill_root}/scripts/list_forms.py
    bundle: [scripts/list_forms.py]
    guardrails:
      - id: g1
        text: Deterministic scan only.
    harnesses: {hermes: {category: insure}}
    """
)


def _layout_type_b(tmp_path: Path, exec_line: str | None = None) -> Path:
    """Write a type-B spec at specs/ with its skills/<name>/ assets present."""
    text = CLI_B if exec_line is None else CLI_B.replace(
        "exec: python {skill_root}/scripts/list_forms.py", f"exec: {exec_line}"
    )
    (tmp_path / "specs").mkdir(exist_ok=True)
    (tmp_path / "skills" / "policy-form-lister" / "scripts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "skills" / "policy-form-lister" / "scripts" / "list_forms.py").write_text(
        "print('ok')\n", encoding="utf-8"
    )
    spec = tmp_path / "specs" / "policy-form-lister.yaml"
    spec.write_text(text, encoding="utf-8")
    return spec


def test_clean_type_b_all_pass(tmp_path: Path) -> None:
    results = lint_spec(_layout_type_b(tmp_path))
    assert all(r.status is Status.PASS for r in results), [r.id for r in results if r.status is not Status.PASS]


def test_cli_exec_without_token_warns(tmp_path: Path) -> None:
    spec = _layout_type_b(tmp_path, exec_line="python scripts/list_forms.py")  # no {skill_root}
    results = lint_spec(spec)
    assert any(r.status is Status.WARN and r.id == "spec.exec-token" for r in results)


def test_bundle_missing_file_warns(tmp_path: Path) -> None:
    spec = _layout_type_b(tmp_path)
    (tmp_path / "skills" / "policy-form-lister" / "scripts" / "list_forms.py").unlink()
    results = lint_spec(spec)
    assert any(r.status is Status.WARN and r.id == "spec.bundle-exists" for r in results)
