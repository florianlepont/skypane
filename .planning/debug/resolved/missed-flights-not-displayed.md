---
status: resolved
trigger: "Je viens de rallumer l'écran et il ne se passe absolument rien. Est-ce que tu peux vérifier que la carte a essayé de communiquer avec le VPS ? / [message suivant, même conversation] Ça a l'air que la tablette vient de se, enfin je veux dire l'écran vient de se mettre à jour, mais là typiquement elle a laissé passer deux autres avions sans afficher, donc soit il y a un problème de consistance dans les données, soit elle met trop de temps à vérifier les données. Est-ce que c'est toujours trente secondes ou est-ce que ça a changé ?"
created: 2026-08-27T00:00:00Z
updated: 2026-08-28T00:00:00Z
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

REOPENED late 2026-08-27, landed 2026-08-28 (second pass) for MECHANISM B, which the user has now
explicitly approved - the session clock rolled over mid-pass, so the B section below is dated 08-28
while the A record above it stays 08-27. Everything
above this line is the MECHANISM A record and is deliberately left untouched. The live focus, hypothesis
and reasoning_checkpoint for the B pass are in the "Mechanism B fix (2026-08-27, second pass)" section at
the bottom of this file. Mechanism C remains UNAPPROVED and untouched.

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

## Still open after the mechanism-A fix (2026-08-27, statuses updated 2026-08-28)

This session is filed as resolved because the fix it was scoped to is applied and verified. It is NOT
a claim that the user's original symptom is gone. Two of the three reproduced mechanisms were left
untouched by the user's explicit scoping, and either is independently sufficient to make a real flight
never appear on the frame:

- MECHANISM B - DISAGREEMENT SUPPRESSION. **FIXED 2026-08-28 by the second pass; see "Mechanism B fix"
  below.** As written on 2026-08-27 this read: "(open). `poll_current_aircraft()` returns None for the
  whole cycle when adsb.fi and adsb.lol name different aircraft, and when candidates tie on effective
  altitude the arbiter is `seen_pos`, a per-provider staleness value measured in adsb-test/RESULTS.md
  as differing by tens of seconds between feeds. The mechanism-A fix REDUCES how often that tie occurs
  (far fewer on-ground candidates now qualify) but does not remove it - runway3.json's new
  known_residuals item (3) records the surviving case of two aircraft both genuinely on the pavement."
  That diagnosis was correct as far as it went but INCOMPLETE: the second pass found the seen_pos
  tie-break was only half of B. The other half was that corroboration compared each feed's final PICK
  rather than its candidate SET, so the two feeds could disagree - and suppress the cycle - even under a
  perfectly stable tie-break, simply because one had not received an aircraft the other had. Fixing only
  the tie-break would have reduced the symptom's frequency while leaving it open and looking closed.
  Both halves are now fixed. What did NOT change: genuine disagreement still suppresses (D-04 intact).
  What is newly open: runway3.json known_residuals (4) stale records are no longer deprioritised, and
  (5) two feeds carrying the SAME wrong record are still undetectable - the latter being a permanent
  limit of cross-source corroboration rather than anything this pass introduced.
- MECHANISM C - DEVICE CONSUMPTION RATE (open, and invisible in server logs).
  CONFIG_FP_MIN_REFRESH_SPACING_S defaults to 60 with no override in any committed sdkconfig, so the
  floor between two DRAWN images is ~90s against a 30s server render cadence. panel.bin can advance
  through 2-3 flights per device draw; D-25's current+previous layout absorbs exactly one.
- OBSERVABILITY (still mostly open, one slice closed 2026-08-28). The mechanism-B pass extracted
  `runway3_candidates()`, so the candidate list now exists as a named thing, and the disagreement stderr
  line prints each feed's FULL candidate set instead of only its winner (pinned by check 37). That makes
  a suppressed cycle fully diagnosable. But the SUCCESSFUL path still logs only the winner: on a normal
  poll the losing candidates are still discarded, so "the right aircraft was present and lost the sort"
  remains unprovable from logs. Deliberately not extended further this pass - it is a separate change
  from mechanism B and was not part of what the user approved.

