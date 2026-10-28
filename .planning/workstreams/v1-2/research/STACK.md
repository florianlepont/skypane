# Stack Research

**Domain:** v1.2 Fleet platform on the shipped SkyPane stack (stdlib + Pillow + requests only)
**Researched:** 2026-10-28
**Confidence:** MEDIUM-HIGH. Auth0/OIDC/PKCE, OurAirports and adsb.fi v3 were checked live or against primary docs today. Two points stay MEDIUM and are flagged below: PKCE on an Auth0 *Regular Web App*, and the EE04 7.3" firmware effort.

**Headline: v1.2 needs zero new runtime dependencies.** Everything below is stdlib (`base64`, `hashlib`, `hmac`, `secrets`, `urllib.parse`, `json`, `csv`, `sqlite3`, `struct`, `zlib`, `math`, `zoneinfo`), Pillow 13.0.0 and requests 2.34.2 (already hash-locked in `server/requirements.txt`). `server/requirements.txt` does not change. The only candidate for an owner decision is a QR-code encoder for pairing, and the recommendation is to defer it and not add one.

Data-source licensing (adsb.fi, adsb.lol, airplanes.live, adsbdb) was researched on 2026-10-28 and is reused as is. OurAirports licensing is new and is covered below.

## Recommended Stack

### Core Technologies (new capabilities, no new packages)

| Capability | Technology | Version | Purpose | Why |
|------------|-----------|---------|---------|-----|
| Auth0 login | OAuth 2.0 authorization-code + PKCE (S256) with OIDC `nonce`, hand-written over `urllib.parse` / `hashlib` / `secrets` / `base64` | RFC 6749, RFC 7636, OIDC Core 1.0, RFC 9700 | Browser login via Auth0 EU hosted login page | Auth0 documents S256 as its only PKCE method. The discovery document of a live tenant lists `code_challenge_methods_supported: [S256, plain]` and `token_endpoint_auth_methods_supported: [client_secret_basic, client_secret_post, private_key_jwt, none]`. The whole client is about 150 lines. |
| ID-token validation | Decode the JWT payload only. Validate `iss`, `aud` (and `azp` when `aud` is a list), `exp`, `iat`, `nonce`. Skip the signature check. | OIDC Core 1.0 section 3.1.3.7 step 6 | Satisfies "no JWT or crypto dependency" legally and safely | The spec says that when the ID token arrives by direct communication between client and token endpoint, "the TLS server validation MAY be used to validate the issuer in place of checking the token signature". Our flow is exactly that: server-to-server POST to `/oauth/token` over verified TLS (HIGH, spec text fetched today). The signature check is only mandatory for tokens that arrive by any other path (front channel, a cookie, a client-supplied token). We never accept one. |
| Redirect and session binding | Existing HMAC-signed `sp_session` cookie (`companion/auth.py`), extended to carry a local `user_id`. A separate short-lived pre-login cookie (`SameSite=Lax`) plus an in-memory pending-login table keyed by `state`. | stdlib | Local session after Auth0 login | Keeps one session mechanism. The pending table (state to nonce, verifier, created_at) is a bounded in-memory dict with a TTL, the same stateful exception the revocation set in `auth.py` already is. |
| Outbound token call | `server.http_fetch.pinned_request` (already stdlib `http.client` + SSRF pinning), not a new client | existing | `POST https://{tenant}.eu.auth0.com/oauth/token` | Reuses the deadline and size-capped, no-proxy, no-redirect primitive. Auth0 is a fixed, operator-configured host, so the pinning is belt-and-braces, but it keeps the code path uniform and testable. `requests` is also acceptable if the companion/server import boundary is a problem (see Integration). |
| Runway geometry | OurAirports `runways.csv` + `airports.csv`, parsed with stdlib `csv`, compiled at build time to a committed France JSON catalogue | CSV dumps from `davidmegginson.github.io/ourairports-data`, nightly | Airport + runway picker, and the per-runway corridor geofence | Public domain (see below). Already the source of the existing Orly runway-3 geofence (`adsb-test/runway3.json` cites it). The generalisation is mechanical. |
| Spherical geometry | `math` (haversine, initial bearing, cross-track and along-track distance) | stdlib | Corridor test, zone clustering, "aircraft around a position" radius | The existing runway-3 detector already does this. Lift it into one `geo` module. No shapely, pyproj or geopy. |
| Fleet data model | `sqlite3` with `PRAGMA user_version` migrations, WAL, `foreign_keys=ON` | stdlib (SQLite bundled with Python 3.14) | users, devices, hardware_types, locations, device_config | `history_db.py` already runs on sqlite3 with a per-thread connection scope. A migration runner is about 40 lines. No Alembic or SQLAlchemy. |
| Versioned image container | Fixed binary header via `struct` (little-endian) + `zlib.crc32` + Pillow for render/quantise | stdlib, Pillow 13.0.0 | Common image format: width, height, palette in header | See "Image format" below. Firmware is little-endian (ESP32-S3), so `<` packing maps to a C struct with no byte swapping. |
| ADS-B budget and zone grouping | stdlib `threading`, `time.monotonic`, a global token bucket, greedy circle clustering using `math` | stdlib | Keep total upstream traffic at or below 1 request/s across all zones and both providers | See "ADS-B budget" below. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Pillow | 13.0.0 (locked) | `Image.quantize(palette=...)`, `Image.putpalette`, `Image.resize`, `ImageDraw` per hardware profile | Per-hardware-type rendering (800x480 landscape vs 1200x1600 portrait) and Spectra 6 palette mapping. Nothing new needed. |
| requests | 2.34.2 (locked) | Existing provider polls (`detect.py`) | Unchanged. Keep it out of `companion/auth.py` (stdlib-only module). |
| `zoneinfo` (stdlib) | n/a | Per-device quiet hours in the owner's timezone | Existing Europe/Paris logic becomes per-device. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| Fake Auth0 (new test helper in `test-support/`, `ThreadingHTTPServer` on loopback) | Exercise login end to end in pytest and the Playwright browser tests | Implements `/authorize` (302 back with `code` and `state`, checks the S256 challenge) and `/oauth/token` (checks `code_verifier` against the stored challenge, returns `id_token`, `access_token`, `token_type`, `expires_in`). The fake ID token needs no real signature. Give it a dummy `RS256` header and junk signature so the production code is proven never to depend on the signature. Add negative modes: wrong `nonce`, wrong `iss`, wrong `aud`, expired, bad verifier, replayed code, `state` mismatch. Fits the existing pytest-socket loopback guard. |
| Committed OurAirports snapshot + `scripts/build_airports.py` | Reproducible catalogue | Download is a manual or CI-optional step. The runtime never fetches OurAirports. Tests read the committed JSON. |
| Existing gates (ruff, mypy module list, function-size at 80 lines, comment-history guard, coverage floor) | Unchanged | Add new modules to the mypy list in `pyproject.toml`. Keep functions under 80 lines (the token-exchange and callback handler are the likely offenders, so split by step). |

