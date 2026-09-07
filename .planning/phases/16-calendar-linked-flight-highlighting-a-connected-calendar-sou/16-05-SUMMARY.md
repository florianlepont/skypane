---
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
plan: 05
subsystem: ui
tags: [companion, settings-page, config_page, copywriting-contract, privacy, T-16-SECRET]

requires:
  - phase: 16-02
    provides: "device_config.py's calendar_theme_id key (normalise_calendar_theme_id(), save_device_config() support)"
  - phase: 16-03
    provides: "server/plane/calendar_rules.py's calendar_is_configured(), load_calendar_registry(), CALENDAR_URL_ENV_VAR"
provides:
  - "The Calendar settings group: three-state configured/pending/synced status line, native calendar_theme_id theme select, appended as the last section inside the settings form"
  - "companion/app.py page_context()'s calendar_configured (bool) and calendar_last_synced_at (str|None) keys, both read fresh per request"
  - "deploy/skypane.env.example documentation for SKYPANE_CALENDAR_ICS_URL"
affects: [16-06, 16-07]

tech-stack:
  added: []
  patterns:
    - "Status-line usability check via layout.parse_iso()/age_seconds() directly rather than trusting an empty concise_timestamp_html() return as the unparseable signal"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/app.py
    - companion/test_config_page.py
    - deploy/skypane.env.example

key-decisions:
  - "calendar_group()'s 'usable timestamp' check calls layout.parse_iso()/layout.age_seconds() directly instead of treating an empty concise_timestamp_html() return as the signal, since that function only returns empty for a falsy ts and otherwise echoes the raw value in a non-empty span"
  - "Task 3's forbidden-vocabulary harness check departs from the plan's literal acceptance-criteria one-liner (naive lowercase substring match), which would reject the plan's own mandated copy — see Deviations"

patterns-established:
  - "Locked settings-group copy constants + status-line usability gated by layout.parse_iso()/age_seconds(), not by an empty-return convention"

requirements-completed: []

coverage:
  - id: D1
    description: "Calendar settings group: three-state status line (not configured / pending / synced with absolute+relative timestamp), theme select, no new CSS/icon/flash, appended last inside the settings form"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py::_calendar_status_not_configured_is_exclusive,_calendar_status_configured_pending_is_exclusive,_calendar_status_configured_synced_is_exclusive_with_relative_age,_calendar_status_unparseable_synced_falls_back_to_pending,_calendar_placement_after_display_before_form_close_with_dirty_attr"
        status: pass
    human_judgment: false
  - id: D2
    description: "Copy fidelity to 16-UI-SPEC.md's Copywriting Contract and absence of banned real-time-awareness/crew-role vocabulary"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py::_calendar_copy_fidelity_against_ui_spec,_calendar_forbidden_vocabulary_absent"
        status: pass
    human_judgment: false
  - id: D3
    description: "The calendar URL never reaches rendered markup or served HTTP bytes (T-16-SECRET); the companion process never calls configured_calendar_url()"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py::_calendar_secret_never_reaches_render_function"
        status: pass
      - kind: integration
        ref: "companion/test_config_page.py::_calendar_secret_never_reaches_served_http_bytes (live HTTP round trip, dedicated harness with the env var set)"
        status: pass
    human_judgment: false
  - id: D4
    description: "No flight/route/count preview leaks from the calendar registry onto the Settings page; the rules editor never shows a calendar-sourced row (D-01)"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py::_calendar_no_preview_no_count_in_rendered_page,_calendar_d01_registry_entries_never_appear_in_rules_list"
        status: pass
    human_judgment: false
  - id: D5
    description: "handle_post()'s calendar_theme_id membership gate: valid persists and carries other fields forward, four adversarial payloads rejected with the generic flash and no write, absent leaves an existing value unchanged"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py::_handle_post_calendar_theme_id_valid_persists_and_carries_forward,_handle_post_calendar_theme_id_adversarial_rejected,_handle_post_calendar_theme_id_absent_leaves_unchanged"
        status: pass
    human_judgment: false
  - id: D6
    description: "companion/app.py page_context() threads calendar_configured/calendar_last_synced_at fresh per request; a corrupt registry never 500s the Settings route"
    verification:
      - kind: unit
        ref: "server/plane/calendar_rules.py wiring check + manual live-server verification of a corrupt calendar_rules.json returning 200"
        status: pass
    human_judgment: false
  - id: D7
    description: "16-VALIDATION.md's human-check item: visual confirmation that the URL appears nowhere on the page/source/tooltip, the copy reads as conditional (not tracking/watching), and the theme picker behaves like the Rules add-form's own select"
    verification: []
    human_judgment: true
    rationale: "Requires eyeballing the live companion Settings page with a real SKYPANE_CALENDAR_ICS_URL set and unset; workflow.human_verify_mode is end-of-phase, so this is recorded for that review rather than gated here."

