# Dedicated Type-D Fixture (Phase 5) Implementation Plan

> **For agentic workers:** this is a **TDD code** plan continuing the multi-harness POC. Every
> code task lists the test first (red), then the implementation (green), then the exact command
> and expected result. Execute task-by-task; re-run the suite after each; commit per task.

**Goal:** Prove the type-D (mcp + cli in one skill) path for real. The schema and generator
already support mixed `invokes` lists — unit-tested in `test_mixed_invokes_type_d_loads`
(Phase 2, `tests/spec/test_schema.py:149`) and `build_context`/`generate`/`generate_mcp_registration`
are already fully spec-driven and invoke-kind-generic (Phase 2 Task 2/3/4; see
`src/trapezia_skill_spec/generate.py`). **No schema or generator code changes are expected in this
phase** — the work is authoring a real type-D skill and running it through the same live
3-harness validation Phases 1–2 used.

**Chosen fixture: `policy-declarations-check`.** A believable real insure-domain workflow, not a
contrived glue skill:

- **CLI half (new, deterministic):** `scripts/extract_declarations.py` regex-scans a raw policy
  declarations-page text for the subset of `PolicyDocument` fields (per the
  `trapezia-commercial-policy-check` engine's actual input schema — confirmed by reading
  `trapezia-commercial-policy-check/src/trapezia_commercial_policy_check/schemas/inputs.py`)
  that a page-level scan can reliably recover: `policy_number`, `carrier_name`,
  `named_insureds`, `policy_effective_date`/`policy_expiration_date`, `gl_each_occurrence`,
  `gl_general_aggregate`, `forms_schedule`. Prints `{"policy": {...}}` JSON, stdlib-only,
  fields omitted (never guessed) when not found in the text.
- **MCP half (reused, not reinvented):** the *same* already-deployed
  `trapezia-commercial-policy-check` MCP server (`health`/`run_policy_check`/`get_run_status`/
  `get_run_report`) that the existing type-C `trapezia-commercial-policy-check` spec already
  wraps. This is the realistic pattern: the checking engine is registered once; a second skill
  can legitimately invoke the same MCP tools with a different front-end. The extractor's output
  is shaped to drop straight into a `PolicyCheckingRun.policy` payload.

**Why this and not a new server:** Phase 0–2 established that the generator repo does not
implement capability servers — it wraps already-deployed ones. Building a second full MCP server
just to avoid one shared server name would be infra-heavy for no fidelity gain and would break
the "declared server already running in Lab/HermesLab, no new registration needed" property that
makes live validation cheap. Reusing the proven server is the same choice a real Trapezia skill
author would make.

**Naming note:** the two skills stay distinct and both remain deployed as living evidence
(matches the Phase 1/2 pattern of leaving prior fixtures in place): `trapezia-commercial-policy-check`
(type C — check only, caller supplies a pre-built payload) and `policy-declarations-check`
(type D — extract from raw text, then check). Distinct trigger phrases so they don't collide in a
live harness's skill-selection.

**Tech Stack:** unchanged — Python 3.13, `pyyaml`, `jinja2`, `pytest`, stdlib-only for the script.

**Branch:** `multi-harness-poc` in the `trapezia-skill-validator-poc` worktree.

---

## Guardrails (carry Phase 1/2's, plus)

- **No generator/schema code changes expected.** If a real gap surfaces (unlikely — Phase 2
  already generalized `build_context`/templates/`generate_mcp_registration` to be invoke-kind
  agnostic), treat it as a genuine finding, fix minimally, and call it out explicitly in the
  evidence note — don't silently expand scope.
- **Additive only in the validator** (unaffected this phase — no linter rule changes planned).
- **Generated files are never hand-edited.** `specs/policy-declarations-check.yaml` +
  `skills/policy-declarations-check/**` are the only authored surfaces; `generated/**` is
  regenerated via the CLI and committed.
- **mypy --strict clean** on the new script (Phase-1/2 carry-forward convention).
- **Keep `trapezia_skill_spec` one-directionally coupled and self-contained** — this phase only
  *uses* the existing generator/schema surface, it doesn't touch `spec_lint.py`'s coupling. See
  the `feedback-keep-spec-generator-extractable` memory; nothing in this phase should erode it.
