---
quick_id: 261004-at1
subsystem: companion
tags: [airlines, tiles, carousel, css, i18n]
key-files:
  modified:
    - companion/pages/airlines_page.py
    - companion/static/airline-types.js
    - companion/static/list-filter.js
    - companion/static/style.css
    - companion/ui_filter.py
    - companion/i18n_fr/airlines.py
    - companion/testdata/render_baseline.json
completed: 2026-10-04
---

# Quick 261004-at1: Airlines tiles cleaned up

- **Summary control removed.** No "N manual resolutions, N superseded" button;
  its six constants, four FR strings, `.manual-summary:hover` rule and the
  `[data-filter-set]` hook in `list-filter.js` (its only consumer) are gone,
  with their tests. The per-card "Resolved by hand" chip stays.
- **Text lines removed.** A default tile is the airline name and its artwork.
  One small badge shows only when notable, by priority: the manual-name chip
  (resolved by hand / built-in name used instead), then "No artwork yet", then
  "Replaced artwork" / "Your artwork". Four now-unused strings dropped, one
  added ("Replaced artwork").
- **Edit button.** The large Replace/Add artwork button is a round pencil on
  the artwork's corner: 32px disc with a 44px hit area (measured 44x44 in a
  browser), accessible name kept ("Replace artwork: Air France"), identical
  `data-view-panel-*` vocabulary, `panel-lookup.js` unchanged. `icon-pencil`
  already existed, so the sprite and icon-count tests are untouched.
- **Type carousel.** The native select is a horizontal scroll-snap strip: one
  slide per type, the type name in the label voice under the image, script-gated
  pagination dots (28 x 44px targets, the one deliberate trade: four 44px dots do
  not fit a 143px phone tile and 28px clears the 24px AA floor). It swipes and
  scrolls natively without script; a single-type airline has no dots and does
  not scroll; reduced motion jumps instead of smooth-scrolling. Tile height at
  390px: about 238px before, 95px after (single-type).
- The disclosure-sweep browser check now exempts scroll-snap strips (a
  deliberate scroller) from its stray-scrollbar and off-screen findings.

Full suite 3771 passed, 8 skipped; ruff, mypy, function-size and
comment-history gates clean.
