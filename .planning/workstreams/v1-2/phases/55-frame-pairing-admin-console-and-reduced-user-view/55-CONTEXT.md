# Phase 55: Frame Pairing, Admin Console and Reduced User View - Context

**Gathered:** 2026-10-30
**Status:** Ready for planning

<domain>
## Phase Boundary

Admins pair a new frame to a user with a short on-panel code (single-use, expiring, claimed atomically, audited), manage the whole fleet from a console (devices, users, releases, audit log) and ordinary users see only their own frames with fewer options. Requirements: AUTH-04, AUTH-05. Depends on Phase 54.

First deliverable (first plan): the Phase 54 hand-off. The rows of the route x role x owner matrix (`companion/test_access_matrix.py`) that waited for Phase 51 are completed, because the new pairing and admin routes extend that same matrix. Items in `54-HANDOFF.md` section A are in scope. The `legacy-admin` fallback is already removed on `main` (owner's change); nothing to do about it.

Out of scope: device co-management (Phase 60), firmware changes (Phase 57 ships the single combined OTA), fleet polling and zones (52), detection modes (53), per-hardware rendering and battery profiles (56), any production deploy, Phase 47 files and `hardware/`.

</domain>

<decisions>
## Implementation Decisions

### Fixed by the owner before discussion (do not reopen)
- **D-01:** Frames keep MAC + secret authentication, independent of Auth0. What the live frame receives (image, interval, auth) does not change; `stub-server/test_phase47_freeze.py` stays green; expand-only.
- **D-02:** No production deploy. No real Auth0 or external service in tests (fake Auth0, pytest-socket guard). No Auth0 secret or real pairing code in the repo.
- **D-03:** Pairing works server-side with what the firmware already does (a frame shows whatever image the display endpoint returns and sleeps for the interval it is given). Any firmware need is reported to the owner, never worked around or added here.
- **D-04:** The shared-password `legacy-admin` fallback was removed by the owner on `main` (Auth0 is the only sign-in) after this context was first written; nothing in this phase depends on it and no `legacy-admin` principal exists any more. Plans and the matrix cover `anonymous`, `user` (owner / other) and `admin` only.
- **D-05:** Co-management is Phase 60; do not implement it. `access.authorized_device_id` keeps its owner-as-input shape.

### Unassigned frame (owner choice)
- **D-06:** A `pending_devices` table (new, schema 3) holds a frame that is enrolled but not yet assigned: MAC, secret hash, hardware type, device token, current pairing code (hash) and expiry. The `devices` row is created only on claim, with its owner, so the Phase 48 rule "exactly one owner, NOT NULL" is untouched. The BYOS registry and token lookups (`tokens_by_mac`, `registry_view`, setup enrolment) must also read `pending_devices`.
- **D-07:** An admin registers a new frame from a form in the console (MAC + secret SHA-256 printed by `firmware/provision.sh`, hardware type). The CLI gets the same verb. The raw secret never enters the companion; only its hash is submitted.
- **D-08:** A pending frame calling `/device/v1/display` receives a server-rendered pairing image in the format it already understands (raw legacy format for 1200x1600; Phase 50 container where negotiated) and a server-chosen 300 s interval. The live frame never takes this path.

### Pairing code (owner choice)
- **D-09:** 8 characters from a 30-symbol Crockford alphabet (digits and letters without 0, 1, I, L, O, U; about 39 bits), shown as `XXXX-XXXX`, entered case-insensitively, with look-alike characters normalised. Generated with `secrets`; only a hash is stored; compared in constant time.
- **D-10:** Valid 30 minutes; a new code is issued on expiry at the pending frame's next wake. An unpaired frame wakes every 5 minutes (server-imposed, new frames only), so a displayed code always outlives at least one wake.
- **D-11:** Single use and atomic: claiming a code is one SQLite transaction that deletes the pending row, inserts the `devices` row (owner, hardware, state directory) and writes the audit entry. Two simultaneous claims: exactly one wins, the other gets "invalid or expired". Wrong, expired and already-claimed codes answer identically.
- **D-12:** Claim attempts are throttled per admin session and globally (reuse `LoginThrottle` patterns) and every failed attempt is audited without recording the guess.

### Reassign and retire (owner choice)
- **D-13:** Reassigning a frame to another user wipes the previous owner's data: device config (calendar URL, colour rules, airline overrides, illustration overrides), history, poll state, gallery. The frame keeps its MAC, secret and token (no re-enrolment) and restarts like a new frame. The live frame (`state_path = "."`) is never wiped: reassigning it changes the owner only, and retiring it is refused (guard that protects the Phase 47 measurements).
- **D-14:** Retiring a frame keeps its token valid and serves a "frame retired" image with a 24 h interval, so the current firmware (no recovery from 401 before Phase 57) neither loops nor drains the battery. Retirement is reversible: an admin can re-activate the frame, which returns it to the pending state with a fresh code. Retirement keeps the data; re-activation wipes config and history exactly like a reassignment (owner choice 2026-10-31). A retired frame is stored as `pending_devices.status = 'retired'` with its previous owner kept for the audit trail. Hard deletion stays a CLI-only act (`devices remove`).

### Console and user view (owner choice)
- **D-15:** Admin console pages: Fleet (every device with owner, hardware, last seen, battery, firmware, pending and retired frames, actions), Users (invite with email + role, change role, disable and re-enable, unlink Auth0 identity; guard: the last active admin cannot be demoted or disabled, nobody disables themselves), Audit log (read-only, newest first), Releases (the existing per-hardware `/update` page entered from the console, no redesign), Locations (see D-18). From the Fleet list an admin opens a frame's own pages under `/devices/<id>/...` as today.
- **D-16:** An ordinary user sees only their own frames (pending, retired and other users' frames do not exist for them: 404). Per frame they keep: Home, Flights, Display (look, quiet hours, time zone, display on/off), Calendar, colour rules and airline names/resolution (the former Display and Airlines pages), and a reduced Health. They do not get: the fleet list, other users, the audit log, releases/update, wake interval, LED, "poll now", the hardware/OTA details.
- **D-17:** The user's Health page shows the frame only: last contact, battery, next wake, frame anomalies. It hides the ADS-B and airline-source status (platform health). Platform health stays admin-only.
- **D-18:** Locations are available to both roles. An admin manages all locations in the console; an ordinary user creates their own locations (name, latitude, longitude, time zone), sees only their own, and picks one for their own frames. This needs an owner column on `locations` (schema 3, expand-only: existing locations belong to nobody and stay visible to admins and assignable by admins; users cannot see or use them). Quota, validation and rate limits are research items. Zones and detection modes remain Phases 52/53; this phase only stores and assigns the location.

### Audit and safety
- **D-19:** An append-only `audit_log` table (fleet.db, therefore in the backup): actor, action, target, outcome, timestamp, source IP; no secrets, no codes, no guesses. Events: frame registered, pairing issued/claimed/failed, reassigned, retired/re-activated, user invited/role changed/disabled/enabled/identity unlinked, location changes, release actions. Read-only page for admins; no purge in this phase.
- **D-20 (owner choice 2026-10-31):** Per-session CSRF token on every new admin and pairing POST, the release actions (`/update*`) and the existing destructive POSTs (rule delete, calendar disconnect, manual-resolution delete, airline rename reset). Other existing forms keep Origin / Sec-Fetch-Site + session. The token is derived from the session secret (no schema change).
- **D-21:** All new schema changes are one expand-only migration to schema 3 (`pending_devices`, `audit_log`, `locations.owner_user_id`). Same rollback caveat as Phase 54: the previous release's byos refuses a schema it does not know; surface it in the hand-off. The freeze test and the backup/restore test cover the new tables.

### Facts to report to the owner (from research)
- **Redraw cost:** an unclaimed frame wakes every 5 minutes but redraws only when the image hash changes (hash-skip); the pairing image is byte-deterministic (no clock, no countdown), so it redraws only when the code rotates (about every 35 minutes, roughly 40 times a day).
- **White after claim:** a claimed non-live frame shows nothing until a poll writes its image; the fleet poll is Phase 52 and users have no poll-now, so a claimed frame stays on its last image until then.
- **Migration index:** schema migration 3 is reserved for this phase; Phases 52/53 append v4 and later.
- **No firmware need** identified for pairing or retirement (frame reads `image_url`, `image_hash`, `sleep_s` 1..86400, `led_enabled`).

### Claude's Discretion
Module layout, table and column names, how the pairing image is drawn (Pillow, vendored fonts, six-colour palette), page layouts under `sketch-findings-skypane`, bilingual strings in `companion/i18n_fr/`, route paths, plan split and waves, throttle parameters, location quotas.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Planning
- `.planning/workstreams/v1-2/ROADMAP.md` — Phase 55 goal and success criteria (edit only Phase 55 lines)
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — AUTH-04, AUTH-05
- `.planning/workstreams/v1-2/STATE.md` — project decisions (edit only Phase 55 lines)
- `.planning/workstreams/v1-2/phases/54-auth0-sign-in-local-roles-and-default-deny-access/54-HANDOFF.md` — leftover work; matrix rows come first
- `.planning/workstreams/v1-2/phases/54-auth0-sign-in-local-roles-and-default-deny-access/54-CONTEXT.md` — roles, sessions, 404 on denial, D-11 account page
- `.planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-DEVICE-SCOPED-ROUTES.md` — route inventory and BYOS endpoints
- `.planning/workstreams/v1-2/phases/51-per-device-config-image-and-state/51-CONTEXT.md` — per-device directories
- `.planning/workstreams/v1-2/phases/48-fleet-data-model-roles-and-live-frame-migration/48-CONTEXT.md` — freeze list, one owner rule
- `.planning/workstreams/v1-2/phases/50-common-image-format/50-CONTEXT.md` — image negotiation
- `.planning/workstreams/v1-2/research/ARCHITECTURE.md`, `PITFALLS.md`

### Code
- `companion/access.py`, `companion/routes.py`, `companion/app.py`, `companion/device_scope.py`, `companion/auth.py`, `companion/pages/account_page.py`
- `companion/test_access_matrix.py`, `test-support/access_matrix_support.py`
- `server/fleet_db.py`, `server/fleet_sessions.py`, `server/hardware.py`, `server/device_dirs.py`
- `stub-server/byos_server.py` (`_enrol`, display handler), `stub-server/fleet_cli.py`
- `stub-server/test_phase47_freeze.py`, `stub-server/measured_fields_freeze.json`
- `firmware/provision.sh`, `deploy/README.md` (frame provisioning), `COMPLIANCE.md`
- `.claude/CLAUDE.md`, `.claude/skills/sketch-findings-skypane/SKILL.md`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `access.authorized_device_id` / `Access(USER, "device")`: ownership gate to open to users.
- `fleet_db.transaction()`, `assign_owner`, `add_device`, `list_devices`; `fleet_cli` verbs to mirror in the console.
- `LoginThrottle`, `post_origin_ok` in `companion/auth.py`; session store in `server/fleet_sessions.py`.
- `server/device_dirs.py` for the per-device directory create/wipe.
- Companion fixtures `companion/conftest.py`, `test-support/companion_app_server.py`, `test-support/fake_auth0.py`.

### Established Patterns
- One route table with a mandatory `Access`; matrix test fails until each route has a row.
- Device selector built from `device_scope.load_devices` has no owner filter yet: it must filter for users.
- `next` after sign-in accepts only fixed un-prefixed routes.

### Integration Points
- `Handler._dispatch_for_device` ownership hook; BYOS `_enrol` and display handler for the pending path; fleet.db migration 3; backup includes new tables; `home_for(principal)` and the Account page "Frames" empty state.

</code_context>

<specifics>
## Specific Ideas

- The pairing screen must be readable from a distance and say what to do in English and French.
- Registering a frame from the web must never accept a raw secret, only its SHA-256.

</specifics>

<deferred>
## Deferred Ideas

- Device co-management — Phase 60.
- Firmware recovery after 401 and any on-device pairing UI — Phase 57.
- "View as user" (AUTH-07).
- Audit log purge/export.

</deferred>

---

*Phase: 55-Frame Pairing, Admin Console and Reduced User View*
*Context gathered: 2026-10-30*
