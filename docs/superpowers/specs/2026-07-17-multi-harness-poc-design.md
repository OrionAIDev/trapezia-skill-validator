# Multi-Harness POC — HermesLab (Phases 0–1 Design)

- **Status:** Draft for review
- **Date:** 2026-07-17
- **Roadmap:** [OrionAIDev/trapezia-roadmap#128](https://github.com/OrionAIDev/trapezia-roadmap/issues/128) (status pointer)
- **Owning repo (incubation):** `trapezia-skill-validator`, branch `multi-harness-poc` (worktree `~/dev/trapezia-skill-validator-poc`)
- **Scope of this doc:** Phases 0 and 1 only. Phases 2–4 are sketched in the roadmap issue and revisited in later specs.

---

## 1. Problem & goal

Trapezia's runtime capabilities are currently coupled to a single agent harness (OpenClaw). We want them **harness-independent** so different customers and use-cases can run on different harnesses — starting with **Hermes** (Nous Research), then OpenClaw and Claude Code, and later others (e.g. a ChatGPT-side surface).

Two forces drive this:

1. **Portability** — the same capability should run on any harness with only a thin, generated adapter changing, not the capability code.
2. **Corruption-resistance** — Hermes's headline feature is *self-learning* (the agent auto-generates and refines its own skills via `skill_manage`). That is a sales asset for end-user-authored skills, but it must never be able to mutate the official skills Trapezia delivers. Protection must be enforced by the filesystem (read-only mounts / locks), not by agent judgment — consistent with trapezia-disciplines Rule 5 (irreversible/safety-critical paths are always code).

**This experiment must not impact current disciplines, skills, environments, or the OrionLab→OrionTest→UAT promotion ladder.** AriaUAT is untouched. OrionDev is untouched. No PHI goes anywhere near the POC.

### Success framing

Chris's framing: this is **not** a throwaway POC to be measured by a fixed scope. It is the **first phase of a progressive build** that develops into a durable HermesLab (and possibly, later, an OCLab that replaces OrionLab). We therefore optimize for a phased, additive build where each phase produces a real, reusable asset — not a demo.

---

## 2. Architecture thesis

Ports-and-adapters (hexagonal), applied to the Trapezia stack:

- **Capability core (harness-agnostic):** business/domain logic as MCP servers or CLI scripts with stable contracts (versioned APIs, JSON schemas, stable exit codes). `trapezia-commercial-policy-check` is already a pure FastMCP server — the ideal first capability.
- **Harness adapters (thin, per-harness):** a small wrapper per harness (a `SKILL.md` in the harness's format, or an MCP registration) that carries only invocation glue, trigger/description, and guardrail prose. **Generated from a single canonical spec — never hand-maintained per harness.**
- **Governance/security lives in the core, never in adapter prose** — so a weaker or self-modifying harness cannot weaken it.

MCP is the interop substrate all three initial harnesses already speak (Hermes: stdio + HTTP with auto-reload; OpenClaw; Claude Code). Shipping capability as MCP + keeping adapters thin is simultaneously the portability answer and the corruption-resistance answer.

### First capability: `trapezia-commercial-policy-check`

Chosen because it is already a pure FastMCP server (4-tool Phase-1 surface: `health`, `run_policy_check`, `get_run_status`, `get_run_report`), the insure domain is **non-PHI** (sensitive-data boundary not in play), the related Applied-Epic integration is also already MCP, and **AriaUAT stays completely untouched** — HermesLab connects to the *existing* OrionLab policy-check deployment (or a local stdio instance), it does not redeploy the capability.

---

## 3. Phase 0 — HermesLab plumbing

**Goal:** stand up an isolated Hermes instance on orion-dev, connect it to the existing MCP services, run a policy check end-to-end, and answer the kill-questions that determine whether the rest of the build is worth it.

### 3.1 Container & placement

- New container `hermeslab` on **orion-dev** (decision: option A — same host as the MCP services, so connectivity is localhost-simple and it matches the existing per-env container pattern).
- Config/state home: `/opt/hermeslab/` (per-env config/state), credentials in `/opt/orion/.env.hermeslab` (canonical-credentials-per-env policy; no env prefix on var names).
- **Deploy artifacts (compose/env) live in the `orion-compose` repo**, beside the other env stacks — *not* in `trapezia-skill-validator` (artifact-home rule: the validator repo does not own container stacks).
- Own Discord bot token, own Hermes state dir, own model auth. **Never copy auth/state from another instance** (single-use refresh-token hazard — same rule as the OpenClaw Codex incident).
- Port plan: Hermes default gateway port is **8642**; host next-free port is **8460**. Allocate deliberately and record in the server port table.

### 3.2 Connectivity

HermesLab's Hermes MCP client connects to the already-running services on orion-dev:

- Microsoft MCP (orionlab) `8444`, Google MCP (orionlab) `8449`, Applied-Epic MCP `8455–8457`, GTD `8458`.
- `trapezia-commercial-policy-check` — either its stdio server run inside the HermesLab image, or its HTTP surface if deployed as such. (Phase 0 decision point; stdio-in-image is the lower-friction start.)

### 3.3 Kill-questions (the real deliverable of Phase 0)

Answer these on the live build before investing in Phase 1+:

1. **Self-learning gating** — does `skills.write_approval: true` stage all `skill_manage` writes to `~/.hermes/pending/skills/` as documented, reviewable via `/skills pending|diff|approve|reject`? Does `guard_agent_created` behave as a scanner only?
2. **Model providers** — is direct Anthropic API supported, with fallback chains equivalent to Haiku→Sonnet→Groq? (Policy-check itself needs Anthropic + Google; no OpenAI.)
3. **Identity mapping** — how does Hermes map a Discord user → a stable identity we can translate to capability-layer identity (the `X-Salus-Acting-As` analog for future PHI work; not needed for insure, but verify the mechanism exists).
4. **Memory / data capture** — does Hermes's persistent memory auto-capture conversation content, and can it be gated (`memory.write_approval`)? Determines the PHI posture for any future non-insure capability.
5. **Programmatic message-injection surface** — does Hermes's interactive CLI or gateway API drive the *same* agent loop / skill dispatch / tool calls as a Discord message? **This determines whether e2e needs a special source build** (as OpenClaw did with `openclaw-qa`) or whether we can drive a CLI/API channel instead. Note: Hermes registers skills as Discord *slash commands*, so Discord-specific dispatch (autocomplete, the 100-command cap) is not covered by CLI-channel tests — plan a one-time manual Discord verification per promotion.

### 3.4 Lead-time item

Begin **M365 Business tenant + Azure Bot registration** procurement now. It is not needed until Phase 3 (Teams), but it is the long-lead dependency and the Teams evaluation is the project's deciding factor.

### 3.5 Exit criteria

A policy check runs end-to-end from Discord via HermesLab against the existing MCP service, and all five kill-questions have documented answers.

---

## 4. Phase 1 — Canonical spec + per-harness generator

**Goal:** prove the portability thesis — one canonical spec emits working thin wrappers for **Hermes, OpenClaw, and Claude Code**, with Hermes and OpenClaw the priority targets.

### 4.1 Canonical skill-spec

A single manifest per capability (YAML), source of truth for all per-harness adapters. Fields (initial):

- `name`, `description` / trigger phrasing
- `invokes`: the MCP tools (and/or CLI scripts) the wrapper calls, with the transport
- `guardrails`: prose the adapter must carry (e.g. a daemon-down / error-handling instruction)
- `model_tier` hints (Opus / Sonnet / Haiku) where a harness honors them
- adapter-specific overrides where a harness genuinely differs (kept minimal)

### 4.2 Generator

A small generator (in this repo, on this branch) that reads the canonical spec and emits:

- **Hermes** — `SKILL.md` in agentskills.io format for `~/.hermes/skills/`
- **OpenClaw** — ClawHub skill format
- **Claude Code** — `SKILL.md` for `~/.claude/skills/` (the cross-check that generation is not Hermes-shaped)

**Generated-artifact policy:** committed to the repo (inspectable, diffable) **plus a CI regeneration check** that fails if committed output drifts from generator output. (Preferred over build-time-only, consistent with existing CI discipline.)

### 4.3 Validation & incubation

- `trapezia-skill-validator` gains a **canonical-spec linter** (additive; does not change the existing check API that `skill-template` self-test and `trapezia-skill-audit` consume).
- Everything incubates on branch `multi-harness-poc` in a worktree. **Main/`master` and all production consumers are untouched.** Pushing the branch to the shared remote is a feature, not a risk: branch CI and the `sensitive-data-guard` hook apply to the experiment for free.

### 4.4 Deployment of the generated wrappers

- **Hermes wrapper** → live in HermesLab.
- **OpenClaw wrapper** → validated in the *existing* **OrionLab** (normal Lab-tier activity — deploying one generated skill is low-risk and inside existing discipline; **no new OCLab container in this phase**).
- **CC wrapper** → validated on the laptop by dropping it in `~/.claude/skills/` and invoking it (no container).

### 4.5 Phase 1 exit criterion — the graduation decision

At Phase 1 exit, decide **with evidence** whether the canonical-spec generator belongs long-term inside `trapezia-skill-validator` (merge branch → master) or as its own extracted repo (e.g. `trapezia-skill-spec`, carrying history). The worktree deliberately defers this decision. Deciding factors: whether the generator's dependencies (e.g. jinja2, per-harness format knowledge) belong in a package that validator consumers install, and whether the generator has grown into a product tool in its own right.

---

## 5. Known future ripples (out of Phase 0–1 scope, recorded to avoid surprise)

The harness-independence work is additive for the POC but has intended downstream effects that later phases must own:

- **Authoring tools change at Phase 4.** Once a canonical spec is real, the *authoring* layer should stop hand-producing per-harness `SKILL.md`:
  - **`skill-template`** would scaffold a **canonical spec** instead of a raw `SKILL.md`.
  - **`plugin-creator`** (the OpenClaw-runtime conversational builder) would ideally emit canonical specs too, so user-built skills are portable and pass through the same generator.
  This is downstream of the trapezia-disciplines rule changes (MCP-first packaging, delivered-skill immutability, canonical-spec rule) already noted in the roadmap. **No Phase 0–2 work touches either creator.**
- **Install/trust-path consolidation.** `plugin-creator` and `secure-plugin-installer` both implement a staging → security-scan → gated-install flow. The long-term goal is **one** corruption-resistant install/trust path across harnesses, not two. (A separate investigation — spawned 2026-07-17 — is mapping the full skill-authoring toolchain, including whether `OrionAIDev/skill-creator` is a dead repo superseded by `plugin-creator`; its findings feed the Phase 4 refactor decision.)
- **Capability plane + gateway (Phase 4).** Consolidate the MCP *interface* (one gateway endpoint per env with per-client tool grants = the entitlement / paid-add-on mechanism), **not** the deployment into one fat container. Per-capability containers stay separate. The **Salus daemon stays architecturally isolated** (PHI sole-writer) — an MCP facade *behind* the gateway at most, never folded into a shared container with non-PHI capabilities.

---

## 6. Non-goals & guardrails

- No changes to existing environments beyond deploying one generated OpenClaw wrapper to OrionLab.
- No PHI or other sensitive data near HermesLab; insure domain only.
- OrionDev untouched. AriaUAT untouched.
- No `deployment-tracker` registration during the experiment — HermesLab is explicitly *untracked* until the POC graduates.
- Generated per-harness files are never hand-edited; the canonical spec is the only authored surface.
- Delivered wrappers are protected by the filesystem (ro-mount / lock) once Phase 2 lands; Phase 0–1 may run without protection while iterating, but protection is a hard requirement before any UAT/Prod analog.

---

## 7. Open questions

- **OQ-1:** Owning repo for HermesLab deploy artifacts confirmed as `orion-compose`? (Assumed yes.)
- **OQ-2:** policy-check transport into HermesLab — stdio-in-image (start here) vs HTTP surface (needs the capability deployed as an HTTP MCP)?
- **OQ-3:** Does Hermes honor `model_tier` hints, or is model selection purely instance-global config? (Affects canonical-spec field set.)
- **OQ-4:** Exact canonical-spec schema — settled at the start of Phase 1 implementation (candidate for a short schema-design pass before coding the generator).
