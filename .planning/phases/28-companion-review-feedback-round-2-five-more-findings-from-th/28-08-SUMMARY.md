---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 08
subsystem: ui
tags: [settings-form, native-post, javascript, css, dirty-state, save-bar]

# Dependency graph
requires:
  - phase: 28-05
    provides: window.SkyPaneLivePreview.refresh() (theme-preview.js), unchanged in shape, confirmed on the merged base
provides:
  - The pre-Phase-27 dirty save bar, restored — real Enregistrer/Annuler buttons over a native form POST, one save affordance (the AST-provably-unconditional native submit, relocated into the bar), section-naming copy, a leave-guard, and a working no-JS floor with the visibility polarity inverted
  - style.css's .dirty-bar rules (fixed at both breakpoints) and a :has(.dirty-bar)-based content-clearance mechanism that works with scripts blocked
  - dirty-state.js rewritten as the bar's driver, network-free again, with exactly one permitted timer (a reset-event side-effect flush)
  - value-controls.js's window.SkyPaneValueControls.repaintAll export
affects: [28-10, 28-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Native form POST over fetch for the settings form — the whole point of this reversal"
    - "CSS :has(.dirty-bar) content-clearance instead of a JS-written marker class, so the clearance works with scripts blocked"
    - "One named, explicitly-scoped setTimeout(fn, 0) exception to a file's own 'no timer' standing constraint, pinned structurally (inside one named event handler's own function body) rather than by count alone"

key-files:
  created: []
  modified:
    - companion/pages/config_page.py
    - companion/i18n_fr/display.py
    - companion/static/style.css
    - companion/static/dirty-state.js
    - companion/static/value-controls.js
    - companion/app.py
    - companion/test_config_page.py
    - companion/test_companion_app.py
    - companion/test_status_pages.py

key-decisions:
  - "DIRTY_BAR_INITIAL_TEXT is read by dirty-state.js for parity with the other six connector words, but no updateBar() branch currently spends it — documented explicitly in both files rather than silently dropping the read the plan's interfaces section requires"
  - "The Cancel button's quiet-wash CSS override is restored even though it is no longer load-bearing (no button[type=\"reset\"] rule competes with the base button rule any more) — kept for the same explicit-is-better-than-implicit precedent .logout-form button/.frame-strip__cell button already establish"
  - "Reused the skypane-bar-arrive @keyframes block 27-04 deliberately kept orphaned rather than reinventing one — the file's pinned @keyframes count stays at 4"
  - "Two test files outside this plan's own declared files_modified list (test_status_pages.py, and a fourth check inside test_config_page.py beyond the plan's named three) were retargeted as direct, unavoidable, foreseeable consequences of the restoration (Rule 1) — documented below"

requirements-completed: [CFG-77, CFG-78]

# Metrics
duration: ~1h40m
completed: 2026-09-16
---

# Phase 28 Plan 08: Restore the pre-Phase-27 settings save bar Summary

**Real Enregistrer/Annuler buttons over a native form POST replace Phase 27's silent auto-save — one save affordance (the same AST-provably-unconditional native submit, relocated), a bar that names which section(s) changed, a Cancel that natively resets with a deferred repaint for the theme preview and quiet-hours dial, and a CSS clearance mechanism that finally works with scripts blocked.**

## Performance

- **Duration:** ~1h 40min
- **Completed:** 2026-09-16
- **Tasks:** 3 (plus one small deviation commit)
- **Files modified:** 9

## Accomplishments

- Restored `.dirty-bar`'s markup, its six translated connector words plus a seventh (role-changed) initial-text word, and relocated the AST-provably-unconditional native submit (`STATIC_SAVE_FALLBACK_ATTR`) into the bar as its own visible Save — one save affordance, the same element, never a second button
- Inverted the no-JS-floor polarity: the bar renders visible by default now (no second fallback button exists any more), and `dirty-state.js` hides it at init once script has proven itself live
- Cancel is a native `<button type="reset" form="settings-form">`, genuinely functional with scripts blocked; `dirty-state.js` layers an enhancement on top via the form's own `reset` event — never calling `form.reset()` itself — that hides the bar, suppresses the leave-guard, and (in one deferred zero-delay tick, because the `reset` event fires *before* the browser restores the fields) repaints the theme live preview and the quiet-hours dial
- Restored `style.css`'s `.dirty-bar` rules, fixed at both breakpoints, and replaced the old `.dirty-ready`-marker-class clearance scoping with `:has(.dirty-bar)` — the one mechanism that actually works for a scripts-blocked visitor, since no script ever runs to write a marker for them
- Rewrote `dirty-state.js` as the bar's driver: section naming, the leave-guard (armed on edit, disarmed on Cancel/submit, **re-armed on the next edit** — T1's own historical fix), and every fetch-era artifact (the save call, the status region, the toast duplicate) deleted outright
- Removed `companion/app.py`'s dead 204 response-shape branch on `/settings` (nothing fetches it any more); `_wants_no_content()` itself survives, unchanged, for `/quick/*`
- Verified live, in a real Chromium tab, both with scripts enabled and scripts blocked: fresh load → no bar; edit → bar appears naming the section; Cancel → every field, the theme preview, and the quiet-hours dial all revert to their pre-edit state; Save → real navigation, value on disk

