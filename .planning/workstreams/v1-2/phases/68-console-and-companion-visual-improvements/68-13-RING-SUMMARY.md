---
phase: 68-console-and-companion-visual-improvements
plan: 13-ring
subsystem: companion
tags: [home, ring, motion, accessibility]
---

# Phase 68 Plan 13 Ring: the cycle ring around the Home frame picture is back

Owner request after plan 68-13 (which had removed the old Home hero ring because the approved mockup has none). No state or requirement command was run, CON-01 is not ticked, ROADMAP unchanged.

## Where the ring sits and how it fills

- It wraps the frame picture inside the Home flight card (`.home-flight__picture`, the same box that holds the picture, 132 px wide on a phone, 168 px from 700 px, 200 px or full width for a landscape frame). It is a thin SVG outline 5 px outside the picture, with corners rounded to the picture's radius plus 5 px (`--radius-frame-pic`), taking no room and no pointer events; the card's own padding keeps its stroke inside the card. The same markup serves a portrait and a landscape picture (it is sized by the picture box).
- It has two strokes: a faint 1 px track (text colour at 14 %) and a 2 px accent bar (`--color-accent`, so it reads in light and dark). The bar is the share of the frame cycle already elapsed: it starts at the top left and runs clockwise, empty right after a wake and full at the moment the next update is due.
- Progress = `1 - (next update - now) / cycle length`, from the same next-update instant (`wake.next_wake_status` triple, the one the title sentence "Prochain rafraichissement dans N min" reads) and the wake interval. The server draws it (`stroke-dashoffset` attribute, so it is right without script and the CSP needs no style attribute); `relative-time.js` repaints it every second from the `data-ring-next` / `data-ring-interval` attributes, with no transition (no running animation for the page to wait out). It stops at full when the update is late.
- A refresh redraws it: the flight card is one of Home's swapped regions, so the 45 s refresh brings a fresh ring computed from the new check-in, and the progress starts over when the frame has woken.

## States

- Online (status "Online"): ring shown.
- Sleeping ("Au repos": quiet hours or screen off), no contact, not seen yet, overdue, low battery, retired, waiting for pairing: no ring is drawn. The old ring drew a countdown whenever a next instant existed; here a frame that is not running its cycle has nothing to count down, and the title sentence already says when it wakes or when it was last heard from (an outline filling towards a wake hours away, or stuck at full for a late frame, would misstate the state). The offline picture keeps its existing grey, dimmed treatment.

## Accessibility and motion

- Decorative: `aria-hidden="true"`, `focusable="false"`, no role and no label. The next-update sentence is the text alternative (the old ring's own aria-label and its string `home.cycle_ring_label` are gone; EN and FR are unaffected).
- `prefers-reduced-motion: reduce`: the ring stays exactly as the server drew it and is not repainted by the per-second tick (it is redrawn only by the next refresh); it never had a CSS animation or transition.

## What changed

- `home_flight_card.ring_html()` and `card_html(ctx, row, ring="")`; `home_page.render` passes the ring only for the Online status.
- `style-home.css`: `.home-ring*` rules (design tokens only, no colour literals) and `position: relative` on the picture box; the dead `.hero__ring*` rules and the ring pop/glow keyframes are deleted from `style.css`. The other `.hero*` rules stay: `ui_groups.hero` is still used (components catalogue).
- `relative-time.js`: the revived ring uses the progress tick; the flourish code (`is-ring-done`, jump detection), the aria-label rewriting and the quarter ticks are removed (the ring is no longer named, and the replaced element would not keep the class). The file stays at 303 lines.
- Tests (`test_browser_home_signature.py`, `test_browser_home_header_landscape.py`, `test_companion_app_04.py`): ring starts at the elapsed share (1, 2 and 4 minutes into a 5 minute cycle); it fills in step when the browser clock is moved forward and stops at full; static under reduced motion; decorative with the sentence as text (EN and FR); 5 px outside the picture with a visible stroke in light and dark; wraps a landscape and a portrait picture inside the card; a new check-in plus a refresh restarts it; absent while the frame rests (screen off) or is out of contact. The plain-ease-out allowlist no longer lists the removed ring rule.
- `render_baseline.json` regenerated once at the end of this part (the Home captures and the stylesheet hash changed).

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p13ring/`: `before_*` and `after_*` full-screen images of Home online (`on`), sleeping (`sleep`) and offline (`off`), phone FR light, phone FR dark and desktop FR light (`before_home_<state>_<phone|desktop>_fr_<light|dark>_full.png`). Only the online captures differ.

## Design-system divergences

- The ring is the one decorative outline on Home that the approved mockup does not show; it is here by explicit owner request, and only on the Online state. It uses `--color-accent` and `--color-text` (mixed to a faint track), `--radius-frame-pic`; stroke widths (1 px, 2 px) and the 5 px offset are plain lengths as in the old ring, since the design system defines no stroke tokens.
- The corner radius uses the CSS `rx` property on the SVG rects, which current Chromium, Firefox and Safari support; an engine without it draws square corners.
- No flourish when a new cycle starts and no quarter ticks (both were part of the old ring); not asked for, and the flourish does not survive the region swap that now replaces the ring.
- Reduced motion freezes progress between refreshes rather than animating, as the owner asked for a static state.
