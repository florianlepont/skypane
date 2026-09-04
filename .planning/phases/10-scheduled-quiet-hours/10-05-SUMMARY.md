---
phase: 10-scheduled-quiet-hours
plan: 05
subsystem: ui
tags: [python, html, css, forms, companion-web-app, accessibility]

# Dependency graph
requires:
  - phase: 10-scheduled-quiet-hours
    provides: "10-01's device_config.json quiet-hours registry fields (quiet_hours_enabled/quiet_hours_start/quiet_hours_end), DEFAULT_QUIET_HOURS_* constants, and save_device_config()'s strict HH:MM validation"
provides:
  - "quiet_hours_group() — the fourth Settings-page group, rendering an enable checkbox and two <input type=\"time\"> fields, wired into render() and handle_post()"
  - "The only writer of quiet_hours_enabled/quiet_hours_start/quiet_hours_end via save_device_config() — poll_loop.py (10-04) and byos_server.py (10-03) read what this page writes"
  - "A generalised .settings-checkbox CSS class (renamed from the LED-only .led-checkbox) serving two consumers"
  - "The stylesheet's first color-scheme declarations, keeping the native <input type=\"time\"> picker icon theme-consistent"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "A fourth .theme-status-wrapped sibling group, following led_group()'s exact structural template, added to the merged Settings <form> with no new <fieldset>/<legend>"
    - "Checkbox-normalization CSS is a single shared class (.settings-checkbox) serving multiple consumers rather than duplicated per-consumer rules"
    - "color-scheme declared per data-ui-theme override (and light dark on :root's default) so native form-control chrome follows the site's explicit theme attribute instead of the OS's own prefers-color-scheme"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/test_config_page.py
    - .claude/skills/sketch-findings-skypane/SKILL.md

key-decisions:
  - "An unchecked 'Enable quiet hours' checkbox still saves edited Start/End times (10-UI-SPEC.md's resolution of 10-RESEARCH.md Assumption A1) — pinned by a dedicated test, not just documented"
  - "quiet_hours_start/quiet_hours_end are passed straight through to save_device_config() unchecked by handle_post() itself, deliberately not pre-validated against device_config's private HH:MM regex — save_device_config() already validates strictly and raises before any write, which the existing except (ValueError, OSError) already maps to the generic save-failed flash"
  - ".led-checkbox renamed to .settings-checkbox in place (not duplicated under a second class name), per 10-UI-SPEC.md's recommended CSS-reuse option, now that Diagnostic LED and Quiet hours share the identical checkbox-normalization pattern"

patterns-established:
  - "Shared single-purpose CSS class renamed in place once a second identical consumer appears, rather than duplicating the rule under a new name"

requirements-completed: []

coverage:
  - id: D1
    description: "Settings renders a fourth Quiet hours group (enable checkbox + Start/End time inputs) with the locked copy, field order and vertical stacking, and no disabled attribute on the time inputs regardless of checkbox state"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#quiet_hours_group() emits the settings-checkbox label, one type=\"time\" input each for Start/End with their current values, exactly one checked flag when enabled and none when disabled, no theme-status__row, and no disabled attribute"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#quiet_hours_group()'s field order is heading, then caption, then the enable checkbox, then Start, then End, in document order"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#render() wires quiet_hours_group() with the saved current values, positioned after Diagnostic LED and before the Save settings button"
        status: pass
    human_judgment: false
  - id: D2
    description: "An unchecked enable checkbox still saves edited Start/End times; an absent checkbox always resolves to False; a malformed HH:MM or crafted checkbox value returns the generic save-failed flash and persists nothing, all-or-nothing across every field"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#handle_post with quiet_hours_enabled absent but both times submitted persists quiet_hours_enabled False and the edited times (a user can pre-configure a window before enabling it)"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#handle_post({\"quiet_hours_start\": \"24:00\"}, ctx) against a legitimately-saved config returns the save-failed flash key and leaves device_config.json byte-identical"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#handle_post({\"quiet_hours_enabled\": \"yes\"}, ctx) returns the save-failed flash key, matching the LED field's own third shape"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#a post with a valid theme AND a malformed quiet_hours_end returns save-failed and persists neither — the theme on disk is unchanged (all-or-nothing across groups)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every interpolated current value is escaped, and the checkbox-normalization CSS class is shared (not duplicated) between Diagnostic LED and Quiet hours with no stale led-checkbox name left anywhere"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#quiet_hours_group() escapes a crafted current_start value — no raw <script> substring reaches the markup"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#style.css declares .theme-status (card-surface token + hover selector), .runway-row (flex display), and .settings-checkbox input[type=\"checkbox\"] (cleared min-height)"
        status: pass
    human_judgment: false
  - id: D4
    description: "The native time-picker indicator follows the site's explicit data-ui-theme override rather than the OS colour scheme — a real-browser claim only a human can settle"
    verification: []
    human_judgment: true
    rationale: "10-05-PLAN.md's own Task 3 human-check explicitly scopes this to a real browser (narrow-viewport wrapping, the OS-vs-site-theme-disagreement picker-icon check, and general visual polish) and this project's human_verify_mode is end-of-phase (config.json), so this deliverable is deferred to the phase-level UAT pass rather than verified inline here."

