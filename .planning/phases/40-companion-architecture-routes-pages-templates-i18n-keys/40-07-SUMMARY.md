---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 07
subsystem: ui
tags: [python, playwright, pytest, html, accessibility, keyboard-navigation]

# Dependency graph
requires:
  - phase: 40-01
    provides: the CMP-06 80-code-line function guard (test-support/companion_structure.py) and the render-baseline byte-equality harness this plan's Task 1 is measured against
provides:
  - history_page._history_cards_html and airlines_page._airline_card_html both split under CMP-06's 80-code-line guard, output byte-identical
  - CFG-52's sixth (and last) requirement clause measured for the artwork drop zone: keyboard-only operation with zero pointer events
affects: [40-companion-architecture-routes-pages-templates-i18n-keys, requirements-cfg-52]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Card/attribute builders split into small pure sub-builders returning plain tuples (no dataclasses introduced), matching this file's existing procedural style"
    - "Keyboard-only browser test recipe for a native <input type=\"file\">: Tab-only focus loop (bounded, names the last focused element on failure) + page.expect_file_chooser() + a measured key (not assumed) + Tab-only focus to the submit button + Enter to submit, with the pointer recorder armed before the first key press"

key-files:
  created: []
  modified:
    - companion/pages/history_page.py
    - companion/pages/airlines_page.py
    - companion/test_browser_ux_04.py

key-decisions:
  - "CFG-52's platform-file-chooser key is \"Space\", not \"Enter\": measured against this repo's real Chromium (--only-shell-installed) over 8 full pytest runs, Enter opened the chooser only 3/8 times while Space opened it 12/12 across the same measurement. No production code changed - the native file input was already reachable and operable; only the harness needed the correct key."

requirements-completed: [CMP-06, CFG-52]

# Metrics
duration: ~50min (not captured precisely at session start; approximate)
completed: 2026-09-27
---

# Phase 40 Plan 07: Split oversized card builders + measure CFG-52's keyboard clause Summary

**Split `_history_cards_html` (95→~20 lines) and `_airline_card_html` (114→~48 lines) into byte-identical sub-builders, then measured — and closed — CFG-52's last unmeasured clause: the artwork drop zone's native file input is keyboard-operable with zero pointer events, using Space (not Enter) to open the platform file chooser.**

## Performance

- **Duration:** ~50 min (approximate; start time not captured at session start)
- **Completed:** 2026-09-27T14:10:10Z
- **Tasks:** 2/2
- **Files modified:** 3

## Accomplishments

