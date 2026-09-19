---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 10
subsystem: testing
tags: [playwright, browser-tests, dirty-bar, mutation-testing, css]

# Dependency graph
requires:
  - phase: 28-05
    provides: the theme-carousel preview-follows-scroll checks this file's own suite already carried
  - phase: 28-08
    provides: the restored dirty save bar (companion/pages/config_page.py's dirty_bar_html(), companion/static/dirty-state.js's driver, style.css's .dirty-bar rules) that every one of this plan's seventeen owners now targets
provides:
  - companion/test_browser_ux.py's bar-shaped wait helpers (_wait_for_bar/_wait_for_bar_hidden/_bar_text/_save_via_bar), replacing the retired auto-save helpers outright
  - all seventeen owners test_browser_ux.py's own suite had reaching through the retired [data-save-status] region/auto-save helpers, retargeted onto the restored bar (nine mechanical, seven rewritten, one removed)
  - a mutation-tested, seven-check audit table proving none of the seven rewrites silently weakened its own contract
  - a real, measured, mutation-testing-discovered fix to style.css's phone-width dirty-bar clearance (the existing figure only ever covered the bar's empty, pre-edit height)
affects: [28-09, 28-11]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Bar-shaped Playwright wait helpers (_wait_for_bar/_wait_for_bar_hidden) replacing status-region text polling, matching the bar's own real hidden-attribute toggle rather than a guessed word"
    - "getBoundingClientRect()-based geometric overlap assertions, scrolled to the true document bottom before measuring — a fixed-position element's clearance cannot be proven from an unscrolled viewport"
    - "Rotation-based (never a hardcoded constant) mutation values for save-persistence checks that share one long-lived harness across the whole suite run, avoiding a false-negative convergence risk"

key-files:
  created: []
  modified:
    - companion/test_browser_ux.py
    - companion/static/style.css

key-decisions:
  - "Two checks outside this plan's own seventeen-owner list, left broken by 28-08's own merge (that plan's own SUMMARY items #5/#8), were fixed here as a direct, unavoidable consequence of the same restoration — both broke on a selector/timing assumption the relocated, now-animated bar invalidates, and 28-11/28-09 do not name them either"
  - "The phase (c) design for the retargeted [data-dirty-count] check ('re-select the SAME value') is empirically impossible to use as the plan's own mutation-test literally describes: MEASURED live (a standalone Playwright probe), clicking an ALREADY-CHECKED radio fires click but never change — so it can never reach updateBar()/setCountText() regardless of the gate under test. Redesigned phase (c) to change to a SECOND, different theme inside the identical data-dirty-section wrapper — a real change that resolves to the textually IDENTICAL label — which does reach the gate and is what the mutation test now confirms"
  - "style.css's phone-width dirty-bar clearance constant (88px, tuned against the bar's EMPTY count span) was widened to 176px (224px total) after this plan's own new overlap check — scrolled to the real document bottom, which 28-08's manual verification was not — found a genuine, reproducible overlap: the bar wraps to two rows once real section-naming text doesn't fit beside Enregistrer, reaching 134px for a realistic three-section worst case. Outside this plan's own files_owned but fixed as a Rule 1 direct consequence, since it is squarely the subject the new check proves"

requirements-completed: [CFG-77, CFG-78]

# Metrics
duration: resumed execution (two prior attempts were killed before any commit; this session completed the plan from a partially-applied, uncommitted Task 1 diff)
completed: 2026-09-19
---

# Phase 28 Plan 10: Retarget test_browser_ux.py onto the restored save bar Summary

**All seventeen test_browser_ux.py owners that reached through the retired auto-save helpers/status region now target the restored dirty bar — nine mechanical swaps, seven hand-rewritten and mutation-tested contracts, one named removal — plus a real, measured clearance bug the new geometry check found and fixed in style.css.**

## Performance

- **Duration:** resumed execution — a prior executor was interrupted mid-Task-1 by an API rate limit before any commit; a second resume attempt also failed before committing; this session verified the salvaged Task 1 diff, completed Tasks 2-3, mutation-tested all seven rewrites, found and fixed two additional pre-existing breakages plus one real CSS bug, and committed
- **Completed:** 2026-09-19
- **Tasks:** 3 (Task 1: helpers/nine mechanical/one removal; Task 2: four inverted-contract rewrites; Task 3: three native-path retargets) — committed as 2 commits (see below; exact per-task commit boundaries were not preserved from the resumed, heavily-interleaved debugging session — see Deviations)
- **Files modified:** 2

