---
phase: 61
plan: 129
type: quick-fix
subsystem: companion
tags: [layout-shift, ci-flake, flights, home, render-blocking]
key-files:
  modified:
    - companion/ui_shell.py
    - companion/pages/history_page.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
    - companion/test_sign_in_surfaces.py
    - companion/test_shell_meta.py
    - companion/test_browser_page_opening.py
    - companion/test_browser_home_signature.py
---

# Phase 61 Plan 129: late layout shifts of the Flights table and the Home frame button

Pages now hold their first frame until the whole page content is parsed, and the Flights table has fixed column widths.

## Root cause

A browser may paint a document that is still arriving. The only render-blocking `expect` link was the tab-bar marker, and the tab bar sits before `<main>`, so everything after it could be painted half-parsed. Two things then moved when the rest arrived. The link and marker order is in `companion/ui_shell.py`.

1. **Flights table.** Recorded with CPU throttling and a per-frame column-width probe, the table was first painted with 5 of its 39 rows. Its auto layout gave the columns widths 154/131/167/132/22. When the remaining rows were parsed they became 120/102/130/103/151. That moved every State and Picture cell by about 100 px, a layout shift of 0.02-0.04 sourced at `TD` cells. It is the CI failure of `test_the_flights_filter_bar_opens_in_its_final_layout`.
2. **Home signature (1280).** The frame button in the top bar (`SUMMARY.frame-menu__button`) was painted with only part of its children, then grew from about 90-106 px to 206 px. It reproduced at 20x CPU throttle as 0.0015-0.0017, which is the CI value of 0.0017 against the 0.001 limit. The hero body also shifted by 0.0024 in one throttled run, again because of streaming.

## Fix

- `companion/ui_shell.py` adds a `page-end` marker after the page content and a second `<link rel="expect" blocking="render">` in the head, emitted on the same pages as the tab-bar one. The first frame now holds the whole page. This removes the whole class of mid-parse shifts, not just the two seen. The three expect links go through one small `_expect_link` helper to keep `page_shell` under 80 lines.
- `companion/pages/history_page.py` and `companion/static/style.css` give the Flights table a `<colgroup>` with fixed percentage widths and `table-layout: fixed`. Its columns no longer depend on which rows have been parsed or on what a row brings, which is the underlying cause of the table shift.

## Tests

- `test_the_flights_table_columns_do_not_depend_on_the_rows_that_arrive` (1024 and 1280) appends a row with long cells and asserts no column moves. It is deterministic and was red on the old code (2 failed), green after.
- `test_home_opens_without_a_shift_on_a_slow_processor` loads Home 8 times under a 20x CPU throttle (CDP) and asserts a layout shift below 0.0005. It was red on the old code (frame button shift) and green after.
- `test_a_page_with_a_tab_bar_holds_its_first_paint_until_all_its_content_is_parsed` covers the served head and marker.
- The existing 0.01 and 0.001 limits are untouched.
- Pinned values updated in the same commit: the shell and error-page sha256 digests in `test_sign_in_surfaces.py` and `render_baseline.json`.

## Gates

- ruff, mypy, check_comment_history, check_function_size (none over 80) and `test_phase47_freeze` pass. `companion/app.py` is 1493 lines.
- Non-browser companion and test-support suite (`-m "not browser"`, `-n 8`): one failure, `test_structure_guards::test_no_production_function_exceeds_the_code_line_ceiling` (`page_shell` at 83 lines). It was fixed with the `_expect_link` helper and passes now.
- Browser: `test_browser_page_opening`, `test_browser_home_signature` and `test_browser_perf_remaining` (179 tests) at `-n 8`, repeated 5 times.
- Also run: the Flights and ux_01/03 browser files, the view-pages, flights, i18n and suite-guard files.

## Deviations

None from a plan (quick fix). `git stash` was used once and popped at once, before a red check. No other state was touched.
