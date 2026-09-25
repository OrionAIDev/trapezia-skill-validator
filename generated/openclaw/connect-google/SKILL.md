---
name: connect-google
description: Link your Google account (Gmail + Calendar + Drive) to Trapezia. Generates a secure OAuth link for the user to authorize Google access. If already connected, shows current status instead. Use when a user wants to connect, link, or authorize their Google, Gmail, Google Calendar, or Google Drive.
---

# connect-google

Link your Google account (Gmail + Calendar + Drive) to Trapezia. Generates a secure OAuth link for the user to authorize Google access. If already connected, shows current status instead. Use when a user wants to connect, link, or authorize their Google, Gmail, Google Calendar, or Google Drive.

Trigger phrases: connect google, link google, authorize google.

## Procedure

### Step 1 -- Check status, live

Call `google_status` now. Leave `principal`/`user_id` empty -- the gateway fills the
principal; you never supply an identity.

- `{"connected": true, ...}` -- go to Step 2a
- `{"connected": true, "pending": true, ...}` -- go to Step 2b (Google has no device-code
  flow, but a link sign-in can still be mid-flight if the user hasn't finished it yet)
- `{"connected": false}` -- go to Step 2c

### Step 2a -- Already connected

Reply using `service_name`/`service_email` from the tool response (never a cached value):

> Your Google account is already connected!
>
> **Account:** {service_name} ({service_email})
>
> This connection covers **Gmail, Calendar, and Drive** -- one consent, by design. Ask me to
> disconnect it if you ever want to unlink.

### Step 2b -- A sign-in is already pending

> You already have a Google sign-in in progress. Come back here and say "done" once you've
> finished it, or ask me for a fresh link if the old one expired.

Offer to call `google_connect` again (a fresh link) only if the user asks for one.

### Step 2c -- Not connected: send the sign-in link

Call `google_connect`. Leave `principal`/`user_id` empty.

- `{"already_connected": true, ...}` -- someone connected it between Step 1 and now; treat
  like Step 2a.
- `{"method": "link", "auth_url": ..., "expires_in": ...}` -- go to Step 3.

### Step 3 -- Relay the link

Reply with the link, and say it expires in roughly `expires_in / 60` minutes (Google's link
typically lasts about 10 minutes):

> **Connect your Google account**
>
> Click the link below to securely authorize access to your Google account. This connection
> covers **Gmail, Calendar, and Drive** -- one consent, by design.
>
> **[Connect Google]({auth_url})**
>
> The link expires in about {expires_in // 60} minutes. Google may show a one-time "Google
> hasn't verified this app" notice -- choose **Advanced -> Go to Trapezia** to continue.
> After you authorize, you can ask me to read your inbox, send mail, list events, schedule
> meetings, or search Drive directly in this chat.

### Step 4 -- Confirm, if the user says they're done

If the user says "done" (or anything indicating they finished), call `google_status` again
-- never assume success. Report the result the way Step 2a would.

Wraps 1 MCP server(s):
- `trapezia-google` (transport: http) tools: `google_status`, `google_connect`

## Guardrails

- Always call google_status right now. Do not skip it or infer connection status from conversation history or memory -- the live tool response is the only source of truth.
- Never supply a platform ID, sender ID, or any identity value as a tool argument. Leave `principal` and `user_id` empty (or omit them) on every call -- the gateway stamps a signed sender principal on the call before it reaches the server. Do not ask the user for their platform ID, and do not read one from message metadata.
- If a tool call returns an MCP error, relay the error message verbatim to the user and suggest trying again. Never improvise a status or guess at what went wrong.
