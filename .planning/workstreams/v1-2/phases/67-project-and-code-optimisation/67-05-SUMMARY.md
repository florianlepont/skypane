---
phase: 67-project-and-code-optimisation
plan: 05
subsystem: docs
tags: [architecture, documentation, claude-md]
requires: [67-02]
provides:
  - "ARCHITECTURE.md corrected claim by claim against the code"
  - ".planning/codebase/ARCHITECTURE.md bullet summary feeding the CLAUDE.md block"
affects: [67-13, 67-14, 67-15]
key-files:
  modified: [ARCHITECTURE.md, .claude/CLAUDE.md]
  created: [.planning/codebase/ARCHITECTURE.md]
decisions:
  - "The Persistent state section merged by plan 02 is kept unchanged; the unify, retire and remove steps of D-12 will rewrite its Migrations and Duplicated data subsections in their own plans."
requirements-completed: [QUAL-01]
completed: 2026-11-27
---

# Phase 67 Plan 05: Architecture document Summary

ARCHITECTURE.md now describes the shipped system (fleet cycle, giant-lettering and landscape renderers, Auth0 and roles, hardware profiles, pairing, OTA, manual gated deploy with atomic swap and rollback, six units), and the CLAUDE.md architecture block points to it.

## Commits

- 1832f2cb: rewrite ARCHITECTURE.md
- a8d380ed: .planning/codebase/ARCHITECTURE.md and the CLAUDE.md managed block

## Verification table (corrected claim, checked against)

| Claim in the old document | Reality | Checked against |
|---|---|---|
| Diagram wrote `state/panel.bin` only | per-device directory, live frame uses the root | `server/device_dirs.py`, `server/fleet_cycle.py` |
| "two-flight poster" is the render | classic poster, giant layouts a/b/c/a_diagonal (default b), landscape card | `server/screen_layouts.py`, `server/plane/render/layout.py`, `giant/__init__.py`, `landscape.py` |
| Module map `style/text/glyphs/hold_screens/layout/cli` | plus `giant/`, `landscape*`, fleet, hardware, firmware, pairing, wake, budget modules | directory listing of `server/`, `server/plane/render/` |
| Companion writes `history.db` and `device_config.json`, never touches byos | companion owns `fleet.db` writes, sessions, Auth0, pairing, registries | `server/fleet_sessions.py`, `companion/oidc.py`, `companion/routes.py`, `companion/user_pairing.py` |
| "there is no separate database" | removed; state map is the Persistent state section | `server/fleet_db.py`, `server/history_db.py` |
| `deploy.sh` rsyncs, two units, no rollback | `git archive` over ssh, `activate.sh` atomic swap, restart, probe, rollback, six units, prune to five | `deploy/deploy.sh`, `deploy/activate.sh`, `deploy/*.service`, `deploy/*.timer` |
| Deploy implied automatic | manual `workflow_dispatch`, `production` environment, tip-of-main confirmation and green CI required | deploy workflow header and first steps |
| Device registry is `devices.json` | `fleet.db` is the source, `devices.json` a legacy mirror | `stub-server/byos_server.py` (`effective_registry`) |
| Auth0, roles, hardware, OTA, pairing, wake interval, budget absent | new "Fleet platform" section | `companion/access.py`, `server/hardware.py`, `server/firmware_registry.py`, `server/fleet_ops.py`, `server/request_budget.py`, `stub-server/byos_server.py` |
| `select_runway3_aircraft()` | `select_aircraft_for_runway()` | `server/plane/detect.py` |
| Corroboration needs agreement of "every answering source" | only sources that saw traffic are intersected | `select_from_provider_results()` |
| "Single view in v1", RER deferred to v2 | RER view and buttons dropped 2026-10-28 | `.planning/workstreams/v1-2/REQUIREMENTS.md` Out of Scope |
| "No freshness indicator" | still no render-age stamp, but an "ADS-B source unavailable" badge exists and the companion reports quiet frames; `freshness.js` only auto-refreshes the companion page | `server/plane/render/style.py`, `layout.py`, `server/wake.py`, `companion/static/freshness.js` |
| Firmware: setup secret from gitignored `secrets.h` | enrolment secret, Wi-Fi and base URL come from the `secret` NVS partition | `firmware/main/enrol_secret.c`, `nvs_schema.h` |
| Firmware: five NVS keys | seven keys on the default partition (adds OTA try, OTA result, `imgfmt_bad`), eight on `secret` | `firmware/main/nvs_schema.h` |
| Firmware: wake flow without OTA or container | OTA branch before the hash check, image container parse, reset and deadline checks | `firmware/main/state_machine.c`, `app_main.c`, `firmware/VENDOR.md` |
| Log Line Contract failure tokens: seven | fifteen; `blit ok bytes` is hardware dependent | `firmware/VENDOR.md`, `state_machine.c` |
| NO CONNECTION allow-list includes `auth`, `enrol` | allow-list is `wifi http status json secret config download verify`, after the 2nd failure | `firmware/main/fault_screen.c`, `fault_screen.h` |

Kept as verified: 30 s timer, request ledger with `flock`, `poll.lock`, BYOS routes, loopback-only BYOS, backoff formula `min(300*2^n, 21600)`, deferred draw semantics, 960,000-byte image on the 13.3" panel, 90 s advance interval and 150 s staleness bound, hold-screen priority.

## Checks

- Path-resolution script of Task 1: exit 0 (no unresolved repo path, none of the three stale claims). Extra checks run: every backticked directory exists, every backticked bare file name exists, every `name()` identifier and `FP_`/`MIN_`/`MAX_`/`DEFAULT_` constant appears in the tracked sources.
- `scripts/check_comment_history.py check`: passes.
- `deploy/tests/test_docs.py`: 23 passed.
- Exposure scan of the diff (addresses, e-mails, host names, owner name): only the loopback address already documented.

## Drift items not verified

- Firmware hardware behaviour was checked against the C sources and `VENDOR.md` only; nothing was run on a device or in the firmware host tests. The 31.5 s refresh figure is from `hardware/BRINGUP-LOG.md` for the 13.3" panel; no figure was checked for the 7.3" panel.
- The detection, enrichment, display-pacing and hold-screen prose (retained, about 300 lines) was spot-checked by function and constant names and by `select_from_provider_results()`, not re-derived line by line.
- Companion statements on throttles and audit rows rely on module docstrings, not a read of every handler.
- The retained Persistent state section still says migrations are "documented, not unified" and that duplicates are kept. D-12 overrides that; plans 17 to 23 must update it as they unify, retire and remove. The module map will also need a refresh after the module moves of plans 13 to 15.

## Deviations from Plan

None. The plan's Task 1 verification script was run unchanged; three runtime artefact paths and one relative path were rewritten so they no longer look like repository paths.

## Self-Check: PASSED
