---
phase: 67-project-and-code-optimisation
plan: 24
subsystem: tests-and-dead-code
tags: [dead-code, test-only-api, ci-floor]
requires: [67-08, 67-09, 67-10]
provides:
  - 67-TEST-ONLY-API.md (evidence list, owner decisions recorded)
  - four test-only functions and their seven tests removed
  - MIN_EXECUTED lowered once, 17,598 to 17,591
key-files:
  modified:
    - server/fleet_cycle.py
    - companion/airline_collection.py
    - companion/resolve_dialog.py
    - companion/draw.py
    - scripts/ci_gates.py
  created:
    - .planning/workstreams/v1-2/phases/67-project-and-code-optimisation/67-TEST-ONLY-API.md
decisions:
  - "Owner 2026-11-27: DELETE only the four names without a MIXED test; KEEP the other 23 (many tests to rewrite, 8 touch Phase 66 audited code); no AUDITED name ticked."
metrics:
  completed: 2026-11-27
---

# Phase 67 Plan 24: Test-only API Summary

Derived 27 functions that only tests call (not the ~30 estimated), the owner approved deleting the 4 with no MIXED test, and those 4 functions plus their 7 exclusive tests are gone; the executed-test floor went from 17,598 to 17,591.

## Tasks

| Task | Result | Commit |
|------|--------|--------|
| 1 Derive the list | 27 names, evidence table | 858d307e |
| 2 Owner checkpoint | 4 DELETE, 23 KEEP, recorded in the document | with this summary |
| 3 Delete approved names | one commit per name | c7b44bd4 `geofence_resolver`; f2e3d0d2 `sightings_across`; 18bd7e84 `step_b_trigger_html`; 9d7be649 `regularity_grid` |
| 4 Lower the floor | 17,598 to 17,591 | 69234efb |

Re-verification before deleting: each of the four names has no mention in any tracked file outside `.planning/` other than its definition and its tests, and every test that calls it is about it alone (no MIXED test).

## Removed test ids (7), each with its function

- `server/test_fleet_cycle.py::test_default_resolver_gives_every_device_the_geofence_zone` (`geofence_resolver`)
- `server/test_fleet_cycle.py::test_default_resolver_with_missing_geofence_raises_oserror` (`geofence_resolver`)
- `companion/test_airline_collection.py::test_sightings_across_frames_are_merged_newest_first_and_counted_together` (`sightings_across`)
- `companion/test_device_links.py::test_step_b_trigger_addresses_stay_in_the_device_and_return_stays_plain` (`step_b_trigger_html`)
- `companion/test_status_pages_02.py::test_regularity_grid_has_four_states_and_never_conflates_them` (`regularity_grid`)
- `companion/test_status_pages_02.py::test_regularity_grid_cells_are_sized_from_the_360px_floor` (`regularity_grid`)
- `companion/test_status_pages_02.py::test_regularity_grid_is_bounded_and_keeps_the_newest_buckets` (`regularity_grid`)

## Proof

- Collected ids (`pytest --collect-only -q`, whole repo, sorted): 17,603 before (branch merged with origin/main, document only) and 17,596 after. `comm -13` (new ids): 0 lines. `comm -23` (missing ids): exactly the seven ids above.
- Freeze test and golden tests (render and giant render) pass without edit; no change under `server/fixtures` or `companion/testdata`.
- ruff, mypy (56 files), function-size (1,266 functions, none over 80), comment-history guard: clean.
- Non-browser suite over server, stub-server, companion, deploy, test-support and scripts: 12,529 passed, 8 skipped (root-environment permission tests and one openssl skip, not related to this change).

## Floor change

`MIN_EXECUTED` 17,598 to 17,591: a drop of 7, equal to the removed-id count, so it does not exceed it. This is the only lowering by this plan. The new value is the old floor minus the removed ids (not the collected count: collected is 17,596, and the previous floor was already below it). The comment in `scripts/ci_gates.py` records the date and reason without a decision id, because the comment-history guard forbids decision ids in comments (the plan text asked for the id; the repository rule wins). `test-support/test_ci_gates.py` follows the constant and needed no edit (14 passed). MAX_SKIPPED stays 0.

Floor confirmed by the draft PR's green CI run: PENDING.

## Deviations from Plan

- [Rule 3] Removing `step_b_trigger_html` left six unused imports in `companion/resolve_dialog.py` (ruff F401) and a stale module docstring; both were cleaned up in the same commit.
- No KEEP name and no AUDITED name was touched.

## Follow-ups (not done, outside the approved names)

- `companion/resolve_dialog.py`: `_return_query` and `_trigger_attrs_html` now have no caller.
- `companion/draw.py`: `grid_columns`, `grid_cell_size`, `cell_class` and the grid constants may now be used only by tests or nowhere.
- The 23 KEEP names, the "considered" names and `airport_label`, `battery_dropped`, `FleetResult.live_outcome` remain open in 67-TEST-ONLY-API.md.

## Self-Check: PASSED

Commits 858d307e, c7b44bd4, f2e3d0d2, 18bd7e84, 9d7be649 and 69234efb exist on the branch.
