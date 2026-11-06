# Phase 61 Plan 75: Motion M6 and M10 Summary

The Flights picture dialog shows the picture alone and grows the tapped thumbnail into it (M6), and a newly seen airline card flips in once per airline and per user (M10). Owner decision D43.

## What changed

- **M6 (`static/panel-lookup.js`, `style.css`, `pages/history_page.py`):**
  - The Flights picture `<dialog>` carries `lightbox--picture`. It has no card: transparent background, no border, no padding, no glass or backdrop filter, the same markup contract (id, aria-label, `img.lightbox__image`, caption, `[data-view-panel-close]`).
  - The image takes the frame-picture radius token and `--shadow-pop`; the caption and the Close button sit under it over the scrim (Close is a solid 44px button).
  - Opening runs a same-document View Transition: the thumbnail and the large picture share the name `skypane-flight-pic` through the server-side class `.vt-pic`, moved between the two elements by script (never inline style). Closing (button, backdrop click, Escape via `cancel`) runs it in reverse and the dialog's own `close()` returns focus to the thumbnail.
  - Without `startViewTransition`, under reduced motion, or for a thumbnail not on screen, the dialog opens and closes exactly as before. Focus trap, drag-to-close and aria labels are untouched.
  - Home's recent-flights rows open no picture dialog (they link to Flights), so Home has nothing to animate; only the Flights list and table use the shared dialog.
- **M10 (`static/motion.js`, `pages/airline_collection_page.py`, `style.css`):**
  - A card that is seen and carries the existing New marker gets `data-unlock="<slug>"` on its `<li>`; the grid carries `data-unlock-scope` (the signed-in email, else "shared").
  - "Played once" is a list in localStorage (`skypane.unlocked.<scope>`), read and written in try/catch; if storage is unusable nothing animates (no replay on every load). The existing server-side New state is time based and has no per-user "viewed" marker, so the storage list is what makes it once-only.
  - When the card is 60% on screen: a 560ms `rotateY(90deg -> 0)` flip with overshoot, a glint sweep and eight sparks (Web Animations API, removed when finished).
  - Without JS or under reduced motion the card is in its final state (no transform, no animation).
- **Stylesheet fixes (pre-existing, found by `test_stylesheet_structure`):** the "one rule per selector per context" test already failed at the previous commit (`.frame-menu__button`, `.filter-bar__search`, `.is-loading::after` in reduced motion, `.tab-bar`, `.tab-bar__link` in the phone media query were declared twice by the motion plans). Merged each pair into one rule with identical cascade intent.
- Colours: the glint uses `--color-switch-thumb`; no colour literals added.
- Render baseline updated. The sign-in digests and goldens needed no further change.

## Tests

New `companion/test_browser_motion_unlock.py` (9 tests, 4 parallel runs of the file green): picture dialog has a transparent background, no border or padding, the frame-picture radius, a centred image with nothing around it, in light and dark at 360 and 1280, and Escape and the Close button both close it with focus back on the thumbnail trigger; focus stays trapped and the dialog is labelled; the new card plays the flip and sparks first time, not after reload; reduced motion and no-JS show it flipped with no animation. `test_browser_flights_cards.py` waits for the (now transition-based) Escape close instead of reading it synchronously.

Screenshots in the session scratchpad `shots75/` (picture dialog, light and dark, 360 and 1280).

## Deviations from Plan

- [Rule 1 - Bug] Merged five duplicate stylesheet selector rules left by earlier motion plans (see above).
- Home recent flights: no picture dialog exists there, so M6 applies to the Flights list and table only.

## Known Stubs

None.

## CI fixes

Full-suite CI on the pull request failed 13 tests after plans 61-72 to 61-75 (which ran targeted tests only).

Code fixed (product was wrong or inconsistent):
- `test_style_css_honours_the_motion_budget`: the picture-transition rules had added a third reduced-motion `reduce` block and a second `no-preference` block; merged into the existing blocks (the stylesheet keeps 2 and 1).
- `test_both_dialogs_fade_in_and_leave_nothing_behind[history]`: the picture dialog had `transition: none` and fixed opacity, so it did not fade; the overrides are removed and it fades and zooms in like every dialog. `panel-lookup.js` now opens the dialog synchronously and only the shared-name handover runs inside the view transition (the dialog was previously opened in an asynchronous callback).
- `test_flights_mobile_cards_each_carry_a_picture_action_at_390_and_360`: same cause (open was asynchronous, passed locally by timing); fixed by the synchronous open above.

Tests updated (they pinned an old structure a validated plan changed, or read mid-animation):
- `test_tab_bar_labels_are_legible_and_uncramped[360, 390]` and `test_the_admin_first_cell_has_the_shape_of_the_other_cells`: `.tab-bar > *` now counts the sliding-pill element as a cell; the selector excludes `.tab-bar__slider`.
- `test_the_space_switch_stays_first_set_apart_and_the_active_item_is_an_inner_pill` (4 params): same selector fix; the active fill, radius and box are read on the slider once placed (the active link's own pill is transparent by design), after waiting for it.
- `test_desktop_toast_floats_top_centre_without_moving_the_page[error, pending]`: positions were read during the spring entrance drop; the helper now waits for the entrance animation to finish (passed locally by timing).
- `test_view_transition_names_are_unique_on_every_route`: `skypane-flight-pic` added to the pinned names with no route (the `.vt-pic` class sits on one picture only while the transition runs).
