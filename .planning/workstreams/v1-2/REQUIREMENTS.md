# Requirements: SkyPane

**Defined:** 2026-10-28
**Milestone:** v1.2 Fleet platform
**Core Value:** Glancing at the frame tells you, in real time, which plane is taking off or landing right now — while also being a satisfying ambient piece on the wall.

Runs in parallel with v1.1 Phase 47 (open, untouched). Phase numbering continues from 48.

## v1.2 Requirements

### Fleet Data Model

- [x] **DATA-01**: The owner can have users, devices, hardware types and locations recorded in one fleet database, with exactly one owner per device.
- [x] **DATA-02**: The current frame is migrated into the fleet database keeping its MAC, secret and token, so it keeps polling without a reflash or re-enrolment and its next poll returns the same image hash and wake interval.
- [x] **DATA-03**: Each user has a role, admin or user, stored in the local database and never derived from Auth0 alone.
- [x] **DATA-04**: The owner can define hardware types as profiles (resolution, palette, image format, battery profile, firmware target), including simulated types so phases 1–7 are testable without a purchase.
- [x] **DATA-05**: The fleet database is included in the backup with a tested restore, and a written freeze list of what Phase 47 measures (wake cadence, battery telemetry, poll state fields) is enforced by a test.

### Firmware and OTA

- [x] **OTA-01**: The owner can publish and schedule firmware releases per hardware type, and a frame is only ever offered a release of its own server-assigned type.
- [x] **OTA-02**: An uploaded binary whose app descriptor or chip target does not match the declared hardware type is rejected, and downgrades are refused by a monotonic build number.
- [ ] **OTA-03**: The owner can decide whether OTA images are signed, record the decision (including any one-time cable flash it needs) before the second hardware is provisioned, and the chosen integrity mechanism is verified on the device side.
- [ ] **OTA-04**: All firmware changes needed on the current frame (image-header reader, any hardware header, recovery after repeated 401) ship in one release, only once Phase 47 allows it.

### Image Format

- [x] **IMG-01**: Images use a common versioned format whose header carries width, height and palette, specified with golden fixtures.
- [x] **IMG-02**: The server serves the new format only to frames that announce support; existing frames keep receiving their current raw image, byte for byte.
- [x] **IMG-03**: The firmware reader validates magic, version, length and panel dimensions before touching the display buffer, and still accepts the legacy format.

### Per-Device Runtime

- [x] **FLT-01**: Each device has its own config, image, poll state, history and health, and the BYOS server serves each frame its own image from its own directory.
- [x] **FLT-02**: The owner or a user can set a device's quiet hours and timezone without affecting others. (The manual poll trigger was removed in Phase 52; the poll process is the only budget consumer.)
- [x] **FLT-03**: Total ADS-B requests stay at or below 1 per second across all providers and processes, using a persisted global limiter, with devices sharing a zone served by one request.
- [x] **FLT-04**: A simulated 100-device fleet test proves the request budget with a fake clock, and a failure for one device or zone never blocks the others.

### Detection Modes

- [ ] **DET-01**: A device can be set to an airport and runway chosen from a committed France catalogue built from OurAirports (rows without both thresholds dropped), with real runway designators.
- [ ] **DET-02**: Recorded Orly traffic replayed through the new runway logic gives the same decisions as the current hand-tuned runway-3 geofence, and at least one parallel-runway airport is tested.
- [ ] **DET-03**: A device can be set to show aircraft around a position within a bounded radius inside France, and coordinates sent to third parties are rounded.

### Accounts and Administration

- [x] **AUTH-01**: A user can sign in with Auth0 (authorization code + PKCE, no new dependency), with state, nonce, iss, aud and exp checked, sign-up closed in the app, and the Auth0 `sub` linked once to an admin-created local user and matched on `sub` afterwards.
- [x] **AUTH-02**: The shared password keeps working temporarily as a named legacy-admin fallback behind a flag, with a throttle and a dated removal task; sessions no longer depend on the password.
- [ ] **AUTH-03**: Every route is default-deny with a minimum role, a user only sees and changes their own devices (404 for others), and a route × role × owner matrix test proves it.
- [ ] **AUTH-04**: An admin can pair a new frame to a user with a short, single-use, expiring on-panel code, claimed atomically and audited.
- [ ] **AUTH-05**: An admin can use a console to see the whole fleet (owner, hardware, last seen, battery, firmware), manage users, reassign or retire devices and manage releases, while ordinary users get a reduced view of their own frames with fewer options.
- [x] **AUTH-06**: Frames keep authenticating with MAC and secret, independently of Auth0, and Auth0 is replaced by a local fake server in tests.
- [ ] **AUTH-08**: A frame keeps one primary owner and can have co-managers who change its settings like the owner but cannot retire, reassign or remove it. The owner and an admin can add or remove co-managers among already-invited users, and each change is audited.

