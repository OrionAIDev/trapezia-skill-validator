# Superhuman: memory-sync evaluation and decision (HermesLab POC Phase 6)

**Slug:** memory-sync-evaluation
**Started:** 2026-07-25
**Superhuman-version:** 1.0.1
**Vision (one-liner):** Decide whether Trapezia should build a deterministic OpenClaw→Hermes memory-sync tool, adopt Hermes' in-box Honcho memory plugin, or do neither — and produce a decision Chris can sign off on.
**Cadence:** per-chunk
**Value-vs-foundation:** value-first
**Parallelism preference:** PM-decides
**Git:** remote
**Remote:** https://github.com/OrionAIDev/trapezia-skill-validator (existing)
**Branch strategy:** existing branch `multi-harness-poc`; `master` in sync as of 80e1216
**Value definition:** a defensible, evidence-backed recommendation Chris can sign off on — assessed against the two primary goals (cross-harness continuity, one shared memory substrate), the sustained-parallel-operation driver, the corruption-safety constraint, the lab/test-only constraint, and licensing/data-egress exposure
**Conventions in effect:** conventions/git.md, conventions/python.md, conventions/testing.md; plus repo-local Trapezia disciplines (docs/superhuman/{plans,notes}/, ask-before-push, verify-CI-green)
**HITL-level:** H
**Modifies-existing-code:** yes
<!-- Host repo `trapezia-skill-validator` has 6 prior phases of tracked content predating this
     superhuman session. Resolved at Step 0.5 as legacy-import (user decision, see Decisions log):
     existing code/artifacts are read-only reference; all 8 gates still run for Phase 6. -->

<!-- **Resolved rung:** laptop (matched by default; profile sha256:383753d5656…) -->
<!-- authority tier 6, specificity 1, no ties. promote_into: none. act_unattended: any_of [self]. -->

## Declared artifacts
<!-- PM appends one line per declared artifact at G3 -->
- VISION.md (PM) — drafted at G0
- REQUIREMENTS.md (PM) — Phase 1
- DESIGN.md (Architect) — Phase 2
- (remainder declared at G3)

