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
- Room and orientation: unknown, asked on 2026-11-19.
- Spot marked with tape: unknown, asked on 2026-11-19.
- Access point name: unknown, asked on 2026-11-19.
- Power state (USB or battery, battery charge): unknown, asked on 2026-11-19.
- Planned start of block A1: unknown, asked on 2026-11-19.

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
| A1 | | | | | | | | | | | | | | | | |
| B1 | | | | | | | | | | | | | | | | |
| A2 | | | | | | | | | | | | | | | | |
| B2 | | | | | | | | | | | | | | | | |

## Raw readings

rssi integers in dBm, in time order, one line per block.

- A1:
- B1:
- A2:
- B2:

## Verdict

- N kept in A:
- N kept in B:
- Difference of medians:
- One-sided lower bound:
- Rule applied:
- Second-line result:
- Drift check:
- Computed by:
- Owner accepted on:
- Result: not done
