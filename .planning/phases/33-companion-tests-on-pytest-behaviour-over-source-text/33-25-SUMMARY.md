---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 25
subsystem: testing
tags: [pytest, health-page, svg-parsing, root-safety, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_status_pages.md fragment (scaffolded with all 317 rows pending) this plan's rows build on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's fixtures and test-support/companion_app_server.py's HTTP client (not directly used by this plan's in-process health_page.render() calls, but the same shared infrastructure the chain's later HTTP-backed parts build on)"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's parse_html()/Node (used here for the battery ring/chart/sparkline SVG structural assertions) and companion/test_suite_guards.py's TST-10/12/13/14 guard, which now scans this plan's two new modules"
provides:
  - "companion/test_status_pages_helpers.py: history_db/poll_loop/manual_resolutions seeding wrappers, stat_tile_slices() (balanced .stat-tile div-depth scan), served_css_rules() (a served-stylesheet css_rules() wrapper), __test__ = False, front-loaded for 33-26..33-31's later status-pages sections"
  - "companion/test_status_pages_01.py: 38 native pytest tests porting companion/test_status_pages.py's original check() calls #1-#37 (health_page's two freshness signals, wake.py's staleness-threshold/env/effective-interval contract and import boundary, layout's absolute_and_relative(), the Battery section through the day-1 raw-series fallback, the D-07 anomaly-category/pill/banner contract, the D-08 Corroboration disclosure, D-09 concise timestamps, the 260902-chc D-12 reversal guard, the badge-to-card-border retargets, the retired anomaly-detail-list guards, and battery_sparkline_svg()'s contract), plus the pulled-forward anomaly_active() root-safety check, now root-safe via tmp_path"
  - "companion/test_status_pages.py shrunk: EXPECTED_CHECK_COUNT collapsed from a ~940-line reassignment history to one authoritative line (279 pending), part-01's checks and the root-unsafe anomaly_active check removed from main(); the literal /nonexistent/definitely-not-here mkdir is gone from the file entirely"
  - "the status-pages ledger fragment's rows 1-37 and 151 flipped to ported, Part 01 note added; 33-ledger-check.py --allow-pending confirms 317/317 baseline checks accounted for"
affects: [33-26, 33-27, 33-28, 33-29, 33-30, 33-31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Battery ring/chart/sparkline SVG assertions parse the rendered markup structurally through companion_markup.parse_html() (circle/line/svg element counts, r/stroke-dasharray/data-mv/data-ts/tabindex attribute values, document order) instead of regex-slicing the raw HTML string the legacy harness used - the drawn fraction is recovered from the parsed value arc's own r/stroke-dasharray attributes and compared against the readout's own printed percentage, exactly reproducing the legacy check's cross-check without a single regex over SVG markup"
    - "The pulled-forward anomaly_active() root-safety check folds its former 'missing state_dir' literal-path case into the same assertion shape as its pre-existing 'empty writable directory' case, rather than keeping a separate hardcoded-False assertion for the renamed tmp_path variant: a tmp_path subpath is always writable (unlike a root-owned host path), so history_db.open_db()'s os.makedirs(..., exist_ok=True) always succeeds and creates the schema for both, regardless of which euid runs the suite - the check's actual invariant (no raise, a real bool, agreement with render()'s own banner presence) survives; only the environment-dependent 'permission denied degrades to False' branch, which was root-unsafe by construction, is gone"
    - "companion.wake's import-boundary check ('never imports the pages package or app.py') is rewritten as a child_env() subprocess importing companion.wake alone and asserting sys.modules carries no companion.pages/companion.app entry, mirroring test_i18n.py's own import-boundary probe precedent from the same phase - proves the same architectural invariant behaviourally instead of grepping wake.py's source text (TST-12/G3)"
  key-files:
    created:
      - companion/test_status_pages_helpers.py
      - companion/test_status_pages_01.py
    modified:
      - companion/test_status_pages.py
      - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md

key-decisions:
  - "The _battery_section() single-positional-argument arity guard (originally an inspect.signature() introspection) could not be ported as written: companion/test_suite_guards.py's G2 rule bans any inspect.* attribute access in a migrated module, with no exemption for inspect.signature (only inspect.getsource is source-text reading, but the guard's ast scan cannot distinguish the two at the attribute-access level). Rewritten as a direct call, health_page._battery_section([]), which raises TypeError if the pinned single-positional-argument call site ever breaks - a strictly narrower but still observable proof of the same contract, and the only form G2 permits"
  - "34 of the 38 ported checks stay close to the legacy harness's own substring/index assertion style (matching 33-14's own precedent for structural checks on rendered HTML) rather than a blanket parse_html() rewrite - TST-12's rule is about not reading source .py/CSS-as-text/planning-doc files, not about banning substring assertions on already-fetched rendered output. parse_html() is used specifically for the 4 checks the plan named explicitly (battery ring, trend-chart canvas/line counts, the two sparkline SVG checks), where element-count/attribute assertions are a meaningfully sharper structural proof than a regex over raw markup"
  - "The anomaly_active() pulled-forward test folds two originally-separate assertion cases (a never-existed path, a pre-created empty directory) into one shared code path/assertion, because both now provision an empty writable tmp_path directory identically - documented inline as a deliberate behavioural narrowing (the environment-dependent 'PermissionError degrades to False' branch cannot be reproduced with an always-writable tmp_path, on any euid), not an oversight"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 14min
completed: 2026-09-24
---

# Phase 33 Plan 25: Status-Pages Helpers, Part 01, and the anomaly_active Root-Safety Fix Summary

**Started the 7-plan status-pages migration chain (the largest companion harness, 16.3k lines, 317 checks): built the chain's shared seeding/parsing helpers module, migrated all 37 of part 01's checks (health_page's freshness signals, wake.py's staleness contract, the full Battery section including its ring/chart/sparkline SVG contract, and the D-07/D-08/D-09/D-12 anomaly-banner/corroboration/timestamp rewrites) to native pytest, and pulled the root-unsafe `anomaly_active()` degrade-safely check forward so the legacy harness finally runs green as root.**

## Performance

- **Duration:** ~14 min (commit-to-commit)
- **Started:** 2026-09-24T12:36:43Z (first commit)
- **Completed:** 2026-09-24T12:50:27Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `companion/test_status_pages_helpers.py`: a new `__test__ = False` module holding the status-pages chain's shared `history_db`/`poll_loop`/`manual_resolutions` seeding wrappers (`seed_device_health`, `seed_meta`, `seed_runway_events`, `seed_unresolved_prefixes`, `seed_manual_resolutions`), a small formatting layer (`iso`/`now`/`ago`/`ctx`), `stat_tile_slices()` (a balanced `.stat-tile` div-depth scan, ported from the legacy `_stat_tile_slices()`), and `served_css_rules()` (a thin `css_rules(served_stylesheet(server))` wrapper for the chain's later CSS-reading parts). Excludes `Harness`/`http_request`/`_NoRedirectHandler`/`tempfile` and the legacy raw-disk stylesheet reader entirely, per the plan's own instruction.
- `companion/test_status_pages_01.py`: 38 native pytest tests — all 37 of part 01's original `check()` calls (health_page's two freshness signals; `wake.py`'s staleness-threshold/env/effective-interval contract, its import-boundary check rewritten as a `child_env()` subprocess `sys.modules` probe; `layout.absolute_and_relative()`'s full documented-case sweep; the Battery section's timestamp-helper promotion, independent per-tile modifiers, empty-state/ring/trend/disclosure/caption/daily-average/day-1-fallback behaviour, the D-07 anomaly-category-text/pill/banner contract, the D-08 Corroboration compact-rows-plus-disclosure rewrite, D-09's concise Device/Pipeline timestamps, the 260902-chc D-12 reversal guard, the badge-to-card-border retargets, and the retired anomaly-detail-list markup guards) plus the pulled-forward `anomaly_active()` degrade-safely check. The battery ring, trend-chart and both sparkline checks parse the rendered SVG structurally through `companion_markup.parse_html()` (circle/line/svg element counts and `r`/`stroke-dasharray`/`data-mv`/`data-ts`/`tabindex` attributes in document order) instead of regex-slicing raw markup.
- `companion/test_status_pages.py` shrunk: the ~940-line `EXPECTED_CHECK_COUNT` reassignment history (185 → 317 across every phase since 19-05) collapsed into one `EXPECTED_CHECK_COUNT = 279` line; part 01's 37 checks and the pulled-forward `anomaly_active()` check removed from `main()`. The legacy harness's own literal `/nonexistent/definitely-not-here` mkdir-as-root call is gone entirely (`grep -c "/nonexistent"` is 0) — `companion/test_legacy_harness_shim.py -k status_pages` now runs green as root for the first time, closing the status-pages half of `32-REVIEW.md` IN-05.
- The ledger fragment's rows 1-37 and the out-of-order row 151 (`anomaly_active`) flipped to `ported`, pointing at real `companion/test_status_pages_01.py::test_*` node ids; a `### Part 01 (plan 33-25)` note records the rubric-code split (34 B/D, 1 S, 1 T, 0 deletions). `33-ledger-check.py --allow-pending` confirms 317/317 baseline checks accounted for (38 ported, 279 pending).
- Full-suite verification beyond the plan's own scoped checks: `pytest -n auto companion test-support server stub-server` as root (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — **1089 passed, 5 skipped, 0 failed.** No new `/nonexistent` entry (the pre-existing empty directory from an earlier baseline run is untouched); `git status --porcelain` clean for every file this plan modified.

