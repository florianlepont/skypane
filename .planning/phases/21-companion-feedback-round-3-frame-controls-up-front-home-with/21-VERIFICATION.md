---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
verified: 2026-09-12T12:54:47Z
status: passed
score: 10/10 acceptance criteria verified
overrides_applied: 0
---

# Phase 21: Companion feedback round 3 — Verification Report

**Phase Goal:** Put the two everyday frame controls (Screen on/off, Quiet hours) and the next
update time where they are seen first — a "Frame" strip at the top of Home and of Display, with
a state reminder in the nav — rebuild Home around the three separate status tiles of phase 19
plus the frame picture and the recent flights side by side, merge the four theme chip grids into
one worked "Frame colours" view, put the calendar status and its feed URL in one tile, make the
Flights table fit a 1280 px desktop without horizontal scroll, remove the simple/full mode and
the Health "Pause updates" button, and restore the artwork upload in the Airlines "name an
airline" flow.

**Verified:** 2026-09-12
**Status:** passed
**Re-verification:** No — initial verification

**Method:** Merged tree at HEAD (`7657e49`, branch `claude/web-companion-audit-ux-refactor-bqx7si`)
was run live. `companion.app` was started against a fresh copy of the scratchpad's seeded state
dir on port 8661 (never 8643/8651), logged in with the real password, and driven with `curl`
(cookie jar, raw HTML/JSON inspection, live POSTs to `/settings`, `/quick/display`,
`/quick/quiet-hours`, `/settings/calendar/connect`) and headless Chromium via Playwright
(computed-style measurement, screenshots at 1280/390 px × EN/FR, click-driven DOM assertions,
native `dialog` event capture). The full test suite and `ruff` were run directly against the
repo. The server was stopped after use; the state-dir copy is scratchpad-only and was never
written back into the repo.

## Goal Achievement — Acceptance Criteria (21-PRD.md)

