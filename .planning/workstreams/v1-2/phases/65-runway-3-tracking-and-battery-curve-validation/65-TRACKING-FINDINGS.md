# Phase 65 tracking: findings register

Sources: `65-TRACKING-INTERNAL.md` (15 days of recorded events), `65-TRACKING-LIVE.md` (live comparison, 2026-11-15 15:30 to 15:50 UTC), and the code at `main` on 2026-11-15. No code was changed. Every finding below is a proposal until the owner decides (D-04). **[observed]** = measured or read in code; **[hypothesis]** = interpretation.

Reference limit: no external source was reachable from the sandbox, so the 15-day comparison against a flight-tracking site was not done; the only external reference is the live session (arrivals only, one hour). The `poll_cycles` table holds only 2026-11-15 from 12:13 UTC, so nothing from 11-11 can be replayed.

## Summary

| Id | Area | What | Severity |
|---|---|---|---|
| F-01 | timing | Real landings detected but never drawn | high |
| F-02 | enrichment | No route for aircraft adsbdb does not know | medium |
| F-03 | enrichment | A stale route that does not mention the watched airport is shown | medium |
| F-04 | held state | The 2026-11-11 carried-over state cannot be reproduced; a guard exists since 2026-11-13 | low (unproven) |
| F-05 | detection | DAH1109 possibly not detected | open |
| F-06 | timing | An aircraft waiting in the queue is invisible in "recent flights" | low |

### F-01 Real landings detected but never drawn
- Area: timing (display queue).
- Evidence [observed]: 3 of 7 aircraft in the live session (VLG2VN, EJU69MC, AFR97SV; TVF90TN as a fourth, not confirmed) were detected, queued and dropped. Each was dropped on the first cycle at least 150 s after first sight. Over the 3 h 35 of `poll_cycles` (12:13 to 15:50 UTC): 36 cycles promoted an aircraft, 27 cycles dropped at least one.
- Root cause [observed in code]: `server/poll_cycle.py`, `pop_fresh_pending()` discards a queued aircraft older than `MAX_STALENESS_S` = 150 s and draws the most recently seen of the others. The image may change only every `wake_interval_s` = 300 s (`check_interval.redraw_due()`, applied by `_redraw_blocked()` while the check-interval experiment is active; at the time of the session the experiment was active with a 60 s check interval). An aircraft first seen in the 150 s after a redraw therefore goes stale before the next one. With one landing every 2 to 4 minutes on this runway, about half cannot be drawn.
- [hypothesis]: without the experiment the frame still wakes every 300 s, so the same limit applies. Not checked.
- Proposed remedies (owner to choose): (a) keep the behaviour and document it: the frame is a "right now" board and a 5 minute wake cannot show every aircraft; (b) raise `MAX_STALENESS_S` so the aircraft is drawn after landing (contradicts "right now"); (c) shorten the wake interval (excluded from this phase: Phase 47.2 and v1.3 power saving); (d) show dropped aircraft in the companion as "not shown" (they are already written to `runway_events`).
- Touches golden hashes or frozen fields: (a) and (d) no; (b) changes a constant outside the render, golden hashes not expected to move, to be checked by a test.
- Owner decision: pending.

### F-02 No route for aircraft adsbdb does not know
- Area: enrichment (`server/plane/enrich.py`).
- Evidence [observed]: 622 of 5031 events over 15 days (534 `airline_only`, 88 `miss`, 12.4 %). Live: TVF18BM (from Beirut) recorded without a route; adsbdb answers "unknown callsign".
- Root cause [observed]: the only route source is adsbdb by callsign; an unknown callsign falls back to the airline name.
- Remedy (proposal, not a defect of detection): add a second route source, or accept the airline-only display. A new source needs a terms check (`COMPLIANCE.md`).
- Owner decision: pending.

