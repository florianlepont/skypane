# Phase 61 Plan 55: Foundations of the refined direction Summary

Tokens, meta tags and type scale of owner decision D39 applied app-wide through the shared stylesheet and the three document shells: one pale sky (Light) and one ink gradient (Dark) painted on `html`, `viewport-fit=cover` plus per-scheme `theme-color`, safe-area tokens, graphite/ivory accent, system sans only, one type scale, three radii.

## What changed

- **Black bars on iPhone.** All three document templates (page shell, login shell, interstitial; hence the login, refusal, error, 404/403/unavailable pages) render `viewport-fit=cover` and two `<meta name="theme-color">` tags through one helper (`head_meta_html` in `companion/ui_base.py`). Light `#E7EEF7`, Dark `#12151D`, equal to each theme's `--sky-top`. The theme is rendered server-side from the theme cookie, so an explicit Light/Dark makes both tags carry that theme's colour (no script involved); Auto lets each scheme choose. `html` itself now carries the gradient (`--color-canvas` as floor colour, `min-height:100%`, `background-attachment: scroll`), so the browser bars and overscroll show the sky. New tokens `--safe-top|right|bottom|left` (`env(safe-area-inset-*, 0px)`) are used by the phone header (top inset added to its height), page content (left/right), tab bar, bottom sheets, modal sheet, toasts and the save bar. Every `vh` became `svh` (`dvh` for `min-height`).
- **Background.** Light gradient `#E7EEF7` / `#F1F3F6` / `#F6F3EE`; Dark `#12151D` / `#161A24` / `#1A1F2B`. The four time-of-day skies, `html[data-sky]`, the `html::before` fixed layer, the sky code in `nav-dropdown.js` and the first-paint flash are gone.
- **Accent.** Graphite `#1F2430` (hover `#343B4D`, on-accent white) in Light, ivory `#F2EFE9` (hover `#E2DED5`, on-accent `#14171F`) in Dark, in all four theme blocks. Status, rarity and toast tone colours kept.
- **Type.** `--font-ui` and `--font-display` system stacks as specified; `--font-serif` removed. Page title 700, -0.03em, 30-34px phone / 40-44px desktop; section/card titles 22px/600 in the display face on every page (nested cards, update card, location sheet, legend included; the Collection phone 26px override is removed). Tokens `--font-caption-size` 13, `--font-label-size` 15 (secondary), body 16. Tracked uppercase and positive letter-spacing removed everywhere (about 45 rules). Mono kept for code (`.mono`: callsigns, ids, hashes, URLs); times, counts and readouts moved to a new `.tnum` (tabular numerals) in `ui_time.py`, health rows/readout and the locations coordinates; `.cell-primary/.cell-secondary/.detection-tag` no longer monospace.
- **Radii.** `--radius-control` 14px, `--radius-card` 22px, `--radius-pill` 32px (`--radius-glass` removed). Every `border-radius` maps to one of these, `0`, `50%` or `inherit`.

## Tests

- New `companion/test_shell_meta.py` (served HTML of ten shell variants x auto/light/dark: viewport-fit=cover, both theme-color tags, colours equal the stylesheet's `--sky-top`).
- New `companion/test_browser_foundations.py` (40 cases): page-title size/weight/tracking/face on Home, Flights, Account, Location, Collection, Display at 390 and 1440 in both themes; section titles on tokens; no serif in headings; no tracked uppercase; all computed radii on the tokens (vendored Leaflet controls excluded); forced `--safe-*` values prove header, tab bar, content, sheet pad themselves with the tokens; theme-color follows the cookie theme and the root paints the gradient. Stable over 4 parallel runs.
- Updated in place (none weakened): `test_sky_contrast.py` (two backgrounds, exact stops, graphite/ivory accent, on-accent 4.5:1, ring 3:1 over every stop and the glass; deleted as meaningless: the four-skies-differ, dark-always-night over `data-sky` and the fixed `html::before` tests, replaced by the root-gradient test), `test_browser_sky_motion.py` (hour-band sky tests became any-hour one-background tests; the no-script default-sky test became a no-script identical-background test), `test_browser_overhaul_sweep.py` (readability over light/dark instead of four skies; radius 22px), `test_browser_home_greeting.py` (tab-bar legibility no longer parametrised by sky), `test_contrast_check.py` (the floor-rejects-superseded-error tests now use the old burnt-orange accent explicitly, since the live accent is neutral), heading/label tests (`test_companion_app_01`, `test_status_pages_03/04/05b/06`), `test_ui_modal.py`, `test_status_pages_01/02/04/05b` (`mono` to `tnum`), `test_browser_admin_personal_scope.py` (15px), `test_browser_airline_collection.py`, digests in `test_sign_in_surfaces.py`, `testdata/render_baseline.json`.

## Deviations

- **[Rule 1] Collection French title may wrap to two lines on a 360px phone.** The old 26px override existed to keep it on one line; unifying the page-title scale (30px+) wraps "Collection de compagnies". The header-height budget (one third of the screen) still holds; the assertion `title height < 40` became `< 70` (two lines).
- Nested card titles, the update card title and the location sheet title moved from sans 16/600 to the 22/600 display section title (the audit's "one system" fix); the dedicated nested-heading tests were updated to match.
- Tab labels (11px) and chart axis labels (10px) stay as the two sub-scale exceptions; everything else that was 10-13px is the 13px caption token.
- The brand logo/apple-touch icon keeps its burnt-orange tile (an image asset, not an accent token).
- Surfaces still use legacy beige `--color-secondary` fills and the phone header/tab bar are still the old bars; those belong to the surface and navigation plans that follow.

## Verification

- Full suite `companion test-support stub-server -n 4`: 8156 passed, 4 skipped (the pre-existing root-permission skips), 0 failed, after the last code change. ruff, mypy, comment-history, function-size (931 functions, none over 80) and `test_phase47_freeze` green; `companion/app.py` unchanged at 1473 lines.
- Before/after screenshots (Home, Flights, Account, Location, Collection; phone 390 and desktop 1440; Light and Dark, 40 files): `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots55/<page>-<phone|desk>-<light|dark>-<before|after>.png`.

## Not verifiable without a real iPhone

Headless Chromium has no notch and no Safari toolbar, so `env(safe-area-inset-*)` is 0 and the Safari bar tinting is not observable. Verified instead: the served HTML carries `viewport-fit=cover` and both `theme-color` tags, the stylesheet builds every padding from `--safe-*` (proved by forcing those tokens) and `--safe-*` are `env()` values, and the root element paints the gradient. Not verified: that iOS Safari actually samples `theme-color`/`html` background as expected (iOS 26 may additionally tint from fixed edge elements, which the unchanged square header/tab bar still are), the overscroll colour, and the SF Pro faces (screenshots use the Linux Inter-like fallback).

## Self-Check: PASSED
