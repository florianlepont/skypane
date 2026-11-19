---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
plan: 05
status: partial
requirements: [ENC-01]
completed: 2026-11-19
key-files:
  created:
    - hardware/ENCLOSURE-WIFI-TEST.md
---

# Phase 69 Plan 05: Wi-Fi comparison protocol Summary

Interleaved A1/B1/A2/B2 Wi-Fi protocol (bootstrap lower bound on the difference of medians) written and accepted by the owner; baseline block A1 not taken yet.

## Done

- Task 1: `hardware/ENCLOSURE-WIFI-TEST.md` written with the protocol, statistic and verdict rule, export notes, an empty block table (four rows), empty raw readings and an empty verdict (Result: not done).
- Task 2 (partly): recorded on 2026-11-19, reported by the owner:
  - Protocol change accepted ("Oui"); the initial 20 + 20 / 3 dB rule stays as the second line.
  - Wake cadence: same as the live frame; the live frame's 300 s is the value noted in `hardware/SECOND-HARDWARE-BATTERY.md` (not re-read from the server). Block duration is arithmetic: 75 min for 15 kept wakes, 80 min with the discarded wake.

## Not done (waiting on the owner)

- Task 2 remainder: room and orientation, taped spot, access point name, power state and planned start are recorded as "unknown, asked on 2026-11-19". Nothing invented.
- Task 3: baseline A1 not taken. The A1 row is empty and the verdict Result is "not done". No reading was inferred.

## What the owner still has to do for A1

Answer the remaining set-up questions (room and orientation, taped spot, access point name only, USB or battery and charge state, start time), then run at least 15 kept wakes on the bare frame at the marked spot (about 75 minutes at 300 s, first wake after placing it discarded, rssi 0 rows dropped), and paste only the rssi values in time order plus start and end time with the time zone. No device id, token or password.

## Verification

- Task 1 verify command: passed after rewording one phrase that matched the bearer-value check.
- Task 2 Set-up and Protocol change date checks: passed.
- Task 3 verify: not run (block not taken).

## Deviations

None beyond the wording fix above. No commit made (orchestrator commits).