- **Trapezia disciplines:** work stays in the `-poc` worktree (Rule 1 ✓); no PHI/sensitive data —
  synthetic declarations text only, same posture as the existing policy-check fixtures (Rule 7
  ✓); live validation is Lab-eligible portable e2e only, no UAT/Prod (Rule 8 N/A).

---

## File & artifact map

**New demo skill (type D):**
- Create: `specs/policy-declarations-check.yaml`
- Create: `skills/policy-declarations-check/scripts/extract_declarations.py`
- Create: `skills/policy-declarations-check/references/declarations-field-map.md`

**Generated outputs (committed):**
- Create: `generated/{hermes,openclaw,claude_code}/policy-declarations-check/SKILL.md` **plus**
  the copied `scripts/extract_declarations.py` + `references/declarations-field-map.md` under
  each, **plus** `generated/hermes/policy-declarations-check/mcp_servers.snippet.yaml`.

**Tests:**
- Create: `tests/skills/test_extract_declarations.py` — unit-tests the extraction function
  directly (new: list_forms.py never got a dedicated behavior test; this script's logic — dates,
  money normalization, multi-field extraction — is complex enough to warrant one).
- `tests/spec/test_regeneration.py` already globs `specs/*.yaml` — the new spec is picked up
  automatically, no edit needed. Confirm this in Task 3 rather than assuming.

---

## Task list (TDD)

### Task 1 — `extract_declarations.py`: red tests first

