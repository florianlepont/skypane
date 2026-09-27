---
phase: 40-companion-architecture-routes-pages-templates-i18n-keys
plan: 05
subsystem: ui
tags: [companion, settings-page, refactor, module-split, function-length]

# Dependency graph
requires:
  - phase: 40-01
    provides: "test-support/companion_structure.py (file/function line-count measurement), companion/test_structure_guards.py (the allowlist this plan shrinks), companion/testdata/render_baseline.json + companion/test_render_baseline.py (the byte-equality proof this plan's split is behaviour-preserving)"
provides:
  - "companion/settings/ package: form.py (shared field-error/repopulation helpers), theme.py (palette/aspect-card rendering), runway_led.py, quiet_hours.py, wake_interval.py, notifications.py, calendar.py, rules.py — one module per settings group"
  - "companion/pages/config_page.py shrunk from 3384 to 1194 lines (now under the 1500-line guard ceiling), keeping only scope/render/handle_post/assembly plus explicit re-export imports of every settings-group name"
  - "_aspect_card_html, _calendar_connection_html and notifications_group all at or under the 80-code-line ceiling"
affects: ["40-06", "40-07", "40-08", "40-09", "40-10"]

tech-stack:
  added: []
  patterns:
    - "A settings-group module never imports companion.pages.* (enforced by grep in this plan's own verify step); group modules may import each other in one direction only — companion.settings.theme owns the shared chip/row-building primitives (_usage_row_html, _usage_row_summary_html, _palette_grid_html, _theme_chip_grid_html, _palette_hex) and never imports calendar/rules/notifications, which import theme and form instead"
    - "A group builder that needs another group's row HTML takes it as an already-built string parameter (calendar_usage_row_html, rules_usage_row_html) rather than the two modules importing each other, which is how the theme<->calendar/rules import cycle this split would otherwise create was avoided"
    - "Re-exporting a moved name from its new module uses an explicit `from companion.settings.X import NAME as NAME` alias — ruff's F401 (unused import) treats a redundant self-alias as an intentional re-export and does not flag it, which a plain `from X import NAME` would"
    - "A too-long builder is shortened by extracting its single largest self-contained sub-block into its own named function (_calendar_status_html, _calendar_url_field_html, _notifications_url_field_html), not by restructuring its control flow"

key-files:
  created:
    - companion/settings/__init__.py
    - companion/settings/form.py
    - companion/settings/theme.py
    - companion/settings/runway_led.py
    - companion/settings/quiet_hours.py
    - companion/settings/calendar.py
    - companion/settings/rules.py
    - companion/settings/wake_interval.py
    - companion/settings/notifications.py
  modified:
    - companion/pages/config_page.py
    - companion/test_structure_guards.py

key-decisions:
  - "Moved the Calendar and colour-Rules groups in Task 1 (companion/settings/calendar.py, rules.py), ahead of the plan's own Task-2 boundary for those two files, because _aspect_card_html calls _calendar_connection_html and the rule-list/add-form/suggestion-chip builders directly — splitting theme.py without them in the same commit would have forced either a config_page import from theme.py (the acceptance criterion this plan forbids) or a theme<->calendar/rules import cycle"
  - "_aspect_card_html no longer takes ctx, calendar_configured, calendar_drift, calendar_last_synced_at, calendar_last_attempt_at, calendar_entry_count, or current_calendar_theme_id: it now takes calendar_row_html, calendar_disconnect_form_html and rules_row_html as pre-built HTML, computed by two new functions (calendar.calendar_usage_row_html, rules.rules_usage_row_html) that render() calls first. This is the mechanism that keeps companion.settings.theme independent of calendar/rules while producing byte-identical output — verified by companion/test_render_baseline.py, not asserted"
  - "departures_safe_theme_id() (new, in theme.py) is the one place the departures-theme fallback (submitted-or-current, falling back to DEFAULT_THEME_ID when unregistered) is computed; render() calls it once and threads the result into calendar_usage_row_html so the Calendar row's own 'same as departures' fallback can never disagree with the Aspect card's own departures/arrivals rows"

requirements-completed: [CMP-03, CMP-06]

duration: ~2h
completed: 2026-09-27
---

# Phase 40 Plan 05: config_page.py settings-group split Summary

Split `companion/pages/config_page.py` (3384 lines) into a `companion/settings/` package of eight group modules (form, theme, runway_led, quiet_hours, calendar, rules, wake_interval, notifications), shrinking config_page.py to 1194 lines — under the file-length guard's 1500-line ceiling for the first time this phase — and bringing all three previously over-length builders (`_aspect_card_html`, `_calendar_connection_html`, `notifications_group`) at or under the 80-code-line function ceiling, with `companion/test_render_baseline.py` proving every page still renders byte-identically in both languages and both themes.

## Performance

- **Duration:** ~2h
- **Completed:** 2026-09-27
- **Tasks:** 2/2 completed
- **Files created:** 9
- **Files modified:** 2

## Accomplishments