## Task Commits

Each task was committed atomically:

1. **Task 1: The bar's markup and its words** — `f067d0b` (feat) — the dirty bar's markup, its constants, the relocated native submit, the native `type="reset"` Cancel, and four retargeted/added `test_config_page.py` checks
2. **Task 2: The bar's CSS** — `15d2792` (feat) — `.dirty-bar` fixed at both breakpoints, `:has()`-based clearance, five superseded style.css comment blocks, one carried-in CFG-72 correction, three retargeted CSS checks
   - **Deviation fix** — `155e9ab` (fix) — `test_status_pages.py`'s own dirty-bar-retired check, broken by Task 2's CSS restoration, retargeted (see Deviations below)
3. **Task 3: The driver** — `b2083f8` (feat) — `dirty-state.js` rewritten, `value-controls.js`'s one-hunk export, `app.py`'s dead-branch removal, five retargeted JS-contract checks (three named by the plan, two more as direct consequences — see Deviations)

**Plan metadata:** this commit (docs: complete plan) — includes `28-08-SUMMARY.md` and `.planning/REQUIREMENTS.md` (CFG-77/CFG-78 marked complete)

## Files Created/Modified

- `companion/pages/config_page.py` — the bar's markup, its six-plus-one translated words, the relocated Save, the native `type="reset"` Cancel; the auto-save status region deleted
- `companion/i18n_fr/display.py` — the six restored French connector-word entries; `"Saved"` removed, `"Saving…"` kept (producer changed back to `DIRTY_SAVING_TEXT`)
- `companion/static/style.css` — `.dirty-bar` restored (base rule + both breakpoints' `position: fixed`), `.dirty-bar[hidden]`, `.dirty-bar__cancel`; `:has(.dirty-bar)` content-clearance (joins the file's one `@supports selector(:has(*))` block); five superseded comment blocks; one carried-in CFG-72 correction
- `companion/static/dirty-state.js` — rewritten as the bar's driver (`updateBar()`, `dirtySectionLabels()`, `setCountText()`, the leave-guard, the Cancel enhancement); every fetch-era artifact deleted
- `companion/static/value-controls.js` — one new hunk: `window.SkyPaneValueControls = { repaintAll: repaintAll }`
- `companion/app.py` — `_settings_saved_redirect()`'s dead 204 branch removed; docstring superseded in writing, not deleted
- `companion/test_config_page.py` — four checks retargeted/added for Task 1, three for Task 2, two for Task 3 (see below); `EXPECTED_CHECK_COUNT` re-derived by running at each step (final: 265)
- `companion/test_companion_app.py` — two JS-contract checks retargeted for Task 3; `EXPECTED_CHECK_COUNT` re-derived by running (final: 316)
- `companion/test_status_pages.py` — one check retargeted (deviation, see below)

## Decisions Made

