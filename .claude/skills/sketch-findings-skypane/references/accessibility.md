# Accessibility and contrast

## Targets, focus, keyboard

- Every control is a 44px target (WCAG 2.5.8 AA is met; the project holds 44px). `.btn` has
  `min-height: 44px`; the sidebar keeps no compact variant; switches, chips, segments, icon
  buttons, list rows and sort menus are 44px or more. An icon-only control with a smaller visible
  box (the 22px `.copy-btn`) draws a 44px hit area with `::before`. The quiet dial handles use
  `inset: -12px` (about 45px measured, because they land on fractional pixels): a shared hit-area
  entry may be overridden upward, never downward.
- A bare un-classed `<button type="submit">` still falls to the legacy 30px base rule (AA met, AAA
  not): always use `.btn`.
- Focus: a global 2px outline at 2px offset (`:focus-visible`), accent coloured, visible on every
  control type; a dialog container draws none (its controls do). Tap targets taller than the box use a
  pseudo-element so the ring stays tight. Cancel on the Save bar returns focus to the last changed
  control; menus take arrow keys; a dialog closed by keyboard keeps the keyboard ring.
- No-script floor: navigation, the More panel (`<details>`), the Save bar, filters and forms all work
  without JavaScript; scripts only enhance.

## Structure

- One `h1` per page; a hidden "Frame state" `h2` follows it; each Style tab has its own title.
  Headings below the title: section label (13px), card title (17px), sub-page title (22px).
  `companion/test_page_structure.py` pins this.
- Landmarks: one "Primary navigation" `nav` in the tree at a time; `aria-current="page"` on the
  current entry; `aria-expanded`/`aria-haspopup` on menus; a skip link; toasts use `role="status"` or
  `role="alert"` and are never announced by moving focus.
- Colour is never the only signal: status dots carry a text label, toasts a glyph and a hidden
  spoken prefix, the Flights direction is spoken as well as drawn.

## Contrast

Executable, not prose. Modules and tests:
- `test-support/skypane_contrast_check.py`: WCAG ratios, `perceptual_distance`, `hue_separation`;
  floors `MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0` and `MIN_SIGNAL_HUE_SEPARATION = 24.0` (accent versus
  error), `WCAG_AA_UI_COMPONENT = 3.0`.
- `companion/test_contrast_check.py`: token pairs, both themes; accent is at least 4.5:1 as text and
  3:1 as a ring on every surface; status and rarity inks pairwise.
- `companion/test_sky_contrast.py`: body text and accent on every sky stop and the glass composited
  over each, both theme cascades; the tab bar fill over white and black.
- `companion/test_browser_contrast_edges.py`, `companion/test_browser_overhaul_sweep.py`: real pages
  at 360 and 1280px (EN/FR, light/dark), 44px hit-testing across the page content, placeholder
  (secondary ink at full opacity, 4.5:1) and disabled text (3:1).
- Known, accepted: warn as body text on a white card is 3.19:1 (`STATUS_WARN_ON_CARD_PAIRS`); the state
  is carried by wording and a dot. The accent-versus-status separation floors were designed for a
  terracotta accent; with graphite and ivory they are met trivially and not revisited.
- Inks on the glass: the tab bar and sheets are nearly opaque so labels hold 4.5:1 over a white
  picture or a black card scrolling beneath.

## Forms and HTTP

- HEAD answers like GET without a body and without leaking a protected page; PUT, DELETE, PATCH and
  OPTIONS answer 405 with `Allow` and the app's own page (`companion/test_http_methods.py`).
- Every state-changing form posts with a CSRF field; the upload token travels in the body, not the
  address; a refused pairing code is kept for one showing in a 2-minute cookie (`sp_pair_code`); an
  expired page offers "Open the page again".
- Forms have native submit with a no-script fallback; a double submit is guarded
  (`submit-guard.js`); destructive actions ask (`confirm-submit.js`, role change confirmation).

## Viewports

Minimum 360px (320px out of contract; keep the existing 320px tab-bar assertion, it is cheap).
Reference devices: Android 360px, iPhone 390px. No horizontal page scroll; long values truncate
with an ellipsis or wrap; French wraps in a detail line instead of clipping. Tests:
`companion/test_browser_french_fit.py` and the `*_ux_*` browser tests.
