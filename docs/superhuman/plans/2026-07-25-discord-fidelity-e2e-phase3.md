# Automated Discord Fidelity E2E (Phase 3) Implementation Plan

> **For agentic workers:** TDD code plan continuing the multi-harness POC. Test first (red),
> implementation second (green), exact command + expected result per task. Commit per task.

**Goal:** Prove HermesLab-family message fidelity end-to-end over live Discord, automated in CI —
the QA-bound e2e deferred since Phase 1. A `discord.py` test-driver client sends a message into a
real Discord channel and asserts the target Hermes bot replies within a timeout. This is the *only*
gate in the POC that exercises Discord's actual wire protocol (mentions, threading, slash-command
registration) rather than a synthetic webhook/ACP call.

**Target environment:** `hermestest` (stood up 2026-07-25, see
`docs/superhuman/plans/2026-07-25-hermestest-standup-phase3.md`) — a dedicated Test-tier Hermes
container (`nousresearch/hermes-agent`, port 8643, `/opt/hermestest/data`), **not** `hermeslab`.
Two independent Discord bot applications: `HermesTest#4353` (target, `DISCORD_BOT_TOKEN`) and a
driver bot (`DISCORD_E2E_TOKEN`), both invited to the `HermesE2E` guild (id
`1530613567618027630`), channel `general` (id `1530613569777827964`). `DISCORD_ALLOW_BOTS=mentions`
is set on `hermestest` so the driver bot's messages are admitted — the test message MUST
`@mention` the target bot's user id (`1530583238974640249`); `hermeslab` is untouched (still
`DISCORD_ALLOW_BOTS=none`, its intended default posture per Chris's 2026-07-25 guidance that only
Salus and E2E servers require an explicit mention).

**Why this doesn't need SSH/orion-dev access from CI:** Discord bots connect outbound to Discord's
own gateway — `hermestest` reaches out to `gateway.discord.com`, and so does the CI-run test
client. Neither needs a direct network path to the other; Discord's servers are the rendezvous
point. The only CI requirement is a `DISCORD_E2E_TOKEN` secret.

**Tech stack:** adds `discord.py>=2.7` as a new optional extra (`e2e`) — not a `test`-extra
dependency, so the fast inner-loop `pytest -q` (laptop/Lab) never needs it installed.

---

## Locked design decisions (2026-07-25)

1. **Separate `e2e` extra, not folded into `test`.** `pip install -e ".[test]"` (the existing CI
   step) must keep working with zero new dependencies for the drift/unit suite. Only a job that
   explicitly installs `.[e2e]` pulls in `discord.py`.
2. **Test skips (not fails) when `DISCORD_E2E_TOKEN` is unset.** Lets the same test file run
   locally (skipped, harmless) and in CI (real, when the secret is present). Uses
   `pytest.mark.skipif`, not a separate conditional test file.
3. **IDs live in the test as named constants, not secrets.** Guild/channel/target-bot-user IDs are
   not sensitive (a Discord snowflake reveals nothing without the bot token). Only
   `DISCORD_E2E_TOKEN` is a GitHub Actions secret.
4. **New CI job, not a step in the existing `test` job.** Keeps the fast unit/drift gate
   (`pytest -q`, ~20s, always green-or-red on real code issues) isolated from a live external
   e2e that depends on Discord's uptime and `hermestest` staying up on orion-dev. The e2e job:
   - runs on push to `multi-harness-poc` and `master` only (not every PR from a fork, which
     wouldn't have the secret anyway — but scope explicitly rather than relying on the secret
     being absent to no-op)
   - has its own timeout (defends against a hung `discord.py` connection)
5. **Reply-detection is "any message from the target bot in-channel after the probe,"** not a
   content match. Fidelity here means "the round trip works," not "the agent said something
   specific" (that's the portable webhook e2e's job, still unbuilt, out of scope here).

**Out of scope for Phase 3 (explicitly deferred, not silently dropped):**
- The portable webhook/ACP e2e (content-correctness, MCP tool-calling path) — separate, unbuilt.
- Wiring `hermestest` into the deployment tracker — still an untracked POC env like `hermeslab`.
- Any Salus-server Discord config — Chris's mention-policy note was forward-looking context, not
  a task for this phase.

---

## Guardrails

- **Additive only.** No changes to `trapezia_skill_validator` or `trapezia_skill_spec` runtime
  code — this phase only adds a test file, a `pyproject.toml` extra, and a CI job.
