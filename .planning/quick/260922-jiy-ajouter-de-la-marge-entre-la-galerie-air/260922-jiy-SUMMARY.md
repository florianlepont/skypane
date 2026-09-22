---
phase: quick-260922-jiy
plan: 01
subsystem: ui
tags: [css, spacing, design-system]

requires: []
provides:
  - "A visible 24px (--space-lg) gap between the Compagnies airline gallery grid and the 'Compagnies non identifiees' gap-strip card below it, via an adjacent-sibling rule that cannot reach the gap-strip's own inner grid"
  - "A visible 16px (--space-md) gap between the Heures calmes preset-row segmented control and the Debut/Fin time fields below it, matching the existing .quiet-dial__readout precedent one component above"
affects: []

tech-stack:
  added: []
  patterns:
    - "Sibling-card gaps in companion/static/style.css are declared as margin-top on the following element via an adjacent-sibling selector when the preceding element's own class is shared by an unrelated consumer, rather than as margin-bottom on the shared class"

key-files:
  created: []
  modified:
    - companion/static/style.css

key-decisions:
  - "Task 1's gap is a margin-top on .illustration-grid + .page-section rather than a margin-bottom on .illustration-grid, because .illustration-grid is also worn by the gap-strip's own inner grid (illustration-grid--gap) and a bottom margin there would have separated the strip's own cards from its caption below them"
  - "Task 2's gap reuses the margin-bottom longhand (not the margin shorthand) on .quiet-preset-row so no horizontal margin is silently zeroed on the segmented container"

requirements-completed:
  - QUICK-260922-jiy

coverage:
  - id: D1
    description: "Compagnies gallery grid is visibly separated from the gap-strip card below it by --space-lg, with no margin leaking onto the shared .illustration-grid class or the bare illustration-grid--gap modifier"
    requirement: QUICK-260922-jiy
    verification:
      - kind: unit
        ref: "inline stylesheet gate (Task 1 verify block) — comment-stripped regex assertions on .illustration-grid + .page-section, .illustration-grid, .illustration-grid--gap"
        status: pass
      - kind: unit
        ref: "companion/test_companion_app.py, companion/test_status_pages.py, companion/test_view_pages.py — 317/317, 316/316, 169/169, unchanged from baseline"
        status: pass
      - kind: automated_ui
        ref: "companion/test_browser_ux.py::_airlines_grid_renders_two_cards_per_row_at_390px — self-skips in this worktree (no playwright); cleared by code inspection instead, since it groups cards by rounded top WITHIN each grid and cannot be affected by a following-sibling margin"
        status: unknown
    human_judgment: true
    rationale: "The plan's own human-check step asks for a real-viewport visual confirmation that the gap reads correctly at phone width and that the gap-strip's internal card rhythm is unchanged; the one browser harness check that names these selectors self-skips (no playwright installed) so its pass/fail state could not be captured from a live run, only reasoned about from source."
  - id: D2
    description: "Heures calmes preset row is visibly separated from the Debut/Fin fields by --space-md, with the three preset segments still flush and their hairline dividers untouched"
    requirement: QUICK-260922-jiy
    verification:
      - kind: unit
        ref: "inline stylesheet gate (Task 2 verify block) — comment-stripped regex assertions on .quiet-preset-row, .quiet-preset-row button:not(:first-child), .quiet-times-row"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py, companion/test_companion_app.py — 274/274, 317/317, unchanged from baseline"
        status: pass
    human_judgment: true
    rationale: "The plan's own human-check step asks for a real-viewport visual confirmation that the gap matches the dial-readout precedent above it and that the three preset buttons still read as one flush control."

duration: 20min
completed: 2026-09-22
status: complete
---

# Quick Task 260922-jiy: Margin fixes for Compagnies gallery and Heures calmes preset row Summary

**Two CSS-only spacing fixes in `companion/static/style.css`: a 24px adjacent-sibling gap between the Compagnies airline gallery and the gap-strip card below it, and a 16px bottom margin on the Heures calmes preset-row segmented control, both spending existing `--space-lg`/`--space-md` tokens with zero new CSS surface.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-22T00:00:00Z (approx, not separately timestamped)
- **Completed:** 2026-09-22
- **Tasks:** 2/2
- **Files modified:** 1

## Accomplishments
- Closed the flush-gap between the Compagnies gallery grid and the "Compagnies non identifiees" card, using an adjacent-sibling selector (`.illustration-grid + .page-section`) that structurally cannot reach the gap-strip's own inner grid (which is always followed by a `<p>`, never a `.page-section`)
- Closed the flush-gap between the Heures calmes preset row and the Debut/Fin fields, by adding one `margin-bottom` declaration to the existing `.quiet-preset-row` rule, matching the `.quiet-dial__readout` precedent one component above it
- Verified both stylesheet gates were genuinely non-vacuous: each failed against the pre-edit file and passed only after its respective edit landed

## Task Commits

Each task was committed atomically:

1. **Task 1: Separate the Compagnies gallery from the unresolved-callsign card below it** - `7643c1e` (feat)
2. **Task 2: Separate the Heures calmes preset row from the Debut/Fin fields** - `30a342c` (feat)

**Plan metadata:** committed separately by the orchestrator (docs commit not made by this executor per constraints)

## Files Created/Modified
- `companion/static/style.css` - Added `.illustration-grid + .page-section { margin-top: var(--space-lg) }` after the `.illustration-grid` media-query block; added `margin-bottom: var(--space-md)` to the existing `.quiet-preset-row` rule

## Decisions Made
- Both gaps reuse existing spacing tokens (`--space-lg`, `--space-md`) per the design-system contract; no eighth spacing token, no bare pixel literal, no new CSS class was introduced
- Task 1 used the adjacent-sibling form rather than a bottom margin on the reused `.illustration-grid` class, to avoid affecting the gap-strip's own inner grid
- Task 2 used the `margin-bottom` longhand rather than the `margin` shorthand to avoid silently zeroing any horizontal margin the segmented container might later need

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Both automated stylesheet gates were confirmed non-vacuous (failing pre-edit, passing post-edit) before proceeding, per the plan's verification instructions. All four non-browser harnesses matched their documented pre-change baselines exactly (companion-app 317/317, config-page 274/274, status-pages 316/316, view-pages 169/169). `test_browser_ux.py` self-skipped (no playwright in this worktree) as expected; its two relevant checks were cleared by direct code inspection per the plan's verification section 4 rather than recorded as a pass: `_airlines_grid_renders_two_cards_per_row_at_390px()` groups cards by rounded `top` WITHIN each grid (unaffected by a following-sibling margin), and no `_css_rule_body()` call in that file targets `.illustration-grid`, `.page-section`, or `.quiet-preset-row`. `git diff --stat` against the plan's starting commit confirms exactly one file changed: `companion/static/style.css`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Both reported spacing gaps are closed. The out-of-scope item recorded in the plan (extending `style.css`'s header-comment accent-reservation list by Phase 23's two genuine accent consumers) remains open for the next plan that touches accent colour in this file — not addressed here since this batch was spacing-only.

---
*Phase: quick-260922-jiy*
*Completed: 2026-09-22*

## Self-Check: PASSED

- FOUND: companion/static/style.css
- FOUND: .planning/quick/260922-jiy-ajouter-de-la-marge-entre-la-galerie-air/260922-jiy-SUMMARY.md
- FOUND commit: 7643c1e
- FOUND commit: 30a342c
