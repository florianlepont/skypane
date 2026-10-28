# Project Research Summary

**Project:** SkyPane, milestone v1.2 Fleet platform (workstream `v1-2`, phases 48+)
**Domain:** Small invite-only multi-user, multi-device, multi-hardware e-ink "BYOS" fleet on one VPS, added to a shipped single-frame system
**Researched:** 2026-10-28
**Confidence:** MEDIUM. The four reports differ in evidence quality and contradict each other in places. Tags **[HIGH]**, **[MEDIUM]**, **[LOW]** follow the reports; MEDIUM and LOW claims are unverified or rest on training knowledge, press or community posts.

## Executive Summary

v1.2 turns a one-frame system into a fleet of a few frames owned by a few invited relatives, with no new dependency and no new daemon. The four reports agree on the shape:

- Identity and ownership live in a stdlib `sqlite3` `fleet.db` with `PRAGMA user_version` migrations.
- Hardware types are a server-side registry (code, not a table).
- Each device gets its own directory shaped like today's `state_dir`, so `device_config`, `state_store`, `poll_cycle` and `history_db` are re-pointed, not rewritten.
- The migrated frame keeps its MAC, secret, token and file paths: no reflash, no re-enrolment.
- The poll loop becomes a fleet cycle that groups devices into zones and does one upstream ADS-B fetch per zone under a global budget.
- The companion gets hand-written Auth0 login (authorization code + PKCE; ID-token signature check skipped as OIDC Core 3.1.3.7 allows for a direct token-endpoint response), local roles, a default-deny route table with an ownership gate, and an admin console.
- `server/requirements.txt` does not change [HIGH].

Main risks: (1) a shared OTA registry would offer the wrong binary to a second hardware type (brick risk); (2) a headered image format must not reach firmware that cannot parse it; (3) many easy-to-miss auth checks (state, nonce, PKCE, iss/aud/exp, link by `sub`, closed signup, default-deny routes, device IDOR); (4) a naive per-device poll loop blows the 1 req/s ADS-B budget; (5) v1.1 Phase 47 (field validation of the same frame on the same VPS) is still open, so everything must be expand-only and behaviour-preserving for the legacy frame.

## Key Findings

### Recommended Stack

**Zero new runtime dependencies [HIGH]** (stdlib, Pillow 13.0.0, requests 2.34.2).

- **Auth0:** code + PKCE S256 with `state` and `nonce`, ~150 lines in a new `companion/oidc.py`. Claims-only validation of the ID token (exact `iss` with trailing slash, `aud`/`azp`, `exp`, `iat`, `nonce`, `sub`); no runtime discovery or JWKS.
- **App type [MEDIUM]:** Regular Web App with `client_secret` + `code_verifier`; gate = one smoke test on the real tenant. Fallback: Native app, pure PKCE.
- **Sign-up/roles:** sign-up disabled on a dedicated database connection [MEDIUM]; roles `admin`/`user` live in the local DB; link `sub` once via a verified email, then match on `sub` only; local `disabled` flag checked per request.
- **Sessions:** signing key independent of the shared password (`SKYPANE_SESSION_SECRET`).
- **Image container:** little-endian header (`SPIM`, version, header_len, width, height, pixel_format, `palette_id`, flags, payload_len, crc32), palette registry by id, no compression in v1; served only to firmware that announces support, legacy raw 960000-byte images otherwise.
- **Hardware profiles:** committed registry (geometry, palette id, battery profile, firmware target, wake bounds).
- **Airports [HIGH, measured]:** OurAirports (public domain) compiled offline to a committed France JSON. 258 of 548 `LF*` runway rows lack coordinates: drop rows without both thresholds, compute bearings from thresholds. Orly "runway 3" is the `07/25` row.
- **ADS-B:** one shared budget, providers queried sequentially, zone merge (≤ 250 NM), per-cycle cache. adsb.fi v2 `lat/lon/dist` is deprecated (no sunset date); v3 uses array key `ac` (silent-failure risk in existing code).
- **Tests:** loopback fake Auth0 in `test-support/` with negative modes.
- **Integration rules:** `companion/auth.py` stays stdlib-only (sibling modules); add new modules to the mypy list; functions ≤ 80 lines.

