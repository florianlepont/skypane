# Accessibility and contrast

## Targets, focus, keyboard

- Every control is a 44px target (WCAG 2.5.8 AA is met; the project holds 44px). `.btn` has
  `min-height: 44px`; the sidebar keeps no compact variant; switches, chips, segments, icon
  buttons, list rows and sort menus are 44px or more. An icon-only control with a smaller visible
  box (the 22px `.copy-btn`) draws a 44px hit area with `::before`. The quiet dial handles use
  `inset: -12px` (about 45px measured, because they land on fractional pixels): a shared hit-area
  entry may be overridden upward, never downward.
- **Icon-only buttons** (the Home "i", Account's manage-access key and
  leave-frame door, the Fleet header's personal view and Rename, the Location "Show all of France"
  globe and locate button, the round check on an airline suggestion, copy): each is a 44px target,
  has an accessible name that says what it does and, where several rows repeat it, what it acts on
  ("Manage access: Kitchen"), and a tooltip. The name is the text a screen reader reads; the
  drawn glyph is `aria-hidden`. On a phone a control whose label is hidden by clipping (the Users
  "+ Invite a user" button) keeps its label as the accessible name.
- A bare un-classed `<button type="submit">` still falls to the legacy 30px base rule (AA met, AAA
  not): always use `.btn`.
- **Known exception:** a link inside running text is not a stand-alone control and keeps its text
  height (the "Orly frame" link in a sample sentence on the Components page is 24px tall). A link
  that stands alone is a 44px target, drawn with a `::before` or `::after` when its text box is
  smaller (the Components page's "Back to the index" links; the "Location" link of the Quiet hours
  dialog keeps its 21px text box and a 44px-high `::after`).
- **Known exception:** the hit circles of the Battery chart (about 8px, one per daily average: 80 on the deployed 90-day series,
  `.sparkline-hit`, each named with its date and reading count) are the points of a chart, not
  stand-alone controls. They are a tap and keyboard enhancement (a roving tab stop that visits the
  chart once, arrow keys between points, a tap shows the readout); every value is also in the open
  Readings table under the chart, so no information depends on hitting one. A 44px hit area on points a few pixels apart would overlap its neighbours. If the owner wants the points to be the
  main way to read a value, this becomes a design question, not a style fix.
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
  spoken prefix, the Flights direction is spoken as well as drawn (an arrow-over-runway icon plus a
  visually hidden word), a Fleet tile spells its state in a hidden word, a rarity is a word as well
  as a tint. The battery is a named dot on Account, never a percentage there.
- Decorative drawings are `aria-hidden` with no role: the 404 "empty frame" illustration (inline
  SVG in the page ink, no image, no asset) and the Home cycle ring. The 404 keeps its HTTP status
  and one muted caption on a panel, the same for every caller.
- A dialog opens on a safe control: a destructive confirmation focuses Cancel, the question dialog
  focuses its cross, so Enter never confirms unasked. On a phone the field in a sheet stays above
  the on-screen keyboard.

## Contrast

Executable, not prose. Modules and tests:
- `test-support/skypane_contrast_check.py`: WCAG ratios, `perceptual_distance`, `hue_separation`;
  floors `MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0` and `MIN_SIGNAL_HUE_SEPARATION = 24.0` (accent versus
  error), `WCAG_AA_UI_COMPONENT = 3.0`.
- `companion/test_contrast_check.py`: token pairs, both themes; accent is at least 4.5:1 as text and
  3:1 as a ring on every surface; status and rarity inks pairwise.
- `companion/test_sky_contrast.py`: body text and accent on every sky stop and the glass composited
  over each, both theme cascades; the tab bar fill over white and black.
- `companion/test_browser_contrast_edges.py`, `companion/test_browser_overhaul_sweep.py`,
  `companion/test_browser_french_fit.py`: real pages at 360 and 1280px (EN/FR, light/dark), 44px
  hit-testing across the page content, placeholder (secondary ink at full opacity, 4.5:1) and
  disabled text (3:1); the sweeps also open the Editor, the Fleet list, a frame page, Battery,
  Versions and System. The secondary ink (text at 70%) holds 4.5:1 on a card; a label on a tinted
  panel uses 80%.
- The Copied label on a console copy button uses `--color-status-ok-text` (`#15803D` in Light, 5.02:1 on white; Dark is the status hue, 9.16:1), so the green text meets 4.5:1; the status hue of dots and icons is unchanged (3.30:1 as text on white, so it is not used for text).
- Known, accepted: warn as body text on a white card is 3.19:1 (`STATUS_WARN_ON_CARD_PAIRS`); the state
  is carried by wording and a dot. The accent-versus-status separation floors were designed for a
  terracotta accent; with graphite and ivory they are met trivially and not revisited.
- Inks on the glass: the tab bar and sheets are opaque so labels hold 4.5:1 over a white
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
