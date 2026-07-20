# HermesLab Phase 0 — Plumbing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. This is an **ops/investigation** plan (remote Docker + live discovery), not a code-TDD plan — "tests" here are verification commands with expected output, and several tasks produce **documented findings** rather than code.

**Goal:** Stand up an isolated `hermeslab` Hermes container on orion-dev, wire it to the existing MCP services, run one `trapezia-commercial-policy-check` end-to-end from Discord, and answer the five kill-questions that gate the rest of the build.

**Architecture:** Ports-and-adapters. HermesLab is a fresh Hermes instance (own Discord bot, own model auth, own state) running the upstream `nousresearch/hermes-agent` image via `gateway run`. The capability core (`trapezia-commercial-policy-check`, a pure FastMCP stdio server) is reached **stdio-in-image** (OQ-2 decision, 2026-07-17). No existing environment changes; AriaUAT/OrionDev untouched; no PHI; not registered in deployment-tracker.

**Tech Stack:** Docker / docker-compose (host `network_mode`), Hermes v0.2.x (`nousresearch/hermes-agent`), FastMCP stdio, orion-dev (Hetzner CPX32, Ubuntu 24.04). Deploy artifacts live in the **`orion-compose`** repo (`~/dev/orion-compose`), **not** in this validator repo.

**Server access:** `ssh root@204.168.222.57` (public) or `ssh root@100.117.27.98` (Tailscale, preferred on VPN).

---

## Guardrails (read before starting — from spec §6 + trapezia-disciplines)

- **Deploy artifacts → `orion-compose` repo only.** Nothing HermesLab-infra goes in `trapezia-skill-validator`.
- **Never copy Hermes auth/state from another instance.** HermesLab gets its own Discord bot token and its own model credentials. (Anthropic/Google use API keys, not single-use OAuth refresh tokens, but the rule stands: independent grants.)
- **No PHI.** Insure domain only. Policy-check is non-PHI.
- **No `deployment-tracker` registration** during the experiment. HermesLab is explicitly untracked.
- **Credential-locality policy:** canonical secrets in `/opt/orion/.env.hermeslab` (chmod 600, root-owned); non-secret config in `/opt/hermeslab/`. No env-name prefixes (`ANTHROPIC_API_KEY`, not `HERMESLAB_ANTHROPIC_API_KEY`).
- **Claude must not create the Discord app or handle the raw bot token as a secret to commit.** Chris creates the Discord application + bot and provides the token; Claude writes it into the server-side `/opt/orion/.env.hermeslab` (a non-repo path) during setup. The `sensitive-data-guard` hook blocks committing secrets in Trapezia repos — never put the token in `orion-compose`.
- **M365 tenant + Azure Bot procurement** (Task 7) is a Chris-owned lead-time item; Claude cannot create accounts.

---

## File & artifact map

**In `orion-compose` (`~/dev/orion-compose`, committed there):**
- Create: `docker-compose-hermeslab.yml` — the HermesLab stack (upstream image, host network, `/opt/hermeslab/data` volume).
- Create: `identity/hermeslab.trapezia-env` — non-secret identity/config, mirroring the existing `identity/<env>.trapezia-env` files.
- Create: `.env.hermeslab.example` — a **placeholder-only** template documenting the required keys (real secrets never committed; they live at `/opt/orion/.env.hermeslab` on the server).

**On orion-dev (server, not version-controlled):**
- `/opt/hermeslab/data/` — Hermes state (`config.yaml`, `.env`, `skills/`, `sessions/`, `memories/`, `logs/`).
- `/opt/orion/.env.hermeslab` — canonical secrets (Discord token, Anthropic/Google keys).

