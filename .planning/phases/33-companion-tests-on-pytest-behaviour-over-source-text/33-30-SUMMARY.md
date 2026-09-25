---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 30
subsystem: testing
tags: [pytest, css-parsing, js-parsing, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_status_pages.md fragment this plan's rows 245-292 build on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture, reused here for the served-CSS/JS checks"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for()/rules_with_selector() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "29"
    provides: "companion/test_status_pages_helpers.py's seeding wrappers and strip_js_line_and_block_comments(), the module-split naming convention, and the three relocated helpers (_home_ctx, _NAV_STATUS_DEVICE_CFG, _card_slice) this plan's own relocation (_frame_strip_ctx, _css_source, _block, _TAB_BAR_BANNER) follows the same precedent for"
provides:
  - "companion/test_status_pages_06.py: 46 native pytest node ids (one per ported row — no row in this slice needed parametrization) porting the original harness's checks #245-#292 — the lightbox replace form (unique/labelled file input, cache-busting keyed on the override file's own mtime, hostile-name escaping, no revert control, retired-surface sweep, the shared icon sprite, the zone's own markup/styling contract), the D19 drag-and-drop upload affordance (byte-identical native controls across all three upload-form renderings, the JS-gate boundary, the framing preview's reserved aspect-ratio), the D-01/D-02/D-04..D-07 coverage-gap block, the D-08/D-10/D-12 manual-resolution card states (_airline_card_html()'s widened manual_info parameter, the superseded fallback, grid injection), the D-03/D-10..D-13 conditional resolve section (all four server-derived states, the datalist contract, hostile-value escaping, CR-02's gap-cleared reachability, the page's own top-to-bottom composition order), the D-06..D-08 manual-resolutions summary line and retired management-table symbol sweep, the WR-06 cross-module template equality check, the D-09 delete-form's two call sites, list-filter.js's new [data-filter-set] hook, the phase 14 Component-Inventory CSS sweep, the D-03/X2/B13/C2/C5/C6/T9 Frame-strip behaviour and CSS, and the X9/D-10 bottom tab bar's CSS geometry, surface and active idiom"
  - "the audit's remaining status-pages TST-12 evidence for source-text reads closed for this slice: no check in the new module opens a production .py/.html/.css/.js file as text; every served-CSS assertion (7 style.css checks) is rewritten structurally against companion_markup.css_rules()/declarations_for()/rules_with_selector() over a served stylesheet, and the one served-JS check (list-filter.js) fetches it via served_asset() and strips only comments"
  - "companion/test_status_pages.py shrunk further: EXPECTED_CHECK_COUNT collapsed from 73 to 25; part 06's 48 checks removed from main(); four small helpers (_frame_strip_ctx, _css_source, _block, _TAB_BAR_BANNER) that used to sit beside their own first use inside part 06's checks are relocated (not deleted) because later, not-yet-migrated part-07 checks still depend on them"
  - "the status-pages ledger fragment's rows 245-292 flipped (46 ported, 2 deleted); 33-ledger-check.py --allow-pending confirms 317/317 baseline checks accounted for (288 ported, 4 deleted, 25 pending)"
affects: [33-31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The 7 served-CSS checks in this module iterate css_rules()'s parsed Rule.selectors/Rule.declarations directly (a per-selector regex boundary match for class/attribute membership, a per-declaration-value substring check for a var(--token) reference) rather than a regex/substring probe over the raw served stylesheet text — the structural discipline 33-FOLLOWUPS.md F-01 asks the closing plans to sweep the rest of the chain for"
    - "The big Component-Inventory CSS check (row 277) and the tab-bar geometry check (row 292) both drop their legacy check's own stylesheet-HEADER-COMMENT sub-clause outright (rubric C: a comment carries no rendered behaviour, guard G1) while keeping every declaration-level assertion intact — the same 'drop the comment clause, keep the behaviour clause' pattern 33-29 established for row 172's freshness-line check"
    - "Four closures (_frame_strip_ctx, _css_source, _block, _TAB_BAR_BANNER) that this plan's own part-06 checks defined are NOT deleted with their checks because later, not-yet-migrated part-07 checks (33-31's own slice) still call them — relocated in place to a small 'shared helpers still used by later checks' block immediately after the check() closure, the identical precedent 33-29 set for _home_ctx/_NAV_STATUS_DEVICE_CFG/_card_slice"

key-files:
  created:
    - companion/test_status_pages_06.py
  modified:
    - companion/test_status_pages.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md

key-decisions:
  - "Row 285 (companion/layout.py grepped for a retired age_seconds(next_wake...) re-derivation) is deleted, not rewritten: this same module's own frame-strip behaviour checks (rows 278-284) already pin every late/due/parked/grace-window scenario against frame_state.resolve_state()'s own output — a re-derivation that quietly diverged would already fail the grace-window or parked check, so the source-text ban protects no behaviour that is not already proven"
  - "Row 291 (the style.css header comment recording the C2 accent-reservation delta) is deleted, not rewritten: it asserted a stylesheet COMMENT's prose, which carries no rendered behaviour under guard G1 — the actual C2 behaviour (the strip's switch buttons no longer inheriting the primary accent fill) is what row 287's rewritten check already proves against the served stylesheet's own rule bodies"
  - "Row 250 (the icon-sprite check) and row 257 (the gap-card filter-group check) each drop one now-redundant source-file-scan sub-clause in place, keeping the rest of the check as 'ported': both source scans proved only 'the markup was not hand-typed', a fact the SAME check's own rendered-output assertions (the <use> tag count/class, the rendered attribute's own regex match) already make true regardless of how the markup was produced"
  - "The huge Component-Inventory sweep (row 277) and the tab-bar geometry check (row 292) both use declarations_for()'s at_rules= parameter to distinguish the same selector's base-rule declarations from its @media-scoped declarations (e.g. .tab-bar is display:none outside the media query and display:flex inside it) — the exact mechanism the plan's own hotspot note named"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: ~70min
completed: 2026-09-25
---

# Phase 33 Plan 30: Status-Pages Part 06 (Lightbox Replace Form, Drop-Zone Upload, Coverage-Gap Block, Manual-Resolution Card States, Conditional Resolve Section, Frame-Strip Behaviour/CSS, Bottom Tab Bar CSS) Summary

**Migrated the sixth of seven status-pages harness slices to native pytest — 48 legacy checks becoming 46 pytest node ids in one new module — converting all 7 remaining style.css disk reads in this slice to structural `companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()` assertions over the served stylesheet, the one served-JS check to a `served_asset()` fetch, and dropping two checks outright (a redundant source-text lateness-derivation grep and a stylesheet-comment assertion) with no independent behaviour left to protect.**

## Performance

- **Duration:** ~70 min (commit-to-commit)
- **Started:** 2026-09-25T00:15:00Z (approx, immediately following 33-29's completion)
- **Completed:** 2026-09-25T01:25:00Z (full-suite verification run)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 2 modified)

## Accomplishments

- `companion/test_status_pages_06.py`: 46 pytest node ids covering all 48 of part 06's legacy checks (2 dropped outright) — the lightbox replace form's unique/labelled file input, cache-busting keyed on the override file's own mtime (with the replace-action trigger deliberately staying un-busted), hostile-airline-name escaping (including inside `data-view-panel-replace-action`), the "no revert/reset control" guard, a retired-surface sweep (no dead markup/stylesheet-rule/module-symbol left behind), the shared icon sprite's `<use>` count and class, and the zone's own five-child markup order plus its served-stylesheet class/pseudo-element contract; the D19 drag-and-drop affordance's three byte-identical upload-form renderings (native controls, the drop zone as the form's LAST child, the input-naming hook), the Step-B edit-mode id-uniqueness/JS-gate-boundary proof, and the framing preview's `--upload-preview-ratio` contract (fed from `illustration_normalize.ILLUSTRATION_TARGET_SIZE`, no CSS fallback, every `.upload-drop*` selector resolving on a boundary, no `:hover`/colour-literal in that rule family); the coverage-gap block's threshold/sort/cap/overflow math, the gap card's own markup shape and attribute vocabulary, its `gap{index}`-prefixed filter-group vocabulary never colliding with a curated card's bare-integer group, and hostile-callsign escaping; `_airline_card_html()`'s widened `manual_info` parameter across the None/active-with-artwork/active-needs-artwork/superseded states, the live-vs-cleared-gap sighting-context fallback, and `render()`'s grid-injection step adding exactly one card for a genuinely novel manual name; the conditional resolve section's all-four server-derived states (absent/Step-A/Step-B/already-done), the datalist's exhaustive `<option>` contract, hostile-value escaping plus WR-04's case/whitespace prefix normalisation, CR-02's Step-B-still-reachable-after-D-14-clears-the-gap regression proof, and the page's own top-to-bottom composition order; the manual-resolutions summary line's empty/populated states and its retired-copy sweep, the retired D-06 supersession symbols' `not hasattr` proof (the slice's named S-rubric hotspot), the six-function/eight-constant retired management-table symbol sweep, the WR-06 cross-module template equality check, and the D-09 delete-form's two call sites (dialog `action=""`, no-JS fallback with the real action); `list-filter.js`'s new `[data-filter-set]` hook fetched via `served_asset()` and comment-stripped with `strip_js_line_and_block_comments()`; the phase-14 Component-Inventory CSS sweep (the slice's other named C-rubric hotspot) rewritten entirely against the served stylesheet's parsed rules; the D-03/X2 Frame-strip behaviour suite (the nightly quiet-hours regression, the grace window's byte-identical due copy, the late/parked states, the no-checkin state, the three-cell row structure, the switch-form attribute count) and its B13/C2/C5/C6/T9 CSS (`.frame-strip__cells`, `.frame-strip__cell button`'s source order and quiet wash, `.stat-tile:not(.frame-strip):hover`, the retired heading-size override's absence, `.time-value`/`.time-value--primary`); and the X9/D-10 bottom tab bar's CSS geometry, surface and active idiom (the slice's other named C-rubric hotspot), rewritten with `declarations_for()`'s `at_rules=` parameter distinguishing `.tab-bar`'s base `display: none` from its `@media (max-width: 959.98px)`-scoped `display: flex` geometry.
- Two checks are deleted outright (TST-12 rubric S/C), both documented in the new module's own comments and docstrings: row 285 (`companion/layout.py` grepped for a retired `age_seconds(next_wake...)` re-derivation) has no behaviour independent of the frame-strip checks this same module already carries (rows 278-284), which would already fail if `layout.py` quietly re-derived lateness on its own; row 291 (the style.css header comment recording the C2 accent-reservation delta) asserted a stylesheet COMMENT's prose, which carries no rendered behaviour under guard G1 — the real C2 behaviour is what the rewritten `.frame-strip__cell button` check already proves.
- Two more checks keep their `ported` status but drop one now-redundant source-file-scan sub-clause each (documented at each test's own docstring, not counted as separate ledger deletions): the icon-sprite check (row 250) drops a `companion/pages/airlines_page.py` source scan for a hand-written glyph token, and the gap-card filter-group check (row 257) drops a source scan for the `'data-filter-group="gap%d"'` format-string literal — both redundant with the SAME check's own rendered-output assertions.
- All 7 style.css checks in this slice fetch the stylesheet `companion/app.py` actually serves and assert on it structurally via `companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`, iterating parsed `Rule.selectors`/`Rule.declarations` — never a regex/substring probe over the raw served text (33-FOLLOWUPS.md F-01). The one served-JS check (`list-filter.js`) fetches it via `served_asset()` and strips only comments with this chain's `strip_js_line_and_block_comments()`.
- `companion/test_status_pages.py` shrunk further: `EXPECTED_CHECK_COUNT` dropped from 73 to 25; part 06's 48 checks removed from `main()`. Four closures/constants (`_frame_strip_ctx`, `_css_source`, `_block`, `_TAB_BAR_BANNER`) that used to sit beside their own first use inside part 06's checks are relocated in place, right after the `check()` closure, because later, not-yet-migrated part-07 checks still call them — the identical precedent 33-29 set for `_home_ctx`/`_NAV_STATUS_DEVICE_CFG`/`_card_slice`.
- The ledger fragment's rows 245-292 flipped: 46 rows to `ported` (each to its own single node id — no parametrization needed in this slice), 2 rows (285, 291) to `deleted` with rubric S/C reasons. `33-ledger-check.py --allow-pending` confirms 317/317 baseline checks accounted for (288 ported, 4 deleted, 25 pending).
- Verification beyond the plan's own scoped checks: `companion/test_suite_guards.py` (70 tests) stays green and the new module is picked up by its per-file parametrize automatically (disk-derived, no guard edit needed); `ruff check` clean on every file this plan touched; the FULL suite (`SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy`) runs **2544 passed, 5 skipped, 0 failed** in 311s — no new failures, no new `DeprecationWarning`s from any file this plan wrote (the run's only warnings are the same pre-existing Pillow `getdata()` deprecations and the pytest-socket guard's own expected warning, unrelated to this plan).

## Task Commits

1. **Task 1: First 24 of part 06's 48 checks (rows 245-268) into test_status_pages_06.py** - `35ac6ef` (test)
2. **Task 2: Remaining 24 checks (rows 269-292) into test_status_pages_06.py** - `fc728e1` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `c78c5c5` (test)

## Files Created/Modified

- `companion/test_status_pages_06.py` - 46 pytest node ids porting all 48 of part 06's legacy checks (2 dropped outright, 2 more dropping one redundant sub-clause each)
- `companion/test_status_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 25`; part 06's checks removed; four still-needed helpers relocated
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md` - rows 245-292 flipped, Part 06 note added

## Decisions Made

See `key-decisions` in the frontmatter above: rows 285 and 291 are deleted outright (no behaviour beyond what other checks in the same module already prove, or a stylesheet-comment assertion with no rendered behaviour); rows 250 and 257 each drop one redundant source-scan sub-clause while staying `ported`; the Component-Inventory sweep and the tab-bar geometry check both use `declarations_for()`'s `at_rules=` parameter to distinguish a selector's base-rule declarations from its media-scoped ones.

## Deviations from Plan

None - plan executed exactly as written. Every hotspot the plan named (the selector-inventory CSS sweep, the tab-bar `display:none`-then-fixed-at-media-query CSS check, the retired D-06 supersession symbols' `not hasattr` proof) was handled with the mechanism the plan specified.

## Issues Encountered

One test assertion (`test_frame_strip_cell_button_quiet_rule_after_submit_no_important_no_id`) initially compared a declaration value with strict equality against a bare colour-mix expression, but the served rule's `border` property carries that value inside a full shorthand (`1px solid color-mix(...)`) — caught immediately by the module's own first standalone test run, fixed by checking substring membership across the joined declaration values instead of exact equality, and re-verified green before the Task 1 commit.

## User Setup Required

None.

## Next Phase Readiness

- 33-31 (the chain's final plan) continues shrinking `companion/test_status_pages.py`'s single `EXPECTED_CHECK_COUNT` line (currently 25), covering rows 293-317, and per `33-MIGRATION-RULES.md` section 1 is responsible for `git rm`-ing the legacy file entirely once its own slice lands, running `LEDGER` (without `--allow-pending`) to confirm zero pending rows.
- The four relocated helpers (`_frame_strip_ctx`, `_css_source`, `_block`, `_TAB_BAR_BANNER`) are ready for 33-31 to consume as-is; that plan should either port each helper alongside its own last remaining caller or fold it into `companion/test_status_pages_helpers.py` if it is still needed after the legacy file is deleted (it should not be, since 33-31 is the chain's last plan).
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-25*

## Self-Check: PASSED

All 4 claimed created/modified files found on disk
(`companion/test_status_pages_06.py`, `companion/test_status_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md`,
this summary) and all 3 commit hashes (`35ac6ef`, `fc728e1`, `c78c5c5`)
found in `git log --oneline --all`.
