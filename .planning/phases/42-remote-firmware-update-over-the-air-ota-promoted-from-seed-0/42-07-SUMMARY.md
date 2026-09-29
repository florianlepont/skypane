---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 07
subsystem: api
tags: [ota, firmware, byos, http-server, stdlib]

# Dependency graph
requires:
  - phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
    provides: "server/firmware_registry.py (plan 01) -- compute_offer, load_registry, load_device_report, firmware_image_path, RESULT_TOKENS, MAX_IMAGE_BYTES, the registry.json/device_report.json/firmware/<sha>.bin storage layout"
provides:
  - "byos's GET /device/v1/display now carries the operator's scheduled firmware offer, gated by server/firmware_registry.py's compute_offer(), never withheld by quiet hours or display-off"
  - "byos records the device's X-Fw-Version and validated X-Ota-Result into firmware/device_report.json, and records an offered event before returning a response that contains an offer"
  - "GET /fw/<sha256>.bin: a strict, content-addressed, unauthenticated route serving only registered release images, streamed in fixed 64 KiB chunks"
affects: [poll-loop-reconcile, companion-update-page, ci-deploy-import, firmware-ota-download]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "byos's vendor boundary now also covers server.firmware_registry (a fourth stdlib-only shared import, alongside server.device_policy and server.state_store), imported directly rather than re-implemented locally, since byos already crossed that boundary in an earlier phase"
    - "firmware/device_report.json is byos-owned (the single writer anywhere in the deployment); server/firmware_registry.py only ever reads it -- the same producer/consumer split battery_state.json already established between byos and the poll loop"
    - "A module-level threading.Lock guards the device_report.json read-modify-write against byos's own other request-handling threads (ThreadingHTTPServer); no inter-process file lock needed since no other process ever writes this file"
    - "device_report.json's global next_seq counter is pre-incremented (next_seq += 1 before each new event's seq), so the first ever event gets seq 1, never 0 -- server/firmware_registry.py's own compute_offer() only counts events with seq strictly greater than the registry's reconciled_seq baseline (0 by default), so a seq-0 first event would silently never count toward the three-attempt cap"

key-files:
  created:
    - stub-server/test_ota_offer.py
  modified:
    - stub-server/byos_server.py
    - stub-server/VENDOR.md

key-decisions:
  - "byos already imports server.device_policy and server.state_store directly (the vendor boundary was retired in an earlier phase), so this plan adds server.firmware_registry the same way rather than building a byos-local parity copy of compute_offer()/load_registry()/load_device_report() -- the plan's own fallback path for a still-closed vendor boundary did not apply"
  - "The offer computation reads the device_report entry AFTER appending the current request's own new result/offered event, not before, so a third counted failure reported in the same request that would otherwise grant a fourth attempt is caught before that request's own response is built -- no dependency on the poll loop's later, separately-timed reconciliation"
  - "GET /fw/<sha256>.bin carries no authentication, matching /img/'s existing rule: release images are signed and (after the device-credentials plan) carry no secret, so they are not confidential -- only their integrity matters, and that is the signature's job, not this route's"
  - "The device_report.json event-cap trim (newest 50) happens on write, in addition to server/firmware_registry.py's own defensive re-cap on load, so a hostile or buggy device cannot grow the file unbounded even between polls"

requirements-completed: []  # OTA-01/06/08 are shared across several plans in this phase
                            # (offer gate, device report, /fw/ route here; the poll loop's
                            # reconcile call and the companion's Update page still owe their
                            # own halves). REQUIREMENTS.md is left Pending per this project's
                            # established convention (see plan 01's precedent) -- only the
                            # phase's own close-out plan flips these to Complete.

