# HermesLab Phase 0 — Findings & Kill-Question Answers

- **Status:** In progress (started 2026-07-20)
- **Plan:** [`2026-07-17-hermeslab-phase0-plumbing.md`](../plans/2026-07-17-hermeslab-phase0-plumbing.md)
- **Spec:** [`2026-07-17-multi-harness-poc-design.md`](../specs/2026-07-17-multi-harness-poc-design.md) §3.3
- **Roadmap:** [OrionAIDev/trapezia-roadmap#128](https://github.com/OrionAIDev/trapezia-roadmap/issues/128)

This document is Phase 0's real deliverable. Each kill-question is answered with **evidence**
(config snippet, log excerpt, or observed behavior), not assertion.

---

## Environment / port allocation

| Item | Value | Verified |
|---|---|---|
| Host | orion-dev (Hetzner CPX32, Ubuntu 24.04), up 16w | 2026-07-20 |
| Container | `hermeslab` (upstream `nousresearch/hermes-agent`, 3.81 GB) — **running** | 2026-07-20 |
| Gateway port | **8642** — FREE, allocated, mapped. *Not serving yet:* `No messaging platforms enabled` until Discord is configured | 2026-07-20 |
| Dashboard port | **9119** — allocated but **disabled in practice**: Hermes refuses to bind a non-loopback dashboard with no auth provider (good default). Access via SSH/Tailscale tunnel, or configure `dashboard.basic_auth`. | 2026-07-20 |
| State dir | `/opt/hermeslab/data` → container `/opt/data` (must be **uid 10000**, see F-8) | 2026-07-20 |
| Secrets | `/opt/orion/.env.hermeslab` (chmod 600 root) — `GOOGLE_API_KEY`, `GEMINI_API_KEY` set; `DISCORD_TOKEN` **placeholder pending Chris** | 2026-07-20 |
| Capability venv | `/opt/hermeslab/data/venvs/policy-check` (isolated from Hermes' own venv; persists in the mounted volume across container recreation) | 2026-07-20 |
| Model | `gemini/gemini-2.5-flash`, provider `gemini`, `model.base_url` unset | 2026-07-20 |
| Tracker | **Untracked by design** — no `deployment-tracker` registration during the POC | n/a |

⚠️ **Operational caution:** every stack in `/opt/orion` shares one docker-compose project name, so
`docker compose -f docker-compose-hermeslab.yml` reports the other envs as *orphans*. **Never pass
`--remove-orphans`** there — it would tear down orionlab/oriontest/ariauat/advenauat/salus.

Note: the host-systemd MCP series occupies the 84xx range (next free 8460). Hermes' 8642/9119
sit outside that range, so no renumbering was needed.

---

## Pre-flight findings (2026-07-20) — corrections to prior assumptions

These were discovered while verifying Task 0 prerequisites and **materially changed the plan**.

### F-1. `/root/.env` does not hold the Anthropic/Google keys (global CLAUDE.md is stale)

`/root/.env` contains `GROQ_API_KEY`, `ORIONDEV_OPENROUTER_API_KEY`, `PROTONMAIL_BRIDGE_PASSWORD`
— **no** `ANTHROPIC_API_KEY` or `GOOGLE_API_KEY`. The model keys live in the **per-env** files:
`/opt/orion/.env.orionlab` and `.env.oriontest` carry `GOOGLE_API_KEY` (plus `OPENROUTER_API_KEY`,
`GROQ_API_KEY`, `DISCORD_TOKEN`, M365/OneDrive secrets, `TRAPEZIA_USER_ID`).

*Action:* the global CLAUDE.md "Key Server Paths" row for `/root/.env` should be corrected.

### F-2. There is no active `ANTHROPIC_API_KEY` anywhere — and none is needed

Only stale `.bak-*` env files still contain one. This is **correct by design**:
`llm/client.py::_make_anthropic_provider` raises unconditionally —

> `anthropic/* provider path is deprecated per FR-7.5`

Trapezia moved off the direct Anthropic API to the **Claude Max subscription via `claude-cli`**.
The live provider registry is `{anthropic → raises, claude-cli, google, stub}`.

### F-3. ⚠️ OrionLab's deployed policy-check currently runs on the **stub** provider

OrionLab's `openclaw.json` registers the MCP server with **only** `TRAPEZIA_PCC_STATE_DIR`:

```json
"mcp": { "servers": { "trapezia-commercial-policy-check": {
  "command": "python",
  "args": ["-m", "trapezia_commercial_policy_check.mcp_server"],
  "env": { "TRAPEZIA_PCC_STATE_DIR": "/opt/trapezia/data/trapezia-commercial-policy-check" }
}}}
```

So `Settings` defaults apply: `llm_primary_model="claude-sonnet-latest"`,
`llm_fallback_model="gemini-2.5-pro"`. Per `_provider_for()`, a model id **with no `/`** resolves
to the **stub** provider (the deliberate hermetic-CI default, FR-7.4). Both defaults are bare
names — therefore **both primary and fallback resolve to the stub**, and OrionLab's policy-check
returns canned output rather than real LLM analysis.

A real provider is constructed only for an explicit `"<provider>/<model>"` id with provider in
`{claude-cli, google}` — e.g. `google/gemini-2.5-pro`.

*Consequence for Phase 0:* wiring HermesLab identically would make the "end-to-end policy check"
exit criterion **hollow** (plumbing green, analysis fake). Hence the two-pass decision below.

*Open item (outside Phase 0 scope):* whether OrionLab running on the stub is intentional
(Lab-tier cost control) or an unnoticed default. Flagged to Chris.

### F-4. The stdio MCP contract is confirmed (de-risks Task 4)

The OrionLab registration above confirms the `command` / `args` / `env` stdio shape, matching the
predicted Hermes equivalent. The launch command is
`python -m trapezia_commercial_policy_check.mcp_server`; the FastMCP surface is
`trapezia-commercial-policy-check` (server surface `v1`, engine v0.2.0) exposing
`health`, `run_policy_check`, `get_run_status`, `get_run_report`.

### F-5. Hermes is far more mature than the spec assumed (image probed 2026-07-20)

The image (`nousresearch/hermes-agent:latest`, 3.81 GB, **built 27 minutes before pull**) is not a
sleepy v0.2.x:

- **Config schema version 33.** First start auto-migrates `0 → 33` and rewrites `config.yaml`,
  keeping a timestamped backup. The written config stores **only non-defaults** (6.7 KB vs the
  78.9 KB pre-migration backup) — which is why documented keys appear "missing" (see F-7).
- **73 bundled skills** are synced into `~/.hermes/skills/` on first run (`claude-code`, `codex`,
  `computer-use`, `arxiv`, …). ⚠️ Directly relevant to the Discord **100-slash-command cap**:
  we start ~73 commands deep before adding any Trapezia skill.
- Default model is `anthropic/claude-opus-4.6` with `provider: auto` and
  `base_url: https://openrouter.ai/api/v1` — i.e. Claude **via OpenRouter** by default.
- Rich subcommand surface: `chat, model, moa, fallback, secrets, gateway, proxy, lsp, setup,
  slack, send, auth, cron, webhook, portal, kanban, hooks, doctor, security, backup, checkpoints,
  config, console, skills, bundles, plugins, curator, memory-graph, memory, tools, computer-use,
  mcp, sessions, acp, dashboard, serve, …`
- `platform` entries for **`teams`** and **`google_chat`** already exist (they warn about unknown
  toolsets until enabled) — encouraging for the Phase 3 Teams decision gate.
- The container runs as **uid 10000**, and `/opt/data` is created `drwx------ 10000:10000`.
  Phase 2's ro-mount/immutability design must account for this non-root uid.

### F-6. ✅ MCP registration schema RESOLVED — `config.yaml` → `mcp_servers.<name>`

This closes the plan's bounded discovery step for Task 4. Evidence is Hermes' own **built-in
OpenClaw→Hermes migration** (`/opt/hermes/optional-skills/migration/openclaw-migration/scripts/openclaw_to_hermes.py`),
which maps OpenClaw `mcp.servers.<name>` → Hermes `config.yaml` `mcp_servers.<name>`, carrying
**stdio** fields `command`, `args`, `env`, `cwd` (HTTP/SSE transport is also handled).

So the HermesLab registration is:

```yaml
mcp_servers:
  trapezia-commercial-policy-check:
    command: python
    args: ["-m", "trapezia_commercial_policy_check.mcp_server"]
    env:
      TRAPEZIA_PCC_STATE_DIR: /opt/data/trapezia-commercial-policy-check
      # Pass B (real provider) adds:
      # TRAPEZIA_PCC_LLM_PRIMARY_MODEL: google/gemini-2.5-pro
```

Two notable corollaries:
- **`hermes mcp` (the CLI subcommand) is broken in this image** — it exits with
  `Error: typer is required. Install with 'pip install mcp[cli]'`. Registration must be done by
  editing config (or via `hermes config set`), not the `mcp` subcommand.
- There is also a **`mcp.json`** surface (GUI editor; supports `enabled: false`) listed among
  **"distribution-owned paths (SOUL.md, mcp.json, skills/, cron/)"** — a built-in ownership concept
  worth exploiting in Phase 2.

### F-7. 🎯 Hermes has native skill drift-detection and repair (upgrade to the Phase 2 thesis)

`hermes skills` exposes far more than the docs suggested:
`browse, search, install, inspect, list, check, update, **audit**, uninstall, **reset**,
**list-modified**, **diff**, opt-out, opt-in, **repair-official**, publish, snapshot, tap, config`.

- `skills list-modified` — lists bundled skills the user/agent has edited
- `skills diff` — shows how a local copy differs from stock
- `skills repair-official` — restores official skills from repo source
- `skills audit` — re-scans installed skills; `hermes security` runs an **OSV.dev supply-chain
  audit over venv, plugins, and MCP servers**

**Implication:** the spec's corruption-resistance plan assumed filesystem ro-mount was the *only*
lever. Hermes natively tracks official-vs-modified and can restore. Phase 2 should therefore layer
**ro-mount (prevention) + `list-modified`/`repair-official` (detection & recovery)**, which is a
stronger and more idiomatic story than ro-mount alone.

Caveat: the documented `skills.write_approval` / `skills.guard_agent_created` keys are **not
present** in the generated `config.yaml` (its `skills` block contains only
`creation_nudge_interval: 15`). Because the file stores only non-defaults, this does *not* prove
they are gone — KQ-1 must verify by explicitly setting them via `hermes config set` and observing
behavior.

### F-8. ⚠️ Capability artifacts must be owned by **uid 10000**, not root

Hermes services run as **uid 10000**; `docker exec` lands you as **root**. Anything created via
`docker exec` (venvs, state dirs) is root-owned and the service then cannot use it. Symptom: the
MCP server crashed at *import* time with

```
PermissionError: [Errno 13] Permission denied: '/opt/data/trapezia-commercial-policy-check/originals'
```

which surfaced only as an opaque Hermes warning:
`initial connection failed … unhandled errors in a TaskGroup (1 sub-exception)` →
`failed initial connection after 3 attempts, parking until a reconnect is requested`.
The real cause was in `/opt/data/logs/mcp-stderr.log`, not the agent log.

**Fix:** `chown -R 10000:10000` the capability venv and state dir. **Phase 2 must bake this into
the overlay image / deploy step**, and the ro-mount design must account for the non-root uid.

*Debugging note for the runbook:* when an MCP server "fails to connect" in Hermes, read
`/opt/data/logs/mcp-stderr.log` first — the agent-level error is uninformative.

### F-9. ✅ RESOLVED: MCP tools surface via the gateway/Discord path (not the one-shot CLI)

The one-shot CLI (`hermes -z`) does **not** receive MCP tools — but the **gateway/Discord path
does**, which is the actual product surface. Hypothesis (a) was correct.

**Evidence (2026-07-23, live Discord):** Chris messaged the bot
`use the trapezia-commercial-policy-check health tool and paste its raw JSON result`, and HermesLab
replied with the exact tool output:

```json
{ "status": "ok", "engine_version": "0.2.0", "schema_version": "2026.06.28-stage2E",
  "spec_version": "2026.05.18-stage1-corpus",
  "models": { "primary": "claude-sonnet-latest", "fallback": "gemini-2.5-pro" } }
```

Gateway log signature confirms a real tool call — the policy-check turn logged **`api_calls=2`**
(one round-trip to choose the tool, one to format the result), vs `api_calls=1` for plain chat:

```
inbound message: … msg='use the trapezia-commercial-policy-check health tool …'
response ready: … time=4.0s api_calls=2 response=240 chars
```

**Takeaway for e2e (KQ-5):** drive the **gateway** path (Discord confirmed; the OpenAI-compatible
gateway API on 8642 is the candidate for a headless portable e2e), **not** the one-shot `hermes -z`
CLI. State registration ≠ tool exposure is mode-dependent — a real trap for anyone testing via `-z`.

### Decisions taken (Chris, 2026-07-20)

| # | Decision |
|---|---|
| D-1 | **Phase 0 e2e = two passes:** Pass A on the stub (proves plumbing, zero cost), then Pass B with `TRAPEZIA_PCC_LLM_PRIMARY_MODEL=google/gemini-2.5-pro` (real analysis). The A-vs-B report diff is the evidence the real path works. |
| D-2 | **HermesLab's own agent model = Google/Gemini**, using the existing `GOOGLE_API_KEY`. No new secret provisioned; direct-Anthropic is moot per F-2. |
| D-3 | **Discord bot token** is written to `/opt/orion/.env.hermeslab` by Chris directly on the server. It never enters the session transcript or any repo (Rule 7). |

---

## Kill-question answers

### KQ-1 — Self-learning gating

> Does `skills.write_approval: true` stage all `skill_manage` writes to `~/.hermes/pending/skills/`,
> reviewable via `/skills pending|diff|approve|reject`? Does `guard_agent_created` behave as a
> scanner only?

**Documented expectation (from Hermes docs, to be verified on the live build):**
`skills.write_approval: false` = write freely (default); `true` = stage instead of commit, under
`~/.hermes/pending/skills/`, reviewed with `/skills pending`, `/skills diff <id>`,
`/skills approve <id>`, `/skills reject <id>`. `skills.guard_agent_created` is documented as
"a content scanner (dangerous-pattern heuristics), not an approval gate — the two are independent."

**Live verification:** _pending_

**Answer:** _pending_

---

### KQ-2 — Model providers & fallback chains

> Is direct Anthropic API supported, with fallback chains equivalent to Haiku→Sonnet→Groq?

**Reframed per F-2:** direct-Anthropic is deprecated on the Trapezia side, so the useful question
is *does Hermes support a working provider + fallback chain at all*, evidenced with Google/Gemini —
plus, separately, whether an `anthropic` provider slot exists for future use.

**Documented (Hermes config docs):** providers include `anthropic`, `openrouter`, `nous`, `openai`,
`codex`, `gemini`, `deepseek`, `xai`, `minimax`, others. Every model slot takes `provider` / `model`
/ `base_url`; auxiliary tasks support an explicit `fallback_chain`. Model selection is
**instance-global** — see KQ-related note in OQ-3 below.

**Live verification (2026-07-20): ✅ provider path works.** Configured
`model.default = gemini/gemini-2.5-flash`, `model.provider = gemini`, and unset the default
`model.base_url` (which otherwise routes Claude via OpenRouter). Set both `GOOGLE_API_KEY` and
`GEMINI_API_KEY` (Hermes' source references both). A CLI agent run then produced a real,
coherent LLM response — proving the model path is live end-to-end.

`hermes fallback list | add | remove` exists as a first-class fallback-chain surface (not yet
exercised).

**Answer (partial):** Hermes supports a working provider + fallback-chain mechanism; verified
concretely with Google/Gemini. An `anthropic` provider slot exists for future use, though
Trapezia's own capability layer has deprecated the direct-Anthropic path (F-2). **Outstanding:**
exercise `hermes fallback add` and force a primary failure to observe failover.

---

### KQ-3 — Identity mapping (Discord user → stable identity)

> How does Hermes map a Discord user to a stable identity we can translate to capability-layer
> identity (the `X-Salus-Acting-As` analog for future PHI work)?

Not needed for the insure domain, but the mechanism must exist for later PHI capabilities.

**Live verification:** _pending_

**Answer:** _pending_

---

### KQ-4 — Memory / data capture

> Does Hermes' persistent memory auto-capture conversation content, and can it be gated
> (`memory.write_approval`)? Determines the PHI posture for any future non-insure capability.

Hermes' `/opt/data/memories/` is the persistent memory store.

**Live verification:** _pending_

**Answer:** _pending_

---

### KQ-5 — Programmatic message-injection surface

> Does Hermes' interactive CLI or gateway API drive the *same* agent loop / skill dispatch / tool
> calls as a Discord message? Determines whether e2e needs a special source build (as OpenClaw
> needed `openclaw-qa`) or can drive a CLI/API channel.

Caveat to carry: Hermes registers skills as Discord **slash commands**, so slash-command dispatch
(autocomplete, the 100-command cap) is not covered by a CLI-channel test — plan a one-time manual
Discord verification per promotion regardless of the answer. ⚠️ Sharpened by F-5: **73 bundled
skills ship by default**, so the 100-command cap is a live constraint, not theoretical.

**Live verification (2026-07-20): a CLI injection surface exists and drives a real agent loop.**
`hermes -z "<prompt>"` runs a one-shot agent turn (note: the flag is `-z`, **not** `-p`) and
returned a genuine Gemini-backed response. Additional candidate surfaces not yet tested:
`hermes chat` (interactive), `hermes send`, `hermes serve`, `hermes acp`, and the gateway's
OpenAI-compatible API on 8642.

**Answer (2026-07-23): the gateway/Discord path drives the full loop *including* MCP tools; the
one-shot CLI does not.** Resolved via F-9 — a live Discord message invoked the policy-check `health`
MCP tool end-to-end (`api_calls=2` signature, raw JSON returned). So:

- **e2e must drive the gateway path, not `hermes -z`.** Discord is proven. The next step is to
  confirm the **OpenAI-compatible gateway API on 8642** drives the same agent+MCP loop headlessly —
  if it does, Phase 2's portable e2e needs **no special source build** (contrast OpenClaw, which
  needed `openclaw-qa`). This is the single most important remaining KQ-5 sub-task.
- **Discord slash-command caveat stands:** skills register as slash commands (69 seen under a
  single `/skill` autocomplete command — see below), so a one-time manual Discord check per
  promotion is still warranted.

**Bonus finding:** Discord skills register as autocomplete options under a **single `/skill`
command** (`Registered /skill command with 69 skill(s) via autocomplete`), not 69 separate
commands. This substantially **de-risks the 100-slash-command cap** concern from F-5 — the cap is
on top-level commands, and Hermes collapses skills under one.

---

## Exit criteria (spec §3.5)

- [x] **Pass A (stub) — MET 2026-07-23.** A Discord message drove HermesLab → Gemini agent → the
      `trapezia-commercial-policy-check` MCP tool (`health`) → raw JSON back to Discord, evidenced by
      the `api_calls=2` gateway signature (F-9). This proves the full harness-independent chain: an
      unmodified Trapezia FastMCP capability invoked from a *different* harness with config only.
- [ ] **Pass B (real `google/gemini-2.5-pro`)** — run `run_policy_check` on a synthetic fixture with
      `TRAPEZIA_PCC_LLM_PRIMARY_MODEL=google/gemini-2.5-pro`, diff vs the stub output. *(health does
      not exercise the LLM; Pass B needs `run_policy_check` on a real fixture.)*
- [ ] Kill-questions: **KQ-2 ✅ / KQ-5 ✅** (this doc). **KQ-1, KQ-3, KQ-4** still to verify on the
      live build.
- [ ] Go/no-go for Phase 1 recorded here and summarized on roadmap #128.

### Milestone note

Pass A is the POC's central proof-of-concept: **capability portability across harnesses is real.**
The same `trapezia-commercial-policy-check` server that runs under OpenClaw in OrionLab ran under
Hermes in HermesLab with only a `config.yaml` `mcp_servers` entry + an isolated venv — no capability
code changed. Remaining Phase 0 work (Pass B, KQ-1/3/4) is confirmatory, not thesis-critical.
