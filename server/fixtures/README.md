# server/fixtures — Provenance

Real ADS-B/enrichment records extracted from Phase 1's raw sampling data
(`adsb-test/samples/*.jsonl`, gitignored per `adsb-test/.gitignore`) and from
live `api.adsbdb.com` queries captured in `02-RESEARCH.md`. Committed here,
in the **raw aggregator response shape** (top-level object with the
provider's own aircraft-array key, per-aircraft `hex`/`flight`/`lat`/`lon`/
`alt_baro`/`gs`/`baro_rate`/`seen_pos`), so every test that claims to run
"against real captured data" is checkable on a fresh clone without needing
the gitignored sample directory.

This file is the only reason a future reader can trust the word "real" in
the test names — every field below is marked either **real** (copied
verbatim from a captured record) or **synthetic** (invented for this
fixture, always explicitly noted).

## `geofence_multi_aircraft.json`

- **Source sample:** `adsb-test/samples/` window 1, provider `airplaneslive`
  (`ac` array).
- **UTC timestamp:** `2026-08-04T17:35:42Z`.
- **Provider:** airplanes.live (`api.airplanes.live/v2/point/...`).
- **Real records:**
  - `hex 39d300` / `flight "TVF23WV "` — real, `alt_baro 450`, `gs 137.1`,
    `lat 48.727996`, `lon 2.405139`, `seen_pos 56.972`, `baro_rate -640`.
    This is the D-P2-01 winner (lowest effective altitude, 450ft).
  - `hex 39dd01` / `flight "TVF83DW "` — real, `alt_baro 800`, `gs 139.0`,
    `lat 48.733017`, `lon 2.431852`, `seen_pos 0.94`, `baro_rate -640`.
- **Synthetic records (explicitly marked `_synthetic_note` in the JSON
  itself):**
  - `hex 000001` / `flight "SYNTH01 "` — synthetic, positioned at
    `lat 48.900000`, `lon 2.100000` (outside `runway3.json`'s bbox on
    purpose) to drive the out-of-bbox negative case in
    `test_plane_detection.py`.
  - `hex 000002` / `flight "SYNTH02 "` — synthetic, `lat`/`lon` set to
    `null` on purpose to drive the missing-position negative case.