## Accomplishments

- Replaced `_SAVE_STATUS_SEL`/`_save_status_text()`/`_wait_for_save_status()`/`_wait_for_saved()`/`_wait_for_saving()` with `_wait_for_bar()`/`_wait_for_bar_hidden()`/`_bar_text()`/`_save_via_bar()` — every new helper waits on real DOM state (`page.wait_for_function`) or a real navigation, never a sleep
- Retargeted the nine genuine mechanical owners (display/device reveal-and-persist, the quiet-hours/wake-interval drag-and-key checks and their `_set_window()`/`_set_interval()` helpers, the arrivals/calendar and theme-carousel keyboard checks) onto the bar with every non-wait assertion byte-identical, correcting two restore-step bugs found during verification (see Deviations)
- Removed `_a_double_fire_of_change_before_the_first_save_resolves_coalesces_to_one_follow_up` and its own `_hold_posts()` helper outright — its subject (fetch coalescing during an in-flight request) ceased to exist with the auto-save model rather than being dropped for convenience
- Rewrote, by hand, the four checks whose contract the restoration inverts or deletes: the leave-guard now asserts it **stays armed** through a commit (inverting the retired auto-save disarm-on-commit contract) and gains the equivalent-or-stronger "bar already visible/naming the section" clause in place of the deleted silent-region clause; the retired status-region sequence check retargets onto `[data-dirty-count]` with a `MutationObserver`, keeping the "already-checked radio announces nothing" idea and adding a genuinely gate-exercising repeat-change phase; the settle check drops the retired CFG-63 "no save button visible" clause and proves the bar's own field/bar-hidden/disk three-way agreement, with disk asserted UNCHANGED while the bar is visible; the fallback-visibility check's polarity fully inverts (bar visible by default, hides once script proves live, reveals on edit, persists via a real navigation)
- Rewrote, by hand, the three checks whose subject moved to a different surface: the whole-form-POST check now diffs the FULL on-disk config before/after a single-field save (stronger than the retired fetch-body capture); the rejected-value check moves from the retired toast onto the native D-07 inline-error path, with an explicit negative that no `.quick-toast` appears on the settings form's own path; the tab-bar/sidebar overlap check moves from proving the retired region was never fixed onto proving the now-genuinely-fixed bar never intersects the tab bar, the sidebar column, or the page's own last in-flow element — scrolled to the true document bottom, at both breakpoints, in both languages
- Mutation-tested all seven rewrites against `dirty-state.js`/`app.py`/`style.css`, every mutation reverted via `git checkout-index -f --`; every failure message quoted verbatim below
- Found and fixed a real, previously-undocumented clearance bug in `style.css`: the phone-width dirty-bar clearance was measured against the bar's EMPTY, server-rendered state, not the populated state a real edit produces, which wraps to two rows and reaches up to 134px tall — 28-08's own clearance figure (88px additive) left a genuine ~34px overlap with the page's real content, only visible once scrolled to the true document bottom under scripts-enabled conditions this plan's new check specifically exercises
- `EXPECTED_CHECK_COUNT` re-derived by RUNNING: **91** (92 → 91, the one removal; the nine mechanical swaps and seven rewrites are each net zero)
- Final state: 91/91 `companion/test_browser_ux.py` checks pass, `ruff check .` clean, `companion/test_config_page.py` (265/265), `companion/test_companion_app.py` (314/316, the same 2 pre-existing unrelated root-permission failures 28-08 already recorded), `companion/test_status_pages.py` (305/306, the same 1 pre-existing unrelated failure 28-08 already recorded)

## Task Commits

Committed as two commits rather than three — see **Deviations** for why the per-task boundary was not preserved:

1. **Tasks 1-3 combined: retarget all seventeen owners onto the restored bar** — `a979724` (feat) — helpers, nine mechanical swaps, one removal, four inverted-contract rewrites, three native-path retargets, `EXPECTED_CHECK_COUNT` re-derived to 91
2. **The style.css clearance fix** — `a9abdd9` (fix) — the phone-width dirty-bar clearance widened from 88px to 176px additive, a Rule 1 deviation found by Task 3's own new overlap check

**Plan metadata:** this commit (docs: complete plan) — includes `28-10-SUMMARY.md`

## Files Created/Modified

