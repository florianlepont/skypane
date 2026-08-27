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
