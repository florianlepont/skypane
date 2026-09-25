---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 31
subsystem: testing
tags: [pytest, css-parsing, js-parsing, migration, companion, chain-closed]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_status_pages.md fragment this plan's final rows 293-317 close"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory/make_app_server fixtures, reused here for the served-CSS/JS checks and the two end-to-end checks"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for()/rules_with_selector()/custom_properties() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "30"
    provides: "companion/test_status_pages_helpers.py's strip_js_line_and_block_comments()/served_css_rules(), the four relocated helpers (_frame_strip_ctx, _css_source, _block, _TAB_BAR_BANNER) this plan's own local re-implementations follow the same shape as, and the shrunk legacy file (EXPECTED_CHECK_COUNT=25) this plan finishes emptying"
provides:
  - "companion/test_status_pages_07.py: 25 native pytest node ids porting the original harness's LAST check() calls #293-#317 (the tab bar's margin-fit/More-sheet/French-label/dropdown-max-height contracts, a structural style.css comment-terminator guard, the T3/T4 disclosure-marker/dead-sticky-claim sweep, freshness.js's backoff ladder and breathing-dot mechanism, the .resolve-context[hidden]/.flight-detail-row__grid CSS guards, the renamed hamburger-toggle label, the restored save-bar geometry beside the tab bar's own untouched stacking, the Health-tile/Frame-strip agreement across all four lateness states, the shared quiet-schedule link, the two server-rendered switches and their optimistic-failure toast, the freshness line's live dot and ticking clock, and the two end-to-end real-subprocess checks)"
  - "companion/test_status_pages.py DELETED outright (git rm) — the LAST legacy companion harness is retired. Confirmed no importer remains anywhere in the repo before deletion (grepped imports, open()/ast/Path()/string mentions across companion, test-support, conftest, the shim, and every other test module)"
  - "the status-pages ledger fragment closed: rows 293-317 flipped (all 25 ported, 0 deleted); 33-ledger-check.py WITHOUT --allow-pending confirms 317/317 baseline checks accounted for (313 ported, 4 deleted, 0 pending)"
  - "33-ledger-check.py --all confirms ALL 9 companion harnesses are now fully migrated (0 pending everywhere) — status-pages was the last chain open. skypane_test_support.legacy_companion_harnesses() now returns () and companion/test_legacy_harness_shim.py's parametrize list collapses to a clean pytest SKIP, never an error"
  - "the full suite (SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy) runs 2569 passed, 6 skipped, 0 failed"