### Per-Hardware Rendering and Credits

- [x] **HWR-01**: The renderer, battery thresholds and health views are driven by the device's hardware profile, with provenance recorded for each battery number and a golden-image baseline of the legacy render.
- [ ] **HWR-02**: A credits page, generated from one data file, cites adsb.fi (with link), adsb.lol, adsbdb and OurAirports, and the project has recorded contact with adsb.fi / adsb.lol about multi-zone use (owner decision 2026-10-31: the message is drafted and its sending is deferred until the fleet has more than 10 registered users).

### Second Hardware

- [ ] **HW2-01**: The owner can choose a second hardware type from a documented shortlist after a time-boxed ESP-IDF panel-driver spike, within the hardware budget.
- [ ] **HW2-02**: The chosen board is validated on an evaluation unit: cable flash, a real OTA, the OTA signing bench procedure of `firmware/SIGNING.md` (the device-side half of OTA-03), a native layout, a measured battery sample and a rebuilt battery model.

### Debt

- [ ] **DEBT-01**: The comment-history guard debt is cleared (or its baseline only shrinks), and no v1.2 phase adds violations.

## Future Requirements

- **FLT-05**: Presence-adaptive poll cadence and per-user device caps.
- **AUTH-07**: "View as user" read-only mode for the admin.
- **PAIR-01**: QR code on the pairing screen (needs a QR encoder, i.e. a new dependency).
- **PWR-01**: Solar or wall power after field evidence.
- **MSG-01**: The companion sends a short message to the frame.

## Out of Scope

| Feature | Reason |
|---|---|
| RER view and physical button views | Dropped from the project on 2026-10-28 |
| Open sign-up, device sharing, fine-grained RBAC, billing | Small invited fleet only |
| Local JWT signature verification | OIDC Core allows skipping it for a direct token-endpoint response; avoids a crypto dependency |
| Remote command channel, websockets | Frames sleep and never accept connections; changes apply at next wake |
| Per-user firmware or artwork upload | Security and scope |
| Overseas territories | France mainland only unless the owner extends it |

## Traceability

Coverage: 31/31 v1.2 requirements mapped, each to exactly one phase.

| Requirement | Phase | Status |
|---|---|---|
| DATA-01 | Phase 48 | Complete |
| DATA-02 | Phase 48 | Complete |
| DATA-03 | Phase 48 | Complete |
| DATA-04 | Phase 48 | Complete |
| DATA-05 | Phase 48 | Complete |
| OTA-01 | Phase 49 | Complete |
| OTA-02 | Phase 49 | Complete |
| OTA-03 | Phase 49 (decision), Phase 58 (device-side check) | Pending (decision recorded 2026-10-29; device-side bench check carried to Phase 58 by the owner, 2026-10-31) |
| IMG-01 | Phase 50 | Complete |
| IMG-02 | Phase 50 | Complete |
| IMG-03 | Phase 50 | Complete |
| FLT-01 | Phase 51 | Complete |
| FLT-02 | Phase 51 | Complete |
| FLT-03 | Phase 52 | Complete |
| FLT-04 | Phase 52 | Complete |
| DET-01 | Phase 53 | Pending |
| DET-02 | Phase 53 | Pending |
| DET-03 | Phase 53 | Pending |
| AUTH-01 | Phase 54 | Complete |
| AUTH-02 | Phase 54 | Complete |
| AUTH-03 | Phase 54 (gate and matrix), Phase 55 (real per-device rows) | Pending (gate and matrix delivered and verified in production; the real per-device route rows are carried to Phase 55 by the owner, 2026-10-31) |
| AUTH-06 | Phase 54 | Complete |
| AUTH-08 | Phase 60 | Pending |
| AUTH-04 | Phase 55 | Pending |
| AUTH-05 | Phase 55 | Pending |
| HWR-01 | Phase 56 | Complete |
| HWR-02 | Phase 56 | Complete (contact deferred by the owner until more than 10 users) |
| OTA-04 | Phase 57 | Pending |
| HW2-01 | Phase 58 | Pending |
| HW2-02 | Phase 58 | Pending |
| DEBT-01 | Phase 59 | Pending |