Recommended next step if the user still sees flights skipped: do NOT re-investigate A or B; both are
fixed and covered by regression checks that are proven to fail against the pre-fix code. Read
`journalctl -u skypane-poll | grep "providers disagree"` first. If that line appears at all now, it is
a GENUINE cross-source disagreement (each feed's full candidate set is printed on it), not the
manufactured kind - and the remaining live suspect is mechanism C, which is invisible in the server
logs and needs `journalctl -u skypane-byos` device-fetch timestamps instead.

## Unconfirmed without live data

- Which mechanism (A, B, or C) actually fired for the two aircraft the user watched pass.
- Whether Orly 07/25 was the active runway at that moment, and whether ground traffic was in fact
  present in the corridor. The E2/E3 scenarios are geometrically real and use runway3.json's own
  admitted residual, but the specific occupancy is reconstructed, not observed.
- Whether the live VPS still runs the in-repo timer/env values (last VPS-verified 2026-08-26).
- The flashed firmware's actual CONFIG values: `firmware/sdkconfig` is generated at build time and is
  not committed, so a menuconfig change to MIN_REFRESH_SPACING_S would not be visible in this repo.
- The real e-ink blit duration on this hardware (assumed "tens of seconds" from panel.c's comments).

## Mechanism B fix (2026-08-28, second pass)

Re-opened after the user explicitly approved fixing mechanism B. Scope was restricted to B: mechanism C
(firmware refresh cadence) stays UNAPPROVED and untouched, and mechanism A was not revisited.

### Current focus (B pass)

hypothesis: Mechanism B is TWO independent defects that both end in the same D-04 suppression branch, and
  a fix for either one alone leaves the other able to freeze the panel on its own.
  B1 - UNSTABLE SORT INPUT. `select_runway3_aircraft()`'s tie-break is `seen_pos`, which is not a property
  of the aircraft at all: it is "seconds since THIS feeder network last got a position report", i.e. a
  property of the provider. Two providers ranking the same two real aircraft by it get different answers.
  B2 - SET-BLIND COMPARISON. `poll_current_aircraft()` compares only the two providers' FINAL PICKS. It
  never asks whether the other provider also SAW the winner. So when the two feeds hold
  overlapping-but-unequal candidate sets - routine, because they are independent feeder networks - the
  picks can differ even under a perfectly deterministic sort, and the cycle is suppressed anyway.
test: DONE. Design verified computationally against the real code and the real config before any edit
  (scratch design_probe.py + replay.py), then by the committed regression checks 32-36 and a full
  pre-fix restoration run.
expecting: DONE. B1 reproduced (adsb.fi picks 000003, adsb.lol picks 3985a7 from the same two real
  pavement positions, differing only in seen_pos). B2 reproduced (with the stable key in place, an
  asymmetric candidate set STILL produces different picks - proving determinism alone is insufficient).
next_action: DONE. Both fixed, 5 new checks committed, 3 of them proven to fail against a restored
  pre-fix implementation. Awaiting the user's own confirmation from the frame.

reasoning_checkpoint:
  hypothesis: |
    The seen_pos tie-break and the pick-only comparison are BOTH defects, and they fail independently.
    B1: seen_pos is the only field in the sort key that is a property of the OBSERVER rather than the
    observed. effective_altitude_ft is a property of the aircraft; hex is a property of the aircraft;
    seen_pos is a property of the feeder network that happened to report it. Ranking a shared reality by
    an observer-local value cannot yield a shared answer, so the two feeds manufacture a disagreement out
    of nothing and D-04 suppresses the cycle.
    B2: even with a provider-independent sort key, `poll_current_aircraft()` still only compares final
    picks. If adsb.fi's candidate set is {X, Y} and adsb.lol's is {Y} - because adsb.lol has not received
    X yet - then a deterministic sort makes adsb.fi pick X and adsb.lol pick Y, and the cycle is
    suppressed even though both feeds agree Y is real and on runway 3, and neither ever asserted X was
    absent. The corroboration question being asked ("did you pick the same aircraft?") is the wrong one;
    the right one is "did you SEE the aircraft I picked?".
  confirming_evidence:
    - "B1 reproduced against the real code this pass (scratch design_probe.py), using the real 3985a7
       on-ground capture at its real captured position plus a second pavement position derived from
       runway3.json's own published thresholds: with seen_pos as the arbiter adsb.fi selects 000003 and
       adsb.lol selects 3985a7 from the SAME two aircraft at the SAME positions; with the tie-break
       falling straight to hex, both select 000003. This is E3 from the diagnosis pass, re-run against
       real positions instead of scratch ones."
    - "seen_pos's instability is MEASURED, not assumed: adsb-test/RESULTS.md reconstructs per-provider
       position-update gaps of 36.2s median / 56.7s max (adsb.fi) and 22.4s / 69.8s (airplanes.live),
       all derived from this very field. The two feeds are also read >=1.1s apart
       (MIN_SECONDS_BETWEEN_CALLS). An arbiter with tens of seconds of provider-local spread is deciding
       between aircraft that tie exactly."
    - "B2's premise - that the two feeds hold unequal candidate sets - is measured in the same file:
       over the ~92-minute combined window, 37 hex were seen by both providers, 1 by adsb.fi only, 0 by
       airplanes.live only. That is a real, recorded set asymmetry between two feeds at THIS geofence.
       The instantaneous asymmetry is necessarily larger than that aggregate, because a 36.2s median
       position-update gap means a newly-appeared aircraft is in one feed before the other by
       construction."
    - "Removing seen_pos from the sort key is proven to be a no-op on every piece of real data this
       repo holds. Replayed all 6 committed geofence fixtures plus test_poll_loop.py's synthetic
       snapshot through both the pre-fix and post-fix keys (scratch replay.py): ZERO selections changed,
       and no committed fixture contains an effective-altitude tie at all - i.e. the seen_pos tie-break
       has never once been reached by real captured data. It was pure downside."
    - "Altitude ties are not hypothetical beyond the on-ground 0.0 collapse: every alt_baro in every
       committed fixture is a multiple of 25 (450, 425, 550, 600, 775, 800, 1050), so two airborne
       aircraft sharing a quantised altitude is an ordinary occurrence, and pre-fix it too fell through
       to seen_pos."
  falsification_test: |
    B1 is refuted if the two providers' picks still diverge when the candidate sets are identical and
    only seen_pos differs - check 33/34 assert exactly that, and both FAIL against a restored pre-fix
    implementation, so the mechanism is real and the fix addresses it.
    B2 is refuted if a stable tie-break alone were sufficient. Check 35 falsifies that directly and is
    the reason this pass did not stop at the sort key: it asserts, on the post-fix code, that adsb.fi's
    and adsb.lol's own deterministic per-provider picks STILL differ when the sets are asymmetric
    (000003 vs 3985a7) - and would therefore still have been suppressed by a pick-only comparison. If
    that assertion ever stops holding, check 35 fails loudly rather than passing for the wrong reason.
    The fix is refuted in the other direction if genuinely disjoint candidate sets stop suppressing -
    check 36 (plus pre-existing checks 23 and 26) fails if D-04 is gutted.
  fix_rationale: |
    B1: the tie-break falls straight to `hex`. This is not "pick a different arbitrary field" - hex is
    the ICAO 24-bit address, the one identifier in the record that is a property of the AIRCRAFT, is
    identical across every feed that sees it, and does not change between polls. It therefore delivers
    the exact property the D-P2-01 docstring already claimed the tie-breaks were for ("the same snapshot
    always yields the same flight and the display never flickers"), which seen_pos never could, since it
    changes on every poll by definition.
    B2: corroboration moves from comparing final PICKS to intersecting the two providers' CANDIDATE
    SETS, then selecting once, deterministically, from the first provider's records restricted to that
    intersection. This deliberately does NOT weaken D-04 - it strengthens what corroboration means. The
    safety property on what reaches the panel is unchanged in both directions: pre-fix, a corroborated
    display required the winner to be in both providers' sets (that is what equal picks implies);
    post-fix, the winner is drawn from the intersection, so it is still in both sets. What narrows is
    only the SUPPRESSION trigger - from "the picks differ" to "no aircraft at all is common to every
    answering source". A feed carrying a phantom the other lacks now yields the corroborated real
    aircraft instead of a blank panel, because the phantom is excluded from the intersection rather
    than merely losing a comparison. Unanimity is preserved exactly: the intersection is taken across
    ALL answering providers, so the existing 3-provider "2 agree, 1 dissents -> suppress" outcome is
    unchanged. The first-listed provider's record still reaches the renderer (ARCHITECTURE.md's
    load-bearing ordering claim, pinned by check 25).
  blind_spots:
    - "The second pavement aircraft's IDENTITY is synthetic, not captured. Only ONE real on-ground
       runway-3 record exists in this repo (3985a7), so a two-aircraft-on-the-pavement snapshot cannot
       be assembled from real captures alone. Its position is derived from runway3.json's own published
       thresholds and its state fields are the real 3985a7 capture's, but hex 000003 / SYNTH03 is an
       invented label following this repo's existing 000001/000002 synthetic convention - and the hex is
       LOAD-BEARING here, since it is the tie-break under test. A real second capture could not change
       the mechanism, but it would make the fixture stronger."
    - "Dropping seen_pos from the sort means a genuinely STALE record (an aircraft that has already
       vacated the runway, still being reported) can now win a tie against a fresher one. This is a real
       trade, not a free win. It is accepted because (a) the old behaviour was not reliably better -
       it was unstable, so it would oscillate rather than consistently prefer the fresher aircraft, and
       (b) the correct remedy is a staleness FILTER, which RESULTS.md's measured 36.2s median / 56.7s max
       update gaps make dangerous to add without more data: any threshold tight enough to catch a vacated
       aircraft would also drop genuine traffic. Deliberately NOT attempted this pass; recorded as an
       open residual instead."
    - "The intersection is keyed on hex with the same `or ''` normalisation the pre-fix comparison used,
       so two DIFFERENT hex-less records from two feeds would still be treated as the same aircraft.
       This is pre-existing behaviour, not opened by this change, and no real aggregator record lacks a
       hex - but it is not fixed here either."
    - "Not verified against live VPS logs or a live two-aircraft-on-the-pavement event. No capture of a
       real mechanism-B occurrence exists; the same constraint the diagnosis and the A pass both
       recorded (no VPS access in any of these sessions). The end-to-end claim remains unproven from the
       user's frame."
    - "Mechanism C is untouched and can still swallow a flight on its own, so closing B does not close
       the user's original symptom."

### Evidence (B pass)

- timestamp: 2026-08-28T00:00:00Z
  checked: B PASS. Derived the second on-pavement position from runway3.json's published thresholds and
    ran the real detect.py over both records (scratch design_probe.py).
  found: |
    The real 3985a7 capture measures along=55.2m, cross=+31.1m - i.e. 55.2m past threshold 07, which is
    physically "lining up on 07". Mirroring that same real measured distance about the runway midpoint,
    on the published centreline, gives along=3259.8m / cross=0.0m -> lat 48.727269, lon 2.401346, which
    is 55.2m short of threshold 25, i.e. "rolling out toward 25". Both records tag on_ground=True,
    in_corridor=True, track_aligned=True, on_runway3=True, below_ceiling=True, and both score effective
    altitude exactly 0.0. This is runway3.json's known_residuals item (3) constructed from the runway's
    own geometry.
  implication: The surviving mechanism-A residual is reproducible from real geometry, and the two
    aircraft are genuinely tied - so the tie-break, whatever it is, decides the whole cycle.

- timestamp: 2026-08-28T00:00:00Z
  checked: B PASS. Replayed all 6 committed geofence fixtures plus test_poll_loop.py's synthetic
    snapshot through the pre-fix (alt, seen_pos, hex) key and the proposed post-fix (alt, hex) key, and
    scanned every fixture for an effective-altitude tie (scratch replay.py).
  found: |
    ZERO selections changed. Additionally, NO committed fixture contains two candidates tied on
    effective altitude at all - meaning the seen_pos tie-break has never been reached by any real
    captured data in this repo. Its only observable effect was in the manufactured-disagreement path.
  implication: Removing seen_pos from the sort key is a no-op on all existing real data. The change
    cannot silently alter any previously-verified selection; it can only affect the tie case, which is
    exactly the case it is meant to fix.

- timestamp: 2026-08-28T00:00:00Z
  checked: B PASS. Whether a stable tie-break ALONE closes mechanism B, tested explicitly rather than
    assumed (this became committed check 35).
  found: |
    It does not. With the stable (alt, hex) key in place, adsb.fi holding {000003, 3985a7} selects
    000003 while adsb.lol holding only {3985a7} selects 3985a7 - the picks still differ, and a pick-only
    comparison still suppresses the cycle. The divergence comes from the SETS, which determinism cannot
    reconcile. RESULTS.md measures this asymmetry as real at this geofence (37 hex seen by both, 1 by
    adsb.fi only, 0 by airplanes.live only, over ~92 minutes).
  implication: Both halves of the fix are load-bearing. Had this pass stopped at the sort key it would
    have reduced the frequency of manufactured suppression without closing it, and the residual would
    have been invisible - the code would have looked deterministic and correct.

- timestamp: 2026-08-28T00:00:00Z
  checked: B PASS. Post-fix verification - full suite, ruff, attribution, and the harness re-run against
    a faithfully restored pre-fix implementation (both seams patched back: selection_sort_key and
    poll_current_aircraft).
  found: |
    Full suite green: 9/9 harnesses, 221 checks, coverage 82% (threshold 75). ruff clean.
    check-attribution.sh PASS. server/test_plane_detection.py 31 -> 37 checks.
    Against the restored pre-fix implementation: checks 33, 34, 35 and 37 FAIL and nothing else does
    (33/37, exit 1). Checks 32 and 36 pass in both directions BY DESIGN - 32 is the precondition check
    (it asserts the pre-fix behaviour is genuinely reproducible, so it MUST hold pre-fix, exactly like
    checks 11 and 29) and 36 is the D-04 guard (it must hold in both directions, or the fix has gutted
    the safety net). 36 was deliberately SPLIT during this pass: it originally also asserted the
    disagreement log line's new content, which made it fail pre-fix and blurred the line between a guard
    and a regression - that assertion is now check 37.
  implication: The three checks that assert the fixed behaviour are proven to catch the bug rather than
    merely to pass alongside it, and the two that are not supposed to flip are documented as such.

### Root cause (mechanism B)

Two independent defects funnelling into the same D-04 suppression branch:

  B1. `select_runway3_aircraft()`'s sort key was `(effective_altitude_ft, seen_pos, hex)`. `seen_pos` is
      the only element of that key that is a property of the OBSERVER rather than the observed - it is
      "seconds since this feeder network last received a position report". adsb.fi and adsb.lol are
      independent feeder networks, queried >=1.1s apart, whose spread on this field is measured in
      adsb-test/RESULTS.md at tens of seconds. So when two records tie on effective altitude - which the
      mechanism-A fix made rarer but explicitly did not remove (runway3.json known_residuals item 3: two
      aircraft both genuinely on the pavement, one lining up on 07 while another rolls out toward 25) -
      each feed ranked the same two real aircraft differently, purely from staleness noise.

  B2. `poll_current_aircraft()` compared only the two providers' FINAL PICKS. It never asked whether the
      other provider had also SEEN the winner. Because the two feeds hold overlapping-but-unequal
      candidate sets as a matter of routine (RESULTS.md: 37 hex common, 1 adsb.fi-only, over ~92
      minutes; and a 36.2s median position-update gap guarantees a new aircraft reaches one feed before
      the other), the picks can differ even under a perfectly deterministic sort.

Either defect alone reaches `return None` for the entire cycle, which poll_loop treats as the D-04
"leave the panel alone" hold - indistinguishable, from the user's chair, from an empty sky.

### Fix (mechanism B)

SCOPE: MECHANISM B ONLY. Mechanism C (device refresh cadence, CONFIG_FP_MIN_REFRESH_SPACING_S, anything
under firmware/) is UNAPPROVED and was not touched. Mechanism A was not revisited.

B1 - STABLE, PROVIDER-INDEPENDENT TIE-BREAK. The sort key is now `(effective_altitude_ft, hex)`,
extracted into a module-level `selection_sort_key()` so it is one named thing that can be reasoned about
and monkeypatched. `hex` is the ICAO 24-bit address: a property of the aircraft, identical across every
feed that sees it, and constant between polls. It delivers precisely the property D-P2-01's docstring
already claimed the tie-breaks provided - "the same snapshot always yields the same flight and the
display never flickers between two simultaneous aircraft" - which `seen_pos` structurally could not,
because it changes on every poll by definition. `seen_pos` is still carried in the returned dict for
diagnostics; it is only removed from the ORDERING.

B2 - CORROBORATE THE CANDIDATE SET, NOT THE PICK. `select_runway3_aircraft()` was split (no behaviour
change) into `runway3_candidates()` - the gated candidate list - and the selection over it, so
`poll_current_aircraft()` can now see each provider's whole candidate set rather than just its winner.
Corroboration is now the INTERSECTION of the answering providers' candidate hex sets; the winner is then
selected once, deterministically, from the FIRST provider's records restricted to that intersection.

  both/all sources share >=1 aircraft -> select from the intersection, corroborated=True
  exactly one source answered          -> its own pick, corroborated=None (unchanged)
  no aircraft common to every source   -> log both candidate sets, return None (D-04, unchanged)

WHY THIS DOES NOT WEAKEN D-04. The safety property on what reaches the panel is unchanged: pre-fix, a
corroborated display required the winner to be in both providers' sets (that is what equal picks
implies); post-fix, the winner is drawn from the intersection, so it is still in every answering
provider's set. What narrows is only the SUPPRESSION TRIGGER - from "the picks differ" to "no aircraft
at all is common to every answering source". The genuine-doubt case the net exists for still suppresses
(checks 23, 26, 36). A feed carrying a phantom or stale record the other lacks now yields the
corroborated REAL aircraft rather than a blank panel, because the uncorroborated record is excluded from
selection rather than merely losing a comparison - so corroboration became more effective, not less.
Unanimity is preserved exactly as before: the intersection is taken across ALL answering providers, so
the 3-provider "two agree, one dissents" case still suppresses. Ordering stays load-bearing - the
first-listed provider's record is still what reaches the renderer (ARCHITECTURE.md; check 25).

