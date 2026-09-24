---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 11
subsystem: testing
tags: [pytest, config-page, aspect-card, css-parser, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture and test-support/companion_app_server.py's served_stylesheet()/served_asset(), needed here for the CSS/JS-reading checks"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "10"
    provides: "companion/test_config_page_helpers.py's write_device_config() and the config-page chain's tmp_path/no-Harness conventions, part 02's 51 migrated checks"
provides:
  - "companion/test_config_page_03.py: 73 native pytest tests porting part 03 of companion/test_config_page.py (original check() calls #85-#145, 61 baseline checks) - handle_post()'s field-level errors dict, the retired LED-route/helper-symbol guards, runway-image detection and runway_fieldset() image emission, cross-file DOM-contract guards between config_page.py and dirty-state.js/style.css, the theme-chip grid's markup/selection-state contract (including the live :has(input:checked) treatment and its saved-but-unchecked Current badge), the arrivals/calendar theme override's clearable contract, and the Aspect card's own accordion shape and per-flight rules editor markup"
  - "companion/test_config_page_helpers.py extended: ASPECT_RETIRED_MARKUP_TOKENS / aspect_usage_row_bounds() / rules_row_segment() (shared Aspect-card locators parts 04/05 also need) and strip_js_line_and_block_comments() (a comments-only JS stripper that preserves string literals, for checks that search served JS for a quoted token)"
  - "companion/test_config_page.py shrunk: EXPECTED_CHECK_COUNT = 131 (was 192), 131/131 still pass standalone and through the shim"
  - "the config-page ledger fragment's rows 85-145 flipped (all 61 ported, zero deletions), Part 03 note added"
affects: [33-12, 33-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two style.css checks named as this plan's own hotspot (STATIC_SAVE_FALLBACK_ATTR selector absence, the retired .save-status selector absence) are rewritten structurally over companion_markup.css_rules() - iterating every parsed Rule's own selectors list rather than scanning raw text for a substring or a regex `\\bclass\\b[^{}]*\\{` shape - so a comment merely naming the retired token can never trip the assertion and a genuine live rule referencing it always would"
    - "The remaining ~9 large style.css checks in this slice (selected-card wash/live-:has()-state/specificity-ordering/keyframes-reference) keep their original index-plus-window/regex logic verbatim, operating on `served_css` (fetched over HTTP from a real companion/app.py via `served_stylesheet()`) instead of a disk-read file - following 33-10's own precedent that a source-order/specificity/brace-nesting relationship a flat selector-to-declaration lookup does not simplify is fine to keep as a served-text scan, since TST-12's concern is reading PRODUCTION SOURCE as text, not the parsing technique applied to what the server actually sent over HTTP"
    - "A NEW helper, `strip_js_line_and_block_comments()` (companion/test_config_page_helpers.py), strips only `//`/`/* */` JS comments and never touches string/template literals - added because one check (the live theme-preview crossfade) needs to find quoted string-literal tokens (`\"load\"`, `\"error\"`, a CSS class name used as a JS string) that `companion_markup.strip_js_comments_and_strings()` would erase along with the comments, mirroring the identically-named/shaped helper 33-07 already added to companion/test_view_pages_helpers.py for the same reason"
    - "Three Aspect-card helpers this slice's checks need (`_ASPECT_RETIRED_MARKUP_TOKENS`/`_aspect_usage_row_bounds()`/`_rules_row_segment()`) are still used by NOT-yet-migrated checks further down the legacy harness's main() (parts 04/05, rows 146+): rather than deleting them, they are relocated earlier in main()'s source order (pure function/constant definitions have no execution-order side effect) and this plan's own equivalents (`ASPECT_RETIRED_MARKUP_TOKENS`/`aspect_usage_row_bounds()`/`rules_row_segment()`) are added to the shared companion/test_config_page_helpers.py module instead of being re-derived per part"

key-files:
  created:
    - companion/test_config_page_03.py
  modified:
    - companion/test_config_page_helpers.py
    - companion/test_config_page.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md

key-decisions:
  - "Rubric split across the 61 baseline checks: 22 B (handle_post()/render() persistence and retired-symbol calls asserted on real output), 1 T (the does-not-exist image_dir check, rewritten onto a never-created tmp_path subpath rather than tempfile.mkdtemp()+shutil.rmtree(), satisfying this plan's own TST-13 must-have), 21 D (render()/runway_fieldset()/_theme_chip_grid_html()/Aspect-card markup-shape checks over the returned HTML string, kept as substring/regex since parse_html() would not materially simplify a narrow single-fragment fact), 11 C (style.css fetched via served_stylesheet() - 2 of the 11 rewritten structurally via css_rules() per this plan's own hotspot, the other 9 kept as index/regex scans over the served text), 5 J (dirty-state.js fetched via served_asset()), 1 mixed C+J (the live theme-preview crossfade check, which needs both a served style.css declaration and a served, comment-but-not-string-stripped theme-preview.js). Zero deletions - every one of the 61 baseline checks in this slice asserts real behaviour, not source text or a comment"
  - "Three loop-shaped legacy checks (rows 87, 123, 124) are converted to @pytest.mark.parametrize with readable ids rather than kept as an internal for-loop inside one test function, following 33-10's own precedent - each parametrized case gets its own tmp_path/seed, independent of the others, strictly stronger than the original's single shared-state sequential loop"
  - "The two named-hotspot style.css checks (STATIC_SAVE_FALLBACK_ATTR / .save-status) iterate companion_markup.css_rules()'s own parsed Rule.selectors lists rather than regex-matching the raw served text for a `\\bclass\\b[^{}]*\\{` rule-opening shape - the parsed representation cannot be fooled by a selector string that merely LOOKS like it opens a rule inside a longer at-rule prelude, and it is the mechanism this plan's must_haves explicitly names"

patterns-established: []

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: ~30min
completed: 2026-09-24
---

# Phase 33 Plan 11: Config-Page Errors Dict, LED/Helper Retirements, Theme-Chip Selection State, and Aspect Card (Part 03) Summary

**Migrated the third 61 of `companion/test_config_page.py`'s 276 `check()` calls to native pytest in `companion/test_config_page_03.py` — handle_post()'s field-level errors dict, the retired LED-route/helper-symbol guards, runway-image detection, cross-file DOM-contract guards against dirty-state.js/style.css (including two structural css_rules()-based selector-absence checks named as this plan's own hotspot), the theme-chip grid's live-selection-state treatment, the arrivals/calendar theme override's clearable contract, and the Aspect card's full accordion shape plus its per-flight rules editor markup.**

## Performance

- **Duration:** ~30 min (commit-to-commit)
- **Started:** 2026-09-24T16:21:41Z (first commit)
- **Completed:** 2026-09-24T16:31:46Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 3 modified — test_config_page_helpers.py, test_config_page.py, and the ledger fragment)

## Accomplishments

- `companion/test_config_page_03.py`: 73 native pytest tests (61 original `check()` calls, three case tables parametrized with ids) porting part 03 in full — `handle_post()`'s new `errors` dict parameter (field-level messages, the all-or-nothing pre-check, the legacy no-errors contract intact), the retired separate-LED-route and five retired helper-constant guards (`hasattr()` against the live module, never source text), runway-image detection and `runway_fieldset()` image emission (including the does-not-exist `image_dir` check rewritten onto a never-created `tmp_path` subpath), several cross-file DOM-contract guards (the restored `dirtySectionLabels()`/beforeunload/quiet-preset wiring, the live theme-preview crossfade spanning both a served stylesheet declaration and a served, string-literal-preserving JS scan), the theme-chip grid's markup and its full live `:has(input:checked)` selection-state treatment (border/wash/check-glyph/hover-restore/transition/scale, and the saved-but-unchecked quiet "Current" badge), the arrivals/calendar theme override's clearable empty-string contract, and the Aspect card's own accordion shape (row order, exactly-one-open, palette counts, retired-markup absence) plus its per-flight rules editor (empty state, ordering, copy, pill badges, confirmed remove).
- Two style.css checks this plan's own hotspot names by property (no rule selector anywhere still references the retired `STATIC_SAVE_FALLBACK_ATTR` token; no rule selector anywhere still targets the retired `.save-status` class) are rewritten to iterate `companion_markup.css_rules()`'s own parsed `Rule.selectors` lists over the served stylesheet, rather than a raw index/regex scan — a comment merely naming the retired token can never trip either assertion. A third check (`.theme-status`/`.runway-row`/`.settings-checkbox`/`.theme-chip*` selectors) is rewritten onto `declarations_for()` for its "selector X declares Y" facts. The remaining ~9 large style.css checks (selected-card wash, the live `:has()`-state treatment across both card components, specificity ordering, keyframes reference) keep their original index/regex logic verbatim, now operating on `served_css` (fetched over HTTP from a real `companion/app.py`) instead of a disk-read file — they assert source-order/specificity/brace-nesting relationships a flat selector lookup would not simplify, following 33-10's own precedent.
- A new `strip_js_line_and_block_comments()` helper (comments-only, string-literals-preserving) was added to `companion/test_config_page_helpers.py` for the one check that needs to find quoted string-literal tokens (`"load"`, `"error"`, a CSS class name) in served JS — `companion_markup.strip_js_comments_and_strings()` would erase those tokens along with the comments. Three Aspect-card helpers (`ASPECT_RETIRED_MARKUP_TOKENS`/`aspect_usage_row_bounds()`/`rules_row_segment()`) were also added there, since parts 04/05 need the same locators and the legacy harness's own originals must stay in place for its own not-yet-migrated checks.
- `companion/test_config_page.py` shrunk: the 61 migrated `check()` calls and their now-unused closures removed from `main()`, `EXPECTED_CHECK_COUNT` collapsed from 192 to 131, and the two still-needed legacy helpers (`_STATIC_DIR`/`_read_static`, `_rules_row_segment`) relocated earlier in source order rather than deleted (they are pure function/constant definitions with no execution-order side effect, still consumed by parts 04/05's own checks). Confirmed 131/131 pass standalone (`server/.venv/bin/python3 companion/test_config_page.py`) and through `companion/test_legacy_harness_shim.py -k config_page`.
- The ledger fragment's rows 85-145 flipped to `ported` (all 61, targeting real `companion/test_config_page_03.py::test_*` node ids; three parametrized rows point at their primary id with the rest listed in this SUMMARY's frontmatter/notes) and a `### Part 03 (plan 33-11)` note added (22 B, 1 T, 21 D, 11 C, 5 J, 1 mixed C+J rubric codes; zero deletions). `33-ledger-check.py --allow-pending companion/test_config_page.py` confirms 276/276 baseline checks accounted for (144 ported, 1 deleted, 131 pending).
- Full-suite sanity beyond the plan's own scoped verification: `pytest -n auto companion test-support server stub-server` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium via `PLAYWRIGHT_BROWSERS_PATH=/tmp/skypane-pw-browsers`) — 1577 passed, 5 skipped, 0 failed (the 5 skips are the documented root-sandbox `requires_non_root` skips, not failures). No regression from this plan.

## Task Commits

1. **Task 1: First half of part 03 (checks #85-#114)** - `f0cd1ec` (test)
2. **Task 2: Second half of part 03 (checks #115-#145)** - `5e8a8e4` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `9d3ac0d` (test)

## Files Created/Modified

- `companion/test_config_page_03.py` - 73 native pytest tests (part 03)
- `companion/test_config_page_helpers.py` - three shared Aspect-card locators and a comments-only JS stripper added
- `companion/test_config_page.py` - shrunk to `EXPECTED_CHECK_COUNT = 131`, part-03 checks and their now-unused closures removed, two still-needed helpers relocated
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md` - rows 85-145 flipped, Part 03 note added

## Decisions Made

See `key-decisions` in the frontmatter above: the 22 B / 1 T / 21 D / 11 C / 5 J / 1 mixed rubric split with zero deletions, the two named-hotspot `css_rules()` rewrites for selector absence, the new `strip_js_line_and_block_comments()` helper (and why `strip_js_comments_and_strings()` cannot be used for that one check), and why the remaining large style.css checks keep their original index/regex logic over served (not disk) text rather than a full `css_rules()` rewrite.

## Deviations from Plan

None - plan executed exactly as written. The two must_haves the plan named explicitly (the does-not-exist path check writing only under `tmp_path`; the two named style.css checks asserting via `css_rules()` over the served stylesheet) were both implemented as specified, and the shrunk legacy harness's `EXPECTED_CHECK_COUNT` equals the ledger fragment's own pending-row count (131) as required.

## Issues Encountered

One arithmetic correction during Task 3: the ledger-check tool rejects a single ledger row pointing at a comma-joined list of parametrized node ids (it expects one node id per row, matching 33-10's own convention of "primary id, rest listed in the SUMMARY/note"). Caught immediately by running `33-ledger-check.py --allow-pending` before committing; fixed by pointing each of the three parametrized rows (87, 123, 124) at their first case's node id alone, with the full id list already recorded in this plan's own ledger note. No commit ever carried the invalid format.

## User Setup Required

None.

## Next Phase Readiness

- 33-12/33-13 (parts 04-05 of this same chain) can extend `companion/test_config_page_helpers.py` further and reuse the `app`/`served_css`/`served_asset`-fixture pattern this plan's own module declares locally (33-MIGRATION-RULES.md section 2 forbids editing shared `conftest.py`, so each part-file that needs the served-stylesheet/asset fixtures declares its own local `app`/`served_css` module-scoped fixtures, following 33-06/33-10's precedent), and continue shrinking `companion/test_config_page.py`'s single `EXPECTED_CHECK_COUNT` line from its current 131.
- `companion/test_config_page.py` still has 131 pending checks (parts 04-05) for the chain's remaining 2 plans.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk (`companion/test_config_page_03.py`,
`companion/test_config_page_helpers.py`, `companion/test_config_page.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_config_page.md`),
this summary, and all 3 commit hashes (`f0cd1ec`, `5e8a8e4`, `9d3ac0d`) found in `git log --oneline --all`.
