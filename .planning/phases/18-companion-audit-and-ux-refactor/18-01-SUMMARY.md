---
phase: 18-companion-audit-and-ux-refactor
plan: 01
subsystem: companion
tags: [companion, ux, ia, audit, navigation, home-page, screens]
requires: []
provides:
  - companion/pages/home_page.py (Home page: status tiles, quick actions, current panel, recent flights)
  - companion/screens.py (screen-type registry declaring per-screen settings groups)
  - layout.NAV_GROUPS / nav_slug() (grouped navigation, NAV_TABS derived)
  - config_page.render(ctx, scope=...) + scope-aware handle_post() (Display / Device pages over one write route)
  - POST /quick/display, POST /quick/quiet-hours (idempotent one-tap switches)
  - layout.local_clock_text() (Paris local time, dated when not today)
affects: [companion/app.py, companion/layout.py, companion/pages/*.py, companion/static/style.css, companion/static/*.js, companion/test_*.py, README.md, .claude/skills/sketch-findings-skypane/SKILL.md]
tech-stack:
  added: []
  patterns: [screen-type registry, scoped form with hidden scope/return_to fields, idempotent state-setting quick actions]
key-files:
  created: [companion/pages/home_page.py, companion/screens.py, .planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md]
  modified: [companion/app.py, companion/layout.py, companion/pages/config_page.py, companion/pages/history_page.py, companion/pages/airlines_page.py, companion/pages/health_page.py, companion/pages/__init__.py, companion/static/style.css, companion/static/panel-lookup.js, companion/static/flash-cleanup.js, companion/static/battery-trend.js, companion/test_companion_app.py, companion/test_config_page.py, companion/test_view_pages.py, companion/test_status_pages.py, README.md]
decisions: [D-01, D-02, D-03, D-04, D-05, D-06, D-07, D-08]
metrics:
  duration: one session
  completed: 2026-09-10
---

# Phase 18 Plan 01: Companion audit & UX refactor Summary

**Six tabs in two groups replace four flat ones; a Home page of widgets answers "is my frame alive, what is it showing, switch it off" without a Save step; Settings is split into an everyday Display page and an Advanced Device page composed from a screen-type registry; 18 of the audit's 46 consolidated findings are fixed in the same pass and the rest are tracked with evidence.**

## What shipped

1. **Audit** — every page, dialog and state screenshotted at desktop and phone width in both themes against a seeded state directory, plus three code reviews. Consolidated ledger in `18-AUDIT.md`; live board in the "SkyPane Companion Audit" artifact.
2. **Navigation** — `layout.NAV_GROUPS`: Home, Display, Flights, Airlines / Advanced: Health, Device. Both renderers draw the "Advanced" label from one helper. Login and the 404 page land on Home. `/settings`, `/history`, `/preview` redirect.
3. **Home page** — `home_page.py`: Frame / Battery (≈ % estimate) / Flight data tiles in plain words; Screen on/off, Quiet hours on/off and Refresh now quick actions; the latest rendered panel; the last five flights.
4. **Display / Device** — `config_page.render(ctx, scope=...)` walks `screens.screen_type()["everyday_groups"]` / `["advanced_groups"]`; hidden `scope` + `return_to` fields; `handle_post()` carries out-of-scope checkboxes forward. The rules editor and manual refresh live on Device.
5. **Fixes** — see 18-AUDIT.md "Fixed in this phase": broken manual-airline image, truncated wake-interval placeholder, single-column chips on phones, save bar off-screen on phones, UTC-only timestamps, raw ISO captions, resolve section rendered twice, SVG class toggling in the sparkline script, query-string loss in flash-cleanup, missing Cache-Control on HTML, several copy fixes.

## Verification

- `scripts/run-all-tests.sh` (PYTHON=system python3, JOBS=4): every harness green except the five checks that also fail on untouched `main` in this root-running sandbox (read-only-directory cases; see 18-AUDIT.md's last section). New checks: companion-app 177→192, config-page 138→142, view-pages 63→65.
- Screenshots re-taken after the refactor at 1280px and 390px, light and dark (scratch only, not committed).

## Deviations from plan

No GSD plan preceded this work; the user asked for an audit and a refactor in one request. The one scope decision made mid-way: French localisation (S-01) was judged too large to bundle and is recorded as the top suggestion instead.

## Next steps

Promote from 18-AUDIT.md in this order: A-25 (field-level save errors), A-32 (lockout reset), A-20 (Health auto-reload), A-40's remainder (per-screen config), S-01 (French).
