---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 03
subsystem: ui
tags: [companion, history-page, flights-page, accessibility, wcag, clipboard, copy-button]

# Dependency graph
requires:
  - phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
    provides: "wave 1 (19-01/19-02) — Health tile text-verdict idiom and companion/battery.py, unrelated to this plan's files but merged into this plan's base"
provides:
  - "History/Flights desktop table is 6 columns, not 7 — the Runway column is gone, its value survives in the row's title attribute and the mobile card's More details (A-36/D-19)"
  - "the .data-table-wrap scroller is keyboard-focusable (tabindex=\"0\") and carries a non-empty aria-label (A-36/D-19)"
  - "the desktop Timestamp cell shows a clock-only local time with no relative-age suffix, full ISO still in a title attribute (A-36/D-19)"
  - "every copy button's aria-label names its own row's callsign (or hex/no-callsign fallback), closing the '50 identical accessible names' defect (A-37/D-20)"
  - "a failed clipboard write reports nothing — fallbackCopy() propagates document.execCommand()'s real boolean instead of discarding it (A-37/D-20)"
  - "a successful copy swaps a visible 'Copied' label in beside the icon for 1.5s, announced by the existing hidden live region from one shared timer (A-37/D-20)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Icon-plus-label button content split (.copy-btn__icon / .copy-btn__label) so a transient text swap never destroys an SVG icon that textContent can't restore"
    - "Positioning a transient confirmation label via CSS absolute overflow (left: 100%) off a fixed-size control's own box, so the control's box size — and therefore any table column width depending on it — never changes for the confirmation's duration"
    - "Per-row accessible-name templates (_COPY_*_LABEL = '...%s') formatted once per row by a single shared fallback helper (_row_copy_name()), rather than a bare shared string"

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/static/copy-button.js
    - companion/static/style.css
    - companion/test_view_pages.py

key-decisions:
  - "A-36/D-19: the dropped Runway column's value is carried in the <tr title=\"...\"> attribute (desktop) rather than invented anywhere else, since the mobile card already had it in More details — no new copy is needed"
  - "A-36/D-19: the clock-only Timestamp cell is built directly from layout.parse_iso() + layout.local_clock_text() inside history_page.py, never by editing companion/layout.py (owned by plan 19-04 in the same wave) or by adding a second formatter to that shared module"
  - "A-37/D-20: the visible 'Copied' confirmation is positioned via CSS absolute overflow off .copy-btn's existing 22x22px box (position: relative already present for the ::before hit area) rather than letting the button grow, so the ::before 44x44 hit area and the table's column widths never shift"
  - "A-37/D-20: copy-button.js writes the transient label into a dedicated leaf <span class=\"copy-btn__label\"> the button contains, never into the button element itself, since the button's own visible content is an SVG icon that textContent would destroy with no way to restore it"

requirements-completed: [CFG-06]

# Metrics
duration: ~45min
completed: 2026-09-11
---

# Phase 19 Plan 03: Flights table Runway drop, scroller focus, and honest copy buttons Summary

**The Flights page's 7-column table is now 6 columns with a keyboard-focusable scroller and a clock-only Timestamp cell, and its copy buttons name their own row and only ever claim success when the clipboard write actually happened (A-36/D-19, A-37/D-20).**

## Performance

- **Duration:** ~45 min (plan/context read through last task commit)
- **Started:** 2026-09-11 (session start; exact epoch not captured before context read)
- **Completed:** 2026-09-11T07:36:09Z (Task 3 commit)
- **Tasks:** 3/3 complete
- **Files modified:** 4 (companion/pages/history_page.py, companion/static/copy-button.js, companion/static/style.css, companion/test_view_pages.py)

