---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 04
subsystem: ui
tags: [auto-save, fetch, playwright, i18n, css, dirty-state, quick-switch-model]

requires:
  - phase: 27-03
    provides: "the no-JS save floor made structural (native submit emitted unconditionally on every render), and the fallback-hide rule simplified to the plain .js gate"
provides:
  - "auto-save on the settings form: change (not input) commits a field, a fetch posts the whole form, only an exact 204 confirms"
  - "the dirty save bar retired outright — no button, no Cancel, no per-field count/section copy"
  - "one small save-status region (role=status, empty at rest) as the sole scripted save affordance, driven by the same optimistic-apply/POST/204-confirms model quick-switch.js already shipped"
  - "the beforeunload leave-guard kept alive and re-armed correctly on a reverted save"
  - "window.SkyPaneDirtyState.hasUncommittedEdits(), a new small cross-script query freshness.js's own stand-down gate now reads instead of the retired bar's liveness marker"
affects: ["27-09 (the closing plan, which ticks CFG-63/CFG-71)"]

tech-stack:
  added: []
  patterns:
    - "auto-save: optimistic snapshot advance -> fetch POST (X-Requested-With: quick-switch, redirect: manual) -> exact 204 confirms, anything else reverts the snapshot and raises the shared toast"
    - "cross-script query via a small exposed namespace object (window.SkyPaneDirtyState), matching window.SkyPaneLivePreview's own precedent, for a script that needs to ask another script a question with no shared module to import"

key-files:
  created: []
  modified:
    - companion/app.py
    - companion/static/dirty-state.js
    - companion/static/freshness.js
    - companion/pages/config_page.py
    - companion/static/style.css
    - companion/i18n_fr/display.py
    - companion/test_browser_ux.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_status_pages.py

key-decisions:
  - "change, not input, drives the save (D-04, PROVISIONAL) — a keystroke is not a decision; the leave-guard is what protects an edit that never fires change"
  - "a rejected value is NOT reverted in the field — it keeps the user's own text, matching wake_interval_group()'s existing D-07 echo-back design, extended to the auto-save path"
  - "the leave-guard stays alive (developer's own binding decision, 2026-09-15), re-armed by reverting the optimistic snapshot advance on any non-204"
  - "freshness.js's own stand-down gate is retargeted onto a new cross-script query (window.SkyPaneDirtyState.hasUncommittedEdits()) rather than a liveness-marker class, since the bar it used to read is gone (Rule 2 deviation, not requested by the plan text but required for correctness)"
  - "Playwright's own .fill() dispatches input only, never change — measured, not assumed — so every .fill()-based test helper needed an explicit change dispatch (_commit_field()) to commit under the new model"

patterns-established:
  - "_commit_field(page, selector) — companion/test_browser_ux.py's own helper for firing the real change event .fill() does not"
  - "_wait_for_saved()/_wait_for_saving() — read the status region's own data-save-status-{saving,saved} attributes rather than a hardcoded English word"

requirements-completed: []

duration: ~3h
completed: 2026-09-15
---

# Phase 27 Plan 04: Auto-save replaces the dirty save bar Summary

**The settings form now saves itself on `change` via the exact optimistic-apply/fetch/204-confirms model the three `role="switch"` controls already shipped — no Save button, no Cancel, one small status region that says "Saving…" then "Saved" — while the beforeunload leave-guard, freshness.js's own refresh-stand-down, and 27-03's no-JS floor all survive unchanged or are retargeted onto the new mechanism.**

## Performance

- **Tasks:** 4 (POST /settings negotiation, dirty-state.js rewrite, server markup + stylesheet, THE two checks) plus one post-hoc fix from mutation testing
- **Files modified:** 10

## Accomplishments

