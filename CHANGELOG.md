# Changelog

All notable changes documented here. Format per [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per semver.

## [Unreleased]

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
