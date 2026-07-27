# Design: cross-harness memory — evaluation, rulings, and recommendation

**Created:** 2026-07-25 (Phase 2, G3)
**Role:** Architect
**Inputs:** `VISION.md`, `REQUIREMENTS.md` (FR-1…FR-14, NFR-1…NFR-7, A-1…A-5), `RESEARCH.md`
**Status:** DONE_WITH_CONCERNS — see §16.

> This project's deliverable is a **decision**. This document is therefore both the
> functional design (§10) and the evaluation that selects what gets designed (§2–§9).
> Requirement text is referenced by ID, not quoted — see `REQUIREMENTS.md`.

---

## 1. The reframe that drives every ruling

The four goals in `VISION.md` are not all on the same clock, and treating them as if they
were is what makes this decision look harder than it is.

| Goal | Clock |
|---|---|
| (i) cross-harness continuity | **End state** — matters once we know which harness(es) we keep |
| (ii) one shared memory substrate | **End state** — explicitly "long-term" in `VISION.md` |
| (iii) avoid re-teaching env facts | **Now** — the cost is being paid during the parallel run |
| (iv) evaluation fairness | **Now, and only now** — it exists solely for the parallel-run window |

Goals (i) and (ii) describe the architecture we want **after** the parallel evaluation
concludes. Goal (iv) exists **only during** it. And they are in direct tension: a shared
memory plane spanning both harnesses makes the comparison measure *harness + shared layer*
rather than *harness*. Each harness's memory system is one of the most decision-relevant
things that differentiates them — putting a common substrate underneath both during the
evaluation destroys the signal the evaluation exists to produce.

**Ruling: the shared-substrate goal is an end-state goal and should be built after the
evaluation concludes, not during it.** Building it now optimises a primary goal by
sacrificing the very process that determines whether that goal's target architecture is
one harness or two.

This is not an argument for inaction. Goal (iv) has *two* failure modes, and plain
inaction hits the other one:

- **Contamination** — a shared runtime memory plane; the comparison stops being about the
  harnesses. (What options A/B/C do.)
- **Asymmetric starvation** — OrionLab carries accumulated workspace memory and authored
  `AGENTS.md`/`TOOLS.md` prompts; HermesLab starts from zero. Judging Hermes in that state
  is the exact unfairness `VISION.md` names. (What doing literally nothing does.)

The needle to thread is a **symmetric, static, authored baseline** given identically to both
harnesses, with each harness's own memory system left untouched and independently
observable. That is the shape of the recommendation in §8.

---

## 2. The rubric (FR-1)

Every option is scored against all twelve criteria. R5–R8 are **disqualifying**: fail one
and the option is out, with the criterion named.

| # | Criterion | Source | Type |
|---|---|---|---|
| R1 | Serves goal (i) cross-harness continuity | VISION, FR-3 | graded |
| R2 | Serves goal (ii) one shared substrate | VISION, FR-3 | graded |
| R3 | Serves goal (iii) avoid re-teaching env facts | VISION, FR-3 | graded |
| R4 | Serves goal (iv) evaluation fairness | VISION, FR-3 | graded |
| **R5** | **Never writes either harness's own memory files** | **FR-9** | **disqualifying** |
| **R6** | **Lab/test boundary enforced by construction** | **FR-10** | **disqualifying** |
| **R7** | **Works for both harnesses (or limitation accepted)** | **FR-11** | **disqualifying** |
| **R8** | **Topology strictly horizontal / tier-peered** | **FR-14** | **disqualifying** |
| R9 | Licensing exposure | FR-2 | graded |
| R10 | Third-party data egress | FR-2 | graded |
| R11 | Reversibility / exit cost | FR-12 | graded |
| R12 | Build cost, and whether it reuses an existing Trapezia asset | dev principle #7, retuning note | graded |

Graded scale: **Strong / Partial / None / Adverse** for R1–R4; **Low / Moderate / High** for
R9–R12 risk-and-cost. "Partial" is never rounded up to "Strong" (FR-3 acceptance criterion).

---

## 3. Disqualification rulings (R5–R8 applied to every option)

FR-14 is the newest constraint and is applied to **A and B as well as C**, per instruction.

### Option C — wiki-as-shared-layer: **DISQUALIFIED**

- **R8 / FR-14 — FAIL, primary disqualifier.** `advena-wiki` is one bare repo at
  `/opt/trapezia/git/trapezia-wiki-vault.git` with branches `main`, `env/orionlab`,
  `env/oriontest`, `env/advenauat`, `env/ariauat`, `env/salus-family` sharing a single
  origin (`RESEARCH.md` §Option C). A single origin spanning lab, test **and** sensitive
  tiers is vertical topology by construction. It is not partitionable per-tier *within the
  existing asset* — partitioning means standing up separate bare repos per tier-pair, which
  is a different system, not an extension of `advena-wiki`, and therefore not the option as
  scoped in `VISION.md`.
