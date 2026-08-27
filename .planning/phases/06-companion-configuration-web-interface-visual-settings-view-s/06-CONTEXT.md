# Phase 6: Companion Configuration Web Interface - Context

**Gathered:** 2026-08-27
**Status:** Ready for planning

<domain>
## Phase Boundary

A password-protected companion web page — a new, separate service on its own subdomain, never touching the vendored device-protocol server — where the user can pick a validated display theme, monitor device/ADS-B-source health over time, browse recent flight/render history, see airline-coverage gaps, and debug the render pipeline directly, all without SSH access to the VPS.

**Scope widened three times during this discussion, all by explicit user request:**
1. CFG-02 (view switching) removed — there is still nothing to switch to until a second view (RER or otherwise) exists. Moved back to REQUIREMENTS.md's v2 "View Switching" section.
2. Six new capabilities added: a flight-history log (CFG-06), a manual poll trigger (CFG-07), airline-resolution statistics (CFG-08), a dark/light theme for the page itself (CFG-09), a live render preview (CFG-10), and a gallery of recent renders (CFG-11).
3. A seventh, raised mid-discussion after the rest of this document was already drafted: **runway selection (CFG-12)** — letting the user pick which of Orly's three runways the device tracks, generalizing PLANE-01/02/03's currently runway-3-specific detection. This one is materially different in weight from the others — it touches `server/plane/detect.py`'s core detection logic (Phase 1/2 territory), not just a display/config layer over data that already exists.

REQUIREMENTS.md and ROADMAP.md were updated live during this discussion to reflect all three changes — this is not a discrepancy to reconcile later.

This phase does not cover the RER view, the physical button, or any battery-indicator work (Phase 5's job).

</domain>

<decisions>
## Implementation Decisions

### Authentication & access control
- **D-01:** Access is gated by a **single shared password** (not per-user accounts, not IP restriction). IP restriction was explored first and explicitly rejected — the user's home IP is not static/stable enough to hardcode, and a dynamic-DNS client felt like unnecessary setup for a single-user personal tool. The password should be stored the same way the existing device bearer token is (a gitignored environment file, e.g. extending `deploy/skypane.env.example`'s pattern) — never committed, never logged.
- **D-02:** The password protects **the entire site uniformly** — including the read-only views (CFG-03 health, CFG-04 coverage, CFG-06 flight log, CFG-11 render gallery), not just the state-changing actions (CFG-01 theme, CFG-07 poll trigger). User explicitly chose simplicity (one auth mechanism everywhere) over splitting read/write access, even knowing CFG-05's fault icon points here during an actual outage.
- Session mechanism (cookie duration, rate-limiting failed attempts) is **Claude's Discretion** — not discussed live; a reasonable, unremarkable session-cookie implementation is expected, nothing elaborate.

### Server architecture & hosting
- **D-03:** A **new, separate service** — its own process/systemd unit — not folded into `poll_loop.py` and never modifying the vendored `stub-server/byos_server.py`. No cost difference either way (same already-provisioned OVH VPS with ample spare capacity); the deciding factor was separation of concerns, keeping the ADS-B detection/render loop and the web-facing config UI as independent failure domains.
- **D-04 (correction of record):** The project's actual VPS provider is **OVH**, not Hetzner — the user confirmed this live. `.claude/CLAUDE.md`'s stack-recommendation doc names Hetzner CX22 as the *recommended* choice, but the project's real, deployed infrastructure (per `deploy/README.md`, `deploy/Caddyfile`, `deploy/provision.sh`, and STATE.md's Phase 4 history) is OVH VPS-1. Downstream agents should treat OVH as ground truth and not "correct" the code to match the stack doc.
- **D-05:** Exposed via a **separate nip.io subdomain** (e.g. `config-<vps-ip>.nip.io`), not a path prefix on the existing device-protocol hostname. Also free (nip.io accepts arbitrary prefixes before the IP-encoding suffix; Let's Encrypt issues certs per-hostname at no cost) — chosen for cleaner separation over the path-based alternative. Caddy needs a new site block alongside the existing one in `deploy/Caddyfile`, reverse-proxying to the new service's own loopback port (matching the existing `127.0.0.1:8642`-behind-Caddy pattern, ufw denying the new port from outside — same discipline as `deploy/provision.sh` already applies to byos_server.py).
- Framework choice (stdlib vs. Flask/FastAPI) was **not discussed live** — Claude's Discretion. Given this new service needs real HTML forms/templating (unlike `byos_server.py`'s narrow 3-endpoint device protocol), a lightweight framework is a reasonable default, but a stdlib approach is also acceptable if it keeps the dependency footprint minimal (`server/requirements.txt` currently has only Pillow + requests).