duration: 55min
completed: 2026-09-03
status: complete
---

# Phase 10 Plan 05: Quiet Hours Settings Fieldset Summary

**A fourth "Quiet hours" group on the companion Settings page (enable checkbox + Start/End `<input type="time">` fields), saved through the existing single `save_device_config()` call, plus a generalised `.settings-checkbox` CSS class and the stylesheet's first `color-scheme` declarations.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-03T20:30Z (approx.)
- **Completed:** 2026-09-03T21:25Z (approx.)
- **Tasks:** 3
- **Files modified:** 4

## Accomplishments
- `quiet_hours_group()` renders the locked field order (heading, caption, enable checkbox, Start, End) with no `<fieldset>`/`<legend>`, matching `led_group()`'s structure; every interpolated current value is escaped
- `render()` emits it as the fourth merged-form group, after Diagnostic LED and before the always-visible Save settings button
- `handle_post()` resolves the enable checkbox's three shapes (absent → False, `"on"` → True, anything else → reject) and passes both times straight through to the single `save_device_config()` call, all-or-nothing across all six settings fields
- `.led-checkbox` renamed to `.settings-checkbox` in `style.css` and `config_page.py`, in place — no stale selector or comment reference left behind — now serving both the Diagnostic LED and Quiet hours groups
- Three `color-scheme` declarations added to `style.css` for the first time (`light`/`dark` on the two `html[data-ui-theme]` blocks, `light dark` on `:root`'s default case), keeping the native time-picker indicator theme-consistent
- `companion/test_config_page.py` grew from 64 to 73 checks; three pre-existing checks were retargeted in place for the new group's presence and the class rename, with no coverage weakened
- `sketch-findings-skypane` SKILL.md's touch-target register and Folded-In Work log updated with both the rename and the new `color-scheme`/`type="time"` facts

## Task Commits

Each task was committed atomically:

1. **Task 1: Add quiet_hours_group() and wire it through render() and handle_post()** - `80c1ff7` (feat)
2. **Task 2: Generalise the checkbox class and add the color-scheme declarations** - `2b9367f` (refactor)
3. **Task 3: Cover the fieldset and the save path in test_config_page.py** - `2c88cbf` (test)

## Files Created/Modified
- `companion/pages/config_page.py` - `QUIET_HOURS_CHECKBOX_VALUE`/`QUIET_HOURS_SECTION_HEADING`/`QUIET_HOURS_SECTION_CAPTION` constants, `quiet_hours_group()`, `render()`/`handle_post()` extensions, `.settings-checkbox` rename
- `companion/static/style.css` - `.led-checkbox` → `.settings-checkbox` rename (in place), three new `color-scheme` declarations
- `companion/test_config_page.py` - 9 new checks (4 markup/field-order/escaping/render-wiring, 5 handle_post save/reject/all-or-nothing), 3 pre-existing checks retargeted, `EXPECTED_CHECK_COUNT` 64 → 73
- `.claude/skills/sketch-findings-skypane/SKILL.md` - touch-target register entry renamed and reworded; Folded-In Work log entry added recording the rename and the two new facts

## Decisions Made
- Kept `handle_post()`'s time-field validation entirely inside `save_device_config()` rather than duplicating a shape check against `device_config`'s private HH:MM regex — the existing `except (ValueError, OSError): return FLASH_SAVE_FAILED` already covers it, and duplicating the check would be a second place the same rule could drift.
- Renamed `.led-checkbox` to `.settings-checkbox` (10-UI-SPEC.md's recommended option) rather than duplicating the rule under a `.quiet-hours-checkbox` fallback class, since the two consumers' needs are identical.
- Fixed two pre-existing test assertions that were a direct, mechanical consequence of Task 1's wiring (the theme-status group count 2→3, and the dirty-section count 3→4) as part of Task 3, per that task's own read_first pointer flagging the surrounding check region — not deferred or left broken between commits.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Reworded two docstring/comment passages that would have failed their own literal acceptance-criteria greps**
- **Found during:** Task 1 and Task 2
- **Issue:** The plan's own suggested docstring wording for `handle_post()` (explaining why `quiet_hours_start`/`quiet_hours_end` aren't pre-validated against `device_config`'s private regex) and for `quiet_hours_group()`'s docstring (describing the `.led-checkbox` → `.settings-checkbox` rename) each contained the literal substrings the same tasks' acceptance criteria required to be *absent* (`grep -n 'device_config\._HHMM_RE'` returns no match in Task 1; `grep -rn 'led-checkbox'` returns no match in Task 2, which also applies to `.claude/skills/sketch-findings-skypane/SKILL.md`'s new prose).
- **Fix:** Reworded all four passages (two in `config_page.py`, two in `SKILL.md`) to describe the same facts without using the literal forbidden strings (e.g. "the HH:MM shape-gate regex `device_config` keeps as a private module-level name" instead of naming it, "a rename of this group's own original checkbox-normalization class" instead of naming the old class).
- **Files modified:** `companion/pages/config_page.py`, `.claude/skills/sketch-findings-skypane/SKILL.md`
- **Verification:** All four `grep` acceptance criteria pass with no match.
- **Committed in:** `80c1ff7`, `2b9367f`

**2. [Rule 1 - Bug] Fixed a test fixture using a theme id retired by the Phase 8 registry merge**
- **Found during:** Task 3 (writing the new all-or-nothing check)
- **Issue:** The first draft of the new all-or-nothing check wrote `theme="sky"` directly to a fixture's on-disk `device_config.json` via `_write_device_config()`. `"sky"` is no longer a member of `device_config.THEME_IDS` post-Phase-8 (the registry now holds 19 real entries, "sky" retired) — `load_device_config()`'s read-path normaliser silently degrades an unrecognised on-disk theme to the default (`"white"`), so the check's own assertion that the pre-existing theme stayed unchanged failed against reality, not against a bug in `handle_post()`.
- **Fix:** Switched the fixture to `"black"` (a real, current `THEME_IDS` member also used by several neighbouring checks in the same file) and the submitted-but-rejected theme to `"white"`.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `server/.venv/bin/python3 companion/test_config_page.py` exits 0 at 73/73.
- **Committed in:** `2c88cbf`

---

**Total deviations:** 2 auto-fixed (both Rule 1 — bugs directly caused by, or surfaced while implementing, this plan's own tasks). No scope creep: every fix stayed within the file already declared for its task, except the intentional, task-3-scoped `config_page.py`/`SKILL.md` doc-string rewordings, which were required to satisfy those same tasks' own literal acceptance-criteria greps.

## Issues Encountered
- Wiring `quiet_hours_group()` into `render()` in Task 1 necessarily changed the count of `class="theme-status"`-wrapped groups from 2 to 3, and the count of `data-dirty-section` elements from 3 to 4 — breaking two pre-existing `test_config_page.py` assertions that Task 1's own file scope (`config_page.py` only) could not fix. This was expected and by design: Task 3's own read_first section explicitly flags the surrounding check region for retargeting, and Task 1/Task 2's acceptance criteria (which call for `test_config_page.py` to exit 0) could only be fully satisfied once Task 3 landed in the same plan. Verified the transient state at each commit boundary (62/64 after Task 1, 59/64 after Task 2 — all failures being exactly the checks Task 3 was scoped to fix) before confirming the final green state (73/73) after Task 3.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 10's full plan set (10-01 through 10-05) is now complete: the registry (10-01), the panel's quiet-hours canvas (10-02), the vendored device-side sleep extension (10-03), the poll-loop gate (10-04), and this Settings fieldset (10-05) form a closed loop — a user can now set and persist the window through the only writer of these fields, and every downstream reader (poll_loop.py, byos_server.py, render.py) already consumes the same six-key `load_device_config()` contract.
- `scripts/run-all-tests.sh` run at the end of this plan: 16/16 harnesses pass, `companion/pages/config_page.py` at 100% statement coverage, overall project coverage 92%.
- The real-browser human-check items from Task 3's `<verify>` block (narrow-viewport wrapping at 320/375px, visual match against the page's other fields, the OS-vs-site-theme-disagreement picker-icon check, and the full save/reload/toggle round trip) are deferred to this project's phase-level UAT pass (`human_verify_mode: end-of-phase` in `.planning/config.json`) rather than performed inline in this plan — see coverage item D4 above.

## Self-Check: PASSED

Verified directly:
- `companion/pages/config_page.py`, `companion/static/style.css`, `companion/test_config_page.py`, `.claude/skills/sketch-findings-skypane/SKILL.md`, and this SUMMARY.md all FOUND on disk.
- Commits `80c1ff7`, `2b9367f`, `2c88cbf` all FOUND in `git log --oneline --all`.
- `companion/test_config_page.py` exits 0 at 73/73; `scripts/run-all-tests.sh` reports overall PASS across all 16 harnesses with `companion/pages/config_page.py` at 100% statement coverage.

---
*Phase: 10-scheduled-quiet-hours*
*Completed: 2026-09-03*