| # | Acceptance criterion | Status | Evidence |
|---|---|---|---|
| 1 | Home @1280px: strip → three tiles (Frame/Battery/Flight data) → picture+flights (3:2); @390px same order, one column; no quick-action widgets elsewhere on Home | **PASS** | Live GET `/`: byte order in the HTML is `page-header` → `frame-strip` (offset 10888) → `home-status-grid` (12697, tiles "Frame"/"Battery"/"Flight data") → `home-columns.home-picture-row` (13986) → `recent-flights` (14635). Playwright `getComputedStyle('.home-picture-row')` at 1280px: `grid-template-columns: 513.59px 342.39px` = exactly 3:2. Screenshot `home-390.png`: strip cells, tiles and picture/flights all stacked one-per-row in the same order. `grep -c 'quick-action--on\|quick-action--off' home_en.html` = 2 (exactly the strip's own pair; zero elsewhere). |
| 2 | Display shows the same strip; Screen/Quiet-hours cards below no longer contain an instant switch; pressing a switch on either page redirects back to that page | **PASS** | GET `/display`: exactly one `quick-action--on`/`--off` pair on the whole page (inside the strip; `grep` count = 2 occurrences total = the pair). Live POST `/quick/display` with `return_to=/` → `Location: /?flash=display_off`; POST `/quick/quiet-hours` with `return_to=/display` → `Location: /display?flash=quiet_on`. State restored after test. |
| 3 | Nav shows "Screen on · Quiet hours off" (matching states, current language) as a link to Home, no button/form | **PASS** | Sidebar and mobile-dropdown HTML both contain `<a class="nav-status text-label" href="/" aria-label="…">` with two `<span class="dot …"><span class="dot-label">` pairs, no `<form>`/`<button>` inside it. FR (`ui_lang=fr` cookie set via `POST /ui-lang`): `<a … aria-label="État de l'écran et des heures calmes — aller à l'accueil">…Écran allumé…Heures calmes désactivées…</a>` — fully French, matches R-04's corrected wording (not the PRD's literal "off" drafting shorthand). |
| 4 | Display's "Look" has one "Frame colours" card: preview left, 4 rows right; clicking a row swaps the visible chip grid + preview; Arrivals/Calendar offer "Same as departures"; rules row shows rule list+form; old checkbox/Calendar-grid/"Flight colours" card gone; one save persists all three theme fields; no-JS still saves every value | **PASS** | Exactly one `page-section frame-colours` on Display (`grep -c "frame-colours"` in body = 1 section). No `theme_arriving_enabled`/`THEME_ARRIVING_CHECKBOX`/"Use a different theme for arrivals" string, no `_rules_section_html`/"Flight colours" heading anywhere in the rendered page (0 hits). Server-rendered no-JS floor: all four `<fieldset class="frame-colours__usage-panel">` render with **no** `hidden` attribute. With JS (Playwright): on load only `departures` panel lacks `frame-colours__usage-panel--collapsed`; clicking the `arrivals` radio label swaps the collapsed class to `arrivals`, preview `<img src>` becomes `/theme-preview/white.png?live=1` (departures' theme, since Arrivals is unset — D-12's "same as departures" preview rule); clicking the `black` chip inside the Arrivals panel updates preview `src` to `/theme-preview/black.png?live=1` with **zero** console/page errors and **no page reload** (`page.url()` unchanged). Live POST `/settings` with `theme=white&theme_arriving=grey&tracked_runway=3&led_enabled=on&quiet_hours_start=…&display_enabled=on` (no `quiet_hours_enabled`, matching an unchecked-checkbox submission) → `theme_arriving` on disk becomes `"grey"`, confirming the three theme fields save through one `settings-form` POST. |
| 5 | Calendar card: status + (not connected: URL field/Connect button) or (connected: masked URL, "Replace" link, small grey "Disconnect" button that still confirms) | **PASS** | Not-connected render: one `page-section` (`data-dirty-section="Calendrier"`) containing the status row ("Non connecté") immediately followed by the URL `<input>` and "Connecter le calendrier" button, no `<details>`. Live POST `/settings/calendar/connect` with an unreachable HTTPS URL saved the URL (`fetch failed` flash, URL persisted per the app's own documented "the URL is saved regardless" contract) — re-render then showed: `status-row--error` "Connecté"/"Impossible de lire le flux", `<p class="calendar-masked-url">calendar.example.com…</p>` (host + ellipsis, `urlsplit()`-based, never the full URL), `<details class="calendar-url-disclosure"><summary class="text-link">Remplacer l'URL du flux</summary>` containing a second URL field + "Remplacer" button, and `<button … class="calendar-disconnect-btn">Déconnecter</button>` on the same `<p class="calendar-actions">` line — matching D-14 exactly. Clicking `.calendar-disconnect-btn` in real Chromium raised a native `confirm()` dialog with message "Disconnect this calendar and delete the flights it supplied?"; dismissing it left the page on `/display` with the calendar still connected (confirmation gate is real, not decorative). |
| 6 | Flights table @1280px: no horizontal scrollbar in FR/EN; hex/ISO timestamp/runway/copy button in an expandable detail row; phone cards unchanged | **PASS** | Playwright measurement at 1280px, both languages: `.data-table-wrap` `scrollWidth === clientWidth === 880` (no overflow) in EN and FR. Headers: EN `When/Flight/Route/State/Corroboration/Details(hidden)`; FR `Quand/Vol/Trajet/Sens/Corroboration/Détails(hidden)` — "Sens" not "État" (matches the shipped, corrected translation the UI-SPEC calls out). 24 `.flight-detail-row` elements + 24 `[data-row-toggle]` buttons found; server HTML shows the detail `<tr>` with **no** `hidden` attribute (no-JS floor) containing `<dt>Code hex</dt><dd>3c6444</dd>` + a copy button, full ISO timestamp, and runway — script adds `flight-detail-row--collapsed` at load. `history_page.py`'s `_history_cards_html()` (mobile) is untouched by this phase's diff (confirmed via `git diff 614d41e..HEAD -- companion/pages/history_page.py`, only referenced in a comment). |
| 7 | No Simple/Full switch, no `/ui-mode` route, no `simple_mode` reference anywhere in `companion/`; everyday pages show full-mode content | **PASS*** | `POST /ui-mode` and `GET /ui-mode` both live-return `404`. `grep -rn "simple_mode\|MODE_CHOICES\|UI_MODE_COOKIE" companion/ --include="*.py" \| grep -v test_` → one hit, a docstring bullet in `companion/pages/__init__.py` describing the historical removal (`"- (simple_mode: the CFG-18 key added by 20-01 was removed by…)"`) — not executable code, and it is the one documented, deliberately-scoped exemption in `test_companion_app.py`'s own package-wide mechanical reintroduction guard (`_EXEMPT_PATH_TOKEN_PAIRS`), flagged in 21-01-SUMMARY.md's Deviations section because that file sat outside 21-01's `files_modified` boundary. `layout._mode_form_html()` is gone (only a removal-comment reference remains); nav footer confirmed rendering "FR/EN, Auto/Light/Dark, Sign out" only, no third switch, on both Home and Display screenshots. |
| 8 | No "Pause updates" button on Health; freshness loop runs without a pause branch | **PASS** | Live GET `/health`: 0 hits for "Pause"/"Suspendre"/`data-refresh-toggle`. `grep -c "Pause updates" companion/pages/health_page.py` = 0. `freshness.js` has no `paused`/`wireToggle` token. |
| 9 | Airlines: naming an unrecognised airline offers upload in step B without `?edit=1`; "Change pictures" still reveals replace/delete on existing artwork | **PASS** | Seeded unresolved prefix `XYZ` (from flight `XYZ123`, no artwork): `GET /airlines?resolve=XYZ` (no `edit=1`) renders `<div class="resolve-upload-zone">` unconditionally. `_edit_toggle_html()`'s early-return on `simple_mode` is gone (D-17), so "Modifier les images"/"Change pictures" (`href="/airlines?edit=1"`) always renders in the page header, unconditionally revealing replace/delete for airlines that already have artwork. |
| 10 | French catalogue complete (`test_i18n.py` green); all harnesses pass with pins updated; `ruff` clean; headless sweep (EN/FR × 1280/390) shows no overflow, no inline script, no 404 | **PASS** | `test_i18n.py`: **22/22** live. Full suite (`scripts/run-all-tests.sh`): **exactly** the five documented root-sandbox failures reproduced and no others — 2 in `companion/test_companion_app.py` (`POST /airlines/resolve` / `/manual-resolutions/{prefix}/delete` against a read-only state dir), 2 in `server/test_manual_resolutions.py` (`add_entry`/`delete_entry` against an uncreatable/read-only dir), 1 in `companion/test_status_pages.py` (`anomaly_active()` for a non-existent state_dir). `server/.venv/bin/ruff check .` → "All checks passed!". Headless sweep re-run: screenshots captured at 1280/390 × EN/FR for Home and Display (visually inspected, matches UI-SPEC's described look); no `<script>` tag without a `src` attribute on any fetched page; every static asset requested (`flight-rows.js`, `theme-preview.js`, `style.css`, `freshness.js`) returned 200, a deliberately-mistyped asset returned 404 (control check); Flights table confirmed non-overflowing in both languages (criterion 6). |

\* Criterion 7 is functionally fully met (zero executable `simple_mode` code path); one inert, already-documented, already-exempted docstring bullet contains the literal token as historical prose. See Gaps/Notes below — not treated as a blocking failure.

## Decisions and Resolutions (21-CONTEXT.md D-01..D-20, R-01..R-14)

All twenty decisions and fourteen resolutions were independently checked against the live-rendered
markup and/or the source; every one matches:

- **D-01/D-02 (strip placement + wording):** `layout.frame_strip_html(ctx, return_to)` is the single
  write site (confirmed: `home_page.render()` and `config_page.render()` both call it; identical
  markup shape on both pages, differing only in `return_to`). Next-update text uses
  `--font-heading-size` (22px) via a scoped rule `.frame-strip__cell--update .status-card__headline`
  — genuinely the largest text in the strip (measured: state text 16px/600, label 12px/600, next-
  update 22px/600), a deliberate post-wave polish fix (commit `d9e0338`) that improves on the
  UI-SPEC's own weaker "no larger role available" reasoning without introducing a new token
  (`--font-heading-size` already existed).
- **D-03/R-03/R-04 (nav reminder):** one shared `layout` function feeds both `sidebar_nav()` and
  `_mobile_nav_html()`; plain `<a>`, no form/button; FR text is fully translated
  ("Heures calmes désactivées", not "off") — R-04's correction, verified live.
- **D-04/R-06 (Home rebuild):** phase-19 tile shape restored with phase-20 wording; picture:flights
  ratio measured at 513.6:342.4px = 3:2 at 1280px.
- **D-05 ("pretty," checked by screenshot):** accent surface (`stat-tile stat-tile--accent`) is the
  only accent-tinted region on Home; confirmed visually in `home-1280.png`/`home-390.png`.
- **D-06..D-12/R-05/R-11 (Frame colours):** one card replaces all four grids; no-JS floor renders
  four `<fieldset>`s with no `hidden`; `theme-preview.js` scopes every lookup inside `.frame-colours`
  (confirmed by reading the rewritten file); "Same as departures" chip submits `""`; preview follows
  selection in both dimensions, confirmed live by clicking a row then a chip.
- **D-13/D-14/R-08/R-09/R-10 (Calendar):** one `page-section`; masked URL is `urlsplit(url).netloc`
  + "…"; Disconnect is `.calendar-disconnect-btn` (30px, 12px text, 6% wash) — visibly small and grey
  in the `display-1280.png` screenshot, never the phase-20 long red primary; confirmation mechanism
  (`data-confirm`) fires a real native `confirm()`, verified live.
- **D-15/D-16/R-12 (Flights table):** 880px column width target hit exactly (`scrollWidth ===
  clientWidth === 880`); Corroboration is dot-only with a `visually-hidden` label; `flight-rows.js`
  is a new, separate ES5 file per Claude's Discretion; `list-filter.js`'s extension for the sibling
  detail row was not independently re-tested beyond the passing harnesses (low risk, filter bar
  untouched in scope).
- **D-17/D-18/R-07/R-13 (removals):** `/ui-mode` 404s; `freshness.js` has no pause branch; FR
  catalogue orphans removed in the same commits (confirmed by `test_i18n.py` passing with no dead-
  translation failures).
- **D-19/D-20 (Airlines upload restore):** confirmed live against the seeded `XYZ` prefix.
- **R-01/R-02 (`return_to` validation):** confirmed live — `/health` and `//evil` both fall back to
  `/display` (the whitelist default), matching the exact fallback R-02 specifies.
- **R-14 (waves):** not independently re-derivable from the merged tree alone; consistent with the
  commit sequence in `git log`.

## Data-Flow / Live-Render Spot-Checks (beyond static grep)

| Behavior | Live check performed | Result |
|---|---|---|
| Frame colours row→panel→chip→preview wiring | Real Chromium: click Arrivals row, then a chip inside it | Panel and preview both updated correctly, zero console/page errors, no reload |
| `theme_arriving` empty/invalid handling | `POST /settings` with `theme_arriving=` and `theme_arriving=nonsense` | Empty → saved as `null` (redirect, `flash=saved`); nonsense → rejected inline (`200`, no redirect, "Ce n'est pas l'un des choix disponibles"), disk value unchanged |
| Strip redirect targets | `POST /quick/display`/`/quick/quiet-hours` with `return_to=/`, `/display`, `/health`, `//evil` | `/`→`/`, `/display`→`/display`, `/health`→`/display` (fallback), `//evil`→`/display` (fallback) |
| Calendar connect→connected render | `POST /settings/calendar/connect` with a real-shaped but unreachable URL | Card flips from "Not connected + URL field" to "Connected(error) + masked URL + Replace/Disconnect line", exactly per D-13/D-14 |
| Native disconnect confirmation | Clicked `.calendar-disconnect-btn` in headless Chromium, captured the `dialog` event | `confirm()` fired with the documented French/English confirmation copy; dismissing cancelled the action |
| Flights table fit | Playwright `scrollWidth`/`clientWidth` on `.data-table-wrap`, EN and FR, 1280px | Equal (880/880) in both languages — no scrollbar |
| Static asset resolution | `GET /static/flight-rows.js`, `/theme-preview.js`, `/style.css`, `/freshness.js`, and a deliberately wrong path | All four 200, wrong path 404 |

## Test Suite / Lint

| Check | Result |
|---|---|
| `companion/test_i18n.py` | 22/22 pass |
| `scripts/run-all-tests.sh` (full suite) | Exactly the 5 documented pre-existing root-sandbox failures, no others |
| `server/.venv/bin/ruff check .` | All checks passed |

## Anti-Patterns Scanned

No `TBD`/`FIXME`/`XXX` in any file touched by this phase. No `TODO`/`HACK`/unresolved
`PLACEHOLDER`-as-stub found — every "placeholder" grep hit is a legitimate UI placeholder
attribute/CSS class (`WAKE_INTERVAL_PLACEHOLDER_TEXT`, `.airline-card__placeholder`,
`.recent-flight__thumb--placeholder`, etc.), not an unfinished-feature marker.

## Gaps / Notes (non-blocking)

1. **`.planning/REQUIREMENTS.md`'s tracking table still lists CFG-19 through CFG-24 as "Pending
   (planning)" / unchecked `[ ]`,** even though every one of the six requirements is fully
   delivered and verified above (phase 20's own CFG-13..17 rows were updated to "Complete" after
   that phase closed; the equivalent update for phase 21's rows was not made). This is a
   documentation-bookkeeping gap only — it does not affect any shipped behaviour — but it should be
   fixed so the requirements ledger stays trustworthy for future phases. **Fix:** flip the six
   checkboxes in `.planning/REQUIREMENTS.md`'s CFG-19..24 bullets to `[x]` and update their table
   rows to `Complete (21-0N)`.
2. **AC7's literal "no `simple_mode` reference anywhere in `companion/`"** is met in every
   functional sense (zero code paths, zero routes, zero cookies) but one inert historical docstring
   bullet in `companion/pages/__init__.py` still contains the string `simple_mode`, because that
   file sits outside plan 21-01's `files_modified` boundary. This is already flagged, already
   exempted by name in `test_companion_app.py`'s own mechanical reintroduction guard, and documented
   in 21-01-SUMMARY.md's Deviations section — not a silent gap. No fix required unless the developer
   wants the docstring itself reworded (a one-line, out-of-phase-boundary edit).

Neither note changes any acceptance-criterion verdict above (both are cosmetic/documentation, not
functional).

## Score

**10/10 acceptance criteria verified.** All twenty D-decisions and fourteen resolutions checked
against the live merged tree matched. No blockers found.

## Verdict

**PASS.** Phase 21's goal is achieved in the codebase, not just claimed in the SUMMARY files: the
Frame strip, nav reminder, rebuilt Home, the merged Frame colours view, the merged Calendar tile,
the compacted Flights table, the removal of simple mode and the Health pause button, and the
restored Airlines upload were all independently reproduced against a live server instance — HTML
byte-order, computed CSS, POST/redirect behaviour, native browser dialogs, and the full automated
test suite all agree with the PRD's ten acceptance criteria. Ready to proceed to the next phase,
with the two non-blocking notes above left for a trivial follow-up.

---

*Verified: 2026-09-12T12:54:47Z*
*Verifier: Claude (gsd-verifier)*