- **`t` field (phase 03.1):** `t: "B738"` on `39d300` and `t: "A20N"` on
  `39dd01` were added synthetically in phase 03.1 for the aircraft-type
  extraction tests (`server/plane/detect.py`'s `aircraft_type` field,
  PLANE-01/02). Neither value was present in the original captured
  payload; both are chosen to be real ICAO type designators plausible for
  the callsign already on each record — `39d300`/`39dd01` are both
  Transavia France (`TVF`) callsigns, and Transavia France's real
  dominant type per `03.1-CONTEXT.md` D-03 is the B737-family (B738 is
  used here; A20N marks the carrier's parallel A320neo-family fleet).
  `000001`/`000002` deliberately carry no `t` key at all, driving the
  missing-type-designator negative case.

## `geofence_on_ground.json`

- **Source sample:** `adsb-test/samples/` window 2, provider `airplaneslive`.
- **UTC timestamp:** `2026-08-04T20:18:08Z` (on-ground record); the
  airborne `39dd01` record is copied from the same window-1 snapshot as
  `geofence_multi_aircraft.json` above (`2026-08-04T17:35:42Z`).
- **Provider:** airplanes.live.
- **Real records:**
  - `hex 3985a7` / `flight "AFR56XX "` — real, `alt_baro "ground"` (on-ground
    sentinel string, per the aggregator's own convention).
  - `hex 39dd01` / `flight "TVF83DW "` — real, `alt_baro 800`, copied from
    `geofence_multi_aircraft.json`'s source snapshot.
- Under D-P2-01 the on-ground aircraft (`3985a7`, effective altitude `0`)
  beats the 800ft airborne aircraft.
- **`t` field (phase 03.1):** `t: "A320"` on `3985a7` was added
  synthetically in phase 03.1 for the aircraft-type extraction tests
  (`server/plane/detect.py`'s `aircraft_type` field, PLANE-01/02). It was
  not present in the original captured payload; the value is chosen to be
  a real ICAO type designator plausible for the callsign already on the
  record — `3985a7` is an `AFR` (Air France) callsign, and A320 is Air
  France's real Orly type per `03.1-CONTEXT.md` D-03. `39dd01` in this
  file deliberately carries no `t` key.

## `geofence_empty.json`

- **Source:** not a captured record — a minimal valid empty-array response
  shape (`{"ac": []}`), used to drive the D-04 "nothing detected, do not
  rewrite the panel" path in `test_pipeline_e2e.py` and `test_plane_detection.py`.
- All fields synthetic (there is nothing to be real about an empty array).

## `track_arrival_440cb1.json`

- **Source sample:** `adsb-test/samples/` window 2, provider `airplaneslive`.
- **Provider:** airplanes.live.
- **Real records (all three fully real, ordered):**
  1. `2026-08-04T19:53:41Z` — `alt_baro 425`, `baro_rate -640`.
  2. `2026-08-04T19:54:11Z` — `alt_baro 425`, `baro_rate 48`.
  3. `2026-08-04T19:54:41Z` — `alt_baro 425`, `baro_rate 48`.
- This is the real flare/quantisation artefact 02-RESEARCH.md Pitfall 3
  describes (near-zero `baro_rate` right before touchdown on an aircraft
  that is unambiguously landing) — the fixture 02-02's D-03 deadband test
  asserts against. `lat`/`lon`/`gs`/`seen_pos` are carried through from the
  same source records; `hex`/`flight` (`440cb1` / `EJU84YF`) are real.

## `geofence_wrong_runway_39de4a.json`

- **Source:** live `GET opendata.adsb.fi/api/v2/lat/48.7233/lon/2.3794/dist/5`
  during the `runway3-false-positive` debug session, captured by a 15-second
  polling loop over `adsb-test/runway3.json`'s bbox.
- **UTC timestamp:** `2026-08-27T09:29:46Z`.
- **Provider:** adsb.fi (hence the `aircraft` array key, not airplanes.live's
  `ac` — this is the raw shape adsb.fi returned).
- **Every field is real**, copied verbatim from the captured record. Nothing
  in this file is synthetic, including the `t`/`track`/`baro_rate` values the
  tests assert on.
- **What it is:** `hex 39de4a` / `flight "TVF12ZW "` / `r "F-HSXK"` (Transavia
  France A320neo) — **a real reproduction of the reported bug**. At this
  moment the aircraft was **departing Orly runway 20**, not runway 3:
  `track 197.67` matches runway 20's published true heading (198°) to within
  0.4°, and `baro_rate 2304` with `alt_baro 1050` caught it just after
  rotation. Tracked across the following polls it climbed to 4,625 ft while
  continuing south (lat 48.7156 → 48.6550), confirming a departure rather
  than an overflight.
- It sits **750 m from runway 3's centreline** yet **inside** the geofence
  bbox and **below** the 3,000 ft ceiling — i.e. it satisfied every condition
  the pre-fix `select_runway3_aircraft()` tested, and was in fact selected and
  would have been displayed as the runway-3 aircraft, in the "departing"
  state. This is why the bug also corrupted the departure/arrival inference,
  not just the callsign.
- Drives checks 11, 12, 14 in `test_plane_detection.py`.

## `geofence_runway3_arrival_347288.json`

- **Source:** the same live adsb.fi polling run as
  `geofence_wrong_runway_39de4a.json`, 90 seconds later.
- **UTC timestamp:** `2026-08-27T09:31:16Z`.
- **Provider:** adsb.fi.
- **Every field is real**, copied verbatim. Nothing synthetic.
- **What it is:** `hex 347288` / `flight "IBE05DP "` / `r "EC-NTP"` (Iberia
  A320neo) — the **correct counter-example**: a genuine runway-3 arrival, on
  final to runway 25. `track 254.9` is within 0.5° of runway 3's true axis
  (254.41°), `baro_rate -576` at `alt_baro 775`, and it measures **+2.9 m**
  from the centreline. It was tracked down the centreline across six
  consecutive polls (775 → 550 ft) before touchdown.
- Its purpose is to prove the fix did not simply tighten the gate until
  nothing qualifies. Checks 13, 14, 20, 21, 22 fail if genuine runway-3
  traffic stops being selected.
- The record's `wd: 235` / `ws: 13` (wind from 235° at 13 kt) independently
  corroborate that runway 25 was the active arrival runway in that window.

## `geofence_taxiway_masking.json`

- **Source:** the `missed-flights-not-displayed` debug session (2026-08-27).
  **Partly derived — read the split below carefully.** This is the only
  fixture in this directory that is not either wholly captured or wholly
  synthetic, and this section exists so nobody has to guess which half is
  which.
- **Provider shape:** adsb.fi (`aircraft` array key), matching the real
  record it is built around.
- **What it is:** a two-aircraft snapshot reproducing the **masking**
  mechanism — an aircraft that is on the ground but *not on runway 3*
  outranking a real runway-3 movement, because
  `effective_altitude_ft()` scores every on-ground record at exactly `0.0`.
- **Record `347288` / `IBE05DP` — 100% real, verbatim.** Copied field for
  field from `geofence_runway3_arrival_347288.json` (live adsb.fi capture,
  `2026-08-27T09:31:16Z`): a genuine runway-3 arrival on final to runway
  25, `alt_baro 775`, `track 254.9`, **+2.9 m** from the centreline. This
  is the aircraft that must be displayed and was not.
- **Record `3985a7` / `AFR56XX` — real fields, DERIVED position.**
  - **Real (verbatim from `geofence_on_ground.json`'s live capture,
    `2026-08-04T20:18:08Z`):** `hex`, `flight`, `alt_baro "ground"`,
    `gs 12.0`, `baro_rate 0`, `seen_pos 3.4`, `t "A320"`.
  - **Derived:** `lat 48.724957` / `lon 2.379671`. Computed from
    `adsb-test/runway3.json`'s own published threshold coordinates —
    along-track **1657.5 m** (exactly half runway 3's 3315 m derived
    centreline length, i.e. abreast of the runway's midpoint) and
    cross-track **+180.0 m**. This is the same construction the debug
    session's E2 experiment used.
  - **Derived:** `track 74.41` — runway 3's exact axis bearing, so the
    record passes the track gate outright. The fixture has to isolate the
    *lateral* gate; a record rejected by the track gate would prove
    nothing about the bug.
  - **Why 180 m, and why it is honest:** no live capture of an actual
    masking event exists, so this position could not be captured. 180 m is
    the midpoint of the **~150–200 m** runway-parallel ground offset that
    `runway3.json`'s own `corridor.known_residuals` had *already
    documented* (before this session) as passing both pre-existing gates —
    it is this project's own recorded measurement, not a number invented
    to make a test pass. The ICAO Annex 14 runway-to-parallel-taxiway
    separation standard would have grounded it in a published figure, but
    a search during the fix **did not confirm that value**, so it is
    deliberately not cited. The sign of the offset is not load-bearing:
    the gate tests `|cross_track_m|`.
- **What it proves:** at +180 m the masking record is still **inside** the
  airborne corridor (`half_width_m` 500, unchanged by this fix) and still
  passes the track gate — so it is the *new on-ground pavement gate*, and
  nothing pre-existing, that rejects it. Check 29 asserts exactly that, so
  check 30 cannot pass for the wrong reason.
- Drives checks 29, 30 in `test_plane_detection.py`.

## `geofence_pavement_pair.json`

- **Source:** the `missed-flights-not-displayed` debug session, second pass
  (2026-08-28, mechanism B). **Mixed provenance — real, derived and
  synthetic all appear in this file.** Read the split below before trusting
  any value in it. Like `geofence_taxiway_masking.json`, this section exists
  so nobody has to guess which half is which.
- **Shape:** unlike every other fixture here, this file carries **two**
  provider payloads side by side (`adsbfi` → `aircraft` key, `adsblol` →
  `ac` key), because the bug it reproduces only exists *between* two
  sources and cannot be expressed in a single snapshot.
- **What it is:** the case `adsb-test/runway3.json`'s own
  `corridor.known_residuals` item (3) had already documented as left open by
  the mechanism-A ground-gate fix — **two aircraft both genuinely on runway
  3's pavement in the same poll**, one lining up on 07 while the other rolls
  out toward 25. Both score effective altitude exactly `0.0`, so the
  selection falls to the tie-break.
- **The two payloads are identical except `seen_pos`.** Same aircraft, same
  positions, same everything else. Check 32 asserts that structurally, so
  the fixture cannot silently drift into encoding a *real* difference
  between the feeds — the entire point is that nothing about the world
  differs, only each feed's own staleness bookkeeping.
- **Record `3985a7` / `AFR56XX` — real, verbatim, including its position.**
  Copied field for field from `geofence_on_ground.json`'s live
  airplanes.live capture (`2026-08-04T20:18:08Z`): `hex`, `flight`,
  `alt_baro "ground"`, `gs 12.0`, `baro_rate 0`, `t "A320"`, and its real
  `lat 48.719800` / `lon 2.359200`, which measure **along-track 55.2 m,
  cross-track +31.1 m** — 55.2 m past threshold 07, i.e. physically an
  aircraft lining up on 07. **No position derivation was needed for this
  record.** It carries no `track` field, exactly as captured; the documented
  unknown-track rule keeps it corridor-gated rather than rejected.
- **Record `000003` / `SYNTH03` — synthetic identity, derived position, real
  state fields.**
  - **Synthetic:** `hex 000003` / `flight "SYNTH03 "`, following this
    directory's existing `000001`/`000002` convention for a record with no
    real counterpart, and marked `_synthetic_note` in the JSON itself. Only
    **one** real on-ground runway-3 record exists in this repo (`3985a7`),
    so a two-aircraft-on-the-pavement snapshot cannot be assembled from real
    captures alone. **The `hex` value here is load-bearing** — it *is* the
    tie-break under test, and it is chosen to sort before `3985a7`. That is
    called out rather than buried: a reader must not mistake this for a
    captured aircraft.
  - **Derived:** `lat 48.727269` / `lon 2.401346`. Computed from
    `adsb-test/runway3.json`'s own published threshold coordinates —
    along-track **3259.8 m**, cross-track **0.0 m** (the published
    centreline). That is the *real* `3985a7` record's own measured 55.2 m
    distance-from-threshold, mirrored about the runway midpoint: 55.2 m
    short of threshold 25, an aircraft rolling out toward 25. No new
    distance was invented — the one real on-ground measurement this project
    holds is reused at the other end of the runway.
  - **Derived:** `track 74.41` — runway 3's exact axis bearing, so the
    record passes the track gate outright. The fixture has to isolate the
    *tie-break*; a record rejected for an unrelated reason would prove
    nothing.
  - **Real:** `alt_baro "ground"`, `gs 12.0`, `baro_rate 0`, `t "A320"` —
    the verbatim values of the `3985a7` on-ground capture above.
- **`seen_pos` values are all real captures, arranged to produce opposite
  orderings.** `adsb.fi` gets `000003 = 0.94` / `3985a7 = 56.972`;
  `adsb.lol` gets `000003 = 56.972` / `3985a7 = 3.4`. Every one of those
  three numbers is a real captured value from this directory — `0.94` from
  `39dd01`, `56.972` from `39d300` (both `geofence_multi_aircraft.json`),
  and `3.4` is `3985a7`'s **own** real value. The resulting **56.0 s spread**
  is inside `adsb-test/RESULTS.md`'s measured maximum reconstructed
  position-update gap (56.7 s adsb.fi / 69.8 s airplanes.live) and well
  above both medians (36.2 s / 22.4 s) — the spread is calibrated to
  measured feed behaviour, not invented to make a test fail.
- **What it proves:** pre-fix, adsb.fi selected `000003` and adsb.lol
  selected `3985a7` from *one identical reality*, `poll_current_aircraft()`
  saw two different hexes, and the D-04 disagreement branch threw the entire
  cycle away — the panel froze while real runway-3 traffic passed. Check 32
  asserts that divergence is genuinely reproducible; 33-35 assert it no
  longer happens.
- Drives checks 32–37 in `test_plane_detection.py`. Checks 35 and 36
  additionally *derive* asymmetric and disjoint candidate sets from this
  fixture inline (dropping a record, or pairing it against real captures),
  rather than committing near-duplicate fixture files for each.

## `adsbdb_hit_TVF16VB.json`

- **Source:** live `GET api.adsbdb.com/v0/callsign/TVF16VB` response,
  captured verbatim in `02-RESEARCH.md`'s "Code Examples" section.
- **Retrieval date:** 2026-08-08 (per 02-RESEARCH.md's research date).
- All fields real, copied exactly — no paraphrasing of field names or
  values (Transavia France, origin ORY/Paris, destination PMI/Palma De
  Mallorca).

## `adsbdb_miss_EJU84YF.json`

- **Source:** the real 404 body shape for an unknown callsign lookup
  against `api.adsbdb.com`, `{"response": "unknown callsign"}`.
- `EJU84YF` is a **confirmed real adsbdb miss** — 02-RESEARCH.md's
  alternatives table records `hexdb.io` recovering this exact callsign
  precisely because adsbdb did not have it. Not an invented/hypothetical
  miss.
- The fixture additionally records the real HTTP status (`404`) alongside
  the body so `test_enrich.py` (a later plan) can replay both.

## `adsbdb_hit_AIA6412.json`

- **Source:** live `GET https://api.adsbdb.com/v0/callsign/AIA6412`,
  captured verbatim during quick task `260827-kih`'s Task 1 execution.
- **Retrieval date:** 2026-08-27.
- **Every field is real** — this is a genuine 200 response, not a
  hand-built/synthetic body. The live response still attributes the `AIA`
  prefix to the defunct Estonian carrier the plan expected: `airline.name`
  is `"Avies"` (ICAO `AIA`, IATA `U3`, country Estonia) — a real airline
  that ceased operations in 2016, whose ICAO code was never retired
  upstream. `origin`/`destination` both resolve to Paris-Orly (`ORY`/
  `LFPO`) — adsbdb's own answer for this callsign, copied verbatim, not
  edited to look like a more plausible route. This is exactly the
  wrong-carrier-attribution failure mode `enrich.correct_airline_name()`
  (quick task `260827-kih`) exists to fix: `AIA6412` is a real Amelia
  flight (Airbus A320, France), not an Avies flight, but adsbdb's
  crowdsourced database has never been corrected for the fact that a
  different, defunct carrier once held the same ICAO code.
- Follows the same wrapper convention as `adsbdb_miss_EJU84YF.json` (a
  top-level object carrying `http_status` alongside `body`) so
  `test_enrich.py` can replay both the status and the body.
