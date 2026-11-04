# Phase 61 Plan 38: Quiet-hours dialog as sketch C Summary

Owner decision D27 (W8): the Home quiet-hours dialog is redesigned as preset cards plus Start/End tiles, with the same form, route and validation.

- **Cards (`quiet_hours_dialog_body_html`, `companion/settings/quiet_hours.py`):** Night 23:00 – 07:00, Day 08:00 – 18:00, "Always active" ("Never rests"). Each is a `type="button"` with a round icon (new `icon-sun`, `icon-infinity` in the sprite, existing `icon-moon`), name, hours and a check on the selected card (`aria-pressed`, accent border and wash). Server-rendered selection: a window card when quiet hours are on with exactly its hours, "Always active" when off.
- **Tiles:** Start and End are filled tiles (small caps label over a 28px time) whose whole surface is the `<label>` of the same `type="time"` input (same ids, names, step 300, error wiring). Rule and "Or choose your hours" label above; footer sentence "Time zone: {zone}. Change it in Location and detection" as in the mockup.
- **Behaviour (`static/dirty-state.js`):** card taps fill the fields as before; a window card now also turns quiet hours on (picking Night after Always active would otherwise save "off"); `aria-pressed` is re-synced after a tap and on any input or change in the form, so hand-edited hours leave no window card selected.
- **No script:** the cards sit in a `.js-gate` wrapper (hidden without script, they are inert); the "Use quiet hours" checkbox stays the visible control without script and is `display:none` with a script (cards drive it, so it is out of the tab order). Same form fields, same `POST /quick/quiet-hours/window`, same validators.
- **Strings:** new `home.quiet_intro`, `home.quiet_presets_label`, `home.quiet_always_active`, `home.quiet_never_rests`, `home.quiet_or_choose`, `home.quiet_hours_zone_link`; `home.quiet_hours_zone_sentence` reworded (EN in code, FR in `companion/i18n_fr/home.py`).
- **Tests (adapted in place, none weakened):** `test_quiet_hours_modal.py` (cards, details, pressed state, tiles, zone sentence, French), `test_browser_quiet_hours_modal.py` (44px on cards and tiles in both themes at 360 and 1280, EN/FR; card selection follows fields; Always active clears the switch and Night re-enables it; accent border, check, large time, filled tile, checkbox hidden in both themes; no-script shows the checkbox and hides the cards; save-off now via the Always active card), `test_browser_ux_quiet_wake.py` (card selector). `render_baseline.json` regenerated; `test_sign_in_surfaces.py` digests regenerated deliberately (the icon sprite is part of the shell).
- **Docs:** `61-UI-SPEC.md` section 10 and the strings table.

## Deviations from Plan

- The "Use quiet hours" checkbox is hidden with a script rather than kept visible (the sketch shows none); it remains in the form for the no-script floor.
- Card label is "Always active" per D27 (the Config page keeps "Always on").

## Self-Check: PASSED
