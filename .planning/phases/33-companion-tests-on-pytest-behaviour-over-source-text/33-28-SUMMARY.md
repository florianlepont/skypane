---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 28
subsystem: testing
tags: [pytest, css-parsing, js-parsing, migration, companion]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "01"
    provides: "the migration ledger tool, baselines and the companion__test_status_pages.md fragment this plan's rows 140-171 build on"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture, reused here for the served-CSS/JS checks"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's css_rules()/declarations_for()/rules_with_selector() and companion/test_suite_guards.py's TST-10/12/13/14 guard"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "27"
    provides: "companion/test_status_pages_helpers.py's seeding wrappers and served_css_rules(), and the module-split naming convention (test_status_pages_NN.py) this plan extends"
provides:
  - "companion/test_status_pages_04.py: 30 native pytest node ids porting the original harness's 31 remaining check() calls #140-#171 (part 04 of the 7-plan chain) — the nested-card heading-to-content rhythm allowlist and its two CSS rhythm rules, the Resolution-statistics data-table--prose opt-out and Description-column muting (markup + builder + stylesheet), the registry's mobile .data-cards representation (completeness, toggle contract, pairing with the desktop table, stacked-cell/short-French-header fit, no-chrome-with-no-data), the humanised battery readout and its typographic split, the anomaly_active()/banner-presence agreement, the stat-tile reframe and tile-icon survival guards, the auto-refresh pill's markup/stylesheet contracts, the pipeline tile's second line (present/absent), the persistent honest-clock freshness note, four one-line UI-regression fixes, two spacing-pair guards, the <summary> accent rule, and the fetch/swap loop's cross-file contracts (interaction-skip guard, one-definition/one-key-set registry proof, server-rendered page key, the three things the loop must not repaint, Flights joining the loop, the new-row highlight diff)"
  - "companion/test_status_pages_helpers.py's strip_js_line_and_block_comments(): a comment-only JS stripper (mirrors the legacy harness's own _js_code_without_comments() idiom) for served-JS checks that need a served script's own quoted string literals intact, since companion_markup.strip_js_comments_and_strings() erases strings too"
  - "the audit's two named TST-12 evidence sites for this harness closed: the ticket-ID-in-a-freshness.js-comment / .planning CONTEXT.md-read check is deleted (P/J), and no status-pages test reads a .planning/ file any more"
  - "companion/test_status_pages.py shrunk further: EXPECTED_CHECK_COUNT collapsed from 177 to 146; part 04's 31 checks and the one closure only they used (_js_code_without_comments()) removed from main(); the now-unused history_page import dropped"
  - "the status-pages ledger fragment's rows 140-171 flipped (30 ported to single node ids, row 154 deleted with a P/J reason); 33-ledger-check.py --allow-pending confirms 317/317 baseline checks accounted for (170 ported, 1 deleted, 146 pending)"
affects: [33-29, 33-30, 33-31]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Every CSS check in this slice goes through companion_markup's structural API (css_rules()/declarations_for()/rules_with_selector()) against the served stylesheet fetched once via a module-scoped read-only server, exactly like 33-26/33-27 — including a combined-selector at-rule lookup (_rule_with_selectors(), new in this module) for the one rule inside @media (min-width: 960px) that raises three selectors' padding together, which declarations_for() alone cannot express (it merges by one selector at a time)"
    - "A served-JS check that needs the script's own quoted string literals intact (a selector, an attribute name, a constant value) cannot use companion_markup.strip_js_comments_and_strings() — it erases strings along with comments. This chain's own strip_js_line_and_block_comments() (added to test_status_pages_helpers.py) blanks only // and /* */ comments, mirroring the legacy harness's _js_code_without_comments() idiom exactly, so every ported JS check keeps looking for the same token it always looked for"
    - "A legacy check's source-text sub-clause with no observable consequence beyond a check the SAME test already makes structurally is dropped in place rather than carried forward or given its own deletion row: a redundant grep for a second REFRESH_SWAP_SELECTORS tuple literal in health_page.py is subsumed by the identity check beside it (health_page.REFRESH_SWAP_SELECTORS is registry[...]) — Python never interns two distinct tuple literals across modules as the same object, so the identity check already fails if a second definition existed"
  key-files:
    created:
      - companion/test_status_pages_04.py
    modified:
      - companion/test_status_pages.py
      - companion/test_status_pages_helpers.py
      - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md

key-decisions:
  - "The plan's own named P/J evidence check (the D-12-reversal-recorded-in-two-prose-sites check, reading freshness.js's header comment and a .planning CONTEXT.md file) is deleted, not rewritten: both halves assert plan-history prose with no rendered or served behaviour behind either — the exact TST-12 evidence site the audit named for this harness"
  - "Two more sub-clauses are dropped in place rather than ported verbatim or given their own deletion rows (TST-12 rubric S): the swap-registry check's redundant health_page.py source grep for a second tuple literal (subsumed by the identity check beside it) becomes hasattr(); the Flights-registry check's layout.py source grep for a comment paragraph explaining an exclusion in prose is dropped (a served page/script cannot disagree with a comment), keeping the check's structural half (which elements are covered/excluded) fully intact"
  - "The bare summary rule's accent-colour check keeps its rule-body clause (real declaration on a real selector) and drops the accent-reservation list's comment-only clause (TST-12 rubric C: the list lives in style.css's own opening comment block, not a rendered rule)"
  - "The combined-selector @media rule for .page-section/.theme-status/.battery-trend-section's desktop padding needed a new small helper, _rule_with_selectors() (selector-set + at_rules match), since declarations_for() only merges declarations for ONE selector string at a time and this rule's contract IS that all three selectors share one rule, not three separate ones with equal declarations"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 10min
