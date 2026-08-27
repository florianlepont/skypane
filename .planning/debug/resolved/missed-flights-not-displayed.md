---
status: resolved
trigger: "Je viens de rallumer l'écran et il ne se passe absolument rien. Est-ce que tu peux vérifier que la carte a essayé de communiquer avec le VPS ? / [message suivant, même conversation] Ça a l'air que la tablette vient de se, enfin je veux dire l'écran vient de se mettre à jour, mais là typiquement elle a laissé passer deux autres avions sans afficher, donc soit il y a un problème de consistance dans les données, soit elle met trop de temps à vérifier les données. Est-ce que c'est toujours trente secondes ou est-ce que ça a changé ?"
created: 2026-08-27T00:00:00Z
updated: 2026-08-27T00:00:00Z
---

## Current Focus
<!-- OVERWRITE on each update - always reflects NOW -->

hypothesis: REVISED after reading detect.py + runway3.json in full. The original mechanism (1) "sub-30s transit blind spot" is now largely ELIMINATED on geometry: the corridor is 8315m along-track x 1000m wide, which no real departure or arrival crosses in under 30s. The surviving mechanisms are two consequences of `select_runway3_aircraft()`'s sort key `(effective_altitude_ft, seen_pos, hex)` combined with a corridor wide enough to contain non-runway ground traffic: (2a) MASKING - `effective_altitude_ft()` returns 0.0 for ANY on_ground record, so a taxiing/holding/stationary aircraft inside the 1000m-wide corridor unconditionally outranks the airborne aircraft actually using runway 3, and because its hex does not change, render output is byte-identical and `panel_changed=False` for every subsequent poll; (2b) TIE-BREAK DISAGREEMENT - when 2+ on-ground records tie at exactly 0.0, the winner is decided by `seen_pos`, a per-provider staleness value sampled >=1.1s apart from two different feeder networks, so adsb.fi and adsb.lol can pick different hexes from the same real situation, hitting the disagreement branch and returning None for the whole cycle. A third, independent mechanism not previously considered: (3) DEVICE-SIDE CONSUMPTION RATE - panel.bin is overwritten by the server every time a new hex is selected, but the e-ink device's own wake->fetch->refresh cycle is much longer than 30s, so a flight whose "reign" over panel.bin is shorter than one device cycle is never fetched at all (partially mitigated by D-25's current+previous two-deep layout).
test: DONE. All three mechanisms were tested by executing the real detect.py against positions computed from runway3.json's own threshold coordinates (scratch experiments E1/E2/E3), plus a firmware config audit.
expecting: DONE. (1) eliminated on geometry - corridor dwell 58-110s always exceeds the 30s poll. (2a) confirmed: a departure at 900ft loses to a parked aircraft at 180m offset. (2b) confirmed: poll_current_aircraft() returned None with the disagreement stderr line when only seen_pos differed between feeds. (3) confirmed as a real contributing constraint: 60s panel guard + ~30s blit vs a 30s server render cadence.
next_action: DONE for mechanism A - fix applied, committed and self-verified (full suite green 9/9 harnesses / 215 checks / 82% coverage, ruff and attribution clean, before/after replay over every committed fixture flipping exactly the masking case and nothing else, and the three new checks proven to FAIL when the pre-fix gate is restored). Session filed to .planning/debug/resolved/ per this project's convention. STILL OUTSTANDING and deliberately not blocking this filing: (1) the user has not yet confirmed from their own frame that flights stop being skipped - and they may not, because (2) mechanisms B and C remain open by the user's own scoping and either can still swallow a flight on its own. See "Still open after the mechanism-A fix" below.
reasoning_checkpoint:
  hypothesis: |
    Mechanism A is NARROWER than the diagnosis framed it. The sort key is not the defect and
    effective_altitude_ft()'s 0.0-for-on-ground is not the defect either: an aircraft physically ON
    runway 3 genuinely IS "the aircraft using runway 3", so ranking it below nothing is correct
    (D-P2-01). The defect is that `select_runway3_aircraft()`'s candidate gate (`on_runway3`) applies
    ONE corridor to every record regardless of whether it is airborne. That corridor's dimensions
    (half_width_m=500, extension_m=2500 over a 3315m runway) were derived in the prior
    runway3-false-positive session from AIRBORNE separation only - every measurement behind them is an
    approach or departure track. Applied to an on-ground record it is physically meaningless: it admits
    every taxiway, holding point and apron position within 500m of the centreline and 2.5km beyond
    either threshold. That is exactly the class runway3.json's own `corridor.known_residuals` already
    admits ("~150-200m offset, runway-aligned track ... still passes both gates"), and any such record
    scores effective altitude 0.0 and therefore outranks every real airborne runway-3 movement.
  confirming_evidence:
    - "Direct measurement, this pass: the ONLY real on-ground runway-3 record committed to this repo
       (fixture 3985a7 AFR56XX) sits at along=55.2m, cross=+31.1m. Runway 3's own published paved
       half-width is 22.6m (OurAirports runways.csv row airport_ident=LFPO le_ident=07, width_ft=148 =
       45.1m, downloaded fresh 2026-08-27 this pass). So real runway-3 ground traffic hugs the pavement
       to within ~8m of position error, while the live gate tolerates 500m - a 16x over-admission."
    - "runway3.json's own corridor.known_residuals, written by the prior session, already documents the
       exact admitted class: an aircraft at ~150-200m offset on a runway-aligned track passes both
       gates. That is a documented, self-admitted hole, not a speculative one."
    - "Debug-file experiment E2 (already recorded in Evidence) executed the real detect.py and showed a
       departure climbing through 900ft at +2400fpm LOSING selection to a stationary aircraft at 180m
       offset, both tagged on_runway3=True, both tied at effective altitude 0.0."
    - "Simulated the proposed gate against every existing check's input before editing any code
       (scratch verify_gate.py): at ground_half_width_m=75 the real 3985a7 record still qualifies
       (31.1 <= 75), the whole documented 150/180/200m residual band is rejected, and check 18's
       premise (the 02/20 centreline crossing must stay in_corridor so the check keeps proving the
       TRACK gate is load-bearing) still holds at cross=-0.4m, along=1600.7m."
  falsification_test: |
    If real runway-3 ground traffic were measured beyond ~75m cross-track, the tight ground gate would
    start rejecting genuine runway-3 movements and the hypothesis that a lateral gate fixes this
    without a false-negative cost would be refuted. Measured: the one real on-ground runway-3 record
    available is at 31.1m and the published pavement half-width is 22.6m, versus a documented residual
    starting at 150m - an empty measured band from 31m to 150m. Not refuted. Second falsifier: if the
    masking record were rejected by the PRE-EXISTING airborne corridor rather than the new ground gate,
    the regression check would pass for the wrong reason - check 29 asserts |cross|=180 <= the airborne
    half_width_m of 500 explicitly, so it fails loudly if that ever stops being true.
  fix_rationale: |
    Addresses the root cause (a geometric gate calibrated on airborne data being applied to ground
    records) rather than the symptom (the sort picking the wrong winner). Deliberately does NOT touch
    effective_altitude_ft() or the sort key: an aircraft genuinely on runway 3's pavement SHOULD win
    over one 900ft above it, and changing that would break D-P2-01 for the correct case. Reuses the
    prior session's machinery verbatim - along_cross_track_m(), corridor_params(), the in_corridor /
    track_aligned / on_runway3 tagging - adding exactly one config number rather than a parallel
    mechanism. That number is used symmetrically for the lateral half-width and the along-track margin
    beyond each threshold, so the ground gate is one concept ("within X of the runway's paved
    rectangle"), not two tunables.
  blind_spots:
    - "Only ONE real on-ground runway-3 record exists in this repo (3985a7, +31.1m), so the lower bound
       of the empty band rests on a single sample plus the published 22.6m pavement half-width. A
       second real ground capture could move it."
    - "The masking aircraft in the new fixture is DERIVED, not captured: no live capture of an actual
       masking event exists. Its position is computed from runway3.json's published thresholds at the
       180m offset runway3.json's own known_residuals documents (the same construction the diagnosis's
       E2 experiment used). Its record fields are the real 3985a7 on-ground capture's."
    - "The ICAO Annex 14 runway-to-parallel-taxiway separation standard would have grounded the 180m
       offset in a published figure; a web search this pass did NOT confirm the number, so it is
       deliberately NOT cited and the offset rests on runway3.json's own documented residual band."
    - "Mechanisms B and C are untouched by explicit user scoping, so a two-source seen_pos disagreement
       or a device that cannot consume panels fast enough can still swallow a flight. This fix cannot
       be verified as closing the user's original symptom end-to-end, only as closing A."
    - "Not correlated against live VPS logs for the two aircraft observed on 2026-08-27 - no VPS access
       in this session, same constraint the diagnosis pass recorded."
tdd_checkpoint: null

## Symptoms
<!-- Written during gathering, then immutable -->

expected: The panel should faithfully reflect real runway-3 traffic - any real aircraft (departure or arrival) that transits the geofence should appear on the display at some point during its transit.
actual: The screen did update on its own (ruling out a dead/unresponsive device), but the user reports two other aircraft passed without ever being shown on the display.
errors: None visible to the user - no crash, no on-screen fault indicator, silent behavior.
reproduction: Observed during normal live operation, not a controlled/scripted repro. User's own hypothesis: either a data-consistency problem between sources, or the poll taking too long relative to how fast a flight transits - directly asked whether the poll interval is still 30 seconds.
started: Today, 2026-08-27, live observation on the real OVH deployment.

## Additional scope (from conversation, not a classic symptom field)

The user's first message ("rallumer l'écran, rien ne se passe") described what looked like a fully blank/dead display and asked to check VPS communication logs. Before that could be checked (no VPS SSH access available in this session - the real host/IP was deliberately scrubbed from git during the Phase 4 compliance pass, see `deploy/README.md`, and is not present in this machine's `~/.ssh/config`), the user's own follow-up message clarified the actual live symptom: the screen did update, so the initial "nothing happens" read was the display simply not having refreshed yet, not a dead device. The real, current concern is the two skipped aircraft and the poll cadence question.

## Eliminated
<!-- APPEND only - prevents re-investigating after /clear -->

- hypothesis: Device is not communicating with the VPS at all (dead device / connectivity failure).
  reasoning: The user directly reported the screen did update on its own during this same session, which requires a successful device -> VPS poll -> render -> fetch -> panel-refresh cycle to have completed. This rules out a full communication failure as the explanation for the current symptom (two missed flights); the initial "nothing happens" report preceded the update and is superseded.

- hypothesis: The 30s poll interval is too slow - a real aircraft transits the runway-3 corridor in
    under 30s and falls entirely between two consecutive polls (the user's own stated theory, "elle met
    trop de temps a verifier les donnees").
  evidence: Computed from the real adsb-test/runway3.json corridor and detect.py's own runway_axis():
    the corridor is 8315m along-track x 1000m wide. Realistic dwell is ~84s for a departure, ~110s for
    an arrival, and ~58s even for a departure truncated the instant a SID turn breaks the 30 deg track
    gate. A window that always exceeds the sample period cannot be missed by sampling alone - every
    movement gets 2-3 poll opportunities. Shortening the poll interval would not change the outcome.
    (Separate but important: the REAL sampling limit is the providers' own position-update cadence,
    measured in adsb-test/RESULTS.md at 36.2s median / 56.7s max for adsb.fi - slower than our poll -
    so polling faster only re-reads the same stale record.)
  timestamp: 2026-08-27T00:00:00Z

## Evidence
<!-- APPEND only - facts discovered during investigation -->

- timestamp: 2026-08-27T00:00:00Z
  checked: deploy/skypane-poll.timer, deploy/skypane-poll.service
  found: |
    OnBootSec=30s / OnUnitActiveSec=30s / AccuracySec=1s - the server-side detect->infer->enrich->render
    cycle (server/poll_loop.py --once) is still triggered every 30 seconds, tightened against systemd's
    default minute-scale jitter.
  implication: Confirms (from the deployment config in-repo) that the server's own poll cadence has not
    changed from 30s. Does not by itself confirm the live VPS's actual running config matches this file
    (would need deploy.sh's last-applied state or a live `systemctl` check for that).
- timestamp: 2026-08-27T00:00:00Z
  checked: deploy/skypane.env.example
  found: |
    SKYPANE_SLEEP_S=30 - "sleep_s handed to the frame in every /device/v1/display response - how long
    the device sleeps between polls. Matches the 30s poll_loop.py cadence... a much larger sleep_s here
    would leave the frame polling far less often than the server refreshes."
  implication: By design, the device's own wake/poll interval is meant to match the server's 30s render
    cadence. The template default is 30s; the real, gitignored skypane.env on the VPS could in principle
    have been hand-edited to something else, which is not verifiable without VPS access.
- timestamp: 2026-08-27T00:00:00Z
  checked: .planning/STATE.md (session note dated 2026-08-26)
  found: |
    "Device wake interval (sleep_s...) is currently 30s on the live OVH deployment (skypane.env's
    SKYPANE_SLEEP_S=30, verified directly on the VPS 2026-08-26)... NOT yet a tuned production value,
    this is the bring-up/test default... tune this once actual battery-life data exists, not before."
  implication: As of the last direct VPS verification (2026-08-26, the day before this session), the
    live deployed value was confirmed 30s and explicitly flagged as an untuned bring-up default, not a
    value chosen for departure-detection completeness. Directly answers the user's question: yes, still
    30 seconds, as of the last check - assuming nobody changed it by hand since.
- timestamp: 2026-08-27T00:00:00Z
  checked: ARCHITECTURE.md's "Server render pipeline" section
  found: |
    "When more than one aircraft is inside the geofence in the same poll, select_runway3_aircraft()
    picks exactly one... When the two sources name different aircraft, the poll returns nothing for
    that cycle, which the pipeline already treats as the between-flights hold rather than an error."
    Also: no in-process memory between poll_loop.py invocations other than state/poll_state.json: the
    pipeline is a per-cycle snapshot selector, not a queue or log of every aircraft seen.
  implication: Confirms both candidate mechanisms in the current hypothesis are real, designed, existing
    behaviors (not speculation): (a) single-snapshot-per-cycle selection with no history/queue, and
    (b) a genuine two-source disagreement silently yields "nothing" for that cycle by design (D-04).
    Either is independently sufficient to explain "a real aircraft passed and was never shown."
- timestamp: 2026-08-27T00:00:00Z
  checked: .planning/debug/resolved/runway3-false-positive.md (prior resolved debug session, same subsystem)
  found: |
    Confirms `poll_current_aircraft()` queries every configured provider each cycle and: agreement ->
    corroborated=True; only one provider answers -> corroborated=None (still returned); genuine
    disagreement -> logs both and returns None ("leave the panel alone" per D-04). Also confirms
    adsb.fi and adsb.lol are the two live default providers as of 2026-08-27 (airplanes.live demoted
    to opt-in-only after losing free API access).
  implication: The disagreement-suppression path is real, current, and was itself exercised/observed
    live in a prior session (for a different symptom - wrong-runway selection - but the same code path).
    Strengthens hypothesis (2) as plausible without yet proving it caused this specific incident.
- timestamp: 2026-08-27T00:00:00Z
  checked: adsb-test/runway3.json corridor block + server/plane/detect.py runway_axis(), executed
    against the real config (scratch experiment E1)
  found: |
    Corridor is 8315m along-track (3315m runway + 2500m beyond EACH threshold) x 1000m wide
    (half_width_m=500), ceiling 3000ft, axis tolerance 30 deg. Computed dwell for a real movement:
    departure 5815m = ~84s (38s takeoff roll + 46s to corridor exit at 160kt); arrival 5815m = ~110s
    (35s final + 76s rollout). Even truncating a departure the instant a SID turn exceeds the 30 deg
    track gate gives ~58s.
  implication: ELIMINATES the original "sub-30s transit" hypothesis on geometry. Every realistic
    runway-3 movement is inside the corridor for 58-110s, i.e. ALWAYS longer than the 30s poll period,
    which guarantees at least one and normally 2-3 sampling opportunities. The 30s poll interval the
    user asked about is NOT the limiting factor and shortening it would not fix this.
- timestamp: 2026-08-27T00:00:00Z
  checked: adsb-test/RESULTS.md per-provider metrics table (real ~92-min live capture at THIS geofence)
  found: |
    Median reconstructed position-update gap for the best-tracked aircraft: 36.2s (adsb.fi), 22.4s
    (airplanes.live). Max gap 56.7s / 69.8s. These are derived from each provider's own seen_pos field
    - "seconds since the underlying feed last received a real position report" - not from the sampler's
    own interval. Both providers FAILED the pre-committed <=15s cadence threshold.
  implication: The real sampling limit is the PROVIDER's refresh cadence (~36s median, up to 57s), not
    this project's 30s poll. Against a ~58s worst-case aligned window a departure may be represented by
    as few as one position report. Also establishes that seen_pos is a per-feeder-network staleness
    value that routinely differs by tens of seconds between the two default providers - which is exactly
    the field select_runway3_aircraft() uses as its tie-break.
- timestamp: 2026-08-27T00:00:00Z
  checked: server/plane/detect.py effective_altitude_ft() + select_runway3_aircraft() sort key, executed
    against real runway geometry (scratch experiment E2)
  found: |
    effective_altitude_ft() returns 0.0 for ANY on_ground record. Placing a departure mid-takeoff-roll
    on the centreline and a second aircraft holding on a runway-parallel taxiway at 180m offset (a case
    runway3.json's own corridor.known_residuals admits passes both gates): both tag on_runway3=True and
    both tie at effective altitude exactly 0.0. Advancing the departure to 900ft climbing at +2400fpm,
    select_runway3_aircraft() picks the STATIONARY queue aircraft (eff_alt 0.0 < 900.0).
  implication: MECHANISM A (masking) confirmed in code. The aircraft actually using runway 3 loses the
    selection to any parked/taxiing aircraft inside the 1000m-wide corridor. Because that ground
    aircraft's hex does not change between polls, and render.py's panel text depends only on
    callsign/state/route/aircraft_type (verified: no altitude, position, or timestamp is drawn, and
    render.py imports no time/random), the rendered bytes are identical every cycle ->
    write_panel_atomic() returns False -> panel_changed=False -> the panel is FROZEN for as long as
    that ground aircraft sits in the corridor.
- timestamp: 2026-08-27T00:00:00Z
  checked: server/plane/detect.py poll_current_aircraft() driven end-to-end through its query_provider
    seam with two provider responses differing ONLY in seen_pos (scratch experiment E3)
  found: |
    Same two real on-ground aircraft, same instant, same positions. adsb.fi seen_pos DEP=2.1/QUE=18.6
    -> selects DEP; adsb.lol seen_pos DEP=24.3/QUE=3.4 -> selects QUE. poll_current_aircraft() returned
    None and emitted "detect: providers disagree on the runway-3 aircraft (adsbfi=DEP001,
    adsblol=QUE002) - treating as doubt, selecting nothing this poll". Control with identical seen_pos
    ordering on both feeds returned hex=DEP001 corroborated=True.
  implication: MECHANISM B (disagreement suppression) confirmed in code. When 2+ on-ground records tie
    at 0.0 the winner is decided ENTIRELY by seen_pos - the single least provider-stable field in the
    record, measured above as differing by tens of seconds between feeds, and read >=1.1s apart because
    of MIN_SECONDS_BETWEEN_CALLS. The difference between a displayed flight and a silently discarded
    cycle is a staleness metric, not anything about the aircraft. poll_loop then takes the D-04 branch:
    panel held, nothing shown.
- timestamp: 2026-08-27T00:00:00Z
  checked: firmware/main/Kconfig.projbuild, firmware/main/panel.c, firmware/sdkconfig.defaults,
    firmware/sdkconfig.ee02.defaults, deploy/skypane.env.example
  found: |
    CONFIG_FP_MIN_REFRESH_SPACING_S default 60, CONFIG_FP_MAX_GUARD_WAIT_S default 90. Verified NEITHER
    is overridden in sdkconfig.defaults or sdkconfig.ee02.defaults, so the Kconfig defaults apply.
    fp_panel_draw() resets s_guard_remaining_s to 60 after every successful blit; a wake that finds a
    new image waits out the remaining guard (up to the 90s budget) before blitting, and a 13.3" Spectra 6
    full refresh itself takes tens of seconds. Device sleep_s=30.
  implication: MECHANISM C (device consumption rate), not previously considered. The device's floor
    between two DRAWN images is ~60s guard + blit (~30s) = ~90s, while the server rewrites panel.bin
    every 30s. panel.bin can advance through 2-3 different flights per device draw. D-25's
    current+previous two-deep layout absorbs exactly ONE skipped flight; a third selection inside one
    device cycle is lost outright. Critically this mechanism is INVISIBLE in skypane-poll's log - the
    server would look completely healthy while flights are still never seen.
- timestamp: 2026-08-27T00:00:00Z
  checked: observability audit - deploy/skypane-poll.service, poll_loop.py's log statement,
    stub-server/byos_server.py log_message()/log_telemetry()
  found: |
    detect.py's disagreement line goes to stderr; skypane-poll.service sets no StandardError= override,
    so journald captures it and it names BOTH hexes - mechanism B is distinguishable from logs.
    poll_loop's single log line prints hex/callsign/corroborated/panel_changed, so mechanism A shows up
    as a constant hex with panel_changed=False across consecutive polls - but select_runway3_aircraft()
    DISCARDS the candidate list, so the losing candidates are never logged and "the right aircraft was
    present and lost the sort" cannot be proven. byos_server logs every GET /device/v1/display plus
    telemetry, so device fetch times are recoverable for mechanism C.
    NOTE: when flight is None, poll_loop prints hex=None corroborated=None state_source=held
    panel_changed=False - byte-identical to a genuine "nothing in the corridor" cycle. The poll_loop
    line ALONE cannot distinguish suppression from an empty sky; only detect.py's stderr line can.
  implication: The highest-value instrumentation gap is that the candidate set is thrown away. Logging
    per-provider candidates (hex, eff_alt, cross_track_m, on_ground) - or even just the count and the
    runner-up - would make A and B unambiguous on the next occurrence without live observation.

- timestamp: 2026-08-27T00:00:00Z
  checked: FIX PASS. OurAirports runways.csv re-downloaded fresh
    (https://davidmegginson.github.io/ourairports-data/runways.csv), row airport_ident=LFPO
    le_ident=07 he_ident=25, plus the along/cross-track measurement of every committed geofence fixture
    through the real detect.along_cross_track_m().
  found: |
    Runway 3's published paved WIDTH is width_ft=148 = 45.11m, i.e. a half-width of 22.6m from the
    centreline. (Same row already used for the thresholds; length_ft=10892 and the le/he coordinates
    match runway3.json byte-for-byte, so the row's identity is confirmed.) Measured cross-track of the
    only real ON-GROUND runway-3 record committed to this repo, fixture 3985a7 AFR56XX: along=55.2m,
    cross=+31.1m - about 8.5m of ADS-B position error beyond the pavement edge. The live gate at the
    time tolerated 500m laterally and 2500m beyond each threshold, for ALL records regardless of
    whether they were airborne.
  implication: |
    Narrows mechanism A to a single specific defect and gives it a measured empty band. Real runway-3
    GROUND traffic hugs the pavement (<=31m observed, 22.6m published half-width); the gate admitted
    16x that. Every number behind half_width_m=500 / extension_m=2500 in the prior session's
    derivation is an AIRBORNE approach or departure measurement - they were never calibrated for
    ground records and are physically meaningless when applied to one. Upper bound of the empty band
    is the ~150m near edge of the residual runway3.json's own corridor.known_residuals already
    documented. 31m -> 150m is empty; ground_half_width_m=75 sits in it.
- timestamp: 2026-08-27T00:00:00Z
  checked: FIX PASS. Simulated the proposed on-ground pavement gate against every existing check's
    input BEFORE editing any code (scratch verify_gate.py), at candidate thresholds 50/75/100/120m.
  found: |
    At every candidate threshold: real 3985a7 (along 55.2, cross 31.1) accepted; the entire documented
    150/180/200m residual band rejected; and - critically - check 18's premise still holds, i.e. the
    real 02/20 centreline crossing point (along 1600.7, cross -0.4, alt_baro "ground") stays
    in_corridor=True so that check keeps proving the TRACK gate is the load-bearing one there. Check
    17's two 06/24 thresholds both fall outside the coarse bbox and hit its `continue` branch, so they
    are unaffected either way. test_poll_loop.py's synthetic snapshot is airborne (alt_baro 450), so it
    never reaches the ground branch.
  implication: The gate could be added without breaking any existing regression coverage, and the
    threshold choice was not load-bearing across a 50-120m range - so 75 was chosen for margin
    (2.4x above the largest real measurement, 2x below the nearest documented residual) rather than to
    make anything pass.
- timestamp: 2026-08-27T00:00:00Z
  checked: FIX PASS. Post-fix verification - full suite, a pre-fix/post-fix replay of every committed
    geofence fixture, and the harness re-run with the pre-fix gate monkeypatched back in.
  found: |
    Full suite green: 9/9 harnesses, 215 checks, coverage 82% (up from 81%, threshold 75), ruff clean,
    check-attribution.sh clean. server/test_plane_detection.py 28 -> 31 checks.
    Before/after replay across all 6 committed geofence fixtures: EXACTLY ONE selection changed -
    geofence_taxiway_masking.json flipped from "3985a7 AFR56XX alt=0.0 cross=180" to
    "347288 IBE05DP alt=775.0 cross=3". Every other fixture selects identically pre- and post-fix,
    including geofence_on_ground.json which still selects the real on-ground runway-3 aircraft.
    Restoring the pre-fix gate (corridor_params monkeypatched so ground==air) fails exactly checks
    29, 30 and 31 and nothing else, 28/31.
  implication: The fix changes precisely the masking case and nothing else - no genuine runway-3
    detection is lost, and the new checks are proven to fail without the fix rather than merely
    passing with it.

## Resolution
<!-- OVERWRITE as understanding evolves -->

root_cause: |
  PRIMARY (code-confirmed, one defect with two faces): `select_runway3_aircraft()`'s primary sort key
  is degenerate for exactly the traffic it is meant to rank. `effective_altitude_ft()` maps EVERY
  `on_ground` record to the single value 0.0, and the corridor is +/-500m wide over 8315m - wide enough
  to contain runway-parallel taxiway traffic, which runway3.json's own `corridor.known_residuals`
  already admits ("~150-200m offset, runway-aligned track ... still passes both gates"). During any
  real runway movement there is normally more than one on-ground aircraft inside that corridor, so
  "lowest altitude wins" stops discriminating and the decision falls through to the `seen_pos`
  tie-break - a per-provider staleness value, measured in adsb-test/RESULTS.md as differing by tens of
  seconds between the two default feeds, and read >=1.1s apart because of MIN_SECONDS_BETWEEN_CALLS.
  Two consequences, both reproduced against the real code:
    A. MASKING - a stationary or taxiing aircraft outranks the aircraft actually using runway 3 (a
       departure climbing through 900ft at +2400fpm loses to a parked aircraft at 180m offset). Its
       hex never changes; render.py draws only callsign/state/route/aircraft_type, so the bytes are
       identical each cycle -> panel_changed=False -> the panel is frozen while real traffic passes.
    B. DISAGREEMENT SUPPRESSION - when the on-ground records tie at 0.0, adsb.fi and adsb.lol order
       them by their own seen_pos, pick different hexes, and hit poll_current_aircraft()'s
       disagreement branch, which returns None for the entire cycle. poll_loop then takes the D-04
       "hold the panel" branch. Nothing is displayed and nothing looks wrong.
  From the user's chair A and B are indistinguishable - in both cases the panel simply goes stale.

  CONTRIBUTING (independent, and invisible in server logs): the device cannot consume panels as fast
  as the server produces them. CONFIG_FP_MIN_REFRESH_SPACING_S defaults to 60 and is not overridden in
  any committed sdkconfig, so fp_panel_draw() re-arms a 60s guard after every blit; with sleep_s=30 and
  a 13.3" Spectra 6 full refresh taking tens of seconds, the floor between two DRAWN images is ~90s
  while the server rewrites panel.bin every 30s. D-25's current+previous layout absorbs exactly one
  skipped flight; a third selection inside one device cycle is lost outright.

  ELIMINATED: the user's own theory that the 30s poll is too slow. Corridor dwell is 58-110s for every
  realistic movement, always longer than the poll period. Answer to the direct question: yes, still 30s
  (deploy/skypane-poll.timer OnUnitActiveSec=30s, SKYPANE_SLEEP_S=30, VPS-verified 2026-08-26 per
  STATE.md) - but that number is not the problem, and lowering it would not help, because the
  providers' own data only refreshes every ~36s (median, adsb.fi; 56.7s max).

fix: |
  SCOPE: MECHANISM A ONLY. The user was shown all three mechanisms and explicitly approved only the
  masking fix this pass. MECHANISM B (disagreement suppression via the seen_pos tie-break in
  poll_current_aircraft()) and MECHANISM C (device panel-refresh guard vs server render cadence,
  CONFIG_FP_MIN_REFRESH_SPACING_S) are UNTOUCHED and REMAIN OPEN by that explicit scoping. The
  observability gap (select_runway3_aircraft() discarding the candidate set) is also untouched by the
  same scoping. This fix therefore cannot be claimed to close the user's original symptom end to end -
  only to close A.

  WHAT THE DEFECT TURNED OUT TO BE - narrower than the diagnosis framed it. Neither the D-P2-01 sort
  key nor effective_altitude_ft()'s 0.0-for-on-ground is wrong, and both were deliberately left alone:
  an aircraft physically on runway 3's pavement genuinely IS the aircraft using runway 3, so ranking it
  below an airborne one would break D-P2-01 for the correct case. The actual defect is that the
  candidate gate (`on_runway3`) applied ONE corridor to every record regardless of whether it was
  airborne. Every measurement behind that corridor's dimensions (half_width_m=500, extension_m=2500
  over a 3315m runway) is an AIRBORNE approach or departure track from the prior runway3-false-positive
  session. Applied to a record already on the ground it is physically meaningless - a 1000m x 8315m box
  around a 45m-wide runway contains taxiways, holding points and aprons - and since every on-ground
  record scores effective altitude exactly 0.0, any one of them outranked every real airborne runway-3
  movement, froze the panel on an aircraft that was not going anywhere, and let real traffic pass
  unseen. This is the same lesson as the prior session, a second time: the gate was wrong, not the
  ranking.

  THE CHANGE. One new config number, `corridor.ground_half_width_m = 75`, and one branch in
  `filter_in_geofence()`: an `on_ground` record must now be on runway 3's PAVEMENT - within
  ground_half_width_m of the paved rectangle, i.e. |cross_track| <= 75m AND along-track within
  [-75, length+75]. The same figure is reused for both bounds deliberately, so the gate is one concept
  ("within 75m of runway 3's paved rectangle") rather than two tunables. Airborne records are entirely
  unchanged: half_width_m stays 500 and extension_m stays 2500, because the prior session's evidence
  that tightening below ~150m would start rejecting genuine APPROACH traffic is still correct - it just
  does not apply to an aircraft that is already on the ground, which is on the pavement by definition.
  The track gate is unchanged and applies to both. This reuses the prior session's machinery verbatim
  (runway_axis, along_cross_track_m, corridor_params, the in_corridor / track_aligned / on_runway3
  tagging) rather than adding a parallel mechanism; corridor_params() now returns a 4-tuple.

  THRESHOLD DERIVATION - read off measured separation, in the prior session's style, not guessed.
  Lower bound: runway 3's own published paved width is 148ft = 45.1m, i.e. a 22.6m half-width
  (OurAirports runways.csv `width_ft`, LFPO 07/25 row - the same row the thresholds come from,
  re-downloaded this pass), and the only real on-ground runway-3 record in server/fixtures (3985a7
  AFR56XX) measures +31.1m cross-track. Upper bound: the residual this closes starts at ~150m, per
  runway3.json's own pre-existing corridor.known_residuals. 75 sits inside that empty 31m-150m band -
  2.4x above the largest real measurement, 2x below the nearest documented residual, 3.3x the published
  pavement half-width. runway3.json's new `corridor.ground_gate_derivation` records all of this in
  place, and `runway.width_m` / `width_source` record the published width it leans on.

  RESIDUAL OPENED BY THIS FIX, recorded in runway3.json's known_residuals as item (3): two aircraft
  BOTH genuinely on runway 3's pavement in the same poll (one rolling out toward 25 while another lines
  up on 07) still both score 0.0 and fall through to the seen_pos tie-break. Both are legitimately "on
  runway 3" so either is defensible to display, but the two feeds can order them differently and hit
  the mechanism-B disagreement branch - which is out of scope this pass.

verification: |
  - FULL SUITE GREEN: `bash scripts/run-all-tests.sh` -> "Result: PASS", all 9 harnesses, 215 checks,
    coverage 82% (up from 81%, threshold 75 in pyproject.toml). `server/.venv/bin/ruff check .` ->
    "All checks passed!". `bash scripts/check-attribution.sh` -> PASS.
  - server/test_plane_detection.py extended 28 -> 31 checks, all passing.
  - REGRESSION TESTS PROVEN TO CATCH THE BUG, not merely to pass with the fix: monkeypatching
    corridor_params() so on-ground records inherit the airborne corridor again (the pre-fix behaviour)
    fails EXACTLY checks 29, 30 and 31 and nothing else -> 28/31, exit 1. Restoring the fix -> 31/31.
  - BEFORE/AFTER REPLAY over all six committed geofence fixtures, through the pre-fix and post-fix
    selection logic: EXACTLY ONE selection changed. geofence_taxiway_masking.json flipped from
    "3985a7 AFR56XX alt=0.0 cross=180m" (the taxiing masker) to "347288 IBE05DP alt=775.0 cross=+3m"
    (the real runway-3 arrival). Every other fixture - including geofence_on_ground.json, whose real
    on-ground runway-3 aircraft must keep winning - selects identically pre- and post-fix. No genuine
    runway-3 detection was lost.
  - PRE-IMPLEMENTATION SIMULATION: the gate was evaluated against every existing check's input before
    any code was edited, at 50/75/100/120m, confirming check 18's premise (the 02/20 crossing must stay
    in_corridor so that check keeps proving the TRACK gate is load-bearing there) survives.
  - The new fixture's masking record is deliberately constructed so it is rejected ONLY by the new
    ground gate: check 29 asserts it is in-bbox, below-ceiling, track-aligned AND that its |cross| of
    180m sits strictly between ground_half_width_m and half_width_m, so check 30 cannot pass for the
    wrong reason. This mirrors check 11's role for the prior session.
  - LIVE END-TO-END: `server/plane/detect.py --provider adsbfi` ran clean against the real endpoint
    (exit 0, no stderr, "no aircraft in the runway-3 geofence"), confirming the 4-tuple corridor_params
    change works on the real path. CAVEAT: adsb.fi returned 0 raw records at that moment - an empty
    sky - so this run exercised the code path but NOT the gate. Unlike the prior session there is no
    live capture of the fixed gate accepting real traffic.
  - NOT VERIFIED: not correlated against live VPS logs for the two aircraft the user watched pass on
    2026-08-27 (no VPS access this session, same constraint as the diagnosis pass), and no live capture
    of a real masking event exists - the fixture's masking position is derived from runway3.json's own
    published thresholds at its own documented residual offset, not captured.

files_changed:
  - server/plane/detect.py (on-ground pavement gate in filter_in_geofence; corridor_params returns a
    4-tuple; DEFAULT_GROUND_HALF_WIDTH_M; docstrings recording why the sort was deliberately NOT
    touched)
  - adsb-test/runway3.json (new corridor.ground_half_width_m + ground_gate_derivation; known_residuals
    item 2 marked CLOSED and item 3 opened; runway.width_m / width_source from OurAirports width_ft;
    corridor.source and threshold_derivation clarified as airborne-only)
  - server/test_plane_detection.py (28 -> 31 checks: precondition, regression, empty-band)
  - server/fixtures/geofence_taxiway_masking.json (NEW - real arrival record verbatim + real on-ground
    record fields at a position derived from the published thresholds)
  - server/fixtures/README.md (provenance, with the real/derived split spelled out field by field)

## Still open after the mechanism-A fix (2026-08-27)

This session is filed as resolved because the fix it was scoped to is applied and verified. It is NOT
a claim that the user's original symptom is gone. Two of the three reproduced mechanisms were left
untouched by the user's explicit scoping, and either is independently sufficient to make a real flight
never appear on the frame:

- MECHANISM B - DISAGREEMENT SUPPRESSION (open). `poll_current_aircraft()` returns None for the whole
  cycle when adsb.fi and adsb.lol name different aircraft, and when candidates tie on effective
  altitude the arbiter is `seen_pos`, a per-provider staleness value measured in adsb-test/RESULTS.md
  as differing by tens of seconds between feeds. The mechanism-A fix REDUCES how often that tie occurs
  (far fewer on-ground candidates now qualify) but does not remove it - runway3.json's new
  known_residuals item (3) records the surviving case of two aircraft both genuinely on the pavement.
- MECHANISM C - DEVICE CONSUMPTION RATE (open, and invisible in server logs).
  CONFIG_FP_MIN_REFRESH_SPACING_S defaults to 60 with no override in any committed sdkconfig, so the
  floor between two DRAWN images is ~90s against a 30s server render cadence. panel.bin can advance
  through 2-3 flights per device draw; D-25's current+previous layout absorbs exactly one.
- OBSERVABILITY (open). `select_runway3_aircraft()` still discards the candidate list, so "the right
  aircraft was present and lost the sort" remains unprovable from logs. Worth closing before the next
  occurrence - see "Next occurrence" below, which is unchanged and still applies.

Recommended next step if the user still sees flights skipped: do NOT re-investigate A. Read
`journalctl -u skypane-poll | grep "providers disagree"` first - that line names both hexes and
separates B immediately.

## Unconfirmed without live data

- Which mechanism (A, B, or C) actually fired for the two aircraft the user watched pass.
- Whether Orly 07/25 was the active runway at that moment, and whether ground traffic was in fact
  present in the corridor. The E2/E3 scenarios are geometrically real and use runway3.json's own
  admitted residual, but the specific occupancy is reconstructed, not observed.
- Whether the live VPS still runs the in-repo timer/env values (last VPS-verified 2026-08-26).
- The flashed firmware's actual CONFIG values: `firmware/sdkconfig` is generated at build time and is
  not committed, so a menuconfig change to MIN_REFRESH_SPACING_S would not be visible in this repo.
- The real e-ink blit duration on this hardware (assumed "tens of seconds" from panel.c's comments).

## Next occurrence - how to tell the mechanisms apart

- `journalctl -u skypane-poll | grep "providers disagree"` -> mechanism B, names both hexes.
- `journalctl -u skypane-poll | grep poll_loop` -> a constant `hex=` with `panel_changed=False` across
  many consecutive polls -> mechanism A. NOTE a suppressed cycle logs `hex=None ... panel_changed=False`,
  byte-identical to a genuinely empty sky; only the stderr line above separates the two.
- `journalctl -u skypane-byos` -> `GET /device/v1/display` timestamps; if panel_changed=True events
  outpace device fetches, mechanism C.
- OBSERVABILITY GAP worth closing first: select_runway3_aircraft() discards the candidate list, so
  "the right aircraft was present and lost the sort" is currently unprovable from logs. Logging the
  per-provider candidate set (hex, eff_alt, cross_track_m, on_ground) - or just the count and the
  runner-up - would make A and B unambiguous next time without anyone having to be watching the sky.
