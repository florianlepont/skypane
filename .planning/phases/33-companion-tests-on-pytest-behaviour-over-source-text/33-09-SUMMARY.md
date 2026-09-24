---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 09
subsystem: testing
tags: [pytest, config-page, migration, aspect-repin-ledger, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's app_server fixture family (not needed directly by this slice, since every part-01 check calls config_page's functions in-process) and test-support/companion_app_server.py"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "companion/test_suite_guards.py's TST-10/12/13/14 guard and the disk-derived legacy companion harness set that companion/test_config_page_01.py is now scanned under"
provides:
  - "companion/test_config_page_helpers.py: write_device_config() - the reusable state-seeding helper for the config-page migration chain (33-09..33-13), __test__ = False, no Harness/http_request/_NoRedirectHandler copy"
  - "companion/test_config_page_01.py: 32 native pytest tests porting part 01 of companion/test_config_page.py (original check() calls #2-#33) - render()'s five-group layout, led_group(), quiet_hours_group() (markup/order/escaping/three presets), wake_interval_group() (markup/value contract/render() placement), handle_post()'s display_enabled three-shape resolution and its eight-combination theme-only-save regression guard, the settings form's class hooks, the Aspect card's per-theme palette coverage/default-selection, and runway_fieldset()'s cards/image-rendering/hostile-label-escaping/photograph-survival"
  - "companion/test_config_page.py shrunk: one EXPECTED_CHECK_COUNT = 243 line (was 276, via a collapsed single-line history), the self-referential _ASPECT_REPIN_LEDGER tuple and its own guard check deleted outright, 243/243 still pass standalone and through the shim"
  - "the config-page ledger fragment's rows 1-33 flipped (1 deleted R, 32 ported), Part 01 note added"