- `POST /settings`'s success branch now answers 204 to a fetch (the same `_wants_no_content()` predicate `/quick/*` already uses) and the byte-identical 303 to a browser form post; the validation-failure branch is untouched, so a rejection can never read as 204.
- `dirty-state.js` is rewritten from the dirty bar's own driver into the settings form's auto-save driver: `change` commits, an optimistic snapshot advance disarms the leave-guard and fires the fetch, serialisation always posts the *whole* form (CFG-36's own hazard, proven end to end on the wire), saves are serialised with exactly one coalesced follow-up on a double-fire, and only an exact `204` confirms.
- The dirty bar, its Save/Cancel buttons, its six connector words and its per-field count are all deleted. `config_page.py` renders one `role="status"` region beside the page's own heading instead — empty at rest, carrying its two translated words as `data-save-status-{saving,saved}` attributes.
- `style.css` loses every `.dirty-bar` rule (base, both breakpoints, the `[hidden]` override, the entrance) and both `.dirty-ready`-scoped content clearances; every comment elsewhere in the file that named the bar as a specificity/z-index/collision precedent now names a surviving rule instead. `grep -c 'dirty-bar' companion/static/style.css` is 0.
- Two new checks in `test_browser_ux.py` prove the whole model end to end: a scripted save settling with the status region's text sequence, the field's DOM value and the value on disk as one agreement subject (27-01's own helper); and a genuine server-side rejection raising the existing toast while the region never claims saved and disk is untouched.
- ~20 pre-existing checks across `test_browser_ux.py`/`test_config_page.py`/`test_companion_app.py`/`test_status_pages.py` that referenced the retired bar, its markup, or assumptions the new model breaks (Playwright's `.fill()` firing `change`; a radio commit staying "unsaved" until a manual Save click) are retargeted in place — see "Deviations" for the two that needed real debugging, not just renaming.

## Task Commits

1. **Task 1: POST /settings answers 204 to a fetch** - `8e9b7d5` (feat)
2. **Task 2: dirty-state.js becomes the auto-save driver** - `5c5d4c9` (feat, includes the freshness.js/test_status_pages.py/test_companion_app.py deviation)
3. **Task 3: the server emits the status region and stops emitting the bar** - `a642944` (feat)
4. **Task 4: THE checks — auto-save proven on disk, its failure proven honest** - `ac5e6a0` (test)
5. **Post-mutation-testing fix: catch a transient false-saved claim** - `da34328` (fix, found by M-B, see below)

**Plan metadata:** this SUMMARY's own commit (docs), staged separately per the plan's own instruction to leave STATE.md/ROADMAP.md/REQUIREMENTS.md untouched.

## The decision that mattered most

**Keeping the leave-guard's snapshot semantics identical in shape to the old bar's, but changing *when* the snapshot advances.** The old dirty bar advanced its snapshot only on a real form submit (a navigation). The new driver advances it the instant `change` fires and `beginSave()` runs — synchronously, before the fetch even resolves — which is simultaneously (a) the "optimistic apply" half of the save model and (b) what makes the leave-guard disarm the moment a save begins rather than waiting on the network. On failure, the snapshot is reverted to what it was before that save attempt, which re-arms the guard for exactly the value that did not land. This one mechanism (advance-then-revert) is what makes the leave-guard, the save-status region, and disk agree with each other in every case tested, including the failure path — there was no second flag or second predicate to keep in sync.

## Rollback proof and leave-guard proof

**Leave-guard proof** (`_leave_guard_arms_on_uncommitted_edit_and_disarms_on_change`, `companion/test_browser_ux.py`): typed `1800` into `wake_interval_s` via real keyboard events (never blurred) — measured `window.SkyPaneDirtyState.hasUncommittedEdits()` true and a dispatched `beforeunload` event's `defaultPrevented` true; the status region stayed silent (no save attempted). Pressed Tab (a real blur, firing `change`) — measured the guard disarm *before* the fetch settles, then measured `_wait_for_saved()` land and the value on disk. Both directions pass.

**Rollback proof** (`_a_rejected_value_claims_nothing_the_toast_fires_and_disk_is_untouched`, same file): typed `30` into `wake_interval_s` (below `WAKE_INTERVAL_MIN_S=60`, a genuine server-side rejection, exercising the 200-is-not-204 branch Task 1 deliberately left in place) and committed it. Measured: the toast becomes visible carrying the *existing* `data-quick-failed-text` copy (not a new string); the status region's own `data-save-status-saved` word never appears anywhere in its recorded text sequence (a `MutationObserver` armed before the edit — see the vacuity finding below for why this had to be a sequence, not a final-state read); and the value on disk stays at what it was before, never the rejected `30`. The field itself keeps the user's typed `30` on screen — per Task 1/2's own explicit instruction, a rejected value is never reverted, matching `wake_interval_group()`'s existing D-07 echo-back design.

## A check that failed the vacuity question

**M-B** (mutation-test: make the status region show the saved word unconditionally the instant a save starts) was predicted by the plan to fail both Check 1 (ordering) and Check 2 (region clause). Running it: Check 1 failed exactly as predicted (`expected the region's own text sequence to be ['Saving…', 'Saved'], got ['Saved']`). **Check 2 passed — a real vacuity gap.** The failure-path code still correctly clears the region to `""` on a non-204, so by the time Check 2 sampled the *settled* text, the transient false "Saved" had already been overwritten and was invisible to a final-state-only read. Fixed by adding the identical `MutationObserver` technique Check 1 already used to Check 2, asserting the saved word never appears in the region's recorded sequence *at any point* during a failed save, not only in its settled state. Re-ran M-B: both checks now fail as the plan predicted (`da34328`).

## Mutation results, quoted verbatim

- **M-A** (treat any 2xx as success instead of exactly 204): Check 2 failed — `TimeoutError('Page.wait_for_function: Timeout 5000ms exceeded.')` waiting for the toast, because the rejection was read as a save and no toast ever fired. Exactly one check failed.
- **M-B** (status region shows saved unconditionally on save-start): see above — Check 1 failed with `expected the region's own text sequence to be ['Saving…', 'Saved'], got ['Saved']`; after the fix, Check 2 failed with `the status region held the saved word 'Saved' at some point during a save that FAILED (full sequence: ['Saved', ''])`.
- **M-C** (post only the changed field instead of the whole form): exactly one check failed — `_auto_save_posts_the_whole_form_never_only_the_touched_field` — `the posted body omits 'tracked_runway=' — a save that posts only the touched field silently resolves every other field to whatever the server's own absent-field semantics decide, the exact CFG-36 hazard, got 'theme=white'`. Named the exact hazard the plan warned this mutation would expose.

All three mutations applied with `sed` on the committed tree, run, and reverted with `git checkout-index -f --` (never `git checkout --`), with `__pycache__` cleared between rounds, per the plan's own standing constraint.

## Criteria that did not evaluate as predicted

- **A large fraction of the "retarget in place" checks that referenced `.fill()` did not just need renaming — they needed a real fix.** Playwright's `locator.fill()` dispatches `input` only (its documented contract), never `change`, which the OLD dirty-state.js also listened for (`input`), so the old bar updated correctly on a bare `.fill()`. The new driver deliberately listens for `change` only (D-04). Discovered by debugging a `TimeoutError` on `_wait_for_saved()` against `/device`'s wake-interval field with a standalone repro script — `.fill()` set the value and left `window.SkyPaneDirtyState.hasUncommittedEdits()` true forever, with no save ever starting. Fixed by adding `_commit_field(page, selector)` (dispatches a real `change` event, the same shape `value-controls.js`'s own `notify()` already uses) after every `.fill()` call feeding auto-save: `_set_window()`, `_set_interval()`, and both reveal-and-persist checks.
- **Two checks assumed a radio click or keyboard-driven radiogroup selection stays "unsaved" until a manual Save click** (`_the_arc_the_handles_and_the_caption_agree_after_an_interaction`'s per-theme baseline reset, and `_keying_the_strip_selects_scrolls_into_view_and_moves_the_preview`'s "must not change the stored theme" assertion). Under auto-save, a radio commit *is* a save — that is the correct, intended behaviour, not a defect. Fixed by resetting the quiet-hours baseline once per loop iteration (rather than once before the loop) and by adding an explicit restore-as-the-last-act step to the carousel check, matching the restore discipline every other check in the file already uses.
- **`_auto_save_posts_the_whole_form_never_only_the_touched_field`'s own first draft asserted `wake_interval_s=` in a *Display*-scope POST body.** `wake_interval_s` is a Device-scope-only field — measured directly against a real captured body (`scope=display&return_to=%2Fdisplay&theme=white&theme_arriving=&calendar_theme_id=&tracked_runway=06-24&quiet_hours_start=15%3A33&quiet_hours_end=07%3A00`), which does not and should not carry it. Corrected the field list to three fields that genuinely are part of Display's scope.
- **The same check's route interception originally faked every POST with `route.fulfill(status=204, ...)`.** That answers the fetch but never lets the request reach the real server, so the disk-persistence assertion at the end always failed against an unwritten value. Fixed to `route.continue_()` after capturing the body, letting the real write happen.

## 27-03's floor check — confirmed passing UNCHANGED

`_the_floor_saves_to_disk_with_scripts_blocked_after_the_gate_simplifies` (companion/test_browser_ux.py) — not edited by this plan at all (verified: it uses only `_persist_without_js()`, `_no_js_page()` and `STATIC_SAVE_FALLBACK_ATTR`, none of which this plan's changes touch) — passes, by name, in the final full run.

## Re-derived counts (by RUNNING)

- `companion/test_browser_ux.py`: **85/85** (was 83; net +2 — the two new checks; every retarget is 1:1)
- `companion/test_config_page.py`: **259/259** (was 261; net -2 — see EXPECTED_CHECK_COUNT's own history comment for the full +3/-5 breakdown)
- `companion/test_companion_app.py`: **312/314** (unchanged; 2 known baseline WR-11 failures)
- `companion/test_status_pages.py`: **304/305** (unchanged; 1 known baseline `anomaly_active()` failure)
- `companion/test_i18n.py`: **24/24**
- `ruff check .`: clean
- `ls companion/static/*.js | wc -l`: **17** (unchanged — no .js file added or removed)
- Deferred `<script src=` count on the authenticated shell: **15** (unchanged — `layout.py`'s total `<script src=` count is 16, of which 1 is the login page's own single script, unrelated to the authenticated-shell block)
- `style.css` `@keyframes` (anchored, `^@keyframes\b`): **4** (unchanged; a bare substring grep overcounts to 7 by matching comment mentions — this is the exact overcounting the plan's own standing constraint warned about)
- `style.css` `@supports selector(:has(*))` blocks (anchored): **1** (unchanged; a bare substring grep overcounts to 6 by matching comment mentions)
- `style.css` `interpolate-size`/`calc-size(`: **2** occurrences, both in comments describing the ban, unchanged from baseline (371ceeb)
- `grep -c 'dirty-bar' companion/static/style.css`: **0**
- `git diff --stat` (371ceeb..HEAD): names neither `submit-guard.js` nor `confirm-submit.js`

## `./scripts/run-all-tests.sh` — final run

Exactly the 5 baseline failures, verified **by name**:
- `server/test_manual_resolutions.py`: 2× WR-11 (`add_entry()`/`delete_entry()` read-only-state-dir cases)
- `companion/test_companion_app.py`: 2× WR-11 (the same two cases exercised end to end over HTTP)
- `companion/test_status_pages.py`: 1× `anomaly_active()` (non-existent state_dir path)

## Files Created/Modified

- `companion/app.py` - `_settings_saved_redirect()` negotiates 204-vs-303 for every success-branch return site in `_handle_settings_post()`; the validation-failure branch is untouched
- `companion/static/dirty-state.js` - rewritten from the dirty bar's driver into the auto-save driver (see Accomplishments)
- `companion/static/freshness.js` - deviation: `unsavedEdits()` reads `window.SkyPaneDirtyState.hasUncommittedEdits()` instead of the retired bar's own liveness marker + visibility
- `companion/pages/config_page.py` - `dirty_bar_html()` and its seven words deleted; `_save_status_region_html()` + `SAVE_STATUS_*` constants added
- `companion/static/style.css` - every `.dirty-bar` rule deleted; `.save-status` added; every stray comment reference to the retired bar repointed at a surviving rule
- `companion/i18n_fr/display.py` - six retired dirty-bar catalogue entries deleted (would have failed the dead-translation check otherwise); `"Saved"` added, matching the existing `"Saved — %s"` entry's translation
- `companion/test_browser_ux.py` - THE two new checks, plus ~20 retargeted checks and two new test helpers (`_commit_field`, `_wait_for_save_status`/`_wait_for_saved`/`_wait_for_saving`)
- `companion/test_config_page.py` - dirty-bar-specific checks deleted/retargeted; DIRTY_SECTION_ATTR checks untouched
- `companion/test_companion_app.py` - ES5-safety and count-animation checks retargeted onto the status region
- `companion/test_status_pages.py` - the freshness-loop stand-down check retargeted onto `window.SkyPaneDirtyState`

## Decisions Made

See `key-decisions` in the frontmatter above; the fullest write-up is "The decision that mattered most" and the PROVISIONAL notes recorded in `dirty-state.js`'s own header comment (the `change`-not-`input` trigger, and the no-per-field-error-delivery choice from Task 1).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] `freshness.js`'s refresh-stand-down gate retargeted onto a new cross-script query**
- **Found during:** Task 2 (dirty-state.js rewrite)
- **Issue:** `freshness.js`'s own `tick()` used to stand its whole refresh cycle down while the retired bar reported unsaved edits, gated on the bar's own liveness-marker class and visibility (`22-01/B1`'s own lesson: presence is not proof of life). Both the marker and the element it read are deleted by this plan. Left as-is, `unsavedEdits()` would silently and permanently return `false`, meaning a periodic swap could land on an uncommitted field mid-edit — the same data-loss class this whole phase exists to close, in a different mechanism.
- **Fix:** Exposed `window.SkyPaneDirtyState = { hasUncommittedEdits: function () { return countDifferences() > 0; } }` from `dirty-state.js` — the same small-namespace-object idiom `window.SkyPaneLivePreview` already established for exactly this kind of cross-script query with no shared module to import. `freshness.js`'s `unsavedEdits()` now calls it.
- **Files modified:** `companion/static/dirty-state.js`, `companion/static/freshness.js`, `companion/test_status_pages.py` (the loop's own check retargeted), `companion/test_companion_app.py` (unaffected — no change needed there for this specific deviation)
- **Verification:** `_a_dirty_settings_form_stands_the_whole_cycle_down` (test_browser_ux.py, retargeted onto a typed-but-uncommitted field since a radio commit no longer stays "dirty") passes; `test_status_pages.py`'s retargeted freshness-loop check passes
- **Committed in:** `5c5d4c9` (Task 2 commit)

**2. [Rule 1 - Bug] `_a_rejected_value_claims_nothing_the_toast_fires_and_disk_is_untouched` strengthened after M-B exposed a vacuity gap**
- **Found during:** mutation-testing M-B, after Task 4
- **Issue:** the check only asserted the status region's *settled* text, which could not distinguish "never claimed saved" from "briefly claimed saved, then quietly corrected itself" — see "A check that failed the vacuity question" above
- **Fix:** added a `MutationObserver` recording the region's full text sequence, asserting the saved word never appears in it at any point during a failed save
- **Files modified:** `companion/test_browser_ux.py`
- **Committed in:** `da34328`

---

**Total deviations:** 2 (1 missing-critical fix, 1 bug fix found by the plan's own mandated mutation testing)
**Impact on plan:** Both necessary for correctness. The freshness.js deviation closes a real data-loss-class gap this plan's own architecture change opened; the Check 2 strengthening is exactly what the plan's mutation-testing requirement exists to catch, and it did.

## Issues Encountered

- **Playwright's `.fill()` does not fire `change`.** Documented above under "Criteria that did not evaluate as predicted" — cost real debugging time (a standalone repro script against a live harness instance) before the root cause was clear. Every `.fill()`-based auto-save test helper now explicitly commits.
- **Two checks' own premises (radio stays unsaved until Save; drag/preset never reach disk) were quietly falsified by the architecture change itself**, not by a bug in the implementation — auto-save committing on every real interaction is the correct, intended behaviour. Both fixed by adding restore-as-last-act steps rather than by weakening the assertions.
- **~85KB, 4-minute Playwright suite** made iterative debugging expensive; used a small standalone repro script (outside the harness) to isolate the `.fill()`/`change` root cause before touching the real test file, and ran the suite fully rather than partially between each round of `test_browser_ux.py` edits, since there is no per-check filter in this harness.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The auto-save model is fully shipped and proven end to end, including its failure path and its interaction with the pre-existing leave-guard and the three `role="switch"` controls.
- **Human verification still needed** (this plan's own `<human-check>`, not executable by this agent): on a real phone at 360px and on desktop, in both themes and both languages — change a setting and confirm the status reads "Sauvegarde…" then "Sauvegardé" (or their French/English catalogue equivalents) and nothing else appears; confirm no save button is present anywhere; confirm a rejected value raises the familiar toast and does not claim saved; confirm the calendar URL saving on blur rather than on keystroke is acceptable to the developer.
- Requirements CFG-63/CFG-71 are deliberately left unticked — per the plan's own instruction, 27-09 (the closing plan) owns marking them, and STATE.md/ROADMAP.md/REQUIREMENTS.md are untouched by this plan.
- 27-05 or whichever plan is next should be aware: `DIRTY_SECTION_ATTR` (`data-dirty-section`) is now unread by any script (its former reader, `dirtySectionLabels()`, was deleted with the bar) but is left standing in `config_page.py`'s markup — it still marks the same visual grouping a sighted reader already sees, and retiring its seven emission sites was explicitly out of this plan's scope.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*
