---
phase: 68-console-and-companion-visual-improvements
plan: 30
subsystem: companion
requirements-completed: [CON-01]
---

# Phase 68 Plan 30: Leave dialog (R06), yellow tile edge (D-10), preview cache artwork Summary

The shared unsaved-changes dialog is now one question with two equal 48 px answers and a close cross; the light-yellow look tile has a 3 px darker on-screen edge; the frame/chip preview cache key includes the artwork, and previews draw uploaded illustrations.

## What changed
- `ui_modal.choice_dialog_html` (+ `.modal--choice` CSS): title as a question, one sentence, primary then secondary of equal width and 48 px height (row from 700 px, stacked below), quiet action became the cross at the top right (its label is the cross's accessible name), bar behind hidden while the dialog is open. EN: "Leave without saving?" / "Your changes are not saved yet." / "Save and leave" / "Leave without saving". FR: "Quitter sans enregistrer ?" / "Vos modifications ne sont pas encore enregistrées." / "Enregistrer et quitter" / "Quitter sans enregistrer". Same builder on every page (Style, Place, Settings, Fleet frame); the component gallery sample follows.
- D-10: token `--color-yellow-tile-edge` (light #7A6D1D, dark #D9C24A, four token blocks), class `look-pick__card--yellow` on the yellow pairing card, `3px solid` edge on its preview. On-screen only; panel palette and server goldens untouched (`git diff server` empty). Real-panel yellow check stays with the owner (plan 32).
- Owner decision, preview cache: `theme_preview.artwork_stamp()` (resolved illustration file per scene: name, size, plus mtime for uploaded overrides) is folded into `preview_signature`, `frame_preview_signature`, hence cache paths and the `v=` address. Previews now pass `state_dir` to `build_canvas`, so an uploaded override is actually drawn (before, previews ignored overrides). Tests: replacing the artwork regenerates a cached frame preview and chip preview.
- Separate commit (coordinator request): `test_browser_brand_logo` sign-in mark test now asserts mark left edge == h1 left edge (1 px), above the heading, inside the card.

## Deviations
- Existing tests adapted to the intended behaviour: wording in `test_browser_style_leave`/`test_browser_leave_dialog_pages` (cross is checked by aria-label), render stubs accept `state_dir` (`test_preview_cache`, `test_display_looks`), `test_legacy_cache_names_are_unchanged` (signature now carries the artwork stamp; the artwork-less digest stays the legacy one), live-event `cache_path` takes the row (`test_companion_app_02`).
- Dialog sentence is generic (the mock names "Departures colours"; section labels do not map to that wording).

## Baseline
`companion/testdata/render_baseline.json` regenerated once: 68 changed lines (hashes of pages carrying the stylesheet / leave dialog markup).

## Tests run (targeted only)
- Core: every companion test file mentioning theme_preview, preview_images, frame_preview, ui_modal, ui_save_bar, layout_picker, leave dialog, choice_dialog, modal__close, look-pick, dirty-state, frame-preview, theme-preview; test_i18n, test_stylesheet_structure, test_suite_guards, test_structure_guards, test_contrast_check, test_sky_contrast, test_ui_modal: pass (3707 + final 517 after baseline).
- Browser (SKYPANE_REQUIRE_BROWSER=1): all test_browser files mentioning the same, plus test_browser_contrast_edges and test_browser_french_fit: 1519 passed. test_browser_brand_logo, web_app_bar, auth0, nav_alignment, test_brand_logo, test_landing, test_companion_app_04: 189 passed. test_render_baseline passes after regeneration.
- ruff, mypy, check_function_size (max 80), check_comment_history: clean. Not run: full core suite, server golden tests (no server file changed), other browser shards.

## Captures
Mock (light only, EN/FR, phone/desktop dialog and yellow tile) in scratchpad `p30/mock/`; built (390/1440, EN/FR, light/dark) in `p30/built/`.
