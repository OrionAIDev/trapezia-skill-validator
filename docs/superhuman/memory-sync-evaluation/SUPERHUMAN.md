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
- [2026-07-25T18:43:25Z] Step 0.5 (pre-existing-code drift check): host repo has src/, tests/, pyproject.toml and Phases 0–5 history built outside the superhuman flow; PM recommended legacy-import; user decision: legacy-import — keep existing repo as read-only reference, run all 8 gates for Phase 6.
- [2026-07-25T19:05:00Z] G0 round 1: PM recommended approve; user decision: refine — five substantive changes required (bi-directional sync + corruption-safety as a first-class constraint; goals re-ranked with continuity + shared-substrate primary, driven by sustained parallel operation and possible product divergence; lab signal-to-noise reading corrected as an unfair sample; master merge promoted to a precondition; Honcho reframed as a layering option with AGPL exposure as a first-class criterion). VISION.md revised.
- [2026-07-25T19:08:04Z] Precondition (user-directed, pre-Phase-6): `multi-harness-poc` → `master` merged. Clean `git merge --ff-only`, 8 commits, `cf7fe56..80e1216`, pushed; CI green (run `30171008308`). Branches in sync.
- [2026-07-25T19:35:00Z] G1: workflow preferences; user decision: approve all four PM recommendations as-is — HITL-level H, cadence per-chunk, value-first, parallelism PM-decides. Git recorded as remote/existing-branch by context (not asked).
- [2026-07-25T19:32:00Z] G0: VISION approved (round 3); user decision: approve — proceed to G1. Option set locked at A (external layered provider, non-AGPL preferred) / B (local provider) / C (wiki-as-shared-layer) / D (do nothing).
- [2026-07-25T19:20:00Z] G0 round 2: PM recommended approve; user decision: narrow AND expand — (a) DROP the bi-directional `memory-sync` tool from scope entirely (roadmap #128 line item superseded, not delivered); (b) widen to layered-memory alternatives similar to Honcho but WITHOUT AGPL exposure; (c) add the existing `advena-wiki` project as a candidate shared layer. VISION.md revised; option set is now A/B/C/D.

## Chunk log
<!-- Append-only table. -->
| # | Title | Files | Dev model | Status | Started | Ended |
|---|---|---|---|---|---|---|

## Drift notes
<!-- Append-only. Format: [<ISO timestamp>] Chunk <n>: <severity> — <one-line trigger>; action: <taken> -->

## Archive log
<!-- Append-only. Format: [<ISO timestamp>] archived <chunk> to archive/<dir>/; reason: <reason> -->

## Recommendation overrides
<!-- Append-only. Format: [<ISO timestamp>] G<n>: PM recommended <X>; user chose <Y>; reason: <if given> -->
- [2026-07-25T19:05:00Z] G0 r1: PM recommended approve; user chose refine (5 substantive changes).
- [2026-07-25T19:20:00Z] G0 r2: PM recommended approve as-is; user chose narrow+expand (drop sync tool, add non-AGPL alternatives, add wiki).

## Retuning notes
<!-- Append-only. Format: [<ISO timestamp>] G<n>: <observation about user pattern>; bias adjustment: <going-forward note> -->
- [2026-07-25T19:20:00Z] G0 (two consecutive overrides): Chris reliably (a) widens the option set beyond what PM proposes, (b) prefers reusing/extending what already exists over building something new, and (c) treats licensing and data-boundary exposure as first-class selection criteria rather than caveats. Bias adjustment: at G2/G3, present a wider candidate set by default — always including a "reuse existing Trapezia asset" option and a "do nothing" option — and lead each candidate with its licensing + data-egress posture rather than appending it. Do not propose net-new build work without first showing why an existing asset cannot be extended.
