# HermesTest stand-up — Phase 3 prep (ops-only plan)

**Goal:** Stand up an isolated `hermestest` Hermes container on orion-dev (Test
tier, mirroring `hermeslab`) so Phase 3's automated Discord fidelity e2e has
a real target that isn't the Lab environment. Reuses the `hermeslab` compose
pattern; own container, own port, own state dir, own Discord bot.

**Why a new env instead of reusing hermeslab (decided 2026-07-25):** the
automated e2e needs a *second*, independent Discord bot account to act as the
test-driver client (HermesLab's adapter rejects other-bot messages by default
— `DISCORD_ALLOW_BOTS=none`; confirmed by reading
`/opt/hermes/plugins/platforms/discord/adapter.py` inside the running
`hermeslab` container). Once a second bot is needed anyway, Chris opted to
stand up a dedicated `hermestest` env rather than bolt a test-client bot onto
Lab — matches the original roadmap classification (Phase 3 targets Test tier,
not Lab) that was initially going to be skipped for expedience.

**Scope:** infra only — no application code changes. Compose file lives in
`orion-compose` (branch `feat/hermeslab-poc`, not yet merged to `main`);
server-side state under `/opt/hermestest/`. No PHI, no deployment-tracker
registration (same POC posture as hermeslab).

## Steps

1. **Compose file** — `docker-compose-hermestest.yml` in `orion-compose`,
   cloned from `docker-compose-hermeslab.yml`: container `hermestest`, port
   `8643:8642` (8642 taken by hermeslab), data dir `/opt/hermestest/data`,
   `env_file: /opt/orion/.env.hermestest`. Same `host.docker.internal`
   extra_hosts, same dashboard-disabled posture, same resource limits.
2. **Env file** — `/opt/orion/.env.hermestest` (chmod 600, root-owned),
   template `.env.hermestest.example` committed (mirrors
   `.env.hermeslab.example`). `GOOGLE_API_KEY` may be reused verbatim from
   `.env.hermeslab` (stateless API key, not a single-use OAuth token — no
   independence requirement, unlike Discord bot tokens). `DISCORD_BOT_TOKEN`
   (the hermestest target bot — corrected var name, 2026-07-25: Hermes reads
   `DISCORD_BOT_TOKEN` not `DISCORD_TOKEN`, confirmed in the adapter source)
   and `DISCORD_E2E_TOKEN` (the driver bot, Chris's naming) are new,
   independent credentials — **Chris writes both directly into the
   server-side file** (never pasted in chat, per updated policy).
3. **State dir + ownership** — `/opt/hermestest/data`, `chown -R 10000:10000`
   (F-8: Hermes runs as uid 10000; unowned dirs crash MCP subprocess imports).
4. **Bring up + `hermes setup`** — once Chris confirms both Discord tokens
   are saved, bring the container up and run the same interactive
   `hermes setup` flow Phase 0 Task 3 used (register Discord bot, set
   `DISCORD_ALLOW_ALL_USERS` or an explicit allowlist for the human path,
   plus `DISCORD_ALLOW_BOTS=mentions` for the test-client bot path this time
   — new requirement vs. hermeslab). Verify gateway + Discord connectivity
   the same way Phase 0 did (logs, not just "awaiting readiness").
5. **No MCP wiring planned** — Phase 3 exercises Discord message fidelity
   (delivery + slash-commands), not a tool-calling loop; the portable
   webhook/ACP e2e (separately scoped, not yet built) covers the MCP path.
   Add MCP registration only if the fidelity test turns out to need a live
   tool call to be meaningful.
6. **Hand back to Phase 3 proper** — write the `discord.py` test client
   (send `@mention` message to a test channel, assert reply within timeout),
   wire it into CI as the QA-bound e2e gate (Test-tier only, matches original
   roadmap classification), evidence note under `docs/superhuman/notes/`.

## Open items to confirm with Chris once bots exist

- Exact Discord server/guild + test channel to use (new dedicated one, or an
  existing throwaway).
- Whether the human-facing allowlist should be `DISCORD_ALLOW_ALL_USERS=true`
  (matches hermeslab) or a scoped `DISCORD_ALLOWED_USERS` — no PHI/sensitive
  data here so either is low-risk, but scoped is tidier for a bot no one
  chats with directly.
