# Feature Research

**Domain:** Small multi-user e-ink frame fleet (owner + a few relatives, handful of devices, France-wide), v1.2 Fleet platform
**Researched:** 2026-10-28
**Confidence:** MEDIUM. Patterns come from well-known IoT / e-ink product conventions (TRMNL, Tidbyt, Inkplate-style BYOS servers, Hue/Sonos-style claiming, Home Assistant user roles, Auth0 docs). No live web verification was done in this pass, so product-specific details are from training knowledge and should be spot-checked. The scale-down judgements are reasoning, not citations.

Scope: only the NEW v1.2 features. Existing poll protocol, render pipeline, companion pages (Home, Display, Flights, Airlines, Health, Device, Update), OTA, quiet hours and battery telemetry are assumed and only referenced as dependencies.

## Feature Landscape

### Table Stakes (Users Expect These)

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Entities: user, device, hardware type, location, with device owned by exactly one user | Every fleet product has "my devices" as the core list; per-device config requires a device record | MEDIUM | SQLite already in use. Hardware type is a static registry (id, width, height, palette, battery curve, firmware channel), not user-editable. Location = lat/lon + label, belongs to the device (one device, one place). Keep a single owner per device; no sharing. |
| Migration of the current frame into the model | The live frame must not break or need re-flash (existing bearer token stays valid) | MEDIUM | Create admin user + hardware type "EE02 13.3in" + location Orly + device row carrying the existing token. Backward-compatible poll endpoint is the gate. Depends on existing poll protocol and NVS-stored token. |
| Two roles: admin, user | Users expect to see only their own frames; owner needs everything | LOW | A role column, checked server-side in one place (route table already exists in `companion/routes.py`; add a per-route minimum role). Do not hide-only in the UI. |
| Ordinary user sees only own devices, with a reduced option set | Standard least-privilege expectation; relatives should not see Update/OTA, other people's frames, global provider settings | MEDIUM | Reduced set typically: rename frame, location, detection mode, quiet hours, wake interval within safe bounds, view battery/last-seen status. Hidden/denied: OTA/firmware, airline registry, provider settings, other users, raw logs. Existing pages need a per-page and per-control visibility rule, which is the main cost (Settings/Device/Update/Airlines/Flights pages already exist). |
| Admin fleet console: list all devices with owner, hardware type, location, last seen, battery, firmware version, state | The one thing a fleet console must answer: "is everything alive?" | MEDIUM | One table, sortable, with a stale/low-battery highlight. Reuses Health + battery telemetry per device. Row click opens the same per-device page the user sees, plus admin-only controls (impersonate-free "view as owner" is enough). |
| Admin can create/disable users and reassign or remove a device | Without it the owner edits SQLite by hand | LOW-MEDIUM | Users are created implicitly on first Auth0 login or pre-registered by email. Disable = deny login, keep devices. Reassign = change owner_id. |
| Auth0 sign-in (code + PKCE), session cookie, logout | Stated requirement; users expect no shared password | MEDIUM-HIGH | Already scoped as no extra crypto dependency (stdlib JWT/JWKS verification is the real work). Allow-list by email so only invited relatives get in: an open Auth0 signup would create accounts for strangers. Shared password stays as admin-only fallback until cutover. |
| Pairing a brand-new frame to an account | Core onboarding; a frame with no owner must be claimable | HIGH | See pairing pattern below. Needs firmware-side or server-side provisioning identity; this is the riskiest table-stake. |
| Unclaimed / unknown device handling | Pattern in TRMNL/Hue: unknown device shows a "pair me" screen, never an error loop | MEDIUM | Server must serve a pairing screen image to an unpaired device and a low-cost sleep interval. Depends on common versioned image format. |
| Per-device detection mode: (a) airport + runway of choice, (b) aircraft around a position | Stated requirement; users expect to pick where their frame looks | HIGH | (a) needs an airport/runway catalogue (OurAirports data: runway endpoints, headings) to build the geofence; France-wide list is a few hundred airports, curate or search-as-you-type. (b) = lat/lon + radius. Both feed the existing detector via a per-device zone. Depends on per-device config in poll loop and request budget with zone grouping (devices in the same zone share one upstream query). |
| Mode-change feedback: after saving, user sees "applies at next wake (~N min)" | Battery frames cannot apply instantly; every deep-sleep product states this | LOW | Show pending-config state and last config applied (device echoes version in poll). |
| Per-hardware-type rendering, battery curve and health thresholds | Different panel sizes/palettes and cell chemistries make one-size values wrong (low-battery %, stale thresholds) | MEDIUM | Hardware-type record carries width/height/palette, voltage-to-percent table, low/critical thresholds, expected wake cadence. Renderer chooses layout by hardware type. Depends on versioned image format. Test against the simulated second type (as PROJECT.md plans). |
| Credits page for data sources | Licence/ToS expectation for adsb.fi, adsb.lol, adsbdb, OurAirports (and illustration sources); required by data-provider terms | LOW | Static bilingual page reachable without login or from every footer; text lives in i18n. COMPLIANCE.md already lists the obligations. |
| Per-user, per-device scoping of everything that was global (config, image, state, quiet hours, wake interval) | Fleet means a setting change on frame A must not touch frame B | MEDIUM-HIGH | The large refactor: global `state_dir` files become per-device. Mostly plumbing but touches poll loop, BYOS server, renderer, Flights history. |
| Language preference per user (EN/FR) | Existing bilingual UI; relatives will want their own | LOW | Stored on user, falls back to cookie/browser. |

