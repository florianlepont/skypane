---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 14
subsystem: testing
tags: [pytest, companion-app, auth, layout, css-structural-parsing, root-safety, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_companion_app.md fragment (scaffolded with all 320 rows pending) this plan's rows build on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's app_server/make_app_server/module_app_server_factory fixtures and test-support/companion_app_server.py's http_request/login/served_stylesheet — this plan's WR-11 pair and CSS checks use them instead of the legacy Harness"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for()/rules_with_selector() (the 5 checks that used to read style.css from disk) and companion/test_suite_guards.py's TST-10/12/13/14 guard, which now scans this plan's two new modules"
provides:
  - "companion/test_companion_app_helpers.py: FakeCalendarResponse/make_calendar_transport/stubbed_calendar_transport/fake_public_hostname (calendar-sync test doubles) and seed_unresolved_prefixes (poll-state seeding), __test__ = False, front-loaded for 33-15..33-18's calendar-sync and manual-resolution sections"
  - "companion/test_companion_app_01.py: 52 native pytest tests porting companion/test_companion_app.py's original check() calls #1-#50 (companion/auth.py's full contract, the first half of companion/layout.py's contract) plus the two WR-11 os.chmod checks pulled forward out of order, now root-safe with @requires_non_root"
  - "companion/test_companion_app.py shrunk: EXPECTED_CHECK_COUNT collapsed from a ~811-line reassignment history to one authoritative line (268 pending), part 01's checks and the two WR-11 checks removed from main(), the now-dead _sign_with_secret()/hmac import removed; Harness/_InProcessHarness/http_request/TEST_PASSWORD still exported"
  - "the companion_app ledger fragment's rows 1-50 and 279-280 flipped to ported, Part 01 note added"
affects: [33-15, 33-16, 33-17, 33-18]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The four style.css-reading checks that survive as behaviour assertions now resolve final computed declarations through companion_markup.declarations_for()'s 'last rule wins, same at-rule context' merge instead of a literal multi-line string search — this is a strictly more faithful model of the real CSS cascade for same-specificity selectors (it would catch a regression the old literal-text search could miss, e.g. a later same-specificity legend{} rule quietly re-declaring font-weight) while also surviving any future reformatting of the stylesheet"
    - "The two WR-11 root-unsafe checks were pulled forward out of their original position (deep in the still-legacy manual-resolution section, original lines ~10315-10412) into this plan's part-01 module, per 33-MIGRATION-RULES.md's rubric T out-of-order-pull exception — the legacy harness's own os.chmod calls are gone entirely (`grep -c os.chmod` is 0), so the shim now runs companion_app green as root instead of red (32-REVIEW.md IN-05)"
    - "companion/test_companion_app_helpers.py is deliberately front-loaded with calendar-transport/public-hostname/seeding doubles that part 01's own tests barely use (only seed_unresolved_prefixes, for the WR-11 pair) — the plan's own Task 1 instruction anticipates 33-15..33-18's calendar-sync and manual-resolution sections needing them, so the whole chain never has to duplicate these doubles a second time"

key-files:
  created:
    - companion/test_companion_app_helpers.py
    - companion/test_companion_app_01.py
  modified:
    - companion/test_companion_app.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md

key-decisions:
  - "_sign_with_secret() (used only by part 01's own 7 auth checks) is kept LOCAL to companion/test_companion_app_01.py rather than moved to the shared helpers module, following 33-09's precedent for single-use helpers; the now-orphaned copy in the legacy file, plus its now-unused `import hmac`, was deleted outright rather than left as dead code"
  - "The calendar-transport fakes/public-hostname fake/seeding helper moved into companion/test_companion_app_helpers.py are renamed without their leading underscore (FakeCalendarResponse, make_calendar_transport, stubbed_calendar_transport, fake_public_hostname, ics_body, seed_unresolved_prefixes) — they are now public shared API for a whole migration chain, not module-private implementation details, mirroring 33-09's own _write_device_config -> write_device_config rename"
  - "The 5 CSS-reading checks share one module-scoped served_css fixture (module_app_server_factory(fake_providers=True) + served_stylesheet()) rather than 5 separate function-scoped servers — none of them mutate server state, matching 33-MIGRATION-RULES.md section 2's 'read-only GETs may share a module-scoped server' guidance and this module's own convention of fake_providers=True for every test_companion_app.py-derived server (RESEARCH Pitfall 4)"
  - "The forbidden-selector check (--font-serif never reaching dense/tabular content) uses companion_markup.rules_with_selector() (returns [] for a selector with no rule at all, in ANY at-rule context) rather than declarations_for() (which requires an exact at_rules match and raises KeyError on a total miss) — this is closer to the original's intent of catching --font-serif creeping in anywhere for that selector, not just at the top level"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 17min
completed: 2026-09-24
---

# Phase 33 Plan 14: Companion-App Helpers, Part 01, and the WR-11 Root-Safety Fix Summary

**Started the 5-plan companion_app migration chain: built the chain's shared calendar/hostname/seeding test-double module, migrated the first 50 of `companion/test_companion_app.py`'s 320 checks (the whole `companion/auth.py` contract plus half of `companion/layout.py`'s) to native pytest, and pulled the two root-unsafe WR-11 `os.chmod` checks forward so the legacy harness finally runs green as root.**

## Performance

- **Duration:** ~17 min (commit-to-commit)
- **Started:** 2026-09-24T11:21:05Z (first commit)
- **Completed:** 2026-09-24T11:37:50Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `companion/test_companion_app_helpers.py`: a new `__test__ = False` module holding the companion_app chain's shared calendar-transport fakes (`FakeCalendarResponse`, `make_calendar_transport`, `stubbed_calendar_transport`), the public-hostname DNS fake (`fake_public_hostname`), an iCal-body builder (`ics_body`), and the poll-state seeding helper (`seed_unresolved_prefixes`) — copies of the legacy file's own originals, renamed to drop their leading underscore now that they are shared public API. Deliberately excludes `Harness`/`_InProcessHarness`/`http_request`/`_NoRedirectHandler`/cookie/login helpers and any `tempfile` use, per the plan's own instruction; the legacy file keeps its own originals of those.
- `companion/test_companion_app_01.py`: 52 native pytest tests — the full `companion/auth.py` contract (password checking, session tokens, cookie security flags, the insecure-cookies opt-out, login throttling, token revocation), the first half of `companion/layout.py`'s contract (HTML escaping, `page_shell()`'s document shape/nav/flash-banner/theme handling, `status_dot`/`data_table`/`sidebar_nav`/icon-sprite/`stat_tile`/`card_status_class`), 5 checks that used to read `companion/static/style.css` from disk and now fetch it from a running `companion/app.py` via `served_stylesheet()` and assert structurally through `companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`, and the two WR-11 `os.chmod` checks pulled forward from the still-legacy manual-resolution section with `@requires_non_root`.
- `companion/test_companion_app.py` shrunk: the ~811-line `EXPECTED_CHECK_COUNT` reassignment history (79 → 320 across every phase since 06.6.4.1) collapsed into one `EXPECTED_CHECK_COUNT = 268` line immediately above `def main()`; part 01's 50 checks and the two WR-11 checks removed from `main()`; the now-orphaned `_sign_with_secret()` helper and its `import hmac` deleted. `Harness`/`_InProcessHarness`/`http_request`/`TEST_PASSWORD` are still exported (the 3 still-legacy browser harnesses and `test_i18n.py` import them until 33-19/33-04). The shrunk harness runs 268/268 standalone and through `companion/test_legacy_harness_shim.py -k companion_app` **as root** — the first time this harness has run green as root since 32-REVIEW.md's IN-05 was opened.
- Verified the WR-11 pair's root-safety both ways in this sandbox: `pytest -k "resolve_post_redirects_manual_save_failed or delete_post_redirects_manual_delete_failed"` shows both tests SKIPPED as root (euid 0) and PASSED under `runuser -u nobody` (no world-readable venv copy needed here — `namei -l` confirmed every path segment from `/` down to `server/.venv/bin/python3` is already `o+rx`, unlike 32-15's environment).
- The ledger fragment's rows 1-50 and the two out-of-order rows 279-280 flipped to `ported`, pointing at real `companion/test_companion_app_01.py::test_*` node ids; a `### Part 01 (plan 33-14)` note added recording the rubric-code split (46 B, 4 C, 0 deletions). `33-ledger-check.py --allow-pending` confirms 320/320 baseline checks accounted for (52 ported, 268 pending).
- Full-suite sanity beyond the plan's own scoped verification: `pytest -n auto companion test-support server stub-server` as root (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — 1034 passed, 1 failed, 5 skipped. The one failure is `test_status_pages`'s pre-existing `anomaly_active("/nonexistent/...")` root-sandbox artifact, already classified in `33-BASELINE/INDEX.md` and explicitly out of scope for this plan (33-25's job). `test_companion_app`'s two `os.chmod` failures — present in every prior plan's full-suite run this phase — are **gone**, replaced by 2 correctly-skipping WR-11 tests.

## Task Commits

1. **Task 1: Helpers module and the first half of part 01** - `355cee5` (test)
2. **Task 2: Second half of part 01 and the WR-11 root-safe pair** - `0d831df` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify as root** - `9d9c644` (test)

## Files Created/Modified

- `companion/test_companion_app_helpers.py` - shared calendar/hostname/seeding test doubles for the companion_app chain
- `companion/test_companion_app_01.py` - 52 native pytest tests (part 01 + the WR-11 pair)
- `companion/test_companion_app.py` - shrunk to `EXPECTED_CHECK_COUNT = 268`, part-01/WR-11 checks and the dead `_sign_with_secret()` removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md` - rows 1-50/279-280 flipped, Part 01 note added

## Decisions Made

See `key-decisions` in the frontmatter above: keeping `_sign_with_secret()` local to the new module (single-use) while deleting it and its import from the legacy file, renaming the moved calendar/hostname/seeding helpers to drop their leading underscore now that they are shared API, sharing one module-scoped `served_css` fixture across the 5 CSS checks, and using `rules_with_selector()` (not `declarations_for()`) for the "forbidden selector never carries --font-serif" check so a miss in any at-rule context is caught, not just at the top level.

## Deviations from Plan

None — plan executed as written. Two judgement calls worth naming explicitly (both anticipated by the plan's own instructions, not scope additions):

- The ledger checker (`33-ledger-check.py`) expects the "New node id / reason" table cell to hold the bare node id string, not one wrapped in Markdown backticks — an initial pass wrapped every new target in backticks (matching this SUMMARY's own prose style) and the checker correctly failed with "not found in `pytest --collect-only` output" for all 52 rows. Fixed by stripping the backticks from the table cells before the checker run that is recorded above; caught before commit, never landed in a failing state.
- `companion/test_companion_app_helpers.py`'s docstring originally named the excluded plumbing (`_NoRedirectHandler`/`tempfile`) literally, which the acceptance criterion's own `grep -cE "class Harness|class _InProcessHarness|def http_request|_NoRedirectHandler|tempfile"` check (correctly) flagged as a non-zero match in prose. Reworded the docstring to describe the exclusion without naming the literal identifiers; re-verified the grep returns 0 for both new files.

## Issues Encountered

None beyond the two judgement calls above, both caught and fixed before any commit.

## User Setup Required

None.

## Next Phase Readiness

- 33-15..33-18 (the chain's remaining 4 plans) can extend `companion/test_companion_app_helpers.py` and continue shrinking `companion/test_companion_app.py`'s single `EXPECTED_CHECK_COUNT` line (currently 268, from the wrapping-midnight quiet-window/health-nav-dot section onward).
- `Harness`/`_InProcessHarness`/`http_request`/`TEST_PASSWORD` remain exported from the legacy file — 33-18 (the chain's last plan) is the one that deletes the file outright, once 33-19 (browser harnesses) and 33-04 (`test_i18n.py`) have repointed their own imports.
- 32-REVIEW.md IN-05 (companion harnesses red as root) is now half-closed: `test_companion_app` is root-green; `test_status_pages`'s half is still open, owned by 33-25.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`companion/test_companion_app_helpers.py`,
`companion/test_companion_app_01.py`, `companion/test_companion_app.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md`)
plus this summary, and all 3 commit hashes (`355cee5`, `0d831df`, `9d9c644`) found in
`git log --oneline --all`.