affects: [33-10, 33-11, 33-12, 33-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Part 01's 32 checks all call companion.pages.config_page's own functions directly (render()/led_group()/quiet_hours_group()/wake_interval_group()/runway_fieldset()/_palette_swatch_html()/_palette_grid_html()/_usage_row_summary_html()/handle_post()) in-process against a tmp_path-backed state directory - none of this slice needed a running companion/app.py server, so no app_server fixture request appears anywhere in companion/test_config_page_01.py"
    - "Every tempfile.mkdtemp()/shutil.rmtree() pair and every literal \"/tmp\" ctx['state_dir'] value from the legacy checks is replaced with pytest's tmp_path (or a tmp_path subdirectory per case, for the two checks that used to build several throwaway tmpdirs inside one check() call) - a literal \"/tmp\" state_dir was a real T-33-09-02 tampering surface (config_page.render()'s live-preview helper opens a real history_db under it), not just a style nit"
    - "A single-use fixture (_temporary_registry()/_runway_entry(), swapping device_config.RUNWAYS/RUNWAY_IDS for a hostile registry entry) is kept local to companion/test_config_page_01.py rather than promoted to the shared helpers module, since grepping the legacy file confirmed no other check (migrated or still-legacy) calls it"
    - "The self-referential _ASPECT_REPIN_LEDGER guard (which opened test_config_page.py's own source to grep def names, a TST-12 violation by construction) is deleted outright rather than rewritten as behaviour - there is no rendered/observable consequence to reconstruct, only plan-history bookkeeping (R, 33-MIGRATION-RULES.md section 3)"

key-files:
  created:
    - companion/test_config_page_helpers.py
    - companion/test_config_page_01.py
  modified:
    - companion/test_config_page.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md

key-decisions:
  - "_ASPECT_RETIRED_MARKUP_TOKENS and _aspect_usage_row_bounds() (module-scoped helpers registered right after the deleted R check, inside main()) stay in companion/test_config_page.py rather than moving anywhere: a dozen still-legacy checks further down main() (Sections beyond part 01) call _aspect_usage_row_bounds() directly, and one calls _ASPECT_RETIRED_MARKUP_TOKENS - setup later checks still need, per 33-MIGRATION-RULES.md section 1"
  - "companion/test_config_page_helpers.py carries only write_device_config() (renamed from the legacy file's private _write_device_config, part 01's only shared cross-check helper) - not _python_identifiers() (an ast/tokenize helper over production source part 01 never calls, used only by later still-legacy sections) and not _temporary_registry()/_runway_entry() (single-use within part 01 itself, kept local to the new test module)"
  - "The 4 handle_post()-centred checks (persistence/regression-guard checks with no primary markup-shape assertion) are classified B; the remaining 28 render()/led_group()/quiet_hours_group()/wake_interval_group()/runway_fieldset()/_palette_*_html() markup-shape/attribute/position checks are classified D, per 33-MIGRATION-RULES.md section 3's rubric - all 32 are 'ported' with only the tempfile->tmp_path/state_dir plumbing changing, none needed a structural parse_html() rewrite since none asserted anything a companion_markup.Node.select() call would materially change (the checks already asserted narrow, single-fragment substring/count/position facts, not multi-attribute nested-structure shapes)"

patterns-established: []

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 13min
completed: 2026-09-24
---

# Phase 33 Plan 09: Config-Page Helpers, Aspect-Repin Ledger Deletion, and Part 01 Migration Summary

**Started the 5-plan config-page migration chain: built the chain's shared helpers module, deleted the self-referential `_ASPECT_REPIN_LEDGER` bookkeeping outright, and migrated the first 33 of `companion/test_config_page.py`'s 276 `check()` calls (render()'s group layout through Aspect-card/runway-card coverage) to native pytest in `companion/test_config_page_01.py`.**

## Performance

- **Duration:** ~13 min (commit-to-commit; previous plan 33-05 completed 2026-09-24T10:52:00Z)
- **Started:** 2026-09-24T10:52:23Z (first commit)
- **Completed:** 2026-09-24T11:05:16Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `companion/test_config_page_helpers.py`: a new `__test__ = False` module holding `write_device_config()` (renamed from the legacy file's private `_write_device_config`) — the one state-seeding helper part 01's checks share, with no `Harness`/HTTP-client copy.
- `companion/test_config_page_01.py`: 32 native pytest tests, one per original `check()` label as its docstring, porting all of part 01 except the deleted R check — `render()`'s five theme-status-wrapped groups and zero-`<fieldset>` contract, `led_group()`'s switch/role/aria-checked sequence, `quiet_hours_group()`'s markup/field order/escaping/three time presets and `handle_post()`'s preset-shaped persistence, `wake_interval_group()`'s markup/value-attribute contract and `render()`'s placement/prefill resolution, the on/off-checkbox removal's no-JS floor, `handle_post()`'s three-shape `display_enabled` resolution and its eight-combination theme-only-save regression guard, the settings-group naming/page-header/class-hook checks, the Aspect card's per-theme palette coverage and default selection, and `runway_fieldset()`'s cards/image-rendering/hostile-label-escaping/photograph-survival checks. Every `tempfile.mkdtemp()`/`shutil.rmtree()` pair and both literal `"/tmp"` `state_dir` values are replaced with `tmp_path` (or a `tmp_path` subdirectory per case, for the two checks that built several throwaway state dirs inside one original `check()` call).
- The self-referential `_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()` guard (which opened `test_config_page.py`'s own source to grep def names — a TST-12 violation by construction) is deleted outright, along with the `_ASPECT_REPIN_LEDGER` tuple it read and that tuple's own history comments. Grepped first to confirm no remaining check (migrated or still-legacy) references the tuple as code, only historical prose comments do (left untouched, per the plan's own minimal instruction and acceptance criteria).
- `companion/test_config_page.py` shrunk: the `EXPECTED_CHECK_COUNT` history (1057 lines of historical reassignments, `EXPECTED_CHECK_COUNT = 79` through `= 276`) collapsed into one `EXPECTED_CHECK_COUNT = 243` line above `def main()`. The shared `_ASPECT_RETIRED_MARKUP_TOKENS`/`_aspect_usage_row_bounds()` helpers (registered alongside the deleted R check, but read by a dozen still-legacy checks further down `main()`) are kept in place. The shrunk harness still runs 243/243 standalone (`server/.venv/bin/python3 companion/test_config_page.py`) and through `companion/test_legacy_harness_shim.py -k config_page`.
- The ledger fragment's rows 1-33 flipped (row 1 `deleted`, reason `R: self-referential CFG-85 aspect-repin bookkeeping; opens test_config_page.py to grep def names; no behaviour`; rows 2-33 `ported` to real `companion/test_config_page_01.py::test_*` node ids) and a `### Part 01 (plan 33-09)` note added (4 B, 28 D rubric codes; 1 R deletion). `33-ledger-check.py --allow-pending companion/test_config_page.py` confirms 276/276 baseline checks accounted for (32 ported, 1 deleted, 243 pending).
- Full-suite sanity beyond the plan's own scoped verification: `pytest -n auto companion test-support server stub-server` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium) — 981 passed, 2 failed (the exact pre-existing root-sandbox artifacts already classified in `33-BASELINE/INDEX.md`: `test_status_pages`'s `anomaly_active("/nonexistent/...")` check and `test_companion_app`'s `os.chmod` checks), 3 skipped. No regression from this plan.

## Task Commits

1. **Task 1: Helpers module, the R deletion, and the first half of part 01** - `3c1dad1` (test)
2. **Task 2: Second half of part 01** - `1345d39` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `6fecabd` (test)

## Files Created/Modified

- `companion/test_config_page_helpers.py` - shared state-seeding helper for the config-page chain
- `companion/test_config_page_01.py` - 32 native pytest tests (part 01)
- `companion/test_config_page.py` - shrunk to `EXPECTED_CHECK_COUNT = 243`, part-01 checks and the `_ASPECT_REPIN_LEDGER` tuple removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md` - rows 1-33 flipped, Part 01 note added

## Decisions Made

See `key-decisions` in the frontmatter above: keeping `_ASPECT_RETIRED_MARKUP_TOKENS`/`_aspect_usage_row_bounds()` in the legacy file (still-legacy consumers), scoping the helpers module to only `write_device_config()`, and the B/D rubric split (4 B handle_post checks, 28 D markup checks) with no check needing a `parse_html()`/`companion_markup` rewrite since none asserted a shape a structural parser would materially change over the original substring/count/position checks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - missing critical functionality] Replaced two literal `"/tmp"` `state_dir` values with `tmp_path`**
- **Found during:** Task 1, porting `_no_page_and_no_scope_renders_a_display_or_quiet_hours_on_off_checkbox` and `_no_js_floor_holds_on_display_and_device_after_the_checkbox_removal`
- **Issue:** the legacy checks passed the literal string `"/tmp"` as `ctx["state_dir"]`. `config_page.render()`'s live-preview helper opens a real `history_db` under `state_dir` for the Display/Device scopes these two checks exercise, so the original checks were writing to the real host `/tmp` directory on every run — a live T-33-09-02 tampering surface (writes outside `tmp_path`), not merely a style mismatch with the migration rules' `tmp_path`-only convention.
- **Fix:** both checks now pass `str(tmp_path)` instead of the `"/tmp"` literal.
- **Files modified:** `companion/test_config_page_01.py`
- **Verification:** both tests pass; `companion/test_suite_guards.py`'s G6 rule (which flags `tempfile.*`/`/nonexistent` literals) has no `/tmp`-specific check, but the fix is directly required by 33-MIGRATION-RULES.md section 2's "write only under tmp_path" rule and this plan's own threat register (T-33-09-02).
- **Committed in:** `3c1dad1` (Task 1 commit)

**2. [Rule 3 - blocking] Restored `STARTUP_DEADLINE_S = 10.0`, briefly lost during the EXPECTED_CHECK_COUNT history collapse**
- **Found during:** Task 3, running the shrunk harness standalone after collapsing the `EXPECTED_CHECK_COUNT` history block
- **Issue:** the module-level constant `STARTUP_DEADLINE_S = 10.0` (used by the legacy `Harness.start()`'s startup-polling loop, still needed by the file's own remaining live-HTTP checks) sat on the line immediately before the large `EXPECTED_CHECK_COUNT` history comment block this task collapsed. A line-range deletion script removed one line more than intended and dropped it.
- **Fix:** re-added `STARTUP_DEADLINE_S = 10.0` directly above `EXPECTED_CHECK_COUNT = 243`. Caught before any commit — verified via `ast.parse()`, then a full standalone run of the harness (243/243 pass) before staging.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `server/.venv/bin/python3 companion/test_config_page.py` — 243/243 pass; `ast.parse()` clean; `ruff check` clean.
- **Committed in:** `6fecabd` (Task 3 commit, never landed in an earlier commit)

## Issues Encountered

The bulk line-range deletions needed for a 13,620-line file (the `EXPECTED_CHECK_COUNT` history collapse, the part-01 body removal, and the `_ASPECT_REPIN_LEDGER` tuple removal) were done with small Python scripts operating on explicit line ranges rather than the `Edit` tool's exact-string matching, since the ranges spanned over a thousand lines each. One such script's range boundary was off by one line (Deviation 2 above) — caught immediately by running the shrunk harness standalone before staging, not left for a later plan or CI to discover.

## User Setup Required

None.

## Next Phase Readiness

- 33-10/11/12/13 (parts 02-05 of this same chain) can extend `companion/test_config_page_helpers.py` with whatever additional seeding/render helpers their own slices need, following this plan's `__test__ = False` / no-Harness convention, and continue shrinking `companion/test_config_page.py`'s single `EXPECTED_CHECK_COUNT` line.
- `companion/test_config_page.py` still has 243 pending checks (everything from the wrapping-midnight quiet-window arithmetic onward) for the chain's remaining 4 plans.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 5 claimed created/modified files found on disk (`companion/test_config_page_helpers.py`,
`companion/test_config_page_01.py`, `companion/test_config_page.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md`,
this summary), and all 3 commit hashes (`3c1dad1`, `1345d39`, `6fecabd`) found in
`git log --oneline --all`.
