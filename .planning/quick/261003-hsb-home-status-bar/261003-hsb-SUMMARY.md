---
phase: quick
plan: 261003-hsb
subsystem: companion/home
tags: [home, status, switches, battery, a11y, i18n]
key-files:
  modified:
    - companion/pages/home_page.py
    - companion/static/style.css
    - companion/i18n_fr/home.py
    - companion/test_home_state_card.py
    - companion/test_browser_home_state_card.py
    - companion/test_companion_app_04.py
metrics:
  completed: 2026-10-03
---

# Quick 261003-hsb: Home status header with real switches

**One rounded status panel directly under the Home title: coloured-dot headline, next update, a battery block with glyph, percentage and level word, muted cadence text, and two native `role="switch"` forms (Screen, Quiet hours with its window).**

## Design

- Desktop: status left, switches right (grid, 840px+); phone: stacked, each
  switch row full width, 56px tall, and the whole row is the tap target
  (the native button's `::after` stretches over it).
- Headline keeps the existing precedence (battery hold > display off > quiet
  hours > on); dot sits in a soft ring; words carry the meaning.
- Switches reuse the shared `layout.quick_switch_html()` (POST
  `/quick/display`, `/quick/quiet-hours`, flash on return, works without JS).
  The row has no `data-quick-region`, so quick-switch.js does not intercept:
  a press is a full redirect and the headline/next update are never stale.
- Battery: SVG glyph filled to the percentage, semibold value, "Battery" label,
  and for low / very low a word too; level follows battery_critical, the
  health battery state and the shared 20% low threshold. One named image
  ("Battery about ≈ 90%, low"). No reading: words only.
- Cadence sentence is small muted help text. Old bottom card and lone chip
  removed; `.home-facts` now holds only the unchanged warning link and is
  hidden when empty. Obsolete strings (turn on/off buttons, quiet schedule
  sentences) removed from the French catalogue.

## Tests

Retargeted test_home_state_card.py and test_browser_home_state_card.py
(position above the picture row, 44px targets, 1280/390/360 EN/FR, Space,
Enter, row click, no-JS, dark/light battery name); new battery level tests
(ok / low / critical, EN/FR, no reading); test_companion_app_04 chip needle.

## Deviations

- Mid-task coordinator request: battery treatment upgraded (glyph + value +
  level word + accessible name) beyond the original chip.
- Fixed a press-state bug found by the row-click test: `button:active`
  transform shrank the stretched target; overridden for the switch.
- No JS enhancement: full redirect kept deliberately (see Design).

Screenshots (not in repo):
/tmp/claude-0/-home-user-skypane/d89080dc-5e3d-5e46-9cec-c090cb9715bb/scratchpad/shots/
(on / quiet / off and battery 90 / 35 / 8 percent, light + dark, 1280/390/360).
