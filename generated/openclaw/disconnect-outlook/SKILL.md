---
name: disconnect-outlook
description: Disconnect your Microsoft Outlook account from Trapezia and remove stored credentials. Use when a user wants to unlink, disconnect, or remove their Outlook connection.
---

# disconnect-outlook

Disconnect your Microsoft Outlook account from Trapezia and remove stored credentials. Use when a user wants to unlink, disconnect, or remove their Outlook connection.

Trigger phrases: disconnect outlook, unlink outlook, remove outlook.

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
GET https://auth.trapezia.ai/status?platform=discord&user_id=<sender_id>&service=outlook&env=<INSTANCE_NAME>
```

Parse the raw JSON response:
- `{"connected": true, "service_name": "...", "service_email": "...", "connected_at": "..."}` -- go to Step 3b
- `{"connected": false}` -- go to Step 3a

### Step 3a -- If `"connected": false`

Reply:
> Your Outlook is not connected -- nothing to disconnect.

### Step 3b -- If `"connected": true`

Warn first -- this is a **tier-wide disconnect**, and reusing OrionLab's identity means it
applies from HermesLab too:
> **Heads up -- tier-wide disconnect**
>
> Credentials are shared across the **dev tier**. Disconnecting will remove your Outlook
> access (both email and calendar) from **OrionDev, OrionLab, and OrionTest** -- including this
> HermesLab session, which reuses OrionLab's identity.
>
> Proceeding with disconnect now...

Then call:
```
GET https://auth.trapezia.ai/disconnect?platform=discord&user_id=<sender_id>&service=outlook&env=<INSTANCE_NAME>
```

The response includes `service_name`, `service_email`, and `affected_environments`. Follow up:
> **Outlook disconnected.**
>
> Removed credentials for {service_name} ({service_email}).
>
> **Environments affected:** {affected_environments (join with ", ")}
>
> You can reconnect anytime with `/connect-outlook`.

## Guardrails

- Always call the status check in Step 2 right now. Do not skip it or infer connection status from context.
- Parse the raw JSON response before deciding which branch to follow.
- Warn the user about the tier-wide impact (see Step 3b) before calling the disconnect API.
