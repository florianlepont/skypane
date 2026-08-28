# Runway Gate Live-Capture Verification (Plan 06-12, Task 1)

Closes 06-RESEARCH.md's Assumption A1 and Pitfall 7 for the two runways
Phase 6 newly made trackable (06-24, 02-20), and re-confirms runway 3's
already-validated gate against fresh live traffic. Uses the shipped
`server/plane/detect.py --runway <id> --json` exactly as the production
poll loop invokes it — no bespoke script, no hand-computed geometry.

## Capture Window

| | |
|---|---|
| Start (UTC) | 2026-08-28T05:29:06Z |
| End (UTC) | 2026-08-28T06:59:32Z |
| Duration | ~90 min 26s |
| Provider | Production default order (`adsbfi` then `adsblol` — no `--provider` override) |
| Cadence | 30s per cycle, all three runway ids polled every cycle (matches `adsb-test/RESULTS.md`'s Phase 1 methodology) |
| Geofence | `adsb-test/runway3.json` (unmodified during the capture) |
| Total polls | 480 (160 cycles × 3 runway ids) |
| Polls with a selection | 95 (83 on runway 3, 0 on 06-24, 12 on 02-20) |
| Polls with no selection (`null`) | 385 |

Raw capture (not committed — 480 JSON lines, one per poll, each recording
`poll_ts`, `runway_requested`, and the exact `detect.py --json` output or
`null`) is retained locally for this session; every figure below is read
directly from those lines.

## Per-Runway Results

### Runway 3 (already-validated corridor, re-confirmed against fresh traffic)

**29 distinct aircraft, 83 accepted selections**, all airborne
(`on_ground: false` in every accepted record — the on-ground pavement gate
from the `missed-flights-not-displayed` debug session was never exercised
by this window's traffic, which is a fact about this capture's traffic
mix, not a gap in that gate).

| Metric | Value |
|---|---|
| `cross_track_m` range (accepted) | −3.37 to 30.56 |
| `along_track_m` range (accepted) | 58.24 to 5763.63 |
| `track_deviation_deg` range (accepted) | 0.00 to 1.64 |

Sample (first 8 of 29 distinct aircraft, in first-seen order):

| Poll (UTC) | Hex | Callsign | Type | cross_track_m | along_track_m | track_dev_deg | Corroborated |
|---|---|---|---|---|---|---|---|
| 05:29:06 | 3455da | VOE3DK | A319 | 7.67 | 3338.07 | 0.12 | True |
| 05:42:05 | 39c5a1 | CRL773 | A339 | 2.47 | 3533.17 | 0.33 | True |
| 05:46:38 | 39de57 | TVF83MR | A20N | 6.46 | 4347.18 | 0.14 | True |
| 05:51:11 | 39ceb4 | TVF750 | B738 | 5.44 | 5753.65 | 0.17 | None |
| 05:54:02 | 39c912 | FWI11B | A35K | 7.39 | 3831.96 | 0.37 | True |
| 05:56:53 | 34568d | VOE96MN | A319 | −3.37 | 5327.97 | 0.30 | True |
| 06:00:52 | 39ceb0 | TVF742F | B738 | 7.22 | 5694.68 | 0.26 | True |
| 06:06:34 | 393f0d | CLG1551 | AT45 | 3.10 | 4738.21 | 0.50 | True |

(Remaining 21 aircraft follow the same pattern — every observed
`cross_track_m` sits well inside the existing 500m corridor half-width and
every `track_deviation_deg` well inside the 30° axis tolerance. Full raw
data available on request; omitted here for length, not selectively
curated — the summary statistics above cover all 83 selections, not just
this sample.)

**Verdict: CONFIRMED.** Real traffic selects correctly and consistently on
runway 3 across a 90-minute window spanning arrivals of many distinct
aircraft types and airlines. No change to `runway3.json`'s `3` entry.

### Runway 06-24 (newly trackable, Assumption A1)

**Zero selections in 160 polls over 90 minutes.**

Orly's runway configuration is wind-dependent (06-RESEARCH.md, this
plan's own instructions anticipate exactly this outcome), and 06-24 sits
only 12° off runway 3's heading — both facts consistent with the airport
simply not routing traffic onto 06-24 during this specific window, not
with a gate defect. No aircraft was ever observed with a `cross_track_m`
or `track_deviation_deg` reading against this runway id at all — there is
no near-miss to report, only a clean empty result.

**Verdict: STILL UNVALIDATED.** Reported honestly as a null result, per
this plan's own instruction that "a capture that observed nothing is a
real and reportable outcome; describing it as confirmation would be worse
than not running it." `runway3.json`'s `06-24` entry is left unchanged —
its `threshold_status` continues to read
`UNVALIDATED (Assumption A1, ...)`, which remains accurate.

### Runway 02-20 (newly trackable, Assumption A1)

**12 distinct aircraft, 12 accepted selections** (one selection per
aircraft — this runway's traffic did not linger across consecutive
30-second polls the way runway 3's did), all airborne.

| Poll (UTC) | Hex | Callsign | Type | cross_track_m | along_track_m | track_dev_deg | Corroborated |
|---|---|---|---|---|---|---|---|
| 05:31:57 | 344698 | VLG883P | A320 | 17.02 | −346.80 | 1.07 | True |
| 05:51:11 | 39de4e | TVF99PC | A20N | −13.19 | −70.79 | 2.08 | True |
| 05:55:44 | 39d314 | TVF22PT | B738 | 6.54 | −324.22 | 0.33 | None |
| 06:09:59 | 39de53 | TVF37DE | A20N | −2.12 | −100.25 | 0.81 | None |
| 06:12:15 | 0201c0 | RAM777Z | B38M | −16.16 | −574.30 | 0.72 | None |
| 06:14:33 | 3964eb | (n/a) | B738 | 3.87 | 307.06 | 0.38 | None |
| 06:32:47 | 39348e | TVF24KU | A20N | 11.00 | 91.80 | 0.43 | True |
| 06:39:02 | 39d30f | TVF298G | B738 | −3.82 | −274.37 | 0.38 | True |
| 06:43:35 | 39d301 | TVF81AQ | B738 | 3.09 | 219.98 | 0.36 | True |
| 06:49:17 | 39de54 | TVF56JZ | A20N | −0.00 | 532.16 | 0.55 | True |
| 06:53:50 | 39dd45 | CCM78JG | A20N | −4.39 | 298.89 | 1.95 | True |
| 06:56:07 | 3475d9 | VLG7FA | A320 | 4.58 | 748.94 | 0.51 | True |

| Metric | Value |
|---|---|
| `cross_track_m` range (accepted) | −16.16 to 17.02 |
| `along_track_m` range (accepted) | −574.30 to 748.94 |
| `track_deviation_deg` range (accepted) | 0.33 to 2.08 |

Every reading is tightly clustered near this runway's own centreline and
axis — consistent with `runway3.json`'s own `geometry_caveat` for this
entry (02/20 is 56° off runway 3's heading, so it is the track-alignment
gate, not the corridor gate, doing the real separating work here). No
aircraft's `track_deviation_deg` came anywhere close to the 30° tolerance
boundary.

**Verdict: PARTIALLY CONFIRMED — read the caveat below before treating
this as a full re-derivation.** The gate genuinely selects real, distinct
aircraft on this runway (12 different aircraft, 12 different airlines/
callsigns, all plausible for Orly traffic), and is exclusive against the
other two runways throughout (see below). What this capture does **not**
establish, and runway 3's original derivation did: an *empty band* between
the largest accepted cross-track offset and the smallest **rejected** one.
`detect.py --json` reports only the winning selection per poll (or
`null`) — it does not surface the geometry of aircraft the gate
considered and rejected. Re-deriving 02-20's threshold the same rigorous
way runway 3's was derived would need a capture method that also logs
near-miss/rejected candidates, which this invocation of the shipped tool
does not do. Because nothing observed here contradicts the copied 500m/
2500m/30° values (every accepted reading sits far inside them, with wide
margin), `runway3.json`'s `02-20` entry is left unchanged rather than
falsely marked "confirmed" in the full sense.

## Cross-Runway Exclusivity

Checked every one of the 160 poll cycles: did the same aircraft hex get
selected under two different runway ids in the same cycle?

**Zero exclusivity violations across 480 polls.** No hex appears as a
selection for more than one runway id at the same `poll_ts`. This directly
answers this plan's second required question for all three runways at
once — the gate never claimed one real aircraft was simultaneously on two
different runways during this capture.

## Summary

| Runway | Distinct aircraft | Selections | Exclusivity | Verdict |
|---|---|---|---|---|
| 3 | 29 | 83 | Clean (0 violations) | **Confirmed** |
| 06-24 | 0 | 0 | N/A (no data) | **Still unvalidated** — null result |
| 02-20 | 12 | 12 | Clean (0 violations) | **Partially confirmed** — real traffic selects correctly and exclusively; the corridor threshold's own empty-band re-derivation needs rejected-candidate data this capture method doesn't produce |

No threshold values in `runway3.json` were changed by this capture — no
reading anywhere in the 480-poll window contradicted the copied
`half_width_m=500` / `extension_m=2500` / `axis_tolerance_deg=30`
values enough to justify a correction, and the honest gaps (06-24's null
result, 02-20's missing rejected-side data) are recorded above rather than
papered over.
