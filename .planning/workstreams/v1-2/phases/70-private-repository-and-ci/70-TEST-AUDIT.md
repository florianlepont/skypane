# Phase 70: test-suite speed audit

Read-only audit made on 2026-11-26. No repository file was changed, nothing was committed. Every number below was measured in this audit unless it is marked as an estimate or as taken from a CI run.

## Summary

The suite is 17,506 tests: 12,768 non-browser and 4,738 browser. Summed over workers it costs about 10,300 seconds of test time. Roughly 2,300 to 2,500 seconds of that (22 to 24 percent) is pure waiting that can be removed without touching an assertion or the test count. A further 1,800 seconds is waiting for entrance animations, removable only with an owner decision.

Top 5 wins, in test-time seconds (sum over workers; divide by 4 for wall-clock on the Mac with 2 runners of 2 workers, or on one hosted 4-worker shard):

| # | Win | Saved test time | Status |
|---|---|---|---|
| 1 | Test servers that run in a thread take 0.5 s to stop (`serve_forever` default poll). One-line change in three test-support files. | about 1,200 s (862 s core, about 340 s browser) | Verified: five core files went from 204 s to 22 s, 329 tests still pass |
| 2 | Every load of `/components` waits 8 s for a spinner specimen. 124 loads. Share one page per parameter set for the read-only tests. | 600 to 760 s of the 959 s spent | Cause verified; fix not run |
| 3 | Mac job layout: 7 test jobs on 2 runners leave one runner idle for 20 min, and each job pays 76 to 242 s of non-test steps. | about 15 min of wall-clock per Mac run | From CI run 1483 step times |
| 4 | Two helper waits that time out silently: the hit-area settle probe burns 300 frames (5 s) on an off-screen element, and the page-wide settle wait is held by the toast's 6 or 12 s timer. | 226 s + up to 312 s | Half of the first verified (113 s gone, 365 tests pass) |
| 5 | Shard weights are stale: 76 of 182 browser files have no weight and count for 370 s instead of the 2,736 s they take. Re-weighting levels the slowest shard. | 13 to 15 percent of the slowest browser shard (77 s on the hosted run) | Simulated on measured durations |

Expected result if wins 1 to 5 and the cold `/display` finding are applied: the Mac goes from about 82 min to about 55 min per full run, the hosted run from about 11.3 min wall and 62 billable minutes to about 8.5 min and 50. The suite-level fixes alone are about 12 min of the Mac gain; the rest is job layout. Getting the Mac under 35 min needs more CPU per VM, which is an owner decision and was not measured.

## Measurements

### How they were made

- Machine: Linux container, 4 vCPU, 15 GB. Venv is Python 3.13.18 (CI runs 3.14). pytest 9.2.0, xdist 3.8.0, playwright 1.65.2, coverage 7.17.4.
- Command: `server/.venv/bin/python3 -m pytest -n 4 --durations=0 -q -p no:cacheprovider` on the file lists from `scripts/ci_shards.py files core 0 1` and `files browser 0 1`. No coverage in these runs.
- The browser group was run twice in full with a measurement-only pytest plugin (kept outside the repository) that timed Playwright calls and server start and stop per test file, and recorded which finite animation was alive before each `wait_for_function`.
- The runs were made as root, so 8 permission-bit tests skipped locally (7 core, 1 browser). CI runs as a normal user and skips none.
- The work tree moved from `2188a9e1` to `61b4a239` during the audit (two new core test files). The file lists were taken before that.

### Totals

| Group | Tests | Wall, 4 workers | Test time (setup + call + teardown) | setup | call | teardown |
|---|---|---|---|---|---|---|
| core | 12,768 | 529 s | 2,028 s | 257 s | 866 s | 905 s |
| browser | 4,738 | 2,094 s (2,101 s second run) | 8,275 s | 1,028 s | 6,855 s | 392 s |
| all | 17,506 | 2,623 s back to back | 10,303 s | | | |

Collection takes 9.6 s for the core group and 7.2 s for the browser group, per worker. CPU was 64 to 76 percent busy during the browser run (4 workers on 4 vCPU).

### Where the browser time goes

Sum over the browser group, 8,275 s of test time:

