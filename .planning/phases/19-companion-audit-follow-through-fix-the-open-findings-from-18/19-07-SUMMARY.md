---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 07
subsystem: ui
tags: [settings-form, validation, accessibility, aria, css, stdlib-only]

# Dependency graph
requires:
  - phase: 19
    plan: 04
    provides: "the CSP's script-src 'self' with no inline scripts, and companion/pages/config_page.py's poll_trigger_section() data-* attribute contract this plan's render() signature widening builds alongside"
provides:
  - "config_page.handle_post(form, ctx, errors=None): an optional caller-filled field-error dict, with first-error-per-field-wins semantics via a new _note_error() helper"
  - "Three new field-level pre-checks in handle_post(): a local HH:MM shape gate for quiet_hours_start/quiet_hours_end (pinned to agree with server/device_config.py's private gate), an explicit wake_interval_s range check, and the calendar_url invalid-signal message"
  - "config_page.render(ctx, scope=SCOPE_ALL, errors=None, submitted=None): every settings group builder repopulates its control from a rejected save's own submission and renders an accessible field-level error message (role=alert, aria-invalid, aria-describedby)"
  - "companion/app.py's _handle_settings_post() renders the same scoped page directly at 200 on a rejected save instead of redirecting with a generic flash, mirroring _handle_login_post()'s existing 200/401-on-failure precedent"
  - "A factored _page_shell_for() helper shared by _render_tab() and the new rejected-save branch"
  - ".field-error CSS rule composing the existing --color-status-error token"
