---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 01
subsystem: docs
tags: [deploy, systemd, caddy, ci, github-actions, doc-drift]

# Dependency graph
requires: []
provides:
  - "deploy/ and .github/workflows/ comments and deploy/README.md corrected to match the code as it stands after Phases 32-40"
  - "41-DOC-DRIFT-DEPLOY.md, a 35-row claim-by-claim evidence log covering every deploy/CI comment and every deploy/README.md section"
affects: [41-02, 41-07]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Doc-drift verification: cite the current implementing file:line or a command's output, never the audit ledger, for every claim (accurate or corrected)"

key-files:
  created:
    - .planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-DOC-DRIFT-DEPLOY.md
  modified:
    - deploy/skypane.env.example
    - deploy/Caddyfile
    - deploy/provision.sh
    - deploy/README.md
    - deploy/.gitignore
    - .github/workflows/ci.yml

key-decisions:
  - "DOC-01 requirement left unticked: this plan is explicitly part 1 of 2 (41-02 owns ARCHITECTURE.md/COMPLIANCE.md/README.md/CLAUDE.md/VENDOR.md/server-README/Python comments); marking DOC-01 complete now would be premature, so REQUIREMENTS.md is left untouched here"
  - "deploy/.gitignore's stale SKYPANE_BYOS_SECRET comment fixed even though the file isn't in this plan's files_modified list (Rule 1 - the fact it names is objectively wrong and the fix is a one-line comment-only correction directly adjacent to the env-template work already in scope)"
  - "The 'single writer' ledger example (poll_loop.py:1116-area) is not addressed here - it never appears in any file this plan touches; it lives in server/poll_loop.py, which is 41-02's 'Python comment claims' territory"

requirements-completed: []

# Metrics
duration: ~50min
completed: 2026-09-28
---

# Phase 41 Plan 01: Deploy/CI doc-drift correction Summary

**Corrected six real inaccuracies across deploy/ and CI comments/docs (env install path, byos "persists nothing" claimed twice, a Caddy log mode typo, an incomplete CI header, two stale planning-file pointers, and a retired-secret .gitignore comment), with all 35 checked claims logged against current code in 41-DOC-DRIFT-DEPLOY.md.**

## Performance

- **Duration:** ~50 min
- **Started:** 2026-09-28 (session start)
- **Completed:** 2026-09-28T04:59:29Z
- **Tasks:** 2 (both `type="auto"`)
- **Files modified:** 6 (plus 1 created: the drift log)

## Accomplishments

- Re-verified all six ledger-named drift patterns (byos bind, "persists nothing" ×2 locations, harness count, log file mode, env path) against the code as it stands after Phases 32-40, not the 2026-09-23 audit snapshot — five were genuinely stale and corrected, one ("18 harnesses") was already fixed and is now logged as `accurate` with evidence instead of being silently assumed.
- Walked every comment in 15 deploy/CI files (env template, Caddyfile, every `deploy/*.sh`, every systemd unit/timer, `ci.yml`, `firmware.yml`) and every `## `-headed section of `deploy/README.md` (14 sections), producing a 35-row evidence table — every row names a current `file:line` or a command's output, never the ledger.
- Found and fixed one drift the ledger never named: `deploy/.gitignore`'s own comment still described the real env file as containing `SKYPANE_BYOS_SECRET`, a variable retired when device enrolment moved to the per-device registry (Phases 34/37).
- Proved every non-markdown edit is comment-only: `check_comment_history.py same-code --base 7bd8664` exits 0 across all 15 files, and `deploy/tests` still passes 137/137.

## Task Commits

1. **Task 1: Verify and correct claims in deploy config, unit, script and workflow comments** - `4d4c51b` (docs)
2. **Task 2: Verify and correct deploy/README.md against the deploy scripts, units and backup tooling** - `313e0a7` (docs)

_Both tasks are doc/comment-only; no `feat`/`fix` commits were needed since nothing here changes runtime behavior._

## Files Created/Modified

