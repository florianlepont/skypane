# Enclosure Wi-Fi comparison test

Does the rear enclosure make the frame's Wi-Fi worse? This file holds the
protocol, the readings and the verdict. Nothing in it is measured until a
block row below is filled from the owner's readings.

## What is measured

The frame's own received signal strength: one integer in dBm per wake, the
value the firmware sends in the `X-Rssi` header with each display request. A
value of 0 means the reading failed and is not data.

No measured attenuation figure for PETG at 2.4 GHz was found, so the effect of
the enclosure is measured, not predicted. The antenna sits above the board on
a block 7 mm from the screen, near the battery pocket (design values, not
measured).

## Why not 20 wakes then 20 wakes

The first rule was: 20 wakes without the enclosure, then 20 wakes with it,
medians within 3 dB. It is weak for these reasons:

- One snapshot per wake, with 1 dB resolution.
- The wake-to-wake spread is assumed to be 2 to 4 dB (an assumption, to be
  measured from the data collected here).
- The standard error of the difference of two medians is then roughly 1 dB or
  more at n = 20.
- With sequential runs, time of day, other users of the access point and small
  position changes are confounded with the enclosure.

## Protocol

1. The bare-frame baseline A1 is taken first, before any enclosure exists, at
   the exact spot and orientation where the frame will later hang. Mark the
   spot with tape and keep a photo (the owner keeps the photo, it is not
   committed). Record the access point name, whether USB is plugged, and how
   the battery was charged.
2. After assembly the blocks run in the order B1, A2, B2 (enclosure, bare,
   enclosure) at the same spot, same orientation, same access point and about
   the same time of day, so the arms are interleaved A1, B1, A2, B2.
3. Each block is at least 15 kept wakes. At the live frame's 300 second
   cadence a block takes about 75 minutes (15 x 300 s, arithmetic), 80 minutes
   with the discarded wake.
4. Discard the first wake after moving or reassembling the frame.
5. Drop every row with rssi 0 and report how many were dropped per block.
6. Report per block: wakes kept, zeros dropped, minimum, first quartile,
   median, third quartile, maximum, standard deviation.
7. Fewer kept wakes than planned means "not done", never extrapolated or
   filled.
8. This file keeps the raw rssi integers of each block in time order (with no
   timestamps beyond the block start and end, and no device identifier) so the
   statistic can be recomputed.

### Set-up

Asked of the owner on 2026-11-19, reported by the owner where stated:

- Wake cadence of the second hardware: the same as the live frame, reported by
  the owner on 2026-11-19. The live frame's 300 s is the value noted in
  `hardware/SECOND-HARDWARE-BATTERY.md` (not re-read from the server). Block
  duration at 300 s is arithmetic: 15 kept wakes plus the discarded wake is 16
  wakes, 4800 s, 80 minutes.
- Room and orientation: the spot is the owner's desk (reported by the owner on 2026-11-19); the owner also reported on 2026-11-19 that the bare frame (board and screen, not in the frame) lies in landscape. The place where the frame will hang later is not stated.
- Spot marked with tape: unknown, asked on 2026-11-19.
- Access point name: Tales Of The City (reported by the owner on 2026-11-19; the name only, no password). The owner first typed "Rales Of The City" and then gave "Tales Of The City"; the owner confirmed "Tales Of The City" on 2026-11-20.
- Power state: battery (reported by the owner on 2026-11-19). Battery charge: 94 % as stated by the owner on 2026-11-19 (not measured here; the voltage can be read from the first exported row).
- Planned start of block A1: left to the assistant by the owner on 2026-11-19; proposed: start as soon as the frame is placed on the desk, in landscape, bare, and note the start time. Not started yet; no reading exists.

### Protocol change

On 2026-11-19 the owner accepted (answer "Oui", reported by the owner) that
the interleaved protocol above replaces the initial rule of 20 wakes without
the enclosure then 20 with it, median not worse by more than 3 dB (design
value). The initial rule stays in this file as the second line of the verdict.

## Statistic and verdict rule

Design values; the owner may adjust them and any change is recorded here with
its date.

- Difference of medians, all B readings minus all A readings (A1 and A2
  pooled, B1 and B2 pooled).
- One-sided 95 percent bootstrap interval: resample each arm with replacement
  5000 times with a fixed seed of 1, take the difference of medians each time;
  the lower bound is the 5th percentile.
