---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 14
subsystem: ui
tags: [companion, ota, firmware, i18n, csrf, python]

# Dependency graph
requires:
  - phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
    provides: "server/firmware_registry.py's schedule_release/cancel_schedule/update_view (plan 01); companion/pages/update_page.py's read-side render() and per-row/Cancel form markup (plan 09)"
provides:
  - "POST /update/install: two-step server-side confirmation (the real D-04 gate) that schedules any published release at or above the floor, including a voluntary downgrade, via firmware_registry.schedule_release()"
  - "POST /update/cancel: cancels a scheduled release only while the device has not yet acknowledged the offer, via firmware_registry.cancel_schedule()"
  - "companion/pages/update_page.py's update_install_confirm_page(ctx, version, next_wake_text) and compute_next_wake_text(ctx), shared by the confirm page and the live GET render()"
  - "Two new flash keys (update_schedule_failed, update_cancel_failed) with English/French copy"
  - "Measured proof (not assumed) that the tab bar's More sheet still fits Health/Device/Update at 375px and 390px, English and French"
affects: [ota-08-close-out]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "The client-side data-confirm dialog never sets its own 'confirm' field -- the POST always lands on the server-rendered confirm page first, which is the only place that can actually schedule (companion/settings/calendar.py's calendar_disconnect_confirm_page() control-flow shape, reused verbatim)"
    - "A DOM el.click() inside page.evaluate() (not Playwright's pointer-based click) submits a form under scripts-blocked test conditions when a real pointer click would be legitimately refused for occluding fixed UI -- companion/test_browser_ux_helpers.py's own _SUBMIT_PROBE already established this technique; this plan's own test module documents and reuses it"

key-files:
  created:
    - companion/test_update_actions.py
    - companion/test_browser_update.py
  modified:
    - companion/app.py
    - companion/pages/update_page.py
    - companion/flash.py
    - companion/routes.py
    - companion/i18n_fr/update.py
    - companion/test_post_origin.py
    - test-support/companion_render_snapshot.py
    - companion/testdata/render_baseline.json
    - .planning/REQUIREMENTS.md

key-decisions:
  - "The plan's own text described route declarations and FLASH_MESSAGES as living in companion/app.py, matching an older main. On the current main (post-Phase-40 refactor) routes live in companion/routes.py's POST table and the flash vocabulary in companion/flash.py; both new routes/keys were added there instead, with companion/app.py gaining only the rebound route/flash-key constants and the two handler methods the plan asked for"
  - "The two new flash keys' literal strings and English Message text are declared in companion/pages/update_page.py (FLASH_UPDATE_SCHEDULE_FAILED/FLASH_UPDATE_CANCEL_FAILED), matching config_page.py's/airlines_page.py's own established FLASH_* ownership pattern -- companion/flash.py imports and re-exports them rather than declaring the literals itself"
  - "D-02's mobile-fit gate is measured at literal 375x812/390x844 viewports (42-UI-SPEC.md's own executor checklist), not companion/test_browser_ux_helpers.py's shared VIEWPORT_MIN_SUPPORTED constant (360px) -- a different, narrower viewport that would not have proven what the UI-SPEC asked for"
  - "The row-level Install form's data-confirm attribute carries no data-confirm-field/data-confirm-value pair, so accepting the native confirm() dialog submits the form with no 'confirm' field at all and still lands on the server confirm page -- confirmed against companion/static/confirm-submit.js's own documented contract rather than assumed"

requirements-completed: [OTA-08]

