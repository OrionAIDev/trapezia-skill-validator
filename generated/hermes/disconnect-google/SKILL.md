---
name: disconnect-google
description: Disconnect your Google account from Trapezia and remove stored credentials. Use when a user wants to unlink, disconnect, or remove their Google connection.
version: 1.1.0
metadata:
  hermes:
    category: connectors
    tags: [connectors, trapezia]
---

# disconnect-google

## When to Use

Disconnect your Google account from Trapezia and remove stored credentials. Use when a user wants to unlink, disconnect, or remove their Google connection.

Trigger phrases: disconnect google, unlink google, remove google.

## Procedure

### Step 1 -- Check status, live

Call `google_status` now. Leave `principal`/`user_id` empty -- the gateway fills the
principal; you never supply an identity.

- `{"connected": false}` -- go to Step 2a
- `{"connected": true, ...}` -- go to Step 2b

### Step 2a -- Not connected

Reply:

> Your Google account is not connected -- nothing to disconnect.

### Step 2b -- Connected: confirm before disconnecting

Ask the user to confirm, naming the account from the status response:

> Disconnect your Google account ({service_email})? This removes the stored credentials and
> revokes access at Google, not just locally -- you'll need to reconnect to use Gmail,
> Calendar, or Drive again in this chat.

Only proceed to Step 3 once the user confirms. If they decline, stop here.

### Step 3 -- Disconnect

Call `google_disconnect`. Leave `principal`/`user_id` empty.

- `{"ok": true, "was_connected": true, "service_name": ..., "service_email": ...}` -- report
  success using those fields:

  > **Google disconnected.**
  >
  > Removed credentials for {service_name} ({service_email}).
  >
  > You can reconnect anytime by asking me to connect Google again in this chat.

- `{"ok": true, "was_connected": false, ...}` -- it was already disconnected by the time the
  call landed; tell the user there was nothing to remove.

This skill wraps 1 MCP server(s):
- `trapezia-google` (transport: http) tools: `google_status`, `google_disconnect`

## Pitfalls

- Always call google_status right now. Do not skip it or infer connection status from conversation history or memory -- the live tool response is the only source of truth.
- Never supply a platform ID, sender ID, or any identity value as a tool argument. Leave `principal` and `user_id` empty (or omit them) on every call -- the gateway stamps a signed sender principal on the call before it reaches the server. Do not ask the user for their platform ID, and do not read one from message metadata.
- Disconnecting is destructive -- it removes stored credentials and revokes the token server-side at Google, not just locally. Confirm with the user before calling google_disconnect; do not disconnect on an ambiguous or implied request.
- If a tool call returns an MCP error, relay the error message verbatim to the user and suggest trying again. Never improvise a status or guess at what went wrong.

## Verification

Confirm the MCP server responds (e.g. its `health`/status tool) before relying on a result.
