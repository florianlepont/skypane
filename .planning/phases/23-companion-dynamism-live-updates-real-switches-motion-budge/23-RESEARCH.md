# Phase 23: Companion dynamism — Research

**Researched:** 2026-09-13
**Domain:** Browser-side dynamism (live updates, motion, modern controls) on a framework-free, build-free, stdlib-only Python web app
**Confidence:** HIGH on the codebase facts (every claim below carries a `file:line`), HIGH on the three named risks (two verified by live experiment in this session), MEDIUM on scope estimation

---

## Summary

Phase 23 proposes twenty-four dynamism features (D1–D24) against a companion app that is a hand-written stdlib `ThreadingHTTPServer` (`companion/app.py:48`, `:3408`) serving a 7,698-line hand-written stylesheet (`companion/static/style.css`) and fourteen ES5-subset `defer` scripts, under a CSP of `script-src 'self'` with no `unsafe-inline` and no nonce (`companion/app.py:143`). Three separate machine-enforced contracts constrain almost every item: a **twelve-deferred-script count** on the authenticated shell (`companion/test_companion_app.py:4165-4169`), **exactly one `@supports selector(:has(*))` block** in the stylesheet (`companion/test_config_page.py:4002`, `:4232`), and a **no-JS floor** proven in a real browser (`companion/test_browser_ux.py:930`, `:1377`, `:1584`).

The three risks the developer asked me to investigate hardest resolved as follows, and two of the three resolved **against the audit's own framing**:

1. **D9 (SSE) is safe from a thread-exhaustion standpoint and I measured it — but the audit's stated mechanism is architecturally impossible, and polling is the right answer here.** The device's poll is **not** served by the companion: it is served by `stub-server/byos_server.py` in a separate systemd service on port 8642, behind a separate Caddy site block (`deploy/Caddyfile:44`, `deploy/skypane-byos.service:17-24`, `deploy/skypane-companion.service:13-17`). The companion cannot starve it in-process by construction. Separately, the events D9 wants to emit (`render`, `checkin`) originate in `server/poll_loop.py`, which runs as a **`Type=oneshot` unit fired by a 30-second timer** (`deploy/skypane-poll.service:12`, `deploy/skypane-poll.timer:6-8`) — a process that exits after every cycle. There is no long-lived process in which the companion could register the hook the audit describes. An SSE endpoint would therefore have to *poll the database itself* and fan out, which for one household with one or two tabs is strictly more machinery than the client polling directly.

2. **D12 (service worker) is a genuine one-way door, and I verified the specific harm.** In the project's own harness Chromium (151.0.7922.34) I confirmed that `cache.put()` stores a response body verbatim **even when the server sent `Cache-Control: no-store`**. Every HTML response from this app is `no-store` by a deliberate Phase 18 decision, precisely because every page is session-gated (`companion/app.py:1197-1200`). A service worker silently overrides that policy and writes authenticated page content to persistent on-disk storage that survives sign-out. Retirement is also not a file deletion: a 404 on the worker script leaves the existing registration live, so a service worker can only be retired by shipping a self-destructing replacement and waiting for every browser that ever installed it to come back.

3. **D10 (cross-document View Transitions) is exactly as cheap and standalone as the audit claims, and I verified the reduced-motion opt-out empirically.** Cross-document view transitions are Baseline **limited**: Chrome/Edge 126+, Safari 18.2+/iOS 18.2+, **no Firefox** (webstatus.dev, Firefox WPT stable score 0.05). Both of the design system's two reference devices (Android at 360 px, iPhone 12-16 at 390 px) are covered. Unsupported browsers ignore the at-rule and navigate normally. Critically, the existing global reduced-motion block (`companion/static/style.css:311-317`) uses `*, *::before, *::after`, which does **not** reach `::view-transition-*` pseudo-elements — so D10 must carry its own opt-out. The CSS spec states the at-rule may be nested in a conditional group rule, and I confirmed in Chromium that `@media (prefers-reduced-motion: no-preference) { @view-transition { navigation: auto } }` parses and is retained.

**Primary recommendation:** Split this work. Land D10 + D14 + D3 first as a self-contained "motion and live counters" foundation; **replace D9's SSE with an extension of the existing `freshness.js` polling loop** and say so as a decision rather than a silent substitution; defer D12 behind an explicit developer decision with a written retirement plan; and break the remaining twenty items across three further phases along the seams named in "Scope: one phase or several" below. Twenty-four features — several of them page redesigns, each needing a no-JS fallback, a French catalogue entry, a browser-harness check and a design-system update — is not one phase on this codebase's own historical evidence.

---

## Project Constraints (from CLAUDE.md)

`./.claude/CLAUDE.md` is a stack/technology document for the whole SkyPane project (hardware, firmware, server APIs, hosting). It carries **no directives that bind companion web-app work** — its "What NOT to Use" table is about flight-data APIs, ADS-B hardware, Arduino-vs-ESP-IDF and hosting tiers, none of which this phase touches.

Two clauses do apply indirectly:

| Directive | Source | Effect on Phase 23 |
|---|---|---|
| Project Skills: `Skill("sketch-findings-skypane")` is the companion's live design system and is auto-loaded during UI work | `.claude/CLAUDE.md` § Project Skills | Every visual item (D3, D4, D5, D13, D16–D21, D24) must be checked against it **before** proposing, and updated in step after. It records rejections. |
| GSD Workflow Enforcement: no direct repo edits outside a GSD workflow | `.claude/CLAUDE.md` § GSD Workflow Enforcement | Process only; no effect on design. |
| Hosting: Hetzner CX22, 2 vCPU / 4 GB, always-on | `.claude/CLAUDE.md` § Server — Hosting | Sets the resource envelope for D9's thread question. Measured below: 200 held connections cost ~5.8 MB RSS. Not a constraint in practice. |

The stylesheet's own header comment also carries a **frame/companion boundary**: the physical e-ink frame's vendored fonts and `PALETTE_RGB` values never cross into `style.css` (`companion/static/style.css` header; restated in `sketch-findings-skypane/SKILL.md`). D5's theme carousel and D13's theme-coloured timeline dots must respect this — they render the *companion's* tokens, not the panel's palette.

---

## User Constraints

**No `23-CONTEXT.md` exists yet** (`gsd-sdk query init.phase-op 23` → `has_context: false`). This section therefore carries the constraints that bind Phase 23 from **upstream locked sources**, which the planner must honour exactly as if they were this phase's own context.

### Locked — from `22-CONTEXT.md` (developer decisions, 2026-09-12, still binding)

> **D-09 — Regression floor.** "Every existing harness keeps passing and the counts move only where a plan's own change forces it. The no-JS floor holds: every page must still be usable and every setting still saveable with scripts blocked. No new runtime dependency in `server/requirements.txt`; no vendored library; the CSP stays `script-src 'self'` with no `unsafe-inline` and no nonce."
> — `.planning/phases/22-.../22-CONTEXT.md:133-135`

> **D-10 — X9's mechanism is a bottom tab bar, not an overlay drawer.** "That second option was a mistake in the audit: `sketch-findings-skypane`'s `references/mobile-navigation.md` carries a locked **rejected** verdict on the absolute-positioned overlay, established by real-device testing during 06.6.1-06 — the overlay could only cover content, never push it… **Do not implement an overlay drawer.** If a plan finds bottom tabs unworkable for a reason this context does not anticipate, it must say so and stop rather than fall back to the rejected pattern."
> — `.planning/phases/22-.../22-CONTEXT.md:137-141`

> **D-11 — Sequencing is by dependency wave, never by calendar.** "**Planner: do not put durations, dates, week numbers or day estimates into any PLAN.md.** Order tasks by what must exist before what."
> — `.planning/phases/22-.../22-CONTEXT.md:143-145`

> **D-12.1 — absent checkbox semantics.** `display_enabled`/`quiet_hours_enabled` resolve absent → *leave unchanged*; `led_enabled` and the two notification checkboxes keep absent → `False`.
> — `.planning/phases/22-.../22-CONTEXT.md:147-149`, implemented at `companion/pages/config_page.py:3926-3958` and `:4236`

### Locked — from `sketch-findings-skypane` (design system, authority)

- **Minimum supported viewport: 360 px.** Developer decision, 2026-09-13. 320 px is out of contract but its existing assertions in `companion/test_browser_ux.py` must not be deleted. (`SKILL.md:19-40`)
- **Three rejected navigation patterns, explicitly unreversed by Phase 22:** full-screen overlay, slide-in drawer with dimming backdrop, and `position: absolute` on `.mobile-nav`. "If a future phase wants any of them back, it needs a new argument and a new decision — not a silent rewrite of these three lines." (`references/mobile-navigation.md:122-126`)
- **Accent reservation list** (`companion/static/style.css:51-90`): after Phase 22, `.stat-tile--accent`'s top rail is the Frame strip's only accent and the page's accent has returned to Save / the page's one primary action. New accent consumers require a stated decision.
- **Colour-separation contract, executable:** `--color-accent` must stay measurably distinguishable from every `--color-status-*` in both themes, enforced by `companion/contrast_check.py` (`MIN_SIGNAL_PERCEPTUAL_DISTANCE = 28.0`, `MIN_SIGNAL_HUE_SEPARATION = 24.0`, `contrast_check.py:69`, `:83`).

### Claude's Discretion (in the absence of a CONTEXT.md)

Plan count, wave grouping, file-level sequencing, and the mechanism for any item where the audit names an outcome but not a means. **Not discretionary:** anything listed under "Conflicts with a locked decision" below.

### Deferred / Out of scope

Everything in `22-AUDIT.md`'s B/X/C/T tables is closed (Phase 22, CFG-25…CFG-31 all complete per `.planning/REQUIREMENTS.md:147-153`) except **T16**, which was explicitly optional and none was taken. T16's items (gzip, hashed filenames, a muted-text token, dead-selector pruning, a shared `ui.js`) overlap D11 — see the coupling note below.

---

## Phase Requirements

No requirement IDs are assigned yet — `.planning/ROADMAP.md:1067` reads `**Requirements**: TBD (assign at planning; audit handles D1–D24)`. The audit's D1–D24 are the specification. This section will be filled by the planner.

---

## Architectural Responsibility Map

The single most important correction this research makes is topological. The audit (and the phase brief) assume the companion is one server doing several jobs. It is not: **four processes** share one VPS and one Caddy.

| Capability | Primary Tier | Secondary Tier | Rationale |
|---|---|---|---|
| Device poll / panel delivery | `stub-server/byos_server.py`, port 8642, own systemd unit | Caddy site block `203-0-113-10.nip.io` | `deploy/skypane-byos.service`; vendored, off-limits to modify (`stub-server/VENDOR.md`) |
| ADS-B detect → render → write DB/gallery | `server/poll_loop.py`, **`Type=oneshot` + 30 s timer** | — | `deploy/skypane-poll.service:12-13`, `deploy/skypane-poll.timer:6-8`. Exits after each cycle. |
| Companion HTML, settings, quick toggles | `companion/app.py`, port 8643, own systemd unit | Caddy site block `config-203-0-113-10.nip.io` | `deploy/skypane-companion.service`; "Separate process (D-03): … a failure or restart in this web-facing configuration interface cannot take down the ADS-B detection loop or the panel the device fetches" (`:13-17`) |
| **Change detection for a live UI (D1/D9/D22)** | **Companion server, reading the DB/gallery it already reads** | Browser `fetch` loop | No IPC exists between the poll loop and the companion. Any "push" is a companion-side poll re-labelled. |
| Optimistic switch state (D2) | Browser (`fetch` + rollback) | Companion `/quick/*` routes | Server stays the authority; browser owns only the pending visual state |
| Motion, view transitions (D3/D10) | Browser / CSS | — | Zero server involvement; this is why D10 is genuinely cheap |
| Data drawings (D8/D13/D20/D21) | **Server-rendered SVG in Python** | Browser only for hover/tap | Matches the existing `battery-trend.js` + `health_page.py` split: the server draws, the script only decorates |
| gzip / compression (D11) | **Caddy (`encode` directive)** | Companion `send_bytes()` | One line of deployment config vs. Accept-Encoding negotiation in Python. See D11 below. |
| Offline shell (D12) | Browser service worker | — | The one tier with *persistent, self-updating* state outside the repo. See Runtime State Inventory. |

