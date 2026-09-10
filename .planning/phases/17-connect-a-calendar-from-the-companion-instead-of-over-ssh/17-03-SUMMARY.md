---
phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh
plan: 03
subsystem: ui
tags: [python, stdlib-http, settings-form, calendar]

requires:
  - phase: 17-02
    provides: >-
      calendar_is_configured()/configured_calendar_url() reading the secret file
      (not the environment), calendar_secret_mode_is_unsafe() for D-02's drift
      predicate, and refresh_calendar_registry()'s min_interval_s bypass param

provides:
  - "A write-only calendar_url text field inside the existing merged Settings form"
  - "A disconnect checkbox (calendar_disconnect), unchecked always, mirror-polarity of theme_arriving_enabled"
  - "calendar_group()'s fourth status branch (drift, checked before not-configured)"
  - "submitted_calendar_signal() - the single carry-forward/set/clear/invalid resolver, ready for plan 17-04 to share"
  - "handle_post()'s calendar_url/calendar_disconnect resolution, gated before persistence, acted on only after it"

affects: [17-04]

tech-stack:
  added: []
  patterns:
    - "Renderer receives only booleans/timestamps, never the secret value, so a leak is structurally impossible at that function (T-17-SECRET)"
    - "A pure resolver function shared by render-time validation and POST-time persistence, returning a small closed set of named outcomes rather than inline branching"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/test_config_page.py

key-decisions:
  - "CALENDAR_STATUS_PERMISSION_UNSAFE was written with no apostrophe/quote so a raw-constant substring check survives escape_html()'s entity rewriting (the same surprise plan 17-02 recorded for CALENDAR_STATUS_NOT_CONFIGURED)"
  - "The URL field and disconnect checkbox were placed between the status line and the theme select, in read-then-act order"
  - "Context key for the drift flag is calendar_drift, matching calendar_configured/calendar_last_synced_at's own naming; render() degrades it to a falsy default until plan 17-04 supplies it"

patterns-established:
  - "submitted_calendar_signal() as the one place a submitted checkbox+field pair's meaning is decided, callable from both a page handler and a future request handler"

requirements-completed: []

coverage:
  - id: D1
    description: "Write-only calendar_url field renders in all four calendar_group() states, never with a value attribute"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#the write-only calendar_url field renders in all four calendar_group() states and never carries a value attribute"
        status: pass
    human_judgment: false
  - id: D2
    description: "calendar_group() itself never emits the stored URL's token/host/path/query-param/whole-URL, independent of render()'s own containment coverage"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#calendar_group() itself, called directly rather than through render(), never emits the token, host, path segment, query-parameter name, or whole URL of a configured calendar"
    human_judgment: false
  - id: D3
    description: "Disconnect checkbox appears only when connected or drifted, and always renders unchecked"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#the disconnect checkbox appears only when the calendar is connected or drifted, and renders unchecked in every state it appears in"
        status: pass
    human_judgment: false
  - id: D4
    description: "The drift status (D-02) is checked before not-configured and reads as actionable without naming a path/filename/URL"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#with the stored calendar link's permissions drifted, render() emits only the drift status string"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#the permission-drift status string names the remedy"
        status: pass
    human_judgment: false
  - id: D5
    description: "The D-07 regression: an empty calendar_url field with no checkbox, submitted twice alongside an unrelated setting change, changes nothing about the calendar"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#the single most important check in this plan (D-07)"
        status: pass
    human_judgment: false
  - id: D6
    description: "Disconnect and replace (D-05) paths write the correct calendar_rules outcome (clear both URL and registry; store the new URL and clear the previous registry)"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#handle_post with the disconnect checkbox at its expected value succeeds"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#handle_post with a different non-empty URL stores the new URL and clears the previous calendar's fetched-entries registry"
        status: pass
    human_judgment: false
  - id: D7
    description: "Contradictory or crafted submissions (URL+checkbox, crafted checkbox value, over-length URL) reject the whole save, including any unrelated field"
    verification:
      - kind: unit
        ref: "companion/test_config_page.py#handle_post with a non-empty URL together with the disconnect checkbox"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#handle_post with a crafted calendar_disconnect value rejects the whole save"
        status: pass
      - kind: unit
        ref: "companion/test_config_page.py#handle_post with a calendar_url longer than CALENDAR_URL_MAX_LEN rejects the whole save"
        status: pass
    human_judgment: false

duration: ~35min
completed: 2026-09-10
status: complete
---

# Phase 17 Plan 03: The write-only feed-URL field, the disconnect checkbox, and the POST-side resolver Summary

**A write-only calendar_url field and a mirror-polarity disconnect checkbox land inside the existing Settings Calendar group, backed by a single resolver function (`submitted_calendar_signal()`) that both render-time validation and POST-time persistence share — proven non-vacuous by mutation.**

## Performance

- **Duration:** ~35 min
- **Completed:** 2026-09-10
- **Tasks:** 3/3
- **Files modified:** 2

## Accomplishments