coverage:
  - id: D1
    description: "POST /update/install without confirm=yes renders the server-side confirmation page at 200 without touching the registry, naming the version and the next wake time; works identically with or without JavaScript"
    requirement: "OTA-08"
    verification:
      - kind: unit
        ref: "companion/test_update_actions.py::test_install_without_confirm_renders_confirm_page_registry_unchanged, ::test_install_confirm_page_offers_a_plain_cancel_link_not_a_second_form"
        status: pass
      - kind: e2e
        ref: "companion/test_browser_update.py::test_js_confirm_accept_lands_on_server_confirm_page_then_schedules, ::test_no_js_install_goes_straight_to_confirm_page_and_completes"
        status: pass
    human_judgment: false
  - id: D2
    description: "POST /update/install with confirm=yes schedules through firmware_registry.schedule_release and redirects to /update; a release older than the running version schedules with no special downgrade wording; every rejection (unknown, below floor, same as running, busy) flashes a generic failure and leaves the registry untouched; an implausible version value is never echoed unescaped"
    requirement: "OTA-08"
    verification:
      - kind: unit
        ref: "companion/test_update_actions.py -- test_install_confirm_yes_schedules_and_get_shows_scheduled, test_install_confirm_yes_downgrade_reads_the_same_as_any_other_install, test_install_confirm_yes_unknown_version_flashes_failure, test_install_confirm_yes_below_floor_flashes_failure, test_install_confirm_yes_same_as_running_flashes_failure, test_install_confirm_yes_while_busy_flashes_failure_original_schedule_unchanged, test_install_implausible_version_treated_as_unknown_never_echoed"
        status: pass
    human_judgment: false
  - id: D3
    description: "POST /update/cancel cancels only while no offer has been served for the schedule; once acknowledged, cancelling changes nothing and flashes the honest failure message"
    requirement: "OTA-08"
    verification:
      - kind: unit
        ref: "companion/test_update_actions.py -- test_cancel_with_no_offered_event_redirects_and_clears_schedule, test_cancel_with_nothing_scheduled_is_a_no_op_redirect, test_cancel_after_offered_event_flashes_failure_schedule_unchanged"
        status: pass
      - kind: e2e
        ref: "companion/test_browser_update.py::test_full_flow_install_then_scheduled_then_cancel_returns_to_available"
        status: pass
    human_judgment: false
  - id: D4
    description: "Both routes sit behind the existing session and Origin/Sec-Fetch-Site gate; French renders the confirm page and both new flash messages"
    requirement: "OTA-08"
    verification:
      - kind: unit
        ref: "companion/test_update_actions.py -- test_both_routes_without_a_session_redirect_to_login, test_confirm_page_renders_in_french, test_schedule_failed_flash_renders_in_french; companion/test_post_origin.py's parametrized cross-origin sweep (now covering both routes)"
        status: pass
    human_judgment: false
  - id: D5
    description: "At 375px and 390px, English and French, the tab bar's More sheet shows Health, Device and Update, each at least 44px tall, without wrapping or truncation, the More summary cell's own box unchanged, and no /update link in the header dropdown; the >=960px sidebar Advanced group shows three links with no overlap"
    requirement: "OTA-08"
    verification:
      - kind: e2e
        ref: "companion/test_browser_update.py::test_more_sheet_fits_health_device_update_at_phone_widths[375/390 x en/fr], ::test_desktop_sidebar_advanced_group_fits_with_no_overlap"
        status: pass
    human_judgment: false

# Metrics
duration: ~90min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 14: Update page Install/Cancel actions Summary

**POST /update/install (two-step server-side confirm, any release at or above the floor including a downgrade) and POST /update/cancel (cancellable only until acknowledged), completing OTA-08 with a measured 375px/390px/en/fr mobile-fit proof.**

## Performance

- **Duration:** ~90 min
- **Completed:** 2026-09-28
- **Tasks:** 2/2
- **Files modified:** 11 (2 created, 9 modified)

## Accomplishments

