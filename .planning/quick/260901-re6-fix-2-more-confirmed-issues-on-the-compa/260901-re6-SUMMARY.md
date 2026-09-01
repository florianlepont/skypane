---
phase: quick-260901-re6
plan: 260901-re6
subsystem: ui

tags: [companion, settings, css, dom-restructure]

requires:
  - phase: quick-260901-qif
    provides: ".theme-status card treatment, .runway-row wrapping layout, .led-checkbox normalization"
provides:
  - "One merged, muted caption per Settings group (Theme/Runway/Diagnostic LED), replacing the old description-above/helper-below paragraph pair"
  - "Save bar moved outside the settings <form>, fixed (not sticky) at >=960px, submitting via a form= attribute proven in a real browser"
affects: [companion-settings-page, 06.6.4.1-closing-checkpoint]

tech-stack:
  added: []
  patterns:
    - "CSS colour-only modifier class (.section-caption) composing with an existing role class (.text-label) instead of restating its font-size"
    - "Cross-DOM form submission via id + matching form= attribute, for a control that must live outside its owning <form> in the DOM"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/test_config_page.py

key-decisions:
  - "Shared caption_html computed once in theme_fieldset() and reused by both branches (single-theme read-only + multi-theme radio-group fallback), so the literal 'section-caption' string appears exactly 3 times in config_page.py (Theme, Runway, LED) rather than 4"
  - "Dirty bar restyled onto --color-dominant (the card surface) with a --color-border top hairline and an upward box-shadow (y-negated --shadow-card-hover pair) as a literal, not a new custom property, since no upward-shadow token exists and one would need 4 definition sites for a single consumer"
  - "Fixed-position bar reproduces .dashboard-main's content-column geometry (left: calc(240px + var(--space-xl)); right: 0; max-width: min(1440px, 100%); margin: 0 auto) rather than introducing a new layout primitive"

requirements-completed: [QUICK-260901-re6]

coverage:
  - id: D1
    description: "Theme/Runway/Diagnostic LED each render exactly one muted caption (validated copy verbatim) directly under the heading and above the control, replacing the old two-paragraph pattern"
    requirement: "QUICK-260901-re6"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_each_group_emits_exactly_one_caption_between_heading_and_control"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_section_captions_appear_escaped_verbatim_exactly_once"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_config_page_exposes_no_retired_helper_or_description_symbols"
        status: pass
    human_judgment: false
  - id: D2
    description: "The save bar is moved outside the <form>, positioned fixed (not sticky) at >=960px, stays pinned to the viewport bottom at any scroll depth, reads as a raised surface aligned to the content column, and its out-of-form Save button persists a merged two-field submission in one POST via a form= attribute"
    requirement: "QUICK-260901-re6"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#_render_dirty_bar_is_sibling_of_form_last_on_page"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#_style_css_carries_section_caption_and_restyled_fixed_dirty_bar"
        status: pass
      - kind: e2e
        ref: "chrome-devtools CLI live-browser smoke test against a throwaway companion/app.py process (documented below): dirtied Runway + LED, clicked the bar's Save button, confirmed device_config.json persisted both new values in one POST"
        status: pass
    human_judgment: false

duration: 35min
completed: 2026-09-01
status: complete
---

# Quick Task 260901-re6: Settings caption merge + save-bar fixed-positioning fix Summary

**Merged Settings' doubled description/helper paragraphs into one muted caption per group, and moved the save bar outside its `<form>` so `position: fixed` (not `sticky`) keeps it pinned to the viewport bottom, submitting via a cross-DOM `form=` attribute proven against a real browser session.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-01T17:35:00Z (approx.)
- **Completed:** 2026-09-01T18:09:28Z
- **Tasks:** 3
- **Files modified:** 3 (`companion/pages/config_page.py`, `companion/static/style.css`, `companion/test_config_page.py`)

## Accomplishments

