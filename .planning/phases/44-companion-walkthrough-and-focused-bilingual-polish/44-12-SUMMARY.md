---
phase: 44-companion-walkthrough-and-focused-bilingual-polish
plan: 12
status: complete (owner validation 2026-10-04)
requirements: [CMP-01, CMP-02, CMP-03, CMP-04]
completed: 2026-10-03
---

# Phase 44 Plan 12: Closing Evidence and Owner Verification Summary

Automated evidence for the whole phase is complete and green. The blocking owner visual verification (Task 2) was resolved on 2026-10-04 by the owner's own statement that they had validated the deployed companion; see `44-VALIDATION.md` for what that does and does not evidence.

## Tasks

1. Regression matrix rerun: focused browser aggregate 338 passed; full `./scripts/run-all-tests.sh` 3481 passed, 8 environment-only skips, coverage 95.12%; ruff, mypy, comment-history and function-size gates green.
2. Owner checkpoint: **validated by the owner, 2026-10-04** (statement only; the original checklist predates later redesigns and no per-item evidence exists). The open decisions below remain open.
3. Dispositions: `44-WALKTHROUGH.md` rewritten with a disposition and owning plan for W-01..W-05 and every owner-feedback item; `44-VALIDATION.md` filled with real results.

## Cleanup

- Deleted 41 retired-contract skipped tests (19 in `test_config_page_04b.py`, 9 in `test_browser_ux_03.py`, 7 in `test_view_pages_04.py`, 3 each in `test_browser_ux_01.py` and `test_view_pages_03.py`) plus helpers only they used.
- Removed dead Home code (`_status_tiles_html`, `_hero_html`, their text constants, `_plain_text_from_markup`) and the orphaned French catalogue entries.
- Left the Frame strip, `quick-switch.js` and `/quick/display` untouched: open decision.

## Deviations from Plan

- The plan said 17 skips; the real count of retired skips was 41, all removed.
- Orphan French ids from the removed Home constants tripped the i18n parity test; the entries were removed with them.

## Open decisions

Navigation labels, Airlines metadata editor, shared freshness indicator, update-cadence explanation, and the unrendered Frame strip / quick-switch / `/quick/display` (see `44-WALKTHROUGH.md`).

## Self-Check: PASSED
