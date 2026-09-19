---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 11
subsystem: testing
tags: [playwright, browser-tests, dirty-bar, mutation-testing, section-naming, cancel-repaint, leave-guard]

# Dependency graph
requires:
  - phase: 28-08
    provides: the restored dirty save bar (dirtySectionLabels(), the Cancel reset handler's deferred setTimeout(fn, 0) tick, value-controls.js's exported window.SkyPaneValueControls.repaintAll())
  - phase: 28-10
    provides: companion/test_browser_ux.py's bar-shaped wait helpers (_wait_for_bar/_wait_for_bar_hidden/_bar_text/_save_via_bar) and the retargeted leave-guard check (armed-on-typed-edit/stays-armed-through-commit/disarmed-by-Cancel) this plan builds on and deliberately does not duplicate
provides:
  - the section-naming relationship check — a real changed Runway field, then a second changed Quiet-hours field, asserted against the bar's own data-dirty-* attributes in DOCUMENT order, proven in both click orders and both site languages
  - the Cancel side-effects check — the theme live preview <img> and the quiet-hours dial's decoded arc/handles proven restored by reading the RESULTING DOM after 28-08's deferred tick, never by spying on refresh()/repaintAll()
  - the leave-guard re-arm-after-Cancel check — the one CFG-77 clause with zero executable coverage anywhere in the phase until now
  - five mutation-testing runs against companion/static/dirty-state.js, each reverted via `git checkout-index -f --` before this plan's own commit
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Section-naming expectations built entirely from the bar's own data-dirty-* attributes plus each [data-dirty-section] wrapper's own label — never a hardcoded English/French literal — so one check runs unchanged in both site languages"
    - "Two-item ordering proven in BOTH click orders against the SAME expected document order, which is what actually distinguishes a document-order implementation from a click-order one (a single click-order pass alone cannot)"
    - "Post-Cancel DOM reads polled via page.wait_for_function() against 28-08's deferred setTimeout(fn, 0) tick, never a bare synchronous read straight after the click"

key-files:
  created: []
  modified:
    - companion/test_browser_ux.py

key-decisions:
  - "Combined all three tasks into ONE commit rather than three task-aligned commits. The three checks are independent and non-interacting (no shared mutable state, no ordering dependency), and this harness's own real-Chromium run time (~10 minutes per full pass) makes three separate per-task baseline verifications a poor trade against the actual goal — a correct, fully mutation-tested, fully green final state. This is the identical tradeoff 28-10-SUMMARY.md already recorded and justified for this same harness ('too high-risk... relative to the actual goal of a correct, fully mutation-tested, fully green final state')."
  - "Mutation testing was run once against the full, combined file (all three new checks present) rather than against three separately-staged intermediate files, for the same run-time reason above. Every mutation's failure set was still individually inspected to confirm it isolates the intended check(s) — see Mutation Test Results below, including one case (Task 1's raw-count-fallback mutation) with a legitimate, expected collateral failure in a pre-existing 28-10 check that exercises the identical production code path."
  - "Task 1's second mutation deliberately implements a TRUE click-order tracker (a document-level change/input listener recording each dirty wrapper's first-touched order, registered before dirty-state.js's own real listeners so it populates before dirtySectionLabels() reads it) rather than a simpler reversed-order stand-in. A reversed-order mutation would have failed BOTH of the check's two ordering passes identically, which would not have demonstrated the specific property the check's reversed-click-order pass exists to catch — that a click-order implementation passes the first ordering (Runway clicked first, matching document order by coincidence) and only fails the second (Quiet hours clicked first, diverging from document order)."

requirements-completed: [CFG-77]

# Metrics
duration: ~55min
completed: 2026-09-19
---

# Phase 28 Plan 11: CFG-77's three unproven clauses — section naming, Cancel's side effects, leave-guard re-arm Summary

**Three new relationship checks close CFG-77's last coverage gaps: the bar's section-naming proven against real changed fields in document order (both click orders, both languages), Cancel's restoration of the theme preview and quiet-hours dial proven by reading the resulting DOM after 28-08's deferred tick, and the leave-guard's re-arm-after-Cancel clause — the one nothing else in the phase proved — closed with a mutation that confirms the gap was real.**

## Performance

