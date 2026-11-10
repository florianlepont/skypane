---
phase: 63-fast-ci
plan: 02
status: executed
requirements: [CIS-01, CIS-02, CIS-03, CIS-04]
---

# Plan 63-02 Summary

The single test job is split into `static`, `tests-core` and `tests-browser`, plus an aggregate job that keeps the id `test` and the name `Lint, test, coverage, attribution`.

## Delivered

- `scripts/ci_gates.py` (+ `test-support/test_ci_gates.py`, 6 tests): JUnit totals gate (no failure or error, executed at least 12,821, skipped at most 0).
- `.github/workflows/ci.yml`: `static` (all former static steps, attribution, shard-completeness check), `tests-core`, `tests-browser` (Playwright steps as before), each uploading `.coverage` and its JUnit file; `test` fails unless every needed job succeeded, combines coverage, applies the unchanged `fail_under` and runs the totals gate. `deploy` and its approval are untouched. New actions are pinned by commit SHA: `actions/upload-artifact` v7.0.1 and `actions/download-artifact` v8.0.1 (lightweight tags, SHAs read with `git ls-remote`).

## Results

Critical path 22.5 min (from 27.4); see `63-TIMINGS.md` for every number and the negative proofs.

## Notes

- The executed floor stays 12,821 (the owner's criterion). The tree now executes 13,816, so the gate is looser than it could be; raising it to the current count would make a PR that deletes tests fail until the constant is lowered on purpose. This is the owner's choice and is not changed here.
- While validating, an `--amend` of the throwaway commit was refused by the remote (non-fast-forward) and fixed with a normal revert commit; no remote history was rewritten.
