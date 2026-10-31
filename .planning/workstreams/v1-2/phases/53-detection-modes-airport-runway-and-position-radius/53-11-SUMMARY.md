---
phase: 53-detection-modes-airport-runway-and-position-radius
plan: 11
subsystem: detection-gates
tags: [tests, kill-switch, gates]
requires: [53-05, 53-07, 53-08, 53-09, 53-10, 53-12]
key-files:
  created:
    - server/test_detection_kill_switch.py
  modified:
    - .planning/workstreams/v1-2/phases/53-detection-modes-airport-runway-and-position-radius/53-VALIDATION.md
requirements-completed: [DET-01, DET-02, DET-03]
completed: 2026-10-31
---

# Phase 53 Plan 11: Final gates Summary

The kill switch is proven end to end through `run_fleet`, and every repository gate and owner constraint passes with the whole suite (browser tests included) at 96.09 % coverage against the unchanged floor of 93.

## Commits

- f7700d8 kill-switch integration test through the fleet cycle
- the SUMMARY / VALIDATION commit (docs)

## Task 1: kill-switch test (`server/test_detection_kill_switch.py`, 12 tests)

Fleet of a live Orly device (default config), an LFPG 08L/26R device and a position device (48.8566, 2.3522, 9 km), driven through `fleet_cycle.run_fleet` with the real `detection_resolver` and the real `poll_cycle.run_once`, a fake fetcher and ledger (offline).

- `test_kill_switch_on_*`: with the switch on, the live device's resolved document equals `adsb-test/runway3.json`, its zone key is `48.7233|2.3794|5.0`, the LFPG and position zone keys are unchanged, and each distinct zone is fetched exactly once (3 fetches). Catalogue and position specs are identical with the switch on or off.
- `test_kill_switch_off_serves_orly_with_identical_observable_output`: same zone key, different (generic) document, identical panel.bin SHA-256, identical fetch list, and the poll state selects the injected aircraft in both runs.
- `test_kill_switch_value_rule`: the accepted rule in `server/detection.py` is exactly `== "1"` (as the plan assumed); "0", "", "true", "yes", " 1", "1 " and "2" do not enable it. No production change was needed.
- `test_config_bytes_unchanged_by_switch`: `device_config.json` bytes of all three devices are identical before, with the switch on and with it off, after a full fleet cycle.
- `test_catalogue_device_ignores_switch`: an LFPG device is unaffected; Orly reached through the catalogue (LFPO 07/25) still maps to the legacy id and is governed by the switch.

Verify command (kill switch + orly replay + pipeline + freeze): 70 passed. `git diff --stat stub-server/` is empty.

## Task 2: gates (all exit 0)

| Gate | Result |
|------|--------|
| Render baseline regenerated (`PYTHONPATH=. server/.venv/bin/python test-support/companion_render_snapshot.py --write`) | `git diff` shows no change (the script needs `PYTHONPATH=.` when run directly) |
| `SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh` (browser path via scratch `PLAYWRIGHT_BROWSERS_PATH` with 1248 symlinks to the installed 1243 builds, outside the repo) | 7595 passed, 8 skipped (root ignores permission bits: 7; openssl cannot backdate a certificate: 1), 0 failed, 472 s |
| Coverage | 96.09 % (18995 statements, 742 missed) against `fail_under = 93`; floor not touched ("Required test coverage of 93.0% reached") |
| `ruff check .` | All checks passed |
| `mypy` | Success: no issues found in 28 source files |
| `check_function_size.py check --max 80 server stub-server` | 905 functions scanned, none over 80 |
| `check_comment_history.py check` | exit 0 |
| `stub-server/test_phase47_freeze.py` | 21 passed, file unmodified |
| `scripts/run-local-verify.sh` | only launches the companion app locally; adds no gate |

## Owner-constraint checks (base 42aa033797d5b3bb699130c87f5b6bd15e0834cc)

- (a) `git diff --name-only <base>` filtered for `hardware/`, `deploy/`, `stub-server/`, "admin", `measured_fields`: empty. No Phase 47 file, no hardware, no deploy, no admin-console file, no `/locations` placeholder change. Nothing was deployed.
- (b) `git diff <base> -- server/requirements.txt server/requirements-dev.txt server/requirements.in`: empty (0 bytes). `pyproject.toml` diff: only four added lines, `server/airports.py` and `server/detection.py` in the mypy `files` list and in the strict override module list.
- (c) `grep -rnE "\bnm\b|NM " companion/pages/detection_page.py companion/detection_actions.py`: no match (no user-visible NM string).
- (d) `server/test_runway_config.py::test_previous_release_reader_still_sees_the_old_keys` and the freeze test pass (also inside the full run).
- (e) `server/test_position_rounding.py` passes (4 selected tests re-run; also in the full run).
- Doc check from the validation map: `## OurAirports` 1, `Seven sources` 1, `rounded to two decimals` 1.

