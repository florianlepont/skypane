---
phase: quick/260905-bba
plan: 01
subsystem: docs
tags: [ui-spec, design-contract, documentation-reconciliation, companion]

requires:
  - phase: 06.6.4.1
    provides: the original UI-SPEC.md design contract (approved 2026-09-01)
  - phase: 06.6.4.1.1
    provides: the largest single batch of post-approval visual-contract changes reconciled here
provides:
  - A design-contract UI-SPEC.md that agrees with live companion/static/style.css and companion/layout.py as of 2026-09-05
  - A sketch-findings-skypane SKILL.md phase-status claim that points at ROADMAP.md instead of restating a status
  - A Post-Approval Amendment Ledger enumerating all 13 reconciled batches, auditable against the file
affects: [any future companion/ UI phase reading 06.6.4.1-UI-SPEC.md or sketch-findings-skypane for current design-system facts]

tech-stack:
  added: []
  patterns:
    - "SUPERSEDED-in-place convention for amending an approved design contract after ship: mark the replaced value, attribute it to the batch that replaced it, never delete the original text"
    - "Post-Approval Amendment Ledger as an auditable table (Batch | What it changed | Section | Outcome), one row per reviewed batch including harmless ones"

key-files:
  created: []
  modified:
    - .claude/skills/sketch-findings-skypane/SKILL.md
    - .planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md

key-decisions:
  - "Frontmatter status moved to approved-amended with a last_amended key; reviewed_at 2026-09-01 and the Checker Sign-Off block stay untouched (DP-5) — verified byte-identical after all edits"
  - "Corrected the plan's own D-08 citation for the serif-stack reorder to D-12/UIR-20, verified against companion/static/style.css:122-132 and 06.6.4.1.1-CONTEXT.md's own D-12 entry"
  - "Corrected the plan's own UIR-24 citations for D-14 (sibling-card gap) and D-15 (card padding) to UIR-25, verified against style.css:3232 and :4123 — the live code comments, not the plan's prose, were treated as authoritative per DP-6"
  - "History's 'Now showing' and 'Recent renders' sections (§8.1/§8.2) marked RETIRED rather than merely amended — they no longer exist in any form (260903-c4o folded them, 260903-etm deleted the successor outright), matching the ROADMAP's own disclosed drift finding from 06.6.4.1-09's checkpoint"
  - "No code Findings recorded — every reconciled discrepancy was documentation drift (UI-SPEC vs. reality), not a gap between the UI-SPEC's requirements and the code's implementation of them"

requirements-completed: []

coverage: []

duration: ~55min
completed: 2026-09-05
status: complete
---

# Quick Task 260905-bba: Reconcile 06.6.4.1-UI-SPEC.md and sketch-findings-skypane Summary

**Reconciled two design-contract documents against eight post-approval batches of shipped companion UI work — zero code changed, every superseded value marked in place and attributed, a new Amendment Ledger makes the sweep auditable.**

## Performance

- **Duration:** ~55 min
- **Started:** 2026-09-05 (session start)
- **Completed:** 2026-09-05
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- `sketch-findings-skypane` SKILL.md's stale "Phase 06.6.4.1 remains open" claim (already wrong twice, per commit `cde14f1`) is replaced with a pointer to `.planning/ROADMAP.md` as the live record, appearing twice, so the claim structurally cannot rot a third time.
- `06.6.4.1-UI-SPEC.md`'s Design System, Spacing Scale, Typography, and Color sections now agree literally with live `companion/static/style.css` (verified line-by-line this session), with every replaced value marked `SUPERSEDED` and attributed to the phase or quick task that replaced it.
- Every per-page Component Spec section (Settings, Health, Airlines, History) was checked against live code; History's two largest divergences (`§8.1` "Now showing", `§8.2` Recent renders) are marked **RETIRED** with original text kept legible, matching the ROADMAP's own disclosed drift finding.
- A new `## Post-Approval Amendment Ledger` (13 rows) and an explicit `### Findings for the developer` subsection (none found) were appended before the Checker Sign-Off block, making the "the rest of the file was swept" claim checkable rather than asserted.
- The 2026-09-01 Checker Sign-Off block and `reviewed_at` are byte-unchanged; `git status --porcelain -- companion/ server/` is empty throughout (documentation-only boundary held).

## Task Commits

1. **Task 1: Retire the stale phase-closure claims in the sketch-findings-skypane skill** - `1d031c8` (docs)
2. **Task 2: Reconcile the UI-SPEC's frontmatter and system-level sections against live style.css** - `bc7e900` (docs)
3. **Task 3: Reconcile the UI-SPEC's per-page Component Specs and append the Amendment Ledger** - `ada3a38` (docs)