**In this repo (`trapezia-skill-validator-poc`, branch `multi-harness-poc`):**
- Create: `docs/superhuman/notes/2026-07-17-phase0-kill-question-findings.md` — the documented answers to the five kill-questions + port allocation record (Phase 0's real deliverable).

---

### Task 0: Prerequisites & decisions checklist (Chris-owned items surfaced first)

**Files:** none (gating checklist).

- [ ] **Step 1: Confirm the Discord application + bot token (Chris action).** Chris creates a dedicated Discord application + bot for HermesLab (separate from all OpenClaw bots) and provides the bot token out-of-band. Do **not** reuse any existing bot token.

- [x] **Step 2: Confirm model credentials are available on orion-dev.** ✅ **DONE 2026-07-20 — the original assumption was wrong; corrected:**
  - `/root/.env` does **not** hold Anthropic/Google keys (it has GROQ / OpenRouter / Proton). The global CLAUDE.md is stale on this point.
  - `GOOGLE_API_KEY` lives in the **per-env** files (`/opt/orion/.env.orionlab`, `.env.oriontest`) and is visible in the orionlab container.
  - There is **no active `ANTHROPIC_API_KEY`** anywhere (only stale `.bak-*` files), and it is not needed: `_make_anthropic_provider` raises unconditionally (**FR-7.5 deprecation** — Trapezia moved to Claude Max via `claude-cli`). Real providers are `claude-cli/<model>` or `google/<model>`.

Run (on server): `sed -n 's/^\(GOOGLE_API_KEY\|OPENROUTER_API_KEY\|GROQ_API_KEY\)=.*/\1=<set>/p' /opt/orion/.env.orionlab`
Expected: `GOOGLE_API_KEY=<set>` (plus OpenRouter/Groq). **Decision 2026-07-20: HermesLab's own agent model uses Google/Gemini via the existing `GOOGLE_API_KEY` — no new secret provisioned.**

- [ ] **Step 3: Verify the Hermes gateway port 8642 is free on orion-dev, and record the allocation.**

Run (on server): `ss -ltnp | grep -E ':8642|:9119' || echo 'FREE: 8642 and 9119 available'`
Expected: `FREE: 8642 and 9119 available`. If occupied, pick the next free port and record the mapping. Note: the host-systemd MCP series uses 84xx (next free 8460); Hermes' 8642/9119 are separate and preferred if free.

- [ ] **Step 4: Create the findings doc skeleton (records decisions as they are answered).**

Create `docs/superhuman/notes/2026-07-17-phase0-kill-question-findings.md` with headers for the five kill-questions (§3.3 of the spec) + a "Port allocation" section. Commit:

```bash
git add docs/superhuman/notes/2026-07-17-phase0-kill-question-findings.md
git commit -m "docs(poc): Phase 0 kill-question findings skeleton"
```

---

### Task 1: Author HermesLab deploy artifacts in orion-compose

**Files (in `~/dev/orion-compose`):**
- Create: `docker-compose-hermeslab.yml`
- Create: `identity/hermeslab.trapezia-env`
- Create: `.env.hermeslab.example`

- [ ] **Step 1: Write `docker-compose-hermeslab.yml`.**

Model after the existing per-env stacks but use the **upstream Hermes image directly** (no Dockerfile needed at this stage — policy-check is baked in via a small overlay in Task 4, revisit then). Content:

```yaml
services:
  hermeslab:
    image: nousresearch/hermes-agent:latest
    container_name: hermeslab
    restart: unless-stopped
    command: gateway run
    env_file:
      - /opt/orion/.env.hermeslab
    volumes:
      - /opt/hermeslab/data:/opt/data
    ports:
      - "8642:8642"
      - "9119:9119"
    environment:
      - HERMES_DASHBOARD=1
    deploy:
      resources:
        limits:
          memory: 2g
          cpus: "2"
```

Note: `ports:` bridge-maps 8642/9119 (bridge networking, unlike the OpenClaw stacks' `network_mode: host`) so HermesLab is isolated; it reaches the host MCP services via the host gateway IP (confirmed in Task 4). If Task 4 discovery shows the MCP clients need host networking, switch to `network_mode: host` and drop the `ports:` block then.

- [ ] **Step 2: Write `identity/hermeslab.trapezia-env`.**

Mirror the field set of `identity/orionlab.trapezia-env` (inspect it first: `cat ~/dev/orion-compose/identity/orionlab.trapezia-env`). Set the env slug to `hermeslab`, mark it a POC/untracked environment, insure-domain, non-PHI. Do **not** put secrets here.

- [ ] **Step 3: Write `.env.hermeslab.example` (placeholders only).**

```dotenv
# HermesLab canonical secrets — real values live at /opt/orion/.env.hermeslab on orion-dev.
# This example is committed; the real file is NOT. Never commit real tokens (Rule 7).
# Var name matches the existing per-env convention (.env.orionlab uses DISCORD_TOKEN).
DISCORD_TOKEN=<discord-bot-token>
GOOGLE_API_KEY=<google-api-key>
# No ANTHROPIC_API_KEY: direct-Anthropic is deprecated (FR-7.5); HermesLab's agent model
# and the policy-check real run both use Google/Gemini (decision 2026-07-20).
```

- [ ] **Step 4: Commit to orion-compose (switch git identity first).**

```bash
cd ~/dev/orion-compose
gh auth switch --user OrionAIDev   # if a push is needed; commit uses repo's configured author
git add docker-compose-hermeslab.yml identity/hermeslab.trapezia-env .env.hermeslab.example
git commit -m "feat(hermeslab): Phase 0 HermesLab deploy stack (POC, untracked env)"
```

Expected: clean commit; `git status` shows nothing to commit. (Push per Chris's preference — Lab-tier POC artifacts; no promotion gate involved.)

---

### Task 2: Provision server dirs, credentials, and Hermes config on orion-dev

**Files (on server):** `/opt/hermeslab/data/`, `/opt/orion/.env.hermeslab`, `/opt/hermeslab/data/config.yaml`

- [ ] **Step 1: Create the state dir and the secrets file.**

```bash
ssh root@100.117.27.98
mkdir -p /opt/hermeslab/data
touch /opt/orion/.env.hermeslab && chmod 600 /opt/orion/.env.hermeslab
```

- [ ] **Step 2: Populate `/opt/orion/.env.hermeslab`** (split by who holds the secret — decision 2026-07-20):
  - **Claude:** create the file `chmod 600` root-owned, pre-filled with `GOOGLE_API_KEY` (value copied server-side from `/opt/orion/.env.orionlab` — never printed to the transcript) and a placeholder `DISCORD_TOKEN=<paste-token-here>` line.
  - **Chris:** SSH in and replace the `DISCORD_TOKEN` placeholder with the real HermesLab bot token. The token never enters this conversation or any repo (Rule 7).

Verify (names only, values never printed): `sed -n 's/^\(DISCORD_TOKEN\|GOOGLE_API_KEY\)=.*/\1=<set>/p' /opt/orion/.env.hermeslab`
Expected: both `DISCORD_TOKEN=<set>` and `GOOGLE_API_KEY=<set>`, and `grep -c 'paste-token-here' /opt/orion/.env.hermeslab` returns `0`.

- [ ] **Step 3: Pull the image and run the Hermes setup wizard once** to generate `config.yaml`, or hand-write a minimal `config.yaml`. Discovery step (Hermes v0.2.x — confirm the exact wizard flow on the live build):

```bash
docker pull nousresearch/hermes-agent:latest
docker run -it --rm -v /opt/hermeslab/data:/opt/data --env-file /opt/orion/.env.hermeslab \
  nousresearch/hermes-agent setup
```

Expected artifact: `/opt/hermeslab/data/config.yaml` exists. Record the generated model + skills sections verbatim in the findings doc.

- [ ] **Step 4: Configure the model provider = Google/Gemini with a fallback chain, and gate self-learning.** Edit `/opt/hermeslab/data/config.yaml`:
  - Main model: provider `gemini` (Google), e.g. `gemini-2.5-flash` for cost, with a `fallback_chain` to `gemini-2.5-pro` and optionally an OpenRouter/Groq entry. (Confirm the exact main-model + fallback keys on the live build — see kill-Q#2, Task 6; docs reference `model.provider`/`model.default` + `fallback_providers`.)
  - **Note for kill-Q#2:** the spec originally asked whether *direct Anthropic* is supported. That question is now partly moot for Trapezia (FR-7.5 deprecates the direct-Anthropic path in favour of Claude Max via `claude-cli`), so record the answer as: *does Hermes support a working provider + fallback chain at all*, evidenced with Google/Gemini. Note separately whether an `anthropic` provider slot exists for future use.
  - `skills.write_approval: true`
  - `skills.guard_agent_created: true`

Record the exact keys used in the findings doc (they are needed by Phase 2).

---

### Task 3: Bring up HermesLab and verify gateway + Discord connectivity

**Files:** none (deploy + verify).

- [ ] **Step 1: Copy the compose file to the server and start the stack.**

```bash
scp ~/dev/orion-compose/docker-compose-hermeslab.yml root@100.117.27.98:/opt/orion/
ssh root@100.117.27.98 'cd /opt/orion && docker compose -f docker-compose-hermeslab.yml up -d'
```

- [ ] **Step 2: Verify the container is running.**

Run: `ssh root@100.117.27.98 'docker ps --filter name=hermeslab --format "{{.Names}} {{.Status}}"'`
Expected: `hermeslab Up ...` (not `Restarting`).

- [ ] **Step 3: Verify the gateway health endpoint.**

Run: `ssh root@100.117.27.98 'curl -fsS http://localhost:8642/health || curl -fsS http://localhost:8642/v1/models'`
Expected: an HTTP 200 JSON body (health status or model list). If the path differs on this build, discover it from `docker logs hermeslab` and record it.

- [ ] **Step 4: Verify Discord connectivity** — check logs for a successful gateway/Discord login (do **not** rely on the benign "awaiting readiness" line).

Run: `ssh root@100.117.27.98 'docker logs --tail 80 hermeslab'`
Expected: a line indicating Discord connected / bot ready. Then send a plain `ping`-style message in the bot's Discord channel and confirm a reply. Record the result.

---

### Task 4: Wire `trapezia-commercial-policy-check` via stdio-in-image

**Files (on server / possibly a small overlay in orion-compose):** `/opt/hermeslab/data/config.yaml` (MCP registration); possibly `~/dev/orion-compose/hermeslab/Dockerfile` if the policy-check package must be baked into the image.

- [ ] **Step 1: Decide the install vector for the policy-check package into the Hermes container.** Two options; pick the lower-friction one that works:
  - (a) **Overlay image:** create `~/dev/orion-compose/hermeslab/Dockerfile` `FROM nousresearch/hermes-agent:latest` that `pip install`s `trapezia-commercial-policy-check` from its GitHub repo (it is pip-installable via hatchling; deps include `fastmcp`, `anthropic`, `google-genai`, and `trapezia-document-reader @ git+https://…`). Point the compose `build:` at it instead of `image:`.
  - (b) **Runtime install** inside the running container (throwaway, for the first e2e only): `docker exec hermeslab pip install 'git+https://github.com/OrionAIDev/trapezia-commercial-policy-check'`.

Start with (b) to prove the path fast; graduate to (a) once it works so it survives restarts. Record the choice.

- [ ] **Step 2: Register the policy-check MCP server (stdio) in Hermes `config.yaml`.** The stdio launch command is:

```
python -m trapezia_commercial_policy_check.mcp_server
```

**Reference shape — confirmed from the live OrionLab registration (2026-07-20)**, which de-risks this step. OrionLab's `openclaw.json` registers it as:

```json
"mcp": { "servers": { "trapezia-commercial-policy-check": {
  "command": "python",
  "args": ["-m", "trapezia_commercial_policy_check.mcp_server"],
  "env": { "TRAPEZIA_PCC_STATE_DIR": "/opt/trapezia/data/trapezia-commercial-policy-check" }
}}}
```

So the stdio contract is `command` / `args` / `env` — expect the Hermes equivalent to mirror it.

**Discovery step (bounded):** the exact Hermes config *key* for an external stdio MCP server is not in the published docs excerpt (v0.2.x). Confirm on the live build via, in order: `docker exec hermeslab hermes config --help` (or interactive `hermes config`), the Hermes MCP docs page, then the GitHub repo. **Record the confirmed YAML snippet verbatim in the findings doc** (this unblocks the Phase 1 Hermes emitter's `invokes` mapping).

**Env to set on the HermesLab registration:**
- `TRAPEZIA_PCC_STATE_DIR=/opt/data/trapezia-commercial-policy-check` (container-local; do **not** share OrionLab's state dir).
- For the **stub** pass: set nothing else — bare-name model defaults resolve to the stub (see Task 5).
- For the **real** pass: `TRAPEZIA_PCC_LLM_PRIMARY_MODEL=google/gemini-2.5-pro` **and** `GOOGLE_API_KEY` (the `google/` prefix is what selects a real provider).

- [ ] **Step 3: Restart HermesLab and verify the four tools are discoverable.**

```bash
ssh root@100.117.27.98 'cd /opt/orion && docker compose -f docker-compose-hermeslab.yml restart hermeslab'
```

Expected: Hermes lists the policy-check tools `health`, `run_policy_check`, `get_run_status`, `get_run_report`. Verify via the Hermes tool-list surface (CLI/gateway) discovered above. Confirm `health` returns `status: ok` with the configured model identifiers.

---

### Task 5: End-to-end policy check from Discord via HermesLab

**Files:** a small non-PHI policy fixture (reuse an existing synthetic fixture from `trapezia-commercial-policy-check` — do **not** author new PHI/PII).

- [ ] **Step 1: Stage a synthetic policy fixture** reachable by the container (e.g. copy a scrubbed fixture from the policy-check repo's test fixtures into `/opt/hermeslab/data/home/`). Confirm it is the synthetic bench fixture, not a real policy.

- [ ] **Step 2: Pass A — stub run (proves plumbing, zero cost).** With no `TRAPEZIA_PCC_LLM_*` env set, drive a policy check from Discord in natural language. The agent should call `run_policy_check`, then `get_run_status`/`get_run_report`.

Expected: a run id is returned, status reaches a terminal state, and a report is produced. **This exercises Discord → Hermes → MCP → tools → report but the analysis is canned** (both default model ids are bare names → stub provider, FR-7.4). Record it explicitly as a *plumbing* pass, not an analysis pass.

- [ ] **Step 3: Pass B — real run (Google/Gemini).** Add `TRAPEZIA_PCC_LLM_PRIMARY_MODEL=google/gemini-2.5-pro` + `GOOGLE_API_KEY` to the policy-check MCP registration env, restart HermesLab, and repeat the same Discord request.

Expected: a report whose content reflects genuine LLM analysis of the fixture (not the stub's canned output). Diff the two reports to prove the provider actually changed — that diff **is** the evidence that the real path works.

- [ ] **Step 4: Capture exit-criteria evidence.** Put the Discord transcript, both `get_run_report` outputs, and the A-vs-B diff into the findings doc. If either pass fails, debug via `docker logs hermeslab` + policy-check run logs before proceeding (systematic-debugging).

---

### Task 6: Answer the five kill-questions (the real Phase 0 deliverable)

**Files:** `docs/superhuman/notes/2026-07-17-phase0-kill-question-findings.md`

Each step below is an investigation producing a **documented answer** (with evidence: a config snippet, a log excerpt, or an observed behavior). Fill the findings doc section-by-section.

- [ ] **Step 1: KQ-1 — Self-learning gating.** With `skills.write_approval: true`, ask the bot to create/modify a skill; confirm the write is staged to `/opt/hermeslab/data/pending/skills/` and is reviewable via `/skills pending`, `/skills diff <id>`, `/skills approve <id>`, `/skills reject <id>`. Confirm `guard_agent_created` behaves as a content scanner (independent of approval). Record the observed staging path + command outputs.

- [ ] **Step 2: KQ-2 — Model providers.** Confirm the main model runs on Anthropic direct and the `fallback_chain` (Sonnet → Google) engages on primary failure. Record the exact config keys and a log line showing a provider selection. (Policy-check itself needs Anthropic + Google; no OpenAI.)

- [ ] **Step 3: KQ-3 — Identity mapping.** Determine how Hermes maps a Discord user → a stable internal identity, and whether it can be translated to a capability-layer identity (the `X-Salus-Acting-As` analog for future PHI work; not needed for insure). Record the mechanism (even if "exists but unused here").

- [ ] **Step 4: KQ-4 — Memory / data capture.** Determine whether Hermes' persistent memory (`/opt/data/memories/`) auto-captures conversation content and whether it can be gated (`memory.write_approval` or equivalent). Record the gate and its default — this sets the PHI posture for any future non-insure capability.

- [ ] **Step 5: KQ-5 — Programmatic message-injection surface.** Determine whether Hermes' interactive CLI or gateway API drives the **same** agent loop / skill dispatch / tool calls as a Discord message. This decides whether Phase 2 e2e needs a special source build (as OpenClaw needed `openclaw-qa`) or can drive a CLI/API channel. Note the caveat: skills register as Discord **slash commands**, so slash-command dispatch (autocomplete, the 100-command cap) still needs a one-time manual Discord check per promotion. Record the finding + the recommended e2e channel.

- [ ] **Step 6: Commit the completed findings and summarize to the roadmap.**

```bash
git add docs/superhuman/notes/2026-07-17-phase0-kill-question-findings.md
git commit -m "docs(poc): Phase 0 kill-question findings (KQ1-5 answered)"
```

Then post a short summary comment (KQ verdicts + go/no-go for Phase 1) to `OrionAIDev/trapezia-roadmap#128` (`gh auth switch --user OrionAIDev` first).

---

### Task 7: Start M365 Business tenant + Azure Bot procurement (lead-time; Chris-owned)

**Files:** none (procurement tracking).

- [ ] **Step 1: Flag the lead-time item to Chris.** The M365 Business tenant + Azure Bot registration is the long-lead dependency for Phase 3 (Teams) and the project's deciding factor. Claude cannot create accounts/tenants. Surface it as a Chris action and record its status (started / blocked) on roadmap #128 so it runs in parallel with Phase 1.

---

### Task 8: Exit-criteria signoff

**Files:** `docs/superhuman/notes/2026-07-17-phase0-kill-question-findings.md`

- [ ] **Step 1: Confirm both exit criteria are met and evidenced (spec §3.5):**
  1. A policy check runs end-to-end from Discord via HermesLab against the policy-check MCP service (Task 5 evidence captured).
  2. All five kill-questions have documented answers (Task 6 complete).

- [ ] **Step 2: Record the go/no-go decision for Phase 1** in the findings doc and on roadmap #128, with rationale. If any kill-question is a hard blocker, stop and re-plan before Phase 1.

---

## Self-review notes

- **Spec coverage:** §3.1 (container/placement) → Tasks 1–3; §3.2 (connectivity) → Task 4; §3.3 (kill-questions) → Task 6; §3.4 (M365 lead-time) → Task 7; §3.5 (exit criteria) → Task 8. All covered.
- **Guardrails:** artifact-home (orion-compose) → Task 1; no-copy-auth → Tasks 0/2; no PHI → Task 5; no deployment-tracker → stated in header; port record → Task 0/8.
- **Known discovery gaps (bounded, not placeholders):** exact Hermes MCP-registration key (Task 4.2), main-model/fallback keys (Task 2.4), gateway health path (Task 3.3) — each has a concrete discovery method and a "record verbatim" artifact, appropriate for a v0.2.x tool where Phase 0's purpose is to resolve unknowns.