| Call | Seconds | Calls | Mean |
|---|---|---|---|
| `page.wait_for_function` | 3,740 | 10,337 | 362 ms |
| `page.goto` | 1,478 | 5,494 | 269 ms |
| `page.evaluate` | 479 | 16,073 | 30 ms |
| companion subprocess start | 416 | 1,222 | 340 ms |
| in-thread server stop | 338 | 1,090 | 310 ms |
| `locator.click` | 228 | 2,188 | 104 ms |
| `context.new_page` | 213 | 4,955 | 43 ms |
| `locator.wait_for` | 213 | 5,977 | 36 ms |
| `page.wait_for_timeout` | 195 | 646 | 302 ms |
| `context.close` | 55 | 4,955 | 11 ms |
| `browser.new_context` | 38 | 4,955 | 8 ms |
| `browser.launch` | 0.2 | 4 | 60 ms |

What `wait_for_function` was waiting for (calls of 0.25 s or more, 3,452 s of the 3,740 s), by the longest finite animation alive just before the call:

| Animation | Seconds | Calls | What it is |
|---|---|---|---|
| `skypane-spin` on `.place-loading__spinner` | 1,058 | 272 | 8 s spinner; 959 s of it on `/components` |
| `skypane-reveal`, `skypane-reveal-fade` | 1,208 | 2,205 | page entrance, 400 to 700 ms |
| `skypane-blur-up` | 588 | 615 | picture reveal, 900 ms |
| `skypane-toast-dwell` on `.toast__timer` | 312 | 45 | toast auto-hide, 6 or 12 s |
| none | 169 | 146 | |
| others | about 120 | | shimmer, view transitions, small transitions |

### Core group: slowest files

| Seconds | setup | call | teardown | File |
|---|---|---|---|---|
| 49.3 | 1.8 | 0.6 | 46.9 | `companion/test_landing.py` |
| 49.3 | 0.0 | 49.2 | 0.0 | `deploy/tests/test_activate.py` |
| 44.2 | 0.0 | 44.2 | 0.0 | `server/test_check_interval_redraw.py` |
| 43.5 | 2.7 | 2.4 | 38.4 | `companion/test_user_view_http.py` |
| 43.0 | 0.0 | 43.0 | 0.0 | `server/test_poll_loop.py` |
| 41.9 | 0.0 | 41.9 | 0.0 | `server/test_giant_aircraft.py` |
| 39.5 | 1.7 | 2.1 | 35.6 | `companion/test_detection_page.py` |
| 36.9 | 0.0 | 1.2 | 35.7 | `companion/test_auth0_management.py` |
| 35.1 | 0.0 | 35.1 | 0.0 | `hardware/test_wakemodel.py` |
| 32.3 | 0.9 | 2.0 | 29.3 | `companion/test_console_users.py` |
| 31.9 | 0.0 | 1.3 | 30.6 | `companion/test_auth0_login.py` |
| 29.9 | 1.2 | 2.0 | 26.8 | `companion/test_personalisation_layout.py` |

By directory: companion 1,388 s, server 366 s, stub-server 122 s, deploy 77 s, hardware 48 s, test-support 18 s, scripts 10 s.

Teardown histogram, core: 1,589 teardowns between 0.45 and 0.56 s (775 s), 89 between 0.95 and 1.10 s (87 s), 308 under 0.1 s (3 s). That is 862 s of the 905 s of teardown, 42 percent of the core group.

### Browser group: slowest files

| Seconds | File | Main cause |
|---|---|---|
| 793.5 | `test_browser_overhaul_sweep.py` | 728 tests, one page load each; 477 s in settle waits, 145 s in `goto` |
| 671.5 | `test_browser_components_page.py` | 662 s of setup: 80 loads of `/components` at 8.3 s |
| 296.0 | `test_browser_personalisation.py` | per-test server, cold `/display` (105 s of `goto`), toast (51 s) |
| 269.4 | `test_browser_components_fit.py` | 265 s of setup: 32 loads of `/components` |
| 218.2 | `test_browser_airline_table.py` | toast timer, 12 waits of 12.2 s (146 s) |
| 197.6 | `test_browser_lighter_dialogs.py` | settle probe, 22 burns of 5.2 s (113 s); 16 s server stop |
| 194.5 | `test_browser_style_leave.py` | per-test server, cold `/display` (71 s) |
| 182.3 | `test_browser_page_opening.py` | 161 tests on entrance timing |
| 150.1 | `test_browser_design_system_fixes.py` | 4 tests of 23 s, 8 loads of `/components` |
| 141.7 | `test_browser_more_scrim_cover.py` | 154 tests, one page load each |
| 124.0 | `test_browser_personalisation_fixes.py` | per-test server, cold `/display` |
| 120.2 | `test_browser_round11_fixes.py` | mixed |

### Slowest 40 tests

Browser (seconds, setup + call + teardown):