**What this map changes:** D9's premise ("one thread per connected tab; events emitted after `_save_to_gallery`/`_record_history`") mixes two tiers that cannot see each other. And the phase brief's own fear ("a companion that starves the frame's poll") is **not reachable** at the Python level — the frame's poll is a different process. The real shared resources are the VPS's 2 vCPU / 4 GB and the single Caddy.

---

## Standard Stack

There is no stack to choose. The phase constraint is **framework-free, build-free, no external dependency** (`.planning/ROADMAP.md:1066`; `22-CONTEXT.md:133-135`). Everything below already exists in the repo or in the browser.

### Core (already present)

| Component | Version | Purpose | Why standard here |
|---|---|---|---|
| Python stdlib `http.server.ThreadingHTTPServer` | 3.11.15 (repo venv) | The whole server | `companion/app.py:48`, `:3408`. Thread-per-connection, `daemon_threads = True`, `request_queue_size = 5`, `protocol_version` left at `HTTP/1.0` (verified by introspection this session) |
| Hand-written ES5-subset scripts, `defer`, one file per concern | — | All client behaviour | Fourteen files in `companion/static/`; twelve on the authenticated shell (`companion/layout.py:1964-1977`), `login-card.js` on the login shell only, `battery-trend.js` emitted by Health's body (`companion/pages/health_page.py:2626`) |
| `companion/static/style.css` | 7,698 lines | All presentation | One file, no build step, no preprocessor |
| Playwright (dev-only) | 1.62.0 | Browser harness | `server/requirements-dev.txt`; never in `server/requirements.txt`, never deployed |
| Caddy | v2 (deployed) | TLS, reverse proxy, access log | `deploy/Caddyfile` |

### Browser platform features the D-items need (all verified against the authoritative Web Platform Status API and, where noted, in the project's own Chromium 151)

| Feature | Baseline status | Chrome | Edge | Firefox | Safari | Needed by |
|---|---|---|---|---|---|---|
| Same-document View Transitions | **newly** (2025-10-14) | 111 | 111 | 144 | 18 | D3 (optional) |
| **Cross-document View Transitions** (`@view-transition { navigation: auto }`) | **limited** | 126 | 126 | **none** | 18.2 / iOS 18.2 | **D10** |
| `@starting-style` | **newly** (2024-08-06) | 117 | 117 | 129 | 17.5 | D3's `<dialog>` fade/zoom |
| `<dialog>` | **widely** (since 2022-03-14) | 37 | 79 | 98 | 15.4 | D3, D5, D15, D23 — already in use |
| `EventSource` (SSE) | widely available | — | — | — | — | D9 (not recommended) |
| Service Workers + Cache API | **widely** (since 2018-04-30) | 45 | 17 | 44 | 11.1 | D12 |
| `navigator.share()` | **limited** | 128 (desktop) / 61 Android | 93 | **desktop: none**, Android 79 | 12.1 / iOS 12.2 | D15 |
| `interpolate-size` / `calc-size()` | **limited** — Chromium only | 129 | 129 | none | none | D3's "height animation" — **do not use**; use `grid-template-rows: 0fr → 1fr` as the audit already says |
| `details-content` (animating `<details>`) | **newly** (2025-09-16) | 131 | 131 | 143 | 18.4 | D3's disclosure animation (optional) |

Source for every row: `https://api.webstatus.dev/v1/features/<id>` queried this session. `view-transition-name` and `web-share` have no dedicated feature id; `share` was used for `navigator.share()`.

**Verified in Chromium 151.0.7922.34 (the exact browser `companion/test_browser_ux.py` drives), this session:**
- `@media (prefers-reduced-motion: no-preference) { @view-transition { navigation: auto } }` **parses and is retained** in the CSSOM — the nested form D10 needs works.
- `@starting-style { … }` parses.
- `document.startViewTransition` is a function.
- `navigator.share` is **`undefined`** — D15 cannot be exercised by the harness at all; it is manual-only on a real phone.
- Over `http://127.0.0.1`, `window.isSecureContext === true`, `'serviceWorker' in navigator === true`, `'caches' in window === true` — so D12 **is** machine-verifiable by the existing harness, which materially improves its risk profile if it is taken.

### Alternatives considered

| Instead of | Could use | Tradeoff |
|---|---|---|
| SSE `/events` (D9) | Extending `freshness.js`'s existing 45 s polling loop to Home and Display | **Recommended.** No new mechanism, no held threads, reuses a loop that already has a retry ladder, an in-flight guard and targeted swaps (`freshness.js:170-195`, T13, landed 22-15). The only thing SSE buys is sub-poll-interval latency, and the underlying data changes at most every 30 s (`server/poll_loop.py:77`, `deploy/skypane-poll.timer:7`) |
| gzip in `send_bytes()` (D11) | `encode zstd gzip` in `deploy/Caddyfile` | **Recommended for production.** One line, correct `Vary`, correct `Accept-Encoding` negotiation, no Python. Cost: local dev and every harness hit the Python server directly and would see no compression — so if the goal is a *pinned* behaviour, it has to be in Python. State the choice; do not do both. |
| Hashed filenames + `immutable` (D11) | Leave the current `public, max-age=300` (`companion/app.py:1854`, `:1883`) | **Recommended to drop.** Hashing implies generating names at build or boot; a build step is forbidden by the phase constraint, and a boot-time hash means fourteen route constants become dynamic, breaking the route-constant pinning in `test_companion_app.py`. The 300 s max-age already prevents re-download on navigation. |
| Client-side canvas crop (D19) | Server-side `illustration_normalize.py` alone, with a client *preview* only | **Recommended.** The server must normalise regardless (never trust a client-supplied image); a client crop that "matches" is a second implementation of the same contract that can drift. Preview ≠ authority. |

**Installation:** none. No package is added by any recommendation in this document.

---

## Package Legitimacy Audit

**No external packages are installed by this phase.** The phase constraint is explicit (`.planning/ROADMAP.md:1066`: "Framework-free, build-free, no external dependency"), reinforced by the still-binding `22-CONTEXT.md` D-09 ("No new runtime dependency in `server/requirements.txt`; no vendored library").

| Package | Registry | Disposition |
|---|---|---|
| *(none)* | — | N/A — zero new dependencies proposed |

The one dev-only dependency this phase relies on, `playwright==1.62.0`, is already pinned in `server/requirements-dev.txt` and was installed and verified working in this session (Chromium 151.0.7922.34 launched successfully). `deploy/deploy.sh` installs `server/requirements.txt` only, so it never reaches the VPS.

**slopcheck was not run because no package is being added.** If a plan ever proposes one, it must be gated behind a `checkpoint:human-verify` task *and* it contradicts a locked decision, so it needs a new developer decision first.

---

## Architecture Patterns

### System data flow (the four processes)

```
                    ┌──────────────────── Hetzner CX22 (2 vCPU / 4 GB) ───────────────────┐
                    │                                                                      │
  e-ink frame ──┐   │  ┌─ Caddy ─────────────────────────────────────────────┐            │
  (ESP32-S3)    └──►│  │  203-0-113-10.nip.io      ──► 127.0.0.1:8642 ────────┼─► byos_server.py
   HTTP poll        │  │    (+ json access log ─┐                            │    (vendored, serves panel.bin)
   + X-Battery-Mv   │  │                        │                            │
                    │  │  config-…nip.io        │  ──► 127.0.0.1:8643 ───────┼─► companion/app.py
  browser ─────────►│  │                        │                            │    ThreadingHTTPServer
  (household)       │  └────────────────────────┼────────────────────────────┘    ├─ HTML pages
                    │                           │                                  ├─ /quick/display, /quick/quiet-hours
                    │                           ▼                                  ├─ /settings (the dirty-state form)
                    │          /opt/skypane/state/caddy-access.log                  └─ /static/*, /gallery/*
                    │                           │                                        │
                    │                           │ tail_caddy_battery_log()                │ reads
                    │                           ▼                                        ▼
                    │   ┌─ systemd timer, every 30 s ──► poll_loop.py --once ──► history.db (runway_events,
                    │   │    Type=oneshot: STARTS, RUNS ONE CYCLE, EXITS          device_health, meta)
                    │   │    _record_history()  ─────────────────────────────────► + state/gallery/*.png
                    │   └──────────────────────────────────────────────────────────► + state/panel.bin
                    └──────────────────────────────────────────────────────────────────────┘

  ✗ There is NO channel from poll_loop.py back into companion/app.py.
    D9's "events emitted after _save_to_gallery/_record_history" cannot be wired as written.
  ✓ companion/app.py DOES call poll_loop.run_once() in-process for the manual
    POST /poll-now button only (companion/app.py:3111, guarded by _POLL_LOCK at :642).
```

### Pattern 1: the "served everywhere, no-ops via guard clause" script convention

**What:** every one of the twelve shell scripts is emitted unconditionally on every authenticated page and returns immediately if its own DOM marker is absent.
**Where it is stated:** `companion/layout.py:2010-2041` (the comment block naming each script and its guard), and each file's own head — e.g. `freshness.js:210-214` returns unless `[data-loaded-at]` exists.
**Why it matters for Phase 23:** a new script is one cached asset served to every page, not a per-page include. But it **changes the pinned count**, so every new script is a deliberate, test-touching decision.

**Example (the guard clause, verbatim shape):**
```javascript
// Source: companion/static/freshness.js:210-219
  var loadedAtEl = document.querySelector("[data-loaded-at]");
  if (!loadedAtEl) {
    return;
  }
  var raw = loadedAtEl.getAttribute("data-loaded-at");
  if (!raw) {
    return;
  }
```

### Pattern 2: the server-rendered, script-decorated drawing

**What:** the server renders the whole SVG in Python; the script only adds hover/keyboard behaviour and never recomputes a value.
**Where:** `companion/pages/health_page.py:446-470` defines `BATTERY_READOUT_ID`, `SPARKLINE_HIT_CLASS`, `SPARKLINE_DOT_CLASS`, `SPARKLINE_LINE_CLASS`, `SPARKLINE_AXIS_CLASS` as Python constants whose literals are asserted present in `battery-trend.js` by a cross-file harness check.
**Apply to:** D13 (timeline), D20 (punctuality grid), D21 (battery ring), D8 (battery chart upgrade), D16 (runway map). Every one is data already in `history.db`.
**Anti-pattern to avoid:** computing the verdict client-side. `freshness.js`'s header states the rule for the whole app: "this file still computes no health state of any kind" (`freshness.js:32-40`).

### Pattern 3: the attribute-with-fallback i18n idiom — **and its enforcement**

**What:** a script carries an English fallback literal and reads the real, translated string from a server-rendered `data-*` attribute.
**Where:** `dirty-state.js:202-206`, `copy-button.js:54`, `flight-rows.js:103-107`, `freshness.js:204-205`.
**The enforcement:** `companion/test_i18n.py` Check 6 is a regex scan over **exactly two shapes** — `var ALL_CAPS_NAME = "literal";` and `… || "literal"` — across every JS file, and demands a French catalogue entry for each (`test_i18n.py:31-37`). **Every new script in Phase 23 that carries any user-facing English will fail this harness until `companion/i18n_fr/` gains the entry.** The scan explicitly cannot see string concatenation or template literals — and template literals are separately banned by the ES5-subset guards.

### Pattern 4: the targeted-swap refresh loop (the thing D1 should extend)

```javascript
// Source: companion/static/freshness.js — the mechanism, summarised
// 1. Guard on [data-loaded-at]; return if absent.
// 2. setInterval at AUTO_REFRESH_INTERVAL_MS (45000, freshness.js:170).
// 3. fetch(location, {redirect: "manual"}) behind an in-flight flag.
// 4. DOMParser.parseFromString + document.importNode + replaceChild —
//    never innerHTML/insertAdjacentHTML/document.write (banned sinks).
// 5. Swap only the selectors in health_page.REFRESH_SWAP_SELECTORS,
//    skipping any region that is unchanged or contains document.activeElement.
// 6. On any failure: exponential ladder 45s → 90s → 3m → 6m → 10m ceiling
//    (RETRY_BASE_MS / RETRY_CEILING_MS, freshness.js:189-190), behind a
//    NEUTRAL .dot--off "Paused" / "Reconnecting…" badge — never a warning.
// 7. visibilitychange gates the loop; a background tab makes zero requests.
```
The swap-target list is a **pinned cross-file contract**:
```python
# Source: companion/pages/health_page.py:438-444
REFRESH_SWAP_SELECTORS = (
    ".dashboard-grid",
    "div.banner--anomaly, div.banner--warn",
    "section.banner",
    ".page-header__freshness",
    'a[href="/health"]',
)
```
D1's "reuse `freshness.js` on `/` and `/display`" therefore means **three** such tuples to keep in sync, or one generic `data-swap-region` attribute convention. The audit names neither.

