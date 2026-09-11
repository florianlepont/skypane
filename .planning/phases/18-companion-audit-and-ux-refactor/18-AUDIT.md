# Phase 18: Companion audit & UX refactor — Audit ledger

**Gathered:** 2026-09-10
**Method:** the companion was run locally against a seeded state directory (40 days of battery readings, 24 runway events, three unresolved prefixes, one manual resolution, four gallery renders) and every page, dialog and state was screenshotted at 1280px and 390px in light and dark mode with Playwright; in parallel, three read-only code reviews covered `config_page.py` + `dirty-state.js`, `health_page.py` + `history_page.py` + their scripts, and `airlines_page.py` + `layout.py` + `app.py` + `auth.py` + `panel-lookup.js`. Roughly 120 raw findings were consolidated into the 46 entries below. The live tracking board is the "SkyPane Companion Audit" artifact published with this phase.

**Audience framing:** a second household member with basic computer skills will use the companion. Every finding is judged against "can they use this without an explanation?" as well as against correctness.

## Fixed in this phase (18)

| ID | Area | Severity | Status | Finding | Fix / next step |
|---|---|---|---|---|---|
| A-01 | Navigation | high | fixed | No home page — login lands on the Settings form; no page answers "what is my frame showing?" | New Home page (companion/pages/home_page.py): status tiles, quick actions, current panel, recent flights. Login and 404 now land on Home. |
| A-02 | Navigation | high | fixed | Everyday and debug functions mixed on every tab | Two nav groups: everyday (Home, Display, Flights, Airlines) and Advanced (Health, Device). Settings split into Display (theme, quiet hours, screen on/off) and Device (runway, LED, wake interval, calendar, colour rules, manual refresh) per companion/screens.py. |
| A-03 | Settings | high | fixed | Switching the screen off required a full valid Save of nine unrelated fields | One-tap Screen on/off, Quiet hours on/off and Refresh now widgets on Home (POST /quick/display, /quick/quiet-hours, /poll-now) — idempotent, no Save step. |
| A-04 | Settings | high | fixed | On phones the only Save button sat at the very bottom of the page | Save bar pinned at every width (safe-area aware). |
| A-05 | Settings | high | fixed | Wake interval placeholder truncated to "Uses se" | Explicit widths for settings number/url/text/time inputs. |
| A-06 | Settings | medium | fixed | 18 theme chips stacked in a single 160px column on phones (page ≈ 5,700px tall) | Two chips per row below 960px; chip names no longer wrap. |
| A-07 | Airlines | high | fixed | A manually-resolved airline without artwork rendered a broken, link-styled image | Dashed placeholder (same as gap cards), empty dialog src, link styling reset on a.airline-card__zoom. |
| A-08 | Airlines | medium | fixed | Resolve flow rendered twice: in-page section visible behind the auto-opened modal | panel-lookup.js hides [data-resolve-fallback] once the dialog auto-opens; backdrop click closes any lightbox. |
| A-09 | Flights | high | fixed | Timestamps were bare UTC clocks with no date and no local time | layout.local_clock_text(): Europe/Paris local time, with the day when not today; full ISO kept in the title attribute. |
| A-10 | Flights | medium | fixed | Lightbox caption and alt text were raw ISO strings ("Panel near 2026-09-10T21:38:48+00:00") | lightbox_caption_text(): "Picture from 10 Sep 23:38". |
| A-11 | Flights | medium | fixed | Lightbox <img src=""> fired a spurious GET of the page as an image; dialogs had no accessible name | img rendered without src until opened; aria-label on both dialogs. |
| A-12 | Health | high | fixed | Sparkline hover highlight never applied: _toggleActive wrote className on SVG circles (read-only SVGAnimatedString, throws under strict mode) | classList with a setAttribute fallback. |
| A-13 | Shell | high | fixed | flash-cleanup.js dropped the whole query string, losing ?resolve= on reload | Strips only flash and rule; keeps every other parameter and the fragment. |
| A-14 | Shell | high | fixed | Authenticated HTML pages carried no Cache-Control — replayable from the back button after sign-out | Cache-Control: no-store on every HTML response. |
| A-15 | Copy | medium | fixed | "Poll triggered — refresh this page…" asked the user to do the app's job, on a page that shows no result | "Refreshing — the frame's new picture will appear on Home within a few seconds." and the trigger redirects back to the page it came from (Home or Device). |
| A-16 | Copy | low | fixed | "Health history is temporarily unavailable — check the companion service logs" shown on the Flights page | "The flight list is temporarily unavailable — try again in a minute." |
| A-17 | Copy | low | fixed | "View 1 readings"; group heading "Display" inside the Display page; section "Poll" | Singular form; group renamed "Screen on / off"; section renamed "Manual refresh". |
| A-18 | Flights | low | fixed | Filter bar's Clear control wrapped alone under the count on phones | Count pushed right, Clear kept on the same line. |

