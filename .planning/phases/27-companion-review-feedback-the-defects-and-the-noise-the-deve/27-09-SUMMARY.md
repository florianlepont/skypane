---
phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve
plan: 09
subsystem: companion-review-feedback-gate
tags: [coverage-ledger, requirements, design-system, phase-gate, verification]

# Dependency graph
requires:
  - phase: 27-01
    provides: "the agreement helper and its executable pattern, generalised here into the review-feedback discipline contract"
  - phase: 27-02
    provides: "the dial defect closed (CFG-62), re-verified byte-identical against the phase base commit at this close"
  - phase: 27-03
    provides: "the no-JS floor made structural (CFG-64), re-verified byte-identical since its own creation commit"
  - phase: 27-04
    provides: "auto-save (CFG-63), the leave-guard's own re-scope recorded per the developer's binding decision"
  - phase: 27-05
    provides: "the runway map removed (CFG-66), CFG-47's retirement re-verified intact"
  - phase: 27-06
    provides: "the title-form investigation (CFG-65, left unticked) and the text cuts (CFG-67), honesty contract re-verified"
  - phase: 27-07
    provides: "the carousel extension (CFG-68) and its stated height prediction, measured against here"
  - phase: 27-08
    provides: "the Frame strip link (CFG-69) and the two carried-in hit-target findings (CFG-70)"
provides:
  - "the Phase 27 coverage ledger in .planning/REQUIREMENTS.md, walking CFG-62..71 clause by clause against the code"
  - "nine of ten requirements ticked with per-clause evidence; CFG-65 deliberately left unticked (investigated, no defect found)"
  - "Display's height measured at 390px (3524px, scripted) and reported against 27-07's own stated prediction, with the 28px miss explained rather than the range silently widened"
  - "CFG-47's three retirement records re-verified intact after five later plans edited the same files again"
  - "the app's sixth standing design-system contract (review-feedback discipline) in sketch-findings-skypane"
  - ".planning/phases/27-.../deferred-items.md — the règles-par-vol deferral, the unwrapped rules grid, DIRTY_SECTION_ATTR, and three open PROVISIONAL decisions"
affects: []

tech-stack:
  added: []
  patterns:
    - "re-derive every count by RUNNING, at the phase's close, never by trusting an earlier plan's own report of it"
    - "re-verify a byte-identical proof against the PHASE'S BASE COMMIT, not just against the plan that first made the claim, when later plans touched the same file again"
    - "a bare grep and an anchored/comment-stripped grep are reported side by side whenever they diverge, so the next reader never mistakes a growing bare count for a regression"
    - "when a requirement's own literal premise (a defect to fix) does not survive investigation, the row stays unticked and the finding is recorded as 'investigated, no defect found' — never silently rounded up to 'fixed'"

key-files:
  created:
    - .planning/phases/27-companion-review-feedback-the-defects-and-the-noise-the-deve/deferred-items.md
  modified:
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md
    - .claude/skills/sketch-findings-skypane/SKILL.md

key-decisions:
  - "CFG-65 left unticked: the title-form 'inconsistency' the developer reported does not hold as literally worded — 27-06's inventory found two forms serving two genuinely different grammatical roles (card title vs. supersection intro), not one form split two ways. Recorded as 'investigated, no defect found' rather than 'fixed', per the standard Phases 23-25 held."
  - "CFG-68 ticked despite the measured height (3524px) missing 27-07's own predicted range (3446-3496px) by 28px — the requirement's own clause asks that the height be REPORTED against a stated prediction, not that the prediction be hit, and the miss itself is explained (the prediction's text-cut term wrongly summed two regions that never render on Display) rather than the range silently widened to fit."
  - "CFG-63's leave-guard clause recorded as RE-SCOPED, not silently satisfied: the requirement anticipated partial retirement ('kept where it confirms a destructive act'); the developer's own binding decision instead kept it alive in full, for a different, narrower reason (protecting an edit that never fires change) — ticked because the developer's own decision is binding and the spirit of the requirement (no save button, one save model, one failure vocabulary) is fully met."
  - "The nine ticked requirements' evidence is re-verified on the FINISHED tree today, not copied from each plan's own SUMMARY — CFG-62's byte-identical arc proof and CFG-64's unchanged-floor-check proof were both re-run against the phase's base commit (839489a) after five later plans touched the same files again, and both still hold exactly."