- **R6 / FR-10 — FAIL, secondary disqualifier.** Assumption A-3 was verified false at G6:
  the bare repo's `hooks/` directory contains only `*.sample` files. Exclusion of
  `medical/` and `financial/` is 100 % client-side `.gitignore`; `git add -f` would commit
  and push cleanly to all five `env/*` clones. This is enforcement **by convention**, which
  FR-10 names as insufficient. Remediable (a `pre-receive` hook), and already spun out as a
  separate tracked task — but not remediated today.
- R5 / FR-9 — pass (git files, not harness memory files).
- R7 / FR-11 — partial: orionlab has a live clone and a native skill; hermeslab has no
  clone, no `env/hermeslab` branch, and `WIKI_PATH` unset.

**Note for the record:** the FR-10 gap is a live latent risk to Trapezia *independent of
this decision* and must not be considered closed by C's disqualification here.

### Option B — local provider (`holographic`): **DISQUALIFIED**

- **R7 / FR-11 — FAIL.** FR-11 permits a single-harness limitation to be *accepted as a
  trade-off*, but that escape hatch does not apply here, because the limitation eliminates
  the option's entire reason for existing. `holographic` is Hermes-only (plugin wrapper
  hard-coupled to `agent.memory_provider`, `hermes_cli.config`, `hermes_constants`; no
  OpenClaw equivalent exists) **and** single-process by construction — its shared-connection
  registry is in-memory Python state scoped to one OS process, and
  `apply_wal_with_fallback()` silently drops WAL on NFS/SMB/FUSE, i.e. on exactly the shared
  volume you would need (`RESEARCH.md` §Option B). A store that cannot be read by the second
  harness and cannot safely be opened by a second process **is not a shared layer**. Scored
  against the shared-substrate purpose, its coverage is zero, not partial.
- R5 / FR-9 — pass. `on_memory_write()` mirrors Hermes' builtin memory-tool writes *into*
  `holographic`; it does not write back into `MEMORY.md`/`USER.md`.
- R6 / FR-10 — pass by absence (not installed in sensitive envs).
- R8 / FR-14 — pass trivially (per-container local store, no flow at all).

**Important framing:** `holographic` remaining *enabled locally inside Hermes* is not option
B. That is the status quo, and is subsumed by option D. Option B is specifically "use
`holographic` as the shared layer", and that fails.

### Option A — external layered provider (ByteRover): **NOT disqualified — but UNRESOLVED**

ByteRover is the only candidate in the provider field that is simultaneously non-copyleft,
layering, and present on both harnesses (`RESEARCH.md` §FR-4 answer). Every other provider
fails a leg: Honcho and OpenViking layer but are AGPL-3.0; Hindsight, Mem0 and Supermemory
are permissive but **replace** the exclusive `plugins.slots.memory` slot. So the A field
collapses to ByteRover, and the rulings below are about ByteRover specifically.

- R5 / FR-9 — **pass on the OpenClaw side, unverified on the Hermes side.** On OpenClaw it
  occupies `plugins.slots.contextEngine` with `ownsCompaction: false`, so `memory-core` and
  the workspace memory files are untouched. On Hermes it is one of the eight in-box
  `MemoryProvider`s; by analogy with `holographic` it should mirror *from* memory writes
  rather than write *into* `MEMORY.md`/`USER.md`, but this was **not source-verified**.
  Flagged, not assumed (NFR-3).
- R6 / FR-10 — **partial.** Enforced by the plugin not being installed and no key being
  provisioned in sensitive envs. That is deployment-and-credential discipline — the same
  class as Trapezia's existing per-env `/opt/orion/.env.<env>` policy. Defensible, but it is
  "not configured", which FR-10 explicitly calls out as weaker than "unreachable".
- R7 / FR-11 — **pass. The only option that does.** In Hermes' in-box set *and* a shipped
  ClawHub OpenClaw plugin.
- R8 / FR-14 — **UNRESOLVED, and unresolvable within this project's scope.** Horizontal
  partitioning requires one isolated store per tier-pair (`orionlab↔hermeslab` separate from
  `oriontest↔hermestest`). Two sharing modes, neither cleared:
  - **Cloud-sync mode** — needs verified per-tier-pair account/workspace tenancy. Not
    verified in `RESEARCH.md`; pricing also unknown. Also makes egress the *mechanism* (R10),
    not an optional extra.
  - **Local shared-volume mode** — avoids egress, but reintroduces the multi-process
    single-SQLite contention class that `holographic` demonstrably hit. Not verified for
    ByteRover.

  Clearing R8 requires standing the thing up. `VISION.md` puts live deployment and
  smoke-testing explicitly **out of scope** — paper evaluation only. **Therefore option A
  cannot be cleared within this project.** It is not failed; it is unadjudicated, and
  recommending it today would mean asserting an unverified structural claim about a
  disqualifying criterion, which NFR-3 forbids.

### Option D — do nothing: **passes all four disqualifiers**

