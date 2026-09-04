---
sketch: 004
name: theme-picker-chips
question: "Do runway-card-style chips with a real rendered theme preview actually read well at 16-theme scale?"
winner: "B"
tags: [theme-picker, settings, visual-direction]
---

# Sketch 004: Theme Picker Chips

## Design Question
UIR-01/02: today's theme picker is 16 native radio inputs stacked one per row (44px each, ~850px of vertical space) with no colour information beyond the theme's name. 06.6.4.1.1-CONTEXT.md locked the direction (D-01 through D-07) — this sketch checks whether it actually holds up rendered, at real 16-theme scale, before any code is written.

## How to View
```
python3 -m http.server 8701 --directory .planning/sketches
open http://localhost:8701/004-theme-picker-chips/index.html
```
(Opening `index.html` directly via `file://` will NOT load `../themes/default.css` in some sandboxed preview environments — serve it over HTTP.)

## Variants
- **A: Today** — the current shipped state (44px radios, one per row, no swatch). Reference/contrast only, not a real option.
- **B: Chip grid, 160px ★ (winner)** — runway-card-style chips (hidden radio, accent border when selected) in a wrapping grid, each with a rendered theme-preview band on top and swatch pair + name below.
- **C: Chip grid, 140px (denser)** — same mechanism, narrower chips, more per row. A refinement knob, not a different direction.

## What to Look For
- Does the chip grid actually read faster than the old radio list at a glance?
- Is the rendered-preview band (top third of each chip) informative at this size, or too small to tell themes apart?
- Band themes (Band Blue, Band Red, etc.) use a CSS `clip-path` diagonal as a stand-in for the real panel render — the actual implementation (D-04) calls `server.plane.render` for a pixel-accurate version; this sketch only validates the layout/sizing concept.
- 160px (B) vs 140px (C): does the denser grid feel cramped, or is it worth the extra themes-per-row?
- Selected-state accent border, in both light and dark (use the "Toggle dark" control).

## Notes
- Theme data (labels, departing/arriving/ink colours, band colours) is pulled directly from `server/device_config.py`'s real `THEMES` dict and `server/panel_format.py`'s real `PALETTE_RGB` — not invented placeholder colours.
- Every theme's `departing_index` currently equals its `arriving_index` (the old two-tone "sky" pairing was retired) — that's why both swatch dots are identical per chip today. The mechanism still shows two dots to support a future two-tone theme without a markup change.
- The fixed fictional scene ("AFR123 → JFK 18:42" / "RER B 8 min") is identical across all 16 previews per D-06, so themes stay visually comparable.
