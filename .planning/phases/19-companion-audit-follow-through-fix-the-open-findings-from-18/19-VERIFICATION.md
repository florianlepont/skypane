---
phase: 19-companion-audit-follow-through-fix-the-open-findings-from-18
verified: 2026-09-11T17:00:39Z
status: human_needed
score: 23/23 must-haves verified (plus 5/5 requirement IDs satisfied)
overrides_applied: 0
human_verification:
  - test: "Health live fetch-and-swap refresh (D-02/A-20)"
    expected: "Open Health and leave it for two minutes: the page never navigates, 'Updated HH:MM' advances, an open 'More details' disclosure stays open across an update, keyboard focus is not lost, the sparkline still responds to hover/arrow-keys after an update, a typed registry filter query survives an update, the nav Health dot matches the on-page banner, Pause stops updates and Resume restarts them, and the browser console shows no CSP violation."
    why_human: "Only fully observable in a real browser session with live JS execution, fetch/DOM-swap timing, and CSP enforcement; this sandbox has no browser."
  - test: "Flights table responsive/keyboard behaviour (D-19/D-20)"
    expected: "At 1280px the table fits without horizontal scroll, or scrolls with a visible focus ring when tabbed to; a copy button shows 'Copied' beside the icon for ~1.5s and announces the row's callsign."
    why_human: "Visual layout and focus-ring rendering."
  - test: "Poll-cooldown countdown and CSP (D-18/A-35)"
    expected: "Loading Device during a poll cooldown, the countdown ticks down and re-enables the button with no CSP console violation; triggering poll on a zero-cooldown page still disables the button and reads 'Polling…'; every Display theme chip still shows its colour swatch."
    why_human: "Live countdown timing and browser console CSP enforcement."
  - test: "Sparkline fixed y-range and Device tile staleness colour (D-04/D-05)"
    expected: "With 40 days of battery history, the sparkline y-axis reads 3000 mV / 4200 mV and a near-flat series draws near-flat; a device that checked in minutes ago shows the Device tile green at a 30s cadence and amber past five minutes."
    why_human: "Visual chart rendering and colour verdict at specific timings."
  - test: "Health plain-language read-aloud (D-06/A-24)"
    expected: "Reading the whole Health page aloud as a household member, no sentence should require the source code to parse; hovering each tile label reveals its technical term."
    why_human: "Subjective comprehension/tone judgement; see also the Anti-Patterns section below for an automated residual jargon finding in this same area."
  - test: "Settings field-level error repopulation (D-07/A-25)"
    expected: "On Display, change the theme, clear the quiet-hours Start field, and save: the page returns with the new theme still selected, an error under the Start field, no generic banner, and nothing saved."
    why_human: "End-to-end form-submission UX in a real browser."
  - test: "Airlines gap strip and edit-gated lightbox (D-21/D-22)"
    expected: "/airlines with seeded unresolved prefixes shows the strip first with its sentence, curated cards only below; a card's lightbox shows no replace/upload/delete controls; /airlines?edit=1 shows all three; a gap card's back link returns to Airlines."
    why_human: "Multi-step visual/navigation flow."
  - test: "Quiet-hours presets, unload guard, no-JS fallback (D-09/D-10/D-14)"
    expected: "Tapping 'Work day' fills both time inputs and shows the save bar; tapping 'Always on' unticks the enable checkbox and keeps the times; triggering poll with unsaved edits prompts a browser confirmation; Save does not prompt; with JS disabled the bottom Save button is visible and works."
    why_human: "Browser-native confirm dialogs and no-JS fallback behaviour."
  - test: "Calendar disconnect confirmation and radiogroup screen-reader semantics (D-08/D-12)"
    expected: "With a calendar connected, Device shows a standalone Disconnect button (no checkbox); clicking raises a native confirm; declining changes nothing, accepting disconnects and flashes; with JS disabled it lands on a confirmation page; with a screen reader, theme chips and runway cards announce as named radio groups with their hints read."
    why_human: "Native browser dialogs and screen-reader announcement behaviour."
  - test: "Runway labels, next-wake caption agreement, Edit-artwork link, screen selector absence (D-11/D-13/D-22/D-23)"
    expected: "Runway cards read 'Runway 3 (07/25)' etc.; Home shows 'Next wake ≈ HH:MM' in Paris local time (nothing when never checked in); Device's 'Applies on the next scheduled poll' captions carry the same figure; Device's 'Edit artwork' link opens Airlines with artwork forms available; no screen selector is visible with one registered screen type."
    why_human: "Cross-page visual/copy agreement check most naturally done by eye."
