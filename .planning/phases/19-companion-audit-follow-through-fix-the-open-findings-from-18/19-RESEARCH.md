# Phase 19: Companion audit follow-through - Research

**Researched:** 2026-09-11
**Domain:** Python stdlib HTTP service (companion/), server-rendered HTML, ES5 vanilla JS static assets, HMAC session auth, CSP hardening
**Confidence:** HIGH (every claim below is grounded in a direct `Read`/`Grep` of the live code and a live run of the affected test harnesses; there is no external library/API research needed — no new dependency is introduced anywhere in this phase)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Every finding id below is an entry in 18-AUDIT.md; its evidence (file:line, screenshot, reviewer note) lives there and is not repeated. Each decision is locked unless marked Discretion.

#### Health page (advanced, but must read in plain words)
- **D-01 (A-19):** Health's battery card shows the same estimated percentage Home already computes (`home_page.battery_percent()`, linear 3.3-4.2 V, labelled "≈") beside the mV readout. Move `battery_percent()` into a shared non-page module (`companion/battery.py`) so neither page module imports the other.
- **D-02 (A-20):** Replace `freshness.js`'s 45 s `location.reload()` with a fetch of the Health page and an in-place swap of the tiles/readout (`.dashboard-grid`, `.battery-readout`, the anomaly banner). The "Live — refreshed HH:MM (0s ago)" line becomes an honest "Updated HH:MM" that advances on each successful swap; a visible Pause/Resume control stops the polling; an open `<details>` no longer silently suspends it.
- **D-03 (A-21):** Every stat tile carries a short text verdict (ok/warn/error words) in addition to its border colour, the way Home's tiles already do — WCAG 1.4.1.
- **D-04 (A-22):** The battery sparkline uses a fixed 3000-4200 mV y-range (clamped), so a flat series draws flat and a 15 mV wiggle stays flat; the dense-point suppression threshold is derived from the rendered width (points per pixel), not a fixed 39-point count tuned for a 226 px canvas.
- **D-05 (A-23):** Device-staleness thresholds derive from the configured wake interval: warn after 3 missed wakes, error after 12, floor 5 min / 20 min, using `wake_interval_s` (or `SKYPANE_SLEEP_S`, or `DISPLAY_OFF_SLEEP_S` while the screen is off). A single ≥100 mV inter-reading dip is a **warn**, never a page-level error. `coverage_status` warn and an active source fault both feed `overall_severity`.
- **D-06 (A-24):** Health's captions and tile labels use plain language; the technical term stays as a `title` tooltip on the label. Concretely: "Corroboration" → "Do the two data sources agree?", "Agreement / Single-source (uncorroborated) / Disagreement" → "Both agree / Only one saw it / They disagree", "ADS-B pipeline last ran" → "Flight data last updated", "adsbdb" → "the route database", "Resolution rate" → "Flights we could name", and the "CFG-04's registry" sentence is rewritten without the requirement id.

#### Settings pages (Display and Device)
- **D-07 (A-25):** A rejected save re-renders the page with the submitted values in the fields and a field-level error message under the offending control, instead of redirecting with one generic flash. Implement via a `?flash=save_failed` redirect that also carries no data — i.e. change the POST handler to render the page directly (200) on validation failure with an `errors` dict threaded through `config_page.render()`. The quiet-hours time inputs get `required`; an empty time is reported at the field, and never discards the rest of the form.
- **D-08 (A-26):** Disconnecting the calendar becomes its own `POST /settings/calendar/disconnect` form on the Device page, outside `#settings-form`, with a native confirm step (`<button>` + a `confirm()` in a tiny inline-free script, plus a server-side `confirm=yes` hidden field so the no-JS path still works via a two-step page). The checkbox is removed.
- **D-09 (A-27):** The static "Save settings" fallback button is hidden only once `dirty-state.js` has actually initialised the bar (that script adds a `dirty-ready` class), never on the mere presence of `.js`.
- **D-10 (A-28):** `dirty-state.js` installs a `beforeunload` guard while the form is dirty; the bar's own Save/Cancel clear it.
- **D-11 (A-29):** Runway card labels become "Runway 3 (07/25)", "Runway 4 (06/24)", "Runway 2 (02/20)" — `device_config.RUNWAYS[*]["label"]` — with the official ADP number kept in parentheses-free `tag_text`. `test_view_pages.py`'s label derivation check updates with it.
- **D-12 (A-30):** Theme chip grids and the runway row are wrapped in `<fieldset>` with a visually-hidden `<legend>` (or `role="radiogroup"` + `aria-labelledby` pointing at the group `<h2>`); every hint paragraph gets an id and its control an `aria-describedby`.
- **D-13 (A-31, S-02):** Home and Device show "Next wake ≈ HH:MM" computed from the last device check-in + the effective wake interval (`DISPLAY_OFF_SLEEP_S` while the screen is off), in Paris local time; "Applies on the next scheduled poll" captions gain "(next wake ≈ HH:MM)" where the value is known.
- **D-14 (S-04):** The Quiet hours group gets three preset buttons above the time inputs — "Night (23:00-07:00)", "Work day (08:00-18:00)", "Always on (off)" — that fill the inputs client-side and mark the form dirty; no server change.

#### Auth and shell
- **D-15 (A-32):** `auth.record_failure()` resets the failure counter once the lockout window has elapsed, so a lockout is 5 fresh failures per window, never permanent. Keep the process-global throttle (one shared password).
- **D-16 (A-33):** Session tokens are HMAC-signed with a key derived from the password via a per-process random salt generated at startup (so a leaked cookie is not an offline password oracle), and Sign out adds the token to a small in-memory revocation set consulted by `verify_session()`. A restart invalidates every session; acceptable for one household.
- **D-17 (A-34):** `Secure` on both cookies follows `SKYPANE_COMPANION_INSECURE_COOKIES=1` (dev/LAN only, documented in `deploy/skypane.env.example` as never-set-in-production).
- **D-18 (A-35):** Every response, redirects included, carries the hardening headers plus a `Content-Security-Policy` of `default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; frame-ancestors 'none'` — the app has no inline scripts or styles except the poll-cooldown countdown, which moves to `static/poll-cooldown.js` reading a `data-cooldown` attribute. `POST /ui-theme` and `POST /logout` require a valid session cookie.

#### Flights and Airlines
- **D-19 (A-36):** The Flights table drops the Runway column (one tracked runway; it stays in the mobile card's "More details" and the row's `title`), the scroller gets `tabindex="0"` and an accessible name, and the timestamp column shortens to the local clock.
- **D-20 (A-37):** Copy buttons show a visible transient "Copied" state (text swap for 1.5 s), carry the row's callsign in their accessible name, and only report success when `execCommand`/`clipboard.writeText` actually succeeded.
- **D-21 (A-38):** Gap cards move out of the main grid into an "Unidentified airlines" strip at the top of Airlines with one plain sentence ("The frame saw these callsigns but doesn't know the airline. Tap one to name it."); the resolve panel's back link returns to Airlines.
- **D-22 (A-39):** The illustration replace/upload/delete forms render in the Airlines lightbox only when the page is opened with `?edit=1` (a link "Edit artwork" on the Device page); the everyday lightbox is view-only.

