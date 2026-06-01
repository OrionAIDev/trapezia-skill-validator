"""Tests for the CLI."""

from __future__ import annotations

import json
from pathlib import Path

from trapezia_skill_validator.cli import main


def test_cli_json_output(make_skill, capsys) -> None:
    root = make_skill("plain-tool")
    rc = main([str(root), "--json"])
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["skill_path"] == str(root)
    assert "results" in payload
    assert rc == 0


def test_cli_markdown_default(make_skill, capsys) -> None:
    root = make_skill("plain-tool")
    main([str(root)])
    out = capsys.readouterr().out
    assert "# Audit:" in out


def test_cli_returns_1_on_failure(make_skill) -> None:
    root = make_skill("salus", {"data/p.json": "{}\n"})  # data.separation FAIL
    rc = main([str(root)])
    assert rc == 1