- `history_page._history_cards_html` (95 code lines) split into `_history_card_primary_html`, `_history_card_secondary_html`, `_history_card_airline_line_html`, `_history_card_details_html`, plus a ~20-line assembly loop — output byte-identical (`test_render_baseline.py`, `test_view_pages_01..04.py` all pass unchanged).
- `airlines_page._airline_card_html` (114 code lines) split into `_airline_card_manual_fields` (manual-resolution-derived values) and `_airline_card_zoom_html` (the click-to-enlarge trigger markup), leaving a ~48-line assembly function — output byte-identical.
- `test-support/companion_structure.py`'s `long_functions()` now returns `[]` for both files.
- New browser test `test_the_artwork_drop_zone_is_operable_from_the_keyboard_alone[light|dark]` in `companion/test_browser_ux_04.py`: Tab alone (never `.click()`/`.focus()`) reaches the drop zone's native `<input type="file">`, a key press inside `page.expect_file_chooser()` opens the platform picker, the chosen file is submitted by pressing Enter on the Tab-focused submit button, zero pointer events fire throughout, and the stored file (read back through `illustrations.override_path_for_key()`, the same loader `test_dropped_and_picked_files_are_stored_identically()` uses) decodes to the source fixture's own 1200x300.
- No production fix was needed: the native file input was already reachable and operable by keyboard. `companion/static/panel-lookup.js` was read (per the plan's contingency) but not modified.

## Task Commits

Each task was committed atomically:

1. **Task 1: Split `_history_cards_html` and `_airline_card_html`** - `fb76be1` (refactor)
2. **Task 2: Measure (and if needed fix) keyboard-only operation of the artwork drop zone** - `20d3489` (test)

**Plan metadata:** (this commit)

## Files Created/Modified

- `companion/pages/history_page.py` - `_history_cards_html` split into four sub-builders (primary/secondary/airline-line/details lines), each under 80 code lines
- `companion/pages/airlines_page.py` - `_airline_card_html` split into `_airline_card_manual_fields` (manual-info-derived values) and `_airline_card_zoom_html` (trigger markup), each under 80 code lines
- `companion/test_browser_ux_04.py` - new `test_the_artwork_drop_zone_is_operable_from_the_keyboard_alone` (parametrized light/dark), plus a small `_tab_until_focused()` helper and `_POINTER_RECORDER_ARM`/`_POINTER_RECORDER_READ` added to the module's helper import list

## Decisions Made

- **CFG-52's platform-chooser key is Space, not Enter** (see `key-decisions` above and the test's own docstring for the measured 3/8 vs 12/12 counts). This is the one deviation from the plan's suggested recipe text (which named Enter first) — explicitly anticipated and pre-authorized by the plan's own `<behavior>` clause ("fall back to Space only if Enter is measured not to open the chooser, and record which key in the test's docstring").
- Split boundaries in both page builders follow existing cohesive sub-concepts already named in the original code's own comments (primary/secondary/airline lines; manual-info derivation vs. the zoom trigger's markup) rather than an arbitrary line-count cut, so each new function has a single clear responsibility.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed forbidden requirement-ID references from new test comments/docstrings**
- **Found during:** Task 2, after writing the new test and its module-level comment
- **Issue:** `scripts/check_comment_history.py check` (part of this plan's own `<verification>` block) failed with two `prefix-id: CFG-52` violations — CLAUDE.md forbids plan/ticket/requirement IDs in comments, and the initial docstring/comment text cited "CFG-52" and "REQUIREMENTS.md's D19 row" directly.
- **Fix:** Reworded the module-level comment and the test's docstring to describe the recipe and the measurement in plain language, with no requirement ID anywhere in the file.
- **Files modified:** `companion/test_browser_ux_04.py`
- **Verification:** `server/.venv/bin/python3 scripts/check_comment_history.py check` exits 0.
- **Committed in:** `20d3489` (Task 2 commit; caught and fixed before that commit was made)

---

**Total deviations:** 1 auto-fixed (1 bug — comment-history guard violation, caught before commit)
**Impact on plan:** No scope creep; the fix only touched comment/docstring wording, not test behavior.

## Issues Encountered

- The keyboard-chooser recipe was genuinely flaky with "Enter" as the trigger key (measured 3/8 full-suite passes, always failing on the *second* parametrized run in the same pytest process — a Chromium/CDP file-chooser-interception quirk in this repo's headless-shell build, not a focus or code defect: DOM inspection during failures confirmed the correct `<input type="file">` element was genuinely focused each time). Switching the trigger key to "Space" resolved it completely (12/12 across the same measurement protocol, plus 10/10 on a further confirmation pass). This is recorded as the key-decision above and in the test's own docstring, per the plan's explicit fallback clause.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CMP-06 (function-size guard) and CFG-52 (keyboard-operability regression floor) both hold for every control the phase has touched so far; `long_functions()` returns `[]` across `companion/pages/history_page.py` and `companion/pages/airlines_page.py`.
- CFG-52 can now be ticked in `.planning/REQUIREMENTS.md` — the per-clause evidence for the artwork drop zone (its sixth, previously-unmeasured clause) is: **saving with scripts blocked** — `test_artwork_uploads_and_is_served_with_scripts_blocked`; **keyboard, zero pointer events** — `test_the_artwork_drop_zone_is_operable_from_the_keyboard_alone[light|dark]` (this plan); **360px touch floor** — `test_the_artwork_drop_zone_meets_its_floors_at_360px_in_both_themes`; **both themes** — same test; **motion budget** — unchanged CSS, no new `@keyframes`/reduced-motion blocks (`git diff` for this plan touches no `.css` file); **design system updated in step** — no visible styling changed, so no design-skill note was needed (the plan's own contingency, "if the fix changes any visible styling," did not trigger, since no fix was needed).
- No blockers for the remaining 40-* plans.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: companion/pages/history_page.py
- FOUND: companion/pages/airlines_page.py
- FOUND: companion/test_browser_ux_04.py
- FOUND: .planning/phases/40-companion-architecture-routes-pages-templates-i18n-keys/40-07-SUMMARY.md
- FOUND commit: fb76be1
- FOUND commit: 20d3489
