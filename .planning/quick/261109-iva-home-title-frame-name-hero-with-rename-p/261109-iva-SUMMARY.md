---
phase: quick-261109-iva
plan: 01
subsystem: companion-home
tags: [home, hero, title, rename, css, i18n]
requires: []
provides:
  - "Home hero: picture left, frame name as the page's one h1 with a round rename pencil, state pill, freshness text"
  - "ui_components.icon_link_html, ui_components.title_action_html, page_header(omit_title=), ui_groups.hero(title_html=)"
affects: [companion/pages/home_page.py, companion/static/style.css]
tech-stack:
  added: []
  patterns: ["title-action catalogue component (.title-action)"]
key-files:
  created:
    - companion/pages/home_title.py
    - companion/test_home_title.py
    - companion/test_browser_home_title.py
  modified:
    - companion/pages/home_page.py
    - companion/ui_components.py
    - companion/ui_groups.py
    - companion/pages/components_page.py
    - companion/static/style.css
    - companion/static/nav-dropdown.js
    - companion/i18n_fr/home.py
    - companion/i18n_fr/components.py
    - companion/prefs.py
    - companion/testdata/render_baseline.json
  deleted:
    - companion/pages/home_greeting.py
    - companion/pages/home_rename_row.py
    - companion/test_home_greeting.py
decisions:
  - "The Home h1 lives in the hero; page_header gained an omit_title kwarg so the silent refresh marker and flash slot stay in the header"
  - "Title sizes 48/28/24px are Home-specific; the shared type-scale tests (foundations, overhaul sweep, surfaces) now carve out Home's hero title"
metrics:
  completed: 2026-11-09
---

# Quick 261109-iva: Home title as frame-name hero with rename pencil

The small grey greeting is replaced by the validated hero: the real picture sits to the left at every width (about 104 px at 360 px), and beside it the frame name is Home's one h1 (48 px desktop, 28 px phone, 24 px under 380 px) with a 44 px circular rename pencil on the same line, then a state pill (dot and word) and the freshness text.

## Commits

- d9a0ffb: home_title replaces greeting and Frame name row; omit_title, hero title_html, icon_link_html, title_action_html
- cb7577f, 0974323: fix the principal e-mail comment in prefs.py (the greeting no longer reads it)
- f507ddd: hero CSS (title-action, pill), greeting JS/CSS/i18n removed, Components page and catalogue entry
- 77743a4: pencil is a circular secondary icon link; extra margin so the desktop frame button clears the banner above the hero
- 9f08283: tests and regenerated render baseline

## Deviations from Plan

**1. [Rule 3 - Blocking] Component helper placed in ui_components**
The Components page cannot import a page module, so the generic markup lives in `ui_components.title_action_html` / `icon_link_html`; `pages/home_title.title_html` composes them. Both are listed in the Components catalogue (headers and buttons families).

**2. [Rule 1 - Bug] Banner collided with the desktop frame button**
With the greeting gone, the attention banner started level with the floating frame button. `.home-facts` top margin in the desktop frame-button rule raised to 2xl + sm.

**3. [Rule 1 - Bug] Existing tests encoded the old layout**
Updated: type-scale contracts (foundations, overhaul sweep headings, surfaces) for Home's hero title; notice order (notification, then hero carrying the title); tab-order in the cadence tooltip test (the pencil precedes the info button); page-title-phone (Home h1 visible); overhaul steps (Home identified through the active tab); toast tests now wait for Home's hero entrance animation before measuring the title; French-translation sweep excludes the frame-name title as data like the frame menu name.

**4. Pencil variant** the plan said ghost-like `.btn--icon`; the mockup shows a filled round button, so the link uses the secondary variant with a 50% radius scoped to `.title-action__action`.

## Gate results

- ruff, mypy (29 files), check_function_size (942 functions, none over 80), check_comment_history: pass
- companion/app.py 1483 lines; largest JS file 1486 lines (under 1500)
- Full run `pytest companion stub-server/test_phase47_freeze.py` with the temporary Chromium override: 9029 passed, 3 failed, 3 skipped. The 3 failures (French-translation sweep for the overdue admin Home, two toast no-shift tests) were fixed afterwards (items above) and the affected files re-run: test_browser_overhaul_sweep, test_browser_toasts, test_render_baseline, test_suite_guards, test_home_title, test_browser_home_title, test_phase47_freeze: 1101 passed. No full-suite re-run after those last test-only fixes.
- Screenshots at 1280, 390, 360 (short and long frame names) reviewed against the d2-planche mockup.
- The Chromium override was applied temporarily to the root conftest.py and reverted; it was never committed.

## Known Stubs

None.

## Self-Check: PASSED

Files and commits d9a0ffb, cb7577f, 0974323, f507ddd, 77743a4, 9f08283 exist; home_greeting.py, home_rename_row.py and test_home_greeting.py are gone.
