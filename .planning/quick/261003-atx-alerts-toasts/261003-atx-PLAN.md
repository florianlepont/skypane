---
quick_id: 261003-atx
slug: alerts-toasts
date: 2026-10-03
branch: claude/alerts-toasts
---

# Quick 261003-atx: alerts as toasts (Direction B)

## Goal

Replace the flat `.banner` flash bars with the approved Direction B "Toasts"
(`scratchpad/sketches-alerts/alerts-B*.png`, `alerts-B.html`): a compact
inverted-surface toast with a tone glyph, bold title and muted detail (split
at the message's ` — `), an optional action and a dismiss link. With scripts
it floats top-centre on desktop and above the tab bar on a phone, out of flow;
without scripts the same markup stays an in-flow banner. Persistent state
surfaces use the docked variant of the same component.

## Owner guardrails (binding)

1. Success/info toasts auto-hide after ~6 s (enhancement only), paused on
   hover, focus or hidden document. Warning, error and pending never auto-hide.
2. prefers-reduced-motion: no sliding, no timer hairline.
3. Health anomaly, Health source outage, Update rollback and Home "needs
   attention" are docked, never floating, never dismissable.
4. Merge `.quick-toast` (quick-switch.js) into the same component.
5. Motion budget: a third token for the toast dwell is a documented,
   pinned exception (stylesheet header + test), not a loosened test.
6. Strict CSP: no `style=""`; hairline drawn by class + CSS animation.
7. Focus never moved; dismiss/action keyboard reachable; error = role=alert.
8. No-JS: flash after POST renders in flow; dismiss link reloads without
   `?flash=`/`rule=`.

## Tasks

1. **Tones + markup** (`companion/flash.py`, `companion/ui_components.py`,
   `companion/ui_base.py`, `companion/page_context.py`, `companion/app.py`,
   `companion/ui_shell.py`, `companion/i18n_fr/common.py`):
   `FLASH_TONES` (success/info/warning/error/pending) for every flash key,
   `FLASH_ROLES` derived from it; `toast_html()` / `flash_banner()` /
   `anomaly_banner()` emit the toast; title/detail split of the translated
   text; visually-hidden tone prefix; dismiss href computed server-side from
   the request path; optional actions (Undo for the three quick switches,
   See Health for the stale coverage gap); new sprite glyphs; quick-toast
   becomes a server-rendered `<template>` cloned into the live region.
2. **Persistent surfaces** (`companion/pages/health_page.py`,
   `companion/pages/update_page.py`, `companion/pages/home_page.py`,
   `companion/ui_nav.py`): docked toast variant, refresh selectors retargeted.
3. **Styles + script** (`companion/static/style.css`, new
   `companion/static/toast.js`, `companion/static/quick-switch.js`,
   `companion/static/flash-cleanup.js`, static route wiring): tokens for the
   inverse surface and tone inks in both themes, floating placement under
   `@media (scripting: enabled)`, docked fallback, the toast-dwell token and
   its own reduced-motion block, timer/pause/dismiss behaviour.
4. **Tests**: retarget every `banner` assertion; behaviour tests (tone/role
   per key, split, dismiss link, no style attributes, EN/FR, sticky tones);
   browser tests (floating position desktop/mobile without layout shift,
   auto-hide timing and pauses, sticky error, reduced motion, keyboard
   dismiss, no-JS fallback); motion budget and contrast pairs updated;
   render baseline regenerated after inspecting the diff.
5. **Visual verification**: Playwright screenshots (1280/390, light/dark,
   EN/FR, every tone, JS and no-JS, long message, persistent banners) under
   `scratchpad/shots-atx/`, compared with the mockup.
6. **Gates**: full suite, ruff, mypy, comment-history, function-size.
