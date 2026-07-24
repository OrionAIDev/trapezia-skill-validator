# Net-New Skill: Scripts Portability + Hermes MCP Registration (Phase 2) Implementation Plan

> **For agentic workers:** this is a **TDD code** plan continuing the multi-harness POC. Every
> code task lists the test first (red), then the implementation (green), then the exact command
> and expected result. Execute task-by-task; re-run the suite after each; commit per task.

**Goal:** Prove the generator on a **genuinely net-new skill** — not the pre-registered
policy-check. Close the two gaps the Phase 1 validation flagged:

- **Gap 1 — scripts portability.** Add a second demo skill of **type B** (`SKILL.md` + scripts,
  no MCP), a `bundle` manifest for files that travel, and **per-harness script-path templating**
  so a `cli` invoke's command resolves to the harness-correct skill root. Chosen demo skill:
  **`policy-form-lister`** (deterministic insure-domain utility; regexes ISO/ACORD form numbers
  out of a policy text file; non-PHI; no MCP; no LLM).
- **Gap 2 — Hermes MCP registration.** The Hermes emitter must also emit the
  `config.yaml mcp_servers.<name>` stdio registration block (Phase 0 **F-6**), as a **committed,
  drift-checked snippet** the operator merges manually.

Doing this forces a third, unavoidable piece of work the candidate menu didn't call out:

- **Generalize the templates + `build_context`.** Phase 1's templates hardcode policy-check
  (`run_policy_check`/`get_run_status`/`get_run_report`) and `build_context` flattens `invokes`
  to a single MCP server. A scripts-only skill (no server) would render nonsense. Templates and
  context must become **spec-driven**: an MCP section iff there are `mcp` invokes, a Scripts
  section iff there are `cli` invokes, and optional freeform `usage` prose in place of the
  hardcoded procedure sentence.

**Architecture:** unchanged from Phase 1 — one canonical YAML per skill, generated per-harness
outputs committed under `generated/**` and drift-checked in CI. This phase widens the schema
(`Invocation.exec`, top-level `bundle`, optional `usage`), teaches the generator path-templating +
bundle-copy + MCP-snippet emission, generalizes the three templates, extends the additive linter,
and adds the `policy-form-lister` fixture end-to-end.

**Tech Stack:** Python 3.13, `pyyaml`, `jinja2` (the `spec`/`test` extra), `pytest`. No new deps.

**Branch:** `multi-harness-poc` in the `trapezia-skill-validator-poc` worktree. Master and all
production consumers stay untouched.

---

## Locked design decisions (2026-07-24, confirmed with Chris)

1. **Demo skill = `policy-form-lister`** (type B, insure, deterministic scripts-only). Runs on the
   existing synthetic policy fixtures — non-PHI by construction.
2. **MCP-registration delivery = committed snippet, manual merge.** Emit
   `generated/hermes/<name>/mcp_servers.snippet.yaml`; drift-checked like `SKILL.md`; the operator
   merges it into `/opt/hermeslab/data/config.yaml`. **No** auto-merge runtime tool.
3. **Authored skill assets live in `skills/<name>/`** (new top-level dir). `bundle:` paths in the
   YAML are **relative to `skills/<name>/`**. Policy-check (type C, no bundle) is unaffected.
4. **Path token = explicit `{skill_root}`.** A `cli` invoke's `exec` string contains the literal
   token `{skill_root}`; the generator substitutes the harness-correct root:
   - **hermes:** `~/.hermes/skills/<category>/<name>` (category from `harnesses.hermes.category`)
   - **openclaw:** `/home/node/.openclaw/workspace/skills/<name>`
   - **claude_code:** `~/.claude/skills/<name>`
   Bundle files copy **verbatim**; only the `SKILL.md` exec line is templated.
5. **`usage` is optional freeform prose** at spec top-level. Renders in the Procedure section when
   present; absent → templates fall back to generic guidance. De-hardcodes the policy-check prose
   without a policy-check-specific template.