The disagreement log line keeps the literal string "providers disagree", so the triage recipe in "Next
occurrence" below stays valid, but now prints each provider's FULL candidate set instead of just its
pick - which is what is actually being compared.

RESIDUALS - recorded in runway3.json known_residuals as items (4) and (5), and honestly NOT closed:
  (4) STALE RECORDS ARE NO LONGER DEPRIORITISED. Dropping seen_pos from the ordering means an aircraft
      that has already vacated the runway but is still being reported can win a tie against a fresher
      record. The old behaviour was not reliably better (being unstable, it oscillated rather than
      consistently preferring the fresher aircraft), and the correct remedy is a staleness FILTER, which
      RESULTS.md's 36.2s median / 56.7s max update gaps make unsafe to add without more data. Not
      attempted.
  (5) A SHARED WRONG ANSWER IS STILL UNDETECTABLE. If both feeds carry the same bad record - the same
      phantom, or the same stale position - it is in the intersection and will be displayed with
      corroborated=True. Cross-source corroboration can only catch a disagreement between sources; it
      has never been able to catch two sources being wrong in the same way, and this change does not
      alter that.

### Verification (mechanism B)

- FULL SUITE GREEN: `bash scripts/run-all-tests.sh` -> "Result: PASS", 9/9 harnesses, 221 checks,
  coverage 82% (threshold 75 in pyproject.toml). `server/.venv/bin/ruff check .` -> "All checks
  passed!". `bash scripts/check-attribution.sh` -> PASS.
