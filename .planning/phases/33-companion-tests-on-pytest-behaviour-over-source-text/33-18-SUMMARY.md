---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 18
subsystem: testing
tags: [pytest, companion-app, migration, chain-closed, calendar-sync, poll-trigger, manual-resolutions, colour-rules, editorial-floor]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "17"
    provides: "companion/test_companion_app.py shrunk to EXPECTED_CHECK_COUNT=52 (ledger rows 267-320), companion/test_companion_app_helpers.py's encode_multipart()/seed_unresolved_prefixes()/calendar-transport fakes, and the kept-alive illustration-upload setup (the pre-upload GET, the real multipart POST, _illustration_pre_upload_render, _VENDORED_ILLUSTRATIONS_DIR) this plan's own first test re-performs and then retires along with the legacy file"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "04"
    provides: "test_i18n.py no longer importing _tca from the legacy harness — one of the two prerequisites clearing the way to delete companion/test_companion_app.py"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "19"
    provides: "companion_app_server.LegacyHarness (the still-legacy browser_ux harness's own import target, confirmed unaffected by this plan's deletion) and companion/conftest.py's app_server_in_process fixture, used throughout this plan's calendar-sync tests in place of the legacy _InProcessHarness"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "13"
    provides: "companion/test_config_page_05.py's module-level _caption_word_count_text() — this plan's own cross-check now imports and calls it directly instead of the legacy check's disk-read/ast-extract of that closed chain's module"
