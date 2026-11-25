---
phase: 68-console-and-companion-visual-improvements
plan: 21
subsystem: companion
tags: [audit, css, accessibility, phone]
requires: ["68-01", "68-10"]
provides:
  - "Audit log per the owner-approved mockup: one scrolling filter row on phone, opened events in a tinted label/value panel"
affects: ["68-22"]
key-files:
  modified:
    - companion/static/style-admin.css
    - companion/static/style-c-lists.css
    - companion/static/motion.js
    - companion/test_browser_audit_page.py
decisions:
  - "The scrolling row is the existing links track made one-line on phones (not separate pills)."
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 21: Audit page Summary

The Audit category filter is one line on phone that scrolls sideways (current category filled and opened into view, right edge fading), and an opened event shows its details in a tinted panel, label left and value right. Access, routes, query parameters and audit content are unchanged; `audit_page.py` markup and French strings did not change.

## What was built

- Filter row: below 700 px `.filter-bar__chips--links` is `nowrap`, scrolls sideways with no scrollbar, a mask fades the right edge and the last chip scrolls clear of it. From 700 px it is the unchanged full-width track. `motion.js` opens a sideways-scrolling strip with the current segment in view and adds the scroll offset to the sliding fill so it stays under the right chip.
- Descender fix: the chip label no longer clips letters such as the g of "Pairing" (the trimmed text box was cut by `overflow: hidden`).
- Opened event: `.audit-event__detail` is a tinted panel (5 % of the text colour, control radius); each item is a 6 rem label column and a value column. From 640 px of group width the panel keeps the four-column grid (label over value) inside the tint. Labels use 80 % text colour so they reach 4.5:1 on the tint (70 % gave 4.36:1, caught by the new test).
- Tests (`test_browser_audit_page.py`): at 360 px one line, scrolls, chips >= 44 px, current chip marked, in view and its text centred, no sideways page scroll (light and dark); opened event is tinted, label and value share a line with the value right of the label, labels >= 13 px, label and value ink contrast >= 4.5:1 measured from pixels, rows spaced apart (light and dark).

## Captures (scratchpad p21)

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p21/`: `before_{ph,dk}_{en,fr}_{light,dark}.png`, `after_*` (full app screen at 390 and 1280), `mock_ph_prop_*` / `mock_ph_today_*` / `mock_sec_*` (mockup), `cmp_ph_*` (mockup left, built right), `after_ph360_fr_dark_failed.png` (Failed chosen, 360 px). Scripts: `shot.py`, `mock.py`, `seed.py`, `scroll.py`, `lib.py`. Seed: ten events (frame, pairing ok and refused, role, location, release by system, co-manager, failed invite, frame actor, rename).

## Design-system divergences

- The mockup phone draws the filter as one glass track with plain labels and a filled chosen chip; this is built (the existing links track made scrolling), not the separate-pill `chips_scroll` row of plan 14, because the mockup wins. `chips_scroll` belongs to the radio filter bar; the Audit strip is links.
- Mockup dark capture shows the chosen "All" as a dark disc on dark; built uses the system's ivory selected fill (accent token).
- The tinted panel also applies on desktop and tablet (container 640 px and up) as a tint around the four-column grid; the mockup shows phone only.
- Panel tint is `color-mix(5 % text)` and the label column is 6 rem; the mockup's pixel values were matched by eye.
- `style-admin.css` and `motion.js` were edited, not only `style-c-lists.css` as the plan listed: the detail rules already live in `style-admin.css` and `test_stylesheet_structure` forbids declaring one selector in two sheets; the scroll offset needed `motion.js`.
- The mask uses `var(--color-text)` as its opaque stop because `test_stylesheet_structure` forbids colour literals.
- The plan's "replace hand-built banner__pill" did not apply: the page already uses the catalogue `pill_html`.

## Deviations from Plan

None beyond the divergences above. No new strings, so no French change was needed (`admin_lifecycle.py` untouched).

## Gates

ruff, mypy, `check_comment_history.py check`, function size (max 80), app.py 1490 lines, motion.js well under 1500. Focused run (audit, co-manager, i18n, structure and suite guards, access matrix, page_styles, stylesheet_structure, French fit, status and view pages, overhaul sweep, contrast, Fleet tabs, motion, components page, Airlines table): all pass. `test_render_baseline.py` not run or regenerated (plan 22 does that).

## Self-Check: PASSED