- `companion/app.py` gained `_handle_update_install_post()` and `_handle_update_cancel_post()`: the install handler validates `version` against `firmware_registry.VERSION_RE`/`VERSION_MAX_LEN` before anything renders it, renders the server-side confirm page when `confirm` is not exactly `"yes"`, then calls `schedule_release()` with the running version read from `update_view()`; the cancel handler calls `cancel_schedule()` and flashes the honest "the frame may have already started" message only on `"not_cancellable"`
- `companion/pages/update_page.py` gained `update_install_confirm_page(ctx, version, next_wake_text)` (byte-for-byte the same control-flow shape as `calendar_disconnect_confirm_page()`) and `compute_next_wake_text(ctx)`, now shared by both the confirm page and the live `GET /update` render
- Two new flash keys with English/French copy: "Couldn't schedule that update — please try again." and "Couldn't cancel — the frame may have already started."
- `companion/test_update_actions.py`: 17 plain-request tests covering every `<behavior>` case in the plan — no-confirm render, confirm=yes scheduling (including a downgrade with no special wording), every registry rejection (unknown/below-floor/same-as-running/busy), an implausible version value never echoed, both routes' session gate, and French rendering
- `companion/test_browser_update.py`: 9 real-Playwright tests — the JS `data-confirm` misclick guard (accept lands on the server confirm page, dismiss sends no request), the no-JS-safe straight-to-confirm-page flow, the full install→scheduled→cancel round trip, and the D-02 mobile-fit gate measured at 375px/390px in both languages plus the >=960px sidebar
- OTA-08 marked Complete in `.planning/REQUIREMENTS.md`

## Task Commits

Each task was committed atomically:

1. **Task 1: Install (two-step confirm) and Cancel POST handlers** - `3f428fb8` (feat)
2. **Task 2: Browser tests — JS confirm, full flow, and the mobile-fit gate** - `ba0587ed` (test)

**Plan metadata:** committed as part of this final docs commit (STATE.md/ROADMAP.md/REQUIREMENTS.md).

_Note: both tasks used `tdd="true"`; tests and implementation were authored and verified together against the plan's `<behavior>` contract rather than via two separately-committed RED/GREEN passes, matching 42-01's and 42-09's own documented precedent for this phase._

## Files Created/Modified

- `companion/app.py` — `_handle_update_install_post()`, `_handle_update_cancel_post()`, the rebound `UPDATE_INSTALL_ROUTE`/`UPDATE_CANCEL_ROUTE`/`FLASH_KEY_UPDATE_*` constants, `update_page`/`firmware_registry` imports
- `companion/pages/update_page.py` — `update_install_confirm_page()`, `compute_next_wake_text()`, the two new flash-key literals and their Message text, `render()` simplified to call the shared helper
- `companion/flash.py` — re-exports the two new flash keys from `update_page.py`, adds them to `FLASH_MESSAGES`/`FLASH_ROLES`
- `companion/routes.py` — the two new POST route declarations (session-required)
- `companion/i18n_fr/update.py` — French forms for the confirm heading/sentence and both flash messages
- `companion/test_update_actions.py` — 17 plain-request behaviour tests (new file)
- `companion/test_browser_update.py` — 9 real-browser tests (new file)
- `companion/test_post_origin.py` — the two new routes added to the parametrized cross-origin sweep
- `test-support/companion_render_snapshot.py` — the two new routes added to `_UNAUTH_POST_REQUESTS`
- `companion/testdata/render_baseline.json` — regenerated; diffed programmatically to confirm the only change is the two new `"unauthenticated"` entries (both `303` to `/login`)
- `.planning/REQUIREMENTS.md` — OTA-08 marked Complete

## Decisions Made