R5, R6, R7, R8 all pass — vacuously but genuinely. There is no mechanism, therefore no
write path, no reachability, no asymmetry, and no topology to violate. This is worth stating
plainly rather than treating as a technicality: **the strongest possible answer to FR-9,
FR-10 and FR-14 is "there is no shared runtime store at all."**

---

## 4. Full rubric scoring (FR-1 — no option silently dropped)

`D+` is the bounded combination recommended in §8: option D's *mechanism* decision (no
shared memory substrate) plus one static, symmetric, authored artifact delivered through the
Phases 1–5 generator.

| | **A** ByteRover | **B** holographic | **C** wiki | **D** do nothing | **D+** recommended |
|---|---|---|---|---|---|
| R1 continuity | Strong (passive capture) | None (Hermes-only) | None | None | **Partial** — articulable prefs only, no passive capture |
| R2 shared substrate | Strong | None | None (adds a *third* memory concept) | None | **Partial** — one shared *authored* substrate, not one memory plane |
| R3 env facts | Strong | None | Partial (best of A/B/C) | None | **Strong** |
| R4 eval fairness | **Adverse** (contaminates) | Adverse (asymmetric) | **Adverse** (OpenClaw pre-populated) | **Adverse** (Hermes starved) | **Strong** — symmetric by construction |
| **R5 FR-9** | pass (Hermes side unverified) | pass | pass | pass | **pass** |
| **R6 FR-10** | partial (config/deploy) | pass | **FAIL** | pass | **pass** |
| **R7 FR-11** | pass | **FAIL** | partial | pass | **pass** (generator emits all three harnesses) |
| **R8 FR-14** | **UNRESOLVED** | pass | **FAIL** | pass | **pass** (no flow exists) |
| R9 licensing | Moderate — ELv2, *not* OSI open source | Low (MIT) | Low (none) | Low (none) | **Low (none)** |
| R10 egress | Moderate–High if cloud sync is the sharing mechanism | **None** (verified by exhaustive grep) | None (self-hosted) | None | **None** |
| R11 reversibility | Moderate — uninstall + revoke + third-party deletion request | Low | High — pushed content is unremovable from history | Nil | **Very low** — delete one spec, regenerate |
| R12 build cost / reuse | Moderate; net-new dependency | High (build an OpenClaw wrapper from scratch) | Moderate; extends an existing asset | Nil | **Low — reuses the Phases 1–5 generator, zero new architecture** |
| **Verdict** | unadjudicated (R8) | **DISQUALIFIED (R7)** | **DISQUALIFIED (R8, R6)** | viable | **recommended** |

Per NFR-5, option D was scored on the identical rubric and is a valid successful outcome. It
loses to D+ on exactly one criterion — R4, evaluation fairness — and that is the criterion
`VISION.md` says the parallel run exists to protect.

---

## 5. Goal-by-option matrix (FR-3)

Partial is stated as partial.

| Goal (rank) | A ByteRover | B holographic | C wiki | D nothing | **D+ recommended** |
|---|---|---|---|---|---|
| **(i) cross-harness continuity — PRIMARY** | Serves | Does not serve | Does not serve | Does not serve | **Partially serves** — carries preferences Chris can *articulate*; does **not** passively learn working style |
| **(ii) one shared substrate — PRIMARY** | Serves | Does not serve | Does not serve | Does not serve | **Partially serves** — one shared authored source of truth for the shared surface; **not** a shared memory plane. The architectural goal is **deferred, not met.** |
| **(iii) avoid re-teaching env facts — secondary** | Serves | Does not serve | Partially serves | Does not serve | **Serves** |
| **(iv) evaluation fairness — secondary** | **Actively harms** | Actively harms | **Actively harms** | **Actively harms** | **Serves** |

The honest headline: **no available option serves both primary goals without harming goal
(iv), and the only option that serves (i) and (ii) fully — A — cannot have its disqualifying
topology criterion cleared without live work this project has ruled out of scope.**

---

## 6. FR-5 / OQ-3 — how much memory genuinely needs to be shared? *(the crux)*

This is the question that decides the whole evaluation, and the answer is: **much less than
the framing assumes.**

Take the "diverge by product" end state seriously — OpenClaw→Salus, Hermes→Trapezia-Insure/
Aria — and partition the memory:

### Genuinely shared (small, slow-moving, curated)

| | Content | Volume | Change cadence | Already authored? |
|---|---|---|---|---|
| **S1** | Operator identity & working preferences — tone, approval discipline (ask-before-push, Rule 8), handoff habit, how Chris wants to be corrected | ~1 page | monthly | mostly, informally |
| **S2** | Trapezia environment & topology facts — env table, deploy ladder, key paths/ports, credential-locality policy, sensitive-data boundary | ~3 pages | weekly-ish | **yes** — `~/.claude/CLAUDE.md`, `/opt/openclaw-workspace/runbooks/`, repo `HOW-TO.md` |
| **S3** | Engineering conventions — the 8 disciplines, dev principles #1–#8, preferred-libraries, Python/testing conventions | ~2 pages | rarely | **yes** — `trapezia-disciplines` skill |

