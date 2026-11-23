# Phase 68 Plan 52: Owner feedback of 2026-11-23 Summary

Three owner items: Home flight card on desktop, foreign-frame banner and space switch in consultation mode, default type only for a type with a livery.

Captures (separate images): `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p52/{before,after}/`
(`home-{1280,1440,1920}-{en,fr}-{light,dark}.png`, `notice-{phone,desktop}-{en,fr}-{home,flights}.png`, `notice-scrolled-*`, after only: `notice-*-place.png`).

## Commits

| Item | Commit |
| ---- | ------ |
| 2. Banner at the very top, no space switch while consulting | 30d90b21 |
| 3. Default type only with a livery | 10ea0b36 |
| 1. Home flight card on desktop | 54023e5e |
| Render baseline regenerated once | final docs commit |

## 1. Home flight card, desktop

Before: at 1280/1440/1920 px the card spanned the whole column with a 168 px portrait at the left and an empty white area. After (>= 960 px): the card is `align-self: flex-start`, `width: min(100%, 36rem)`, 24 px padding and gap, a 208 px portrait (280 px landscape) and a 28 px callsign; the pills, statistics and strip keep the column width. Below 960 px nothing changed (phone and the 700 to 959 px layout are as before). Test: `test_the_flight_card_hugs_its_content_on_a_wide_screen` (1280/1440/1920, EN/FR) fails before, plus `test_the_flight_card_still_spans_the_column_on_a_phone` (360, 390).

## 2. Consultation mode (administrator on another person's frame)

Reproduced: on desktop the banner sat inside the main column, 48 px under the top and beside the sidebar; on phone it sat under the app bar (logo and frame chip); the "My frames | Console" pill stayed in the sidebar and the More panel kept its space row.

- The notice now renders as the first block of the body, before the shell, `position: sticky; top: 0`, full width, padded for the status bar / notch (`--safe-top`, `--app-bar-drop`), z-index above the sidebar and app bar. `--notice-h` (one line) keeps the desktop sticky sidebar clear below it. Location (map) page: the app bar laid over the map starts under the banner because the shell is its positioning context; the old per-page notice overrides in `style-place.css` are removed.
- `page_shell` computes the notice once; when present the sidebar space switch is not rendered and `_tab_bar_html(consulting=True)` drops the More panel's space row. Console pages and the administrator's own / co-managed frames are unchanged (switch present, no banner).
- Kept: Back to Fleet (`/fleet?frame=<id>`), eye icon, accent slab, texts (OWNER-APPROVED block unchanged). The frame-switch chip is kept (the mockup does not show it either way and existing tests rely on it); flag below.

Tests: HTTP (`test_admin_personal_scope.py`: notice is a direct child of body before the shell, no switch / space row while consulting, switch still present on own frame and Console), browser (`test_browser_admin_personal_scope.py::test_the_notice_is_flush_to_the_top_and_no_space_switch_is_offered`, 360/1280, EN/FR: top 0, full width, first block, over the sidebar, no visible switch, stays at 0 after scrolling). All fail before the change.

### Existing tests adapted to the new behaviour

- `test_console_shell.py` (two tests): the administrator on the owner's frame has no space row in More.
- `test_nav_personal_console.py`: admin More sheet on a foreign frame is Account alone; unused constant removed.
- `test_space_switch.py`: the two "My frames current" cases on the owner's frame removed (that state is covered by `test_nav_spaces.py` on `space_switch_html` and by the browser files below).
- `test_browser_overhaul_sweep.py::test_an_administrators_personal_page_equals_a_users`: admin has the notice and no switch.
- `test-support/nav_spaces_support.py::own_frame_home` now opens the administrator's own frame (`live_id`, it previously opened the owner's frame, despite its name); this keeps `test_browser_nav_spaces`, `test_browser_space_switch`, `test_browser_tab_bar_roles`, `test_browser_nav_alignment` testing the switch on a page that has one.

## 3. Default type needs a livery

A type has a livery when its artwork (built in or fleet-wide upload) exists for that airline: new `illustrations.type_artwork_keys` / `has_type_livery` (variant or shape slot, plus the lower-cased designator slot of curated pictures such as ATR72 / A330).

- Menu: "Set as default type" is offered only when the type has a livery; otherwise the type has no menu at all (the Editor's menus never show disabled items, so no new string and no orphan). "Remove as the default type" stays on the current default even without a livery.
- Server: `airline.default_type` with a type lacking a livery returns `FLASH_KEY_DEFAULT_TYPE_FAILED`, writes nothing, no audit row. Clearing (empty type) is always allowed.
- Deletion: today (before the change) deleting the artwork of the default type left a dangling default (star pill on a row with no picture, the airline row showing the code with the airline picture). Now `handle_artwork_delete` clears the default when no picture (built in or upload) is left for that type; the default is kept while a built-in picture remains.
- Pre-existing defaults without a livery: not changed. They keep their star and can be removed from the menu. Not measured on production data (no access); a one-off scan of `airline_default_types.json` against the illustration directories would list them.
- Not changed: naming an airline through the lookup panel with a `default_type` (`post_actions._record_resolution` and the upload `?default_type=` path) still stores the type directly, so a freshly named airline can get a default before it has a type picture. See owner decisions.

Tests: `test_airline_editor.py` (refused POST writes nothing and is not audited; built-in and uploaded accepted; clearing allowed; deleting the default's artwork clears it; kept while a built-in remains), `test_browser_airline_table.py::test_only_a_type_with_a_picture_offers_to_be_the_default` (360/1280, EN/FR) and two existing browser tests updated (a type with no picture has no menu; deleting the default's artwork leaves no default). Seeded default in the existing editor test now has the artwork it needs.

## Verification

Targeted and full results are listed in the hand-back report; ruff, mypy, function-size and comment-history clean.

## Owner decisions needed

1. Frame-switch chip while consulting: kept. Remove it too if "the pill to switch screens" meant it.
2. Lookup-panel / upload naming flows can still set a default type without a livery; apply the same rule there?
3. Pre-existing defaults without a livery stay until the owner removes them (or clear them in a one-off migration).
4. Sidebar clearance under the banner uses a one-line height; a banner wrapped on 2 lines on desktop (very long address) overlaps the top of the sticky sidebar only while scrolling.
