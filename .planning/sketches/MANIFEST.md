# Sketch Manifest

## Design Direction

SkyPane companion web app — Phase 06.6.1's visual polish pass. Evolving 06.3's shipped design (still valid: sidebar nav at desktop width, `stat_tile()` dashboard grid, status-dot system) toward something warmer and more "crafted," referenced against Goodreads: cards with visible relief instead of flat bordered boxes, a warm serif for headings (body/data stays sans-serif for legibility), a new orange/amber accent color, and a generally airier layout with more breathing room. Real-device testing during 06.5-03 also found the mobile nav-bar (a horizontally-scrollable strip) hides most tabs on a real phone — sketch 002 explores a real hamburger menu to replace it.

Core value this all serves: "glancing at the frame tells you, in real time, whether you'll make the next RER" — the web companion is a secondary surface, but the same at-a-glance clarity matters here too.

## Reference Points

Goodreads — warm editorial feel, card-based browsing with visible relief, serif headings over a clean utility layout.

## Sketches

| # | Name | Design Question | Winner | Tags |
|---|------|----------------|--------|------|
| 001 | health-page-direction | Does the new visual direction (serif headings, cards with relief, orange/amber accent, airier spacing) work on a real page? | B (Full editorial) | visual-direction, typography, color |
| 002 | mobile-hamburger-nav | How should the mobile nav menu open, and where does the theme picker live inside it? | C (Header dropdown) | navigation, mobile, interaction |
| 003 | history-table-density | Does merging Callsign+Hex and Type+Airline make the table fit a 13" laptop without horizontal scroll? | B (Inline compact) | data-density, table |
| 004 | theme-picker-chips | Do runway-card-style chips with a real rendered theme preview actually read well at 16-theme scale? | pending | theme-picker, settings, visual-direction |
| 005 | type-ladder-health-page | Does the new type ladder (32/22/16px + unified sans-uppercase labels + 24px gaps) hold together on a real page? | pending | typography, hierarchy, labels, spacing, visual-direction |

## 06.6.4.1.1 note

Sketches 004-005 validate the design decisions already locked in `.planning/phases/06.6.4.1.1-settings-theme-picker-and-typography-spacing-direction-pass/06.6.4.1.1-CONTEXT.md` (a `/gsd-discuss-phase` session, not open exploration) — this is a "does it actually look right, rendered" check the developer explicitly required before planning, not a fresh design search. `themes/default.css` was resynced to the current REAL production tokens (`companion/static/style.css`, as of 2026-09-03) for this round — the prior 06.6.1-era snapshot it held is superseded; see the file's own header comment.
