---
sketch: 002
name: mobile-hamburger-nav
question: "How should the mobile nav menu open, and where does the theme picker live inside it?"
winner: null
tags: [navigation, mobile, interaction]
---

# Sketch 002: Mobile Hamburger Nav

## Design Question
Real-device testing during 06.5-03 found the current horizontal-scroll nav strip (below 960px) effectively hides Health/Airlines/History/Preview behind an undiscoverable swipe — only 2-3 tabs are visible at once on a real phone. This sketch replaces it with a real hamburger menu and explores where the theme picker (Auto/Light/Dark) relocates to once it's no longer squeezed into the header row.

All three variants are wrapped in a phone-frame for a realistic feel, and are fully interactive — tap the ☰ icon for real.

## How to View
```
open .planning/sketches/002-mobile-hamburger-nav/index.html
```
(Same file:// caveat as sketch 001 — serve via `python3 -m http.server` from `.planning/sketches/` if the stylesheet doesn't load.)

## Variants
- **A: Full-screen overlay** — Tapping ☰ replaces the whole screen with the menu (large serif nav links, theme picker at the bottom, × to close). Maximum focus, no ambiguity about what's interactive, but a full context switch away from the page.
- **B: Slide-in drawer** — Menu slides in from the left over a dimmed backdrop; the page is still visible (dimmed) behind it. Tapping the backdrop or × closes it. Familiar pattern (same shape as most native apps' side menus).
- **C: Header dropdown** — Menu expands directly below the header, page content still fully visible below it (pushed down, not covered). Smallest visual jump, but the dropdown can get long with 5 links + 3 theme buttons.

All three: Escape key closes, hamburger button has `aria-expanded`, 44px+ tap targets on every link/button.

## What to Look For
- Does the theme picker feel natural inside the menu, or does it want to live somewhere else (e.g., a separate icon)?
- Full-screen (A) vs. partial (B/C): which feels right for a 5-item nav — is A overkill, or does the focus help?
- C's dropdown pushes page content down rather than covering it — does that feel more or less jarring than A/B's overlay approach?
- Try resizing the phone frame narrower/wider, and try tabbing with the keyboard instead of clicking.
