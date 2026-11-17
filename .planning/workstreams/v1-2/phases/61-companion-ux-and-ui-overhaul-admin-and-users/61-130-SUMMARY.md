# Phase 61 Plan 130: Tablet cap for the tab bar and More sheet Summary

Quick fix (owner decision D58, audit item V6-10): on tablet widths (below the 960px sidebar breakpoint) the bottom tab bar and the More sheet are capped at 460px and centred.

## Changes
- `companion/static/style.css`: new token `--tab-bar-max: 460px`; the existing `.tab-bar` rule (inside the `max-width: 959.98px` media block) gained `max-width: var(--tab-bar-max)` and `margin-inline: auto`. Left/right insets, bottom offset and safe-area handling are unchanged, so auto margins centre the capped bar. The More sheet is absolutely positioned against the bar (`left: 0; right: 0`), so it follows the cap with no extra rule. The scrim (`body::after`, `inset: 0`) is untouched and still covers the viewport; the slider and view-transition names are untouched.
- `companion/test_browser_tab_bar_tablet_cap.py` (new, red then green): at 768 and 940 widths in both themes, bar and open sheet are at most 460px wide with equal side margins (1px), the scrim covers the full viewport, the pill stays inside its cell at 768, a 390 phone keeps 8px gutters, and the sidebar layout shows no bar.
- `companion/testdata/render_baseline.json` regenerated (stylesheet digest moved).

## Notes
- The task asked for a 1024 width check. At 1024 the sidebar layout is active and the tab bar is hidden (breakpoint 960px), so the test asserts that and uses 940 as the widest tablet-bar width.
- The Console space bar uses the same `.tab-bar` rule, so it is capped by the same declaration; the Console role tests pass.

## Deviations
None.

## Verification
ruff, mypy, check_comment_history, check_function_size, phase47 freeze all green. Ran at -n 8 (667 passed): tab-bar float/roles, More sheet/redesign/scrim, motion, motion sheets, motion unlock, page opening, tab pill transition, stylesheet structure/load order, status pages 06/07, sign-in surfaces, the new file. The new file was run 4 times in parallel with zero failures.