---

# Phase 19: Companion audit follow-through — fix the open findings from 18-AUDIT.md Verification Report

**Phase Goal:** Close every defect still open in 18-AUDIT.md (A-19 through A-39, plus the remainder of A-40) and the two small suggestions that belong with them (S-02 next-wake countdown, S-04 quiet-hours presets), keeping the everyday pages plain-language and the design contract intact — see 19-CONTEXT.md D-01..D-23.
**Verified:** 2026-09-11T17:00:39Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

All 23 locked decisions (D-01 through D-23, covering audit findings A-19 through A-40 remainder plus S-02/S-04) were checked directly against the current codebase — not against SUMMARY.md narrative — by reading the implementing source, running the full test harness, and probing default-render output by hand for jargon leaks. Every plan's declared `must_haves.truths` in its PLAN frontmatter is substantively implemented and wired.

### Observable Truths

| # | Truth | Status | Evidence |
|---|---|---|---|
| 1 | D-01 (A-19): Health shows the same battery % estimate as Home, from a shared non-page module | ✓ VERIFIED | `companion/battery.py` (new, stdlib-only, no import of `companion.pages`/`server`); `home_page.py:22` and `health_page.py:56` both `import companion.battery as battery`; `health_page.py:936` calls `battery.battery_percent(mv)` |
| 2 | D-03 (A-21): every Health stat tile carries a text verdict beside its border colour (WCAG 1.4.1) | ✓ VERIFIED | `DEVICE_STATE_TEXT`/`PIPELINE_STATE_TEXT`/`CORROBORATION_STATE_TEXT` dicts (health_page.py:247-260); `widget-verdict` paragraph emitted at all three `stat_tile()` call sites (lines 1718, 1743, 2774) |
| 3 | D-15 (A-32): lockout resets after the window elapses — never permanent | ✓ VERIFIED | `auth.py` `LoginThrottle.record_failure()` (lines 314-324): resets `self._failures = 0` once `time.time() >= self._locked_until` and the counter was saturated |
| 4 | D-16 (A-33): session tokens signed with a derived key + per-process salt; Sign out revokes server-side | ✓ VERIFIED | `_PROCESS_SALT = secrets.token_bytes(32)` (auth.py:72), `_signing_key()` (line 75-84) HMACs the configured password with it; `revoke()`/`is_revoked()` (lines 105, 127) consulted from `_is_authenticated()`; `LOGOUT_ROUTE` branch calls `auth.revoke()` |
| 5 | D-17 (A-34): Secure cookie flag fail-closed, droppable only via explicit dev env var | ✓ VERIFIED | `auth.secure_cookie_flag()` (lines 228-245): only `"1"` (exact match) disables `Secure`; `deploy/skypane.env.example` documents `SKYPANE_COMPANION_INSECURE_COOKIES` as never-set-in-production |
| 6 | D-19 (A-36): Flights table is 6 columns (Runway dropped, survives in `title`/mobile card); scroller is keyboard-focusable and named; Timestamp is clock-only | ✓ VERIFIED | `history_page.py:139-141` `_HEADERS` has 6 entries, no "Runway"; `.data-table-wrap` carries `tabindex="0" role="region"` + `aria-label` (line 809); `<tr title="...">` carries the runway value |
| 7 | D-20 (A-37): copy buttons name their own row, show a visible "Copied" state, and only report success when the clipboard write actually succeeded | ✓ VERIFIED | `_row_copy_name()` (history_page.py:233) feeds per-row `aria-label`s; `copy-button.js` `fallbackCopy()` returns `execCommand()`'s real boolean and gates `showFeedback()` on it; `.copy-btn__label`/`.copy-btn--copied` CSS added |
| 8 | D-18 (A-35): CSP on every response including redirects; zero inline `<script>`; `/ui-theme` and `/logout` require a session | ✓ VERIFIED | `CONTENT_SECURITY_POLICY` constant (app.py:129-133) sent from `_send_hardening_headers()`, called by `redirect()` too; `poll_trigger_section()` emits no `<script>` (externalized to `companion/static/poll-cooldown.js`); `THEME_ROUTE`/`LOGOUT_ROUTE` both gated with `require_session()` |
| 9 | D-04 (A-22): fixed 3000-4200mV sparkline y-range; density threshold derived from rendered canvas width, not a typed 39 | ✓ VERIFIED | `SPARKLINE_Y_MIN_MV`/`MAX_MV` = 3000/4200 (health_page.py:742-743); `_sparkline_dense_threshold()` computes from `canvas_width_px` and dot diameter (lines 794-823), retiring the old typed constant |
| 10 | D-05 (A-23): device staleness derives from wake_interval_s (3/12 missed wakes, floored 5min/20min); a single ≥100mV dip is warn-only; coverage + source-fault fold into overall_severity | ✓ VERIFIED | `companion/wake.py` (`device_staleness_thresholds()`, `effective_wake_interval_s()`); `health_page.py`'s `BATTERY_DROP_WARN_MV = 100` demoted to warn; `overall_severity()`/`collect_anomalies()` both gained `coverage_state`/`source_fault` params (lines 1290, 1338) |
| 11 | D-06 (A-24): Health's tile labels/captions and corroboration rows read in plain language; 'adsbdb'→'the route database'; no CFG-04 id in visible text; technical term survives as a `title` tooltip | ✓ VERIFIED (see Anti-Patterns for a residual empty-state leak) | `PIPELINE_FRESHNESS_LABEL`/`RESOLUTION_RATE_LABEL`/`CORROBORATION_TILE_LABEL` renamed; `_CORROBORATION_ROWS` labels are "Both agree"/"Only one saw it"/"They disagree"; `*_TITLE` constants feed `caption_title=` tooltips; automated check `_health_registry_and_stats_prose_has_no_adsbdb_or_requirement_id` passes (companion/test_status_pages.py) |
| 12 | D-07 (A-25): a rejected save re-renders at 200 with submitted values kept and field-level errors; quiet-hours time inputs are `required` | ✓ VERIFIED | `app.py`'s `_handle_settings_post()` (lines 2359-2370): `if errors:` re-renders via `config_page.render(ctx, scope=scope, errors=errors, submitted=form)` at `send_html(200, ...)`, never a redirect; `<input type="time" name="quiet_hours_start" ... required...>` (config_page.py:1339-1341) |
| 13 | D-08 (A-26): calendar disconnect is its own confirmed `POST /settings/calendar/disconnect` form, outside `#settings-form`, with native-confirm + no-JS two-step fallback | ✓ VERIFIED | `CALENDAR_DISCONNECT_ROUTE = "/settings/calendar/disconnect"` (config_page.py:422); dispatched at app.py:2582; `companion-app` harness: "confirm=maybe renders the confirmation page", "confirm=yes 303-redirects... and actually disconnects" (both PASS) |
| 14 | D-09 (A-27): static Save fallback button hides only once `dirty-state.js` initialised the bar (`dirty-ready` class), never on mere `.js` presence | ✓ VERIFIED | `dirty-state.js:133`: `document.documentElement.className += " dirty-ready"` only after the bar guard passes; CSS keys the fallback-hide on that class |
| 15 | D-10 (A-28): `beforeunload` guard while dirty; Save/Cancel clear it | ✓ VERIFIED | `dirty-state.js:264`: `window.addEventListener("beforeunload", ...)` |
| 16 | D-11 (A-29): runway labels read "Runway 3 (07/25)", "Runway 4 (06/24)", "Runway 2 (02/20)" | ✓ VERIFIED | `server/device_config.py` `RUNWAYS` dict, `"label"` values exactly match; keys/tag_text/empty_heading deliberately unchanged |
| 17 | D-12 (A-30): chip grids and runway row carry group semantics (`role="radiogroup"` + `aria-labelledby`) and hints link via `aria-describedby` | ✓ VERIFIED | `config_page.py` lines 940, 959, 1113: `role="radiogroup" aria-labelledby="%s"` on both theme grids and the runway row; `_field_error_attrs()`/`aria-describedby` plumbing at lines 601-698 |
| 18 | D-13 (A-31, S-02): Home/Device show "Next wake ≈ HH:MM" computed from last check-in + effective wake interval | ✓ VERIFIED | `companion/wake.py` `next_wake_at_iso()`; `home_page.py:184` calls it; `config_page.py` `NEXT_WAKE_HEADER_LABEL`/`NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE` (lines 2382, 646) |
| 19 | D-14 (S-04): Quiet hours has 3 preset buttons (Night/Work day/Always on), client-side only, no server change | ✓ VERIFIED | `config_page.py:274-287` preset labels/constants; `dirty-state.js` (lines 54-100) wires `[data-quiet-preset]` click handlers, marks the form dirty |
| 20 | D-21 (A-38): gap cards moved into an "Unidentified airlines" strip with one plain sentence; resolve panel's back link returns to Airlines | ✓ VERIFIED | `airlines_page.py` `GAP_STRIP_HEADING = "Unidentified airlines"`; `_gap_strip_html()` (line 1102); `RESOLVE_BACK_LINK_TEXT = "← Back to Airlines"` (line 328) |
| 21 | D-22 (A-39): replace/upload/delete forms render only with `?edit=1`; everyday lightbox is view-only | ✓ VERIFIED | `EDIT_QUERY_PARAM = "edit"` (airlines_page.py:305); `_lightbox_html(edit_mode=False)` and `_resolve_section_html(ctx, edit_mode=False)` gate all three forms on `edit_mode`; `app.py:1231-1232` reads `?edit=1` into `ctx["edit_mode"]` |
| 22 | D-23 (A-40 remainder): `device_config` gains `screen_id`; `page_context()` threads it; selector `<select>` renders only when `len(SCREEN_IDS) > 1` | ✓ VERIFIED | `server/device_config.py` `DEFAULT_SCREEN_ID`/`SCREEN_IDS` (duplicated-not-imported from `companion/screens.py`, pinned equal by `server/test_config_history.py`); `config_page.py:2429`: `if len(screens.SCREEN_IDS) <= 1: return ""` |
| 23 | Requirement coverage: CFG-01/03/04/06/08 all satisfied by this phase's changes | ✓ VERIFIED | See Requirements Coverage table below |