requirements-completed: [CFG-62, CFG-63, CFG-64, CFG-66, CFG-67, CFG-68, CFG-69, CFG-70, CFG-71]

# Metrics
duration: ~2h45m
completed: 2026-09-15
---

# Phase 27 Plan 09: The closing gate — every count re-derived, the ledger written against the code Summary

**Nine of ten requirements ticked with per-clause evidence re-verified on the finished tree (not copied from earlier SUMMARYs); CFG-65 deliberately left unticked after investigation found no real title-form inconsistency; Display measured 3524px at 390px against 27-07's own stated ≈3446-3496px prediction with the 28px miss explained rather than absorbed; and the app's sixth design-system contract — review-feedback discipline — recorded in `sketch-findings-skypane`.**

## Performance

- **Duration:** ~2h45m
- **Tasks:** 4 of 4 (Tasks 1-3 produced no file diffs — pure re-verification; Task 4 is the only task with a commit)
- **Files modified:** 4 (3 modified, 1 created)

## Accomplishments

- Ran the whole suite (`scripts/run-all-tests.sh`, `PYTHON=server/.venv/bin/python3`): exactly the 5 sandbox baseline failures, verified **by name**, unchanged from the set every earlier plan in this phase reported. `grep -c SKIP` over the whole run is 0. Total wall time 265.9s at `JOBS=4`.
- Enumerated and confirmed passing, by name, all seven scripts-blocked save-to-disk checks this phase's floor depends on (25-04 through 25-07, 27-03's floor proof, 27-07's arrivals grid).
- Measured Display's page height at 390px today, both scripted (3524px) and scripts-blocked (5550px) — reproducing 25-06's own conditions exactly — and reported the scripted figure against 27-07's own stated prediction, naming why the measurement missed the predicted range rather than silently widening it.
- Proved every structural pin together, once, at the phase's end: zero new script, zero new route (confirmed by source diff against the phase's base commit, not by re-deriving the route list by hand), the deferred-script pin at 15, `@keyframes`/`:has()` counts unmoved (comment-stripped), zero stray comment terminators, both standing refusals (overlay drawer, sticky day headers) still refused.
- Wrote the Phase 27 coverage ledger in `.planning/REQUIREMENTS.md`: the dial defect's own paragraph, one subsection per correction/finding, and a full phase-gate section — walking CFG-62 through CFG-71 against the code, re-verifying two things this phase itself warned would need care (CFG-68's height prediction, CFG-47's retirement note).
- Updated `sketch-findings-skypane`: a new "review-feedback discipline" paragraph (the sixth standing contract), a new "Settings auto-save" paragraph superseding the dirty-bar entry in writing, a one-title-form finding folded into the Spacing contract, and Phase 27 folded-in-work / Design-Areas-table entries throughout.
- Created `deferred-items.md` for this phase: the "règles par vol" view, the unwrapped rule-add grid, `DIRTY_SECTION_ATTR`, and three open PROVISIONAL decisions the developer has not yet ruled on (the dial caption's blanking duration, auto-save's `change`-not-`input` trigger, no per-field error delivery).
- Filled in ROADMAP.md's Phase 27 entry: all nine plan checkboxes ticked, the Requirements line updated to reflect final tick status, a closing summary paragraph added matching the phase-close convention every prior phase entry carries.

## Task Commits

