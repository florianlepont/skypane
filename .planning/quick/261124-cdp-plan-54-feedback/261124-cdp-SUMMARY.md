# Quick 261124-cdp: Plan 54 owner feedback fixes - Summary

Branch `phase-68-plan-54-feedback`, seven code commits (one per task 1-7), one test follow-up commit, plus the task 8 findings file (not committed, with this summary).
STATE.md, ROADMAP.md and requirements untouched; nothing pushed; `render_baseline.json` not regenerated.

## What changed per task

1. **Home pencil removed, "i" kept on the sentence line** (`b1441b3b`).
   `pages/home_title.py` renders the name only; the Home rename dialog, the `home.rename_frame_action`
   string and the pencil CSS are gone (rename stays in Account and Fleet). The wrapping bug came from the
   "i" being an atomic inline that wrapped alone: `pages/home_state.py` now wraps the sentence's last word
   plus the "i" in a nowrap `home-state__tail` (`static/style-home.css`). Browser test at 360 and 390 px
   in EN and FR (the FR 360 case failed before the fix). Old tests that opened the dialog from Home moved
   to Account; skill notes updated.
2. **Airlines default sort is rarest** (`393df3c9`). `DEFAULT_SORT = "rarest"` and the script default in
   `static/list-filter.js`; menu order and other options unchanged. Tests updated plus a default-order test.
3. **French nav label is "Airlines"** (`1480496d`). This restores the earlier change that a later commit
   reverted: `nav.airline_collection`, table caption, back link, count labels and the two reload hints
   (`i18n_fr/nav.py`, `airlines.py`, `common.py`). Other nav entries checked: no other regression. Tests
   (tab bar, i18n identical-to-English allow list, shell digest in `test_sign_in_surfaces.py`) follow, and
   `test_i18n.py` now asserts the Airlines wording instead of forbidding it.
4. **Signed-in Credits has no navigation** (`f74815ad`). `ui_shell.page_shell(bare=True)` drops the
   sidebar, tab bar, space switch, frame button and wordmark link (`dashboard-shell--bare` single column in
   `style.css`); `credits_page` uses it only when signed in. Signed-out unchanged. New
   `test_credits_signed_in_chrome.py` (served markup for user and admin in EN/FR, browser at 360 and 1280).
5. **Frame page anchor chips bar** (`4abdc0de`). `.fleet-anchors` keeps its solid canvas colour and gets a
   `::before` strip of the same colour covering the safe area plus app-bar drop above it
   (`static/style-admin.css`). Browser test with a simulated 47 px notch and web-app mode, both themes and
   languages (fails without the strip).
6. **New frames wake every 15 minutes** (`21eac6b0`). `device_dirs.provision_device_dir` seeds
   `{"wake_interval_s": 900}` instead of `{}` (`NEW_FRAME_WAKE_INTERVAL_S`). Only newly provisioned frames
   get it; existing configs are never overwritten and a config with no stored value stays unset. No
   migration. Tests in `server/test_device_dirs.py` and `test_fleet_ops.py`.
7. **Type row menu labels and modal title** (`e156f541`). EN "Set as default" / "Remove as default", FR
   "Image par défaut" / "Retirer par défaut". The add-illustration dialog title is now "Add an
   illustration" (FR "Ajouter une illustration") with the airline (and type) shown as the subtitle
   (`STEP_B_TITLE`, `resolve_dialog.py`, `static/panel-lookup.js` keeps the caption visible in that mode).
   The no-JS step page keeps its full sentence. Browser test checks one line at 360 px.
8. **Auth0 invitation: investigation only** - see `261124-cdp-AUTH0.md`. Exact three requests documented;
   most likely a missing `SKYPANE_AUTH0_CUSTOM_DOMAIN` (ticket URL rejected) or a missing
   `create:user_tickets` Management API permission; the real reason code is in the `user.invitation` audit
   row. Nothing changed.

## Deviations and judgement calls

- Task 6: a frame reassigned to a new owner is reseeded through the same function, so it also starts at
  900 s (its config is already wiped on reassign). `test_fleet_ops.py` asserts this.
- Task 3: the shell digest in `test_sign_in_surfaces.py` was re-pinned (French nav text changed), as the
  earlier Airlines change did.
- Task 4: the small wordmark in the phone header stays (not navigation, not a link).
- A stale `/devices/<id>/frame/name?return_to=<Home>` link now lands on a page without the dialog (Home);
  `frame_rename` was left as is, tests use Account as the origin.

## Not done / for the orchestrator

- `companion/testdata/render_baseline.json` is NOT regenerated (as instructed); the render-baseline test
  will differ for Home, Airlines (FR), Credits and the frame page until it is.
- Task 8 only reports; no config or code change.

## Tests and gates run (SKYPANE_REQUIRE_BROWSER=1, server/.venv/bin/python)

- Targeted files per task plus `test_companion_app_04.py`, `test_stylesheet_structure.py`, `test_i18n.py`:
  all passing.
- Whole suite `pytest companion server stub-server -n 8` (30 min): 15781 passed, 14 failed. 12 were tests
  following the changes (fixed in the last commit and re-run green); `test_browser_place_search` CDG was a
  flake (green alone); the one remaining is `test_render_baseline.py` (expected, baseline not regenerated).
  The silent-frame tile now reads "Has not checked in for a while" (warn) for a new 900 s frame: a frame
  with an explicit interval resolves to the late state, never the long-time error (existing behaviour).
- ruff: clean. mypy: no issues in 50 files. `check_function_size.py check --max 80 server stub-server`:
  none over 80. `check_comment_history.py check`: clean. `companion/app.py` 1491 lines (<= 1500); largest JS
  file 1227 lines (<= 1500).
