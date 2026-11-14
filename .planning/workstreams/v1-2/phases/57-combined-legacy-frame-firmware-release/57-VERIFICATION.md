---
phase: 57-combined-legacy-frame-firmware-release
verified: 2026-11-14
status: human_needed
score: 0/3 roadmap criteria fully verified; code-side parts of 1 and 2 verified, 3 not verified on a device
re_verification: false
gaps:
  - severity: warning
    item: "ESP-IDF-only glue (state_machine.c download/parse/draw/latch ordering, api_client.c capability_headers, NVS flag read/write) has no host test; the first compile was CI, the first execution is the bench"
  - severity: warning
    item: "imgfmt_bad sticky flag is never cleared by any code path (set in state_machine.c, read in api_client.c/state_machine.c only). Matches D-08 literally, but a one-off bad container permanently stops container announcements until reflash/NVS erase"
  - severity: info
    item: "Whether an EE02-profile image runs its OTA mechanics on the EE04 unit is unverified (stated in 57-BENCH-CHECKLIST.md)"
  - severity: info
    item: "CRC-32 over about 960 KB on the ESP32-S3 (crc_ms) and total wake time with the container are unmeasured (B3, B8)"
  - severity: info
    item: "Local pytest was not installed in the verification sandbox; the server tests were not re-run here and rely on the CI result on PR #391"
human_verification:
  - "B1 SIGNING.md bench on a non-live unit"
  - "B2 unconfirmed-trial rollback (nvs and slow_wake fault builds)"
  - "B3 container wake (crc_ms, correct picture, hash-skip on next wake)"
  - "B4 legacy fallback"
  - "B5 hardware claim match and contradiction"
  - "B6 401 loop (5/10/20 min spacing, no NO CONNECTION)"
  - "B7 sticky fallback"
  - "B8 size and wake time"
  - "B9 owner sign-off, then 57-RELEASE-INSTRUCTIONS.md"
---

# Phase 57: Combined Legacy-Frame Firmware Release - Verification