**Plan metadata:** pending final commit (this SUMMARY + STATE.md + ROADMAP.md — handled by the orchestrator per this project's `commit_docs` convention; ROADMAP.md is explicitly NOT updated by this quick task's own constraints)

_Note: all three commits are `docs` type — this is a documentation-only reconciliation, no `feat`/`fix`/`test` commits were needed._

## Files Created/Modified

- `.claude/skills/sketch-findings-skypane/SKILL.md` - Two stale phase-status statements (the `<context>` "Current as of" paragraph, the `<metadata>` Folded-In Work entry for 06.6.4.1) replaced with a ROADMAP.md pointer; nothing else in the file touched (2 insertions, 2 deletions, surgical per the plan's own numstat gate)
- `.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md` - Frontmatter amended (`status: approved-amended`, `last_amended: 2026-09-05`, `amended_by` list); Design System/Spacing Scale/Typography/Color sections reconciled against live `style.css`/`layout.py`; Settings/Health/Airlines/History Component Specs reconciled against live `config_page.py`/`health_page.py`/`airlines_page.py`/`history_page.py`; Amendment Ledger and Findings subsection appended (100 insertions, 21 deletions across both tasks)

## Decisions Made

- Used the plan's own SUPERSEDED-in-place convention (matching the existing `§5.3`/Color-table precedent already in the file) for every amendment — no original text deleted, every replacement attributed to a named phase or quick task.
- Where the plan's own prose cited a D-*/UIR-* pairing that disagreed with the live `style.css` comment (D-08 vs. the code's D-12 for the serif reorder; UIR-24 vs. the code's UIR-25 for D-14/D-15's spacing changes), the live code comment was treated as authoritative per DP-6 — this plan's own drift list is "a starting point... assembled by one pass" (plan's own §Task 2 wording), not itself infallible.
- `.airline-card` markup and `.airline-card__chip` styling were both found changed since approval (image now wrapped in a `.airline-card__zoom` trigger button into the shared lightbox; chip absorbed into the 12px label voice) — recorded as amendments, not findings, since the UI-SPEC's own contract wasn't violated by the code, the code simply evolved past what the spec described.
- Settings' fifth-group drift (Quiet hours, Wake interval from Phases 10/11) and History's "Now showing" retirement were both recorded as citing the ROADMAP's own 06.6.4.1-09 developer-checkpoint disclosure, rather than presented as new findings — the developer already saw and approved both drifts at that checkpoint.

## Deviations from Plan

None — plan executed exactly as written. All three tasks' automated verification gates passed on the first attempt after the amendments were written (one environment-only wrinkle is noted below, not a plan deviation).

### Note on Task 3's verification gate (not a deviation, an environment observation)

Task 3's automated verify command uses `awk '/^### §8\.1/,/^### §8\.3/'` to scope a `SUPERSEDED` count to the History §8.1–§8.3 range. In a shell with no `LANG`/`LC_ALL` set (the sandbox's default), `awk`'s `.` (any-character) regex metacharacter does not match the multi-byte UTF-8 `§` character correctly, so the range match silently returns zero lines. Running the identical command with `LC_ALL=en_US.UTF-8` set (a normal, UTF-8-locale shell — the expected execution environment for this repo's own tooling) resolves correctly and the gate passes as designed. This is pre-existing behavior in the plan's own verify script — the `§` characters were already present in the file before this quick task touched it — not something introduced or fixed by this task. No plan text was altered to work around it.

## Issues Encountered

None beyond the locale note above.

## User Setup Required

None - no external service configuration required. Documentation-only change.

## Next Phase Readiness

- `06.6.4.1-UI-SPEC.md` and `sketch-findings-skypane`'s SKILL.md are both current as of 2026-09-05 and agree with live `companion/` code; either can be safely `@`-referenced by a future companion-UI phase without re-verifying the drift this task closed.
- The Post-Approval Amendment Ledger's convention (a row for every reviewed batch, `amended` or `no UI-SPEC change needed`) is now established in this file and can be extended by the next batch that touches companion UI, rather than restarted.
- No blockers. No code defects were surfaced — the Findings subsection is explicitly empty, backed by the same file:line/commit verification recorded inline throughout the amendments above.

## Self-Check: PASSED

- FOUND: `.claude/skills/sketch-findings-skypane/SKILL.md`
- FOUND: `.planning/phases/06.6.4.1-companion-page-by-page-ia-consolidation-full-page-by-page-vi/06.6.4.1-UI-SPEC.md`
- FOUND: `.planning/quick/260905-bba-reconcile-06-6-4-1-ui-spec-md-and-the-sk/260905-bba-SUMMARY.md`
- FOUND commit `1d031c8` (Task 1)
- FOUND commit `bc7e900` (Task 2)
- FOUND commit `ada3a38` (Task 3)

---
*Phase: quick/260905-bba*
*Completed: 2026-09-05*
