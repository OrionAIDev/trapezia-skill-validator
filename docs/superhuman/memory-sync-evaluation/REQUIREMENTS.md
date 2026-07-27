# Requirements: memory-sync evaluation and decision (HermesLab POC Phase 6)

**Created:** 2026-07-25
**Last revision:** 2026-07-25
**Source vision:** `VISION.md`

## Framing

The deliverable of this project is a **decision**, so the functional requirements split in
two:

- **FR-1 … FR-8 — the evaluation itself.** What Phase 6 must produce for the decision to be
  trustworthy.
- **FR-9 … FR-13 — constraints on whatever is recommended.** These act as *selection
  criteria* during evaluation, and become *implementation requirements* if the decision is
  "adopt/build". An option that cannot satisfy these is disqualified, not merely marked
  down.

## Functional requirements

### The evaluation

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-1 | Evaluate all four options — A (external layered provider, non-AGPL preferred), B (local provider, e.g. Hermes `holographic`), C (wiki-as-shared-layer), D (do nothing) — against one stated, written rubric. | Every option scored against every rubric criterion; no option silently dropped. If an option is disqualified, the disqualifying criterion is named. |
| FR-2 | Assess each option's **licensing exposure** and **third-party data-egress posture** as first-class criteria, not caveats. | Each option carries a license identifier verified at source (not from memory or a summary article) and a plain statement of what data, if any, leaves Trapezia infrastructure. |
| FR-3 | Assess each option against the four ranked goals: cross-harness continuity (primary), one shared substrate (primary), avoid re-teaching env facts (secondary), evaluation fairness (secondary). | A goal-by-option matrix showing which goals each option actually serves and which it leaves unserved. Partial coverage is stated as partial, not rounded up. |
| FR-4 | Resolve VISION open question 1 — whether "layered" and "non-AGPL" can both be satisfied today — with evidence rather than assumption. | A sourced finding on each candidate provider's OpenClaw-side behavior (layers vs replaces the exclusive memory slot), plus the current status of OpenClaw multi-slot memory (issue #60572). |
| FR-5 | Determine how much memory genuinely needs to be **shared** versus deliberately kept **separate**, given the possible "diverge by product" end state (OpenClaw→Salus, Hermes→Trapezia-Insure/Aria). | An explicit statement of the shared surface. A smaller shared surface must be allowed to change the recommendation — this is not a formality. |
| FR-6 | Produce a single recommendation with reasoning, plus the runner-up and the condition under which the runner-up would win. | Recommendation names one option (or a bounded combination), states why, and states what evidence would overturn it. |
| FR-7 | Record the decision as a note under `docs/superhuman/notes/`, following the Phase 3/4/5 evidence-note convention. | File exists, matches the naming pattern `2026-07-25-phase6-*.md`, and is committed. |
| FR-8 | Update the `multi-harness-poc` memory and flag that roadmap `#128`'s `memory-sync` line item is **superseded, not delivered**. | Memory file updated. Roadmap issue update drafted and **presented for approval before any write to GitHub** (external, outward-facing action). |

### Constraints on whatever is recommended

| ID | Requirement | Acceptance criteria |
|---|---|---|
| FR-9 | **No component may write into either harness's own local memory files.** | The recommended option provably never writes OpenClaw's `workspace/memory/`, `users/*/MEMORY.md`, or Hermes' `memories/MEMORY.md`/`USER.md`. This is the corruption risk that caused the sync tool to be dropped; an option that reintroduces it is disqualified. |
| FR-10 | The lab/test-only boundary must be enforced **by construction**, not by convention or agent judgment. | Sensitive environments (advenauat, ariauat, salus-family, oriondev, production) are unreachable by the mechanism itself — e.g. the `advena-wiki` gitignore-at-source precedent — rather than merely "not configured". Consistent with Trapezia development principle #5 (safety-critical paths are always code). |
| FR-11 | The recommended option must work for **both** harnesses, or its single-harness limitation must be stated as an accepted trade-off. | For each harness, a named integration path. `holographic` being Hermes-only, for example, is recorded as a limitation rather than glossed. |
| FR-12 | The decision must be **cheaply reversible**. | The note states the exit/rollback path — what it costs to abandon the choice later — since Hermes' longevity is explicitly unsettled. |
| FR-13 | If implementation follows, it must reuse the Phases 1–5 generator rather than duplicating it, where a per-harness skill wrapper is the delivery vehicle. | Any generated wrapper flows through `trapezia_skill_spec` (`specs/*.yaml` → `generated/**`) and is covered by the existing regeneration drift test. |
| FR-14 | **Sync topology must be strictly horizontal (tier-peered), never vertical.** The only permitted flows are between *like systems at the same rung*: `orionlab ↔ hermeslab`, `oriontest ↔ hermestest`. There must be **no** lab→test, test→UAT, or any other cross-tier memory flow. | The recommended mechanism makes cross-tier flow structurally impossible, not merely unconfigured. An option whose topology allows a shared store, branch, or account to span two tiers is disqualified unless it can be partitioned per-tier by construction. |

