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
  - The combined firmware OTA to the legacy frame (Phase 57, OTA-04). No firmware change reaches the live frame before this gate, nor before the `firmware/SIGNING.md` bench procedure has passed on a non-live unit (owner decision, 2026-10-31).
  - The legacy-frame battery numbers feeding the hardware profile (Phase 56, HWR-01) are final only after Phase 47.
- Every deploy before then, if the owner allows it, must run the previous release correctly on post-migration state (forward-only, expand-only).

## Phases

**Phase Numbering:**

- Integer phases are planned milestone work, continuing from v1.1 (Phase 47).
- Decimal phases are urgent insertions created only when needed.

- [x] **Phase 48: Fleet Data Model, Roles and Live-Frame Migration** - One fleet database with users, roles, devices and hardware profiles; the live frame migrated without any visible change. (completed 2026-10-29)
- [x] **Phase 49: Per-Hardware OTA Registry** - Firmware releases are published, scheduled and offered per hardware type, with integrity checks. (closed 2026-10-31 by the owner; criteria 1, 2, 4 verified 2026-10-30; the device-side half of criterion 3 is carried to Phase 58, which has the bench unit)
- [x] **Phase 50: Common Image Format** - A versioned image container served only to frames that announce support, with a legacy-safe firmware reader specified. (completed 2026-10-30)
- [x] **Phase 51: Per-Device Config, Image and State** - Every device has its own config, image, history and health, and the BYOS serves each frame its own image.
- [x] **Phase 52: Fleet Poll Cycle, Zones and Request Budget** - One upstream ADS-B request per zone under a persisted global 1 req/s budget.
- [x] **Phase 53: Detection Modes (Airport/Runway and Position/Radius)** - Devices can follow any French runway or any position within a bounded radius. (criteria 1-3 verified in code 2026-10-31; deployed by CI on merge to main 2026-10-31 20:20 UTC; live Orly frame checked by the owner and unchanged; policy numbers validated 2026-11-01; real-panel render of runway mode seen and position mode tested by the owner 2026-11-01; closed 2026-11-01)
- [x] **Phase 54: Auth0 Sign-In, Local Roles and Default-Deny Access** - Invite-only sign-in with local roles and a proven route and ownership matrix. (closed 2026-10-31 by the owner after production tests; the real per-device rows of the matrix, AUTH-03, are carried to Phase 55)
- [x] **Phase 55: Frame Pairing, Admin Console and Reduced User View** - Admins pair frames to users and manage the fleet; users see only their own frames with fewer options.
- [x] **Phase 56: Per-Hardware Rendering, Battery Profiles, Health and Credits** - Rendering and health follow the hardware profile; credits page published. (closed 2026-10-31; 11/11 plans, criteria 1-3 verified, merged in #257. Owner follow-ups, not gaps: send the adsb.fi / adsb.lol contact draft once the fleet exceeds 10 users, non-blocking landscape preview follow-up)
- [ ] **Phase 57: Combined Legacy-Frame Firmware Release** - One OTA release gives the live frame the new image reader and 401 recovery. Gated on Phase 47 and on the OTA signing bench check passing on a non-live unit.
- [ ] **Phase 58: Second Hardware (Shortlist, Spike, Purchase, Validate)** - A second hardware type chosen after a driver spike and validated on a real unit.
- [ ] **Phase 59: Comment-History Debt** - The comment-history guard debt is cleared or only shrinks.
- [x] **Phase 60: Device Co-Management** - A frame keeps one primary owner and gains co-managers whom the owner or an admin can add. (9 plans, merged (#276, #277, #279, #282) and deployed by CI 2026-11-02; production checks reported done by the owner, see 60-HANDOFF.md)
- [x] **Phase 61: Companion UX and UI Overhaul (Admin and Users)** - Navigation, page structure, the admin console, the user view and the sign-in and invitation flows are reworked from observed friction and validated by the owner on a phone and a desktop, in English and French. (added 2026-11-02 at the owner's request; Phase 59 stays last)
- [x] **Phase 62: Plane Screen Redesign (giant-lettering design)** - The flight screens and the generic status screens use the giant-lettering design in portrait and landscape, from the validated design brief. (added 2026-11-08 at the owner's request; Phase 59 stays last; 13 of 13 plans done; the owner confirmed the real-panel check and kept layout B as the default, 2026-11-10)
- [x] **Phase 63: Fast CI** - The CI test job drops from about 27 minutes to 10 minutes or less by running independent test groups in parallel jobs and trimming the slowest tests, with no test skipped, disabled or weakened.

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
  3. The owner's decision on OTA signing (and any one-time cable flash it needs) is recorded before any second hardware is provisioned, and the chosen integrity check is verified on the device-side code path. (Decision recorded 2026-10-29, option S, in `firmware/SIGNING.md`. The device-side verification is carried to Phase 58 by the owner's decision of 2026-10-31.)
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

**Plans**: 12 plans
Plans:
**Wave 1**

- [x] 53-01-PLAN.md — OurAirports France catalogue: committed raw subset, offline build script, parallel half-width rule, typed loader and search (DET-01, DET-02)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 53-02-PLAN.md — Runway detection spec with frozen Orly override, replay proof (fixtures plus deterministic sweep) and kill switch (DET-01, DET-02)

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 53-03-PLAN.md — Position mode: airborne gate, radius_km bounds, France box, single rounding choke point (DET-03)

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 53-04-PLAN.md — Expand-only storage of the detection setting and validated selection helpers (DET-01, DET-03)

**Wave 5** *(blocked on Wave 4 completion)*

- [x] 53-05-PLAN.md — Per-device fleet resolver, spec-driven selection and frame tag text (DET-01, DET-02, DET-03)

**Wave 6** *(blocked on Wave 5 completion)*

- [x] 53-06-PLAN.md — /detection route, access matrix and the runway half of the page (DET-01)
- [x] 53-07-PLAN.md — OurAirports COMPLIANCE section, corrected credits text and drift test (DET-01, DET-03)

**Wave 7** *(blocked on Wave 6 completion)*

- [x] 53-08-PLAN.md — Position panel, minimal location form and leave-guard handling (DET-03)
- [x] 53-09-PLAN.md — Display Runway card removed; read-only Detection cards on Display and Device (DET-01)

**Wave 8** *(blocked on Wave 7 completion)*

- [x] 53-10-PLAN.md — Browser tests: no-JS flow, hidden-panel submit, 360 px measurements, dirty bar; legacy browser tests updated (DET-01, DET-03)
- [x] 53-12-PLAN.md — Remaining non-browser tests and test-support helpers updated for the removed Display Runway card (DET-01)

**Wave 9** *(blocked on Wave 8 completion)*

- [x] 53-11-PLAN.md — Kill-switch integration test and phase-level gates (DET-01, DET-02, DET-03)

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

**Plans**: 14 plans
Plans:
**Wave 1**

- [x] 55-01-PLAN.md — Role-conditional reductions of Display, Home, Health and navigation, settings form policy (AUTH-05)
- [x] 55-02-PLAN.md — fleet.db schema 3 (pending_devices, audit_log, locations.owner_user_id), typed API, directory wipe (AUTH-04, AUTH-05)
- [x] 55-03-PLAN.md — Pairing code module and deterministic pairing and retired screens (AUTH-04)

**Wave 2**

- [x] 55-04-PLAN.md — Ownership gate flip, owner-aware device scope, Account frames list, matrix update (AUTH-05)
- [x] 55-05-PLAN.md — fleet_ops: register, atomic claim, retire, re-activate, reassign (AUTH-04, AUTH-05)

**Wave 3**

- [x] 55-06-PLAN.md — Real-handler HTTP layer of the access matrix (AUTH-05)
- [x] 55-07-PLAN.md — BYOS pending and retired path, CLI verbs, backup and freeze coverage (AUTH-04)
- [x] 55-08-PLAN.md — Per-session CSRF mechanism and retrofit of release and destructive POSTs (AUTH-05)

**Wave 4**

- [x] 55-09-PLAN.md — Console shell: throttle, audit helper, flash, navigation, route seams (AUTH-04, AUTH-05)

**Wave 5**

- [x] 55-10-PLAN.md — Fleet page, register and pair handlers with throttling (AUTH-04, AUTH-05)
- [x] 55-11-PLAN.md — Retire, re-activate, reassign, Audit log page, release audit events (AUTH-04, AUTH-05)
- [x] 55-12-PLAN.md — Users page and actions with last-admin guards (AUTH-05)
- [x] 55-13-PLAN.md — Locations for both roles and Display location picker (AUTH-05)

**Wave 6**

- [x] 55-14-PLAN.md — Browser tests, full verification, deploy docs and phase hand-off (AUTH-04, AUTH-05)

**UI hint**: yes

### Phase 56: Per-Hardware Rendering, Battery Profiles, Health and Credits

**Goal**: What a frame displays and how its health is judged follow its hardware profile, and data sources are credited.
**Depends on**: Phase 48, Phase 50, Phase 51 (final legacy battery numbers need Phase 47)
**Requirements**: HWR-01, HWR-02
**Success Criteria** (what must be TRUE):

  1. A simulated second-geometry frame is rendered natively from its profile, and a golden-image baseline shows the legacy render is unchanged.
  2. Battery thresholds and health views come from the device's profile, with the provenance of each battery number recorded.
  3. A credits page generated from one data file cites adsb.fi (with link), adsb.lol, adsbdb and OurAirports, and contact with adsb.fi / adsb.lol about multi-zone use is recorded (drafted; sending deferred by the owner until the fleet exceeds 10 users).

**Plans**: 11 plans
Plans:
**Wave 1**

- [x] 56-01-PLAN.md — Golden SHA-256 baseline of the legacy render (HWR-01)
- [x] 56-02-PLAN.md — Battery provenance, inks, layout family, theme ink accessors (HWR-01)
- [x] 56-03-PLAN.md — Public bilingual credits page from one data file (HWR-02)
- [x] 56-04-PLAN.md — Policy functions take profile thresholds and curve (HWR-01)

**Wave 2**

- [x] 56-05-PLAN.md — Provider contact draft (to send) and COMPLIANCE credits (HWR-02)
- [x] 56-06-PLAN.md — Size-aware canvas primitives and landscape hold screens (HWR-01)
- [x] 56-07-PLAN.md — Companion battery and health follow the device profile (HWR-01)

**Wave 3**

- [x] 56-08-PLAN.md — Landscape card composition and entry point (HWR-01)
- [x] 56-11-PLAN.md — Theme picker filtered by profile inks (HWR-01)

**Wave 4**

- [x] 56-09-PLAN.md — Profile dispatch in build_canvas, --hardware preview (owner preview approved)

**Wave 5**

- [x] 56-10-PLAN.md — Poll-cycle profile seam and BYOS serving of 800x480 (HWR-01)
**UI hint**: yes

### Phase 57: Combined Legacy-Frame Firmware Release

**Goal**: The live frame receives, in one OTA, every firmware change the fleet needs.
**Depends on**: Phase 47 (v1.1, must be closed), Phase 49, Phase 50, Phase 54, and the OTA-03 device-side signing check (see the precondition below)
**Requirements**: OTA-04
**Precondition (owner decision, 2026-10-31)**: no signed OTA reaches the live frame until the bench procedure of `firmware/SIGNING.md` has passed on a non-live unit: a correctly signed image is accepted, a wrongly signed image is refused with the unit keeping its firmware and the next poll reporting `fail-image`. The unit is either the Phase 58 evaluation unit or an earlier spare ESP32-S3 board. This check was carried out of Phase 49 and is otherwise run in Phase 58; Phase 57 does not start its release until it has passed, because a wrong signing configuration could leave the only live frame unreachable by OTA and recoverable only by cable.
**Success Criteria** (what must be TRUE):

  1. One release bundles the image-header reader, any hardware header and recovery after repeated 401, and it is published only after Phase 47 allows it and the signing bench check has passed on a non-live unit.
  2. After the OTA, the live frame still wakes on its cadence and displays a correct image, and it is served the new container only after announcing support.
  3. A frame that fails the update stays on the previous working firmware.

**Plans**: TBD

### Phase 58: Second Hardware (Shortlist, Spike, Purchase, Validate)

**Goal**: A second hardware type is chosen on evidence and proven on a real unit.
**Depends on**: Phase 49, Phase 50, Phase 56
**Requirements**: HW2-01, HW2-02
**Success Criteria** (what must be TRUE):

  1. The owner can choose from a documented shortlist after a time-boxed ESP-IDF panel-driver spike, with the choice within the hardware budget; no purchase happens before the spike.
  2. The evaluation unit is cable-flashed, receives a real OTA, and shows a native layout. Before it takes any role in the fleet, the `firmware/SIGNING.md` bench procedure is run on it (carried from Phase 49): a correctly signed image is accepted, a wrongly signed image is refused with the unit keeping its firmware and the next poll reporting `fail-image`, and the `fail-image` / `fail-floor` tokens and a wrong-hardware rollback are seen to round-trip into the right type's registry.
  3. A measured battery sample is recorded and the battery model for the new type is rebuilt from it.

**Plans**: 5 plans (58-01, 58-02 and 58-05 done, 58-05 code only on 2026-11-14: gated 800x480 profile, image size from the panel Kconfig value, 800x480 screens, ee02 section-level identical; the evaluation unit was ordered on 2026-11-07; 58-03 and 58-04 wait for the unit on the bench, 58-03 Task 1 is code only and done 2026-11-14: driver promoted behind a Kconfig choice, second board profile, flash-second.sh, ee02 image proven unchanged)
Plans:
**Wave 1**

- [x] 58-01-PLAN.md — Costed shortlist from opened product pages, cost-first, landed cost vs 100 EUR TTC (HW2-01)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 58-02-PLAN.md — 1-day driver spike, trial driver in the IDF container, owner purchase decision checkpoint (HW2-01)

**Wave 3** *(BLOCKED: owner purchase agreement)*

- [ ] 58-03-PLAN.md — Cable flash of the evaluation unit, real OTA, full SIGNING.md bench before any fleet role (HW2-02)
- [x] 58-05-PLAN.md — 800x480 data path (code only, no hardware): the unit's gated hardware profile, device image size from the panel Kconfig value, 800x480 fault and updating screens, EE02 unchanged proof; run BEFORE 58-03 Task 2/3 and 58-04 (HW2-02)

**Wave 4** *(BLOCKED)*

- [ ] 58-04-PLAN.md — Native landscape layout, Phase 55 real-panel pairing test, battery sample and rebuilt model (HW2-02)

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

**Plans**: 9 plans
Plans:
- [x] 60-01-PLAN.md — Migration v4 (expand-only device_co_managers table) and the fleet_db co-manager API, schema-3 test fix, rollback README paragraph
- [x] 60-02-PLAN.md — Reassign, retire, hard-delete cascades with per-user audit; location rule against the device owner
- [x] 60-03-PLAN.md — Ownership gate accepts co-managers; owner-or-admin access kind; dispatcher wiring
- [x] 60-04-PLAN.md — Device list, Detection location scope (D-04) and HTTP proof a co-manager acts like the owner
- [x] 60-05-PLAN.md — Add, remove, leave routes with CSRF, single refusal, audit, flash, labels and French
- [x] 60-06-PLAN.md — Co-managers card on Home, Account Shared mark and leave toast, CSS and i18n
- [x] 60-07-PLAN.md — Access matrix co-manager rows and live-frame immutability test
- [x] 60-08-PLAN.md — Browser tests at 360 px (layout, tap targets, leave flow, freshness)
- [x] 60-09-PLAN.md — Full gate run, constraint diff guard and owner handoff
**UI hint**: yes

### Phase 61: Companion UX and UI Overhaul (Admin and Users)

**Goal**: The companion is clear and pleasant to use for an administrator and for an invited user: navigation, page structure, the admin console, the user view and the sign-in and invitation flows are reworked from observed friction and validated by the owner on a real phone and a desktop, in English and French.
**Depends on**: Phase 54, Phase 55, Phase 60 (all closed). Runs before Phase 59, which stays last.
**Requirements**: UX-01, UX-02, UX-03, UX-04
**Success Criteria** (what must be TRUE):

  1. The owner's task-based walkthrough of the companion, as an administrator and as an invited user, on a phone and a desktop and in both languages, is recorded with each friction point ranked, and the changes made are traced to those findings.
  2. Navigation and page structure are reworked against an updated design contract (the companion's design system), and the number of steps for each core task is recorded before and after.
  3. An administrator completes the core console tasks without help: read the fleet state, invite a user, pair a frame, retire, reassign or re-activate a frame, add a co-manager and read the audit log. An invited user sees only their own frames, understands each frame's state at a glance and meets no administrator concept.
  4. A user whose Auth0 email is not verified gets a message that says so instead of the "not invited" page, the first arrival of an invited user is guided, and sign-in errors say what to do next.
  5. Both languages, the 360 px width and the 44 px tap targets hold, the existing browser tests stay green with new ones for the changed flows, and the owner validates on the deployed companion.

**Plans**: 34 plans (15 built and merged, 61-13 the owner checkpoint kept open and last, and 18 added by the owner validation on 2026-11-03)
Plans:
**Wave 1**

- [x] 61-01-PLAN.md — Owner-validation ledger, status-dot resolver, sprite glyphs and hollow dot (UX-01, UX-02, UX-03)
- [x] 61-05-PLAN.md — Role landing, user 303 from un-prefixed pages, signed-in /login redirect, matrix rows (UX-01, UX-03, UX-04)

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 61-02-PLAN.md — Shared modal component (dialog helpers, modal.js, CSS) (UX-02)
- [x] 61-14-PLAN.md — Remove the Console section chip rows (UX-01, UX-02)

**Wave 3**

- [x] 61-03-PLAN.md — Shared entity list and row menu (UX-02, UX-03)

**Wave 4**

- [x] 61-04-PLAN.md — Console and My views spaces, tab bars, sidebars, space switch, Locations 360px fix (UX-01, UX-02, UX-03)

**Wave 5**

- [x] 61-06-PLAN.md — Fleet list with add, retire, reassign and re-activate dialogs (UX-02)
- [x] 61-08-PLAN.md — Users list with invite and manage-user dialogs (UX-02)
- [x] 61-09-PLAN.md — Frame switcher and user Home (UX-03)

**Wave 6**

- [x] 61-07-PLAN.md — Manage access dialog, co-managers leave Home (UX-02, UX-03)
- [x] 61-11-PLAN.md — Sign-in messages, unverified email, first-arrival guidance (UX-04)

**Wave 7**

- [x] 61-10-PLAN.md — Account My frames, leave dialog, merged Location and detection card (UX-03)
- [x] 61-15-PLAN.md — Audit items in scope: Device LED switch box, Health check-in wording, compact empty states (UX-01, UX-02, UX-03)

**Wave 8**

- [x] 61-12-PLAN.md — Step-count record, friction traceability, cross-page sweep (UX-01..UX-04)

**Wave 9**

- [x] 61-16-PLAN.md — Owner follow-ups: time zone in the Location and detection card, 44 px desktop targets, compact History and table empty states (UX-02, UX-03)

**Revision 2 (owner validation of the deployed companion: V0-V10, D16-D22; UI-SPEC revision 2). Each plan commits green states; the stylesheet and render baseline are shared, so most waves hold one plan.**

**Revision 2, wave 1**

- [x] 61-17-PLAN.md — Admin-only device-scoped access kind: Health, airline editing, /airlines/manage, /locations redirect, ledger R2-1..R2-18 (UX-01, UX-03)
- [x] 61-18-PLAN.md — A frame's own position (private location row, copy-on-write) and poll-position parity tests, expand-only (UX-03)

**Revision 2, wave 2**

- [x] 61-19-PLAN.md — Administrator personal space follows the user's frame rule, Fleet entry points, foreign-frame notice (UX-01, UX-03)

**Revision 2, wave 3**

- [x] 61-20-PLAN.md — save_place on POST /detection: validated write of the frame's place and detection choice (UX-03)

**Revision 2, wave 4**

- [x] 61-21-PLAN.md — Navigation model: one personal nav for everyone, Console with Health, Device and Airline editor, new labels and glyphs (UX-01, UX-02, UX-03)

**Revision 2, wave 5**

- [x] 61-22-PLAN.md — Two-segment Console / My frame switch, personal-space parity and content scrub (UX-01, UX-02, UX-03)

**Revision 2, wave 6**

- [x] 61-23-PLAN.md — Frame chip and card sheet replacing the frame drop-down; Console all-frames chip (UX-01, UX-03)

**Revision 2, wave 7**

- [x] 61-24-PLAN.md — Vendored Leaflet 1.9.4, per-route CSP and Permissions-Policy, credits and COMPLIANCE.md (UX-03)

**Revision 2, wave 8**

- [x] 61-25-PLAN.md — Location and detection page, no-script complete (UX-03)

**Revision 2, wave 9**

- [x] 61-26-PLAN.md — Map interaction: pin, airports, search, use my position, failure modes (UX-03)

**Revision 2, wave 10**

- [x] 61-27-PLAN.md — Quiet hours dialog on Home and POST /quick/quiet-hours/window (UX-03)

**Revision 2, wave 11**

- [x] 61-33-PLAN.md — Display loses the location card, the location picker and the time zone (UX-03)

**Revision 2, wave 12**

- [x] 61-34-PLAN.md — Display loses quiet hours; amber-dot notification on Home with a mailto contact to an administrator (UX-01, UX-03)

**Revision 2, wave 13**

- [x] 61-28-PLAN.md — Personalisation page: five cards, Look radio cards, Refresh and Screen, wake-interval access decision point (UX-02, UX-03)

**Revision 2, wave 14**

- [x] 61-29-PLAN.md — Special looks and Calendar cards, Remove confirm dialog (UX-02, UX-03)

**Revision 2, wave 15**

- [x] 61-30-PLAN.md — Airline collection read model and page (read-only, everyone) (UX-03)

**Revision 2, wave 16**

- [x] 61-31-PLAN.md — Airline editor in the Console (administrator only), delete-resolution dialog (UX-01, UX-03)

**Revision 2, wave 17**

- [x] 61-32-PLAN.md — Revision 2 step counts, cross-page sweep, traceability and the full run (UX-01..UX-04)

**Revision 2, wave 18**

- [x] 61-13-PLAN.md — Owner validation on the deployed companion, both rounds (checkpoint, no deploy step) (UX-01..UX-04)

**Notes**: The extent of the structural change (how far navigation and pages may move, and whether the existing companion architecture stays as is) is settled in discuss-phase; no new runtime dependency is assumed. SEED-011 (distinct message for an unverified email) is absorbed by UX-04. SEED-012 (the admin invite creating the Auth0 account) stays an owner decision and is not part of this phase unless the owner brings it in. Phase 44 of v1.1 is the model for the walkthrough method.
**UI hint**: yes

### Phase 62: Plane Screen Redesign (giant-lettering design)

**Goal**: The e-ink plane screens read from 2-3 m: the destination is set in giant lettering behind the aircraft, a diagonal band and a per-state colour carry the mode, and the generic status screens share one calm layout, in portrait (1200x1600) and landscape (800x480), without changing a pixel of the current layout until the owner chooses.
**Depends on**: Phase 56 (per-hardware rendering, closed). Runs before Phase 59, which stays last. Touches no file of Phase 47, 47.1 or `hardware/`.
**Requirements**: PSR-01, PSR-02, PSR-03, PSR-04, PSR-05, PSR-06, PSR-07, PSR-08, PSR-09
**Source**: `.planning/notes/plane-screen-design-brief.md` (mock-ups in `.planning/notes/plane-screen-design-brief/`, scripts in `design-exploration/plane-screen/`).
**Open decisions** (settled in discuss-phase): the three aircraft layouts (A nose and tail, B whole aircraft, C band) and the default; the arrival colour; the status screens in landscape; the real-panel contrast; vendoring the Anton font.

Plans: 13 plans in 7 waves
- [x] 62-01-PLAN.md - Anton vendoring, pairing registry, giant package skeleton (wave 1)
- [x] 62-02-PLAN.md - layout ids and the per-frame layout device-config key (wave 1)
- [x] 62-03-PLAN.md - automatic destination splitter (wave 2)
- [x] 62-04-PLAN.md - aircraft crop points and placement (wave 2)
- [x] 62-05-PLAN.md - stretched binary lettering, pairing fields, giant palette check (wave 3)
- [x] 62-06-PLAN.md - portrait layouts B, A, A+diagonal, dispatch, poll-cycle threading (wave 4)
- [x] 62-07-PLAN.md - layout C and the landscape family (wave 5)
- [x] 62-08-PLAN.md - seven calm status screens, portrait and landscape (wave 5)
- [x] 62-10-PLAN.md - layout-aware previews and render CLI option (wave 5)
- [x] 62-09-PLAN.md - regenerated firmware masks, host tests (wave 6)
- [x] 62-11-PLAN.md - companion Layout view, pairing picker, EN/FR (wave 6)
- [x] 62-12-PLAN.md - giant golden manifest and docs (wave 6)
- [x] 62-13-PLAN.md - owner real-panel check and handoff (wave 7, checkpoint)

### Phase 63: Fast CI

**Goal**: The `Lint, test, coverage, attribution` check finishes in 10 minutes or less (it takes about 27 minutes today) with every test still running and every existing guard still enforced.
**Depends on**: Nothing. Runs alongside Phase 61 and Phase 62, and never modifies a Phase 61 test file without the owner's agreement. Touches no file of Phase 47 or `hardware/`, and leaves the production deploy job and its approval step as they are.
**Requirements**: CIS-01, CIS-02, CIS-03, CIS-04, CIS-05
**Baseline** (measured 2026-11-10, run 42770577886 and a local 4-core run; the runner has 4 xdist workers):
- Job 27.5 min, of which the pytest step is 26.5 min and everything else (setup, Playwright, ruff, mypy, guards) about 1 min. 12,821 tests.
- Browser tests: about 2,800 tests, 17 min 47 s alone on 4 cores (70 min of summed test time). One file, `companion/test_browser_overhaul_sweep.py`, is 739 tests and 11 min summed; `test_browser_components_page.py` is 59 tests and 7.8 min summed.
- Everything else: about 10,900 tests in 9 min 40 s on 4 cores.
- Three firmware size-bound tests take about 51 s each; `server/test_golden_giant_render.py` has one test of 22 s.
- xdist scales almost linearly (3,757-test subset: 478 s with 1 worker, 244 s with 2, 134 s with 4, 120 s with 8). Coverage costs about 1% on server tests and about 12% on browser tests.
**Success criteria** (what must be TRUE):
1. The median wall time of the CI test checks over five consecutive pull-request runs is 10 minutes or less.
2. The number of executed tests is at least 12,821 and no test is skipped, deselected, quarantined or marked slow-optional to get there.
3. Coverage from every job is combined and the existing `fail_under` floor is applied unchanged to the combined result.
4. A missing browser still fails CI, the non-loopback network guard stays on in every job, and `companion/test_suite_guards.py` is unchanged and green.
5. The `deploy` job, its `production` environment approval and its dependency on the test result are unchanged.
**Plan outline** (detailed plans are made in plan-phase):
- Split the job into parallel jobs: static checks, non-browser tests, and browser tests in shards; a final aggregate job that keeps the current required check name, combines coverage and applies the floor.
- Make the slowest non-browser tests cheaper without dropping cases.
- Reduce the cost of the large browser sweep and components-page files by agreement with the owner and with Phase 61.
- Record before and after timings in the documentation.
**Must not break**: every item in success criteria 2-5, plus local `./scripts/run-all-tests.sh` as the single entry point that matches CI.

Plans: 6 plans in 5 waves
- [x] 63-01-PLAN.md - timing script, baseline record, group and shard tooling, partial-run knobs (wave 1)
- [x] 63-02-PLAN.md - split ci.yml into parallel jobs with an aggregate check, combined coverage floor, totals gate (wave 2)
- [x] 63-03-PLAN.md - matrix shards, 5 browser and 2 non-browser, balanced from measured file times (wave 3)
- [x] 63-04-PLAN.md - cheaper slow firmware and golden-render tests, nothing dropped (wave 3)
- [x] 63-05-PLAN.md - owner decision on the two large browser files Phase 61 also touches: left unchanged (wave 4, checkpoint)
- [x] 63-06-PLAN.md - five green runs, before and after record, documentation (wave 5)

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 48. Fleet Data Model, Roles and Live-Frame Migration | v1.2 | 8/8 | Complete   | 2026-10-29 |
| 49. Per-Hardware OTA Registry | v1.2 | 11/11 | Complete, closed by the owner; OTA-03 device-side bench check carried to Phase 58 | 2026-10-31 |
| 50. Common Image Format | v1.2 | 5/5 | Complete    | 2026-10-30 |
| 51. Per-Device Config, Image and State | v1.2 | 13/13 | Complete    | 2026-10-30 |
| 52. Fleet Poll Cycle, Zones and Request Budget | v1.2 | 7/7 | Complete, merged (#253) and deployed: carried by the Phase 56 deploy of 2026-10-31 (its commit contains #253) and by the later Phase 53 deploys | 2026-10-31 |
| 53. Detection Modes | v1.2 | 12/12 | Complete, closed 2026-11-01; deployed by CI on merge 2026-10-31 20:20 UTC (see 53-VERIFICATION.md) | 2026-11-01 |
| 54. Auth0 Sign-In, Local Roles and Default-Deny Access | v1.2 | 9/9 | Complete, closed by the owner after production tests (2026-10-30 and 2026-10-31); AUTH-03 per-device matrix rows carried to Phase 55 (see 54-HANDOFF.md) | 2026-10-31 |
| 55. Frame Pairing, Admin Console and Reduced User View | v1.2 | 14/14 | Complete: merged and deployed 2026-10-31, verified in code and by the owner in production; real-panel pairing test waits for the second hardware (see 55-HANDOFF.md) | 2026-11-01 |
| 56. Per-Hardware Rendering, Battery Profiles, Health and Credits | v1.2 | 11/11 | Complete, merged (#257) and deployed 2026-10-31; verification passed, two owner follow-ups open (see 56-VERIFICATION.md) | 2026-10-31 |
| 57. Combined Legacy-Frame Firmware Release | v1.2 | 0/0 | Not started (gated on Phase 47 and on the OTA signing bench check) | - |
| 58. Second Hardware | v1.2 | 3/5 | In progress (part 1 done; one Seeed EE04 unit ordered 2026-11-07): 58-03/58-04 wait for the unit on the bench | - |
| 59. Comment-History Debt | v1.2 | 0/0 | Not started | - |
| 60. Device Co-Management | v1.2 | 9/9 | Complete: merged (#276, #277, #279, #282) and deployed 2026-11-02; production checks reported done by the owner (see 60-HANDOFF.md) | 2026-11-02 |
| 61. Companion UX and UI Overhaul (Admin and Users) | v1.2 | Complete | Complete (owner validated on the deployed companion, 2026-11-13; follow-up plans 61-100 to 61-129 recorded in the validation ledger) | 2026-11-13 |
| 62. Plane Screen Redesign (giant-lettering design) | v1.2 | 13/13 | Complete | 2026-11-10 |
| 63. Fast CI | v1.2 | 6/6 | Complete: merged (#319, #320, #322); test check median 9.0 min against 27.4 over five green runs, nothing skipped; the large browser files were left unchanged by the owner's decision (63-05) | 2026-11-10 |