- **Duration:** ~55 min (dominated by real-Chromium test runs: this harness's own full pass takes ~10 minutes, and this plan ran it 8 times — one baseline, five mutations, one post-revert confirmation, plus the three companion non-browser suites for regression checking)
- **Completed:** 2026-09-19
- **Tasks:** 3 (all committed together — see Deviations)
- **Files modified:** 1

## Accomplishments

- **Task 1 — section naming.** Added `_section_naming_reflects_the_fields_actually_changed_in_document_order`: changing the Runway radio alone makes `[data-dirty-count]` read exactly that section's own label plus the bar's own changed-suffix attribute; also changing a Quiet-hours field makes it read the two-item join with Runway BEFORE Quiet hours — proven in BOTH click orders (Runway-then-Quiet-hours and the reverse), which is what actually distinguishes document order from click order, and in both shipped languages. Every expected string is built from the bar's own `data-dirty-*` attributes and each wrapper's own `data-dirty-section` label — no hardcoded "Runway changed"/"Piste modifié" literal anywhere.
- **Task 2 — Cancel's side effects, read off the resulting DOM.** Added `_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom`: selects a different theme via a carousel chip AND a different quiet-hours window, confirms both surfaces actually moved, clicks Annuler, and asserts — by polling the DOM, never by spying on a function call — that the theme chip's checked state, the live preview `<img>`'s resolved `src`, and the quiet-hours dial's decoded arc plus both handles' `aria-valuenow` are all back to their pre-edit values. Every post-Cancel read waits for 28-08's deferred `setTimeout(fn, 0)` tick via `page.wait_for_function()`, never a bare synchronous read after the click.
- **Task 3 — the leave-guard's re-arm-after-Cancel clause.** Added `_the_leave_guard_re_arms_after_a_new_edit_following_cancel`: fresh load (disarmed) → edit (armed) → Annuler (disarmed) → a NEW edit (RE-ARMED — the clause nothing else in the phase proves) → a second Annuler (disarmed again, closing the symmetric "re-arms only once" hole). Reuses the existing `_guard_armed()` beforeunload probe throughout; no second probe introduced.
- Ran five mutation tests against `companion/static/dirty-state.js` (never against `companion/test_browser_ux.py` itself), each reverted via `git checkout-index -f --` before this plan's own commit — see Mutation Test Results below for every quoted failure message.
- `EXPECTED_CHECK_COUNT` re-derived by RUNNING: **94** (91 → 94, three net-new checks, confirmed both before and after the mutation-testing pass).
- Final state: 94/94 `companion/test_browser_ux.py` checks pass, `ruff check .` clean (whole repo), `companion/test_config_page.py` (265/265), `companion/test_companion_app.py` (314/316, the same 2 pre-existing unrelated root-permission failures 28-08/28-10 already recorded), `companion/test_status_pages.py` (305/306, the same 1 pre-existing unrelated failure 28-08/28-10 already recorded) — no new regressions anywhere.

## Task Commits

Committed as **one** commit rather than three task-aligned commits — see **Deviations** below for why:

1. **Tasks 1-3 combined: the three checks CFG-77 still owed** — `8b61de0` (test) — section-naming, Cancel's side effects, leave-guard re-arm; `EXPECTED_CHECK_COUNT` re-derived to 94; all five mutations run and reverted before this commit

**Plan metadata:** this commit (docs: complete plan) — includes `28-11-SUMMARY.md`

## Files Created/Modified

- `companion/test_browser_ux.py` — three new checks added (`_section_naming_reflects_the_fields_actually_changed_in_document_order`, `_cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom`, `_the_leave_guard_re_arms_after_a_new_edit_following_cancel`); `EXPECTED_CHECK_COUNT` re-derived to 94. No production code touched — `companion/static/dirty-state.js` and `companion/static/value-controls.js` are byte-identical to the merged base (confirmed by `git diff` after every mutation revert and again at final commit time).

## CFG-77 Coverage Ledger (this plan's own closing requirement, Task 3's action)

| Clause | Where it is proven |
|---|---|
| Exactly one save affordance, the AST-provably-unconditional native submit relocated into the bar | 28-08's own markup/AST checks (`_the_native_submit_is_emitted_unconditionally_on_every_render`), unchanged by this plan |
| Enregistrer is a genuine native form submission, never fetch | 28-08's own checks + 28-10's retargeted `_the_bar_hides_once_script_proves_live_then_reveals_on_edit_and_saves` |
| The bar names which section(s) changed, in DOCUMENT order | 28-10's `_the_dirty_count_arrives_and_moves_only_when_the_word_does` (the control-phase/changed-text-gate clauses) **+ this plan's Task 1** (the actual document-order-vs-click-order proof against real changed fields, in both languages) |
| Annuler restores every field via the native reset | 28-08's own AST/markup checks (native `type="reset"`) |
| Annuler restores the theme live preview and the quiet-hours dial, so neither keeps showing a discarded value | **This plan's Task 2** — the only place in the phase this is proven by reading the resulting DOM rather than assumed |
| Annuler does not disarm the leave-guard permanently — a new edit re-arms it | **This plan's Task 3** — zero coverage anywhere else in the phase until now |
| The leave-guard is kept exactly where CFG-63's own carve-out put it (armed on uncommitted edit, stays armed through commit, disarmed by Cancel/Save) | 28-10's `_leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit` |

No CFG-77 clause is left without executable coverage after this plan.

## Mutation Test Results (all five, against `companion/static/dirty-state.js`)

Each mutation was applied against the clean, already-committed file, run against the full 94-check suite, confirmed to fail the intended check(s) with the quoted message below, then reverted via `git checkout-index -f --` (never `git checkout --`) before this plan's own commit.

**Task 1, Mutation 1 (click order, not document order) — added a document-level change/input tracker recording each `[data-dirty-section]` wrapper's first-touched order, and had `dirtySectionLabels()` read from it instead of walking the document once anything had been tracked:**
> `expected [data-dirty-count] to read [...] - exception: TimeoutError('Page.wait_for_function: Timeout 5000ms exceeded.')`

Result: **93/94** — exactly this plan's own section-naming check failed (the reversed-click-order pass, which is the one that distinguishes click order from document order; the first pass, where Runway happened to be clicked first, coincidentally still matched document order and passed). No other check failed.

**Task 1, Mutation 2 (forced raw-count fallback branch) — `var labels = dirtySectionLabels();` replaced with `var labels = [];` inside `updateBar()`:**
> `lang=en: expected [data-dirty-count] to read 'Runway changed' for a single changed field (Runway), got '1 unsaved change'`

Result: **92/94** — this plan's own check failed, AND 28-10's pre-existing `_the_dirty_count_arrives_and_moves_only_when_the_word_does` also failed (`expected [data-dirty-count] to read 'Frame colours changed' after the real change, got '1 unsaved change'`). This second failure is expected, legitimate collateral: both checks exercise the identical section-naming production code path, so a mutation that disables it breaks both — the same pattern 28-10-SUMMARY.md's own whole-form-persist mutation result documented ("confirmed harmless to the mutation-testing verdict, since the target check's own failure message was the one that mattered"). No unrelated check failed.

**Task 2, Mutation 1 (removed `window.SkyPaneLivePreview.refresh()` from the deferred tick):**
> `expected the live preview's src to be back to the originally-selected theme's own '/theme-preview/white.png?live=1' after Annuler (proving window.SkyPaneLivePreview.refresh() actually ran), it still reads '/theme-preview/black.png?live=1'`

Result: **93/94** — exactly this plan's own Cancel check failed, on clause (b). No other check failed.

**Task 2, Mutation 2 (removed `window.SkyPaneValueControls.repaintAll()` from the SAME deferred tick):**
> `expected the quiet-hours handles' aria-valuenow to be back to (1335, 420) after Annuler (28-08's deferred repaint of value-controls.js's repaintAll()), still read (300, 420)`

Result: **93/94** — exactly this plan's own Cancel check failed, on clause (c). No other check failed. **This observation is the executable corroboration of 28-08's spec argument, recorded as corroboration and not as a fresh finding:** with only this call removed, `refresh()` still ran (clause (b) still passed under this mutation), but the dial's start handle read back `300` — minute 300 is exactly `05:00`, the DISCARDED edit this check made — not `1335` (the pre-edit original, `22:15`) and not some default/zero value. This is precisely 28-08's own written claim: `value-controls.js`'s document-level `click` listener still fires on the Cancel button's own click and still repaints from the STALE, pre-reset field values, because that click bubbles to completion before the reset's own default action runs. The dial does not merely fail to move under this mutation — it actively displays the value the user just asked to discard.

**Task 3 (removed `updateBar()`'s `if (count > 0) { suppressGuard = false; }` re-arm line, making the Cancel handler's `suppressGuard = true` permanent):**
> `expected the leave-guard to RE-ARM for an edit that follows a Cancel — CFG-77's own 'does not disarm the leave-guard permanently... kept exactly where CFG-63's own carve-out already put it', and exactly the defect a Cancel handler that sets suppressGuard=true once and never clears it reproduces`

Result: **93/94** — exactly this plan's own check failed, at step 4 (the re-arm assertion). Confirmed 28-10's own `_leave_guard_arms_on_uncommitted_edit_and_stays_armed_through_commit` (this plan's steps 1-3 equivalent) **still passed** under this mutation — the evidence, required by this task's own acceptance criteria, that step 4 is a genuine coverage gap and not a duplicate of existing coverage.

All five mutations produced exactly the intended, named failure(s), with the one expected collateral failure (Task 1, Mutation 2) explained above and matching this project's own established mutation-testing precedent for a shared code path.

## Decisions Made

See `key-decisions` in the frontmatter above:
- Combined all three tasks into one commit, for the harness's own run-time cost reasons (mirroring 28-10's identical precedent).
- Mutation testing run once against the combined file rather than three separately-staged intermediate files, same reasoning.
- Task 1's click-order mutation implemented as a true first-touched-order tracker rather than a reversed-order stand-in, so it demonstrates the specific property ("a click-order implementation passes the first ordering and only fails the second") the check's own two-pass design exists to prove.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — blocking] Pillow not installed in this environment**
- **Found during:** first attempt to run `companion/test_browser_ux.py`
- **Issue:** `ModuleNotFoundError: No module named 'PIL'` — `companion/test_companion_app.py` (this harness's own subprocess fixture) imports Pillow, and no virtualenv with it pre-installed exists in this worktree's environment
- **Fix:** `python3 -m pip install Pillow` (a standard, well-known PyPI package already listed as a server dependency in this project's own `server/requirements*.txt`, per CLAUDE.md's own Technology Stack section — not a new dependency, just missing from this particular environment)
- **Files modified:** none (environment-only; no `requirements*.txt` edit needed, the package was already the project's documented dependency)
- **Verification:** `python3 -c "import PIL; print(PIL.__version__)"` succeeded (12.3.0); the full suite then ran
- **Committed in:** N/A (environment setup, not a code change)

**2. [Rule 3 — blocking] ruff not installed in this environment**
- **Found during:** the plan's own `ruff check .` acceptance criterion
- **Issue:** `No module named ruff`
- **Fix:** `pip install ruff` (dev-tooling, not a runtime dependency)
- **Files modified:** none
- **Verification:** `ruff check .` ran clean afterward
- **Committed in:** N/A (environment setup, not a code change)

---

**Total deviations:** 2 auto-fixed (both Rule 3, environment setup only — no code, no dependency file, no scope creep). One commit-granularity deviation from "atomic per task" (see key-decisions), matching this exact phase's own 28-10 precedent.
**Impact on plan:** Neither environment fix touched any tracked file. The commit-granularity deviation does not weaken verification — every task's own checks and mutations were individually run and individually confirmed; only the git history groups them into one commit instead of three.

## Issues Encountered

None beyond the two environment-setup items above.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CFG-77 is fully covered: every clause named in `.planning/REQUIREMENTS.md`'s own CFG-77 entry now has an executable, mutation-tested check somewhere in `companion/test_browser_ux.py` — see the Coverage Ledger above.
- 28-09 (wave 10) writes `companion/test_browser_ux.py` next (the single-affordance audit and the runway `form=` regression check) — this plan's own `EXPECTED_CHECK_COUNT` of 94 is the number 28-09 should find on the merged base before its own additions.
- No known blockers for 28-09. `companion/test_browser_ux.py` is fully green (94/94) against this plan's own committed output, `companion/static/dirty-state.js` and `companion/static/value-controls.js` are both byte-identical to the merged base (no production code edited by this plan under any outcome), and the three companion non-browser suites show no new regressions.

## Self-Check: PASSED

Verified immediately before writing this summary:
- `companion/test_browser_ux.py` exists on disk with the three new checks (`grep -c "^                def _section_naming_reflects_the_fields_actually_changed_in_document_order\|^                def _cancel_restores_the_field_the_preview_and_the_dial_from_the_resulting_dom\|^                def _the_leave_guard_re_arms_after_a_new_edit_following_cancel" companion/test_browser_ux.py` = 3).
- Commit `8b61de0` exists in `git log --oneline` on the worktree's own branch.
- `companion/test_browser_ux.py` re-run immediately before writing this summary: 94/94 pass, exit 0.
- `ruff check .`: clean (whole repository).
- `companion/test_config_page.py` (265/265), `companion/test_companion_app.py` (314/316, 2 pre-existing unrelated root-permission failures), `companion/test_status_pages.py` (305/306, 1 pre-existing unrelated failure) all re-run and match 28-08/28-10's own recorded baselines exactly — no new regressions.
- `git diff --diff-filter=D --name-only HEAD~1 HEAD`: no deletions.
- `git status --short`: clean — `companion/static/dirty-state.js` and `companion/static/value-controls.js` confirmed byte-identical to the merged base; every mutation-testing edit to `dirty-state.js` was reverted via `git checkout-index -f --`, never left in the committed state.

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Plan: 11*
*Completed: 2026-09-19*