### Pattern 5: the single `@supports selector(:has(*))` block

All live-selection state (`.theme-chip:has(input:checked)`, `.runway-card:has(input:checked)`, `.frame-colours__list li:has(input:checked)`) lives in **one** block at `companion/static/style.css:2359`, with `--selected` demoted to the no-`:has()` fallback plus a dashed "Current" saved-state marker. The specificity arithmetic is documented at `style.css:2323-2345` and is explicitly marked "verified, not to be re-derived". Two separate checks assert the block count is exactly 1 (`test_config_page.py:4002`, `:4232`).

### Anti-patterns to avoid

- **A second `@supports selector(:has(*))` block.** Two harness checks fail immediately. Phase 15's D-05 already tried this once and the block was retired.
- **An overlay drawer for the mobile nav.** Three recorded rejections plus a locked Phase 22 decision. See "Conflicts" below.
- **Computing a device/health verdict in JavaScript.** `freshness.js:32-40` and `battery-trend.js`'s own contract forbid it.
- **`innerHTML` / `insertAdjacentHTML` / `document.write` / `eval` / arrow functions / `let` / `const` / backticks** in any script. Pinned per-file by name in `test_companion_app.py:4143`, `:4217-4218`, `test_status_pages.py:6720-6731`, `:10392`, `test_view_pages.py:2724`.
- **A per-rule `@media (prefers-reduced-motion: reduce)` block for a plain transition.** The global block at `style.css:311-317` already covers it; `accessibility-contrast.md:90` records a redundant per-rule block as "dead code, not a safety net". **Exception:** view-transition pseudo-elements, which the global block genuinely does not reach.

---

## The D-item dossier

Scope column is the audit's own (**S** = one file/rule, **M** = a few files or one component, **L** = a redesign). "Touches" names the pinned contract each item moves.

| ID | Verdict | Touches | Notes |
|---|---|---|---|
| **D1** Home/strip self-refresh | **Take — as polling, not SSE** | `freshness.js`, a new `REFRESH_SWAP_SELECTORS` per page, the no-JS floor (must stay a no-op) | Needs a swap-region convention. Races D2 — see coupling #4. |
| **D2** `role="switch"` + fetch | **Take, narrowed to two switches** | `/quick/*` routes, `frame_strip_html()`, the no-JS floor, X1/D-04 | LED and notifications have **no** quick route and live in the settings form. See coupling #1/#2. |
| **D3** Motion budget | **Take — but delete the overlay-drawer clause** | `style.css` reduced-motion block, `@keyframes` (the app has **zero** today), `:has()` block (do not touch) | **Conflicts with a locked decision.** See below. |
| **D4** Home hero | Take, but after D1/D13/D21 | `home_page.py`, `.home-columns`, design system | A page redesign. Phase 21 already rebuilt Home once and Phase 22 amended it. |
| **D5** Theme carousel | Take, with care | `.theme-chip*`, the **one** `:has()` block, `theme-preview.js`, `.theme-chip--compact` | Highest risk of opening a second `@supports` block. |
| **D6** Installable app | **Take, reduced** | New `/manifest.webmanifest` route, `<meta name="theme-color">`, favicon assets | Its third clause ("bottom tab bar (X9)") **already shipped in Phase 22** (`layout.py` `_tab_bar_html`, 22-14). Only manifest + theme-color remain. Manifest icons: the app has only an inline SVG data-URI favicon (`layout.py:645-652`); installability on Android reliably wants 192/512 PNGs — new binary assets in a repo that has none. |
| **D7** Live flights list | Take, after D1 | `history_page.py`, `flight-rows.js`, `list-filter.js` | "Sticky day headers" — note Phase 22's **T4 removed the false sticky-header claim outright**; re-adding sticky is a reversal needing a stated reason. |
| **D8** Battery chart upgrade | Take | `health_page.py` SVG, `battery-trend.js` | "≈ 41 days left" does not exist anywhere; `companion/battery.py` has only `battery_percent()` (a linear 3.3–4.2 V estimate). A slope estimator is new arithmetic. |
| **D9** SSE `/events` | **Decline as specified; substitute polling** | Would add a held-thread endpoint and a new script | See "Risk 1" in full below. |
| **D10** View Transitions | **Take first — genuinely cheap and standalone** | 1 at-rule + ~3 `view-transition-name` declarations | Needs its own reduced-motion wrapper. See "Risk 3". |
| **D11** Prefetch + gzip + hashed names | **Split: take prefetch + gzip, drop hashed names** | `Caddyfile` (gzip), `layout.py` (prefetch links), route constants (hashing) | Hashed filenames imply a build step — forbidden. Overlaps the deliberately-optional T16. |
| **D12** Service worker | **Do not take without an explicit decision** | Persistent browser state, the `no-store` policy, session security | See "Risk 2". |
| **D13** Day timeline | Take | `home_page.py` SVG, `runway_events` | Data confirmed present: `ts`, `confirmed_state`, `airline`, `tracked_runway` (`server/history_db.py:103-118`). Quiet-hours zone comes from `device_config`, which is **current**, not historical. |
| **D14** Live counters | **Take first — standalone** | +1 script → **breaks the twelve-script check**; needs FR entries for "waiting…" | The "breathing dot" is this app's **first** `@keyframes`. |
| **D15** Share | Take last, or drop | New script | `navigator.share` is `undefined` in the harness browser — **untestable by machine**. Firefox desktop has no support. Manual-only verification. |
| **D16** Runway SVG map | Take | `config_page.py` runway fieldset, `.runway-card`'s `:has()` state | The three `runway-*.png` files are 338–371 KB **photographs/drawings**, not vectors — "reuse" means redrawing, not embedding. |
| **D17** Quiet-hours dial | Take | `config_page.py`, `dirty-state.js` (presets at `:164-166`), the no-JS floor, the touch-target register | Claims to "fix B14" — **B14 already landed in 22-10**. Must not regress it. A drag handle on a ring is the hardest touch-target case in the whole phase at 360 px. |
| **D18** Wake slider + gauges | Take | `config_page.py` wake-interval group, `server/wake.py`, new battery-life arithmetic | The "battery life ≈ N days" figure does not exist; needs the same slope estimator as D8. |
| **D19** Drag-and-drop artwork | Take, preview-only crop | `airlines_page.py`, `illustration_normalize.py` | Server must keep normalising. Client crop is a preview, never the authority. |
| **D20** Wake punctuality grid | **Take, but re-scope the claim** | `health_page.py`, `device_health` | `device_health` records **observed** check-ins only (`history_db.py:124-133`). "Honoured-wake rate" needs the *historical expected interval*, which is not recorded anywhere — `wake_interval_s` and quiet hours are stored as current config, not versioned. Honest version: a check-in **density** grid, not a rate. |
| **D21** Battery ring | **Take — standalone** | `health_page.py`, `home_page.py`, reuses `battery.battery_percent()` | The "≈ 38 days left" half needs D8's estimator. |
| **D22** Honest live indicator | **Already ~80 % shipped** | `freshness.js:189-205` | T13 (22-15) already landed the retry ladder, the neutral `.dot--off` Paused/Reconnecting badge and the in-flight guard. D22 adds only the ticking "updated 12 s ago" (which is D14) and the pulse. Re-scope, do not re-implement. |
| **D23** Shortcuts + ⌘K palette | Take late | +1 script, a new `<dialog>`, state-changing actions from a keystroke | CSRF posture is `SameSite=Strict` only, no token (`companion/app.py:2178-2180`, `auth.py:263`). A palette action must be a POST with `credentials: 'same-origin'`, never a GET. |
| **D24** Guided first run + empty states | Take late | `home_page.py`, every empty list, `empty_state()` | `empty_state()` already has a compact variant from 22-12 (C1). Reuse it. |

---

## Risk 1 — D9: SSE on a stdlib `ThreadingHTTPServer`

### What I measured

I ran a purpose-built experiment reproducing `companion/app.py`'s handler shape (`timeout = 30`, default `HTTP/1.0`) on `http.server.ThreadingHTTPServer`, holding N SSE connections open while issuing ordinary requests. Results (Python 3.11.15, Linux, this session):

| Held SSE connections | Threads (delta) | RSS delta | Per-connection RSS | Plain GET (serial) | 20 concurrent plain GETs, p50 / max |
|---|---|---|---|---|---|
| 0 | 0 | — | — | 0.7–1.3 ms | 9 ms / 1 037 ms |
| 5 | +5 | 360 KB | 72 KB | 0.6–1.3 ms | 8 ms / 1 026 ms |
| 20 | +20 | 916 KB | 46 KB | 0.6–1.2 ms | 11 ms / 1 021 ms |
| 50 | +50 | 1 828 KB | 37 KB | 0.6–1.4 ms | 12 ms / 1 021 ms |
| 200 | +200 | 5 812 KB | 29 KB | 0.8–1.2 ms | 9 ms / 1 011 ms |

**Findings, stated plainly:**

- **There is no thread or connection ceiling in `ThreadingHTTPServer`.** It spawns one unbounded `threading.Thread` per accepted connection. `request_queue_size = 5` is the *listen backlog*, not a concurrency limit.
- **Threads are not leaked.** `ThreadingHTTPServer` sets `daemon_threads = True` (verified by `inspect.getsource`), and `socketserver._Threads.append()` returns early for daemon threads, so the `_threads` bookkeeping list never grows. After closing all 200 clients, the thread count returned exactly to baseline.
- **Held streams do not measurably slow other requests.** The ~1 s tail in the burst column is present at **N = 0** and is unchanged at N = 200 — it is the `request_queue_size = 5` accept backlog, a pre-existing property of this server, entirely unrelated to SSE.
- **Memory cost is ~29–46 KB RSS per held connection** — 200 tabs would cost under 6 MB on a 4 GB CX22.
- **`Handler.timeout = 30` (`companion/app.py:113`, `:1168`) is an accidental safety valve.** `StreamRequestHandler` applies it to the socket in both directions, so a client that stops reading until its receive buffer fills will make the server's `send` raise `socket.timeout` after 30 s, freeing the thread. A heartbeat below 30 s is therefore required, and also sufficient.
- **Caddy will not cut the stream.** Caddy's `reverse_proxy` flushes immediately when the upstream response carries `Content-Type: text/event-stream`, regardless of `flush_interval`, and both the HTTP-transport read and write timeouts default to "no timeout".
- **The device's poll cannot be starved.** Different process, different port, different systemd unit, different Caddy site block.

### The finding that actually settles it

**The audit's mechanism cannot be built as written.** D9 says events are "emitted after `_save_to_gallery`/`_record_history`". Those functions live in `server/poll_loop.py` (`:835`, `:758`), which runs as `Type=oneshot` under a 30-second timer (`deploy/skypane-poll.service:12`, `deploy/skypane-poll.timer:6-8`) — a process that starts, runs one cycle, and exits. It has no handle on the companion process and no IPC to it. `companion/app.py` calls `poll_loop.run_once()` in-process for exactly one path: the manual `POST /poll-now` button (`companion/app.py:3111`, serialised by `_POLL_LOCK` at `:642`).

So an SSE server in the companion would have to **detect** changes itself — stat the gallery directory, poll `history.db` — and fan out. That is a server-side poll wearing a push-shaped hat. Against a data source that changes at most every 30 seconds, for a household with one or two tabs, it adds:

- a new long-lived endpoint with its own bounded-concurrency, heartbeat and idle-timeout design,
- a new client script (breaking the twelve-script count),
- a server-side change detector (a second polling loop),
- and a fallback-to-polling path that must be tested — meaning the polling path has to exist and be correct **anyway**.

### Verdict

**SSE is technically safe on this server under a bound, but it is the wrong mechanism here, and I recommend declining it.** The honest answer the phase brief asked for: **polling is the right mechanism for this server.** `freshness.js` already implements a better-behaved version of what D9 wants — visibility-gated, in-flight-guarded, exponentially backing off, with a neutral reconnecting state, and targeted swaps that preserve focus (`freshness.js:120-195`). Extending it to `/` and `/display` at a 30 s cadence delivers D1, D22 and the "fallback to polling" half of D9 with **zero new mechanisms**.