### Config delivery timing
- **D-06:** A setting changed on the web page (e.g. the CFG-01 theme) takes effect on the **device's next regularly-scheduled poll** — not immediately. This preserves the existing "device never accepts inbound pushes, always initiates" security model (MSG-01, already established) rather than introducing an early-wake mechanism, which would be a much larger architecture change not currently budgeted for in the battery plan.
- **D-07:** After saving a setting, the page must show an **explicit confirmation message** stating the change applies on the frame's next wake (e.g. "Saved — will apply on the frame's next scheduled refresh"), so the user isn't confused if they check the physical device immediately and see no change yet.
- **Note:** CFG-07's manual poll trigger (D-17 below) is a *different* mechanism — it forces the *server* to re-run detection/render immediately for debugging, but does not change when the *device* next fetches that render. D-06 still governs when the device itself picks anything up.

### CFG-02 removed from this phase
- **D-08:** CFG-02 (view switching) does not belong in this phase — building a switcher UI for a single-option list (only "Plane" exists) is dead weight. Moved back to REQUIREMENTS.md's v2 "View Switching" section, to be revisited once a second view actually exists. DEVICE-01/DEVICE-02 (the actual switching requirements) were already there.

### CFG-01 — theme picker, cross-phase dependency on Phase 7
- **D-09 (correction of record):** The panel's design has **not** been calibrated on real glass yet — Phase 7 (Final On-Glass Verification) is where that happens, and it hasn't run. The user caught an assistant error here mid-discussion: an initial question wrongly assumed the design was "freshly calibrated." In fact `03-CONTEXT.md`'s D-21 (the current DEPARTING/ARRIVING Blue/Green values) was only ever confirmed against **on-screen previews**, and ROADMAP.md's Phase 7 criterion 7 still explicitly lists Yellow/Red as "still-interim." Downstream agents must not assume any panel color is real-glass-validated before Phase 7 completes.
- **D-10:** Given D-09, CFG-01's background-color configurability is scoped to a **theme picker among a small set of DEPARTING/ARRIVING color variants validated on real glass** — not a free-form color picker, and not simply exposing the current (screen-only-confirmed) D-21 values as the sole option. The user chose to use Phase 7's on-glass session to test 2-3 alternate Blue/Green hues instead of just confirming the existing pair unchanged.
- **D-11 (cross-phase, already applied to ROADMAP.md):** This reopens `03-CONTEXT.md`'s D-21 (previously "confirmed as 'parfait,' locked") and widens Phase 7's success criterion 7 accordingly — done live during this discussion, see ROADMAP.md's Phase 7 section ("Note on scope — D-21 reopened"). **Not yet reflected in `07-01-PLAN.md`'s task detail/acceptance criteria** — that plan's Task 3 still assumes "Blue/Green confirmed unchanged"; must be revised before Phase 7 executes Task 3. This is a real sequencing dependency: Phase 6 (this phase) runs *before* Phase 7 in the roadmap, so CFG-01's actual selectable theme list cannot be finalized until Phase 7 delivers it. **Left to planning to resolve** — e.g. ship CFG-01's picker mechanism now against a placeholder/single-option list (the current D-21 pair), with the real multi-theme list arriving as a small follow-up once Phase 7 completes; or defer CFG-01's implementation task until after Phase 7. Do not guess Phase 7's eventual color values — they don't exist yet.

