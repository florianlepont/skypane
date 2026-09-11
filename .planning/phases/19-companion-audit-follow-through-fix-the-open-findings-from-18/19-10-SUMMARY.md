---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 10
subsystem: ui
tags: [settings-form, dirty-state, accessibility, presets, stdlib-only]

# Dependency graph
requires:
  - phase: 19
    plan: 03
    provides: "the dirty-state.js/style.css .js-gated fallback-hide baseline this plan retargets"
  - phase: 19
    plan: 07
    provides: "config_page.py's render()/quiet_hours_group() errors/submitted signature widening this plan's preset markup lands alongside"
provides:
  - "dirty-state.js adds a dirty-ready class to <html> only once its own save bar is proven present, and style.css's fallback-hide rule keys on that class instead of nav-dropdown.js's unconditional .js class"
  - "A beforeunload guard, keyed on the existing countDifferences() predicate, warns before a real navigation discards unsaved Settings edits"
  - "Three type=\"button\" Quiet hours presets (Night, Work day, Always on) that fill quiet_hours_start/quiet_hours_end/quiet_hours_enabled client-side with no server change"
affects: [any future plan touching companion/static/dirty-state.js, companion/static/style.css's fallback-hide rule, or companion/pages/config_page.py's quiet_hours_group()]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "dirty-ready marker: a client-side-proven-present class added to <html> only after a guard clause succeeds, mirroring nav-dropdown.js's own unconditional .js class-add but scoped to a single feature's own success condition rather than 'JS ran at all'"
    - "notifyDirty() indirection: a tiny helper that calls the existing updateBar() only when the bar/countEl guard has passed, letting a second, independent feature (the presets) mark the form dirty without either reimplementing countDifferences() or dispatching a synthetic change event"
    - "Reusing an existing generic flex/wrap/gap CSS class (.runway-row) for an unrelated markup section rather than declaring a new rule, once confirmed no pinned test asserts its absence from that section specifically"

key-files:
  created: []
  modified:
    - companion/static/dirty-state.js
    - companion/static/style.css
    - companion/pages/config_page.py
    - companion/test_config_page.py

key-decisions:
  - "The dirty-ready marker is written with document.documentElement.className += \" dirty-ready\" (string concatenation), matching nav-dropdown.js's own established convention for writing a class onto <html>, rather than classList.add()"
  - "The Quiet hours preset row reuses the existing .runway-row CSS class (display:flex, flex-wrap:wrap, gap) instead of declaring a new rule - confirmed first that no pinned test in test_config_page.py asserts .runway-row's absence from quiet_hours_group()'s own output (unlike .theme-status__row, which IS pinned absent there), so this required no style.css change for Task 3 at all"
  - "The Quiet hours preset click-handling block in dirty-state.js is placed before the [data-dirty-bar]/[data-dirty-count] guard, wrapped in its own nested IIFE with its own early return on an empty NodeList, so the presets keep working even on a page whose save bar failed to initialise - this is the same page-degradation goal D-09 itself pursues"
  - "notifyDirty() reuses updateBar()/countDifferences() rather than dispatching a synthetic DOM change event, since constructing one in an ES5-safe way is unnecessary when the reacting code lives in this same file"

requirements-completed: [CFG-01]

# Metrics
duration: ~35min
completed: 2026-09-11
---

# Phase 19 Plan 10: Dirty-State No-Way-To-Save Fix, Unsaved-Edit Warning, and Quiet Hours Presets (D-09/D-10/D-14) Summary

**The Settings page's fallback Save button now hides only once its own JS replacement bar is proven working (not merely because an unrelated script set a `.js` class), leaving with unsaved edits raises the browser's own confirmation, and Quiet hours gained three one-tap presets that fill the existing fields with no server change.**

## Performance

- **Duration:** ~35 min (first task commit to last)
- **Started:** 2026-09-11 (worktree base commit `2caebef`)
- **Completed:** 2026-09-11T08:32:16Z
- **Tasks:** 3/3
- **Files modified:** 4

