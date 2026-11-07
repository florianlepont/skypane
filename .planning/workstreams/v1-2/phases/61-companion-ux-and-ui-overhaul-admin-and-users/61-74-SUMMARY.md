# Phase 61 Plan 74: Motion M7 and M9 Summary

Draggable phone bottom sheets (M7) and the swipeable floating toast (M9), ported from the demos onto the real pages. Owner decision D43.

## What changed

- **M7 (`static/modal.js`, `style.css`):**
  - Every `dialog.modal` gets a `.modal__grabber` hit area (role img, aria-label "Drag down to close", read from `<body data-sheet-grab-text>`). It is shown only below 700px and sits over the drawn pill.
  - Pointer Events start a drag only on the grabber or on the non-interactive part of `.modal__head`. `touch-action: none` is set only on those two, so the body scrolls natively.
  - The sheet follows the pointer in whole pixels (upward drags are damped 1/6), through the CSSOM transform.
  - Release past 90px, or a downward flick faster than 0.5px/ms, slides the sheet off and then calls the dialog's own `close()`. That is the Close link's path: the same `close` event, focus return and hash clean-up, with no form submitted.
  - Otherwise the sheet springs back (`--motion-spring`).
  - State is the `data-sheet-state` attribute (dragging, springing, closing); the transitions live in the stylesheet.
  - Reduced motion: no slide and no spring; the close or the return is instant.
  - Desktop dialogs are unchanged; the focus trap and Escape are untouched.
- **M9 (`static/toast.js`, `style.css`):**
  - The floating toast enters with a spring drop (`skypane-toast-in`, 16px, `--motion-spring`).
  - A sideways drag, mouse or touch, moves and fades it. Released past 80px, or on a flick, it slides off and is removed; otherwise it springs back.
  - The auto-hide timer and its hairline pause for the gesture through a new "swipe" pause reason, and resume on release.
  - The dismiss and action controls, Escape, auto-dismiss and the no-JS flash are unchanged.
  - `touch-action: pan-y` on floating toasts only.
- **Strings:** `common.sheet_grabber` (EN in `ui_nav.py`, FR in `i18n_fr/common.py`), rendered on `<body>` by `ui_shell.py`.
- Render baseline and the sign-in digests updated in place.

## Tests

New `companion/test_browser_motion_sheets.py` (17 tests, 4 parallel runs of the file all green): drag past 90px closes and returns focus to the trigger (360 and 390); a flick closes; a short drag springs back and stays open; a drag in the body does not move the sheet; the heading drag closes while the Close link works; Tab loops without landing on the grabber and Escape returns focus; reduced motion closes and returns instantly; a wide screen has no grabber and ignores a heading drag; the French label; a drag-closed Invite dialog posts nothing; the toast settles, swipes away, springs back, pauses its dwell bar during the gesture, keeps its close button and still swipes under reduced motion.

## Deviations from Plan

- `animation: none` is forbidden by the stylesheet motion-budget guard, so toast.js sets `style.animation = "none"` through the CSSOM at swipe start instead.
- Mouse-down on the grabber moves focus off the dialog title into the dialog (native behaviour); focus stays inside the dialog and returns to the opener on close.
- The sheet drag does not fade the backdrop.

## Screenshots

`scratchpad/shots74/` (360px sheet at rest and mid-drag, light and dark).

## Self-Check: PASSED
