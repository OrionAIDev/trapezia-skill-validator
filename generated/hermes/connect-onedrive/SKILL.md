---
name: connect-onedrive
description: Link your Microsoft OneDrive account to Trapezia. Generates a secure OAuth link for the user to authorize OneDrive access. If already connected, shows current status instead. Use when a user wants to connect, link, or authorize their OneDrive.
version: 1.0.0
metadata:
  hermes:
    category: connectors
    tags: [connectors, trapezia]
---

# connect-onedrive

## When to Use

Link your Microsoft OneDrive account to Trapezia. Generates a secure OAuth link for the user to authorize OneDrive access. If already connected, shows current status instead. Use when a user wants to connect, link, or authorize their OneDrive.

Trigger phrases: connect onedrive, link onedrive, authorize onedrive.

## Procedure

### Step 0 -- Resolve your instance name

On OpenClaw, read the instance marker:
```python
import os
try:
    print(open("/opt/openclaw-workspace/.instance").read().strip())
except FileNotFoundError:
    print(os.environ.get("INSTANCE_NAME", "oriondev"))
```
On Hermes (HermesLab), always use `orionlab` -- HermesLab reuses OrionLab's connected
identity via the shared trapezia-auth-server (roadmap #128 Phase 3 step 1); it has no
dedicated instance/OAuth identity of its own.

Store the resolved value as `INSTANCE_NAME` and use it as `env=` in every URL below.

### Step 1 -- Get the user's platform ID

From inbound message metadata (e.g. `sender_id` on Discord).

### Step 2 -- Call the status API RIGHT NOW

Your harness's tool-calling surface for "make an HTTP GET and read the JSON body" varies
(OpenClaw: `web_fetch`; Hermes: no dedicated fetch tool -- run this via your code-execution
tool instead, e.g.:
```python
import json, urllib.request
with urllib.request.urlopen("<url>", timeout=10) as r:
    print(json.load(r))
```
). Whichever mechanism your harness uses, call it now -- do not skip this call and do not
infer connection status from conversation history or memory. The live API response is the
only source of truth.

```
GET https://auth.trapezia.ai/status?platform=discord&user_id=<sender_id>&service=onedrive&env=<INSTANCE_NAME>
```

Parse the raw JSON response:
- `{"connected": true, "service_name": "...", "service_email": "...", "connected_at": "..."}` -- already connected
- `{"connected": false}` -- not connected

### Step 3a -- If `"connected": true`

Reply using `service_name`/`service_email` from the API response (never a cached value):
> Your OneDrive is already connected!
>
> **Account:** {service_name} ({service_email})
>
>  Use `/disconnect-onedrive` to unlink.

### Step 3b -- If `"connected": false`

Call:
```
GET https://auth.trapezia.ai/onedrive/connect?platform=discord&user_id=<sender_id>&env=<INSTANCE_NAME>
```

This returns JSON with an `auth_url` field. Reply:
> Connect your OneDrive
>
> Click the link below to securely authorize access to your Microsoft OneDrive account. 
>
> **[Connect OneDrive]({auth_url})**
>
> The link expires in 10 minutes. After you authorize, you can ask me to
> list, search, or upload files directly in chat.

## Pitfalls

- Always call the status check in Step 2 right now. Do not skip it or infer connection status from conversation history or memory -- the live API response is the only source of truth.
- Parse the raw JSON response before deciding which branch to follow.

## Verification

Follow the Procedure above — its live status check *is* the verification step; never infer
connection state from memory or conversation history.
