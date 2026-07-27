# Research findings — cross-harness memory options

**Created:** 2026-07-25 (Phase 2, pre-DESIGN)
**Method:** three parallel read-only research dispatches (options A / B / C). All load-bearing
claims verified at source per NFR-3; confidence and unconfirmed items flagged throughout.
**Constraints honored:** NFR-1 (no sensitive-env data read), NFR-2 (no live memory state mutated),
read-only throughout — no writes, commits, or pushes anywhere.

---

## Option A — external layered provider

### Provider matrix

| Provider | What it is | License (verified at source) | Egress posture | OpenClaw support | Layers or replaces? |
|---|---|---|---|---|---|
| **ByteRover** | Hybrid — local `brv` CLI, optional cloud sync | **Elastic License 2.0** — source-available, non-copyleft, bans offering as a hosted service | Local-first; `BRV_API_KEY` optional | Yes (ClawHub `@byterover/byterover`) | **Layers** — uses `plugins.slots.contextEngine`, not `memory`; `ownsCompaction: false` |
| **Hindsight** | Cloud / local-embedded / local-external | **MIT** (vectorize-io/hindsight) | Cloud mode → `api.hindsight.vectorize.io`; local modes keep data in-house | Yes | **Replaces** — vendor docs: "takes the exclusive memory slot, replacing the default MEMORY.md and daily notes system" |
| **Holographic** | Local SQLite fact store — native Hermes in-tree code | **MIT** (Hermes repo license) | **Zero third-party egress** | No — Hermes-only in-tree plugin | n/a |
| **Honcho** | Honcho Cloud or self-hosted | **AGPL-3.0** ⚠️ copyleft | Cloud → `app.honcho.dev`; self-host keeps in-house | Yes | **Layers**, via a narrower mechanism than assumed — see note below |
| **Mem0** | Platform / self-hosted / in-process OSS | **Apache-2.0** | Platform → `api.mem0.ai`; self-host local | Yes | **Replaces** — requires `plugins.slots.memory: "openclaw-mem0"` |
| **OpenViking** | Self-hosted context DB (Volcengine) | **AGPLv3** ⚠️ copyleft (CLI/examples Apache-2.0) | Self-hosted by design | Yes | **Layers** — `contextEngine` slot |
| **RetainDB** | Cloud memory API | Dual: Apache-2.0 (local/sdk/mcp) + **BSL 1.1** (server) | Cloud `api.retaindb.com`, needs API key | **None found** | n/a |
| **Supermemory** | Hosted or self-hosted | **MIT** | Hosted → `api.supermemory.ai`; self-host local | Yes | **Replaces** (high confidence, not source-quoted) |

### The `contextEngine` vs `memory` distinction — the key structural finding

OpenClaw has **two separate plugin slot families**. `plugins.slots.memory` is exclusive — one
provider owns the memory runtime. `plugins.slots.contextEngine` is a *different* slot, and
OpenClaw's own docs state the two "can work together". Providers that layer do so by occupying
`contextEngine`, not by cooperating within `memory`.

**Honcho's "coexistence" is a narrower trick than the docs imply.** Per the raw text of OpenClaw
issue #60572, enabling Honcho as the memory slot owner *does* displace `memory-core`. The
documented coexistence works only if you **never set `plugins.slots.memory` to Honcho at all** —
Honcho registers via `registerMemoryPromptSection()` rather than the full
`registerMemoryCapability({runtime})`, so its tool surface is slot-independent and rides alongside
`memory-core`. Mem0 has no equivalent escape hatch.

### OpenClaw multi-slot memory (issue #60572) — status

**Open, unmerged, not landed** as of v2026.6.11. Filed 2026-04-03, last reviewed 2026-07-06. The
project's own review bot cites `src/config/types.plugins.ts:42` (`memory?: string`) and
`src/plugins/memory-runtime.ts:10` (resolves at most one memory plugin) as evidence the slot is
still an exclusive scalar. Candidate PR **#88504** implements `memory.recall` / `memory.capture` /
`memory.compaction` / `memory.userModel` sub-slots and explicitly closes the issue, but is
unmerged and awaiting a maintainer product decision. **If it lands**, non-Honcho providers would
be able to layer — the proposal explicitly names `memory.userModel: openclaw-honcho` coexisting
with `memory.recall: memory-core`, and lists Mem0 as a candidate too.