## Auth0 specifics (verified)

**Tenant and endpoints (EU).** Derive everything from one configured domain, `https://{tenant}.eu.auth0.com` (or a custom domain):
- `GET /authorize`, `POST /oauth/token`. Confirmed in a live discovery document (`/.well-known/openid-configuration`) of a public Auth0 tenant.
- `issuer` is `https://{domain}/` **with a trailing slash**. Compare the `iss` claim by exact string equality against `"https://%s/" % domain`. A custom domain changes the issuer, so configure the domain, not the tenant name.
- Do not fetch discovery at runtime. Build the URLs from the configured domain (fewer moving parts, no extra TLS fetch, no JWKS). `end_session_endpoint` was absent from the older sample tenant. For a tenant created on or after 2023-11-14, RP-initiated logout is on by default (Auth0 docs). Cache or pin it if logout against Auth0 is wanted.

**Authorize request** (Auth0 docs, fetched today): `response_type=code`, `client_id`, `redirect_uri`, `scope=openid profile email`, `state`, `nonce`, `code_challenge`, `code_challenge_method=S256`. Do **not** send `audience`: there is no API, so no access token is needed (it avoids an opaque/JWT access-token question entirely). Do not request `offline_access`: the companion keeps its own session and does not need refresh tokens.

**PKCE generation** (Auth0 docs and RFC 7636): verifier = `base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=")`. Challenge = `base64url(sha256(verifier_ascii))` without padding.

**Token request**: form-encoded `grant_type=authorization_code`, `client_id`, `code`, `redirect_uri` (exact match), `code_verifier`, plus `client_secret` (see next paragraph).