1. **Task 1: Run everything; name the five** — no file diff (pure verification; findings folded into this SUMMARY and the ledger)
2. **Task 2: Measure Display's height against the stated prediction** — no file diff (documentation-only, matching 27-07's own Task 4 precedent; the measurement script lives in the session scratchpad, not the repo)
3. **Task 3: Prove the structural pins and the two standing refusals, together** — no file diff (pure verification)
4. **Task 4: The ledger, the design authority, the deferred item, and the roadmap** — `6de7423` (docs)

**Plan metadata:** this SUMMARY's own commit, plus the `state advance-plan`/`update-progress` commit that follows it.

## Files Created/Modified

- `.planning/REQUIREMENTS.md` — nine `[ ]`→`[x]` checkbox flips (CFG-62, 63, 64, 66, 67, 68, 69, 70, 71), all ten traceability rows (CFG-62..71) rewritten with post-close evidence, and the new "Phase 27 coverage ledger" section (dial defect, nine correction/finding subsections, the phase gate, `deferred-items.md` pointer, the human sweep) inserted before the file's closing v1/v2 coverage summary.
- `.planning/ROADMAP.md` — Phase 27's nine plan checkboxes ticked, the Requirements line updated, a closing summary paragraph appended matching every other closed phase's own entry shape.
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the top "Current as of" line advanced to Phase 27; a new "review-feedback discipline" paragraph in `<design_direction>` (the sixth standing contract: assert relationships not endpoints, measure the resolved hit-target box in its own container, a stale comment can sit beside correct code, `git commit --only` commits the working tree not the index); a new "Settings auto-save" paragraph superseding the save-bar/dirty-bar account in writing; the one-title-form finding folded into the Spacing paragraph; the Design Areas table's Data Density/Control Density/Settings Page Patterns rows extended with Phase 27 notes; a new Phase 27 bullet in the Folded-In Work list.
- `.planning/phases/27-companion-review-feedback-the-defects-and-the-noise-the-deve/deferred-items.md` (created) — the "règles par vol" deferral, the unwrapped rule-add grid, `DIRTY_SECTION_ATTR`, and three open PROVISIONAL decisions.

## Decisions Made

See `key-decisions` in the frontmatter for the full reasoning on each; in one line:

1. CFG-65 left unticked — the title-form "inconsistency" does not survive investigation; recorded as "investigated, no defect found."
2. CFG-68 ticked despite the height measurement missing 27-07's own predicted range — the requirement asks for honest reporting against a stated figure, not for hitting it, and the 28px miss is explained rather than hidden.
3. CFG-63's leave-guard clause recorded as RE-SCOPED per the developer's own binding decision (kept alive in full, for a narrower reason than the requirement's own wording anticipated).
4. Every ticked requirement's evidence is re-verified on the finished tree today (byte-identical proofs re-run against the phase's base commit), not copied forward from an earlier plan's own SUMMARY.

## The measured height gap, explained (not absorbed)

Display's scripted height at 390px measured **3524px** today — 219px under 25-06's 3743px baseline, but **28px above** the top of 27-07's own stated prediction (≈3446-3496px, midpoint ≈3471px). The cause: 27-07's own text-cut term (−40 to −90px, midpoint −65) summed all 236 characters 27-06 cut across three regions, but two of those three regions (the wake-interval caption, the two wake gauges) render only on `/device` — `screens.GROUP_WAKE_INTERVAL` is Device-scope-only by its own code comment — and never contribute to Display's height at all. Only the Quiet hours paragraph's 67-of-236 characters actually apply. Scoped correctly, the text-cut term should have been roughly a third of what was estimated. A second, smaller contributor in the same direction: the `.save-status` region that replaced the dirty bar's fixed `padding-bottom` reservation measures 0px of its own box height when empty (only its 8px `margin-top` is real), so the −144px `.dirty-ready` padding removal is very nearly fully realized rather than partly offset. Together these explain most of the 28px gap. 2600px remains 924px away; what is left is still four more Display cards plus the Frame strip, not a grid.