affects: ["33-32", "33-33"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two checks (rows 299, 309) drop a legacy check's own literal raw-substring/at-rule-occurrence COUNT with no structural equivalent under companion_markup's parsed-Rule model, and substitute the actual structural invariant the count stood in for: row 299's '@media (prefers-reduced-motion: reduce) count == 2' becomes 'the one global *, *::before, *::after override exists, the one .js .mobile-nav opt-out exists, and summary::before carries no third redundant override'; row 309's 'dot-- substring count == 9' (5 of those 9 hits are prose inside COMMENTS, guard G1) becomes 'exactly the four .dot--{ok,warn,error,off} modifier classes exist and no fifth was added' — both documented in the new module's own docstring and the ledger's Part 07 note, following the same 'ported, sub-clause replaced, not counted as a separate deletion' precedent 33-30 set for rows 250/257"
    - "Row 298 (the stray-comment-terminator structural guard) is the one check in this slice that scans the SERVED stylesheet's raw character stream rather than parsing it with css_rules(): the defect it guards against (an unterminated /* */ comment silently swallowing the next rule) is exactly the shape a real CSS parser cannot see through either, so no parsed-structure rewrite is possible without losing the property under test — it still never reads the file from disk, only the bytes companion/app.py's STYLE_ROUTE serves over HTTP"
    - "The chain's two closing end-to-end checks (rows 316-317) move from the legacy harness's own local Harness/http_request/_NoRedirectHandler to companion/conftest.py's function-scoped make_app_server fixture and test-support/companion_app_server.py's login()/get(); row 316's previously-raw-substring STYLE_ROUTE assertions are rewritten structurally against rules_with_selector()/declarations_for() over that SAME real subprocess's own served bytes (33-FOLLOWUPS.md F-01), closing this chain's own open F-01 item before the closing plans have to sweep it"

key-files:
  created:
    - companion/test_status_pages_07.py
  modified:
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md
  # companion/test_status_pages.py: deleted (git rm)

key-decisions:
  - "Row 293's margin-fit check resolves --space-xs/--space-sm through companion_markup.custom_properties(':root') rather than the legacy check's own ad hoc re.findall() token scan over raw CSS text — the same structural token-resolution mechanism 33-27's test_status_pages_03.py already established for font-size/line-height tokens, applied here to spacing tokens for the first time in this chain"
  - "Row 309 is rewritten rather than deleted, even though its legacy literal count is entangled with comment prose: the PROPERTY under test (this plan added no new dot modifier class) still has an observable, comment-immune structural expression (the exact set of .dot--* selectors), so rubric C's 'ported: fetch and assert structurally' applies, not rubric C's 'deleted: asserted a stylesheet comment' branch — the comment pollution affected only the legacy MECHANISM, not the underlying claim"
  - "Rows 316-317 use two SEPARATE function-scoped make_app_server calls (not one shared server) even though both are read-only after seeding, because row 316's rich seed (device health, meta, unresolved prefixes, runway events) is unrelated to row 317's plain default-vendored-illustrations lookup — sharing one server would couple two independent fixtures for no xdist benefit, since neither test POSTs"
  - "requirements-completed intentionally left empty in this SUMMARY's frontmatter, matching 33-18's own precedent for a chain-closing plan: TST-10/12/13/14/15 are phase-wide and are marked complete only by the closing plans (33-32 guard tightening, 33-33 closing parity/verification), not by whichever plan happens to empty the last chain"

requirements-completed: []

# Metrics
duration: ~110min
completed: 2026-09-25
---

# Phase 33 Plan 31: Status-Pages Part 07 (Chain Closed — Last Legacy Companion Harness Retired) Summary

**Migrated the status-pages harness's final 25 legacy checks into `companion/test_status_pages_07.py`, deleted `companion/test_status_pages.py` outright, and closed its ledger fragment at 317/317 with 0 pending — the LAST legacy companion harness in the whole phase, confirmed by `33-ledger-check.py --all` reporting 0 pending across all 9 companion harnesses.**

## Performance

- **Duration:** ~110 min (commit-to-commit across 3 tasks, including a ~5 min full-suite verification run)
- **Started:** 2026-09-25T01:35:00Z (approx, immediately following 33-30's completion)
- **Completed:** 2026-09-25T03:25:00Z (full-suite verification run)
- **Tasks:** 3/3 completed
- **Files modified:** 3 (1 created, 1 deleted, 1 ledger fragment updated)

## Accomplishments

- `companion/test_status_pages_07.py`: 25 pytest node ids porting all 25 of part 07's legacy checks — the `.tab-bar__pill` horizontal-margin fit derived from `companion_markup.custom_properties(':root')` (CFG-82), the More sheet's upward-opening geometry with the legacy check's own stylesheet-COMMENT assertion dropped in place (guard G1: the geometry assertions already prove the behaviour a comment merely narrated), the French tab-bar labels and landmark, the nav-status span-on-Home/link-elsewhere contract, the ONE open-dropdown max-height with the dead `.mobile-nav__nav` selector sweep, a structural stray-comment-terminator scan over the SERVED stylesheet's raw character stream (the one check in this module that cannot be expressed via `css_rules()`, since the defect it catches is exactly the shape a real parser cannot see through either), the T3/T4 disclosure-marker/dead-sticky-claim sweep (including the tab bar's own out-of-flow "More" chevron and its inverted open-state rotation), `freshness.js`'s full backoff-ladder/in-flight-guard/targeted-swap/neutral-badge contract fetched via `served_asset()` and comment-stripped, the `.resolve-context[hidden]` and `.flight-detail-row__grid` CSS guards, the renamed hamburger-toggle accessible name, and the restored save-bar geometry beside the tab bar's own untouched stacking value and content clearance; the Health-tile/Frame-strip agreement across all four lateness states (nightly-held/inside-grace/past-grace/held-then-elapsed), a structural rewrite of the `dot--` modifier-class count (four real `.dot--{ok,warn,error,off}` selectors, not the legacy check's comment-polluted raw substring count of 9), the shared quiet-schedule link proven as ONE write site reaching both Home's and Display's own real `render()` output, the two server-rendered `role="switch"` controls' full accessible-state/no-JS-floor/pending-marker contract, the optimistic switch's transient failure toast (translated, no server internal, exactly one empty live region), the freshness line's neutral live dot and server-rendered ticking clock (never the ladder's frozen zero), `freshness.js`'s breathing-class state derivation (`syncLiveDot()` called from exactly the four places the loop's own state changes), and the two end-to-end checks against a real `companion/app.py` subprocess (health/airlines/flights routes, the served stylesheet now asserted structurally via `rules_with_selector()`/`declarations_for()` rather than a substring probe, the served freshness script, and the illustration route's normalized-bytes round trip).
- Two checks keep their `ported` status but replace a legacy sub-clause that had no structural equivalent (documented in the new module's own docstring and the ledger's Part 07 note, not counted as separate deletions, following 33-30's precedent for rows 250/257): row 299 drops the legacy `css_source.count("@media (prefers-reduced-motion: reduce)") != 2` literal (there is no `css_rules()`-exposed count of top-level at-rule block *occurrences*, only per-rule enclosing-context membership) and substitutes the two specific things that count actually protected — the one global override exists, the one `.js .mobile-nav` opt-out exists, and `summary::before` carries no third redundant override under the same at-rule; row 309 drops the legacy `css_source.count("dot--") != 9` literal (5 of those 9 raw-text hits are prose inside comments, guard G1) and substitutes the real, comment-immune invariant — exactly four `.dot--*` modifier classes exist and no fifth was added.
- All 9 style.css checks in this slice fetch the stylesheet `companion/app.py` actually serves and assert on it structurally via `companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`/`custom_properties()` — never a regex/substring probe over the raw served text (33-FOLLOWUPS.md F-01), including the chain's own closing end-to-end check (row 316), whose STYLE_ROUTE assertions were the legacy harness's own last remaining raw-substring CSS probe. The two served-JS checks (`freshness.js`, rows 300 and 315) fetch it via `served_asset()` and strip only comments with this chain's `strip_js_line_and_block_comments()`, never a disk read; the end-to-end check's own FRESHNESS_SCRIPT_ROUTE fetch is likewise comment-stripped before its needle checks, per this chain's JS convention.
- `companion/test_status_pages.py` — the LAST legacy companion harness — deleted outright (`git rm`), after grepping the WHOLE repo (not only imports — `open(`/`ast`/`Path(`/string mentions across companion, test-support, conftest, the shim, and every other test file) and confirming every remaining reference is prose in a comment or the frozen `ORIGINAL_COMPANION_HARNESSES` history tuple in `test-support/skypane_test_support.py` (used only to bound a guard's own exemption set, never opened). `skypane_test_support.legacy_companion_harnesses()` now returns `()`.
- The ledger fragment's rows 293-317 flipped: 25 rows to `ported` (each to its own single node id — no parametrization needed in this final slice), 0 deletions this part. A `### Part 07 (plan 33-31) — chain closed` note documents the rubric-code split and the two sub-clause replacements. `33-ledger-check.py companion/test_status_pages.py` **WITHOUT** `--allow-pending` confirms **317/317 baseline checks mapped (313 ported, 4 deleted, 0 pending)**.
- `33-ledger-check.py --all` (run across all 9 companion harnesses, WITHOUT `--allow-pending`) confirms **every companion harness is now 0 pending**: `test_contrast_check.py` 49/49, `test_i18n.py` 24/24, `test_view_pages.py` 169/169, `test_config_page.py` 276/276, `test_companion_app.py` 320/320, `test_status_pages.py` 317/317, `test_browser_ux_health_drawings.py` 11/11, `test_browser_ux_quiet_wake.py` 9/9, `test_browser_ux.py` 75/75. The legacy set derived from disk is empty; `companion/test_legacy_harness_shim.py`'s own parametrize list collapses to a clean pytest SKIP (`got empty parameter set for (harness)`), never an error — confirmed by running the shim module directly.
- Verification beyond the plan's own scoped checks: `companion/test_suite_guards.py` (110 tests, including `test-support`) stays green; `ruff check .` clean across the WHOLE tree; the FULL suite (`SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy`) runs **2569 passed, 6 skipped, 0 failed** in 304s — up from the prior baseline of 2544/5 because this plan adds 25 new node ids and the shim's now-empty parametrize contributes one additional documented skip. No new `DeprecationWarning`s from any file this plan wrote (the run's only warnings are the same pre-existing Pillow `getdata()` deprecations and the pytest-socket guard's own expected warning).

## Task Commits

1. **Task 1: First 12 of part 07's 25 checks (rows 293-304) into test_status_pages_07.py** - `8c39575` (test)
2. **Task 2: Remaining 13 checks (rows 305-317) and delete the legacy harness** - `e8d76fd` (test)
3. **Task 3: Close the ledger fragment, confirm the legacy set is empty** - `4b1ec86` (test)

## Files Created/Modified

- `companion/test_status_pages_07.py` - 25 pytest node ids, the chain's closing module
- `companion/test_status_pages.py` - deleted outright (`git rm`)
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md` - rows 293-317 ported, Part 07 closing note added, 0 pending

## Decisions Made

See `key-decisions` in the frontmatter above: the `custom_properties(':root')` token-resolution mechanism for the margin-fit check, the rubric-C rewrite (not deletion) for the `dot--` count check, the two-separate-servers choice for the two end-to-end checks, and leaving `requirements-completed` empty per 33-18's own precedent for a chain-closing (but not requirement-closing) plan.

## Deviations from Plan

None — plan executed exactly as written. The plan's own named hotspots (the `.resolve-context[hidden]` guard resolving `--space-xs`/`--space-sm` via `custom_properties`, and the illustration round trip running against a function-scoped server asserting served bytes) were handled with the mechanism the plan specified.

## Issues Encountered

One test assertion (`test_tab_bar_pill_horizontal_margin_lets_the_longest_label_fit`) initially indexed `custom_properties()`'s returned token dict by the BARE token name (matching the legacy check's own `re.findall()`-built dict, whose keys never carried a `--` prefix), but `companion_markup.custom_properties()` returns keys WITH the `--` prefix — caught immediately by the module's own first standalone test run, fixed by prefixing the lookup key, and re-verified green before the Task 1 commit.

## User Setup Required

None.

## Next Phase Readiness

- The status-pages migration chain (33-25 through this plan) is CLOSED: `companion/test_status_pages.py` no longer exists, all 317 of its baseline checks are accounted for (313 ported to new node ids across `companion/test_status_pages_01.py`..`_07.py`, 4 deleted with a stated reason), and its ledger fragment reports 0 pending.
- **All 9 companion harnesses are now fully migrated.** `skypane_test_support.legacy_companion_harnesses()` returns `()`; `companion/test_legacy_harness_shim.py` is now a no-op (empty parametrize, clean skip) but is NOT retired in this plan — per 33-MIGRATION-RULES.md section 1 and this plan's own instructions, retiring the shim itself is 33-32's job.
- Phase-wide requirements TST-10/TST-12/TST-13/TST-14/TST-15 are intentionally NOT marked complete in REQUIREMENTS.md by this plan (they are phase-wide and remain the closing plans' responsibility): 33-32 (guard tightening — including the 33-FOLLOWUPS.md F-01 sweep of the four modules it names, none of which is `test_status_pages_07.py`, since this plan's own end-to-end check already closed its own F-01 exposure) and 33-33 (closing parity/verification) are what actually close them.
- No blockers. The full suite (`pytest -n auto companion test-support server stub-server deploy`, `SKYPANE_REQUIRE_BROWSER=1`) is green at 2569 passed / 6 skipped / 0 failed, and `ruff check .` is clean across the whole tree.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-25*

## Self-Check: PASSED

`companion/test_status_pages_07.py`, the ledger fragment, and this summary
all found on disk; `companion/test_status_pages.py` confirmed deleted; all
three commit hashes (`8c39575`, `e8d76fd`, `4b1ec86`) found in
`git log --oneline --all`.
