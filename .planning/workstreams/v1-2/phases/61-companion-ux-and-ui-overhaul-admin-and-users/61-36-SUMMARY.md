# Phase 61 Plan 36: Account page and navigation chrome Summary

Owner feedback W13, W14, W15 plus an orchestrator addition (space switch overflow in the sidebar).

- **W14:** the language (FR/EN) and theme (Auto/Light/Dark) forms are gone from the desktop sidebar footer and from the phone hamburger panel (which now holds Sign out only). They remain on the Account page; the `/ui-lang` and `/ui-theme` routes are unchanged.
- **W13:** the Account "Preferences" card is two labelled rows, Language / Langue and Theme / Thème, each with a one-line hint and a segmented control sized to its content (`.pref-row`, 44 px targets, text above the control below 640 px and beside it from 640 px). New EN/FR strings in `companion/i18n_fr/account.py`. No-script POST forms are kept.
- **W15:** new `icon-person` sprite symbol (sprite now 48 symbols) used by the Account entry in every nav (sidebar, phone More sheet, user bar).
- **Space switch overflow (orchestrator addition):** columns are `minmax(0, 1fr)` so both segments share the width equally; segments clip their content; labels ellipsise inside their own segment. In the sidebar copy the space glyph is dropped (check and label stay, 13 px) so "Mon cadre" and "My frame" fit in EN and FR, both themes.
- Tests updated in place to assert served HTML / browser behaviour: `test_browser_theme_switch.py` (now on Account, plus new tests for labelled compact rows at 360 and 1280 px in both themes, no switch in any nav, person icon), `test_browser_space_switch.py` (new test: equal segment widths, label box inside segment and pill, scrollWidth <= clientWidth), `test_browser_ux_02.py`, `test_status_pages_05.py`, `test_companion_app_01/02/04b.py`, `test_sign_in_surfaces.py` (shell and error-page digests regenerated deliberately). `companion/testdata/render_baseline.json` regenerated. `61-UI-SPEC.md` wording updated.

## Deviations from Plan

- The Account hint wording avoids the word "device" (an Account-vocabulary test forbids administrator words).
- The phone hamburger toggle (gear) and its panel are kept; the panel now holds only Sign out.

## Self-Check: PASSED (see report for gate results)
