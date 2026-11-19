---
phase: 68-console-and-companion-visual-improvements
plan: 13-ring-flash
subsystem: companion
tags: [home, ring, motion, accessibility]
---

# Phase 68 Plan 13 Ring Flash: the cycle ring flashes green when it reaches 100%

Owner request: restore the old "done" flourish. No state or requirement command was run, CON-01 is not ticked, ROADMAP unchanged.

## Behaviour

- When the countdown reaches 100% (the next-update instant, client clock, in `relative-time.js`) the ring bar turns the success colour (`--color-status-ok`, the same token as the Online dot) with a short stroke-width pulse (2 s, `--motion-slow`, `--ease-out`), and returns to the accent colour after 2 s. The next check-in plus refresh then restarts the ring from zero as before.
- The state is keyed on the `data-ring-next` timestamp, not on the element. A page only flashes a cycle it watched count down (no flash on opening a page already past the instant). A region swap during the flourish brings a fresh ring that is given `is-ring-done is-ring-resumed`: it stays green for the rest of the 2 s without replaying the animation. After the flourish a swap never brings it back, so there is one flourish per cycle.
- Reduced motion: the per-second ring repaint is already off, so the ring never turns green and has no animation.
- Decorative (`aria-hidden` unchanged); no text, targets or markup changed.

## What changed

- `relative-time.js` (339 lines): `ringFlourish()` called from `repaintRing()`.
- `style-home.css`: `.home-ring.is-ring-done .home-ring__bar`, the animation rule (not applied with `is-ring-resumed`) and `@keyframes skypane-ring-done`; no colour literals. The motion-budget and plain-ease-out guards needed no change (the new animation spends the shared tokens).
- Tests in `test_browser_home_signature.py` (faked clock, phone, EN and FR, light and dark): turns green at 100% and returns to normal; one flourish across a region swap (resumed ring has no animation, a later swap plays none); no flash under reduced motion.
- `render_baseline.json` regenerated once (stylesheet hash).

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p13flash/`: `home_online_phone_fr_<light|dark>_<50pct|100pct_flash>_full.png`.

## Design-system divergences

- The flourish colour is the success/status-ok token; the 4 px pulse width is a plain length (no stroke tokens exist).
- Under reduced motion there is no green state at all (none rather than a static moment), as the ring does not repaint then.
- The flourish is on the Home ring only, which is itself an owner-requested element absent from the approved mockup.