### Expected Features (MEDIUM)

Must have (P1): entities with one owner per device; migration of the live frame; two roles enforced server-side; reduced user view (name, location, detection mode, quiet hours, language, read-only battery/last seen); admin fleet console; invite-only Auth0 sign-in; pairing by short code; per-device scoping of everything global; two detection modes; "applies at next wake" feedback; per-hardware render/battery/health; credits page; per-user EN/FR.

Should have (P2): airport search with runway picker; read-only "view as owner"; "add hardware type" recipe; admin-actions log.

Defer: QR on the pairing screen, map picker, offline banner, device sharing, scheduled modes, remote commands, fine-grained RBAC, open signup, per-user firmware/artwork, billing, websockets.

### Architecture Approach (HIGH on seams, MEDIUM on design)

Same six systemd units. New persistence: `fleet.db` plus the existing atomic-JSON pattern. Per-device state under `devices/<id>/` (legacy frame keeps `state_path = "."`). Shared: airline overrides, manual resolutions, illustrations, adsbdb cache.

Single-frame assumptions verified in code: one global OTA registry with no hardware key; OTA event scans span all devices; device-side OTA check is only `project_name == "skypane"`; byos serves one fixed-size image; `_resolve_device_id` falls back to `"default"`; global `/img` store with `IMG_KEEP = 8`; battery telemetry attributed by tailing Caddy logs; `detect.py` hard-wired to LFPO runway 3; one shared password and `auth_required: bool`; backup allow-list names files individually.

Components: `fleet_db.py`/`hardware.py`/`fleet_migrate.py`; `firmware_registry.py` schema 2; `imgfmt.py`; `fleet_cycle.py` + `plane/zones.py` + `plane/budget.py`; byos per-device; `companion/oidc.py`, `accounts.py`, `Route.access` (public/user/admin), `/d/<device_id>/…` routes, `require_device()` (404 on foreign devices); admin console, audit log, credits page, airports catalogue.

Anti-patterns: trusting device-reported `hw_rev`/`X-Fw-Version` for authorisation; an "active device" cookie; per-device ADS-B fetches; auto-creating users on first login; moving the legacy frame's files; changing the legacy OTA project name.

### Critical Pitfalls (MEDIUM)

1. Wrong firmware / downgrade / integrity: registry keyed `(hardware_type, version)`, server-assigned type, upload-time descriptor check, monotonic build number, missing header = legacy only, canary rollout.
2. Image format breaks deployed frames: capability negotiation, server first, hash covers served bytes, golden fixtures + byte-identical legacy regression.
3. Live-frame migration while Phase 47 is open: idempotent, forward-only, expand-only; old code must run on post-migration state; freeze list; backup before deploy.
4. Auth checklist: single-use state/nonce/PKCE in a Lax pre-login cookie; closed sign-up in two layers; default-deny route matrix; CSRF; fixed redirect URI; secrets only in env; redact `/callback` in Caddy logs.
5. ADS-B budget: zone cells + persisted global gate, fake-clock fleet test, backoff/circuit breaker, shared adsbdb cache with negative caching.
6. Runway geometry: vendored validated snapshot, replay test against the hand-tuned Orly geofence, parallel-runway disambiguation.
7. Pairing as attack surface: single-use expiring rate-limited code, atomic claim, no silent transfer, server-generated device id.

## Conflicts Between the Reports

