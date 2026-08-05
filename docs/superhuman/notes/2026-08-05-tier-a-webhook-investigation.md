# Tier (a) hermetic webhook gate — investigation and supersession

**Date:** 2026-08-05
**Roadmap:** `OrionAIDev/trapezia-roadmap#128`, Phase 2

## Why this investigation happened

#128 scoped Phase 2's e2e work as two tiers: (a) a "hermetic" webhook/serve gate
described as *"the everyday CI gate"* and *"portable e2e → Lab-eligible"*, and
(b) the Discord fidelity gate, already done 2026-07-25. Before implementing (a),
Chris flagged that an e2e harness (`trapezia-e2e`) and a Discord test setup
(`hermestest`, `HermesE2E` guild) already exist, and asked what tier (a) would
actually add. That question turned up findings that invalidate tier (a)'s
original design.

## What was checked

**`hermes serve` is not an e2e surface.** It is the desktop-app JSON-RPC/
WebSocket backend, default port 9119, loopback-only unless an auth provider is
configured. Not a candidate for driving the agent+MCP loop headlessly.

**Nothing listens on 8642.** F-9 (2026-07-17 kill-question findings) guessed
"the OpenAI-compatible gateway API on 8642" as the tier-(a) candidate but never
verified it. Live probe against `hermeslab` (`curl localhost:8642/health` from
inside the container network) returned connection-refused; `ss -tlnp` inside
the container shows only the Discord-adapter process, no HTTP listener on
8642. The compose port mapping exists; nothing binds it.

**`hermes webhook` is real, but not what "hermetic" implies.** It is a
disabled-by-default gateway platform (`gateway/platforms/webhook.py`, aiohttp,
default port **8644**). Enabling it means editing `hermeslab`'s live
`config.yaml` (`platforms.webhook.enabled: true` + a route). The POST handler
(`_handle_webhook`) is **fire-and-forget**: it returns `202 Accepted` with a
`delivery_id` and spawns the agent turn as a background task
(`asyncio.create_task(self.handle_message(event))`). There is no synchronous
response to assert against — an e2e test would have to poll `/opt/data/state.db`
(`sessions.chat_id = webhook:<route>:<delivery_id>`, `tool_call_count`,
`messages.tool_name`) or the gateway log out-of-band. That's materially more
than "POST and assert," and it's a live-config mutation on `hermeslab`, not a
zero-touch CI job.

**The existing `trapezia-e2e` harness does not cover this gap.** Its
`SshDockerDriver.run_tool` is `ssh → docker exec <container> → python3
<skill_scripts>/<tool>.py` — it drives deployed skill *scripts* directly,
bypassing the agent loop and MCP dispatch entirely. It has no insure/
policy-check scenario and was never a candidate for proving harness→MCP
dispatch.

**policy-check's own MCP tests are in-process.**
`tests/integration/test_e2e_mcp_chunk3_demo.py` (in
`trapezia-commercial-policy-check`) imports and calls the tool functions
directly — no deployed harness, no agent loop.

## The actual coverage gap

| Layer | Automated coverage |
|---|---|
| MCP capability logic | ✅ policy-check's own suite (in-process) |
| Deployed skill scripts in a container | ✅ `trapezia-e2e` (OpenClaw only) |
| Harness channel reachability | ✅ tier (b) Discord |
| **Harness agent loop → MCP tool dispatch, content-verified** | ❌ nothing automated — proven once, manually, by Chris typing into Discord (F-9) |

Tier (b)'s existing assertion is "a reply arrived within timeout," not that
the reply reflects a real tool call. That's the actual gap — not the absence
of a webhook-specific gate.

## Decision (Chris, 2026-08-05)

**Drop tier (a).** Strengthen tier (b) instead: change the Discord probe to
ask HermesTest for the `trapezia-commercial-policy-check` `health` tool and
assert the reply's JSON content (`engine_version`, `schema_version`) rather
than merely "a reply arrived." This:

- closes the real gap (content-verified agent→MCP dispatch), matching the
  exact tool F-9 proved manually — a like-for-like comparison;
- reuses the already-green `discord-fidelity-e2e` CI job, no new container
  config, no new secret;
- retires "verify webhook/serve ≡ Discord dispatch" as moot — the strengthened
  gate asserts the product surface directly, so there is nothing left to
  compare it against.

The tier-(b) strengthening itself is **not implemented in this session**
(scope for this session is the Phase 2 protection group) — tracked as an open
subtask in #128.

`hermes webhook` is not wasted knowledge: it's the same platform mechanism
Phase 3 will need if a webhook-style push channel (vs. `trapezia-auth-server`
polling) is ever wanted for MS/Google. Not pursued now; no current Phase 3
sub-task needs it.

## Incidental finding — flag for rotation

While inspecting `hermeslab`'s live `config.yaml` `mcp_servers` block to
confirm F-6's registration shape, its raw `GOOGLE_API_KEY` value was printed
into a Claude Code session transcript (read-only `grep`, no write). Per the
sensitive-data boundary, HermesLab is a non-sensitive-by-policy Lab
environment, so this is not a PHI/PII incident, but the key is now sitting in
a session log outside its `/opt/orion/.env.hermeslab` home. **Recommend
rotating it** next time credentials are touched; not urgent enough to block
Phase 2 work.