## Accomplishments
- Closed A-36 (D-19): the Flights table dropped from 7 to 6 columns (Runway removed — one runway is tracked at a time, so the column was the same value on every row while costing ~90px of a 1,305px table). The value survives in the desktop row's `title` attribute and, unchanged, in the mobile card's existing More details disclosure. The `.data-table-wrap` scroller is now `tabindex="0"`/`role="region"` with a named `aria-label`, so a keyboard user who could not previously reach the table at all can Tab to it and arrow-scroll. The desktop Timestamp cell dropped its relative-age suffix (the thing making the column too wide) in favour of a clock-only local time, built from `layout.parse_iso()` + `layout.local_clock_text()` without touching `companion/layout.py` (owned by a sibling plan this same wave).
- Closed A-37 (D-20), all three of its named defects: (1) every copy button's accessible name now includes its own row's callsign (falling back to hex, then a "no callsign" note), so 50 rows no longer share one aria-label; (2) `fallbackCopy()` now returns `document.execCommand()`'s real boolean instead of discarding it, and `handleClick()` only shows the "Copied" confirmation on genuine success — a failed copy reports nothing; (3) a successful copy swaps a visible "Copied" word in beside the icon for 1.5s (was invisible, `visually-hidden`-only), using the existing `--color-status-ok` token and existing label-voice values — zero new custom properties, zero new colours.
- The 44x44 synthesized hit area and the table's column widths are provably unaffected by the new visible confirmation: the label is positioned via CSS absolute overflow off the button's own unchanged 22x22px box rather than by growing the box.

## Task Commits

Each task was committed atomically:

1. **Task 1: Drop the Runway column, name and focus the scroller, shorten the Timestamp (D-19)** - `f94565a` (feat)
2. **Task 2: Name every copy button for its own row and only report real success (D-20)** - `681b181` (feat)
3. **Task 3: Make the copy confirmation visible for 1.5 s (D-20)** - `03d2620` (feat)

_No plan-metadata commit yet — SUMMARY.md and this plan's metadata commit follow this file's own creation, per worktree-mode instructions._