| s | Test |
|---|---|
| 40.1 | `test_browser_airline_table.py::test_the_type_menu_sets_the_default_type_and_deletes_only_an_uploaded_picture` |
| 37.3 | `test_browser_ux_04.py::test_a_row_expands_to_its_types_and_each_type_has_its_own_replace` |
| 28.1, 27.7 | `test_browser_sheet_keyboard_surface.py::test_every_sheet_continues_its_surface_down_to_the_keyboard[admin-/airlines/manage-dark, -light]` |
| 27.7, 27.5 | `test_browser_airline_table.py::test_a_type_row_is_given_a_picture_then_its_artwork_is_deleted[1280, 360]` |
| 26.6 | `test_browser_airline_table.py::test_renaming_opens_a_dialog_and_the_menu_resets_the_name` |
| 23.9 | `test_browser_navigation_assist.py::test_idle_warming_runs_on_a_new_page_view_only_not_on_back_forward_or_reload` |
| 23.3, 23.3, 23.2, 23.2 | `test_browser_design_system_fixes.py::test_components_back_to_index_links_are_forty_four_pixel_targets` (4 parameter sets) |
| 19.0 | `test_browser_home_signature.py::test_home_opens_without_a_shift_on_a_slow_processor` |
| 18.6, 17.8, 17.4, 16.2 | `test_browser_personalisation.py::test_choosing_in_the_picker_raises_the_bar_naming_look_and_save_persists_it` (4 sets) |
| 16.8 | `test_browser_save_bar.py::test_every_page_shows_the_same_save_bar[390-en-light]` |
| 16.6 | `test_browser_personalisation.py::test_the_floating_save_bar_saves_the_look` |
| 15.2 | `test_browser_airline_table.py::test_the_artwork_uploads_through_the_real_routes_for_an_airline_and_a_type` |
| 14.6 | `test_browser_airline_missing.py::test_the_row_without_sighting_asks_the_type_and_an_upload_removes_the_row` |
| 14.5, 14.4 | `test_browser_airline_promotion.py::test_artwork_uploaded_for_an_airline_without_artwork_gives_it_a_row_of_the_table` (2 sets) |
| 14.5, 14.1 | `test_browser_airline_named_missing.py` (2 tests) |
| 14.1 | `test_browser_airline_editor.py::test_renaming_an_airline_through_the_editor_works_end_to_end` |
| 14.1, 14.0 | `test_browser_airline_table.py::test_the_unidentified_prefix_is_a_compact_row_on_top_named_in_a_dialog`, `::test_naming_a_prefix_is_audited` |
| 12.7 | `test_browser_motion_live.py::test_a_minute_less_rolls_the_countdown_once` |
| 12.0 | `test_browser_ux_03.py::test_the_theme_still_saves_with_scripts_blocked` |
| 11.8, 11.7 | `test_browser_calendar_connect.py::test_the_page_is_usable_in_both_themes[390-en, 390-fr]` |
| 10.3 to 11.4 | `test_browser_save_bar.py::test_every_page_shows_the_same_save_bar` (7 more sets) |
| 10.9 | `test_browser_ux_04.py::test_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies` |
| 10.8 | `test_browser_splash.py::test_a_request_that_never_answers_cannot_hold_the_splash_past_the_safety_cap` |
| 10.4 | `test_browser_splash_preload.py::test_after_the_splash_no_tab_asks_the_network_for_its_stylesheets_scripts_or_pictures` |

Besides these, 112 setups of 8.3 to 9.4 s each belong to the two `/components` files (927 s).

Core: `hardware/test_wakemodel.py::test_rates_filter_selects_one_device` 16.1 s and `::test_without_a_filter_the_mixed_export_is_not_the_owner_export` 14.4 s; `server/test_check_interval_redraw.py::test_off_states_match_a_run_without_the_experiment` 7.6 to 8.9 s for each of 5 sets; `companion/test_suite_guards.py::test_no_legacy_runner_anywhere` 6.9 s; `server/test_orly_replay.py::test_sweep_decisions_identical_on_every_cell[3]` 6.2 s; `server/test_pipeline_e2e.py::test_full_pipeline_end_to_end_through_the_real_device_protocol` 5.7 s; `deploy/tests/test_activate.py::test_rollback_on_http_probe_failure_and_missing_hsts` 5.0 s. Every other core test is under 5 s.

### CI runs read through the GitHub API

Hosted run 1486 (push to main, green, 11 min 21 s wall, 62 billable minutes after per-job rounding):

