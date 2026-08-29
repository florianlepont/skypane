---
name: sketch-findings-skypane
description: Validated design decisions, CSS patterns, and visual direction from Phase 06.6.1's sketch experiments (warm serif headings, orange/amber accent, card relief, mobile hamburger nav, History table density). Auto-loaded during UI implementation on skypane.
---

<context>
## Project: skypane

SkyPane's companion web app (a stdlib-only Python HTTP service under `companion/`) evolving 06.3's shipped visual design toward something warmer and more "crafted," referenced against Goodreads: cards with visible relief instead of flat bordered boxes, a warm serif for headings (body/data stays sans-serif for legibility), a new orange/amber accent color, and a generally airier layout with more breathing room.

Reference point: Goodreads — warm editorial feel, card-based browsing with visible relief, serif headings over a clean utility layout.

Raised from real-device testing during Phase 06.5's 06.5-03 verification session, which found the shipped 06.3 UI had never actually been looked at on a real phone before, surfacing both a real CSS bug (mobile nav-bar crush, fixed separately in commit `b90ed88`) and this batch of design feedback.

Sketch sessions wrapped: 2026-08-29
</context>

<design_direction>
## Overall Direction

- **Color:** new primary accent `#E8622C` (light) / `#FF8A5C` (dark) — a coral/terracotta orange, deliberately distinct in hue from the existing `--color-status-warn` amber (`#D97706`) so the two never blur together. All other existing tokens (status colors, borders) unchanged.
- **Typography:** warm serif (`Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif`) on every heading level — page titles, section headings, stat-tile captions. Body text, tables, and monospace/data content stay on the existing sans-serif — serif is a headings-only treatment, never applied to dense/tabular content.
- **Spacing:** generously increased throughout — this is a global direction, not limited to specific flagged pages.
- **Cards:** visible shadow at rest (`--shadow-card`), lift on hover, transparent border instead of a hairline border.
- **Layout:** the battery-trend chart breaks out of the stat-tile dashboard grid into its own full-width section. The Health page's anomaly banner keeps its visual alert (red left border) but drops the redundant detail-text list, since the Overview stat tiles below already carry that information via color/status.
- **Navigation (mobile, <960px):** a hamburger-triggered dropdown replaces the horizontal-scroll nav strip, expanding below the header and pushing page content down (not a full-screen or backdrop overlay). The theme picker relocates inside this dropdown.
- **Data density:** History's table drops from 9 to 7 columns by merging Callsign+Hex and Type+Airline into single dot-separated cells, keeping today's row height.
</design_direction>

<findings_index>
## Design Areas

| Area | Reference | Key Decision |
|------|-----------|--------------|
| Visual Direction & Typography | references/visual-direction-typography.md | Serif headings, card shadows, warm background tint, `#E8622C` accent |
| Mobile Navigation | references/mobile-navigation.md | Header-dropdown hamburger menu, pushes content down, theme picker inside |
| Data Density | references/data-density.md | History table: Callsign·Hex and Type·Airline merged inline, 9→7 columns |

## Theme

The winning theme file is at `sources/themes/default.css` — evolves the real tokens from `companion/static/style.css` (do not treat this as a from-scratch palette; it's additive/modifying, not a replacement file).

## Source Files

Original sketch HTML files (all variants, winners marked with ★) are preserved in `sources/`:
- `sources/001-health-page-direction.html`
- `sources/002-mobile-hamburger-nav.html`
- `sources/003-history-table-density.html`
</findings_index>

<metadata>
## Processed Sketches

- 001-health-page-direction (winner: B)
- 002-mobile-hamburger-nav (winner: C)
- 003-history-table-density (winner: B)
</metadata>