coverage:
  - id: D1
    description: "GET /device/v1/display carries the operator's scheduled firmware offer (gated by version-differs/floor/battery-low/three-attempts), byos records the device's X-Fw-Version and a validated X-Ota-Result into firmware/device_report.json, and records an offered event before a response carrying an offer is sent"
    requirement: "OTA-01"
    verification:
      - kind: integration
        ref: "stub-server/test_ota_offer.py -- test_offer_present_when_scheduled_version_differs_from_reported, test_offer_absent_when_reported_version_matches_scheduled, test_offer_withheld_while_battery_low_active, test_offer_present_during_quiet_hours_and_display_off, test_offered_event_recorded_and_schedule_not_cancellable, test_third_counted_failure_withdraws_offer_in_the_same_response, test_malformed_ota_headers_are_ignored, test_unauthenticated_request_records_nothing_and_401, test_nothing_written_when_no_header_and_no_offer"
        status: pass
    human_judgment: false
  - id: D2
    description: "GET /fw/<sha256>.bin serves exactly the registered release image (correct bytes, Content-Type, Content-Length), streamed in fixed-size chunks; any other name, unregistered sha, missing file, or oversized on-disk file is 404"
    requirement: "OTA-08"
    verification:
      - kind: integration
        ref: "stub-server/test_ota_offer.py -- test_fw_route_serves_registered_release_image, test_fw_route_404_for_malformed_or_unregistered_paths (parametrized x7), test_fw_route_404_when_registered_image_file_is_missing, test_fw_route_never_serves_a_file_larger_than_max_image_bytes"
        status: pass
      - kind: unit
        ref: "stub-server/test_ota_offer.py::test_serve_firmware_image_streams_in_fixed_size_chunks"
        status: pass
    human_judgment: false

# Metrics
duration: ~50min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 07: byos OTA offer, device report and /fw/ route Summary