### CFG-03 — health status detail
- **D-12:** CFG-03 shows **history/trend**, not just a current snapshot — the user explicitly wants to spot degradation over time (particularly battery), not just "is it fine right now."
- **D-13:** Retention is **unbounded, kept forever** — clarified live that storage cost is negligible for this data shape (a timestamp + a battery reading per poll cycle, worst-case ~35,000 entries/year even at an unrealistically-frequent 15-minute cadence, ~1-2MB/year). No purge job needed. The UI shows recent weeks by default rather than the full history, for readability — not because older data is discarded.
- **D-14:** The page must **visually flag anomalies** — an unusually stale last-poll time, or an abnormal battery drop — rather than presenting raw numbers with no judgment. Ties into CFG-05's fault icon, which already redirects the user here during a real outage.
- **D-15:** Also surface the **ADS-B cross-source corroboration status** (`corroborated=True/False/None`, already computed server-side by the runway3-false-positive fix — see `server/plane/detect.py`) — zero new computation needed, just expose an existing signal. This tracks adsb.fi/adsb.lol reliability, not just the device itself.
- **New persistence needed:** `poll_state.json` currently has no per-poll history (only a rolling `last_flight`/`previous_flight` pair) and does not persist battery voltage or per-poll timestamps at all — `byos_server.py` receives `X-Battery-Mv` per request but nothing currently stores it. This phase needs new, separate persistence (append-only log or small DB) — left to research/planning to design; does not touch `poll_state.json`'s existing flight-state shape.

### CFG-04 — airline-coverage monitoring
- **D-16:** **Read-only display** of the existing `unresolved_prefixes` registry (`poll_state.json`, documented in a prior quick-task's runbook) — no in-page actions (no "mark resolved" button). The user acts on this data manually elsewhere, matching the existing runbook's discipline; CFG-04 just makes the registry visible without needing to grep server-side JSON over SSH.

### Scope widening — six new capabilities (CFG-06..11)
- **D-17 (CFG-07, manual poll trigger):** Must have a **short cooldown** after use — a disabled-button period of some tens of seconds — specifically to prevent accidental repeated triggering from hammering the free adsb.fi/adsb.lol APIs. Not a hard rate-limit against abuse (this is a single-user personal tool), just a guard against an accidental double-click or reflexive re-clicking.
- **D-18 (CFG-06, flight-history log):** A log of recently-detected flights (not just current+previous, which `poll_state.json` already tracks) — same "keep it, storage is cheap" reasoning as D-13 applies; exact retention/format left to planning.
- **D-19 (CFG-08, resolution statistics):** Airline/route resolution rate over time, going beyond CFG-04's raw unresolved-prefix list — exact metrics/visualization left to planning; likely derived from the same new history persistence D-15 needs anyway.
- **D-20 (CFG-10/CFG-11, render preview & gallery):** Both grounded in capability that already exists as CLI flags on the developer's own machine (`server/plane/render.py --preview`, `--state`, `--callsign` — used throughout Phase 3/6/7's on-glass iteration) but currently requires SSH + manual file transfer to see. CFG-10 shows what the panel currently displays; CFG-11 shows the last N rendered images for quick visual QA. Both are read-only, no new render logic — just surfacing existing renderer output over HTTP.

### CFG-12 — runway selection (raised mid-discussion, after the rest of this document was already drafted)
- **D-26:** The device should let the user **select which of Orly's three runways to track** — not just the currently-hardcoded runway 3. Unlike every other CFG item in this phase, this is **not** a thin config/display layer over already-existing server data: `server/plane/detect.py`'s `select_runway3_aircraft()` has a runway-3-specific geofenced corridor, hardened by the runway3-false-positive fix specifically to *exclude* traffic from the two neighboring runways (06/24, 02/20) — it does not currently have the corridor geometry needed to *positively track* those runways instead.
- **D-27:** All **three of Orly's real runways** should be selectable (runway 3, 06/24, 02/20) — not just a placeholder mechanism with runway 3 as the sole working option. The corridor/track-alignment geometry for 06/24 and 02/20 already exists in the codebase (added for exclusion purposes by the runway3-false-positive fix) and needs to be repurposed/extended for positive tracking, not derived from scratch.
- **D-28:** One runway tracked at a time (a single global setting, not simultaneous multi-runway tracking) — consistent with the device showing one view/one flight at a time. Applies on the device's **next scheduled poll**, same timing rule as every other setting (D-06).
- **Consequence for REQUIREMENTS.md:** PLANE-01/02/03 (Phase 2, already shipped and marked complete) are written specifically around "runway 3." CFG-12 generalizes their underlying detection logic without rewriting those historical, already-complete requirement entries — the generalization is CFG-12's own job, not a retroactive edit to Phase 2's record. Downstream agents implementing CFG-12 should treat `detect.py`'s runway-3 corridor as the pattern to replicate/parameterize for the other two runways, not as code to preserve unchanged.

