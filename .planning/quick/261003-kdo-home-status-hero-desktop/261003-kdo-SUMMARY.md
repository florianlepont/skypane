---
quick_id: 261003-kdo
slug: home-status-hero-desktop
date: 2026-10-03
branch: claude/home-status-hero
commits: [728c5e32, c3f7e863]
key-files:
  modified:
    - companion/pages/home_page.py
    - companion/draw.py
    - companion/ui_base.py
    - companion/i18n_fr/home.py
    - companion/static/style.css
    - companion/test_home_state_card.py
    - companion/test_browser_home_state_card.py
    - companion/test_companion_app_01.py
    - companion/test_view_pages_04.py
    - companion/testdata/render_baseline.json
---

# Quick 261003-kdo: Home status header as the "Frame signal" hero

Home's status header now follows the approved Direction A mockup on every
width. One component, mobile-first, arranged by the card's own width.

## What shipped

- **Hero card**: a faint radial glow tinted by the state (green on, amber
  long overdue or battery hold, neutral when screen off or quiet hours); a
  visible "Frame state / État du cadre" micro-label (the section's h2, no
  longer visually hidden); a serif title at the page-title size with a
  haloed dot. Held states are now a short title plus a muted sentence
  ("Screen off" / "The frame stays blank"), with six new EN/FR message ids
  replacing the three long ones.
- **Next update** line led by a clock icon, or a warning sign once overdue;
  the cadence `<details>` is muted (no accent); "See Health" is an accent
  pill with a chevron beside it when long overdue.
- **Battery dial**: new `draw.arc_gauge()` (270-degree open arc, the same
  dashed-circle technique as `ring_gauge()`, presentation attributes only,
  no `style=`; round caps paid for in the dash so the ink equals the
  fraction). Percentage and "Battery" sit in its centre, Low / Very low as a
  pill in the gap. Levels, thresholds (`LOW_BATTERY_DISPLAY_PERCENT`, health
  verdict, battery hold) and the accessible name are unchanged.
- **Switches** become pills with leading monitor and moon icons in a
  recessed panel; still the shared native `role="switch"` POST forms to
  `/quick/display` and `/quick/quiet-hours` (no-JS, flash, 56 px row target).
- **Layout** (container query on the card): stacked under 520 px of card;
  state beside the dial with the switches below (side by side from 600 px)
  up to 840 px; three columns from 840 px of card.
- **Dark switch thumb**: new `--color-switch-thumb` token (white light,
  `#E6E9EE` dark) applied to every `.switch`, so an unchecked thumb is
  visible on its dark track.
- Sprite gains `icon-warning` and `icon-chevron-right`.

## Deviations

1. **Owner update mid-task**: mobile was first to stay unchanged, then the
   owner asked for Direction A on mobile too. Mobile now uses the same
   component (centred dial, full-width pills, 44 px Health pill).
2. **Container query, not a viewport media query, for the columns.** With
   the sidebar, the card is about 624 px wide at a 1024 px window, narrower
   than at 840 px (792 px). Three columns at that width would squeeze the
   state column to under 200 px (the old layout already overflowed its
   switches out of the card at 1024). So the three-column layout needs
   840 px of *card* (a 1280 px window), and 840/1024 px windows get the
   two-row desktop layout (state | dial, switches below side by side).
3. **Headline split** into a title plus a sentence, so the serif display
   size fits every state ("Batterie très faible — le cadre se repose
   jusqu’à sa recharge" would otherwise fill four lines on a phone).
4. **Health link moved** out of the next-update line, beside the cadence,
   as in the mockup.
5. **Sizes**: only existing tokens and the documented 12 px uppercase
   micro-label tier are used. There are no new font sizes. The headline and
   the dial figure use `--font-page-title-size`.

## Verification

- Screenshots (not in repo): `scratchpad/shots4/after/` (6 states x
  1280/1024/840/600/390/360 x light/dark x EN/FR) and `shots4/before/`.
- `render_baseline.json` regenerated after a scripted check that the only
  differences were the two new sprite symbols (every page) and the Home
  status header section.
- Full `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`: 3607 passed,
  8 skipped (root-permission and openssl environment skips), coverage
  95.17% (floor 93%). ruff, mypy, comment-history and function-size gates
  green.

## Known notes

- In the seeded fixture, the screen-off and quiet-hours states show 90%
  battery as "Low". The health snapshot gives a `warn` battery verdict for
  that fixture, and the app already showed the same before this change. The
  level logic was not touched.

## Self-Check: PASSED
