---
status: awaiting_human_verify
trigger: "Incohérences dans les données de détection avion sur la piste 3 (runway 3) : l'utilisateur a observé des cas où l'appareil détecté/affiché ne correspond pas réellement à runway 3 - possiblement dû à une divergence entre les deux sources ADS-B agrégées (airplanes.live primaire, adsb.fi secondaire) dans server/plane/detect.py, ou à un problème dans la logique de géofencing/sélection (select_runway3_aircraft()) ou l'inférence d'état départ/arrivée dans server/plane/runway_config.py. Objectif : investiguer la cause racine de ces incohérences avant de consolider/fiabiliser les sources de données, en amont de l'exécution de la Phase 5."
created: 2026-08-27T00:00:00Z
updated: 2026-08-27T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

hypothesis: CONFIRMED (and broader than the original theory). `runway3.json`'s bbox is an axis-aligned 19.8 km2 box around a 3.3 km runway that contains 71.9% of runway 06/24 AND 80.5% of runway 02/20, and `select_runway3_aircraft()` applies no lateral or directional test whatsoever — so any low aircraft anywhere in that box, on any Orly runway, can win selection as "runway 3".
test: DONE — real published geometry (OurAirports LFPO) quantified the overlap; a 22-poll live adsb.fi capture caught two real wrong-runway aircraft being selected (a runway-20 departure and a 02/20-aligned arrival) alongside two correctly-selected real runway-25 arrivals.
expecting: DONE — real runway-3 traffic measured at <=31 m cross-track / <=0.7 deg off axis; real wrong-runway traffic at >=611 m / ~56 deg. Two cleanly separated populations.
next_action: WAITING ON USER. Fix implemented, committed and self-verified (full suite green, 53-poll before/after replay on real data, live end-to-end run). Awaiting the user's confirmation that the frame no longer shows wrong-runway aircraft in their real workflow before this session is archived to .planning/debug/resolved/ and appended to the knowledge base.
reasoning_checkpoint:
  hypothesis: "runway3.json's bbox admits most of both neighbouring Orly runways (06/24: 71.9% of its paved surface; 02/20: 80.5%, including its 02 threshold), and select_runway3_aircraft() ranks candidates only by altitude/freshness/hex — it never tests whether the aircraft is laterally on runway 3's centreline or pointing along runway 3's axis. Any low aircraft in the box therefore wins."
  confirming_evidence:
    - "Direct computation against real published OurAirports LFPO geometry: 2621 m of runway 06/24's 3647 m and 1935 m of runway 02/20's 2403 m lie inside the bbox; runway 02's threshold is itself inside it. bbox is 19.8 km2 and reaches 2229 m cross-track from runway 3's centreline."
    - "Live capture, directly observed: hex 39de4a (TVF12ZW) was SELECTED by the current code at 1050 ft while climbing +2304 fpm on track 197.67 deg, 750 m south of runway 3's centreline — a real departure off runway 20, not runway 3."
    - "Live capture, second instance: hex 3964e8 selected at 825 ft, track 198.43 deg, 60 m from runway 02's published threshold, 611 m off runway 3's centreline."
    - "Contrast, same capture: real runway-25 arrivals 347288 (IBE05DP) and 39cea8 (TVF45RP) sat at +2..+7 m cross-track with 0.0-0.7 deg axis deviation across 6 polls — so the discriminating signals are present and unambiguous in the very same data."
    - "All three committed real runway-3 fixtures measure +3.1, +14.3 and +31.0 m cross-track, corroborating that genuine runway-3 traffic hugs the centreline."
  falsification_test: "If real runway-3 traffic had shown cross-track offsets or axis deviations overlapping the wrong-runway population (e.g. genuine runway-3 aircraft at 600+ m off centreline, or wrong-runway aircraft within 30 m), the corridor/track gates could not separate them and the hypothesis that a geometric gate fixes this would be refuted. Measured: the two populations are separated by an empty 580 m band and an empty 55 deg band. Not refuted."
  fix_rationale: "The root cause is a missing geometric constraint, so the fix adds exactly that constraint rather than tuning the sort. Two gates are required and neither is redundant: runway 06/24 is only 12 deg off runway 3's heading (a track gate cannot separate it) but never comes within 887 m of its centreline (a corridor gate can); runway 02/20 physically crosses runway 3's centreline at 0 m (a corridor gate cannot separate it) but is 56 deg off its heading (a track gate can). Cross-source validation is layered on top as defence-in-depth for the residual, since it addresses a different failure mode (one feed's bad or stale record) than the geometry gates do."
  blind_spots:
    - "The primary aggregator (airplanes.live) returns 403 today, so the cross-validation path could only be exercised against stubbed providers in tests, never against two live feeds simultaneously."
    - "An aircraft taxiing on a runway-parallel taxiway (~150-200 m offset, runway-aligned track) passes both gates. Tightening the corridor below ~150 m would start rejecting genuine approach traffic, so this residual is documented rather than closed."
    - "A record carrying no `track` field is not disqualified by the alignment gate (it still must pass the corridor). Measured 21/21 live records carried a numeric track, so exposure is small — but it is non-zero, and the committed pre-existing fixtures carry no track at all."
    - "The 15-minute live window sampled one runway configuration on one afternoon; a different Orly configuration (e.g. 06/24 active for departures) was not observed."
