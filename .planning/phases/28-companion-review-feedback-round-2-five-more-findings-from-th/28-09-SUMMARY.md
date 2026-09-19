---
phase: 28-companion-review-feedback-round-2-five-more-findings-from-th
plan: 09
subsystem: testing
tags: [playwright, browser-tests, dirty-bar, mutation-testing, requirements-ledger, design-system]

# Dependency graph
requires:
  - phase: 28-05
    provides: the theme-carousel preview-follows-scroll checks and EXPECTED_CHECK_COUNT baseline this plan's own gate re-verifies
  - phase: 28-08
    provides: the restored dirty save bar (companion/pages/config_page.py's dirty_bar_html(), companion/static/dirty-state.js's driver) the single-affordance audit and the runway regression check both target
  - phase: 28-10
    provides: companion/test_browser_ux.py's bar-shaped wait helpers (_wait_for_bar/_wait_for_bar_hidden/_bar_text/_save_via_bar), reused by name rather than reimplemented
  - phase: 28-11
    provides: the three CFG-77 relationship checks and the EXPECTED_CHECK_COUNT=94 baseline this plan's own two additions build on
provides:
  - companion/test_browser_ux.py's single-affordance audit, resolving every submit-shaped control's own .form property in a live browser rather than counting <button occurrences or maintaining an allow-list
  - companion/test_browser_ux.py's runway form= regression check, proving the cross-tree path from a click to bar-naming to a real Enregistrer navigation to disk to a reload, closing the path CFG-74(c) named before it was superseded
  - companion/test_config_page.py's orphan-rule check for the retired .save-status region (the half of the orphan-rule clause 28-08 Task 2's own check does not cover)
  - the phase's closing gate — every EXPECTED_CHECK_COUNT re-derived by running, the sandbox baseline re-verified by name
  - the Phase 28 coverage ledger, seven new traceability-table rows (CFG-72..CFG-78), the corrected ROADMAP.md entry, and the design-system skill's restored-bar standing account
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Resolving a control's own .form.id in a live browser (never a string count of <button occurrences, never a hand-maintained allow-list) as the executable form of 'exactly one save affordance'"
    - "A phase-closing coverage ledger that names which of a superseded requirement's clauses were genuinely built (none) rather than rounding a reversal up to 'fixed' or down to 'not met'"

key-files:
  created: []
  modified:
    - companion/test_browser_ux.py
    - companion/test_config_page.py
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .claude/skills/sketch-findings-skypane/SKILL.md

key-decisions:
  - "The single-affordance audit's complement assertion (calendar/rules/notifications-test/quick-LED/quick-switch controls resolving to a non-settings-form id) is proven generically over every collected submit-shaped control the page actually renders, rather than by hand-enumerating a CSS selector per named category — this is what keeps the audit free of the hand-maintained allow-list CFG-78's own wording forbids, and it naturally covers the Poll card's 'Manual refresh' form and the calendar disconnect button too, neither of which the plan's own read_first list named"
  - "The document-to-form listener-narrowing mutation had to narrow BOTH dirty-state.js's change AND input listeners, not change alone: _click_control()'s native el.click() on a radio dispatches both events, and narrowing only 'change' left the 'input' listener (still on document) silently masking the mutation for the runway check specifically, while still breaking checks that rely on _commit_field()'s change-only dispatch. Both listeners narrowed together reproduces the B1 defect class faithfully and the runway check times out waiting for the bar exactly as expected"
  - "Airlines' own 'Enregistrer le nom' form is excluded from the single-affordance audit's complement assertion by construction, trivially — the audit only navigates to /display and /device, and Airlines lives on a different route entirely, so there is nothing for it to collect there"

requirements-completed: [CFG-77, CFG-78]

# Metrics
duration: ~65min
completed: 2026-09-19
---

# Phase 28 Plan 09: The closing plan — one affordance proven, the runway path proven, the record written Summary

**The single-affordance audit resolves every submit-shaped control's own `.form` property in a live browser and requires exactly one whose form is `settings-form`; the runway radios' cross-tree `form=` path is proven end to end from a click to bar-naming to a real Enregistrer navigation to disk to a reload; the phase's closing gate re-derives every check count by running and re-verifies the five-check sandbox baseline by name; and the Phase 28 coverage ledger records CFG-74 as superseded before implementation — never built, never ticked, never rounded up.**

