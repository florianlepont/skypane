# Phase 68 Plan 49: Owner feedback of 2026-11-23 Summary

Removes useless help text on Rename and Style and examines four visual cases from the owner's Notion page: three real defects fixed (picture fade on tab switch, picture box margin, info glyph offset) and one normal case.

Captures: `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p49/{before,after}/` (390, 1440, 844x390, 926x428; EN/FR; light).

## Per item

**a. Rename** (commit 012466c0). Removed the standing "Up to 40 characters." help and the purpose sentence ("The name you see ... not shown on the frame") and their French strings (`frame_name.help`, `frame_name.purpose`). `maxlength=40` stays; the limit now shows only as the existing validation error ("Enter a name of 1 to 40 characters."). Rename-as-dialog: NOT done. Rename is a full page (`/devices/<id>/frame/name`) reached by link from three places (Home title pencil, Account frames list, access card), with its own Save bar, return_to allow-list, unsaved-changes guard, flash after redirect and POST/error re-render as a page. A dialog on desktop and bottom sheet on phones means a dialog per entry point (or one shared fragment), a sheet-open/error-reopen protocol on POST refusal, return_to and dirty-guard rewiring, and a no-script fallback page kept alongside: several files and a new test surface, not small. Owner decision needed. Test: new `test_the_rename_page_carries_no_standing_help_or_purpose_sentence` (EN/FR).

**b. Style page** (commit d017a8ac). The two sentences were `look.layout_help` (Layout card) and `look.pairing_help` (colour pickers, departures panel and calendar picker). Removed both renderings, both Messages, both French strings, and the CSS rule `.layout-card__picker > .section-caption` only they used. The position-mode sentence (`look.position_help`) is a different sentence and stays. Tests adapted: `test_personalisation_layout.py` two tests that asserted the sentence ("says_when_it_repaints" renamed `..._without_a_redraw_sentence`, and the French card test) now assert it is absent.

**c. Home card without the big word (VOE1682).** Normal case, no code change. The big word is part of the archived picture the server draws, not of the Home card. In every giant layout (A, B, C, A diagonal, landscape) and every colour pairing the lettering is always drawn: city (origin when arriving), else the airline name, else "Unknown flight" (checked by rendering a Volotea arrival with no route, with an origin, and with an empty route; already pinned by `server/test_giant_compose.py`). The only picture with no big word is the classic layout, which by design omits line 1 when no city is known and shows the airline small. So a card on white with only the aircraft is a picture rendered under the classic layout (the frame's layout was changed after it was archived, or the frame was on classic then). The cause cannot be confirmed without the owner's archive entry. Nothing invented: Home itself shows airline/route/callsign beside the picture. Owner decision: whether archived pictures should be re-rendered after a layout change (not planned).

**d. Style tab blink** (commit 31b1874f). Real defect. Preview URLs, cache headers (immutable, content address with artwork stamp) and no extra network fetch were already correct (existing tests). The blink came from `motion.js`: the blur-up reveal (blur 16px, opacity .35) ran on every `load` event, including copies served from the browser cache, so each tab switch re-faded every preview. Fix: skip the reveal when the resource timing entry reports no bytes over the network (`heldByBrowser`). Test (fails before): `test_a_preview_already_loaded_does_not_fade_in_again_on_a_tab_switch` in `test_browser_style_tab_previews.py`.

**e. Home landscape empty margin** (commit c14b2cd8). Real defect. At 844x390 and 926x428 the text column of a landscape-frame card is taller than the picture; the picture box (and the cycle ring around it) was flex-stretched (140px box for a 120px picture), leaving an empty strip under the picture. Fix: `align-self: flex-start` on `.home-flight__picture`. Test (fails before): `test_the_picture_box_hugs_the_picture_when_the_text_is_taller` (both viewports, both frame shapes).

**f. Info button glyph** (commit c85443c8). Real defect. `.home-state__next .icon { margin-top: 3px }` (meant for the clock) also hit the "i" glyph inside the round button, pushing it 1.5px below the circle centre. Fix: `margin: 0` on `.home-state .info-tip__button .icon`. The info button is the only `.info-tip__button` in the app; the title pencil measured centred. Test (fails before): `test_the_round_icon_buttons_hold_their_glyph_at_the_centre` (info, pencil).

## Tests adapted
- `companion/test_personalisation_layout.py`: the two assertions of the removed Style sentences (see b).
- `companion/testdata/render_baseline.json` regenerated once (PR #521 also moves it).

## Verification
- Non-browser companion suite: 7427 passed, 1 flaky `test_status_pages_01.py::test_battery_trend_timestamps_show_concise_format` (time-dependent, passes alone, untouched code).
- Browser: Home, Style, Personalisation, Components, display looks, motion, ux_02, fleet-users fixes, audit4 fixes, render baseline: 627 passed. test_companion_app_04, stylesheet structure, suite/structure guards, i18n: pass.
- ruff, mypy, function-size, comment-history: clean.

## Deviations
None. Components page sample ("Up to 40 characters.") left as the help-text sample of the showcase.