| Job | Before the tests | Test step | Whole job |
|---|---|---|---|
| core 0, core 1 | 21 s | 330 s, 319 s | 354 s, 343 s |
| browser 0 to 4 | 31 to 48 s | 452, 498, 468, 531, 583 s | 494 to 638 s |
| static | | | 42 s |
| aggregate `test` | | | 38 s, starts after the last shard |

The core weights in `ci_shard_weights.json` sum to 2,027 s for a 325 s shard, so that run had about 4 workers per shard. The runner README says a private repository gets 2 vCPU; the hosted figures below assume the 4-worker run that was measured.

Mac run 1483 (2 runners, 2 vCPU each, 82 min wall; it failed in `static` and one browser shard for reasons not looked at here, the step times are still valid):

| Job | Test step | Non-test steps in the job |
|---|---|---|
| core 0, core 1 | 1,080 s, 1,110 s | 76 s, 126 s |
| browser 0 to 4 | 907, 985, 922, 1,073, 1,083 s | 136, 242, 237, 132, 145 s |

Test steps sum to 7,160 s. Non-test steps in the test jobs sum to 1,094 s: "Set up job" 18 to 59 s, checkout 21 to 117 s, "Cache Playwright browsers" 35 to 48 s, artifact upload 14 s. A runner takes another 35 to 60 s between two jobs. Runner 1 ran four test jobs in a row; runner 2 ran three and then sat idle from 10:02 to 10:22.

### Coverage overhead

Twelve core files (2,783 tests), 4 workers: 68.4 s without coverage, 79.8 s with `--cov` and `COVERAGE_CORE=sysmon` (+17 percent), 117.6 s with the C tracer (+72 percent). `run-all-tests.sh` already selects sysmon. Not measured on the browser group or on Python 3.14.

## Findings

Ranked by saved time per unit of risk. "Test time" is summed over workers.

### F1. A test server running in a thread takes 0.5 s to stop

- What: `InProcessAppServer` (`test-support/companion_app_server.py:533`), `FakeAuth0` (`test-support/fake_auth0.py:77`) and the fake Anthropic server (`test-support/fake_anthropic.py:67`) start `serve_forever` with its default `poll_interval` of 0.5 s. `shutdown()` blocks until the loop next looks, so every stop costs up to 0.5 s; the Auth0 rig stops two servers and costs 1.0 s. `companion/test_browser_origin.py:44` has the same pattern once.
- Evidence: stop measured at 0.500 s three times; 0.010 s with `poll_interval=0.01`. Core: 1,589 teardowns of about 0.5 s and 89 of about 1.0 s, 862 s. Browser: 1,090 stops, 338 s. Experiment with the poll interval set to 0.01 s from outside the repository: `test_landing.py`, `test_user_view_http.py`, `test_auth0_login.py`, `test_detection_page.py`, `test_auth0_management.py` together went from 204.3 s to 22.4 s serial, 329 passed both times. Four browser files using the in-thread server lost 20 to 30 percent each.
- Saved: about 1,200 s of test time. Mac: about 215 s per core shard and about 35 s per browser shard, 5 min of wall-clock per run. Hosted: about 108 s per core shard, about 17 s per browser shard.
- Risk: very low. Production code is not touched. An idle server thread wakes 50 to 100 times a second instead of twice.
- Effort: three or four lines.
- Keeps every assertion and every executed test: yes.

### F2. Every load of `/components` waits 8 s