## Accomplishments
- `dirty-state.js` adds a `dirty-ready` class to `<html>` immediately after it confirms `[data-dirty-bar]`/`[data-dirty-count]` both exist; `style.css`'s fallback-hide rule (`... [data-static-save-fallback] { display: none; }`) is retargeted from `.js` to `.dirty-ready`, so a failure anywhere in `dirty-state.js` now degrades to the always-working bottom Save button instead of hiding it with nothing to replace it (A-27)
- A `beforeunload` guard, keyed on the pre-existing `countDifferences()` predicate (reused, never reimplemented), warns before Add rule / Delete / Trigger poll / tab-close discards unsaved Settings edits; a single `submit` listener clears it for both the in-form bottom Save button and the bar's out-of-form Save button (they submit the same form natively), and the Cancel handler clears it too (A-28)
- `quiet_hours_group()` renders three `type="button"` presets (Night, Work day, Always on) between the enable checkbox and the Start input; Night's values are sourced from `server.device_config.DEFAULT_QUIET_HOURS_START`/`DEFAULT_QUIET_HOURS_END` so the preset and the shipped default can never drift, and Always on carries `data-preset-enabled="0"` with no time attributes (unchecking the curfew while leaving the configured window intact)
- `dirty-state.js` reads each button's `data-preset-start`/`data-preset-end`/`data-preset-enabled` and writes into the same form's fields, then marks the form dirty through a new `notifyDirty()` helper — no server-side code path is new; a new `handle_post()` test proves a preset-shaped submission persists identically to a hand-typed one (T-19-38)
- Zero new CSS custom properties and zero new CSS rules across the whole plan — the preset row reuses the existing `.runway-row` class

## Task Commits

Each task was committed atomically:

1. **Task 1: Hide the fallback Save button only once the bar really initialised (D-09)** - `b13556d` (fix)
2. **Task 2: Warn before discarding unsaved settings edits (D-10)** - `cf264b5` (feat)
3. **Task 3: Add the three Quiet hours presets (D-14/S-04)** - `c3c6042` (feat)

**Plan metadata:** committed as part of this SUMMARY's own commit (worktree mode — orchestrator handles STATE.md/ROADMAP.md centrally after merge)

## Files Created/Modified
- `companion/static/dirty-state.js` — added the `dirty-ready` marker write (right after the bar guard passes), rewrote the header paragraph that used to say hiding the fallback button was not this file's job (SUPERSEDED by D-09/A-27); added a `beforeunload` listener, a module-scoped `suppressGuard` flag, a `submit` listener that sets it, and set it in the Cancel handler too (D-10/A-28); added a nested-IIFE preset block (before the bar guard) that reads `data-preset-*` attributes and writes into the form's quiet-hours fields, plus `attachPresetClickHandler()`/`notifyDirty()` helpers (D-14/S-04)
- `companion/static/style.css` — retargeted the fallback-hide rule's selector from `.js [data-static-save-fallback]` to `.dirty-ready [data-static-save-fallback]`, with a rewritten comment naming D-09/A-27; the three `.js .mobile-nav` rules are untouched; no new rule and no new custom property were added for the presets (they reuse `.runway-row`)
- `companion/pages/config_page.py` — added `QUIET_HOURS_PRESET_NIGHT_START`/`_END`/`_LABEL`, `QUIET_HOURS_PRESET_WORKDAY_START`/`_END`/`_LABEL`, `QUIET_HOURS_PRESET_ALWAYS_ON_LABEL`, and `QUIET_HOURS_PRESET_ATTR`; extended `quiet_hours_group()`'s docstring (D-14/S-04) and its return markup with a `preset_row_html` block rendered between the enable checkbox and the Start input
- `companion/test_config_page.py` — 2 checks retargeted in place (the `.js`-gated → `.dirty-ready`-gated style.css guard, the dirty-state.js literal-reference guard extended to also pin `dirty-ready`); 10 new checks added (dirty-ready-after-bar-guard source ordering, the beforeunload/submit-listener contract, three presets rendered with `type="button"`, Night preset matches `device_config` defaults, Work day preset values, Always-on preset shape, preset-row document position, the `handle_post()` preset-vs-hand-typed identical-persistence pin (T-19-38), and the dirty-state.js/config_page.py cross-file `data-preset-*` attribute agreement); `EXPECTED_CHECK_COUNT` re-derived three times, 154 → 155 → 156 → 163

## Decisions Made
See `key-decisions` in the frontmatter above for the four load-bearing decisions (the `className +=` write convention, the `.runway-row` reuse and why it was safe, the preset block's placement before the bar guard, and `notifyDirty()`'s reuse of `updateBar()` over a synthetic event).

