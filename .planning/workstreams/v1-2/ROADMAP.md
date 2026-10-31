# Roadmap: SkyPane

## Milestones

- [x] **v1.0 — MVP** — shipped and archived on 2026-09-30 (see the root `.planning/milestones/`).
- [ ] **v1.1 — Battery and Companion!** — Phases 44–47, tracked in the root `.planning/ROADMAP.md`. Phase 47 (field validation of the live frame) is still open and is not touched by this roadmap.
- [ ] **v1.2 — Fleet platform** — Phases 48–59 (this workstream, `v1-2`). Turn the one-frame system into a small invite-only fleet: several users, several devices, several hardware types, any location in France.

## Overview

V1.2 adds a fleet database, per-hardware OTA and image formats, a per-device runtime with a shared ADS-B request budget, two detection modes, Auth0 sign-in with local roles, pairing and an admin console, profile-driven rendering, and a second hardware type. There is no new runtime dependency and no new daemon. Phases 48–57 are built and tested with simulated hardware types; only Phase 58 needs a purchase, and only after its driver spike.

Everything is expand-only and behaviour-preserving for the live frame: it keeps its MAC, secret, token and file paths, and keeps receiving its current raw image and wake interval.

## Phase 47 coordination (v1.1, open)

Phase 47 measures the live frame on the live VPS. This milestone must not modify, block, or disturb it.

- **May proceed now** (no production effect): all design, code, tests and CI work in Phases 48–56, and the Phase 58 shortlist and driver spike.
- **Must wait until Phase 47 closes (or the owner explicitly releases it):**
  - Any production deploy that touches the live frame's state, registry, poll loop, BYOS responses or companion: Phases 48, 49, 51, 52, 54, 55, 56 each ship to production only after this gate. The Phase 48 freeze-list test (DATA-05) is the guard that a deploy cannot change what Phase 47 measures.
  - The combined firmware OTA to the legacy frame (Phase 57, OTA-04). No firmware change reaches the live frame before this gate.
  - The legacy-frame battery numbers feeding the hardware profile (Phase 56, HWR-01) are final only after Phase 47.
- Every deploy before then, if the owner allows it, must run the previous release correctly on post-migration state (forward-only, expand-only).

## Phases

**Phase Numbering:**

- Integer phases are planned milestone work, continuing from v1.1 (Phase 47).
- Decimal phases are urgent insertions created only when needed.

- [x] **Phase 48: Fleet Data Model, Roles and Live-Frame Migration** - One fleet database with users, roles, devices and hardware profiles; the live frame migrated without any visible change. (completed 2026-10-29)
- [ ] **Phase 49: Per-Hardware OTA Registry** - Firmware releases are published, scheduled and offered per hardware type, with integrity checks. (criteria 1, 2, 4 verified 2026-10-30; criterion 3 device-side check deferred, awaiting a bench unit)
- [x] **Phase 50: Common Image Format** - A versioned image container served only to frames that announce support, with a legacy-safe firmware reader specified. (completed 2026-10-30)
- [x] **Phase 51: Per-Device Config, Image and State** - Every device has its own config, image, history and health, and the BYOS serves each frame its own image.
- [x] **Phase 52: Fleet Poll Cycle, Zones and Request Budget** - One upstream ADS-B request per zone under a persisted global 1 req/s budget.
- [ ] **Phase 53: Detection Modes (Airport/Runway and Position/Radius)** - Devices can follow any French runway or any position within a bounded radius.
- [ ] **Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access** - Invite-only sign-in with local roles and a proven route and ownership matrix.
- [ ] **Phase 55: Frame Pairing, Admin Console and Reduced User View** - Admins pair frames to users and manage the fleet; users see only their own frames with fewer options.
- [ ] **Phase 56: Per-Hardware Rendering, Battery Profiles, Health and Credits** - Rendering and health follow the hardware profile; credits page published.
- [ ] **Phase 57: Combined Legacy-Frame Firmware Release** - One OTA release gives the live frame the new image reader and 401 recovery. Gated on Phase 47.
- [ ] **Phase 58: Second Hardware (Shortlist, Spike, Purchase, Validate)** - A second hardware type chosen after a driver spike and validated on a real unit.
- [ ] **Phase 59: Comment-History Debt** - The comment-history guard debt is cleared or only shrinks.
- [ ] **Phase 60: Device Co-Management** - A frame keeps one primary owner and gains co-managers whom the owner or an admin can add.