#### Screens seam (A-40 remainder)
- **D-23 (A-40):** `device_config` gains `screen_id` (default `"plane-frame"`, normalised against `screens.SCREEN_IDS`); `page_context()` threads it as `ctx["screen_id"]`; the Display/Device headers render a screen selector `<select>` only when `len(SCREEN_IDS) > 1`. No second screen type is added; this closes the seam so the next screen type is a registry entry plus its groups.

### Claude's Discretion
- Exact copy of the plain-language Health labels beyond the mapping in D-06, the CSP header's exact directive order, the shape of the field-level error markup (must reuse the existing `--color-status-error` token and the label voice), test check counts.
- Whether D-16's revocation set lives in `auth.py` or `app.py` (it must be consulted from `require_session()`).

### Deferred Ideas (OUT OF SCOPE)

The four larger suggestions from 18-AUDIT.md are each a phase of their own and are added to the roadmap as Phase 20, not folded in here:
- S-01 French localisation of the companion
- S-03 Theme picker as a carousel with a live preview of the current flight
- S-05 Notifications (battery low, frame silent)
- S-06 Per-person entry point / simple mode

Also deferred: a calibrated battery curve (D-01 keeps the linear estimate until Phase 5's discharge run yields data); per-IP login throttling (D-15 keeps the global counter).
</user_constraints>

## Summary

This phase has no "unknown domain" risk — it is 23 pre-scoped bugfixes/enhancements against a single, mature, well-documented stdlib-only codebase (`companion/`, `server/device_config.py`). The real risk is entirely mechanical: (1) this codebase's test harnesses pin exact markup strings and a running `EXPECTED_CHECK_COUNT` per file that **must** be re-derived by executing the harness, not by arithmetic on old comments; (2) two decisions (D-07, D-16) require careful, backward-compatible signature widening rather than a breaking rewrite, because 46-75 existing pinned test call sites depend on the current return shapes; (3) D-18's locked CSP string (`style-src 'self'`, no `unsafe-inline`, no nonce) will — if implemented literally with no other change — silently break the Theme picker's rendered colour swatches, because `companion/pages/config_page.py` renders 7 `style="background:..."` attributes today. This is flagged as an Open Question requiring an explicit resolution before Wave planning, not silently overridden.

Every one of the 23 decisions lands in code that already exists and is already well-commented with its own precedent (the codebase's own convention is "explain the why in a comment beside the code"), so this research is primarily a map from decision -> file:line -> function/constant -> the exact test-harness checks that pin today's behaviour and will need retargeting.

**Primary recommendation:** Treat this phase as a large "surgical edit" pass, not a redesign. For each decision, retarget the pinned check(s) named below in place (same check, same name, updated expectation) rather than deleting and re-adding — this codebase's own established convention (visible in every file's history comments) is to retarget pinned checks in place and note the retargeting, never to silently drop coverage.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CFG-01 | User can configure the frame's settings via a web interface | D-07 (field-level errors), D-11 (runway labels), D-12 (fieldset/aria), D-14 (quiet-hours presets), D-23 (screen seam) all land in `companion/pages/config_page.py`, the CFG-01 settings surface |
| CFG-03 | User can see the device's last-known health status via the web interface | D-01..D-06 (Health page battery %, freshness, tile verdicts, sparkline scaling, staleness thresholds, plain language) all land in `companion/pages/health_page.py`, the CFG-03 surface |
| CFG-04 | User can see unresolved ADS-B callsign ICAO prefixes via the web interface | D-06's "CFG-04's registry" copy fix and D-21's "Unidentified airlines" strip both touch the CFG-04 registry's presentation (`health_page.py`'s migrated registry section, `airlines_page.py`'s gap cards) |
| CFG-06 | User can see a log of recently detected flights via the web interface | D-19 (drop Runway column, shorten timestamp, scroller a11y) and D-20 (visible copy feedback) land in `companion/pages/history_page.py`, the CFG-06 Flights page |
| CFG-08 | User can see airline/route resolution statistics via the web interface | D-06's plain-language pass touches the migrated Resolution-statistics section in `health_page.py`, the CFG-08 surface |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Session auth / lockout / CSP headers (D-15..D-18) | API / Backend (`companion/auth.py`, `companion/app.py`) | — | Stateless HTTP handler tier; no browser-side auth logic exists or should exist |
| Settings validation + persistence (D-07..D-14, D-23) | API / Backend (`companion/pages/config_page.py`, `server/device_config.py`) | Browser (dirty-state.js, poll-cooldown.js) | Server is sole source of truth for validation (ASVS V5); browser only provides UX affordances (dirty tracking, countdown) that degrade to a fully-working no-JS form |
| Health/Flights/Airlines presentation (D-01..D-06, D-19..D-22) | API / Backend (server-rendered HTML in `companion/pages/*.py`) | Browser (battery-trend.js, copy-button.js, panel-lookup.js, freshness.js) | This app has no client-side rendering framework; every page is generated server-side per request, JS only attaches behaviour to already-rendered DOM |
| Freshness/live-refresh (D-02) | Browser (`companion/static/freshness.js`) | API / Backend (`health_page.py` still computes all severity server-side) | D-02 changes the *transport* (reload -> fetch+swap) but explicitly must not move any verdict computation client-side |
| Database / Storage | Database (`server/history_db.py`, SQLite) | — | Out of scope for this phase except as a read source; no schema changes are needed by any of the 23 decisions |

## Standard Stack

No new library, framework, or package is introduced by this phase. Every decision is implemented with:
- Python 3 stdlib only (`hmac`, `hashlib`, `secrets`, `time`, `json`, `sqlite3` via `server/history_db.py`) — matching this codebase's existing, explicit stdlib-only discipline (`companion/auth.py`'s own header comment).
- The project's existing hand-rolled ES5-safe vanilla-JS idiom (`companion/static/*.js`) — no build step, no bundler, no framework, no third-party JS.

**Package Legitimacy Audit:** Not applicable — this phase installs zero external packages in any ecosystem. The Package Legitimacy Gate is skipped per its own "no external packages" exemption.

**Version verification:** Not applicable (no packages).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| A per-request CSP nonce mechanism | A custom nonce generator | `secrets.token_urlsafe()` (stdlib, already the correct tool if the CSP-vs-inline-style conflict below is resolved via nonce) | Never hand-roll random-token generation; `secrets` is stdlib and already implicitly endorsed by this codebase's own `hmac`/`hashlib` stdlib-only discipline |
| JS->Python value passing into an inline `<script>` | String formatting / f-string interpolation into script bodies | `config_page._js_literal()` (already exists, `json.dumps()` + `</`-escaping) | This exact helper already solves the escaping problem correctly; any new script-emitting code in this phase must reuse it, never re-derive it |
| Signing-key derivation for D-16 | A hand-rolled KDF | `hmac.new(configured_password(), per_process_salt, hashlib.sha256).digest()` as the derived signing key (HMAC-as-KDF is a standard, well-understood construction; do not invent a new derivation) | `auth.py`'s own module docstring already states "stdlib-only... hashlib, hmac... this module never imports anything under server/" — the KDF must stay inside that same discipline |

**Key insight:** every "problem" in this phase is a modification of existing, working code, not a new capability needing a new tool. The single highest-risk temptation is to add a JS framework or template library to solve D-07's field-level-errors problem "more cleanly" — resist it; the existing string-templating + `escape_html()` choke-point discipline extends cleanly to every decision here (see Code Examples below).

