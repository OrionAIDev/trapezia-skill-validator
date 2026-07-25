# Declarations extraction field map

What `extract_declarations.py` recovers from a declarations-page text scan,
mapped to the `PolicyDocument` field names used by the
`trapezia-commercial-policy-check` engine's input schema
(`trapezia_commercial_policy_check.schemas.inputs.PolicyDocument`). This is a
mapping key, not a coverage guide.

## Fields extracted

| Declarations-page text                          | `PolicyDocument` field         | Notes |
| ------------------------------------------------- | ------------------------------- | ----- |
| `Policy Number: <id>`                              | `policy_number`                 | Verbatim capture. |
| `Carrier: <name>`                                  | `carrier_name`                  | Verbatim capture. |
| `Named Insured: <name>`                            | `named_insureds`                | Wrapped in a single-element list; only the first named insured is captured. |
| `Policy Period: MM/DD/YYYY to MM/DD/YYYY`          | `policy_effective_date`, `policy_expiration_date` | Normalized to ISO 8601 (`YYYY-MM-DD`). |
| `Each Occurrence Limit: $N`                        | `gl_each_occurrence`            | `$`/commas stripped; normalized integer. |
| `General Aggregate Limit: $N`                      | `gl_general_aggregate`          | `$`/commas stripped; normalized integer. |
| ISO/ACORD form numbers anywhere in the text        | `forms_schedule`                | Normalized uppercase, spaces stripped, edition suffix dropped (e.g. `CG 00 01 04 13` → `CG0001`) — same convention as `PolicyDocument.forms_schedule`, not `list_forms.py`'s human-readable spaced format. |

## Fields NOT extracted

`PolicyDocument` has roughly 120 fields (property, business income, auto,
workers' comp, umbrella, professional liability, cyber, additional
insureds, compliance/TRIA, etc.) that a single declarations-page regex scan
cannot reliably recover — they require reading coverage parts, endorsement
forms, and schedules the declarations page only references by number. Those
stay `None`/absent in the extracted `policy` document; an account manager
(or a follow-up extraction pass) fills them in before the payload is
considered complete for a full `run_policy_check` run. `run_policy_check`
itself does not require every field — checks that depend on a missing field
are flagged "Unable to Complete" by the engine, not blocked outright.
