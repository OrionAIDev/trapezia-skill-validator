# Phase 4 Decision — `trapezia_skill_spec` extraction exploration

**Date:** 2026-07-25
**Plan:** `docs/superhuman/plans/2026-07-25-extraction-exploration-phase4.md`

## Summary

Evaluated whether to extract `trapezia_skill_spec` (the canonical-spec
generator, ~421 lines Python + ~154 lines Jinja2 templates) out of the
`trapezia-skill-validator` repo into its own package. The Phase 1/2
graduation-decision rule gated extraction on two triggers: (a) a second real
skill type proven through the generator, or (b) another team needing the
generator standalone without the validator. Phase 2's `policy-form-lister`
satisfied trigger (a). Trigger (b) has not occurred.

## Decision: stay merged (Chris, 2026-07-25)

No extraction. `trapezia_skill_spec` remains inside `trapezia-skill-validator`.
No code changes made this phase — this was explicitly a decision-only phase
per the locked roadmap.

## Reasoning

Trigger (a) firing proved the generator generalizes across skill shapes; it
did not create any actual pressure to split the package. Trigger (b) — the
harder bar, and the one that would create real pressure (an external
consumer, an independent versioning need) — has not fired. Extracting solely
because trigger (a) fired would be a premature-abstraction move at the
package-boundary level, with concrete near-term costs and no offsetting
benefit:

- `spec_lint.py` imports `trapezia_skill_spec.schema` directly, in-process;
  extraction turns this into an external dependency with no package index to
  pin against (git-ref pinning only, since Trapezia-internal packages don't
  have a registry yet).
- `specs/*.yaml`, `skills/<name>/` bundle assets, and committed `generated/**`
  all live in this repo today, exercised by the same drift test
  (`tests/spec/test_regeneration.py`) that proves the generator works —
  extracting the engine alone doesn't relocate this content.
- CI would split into two pipelines; the validator's pipeline would need to
  pull the extracted package before it could even run `spec_lint`'s tests or
  the drift test.
- Both packages ship at one version today (`0.1.3`); every phase so far has
  changed schema and lint together, so splitting adds coordination cost per
  future change starting now, for zero current consumers.

Full tradeoff survey in the plan doc.

## Revisit condition

Re-open this decision if a concrete external consumer appears — a team,
repo, or tool that wants `trapezia-skill-gen` without also wanting the
validator's conformance-lint machinery. Trigger (a) does not need to be
re-proven; it already fired and stays satisfied.

## Roadmap status

Phase 4 is now complete (decision recorded, no code changes). Next up:
Phase 5 (dedicated type-D fixture) per the locked roadmap in the
`multi-harness-poc` memory.