**Score:** 23/23 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|---|---|---|---|
| `companion/battery.py` | Shared battery % estimate module (D-01) | ✓ VERIFIED | Exists, stdlib-only, imported by both home_page.py and health_page.py, no cross-import between them |
| `companion/wake.py` | Shared wake-interval/staleness-threshold module (D-05, D-13) | ✓ VERIFIED | Exists; `effective_wake_interval_s()`, `device_staleness_thresholds()`, `next_wake_at_iso()` all present and consumed by health_page.py/home_page.py/config_page.py |
| `companion/static/poll-cooldown.js` | Externalized poll-cooldown/disable-on-submit script (D-18) | ✓ VERIFIED | Exists; served pre-auth at its own route; `config_page.py`'s `poll_trigger_section()` emits zero `<script>` |
| `companion/static/confirm-submit.js` | Inline-free native confirm step for calendar disconnect (D-08) | ✓ VERIFIED | Exists; referenced by 19-11-SUMMARY.md and present in the review's `files_reviewed_list` |
| `companion/auth.py` (revocation/salt/lockout-reset) | D-15/D-16/D-17 | ✓ VERIFIED | `_PROCESS_SALT`, `_signing_key()`, `revoke()`/`is_revoked()`, `secure_cookie_flag()`, fixed `record_failure()` all present |
| `server/device_config.py` (RUNWAYS labels, screen_id seam) | D-11/D-23 | ✓ VERIFIED | English parenthetical labels; `DEFAULT_SCREEN_ID`/`SCREEN_IDS` present |

