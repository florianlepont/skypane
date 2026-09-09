---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
verified: 2026-09-07T23:58:35Z
status: passed
score: 13/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Load the companion Settings page with SKYPANE_CALENDAR_ICS_URL unset, then with it set to a real feed."
    expected: "The URL appears nowhere (page, page source, tooltip). The copy promises only that the frame colours a flight that happens to be on screen, with no suggestion of tracking/watching/announcing. The theme picker looks and behaves like the Rules add-form's, and changing it dirties the save bar like Wake interval does."
    why_human: "Visual/UX confirmation of copy tone and control behaviour cannot be fully certified by grep alone; workflow.human_verify_mode is end-of-phase, so this was deliberately deferred rather than blocking each plan."

  - test: "Run /gsd-secure-phase 16 — the mandatory retroactive security pass over the consolidated T-16-* threat register (SSRF, secret handling, DoS, tamper, privacy) across all seven plans."
    expected: "The security agent confirms the per-plan STRIDE mitigations actually close the register with no residual high-severity gap."
    why_human: "ROADMAP.md's 'Closes with' clause and 16-VALIDATION.md's Sampling Rate both name this as a mandatory phase-gate agent pass, not something this goal-backward code verification substitutes for. Not run yet — no 16-SECURITY.md exists in the phase directory."
---

# Phase 16: Calendar-linked flight highlighting — a connected calendar sources colour rules automatically — Verification Report

**Phase Goal:** The operator connects a calendar (one iCal feed). When the frame displays a flight that calendar lists, the panel uses a chosen theme for that render. This is a new SOURCE for Phase 15's existing rule mechanism (registry, resolver, precedence order, Settings editor), not a new mechanism.

**Verified:** 2026-09-07T23:58:35Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