duration: ~22min
completed: 2026-09-08
status: complete
---

# Phase 16 Plan 05: Calendar Settings Group Summary

**Added the Settings page's Calendar group — a three-state configured/pending/synced status line plus a native calendar_theme_id theme select, wired into companion/app.py's page_context() and documented in the deploy env template — with zero new CSS, icon, button, or flash key.**

## Performance

- **Duration:** ~22 min
- **Started:** ~2026-09-07T22:14Z (context gathering)
- **Completed:** 2026-09-07T22:35:53Z (final task commit)
- **Tasks:** 3
- **Files modified:** 4 (`companion/pages/config_page.py`, `companion/app.py`, `companion/test_config_page.py`, `deploy/skypane.env.example`)

## Accomplishments

- `calendar_group()` in `companion/pages/config_page.py`: locked-English copy constants byte-identical to `16-UI-SPEC.md`'s Copywriting Contract, a three-branch not-configured/pending/synced status line (the synced branch interpolating `layout.concise_timestamp_html()`'s raw markup), and a native `<select name="calendar_theme_id">` reusing the Rules add-form's exact option-building loop and field wrapper
- Wired as the seventh and last section inside `<form id="settings-form">`, after Display — `render()`'s zero-disruption append per `16-UI-SPEC.md`'s Placement recommendation
- `handle_post()` gained a `calendar_theme_id` membership gate against `device_config.THEME_IDS`, reusing the existing generic save-failed flash (no new flash constant), passed through to the existing single `save_device_config()` call
- `companion/app.py`'s `page_context()` gained `calendar_configured` (bool, `calendar_rules.calendar_is_configured()`) and `calendar_last_synced_at` (str|None, `calendar_rules.load_calendar_registry()`), both read fresh per request — `configured_calendar_url()` has zero call sites anywhere under `companion/` (verified by a recursive zero-count grep, not just review)
- `deploy/skypane.env.example` documents `SKYPANE_CALENDAR_ICS_URL` as a credential, with a non-URL-shaped placeholder matching the file's existing discipline
- `companion/test_config_page.py` extended with 18 new checks covering every `<behavior>` bullet: status-state exclusivity, unparseable-timestamp fallback, copy fidelity against the spec file, forbidden-vocabulary absence, secret-containment (both in-process `render()` and a real HTTP round trip via a second dedicated harness), no-preview/no-count, D-01 (no calendar row in the rules editor), theme-select population/order/selection, placement, no-JS correctness, and `handle_post()`'s valid/adversarial/absent-field behavior — `EXPECTED_CHECK_COUNT` 109 → 127

## Task Commits

1. **Task 1: Add the Calendar group to config_page.py** — `69d0ebe` (feat)
2. **Task 2: Thread calendar presence/last-synced into app.py, document env var** — `33d31c5` (feat)
3. **Task 3: Extend test_config_page.py with the Calendar group's contract** — `61da84d` (test)

**Plan metadata:** pending (this commit)

## Files Created/Modified

- `companion/pages/config_page.py` — `CALENDAR_*` copy constants, `calendar_group()`, `render()`/`handle_post()` wiring
- `companion/app.py` — `calendar_rules` import, two new `page_context()` keys
- `companion/test_config_page.py` — 18 new checks, `EXPECTED_CHECK_COUNT` 109 → 127, two pre-existing count-shaped checks retargeted in place (6 → 7 dirty-section groups)
- `deploy/skypane.env.example` — `SKYPANE_CALENDAR_ICS_URL` documentation block

## Decisions Made

- `calendar_group()`'s "is this timestamp usable" check calls `layout.parse_iso()`/`layout.age_seconds()` directly rather than trusting an empty `concise_timestamp_html()` return as the unparseable signal (see Deviations — this is a Rule 1 bug fix, not a plan-time design choice, but it changed the shipped implementation from what the plan's prose described).
- Kept the plan's literal `<select>` markup shape (`_rule_add_form_html()`'s exact loop) rather than any alternate theme-picker idiom, per `16-UI-SPEC.md`'s explicit rejection of a third chip grid.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `concise_timestamp_html()` never returns empty for an unparseable-but-truthy timestamp**