### F-03 A stale route that does not mention the watched airport is shown
- Area: enrichment (`server/plane/route_sanity.py`, `route_contradicts()` and `server/poll_cycle.py`, `_drop_contradicting_route()`).
- Evidence [observed]: 410 of 4409 events with a complete route (9.3 %) over 15 days have a route that cannot be true (departure not from ORY, or arrival not to ORY). About 50 per day until 2026-11-12, then 3, 1 and 2 on 11-13, 11-14 and 11-15. The 6 residual rows (for example TVF47HR departing NTE > MRS, VLG6VM departing VLC > BRU, IBE05KY departing MAD > LIS twice, AFR78KG arriving PUF > LYS) are all routes that do not contain ORY at all. Live: EJU69MC, which the owner says came from Milan, has an adsbdb route CAG > BER.
- Root cause [observed in code]: `route_contradicts()` rejects only an arrival whose origin is a watched airport or a departure whose destination is a watched airport. A stale route that contains no watched airport passes, so the wrong city can be drawn. The existing filter (present since the squash commit of 2026-11-13) explains the drop in the daily counts.
- Proposed remedy: also treat a complete route as contradicting when it contains no watched airport in the matching role (arrival: destination watched; departure: origin watched), then fall back to the airline-only display. Risk: diversions and position mode (no watched airport), to be handled by the test cases.
- Touches frozen fields: `stub-server/test_phase47_freeze.py` covers wake cadence, battery and poll state fields; no effect expected, to be checked.
- Owner decision: pending.

### F-04 The 2026-11-11 carried-over arrival/departure state
- Area: held vertical-rate state (`server/plane/runway_config.py`, `server/poll_cycle.py`).
- Evidence [observed]: not reproducible. `poll_cycles` has no rows before 2026-11-15. Indirect: 39 events switch from arriving to departing within 10 minutes, 14 of them on 11-11 and 18 on 11-07; in 27 of the 39 the first state contradicts the route and the second fits it [hypothesis: first state wrong, corrected later].
- Code [observed]: `advance_display_queue()` resets `prior_confirmed_state` to None when the promoted aircraft differs from the outgoing one ("a different aircraft never inherits the previous one's direction"). This guard is present on `main` since the squash commit of 2026-11-13, i.e. after the 11-11 incident, which matches a fix. No test built from the recorded failing row exists.
- Live check [observed]: no carry-over seen in 8 aircraft, all arrivals; a departure after an arrival was not tested.
- Proposal: keep the guard, add a test with two consecutive aircraft (arrival then departure at a take-off roll inside the +/-200 ft/min deadband). Needs a departure session to confirm in production.
- Owner decision: pending.

### F-05 DAH1109 possibly not detected
- Area: detection.
- Evidence: the owner reported "DAH1109 arrivé" at 15:35:34 UTC; only DAH1108 (detected 15:33:16) exists in the export. Unresolved: wrong callsign or missed aircraft.
- Needs from the owner: touch-down time and hex.
- Owner decision: pending.

### F-06 An aircraft waiting in the queue is invisible
- Area: timing (`server/history_db.py`, cadence rule).
- Evidence [observed]: a row is written only when an aircraft is drawn or dropped. VLG2VN was first seen at 15:35:51 and its row appeared at 15:38:24. The companion's "recent flights" (`companion/pages/home_page.py`) reads the table directly, with no cache, so it lags by up to 150 s plus the queue wait.
- Disposition candidate: design choice, document it.
- Owner decision: pending.

## Work for plan 05
Empty until the owner decides. Candidates for a test-first fix, if agreed: F-03 (recorded rows: TVF47HR 2026-11-13T13:06:56Z, VLG6VM 14:52:55Z, IBE05KY 18:11:34Z, AFR78KG 2026-11-15T10:56:39Z, EJU69MC 2026-11-15T15:40:28Z), F-04 (test only).

## Coverage not achieved
Departures were not observed live. The 15-day external comparison was not done. Other runways and airports are untouched (owner question open).