completed: 2026-09-24
---

# Phase 33 Plan 28: Status-Pages Part 04 (Nested-Card Rhythm, Registry Mobile Cards, Auto-Refresh Pill/Loop Contracts, Fetch-Swap Cross-File Proofs) Summary

**Migrated the fourth of seven status-pages harness slices to native pytest — 31 legacy checks becoming 30 pytest node ids in a new `companion/test_status_pages_04.py` — closing the audit's own named evidence sites for a comment-quoted ticket ID and a `.planning/` CONTEXT.md read by deleting that check outright, and adding a comment-only (never string-erasing) JS stripper to the chain's shared helpers module so served-script checks that need a script's own quoted literals can still strip its comments.**

## Performance

- **Duration:** ~10 min (commit-to-commit)
- **Started:** 2026-09-24T20:59:09Z (first commit)
- **Completed:** 2026-09-24T21:08:46Z (last commit)
- **Tasks:** 3/3 completed
- **Files modified:** 4 (1 created, 3 modified)

## Accomplishments

- `companion/test_status_pages_04.py`: 30 native pytest node ids covering all 31 of part 04's remaining `check()` calls — the nested-card heading-to-content rhythm allowlist across all three nested Health cards plus its two CSS rhythm rules (the demotion rule and the prose-rhythm rule, source-ordered); the Resolution-statistics table's sole `data-table--prose` opt-out and the Description-column's end-to-end muting (markup count, `data_table()`'s `desc_columns` builder contract, and the stylesheet's 70%-muted/no-min-width/no-opacity/no-second-token guard); the registry's mobile `.data-cards` representation — completeness ahead of the desktop table, the toggle contract at both breakpoints, exact pairing with the desktop `<tr>`s by filter attributes, the stacked-cell/shortened-French-header fit (never a card fallback), and the standing no-chrome-with-no-data rule (including History/Airlines carrying zero of the new card class names); the humanised battery readout (id/role/value+detail spans/no-raw-ISO/title-equals-visible-text) cross-checked against `battery-trend.js`'s own served source, plus its typographic-split stylesheet guard; `anomaly_active()`/banner-presence agreement across three fixtures; the stat-tile reframe's markup survival; the tile-icon-only guard (zero glyphs in any Health heading, `ICON_BATTERY` gone); the auto-refresh pill's markup contract (seeded and fresh) and its full stylesheet contract (`.refresh-pill`/`[hidden]`/pill-scoped icon/`.page-header`'s absolute-positioning takeover, the named C hotspot from this plan's `<slice>`); the pipeline tile's second line, present and absent; the persistent honest `<time data-relative>` freshness clock (no relative-age suffix, full local timestamp in the title, zero Pause/Resume markup, correct source order and DOM position); four one-line UI-regression fixes held together as a set (`.banner` wrap, `.banner__pill`, `.airline-card__image`, `.data-table--prose` first-column nowrap, the battery caption's no-leading-em-dash); the `.dashboard-grid`/`.battery-trend-section` two-role spacing-pair guard and the desktop-padding/mobile-density pair (the other named C hotspot, requiring a new combined-selector `@media` lookup); the bare `<summary>` accent rule; and the fetch/swap loop's six cross-file contracts — the interaction-skip guard, the swap-selector registry's one-definition-site/one-key-set proof (both directions), the server-rendered page-key gate, the three things the loop must never repaint, Flights joining the loop, and the new-row highlight diff.
- The plan's own named P/J evidence check — reading `freshness.js`'s header comment for a ticket ID and the house `SUPERSEDED` token, and separately opening a `.planning/phases/06.6.3-.../06.6.3-CONTEXT.md` file for the same pair beside the original decision's wording — is **deleted**, not ported: both halves asserted plan-history prose with no rendered or served behaviour behind either, exactly the evidence site TST-12/the audit named for this harness. After this plan, `grep -c '"\.planning"' companion/test_status_pages.py` is 0.
- `companion/test_status_pages_helpers.py` gains `strip_js_line_and_block_comments()`: a small state machine blanking only `//`/`/* */` comments (never string/template literals), mirroring the legacy harness's own `_js_code_without_comments()` idiom exactly — needed because several of this slice's JS checks (the swap registry's key-set proof, the page-key gate, the three-things-not-repainted guard, the new-row highlight diff) look for a served script's own quoted selectors/attribute names/constants, which `companion_markup.strip_js_comments_and_strings()` would erase along with the comments.
- Two more source-text sub-clauses are dropped in place (TST-12 rubric S), each leaving its parent check's structural half fully ported: the swap-registry check's redundant `health_page.py` grep for a second `REFRESH_SWAP_SELECTORS = (` tuple literal is subsumed by the identity check beside it (`health_page.REFRESH_SWAP_SELECTORS is registry[...]`, which already fails if a second definition existed, since Python never interns distinct tuple literals across modules) and becomes `hasattr(health_page, "REFRESH_SWAP_SELECTORS")`; the Flights-registry check's `layout.py` grep for a comment paragraph explaining an exclusion in prose is dropped, since a served page or script cannot disagree with a comment's wording. A third clause (the bare `<summary>` rule's accent-reservation-list check) keeps its rule-body half and drops its header-comment half for the same reason (rubric C).
- Every CSS check in this slice goes through `companion_markup`'s structural API against the served stylesheet, per 33-FOLLOWUPS.md F-01 — including a new local helper, `_rule_with_selectors()`, for the one rule this slice needed that `declarations_for()` cannot express alone: a single `@media (min-width: 960px)` rule whose contract is that it covers THREE selectors (`.page-section`, `.theme-status`, `.battery-trend-section`) together, not three separately-declared rules that happen to agree.
- `companion/test_status_pages.py` shrunk further: `EXPECTED_CHECK_COUNT` dropped from 177 to 146; part 04's 31 checks and their own closure (`_js_code_without_comments()`, used only within this slice) removed from `main()`; the now-unused `history_page` import dropped (caught by ruff, fixed before commit). The shrunk harness re-verified 146/146 green standalone, and through `companion/test_legacy_harness_shim.py -k status_pages`.
- The ledger fragment's rows 140-171 flipped: 30 rows to `ported` (single node ids each — no parametrised splits needed in this slice), 1 row (154) to `deleted` with the plan's own specified reason (`P: asserted plan-history prose in a freshness.js header comment and in a .planning CONTEXT.md; no behaviour`). `33-ledger-check.py --allow-pending` confirms 317/317 baseline checks accounted for (170 ported, 1 deleted, 146 pending).
- Verification beyond the plan's own scoped checks: `companion/test_suite_guards.py test-support` (102 tests) stays green; `ruff check` clean on every file this plan touched; the FULL suite (`SKYPANE_REQUIRE_BROWSER=1 pytest -n auto companion test-support server stub-server deploy`) runs 2116 passed, 5 skipped, 0 failed.

## Task Commits

1. **Task 1: First half of part 04, including the P/J deletion (13 pytest nodes)** - `05e65ce` (test)
2. **Task 2: Second half of part 04 (17 more pytest nodes)** - `501fb6c` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `6102da2` (test)

## Files Created/Modified

- `companion/test_status_pages_04.py` - 30 pytest node ids porting part 04's 31 legacy checks
- `companion/test_status_pages_helpers.py` - `strip_js_line_and_block_comments()` added for this chain's remaining served-JS checks
- `companion/test_status_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 146`; part 04's checks and their closure removed; unused `history_page` import dropped
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md` - rows 140-171 flipped, Part 04 note added

## Decisions Made

See `key-decisions` in the frontmatter above: the plan's own named P/J check is deleted outright (no rendered/served behaviour in either half); two more source-text sub-clauses are dropped in place as redundant-with-a-structural-check or comment-only, rather than ported verbatim or split into their own deletion rows; and a new `_rule_with_selectors()` helper was needed for the one combined-selector `@media` rule this slice's desktop-padding check depends on.

## Deviations from Plan

None beyond the plan's own explicitly-named P/J deletion and C-hotspot rewrites (not deviations — Task 1/2's own instructions). One Rule 3 auto-fix, caught by ruff before any commit: removing the migrated checks from the legacy harness in Task 3 left `history_page` unused in `companion/test_status_pages.py`'s import list (its only remaining consumer, the no-cross-page-leak check, moved to the new module); the import was dropped and the file re-verified green.

## Issues Encountered

None beyond the `history_page` import cleanup above, caught and fixed before the Task 3 commit.

## User Setup Required

None.

## Next Phase Readiness

- 33-29..33-31 (the chain's remaining 3 plans) continue shrinking `companion/test_status_pages.py`'s single `EXPECTED_CHECK_COUNT` line (currently 146), starting from `_home_ctx()` and the Home/Frame-strip section that follows part 04's boundary.
- `strip_js_line_and_block_comments()` (new in `companion/test_status_pages_helpers.py`) is ready for reuse by any later part whose served-JS checks need a script's own quoted literal intact after stripping comments — no later plan needs to re-derive this idiom.
- `_rule_with_selectors()` (local to `test_status_pages_04.py`, not exported) is a one-off for this slice's combined-selector `@media` rule; a later part needing the same shape can copy it, following this chain's own precedent of small part-local helpers over a shared dependency.
- No blockers.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 5 claimed created/modified files found on disk
(`companion/test_status_pages_04.py`, `companion/test_status_pages_helpers.py`,
`companion/test_status_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_status_pages.md`,
this summary) and all 3 commit hashes (`05e65ce`, `501fb6c`, `6102da2`)
found in `git log --oneline --all`.
