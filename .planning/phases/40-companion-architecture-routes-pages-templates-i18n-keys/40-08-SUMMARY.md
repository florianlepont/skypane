---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 08
subsystem: ui
tags: [python, stdlib, wsgi-free-http-server, settings-form, refactor]

# Dependency graph
requires:
  - phase: 40-companion-architecture-routes-pages-templates-i18n-keys
    provides: "companion/settings/*.py per-group builder modules (40-05), the shared companion/settings/form.py helpers"
provides:
  - "companion/settings/form_post.py: one validate-and-resolve function per settings group, called by config_page.handle_post() in the exact order the unsplit function checked the same fields"
  - "config_page.render() split into per-scope/per-group assembly helpers, no function over 80 code lines"
  - "config_page.py under both the 1500-line file ceiling and the 80-line function ceiling with zero PENDING_LONG_FUNCTIONS entries remaining for this file"
affects: [companion-settings, companion-config-page, companion-structure-guards]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Validate-then-resolve per-group resolvers returning either a save_device_config() kwargs dict or a FAILED sentinel, called from a lazy per-step loop (never a pre-built tuple of already-evaluated calls) so a later group's resolver never runs after an earlier one has already failed"
    - "render() as a thin orchestrator delegating to _render_current_values/_render_calendar_and_poll_context/_next_wake_clock_and_iso/_dirty_bar_strings/_group_builders/_render_<scope>_scope/_poll_html_for_scope/_settings_page_html, each under 80 code lines"

key-files:
  created:
    - companion/settings/form_post.py
  modified:
    - companion/pages/config_page.py
    - companion/settings/form.py
    - companion/test_config_page_05.py
    - companion/test_structure_guards.py

key-decisions:
  - "form_post.py resolvers are called one per line-item, not strictly one call per named group: four groups (theme, calendar, quiet_hours, notifications) get two calls each — a validate call at the field's original check position and a resolve call at its original resolve position — because the unmodified handle_post() checked those groups' fields at two separate points in its single linear pass, interleaved with other groups' checks. Preserving the plan's own hard requirement (byte-identical errors in the exact same order) over the letter of 'one function per group' was the deliberate trade-off; the plan's own text anticipated this ('keep a two-phase validate-then-resolve structure if that is what preserves the order')."
  - "Shared error-message/checkbox-value constants, the four calendar-signal sentinels and _note_error moved out of config_page.py: ERROR_*/LED_CHECKBOX_VALUE/etc. into form_post.py (form_post.py cannot import config_page back), _note_error into companion/settings/form.py (the existing shared leaf module). config_page.py re-exports every one of them under its own name so every existing companion/app.py and test-suite reference to config_page.X keeps working unchanged."
  - "companion/settings/screen.py was not created: config_page.py was already 1040 lines after Task 1's move (well under the 1500 ceiling) before Task 2 started, so the plan's own conditional ('if not [under 1500], move remaining helpers... into settings/screen.py') did not trigger. render()'s 80-line-per-function split alone was sufficient."

# Metrics
duration: 35min
completed: 2026-09-27

requirements-completed: [CMP-03, CMP-06]
---

# Phase 40 Plan 08: Split handle_post per settings group and shrink render() Summary

**Split config_page.py's 150-line handle_post() into nine settings-group resolvers in a new companion/settings/form_post.py (called in the exact original validation order) and its 183-line render() into eight assembly helpers, closing out CMP-03/CMP-06 for this file with zero behaviour change.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-09-27T14:10:00Z (approx.)
- **Completed:** 2026-09-27T14:50:00Z (approx.)
- **Tasks:** 2
- **Files modified:** 5 (1 created)

## Accomplishments
- `companion/settings/form_post.py` — 13 resolver functions covering the 9 settings groups (theme, screen, runway, quiet hours, LED, wake interval, display, notifications, calendar), each returning a `save_device_config()` kwargs dict or the `FAILED` sentinel; `handle_post()` is now a 41-line orchestrator that calls them one at a time (via a lazily-evaluated list of thunks, not a pre-built tuple) and makes exactly one `save_device_config()` call.
- `config_page.render()` split into `_render_current_values`, `_render_calendar_and_poll_context`, `_next_wake_clock_and_iso`, `_dirty_bar_strings`, `_group_builders`, `_render_display_scope`, `_render_device_scope`, `_render_all_scope`, `_poll_html_for_scope` and `_settings_page_html`; `render()` itself is now a 34-line orchestrator.
- `companion/pages/config_page.py` is 1105 lines (was 1194 after 40-05, well under the 1500 ceiling) with zero functions over 80 code lines; `companion/test_structure_guards.py`'s `PENDING_LONG_FUNCTIONS` no longer lists `config_page.py::handle_post` or `config_page.py::render`.
- Two new characterisation tests (`test_handle_post_errors_keep_their_order_for_a_fully_invalid_submission`, `test_handle_post_saves_the_same_config_for_every_group_shape`) captured from the unmodified `handle_post()` before the split, both still passing after it — the split's own regression proof.
- `companion/test_render_baseline.py` passes byte-for-byte both before and after; the full companion suite (1851 tests) passes with 0 failures.

