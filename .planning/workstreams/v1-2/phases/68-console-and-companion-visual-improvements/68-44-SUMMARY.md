# Plan 68-44 Summary: test hardening, Home pulse under dialogs, point-10 defects

## What changed

1. **Test hardening.** New `test-support/animation_settle.py` is the one shared wait: it ignores infinite, paused and finished animations (`endTime` not finite) and offers `SETTLED` (document loaded + no finite animation running), `ANIMATIONS_DONE`, `DONE_EXPR` (to compose into larger waits), `TARGET_SETTLED` and `wait_settled(page, target)` (the element and its subtree via `getAnimations({subtree: true})`). The ten page-wide waits that hung on any loop (`getAnimations().length === 0`, or `playState !== 'running'` with no infinite check) now use it, three of them scoped to their dialog or `main`. 50 identical module-level SETTLED/IDLE/READY copies were replaced by the shared constant. Assertions are unchanged. About 40 further variants (selector-specific, pause-and-pin, probes that assert on animations themselves) were left as they are on purpose.
2. **Home pulse under a dialog.** `html:has(dialog[open])` now stops `.home-state__dot--pulse`, `.is-breathing` (style.css) and the dot halo (`::after`, joined to the existing rule in style-home.css, because the stylesheet-structure test forbids declaring a selector twice). Browser test `test_home_pulses_stop_under_an_open_dialog_and_run_otherwise` (fails without the CSS, verified against HEAD).
3. **Point 10.**
   - (a) At 359.98px and below the More sheet rows use 8px side padding, the label column is 6.25rem and the theme segments 2px side padding, so FR "Auto / Clair / Sombre" and EN "Language" show whole. The existing theme/language edge test now also runs at 320px, EN and FR (failed before, passes after).
   - (b) The selected row is the Fleet list's (wide layout: the list panel scrolls by itself). `fleet-anchors.js` centres `.fleet-frame-row.is-selected` in `.fleet-list__body` on load without moving the page. Browser test with 30 frames (fails without the script).
   - (c) Header of a retired frame: **EN** `Retired · Formerly owner@example.test` became `Retired · Belonged to owner@example.test`; **FR** `Retiré · Anciennement owner@example.test` became `Retiré · Appartenait à owner@example.test`. New strings `admin_fleet.belonged_to` ("Belonged to %s" / "Appartenait à %s"). A retired frame without an owner keeps the old unassigned wording. The list row keeps "Formerly <owner>" only as its no-date fallback. Test in `test_console_fleet_view.py`, EN and FR.
   - (d) The `.hero*` CSS was not fully dead: `ui_groups.hero()` fed only the Components gallery (one "Hero" state) and the `.hero__picture` glow / `.hero__glass` glint had no producer. I removed the whole chain: the `.hero*` rules, the reduced-motion entries, `skypane-picture-breathe` and `skypane-glint` keyframes, `--motion-glint`, `ui_groups.hero`, its gallery state and the two FR strings, its unit test, the `.hero__picture` selector in motion.js, and the references in four tests. Nothing real-page rendered it.
4. **Render baseline** regenerated once at the end: 17 paths x 2 languages x 2 themes changed, all of them only the `?v=` asset hash; no page content moved (the baseline has no retired-frame page).

## Verification

- ruff, mypy (49 files), function-size (1221 functions, none over 80), comment-history: clean. `companion/app.py` is 1497 lines.
- Core group: 12526 passed, 7 skipped (root-only permission tests).
- Browser shards 0-4 of 5: 1211 / 761 (1 skipped) / 753 / 668 / 731 passed, 0 failed. All runs came after the last code change (a first core run had one failure, the duplicate-selector structure test, fixed in `de7a72dd` and rerun in full).
- New tests: 1 (pulse), 1 (selected row), 2 (retired header EN/FR), +2 params (320 px EN/FR).

## Divergences

- (d) went beyond CSS because the markup helper and tests used `hero`; see above.
- The retired header's tail still wraps onto its own line at 320px with a leading "·" (existing layout, not changed).
- The mixed files `test_browser_overhaul_sweep.py` and `test_browser_more_sheet.py` carry both their settle-helper change and their feature change, so they sit in the feature commits, not the hardening one.
- PR #514 (branch -19) touches `style-admin.css` and `render_baseline.json`; regenerate the baseline after it merges.

## Screenshots

`/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p44/` holds before-/after- images of the More sheet (`more`) and the retired frame header (`header`) at 320 and 390 px, EN and FR, light.

## Commits

4ff28020, 3a3c4f1d, 18755948, 91aa28a4, de7a72dd, b5ee2393 (plus the docs commit for this file).
