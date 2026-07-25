# Phase 5 Validation Evidence — Dedicated Type-D Fixture

**Date:** 2026-07-25
**Branch:** `multi-harness-poc` (worktree `trapezia-skill-validator-poc`)
**Plan:** `docs/superhuman/plans/2026-07-25-type-d-fixture-phase5.md` (6 tasks, TDD).

Phase 5 proved the type-D (mcp + cli in one skill) path for real, on a genuinely
believable skill — `policy-declarations-check`. No schema or generator changes
were needed for mixed `invokes` support itself (Phase 2 already made
`build_context`/`generate` fully invoke-kind agnostic). What this phase *did*
turn up: **two latent, previously-unverified bugs in `skill_root()`** — the
OpenClaw and Hermes deployed-path conventions were both wrong, undetected since
Phase 1/2 because neither phase had ever actually run the *literal* generated
exec command inside a live container. Full suite: **109 passed, 1 skipped**
(baseline 101 + 8 new). mypy `--strict` clean on the new script and all touched
generator files (same pre-existing `yaml` import-untyped gap as always).

## The fixture: `policy-declarations-check`

A real two-step insure workflow, not a contrived glue skill:

- **CLI half (new):** `extract_declarations.py` — deterministic regex extraction
  of the `PolicyDocument` fields (per
  `trapezia_commercial_policy_check.schemas.inputs`) a declarations-page scan
  can reliably recover: `policy_number`, `carrier_name`, `named_insureds`,
  `policy_effective_date`/`policy_expiration_date` (normalized to ISO 8601),
  `gl_each_occurrence`/`gl_general_aggregate` (normalized integers), and
  `forms_schedule` (normalized per the engine's own convention — uppercase,
  spaces stripped, edition suffix dropped — distinct from `list_forms.py`'s
  human-readable spaced format, because this output feeds a machine payload).
  Fields not found in the text are omitted, never guessed.
- **MCP half (reused, not reinvented):** the same already-deployed
  `trapezia-commercial-policy-check` server (`health`/`run_policy_check`/
  `get_run_status`/`get_run_report`) the existing type-C spec wraps. No new
  server, no new registration — this phase only added the SKILL.md wrapper +
  script bundle.

`specs/policy-declarations-check.yaml`'s `invokes` list: one `cli` entry
followed by one `mcp` entry, identical `launch`/`tools`/`required_env` to the
type-C spec (same running server). Distinct `triggers` from the type-C spec so
the two don't collide in a live harness's skill selection.

Unit tests (`tests/skills/test_extract_declarations.py`, 5 cases) load the
script by file path and assert: full extraction against a synthetic
declarations-page fixture, `MM/DD/YYYY to MM/DD/YYYY` → ISO date
normalization, `$1,000,000` → integer normalization, form-number
normalization matching the engine's convention, missing fields omitted (not
guessed/null), empty text → empty policy, and the CLI's missing-input exit
code 2.

## The type-D proof point

Both a Scripts section and an MCP section render in the same generated
`SKILL.md`, on all three harnesses, driven by one canonical YAML. Hermes
output (`generated/hermes/policy-declarations-check/SKILL.md`):

```
## Procedure

Run extract_declarations.py against the raw policy text to get a `policy`
document, wrap it in a PolicyCheckingRun payload...

This skill wraps 1 MCP server(s):
- `trapezia-commercial-policy-check` (transport: stdio) tools: `health`, `run_policy_check`, `get_run_status`, `get_run_report`

Run the bundled script(s):
```
python /opt/data/skills/insure/policy-declarations-check/scripts/extract_declarations.py --input <policy.txt>
```
```

The regeneration/drift test (`tests/spec/test_regeneration.py`) picked up the
new spec via its existing `specs/*.yaml` glob with **zero test-file edits** —
9/9 parametrized cases (`SKILL.md` × 3 harnesses, bundle × 3 harnesses, hermes
snippet) passed against the freshly authored fixture.

## Finding: `skill_root()` was wrong for both OpenClaw and Hermes