- server/test_plane_detection.py extended 31 -> 37 checks, all passing.
- REGRESSION CHECKS PROVEN TO CATCH THE BUG, not merely to pass with the fix: restoring the pre-fix
  implementation at both seams (`selection_sort_key` back to (alt, seen_pos, hex), and
  `poll_current_aircraft` back to the pick-comparison body, lifted verbatim from commit d9ec8f8) fails
  EXACTLY checks 33, 34, 35 and 37 -> 33/37, exit 1. Checks 32 and 36 hold in both directions BY DESIGN
  and this is deliberate: 32 is the precondition check (it asserts the pre-fix ordering really does
  diverge, so it must hold pre-fix - the same role checks 11 and 29 play for the earlier fixes), and 36
  is the D-04 guard (it must hold before AND after, or the safety net has been gutted). The harness
  docstring now states this three-way distinction - regression / precondition / guard - explicitly, so a
  later reader cannot mistake a guard for a regression and quietly relax it.
- BEFORE/AFTER REPLAY over every committed fixture plus test_poll_loop.py's synthetic snapshot: ZERO
  selections changed, and no committed fixture contains an effective-altitude tie at all - the seen_pos
  tie-break was never reached by any real captured data in this repo.
- DETERMINISM-ALONE FALSIFIER IS COMMITTED, NOT JUST ARGUED: check 35 asserts on the POST-fix code that
  the two providers' own per-provider deterministic picks still differ under asymmetric candidate sets,
  so the claim "a stable tie-break would not have been enough" is enforced by a test rather than left as
  prose.