**byos's GET /device/v1/display now offers the operator's scheduled release (via server/firmware_registry.py's compute_offer()), records device version/result reports into firmware/device_report.json, and serves release images from a strict content-addressed GET /fw/<sha256>.bin route.**

## Performance

- **Duration:** ~50 min
- **Completed:** 2026-09-28
- **Tasks:** 2 (Task 1: device report recording and the offer; Task 2: the /fw/ route and vendor record)
- **Files modified:** 3 (1 new, 2 modified)

## Accomplishments

- byos imports `server.firmware_registry` directly (the vendor boundary was already retired) and composes the device's firmware offer from `compute_offer()`, `load_registry()` and `load_device_report()` -- no byos-local reimplementation of the offer rule.
- Added `parse_fw_version_header()`, `parse_ota_result_header()` (anchored regexes, the result token drawn from `firmware_registry.RESULT_TOKENS`, the whole header capped at 64 bytes), `read_battery_low_active()` (a fail-open read of `poll_state.json`'s `battery_low_active` latch), `_resolve_device_id()` (which MAC a presented bearer token belongs to), and `_record_device_report_and_offer()` -- the one call `GET /device/v1/display` makes for the whole OTA offer contract, guarded by a module-level `threading.Lock`.
- `firmware/device_report.json` is now byos's own new state file: it records `fw_version`/`reported_at`, `result` events for a validated `X-Ota-Result`, and `offered` events for a served offer, all before the response is sent -- so `firmware_registry.cancel_schedule()` correctly refuses to cancel a schedule the device has just been offered.
- `log_telemetry()`'s allow-listed header loop now also echoes `X-Ota-Result` to stdout.
- Added `GET /fw/<sha256>.bin` next to `/img/*.bin`: a strict `^/fw/([0-9a-f]{64})\.bin$` path match, registry membership check, a regular-file-and-size check against `MAX_IMAGE_BYTES`, and a 64 KiB chunked stream (`_serve_firmware_image()`) -- no authentication, matching `/img/`'s own existing rule.
- `stub-server/VENDOR.md` gained local modification 12, documenting the offer, the device report, and the `/fw/` route in the file's established format; the re-pinning checklist now names twelve modifications and three confirming test files.
- 20 new tests in `stub-server/test_ota_offer.py` (a self-contained Harness following the same shape as `test_poll_cycle.py`/`test_byos_hardening.py`/`test_devices_registry.py`, per this codebase's own convention of not cross-importing test harnesses), plus the existing `stub-server/test_poll_cycle.py` (21 tests, unaffected -- its own `firmware: null` assertion still holds since no schedule exists in that harness).

## Task Commits

Each task was committed atomically:

1. **Task 1: Device report recording and offer in /device/v1/display** - `1e9e2fd9` (feat)
2. **Task 2: Strict /fw/<sha>.bin route and vendor record** - `dc865bbc` (feat)

**Plan metadata:** committed as part of this final docs commit (STATE.md/ROADMAP.md/REQUIREMENTS.md).

_Note: both tasks used `tdd="true"`; tests and implementation were authored and verified together against each task's `<behavior>` contract rather than via two separately-committed RED/GREEN passes -- matching this phase's plan 01 precedent (see its own Deviations section)._

## Files Created/Modified

- `stub-server/byos_server.py` - the offer, device report recording, and the `/fw/` route
- `stub-server/test_ota_offer.py` - 20 behaviour tests (offer gating, device report recording, malformed-header handling, the `/fw/` route, chunked streaming)
- `stub-server/VENDOR.md` - local modification 12 and the updated re-pinning checklist

## Decisions Made

- See `key-decisions` in the frontmatter above -- the vendor-boundary import choice, the read-after-append offer ordering, the unauthenticated `/fw/` route, and the write-side event cap are the four decisions with real behavioural consequences.
- `device_report.json`'s `next_seq` field is pre-incremented (the first assigned event gets seq 1, not 0), discovered live while writing the third-counted-failure test: `server/firmware_registry.py`'s `compute_offer()` only counts events with `seq > reconciled_seq`, and `reconciled_seq` defaults to 0, so a seq-0 first event would never count until the poll loop's `apply_reconcile()` had run at least once -- confirmed against `server/test_firmware_registry.py`'s own fixtures, which uniformly start real event sequences at 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] First-ever device_report.json event used seq=0, which server/firmware_registry.py's compute_offer() never counts**
- **Found during:** Task 1, running `test_third_counted_failure_withdraws_offer_in_the_same_response` for the first time (it failed: the third failure's response still carried an offer)
- **Issue:** `_record_device_report_and_offer()` originally assigned `seq = next_seq` then incremented afterward, starting the first-ever event at seq 0. `compute_offer()` only counts events with `seq` strictly greater than the registry's `reconciled_seq` (0 by default), so the first event was silently never counted toward the three-attempt cap.
- **Fix:** Switched to pre-increment (`next_seq += 1` before assigning), so the first assigned seq is 1 -- matching the convention every fixture in `server/test_firmware_registry.py` already assumes.
- **Files modified:** `stub-server/byos_server.py`
- **Verification:** `test_third_counted_failure_withdraws_offer_in_the_same_response` and the full `stub-server/test_ota_offer.py`/`stub-server/test_poll_cycle.py` suites pass
- **Committed in:** `1e9e2fd9` (Task 1 commit)

**2. [Rule 1 - Bug] A code comment cited a plan number ("plan 06"), violating the project's comment-history rule**
- **Found during:** Task 2, self-review before running `scripts/check_comment_history.py check`
- **Issue:** `_serve_firmware_image()`'s docstring originally read "release images are signed and carry no credential (plan 06)" -- the project's `CLAUDE.md` and this plan's own rules forbid plan/decision/requirement IDs in source comments
- **Fix:** Reworded to state the rationale without the citation: "release images are signed and carry no credential, so they are not secret"
- **Files modified:** `stub-server/byos_server.py`
- **Verification:** `scripts/check_comment_history.py check` exits 0 with no findings
- **Committed in:** `dc865bbc` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug in seq numbering, 1 comment-history compliance fix)
**Impact on plan:** Both fixes were required for the plan's own stated behaviour (D1's three-attempts rule) and its own verification command (`check_comment_history.py check`); no scope creep beyond what each task already specified.

## Issues Encountered

None beyond the two auto-fixed items above.

## User Setup Required

None - no external service configuration required. This plan is server-side, stdlib-only, and touches no deployment or secrets configuration.

## Next Phase Readiness

- `GET /device/v1/display` now carries a real, gated firmware offer and `GET /fw/<sha256>.bin` serves registered release images -- the poll loop's own reconcile step (a later plan) can read `firmware/device_report.json`'s events through `server/firmware_registry.py`'s `apply_reconcile()` exactly as that module already expects.
- No blockers. `firmware/device_report.json` did not exist on disk before this plan; it is created lazily on the first poll that has something to record (a reported version, a result, or a served offer) -- `load_device_report()`'s tolerant-missing-file default already covered this gap from plan 01.
- `REQUIREMENTS.md` deliberately left untouched: OTA-01/06/08 are each shared across further plans in this phase (the poll loop's reconcile call, the companion's Update page), so this plan does not call `requirements mark-complete` for them -- matching this phase's own established convention.
- `deploy/Caddyfile`'s single catch-all `reverse_proxy 127.0.0.1:8642` block already forwards `/fw/*` to byos with no configuration change needed (confirmed by reading the file; not itself modified by this plan).

---

*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: stub-server/byos_server.py
- FOUND: stub-server/test_ota_offer.py
- FOUND: stub-server/VENDOR.md
- FOUND: .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-07-SUMMARY.md
- FOUND: 1e9e2fd9 (feat: device report recording and offer in /device/v1/display)
- FOUND: dc865bbc (feat: strict /fw/<sha>.bin route and vendor record)