- Theme, Runway, and Diagnostic LED each now render exactly one muted `.section-caption` sentence (14px, 70% text-mix opacity) directly under the group heading and above its control — the validated typography-sketch copy, verbatim. The five superseded constants (`THEME_HELPER_TEXT`, `THEME_SECTION_DESCRIPTION`, `RUNWAY_HELPER_TEXT`, `RUNWAY_SECTION_DESCRIPTION`, `LED_HELPER_TEXT`) are gone with no dead markup or stale docstrings left behind.
- The unified save bar is now the last element `render()` emits — a sibling of `<form id="settings-form">`, not a descendant — and submits via `<button type="submit" form="settings-form">`. At >=960px it is `position: fixed` (previously `sticky`, which detached from the viewport bottom on pages taller than the short 3-section form) with geometry copied from `.dashboard-shell`/`.dashboard-main` so it lines up with the content column instead of running full-bleed.
- The bar's surface moved from the muted `--color-secondary` to the dominant card surface, with a `--color-border` top hairline and an upward box-shadow (the y-negated `--shadow-card-hover` pair) — it now visibly reads as a raised action surface rather than a receding strip.
- `companion/static/dirty-state.js` required zero changes — its bar lookups were already document-wide `document.querySelector` calls, confirmed by both a source read and `git diff --stat` showing an empty diff across the whole plan.
- A real-browser smoke test (chrome-devtools CLI against a live, throwaway `companion/app.py` process) proved the cross-DOM `form=` association actually works at runtime: dirtying Runway and Diagnostic LED and clicking the bar's Save button persisted both new values in `device_config.json` in a single POST.

## Task Commits

Each task was committed atomically:

1. **Task 1: Merge each settings group's two paragraphs into one muted section caption** - `68272fd` (feat)
2. **Task 2: Move the save bar outside the form and restyle it as a fixed, page-width, raised bar** - `9cad339` (feat)
3. **Task 3: Add three guard checks, prove the moved Save button really submits in a real browser, and clear the full suite** - `f92f34f` (test)

**Plan metadata:** commit pending (orchestrator handles the docs commit)

## Files Created/Modified

- `companion/pages/config_page.py` - Retired 5 copy constants, added 3 `*_SECTION_CAPTION` constants and `SETTINGS_FORM_ID`; `theme_fieldset()` (both branches), `runway_fieldset()`, `led_group()` each emit exactly one `<p class="text-label section-caption">`; `render()` restructured so the dirty bar is emitted last, outside the form, with `form=` wiring
- `companion/static/style.css` - Added `.section-caption` (colour-only, composes with `.text-label`); restyled the base `.dirty-bar` rule (dominant surface, top hairline, upward shadow); replaced the >=960px `.dirty-bar` sticky rule with a fixed one reproducing `.dashboard-main`'s content-column geometry
- `companion/test_config_page.py` - Retargeted 5 pre-existing checks in place (Task 1: 3, Task 2: 2) with no count change; added 3 new checks in Task 3 (one-caption-per-group position assertion, retired-symbol source assertion, cross-file CSS DOM contract guard); `EXPECTED_CHECK_COUNT` moved from the real on-disk baseline (57) to 60

## Decisions Made

- Computed `theme_fieldset()`'s caption markup once (`caption_html`) and reused it across both the single-theme read-only branch and the multi-theme radio-group fallback branch, rather than duplicating the literal markup string in each — keeps the `section-caption` literal's occurrence count in the source at exactly 3 (Theme, Runway, LED), one per group, matching the plan's automated verification gate.
- Used a hand-rolled black-alpha `box-shadow` literal (the y-negated `--shadow-card-hover` pair) for the bar's upward shadow instead of introducing a new custom property, per the plan's explicit reuse-never-invent constraint — a new token would need four definition sites (`:root`, dark-mode, both `[data-ui-theme]` blocks) for a single consumer.
- Kept the `240px` sidebar-width literal duplicated (not imported) in the fixed bar's `left` offset, matching this file's existing `DIRTY_SECTION_ATTR`-style duplicated-not-imported discipline, and added a harness guard (`_style_css_carries_section_caption_and_restyled_fixed_dirty_bar`) asserting both the `.dashboard-shell` and `.dirty-bar` sites still agree.

## Deviations from Plan