**Application type (decision, MEDIUM).** Register a **Regular Web Application** and send **both** `client_secret` (`client_secret_post`) and the PKCE `code_verifier`. Reasoning:
- Auth0 treats Regular Web Apps as confidential clients and authenticates them at the token endpoint with a secret (Auth0 docs, "confidential and public applications").
- RFC 9700 (OAuth 2.0 Security BCP, 2025) says PKCE is RECOMMENDED even for confidential clients, and that the PKCE-using client may rely on it for CSRF only if it has confirmed the server supports it. We still send `state` and `nonce`, so this is moot.
- The owner asked for "authorization code + PKCE". Doing both gives PKCE plus a secret held only in the `skypane.env` file.
- Caveat: an Auth0 community staffer says the Regular Web App *SDKs* do not use PKCE, but that sending it is technically possible. I did not find Auth0 documentation that explicitly guarantees `code_challenge` is honoured for a confidential app. **Gate:** one manual smoke test against the real tenant in the auth phase (login succeeds, and a wrong `code_verifier` is rejected). Fallback if it fails: a **Native** app type with token auth method `none` (pure PKCE, no secret). That variant is also fully supported (Auth0 docs) but forces RS256 ID tokens, which we do not care about.

**Sign-up disabled.** Database connection, "Disable Sign Ups" toggle (Dashboard: Authentication > Database > connection > Settings). It blocks the public `/dbconnections/signup` endpoint, while the Dashboard and Management API can still create users, so the admin invites a relative by creating the Auth0 user. The setting is per connection and applies to every application using it (Auth0 support), so use a dedicated connection for SkyPane. Disable social connections or leave them off, otherwise they bypass this. Do not send `screen_hint=signup` (unverified how a disabled tenant handles it).

**Roles.** Keep `admin` / `user` **in the local database, not in Auth0 RBAC**. Auth0 roles reach the ID token only through a post-login Action that adds a namespaced custom claim, which is more Auth0-side configuration, drift between two stores and a lockout risk. The local DB is already needed because devices are owned by a local user. The `sub` is stored on first login.

**Account linking.** Admin pre-registers a local user with the invited email. On the first Auth0 login, if `email_verified` is `true` and the email matches a local user whose `sub` is null, bind `sub` to that user. After that, look up **only by `sub`** (never by email again). Treat `sub` as an opaque string (Auth0 uses `auth0|…`, `google-oauth2|…`) with a length cap. Refuse unverified emails and unknown subs (no auto-provisioning, because sign-up is closed anyway). Local `disabled` flag is checked on every request, so revocation is instant even though the cookie is stateless.

**Required checks on the ID token** (OIDC Core 3.1.3.7): `iss` exact; `aud` contains our `client_id` (string or list; if a list with several entries, `azp` must equal `client_id`); `exp` in the future (allow small skew, e.g. 60 s); `iat` not absurdly far in the past or future; `nonce` equals the stored one (`hmac.compare_digest`); `sub` present. Also reject a header with `alg: none`, as cheap belt-and-braces even though no signature is checked. Never read an ID token from anywhere except the `/oauth/token` response body.

## Image format (common, versioned)

Current wire format (verified in `firmware/main/api_client.h`, `stub-server/make_test_panel.py`): raw headerless **960000 bytes** = 1200x1600 at 4 bits/pixel, left pixel in the high nibble, Spectra 6 nibble codes (0 black, 1 white, then yellow, red, blue, green). The firmware hard-gates the download length to exactly `FP_IMAGE_BYTES` and verifies SHA-256.

Recommended container (little-endian, `struct.pack("<4sBBHHHBBBBII", ...)`, 24 bytes, fixed so a C struct maps 1:1):

| Field | Type | Meaning |
|-------|------|---------|
| magic | 4 bytes | `b"SPIM"` |
| version | u8 | format version, starts at 1 |
| header_len | u8 | bytes in the header, so later versions can append fields and old readers skip them |
| width, height | u16, u16 | pixels |
| pixel_format | u8 | 1 = packed 4 bpp, high nibble first |
| palette_id | u8 | 1 = Spectra 6 (6 entries with the controller codes listed above) |
| flags | u8 | bit 0: reserved for compression (not used in v1) |
| payload_len | u32 | must equal `ceil(width*height*bpp/8)` |
| crc32 | u32 | `zlib.crc32` of the payload, cheap integrity check on top of SHA-256 |

