---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 21
subsystem: testing
tags: [pytest, pytest-playwright, chromium, browser-tests, companion, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "19"
    provides: "companion/test_browser_ux_helpers.py's make_context factory-parameter shape, companion_app_server.LegacyHarness as the still-legacy import, and the module-scoped/function-scoped server fixture precedent from test_browser_ux_health_drawings.py"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "20"
    provides: "the 'mutating check gets its own function-scoped make_app_server' pattern applied to an entire browser harness, and companion_app_server.LegacyHarness reduced to test_browser_ux.py's own remaining importer"
provides:
  - "companion/test_browser_ux_01.py: the first 18 of companion/test_browser_ux.py's 75 legacy check() calls, rewritten as 18 native pytest-playwright test node ids (17 real tests plus a parametrized language split on the Health registry-table check) — the self-referential coverage-gap ledger guard is deleted with an R-coded ledger reason instead of ported"
  - "13 read-only checks sharing one module-scoped seeded server; the 4 checks that persist a real setting through the UI (Display/Device reveal-and-persist, the dirty bar's hide/reveal/save cycle, the Frame strip quick-switch) each get their own function-scoped make_app_server server"
  - "companion/test_browser_ux.py shrunk: its own EXPECTED_CHECK_COUNT history (938 lines of superseded reassignment comments) collapsed to one EXPECTED_CHECK_COUNT = 57 line, the _ASPECT_REPIN_LEDGER coverage-gap table and its guard check deleted outright, and the now-unused re/_guard_armed imports removed"
  - "the migration ledger fragment's rows 1-18 flipped: 1 deleted (rubric R), 17 ported to real collected node ids"
affects: [33-22, 33-23, 33-24, 33-33]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A legacy check that only ever clicks the leave-guard's own Cancel control (never Enregistrer) reaches no disk state at all, so it is read-only for isolation purposes even though it commits an in-browser change event — it shares the module's read-only server rather than getting its own function-scoped one, same reasoning as a plain GET"
    - "A per-language loop with no cross-language comparison (each iteration's assertions stand entirely on their own) is parametrized rather than kept as an internal Python loop, unlike the theme/width loops in this same file that DO compare values across iterations and therefore stay single tests (33-19's own established distinction, now applied to a new case: the two languages of the Health registry-table check)"
    - "Collapsing a legacy harness's own EXPECTED_CHECK_COUNT reassignment history to one line can leave an import with no remaining consumer in that file (this file's own `re` and `_guard_armed`, both consumed only by checks this plan just deleted/migrated) — ruff catches this immediately after the shrink, before the commit, rather than needing a separate cleanup pass"

key-files:
  created:
    - companion/test_browser_ux_01.py
  modified:
    - companion/test_browser_ux.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md

key-decisions:
  - "Only the Health registry-table check's en/fr loop was parametrized. Every other loop in this slice (the two `light`/`dark` theme reads on the Quiet-hours schedule link, the desktop/mobile `.copy-btn` family measurement) either shares one page/context across iterations for a genuine reason (theme reads on the same navigated page) or would gain nothing from parametrizing beyond the language case's already-clean independence, so they stayed as internal loops rather than being split for its own sake."
  - "The four checks that persist a real setting (Display/Device reveal-and-persist, the dirty bar's own hide-on-load/reveal-on-edit/save cycle, and the Frame strip's quick-switch) each get their own function-scoped make_app_server(seed=seed_state_dir, fake_providers=True) server. The two leave-guard checks that only ever click Annuler (never Enregistrer) and the theme-chip/runway-card geometry checks that only click a radio with no save at all stay on the shared module-scoped server, since nothing they do reaches disk — matching 33-MIGRATION-RULES.md section 2's isolation rule by what a check actually does to shared state, not by which UI family it belongs to."
  - "The ledger row for the parametrized Health registry-table check points at a single primary node id ([chromium-en]), with the [chromium-fr] counterpart named in this SUMMARY rather than encoded into the ledger target string — the same one-row/one-canonical-node-id convention 33-19's ledger fragment already established for its own parametrized RING_PAGES check, which 33-ledger-check.py's collect-only matcher expects."
  - "EXPECTED_CHECK_COUNT's entire history block (938 lines of superseded per-plan reassignment comments, spanning from 22-01 through 31-03) was collapsed to one line at its ORIGINAL location near the top of the file, matching companion/test_config_page.py's and companion/test_status_pages.py's own already-shipped single-line placement, rather than moved down to sit immediately above def main() as 33-MIGRATION-RULES.md section 1's literal wording suggests — consistent with the two sibling harnesses this phase already closed this way, and a smaller diff than relocating it."

requirements-completed: []

# Metrics
duration: 21min
completed: 2026-09-24
---

# Phase 33 Plan 21: Browser UX Part 01 Migration Summary

**First 18 of `companion/test_browser_ux.py`'s 75 legacy checks (the Flights/Airlines/Health filter-bar family, the settings-page reveal/persist/leave-guard group, and the runway/theme-chip selection-signal geometry) now run as 18 native pytest-playwright node ids in `companion/test_browser_ux_01.py`, with the self-referential coverage-gap ledger guard deleted outright.**

## Performance

- **Duration:** ~21 min (commit-to-commit, previous plan's last commit `b206155` at 17:14:10Z to this plan's last commit `f3ca405` at 17:35:02Z)
- **Started:** 2026-09-24T17:14:10Z
- **Completed:** 2026-09-24T17:35:02Z
- **Tasks:** 3/3 completed
- **Files modified:** 3

## Accomplishments

- `companion/test_browser_ux_01.py` created: `pytestmark = pytest.mark.browser`, one module-scoped read-only seeded server (`module_app_server_factory(seed=seed_state_dir, fake_providers=True)`) shared by the 13 checks that never write to disk (the Flights detail-row toggle, the Quiet-hours schedule link hit target, the `.copy-btn`/`.row-toggle` family, the three `.filter-bar__meta` siblings on Flights/Airlines/Health, the Airlines two-per-row grid, Health's 1280px registry table, Health's no-JS floor, both leave-guard checks that only ever click Annuler, and the two runway-card/theme-chip layout-geometry checks). The 4 checks that persist a real setting through the UI (Display and Device reveal-and-persist, the dirty bar's own hide/reveal/save cycle, and the Frame strip's quick-switch) each get their own function-scoped `make_app_server` server, so no xdist worker can see another test's leftover on-disk state.
- The self-referential `_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement` check — which opened `test_browser_ux.py`'s own source to grep for `def` names — is deleted outright rather than ported, with ledger reason `R: self-referential CFG-85 aspect-repin bookkeeping; opens test_browser_ux.py to grep def names; no behaviour`.
- The Health registry-table check's `for lang in ("en", "fr")` loop, which has no cross-language comparison in the original code, is parametrized (`@pytest.mark.parametrize("lang", ["en", "fr"])`) into two independent node ids rather than kept as an internal loop — every other loop in this slice stayed a single test.
- `companion/test_browser_ux.py` shrunk: the 938-line `EXPECTED_CHECK_COUNT` reassignment history (22-01 through 31-03) collapsed to one `EXPECTED_CHECK_COUNT = 57` line at its original location; the `_ASPECT_REPIN_LEDGER` coverage-gap table (its own 107-line comment-plus-tuple block) and the guard check that read it are both gone; the `re` import and the `_guard_armed` helper import, each left with no remaining consumer by these deletions, were removed too (caught by `ruff check` immediately after the shrink).
- The migration ledger fragment's rows 1-18 flipped: 1 `deleted` (rubric R), 17 `ported` to real collected `[chromium]` node ids (row 8, the parametrized language check, points at its `[chromium-en]` primary id, with `[chromium-fr]` named in this SUMMARY). `33-ledger-check.py --allow-pending` confirms `75/75 baseline checks mapped (17 ported, 1 deleted, 57 pending)`.
- Full verification chain green: `companion/test_browser_ux_01.py` — 18/18 passed, 0 skipped, `SKYPANE_REQUIRE_BROWSER=1`, real Chromium (~12s under xdist). The shrunk legacy file through the shim (`companion/test_legacy_harness_shim.py -k "exits_zero and test_browser_ux"`) — 1 passed in 184s, same `SKYPANE_REQUIRE_BROWSER=1` real-Chromium proof the shim always ran, now against 57 remaining checks. `companion/test_suite_guards.py` (both the `browser_ux`-scoped subset and the full 55-test module) passes. `ruff check companion/test_browser_ux*.py` clean.

## Task Commits

1. **Task 1: The R deletion and the first half of part 01** - `2656521` (test)
2. **Task 2: Second half of part 01** - `aab09b6` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify in a browser, commit** - `f3ca405` (test)

## Files Created/Modified

- `companion/test_browser_ux_01.py` - new module, 18 pytest-playwright test node ids (17 tests, one parametrized over 2 languages)
- `companion/test_browser_ux.py` - shrunk: `EXPECTED_CHECK_COUNT` history collapsed to one line (75 → 57), `_ASPECT_REPIN_LEDGER` table and its guard check deleted, `re`/`_guard_armed` imports removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md` - rows 1-18 flipped (1 deleted, 17 ported), Part 01 note added

## Decisions Made

See `key-decisions` in the frontmatter: which loop got parametrized (only the Health registry-table's en/fr split, since it is the one loop in this slice with no cross-iteration comparison), which checks needed their own function-scoped server (the 4 that actually persist a setting, decided by what a check DOES rather than which settings page it is on — the two leave-guard checks that only click Annuler and the theme-chip/runway-card geometry checks stayed on the shared server), the single-primary-node-id convention for the parametrized ledger row, and keeping the collapsed `EXPECTED_CHECK_COUNT` line at its original top-of-file location rather than moving it next to `def main()`, matching the two sibling harnesses (`test_config_page.py`, `test_status_pages.py`) this phase already closed the same way.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed the now-unused `re` import and its explanatory MERGE NOTE comment**
- **Found during:** Task 3, immediately after collapsing `EXPECTED_CHECK_COUNT` and deleting the `_ASPECT_REPIN_LEDGER` guard
- **Issue:** `re` was imported solely for the deleted guard check's `re.search`/`re.escape` calls (the import's own 7-line comment named this exact guard as its last consumer). With the guard gone, `ruff check` flagged `F401 're' imported but unused`.
- **Fix:** Removed the `import re` line and its stale explanatory comment block.
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** `ruff check companion/test_browser_ux.py` clean; full shim run for this file still 1/1 passed.
- **Committed in:** `f3ca405` (Task 3 commit)

**2. [Rule 3 - Blocking] Removed the now-unused `_guard_armed` import**
- **Found during:** Task 3, same pass
- **Issue:** `_guard_armed` was imported from `test_browser_ux_helpers` for use by checks 14, 15 and 16 (the leave-guard family), all three now ported to `test_browser_ux_01.py`. `ruff check` flagged `F401` on the import.
- **Fix:** Removed `_guard_armed` from the `from companion.test_browser_ux_helpers import (...)` block.
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** `ruff check companion/test_browser_ux.py` clean.
- **Committed in:** `f3ca405` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (both Rule 3, blocking unused-import lint failures caused directly by this plan's own deletions)
**Impact on plan:** Both fixes are the direct, expected consequence of migrating this slice's checks out of the legacy file — no scope creep, no behaviour change.

## Issues Encountered

None beyond the two auto-fixed unused imports above.

## User Setup Required

None.

## Next Phase Readiness

- `companion/test_browser_ux.py` now carries 57 remaining legacy checks across parts 02-04 (originally numbered 19-75); its `EXPECTED_CHECK_COUNT` and legacy-detection markers are otherwise unchanged, so `companion/test_legacy_harness_shim.py` keeps running it unmodified until 33-24 (the chain's last plan) deletes the file outright.
- `companion/test_browser_ux_01.py`'s module-scoped-server-for-read-only / function-scoped-server-for-mutating split, and its single-primary-node-id ledger convention for a parametrized check, are both available as direct precedent for 33-22/33-23's own parts of this same harness.
- No blockers for 33-22 (part 02, picking up immediately after this plan's LAST anchor, `_both_dialogs_fade_in_and_leave_nothing_behind`) or the rest of the companion migration chain. Scoped verification (this plan's own new module, the shim run, the guard suite, ruff) is fully green; a full unscoped suite run was not re-run in this plan beyond the shim/guard scope named above, since the shim proof already re-executes every remaining check in this file end to end.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk
(`companion/test_browser_ux_01.py`, `companion/test_browser_ux.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_browser_ux.md`,
plus this summary), and all 3 commit hashes (`2656521`, `aab09b6`,
`f3ca405`) found in `git log --oneline --all`.