## Decisions log
<!-- Append-only. Format: [<ISO timestamp>] G<n>: <one-line summary>; user decision: <decision> -->
- [2026-07-27T22:50:39Z] **G3: ABORT — PROJECT CLOSED.** PM presented the Architect's D+ recommendation (70%) together with the adversarial review that split it (negative half ~80% on repaired reasoning; positive half ~30%, refuted), plus three options for proceeding; user decision: **"I do not like any of these results. Consider memory-sync to be canceled/closed and off-the-table."** No shared cross-harness memory layer will be built or adopted. Roadmap #128's `memory-sync` line item is CLOSED, not delivered. This is a valid terminal outcome per NFR-5 (which made "do nothing" a first-class success). Decision note: `docs/superhuman/notes/2026-07-27-phase6-memory-sync-closed.md`. Two carry-forward findings explicitly do NOT close with this decision — the `advena-wiki` boundary gap (convention, not construction) and the `~/.claude/CLAUDE.md` sensitive-content risk; both recorded in the note.
- [2026-07-25T18:43:25Z] Step 0.5 (pre-existing-code drift check): host repo has src/, tests/, pyproject.toml and Phases 0–5 history built outside the superhuman flow; PM recommended legacy-import; user decision: legacy-import — keep existing repo as read-only reference, run all 8 gates for Phase 6.
- [2026-07-25T19:05:00Z] G0 round 1: PM recommended approve; user decision: refine — five substantive changes required (bi-directional sync + corruption-safety as a first-class constraint; goals re-ranked with continuity + shared-substrate primary, driven by sustained parallel operation and possible product divergence; lab signal-to-noise reading corrected as an unfair sample; master merge promoted to a precondition; Honcho reframed as a layering option with AGPL exposure as a first-class criterion). VISION.md revised.
- [2026-07-25T19:08:04Z] Precondition (user-directed, pre-Phase-6): `multi-harness-poc` → `master` merged. Clean `git merge --ff-only`, 8 commits, `cf7fe56..80e1216`, pushed; CI green (run `30171008308`). Branches in sync.
- [2026-07-25T20:10:00Z] G6 (Moderate drift, assumption A-3 invalidated): PM recommended CONTINUE with option C re-scored + wiki boundary gap spun out separately; user decision: **CONTINUE, fix wiki separately**. User additionally imposed a new hard constraint → recorded as **FR-14**: memory sync must be strictly horizontal/tier-peered (`orionlab ↔ hermeslab`, `oriontest ↔ hermestest`) with NO cross-tier flow (no lab→test, no test→UAT). Disqualifying criterion. REQUIREMENTS.md amended mid-project.
- [2026-07-25T19:45:00Z] G2: REQUIREMENTS approved (13 FR / 7 NFR / 5 assumptions / 5 open questions); user decision: approve as-is — proceed to design.
- [2026-07-25T19:35:00Z] G1: workflow preferences; user decision: approve all four PM recommendations as-is — HITL-level H, cadence per-chunk, value-first, parallelism PM-decides. Git recorded as remote/existing-branch by context (not asked).
- [2026-07-25T19:32:00Z] G0: VISION approved (round 3); user decision: approve — proceed to G1. Option set locked at A (external layered provider, non-AGPL preferred) / B (local provider) / C (wiki-as-shared-layer) / D (do nothing).
- [2026-07-25T19:20:00Z] G0 round 2: PM recommended approve; user decision: narrow AND expand — (a) DROP the bi-directional `memory-sync` tool from scope entirely (roadmap #128 line item superseded, not delivered); (b) widen to layered-memory alternatives similar to Honcho but WITHOUT AGPL exposure; (c) add the existing `advena-wiki` project as a candidate shared layer. VISION.md revised; option set is now A/B/C/D.

## Chunk log
<!-- Append-only table. -->
| # | Title | Files | Dev model | Status | Started | Ended |
|---|---|---|---|---|---|---|

## Drift notes
<!-- Append-only. Format: [<ISO timestamp>] Chunk <n>: <severity> — <one-line trigger>; action: <taken> -->
- [2026-07-25T21:00:00Z] Phase 2 (pre-G3): **MODERATE** — PM-commissioned adversarial review of DESIGN.md returned SURVIVE-WITH-AMENDMENTS, splitting the recommendation into a negative half (~80%, sound conclusion but published reasoning defective) and a positive half (chunk 2 / D+, ~30%, sole differentiator refuted). Landed objections: (1) FATAL to chunk 2 — D+ adds the same content to both harnesses, but the starvation differential is *unequal baselines*, so an equal increment preserves it rather than curing it; (2) the fairness argument as written is a methodological error (a constant applied to both arms does not bias a contrast) though a valid replacement exists unused in RESEARCH.md (ByteRover occupies `contextEngine` on OpenClaw vs `MemoryProvider` on Hermes → treatment-by-arm interaction + masking); (3) the FR-5 partition argues from volume rather than tacitness, is circular against OQ-5, and its "providers capture what must not be shared" step is false for user-modeling providers; (4) an uncited and overstated safety claim about `sensitive-data-guard`, plus a real content-boundary hole (the named S2 source contains sensitive-tier topology and a clinical user identifier); (5) options C′ (per-tier-pair repo + `pre-receive` hook, cures both of C's disqualifiers), E (seed native ambient prompt surfaces), and F (daemon-fronted store, salus-server pattern) never scored; (6) option A ruled "unresolvable in scope" but in fact simply never researched. Not resolved as a standalone G6 — no approved design baseline exists yet to drift from; carried into G3, which is the design-approval gate. Action: G3 presented with both the recommendation and the review.
- [2026-07-25T20:05:00Z] Phase 2 (pre-DESIGN): **MODERATE** — REQUIREMENTS assumption **A-3 invalidated by evidence**. A-3 assumed the `advena-wiki` clone's sensitive-domain exclusion (`medical/`, `financial/`) holds "by construction" via gitignore-at-source. Verified false: the self-hosted bare repo at `/opt/trapezia/git/trapezia-wiki-vault.git/hooks/` contains **only `*.sample` files — no active `pre-receive`/`update` hook**. Enforcement is 100% client-side `.gitignore`; `git add -f` (or a locally edited `.gitignore`) would commit and push sensitive content cleanly and propagate to all five `env/*` branch clones. Secondary findings: wiki branches have already diverged (182 files between `env/advenauat` and `env/orionlab`); no `env/hermeslab` branch exists; OpenClaw already runs two wiki-like systems (custom `wiki` skill + native `memory-wiki` plugin). Action: G6 raised.

## Archive log
<!-- Append-only. Format: [<ISO timestamp>] archived <chunk> to archive/<dir>/; reason: <reason> -->

## Recommendation overrides
<!-- Append-only. Format: [<ISO timestamp>] G<n>: PM recommended <X>; user chose <Y>; reason: <if given> -->
- [2026-07-25T19:05:00Z] G0 r1: PM recommended approve; user chose refine (5 substantive changes).
- [2026-07-25T19:20:00Z] G0 r2: PM recommended approve as-is; user chose narrow+expand (drop sync tool, add non-AGPL alternatives, add wiki).

## Retuning notes
<!-- Append-only. Format: [<ISO timestamp>] G<n>: <observation about user pattern>; bias adjustment: <going-forward note> -->
- [2026-07-25T19:20:00Z] G0 (two consecutive overrides): Chris reliably (a) widens the option set beyond what PM proposes, (b) prefers reusing/extending what already exists over building something new, and (c) treats licensing and data-boundary exposure as first-class selection criteria rather than caveats. Bias adjustment: at G2/G3, present a wider candidate set by default — always including a "reuse existing Trapezia asset" option and a "do nothing" option — and lead each candidate with its licensing + data-egress posture rather than appending it. Do not propose net-new build work without first showing why an existing asset cannot be extended.