provides:
  - "companion/test_companion_app_05.py: 47 native pytest tests porting the companion_app chain's final 52 baseline checks (ledger rows 267-320) — the illustration-override effects after a real upload (normalization pipeline, exact-one-file write, untouched vendored original, select_illustration resolution, consolidated into one test), the illustration upload rejection paths, the manual-resolution /airlines/resolve and delete routes, the colour-rules /settings/rules/* routes, the poll-trigger cooldown sequence (consolidated) and its --geofence failure hotspot (now a tmp_path absent path), the concurrent /poll-now lock-serialization proof, the full calendar save-triggered sync family over app_server_in_process, the notifications 'send a test' route, the retired display-mode-switch removal (rewritten as a not-hasattr() battery, rubric S), the flash/title/nav i18n round trips, and the site-wide editorial floor (CFG-79) split into a calling-behaviour cross-check plus the six-route/two-language measurement test"
  - "companion/test_companion_app.py deleted outright (git rm) — the companion_app migration chain (33-14 through this plan) is CLOSED: all 320 baseline checks are accounted for (319 ported across companion/test_companion_app_01.py..05.py, 1 deleted with a stated reason from an earlier plan, 0 pending)"
  - "the companion_app ledger fragment's remaining 52 rows flipped to ported, a Part 05 closing note added, 33-ledger-check.py WITHOUT --allow-pending confirms 320/320"
  - "skypane_test_support.legacy_companion_harnesses() now returns only ('companion/test_status_pages.py', 'companion/test_browser_ux.py') — companion_app drops out of the disk-derived legacy set and the shim's parametrize list automatically"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Several old check() calls that all read state produced by ONE shared, fixed-order setup (never each other's mutations) are consolidated into one atomic pytest test, following 33-17-SUMMARY.md's own precedent: the four illustration-override-effects checks (rows 267-270) share one real upload; the four poll-trigger-cooldown checks (rows 287-290) share one server's cooldown timer across three sequential calls in a fixed order"
    - "A retired whole-repo source-text scan for identifier-shaped tokens (rubric S) is rewritten as a not-hasattr() battery across the exact modules the removal touched, rather than deleted, since the property (the identifiers no longer exist) still has an observable consequence — confirmed by grepping the WHOLE repo before writing the rewrite that none of the tokens remain in production code; the two non-identifier tokens (a retired route, a retired cookie name) are behavioural claims already covered by sibling tests in test_companion_app_04b.py, named directly in this test's own docstring rather than re-proven"
    - "A cross-file counting-rule agreement check that used to ast-extract a sibling (now-native) pytest module's function from disk is rewritten as a plain `import companion.test_config_page_05` and a direct call to both implementations across several fixtures — 'both implementations agree by calling them', never a source read; this is possible once the sibling chain (config_page) is itself closed and its function lives at module level rather than nested inside a retired main()"
    - "Every remaining companion.test_companion_app.Harness()/_InProcessHarness() call site maps 1:1 onto companion/conftest.py's make_app_server(fake_providers=True) / app_server_in_process fixtures — no bespoke harness code survives anywhere in companion/"

key-files:
  created:
    - companion/test_companion_app_05.py
  modified:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md
  # companion/test_companion_app.py: deleted (git rm)

key-decisions:
  - "The illustration-override-effects checks (rows 267-270) are consolidated into one test rather than four, since all four read state produced by the SAME single upload and none depends on another's mutation — matching 33-17-SUMMARY.md's own consolidation rule for a shared, fixed-order setup, and avoiding four separate re-uploads of the identical fixture for no behavioural gain"
  - "The poll-trigger cooldown sequence (rows 287-290) is one test, not four, because each step's assertion depends on the previous step's own mutation to the server-global cooldown timer — splitting it into separate pytest functions would depend on xdist happening to run them in file order, which 33-MIGRATION-RULES.md section 2 forbids"
  - "Row 291's --geofence hotspot uses make_app_server(extra_args=[\"--geofence\", str(tmp_path / \"absent\" / \"no-such-geofence.json\")]) instead of the legacy literal /nonexistent/no-such-geofence.json string, per the plan's own hotspot instruction and guard G6 (T-33-18-01)"
  - "Row 317 (the retired display-mode-switch scan) is rewritten as a not-hasattr() battery across companion.app/auth/layout/prefs and every companion.pages module, rather than deleted, because the property (no module still defines the seven retired identifiers) has an observable consequence and rubric S explicitly recommends this technique for 'retired symbol gone'. Confirmed by grepping the whole repo first that none of the identifier-shaped tokens remain in production code (only unrelated \"simple_mode\": False fixture dict keys in other test files); the route/cookie-name halves of the same removal are already proven behaviourally by test_companion_app_04b.py and are named, not re-proven, in this test's own docstring"
  - "Row 320's cross-file counting-rule check is split into two node ids: test_caption_word_count_text_agrees_with_test_config_page_05s_own_copy (the cross-check, now a plain import + direct call across four fixtures instead of a disk-read/ast-extract) and test_site_wide_editorial_floor_all_six_routes_both_languages (the rest of the original check, unchanged in substance). The ledger row points at the primary (editorial-floor) node id; this SUMMARY names the split-off cross-check test, per 33-MIGRATION-RULES.md section 3's 'one old check may split into several node ids' rule"
  - "The route-list parity half of row 320 reads companion.test_browser_ux_helpers.VIEW_TRANSITION_ROUTES via a plain import rather than the legacy check's own ast.parse() of that file's source — the same behaviour-over-source-text principle applied a second time in the same test"

requirements-completed: []

# Metrics
duration: ~35min (commit-to-commit across 3 tasks; full-suite verification runs added ~10min more)
completed: 2026-09-24
---

# Phase 33 Plan 18: Companion-App Migration Chain Part 05 (Chain Closed) Summary

**Migrated the companion_app chain's final 52 `check()` calls (illustration-override effects, manual-resolution and colour-rules routes, the poll-trigger cooldown sequence with its `--geofence` failure hotspot, the full calendar save-triggered sync family, the retired display-mode-switch removal rewritten as a `not hasattr()` battery, and the site-wide editorial floor) into `companion/test_companion_app_05.py`'s 47 native pytest node ids, deleted the legacy `companion/test_companion_app.py` outright, and closed its ledger fragment at 320/320 with 0 pending — the chain that started at 33-14 is now fully migrated.**

## Performance

- **Duration:** ~35 min (commit-to-commit across 3 tasks)
- **Started:** 2026-09-24T23:09:44Z (first commit)
- **Completed:** 2026-09-24T23:22:45Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 1 deleted, 1 ledger fragment updated)

