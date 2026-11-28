---
phase: 67-project-and-code-optimisation
plan: 15
subsystem: server
tags: [module-move, shims, pairing, architecture]
requirements: [QUAL-01]
key-files:
  created:
    - server/pairing/__init__.py
    - server/test_module_shims_pairing.py
  modified:
    - server/pairing/pairings.py (moved from server/pairings.py)
    - server/pairing/code.py (moved from server/pairing_code.py)
    - server/pairing/image.py (moved from server/pairing_image.py)
    - server/pairings.py
    - server/pairing_code.py
    - server/pairing_image.py
    - pyproject.toml
    - ARCHITECTURE.md
decisions:
  - poll_loop.py, poll_cycle.py, fleet_db, history_db and device_config stay in place.
  - Old flat names are sys.modules alias shims with a TYPE_CHECKING-only star import.
---

# Phase 67 Plan 15: Pairing package move Summary

pairings, pairing_code and pairing_image now live in `server/pairing/` as `pairings.py`, `code.py` and `image.py`; the old flat names are `sys.modules` alias shims. ARCHITECTURE.md describes all three moves (firmware, polling, pairing) and carries a "Compatibility shims" note.

## Tasks

1. Shim tests first (identity, package attribute, patch-through-alias, cross-module patch reaching `pairing.image`, old-name import from a foreign cwd), then `git mv` and shims. Verbatim-move proof (diff of origin/main file vs moved file):
   - `pairings.py`: only the repo-root bootstrap changed (`_REPO_ROOT = dirname(dirname(_HERE))`, comment `server/pairing/`).
   - `code.py`: no changes.
   - `image.py`: only the import `from server import ... pairing_code ...` became `from server.pairing import code as pairing_code` (the local name is kept, so no logic line changed).
2. pyproject.toml: mypy file list and strict-module entries substituted (`server/pairing/pairings.py`, `server/pairing/code.py`, `server/pairing/image.py`, `server.pairing.code`, `server.pairing.pairings`); path substitution only, mypy source count unchanged at 56.
3. ARCHITECTURE.md: module map, data-flow diagram and prose updated to the new paths; "Compatibility shims" note added. The backticked-path script resolves every path (exit 0) and names the three package paths. The "Persistent state" statements were not touched (plans 17-23 own them; this plan does not list them).

## Verification

- Collected ids: the before and after lists are identical apart from the new `test_module_shims_pairing.py` ids (11 new, none removed).
- `python3 server/poll_loop.py --help` works; no moved module has a `-m` entry point.
- deploy/tests/test_units.py, test_docs.py, server/test_import_boundaries.py: pass. `-k "pairing or access_matrix"`: 2165 passed, 52 skipped (browser tests: no Chromium here).
- mypy (56 files), ruff, function-size gate (3412 functions, none over 80), comment-history: green.
- Exposure scan: no hit in ARCHITECTURE.md (existing test-file e-mail hits in companion tests are pre-existing).
- Core group (golden and freeze tests included, unchanged hashes): 12891 passed, 7 skipped (root-permission and openssl skips). Browser tests not run locally; CI is the check.

## Deviations

- The plan text says the shims serve "the `-m` entry points"; no moved module has one, so the ARCHITECTURE.md note says the shims keep importers, tests and monkeypatch sites working instead.
- ARCHITECTURE.md diagram lines use the shortened `polling/zone_fetch.py` form to keep the box aligned.

## Retained shims (eleven)

`server/firmware_cli.py`, `server/firmware_image.py`, `server/firmware_registry.py`, `server/request_budget.py`, `server/zone_fetch.py`, `server/http_fetch.py`, `server/fleet_zones.py`, `server/fleet_cycle.py`, `server/pairings.py`, `server/pairing_code.py`, `server/pairing_image.py`. All outside importers (companion, stub-server, server modules, tests) still use the old names; retirement is a later owner decision.

## Untouched

systemd units, poll_loop.py, poll_cycle.py, fleet_db, history_db, device_config, STATE.md, ROADMAP.md.

## Self-Check: PASSED