- `companion/settings/form.py` holds the six shared field-error/repopulation helpers plus the handful of constants read by three or more groups (`SETTINGS_FORM_ID`, `CURRENT_BADGE_LABEL`/`_ATTR`, `DIRTY_SECTION_ATTR`, `CALENDAR_HOW_IT_WORKS_SUMMARY`) — the one module every other settings module may depend on with no risk of a cycle.
- `companion/settings/theme.py` holds the palette/chip/aspect-card rendering primitives and the (rewritten) `_aspect_card_html`, now independent of calendar/rules — see Deviations below for why and how.
- `companion/settings/{runway_led,quiet_hours,wake_interval}.py` are straightforward verbatim moves (constants + functions), each importing only from `form.py`.
- `companion/settings/{calendar,rules}.py` each hold their group's full rendering (including the two-step calendar-disconnect confirm page and the colour-rules add/list/suggestion-chip editor) plus a new `*_usage_row_html()` function that builds that group's complete Aspect-card row, importing `theme.py`'s row-building primitives one-directionally.
- `companion/settings/notifications.py` holds the Notifications card, its write-only URL field extracted into `_notifications_url_field_html()` to bring `notifications_group()` from 86 to 59 code lines.
- `companion/settings/calendar.py`'s `_calendar_connection_html()` had its status line extracted into `_calendar_status_html()` (also the future home of plan 40-10's live "refreshed Xm ago" conversion) and its feed-URL field extracted into `_calendar_url_field_html()`, bringing it from 114 to 70 code lines.
- `companion/pages/config_page.py` re-exports every one of the ~135 moved names external code reads as `config_page.X`, via explicit `from companion.settings.MODULE import NAME as NAME` blocks — the redundant self-alias is ruff's own recognised "intentional re-export" marker, so `ruff check` (select F401) stays clean even for names config_page.py's own remaining code never touches itself.
- `companion/test_structure_guards.py`'s `PENDING_OVERSIZED_FILES` no longer names `companion/pages/config_page.py`; `PENDING_LONG_FUNCTIONS` no longer names `_aspect_card_html`, `_calendar_connection_html` or `notifications_group`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extract form helpers, theme/aspect, runway/LED and quiet-hours groups** - `14e5a05` (feat) — also carries the Calendar and colour-Rules groups, moved early; see Deviations.
2. **Task 2: Extract wake, notifications, calendar and rules groups; split their long builders** - `ea4d12e` (feat) — the calendar/rules *files* already existed from Task 1's deviation; this commit adds wake_interval.py and notifications.py, and performs the `_calendar_connection_html`/`notifications_group` function-length splits.

## Files Created/Modified

- `companion/settings/__init__.py` - package docstring: one module per settings group, the no-import-cycle rule
- `companion/settings/form.py` - `_field_error_html`, `_describedby_attr`, `_with_next_wake`, `_field_error_attrs`, `_submitted_or_current`, `_submitted_checkbox_checked`, plus shared constants
- `companion/settings/theme.py` - palette/chip/live-preview builders, `_usage_row_html`/`_usage_row_summary_html`, `departures_safe_theme_id()` (new), `_aspect_card_html` (rewritten signature)
- `companion/settings/runway_led.py` - `runway_fieldset`, `led_group`, `quick_led_form_html`
- `companion/settings/quiet_hours.py` - window-arithmetic helpers, the 24h dial SVG/handles/readout, `quiet_hours_group`
- `companion/settings/calendar.py` - `_masked_calendar_url`, `_calendar_status_html` (new), `_calendar_url_field_html` (new), `_calendar_connection_html`, `calendar_disconnect_confirm_page`, `calendar_usage_row_html` (new)
- `companion/settings/rules.py` - `poll_trigger_section`, the colour-rules add/list/suggestion-chip editor, `rules_usage_row_html` (new)
- `companion/settings/wake_interval.py` - the freshness/battery-life gauge text, the range slider, `wake_interval_group`
- `companion/settings/notifications.py` - `_notifications_url_field_html` (new), `notifications_group`, `notifications_test_section`
- `companion/pages/config_page.py` - shrunk to `scope_groups`/`submitted_scope`/`submitted_return_route`, the assembly helpers, `render()`, `handle_post()`, and the explicit re-export imports
- `companion/test_structure_guards.py` - `PENDING_OVERSIZED_FILES`/`PENDING_LONG_FUNCTIONS` updated to reflect the new, smaller offender set

## Decisions Made

