# Phase 65 tracking: internal-consistency analysis

Tool: `scripts/runway_compare.py` (read-only, stdlib, thresholds imported from `server/plane/runway_config.py`).
Input: the committed snapshot in `data/` (see 65-SNAPSHOT.md). No outside source was consulted. No code under `server/` or `stub-server/` was changed.

Labels: **[measured]** = computed from the data; **[hypothesis]** = interpretation, to be checked in the external comparison.

## Data window and coverage

- runway_events: 5031 rows, 2026-11-01T05:09:42Z .. 2026-11-15T13:39:01Z [measured].
- poll_cycles: 75 rows, 2026-11-15T12:13:50Z .. 13:40:35Z only [measured]. This is about 1.5 h of 15 days. Every class that needs poll_cycles is therefore "not testable" for 2026-11-01..11-14 and for most of 11-15.
- Join: runway_events row to poll_cycles rows of the same hex within +/-120 s.

## Per-day counts [measured]

| Day | Departing | Arriving | Stateless |
|-----|-----------|----------|-----------|
| 11-01 | 316 | 11 | 0 |
| 11-02 | 297 | 158 | 0 |
| 11-03 | 250 | 52 | 0 |
| 11-04 | 273 | 5 | 0 |
| 11-05 | 298 | 8 | 0 |
| 11-06 | 20 | 454 | 0 |
| 11-07 | 167 | 373 | 0 |
| 11-08 | 230 | 384 | 0 |
| 11-09 | 293 | 31 | 0 |
| 11-10 | 205 | 279 | 0 |
| 11-11 | 96 | 312 | 0 |
| 11-12 | 265 | 64 | 0 |
| 11-13 | 59 | 0 | 0 |
| 11-14 | 52 | 7 | 0 |
| 11-15 (to 13:39) | 20 | 51 | 1 |
| total | 2841 | 2189 | 1 |

Imbalance note. Over 15 days departing (2841) exceeds arriving (2189), but the split is by day, not mixed: 11-01, 11-04, 11-05, 11-09, 11-12..11-14 are nearly all departures; 11-06, 11-07, 11-08 are mostly arrivals; 11-02, 11-10, 11-11, 11-15 are mixed [measured]. [hypothesis] A one-sided day is plausible if runway 3 is used in one direction per day by the airport's runway configuration (wind), but a day with 0 arrivals (11-13) or 20 departures (11-06) cannot be confirmed from this data. Flag for the external check: compare per-day runway-3 direction against an outside source. The route-direction check below is the internal evidence that some states are wrong, so the imbalance cannot be accepted as pure runway usage without it.

## Class table

Percentages are of the 5031 runway_events rows (held-carry-over and the supplementary line are poll_cycles based).

| Class | Count | % of rows | Notes |
|-------|-------|-----------|-------|
| held-carry-over | 0 | 0 | measured over the 75 poll_cycles rows only; not testable for the rest of the period |
| state-contradiction | 0 | 0 | 5009 of 5031 events not testable (no poll_cycles in the window); the 22 testable events (11-15) show none |
| stateless | 1 | 0.02 | 2026-11-15T12:13:50Z hex 39de41 TVF22UT |
| rotating-route | 0 | 0 | no callsign has two complete routes on one day |
| no-route | not testable | n/a | rule needs 30+ days; data spans 15. With a 5-day threshold: 22 callsigns have an empty origin or destination on every row (e.g. FBU30M 8 days, TVF11KJ 5 days, TVF15MJ 5 days) |
| flip-flop | 39 | 0.78 | one hex arriving then departing within 10 min, in every case in that order (see below) |
| route-direction-mismatch | 447 | 8.88 | route does not fit the state: 241 arriving, 206 departing |

Supplementary [measured]: 3 of 75 poll_cycles rows have a pending aircraft whose own vertical rate contradicts the state of the aircraft on screen (expected during queueing, not a defect by itself).

Context for route-direction-mismatch: 4409 rows have a complete route; 447 of them (10.1%) do not fit their state (arriving 241 of 1973, departing 206 of 2436) [measured]. Route_source of the mismatches: fresh_hit 298, cache_hit 149, so it is not only a stale cache [measured].

### Example rows (hex, ts, callsign)

- stateless: 39de41, 2026-11-15T12:13:50Z, TVF22UT. The same aircraft is in poll_cycles at that instant with rate -832 fpm, pending behind the shown 471f65, so the event was written before the aircraft had a state [measured].
- flip-flop: 39cdce, 2026-11-06T10:19:17Z (no callsign), arriving then departing at 10:19:48Z; 39e5c4, 2026-11-06T12:04:16Z, CRL924; 39c494, 2026-11-06T17:51:12Z, FBU72J.
- route-direction-mismatch: 347696, 2026-11-01T05:50:52Z, VLG3MU, departing BCN-XRY; 3985a3, 2026-11-01T06:03:14Z, AFR49EZ, departing STR-CDG; 39ceb0, 2026-11-01T06:37:42Z, TVF45DA, departing DBV-ORY.
- held-carry-over, rotating-route, state-contradiction: no rows.

