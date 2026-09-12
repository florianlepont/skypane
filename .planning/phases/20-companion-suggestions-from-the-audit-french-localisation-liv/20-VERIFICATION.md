---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
verified: 2026-09-12T00:00:00Z
status: gaps_found
score: 34/35 must-haves verified
overrides_applied: 0
gaps:
  - truth: "D-12: Display's Look supersection holds Theme, Flight colours, Calendar, in that order, under one heading"
    status: partial
    reason: "Flight colours cannot be a literal descendant of <form id=settings-form> (its add form and each Remove row are real <form> elements — HTML forbids nesting a <form> inside another <form>). The shipped fix for the calendar-connect placement (polish commit 00c4737) moved Runway out of the form too, so the final Display document order is: Look (Theme, Calendar) -> </form> -> calendar connect/disconnect -> What it watches (Runway) -> Flight colours (no supersection heading at all) -> When it is on (Screen, Quiet hours). Flight colours therefore renders as an orphaned, unheaded section between 'What it watches' and 'When it is on', not inside 'Look' between Theme and Calendar as D-12 specifies. This is documented at length in config_page.py's own _display_groups_html()/render() docstrings as a known, reasoned trade-off (\"a future plan could close that remaining gap\"), not a silent miss — but it was never surfaced to the developer as a locked-decision deviation requiring sign-off, unlike the order deviations the CONTEXT.md's own 'Assumptions flagged' section pre-cleared."
    artifacts:
      - path: "companion/pages/config_page.py"
        issue: "_display_groups_html()/render(): rules_section_html (Flight colours) renders after display_watches_supersection_html (Runway) and before display_on_supersection_html (Screen/Quiet), under no section_intro_html() heading of its own — verified by rendering scope=display and listing <h2> order: Look, Theme, Calendar, What it watches, Runway, Flight colours, When it is on, Screen on/off, Quiet hours"
    missing:
      - "Either restructure so Flight colours visually reads as part of Look (e.g. give it its own dedicated non-nested route so it can sit between Theme/Calendar and the form boundary, as the code's own docstring suggests), or get the developer's explicit sign-off to keep the current position via a VERIFICATION.md override."
human_verification:
  - test: "Push a real battery-low/frame-silent transition end to end with a real ntfy topic pasted into Device -> Notifications, and confirm the phone receives the two paired pushes (D-25..D-28)"
    expected: "A push arrives at the phone with the documented Title/body pair for each of the four transition states, and 'Send a test' reaches the same phone"
    why_human: "Requires a real ntfy.sh (or self-hosted) topic and a subscribed phone — the harnesses only prove the code builds and POSTs the right payload to an injected transport (server/test_notify.py, server/test_poll_loop.py), not that a real device notification renders"
  - test: "Select each theme chip on Display and confirm the live preview above the grid swaps to that theme rendered with the last real flight, then reload with JavaScript disabled and confirm the preview still shows the saved theme rendered with the last real flight"
    expected: "The .theme-live-preview image src changes on chip click without a page reload; with no JS, the server-rendered image for the currently-saved theme is shown"
    why_human: "theme-preview.js's DOM-swap behaviour and the no-JS fallback require a real browser; companion/test_companion_app.py proves the route, cache key and script wiring, not the swap animation itself"
  - test: "Trigger the calendar-disconnect confirmation and the rule Remove buttons and confirm the native confirm() dialog text is in the current language"
    expected: "A native browser confirm() dialog appears with translated copy before the destructive POST fires"
    why_human: "confirm-submit.js drives window.confirm(), which cannot be exercised by a stdlib HTTP-only test harness"
  - test: "With a screen reader, navigate Home's status card and Display's supersections and confirm status_row()'s dot/verdict/detail structure and section_intro_html()'s headings announce sensibly, and that the beforeunload guard's native browser dialog appears when leaving Display with unsaved edits"
    expected: "Each status row announces as one coherent unit (label, verdict, detail); leaving a dirty settings form triggers the browser's own unsaved-changes prompt"
    why_human: "Screen-reader announcement quality and the beforeunload native dialog are both real-browser-only behaviours no stdlib harness can observe"
  - test: "Confirm the FR/EN switch, the Simple/Full switch and the theme switch each survive across a real browser tab close/reopen (cookie persistence) and across the two different pages of the household (two different browsers/profiles show two different languages at once)"
    expected: "Each browser/profile keeps its own independent language/mode/theme after restart, matching the 'each person in their own language' requirement"
    why_human: "Cookie persistence across a real browser restart and simultaneous multi-browser use is outside what an in-process HTTP harness can exercise"