### FR-4 answer: is there a provider that is non-copyleft AND layers AND works on both harnesses?

**Yes — ByteRover**, and it is the only one.

- Non-copyleft: Elastic License 2.0. **Caveat worth stating plainly:** ELv2 is *not* OSI
  open-source either — it prohibits offering the software as a hosted/managed service. It is a
  third category, not a clean permissive win. Whether that restriction bites Trapezia depends on
  whether Trapezia would ever resell it as a service.
- Layers: `contextEngine` slot, merged core interface (OpenClaw PR #50848), live ClawHub plugin.
- Both harnesses: in Hermes' in-box set **and** a shipped OpenClaw plugin.

Every other candidate fails at least one leg: Honcho and OpenViking layer but are AGPL; Hindsight,
Mem0 and Supermemory are permissively licensed but replace the memory slot.

---

## Option B — local provider (`holographic`)

- **What it is:** Hermes `MemoryProvider` plugin exposing `fact_store` / `fact_feedback`. SQLite
  tables (`facts`, `entities`, `fact_entities`) plus an FTS5 virtual table with sync triggers.
  Retrieval blends BM25-style keyword search, Jaccard similarity, trust weighting, temporal decay,
  and HRR compositional retrieval (SHA-256-derived deterministic atoms, so vectors are stable
  across processes).
- **Egress: genuinely zero.** A grep for `http|requests|urllib|socket|api_key|openai|anthropic`
  across all four plugin `.py` files returned **no matches**. Stdlib plus optional NumPy. No API
  key, no account, no network call. Cleanest of the eight on privacy grounds.
- **License:** MIT (inherited from Hermes' repo LICENSE, Nous Research).
- **Capture mode:** primary path is explicit tool calls. `auto_extract` passive extraction defaults
  to **false**. But `on_memory_write()` mirrors Hermes' builtin memory-tool writes into
  `holographic` **unconditionally** — so some passive capture happens by default.

### Disqualifying limitation: single-process by construction

`store.py` implements a process-wide shared connection registry (class-level dict + `threading.RLock`)
explicitly because coexisting providers in one process "raced as independent WAL writers", causing
*"database is locked"*. That registry is **in-memory Python state scoped to one OS process** — it
does nothing for a second process opening the same file, which gets a raw `sqlite3.connect()` with
only native file locking and a 10s busy timeout. Worse, `apply_wal_with_fallback()` silently drops
WAL for `DELETE` journal mode on NFS/SMB/FUSE paths — i.e. exactly the shared-volume arrangement
you would need to share the file, making contention worse.

There is also **no OpenClaw equivalent**: the plugin wrapper is hard-coupled to Hermes internals
(`agent.memory_provider.MemoryProvider`, `hermes_cli.config`, `hermes_constants`). The three engine
files are Hermes-independent and technically vendorable, but an OpenClaw-side wrapper would have to
be built from scratch. OpenClaw's own builtin memory is a separate, incompatible implementation
(per-agent SQLite at `~/.openclaw/agents/<id>/agent/openclaw-agent.sqlite`).

**Verdict: fundamentally single-harness today.** Sharing it means real engineering, against the
grain of its own design.

---

## Option C — wiki as shared layer

- **Structure:** 193 tracked files, 1.8 MB under `users/`, 14 domains. Genuinely curated — page
  template enforces `Type | Domain | Tags | Sources | Last updated` plus
  `Summary / Key Claims / Connections / Contradictions / Notes`. `index.md` is script-rebuilt,
  `log.md` is an append-only operational trail.

### The boundary claim is FALSE — verdict: **BY CONVENTION, weaker than claimed**

SKILL.md states the clone is *"financial- and medical-free by construction"*. It is not.

- The `.gitignore` does correctly exclude `users/*/wiki/medical/`, `users/*/wiki/financial/`,
  `users/*/raw/`, `users/*/inbox/`, and `git check-ignore -v` confirms the patterns are live.
- **But the bare repo at `/opt/trapezia/git/trapezia-wiki-vault.git/hooks/` contains only
  `*.sample` files — no active `pre-receive` or `update` hook.** Enforcement is entirely
  client-side. `git add -f` would commit and push cleanly, propagating to every `env/*` clone.
- No such path was ever added in history (`git log --all --diff-filter=A`), so nothing has leaked —
  the gap is latent, not realized.

Spun out as a separate tracked remediation task; see the G6 entry in `SUPERHUMAN.md`.

### Topology — cross-tier by construction, which FR-14 now disqualifies

One bare repo, branches `main`, `env/advenauat`, `env/ariauat`, `env/orionlab`, `env/oriontest`,
`env/salus-family`. **No `env/hermeslab` branch exists.** Branches have already **diverged** rather
than staying unified — `git diff --stat env/advenauat env/orionlab` shows 182 files changed
(2,469 insertions / 11,547 deletions). A single origin spanning lab, test, and sensitive-tier
environments is exactly the vertical topology FR-14 forbids.

### Harness access

- **orionlab (OpenClaw):** git 2.39.5; already has a live clone at `/opt/openclaw-workspace/wiki`
  (`env/orionlab`) and its own native `wiki` skill with a `phi_screen.py` PHI-screening script.
  Separately, OpenClaw ships a native `memory-wiki` plugin — a *different*, non-git compiled-vault
  memory subsystem. **OpenClaw already runs two wiki-like systems.**
- **hermeslab (Hermes):** git 2.47.3; has `code-wiki` and `llm-wiki` skills, but `WIKI_PATH` is
  unset and `~/wiki` does not exist. No advena-wiki clone or skill. Integrating would be net-new
  work that also overlaps its existing `llm-wiki`.

### Goal fitness — assessed uncharitably, as instructed

| Goal | Verdict | Why |
|---|---|---|
| (i) cross-harness continuity of preferences/identity/working style | **Does not serve** | The page schema is built for topical/reference knowledge about the world and the business, not how-to-work-with-Chris facts. Nothing captures interaction style or session identity. |
| (ii) one shared substrate | **Does not serve today** | Branches already diverged; no hermeslab branch; OpenClaw already runs a second native memory-wiki. Adding this makes a third memory concept, not a unification. |
| (iii) avoid re-teaching env facts | **Partially serves — best fit of the four** | `dev`/`engineering` domains hold real infra-reference pages. But it is manually curated prose an agent must remember to write, not a queryable registry. |
| (iv) evaluation fairness | **Does not serve — actively cuts against it** | OpenClaw's branch is populated and backed by two working systems; Hermes starts from zero. Wiring this in now would hand OpenClaw a large pre-existing advantage in the very comparison the parallel run exists to make. |

---

## Confidence and unconfirmed items

**Verified at source:** all eight upstream LICENSE files fetched raw; Hermes plugin manifests and
source read live on the running container; OpenClaw issue #60572 body, comments and metadata pulled
via `gh api` (not paraphrase); PRs #50848 / #88504 merge status checked directly; `holographic`
egress-free claim confirmed by exhaustive grep; wiki `.gitignore` behavior confirmed via
`git check-ignore -v`; bare-repo hooks directory listed directly; branch divergence measured with
`git diff --stat` (filenames and counts only).

**Not independently confirmed — flagged rather than smoothed:**
- ByteRover cloud-tier pricing (README shows the key is optional but omits cost).
- Whether RetainDB's `RETAINDB_BASE_URL` can actually be pointed at a self-hosted server *from the
  Hermes plugin specifically*.
- Supermemory's exact OpenClaw slot mechanism — one secondary source says "memory" slot; no primary
  doc quote obtained. Treat as high-confidence-but-not-source-quoted, unlike Mem0's direct quote.
- The original `holographic` upstream PR #2351's own license terms (only the repo-level MIT LICENSE
  and an in-source attribution comment were verified).
- That `env/ariauat` and `env/salus-family` are inactive — inferred from a shared older commit hash
  only; their contents were deliberately **not** read, per NFR-1.
- Third-party ClawHub local-memory plugins (Memoria, MemClaw, Memori et al.) — web-summary level
  only, source not inspected. Noted because a daemon-fronted design could in principle solve the
  cross-process problem raw file-sharing cannot.