## Performance

- **Duration:** ~65 min
- **Completed:** 2026-09-19
- **Tasks:** 3/3 completed
- **Files modified:** 5

## Accomplishments

- **Task 1 — the single-affordance audit and the runway regression check.** Added `_exactly_one_submit_shaped_control_resolves_to_the_settings_form()` to `companion/test_browser_ux.py`: on both `/display` and `/device`, in both site languages, it collects every `input[type="submit"]`, `button[type="submit"]` and bare `<button>` (the HTML default IS submit) via a browser-side `.form.id` resolution, requires exactly one whose form id is `config_page.SETTINGS_FORM_ID`, asserts that one carries `data-static-save-fallback` and sits inside `[data-dirty-bar]`, and names every collected control as a `tagName[type] form=id text=...` tuple in its failure message. The bar's native `type="reset"` Cancel is excluded from the collection by construction (not submit-shaped), with the reasoning recorded in the check's own comment. Also added `_the_runway_form_associated_path_reaches_the_bar_and_disk_end_to_end()`: selecting a runway radio (rendered OUTSIDE the settings form) reveals the bar naming exactly its own Runway/Piste label (built from the bar's own `data-dirty-*` attributes, never a hardcoded literal), a real Enregistrer click causes a real navigation, `tracked_runway` is read back off disk, and a reload confirms the radio reflects the saved value — both languages.
- **The orphan-rule clause's other half.** `companion/test_config_page.py` gained `_style_css_carries_no_rule_for_the_retired_save_status_region()`, asserting `style.css` (comments stripped) contains zero RULE selectors targeting `.save-status`, while the comment prose narrating its retirement survives — the half of the orphan-rule clause 28-08 Task 2's own `STATIC_SAVE_FALLBACK_ATTR` check does not cover.
- **Three mutations, all run and reverted.** (1) A second submit button added inside the settings form: the audit failed, naming it by its exact `tagName[type=submit] form='settings-form' text='MUTATION second save'` tuple, with 95/96 other checks unaffected. (2) `dirty-state.js`'s document-level `change` AND `input` delegation narrowed to the form element (reproducing the B1 defect the runway check exists to guard): the runway check failed with a timeout waiting for the bar, alongside 13 other checks whose own fields are similarly cross-tree associated — a broader blast radius than the audit's own mutation, but the intended check failed with exactly the right symptom. (3) A `.save-status { display: none; }` rule re-added to `style.css`: the orphan check failed, quoting the exact re-added rule in its failure message. All three reverted via `git checkout-index -f --`.
- **`EXPECTED_CHECK_COUNT` re-derived by RUNNING**: `test_browser_ux.py` 94 -> **96** (96/96); `test_config_page.py` 265 -> **266** (266/266).
- **Task 2 — the gate.** Every one of the seven suites run individually; every printed `N/N checks pass` line recorded. `test_companion_app.py`'s own `EXPECTED_CHECK_COUNT` (316) explicitly re-checked and confirmed NOT stale (last assignment already matched the real run). `scripts/run-all-tests.sh` (`PYTHON=.../python3`, `JOBS=4`) exit status: **1 (FAIL)**, naming three harnesses — `server/test_manual_resolutions.py`, `companion/test_companion_app.py`, `companion/test_status_pages.py` — carrying the SAME five individually-named failures 28-04 first recorded on 2026-09-15, re-verified by running today rather than carried forward: 2x WR-11 (`manual_save_failed`/`manual_delete_failed` flash keys in `test_companion_app.py`), 2x WR-11 (`add_entry()`/`delete_entry()` read-only-dir simulations in `test_manual_resolutions.py`), 1x `anomaly_active()` for a non-existent `state_dir` in `test_status_pages.py`. Unchanged in count and membership; none attributable to 28-08/28-10/28-11/this plan's Task 1. `ruff check .` clean across the whole repository.
- **Task 3 — the record.** `.planning/REQUIREMENTS.md` gained a "## Phase 28 coverage ledger" section (six `### Correction N` sub-sections: CFG-72, CFG-73, CFG-75, CFG-76, CFG-74, and the CFG-77/CFG-78 restoration across 28-08/28-10/28-11/28-09) written against the finished tree, plus seven new per-requirement traceability-table rows (CFG-72 through CFG-78), closing the gap that left the table ending at CFG-71. `.planning/ROADMAP.md`'s Phase 28 entry corrected: the Plans count (nine live plans across ten waves, 28-06/28-07 superseded before execution — eleven plan numbers issued), the plan checklist (28-10 and 28-11 added, every plan marked to what actually shipped), and the Requirements line (CFG-77/CFG-78 added, CFG-74 recorded as superseded) — both existing 2026-09-16 addenda left untouched (confirmed via `git diff`, no hunk inside either). `.claude/skills/sketch-findings-skypane/SKILL.md`'s "Settings auto-save (new, Phase 27, CFG-63/CFG-64)" paragraph kept verbatim, marked `SUPERSEDED by Phase 28 (CFG-77/CFG-78)`, and followed by the restored bar's own standing account (section-naming, the relocated AST-unconditional native submit as the bar's one Save under two rendering conditions, the inverted visibility polarity and why it keeps CFG-64's floor intact, the native `type="reset"` Cancel and why the polarity inversion requires it, the no-claim `[data-dirty-count]` seed, `DIRTY_SECTION_ATTR` regaining a reader, `.quick-toast` staying `quick-switch.js`'s alone, `hasUncommittedEdits()` surviving for `freshness.js`); the "Current as of" header and the Folded-In Work list both updated with Phase 28's own entry.

