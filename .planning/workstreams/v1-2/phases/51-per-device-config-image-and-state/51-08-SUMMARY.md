---
phase: 51-per-device-config-image-and-state
plan: 08
subsystem: companion
tags: [device-scope, links, forms, freshness]
requires: ["51-06", "51-07"]
provides:
  - prefix-aware emitters for nav, quick switches, flash actions, LED form, airlines, resolve dialog, calendar sheet, previews
affects: [51-10, 51-11, 51-12, 51-13]
key-files:
  modified:
    - companion/ui_nav.py
    - companion/ui_components.py
    - companion/flash.py
    - companion/settings/runway_led.py
    - companion/settings/calendar.py
    - companion/pages/airlines_page.py
    - companion/pages/airline_sheet.py
    - companion/resolve_dialog.py
    - companion/theme_preview.py
    - companion/flight_card.py
    - companion/static/freshness.js
    - companion/test_status_pages_04.py
  created:
    - companion/test_device_links.py
key-decisions:
  - "Every emitter calls device_scope.scoped at the point it writes a URL; no HTML rewriting"
  - "return_to / return hidden values stay un-prefixed (handlers re-prefix and whitelist)"
  - "Health nav-dot swap selector became a[href$=\"/health\"] in both ui_nav.py and freshness.js"
requirements-completed: []
duration: ~40min
completed: 2026-10-30
---

# Phase 51 Plan 08: Prefix-aware links and forms Summary

Pages under /devices/<id>/ keep every nav link, quick switch, flash action, LED form, airline/illustration URL, calendar sheet action and frame-preview URL inside that device through the single `device_scope.scoped` helper; the Update link and the live frame's un-prefixed output are unchanged.

## Commits
- c2e05f6: nav, quick switches, flash actions, LED form
- 7e5d283: airlines, airline sheet, resolve dialog, calendar sheet, previews, freshness selector

## Results
- `companion/test_device_links.py`: 26 tests pass (nav prefix incl. sidebar and tab-bar More sheet, Update never prefixed, active state, quick-switch action and plain return_to, flash undo/link/dismiss, LED action, airlines/resolve/rename/delete/upload URLs, calendar sheet actions and close links, frame preview 200 under the prefix, freshness script, un-prefixed pages carry no /devices/ URL outside the device selector).
- Plan verify set plus test_status_pages_04, suite and structure guards: 406 passed, 5 skipped (Chromium not installed here, root-permission test).
- ruff, mypy, check_comment_history, check_function_size (max 80), stub-server image negotiation and phase-47 freeze tests: clean. `git diff --stat companion/testdata` empty; baseline test passes unchanged.

## Deviations from Plan

1. **[Rule 3] Deliberate pin update**: `companion/test_status_pages_04.py` pinned the Health swap selector as `a[href="/health"]`; updated to `a[href$="/health"]` together with `ui_nav.py` and `freshness.js` (the refresh URL already was `window.location.href`, so no change needed there).
2. **Un-prefixed "no /devices/ substring" assertion narrowed**: plan 51-09 added a device selector to the shell that legitimately links to other devices; the test ignores URLs inside `.device-selector` and asserts none elsewhere.
3. `companion/flight_card.py` carried an uncommitted edit (scoped illustration URL) from a parallel executor, identical to this plan's intent; it was committed in 7e5d283.
4. Quick switches are rendered on Home (not Display), so the quick-switch test loads `/devices/<id>/`.

## Known gaps (owned by other plans)
- The Display page's `/settings` form action and the Health page's resolve dialog are not rendered prefixed/covered here (display-settings and health emitters belong to plans 10/11). On the seeded fixture the Health page rendered no resolve dialog, so the dialog's prefixing is asserted on the Airlines page and via an in-process `step_b_trigger_html` test.
- Browser check of the dynamic freshness behaviour is for the final plan (no Chromium here).

## Threat Flags
None.

## Self-Check: PASSED