## Accomplishments

- `companion/test_companion_app_05.py`: 47 pytest node ids porting the chain's final 52 baseline checks in full — the illustration-override effects after a real upload (normalization-pipeline identity, exact-one-file write, byte-identical vendored original, `select_illustration()` resolution — consolidated into one test since all four read state from the SAME shared upload); the illustration upload's four rejection paths (non-image, oversized, unknown/traversal keys, unauthenticated); the manual-resolution `/airlines/resolve` and `/airlines/manual-resolutions/{prefix}/delete` routes (auth gate, live-registry revalidation, the rejection-flash/D-03-branch/cap-fill cluster, the delete route's full contract); the colour-rules `/settings/rules/*` routes (auth gate, form placement outside `SETTINGS_FORM_ID`, add/replace, rejection paths plus registry cap, delete, fresh-per-request reads); the poll-trigger cooldown sequence (first trigger + fake-provider call-log proof + immediate cooldown + fresh second-opener session, consolidated into one test since each step depends on the previous step's own cooldown-timer mutation) and its distinct-failure-flash-key check using a `tmp_path` absent `--geofence` path instead of a literal `/nonexistent/...` string (T-33-18-01); the concurrent `/poll-now` lock-serialization proof; the full calendar save-triggered sync family over `companion/conftest.py`'s `app_server_in_process` fixture (connect/disconnect reporting and both dedicated routes' full auth/confirm contracts, the throttle-bypass spy, lock contention/release, the two independence proofs); the notifications "send a test" route; the retired display-mode-switch removal rewritten as a `not hasattr()` battery across every `companion.*` module the removal touched (rubric S, confirmed by grepping the whole repo first that none of the seven tokens remain in production code); the flash/title/nav i18n round trips; and the site-wide editorial floor (CFG-79), split into a calling-behaviour cross-check against `companion.test_config_page_05`'s own counting-rule function and the six-route/two-language measurement test itself.
- Two rubric-S rewrites replace the legacy checks' own source-text reads with calling behaviour: row 317's whole-repo `*.py`/`*.js` token scan becomes a `not hasattr()` battery (the route/cookie-name halves of the same removal are already proven by sibling tests in `test_companion_app_04b.py`, named rather than re-proven); row 320's cross-file `_caption_word_count_text()` agreement check becomes a plain `import companion.test_config_page_05` and a direct call to both implementations across four fixtures, replacing the legacy check's disk-read + `ast.parse()` + `ast.get_source_segment()` + `exec()` extraction. The same row's route-list parity half reads `companion.test_browser_ux_helpers.VIEW_TRANSITION_ROUTES` via a plain import rather than `ast.parse()`-ing that file's source.
- `companion/test_companion_app.py` deleted outright (`git rm`): its `EXPECTED_CHECK_COUNT`/`check()`/`main()`, `Harness`, `_InProcessHarness`, `_NoRedirectHandler` and every remaining helper leave the tree with it. Grepped the whole repo (not only imports — `open(`/`ast`/`Path(`/string mentions across companion, test-support, conftest, the shim, and other tests) before deleting: every remaining reference to the filename is prose in a comment or the frozen `ORIGINAL_COMPANION_HARNESSES` history tuple in `test-support/skypane_test_support.py` (used only by a guard self-test to bound the exemption set, never opened), confirmed by direct check — `legacy_companion_harnesses()` now returns `('companion/test_status_pages.py', 'companion/test_browser_ux.py')`, `test_companion_app` no longer among them.
- The ledger fragment's rows 267-320 flipped to `ported` (52 baseline checks across 47 pytest node ids), a `### Part 05 (plan 33-18) — chain closed` note added with the rubric-code split (44 B, 6 D, 2 S, 0 C/J/P/R/T, 0 deleted this part). `33-ledger-check.py companion/test_companion_app.py` **WITHOUT** `--allow-pending` confirms **320/320 baseline checks mapped (319 ported, 1 deleted, 0 pending)**.
- Full-suite verification: `SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy` (real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **2230 passed, 5 skipped, 0 failed** in 194s. The 5 skips are the documented root-sandbox `requires_non_root` skips, not failures. `ruff check .` clean across the whole tree (verified on `companion/test_companion_app*.py` directly, and no other files were touched). No new `DeprecationWarning`s from any file this plan wrote — the Pillow `getdata()` warnings in the full-suite output are pre-existing, from `server/test_panel_preview.py`/`server/test_render.py`, untouched by this plan.

## Task Commits

1. **Task 1: First half of part 05 (illustration override, manual-resolve, rules, poll-trigger)** - `5a354af` (test)
2. **Task 2: Second half of part 05 (calendar, notifications, retired scan, i18n, editorial floor)** - `91b7fb8` (test)
3. **Task 3: Delete the legacy harness, close the ledger, verify** - `5d093ef` (test)

## Files Created/Modified

- `companion/test_companion_app_05.py` - 47 native pytest node ids, the chain's closing module
- `companion/test_companion_app.py` - deleted outright (`git rm`)
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_companion_app.md` - rows 267-320 ported, Part 05 closing note added, 0 pending

## Decisions Made

See `key-decisions` in the frontmatter above: the two consolidated tests (illustration-override effects, poll-trigger cooldown sequence), the `--geofence` hotspot's `tmp_path` rewrite, the `not hasattr()` battery for the retired display-mode-switch scan, and the two-way split of the editorial floor's own cross-check.

## Deviations from Plan

None — plan executed exactly as written. The plan's own `<slice>` hotspots (the `--geofence` path and the editorial-floor cross-check/route-list-parity source reads) were handled as instructed, and the pre-deletion grep found no importer of the legacy module beyond prose comments and the frozen history tuple.

## Issues Encountered

None. The 52-row slice (rows 267-320, the LAST anchor of the whole companion_app chain) matched the plan's own anchor labels exactly, and every hand-off item 33-17-SUMMARY.md flagged for this plan (the kept-alive illustration-upload setup, the exact row range) was present and correct in the shrunk file.

## User Setup Required

None.

## Next Phase Readiness

- The companion_app migration chain (33-14 through this plan) is CLOSED: `companion/test_companion_app.py` no longer exists, all 320 of its baseline checks are accounted for (319 ported to new node ids across `companion/test_companion_app_01.py`..`_05.py`, 1 deleted with a stated reason from an earlier plan), and its ledger fragment reports 0 pending.
- `companion/test_companion_app_helpers.py` remains shared, stable infrastructure for this now-closed chain — no further plan in this chain will edit it.
- Two companion harnesses remain legacy per `skypane_test_support.legacy_companion_harnesses()`: `companion/test_status_pages.py` and `companion/test_browser_ux.py`. Phase-wide requirements TST-10/TST-12/TST-13/TST-14/TST-15 are NOT marked complete in REQUIREMENTS.md — they are phase-wide and remain open until every companion harness (including these two) is migrated and the phase's closing plans (guard tightening, closing parity/verification) land.
- No blockers. The full suite (`pytest -n auto companion test-support server stub-server deploy`, `SKYPANE_REQUIRE_BROWSER=1`) is green at 2230 passed / 5 skipped / 0 failed, and `ruff check .` is clean across the whole tree.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

`companion/test_companion_app_05.py`, the ledger fragment, and this summary
all found on disk; `companion/test_companion_app.py` confirmed deleted; all
three commit hashes (`5a354af`, `91b7fb8`, `5d093ef`) found in
`git log --oneline --all`.
