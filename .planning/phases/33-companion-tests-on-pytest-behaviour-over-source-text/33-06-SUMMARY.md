---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 06
subsystem: testing
tags: [pytest, html-parser, css-parser, js-served-asset, companion, view-pages, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "05"
    provides: "companion/test_view_pages_helpers.py's seed_runway_events()/history_ctx()/row_block() and companion/test_view_pages_01.py's part-01 conventions"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's parse_html()/css_rules()/declarations_for() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
provides:
  - "companion/test_view_pages_02.py: 59 native pytest tests porting part 02 of companion/test_view_pages.py (original check() calls #38-#96) - the icon-only row-toggle contract, the summary/detail row split's copy buttons and CSS, the render-gallery section's retirement in favour of the per-row View-panel lightbox, panel-lookup.js's DOM/JS contracts, and the Airlines gap strip / unconditional dialog forms / resolve dialog's Paris-local time"
  - "companion/test_view_pages_helpers.py additions: detail_row_block()/table_markup() (raw-markup slice helpers for substring/attribute-value checks a parsed Node has no serializer for), seed_gallery()/seed_unresolved_prefixes()/write_panel_file() (tmp_path-backed fixture seeding), strip_js_line_and_block_comments() (comment-only JS stripper that preserves string literals, unlike companion_markup.strip_js_comments_and_strings())"
  - "companion/test_view_pages.py shrunk: one EXPECTED_CHECK_COUNT = 73 line (was 132), 73/73 still pass standalone and through the shim"
  - "the view-pages ledger fragment's rows 38-96 flipped to ported with real node ids, Part 02 note added (33 D, 14 J, 5 C, 7 B; 0 deleted)"
affects: [33-07, 33-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A JS source-content check that must preserve string-literal content (e.g. asserting the exact absence of `image.src = \"\"`) uses the new local strip_js_line_and_block_comments() helper, not companion_markup.strip_js_comments_and_strings() - the toolkit function also erases string/template literals, which would silently erase the very empty-string literal the check searches for"
    - "A CSS check scoped to a media-query block (the desktop-only [data-copy-value] reveal rule inside @media (min-width: 960px)) uses declarations_for(css, selector, at_rules=(\"@media (min-width: 960px)\",)) instead of manual brace-matching over the raw stylesheet text - the tokenizer's at_rules parameter eliminates the need to find/slice the media block by hand"
    - "A row/detail-row check needing byte-for-byte attribute-value equality or substring containment across a row's raw markup (e.g. \"this data-view-panel-src value is byte-identical on the desktop and mobile representations\") keeps a plain regex slice over the RENDERED string (a private _row_markup() helper in test_view_pages_02.py, and the shared vp.detail_row_block()) rather than forcing every check through companion_markup.Node - Node has no markup serializer, so byte-identity/attribute-string assertions are still permitted directly on a production render() call's return value (TST-12 forbids reading source files, not regexing a render() call's own output)"
    - "A JS file's served text (panel-lookup.js/flight-rows.js/copy-button.js), fetched once per module through a served_asset(app, path) call (or the panel_lookup_js module-scoped fixture), is scanned with the exact same string/regex assertions the legacy check used when it opened the file from disk - the HTTP fetch is the only change TST-12 required; the check's own logic (token presence, indentation, call-site counts, preventDefault() positioning) is unaffected by where the bytes came from"
    - "A source-text completeness check with a direct behavioural substitute (history_page.py 'never renders the script's own clickable marker class') is rewritten as an assertion on a real history_page.render() call's output instead of a disk read of history_page.py - no S-classified check in this slice needed a deletion; every one had either a served-asset/served-stylesheet equivalent or a render()-output equivalent"

key-files:
  created:
    - companion/test_view_pages_02.py
  modified:
    - companion/test_view_pages_helpers.py
    - companion/test_view_pages.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md

key-decisions:
  - "detail_row_block()/table_markup() (raw-markup-string helpers) are added to the SHARED companion/test_view_pages_helpers.py rather than kept module-local to test_view_pages_02.py, because the still-legacy sections beyond row 96 already call the legacy file's own _detail_row_block()/_table_markup() - 33-07/08 will need the identical helper when their own slices migrate those calls, and this keeps the chain's convention of extending the shared helpers module rather than each part re-inventing the same locator"
  - "_row_markup() (the raw-string sibling of vp.row_block(), keyed by data-filter-group) stays LOCAL to test_view_pages_02.py rather than joining the shared helpers module, because vp.row_block() already established a Node-returning contract in 33-05 for the SAME locator name/shape - introducing a second, string-returning helper under a different name only where THIS module's checks need byte-for-byte attribute-value/substring semantics avoids overloading or renaming 33-05's own public contract"
  - "The three lightbox DOM-contract token tuples (_LIGHTBOX_SHARED_TOKENS/_LIGHTBOX_AIRLINES_ONLY_TOKENS/_LIGHTBOX_RENDER_ONLY_TOKENS) and _NEW_VIEW_PANEL_ATTR_NAMES are re-declared as module-level constants inside test_view_pages_02.py (not the shared helpers module), because grepping every remaining occurrence in the legacy file confirmed all of them are used exclusively by this slice's two checks (rows 69-70, 75) - they are deleted from companion/test_view_pages.py rather than left as unused dead weight"
  - "CSS checks use companion_markup.declarations_for() throughout (including the two @media (min-width: 960px)-scoped reveal-rule checks, via the at_rules= parameter) rather than a raw regex/brace-match over the served stylesheet text, matching 33-05's own established C-classification pattern even though a plain string search on served (not disk-read) text would also have satisfied TST-12 - this keeps the chain's CSS assertions uniformly structural rather than reintroducing brace-matching regex the toolkit already replaces"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: ~35min
completed: 2026-09-24
---

# Phase 33 Plan 06: View-Pages Migration Chain Part 02 Summary

**Migrated the next 59 of `companion/test_view_pages.py`'s original 169 check() calls (icon-only row toggle, summary/detail row split, render-gallery retirement, panel-lookup.js's three-file DOM/JS contract, and the Airlines gap strip/unconditional dialog forms/Paris-local resolve dialog) to native pytest in `companion/test_view_pages_02.py`, fetching every CSS/JS asset the legacy checks used to open from disk over a real running `companion/app.py` instead.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-24T12:54:19Z (previous plan's completion timestamp)
- **Completed:** 2026-09-24T13:21:51Z
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `companion/test_view_pages_02.py`: 59 native pytest tests, one per original `check()` label as its docstring, porting part 02 in full - the icon-only row-toggle contract in both languages, `.row-toggle`'s CSS reusing `.copy-btn`'s icon-only pattern verbatim (via `declarations_for()`, no manual brace-matching), `flight-rows.js`'s attribute/no-sink contract (fetched via `served_asset()`), the desktop/detail-row copy-button split and its `@media (min-width: 960px)`-scoped reveal rule, `copy-button.js`'s `execCommand` propagation and ES5-safety, the render-gallery section's full retirement in favour of the per-row View-panel lightbox (with the orphaned colour caveat rehomed into `.lightbox__note`), `nearest_gallery_entry()`'s boundary/degradation fixtures, `panel-lookup.js`'s nine source-content contracts (image-src-never-empty, conditional `removeAttribute`, the shared `openFromTrigger` factoring, `location.search`'s single guarded read, the eleven new `data-view-panel-*` attributes, the mode-toggle-before-`showModal()` ordering, `preventDefault()`'s exact three-call shape, the single dialog lookup/click listener, the count-gated `contextCallsign` write), the three-file (JS + both pages' rendered markup) lightbox token contract and its reflection-driven completeness check, History's zero-replace-markup guarantee against Airlines' replace/upload/delete apparatus, the Airlines gap strip's post-reorder section ordering (title < filter < gallery < gap strip < lightbox, CFG-82), the no-chrome gate surviving that reorder, the resolve panel's Airlines-targeted back link, the now-unconditional replace/delete/upload dialog forms (CFG-81), the retired page-wide editing toggle's permanent absence, the French i18n catalogue end to end, and the resolve dialog's `data-view-panel-first-seen`/`-last-seen` Paris-local-time contract (B5/D-05) verified byte-identical against the no-JS fallback's own rendered text.
- `companion/test_view_pages_helpers.py` extended with `detail_row_block()`/`table_markup()` (raw-markup-string locators for the handful of checks needing byte-for-byte attribute-value/substring assertions a parsed `companion_markup.Node` has no serializer for), `seed_gallery()`/`seed_unresolved_prefixes()`/`write_panel_file()` (tmp_path-backed fixture seeding, replacing `_mkstate()`/`tempfile.mkdtemp()`), and `strip_js_line_and_block_comments()` (a comment-only JS stripper that preserves string/template literals, since `companion_markup.strip_js_comments_and_strings()` would also erase the empty-string literal the one check needing it searches for).
- Every check that used to `open()` `companion/static/style.css`, `flight-rows.js`, `copy-button.js` or `panel-lookup.js` from disk now fetches them from a running `companion/app.py` via `served_stylesheet()`/`served_asset()` (a module-scoped `app`/`served_css`/`panel_lookup_js` fixture trio) and asserts on `companion_markup.declarations_for()` (CSS, including the two `@media (min-width: 960px)`-scoped reveal-rule checks via its `at_rules=` parameter) or the served JS text directly (the same string/regex logic as the legacy check, now against behaviour rather than source).
- `companion/test_view_pages.py` shrunk: the entire part-02 slice (original lines ~448-2756: Section 1b-X5 through the row-96 `check()` call) deleted from `main()`, plus the three lightbox token tuples, `_NEW_VIEW_PANEL_ATTR_NAMES` and `_read_panel_lookup_source()` (confirmed by grep to be used exclusively by this slice) and the now-unused `import html`. `_row_block()`, `_detail_row_block()`, `_table_markup()`, `_strip_js_comments()` and the seeding helpers all stay (still called by later, still-legacy sections). `EXPECTED_CHECK_COUNT` set to `73` (was `132`). The shrunk harness still runs 73/73 standalone and through `companion/test_legacy_harness_shim.py`.
- The ledger fragment's rows 38-96 flipped to `ported` with real `companion/test_view_pages_02.py::test_*` node ids and a `### Part 02 (plan 33-06)` note (33 D, 14 J, 5 C, 7 B rubric codes; 0 deleted - every check in this slice had a direct behavioural, served-asset or parsed-structure equivalent). `33-ledger-check.py --allow-pending companion/test_view_pages.py` confirms 169/169 baseline checks accounted for (96 ported, 73 pending).
- Full-suite sanity beyond the plan's own scoped verification: `pytest -n auto companion test-support server stub-server` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) - **1149 passed, 5 skipped, 0 failed** in 284.50s. No regression from this plan; `ruff check .` clean across the whole tree.

## Task Commits

1. **Task 1: First half of part 02 (checks 38-68)** - `7bd312f` (test)
2. **Task 2: Second half of part 02 (checks 69-96)** - `894dbd5` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `255d2da` (test)

## Files Created/Modified

- `companion/test_view_pages_02.py` - 59 native pytest tests (part 02)
- `companion/test_view_pages_helpers.py` - `detail_row_block()`/`table_markup()`/`seed_gallery()`/`seed_unresolved_prefixes()`/`write_panel_file()`/`strip_js_line_and_block_comments()` added for this and later parts of the chain
- `companion/test_view_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 73`, part-02 checks and their now-unused module-level constants removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md` - rows 38-96 ported, Part 02 note added

## Decisions Made

See `key-decisions` in the frontmatter above: `detail_row_block()`/`table_markup()` joining the shared helpers module (33-07/08 will need them too) versus `_row_markup()` staying module-local to avoid overloading 33-05's `row_block()` Node contract; the lightbox token tuples staying scoped to this module since nothing else uses them; and CSS checks uniformly using `declarations_for()` (including `at_rules=` for the media-query-scoped reveal rule) rather than a raw string search over served (but not disk-read) CSS text.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `button.calendar-disconnect-btn` selector, not `.calendar-disconnect-btn`**
- **Found during:** Task 1, first standalone run of `test_view_panel_trigger_reuses_the_small_grey_secondary_treatment`
- **Issue:** The check asserted `declarations_for(served_css, ".calendar-disconnect-btn")`, but `companion/static/style.css` scopes the rule to `button.calendar-disconnect-btn` (an element-qualified selector) - `declarations_for()`'s exact-selector-string match correctly raised `KeyError` rather than silently matching nothing.
- **Fix:** Changed the selector string to `"button.calendar-disconnect-btn"`, matching the real stylesheet.
- **Files modified:** `companion/test_view_pages_02.py`
- **Verification:** Re-ran the test standalone; passes.
- **Committed in:** `7bd312f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Purely a selector-precision correction discovered while writing the test against the real, current stylesheet - no scope creep, no other file touched.

## Issues Encountered

None beyond the deviation above. The legacy-slice deletion (Task 3) required three separate, non-adjacent line ranges (the part-02 `check()` calls, the three lightbox token tuples plus `_NEW_VIEW_PANEL_ATTR_NAMES`, and `_read_panel_lookup_source()`) - each range's exclusivity to this slice was confirmed with a `grep -n` count of every occurrence past line 2756 before deleting, so nothing still-legacy-and-still-needed was removed by accident (per `33-MIGRATION-RULES.md` section 1's "setup that remaining checks still need stays").