**Out of scope for Phase 2 (deferred, noted here so it isn't silently dropped):**
- A dedicated **type-D** (mcp + cli in one skill) fixture — its mechanics are fully covered by
  proving B (this phase) and C (Phase 1); a D skill is a trivial union once both render. Schema
  and generator will *support* mixed `invokes` (tested at the unit level), just no shipped D skill.
- The **automated Discord fidelity e2e** (POC candidate c) — still Test-tier/QA-bound, not chosen.
- **Graduation/merge** of `multi-harness-poc` → `master` (candidate d) — separate, needs sign-off.
- Any **auto-merge** helper for the MCP snippet — Chris chose manual merge.

---

## Guardrails (carry Phase 1's, plus)

- **Additive only in the validator.** Linter changes stay in `spec_lint.py`; do not touch
  `runner.run_audit` / `registry.CHECKS` / the `trapezia-skill-validator` CLI.
- **Generated files are never hand-edited.** `specs/*.yaml` + `skills/<name>/**` are the only
  authored surfaces; `generated/**` is machine output guarded by the regeneration test.
- **`jinja2` stays an optional extra**; `schema.py` stays jinja2-free (the linter imports it).
- **Backward compatible.** Every schema addition is optional; the existing policy-check spec keeps
  validating. `Invocation.exec`/`bundle`/`usage` default to empty/None.
- **mypy --strict clean** on every file touched (Phase-1 carry-forward: the `mypy.strict` gate is
  live in the validator's own audit and in CI). `yaml` import-untyped is the one pre-existing,
  shared, out-of-scope gap.
- **Trapezia disciplines:** work stays in the `-poc` worktree (Rule 1 placement ✓); no sensitive
  data (Rule 7 ✓); live validation is Lab-eligible **portable e2e** only — no UAT/Prod (Rule 8
  N/A this phase).

---

## File & artifact map

**Schema / generator (extend):**
- Modify: `src/trapezia_skill_spec/schema.py` — `Invocation.exec`, `CanonicalSpec.bundle`,
  `CanonicalSpec.usage`; kind-branched validation; bundle path validation.
- Modify: `src/trapezia_skill_spec/generate.py` — spec-driven `build_context`; `skill_root(harness,
  spec)`; `{skill_root}` substitution; `generate_mcp_registration(spec)`.
- Modify: `src/trapezia_skill_spec/templates/{hermes,openclaw,claude_code}.md.j2` — generic
  MCP-section + Scripts-section + optional `usage`.
- Modify: `src/trapezia_skill_spec/cli.py` — copy `bundle` files; write MCP snippet.

**New demo skill (type B):**
- Create: `specs/policy-form-lister.yaml`
- Create: `skills/policy-form-lister/scripts/list_forms.py` (deterministic; regex form numbers)
- Create: `skills/policy-form-lister/references/form-glossary.md` (a second bundle file, proves
  multi-path + subdir copy)

**Generated outputs (committed):**
- Regenerate: `generated/{hermes,openclaw,claude_code}/trapezia-commercial-policy-check/SKILL.md`
  (templates generalized) **plus** `generated/hermes/.../mcp_servers.snippet.yaml` (new).
- Create: `generated/{hermes,openclaw,claude_code}/policy-form-lister/SKILL.md` **plus** the copied
  `scripts/list_forms.py` + `references/form-glossary.md` under each.

**Validator (additive):**
- Modify: `src/trapezia_skill_validator/spec_lint.py` — cli/bundle/exec-token rules.

**Tests:**
- Modify: `tests/spec/test_schema.py` — cli invoke, bundle, mixed invokes, negative cases.
- Create: `tests/spec/test_generate_scripts.py` — type-B rendering + `{skill_root}` per harness.
- Create: `tests/spec/test_mcp_registration.py` — snippet content for policy-check.
- Modify: `tests/spec/test_generate_{hermes,openclaw,claude_code}.py` — generic-template assertions.
- Modify: `tests/spec/test_regeneration.py` — iterate **all** specs; assert bundle copies + snippet.
- Modify: `tests/spec/test_cli.py` — `--all` writes bundle + snippet.
- Modify: `tests/test_spec_lint.py` — new rule coverage.

---

## Task list (TDD)

### Task 1 — Schema: `exec`, `bundle`, `usage`, kind-branched validation

**Red:** in `tests/spec/test_schema.py` add:
- a `cli` invoke with `exec` and no `server`/`transport`/`tools` **loads**;
- a `cli` invoke **without** `exec` raises `SpecError`;
- `bundle: ["scripts/x.py", "references/y.md"]` loads and round-trips;
- `bundle: ["../evil"]` and `bundle: ["/abs"]` raise `SpecError`;
- a spec mixing one `mcp` + one `cli` invoke (type D) loads;
- top-level `usage: "..."` round-trips; absent → `None`.

**Green (`schema.py`):**
- Add `exec: str | None = None` to `Invocation`.
- Add `bundle: list[str] = field(default_factory=list)` and `usage: str | None = None` to
  `CanonicalSpec`.
- Branch validation on `kind`:
  - `mcp` → require `server`, `transport ∈ TRANSPORTS`, non-empty `tools` (as today).
  - `cli` → require `exec`; `server`/`transport`/`tools` optional (default `""`/`""`/`[]`).
- Validate `bundle`: list of `str`; each relative (`not startswith("/")`, no `..` segment, not a
  Windows-abs path); else `SpecError`.
- Load `usage = raw.get("usage")`.

**Verify:** `pytest tests/spec/test_schema.py -q` → all pass.

---

### Task 2 — Generator: spec-driven `build_context` + `skill_root` + `{skill_root}` substitution

**Red:** in a new `tests/spec/test_generate_scripts.py`, assert (against a small inline type-B
spec) that `build_context(spec, harness)` exposes `cli_cmds` with `{skill_root}` **resolved** to:
- hermes → `~/.hermes/skills/insure/<name>`
- openclaw → `/home/node/.openclaw/workspace/skills/<name>`
- claude_code → `~/.claude/skills/<name>`
and `mcp_servers == []` (no MCP). Also assert a type-C spec still exposes `mcp_servers` with the
server + tools and `cli_cmds == []`.

**Green (`generate.py`):**
- Add `skill_root(harness: str, spec: CanonicalSpec) -> str` using the roots above; hermes category
  = `spec.harnesses.get("hermes", {}).get("category", "general")`.
- Change `build_context(spec)` → `build_context(spec, harness)`. Emit structured lists:
  `mcp_servers` = `[{server, transport, tools, required_env} for mcp invokes]`;
  `cli_cmds` = `[inv.exec.replace("{skill_root}", skill_root(harness, spec)) for cli invokes]`;
  keep `name/description/version/triggers/guardrails/model_tier`; add `usage`.
- `generate(spec, harness)` passes `harness` through to `build_context`.

**Verify:** `pytest tests/spec/test_generate_scripts.py -q` (context assertions) → pass. Existing
generate tests will fail until Task 3 (templates) — expected; note in commit.

---

### Task 3 — Generic templates (MCP section + Scripts section + optional `usage`)

**Red:** update `tests/spec/test_generate_{hermes,openclaw,claude_code}.py` to assert **generic**
structure: for policy-check, a "## Procedure" that lists each tool; when `usage` is set, the usage
prose appears; **no** hardcoded `run_policy_check` literal unless it comes from `usage`/`tools`.
Add to `test_generate_scripts.py`: type-B output contains a Scripts section with the resolved
command and **no** MCP section.

**Green:** rewrite the three `*.md.j2` to be data-driven:
- `{% if mcp_servers %}` → MCP section iterating servers + their tools.
- `{% if cli_cmds %}` → Scripts section listing each command in a fenced block.
- `{% if usage %}{{ usage }}{% endif %}` in Procedure; else a generic one-liner.
- Hermes still omits `model_tier` (OQ-3); CC/OpenClaw still emit the advisory note.
- Hermes `category` comes from context, not hardcoded.

**Verify:** `pytest tests/spec -q` → the three generate suites + scripts suite pass. Do **not**
commit regenerated `generated/**` yet (Task 6 regenerates everything at once).

---

### Task 4 — Hermes MCP-registration snippet emitter

**Red:** `tests/spec/test_mcp_registration.py` — `generate_mcp_registration(policy_check_spec)`
returns a string containing `mcp_servers:`, the server name, `command: python`, an `args` list
built from `launch` via `shlex.split` (`["-m", "trapezia_commercial_policy_check.mcp_server"]`),
and `GOOGLE_API_KEY: "${GOOGLE_API_KEY}"` under `env`. For a spec with **no** mcp invoke it returns
`None`.

**Green (`generate.py`):** add `generate_mcp_registration(spec) -> str | None`. Hand-render a
deterministic YAML block (stable key order) per mcp invoke:
```yaml
# Generated by trapezia-skill-gen — merge into config.yaml `mcp_servers`.
# Operator: point `command` at the skill's isolated venv interpreter if one is used.
mcp_servers:
  <server>:
    command: <argv0 of launch>
    args: [<rest of launch, shlex-split>]
    env:
      <VAR>: "${<VAR>}"   # one per required_env
    cwd: "{skill_root}"    # hermes skill root; operator finalizes
```
Return `None` when the spec has zero mcp invokes.

**Verify:** `pytest tests/spec/test_mcp_registration.py -q` → pass.

---

### Task 5 — CLI: copy bundle files + write MCP snippet

**Red:** `tests/spec/test_cli.py` — run `main([spec, "--all", "--out", tmp])` for the type-B spec
and assert `tmp/<h>/policy-form-lister/scripts/list_forms.py` exists per harness with **identical
bytes** to the source, and the exec line inside `SKILL.md` differs per harness. Run it for
policy-check and assert `tmp/hermes/<name>/mcp_servers.snippet.yaml` exists and
`tmp/openclaw/<name>/mcp_servers.snippet.yaml` does **not** (hermes-only).

**Green (`cli.py`):** after writing each harness `SKILL.md`:
- copy every `bundle` path from `skills/<spec.name>/<path>` → `out/<harness>/<name>/<path>`
  (create parents; copy bytes verbatim);
- for hermes only, if `generate_mcp_registration(spec)` is not `None`, write it to
  `out/hermes/<name>/mcp_servers.snippet.yaml`.
- Resolve the assets root as `spec_path.parent.parent / "skills" / spec.name` — pass the spec path
  down (add a small helper; keep `load_spec` signature unchanged).

**Verify:** `pytest tests/spec/test_cli.py -q` → pass.

---

### Task 6 — The `policy-form-lister` fixture + regenerate the world

**Steps:**
- Write `skills/policy-form-lister/scripts/list_forms.py`: `argparse` `--input <path>`; read text;
  regex `\b(?:CG|CP|IL|CA|WC|BP)\s?\d{2}\s?\d{2}\s?\d{2}\b` (ISO) + a couple ACORD patterns;
  print sorted unique matches as JSON to stdout; exit 0. Deterministic, stdlib-only, full type
  hints, Google docstring.
- Write `skills/policy-form-lister/references/form-glossary.md` (a few lines mapping prefixes to
  names — second bundle file, proves subdir copy).
- Write `specs/policy-form-lister.yaml`: type B — `invokes: [{kind: cli, exec: "python
  {skill_root}/scripts/list_forms.py --input <policy.txt>"}]`, `bundle: ["scripts/list_forms.py",
  "references/form-glossary.md"]`, `usage`, `guardrails`, `triggers`, `harnesses.hermes.category:
  insure`, `model_tier` omitted (deterministic).
- Add `usage:` to `specs/trapezia-commercial-policy-check.yaml` (the former hardcoded sentence),
  and `harnesses.hermes.category: insure`.
- Regenerate everything:
  `python -m trapezia_skill_spec.cli specs/trapezia-commercial-policy-check.yaml --all`
  and `... specs/policy-form-lister.yaml --all`; commit the full `generated/**` diff.

**Verify:** `python skills/policy-form-lister/scripts/list_forms.py --input <a synthetic fixture>`
prints expected form numbers; eyeball the regenerated `generated/**`.

---

### Task 7 — Regeneration/drift test over ALL specs (incl. bundle + snippet)

**Green (`tests/spec/test_regeneration.py`):** discover every `specs/*.yaml`; for each spec ×
harness assert the committed `SKILL.md` matches `generate()`; for each `bundle` path assert the
committed copy matches the source bytes; assert the hermes `mcp_servers.snippet.yaml` matches
`generate_mcp_registration()` when non-`None` (and is absent otherwise).

**Verify:** `pytest tests/spec/test_regeneration.py -q` → pass (proves committed tree is fresh).

---

### Task 8 — Linter: cli/bundle/exec-token rules

**Red:** `tests/test_spec_lint.py` — a cli invoke whose `exec` lacks `{skill_root}` → WARN
(`spec.exec-token`); a `bundle` path missing on disk → WARN/FAIL (`spec.bundle-exists`); a clean
type-B spec → all PASS.

**Green (`spec_lint.py`):** add rules (additive; keep `spec.valid`/`spec.guardrails`):
- `spec.exec-token` — each cli `exec` contains `{skill_root}` (portability smell if not).
- `spec.bundle-exists` — each `bundle` path resolves under `skills/<name>/` (linter may hit the
  filesystem; it already takes a path).

**Verify:** `pytest tests/test_spec_lint.py -q` → pass.

---

### Task 9 — Full suite + mypy + live validation (portable e2e, Lab-eligible)

- `pytest -q` at repo root → **all green** (Phase-1 77 + the new tests).
- `python -m trapezia_skill_validator.cli ... ` self-audit unaffected; `mypy --strict` clean on
  touched files.
- **Live deploy of `policy-form-lister`** to all three harnesses (mirrors Phase 1's policy-check
  validation, but for a scripts skill):
  - **CC:** drop `generated/claude_code/policy-form-lister/` into a throwaway
    `~/.claude/skills/policy-form-lister-poc/`; confirm it appears in the live `Skill` listing;
    run `list_forms.py` against a synthetic fixture; remove.
  - **OrionLab (portable e2e):** scp the generated dir (SKILL.md + scripts/ + references/) to
    `/opt/orionlab/workspace/skills/policy-form-lister/`; `openclaw skills info` → `✓ Ready`; run
    the script inside the container against a fixture.
  - **HermesLab:** scp to `/opt/hermeslab/data/skills/insure/policy-form-lister/`;
    `hermes skills list` → `enabled`/`local`/`insure`; run the script.
  - Record evidence in a Phase 2 validation note.

**Verify:** capture command output as evidence; no UAT/Prod (Rule 8 N/A).

---

### Task 10 — Phase 2 validation note + memory + push + CI

- Write `docs/superhuman/notes/2026-07-24-phase2-validation.md` (deploy evidence for all three
  harnesses + the MCP-snippet artifact + what closed each gap).
- Update the `multi-harness-poc` memory with Phase 2 outcome.
- Commit per task along the way; at the end **ask before pushing** (Phase-1 pattern). On push,
  verify CI green (trapezia-disciplines post-push rule).

---

## Definition of done

- `policy-form-lister` (type B) generates, deploys, and runs on **all three harnesses** from one
  canonical YAML — script-path portability proven, not just MCP registration.
- The Hermes emitter produces a committed, drift-checked `mcp_servers.snippet.yaml` — a fresh
  MCP-backed skill now has a deployable registration (Gap 2 closed).
- Templates + `build_context` are spec-driven; no policy-check hardcoding remains.
- Additive-only in the validator; jinja2 still optional; `schema.py` still jinja2-free.
- Full suite green; regeneration/drift test covers SKILL.md + bundle copies + snippet across both
  specs; CI green after push.
