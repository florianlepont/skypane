# Sources: historical design explorations

These files are throwaway HTML sketches from the September 2026 round (Phase 06.6.1 direction:
warm canvas, terracotta accent, serif headings, hamburger navigation, relief cards). They are kept
only as history. **They are NOT the current design.** The shipped system is described in
`../SKILL.md` and `../references/`, and is implemented in `companion/static/style*.css` and
`companion/ui_*.py`. Do not copy values from here.

| File | Status |
|------|--------|
| `001-health-page-direction.html` | Superseded. Warm-serif card direction; Health is now a part of the Fleet view and the whole app is sky, glass and system sans (`references/tokens-and-theming.md`, `references/page-patterns.md`). |
| `002-mobile-hamburger-nav.html` | Superseded. The hamburger and gear toggle, dropdown panel and `.nav-status` strip no longer exist; navigation is a floating bottom tab bar with a More panel (`references/navigation.md`). |
| `003-history-table-density.html` | Superseded. The Flights page has no detail row, toggle column or uppercase header; it is one glass group per day on a phone and a glass table on desktop (`references/page-patterns.md`). |
| `themes/default.css` | Superseded. The sketch theme (serif, orange accent, `--color-secondary` beige). The real tokens are in `references/tokens-and-theming.md`. |

Newer exploratory sketches (v1.3 photo frames, companion mockups) live under `.planning/sketches/`
and in draft PR #378; they are not part of this skill until they ship.
