---
phase: 01-foundation-hardware-bring-up-ads-b-validation
plan: 02
subsystem: infra
tags: [stub-server, device-protocol, sha256, python-stdlib, tdd, byos, flightportrait]

# Dependency graph
requires:
  - phase: 01-foundation-hardware-bring-up-ads-b-validation (plan 01)
    provides: hardware/BOM.md (orders placed, no code dependency)
provides:
  - "Local BYOS stub server (stub-server/byos_server.py) answering all three device protocol endpoints plus /img/<sha>.bin"
  - "Deterministic Spectra 6 panel .bin generator (stub-server/make_test_panel.py) with palette and quadrants patterns"
  - "Host-side end-to-end poll-cycle contract harness (stub-server/test_poll_cycle.py), 15/15 checks passing"
  - "Vendored-source provenance record (stub-server/VENDOR.md)"
  - "Run/targeting documentation (stub-server/README.md)"
affects: [01-05-full-ee02-firmware, 01-06-first-light, 01-07-repeatability-and-backoff, 01-08-battery-time-to-depletion]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vendor-at-pinned-commit with a VENDOR.md delta log (flightportrait/frame @ ce3335fc5e566bcc6ccd29966ec39bf5c5318f12)"
    - "Stdlib-only Python for all Phase 1 server/test tooling - zero pip installs"
    - "Harness owns its own fixture lifecycle: bind-port-0 for the listen port, subprocess launch/terminate in a finally block, isolated --state-dir per run"

key-files:
  created:
    - stub-server/test_poll_cycle.py
    - stub-server/byos_server.py
    - stub-server/make_test_panel.py
    - stub-server/VENDOR.md
    - stub-server/README.md
    - stub-server/.gitignore
  modified: []

key-decisions:
  - "Vendored byos_server.py byte-for-byte from the pinned commit, then made exactly one local change (--state-dir) rather than reimplementing any endpoint"
  - "Panel image halves in the quadrants pattern split exactly on a byte-pair boundary (column 600 of 1200), so no byte mixes the black border with a fill colour except the two edge bytes per interior row"
  - "Hash-skip and image-change checks are demonstrated by the harness's own control flow (it does not re-download when the hash is unchanged, and does download when it is) rather than by a separate assertion helper"

requirements-completed: [DEVICE-03]

coverage:
  - id: D1
    description: "Local stub server answers all three device protocol endpoints and serves a valid 960,000-byte panel image"
    requirement: "DEVICE-03"
    verification:
      - kind: integration
        ref: "stub-server/test_poll_cycle.py::main (checks 1,2,3,4,5,6,11,12)"
        status: pass
    human_judgment: false
  - id: D2
    description: "One command completes the full simulated poll cycle end to end - setup, authenticated poll, download, SHA-256 verify, exact size check, hash-skip on the second poll - and exits non-zero on any contract break"
    requirement: "DEVICE-03"
    verification:
      - kind: integration
        ref: "stub-server/test_poll_cycle.py (poll-cycle: 15/15 checks pass, exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "A deliberately corrupted image download is rejected by verify_panel_bytes, and a truncated one too - the integrity gate is exercised, not decorative"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py::main (checks 7,8 - flipped byte and one-byte truncation)"
        status: pass
    human_judgment: false
  - id: D4
    description: "An unauthenticated display poll is refused with 401, proving the bearer-token gate is enforced"
    requirement: "DEVICE-03"
    verification:
      - kind: integration
        ref: "stub-server/test_poll_cycle.py::main (checks 3,4 - missing header and unissued bearer)"
        status: pass
    human_judgment: false
  - id: D5
    description: "The test panel image is generated deterministically at run time, not committed as a binary blob, and every nibble is a legal Spectra 6 colour code"
    requirement: "DEVICE-03"
    verification:
      - kind: unit
        ref: "python3 stub-server/make_test_panel.py --pattern palette --out /tmp/ink_panel.bin (960000 bytes, all nibbles in {0,1,2,3,5,6}); shasum -a 256 identical across two runs; quadrants digest differs from palette digest"
        status: pass
    human_judgment: false

# Metrics
duration: ~15min
completed: 2026-08-04
status: complete
---

# Phase 1 Plan 2: Local Stub Server + Protocol Contract Harness Summary

**A stdlib-only local BYOS stub server vendored from flightportrait/frame, a deterministic Spectra 6 panel-image generator, and a 15-check end-to-end poll-cycle harness that proves the device protocol contract with zero hardware.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-08-04T15:26:00Z (approx.)
- **Completed:** 2026-08-04T15:38:28Z
- **Tasks:** 3
- **Files modified:** 6 created (0 modified)

## Accomplishments
- Wrote a 15-check host-side contract harness (`stub-server/test_poll_cycle.py`) *before* the server it tests existed, confirmed it fails RED naming the missing files, then vendored the server and confirmed it goes GREEN (15/15, exit 0) — a genuine TDD red/green cycle at the plan level, not just per-function.
- Vendored `examples/byos_server.py` from `flightportrait/frame` at pinned commit `ce3335fc5e566bcc6ccd29966ec39bf5c5318f12` (Apache-2.0) byte-for-byte, adding exactly one local change (`--state-dir`) so the harness's issued tokens never collide with the long-running instance the hardware plans (01-05, 01-06, 01-07) will keep alive.
- Wrote an original, deterministic panel-image generator (`make_test_panel.py`) producing the exact PROTOCOL.md §1 byte format — 960,000 bytes, LEFT-pixel-in-HIGH-nibble packing, only the six legal Spectra 6 nibble codes — with a `palette` pattern (six stripes, for instant visual verification of nibble order and chip-select split) and a `quadrants` pattern (four bordered quadrants, for the hash-change check).
- Proved the integrity and auth gates actually reject bad input (flipped byte, truncated buffer, missing/forged bearer token) rather than merely accepting good input.
- Documented run commands, LAN targeting (`firmware/main/secrets.example.h`), the plain-HTTP transport decision and its Phase-1-only boundary, and the telemetry stdout stream plan 01-07 depends on, in `stub-server/README.md`.

