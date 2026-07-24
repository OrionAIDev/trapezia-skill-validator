# Phase 1 Validation Evidence + Graduation Decision

**Date:** 2026-07-24
**Branch:** `multi-harness-poc` (worktree `trapezia-skill-validator-poc`)
**Scope:** Task 11 of `docs/superhuman/plans/2026-07-17-canonical-spec-generator-phase1.md`.

Tasks 1–10 are code: schema + loader, generator core, three harness emitters
(Hermes/OpenClaw/Claude Code), the `trapezia-skill-gen` CLI, a CI regeneration
drift check, and the additive `trapezia-canonical-spec-lint` linter in
`trapezia_skill_validator`. 73/73 tests pass (`pytest -q` at the repo root).
One bug was found and fixed in the plan's own Task 10 test: the
`test_missing_guardrails_warns` `.replace()` target assumed 4/6/8-space
indentation, but `textwrap.dedent` on `VALID` actually produces 0/2/4-space
indentation, so the replace was a silent no-op and the WARN path went
untested until the target string was corrected.

## Step 1 — Claude Code wrapper (laptop)

Copied `generated/claude_code/trapezia-commercial-policy-check/SKILL.md`
verbatim into a throwaway `~/.claude/skills/trapezia-commercial-policy-check-poc/`.
Result: **discoverable immediately, mid-session** — no fresh session needed.
The skill appeared in the live `Skill` tool listing (`trapezia-commercial-policy-check-poc:
Run an automated commercial-insurance policy check...`) right after the file
was dropped in place. Frontmatter (`name`/`description` only) matches the
convention used by every other skill under `~/.claude/skills/`.

## Step 2 — OpenClaw wrapper (OrionLab)

Deployed manually via `scp` (not `orion-compose/skill_deploy.sh` — see
"Deviation" below) to
`/opt/orionlab/workspace/skills/trapezia-commercial-policy-check/SKILL.md`.

Verified via `docker exec orionlab node /opt/openclaw-app/openclaw.mjs`:

```
$ skills list | grep -A2 policy-check
✓ ready  │ trapezia-commercial-policy-check │ Run an automated commercial-insurance policy...

$ skills info trapezia-commercial-policy-check
trapezia-commercial-policy-check ✓ Ready
  Source: openclaw-workspace
  Path: /opt/openclaw-workspace/skills/trapezia-commercial-policy-check/SKILL.md
  Visible to model: yes
  Available as command: yes
```

No container restart was needed — OpenClaw's `skills list`/`info` discover
the dropped-in directory live.

**Deviation from the plan text:** the plan says "via the orion-compose
`skill_deploy.sh` path." `skill_deploy.sh` clones a full `OrionAIDev/<repo>`
from GitHub — it assumes each deployed skill is its own repo. The generated
wrapper here is *not* its own repo (that's precisely what the graduation
decision below is about), so the script doesn't apply yet. Deployed the
generated file directly instead. Once/if a generated wrapper graduates to
its own `OrionAIDev/<name>` repo, `skill_deploy.sh` becomes the right tool.

## Step 3 — Hermes wrapper (HermesLab)

Deployed manually via `scp` to
`/opt/hermeslab/data/skills/insure/trapezia-commercial-policy-check/SKILL.md`
(the `insure` category dir didn't exist yet; created it).

Verified via `docker exec hermeslab hermes skills list`:

```
│ trapezia-commercial-po… │ insure   │ local  │ local │ enabled │
```

The underlying MCP registration (`mcp_servers.trapezia-commercial-policy-check`
in `/opt/hermeslab/data/config.yaml`) already existed from Phase 0 — this
step only added the SKILL.md wrapper layer, which now shows `enabled`/`local`
in the correct `insure` category. A full end-to-end `/trapezia-commercial-policy-check`
Discord-driven check was **not** re-run here — Phase 0 already proved that
path end-to-end against the same MCP server (Pass A/B), and the Discord
fidelity gate is explicitly a separate, later QA-bound e2e concern per the
Phase 0 carry-forward notes, not a Phase 1 Task 11 checkpoint.

**Gap noted, not fixed in Phase 1:** the Phase 0 carry-forward section says
"The Hermes emitter must emit both the SKILL.md wrapper **and** this
registration snippet." Tasks 1–10 as written only implement the SKILL.md
emitter — no task generates the `mcp_servers.<name>` config.yaml snippet.
For policy-check this didn't block validation because the registration
already existed from Phase 0's manual setup, but for a *new* MCP-backed
skill the generator does not yet produce a deployable MCP registration.
Flagging as a Phase 2 candidate, not fixing now (out of Task 11's scope).

## Graduation decision (§4.5)

**Recommendation: stay merged in `trapezia-skill-validator`, defer
extraction.** Reasoning:

- Only one real capability (`trapezia-commercial-policy-check`) has been
  proven through the generator. The stated Phase 1 guardrail — jinja2 as an
  optional `spec` extra, `schema.py` jinja2-free — already isolates the
  validator's existing consumers (skill-template self-test,
  trapezia-skill-audit) from the new dependency, so there's no current
  packaging pressure to split.
- Extraction has a real cost (new repo, new CI, new release cadence) that
  isn't justified until the generator has more than one real consumer or a
  second team wants to depend on it without the validator.
- The gap above (no MCP-registration-snippet emitter) and the still-pending
  type-B (scripts-only) fixture mean the schema/generator surface will keep
  moving for at least one more phase. Cheaper to keep iterating in one repo
  before committing to a public package boundary.

**Revisit when:** a second skill type (B/D) is generated for real use, or
another repo/team needs `trapezia_skill_spec` without also wanting
`trapezia_skill_validator`.

This is a recommendation, not an executed merge — merging `multi-harness-poc`
into `master` is a separate, explicit step to take with Chris's sign-off.