## Common Pitfalls

### Pitfall 1: `EXPECTED_CHECK_COUNT` is NOT a single, findable assignment
**What goes wrong:** Several harness files (`companion/test_companion_app.py`, `companion/test_config_page.py`) contain **multiple** `EXPECTED_CHECK_COUNT = N` statements at different line numbers, each followed by a large comment block narrating the historical derivation of a *previous* count. Grepping for the first match, or trusting the largest number in a comment, gives a wrong answer.
**Why it happens:** This codebase's convention is to leave the full historical derivation trail in place as an append-only log, rather than deleting superseded lines. Because Python executes top-to-bottom, only the **last** `EXPECTED_CHECK_COUNT = N` assignment in the file is live at runtime.
**How to avoid:** Never compute the new count by arithmetic. After adding/removing/retargeting checks, run the harness directly (`server/.venv/bin/python3 companion/test_X.py`) and read the actual "N/M checks pass" line, then set `EXPECTED_CHECK_COUNT` to that M with a comment citing this plan.
**Warning signs:** A `grep -n EXPECTED_CHECK_COUNT` returning more than one line for the same file — treat only the **last** line number as authoritative before your edit.

**Current authoritative values** (verified live, 2026-09-11, `server/.venv/bin/python3 <file>`):

| Harness | Current pass/total | Notes |
|---|---|---|
| `companion/test_companion_app.py` | 190/192 | 2 failures are the documented pre-existing root-sandbox artifacts (see file's own header) — do not "fix" by weakening |
| `companion/test_config_page.py` | 142/142 | clean |
| `companion/test_status_pages.py` | 162/163 | 1 pre-existing root-sandbox failure — do not "fix" |
| `companion/test_view_pages.py` | 65/65 | clean |
| `companion/test_contrast_check.py` | 36/36 | clean, unaffected by this phase |
| `server/test_runway_config.py` | 14/14 | clean, unaffected by this phase |

### Pitfall 2: D-18's locked CSP string will silently break the Theme picker's colour swatches
**What goes wrong:** `companion/pages/config_page.py` renders exactly 7 `style="background:%s"` attributes (theme-chip preview `<img>` background, 2x `theme-chip__dot`, 2x `theme-swatch__chip` in the single-theme read-only branch, plus one more `theme-swatch__chip` pair at line ~1471 in the Calendar section's theme-status display) — all populated from `device_config.THEMES[...]`'s fixed hex registry, never from user input. D-18 locks `Content-Security-Policy: ...; style-src 'self'; ...` verbatim, with no `'unsafe-inline'`, no nonce, no hash. A CSP `style-src` directive without one of those exceptions blocks **every** `style` attribute on the page, not just `<style>` blocks. Implemented literally, every theme chip and swatch on Display/Device silently loses its colour preview (the attribute is simply ignored by the browser — no error, no console warning most users would see, so this could ship unnoticed by casual QA).
**Why it happens:** D-18 was authored against the *script* half of the CSP problem (the two inline `<script>` tags in `poll_trigger_section()`) and states "no inline scripts or styles **except** the poll-cooldown countdown" — but a source read shows the inline-**style** attributes were not accounted for in that sentence at all; they are a separate, pre-existing surface D-18's own text does not mention.
**How to avoid:** This needs an explicit decision before Wave planning (see Open Questions below) — not a silent substitution. The two structurally sound options are: (a) add `'unsafe-inline'` to `style-src` only (not `script-src`), justified because every style value is server-controlled from a small fixed enum, never user-supplied, or (b) generate the swatch colours as CSS custom properties set via a handful of registry-driven classes added to `companion/static/style.css` (one rule per `THEME_IDS` member, hand-written to mirror `device_config.THEMES`, matching this file's existing "hand-written, no generator" discipline) and swap every `style="background:X"` for a `class="theme-swatch--{id}"` reference — CSP-clean with zero exceptions, at the cost of one CSS rule to keep in sync by hand whenever a theme is added (no different in kind from the runway/theme registries already requiring hand-sync in a few places).
**Warning signs:** A visual regression where every theme chip's coloured background disappears but the check-glyph/border selection state still works (that part uses classes, not inline style, so it survives).

### Pitfall 3: D-16's stateless-token design and D-16's revocation-set requirement are in tension
**What goes wrong:** `auth.issue_session_token()`/`verify_session_token()` are deliberately stateless (`auth.py`'s own docstring: "There is no server-side session store to leak, to grow unbounded, or to lose on restart"). D-16 now asks for BOTH a derived signing key AND a small in-memory revocation set consulted by `require_session()`/`_is_authenticated()` on Sign out — this is a real, deliberate departure from "stateless," not a bug, and the Discretion note ("D-16's revocation set lives in auth.py or app.py") already anticipates it needs a home.
**Why it happens:** A pure stateless HMAC token cannot be "revoked" without server-side memory of what was revoked — this is inherent to stateless tokens, not a design flaw to route around.
**How to avoid:** Accept the small state addition explicitly (a module-level `set()` in whichever module wins the Discretion call, guarded because `ThreadingHTTPServer` serves concurrent requests — a `set.add()`/`in` check on a `set` is not atomic-safe against concurrent mutation in CPython without a lock in the general case, though CPython's GIL makes single `add()`/`in` operations effectively atomic in practice; consider a `threading.Lock()` around it anyway to be explicit, mirroring the existing `_POLL_LOCK` precedent in `app.py`). Cap or expire entries so the set cannot grow unbounded over the 12h `SESSION_TTL_S` window (a set entry only needs to live until the token's own embedded expiry passes — prune on each check, or track `(token, expiry)` pairs).
**Warning signs:** A revocation set with no pruning growing unbounded on a long-running process; a revocation check missing from one of the two auth entry points (`_is_authenticated()` is the sole call site today — confirm any new revocation check is added there, not duplicated at each of the 9+ `require_session()` call sites).

### Pitfall 4: D-15's fix location is `LoginThrottle.record_failure()`, not `locked_out()`
**What goes wrong:** The bug is that `self._failures` is never decremented/reset except by `record_success()`. Once `_failures >= limit`, `locked_out()` correctly reports `False` once `_locked_until` passes — but the very next `record_failure()` call re-arms `_locked_until` immediately (since `_failures` was already >= limit and only grows), producing an effectively permanent lockout after the first 5 failures, exactly as A-32 describes. Fixing `locked_out()` instead of `record_failure()` cannot fix this — `locked_out()` already returns the right time-window answer.
**Why it happens:** The counter and the timer are two different pieces of state that must be reconciled at the point a *new* failure arrives, not at the point lockout status is *read*.
**How to avoid:** In `record_failure()`, first check whether `time.time() >= self._locked_until` (the previous window, if any, has fully elapsed) — if so, reset `self._failures = 0` before incrementing. This gives "5 fresh failures per window, never permanent" per D-15's own wording.
**Warning signs:** The existing pinned check `_login_throttle_allows_locks_and_resets` (companion/test_companion_app.py ~line 798) only tests the `record_success()` reset path — a new check exercising "wait past `lockout_s`, fail once more, confirm still only 1/limit toward a fresh lockout" must be added; it does not currently exist anywhere in the harness.

### Pitfall 5: D-02's fetch-and-swap must keep three independent contracts intact
**What goes wrong:** `freshness.js`'s own header comment (lines 42-96) already documents, in detail, *why* a prior design decision chose `location.reload()` over an in-place fetch-and-swap: (1) the Health nav-tab dot is emitted by `layout.page_shell()`, **outside** `health_page.render()`'s own output — an in-page patch of only the body leaves a stale nav dot beside a fresh banner; (2) `battery-trend.js` and `list-filter.js` each capture their DOM once inside an IIFE with no re-init hook — replacing the chart/filter region under a patch leaves a permanently dead chart or filter; (3) a patch needs an HTML-writing DOM sink, which this codebase's forbidden-sink test guards currently ban outright for other files.
**Why it happens:** D-02 is explicitly reversing this prior decision, but the reasons the prior decision gave are still real constraints on *how* to reverse it.
**How to avoid:** The fetch-and-swap replacement must (a) either re-fetch and swap the **entire authenticated shell** including the nav (not just `.dashboard-grid`), or fetch just the Health body but also separately re-fetch/update the nav dot's `class`/text via a second, tiny targeted DOM write (never re-running `layout.page_shell()` client-side); (b) re-attach `battery-trend.js`'s hover/tap/roving-tabindex behaviour and `list-filter.js`'s query state after every swap (i.e., re-run their IIFEs' setup logic against the new DOM, or preserve the filter input's live value across the swap before replacing surrounding markup); (c) if an HTML-writing sink is now unavoidable (e.g. `element.innerHTML = fetchedHtml`), get this reviewed explicitly against `test_config_page.py`'s `_FORBIDDEN_SCRIPT_SINKS` guard and `test_companion_app.py`'s nav-dropdown.js/panel-lookup.js sink guards — freshness.js is not currently covered by name in those guards (confirmed by grep), so extending the sink ban list to include it may be the safer complementary change, or the plan must document why freshness.js is a deliberate, reviewed exception.
**Warning signs:** After the swap, the battery sparkline no longer responds to hover/tap; the Health nav-tab dot shows stale severity after a swap that changed the on-page severity; an open `<details>`/filter query silently resets on a background swap despite the "no swap while interacting" guard (the existing `userIsInteracting()` predicate in freshness.js should be reused for the new mechanism, not reimplemented).

### Pitfall 6: D-07's "least invasive" path is signature widening, not a return-type change
**What goes wrong:** `config_page.handle_post(form, ctx)` is called from 75 places in `companion/test_config_page.py`, every one expecting a single string return (the flash key). `config_page.render(ctx, scope=SCOPE_ALL)` is called from 46 places, all expecting the current two-argument (or one-argument) shape. Changing either function's return type or required-argument shape to add error/submitted-value support breaks all of these call sites simultaneously.
**Why it happens:** The natural first instinct ("just return a tuple") is the most invasive possible change to the most heavily-pinned function in the phase.
**How to avoid:** Add `errors=None` as a new, fully-defaulted keyword parameter to both functions. `handle_post(form, ctx, errors=None)` fills the caller-supplied `errors` dict in place at each of its 13 `return FLASH_SAVE_FAILED` sites (via a tiny `_note_error(errors, field, message)` helper that no-ops when `errors is None`) and still returns the same string as always — every existing call site (which never passes `errors=`) is untouched. `render(ctx, scope=SCOPE_ALL, errors=None, submitted=None)` renders each field's current value from `submitted.get(field)` when `submitted` is provided and a matching key exists in `errors`, else falls back to today's `ctx["device_config"]`-sourced value exactly as now. `companion/app.py`'s `_handle_settings_post()` (the sole real caller that needs the new behaviour) passes `errors={}` and, if it comes back non-empty after `handle_post()`, renders the page directly at 200 (mirroring the exact pattern `_render_login_page()`/`_handle_login_post()` already establish for the login form's own inline-error 401 re-render) instead of taking the existing `self.redirect(...)` branch.
**Warning signs:** Any diff that changes `handle_post`'s return statement shape (e.g., to a tuple) — this is the signal the least-invasive path was abandoned.

### Pitfall 7: D-08's calendar-disconnect move leaves `submitted_calendar_signal()` partially dead
**What goes wrong:** `submitted_calendar_signal(form)` (config_page.py ~line 1824) has 6 resolution gates; gates 1-3 exist solely to interpret a `calendar_disconnect` field submitted **inside** the main settings form. D-08 removes that checkbox from the settings form entirely and gives disconnect its own route/form. After this change, `calendar_disconnect` can never appear in the `/settings` POST body again, so gates 1-3 become unreachable dead code for that call site — but the same function is documented as shared with "plan 17-04's request handler," meaning a second caller may also rely on its current 6-gate shape.
**Why it happens:** D-08 changes *where* disconnect is triggered from without this function's contract being told about it.
**How to avoid:** Before removing the checkbox from `config_page.py`'s calendar section HTML, grep every call site of `submitted_calendar_signal()` in both `config_page.py` and `app.py`Text to confirm which ones the new dedicated disconnect route can call directly (bypassing signal resolution as it will always mean "clear") versus which keep needing the full function. Prefer leaving gates 1-3 in place (harmless, unreachable from the trimmed form, but still correct if a hostile client crafts a `calendar_disconnect` field into a `/settings` POST directly — the all-or-nothing rejection in `handle_post()` still protects against that) over deleting them, unless a specific test proves them unreachable and worth removing for clarity. Document the choice either way.
**Warning signs:** A test exercising `POST /settings` with a crafted `calendar_disconnect` field expecting the OLD in-form-disconnect behaviour — this specific behaviour is being deliberately retired by D-08 and any such test must be retargeted to assert the new dedicated route is the only path to disconnect, not that the old field is now silently ignored (ignoring might be fine, but the test should say so explicitly).

## Code Examples

### D-07: field-level errors without breaking the PRG success path
```python
# companion/pages/config_page.py — signature widening, not a rewrite
def handle_post(form, ctx, errors=None):
    def _note(field, message):
        if errors is not None:
            errors[field] = message
    ...
    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        _note("theme", "Not a recognised theme.")
        return FLASH_SAVE_FAILED
    ...

def render(ctx, scope=SCOPE_ALL, errors=None, submitted=None):
    errors = errors or {}
    submitted = submitted or {}
    # each field builder reads submitted.get(name, ctx["device_config"][name])
    # and, if name in errors, renders a <p class="field-error">{errors[name]}</p>
    # immediately under that control.
```
```python
# companion/app.py — mirrors _render_login_page()'s existing 200-on-failure precedent
def _handle_settings_post(self):
    ...
    errors = {}
    flash_key = config_page.handle_post(form, ctx, errors=errors)
    if errors:
        scope = config_page.submitted_scope(form)
        body = config_page.render(ctx, scope=scope, errors=errors, submitted=form)
        html_doc = layout.page_shell(
            title=_PAGE_TITLES[back], active=layout.nav_slug(back), body=body,
            ui_theme=ctx["ui_theme"], health_alert=ctx["health_severity"])
        return self.send_html(200, html_doc)
    if flash_key != FLASH_KEY_SAVED:
        return self.redirect("%s?flash=%s" % (back, quote(flash_key)))
    ...  # unchanged PRG success path below
```
Source: `companion/pages/config_page.py:1617` (`render`), `:1888` (`handle_post`); `companion/app.py:1246-1249` (`_render_login_page`, the precedent), `:2114-2122` (current redirect-only failure branch).

### D-15: reset the failure counter when the lockout window has elapsed
```python
# companion/auth.py
def record_failure(self):
    if self._failures >= self._limit and time.time() >= self._locked_until:
        self._failures = 0  # the previous window fully elapsed; start counting fresh
    self._failures += 1
    if self._failures >= self._limit:
        self._locked_until = time.time() + self._lockout_s
```
Source: `companion/auth.py:187-190`.

### D-16: derive a signing key, never sign with the raw password
```python
# companion/auth.py — generated once at process start (module import time)
_PROCESS_SALT = secrets.token_bytes(32)

def _signing_key():
    # HMAC-as-KDF: leaking a token's signature no longer lets an attacker
    # test password guesses offline, because _PROCESS_SALT never leaves
    # this process and is not derivable from any (expiry, signature) pair.
    return hmac.new(configured_password(), _PROCESS_SALT, hashlib.sha256).digest()

def issue_session_token():
    expiry = str(int(time.time()) + SESSION_TTL_S)
    signature = hmac.new(_signing_key(), expiry.encode(), hashlib.sha256).hexdigest()
    return "%s.%s" % (expiry, signature)
```
Revocation set (Discretion: pick one home, e.g. `app.py` beside `_POLL_LOCK`):
```python
_REVOKED_TOKENS = {}  # token -> expiry_int, pruned on each check
_REVOKED_LOCK = threading.Lock()

def revoke(token, expiry_int):
    with _REVOKED_LOCK:
        _prune(_REVOKED_TOKENS)
        _REVOKED_TOKENS[token] = expiry_int
```
`_is_authenticated()` must check `verify_session_token(token) and token not in _REVOKED_TOKENS` (or equivalent), and the `LOGOUT_ROUTE` handler must extract the token from the cookie *before* clearing it and call `revoke()`.
Source: `companion/auth.py:92-125` (token issue/verify), `companion/app.py:916-942` (`_is_authenticated`/`require_session`), `:2255-2256` (current ungated logout handler).

### D-18: gate `/ui-theme` and `/logout`, and add hardening headers to redirects
```python
# companion/app.py do_POST() — both currently missing require_session()
if path == THEME_ROUTE:
    if not self.require_session():
        return None
    return self._handle_theme_post()

if path == LOGOUT_ROUTE:
    if not self.require_session():
        return None
    return self.redirect(LOGIN_ROUTE, set_cookie=auth.logout_set_cookie_header())
```
```python
# companion/app.py redirect() currently sends no hardening headers at all
def redirect(self, location, set_cookie=None):
    self.send_response(303)
    self.send_header("Location", location)
    if set_cookie:
        self.send_header("Set-Cookie", set_cookie)
    self.send_header("Content-Length", "0")
    self._send_hardening_headers()  # NEW — also needs the CSP header added inside this method
    self.end_headers()
```
Source: `companion/app.py:2252-2256` (ungated theme/logout routes), `:906-912` (redirect with no hardening headers), `:855-880` (`_send_hardening_headers`/`send_html`, the pattern to extend with the CSP header).

### D-18: externalize both inline `<script>` bodies in the poll trigger
`companion/pages/config_page.py`'s `poll_trigger_section()` currently emits `_poll_cooldown_script()` (disabled branch) or `_poll_submit_script()` (enabled branch) — both literal inline `<script>` elements. Under `script-src 'self'`, both must move to a static file (e.g. `companion/static/poll-cooldown.js`) reading `data-cooldown`/`data-cooldown-text-id`/etc. attributes off the button, following the exact ES5/`_js_literal()`-free pattern `battery-trend.js`/`copy-button.js` already establish (attribute reads, `textContent` writes only, no eval). Both scripts' logic must be preserved (the countdown AND the disable-on-submit affordance) — D-18's own text names only "the poll-cooldown countdown," but the submit-affordance script is the same kind of inline-script CSP violation and must move too, or `script-src 'self'` will simply strip it silently.
Source: `companion/pages/config_page.py:1192-1364`.

### D-01: shared `battery_percent()`, imported by both pages, owned by neither
```python
# companion/battery.py (new file)
BATTERY_FULL_MV = 4200
BATTERY_EMPTY_MV = 3300

def battery_percent(mv):
    ...  # moved verbatim from companion/pages/home_page.py:114-124
```
`home_page.py` and `health_page.py` both `import companion.battery as battery` and call `battery.battery_percent(mv)` — preserving `companion/pages/__init__.py`'s documented "no page module imports another page module" boundary, since `battery.py` is not a page module.
Source: `companion/pages/home_page.py:106-124` (current owner, to move), `companion/pages/health_page.py` (new consumer, currently mV-only).

### D-11: runway label change is self-verifying at test time
`companion/test_view_pages.py`'s `_presentation_labels_in_full_render()` check already derives its expected string via `device_config.runway_label("3")` (a live call, not a hardcoded literal) — so changing `RUNWAYS["3"]["label"]` from `"Piste 3"` to `"Runway 3 (07/25)"` (and the sibling two) does **not** require touching that test file at all; it tracks the registry automatically. Confirmed via `grep -rn "Piste"` across `companion/` — the only production reference is `server/device_config.py`'s own `RUNWAYS` dict; the only test reference is the self-deriving check above.
Source: `server/device_config.py:416-432` (`RUNWAYS`), `:960-961` (`runway_label()`), `companion/test_view_pages.py:1434-1472`.

## Runtime State Inventory

Not applicable — this phase is not a rename/refactor/migration. Confirmed: no decision renames an on-disk key, a database column, an env var, or a secrets-file key. (D-23 *adds* a new `screen_id` key to `device_config.json` with a default that degrades a pre-existing file with no such key to `"plane-frame"` — an additive schema change, not a rename, and `load_device_config()`'s existing "always returns all N keys, missing key -> normalise's default" pattern already handles this correctly by construction; no migration script is needed.)

## Environment Availability

Not applicable — no new external tool, service, or runtime dependency is introduced. The existing `server/.venv/bin/python3` interpreter (already provisioned) is sufficient for every harness this phase touches.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib-only, hand-rolled `check(name, fn)` harness convention — no pytest, no unittest runner |
| Config file | none — `scripts/run-all-tests.sh` -> `scripts/run_all_tests.py` is the canonical list |
| Quick run command | `server/.venv/bin/python3 companion/test_<name>.py` (each file is directly executable and self-reports `N/M checks pass`) |
| Full suite command | `scripts/run-all-tests.sh` (parallel runner over the canonical harness list) |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-01 | Settings save shows field-level errors + presets + a11y groups | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py` | Yes |
| CFG-03 | Health shows battery %, honest refresh, plain language | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_status_pages.py` | Yes |
| CFG-04 | Unresolved-prefix registry copy/placement | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_status_pages.py` (Health) and `companion/test_view_pages.py` (Airlines gap strip) | Yes |
| CFG-06 | Flights table columns, scroller a11y, copy feedback | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_view_pages.py` | Yes |
| CFG-08 | Resolution-statistics plain language | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_status_pages.py` | Yes |
| Auth (D-15..D-18) | Lockout reset, revocation, CSP, route gating | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` | Yes |

### Sampling Rate
- **Per task commit:** the single most relevant harness for the file(s) touched (e.g. touching `health_page.py` -> run `test_status_pages.py`)
- **Per wave merge:** `scripts/run-all-tests.sh` (full suite)
- **Phase gate:** full suite green (excluding the 2 pre-existing, documented root-sandbox failures) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `companion/auth.py` — no test currently exercises "a failure after the lockout window has fully elapsed only counts as 1 toward a *fresh* lockout" (D-15's actual fix). Add before or alongside the fix.
- [ ] `companion/auth.py` / wherever D-16 lands — no test exists for token revocation (Sign out -> the same token cookie replayed -> rejected). Add.
- [ ] `companion/app.py` — no test exists asserting `redirect()` responses carry the hardening headers/CSP (today's `redirect()` sends none). Add.
- [ ] `companion/pages/config_page.py` — no test exists for the field-level-error-with-resubmitted-values render path (today only the generic `FLASH_SAVE_FAILED` redirect is tested). Add.
- [ ] `companion/static/poll-cooldown.js` (new file) — needs its own pre-auth-serving/ES5-dialect/route-agreement regression checks, mirroring the existing pattern for every other static script (`dirty-state.js`, `list-filter.js`, `copy-button.js`, `freshness.js` each have one in `test_companion_app.py`).

*(Every other decision extends existing, already-covered render paths — see the Decision Implementation Map below for the exact existing check each retargets.)*

## Security Domain

### Applicable ASVS Categories (Level 1, block on high — per `.planning/config.json`)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | Yes | HMAC-signed session tokens (existing), constant-time password check (`hmac.compare_digest`, existing) — D-15/D-16 harden the lockout and revocation halves |
| V3 Session Management | Yes | D-16 adds explicit session revocation on logout; D-17 makes the `Secure` cookie flag conditional on an explicit dev-only env flag (never default-off) |
| V4 Access Control | Yes | D-18 closes the two ungated state-changing routes (`/ui-theme`, `/logout`) |
| V5 Input Validation | Yes | Existing membership-test-before-use discipline (`device_config.py`'s `normalise_*()` / `save_device_config()`'s explicit gates) extends unchanged to D-23's new `screen_id` field and D-14's presets (client-fill only, still validated server-side as an ordinary `quiet_hours_start`/`quiet_hours_end` pair) |
| V6 Cryptography | Partially | `hmac`/`hashlib.sha256` (stdlib, correct primitive) already in use; D-16 must derive rather than reuse the raw password as a signing key — see Pitfall 3 |
| V14 Configuration (CSP) | Yes | D-18's CSP header — see Pitfall 2 for the concrete conflict that must be resolved, not silently shipped broken |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Offline password oracle from a leaked session cookie | Information Disclosure / Elevation of Privilege | D-16: derive the signing key via HMAC-as-KDF with a per-process random salt never embedded in the cookie (see Code Examples) |
| Permanent lockout / DoS against the single shared password (A-32, one household member locks out another) | Denial of Service | D-15: reset the failure counter once the lockout window elapses (see Pitfall 4) — this is a courtesy guard for one household, not a defense against a distributed attacker (existing `LoginThrottle` docstring already states this scope) |
| Clickjacking / MIME-sniffing / referrer leakage on a redirect response | Tampering / Information Disclosure | D-18: `redirect()` must call `_send_hardening_headers()` (currently only `send_html()`/`send_bytes()` do) |
| Reflected/stored XSS via an unescaped dynamic value in server-rendered HTML | Tampering | Already mitigated site-wide by the single-escaping-choke-point discipline (`escape_html()`); every new markup builder this phase adds (field-level error spans, screen-selector `<select>`, disconnect-confirmation page, "Unidentified airlines" strip heading) must route every dynamic value through it, with zero exceptions — this is the one discipline every existing page module's docstring restates |
| CSRF on the new dedicated calendar-disconnect route (D-08) | Tampering | Inherits the site-wide mitigation already in place: `SameSite=Strict` session cookie + no cross-origin legitimate use case (single-operator tool) — same posture every other state-changing POST route already relies on; the native `confirm()` step is a UX safeguard against misclick, not a CSRF control, and must not be mistaken for one |
| Un-gated state-changing routes reachable without a session (A-35) | Elevation of Privilege | D-18: add `require_session()` to `POST /ui-theme` and `POST /logout` (currently the only two state-changing POST routes in `do_POST()` without it) |

## Decision Implementation Map

Every decision below lists: the exact function/constant it lands in (file:line, verified live), and the existing pinned test-harness check(s) that will need retargeting in place (never deleted) once the behaviour changes.

| Decision | Lands in | Existing pinned check(s) to retarget |
|---|---|---|
| D-01 battery % on Health | New `companion/battery.py`; `companion/pages/home_page.py:114-124` (move from); `companion/pages/health_page.py` (new consumer, `_device_section()`/tile builder ~line 1403+) | `companion/test_view_pages.py` home_page battery-percent checks (currently assert `battery_percent` lives on `home_page`); `companion/test_status_pages.py` Health battery-tile checks (currently mV-only, no `%` assertion) |
| D-02 fetch-and-swap freshness | `companion/static/freshness.js` (full rewrite of `doRefresh()`/interval machinery); `companion/pages/health_page.py`'s `render()` freshness pill block (~line 2468-2498) | `companion/test_status_pages.py`'s served-`freshness.js`-carries-interval-constant check (~"the real served freshness script... carries the interval constant and the visibility-change listener") — text changes since the reload call is replaced |
| D-03 tile text verdicts | `companion/pages/health_page.py`'s `_device_section()`/`_pipeline_section()`/tile calls in `render()` (~line 1403-1476, 2423-2441) | New checks needed — WCAG 1.4.1 text-verdict presence was explicitly removed by quick task 260901-tsa finding C's own comment; this decision reverses that removal for Health only (Home's tiles already have it, per `FRAME_STATE_TEXT` etc.) |
| D-04 sparkline fixed range + width-aware density | `companion/pages/health_page.py`: `battery_sparkline_svg()`'s `lo, hi = min(values), max(values)` (~line 866) and `_SPARKLINE_DENSE_POINT_THRESHOLD = 39` (~line 637) | `companion/test_status_pages.py`'s sparkline y-axis-label checks (currently assert min/max-derived labels; must assert fixed 3000/4200 labels) and the hardcoded-39-threshold checks |
| D-05 wake-interval-derived staleness | `companion/pages/health_page.py`: `STALE_DEVICE_WARN_S`/`STALE_DEVICE_ERROR_S` constants (~line 91-92) become functions of `wake_interval_s`; `battery_status()`'s `BATTERY_DROP_WARN_MV` escalation to `"error"` (~line 1039) demotes to `"warn"`; `overall_severity()` (~line 1100) folds in `coverage_status()`/source-fault | `companion/test_status_pages.py`'s fixed 3600s/21600s threshold checks; the `battery_status()` "returns error on >=100mV drop" check (demotes to warn); `overall_severity()`'s precedence-table check |
| D-06 plain-language Health copy | `companion/pages/health_page.py` constants: `RESOLUTION_RATE_LABEL`, `_CORROBORATION_ROWS` labels, `PIPELINE_FRESHNESS_LABEL`, the "adsbdb"/"CFG-04's registry" prose in `_SOURCE_ROWS`/`_READ_ONLY_NOTE` | `companion/test_status_pages.py`'s copy-substring checks for "Corroboration"/"Agreement"/"adsbdb"/"Resolution rate" — every literal-string assertion on this old copy must be retargeted to the new plain-language strings, with the technical term preserved only in a `title=` tooltip |
| D-07 field-level errors | `companion/pages/config_page.py`: `handle_post(form, ctx, errors=None)` (~line 1888), `render(ctx, scope=SCOPE_ALL, errors=None, submitted=None)` (~line 1617); `companion/app.py`: `_handle_settings_post()` (~line 2114) | None of the 75/46 existing pinned calls break (see Pitfall 6) — new checks needed for the 200-render-with-errors path, none exist today |
| D-08 dedicated calendar disconnect | `companion/pages/config_page.py`: remove `disconnect_checkbox_html` from calendar section (~line 1109-1128), trim `submitted_calendar_signal()` gates 1-3 (~line 1824-1885, see Pitfall 7); `companion/app.py`: new `POST /settings/calendar/disconnect` route + handler | `companion/test_config_page.py`'s calendar-disconnect-checkbox-in-form checks; `companion/test_companion_app.py`'s T-17-FLASH calendar-disconnect-related checks may need a new route target |
| D-09 dirty-ready gated fallback | `companion/static/dirty-state.js` (add a `dirty-ready` marker, e.g. `document.documentElement.classList.add("dirty-ready")` once `bar`/`countEl` are confirmed present, ~line 51-53); `companion/static/style.css`'s `.js [data-static-save-fallback]` rule (~line 704) retargets to `.dirty-ready [data-static-save-fallback]` | None found pinning the current `.js`-keyed selector by name in a Python test; a CSS-string-presence check in `test_status_pages.py`/`test_companion_app.py` for `.js [data-static-save-fallback]` (if any) must be retargeted to the new selector text |
| D-10 beforeunload guard | `companion/static/dirty-state.js` — new `window.addEventListener("beforeunload", ...)` gated on `countDifferences() > 0`, cleared by the existing Save/Cancel paths | New check needed — none exists today |
| D-11 runway labels | `server/device_config.py`: `RUNWAYS` dict `"label"` values (~line 416-432) | Self-verifying, no retargeting needed (see Code Examples, D-11) |
| D-12 fieldset/aria groups | `companion/pages/config_page.py`: `_theme_chip_grid_html()` (~line 504-543), `runway_fieldset()` (~line 673-763) | New checks needed for `role="radiogroup"`/`aria-labelledby`/`aria-describedby` presence — none exist today (the multi-theme branch explicitly emits zero `<fieldset>`/`<legend>` today, per its own docstring) |
| D-13 next-wake countdown | New logic in `companion/pages/home_page.py` and `companion/pages/config_page.py` headers, using `ctx["device_config"]["wake_interval_s"]` or `ctx["wake_interval_env_default"]` or `device_config.DISPLAY_OFF_SLEEP_S` (when screen off) + last device check-in ts (`history_db.latest_device_health()`) + `layout.local_clock_text()` | New checks needed — none exist today |
| D-14 quiet-hours presets | `companion/pages/config_page.py`: `quiet_hours_group()` (~line 830-882), new preset `<button>`s; no server change (client-side fill only) | New checks needed for the three preset buttons' presence/values; `handle_post()`'s existing quiet-hours validation is untouched (presets submit through the same `quiet_hours_start`/`quiet_hours_end` fields) |
| D-15 lockout reset | `companion/auth.py`: `LoginThrottle.record_failure()` (~line 187-190) | `companion/test_companion_app.py`'s `_login_throttle_allows_locks_and_resets` (~line 798) stays valid; add a new check for the "fails again immediately after window elapses" case (see Wave 0 Gaps) |
| D-16 signing-key derivation + revocation | `companion/auth.py`: `issue_session_token()`/`verify_session_token()` (~line 92-125); new revocation-set module (location: Discretion) | `companion/test_companion_app.py`'s token round-trip/forged-token checks (~line 724-761) stay valid unmodified since they exercise the public `issue_session_token()`/`verify_session_token()` contract, not the internal key; add new revocation checks |
| D-17 conditional Secure cookie | `companion/auth.py`: `session_set_cookie_header()`/`logout_set_cookie_header()` (~line 128-149); new `SKYPANE_COMPANION_INSECURE_COOKIES` env check; `deploy/skypane.env.example` doc addition | `companion/test_companion_app.py`'s "session cookie header carries... Secure" check (~line 764) stays valid by default (env var unset in test harness); add a new check for the opt-out path |
| D-18 CSP + gate /ui-theme, /logout + redirect headers | `companion/app.py`: `_send_hardening_headers()` (~line 855), `redirect()` (~line 906-912), `do_POST()`'s `THEME_ROUTE`/`LOGOUT_ROUTE` branches (~line 2252-2256); `companion/pages/config_page.py`: externalize both inline scripts (~line 1192-1364) | New checks needed for CSP header presence/value, redirect-carries-headers, and the two now-gated routes' 303-to-login-when-unauthenticated behaviour — none of these exist today (confirmed: `redirect()` sends zero hardening headers currently, and `THEME_ROUTE`/`LOGOUT_ROUTE` have zero `require_session()` calls today) |
| D-19 drop Runway column, scroller a11y, shorter timestamp | `companion/pages/history_page.py`: `_HEADERS` tuple (~line 132-135, drop `"Runway"`), `_history_table_html()` (~line 668-719, drop the `tracked_runway` `<td>`, add `title=` to `<tr>`, add `tabindex="0"` + `aria-label` to `.data-table-wrap`), Timestamp cell (currently `layout.concise_timestamp_html()`, which includes a relative-age suffix — needs a shorter clock-only rendering) | `server/test_view_pages.py`/`companion/test_view_pages.py`'s 7-column-header check retargets to 6; any check asserting the Runway `<td>` position shifts |
| D-20 visible copy feedback + per-row accessible names + execCommand result check | `companion/static/copy-button.js`: `showFeedback()` (~line 55-64, currently writes only to the `visually-hidden` `data-copy-feedback` span), `fallbackCopy()` (~line 38-53, `document.execCommand("copy")`'s boolean return value is currently discarded); `companion/pages/history_page.py`: `_copy_button_html(value, label)` (~line 539-553, `label` needs the row's callsign folded in) | New checks needed — none exist today for visible feedback or execCommand result; existing checks asserting the static `"Copy callsign"`/`"Copy hex ID"`/`"Copy timestamp"` aria-labels must retarget to include the per-row callsign |
| D-21 "Unidentified airlines" strip + resolve-panel back link | `companion/pages/airlines_page.py`: `_gap_card_html()`/`_gallery_grid_html()` call site in `render()` (~line 1760-1836, needs a heading+sentence wrapper before the gap cards, currently prepended with no heading at all); `RESOLVE_BACK_LINK_TEXT`/`back_link` href (~line 299, 1540, currently `"← Back to Health"` / `href="/health"`) | `companion/test_view_pages.py`'s back-link-href-equals-`/health` check retargets to `/airlines`; no existing check pins "no heading before gap cards" (an absence, so nothing to retarget, only to add) |
| D-22 illustration forms only on `?edit=1` | `companion/pages/airlines_page.py`: `_lightbox_replace_form_html()` call site inside the shared dialog builder (~line 1104-1132, currently unconditional); `companion/pages/config_page.py`/Device page: new "Edit artwork" link to `/airlines?edit=1` | `companion/test_view_pages.py`'s checks asserting "exactly one lightbox replace form and one action="" and one file input" on every Airlines render must retarget to assert that shape ONLY when `?edit=1`, and assert its total absence otherwise |
| D-23 screen_id seam | `server/device_config.py`: `load_device_config()`/`save_device_config()` gain `screen_id` (new `normalise_screen_id()` against `screens.SCREEN_IDS`); `companion/app.py`: `page_context()` threads `ctx["screen_id"]` (~line 1043-1091, insert alongside the existing `device_config` read); `companion/pages/config_page.py`: `render()`'s existing `screens.current_screen_id(ctx)` call (~line 1722) and `handle_post()`'s existing `screens.current_screen_id(ctx)` call (~line 2056) already consume `ctx["screen_id"]` — **the seam is already built and already wired to these two call sites**, it is simply fed `None` today because nothing populates `ctx["screen_id"]` or `device_config.json`'s `screen_id` key yet | `server/test_config_history.py`'s full-config-dict equality checks (multiple, e.g. ~line 100, 116, 131, 144, 193, 225) currently assert an exact dict **without** a `screen_id` key — every one of these must add `"screen_id": "plane-frame"` to the expected dict or they will fail the moment `load_device_config()` starts returning an 11th key |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The CSP `style-src 'self'` vs. inline `style="background:..."` conflict has no resolution stated anywhere in 19-CONTEXT.md and must be decided before implementation | Pitfall 2 / Open Questions | If assumed away and shipped literally, every theme-chip/swatch colour preview silently disappears — a real, user-visible regression that could ship unnoticed |
| A2 | D-16's revocation set should be pruned by embedded token expiry, not left to grow unbounded for the 12h `SESSION_TTL_S` window | Pitfall 3 | Low risk either way at this traffic volume (one household), but an unbounded set is still worth avoiding on principle for a long-running process |
| A3 | D-18's inline-script externalization must cover both `_poll_cooldown_script()` AND `_poll_submit_script()`, even though D-18's own text names only "the poll-cooldown countdown" | Code Examples (D-18) | If only the countdown script is moved, the submit-affordance script remains an inline `<script>` that `script-src 'self'` will silently strip, breaking the "Polling…" disable-on-submit UX (cosmetic-only per its own docstring, but still a shipped-broken feature) |
| A4 | D-08's `submitted_calendar_signal()` gates 1-3 should be left in place (defensive/dead) rather than deleted, pending a grep confirming no other caller needs them | Pitfall 7 | If deleted prematurely and a second caller (the docstring names "plan 17-04's request handler") depends on them, that caller breaks |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **How should D-18's `style-src 'self'` be reconciled with the 7 existing `style="background:..."` attributes in `config_page.py`?**
   - What we know: the CSP string is locked verbatim in 19-CONTEXT.md D-18; the inline styles are pre-existing, render server-controlled (not user-supplied) hex values from a fixed 18-member registry.
   - What's unclear: whether the user intends `'unsafe-inline'` scoped to `style-src` only (simplest, smallest diff, technically still "no inline scripts" since `script-src` stays strict) or a CSS-class-based registry-driven refactor (zero exceptions, more code).
   - Recommendation: surface this explicitly at plan-check / discuss-phase time before Wave 1 starts on D-18 — do not let a plan silently pick one without the user confirming, since this is a locked decision's literal text producing a real visual regression if followed to the letter with no companion fix.

2. **Where should D-16's revocation set live — `auth.py` or `app.py`?**
   - What we know: 19-CONTEXT.md explicitly marks this as Claude's Discretion, with the one hard constraint that it "must be consulted from `require_session()`."
   - What's unclear: `auth.py`'s own docstring states it "must never import Pillow, sqlite3, or anything under server/" (a stdlib-only boundary) — a revocation set has no such import needs, so either location is equally valid on that axis; `app.py` already owns one comparable piece of shared mutable state (`_POLL_LOCK`), which is a mild precedent for putting it there instead.
   - Recommendation: default to `auth.py` (keeps all session-token logic, including its exceptions, in one module) unless the planner finds a reason `app.py` is cleaner; either is acceptable per the locked Discretion note.

3. **Does D-08's dedicated disconnect route need its own CSRF-equivalent confirm step beyond the native `confirm()`, given ASVS V4?**
   - What we know: the existing site-wide posture (SameSite=Strict, single-operator tool, no CSRF token anywhere) is explicitly accepted elsewhere in this codebase for every other state-changing route.
   - What's unclear: whether a destructive, hard-to-undo action (permanently erasing the fetched calendar registry) warrants anything beyond that baseline.
   - Recommendation: match the existing site-wide posture (no new CSRF token) — the native `confirm()` + a required `confirm=yes` hidden field is a misclick guard, not a security control, and this is consistent with D-08's own text framing it that way.

## Sources

### Primary (HIGH confidence — direct source read, 2026-09-11)
- `companion/pages/health_page.py` (full read, 2581 lines) — D-01..D-06
- `companion/pages/config_page.py` (targeted read, 2182 lines) — D-07..D-14, D-23
- `companion/pages/history_page.py` (targeted read, 902 lines) — D-19, D-20
- `companion/pages/airlines_page.py` (targeted read, 1839 lines) — D-21, D-22
- `companion/auth.py` (full read, 201 lines) — D-15..D-17
- `companion/app.py` (targeted read, 2370 lines) — D-07, D-16..D-18, D-23
- `companion/screens.py` (full read, 87 lines) — D-23
- `companion/layout.py` (targeted read) — `concise_timestamp_html()`/`local_clock_text()` for D-19
- `companion/static/freshness.js`, `battery-trend.js`, `copy-button.js`, `dirty-state.js` (full reads) — D-02, D-09, D-10, D-20
- `server/device_config.py` (targeted read, 961 lines) — D-11, D-23
- `companion/pages/__init__.py` (full read) — ctx contract for D-23/D-13
- `.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md`, `18-CONTEXT.md` — every finding's own evidence and Phase 18's locked decisions
- `.planning/phases/19-companion-audit-follow-through-fix-the-open-findings-from-18/19-CONTEXT.md` — the phase's locked decisions D-01..D-23
- `.planning/REQUIREMENTS.md`, `.planning/STATE.md`, `.planning/config.json` — requirement IDs, project history, workflow flags (`nyquist_validation: true`, `security_enforcement: true`, `security_asvs_level: 1`, `security_block_on: "high"`)
- Live harness execution, 2026-09-11: `server/.venv/bin/python3 companion/test_companion_app.py`, `test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`, `test_contrast_check.py`, `server/test_runway_config.py` — current pass/total counts as tabulated in Pitfall 1

### Secondary (MEDIUM confidence)
- None — no external documentation, library, or API was consulted; this phase is entirely internal-codebase research.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, verified by direct source read of every file this phase touches
- Architecture: HIGH — every decision's landing site verified by file:line read, not inferred from summaries
- Pitfalls: HIGH — every pitfall is grounded in a specific, quoted source comment or a direct grep count (e.g. "75 call sites," "7 style= occurrences")

**Research date:** 2026-09-11
**Valid until:** This research is tied to the exact commit state read on 2026-09-11; re-verify file:line references and `EXPECTED_CHECK_COUNT` values if planning is delayed more than a few days past this date or if any other phase/quick-task touches the same files first.
