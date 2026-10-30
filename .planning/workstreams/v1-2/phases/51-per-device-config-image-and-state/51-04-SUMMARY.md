---
phase: 51-per-device-config-image-and-state
plan: 04
subsystem: byos
tags: [byos, fleet, per-device-image, device-context]
requires: [51-01, 51-02]
provides:
  - _authenticate_device, DeviceContext, _device_context, read_timezone in stub-server/byos_server.py
  - Handler._handle_display, per-device /img/<device_id>/<sha>.bin route
  - stub-server/test_device_fleet.py
key-files:
  modified: [stub-server/byos_server.py]
  created: [stub-server/test_device_fleet.py]
metrics:
  completed: 2026-10-30
---

# Phase 51 Plan 04: BYOS per-device serving Summary

The BYOS now binds each display poll to one device (token to MAC to fleet.db row to validated directory) and reads and writes only that directory; the live frame runs the same path with root state, `--image` and the frozen `/img/<sha>.bin` URL.

## Commits

- f13da8d: both tasks. The per-device /img route and health rows were written in the same pass as the context code, so one commit covers Task 1 and Task 2.

## Verification

- `pytest stub-server`: 294 passed, 1 skipped (root ignores dir permission bits). 28 new tests in test_device_fleet.py.
- `test_phase47_freeze.py`, `test_image_negotiation.py`, `measured_fields_freeze.json` unmodified and green; hardware/ and firmware/ untouched.
- ruff clean; check_comment_history clean; check_function_size: 629 functions, none over 80.
- mypy: one error, `server/panel_format.py:14` missing PIL stub (pre-existing, same as noted in 51-03, not touched here).
- No Pillow or requests import in the BYOS (history_db is stdlib only).

## Single-device assumption audit (other Handler branches)

- `/device/v1/setup` (POST): enrols into the registry and token store only; serves no image or per-device state.
- `/device/v1/log` (POST): `bearer_ok()` unchanged, prints log lines only.
- `/fw/<sha>.bin`: root firmware registry, shared by design, no panel or state data.
- `/img/<sha>.bin`: reads only `<root>/img/`; non-live devices never publish there (they publish to their own `img/`), so it cannot hand them out.
- `/img/<id>/<sha>.bin`: id regex on the raw path, fleet.db row lookup, `state_path` must be a `devices/` path (never "."), resolved via `device_dirs.resolve_state_dir`, only that directory's `img/` read.

## Checks recorded

- Caddyfile: single catch-all `reverse_proxy 127.0.0.1:8642`, no path matcher, so `/img/<id>/...` is proxied.
- image_url buffer: `fp_display_t.image_url` is `char[768]`; `fp_url_valid` checks only length < cap, scheme and non-empty host. A URL is about 8 + host + 16 + 64 + 4 (roughly 110 chars), well within the buffer. No firmware change needed.

## Deviations from Plan

**1. Root OTA files are exempt from the "root unchanged" assertion.** `_record_device_report_and_offer` deliberately keeps the root OTA registry and device report, so a non-live poll rewrites root `firmware/device_report.json` and creates `firmware/registry.lock`; the test excludes those plus fleet.db status files and the harness log.
**2. Malformed /img paths.** Paths not matching either route regex fall through to the existing generic 404 ("unknown endpoint"), as with the pre-existing route; shape-matching but unknown ids/hashes give "unknown image". Test accepts both for malformed shapes.
**3. rssi** is stored as the integer parsed from X-Rssi (the Caddy tailer stores the raw string; SQLite column affinity makes both readable).
**4. "MAC without a row is 401"** is unit-tested on `_device_context` (a token for a MAC without a row cannot exist in the fleet.db token view, so it cannot be reached over HTTP).
**5. One commit** for both tasks instead of one each.

## Known limitation (out of scope)

The Caddy access-log tailer (`server/history_db.py`) still writes battery readings only to the root history.db and cannot attribute them to a device; per-device health comes from the BYOS write added here.

## Known Stubs

None.

## Self-Check: PASSED
