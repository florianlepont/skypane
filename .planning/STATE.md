---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 01
current_phase_name: foundation-hardware-bring-up-ads-b-validation
status: executing
stopped_at: Completed 01-01-PLAN.md
last_updated: "2026-08-05T06:24:13.644Z"
last_activity: 2026-08-04
last_activity_desc: Phase 01 execution started
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 8
  completed_plans: 4
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-04)

**Core value:** Glancing at the frame tells you, in real time, whether you'll make the next RER — while also being a satisfying ambient piece on the wall.
**Current focus:** Phase 01 — foundation-hardware-bring-up-ads-b-validation

## Current Position

Phase: 01 (foundation-hardware-bring-up-ads-b-validation) — EXECUTING
Plan: 5 of 8
Status: Ready to execute
Last activity: 2026-08-04 — Phase 01 execution started

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**

- Total plans completed: 0
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
| Phase 01 P02 | 15min | 3 tasks | 6 files |
| Phase 01 P03 | 25min | 3 tasks | 15 files |
| Phase 01 P05 | 50min | 3 tasks | 22 files |
| Phase 01 P01 | 12min | 2 tasks | 1 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Local ADS-B receiver (geofenced to runway 3) chosen over public flight-data/schedule APIs — validate reception early in Phase 1
- Battery-only power for v1, solar deferred — Phase 1 must produce a real mAh/wake-cycle measurement
- Server on a small always-on cloud VPS, not a home server
- No freshness timestamp / stale-data indicator in v1 (explicit user tradeoff, despite research flagging it as a pitfall)
- [Phase 01]: Vendored byos_server.py byte-for-byte from flightportrait/frame @ ce3335fc, adding only a --state-dir flag so the harness's isolated test tokens never collide with the long-running stub instance the hardware plans keep alive
- [Phase 01]: make_test_panel.py's quadrants pattern splits left/right exactly on a byte-pair boundary (column 600 of 1200) so no byte mixes two colours except the two intentional border-edge bytes
- [Phase 01]: Disabled Bluetooth in firmware/sdkconfig.defaults (only functional delta from upstream) - Phase 1 has no BLE provisioning, hardcoded secrets.h credentials replace it
- [Phase 01]: Containerised build (espressif/idf:v5.3.1), native flash - build.sh runs the whole ESP-IDF toolchain in Docker as the invoking user; USB flashing stays on the host for plan 01-06 because Docker Desktop's macOS USB passthrough is unreliable
- [Phase 01]: Vendored+trimmed api_client.c/wifi.c to the three device endpoints and STA join, reading credentials from a gitignored secrets.h
- [Phase 01]: Trimmed nvs_schema.h from ~30 upstream keys to exactly 4: bearer token, image hash, failure counter, boot counter
- [Phase 01]: Added FP_ERR_HTTP_TRANSPORT/STATUS/JSON/FP_ERR_IMAGE_VERIFY sentinels so state_machine.c can emit the exact Log Line Contract step token
- [Phase 01]: Froze the five-line Log Line Contract in firmware/VENDOR.md for plans 01-06/01-07/01-08 to grep
- [Phase 01]: Hardware orders placed — Seeed EE02 kit (order <seeed-order-ref>) and Kubii battery+cable (order <kubii-order-ref>); Unblock Date 2026-08-26 gates only 01-06/01-07, not 01-05 (already complete)

### Pending Todos

None yet.

### Blockers/Concerns

- Research flagged as unverified before commit: exact AeroDataBox tier/cost is not needed (project uses local ADS-B, not AeroDataBox, per PROJECT.md's reversed decision) — but PRIM/IDFM's exact SIRI Lite quota figures are community-sourced only; verify against the live account dashboard before finalizing RER poll cadence in Phase 3.
- Spectra 6 dual-chip display driver has no confirmed off-the-shelf ESP-IDF library (flightportrait uses a custom driver) — budget driver research/porting time in Phase 1.
- No publicly confirmed enclosure design exists for the EE02 kit — budget design time in Phase 1 or plan around an off-the-shelf enclosure.
- Battery-life real-world figure for this exact hardware combo is unmeasured — must be bench-measured in Phase 1, not assumed from datasheet/precedent.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none — first milestone)* | | | |

## Session Continuity

Last session: 2026-08-05T06:24:13.640Z
Stopped at: Completed 01-01-PLAN.md
Resume file: None
