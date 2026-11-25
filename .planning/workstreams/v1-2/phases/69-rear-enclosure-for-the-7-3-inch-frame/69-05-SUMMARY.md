---
phase: 69-rear-enclosure-for-the-7-3-inch-frame
plan: 05
status: complete
requirements: [ENC-01]
completed: 2026-11-20
key-files:
  created:
    - hardware/ENCLOSURE-WIFI-TEST.md
---

# Phase 69 Plan 05: Wi-Fi comparison protocol Summary

Interleaved A1/B1/A2/B2 Wi-Fi protocol (bootstrap lower bound on the difference of medians) written and accepted by the owner; baseline block A1 recorded on 2026-11-20 (16 kept wakes, 0 zeros, median -59 dB, from a read-only export the owner authorised).

## Done

- Task 1: `hardware/ENCLOSURE-WIFI-TEST.md` written with the protocol, statistic and verdict rule, export notes, an empty block table (four rows), empty raw readings and an empty verdict (Result: not done).
- Task 2 (partly): recorded on 2026-11-19, reported by the owner:
  - Protocol change accepted ("Oui"); the initial 20 + 20 / 3 dB rule stays as the second line.
  - Wake cadence: same as the live frame; the live frame's 300 s is the value noted in `hardware/SECOND-HARDWARE-BATTERY.md` (not re-read from the server). Block duration is arithmetic: 75 min for 15 kept wakes, 80 min with the discarded wake.

## Resolved on 2026-11-20

- Set-up answers (reported by the owner): the owner's desk, landscape, battery at 94 %, access point name only, placed at 19:10 Paris time, no RESET, frame already at that spot (not moved).
- Task 3: block A1 filled from the owner-authorised read-only export: 16 kept wakes, 0 zeros dropped, minimum -61, Q1 -60, median -59, Q3 -58, maximum -44, standard deviation 5.76 dB (13 of the 16 readings have a spread of 1.04 dB; three isolated readings at -44 to -46). The 19:10 reading as Paris time (UTC+1) and the omission of the first-wake discard (frame not moved) are Claude's readings, written in the file.
- Still to confirm by the owner: the exact access point spelling, and whether the final hanging spot is the same as the desk (the later blocks need the same spot).

## Verification

- Task 1 verify command: passed after rewording one phrase that matched the bearer-value check.
- Task 2 Set-up and Protocol change date checks: passed.
- Task 3 verify: the A1 row has a date, "reported by the owner" and the statistics; the raw values are in the file; no MAC, device identifier, token or password (checked by grep).

## Deviations

None beyond the wording fix above. No commit made (orchestrator commits).