- Put the palette as an **id plus a registry**, not RGB triples inside every image. The palette registry lives in the hardware-profile table (server) and a constants table (firmware). An id is enough for "palette in header" (what the device needs is the controller code mapping, not display RGB), and it avoids the display RGB vs controller code confusion.
- **Backward compatibility by negotiation, not sniffing alone.** The poll request already carries `X-Fw-Version`. The server serves legacy raw 960000 bytes to any firmware that does not announce container support, and `SPIM` to firmware that does. Legacy blobs are also self-identifying (exactly 960000 bytes, no magic), so a new firmware accepts both during rollout. Old firmware would reject any other length, which is the safe failure.
- Content addressing stays: `/img/<sha256>.bin`, with the SHA-256 computed over the whole file including the header.
- No compression in v1: 1200x1600 = 960 KB and 800x480 = 192 KB are fine on the existing path. Revisit only if wake energy shows the download dominates.

## Hardware profiles

Server-side static registry (Python dict or JSON committed in the repo; DB rows seeded from it), keyed by hardware-type id: `width`, `height`, `orientation`, `palette_id`, `image_format_version`, `battery_profile` (voltage-to-percent points, low and critical thresholds), `firmware_target` (ESP-IDF target and build config), `wake_bounds`. Do not make it user-editable. No new technology. Pillow drives per-profile layout.

