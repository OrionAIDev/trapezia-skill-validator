"""CLI: generate one harness, or --all into generated/<harness>/<name>/SKILL.md."""

from __future__ import annotations

import textwrap
from pathlib import Path

from trapezia_skill_spec.cli import main

SPEC = "specs/trapezia-commercial-policy-check.yaml"

CLI_SPEC = textwrap.dedent(
    """
    name: policy-form-lister
    spec_version: 0
    version: 0.1.0
    description: List insurance form numbers found in a policy document.
    invokes:
      - kind: cli
        exec: python {skill_root}/scripts/list_forms.py --input policy.txt
    bundle:
      - scripts/list_forms.py
      - references/form-glossary.md
    harnesses:
      hermes: {category: insure}
      openclaw: {}
      claude_code: {}
    """
)


def _make_type_b(tmp_path: Path) -> Path:
    """Lay out a type-B spec + its skills/<name>/ assets; return the spec path."""
    (tmp_path / "specs").mkdir()
    (tmp_path / "skills" / "policy-form-lister" / "scripts").mkdir(parents=True)
    (tmp_path / "skills" / "policy-form-lister" / "references").mkdir(parents=True)
    spec = tmp_path / "specs" / "policy-form-lister.yaml"
    spec.write_text(CLI_SPEC, encoding="utf-8")
    (tmp_path / "skills" / "policy-form-lister" / "scripts" / "list_forms.py").write_text(
        "print('forms')\n", encoding="utf-8"
    )
    (tmp_path / "skills" / "policy-form-lister" / "references" / "form-glossary.md").write_text(
        "# glossary\n", encoding="utf-8"
    )
    return spec


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


def test_all_copies_bundle_files_verbatim(tmp_path: Path) -> None:
    spec = _make_type_b(tmp_path)
    out = tmp_path / "out"
    src_dir = tmp_path / "skills" / "policy-form-lister"
    rc = main([str(spec), "--all", "--out", str(out)])
    assert rc == 0
    for harness in ("hermes", "openclaw", "claude_code"):
        dest = out / harness / "policy-form-lister"
        for rel in ("scripts/list_forms.py", "references/form-glossary.md"):
            copied = dest / rel
            assert copied.is_file(), f"missing {copied}"
            assert copied.read_bytes() == (src_dir / rel).read_bytes()


def test_all_templates_exec_path_per_harness(tmp_path: Path) -> None:
    spec = _make_type_b(tmp_path)
    out = tmp_path / "out"
    main([str(spec), "--all", "--out", str(out)])
    hermes = (out / "hermes" / "policy-form-lister" / "SKILL.md").read_text(encoding="utf-8")
    openclaw = (out / "openclaw" / "policy-form-lister" / "SKILL.md").read_text(encoding="utf-8")
    assert "~/.hermes/skills/insure/policy-form-lister/scripts/list_forms.py" in hermes
    assert "/opt/openclaw-workspace/skills/policy-form-lister/scripts/list_forms.py" in openclaw


def test_all_writes_hermes_mcp_snippet_only(tmp_path: Path) -> None:
    out = tmp_path / "out"
    main([SPEC, "--all", "--out", str(out)])
    hermes_snip = out / "hermes" / "trapezia-commercial-policy-check" / "mcp_servers.snippet.yaml"
    openclaw_snip = out / "openclaw" / "trapezia-commercial-policy-check" / "mcp_servers.snippet.yaml"
    assert hermes_snip.is_file(), "hermes snippet missing"
    assert not openclaw_snip.exists(), "snippet must be hermes-only"
    assert "mcp_servers" in hermes_snip.read_text(encoding="utf-8")


def test_all_no_snippet_for_cli_only(tmp_path: Path) -> None:
    spec = _make_type_b(tmp_path)
    out = tmp_path / "out"
    main([str(spec), "--all", "--out", str(out)])
    snip = out / "hermes" / "policy-form-lister" / "mcp_servers.snippet.yaml"
    assert not snip.exists(), "cli-only skill must produce no MCP snippet"
