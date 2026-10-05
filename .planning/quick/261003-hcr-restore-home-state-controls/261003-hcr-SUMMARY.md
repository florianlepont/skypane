---
phase: quick
plan: 261003-hcr
subsystem: companion
tags: [home, frame-state, quick-actions, freshness, i18n, lightbox]
requires: []
provides:
  - "One merged frame-state card on Home (state, next update, cadence sentence, screen and quiet-hours POST buttons)"
  - "Home background refresh restored through the silent data-loaded-at marker"
  - "Flights picture lightbox without the nearest-render / nominal-colours disclaimer"
affects: [companion/pages/home_page.py, companion/ui_nav.py, companion/static/freshness.js]
key-files:
  created:
    - companion/test_home_state_card.py
    - companion/test_browser_home_state_card.py
  modified:
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/static/freshness.js
    - companion/ui_nav.py
    - companion/i18n_fr/home.py
    - companion/i18n_fr/flights.py
    - companion/pages/history_page.py
    - companion/static/panel-lookup.js
    - companion/testdata/render_baseline.json
decisions:
  - "Reuse /quick/display and /quick/quiet-hours unchanged; no new route"
  - "Plain forms without data-quick-switch, so Home does a full redirect and shows the existing flash (no optimistic JS)"
  - "Quiet-hours 'pause/resume' is the existing quiet_hours_enabled flag; buttons read 'Turn quiet hours on/off' to match the existing flash wording"
metrics:
  completed: 2026-10-03
---

# Quick 261003-hcr: Home frame state and controls restored

The owner lost the screen and quiet-hours buttons and the frame state when
Phase 44 removed the Frame strip instead of merging its two cards. Home now has
ONE card below the picture + recent-flights row.

## What the card shows and does

- Headline in plain language, resolved with the precedence of
  `wake.effective_wake_interval_s`: battery empty ("Battery very low ...") >
  screen off > in quiet hours ("... the screen rests until HH:MM") > screen on.
- "Next update ≈ HH:MM · in 5m" from `wake.next_wake_status` and the shared
  `frame_state` due/held/late wording (omitted when the frame never checked in).
- The quiet-hours schedule line (on with window / turned off).
- ONE cadence sentence naming the effective interval ("... wakes about every 15
  min, so it does not refresh continuously"); the interval follows the same
  precedence (battery hold, screen-off cadence, configured interval).
- Two native POST forms, 44px minimum height, visible focus, full width under
  480px: screen on/off (`/quick/display`) and quiet hours on/off
  (`/quick/quiet-hours`). Each posts the opposite state with `return_to=/`,
  persists through the existing server-side validation, redirects to Home and
  the existing flash banner confirms.

## Routes

Reused, unchanged: `POST /quick/display`, `POST /quick/quiet-hours` (the
`return_to` whitelist already contains Home). Nothing added.

## Auto-refresh

Home header carries `refresh_marker_html(now)`; `.page-header__freshness` and
the card (`section[aria-labelledby="home-frame-state"]`) join the Home swap
registry in `companion/ui_nav.py` and its mirror in `freshness.js`.

## Lightbox

The Flights lightbox lost its note element; `panel-lookup.js` no longer
requires one (Airlines keeps its empty note). Deleted
`flights.this_is_the_nearest_recorded_render_not` and
`flights.colours_are_nominal_render_internal_swatches` (EN source and FR).

## Tests

- `companion/test_home_state_card.py`: state wording per state (on, off, quiet
  hours, battery hold over display off, no check-in), FR, POST round trips
  with persisted effect and flash, rejected state value.
- `companion/test_browser_home_state_card.py`: 1280/390/360 px, EN and FR, 44px
  targets, no overflow, keyboard focus ring and Space activation, scripts-blocked
  post.
- Retargeted (not skipped): Home widgets test, Home swap-registry and
  freshness-marker tests, the panel-lookup guard test, the lightbox shared-token
  list and the lightbox caveat test.
- `render_baseline.json` regenerated after inspecting the diff: exactly the four
  Home entries (EN/FR across the two themes) gained the
  silent marker and the card; every other page and the unauthenticated
  responses are byte-identical.

## Deviations from Plan

None of substance. The Frame strip code was kept (Display still uses it);
nothing was deleted except the lightbox note and its two keys.

## Unresolved

- The Phase 44 open question about renaming Home to "General" is untouched.
- Quiet-hours flash text still says "turned on/off" (existing keys reused).