## User Setup Required

None.

## Next Phase Readiness

- 33-07/08 (parts 03-04 of this same chain) can extend `companion/test_view_pages_helpers.py` with whatever their own slices need (the legacy file's still-live `_detail_row_block()`/`_table_markup()`/`_strip_js_comments()`/`_mkstate()`/seeding helpers are the exact functions this plan's helpers additions already mirror), and continue shrinking `companion/test_view_pages.py`'s single `EXPECTED_CHECK_COUNT` line from `73`.
- The `served_asset()` + same-logic-on-served-text pattern for JS source-content checks (rows 41, 52, 54, 69, 71-79, 82) is directly reusable by 33-07/08 for any remaining `open()`-based JS checks in their own slices - no toolkit change was needed.
- No blockers. `companion/test_view_pages.py` still has 73 pending checks (Sections 1d onward - the day-separator/row-identity/refresh-region/reveal-animation checks, Flights' resolve-link fallback wording, Home's own extensive render/battery-ring/day-band suite, and the browser-only entrance-animation check) for the chain's remaining 2 plans.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 5 claimed created/modified files found on disk (`companion/test_view_pages_02.py`,
`companion/test_view_pages_helpers.py`, `companion/test_view_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md`,
this summary), and all 3 commit hashes (`7bd312f`, `894dbd5`, `255d2da`) found in
`git log --oneline --all`.
