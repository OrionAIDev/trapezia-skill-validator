# Phase 4 — `trapezia_skill_spec` extraction exploration (decision-only)

**Goal:** decide whether to extract `trapezia_skill_spec` (the canonical-spec
generator) out of the `trapezia-skill-validator` repo into its own package,
now that Phase 2 has satisfied one of the two graduation triggers set at
Phase 1/2 close. This is explore → recommend → decide with Chris, not an
implementation plan — no code changes unless the decision lands on "extract."

## Refresher: what `trapezia_skill_spec` is

Lives at `src/trapezia_skill_spec/` inside this repo. Takes a canonical YAML
spec (`specs/*.yaml` — name, triggers, `invokes` list of mcp/cli invocations,
`bundle` manifest, guardrails, `model_tier`, per-harness config) and generates
harness-specific deployable artifacts:

- `schema.py` (171 lines) — dataclasses + YAML loader/validator for the spec.
- `generate.py` (171 lines) — `build_context()` + `skill_root()`, spec-driven
  rendering; also emits the Hermes `mcp_servers.snippet.yaml` registration
  block.
- `cli.py` (79 lines) — `trapezia-skill-gen` entry point; copies `bundle`
  files verbatim alongside the rendered `SKILL.md`.
- 3 Jinja2 templates (`templates/*.j2`, ~154 lines total) — one per harness
  (Claude Code, OpenClaw, Hermes).

Total: ~421 lines of Python + ~154 lines of templates. Consumed by:
`specs/*.yaml` (authored specs), `skills/<name>/` (bundle assets),
`generated/**` (committed output, drift-checked by
`tests/spec/test_regeneration.py`), and — the one internal coupling point —
`trapezia_skill_validator/spec_lint.py:14` imports `schema.SpecError` and
`schema.load_spec` directly to implement the additive canonical-spec-lint
checks (`spec.exec-token`, `spec.bundle-exists`).

## Why extraction was on the table at all

Called out as "future-extractable" from the moment the package was created
(Phase 1). The Phase 1/2 graduation-decision recommendation (recorded, not
executed) was explicit: **stay merged in `trapezia-skill-validator` until
either (a) a second real skill type is generated through it, proving the
generator generalizes beyond the first MCP-only case, or (b) another team
needs the generator standalone, without the validator.**

Phase 2 delivered `policy-form-lister` — a genuinely different skill shape
(type B: `cli` exec + `bundle`, vs. policy-check's type C: `mcp`) — through
the same generator, unmodified schema, de-hardcoded templates. **Trigger (a)
is now satisfied.** Trigger (b) has not happened: no team, repo, or
consumer outside this POC has asked to depend on `trapezia-skill-gen`
without also wanting the validator.

## The actual question this phase answers

Is trigger (a) alone now sufficient reason to extract, or is trigger (b) —
the harder bar — still the one that actually matters? Do not assume "a
trigger fired" means "extract." Weigh the real tradeoffs below.

## Tradeoffs surveyed

**For extraction now:**
- Generator is proven to generalize (mcp, cli, and the unit-tested mixed
  type-D case) — conceptually it's a complete, self-contained tool.
- Clean conceptual boundary: codegen (author a spec → get deployable
  artifacts) is a different concern from conformance linting (audit an
  existing skill against Trapezia standards).
- The package has no reverse dependency today — `schema.py`/`generate.py`
  never import from `trapezia_skill_validator`, so the split is directionally
  clean (validator → spec, never spec → validator).

**Against extraction now:**
- **Trigger (b) hasn't fired.** No second consumer exists. Extracting for a
  team that doesn't exist yet is the premature-abstraction pattern applied
  at the package-boundary level — the same "don't design for hypothetical
  future requirements" discipline that applies to code applies here.
- **Real coupling would become a packaging problem.** `spec_lint.py` imports
  `trapezia_skill_spec.schema` directly today, in-process, no version skew
  possible. Extracted, `trapezia-skill-validator` would need a hard external
  dependency on `trapezia-skill-gen` — and there's no package index for
  Trapezia-internal Python packages yet (per the laptop workspace-layout
  convention, "Shared library / package" homes are `~/dev/<name>/`,
  consumed via `pip install -e`, i.e. editable-local or git-ref, not a
  registry). That means git-ref pinning and manual version bumps for a
  dependency edge that costs nothing today.
- **Authored content doesn't cleanly split.** `specs/*.yaml`, `skills/<name>/`
  assets, and committed `generated/**` all live in this repo, exercised by
  `tests/spec/test_regeneration.py` (the drift test) side-by-side with the
  validator's own tests. Extracting the *engine* doesn't relocate this
  content — it would either need to move too (fragmenting the "one repo
  proves the whole story" evidence Phases 1–2 built) or stay here behind an
  import boundary, which is the coupling problem above restated.
- **CI duplication for no current benefit.** Today: one `pip install -e
  ".[test]"` + one `pytest -q`, 18–21s, covers both packages. Split: two
  repos, two CI pipelines, and the validator's CI would need to pull the
  extracted package (from a git ref) before it can even run `spec_lint`'s
  tests or the drift test.
- **Versioning/release coordination.** Both currently ship at one version
  (`0.1.3`) in one `pyproject.toml`. Every phase so far has changed the
  schema and `spec_lint` together (Phase 1 added `Invocation` types, Phase 2
  added `bundle`/`exec`/`usage` plus two new lint rules) — splitting means
  two version numbers and a coordination step on every such change, with no
  offsetting benefit until something actually needs to pin them
  independently.

## Recommendation

**Don't extract yet.** Trigger (a) alone proves the generator *can*
generalize — it doesn't create any actual pressure to extract (no second
consumer, no independent-versioning need, no one blocked on depending on it
without the validator). Trigger (b) is the bar that was actually meant to
gate this, and it hasn't been hit. Recommend keeping the packages merged and
treating "stay merged" as the default going forward, revisited only if a
concrete external consumer shows up.

The internal coupling (`spec_lint.py` importing `schema` in-process) is
evidence *for* staying merged, not against it — it's a real, tested
dependency that would need new packaging infrastructure (a git-ref pin at
minimum, an internal index at worst) purely to preserve, for zero new
capability.

**Decision is Chris's.** If he decides to extract anyway (e.g. for reasons
outside the trigger framework — a clean split for its own sake, or a known
near-term consumer not yet mentioned), that becomes its own TDD-plan-doc
phase with a real implementation plan; this doc does not attempt to design
that migration.