- **DIRTY_BAR_INITIAL_TEXT has no active call site.** The plan's own interfaces section requires `dirty-state.js` to read all seven `data-dirty-*` attributes (the six connector words plus this one), but none of `updateBar()`'s four copy branches ever say the plain initial-state sentence. Read anyway, for parity with the other six and to satisfy the retargeted ES5-safety check's fallback-literal requirement — documented explicitly, in both `config_page.py` and `dirty-state.js`, so a future reader does not go looking for a dead branch that was silently trimmed.
- **The Cancel button's CSS quiet-wash override is not load-bearing any more, but is restored anyway.** Checked live: this file declares no `button[type="reset"]` rule and no other type-qualified rule that reaches the Cancel button now that it is `type="reset"` instead of `6dea46a`'s `type="button"` — the base `button` rule alone already gives it the correct quiet wash. Ported the override anyway, matching `.logout-form button`/`.frame-strip__cell button`'s own "explicit is better than implicit" precedent, and said so in the rule's own comment.
- **Reused `skypane-bar-arrive` rather than reinventing an entrance animation.** Live investigation found the `@keyframes` block still present in `style.css` — 27-04 had deliberately kept it orphaned (unreferenced), with its own test (`_skypane_bar_arrive_keyframes_survive_unreferenced`) enforcing that no rule referenced it "without a plan saying so." This plan is that plan: the restored `.dirty-bar` base rule's own `animation:` declaration references it again, and the retargeted test now enforces the opposite (referenced, exactly once). The file's pinned `@keyframes` count stays at 4.
- **No backticks, anywhere, in `dirty-state.js`.** This file's own ES5-safety check bans the literal backtick character with a raw, comment-inclusive `grep`-style scan (unlike `style.css`'s more permissive convention, which explicitly tolerates historical prose mentions of retired literals). Every code-quoting backtick in my own prose comments had to be removed — a real, working discovery made mid-task, not assumed in advance.
- **Several literal substrings (`fetch(`, `setTimeout`, `form.reset()`, `announceFailure`, `serializeForm`, `beginSave`, the marker-class names, and the constants' own English fallback text) are similarly banned file-wide, including in comments** — several retargeted checks assert a raw, unconditional zero-count or exactly-one-count across the whole file. Every historical/explanatory mention of these had to be reworded to avoid the literal token while keeping the narrative legible (e.g. "the form's own native reset() method" instead of "form.reset()").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — direct, unavoidable consequence] `test_status_pages.py`'s own dirty-bar-retired check broken by Task 2's CSS restoration**
- **Found during:** Task 2, immediately after committing the CSS restoration
- **Issue:** `_save_bar_geometry_is_retired_and_the_tab_bar_stacking_survives()` — a file entirely outside this plan's declared `files_modified` list — asserted "zero occurrences of `.dirty-bar` anywhere in `style.css`," a 27-04-era assertion that cannot survive a plan whose whole point is putting `.dirty-bar` back
- **Fix:** Renamed and retargeted in place (no `EXPECTED_CHECK_COUNT` change) to assert the restored `.dirty-bar` rule exists, with its own `z-index: 30` and `position: fixed` at both breakpoints, while confirming `.dirty-ready` still does not survive (this restoration's own clearance mechanism needs no marker class)
- **Files modified:** `companion/test_status_pages.py`
- **Verification:** 305/306 checks pass (the one remaining failure, `anomaly_active()`/non-existent state_dir, is pre-existing and entirely unrelated — `health_page.py` is untouched by this plan)
- **Committed in:** `155e9ab`

**2. [Rule 1 — direct, unavoidable consequence] A fourth `test_config_page.py` check, outside the plan's own named three, broken by restoring `dirtySectionLabels()` and the dual change/input delegation**
- **Found during:** Task 3, after retargeting the three JS-contract checks the plan explicitly names
- **Issue:** `_dirty_state_js_delegates_change_only_at_document_level_and_has_no_forbidden_syntax()` asserted `dirty-state.js` references NEITHER `DIRTY_SECTION_ATTR` NOR the retired marker classes, and that only `change` (never `input`) drives the bar — both premises contradicted by Task 3's own restoration (which correctly brings `dirtySectionLabels()`'s attribute read back, and correctly restores the pre-27-04 dual `change`+`input` delegation)
- **Fix:** Renamed and retargeted in place (no count change) to assert the restored behaviour: `DIRTY_SECTION_ATTR` present again, neither marker class present, both `change` and `input` delegated at the document level
- **Files modified:** `companion/test_config_page.py`
- **Verification:** 265/265 checks pass
- **Committed in:** `b2083f8`

**3. [Rule 1 — two orphaned checks whose entire subject was deleted] Two `test_config_page.py` checks testing the now-deleted auto-save status region**
- **Found during:** Task 1, first test run after the constants/markup rewrite
- **Issue:** `_the_save_status_region_carries_both_translated_words_and_no_script_holds_client_state` and `_save_status_region_sits_beside_the_heading_empty_and_announcing` both tested a region this plan deletes outright — unlike the fourth-check case above, there was no "restored" state to retarget onto, since the region simply no longer exists
- **Fix:** Deleted outright (net −2 to `EXPECTED_CHECK_COUNT`), offset by two new checks Task 1's own action requires (net 0 overall for Task 1); their load-bearing properties (translated-word/fallback byte-identity, no-client-storage) are recovered by Task 3's own retargeted ES5-safety check
- **Files modified:** `companion/test_config_page.py`
- **Verification:** 265/265 checks pass
- **Committed in:** `f067d0b`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — direct, unavoidable, foreseeable consequences of implementing this plan's own explicit requirements)
**Impact on plan:** All three were necessary for correctness — none is scope creep. Two touch files outside this plan's own declared `files_modified` list (`test_status_pages.py`, and one extra check in `test_config_page.py` beyond the plan's named three), but each breakage is a direct, mechanical consequence of restoring the bar and was fixed narrowly, in place, with no count drift beyond what the fix itself required.