### Key Link Verification

| From | To | Via | Status | Details |
|---|---|---|---|---|
| `companion/app.py` `redirect()` | `_send_hardening_headers()` | direct call | ✓ WIRED | `redirect()` now calls the same choke point every other response helper uses, plus `Cache-Control: no-store` |
| `companion/app.py` `do_POST()` (THEME_ROUTE/LOGOUT_ROUTE) | `require_session()` | gate-then-dispatch | ✓ WIRED | Both branches gated identically to every other state-changing route |
| `companion/pages/health_page.py` `render()` | `companion/wake.py` | `wake.effective_wake_interval_s(device_cfg)` | ✓ WIRED | health_page.py:1407 |
| `companion/static/freshness.js` | Health's own served HTML | `fetch(window.location.href, {redirect:"manual"})` + `DOMParser` + `SWAP_SELECTORS` | ✓ WIRED | `SWAP_SELECTORS` list matches `health_page.REFRESH_SWAP_SELECTORS`, pinned equal by a cross-file harness check |
| `companion/pages/config_page.py` `handle_post()` | `render()`'s `errors`/`submitted` | `_handle_settings_post()`'s `if errors:` branch | ✓ WIRED | 200-render-in-place path confirmed in app.py:2359-2370 |
| `companion/pages/airlines_page.py` gap strip | Airlines resolve section | `?resolve=` query param + back link | ✓ WIRED | `RESOLVE_BACK_LINK_TEXT` points at Airlines, not Health |

