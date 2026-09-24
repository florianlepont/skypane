---
phase: 33-companion-tests-on-pytest-behaviour-over-source-text
plan: 05
subsystem: testing
tags: [pytest, html-parser, css-parser, companion, history-page, migration]

# Dependency graph
requires:
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "02"
    provides: "companion/conftest.py's module_app_server_factory fixture and companion_app_server.py's served_stylesheet()"
  - phase: 33-companion-tests-on-pytest-behaviour-over-source-text
    plan: "03"
    provides: "test-support/companion_markup.py's parse_html()/Node.select()/find_all() and css_rules()/declarations_for(), companion/test_suite_guards.py's TST-10/12/13/14 guard, and the disk-derived legacy companion harness set"
provides:
  - "companion/test_view_pages_helpers.py: seed_runway_events()/history_ctx()/row_block() - the seeding/render helpers the view-pages migration chain (33-05..33-08) shares, __test__ = False, no Harness/http_request/_NoRedirectHandler copy"
  - "companion/test_view_pages_01.py: 37 native pytest tests porting part 01 of companion/test_view_pages.py (original check() calls #1-#37) - History's empty state, newest-first ordering, the reused render-module presentation mappings, monospace/escaping, the merged When/Flight cells, the Corroboration column's agreement with health_page.py, the filter bar, and the summary/detail row disclosure pairing"
  - "companion/test_view_pages.py shrunk: one EXPECTED_CHECK_COUNT = 132 line (was 169), 132/132 still pass standalone and through the shim"
  - "the view-pages ledger fragment's rows 1-37 flipped to ported with real node ids, Part 01 note added (10 B, 21 D, 4 C, 2 S; 0 deleted)"
affects: [33-06, 33-07, 33-08]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Structural rendered-HTML assertions (element/attribute counts, nesting, aria-* attributes, class-token membership) go through companion_markup.parse_html()'s Node.select()/find_all() instead of regex over the rendered string - Node.select() uses an exact-string attribute-value selector ([attr=\"v\"]), which cannot contain a space, so a class attribute holding several tokens (e.g. class=\"data-table data-table--flights\" or class=\"dot-label visually-hidden\") is matched with find_all(tag, attrs={...}) (exact dict equality, no selector tokenizer) or find_all(cls=...) (single-token membership) instead"
    - "A bare, attribute-free tag count (the legacy harness's literal \"<th>\" substring match) is reproduced as [th for th in doc.select(\"th\") if not th.attrs] rather than doc.select(\"th\") alone, so a differently-shaped header cell that legitimately carries attributes (History's day-separator <th scope=\"colgroup\" colspan=\"6\">) is not miscounted as a same-kind column header"
    - "A CSS check that used to open companion/static/style.css from disk now depends on a module-scoped served_css fixture (module_app_server_factory + served_stylesheet()) and asserts through css_rules()/declarations_for() - a rule's selector-list membership (\"[data-filter-clear]\" in sel) or its resolved declarations (decls.get(\"display\") == \"flex\"), never a raw substring/regex over the stylesheet text"
    - "A source-text completeness check with an observable consequence (history_page.py must not import html directly / must not redefine _TYPE_DISPLAY_LABELS) is rewritten as a getattr()/hasattr() identity check on the imported module object - no file is opened, and the check still fails the moment the guarded shape actually regresses"

key-files:
  created:
    - companion/test_view_pages_helpers.py
    - companion/test_view_pages_01.py
  modified:
    - companion/test_view_pages.py
    - .planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md

key-decisions:
  - "_row_block() (the private helper History's own legacy main() relocated ahead of its first use so an earlier UIR-04 check could call it) stays in companion/test_view_pages.py rather than moving to the helpers module: sections after this plan's cut (Section 1b-X5 onward, still legacy) call it dozens of times, so it is setup later checks still need, per 33-MIGRATION-RULES.md section 1. The relocation comment above it is rewritten to state why it survives now, since the checks that originally motivated the relocation are gone"
  - "companion/test_view_pages_helpers.py only carries the three helpers part 01 actually calls (seed_runway_events, history_ctx, row_block), not every module-level helper the legacy file still has (e.g. the gallery/panel-file seeding helpers Section 1c and later need) - 33-06/07/08 extend this same file as their own slices need them, per the chain's own sequential-edit convention"
  - "Tasks 1 and 2 both port into the same companion/test_view_pages_01.py module rather than splitting into _01a.py/_01b.py: part 01's 37 checks are all read-only history_page.render() calls (or pure-Python behaviour with no rendering), so xdist parallelism is unaffected by keeping them in one file, and the plan's own acceptance criteria (a single module, a single guard/shim/ledger check) read more directly against one file"

requirements-completed: [TST-10, TST-12, TST-13, TST-15]

# Metrics
duration: 55min
completed: 2026-09-24
---

# Phase 33 Plan 05: View-Pages Migration Chain Setup and Part 01 Summary

**Migrated the first 37 of `companion/test_view_pages.py`'s 169 check() calls to native pytest in `companion/test_view_pages_01.py`, replacing every regex-over-rendered-HTML and disk-read-`style.css` assertion with `companion_markup`'s parsed DOM/CSS helpers, and set up the chain's shared helpers module for 33-06 through 33-08.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-24T10:13:30Z (previous plan's completion timestamp)
- **Completed:** 2026-09-24T10:52:00Z
- **Tasks:** 3/3 completed
- **Files modified:** 4 (2 created, 2 modified)

## Accomplishments

