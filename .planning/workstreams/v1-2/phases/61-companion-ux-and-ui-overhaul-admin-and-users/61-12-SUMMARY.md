---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 12
subsystem: companion
tags: [step-counts, traceability, sweep, a11y]
requires: [61-06, 61-07, 61-08, 61-09, 61-10, 61-11, 61-15]
provides: [measured step counts, friction traceability, cross-page sweep]
key-files:
  created:
    - companion/test_browser_overhaul_steps.py
    - companion/test_browser_overhaul_sweep.py
    - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-STEP-COUNTS.md
    - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-TRACEABILITY.md
  modified:
    - companion/static/style.css
    - companion/ui_nav.py
    - companion/ui_shell.py
    - companion/i18n_fr/nav.py
    - companion/test_sign_in_surfaces.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---
# Phase 61 Plan 12: Step counts, traceability and cross-page sweep Summary

Nine of the ten walkthrough tasks now meet their step target in a real browser, Display settings do not (4 and 5 actions against 3), and a 204-case sweep over every reworked page and dialog found and fixed six phone/French defects.

## Commits
- c250315 step-count test and record
- 1b0ca4b friction traceability
- 5661872 fixes the sweep forced (skip link French text, admin Account tab bar, 44 px targets, pins)
- c83d98e the sweep
- e2e4a1b sweep findings and limits in the traceability

## Step counts (measured, 360 px, fake identity provider)
See `61-STEP-COUNTS.md`. Met: A1 0, A2 4, A3 4, A4 retire 3 and reassign 4, A5 4, A6 1, U1 4 (ends on Home), U2 0 / 1, U3 0. Not met: U4 (quiet hours 4, look sheet 5, target 3), because Display settings sit under the first screen or in a sheet. Not improved over the walkthrough: A4 reassign, U1, U2 with several frames, U4.

## Deviations from Plan
1. **[Rule 1 - Bug] Skip link was English only.** The sweep's French-versus-English comparison flagged it. Now an `i18n` message with an FR entry. Pins moved deliberately: the no-principal shell digest and 24 French pages of `render_baseline.json` (only the skip-link text differs; verified by recomputing the digest with the old text).
2. **[Rule 1 - Bug] An administrator's Account page had no phone tab bar** (`_tab_bar_html` keyed on a device config that Account does not pass). It now also renders for an admin principal.
3. **[Rule 1 - Bug] Targets under 44 px found by hit-testing:** Fleet name link (stretched tap area), Account language/theme segments and Sign out, the phone toast action (40 to 44), quiet-hours presets and special-look Remove (CSS only).
4. **Sweep scope for 44 px at 1280 px.** The sidebar, its footer controls, the brand link and the Home Health pill are pointer-sized by design (29 to 33 px); the desktop assertion covers dialogs, list rows and page headers. UI-SPEC section 8 item 2 asks for both widths; recorded as a limit.
5. **French check is a render comparison, not a catalogue lookup.** `test-support/i18n_ids.py` is a migration helper; catalogue completeness is already in `test_i18n.py`.
6. **Phase 44 walkthrough test needed no edit** (passes unchanged).
7. **U4 test pins the measured value (4 and 5), not the target 3**, because the target cannot be met without changing Display, outside this plan.
8. There is no F12 in `61-WALKTHROUGH.md` (F1 to F11); recorded in the traceability.

## Known Stubs
None.

## Open points for the owner / orchestrator
- U4 misses its target (Display page length and the look sheet).
- Time zone select stays in the Quiet hours card (61-10); owner confirm.
- Large empty states remain on History, Detection, My frames and the table fallback.
- Desktop controls at 29 to 33 px (sidebar, Health pill) versus the 44 px wording of UI-SPEC section 8.

## Self-Check: PASSED
Full `./scripts/run-all-tests.sh`: 9300 passed, 8 skipped (root-permission and openssl skips, no browser skips), coverage 96.23% against the 93.0% floor. ruff, mypy (28 files), comment history, function size (922 functions) and the Phase 47 freeze test are clean. Commits c250315, 1b0ca4b, 5661872, c83d98e, e2e4a1b exist.
