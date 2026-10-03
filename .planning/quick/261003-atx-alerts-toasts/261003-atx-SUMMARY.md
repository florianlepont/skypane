---
quick_id: 261003-atx
slug: alerts-toasts
date: 2026-10-03
branch: claude/alerts-toasts
commits: [2dceab39, a004b268, f72cecec, 2a7811ad]
---

# Quick 261003-atx: alerts as toasts (Direction B) Summary

Every flash and persistent alert is now one toast component with five tones
(success, info, warning, error, pending), a per-tone glyph, a title/detail
split at the message's " — ", an optional action and a no-script dismiss link;
flash toasts float with scripts and stay in flow without them.

## What shipped

- `companion/flash.py`: `FLASH_TONES` for all 41 flash keys; `FLASH_ROLES`
  derived from it (alert for warning/error). `flash_toast_html()` builds the
  toast: dismiss href = request path minus `flash`/`rule` (other params kept,
  never off-site), Undo (real POST of the opposite state) for the screen,
  quiet-hours and LED switches, "See Health" for a closed coverage gap, a bin
  glyph for "calendar disconnected". The "Saved" detail is no longer
  lower-cased.
- `companion/ui_components.py`: `toast_html()` and helpers; `flash_banner()`
  and `anomaly_banner()` now emit toasts. New FR strings (tone prefixes, dismiss,
  Undo, See Health) in `companion/i18n_fr/common.py`.
- Persistent docked toasts: Health anomaly (pills kept) and source outage
  (section with its h2), Update rollback, Home attention row (warning, or error
  when a shared health state is error). Refresh selectors retargeted in
  `ui_nav.py` and `freshness.js`.
- `companion/static/toast.js` (new, global): in-place dismiss (click/Enter/
  Escape, focus restored to `<main>` only if it was inside), success/info
  auto-hide over `--motion-toast-dwell`, paused on hover, focus and hidden
  document. Warning, error and pending are never marked to auto-hide.
- Quick-switch toast merged: the shell renders a translated error toast in a
  `<template>`; `quick-switch.js` clones it into the existing empty live region.
  It no longer auto-hides (error rule). The `data-quick-failed-text` body
  attribute is gone.
- `style.css`: toast tokens for both themes, docked and floating forms, a
  phone grid layout, floating under `@media (scripting: enabled)` (first paint,
  no shift), above the tab bar under 960 px. The motion budget's header
  documents `--motion-toast-dwell` as the one exception. `.banner*` is removed
  except `.banner__pill`, which is still used by row and badge pills.

## Deviations from the mockup and brief

- **Pending never auto-hides.** The mockup hid it after 6 s, but the owner
  guardrail wins. Warning is `role=alert`, also per the guardrail (the mockup
  had `status`).
- **Spoken tone wording.** The tone wording is a visually-hidden prefix
  ("Error:", "Pending:" / "Erreur :", "En attente :"). Visibly, tone shows
  through the glyph shape and the message text. There is no separate visible
  tone word, which matches the mockup.
- **Reduced motion.** No third reduced-motion block was needed. The existing
  global override reduces the slide and the hairline to 0.01 ms, so the toast
  just appears and the hairline is never seen. The motion-budget test instead
  pins the token set and that the dwell token drives only the timer hairline.
- **Floating trigger.** Floating uses `@media (scripting: enabled)`, not the
  `.js` class. A class added by a deferred script would make the toast jump
  out of flow after first paint.
- **Undo scope.** Undo only appears on the no-script and redirect paths. With
  scripts the switches use fetch/204 and show no success flash at all.

## Verification

- Full suite: `./scripts/run-all-tests.sh` → 3657 passed, 8 skipped, coverage
  95.23% (floor 93%). This run came after the baseline regeneration.
- A clean origin/main export had 7 failures before this change, all git-only
  tests that cannot run from an export.
- ruff, mypy, `check_comment_history.py check` and
  `check_function_size.py check --max 80 server stub-server` are all clean.
- `render_baseline.json` was regenerated after checking the diff: 45 changed
  leaves, all intended. They are the new sprite symbols, the toast template
  and live-region class, the `toast.js` tag and its unauthenticated route, the
  removed body attribute, and the flash and anomaly toast markup.
- Screenshots (not in repo) are in `scratchpad/shots-atx/`: every tone at
  1280/390, light/dark, EN/FR, with and without JS, plus the long message,
  persistent Health/Home and the quick-switch failure.

## Self-Check: PASSED
