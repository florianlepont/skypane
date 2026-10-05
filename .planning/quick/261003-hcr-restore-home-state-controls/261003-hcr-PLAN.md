---
phase: quick
plan: 261003-hcr
type: execute
autonomous: true
files_modified:
  - companion/pages/home_page.py
  - companion/static/style.css
  - companion/static/freshness.js
  - companion/ui_nav.py
  - companion/i18n_fr/home.py
  - companion/pages/history_page.py
  - companion/static/panel-lookup.js
  - companion/i18n_fr/flights.py
---

# Quick 261003-hcr: restore the frame state and its controls on Home

## Problem

The owner reports the new Home has no buttons to turn the screen on or manage
quiet hours, and no frame state. Their Phase 44 feedback asked to MERGE the
duplicated screen and quiet-hours cards into one clear current state, not to
delete the controls. The Frame strip was removed instead, leaving
`/quick/display` and `quick-switch.js` orphaned.

## Tasks

1. Home gets ONE merged "frame state" card below the image + recent flights
   hierarchy: plain-language state (screen on / quiet hours until HH:MM /
   screen off / battery resting), next update, one cadence sentence, and two
   native POST buttons (screen on/off via `/quick/display`, quiet hours on/off
   via `/quick/quiet-hours`) that redirect back to Home with the existing flash.
   All derived from PageContext via `wake.next_wake_status` /
   `wake.effective_wake_interval_s` (battery-critical and display-off
   precedence preserved). 44px targets, visible focus.
2. Home auto-refresh: hidden `data-loaded-at` marker (`refresh_marker_html`),
   `.page-header__freshness` and the new card added to the Home swap registry
   in `ui_nav.py` and mirrored in `freshness.js`.
3. Remove the Flights lightbox disclaimer (markup/JS) and its two orphaned
   i18n keys; keep the picture caption.
4. Tests: served-HTML behaviour tests, POST persistence + flash, EN/FR,
   real-browser test at 1280/390/360 with keyboard and no-JS; retarget retired
   contracts; regenerate render baseline after inspecting the diff.

## Verification

Full `./scripts/run-all-tests.sh`, ruff, mypy, comment-history guard and the
function-size gate all green.