| # | Topic | Recommendation | Owner? |
|---|---|---|---|
| 1 | ADS-B cap: global vs per provider; in-process bucket cannot work across a oneshot poll + companion | Sequential global rule + persisted flock ledger shared with poll-now | yes |
| 2 | Zone sizing/rounding, capacity quoted 14 vs 20+ zones | 0.01° for privacy; prove large-radius merge in the phase | |
| 3 | Session model: stateless HMAC + per-request check vs server-side store | Lean stateless + `session_epoch` check; independent secret | yes |
| 4 | First admin / linking | Link once via verified admin-created email, then `sub` only; unique `(iss, sub)` | yes |
| 5 | Invites | Pre-registered email suffices | |
| 6 | How a new frame becomes known | Admin-provisioned; pairing = bind owner via short on-panel code; research flag | yes |
| 7 | Hardware type assigned or reported | Server-assigned, authoritative; flag mismatches | |
| 8 | Registry: code or table | Code registry; simulated types are entries | |
| 9 | Image negotiation signal | One explicit capability header (`X-Img-Fmt`); server never requires it | |
| 10 | STACK header table is 21 bytes but its struct string is 24 | Layout undecided; settle in Phase 50 spec | |
| 11 | Image URL shape/retention | Per-device retention; URL change depends on firmware `image_url` constraints [LOW] | |
| 12 | Render approach / simulated geometry | Two simulated types (same geometry; 800×480 landscape); final call after hardware choice | |
| 13 | History DB | One DB per device dir | |
| 14 | When registry rewrite happens | Move out of Phase 48 into Phase 49 with `*.pre-fleet` copy | |
| 15 | Phase 2 vs 3 order / number of OTAs | Server work parallel; one combined legacy-frame firmware release after Phase 47 allows it | yes |
| 16 | Does the device verify an OTA signature? | Unresolved: read `ota.c`/Kconfig at start of Phase 49 | |
| 17 | Orly runway names | Use measured: LFPO `02/20`, `06/24`, `07/25`; "piste 3" = alias for `07/25` | |
| 18 | OurAirports licence | Public domain [HIGH]; credit anyway | |
| 19 | JWT signature work | Skip, per OIDC Core 3.1.3.7 [HIGH] | |
| 20 | CSRF depth | Origin check baseline; decide on tokens in 53a | yes |
| 21 | Cookie attributes | Lax for both; Playwright login test | |
| 22 | Comment-history ordering | Run `check` before Phase 48; baseline approach if it fails on touched files | yes |
| 23 | Second hardware scope | Follow the owner: a v1.2 phase | |
| 24 | Location rounding | See 2 | yes |

## Implications for Roadmap

Numbering continues after v1.1's Phase 47.

- **Phase 48 — Data model + migration (with roles).** `fleet.db`, hardware registry (legacy EE02 + env-gated `sim-*`), idempotent `fleet_migrate`, roles column, unique `(iss, sub)`, `devices_cli`, backup allow-list with sqlite online backup + restore test, drop the `"default"` fallback, Phase 47 freeze list + test. Success: live frame's next poll returns the same `image_hash` and `sleep_s`; previous release still runs on migrated state. No registry rewrite here.
- **Phase 49 — OTA per hardware.** Registry schema 2, per-device schedules, `compute_offer(hardware, device)`, upload-time descriptor check, monotonic build number, CLI `--hardware`, Update page per device. No legacy-frame firmware change here.
- **Phase 50 — Common image format.** `imgfmt.py` + spec, header negotiation, legacy regression, firmware reader accepting legacy and v1, golden baseline. Server side parallel with 49.
- **Phase 51 — Per-device config/image/state + poll loop, budget, zones.** Split 51a (device dirs, per-device byos, health) / 51b (`fleet_cycle`, zones, persisted ledger, detect split, shared adsbdb cache). Fake-clock 100-device test. adsb.fi v3 migration fits here.
- **Phase 52 — Detection modes.** France airport/runway catalogue + build script, runway mode, position + radius mode with bounds, replay harness vs Orly geofence, parallel-runway test. Research flag.
- **Phase 53 — Auth0 + accounts + ownership + pairing + admin console.** 53a gate (fake Auth0 first, `oidc.py`, sessions, default-deny matrix, ownership gate, `/d/<id>`, shared password as flagged legacy admin); 53b pairing; 53c admin console + reduced user view. Research flags for 53a (smoke test) and 53b (device identity).
- **Phase 54 — Per-hardware render/battery/health + credits page.** Profile-driven renderer, battery profile object with provenance, per-device health, credits from one data file (can be pulled forward).
- **Phase 55 — Second hardware (choose, spike, buy, validate).** Shortlist + time-boxed ESP-IDF driver spike; purchase only after; real OTA + measured battery sample before done. Full research.
- **Phase 56 — Comment-history debt.** Run `check` before Phase 48; no new violations in any phase.

