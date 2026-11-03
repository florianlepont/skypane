---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 14
subsystem: companion
tags: [navigation, console]
requires: [61-05]
provides: [console pages without the section chip row]
key-files:
  modified:
    - companion/console_routes.py
    - companion/app.py
    - companion/pages/update_page.py
    - companion/test_console_shell.py
    - companion/test_browser_console_shell.py
    - companion/test_console_audit_page.py
    - companion/test_browser_console.py
    - companion/testdata/render_baseline.json
    - companion/testdata/update_page_one_type_golden.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 14: Remove Console section chip rows Summary

section_subnav_html and both call sites (console page shell, Update page) are removed; no Console page renders a second navigation row. Audit filter chips are untouched. Route access rows are unchanged.

## Commit

- Single atomic commit for both tasks (code and test updates must land together to stay green).

## Deviations from Plan

**[Rule 1 - Test fallout] Extra files updated:**
- `test_console_audit_page.py::test_the_page_is_read_only` split the page on the first `filter-bar__chips` occurrence, which only worked because the section chip row was the first; it now bounds the check to `<main>`.
- `test_browser_console.py` colour/motion test relied on the Update page's chip row to make the chip-box transition "already used"; its probe now also adds a shared `filter-chip` to the reference page.
- `render_baseline.json` and `update_page_one_type_golden.json` regenerated deliberately (diff is only the removed chip row).
- test_console_fleet_page.py and test_console_users.py had no chip-row expectations; unchanged.
- `.section-subnav` CSS rules and `SECTION_NAV_LABEL` left in place (stylesheet owned by 61-04).

## Gates
ruff, mypy, comment-history, function-size, phase47 freeze all clean; companion + test-support suite 5733 passed, 3 skipped (root-permission tests only).

## Self-Check: PASSED
