---
sketch: 001
name: health-page-direction
question: "Does the new visual direction (serif headings, cards with relief, orange/amber accent, airier spacing) work on a real page?"
winner: null
tags: [visual-direction, typography, color]
---

# Sketch 001: Health Page Direction

## Design Question
Real-device testing during 06.5-03 surfaced a request for a warmer, more "crafted" feel (referenced against Goodreads: cards with relief, warm serif headings, richer color, airier layout). This sketch applies that direction to the real Health page — the page with the most element variety (badge, dashboard grid, anomaly banner, full-width chart) — to see if it actually works before touching any real code.

Also validates: the cleaned-up anomaly banner (no redundant text list, per 06.6.1-CONTEXT.md D-... anomaly banner decision), SVG icons on Overview tiles, and the battery trend chart broken out of the stat-tile grid into its own full-width section.

## How to View
```
open .planning/sketches/001-health-page-direction/index.html
```
(If your browser blocks the relative stylesheet link over `file://`, serve the `sketches/` directory with `python3 -m http.server` from `.planning/sketches/` and open `http://localhost:PORT/001-health-page-direction/index.html` instead.)

## Variants
- **A: Minimal warmth** — Subtle relief (shadow only on hover), the new orange accent used sparingly (left-border accent on the battery section, sparkline color), serif on the page `<h1>` only, spacing bumped modestly. Lowest-risk evolution of 06.3's existing look.
- **B: Full editorial** — Cards carry a visible shadow at rest (lift on hover), background gets a very slight warm tint, serif on every heading including stat-tile captions, generous spacing throughout. The fullest expression of the "Goodreads" reference.
- **C: Structured warmth** — Cards use a colored left border (echoing the existing anomaly-banner pattern) instead of shadow for visual weight, with matching-colored icons per status. A genuinely different structural idea: color-coding via border rather than shadow-driven relief.

## What to Look For
- Does the orange/amber accent read as clearly distinct from the existing amber "warn" status dot, or do they blur together?
- Serif headings: do they feel warm/crafted, or do they clash with the mono/sans-serif data below them?
- Card relief (B's shadows vs. C's colored borders vs. A's minimal touch): which best signals "this card matters" without becoming noisy across a whole page of cards?
- Does the cleaned-up anomaly banner (visual alert only, no repeated detail text) still communicate clearly, or does it feel like it's hiding information?
- The full-width battery-trend section: does breaking it out of the grid make it feel like a distinct, more readable focal point, or does it feel disconnected from the Overview tiles above it?
- Check both desktop (`≥960px`, sidebar nav) and mobile (`<960px`, top header) — the toolbar's viewport buttons help, or just resize the window.