- Pass if the lower bound is above -3 dB. With a standard deviation of 3 dB
  and 30 kept wakes per arm this means the observed difference has to be no
  worse than about -1 dB (arithmetic, not a source).
- Second line: the original rule (median of B no more than 3 dB below median
  of A). The verdict states which rule it applies; the bootstrap rule applies
  because the owner accepted the change.
- Drift check: report the difference between the medians of A1 and A2; more
  than 2 dB is flagged "access point drift suspected" (design value).
- The statistic is computed by Claude from the raw readings in this file in a
  throwaway computation, nothing committed. The verdict states "computed by
  Claude from the owner's readings recorded above" and the owner's acceptance
  with its date.

## If it fails

- A block C with the enclosure open and the lid off separates the effect of
  the plastic from the antenna move and the battery.
- A U.FL antenna extension is the documented fallback.
- The choices (change the lid or hook design, accept, retest) are the owner's
  and are recorded with their date.
- Optional: a phone Wi-Fi analyser reading at the frame's spot is a sanity
  check of the access point strength only, not of the frame's antenna.

## Export

Read-only `GET /api/export/battery-history` for the frame's device, with
`since` as a UTC ISO time, with the export access token supplied by the owner
from the environment. The token, the device identifier and the access point
password are never written to this file or to any message. The owner pastes
only the rssi values and the block start and end, not the other columns of the
rows. Only the access point name is recorded.

## Block table

