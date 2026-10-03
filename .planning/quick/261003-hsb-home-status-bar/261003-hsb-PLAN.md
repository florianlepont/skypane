---
phase: quick
plan: 261003-hsb
type: execute
autonomous: true
files_modified:
  - companion/pages/home_page.py
  - companion/static/style.css
  - companion/ui_nav.py
  - companion/static/freshness.js
  - companion/i18n_fr/home.py
---

# Quick 261003-hsb: Home status header with real switches

## Problem

The "Frame state" card from 261003-hcr is plain and sits at the bottom of
Home; the owner expected it at the top, more modern, and misses the on/off
switches the old Frame strip had.

## Tasks

1. Replace the bottom card and the lone battery chip with ONE status header
   directly under the page title: coloured-dot headline (same precedence),
   next-update line, battery pill with a small meter, muted cadence help text,
   and two `role="switch"` controls (Screen, Quiet hours + its window) built
   from the shared `quick_switch_html` (native POST forms, work without JS).
   The switch region does not opt into quick-switch.js's optimistic flip, so a
   press is a full redirect with the flash and the headline is never stale.
   Desktop: status left, switches right. Mobile: stacked, 44px+ targets.
2. Home refresh registry: `.home-facts` keeps only the actionable-warning link.
3. Tests: retarget state-card and browser tests, add switch semantics tests
   (role, aria-checked, POST, flash, no-JS, Space/Enter, EN/FR).
4. Screenshots at 1280/390/360, light and dark, three states; iterate.

## Verification

Full `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`, ruff, mypy,
comment-history guard and function-size gate all green.
