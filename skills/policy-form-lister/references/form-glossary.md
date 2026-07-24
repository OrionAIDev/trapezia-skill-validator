# Insurance form-number glossary

Reference for the prefixes `list_forms.py` recognizes. This is a naming key, not
a coverage guide — the script only reports which form numbers appear in a
document, never what they mean for a given policy.

## ISO commercial-lines prefixes

| Prefix | Line of business                     |
| ------ | ------------------------------------ |
| CG     | Commercial General Liability         |
| CP     | Commercial Property                  |
| IL     | Interline (applies across lines)     |
| CA     | Commercial Auto                      |
| WC     | Workers Compensation                 |
| BP     | Businessowners                       |
| CR     | Crime                                |
| CU     | Commercial Umbrella / Excess         |
| GL     | General Liability (legacy)           |
| CM     | Commercial Inland Marine             |
| MP     | Multi-Peril                          |

An ISO form id looks like `CG 00 01` — a two-letter prefix plus two 2-digit
groups. An edition date may follow (`CG 00 01 04 13`); only the base id is
reported.

## ACORD forms

ACORD certificate/application forms are reported as `ACORD <number>`
(e.g. `ACORD 25`, the Certificate of Liability Insurance).