- D-04 GUARDED FROM THREE ANGLES: pre-existing checks 23 and 26 (disjoint single-candidate sets, via
  explicit providers and via the production default order) plus new check 36 (disjoint MULTI-candidate
  sets, the case where set-comparison and pick-comparison could have diverged), which also asserts the
  stderr line still contains the literal "providers disagree" that the triage runbook greps for.
- LIVE END-TO-END: `server/plane/detect.py` and `--json` both ran clean against the real endpoints
  through the rewritten corroboration path (exit 0, no stderr, "no aircraft in the runway-3 geofence" /
  `null`). CAVEAT, same as the mechanism-A pass: both adsb.fi and adsb.lol returned 0 raw records at
  that moment - Orly is under curfew at this hour - so the run exercised the code path but NOT the
  corroboration logic. There is no live capture of the fixed comparison accepting real traffic.
- NOT VERIFIED: no live VPS correlation and no capture of a real mechanism-B occurrence - the same
  constraint the diagnosis and mechanism-A passes both recorded. The fixture's second pavement aircraft
  has a synthetic identity (see blind_spots). Mechanism C is untouched, so this does not close the
  user's original symptom end to end.

files_changed (B pass):
  - server/plane/detect.py (selection_sort_key() extracted, seen_pos removed from the ordering;
    runway3_candidates() split out of select_runway3_aircraft(); poll_current_aircraft() corroborates
    by candidate-set intersection; docstrings recording why)
  - server/test_plane_detection.py (31 -> 37 checks, plus a docstring section distinguishing
    regression checks from precondition checks and guards)
  - server/fixtures/geofence_pavement_pair.json (NEW)
  - server/fixtures/README.md (provenance, real/derived/synthetic split field by field)
  - adsb-test/runway3.json (known_residuals item 3 marked CLOSED; items 4 and 5 opened)
  - ARCHITECTURE.md (detection paragraph updated to describe set-level corroboration)

