# Phase 65: evidence table (plan 65-06)

Draft for the owner's check. Nothing here approves a merge or a production deploy.

## Success criteria

| # | Criterion | Evidence | Status |
|---|---|---|---|
| 1 | Runway 3 (TRK-01): every mismatch explained, fixed or written down | Recorded period 2026-11-01 to 11-15 (`65-TRACKING-INTERNAL.md`), live session of 2026-11-15 (`65-TRACKING-LIVE.md`), orly evening of 2026-11-17 (`65-TRACKING-MULTI-EVENING.md`: 16 of 19 arrivals drawn, 3 dropped by the queue, one wrong route in 19). Findings F-01..F-06 in `65-DECISIONS-TO-TAKE.md` | Met: F-01 and F-03 fixed or enriched (#457, #458), F-04 covered by an existing test, F-02, F-05, F-06 written down |
| 2 | Other runways and airports (TRK-02): observed live on simulated devices and compared | Nantes (simple), Lyon (parallel), Roissy (four runways), Orly 02/20 against Flightradar24 on 2026-11-17: 18 of 18, 22 of 24, 88 of 102, 15 of 22 departures shown; every miss explained (queue H-01, source coverage H-03). Orly 06/24 not in use: **not tested** | Partly met: 06/24 and Roissy's north pair uncovered, recorded as such |
| 3 | Any fix is agreed, test-first, keeps the golden hashes and the freeze test | G-02 (#457), H-02 and H-01 (#458), six airline names (#461): tests that failed first, 4130 to 11005 tests green with the golden hashes and `stub-server/test_phase47_freeze.py`. Owner agreement quoted in `65-DECISIONS-TO-TAKE.md` | Met |
| 4 | The live frame's configuration is not changed during any session | Every session ran on an isolated scratch root (`65-TRACKING-MULTI-SETUP.md`); the live export was read only | Met |

## What changed in the code (all merged or in draft pull requests)
- #457 `route_contradicts`: a route that excludes the watched airport is dropped (G-02).
- #458 a landing roll-out stays an arrival (H-02); an aircraft dropped unseen keeps its route and direction in the recent-flights list (H-01).
- #461 six airlines known by name only (THY, KLM, FDX, FIN, KAL, UAE), draft.
- This pull request: `scripts/multi_site_replay.py` and its tests; no change under `server/`.

## Measured on the recorded traffic (`65-TRACKING-REPLAY.md`)
Replayed through the current code: the 8 routes without Nantes of the morning session are gone; KAL901's false departure is gone; no aircraft was lost. One case remains (H-05, UAE7V: a wrong vertical-rate sign in the air).

## Written down, not fixed (with the cause)
- F-02, 25 % of flights without a route: adsbdb does not know the callsign; OpenSky ruled out by its terms (`COMPLIANCE.md`).
- G-01, H-03: the ADS-B source does not report some low aircraft (Roissy, Orly departures).
- H-01: the screen advances at most every 90 s; an aircraft waiting 150 s is dropped (now listed with route and direction).
- H-04: about 2 % of routes keep the watched airport but have the wrong other end (adsbdb, rotating callsigns).
- F-06: a queued aircraft has no row until it is drawn or dropped (up to about 150 s).
- G-04: departures near the 3000 ft ceiling, to be measured with more departures.
- H-05: proposed fix awaits the owner's agreement.

## Gates run on this branch
`scripts` tests 54 passed; ruff clean. The full suites ran on the pull requests above.