- **Found during:** Task 3, writing the "unparseable synced timestamp falls back to pending" check (TDD RED confirmed the bug: the check failed against Task 1's own implementation).
- **Issue:** The plan's Task 1 action text instructed calling `layout.concise_timestamp_html(last_synced_at, now, fallback="")` and treating an empty return as "not usable." But `concise_timestamp_html()`'s actual, documented contract only returns the escaped `fallback` when `ts` is falsy (`None`/`""`); for a truthy string that fails to parse, it instead returns a non-empty `<span class="mono" title="...">...</span>` echoing the raw value verbatim (its own "degrade gracefully, never raise" contract). The initial implementation therefore rendered the *raw stored garbage string* inside a mono span for a corrupt `last_synced_at`, instead of falling back to the pending copy as `16-UI-SPEC.md` Open Question 3 requires.
- **Fix:** `calendar_group()` now determines "usable" via `layout.parse_iso(last_synced_at) is not None and layout.age_seconds(last_synced_at, now) is not None` (the same two calls `concise_timestamp_html()` makes internally), only calling `concise_timestamp_html()` once usability is already confirmed.
- **Files modified:** `companion/pages/config_page.py`
- **Verification:** `companion/test_config_page.py::_calendar_status_unparseable_synced_falls_back_to_pending` passes; confirmed live (temporarily reverted the fix, watched the check fail with the expected reason, restored it).
- **Committed in:** `61da84d` (Task 3 commit, alongside the test that caught it)

**2. [Rule 1 - Bug, plan-authoring] Two of Task 1's own acceptance-criteria one-liners are unsatisfiable against the plan's own mandated copy**

- **Found during:** Task 1's acceptance-criteria verification pass, before Task 3 began.
- **Issue:** The plan's literal forbidden-vocabulary check (`bad=[w for w in ('track', ..., 'his', ...) if w in blob]`) is a naive lowercase substring match with no word-boundary awareness. Run against the byte-identical, plan-mandated `CALENDAR_SECTION_CAPTION` — which itself must contain the negated construction "it does not track or announce anything on its own" per `16-UI-SPEC.md`'s own locked Copywriting Contract — the check fails on `'track'` (present only inside "does *not* track") and on `'his'` (a false-positive substring of "this theme"). Satisfying the acceptance criterion literally would require paraphrasing the spec's own mandated sentence, which the plan's higher-priority `must_haves.truths` explicitly forbids ("byte-identical to 16-UI-SPEC.md's Copywriting Contract").
- **Fix:** Implemented Task 3's `_calendar_forbidden_vocabulary_absent` check with the evident actual intent instead: word-boundary-aware regex checks for AFFIRMATIVE tracking/watching/monitoring claims and real-time/crew-role phrases (`16-UI-SPEC.md`'s "What this section deliberately does NOT say" section), plus a positive assertion that the mandated negated "does not track" construction survives verbatim. Did not alter the locked copy to dodge the substring collision.
- **Files modified:** `companion/test_config_page.py` (the corrected check); `companion/pages/config_page.py`'s copy is unaffected (kept verbatim per the higher-priority must-have)
- **Verification:** Ran the plan's literal one-liner by hand against the shipped copy to confirm the exact false-positive pair (`['track', 'his']`); the corrected check in the harness passes and was confirmed live (temporarily injected an affirmative "3 upcoming flights" phrase and a leaked-secret string — both caused the intended checks to fail with the right reasons, then were reverted).
- **Committed in:** `61da84d` (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 bugs — one in the shipped code, one in the plan's own verification script)
**Impact on plan:** Both fixes were necessary for correctness; neither changed scope. The forbidden-vocabulary deviation is documented in detail because a future reader re-running the plan's literal acceptance-criteria command verbatim will see it fail against this (correct, spec-compliant) implementation — that failure is expected and should not be "fixed" by paraphrasing the locked copy.

## Issues Encountered

- This worktree had no `server/.venv` provisioned (unlike sibling worktrees). Symlinked `server/.venv` to the sibling `airplanes-api-sustainability-a4b703` worktree's already-built venv — the same network-free bootstrap pattern already established and gitignored for this repo (see `.gitignore`'s "Symlinked venv (phase 14 plan 14-01 Task 1)" precedent). No repo changes; purely a local execution convenience.

## Next Phase Readiness

- `calendar_theme_id` is now settable end-to-end from the web UI (validated write path) and the companion process has a working presence/last-synced read path — 16-06 (the resolver/matcher) and 16-07 can build on both without further wiring here.
- Full suite green: `scripts/run-all-tests.sh` exits 0 (`Result: PASS`), 93% coverage, `companion/test_config_page.py` at 127/127.
- The one open item is the phase's single manual/human-check row (`16-VALIDATION.md` § Manual-Only Verifications) — recorded for the end-of-phase review per `workflow.human_verify_mode: end-of-phase`, not a blocker for this plan.

---
*Phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou*
*Plan: 05*
*Completed: 2026-09-08*
## Self-Check: PASSED

All created/modified files confirmed present on disk; all three task commits (69d0ebe, 33d31c5, 61da84d) confirmed in git log.