The scripts-blocked (no-JS) height — measured for the first time at this close — is **5550px at 390px**, roughly 2000px taller than the scripted page, confirming 27-07's own prediction that the carousel extension's real saving is for a no-JS reader (all three grids render un-collapsed with scripts blocked) rather than for the default scripted load.

## CFG-47's retirement note — re-verified intact

All three records confirmed present, dated `2026-09-14`, and consistent with the tree Phase 27 actually produced: the ticked requirement row, the traceability row, and the D16 coverage-ledger section (Phase 25's own ledger). `grep -c RETIRED .planning/REQUIREMENTS.md` → **3**, re-run today after 27-06, 27-07 and 27-08 each edited `config_page.py`/`style.css` again since 27-05 landed.

## The phase gate — quoted numbers

- `scripts/run-all-tests.sh`: exactly 5 failing checks, verified BY NAME (2× WR-11 in `companion/test_companion_app.py`, 2× WR-11 in `server/test_manual_resolutions.py`, 1× `anomaly_active()` in `companion/test_status_pages.py`). No sixth. `grep -c SKIP` — 0. Total wall time **265.9s** (`JOBS=4`).
- `companion/test_browser_ux.py` standalone: **88/88, 0 SKIP, 4m17.4s (257.4s)**.
- Structural pins (comment-stripped/brace-anchored, against base commit `839489a`): `@supports selector(:has(*))` blocks 1→1, `@keyframes` 4→4, `ls companion/static/*.js` 17→17, deferred `<script src=` on the authenticated shell 15→15, stray comment terminators balanced (486/486), `interpolate-size`/`calc-size(` 2→2, overlay drawer 0→0, `position: sticky` 1→1 (still `.dashboard-sidebar`, not a day header). A bare `@keyframes` grep returns 6 and a bare `:has(*)` grep returns 9 — both prose, recorded alongside the real counts.
- Unauthenticated route set: unchanged — `git diff 839489a..HEAD -- companion/app.py` touches zero `require_session()` call sites across a 63-line diff, and `git diff 839489a..HEAD -- companion/` adds zero `*_ROUTE` constants anywhere.
- One intermittent 27-08 flagged (`SkyPaneDirtyState` timing on `quiet_hours_start` under 4-way parallel load) did **not** recur in this closing plan's own final run.

## Deviations from Plan

None triggering Rules 1-4. Tasks 1-3 produced no file diffs because everything they verify was already correct on the tree handed to this plan — this is itself evidence the preceding eight plans' own closing claims held, not a shortfall in this plan's own work.

## Issues Encountered

None. No auth gates, no package installs, no checkpoints.

## Known Stubs

None. Every figure in the coverage ledger and the phase gate is either re-derived by running today or a direct source-diff/grep result quoted verbatim.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 27 is closed: 9/9 plans complete, nine of ten requirements ticked with evidence, one (CFG-65) deliberately left unticked with its own decision recorded.
- The PR is **not** marked ready and **not** merged — the developer's own real-phone/desktop review (the human sweep enumerated in the coverage ledger's closing section) is the phase's real gate and has not happened yet.
- `deferred-items.md` carries three open PROVISIONAL decisions and the "règles par vol" view for whoever plans the next companion phase.

---
*Phase: 27-companion-review-feedback-the-defects-and-the-noise-the-deve*
*Completed: 2026-09-15*

## Self-Check: PASSED

- `.claude/skills/sketch-findings-skypane/SKILL.md` — FOUND.
- `.planning/REQUIREMENTS.md` — FOUND.
- `.planning/ROADMAP.md` — FOUND.
- `.planning/phases/27-companion-review-feedback-the-defects-and-the-noise-the-deve/deferred-items.md` — FOUND.
- Commit `6de7423` — FOUND in `git log --oneline --all`.