## Deviations from Plan

None — plan executed as written. One correction was made and caught entirely by the harness before commit, not left in any committed state: an early draft of the retargeted `style.css` cross-file test checked for the literal `dirty-ready` only in the 120-character window *forward* from the attribute reference, but the selector prefix (`.dirty-ready [data-static-save-fallback]`) sits *before* that reference in the source, so the check initially false-failed; widened the window to also look 40 characters backward before commit. A similar pre-commit self-catch: the header-comment prose in `dirty-state.js` initially used backtick characters around inline code references (e.g. `` `dirty-ready` ``), which the file's own standing ES5-safety/no-backtick harness check correctly flagged as a forbidden token in the raw source — reworded the prose to avoid every banned literal before committing, echoing the identical false-positive class 19-04's own SUMMARY documented for `poll-cooldown.js`.

## Issues Encountered

None beyond the two pre-commit self-catches described above (both caught and fixed before any commit, per this plan's own fix-attempt-limit discipline — neither required more than one correction).

## User Setup Required

None — no external service configuration required.

## Self-Check: PASSED

- FOUND: companion/static/dirty-state.js
- FOUND: companion/static/style.css
- FOUND: companion/pages/config_page.py
- FOUND: companion/test_config_page.py
- FOUND commit b13556d
- FOUND commit cf264b5
- FOUND commit c3c6042

## Next Phase Readiness
- A-27/D-09 is closed: the fallback Save button hides if and only if `dirty-state.js` has proven its own replacement bar exists; a JS failure in that file no longer leaves the page with no way to save
- A-28/D-10 is closed: leaving Settings with unsaved edits (via Add rule, Delete, Trigger poll, or closing the tab) raises the browser's own confirmation; a real Save or Cancel clears it
- S-04/D-14 is closed: Quiet hours has three one-tap presets, entirely client-side, with `handle_post()` proven to treat a preset-shaped submission identically to a hand-typed one
- `companion/test_config_page.py`: 163/163; `companion/test_contrast_check.py`: 36/36; `companion/test_view_pages.py`: 76/76; `companion/test_companion_app.py`: 209/211 (2 documented pre-existing root-sandbox WR-11 failures, unrelated to this plan, unchanged); `companion/test_status_pages.py`: 189/190 (1 documented pre-existing `anomaly_active()` root-sandbox failure, unrelated to this plan, unchanged)
- `PYTHON=$(command -v python3) bash scripts/run-all-tests.sh` reports exactly the 3 pre-existing-failure harnesses (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`) an untouched checkout also reports — no new failures
- The end-of-phase `<human-check>` (tap Work day and confirm both time inputs fill and the save bar appears; tap Always on and confirm the enable checkbox unticks and the times stay; click Trigger poll with unsaved edits and confirm the browser asks before leaving; Save and confirm it does not ask; with JavaScript disabled, confirm the bottom Save settings button is visible and works) is still outstanding — deferred to end-of-phase per the plan's own verification section
- No blockers for subsequent phase-19 plans; this plan did not touch `companion/pages/airlines_page.py`, `companion/app.py`, `companion/static/freshness.js`, `companion/pages/health_page.py`, or `companion/test_view_pages.py`/`companion/test_status_pages.py`/`companion/test_companion_app.py`, which the other wave-4 plans (19-08/19-09) own

## Threat Flags

None — every new surface this plan introduces (the preset buttons' client-side writes, the `beforeunload` guard, the `dirty-ready` marker) was already named in the plan's own `<threat_model>` (T-19-38, T-19-10, T-19-39, T-19-40) and is covered by the harness checks above; no new network endpoint, auth path, file-access pattern, or schema change was added.

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 10*
*Completed: 2026-09-11*

## Self-Check: PASSED (re-verified)

- FOUND: companion/static/dirty-state.js
- FOUND: companion/static/style.css
- FOUND: companion/pages/config_page.py
- FOUND: companion/test_config_page.py
- FOUND commit b13556d (fix(19-10): hide the fallback Save button only once the bar really initialised)
- FOUND commit cf264b5 (feat(19-10): warn before discarding unsaved settings edits)
- FOUND commit c3c6042 (feat(19-10): add the three Quiet hours presets)
