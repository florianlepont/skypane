# Phase 68 Plan 26 FIX4: Other-frame action margin and no frame button in the Console

Two owner-reported defects on PR #488.

## Defect A: Re-activate / Pair frame button touched the card's right edge

- Cause: `companion/pages/fleet_frames_list.py` `other_page_html` passed the trigger button to
  `ui_groups.row(..., trailing_html=action)` without the trailing-control margin that
  `.group > .row > .row__trailing` provides.
- Fix: the button now carries the existing `row__trailing` class (same pattern as
  `co_managers_card.py`'s remove control). No new CSS: the one existing selector in
  `style.css` gives the `--space-md` right margin.
- Test: `companion/test_browser_fleet_other_action.py` measures the gap between the button and
  the row's right edge against the row text's left padding, retired and pending page, 390 and
  1440, EN and FR (8 cases; fails without the fix, passes with it).
- `test_console_fleet_page.py` pinned the exact class string of the button; it now expects
  `fleet-action-button row__trailing` (same assertion otherwise).

## Defect B: frame button drawn on Console pages

- Fix: `frame_menu.personal_menu_html` returns "" when `ui_shell.current_space(active)` is the
  Console space (shell helper used lazily through `_shell()`). `_add_row_for_viewer` lost its
  now-dead Console branch (the Add a frame row always goes to the viewer's own page); the unused
  `access` import was removed.
- Tests: `test_frame_sheet.py` gains Console pages (health, device, update, fleet, users, system)
  with no button and `header_menu_html` empty, plus a plain user keeping the button on Health.
  `test_browser_console_no_frame_button.py` checks a browser (390/1440, EN/FR): `/health`,
  `/device`, `/update` and the per-frame health/device pages have no `details.frame-menu`; the
  frame's personal pages keep it.
- Existing tests updated to the approved behaviour (only where they asserted the button on a
  Console page): `test_frame_sheet.py` (hostile-name test now renders a personal page; the
  "Console pages list every frame with owner email" and "Console cards sort" tests removed, as
  the list they described no longer exists on Console pages; the personal-space list rules stay
  covered by the other tests in the file), `test_frame_switcher.py` (Console assertion is now
  an empty menu).
- Reserved space: the desktop rules that keep content clear of the floating frame button
  (`.site-header:has(.frame-menu) ~ ...` padding, banner margin, frame-notice padding) are all
  conditioned on `:has(.frame-menu)`, and the Back to Fleet marker only appears on personal
  pages (an administrator viewing another person's frame), where the button stays. Nothing
  applies to Console pages any more, so there was no reserved space to remove.

## Verification

- Non-browser companion suite: 7060 passed before the test edits (5 expected failures, all
  fixed above); affected files 40 passed after.
- Full browser suite (`companion/*browser*.py`, SKYPANE_REQUIRE_BROWSER=1): 10940 passed, 3 skipped.
- Access tests (`companion/test_access*.py`) and `stub-server/test_phase47_freeze.py`: 2075 passed.
- ruff, mypy, function-size (max 80, server and stub-server), comment-history: clean;
  `companion/app.py` 1491 lines.
- Golden render hashes: `render_baseline.json` regenerated, no change.
- Screenshots (before/after, light, 390/1440, EN/FR) of retired, pending and Console health pages:
  `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/fix4/{before,after}/`.

## Deviations from Plan

None to plan scope. Process note: one `git stash` / `git stash pop` was run to prove the new
browser test fails without the fix; the stash list was empty before and after, nothing lost.

## Design-system divergences

None. The button reuses the existing `row__trailing` margin token; the Console simply omits the
frame button (frames are switched from the Fleet list), which uses no new colour, size or
selector.