## Files Created/Modified
- `companion/pages/history_page.py` - `_HEADERS` dropped to 6 entries; new `SCROLLER_ARIA_LABEL` constant; new `_clock_cell_html()` (clock-only, `layout.parse_iso()` + `layout.local_clock_text()`); `_history_table_html()`'s `<tr>` gained a `title` attribute carrying the runway, and its `.data-table-wrap` wrapper gained `tabindex="0"`/`role="region"`/`aria-label`; `_COPY_CALLSIGN_LABEL`/`_COPY_HEX_LABEL`/`_COPY_TIMESTAMP_LABEL` became `%s` templates; new `_row_copy_name()` helper; `_callsign_hex_cell()` and `_history_cards_html()`'s three copy-button call sites now format the per-row label; `_copy_button_html()` wraps its icon in `.copy-btn__icon` and adds an empty `.copy-btn__label` sibling span
- `companion/static/copy-button.js` - `fallbackCopy()` now returns `document.execCommand("copy")`'s result; `handleClick()` gates `showFeedback()` on that result on both the fallback and Clipboard-API-reject paths; `FEEDBACK_RESET_MS` 2000 → 1500; new `_toggleCopiedClass()` (classList + setAttribute fallback, mirroring `battery-trend.js`'s own `_toggleActive()`); `showFeedback()` extended to swap the `.copy-btn__label` span's text and toggle `.copy-btn--copied`, guarded against double-click re-entrancy via a `data-copy-pending` attribute, restoring everything from one shared `setTimeout`; header comment reworded ("no inner-HTML assignment") to avoid an incidental match on the file's own forbidden-token grep
- `companion/static/style.css` - new `.copy-btn__label` (hidden at rest) and `.copy-btn--copied .copy-btn__label` (revealed via absolute positioning off the button's own box, using `--color-status-ok` and existing label-voice values) rules
- `companion/test_view_pages.py` - retargeted the `.data-table-wrap` exact-tag-match check and the 7-column check (now 6, `_six_columns_named_and_ordered`) in place; retargeted the raw-`_COPY_*_LABEL` aria-label check to format against a row; added 9 new checks across the three tasks (runway survives in `<tr title>`/mobile details, scroller focusable+named, desktop Timestamp has no relative-age suffix, 2 distinct copy-button aria-labels, each button names its own row, `copy-button.js` propagates `execCommand`'s result, the rendered icon/label span pair with `data-copy-feedback` intact, `copy-button.js` + `style.css` both carry the `copy-btn__label`/`copy-btn--copied`/`1500` contract); `EXPECTED_CHECK_COUNT` 67 → 76, re-derived incrementally per task (70 → 73 → 76) by running the harness after each

## Decisions Made
- The runway value's only surviving home on desktop is the row's `title` attribute — no new visible column, no tooltip icon, matching the plan's own instruction that the mobile card already carries it and nothing should be duplicated.
- The visible "Copied" confirmation is positioned via `position: absolute; left: 100%` off `.copy-btn`'s own existing `position: relative` box, rather than letting the button grow (`width: auto`) — this keeps the button's own footprint, and therefore the `::before` 44x44 hit area and the table's column widths, byte-identical before and during the confirmation.
- `_row_copy_name()` is a single shared helper (not duplicated logic) consumed by both the desktop cell and the mobile card's disclosure, matching this file's existing "a future edit to one branch is visibly obliged to touch the other" discipline already documented for `_callsign_hex_cell()`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded copy-button.js's own header comment to avoid an incidental match on its own forbidden-token grep**
- **Found during:** Task 2
- **Issue:** The plan's Task 2 acceptance criteria run `grep -c "innerHTML\|insertAdjacentHTML\|document.write\|eval(" companion/static/copy-button.js` expecting `0` — but the file's own pre-existing header comment states the standing constraint in prose ("no innerHTML, no other HTML-writing sink"), which matches that same grep purely as documentation, with no actual sink in the code.
- **Fix:** Reworded the comment to "no inner-HTML assignment, no other HTML-writing sink" — same meaning, no literal `innerHTML` substring. No functional/behavioural change.
- **Files modified:** companion/static/copy-button.js
- **Verification:** `grep -c "innerHTML\|insertAdjacentHTML\|document.write\|eval(" companion/static/copy-button.js` now outputs `0`; the same substantive check was also added as an automated harness check in `companion/test_view_pages.py` (`_copy_button_script_propagates_execcommand_success`).
- **Committed in:** `681b181` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — a documentation wording fix required to make the plan's own acceptance criteria pass without weakening the real constraint)
**Impact on plan:** No change to the plan's intent or scope; the standing no-HTML-writing-sink constraint is unchanged and now additionally enforced by an automated harness check.

## Issues Encountered

- The plan's Task 2 action text describes "five" `_copy_button_html(...)` call sites in `history_page.py` ("three in `_callsign_hex_cell()`'s branches, three in `_history_cards_html()`"), which sums to six, not five. All six real call sites (verified by `grep -n "_copy_button_html("`) were updated; the plan's own arithmetic was internally inconsistent, not the ground truth.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- History/Flights' desktop table and copy-button contract are both closed for this wave; plan 19-04 (which owns `companion/layout.py` in the same wave) can proceed independently — this plan never touched that file (`git diff --stat companion/layout.py` is empty).
- No blockers. `scripts/run-all-tests.sh` run in full: only the three documented pre-existing root-sandbox failures (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — read-only-directory/`anomaly_active()` cases that fail identically on untouched main because this sandbox runs as root) appear; zero new failures. `companion/test_view_pages.py` 76/76, `companion/test_contrast_check.py` 36/36.

## Self-Check: PASSED

All modified files verified present on disk (companion/pages/history_page.py, companion/static/copy-button.js, companion/static/style.css, companion/test_view_pages.py, this SUMMARY.md); all three task commits (f94565a, 681b181, 03d2620) verified present in git log.

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Completed: 2026-09-11*
