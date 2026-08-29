# Visual Direction & Typography

## Design Decisions

**Winning variant: Sketch 001, Variant B ("Full editorial")**

- **Background:** slight warm tint instead of the current cool off-white — `#FBF9F6` for the page body, `#F3EEE7` for sidebar/header surfaces (was `--color-dominant: #FAFBFD` / `--color-secondary: #EEF1F7`).
- **Cards:** visible shadow at rest (`--shadow-card`), lift on hover (`--shadow-card-hover` + `translateY(-1px)`), border goes transparent (shadow carries the edge instead of a hairline border).
- **Headings:** warm serif (`Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif`) on every heading level — page `<h1>`, section `<h2>`, and stat-tile captions. Body text, tables, and mono/data content stay on the existing sans-serif (`--font-ui`) — serif is for headings only, never for dense/tabular content (legibility).
- **Stat-tile captions:** switch from small-caps uppercase label style to a normal-case serif treatment at 15px (was `text-transform:uppercase; letter-spacing:0.04em` in the sans-serif label size) — reads warmer, less "form field label."
- **Accent color:** new primary accent — `#E8622C` (light) / `#FF8A5C` (dark), a coral/terracotta orange. **Deliberately chosen to sit at a different hue (~16°) than the existing `--color-status-warn` (`#D97706`, ~32° golden amber)** so the new accent and the "warn" status dot never read as the same color at a glance. Do not substitute a more golden/yellow orange without re-checking this against the warn color.
- **Icons on stat tiles:** accent-tinted (`color: var(--color-accent)`) in the winning variant, small inline SVG (20×20), outline style, `stroke="currentColor"`.
- **Spacing:** generous throughout — `.page-content` padding bumped from `var(--space-xl) var(--space-2xl)` to `var(--space-2xl) var(--space-3xl)`, `.overview-grid` gap bumped from `var(--space-lg)` to `var(--space-xl)`. This is a global direction (per 06.6.1-CONTEXT.md D-02: "plus aéré partout"), not limited to the pages that were flagged.
- **Anomaly banner:** kept the existing red-left-border treatment (`.banner--anomaly`) but with its redundant detail-text list removed — the banner communicates "something needs attention," the Overview stat tiles below carry the specifics via their own color/status.
- **Battery trend section:** moved OUT of the `.overview-grid` entirely into its own full-width section below it (was cramped inside the grid as one of several tiles). Same card treatment (shadow, radius) as the stat tiles, serif `<h2>` heading.

## CSS Patterns

Full winning-variant CSS is in `sources/001-health-page-direction.html`, scoped under `#variant-b`. Key extractable rules:

```css
/* Card relief */
.stat-tile{box-shadow:var(--shadow-card);border-color:transparent;transition:box-shadow .15s, transform .15s}
.stat-tile:hover{box-shadow:var(--shadow-card-hover);transform:translateY(-1px)}

/* Serif headings */
h1, h2, h3, .text-heading{font-family:var(--font-serif);font-weight:var(--weight-regular);letter-spacing:-0.01em}

/* New tokens (add alongside existing companion/static/style.css tokens, don't replace the file) */
--font-serif: Georgia, "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
--color-accent: #E8622C;      /* light theme, was #3454D1 */
--color-accent-hover: #D2521F;
--shadow-card: 0 1px 3px rgba(18, 21, 27, 0.06), 0 1px 2px rgba(18, 21, 27, 0.04);
--shadow-card-hover: 0 4px 12px rgba(18, 21, 27, 0.08), 0 2px 4px rgba(18, 21, 27, 0.05);
--radius-card: 10px;
```

Dark theme accent: `#FF8A5C` (light) — proportionally shifted the same way the existing dark-theme tokens shift `--color-status-*` lighter/more saturated than their light-theme counterparts.

## HTML Structures

No new HTML elements beyond what `companion/layout.py`'s `stat_tile()` and `page_shell()` already emit — this is a CSS-only visual layer on the existing markup, plus:
- New `<svg>` icons inside each stat-tile's header (see sketch source for the 4 icon defs: check-in, pipeline, corroboration, battery — reusable `<use href="#icon-name">` pattern via a shared `<defs>` block).
- Battery-trend section's markup unchanged in shape, just relocated outside the grid container in the DOM/render order.

## What to Avoid

- **Variant A ("Minimal warmth")** — rejected. Too subtle; the serif-only-on-h1 + shadow-on-hover-only treatment didn't read as a meaningfully different direction from the current 06.3 look.
- **Variant C ("Structured warmth")** — rejected. The colored-left-border-per-status approach (echoing the anomaly banner) was visually distinct but competed with the anomaly banner's own left-border for attention, and made every card look like a warning/status indicator even for the accent-only battery section.
- Do not use serif for body text, table cells, or any monospace/data content — sketch 001's "Serif partout" option was explicitly rejected during discuss-phase (06.6.1-CONTEXT.md D-03) for legibility reasons.
- Do not pick an accent hue close to the existing warn-status amber (`#D97706`) — this was a specific, named risk in 06.6.1-CONTEXT.md D-04.

## Origin
Synthesized from sketch: 001 (health-page-direction), winner: Variant B
Source file available in: `sources/001-health-page-direction.html`