tdd_checkpoint: null

## Symptoms
<!-- Written during gathering, then immutable -->

expected: Only aircraft genuinely using Orly runway 3 (departing or landing on it) are ever selected and displayed by `select_runway3_aircraft()`.
actual: The user has observed cases where the aircraft shown on the frame does not seem to actually be using runway 3 — a wrong-runway false positive in the detection/selection pipeline.
errors: None — no crash, no exception. This is a silent incorrect-selection issue, not a failure that surfaces in logs.
reproduction: No specific callsign/timestamp available — a recurring general observation since initial production deployment (Phase 2), not a single reproducible incident.
started: Since the initial Phase 2 deployment (real ADS-B detection went live then); user cannot pin down a more specific onset.

## Additional scope (from conversation, not a classic symptom field)

The user also asked whether the two ADS-B sources (airplanes.live primary, adsb.fi secondary) should be "consolidated" to provide a backup/cross-check. Current architecture confirmed by inline code read (server/plane/detect.py `poll_current_aircraft()`): adsb.fi is used ONLY as a failover when airplanes.live's query errors or returns no candidate — never for cross-validating a questionable selection against the primary. A wrong-runway aircraft would appear identically from either source, so source failover alone does not address this symptom.

User-approved fix scope (both, pending investigation confirming the root cause):
1. Tighten geofence precision (bbox and/or a heading/track check) so aircraft on runway 06/24 no longer win selection as runway 3.
2. Add cross-validation between airplanes.live and adsb.fi per poll (query both, compare selections, treat disagreement as a signal of doubt) as defense-in-depth — not just failover.

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: 2026-08-27T00:00:00Z
  checked: server/plane/detect.py `select_runway3_aircraft()` docstring
  found: "Known limitation (accepted for v1, inherited from runway3.json's own sourcing note): the bbox is not perfectly exclusive of the nearby 06/24 runway, so an occasional wrong-runway aircraft can win this selection."
  implication: The reported symptom matches a pre-existing, disclosed, deliberately-accepted-for-v1 trade-off in the code itself — this is very likely the root cause, not an unknown defect. Confirm with real geofence/track data before treating as fully diagnosed.
- timestamp: 2026-08-27T00:00:00Z
  checked: server/plane/detect.py `poll_current_aircraft()`
  found: adsb.fi (secondary) is only queried when airplanes.live's query raises an exception or returns no in-geofence/below-ceiling candidate; there is no per-poll cross-validation between the two sources when airplanes.live succeeds.
  implication: The existing primary/secondary pattern is pure failover for source availability, not consensus/cross-validation for selection correctness — it would not have caught or prevented a wrong-runway false positive from either source.
