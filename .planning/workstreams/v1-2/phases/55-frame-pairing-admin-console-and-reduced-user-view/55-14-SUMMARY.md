---
phase: 55-frame-pairing-admin-console-and-reduced-user-view
plan: 14
subsystem: companion
tags: [browser-tests, verification, deploy-docs, handoff]
requires: [55-06, 55-07, 55-10, 55-11, 55-12, 55-13]
provides:
  - companion/test_browser_console.py (22 real-browser tests of the console and the reduced user view)
  - deploy/README.md pairing, retirement and schema 3 rollback documentation
  - 55-HANDOFF.md
affects: [phase-57, phase-60]
tech-stack:
  added: []
  patterns:
    - code issued through the real byos pending path with the code chosen at test time
    - colour and motion non-regression asserted on computed styles in the browser, not on stylesheet text
key-files:
  created:
    - companion/test_browser_console.py
    - .planning/workstreams/v1-2/phases/55-frame-pairing-admin-console-and-reduced-user-view/55-HANDOFF.md
  modified:
    - deploy/README.md
    - companion/static/style.css
key-decisions:
  - "Test 6 compares resolved computed colours and motion declarations of the console pages against pages that already existed, because the behaviour-over-source guard forbids pattern matching over the stylesheet text."
requirements-completed: [AUTH-04, AUTH-05]
duration: ~2h
completed: 2026-10-31
---

# Phase 55 Plan 14: Browser proof, verification and hand-off Summary

Real-browser evidence for the console and the reduced user view (22 tests), a green full verification run, the deploy documentation and `55-HANDOFF.md`. Nothing was deployed.

## Tasks and commits

| Task | Commit | Content |
|------|--------|---------|
| 1 (fix found by the tests) | 18bc19d | `.data-card__primary > :first-child { min-width: 0; overflow-wrap: anywhere }` |
| 1 | 9bd0157 | `companion/test_browser_console.py` |
| 2 | 56a4034 | `deploy/README.md`: pairing procedure, retire and re-activate, CLI-only hard delete, `devices assign` wipes, schema 2 to 3 dry-run line, rollback caveats |
| 2 | (this commit) | `55-HANDOFF.md`, this SUMMARY |

## Browser tests (the seven behaviours)

1. 360 px and 1280 px: Fleet, Users, Locations, Audit have no sideways scroll and no visible table on the phone.
2. 44 px targets: claim, register, invite, location controls, opened confirm buttons, `<summary>` actions, audit pager links.
3. Scripts blocked: `<details>` confirm opens and closes; Register, Pair, Invite and Add location post, redirect and show a flash.
4. Both themes on all four pages; French shows Cadres, Utilisateurs, Lieux, Journal d'audit.
5. User (own frame): no link to `/fleet`, `/users`, `/audit`, `/update`, `/device`, no wake-interval, LED, runway or Poll now control in served or live DOM, tab bar is Home, Flights, Display, Health, Account; admin URLs are the unknown-path 404 with an identical main body.
6. Served pages and scripts contain no `<dialog` or `confirm(`; computed colours and transition/animation declarations of the console pages are a subset of those of existing pages, in both themes.
7. Pairing in the browser: register, code issued by `byos_server._pending_panel` (code generated at test time), two different wrong codes show the same refusal text, the right code shows "Frame paired" and creates the device.

## Verification results

- Full suite `./scripts/run-all-tests.sh` (browser included, `SKYPANE_REQUIRE_BROWSER=1`, chromium symlink dir outside the repo via `PLAYWRIGHT_BROWSERS_PATH`): 7281 passed, 8 skipped (root-permission and one openssl skips, pre-existing), coverage 96.14% against the 93.0% floor.
- `companion/test_browser_console.py`: 22 passed (also 33 passed together with the guards).
- Non-root run as `nobody` (the exact command from the brief): 399 passed, 4 skipped. The 4 skips are `companion/test_freshness_token.py` browser tests: `nobody` has no Playwright browser path (no symlink dir), so Chromium could not launch; the same tests passed in the root full run.
- `ruff check .`: all checks passed. `mypy`: no issues in 26 source files.
- `scripts/check_comment_history.py check`: exit 0. `scripts/check_function_size.py check --max 80 server stub-server`: 814 functions, none over. `scripts/check-attribution.sh`: PASS.
- `stub-server/test_phase47_freeze.py`, `stub-server/test_pairing_freeze.py`, `deploy/tests/test_backup.py`: 51 passed.
- Scope: `git diff origin/main...HEAD --name-only` (81 files: `.planning`, `companion`, `server`, `test-support`, plus this plan's `deploy/README.md`) has no path under `hardware/` or `firmware/`, no Phase 47 file, nothing under `.github/`, no deploy script or unit. `stub-server/test_phase47_freeze.py` and `stub-server/measured_fields_freeze.json` have an empty diff against `origin/main`. `companion/access.py` has an empty diff. Note: the two-dot `git diff origin/main --stat` shows 161 files with deletions because `origin/main` gained four commits (Phase 56, Phase 49 docs) after this branch was cut; the three-dot diff is the phase's own change.
- Secret scan: the repository has no secret scanner. Manual scan of the diff: `git diff origin/main...HEAD -U0 -- . ':!.planning'` filtered for quoted 8-character strings over the 30-symbol alphabet finds only five obviously fake test constants (`ABCD2345`, `EFGH6789`, `KKKK2222`, `MMMM3333`, `WXYZ7654`, none generated by the server); the pattern for Auth0 client secret assignments, PEM headers, AWS key ids and Auth0 JWT-like strings finds nothing. The new browser test generates every code with `pairing_code.generate_code()`.

## Deviations from Plan

**1. [Rule 1 - Bug] Users card pill overflowed at 360 px.** Found by test 1 on `/users`: the "Invited" pill sat 8 px beyond the viewport because the first column of `.data-card__primary` could not shrink. One rule added to `companion/static/style.css` (no new token, colour or motion). Commit 18bc19d. `companion/static/style.css` is not in this plan's `files_modified`.

**2. Test 6 implementation.** The plan said to compare against a pre-phase stylesheet hash. `companion/test_suite_guards.py` (G11) forbids pattern matching over served stylesheet text, so the test asserts in the browser that every resolved colour and every transition/animation declaration on the console pages already occurs on existing pages (with the shared `calendar-disconnect-btn` class probed on the reference page, since it only renders on some pages). The `<dialog` and `confirm(` check on served pages and scripts is on bytes, as planned.

**3. Test 7 setup.** The code is issued by calling the real `byos_server._pending_panel` in-process with `generate_code` patched inside a `monkeypatch.context()` to a value generated by the test, so the test can type it; the real rendering, hashing, storage and audit path runs.

## Known Stubs

None.

## Threat Flags

None. T-55-14-01 to -03 and -05 mitigated (scan above, user-DOM test, scope check, no skipped or weakened test).

## Notes for the owner

See `55-HANDOFF.md` sections C and D. In short: no deploy happened; the schema 3 rollback caveat, `devices assign` wiping, the Pillow import in byos, the redraw cost, the red pairing header band to confirm on the panel and the flaky `stub-server/test_ota_offer.py` port race are all listed there. `origin/main` has moved on since the branch was cut and the branch is not rebased.

## Self-Check: PASSED

Files present: `companion/test_browser_console.py`, `55-HANDOFF.md`, this SUMMARY. Commits 18bc19d, 9bd0157, 56a4034 exist in `git log`.