### Behavioral Spot-Checks / Test Suite

| Behavior | Command | Result | Status |
|---|---|---|---|
| Full harness run | `PYTHON=.../python bash scripts/run-all-tests.sh` | 3 harnesses report FAIL, all 5 individual failures match the documented pre-existing root-sandbox set (2× `companion/test_companion_app.py`, 2× `server/test_manual_resolutions.py`, 1× `companion/test_status_pages.py`) | ✓ PASS (no new regressions) |
| `companion/test_companion_app.py` | direct run | 219/221 pass, 2 fails = documented WR-11 read-only-dir cases | ✓ PASS |
| `companion/test_status_pages.py` | direct run | 190/191 pass, 1 fail = documented `anomaly_active()` non-existent-dir case | ✓ PASS |
| `server/test_manual_resolutions.py` | direct run | 2 fails = documented WR-11 read-only-dir cases | ✓ PASS |
| `companion/test_view_pages.py` | direct run | 85/85 pass | ✓ PASS |
| `companion/test_config_page.py` | via run-all-tests.sh | 142/142 (referenced in per-plan summaries) | ✓ PASS |
| Health empty-state jargon probe | manual `health_page.render(ctx)` with a fresh/empty state_dir | Output contains `"ADS-B pipeline run is stale."` (anomaly banner pill) and `"Corroboration data appears once the ADS-B pipeline has..."` (empty-state prose), both outside any `title="..."` attribute | ⚠️ See Anti-Patterns below |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|---|---|---|---|---|
| CFG-01 | 19-02, 19-04, 19-07, 19-10, 19-11, 19-12 | Configure frame settings via web interface | ✓ SATISFIED | Settings pages hardened (CSP, field errors, dirty-state, calendar disconnect, screen_id) |
| CFG-03 | 19-01, 19-02, 19-05, 19-06 | See device's last-known health status via web interface | ✓ SATISFIED | Health page battery %, tile verdicts, fixed sparkline range, wake-derived staleness, plain-language copy |
| CFG-04 | 19-06, 19-08, 19-12 | See unresolved ICAO callsign prefixes via web interface | ✓ SATISFIED | Unresolved-prefix registry surfaced on Health (plain language) and Airlines (gap strip) |
| CFG-06 | 19-03 | Log of recently detected flights via web interface | ✓ SATISFIED | Flights table (6 columns), scroller accessibility, copy-button honesty |
| CFG-08 | 19-06 | Airline/route resolution statistics via web interface | ✓ SATISFIED | Resolution-statistics card retained and de-jargoned on Health |