None - plan executed exactly as written. All three tasks, their verify blocks, and the live-browser smoke test were completed per the plan's action/read_first instructions without needing Rule 1-4 auto-fixes.

## Live-Browser Smoke Test Evidence (Task 3 Part B)

Ran against a throwaway state directory (never the developer's own `/tmp/skypane-prod-state`), using the `chrome-devtools` CLI at a 1280x800 viewport:

1. Started `server/.venv/bin/python3 companion/app.py --port 65206 --state-dir <throwaway-tmpdir>` with `SKYPANE_COMPANION_PASSWORD` set.
2. Navigated to `/settings`, followed the `/login` redirect, authenticated.
3. Pre-interaction `device_config.json`: did not exist yet (defaults in effect: `tracked_runway="3"`, `led_enabled=True`).
4. Clicked the "Runway 06/24" card and toggled the Diagnostic LED checkbox off — two fields, two different groups, both dirty.
5. Dirty-bar copy observed: **"Runway and Diagnostic LED changed"** — the section-aware, multi-field copy `dirty-state.js` computes from the DOM order of `[data-dirty-section]` elements.
6. Screenshot at scroll-top: bar pinned to the viewport bottom, reading as a raised white surface with a visible top hairline, aligned exactly with the content column (confirmed via `getBoundingClientRect()`: bar `left=272 / right=1265`, `.dashboard-main` `left=272 / right=1265` — an exact match).
7. Screenshot at scroll-bottom: bar remained pinned to the viewport bottom, now visibly overlapping the Poll section — the direct regression evidence, since this is exactly where the old `position: sticky` bar used to detach and stop above the Poll section instead.
8. Clicked the bar's "Save settings" button: browser navigated to `/settings?flash=saved`, confirmation banner "Saved — will apply on the frame's next scheduled refresh." rendered.
9. Post-save `device_config.json` (read via `python3 -c "import json,sys; d=json.load(open(sys.argv[1])); print(d)"`):
   ```
   {'theme': 'sky', 'tracked_runway': '06-24', 'led_enabled': False}
   ```
   Both dirtied fields changed from their pre-interaction defaults (`tracked_runway`: `"3"` → `"06-24"`; `led_enabled`: `True` → `False`) — proving the single POST from the out-of-form Save button, associated via `form="settings-form"`, submitted the whole merged settings form correctly.
10. Stopped the app process (`pkill`) and deleted the throwaway state directory.

Computed styles captured via `evaluate_script`: `position: fixed`, `background-color: rgb(255, 255, 255)` (the dominant surface), `border-top: 1px rgb(223, 215, 200)`, `box-shadow: rgba(18, 21, 27, 0.08) 0px -4px 12px 0px, rgba(18, 21, 27, 0.05) 0px -2px 4px 0px` (upward, matching the plan's spec).

## Issues Encountered

None. The runway card's underlying `<input type="radio">` is intentionally `visually-hidden`, so the CLI's first click attempt on the radio element itself timed out waiting for interactivity; clicking the card's visible label text instead succeeded immediately — a tooling quirk, not a product defect (the card's entire `<label>` is the documented hit target).

## Full Suite Result

`scripts/run-all-tests.sh`: all harnesses passed except the known, pre-existing, unrelated `server/test_poll_loop.py` digest mismatch. No coverage-threshold failure (overall 91%, `companion/pages/config_page.py` itself at 100%).

## Next Phase Readiness

Both confirmed issues from 06.6.4.1's closing checkpoint are closed. The Settings page (`/settings`) now matches its validated typography/interaction target: one caption per group, and a save bar that stays genuinely pinned to the viewport bottom and reads as a raised surface at any scroll depth. No blockers for closing out 06.6.4.1's checkpoint.

---
*Phase: quick-260901-re6*
*Completed: 2026-09-01*

## Self-Check: PASSED

All modified files verified on disk (`companion/pages/config_page.py`, `companion/static/style.css`, `companion/test_config_page.py`, this SUMMARY.md) and all three task commits (`68272fd`, `9cad339`, `f92f34f`) verified in `git log --oneline --all`.
