---
quick_id: 261004-9ax
subsystem: companion
tags: [flights, mobile, cards, css, i18n]
key-files:
  created:
    - companion/test_flights_cards.py
    - companion/test_browser_flights_cards.py
  modified:
    - companion/pages/history_page.py
    - companion/static/style.css
    - companion/i18n_fr/flights.py
    - companion/ui_base.py
    - companion/test_view_pages_01.py
    - companion/test_view_pages_02.py
    - companion/test_view_pages_03.py
    - companion/test_view_pages_helpers.py
    - companion/test_browser_ux_01.py
    - companion/test_companion_app_01.py
    - companion/testdata/render_baseline.json
completed: 2026-10-04
---

# Quick 261004-9ax: Flights phone tiles as compact boarding-pass cards

Below 960 px, each Flights row is now a boarding-pass card with three bands.

- **Head:** the callsign in mono, the airline muted under it with an ellipsis,
  and a 44 px icon-only "View picture" link in the top-right corner.
- **Route line:** a single row reading ORY ┄✈┄ KEF. The home end is muted and
  the direction label is tucked under the plane.
- **Tear-line stub:** a 40 px artwork plate, or a dashed "No illustration"
  placeholder, with the time and live age right-aligned on the same row.

Slim day headers ("Today · 3 Oct") come from the existing Paris-day grouping.
The desktop table is unchanged.

## What shipped vs the mockup (Direction B)

These match the mockup:
- the head layout;
- the unresolved variant ("Airline unknown" in italics plus the "Name this
  airline" link);
- the plane on a dashed track;
- the direction label in label voice;
- the dashed tear line with notches in the canvas colour (correct in both
  themes);
- the artwork plate with time and age on one row;
- the dashed no-illustration plate;
- no action at all when there is no picture;
- the day headers.

Changes made to keep the card compact:
- The direction label shares the route row's grid instead of taking its own
  padded row.
- The callsign is 16 px, not 20.
- The codes are 22 px (heading token), not 26.
- The plate is 40 px.
- Paddings are one step lower (sm/xs).
- The card gap is 8 px, not 12.

**Cards per screen at 390x844:**

| | Card pitch | Per screen (787 px above the tab bar) | Fully visible on first load |
|---|---|---|---|
| Before | 198 + 8 px | about 3.8 | 2 |
| Mockup B | about 207 + 12 px | about 3.6 | — |
| After | 159 + 8 px | about 4.7 | 3 |

## Commits

- d0eb7633 feat: card markup, icon link variant, sprite icons, FR string
- de3cce2b feat: compact card stylesheet
- a743be49 test: retargeted card tests, new served-HTML and browser checks, baseline regenerated
- 367f53ff fix: stylesheet structure guards (one rule per notch selector, no extra align-items: start)

## Deviations from Plan

1. **[Rule 1] Stylesheet guards.** The first CSS pass shared one rule between the
   two notch pseudo-elements and used `align-items: start`. That tripped
   `test_stylesheet_structure` and the dashboard-grid alignment pin. The fix
   splits the rule and drops the declaration, with no visual change.
2. **Day headers stay visible while filtering.** A header stays on screen even
   when every card under it is filtered out. This is the same behaviour as the
   desktop table's separator rows. `list-filter.js` was not changed.

## Verification

- `./scripts/run-all-tests.sh` (SKYPANE_REQUIRE_BROWSER=1) passed after the
  baseline regeneration: 3765 passed, 8 skipped (environmental), coverage gate
  met.
- ruff, mypy, `check_comment_history.py check` and
  `check_function_size.py check --max 80 server stub-server` are all green.
- I inspected the render-baseline diff before regenerating. It contains only the
  Flights card markup on the four /flights keys and the two new sprite symbols
  on every page. No unauthenticated-response change.
- Screenshots are in the session scratchpad `shots-9ax/`: before-*, v1-*, v2-*,
  v3-*, after-* at 390/360, light and dark, EN and FR, plus 1280.

## Self-Check: PASSED
