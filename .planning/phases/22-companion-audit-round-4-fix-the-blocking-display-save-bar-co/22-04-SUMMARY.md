---
phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co
plan: 04
subsystem: ui
tags: [python, css, frame-strip, health-page, frame-state, i18n, tabular-nums]

# Dependency graph
requires:
  - phase: 22-02
    provides: "server.wake.next_wake_status()'s (next_wake_iso, effective_interval_s, hold_reason) triple, and companion/frame_state.py's resolve_state()/headline_template()/delay_sentence_template() — the one frame-state resolution and the one delay sentence"
  - phase: 22-03
    provides: "companion/pages/health_page.py's never-ran pipeline state and resolution-stats fix — this plan's own Frame-tile edits sit beside, not on top of, that work"
provides:
  - "companion/layout.py's frame_strip_html(): the strip reads frame_state.resolve_state()/headline_template()/delay_sentence_template() instead of a local age>=0 warn trigger — the grace window and the held case are the resolution's job"
  - "companion/layout.py's _frame_strip_cell_html(): one shared 3-row-grid wrapper (label/state+control/caption) for all three strip cells"
  - "data-quick-switch on both strip switch forms — the D-04 handshake plan 22-05 Task 3 keys its leave-guard suppression on, in this same wave"
  - "companion/static/style.css: .frame-strip__cell (shared chrome + 3-row grid), the C2 quiet strip-button rule, the T9 three-edge hover with .frame-strip excluded, the C6 heading-size-override retirement, the one .time-value/.time-value--primary role, and the header comment's C2 accent-reservation delta"
  - "companion/pages/health_page.py's _device_section(): consumes the SAME wake.next_wake_status()/frame_state.resolve_state() result compute_health_state() computes once; a held frame maps to the neutral 'off' device_state, never warn/error, so the nav notification dot cannot light for it"
affects: [22-05, 22-06, 22-07, 22-08, 22-09, 22-12, 22-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scanner-visibility copy constants: companion/test_i18n.py's D-08 AST scan cannot trace an imported module's attribute access (frame_state.HEADLINE_DUE), only a same-file top-level scalar used directly as an i18n.t() argument — so companion/layout.py and companion/pages/health_page.py each keep small, byte-identical local copies of the frame_state.py wording they consume, selected by comparing frame_state's own return value for equality (the DECISION stays sourced from frame_state; only the wording's scanner-visible home is local, until plan 22-08 widens the scan list to include frame_state.py itself)"
    - "Recompute-not-reuse for signature compatibility: frame_strip_html() recomputes wake.next_wake_status() fresh from ctx['last_checkin_ts']/ctx['device_config'] rather than trusting its own next_wake_iso parameter, so home_page.py/config_page.py's call sites (owned by other wave-3/4 plans) never need to change, while the DECISION is still sourced from exactly one function call against exactly one set of inputs"
    - "One wrapper, one 3-row grid, empty tracks: all three Frame-strip cells share frame_strip_cell_html()'s wrapper and frame-strip__row--label/--state/--caption row classes; a cell with nothing for a row still emits that row's own empty div rather than omitting it, which is what a harness can assert as byte-identical row-class lists across all three cells"

key-files:
  created: []
  modified:
    - companion/layout.py
    - companion/static/style.css
    - companion/pages/health_page.py
    - companion/i18n_fr/health.py
    - companion/i18n_fr/home.py
    - companion/test_status_pages.py
    - companion/test_view_pages.py