- `.planning/phases/41-docs-repository-hygiene-and-closing-re-audit/41-DOC-DRIFT-DEPLOY.md` - 35-row claim-by-claim evidence log (created)
- `deploy/skypane.env.example` - install path corrected to `/opt/skypane/skypane.env`; "persists nothing" replaced with what byos actually persists (the latest battery reading)
- `deploy/Caddyfile` - same "persists nothing" correction, on the access-log comment
- `deploy/provision.sh` - Caddy access-log mode comment corrected from 640 to 660 (matching `deploy/Caddyfile:33`)
- `.github/workflows/ci.yml` - header now lists every check the `test` job actually runs (comment-history guard, mypy, function-size gate, shellcheck, systemd unit scoring), not just lint/pytest/attribution
- `deploy/README.md` - two stale planning-file pointers removed (`02-05-PLAN.md`/`02-05-SUMMARY.md`, `06-11-PLAN.md`); every other claim across all 14 sections verified accurate, no other prose changed
- `deploy/.gitignore` - comment reworded off the retired `SKYPANE_BYOS_SECRET` name

## Decisions Made

- Left `DOC-01`'s REQUIREMENTS.md checkbox unticked - the plan frontmatter names `DOC-01` but the plan itself is explicitly "part 1 of 2"; the other doc surface (ARCHITECTURE.md, COMPLIANCE.md, root README.md, CLAUDE.md, VENDOR.md, server/README.md, Python comments) is 41-02's job, and 41-07 folds both into the closing DOC-01 row per 41-CONTEXT.md.
- Fixed `deploy/.gitignore` even though it isn't in this plan's `files_modified` list, since it's a one-line, comment-only, directly-on-topic correction discovered while checking the "Secrets discipline" section's claims (Rule 1 - the comment stated an objectively false fact about what the file contains).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] deploy/.gitignore's comment named a retired secret variable**
- **Found during:** Task 2 (verifying deploy/README.md's "Secrets discipline" section)
- **Issue:** The comment said the real `skypane.env` "contains SKYPANE_BYOS_SECRET" - that variable was retired when device enrolment moved to the per-device registry (`devices.json`); `deploy/skypane.env.example` itself already documents this ("A stray SKYPANE_BYOS_SECRET=... line is harmless and can be deleted").
- **Fix:** Reworded the comment to describe the file generically (holds `SKYPANE_COMPANION_PASSWORD` and the rest of `skypane.env.example`'s values) instead of naming a retired variable.
- **Files modified:** `deploy/.gitignore`
- **Verification:** `check_comment_history.py check` still exits 0; logged as row 35 in `41-DOC-DRIFT-DEPLOY.md`.
- **Committed in:** `313e0a7` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary correctness fix, one line, comment-only, directly adjacent to the plan's own scope. No behavioral or scope creep.

## Issues Encountered

`state.advance-plan` reproduced this file's own documented recurring bugs again: it wrote into
the demoted, "kept verbatim, as data, no longer parsed as state" 2026-09-04 stale block (inside
the fenced ` ```yaml ` block under "Structural repair, 2026-09-13"), flipping its `status` from
`Ready to plan` to `Ready to execute` and its progress bar from 94% to 93% — reverted by hand to
match the pre-Phase-41 baseline (`git show 7bd8664:.planning/STATE.md`). Separately,
`state.update-progress`/`state.advance-plan` again left the top frontmatter's `percent` at the
stale `91` (`completed_phases/total_phases` = 49/54) instead of the tool's own correctly computed
`93` (410/442); corrected to `93` by hand, per this file's established precedent.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `41-DOC-DRIFT-DEPLOY.md` is ready for 41-02 to continue numbering from row 35, and for 41-07's closing DOC-01 row to fold in.
- `41-02` still owns: `ARCHITECTURE.md`, `COMPLIANCE.md`, root `README.md`, `CONTRIBUTING.md`, `.claude/CLAUDE.md` (including its now-confirmed-stale "three systemd units" hosting-row claim, logged here as row 17 `handed to 41-02`), `firmware/VENDOR.md` (doc content only), `server/README.md`, and Python comment claims (including the "single writer" ledger example in `server/poll_loop.py`, not touched here).
- No blockers for 41-02 or the rest of the phase.

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*

## Self-Check: PASSED

All 8 claimed files found on disk (`deploy/skypane.env.example`, `deploy/Caddyfile`,
`deploy/provision.sh`, `.github/workflows/ci.yml`, `deploy/README.md`, `deploy/.gitignore`,
`41-DOC-DRIFT-DEPLOY.md`, `41-01-SUMMARY.md`); both task commit hashes (`4d4c51b`, `313e0a7`)
found in `git log --oneline --all`.
