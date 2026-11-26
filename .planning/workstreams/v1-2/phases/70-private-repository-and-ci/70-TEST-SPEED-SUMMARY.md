# Phase 70: test-suite speed, items 1 to 6 of the audit

Implements items 1 to 6 of the "Proposed PR plan" of `70-TEST-AUDIT.md` on one branch, one commit per item. Items 7 (shard counts and VM CPUs in `ci.yml`), 8 (faster animation playback) and 9 (executed-test floor) need owner decisions and are not touched, nor are `scripts/ci_gates.py`, the coverage settings or `.github/workflows/`.

All timings: Linux container, 4 vCPU, Python 3.13, `pytest -n 4`, no coverage, wall-clock seconds, the same files run before and after each item with the earlier items already applied. Run as root, so 7 core tests and 1 browser test skip (permission bits), as in the audit.

## Per item

| # | Change | Files run | Tests | Before | After | Saved |
|---|---|---|---|---|---|---|
| 1 | `serve_forever(poll_interval=0.01)` in the four in-thread test servers | 5 core files named in the audit, `test_browser_origin.py`, `test_browser_toasts.py` | 347 | 58.6 s | 17.6 s | 41.0 s |
| 2 | Hit-area settle probe scrolls the element into view first; lighter-dialogs helper waits on the dialog's animations instead of the title's hit-test | `test_browser_lighter_dialogs.py`, `_design_system_fixes.py`, `_ux_04.py`, `_calendar_connect.py` | 125 | 143.4 s | 61.6 s | 81.8 s |
| 3 | `/components`: module-scoped guarded context, one page per width/theme/language for read-only tests, explicit wait for the save-bar specimen | `test_browser_components_page.py`, `_components_fit.py` | 116 | 236.4 s | 119.1 s | 117.3 s |
| 4 | Settle wait that ignores a toast's own animations | 10 files of finding F4 | 204 | 209.7 s | 163.6 s | 46.1 s |
| 5 | Module-scoped server for tests that only read `/display` pages | `test_browser_personalisation.py`, `_style_leave.py`, `_personalisation_layout.py`, `_personalisation_fixes.py` | 152 | 195.7 s | 117.0 s | 78.7 s |
| 6 | Weights regenerated, median fallback | n/a | n/a | slowest browser shard 1.205 x mean | 1.014 x mean | see below |

Item 4 was measured with a timing plugin attached in both runs (it adds one `evaluate` per wait). Item 6 is a simulation on the measured per-file durations of the full runs below: the five browser shards come to 1,333, 1,335, 1,292, 1,333 and 1,290 s (they were 1,584 to 1,586 s at the slowest with the old file), the two core shards to 537 and 522 s (557 at the slowest before).

## Full runs after item 5 (`-n 4`)

| Group | Result | Wall |
|---|---|---|
| core (372 files) | 12,803 passed, 7 skipped (root) | 282.5 s (audit: 529 s on 12,768 tests) |
| browser (183 files) | 4,736 passed, 1 skipped (root), 1 failed | 1,664 s (audit: 2,094 s on 4,738 tests) |

The one browser-group failure is `test-support/test_ci_shards.py::test_heavy_files_land_in_different_shards_and_the_result_is_stable`. That file is in the browser group because its source mentions the browser marker. The run was in progress while item 6 changed `scripts/ci_shards.py` (median fallback) before the test input was updated, so it failed on the half-finished change. After the item 6 commit the file passes (27 tests). The two full runs are not an untouched before/after comparison with the audit's: the tree also moved by two test files and later main commits.

## Test items

`pytest --collect-only -q` of the whole suite: 17,544 before, 17,552 after. No test id was removed (`comm` of the sorted lists: 0 only in the old list). The 8 new ids are 3 new cases and 1 new module scan in `companion/test_suite_guards.py` (for the new fixture and helper module) and 4 tests in `test-support/test_ci_shards.py`. In the four item 5 files the collected ids are identical before and after (152).

## Per item notes