**If the developer takes SSE anyway**, the bounded design is:

| Bound | Value | Reason |
|---|---|---|
| Hard cap on concurrent streams | 4 (module-level counter + `threading.Lock`, same shape as `_POLL_LOCK` at `app.py:642`) | One household. Over the cap, respond **503 with `Retry-After`** and let `EventSource` fall back to the polling loop. |
| Heartbeat | 15 s (`: ping\n\n`) | Must be < `REQUEST_SOCKET_TIMEOUT_S` (30 s) or the handler's own socket timeout kills healthy streams. |
| Idle/max lifetime | close and let the client reconnect after ~10 min | Bounds the blast radius of any leak; `EventSource` reconnects automatically. |
| Session gate | `require_session()` before the first byte | `/events` would carry render/check-in/battery telemetry. Same gate as every other authenticated route. |
| Browser connection limit | note it | Over HTTP/1.1 a browser allows ~6 connections per origin; one permanent `EventSource` leaves 5. Caddy serves HTTP/2 over TLS in production, where this does not apply — but a LAN/direct-to-8643 access path would hit it. |
| Never | do not set `protocol_version = "HTTP/1.1"` on the shared `Handler` to make SSE nicer | That turns on keep-alive for **every** route and changes the server's connection lifecycle app-wide. Out of proportion. |

**Confidence: HIGH.** Every number above was measured this session; every topology claim carries a `file:line`.

---

## Risk 2 — D12: the service worker as a one-way door

### The verified harm

In the project's own harness Chromium (151.0.7922.34), over `http://127.0.0.1` (a secure context — confirmed `window.isSecureContext === true`), I ran:

```javascript
const c = await caches.open('t');
const resp = await fetch('/');            // server sent: Cache-Control: no-store
await c.put('/', resp.clone());
const got = await c.match('/');
await got.text();
```

**Result:** `Cache-Control: no-store` on the response, and the Cache API returned the body verbatim: `'<p>SECRET-SESSION-CONTENT</p>'`.

This matters because **every HTML response from this app is `no-store`, deliberately**:

```python
# Source: companion/app.py:1197-1200
        # Phase 18 (audit): every HTML page is either session-gated or a
        # login form — never something a shared cache or the back button
        # should replay after sign-out.
        self.send_header("Cache-Control", "no-store")
```

