---
sketch: 005
name: type-ladder-health-page
question: "Does the new type ladder (32/22/16px + unified sans-uppercase labels + 24px gaps) hold together on a real page?"
winner: null
tags: [typography, hierarchy, labels, spacing, visual-direction]
---

# Sketch 005: Type Ladder on Health

## Design Question
UIR-20/21/22/23/25: today, the page title, section headings, and nested card titles are all 20-30px serif regular — hierarchy is carried by size alone, and flattens once a card title sits inside a section (both read as the same "thing"). Two competing label voices also coexist (serif tile captions vs. sans-uppercase table headers). 06.6.4.1.1-CONTEXT.md locked a full ladder redesign (D-09 through D-19) — this sketch checks it on a real Health-page composition (tiles, a card with a chart, two nested cards with tables) rather than in isolation.

## How to View
```
python3 -m http.server 8701 --directory .planning/sketches
open http://localhost:8701/005-type-ladder-health-page/index.html
```

## Variants
- **A: Today** — current shipped hierarchy: wordmark/page-title/section-heading/nested-card-title all serif, sizes 20-30px, weight 400 throughout; serif tile captions; flash banner above the title.
- **B: New ladder ★ (winner)** — 24px semibold wordmark, 32px semibold page title, 22px section heading, 16px sans-semibold nested card titles, unified 12px sans-uppercase labels everywhere (tile captions AND table headers), 24px unified card gaps, flash banner below the title.
- **C: Sizes only (the declined alternative)** — same page-title/section-heading size bumps as B, but NO weight changes anywhere and nested card titles stay serif. Kept specifically so the chosen direction (B) can be compared against the lower-risk alternative that was explicitly turned down during discussion.

## What to Look For
- Scroll to "Unresolved prefixes" / "Resolution statistics" — in B, do the nested card titles read as clearly one tier below "Battery trend" (the section heading) and two tiers below "Health" (the page title)? In A and C, do all three still read as visually interchangeable?
- **Note on B's nested-card-title change:** this specific change (sans-semibold nested titles) directly reverses quick task 260902-iag's own prior reversal of the identical change — the developer confirmed re-applying it anyway now that it's part of a full ladder, not an isolated tweak. Worth a deliberate second look here given that history.
- The tile captions ("DEVICE LAST CHECKED IN", etc.) and the table headers ("PREFIX", "COUNT") — in B they should look like the same voice for the first time. In A, the tile captions are a distinctly softer serif next to the crisp uppercase table headers.
- Flash banner position: below the title in B/C, above it in A — does moving it change how the page reads on load?
- Toggle dark mode — the unified uppercase label colour is `color-mix(in srgb, var(--color-text) 70%, transparent)`, matching this project's own established muted-text convention exactly (not a new colour).

## Notes
- All three variants share one HTML composition (injected via JS) — only the CSS differs, so any visual difference you see is purely the type-ladder change, not incidental content differences.
- Content (labels, table rows, copy) is pulled from `companion/pages/health_page.py`'s real constants and structure, not placeholder text.
- This sketch does not touch History's density tweaks (13px/75% hex, 14px/36px mobile buttons — D-18) or the section-intro mobile wrap fix (D-19) — those are lower-risk, narrowly-scoped CSS changes with no real layout ambiguity, not worth a dedicated visual check.