- timestamp: 2026-08-27T09:25:00Z
  checked: Real published Orly runway geometry — OurAirports runways.csv (https://davidmegginson.github.io/ourairports-data/runways.csv), the exact source runway3.json itself cites, downloaded fresh this session. All three LFPO rows.
  found: |
    02/20: le 02 (48.717499, 2.376700) hdg 018T, he 20 (48.737999, 2.386970) hdg 198T, 7874ft = 2400m
    06/24: le 06 (48.720001, 2.316920) hdg 062T, he 24 (48.735500, 2.360680) hdg 242T, 11975ft = 3650m
    07/25: le 07 (48.719398, 2.358590) hdg 074T, he 25 (48.727402, 2.402070) hdg 254T, 10892ft = 3320m
    The 07/25 row matches runway3.json's `runway` block byte-for-byte, so runway3.json's runway-3 identity is confirmed correct. The bbox is what is wrong.
  implication: Runway 3's own geometry is right; the discrepancy must be in the bbox derived from it. Gave exact coordinates for the neighbouring runways to quantify the overlap.
- timestamp: 2026-08-27T09:30:00Z
  checked: Computed clipping of each real runway's paved surface against runway3.json's bbox (lat 48.712-48.734, lon 2.325-2.435), plus along/cross-track offsets relative to the true 07/25 centreline (bearing 74.4T, length 3315m).
  found: |
    bbox is 8078 m (E-W) x 2449 m (N-S) = 19.8 km^2 -- for a 3.3 km runway.
    07/25 (runway 3): 3315 m of 3315 m inside = 100.0%   <- correct
    06/24:            2621 m of 3647 m inside =  71.9%   <- WRONG-RUNWAY EXPOSURE
    02/20:            1935 m of 2403 m inside =  80.5%   <- WRONG-RUNWAY EXPOSURE
    Runway 02's threshold (48.717499, 2.376700) is itself INSIDE the bbox.
    bbox corners reach up to 2229 m cross-track from the 07/25 centreline (NW corner)
    -- not the "small lateral margin" its sourcing note claims.
  implication: |
    The bbox is far worse than its own sourcing note admits, on TWO counts:
    (1) the note says the box "is tight enough to exclude the crossing 02/20 runway" -- FALSE, 80.5% of 02/20 is inside, including its 02 threshold;
    (2) the note downplays 06/24 as merely "not perfectly exclusive" -- in fact 71.9% of its paved surface is inside.
    So the geofence admits most of BOTH other Orly runways, and selection applies no directional or lateral test to tell them apart.
- timestamp: 2026-08-27T09:32:00Z
  checked: Which discriminating signal separates runway 3 from each neighbour (computed from the real geometry above).
  found: |
    06/24 vs 07/25: only 12 deg apart in heading (062/242 vs 074/254) -> a track/heading gate CANNOT separate them.
                    But 06/24's surface never comes closer than 887 m cross-track to the 07/25 centreline
                    (>= ~1034 m for the part actually inside the bbox) -> a lateral corridor CAN separate them.
    02/20 vs 07/25: 02/20 physically CROSSES the 07/25 centreline (min |cross| = 0 m, at along=+1601 m,
                    i.e. mid-runway-3) -> a lateral corridor CANNOT separate them.
                    But they are 56 deg apart in heading (018/198 vs 074/254) -> a track gate CAN separate them.
  implication: |
    Decisive design finding: NEITHER signal alone is sufficient. The corridor handles 06/24; the track
    gate handles 02/20; each is blind to the other's runway. Both parts of approved fix 1
    (bbox refinement AND a heading/track check) are required by the evidence -- this is not an
    either/or, and it is not belt-and-braces.
- timestamp: 2026-08-27T09:40:00Z
  checked: Live query of adsb.fi (opendata.adsb.fi/api/v2/lat/48.7233/lon/2.3794/dist/5) over the real bbox, 2026-08-27 ~11:40 CEST.
  found: |
    Single aircraft returned: hex 3964e8, lat 48.71701, lon 2.376589, alt_baro 825 ft, track 198.43, gs 137.
    - Inside bbox: lat and lon both within range -> YES
    - Below 3000ft ceiling -> YES
    - Therefore the CURRENT select_runway3_aircraft() selects it as "the aircraft using runway 3".
    Its track of 198.43 deg is runway 20's published true heading (198T) to within 0.4 deg, and its
    position is ~60 m from runway 02's published threshold (48.717499, 2.376700). Deviation from
    runway 3's axis: 56.0 deg. Cross-track offset from the 07/25 centreline: -561 m.
  implication: |
    REPRODUCED LIVE, FIRST TRY. This is not a theoretical risk and not merely the "occasional"
    wrong-runway aircraft the docstring concedes -- a real aircraft on final to Orly runway 02/20
    was selected and would have been displayed as "runway 3". The symptom is confirmed with real data.
- timestamp: 2026-08-27T09:42:00Z
  checked: Live query of the PRIMARY provider, api.airplanes.live/v2/point/48.7233/2.3794/5, same User-Agent the server sends.
  found: |
    HTTP 403 Forbidden, body: {"error": "Please contact us at contact@airplanes.live. Your email MUST
    include any links, a description of the project, and any information you deem appropriate."}
    adsb.fi answered 200 for the identical query in the same minute.
  implication: |
    Independent, separate live finding: the configured PRIMARY aggregator is currently hard-blocked, so
    poll_current_aircraft() is silently running on the secondary for every poll today. It does not cause
    the wrong-runway symptom (the 02/20 aircraft above came from adsb.fi and would look identical from
    either feed), but it constrains fix 2: per-poll cross-validation must degrade gracefully to
    "single source, no corroboration" rather than treating an unreachable provider as disagreement.
- timestamp: 2026-08-27T10:05:00Z
  checked: 22-poll live capture of adsb.fi over the real bbox (15s interval, 2026-08-27 ~11:45-12:00 CEST), running the CURRENT unfixed select_runway3_aircraft() and annotating every selection with along/cross-track offset from the real 07/25 centreline and track-vs-axis deviation.
  found: |
    SELECTED as "runway 3" by the current code, with ground truth from the raw records:
      poll 3      39de4a TVF12ZW (F-HSXK, A20N)  alt 1050ft  cross= -750 m  track 197.67  dev 56.7 deg
                  -> baro_rate +2304 fpm, climbing 1050->4625 ft over polls 3-9 while tracking ~197 deg
                     SOUTH (lat 48.7156 -> 48.6550). This is a real DEPARTURE off Orly runway 20.
      probe       3964e8                         alt  825ft  cross= -611 m  track 198.43  dev 56.0 deg
                  -> 60 m from runway 02's published threshold, on 02/20's axis to within 0.4 deg.
      polls 9-14  347288 IBE05DP (EC-NTP, A20N)  alt 775->550 cross=   +3 m  track 254.2-254.9  dev 0.2-0.5
                  -> baro_rate -896..-640, a real runway-25 ARRIVAL down the centreline. CORRECT.
      polls 20-22 39cea8 TVF45RP                 alt 775->550 cross=  +2..+7 track 254.4-255.1  dev 0.0-0.7
                  -> another real runway-25 ARRIVAL. CORRECT.
    Also measured: 21/21 raw records (100%) carried a numeric `track` field.
  implication: |
    Two of the aircraft the current code selected as "the aircraft using runway 3" in a 15-minute
    window were demonstrably not on runway 3 at all. The TVF12ZW case is the worst kind: it was
    climbing at +2304 fpm, so runway_config.infer_from_flight() would also have flipped the panel
    to "departing" -- the false positive corrupts the departure/arrival state, not just the callsign.
    This directly explains the user's report AND the trigger's mention of state inference.
- timestamp: 2026-08-27T10:10:00Z
  checked: Cross-track offset of every REAL runway-3 aircraft available (3 committed fixtures + 6 live captures) vs every REAL wrong-runway aircraft observed, plus the neighbouring runways' paved surfaces.
  found: |
    REAL runway-3 traffic          cross-track from the 07/25 centreline
      39d300 TVF23WV (fixture)        +3.1 m
      39dd01 TVF83DW (fixture)       +14.3 m
      3985a7 AFR56XX (fixture, ground) +31.0 m
      347288 IBE05DP (live, x3)       +3.0 m
      39cea8 TVF45RP (live, x3)       +2..+7 m
      -> MAXIMUM observed: 31 m
    REAL wrong-runway traffic
      3964e8                        -611.3 m
      39de4a TVF12ZW                -750.4 m
      runway 06/24 paved surface     >= 887 m (>= ~1034 m for the part inside the bbox)
      -> MINIMUM observed: 611 m
    Track deviation from runway 3's axis: real runway-3 traffic 0.0-0.7 deg; wrong-runway 56.0-56.7 deg.
    Also: test_poll_loop.py's synthetic snapshot sits at cross=+7.6 m, so it is unaffected by a corridor gate.
  implication: |
    The two populations are separated by an EMPTY 580 m gap in cross-track (31 m vs 611 m) and an
    EMPTY 55 deg gap in track deviation (0.7 deg vs 56.0 deg). Both gates are therefore trivially
    separable on real data, with enormous margin -- a 500 m corridor half-width sits 16x above the
    largest real runway-3 offset and 1.8x below the nearest wrong-runway paved surface; a 30 deg
    axis tolerance sits 43x above the largest real deviation and well below the 56 deg 02/20 axis
    separation. These are not guessed thresholds; they are read off measured separation.
- timestamp: 2026-08-27T10:12:00Z
  checked: `track` vs `mag_heading` vs `dir` in the raw adsb.fi records, against the OurAirports heading convention.
  found: |
    For IBE05DP on the runway-25 centreline: track 254.24-254.9, mag_heading 249.3-253.7, dir 74.4-74.5.
    The centreline bearing computed from the two published thresholds is 74.41 deg TRUE.
    `track` matches it to within 0.5 deg; `mag_heading` is ~4 deg off (magnetic variation);
    `dir` is adsb.fi's bearing FROM THE QUERY CENTRE to the aircraft, not the aircraft's heading at all.
  implication: |
    The alignment gate must use `track` (true track over ground), never `mag_heading` and never `dir`.
    Corollary defect found in runway3.json: its `runway.source` calls 074/254 "magnetic", but
    OurAirports supplies them as `le_heading_degT`/`he_heading_degT` (degrees TRUE) and the
    threshold-derived bearing confirms 74.41 TRUE. The "magnetic" label is wrong and would mislead
    anyone implementing exactly this gate.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  `select_runway3_aircraft()` decided "this aircraft is using runway 3" from two conditions that
  say nothing about runway 3: inside `runway3.json`'s bbox, and below the 3000 ft ceiling. It then
  ranked those candidates by altitude, position freshness and hex. At no point did it test whether
  the aircraft was laterally on runway 3's centreline or pointing along runway 3's axis.

  That would be harmless if the bbox were a runway-3 filter. It is not. Measured against the real
  published OurAirports LFPO geometry (the very source runway3.json cites), the bbox is an
  axis-aligned 8078 m x 2449 m = 19.8 km2 box around a 3.3 km runway, and it contains:
    - 2621 m of runway 06/24's 3647 m paved surface (71.9%)
    - 1935 m of runway 02/20's 2403 m paved surface (80.5%), including runway 02's threshold
  reaching up to 2229 m cross-track from runway 3's own centreline.

  So ANY low aircraft on ANY of Orly's three runways could win selection as "the aircraft on
  runway 3", and the lowest one won regardless of which runway it was actually using.

  This was reproduced live, not inferred. A 53-poll adsb.fi capture over the real bbox on
  2026-08-27 caught hex 39de4a (TVF12ZW, F-HSXK) being selected at 1050 ft while climbing at
  +2304 ft/min on track 197.67 deg, 750 m off runway 3's centreline - a real DEPARTURE off Orly
  runway 20. A second instance (hex 3964e8, track 198.43, 611 m off centreline, 60 m from runway
  02's published threshold) was caught in an earlier probe. Because 39de4a was climbing hard,
  `runway_config.infer_from_flight()` would also have flipped the panel to "departing" - so the
  false positive corrupted the departure/arrival state as well as the aircraft identity, which
  explains the state-inference half of the original trigger.

  Two secondary defects were found and corrected along the way:
    - runway3.json's own bbox sourcing note asserted the box "is tight enough to exclude the
      crossing 02/20 runway" and called the 06/24 overlap merely "not perfectly exclusive".
      Both claims are false; the real figures are 80.5% and 71.9%.
    - runway3.json described runway 3's 074/254 heading pair as MAGNETIC. OurAirports supplies it
      as degrees TRUE (`le_heading_degT`), and the bearing computed from the two thresholds is
      74.41 TRUE. This matters because the new alignment gate compares against ADS-B `track`
      (true track over ground); the same records' `mag_heading` runs ~4 deg off, and adsb.fi's
      `dir` field is not a heading at all but the bearing from the query centre.
fix: |
  1. GEOMETRY GATE (the actual root-cause fix). `detect.py` now identifies runway 3 from the
     runway's own published threshold coordinates rather than from bbox membership. New helpers
     `runway_axis()`, `along_cross_track_m()`, `track_axis_deviation_deg()` and `corridor_params()`
     derive the centreline (74.41 deg TRUE, 3315 m); `filter_in_geofence()` now tags every record
     with along_track_m / cross_track_m / track_deg / track_deviation_deg / in_corridor /
     track_aligned / on_runway3; `select_runway3_aircraft()` gates candidates on `on_runway3`
     instead of bare bbox membership. Records are still RETURNED on bbox containment, so
     adsb-test/RESULTS.md's Phase 1 "in bbox" counts keep their recorded meaning.

     Both gates are required and neither is redundant - this follows from Orly's real layout:
       - runway 06/24 is only 12.4 deg off runway 3's heading, so a track gate cannot separate it,
         but its surface never comes within 887 m of runway 3's centreline -> the CORRIDOR catches it.
       - runway 02/20 physically crosses runway 3's centreline (min cross-track 0 m at 1601 m
         along), so a corridor gate cannot separate it, but it is 56 deg off runway 3's heading
         -> the TRACK GATE catches it.
     Checks 17 and 18 in the harness assert exactly this complementarity, and fail loudly if a
     future change makes either gate stop being load-bearing.

     Thresholds (in runway3.json's new `corridor` block, with the derivation recorded there) are
     read off measured separation, not guessed: half_width_m=500 sits inside an empty band between
     real runway-3 traffic (<=31 m cross-track, 9 real aircraft) and real wrong-runway traffic
     (>=611 m); axis_tolerance_deg=30 sits inside an empty band between 0.0-0.7 deg and 56 deg.
     extension_m=2500 preserves the bbox's original stated intent.

  2. CROSS-SOURCE VALIDATION (defence-in-depth). `poll_current_aircraft()` no longer stops at the
     first provider that answers - it queries every provider each poll and compares their
     independent selections: agreement -> return it with corroborated=True; only one provider
     produced a selection -> return it with corroborated=None; genuine disagreement -> log both
     and return None, which D-04 already defines as "leave the panel alone". The returned dict
     carries `sources` and `corroborated`. An unreachable provider is deliberately NOT scored as
     disagreement - api.airplanes.live currently answers 403 to this project's User-Agent, so the
     single-source branch is the live one today and suppressing on it would blank the display.

  3. OBSERVABILITY. The selection dict and the CLI line now carry cross_track_m / track_deg /
     track_deviation_deg / sources / corroborated, so a future questionable pick is diagnosable
     from the logged selection alone rather than needing another live capture.
verification: |
  - Full suite green: `bash scripts/run-all-tests.sh` -> "Result: PASS", all 9 harnesses, coverage
    81% (up from 79%, threshold 75). `ruff check .` clean.
  - server/test_plane_detection.py extended 10 -> 22 checks, all passing.
  - REGRESSION TEST PROVEN TO CATCH THE BUG: temporarily restoring the pre-fix candidate gate
    (`below_ceiling` only) makes check 12 fail with the exact real false positive
    (39de4a, cross=-750 m, dev=56.7 deg); restoring the fix returns 22/22.
  - BEFORE/AFTER REPLAY ON REAL DATA: replaying the complete 60-poll live capture
    (adsb.fi over the real bbox, 2026-08-27 ~11:45-12:00 CEST) through both the pre-fix and
    post-fix selection logic ->
      pre-fix : 26 polls selected an aircraft, 6 distinct hex, 1 poll selected a NON-runway-3
                aircraft (poll 3: 39de4a TVF12ZW, cross -750 m, axis deviation 56.7 deg)
      post-fix: 25 polls selected an aircraft, 5 distinct hex, 0 non-runway-3 selections
      false-positive rate 3.8% -> 0.0%; genuine runway-3 detections retained 25/25 (100%).
      Exactly one poll was suppressed and it is exactly the wrong-runway one. The distinct-hex
      sets differ by precisely 39de4a. No false negatives introduced.
  - LIVE END-TO-END with the fixed code: `server/plane/detect.py` selected 392ae6 (AFR25EA) at
    525 ft, cross=+5 m, track 253.59, dev 0.8 deg, reporting `sources=adsbfi corroborated=None`
    and correctly degrading past airplanes.live's 403 rather than suppressing.
  - Regression coverage uses two newly committed fixtures that are real verbatim live captures -
    the actual false positive and its correct counter-example - documented to the standard
    server/fixtures/README.md sets, with no invented field values.
files_changed:
  - server/plane/detect.py (runway-3 geometry gate + per-poll cross-source validation)
  - adsb-test/runway3.json (new `corridor` block; two factual corrections; neighbouring runway geometry)
  - server/test_plane_detection.py (10 -> 22 checks; regression + complementarity + cross-validation)
  - server/fixtures/geofence_wrong_runway_39de4a.json (NEW - real captured false positive)
  - server/fixtures/geofence_runway3_arrival_347288.json (NEW - real captured counter-example)
  - server/fixtures/README.md (provenance for both new fixtures)

## Follow-ups (out of this fix's scope, flagged for the user)

- `.planning/phases/02-plane-view-end-to-end-slice/02-VALIDATION.md` still carries the row
  "Occasional wrong-runway aircraft from the non-exclusive geofence ... Accepted v1 limitation;
  watched for, not fixed", and 02-RESEARCH.md's Pitfall 5 says the same. Both are now out of date,
  and both understate the original overlap. Left untouched because they are completed-phase
  historical artifacts and outside this fix's stated scope.
- api.airplanes.live returns 403 to this project's User-Agent and asks to be contacted at
  contact@airplanes.live. The configured PRIMARY provider is therefore dead in production right
  now and every poll silently runs single-source. Separate issue from this bug, but worth its own
  ticket - the cross-validation added here cannot corroborate anything until it is resolved.
- Residual, documented in runway3.json's `corridor.known_residuals`: an aircraft taxiing on a
  runway-parallel taxiway (~150-200 m offset, runway-aligned track) still passes both gates.
- `runway_config.CLIMB_THRESHOLD_FPM` is still, per its own docstring, never validated against a
  real climbing runway-3 track. The one real climb-out captured in this session (+2304 ft/min) was
  the wrong-runway aircraft, so it does not close that gap.