- What: the Components page shows a `.place-loading__spinner` specimen whose animation is finite (`skypane-spin`, 4 turns, 8 s in total, `companion/static/style.css:4543`). `animation_settle.SETTLED` waits for every finite animation in the document, so each load waits 8 s. `test_browser_components_page.py:167` builds a function-scoped page for each of 9 tests times 8 parameter sets; `test_browser_components_fit.py` does the same for 4 tests times 8.
- Evidence: `/components` settles after 7.97 to 8.00 s, the other pages after 0.4 to 2.2 s. 124 waits held by the spinner on that page: 638 s in `test_browser_components_page.py`, 255 s in `test_browser_components_fit.py`, 66 s in `test_browser_design_system_fixes.py`.
- A dependency found on the way: the save-bar specimen (`.components-save-bar .dirty-bar`) has no box until 5.9 s after load, because the toast specimen hides on a real 6 s timer (`companion/static/toast.js:120`). Finishing the spinner animation by script settles the page in 0.45 s, but then 75 of 1,043 specimen elements measure differently. The tests are correct today only because the 8 s spinner outlasts the 6 s toast. With an explicit wait for the save bar the geometry is identical to today's (0 of 1,043 differ) at 6.1 s.
- Proposed fix: load the page once per parameter set (width, theme, language) for the tests that only read it. In `test_browser_components_page.py` 7 of the 9 tests only call `evaluate` with read-only probes; the two dialog tests keep their own page. That is 24 loads instead of 72, and 8 instead of 32 in `test_browser_components_fit.py`. Also wait for the save-bar specimen explicitly, so the readiness no longer depends on the spinner's length.
- Saved: 72 loads at 8.3 s, about 600 s; about 760 s if the explicit wait brings the remaining loads from 8.3 to 6.1 s. Mac: 2.5 to 3 min of wall-clock. Not run.
- Risk: low to medium. The assertions are unchanged, but tests of one parameter set share a page, so a probe that changed the page would affect the next test. The probes read here (`OVERFLOW`, `SEGMENTS`, `BUTTONS`, `TARGETS`, `SWITCHES`, `OVERLAP`) do not change it. It needs a module-scoped context with the same loopback guard as `new_context` in `companion/conftest.py`, and `companion/test_suite_guards.py` rule G10 has to accept that fixture. With xdist's default distribution a worker may load its own copy, so the count is between 8 and 32 loads per file, not exactly 8.
- Effort: half a day.
- Keeps every assertion and every executed test: yes, the test items stay as they are.

### F3. The hit-area settle probe burns 300 frames on an element it cannot see

- What: `_SETTLE_PROBE` (`companion/test_browser_ux_helpers.py:1001`) waits until the element owns its own centre on 3 consecutive frames, for at most 300 frames (line 1027). For an element below the fold `elementFromPoint` can never answer, so the loop runs all 300 frames, 5 s, and then `_HIT_AREA_PROBE` scrolls the element into view (line 955) and measures.
- Evidence: 5.05, 4.99 and 4.99 s for three links on `/components`; 0.04 to 0.05 s when the element is scrolled into view first. 44 such burns in the browser group, 226 s: `test_browser_lighter_dialogs.py` 22 (113 s), `test_browser_design_system_fixes.py` 12 (60 s), `test_browser_ux_04.py` 6 (33 s), `test_browser_calendar_connect.py` 4 (20 s). Experiment with the scroll moved before the loop: `test_browser_design_system_fixes.py` 150.1 to 87.5 s, `test_browser_ux_04.py` 107.4 to 66.1 s, `test_browser_calendar_connect.py` 41.3 to 20.8 s, all tests pass.
- Not fixed by the scroll: `test_browser_lighter_dialogs.py:100` calls the probe on `dialog .modal__title`, and in 22 cases that title never owns its centre even in view. The cause there was not found; the file needs a wait on something the dialog really shows, for example `animation_settle.wait_settled(page, target=dialog)`.
- Saved: 113 s verified, up to 226 s. Mac: 0.5 to 1 min.
- Risk: low. The measurement step already scrolls the element to the same place, so the measured state is the same.
- Effort: one line in the helper; one call site to look at.
- Keeps every assertion and every executed test: yes.

### F4. The page-wide settle wait is held by the toast timer

- What: after an action that shows a toast, `page.wait_for_function(animation_settle.SETTLED)` waits for `skypane-toast-dwell` on `.toast__timer`, 6 s or 12 s (`companion/static/style.css:219`). The module docstring of `test-support/animation_settle.py` says such unrelated animations do not hold a test back; that is true of the scoped waits, not of `SETTLED`.
- Evidence: 45 waits, 312 s: `test_browser_airline_table.py` 12 (146 s), `test_browser_personalisation.py` 5 (51 s), `test_browser_fleet_users_fixes.py` 4 (25 s), `test_browser_airline_promotion.py` 2 (24 s), `test_browser_airline_named_missing.py` 2 (24 s), `test_browser_round11_fixes.py` 2 (12 s), `test_browser_airline_missing.py` 1 (12 s), `test_browser_airline_editor.py` 1 (12 s), and small ones in `test_browser_toasts.py` and `test_browser_motion_sheets.py`.
- Proposed fix: at those call sites wait on the element under test with `wait_settled(page, target=...)`.
- Saved: up to 312 s. Mac: about 1 min. Not run.
- Risk: medium. The assertion is the same, but it would run while the toast is still on screen, where today it runs after the toast has gone. A test that measures something the toast covers would change its result, so each call site needs a look. A test that really needs the toast gone should say so (one already does: `() => !document.querySelector('[data-toast]')`).
- Effort: about 30 call sites in 10 files.
- Keeps every assertion and every executed test: yes.

