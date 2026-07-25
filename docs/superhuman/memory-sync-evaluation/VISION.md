# Vision: memory-sync evaluation and decision (HermesLab POC Phase 6)

**Created:** 2026-07-25 (G0)
**Last refined:** 2026-07-25 (post-G0 refinement round 2 — Chris: drop the sync tool, widen to non-AGPL layered alternatives, add the wiki)

## Purpose

Decide how Trapezia should keep memory coherent across **two harnesses running in
parallel for an extended period** — and come out with a recommendation Chris can sign
off on.

This was parked during Phase 1 of the HermesLab multi-harness POC as a cross-cutting
concern (roadmap `OrionAIDev/trapezia-roadmap#128`), originally scoped as a
*deterministic, one-way* OpenClaw→Hermes tool writing Hermes `MEMORY.md`/`USER.md`,
env-mapped, lab/test sources only. Phases 0–5 are complete, pushed, and CI-green, so it
now gets its first real decision point.

**The original framing has been superseded in two ways** (Chris, 2026-07-25):

1. **Sync must be bi-directional**, not one-way. Whatever is learned in either harness
   should be available in the other.
2. **Bi-directional is the dangerous direction.** Hermes and OpenClaw have materially
   different memory-update procedures. A tool that writes *into* OpenClaw's memory risks
   breaking or corrupting it — and protecting the real environments from exactly that
   class of mistake is why Lab and Test exist in the first place.

This project remains **evaluate + decide, not build**. If the evaluation concludes
"build", this same superhuman project carries into implementation.

## Reason

### The primary driver: sustained parallel operation

Chris wants to **run Hermes and OpenClaw side by side for an extended period** to decide
which to keep — with a real possibility that the answer is *both*. A plausible end state
is keeping both at Lab and Test tiers but **diverging by product**: OpenClaw for Salus,
Hermes for Trapezia-Insure / Aria.

The cost that makes this hard is **duplicative work across parallel environments of the
same tier/rung**. If every fact, preference, and convention has to be taught twice, the
parallel evaluation becomes expensive enough to bias the outcome — or to not happen at
all.

### The four goals, ranked

Chris confirmed all four, with an explicit ranking (2026-07-25):

| Rank | Goal | Notes |
|---|---|---|
| **Primary** | **Cross-harness continuity** | Preferences, identity, working style follow Chris between harnesses without re-teaching. Ongoing, not one-shot. |
| **Primary** | **Architectural: one memory substrate** | Long-term, harnesses share one memory plane rather than each keeping an island. |
| Secondary | Avoid re-teaching environment facts | Practical: ports, paths, deploy conventions. |
| Secondary | Evaluation fairness | Don't judge HermesLab while it runs context-starved. |

The two primaries both argue for something **continuous and shared**, not a one-shot
seeding script. That is a meaningful shift from the original roadmap framing.

### The standing pivot

Is Hermes' own longevity sufficient to justify building bespoke Trapezia tooling against
its memory format at all? Still open — and it now cuts both ways, because the
"keep both, diverge by product" end state would make Hermes durable by decision rather
than by external bet.

## Scope as user envisions it

**Decided at G0 round 2 (Chris): the bi-directional `memory-sync` tool is dropped from
scope.** The layering finding below is convincing enough that building a tool to write into
another harness's memory files is not worth evaluating further — it carries the corruption
risk Lab and Test exist to prevent, while a layered approach obtains the same outcome
without ever touching those files. Roadmap `#128`'s `memory-sync` line item is therefore
superseded rather than completed, and this project must say so explicitly.

Phase 6 now evaluates **how to give both harnesses a shared memory layer**, comparing:

- **A — External layered provider**, *non-AGPL preferred* (Chris): Mem0 (Apache-2.0),
  Supermemory (MIT), and others, with Honcho (AGPL-3.0) retained only as the reference
  baseline because it is the one currently documented to layer rather than replace.
- **B — Local/self-contained provider**: Hermes ships `holographic`, a local SQLite fact
  store (FTS5 search, trust scoring, HRR compositional retrieval) with **no cloud service
  and no third-party data egress**.
- **C — Wiki-as-shared-knowledge-layer**: extend the existing `advena-wiki` (git-backed
  markdown, self-hosted bare repo on the VPS) to serve as the durable cross-harness layer.
- **D — Do nothing**: accept duplicative teaching across the two harnesses for the duration
  of the parallel run.

Plus, in all cases:

- Respect the hard constraint: **lab/test sources only, never sensitive environments**
  (advenauat, ariauat, salus-family, oriondev, production).
- Produce a recommendation and decision, recorded under `docs/superhuman/notes/`.
- If the decision is "build/adopt", carry into implementation under this project.