## Phase Details

### Phase 48: Fleet Data Model, Roles and Live-Frame Migration

**Goal**: The owner can record users, devices, hardware types and locations in one fleet database, and the live frame is migrated into it with no observable change.
**Depends on**: Nothing in v1.2 (v1.1 Phase 47 must stay unaffected; production deploy waits for it)
**Requirements**: DATA-01, DATA-02, DATA-03, DATA-04, DATA-05
**Success Criteria** (what must be TRUE):

  1. After migration, the live frame's next poll returns the same image hash and wake interval as before, with no reflash and no re-enrolment (MAC, secret, token and file paths kept).
  2. The previous release still runs correctly on the migrated state, and re-running the migration changes nothing.
  3. The owner can create users with role admin or user, devices with exactly one owner each, and hardware types (including simulated ones) as profiles; the role is stored locally and never read from Auth0 alone.
  4. The fleet database is part of the backup and a restore from that backup is tested; a test fails if wake cadence, battery telemetry or poll state fields that Phase 47 measures change.

**Plans**: 7 plans
Plans:
**Wave 1**

- [x] 48-01-PLAN.md — Hardware profile registry with env-gated simulated types (DATA-04)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 48-02-PLAN.md — fleet.db schema, user_version migrations, users/roles/locations/devices with one owner (DATA-01, DATA-03)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 48-03-PLAN.md — fleet_migrate (idempotent, dry-run), fleet_cli, live-shaped fixture (DATA-01..03)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 48-04-PLAN.md — byos auth from fleet.db with legacy fallback, dual-write, drop "default" bucket (DATA-02)
- [x] 48-05-PLAN.md — fleet.db in backup with tested restore; activate.sh backup, dry-run, migrate before swap (DATA-05, DATA-02)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 48-07-PLAN.md — Health-page signal for the fleet.db fallback (owner-confirmable) (DATA-02)

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 48-06-PLAN.md — Freeze list and before/after migration replay tests (DATA-02, DATA-05)

### Phase 49: Per-Hardware OTA Registry

**Goal**: The owner can publish and schedule firmware per hardware type, and no frame can ever be offered a binary built for another type or an older build.
**Depends on**: Phase 48
**Requirements**: OTA-01, OTA-02, OTA-03
**Success Criteria** (what must be TRUE):

  1. The owner can publish and schedule a release for a chosen hardware type, and a simulated frame of each type is offered only a release of its own server-assigned type.
  2. Uploading a binary whose app descriptor or chip target does not match the declared type is rejected, and a lower build number than the current one is refused.
  3. The owner's decision on OTA signing (and any one-time cable flash it needs) is recorded before any second hardware is provisioned, and the chosen integrity check is verified on the device-side code path.
  4. The live frame's existing registry entries keep working unchanged (registry rewrite keeps a `*.pre-fleet` copy).

**Plans**: 11 plans
Plans:
**Wave 1**