- `companion/test_view_pages_helpers.py`: a new `__test__ = False` module holding `seed_runway_events()`, `history_ctx()` and `row_block()` (the last one now built on `companion_markup.parse_html()` rather than a hand-rolled regex) - the seeding/render plumbing the whole view-pages chain (33-05..33-08) shares, with no `Harness`/HTTP-client copy.
- `companion/test_view_pages_01.py`: 37 native pytest tests, one per original `check()` label as its docstring, porting part 01 in full - History's empty state and newest-first ordering, the reused aircraft-type/airline/route-fallback presentation mappings, monospace/escaping contracts, the six-header layout, the runway-in-title/mobile-details survival, the merged When/Flight cells and their CSS-class agreement, the Timestamp column's `<time data-relative>` element, the Corroboration column's agreement with `health_page.py`, `layout.status_dot()`'s title/`visually_hide_label` contracts, the filter bar (markers, Safari autofill suppression, the French count template, the `.filter-bar__meta` group and its CSS), the `data-filter-text` attribute pairing, and the summary/detail row `aria-controls`/`id` pairing. All 37 run with no server (in-process `history_page.render()` calls) except the 4 that fetch CSS from a `module_app_server_factory` server via `served_stylesheet()`.
- `companion/test_view_pages.py` shrunk: every historical `EXPECTED_CHECK_COUNT = ...` reassignment (and its history comments, ~625 lines) collapsed into one `EXPECTED_CHECK_COUNT = 132` line above `def main()`; the 37 migrated `check()` calls and their closures deleted (`_row_block()` itself kept - later, still-legacy sections call it). The shrunk harness still runs 132/132 standalone and through `companion/test_legacy_harness_shim.py`.
- The ledger fragment's rows 1-37 flipped to `ported` with real `companion/test_view_pages_01.py::test_*` node ids and a `### Part 01 (plan 33-05)` note (10 B, 21 D, 4 C, 2 S rubric codes; 0 deleted - every check in this slice had a direct behavioural or parsed-DOM equivalent). `33-ledger-check.py --allow-pending companion/test_view_pages.py` confirms 169/169 baseline checks accounted for (37 ported, 132 pending).
- Full-suite sanity beyond the plan's own scoped verification: `pytest -n auto companion test-support server stub-server` (`SKYPANE_REQUIRE_BROWSER=1`, real Chromium) - 947 passed, 2 failed (the exact pre-existing root-sandbox artifacts already classified in `33-BASELINE/INDEX.md`: `test_companion_app`'s `os.chmod` checks, `test_status_pages`'s `anomaly_active("/nonexistent/...")` check), 3 skipped. No regression from this plan.

## Task Commits

1. **Task 1: Helpers module and the first half of part 01** - `f235c9d` (test)
2. **Task 2: Second half of part 01** - `5a440d3` (test)
3. **Task 3: Shrink the legacy harness, fill the ledger, verify** - `93044f7` (test)

## Files Created/Modified

- `companion/test_view_pages_helpers.py` - shared seeding/render helpers for the view-pages chain
- `companion/test_view_pages_01.py` - 37 native pytest tests (part 01)
- `companion/test_view_pages.py` - shrunk to `EXPECTED_CHECK_COUNT = 132`, part-01 checks removed
- `.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md` - rows 1-37 ported, Part 01 note added

## Decisions Made

See `key-decisions` in the frontmatter above: keeping `_row_block()` in the legacy file rather than the helpers module, scoping the helpers module to only what part 01 needs, and keeping part 01 in a single `test_view_pages_01.py` rather than splitting it.

## Deviations from Plan

None - plan executed exactly as written. The plan left "Claude's discretion" for module splits and the structural-vs-substring choice per check; both were resolved using `companion_markup.parse_html()`/`css_rules()` for every check the migration rules classify as structural (element counts, nesting, attributes, CSS rule declarations), and plain substring/equality only for user-visible text and pure-Python behaviour (Corroboration agreement, `status_dot()`'s contracts).

## Issues Encountered

Two selector-syntax discoveries while porting, both fixed before the first green run and not left as workarounds: `companion_markup`'s CSS-selector tokenizer splits on whitespace, so an exact `[attr="two words"]`/`tag[class="a b"]` selector cannot be expressed as a `select()` string - `Node.find_all(tag, attrs={...})` (exact dict equality) and `Node.find_all(cls=...)` (single-token membership) are the two escape hatches used instead, and both are already part of `companion_markup.py`'s own public API (no toolkit change needed). Separately, `doc.select("th")` alone over-counted the six-header check by one: History's day-separator row also renders a `<th scope="colgroup" colspan="6">`, which the original literal `"<th>"` substring never matched (it requires the bare, attribute-free tag) - filtering to `not th.attrs` reproduces that exact distinction structurally.

## User Setup Required

None.

## Next Phase Readiness

- 33-06/07/08 (parts 02-04 of this same chain) can extend `companion/test_view_pages_helpers.py` with whatever gallery/panel-file seeding helpers their own slices need, following this plan's `__test__ = False` / no-Harness convention, and continue shrinking `companion/test_view_pages.py`'s single `EXPECTED_CHECK_COUNT` line.
- The exact-attribute-value-with-a-space workaround (`find_all(attrs={...})` / `find_all(cls=...)`) is directly reusable by any later plan hitting the same selector-tokenizer limit - no toolkit change was needed.
- No blockers. `companion/test_view_pages.py` still has 132 pending checks (Sections 1b-X5 onward) for the chain's remaining 3 plans.

---
*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 5 claimed created/modified files found on disk (`companion/test_view_pages_helpers.py`,
`companion/test_view_pages_01.py`, `companion/test_view_pages.py`,
`.planning/phases/33-companion-tests-on-pytest-behaviour-over-source-text/33-ledger/companion__test_view_pages.md`,
this summary), and all 3 commit hashes (`f235c9d`, `5a440d3`, `93044f7`) found in
`git log --oneline --all`.
