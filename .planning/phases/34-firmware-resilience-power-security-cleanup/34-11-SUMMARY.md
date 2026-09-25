---
phase: 34-firmware-resilience-power-security-cleanup
plan: 11
subsystem: firmware
tags: [hardware-session, ee02, resilience, power, enrolment, tls, measurements]

# Dependency graph
requires:
  - phase: 34-firmware-resilience-power-security-cleanup
    provides: "plans 34-01..34-10: pure helpers and host tests, byos per-device registry, Kconfig/sdkconfig, build profiles and provision.sh, api_client hardening, wake_guard, app_main wiring, connection reuse and TLS resumption, VENDOR.md and the pre-registered results template"
provides:
  - "hardware/logs/phase34/ - 18 serial and server captures from the one hardware session (SSID/BSSID scrubbed)"
  - "hardware/PHASE34-HARDWARE-SESSION.md - filled results: verdict PASS, 21 scenario rows, wake-duration table, the ~28 s per-cycle overhead explained, battery vs multimeter, deviations"
affects: ["35-21"]

tech-stack:
  added: []
  patterns:
    - "Reconnecting serial capture (wait for the USB-CDC port, cat through tee -a, repeat) instead of firmware/monitor.sh, which exits when the port disappears in deep sleep"

key-files:
  created:
    - hardware/logs/phase34/
  modified:
    - hardware/PHASE34-HARDWARE-SESSION.md

key-decisions:
  - "H-10 (static IP) skipped by the developer: the estimated gain is ~0.7 s per no-change wake, not worth a router reservation and a rebuild on network changes (D-34-03 keeps static IP optional)."
  - "H-16 (brownout) N/A: no variable bench supply; the classification is host-tested and shares H-12's reset -> backoff path."
  - "H-17 recorded as PARTIAL: one multimeter reading (3.92 V vs 3928 mV) instead of three; within the 60 mV threshold."
  - "Scenarios that started from a non-zero backoff_n (H-07, H-09, H-12..H-15) are PASS: the pre-registered failure step, doubling and 6 h cap all held; only the absolute counter differs."

requirements-completed: [FW-01, FW-02, FW-03, FW-04, FW-07, FW-08, FW-09, FW-10, FW-11, FW-12, FW-15]

# Metrics
duration: two sessions (2026-09-24 preparation, 2026-09-25 scenarios)
completed: 2026-09-25
---

# Phase 34 Plan 11: Single hardware session Summary

**On the real EE02 (firmware `e8d293c`), every crash, watchdog and hung wake ends in a backoff sleep, a revoked token re-enrols with the device's own secret without a reflash, byos refuses a wrong secret (401) and an unknown MAC (403), and a no-change wake dropped from 6.3 s to 1.65 s against the VPS. Verdict: PASS on all five ROADMAP success criteria.**

## Performance

- **Duration:** preparation on 2026-09-24 (stopped by the server's BATTERY EMPTY mode), all scenarios on 2026-09-25 after charging
- **Completed:** 2026-09-25
- **Tasks:** developer-run checkpoint, 21 scenarios (19 PASS or PARTIAL, 2 N/A)
- **Files:** 18 capture files created, 1 results document filled

## Accomplishments

- **Resilience (SC1):** panic, task watchdog and interrupt watchdog each give `reset reason=<label>` then `poll fail step=reset`, with the sleep doubling (600 -> 1200 s) up to the 6 h cap. A hung wake is cut by the 300 s budget (`total_ms=300744`, `step=deadline`) before the 60 s task watchdog fires.
- **Re-enrolment (SC2):** a token revoked on the VPS gives `device token rejected; erased` and `step=auth`. The next wake logs `setup accepted` and `poll ok`, with no reflash. The same path held in H-08 and H-19.
- **Per-device secret (SC5):** `provision.sh` wrote the `secret` partition and the token survived. byos returned 401 for a wrong secret, 403 for an unregistered MAC and 401 for the retired shared secret.
- **Wake duration (SC4):**
  - No-change wake: 6336 ms -> 1646 ms against the VPS, and 4.4 s -> 1566 ms on the LAN (n=53).
  - Wi-Fi phase: 1.15 s, down from ~3.0 s for DHCP alone.
  - TLS connect: 1938 ms for a fresh handshake, 97 ms median when the session is resumed.
  - One connection per wake.
  - No PSRAM memtest line.
- **~28 s overhead explained:** 0.4 × 6.3 s + 0.6 × 40 s ≈ 26.5 s. The poll-to-poll interval is `sleep_s` plus the awake time, and screen refreshes (~31.5 s of panel draw) dominate it. The remaining battery-life lever is to refresh less often, which is a server-side change.
- **Other checks:**
  - `sleep_s` 86401 rejected with `step=json`.
  - An http base refused in the production build with `step=config`.
  - `X-Fw-Version` equals `git describe` (`e8d293c` and `e8d293c-dev`).
  - Battery: 3928 mV reported against 3.92 V on the multimeter.

## Deviations from Plan

- **Kit without a reset button:** every RESET was a power switch cycle.
- **`monitor.sh` replaced by a reconnecting capture loop:** the first ~0.5 s of each boot is missing from the captures. This hides the `wake reason`, `boot_count` and `fp_batt` lines, which is why H-02, H-08 and H-17 were only partly observed.
- **Low battery at the start:** BATTERY EMPTY mode (3600 s wakes) stopped the first attempt. The session resumed after charging.
- **Morning departure traffic:** almost every VPS wake was a refresh, so the VPS no-change medians rest on n=3 (before) and n=2 (after). The LAN-after figure (n=53) is the robust one.
- **Skipped or partial:** H-10 skipped, H-16 N/A, H-17 1 of 3 readings. None of these blocks a success criterion.

## Issues Encountered

None in the firmware. The problems were in operating the tools:
- macOS `sed` and `grep` byte handling, fixed with `LC_ALL=C` and `grep -a`;
- the serial port being busy during a flash;
- the stub being stopped, which raised the backoff counter.

All of them are recorded in the results document.

## Next Phase Readiness

- Phase 34 is complete, which clears gate G-34 for plan 35-21 (the firmware comment purge).
- The companion wake interval is back to 300 s.
- Possible follow-ups, not blocking:
  - a static-IP measurement (~0.7 s per no-change wake);
  - two more battery readings under the multimeter;
  - a server-side change to refresh less often.