## Task Commits

Each task was committed atomically:

1. **Task 1: The single-affordance audit and the runway `form=` regression check** — `766e9ad` (test) — the audit, the runway check, the `.save-status` orphan-rule half; `EXPECTED_CHECK_COUNT` re-derived to 96/266. All three mutations run and reverted before this commit.
2. **Task 3: The record** — `b1496fd` (docs) — the Phase 28 coverage ledger, seven traceability rows, the corrected ROADMAP.md entry, the design-system skill's restored-bar account.

**Task 2 (the gate) produced no file changes** — `test_companion_app.py`'s constant was explicitly checked and found NOT stale, so no commit was needed for it; its findings are recorded in this SUMMARY and in the Phase 28 coverage ledger's own gate table.

## Files Created/Modified

- `companion/test_browser_ux.py` — the single-affordance audit and the runway `form=` regression check; `EXPECTED_CHECK_COUNT` re-derived to 96
- `companion/test_config_page.py` — the `.save-status` orphan-rule check; `EXPECTED_CHECK_COUNT` re-derived to 266
- `.planning/REQUIREMENTS.md` — the Phase 28 coverage ledger, seven new traceability rows
- `.planning/ROADMAP.md` — the Phase 28 entry's Plans count, plan checklist and Requirements line corrected
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the "Settings auto-save" paragraph superseded in writing, "Current as of" and the Folded-In Work list updated

## Decisions Made

- The single-affordance audit's complement assertion is proven generically (every collected non-settings-form control) rather than by a hand-enumerated selector per named category, which is what keeps it free of the hand-maintained allow-list CFG-78 forbids and gives it correct coverage of forms the plan's own `read_first` list did not name (the Poll card's "Manual refresh" form, the calendar disconnect button).
- The runway-check mutation required narrowing BOTH of `dirty-state.js`'s document-level listeners (`change` and `input`), not `change` alone — `_click_control()`'s native `.click()` on a radio dispatches both, and the `input` listener (left on `document`) silently masked a `change`-only mutation for this specific check. Documented in the mutation-testing findings below.
- `test_companion_app.py`'s `EXPECTED_CHECK_COUNT` was explicitly re-checked against a real run and found NOT stale (316, matching the file's own last assignment) — no edit was made, and this SUMMARY states that explicitly per the plan's own acceptance criterion, rather than silently doing nothing and leaving the reader to wonder whether it was checked.

## Deviations from Plan

### Auto-fixed Issues

None — plan executed exactly as written. The two arithmetic corrections below were caught during my own drafting of the SKILL.md Folded-In Work entry and fixed before commit, not left as errors in the shipped record.

**Impact on plan:** No deviation from the plan's own scope. No file outside the plan's declared `files_modified` list was touched.

## Mutation Test Results (all three, quoted verbatim)

**#1 (single-affordance audit) — a second `<button type="submit">MUTATION second save</button>` added inside `<form id="settings-form">`:**
> `/display lang=en: expected exactly ONE submit-shaped control whose own .form.id resolves to 'settings-form', got 2 — every collected submit-shaped control on this page: ... button[type=submit] form='settings-form' text='MUTATION second save'; ... button[type=submit] form='settings-form' text='Save settings'`

