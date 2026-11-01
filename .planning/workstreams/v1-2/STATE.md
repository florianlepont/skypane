---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Fleet platform
current_plan: 11
status: verifying
stopped_at: Phase 51 closed at the owner's request
last_updated: "2026-10-30T18:02:51.253Z"
last_activity: 2026-10-30
progress:
  total_phases: 12
  completed_phases: 4
  total_plans: 37
  completed_plans: 31
  percent: 25
---

# Project State

## Project Reference

**Core Value:** Glancing at the frame tells you, in real time, which plane is taking off or landing right now — while also being a satisfying ambient piece on the wall.
**Current focus:** Phase 49 — per-hardware-ota-registry

## Current Position

Phase: 49 (per-hardware-ota-registry) — ready for verification
Plan: 11 of 11 (all plans complete)
Status: Phase complete — ready for verification
Last activity: 2026-10-30

Progress: [████████░░] 84%

## Progress

**Phases Complete:** 0 of 12
**Current Plan:** 11

## Accumulated Context

### Decisions

- Phase numbering continues from v1.1 (Phase 47). Phase 47 is open and untouched by this workstream.
- Production deploys touching the live frame and the combined firmware OTA (Phase 57) wait for Phase 47 to close, or for an explicit owner release.
- Phases 48–57 use simulated hardware types; only Phase 58 needs a purchase, after its driver spike.
- Registry rewrite lives in Phase 49, not Phase 48. Auth is split: Phase 54 gate, Phase 55 pairing and console.
- Run `scripts/check_comment_history.py check` before Phase 48 and record the result for Phase 59.
- [Phase 49]: Phase 49-02: OTA signing option S (one key for all hardware types), decided 2026-10-29 by project owner; revisitable before second board first cable flash (Phase 58)
- [Phase 49]: import-dir orders by build; per-type pairs release-<key>.json + skypane-<key>-<tag>.bin; --hardware-type on import-bench/list/check-image
- [Phase 49]: 49-07: legacy frame's report entry is not rewritten solely to add hardware_type (Phase 47 telemetry freeze)
- [Phase 49]: Update page type chooser reuses the segmented control as a GET form; shown only with more than one relevant type; hidden hardware_type field also carried for a sole non-legacy type
- [Phase 50]: Image container announced per request by `X-Img-Fmt` (never persisted); BYOS imports the canonical `server/image_container.py` encoder; legacy frames get raw 960000 bytes byte for byte; firmware reader is host-tested only, wiring and OTA belong to Phase 57
- [Phase 54]: Auth0 sign-in, local roles and default-deny delivered; the per-device routes of Phase 51 are covered by the access matrix but stay admin-only; letting an owner see their own frames comes with Phase 55 (AUTH-03 stays open until then). Legacy shared-password removal is event-driven (when Auth0 sign-in is in production), owner stamps the date at go-live. Sessions live in fleet.db (30 d absolute, 7 d idle), sign-out also ends the Auth0 session. Role denial answers the same 404 as an unknown path. See phases/54-*/54-HANDOFF.md.
- [Phase 54 go-live 2026-10-30]: deployed `af9e8521` (20:27 UTC; earlier Phase 50 deploy 15:34 UTC), Auth0 env set 20:33 UTC, real-tenant smoke test passed (sign-in, wrong code_verifier rejected, sign-out ends the Auth0 session, Caddy redaction). Companion restarts at those times may explain Phase 47 telemetry gaps. The owner turned the shared-password fallback off the same day (`SKYPANE_LEGACY_PASSWORD_LOGIN=0`) and its code was removed and deployed at 22:28 UTC (Auth0 is the only sign-in; the sessions schema is untouched and an old `legacy-admin` row never authenticates). Phase 51 was deployed at 22:11 UTC. All production restarts of 2026-10-30 (UTC): 15:34, 20:27, 20:33, about 21:0x (flag off), 22:11, 22:28.
- [Phase 60 added 2026-10-30]: device co-management (primary owner plus co-managers, added by the owner or an admin) requested by the owner; extends the ownership gate `access.authorized_device_id`.
- [Phase 56 2026-10-31]: Hardware profile drives render, battery thresholds/curve and theme offer. Layout family per profile (portrait untouched, dedicated landscape). Battery values carry per-value provenance, legacy values provisional until Phase 47 closes; EE04 slot is number-free (Phase 58). Credits page `/credits` public from `companion/credits.json`. adsb.fi / adsb.lol contact draft `56-PROVIDER-CONTACT.md` status deferred: the owner sends it once the fleet has more than 10 users. Landscape previews approved; owner then asked for the band themes to cross the whole canvas like portrait (fixed).
- [Phase 52 merged 2026-10-31, not deployed]: fleet poll cycle serves every device; global ADS-B budget 1 request per 1.1 s across providers and processes (flock-guarded `request_ledger.json` in the state root, persisted ~60 s provider pause); one fetch per exact (centre, radius) zone, live-frame zone first then oldest-served, 25 s start deadline, devices silent for 7 days skipped; shared adsbdb cache `adsbdb_shared_cache.json` (TTLs unchanged). Poll now removed at the owner's request (FLT-02 trigger dropped, quiet hours and timezone kept). Deploy waits for the owner; it adds about 1 s to the live frame's cycle (providers no longer run in parallel).
- [Phase 56 deployed 2026-10-31]: deployed from `main` at `26f1d292` (PR #257) at 12:02 Paris time, reported by the owner (not checked by Claude). The deploy carries everything merged into `main` up to that commit, not Phase 56 alone. The contact with adsb.fi / adsb.lol stays deferred until the fleet has more than 10 users.
- [Phase 55 2026-10-31, not deployed]: frame pairing (30-symbol 8-char code, 30 min, wake 300 s, atomic claim), admin console (Cadres, Users, Audit log, Locations, Releases entry) and reduced owner view delivered on schema 3; verified in code (3/3), real-frame and deploy checks pending with the owner; see phases/55-*/55-HANDOFF.md and 55-REVIEW-FIX.md.
- [Phase 53 2026-10-31, deployed by CI on merge]: detection modes in code on branch `milestone/v1.2-phase-53-detection-modes` (PR #265). France runway catalogue built offline from OurAirports (340 runways, 272 airports, pinned snapshot, byte-identical rebuild); runway-pair following with a 50 m corridor floor and a narrow corridor between parallel runways; position mode around a saved location with a whole-km radius of 4 to 28, coordinates rounded to 2 decimals before any third party, France bounding box. The live Orly frame runs on the generic logic with the frozen hand-tuned box and a kill switch (`SKYPANE_LEGACY_ORLY_GEOFENCE=1`); replay of about 709,000 swept cells plus the recorded fixtures shows no differing decision. Display Runway card removed; new `/detection` page (owner or admin) with minimal location create/edit; a position device without a usable location shows a `SET A LOCATION` screen. Verification `human_needed`: panel look, policy numbers (50 m floor, 5 degree parallel threshold, France box, 4-28 km), flipping the live frame, deploy.
- [Phase 53 deployment 2026-10-31/11-01]: merging to `main` runs the CI `deploy` job (no reviewer pause was observed), so the merge of PR #265 deployed Phase 53 on 2026-10-31 at 20:20 UTC (run 41237444594); the earlier note that nothing was deployed was wrong. The owner checked the live Orly frame afterwards: image and rhythm unchanged. The owner validated the policy numbers (50 m corridor floor, 5 degree parallel threshold, France box, radius, ceiling) on 2026-11-01 and chose, for position mode, no altitude ceiling, a 2 to 28 km radius and an `OVERHEAD` state for level aircraft (PR #268, merged 2026-11-01 17:50 UTC, deployed by its own run 41333550343). Review findings LW-01, LW-03, LW-04 and LW-06 fixed in the same PR; LW-04 also narrows the Phase 55 Display-form location picker to the frame owner's and ownerless locations. `SKYPANE_LEGACY_ORLY_GEOFENCE=1` remains the kill switch for the Orly frame. Phase 53 closed 2026-11-01: the owner saw the CDG 08L/26R runway render on the real panel and confirmed the live frame is back on Orly 07/25; the owner also tested the position mode on the real panel the same day and reports that it works and saw the `OVERHEAD` state on the panel (the `SET A LOCATION` screen was not reported as seen).

### Pending Todos

None yet.

### Blockers/Concerns

- Owner decisions still open (see research/SUMMARY.md): OTA signing, Auth0 app type, shared-password removal date, second board.
- Research flagged for Phases 49, 50, 52, 53, 54, 55 and 58.

## Session Continuity

**Stopped At:** Phase 51 closed at the owner's request
**Resume File:** None