## Partially addressed (1)

| ID | Area | Severity | Status | Finding | Fix / next step |
|---|---|---|---|---|---|
| A-40 | Navigation | medium | partial | Several screen types will each need their own settings | companion/screens.py declares per-screen-type settings groups and the Display/Device pages are composed from it; the pages carry a "Screen: Plane frame" caption. Remaining: per-screen state directory or config key, a screen selector in the header, per-screen poll/cooldown. |

## Open — backlog, by severity (21)

| ID | Area | Severity | Status | Finding | Fix / next step |
|---|---|---|---|---|---|
| A-19 | Health | high | open | Battery is millivolts only — no percentage, no verdict a non-technical user can act on | Backlog: adopt the same estimate on Health, or a calibrated curve once the discharge run (Phase 5) yields real data. |
| A-20 | Health | high | open | Health auto-reloads the whole page every 45 s with no opt-out; "Live — refreshed (0s ago)" is structurally always 0s and pauses silently while any disclosure is open | Backlog: fetch-and-swap the tiles instead of location.reload(); honest refresh label; pause control. |
| A-25 | Settings | high | open | A rejected save throws away everything typed and shows one generic message; clearing a time field kills the whole save | Backlog: field-level errors and repopulation; required on the time inputs. |
| A-26 | Settings | high | open | "Disconnect this calendar and delete the flights it supplied" is an ordinary checkbox with no confirmation | Backlog: a dedicated Disconnect button with a confirm step, outside the settings form. |
| A-32 | Auth | high | open | Lockout never resets: after 5 failures every later wrong password re-arms a fresh 300 s lockout forever; one shared password means anyone can lock the owner out | Backlog: reset the counter when the lockout expires; consider per-IP throttling. |
| A-21 | Health | medium | open | Tile status is colour-only (border + icon tint) — WCAG 1.4.1 | Backlog: reinstate a text verdict inside each tile (Home's tiles already carry one). |
| A-22 | Health | medium | open | Sparkline auto-scales min–max (a 15 mV wiggle looks like a cliff; a flat series pins to the bottom); dot suppression tuned for a 226px canvas applies at every width | Backlog: fixed 3000–4200 mV range; width-aware density threshold. |
| A-23 | Health | medium | open | Thresholds: device staleness warn at 1 h / error at 6 h against a 30 s cadence; a single ≥100 mV dip escalates to page-level error; coverage warn and source fault are excluded from overall severity | Backlog: derive thresholds from wake_interval_s; demote the dip to warn; fold the two excluded signals in. |
| A-24 | Health | medium | open | Jargon a household member cannot parse: Corroboration / Agreement / Single-source, ADS-B pipeline, adsbdb, Resolution rate, "CFG-04's registry" | Backlog: plain-language captions on Health, keep the technical terms in tooltips. |
| A-27 | Settings | medium | open | Any JS hiccup leaves no way to save: the fallback button hides on .js presence, the bar is produced by a different file that can bail | Backlog: hide the fallback only once the bar exists. |
| A-28 | Settings | medium | open | Add rule / Delete / Trigger poll navigate away and discard unsaved edits; no beforeunload guard | Backlog: beforeunload guard while dirty. |
| A-29 | Settings | medium | open | Runway cards say "Piste 3 / 4 / 2" (French, ADP numbering) while everything else says Runway 3 / 06-24 / 02-20 | Backlog: "Runway 3 (07/25)"-style labels, or a full French localisation (see S-01). |
| A-30 | Settings | medium | open | Chip grids and runway cards have no group semantics (no fieldset/legend or role=radiogroup); hints not linked via aria-describedby | Backlog. |
| A-31 | Settings | medium | open | "Applies on the next scheduled poll" is unquantified — the page never shows when the next wake is | Backlog: compute and show "next wake ≈ HH:MM" from wake_interval_s and the last check-in (Home is the natural place). |
| A-33 | Auth | medium | open | Session tokens are stateless HMACs keyed by the password itself; Sign out only deletes the client cookie | Backlog: derive the key from a separate secret; a small server-side revocation list. |
| A-35 | Shell | medium | open | No Content-Security-Policy; redirects skip the hardening headers; POST /ui-theme and /logout are un-gated and token-less | Backlog. |
| A-36 | Flights | medium | open | The 7-column table needs 1,305px inside an 880px column at 1280px: it scrolls, but the affordance is a 12px shadow and keyboard users cannot reach columns 5–7 | Backlog: tabindex=0 on the scroller, drop the Runway column (single runway today), narrower timestamp. |
| A-38 | Airlines | medium | open | Gap cards sit head-of-grid with no heading or sentence explaining what they are; "← Back to Health" is the wrong return for the common path | Backlog: an "Unidentified airlines" strip with one sentence; back link to Airlines. |
| A-34 | Auth | low | open | Secure cookie flag is unconditional — a plain-http LAN/dev run silently bounces back to /login | Backlog: an explicit dev flag, or honour X-Forwarded-Proto. |
| A-37 | Flights | low | open | Copy confirmation is invisible to sighted users; all 50 rows share identical accessible names; execCommand result ignored | Backlog. |
| A-39 | Airlines | low | open | Illustration replace/upload/delete forms live in the everyday Airlines lightbox | Backlog: show the replace zone only from Device (or behind an "Edit artwork" toggle). |

## Suggestions (6)

| ID | Area | Severity | Status | Finding | Fix / next step |
|---|---|---|---|---|---|
| S-01 | Suggestion | suggestion | open | French localisation | A small gettext-style dictionary keyed by the existing constants, with a language toggle in the nav footer next to the theme picker. |
| S-02 | Suggestion | suggestion | open | Next-wake countdown on Home | Derive from the last check-in + wake_interval_s (or DISPLAY_OFF_SLEEP_S while off). |
| S-03 | Suggestion | suggestion | open | Theme picker as a carousel with a live preview of the current flight | Reuse theme_preview.py with the latest runway_events row. |
| S-04 | Suggestion | suggestion | open | Schedule presets for quiet hours |  |
| S-05 | Suggestion | suggestion | open | Notifications for the two things that matter: battery low and frame silent | A daily digest e-mail or a ntfy/Pushover hook from the poll loop. |
| S-06 | Suggestion | suggestion | open | Per-person entry point |  |

## Pre-existing harness failures (not this phase's)

Five checks in `server/test_manual_resolutions.py`, `companion/test_companion_app.py` and `companion/test_status_pages.py` fail identically on the untouched `main` in this sandbox because it runs as root: the read-only-directory cases cannot trip, and `anomaly_active()`'s non-existent-state-dir case resolves differently. They pass in CI's unprivileged runner and are outside this phase's scope.