No REQUIREMENTS.md ID maps to this phase (unmapped, promoted from a seed — Phase 10-15 precedent, per the phase's own framing). Verified against `16-CONTEXT.md`'s decisions D-01 through D-04 and the phase's stated security/copy constraints instead, per this verification's explicit brief.

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | **D-01 separation** — a calendar entry is never written into `colour_rules.json`, and the Settings rules editor never fills with calendar-sourced rows | ✓ VERIFIED | `server/plane/calendar_rules.py` is a structurally-leaf module (AST-checked: no `colour_rules` import); `calendar_rules_path()` returns `calendar_rules.json`, a distinct file from `colour_rules.json`. `companion/test_config_page.py::_calendar_d01_registry_entries_never_appear_in_rules_list` writes a populated calendar registry + one hand-added manual rule and asserts the rendered rules list shows only the manual rule (127/127 checks pass). `server/test_calendar_rules.py` behaviourally proves writing/re-writing the calendar registry leaves `colour_rules.json`'s bytes unchanged. |
| 2 | **D-02 precedence** — a calendar match beats every manual rule including an exact-callsign pin, and a tampered/unregistered theme id never reaches the resolver | ✓ VERIFIED | `colour_rules.resolve_effective_theme_id()` (server/plane/colour_rules.py:471-531) checks `calendar_theme_id` as its very first statement, before the cache read and all three rule lookups (callsign → hex → prefix), before the arrivals override, before the base theme. `server/test_colour_rules.py` proves the calendar value beats callsign/hex/prefix rules and the arrivals override, is additive (byte-identical 3-arg vs. 4-arg-with-None calls), and that a non-member value falls through rather than returning or short-circuiting (33/33 pass). End-to-end through `poll_loop.run_once()`, `server/test_poll_loop.py::_calendar_match_beats_an_exact_callsign_rule` confirms the same through the real loop (80/80 pass). |
| 3 | **D-04 match key** — airline + far-end airport + time window, never the flight number; matching runs after `enrich.resolve_route()` | ✓ VERIFIED | `match_calendar_theme()` (calendar_rules.py:1283) requires `origin_iata`/`destination_iata`/`callsign_iata` from the enriched route, derives the airline from `callsign_iata`'s leading two characters (`_airline_iata_from_route()`), and never reads the flight number or the summary's UTC offset (grep-confirmed: no flight-number key in the 5-key entry shape; `offset` only appears in the parser's own regex/comment). Direction symmetry (`_far_end_iata`/`_entry_far_end_iata`) and time-window tie-breaking are both independently asserted and mutation-tested in `server/test_calendar_rules.py` (74/74 pass), including the fixture's real same-route 8-hours-apart pair. |
| 4 | **No static IATA↔ICAO airline table exists anywhere** — the bridge is `route["callsign_iata"]`'s leading letters | ✓ VERIFIED | `_airline_iata_from_route()`'s docstring records CORRECTION 1 verbatim and explicitly forbids building one. `grep -rn '"TO"\|"VY"\|"EJU"\|"TVF"' server/plane/calendar_rules.py` returns nothing. `server/test_calendar_rules.py` proves the match still fires for a two-letter designator (`ZQ`) the codebase has never seen, which no static table seeded from the measured ten carriers could satisfy. |
| 5 | **Date parsing is bare-UTC only** — rejects unknown forms loudly, no `zoneinfo`/`pytz` import | ✓ VERIFIED | `parse_ics_datetime()` matches only `_ICAL_UTC_RE` (`YYYYMMDDTHHMMSSZ`); AST-checked import list contains no `zoneinfo`/`pytz`. `parse_ics_events()` counts date-form rejections in their own bucket and prints a non-zero, value-free warning (never the rejected date) on the fixture's deliberate `TZID` tripwire event, still returning exactly 4 valid entries. |
| 6 | **The clock-dependency invariant** — the held/repaint branch reuses the persisted calendar match rather than recomputing one, so a battery-icon repaint hours after the flight was first displayed never changes the panel's colour | ✓ VERIFIED (behavioral test, not just presence) | `server/poll_loop.py`: `current_calendar_theme_id = poll_state.get("last_calendar_theme_id")` (line 984, membership-tested against `THEMES`) is passed into the held branch's resolver call (line 1315-1317) — the only `match_calendar_theme(` call site in the file is in the flight-detected branch (line 1204), never in the held branch. `server/test_poll_loop.py::_calendar_match_survives_a_battery_repaint_past_its_own_window` genuinely distinguishes the two implementations: it advances the fake clock `CALENDAR_MATCH_TOLERANCE_S + 3600` seconds past the calendar entry's own window before forcing the held-branch repaint, and asserts the rendered `theme_id` is unchanged and still the calendar theme (not the base theme) — a recomputing implementation would fail this specific test while passing a same-minute one. |
| 7 | **SSRF hardening** — validation on the resolved IP (not hostname), re-validated per redirect hop | ✓ VERIFIED | `_host_is_safe()` resolves via `socket.getaddrinfo()` and rejects if *any* returned address is non-public (loopback/private/link-local/reserved/multicast/unspecified) via `ipaddress`. `fetch_ics()`'s redirect loop re-runs `_url_is_safe()` on every iteration including redirect targets, before any request. `server/test_calendar_rules.py` proves a mixed public+private DNS answer for a public-looking hostname is refused (the DNS-rebinding case a hostname-only check would pass), and that a redirect to a loopback address is refused. |
| 8 | **Response body capped by streaming, never by `Content-Length`** | ✓ VERIFIED | `fetch_ics()` iterates `response.iter_content()` with a running byte counter, aborting mid-stream past `CALENDAR_MAX_RESPONSE_BYTES`; `grep -c 'Content-Length' server/plane/calendar_rules.py` returns 0. Test drives an oversized body declaring `Content-Length: 1` and confirms it is still refused. |
| 9 | **No log path interpolates an exception's string form** (the URL-in-exception-message trap) | ✓ VERIFIED | `fetch_ics()`'s only two print statements log `type(exc).__name__` and a fixed description, never `exc` itself, with an explicit comment naming the divergence from `detect.py`'s caller-catch idiom and the reason (`requests.exceptions.*` embed the URL). `server/test_calendar_rules.py`'s secret-containment group forces a `requests.RequestException` whose message *is* the full secret URL and asserts none of the token/host/path/query substrings reach stderr, the persisted registry, or the rendered Settings page (confirmed again via a real authenticated HTTP round trip in `companion/test_config_page.py`, 127/127 pass). |
| 10 | **The copy guard** — no user-facing string implies the frame tracks/watches/follows/monitors/notifies (as an affirmative claim), no flight count or preview | ✓ VERIFIED | `companion/pages/config_page.py`'s locked `CALENDAR_*` constants contain no affirmative real-time-awareness claim and no person/role/crew noun; the one literal occurrence of the substring "track" is the phase's own mandated negated construction ("it does not track or announce anything on its own"), which `companion/test_config_page.py::_calendar_forbidden_vocabulary_absent` explicitly asserts is present as a negation while independently regex-banning any affirmative `tracks`/`is tracking`/`watching`/`monitoring` claim — see Note below. `_calendar_no_preview_no_count_in_rendered_page` renders a populated registry and asserts no airport code, airline code, or derived flight-count phrase appears anywhere on the page. |
| 11 | Settings page: 3-state text-only status line, no URL leak, theme select correctly wired, POST gated | ✓ VERIFIED | `companion/test_config_page.py` (127/127 pass): three mutually-exclusive status strings incl. `concise_timestamp_html()` for the synced state and honest pending-fallback on an unparseable timestamp; `configured_calendar_url` has zero call sites anywhere under `companion/` (`grep -rc` = 0 in every file); theme select carries exactly one `calendar_theme_id` field with `THEME_IDS`-ordered options; `handle_post()` refuses non-member/adversarial payloads with the existing generic flash and writes nothing. |
| 12 | `device_config.json`'s `calendar_theme_id` degrades to `None` (never `DEFAULT_THEME_ID`) on any hostile/absent value, on both read and write paths | ✓ VERIFIED | `server/device_config.py`: `normalise_calendar_theme_id()` degrades to `None`; `save_device_config()` raises `ValueError` pre-write on a non-member value, leaving the file byte-identical. `server/test_config_history.py` (60/60 pass) exercises 7 hostile on-disk shapes, each degrading to `None` and never `DEFAULT_THEME_ID`. |
| 13 | `render.py` untouched across the whole phase; no new dependency added | ✓ VERIFIED | `git diff --stat` from the commit immediately before the first phase-16 commit (`a564872~1`) through `HEAD` for `server/plane/render.py` and `server/requirements*.txt` is empty in both cases. `git log -- server/plane/render.py` shows the last touch predates Phase 16 entirely (Phase 12). |

**Score:** 13/13 truths verified (0 present-but-behavior-unverified — the one behavior-dependent truth, #6, has genuine passing behavioral evidence with a mutation-sensitive test, not presence alone).

### Note on Truth #10 (the copy guard)

The phase's own `16-05-PLAN.md` included an illustrative one-line verification command banning the literal substring `"track"`. That literal command would fail against the shipped copy, because the locked `CALENDAR_SECTION_CAPTION` (itself dictated by `16-UI-SPEC.md`'s Copywriting Contract) requires the sentence *"it does not track or announce anything on its own"* verbatim — a negation that contains the substring but asserts the opposite of what the ban intends. The executor did not use that literal command; instead `companion/test_config_page.py::_calendar_forbidden_vocabulary_absent` implements the correct, more precise check (bans affirmative `tracks`/`is tracking`/`watching`/`monitoring` regexes and a list of role/real-time phrases, while positively requiring the mandated negated construction), with an in-file comment recording the reasoning. This is judged a defensible, documented engineering correction of a self-contradictory illustrative command in the plan body — not a violation of the actual intent (measured finding 3's overstatement guard) — and is not counted as a gap. Flagging it here for visibility rather than silently passing over it.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/plane/calendar_rules.py` | Leaf module: parser, registry, fetch, matcher | ✓ VERIFIED | 1425 lines; all 22 functions from plans 16-01/03/04/06 present; AST-verified leaf import list `{datetime, ipaddress, json, os, re, requests, server(.device_config), socket, sys, threading, urllib.parse}` — no forbidden `server.plane.*` import. |
| `server/test_calendar_rules.py` | Hermetic harness, no network calls, ledger-enforced | ✓ VERIFIED | 74/74 checks pass; registered in `scripts/run-all-tests.sh` (19 harnesses). |
| `server/fixtures/calendar_crewwebplus_redacted.ics` | Synthetic 11-event fixture with provenance record | ✓ VERIFIED | Present; `server/fixtures/README.md` carries its provenance section; `git ls-files '*.ics'` lists exactly this one path. |
| `server/device_config.py` | `calendar_theme_id` key, two-gate validation | ✓ VERIFIED | Present at lines 479 (normaliser), 635 (read), 649/713/753 (write gate/carry-forward). |
| `server/plane/colour_rules.py` | `resolve_effective_theme_id(..., calendar_theme_id=None)` | ✓ VERIFIED | Additive 4th param, checked first; no new import added (diff-confirmed); docstring's forbidden-import list now names `calendar_rules`. |
| `server/poll_loop.py` | One refresh call, one match call, both resolver calls updated | ✓ VERIFIED | Exact counts match plan's pinned criteria: 6 `build_canvas(` calls (4 bare + 2 resolved), 1 `match_calendar_theme(`, 1 `refresh_calendar_registry(`, 2 `calendar_theme_id=` keyword uses. |
| `companion/pages/config_page.py` | Calendar Settings group, locked copy, POST gate | ✓ VERIFIED | `calendar_group()` present, wired into `render()` after Display and before form close; `handle_post()` extended with membership test. |
| `companion/app.py` | `calendar_configured`/`calendar_last_synced_at` ctx keys | ✓ VERIFIED | Present in `page_context()`; zero `configured_calendar_url` or `SKYPANE_CALENDAR_ICS_URL` literal references anywhere under `companion/`. |
| `deploy/skypane.env.example` | `SKYPANE_CALENDAR_ICS_URL` documented as a credential | ✓ VERIFIED | Present with placeholder value and full documentation of scope/reader/cadence. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `calendar_rules.py` | (never) `colour_rules.py` | leaf-import contract | ✓ WIRED (as absence) | AST-confirmed no `colour_rules` import in `calendar_rules.py`; the precedence is instead wired via `poll_loop.py` computing the value and passing it as a keyword argument. |
| `colour_rules.py` | (never) `calendar_rules.py` | leaf-import contract | ✓ WIRED (as absence) | `git diff` shows zero added import lines in `colour_rules.py`; AST-confirmed. |
| `poll_loop.py` flight-detected branch | `calendar_rules.match_calendar_theme()` → `colour_rules.resolve_effective_theme_id(calendar_theme_id=...)` | direct call, in order after `enrich.resolve_route()` | ✓ WIRED | Ordering script in the plan's own acceptance criteria re-derived and confirmed manually: match call sits after `route = enrich.resolve_route(...)` and before the first `resolve_effective_theme_id(` call. |
| `poll_loop.py` held/repaint branch | persisted `poll_state["last_calendar_theme_id"]` → `colour_rules.resolve_effective_theme_id(calendar_theme_id=...)` | reuse, not recompute | ✓ WIRED | Confirmed by direct code read (line 1315-1317) and by the mutation-sensitive clock-advance test. |
| `companion/pages/config_page.py` | `calendar_rules.calendar_is_configured()` (never `configured_calendar_url()`) | presence-only boolean | ✓ WIRED | `grep -rc 'configured_calendar_url' companion/` = 0 across every file. |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `bash scripts/run-all-tests.sh` | `Result: PASS`, 19/19 harnesses, 92% coverage | ✓ PASS |
| Lint | `server/.venv/bin/python3 -m ruff check .` | `All checks passed!` | ✓ PASS |
| `server/test_calendar_rules.py` | direct run | `calendar_rules: 74/74 checks pass` | ✓ PASS |
| `server/test_colour_rules.py` | direct run | `colour_rules: 33/33 checks pass` | ✓ PASS |
| `server/test_config_history.py` | direct run | `config-history: 60/60 checks pass` | ✓ PASS |
| `server/test_poll_loop.py` | direct run | `poll-loop: 80/80 checks pass` | ✓ PASS |
| `companion/test_config_page.py` | direct run | `config-page: 127/127 checks pass` | ✓ PASS |
| No static airline table | `grep -rn '"TO"\|"VY"\|"EJU"\|"TVF"' server/plane/calendar_rules.py` | no matches | ✓ PASS |
| `render.py` untouched, whole phase | `git diff --stat a564872~1..HEAD -- server/plane/render.py` | empty | ✓ PASS |
| No new dependency, whole phase | `git diff a564872~1..HEAD -- server/requirements.txt server/requirements-dev.txt` | empty | ✓ PASS |
| Debt markers | `grep -n 'TBD\|FIXME\|XXX' <every phase-16-touched file>` | none | ✓ PASS |

### Requirements Coverage

Not applicable — the phase's own front matter and ROADMAP.md entry both state "Requirements: None expected — unmapped phase promoted from a seed, matching Phases 10-15's precedent." No REQUIREMENTS.md ID maps to Phase 16. Per this verification's brief, this absence is not reported as a finding; verification proceeded against `16-CONTEXT.md`'s D-01 through D-04 instead (see Observable Truths above).

### Anti-Patterns Found

None. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers, no `console.log`-only stubs, no hardcoded-empty stub returns, in any file this phase touched.

### Human Verification Required

1. **Settings page copy/behaviour, eyes-on** (deferred to end-of-phase per `workflow.human_verify_mode: end-of-phase`, carried in both `16-05-PLAN.md`'s and `16-07-PLAN.md`'s `<human-check>` blocks)
   **Test:** Load the companion Settings page with `SKYPANE_CALENDAR_ICS_URL` unset, then set to a real feed.
   **Expected:** The URL appears nowhere; the copy reads as "colours a flight on screen", never as tracking/watching/announcing; the theme select behaves like the Rules add-form's and dirties the save bar correctly.
   **Why human:** Visual/tone confirmation; deliberately deferred rather than blocking each plan, per this project's workflow mode.

2. **`/gsd-secure-phase 16`** (mandatory phase close-out gate, not yet run)
   **Test:** Run the retroactive security-verification agent over the phase's consolidated `T-16-*` threat register (SSRF, secret handling, DoS, tamper, privacy) spanning all seven plans.
   **Expected:** Confirmation that the per-plan STRIDE mitigations this code-verification already exercised (Observable Truths #7-#9 above) hold up under the dedicated security agent's own analysis, with no residual high-severity finding.
   **Why human/agent:** `ROADMAP.md`'s "Closes with" clause and `16-VALIDATION.md`'s Sampling Rate both name this as a mandatory, separate phase-gate pass. No `16-SECURITY.md` exists yet in the phase directory, confirming it has not run.

Per this verification's explicit brief, neither item above is a gap — both are recorded remaining obligations for phase close-out, not missing implementation. No on-glass verification is expected or required: a calendar match resolves to an already-registered theme id, so nothing new reaches the panel (confirmed: `render.py` untouched for the whole phase).

### Gaps Summary

No gaps found. All 13 derived must-have truths (spanning D-01 separation, D-02 precedence, D-04 match key and its two research corrections, the clock-dependency/both-branches invariant, SSRF/secret/DoS hardening, the copy guard, and the standing D-07/no-new-dependency gates) are verified against the actual codebase — code read directly, not SUMMARY.md claims — and confirmed by a live, passing 19-harness/92%-coverage test suite plus a clean `ruff check`. The two outstanding items (human eyes-on the Settings copy, and the mandatory `/gsd-secure-phase 16`) are deliberately deferred phase-closure obligations per this project's own workflow configuration, not implementation gaps.

---

*Verified: 2026-09-07T23:58:35Z*
*Verifier: Claude (gsd-verifier)*
