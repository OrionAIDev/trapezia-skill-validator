"""Behavior tests for the policy-declarations-check CLI script.

Loaded by file path (mirrors that ``skills/<name>/scripts/`` is deployed
standalone, not a package of this repo).
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pytest

_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "skills"
    / "policy-declarations-check"
    / "scripts"
    / "extract_declarations.py"
)

_DECLARATIONS_TEXT = """
COMMERCIAL LINES POLICY DECLARATIONS

Named Insured: Acme Fabrication LLC
Policy Number: CLP-4471829-01
Carrier: Meridian Assurance Company

Policy Period: 03/01/2026 to 03/01/2027

COMMERCIAL GENERAL LIABILITY COVERAGE PART
Each Occurrence Limit: $1,000,000
General Aggregate Limit: $2,000,000

FORMS AND ENDORSEMENTS SCHEDULE
CG 00 01 04 13
CG 20 10 07 04
ACORD 25
"""


def _load_module() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location("extract_declarations", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod() -> types.ModuleType:
    return _load_module()


def test_extracts_all_recoverable_fields(mod: types.ModuleType) -> None:
    policy = mod.extract_declarations(_DECLARATIONS_TEXT)
    assert policy["policy_number"] == "CLP-4471829-01"
    assert policy["carrier_name"] == "Meridian Assurance Company"
    assert policy["named_insureds"] == ["Acme Fabrication LLC"]
    assert policy["policy_effective_date"] == "2026-03-01"
    assert policy["policy_expiration_date"] == "2027-03-01"
    assert policy["gl_each_occurrence"] == 1000000
    assert policy["gl_general_aggregate"] == 2000000
    # Normalized per the engine's convention: uppercase, spaces stripped,
    # edition suffix dropped.
    assert policy["forms_schedule"] == ["ACORD25", "CG0001", "CG2010"]


def test_missing_fields_are_omitted_not_guessed(mod: types.ModuleType) -> None:
    policy = mod.extract_declarations("Named Insured: Solo Freelancer LLC\n")
    assert policy == {"named_insureds": ["Solo Freelancer LLC"]}
    assert "policy_number" not in policy
    assert "gl_each_occurrence" not in policy
    assert "forms_schedule" not in policy


def test_empty_text_yields_empty_policy(mod: types.ModuleType) -> None:
    assert mod.extract_declarations("") == {}


def test_main_missing_input_file_exits_2(mod: types.ModuleType, tmp_path: Path) -> None:
    missing = tmp_path / "nope.txt"
    assert mod.main(["--input", str(missing)]) == 2


def test_main_prints_policy_json(
    mod: types.ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    doc = tmp_path / "policy.txt"
    doc.write_text(_DECLARATIONS_TEXT, encoding="utf-8")
    exit_code = mod.main(["--input", str(doc)])
    assert exit_code == 0
    out = capsys.readouterr().out
    assert '"policy"' in out
    assert "CLP-4471829-01" in out