- Route declarations and the flash vocabulary now live in `companion/routes.py`/`companion/flash.py` (Phase 40's refactor), not `companion/app.py` directly as the plan's own text described from an older `main` — `companion/app.py` still gained the handler methods and rebound constants the plan asked for, matching every existing sibling route's shape
- The two new flash keys' literal strings and English text are owned by `companion/pages/update_page.py` (matching `config_page.py`'s/`airlines_page.py`'s own `FLASH_*` pattern), not declared inline in `companion/flash.py`
- D-02's mobile-fit gate is measured at the literal 375×812/390×844 viewports 42-UI-SPEC.md's own checklist names, not `companion/test_browser_ux_helpers.py`'s shared `VIEWPORT_MIN_SUPPORTED` (360px) — a different, narrower viewport that would not have proven the UI-SPEC's own stated claim
- Line-wrap detection in the mobile-fit browser test reads the rendered text's own line boxes via `Range.getClientRects()`, not `clientHeight / line-height` — the 44px tap target's vertical padding makes that ratio read "2 lines" for a genuinely single line of text

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Route table and flash vocabulary live in different modules than the plan's action text described**
- **Found during:** Task 1, re-reading `companion/app.py` on current `main` per the plan's own instruction
- **Issue:** The plan's action text says to add route table entries and `FLASH_MESSAGES` entries "in app.py" — true on the `main` the plan's interfaces block was written against, but Phase 40's refactor (already merged) moved POST route declarations into `companion/routes.py`'s table and the flash vocabulary into `companion/flash.py`
- **Fix:** Added the two `Route(...)` entries to `companion/routes.py`'s `_POST_ROUTES`, and the two flash keys/messages/roles to `companion/flash.py`'s tables, re-exported from there under the `FLASH_KEY_*` names `companion/app.py` already rebinds every other flash key under
- **Files modified:** `companion/routes.py`, `companion/flash.py` (plus `companion/app.py`'s handler methods per the plan)
- **Verification:** `companion/test_route_table.py`'s table-driven auth-coverage test picks up both new routes automatically (it iterates `routes.ROUTES`, never a hand-kept list) and passes; the full companion suite is green
- **Committed in:** `3f428fb8` (Task 1 commit)

**2. [Rule 3 - Blocking] Committed render-baseline fixture and two route-list guards needed the two new routes**
- **Found during:** Task 1's full-suite verification (`pytest -q companion -m "not browser"`)
- **Issue:** `companion/test_route_table.py::test_every_gated_route_redirects_an_anonymous_request` and `companion/test_render_baseline.py::test_unauthenticated_responses_match_the_baseline` both index the committed `companion/testdata/render_baseline.json`'s `"unauthenticated"` map by every route in `routes.ROUTES` — the two new routes had no entry yet and failed with `KeyError`/a key-set mismatch. `test-support/companion_render_snapshot.py`'s own `_UNAUTH_POST_REQUESTS` list (which the baseline is generated from) also did not yet name the new routes.
- **Fix:** Added `UPDATE_INSTALL_ROUTE`/`UPDATE_CANCEL_ROUTE` to `_UNAUTH_POST_REQUESTS`, regenerated `render_baseline.json` via the module's own `--write` mode, and diffed the result programmatically against the prior committed version to confirm the only change is the two new `"unauthenticated"` entries (both `303 /login`, matching every other gated POST route) — no other baseline entry changed
- **Files modified:** `test-support/companion_render_snapshot.py`, `companion/testdata/render_baseline.json`
- **Verification:** `pytest -q companion -m "not browser"` green; programmatic diff confirmed no unrelated baseline drift
- **Committed in:** `3f428fb8` (Task 1 commit)

**3. [Rule 1 - Bug] `companion/test_post_origin.py`'s own hand-kept exact-route list did not name the two new routes**
- **Found during:** Task 1, re-reading `companion/test_post_origin.py` per the plan's own `<read_first>` instruction
- **Issue:** `_EXACT_POST_ROUTES` is a hand-kept tuple this module's own docstring says "a route added there later needs a line added here too" — the origin/session gate itself already covers new routes regardless (proven by the module's own `test_cross_site_origin_rejected_before_routing_on_unknown_path`), but leaving this list stale would silently drop the two new routes from that module's parametrized coverage
- **Fix:** Added `app.UPDATE_INSTALL_ROUTE`/`app.UPDATE_CANCEL_ROUTE` to `_EXACT_POST_ROUTES`
- **Files modified:** `companion/test_post_origin.py`
- **Verification:** `pytest -q companion/test_post_origin.py` green, both new routes now included in the parametrized cross-site sweep
- **Committed in:** `3f428fb8` (Task 1 commit)

**4. [Rule 3 - Blocking] Two stale forward-reference comments ("a later plan's own route") failed the comment-history check's spirit and were simply inaccurate now that the routes are live**
- **Found during:** Task 1, `scripts/check_comment_history.py check` and a manual re-read for staleness
- **Issue:** `companion/pages/update_page.py`'s route-constant comment and `companion/app.py`'s `_PAGE_SCRIPTS[UPDATE_ROUTE]` comment both described the Install/Cancel routes as not-yet-implemented, written by plan 09 before this plan existed
- **Fix:** Reworded both to describe the code as it now is (per this plan's own project rules instruction), with no decision/plan ID introduced
- **Files modified:** `companion/pages/update_page.py`, `companion/app.py`
- **Verification:** `scripts/check_comment_history.py check` exits 0 with no findings
- **Committed in:** `3f428fb8` (Task 1 commit)

**5. [Rule 1 - Bug] The no-JS Install-form click failed under Playwright's real pointer-based click at 390px**
- **Found during:** Task 2, first run of the no-JS browser test
- **Issue:** With `java_script_enabled=False`, `companion/static/nav-dropdown.js` never collapses the header's fallback preferences panel, which stays in normal document flow and pushes the page ~190px taller — enough that the row-level Install button's real screen position sits under the fixed bottom tab bar. Playwright's pointer-based `.click()` correctly refuses to punch through an occluding element and times out.
- **Fix:** Submitted the form via a DOM `el.click()` executed inside `page.evaluate()` (which runs over CDP, unaffected by `java_script_enabled=False`, unlike a page `<script>`) — the identical technique `companion/test_browser_ux_helpers.py`'s own `_SUBMIT_PROBE` already uses for every other no-JS form submission in this suite
- **Files modified:** `companion/test_browser_update.py`
- **Verification:** the no-JS test passes reliably; the occlusion itself is a genuine, pre-existing characteristic of the no-JS fallback nav unrelated to anything this plan built, so it was not "fixed" as a layout defect
- **Committed in:** `ba0587ed` (Task 2 commit)

**6. [Rule 1 - Bug] Line-wrap detection using `clientHeight / line-height` false-positived on every More-sheet link**
- **Found during:** Task 2, first run of the mobile-fit browser test
- **Issue:** The initial probe divided the link's full `clientHeight` (44px, including the tap-target's own vertical padding) by its computed `line-height` (~22px), reading "2 lines" for text that renders on exactly one line
- **Fix:** Rewrote the probe to count the rendered text's own line boxes via `Range.getClientRects()` (one rect per line, deduplicated by rounded `top`), which is insensitive to padding
- **Files modified:** `companion/test_browser_update.py`
- **Verification:** all four mobile-fit parametrizations (375/390 × en/fr) pass with real, non-vacuous truncation/wrap assertions
- **Committed in:** `ba0587ed` (Task 2 commit)

---

**Total deviations:** 6 auto-fixed (4 Rule 3 blocking, 2 Rule 1 bug), all required by the plan's own stated verification commands and acceptance criteria, all discovered by re-reading current `main` and running real tests rather than assumed. No scope creep beyond what the plan's own `<behavior>`/`<acceptance_criteria>` already specified.

## Issues Encountered

None beyond the six auto-fixed items above.

## User Setup Required

None — no external service configuration required. This plan is companion-only and touches no deployment or secrets configuration.

## Next Phase Readiness

- OTA-08 is now fully satisfied end to end: the read side (plan 09) and the write side (this plan) together cover every clause in `.planning/REQUIREMENTS.md`'s OTA-08 line, and REQUIREMENTS.md marks it Complete
- No blockers for any later phase-42 plan; the Update page's Install/Cancel actions are live and tested with and without JavaScript

---

*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: companion/test_update_actions.py
- FOUND: companion/test_browser_update.py
- FOUND: companion/pages/update_page.py
- FOUND: .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-14-SUMMARY.md
- FOUND: 3f428fb8 (feat: Install/Cancel POST handlers with server-side confirm)
- FOUND: ba0587ed (test: JS confirm guard, no-JS flow and D-02 mobile fit)
