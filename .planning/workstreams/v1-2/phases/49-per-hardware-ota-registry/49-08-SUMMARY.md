---
phase: 49-per-hardware-ota-registry
plan: 08
subsystem: companion
tags: [update-page, hardware-type, chooser, i18n, golden]
requires: [49-03, 49-05]
provides:
  - Update page type chooser (shown only with more than one relevant type)
  - type-aware GET /update?type=<key> and POST install, cancel and confirm
  - one-type byte-identity golden for the Update page
affects: [49-09 and later]
key-files:
  created:
    - companion/testdata/update_page_one_type_golden.json
  modified:
    - companion/pages/update_page.py
    - companion/app.py
    - companion/routes.py
    - companion/i18n_fr/update.py
    - companion/static/style.css
    - companion/test_update_page.py
    - companion/test_update_actions.py
    - companion/test_browser_update.py
decisions:
  - "The chooser reuses the segmented control (.theme-form / .theme-option buttons, aria-pressed) as a GET form, so it needs no script and no new colour, size or motion"
  - "The hidden hardware_type field is also added when the single relevant type is not the legacy one, because a form without the field would act on the legacy type; with the legacy type alone nothing is added"
  - "An absent hardware_type field means legacy; a present but empty, malformed or unavailable value is rejected with the existing schedule-failed or cancel-failed flash and changes nothing"
  - "A GET type value is honoured only when the chooser is shown and names a relevant type; otherwise the legacy type (or the single relevant type) is shown"
  - "After an action on a non-legacy type the redirect and flash URLs carry ?type=; legacy redirects are unchanged"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [OTA-01]
---

# Phase 49 Plan 08: Per-type Update page Summary

The Update page can schedule and cancel per hardware type with an independent schedule per type, and with a single relevant type it renders byte for byte as before.

## Tasks

| Task | Commit | Notes |
|------|--------|-------|
| 1 golden | cd8a12eb | one-type render of 7 states x EN/FR plus the confirm page, captured from the unmodified code |
| 1 RED | 73a13381 | 14 per-type action tests failed first |
| 1 GREEN | 55a92c60 | resolve_type_choice, posted_type, chooser, type-aware handlers, EN/FR strings, one CSS rule |
| 2 | c3c2eb22 | browser tests: no chooser with one type, switching, independent scheduling, keyboard, overflow at 360/375/1280 px in EN and FR |

## Design-system notes

- Chooser markup is the existing segmented control. One CSS rule (`.update-type-chooser`) lets long type labels wrap instead of clipping and adds a card-gap margin; no new token, colour or animation.
- Strings: `update.hardware_type` ("Type de matériel") and `update.for_hardware_type_s` ("Pour %s"), both with French entries.

## Deviations from Plan

None that change behaviour. The golden is held as a function in `companion/test_update_page.py` (`one_type_golden_pages`) so the test and the fixture share one generator; it covers the page bodies and the confirm page rather than a full served shell.

## Known Stubs

None.

## Threat Flags

None. T-49-24 is mitigated: the posted type is checked against `hardware.available_types()` before any use, and `registry_path`'s own key check remains the second layer.

## Verification (run in this session)

- `pytest companion/test_browser_update.py test-support/test_i18n_ids.py companion/test_update_page.py companion/test_update_actions.py companion/test_suite_guards.py` with `SKYPANE_REQUIRE_BROWSER=1` and the scratchpad `PLAYWRIGHT_BROWSERS_PATH`: 272 passed
- `pytest server stub-server deploy/tests test-support companion -n auto --no-cov`, same env: 4560 passed, 8 skipped (root permission bits, one openssl limitation)
- `ruff check .`: clean; `mypy`: no issues in 16 source files
- `scripts/check_function_size.py check --max 80 server stub-server`: 595 functions, none over 80
- `scripts/check_comment_history.py check`: exit 0
- `./scripts/run-all-tests.sh` (coverage gate) was not run.

## Self-Check: PASSED

Commits cd8a12eb, 73a13381, 55a92c60 and c3c2eb22 exist; the golden and this file exist.
