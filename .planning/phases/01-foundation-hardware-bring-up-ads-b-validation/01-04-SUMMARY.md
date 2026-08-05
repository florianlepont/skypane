---
phase: 01-foundation-hardware-bring-up-ads-b-validation
plan: 04
subsystem: infra
tags: [adsb, adsb.fi, airplanes.live, urllib, geofence, decision-checkpoint]

# Dependency graph
requires:
  - phase: 01-foundation-hardware-bring-up-ads-b-validation
    provides: PROJECT.md/REQUIREMENTS.md's prior "local ADS-B primary, aggregator fallback" framing (D-01 through D-04 in 01-CONTEXT.md), which this plan tests and reverses
provides:
  - A stdlib-only geofenced live query tool (query_aggregator.py) against adsb.fi and airplanes.live
  - An unattended windowed sampler (sample_window.py) and metrics analyser (analyze_samples.py) with a pre-committed viability threshold
  - A recorded, dated, numeric verdict in adsb-test/RESULTS.md answering the plane-detection data-source question for Phase 2
affects: [02-plane-view, project-decisions, requirements]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Geofence + viability threshold fixed before sampling, in a dedicated adsb-test/ directory unwired from firmware"
    - "Decision checkpoints record the resolved choice, date, and citing numbers directly in the artifact the decision was made from (RESULTS.md), not just in SUMMARY.md"

key-files:
  created:
    - adsb-test/query_aggregator.py
    - adsb-test/sample_window.py
    - adsb-test/analyze_samples.py
    - adsb-test/runway3.json
    - adsb-test/README.md
    - adsb-test/RESULTS.md
    - adsb-test/.gitignore
  modified:
    - adsb-test/RESULTS.md

key-decisions:
  - "aggregator-sufficient (2026-08-05): both adsb.fi and airplanes.live cleared the coverage bar over a combined ~92-minute real-traffic window (38/37 distinct aircraft <=3000ft, 2/2 on-ground detections); the only miss was update cadence (36.2s/22.4s median gap vs a 15s target), judged immaterial given the device's multi-minute wake/poll refresh cycle. No RTL-SDR hardware ordered; D-02 fallback not invoked."
  - "airplanes.live preferred as primary provider (tighter 22.4s median update gap, zero sample errors vs 1 for adsb.fi); adsb.fi retained as a viable secondary given 37/38 hex overlap between the two."
  - "PROJECT.md/REQUIREMENTS.md's 'local ADS-B primary, aggregator fallback' framing (D-03) is left unchanged by this plan per the plan's Task 3 action, which reserves that rewrite as an explicit phase-close follow-up rather than making it here."

patterns-established:
  - "Pattern: pre-commit a numeric viability threshold in the analysis script before collecting real data, so a go/no-go decision is a reading of a test rather than a post-hoc rationalisation."

requirements-completed: []

coverage:
  - id: D1
    description: "Recorded, dated, numeric decision on the plane-detection data source (aggregator-sufficient) and the D-02 RTL-SDR fallback (not invoked), based on a pre-committed viability threshold tested over real Orly traffic"
    verification:
      - kind: manual_procedural
        ref: "adsb-test/RESULTS.md ## Recommendation and ## Downstream Actions sections; sed -n '/## Recommendation/,$p' adsb-test/RESULTS.md | grep -c PENDING returns 0"
        status: pass
    human_judgment: true
    rationale: "This is a checkpoint:decision task — the developer explicitly chose aggregator-sufficient in conversation; the deliverable is the correct transcription of that choice with citing numbers, which was verified by inspection rather than an automated test of judgment quality."

duration: 25min
completed: 2026-08-05
status: complete
---

# Phase 1 Plan 4: ADS-B Aggregator Viability & Data-Source Decision Summary

**Recorded the aggregator-sufficient verdict for Phase 2's plane-detection data source: both adsb.fi and airplanes.live see runway-3 traffic below 3000ft and on the ground over a 92-minute real-traffic window, so no RTL-SDR hardware is being ordered.**

## Performance

- **Duration:** ~25 min (Task 3 only; Tasks 1-2 completed and committed in a prior session)
- **Completed:** 2026-08-05T06:38:47Z
- **Tasks:** 3 (Tasks 1-2 completed previously; Task 3 completed this session)
- **Files modified:** 1 (adsb-test/RESULTS.md)