## Issues Encountered

**`test_browser_ux.py` now fails 20 of its 92 checks — expected, out of scope for this plan, and explicitly named for 28-10/28-11.** This file is deliberately unedited here (the plan's own `<files_owned>` section: "This plan is deliberately ABSENT from `files_modified`. It belongs to 28-10 (wave 8) and 28-11 (wave 9)"). Every one of the 20 failures tests either the fetch-based auto-save mechanism this plan removes, the `[data-save-status]` region this plan deletes, or an "auto-saves with no click anywhere" assumption this plan's own reversal invalidates by design — the developer explicitly asked for a bar that requires a click again. Full run: 72/92 pass. The 20 failing checks, by their own self-descriptive text (all of which already name `27-04-PLAN.md Task 4, CFG-63` as the plan that retargeted them onto auto-save in the first place — this restoration is the mirror-image retarget):

1. Display: theme chip/runway card/quiet-hours field auto-save with no click (timeout)
2. Device: wake-interval field auto-save with no click (timeout)
3. Fallback Save button hides immediately once script runs and stays hidden through an edit (assertion failure — the button is the bar's own visible Save now, it does not stay hidden)
4. Leave-guard disarms the instant change commits and auto-save begins (element `[data-save-status]` not found)
5. Scripts-blocked "Send a test" button + Display save round-trip (timeout waiting for `#settings-form button[type="submit"]` — the submit moved into the bar)
6. Auto-save status region sits in normal document flow, never fixed/sticky (timeout)
7. Double-fire-before-resolve coalesces to one follow-up request (0 requests reached the wire — there is no fetch any more)
8. Scripts-blocked Display save via fallback Save + freshness line (element not stable — likely a locator needing to target the bar's new position)
9. Auto-save status region ARRIVES with [saving, saved] text sequence (element `[data-save-status]` not found)
10. A single field's commit auto-saves by posting the whole form (timeout — no fetch)
11. Dragging a quiet-hours handle auto-saves with no click (timeout)
12. Arc/handles/caption agreement after drag+preset, read fresh under auto-save (timeout)
13. Dial caption keeps its form after drag/keyboard/typed/preset (timeout)
14. Quiet dial 360px floors (timeout — chained to the auto-save-dependent setup above)
15. Handle-stays-on-its-ring press test (timeout — same chain)
16. Dragging the wake-interval range auto-saves with no click (timeout)
17. Arrivals'/calendar's carousels keep keyboard selection auto-saved (timeout)
18. Scripted save settles [saving, saved] via MutationObserver (MutationObserver constructor error — target element gone)
19. Server-rejected value raises the generic toast, status region never holds "saved" (same MutationObserver error)
20. Keyboard-only carousel driving with auto-saved theme restore (timeout)

None of these represent a regression this plan introduced beyond the deliberate, developer-requested reversal itself — they are 27-04's own retargets of `test_browser_ux.py`, now needing the mirror-image retarget 28-10/28-11 exist to perform.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- 28-10 and 28-11 (waves 8/9) have a complete, itemized list of the 20 `test_browser_ux.py` checks needing retargeting, plus the exact exception each currently raises — a substantial head start on their own scope.
- CFG-77 and CFG-78 are both fully implemented, live-verified (browser, both scripts-enabled and scripts-blocked, both breakpoints, both languages where applicable), and marked complete in `.planning/REQUIREMENTS.md`.
- No blockers for 28-09, 28-10, or 28-11.

## Self-Check: PASSED

All nine modified files exist on disk; all four commits (`f067d0b`, `15d2792`, `155e9ab`, `b2083f8`) exist in the worktree's own git history. `companion/test_config_page.py` (265/265), `companion/test_companion_app.py` (314/316, 2 pre-existing unrelated root-permission failures), `companion/test_i18n.py` (24/24), and `companion/test_status_pages.py` (305/306, 1 pre-existing unrelated failure) all verified passing by direct re-run immediately before writing this summary. `ruff check .` clean. `companion/static/quick-switch.js`, `companion/static/freshness.js`, `companion/static/theme-preview.js`, and `companion/test_browser_ux.py` all confirmed byte-for-byte untouched via `git diff --stat` against the plan's own base commit. `companion/static/value-controls.js`'s diff confirmed scoped to exactly one hunk (the new export).

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Plan: 08*
*Completed: 2026-09-16*
