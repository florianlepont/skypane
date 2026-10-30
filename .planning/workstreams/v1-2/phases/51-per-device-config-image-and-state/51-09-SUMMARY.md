---
phase: 51-per-device-config-image-and-state
plan: 09
subsystem: companion
tags: [device-selector, ui, no-js, i18n, browser-tests]
requires: [51-06]
provides:
  - Device selector in page_shell (several devices only), device name in the document title
  - No-script switch redirect (`?device=`) validated against the fleet
  - Selector layout CSS and change handler in the existing nav script
affects: [51-10 baselines]
key-files:
  created: [companion/test_device_selector.py, companion/test_browser_device_selector.py]
  modified: [companion/ui_shell.py, companion/device_scope.py, companion/app.py, companion/i18n_fr/nav.py, companion/static/style.css, companion/static/nav-dropdown.js]
requirements-completed: []
completed: 2026-10-30
---

# Phase 51 Plan 09: Device selector Summary

A labelled native select in a GET form sits above the page title of every device-scoped page when the fleet has more than one device, works without script, and is armed (submit hidden, change navigates) by the existing nav script. FLT-01 / FLT-02 are intentionally NOT marked complete.

## Commits
- 94ffec6 feat(51-09): device selector markup, device title and no-script switch redirect
- 5f049e3 feat(51-09): device selector layout, change handler and browser tests

## What changed
- `ui_shell.device_selector_html(active)`: `<div role="group" aria-labelledby>` around an unnamed `<form method="get">`, label, `<select name="device">`, a base (not accent) submit, and a neutral `.banner__pill` for the selected non-live device when never seen or offline. Live frame first (value `live`), then by name/id; non-live options get ` — not seen yet` / ` — offline`; each option has a server-built `data-href`. Everything dynamic goes through `escape_html`. The template slot sits directly before `{flash}`, so one device yields byte-identical HTML (render baseline passes, `companion/testdata` untouched).
- `device_scope.switch_target` and a short hook in `_dispatch_for_device` (after the session gate, GET device-scoped pages only): valid id or `live` gives a 303 to the same page under that device, other query parameters kept; unknown or malformed value is a 404. The location is built from the matched route path plus a validated id.
- `nav-dropdown.js`: change handler and `device-selector--armed` class, attached before the mobile-toggle early return.
- `style.css`: 48 lines, no custom property, no `@keyframes`, no accent.
- French strings in `i18n_fr/nav.py` (7 keys, Message declarations in `ui_shell.py`).

## Verification
- `pytest companion/test_device_selector.py` 35 passed; browser tests 10 passed (Chromium, scripts blocked and armed, 360/1280px, both themes, hit areas, focus outline).
- `test_render_baseline`, `test_status_pages_01`, `test_i18n`, `test_structure_guards`, `test-support/test_i18n_ids`, `test_stylesheet_structure`, `test_contrast_check`, `test_page_scripts`, device dispatch/route tests pass. Full `companion` run: 2362 passed, 550 browser-launch errors under `-n 4` (Chromium target closed in this sandbox under parallelism, no FAILED); the browser files I re-ran serially pass.
- ruff clean on my files (`companion/test_device_links.py` from another plan has one ruff finding), mypy clean, comment-history and function-size gates pass.

## Deviations from Plan
- [Rule 3] Document title keeps the existing " - " separator (`Flights - sim-1 - SkyPane`), not the em dash written in the UI-SPEC, because the plan says "with the existing separator" and the shell template uses it.
- [Rule 3] The sandbox Chromium is build 1243 while Playwright wants 1248; I ran the browser tests through a symlinked browsers directory in the scratchpad (no repo change). `/opt/pw-browsers/chromium` exists.
- The no-script submit has `min-height: 44px` (UI-SPEC layout), rather than the 30px base button height.
- A scripts-blocked page cannot use `page.evaluate`, so that browser test measures boxes directly.

## Known Stubs
None.

## Threat Flags
None beyond the plan's threat model (T-51-36..39 mitigated and tested: open-redirect payloads, escaped names/title, no MAC/token/secret, switch behind the session gate).

## Self-Check: PASSED
