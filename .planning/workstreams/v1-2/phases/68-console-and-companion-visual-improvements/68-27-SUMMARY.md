---
phase: 68-console-and-companion-visual-improvements
plan: 27
subsystem: companion
tags: [pairing, fleet, i18n, alert, dialog]
requirements: [CON-01]
key-files:
  modified:
    - companion/pages/pair_frame_page.py
    - companion/pages/fleet_page.py
    - companion/console_lifecycle.py
    - companion/i18n_fr/pair_frame.py
    - companion/i18n_fr/admin_lifecycle.py
    - companion/static/style.css
    - companion/static/style-admin.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-21
---

# Phase 68 Plan 27: Pair refusal alert and re-activation explanation Summary

The refused pairing code is shown as a tinted alert box (icon, bold sentence, validity line under it); the re-activation confirmation explains the wake (Reset now, otherwise next wake, up to 24 h); the re-activation question sits closer to its title block and buttons; the Add a frame page tells a frame showing no code to press Reset. All in English and French, built from the owner-approved mock `68-MOCKUP-retired.html`.

## Commits

- c2f538dd feat(68-27): refused pairing code as an alert, Reset help line on the pairing page
- 2152d019 feat(68-27): re-activation confirmation explains the wake and Reset, tighter question margins
- render baseline regeneration (stylesheet version hash only; third commit of the branch, see `git log`)

## What changed

- `pair_frame_page.py`: refusal rendered as one `role="alert"` box (inline circled-exclamation icon, `.field-error` bold sentence, validity line inside); the field's `aria-describedby` points at the box. Plain form shows the validity line under the field and, under the form, "If your frame shows no code, press its Reset button." (not shown in the refused state).
- `console_lifecycle.py` + `i18n_fr/admin_lifecycle.py`: re-activation flash detail: "Press Reset on the frame to show its pairing code now. Otherwise it appears at its next wake, up to 24 hours from now."
- `fleet_page.py` + `style.css`: the re-activation dialog sentence carries `modal__question`; margins tightened for that dialog only.
- `style-admin.css`: `.pair-alert` styles. French ids added/updated; no orphan ids (`test_i18n.py` green).
- Not touched: refusal conditions, status codes, throttles, cookie, `server/pairing_code.py`, `RETIRED_SLEEP_S`, the 24 h cadence, STATE.md, ROADMAP, overview.

## Fidelity check (mock vs built)

Mock captures are in `.../scratchpad/p27/mock/` (extracted from the HTML; 390 px, light only), built captures in `.../scratchpad/p27/built/` (full page; pair, refuse, dlg, toast x en/fr x light/dark x 320/390/1440 = 48 images). Row-by-row pixel profiles of mock vs built at 390 light: refusal page matches within 1 px; re-activation dialog matches exactly (EN and FR).

## Design-system divergences

The `sketch-findings-skypane` skill could not be loaded (no Skill tool in this environment); I used the mock's tokens and the existing CSS tokens instead.

1. Hardware-specific gesture text: the plan asked for a lookup per hardware type; the approved mock text and `68-RESET-GESTURE.md` both say "press Reset" for EE02 and EE04 with no location, so there is one text and no lookup (a lookup would give identical strings). The generic fallback is the same text.
2. Pair page help line: the mock image "Proposed: line under the form" is pixel-identical to today (the line is not drawn), while the approval note says the page gets a help line for a frame showing no code. I built the note: a line under the form (after the buttons), hidden in the refused state (the refused mock shows nothing under the buttons). Owner to confirm.
3. French re-activation confirmation: the mock's French capture still shows the old sentence. The FR text is my translation: "Sur le cadre, appuyez sur Reset pour afficher tout de suite son code d'association. Sinon, il apparaît à sa prochaine mise à jour, dans 24 h au plus." Owner to confirm.
4. Literal pixel values taken from the mock outside the 4 px scale: alert padding `12px 16px`, margin `10px 0`, icon gap `12px`, detail text `14px`; dialog question: body margin-top `6px`, action gap `6px`.
5. The alert icon is an inline SVG (circled exclamation), not the shared sprite: the sprite has only the toast cross and the warning triangle, and adding a symbol would change every page's HTML.
6. Scope: the tighter margins apply to the re-activation question only (as approved); the Retire and Reassign dialogs keep their margins. The console's own Add a frame dialog keeps its plain error line (the mock only draws the user pairing page). Owner decision: extend either?
7. The mock covers 390 px light only; 320 and 1440, dark and FR were checked visually (see built captures), not against drawings.

## Deviations from plan

- The plan's `banner__pill` replacement (D-14): no hand-built `banner__pill` markup exists in either file, nothing to replace.
- Plan Task 3 listed `test_render_baseline.py` and `test_access_matrix.py`; the full core group covers both (green).

## Tests

- New behaviour tests: `test_user_pairing.py` (alert structure, FR refusal, Reset help line EN/FR, absent in refusal), `test_console_lifecycle.py` (flash EN/FR), `test_browser_fleet_dialogs.py` (question spacing, flash visible and not clipped, 44 px buttons, 360/1280, EN/FR), `test_browser_user_pairing.py` (alert geometry).
- Core group (`SKYPANE_TEST_GROUP=core scripts/run-all-tests.sh`, SKYPANE_REQUIRE_BROWSER=1): 12310 passed, 7 skipped, 2 setup errors in `companion/test_update_actions.py::test_post_with_an_invalid_type_is_rejected_and_changes_nothing[../../etc]` and `[sim-ee02-clone/../x]` (fixture setup under 4-worker load); both pass when the file is rerun alone (37 passed). Not related to this change.
- Browser, in chunks (`-n 4`): fleet dialogs + user pairing + other action + one toast one sheet 60 passed; console group 88 passed; fleet anchors/detail/dirty/page/sections/users fixes 113 passed; french fit + leave dialog + personalisation pairings + quiet hours 102 passed.
- Gates: ruff (companion) clean, mypy clean, function size none over 80, comment history exit 0, companion/app.py 1496 lines, largest JS 1227 lines (no JS changed), `stub-server/test_phase47_freeze.py` and access tests green within the core run, `server/pairing_code.py` unchanged.
- Render baseline: regenerated once; 68 of the 76 page entries changed, all with identical length, i.e. only the stylesheet version hash.

## Notes

- Phase 64 touched these modules; open PRs: only #481 (dependabot playwright bump, server/); none touches fleet_page.py or pairing modules.

## Owner decisions needed

Divergences 2, 3 and 6 above.
