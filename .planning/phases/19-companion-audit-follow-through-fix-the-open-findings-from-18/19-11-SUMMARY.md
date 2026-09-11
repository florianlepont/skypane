---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
plan: 11
subsystem: ui
tags: [settings-form, accessibility, aria, confirmation-flow, csp, stdlib-only]

# Dependency graph
requires:
  - phase: 19
    plan: 04
    provides: "the six-touch-point duplicated-not-imported static-script contract this plan's confirm-submit.js reuses verbatim, and script-src 'self' with no inline scripts"
  - phase: 19
    plan: 07
    provides: "config_page.py's render()/handle_post() errors/submitted signature widening and the _field_error_html()/_field_error_attrs() helpers this plan extends with a hint_id parameter"
  - phase: 19
    plan: 10
    provides: "quiet_hours_group()'s current markup shape this plan adds a caption id to, and dirty-state.js's own submit-listener scoping this plan's confirm-submit.js must not collide with"
provides:
  - "POST /settings/calendar/disconnect: a dedicated, session-gated, two-step-confirmed route that erases nothing without an exact confirm=yes"
  - "companion/static/confirm-submit.js: the ninth static script, the inline-free native confirm() step for any form[data-confirm]"
  - "role=\"radiogroup\" + aria-labelledby + aria-describedby on Theme's two chip grids and the Runway row, with zero new <fieldset>/<legend> elements"
  - "_describedby_attr(*ids) and _field_error_attrs(..., hint_id=None): the single builders of every aria-describedby fragment on the Settings page"