key-decisions:
  - "frame_strip_html()'s next_wake_iso parameter is kept (never removed) even though its own logic no longer uses it — home_page.py and config_page.py, both owned by other plans in this same wave, still pass it positionally/by keyword, and this plan's files_owned boundary forbids editing either file. The function instead recomputes wake.next_wake_status() itself from ctx['last_checkin_ts']/ctx['device_config'] — the SAME two facts the caller already used to compute the value it passes in — so the two calls can never disagree; only the DECISION (grace window, held detection) is single-sourced, which is what CFG-26 actually requires."
  - "QUICK_ACTION_APPLIES_SENTENCE is kept defined in companion/layout.py (not deleted, contrary to a literal reading of the plan's own action text) because companion/pages/config_page.py and companion/test_config_page.py — both owned by plan 22-05 in this same wave — reference layout.QUICK_ACTION_APPLIES_SENTENCE directly; deleting it would have broken an AttributeError in a file this plan may not edit. frame_strip_html() itself no longer reads it; _FRAME_DELAY_UNKNOWN_TEXT is defined as an alias of it (byte-identical value, not a re-typed literal) so the retired wording's TEXT still resolves as DELAY_UNKNOWN's own copy."
  - "DEVICE_STATE_TEXT is widened to a fourth 'off' key (mirroring PIPELINE_STATE_TEXT's own 22-03-PLAN.md Task 1 precedent) for the frame's held state — a genuinely new, real state this plan's own scope requires, unlike 22-03's deliberate choice not to widen DEVICE_STATE_TEXT for a different (pipeline-only) reason. The existing key-set pin was retargeted in place, not left broken."
  - "Health's Frame tile's own detail row now shows the SAME next-wake clock text the strip's headline shows (via layout.local_clock_text() against the SAME next_wake_iso), replacing the raw last-check-in timestamp _device_section() used to render — but _device_timestamp_only() itself (and the 'device_detail_html' key it feeds Home through) is untouched, since Home's own Frame row is plan 22-07's, not this one's."
  - "device_staleness_thresholds()/staleness_status() are kept as the fallback path for frame_state.resolve_state()'s STATE_UNKNOWN case (no computed next-wake data at all) — every pre-existing direct-call harness fixture that omits the three new keyword arguments is unaffected by this task, by construction."

requirements-completed: []  # CFG-26 is served by three plans (22-02, 22-04, 22-07); CFG-30 by nine; CFG-31 by seven — NOT complete after this one alone.

# Metrics
duration: ~95min
completed: 2026-09-12
---

# Phase 22 Plan 04: The Frame strip and Health's Frame tile read the one frame-state result Summary

**The Frame strip and Health's Frame tile both resolve due/held/late from `companion.frame_state.resolve_state()` fed by the same `wake.next_wake_status()` triple — the nightly false alarm (X2) is pinned dead across both surfaces, the strip's three cells share one wrapper and one three-row grid (B13), its switch buttons are quiet (C2), the update line is demoted to Emphasis size (C6), tile hover leaves the top rail intact (T9), and one `.time-value` role now formats every clock text the strip and tile share (C5).**

## Performance

- **Duration:** ~95 min
- **Started:** 2026-09-12T21:50:00Z (approx.)
- **Completed:** 2026-09-12T23:25:00Z
- **Tasks:** 3 completed
- **Files modified:** 7 (companion/layout.py, companion/static/style.css, companion/pages/health_page.py, companion/i18n_fr/health.py, companion/i18n_fr/home.py, companion/test_status_pages.py, companion/test_view_pages.py — no new files)

## Accomplishments