affects: [any future plan touching companion/pages/config_page.py's handle_post()/render()/group builders, or companion/app.py's _handle_settings_post()/_render_tab()]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Signature widening over return-type change: handle_post(form, ctx, errors=None) and render(ctx, scope=SCOPE_ALL, errors=None, submitted=None) both add fully-defaulted trailing keyword parameters, matching every existing caller byte-for-byte when unused (config_page.py's own established convention, per 19-PATTERNS.md)"
    - "First-error-per-field-wins: _note_error(errors, field, message) is a no-op when errors is None and never overwrites an existing message for the same field"
    - "The explicit-is-None idiom applied to form repopulation: _submitted_or_current()/_submitted_checkbox_checked() distinguish submitted is None (an ordinary page-load render(), current wins) from submitted is an actual dict (a rejected save's own submission, even an empty one, since companion/app.py's read_form() never returns None) — collapsing that distinction to {} would silently unckeck every checkbox on every ordinary page load"
    - "200-on-validation-failure, not 422 or a redirect: mirrors _handle_login_post()'s existing send_html(401, ...) precedent for 'render the same page directly instead of redirecting with a flash', the only other place in this codebase with that shape"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/app.py
    - companion/static/style.css
    - companion/test_config_page.py
    - companion/test_companion_app.py

key-decisions:
  - "The write-only calendar_url field is the ONE control D-07's repopulation rule does not apply to (T-16-SECRET/T-19-12): its value stays empty on every branch of calendar_group(), even when submitted carries the URL the operator just typed — only its error message is added"
  - "The three radio-group fields (theme, theme_arriving, tracked_runway) render their field-level error message but do not gain an aria-invalid/aria-describedby attribute fragment: no single native input in a same-named radio group is uniquely 'the' control the message describes, unlike a checkbox/text/number/select field which has exactly one control to decorate"
  - "wake_interval_group() bypasses its own in-range/non-bool-int value_attr guard when repopulating from a real submission, echoing the raw submitted string verbatim (e.g. \"7\") even though it fails HTML5 min/max constraint validation on the user's next submit attempt — that native validation is the desired next-step prompt, not a bug, and is the only way to satisfy D-07's 'everything the user typed still in the fields' requirement for a syntactically-valid-but-out-of-range number"
  - "config_page.render()'s submitted parameter is deliberately NOT normalised to {} at the top of the function (a literal reading of the plan's own action text would do so) — collapsing None to {} would make every ordinary page-load render() call indistinguishable from a rejected save with every checkbox unticked, silently rendering the LED/quiet-hours/display/theme-arriving-enabled checkboxes unchecked on every normal page view. errors IS normalised to {}, which is harmless since every lookup already treats None/{} identically."
  - "_handle_settings_post() keeps the pre-existing redirect-with-flash branch as a fallback AFTER the new errors-branch, for any failure path that produces no field error (none exist today, but a future gate forgetting to call _note_error() should still reject visibly rather than silently succeed or fall through)"

requirements-completed: [CFG-01]

# Metrics
duration: 15min
completed: 2026-09-11
---

# Phase 19 Plan 07: Settings Field-Level Errors — Stop Discarding the Form on a Rejected Save (D-07) Summary

**A rejected Settings save now re-renders the same scoped page at 200 with every submitted value still in the fields (except the write-only calendar URL) and an accessible message under the one control that failed, instead of redirecting to a generic "Couldn't save settings" banner.**

## Performance

- **Duration:** ~15 min (first task commit to last)
- **Started:** 2026-09-11T07:56:31Z
- **Completed:** 2026-09-11T08:11:01Z
- **Tasks:** 3/3
- **Files modified:** 5

## Accomplishments
- `handle_post()` fills an optional `errors` dict with a field-keyed message for every real-user-error and hostile-request-shape rejection, via a new `_note_error()` helper, with zero change to its return type or to any of its 75 pre-existing callers
- Three new pre-checks report a real user error at its own field before ever reaching `save_device_config()`'s generic exception path: a malformed quiet-hours `HH:MM` (including an empty-but-present value), an out-of-range `wake_interval_s`, and an invalid calendar submission
- `render()` widened with `errors`/`submitted`, threaded through all seven settings-group builders — each control now repopulates from the rejected submission (`_submitted_or_current()`/`_submitted_checkbox_checked()`) and renders its own accessible error (`_field_error_html()`/`_field_error_attrs()`: `role="alert"`, `aria-invalid`, `aria-describedby`) — while staying byte-identical to today when neither argument is passed
- The write-only calendar feed URL is provably never echoed back, even while repopulating everything else
- Both quiet-hours time inputs gained `required` (a client-side convenience; the server-side gate remains authoritative)
- `_handle_settings_post()` now renders the same scoped page directly at 200 on a rejected save — mirroring the login form's own 200/401-on-failure precedent — instead of redirecting with a generic flash; the success path and the pre-existing calendar-signal branching below it are untouched
- `.field-error` styled from the existing `--color-status-error` token and `--space-xs` spacing token — zero new custom properties

## Task Commits

Each task was committed atomically:

1. **Task 1: Widen handle_post() with an errors dict and field-specific messages** - `8801049` (feat)
2. **Task 2: Repopulate the form and render field-level errors (D-07)** - `4a2682a` (feat)
3. **Task 3: Re-render the settings page at 200 on a rejected save (D-07)** - `f14771b` (fix)

**Plan metadata:** committed as part of this SUMMARY's own commit (worktree mode — orchestrator handles STATE.md/ROADMAP.md centrally after merge)

## Files Created/Modified
- `companion/pages/config_page.py` — `handle_post(form, ctx, errors=None)`: `_note_error()`, `ERROR_*` message constants, a local `_QUIET_HOURS_TIME_RE` (agreement-pinned against `server/device_config.py`'s private gate), and three new pre-checks; `render(ctx, scope=SCOPE_ALL, errors=None, submitted=None)`: `_field_error_html()`, `_field_error_attrs()`, `_submitted_or_current()`, `_submitted_checkbox_checked()`, and every group builder (`theme_fieldset()`, `runway_fieldset()`, `led_group()`, `quiet_hours_group()`, `wake_interval_group()`, `display_group()`, `calendar_group()`) widened to accept and use `errors`/`submitted`
- `companion/app.py` — `_handle_settings_post()`'s failure branch now builds `errors={}`, passes it into `handle_post()`, and renders a 200 re-render on any non-empty result; new `_page_shell_for()` helper factored out of `_render_tab()` and reused by both
- `companion/static/style.css` — `.field-error` rule beside `.section-caption`, composing `--color-status-error`/`--space-xs`
- `companion/test_config_page.py` — 12 new checks across the three tasks (147 → 154, `EXPECTED_CHECK_COUNT` re-derived three times)
- `companion/test_companion_app.py` — 1 new real end-to-end HTTP check (210 → 211, `EXPECTED_CHECK_COUNT` re-derived once)

## Decisions Made
See `key-decisions` in the frontmatter above for the five load-bearing decisions (calendar_url's repopulation exemption, radio-group aria scope, the wake_interval_s value-echo bypass, why `submitted` is not normalised to `{}`, and the redirect fallback ordering).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Avoided a literal reading of "normalise both to {} at the top" for render()'s `submitted` parameter**
- **Found during:** Task 2 (Repopulate the form and render field-level errors)
- **Issue:** The plan's action text says to normalise both `errors` and `submitted` to `{}` at the top of `render()`. Doing that literally for `submitted` would destroy the only signal the absent-means-unchecked checkbox fields (`led_enabled`/`quiet_hours_enabled`/`display_enabled`/`theme_arriving_enabled`) have for distinguishing "an ordinary page-load render(), nothing was submitted" from "a rejected save's own submission, which happened to have this checkbox unticked" — both would collapse to the identical `{}`, and every checkbox in that family would render unchecked on every normal page view regardless of the stored config.
- **Fix:** `errors` is normalised to `{}` (harmless — every lookup already treats `None`/`{}` identically). `submitted` is passed through unchanged (`None` or the real form dict); `_submitted_checkbox_checked()` and `_submitted_or_current()` both explicitly branch on `submitted is None` rather than relying on emptiness. Documented in `render()`'s own docstring and in `_submitted_checkbox_checked()`'s docstring.
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** `companion/test_config_page.py` 154/154; the byte-identical check (`render(ctx)` vs `render(ctx, errors=None, submitted=None)`) and every pre-existing checkbox-checked-state check pass unmodified.
- **Committed in:** `4a2682a` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug avoided before it could ship)
**Impact on plan:** Necessary for correctness — a literal implementation would have silently broken every checkbox's default state on every ordinary Settings page load. No scope creep: the fix is confined to the two helper functions and `render()`'s own normalisation line the plan was already touching.

## Issues Encountered
None beyond the deviation above.

## User Setup Required

None — no external service configuration required.

## Self-Check: PASSED

- FOUND: companion/pages/config_page.py
- FOUND: companion/app.py
- FOUND: companion/static/style.css
- FOUND: companion/test_config_page.py
- FOUND: companion/test_companion_app.py
- FOUND commit 8801049
- FOUND commit 4a2682a
- FOUND commit f14771b

## Next Phase Readiness
- A-25/D-07 is closed: a rejected Settings save no longer discards the user's other edits, reports the problem at the offending field, and never persists a partial save
- `handle_post()`/`render()`'s widened signatures are additive only — any future plan can pass `errors`/`submitted` from a new call site without touching this plan's work
- `companion/test_config_page.py` (154/154), `companion/test_companion_app.py` (209/211 — the two documented pre-existing root-sandbox WR-11 failures, unrelated to this plan, unchanged), `companion/test_contrast_check.py` (36/36), `companion/test_view_pages.py` (76/76), `companion/test_status_pages.py` (184/185 — the one documented pre-existing `anomaly_active()` root-sandbox failure, unrelated to this plan, unchanged)
- `scripts/run-all-tests.sh` reports exactly the 3 pre-existing-failure harnesses (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`) an untouched checkout also reports — no new failures
- The end-of-phase `<human-check>` (change the theme, clear the quiet-hours Start field, save, confirm the page comes back with the new theme still selected and an error under Start with nothing saved) is still outstanding — deferred to end-of-phase per the plan's own verification section
- No blockers for subsequent phase-19 plans; this plan did not touch `companion/layout.py`, `companion/pages/health_page.py`, or `companion/test_status_pages.py`, which plan 19-06 owns

## Threat Flags

None — every new surface this plan introduces (the reflected `submitted` values, the write-only calendar URL's continued non-repopulation) was already named in the plan's own `<threat_model>` (T-19-26, T-19-12, T-19-27, T-19-28, T-19-29) and is covered by the harness checks above; no new network endpoint, auth path, file-access pattern, or schema change was added.

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 07*
*Completed: 2026-09-11*