affects: [any future plan touching companion/pages/config_page.py's calendar_group()/render()/handle_post()/group builders, companion/app.py's do_POST()/do_GET(), or companion/layout.py's page_shell()]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Server-rendered two-step confirmation page as the real control, native confirm() as a misclick guard only — companion/static/confirm-submit.js's own header comment states this explicitly so a future reader never mistakes the dialog for authorisation"
    - "role=\"radiogroup\" + aria-labelledby as the compatible-with-zero-<fieldset> alternative to a literal <fieldset>/<legend>, applied via _theme_chip_grid_html()'s existing extra_attr seam rather than a second seam"
    - "_describedby_attr(*ids): drops falsy ids, joins survivors with one space (hint first, then error), returns \"\" when none remain — the single place aria-describedby is ever assembled in this file"

key-files:
  created:
    - companion/static/confirm-submit.js
  modified:
    - companion/pages/config_page.py
    - companion/app.py
    - companion/layout.py
    - companion/test_config_page.py
    - companion/test_companion_app.py

key-decisions:
  - "Disconnecting the calendar moved from an in-form checkbox to a standalone POST /settings/calendar/disconnect form, rendered by render() as a sibling of the settings form (never a descendant — HTML forbids nesting <form>, and this action needs its own confirmation step the shared form's fields never have)"
  - "submitted_calendar_signal()'s checkbox-interpreting gates 1-3 are deliberately LEFT IN PLACE, not deleted, even though the ordinary rendered form can no longer produce a calendar_disconnect field — they still correctly reject a hostile client crafting that field into a /settings POST, via handle_post()'s existing all-or-nothing rejection (19-RESEARCH.md Pitfall 7)"
  - "The native confirm() dialog in confirm-submit.js is documented, repeatedly and explicitly, as a misclick guard only — the server-rendered confirmation page (calendar_disconnect_confirm_page()) is the real control, since the dialog is trivially bypassable (no-JS, CSP block, hand-crafted request)"
  - "D-12's radiogroup semantics are wired through _theme_chip_grid_html()'s EXISTING extra_attr seam (the same seam ARRIVAL_GRID_ATTR already uses) rather than adding a second attribute-injection parameter, so the two grids can never drift apart in how they accept new attributes"
  - "_field_error_attrs() gained a fully-defaulted hint_id=None keyword (signature widening, not a new function) so every pre-Task-3 call site keeps emitting byte-identical output when hint_id is omitted, matching this file's own established convention for extending a many-caller function"

requirements-completed: [CFG-01]

# Metrics
duration: ~70min
completed: 2026-09-11
---

# Phase 19 Plan 11: Calendar Disconnect Confirmation and Settings Accessibility Groups (D-08/D-12, A-26/A-30) Summary

**Calendar disconnect is now its own confirmed, session-gated route instead of a checkbox buried in the Settings form, and the theme/runway pickers announce as named ARIA radiogroups with every hint linked to its control — without a single new `<fieldset>` or `<legend>` element.**

## Performance

- **Duration:** ~70 min (first task commit to last)
- **Started:** 2026-09-11 (worktree base commit `f58c634`)
- **Completed:** 2026-09-11T16:15:00Z
- **Tasks:** 3/3
- **Files modified:** 5 (1 created)

## Accomplishments

- `POST /settings/calendar/disconnect` (D-08/A-26): a dedicated, `require_session()`-gated route with its own standalone form (`calendar_disconnect_section()`), outside `<form id="settings-form">`. A bare POST, or any confirm value other than the exact accepted token, renders a server-side two-step confirmation page (`calendar_disconnect_confirm_page()`) at 200 and erases nothing; only `confirm=yes` calls the existing `calendar_rules.save_calendar_url(CLEAR_CALENDAR_URL)` writer
- The in-form `calendar_disconnect` checkbox is retired from `calendar_group()`'s own markup entirely; `submitted_calendar_signal()`'s checkbox-interpreting gates 1-3 are kept, with the decision to keep them recorded in that function's own docstring
- `companion/static/confirm-submit.js`: the ninth static script, wired through all six touch points of the duplicated-not-imported static-script contract, giving any `form[data-confirm]` a native `confirm()` misclick guard with no inline `<script>` anywhere
- `role="radiogroup"` + `aria-labelledby` on Theme's departures/arrivals chip grids and the Runway row, each pointing at its own group heading/label; every hint paragraph on the Settings page (LED, both quiet-hours time inputs, wake interval, display, calendar theme/URL, plus the two radiogroups) now carries an `id` an `aria-describedby` points at
- `_describedby_attr(*ids)` and a widened `_field_error_attrs(..., hint_id=None)` are the single builders of every `aria-describedby` value in the file, combining a hint id and an error id (hint first) rather than one overwriting the other
- Zero `<fieldset>`/`<legend>` elements added — all three of `companion/test_config_page.py`'s full-`render()` zero-`<fieldset>` pinned checks pass unmodified

## Task Commits

Each task was committed atomically:

1. **Task 1: Give calendar disconnect its own route, its own form, and a server-side confirmation step (D-08)** - `ba496a2` (fix)
2. **Task 2: Add the inline-free native confirm step (D-08, client half)** - `27ab912` (feat)
3. **Task 3: Expose the chip grids and the runway row as radiogroups, and link every hint (D-12)** - `648c6d3` (feat)

**Plan metadata:** committed as part of this SUMMARY's own commit (worktree mode — orchestrator handles STATE.md/ROADMAP.md centrally after merge)

## Files Created/Modified

- `companion/static/confirm-submit.js` (new) - intercepts submit on `form[data-confirm]`, shows one native `confirm()`, and on acceptance fills `[data-confirm-field]` with `data-confirm-value` before letting the submit proceed; documents plainly that this is a misclick guard, never a security control
- `companion/pages/config_page.py` - `CALENDAR_DISCONNECT_ROUTE`/`CALENDAR_DISCONNECT_CONFIRM_FIELD`/`_VALUE`/copy constants; `calendar_disconnect_section()`/`calendar_disconnect_confirm_page()` (new); `calendar_group()`'s in-form checkbox deleted; `render()` emits the disconnect form as a Device-scope-only sibling of the settings form; `submitted_calendar_signal()`'s docstring records the gates-1-3-kept decision; nine new `*_GROUP_HEADING_ID`/`*_SECTION_CAPTION_ID`/`*_HINT_ID` constants; `_describedby_attr()` (new); `_field_error_attrs()` widened with `hint_id=None`; `theme_fieldset()`/`runway_fieldset()`/`led_group()`/`quiet_hours_group()`/`wake_interval_group()`/`display_group()`/`calendar_group()` all updated to emit the new ids/ARIA attributes
- `companion/app.py` - `CALENDAR_DISCONNECT_ROUTE` rebind; `_handle_calendar_disconnect_post()` (new); `do_POST()` dispatch line; `CONFIRM_SUBMIT_SCRIPT_ROUTE`/`_CONFIRM_SUBMIT_JS_PATH`/`_serve_confirm_submit_script()`; `do_GET()` dispatch line
- `companion/layout.py` - `CONFIRM_SUBMIT_SCRIPT_SRC` constant; `page_shell()`'s script-tag format string and value tuple grew from eight to nine entries
- `companion/test_config_page.py` - Task 1: 1 check retargeted in place (checkbox-presence → checkbox-absence), 4 new checks (disconnect section shape/presence, confirm page, sibling-position, absence-when-not-configured). Task 3: 6 checks retargeted in place to tolerate the new `id="..."`/ARIA attributes (wake-interval/display caption literals, the runway-row opening tag, the settings-group-headings-named-once loop, the wake-interval aria-describedby check, the calendar-theme required-attribute regex), 3 new checks (Display ≥2/Device ≥1 radiogroups, every ARIA reference resolves with none empty across all three scopes, hint+error ids coexist in order). `EXPECTED_CHECK_COUNT` re-derived three times: 163 → 167 → 170
- `companion/test_companion_app.py` - Task 1: 4 new real-HTTP checks for the disconnect route (bare POST, confirm=maybe, confirm=yes, unauthenticated). Task 2: 3 new checks for confirm-submit.js (public-serving, ES5-safe/no-HTML-writing-sink, route/src agreement) plus 1 check retargeted in place (eight→nine deferred scripts). `EXPECTED_CHECK_COUNT` re-derived twice: 213 → 217 → 220

## Decisions Made

See `key-decisions` in the frontmatter above for the five load-bearing decisions (the standalone-form-not-descendant structural reason, keeping gates 1-3, the misclick-guard-only framing, the shared `extra_attr` seam reuse, and `_field_error_attrs()`'s signature-widening shape).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Worktree base drift required a `git reset --hard` before any work could begin**
- **Found during:** Setup, before Task 1
- **Issue:** The worktree's HEAD (`ddeb34e`) predated the phase's wave 1-4 merges; the expected base commit (`f58c634`) was not an ancestor of HEAD (`git merge-base` returned a much older common ancestor). Every file this plan needed to read/edit (calendar_group(), the six-touch-point static-script contract, the D-07 errors/submitted signature) was missing entirely at that HEAD.
- **Fix:** Per the mandatory worktree-branch-check protocol, verified HEAD was on the expected `worktree-agent-*` namespace (not a protected ref), confirmed the working tree was clean, then ran `git reset --hard f58c634` to correct the base — the documented, sanctioned recovery path for this exact situation.
- **Files modified:** None (git-level correction only).
- **Verification:** `git rev-parse HEAD` afterward matched `f58c634` exactly; all subsequently-read files matched the plan's own line-number references.
- **Committed in:** N/A (pre-work setup, not a code change)

---

**2. [Rule 1 - Bug] `misclick` appeared uppercase in confirm-submit.js's header comment, missing the plan's own required lowercase grep**

- **Found during:** Task 2
- **Issue:** The plan's acceptance criteria require `grep -c "misclick" companion/static/confirm-submit.js` to output at least 1 (case-sensitive). An early draft used "MISCLICK GUARD ONLY" in the header comment, which the lowercase grep does not match.
- **Fix:** Reworded to lowercase ("a misclick guard only") before the file was ever committed.
- **Files modified:** `companion/static/confirm-submit.js` (pre-commit).
- **Verification:** `grep -c "misclick" companion/static/confirm-submit.js` returns `1`.
- **Committed in:** `27ab912` (caught and fixed before this commit, not a separate commit)

---

**Total deviations:** 1 pre-work git-level correction (worktree base drift), 1 pre-commit self-catch (lowercase grep token). Neither affected the plan's actual scope or required a user decision.

## Issues Encountered

- The plan's Task 3 acceptance criterion `grep -c "<fieldset\|<legend" companion/pages/config_page.py` outputs `0` is unsatisfiable as literally stated: this file's docstrings have extensively discussed *why* it uses no `<fieldset>`/`<legend>` since well before this plan (06.6.3/06.6.4.1.1-05 and others), and those prose mentions alone give a non-zero grep count (24, unchanged by this plan's own edits — verified by diff). The SUBSTANTIVE requirement — zero `<fieldset>`/`<legend>` in the actual *rendered HTML* — is what the plan's own pinned harness checks (`"<fieldset" in rendered`) verify, and all three pass. No code or documentation was weakened to chase the literal grep count; this is noted here rather than silently treated as satisfied.

## User Setup Required

None — no external service configuration required.

## Self-Check: PASSED

- FOUND: companion/static/confirm-submit.js
- FOUND: companion/pages/config_page.py
- FOUND: companion/app.py
- FOUND: companion/layout.py
- FOUND: companion/test_config_page.py
- FOUND: companion/test_companion_app.py
- FOUND commit ba496a2
- FOUND commit 27ab912
- FOUND commit 648c6d3

## Next Phase Readiness

- A-26/D-08 is closed: disconnecting the calendar is a dedicated, confirmed, session-gated action; a bare or wrong-confirm POST erases nothing; a JS user gets one native `confirm()` (a misclick guard), a no-JS/CSP-blocked user gets the server's own two-step confirmation page
- A-30/D-12 is closed: the theme chip grids and the runway row announce as named radiogroups; every hint is programmatically linked to its control; hint and error ids coexist in one `aria-describedby` without either overwriting the other; zero new `<fieldset>`/`<legend>` elements
- `companion/test_config_page.py`: 170/170; `companion/test_view_pages.py`: 83/83; `companion/test_contrast_check.py`: 36/36; `companion/test_companion_app.py`: 218/220 (the two documented pre-existing root-sandbox WR-11 failures, unrelated to this plan, unchanged); `companion/test_status_pages.py`: 190/191 (the one documented pre-existing `anomaly_active()` root-sandbox failure, unrelated to this plan, unchanged)
- `PYTHON=$(command -v python3) bash scripts/run-all-tests.sh` reports exactly the three pre-existing-failure harnesses (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`) an untouched checkout also reports — no new failures
- The end-of-phase `<human-check>` (calendar disconnect button/confirm dialog/no-JS confirmation page; screen-reader announcement of the theme chips and runway cards as named radio groups with hints read alongside each control) is still outstanding — deferred to end-of-phase per the plan's own verification section
- No blockers for subsequent phase-19 plans

## Threat Flags

None — every new surface this plan introduces (the new `POST /settings/calendar/disconnect` route, the confirm field, `confirm-submit.js`'s DOM reads/writes) was already named in the plan's own `<threat_model>` (T-19-41, T-19-09, T-19-42, T-19-43, T-19-08, T-19-10, T-19-SC) and is covered by the harness checks above; no new network endpoint beyond the one explicitly planned, no new auth path, no new file-access pattern, no schema change.

---
*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Plan: 11*
*Completed: 2026-09-11*

## Self-Check: PASSED (re-verified)

- FOUND: companion/static/confirm-submit.js
- FOUND: companion/pages/config_page.py
- FOUND: companion/app.py
- FOUND: companion/layout.py
- FOUND: companion/test_config_page.py
- FOUND: companion/test_companion_app.py
- FOUND commit ba496a2 (fix(19-11): give calendar disconnect its own confirmed route)
- FOUND commit 27ab912 (feat(19-11): add confirm-submit.js, the inline-free native confirm step)
- FOUND commit 648c6d3 (feat(19-11): expose the chip grids and runway row as radiogroups)