## Accomplishments
- Transcribed the developer's `aggregator-sufficient` decision into `adsb-test/RESULTS.md`'s `## Recommendation` section, replacing the `PENDING` placeholder with the chosen option identifier, today's date, and a rationale citing the specific recorded numbers (38/37 distinct aircraft <=3000ft, 2/2 on-ground, 36.2s/22.4s median update gaps vs the 15s threshold).
- Appended a `## Downstream Actions` section per the plan's `aggregator-sufficient` path: named airplanes.live as the preferred primary provider (with adsb.fi as a viable secondary), noted Phase 2 builds behind a single data-source module for a cheap future swap, flagged the D-03 PROJECT.md/REQUIREMENTS.md rewrite as an explicit phase-close follow-up (not made here, per the plan's own scoping), and confirmed no RTL-SDR hardware is being ordered.
- Closed out the highest-uncertainty question in the whole project: Phase 2's plane view now has a settled, evidence-backed data source before planning starts.

## Task Commits

Each task was committed atomically:

1. **Task 1: Geofenced live query against both candidate aggregators** - `1f79761` (feat)
2. **Task 2: Sample a real traffic window and compute the viability metrics** - `eaef44c` (feat)
3. **Task 3: Decide the plane-detection data source and the D-02 fallback** - `6f413b7` (docs)

**Plan metadata:** (this commit, following SUMMARY.md creation)

## Files Created/Modified
- `adsb-test/RESULTS.md` - Recommendation section resolved from `PENDING` to `aggregator-sufficient` with dated rationale; new `## Downstream Actions` section added
- `adsb-test/query_aggregator.py` (Task 1, prior session) - Single-shot geofenced query against adsb.fi and airplanes.live
- `adsb-test/sample_window.py` (Task 2, prior session) - Unattended windowed sampler
- `adsb-test/analyze_samples.py` (Task 2, prior session) - Viability metrics analyser with pre-committed threshold
- `adsb-test/runway3.json` (Task 1, prior session) - Runway-3 geofence with sourced coordinates
- `adsb-test/README.md` (Task 2, prior session) - Command reference and D-03 interpretation note

## Decisions Made
- **aggregator-sufficient** chosen by the developer over `rtl-sdr-fallback` and `sample-again`: both providers comfortably cleared the coverage thresholds (distinct sub-ceiling aircraft, on-ground detection) that Pitfall 3 identified as the real risk; the update-cadence miss was judged immaterial because the device's wake/poll cycle refreshes on the order of minutes, not seconds, so even the slower 36.2s median gap is well within the display's own refresh tolerance. No interest in taking on RTL-SDR hardware/setup for marginal benefit.
- airplanes.live preferred as primary provider over adsb.fi for the tighter update cadence and zero sample errors in this window, with adsb.fi retained as a viable secondary given near-total hex overlap (37 of 38 hex seen by adsb.fi were also seen by airplanes.live).
- The D-03 rewrite of PROJECT.md's "Key Decisions" table and REQUIREMENTS.md's "Out of Scope" ADS-B-aggregator row is deliberately **not** made in this plan — the plan's Task 3 action explicitly lists it as a follow-up for phase close, and this executor followed that scoping rather than expanding it into this plan's file set.

## Deviations from Plan

None - plan executed exactly as written. Task 3's `<action>` block was followed precisely: the `PENDING` line was replaced with the option identifier, date, and a rationale citing at least two specific numbers, and a `## Downstream Actions` section was appended naming the aggregator-sufficient follow-ups (winning provider, single data-source module, D-03 citation) without pre-emptively editing PROJECT.md or REQUIREMENTS.md, which the plan explicitly reserves for phase close.

## Issues Encountered

None. Tasks 1 and 2 (query tooling, sampling, and analysis) were already complete and committed from a prior session; this session's only work was resolving the Task 3 decision checkpoint now that the developer's choice was known.

## User Setup Required

None - no external service configuration required. No hardware ordered as a result of this decision.

## Next Phase Readiness

- Phase 2's plane view has a settled, evidence-backed data source: the public ADS-B aggregators (airplanes.live primary, adsb.fi secondary), queried via the geofence and filtering logic already proven out in `adsb-test/query_aggregator.py`.
- **Follow-up required at phase close (not done in this plan, per D-03 and this plan's own scoping):** rewrite PROJECT.md's "Key Decisions" table entry for local ADS-B and REQUIREMENTS.md's "Out of Scope" row for the ADS-B aggregator API to reflect aggregator-as-primary rather than "documented fallback only". This is explicitly listed as a downstream action in `adsb-test/RESULTS.md` and should not be missed when Phase 1 transitions.
- `hardware/BOM.md`'s "Separate Budget Line" RTL-SDR items remain unordered and out of scope for this milestone.
- Nothing from this track was wired into device firmware, matching this phase's scope - PLANE-03 remains a Phase 2 deliverable.

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Completed: 2026-08-05*

## Self-Check: PASSED

All files created by this plan exist on disk (query_aggregator.py, sample_window.py, analyze_samples.py, runway3.json, README.md, RESULTS.md, .gitignore, this SUMMARY.md). All three task commits (1f79761, eaef44c, 6f413b7) found in git log.