## Task Commits

1. **Task 1: Characterise handle_post, then split it per settings group**
   - `5be77ea` (test) — the two characterisation tests, run and passing against the unmodified `handle_post()`
   - `f8f613d` (feat) — `companion/settings/form_post.py` created, `handle_post()` rewritten as the per-group orchestrator, shared constants moved and re-exported
2. **Task 2: Split render per scope/group and close config_page's size items**
   - `f8f9ed4` (refactor) — `render()` split into the 8 helpers listed above; `PENDING_LONG_FUNCTIONS` updated

**Plan metadata:** (this commit)

_Note: Task 1 is `tdd="true"`; the RED-equivalent commit (`5be77ea`) is a characterisation-test commit against the unmodified function (both tests passed immediately — this is a refactor-safety-net pattern, not a failing-test RED gate), and the GREEN commit (`f8f613d`) is the actual split, verified against the same literals._

## Files Created/Modified
- `companion/settings/form_post.py` (new, 331 lines) — per-group `resolve_*()` validators/resolvers, the `FAILED` sentinel, and the error-message/checkbox-value/calendar-signal constants moved out of `config_page.py`
- `companion/settings/form.py` — added the shared `_note_error()` helper (moved from `config_page.py`)
- `companion/pages/config_page.py` — `handle_post()` reduced from 150 to 41 code lines; `render()` reduced from 183 to 34 code lines via 8 new helper functions; re-exports every constant/function moved to `form_post.py` under its original `config_page.X` name
- `companion/test_config_page_05.py` — two new characterisation tests plus their golden literals (captured from a live run of the unmodified code, not guessed)
- `companion/test_structure_guards.py` — removed `config_page.py::handle_post` and `config_page.py::render` from `PENDING_LONG_FUNCTIONS`

## Decisions Made
See `key-decisions` in the frontmatter above (form_post.py's two-call groups, the constant/`_note_error` moves and re-exports, and skipping `companion/settings/screen.py`).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Lazy resolver dispatch instead of a tuple of already-evaluated calls**
- **Found during:** Task 1, first verification run
- **Issue:** The first `handle_post()` draft built a Python tuple literal of resolver *call results* (`(form_post.resolve_theme(...), form_post.resolve_screen(...), ...)`) to iterate over. Python evaluates every element of a tuple literal before the `for` loop starts, so all 13 resolvers ran unconditionally on every submission — every group's own error landed in `errors` at once instead of stopping at the first offender, changing which error message a multi-invalid-field submission shows (a real, observable rendered-output regression the plan explicitly forbids).
- **Fix:** Rewrote the dispatch as a tuple of zero-argument lambdas (`steps = (lambda: form_post.resolve_theme(form, errors), ...)`), invoked one at a time inside the loop, returning `FLASH_SAVE_FAILED` immediately on the first `FAILED` result — exactly reproducing the unsplit function's own early-return, first-error-wins behaviour.
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** `test_handle_post_errors_keep_their_order_for_a_fully_invalid_submission` caught the regression immediately (13 errors recorded instead of the expected 1-per-call); re-ran green after the fix, along with the full task-1 verify command (210 tests).
- **Committed in:** `f8f613d` (part of the Task 1 commit — caught before committing)

---

**Total deviations:** 1 auto-fixed (1 bug caught by the plan's own characterisation test before it ever reached a commit)
**Impact on plan:** The bug never shipped; the characterisation test written in Task 1 did exactly the job the plan intended it for. No scope creep.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- CMP-03 (file split) and CMP-06 (function size / handle_post per group) are now fully satisfied for `companion/pages/config_page.py`; `REQUIREMENTS.md` already carried both as Complete (satisfied across earlier 40-0x plans plus this one's own closing step).
- `companion/test_structure_guards.py`'s `PENDING_LONG_FUNCTIONS` now lists only `airlines_page.py::_airline_card_html`, `health_page.py::battery_sparkline_svg` and `history_page.py::_history_cards_html` — none in `config_page.py` or `companion/settings/`.
- No blockers for subsequent Phase 40 plans.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED
- FOUND: .planning/phases/40-companion-architecture-routes-pages-templates-i18n-keys/40-08-SUMMARY.md
- FOUND: companion/settings/form_post.py
- FOUND commit: 5be77ea (test)
- FOUND commit: f8f613d (feat)
- FOUND commit: f8f9ed4 (refactor)
