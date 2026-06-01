# Changelog

All notable changes documented here. Format per [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versioning per semver.

## [Unreleased]

## [0.1.0] - 2026-05-31

### Added
- Tier classification (T0/T1/T2 + sensitive modifier).
- Structural checks: frontmatter, README, CHANGELOG, VERSION, tests, git, NOTICE, hooks, action-items, docstrings.
- Data checks: sensitive-data separation (shape patterns + optional PHI wordlist), secret scan.
- Audit runner with JSON + markdown output and prioritized fix list.
- CLI entrypoint `trapezia-skill-validator`.
