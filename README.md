# trapezia-skill-validator

Deterministic conformance checks for Trapezia skills. Shared by `skill-template`
(self-test) and the `trapezia-disciplines` auditor skill.

## Quick start

```bash
pip install -e .
trapezia-skill-validator /path/to/some-skill          # human-readable report
trapezia-skill-validator /path/to/some-skill --json    # machine-readable
```

## What it checks

See the check catalog in the design spec
(`docs/superpowers/specs/2026-05-31-trapezia-disciplines-conformance-standard-design.md` §5a).
Structural checks are deterministic; LLM-judgment checks live in the auditor skill, not here.

## Sensitive data

The non-secret *shape* patterns ship in `data/sensitive_patterns.toml`. The secret PHI
wordlist is read from `$TRAPEZIA_PHI_WORDLIST` at runtime and is never bundled.