### F5. Shard weights are stale

- What: `scripts/ci_shard_weights.json` has no entry for 76 of the 182 browser files and 88 of the 372 core files, and 3 entries for files that no longer exist (`companion/test_browser_fleet_tabs.py`, `companion/test_console_locations.py`, `companion/test_health_connection_row.py`). A file without a weight counts one "second" per `def test_`, which ignores parametrisation.
- Evidence: the unweighted browser files weigh 370 in the packer and take 2,736 s. Examples (packer weight, measured seconds): `test_browser_components_fit.py` 5 and 269, `test_browser_lighter_dialogs.py` 7 and 198, `test_browser_style_leave.py` 18 and 194, `test_browser_page_opening.py` 25 and 182. The current 5 browser shards, valued with the measured durations, are 1,855, 1,936, 1,360, 1,643 and 1,481 s (slowest is 1.17 times the mean). The hosted run shows the same: 452 to 583 s (1.15 times the mean). Re-packed on measured durations: 1,655 s each. Core is balanced (993 and 1,036 s).
- Proposed fix: regenerate the file from the JUnit reports of a green run with `scripts/ci_shards.py weights`, after the fixes above since they change the durations. Give a file without a weight the median weight of its group instead of its `def test_` count.
- Saved: 13 to 15 percent of the slowest browser shard, 77 s on the hosted critical path. On the Mac it matters less than the job layout (F7).
- Risk: none for the assertions. `ci_shards.py check` still proves every file is in exactly one shard.
- Effort: small.
- Keeps every assertion and every executed test: yes.

### F6. A fresh server renders the look previews again for every test

- What: the preview cache lives under the state directory (`companion/theme_preview.py:294`), and 72 browser files start a server per test through `make_app_server`, each with a new state directory. The first `/display` of each server renders its previews.
- Evidence: on a quiet machine the first load of `/display` takes 0.83 s to navigate and 1.74 s to settle, the second 0.10 s and 0.67 s. Under a 4-worker run the cold loads take 2.3 to 5.7 s. `goto` calls of 0.25 s or more on the `/display` pages: about 420 calls, 523 s, against about 0.3 s per call on other pages. By file: `test_browser_personalisation.py` 105 s, `test_browser_style_leave.py` 71 s, `test_browser_personalisation_layout.py` 40 s, `test_browser_ux_03.py` 36 s, `test_browser_personalisation_fixes.py` 36 s. Subprocess start itself is 1,222 starts at 0.34 s, 416 s.
- Proposed fix: move the tests that only read the page to a module-scoped server (`module_app_server_factory`, already used by 70 browser files). In `test_browser_personalisation.py` the parametrised layout tests at lines 107, 146 and 194 are of that kind; the tests that save keep their own server.
- Saved: an estimate of 200 to 300 s; this is CPU time (image rendering), not waiting, so it also saves energy. Not run.
- Risk: low to medium, the usual one for a shared server: a test that writes must not be moved.
- Effort: medium, file by file.
- Keeps every assertion and every executed test: yes.

### F7. On the Mac the job layout costs more than any single test

- What and evidence, from run 1483: (a) 7 test jobs of 15 to 18 min on 2 runners means one runner does 4 and the other 3, so one runner was idle for the last 20 min. (b) Each test job pays 76 to 242 s outside the test step, 1,094 s in total, plus 35 to 60 s between jobs. The largest parts are the checkout (21 to 117 s) and "Cache Playwright browsers" (35 to 48 s), which restores from GitHub's cache a browser that the VM could keep on its own disk. (c) Each VM has 2 CPUs (`deploy/runner/lima-skypane-ci.yaml`), so xdist runs 2 workers.
- Proposed fix: take the shard counts from the runner type, so the Mac runs an even number of equal jobs, for example 1 core and 3 browser shards once F1 has shortened the core group. Restrict the two `actions/cache` steps to hosted runners. Keep pip's download cache and the Playwright browser in the VM.
- Saved: about 10 min from the idle runner, about 4 min from 3 fewer jobs, and 35 to 48 s per browser job from the cache step. About 15 min of wall-clock per Mac run.
- Not measured: more CPUs per VM. In this audit 4 workers on 4 vCPU ran the whole browser group in 2,094 s, where the Mac's two 2-CPU VMs spent 4,970 s of step time on it. Whether the Mac can give each VM 4 CPUs is the owner's call.
- Risk: none for the assertions. The static job's shard check and the aggregate job's artifact count must use the same counts as the matrix.
- Effort: medium (workflow and runner documentation, `deploy/tests/test_ci_runner.py` asserts on the workflow).
- Keeps every assertion and every executed test: yes.

