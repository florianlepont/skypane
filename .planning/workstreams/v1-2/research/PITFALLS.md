# Domain Pitfalls

**Domain:** Fleet platform (multi-user, multi-hardware) added to an existing single-frame SkyPane system
**Milestone:** v1.2 (workstream `v1-2`, phases 48+; owner's tentative phases 1-9 below)
**Researched:** 2026-10-28
**Overall confidence:** MEDIUM. Auth/OAuth and OTA items rest on well-known standards (RFC 6749/7636/9700 BCP, OWASP) and on the repo's existing code shape (`stub-server/byos_server.py`: MAC-keyed `devices.json` with SHA-256 secret hashes, content-addressed `/img/<sha256>.bin` and `/fw/<sha256>.bin`, `X-Fw-Version`/`X-Ota-Result` headers; one shared `device_config.json`). I did not run live web research for this file; ADS-B provider terms were already researched 2026-10-28 and are only applied here. OurAirports specifics are from training knowledge (LOW-MEDIUM) and flagged for phase-time verification.

Phase key: P1 data model+migration, P2 OTA per hardware, P3 image format, P4 per-device config/poll budget, P5 detection modes, P6 Auth0+accounts+ownership+pairing+admin, P7 per-hardware render/battery/credits, P8 second hardware, P9 comment-history debt.

---

## Critical Pitfalls

### C1: Auth0 login without state / nonce / iss / aud validation (login CSRF, token substitution)
**What goes wrong:** Callback accepts any `code` for any browser. An attacker feeds a victim their own `code` (login CSRF) or a token minted for another Auth0 client/tenant is accepted.
**Why it happens:** With no JWT library and no signature verification, it is tempting to base64-decode the ID token and trust it, or skip `state`/`nonce` because "TLS protects it".
**Consequences:** Account takeover or victim silently logged into the attacker's account (and then pairing a frame to it).
**Prevention (all must be tested):**
- Generate `state` (>=128-bit, `secrets.token_urlsafe`), `nonce`, PKCE `code_verifier` (43-128 chars, S256 challenge) per login attempt; store them server-side keyed by a short-lived (<=10 min), single-use, HttpOnly pre-login cookie id. Delete on first use, success or failure.
- Callback: reject on missing/mismatched state, expired attempt, `error` param, replayed attempt.
- Exchange the code only by a server-to-server HTTPS POST to the Auth0 token endpoint with `requests` default TLS verification (never `verify=False`; the endpoint host must come from config, never from the request). Skipping signature verification is acceptable ONLY because the token arrives directly from the token endpoint over TLS (OIDC Core 3.1.3.7 allows this); the claim checks are still mandatory: `iss` == configured `https://<tenant>/`, `aud` == our client_id, `exp` > now (small skew), `nonce` == stored, `sub` present.
- Never accept an ID token from any other channel (query string, form, cookie). Do not use the access token for authz decisions.
- Pin issuer/domain in config; refuse to start if unset in production mode.
**Detection:** A faux-Auth0 test that returns wrong `iss`, wrong `aud`, wrong `nonce`, expired `exp`, missing `sub`, and a replayed state must each yield a 4xx with no session cookie set.
**Phase:** P6 (test harness for faux Auth0 is a P6 deliverable, built first).

### C2: Account linking by email instead of `sub`
**What goes wrong:** Users are matched or merged by `email`. Social/unverified-email IdP connections let someone claim another user's email and inherit their account and role (including admin).
**Prevention:** Primary key of identity is `(iss, sub)`. Store `email` as display only. Never auto-link or auto-promote by email. The first admin is bootstrapped by an out-of-band action (CLI on the VPS or env allowlist of `sub`), never by "the email equals the owner's". Test: two different `sub` with the same email are two users.
**Phase:** P1 (schema: unique `(iss, sub)`), P6 (login logic).

### C3: Sign-up not actually disabled; any Auth0 user gets in
**What goes wrong:** Auth0 tenant allows open signup (or social connections), and the app auto-creates a user row on first successful login. Anyone on the internet becomes a "user".
**Prevention:** Two layers. (1) Auth0 tenant: disable sign-ups on the database connection, no social connections, and enforce this in the deploy checklist. (2) App-side: a verified Auth0 login for an unknown `sub` creates NO user; it shows "ask the admin for an invite". Users exist only through admin-created invites (single-use, expiring token bound to intended role=user) redeemed after login. App-side is the real control because tenant settings drift. Test: unknown `sub` with a valid token -> no row, no session.
**Phase:** P6.

### C4: Role escalation and admin/user separation done only in the UI
**What goes wrong:** The reduced user view hides admin links but the routes behind them still answer. Role is read from a client-controlled field (cookie, form, `?role=`), or from token claims instead of the DB. Existing companion pages (settings, flash, resolve, airline overrides) were all admin-grade and now become reachable by ordinary users.
**Why it happens here:** `companion/routes.py` is one dispatch table built for a single trusted password holder; every current route is implicitly "admin".
**Prevention:**
- Add a required `min_role` (and `ownership` requirement) column to every entry in the route table; default-deny: a route without an explicit policy fails a unit test and refuses to register.
- Role is loaded from the DB on each request from the session's user id, never trusted from the cookie payload.
- POST body fields cannot set `role`/`owner_id`; admin-only mutations use separate routes.
- A parametrized test enumerates the whole route table x {anonymous, user, admin} and asserts the expected status (the repo already has a session-gating-vs-baseline test pattern from Phase 40 to extend).
- The last admin cannot be demoted/deleted (lockout).
**Phase:** P6 (policy table) with the roles column in P1.

### C5: Per-device IDOR (user A reads or edits user B's frame)
**What goes wrong:** Routes take `device_id` (or MAC) in the path/body and load it without checking `device.owner == session.user`. Also leaks via derived resources: image URLs, battery charts, flight history, config history, backups, firmware status, and the content-addressed `/img/<sha256>.bin` (guessable only by hash, but hashes appear in poll responses and logs).
**Prevention:** One choke-point function `get_device_for(user, device_id)` returns 404 (not 403, to avoid existence oracle) for foreign devices; admin bypass explicit. No handler may query the devices table directly (enforce by a repo test grepping handler modules is source-text and forbidden by the behaviour-over-source rule, so instead test behaviourally). Test: two users, two devices; every device-scoped route x every verb as the wrong user -> 404 and no state change. Also: device-facing endpoints authenticate by per-device secret and may only ever see that device's data; verify device A's token on device B's image path fails.
**Phase:** P6 (enforcement), P1 (owner_id FK), P4 (per-device state paths), P7 (health/battery pages are IDOR-prone).

### C6: Session cookie mistakes
**What goes wrong:** Cookie lacks `Secure`/`HttpOnly`/`SameSite`; session id predictable or stored client-side unsigned; session survives logout; fixation (same id before and after login); stdlib `ThreadingHTTPServer` code hand-formats `Set-Cookie` and omits attributes. Caddy terminates TLS, so the app sees plain HTTP and may wrongly omit `Secure`.
**Prevention:** Random 256-bit opaque session id, server-side store (SQLite), rotate id on login, delete on logout, absolute (e.g., 30 d) plus idle timeout, `HttpOnly; Secure; SameSite=Lax; Path=/`; the pre-login cookie uses SameSite=Lax too (Strict breaks the Auth0 redirect back). Decide `Secure` from config (`SKYPANE_PUBLIC_URL` is https), not from the socket. Test: parse `Set-Cookie` from the real server in the fixture and assert attributes; logout invalidates server-side.
**Phase:** P6.

### C7: CSRF on state-changing routes
**What goes wrong:** SameSite=Lax cookies are not enough (GET-with-side-effects, subdomain attacks, old browsers). The companion currently relies on a shared-password session and probably has few CSRF controls; v1.2 adds destructive admin actions (delete device, push firmware, change role).
**Prevention:** All mutations are POST; per-session CSRF token embedded in forms and checked with constant-time compare; also check `Origin`/`Sec-Fetch-Site` header against the public origin. No state change on GET (including logout and the OAuth callback beyond session creation). Test: POST without/with wrong token -> 403 for every mutating route (enumerate from the route table).
**Phase:** P6.

### C8: Open redirect via `return_to` / `next`
**What goes wrong:** Post-login redirect target taken from the query string; attacker sends `https://host/login?next=//evil.example`. Also `redirect_uri` built from the `Host` header.
**Prevention:** `redirect_uri` is a fixed configured constant and registered exactly in Auth0 (no wildcards; Auth0 "Allowed Callback URLs" with one entry per environment). Store `return_to` server-side in the pre-login record, accept only same-site relative paths matching `^/[A-Za-z0-9/_-]*$` (reject `//`, `\`, `:`, CR/LF). Never reflect `Host`. Test: table of hostile values -> falls back to `/`.
**Phase:** P6.

### C9: Shared-password fallback becomes a permanent backdoor
**What goes wrong:** The password is kept "temporarily" but grants admin over all users' frames, bypasses ownership, has no rate limit, and is never removed. It also defeats everything else: an attacker needs only to brute-force one string. Also, the fallback can silently shadow Auth0 if the order of checks is wrong.
**Prevention:** Make it explicit: env flag `SKYPANE_LEGACY_PASSWORD_LOGIN=1`, default off after cutover; it maps to a single named legacy admin principal (auditable, shown in the UI as "legacy"), never to user-role. Add login rate limiting/lockout per IP (Caddy or app) and constant-time compare. Log every legacy login. Put a removal date/phase in the roadmap (end of P6 or first plan of the next milestone) with a test that the flag off yields 401 on the old form. Do not expose the password form to non-admin users if the owner has Auth0 working.
**Phase:** P6 (introduce flag + audit), removal tracked as an explicit roadmap item.

### C10: Bricking a frame with the wrong firmware binary (OTA per hardware type)
**What goes wrong:** A registry indexed by version only (as today: one `/fw/<sha256>.bin`) is extended without a hardware key; a second type (different panel, flash size, partition table, pins) receives the XIAO/EE02 binary. ESP-IDF's rollback protects against an app that crashes before `esp_ota_mark_app_valid_cancel_rollback`, but not against an app that boots, marks itself valid, and drives the wrong pins/panel; and not against partition-table mismatch or too-large images.
**Prevention:**
- Registry key is `(hardware_type, version)`. The device sends its `hardware_type` (compiled in via Kconfig/`CONFIG_` and `esp_app_desc_t.project_name`) in every poll; the server offers only binaries of that exact type. Server refuses to publish an image whose embedded `esp_app_desc` project name/chip target does not match the declared type (parse the app descriptor from the binary at upload; offset 0x20 of the image after headers).
- Device-side check before `esp_ota_set_boot_partition`: verify `esp_app_desc` project_name == own, `esp_ota_get_next_update_partition` size fits, and SHA-256 matches the advertised hash (already content-addressed; keep it). Keep the app-valid mark gated on a successful poll+display, not just boot.
- Staged rollout: per-device `target_version`, admin pushes to one canary device first; the `X-Ota-Result` reports already exist and should drive "halt rollout on first failure".
- Migration: existing frames send no hardware header; treat a missing header as `xiao-ee02-13in3` explicitly (one documented default, only for legacy), never as "any".
**Detection/testing:** Simulated hardware type receives only its own binary; a test publishes a mismatched-name binary and the registry rejects it; a device claiming type X and requesting hash of type Y gets 404 at `/fw/`. Host firmware test (firmware.yml) for the app-desc check.
**Phase:** P2 (server registry and offer), P8 (first real second-type OTA is the true test; do not enable OTA push for type 2 until it was flashed by cable once).

### C11: Downgrade, replay and integrity of OTA
**What goes wrong:** Admin or a stale registry entry offers an older version (reintroducing fixed bugs, or an older image incompatible with the newer NVS layout/image format). Hash is fetched from the same channel as the binary, so it only detects corruption, not tampering. No signature -> anyone who compromises the VPS or gets a TLS MITM (if CA pinning absent) can push code to every frame.
**Prevention:** Offer only if `offered_version > running_version` (monotonic build number, not string compare of "1.2.10" vs "1.2.9"; use an integer). Explicit admin "allow downgrade" flag per device for rollbacks, logged. Decide security level consciously: at minimum TLS with server cert verification on device (verify the existing `esp_http_client` config uses the CA bundle, not `skip_cert_common_name_check`); preferably ESP-IDF secure OTA signature verification (app signing v2) with the signing key kept off the VPS. Note in docs that enabling signed images later requires a one-time cable flash of a bootloader that supports it, so decide before the second hardware ships. Record this as an explicit decision even if answer is "TLS+hash only for a family fleet".
**Phase:** P2 (monotonic version, offer rule), P8 (signing decision before second-type provisioning).

### C12: New image format breaks already-deployed frames
**What goes wrong:** Deployed firmware expects a fixed raw 1200x1600 6-colour payload (or a specific packing) verified by SHA-256 of the whole body. Adding a header (width/height/palette) to the same URL makes old frames render garbage, fail the hash check and loop in backoff, or - worst - draw a shifted image. Backoff caps at 6 h (flightportrait model), so a bad rollout looks like a dead frame for hours.
**Prevention:**
- Content negotiation, not replacement: new header-bearing format lives under a new path/version (`/img/v2/<hash>.bin`) or is selected by a request header (`X-Img-Format: 2`) that old firmware never sends. Old frames keep getting legacy raw bytes until they OTA to a firmware that sends the header.
- The header begins with a magic and a version byte, fixed-size little-endian fields, explicit payload length and a header CRC/size; firmware parser validates magic, version <= supported, width*height*bpp == payload length, dimensions == its panel before touching the display buffer; any failure = keep current image, report error code in the next poll, do not retry hot.
- Define what the hash covers (whole file including header) and keep hash-skip logic (device skips download when advertised hash == last displayed hash) consistent: the hash stored in NVS must be of the same bytes in both formats, otherwise after OTA to the v2 firmware the device compares a legacy hash to a v2 hash and re-downloads (harmless, one extra refresh = ~25 s of battery) or, worse, equal hashes of different representation suppress a needed redraw. Decide: hash is over the served file; a format change always changes the hash.
- Ordering: ship firmware that understands v2 (P3 firmware) and OTA it to the deployed frame BEFORE the server starts serving v2 to it; the server decides per device from reported `X-Fw-Version`/capability header.
- Golden-file tests: committed binary fixtures of legacy and v2 images; firmware host tests parse both; server test renders the legacy format byte-identically to the pre-change output (regression guard); Pillow palette quantisation of the 6 Spectra colours is shared by both paths.
**Detection:** After rollout, `X-Ota-Result`/error reports spike; a frame whose displayed hash never changes.
**Phase:** P3 (format + firmware parser + legacy negotiation), P2 must precede (OTA is the delivery mechanism), P7 (per-hardware render uses header dims).

### C13: Migrating the shared `device_config.json` to per-device config loses or corrupts the live frame
**What goes wrong:** Settings today (wake interval, quiet hours, runway geofence, theme, looks) are global. Migration moves them to a per-device store, but the poll loop (systemd timer oneshot every 30 s), the companion and the BYOS server are three separate processes reading the same files; a half-migrated state yields the frame getting default config (sleep_s wrong -> battery drain, or quiet hours dropped), or the poll loop writing the old file after migration. `device_config.py` is duplicated byte-for-byte in `stub-server/byos_server.py` for quiet-hours arithmetic; two copies can diverge.
**Prevention:**
- Idempotent, versioned, forward-only migration with a schema_version row; run once at startup under a file/DB lock; take a backup copy (existing backup timer) before; write new store atomically (temp+rename or one SQLite transaction); keep the old file untouched for one release and read it only as a fallback when the device has no row.
- The migrated frame keeps its existing identity: same MAC key, same secret hash, same token; do not regenerate (the Phase 02-05 lesson: NVS holds the old token, stale credentials loop forever). Map legacy MAC -> `device_id` -> owner=legacy admin.
- A "global defaults" layer stays so a device with no override behaves exactly as before; test that the migrated device's computed `sleep_s`, quiet hours and geofence equal the pre-migration values (golden snapshot comparing old and new code paths on the same inputs).
- Single code path for config resolution; delete the byte-for-byte duplication or add a test that asserts equal behaviour on a table of inputs.
- Rollback plan: since v1.1 Phase 47 (field validation on the same VPS) is open and the frame is in the field, the migration must be reversible by redeploying the previous release with the old file untouched. Test by running old code against the post-migration state directory.
**Phase:** P1 (store+migration), P4 (poll loop/BYOS consume per-device config).

### C14: Running v1.2 in parallel with open v1.1 Phase 47 on the same repo and VPS
**What goes wrong:** (a) A v1.2 deploy restarts byos/poll units or changes the schema mid field-validation run, corrupting the battery/discharge telemetry v1.1 needs; (b) merge conflicts in `device_config.py`, `byos_server.py`, `companion/routes.py`, state files; (c) a v1.2 migration makes `main` incompatible with the code v1.1 hotfixes are cut from; (d) the reviewer-gated production deploy ships a half-finished v1.2 phase because everything merges to `main`.
**Prevention:**
- Feature-gate, don't branch long: every v1.2 phase merges only behavior-preserving changes for the legacy frame by default (the legacy device must render byte-identical output and identical `sleep_s`); new capabilities behind flags/env default off until a phase is complete.
- Expand/contract migrations: P1 only adds tables/columns and dual-reads; the destructive "contract" step (drop old file, remove fallback) is a separate late plan, after Phase 47 closes.
- Do not change anything the Phase 47 measurement depends on (wake cadence, telemetry header names, `X-Battery-Mv` handling, poll_state fields). Freeze list written in the P1 plan and checked by a test on those headers/fields.
- Deploy hygiene: schedule v1.2 deploys outside a discharge-run window or record the interruption; keep the previous release directory for one-command rollback; verify `deploy/README.md` has a rollback section, add if missing. Backup immediately before any migrating deploy (existing backup unit).
- Phase numbering: v1.2 continues from 48; make sure STATE.md/ROADMAP edits live under the workstream to avoid clobbering v1.1's files.
**Phase:** P1 (freeze list, expand-only), all phases (gates), P9 deliberately last.

### C15: ADS-B budget blown by multiplying devices (≤ 1 req/s global, zone grouping)
**What goes wrong:** Naive per-device polling: N devices x 2 providers every 30 s is fine for 3 devices but each "aircraft around a position" device with a unique radius/centre triggers its own request; runway-mode devices at the same airport duplicate identical queries. Burst at timer tick (all requests fired in the same second) violates ≤ 1 req/s even if the 30 s average is low. A retry storm on provider error multiplies traffic. adsb.lol fragility plus no budget ceiling can get the VPS IP blocked. Removing the old fixed 1.1 s sleep between providers (Phase 38) means pacing is now absent unless re-added.
**Prevention:**
- Zone grouping: normalise each device's need into a query "cell" (provider endpoint is point+radius; quantise centre to a grid, take max radius in the group) and fetch once per cell per cycle; fan out to devices by filtering locally. Test: 10 devices in 2 zones = 2 (x providers) requests.
- Global token-bucket/rate gate in the poll process (monotonic clock, >=1.0 s spacing between ANY outbound ADS-B requests across providers), plus a hard per-cycle cap; when demand exceeds cap, serve the oldest cells first and let others age (staleness is acceptable for a wall frame). Persist last-fetch times so the 30 s oneshot (a new process each time) does not reset the gate.
- Per-zone adaptive cadence: devices in quiet hours or with long sleep_s do not need 30 s polling; poll cell only if some device in it will wake within the next cycle or has stale data (use each device's next-wake estimate).
- Backoff on 429/5xx with jitter and a per-provider circuit breaker; never retry within the same second.
- Fail closed: if the budget is exhausted, return "unchanged" rather than querying.
- A test with a fake clock and fake provider counts requests per second across a simulated 100-device fleet.
- Provider terms (already researched, apply): adsb.fi is non-commercial, with credit shown (credits page, P7; also keep it in repo `COMPLIANCE.md`); adsb.lol keep the CC0 but expect an API key requirement in future (isolate behind the provider abstraction, treat as optional); airplanes.live stays opt-in only.
**Phase:** P4 (budget, grouping, gate), P5 (detection modes generate the cells), P7 (credits).

### C16: adsbdb abuse (low-volume service, no redistribution, 30-day cache)
**What goes wrong:** Per-device lookups multiply callsign queries; negative results are not cached and re-hit every cycle; cached data is exposed through a public endpoint (redistribution); cache TTL handled wrongly.
**Prevention:** Single shared server-side cache keyed by callsign (positive and negative, negative TTL shorter, e.g. 1-6 h; positive <= 30 d), lookups deduplicated across devices within a cycle, share the global rate gate, descriptive User-Agent with contact, no raw adsbdb passthrough API; the credits page credits it. Only derived rendered images and necessary fields leave the server. Test: 50 devices seeing the same callsign = 1 request, second cycle = 0.
**Phase:** P4 (shared cache + gate), P7 (credits).

### C17: Runway geometry from OurAirports is wrong in ways that produce false detections
**What goes wrong (confidence LOW-MEDIUM, verify against the current dataset at phase time):**
- `runways.csv` stores each runway as two ends (`le_*`, `he_*`) with identifiers like "03" and "21", lat/lon, `*_heading_degT`; many rows have missing coordinates or headings, heading can be magnetic-vs-true confusion, displaced thresholds are separate fields, and closed runways have `closed=1`. Orly is `ORY` with 02/20 style ends is not the SkyPane's "runway 3" naming: the project's "runway 3" (08/26 vs 02/20... the actual Orly runways are 02/20, 06/24, 08/26) means the v1 geofence was hand-tuned; a generic derivation may not reproduce it, so the existing frame's hand-tuned geofence must be preserved as an override.
- Parallel runways (L/R, e.g., Paris-CDG 08L/08R and 09L/09R, Orly 06/24 near 08/26 at shallow angles) overlap in a geofence made from heading + width; ends/designators like "08L" need parsing; two-digit designator alone is only approximately the heading (rounded to 10 degrees).
- Geofence built from the runway line only catches aircraft ON the runway; arrivals/departures at 100-3000 ft need an approach/departure corridor (extended centreline, length, half-width), and altitude/vertical-rate/on-ground logic differs (v1 uses <=3000 ft; keep the same thresholds).
- Closed or non-existent runways selectable in the UI; airports with no runways listed; grass/water/helipad surfaces; heliports; airports outside France (scope is France, so filter by ISO country `FR` and overseas territories explicitly decide).
- Dataset updates change geometry silently between refreshes, shifting detection for devices.
**Prevention:** Vendor a snapshot (versioned, with checksum) rather than fetching at runtime; preprocess offline into a small validated JSON (France only, `closed=0`, both ends with coordinates, computed bearing from the coordinates compared against stated heading: reject if disagreement > ~5 degrees), compute true bearing and length from coordinates, geodesic not planar maths. Corridor geometry parameters as data with tests against known good cases (Orly runway used by the legacy frame must produce the same detection decisions on the recorded `adsb-test` data as the hand-tuned geofence). Parallel runways: disambiguate by lateral offset from the centreline, test with recorded traffic for a dual-runway airport. Show the user a map or at least a validated list; allow admin override. Attribute OurAirports (public domain, but credit is good practice).
**Phase:** P5 (research flag: needs phase-level research and a replay test harness using recorded ADS-B data).

### C18: Pairing a new frame is an account-takeover/DoS surface
**What goes wrong:** Pairing code is short/guessable or never expires, allowing someone to claim another user's unpaired frame; or a device registers itself freely (the current `register_device` keyed by MAC with `replace` flag); MAC spoofing: since identity is the MAC, anyone who knows a MAC can register it first. Re-pairing after a factory reset silently transfers ownership.
**Prevention:** Provisioning issues a per-device random secret (already hashed in `devices.json`) at manufacturing/flash time by an admin; the pairing code is bound to that device record, single-use, >= 8 chars from a non-ambiguous alphabet or 6+ digits with rate limiting and short TTL (e.g., 15 min after the device shows it on the panel/BLE). Claiming requires a logged-in user and creates the owner link atomically (`UPDATE ... WHERE owner_id IS NULL`). Transferring or releasing a device is an explicit admin or owner action. Identity should be a server-generated device id, not the MAC alone. Test: wrong code x N attempts locks out; expired code rejected; claimed device cannot be re-claimed; concurrent double-claim yields one winner.
**Phase:** P6 (pairing), P1 (device record fields), P8 (second hardware may pair by a different mechanism e.g. no BLE).

---

## Moderate Pitfalls

### M1: Data model that cannot express reality
Mistake: `device.location` stored on the user; hardware type as a free string; one config row per user. Prevention: tables `users`, `devices (id, owner_id nullable, hardware_type_id, location, mode, secret_hash)`, `hardware_types (id, width, height, palette, battery_model, fw_target)`, with FKs and unique `(iss, sub)`. Hardware type is data (a registry row), not an `if hw == "xiao"` branch scattered through code; the simulated hardware type is just a second row. SQLite with `PRAGMA foreign_keys=ON` (off by default!), WAL, and per-request connection discipline already used (Phase 38). **Phase:** P1.

### M2: SQLite concurrency across the 3-4 processes
Poll oneshot, BYOS server, companion and backup all open the same DB; the backup copying a live DB file produces a corrupt snapshot. Prevention: use `sqlite3.Connection.backup()` or `VACUUM INTO` in the backup unit, `busy_timeout`, short transactions, WAL, no long write transactions in the poll cycle. Test with two processes hammering. **Phase:** P1, P4.

### M3: Hash-skip logic and per-device images
Content-addressed images keyed only by hash are fine, but per-device dimensions/palette mean the cache key must include render parameters; retention "keeping the newest" must be per device or one busy device evicts another's current image, causing 404 mid-download. Prevention: keep newest N per device, GC only after confirming no device advertises it. **Phase:** P3/P4.

### M4: Device authentication per device vs shared token
Phase 02-05 showed a token minted by another server persisting in NVS forever with no 401 recovery. With many devices, a rotated secret or a deleted device leaves frames in 6 h backoff. Prevention: firmware clears stale token / re-enters provisioning state on repeated 401 (or server returns a distinct "unknown device" so the admin sees it in a "unclaimed/unknown devices" list); document NVS erase. **Phase:** P2 (firmware change rides the same OTA), P6.

### M5: Per-hardware battery model reuse
The v1.1 model separates per-wake energy and deep-sleep leakage measured on the 13.3" EE02 panel (full refresh ~20-25 s at high current). Reusing numbers for another panel/MCU/battery gives plausible but wrong percentages and low-battery icon thresholds (LiPo curve, ADC divider and calibration differ per board; the ADC is already calibrated per unit). Prevention: battery parameters (capacity, divider ratio, voltage-to-percent curve, per-wake mJ, leakage uA, refresh time) are fields of the hardware type with provenance ("measured"/"assumed") and the UI shows "estimate" for assumed values; the simulated type is explicitly flagged as fake. Per-wake energy scales with refresh time, which depends on panel and temperature; the interval recommendation must not be copied. Wait for v1.1 Phase 47 results before freezing the xiao parameters. **Phase:** P7 (schema/fields), P8 (measure on real second unit).

### M6: Per-hardware rendering regressions
Refactoring `draw.py`/layout to take width/height/palette can shift pixel layout of the existing frame (fonts, margins hard-coded for 1200x1600). Prevention: golden-image tests of the legacy device at the pixel level (hash equality) before and after; render tests for each hardware type incl. non-portrait aspect and different palette (e.g., 4-colour or B/W requires dithering/quantisation path); palette-aware contrast (the repo has a contrast check). **Phase:** P7, with the golden baseline captured in P3.

### M7: Testing with a faux Auth0 that lies like the real one
Faux IdP only returns happy paths and unsigned tokens, so negative checks never run; or it is reachable from CI over the network (the suite has a pytest-socket non-loopback guard). Prevention: faux Auth0 as a loopback stdlib server in `test-support/` (same pattern as the companion app-server fixture) with knobs to mutate each claim, delay, 5xx on token endpoint, wrong `redirect_uri`, reused code; the app's issuer/token endpoint come from config so the same code path is exercised (no `if TEST` branch). The simulated hardware type must be a registry row, not mock objects, so the flow exercised is the production one. Real Auth0 tenant smoke test is a manual, documented step once, not CI. **Phase:** P6 (faux Auth0), P1/P2 (simulated hardware type).

### M8: Secrets and config for Auth0
Client secret/domain in git or `skypane.env` world-readable; logged by request logging; shown in the companion. Prevention: PKCE with public flow is possible but Auth0 regular web app still uses a client secret at the token endpoint: keep it in the systemd `EnvironmentFile` mode 0600, redact in logs, and in the health page show only "configured: yes/no". Authorization codes, tokens and the `code` query param must not be logged (Caddy access logs include query strings: configure log redaction for `/callback`). **Phase:** P6.

### M9: Admin console exposure
Remote admin on the same public hostname as the device endpoints enlarges attack surface (the device API was poll-only by design). Prevention: admin routes under the same auth, rate-limited; consider a Caddy IP/path restriction or mTLS optional; audit log of admin actions (who pushed firmware to which device); destructive actions need confirmation + CSRF. Device endpoints must not accept session cookies and the web routes must not accept device tokens. **Phase:** P6.

### M10: Wake interval and quiet-hours semantics per device and timezone
Quiet hours are Europe/Paris-only DST arithmetic; "anywhere in France" includes overseas territories with other timezones; config floor 60 s vs deployed 30 s already conflicts. Prevention: store an IANA timezone per device (default Europe/Paris), reuse existing DST-safe code with tz parameter, keep legacy value preserved through migration even if below the new form floor (warn, do not clamp silently). **Phase:** P4.

### M11: Credits page obligations forgotten or incorrect
adsb.fi requires credit; OurAirports, adsb.lol, adsbdb attributions; licences in `COMPLIANCE.md` drifting from the page. Prevention: credits page generated from one data file also used by `COMPLIANCE.md` checks; a test asserts every provider enabled in config appears on the page (behavioural: fetch the served page). Shown to non-logged-in or all users. **Phase:** P7.

### M12: Detection-mode UX produces invalid configs
"Aircraft around a position" with a radius of 250 NM, or at 0,0, floods the provider and the frame; airport + runway chosen for an airport without ADS-B coverage. Prevention: validate bounds (radius cap, France bounding box), per-user device count cap, server-side validation independent of UI, show "no coverage" hint. **Phase:** P5.

---

## Minor Pitfalls

### m1: Comment-history guard debt (P9) interacting with new code
New v1.2 code written in P1-P8 will cite "Phase 51", "D-03" etc. in comments, enlarging debt and failing `check_comment_history.py` in CI mid-milestone. Prevention: the guard stays enforced for new/changed lines from phase 1 (baseline file of known violations that may only shrink), and P9 only burns down the baseline. Do not bulk-rewrite comments earlier: it creates merge conflicts with phases touching the same files and with v1.1. **Phase:** P9, rule applied in all.

### m2: Function-size gate (80 lines) and mypy module list
Auth callback and migration code tend to be long single functions; new modules must be added to `[tool.mypy]`. Prevention: split into validate/exchange/create-session steps (also easier to test). **Phase:** P1, P6.

### m3: Version strings
`X-Fw-Version` regex allows `[A-Za-z0-9._-]{1,31}`; semantic version comparison by string breaks. Use a separate integer build number header. **Phase:** P2.

### m4: Hash-locked requirements and "stdlib only" drift
Temptation to add `authlib`/`pyjwt`/`cryptography` for Auth0 contradicts the owner's constraint and hash-locked requirement process. Prevention: if signature verification is later wanted, JWKS RS256 verify needs big-int RSA with stdlib (feasible but easy to get wrong - padding checks); not recommended; rely on the token-endpoint-over-TLS path and document the rationale in the plan. **Phase:** P6.

### m5: Time and clock
Session expiry, pairing TTL, OIDC `exp` use `time.time()`; VPS clock drift or tests with real sleeps. Inject a clock; check NTP on VPS. **Phase:** P6.

### m6: Logout and Auth0 session
App logout does not end the Auth0 SSO session, so "logout" instantly re-logs in. Use Auth0 `/v2/logout?returnTo=` with an allow-listed URL, or accept and document. **Phase:** P6.

---

## Phase-Specific Warnings

| Phase | Topic | Likely Pitfall | Mitigation |
|-------|-------|---------------|------------|
| P1 Data model + migration | Migrating the live frame | C13, C14, M1, M2: identity regeneration, half-migration, backup of live DB | Idempotent forward-only migration, keep MAC/secret, expand-only, old code can run on new state, freeze list for Phase 47 |
| P1 | Roles/identity schema | C2: email keyed identity | Unique `(iss, sub)`; bootstrap admin out of band |
| P2 OTA per hardware | Wrong binary / downgrade | C10, C11, M3-ish, m3 | `(hardware_type, version)` registry, app-desc check on upload and on device, monotonic build integer, canary and `X-Ota-Result` halting, decide signing before P8 |
| P2 | Legacy frames with no hardware header | Treated as "any" | Explicit default type for header-less legacy requests only |
| P3 Image format | Old frames choke on header | C12 | Version negotiation by capability header, firmware parser validation, golden fixtures, OTA first then serve v2 |
| P3 | Hash-skip semantics | M3, C12 | Hash covers served bytes; format change changes hash; per-device retention |
| P4 Per-device config / poll budget | Request multiplication | C15, C16 | Zone cells, global persisted rate gate (1 req/s), shared adsbdb cache, fake-clock fleet test |
| P4 | Per-device state paths, tz | C5, M10 | One accessor, IANA tz per device, preserve legacy sleep_s |
| P5 Detection modes | OurAirports geometry | C17, M12 | Vendored, validated snapshot; replay test vs hand-tuned Orly geofence; parallel runway disambiguation; research flag |
| P6 Auth0 + accounts + ownership + pairing + admin | OAuth flow checks | C1, C3, C6-C9, M7-M9, m4-m6 | Faux Auth0 harness first; route policy table default-deny; invite-only; cookie/CSRF/redirect tests; legacy flag with removal date |
| P6 | Ownership | C5, C18 | Single device accessor, 404 for foreign, route x role x owner matrix test |
| P7 Per-hardware render/battery/credits | Regressions and wrong battery figures | M5, M6, M11 | Golden image of legacy device, battery params with provenance, credits page generated from data |
| P8 Second hardware | First real non-simulated type | C10, M5, C18 | Cable-flash first, OTA only after, measure battery, pairing path for hardware without BLE; simulated-type tests reused |
| P9 Comment-history debt | Conflicts and guard drift | m1 | Shrink-only baseline enforced from P1; bulk rewrite last |

### Suggested restructuring hints for the roadmap (non-binding)
- Move "faux Auth0 harness" and "route policy table (default-deny)" to the first plan of P6; add "legacy password removal" as an explicit late task, not an implicit one.
- P2 should precede P3 strictly (C12 needs OTA to roll out the v2-capable firmware), and the P3 firmware parser should ship in the same OTA as the P2 hardware-type header, to save one field OTA of the single deployed frame (each OTA of the only frame in the field is a risk during Phase 47).
- Put the 1 req/s gate into P4 before P5 adds more device modes; P5 should not issue provider requests except via that gate.
- P5 needs a dedicated research step (runway data and replay harness); P6 needs a short research step only for Auth0 tenant settings (signups, allowed callbacks, logout URLs), the code patterns are standard.
- P8: do not mark done until a real OTA to the second hardware and a measured battery sample exist.

## Sources

- RFC 6749 (OAuth 2.0), RFC 7636 (PKCE), OAuth 2.0 Security BCP (RFC 9700), OpenID Connect Core 1.0 sections 3.1.3.7 (ID token validation; TLS server auth may replace signature check for token endpoint responses) - standards knowledge, HIGH for the checklist, not re-fetched today.
- OWASP Cheat Sheets: Session Management, CSRF Prevention, Unvalidated Redirects, IDOR (Authorization) - MEDIUM, from training.
- ESP-IDF OTA docs (app rollback, `esp_app_desc_t`, secure OTA / app signing v2) - MEDIUM, from training; verify against ESP-IDF 5.3.1 docs at P2/P8 planning.
- Repo evidence: `stub-server/byos_server.py` (devices.json, content-addressed `/img/` and `/fw/`, X-Fw-Version / X-Ota-Result parsing), `.planning/PROJECT.md` Key Decisions (NVS stale-token lesson, wake-interval floor vs deployed 30 s, quiet-hours duplication, ADS-B provider decisions), CLAUDE.md conventions (stdlib only, function-size gate, comment-history guard, behaviour-over-source tests).
- OurAirports data dictionary (`runways.csv` fields: le/he ident, lat/lon, heading_degT, closed) - LOW-MEDIUM, from training; verify at P5.
- ADS-B provider constraints: taken as given from the owner's 2026-10-28 research, not re-verified.
