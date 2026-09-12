---
phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with
plan: 07
subsystem: ui
tags: [config-page, i18n, css, url-parsing, secret-handling]

# Dependency graph
requires: ["21-01", "21-02", "21-03", "21-04", "21-05"]
provides:
  - "companion/pages/config_page.py — calendar_group(configured, drift, last_synced_at, last_attempt_at, now, entry_count, errors=None, submitted=None, state_dir=None): the ONE merged Calendar card (status row, a not-connected/connected state branch, 'How it works') plus a data-only disconnect-form sibling fragment concatenated onto the same return value — calendar_connect_section()/calendar_disconnect_section() are retired outright"
  - "companion/pages/config_page.py — _masked_calendar_url(url): the one function in this codebase that reads a stored calendar secret back for display, host + '…' via a real urlsplit() parse, never a byte-offset truncation, empty string (line omitted) on any failure"
  - "companion/static/style.css — .calendar-actions/.calendar-actions--solo, .calendar-disconnect-btn (R-09's one additive small-grey-button rule block), .calendar-masked-url, .text-link — and the retirement of both Calendar-card fusion rules plus the now-empty @supports block that held one of them"
affects: ["21-08"]

tech-stack:
  added: []
  patterns:
    - "merge-three-siblings-into-one-plus-a-data-only-sibling-fragment: calendar_group() now returns card_html + disconnect_form_html concatenated as ONE string, so _nested_wrapper_html()'s single str.replace(needle, ..., 1) call still only touches the card's own outer wrapper (the disconnect form carries no page-section class to collide with)"
    - "screens.GROUP_CALENDAR dropped from render()'s generic per-group `builders` dict, mirroring 21-05's identical fate for screens.GROUP_THEME — a merged card that embeds a real <form> in every state cannot safely live inside the legacy SCOPE_ALL settings form any more, so render()'s Display branch builds it directly, as a sibling of the physical form"
    - "one new call site that reads a stored secret back for display (_masked_calendar_url() via calendar_rules.configured_calendar_url()), deliberately narrow and named as the sole exception to this file's write-only-secret-URL convention"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/i18n_fr/calendar_group.py
    - companion/i18n_fr/display.py
    - companion/test_config_page.py
    - companion/test_companion_app.py

key-decisions:
  - "Confirmed at start of execution, per the launch instructions: the worktree branch had been created at main (614d41e) instead of the phase branch. Fast-forwarded to origin/claude/web-companion-audit-ux-refactor-bqx7si (d9e0338) before touching any file — plans 21-01..21-06 were already merged, so the Calendar card's own compact chip grid was already gone (D-06, from 21-05) and this plan built on the CURRENT config_page.py, not the plan's own pre-wave file:line references (which had drifted by a handful of lines after 21-04/21-05's own edits)."
  - "calendar_group() is the ONE retained merged function name (not a new name) — the acceptance criterion's 'exactly 1 if one function name is retained' branch. calendar_connect_section()/calendar_disconnect_section() are deleted outright, not renamed."
  - "Deferred all masking logic to Task 2, by design: Task 1's calendar_group() keeps its pre-merge signature (no state_dir parameter at all) and its connected branch renders no masked-URL markup — a pure structural merge with zero new secret-reading capability. Task 2 adds state_dir=None and the whole masked-URL line in one place, keeping the 'genuinely new capability' (R-10) isolated to its own commit."
  - "The drifted (permission-unsafe) state gets its own small Disconnect button (no Replace disclosure) inside the not-connected branch — a deliberate, plan-compatible addition beyond the UI-SPEC's own two-state illustration, preserving the pre-merge calendar_disconnect_section()'s identical `configured or drift` predicate for the disconnect form's own presence. Without this, drift would have silently lost the disconnect affordance the retired standalone function always gave it. Documented via a new .calendar-actions--solo CSS modifier (right-aligns a lone button where plain .calendar-actions' space-between would otherwise pin it to the start)."
  - "The disconnect form's own id/method/action attribute order follows 21-UI-SPEC.md §E's exact given markup (id first) rather than the pre-merge function's old method-first order; the button's own form= attribute is written as literal text (form=\"calendar-disconnect-form\"), not a %s interpolation of CALENDAR_DISCONNECT_FORM_ID — matching this file's own established convention (CALENDAR_CONNECT_ROUTE's action attribute) that this module's acceptance gate greps literal attribute text, not an interpolated variable's name."
  - "Task 1's own commit also deletes the now-orphaned French entry for the retired long-sentence 'Disconnect this calendar and delete the flights it supplied' (no question mark) from companion/i18n_fr/display.py, even though the plan's own Task 1 <files> list does not name that file — Task 3's action text explicitly anticipates this cleanup but schedules it there; moving it earlier was necessary because Task 1's own <verify> block runs test_i18n.py, and its dead-translation check (_check_d08_no_dead_translations) fails the moment the English call site disappears, regardless of which task's commit removes it."
  - "companion/test_companion_app.py's own pre-existing T-17-FLASH leak-guard check (_calendar_sync_failure_never_leaks_the_url) is extended in Task 2's commit, outside this plan's own files_modified list — the masked-URL feature's own host-appears-once-connected behavior directly (and correctly) breaks that check's old 'host never appears anywhere' assumption; SCOPE_BOUNDARY Rule 1 (auto-fix a bug this task's own change causes) applies."