**Red:** in `tests/skills/test_extract_declarations.py`, import the script by file path
(`importlib.util.spec_from_file_location`, mirroring that `skills/<name>/scripts/` isn't a
package) and assert `extract_declarations(text)` on a synthetic declarations-page fixture
returns the expected `policy` dict: correct `policy_number`, `carrier_name`, `named_insureds`
(list), ISO-normalized `policy_effective_date`/`policy_expiration_date` from an `MM/DD/YYYY to
MM/DD/YYYY` period line, integer `gl_each_occurrence`/`gl_general_aggregate` from `$1,000,000`
style text, and `forms_schedule` normalized per the engine's convention (uppercase, spaces
stripped, edition suffix dropped — confirmed against `inputs.py`'s documented convention, e.g.
`CG 00 01 04 13` → `CG0001`). Also assert: a field absent from the text is *absent* from the
returned dict (never a guessed/null placeholder), and CLI `main()` with a missing `--input` file
returns exit code 2 (mirrors `list_forms.py`'s contract).

**Green:** write `skills/policy-declarations-check/scripts/extract_declarations.py` (argparse
`--input`, stdlib regex, full type hints, docstrings — same quality bar as `list_forms.py`).

**Verify:** `pytest tests/skills/test_extract_declarations.py -q` → pass.

---

### Task 2 — `specs/policy-declarations-check.yaml` + reference doc

**Steps:**
- Write `specs/policy-declarations-check.yaml`: `invokes` = one `cli` entry (`exec: python
  {skill_root}/scripts/extract_declarations.py --input <policy.txt>`) **followed by** one `mcp`
  entry (`server: trapezia-commercial-policy-check`, same `launch`/`tools`/`required_env` as the
  existing type-C spec — intentionally identical since it's the same running server). `bundle:
  [scripts/extract_declarations.py, references/declarations-field-map.md]`. Distinct `triggers`
  from the type-C spec (e.g. "intake this policy", "extract and check this policy",
  "declarations check"). `guardrails`: a new `deterministic-extraction-only` id (script is a text
  scan, not a coverage judgment — don't fabricate missing fields) plus the two carried over from
  the type-C spec (`service-unreachable`, `commercial-only`). `usage` describing the two-step
  extract-then-check flow. `harnesses.hermes.category: insure`; `model_tier: sonnet` (same tier
  as the type-C spec — this skill's inference step is the same MCP-backed check).
- Write `skills/policy-declarations-check/references/declarations-field-map.md`: which regex
  captures map to which `PolicyDocument` field name, and which fields the script does **not**
  attempt to extract (the other ~120 optional fields — property, auto, WC, umbrella, cyber, etc.
  — a declarations-page scan can't reliably get; those stay for a human/AM to fill in before
  `run_policy_check`).

**Verify:** `python -c "from trapezia_skill_spec.schema import load_spec; load_spec('specs/policy-declarations-check.yaml')"` loads without error.

---

### Task 3 — Regenerate and confirm the drift test picks it up automatically

**Steps:**
- `python -m trapezia_skill_spec.cli specs/policy-declarations-check.yaml --all` → writes
  `generated/{hermes,openclaw,claude_code}/policy-declarations-check/**` and the hermes MCP
  snippet.
- Eyeball each generated `SKILL.md`: confirm **both** a Scripts section (resolved `{skill_root}`
  per harness) and an MCP section (server + 4 tools) render in the same file — the actual type-D
  proof point.
- `pytest tests/spec/test_regeneration.py -q` → the new spec is picked up by the existing
  `SPECS = sorted((REPO / "specs").glob("*.yaml"))` glob with **no test-file edit**; passes only
  if the committed generated output matches fresh generation. If a test-file edit turns out to be
  needed, that itself is a finding — note it in the evidence doc.

**Verify:** `pytest tests/spec -q` → all pass, including the 3 new regeneration-drift
parametrizations (`SKILL.md` × 3 harnesses, bundle × 2 files × 3 harnesses, hermes snippet).

---

### Task 4 — Full suite + mypy

- `pytest -q` at repo root → all green (baseline 101 passed/1 skipped + the new
  `test_extract_declarations.py` cases + the 3 new regeneration parametrizations).
- `mypy --strict skills/policy-declarations-check/scripts/extract_declarations.py` → clean (same
  bar as `list_forms.py`; the one pre-existing shared gap is `yaml` import-untyped, unrelated).

---

### Task 5 — Live 3-harness validation (portable e2e, Lab-eligible)

Same pattern as Phase 1 (policy-check) and Phase 2 (policy-form-lister) — **no new MCP
registration needed anywhere** since `trapezia-commercial-policy-check` is already registered and
running on OrionLab/HermesLab from Phase 0/1; this phase only adds the new SKILL.md wrapper +
script bundle.

- **CC:** drop `generated/claude_code/policy-declarations-check/` into a throwaway
  `~/.claude/skills/policy-declarations-check/`; confirm it appears in the live `Skill` listing;
  run `extract_declarations.py` against a synthetic fixture; remove afterward (cleanup, matches
  Phase 1's CC step).
- **OrionLab:** scp the generated dir (SKILL.md + scripts/ + references/) to
  `/opt/orionlab/workspace/skills/policy-declarations-check/`; `openclaw skills info
  policy-declarations-check` → `✓ Ready`; run the script inside the container against a fixture;
  confirm the pre-existing `trapezia-commercial-policy-check` MCP registration is still the one
  in effect (no new registration step). Leave deployed (living evidence, matches Phase 1/2).
- **HermesLab:** scp to
  `/opt/hermeslab/data/skills/insure/policy-declarations-check/`; `hermes skills list` →
  `enabled`/`local`/`insure`; run the script inside the container against the same fixture; same
  no-new-registration confirmation. Leave deployed.
- Capture literal command output for each as evidence (Phase 1/2 discipline — real deploy, not a
  claimed one).

**Verify:** identical extraction JSON from all three (deterministic script, no reason it should
differ); the MCP half is not re-exercised end-to-end here (that was already proven in Phase 1/2
for the same server) — this phase's live-validation focus is the *new* half: does the type-D
SKILL.md correctly surface both a script command and an MCP tool reference, and does the script
actually run, on all three harnesses.

---

### Task 6 — Phase 5 validation note + memory + push + CI

- Write `docs/superhuman/notes/2026-07-25-phase5-validation.md` (deploy evidence for all three
  harnesses, the type-D SKILL.md excerpt proving both sections render, confirmation no new MCP
  registration was needed).
- Update the `multi-harness-poc` memory with Phase 5 outcome; point `[[feedback-keep-spec-generator-extractable]]`
  usage forward to Phase 6 if still relevant.
- Commit per task along the way; at the end **ask before pushing** (established pattern). On
  push, verify CI green (trapezia-disciplines post-push rule).

---

## Definition of done

- A real, believable type-D skill (`policy-declarations-check`) generates from one canonical YAML
  with both a Scripts section and an MCP section in the same rendered `SKILL.md`, on all three
  harnesses.
- Deployed and run for real on Claude Code, OrionLab, and HermesLab — not just generated.
- No schema or generator code changes were needed (or, if one was, it's called out as a genuine
  Phase-2-coverage gap in the evidence note, not silently absorbed).
- Full suite green, mypy --strict clean on the new script, CI green after push.