- **Never commit a live token.** `DISCORD_E2E_TOKEN` exists only as a GitHub Actions repo secret
  and in `/opt/orion/.env.hermestest` (chmod 600, root-owned) — never in the repo, never pasted
  in a session transcript (per the updated no-secrets-in-chat policy).
- **mypy --strict clean** on the new test file (matches the Phase 1/2 carry-forward convention).

---

## Task 1: `discord.py` dependency + `e2e` extra

**Red:** `python -c "import discord"` fails outside a `.[e2e]` install (expected — no test to
write here, this is a packaging task). Confirm current `pip show discord.py` is absent in the
`test`-only env.

**Green:** add to `pyproject.toml`:
```toml
[project.optional-dependencies]
e2e = ["discord.py>=2.7"]
```

**Verify:** `pip install -e ".[test]"` still succeeds with no `discord` importable;
`pip install -e ".[e2e]"` makes `import discord` succeed.

## Task 2: Discord fidelity e2e test

**Red:** write `tests/e2e/test_discord_fidelity.py` — fails to collect without `discord.py`
installed (expected, matches Task 1's extra split) and fails/skips meaningfully without
`DISCORD_E2E_TOKEN`.

```python
import asyncio
import os
import time

import pytest

pytest.importorskip("discord")
import discord  # noqa: E402

GUILD_ID = 1530613567618027630
CHANNEL_ID = 1530613569777827964
TARGET_BOT_USER_ID = 1530583238974640249
REPLY_TIMEOUT_SECONDS = 30

E2E_TOKEN = os.environ.get("DISCORD_E2E_TOKEN")


@pytest.mark.skipif(not E2E_TOKEN, reason="DISCORD_E2E_TOKEN not set — live Discord e2e skipped")
def test_hermestest_replies_to_mention() -> None:
    """Send a mention into the HermesE2E test channel; assert HermesTest replies."""
    probe_nonce = str(time.time())
    result: dict[str, bool] = {"replied": False}

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        channel = client.get_channel(CHANNEL_ID) or await client.fetch_channel(CHANNEL_ID)
        await channel.send(f"<@{TARGET_BOT_USER_ID}> e2e-probe {probe_nonce}")

    @client.event
    async def on_message(message: "discord.Message") -> None:
        if message.author.id == TARGET_BOT_USER_ID and message.channel.id == CHANNEL_ID:
            result["replied"] = True
            await client.close()

    async def run() -> None:
        try:
            await asyncio.wait_for(client.start(E2E_TOKEN), timeout=REPLY_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            await client.close()

    asyncio.run(run())
    assert result["replied"], "hermestest did not reply within the timeout"
```

**Green:** the test as written IS the implementation — no production code changes. Run locally
without the secret: `pytest tests/e2e/test_discord_fidelity.py -v` → 1 skipped.

**Verify (manual, needs the secret):**
`DISCORD_E2E_TOKEN=<from /opt/orion/.env.hermestest, read server-side, never pasted in chat>
pytest tests/e2e/test_discord_fidelity.py -v` → 1 passed, and the `general` channel in HermesE2E
shows both the probe message and a real reply from `HermesTest#4353`.

## Task 3: CI job for the live e2e

**Red:** no `.github/workflows/ci.yml` job runs this test yet — confirm by inspection (no red
test to write for a workflow file; verify via a real push once added).

**Green:** add a second job to `.github/workflows/ci.yml`:

```yaml
  discord-fidelity-e2e:
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/multi-harness-poc' || github.ref == 'refs/heads/master'
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -e ".[test,e2e]"
      - run: pytest tests/e2e/test_discord_fidelity.py -v
        env:
          DISCORD_E2E_TOKEN: ${{ secrets.DISCORD_E2E_TOKEN }}
```

**Verify:** push, confirm the new job appears in the Actions run and passes (real Discord round
trip, not a skip — requires the repo secret to be set first, see Task 4).

## Task 4: Wire the CI secret (Chris action, not code)

GitHub repo secret `DISCORD_E2E_TOKEN` (Settings → Secrets and variables → Actions) on
`OrionAIDev/trapezia-skill-validator`, value = the same token saved in
`/opt/orion/.env.hermestest`. Chris sets this directly in GitHub's UI — never routed through chat
or committed.

## Task 5: Evidence + memory update

Evidence note `docs/superhuman/notes/2026-07-25-phase3-validation.md`: CI run URL/id, timing,
confirmation the `general` channel shows the probe + reply. Update the `multi-harness-poc` memory
with Phase 3 completion, matching the Phase 1/2 close-out bar.
