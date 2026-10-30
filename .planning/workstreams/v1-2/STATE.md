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
- [Phase 54]: Auth0 sign-in, local roles and default-deny delivered; per-device route rows wait for Phase 51. Legacy shared-password removal is event-driven (when Auth0 sign-in is in production), owner stamps the date at go-live. Sessions live in fleet.db (30 d absolute, 7 d idle), sign-out also ends the Auth0 session. Role denial answers the same 404 as an unknown path. See phases/54-*/54-HANDOFF.md.
- [Phase 54 go-live 2026-10-30]: deployed `af9e8521` (20:27 UTC; earlier Phase 50 deploy 15:34 UTC), Auth0 env set 20:33 UTC, real-tenant smoke test passed (sign-in, wrong code_verifier rejected, sign-out ends the Auth0 session, Caddy redaction). Companion restarts at those times may explain Phase 47 telemetry gaps. The owner turned the shared-password fallback off the same day (`SKYPANE_LEGACY_PASSWORD_LOGIN=0`); removing its code is still to do.
- [Phase 60 added 2026-10-30]: device co-management (primary owner plus co-managers, added by the owner or an admin) requested by the owner; extends the ownership gate `access.authorized_device_id`.

### Pending Todos

None yet.

### Blockers/Concerns

- Owner decisions still open (see research/SUMMARY.md): OTA signing, Auth0 app type, shared-password removal date, second board.
- Research flagged for Phases 49, 50, 52, 53, 54, 55 and 58.

## Session Continuity

**Stopped At:** Phase 51 closed at the owner's request
**Resume File:** None
