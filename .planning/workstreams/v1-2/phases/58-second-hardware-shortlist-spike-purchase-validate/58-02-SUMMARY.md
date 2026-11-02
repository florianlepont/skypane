---
phase: 58-second-hardware-shortlist-spike-purchase-validate
plan: 02
subsystem: hardware
tags: [second-hardware, spike, esp-idf, ed2208, spectra-6, e-ink]
requires: [58-01]
provides:
  - hardware/SECOND-HARDWARE-SPIKE.md per-candidate verdicts, sources, pin maps, build evidence, risks
  - firmware/spike-7in3/ isolated trial driver (never wired into the live build, never flashed)
affects: [58-03 evaluation unit, 58-04]
key-files:
  created:
    - hardware/SECOND-HARDWARE-SPIKE.md
    - firmware/spike-7in3/CMakeLists.txt
    - firmware/spike-7in3/main/CMakeLists.txt
    - firmware/spike-7in3/main/epd7in3e_trial.h
    - firmware/spike-7in3/main/epd7in3e_trial.c
    - firmware/spike-7in3/main/spike_main.c
    - firmware/spike-7in3/test_epd7in3e_trial.c
    - firmware/spike-7in3/build-spike.sh
    - firmware/spike-7in3/run-spike-host-test.sh
  modified: []
key-decisions:
  - "Front-runner for the trial driver is the Seeed EE04 route (cheapest PASS); its pin map equals the EE02 values already in sdkconfig.ee02.defaults"
  - "Init table re-typed from MIT-licensed Seeed_GFX2 Driver_ED2208.cpp (constants only); PhotoPainter repo has no licence file so nothing taken from it"
status: tasks 1-2 complete; owner decision PENDING; Task 3 not executed
requirements-completed: []
duration: ~10 min session clock
completed: 2026-11-01
---

# Phase 58 Plan 02: Driver spike Summary

**Owner decision PENDING; Task 3 not executed.** Tasks 1 and 2 are done. Nothing was bought, carted, ordered or paid, and nothing was flashed. HW2-01 is not marked complete: its second half is the owner's purchase decision.

## Per-candidate verdict

| Rank | Candidate | Controller | Init sequence found | Pin map | Source licence | Verdict |
|---|---|---|---|---|---|---|
| 1 | Seeed EE04 + 7.3" | ED2208 (Seeed_GFX2 catalogue) | yes, 20 commands | SCK 7, MOSI 9, CS 44, DC 10, RST 38, BUSY 4, EN 43 | MIT | PASS |
| 2 | Waveshare ESP32-S3-PhotoPainter | same command set, chip not named | yes (ESP-IDF source, 14 commands) | MOSI 11, SCLK 10, DC 8, CS 9, RST 12, BUSY 13 | repo has no licence file | PASS (no code reuse) |
| 3 | Waveshare 7.3" (E) raw/HAT (+ESP32 driver board) | same family, chip not named | yes (C reference, 14 commands) | driver board P14/P13/P15/P27/P26/P25 (an "ESP32", 7.3" (E) not listed) | MIT-style notice in file header | PASS for the sequence; driver-board fit unresolved |
| 4 | Seeed reTerminal E1002 | ED2208 ("GDEP073E01 / ED2208") | yes (same driver as 1) | CS 10, DC 11, RST 12, BUSY 13, MOSI 9, SCK 7 | MIT | PASS (exceeds 100 EUR) |
| 5 | Good Display GDEP073E01 | ED2208, stated only by Seeed_GFX2 | yes via 1 and 3 | none of its own (bare panel) | none read | PASS on secondary evidence only |

Sequence evidence is "source read"; no sequence is hardware verified. Details, URLs, SHA-256 prefixes and the not-found list are in `hardware/SECOND-HARDWARE-SPIKE.md`. GitHub commit SHAs could not be read (API and HTML denied by the session proxy); sources are pinned by branch, fetch date and file hash.

## Build evidence (labelled)

- Host test: `firmware/spike-7in3/run-spike-host-test.sh` passes (red first, then green). Packed buffer 192000 bytes, high nibble first; init table order; rejection of wrong length and bad colours; pin tables.
- Container build: **PASS** in the ESP-IDF v5.3.1 container (`idf.py --version` in the image reports v5.3.1), target esp32s3, exit 0, 1007/1007 steps, no warnings, build dir outside the repo. **Provenance caveat:** Docker Hub answered `429 Too Many Requests` and ghcr.io `denied`; the image came from the Docker Hub mirror `mirror.gcr.io/espressif/idf:v5.3.1` (digest sha256:55ab243e8758...2722d) and was tagged locally as `espressif/idf:v5.3.1`. Its digest was not compared with Docker Hub's. The Docker daemon also had to be started by hand.
- Proves: the component compiles and links. Does not prove any behaviour on a panel.

## Recommendation (D-06, cost first)

Seeed XIAO ePaper EE04 (board + 7.3"): at least 78.73 EUR TTC delivery excluded, 98.73 with the shortlist's delivery assumption. Unconfirmed: VAT treatment, delivery to France, Kubii battery (out of stock). Runner-up: Waveshare PhotoPainter, 90.48 EUR at least (105.48 assumed, over target).

## Risks

Paper-only (no panel ever seen); two vendor init sets for the same panel differ in several values; sleep policy differs (Seeed no deep sleep, Waveshare deep sleep) which drives battery life; no ESP-IDF driver published by Seeed; palette mapping from the image container to controller codes undecided; PhotoPainter code is unlicensed and for IDF 5.5.2/6.1; Waveshare ESP32 driver-board fit unconfirmed; Good Display data unreadable; shop/delivery uncertainty; image-provenance caveat above.

## Deviations from Plan

**1. [Rule 3 - Blocking] Docker daemon not running and Docker Hub rate limited.** Started `dockerd` manually; pulled the image through the `mirror.gcr.io` Docker Hub mirror and tagged it locally. Recorded in the spike document; not hidden.

**2. [Rule 3 - Blocking] GitHub API and HTML denied.** Only `raw.githubusercontent.com` was readable, so file paths were found by following the vendors' own READMEs, catalogues and guides, and no commit SHA was recorded.

**3. Commit trailers.** `gsd-sdk query commit` does not add the attribution trailers; both task commits were amended (before any push) to carry them.

## Verification

- `sh firmware/tests/run_host_tests.sh`: 14 suites passed.
- `stub-server/test_phase47_freeze.py`: 21 passed.
- `scripts/check_comment_history.py check`: exit 0.
- No tracked file modified under `firmware/main`, `firmware/CMakeLists.txt`, `firmware/build.sh`, `firmware/tests`, `firmware/sdkconfig*.defaults`, `hardware/`; only new files.

## Pending: Task 3 (owner decision, blocking)

Not executed and not decided on the owner's behalf. Options: buy the recommended candidate, buy the runner-up, or do not buy now. Buying starts Part 2 (plans 58-03, 58-04); Phase 57 does not start before the signing bench passes on the unit. The owner's written answer is to be recorded here.

## Known Stubs

None in tracked code. `spike_main.c` is a compile-only entry point by design and is never flashed.

## Self-Check: PASSED

All created files exist. Task commits: c2a33f8 (Task 1), 01aad71 (Task 2).