- **Task 1:** `frame_strip_html()` deletes its own `age_seconds(next_wake...) >= 0` warn trigger outright and instead resolves due/held/late through `frame_state.resolve_state()`/`headline_template()`/`delay_sentence_template()`, fed by a fresh `wake.next_wake_status()` call against the same `ctx["last_checkin_ts"]`/`ctx["device_config"]` the caller already used. All three strip cells now share one `_frame_strip_cell_html()` wrapper and one three-row internal structure (label / state+control / caption), with an empty track where a cell has no content for a row. Both strip switch forms carry the literal `data-quick-switch` attribute — plan 22-05's own D-04 handshake dependency. The two switch-cell captions now show the ONE computed delay sentence (due/held/unknown) instead of a static literal.
- **Task 2:** `.frame-strip__cells` takes `align-items: stretch` (B13); `.frame-strip__cell` is a new shared class carrying padding/hairline/radius/surface plus `display: grid; grid-template-rows: auto auto auto`, applied to all three cells alike. A `.frame-strip__cell button` rule at `(0,1,1)` — equal specificity to `button[type="submit"]`, placed after it in source order, the same mechanism `.logout-form button`/`.dirty-bar__cancel` already use — repaints the strip's two switch buttons quiet (C2); the header comment's accent-reservation list is edited in the same commit to record the delta. The Phase 21 heading-size override on the update cell's headline is retired outright (C6). `.stat-tile:hover, .stat-tile:focus-within`'s four-edge `border-color: transparent` becomes side-and-bottom only, and the whole hover/focus-within reveal is `:not(.frame-strip)`-scoped so the strip never lifts on an inner button hover (T9). One `.time-value`/`.time-value--primary` role is defined and applied to the strip's own next-wake clock text (C5).
- **Task 3:** `health_page._device_section()` consumes the SAME `wake.next_wake_status()` triple `compute_health_state()` computes once, resolved through `frame_state.resolve_state()` — never its own raw age-based decision alone. A held frame maps to the neutral `"off"` device_state (mirroring the pipeline's own 22-03 precedent), so it can never light the Health nav notification dot; `collect_anomalies()` gained the matching `"off"` exemption. The tile's own detail row now renders the SAME next-wake clock text the strip's headline renders, by construction (both format the same `next_wake_iso` through `layout.local_clock_text()`). The nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/Paris) is pinned as one named check proving the strip, the tile and the nav dot all agree and stay neutral.
- Reconciled `companion/i18n_fr/home.py`'s "Expected since %s" French value from "Attendue depuis %s" (feminine agreement) to the locked "Attendu depuis %s" — this plan is the first real consumer of that headline, so it closed the discrepancy 22-02-SUMMARY.md flagged rather than leaving it for 22-05 (which owns no file that string lives in).

## Task Commits

1. **Task 1: The strip reads one result and renders three equal cells** - `0c2c6ae` (feat)
2. **Task 2: The strip's CSS — stretch, quiet buttons, demoted headline, repaired hover, and the one time-value role** - `ba0044b` (feat)
3. **Task 3: Health's Frame tile and the nav notification dot read the same result** - `19dfec1` (feat) — also folds in the Task-1/Task-2-caused `test_view_pages.py` fix (see Deviations)

**Plan metadata:** committed separately below (STATE.md/ROADMAP.md/this SUMMARY).

## Files Created/Modified

- `companion/layout.py` — `frame_strip_html()` rebuilt around `frame_state.resolve_state()`/`headline_template()`/`delay_sentence_template()`; new `_frame_strip_cell_html()` shared cell builder; six new `_FRAME_HEADLINE_*_TEXT`/`_FRAME_DELAY_*_TEXT` scanner-visibility constants and `_FRAME_DOT_CLASS_BY_STATE`; `data-quick-switch` on both switch forms; the clock value wrapped in `<span class="time-value time-value--primary">`; `QUICK_ACTION_APPLIES_SENTENCE` kept (not deleted — see Decisions), `NEXT_UPDATE_TEMPLATE`/`EXPECTED_SINCE_TEMPLATE` retired
- `companion/static/style.css` — `.frame-strip__cell` (shared chrome + 3-row grid) replaces the old bare `.quick-action` chrome rule; `.frame-strip__cell.quick-action` narrowed to the border-left width only; `.frame-strip__row--state` (row 2's flex layout); `.frame-strip__cells` gains `align-items: stretch`; the `.frame-strip__cell--update .status-card__headline` heading-size override deleted (C6); a new `.frame-strip__cell button` quiet-button rule (C2); `.stat-tile:hover/:focus-within` narrowed to three edges and scoped `:not(.frame-strip)` (T9); `.time-value`/`.time-value--primary`/`.time-value__age` (C5); the header comment's accent-reservation delta recorded; a now-dead sub-960px `.quick-action { flex-wrap: wrap; }` rule removed
- `companion/pages/health_page.py` — `DEVICE_STATE_TEXT` widened to a fourth `"off"` key; new `_FRAME_STATE_TO_DEVICE_STATE` mapping; `_device_section()` takes three new optional keyword args and resolves through `frame_state.resolve_state()`, falling back to the pre-existing age-based path only for `STATE_UNKNOWN`; `collect_anomalies()`'s device-state membership check widened to exempt `"off"`; `compute_health_state()` computes `wake.next_wake_status()` once and threads it through
- `companion/i18n_fr/health.py` — new entry: `"Asleep for quiet hours"` -> `"En veille pendant les heures calmes"`
- `companion/i18n_fr/home.py` — `"Expected since %s"` French value reconciled: `"Attendue depuis %s"` -> `"Attendu depuis %s"`
- `companion/test_status_pages.py` — 16 new checks across the three tasks (Frame-strip behaviour, CSS block-scoped checks, the Health nightly regression and its three sibling behaviours, the unchanged-dot-count guard); one existing check retargeted in place (`DEVICE_STATE_TEXT`'s key set). `EXPECTED_CHECK_COUNT`: 228 -> 235 (Task 1) -> 241 (Task 2) -> 246 (Task 3), each re-derived by running the harness
- `companion/test_view_pages.py` — one existing pinned French headline value retargeted (`"Attendue depuis %s"` -> `"Attendu depuis %s"`); one existing check retargeted (the C5 clock-span wrapping broke a contiguous-substring assertion — see Deviations). No `EXPECTED_CHECK_COUNT` change (no check added or removed, only value/assertion edits)

## Decisions Made

See `key-decisions` in the frontmatter above.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `frame_strip_html()`'s `next_wake_iso` parameter could not be removed without breaking two other wave-3/4 plans' owned files**
- **Found during:** Task 1
- **Issue:** The plan's own interface note reads "Change `frame_strip_html()` to take the one state result ... instead of a bare `next_wake_iso`", which read as a signature change. But `companion/pages/home_page.py` (owned by plan 22-07) and `companion/pages/config_page.py` (owned by plan 22-05) both call this function passing `next_wake_iso=...` by keyword, and this plan's own `files_owned` section forbids editing either file this wave.
- **Fix:** Kept the parameter in the signature (byte-identical call-site compatibility) but stopped using it for the state decision; the function instead calls `wake.next_wake_status()` fresh from `ctx["last_checkin_ts"]`/`ctx["device_config"]` — the SAME two facts the callers already used to compute the `next_wake_iso` value they pass in, so the two calls can never disagree. Documented at length in the function's own docstring.
- **Files modified:** `companion/layout.py`
- **Verification:** `companion/test_view_pages.py`'s pre-existing `_home_status_card_headline_next_update_or_expected_since` (which builds its own `next_wake_iso` via `wake.next_wake_at_iso()` exactly like the real callers do) passes unmodified; `companion/test_config_page.py` (221/221) and `companion/test_status_pages.py`'s new Frame-strip checks all pass against the recomputed value.
- **Committed in:** `0c2c6ae`

**2. [Rule 3 - Blocking] Deleting `QUICK_ACTION_APPLIES_SENTENCE` broke `companion/test_config_page.py` (owned by plan 22-05)**
- **Found during:** Task 1
- **Issue:** The plan's action text says to retire this constant "from this file, together with its French entry, in the same commit". `companion/test_config_page.py` (owned by plan 22-05) references `layout.QUICK_ACTION_APPLIES_SENTENCE` directly at two call sites — deleting the constant would raise `AttributeError` the moment that test file (which this plan may not edit) imports it.
- **Fix:** Kept the constant defined (documented as "no longer used by `frame_strip_html()` but not deleted, because config_page.py/test_config_page.py — owned by 22-05 — still reference it; that plan retires it in its own commit"). `_FRAME_DELAY_UNKNOWN_TEXT = QUICK_ACTION_APPLIES_SENTENCE` (an alias, not a re-typed literal) carries the retired wording forward as `frame_state.DELAY_UNKNOWN`'s own scanner-visible copy.
- **Files modified:** `companion/layout.py`
- **Verification:** `companion/test_config_page.py` — 221/221 (both `layout.QUICK_ACTION_APPLIES_SENTENCE` call sites use a fixture with no `last_checkin_ts`, which resolves to `frame_state.STATE_UNKNOWN`/`DELAY_UNKNOWN` — the SAME text as before this task, confirmed by direct inspection of both fixtures).
- **Committed in:** `0c2c6ae`

**3. [Rule 1 - Bug] `test_view_pages.py`'s "Next update ≈ 14:10" pinned assertion broke after Task 2's `.time-value` span wrapping**
- **Found during:** Task 3's full-suite verification pass (not caught immediately after Task 2 — a process gap, noted below)
- **Issue:** Task 2 wrapped the strip's clock text in `<span class="time-value time-value--primary">14:10</span>` (C5). A pre-existing pinned check in `test_view_pages.py` asserted the CONTIGUOUS substring `"Next update ≈ 14:10"`, which no longer matches once a `<span>` tag sits between "≈ " and "14:10".
- **Fix:** Retargeted the assertion to check `"Next update ≈"` and `"14:10"` as two separate substrings.
- **Files modified:** `companion/test_view_pages.py`
- **Verification:** `companion/test_view_pages.py` — 116/116, exit 0.
- **Committed in:** `19dfec1` (folded into the Task 3 commit, since it was caught during Task 3's own full-suite verification step)

**4. [Rule 1 - Bug] The nightly-regression fixture's own pipeline-run timestamp made `overall_severity()` return `"error"`, not `"ok"`**
- **Found during:** Task 3, writing the nightly-regression check
- **Issue:** The check's first draft seeded `META_LAST_PIPELINE_RUN` at the SAME 22:58 check-in timestamp used for the device's own held state — three hours stale by the 02:00 clock, which is a genuine, UNRELATED pipeline-staleness signal, not the frame-state signal under test. This made `health_severity()` return `"error"` instead of the expected `"ok"`, failing the check for a reason outside its own subject.
- **Fix:** Seeded `META_LAST_PIPELINE_RUN` at the fixture's own `now` (02:00) instead — "the pipeline just ran," isolating the check to the device/frame signal it actually tests.
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** The nightly-regression check passes; `severity == "ok"` confirmed directly.
- **Committed in:** `19dfec1`

**5. [Rule 3 - Blocking, files_modified mismatch] `companion/i18n_fr/health.py` was in the PLAN's Task 1 `<files>` list, but Task 1 needed no health.py edit; Task 3 did**
- **Found during:** Task 1 read-through
- **Issue:** Task 1's own `<files>` tag lists `companion/i18n_fr/health.py`, but Task 1's actual work (the strip's headline/delay copy) touches `companion/i18n_fr/home.py`/`display.py` territory, not health.py at all — a plan drafting mismatch, most likely a typo for `companion/i18n_fr/frame_state.py` or a task-list swap with Task 3 (which genuinely does need a new `health.py` entry, "Asleep for quiet hours").
- **Fix:** Did not touch `i18n_fr/health.py` in Task 1 (nothing there needed it); added the one genuinely new `health.py` entry in Task 3 instead, where it belongs. `companion/i18n_fr/frame_state.py`, `companion/i18n_fr/home.py` and `companion/test_view_pages.py` — none formally listed in this plan's frontmatter `files_modified` at all — were edited where the work genuinely required it (see Decisions/Deviation 3 above), since none of the three is claimed by another wave-3 plan's own `files_owned`.
- **Files modified:** none beyond what Tasks 1/3 already needed
- **Verification:** `test_i18n.py` exits 0 (22/22) after both tasks — proof the actual translation-catalogue wiring is correct regardless of which task's file list technically named which i18n file.
- **Committed in:** `0c2c6ae` (Task 1), `19dfec1` (Task 3)

---

**Total deviations:** 5 auto-fixed (2 blocking file-ownership conflicts, 1 blocking regression from this plan's own earlier task, 1 bug in this plan's own new test fixture, 1 files_modified/task-list mismatch worked around by editing the right file at the right task instead of the named-but-wrong one).
**Impact on plan:** All five were necessary for correctness or to honor this wave's file-ownership boundaries; none touched a file owned by another wave-3 plan (`config_page.py`, `screens.py`, `app.py`, `dirty-state.js`, `test_config_page.py`, `test_companion_app.py`, `test_browser_ux.py`, `i18n_fr/display.py` — all untouched) or by 22-07 (`home_page.py` — untouched). No scope creep.

## Issues Encountered

**Acceptance criteria that evaluated exactly as the plan predicted (constraint 5, run literally):**
- `grep -c "age_seconds(next_wake" companion/layout.py` -> `0`. Confirmed.
- `grep -c '@supports selector(:has(\*)) {' companion/static/style.css` -> `1`. Confirmed, unchanged by this plan.
- `grep -c "dot--" companion/static/style.css` -> `9` before and after this plan (Task 3 touches no CSS). Confirmed and pinned by a new check.
- A rendered strip contains exactly `2` occurrences of `data-quick-switch`. Confirmed.
- `companion/test_status_pages.py` reports M/M at its new pin (246) apart from the documented `anomaly_active()` FAIL, at every one of the three tasks' own intermediate pins (235, 241, 246). Confirmed at each step.
- `companion/test_i18n.py` exits 0 (22/22) — this criterion evaluated BETTER than 22-02's own executor predicted: that plan left `test_i18n.py` failing (a documented, expected D-08 Check 2 gap for three strings awaiting a real consumer). This plan IS that consumer for two of the three (`HEADLINE_HELD`, via the strip's own `_FRAME_HEADLINE_HELD_TEXT` scanner-visibility constant) plus the two collision strings (`HEADLINE_DUE`/`HEADLINE_LATE`), and Task 3 is a consumer for none of the remaining `DELAY_*` templates directly — but the scanner-visibility pattern (see `patterns` above) makes every one of the six frame_state constants this plan touches resolve as genuinely "produced" without needing the pre-existing `_FRAME_STATE_AWAITING_CONSUMERS` exception list to grow OR shrink. That exception-list frozenset itself is untouched (it belongs to plan 22-08 per 22-02-SUMMARY's own note) and its continued presence is now redundant for the strings this plan wired, not load-bearing.
- `PYTHON=.../python bash scripts/run-all-tests.sh` at plan close: exactly 3 failing harnesses (`server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py`), each confirmed by its own FAIL message to be the documented root-sandbox read-only-directory/`anomaly_active()` case, not a new regression. Coverage: 93% total (well above the 83% floor).
- `companion/test_config_page.py` — 221/221 (M/M, the `:has()` gate and dirty-bar checks untouched).
- `companion/test_contrast_check.py` — 41/41 (M/M).
- `ruff check .` — clean at every task boundary.

No acceptance criterion needed to be flagged as a bad criterion (unlike 22-02's own executor, cited as the model for that situation) — every command here returned exactly what this plan's text predicted, once the file-ownership-driven deviations above were applied.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- **French agreement — resolved, not deferred:** `companion/i18n_fr/home.py`'s `"Expected since %s"` French value is now the locked `"Attendu depuis %s"`. **Plan 22-05 does NOT need to touch this string.**
- **French agreement — genuinely still open, deferred to 22-05:** `frame_state.DELAY_UNKNOWN`'s French value still resolves through `companion/i18n_fr/display.py`'s pre-existing `"Applies the next time the frame wakes up."` -> `"S’applique la prochaine fois que le cadre se réveille."` entry (unchanged by this plan — that file is owned by plan 22-05 this wave), while 22-UI-SPEC.md's locked Copywriting Contract specifies `"S’applique au prochain réveil du cadre."` instead. This is the SAME discrepancy 22-02-SUMMARY.md originally flagged for `DELAY_UNKNOWN`; this plan resolved the `HEADLINE_LATE` half of that flag (in `home.py`, which this plan owns) but could not resolve the `DELAY_UNKNOWN` half (in `display.py`, which it does not own). **Action item for 22-05:** reconcile `i18n_fr/display.py`'s `"Applies the next time the frame wakes up."` entry to the locked French wording when that plan retires `QUICK_ACTION_APPLIES_SENTENCE`'s own remaining settings-form consumer.
- `data-quick-switch` is live on both strip switch forms, ready for plan 22-05 Task 3's own leave-guard suppression in this same wave.
- `companion/layout.py`'s `QUICK_ACTION_APPLIES_SENTENCE` constant is still defined (kept for `config_page.py`/`test_config_page.py`'s own continued reference) — plan 22-05 is the one that retires it, once its own settings-form consumer of the retired wording is gone.
- The `.time-value`/`.time-value--primary` role is defined and applied to the strip's own clock text only; plans 22-06, 22-07, 22-09 and 22-12 adopt it at their own render sites, per C5's own spec.
- No blockers for the rest of Phase 22's wave-3/4 plans.

---
*Phase: 22-companion-audit-round-4-fix-the-blocking-display-save-bar-co*
*Completed: 2026-09-12*

## Self-Check: PASSED

All modified files present on disk (`companion/layout.py`,
`companion/static/style.css`, `companion/pages/health_page.py`,
`companion/i18n_fr/health.py`, `companion/i18n_fr/home.py`,
`companion/test_status_pages.py`, `companion/test_view_pages.py`, this
SUMMARY.md); all three task commits (`0c2c6ae`, `ba0044b`, `19dfec1`)
found in `git log`.