## Task Commits

Each task was committed atomically:

1. **Task 1: End-to-end poll-cycle contract harness, written failing first** - `0e14905` (test) — RED confirmed: exits 1, `poll-cycle: 0/15 checks pass`, naming the missing `make_test_panel.py`.
2. **Task 2: Vendor the stub server and generate a valid panel image so the harness goes green** - `0806311` (feat) — GREEN confirmed: exits 0, `poll-cycle: 15/15 checks pass`.
3. **Task 3: Document the run commands, including the LAN address the firmware will target** - `7bbbb09` (docs).

_Note: this plan's `type="tdd"` frontmatter and Task 1's `tdd="true"` behavior/action blocks describe the plan-level TDD gate documented below; see "TDD Gate Compliance."_

## Files Created/Modified
- `stub-server/test_poll_cycle.py` - Stdlib-only harness; `verify_panel_bytes`, `validate_display_response`, `main` plus 15 named checks covering setup, auth, display shape, download, integrity/size gates, hash-skip, image change, telemetry, log endpoint, two negative validator cases, and failure classification against a stopped server
- `stub-server/byos_server.py` - Vendored BYOS stub server (Apache-2.0, pinned commit), plus a `--state-dir` flag
- `stub-server/make_test_panel.py` - Original deterministic panel generator (`--pattern palette|quadrants`, `--out`)
- `stub-server/VENDOR.md` - Upstream provenance, pinned commit, licence, exact local modification list
- `stub-server/README.md` - Run instructions, LAN targeting, transport decision, telemetry capture
- `stub-server/.gitignore` - Excludes `byos_state.json`, generated `.bin` files, `__pycache__/`

## Decisions Made
- Vendored `byos_server.py` byte-for-byte first, then applied exactly one local change (`--state-dir`), rather than reimplementing any endpoint — keeps a future re-pin a diff, not an archaeology project (per the Walking Skeleton's provenance-discipline decision).
- Chose quadrant-boundary columns (600 of 1200) so the left/right split in `make_test_panel.py`'s `quadrants` pattern lands exactly on a byte-pair boundary — avoids any byte mixing two colours except the two intentional border-edge bytes per interior row, keeping the packing logic simple and auditable.
- Implemented hash-skip and image-change checks by having the harness's own control flow skip or perform the download (rather than a separate "did it skip" assertion helper) — the behavior bullet says "the simulated client skips the download," and the harness genuinely does or doesn't call the download step based on the hash comparison.

## Deviations from Plan

None - plan executed exactly as written. All three tasks, their read_first inputs (fetched live from `flightportrait/frame` at the pinned commit — `docs/PROTOCOL.md` sections 1, 2, 3, 5; `examples/byos_server.py`; `LICENSE`), and every acceptance criterion were followed as specified.

## TDD Gate Compliance

Task 1 (`tdd="true"`) followed the RED → GREEN cycle at the plan level:
- **RED gate:** `test(01-02): write failing end-to-end poll-cycle contract harness` (`0e14905`) — verified failing before commit (`poll-cycle: 0/15 checks pass`, exit 1, naming the missing `make_test_panel.py`).
- **GREEN gate:** `feat(01-02): vendor byos_server.py and generate a valid panel image so the harness goes green` (`0806311`) — verified passing after commit (`poll-cycle: 15/15 checks pass`, exit 0).
- No REFACTOR commit was needed; the vendored server required no changes beyond the `--state-dir` addition made in the GREEN commit itself.

Both gate commits are present in git log in the correct order. No warning needed.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required. The stub server and harness are fully local and require no accounts, API keys, or manual dashboard steps.

## Next Phase Readiness

- `stub-server/` is a complete, self-contained local dev tool: `python3 stub-server/byos_server.py --image <bin> --port 8642 --sleep <n> --state-dir <dir>` serves the protocol, and `python3 stub-server/test_poll_cycle.py` proves the contract end to end with zero hardware.
- Plan 01-05 (full EE02 firmware) can point its firmware build directly at this server via `firmware/main/secrets.example.h`'s base URL, per `stub-server/README.md`'s "Point the device at it" section.
- Plans 01-06 (first light) and 01-07 (repeatability + battery) can reuse the `--sleep 300` invocation documented in the README, and consume the telemetry stdout stream (`X-Battery-Mv`, `X-Rssi`, `X-Fw-Version`, `X-Boot-Reason`) that `byos_server.py`'s `log_telemetry()` already prints on every poll — unmodified from upstream.
- No blockers. The stub server's `--state-dir` isolation means the harness can be re-run at any time (e.g. as a regression check after a future re-pin) without disturbing a long-running server instance kept up for hardware testing.

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 6 created files verified present on disk; all 3 task commits (`0e14905`, `0806311`, `7bbbb09`) verified present in git log.