## Scope extensions identified during elicitation

### 1. Honcho is a *layering* option, and both harnesses already support it — confirmed

Chris's hypothesis was that Honcho's value is durable long-term user memory **layered on
top of** each harness's existing local memory, leaving that local memory essentially
unaffected. **Reconnaissance confirms this, and it is stronger than assumed:**

- **Hermes** ships the Honcho memory plugin **in-box** (`/opt/hermes/plugins/memory/honcho/`,
  ~300 KB across 9 modules, `MemoryProvider` interface, OAuth or API key, five tools:
  profile / search / reasoning / context / conclude). Context is injected into the user
  message at call time in two layers on independent cadences.
- **OpenClaw** supports Honcho through the `@honcho-ai/openclaw-honcho` plugin, and its
  docs state plainly that *"Honcho and the builtin memory system can work together"* —
  workspace `USER.md` / `MEMORY.md` / `IDENTITY.md` **remain local**. OpenClaw is also
  moving to a multi-slot memory architecture so several providers can occupy distinct
  layers simultaneously.

**Why this matters:** if both harnesses natively write to and read from one shared layer
while each keeps its own local memory untouched, the continuity and shared-substrate goals
are met **without any process writing into OpenClaw's memory files** — precisely the
corruption risk Chris flagged. This satisfies the bi-directional *requirement* without
bi-directional *sync*, and is why the sync tool was dropped from scope.

### 1b. The provider field is much wider than Honcho — and layering is provider-specific

**Hermes ships eight memory providers in-box**, not one: `byterover`, `hindsight`,
`holographic`, `honcho`, `mem0`, `openviking`, `retaindb`, `supermemory`. So the AGPL
exposure is avoidable in principle — Mem0 is Apache-2.0, Supermemory is MIT, and
`holographic` is a purely local SQLite store with no cloud dependency at all.

**But there is an awkward finding that Phase 1 must confront head-on.** Chris's two
criteria — *layered, not replacement* and *non-AGPL* — may conflict today, on the OpenClaw
side specifically:

- OpenClaw treats memory as an **exclusive slot** (`plugins.slots.memory`). The
  `@mem0/openclaw-mem0` plugin is documented as **replacing** the default memory-core slot.
- OpenClaw's **Honcho** integration is the one explicitly documented to **coexist** with the
  builtin memory system.