- Calendar and colour-Rules groups moved in Task 1's commit rather than Task 2's, purely to resolve a real circular-import constraint (see Deviations) — no scope was added beyond what the plan already specified for those two groups; their own function-length split (a Task 2 requirement) still happened in the Task 2 commit.
- `_aspect_card_html`'s signature changed materially (dropped `ctx` and six calendar-specific parameters, gained three pre-built-HTML parameters). Nothing outside `render()` called it directly (confirmed by grep before making the change), so this was a safe internal contract change with no external caller to update.
- Constants used by exactly one settings group moved into that group's module; constants used by two or more groups (or by config_page's own kept code plus one group) moved into `form.py`; constants used only by config_page's own kept code (`handle_post`/`render`/assembly) or read externally but never internally stayed in `config_page.py` untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - blocking issue: circular dependency] Moved Calendar and colour-Rules groups into Task 1's commit instead of Task 2's**
- **Found during:** Task 1, while designing `_aspect_card_html`'s extraction into `theme.py`
- **Issue:** `_aspect_card_html` (theme's own function, per the plan's own line range) calls `_calendar_connection_html()` and the colour-rules `_rule_list_html()`/`_rule_add_form_html()`/`_rule_suggestion_chips_html()` directly. At the point Task 1 alone would have completed, those functions were still physically in `config_page.py` (Task 2's stated scope) — so `theme.py` would have needed `from companion.pages.config_page import ...`, which the plan's own acceptance criteria explicitly forbid (`grep -rlE "companion.pages|config_page" companion/settings/*.py` must print nothing). Moving Calendar/Rules to Task 2 as originally planned did not resolve this either: it only delays the same import to the *next* commit, and `theme.py`'s `_aspect_card_html` would still need it during Task 1's own verification window (the render-baseline test imports the whole module graph).
- **Fix:** Restructured `_aspect_card_html` so it never calls into Calendar/Rules at all — it now takes their two rows as pre-built HTML strings, computed by two new functions in `companion/settings/calendar.py` and `companion/settings/rules.py` (`calendar_usage_row_html`, `rules_usage_row_html`) that `render()` calls first. Those two new functions import `theme.py`'s row-building primitives (one-directional: `calendar`/`rules` → `theme`, never the reverse). This meant `calendar.py` and `rules.py` had to exist by the end of Task 1's commit (so `theme.py`'s tests could import cleanly), so both groups' full extraction (not just the pieces `_aspect_card_html` needed) landed in Task 1's commit; their function-length splitting (a genuinely Task-2-scoped requirement) still happened in Task 2's own commit.
- **Files modified:** `companion/settings/theme.py`, `companion/settings/calendar.py`, `companion/settings/rules.py`, `companion/pages/config_page.py`
- **Verification:** `companion/test_render_baseline.py` passes (byte-identical output); `grep -rlE "companion.pages|config_page" companion/settings/*.py` prints nothing; no import cycle (`python3 -c "import companion.pages.config_page"` succeeds).
- **Commit:** `14e5a05`

**2. [Rule 1 - bug] `companion/settings/rules.py` missing `from server import history_db`, silently swallowed by a broad `except Exception`**
- **Found during:** Task 1, first `companion/test_render_baseline.py` run after the calendar/rules move
- **Issue:** `_rule_suggestion_chips_html()` calls `history_db.open_db(state_dir)`, but the module never imported `history_db` — a `NameError` on every call, caught by the function's own `except Exception: return ""` (a deliberate "never raise, degrade to no suggestions" contract), so the bug produced no traceback, only a silently empty render that differed from the baseline.
- **Fix:** Added `history_db` to the module's `from server import device_config, history_db` line.
- **Files modified:** `companion/settings/rules.py`
- **Verification:** `companion/test_render_baseline.py` passes; a standalone script confirmed `_rule_suggestion_chips_html()` now returns real suggestion-chip markup against seeded state.
- **Commit:** `14e5a05`

---

**Total deviations:** 2 (1 forced reordering for a real circular-import constraint, 1 bug fix in code moved during that reordering)
**Impact on plan:** Both were necessary for the split to import cleanly and render correctly. The net file/function inventory at the end of Task 2 matches what the plan specified — only the commit boundary for calendar.py/rules.py's initial creation moved earlier. No scope creep: no group's rendering logic changed beyond the `_aspect_card_html`/`calendar_usage_row_html`/`rules_usage_row_html` restructuring documented above, and `test_render_baseline.py` proves the final HTML is unchanged.

## Issues Encountered

None beyond the deviations above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `companion/pages/config_page.py` is now under the 1500-line guard ceiling; `companion/app.py` and `companion/pages/health_page.py` remain the two oversized production files for a later plan.
- `companion/test_structure_guards.py`'s `PENDING_LONG_FUNCTIONS` now names only `handle_post`, `render` (both explicitly deferred to plan 40-08 per this plan's own objective), `airlines_page.py::_airline_card_html`, `health_page.py::battery_sparkline_svg` and `history_page.py::_history_cards_html` — none of which this plan touched.
- `companion/settings/calendar.py::_calendar_status_html()` is named and shaped exactly as plan 40-10 will need it for the "refreshed Xm ago" live-age conversion (CFG-34b) — its full `configured, drift, last_synced_at, last_attempt_at, now, entry_count` signature and its `layout.status_row()`-shaped return are unchanged from `_calendar_connection_html()`'s own prior inline computation, just relocated.
- No blockers.

---
*Phase: 40-companion-architecture-routes-pages-templates-i18n-keys*
*Completed: 2026-09-27*

## Self-Check: PASSED

All 9 created files confirmed present on disk; both task commit hashes
(`14e5a05`, `ea4d12e`) confirmed present in git history.