### Research Flags
Needs research: 49 (device-side OTA checks, signing), 50 (`image_url` constraints), 52, 53a, 53b, 55. Standard: 48, 51, 54, 56.

## Decisions Reserved for the Owner

1. OTA image signing (TLS+SHA-256 only vs ESP-IDF secure OTA; later enabling may need a cable flash).
2. QR pairing vs text code (QR encoder is the only thing that would add a dependency).
3. Auth0 app type (smoke test decides), tenant region/domain, dedicated DB connection, no social logins.
4. adsb.fi v3 migration (touches validated detection code).
5. Shared-password removal date.
6. Second hardware: which board, whether to buy (EE04 7.3" plausible on paper; no ESP-IDF driver found [LOW]; buy only after spike).
7. ADS-B policy: global vs per-provider cap; paid/feeder-gated providers; airplanes.live opt-in only.
8. Phase 47 coordination: when v1.2 deploys and the legacy-frame firmware OTA may go out.
9. Session model and CSRF depth.
10. First-admin bootstrap and invite style.
11. Comment-history ordering.
12. Airport scope (France only? sizes? overseas? keep "piste 3" alias?).
13. Location precision sent to third parties and who sees stored coordinates.
14. Credits page placement and timing.
15. Second-hardware scope inside v1.2.
16. Smaller: per-user device cap, "view as user", header name/fields, Auth0 logout.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | MEDIUM-HIGH | Auth0 discovery, OIDC text, OurAirports and adsb.fi probed 2026-10-28; PKCE on confidential app and EE04 effort/price MEDIUM; one header-spec inconsistency |
| Features | MEDIUM | Training-based product conventions |
| Architecture | HIGH on seams, MEDIUM on design | Read from named repo files; second-hardware firmware LOW |
| Pitfalls | MEDIUM | Standards + OWASP, nothing web-fetched |

**Overall:** MEDIUM. Direction well supported; weak spots are the contradictions above and second-hardware firmware.

### Gaps to Address
EE04 firmware effort [LOW]; device-side OTA signature check; PKCE on confidential app; sign-up-disabled behaviour and free-tier limits; corridor defaults outside Orly; cookie behaviour across the Auth0 redirect; firmware `image_url` constraints; real ADS-B cost per zone; current enrolment path and eFuse-MAC stability; current output of `check_comment_history.py`; reliance on the `"default"` device fallback; legacy battery numbers wait for Phase 47; adsb.lol future API-key terms.

## Sources
Primary: OIDC Core 1.0 §3.1.3.7; RFC 9700/7636/6749; Auth0 docs and live discovery; OurAirports dumps (2026-10-28); adsb.fi README and live probes; repo files read by the researchers. Secondary: Auth0 community/support posts; CNX Software, Hackster, OpenELAB (EE04); OWASP, ESP-IDF OTA docs (from training). Tertiary: product patterns (TRMNL, Tidbyt, Hue/Sonos, Home Assistant); EE04 toolchain claims.

---
*Research completed: 2026-10-28*
*Ready for roadmap: after the owner confirms the decision list or accepts the stated recommendations as defaults*