### Differentiators (Competitive Advantage)

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Zone grouping across devices (shared upstream query) | Keeps the fleet within the 1 req/s provider budget and is polite to volunteer APIs | MEDIUM | Already in scope; invisible to users but a real quality point. Group by (airport/runway) or rounded position + radius. |
| Map/list picker for position mode with radius preview | Makes "aircraft around a position" understandable | MEDIUM | Defer a map widget; start with lat/lon fields, "use my city" preset, and a small set of presets. Add map only if relatives struggle. |
| Airport search by name/ICAO/city with runway picker showing orientation | Friendly runway selection | MEDIUM | Static JSON built from OurAirports at build time; no runtime dependency. |
| Fleet health digest (e.g. daily email/summary) or "frame offline for N hours" banner in console | Owner cares if a relative's frame dies | LOW-MEDIUM | Banner is cheap. Email needs a mail path; defer. |
| Hardware-type onboarding checklist for the second device (render preview, battery calibration, OTA channel) | Reduces risk when the unchosen second type arrives | MEDIUM | Document as a repeatable "add hardware type" recipe: registry entry + palette/layout + firmware build target + battery table + bring-up checklist. |
| Admin "view as user" (read-only impersonation) | Debugging a relative's frame without asking for a screenshot | LOW-MEDIUM | Implement as admin opening the owner's device page with a visible banner; log it. Avoid full session switching. |
| Pairing by QR code on the frame's pairing screen | Smooth onboarding, matches TRMNL/Tidbyt feel | MEDIUM | The pairing screen already has to be rendered; add the code as text first, QR later. Pillow can render QR only with a dependency or a small stdlib-free encoder, so text code first. |

### Anti-Features (Commonly Requested, Often Problematic)

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Self-service open signup / public SaaS flow | "Anyone can get a frame" | Account abuse, support burden, ToS exposure with volunteer ADS-B APIs; scale is a handful of devices | Invite-only: admin allow-lists emails, Auth0 signup disabled or gated. |
| Fine-grained RBAC, teams/orgs, device sharing between users | "Share frame with partner" | Permission matrix, UI states, and test surface explode for two roles | Two fixed roles, single owner per device; admin can reassign. |
| Multiple locations or modes per device with scheduling ("airport A by day, B at night") | Flexible | Changes the zone grouping, render cache and battery model | One mode per device; user changes it manually. |
| Social login zoo, MFA enforcement UI, password reset flows in-app | Convenience | Auth0 already provides these; duplicating it adds crypto and security burden | Delegate all to Auth0 hosted login; one or two connections. |
| Custom user-uploaded firmware or per-user OTA channels | Hackers like it | Bricking, support, signing; OTA is hardware-type-indexed by design | Admin-only OTA by hardware type, with the existing update flow. |
| Billing, plans, quotas, usage dashboards | Looks like a platform | No customer; pure cost | Fixed fleet budget enforced by the global 1 req/s limit. |
| Real-time fleet dashboard (websockets, live push to devices) | Looks impressive | Devices sleep and poll; the server cannot reach them. Live updates imply false promise | Polling-based last-seen view and "applies at next wake" messaging. |
| Remote command channel (reboot, push now) to devices | Remote management expectation | Devices never accept connections (design invariant); needs pending-command queue and ack semantics | Piggy-back flags on the next poll response (already how sleep_s and config travel), only if clearly needed. |
| Device-side pairing UI (menus, buttons, BLE provisioning flows beyond what exists) | Easy onboarding | On-device settings UI is already an out-of-scope anti-feature | Server-side pairing code shown on the pairing screen; entered in the companion. |
| Per-user custom artwork or illustration upload | Personalisation | Moderation and storage; existing artwork registry is admin-curated | Keep artwork admin-only. |
| Auto-detected hardware capabilities negotiated at runtime | Elegant | Complex versioning surface | Hardware type declared at pairing/OTA and fixed in the registry. |
| Full audit/event-log product | Compliance feel | Not needed for family scale | A simple admin-actions log table (who changed what), no UI beyond a list. |

