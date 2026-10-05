---
quick_id: 261005-nvt
type: quick
autonomous: true
branch: claude/fix-nav-transition-clicks
---

# 261005-nvt: scripts-blocked sheet tests opt out of the cross-document view transition

## Objective

CI keeps failing scripts-blocked in-page sheet tests with `<html> intercepts pointer events`
(airline sheet on main, then the calendar sheet), always on a click made right after a
navigation. Find the cause and fix it at the root instead of retrying clicks.

## Finding

`style.css` installs `@view-transition { navigation: auto }` only under
`prefers-reduced-motion: no-preference`, which is the default of every test context. Right
after a cross-document navigation the transition's overlay is the hit target: an isolated
experiment (two static pages, same at-rule) reports `HTML` at the centre of a visible button
under `no-preference` and `BUTTON` under `reduce`. On a slow CI machine that window outlasts
Playwright's click retries.

## Tasks

1. `_no_js_page()` takes an optional `reduced_motion` (default unchanged, so tests that assert
   motion keep seeing the transition).
2. The three scripts-blocked airline sheet tests opt in with `reduced_motion="reduce"`.
