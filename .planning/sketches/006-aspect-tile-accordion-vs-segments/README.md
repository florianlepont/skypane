---
sketch: 006
name: aspect-tile-accordion-vs-segments
question: "Accordion or segments — which structure reads best for Aspect's one-tile rebuild (CFG-85)?"
winner: "A (Accordion)"
tags: [settings, theme-picker, control-density, visual-direction, phase-30]
---

# Sketch 006: Aspect tile — accordion vs segments

## Design Question

Phase 30 (CFG-85) replaces Display's "Frame colours" card (live preview + 4-row radiogroup + 18-chip scroll-snap carousel with pagers/dots/disclosure) and the separate "Calendar" card with ONE tile: a live preview, three usage rows (Départs/Arrivées/Vols du calendrier) each showing one swatch and the theme name, a wrapping palette of the 18 real themes under the open row (no strip, no scrollbar, no pagers, no dots, no disclosure), the calendar's connection folded under its own row, and "Règles par vol" as a secondary disclosure row.

Two structures deliver that content. Which one reads best?

## How to View

```
python3 -m http.server 8731 --directory .planning/sketches
open http://localhost:8731/006-aspect-tile-accordion-vs-segments/index.html
```

(A plain `open index.html` also works — the sketch has no external dependency beyond `../themes/default.css`, which resolves fine over `file://` in a real browser.)

## Variants

- **A: Accordion** — the three usage rows plus the secondary rules row are native `<details name="aspect-rows">` elements (zero script needed for the one-open-at-a-time behaviour — the browser's own `name`-grouped `<details>` feature does it). Opening a row reveals its palette directly underneath. All three current values (Départs, Arrivées, Vols du calendrier) are visible at once, closed.
- **B: Segments** — three tab-like segments above ONE shared palette grid, reused across all three usages. The calendar's connection status sits permanently below the grid, never hidden behind the Calendrier segment. Only one usage's value is visible at a time; the other two require a click to see.

Both variants:
- Use the real 18-theme registry (`server/device_config.py` THEMES) and the real Spectra 6 ink colours (`server/panel_format.py` PALETTE_RGB) for every swatch — including the honest fact that `band_blue_field`/`band_red_field` paint identically to their plain-hue sibling (departing_index == band_index for both in the real registry), so their swatches are solid fills too, not a fake band.
- Ground the live preview in a real callsign (`TVF58GB`, the same one from the developer's own original screenshot that started this cycle of feedback).
- Carry "Comme les départs" as a real toggle on Arrivées/Vols du calendrier, wired to actually follow Départs' selection live.
- Are fully clickable — every swatch, segment, and toggle updates real state, not decoration.

## What to Look For

- **At-a-glance value visibility.** Accordion shows all three current themes closed; Segments shows only the active one. Does seeing all three matter, or is clicking through acceptable given the palette is the same content either way?
- **Calendar's placement.** Accordion nests the connection status inside the "Vols du calendrier" row (opens/closes with it). Segments keeps it permanently visible below the grid, decoupled from which segment is active. Which reads as "the calendar's colour AND its connection live in one place" more clearly?
- **Repetition vs redundancy.** Accordion builds three independent palette grids (one per row); Segments builds one, reused. Does Accordion's repetition feel like unnecessary weight, or does each row feeling "complete on its own" matter more?
- **Résize to 360px** (the app's own floor) — both variants target a narrow settings-page column; check nothing wraps awkwardly or the palette grid gets uncomfortably cramped.
- **Dark mode** (the Clair/Sombre switch top-right) — swatches and selection state should stay legible in both themes.

## Decision

**Winner: A (Accordion).** Approved by the developer 2026-09-22 after re-verifying both variants at the 360px floor and in dark mode. Phase 30 planning should build the one-tile Aspect rebuild on the accordion structure: `<details name="aspect-rows">` per usage row, palette inline under the open row, calendar connection status nested inside "Vols du calendrier", "Règles par vol" as a fourth disclosure row with the add-rule form from `config_page.py`'s `_rule_add_form_html()`.