## Next occurrence - how to tell the mechanisms apart

- `journalctl -u skypane-poll | grep "providers disagree"` -> a cross-source disagreement. Since the
  2026-08-28 mechanism-B fix this line prints each feed's FULL candidate set, not just its winner, and
  it now fires ONLY when no aircraft at all is common to the two feeds. A hit here is therefore a
  GENUINE disagreement worth investigating on its merits - the manufactured kind (same aircraft, feeds
  ordering them differently; or one feed simply not having received a record yet) no longer reaches it.
- `journalctl -u skypane-poll | grep poll_loop` -> a constant `hex=` with `panel_changed=False` across
  many consecutive polls -> mechanism A. NOTE a suppressed cycle logs `hex=None ... panel_changed=False`,
  byte-identical to a genuinely empty sky; only the stderr line above separates the two.
- `journalctl -u skypane-byos` -> `GET /device/v1/display` timestamps; if panel_changed=True events
  outpace device fetches, mechanism C.
- OBSERVABILITY GAP, PARTIALLY CLOSED 2026-08-28. The SUPPRESSED path is now fully diagnosable: the
  disagreement line above prints every candidate each feed saw. The SUCCESSFUL path is not - a normal
  poll still logs only the winner, so "the right aircraft was present and lost the sort" remains
  unprovable from logs. `runway3_candidates()` now exists as a named function, so logging the
  per-provider candidate set (hex, eff_alt, cross_track_m, on_ground) - or just the count and the
  runner-up - on every poll is a small change whenever it is wanted.
