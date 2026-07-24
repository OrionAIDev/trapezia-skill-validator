"""CLI: generate one harness, or --all into generated/<harness>/<name>/SKILL.md."""

from __future__ import annotations

from pathlib import Path

from trapezia_skill_spec.cli import main

SPEC = "specs/trapezia-commercial-policy-check.yaml"


def test_generate_single_harness_to_stdout(capsys) -> None:
    rc = main([SPEC, "--harness", "hermes"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "name: trapezia-commercial-policy-check" in out


def test_generate_all_writes_three_files(tmp_path: Path) -> None:
    rc = main([SPEC, "--all", "--out", str(tmp_path)])
    assert rc == 0
    for harness in ("hermes", "openclaw", "claude_code"):
        p = tmp_path / harness / "trapezia-commercial-policy-check" / "SKILL.md"
        assert p.is_file(), f"missing {p}"
        assert "trapezia-commercial-policy-check" in p.read_text(encoding="utf-8")