### F8. Entrance animations: 1,800 s of waiting, removable only by changing how tests wait

- What: after almost every page load a test waits for the entrance animation (400 to 700 ms, 1,208 s in total) and for pictures to reveal (900 ms, 588 s).
- Experiment: with every page's animations played at 10 times speed through the DevTools protocol, `test_browser_overhaul_sweep.py`, `test_browser_more_scrim_cover.py`, `test_browser_page_title_phone.py`, `test_browser_frame_preview_shape.py` and `test_browser_save_bar.py` took 854 s of test time instead of 1,204 s (wall 219 s instead of 325 s). 1,046 of 1,047 tests passed; `test_browser_overhaul_sweep.py::test_an_administrators_personal_page_equals_a_users[/detection-360]` failed.
- Saved: about 29 percent on layout sweeps; perhaps 600 to 900 s over the browser group if applied only to files that assert layout and not motion.
- Risk: medium. No assertion changes, but timing does, and one test already depends on it. Tests about motion must be left at normal speed.
- This needs the owner's decision. It is not in the estimates of the summary.
- Keeps every assertion and every executed test: yes, if the failing test is understood first.

### F9. Smaller items

- `test_browser_sheet_keyboard_surface.py:59` and `:62` sleep 450 ms and 150 ms per sheet, 55 s in the file. A wait on the sheet's own animation would replace them. Low value.
- Fixed sleeps in total: 646 `wait_for_timeout` calls, 195 s, and 27 s of `time.sleep`. Most of them test real timers (idle warming at 4.5 s, the splash safety cap, the minute roll). Leave them.
- The aggregate job installs the whole development lock file (12 s hosted, plus a runner slot on the Mac) to run `coverage combine` and one stdlib script.

## Proposed PR plan

Small and independent. Each one keeps every test item and every assertion; the gates in `scripts/ci_gates.py` and the coverage floor are not touched.

| PR | Files | Change | Saves (test time) | Owner decision |
|---|---|---|---|---|
| 1 | `test-support/companion_app_server.py`, `test-support/fake_auth0.py`, `test-support/fake_anthropic.py`, `companion/test_browser_origin.py` | pass a short `poll_interval` to `serve_forever` | about 1,200 s | no |
| 2 | `companion/test_browser_ux_helpers.py`, `companion/test_browser_lighter_dialogs.py` | scroll the element into view before the stable-centre loop; wait on the dialog in the one file where the title never owns its centre | 113 to 226 s | no |
| 3 | `companion/conftest.py`, `companion/test_browser_components_page.py`, `companion/test_browser_components_fit.py`, `companion/test_suite_guards.py` | module-scoped guarded context; one page per parameter set for read-only tests; explicit wait for the save-bar specimen | 600 to 760 s | no, but review the shared-page fixture |
| 4 | about 10 browser files listed in F4 | target-scoped settle wait after an action that shows a toast | up to 312 s | no, review each call site |
| 5 | `test_browser_personalisation.py`, `test_browser_style_leave.py`, `test_browser_personalisation_layout.py`, `test_browser_personalisation_fixes.py`, `test_browser_ux_03.py` | module-scoped server for tests that only read `/display` | 200 to 300 s (estimate) | no |
| 6 | `scripts/ci_shard_weights.json`, `scripts/ci_shards.py`, `test-support/test_ci_shards.py` | regenerate weights after PRs 1 to 5; median fallback for a file without a weight; drop 3 stale entries | 13 to 15 percent of the slowest browser shard | no |
| 7 | `.github/workflows/ci.yml`, `deploy/runner/README.md`, `deploy/tests/test_ci_runner.py` | shard counts by runner type (even number of jobs on the Mac); cache steps on hosted runners only | about 15 min wall on the Mac | yes: shard counts, and whether the VMs get 4 CPUs |
| 8 | `companion/conftest.py` and the layout-sweep files | faster animation playback for layout-only tests | 600 to 900 s (estimate) | yes |
| 9 | `scripts/ci_gates.py` | raise the executed-test floor from 12,821 to the current count | none; closes a gap | yes |

PR 1 first: it is the largest and the safest. PR 6 after the others, since they change the durations it records.

### Estimated wall-clock after PRs 1 to 7