### Deliberately kept separate

| | Content | Why separate |
|---|---|---|
| **N1** | Product-domain memory (Salus clinical workflow vs insurance/Aria underwriting) | Under product divergence these must not mix. Salus context is PHI-adjacent (A-5); insurance context is noise to Salus. Sharing is a **net negative**, not a missed opportunity. |
| **N2** | Harness-mechanics memory — this harness's tool surface, plugin quirks, config paths | Actively **wrong** in the other harness. Sharing it would mislead. |
| **N3** | Session/episodic transcript memory (e.g. OrionLab's ~40 dated files, ~220 KB) | High volume, low durable signal, tier-local scratch. This is the bulk of what a passive memory provider captures. |
| **N4** | Tier-local operational state — what is deployed where in *this* tier | Sharing it sideways across tiers is precisely what FR-14 forbids; it would route around the Rule 8 promotion gate. |

### The conclusion this forces

The shared surface is **S1 + S2 + S3 ≈ six pages of prose that already exists, is
human-authored, and changes on a human cadence.** It does not need passive capture, a
vector store, trust scoring, temporal decay, an account, or a third party.

> **The genuinely shared surface is a document, not a memory system.**

Everything a memory provider is *good at* — passively capturing high-volume episodic
signal — maps onto N1–N4, the material we have just established should **not** be shared.
`REQUIREMENTS.md` FR-5 states a smaller shared surface must be allowed to change the
recommendation. It does. This finding is what moves the recommendation off option A.

It also answers **OQ-5** (signal quality without reading a sensitive env) as moot: whatever
the true signal-to-noise of passively captured harness memory, that captured material is
N3 — in the deliberately-separate partition — so its quality does not bear on the shared
surface.

---

## 7. FR-4 / OQ-1 — can "layered" and "non-AGPL" both be satisfied today?

**Yes, by exactly one provider — ByteRover — and the win is not clean.**

- OpenClaw has two slot families. `plugins.slots.memory` is an exclusive scalar
  (`src/config/types.plugins.ts:42`, `src/plugins/memory-runtime.ts:10`).
  `plugins.slots.contextEngine` is separate, and the two coexist. Providers that "layer" do
  so by occupying `contextEngine`.
- **Honcho's documented coexistence is narrower than the docs imply** — it works only if you
  never set `plugins.slots.memory` to Honcho at all, because it registers via
  `registerMemoryPromptSection()` rather than `registerMemoryCapability({runtime})`. Mem0 has
  no equivalent escape hatch. Honcho remains AGPL-3.0 with no dual license.
- **Multi-slot (issue #60572) has not landed** as of v2026.6.11. Candidate PR #88504
  implements `memory.recall`/`capture`/`compaction`/`userModel` sub-slots and would dissolve
  the conflict, but is unmerged and awaiting a maintainer product decision. Assumption A-2
  holds for now.
- **ByteRover's ELv2 must be weighed honestly, not scored as a permissive win.** Elastic
  License 2.0 is source-available and non-copyleft, but it is **not OSI open source** — it
  prohibits offering the software as a hosted or managed service. Whether that bites depends
  on whether Trapezia would ever resell a product embedding it. Probability today: low.
  Consequence if it ever applies: a forced re-architecture at the worst time. It is a third
  license category, and calling it "non-AGPL, therefore fine" would be exactly the kind of
  smoothing FR-2 was written to prevent.

So OQ-1 resolves **yes-with-an-asterisk**, and it is no longer the decisive question,
because §6 shows the shared surface does not require a provider at all.

---

## 8. Recommendation (FR-6)

Presented as options, recommendation first.

| | **D+ — no shared memory substrate; one generated shared-context skill** *(recommended)* | **D — plain do-nothing** | **A — adopt ByteRover** |
|---|---|---|---|
| Mechanism | Zero new runtime machinery. The shared surface (§6 S1–S3) is authored once as a spec + reference bundle and emitted per-harness by the existing Phases 1–5 generator. | Nothing. Teach each harness separately for the duration of the parallel run. | Install ByteRover on both harnesses at both tiers; partition per tier-pair. |
| Primary goals | Partial / Partial — deferred to end state | None / None | Serves / Serves |
| Eval fairness (R4) | **Strong** — symmetric baseline, native memory untouched | Adverse — Hermes starved | Adverse — contaminates the comparison |
| Disqualifiers | all pass | all pass | **R8 unresolved**, R6 partial |
| Licensing / egress | none / none | none / none | ELv2 (non-OSI) / cloud egress if sync is the sharing mechanism |
| Cost to build | Low — reuses a CI-tested asset | Nil | Moderate + a live verification phase that is out of scope |
| Cost to exit | Delete one spec, regenerate | Nil | Uninstall, revoke, third-party deletion request |

**Recommendation: D+ — decline to adopt any shared memory substrate during the parallel run,
and instead deliver the small genuinely-shared surface as a static, symmetric,
version-controlled `trapezia-shared-context` skill generated for every harness by the
generator built in Phases 1–5.**

Rationale. The two primary goals are end-state goals, and we do not yet know the end state —
that is precisely what the parallel run is for; committing a shared memory plane now would
degrade the evaluation that decides which architecture the shared plane should serve. Of the
three build options, one is disqualified on topology and boundary enforcement (C), one cannot
form a shared layer at all (B), and the third cannot have its disqualifying topology
criterion cleared without live work this project has ruled out of scope (A). Meanwhile FR-5
shows the material that actually needs sharing is roughly six pages of already-authored,
human-curated prose — a document, not a database — and the material a memory provider excels
at capturing is exactly the material that "diverge by product" says must stay separate.
Delivering that document identically to both harnesses removes the asymmetric-starvation
unfairness of plain D, costs one spec file against machinery that already exists and is
CI-tested, and leaves each harness's native memory system pristine and independently
observable — which is both the safest answer to FR-9/FR-10/FR-14 and the best possible state
for the comparison Chris is actually trying to run.

**Runner-up: A (ByteRover).** It is the only option that fully serves both primary goals.

**Condition under which A wins (FR-6):** all three of —
1. the parallel evaluation **concludes** (harness decision made), so contaminating the
   comparison is no longer a cost; **and**
2. ByteRover per-tier-pair store partitioning is **verified live** — separate workspaces or
   accounts for `lab` and `test`, with cross-tier read proven impossible, not merely
   unconfigured (clears R8/FR-14); **and**
3. either OpenClaw multi-slot PR #88504 lands (making the layering general and durable rather
   than dependent on the `contextEngine` side-door), **or** local shared-volume operation is
   verified free of the multi-process SQLite contention class `holographic` exhibited — so
   that sharing does not *require* cloud egress.

A weaker single trigger: if Chris judges the parallel run will last **many months** and the
duplicative-teaching cost proves to be dominated by material in the S1 "working style"
bucket rather than S2/S3 env facts, then passive capture earns its keep and A moves ahead
even mid-run. That would invalidate the §6 partition, which is the load-bearing finding.

**Confidence: 70 %.**
Above the ≤60 % adversarial-doubt threshold, but not comfortably. What holds it down: the
recommendation **defers two goals Chris ranked PRIMARY**, and the §6 partition — while
well-evidenced — is my analysis rather than an observed measurement. The main things that
would raise it: Chris confirming the shared surface really is S1–S3; a short parallel run
(A-4 weakening). The main thing that would lower it: Chris caring more about (ii) as a
near-term architectural commitment than about protecting the evaluation window.

---

## 9. Reversibility and exit cost (FR-12)

| Option | Exit path | Cost | Residue |
|---|---|---|---|
| **D+** | Delete `specs/trapezia-shared-context.yaml` and `skills/trapezia-shared-context/`, regenerate, redeploy | **Minutes.** Additive files only; no runtime coupling, no state, no account | None |
| D | n/a | Nil | None |
| A | Unset slot, uninstall plugin, revoke key, request third-party data deletion | Days, plus loss of whatever tuning accrued | Captured content in a third-party store until deletion is confirmed |
| B | Disable provider | Low | Local SQLite file |
| C | Remove clone/branch | Low to remove — **but pushed content is permanent in git history** | Irreversible if anything sensitive ever lands |

D+ is the cheapest possible exit consistent with doing anything at all, which matters
because OQ-4 (Hermes' longevity) remains **unresolved and is recorded as a standing
uncertainty**. Note the reflexive point: "keep both, diverge by product" would make Hermes
durable by decision — but that decision is an output of the parallel run, so it cannot be
used as an input to justify committing to shared infrastructure now.

---

## 10. Functional design of the recommendation

Only D+ has an implementable component; A/B/C are disqualified or unadjudicated.

### Components and responsibilities

| Component | Responsibility | Owner |
|---|---|---|
| `specs/trapezia-shared-context.yaml` | Single canonical declaration of the shared surface: name, version, triggers, guardrails, bundle manifest | new (chunk 2) |
| `skills/trapezia-shared-context/references/*.md` | The authored content — `operator-preferences.md` (S1), `environment-facts.md` (S2), `engineering-conventions.md` (S3) | new (chunk 2) |
| `trapezia_skill_spec.generate` + `cli` | Renders per-harness `SKILL.md` from `templates/{claude_code,hermes,openclaw}.md.j2`, copies the bundle verbatim | **existing, unchanged** |
| `generated/{claude_code,hermes,openclaw}/trapezia-shared-context/` | Per-harness deliverable | generated output |
| Existing regeneration-drift test | Guarantees `generated/**` matches `specs/**` | **existing, unchanged** |
| Existing `sensitive-data-guard` PreToolUse hook | Blocks sensitive content entering a Trapezia repo commit | **existing, unchanged** |

### Data flow

```
  human-authored prose (from CLAUDE.md / runbooks / trapezia-disciplines)
        │  (curation — a human act, not a capture pipeline)
        ▼
  skills/trapezia-shared-context/references/*.md  +  specs/trapezia-shared-context.yaml
        │  trapezia_skill_spec.cli  (deterministic, CI-verified)
        ▼
  generated/claude_code/… │ generated/hermes/… │ generated/openclaw/…
        │  existing governed per-env deploy flow (Rule 8 gates unchanged)
        ▼
  hermeslab + orionlab   ·   hermestest + oriontest     (each tier deployed independently)
```

### Why this satisfies the disqualifying criteria structurally

- **FR-9** — the only files written are skill files under `generated/`. Nothing in the path
  can address `workspace/memory/`, `users/*/MEMORY.md`, or `memories/MEMORY.md`/`USER.md`.
- **FR-10** — there is no ingest. Content originates from human-authored non-sensitive
  sources; no code reads any environment, sensitive or otherwise. A sensitive env is
  unreachable because **no reachability mechanism exists**, which is stronger than "not
  configured".
- **FR-11** — the generator emits all three harness flavours from one spec. Cross-harness
  support is the asset's purpose, not an adaptation.
- **FR-14** — there is no store, no sync, no flow, and therefore no topology. The artifact
  reaches a tier only through the existing human-approved deploy ladder, so Rule 8 is
  reinforced rather than routed around.
- **FR-13** — implementation flows through `trapezia_skill_spec` and is covered by the
  existing drift test. No duplication of the generator.

### Explicit rulings on things deliberately *not* built

| Proposed | Ruling |
|---|---|
| A new lab/test-only content guard | **Not built.** The registered `sensitive-data-guard` PreToolUse hook already blocks sensitive data in Trapezia repo commits, and the design has no automated ingest for a guard to sit on. Adding one would guard only against a human typing PHI into a YAML — already covered. (Dev principle #7: don't hand-roll what exists.) |
| Any automated capture / summarisation of harness memory | **Not built.** That material is §6 N3, the deliberately-separate partition. |
| A fourth memory concept in OpenClaw | **Avoided by construction** — a skill, not a memory subsystem. OpenClaw already runs two wiki-like systems; option C would have made three. |
| An LLM in the delivery path | **None.** The path is fully deterministic (dev principle #1); curation is a human editorial act performed before the pipeline, not an inference step inside it. |

---

## 11. Requirements traceability (verification before completion)

Every FR and NFR checked against this design. No requirement is unaddressed without an
explicit ruling.

| ID | Responsible component / ruling | Status |
|---|---|---|
| FR-1 | §2 rubric, §4 scoring — all four options scored, disqualifiers named (§3) | ✅ |
| FR-2 | §4 R9/R10 + §7 ELv2 treatment; licenses verified at source in `RESEARCH.md` | ✅ |
| FR-3 | §5 goal-by-option matrix; partials stated as partial | ✅ |
| FR-4 | §7 — resolved yes-with-asterisk (ByteRover only); #60572 status stated | ✅ |
| FR-5 | §6 — shared surface = S1–S3; separate = N1–N4; **this finding changed the recommendation** | ✅ |
| FR-6 | §8 — recommendation, runner-up A, three-part flip condition, confidence 70 % | ✅ |
| FR-7 | Chunk 1 → `docs/superhuman/notes/2026-07-25-phase6-memory-decision.md` | ⏳ chunk 1 |
| FR-8 | Chunk 1 → memory update + roadmap #128 supersede **draft**, presented before any GitHub write | ⏳ chunk 1 |
| FR-9 | §10 — no write path to any harness memory file exists | ✅ |
| FR-10 | §10 — no ingest, no reachability mechanism | ✅ |
| FR-11 | §10 — generator emits all three harnesses; B's failure ruled in §3 | ✅ |
| FR-12 | §9 — exit = delete one spec, regenerate | ✅ |
| FR-13 | §10 — flows through `trapezia_skill_spec`, covered by the drift test | ⏳ chunk 2 |
| FR-14 | §3 (C disqualified, A unresolved, B/D pass), §10 (D+ has no topology) | ✅ |
| NFR-1 | No sensitive env read in design or research; C's `env/ariauat`/`env/salus-family` contents deliberately not read | ✅ |
| NFR-2 | This phase is read-only; D+ never mutates harness memory state | ✅ |
| NFR-3 | Load-bearing claims cite `RESEARCH.md` source verification; unverified items flagged (ByteRover Hermes-side FR-9, tenancy partitioning, Supermemory slot) rather than smoothed | ✅ |
| NFR-4 | §7 describes AGPL/ELv2 exposure with specificity and renders **no legal conclusion**; not legal advice | ✅ |
| NFR-5 | §4 — D scored on the identical rubric; D+ is a bounded form of D, and recommending it is a successful outcome | ✅ |
| NFR-6 | Chunk 2 acceptance requires pytest green, `mypy --strict` clean, CI green, ask-before-push | ⏳ chunk 2 |
| NFR-7 | Design adds no coupling; `trapezia_skill_spec` still never imports `trapezia_skill_validator` | ✅ |
| A-1 | Untested (no live provider adopted) — moot under D+ | n/a |
| A-2 | Holds — #60572 unmerged; noted as a flip condition | ✅ |
| A-3 | **Invalidated** (G6). Consumed as a disqualifier for C; remediation tracked separately | ✅ |
| A-4 | **Load-bearing.** If the parallel run is short, plain D beats D+ and chunk 2 should not be built — see §16 concern 6 | ⚠️ |
| A-5 | Holds trivially — no external layer is adopted, so nothing egresses | ✅ |
| OQ-1 | §7 | resolved |
| OQ-2 | §3 + §5 — wiki serves goal (iii) partially only; disqualified regardless | resolved |
| OQ-3 | §6 | resolved |
| OQ-4 | Hermes longevity — **unresolved, recorded as a standing uncertainty**; §9 explains why it cannot be used as an input | standing |
| OQ-5 | §6 — moot; passively captured memory is partition N3 | resolved |

---

## 12. ARCHITECTURE.md trigger ruling (required at G3)

**Ruling: ARCHITECTURE.md is NOT required and is NOT declared as an artifact.**

The trigger fires on 2+ independently deployable units, external-API integration, or
cross-process IPC. Against the recommended design:

| Trigger | Present? | Why |
|---|---|---|
| 2+ independently deployable units | **No** | One generated skill artifact riding the existing per-env deploy flow. No new deployable unit. |
| External-API integration | **No** | No third-party service, no account, no network call anywhere in the path. |
| Cross-process IPC | **No** | Static files. No daemon, no socket, no shared store. |

Stated explicitly for the record: **had option A been recommended, the external-API trigger
would have fired and ARCHITECTURE.md would be mandatory** — covering tenancy partitioning
per tier-pair, credential locality, and the egress boundary. If Chris overrides toward A at
G3, this ruling reverses and ARCHITECTURE.md must be added before any implementation chunk.

---

## 13. Declared artifact set (G3)

| Artifact | Owner | Status |
|---|---|---|
| `VISION.md` | PM | done (G0) |
| `REQUIREMENTS.md` | PM | done (G2, amended at G6 with FR-14) |
| `RESEARCH.md` | PM / research dispatches | done (Phase 2) |
| `DESIGN.md` | Architect | **this document** |
| `ARCHITECTURE.md` | — | **explicitly NOT declared** (§12) |
| `docs/superhuman/notes/2026-07-25-phase6-memory-decision.md` | Developer | chunk 1 (FR-7) |
| `multi-harness-poc` memory update | Developer | chunk 1 (FR-8) |
| Roadmap `#128` supersede comment — **draft only, approval-gated** | Developer | chunk 1 (FR-8) |
| `specs/trapezia-shared-context.yaml` + `skills/trapezia-shared-context/references/*.md` + regenerated `generated/**` | Developer | chunk 2 (FR-13) — **decision-gated** |
| Test coverage | QA | existing pytest suite + regeneration-drift test; chunk 2 adds spec-lint coverage only |

No Business Expert artifact — deliberate omission already logged in `REQUIREMENTS.md`
§Domain context.

---

## 14. Chunking

### Strategy

| | **Value-first, decision-first** *(recommended)* | Foundation-first | Hybrid |
|---|---|---|---|
| Spine | Ship the decision artifact before any code, because the code is contingent on the decision | Bump the spec schema first, then author content | Draft note and schema in parallel |
| Pro | Chris can approve or reject D+ before a line of implementation exists; if he chooses plain D, chunk 2 is simply never built and nothing is wasted | Unblocks chunk 2 cleanly | Faster wall-clock |
| Con | Chunk 2 may need a small schema decision made under time pressure | **Builds machinery before the decision that justifies it** — exactly the sunk-cost trap this evaluation is guarding against | Same trap, diluted |
| Verdict | **chosen** | rejected | rejected |

Value-first is already the project's declared `Value-vs-foundation` setting, and it is
correct here for a stronger reason than consistency: the entire recommendation rests on
*not* building things before the decision that justifies them. Building the foundation first
would contradict the design's own argument.

### Draft chunk list

| # | Title | Strategy alignment | Foundation? | Est. size | Acceptance criteria |
|---|---|---|---|---|---|
| 1 | Phase 6 decision note + memory update + roadmap #128 supersede draft | value-first (the deliverable IS the decision) | No | ~150 lines, docs only | Note exists at `docs/superhuman/notes/2026-07-25-phase6-memory-decision.md`, matches the `2026-07-25-phase6-*.md` pattern and the Phase 3/4/5 evidence-note convention; names the disqualified options **by criterion**; states exit cost and the runner-up flip condition; carries the NFR-4 legal disclaimer; `multi-harness-poc` memory updated; roadmap #128 comment **drafted and presented for approval, not written to GitHub**; committed, ask-before-push honoured |
| 2 | `trapezia-shared-context` spec + reference bundle + per-harness generation | value-first | Yes (but reuses existing foundation — no new architecture) | ~250 lines (1 YAML + 3 reference `.md` + regenerated output) | Spec lints clean; `trapezia_skill_spec` CLI regenerates all three harness trees; existing regeneration-drift test green; `pytest` green; `mypy --strict` clean; reference content sourced only from non-sensitive authored material; no invoke touches any memory path; CI green after push |
| 3 | *(conditional)* schema support for reference-only skills | foundation | Yes | ~80 lines src + tests | Only built if chunk 2 takes option **2b** below. `spec_version` bumped; empty `invokes` accepted when `bundle` is non-empty; the three existing specs parse unchanged; tests cover both shapes; `mypy --strict` clean |

**Chunk 2 is gated on Chris approving D+ over plain D at G3/G4.** If he prefers plain D, the
project closes after chunk 1 — a two-chunk project shrinking to one. That is an honest
outcome, not a shortfall; §4 shows D and D+ differ on exactly one criterion.

### A real constraint chunk 2 must resolve (surfaced, not deferred)

Verified in the code: `schema.py:100–102` requires `invokes` to be a **non-empty list**, and
there is no `references` field — reference assets ride the `bundle:` list, copied verbatim by
`cli.py:_copy_bundle`. So a knowledge-only skill is **not expressible under `spec_version: 0`
as written.** Two ways out, recommendation first:

| | **2a — trivial CLI invoke** *(recommended)* | 2b — schema bump for reference-only specs |
|---|---|---|
| Shape | `invokes: [{kind: cli, exec: cat {skill_root}/references/environment-facts.md}]` — a real, useful "dump the context" entry point | Allow empty `invokes` when `bundle` is non-empty; bump `spec_version` |
| Cost | Zero source change; chunk 3 never happens | ~80 lines + tests + a spec-version migration story |
| Risk | Slightly contrived — the invoke exists partly to satisfy the schema | Widens the schema for one consumer; three existing specs must be re-verified |
| Verdict | **chosen** | fallback if 2a reads as a hack in review |

2a is recommended because the invoke is not purely ceremonial — an explicit "print the shared
context" command is genuinely useful to both harnesses and to a human debugging what a
harness was told, and it keeps the generator untouched, which is the whole point of reusing
it. If review judges it contrived, 2b is a clean fallback and chunk 3 activates. **This is a
Developer-facing constraint I am flagging, not resolving by fiat** — the final call belongs
with whoever implements chunk 2.

---

## 15. Value definition (one line)

> A signed-off ruling on cross-harness memory that names, by criterion, why each rejected
> option fails — and, only if approved, the small genuinely-shared surface delivered
> identically to both harnesses through the generator that already exists.

---

## 16. DONE_WITH_CONCERNS

Surfaced explicitly rather than hidden, per the role's honesty requirement.

1. **Both PRIMARY goals are deferred, not met.** The recommendation fully serves one
   secondary goal and evaluation fairness; it partially serves the two goals Chris ranked
   primary. §1 argues those are end-state goals, but this is a real gap against a stated
   ranking and Chris may legitimately reject the reframe. **This is the single most likely
   reason the recommendation is overturned.**
2. **Option A is unadjudicated, not defeated.** Its FR-14 partitionability cannot be cleared
   without live verification, which `VISION.md` puts out of scope. If Chris wants A properly
   judged, that requires a scope change to permit a bounded live test — a legitimate ask that
   this design cannot satisfy from paper alone.
3. **ByteRover's FR-9 behaviour on the Hermes side is not source-verified.** Inferred by
   analogy with `holographic`. It does not change the ruling (A is held up by FR-14, not
   FR-9), but the gap is recorded.
4. **Chunk 2 is not free.** The `invokes`-required constraint means it is a design decision
   plus a spec plus authored content, not "one YAML file". Estimated small, but not zero —
   see §14 2a/2b.
5. **The wiki FR-10 gap remains open.** Disqualifying option C does not remediate it. A
   Trapezia-owned bare repo has no server-side enforcement against pushing `medical/` or
   `financial/` content to branches that reach sensitive-tier clones. Latent, not realised —
   and tracked separately, not here. It should not be considered closed by this document.
6. **A-4 is load-bearing and unverified.** The whole case for chunk 2 assumes the parallel
   run is long enough for duplicative teaching to cost real time. If Chris expects weeks
   rather than months, **plain D is the better answer and chunk 2 should be dropped.** This
   is a one-question check worth asking at G3 before chunk 2 is authorised.
7. **OQ-4 (Hermes longevity) stays unresolved.** Recorded as a standing uncertainty. It is
   mitigated rather than answered — D+'s exit cost is minutes, so being wrong about Hermes is
   cheap under this recommendation and expensive under A or C.
