---
phase: 12-remote-display-on-off-toggle
plan: 05
subsystem: ui
tags: [companion-web, settings-page, python-stdlib, server-rendered-html, form-validation]

# Dependency graph
requires:
  - phase: 12-01
    provides: "server/device_config.py's display_enabled registry — DEFAULT_DISPLAY_ENABLED, normalise_display_enabled(), and save_device_config()'s eighth display_enabled keyword"
provides:
  - "The Display Settings group (companion/pages/config_page.py's display_group()), the sixth and last .theme-status group on the companion Settings page"
  - "handle_post()'s eighth save_device_config() keyword, resolved through the same absent-means-False checkbox ladder led_enabled/quiet_hours_enabled already use"
  - "The single writer of display_enabled — server/poll_loop.py (12-04) and stub-server/byos_server.py (12-03) only read the saved key by JSON name"
affects: [12-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "display_group() mirrors led_group()'s exact markup shape (lone checkbox, no <fieldset>/<legend>) rather than quiet_hours_group()'s (which has dependent fields this group deliberately does not gain)"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/test_config_page.py

key-decisions:
  - "Modeled display_group() on led_group() rather than quiet_hours_group() — a lone checkbox with no dependent fields is led_group()'s shape, not quiet_hours_group()'s two-time-input shape"
  - "DISPLAY_SECTION_CAPTION states its own ~5-minute apply latency (D-02) instead of reusing every other caption's generic next-scheduled-poll clause, because D-01 pins the off-state check-in to a fixed 300s cadence independent of wake_interval_s/quiet hours"
  - "Retargeted the three fail-closed group-shape assertions in test_config_page.py (theme-status count, dirty-section order, DIRTY_SECTION_ATTR count) from five to six rather than relaxing them to inequalities"
  - "Left companion/test_companion_app.py untouched — it exercises the rendered page over real HTTP, not whole-page dict comparison, and passed at 148/148 with zero change needed"

requirements-completed: []

coverage:
  - id: D1
    description: "The Settings page renders a sixth Display group, last in the locked order, holding exactly one checkbox pre-filled from the saved config"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#render() emits Theme's .theme-chip-grid (no <fieldset>, D-01), six theme-status-wrapped groups (Theme/Runway/Diagnostic LED/Quiet hours/Wake interval/Display), three runway-card labels, and a Save settings submit button"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#display_group(True)/display_group(False) emit exactly one .theme-status[data-dirty-section] wrapper..."
        status: pass
    human_judgment: false
  - id: D2
    description: "An absent display_enabled field resolves to False on save; the exact checkbox constant resolves to True; a crafted value rejects the whole submission and leaves the file byte-identical"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#handle_post() resolves display_enabled through all three checkbox shapes: absent persists False, DISPLAY_CHECKBOX_VALUE persists True, and a crafted value returns the save-failed flash key and leaves a pre-existing device_config.json byte-identical"
        status: pass
    human_judgment: false
  - id: D3
    description: "An absent display_enabled on disk resolves to True when the page renders (D-09), so an installation already in service shows the box checked"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#render() with an empty device_config renders the Display checkbox checked (D-09), and with display_enabled explicitly False renders it unchecked"
        status: pass
    human_judgment: false
  - id: D4
    description: "The caption states the ~5-minute apply latency in both directions and never claims immediacy (D-02)"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#DISPLAY_SECTION_CAPTION equals 12-UI-SPEC.md's locked sentence exactly..."
        status: pass
    human_judgment: false
  - id: D5
    description: "Zero new CSS selectors, declarations, or design tokens — the group reuses .theme-status and .settings-checkbox verbatim"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#style.css already declares .theme-status and .settings-checkbox - the Display group introduces zero new CSS selectors"
        status: pass
      - kind: other
        ref: "git diff --quiet companion/static/style.css .claude/skills/sketch-findings-skypane/"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-09-05
status: complete
---

# Phase 12 Plan 05: Companion Settings Display Group Summary

**Added the sixth and last Settings group (a single "Enable display" checkbox mirroring led_group()'s markup shape), wired through the same merged form and single save_device_config() call every other setting already uses, defaulting to on with a caption that honestly states the ~5-minute apply latency.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-05T17:50:00Z (approx.)
- **Completed:** 2026-09-05T18:04:11Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `display_group()` in `companion/pages/config_page.py`: one `.theme-status` wrapper, one `.settings-checkbox` label, one checkbox input named `display_enabled`, no `<fieldset>`/`<legend>`, no new class — structurally identical to `led_group()`
- `render()` prefills from `device_cfg.get("display_enabled", device_config.DEFAULT_DISPLAY_ENABLED)` so a config predating this field renders checked (D-09), and places the group sixth and last: Theme → Runway → Diagnostic LED → Quiet hours → Wake interval → Display
- `handle_post()` resolves `display_enabled` through the identical three-shape ladder `led_enabled`/`quiet_hours_enabled` already use (absent → `False`, exact `DISPLAY_CHECKBOX_VALUE` → `True`, anything else → reject the whole submission) and passes it as an eighth keyword into the single existing `save_device_config()` call
- Retargeted the three fail-closed page-shape assertions in `companion/test_config_page.py` (the `.theme-status` count, the dirty-section ordered list, and the `DIRTY_SECTION_ATTR` occurrence count) from five to six, none relaxed into an inequality
- Added five new checks covering `display_group()`'s markup shape, the locked caption's exact copy, `render()`'s D-09 prefill in both directions, `handle_post()`'s three-shape resolution with byte-identity on rejection, and a cross-file guard proving `style.css` needs no new selector
- `companion/test_companion_app.py` passed untouched at 148/148 — no change needed there

## Task Commits

Each task was committed atomically:

1. **Task 1: Add display_group() and wire it into render() and handle_post()** - `eeb1008` (feat)
2. **Task 2: Retarget the three fail-closed group assertions and extend the companion harnesses** - `e09ca03` (test)

_Note: `companion/test_companion_app.py` needed no change (verified, not modified) — see Deviations._

## Files Created/Modified
- `companion/pages/config_page.py` - `DISPLAY_CHECKBOX_VALUE`/`DISPLAY_SECTION_HEADING`/`DISPLAY_SECTION_CAPTION` constants, `display_group()`, `render()`'s sixth-group wiring and D-09 prefill, `handle_post()`'s eighth checkbox-resolution branch and docstring updates (seven → eight fields)
- `companion/test_config_page.py` - three retargeted fail-closed assertions (5→6), five new Display-group checks, the round-trip dict-equality literal gaining `"display_enabled": False`, `EXPECTED_CHECK_COUNT`'s effective assignment bumped 87 → 92

## Decisions Made
- `display_group()` mirrors `led_group()`, not `quiet_hours_group()` — the plan's own read-first note called this out explicitly, and it is the correct model since this group has no dependent fields
- The caption earns its own honest ~5-minute-latency sentence (D-02) rather than reusing the generic "applies on the next scheduled poll" clause every sibling caption ends on, because D-01's fixed 300s off-state cadence is genuinely independent of `wake_interval_s`/quiet hours
- `test_companion_app.py` was left untouched after confirming it passes at 148/148 — it exercises the page over real HTTP, not by whole-page dict comparison, so adding a redundant check there would have been unnecessary risk on a 148-check harness, per the plan's own instruction

## Deviations from Plan

**1. [Rule 1 - Bug] Updated a pre-existing whole-dict round-trip equality check**
- **Found during:** Task 2, first harness run after Task 1's edits
- **Issue:** `_valid_save_writes_both_and_returns_saved_key()`'s exact-dict-equality assertion against `device_config.load_device_config()`'s return value did not include the new `display_enabled` key, so it failed the moment `display_group()` existed (the same class of update `wake_interval_s`'s addition required of this exact test in 11-03-PLAN.md).
- **Fix:** Added `"display_enabled": False` to the expected dict literal, matching the pattern `wake_interval_s: None` established.
- **Files modified:** `companion/test_config_page.py`
- **Verification:** `config-page: 92/92 checks pass`
- **Committed in:** `e09ca03` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary consequence of adding an eighth registry field to a pre-existing exact-equality regression test; no scope creep — the plan's own "three fail-closed assertions" list was the group-shape assertions, and this fourth pre-existing failure surfaced from the same root cause (a sixth/eighth field appearing where a test compared an exact literal).

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `display_enabled` is now readable/writable end-to-end through the companion Settings page; `server/poll_loop.py` (12-04) and `stub-server/byos_server.py` (12-03) — running in parallel in this same wave — read it by JSON key name, independent of this plan's changes
- Ready for 12-06's closing work (the phase's on-glass verification and any remaining integration)
- No blockers

---
*Phase: 12-remote-display-on-off-toggle*
*Completed: 2026-09-05*

## Self-Check: PASSED
- FOUND: companion/pages/config_page.py
- FOUND: companion/test_config_page.py
- FOUND: .planning/phases/12-remote-display-on-off-toggle/12-05-SUMMARY.md
- FOUND commit: eeb1008
- FOUND commit: e09ca03