While live-deploying, the plan called for running the *literal* generated exec
command inside each container rather than a manually-typed "should work" path.
That surfaced two bugs, both dating back to when each harness's `skill_root()`
branch was first written and both undetected because Phase 1/2's evidence
notes recorded scripts as having "run inside the container" without actually
exercising the templated command string:

- **OpenClaw:** `skill_root()` emitted
  `/home/node/.openclaw/workspace/skills/<name>`. Real container filesystem
  check on `orionlab`: `/home/node/.openclaw/` exists (bind-mounted from host
  `state/`, `OPENCLAW_STATE_DIR`) but has **no `workspace/` subdirectory at
  all**. The real skill root, confirmed against
  `docker-compose-orionlab.yml`'s `volumes: /opt/orionlab/workspace:/opt/openclaw-workspace`
  and `OPENCLAW_WORKSPACE=/opt/openclaw-workspace`, is
  `/opt/openclaw-workspace/skills/<name>` — a fixed container-side path, not
  home-relative.
- **Hermes:** `skill_root()` emitted `~/.hermes/skills/<category>/<name>`.
  Checked both plausible exec users inside `hermeslab`: default (root,
  `HOME=/root`) and the F-8 uid-10000 user (`HOME=/opt/data`) — neither has a
  `.hermes/` subdirectory. The real skill root, confirmed against
  `docker-compose-hermeslab.yml`'s `volumes: /opt/hermeslab/data:/opt/data`
  (same convention on `hermestest`: `/opt/hermestest/data:/opt/data`), is
  `/opt/data/skills/<category>/<name>` — again a fixed container-side path.
  Bonus finding: the live `mcp_servers.trapezia-commercial-policy-check`
  registration (set up manually in Phase 0) has **no `cwd` field at all**,
  confirming the MCP-registration snippet's `cwd: ~/.hermes/skills/...` had
  never been validated against a real deployment either.

**Fix (two commits):** `skill_root()` in `src/trapezia_skill_spec/generate.py`
now returns `/opt/openclaw-workspace/skills/<name>` (openclaw) and
`/opt/data/skills/<category>/<name>` (hermes). Updated the four test
assertions that had encoded the wrong paths
(`tests/spec/test_generate_scripts.py`, `tests/spec/test_cli.py`). Regenerated
every affected output — only the OpenClaw/Hermes `SKILL.md` exec lines and the
two Hermes `mcp_servers.snippet.yaml` `cwd` fields changed (confirmed by diff:
2 lines then 4 lines, nothing else); Claude Code output and the MCP-only
`trapezia-commercial-policy-check` OpenClaw/Claude-Code output were already
byte-identical, as expected (no cli invoke there). `policy-form-lister`'s
already-deployed copies on OrionLab and HermesLab were **also broken by this
same bug since Phase 2** — re-deployed the corrected `SKILL.md` to both as
part of fixing this.

This is a genuine Phase-1/2-era gap, not scope creep: fixed minimally (one
function, four test assertions, no schema changes), called out here per the
plan's guardrail rather than silently absorbed.

## Live 3-harness deployment (portable e2e, Lab-eligible)

No new MCP registration needed anywhere — `trapezia-commercial-policy-check`
was already registered and running on OrionLab/HermesLab from Phase 0/1; this
phase only added the SKILL.md wrapper + script bundle, confirmed by re-reading
each live config before touching anything.

