# Phase 61 Plan 85: Home status block, Quiet hours sheet, Flights rows Summary

Owner decisions D47 R9-1, R9-2 and R9-3 (W114, W115, W117, W118, W119, W120): one coherent Home status block with the new wording, a Quiet hours sheet that fits a small phone, and two-line Flights rows without the plane icon or the call sign.

## What changed

- **R9-1 Home status.** The healthy word of the shared frame-status resolver is "Online" / "En ligne" (was "Up to date" / "À jour"), so Home, the Fleet list, the frame switcher, the account list and the notices agree; the other states' words are unchanged. The due line reads "Next refresh in N min" / "Prochain rafraîchissement dans N min" (shared headline template, the Frame strip, the signature ring's accessible name "Frame cycle: next refresh in N min"); the clock icon on the due line is gone so the state word and the line read as one block. The greeting is a 16 px secondary line (`.page-title--greeting`), the state word is the title. The Battery row reads "69% · battery life ~6 weeks" on one line (percentage, then the estimate beside it, the bar below); the "Normal level" word is gone, Low / Very low stay, and the estimate is still hidden when not honest or while charging.
- **R9-2 Quiet hours sheet.** Night and Day presets side by side, Start and End side by side at every width; on a phone the check mark gives way (accent border and filled icon mark the selection) and the time inputs use 20 px, so nothing clips in 12-hour locales. Everything is visible without scrolling at 390x844 and 375x667, EN and FR.
- **R9-3 Flights rows.** Phone rows: picture thumbnail, title = airline plus route codes, second line = direction and aircraft type, clock over age at the right. No plane icon (the thumbnail's corner glyph and the no-picture chip are gone), no drawn call sign. The call sign stays as visually hidden text in the row (phone and desktop table), in the search text, and in the picture link's accessible name and the picture dialog. The desktop table's Flight column is "airline · aircraft". A missing route no longer prints "Route unavailable" on the phone row (the desktop Route column keeps it).

## Tests

New behaviour tests: status block coherence (EN/FR, 390/1280: "Online"/"Next refresh in", no "Up to date" / "update", ring name, greeting smaller than the state title), battery on one line, Quiet hours fits at 390x844 and 375x667 in EN/FR (no scroll, presets and times side by side), Flights rows have no plane icon and no visible call sign (phone and desktop) while search by call sign finds the row, two-line row shape.

Changed in place (subject changed deliberately): the pins of "Up to date" / "Next update" / "Prochaine mise à jour", the Battery row texts, the flights card/row tests (plane chip, direction glyph, call sign slot, route fallback), the type-scale and sweep heading checks (Home's greeting is a quiet line, not a title), the Quiet hours sketch test (no check mark on a phone, time size >= 20). Render baseline rewritten.

Screenshots: `scratchpad/shots85/` (quiet hours EN/FR at 390x844, 375x667, 1280; Home FR 390; Flights 390 and 1280).

## Deviations

- The Flights desktop stays a table (the owner's text says phone cards and desktop table); the mockup's desktop shows cards.
- The call sign is kept as visually hidden text rather than removed from the DOM, so screen readers and existing text-based checks keep it.

## Tests run

ruff, mypy, check_comment_history, check_function_size, stub-server/test_phase47_freeze.py, render snapshot rewritten. Non-browser companion tests that mention the changed pages plus test_sign_in_surfaces, test_render_baseline, test_page_scripts, test_stylesheet_structure, test_suite_guards, test_companion_app_0* (4754 passed). 41 whole browser files that mention the changed pages plus test_browser_overhaul_sweep (all green after the in-place updates; the sweep and foundations re-run whole: 831 passed). The touched browser files (flights cards, quiet hours, battery row, suite guards) run 4 times in parallel: 364 passed each.
