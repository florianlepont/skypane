---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 15
subsystem: companion
tags: [device, health, empty-state, css]
requires: [61-01, 61-07, 61-09, 61-14]
provides: [LED switch without accent box, single no-check-in statement, compact empty states]
key-files:
  created:
    - companion/test_browser_device_led_switch.py
    - companion/test_health_connection_row.py
    - companion/test_empty_state_scale.py
    - companion/test_browser_empty_state_scale.py
  modified:
    - companion/static/style.css
    - companion/pages/health_page.py
    - companion/pages/home_page.py
    - companion/pages/audit_page.py
    - companion/pages/locations_page.py
    - companion/pages/update_page.py
    - companion/health_sections.py
    - companion/test_user_health.py
    - companion/test_status_pages_02.py
    - companion/testdata/render_baseline.json
    - companion/testdata/update_page_one_type_golden.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 15: Three audit items Summary

Closes ledger rows A, B and C.

## Commits

- f998547: LED switch box (A)
- bc2fafd: Health connection row (B)
- f26d4f2: compact empty states (C)

## What changed

- **A, root cause.** The Diagnostic LED switch is a `button[type=submit]`; that rule (0,1,1: accent fill and shadow) outranked the single-class `.switch` rule (0,1,0), so the button painted an accent box behind its track (Home's switch was already neutralised by `.home-switch .switch`). The rule is now `button.switch` (and its hover/active), plus `box-shadow: none`. The global focus-visible ring is untouched; a browser test checks it on keyboard focus. The browser test measures the button background, outline, border and shadow in both themes, EN/FR, 360 and 1280 px, plus click toggling.
- **B.** With no check-in on record, `_connection_row` renders an empty value cell and no Last check-in fact; the verdict ("Has not checked in for a while") says it once. Rows with a check-in are unchanged.
- **C.** `compact=True` on the Home no-panel and no-flights blocks, Health device-empty page and no-gaps section, Audit no-events, Locations and Update. Co-managers card, Fleet and the battery rows were already compact. The Audit filtered-no-result block is untouched (still `empty-state--filter`). New CSS: `.status-page > .empty-state--compact, .page-content > .empty-state--compact` get `var(--space-md)` padding.

## Deviations from Plan

1. **Files outside the frontmatter:** `companion/test_user_health.py` (its fresh-install Health assertion expected the Last check-in fact; it now seeds a check-in), `companion/test_status_pages_02.py` (the Health test asserting the Unresolved-prefixes empty state keeps the large form was inverted and renamed `test_health_empty_states_are_all_compact`), `companion/testdata/update_page_one_type_golden.json` (only the two `no_releases` entries moved) and `companion/testdata/render_baseline.json` (empty-state bodies only). All updated deliberately.
2. **Task 1 selector.** The plan expected a focus or hover shadow; measurement showed it was the submit-button fill. `button.switch` is slightly broader than "LED region only" but fixes the same defect for every quick switch.
3. Plan 61-15 listed `co_managers_card.py`: already compact, no change.

## Not done / for the orchestrator

Large-form empty states remain on pages outside the plan's list: `history_page.py` (two), `detection_page.py` (three), `account_page.py` (My frames), and the table fallback `ui_components.py:814`. The plan did not list them; converting them would move more pinned renders.

## Known Stubs

None.

## Gates

ruff, mypy (28 modules), comment history, function size (922 functions, none over 80), Phase 47 freeze (21 passed) clean. Companion plus test-support with `-n auto`: 5988 passed, 3 skipped (root-permission tests only, no browser skips).

## Self-Check: PASSED