- `calendar_group()` widened to a fourth (drift) status branch, checked first, and now renders a write-only URL field plus a disconnect checkbox that receives only two booleans and two timestamps — never the URL itself, so a leak is structurally impossible at this function regardless of future edits (T-17-SECRET)
- The disconnect checkbox is the deliberate mirror image of `theme_arriving_enabled`: always rendered unchecked, and its *presence* in the submission (not its absence) means clear — the safe default is doing nothing
- `submitted_calendar_signal()` is the single definition of carry-forward/set/clear/invalid, called once from `handle_post()` and ready for plan 17-04's request handler to call identically
- `handle_post()` gates on the resolver's `invalid` outcome alongside every other membership check (all-or-nothing, before any write), then calls `calendar_rules.save_calendar_url()` only for `set`/`clear` — `carry_forward` never calls it, so an unrelated settings save can never erase the fetched calendar registry
- Confirmed by mutation: inverting the resolver's checkbox-presence gate (the exact D-07 defect) makes the empty-field-with-no-checkbox regression check fail, along with 3 collateral checks; reverting restores 138/138

## Task Commits

1. **Task 1: Copy constants, the field, the disconnect checkbox, and the fourth status state** - `687c160` (feat)
2. **Task 2: The three-way resolver and the POST branch that writes the secret** - `c770704` (feat)
3. **Task 3: Reconcile the harness and pin the field's containment, the checkbox's polarity and the contradiction rejection** - `4493a88` (test)

**Plan metadata:** committed together with this summary.

## Files Created/Modified

- `companion/pages/config_page.py` - Five new copy constants; `calendar_group()` widened to accept a `drift` parameter, four-branch status resolution (drift first), the write-only field and disconnect checkbox markup; `submitted_calendar_signal()` and its four resolution constants; `handle_post()`'s new `invalid` gate and post-persistence `set`/`clear` branch; `render()` threads the new `calendar_drift` context key
- `companion/test_config_page.py` - 11 new checks covering the field's no-value-attribute guarantee, direct-at-the-renderer containment, the checkbox's presence/unchecked contract, the drift status's exclusivity and ordering, the drift status's remedy-naming, the D-07 regression, the disconnect and D-05 replace paths, and three all-or-nothing rejection paths; ledger 127 → 138

## Decisions Made

- **`CALENDAR_STATUS_PERMISSION_UNSAFE` carries no apostrophe, quote, or ampersand.** The Task 1 verification script does a raw-constant substring check against `calendar_group()`'s escaped HTML output; an apostrophe would render as `&#x27;` (the exact surprise plan 17-02 recorded for `CALENDAR_STATUS_NOT_CONFIGURED`) and break that check. The wording was adjusted to avoid the character class entirely rather than working around the escaping downstream.
- **Field and checkbox placement.** Placed between the status line and the theme `<select>`: read the current state, then act on it (paste/disconnect), then set the theme — a natural top-to-bottom reading order the plan left as an open choice.
- **Context key name `calendar_drift`.** Matches the existing `calendar_configured`/`calendar_last_synced_at` naming convention in `companion/app.py`'s page context; `render()` reads it with `ctx.get("calendar_drift")`, degrading to `None` (falsy) until plan 17-04 supplies the real value from `calendar_rules.calendar_secret_mode_is_unsafe(state_dir)`.
- **Resolver constant naming.** `CALENDAR_URL_SIGNAL_{CARRY_FORWARD,SET,CLEAR,INVALID}` rather than a smaller enum-like set, so a future reader cannot mistake one outcome's sentinel for another's.

## Deviations from Plan

None — plan executed exactly as written. The single wording adjustment above (avoiding apostrophes in `CALENDAR_STATUS_PERMISSION_UNSAFE`) is Claude's-discretion copywriting within the plan's own explicit grant ("the exact rendered wording... is Claude's discretion"), not a deviation from a locked requirement.

## Issues Encountered

The Task 1 verification script's own literal-substring check against the drift status constant initially failed because the first-drafted wording ("beyond the frame's own account") contained an apostrophe that `escape_html()` rewrites to `&#x27;`. Caught immediately by running the plan's own verify block before committing; fixed by rewording to avoid the character class, re-verified, then committed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 17-04 can now:
- Call `config_page.submitted_calendar_signal()` from its own request handler and get an identical resolution to `handle_post()`'s, by construction (the plan's own load-bearing requirement)
- Supply the `calendar_drift` context key (`calendar_rules.calendar_secret_mode_is_unsafe(state_dir)`) in `companion/app.py`'s page context — `render()` already reads it and degrades gracefully if it arrives late
- Rely on `calendar_rules.save_calendar_url()` being called correctly from the Settings POST path for `set`/`clear`, and never for `carry_forward`

No blockers. `bash scripts/run-all-tests.sh` is green (92% coverage, run three times to rule out a coverage-collection artifact from a stray concurrent invocation), `server/.venv/bin/ruff check .` is clean, and the polarity mutation was run and reverted cleanly (confirmed by `git diff --stat` showing zero changes to `config_page.py` after revert).

---
*Phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh*
*Completed: 2026-09-10*

## Self-Check: PASSED

Verified on disk and in git history after writing this summary:
- `companion/pages/config_page.py` — FOUND
- `companion/test_config_page.py` — FOUND
- This summary file — FOUND
- Commits `687c160`, `c770704`, `4493a88`, `918f8e3` — all FOUND in `git log --oneline --all`