A service worker that caches "the page shell + last Home response" (D12's own words) therefore **silently reverses a documented security decision**, writing session-gated admin-panel content to persistent on-disk browser storage that survives sign-out, survives session revocation (`auth.is_revoked`, `app.py:1250`), and is not cleared by the logout path. On a shared household device — which is precisely this app's stated audience ("a second household member with basic computer skills") — that is a real regression, not a theoretical one.

### The retirement story

- **Deleting `sw.js` does not remove the worker.** A 404 during the update check leaves the existing registration active and controlling. The only reliable retirement is to *replace* the file with a self-destructing worker that calls `self.skipWaiting()` on `install`, then on `activate` calls `self.registration.unregister()`, iterates `caches.keys()` → `caches.delete()`, and navigates every client via `self.clients.matchAll()`.
- **That retirement only reaches a browser that returns to the site.** The browser re-fetches the worker script on navigation, bypassing HTTP cache only if the last fetch was over 24 hours ago. A browser that never comes back keeps the old worker forever.
- **Therefore: a service worker cannot be safely retired unless its retirement path ships with it.** The phase brief's instinct is correct and I can put a number on it: the removal cost is not "delete a file", it is "ship a second worker and wait".

### Interaction with D11

D11 proposes gzip and hashed filenames with `Cache-Control: immutable`. A service worker precache list keyed to hashed filenames is a **generated manifest** — that is a build step, which the phase constraint forbids. If both D11-hashing and D12 are taken, they force each other into a build step. Taking gzip via Caddy and dropping hashing removes that pressure entirely.

### Verdict

**Do not take D12 without an explicit developer decision recorded in `23-CONTEXT.md`.** If it is taken, the minimum conditions are:

1. **Cache nothing session-gated.** Precache `style.css`, the twelve scripts and the favicon only — assets already served `public, max-age=300` pre-auth (`app.py:1854`, `:1883`). The "last Home response" half of D12 must be **dropped**, or the `no-store` decision must be formally reversed with its own argument.
2. **The self-destructing replacement worker ships in the same phase**, committed and tested, so retirement is a one-commit operation.
3. **A browser-harness check pins it.** This is now known to be possible: service workers and the Cache API are available to the harness over `http://127.0.0.1`. A check that installs the worker, then installs the self-destructor, then asserts `navigator.serviceWorker.getRegistrations()` is empty and `caches.keys()` is empty, converts the one-way door into a tested two-way one.
4. **`/sw.js` needs a root-scope route** (the app serves scripts from `/static/*`; a worker at `/static/sw.js` is scoped to `/static/` unless a `Service-Worker-Allowed` header widens it). A new root route is simpler than a header.

**Confidence: HIGH** on the `no-store` bypass (measured) and on the 404 behaviour (multiple independent sources agree, and none contradicts). **MEDIUM** on whether any specific current browser additionally unregisters on 404 — treat that as unavailable and ship the self-destructor regardless.

---

## Risk 3 — D10: native multi-page View Transitions

### Support, from the authoritative source

`https://api.webstatus.dev/v1/features/cross-document-view-transitions`, queried this session:

| Browser | Version | Date |
|---|---|---|
| Chrome / Chrome Android | 126 | 2024-06-11 |
| Edge | 126 | 2024-06-13 |
| Safari / Safari iOS | 18.2 | 2024-12-11 |
| **Firefox / Firefox Android** | **not implemented** | — (WPT stable score 0.053) |

Baseline status: **limited**. Developer-signals upvotes: 57.

Compare the same-document feature (`document.startViewTransition`), which reached Baseline **newly** on 2025-10-14 with Firefox 144 — the cross-document opt-in is a full generation behind it.

### Degradation

A browser without support **ignores the `@view-transition` at-rule entirely** and performs an ordinary navigation. There is no flash, no layout shift, no fallback code path, and no feature detection needed. This is the cleanest degradation of any item in the D-table.

### Against the design system's own reference devices

`sketch-findings-skypane/SKILL.md:19-21` names two reference devices: **an Android at 360 px** (Chrome → supported since 126) and an **iPhone 12-16 at 390 px** (Safari iOS → supported since 18.2). Both get the transition. Firefox desktop does not — and gets today's behaviour exactly.

### The reduced-motion trap the audit does not name

D10 says "disabled under reduced motion". The existing global override is:

```css
/* Source: companion/static/style.css:311-317 */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
    scroll-behavior: auto !important;
  }
}
```

`*` matches **elements**. The view-transition pseudo-elements (`::view-transition-group()`, `::view-transition-old()`, `::view-transition-new()`, and the `::view-transition` root) form a separate pseudo-element tree and are **not** matched by `*, *::before, *::after`. The global block therefore does **not** disable a cross-document view transition. This is a silent gap: shipping D10 without its own rule would give reduced-motion users full-page cross-fades.

**The fix, verified working in Chromium 151 this session** (the nested at-rule parses and is retained in the CSSOM):

```css
/* Source: CSS View Transitions Module Level 2, §8.3.1 —
 * "Note: as per default behavior, the @view-transition rule can be nested
 *  inside a conditional group rule such as @media or @supports."
 * Verified parsing in Chromium 151.0.7922.34 this session. */
@media (prefers-reduced-motion: no-preference) {
  @view-transition { navigation: auto; }
}
```

This is preferable to an `animation: none` override on the pseudo-elements because it prevents the transition from being *set up* at all, rather than running it with a zeroed duration.

### Verdict

**D10 is still cheap and still standalone — confirmed.** It is one media-wrapped at-rule plus a handful of `view-transition-name` declarations on the sidebar, the page title and the frame picture. It adds no script, touches no pinned count, and needs no no-JS consideration (it is CSS-only, so a scripts-blocked browser gets it too — a rare case where the enhancement survives the no-JS floor intact).

**One caveat the audit does not mention:** `view-transition-name` values must be unique per document. The sidebar nav, the page title and the picture are each rendered once per page (`layout.py:1930-1960`) — but `sidebar_nav()` and `_mobile_nav_html()` and `_tab_bar_html()` render **three** nav copies simultaneously in the DOM, hidden by CSS at different breakpoints (`layout.py:1905-1920`). Naming "the sidebar" must therefore target `.dashboard-sidebar` specifically, not a shared nav class, or the name collides and the transition silently drops. **Confidence: HIGH** (the three-nav-copies fact is documented in `layout.py`'s own comment); the collision behaviour is spec-level and **MEDIUM** — worth a one-line harness assertion.

**Because D3 must own the reduced-motion rule, D3 is a prerequisite of D10, not its peer.** The audit's order ("D10 and D14 first") is very slightly wrong: it should be "D3's reduced-motion clause, then D10 and D14".

---

## Independence and hidden couplings

### Genuinely independent (can land in any order, touch nothing else)

| Item | Why |
|---|---|
| **D10** | CSS-only, one at-rule plus name declarations (given D3's reduced-motion rule) |
| **D21** | One SVG built in Python from `battery.battery_percent()`, which already exists |
| **D11's gzip half** | One line in `deploy/Caddyfile`; touches no Python |
| **D15** | One script, one `<dialog>`; but see the "+1 script" cost below |

### Couplings the audit's stated order does **not** name

**1. D2's four switches are not four of a kind.** The audit says "fetch to the existing `/quick/*` routes". Only **two** exist: `QUICK_DISPLAY_ROUTE = "/quick/display"` and `QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"` (`companion/app.py:238-239`, handled at `:3132-3179`). The LED toggle is `screens.GROUP_LED`, and notifications is `screens.GROUP_NOTIFICATIONS` — both are **Advanced settings-form groups** (`companion/screens.py:65`) saved through `POST /settings` and governed by the dirty-state save bar. Turning them into optimistic instant-apply switches means: two new quick routes, **and** either removing them from the form (reopening Phase 22's X1/D-04 "one control per setting") or leaving two controls for one setting (the exact defect X1 existed to fix).

**2. Absent-field semantics differ per field, and D2 can trip on it.** Phase 22 changed `display_enabled`/`quiet_hours_enabled` to resolve absent → `None` (leave unchanged), but **`led_enabled` and the two notification checkboxes still resolve absent → `False`** — deliberately, because their checkboxes are still rendered (`companion/pages/config_page.py:3926-3958`, `:4236`). The docstring at `:3939-3947` describes the severe regression this asymmetry exists to prevent. A `fetch`-based LED switch must therefore be its own `/quick/led` route passing `led_enabled=` explicitly to `save_device_config()` — **never** a partial `POST /settings`, which would silently switch off whatever the partial body omitted within the same scope.

**3. D1 needs a swap-region convention that does not exist.** `freshness.js` is gated on `[data-loaded-at]` (`:210-214`) and swaps exactly `health_page.REFRESH_SWAP_SELECTORS` (`health_page.py:438-444`). Extending to two more pages means either three pinned tuples or one generic attribute. The audit says "reuse `freshness.js`" and stops there.

**4. D1 races D2.** If Home refreshes every 30 s and a switch is optimistic with a 300 ms spinner, a swap landing between the optimistic flip and the server's confirmation will paint the old state back. `freshness.js` already has the precedent for the guard — `userIsInteracting()` — which currently covers form fields, `<summary>` and sparkline hit targets. It must gain a "a switch has an unconfirmed optimistic state" clause. **The audit orders D9 → D1, D2 and does not name this.**

**5. D3 and D10 are ordered wrong.** See Risk 3.

**6. D5 is the single largest threat to the `:has()` block count.** `.theme-chip`'s entire selected-state — border, inset ring, 12 %-accent wash, check glyph, hover restore, and the dashed no-`:has()` "Current" marker — lives inside the one `@supports selector(:has(*))` block at `style.css:2359`, with specificity arithmetic explicitly marked "verified, not to be re-derived" (`:2323-2345`). A carousel that needs its own live selected state is one careless `@supports` away from failing `test_config_page.py:4002` **and** `:4232`.

**7. D6's third clause already shipped.** "bottom tab bar (X9)" landed in Phase 22 plan 22-14 (`.planning/ROADMAP.md:1060`; `layout.py`'s `_tab_bar_html()`). D6 reduces to manifest + `theme-color`.

**8. D22 is ~80 % already shipped.** T13 (22-15) landed the retry ladder, the in-flight guard, and the neutral `.dot--off` "Paused"/"Reconnecting…" badge — the exact "replaces T13's silent stop" D22 asks for (`freshness.js:124-160`, `:189-205`). D22's genuinely new content is the pulse and the ticking age, and the ticking age **is D14**.

**9. D7's "sticky day headers" reverses a Phase 22 decision.** T4 removed the false sticky-table-header claim outright ("either stick or stop claiming to" → it stopped claiming). Re-adding sticky needs a stated argument, not a silent re-add.

**10. D17 claims to fix an already-fixed defect.** "fixes B14" — B14 (showing the normalised 24 h value beside the native time fields) landed in 22-10 (`.planning/REQUIREMENTS.md:152`). D17 must preserve it, not re-derive it.

**11. D20's premise is not supported by the data.** `device_health` stores observed check-ins only (`ts`, `battery_mv`, `fw_version`, `boot_reason`, `rssi` — `history_db.py:124-133`), fed by tailing the Caddy access log. A "honoured-wake **rate**" needs the *expected* interval at each past moment; `wake_interval_s`, `quiet_hours_*` and `display_enabled` are stored as **current** config only, with no history. The honest, buildable version is a **check-in density** grid ("how many check-ins landed in this hour"), read against *today's* quiet-hours window as a visual overlay. Saying "honoured-wake rate" would be the same class of dishonest-state defect Phase 22's X2/B2/B3 existed to remove.

**12. D18 and D8 need the same new arithmetic.** Neither a battery-life estimator nor a 14-day slope exists. `companion/battery.py` is 38 lines and contains only `battery_percent()`; `history_db.daily_battery_averages()` (`:292`) provides the daily series. Whichever of D8/D18/D21 lands first should own the estimator; the other two consume it. The audit treats them as three unrelated items.

**13. Every new script costs the same three things.** (a) The twelve-script check at `test_companion_app.py:4165-4169` must be retargeted in place with a stated reason; (b) `test_i18n.py` Check 6 demands a French catalogue entry for every `var ALL_CAPS = "literal"` and `|| "literal"` in it (`test_i18n.py:31-37`); (c) a served-route check plus the ES5/forbidden-sink guard, following the existing per-file pattern. **By my count D14, D2, D12, D15, D23 and probably D16/D17/D18 each want a script — six to eight new files against a shell that currently carries twelve.**

**14. A documentation drift worth fixing in passing.** `test_companion_app.py:4177-4179` says "the app has THIRTEEN static scripts as of 22-15". There are **fourteen** `.js` files in `companion/static/` — the comment omits `battery-trend.js`, which `health_page.py:2626` emits inside Health's body rather than from the shell. The *assertion* is correct (a shell renders 12); only the prose is off by one.

---

## Conflicts with locked decisions and recorded rejections

This is the class of error the phase brief asked me to hunt for. I found **one direct conflict**, one near-miss, and three "already-done / already-decided" items.

### CONFLICT — D3's "mobile nav as an overlay drawer"

D3's fifth clause reads: *"mobile nav as an overlay drawer"*.

This contradicts, simultaneously:

1. **A locked Phase 22 developer decision.** `22-CONTEXT.md:137-141`, D-10: *"Do not implement an overlay drawer. If a plan finds bottom tabs unworkable for a reason this context does not anticipate, it must say so and stop rather than fall back to the rejected pattern."*
2. **Three separate recorded rejections in the design system.** `references/mobile-navigation.md:122-124`: full-screen overlay (rejected), slide-in drawer with dimming backdrop (rejected — "adds more moving parts… than the header-dropdown needs"), and `position: absolute` on `.mobile-nav` (*"a recorded real defect (SUPERSEDED), not a viable alternative — it can only overlay, never push"*, established by **real-device testing** during 06.6.1-06).
3. **An explicit warning that this exact mistake has already happened once.** `references/mobile-navigation.md:126`: *"X9 rewrote this app's entire sub-960px navigation, which is exactly the kind of work that reopens an old rejection by accident — the phase's own audit had already produced one row proposing a pattern this file had rejected… All three entries above stay rejected on their original grounds, including the real-device history behind the third. If a future phase wants any of them back, it needs a new argument and a new decision — not a silent rewrite of these three lines."*

**It is also aimed at a component that no longer holds that role.** Phase 22's 22-14 shipped a bottom tab bar as the sub-960 px destination nav and **reduced `.mobile-nav` to a preferences panel** (language, theme, Sign out). There is no longer a "mobile nav" of the kind D3's clause imagines.

**Recommendation: strike the overlay-drawer clause from D3 before planning.** The rest of D3 (save-bar slide-in with animated count, Saving…/Saved ✓ states, chip selection scale + wash fade, preview crossfade, `0fr → 1fr` detail-row animation, rotating chevron, `<dialog>` fade/zoom via `@starting-style`, skeletons at final size) is uncontroversial and lands cleanly.

*The audit produced this row on 2026-09-12 and the developer validated the whole D-table in one action — the same validation mechanism that produced the Phase 22 overlay-drawer row D-10 had to strike. A blanket validation is not a per-row decision.*

### NEAR-MISS — D3's "rotating chevron"

`references/control-density.md:78` already anticipates this and pre-approves it: *"The glyph rotation takes no transition of its own. A rotating-chevron transition is D3 / Phase 23's motion budget; the global `prefers-reduced-motion` block already covers a plain `transform` for free, and a per-rule block here would be dead code, not a safety net."* — so the chevron transition is expected, and must **not** carry its own reduced-motion block. Phase 22's T3 also notes "the reduced-motion block count unchanged at two", implying that count is watched.

### ALREADY DONE — D6's tab bar, D17's B14 fix, D22's reconnecting state

See couplings 7, 10 and 8. Each of these must be **re-scoped**, not re-implemented, or a plan will re-derive shipped work and risk regressing it.

### ALREADY DECIDED AGAINST — D11's hashed filenames

`22-CONTEXT.md:129-131`, D-08/T16: the debt items (gzip, hashed filenames, muted-text token, dead selectors, a shared `ui.js`) are *"**optional** for this phase: take them only where a plan already touches that code. **Do not open a stylesheet-wide refactor.**"* That was Phase 22's scoping; it is not binding on Phase 23. But the reason hashed filenames should still be dropped is independent: they imply a build step, which the Phase 23 constraint forbids outright.

---

## Motion budget (D3) — the concrete baseline

The phase brief asks what a motion budget means "concretely against the design system's existing entries", and whether `prefers-reduced-motion` is already honoured anywhere. Measured facts:

| Measure | Value | Source |
|---|---|---|
| `transition:` declarations in the whole stylesheet | **15** | `grep -c "transition:" companion/static/style.css` |
| `@keyframes` rules | **0** | `grep -n "@keyframes" …` returns nothing |
| `animation:` declarations | **0** | same |
| `@media (prefers-reduced-motion: reduce)` blocks | **2** | `style.css:311-317` (global `*` override) and `:763-767` (`.js .mobile-nav`'s `max-height`, which needs `transition: none` rather than a near-zero duration) |

**So: yes, `prefers-reduced-motion` is already honoured, globally and unconditionally, and has been since 06.6.2 (D-19).** `references/accessibility-contrast.md:25` records it as a floor that survived 06.6.4's density pass untouched, and `:90` records the standing rule that a redundant per-rule block is dead code.

**What a motion budget therefore means here, concretely:**

1. **The global block is the budget's enforcement mechanism — do not touch it.** Any new `transition` or `animation` on a real element is covered for free.
2. **`@keyframes` is a genuinely new primitive for this app.** D14's "breathing dot" and D22's "pulsing dot" would be the first two. A single shared `@keyframes skypane-pulse` reused by both is the right shape; two near-identical keyframe blocks is not.
3. **View-transition pseudo-elements are the one gap** and D3 must close it (Risk 3).
4. **`.js .mobile-nav`'s `transition: none` at `:763-767` is the documented precedent** for the one case where `0.01ms` is not good enough (a `max-height` transition still animating at 0.01 ms can strand an intermediate computed value). Any new `max-height`/`grid-template-rows` animation should be checked against the same question, and D3's `0fr → 1fr` detail-row animation is exactly that shape.
5. **State a numeric ceiling.** The design system records no duration token today. D3 should introduce at most two — e.g. `--motion-fast` and `--motion-slow` — and the register in `SKILL.md` should gain a motion row, because "zero new custom properties" has been a stated achievement of Phases 20 and 21 and breaking it needs to be deliberate.

---

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---|---|---|---|
| Page-to-page transition animation | A JS route-interception + FLIP animation layer | `@view-transition { navigation: auto }` (D10) | The browser does the snapshotting; there is no JS, no framework, no fallback branch, and unsupported browsers simply navigate |
| HTTP response compression | `gzip.compress()` + `Accept-Encoding` parsing + `Vary` in `send_bytes()` | `encode zstd gzip` in `deploy/Caddyfile` | Caddy already terminates every production request; content-negotiation edge cases (identity, `q=0`, `*`) are where hand-rolled compression goes wrong |
| Change notification to an open tab | An SSE endpoint plus a server-side change detector plus a polling fallback | The existing `freshness.js` loop, extended | It already has the retry ladder, in-flight guard, visibility gate and focus-preserving targeted swaps that any new loop would have to re-earn |
| Relative-time formatting on the client | A second date-formatting implementation in the new D14 script | The `data-*`-attribute-with-English-fallback idiom, with the server formatting via `layout.local_clock_text()` / `concise_timestamp_html()` | Phase 22's CFG-28 made Paris local time exhaustive and cost four surfaces to find; a client-side formatter is a fifth path waiting to drift. `panel-lookup.js` is pinned **free of every date API** for exactly this reason |
| Image cropping / normalisation (D19) | A canvas crop that "matches `illustration_normalize.py`" | Server-side `illustration_normalize.py` as the sole authority; canvas for **preview only** | Two implementations of one contract drift; and a client-trusted crop is an upload-validation bypass |
| Optimistic UI state machine (D2) | A generic store/reducer | Per-control: a pending class, a `fetch`, a rollback in `.catch`, a toast | Two switches. A state library for two switches is the framework this project exists without |
| A command palette's fuzzy search (D23) | A ranking/scoring library | `String.prototype.indexOf` over a server-rendered index | ES5 subset is mandatory; ~300 lines is the audit's own estimate and it is right |

**Key insight:** on this codebase, "don't hand-roll" almost always resolves to *"use something the repo already built and pinned"* rather than *"add a library"* — because adding a library is forbidden. The expensive mistake here is not reaching for npm; it is **building a second mechanism beside an existing one** and letting the two drift. Every one of the fourteen scripts has a header paragraph explaining which earlier decision it superseded and why; that is the house style, and it exists because this failure mode has happened repeatedly.

---

## Runtime State Inventory

Not a rename phase — but **D12 introduces persistent, self-updating state outside the repository**, which is the same class of problem this section exists to catch. Included for that item alone.

| Category | Items | Action required |
|---|---|---|
| Stored data | **If D12 ships:** a `CacheStorage` bucket per origin, per browser profile, holding whatever the worker precached. Verified this session: it will store `Cache-Control: no-store` bodies. | Explicit cache-name versioning; a self-destructing worker that iterates `caches.keys()` and deletes |
| Live service config | `deploy/Caddyfile` is in git and deployed by `deploy/provision.sh`. D11's gzip would edit it. **No** Caddy config lives outside git. | If gzip goes in the Caddyfile, it ships via the normal deploy; note it in the plan so a redeploy is not forgotten |
| OS-registered state | **If D12 ships:** a service-worker **registration** in every browser profile that ever loaded the site, which outlives the file and cannot be removed server-side. | Ship the self-destructor in the same phase; test it in the harness |
| Secrets / env vars | None affected. `SKYPANE_COMPANION_PORT`, `SKYPANE_SLEEP_S` etc. unchanged by any D-item | None |
| Build artifacts | **None — verified.** There is no build step, no bundler, no `node_modules`, no generated asset. `server/.venv` is the only installed artifact and no D-item changes its contents | None |
| Browser-held state (new category) | `localStorage`/`sessionStorage`: **none used today** — grep of `companion/static/*.js` finds no storage API. D23's palette and D24's first-run checklist would be the first tempted to use it | If any item adds client storage, it must be stated: it is a second source of truth beside the server, and this app's whole discipline is server-authoritative state |

---

## Common Pitfalls

### Pitfall 1: adding a script without paying its three taxes
**What goes wrong:** a new `companion/static/*.js` lands and three unrelated harnesses go red at once.
**Why:** the twelve-script assertion (`test_companion_app.py:4165-4169`), the i18n fallback-literal scan (`test_i18n.py` Check 6), and the per-file ES5/forbidden-sink guard are three independent pins on the same act.
**How to avoid:** treat "+1 script" as a planned, three-part change: retarget the count check **in place** with a stated reason (the file's own comment shows the format used eleven times already), add the French catalogue entries, add the served-route + banned-token check.
**Warning sign:** a plan that says "add a small script" without naming `EXPECTED_CHECK_COUNT`.

### Pitfall 2: assuming `prefers-reduced-motion` covers everything
**What goes wrong:** reduced-motion users get full-page cross-fades from D10, or a stranded `max-height` from a 0.01 ms transition.
**Why:** `*, *::before, *::after` does not match view-transition pseudo-elements, and a near-zero duration is not the same as `none`.
**How to avoid:** wrap `@view-transition` in `@media (prefers-reduced-motion: no-preference)`; follow `.js .mobile-nav`'s `transition: none` precedent (`style.css:763-767`) for any new size-interpolating transition.
**Warning sign:** a plan that says "the global block covers it" about anything that is not a plain colour/border/shadow/transform transition on a real element.

### Pitfall 3: an enhancement that renders but does nothing without script
**What goes wrong:** exactly what Phase 22 found — a control that renders with scripts blocked and silently does nothing. The audit notes only the browser harness could catch it.
**Why:** the no-JS floor is a *behavioural* contract, and every string-comparison harness is blind to it.
**How to avoid:** for every new control (D2, D16, D17, D18, D19, D23), the no-JS path must be the **submitting** path — a hidden synced native input that the form actually posts (D17 already specifies this correctly), or a plain `<form>` the script progressively upgrades. Every one needs a `context.new_page(java_script_enabled=False)` check in `test_browser_ux.py`, following the three that exist (`:930`, `:1377`, `:1584`).
**Warning sign:** a control whose only writer is `fetch`.

### Pitfall 4: re-deriving arithmetic that has one definition site
**What goes wrong:** two "next wake" figures, two battery estimates, two time formats.
**Why:** this has happened repeatedly — Phase 22's X2 exists because the strip and the tiles disagreed; CFG-28 exists because four surfaces never got converted to Paris time; the `concise_timestamp_html()` docstring promised a format it had not emitted for two phases and the battery code copied the stale doc.
**How to avoid:** `server/wake.py` owns next-wake; `companion/battery.py` should own the new life-estimator for D8/D18/D21; `layout.local_clock_text()` owns visible times. Import, never re-derive.
**Warning sign:** a second function computing days-remaining.

### Pitfall 5: an optimistic switch that lies
**What goes wrong:** the switch flips, the POST fails (or a refresh swap lands first), and the UI shows a state the frame is not in.
**Why:** the whole Phase 22 X2/B2/B3 arc was about the companion never reporting a state dishonestly.
**How to avoid:** rollback on `!response.ok` **and** on network error; a toast that names the failure; and the refresh loop must not swap a region holding an unconfirmed switch. Also: `/quick/*` currently returns a **303 redirect** with a `?flash=` query (`app.py:3178`), not JSON/204 — `fetch` follows redirects by default, so the handler needs a content-negotiated branch (or `redirect: "manual"` on the client) and the no-JS form path must keep its redirect exactly.
**Warning sign:** a `fetch(...).then(() => setOn(true))` with no `.catch`.

### Pitfall 6: opening a second `@supports selector(:has(*))` block
**What goes wrong:** two checks fail, and the specificity arithmetic documented at `style.css:2323-2345` has to be re-derived.
**Why:** an unsupported `:has()` invalidates the whole selector list it appears in, which is why every live-state rule is quarantined in one feature query.
**How to avoid:** add rules **inside** the existing block at `style.css:2359`. If a new selectable surface needs live state, it joins the four already there.
**Warning sign:** any diff introducing the literal `@supports selector(:has(*)) {`.

### Pitfall 7: treating a blanket validation as a per-row decision
**What goes wrong:** an item that contradicts an existing locked decision ships because "the developer validated the whole table".
**Why:** this already happened once — Phase 22's audit proposed an overlay drawer that the design system had rejected on real-device evidence, and only the research caught it (`22-CONTEXT.md:137-141`).
**How to avoid:** for each D-item, grep the design system and prior CONTEXT files for the pattern name before planning it. D3's overlay drawer is this phase's instance.
**Warning sign:** "the developer validated D1–D24" used as the justification for a mechanism.

---

## Code Examples

### D10 — the whole feature, verified to parse in Chromium 151

```css
/* companion/static/style.css — near the existing reduced-motion block (:311).
 * Spec: CSS View Transitions 2 §8.3.1 permits nesting in a conditional group rule.
 * Verified parsing + retained in the CSSOM, Chromium 151.0.7922.34, this session. */
@media (prefers-reduced-motion: no-preference) {
  @view-transition { navigation: auto; }
}

/* Names must be unique per document. layout.py renders THREE nav copies
 * simultaneously (sidebar / mobile-nav / tab-bar, layout.py:1905-1920),
 * so target the sidebar specifically — never a shared nav class. */
.dashboard-sidebar { view-transition-name: skypane-sidebar; }
.page-header__title { view-transition-name: skypane-title; }
.preview-frame img  { view-transition-name: skypane-picture; }
```

### D2 — a quick switch that respects every existing contract

```javascript
/* ES5 subset: no let/const, no arrows, no template literals, no backticks.
 * Guard clause first, per companion/layout.py's "served everywhere" convention. */
(function () {
  "use strict";
  var switches = document.querySelectorAll("[data-quick-switch]");
  if (!switches.length) { return; }          // no-op on every other page

  function flip(el, form) {
    var wanted = el.getAttribute("aria-checked") === "true" ? "off" : "on";
    el.setAttribute("aria-checked", wanted === "on" ? "true" : "false");
    el.setAttribute("data-pending", "1");    // freshness.js must skip this region
    var body = new URLSearchParams(new FormData(form));
    body.set("state", wanted);
    fetch(form.getAttribute("action"), {
      method: "POST",
      credentials: "same-origin",            // SameSite=Strict is the CSRF control
      redirect: "manual",                    // /quick/* answers 303, app.py:3178
      headers: {"Content-Type": "application/x-www-form-urlencoded"},
      body: body.toString()
    }).then(function (r) {
      if (r.type !== "opaqueredirect" && !r.ok) { throw new Error("save failed"); }
      el.removeAttribute("data-pending");
    })["catch"](function () {                 // bracket form: `catch` is reserved in ES3
      el.setAttribute("aria-checked", wanted === "on" ? "false" : "true");
      el.removeAttribute("data-pending");
      // toast: read the translated string from a data-* attribute, never a literal
    });
  }
})();
```
**The no-JS floor:** the `<form>` these upgrade already exists and already works — `layout.frame_strip_html()` (`layout.py:2221`) renders a real form per switch with a `return_to` hidden field validated against `{HOME_ROUTE, DISPLAY_ROUTE}` in `_handle_quick_toggle()` (`app.py:3161-3164`). The script must **not** remove or replace it.

### The absent-field contract D2 must not break

```python
# Source: companion/pages/config_page.py:3954-3958 (docstring, verbatim)
#   So, for all three checkboxes: `led_enabled`
#   resolves absent -> `False`, equal to `LED_CHECKBOX_VALUE` -> `True`,
#   anything else -> reject; `display_enabled`/`quiet_hours_enabled`
#   resolve absent -> `None` (unchanged), equal to their own
#   `*_CHECKBOX_VALUE` -> `True`, anything else -> reject.
```
A new `/quick/led` route must call `device_config.save_device_config(state_dir, led_enabled=<bool>)` directly — the same shape `_handle_quick_toggle()` uses (`app.py:3172-3176`) — never a partial `POST /settings`.

### The bounded SSE handler, if D9 is taken anyway

```python
# companion/app.py — module level, same shape as _POLL_LOCK (app.py:642).
MAX_EVENT_STREAMS = 4
EVENT_HEARTBEAT_S = 15          # must stay < REQUEST_SOCKET_TIMEOUT_S (30, app.py:113)
EVENT_STREAM_MAX_LIFETIME_S = 600
_STREAM_LOCK = threading.Lock()
_stream_count = 0

    def _handle_events(self):
        if not self.require_session():
            return None
        global _stream_count
        with _STREAM_LOCK:
            if _stream_count >= MAX_EVENT_STREAMS:
                self.send_response(503)
                self.send_header("Retry-After", "30")   # client falls back to polling
                self.send_header("Content-Length", "0")
                self._send_hardening_headers()
                return self.end_headers()
            _stream_count += 1
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")  # Caddy auto-flushes
            self.send_header("Cache-Control", "no-store")
            self._send_hardening_headers()
            self.end_headers()
            deadline = time.time() + EVENT_STREAM_MAX_LIFETIME_S
            while time.time() < deadline:
                self.wfile.write(b": ping\n\n")   # wbufsize == 0: unbuffered, no flush needed
                time.sleep(EVENT_HEARTBEAT_S)
        except (OSError, socket.timeout):
            pass                                   # client went away; thread is freed
        finally:
            with _STREAM_LOCK:
                _stream_count -= 1
```
Note `BaseHTTPRequestHandler.wbufsize == 0` (verified by introspection this session), so `wfile.write` goes straight to the socket — no explicit flush is needed, unlike most SSE examples written for buffered frameworks.

---

## State of the Art

| Old approach | Current approach | When it changed | What it means here |
|---|---|---|---|
| JS-driven page transitions (FLIP, route interception, a framework's `<Transition>`) | `@view-transition { navigation: auto }` — zero JS, browser-native, MPA-native | Chrome 126 (2024-06), Safari 18.2 (2024-12); still no Firefox | D10 is the reason a build-free MPA can now feel like an SPA. This is genuinely new since this project started. |
| `height: auto` animation hacks (max-height guesses, JS measurement) | `grid-template-rows: 0fr → 1fr`; `interpolate-size: allow-keywords` where available | `0fr → 1fr` widely usable; `interpolate-size` **Chromium-only, Baseline limited** | D3's audit text already picks the right one. Do not reach for `interpolate-size`. |
| `display: none` → visible with a JS class dance for dialogs | `@starting-style` + `transition-behavior: allow-discrete` | Baseline newly, 2024-08-06 (Chrome 117, Firefox 129, Safari 17.5) | D3's `<dialog>` fade/zoom is now a pure-CSS enhancement on the two `<dialog>`s that already exist (`history_page.py:589`, `airlines_page.py:1430`) |
| SSE / long-polling for "live" pages | Still SSE where a real push source exists; **plain polling where the source is itself a poll** | — | This project's source **is** a 30 s systemd timer. Polling the poller over SSE adds a layer and buys nothing. |
| Service workers as a default PWA ingredient | Still standard — but the "one-way door" cost is now well understood, and self-destructing workers are the documented retirement pattern | — | Treat D12 as a decision, not a checkbox |

**Deprecated / outdated in this context:**
- **`AppCache`** — long removed; irrelevant, but worth stating so nobody reaches for it.
- **`navigator.share()` on desktop Firefox** — not implemented and no signal it will be. D15 is a phone-only feature; the audit's "PNG download elsewhere" fallback is correct and load-bearing, not an afterthought.
- **`Cache-Control: immutable` + hashed filenames** as a default best practice — still correct in general, still wrong *here*, because it presupposes a build step.

---

## Scope: one phase or several — my honest read

**This is not one phase. I would split it into four.**

### The evidence

| Signal | Value |
|---|---|
| Phase 22's input | 49 findings, described by its own context as "mostly small", explicitly a "correction pass where every item is individually verifiable" |
| Phase 22's output | **16 plans across 12 waves** (`.planning/ROADMAP.md:1044-1062`) |
| Phase 23's input | **24 features**, five of which the audit itself scopes **L** ("a redesign across pages"), two of which are architectural (D9, D12) |
| New scripts implied | **6–8** against a shell that carries 12 today |
| New CSS implied | a motion system with the app's first `@keyframes`, an SVG runway map, a 24 h dial, a 168-cell grid, a carousel, a timeline, a ring gauge — against a stylesheet already at 7,698 lines |
| Per-feature fixed cost | each visible control needs: a no-JS fallback, a French catalogue entry, a touch-target register entry, a browser-harness check at 360 px, and a design-system update in step |

Phase 22 turned 49 *small* items into 16 plans. Phase 23's 24 items are *not* small — nine of them are new components and two are page redesigns. A straightforward per-item estimate lands near **30 plans**, roughly double the largest phase this project has ever run, and Phase 22 is already an outlier (the previous largest was Phase 21 at 8).

There is a second argument that does not depend on counting. **Three of the twenty-four items are decisions, not tasks** — D9 (mechanism), D12 (a one-way door), and D3's overlay-drawer clause (a conflict). Those belong in a `discuss-phase` conversation, and a phase that bundles three open decisions with twenty-one implementation items will either stall on the decisions or ship them by default.

### The seams

I looked for seams where the *contract surface* changes, not just where the features group nicely.

**Phase 23 — "Alive": the whole site starts moving.**
D3 (minus the overlay clause) → D10 → D14 → D1 → D22 (re-scoped) → D2 (narrowed) → D7 → D11 (gzip + prefetch only).
*Why this is a seam:* every item here modifies **existing** pages and existing scripts. Nothing new is drawn. The deliverables are one motion vocabulary, one refresh convention, and one optimistic-switch pattern — three reusable things the next three phases consume. It also contains the D9 decision, which must be settled before D1 can be planned.
*Ships on its own:* yes. The site feels different the day it lands, which is the stated goal of the phase.

**Phase 24 — "Drawn": data already in the database becomes visible.**
D21 → D8 → D13 → D20 (re-scoped to check-in density) → D4 (the Home hero that consumes D13 and D21).
*Why this is a seam:* every item is server-rendered SVG from `history.db`, following the `battery-trend.js` pattern exactly. They share one new dependency — the battery-life estimator — and one new skill: drawing in Python. D4 is last because it is the page that composes the other four.
*Risk it isolates:* D20's premise is unsupported by the schema. Better to discover that inside a phase scoped to drawing than inside a phase also shipping a service worker.

**Phase 25 — "Controls": bare fields become purpose-built controls.**
D16 → D17 → D18 → D5 → D19.
*Why this is a seam:* every one of these is a **new interactive control with a no-JS fallback and a touch-target obligation at 360 px**. They share one hard problem (drag/swipe targets that must also work by keyboard and by form submission) and one shared risk (the single `:has()` block). Grouping them means solving the no-JS-control pattern once.
*This is the phase most likely to need its own UI spec*, as Phase 22 had.

**Phase 26 — "App": the finishes and the one-way door.**
D6 (manifest only) → D23 → D24 → D15 → **D12 last, behind an explicit decision**.
*Why this is a seam:* these are the items with the weakest dependency on anything else, the ones most likely to be descoped, and the one item that changes browser state permanently. Putting D12 last means it ships onto a site whose shape has stopped moving — which is exactly when a precache manifest is least likely to go stale.

### If the developer wants fewer boundaries

The **minimum defensible split is two**: "Alive" (the eight items above) and "Everything else". The single seam that matters most is between *changing how existing pages behave* and *building new components* — those are different kinds of work with different failure modes, different test shapes, and different design-system consequences. Merging 24/25/26 back together recreates a 20-plan phase, which is large but not unprecedented.

### What I would not do

Do not ship this as one phase and let the wave structure absorb it. Phase 22's twelve waves were possible because its items were *independent small fixes*. Phase 23's items are dependent, and several are redesigns of the same three pages (Home, Display, Health) — so waves would serialise rather than parallelise, and a single blocked decision (D9, D12) would stall everything downstream of it.

**This judgement is the developer's to make. The evidence above is what I would want to make it on.**

---

## Environment Availability

| Dependency | Required by | Available | Version | Fallback |
|---|---|---|---|---|
| Python 3 (repo venv) | Everything | ✓ | 3.11.15 | — |
| `playwright` | The browser harness for every no-JS and interaction check | ✓ | 1.62.0 (`server/requirements-dev.txt`) | Harness skips with a printed `SKIP`, never fails (`test_browser_ux.py:24-31`) |
| Chromium (playwright) | Same | ✓ | **151.0.7922.34** | Same skip gate |
| `gzip` / `zlib` (stdlib) | D11 if compression is done in Python | ✓ | stdlib | Caddy `encode` (preferred) |
| Caddy | D11 if compression is done at the proxy | ✗ **locally** | — deployed on the VPS only | Do compression in Python, or accept that it is production-only and untestable locally |
| `sqlite3` (stdlib) | D8, D13, D20, D21 read `history.db` | ✓ | stdlib | — |
| Network egress for CDN assets | *(nothing needs it — no external dependency is permitted)* | n/a | — | — |

**Missing with no fallback:** none.

**Missing with fallback:** Caddy is not installed in this environment. **This directly affects D11.** If gzip goes into the Caddyfile, no harness in this repo can verify it, and the only proof is a manual `curl -H 'Accept-Encoding: gzip'` against the deployed host. If that is unacceptable, gzip must go into `send_bytes()` in Python, where it is testable — at the cost of hand-rolling content negotiation. **State the choice in `23-CONTEXT.md`; do not let a plan pick silently.**

**Also worth stating:** `navigator.share` is `undefined` in the harness Chromium (verified). **D15 has no machine verification path in this repository at all** and is manual-only on a real phone.

---

## Validation Architecture

### Test framework

| Property | Value |
|---|---|
| Framework | The project's own stdlib harness idiom — `check(name, fn)` + a module-level `EXPECTED_CHECK_COUNT` + `main()` returning 0/1. **No pytest anywhere.** |
| Config file | `scripts/run_all_tests.py` (`HARNESSES` list at `:62-90`); `scripts/run-all-tests.sh` is a thin wrapper owning the `PYTHON` contract |
| Quick run (one harness) | `server/.venv/bin/python3 companion/test_<name>.py` |
| Full suite | `scripts/run-all-tests.sh` (parallel; `JOBS=1` for serial; `HARNESS_TIMEOUT_S` default 600) |
| Browser harness | `server/.venv/bin/python3 companion/test_browser_ux.py` — listed in `EXPECTED_SLOWEST` (`run_all_tests.py:105`) and submitted first for scheduling |

### Current pinned counts (the surface Phase 23 will move)

| Harness | `check()` calls on disk | `EXPECTED_CHECK_COUNT` |
|---|---|---|
| `companion/test_browser_ux.py` | 26 | **26** |
| `companion/test_companion_app.py` | 254 | 272 |
| `companion/test_config_page.py` | 233 | 233 |
| `companion/test_status_pages.py` | 268 | 268 |
| `companion/test_view_pages.py` | 143 | 143 |
| `companion/test_i18n.py` | 19 | 24 |
| `companion/test_contrast_check.py` | 12 | 43 |

*(The `check()`-call vs `EXPECTED_CHECK_COUNT` gap in three files is because some checks are registered inside loops or nested scopes. The harness asserts `passed == total and total == EXPECTED_CHECK_COUNT` at `test_browser_ux.py:2875` — the count is authoritative, the grep is not.)*

### Phase requirements → test map (to be completed at planning; the shape each D-item needs)

| Item | Behaviour | Test type | Automated command | Exists? |
|---|---|---|---|---|
| D10 | `@view-transition` present, wrapped in `prefers-reduced-motion: no-preference`; `view-transition-name` unique per rendered document | unit (stylesheet source scan + rendered-doc scan) | `… companion/test_companion_app.py` | ❌ Wave 0 |
| D3 | The stylesheet's `@media (prefers-reduced-motion: reduce)` block count moves only where a plan forces it; every new `@keyframes` has one definition | unit | `… companion/test_companion_app.py` | ❌ Wave 0 |
| D14 | A `<time data-relative>` text updates within 2 s in a real tab; stops updating when the tab is hidden | **browser** | `… companion/test_browser_ux.py` | ❌ Wave 0 |
| D2 | Switch flips optimistically; on a forced 500 it rolls back and announces; **with scripts blocked the form still posts and persists** | **browser** (both JS on and `java_script_enabled=False`) | `… companion/test_browser_ux.py` | ❌ Wave 0 |
| D2 | Saving an unrelated setting does not alter `led_enabled` / notifications (the D-12.1 asymmetry) | unit | `… companion/test_config_page.py` | ✅ analogous check exists for display/quiet-hours (22-05) — **extend, do not duplicate** |
| D1 | Home swaps its tiles without losing focus or an open disclosure; a background tab issues zero requests | **browser** | `… companion/test_browser_ux.py` | ❌ Wave 0 |
| D12 (if taken) | Worker installs; the self-destructor unregisters it **and** empties `caches.keys()`; no session-gated URL is ever in the cache | **browser** | `… companion/test_browser_ux.py` | ❌ Wave 0 — *verified possible: `http://127.0.0.1` is a secure context* |
| D16/D17/D18/D19 | Each control is operable by keyboard; hit areas ≥ 44 px at 360 px; **the hidden native input is what the form posts** | **browser** | `… companion/test_browser_ux.py` | ❌ Wave 0 |
| D20 | The grid's cell count and labelling match the queried rows; the copy does not claim a rate the data cannot support | unit | `… companion/test_status_pages.py` | ❌ Wave 0 |
| every new script | served route returns 200; body free of `innerHTML`/`document.write`/`=>`/` let `/` const `/backtick | unit | `… companion/test_companion_app.py` | ✅ pattern exists (`:4130-4152`) — copy it |
| every new user-facing string | has a French catalogue entry | unit | `… companion/test_i18n.py` | ✅ Check 6 exists — it will fail until the entry lands |

### Sampling rate

- **Per task commit:** the one or two harnesses the task touched, e.g. `server/.venv/bin/python3 companion/test_config_page.py` (each is under ~10 s except the browser harness).
- **Per wave merge:** `scripts/run-all-tests.sh` (full parallel suite).
- **Phase gate:** full suite green, including `companion/test_browser_ux.py` **not** skipping — a `SKIP` line means the interaction contracts were never checked, and this phase is almost entirely interaction.

### Wave 0 gaps

- [ ] A **reduced-motion assertion helper** — the phase adds motion in many plans; one shared check that scans the stylesheet for animated properties outside the covered set is cheaper than N per-rule checks.
- [ ] A **no-JS control helper** in `test_browser_ux.py` — `context.new_page(java_script_enabled=False)` then "render the control, submit the form, assert persistence". Three such checks exist (`:930`, `:1377`, `:1584`) but are hand-written per page. D16/D17/D18/D19/D2 each need one; factor it once.
- [ ] A **360 px viewport helper** — the design system's floor moved to 360 px on 2026-09-13 and the existing assertions are a mix of 320/390.
- [ ] **No framework install needed.** The harness idiom and Playwright are both already in place.

---

## Security Domain

`security_enforcement: true`, `security_asvs_level: 1` (`.planning/config.json`).

### Applicable ASVS categories

| ASVS category | Applies | Standard control in this codebase |
|---|---|---|
| V2 Authentication | yes | `companion/auth.py` — session cookie, `LoginThrottle`, revocation list; **unchanged by this phase**. Any new route must call `require_session()`. |
| V3 Session Management | **yes, and at risk** | `HttpOnly; Secure; SameSite=Strict; Path=/` (`auth.py:270`) + `Cache-Control: no-store` on every HTML response (`app.py:1200`). **D12 defeats the second half — verified this session.** |
| V4 Access Control | yes | Every state-changing route gated in `do_POST()` (`app.py:3213-3250`). A new `/events`, `/quick/led`, `/quick/notifications` or `/manifest.webmanifest` route each needs an explicit gate decision — manifest is fine pre-auth (it names no user data); `/events` is **not**. |
| V5 Input Validation | yes | Whitelist-membership + exact-equality gates in `config_page.handle_post()` and `_handle_quick_toggle()`. D19's client crop must not become a trusted input — `illustration_normalize.py` stays the authority. |
| V6 Cryptography | no change | `auth.py` owns it; nothing in D1–D24 touches it |
| V7 Error Handling / Logging | yes | D2's toasts and D22's reconnecting state must not surface server internals; follow the existing generic "save failed" flash (`FLASH_KEY_QUICK_FAILED`) |
| V12 File Upload | yes (D19) | `MAX_ILLUSTRATION_UPLOAD_BYTES = 4 MB` (`app.py:104`), `parse_single_uploaded_file()` discards the client-declared filename entirely (`app.py:1146-1149`). Drag-and-drop changes the *affordance*, not the parser — keep it that way. |
| V14 Configuration | yes | CSP is `default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; form-action 'self'; frame-ancestors 'none'` (`app.py:143-146`), asserted by exact equality at `test_companion_app.py:5236-5257`. **No D-item requires a CSP change** — every new script is a same-origin file, `EventSource` is covered by `connect-src` falling back to `default-src 'self'`, the manifest by `default-src`, and a service worker by `default-src`/`worker-src` fallback. |

### Known threat patterns for this stack

| Pattern | STRIDE | Standard mitigation | Phase 23 exposure |
|---|---|---|---|
| **Authenticated content persisted to disk by a service worker, surviving sign-out** | Information disclosure | Never `cache.put()` a session-gated response; precache only pre-auth static assets | **D12 — verified reachable this session.** The primary security finding of this research. |
| CSRF on a new state-changing route | Spoofing | `SameSite=Strict` session cookie (`auth.py:263`); there is **no CSRF token anywhere** | D2's new quick routes, D23's palette actions. All must be POST with `credentials: 'same-origin'`. **A state change reachable by GET would have no CSRF defence at all.** |
| Unauthenticated telemetry leak via a new endpoint | Information disclosure | `require_session()` before the first byte | **`/events` (D9)** would stream render/check-in/battery events. A `manifest.webmanifest` is safe pre-auth; `/events` is not. |
| Slowloris / held-connection resource exhaustion | Denial of service | `REQUEST_SOCKET_TIMEOUT_S = 30` (`app.py:106-113`) | **D9** deliberately holds connections, which is the pattern that timeout exists to prevent. If taken, the hard cap + heartbeat + max-lifetime in Risk 1 is the mitigation, and it must be a bounded design, not an unbounded one. |
| Open redirect via a new `return_to`-style parameter | Tampering | Whitelist membership, never prefix/URL parsing (`app.py:3161-3164`, T-21-12) | Any new route D2 adds must copy this exact shape |
| XSS via a new DOM sink | Tampering | `innerHTML`/`insertAdjacentHTML`/`document.write`/`eval` banned and pinned per file; `DOMParser` + `importNode` + `replaceChild` is the one sanctioned swap mechanism | Six to eight new scripts. Each needs its own banned-token check. |
| Client-trusted image transform | Tampering | Server normalises unconditionally | **D19.** Canvas crop is a preview; `illustration_normalize.py` remains authoritative. |

### One net-positive security note

D11's gzip is worth a sentence: compressing responses that mix attacker-influenced and secret content over TLS is the BREACH pattern. It does **not** apply here — the compressible responses are `style.css` and the scripts, which are pre-auth, identical for every client, contain no secret, and already carry `public, max-age=300` (`app.py:1854`, `:1883`). Compressing **HTML** would be the questionable one, and the gain there is much smaller because HTML is already `no-store` and not re-fetched from cache. Recommend: compress static assets only.

---

## Assumptions Log

| # | Claim | Section | Risk if wrong |
|---|---|---|---|
| A1 | Manifest installability on Android reliably wants 192/512 PNG icons; an SVG data-URI favicon is not sufficient | D6 dossier row | D6 is cheaper than stated (no new binary assets). Low risk — verify against Chrome's install criteria before planning D6. |
| A2 | `view-transition-name` collisions cause the transition to be dropped silently rather than erroring | Risk 3 caveat | A name collision across the three simultaneous nav renderings goes unnoticed. Mitigate with a one-line harness assertion rather than by research. |
| A3 | Browsers cap ~6 concurrent HTTP/1.1 connections per origin, so a permanent `EventSource` leaves 5 | Risk 1 bounds table | Only matters if D9 is taken **and** the site is reached over HTTP/1.1 (direct-to-8643). Production is HTTP/2 via Caddy, where it does not apply. |
| A4 | My plan-count estimate (~30 plans for all 24 items) | Scope section | The split recommendation is softer than stated. The *structural* arguments (three open decisions; nine new components; three shared pages) do not depend on this number. |
| A5 | Per-connection RSS measured on this Linux container generalises to the CX22 | Risk 1 measurements | Memory is not the binding constraint either way — 200 connections at 5.8 MB is three orders of magnitude below 4 GB. |
| A6 | No current browser unregisters a service worker on a 404 during update | Risk 2 | If some do, retirement is easier than stated — but the self-destructing worker is correct regardless, so the recommendation does not change. |

---

## Open Questions

1. **Is D9 declined, or taken under the bound?**
   - *Known:* SSE is measurably safe on this server; the device poll cannot be starved; the audit's emission mechanism cannot be built; `freshness.js` already does the job better.
   - *Unclear:* whether the developer values sub-30-second latency enough to accept a new long-lived endpoint. My read is no, and D9 is explicitly a suggestion.
   - *Recommendation:* settle it in `discuss-phase`. If declined, say so in `23-CONTEXT.md` **with the reason**, so a future audit does not re-propose it as an unexamined idea.

2. **Is D12 taken at all, and if so with what cache scope?**
   - *Known:* the Cache API stores `no-store` bodies (verified); retirement requires a self-destructing worker; the harness **can** test all of it.
   - *Unclear:* whether an offline shell is worth anything for a device whose whole value is *live* departure information. A stale companion showing "last known state 2 h ago" is arguably the opposite of the product.
   - *Recommendation:* a developer decision, not a planner's.

3. **D11: gzip in Caddy (untestable locally) or in Python (testable, hand-rolled)?**
   - *Recommendation:* Caddy, and accept manual verification — unless the developer wants it pinned, in which case Python.

4. **D20: is a check-in *density* grid acceptable in place of an "honoured-wake rate"?**
   - *Known:* the expected-interval history needed for a rate does not exist in `device_health` or anywhere else.
   - *Options:* (a) ship density and name it honestly; (b) start recording the effective interval alongside each check-in and ship the rate grid a phase later; (c) drop D20.
   - *Recommendation:* (a) now, (b) as a follow-on if the developer wants the rate.

5. **D3's overlay-drawer clause — struck, or argued?**
   - *Recommendation:* struck. If the developer wants it, `references/mobile-navigation.md:126` sets the bar: "a new argument and a new decision". Note that Phase 22 already removed the component it would apply to.

6. **The script budget.** Six to eight new files against twelve. Is there a point at which a shared `ui.js` (T16's own suggestion) becomes the right consolidation, or does the one-file-per-concern convention hold?
   - *Recommendation:* hold the convention for this phase; revisit if the count passes ~18. Consolidation is a refactor, and the phase already has enough architectural weight.

---

## Sources

### Primary (HIGH confidence)

- **The codebase itself**, read directly this session. Every `file:line` in this document was verified at execution time, not recalled: `companion/app.py`, `companion/layout.py`, `companion/screens.py`, `companion/battery.py`, `companion/wake.py`, `companion/prefs.py`, `companion/pages/*.py`, `companion/static/*.js`, `companion/static/style.css`, `companion/test_*.py`, `scripts/run_all_tests.py`, `server/wake.py`, `server/history_db.py`, `server/poll_loop.py`, `server/device_config.py`, `stub-server/byos_server.py`, `stub-server/VENDOR.md`, `deploy/Caddyfile`, `deploy/skypane-*.service`, `deploy/skypane-poll.timer`.
- **Live experiments run this session** (scripts in the session scratchpad):
  - SSE thread/latency/memory measurement on `http.server.ThreadingHTTPServer` at N = 0/5/20/50/200 held connections, with a control run isolating the accept-backlog tail.
  - CPython introspection of `socketserver.ThreadingMixIn`, `socketserver._Threads`, `http.server.ThreadingHTTPServer`, `BaseHTTPRequestHandler.{wbufsize, rbufsize, protocol_version}`.
  - Playwright + Chromium 151.0.7922.34: `@view-transition` nested in `@media (prefers-reduced-motion: no-preference)` parses and is retained; `@starting-style` parses; `document.startViewTransition` present; `navigator.share` undefined; over `http://127.0.0.1` `isSecureContext`/`serviceWorker`/`caches` all available; **`cache.put()` stores a `Cache-Control: no-store` body verbatim.**
- **Web Platform Status API** (`https://api.webstatus.dev/v1/features/…`) — the official Web Platform Dashboard, backed by MDN browser-compat-data — for `view-transitions`, `cross-document-view-transitions`, `starting-style`, `dialog`, `details-content`, `interpolate-size`, `service-workers`, `share`.
- **CSS View Transitions Module Level 2** (`https://drafts.csswg.org/css-view-transitions-2/`) §8.3.1, read directly: *"Note: as per default behavior, the @view-transition rule can be nested inside a conditional group rule such as @media or @supports."*
- **Planning records:** `.planning/phases/22-.../22-AUDIT.md` (the D-table and its dependency order, lines 100-131), `22-CONTEXT.md` (D-01…D-12), `.planning/ROADMAP.md:1041-1072`, `.planning/REQUIREMENTS.md:147-153`, `.planning/config.json`, `.planning/STATE.md`.
- **Design system:** `.claude/skills/sketch-findings-skypane/SKILL.md` and its six reference files, read directly.

### Secondary (MEDIUM confidence)

- Caddy `reverse_proxy` documentation (`https://caddyserver.com/docs/caddyfile/directives/reverse_proxy`) — SSE auto-flush on `Content-Type: text/event-stream`; no default read/write timeout on the HTTP transport.
- MDN `@view-transition` (`https://developer.mozilla.org/en-US/docs/Web/CSS/@view-transition`) — "Limited availability… not Baseline"; unsupported browsers ignore the at-rule.
- MDN `ServiceWorkerRegistration.update()` — the 24-hour browser-cache bypass for the worker script.
- Chrome for Developers, "Cross-document view transitions for multi-page applications" — version support and the same-origin restriction.

### Tertiary (LOW confidence — flagged, not relied on for any recommendation)

- Community writeups on retiring a service worker (Kevin Cox, Benjamin Rancourt, Ankur Sheel, Netlify support guide, `w3c/ServiceWorker#614`). These **agree** that a 404 leaves the registration live and that a self-destructing worker is the retirement pattern, which is why I state it — but no single one is authoritative, and I could not locate the governing clause in the spec text. The recommendation (ship the self-destructor) is safe under either behaviour.

---

## Metadata

**Confidence breakdown:**

| Area | Level | Reason |
|---|---|---|
| Codebase facts and pinned contracts | **HIGH** | Every claim carries a `file:line` read this session; counts (12 scripts, 1 `:has()` block, 15 transitions, 0 keyframes, 26 browser checks, 14 JS files) were computed, not recalled |
| Process topology (the D9 correction) | **HIGH** | Read from four systemd units and the Caddyfile; corroborated by three independent module docstrings that state the separation as a deliberate decision |
| SSE behaviour under load | **HIGH** | Measured at five connection counts with a control run; the ~1 s burst tail was isolated to the accept backlog and shown to be independent of SSE |
| Service-worker `no-store` bypass | **HIGH** | Reproduced in the project's own harness browser against a server sending the app's exact header |
| Service-worker retirement semantics | **MEDIUM** | Multiple agreeing secondary sources; could not locate the governing spec clause. The recommendation is safe under either behaviour. |
| Browser support figures | **HIGH** | Authoritative Web Platform Status API, plus in-browser verification for the three features that matter most |
| Conflict detection against locked decisions | **HIGH** | The overlay-drawer conflict is stated verbatim in two places and the design system explicitly warns that this exact reopening has happened before |
| D20's data gap | **HIGH** | Read directly from the `device_health` schema and the config write path |
| Scope estimate | **MEDIUM** | The plan-count figure is an estimate (A4). The structural arguments for splitting do not depend on it. |
| D6 manifest icon requirements | **LOW** | Assumed from general PWA practice; flagged as A1 |

**Research date:** 2026-09-13
**Valid until:** 2026-10-13 for the codebase facts (they change when the code changes — re-verify any `file:line` after the first plan lands). **2026-11-13** for the browser-support figures; the one worth re-checking before D10 ships is Firefox's cross-document view transitions, which has 57 developer-signal upvotes and a positive Mozilla standards position on the parent feature.