## Feature Dependencies

```
Entities (user/device/hardware-type/location)
    └──requires──> Migration of current frame (poll endpoint stays backward compatible)
    └──enables───> Roles (admin/user)
                       └──enables──> Reduced user view
                       └──enables──> Admin fleet console

Common versioned image format (width/height/palette in header)
    └──requires──> Hardware-type registry
    └──enables───> Per-hardware rendering, pairing screen for unclaimed devices
    └──enables───> Second hardware type

Per-device config/state in BYOS + poll loop
    └──requires──> Entities
    └──enables───> Per-device detection mode
                       └──requires──> Airport/runway catalogue (mode a)
                       └──requires──> Zone grouping + request budget

Auth0 sign-in (PKCE, email allow-list)
    └──requires──> Users table
    └──enables───> Account ownership, pairing
    └──keeps─────> Shared-password fallback (admin) until cutover

Pairing a new frame
    └──requires──> Auth0 login + ownership + unclaimed-device handling + pairing screen image
    └──requires──> Device identity (factory/provisioning token or id) on firmware side

Credits page ── independent (can ship any time, needs only i18n)
Per-hardware battery/health ──requires──> Hardware-type registry + existing battery telemetry
```

### Dependency Notes

- **Pairing is the highest-risk dependency chain.** It needs Auth0, ownership, an unclaimed-device flow and a device identity. Settle device identity early (see pairing pattern below) because it may touch firmware (and NVS persistence: a normal flash does not clear NVS, a known pitfall in PROJECT.md).
- **Versioned image format precedes everything hardware-related.** Pairing screens, second hardware type and per-hardware rendering all rely on it, and existing frames must keep working.
- **Per-device state plumbing precedes detection modes.** Do not build mode UI before the poll loop can run zones per device.
- **Roles precede reduced view and console.** Enforce in the route table so tests can assert the gating (the codebase already has a session-gating test pattern).
- **Auth0 and migration can ship before pairing**: manually creating devices (admin console "add device" with token) is a valid intermediate path for relatives' frames.

## Expected Behaviour Patterns (reference for roadmap/requirements)

**Pairing (typical):** an unpaired frame has either a factory-printed ID or generates one on first boot. It polls with that ID; server has no owner, so it returns a pairing screen showing a short human-enterable code (6 to 8 characters, no ambiguous letters, expires in roughly 10-30 minutes, regenerated on expiry) and a short URL. The user, logged in, enters the code on a "Add a frame" page, chooses hardware type (or it is reported by the device), name and location. The server binds device to account and issues the long-lived device token on the device's next poll (token is delivered via the poll response, stored in NVS, never shown to the user). Expected edge cases: wrong or expired code, code already claimed, claim by wrong user, and "unpair / factory reset" which rotates the token and returns the frame to the pairing screen. Because the frame sleeps, the pairing completes only on the next wake; the UI must say so and use a short wake interval while unclaimed. Admin should also be able to pre-register a device (token + hardware type) for relatives' frames as a fallback.

**Admin console (typical at this scale):** one fleet table plus per-device detail; health colouring; ability to edit any device's config, reassign owner, retire a device, trigger OTA by hardware type. No metrics backend. Everything reads existing telemetry.

