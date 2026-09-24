---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 26
subsystem: testing
tags: [pytest, svg-parsing, css-parsing, regularity-grid, i18n, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_status_pages.md fragment this plan's rows 38-85 build on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture (used here, for the first time in this chain, to fetch a served stylesheet/JS asset for a read-only check)"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's declarations_for()/rules_with_selector()/css_rules() (used here for the first time in the status-pages chain) and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "25"
    provides: "companion/test_status_pages_helpers.py's seeding/formatting wrappers and stat_tile_slices(); the module-split naming convention (test_status_pages_NN.py) and the substring/regex-over-rendered-markup assertion style this plan mostly keeps"
provides:
  - "companion/test_status_pages_02.py: 62 native pytest node ids porting the original harness's check() calls #38-#85 (part 02 of the 7-plan chain) — battery_sparkline_svg()'s axis-label/flat-series/wiggle/clamp/area/mark/low-battery-threshold contract, the 24-07-PLAN.md check-in regularity grid (draw.cell_class()/regularity_grid(), Health's regularity caption and its four 'moved, not cut' disclosure cases), the daily-mode sparkline date/average-label contract, the D-05/B4 Paris-local-time sweep, the D-03/A-21 Device/Pipeline/Corroboration tile verdicts, the X8/C1 one-tile-anatomy sweep and compact empty_state() variant, the D-06/B16 resolution-rate singular form, and the B2 never-ran-pipeline neutral state"
  - "the first served-CSS/served-JS checks in the status-pages chain: a module-scoped read-only server (_module_server/css_text/battery_trend_js fixtures) replaces two raw style.css reads and one raw battery-trend.js read"
  - "companion/test_status_pages.py shrunk further: EXPECTED_CHECK_COUNT collapsed from 279 to 231; part 02's 48 checks and the closures/constants only they used removed from main(); _tile_slice_by_caption() promoted to module scope because a later, still-pending section calls it"
  - "the status-pages ledger fragment's rows 38-85 flipped to ported (7 of them pointing at a parametrized test's primary node id, siblings recorded below); 33-ledger-check.py --allow-pending confirms 317/317 baseline checks accounted for (86 ported, 231 pending)"
affects: [33-27, 33-28, 33-29, 33-30, 33-31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The first served-stylesheet/served-JS checks in the status-pages chain use a single module-scoped read-only AppServer (companion/conftest.py's module_app_server_factory) fetched once per test session via css_text/battery_trend_js fixtures, since none of this part's checks mutate server state — declarations_for()/rules_with_selector()/css_rules() replace regex-over-disk-CSS, and served_asset() replaces a raw JS file read"
    - "A check whose legacy body was a for-loop over cases (device/pipeline/corroboration tile severities, the two-language 'Only one saw it' pair, the seeded/fresh tile-anatomy sweep, the four check-in-disclosure cases, and the resolution-rate singular/plural matrix) becomes a @pytest.mark.parametrize test per this plan's own Task 1 instruction, with one ledger row still pointing at the primary parametrized node id and the SUMMARY (this file) naming the sibling ids — the TST-12 rubric's 'one old check splits into several tests' clause, not the loop-preserving style 33-25 used for cases that stayed inside one function body"
    - "A source-text assertion embedded inside an otherwise-behavioural check (proving a constant is 'never re-typed' by reading the module's own __file__, or proving no interval arithmetic exists by reading a function's inspect.getsource()) is dropped in place rather than deleting the whole check when the check's other assertions are still real behaviour proofs (rubric S, no observable rendered consequence) — narrower than 33-25's precedent of rewriting a whole check, because here only one clause among several needed to go"
  key-files:
    created:
      - companion/test_status_pages_02.py
    modified:
      - companion/test_status_pages.py
      - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md

key-decisions:
  - "Two raw style.css reads (the .battery-trend-section svg:not(.icon) height-declaration/no-@media-override check, and the .sparkline-area fill/opacity plus .sparkline__area absence check) and one raw battery-trend.js read are rewritten against SERVED bytes (a module-scoped read-only companion/app.py, since neither check mutates server state) instead of moving to a per-test function-scoped server — matching 33-MIGRATION-RULES.md section 2's explicit read-only/GET-only carve-out"
  - "_sparkline_low_battery_threshold_is_read_from_battery_py_and_labelled()'s open(health_page.__file__).read() clause (proving the millivolt threshold is never re-typed into health_page.py's own source) and _every_cell_verdict_is_the_classifiers_own_output()'s inspect.getsource(fn) sweep (proving no interval-arithmetic literal exists in two builder functions' source) are both dropped in place — TST-12 rubric S, no observable rendered consequence — while every other assertion in both checks (the threshold's VALUE/placement reading from companion/battery.py; the co_names reuse sweep proving classify_check_in_gap() is actually called) is kept and still counted as ported"
  - "_tile_slice_by_caption() is promoted from a main()-local closure to a module-level function in companion/test_status_pages.py (beside its existing sibling _stat_tile_slices()) rather than re-defined at the top of whichever later part first needs it, because Task 3's own standalone-harness run caught it being called by a check this plan's slice did not include (a still-pending later section) — a live example of the 'bulk line-range deletions can drop still-used closures' lesson from prior status-pages/companion-app plans"
  - "Per-case loops (device/pipeline/corroboration tile severities, language-pair checks, the seeded/fresh tile-anatomy sweep, the four check-in-disclosure cases, and the resolution-rate singular/plural matrix) become @pytest.mark.parametrize tests, per Task 1's explicit instruction — a departure from 33-25's own precedent of keeping some loops inside one function body, applied here because this plan's Task 1 named it directly rather than leaving it to Claude's discretion"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 9min
completed: 2026-09-24
---

# Phase 33 Plan 26: Status-Pages Part 02 (Sparkline Contract, Regularity Grid, Tile Verdicts) Summary

**Migrated the second of seven status-pages harness slices to native pytest: `battery_sparkline_svg()`'s remaining axis-label/flat/wiggle/clamp/area/mark/low-battery-threshold contract, the whole 24-07-PLAN.md check-in regularity grid, the D-05/B4 Paris-local-time sweep, the D-03/A-21 tile-verdict/tile-anatomy sweep, and the B2 never-ran-pipeline state — 48 legacy checks becoming 62 pytest node ids in a new `companion/test_status_pages_02.py`, with the chain's first served-stylesheet/served-JS checks replacing three raw-disk reads.**

## Performance

- **Duration:** ~9 min (commit-to-commit)
- **Started:** 2026-09-24T15:22:41Z (first commit)
- **Completed:** 2026-09-24T15:30:54Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `companion/test_status_pages_02.py`: 62 native pytest node ids covering all 48 of part 02's original `check()` calls — the sparkline axis-label/flat-series/wiggle/out-of-range-clamp/density-threshold/scale-bound/area-fill/newest-point-mark/low-battery-threshold contract; the 24-07-PLAN.md check-in regularity grid (`draw.cell_class()`'s four-state mapping, `regularity_grid()`'s 360px-floor sizing and capacity-bounded newest-buckets-kept behaviour, `draw.CELL_STATE_CLASSES`' classifier-vocabulary coupling); Health's regularity caption (three clauses each as their own test, the no-cadence-floors fallback, the classifier-agreement sweep, the empty-grid still-renders case, the punctuality-vocabulary ban, and the four-case "moved, not cut" disclosure parametrized test); the daily-mode date-endpoint/average-label contract; the D-05/B4 Paris-local sweep (axis clock/day labels, the sparkline point's title/aria-label/data-when agreement, the zero-UTC-literal sweep, `battery-trend.js`'s date-math absence, `concise_timestamp_html()`'s local title); the D-03/A-21 Device/Pipeline/Corroboration tile-verdict severities (parametrized); the X8/C1 one-tile-anatomy sweep (parametrized seeded/fresh) and the "Only one saw it" neutral-dot check (parametrized by language); the compact `empty_state()` variant and its in-tile/full-card split; the D-06/B16 resolution-rate singular-form matrix (parametrized, plus its own French-catalogue-entry test); and the B2 never-ran-pipeline neutral state in both languages plus `compute_health_state()`'s verdict-free `pipeline_detail_html`.
- The chain's first served-CSS/served-JS checks: a module-scoped read-only `companion/app.py` server (`_module_server`/`css_text`/`battery_trend_js` fixtures) replaces two raw `style.css` reads (`declarations_for()`/`css_rules()` for the `.battery-trend-section svg:not(.icon)` height contract and its no-`@media`-override guard; `declarations_for()`/`rules_with_selector()` for `.sparkline-area`'s fill/opacity and `.sparkline__area`'s deliberate absence) and one raw `battery-trend.js` read (`served_asset()`), per 33-MIGRATION-RULES.md's rubric C/J.
- `companion/test_status_pages.py` shrunk further: `EXPECTED_CHECK_COUNT` dropped from 279 to 231; part 02's 48 checks and the closures/constants only they used removed from `main()`. `_tile_slice_by_caption()` — caught by Task 3's own standalone harness run still calling it from a later, still-pending section — is promoted to module scope beside its existing sibling `_stat_tile_slices()`. The now-unused `battery`/`draw` top-level imports are removed.
- The ledger fragment's rows 38-85 flipped to `ported`: 44 B/D rows, 3 C rows (the two `style.css` reads above), 1 J row (the `battery-trend.js` read), 7 rows pointing at a parametrized test's primary node id with siblings named below, and two in-place rubric-S clause drops inside otherwise-ported checks (documented in the ledger's Part 02 note, not counted as separate deletions). `33-ledger-check.py --allow-pending` confirms 317/317 baseline checks accounted for (86 ported, 231 pending).
- Verification beyond the plan's own scoped checks: the shrunk legacy harness runs 231/231 green standalone (`server/.venv/bin/python3 companion/test_status_pages.py`) and through `companion/test_legacy_harness_shim.py -k status_pages`; `companion/test_suite_guards.py test-support` (90 tests) stays green; `ruff check companion/test_status_pages*.py` clean.

## Task Commits

1. **Task 1: First half of part 02 (27 pytest nodes)** - `b9779a4` (test)
2. **Task 2: Second half of part 02 (35 more pytest nodes)** - `09f1d97` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `9c8e4ee` (test)

## Files Created/Modified

- `companion/test_status_pages_02.py` - 62 native pytest node ids porting part 02's 48 legacy checks
- `companion/test_status_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 231`; part 02's checks removed; `_tile_slice_by_caption()` promoted to module scope; unused imports dropped
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md` - rows 38-85 flipped, Part 02 note added

## Parametrized checks: primary node id and sibling ids

Per 33-MIGRATION-RULES.md section 3 ("one old check splits into several tests"), each of the following ledger rows points at ONE primary node id; the siblings below are the other node ids the same old check now covers:

- Row 58 (`test_check_in_disclosure_moved_clauses_render_across_all_four_cases`): primary `[observed, cadence known]`; siblings `[observed, cadence unknown]`, `[not observed, cadence known]`, `[not observed, cadence unknown]`.
- Row 73 (`test_device_tile_verdict_matches_state_at_each_severity`): primary `[ok]`; siblings `[warn]`, `[error]`.
- Row 74 (`test_pipeline_tile_verdict_matches_state_at_each_severity`): primary `[ok]`; siblings `[warn]`, `[error]`.
- Row 75 (`test_corroboration_tile_verdict_matches_disagreement_state`): primary `[agree]`; sibling `[disagree]`.
- Row 77 (`test_one_tile_anatomy_across_every_health_tile`): primary `[seeded]`; sibling `[fresh]`.
- Row 78 (`test_only_one_saw_it_is_neutral_and_still_distinct`): primary `[en-Both agree-Only one saw it]`; sibling `[fr-Les deux concordent-Une seule l'a vu]`.
- Row 81 (`test_resolution_detail_line_has_a_singular_form`): primary `[total=1-en]`; siblings `[total=1-fr]`, `[total=2-en]`, `[total=2-fr]`, plus the trailing French-catalogue-entry assertion split into its own `test_resolution_detail_templates_have_french_catalogue_entries`.

## Decisions Made

See `key-decisions` in the frontmatter above: the served-CSS/served-JS checks use a single module-scoped read-only server (matching the migration rules' explicit GET-only carve-out); two rubric-S source-text clauses are dropped in place rather than the whole check being deleted, since the rest of each check is still a real behaviour proof; `_tile_slice_by_caption()` is promoted to module scope because a later section still calls it; and per-case loops become parametrized tests per this plan's own explicit Task 1 instruction (rather than 33-25's precedent of leaving some loops inside one function body).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `_tile_slice_by_caption()` promoted to module scope after Task 3's bulk deletion removed it**
- **Found during:** Task 3, running the shrunk legacy harness standalone (`server/.venv/bin/python3 companion/test_status_pages.py`)
- **Issue:** The plan's own line-range deletion (part 02's original `check()` calls #38-#85) removed `_tile_slice_by_caption()`, a `main()`-local closure that part 02's own checks defined and used — but a later, still-pending section (not yet migrated) also calls it. Deleting the range left a `NameError` on the first still-legacy check that calls it, failing the harness at 230/231 instead of 231/231.
- **Fix:** Re-added `_tile_slice_by_caption()` as a module-level function immediately after its existing sibling `_stat_tile_slices()` (both now module scope, both already used the same way by any remaining `main()` closure), with a short docstring naming why it moved.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** The harness re-run standalone: 231/231 pass. `ruff check` (which would otherwise flag the resulting unused `battery`/`draw` imports as F401, and did) confirmed clean after also removing those two now-unused imports. `companion/test_legacy_harness_shim.py -k status_pages` and `companion/test_suite_guards.py test-support` re-verified green.
- **Committed in:** `9c8e4ee` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for the shrunk legacy harness to stay green — exactly the "bulk line-range deletions can drop still-used closures" failure mode prior status-pages/companion-app plans documented; caught before commit by running the harness standalone per 33-MIGRATION-RULES.md section 5. No scope creep — no other file touched for this fix.

## Issues Encountered

None beyond the deviation above, caught and fixed before the Task 3 commit.

## User Setup Required

None.

## Next Phase Readiness

- 33-27..33-31 (the chain's remaining 5 plans) continue shrinking `companion/test_status_pages.py`'s single `EXPECTED_CHECK_COUNT` line (currently 231, from wherever `compute_health_state_carries_pipeline_detail_html_has_run` and onward — Section 1 continues past part 02's boundary into the remaining pipeline-off/anomaly-suppression/sparkline-empty-guard/data-table-contract checks the plan's own slice explicitly left for later parts).
- `_module_server`/`css_text`/`battery_trend_js` are the chain's first served-CSS/served-JS fixtures; a later part needing the served stylesheet or another served asset can reuse this exact pattern (a module-scoped read-only server, since none of these checks mutate state) rather than inventing a new one.
- `_tile_slice_by_caption()` is now module scope in the legacy harness — any later part's own migration slice that ports the checks still calling it does not need to re-discover or re-define it; it simply stops being called from `companion/test_status_pages.py` once that slice's checks move to their own new module.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk
(`companion/test_status_pages_02.py`, `companion/test_status_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md`,
this summary) and all 3 commit hashes (`b9779a4`, `09f1d97`, `9c8e4ee`)
found in `git log --oneline --all`.