- [x] 49-01-PLAN.md — Stdlib ESP image parser, synthetic image builder, separate firmware size bound (OTA-02)
- [x] 49-02-PLAN.md — OTA signing decision checkpoint (S/P/M/N) recorded in firmware/SIGNING.md, non-autonomous (OTA-03)
- [x] 49-03-PLAN.md — Per-type registry documents, pre-fleet copy, type-filtered reconcile/view (OTA-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 49-04-PLAN.md — Migrate publishing test fixtures to valid synthetic images (OTA-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 49-05-PLAN.md — publish_release image validation, grandfather rule, per-type build gate (OTA-01, OTA-02)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 49-06-PLAN.md — firmware_cli per-type, build-ordered import, check-image, docs (OTA-01, OTA-02)
- [x] 49-07-PLAN.md — byos type resolution, per-type offers, report stamp, reconcile-all (OTA-01)
- [x] 49-08-PLAN.md — Update page type chooser, EN/FR (OTA-01)
- [x] 49-09-PLAN.md — Release manifest hardware_type/build and CI descriptor check (OTA-01, OTA-02)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 49-10-PLAN.md — Hardware-free verification of the chosen signing option and bench checkpoint, non-autonomous (OTA-03)
- [x] 49-11-PLAN.md — End-to-end and live-frame regression, phase gates (OTA-01, OTA-02)

**UI hint**: yes

### Phase 50: Common Image Format

**Goal**: Images use one versioned container that any hardware type can carry, introduced without changing what existing frames receive.
**Depends on**: Phase 48
**Requirements**: IMG-01, IMG-02, IMG-03
**Success Criteria** (what must be TRUE):

  1. A written spec and golden fixtures define the container (width, height, palette, length, checksum), and encoder and decoder agree on them.
  2. A frame that does not announce support receives its current raw image byte for byte; a frame that announces support receives the new container.
  3. The reference reader rejects bad magic, version, length or panel dimensions before touching a display buffer, and still accepts the legacy raw format (host-tested firmware reader).

**Plans**: 5 plans

Plans:
- [x] 50-01-PLAN.md — Capture legacy reference constants from unmodified BYOS; legacy regression and junk-header tests
- [x] 50-02-PLAN.md — Canonical server/image_container.py, golden fixtures, manifest, generator, Python tests
- [x] 50-03-PLAN.md — Pure-C reference reader, host test over shared fixtures, runner fixture dir
- [x] 50-04-PLAN.md — BYOS X-Img-Fmt negotiation (import of canonical encoder), announce and no-state-effect tests
- [x] 50-05-PLAN.md — docs/IMAGE-FORMAT.md, README pointer, phase gates, Phase 50 close-out via GSD tooling

### Phase 51: Per-Device Config, Image and State

**Goal**: Each device has its own config, image, poll state, history and health, so that one frame's settings and failures never affect another.
**Depends on**: Phase 48, Phase 50
**Requirements**: FLT-01, FLT-02
**Success Criteria** (what must be TRUE):

  1. Two simulated devices each receive their own image from their own directory, and the live frame's files and responses are unchanged.
  2. The owner can trigger a poll for one device and set its quiet hours and timezone, and no other device's state changes.
  3. Each device shows its own history and health, and there is no fallback to a shared "default" device.

**Plans**: 13 plans in 8 waves

Plans:
- [x] 51-01-PLAN.md — device_dirs path chokepoint, add_device validation, CLI --state-path auto, two-device test fixture
- [x] 51-02-PLAN.md — per-device IANA timezone in device_config and tz-aware quiet-hours arithmetic
- [x] 51-03-PLAN.md — backup walks devices/<id>/ with WAL-safe history snapshots; layout and rollback notes
- [x] 51-04-PLAN.md — BYOS token to device resolution, per-device image/health/sleep, /img/<id>/<sha>.bin
- [x] 51-05-PLAN.md — route table device_scoped flag, /devices/<id> prefix matching, device_scope module
- [x] 51-06-PLAN.md — device-aware dispatch, page context, GET handlers, per-device poll-now, settings and quick switches
- [x] 51-07-PLAN.md — explicit-device airline, illustration, rule and calendar action handlers
- [x] 51-08-PLAN.md — prefix-aware nav, quick switches, flash actions, airlines, calendar sheet, previews, freshness
- [x] 51-09-PLAN.md — device selector (markup, no-JS switch, CSS, change handler, browser tests)
- [x] 51-10-PLAN.md — timezone field in the quiet-hours card, device-aware Poll section and rule forms
- [x] 51-11-PLAN.md — per-device Home, Health and History pages with empty and unreachable states
- [x] 51-12-PLAN.md — prefix crawl, end-to-end isolation tests, device-scoped route inventory for the auth phase
- [x] 51-13-PLAN.md — merge main, full suite and gates, verification items and owner checks
**UI hint**: yes

### Phase 52: Fleet Poll Cycle, Zones and Request Budget

**Goal**: The poll loop serves the whole fleet while total ADS-B requests stay within 1 per second.
**Depends on**: Phase 51
**Requirements**: FLT-03, FLT-04
**Success Criteria** (what must be TRUE):

  1. Devices sharing a zone are served by one upstream request set, and the budget holds across all providers and across overlapping poll processes (persisted, file-locked).
  2. A simulated 100-device fleet test with a fake clock shows at most 1 request per second.
  3. A provider failure or timeout for one device or zone leaves the other devices' images updated on time.

**Plans**: 7 plans (01–07)

### Phase 53: Detection Modes (Airport/Runway and Position/Radius)

**Goal**: A device can follow traffic on any French runway, or any aircraft around a chosen position, in addition to the Orly runway 3 behaviour.
**Depends on**: Phase 52
**Requirements**: DET-01, DET-02, DET-03
**Success Criteria** (what must be TRUE):

  1. The owner can pick an airport and runway from the committed France catalogue (real designators, rows without both thresholds absent) and the device follows it.
  2. Recorded Orly traffic replayed through the new runway logic gives the same decisions as the existing runway-3 geofence, and at least one parallel-runway airport is tested.
  3. A device set to a position and radius inside France shows aircraft around it; radius and country bounds are enforced, and coordinates sent to third parties are rounded.

**Plans**: TBD
**UI hint**: yes

### Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access

**Goal**: Invited users can sign in with Auth0, and every route enforces a minimum role and device ownership.
**Depends on**: Phase 48 (and Phase 51 for device-scoped routes)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-06
**Success Criteria** (what must be TRUE):

  1. An admin-created user can sign in with Auth0 (state, nonce, issuer, audience and expiry checked), the Auth0 subject is linked once and matched on subject afterwards, and an uninvited person cannot create an account.
  2. The shared password still works as a flagged, throttled legacy-admin fallback with a dated removal task, and sessions no longer depend on that password.
  3. A route by role by owner matrix test proves every route is default-deny, and a user gets a 404 for another user's device.
  4. Frames still authenticate with MAC and secret independently of Auth0, and the whole auth flow is tested against a local fake Auth0 including failure modes.

**Plans**: 9 plans
Plans:
**Wave 1**

- [x] 54-01-PLAN.md — fleet.db schema v2 sessions, race-free upgrade, fleet_migrate pending schema, invite-only identity resolution, CLI unlink-identity (AUTH-01, AUTH-02, AUTH-06)
- [x] 54-02-PLAN.md — loopback fake Auth0 with failure knobs and the pure OIDC client module (AUTH-01, AUTH-06)
- [x] 54-03-PLAN.md — login, refusal, error, interstitial and Account markup, user shell and legacy pill hook, FR strings (AUTH-01, AUTH-02, AUTH-03)

**Wave 2**

- [x] 54-04-PLAN.md — Access annotation, decide() and ownership gate, server-side session principal, session-backed shared-password login, baseline regeneration (AUTH-02, AUTH-03)

**Wave 3**

- [x] 54-05-PLAN.md — Auth0 start, callback, invite-only sign-in and sign-out handlers with the full failure-mode suite (AUTH-01)

**Wave 4**

- [x] 54-06-PLAN.md — Account route, user shell and 404 pages, real-browser sign-in/sign-out proof (AUTH-01, AUTH-03)

**Wave 5**

- [x] 54-07-PLAN.md — legacy-admin flag, audit, fail-closed startup, removal of the stateless token API (AUTH-02, AUTH-06)
- [x] 54-08-PLAN.md — route x role x owner matrix with probe family, frame-auth independence tests (AUTH-03, AUTH-06)

**Wave 6**

- [x] 54-09-PLAN.md — Caddy query redaction, env and README owner steps, handoff record for the work after the device-scoped routes (AUTH-01, AUTH-02, AUTH-03, AUTH-06)

Real `/d/<id>/...` routes and their matrix rows are completed after Phase 51; see 54-HANDOFF.md.
**UI hint**: yes

### Phase 55: Frame Pairing, Admin Console and Reduced User View

**Goal**: Admins can add frames to users and manage the whole fleet; ordinary users manage only their own frames with a simpler view.
**Depends on**: Phase 54
**Requirements**: AUTH-04, AUTH-05
**Success Criteria** (what must be TRUE):

  1. An admin can pair a new frame to a user with a short on-panel code that is single-use, expires, is claimed atomically, and is recorded in an audit log.
  2. The admin console shows every device with owner, hardware, last seen, battery and firmware, and lets the admin manage users, reassign or retire devices and manage releases.
  3. An ordinary user sees only their own frames with fewer options and no fleet or release controls.

**Plans**: TBD
**UI hint**: yes

### Phase 56: Per-Hardware Rendering, Battery Profiles, Health and Credits

**Goal**: What a frame displays and how its health is judged follow its hardware profile, and data sources are credited.
**Depends on**: Phase 48, Phase 50, Phase 51 (final legacy battery numbers need Phase 47)
**Requirements**: HWR-01, HWR-02
**Success Criteria** (what must be TRUE):

  1. A simulated second-geometry frame is rendered natively from its profile, and a golden-image baseline shows the legacy render is unchanged.
  2. Battery thresholds and health views come from the device's profile, with the provenance of each battery number recorded.
  3. A credits page generated from one data file cites adsb.fi (with link), adsb.lol, adsbdb and OurAirports, and contact with adsb.fi / adsb.lol about multi-zone use is recorded.

**Plans**: TBD
**UI hint**: yes

### Phase 57: Combined Legacy-Frame Firmware Release

**Goal**: The live frame receives, in one OTA, every firmware change the fleet needs.
**Depends on**: Phase 47 (v1.1, must be closed), Phase 49, Phase 50, Phase 54
**Requirements**: OTA-04
**Success Criteria** (what must be TRUE):

  1. One release bundles the image-header reader, any hardware header and recovery after repeated 401, and it is published only after Phase 47 allows it.
  2. After the OTA, the live frame still wakes on its cadence and displays a correct image, and it is served the new container only after announcing support.
  3. A frame that fails the update stays on the previous working firmware.

**Plans**: TBD

### Phase 58: Second Hardware (Shortlist, Spike, Purchase, Validate)

**Goal**: A second hardware type is chosen on evidence and proven on a real unit.
**Depends on**: Phase 49, Phase 50, Phase 56
**Requirements**: HW2-01, HW2-02
**Success Criteria** (what must be TRUE):

  1. The owner can choose from a documented shortlist after a time-boxed ESP-IDF panel-driver spike, with the choice within the hardware budget; no purchase happens before the spike.
  2. The evaluation unit is cable-flashed, receives a real OTA, and shows a native layout.
  3. A measured battery sample is recorded and the battery model for the new type is rebuilt from it.

**Plans**: TBD

### Phase 59: Comment-History Debt

**Goal**: The comment-history guard passes without a growing baseline, and no v1.2 phase has added violations.
**Depends on**: Phase 48 (guard checked before it starts; runs last)
**Requirements**: DEBT-01
**Success Criteria** (what must be TRUE):

  1. `scripts/check_comment_history.py check` passes in CI, or its baseline is strictly smaller than before v1.2.
  2. The check output measured before Phase 48 is recorded, and no v1.2 phase raised it.

**Plans**: TBD

### Phase 60: Device Co-Management

**Goal**: A frame keeps exactly one primary owner and can also be managed by co-managers, added by the owner or by an admin.
**Depends on**: Phase 51, Phase 54, Phase 55
**Requirements**: AUTH-08
**Success Criteria** (what must be TRUE):

  1. A co-manager can view and change a shared frame's settings like its owner, but cannot retire it, reassign it or remove the owner.
  2. The owner of a frame and an admin can add or remove a co-manager among users already invited to the platform; a co-manager cannot add others.
  3. A user who is neither owner nor co-manager still gets a 404 for the frame, and the route x role x owner matrix covers the co-manager rows.
  4. The one-primary-owner rule from the fleet data model still holds, and adding or removing a co-manager is recorded in the audit log.

**Plans**: TBD
**UI hint**: yes

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 48. Fleet Data Model, Roles and Live-Frame Migration | v1.2 | 8/8 | Complete   | 2026-10-29 |
| 49. Per-Hardware OTA Registry | v1.2 | 11/11 | Human verification pending (OTA-03 bench check deferred) | - |
| 50. Common Image Format | v1.2 | 5/5 | Complete    | 2026-10-30 |
| 51. Per-Device Config, Image and State | v1.2 | 13/13 | Complete    | 2026-10-30 |
| 52. Fleet Poll Cycle, Zones and Request Budget | v1.2 | 0/0 | Not started | - |
| 53. Detection Modes | v1.2 | 0/0 | Not started | - |
| 54. Auth0 Sign-In, Local Roles and Default-Deny Access | v1.2 | 9/9 | Deployed and verified on the real tenant 2026-10-30; legacy-admin removal and post-Phase-51 matrix rows pending (see 54-HANDOFF.md) | - |
| 55. Frame Pairing, Admin Console and Reduced User View | v1.2 | 0/0 | Not started | - |
| 56. Per-Hardware Rendering, Battery Profiles, Health and Credits | v1.2 | 0/0 | Not started | - |
| 57. Combined Legacy-Frame Firmware Release | v1.2 | 0/0 | Not started (gated on Phase 47) | - |
| 58. Second Hardware | v1.2 | 0/0 | Not started | - |
| 59. Comment-History Debt | v1.2 | 0/0 | Not started | - |
| 60. Device Co-Management | v1.2 | 0/0 | Not started | - |