**Reduced user view (typical):** same page chrome, fewer controls, scoped data. Typical user controls: frame name, location, detection mode, quiet hours, language. Hidden: firmware, providers, airline registry, other users. Show status (battery %, last seen) read-only.

**Detection mode UX:** a mode switch with only the fields relevant to the selected mode, validation of bounds (radius, France-wide lat/lon), and a plain-language preview of what the frame will show ("Taking off or landing at Nice runway 04L").

## MVP Definition

### Launch With (v1.2 core)

- [ ] Data model + hardware-type registry + migration of the current frame, backward-compatible poll
- [ ] Common versioned image format (prerequisite for second hardware, pairing screen)
- [ ] Per-device config/state in poll loop and BYOS with zone grouping and global budget
- [ ] Two detection modes (airport+runway from a static catalogue; position+radius with lat/lon fields)
- [ ] Auth0 sign-in with invite-only allow-list; shared password retained as fallback
- [ ] Roles; reduced user view with a small, explicit option set; server-side enforcement
- [ ] Admin fleet console (list, detail, reassign, disable user, add device manually)
- [ ] Pairing by short code via the pairing screen
- [ ] Per-hardware rendering, battery curve and health thresholds
- [ ] Credits page

### Add After Validation (v1.2.x)

- [ ] Second hardware type end to end on real hardware (needs purchase; keep the simulated type as the test stand-in)
- [ ] QR on pairing screen, map picker, offline-frame banner/digest

### Future Consideration (v2+)

- [ ] Device sharing between users, scheduled modes, remote commands, phone push message (already v2/later in PROJECT.md)

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Entities + migration of current frame | HIGH | MEDIUM | P1 |
| Versioned image format + hardware registry | HIGH | MEDIUM | P1 |
| Per-device config/state, zone grouping | HIGH | HIGH | P1 |
| Detection modes (both) | HIGH | HIGH | P1 |
| Auth0 + allow-list | HIGH | MEDIUM-HIGH | P1 |
| Roles + reduced view | HIGH | MEDIUM | P1 |
| Admin console | HIGH | MEDIUM | P1 |
| Pairing by code | HIGH | HIGH | P1 |
| Per-hardware render/battery/health | MEDIUM | MEDIUM | P1 |
| Credits page | MEDIUM (compliance) | LOW | P1 |
| Second hardware selection/validation | MEDIUM | MEDIUM-HIGH (purchase) | P2 |
| Airport search UX | MEDIUM | MEDIUM | P2 |
| QR pairing, map picker, offline banner | LOW-MEDIUM | MEDIUM | P3 |
| Read-only admin view-as-user | MEDIUM | LOW-MEDIUM | P2 |

## Competitor / Reference Pattern Analysis

| Feature | TRMNL-style e-ink | Tidbyt / Hue-style consumer devices | Our Approach |
|---------|-------------------|--------------------------------------|--------------|
| Claiming | Device ID (MAC) plus friendly code entered in dashboard | App-guided Wi-Fi pairing, account binding | Short code on pairing screen, bound on next wake |
| Reduced vs admin views | Single account, no roles | Household members share devices | Two fixed roles, single owner per device |
| Config delivery | Applied on next refresh | Pushed immediately (always-on) | Applied on next wake, message the delay |
| Fleet console | Dashboard of devices with battery and last seen | Per-account list | Same, plus admin cross-account view |
| Auth | Hosted login | Hosted login | Auth0 hosted, invite-only |

## Sources

- Known product patterns (training knowledge, not re-verified this session): TRMNL BYOS device claiming/friendly ID, Tidbyt app pairing, Philips Hue/Sonos claim flows, Home Assistant admin vs user roles, OAuth 2.0 authorization code + PKCE (RFC 7636) and Auth0 hosted login docs.
- `.planning/PROJECT.md` (v1.2 target features, constraints, NVS pitfall, out-of-scope list)
- `.claude/CLAUDE.md` (stack: stdlib server, companion `routes.py`, COMPLIANCE.md for data-source obligations)
- Gaps to verify later: OurAirports licence (public domain) and data shape for runway endpoints; Auth0 free-tier user and connection limits and signup-disable setting; whether the XIAO ESP32-S3 EE02 exposes a stable per-chip ID (eFuse MAC does on ESP32-S3) usable as device identity.

---
*Feature research for: SkyPane v1.2 Fleet platform*
*Researched: 2026-10-28*