---

# Phase 20: Companion suggestions from the audit — Verification Report

**Phase Goal:** Make the companion usable by both people in the household in their own language (French and English, switchable per browser), redesign Home to be useful and pleasant at a glance with the quick actions moved to Display/Device, regroup Display so every everyday setting lives there with a strongly improved calendar and flight-colours experience, add push notifications for battery-low and frame-silent transitions, and add a simple mode that hides everything advanced.

**Verified:** 2026-09-12
**Status:** gaps_found
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | D-01: EN is the source, FR is a lookup catalogue, missing keys fall back to English, never raise | VERIFIED | `companion/i18n.py` `t()`/`t_lang()`; `companion/i18n_fr/__init__.py`'s auto-merging `CATALOG`; `test_i18n.py` round-trip/fallback checks pass |
| 2 | D-02: nav-footer FR·EN control, `<form method=post>` idiom, `POST /ui-lang` session-gated, cookie via `auth.secure_cookie_flag()` | VERIFIED | `companion/layout.py:_lang_form_html()`; `companion/app.py:_handle_lang_post()` (byte-for-byte sibling of `_handle_theme_post()`) |
| 3 | D-03: no-cookie language from `Accept-Language` (fr*→fr, else en); `<html lang>` set | VERIFIED | `companion/app.py:_lang_from_request()`; `companion/layout.py` `<html lang="%s">` |
| 4 | D-04: `companion/i18n.py` exposes `t()`/`t_lang()` over `i18n_fr.CATALOG` keyed by English string | VERIFIED | code read directly; `test_i18n.py` passes |
| 5 | D-05: every user-visible string on every page renders through `t()` | VERIFIED | mechanical AST completeness harness (D-08 Check 1/2) passes on all page modules, `layout.py`, `auth.py`; per-page French renders (D-08 Check 3) pass for Home/Display/Device/Flights/Airlines/Health/login/404/disconnect-confirmation |
| 6 | D-06: JS strings (`copy-button.js` "Copied", `dirty-state.js` connector words) come from server-rendered `data-*` attributes | VERIFIED | both scripts read `data-copied-text`/`data-dirty-*` with hardcoded-fallback-only literals; callers wrap in `t()` |
| 7 | D-07: dates/relative-age follow request language; 24h Europe/Paris in both | VERIFIED | `layout.local_clock_text()`/`relative_age_text()`; polish commit `63e4c95` fixed a real ordering bug (health-state built before prefs were resolved) with new regression tests |
| 8 | D-08: mechanical completeness + dead-translation harness, ast-based | VERIFIED | `companion/test_i18n.py` Check 1/Check 2, `ast.parse()`-based; 24/24 pass |
| 9 | D-09: French copy quality (typographic apostrophe, NBSP before `:;?!`, nav labels) | VERIFIED | `test_i18n.py` Check 4 asserts both rules over every CATALOG value; nav labels confirmed Accueil/Affichage/Vols/Compagnies/Avancé/État/Appareil |
| 10 | D-10: Runway moved to Display's `everyday_groups` | VERIFIED | `companion/screens.py`: `GROUP_RUNWAY` in `everyday_groups`, not `advanced_groups` |
| 11 | D-11: Calendar + rules render on Display; disconnect/rule forms return to Display | VERIFIED | `scope_groups()`; `show_calendar_disconnect`/`show_rules` gated on `scope == SCOPE_DISPLAY` |
| 12 | D-12: Display is three headed sections, Look (Theme, Flight colours, Calendar) / What it watches (Runway) / When it is on (Screen, Quiet) | **PARTIAL** | See Gaps — Flight colours renders unheaded, after "What it watches", not inside "Look" |
| 13 | D-13/Pitfall 1: instant-switch forms never nest inside `<form id=settings-form>` | VERIFIED | live-rendered Display/Device scope HTML: form-tag nesting depth never exceeds 1 |
| 14 | D-14a-e: Calendar redesign (one-line purpose, status row, dedicated connect route, chip theme picker) | VERIFIED | `calendar_group()`/`calendar_connect_section()`; `POST /settings/calendar/connect` via `_handle_calendar_connect_post`; write-only URL field confirmed (no `value=` ever emitted) |
| 15 | D-15a-e: Flight colours redesign (rename, one-line add form, `.rule-row` list, empty state, suggestion chips) | VERIFIED | `_rule_add_form_html()`, `_rule_row_html()`, `RULES_EMPTY_HEADING`, `_rule_suggestion_chips_html()`; native-radio segmented control confirmed as the deliberate, spec-endorsed zero-degraded-state choice over a `rule-form.js` script (20-UI-SPEC.md §F Structural Note 5, adopted in 20-CONTEXT.md's Resolutions) |
| 16 | D-16: Home has no Quick-actions card; `/quick/*` routes/flash keys untouched, `return_to` now Display | VERIFIED | `home_page.py` render() has no switch/refresh markup; `_handle_quick_toggle()` in `app.py` redirects to `layout.DISPLAY_ROUTE` |
| 17 | D-17: hero row (picture + one status card, headlined by next update / "Expected since"), Frame verdict exactly once | VERIFIED | `home_page.py:_status_card_html()`/`_hero_figure_html()`; `_plain_text_from_markup()` strips the embedded verdict from `device_detail_html` so `FRAME_STATE_TEXT` renders once |
| 18 | D-17.2: recent-flight thumbnails only when real artwork resolves, never a broken image | VERIFIED | `_recent_flight_thumb_html()` gates on `illustrations.resolved_illustration_path()`; polish commit `d75dc07` fixed a real 404 defect with a new placeholder-vs-real-file test case |
| 19 | D-18: visual contract (24px gap, hairline cards, label voice, status colour + text verdict, dark-theme, 1280/390 sweep) | VERIFIED | `companion/static/style.css` reuses only existing tokens; `contrast_check.py` 39/39; 20-12-SUMMARY.md's FR/EN sweep (24 renders) found one overflow (Health/390/fr), fixed by polish commit `35055ca`, confirmed present and tested on the current tree |
| 20 | D-19: instant switches on Display's Screen/Quiet-hours cards, posting to `/quick/*`, shared "applies next wake" sentence | VERIFIED | `display_group()`/`quiet_hours_group()`; `QUICK_ACTION_APPLIES_SENTENCE` |
| 21 | D-20: Home adds no query beyond the existing ones + one pure-string resolve | VERIFIED | `home_page.render()`: one `history_db` read reused for both hero and recent-flights; `illustrations.normalise_airline_key()` is pure-string |
| 22 | D-21: `layout.status_row()` shared primitive, empty label omits the span, state maps through the existing whitelist | VERIFIED | code read directly; used by Home (3 rows) and Calendar's status line |
| 23 | D-22: chip grid unchanged, live preview added above it, no carousel | VERIFIED | `theme_fieldset()`; grid markup unchanged, `.theme-live-preview` new figure above it |
| 24 | D-23: `?live=1` renders the most recent runway event, falls back to sample, cached per (theme, event id) | VERIFIED | `companion/theme_preview.py:cache_path()`/`preview_signature()` fold `live_event_id`; `companion/app.py:_safe_latest_runway_event()` |
| 25 | D-24: preview follows chip selection via `theme-preview.js`, no-JS shows saved theme | VERIFIED | six-touch-point script wiring in `app.py`/`layout.py`; `data-preview-src` swap; server always renders the saved theme's `src` first |
| 26 | D-25: ntfy-style POST, plain-text body + Title header, reuses `calendar_rules._url_is_safe()`, never raises | VERIFIED | `server/notify.py:send_notification()` |
| 27 | D-26: Notifications group on Device (write-only topic URL, two checkboxes, "Send a test"), persisted with config-history entry | VERIFIED | `notifications_group()`; `server/device_config.py:normalise_notifications()`/`save_device_config()`; `server/test_config_history.py` 69/69 |
| 28 | D-27: exactly one push per genuine transition (battery, frame-silent), silent threshold = shared WARN value, never breaks the poll cycle | VERIFIED | `_notify_battery_transition()`/`_notify_silence_transition()` in `server/poll_loop.py`; `poll_state["notifications"]` remembers last-sent state; both wrapped in try/except; `server/test_poll_loop.py` 96/96. Note: the silence check's one call site is intentionally skipped during "hold" cycles (quiet hours/off) per the code's own documented reasoning — see Gaps note below (not scored as a failure; flagged as informational) |
| 29 | D-28: notification body language comes from persisted `notifications.lang`, set at save time from the session's language | VERIFIED | `notify.body_for_lang()`; `notifications_group()` writes `lang` from `ctx.get("lang")` at save, no selector in the group |
| 30 | D-29: Simple/Full nav-footer switch, session-gated `POST /ui-mode`, `sp_ui_mode` cookie | VERIFIED | `_mode_form_html()`; `_handle_mode_post()` |
| 31 | D-30: simple mode hides Advanced nav group + Health dot, "See details on Health", "Edit artwork"→"Change pictures", disclosures collapse; advanced URLs still reachable | VERIFIED | `_nav_groups()` server-side omission; `companion/test_status_pages.py`/`test_companion_app.py` simple-mode suite (16 checks) all pass, including `/health`/`/device` still 200 under simple mode |
| 32 | D-31: simple mode keeps Home, all six Display groups, Flights, Airlines (incl. gap-resolve forms), switches, Sign out | VERIFIED | "PASS Display still renders all six everyday groups under sp_ui_mode=simple" and "PASS Flights and Airlines keep their full content under sp_ui_mode=simple" |
| 33 | D-32: no inline `<script>`/`on*` handlers introduced | VERIFIED | six-touch-point contract followed for `theme-preview.js`; existing CSP-clean pattern preserved; 20-12 sweep found zero CSP violations/inline scripts across 24 renders |
| 34 | D-33: every touched harness's `EXPECTED_CHECK_COUNT` re-derived and matches a live run; the five root-sandbox failures untouched | VERIFIED | spot-checked 9 harnesses — every `EXPECTED_CHECK_COUNT` matches its actual pass count exactly; the same 5 pre-existing root-sandbox failures reproduce identically to main and are not counted as gaps |
| 35 | D-34/D-35/D-36: design-system skill updated; S-01/S-03/S-05/S-06 marked shipped; "Edit artwork" replaced by "Change pictures" on Airlines | VERIFIED | `SKILL.md`/`control-density.md`/`settings-page-patterns.md` all carry new Phase 20 entries; `18-AUDIT.md` marks all four `fixed (phase 20)`; `airlines_page.py`'s toggle confirmed, Device's old link confirmed gone |

**Score:** 34/35 truths verified (one partial — D-12's Flight-colours placement)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `companion/prefs.py` | per-request lang/simple-mode contextvars | VERIFIED | `set_request_prefs`/`current_lang`/`simple_mode`/`LANG_CHOICES`/`MODE_CHOICES` all present |
| `companion/i18n.py` | `t()`/`t_lang()` | VERIFIED | present, tested |
| `companion/i18n_fr/__init__.py` | auto-merging `CATALOG` | VERIFIED | present, raises on duplicate key |
| `companion/test_i18n.py` | completeness/dead-translation harness | VERIFIED | 24/24, `EXPECTED_CHECK_COUNT` matches |
| `server/wake.py` | shared wake-interval arithmetic | VERIFIED | `effective_wake_interval_s`, `device_staleness_thresholds`, `next_wake_at_iso`, `MISSED_WAKES_WARN` all present; `companion/wake.py` is a re-export shim |
| `server/notify.py` | `send_notification()` | VERIFIED | present, SSRF-gated, tested (`server/test_notify.py` 7/7) |
| `server/device_config.py` | `notifications` group | VERIFIED | `normalise_notifications` present, validated, config-history-backed |
| `companion/layout.py` | `status_row()`, `section_intro_html()` | VERIFIED | both present, both consumed by Home/Calendar/Display |
| `companion/pages/home_page.py` | rebuilt hero/status/recent-flights | VERIFIED | `layout.status_row` calls present |
| `companion/screens.py` | moved group membership | VERIFIED | `everyday_groups` carries Runway/Calendar |
| `companion/theme_preview.py` | live-event render + cache | VERIFIED | `live_event`-aware `cache_path`/`preview_signature`/`cached_preview_bytes` |
| `companion/static/theme-preview.js` | chip-selection src swap | VERIFIED | `data-preview-src` swap present |
| `companion/test_i18n.py` | AST-based scan | VERIFIED | `ast.parse`/`ast.walk` used throughout |
| `.claude/skills/sketch-findings-skypane/SKILL.md` | Phase 20 components | VERIFIED | `status-row` and full Phase 20 entry present |
| `.planning/phases/18-companion-audit-and-ux-refactor/18-AUDIT.md` | S-01 shipped status | VERIFIED | all four suggestions marked `fixed (phase 20)` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `companion/app.py` | `companion/prefs.py` | `page_context()` resolves cookie/Accept-Language once | WIRED | `prefs.set_request_prefs(...)` called once per request path (fixed to run before health-state computation by polish commit `63e4c95`) |
| `companion/i18n.py` | `companion/i18n_fr` | `CATALOG.get(text, text)` | WIRED | confirmed in `t()` |
| `companion/layout.py` | `/ui-lang` | nav footer language form | WIRED | `_lang_form_html()` posts to `/ui-lang` |
| `server/notify.py` | `server/plane/calendar_rules.py` | reused SSRF gate | WIRED | `_url_is_safe` call confirmed first line of `send_notification()` |
| `companion/wake.py` | `server/wake.py` | re-export shim | WIRED | `from server.wake import (...)` |
| `companion/pages/health_page.py` | `companion/layout.py` | promoted `section_intro_html` | WIRED | `layout.section_intro_html` used by both Health and Display |
| `server/poll_loop.py` | `server/notify.py` | transition senders | WIRED | both `_notify_*_transition()` call `notify.send_notification` |
| `server/poll_loop.py` | `server/wake.py` | shared staleness thresholds | WIRED | `wake.device_staleness_thresholds(...)` in `_notify_silence_transition()` |
| `companion/app.py` | `companion/theme_preview.py` | `?live=1` cache | WIRED | `cached_preview_bytes(..., live_event=...)` |
| `companion/pages/config_page.py` | `/theme-preview/{id}.png?live=1` | live preview img src + chip `data-preview-src` | WIRED | confirmed in `theme_fieldset()` |
| `companion/static/copy-button.js` | `companion/pages/history_page.py` | `data-copied-text` | WIRED | confirmed |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|-----------------|--------------|--------|----------|
| CFG-13 | 01,03,06,07,08,09,10,11,12 | Bilingual FR/EN, per-browser, completeness harness | SATISFIED | full-suite FR sweep passes, `test_i18n.py` 24/24 |
| CFG-14 | 03,04,06 | Home glanceable page, no quick actions | SATISFIED | `home_page.py` rebuilt, no switch markup, tests pass |
| CFG-15 | 03,04,07,09 | Display carries every everyday setting; redesigned calendar/rules | **PARTIAL** | everything IS on Display (satisfied), but the "Look" grouping specifically omits Flight colours — see Gaps |
| CFG-16 | 04,08,11 | Live theme preview from last real flight, follows selection | SATISFIED | `?live=1` route + `theme-preview.js` verified |
| CFG-17 | 02,05,11 | Push notification on battery-low/frame-silent, once per transition | SATISFIED | `server/notify.py` + `poll_loop.py` transitions verified; real-device delivery is human-verification |
| CFG-18 | 01,06,07,09,10,12 | Simple mode hides Advanced pages/affordances, everyday pages stay usable | SATISFIED | full simple-mode test suite (16 checks) passes |

No orphaned requirements: all six phase requirement IDs (CFG-13..CFG-18) are declared across the 12 plans' `requirements:` frontmatter and each has direct code evidence above. `.planning/REQUIREMENTS.md`'s CFG-13..CFG-18 checkboxes are still unchecked `[ ]` — this is expected to be the orchestrator's post-verification bookkeeping step, not a phase gap.

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX` markers, no `placeholder`/`coming soon`/`not yet implemented` copy, no empty stub implementations, and no hardcoded-empty props found across every file this phase's 12 plans + 5 polish commits touched.

### Behavioral Spot-Checks / Full Suite

`PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` → 265/267 companion-app checks pass; the only two companion-app failures plus the three failures in `server/test_manual_resolutions.py`/`companion/test_status_pages.py`'s `anomaly_active()` case are the five documented root-sandbox (read-only-directory, running-as-root) failures, reproduced identically and not counted as regressions. `ruff check .` → clean. All 21 harnesses otherwise green; `EXPECTED_CHECK_COUNT` spot-checked against 9 of the phase's own harnesses and matches exactly in every case.

### Probe Execution

SKIPPED — no `scripts/*/tests/probe-*.sh` files exist in this repository and none are named by any of this phase's plans or SUMMARYs.

### Human Verification Required

See the `human_verification` list in the frontmatter above — five items, all genuinely browser/hardware-only (native `confirm()`/`beforeunload` dialogs, screen-reader announcements, real ntfy push delivery, the live-preview JS swap, and multi-browser cookie independence). None of these can be resolved by static analysis or the stdlib HTTP test harnesses this project uses.

### Gaps Summary

One structural gap: **D-12's "Look" supersection is supposed to hold Theme, Flight colours and Calendar together**, but the shipped Display page renders Flight colours as an unheaded section physically positioned between "What it watches" (Runway) and "When it is on" (Screen/Quiet hours) — never inside "Look", and under no supersection heading of its own. This is not an oversight: `companion/pages/config_page.py`'s own `_display_groups_html()`/`render()` docstrings explain the exact HTML constraint that forces it (Flight colours' add-form and each Remove-row are real `<form>` elements, which cannot be literal descendants of `<form id="settings-form">`; the polish fix that correctly repositioned the Calendar-connect form pushed Runway out of the form too, which left Flight colours needing to render after it). The code even flags a possible future fix ("a future plan could close that remaining gap"). Because this is a locked decision (D-12) and the deviation was never explicitly pre-cleared the way the CONTEXT.md's "Assumptions flagged" section pre-cleared the overall section order, it is reported here rather than silently accepted.

**This looks intentional and well-reasoned.** To accept this deviation, add to VERIFICATION.md frontmatter:

```yaml
overrides:
  - must_have: "D-12: Look holds Theme, Flight colours, Calendar under one heading"
    reason: "Flight colours' add/remove forms cannot be literal descendants of <form id=settings-form>; positioning it after What it watches (rather than inside Look) is the documented, reasoned trade-off in config_page.py; a dedicated non-form route would close the gap in a later phase"
    accepted_by: "<developer name>"
    accepted_at: "<ISO timestamp>"
```

Everything else — the bilingual sweep, the completeness harness, the Home redesign, the notifications pipeline, simple mode, the live theme preview, and the design-system/audit-record updates — is verified directly against the current codebase and passes.

---

*Verified: 2026-09-12*
*Verifier: Claude (gsd-verifier)*
