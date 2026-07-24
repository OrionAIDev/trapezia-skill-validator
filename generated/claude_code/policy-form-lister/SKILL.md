---
name: policy-form-lister
description: List the insurance form numbers (ISO commercial-lines and ACORD) referenced in a policy document. Use when the user asks to "list the forms", "what forms are in this policy", or wants a form-number inventory.
---

# policy-form-lister

List the insurance form numbers (ISO commercial-lines and ACORD) referenced in a policy document. Use when the user asks to "list the forms", "what forms are in this policy", or wants a form-number inventory.

Use when the user says: list forms, what forms are in this policy, form inventory.

## Procedure

Run list_forms.py with --input pointing at the policy text; it prints the sorted unique form numbers as JSON. Deterministic, no network, no LLM.

Run the bundled script(s):
```
python ~/.claude/skills/policy-form-lister/scripts/list_forms.py --input <policy.txt>
```

## Guardrails

- This is a deterministic text scan, not a coverage judgment — report the form numbers it finds and do not infer coverage from their presence or absence.
- Recognizes ISO commercial-lines and ACORD form numbers only; unrecognized or manuscript forms will not appear.
