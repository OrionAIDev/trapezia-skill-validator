# Phase 3 Validation — Automated Discord Fidelity E2E

**Date:** 2026-07-25
**Plans:** `docs/superhuman/plans/2026-07-25-hermestest-standup-phase3.md` (ops),
`docs/superhuman/plans/2026-07-25-discord-fidelity-e2e-phase3.md` (TDD code)

## Summary

Proved the QA-bound Discord fidelity e2e deferred since Phase 1: a `discord.py`
test-driver client, running entirely on GitHub-hosted CI infrastructure, sends
a live `@mention` into a real Discord channel and confirms a dedicated Hermes
target bot (`hermestest`, running on orion-dev) replies within a timeout.

## Environment stood up

New Test-tier Hermes container `hermestest` (`nousresearch/hermes-agent`,
port 8643, `/opt/hermestest/data`), independent of `hermeslab` — required
because HermesLab's Discord adapter rejects other-bot messages by default
(`DISCORD_ALLOW_BOTS=none`) and a driver bot is unavoidably a second bot
account. `hermestest` runs with `DISCORD_ALLOW_BOTS=mentions` instead, kept
off `hermeslab` to avoid loosening its ingress policy for a Lab-tier env.

Two independent Discord bot applications, both invited to a dedicated
`HermesE2E` guild (id `1530613567618027630`), channel `general` (id
`1530613569777827964`):
- **`HermesTest#4353`** (user id `1530583238974640249`) — the target agent,
  `DISCORD_BOT_TOKEN` in `/opt/orion/.env.hermestest`.
- **A separate driver bot** — `DISCORD_E2E_TOKEN`, used exclusively to send
  the test probe and observe the reply. Never used for normal agent traffic.

## Live findings during stand-up

- **Confirmed the real env var Hermes reads is `DISCORD_BOT_TOKEN`, not
  `DISCORD_TOKEN`** — the `.env.hermeslab.example` / `.env.hermestest.example`
  templates in `orion-compose` had it wrong (stale guess from before Phase 0's
  hands-on setup). Fixed both templates (commit `19b37eb` in `orion-compose`).
- **Discord bots connect outbound to Discord's own gateway**, so the e2e test
  needs no network path to orion-dev at all — it runs unmodified on GitHub
  Actions runners, authenticating only as the driver bot.
- **Hermes' `auto_thread` behavior** spins up a reply thread off the
  triggering message (thread channel id = the triggering message's id) rather
  than replying in-channel. First test run timed out because it only watched
  the parent channel id; fixed by accepting a reply either in the target
  channel or in a thread whose `parent_id` matches it — this is also more
  representative of real Discord fidelity than forcing `no_thread_channels`.
- **A model-provider misconfiguration surfaced but did not block the gate**:
  `hermestest`'s fresh `hermes setup` paired `model=anthropic/claude-opus-4.6`
  with `provider=gemini`, causing 3 retried `HTTP 404` calls before a fallback
  reply was sent (~14s total). Phase 3 explicitly only asserts "a reply
  arrived," not content correctness (that's the separate, still-unbuilt
  portable webhook/ACP e2e's job), so this didn't fail the test — flagged
  here as a known follow-up if `hermestest` is used for anything beyond
  fidelity checks.

## CI evidence

- Pushed `multi-harness-poc` → `623bbff` (2 commits: test + CI job).
- Run [`30167023628`](https://github.com/OrionAIDev/trapezia-skill-validator/actions/runs/30167023628):
  both jobs green — `test` (18s, existing unit/drift suite, unaffected) and
  **`discord-fidelity-e2e` (17s, new — real Discord round trip from GitHub's
  infrastructure)**.
- `DISCORD_E2E_TOKEN` set as a GitHub Actions repository secret on
  `OrionAIDev/trapezia-skill-validator` (Chris, via GitHub's UI — never
  routed through chat). `DISCORD_BOT_TOKEN` deliberately NOT added to GitHub
  secrets — CI only needs to act as the driver bot, never the target.
- Local pre-CI verification: `pytest tests/e2e/test_discord_fidelity.py -v`
  with `DISCORD_E2E_TOKEN` sourced server-side via SSH (never pasted in
  chat) — 1 passed, confirmed against the live `HermesE2E` guild before
  wiring into CI.

## Scope confirmation vs. the locked design decisions

- `e2e` kept as a separate `pyproject.toml` extra — `pip install -e ".[test]"`
  still has zero `discord.py` dependency; only `discord-fidelity-e2e` CI job
  installs `.[test,e2e]`.
- New CI job kept separate from the fast `test` job, scoped to
  `multi-harness-poc`/`master` pushes only (skips PRs).
- mypy --strict clean on the new test file (two narrow, named
  `# type: ignore[untyped-decorator]` exceptions for discord.py's untyped
  `Client.event` decorator — a real, external library gap, same pattern as
  the pre-existing `yaml` import-untyped exception).

Phase 3 is complete: implemented, validated live, pushed, CI green — same bar
as Phases 1 and 2's close.
