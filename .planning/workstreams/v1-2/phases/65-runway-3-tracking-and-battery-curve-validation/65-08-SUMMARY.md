---
phase: 65-runway-3-tracking-and-battery-curve-validation
plan: 08
subsystem: tracking-validation
tags: [trk-02, scratch-fleet, tooling, replay-recording, export]
requires: ["65-07"]
provides:
  - "scripts/multi_site_setup.py: scratch fleet with a production-path guard"
  - "scripts/multi_site_run.py: timed fleet-cycle driver that records raw zone payloads"
  - "scripts/multi_site_export.py: per-device export in the production line format"
affects: [65-09, 65-10, 65-11, 65-12]
key-files:
  created:
    - scripts/multi_site_setup.py
    - scripts/test_multi_site_setup.py
    - scripts/multi_site_run.py
    - scripts/multi_site_export.py
    - scripts/test_multi_site_run_export.py
decisions:
  - "Scratch roots carry a .multisite-scratch marker; setup, run and export refuse the server default state directory and any root that looks real"
  - "The simulation flag is passed as an argument at setup and set only in the runner's process environment, restored on exit"
  - "The exporter reuses companion.export_api's route table and line renderer, so output is the companion's own rendering"
requirements: [TRK-02]
status: complete
completed: 2026-11-15
---

# Phase 65 Plan 08: Multi-site scratch tooling Summary

Three stdlib-plus-repository scripts let TRK-02 sessions run on simulated devices in an isolated scratch root and feed the TRK-01 comparison tools unchanged, with no change to server, stub-server, companion, deploy or firmware.

## What was built

- **multi_site_setup.py**: `--root`, repeated `--device NAME=ICAO:DESIGNATOR`. Writes the marker first, creates fleet.db, a scratch owner (example.invalid address), a held live row (display off in the root's own config, so it joins no zone), and one `sim-ee02-clone` device per entry with documentation-range MACs and random secret hashes. Orly runways 3-equivalent ids (06/24, 02/20) store the legacy `tracked_runway`; other runways store a detection object; the selection reads back through `detection.current_selection`. Refuses the default state dir, roots with live_frame_macs.json, panel.bin, fleet.db or other content and no marker, unknown airports or runways, an empty owner, and non-simulated or unknown hardware; validation happens before any write.
- **multi_site_run.py**: `--root`, `--cycles` and/or `--until`, `--interval` (floor 30 s, enforced in code), `--stop-file`. Each cycle is `fleet_cycle.run_fleet` with the unchanged ledger and provider list; a recording fetcher appends one JSON line per zone fetch to `payloads/<zone>.jsonl` (ts, zone key, centre and radius, per-provider aircraft, queried, failed) and returns the inner result untouched. One count-only summary line per cycle. Exits 2 for a refused root or bad arguments.
- **multi_site_export.py**: `--root`, `--device` (id or `all`), `--since`, `--out`. Writes `<out>/<id>/runway_events.jsonl`, `poll_cycles.jsonl` and `MANIFEST.json` (rows and sha256) through the companion's route table and `_render_lines`; opens history.db read-only (missing database is an error, nothing created); device directory only from `device_dirs.resolve_state_dir`; never overwrites.

## Tests (no network)

- scripts/test_multi_site_setup.py: 6 tests (creation and selections, guards, owner and hardware refusals, held live row and zone grouping, nothing written outside the root, flag not left in the environment).
- scripts/test_multi_site_run_export.py: 13 tests (payload recording per zone, interval floor and fake-clock spacing, wrapper returns the inner result, marker and default-root refusal, flag set and restored even on runner failure, stop file, `--until`, byte equality with the companion rendering on a history.db written by a real `run_once`, read-only missing database, no overwrite, `all`, `runway_compare.analyse` reads the output).
- RED runs recorded: both test files failed at collection (module missing) and were committed before the code (8317de6e, e1dec836).
- Full scripts suite plus stub-server/test_phase47_freeze.py: 68 passed. ruff, comment-history guard and `ci_shards.py check` clean.

## Commits

- 8317de6e test(65-08): failing tests for the scratch fleet setup script
- d5d03f6f feat(65-08): scratch fleet setup script with a production-path guard
- e1dec836 test(65-08): failing tests for the recording runner and per-device exporter
- e4bbd424 feat(65-08): recording fleet runner and per-device exporter

## Deviations from Plan

None - plan executed as written. No real network call was needed, so the adsb.fi allowance was not used. One test assertion was adjusted during GREEN (a loaded device config carries `detection: None` rather than omitting the key; and the stop-file test asserts no sleeping instead of a call count, since the held live row also runs).

## Known Stubs

None.

## Self-Check: PASSED

All five files exist, the four commits are in the log, and git status shows no change under server, stub-server, companion, deploy or firmware.