requirements-completed: [CFG-21]

# Metrics
duration: ~130min
completed: 2026-09-12
---

# Phase 21 Plan 07: Calendar in one tile — masked URL, replace link, small grey Disconnect Summary

**One merged `calendar_group()` now renders the Calendar card's status row, a not-connected/connected state branch (write-only URL field, or a host-only masked feed URL plus a "Replace the feed URL" disclosure and a small grey Disconnect button), and "How it works" — retiring the three-piece split and both `:has()` CSS fusion rules that used to visually glue it together.**

## Performance

- **Duration:** ~130 min
- **Started:** 2026-09-12
- **Completed:** 2026-09-12
- **Tasks:** 3
- **Files modified:** 6 (across all three tasks; no file created)

## Accomplishments

- `companion/pages/config_page.py`: `calendar_group()` merges `calendar_group()`/`calendar_connect_section()`/`calendar_disconnect_section()` into ONE `<div class="page-section" data-dirty-section="Calendar">` plus a data-only disconnect-`<form>` sibling fragment, both returned concatenated from a single call. Not-connected (including the drifted case) renders the write-only feed-URL field inline, unwrapped, with the primary "Connect calendar" button; drift additionally gets a small, right-aligned Disconnect button with no Replace disclosure. Connected renders the masked feed URL, then a `.calendar-actions` line holding the same connect form — relabelled "Replace" — behind a `<details class="calendar-url-disclosure"><summary class="text-link">` disclosure, plus the small grey Disconnect button cross-submitting via `form="calendar-disconnect-form"`.
- `companion/pages/config_page.py`: `_masked_calendar_url(url)` — the one new function in this module that reads a stored secret back for display: `urlsplit(url).netloc` plus an ellipsis, never a byte-offset truncation, degrading to the empty string (line omitted, never fabricated) on any parse failure, empty netloc, or falsy input.
- `companion/pages/config_page.py`: `screens.GROUP_CALENDAR` is dropped from `render()`'s generic per-group `builders` dict — the merged card now embeds a real `<form>` in every state, which would nest inside the legacy SCOPE_ALL settings form if left there (the identical reason 21-05 already retired `screens.GROUP_THEME` from that same dict). `render()`'s Display branch builds the merged card directly, as a sibling of the physical form, exactly like the Frame colours card.
- `companion/static/style.css`: both Calendar-card fusion rules (`.page-section:has(+ .calendar-disconnect-form)`, `.calendar-disconnect-form`) are deleted, and the now-empty `@supports selector(:has(*))` block that held the first is deleted outright — the whole-file pinned block count moves from 2 to 1. New rules: `.calendar-actions`/`.calendar-actions--solo` (layout), the one additive `.calendar-disconnect-btn` block (R-09 — 30px/12px, matching this app's existing bare-button touch-target register at ≥960px, not a new exception), `.calendar-masked-url` (`--font-mono`), and the new one-line `.text-link` rule.
- `companion/i18n_fr/calendar_group.py`: adds `"Replace": "Remplacer"` and `"Disconnect": "Déconnecter"` — the two new short button-text constants (`CALENDAR_REPLACE_BUTTON_TEXT`, `CALENDAR_DISCONNECT_BUTTON_TEXT`) the merge introduces.
- `companion/i18n_fr/display.py`: the now-orphaned French entry for the retired long-sentence Disconnect-button label is deleted in the same commit as its English source constant.
- `companion/test_config_page.py`: every check that called either retired function directly, or relied on Calendar rendering on the legacy SCOPE_ALL scope, is retargeted in place; five new checks added (exactly one Calendar page-section on Display, no nested `<form>` across all four Calendar states, the new short button-copy fidelity against 21-UI-SPEC.md, a hostile-stored-URL renders-no-masked-line check, and neither retired fusion selector survives in style.css). `EXPECTED_CHECK_COUNT` 215 → 220 across the three tasks.
- `companion/test_companion_app.py`: the pre-existing T-17-FLASH leak-guard check is extended (not replaced) to assert the masked host + ellipsis legitimately appears once a calendar connects, while the token/path/query-parameter/whole-URL still never do — a Rule 1 fix outside this plan's own file list, made necessary by Task 2's own change.
- `ruff check .` clean; every harness named in the plan's own `<verification>` section reports either full green or exactly its documented pre-existing failures (2 WR-11 read-only-directory cases in `test_companion_app.py`, 1 `anomaly_active()` case in `test_status_pages.py`).

## Task Commits

1. **Task 1: Merge the three calendar builders into one card** - `3a34d94` (feat)
2. **Task 2: The host-only masked feed URL** - `334a80f` (feat)
3. **Task 3: Retire the fusion CSS, style the small grey button, re-derive the :has() pin** - `be8ea12` (style)

_No separate plan-metadata commit at execution time — SUMMARY.md/STATE.md/ROADMAP.md updates are owned by the orchestrator after all worktree agents in this wave complete, per the launch instructions; this SUMMARY.md is committed separately as the final commit of this plan's own execution._

## Harness Counts (before → after)

| Harness | Before | After | Notes |
|---|---|---|---|
| `companion/test_config_page.py` | 215 | 220 | +3 (Task 1: exactly-one-page-section, no-nested-form, 21-UI-SPEC.md copy-fidelity checks); +1 (Task 2: hostile-stored-URL check, two existing secret-leak checks extended in place); +1 (Task 3: neither-retired-selector-survives check) |
| `companion/test_i18n.py` | 22 | 22 | net 0 (no check added/removed; the D-08 dead-translation scan simply covers the two new short button-copy keys and no longer covers the retired long-sentence entry) |
| `companion/test_companion_app.py` | 258 | 258 | net 0 (the T-17-FLASH leak-guard check's body retargeted in place, outside this plan's own file list — see Deviations) |
| `companion/test_status_pages.py` | 218 | 218 | net 0 (no test-file edit) |
| `companion/test_view_pages.py` | 114 | 114 | net 0 (no test-file edit) |
| `companion/test_contrast_check.py` | 41 | 41 | net 0 (no test-file edit) |

Real on-disk pass counts at the final commit: `test_config_page.py` 220/220, `test_i18n.py` 22/22, `test_companion_app.py` 256/258 (the two documented WR-11 root-sandbox FAILs), `test_status_pages.py` 217/218 (the one documented `anomaly_active()` FAIL), `test_view_pages.py` 114/114, `test_contrast_check.py` 41/41.

## Files Created/Modified

- `companion/pages/config_page.py` — `calendar_group()` rewritten as the merged builder; `_masked_calendar_url()` (new); `calendar_connect_section()`/`calendar_disconnect_section()` deleted; `CALENDAR_REPLACE_BUTTON_TEXT`/`CALENDAR_DISCONNECT_BUTTON_TEXT`/`CALENDAR_DISCONNECT_FORM_ID` (new constants); `CALENDAR_DISCONNECT_CHECKBOX_LABEL` deleted; `_display_groups_html()` narrowed to a 2-tuple return (Calendar's own slot removed); `render()`'s `builders` dict loses `screens.GROUP_CALENDAR`; `render()`'s Display branch builds the merged card directly and threads `state_dir`; the two separate `calendar_connect_html`/`calendar_disconnect_html` return-tuple slots removed
- `companion/static/style.css` — both Calendar-card fusion rules and their now-empty `@supports` block deleted; `.calendar-actions`/`.calendar-actions--solo`/`.calendar-disconnect-btn`/`.calendar-masked-url`/`.text-link` added
- `companion/i18n_fr/calendar_group.py` — `"Replace"`/`"Disconnect"` added
- `companion/i18n_fr/display.py` — the orphaned long-sentence Disconnect-label French entry deleted
- `companion/test_config_page.py` — extensive retargeting/deletion/addition (see Harness Counts); `EXPECTED_CHECK_COUNT` re-derived three times, once per task
- `companion/test_companion_app.py` — one existing check's body retargeted (Deviations)

## Decisions Made

See `key-decisions` in the frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Deleted an orphaned French catalogue entry in Task 1's own commit, ahead of the plan's own Task 3 scheduling**
- **Found during:** Task 1, running `companion/test_i18n.py` as part of its own `<verify>` step
- **Issue:** Retiring `CALENDAR_DISCONNECT_CHECKBOX_LABEL`'s only call site (inside the now-deleted `calendar_disconnect_section()`) orphans its matching French entry in `companion/i18n_fr/display.py` — `_check_d08_no_dead_translations()` fails immediately once the English call site is gone, regardless of which task's commit does the deletion. The plan's own Task 3 action text anticipates this exact cleanup ("If a French entry ... was orphaned by Task 1's merge ... delete it here") but schedules it in Task 3, whose own `<files>` list is the only one naming `companion/i18n_fr/display.py` — Task 1's own `<files>` list does not.
- **Fix:** Deleted the orphaned entry in Task 1's own commit instead, so Task 1's own `<verify>` (which runs `test_i18n.py`) stays green. Documented in `key-decisions`.
- **Files modified:** `companion/i18n_fr/display.py`
- **Verification:** `companion/test_i18n.py` 22/22 at every subsequent task's own verify step.
- **Committed in:** `3a34d94` (Task 1)

**2. [Rule 1 - Bug] Extended `companion/test_companion_app.py`'s pre-existing T-17-FLASH leak-guard check, outside this plan's own file list**
- **Found during:** Task 2, running `companion/test_companion_app.py` after wiring `state_dir` through to the masked-URL helper
- **Issue:** `_calendar_sync_failure_never_leaks_the_url` asserts a stored calendar host never appears anywhere in the served Settings page — directly contradicted by D-14/R-10's own explicit requirement (the masked host legitimately appears once connected). This plan's own `files_modified` list does not name `companion/test_companion_app.py`, but the failure is a direct, mechanical consequence of Task 2's own change (SCOPE_BOUNDARY Rule 1 explicitly permits this).
- **Fix:** Retargeted the check's body to assert the masked host + ellipsis fragment DOES appear on the served page while the token/path/query-parameter/whole-URL still never do — narrowing, not removing, the original leak guard. No count change (one existing `check(...)` call site retargeted in place).
- **Files modified:** `companion/test_companion_app.py`
- **Verification:** `companion/test_companion_app.py` 256/258 (only the two documented WR-11 root-sandbox FAILs).
- **Committed in:** `334a80f` (Task 2)

**3. [Rule 3 - Blocking] Several of my own explanatory comments contained the exact literal strings this plan's own acceptance-criteria greps scan for**
- **Found during:** Task 1/Task 2, during acceptance-criteria verification
- **Issue:** Docstring/comment mentions of `form="calendar-disconnect-form"` and `<p class="calendar-masked-url">` (explaining the design in prose) tripped the plan's own `grep -c ... outputs 1` acceptance checks against the raw file text — the same class of self-inflicted friction every prior plan in this phase has documented for this exact codebase's convention.
- **Fix:** Reworded every avoidable literal occurrence to describe the same thing without the exact matched substring, keeping the one genuinely load-bearing literal occurrence in each case (the actual markup-emitting code).
- **Files modified:** `companion/pages/config_page.py`, `companion/static/style.css`
- **Verification:** every named acceptance-criteria grep in all three tasks now returns its exact expected count.
- **Committed in:** `3a34d94`, `334a80f`, `be8ea12`

### Not Fixed — Flagged Instead

None.

---

**Total deviations:** 3 auto-fixed (1 Rule 1 - orphaned-translation cleanup moved earlier than nominally scheduled, 1 Rule 1 - a pre-existing leak-guard check outside this plan's own files narrowed to match the deliberately-widened masking contract, 1 Rule 3 - self-inflicted grep trips).
**Impact on plan:** No scope creep. The first deviation is purely a commit-ordering correction (the cleanup itself was already the plan's own instruction). The second is the minimum fix needed to make an existing, unrelated-file security regression test agree with D-14/R-10's own explicit requirement, fully covered by the extended check. The third is cosmetic wording only.

## Known Stubs

None.

## Threat Flags

None — every threat this plan's own STRIDE register named (T-21-24 information disclosure via the masked URL, T-21-25 XSS via the masked host/status detail, T-21-26 tampering via the small Disconnect button, T-21-27 tampering via cross-form submission, T-21-28 tampering via the connect field ever pre-filled) was mitigated exactly as specified:
- The mask is `urlsplit(url).netloc` plus an ellipsis — a real parse, never a byte-offset truncation — and degrades to the empty string (line omitted) on any failure; pinned by the two extended secret-leak checks (render-function and real-served-HTTP-bytes) plus a new hostile-stored-value check (`"not a url"`, `""`, a `javascript:` URI).
- Every interpolation in `calendar_group()`/`_masked_calendar_url()`'s caller crosses `escape_html()`.
- The confirmation mechanism (`data-confirm`/`data-confirm-value`/the hidden, empty confirm field, the server-rendered confirmation page) is byte-identical to the retired standalone function's own — only the button's surrounding markup and size changed.
- The disconnect form is a data-only sibling with its own id, never a descendant of `<form id="settings-form">` or of the card's own connect/replace form — pinned by a new dedicated no-nested-form check across all four Calendar states, plus the retargeted "disconnect form's opening tag appears after the settings form's own closing tag" check.
- The write-only connect field still never carries a `value` attribute in either state, pinned by the retargeted `_calendar_connect_field_never_carries_value_in_either_state` check.

## Issues Encountered

- The worktree branch was initially created at `main` (614d41e) rather than the phase branch — resolved by fast-forwarding to `origin/claude/web-companion-audit-ux-refactor-bqx7si` (d9e0338) before touching any file, per the launch instructions. Confirmed the Calendar card's own compact chip grid was already gone (D-06, merged via 21-05) before starting.
- The plan's own `<interfaces>` file:line references had drifted by tens of lines from the current `config_page.py`/`test_config_page.py` (both files were touched by intervening plans 21-04/21-05) — every check named in the plan's interfaces block was located by name/content rather than by its stated approximate line number, and several had already been renamed by 21-05 (e.g. `_calendar_group_no_inline_js_and_chip_grid_within_form` → `_calendar_group_no_inline_js_and_chip_grid_cross_submits_form`).
- Several pre-existing tests exercised `calendar_group()`'s render path via the DEFAULT (`SCOPE_ALL`) render scope — a legacy path that, after this task's own change, no longer renders Calendar content at all (the merged card cannot safely live inside SCOPE_ALL's own physical settings form, mirroring 21-05's identical treatment of the Frame colours card). Every such check was retargeted to `scope=config_page.SCOPE_DISPLAY` explicitly, with its own placement assertions re-derived to match the merged card's real document position (a sibling AFTER the settings form's own closing tag, not before it).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- The Calendar card is one real `<section class="page-section">` in both states, with no second Calendar card and no trailing disconnect card anywhere on the Display scope.
- The masked URL is host-only and parse-derived; no path, query, token or fragment character can reach the page or the wire — extended coverage now runs against both the render function and the real served HTTP bytes.
- "Replace the feed URL" is a `<details>` link whose button reads "Replace"; Disconnect is small, grey, right-aligned, and still confirms via the unchanged two-step mechanism.
- Both fusion CSS rules and the now-empty `@supports` block that held one of them are gone; the whole-file feature-query block count is now 1, re-derived and pinned.
- Plan 21-08 (the phase's own cross-cutting headless sweep) inherits a Calendar card whose visual shape is now genuinely one nested card in both languages/viewports — the `<human-check>` item this plan's own `<verification>` section folds into 21-08 (connected card shows one status line, the masked host, the Replace link with the small grey Disconnect button on the same line; clicking Disconnect still confirms) is ready for that sweep.

## Self-Check: PASSED

- FOUND: `companion/pages/config_page.py` (contains `_masked_calendar_url`)
- FOUND: `companion/static/style.css` (contains `calendar-disconnect-btn`)
- FOUND: `companion/i18n_fr/calendar_group.py` (contains `"Disconnect": "Déconnecter"`)
- FOUND: `.planning/phases/21-companion-feedback-round-3-frame-controls-up-front-home-with/21-07-SUMMARY.md`
- FOUND commit `3a34d94` (Task 1)
- FOUND commit `334a80f` (Task 2)
- FOUND commit `be8ea12` (Task 3)

---
*Phase: 21-companion-feedback-round-3-frame-controls-up-front-home-with*
*Completed: 2026-09-12*