- A **multi-slot memory architecture** (OpenClaw issue #60572) is the in-progress work that
  would make layering general across providers — i.e. the conflict may be temporary.

So the provider that best satisfies "layered" is currently the one that fails "non-AGPL",
and vice versa. Resolving this — by picking a horn, by waiting for multi-slot, or by
choosing an option outside the provider category entirely — is core Phase 1/2 work. It is
recorded here rather than smoothed over.

### 3. The existing wiki as the shared layer — Chris's addition

Chris raised the **`advena-wiki`** project as a candidate to eventually meet the same need.
On inspection this is a serious contender, not a consolation option:

- **Already exists and is already governed** — git-backed markdown, self-hosted bare repo on
  the VPS, AdvenaUAT-primary with a laptop clone, documented page/index/log conventions.
- **No licensing exposure whatsoever** — it is git and markdown.
- **No third-party data egress** — self-hosted, unlike every cloud provider above.
- **Sensitive-domain boundary is enforced by construction** — `medical/` and `financial/`
  are gitignored at the source and do not exist in the clone. This is the same
  by-construction enforcement Phase 6 needs for its lab/test-only constraint, already built
  and already trusted.
- **Inherently harness-independent** — any harness that can run git and read markdown can
  use it. That is exactly the multi-harness POC thesis, and it means the wiki layer could be
  delivered as a **generated per-harness skill using the generator built in Phases 1–5** —
  a notable convergence with the work this POC has already done.

Honest caveats for Phase 1: the wiki is **curated knowledge, not automatic memory capture** —
it will not passively learn like a memory provider does, so it may serve the
"avoid re-teaching facts" goal far better than the "continuity of working style" goal. And
its primary lives in **AdvenaUAT, a sensitive environment**, so which branch/clone a lab/test
harness is allowed to consume needs deliberate design.

### 2. Licensing is a first-class evaluation criterion, not a footnote

Chris flagged AGPL exposure. Verified at source: **Honcho is AGPL-3.0**, with a managed
cloud service at `api.honcho.dev` and **no dual/commercial license offered**. This creates
a genuine fork, and the two horns point in opposite directions:

- **Self-host** → AGPL copyleft. Self-hosting as part of a networked application carries an
  obligation to release that application's source under AGPL. The danger zone Chris named
  — embedding or linking Honcho into the Trapezia stack such that the combined work looks
  derivative — is real, and is why AGPL is widely treated as high-risk for closed-source
  SaaS.
- **Managed cloud** → sidesteps the copyleft obligation (the license binds the OSS code,
  not use of the SaaS), **but** routes Trapezia conversation data and user-modeling to a
  third party. Honcho persists conversations after each turn.

Note how cleanly this maps onto Trapezia's existing sensitive-data boundary: the
licensing-safe path is the data-boundary-risky one, and vice versa. Any Honcho
recommendation must resolve this explicitly, and any use must stay inside the
lab/test-only constraint.

**This project does not settle the legal question** — it surfaces it with enough
specificity for Chris to get a real answer if the recommendation depends on it. I am not
a lawyer and will not present a legal conclusion as if I were.

## Out of scope (explicit)

- **Deploying or smoke-testing Honcho live.** Paper evaluation only, per Chris. A live
  stand-up needs a Honcho account and would turn a decision phase into an ops phase.
- **Reading, syncing, or touching sensitive environments** — advenauat, ariauat,
  salus-family, oriondev, production. Hard constraint.
- **Mutating live HermesLab / hermestest / OrionLab memory state** during the evaluation.
- **Rendering a legal opinion on AGPL.** Surface the risk precisely; don't adjudicate it.
- **Building the bi-directional `memory-sync` tool** — dropped at G0 round 2 (see Scope).
  Roadmap `#128`'s line item is superseded, not delivered, and must be updated to say so.
- Re-litigating Phase 6's evaluate-then-maybe-build framing.

## Completed as a precondition (was previously listed out of scope)

- **`multi-harness-poc` → `master` merge.** Chris directed this be done *before* Phase 6
  proceeds. Done 2026-07-25: clean `git merge --ff-only`, 8 commits, `cf7fe56..80e1216`,
  pushed; **CI green** (run `30171008308`). `master` and `multi-harness-poc` are in sync.

## Success looks like

Chris has a clear, evidence-backed recommendation among the real options — build the
bi-directional `memory-sync`, adopt a layered external provider, do neither, or a bounded
combination — assessed against the two primary goals (continuity, shared substrate), the
sustained-parallel-operation driver, the corruption-safety constraint, the lab/test-only
constraint, and the licensing exposure. The decision is recorded under
`docs/superhuman/notes/` and the `multi-harness-poc` memory is updated. If "build", the
tool exists, is tested, enforces its constraints by construction, and is pushed CI-green.
If "don't build", that is an equally successful outcome, with reasoning durable enough
that the question doesn't get silently re-opened.

## Open questions for Phase 1 (requirements)

1. **Can "layered" and "non-AGPL" both be satisfied today?** See extension 1b. On OpenClaw,
   Honcho layers but is AGPL; Mem0 is Apache-2.0 but replaces the memory slot. Options:
   pick a horn, wait for OpenClaw's multi-slot architecture (#60572), or step outside the
   provider category. This is now the single most decision-relevant question.
2. **How much does the wiki actually cover?** It is curated knowledge, not passive capture.
   Which of the four goals does it genuinely serve, and which does it leave on the table?
   Would a wiki layer *plus* each harness's existing local memory be sufficient without any
   external provider at all?
3. **What does "diverge by product" actually require?** If OpenClaw keeps Salus and Hermes
   takes Trapezia-Insure/Aria, how much memory genuinely needs to be *shared* versus
   deliberately kept *separate*? Shared-everything may be the wrong target, and a smaller
   shared surface makes cheaper options viable.
4. **What is the real signal-to-noise of harness memory?** *(Framing corrected by Chris —
   the earlier reading was unfair.)* OrionLab's `workspace/memory/` is 40 dated files
   (~220 KB) of session transcripts that look like noise — but **Lab is a scratch
   environment, so that is expected and not a fair sample.** A comparison against a *product*
   environment (salus-family, advenauat) would be far more telling, yet those are sensitive
   and out of bounds. Phase 1 must find an honest way to assess this without reading a
   sensitive env.
5. **How is lab/test-only enforced by construction** rather than by convention? The wiki's
   gitignore-at-source pattern is a proven precedent worth reusing.
6. **Self-host vs managed, if an external provider is recommended** — which horn of the
   AGPL / data-boundary fork, and what evidence settles it? Note `holographic` sidesteps the
   fork entirely by being local, at the cost of being Hermes-only.
7. **What is the honest read on Hermes' longevity**, and what evidence would change it?
   Note that "keep both, diverge by product" would make Hermes durable by decision rather
   than by external bet.