| Block | Condition (A bare, B enclosure) | Order | Start | End | Wakes kept | Zeros dropped | Min | Q1 | Median | Q3 | Max | Std dev | Access point name | Position (tape-marked spot yes or no) | Power (USB or battery) | Source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | A (bare frame, no enclosure) | 1 | 2026-11-19 18:11 UTC (19:10 Paris, as reported by the owner) | 2026-11-19 19:28 UTC | 16 | 0 | -61 | -60 | -59 | -58 | -44 | 5.76 | Tales Of The City | yes (the owner's assembly desk, landscape; not the final hanging place) | battery (94 % as stated by the owner) | read-only export of the frame's history, authorised by the owner on 2026-11-20; reported by the owner (statistics computed by Claude from the exported values) |
| B1 | B (enclosure, assembled during the 2026-11-24 power cut, frame back on at 19:12 Paris per the owner's best estimate) | 2 (not interleaved: no A2 or B2) | 2026-11-24 18:12 UTC (power-on row) | 2026-11-26 17:00 UTC | 541 | 0 | -69 | -61 | -59 | -34 | -26 | not computed | Tales Of The City (not confirmed for this period) | not stated | not stated |
| A0 (before the power cut, state not confirmed) | not an arm (state unknown: see the notes) | 0 (earlier than B1) | 2026-11-24 00:03 UTC | 2026-11-24 05:24 UTC | 61 | 0 | -74 | -73 | -73 | -42 | -39 | 15.43 | not confirmed | not stated | not stated |
| A2 | | | | | | | | | | | | | | | | |
| B2 | | | | | | | | | | | | | | | | |

## Raw readings

rssi integers in dBm, in time order, one line per block.

- A1: -60, -60, -46, -61, -61, -59, -60, -60, -46, -59, -59, -59, -58, -44, -58, -58
- A0 (61 wakes, in time order): -73, -42, -41, -73, -43, -73, -73, -41, -73, -41, -72, -41, -73, -73, -42, -73, -73, -41, -43, -73, -73, -69, -71, -72, -72, -43, -73, -74, -43, -73, -41, -74, -73, -41, -73, -73, -41, -42, -73, -74, -74, -42, -74, -42, -42, -73, -74, -74, -42, -74, -74, -42, -74, -41, -73, -39, -74, -74, -74, -42, -40
- B1 (541 wakes, in time order): -59, -63, -64, -59, -63, -62, -67, -26, -26, -27, -69, -66, -65, -66, -27, -27, -27, -28, -26, -28, -26, -26, -63, -26, -63, -26, -64, -26, -27, -26, -63, -63, -64, -63, -26, -26, -62, -62, -26, -62, -62, -62, -61, -61, -61, -26, -60, -61, -26, -62, -62, -62, -62, -62, -63, -27, -62, -26, -62, -62, -62, -61, -62, -63, -63, -63, -63, -68, -63, -62, -26, -63, -61, -26, -62, -61, -62, -26, -61, -62, -62, -63, -26, -26, -60, -26, -26, -26, -26, -62, -26, -27, -26, -62, -61, -62, -62, -63, -26, -61, -63, -62, -61, -26, -61, -61, -26, -62, -62, -62, -61, -26, -26, -62, -62, -62, -62, -62, -62, -26, -62, -62, -62, -62, -26, -26, -26, -62, -62, -62, -26, -27, -62, -26, -26, -61, -26, -26, -62, -62, -62, -62, -63, -63, -61, -62, -26, -62, -26, -62, -26, -61, -62, -27, -62, -61, -62, -60, -30, -58, -60, -29, -59, -58, -59, -28, -58, -28, -58, -60, -28, -63, -34, -34, -61, -61, -62, -65, -62, -62, -62, -34, -64, -64, -63, -34, -62, -61, -61, -32, -59, -60, -60, -60, -58, -33, -60, -59, -61, -59, -33, -61, -32, -61, -60, -33, -60, -62, -61, -62, -59, -59, -60, -62, -61, -60, -59, -32, -33, -60, -59, -59, -33, -60, -64, -60, -58, -33, -63, -62, -33, -33, -33, -33, -63, -33, -33, -61, -61, -63, -33, -62, -63, -62, -33, -61, -33, -61, -62, -33, -60, -61, -55, -61, -62, -33, -60, -62, -33, -63, -61, -32, -61, -62, -63, -60, -32, -32, -32, -60, -32, -60, -62, -60, -60, -32, -32, -32, -60, -60, -32, -60, -32, -62, -32, -60, -60, -32, -32, -61, -60, -32, -32, -32, -60, -60, -62, -60, -60, -32, -60, -32, -61, -62, -60, -32, -62, -60, -61, -60, -62, -60, -60, -61, -62, -62, -61, -32, -62, -60, -32, -60, -61, -62, -60, -31, -62, -32, -60, -32, -58, -59, -33, -60, -59, -57, -60, -32, -59, -57, -32, -32, -58, -32, -59, -32, -59, -58, -32, -58, -57, -57, -59, -59, -57, -58, -32, -57, -59, -59, -59, -33, -33, -60, -57, -59, -59, -32, -59, -59, -58, -59, -59, -59, -56, -59, -59, -59, -32, -59, -57, -33, -59, -33, -59, -58, -58, -59, -59, -59, -57, -57, -57, -59, -57, -57, -33, -59, -57, -33, -57, -57, -59, -59, -59, -59, -59, -57, -61, -58, -58, -59, -58, -33, -58, -56, -58, -33, -58, -58, -56, -58, -33, -57, -58, -58, -58, -33, -58, -58, -33, -33, -58, -58, -58, -58, -58, -57, -57, -58, -58, -33, -58, -57, -59, -33, -59, -62, -60, -32, -33, -60, -35, -60, -33, -59, -61, -60, -62, -59, -59, -61, -60, -59, -58, -59, -33, -58, -59, -33, -58, -34, -34, -60, -59, -60, -60, -59, -60, -61, -59, -59, -59, -35, -34, -60, -34, -60, -34, -58, -59, -34, -58, -33, -59, -34, -57, -57, -57, -58, -59, -58, -57, -57, -58, -34, -59, -34, -34, -57, -58, -59, -34, -34, -58, -60, -61, -43, -59, -60, -59, -59, -60, -60, -58, -58, -58, -58, -58, -46, -58, -61, -59, -60, -60, -42, -45, -42, -61, -40, -66
- A2:
- B2:

## Notes on block A1

Recorded on 2026-11-20 from a read-only export of the frame's own history, which
the owner authorised in chat ("vas-y, lis l'export"). Only the rssi integers,
the block start and end are kept here; no device identifier, token or other
column is written.

- Start: the owner placed the frame at 19:10 Paris time on 2026-11-19, read as
  18:10 UTC (Paris is UTC+1 in November; the reading of the time zone is
  recorded here, the owner did not state it). The owner also said the frame
  already stood at that spot before, and that no RESET was pressed (the export
  shows only RTC wakes). The frame was therefore not moved, so no first wake
  was discarded; this departs from the protocol's discard rule, which applies
  after a move.
- The block holds the 16 consecutive wakes from the first wake after 18:10 UTC
  (about 80 minutes at 300 s), 16 kept, 0 zero readings dropped.
- Quartiles use the inclusive method. The standard deviation of 5.76 dB is
  inflated by three isolated readings at -44 to -46 dB; the other 13 readings
  have a standard deviation of 1.04 dB and a median of -59 dB. The earlier
  assumption of 2 to 4 dB was a guess; the spread is bimodal (a steady level
  around -60 with occasional readings about 14 dB higher), so a median-based
  statistic is better suited than a mean. The rule is not changed here; the
  owner may adjust it.
- Context only, not part of A1: the same export shows a median near -60 dB
  all night (no zero readings in 177 wakes from 17:02 UTC on 2026-11-19 to
  08:20 UTC on 2026-11-20), which suggests the spot is stable.
- Spot, reported by the owner on 2026-11-20: the desk is the owner's assembly
  desk, not the place where the frame will hang. The comparison of the
  enclosure against the bare frame is therefore made at this desk: blocks B1,
  A2 and B2 must be taken at the same spot, in the same orientation, on the same
  access point, at about the same time of day. The result says what the
  enclosure changes at this desk; it does not measure the signal at the final
  hanging place (walls, distance to the access point and metal nearby are not
  tested). A reading at the hanging place, bare and with the enclosure, is a
  possible later check, to be decided by the owner.
- Block A1 is a baseline. It says nothing about the enclosure; blocks B1, A2
  and B2 come after assembly.

## Verdict

- N kept in A: 16 in A1 (2026-11-19, desk, landscape) and about 1315 wakes of the bare history from 2026-11-19 00:00 to 2026-11-23 18:59 UTC (hourly medians from the owner's export, weighted by the wakes of each hour: an approximation, not a per-wake median)
- N kept in B: 541 (B1; the owner's best estimate puts the assembly at the 2026-11-24 power cut)
- Difference of medians: A1 to B1 0 dB (-59 to -59); bare history to B1 about +1 dB (-60 to -59)
- One-sided lower bound: A1 against B1 -1 dB (bootstrap, 5000 resamples, seed 1); not computed for the history, which is only known as hourly medians
- Rule applied: the bootstrap rule on A1 against B1; not the interleaved protocol (no A2 or B2: the owner declined to take the frame out of the enclosure again because the printed PLA threads would break)
- Second-line result: median of B is not below median of A (0 dB with A1, about +1 dB with the history)
- Drift check: not possible (no A2); the bare history is steady from 2026-11-19 to 2026-11-23 (hourly medians -55 to -64), which shows the access point and the position were stable over those days
- Computed by: Claude on 2026-11-26 from the readings recorded above and from the hourly medians the owner supplied from the frame's read-only export
- Owner accepted on: 2026-11-26, the owner declined a further measure and pointed to the readings already given; the position and the access point after the assembly are not confirmed
- Result: no evidence that the enclosure with the lid lowers the signal; the signal was about 13 dB lower from 2026-11-23 about 20:00 to 2026-11-24 05:24 UTC (A0, median -73) because the frame was moved (reported by the owner on 2026-11-26), so the position moves the reading more than the enclosure does; not a protocol verdict (interleaved blocks not taken)

Notes on the readings (not measured by the assistant, read from the owner's export):

- The readings are bimodal: a weak level around -60 dBm and a strong level from -26 to -34 dBm (29 percent of the B1 wakes, 3 of 16 in A1 at -44 to -46). The cause is not known (two access points or a reading effect are guesses). On the weak level alone B1 has median -60 (384 wakes) against -59 in A1 (13 of 16).
- The medians of B1 by quarter rise from -62 to -58 over the two days; the cause is not known.
- The 61 wakes before the power cut (2026-11-24 00:03 to 05:24 UTC) read -73 and -42; they are block A0. The frame was handled just before (three power-on rows on 2026-11-23 at 19:20:49, 19:28:55 and 19:46:05 UTC) and the level stayed 13 dB below the bare history until the power cut. The test log has the board and the battery placed in the tray on 2026-11-23. The owner reported on 2026-11-26 that the frame was moved then (the new place is not stated), so the lower level is attributed to the position, not to the enclosure; it is not used as an arm.
- One gap of 769 minutes (2026-11-24 05:24 to 18:12 UTC), then a power-on row; firmware fw-v1.2.1 on every row.
