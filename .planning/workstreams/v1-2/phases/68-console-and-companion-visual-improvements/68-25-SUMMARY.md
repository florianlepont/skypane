---
phase: 68-console-and-companion-visual-improvements
plan: 25
subsystem: companion
tags: [foreign-frame-marker, back-to-fleet, french-nav, render-baseline]
requires: ["68-34", "68-03"]
provides:
  - "Strong foreign-frame marker (accent slab, eye icon, sticky) built as approved (R35, D-21)"
  - "Back to Fleet leads to /fleet?frame=<id of the viewed frame> (R12, D-06)"
  - "French label of the Airlines page is Compagnies in tab bar, sidebar, More sheet and page title"
key-files:
  modified:
    - companion/ui_components.py
    - companion/ui_shell.py
    - companion/ui_base.py
    - companion/static/style.css
    - companion/static/style-place.css
    - companion/i18n_fr/nav.py
    - companion/i18n_fr/components.py
    - companion/pages/components_page.py
    - companion/testdata/render_baseline.json
decisions:
  - "The markup lives in ui_components.frame_notice_markup (catalogued on the Components page, Foreign-frame marker); ui_shell.frame_notice_html keeps the scope predicate and builds the href from device_scope.current_device()."
  - "Two icons added to the sprite: icon-eye and icon-chevron-left."
  - "The marker is one <div> (spans inside), so the existing parity regexes keep working."
  - "No element id was added: the rel=expect hint points at the carried-strip end marker, not at the notice, so there was no id to keep."
metrics:
  completed: 2026-11-19
---

# Phase 68 Plan 25: Foreign-frame marker and Back to Fleet Summary

Variant A of `68-MOCKUP-frame-banner.html` (graphite slab in light, ivory in dark, amber 3 px edge, eye icon, 16 px text with the e-mail in bold, inverse 44 px Back to Fleet button with a back chevron, sticky) is built in the single builder; Back to Fleet now returns to the viewed frame.

## What was built

- `ui_components.frame_notice_markup(email, href)`: e-mail and href escaped; one `<div>`. `ui_shell.frame_notice_html` shows it only to an administrator on a personal page of a frame they neither own nor co-manage; href is `/fleet?frame=` plus the percent-encoded id of `device_scope.current_device()` (a `?frame=` in the request is ignored), `/fleet` with no device. No `app.py` change (1490 lines).
- Wording: EN "You are viewing {e-mail}'s frame" / "Back to Fleet"; FR "Vous consultez le cadre de {e-mail}" / "Retour à la flotte".
- CSS: slab bleeds to the page padding, sticky under the status bar, wraps (never ellipsis), button centred 44 px opaque. On desktop it keeps its button clear of the floating frame button, and that button is made opaque over the slab. On the full-bleed Location page it spans the width itself, starts below the floating app bar on phones, and the frame button sits below it on desktop.
- French navigation: `nav.airline_collection` is "Compagnies" (tab bar, sidebar, More, title). The six-tab bar fits at 320, 360 and 390 px (tab bar tests, French fit tests). English stays "Airlines".
- Components page: new state "Foreign-frame marker" / "Repère de cadre étranger" in the Messages family.

## Deviations from Plan

- [Rule 3] The plan lists no `ui_base.py` / `ui_components.py` / `style-place.css`; the eye and back glyphs, the catalogue-compatible helper location and the Location page full-bleed fix needed them.
- [Rule 1] Tests left stale by plan 34 (`Mon cadre`) fixed in `test_browser_console.py`.

## Design-system divergences

- Phone slab text aligns with the page content (24 px side padding) where the mockup uses 16 px, because the real content column is 24 px; at 360 px and 390 px the line wrapping (message, then the button on its own row) equals the mockup.
- Desktop: the Back to Fleet button sits left of the frame button (reserved space) instead of at the far right; the frame button is drawn opaque over the slab. The mockup has no frame button.
- The mockup draws no app bar; the real marker sits under it (phones) and scrolls up to the sticky position under the status bar.
- Slab flush right edge on desktop reaches the window edge (the main column has no right panel edge).

## Open decisions for the owner

1. Other French text still reads "Airlines" (separate ids, not changed): `airlines.back_to_airlines` ("← Retour à Airlines"), `airlines.collection_count` ("Airlines : %d"), `airlines.table_caption`, and the French flash/help sentences "page Airlines" (`i18n_fr/common.py`). Suggested: "Retour aux compagnies", "Compagnies : %d", "page Compagnies".
2. No other untranslated English navigation label found (Style, Console are French words; Fleet is Flotte).
3. `test_companion_app_01::test_icon_sprite_integrity` (known failing, count 55 vs now 59) was not touched.
4. Open pull requests: #483 (this phase) and #481 (dependabot playwright); none touches the files here.

## Captures

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p25/`: `mock_banner_{home,flights,place,style,airlines,longmail}_ph_*`, `mock_banner_home_dk_*`; `before_*` / `after_*` for home, flights, airlines, style, location at phone 390 (`ph`) and desktop 1280 (`dk`), EN and FR, light and dark; `*_scroll_*` (scrolled, sticky) and `*_fleetback_*` (Fleet after Back to Fleet). Side-by-side compared; differences fixed (desktop overlap, dark frame button, Location page overflow and app bar overlap).

## Verification

`SKYPANE_REQUIRE_BROWSER=1` (server/.venv): scope, parity, components, sweep, contrast edges, i18n, structure and suite guards, French fit, tab bar, nav, airline pages, console, status pages: 1841 passed first run, 2 stale tests fixed and re-run green; access matrix, render baseline, phase 47 freeze, golden render, stylesheet structure: green. Only `test_companion_app_01` (2, known) fails. ruff, mypy, function size (80), comment history clean; JS unchanged (max 1227).

## Self-Check: PASSED
