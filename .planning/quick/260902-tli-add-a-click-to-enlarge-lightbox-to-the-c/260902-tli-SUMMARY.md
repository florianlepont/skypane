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

## Task 3 checkpoint — developer feedback and corrections (commits `d6b6da2`, `b401eb7`)

The developer's own live-device test (Chrome, then a real phone via a tunnel) found three real issues, all fixed on the same pass:

1. **Note copy was meaningless.** The original wording ("Shown at the shared 900x263 frame every illustration is normalized to...") named an implementation detail no viewer needs. Reworded once, then the reworded version was ALSO rejected — no note is wanted here at all. `LIGHTBOX_NOTE` is now the empty string; the `<p class="lightbox__note">` element still exists (required by `panel-lookup.js`'s shared guard clause) but collapses to zero visible space via a new `.lightbox__note:empty { display: none; }` rule.
2. **Dark-mode text was illegible.** A native `<dialog>` promoted to the top layer via `showModal()` does not reliably inherit `color` from its DOM ancestors — every browser tested fell back to UA-stylesheet black regardless of the page's theme, so `.lightbox__caption`/`.lightbox__note` (which set no color of their own) rendered black-on-near-black in dark mode. Fixed by declaring `color: var(--color-text)` explicitly on `.lightbox` — benefits History's own dialog too, which had the same latent bug.
3. **Misread the original spec — a real design correction, not just a bug.** "En mode paysage" meant the enlarged view should present the illustration in a landscape-style (wide) layout, which `.lightbox--wide`'s own sizing already provides — not that the click should be gated behind the device's physical orientation. The implemented `@media (max-width: 959px) and (orientation: portrait) { pointer-events: none }` gate disabled the trigger on the developer's real phone in BOTH orientations. Removed outright; the trigger now works unconditionally at every viewport/orientation, and the existing wide-dialog sizing already handles presentation correctly on a narrow phone.

All three verified together in one live screenshot: real running `companion/app.py`, 375×812 portrait viewport, dark color-scheme — dialog opens, text legible, no note gap, illustration displayed wide.

`companion/test_status_pages.py`: 116/116 (the stylesheet-contract check rewritten in place to pin the gate's *absence* rather than its presence, so it cannot silently return). `ruff check companion/`: clean. `scripts/run-all-tests.sh`: fully green throughout.

## Task 3 checkpoint — approved

Developer approved on re-check, via the same real-phone tunnel used for the earlier `260902-l9w`/`260902-qkm` checkpoints. All three fixes confirmed working on a real device: click opens the dialog in every orientation, dark-mode text is legible, no note gap.