Result: 95/96 — exactly the intended check failed, naming the offending control by tuple. No collateral failures.

**#2 (runway regression check) — `dirty-state.js`'s document-level `change` AND `input` delegation narrowed to the form element (reproducing the B1 defect this path guards):**
> `lang=en: expected [data-dirty-count] to read ... — exception: TimeoutError('Page.wait_for_function: Timeout 5000ms exceeded.')`

Result: 82/96 (14 failures) — the runway check failed with exactly the expected symptom (the bar never appears), alongside 13 other checks whose own fields are similarly cross-tree `form=`-associated outside the physical `<form>` (the quiet-hours dial, the theme carousel, the whole-form-persist and rejected-value checks) — a substantially broader blast radius than a narrower single-listener mutation would have produced, since nearly all of Display's own fields reach the form only through `form=`. This is the mutation's own honest scope, not a defect in the check: the B1 defect class this path guards against would, if it recurred, break exactly this many real user interactions.

**#3 (orphan-rule check) — `.save-status { display: none; }` re-added to `style.css`:**
> `expected NO rule selector anywhere in style.css (comments stripped) to still target .save-status — its own retired region is gone outright (27-04-PLAN.md, CFG-63) and no rule should still reach for it; context: '...\n\n.save-status { display: none; }\n\n...'`

Result: 265/266 — exactly the intended check failed, quoting the re-added rule verbatim. No collateral failures.

All three mutations were applied against an already-committed, clean base file, confirmed to produce the named failure, then reverted via `git checkout-index -f --` before this plan's own commits — never `git checkout --`.

## Issues Encountered

None beyond the mutation-testing redesign noted above (narrowing both listeners rather than one).

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- CFG-77 and CFG-78 are both complete, with every clause of each requirement's own wording paired with named, mutation-tested evidence in the Phase 28 coverage ledger.
- CFG-74 is recorded as superseded before implementation, never built, and left unticked — the ledger, the ROADMAP entry and the traceability table all agree on this, and none claims a Safari defect was found or fixed.
- Phase 28 is closed: nine live plans (28-01 through 28-05, 28-08, 28-10, 28-11, 28-09) executed across ten waves; 28-06/28-07 superseded before execution.
- This is the phase's last plan. No blockers for any future phase.

## Known Stubs

None.

## Threat Flags

None — this plan adds no new network surface, auth path, file-access pattern or schema change. The one trust boundary in this plan's own threat model (browser to `POST /settings` via the runway radio's cross-tree `form=` association) is unchanged in shape, only newly proven.

## Self-Check: PASSED

Verified immediately before writing this summary:
- `companion/test_browser_ux.py` and `companion/test_config_page.py` both exist on disk with the described checks; both files re-run immediately before writing: `test_browser_ux.py` 96/96 pass (exit 0), `test_config_page.py` 266/266 pass (exit 0).
- Both commit hashes (`766e9ad`, `b1496fd`) exist in `git log --oneline` on the worktree's own branch.
- `ruff check .`: clean (whole repository).
- `grep -cE '^\| CFG-7[2-8] \|' .planning/REQUIREMENTS.md` = 7.
- `grep -q '28-10-PLAN.md' .planning/ROADMAP.md` and `grep -q '28-11-PLAN.md' .planning/ROADMAP.md` both true.
- `grep -q 'SUPERSEDED by Phase 28' .claude/skills/sketch-findings-skypane/SKILL.md` and `grep -q 'countDifferences' .claude/skills/sketch-findings-skypane/SKILL.md` both true.
- `grep -c '^- \[x\] \*\*CFG-74\*\*' .planning/REQUIREMENTS.md` = 0 — CFG-74 remains unticked.
- `git diff` over `.planning/ROADMAP.md` shows only the intended hunk (the Requirements line, the Plans count/intro sentence, and the plan checklist); both 2026-09-16 addenda are untouched.
- `git status --short`: clean — `companion/pages/config_page.py` and `companion/static/dirty-state.js` confirmed byte-identical to the merged base; every mutation-testing edit to them was reverted via `git checkout-index -f --`, never left in the committed state.

---
*Phase: 28-companion-review-feedback-round-2-five-more-findings-from-th*
*Plan: 09*
*Completed: 2026-09-19*