## Task Commits

1. **Task 1: Helpers module, the anomaly_active pull, and the first half of part 01** - `2a8cb2c` (test)
2. **Task 2: Second half of part 01** - `9b67882` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify as root** - `17ba4ad` (test)

## Files Created/Modified

- `companion/test_status_pages_helpers.py` - shared seeding/formatting helpers for the status-pages chain
- `companion/test_status_pages_01.py` - 38 native pytest tests (all of part 01 plus the pulled-forward `anomaly_active()` check)
- `companion/test_status_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 279`, part-01/`anomaly_active` checks removed, `/nonexistent` literal gone
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md` - rows 1-37/151 flipped, Part 01 note added

## Decisions Made

See `key-decisions` in the frontmatter above: the `_battery_section()` arity guard rewritten as a direct call rather than `inspect.signature()` introspection (banned outright by `test_suite_guards.py`'s G2 rule, with no carve-out for `inspect.signature` versus `inspect.getsource`); keeping most checks in the legacy harness's own substring/index assertion style over rendered HTML (matching 33-14's precedent) and reserving `parse_html()` for the four SVG-heavy checks the plan named explicitly; and folding the pulled-forward `anomaly_active()` check's "missing path" and "empty directory" cases into one shared assertion shape once both provably take the identical `os.makedirs`-succeeds code path under a `tmp_path`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `_battery_section()` arity guard rewritten to avoid `inspect.signature()`, which `test_suite_guards.py`'s G2 rule forbids outright**
- **Found during:** Task 1, first run of `companion/test_suite_guards.py -k status_pages_01`
- **Issue:** The plan's own slice reads the legacy check's `inspect.signature(health_page._battery_section)` call as a straightforward port, but the phase's own guard (33-03) bans any `inspect.*` attribute access in a non-legacy companion module with no exemption for `inspect.signature` versus `inspect.getsource` — the guard's `ast.Attribute` visitor cannot distinguish "introspecting a function's signature" from "reading its source text" at that granularity, so it blocks both categorically.
- **Fix:** Replaced the signature introspection with a direct call, `health_page._battery_section([])`, immediately before the check's existing render-based assertions. This still raises `TypeError` (failing the test) if the pinned single-positional-argument call site inside `render()` ever needs a second required argument — a narrower but still real, observable proof of the same contract, and the only form the guard permits.
- **Files modified:** `companion/test_status_pages_01.py`
- **Verification:** `companion/test_suite_guards.py -k "status_pages_01 or status_pages_helpers"` passes 2/2; the full 38-test module still passes 38/38; `ruff check` clean.
- **Committed in:** `2a8cb2c` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for Task 1's own verification step (the guard scanning the new module) to pass; the arity contract this check protects is still exercised, just via a direct call instead of introspection. No scope creep — no other file touched for this fix.

## Issues Encountered

None beyond the deviation above, caught and fixed before the Task 1 commit.

## User Setup Required

None.

## Next Phase Readiness

- 33-26..33-31 (the chain's remaining 6 plans) can extend `companion/test_status_pages_helpers.py` and continue shrinking `companion/test_status_pages.py`'s single `EXPECTED_CHECK_COUNT` line (currently 279, from the `_health_page_section_builder_markup_survives_reframe` check onward — Section 1 continues past part 01's boundary into checks the plan's own slice explicitly left for later parts, e.g. the sparkline axis-label/threshold/area-fill/mark checks starting at check #38).
- `32-REVIEW.md` IN-05 (companion harnesses red as root) is now fully closed: `test_companion_app` (33-14) and `test_status_pages` (this plan) both run green as root; no other companion harness in `32-REVIEW.md`'s original finding remains.
- The `stat_tile_slices()`/`served_css_rules()` helpers are ready for whichever later part first needs a served stylesheet or another `.stat-tile` scan (none of part 01's own checks needed `served_css_rules()` directly — Health's tiles never read `style.css` in this slice — so it is exercised for the first time by a later part).
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk
(`companion/test_status_pages_helpers.py`, `companion/test_status_pages_01.py`,
`companion/test_status_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md`)
plus this summary, and all 3 commit hashes (`2a8cb2c`, `9b67882`, `17ba4ad`)
found in `git log --oneline --all`.