- `companion/test_browser_ux.py` — all seventeen owners retargeted; bar-shaped wait helpers; `EXPECTED_CHECK_COUNT` re-derived to 91
- `companion/static/style.css` — the phone-width `.has-tab-bar .page-content:has(.dirty-bar)` clearance rule's additive constant widened from 88px to 176px, with the measured evidence recorded in the rule's own comment

## The Seventeen-Owner Audit Table

Per check → classification → what it proved before → what it proves now → equivalent-or-stronger.

| # | Check (current name) | Class | Before → After | Equiv-or-stronger |
|---|---|---|---|---|
| 1 | `_display_reveal_and_persist_across_all_field_kinds` | mechanical | `_wait_for_saved()` → `_wait_for_bar()`+`_save_via_bar()`; non-wait assertions unchanged | Yes — identical |
| 2 | `_device_reveal_and_persist_stays_in_step_with_display` | mechanical | same swap | Yes — identical |
| 3 | `_set_window()` (helper) | mechanical | same swap + an idempotency guard (skip if disk already matches, since the bar never reveals for a no-op) | Yes — identical, the guard is a correctness fix the bar model requires |
| 4 | `_dragging_and_keying_a_handle_reach_disk` | mechanical | same swap | Yes — identical |
| 5 | `_the_dial_handle_stays_on_its_ring_for_the_whole_of_a_held_press` | mechanical | doc-comment only (uses `_set_window()`, no direct helper call) | Yes — unaffected |
| 6 | `_set_interval()` (helper) | mechanical | same swap + idempotency guard | Yes — identical |
| 7 | `_dragging_and_keying_the_range_reach_disk` | mechanical | same swap | Yes — identical |
| 8 | `_arrivals_and_calendar_keep_the_focused_chip_in_view_when_keyed` | mechanical | same swap, PLUS a restore-step bug fixed: the original salvaged diff called `_wait_for_bar()`+`_save_via_bar()` unconditionally on restore, but clicking back to the field's own ORIGINAL value returns `countDifferences()` to 0 (the bar correctly hides, nothing to save) — mutation-testing/live debugging found this timed out; fixed to assert disk was never touched instead | Yes — the fix makes the assertion honest about what the bar model actually does (disk never moves without a real Save) |
| 9 | `_keying_the_strip_selects_scrolls_into_view_and_moves_the_preview` | mechanical | same restore-step bug and fix as #8 | Yes — same reasoning |
| 10 | `_a_double_fire_of_change_before_the_first_save_resolves_coalesces_to_one_follow_up` + `_hold_posts()` | **removed** | proved fetch-coalescing during an in-flight request | N/A — subject (an in-flight fetch to coalesce against) ceased to exist; the bar issues no request until Enregistrer is clicked, once, whenever the user likes |
| 11 | `_leave_guard_arms_on_uncommitted_edit_and_disarms_on_change` → `_leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit` | **rewritten** | guard disarms the instant change commits; save-status region stays silent before commit | guard **stays armed** through a commit (the restored, inverted semantics); the bar is already visible and already naming the section for a merely-typed edit (no silent phase at all) | Yes — strictly stronger (asserts the correct, inverted contract; the no-silent-phase clause is new and stronger than "stays silent") |
| 12 | `_the_status_region_arrives_and_moves_only_when_the_word_does` → `_the_dirty_count_arrives_and_moves_only_when_the_word_does` | **rewritten** | `[saving, saved]` text sequence via MutationObserver on the retired region | `[data-dirty-count]`: already-checked radio writes nothing; a real change writes the section name exactly once; a SECOND different value resolving to the IDENTICAL label writes nothing further (setCountText()'s own gate) | Yes — the retired sequence no longer exists to prove; the surviving control-phase idea is kept, and a genuinely new repeat-label phase is added |
| 13 | `_the_save_settles_the_field_the_region_and_disk_agree` → `_the_bar_settles_the_field_disk_agree_and_the_bar_hides` | **rewritten** | asserted the retired CFG-63 "no save button ever visible" contract verbatim | field/bar/disk three-way agreement after a real navigation; disk explicitly asserted UNCHANGED while the bar is visible and unsaved | Yes — the retired clause is gone (correctly, since this phase reverses it); the disk-untouched-while-unsaved clause is new and stronger |
| 14 | `_fallback_save_hides_immediately_once_script_runs` → `_the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves` | **rewritten** | fallback button hidden always, before and after an edit | bar visible by default (no-JS floor), hides once script proves live, reveals on edit, persists via a real navigation | Yes — the INVERSE polarity, correctly asserted; same overall strength (three checkpoints then vs. three now) |
| 15 | `_auto_save_posts_the_whole_form_never_only_the_touched_field` → `_the_bars_save_persists_every_field_never_only_the_touched_one` | **rewritten** | intercepted the fetch body, asserted every field present | reads the FULL on-disk config before/after, asserts exactly one key differs | Yes — strictly stronger: a server that posts the whole form correctly but WRITES only the touched key still passes the retired check and fails this one (mutation-proven) |
| 16 | `_a_rejected_value_claims_nothing_the_toast_fires_and_disk_is_untouched` → `_a_rejected_value_claims_nothing_the_field_echoes_it_and_disk_is_untouched` | **rewritten** | asserted a `.quick-toast` fires with the generic copy | asserts the field's own inline error (`aria-describedby`-linked), the user's rejected input echoed back, disk unchanged, AND an explicit negative that NO `.quick-toast` appears on this path | Yes — the two surviving clauses ("claims nothing", "disk untouched") kept at full strength; toast clause replaced with the actual current failure surface, plus a new negative preventing the two mechanisms from re-merging |
| 17 | `_save_status_region_never_overlaps_the_tab_bar_at_390x844` → `_the_dirty_bar_never_overlaps_the_tab_bar_sidebar_or_the_pages_last_element` | **rewritten** | proved the retired region was NEVER `position: fixed` | proves the now-genuinely-fixed bar never intersects the tab bar (<960px) or the sidebar column (>=960px), and never covers the page's own last in-flow element (scrolled to the true document bottom) — both breakpoints, both languages | Yes — the retired contract is inverted correctly (the bar IS fixed now, by design); widened from one breakpoint/relationship to two breakpoints, two relationships, two languages, and this widening is what surfaced the real style.css bug fixed in this plan |

No "no" verdicts — every rewrite is equivalent-or-stronger than what it replaced.

## Mutation Test Results (all seven rewrites)

Each mutation was applied against a clean, already-committed app file, run against the full suite, confirmed to fail ONLY the intended check (or, for the shared bar-hidden-at-init mutation, exactly the two checks that share that code path) with the quoted message below, then reverted via `git checkout-index -f --` (never `git checkout --`).

**#11 (leave-guard) — mutated `dirty-state.js`'s `change` listener to unconditionally disarm the guard (restoring the retired auto-save contract):**
> `expected the leave-guard to STAY ARMED the instant change commits the edit — a committed change is unsaved until Enregistrer, not the retired auto-save contract where a commit disarmed the guard because it was already persisted`

**#12 (dirty-count arrives) — mutated `dirty-state.js`'s `setCountText()` to remove its changed-text gate:**
> `changing to a DIFFERENT theme inside the same section wrote a new mutation to [data-dirty-count]: ['Frame colours changed'] became ['Frame colours changed', 'Frame colours changed'] — the two renders are textually IDENTICAL, so a write here is setCountText()'s own changed-text gate failing to suppress a no-op text assignment`

**#13 (bar settles) & #14 (bar hides/reveals) — mutated `dirty-state.js`'s init to remove `bar.hidden = true` (shared root cause, both checks fail from the one mutation):**
> `#14: expected the bar to be HIDDEN immediately once script runs on a fresh load — dirty-state.js's own bar.hidden = true at init, the no-JS-floor polarity this check exists to pin down`
> `#13: expected the bar to be hidden before any edit`

**#15 (whole-form persist) — mutated `config_page.py`'s `save_device_config()` call to force `theme` to a value rotated off whatever is currently on disk (a deterministic clobber that can never coincidentally match, unlike a hardcoded constant, across a harness many earlier checks already saved through):**
> `lang=en: saving ONE field (tracked_runway) changed ['theme', 'tracked_runway'] on disk — a save that clobbers an untouched field is CFG-36's own hazard; before={'theme': 'green', ...}; after={'theme': 'green_light', ...}`

**#16 (rejected value) — mutated `app.py`'s `_handle_settings_post()` to redirect with `FLASH_KEY_SAVED` instead of rendering the inline-error page when `errors` is non-empty:**
> `expected 'input[name="wake_interval_s"]''s own aria-describedby to name its error anchor (wake-interval-s-error), got 'wake-interval-caption'`

**#17 (overlap) — mutated `style.css` to remove the (now-fixed, 176px-additive) phone-width clearance rule outright:**
> `390x844/en: the bar must not cover the page's own last in-flow element; bar {'top': 650, 'bottom': 772, 'left': 16, 'right': 374} vs last element {'top': 92.625, 'bottom': 684.40625, 'left': 24, 'right': 366}`

All seven mutations produced exactly the intended, named failure and no unintended collateral failures (the whole-form-persist mutation is deliberately global — it clobbers `theme` on EVERY save for the rest of the run — so it also broke several unrelated theme-dependent checks downstream in the same run; this is expected and was confirmed harmless to the mutation-testing verdict, since the target check's own failure message was the one that mattered).

## Decisions Made

- **The phase (c) redesign for check #12** (see key-decisions in frontmatter) — the plan's own literal text ("re-select the SAME value") cannot reach `setCountText()`'s own gate at all: a standalone Playwright probe confirmed clicking an already-checked native radio fires `click` but never `change`. Redesigned to change to a SECOND, different value that resolves to the textually identical label, which does exercise the gate and is what the mutation test above confirms.
- **The `style.css` clearance fix** (see key-decisions) is a Rule 1 deviation outside this plan's own declared `files_owned`, applied because it is squarely the subject the new overlap check (#17) exists to prove, and the plan's own acceptance criteria for that check require it to be mutation-proven against a REAL clearance rule — leaving a genuinely-undersized rule in place would make the check either fail permanently or pass by accident depending on scroll state.
- **Two checks outside the seventeen-owner list were also fixed** (see below, Deviations) rather than left broken, since `companion/test_browser_ux.py exits 0` is this plan's own stated acceptance criterion for all three tasks, and both breakages are direct, foreseeable, unavoidable consequences of the SAME restoration this plan retargets everything else onto.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 — direct, unavoidable consequence] `_the_no_js_floor_holds_for_both_settings_pages` (22-10-PLAN.md Task 3), outside this plan's own seventeen-owner list, broken by 28-08's own merge**
- **Found during:** final full-suite verification pass
- **Issue:** used `page.click('#settings-form button[type="submit"]')` — the settings form's own submit button is now relocated OUTSIDE `#settings-form`, cross-submitting via its own `form=` attribute from inside `.dirty-bar`; the descendant selector no longer resolves to it. Also hit the bar's own unconditional entrance `animation: skypane-bar-arrive`, which fires on first paint regardless of scripts being blocked (CSS animations are independent of JS), causing an "element not stable" click failure
- **Fix:** retargeted the selector to `[data-static-save-fallback]`; added a `page.wait_for_timeout(600)` (well past `var(--motion-fast)`'s 180ms) before the coordinate click
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** included in the 91/91 final run
- **Committed in:** `a979724`

**2. [Rule 1 — direct, unavoidable consequence] `_display_still_saves_with_scripts_blocked_at_360px` (23-06-PLAN.md Task 3), outside this plan's own seventeen-owner list, broken by 28-08's own merge**
- **Found during:** final full-suite verification pass
- **Issue:** `ElementHandle.click()` on the relocated `[data-static-save-fallback]` button failed with "element is not stable" — the same unconditional entrance animation as deviation #1
- **Fix:** added the same `page.wait_for_timeout(600)` before the click
- **Files modified:** `companion/test_browser_ux.py`
- **Verification:** included in the 91/91 final run
- **Committed in:** `a979724`

**3. [Rule 1 — direct, unavoidable consequence, found via this plan's own new check] `style.css`'s phone-width dirty-bar clearance undersized for real content**
- **Found during:** Task 3, mutation-testing check #17 (the overlap check)
- **Issue:** the existing clearance figure (88px additive) was measured against the bar's EMPTY, server-rendered count span — not the populated, scripts-enabled state a real edit produces. At <960px the bar wraps (`flex-wrap: wrap`) once section-naming text plus Enregistrer no longer fit one row, reaching 122px for one changed section and 134px for three (the realistic worst case on the Display scope), well past the ~70-88px baseline. A real, reproducible ~34px overlap with the page's own last content resulted, only visible once scrolled to the true document bottom
- **Fix:** widened the additive constant from 88px to 176px (224px total with `--space-2xl`), covering the measured worst case (134px bar + 56px tab bar + two 16px cushions = 222px) with an 8px-grid rounding margin
- **Files modified:** `companion/static/style.css`
- **Verification:** the overlap check passes cleanly against the fix, and still correctly fails when the fix is mutated away (both confirmed by live runs)
- **Committed in:** `a9abdd9`

---

**Total deviations:** 3 auto-fixed (all Rule 1 — direct, unavoidable, foreseeable consequences of this plan's own restoration work, or found by this plan's own new checks)
**Impact on plan:** All three were necessary for the plan's own "exits 0" acceptance criterion. Two touch a check outside this plan's own declared seventeen-owner list (matching 28-08's own precedent of fixing direct-consequence breakage outside its declared scope); one touches a file outside this plan's own declared `files_owned` (`companion/static/style.css`) but is squarely the subject the new overlap check proves, mutation-tested, and committed separately from the test-retargeting work for a clean audit trail. No scope creep beyond what "exits 0" and "mutation-proven" require.

## Issues Encountered

- **Resume context:** this plan had two prior execution attempts killed by an API rate limit before either committed. The second resume left an uncommitted diff in `companion/test_browser_ux.py` (149 insertions/165 deletions) that, on inspection, was genuine, correct, well-reasoned progress on Task 1's helper block and three of the nine mechanical swaps plus the one removal — verified against the current merged state of `dirty-state.js`/`config_page.py` and committed as the base for this session's own completion of the remaining fourteen owners.
- **Environment note (not a plan defect):** the very first full-suite run in this session was accidentally executed against `/home/user/skypane`'s main-repo checkout rather than this worktree (a `cd /home/user/skypane && ...` copied verbatim from the plan's own generic `<verify>` block, which does not account for worktree isolation) — its results were therefore stale and discarded once noticed; every subsequent run in this SUMMARY was executed from the worktree path directly.
- **Commit granularity:** see Deviations/key-decisions — the seven rewrites and the debugging fixes to the nine mechanical owners were developed together, interleaved, while diagnosing and fixing genuine live-behaviour bugs (the restore-step timeout in checks #8/#9, the phase-(c) redesign in check #12, the clearance bug in check #17). Splitting the resulting ~1600-line, 86-hunk diff into exactly three task-aligned commits after the fact was judged too high-risk (a mis-split hunk boundary could produce an intermediate commit that does not even parse) relative to the actual goal of a correct, fully mutation-tested, fully green final state. Committed as two commits instead (the full test-retargeting work; the separate, file-scoped CSS fix), both fully described above and independently verifiable via the mutation-testing evidence and the audit table rather than via commit-history isolation.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CFG-77/CFG-78's browser-level coverage for the restored bar is complete: all seventeen `test_browser_ux.py` owners this plan named are retargeted, mutation-tested, and green.
- 28-11 (wave 9) owns the section-naming check, the Cancel-side-effects check, and the leave-guard re-arm-after-Cancel check — none duplicated here (the leave-guard rewrite in this plan explicitly names 28-11's own re-arm check in its comment, for the two to be findable from each other).
- 28-09 (wave 10) owns the single-affordance audit and the runway `form=` regression check — not touched here.
- No known blockers for 28-09 or 28-11. `companion/test_browser_ux.py` is fully green (91/91) against the current merged base; both later plans run against this plan's own committed output per the phase's own `<files_owned>` sequencing.

## Self-Check: PASSED

Verified immediately before writing this summary:
- `companion/test_browser_ux.py`, `companion/static/style.css` both exist on disk with the described changes (`git diff a20c946 HEAD -- companion/test_browser_ux.py companion/static/style.css` shows only these two files touched across both commits).
- Both commit hashes (`a979724`, `a9abdd9`) exist in `git log --oneline` on the worktree's own branch.
- `companion/test_browser_ux.py` re-run immediately before writing: 91/91 pass, exit 0.
- `ruff check companion/test_browser_ux.py companion/app.py companion/pages/config_page.py`: clean.
- `companion/test_config_page.py` (265/265), `companion/test_companion_app.py` (314/316, 2 pre-existing unrelated root-permission failures), `companion/test_status_pages.py` (305/306, 1 pre-existing unrelated failure) all re-run and match 28-08's own recorded baselines exactly — no new regressions.
- `git diff --diff-filter=D --name-only 2c4b3e3 HEAD`: no deletions.
- `companion/app.py` and `companion/pages/config_page.py` confirmed clean (`git status --short`) — every mutation-testing edit to them was reverted via `git checkout-index -f --`, never left in the committed state.

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Plan: 10*
*Completed: 2026-09-19*