### Visual tone & UX
- **D-21:** The page is a **plain utility tool**, not a piece of "ambient art" design work — deliberately less visual investment than the physical frame's own carefully-tuned poster aesthetic (Phases 3/6/7). This is consistent with the project's established "ambient device, not a gadget" philosophy (REQUIREMENTS.md's Out of Scope table already rejects on-device menus/LEDs for the same reason) — the philosophy governs the *physical frame*, not this admin page, which is allowed to just be functional.
- **D-22:** Must be **responsive on mobile** — basic adaptation only (readable text, tappable controls), not a dedicated mobile design pass. The user will realistically check this from their phone sometimes.
- **D-23:** UI copy is in **English** — consistent with the rest of the codebase (already English) and the public GitHub repo, not French, despite this discussion happening in French.
- **D-24:** The page carries a simple **"SkyPane" title/header** — enough to orient the user, no logo or elaborate branding.

### Navigation structure
- **D-25:** Given the breadth after D-17 through D-20's additions (config, health/history, coverage, flight log, stats, poll trigger, render preview/gallery), the interface is **multiple pages/tabs** (e.g. Config / Health / Airlines / History), not one long single-scroll page. Exact page grouping/IA left to planning.

### Claude's Discretion
- Web framework choice (stdlib vs. Flask/FastAPI) for the new service.
- Session/cookie mechanism for the password gate (D-01/D-02) — duration, failed-attempt handling.
- New persistence format for poll/battery history and flight log (D-12/D-15/D-18/D-19) — file-based (JSON/SQLite) vs. something else; exact schema.
- Exact page/tab grouping (D-25) and per-page layout.
- Exact metrics/visualization for CFG-08's resolution statistics (D-19).
- Whether CFG-01's theme picker ships now against a single-option placeholder or waits for Phase 7 (D-11) — a real open sequencing question for the planner to resolve explicitly, not silently pick either way.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Deploy / infrastructure (existing, must not be reimplemented or modified)
- `deploy/Caddyfile` — the existing reverse-proxy config; the new service needs a new site block here (D-05), following the same loopback-port + ufw-deny pattern already used for `byos_server.py`
- `deploy/README.md` — real OVH VPS-1 provisioning + deploy flow (D-04: this project runs on OVH, not Hetzner)
- `deploy/provision.sh` — one-time VPS setup; the new service's systemd unit and firewall rule should follow this file's existing pattern for `skypane-byos.service`/`skypane-poll.service`
- `deploy/skypane.env.example` — template for the gitignored production env file; the new shared password (D-01) should follow this same never-committed pattern
- `deploy/skypane-byos.service`, `deploy/skypane-poll.service`, `deploy/skypane-poll.timer` — existing systemd units to model the new service's own unit on

### Server code this phase reads from (must not modify the vendored parts)
- `stub-server/byos_server.py` — the vendored, do-not-modify device-protocol server (D-03); receives `X-Battery-Mv` per request but does not currently persist it — the new service needs its own path to this data or a shared persistence layer
- `server/poll_loop.py` — writes `poll_state.json` (`last_flight`/`previous_flight`/`last_confirmed_state`/etc.); the new service should read this file, not duplicate its logic (D-03)
- `server/plane/detect.py` — computes the ADS-B cross-source `corroborated` status (D-15); `select_runway3_aircraft()` and the runway3-false-positive fix's corridor/track-alignment gates are the code CFG-12 (D-26/D-27) must generalize/parameterize by runway — currently hardcoded to runway 3, with 06/24 and 02/20's geometry present but only used to exclude, not track
- `server/plane/enrich.py` — owns the `unresolved_prefixes` registry `poll_state.json` already tracks (D-16); see the runbook documented in a prior quick-task (STATE.md 260827-oz9-03) for the existing manual-resolution workflow this page should not duplicate
- `server/plane/render.py` — `--preview`, `--state`, `--callsign` CLI flags are the existing capability CFG-10/CFG-11 (D-20) should expose over HTTP instead of SSH
- `server/panel_format.py` — `PALETTE_RGB`, the six-color palette CFG-01's theme options must stay legal against

### Project planning docs
- `.planning/ROADMAP.md` — Phase 6 section (this phase, updated live during this discussion) and Phase 7 section (D-21 reopening, also updated live — see its "Note on scope — D-21 reopened")
- `.planning/REQUIREMENTS.md` — CFG-01, CFG-03 through CFG-12 (v1, this phase); CFG-02/DEVICE-01/DEVICE-02 (v2, deferred); DEVICE-06 (v2, the sibling seed not chosen)
- `.planning/phases/03-visual-polish-on-real-glass/03-CONTEXT.md` — D-21 (the DEPARTING/ARRIVING colors this phase's CFG-01 reopens, D-09/D-10/D-11)
- `.planning/phases/07-final-on-glass-verification/07-01-PLAN.md` — the plan whose Task 3 acceptance criteria need revising before Phase 7 executes, per D-11
- `.planning/seeds/on-device-fault-icon.md` — CFG-05's full design rationale (already-locked decision, carried forward unchanged from the original seed)
- `.planning/phases/04-ci-cd-documentation-legal-compliance-github-actions-ci-tests/04-CONTEXT.md` — D-06 (secrets discipline: real credentials only in gitignored env files, never committed) — the pattern D-01's password must follow

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/plane/render.py`'s `--preview`/`--state`/`--callsign` CLI flags — direct backing for CFG-10 (live preview) and CFG-11 (render gallery); no new render logic needed, just an HTTP-facing wrapper
- `server/plane/enrich.py`'s `unresolved_prefixes` registry — direct backing for CFG-04, already computed and persisted
- `server/plane/detect.py`'s `corroborated` field — direct backing for part of CFG-03's health page (D-15)
- `deploy/provision.sh`'s existing systemd-unit + ufw-deny pattern — template for the new service's own deployment (D-03/D-05)

### Established Patterns
- Secrets discipline: real credentials only in gitignored env files (`deploy/skypane.env`, `firmware/main/secrets.h`), never committed — D-01's shared password follows this exactly
- "Device never accepts inbound pushes, always initiates" — the poll-only security model (MSG-01) that D-06 preserves; do not add any mechanism for the server to push to the device
- Vendored-code discipline: `stub-server/byos_server.py` is never modified, even though it's the closest existing precedent for a device-facing HTTP server — D-03 makes the new service fully separate specifically to preserve this

### Integration Points
- The new service needs read access to `poll_state.json` (written by `poll_loop.py`) — likely via direct file reads (same host, same filesystem) rather than an API call between the two processes, matching how simple/local this project's existing components already are
- New persistence for poll/battery/flight history (D-12/D-15/D-18/D-19) is a genuinely new piece of infrastructure — not an extension of `poll_state.json`'s existing single-flight-pair shape, which stays as-is for the render pipeline's own use
- **CFG-12 is the one exception to "this phase only reads existing data."** Selecting a runway must actually change what `poll_loop.py`/`detect.py` do on the next cycle — likely a small persisted config value (e.g. in `poll_state.json` or a new small config file) that `select_runway3_aircraft()`'s successor reads to pick which runway's corridor gate to apply. This is a real, if small, change to the detection pipeline itself, not just the new web service.

</code_context>

<specifics>
## Specific Ideas

- User's own words on rejecting IP-restriction: home IP addresses from consumer ISPs change too often to hardcode reliably (D-01).
- User's own words on cost questions (asked twice, about hosting and about DNS/routing): reassured both times that the marginal cost is zero since everything runs on the already-provisioned OVH VPS — the real tradeoffs discussed were architectural (separation of concerns, D-03) and organizational (one name vs. two, D-05), not financial.
- The mid-discussion correction (D-09) — the user caught an assistant assumption that the panel design was "already calibrated" when Phase 7 (the calibration phase) hasn't run yet — is itself evidence downstream agents should double-check phase-sequencing assumptions against ROADMAP.md rather than assuming completed-sounding work has actually happened.

</specifics>

<deferred>
## Deferred Ideas

- **Simulate a flight/state for preview** (type in a callsign or force a state to preview its render, reusing `render.py --callsign`/`--state`) — proposed alongside CFG-10/CFG-11 but not selected by the user. A natural companion to CFG-10 if wanted later; genuinely useful for testing illustration coverage of a specific airline without waiting for a real detection.
- **Webhook/notification integration** — considered and explicitly not proposed to the user, since it would contradict CFG-03's own already-established rationale ("deliberately not a phone push notification, to avoid reintroducing a phone dependency for an ambient device").

### Reviewed Todos (not folded)
None — no pending todos matched this phase.

</deferred>

---

*Phase: 6-companion-configuration-web-interface-visual-settings-view-s*
*Context gathered: 2026-08-27*