1. `serve_forever` polls for shutdown every 0.5 s by default; the four servers now poll every 0.01 s. Production code untouched.
2. The scroll uses the same `scrollIntoView({block: 'center', inline: 'center'})` as the measuring step, so the measured state is unchanged. In `test_browser_lighter_dialogs.py` the title never owned its centre (cause not found, as in the audit); the helper now calls `animation_settle.wait_settled(page, target=dialog)`, which awaits every finite animation on the dialog and its subtree. The 125 tests, which measure geometry and contrast of the dialogs, pass.
3. `module_new_context` in `companion/conftest.py` installs the same loopback route guard and splash opt-out as `new_context` and fails the module's last test at teardown if a non-loopback request was blocked. Guard rule G10 accepts `browser.new_context` only inside that function of that file; both a positive and a negative self-test cover it. The two dialog tests (they open a dialog) and the reduced-motion test keep pages of their own. The spinner specimen's 8 s animation is finished by script and the save-bar specimen is waited for explicitly (it appears when the toast specimen's own 6 s timer ends), so a page is measurable after about 6 s instead of 8.3 s. A temporary test (not committed) loaded `/components` at all 8 parameter sets with the old wait and the new one and compared every probe result of both files plus every specimen box to 0.1 px: identical. With xdist each worker loads its own copy per parameter set, so the number of loads is between 8 and 32 per file.
4. `animation_settle.SETTLED_APART_FROM_TOASTS` ignores animations inside `.toast` (the entrance and the 6 or 12 s dwell timer). It replaces `SETTLED` in six files: `test_browser_airline_table.py`, `_airline_editor.py`, `_airline_missing.py`, `_airline_named_missing.py`, `_airline_promotion.py`, `test_browser_personalisation.py`. Reasoning per file: the toast is a fixed overlay (`position: fixed` under scripting), every step after the wait reads DOM, files, audit rows or box geometry (unaffected by an overlay) or clicks through Playwright's actionability wait (which retries while the toast covers the target), and `_settle` scrolls its target to the viewport centre first. A test that needs the toast gone must say so; none of these did.
5. 37 test functions that never POST and never store anything moved to `module_app_server_factory` servers (one or two per file). Every test that saves keeps its own function-scoped server, so the shared servers are never written.
6. How the weights were made: `scripts/ci_shards.py files core 0 1` and `files browser 0 1` give the file lists; `pytest -n 4 --junitxml=junit-core.xml <core files>` and the same for the browser files; `scripts/ci_shards.py weights junit-core.xml junit-browser.xml > scripts/ci_shard_weights.json`. The documentation is also in the docstring of `scripts/ci_shards.py`.

## Skipped, and why

- Item 4, `test_browser_fleet_users_fixes.py` (line 76): the wait for `!document.querySelector('[data-toast]')` is explicitly about the toast going.
- Item 4, `test_browser_round11_fixes.py` (line 122): the wait is held by the switch ring animation on the switch being measured as well as the toast; not a call site where the meaning is provably unchanged.
- Item 4, `test_browser_toasts.py`, `test_browser_motion_sheets.py`: tests about toasts and sheet motion; their waits were short (under 1.5 s) in the measurement.
- Item 5, `test_browser_ux_03.py`: already shares a module server for its read-only tests; its remaining per-test servers save settings.
- Item 5, tests in the four files that save or submit (layout C saves, save and continue, the no-scripts save, the giant-layout pairing, the floating-bar save, the picker save): they keep their own server.
- `test_browser_design_system_fixes.py` still loads `/components` per test (8 s waits remain there, 4 tests of about 8.4 s after item 2); it is not in the audit's item 3 file list.

## Not verified

- Anything on the Mac runners or Python 3.14; no CI run was made, and nothing was run with coverage.
- Fixed-overlay reasoning for item 4 is by reading the stylesheet and the call sites and by the passing runs; no screenshot comparison with and without the toast was made.
- The per-item timings are single runs; run-to-run variation on this machine was not measured. No flaky result was seen in the runs reported here.
- The effect of the new weights on real CI shard times is a simulation, not a CI run.