> **FR-14 added mid-project** at G6 resolution (Chris, 2026-07-25), after research showed the
> `advena-wiki` topology — one bare repo with five `env/*` branches sharing a single origin —
> is inherently cross-tier. Promotion between tiers is a governed, human-approved act
> (Trapezia Rule 8); memory that flows sideways into it would route around that gate. This is
> a **disqualifying** criterion, not a preference.

## Non-functional requirements

| ID | Requirement | Acceptance criteria |
|---|---|---|
| NFR-1 | No sensitive environment is read during the evaluation. | No command in the evidence trail reads advenauat, ariauat, salus-family, oriondev, or production data. |
| NFR-2 | No live harness memory state is mutated during the evaluation. | HermesLab/hermestest/OrionLab memory files are unchanged; verified before close. |
| NFR-3 | Factual claims are verified at source, not asserted from model knowledge or a single secondary article. | Every load-bearing claim (licenses, plugin behavior, config limits) cites the file, repo, or doc it came from. |
| NFR-4 | No legal conclusion is presented as authoritative. | AGPL exposure is described with enough specificity for Chris to seek a real answer; the note explicitly disclaims legal advice. |
| NFR-5 | The evaluation must be able to conclude "do nothing". | Option D is scored on the same rubric, not treated as failure. A recommendation of D is a valid successful outcome. |
| NFR-6 | Any code written meets repo conventions. | `pytest` green, `mypy --strict` clean for new skill scripts, CI green after push, ask-before-push honored. |
| NFR-7 | `trapezia_skill_spec` remains one-directionally coupled and self-contained. | It never imports from `trapezia_skill_validator`; `spec_lint.py` consumes only its public surface. Per the `feedback-keep-spec-generator-extractable` memory and the Phase 4 decision. |

## Out-of-scope (explicit)

Inherited from `VISION.md`:

- Building the bi-directional `memory-sync` tool (dropped at G0 round 2).
- Deploying or live-smoke-testing Honcho or any other external provider — paper evaluation only.
- Reading, syncing, or touching sensitive environments.
- Mutating live harness memory state.
- Rendering a legal opinion on AGPL.
- Re-litigating the evaluate-then-maybe-build framing.

## Assumptions

| ID | Assumption | If false |
|---|---|---|
| A-1 | Hermes' eight in-box memory providers are usable as shipped in our pinned image, not aspirational stubs. | Option A narrows sharply; drift → REVISIT-DESIGN. |
| A-2 | OpenClaw's memory slot remains exclusive for the duration of the parallel run (multi-slot #60572 not yet landed for us). | If multi-slot lands, the layered/non-AGPL conflict dissolves and option A strengthens. |
| A-3 | The `advena-wiki` clone's sensitive-domain gitignore genuinely holds — `medical/`/`financial/` are absent by construction. | FR-10's precedent collapses; option C needs its own boundary mechanism. |
| A-4 | Chris's parallel-run intent is real and extended (months, not weeks), making duplicative-teaching cost material. | If the parallel run is short, option D ("do nothing") strengthens considerably. |
| A-5 | No PHI/PII enters any shared memory layer, because only lab/test sources feed it. | Any external-provider option becomes untenable on data-boundary grounds regardless of license. |

## Open questions

Carried into Phase 2 (Design), where the Architect resolves them:

- **OQ-1 (→ FR-4):** Can "layered" and "non-AGPL" both be satisfied today?
- **OQ-2 (→ FR-3):** How much of the four goals does a curated wiki actually serve, given it is not passive capture?
- **OQ-3 (→ FR-5):** What is the genuinely shared surface under "diverge by product"?
- **OQ-4:** What is the honest read on Hermes' longevity, and what evidence would change it? *(Informs FR-12 reversibility; may remain unresolved and be recorded as a standing uncertainty.)*
- **OQ-5:** How is signal quality of harness-captured memory assessed without reading a sensitive env? *(Lab is an unfair sample — Chris, G0 r1.)*

## Domain context

Business Expert not dispatched. The domain here is agent-harness infrastructure and
software licensing, not insurance / wealth / EE / trading / healthcare — the Business Expert
role has no applicable domain knowledge to contribute. Logged as a deliberate omission per
the PM role's "declared references" discipline.
