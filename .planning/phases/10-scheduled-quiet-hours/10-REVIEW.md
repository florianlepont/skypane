---
phase: 10-scheduled-quiet-hours
reviewed: 2026-09-03T20:59:55Z
depth: standard
files_reviewed: 13
files_reviewed_list:
  - .claude/skills/sketch-findings-skypane/SKILL.md
  - companion/pages/config_page.py
  - companion/static/style.css
  - companion/test_config_page.py
  - server/device_config.py
  - server/plane/render.py
  - server/poll_loop.py
  - server/test_config_history.py
  - server/test_poll_loop.py
  - server/test_render.py
  - stub-server/VENDOR.md
  - stub-server/byos_server.py
  - stub-server/test_poll_cycle.py
findings:
  critical: 0
  warning: 2
  info: 1
  total: 3
status: issues_found
---

# Phase 10: Code Review Report

**Reviewed:** 2026-09-03T20:59:55Z
**Depth:** standard
**Files Reviewed:** 13
**Status:** issues_found

## Summary

This phase adds a scheduled quiet-hours curfew: a DST-safe window-arithmetic
helper (duplicated across `server/device_config.py` and the vendored,
stdlib-only `stub-server/byos_server.py`), three new HH:MM/boolean
device-config fields with server-side validation, a dedicated
`_build_quiet_hours_canvas()` panel screen, and a "render once at
entry / hold / repaint-on-exit" state machine layered into
`server/poll_loop.py::run_once()`.

I traced the window arithmetic numerically against real DST transition
dates (spring-forward and fall-back 2026, plus a non-DST wrap-midnight
case) and confirmed the UTC-subtraction fix is correct in all four cases.
I diffed `seconds_until_quiet_hours_end()`/`_HHMM_RE` between
`server/device_config.py` and `stub-server/byos_server.py` and found them
byte-for-byte identical, matching the automated drift guard in
`stub-server/test_poll_cycle.py` (which I confirmed actually extracts and
compares the right text blocks). I traced every branch of
`poll_loop.run_once()`'s quiet-hours entry/hold/exit logic by hand,
including the interaction between `quiet_hours_exited`, `battery_changed`,
`queue_dirty`, and the pending-flight queue, and could not construct a
scenario where a stale QUIET HOURS image survives past window exit or
where the flag fails to persist. I then ran all five affected test
suites (39 + 127 + 51 + 73 + 29 = 319 checks) end-to-end in the repo's
own venv; all 319 pass.

No BLOCKER-level defects found. Two WARNING-level robustness/UX gaps and
one INFO-level documentation-staleness nit are listed below.

## Warnings

### WR-01: Battery-low icon is frozen for the entire quiet-hours window, even if the battery crosses the warning threshold mid-window

**File:** `server/poll_loop.py:716-733`
**Issue:** Inside the quiet-hours early-return branch, `battery_low_active`
is recomputed and persisted to `poll_state.json` every cycle (so the
*hysteresis memory* stays current), but the panel is only ever repainted
`if not was_quiet` — i.e. on the single entry cycle. If the device's
battery crosses `BATTERY_LOW_THRESHOLD_MV` partway through an 8-hour
window, the physical panel keeps showing the entry-time QUIET HOURS
screen (with whatever battery icon state was true at entry) until the
window ends. For a battery-only device whose whole point is to surface a
DEVICE-04 low-battery signal, silently deferring that signal for up to
several hours — precisely during the longest unattended sleep interval —
undercuts the feature it's supposed to complement. The code comment at
lines 718-723 acknowledges this is deliberate ("nothing rendered
mid-window can ever reach the glass... a battery transition during the
window must not trigger a repaint"), but the stated rationale (avoiding a
full ~31.5s e-ink refresh) doesn't establish that the tradeoff was
weighed against DEVICE-04's own stated purpose.
**Fix:** At minimum, confirm with the DEVICE-04/CFG-05 stakeholders that
deferring the battery-low warning for the whole window is acceptable; if
not, add a second render inside the quiet-hours branch gated on
`battery_changed` (mirroring the `held` branch's own
`source_fault != previous_source_fault or battery_changed` re-render
gate at line 1055), e.g.:
```python
if not was_quiet or battery_changed:
    canvas = render.build_canvas(
        None, "quiet_hours", quiet_hours_until=quiet_until,
        source_fault=source_fault, battery_low=battery_low,
    )
    rendered = panel_format.pack_panel(canvas)
    panel_changed = write_panel_atomic(state_dir, rendered)
    ...
```

### WR-02: A zero-width (start == end) quiet-hours window silently persists and never activates, with no user-facing feedback

**File:** `server/device_config.py:498-505`, `companion/pages/config_page.py:760-870`
**Issue:** `seconds_until_quiet_hours_end()` correctly documents and
implements "start_hm == end_hm is a zero-width window that is never
active" as an intentional, not-a-bug behavior. However, nothing in
`config_page.handle_post()` or `save_device_config()` rejects or flags a
submitted config where the Start and End times are equal (or, more
generally, warns when the resulting window has zero width). A user who
mistypes or leaves both time fields at the same value will have their
save silently succeed (`FLASH_SAVED`, the standard "saved but not yet
applied" copy) with quiet hours effectively permanently disabled — with
no distinguishing message telling them the window they just configured
will never take effect. This is a real support/confusion trap: the user
believes quiet hours are on (checkbox checked, times saved) but the
frame never enters the state.
**Fix:** Either (a) reject `quiet_hours_start == quiet_hours_end` in
`save_device_config()` with a `ValueError` (surfacing `FLASH_SAVE_FAILED`
so the user gets feedback and can correct it), or (b) add a distinct
flash/warning copy in `config_page.py` for this specific case so the
"saved" confirmation doesn't imply the feature is now doing something.

## Info

### IN-01: `config_page.py`'s module docstring is stale relative to the module's actual scope

**File:** `companion/pages/config_page.py:1-13`
**Issue:** The top-of-file docstring still describes the module as "CFG-01
(theme picker), CFG-12 (runway picker), and CFG-07's 'Trigger poll now'
control" — it doesn't mention the Diagnostic LED group (added in an
earlier phase) or, now, the Quiet hours group this phase adds
(`quiet_hours_group()`, `QUIET_HOURS_*` constants, the three new
`handle_post()` fields). Every individual function is well-documented in
place, but a reader skimming only the module docstring gets an
increasingly incomplete picture of what `render()`/`handle_post()` now
cover.
**Fix:** Extend the module docstring's opening sentence to name the LED
and Quiet-hours groups alongside Theme/Runway/Poll, or replace the
enumerated feature list with a pointer to `render()`'s own docstring/the
four `*_group()`/`*_fieldset()` functions.

---

_Reviewed: 2026-09-03T20:59:55Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
