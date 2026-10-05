---
quick_id: 261005-lgo
type: quick
autonomous: true
branch: claude/skypane-logo
---

# 261005-lgo: SkyPane logo, direction C ("Leaving the frame")

## Objective

Ship the owner-approved logo: an "S" inside a portrait 3:4 pane whose top-right corner is open,
with one accent flick leaving through the gap. Sketches and the cost/risk analysis live outside
the repo (scratchpad `sketches-logo/`); owner decisions: direction C, favicon/home-screen tile is
C's own tile, wordmark text "SkyPane" stays beside the mark (live `.site-title` text), casing
unchanged, no mark on the e-ink image, no web manifest, an apple-touch-icon yes.

## Tasks

1. `icon-logo` sprite symbol (ink = currentColor, one accent stroke through a class bound to
   `--color-accent`), `ICON_IDS` 39 -> 40, tests that pin the count.
2. Brand lockup (mark + `.site-title` text) in the sidebar and the phone app bar; decorative mark.
3. Login card: inline SVG mark above the `<h1>` (the login shell carries no sprite).
4. Replace the `data:` favicon with a served `favicon.svg` (public static route) and add a
   pre-rendered 180x180 `apple-touch-icon.png` + its `<link>`.
5. Rewrite the stale accent-reservation comment in `style.css` as a current, exhaustive list
   that includes the logo accent.
6. Tests: served-HTML (mark in sidebar/app bar/login, favicon links in EN/FR on every page
   type), static route (public, type, cache, no secrets), PNG sanity, Playwright lockup checks.
7. Regenerate the render baseline and review that only the favicon link, brand lockup, login
   mark and the new sprite symbol changed.
