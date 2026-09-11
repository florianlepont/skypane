# Phase 19: Companion audit follow-through — fix the open findings from 18-AUDIT.md - Context

**Gathered:** 2026-09-11
**Status:** Ready for planning
**Source:** PRD Express Path (`.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` — the audit ledger is this phase's requirements document; the developer asked, in their own words, to "reprendre la correction de l'ensemble des points de l'audit avec GSD")

<domain>
## Phase Boundary

Phase 18 audited the companion web app and fixed 18 of 46 consolidated findings in the same pass. This phase closes the rest of the **defects** — the 21 findings still marked `open` plus the remainder of the one marked `partial` — and takes the two **small** suggestions that are natural companions to those fixes. It stays inside `companion/` (pages, layout, static assets, tests) plus the two server modules a finding names directly (`server/device_config.py` for runway labels, `companion/auth.py` for the lockout). It does not touch the poll loop, the firmware, or the on-disk config format beyond what A-40 needs.

The audience framing from Phase 18 still governs every change: a second household member with basic computer skills uses the everyday pages (Home, Display, Flights, Airlines); the developer uses Advanced (Health, Device). A fix that makes a page more technical is the wrong fix.

</domain>

<decisions>
## Implementation Decisions

Every finding id below is an entry in 18-AUDIT.md; its evidence (file:line, screenshot, reviewer note) lives there and is not repeated. Each decision is locked unless marked Discretion.

### Health page (advanced, but must read in plain words)
- **D-01 (A-19):** Health's battery card shows the same estimated percentage Home already computes (`home_page.battery_percent()`, linear 3.3–4.2 V, labelled "≈") beside the mV readout. Move `battery_percent()` into a shared non-page module (`companion/battery.py`) so neither page module imports the other.
- **D-02 (A-20):** Replace `freshness.js`'s 45 s `location.reload()` with a fetch of the Health page and an in-place swap of the tiles/readout (`.dashboard-grid`, `.battery-readout`, the anomaly banner). The "Live — refreshed HH:MM (0s ago)" line becomes an honest "Updated HH:MM" that advances on each successful swap; a visible Pause/Resume control stops the polling; an open `<details>` no longer silently suspends it.
- **D-03 (A-21):** Every stat tile carries a short text verdict (ok/warn/error words) in addition to its border colour, the way Home's tiles already do — WCAG 1.4.1.
- **D-04 (A-22):** The battery sparkline uses a fixed 3000–4200 mV y-range (clamped), so a flat series draws flat and a 15 mV wiggle stays flat; the dense-point suppression threshold is derived from the rendered width (points per pixel), not a fixed 39-point count tuned for a 226 px canvas.
- **D-05 (A-23):** Device-staleness thresholds derive from the configured wake interval: warn after 3 missed wakes, error after 12, floor 5 min / 20 min, using `wake_interval_s` (or `SKYPANE_SLEEP_S`, or `DISPLAY_OFF_SLEEP_S` while the screen is off). A single ≥100 mV inter-reading dip is a **warn**, never a page-level error. `coverage_status` warn and an active source fault both feed `overall_severity`.
- **D-06 (A-24):** Health's captions and tile labels use plain language; the technical term stays as a `title` tooltip on the label. Concretely: "Corroboration" → "Do the two data sources agree?", "Agreement / Single-source (uncorroborated) / Disagreement" → "Both agree / Only one saw it / They disagree", "ADS-B pipeline last ran" → "Flight data last updated", "adsbdb" → "the route database", "Resolution rate" → "Flights we could name", and the "CFG-04's registry" sentence is rewritten without the requirement id.

### Settings pages (Display and Device)
- **D-07 (A-25):** A rejected save re-renders the page with the submitted values in the fields and a field-level error message under the offending control, instead of redirecting with one generic flash. Implement via a `?flash=save_failed` redirect that also carries no data — i.e. change the POST handler to render the page directly (200) on validation failure with an `errors` dict threaded through `config_page.render()`. The quiet-hours time inputs get `required`; an empty time is reported at the field, and never discards the rest of the form.
- **D-08 (A-26):** Disconnecting the calendar becomes its own `POST /settings/calendar/disconnect` form on the Device page, outside `#settings-form`, with a native confirm step (`<button>` + a `confirm()` in a tiny inline-free script, plus a server-side `confirm=yes` hidden field so the no-JS path still works via a two-step page). The checkbox is removed.
- **D-09 (A-27):** The static "Save settings" fallback button is hidden only once `dirty-state.js` has actually initialised the bar (that script adds a `dirty-ready` class), never on the mere presence of `.js`.
- **D-10 (A-28):** `dirty-state.js` installs a `beforeunload` guard while the form is dirty; the bar's own Save/Cancel clear it.
- **D-11 (A-29):** Runway card labels become "Runway 3 (07/25)", "Runway 4 (06/24)", "Runway 2 (02/20)" — `device_config.RUNWAYS[*]["label"]` — with the official ADP number kept in parentheses-free `tag_text`. `test_view_pages.py`'s label derivation check updates with it.
- **D-12 (A-30):** Theme chip grids and the runway row are wrapped in `<fieldset>` with a visually-hidden `<legend>` (or `role="radiogroup"` + `aria-labelledby` pointing at the group `<h2>`); every hint paragraph gets an id and its control an `aria-describedby`.
- **D-13 (A-31, S-02):** Home and Device show "Next wake ≈ HH:MM" computed from the last device check-in + the effective wake interval (`DISPLAY_OFF_SLEEP_S` while the screen is off), in Paris local time; "Applies on the next scheduled poll" captions gain "(next wake ≈ HH:MM)" where the value is known.
- **D-14 (S-04):** The Quiet hours group gets three preset buttons above the time inputs — "Night (23:00–07:00)", "Work day (08:00–18:00)", "Always on (off)" — that fill the inputs client-side and mark the form dirty; no server change.

### Auth and shell
- **D-15 (A-32):** `auth.record_failure()` resets the failure counter once the lockout window has elapsed, so a lockout is 5 fresh failures per window, never permanent. Keep the process-global throttle (one shared password).
- **D-16 (A-33):** Session tokens are HMAC-signed with a key derived from the password via a per-process random salt generated at startup (so a leaked cookie is not an offline password oracle), and Sign out adds the token to a small in-memory revocation set consulted by `verify_session()`. A restart invalidates every session; acceptable for one household.
- **D-17 (A-34):** `Secure` on both cookies follows `SKYPANE_COMPANION_INSECURE_COOKIES=1` (dev/LAN only, documented in `deploy/skypane.env.example` as never-set-in-production).
- **D-18 (A-35):** Every response, redirects included, carries the hardening headers plus a `Content-Security-Policy` of `default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; form-action 'self'; frame-ancestors 'none'` — the app has no inline scripts or styles except the poll-cooldown countdown, which moves to `static/poll-cooldown.js` reading a `data-cooldown` attribute. `POST /ui-theme` and `POST /logout` require a valid session cookie.

### Flights and Airlines
- **D-19 (A-36):** The Flights table drops the Runway column (one tracked runway; it stays in the mobile card's "More details" and the row's `title`), the scroller gets `tabindex="0"` and an accessible name, and the timestamp column shortens to the local clock.
- **D-20 (A-37):** Copy buttons show a visible transient "Copied" state (text swap for 1.5 s), carry the row's callsign in their accessible name, and only report success when `execCommand`/`clipboard.writeText` actually succeeded.
- **D-21 (A-38):** Gap cards move out of the main grid into an "Unidentified airlines" strip at the top of Airlines with one plain sentence ("The frame saw these callsigns but doesn't know the airline. Tap one to name it."); the resolve panel's back link returns to Airlines.
- **D-22 (A-39):** The illustration replace/upload/delete forms render in the Airlines lightbox only when the page is opened with `?edit=1` (a link "Edit artwork" on the Device page); the everyday lightbox is view-only.

### Screens seam (A-40 remainder)
- **D-23 (A-40):** `device_config` gains `screen_id` (default `"plane-frame"`, normalised against `screens.SCREEN_IDS`); `page_context()` threads it as `ctx["screen_id"]`; the Display/Device headers render a screen selector `<select>` only when `len(SCREEN_IDS) > 1`. No second screen type is added; this closes the seam so the next screen type is a registry entry plus its groups.

### Claude's Discretion
- Exact copy of the plain-language Health labels beyond the mapping in D-06, the CSP header's exact directive order, the shape of the field-level error markup (must reuse the existing `--color-status-error` token and the label voice), test check counts.
- Whether D-16's revocation set lives in `auth.py` or `app.py` (it must be consulted from `require_session()`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The audit itself
- `.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` — every finding with evidence; the status column is the ground truth for what this phase closes.
- `.planning/phases/18-companion-audit-and-ux-refactor/18-CONTEXT.md` — Phase 18's decisions D-01..D-08 (nav groups, Home widgets, scoped settings form, screens seam, local time); this phase must not undo any of them.
- `.planning/phases/18-companion-audit-and-ux-refactor/18-01-SUMMARY.md` — what Phase 18 shipped and how it was verified.

### Design system
- `.claude/skills/sketch-findings-skypane/SKILL.md` and its `references/` — the companion's design contract (tokens, label voice, accent reservation, card set, touch-target register). No new tokens; no new accent consumer.

### Code the decisions name
- `companion/pages/health_page.py`, `companion/static/freshness.js`, `companion/static/battery-trend.js` — D-01..D-06
- `companion/pages/config_page.py`, `companion/static/dirty-state.js`, `companion/screens.py` — D-07..D-14, D-23
- `companion/auth.py`, `companion/app.py` — D-15..D-18
- `companion/pages/history_page.py`, `companion/static/copy-button.js`, `companion/pages/airlines_page.py`, `companion/static/panel-lookup.js` — D-19..D-22
- `server/device_config.py` — D-11, D-23
- `scripts/run-all-tests.sh`, `companion/test_*.py` — every harness pins an `EXPECTED_CHECK_COUNT`; each plan must re-derive it by running the harness.

</canonical_refs>

<specifics>
## Specific Ideas

- Home's `FRAME_STATE_TEXT` / `DATA_STATE_TEXT` / `BATTERY_STATE_TEXT` dictionaries are the tone to match on Health.
- The five checks that fail in a root-running sandbox (read-only-directory cases, `anomaly_active()` non-existent dir) are pre-existing and pass in CI; a plan must not "fix" them by weakening the tests.
- Times are Europe/Paris everywhere visible (Phase 18 D-06); "next wake" must use `layout.local_clock_text()`.

</specifics>

<deferred>
## Deferred Ideas

The four larger suggestions from 18-AUDIT.md are each a phase of their own and are added to the roadmap as Phase 20, not folded in here:
- S-01 French localisation of the companion
- S-03 Theme picker as a carousel with a live preview of the current flight
- S-05 Notifications (battery low, frame silent)
- S-06 Per-person entry point / simple mode

Also deferred: a calibrated battery curve (D-01 keeps the linear estimate until Phase 5's discharge run yields data); per-IP login throttling (D-15 keeps the global counter).

</deferred>

---

*Phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18*
*Context gathered: 2026-09-11 via PRD Express Path*