- Mac, 2 runners of 2 workers: test steps go from 7,160 s to about 5,800 s of runner time (F1 600 s, F2 about 340 s, F3 about 110 s, F4 about 125 s, F6 about 150 s). With 4 equal jobs and no idle runner that is about 49 min of tests plus about 5 min of job overhead: about 55 min against 82 min today. With PR 8, about 50 min. With 4 CPUs per VM, an unmeasured estimate of 30 to 35 min.
- Hosted, 4 workers per shard: core shards from about 325 s to about 220 s; browser shards from 452 to 583 s to about 415 s each. Wall-clock from 11.3 min to about 8.5 min, billable minutes from 62 to about 50. On 2-vCPU runners these figures would be higher; that was not measured.

These are projections from the measurements above, not measured runs.

## Not worth touching

- Browser, context and page fixtures. The browser is launched once per worker (4 launches, 0.06 s each). A fresh context per test costs 8 ms to open, 11 ms to close and 43 ms for its page.
- Coverage. The sysmon core is already selected and costs 17 percent on the core sample; the C tracer would cost 72 percent.
- Collection: 9.6 s and 7.2 s per worker for the whole groups, less per shard.
- pytest-socket, the DNS guard and JUnit output: the 1,747 core setups under 0.1 s sum to 43 s with everything else in them.
- The golden hashes and the freeze test: `stub-server/test_phase47_freeze.py` 7.9 s, `server/test_golden_giant_render.py` 18.3 s.
- The CPU-bound core tests: `hardware/test_wakemodel.py` 35 s, `server/test_check_interval_redraw.py` 44 s, `deploy/tests/test_activate.py` 49 s, `server/test_poll_loop.py` 43 s, `server/test_giant_aircraft.py` 42 s. They do real rendering and real subprocess work; caching a baseline would save a few seconds each.
- `companion/test_access_matrix.py`: 1,960 tests in 10 s.
- Subprocess server start, 0.30 to 0.35 s. It is the price of a real process; module scope is already the convention.
- The static job: 42 s on hosted runners, and no test repeats what it checks.
- xdist distribution mode. A module-scoped server is started once per worker that meets the module, which costs about 0.35 s each time.
- More workers than CPUs for browser shards: the CPU was already 64 to 76 percent busy. Not measured further.

## Latent test-quality problems noticed

- The `/components` tests measure the right page state only because an 8 s spinner outlasts a 6 s toast timer (F2). If the spinner were shortened, the save-bar specimen would silently drop out of the overflow, target and overlap checks, which only look at visible elements.
- `_SETTLE_PROBE` gives up after 300 frames without an error, so a wait that never succeeds looks like a wait that did (F3, `test_browser_lighter_dialogs.py:100`).
- `animation_settle.SETTLED` is held by toast timers, against what the module's docstring suggests (F4).
- One test fails when animations run faster (F8), which suggests it could also fail on a slow machine.
- The executed-test floor is 12,821 and the suite runs 17,506, so about 4,700 tests could disappear before the gate noticed.
- Nothing keeps `ci_shard_weights.json` in step with the test files (F5).
- pytest warns that pytest-playwright's session-scoped `base_url` fixture is defined as an instance method, which pytest 10 will refuse.
- The local venv is Python 3.13 while CI and production are 3.14.

## Risks and what must be preserved

- No test is removed, skipped or merged in any proposal: the executed count stays at 17,506 and the skipped count at 0 in CI.
- No assertion text changes in PRs 1, 2, 5, 6 and 7. PRs 3 and 4 change when or on which page object an unchanged assertion runs; they need review for shared state (PR 3) and for a toast still on screen (PR 4).
- Browser tests keep running on every code change, and they still drive a real Chromium against served pages. No proposal reads source text or `.planning/`.
- `scripts/ci_gates.py`, the coverage floor in `pyproject.toml` and the shard completeness check are unchanged, except PR 9, which only raises a floor.
- `stub-server/test_phase47_freeze.py` and the golden hashes are not touched by any proposal.
- A new shared context fixture must install the same loopback route guard as `new_context` and fail on a blocked request, or the network guard would be weaker for the tests that use it.
- Comments added by these PRs are in English and carry no plan or phase identifiers.

## Not measured

- Anything on the Mac itself, and anything on Python 3.14.
- Coverage overhead on the browser group.
- The fixes for F2, F4 and F6 were not run; their savings are computed from measured causes.
- Why the `/detection` test fails under faster animations, and why the dialog title in `test_browser_lighter_dialogs.py` never owns its centre.
- The number of vCPUs of the hosted runner (inferred as 4 from the weights).
- Why the Mac run 1483 failed in `static` and in one browser shard.