No orphaned requirement IDs found: the phase's declared set (CFG-01, CFG-03, CFG-04, CFG-06, CFG-08) exactly matches the union of `requirements:` fields across all 12 plans, and REQUIREMENTS.md's top-level checklist already marks all five `[x]` complete (the stale per-phase mapping table further down that file, dated to Phase 6, was not updated when these were originally delivered and is a pre-existing documentation staleness unrelated to this phase's work — not a phase-19 gap).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|---|---|---|---|---|
| `companion/pages/health_page.py` | 2109 (`_corroboration_section()` empty-state) and 1326 (`collect_anomalies()`'s "ADS-B pipeline run is stale." item) | Residual jargon: "Corroboration" and "ADS-B pipeline" appear in visible page text (empty-state message, anomaly banner pill) outside any `title` attribute | ⚠️ WARNING | Directly reachable on a fresh/low-traffic install (no runway events recorded yet) — a household member would see "Corroboration data appears once the ADS-B pipeline has recorded at least one runway event," reusing exactly the jargon D-06 locked a rename for. The 19-06-PLAN.md harness check that verifies "no visible 'Corroboration'/'pipeline last ran'" only exercises a fixture with non-empty corroboration counts, so this empty-state branch was never exercised by the automated check and the leak went undetected. Does not violate any literal PLAN-frontmatter must-have (those are scoped to the three renamed tile labels/rows, which are all correctly plain-language), but is a genuine partial miss against A-24's own evidence list and the phase's audience framing. |
| `companion/pages/config_page.py` | 2404-2444 (`_screen_selector_html()`) | A crafted/invalid `screen_id` on `POST /settings` is rejected server-side (`FLASH_SAVE_FAILED`) but the field-level error is silently dropped — `_screen_selector_html()` has no `errors` parameter and never calls `_field_error_html()` | ⚠️ WARNING | Currently unreachable through the live UI (today's single-member `SCREEN_IDS` means the `<select>` itself renders `""`), but latent: it will silently regress D-07's own "the message lives at the field" contract the moment a second screen type is registered, and is already reachable via a hand-crafted POST body. Corroborated independently by the untracked `19-REVIEW.md` code-review artifact already present in this worktree (WR-01). |
| `companion/app.py` | 8-16 (module docstring) and 1384-1387 | Docstring's D-02 gate-exemption list ("login routes, the stylesheet, and the theme-toggle POST") was not updated when 19-04 added `require_session()` to `POST /ui-theme` | ℹ️ INFO | Documentation drift only — the code is more restrictive than the docstring claims, not less, so no access-control bug, but the file's own stated invariant ("the two lists are not allowed to silently drift apart") is now violated. Corroborated by `19-REVIEW.md` (WR-02). |
| `companion/auth.py` | 308-335 (`LoginThrottle`) | `record_failure()`/`record_success()`/`locked_out()` mutate shared process-global state with no lock, under a `ThreadingHTTPServer` that runs one thread per connection | ℹ️ INFO | Pre-existing gap (the class was never locked), but this phase's own A-32/D-15 fix added new, more stateful reset logic to this exact unlocked counter. A tight race could under-count concurrent failures. Corroborated by `19-REVIEW.md` (WR-03). |

No 🛑 BLOCKER-level anti-patterns found (no unreferenced TBD/FIXME/XXX debt markers in any file this phase touched).

### Gaps Summary

No must-have truth failed, no artifact is missing or stub, no key link is unwired, and no blocker anti-pattern exists. `status: gaps_found` is therefore not warranted.

However, `status: passed` is also not warranted, for two independent reasons:

1. **Ten `<human-check>` blocks** were deliberately deferred to end-of-phase across 19-03/19-04/19-05/19-06/19-07/19-08/19-09/19-10/19-11/19-12 (per `workflow.human_verify_mode = end-of-phase`) — these cover real-browser behaviours (live fetch-and-swap timing, CSP console violations, native `confirm()` dialogs, screen-reader radiogroup announcement, no-JS fallback paths) that cannot be exercised in this sandbox. They are harvested verbatim into `human_verification` above.
2. **One residual jargon leak** in Health's empty-state/anomaly-banner prose (see Anti-Patterns) is a genuine, automated-check-confirmed partial miss against A-24's own evidence list, even though it does not violate any plan's literal frontmatter must-have. It is reported as a WARNING for the developer's judgment call, not blocking the phase.

Recommended next step: either accept the WARNING items as-is (they are all narrow, latent, or cosmetic — none is exploitable or currently user-visible in the common path except the Health empty-state sentence) or fold a one-line fix for each into a `/gsd-quick` task; then perform the ten human-check items above before considering Phase 19 fully closed.

---

*Verified: 2026-09-11T17:00:39Z*
*Verifier: Claude (gsd-verifier)*
