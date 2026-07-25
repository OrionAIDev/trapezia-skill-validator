"""Live Discord fidelity e2e for the multi-harness POC (Phase 3).

Sends a mention into the HermesE2E test guild's ``general`` channel and
asserts the ``hermestest`` Hermes container replies within a timeout. Skips
cleanly when ``DISCORD_E2E_TOKEN`` is unset (laptop/Lab runs); only runs for
real in CI, where the token is a GitHub Actions secret.
"""

from __future__ import annotations

import asyncio
import os
import time
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import discord as discord_types

discord = pytest.importorskip("discord")

GUILD_ID = 1530613567618027630
CHANNEL_ID = 1530613569777827964
TARGET_BOT_USER_ID = 1530583238974640249
REPLY_TIMEOUT_SECONDS = 30

E2E_TOKEN = os.environ.get("DISCORD_E2E_TOKEN")


@pytest.mark.skipif(not E2E_TOKEN, reason="DISCORD_E2E_TOKEN not set — live Discord e2e skipped")
def test_hermestest_replies_to_mention() -> None:
    """Send a mention into the HermesE2E test channel; assert HermesTest replies."""
    probe_nonce = str(time.time())
    result = {"replied": False}

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event  # type: ignore[untyped-decorator]  # discord.py's Client.event decorator is untyped
    async def on_ready() -> None:
        channel = client.get_channel(CHANNEL_ID) or await client.fetch_channel(CHANNEL_ID)
        await channel.send(f"<@{TARGET_BOT_USER_ID}> e2e-probe {probe_nonce}")

    @client.event  # type: ignore[untyped-decorator]  # discord.py's Client.event decorator is untyped
    async def on_message(message: "discord_types.Message") -> None:
        # Hermes' auto_thread behavior spins up a reply thread off the triggering
        # message (thread channel id = message id), so the reply may land in a
        # thread rather than the channel directly — accept either.
        channel = message.channel
        in_target = channel.id == CHANNEL_ID or getattr(channel, "parent_id", None) == CHANNEL_ID
        if message.author.id == TARGET_BOT_USER_ID and in_target:
            result["replied"] = True
            await client.close()

    async def run() -> None:
        try:
            await asyncio.wait_for(client.start(E2E_TOKEN or ""), timeout=REPLY_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            await client.close()

    asyncio.run(run())
    assert result["replied"], "hermestest did not reply within the timeout"
