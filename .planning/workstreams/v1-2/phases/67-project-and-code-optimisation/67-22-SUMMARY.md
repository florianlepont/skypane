---
phase: 67-project-and-code-optimisation
plan: 22
subsystem: server
tags: [cleanup, history_db, fleet_db]
requirements-completed: [QUAL-01]
key-files:
  modified: [server/history_db.py, server/fleet_db.py, server/test_fleet_schema3.py]
metrics:
  completed: 2026-11-28
---

# Phase 67 Plan 22: Leftovers (partial) Summary

Removed `META_LAST_POLL_TRIGGER` and the three unused `fleet_db` location helpers (gate G5 approved); `wake_epochs` kept (gate G4 = KEEP); test floor unchanged.

## Task 1 (G5 approved): done

Commit `870349c4`.

Removed names:
- `server/history_db.py`: `META_LAST_POLL_TRIGGER` and its entry in `_STATUS_META_KEYS`. A stored `last_poll_trigger` row, if any, is ignored by `export_status_meta`; no data or schema touched.
- `server/fleet_db.py`: `delete_location_if_unused`, `count_locations_owned`, `location_usage_counts`.

Evidence: `git grep -nIw` for the four names plus `last_poll_trigger` over the whole tree (code, tests, units, deploy, docs) found only the definitions, the one filter entry, the three assertions groups in `server/test_fleet_schema3.py`, planning documents and two lines of `ARCHITECTURE.md`. No production caller, no unit or deploy reference. Kept: `META_PROVIDER_LAST_CALL_PREFIX` (used by `export_status_meta` and `server/test_provider_rate.py`); `LocationInUse` (class left defined, now unreferenced apart from its definition; not in this plan's list, flagged for plan 24).

Tests: no test id removed. Assertions removed (D-12) from `test_location_visibility_by_owner` (`count_locations_owned`) and `test_update_and_delete_location` (`location_usage_counts`, the LocationInUse raise and both `delete_location_if_unused` calls); every other assertion kept. Collected-id diff origin/main vs branch: identical (17,694 each).

## Task 2 (G4): kept: owner decision G4 = KEEP

No `wake_epochs` drop, no history schema 2, no change to writers, readers or tests.

## Task 3: MIN_EXECUTED unchanged

Collected 17,694 >= `MIN_EXECUTED` 17,591, so nothing changed in `scripts/ci_gates.py`.

## Lines for plan 23 (not edited here)

`ARCHITECTURE.md` lines 895-898 (item 3, names `META_LAST_POLL_TRIGGER`; `META_PROVIDER_LAST_CALL_PREFIX` stays) and lines 907-910 (item 6, the three helpers, "tests still use them"). `deploy/README.md`: no mention.

## Checks

pytest (all non-browser suites, 13,020 passed, 0 failed; browser tests skipped, Chromium not installed here), freeze test, goldens, fleet_db/history_db/config_history/status-export, access-matrix and backup tests inside that run; mypy clean; ruff clean; function-size (3,390 functions, none over 80); comment-history clean; exposure scan shows only the pre-existing findings in untouched lines.

## Deviations

Branch: commit guard allows `worktree-agent-*` only, so the commit is on `worktree-agent-af32fb1f5300ed44e` (based on origin/main 091dd371), not `phase-67-22-leftovers`. No PR opened.