**Candidate second type (not chosen; for the owner's purchase decision):**

| Option | Facts found | Fit |
|--------|-------------|-----|
| Seeed XIAO ePaper DIY Kit **EE04** + 7.3" Spectra 6 panel | ESP32-S3R8 (8 MB PSRAM, 16 MB flash), 3.7 V LiPo JST + charger, 24-pin and 50-pin FPC; panel 800x480, six colours; kit board $9.90, panel in the $5.85 to $45 range (CNX Software, Hackster); an EU reseller lists the full 7.3" kit at about 70 EUR incl. VAT (OpenELAB, price may be stale). | Same SoC family and the same ESP-IDF target (`esp32s3`) as EE02, 192 KB framebuffer vs 960 KB, same Spectra 6 colour set. **Landscape 5:3 vs portrait 3:4**, so the layout needs a separate template. |
| Other XIAO ePaper sizes (1.54" to 7.5") | Same vendor range (CNX). 10.3" and 13.3" are not supported by EE04/EN04 per CNX. | Monochrome or 3 or 4-colour panels would need a second palette id and a different layout. Not recommended for a first expansion. |

**Open risk (LOW confidence, needs phase research):** no ESP-IDF driver or pin map for the EE04 + 7.3" panel was found; Seeed documents Arduino IDE, PlatformIO and ESPHome. The panel controller, init sequence and GPIO map differ from the 13.3" dual-chip `epd13in3e.c`. Expect a new `epd7in3e.c` panel module and a per-hardware-type build target. The server, image container and renderer are the easy part. The firmware panel driver is the real cost, so the second-hardware phase needs its own research. Keep it last, as the roadmap already has it.

## OurAirports (verified today)

- **Licence:** "released into the public domain, with no warranty" (ourairports.com/data). No attribution legally required. Credit it on the credits page anyway (it is a courtesy and cheap).
- **Files:** `airports.csv` 12.7 MB, `runways.csv` 4.0 MB, regenerated nightly, mirrored at `https://davidmegginson.github.io/ourairports-data/{airports,runways}.csv` (GitHub repo `davidmegginson/ourairports-data`).
- **runways.csv columns (20):** `id, airport_ref, airport_ident, length_ft, width_ft, surface, lighted, closed, le_ident, le_latitude_deg, le_longitude_deg, le_elevation_ft, le_heading_degT, le_displaced_threshold_ft, he_ident, he_latitude_deg, he_longitude_deg, he_elevation_ft, he_heading_degT, he_displaced_threshold_ft`. Join to airports on `airport_ident` = airports `ident` (ICAO for LF* airports). `airports.csv` columns: `id, ident, type, name, latitude_deg, longitude_deg, elevation_ft, continent, iso_country, iso_region, municipality, scheduled_service, icao_code, iata_code, gps_code, local_code, home_link, wikipedia_link, keywords`.
- **Measured on the 2026-10-28 dump:** France has 18 `large_airport` + 117 `medium_airport` (+1054 small, 466 heliports, 114 closed). **All 135 large/medium French airports have at least one open runway with both thresholds' coordinates and headings.** For the whole `LF*` set, 258 of 548 runway rows lack coordinates (mostly small strips and grass), so the catalogue must drop or flag rows without both thresholds. For `closed=1` rows (1070 worldwide) exclude. Skip `H*` helipad idents.
- **Orly:** LFPO has three runways, `02/20`, `06/24` and `07/25`. The project's "runway 3" is the `07/25` row (length 10892 ft, 148 ft wide). Computed bearing from the thresholds is 74.39, the file says 74. The catalogue UI must therefore show real designators (`07/25`), and may add a project alias "piste 3" for LFPO only.
- **Compile step:** For each selected runway store `{airport ident, name, municipality, reference point, le/he ident, le/he lat/lon, width_m = width_ft*0.3048, length_m}`. Compute bearing from the thresholds and prefer that over `*_heading_degT`, which is missing on some rows. Generate the same corridor parameters that the hand-written `runway3.json` uses (half width, extension, axis tolerance, on-ground half width). Make those parameters **global defaults, not per-airport**, since they were calibrated on Orly traffic (see the long derivation in `runway3.json`). Different airports may need parallel-runway handling (CDG has four close parallel runways, so a lateral half-width of 500 m would capture neighbours). **Flag:** the corridor defaults are Orly-calibrated and unvalidated elsewhere. Parallel-runway airports (LFPG, LFPB single, LFML, LFLL parallels) need a derived half-width of `min(500, 0.45 * nearest parallel spacing)` or a per-runway override.
- **Scope:** ship only `iso_country = FR`, types `large_airport`/`medium_airport` (+ small airports that have two thresholds if the owner wants gliding fields), as a committed JSON of well under 200 KB. Keep the loader country-agnostic.

## ADS-B budget and zone grouping

- **Verified today:** adsb.fi public endpoints are rate limited to 1 request/second (opendata README). The existing `MIN_SECONDS_BETWEEN_CALLS = 1.1` per provider is separate for each provider, and the two providers run in parallel, so the current implementation could use roughly 2 req/s in total. A "global <= 1 req/s" budget must be across providers.
- **adsb.fi deprecation (action item):** `GET /api/v2/lat/{lat}/lon/{lon}/dist/{dist}` (used by `PROVIDERS["adsbfi"]` in `server/plane/detect.py`) is marked **deprecated but working**. New integrations should use `GET /api/v3/lat/{lat}/lon/{lon}/dist/{dist}`, max radius **250 NM** (a 300 NM request returned HTTP 400). No sunset date. v3 returns the same record fields, but the array key is `ac`, not `aircraft`, and the response keys include `ac, msg, now, total, ctime, ptime`. I compared v2 and v3 field lists for a 100 NM query around Paris: identical aircraft fields. So the migration is a `url_template` plus `aircraft_key: "ac"` change in the provider table. The in-code comment warns this key mismatch fails silently (`data.get(key) or []`), so add a test that asserts a non-empty parse on a recorded v3 fixture. adsb.lol `/v2/point/{lat}/{lon}/{dist}` answered 200 for both 250 and 300 NM, probably clamping. Cap our requests at 250 NM for both.
- **Design (stdlib only):**
  1. One process-wide token bucket (`threading.Lock` + `time.monotonic`, 1 token/s, burst 1) in front of every outbound ADS-B call, shared by all providers. Providers are queried **sequentially** under it, not in parallel. With two providers and one zone, one poll costs about 2 s of budget, and 30 s cycles leave room for roughly 14 zone polls per cycle. That is plenty for a family-size fleet.
  2. Zone key per device: either `(airport ident)` or `(lat, lon, radius)` quantised (e.g. 0.05 degree grid). Devices with the same key share one fetch per cycle.
  3. Greedy merge: cluster zone centres whose enclosing circle (centre distance + each radius) fits within a chosen **query radius <= 200 NM** (headroom under 250). One big query then serves all those devices, filtered locally by each device's own geometry (corridor or radius). The extra payload at 200 to 250 NM is a few hundred KB, so raise the `max_bytes` cap in `bounded_get` for those calls.
  4. Per-cycle result cache keyed by zone (TTL about 20 s) so the companion's "poll now" and the BYOS requests never trigger upstream calls themselves.
  5. When the budget is exceeded, serve the last result and mark it stale. Never spill over the limit. adsb.fi counts 4xx against the limit (existing code comment), so back off on any error.
- No Redis, no APScheduler, no asyncio. The poll stays a systemd-timer oneshot.

## Installation

```bash
# Nothing to install. server/requirements.txt is unchanged (certifi, charset-normalizer,
# idna, pillow==13.0.0, requests==2.34.2, urllib3 - hash-locked via scripts/lock-deps.sh).

# One-off, to (re)build the airport catalogue (not part of the runtime):
curl -fsSLO https://davidmegginson.github.io/ourairports-data/airports.csv
curl -fsSLO https://davidmegginson.github.io/ourairports-data/runways.csv
python3 -I scripts/build_airports.py airports.csv runways.csv > server/data/airports_fr.json
```

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Hand-rolled auth-code + PKCE client (about 150 lines) | Authlib / PyJWT / python-jose / `auth0-python` | Only if the project later needs ID-token signature verification (front-channel tokens, API access tokens, multiple issuers). Those pull in `cryptography` (a compiled wheel), which breaks the hash-locked, stdlib-only posture. The owner has ruled this out. |
| Skip signature, rely on TLS to the token endpoint (OIDC Core 3.1.3.7 step 6) | Verify RS256 against JWKS with stdlib | Possible (`pow(sig, e, n)` plus PKCS#1 v1.5 padding is about 60 lines), but hand-written RSA verification is exactly the kind of crypto code to avoid, and adds no security for a token we received directly over TLS. |
| Roles in the local DB | Auth0 RBAC + Action claim | If many apps shared the Auth0 tenant and roles had to be global. Not here. |
| Regular Web App (secret + PKCE) | Native app type (pure PKCE, no secret) | If the smoke test shows Auth0 rejects `code_challenge` on a confidential app. |
| Static France catalogue built at dev time | Runtime fetch of OurAirports or Overpass | Never at runtime: adds an outbound dependency, nightly churn and a parse-failure mode on the device-serving path. |
| Committed hardware registry | A DB-editable hardware-types table | If non-developers must add hardware without a deploy. Not the case. |
| Greedy circle clustering | A spatial index (R-tree, geohash libs) | At hundreds of zones. A family fleet has a handful. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `PyJWT`, `python-jose`, `authlib`, `cryptography`, `jwcrypto`, `oauthlib`, `requests-oauthlib` | New hash-locked dependency (and a compiled one for `cryptography`) for a check the spec waives on this flow | Stdlib payload decode plus the claim checks above |
| `plain` PKCE method | Defeats PKCE (the challenge equals the verifier). Auth0 itself documents S256 as its only supported method for this flow. | `S256` |
| Implicit flow / ID token in the URL fragment | Front-channel tokens would need a signature check, which we do not do | Authorization code, back-channel exchange only |
| `SameSite=Strict` on the pre-login (state/nonce) cookie | The callback is a cross-site top-level navigation from Auth0, so a Strict cookie is not sent and every login fails the state check. Existing session cookies are `SameSite=Strict` (`companion/auth.py`). | `SameSite=Lax; HttpOnly; Secure` for the short-lived pre-login cookie. Same caveat for the session cookie: a 302 straight from the callback to `/` can land on a cross-site-initiated chain where the browser withholds Strict cookies, so answer the callback with a 200 page that navigates (meta refresh), or set the session cookie `Lax`. MEDIUM confidence (browser behaviour); cover it with the Playwright login test. |
| Trusting `email` without `email_verified`, or matching by email after first link | Account takeover through an email change | Link once, then match on `sub` |
| Putting `client_secret` in the repo, `deploy/`, logs or the companion HTML | Secret leakage | `skypane.env` only (same pattern as `SKYPANE_COMPANION_PASSWORD`); redact in error paths |
| Loading discovery or JWKS at runtime | Extra outbound calls and an SSRF surface for no benefit without signature checks | URLs derived from the configured domain |
| `http://` Auth0 domain outside tests | Token exchange over cleartext | Require `https`, allow `http` only for loopback behind an explicit test-only env flag (like `SKYPANE_COMPANION_INSECURE_COOKIES`) |
| An ORM / migration framework (SQLAlchemy, Alembic, peewee) | Dependency weight for 5 small tables | `sqlite3` plus a `user_version` runner |
| A geo library (shapely, pyproj, geopy, geopandas) | Heavy compiled wheels for haversine arithmetic you already have | `math` |
| A QR-code library (qrcode, segno) for pairing | New dependency just for onboarding | Show a short pairing code as text on the frame (Pillow text). Treat a QR encoder as a later, owner-approved decision. |
| Querying both ADS-B providers in parallel under a 1 req/s global budget | Doubles the instantaneous rate | Sequential calls through the shared bucket |
| Sending an adsb.fi v2 deprecated URL in new code | May be removed (no sunset date given) | v3 with `ac` key |
| Treating OurAirports `*_heading_degT` as always present | Missing on many rows | Bearing computed from the thresholds |
| Embedding RGB palettes in the image header | Confuses display colours with controller codes and bloats every image | `palette_id` registry |

## Stack Patterns by Variant

**If the Auth0 smoke test shows the confidential app ignores or rejects PKCE:**
- Switch the Auth0 application to Native type with token auth `none` and drop `client_secret`.
- Because the code is identical apart from one form field, keep `client_secret` optional in config.

**If a second hardware type reuses Spectra 6 (EE04 7.3" case):**
- Add one hardware-registry entry (800x480, `palette_id=1`, landscape) and one layout template. No change to the image container.

**If a future hardware type uses another palette (e.g. 4-gray or 3-colour):**
- Add a `palette_id` entry and a Pillow quantisation table. The container version stays 1, and only `pixel_format` or `palette_id` differ.

**If the fleet grows beyond a handful of zones:**
- The shared-token-bucket design still holds, but cluster more aggressively (larger merged radius up to 250 NM) before considering a paid or feeder-gated provider. This is a licensing decision for the owner, not a stack change.

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| Python 3.14 (server) | stdlib `sqlite3`, `zoneinfo`, `struct`, `zlib`, `base64`, `secrets` | Everything used exists in 3.9+. Local dev here is 3.13.17, so keep within the common subset. |
| Pillow 13.0.0 | `Image.quantize(palette=img)`, `ImageDraw` | Palette quantisation API unchanged across the 10 to 13 line. No upgrade needed for v1.2. |
| ESP-IDF 5.3.1, target `esp32s3` | XIAO ESP32-S3 Plus (EE02) and ESP32-S3R8 (EE04) | One `idf` version and one SoC target for both hardware types. Differences are the panel driver and GPIO map. |
| adsb.fi v3 (`ac`) | adsb.lol v2 point (`ac`) | After migration both providers share the `ac` key, which removes the silent-mismatch hazard in `detect.py` comments. |

## Integration Points (existing code)

- `companion/auth.py`: the docstring says "No per-user accounts" and "stdlib-only; must never import Pillow, sqlite3, or anything under server/". Putting Auth0 and users in the same module would break that rule. Add `companion/oidc.py` (state, PKCE, claim checks, no I/O beyond an injected HTTP callable) and a `users` store module; keep `auth.py` for the cookie primitives. The current session token is `expiry.signature` and its signing key is derived from the shared password. A per-user session needs a signing secret independent of the password (a persisted random `SKYPANE_SESSION_SECRET`), because the shared password is to be retired.
- `companion/routes.py` route table (already gated by a session-gating test against a baseline): add `/login/auth0` (start), `/callback` (code exchange) and `/logout`, plus a minimum-role column checked server-side per route.
- Token exchange calls out to the network, and the `companion` package's `pytest-socket` guard allows loopback only. The fake Auth0 on loopback satisfies it. Inject the HTTP function so unit tests need no socket at all.
- `server/plane/detect.py` `PROVIDERS` and `MIN_SECONDS_BETWEEN_CALLS`: move the per-provider spacing to one shared limiter. Keep the corroboration logic, applied per zone.
- `stub-server/byos_server.py` (vendored, stdlib-only, byte-for-byte duplicated helpers with `server/device_config.py`): per-device image/config state and the `X-Fw-Version` negotiation for the image container belong here. Mind the duplication rule when adding shared helpers.
- `firmware/main/api_client.[ch]`: `FP_IMAGE_BYTES` becomes per-hardware-type, and the downloader gains a header parser. The new firmware must still accept legacy raw images.
- `server/history_db.py`: an existing sqlite3 pattern with a per-thread connection scope; reuse it for the fleet tables, and add `device_id` to the history tables in the same migration.

## Decisions Flagged for the Owner

1. **No new dependency is recommended.** The one thing that would force one is a QR-code pairing screen. Recommendation: defer, use a text pairing code.
2. **Auth0 application type**: Regular Web App + secret + PKCE (recommended) vs Native + PKCE only. Needs the one-time smoke test on the real tenant.
3. **Second hardware**: EE04 7.3" is feasible on paper (same SoC, same colour set, about 70 EUR), but the firmware panel driver has no known ESP-IDF source. Decide the purchase only after a short driver spike.
4. **adsb.fi v3 migration** is a small, recommended change. It touches existing, validated detection code.
5. **Corridor defaults** are Orly-calibrated. Other airports (especially CDG with parallel runways) need either per-runway overrides or a derived half-width. This is a behaviour risk, not a dependency.

## Sources

- OIDC Core 1.0, section 3.1.3.7 ID Token Validation (https://openid.net/specs/openid-connect-core-1_0.html#IDTokenValidation) — step 6 TLS-in-place-of-signature text; iss, aud, azp, exp, nonce steps. **HIGH**
- RFC 9700, OAuth 2.0 Security BCP (https://www.rfc-editor.org/rfc/rfc9700) — PKCE recommended for confidential clients, state handling. **HIGH**
- RFC 7636 (PKCE), RFC 6749 (OAuth 2.0) — standard references. **HIGH**
- Auth0: Authorization Code Flow with PKCE (https://auth0.com/docs/get-started/authentication-and-authorization-flow/authorization-code-flow-with-pkce/call-your-api-using-the-authorization-code-flow-with-pkce) — authorize and token parameters, S256 only. **HIGH**
- Auth0: Confidential and public applications (https://auth0.com/docs/get-started/applications/confidential-and-public-applications) — Regular Web App is confidential and authenticates with a secret. **HIGH**
- Live discovery document of a public Auth0 tenant (https://samples.auth0.com/.well-known/openid-configuration), checked today — issuer trailing slash, `/authorize`, `/oauth/token`, PKCE and token-auth method lists. **HIGH** for format; the EU tenant uses the same paths (`auth0.eu.auth0.com` discovery answered 200).
- Auth0: Log users out (https://auth0.com/docs/authenticate/login/logout/log-users-out-of-auth0) — RP-initiated logout, `end_session_endpoint` default for tenants created after 2023-11-14, exact-match logout URLs. **HIGH**
- Auth0 community and support on PKCE for Regular Web Apps (https://community.auth0.com/t/is-it-possible-to-use-pkce-authorization-code-flow-for-regular-web-app/102282) and disabling sign-ups (https://support.auth0.com/center/s/article/Disable-Signups-at-Connection-Level) — **MEDIUM** (community and support articles, not core docs).
- OurAirports data page (https://ourairports.com/data/) and the CSVs from `davidmegginson.github.io/ourairports-data/` — public domain, nightly, column lists, measured counts from the 2026-10-28 dump. **HIGH**
- adsb.fi opendata README (https://github.com/adsbfi/opendata/blob/main/README.md) — 1 req/s, v2 lat/lon/dist deprecated, v3 250 NM; live probes of v2 and v3 (`ac` key, identical fields; 300 NM returns 400). **HIGH**
- CNX Software (https://www.cnx-software.com/2025/12/02/xiao-epaper-diy-kit-features-esp32-s3-or-nrf52840-soc-supports-1-54-inch-to-13-3-inch-displays/), Hackster (https://www.hackster.io/news/seeed-studio-s-new-epaper-kits-make-electrophoretic-display-development-a-breeze-4d7b69aadd4b), OpenELAB (https://openelab.com/products/seeed-studio-xiao-epaper-7-3-inch-diy-kit) — EE04 specs and prices. **MEDIUM** (retailer and press; no Seeed wiki page was retrievable, so pin map and driver IC are unverified).
- Repo files read: `server/requirements.txt`, `server/plane/detect.py`, `server/http_fetch.py`, `companion/auth.py`, `firmware/main/api_client.h`, `stub-server/make_test_panel.py`, `adsb-test/runway3.json`, `.planning/PROJECT.md`.

---
*Stack research for: SkyPane v1.2 Fleet platform*
*Researched: 2026-10-28*
