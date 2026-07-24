# Changelog

All notable changes documented here. Format per [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per semver.

## [Unreleased]

## [0.1.3] - 2026-07-24

### Added
- Added `mypy.strict` check (T1+) — runs `mypy --strict` against a skill's `scripts/` directory, FAILs with the mypy error output on any error. PASSes when `scripts/` is absent or holds no `.py`/`.pyi` files (e.g. shell-only scripts); WARNs if `mypy` isn't installed. Added `mypy>=1.8` to the `test` optional-dependency extra.

## [0.1.2] - 2026-06-01

### Added
- Added `block_content_regexes` + `matches_block_content()` — block-grade subset (SSN, MRN) for hard guards, excluding the broad advisory ISO-date pattern.

## [0.1.1] - 2026-06-01

### Fixed
- `frontmatter.name` no longer fails when auditing via a relative path (e.g. `audit .`); the skill root is resolved to an absolute path.
- `frontmatter.desc` trigger detection now accepts "Use whenever", "Use this when", "Use this skill when", not only the literal "Use when".
- File-walking checks (`docstrings.present`, `no_action_items`) no longer recurse into `.venv`, `site-packages`, and other vendored/cache dirs; skip-dir set centralized in `walk.py`.

## [0.1.0] - 2026-05-31

### Added
- Tier classification (T0/T1/T2 + sensitive modifier).
- Structural checks: frontmatter, README, CHANGELOG, VERSION, tests, git, NOTICE, hooks, action-items, docstrings.
- Data checks: sensitive-data separation (shape patterns + optional PHI wordlist), secret scan.
- Audit runner with JSON + markdown output and prioritized fix list.
- CLI entrypoint `trapezia-skill-validator`.
