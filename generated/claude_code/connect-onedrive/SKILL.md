---
name: connect-onedrive
description: Link your Microsoft OneDrive account to Trapezia. Generates a secure OAuth link for the user to authorize OneDrive access. If already connected, shows current status instead. Use when a user wants to connect, link, or authorize their OneDrive.
---

# connect-onedrive

Link your Microsoft OneDrive account to Trapezia. Generates a secure OAuth link for the user to authorize OneDrive access. If already connected, shows current status instead. Use when a user wants to connect, link, or authorize their OneDrive.

Use when the user says: connect onedrive, link onedrive, authorize onedrive.

## Procedure

### Step 1 -- Check status, live

Call `onedrive_status` now. Leave `principal`/`user_id` empty -- the gateway fills the
principal; you never supply an identity.

- `{"connected": true, ...}` -- go to Step 2a
- `{"connected": true, "pending": true, ...}` -- go to Step 2b
- `{"connected": false}` -- go to Step 2c

### Step 2a -- Already connected

Reply using `service_name`/`service_email` from the tool response (never a cached value):

> Your OneDrive is already connected!
>
> **Account:** {service_name} ({service_email})
>
> Ask me to disconnect it if you ever want to unlink.

### Step 2b -- A sign-in is already pending

Tell the user a sign-in is already waiting rather than starting a second one:

> You already have a OneDrive sign-in in progress. Come back here and say "done" once
> you've finished it, or ask me for a fresh code if the old one expired.

Offer to call `onedrive_connect` again (a fresh code) only if the user asks for one.

### Step 2c -- Not connected: start device-code sign-in

Call `onedrive_connect` with `method="device_code"` (the default -- omit `method` or pass it
explicitly, either is fine). Leave `principal`/`user_id` empty.

- `{"already_connected": true, ...}` -- someone connected it between Step 1 and now; treat
  like Step 2a.
- `{"method": "device_code", "verification_uri": ..., "user_code": ..., "expires_in": ...}`
  -- go to Step 3.

### Step 3 -- Relay the device code

Reply with the verification URL and the user code, and say it expires in roughly
`expires_in / 60` minutes:

> **Connect your OneDrive**
>
> 1. Go to **{verification_uri}**
> 2. Enter this code: **{user_code}**
> 3. Sign in and approve access.
>
> This code expires in about {expires_in // 60} minutes. Come back here and say "done" once
> you've finished, and I'll confirm the connection.
>
> If the code doesn't work for you, I can send a sign-in link instead.

### Step 4 -- Confirm

When the user says "done" (or anything indicating they finished), call `onedrive_status`
again -- never assume success. Report the result the way Step 2a/2b would.

### Step 5 -- Link fallback (only if asked, or device code failed)

Only if the user asks for a link instead, or the device-code flow failed, call
`onedrive_connect` with `method="link"`. It returns `{"method": "link", "auth_url": ...,
"expires_in": ...}`. Reply:

> **Connect your OneDrive**
>
> Click the link below to securely authorize access to your Microsoft OneDrive account.
>
> **[Connect OneDrive]({auth_url})**
>
> The link expires in about {expires_in // 60} minutes. After you authorize, you can ask me
> to list, search, or upload files directly in this chat.

Wraps 1 MCP server(s):
- `trapezia-m365` (transport: http) tools: `onedrive_status`, `onedrive_connect`

## Guardrails

- Always call onedrive_status right now. Do not skip it or infer connection status from conversation history or memory -- the live tool response is the only source of truth.
- Never supply a platform ID, sender ID, or any identity value as a tool argument. Leave `principal` and `user_id` empty (or omit them) on every call -- the gateway stamps a signed sender principal on the call before it reaches the server. Do not ask the user for their platform ID, and do not read one from message metadata.
- If a tool call returns an MCP error, relay the error message verbatim to the user and suggest trying again. Never improvise a status or guess at what went wrong.