## Files outside the plans' declared `files_modified` lists

`git diff --name-only <base>` minus the union of all 53-*-PLAN.md `files_modified`, excluding the phase's own planning directory:

- `.planning/workstreams/v1-2/ROADMAP.md` (shared with the other session, not touched by this plan; flagged for the verifier)
- `companion/detection_summary.py` (new, 65 lines; shared Detection card sentence, commit 7955ebd, plan 09)
- `companion/flash.py` (commits e1b8b05 plan 08, b1a24d0 plan 06; flash messages for the detection flow)
- `companion/i18n_fr/registry.py` (commit f8ab9c3, plan 09; French registry entries for the removed/new strings)
- `companion/test_device_routes.py` (commit b1a24d0, plan 06; route table expectation)
- `companion/test_i18n.py` (commit e1b8b05, plan 08; i18n registration of new strings)
- `server/fleet_db.py` (commit 578f505, plan 05; per-device location read for the fleet cycle)

Plans 06, 08 and 09 recorded these as Rule 3 deviations in their own summaries. `git status` after the final gate run showed no stray or untracked files.

## Requirement and decision coverage

All rows of 53-VALIDATION.md's per-task map ran in the full suite (7595 passed) and are now marked green; its frontmatter has `nyquist_compliant: true` and `wave_0_complete: true`. Nothing is unproven by automation; the two manual-only items (look of the page and tag on a real panel, owner confirmation of the policy numbers) remain for the owner and are outside this phase (no deploy).

| Item | Proven by |
|------|-----------|
| DET-01 (airport/runway choice) | 53-01 catalogue tests, 53-04 storage/settings, 53-06 page + access matrix, 53-09/12 Display/Device cards, 53-10 browser |
| DET-02 (parallel runways, Orly identical) | 53-01 half-width tests, 53-02 replay + sweep, 53-05 pipeline equality, 53-11 kill switch |
| DET-03 (position radius) | 53-03 gate/bounds/rounding, 53-05 zone sharing, 53-08 position page, 53-10 browser |
| D-01, D-04, D-18 (catalogue, exclusions, floor) | test_airports_catalogue.py |
| D-02, D-12, D-24 (Phase 52 zones, rounding, km to NM) | test_fleet_cycle.py, test_position_rounding.py, test_detection_spec.py |
| D-03, D-09 (no deploy) | owner check (a): no deploy/ change |
| D-05, D-06, D-07 (pair, tag, half-width) | test_airports_catalogue.py, test_detection_spec.py, test_render*.py |
| D-08, D-20 (Orly switch, identical replay, kill switch) | test_orly_replay.py, test_detection_pipeline.py, test_detection_kill_switch.py, test_phase47_freeze.py |
| D-10, D-11, D-13, D-22, D-25, D-26 (position mode) | test_plane_detection.py, test_detection_position.py, test_detection_pipeline.py |
| D-14, D-16 (route, OWNER_DEVICE) | test_access_matrix.py, test_route_table.py, test_detection_page.py |
| D-15, D-27 (no-JS page, UI constraints) | test_detection_page.py, test_browser_detection.py |
| D-17 (locations, no admin-console change) | test_detection_position.py, owner check (a) |
| D-19 (Runway card removed) | test_config_page_*.py, test_display_detection_card.py, 53-12 re-pointed tests |
| D-21 (one spec for fetch, select, render) | test_detection_pipeline.py, test_render.py |
| D-23 (compliance and credits) | test_compliance_credits.py, test_credits_page.py, COMPLIANCE.md grep |
| GOAL 1 to 3 | the DET-01 to DET-03 rows above |

## Deviations from Plan

- The plan said not to commit in Task 2; the orchestrator instructions asked for a SUMMARY commit, so the VALIDATION update is committed with the SUMMARY.
- STATE.md and ROADMAP.md were deliberately not touched, per the orchestrator.
- No production code changed; no defects were exposed by the new test.

## Self-Check: PASSED

Created `server/test_detection_kill_switch.py` (commit f7700d8); all gate outputs above were observed in this session.