- **Claude Code (laptop).** Dropped `generated/claude_code/policy-declarations-check/`
  into `~/.claude/skills/policy-declarations-check/`. Took one extra tool-call
  cycle to appear in the live `Skill` tool listing this session (a
  system-reminder surfaced it after the next tool call, not synchronously
  within the same call that copied the files — a minor timing difference from
  Phase 1/2's "immediately" observation, not a functional gap). Ran the
  deployed script against a synthetic fixture:

  ```
  python ~/.claude/skills/policy-declarations-check/scripts/extract_declarations.py --input sample-policy.txt
  ```

  Output matched expectations exactly (see JSON below). Throwaway removed
  after validation.

- **OrionLab (OpenClaw; portable e2e).** scp'd
  `generated/openclaw/policy-declarations-check/` to
  `/opt/orionlab/workspace/skills/policy-declarations-check/`.
  `openclaw skills info policy-declarations-check` →

  ```
  policy-declarations-check ✓ Ready
    Source: openclaw-workspace
    Path: /opt/openclaw-workspace/skills/policy-declarations-check/SKILL.md
    Visible to model: yes
    Available as command: yes
  ```

  Ran the **literal generated exec line** inside the `orionlab` container
  (after the `skill_root()` fix):

  ```
  docker exec orionlab python /opt/openclaw-workspace/skills/policy-declarations-check/scripts/extract_declarations.py --input /tmp/sample-policy.txt
  ```

  Also re-ran `policy-form-lister`'s corrected exec line in the same
  container to confirm its Phase-2 regression was fixed. Confirmed the
  pre-existing `trapezia-commercial-policy-check` MCP registration in
  `/opt/orionlab/config/openclaw.json` — no new registration step. Left
  deployed (living evidence, matches Phase 1/2).

- **HermesLab.** scp'd `generated/hermes/policy-declarations-check/` to
  `/opt/hermeslab/data/skills/insure/policy-declarations-check/`
  (chown 10000:10000 per F-8). Deliberately did **not** deploy the
  `mcp_servers.snippet.yaml` alongside it — that file is an operator-merge
  config fragment (Chris's Phase-2 decision: committed snippet + manual
  merge), not a skill runtime asset, and doesn't belong in the live skill
  directory. `hermes skills list` →

  ```
  │ policy-declarations-check │ insure │ local │ local │ enabled │
  ```

  Ran the **literal generated exec line** inside the `hermeslab` container
  (after the `skill_root()` fix):

  ```
  docker exec hermeslab python /opt/data/skills/insure/policy-declarations-check/scripts/extract_declarations.py --input /tmp/sample-policy.txt
  ```

  Also re-ran `policy-form-lister`'s corrected exec line in the same
  container. Confirmed the live `mcp_servers.trapezia-commercial-policy-check`
  registration in `/opt/hermeslab/data/config.yaml` is unchanged — no new
  registration step. Left deployed (living evidence).

**Identical output from all three harnesses** against the same synthetic
declarations-page fixture (`sample-policy.txt`: named insured "Blue Ridge
Millwork LLC", policy `CLP-9921047-02`, carrier "Meridian Assurance Company",
06/01/2026–06/01/2027, $1M/$2M GL limits, `CG 00 01 04 13` / `CG 20 10 07 04`
/ `ACORD 25`):

```json
{
  "policy": {
    "policy_number": "CLP-9921047-02",
    "carrier_name": "Meridian Assurance Company",
    "named_insureds": ["Blue Ridge Millwork LLC"],
    "policy_effective_date": "2026-06-01",
    "policy_expiration_date": "2027-06-01",
    "gl_each_occurrence": 1000000,
    "gl_general_aggregate": 2000000,
    "forms_schedule": ["ACORD25", "CG0001", "CG2010"]
  }
}
```

The MCP half was not re-exercised end-to-end in this phase (already proven in
Phase 1 for the same server via the automated Discord fidelity e2e); this
phase's live-validation focus was the new half — does the type-D `SKILL.md`
correctly surface both a script command and an MCP tool reference, and does
the script actually run, on all three harnesses.

`policy-declarations-check` is **left deployed** on OrionLab and HermesLab as
living evidence (parallel to policy-check and policy-form-lister). Per POC
scope it is **not** registered in any deployment tracker.

## Extractability discipline (Phase 4 carry-forward)

No `trapezia_skill_spec` coupling changes this phase — `skill_root()` and
`build_context()` remain the only public surface `spec_lint.py` consumes, and
the fix stayed inside `generate.py`. The
[[feedback-keep-spec-generator-extractable]] guidance held without needing to
think about it, which is itself a small positive signal for "stay merged, stay
extractable."

## Not done (deferred, unchanged from the roadmap)

- Phase 6 — `memory-sync` evaluation and decision (next up per the locked
  roadmap).
- No new capability servers, no UAT/Prod promotion (Rule 8 N/A this phase).