**Goal:** The live frame receives, in one OTA, every firmware change the fleet needs.
**Requirement:** OTA-04 (stays Pending).
**Verified against:** origin/main 807007a0 (PR #391), branch firmware/phase-57-verification.
**Status: human_needed.** The code, tests and documents are in place and CI is green. The phase goal (a published release that reaches the live frame) is deliberately not reached: publication is gated by the owner on the EE04 bench (D-01) and Phase 47.

## Roadmap criteria

| # | Criterion | Result | Evidence |
|---|-----------|--------|----------|
| 1 | One release bundles the image-header reader, hardware header and 401 recovery; published only after Phase 47 allows it and the signing bench passed on a non-live unit | Partly verified (bundle in code); publication gate NOT satisfied, by design | Bundled in one tree: `imgc_parse` called in `state_machine.c` (parse before `fp_panel_draw`); `X-Img-Fmt` and `X-Hw-Type` set on the display request only (`api_client.c` `capability_headers`); auth/enrol removed from the fault-screen allow-list (`fault_screen.c`), backoff 300 s doubling to a 6 h cap (`backoff.c`). Latest tag is still fw-v1.0.4, no `fw-v*` tag contains HEAD. The SIGNING.md bench has not run (B1), so the "published only after" part cannot be verified yet; `57-RELEASE-INSTRUCTIONS.md` preconditions are unticked. |
| 2 | After the OTA the frame still wakes on its cadence, shows a correct image, and is served the container only after announcing support | Server side verified; device side NOT verified | Server: `claim_contradicts(None, ...)` is False, so a header-less frame gets the unchanged path; `announced` is `None` unless `X-Img-Fmt` is sent (`byos_server.py` lines near 1493 and 1722). `test_hw_claim.py` has a header-less case, a match case, an announce-only case and malformed/contradiction cases. Device: cadence, correct image and the first container wake are bench items B3, B4, B8. Not run. |
| 3 | A frame that fails the update stays on the previous working firmware | NOT verified | The existing OTA policy classification (`test_ota_policy.c`) is green, but the new risk (an image that boots yet cannot reach the server, rolling back across deep sleep) was never seen on a device. Bench B2. |

## Specific checks requested

- **(a) Draw argument fix.** `state_machine.c` calls `fp_panel_draw(view.payload)` after `imgc_parse(buf, body_len, FP_PANEL_W, FP_PANEL_H, &view)`. In `image_container.c`, a container body yields `payload = body + header_len` and a legacy body (length exactly 960000, no `SPIM` magic) yields `payload = body`, so both are correct. The header is bounded (`header_len <= len`), payload length and CRC are checked before the pointer is exposed, and `buf` is freed after the draw on the success path and before returning on every failure path. The CI first-compile catch (9ab5428c) is consistent with this. Verified by reading; the draw itself runs only on a device.
- **(b) Header-less frame served as before.** Verified in code and test (`test_no_headers_gets_raw_image_and_offer`). No claim means no contradiction, a raw image, and the normal firmware offer.
- **(c) D-04/D-09.** `test_fault_screen.c` (lines 176-177) asserts that `auth` and `enrol` never draw for the tested backoff counts; `fault_screen.c` allow-list no longer contains them. The token erase and re-enrol path was not modified. **D-06.** A contradicting claim withdraws the container and the firmware offer only; the raw image is still served, the reported version is still recorded, the claim is never stored (tests listed in `test_hw_claim.py`, including fleet and pending frames). **D-08.** On a fully received but rejected body after announcing (`fp_imgfmt_latch_bad`) or on `imgc_parse` failure, `imgfmt_bad` is set, the hash is not written, the step is `verify` and the frame backs off; later wakes omit `X-Img-Fmt`. Predicate tests are in `test_validate.c`. The latch never fires for partial, timeout or zero-byte bodies. Behaviour on glass is B6/B7.
- **(d) No secrets, tags or releases.** `git tag --list 'fw-v*'` ends at fw-v1.0.4; no tag contains HEAD. The phase's diff (`ec1860b2..807007a0`) touches no `panel.c`, `epd13in3e.c`, `wake_telemetry.*`, `wake_record.*`, phase-47 freeze files or `hardware/`. The only workflow change is a 13-line addition to `firmware.yml`. No publish, schedule, flash or production import is in the diff.
- **(e) Gaps.** See the frontmatter list and below.

## Automated results

| Check | Result |
|-------|--------|
| `./firmware/tests/run_host_tests.sh` (run here) | 15 suites passed, including check_panel_diff |
| CI `firmware.yml` on main for 807007a0 (including the ESP-IDF build) | success (2m1s) |
| Server pytest files (`test_hw_claim.py` etc.) | Not run here (pytest missing in the sandbox); CI on PR #391 reported green |

## Human-needed items

All of B1 to B9 in `57-BENCH-CHECKLIST.md` are unticked and have empty Result fields; none was ticked by an agent. B1 (signing bench) and B9 (owner sign-off) gate publication; B2 and B6 to B8 cover the device-side parts of criteria 2 and 3. The owner must also decide the Phase 47.1 window restart (D-07) and read the live frame's installed version with `firmware_cli list`.

## Gaps and severity

1. **Warning:** ESP-IDF-only glue has no host test (the swapped `fp_panel_draw` argument already slipped through host tests once). Bench B3/B4/B7 is the only coverage.
2. **Warning:** the sticky flag has no clearing path. A transient corrupt container (for example a server bug) permanently sends the frame back to the raw format until reflash or NVS erase. Acceptable per D-08 as written; decide whether a later release should expire it.
3. **Info:** EE02 image on EE04 hardware compatibility for the OTA mechanics is unknown.
4. **Info:** container CRC time and wake duration against the battery profile are unmeasured.

No blocker was found in the code. Nothing here is marked passed: the phase stays `human_needed` until the EE04 bench and owner sign-off.
