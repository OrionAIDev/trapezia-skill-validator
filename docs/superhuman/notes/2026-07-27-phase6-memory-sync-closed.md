# Phase 6 decision — `memory-sync` cancelled and closed

**Date:** 2026-07-27
**Phase:** 6 of the HermesLab multi-harness POC — "`memory-sync` evaluation and decision"
**Decision:** **CANCELLED / CLOSED. Off the table.**
**Decided by:** Chris, 2026-07-27, at the G3 design gate.
**Outcome type:** ABORT (superhuman gate action). Not a deferral, not a "revisit later" —
the line of work is closed.

---

## The decision

Chris reviewed the design options and the adversarial review of them, and closed the
work: *"I do not like any of these results. Consider memory-sync to be
canceled/closed and off-the-table."*

No shared cross-harness memory layer will be built or adopted. The original
OpenClaw→Hermes `memory-sync` tool is not being built, and neither are any of the
alternatives that replaced it during evaluation.

Roadmap `OrionAIDev/trapezia-roadmap#128`'s `memory-sync` line item is **closed, not
delivered**.

## What was evaluated before closing

The phase was chartered as "evaluate + decide, not build". It ran through superhuman
gates G0–G2 and G6, and stopped at G3 when the decision was made. The scope changed
twice during elicitation before landing on four options:

| Option | What it was | Status at close |
|---|---|---|
| **A** | External layered memory provider (non-AGPL preferred) | Never fully adjudicated — see below |
| **B** | Local provider (Hermes `holographic`) | Disqualified on FR-11 (Hermes-only *and* single-process by construction) |
| **C** | Wiki as shared layer (extend `advena-wiki`) | Disqualified on FR-14 (cross-tier topology) and FR-10 (boundary is convention, not construction) |
| **D** | Do nothing | Viable; effectively where the decision landed |

The original bi-directional `memory-sync` tool had already been dropped at G0 round 2,
once research established that both harnesses support *layered* memory providers that
leave each harness's own local memory files untouched — which obtained the desired
outcome without anything writing into OpenClaw's memory, the corruption risk that
motivated dropping it.

## Why this is a clean outcome, not a failed one

The phase was chartered to produce a decision. It produced one. Requirements NFR-5
explicitly made "do nothing" a first-class success outcome scored on the same rubric,
precisely so this result would not be treated as failure.

The evaluation also did real work before stopping: it killed a tool that would have
been actively dangerous to build (writing into a foreign harness's memory files),
and it surfaced two problems that exist independently of memory-sync — see below.

## Findings preserved (independent of this decision)

The research is retained in `docs/superhuman/memory-sync-evaluation/RESEARCH.md`. It
answers questions that will recur, so it should be read before anyone re-opens
anything in this space:

- **Honcho is AGPL-3.0** with a managed cloud and **no dual/commercial license**.
  Self-host carries copyleft exposure; managed sidesteps the license but ships
  conversation content to a third party, persisted every turn.
- **Hermes ships eight in-box memory providers** — `byterover`, `hindsight`,
  `holographic`, `honcho`, `mem0`, `openviking`, `retaindb`, `supermemory` — with
  licenses ranging across AGPL-3.0, Apache-2.0, MIT, BSL 1.1 and Elastic License 2.0.
- **OpenClaw's memory slot is exclusive.** Providers either occupy
  `plugins.slots.memory` (replacing `memory-core`) or `plugins.slots.contextEngine`
  (layering alongside it). Multi-slot memory (issue #60572, PR #88504) is **open and
  unmerged**, so "layered" and "non-copyleft" could not both be satisfied cleanly at
  the time of this decision.
- **`holographic` is genuinely zero-egress** (no network calls, no API key, MIT) but is
  single-process by construction — its own concurrency guard is process-local.

## Carry-forward items (adjudicated by Chris, 2026-07-27)

Two findings surfaced during Phase 6 that are independent of the memory-sync decision.
Chris ruled on both after review; the rulings are recorded here **in place of** this
note's original, more alarmed framing.

### 1. `advena-wiki` "by construction" wording — documentation accuracy only, NOT a risk

**Original finding:** `advena-wiki`'s SKILL.md states the clone is *"financial- and
medical-free by construction (gitignored at the AdvenaUAT source, never pushed)"*. That
wording is inaccurate — the bare repo at
`/opt/trapezia/git/trapezia-wiki-vault.git/hooks/` contains only `*.sample` files, with
no active `pre-receive`/`update` hook, so exclusion is entirely client-side
`.gitignore`. A `git add -f` would commit and push cleanly.

**Chris's ruling (authoritative):** *"advena-wiki is my personal environment. There is
no legal or regulatory danger to storing PII/PHI here on my VPS to which only I have
access."*

**Corrected severity: none.** This note originally framed the gap as a security/
compliance exposure and proposed a server-side `pre-receive` remediation. That framing
was wrong — it assumed a legal/regulatory boundary that does not exist for a personal
environment on a single-tenant VPS with sole access. **No remediation is required**, and
the previously-spun-out remediation task is withdrawn.

What remains is a small documentation-accuracy point: the phrase "by construction"
overstates a client-side convention. The client-side `.gitignore` still functions as
designed (it keeps medical/financial out of the laptop Claude Code clone, which is the
actual intent). Fixing the wording is optional cleanup, not a security fix.

### 2. Only a **scrubbed** `~/.claude/CLAUDE.md` may be copied into a lab-deployed artifact

**Finding:** a rejected design proposed copying environment facts from
`~/.claude/CLAUDE.md` wholesale into a lab-deployed skill. That file contains the full
environment table including advenauat / ariauat / salus-family, salus per-env data-root
paths, per-env credential file locations, the auth/MCP port map, and a real
Discord-ID → user-UUID mapping.

The design waved this off citing the `sensitive-data-guard` PreToolUse hook. That hook
was read directly: it matches credential/secret *shape* patterns plus an **optional**
PHI wordlist that is inert unless `$TRAPEZIA_PHI_WORDLIST` points at an existing file.
It would not catch environment topology or user identifiers.

**Chris's ruling (standing rule going forward):**

> **Only a scrubbed `~/.claude/CLAUDE.md` may be copied into a lab-deployed artifact.**

Wholesale copying is not permitted. Any future "share the env facts across harnesses"
idea must scrub first — and because `sensitive-data-guard` does not catch this class,
the scrub cannot rely on that hook to catch a mistake.

## What this does not change

- Phases 0–5 of the HermesLab POC stand as completed, validated, and pushed.
- The canonical spec generator (`trapezia_skill_spec`) and its three harness emitters
  are unaffected.
- The parallel Hermes/OpenClaw operation itself is unaffected — this decision only says
  their memories stay separate.
- HermesLab and hermestest remain deployed and untouched. No live memory state was read
  or mutated at any point during this phase.

## Artifacts

Retained under `docs/superhuman/memory-sync-evaluation/`:
`VISION.md`, `REQUIREMENTS.md`, `RESEARCH.md`, `DESIGN.md`, `SUPERHUMAN.md`
(full gate/decision audit trail, G0–G3).
