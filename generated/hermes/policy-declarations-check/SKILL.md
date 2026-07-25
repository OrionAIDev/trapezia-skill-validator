---
name: policy-declarations-check
description: Extract a commercial policy's declarations-page fields from raw policy text and run them straight through the automated coverage/gap check. Use when the user wants a policy checked but only has the raw policy text, not a pre-built PolicyCheckingRun payload — this skill does the extraction step and the check in one pass.
version: 0.1.0
required_environment_variables:
  - GOOGLE_API_KEY
metadata:
  hermes:
    category: insure
    tags: [insure, trapezia]
---

# policy-declarations-check

## When to Use

Extract a commercial policy's declarations-page fields from raw policy text and run them straight through the automated coverage/gap check. Use when the user wants a policy checked but only has the raw policy text, not a pre-built PolicyCheckingRun payload — this skill does the extraction step and the check in one pass.

Trigger phrases: intake this policy, extract and check this policy, declarations check.

## Procedure

Run extract_declarations.py against the raw policy text to get a `policy` document, wrap it in a PolicyCheckingRun payload (run_id/run_timestamp/ spec_version plus the extracted `policy`), call run_policy_check, then poll get_run_status and fetch get_run_report — same engine as trapezia-commercial-policy-check, but starting from raw declarations text instead of a pre-built payload.

This skill wraps 1 MCP server(s):
- `trapezia-commercial-policy-check` (transport: stdio) tools: `health`, `run_policy_check`, `get_run_status`, `get_run_report`

Run the bundled script(s):
```
python ~/.hermes/skills/insure/policy-declarations-check/scripts/extract_declarations.py --input <policy.txt>
```

## Pitfalls

- extract_declarations.py is a deterministic text scan of the declarations page, not a coverage judgment — fields it cannot find are omitted, not guessed. Do not fabricate a policy_number, dates, or limits that were not present in the source text.
- If the policy-check MCP service is unreachable or a tool returns an error, surface the error verbatim and do not improvise a coverage verdict.
- This capability is for commercial (business) insurance policies only and handles no personal health information.

## Verification

Confirm the MCP server responds (e.g. its `health`/status tool) before relying on a result.

Run the script against a known input and confirm it exits 0 with the expected output.