### Per-class reading

- held-carry-over (0). Within the 1.5 h covered, a carried state with no vertical rate does not occur: every held row has a rate except 12:14:52 (same aircraft as the row before) [measured]. One related case is visible: at 12:57:20 FWI57Q (hex 39ce24) is promoted as departing (+2752 fpm); at 12:59:55 the next aircraft TVF25SE (3964f8, -960 fpm) appears pending while the shown state stays "departing" (held), and at 13:02:30 it is promoted as arriving [measured]. The held state is correctly replaced on promotion here. Suspected path: held vertical-rate state in `server/plane/runway_config.py` (`infer_from_flight`, `awaits_state`) and promotion in the poll loop [hypothesis].
- state-contradiction (0, mostly not testable). Cannot be assessed for the fortnight. Suspected path: same held state and altitude trend [hypothesis].
- stateless (1). Suspected path: pending aircraft written to history before `awaits_state` resolves a direction [hypothesis].
- flip-flop (39). Days: 11-07 18, 11-11 14, 11-06 4, 11-08 2, 11-10 1 [measured]. For 27 of 39 the first (arriving) state contradicts the route while the second (departing) fits it; 7 have no complete route; 3 are the reverse; 2 contradict in both [measured]. [hypothesis] The first arriving state of a departing aircraft is a wrong held or inferred state corrected by later data. Suspected path: held state / altitude trend near the runway box, where a departing aircraft is first seen low and level.
- route-direction-mismatch (447). Days with most: 11-07 59, 11-08 57, 11-11 56, 11-06 52 [measured]. Repeated callsigns: IBE05KY 11, FBU70A 11, TVF81SF 10, EJU305G 10 [measured]. [hypothesis] Either the state is wrong (see flip-flop) or the route is stale or belongs to another rotation of a reused callsign (adsbdb legacy vs rotating lookup, see `.planning/notes/adsbdb-callsign-lookup-legacy-vs-rotating.md`). Suspected path: enrichment lookup and route sanity (`server/plane/enrich.py`, `server/plane/route_sanity.py`). The data alone cannot say which side is wrong; the external comparison must decide.

## 2026-11-11

Day total: 408 events (312 arriving, 96 departing) [measured].

- Known issue 1, held state carried from one aircraft to the next. The snapshot does not contain the poll_cycles rows of 11-11 (the table starts 2026-11-15 12:13Z), so the carry cannot be located directly [measured]. Indirect evidence in runway_events [measured]: 14 flip-flops on 11-11, all arriving then departing, e.g. 39de53 TVF28VH 05:13:27Z (route ORY-IST on the arriving row), 39de43 TVF43FE 06:05:23Z (ORY-BCN), 4401dc EJU84GE 06:12:05Z (ORY-NCE), 3444cb VLG8066 06:20:50Z (ORY-RAK), 4400ec EJU58AP 06:47:35Z, 39d30d TVF53AJ 07:09:13Z, 39de4b TVF40RN 07:19:31Z, 39de50 (no callsign) 08:43:56Z, 39dd53 CCM43LD 09:01:25Z, 39c48d FBU80G 17:33:36Z, 39cc8a CRL910 20:07:30Z, 39ceac TVF22BF 20:44:04Z, 4404a4 EJU75WT 21:05:06Z, 3985a3 AFR4116 21:10:18Z. The first four have an ORY-origin route on the arriving row (checked); the routes of the others were not individually checked. [hypothesis] this is the footprint of an arriving state held over from the previous aircraft. It is not proof.
- Known issue 2, stale or rotating route. 56 route-direction mismatches on 11-11 [measured], e.g. 06:23:23Z 344501 VLG3MU departing BCN-XRY (fresh_hit, again cache_hit 06:24:25Z), 06:38:50Z 39ceb0 TVF81SF departing BVC-ORY, 06:43:28Z 3463c6 VOE53RC arriving LIL-FAO. VLG3MU, TVF81SF also mismatch on other days (VLG3MU 9 rows overall) [measured], consistent with a stale or reused-callsign route [hypothesis]. A same-day two-route rotation (rotating-route class) does not occur in the snapshot [measured].
- The exact poll_cycles rows for the known issues are not available; they would have had to be exported before the table started recording.

## Out of scope / not changed

No detection, enrichment or history code was modified. Next step (plan 65-03 and the external comparison): check the 447 mismatches, the 39 flip-flops and the per-day direction against an outside source.
