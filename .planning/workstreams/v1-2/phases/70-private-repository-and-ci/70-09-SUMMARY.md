---
phase: 70-private-repository-and-ci
plan: 09
subsystem: docs
tags: [docs, private-repository, compliance]
requirements: [PRV-01, PRV-02, PRV-03]
key-files:
  modified:
    - README.md
    - SECURITY.md
    - CONTRIBUTING.md
    - COMPLIANCE.md
    - deploy/README.md
    - deploy/tests/test_docs.py
metrics:
  completed: 2026-11-25
---

# Phase 70 Plan 09: Private-repository documents Summary

README licence section, SECURITY, CONTRIBUTING, COMPLIANCE ("Repository hosting and CI") and deploy/README ("Private repository (GitHub Free plan)") now describe the private setup, with a doc test pinning the deploy section.

## Commits

- 952d95e: README, SECURITY, CONTRIBUTING, COMPLIANCE
- 94a09af: deploy/README section and test_docs.py test

## Facts kept honest

- Self-hosted runner described as the intended setup: kit exists, runner not installed, `CI_RUNS_ON` unset.
- Signing key not held by GitHub; deploy manual via `deploy.yml` with repository-level secrets; owner chose dedicated-key-only.
- Licence terms untouched; `efafc89` sentence kept (added "including copies already taken while the repository was public").
- Private-repository text is written as what applies after the visibility flip.

## Deviations from Plan

- `70-MEASUREMENTS.md` does not exist, so the COMPLIANCE "charge status" line was written from 70-RESEARCH.md (charge announced, postponed, no date; changelog of 2025-12-16; read again in November 2026) instead of copied.
- SECURITY.md/CONTRIBUTING.md/README now point to the owner's profile (github.com/florianlepont, already named in README) instead of GitHub private vulnerability reporting and public issues, since neither exists on a private Free repository as a public route. No new contact route added.

## Verification

- deploy/tests plus stub-server/test_phase47_freeze.py: 399 passed, 1 skipped (pre-existing openssl skip).
- companion/test_compliance_credits.py + test_docs.py: 26 passed.
- server golden render tests: 94 passed. ruff and check_comment_history clean.
- Not run: full suite; venv was taken from /home/user/skypane/server/.venv.

## Self-Check: PASSED
