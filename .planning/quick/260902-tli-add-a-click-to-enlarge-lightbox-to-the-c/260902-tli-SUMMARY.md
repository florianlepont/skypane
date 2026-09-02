---
phase: quick-260902-tli
plan: 01
status: complete
---

# Quick Task 260902-tli: Add a click-to-enlarge lightbox to the companion Airlines gallery

## What was built

Every Airlines gallery card's illustration is now click-to-enlarge, reusing History's already-shipped `<dialog>` lightbox mechanism rather than inventing a second one. The trigger is gated off on narrow portrait viewports entirely in CSS — `panel-lookup.js` receives no logic change.

**Task 1** (`companion/pages/airlines_page.py`, `companion/static/style.css`, `companion/test_status_pages.py`, commit `7bd18c5`):
- Each `.airline-card__image` is wrapped in a `.airline-card__zoom` `<button>` carrying `data-view-panel-src` (byte-identical to the card's own `<img src>`), `data-view-panel-caption` (`CARD_IMAGE_ALT_TEMPLATE % name`), and `aria-label` (`ZOOM_LABEL_TEMPLATE % name`).
- A new `_lightbox_html()` mirrors History's element-for-element, emitting `id="panel-lookup-dialog"` with `class="lightbox lightbox--wide"`, once per page, only when the gallery is non-empty.
- `style.css` adds `.airline-card__zoom` (with equal-specificity `:hover`/`:active` neutralizers to out-rank the base `button` rules), the `.lightbox--wide` variant capped at `ILLUSTRATION_TARGET_WIDTH` (900px, never upscaled), and the gate: `@media (max-width: 959px) and (orientation: portrait) { pointer-events: none }` — `959px` being the exact complement of the file's one existing `960px` breakpoint, not a new magic number.
- Four new checks in `test_status_pages.py`.

**Task 2** (`companion/static/panel-lookup.js`, `companion/layout.py`, `companion/test_view_pages.py`, `companion/test_companion_app.py`, commit `252fa6e`):
- `panel-lookup.js` and `layout.py` get comment-only corrections recording that both pages now render the dialog, and that the script must never itself decide from viewport/orientation whether to open (that gate lives entirely in the stylesheet).
- `test_companion_app.py`'s existing banned-token guard retargeted in place to also forbid `matchMedia`/`innerWidth` — no count change.
- `test_view_pages.py`'s three-file DOM-contract guard widened to assert against a rendered Airlines page too; one new check pins `airlines_page`'s `LIGHTBOX_DIALOG_ID`/`_VIEW_PANEL_*_ATTR` constants equal to `history_page`'s own values (duplicated-not-imported, per the page-module boundary).

## Verification

- `companion/test_status_pages.py`: passes with 4 new checks.
- `companion/test_view_pages.py`: 44/44 (1 new check + widened guard).
- `companion/test_companion_app.py`: 108/108 (retargeted guard, no count change).
- `ruff check companion/`: clean.
- `./scripts/run-all-tests.sh`: `Result: PASS`, zero new failures.
- Live running-service check (throwaway script, not committed): against a real `companion/app.py` instance — `GET /airlines` serves exactly one `#panel-lookup-dialog` and 27 `.airline-card__zoom` buttons (one per card); `GET /static/style.css` carries the `.airline-card__zoom` rule and the orientation gate; `GET /static/panel-lookup.js` returns 200.
- `git diff companion/static/panel-lookup.js`: comment lines only, confirmed.

## Outstanding — Task 3, blocking developer checkpoint

Not self-approved, per the plan's own explicit instruction. Needs a real browser and, for steps 2-3, a real phone (not DevTools emulation — the gate keys on the device's actual reported orientation):

1. **Desktop**: hover shows a zoom cursor; click opens the dialog with the illustration enlarged, correct caption, no distortion; Escape closes it; clicking a different card shows that card's own aircraft.
2. **Phone portrait**: tapping the illustration does nothing at all — no dialog, no flash, no dead-tap feedback.
3. **Phone landscape**: tapping opens the dialog, and the whole dialog fits on screen without the page jumping.
4. **History's own lightbox still works** — it now shares the same script and dialog id, so a regression there is the main risk worth a specific look.
