---
name: trapezia-commercial-policy-check
description: Run an automated commercial-insurance policy check and produce a coverage/gap report. Use when the user asks to "check a policy", "run a policy check", or "review coverage", or drops a commercial policy document expecting analysis.
---

# trapezia-commercial-policy-check

Run an automated commercial-insurance policy check and produce a coverage/gap report. Use when the user asks to "check a policy", "run a policy check", or "review coverage", or drops a commercial policy document expecting analysis.

Use when the user says: policy check, check this policy, review coverage.

## Procedure

Call run_policy_check with the policy payload, then poll get_run_status and fetch get_run_report.

Wraps 1 MCP server(s):
- `trapezia-commercial-policy-check` (transport: stdio) tools: `health`, `run_policy_check`, `get_run_status`, `get_run_report`

**Model tier: sonnet** (advisory — dispatch judgment-heavy steps to a `sonnet`-tier agent).

## Guardrails

- If the policy-check MCP service is unreachable or a tool returns an error, surface the error verbatim and do not improvise a coverage verdict.
- This capability is for commercial (business) insurance policies only and handles no personal health information.
