---
phase: 67-project-and-code-optimisation
plan: 14
subsystem: server
tags: [module-move, shims, polling]
requirements: [QUAL-01]
key-files:
  created:
    - server/polling/__init__.py
    - server/test_module_shims_polling.py
  modified:
    - server/polling/request_budget.py (moved from server/request_budget.py)
    - server/polling/zone_fetch.py (moved from server/zone_fetch.py)
    - server/polling/http_fetch.py (moved from server/http_fetch.py)
    - server/polling/fleet_zones.py (moved from server/fleet_zones.py)
    - server/polling/fleet_cycle.py (moved from server/fleet_cycle.py)
    - server/request_budget.py
    - server/zone_fetch.py
    - server/http_fetch.py
    - server/fleet_zones.py
    - server/fleet_cycle.py
    - pyproject.toml
decisions:
  - poll_loop.py and poll_cycle.py stay in place (systemd ExecStart path, many importers).
  - Old flat names are sys.modules alias shims with a TYPE_CHECKING-only star import so mypy follows the shim.
---

# Phase 67 Plan 14: Polling package move Summary

request_budget, zone_fetch, http_fetch, fleet_zones and fleet_cycle now live in `server/polling/`; the old flat names are `sys.modules` alias shims, so every importer and `monkeypatch`/`mock.patch` site keeps working unchanged. Request-budget logic, ledger format and lock behaviour are moved verbatim.

## Tasks

1. Shim tests first (identity, package attribute, patch-through-alias, cross-module patch reaching zone_fetch, `poll_loop.py --help` and old-name imports from a foreign cwd), then `git mv` and shims. None of the five modules uses `__file__`, so no bootstrap needed adjusting. Imports among the moved modules (zone_fetch, fleet_cycle) now use `server.polling.*`; all outside importers keep the old names.
2. pyproject.toml: mypy file list and strict-module entries substituted to the new paths (path substitution only; file count unchanged at 56).

## Verification

- Collected ids origin/main (17610) vs branch (17628): nothing removed; only 18 new `test_module_shims_polling.py` ids added.
- `python3 server/poll_loop.py --help` works from a foreign cwd; no moved module has a `-m`/`__main__` entry point.
- deploy/tests/test_units.py, test_import_boundaries.py: pass; `deploy/` and poll_loop.py untouched.
- mypy, ruff, function-size gate (3412 functions, none over 80), comment-history: green.
- Core group (`SKYPANE_TEST_GROUP=core`, includes golden and freeze tests): 12879 passed, 7 skipped (root-permission skips). Browser tests not run locally; CI is the check.

## Deviations

None - plan executed as written. mypy needed no extra handling beyond the TYPE_CHECKING star import already established by plan 13.

## Retained shims

`server/request_budget.py`, `server/zone_fetch.py`, `server/http_fetch.py`, `server/fleet_zones.py`, `server/fleet_cycle.py`.

## Untouched

systemd units, poll_loop.py, poll_cycle.py, fleet_db, history_db, device_config, ARCHITECTURE.md (plan 15), STATE.md, ROADMAP.md.

## Self-Check: PASSED
