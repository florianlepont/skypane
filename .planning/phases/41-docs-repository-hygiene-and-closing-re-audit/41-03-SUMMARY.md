---
phase: 41-docs-repository-hygiene-and-closing-re-audit
plan: 03
subsystem: infra
tags: [git, gzip, attribution, hygiene, illustrations]

# Dependency graph
requires:
  - phase: 41-docs-repository-hygiene-and-closing-re-audit
    provides: "41-01/41-02 doc-drift corrections (deploy/README.md, ARCHITECTURE.md, COMPLIANCE.md, firmware/VENDOR.md)"
provides:
  - "hardware/logs/backoff-powercycle.log compressed in the working tree (15.8 MB -> 86.5 KB), no git-history rewrite"
  - "server/assets/icons/illustrations/_unresolved/air-caraibes-atr72-unused.png removed after confirming it is unreferenced; it no longer ships via git archive"
  - "explicit record that /gsd-cleanup phase-directory archival is deferred to the real v1.0 close after Phase 42"
affects: [42-ota]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Large evidentiary log files are compressed in the working tree only (gzip -9 -n -k), never via git-history rewrite; references are updated to the .gz path with a decompress-first reproduction command"
    - "Before deleting an asset flagged unused by an audit snapshot, re-grep the whole repo at execution time to confirm it is still unused, since audit snapshots can go stale"

key-files:
  created:
    - hardware/logs/backoff-powercycle.log.gz
  modified:
    - hardware/BACKOFF-OBSERVATION.md
    - server/assets/icons/illustrations/VENDOR.md
  deleted:
    - hardware/logs/backoff-powercycle.log (working tree only; unchanged in git history at and before 7bd8664)
    - server/assets/icons/illustrations/_unresolved/air-caraibes-atr72-unused.png

key-decisions:
  - "D-A6 honored: hardware/logs/backoff-powercycle.log was gzipped in the working tree only; no git filter-branch/BFG/filter-repo was run, so the uncompressed blob remains reachable in every commit up to and including 7bd8664."
  - "air-caraibes-atr72-unused.png was re-verified unused at execution time (not trusted from the 2026-09-23 audit snapshot alone) before deletion, per 41-CONTEXT.md's DOC-02 instruction."
  - "/gsd-cleanup phase-directory archival is explicitly deferred, not run: ROADMAP.md places Phase 42 (OTA) in v1.0 scope immediately after Phase 41, so the v1.0 milestone is not closing at this phase."

patterns-established:
  - "Reproduction commands for a gzipped evidence log decompress on the fly via process substitution (`<(gunzip -c file.log.gz)`), without modifying the log-parsing tool itself."

requirements-completed: [DOC-02]

# Metrics
duration: 12min
completed: 2026-09-28
---

# Phase 41 Plan 03: Repository Hygiene (DOC-02) Summary

**Compressed a 15.8 MB hardware log to 86.5 KB in the working tree (git history untouched), removed a confirmed-unused illustration draft and its attribution row, and recorded that phase-directory archival is deferred until after Phase 42.**

## Performance

- **Duration:** 12 min
- **Started:** 2026-09-28T05:31:48Z
- **Completed:** 2026-09-28T05:43:00Z (approx.)
- **Tasks:** 2/2
- **Files modified:** 5 (1 created, 2 modified, 2 deleted)

## Accomplishments
- `hardware/logs/backoff-powercycle.log` (15,770,875 bytes) is now tracked as `hardware/logs/backoff-powercycle.log.gz` (86,539 bytes), verified byte-identical via sha256 before compressing and after decompressing; the uncompressed blob is untouched in git history (`git rev-list --count HEAD` grew from 51 at `7bd8664` to 59, appended-only).
- Every non-`.planning/` reference to the log in `hardware/BACKOFF-OBSERVATION.md` now points at the `.gz` path, with reproduction commands that decompress via process substitution (`hardware/logtools.py` has no gzip support and was not modified).
- `server/assets/icons/illustrations/_unresolved/air-caraibes-atr72-unused.png` was proven unreferenced by any code path (not just the attribution table) before deletion, then removed; `server/assets/icons/illustrations/VENDOR.md`'s attribution row and now-false "this one file exists on disk" prose were replaced with a one-sentence note, and two dangling "see the `_unresolved/` table above" references were repointed.
- `/gsd-cleanup` archival of completed v1.0 phase directories was explicitly NOT run — see "Archival deferred" below.

## Task Commits

Each task was committed atomically:

1. **Task 1: Gzip the power-cycle log in the tree and update its references** - `2101217` (chore)
2. **Task 2: Remove the unused illustration draft and its attribution row; record the archival deferral** - `38d3e88` (chore)

**Plan metadata:** (this commit) - docs: complete 41-03 plan

## Files Created/Modified
- `hardware/logs/backoff-powercycle.log.gz` - gzip -9 -n -k of the original log, sha256-verified byte-identical on decompression
- `hardware/logs/backoff-powercycle.log` - removed from the working tree only (git history unchanged, D-A6)
- `hardware/BACKOFF-OBSERVATION.md` - every path reference repointed to `.log.gz`; reproduction commands updated to decompress via process substitution; the original 2026-08-26 checker transcript is left verbatim as evidence
- `server/assets/icons/illustrations/_unresolved/air-caraibes-atr72-unused.png` - deleted after confirming no code path references it
- `server/assets/icons/illustrations/VENDOR.md` - attribution row and stale prose for the deleted draft replaced with a one-sentence note; two dangling "table above" cross-references repointed

## Decisions Made
- Compressed the log in the working tree only, per D-A6 — no `git filter-branch`, `filter-repo`, `rebase`, or BFG was run. `git rev-list --count 7bd8664` (51) vs `git rev-list --count HEAD` (59, after this plan's two commits) confirms history was only appended to, never rewritten.
- Re-verified the PNG's unused status at execution time via three independent greps (see Task 2 commit message) rather than trusting the audit's 2026-09-23 snapshot, since 41-CONTEXT.md explicitly flagged that snapshot as possibly stale.
- Did not run `/gsd-cleanup`: ROADMAP.md places Phase 42 (OTA) in v1.0 scope, immediately after Phase 41, so the v1.0 milestone does not close here (see "Archival deferred" below).

## Deviations from Plan

None of Rules 1-4 applied to the planned actions themselves (both tasks executed exactly as specified — gzip only, delete only after confirming unused). One **transparency finding** surfaced during Task 1's required re-run of the reproduction command, disclosed here per the plan's own instruction to "record the comparison in the SUMMARY," not fixed, since the plan explicitly forbids editing the doc's observed results/verdicts/checker transcript (they are evidence):

### Checker re-run result differs from the doc's recorded transcript (not a compression artifact)

- **Found during:** Task 1, required re-run of `hardware/logtools.py check-backoff hardware/logs/backoff-run.log <(gunzip -c hardware/logs/backoff-powercycle.log.gz) --min-steps 6 --expect-persist --expect-reset`.
- **Recorded in the doc (2026-08-26 session):** `backoff: 5/8 checks pass`, exit code 1, with `check_persist` FAILing ("no power-on wake was followed by a failed poll").
- **Actual result today:** `backoff: 6/8 checks pass`, exit code 1. Six checks match the doc exactly (`check_min_polls`, `check_curve`, `check_sleep_variety`, `check_sleep_entry` all PASS; `check_sequence` and `check_wall_clock` FAIL with the identical messages the doc records). The one check that differs is `check_persist`, which now **PASSes**.
- **Root cause, confirmed not a gzip artifact:** re-ran the identical command against a pristine copy of the file extracted straight from git (`git show 7bd8664:hardware/logs/backoff-powercycle.log`, sha256-verified identical to the `.gz`'s decompressed content) and got the same 6/8 result. `grep -n "power-on" <decompressed log>` shows the tracked log file genuinely contains twelve `wake reason=power-on` lines (`boot_count=49` through `boot_count=60`, timestamps `08:49:05`–`09:02:57` on 2026-08-26), well beyond the nine rows the doc's "Observed Sequence" table narrates (which stops at `boot_count=45`). `logtools.py`'s `check_persist` function is byte-identical to its first commit in this repo's history (only cosmetic comment-purge diffs touch the file) — the function did not change; the underlying log content already contained more power-on wakes than the doc's table describes.
- **Disposition:** left the doc's evidentiary content (verdict, Observed Sequence table, Checker Output transcript, Capture-Timing Limitation claim that the log "does not" contain `wake reason=power-on`) completely unedited, per the plan's explicit instruction — only path references were repointed to `.log.gz`. This is a pre-existing content gap between the doc's 9-row table and the full log file's ~312,533 lines, unrelated to compression and out of this hygiene plan's scope to resolve (it reads as a DOC-01-flavoured doc/evidence mismatch in a hardware observation report, not a DOC-02 repository-hygiene item). Flagging here for visibility; no further action taken in this plan.

**Total deviations:** 0 auto-fixed; 1 transparency finding disclosed (no code/doc change made beyond the plan's own required path updates).
**Impact on plan:** None on this plan's own scope. The finding does not affect DOC-02's success criteria (log compressed correctly, references updated, reproduction command still runs and its command line is documented correctly).

## Issues Encountered
None beyond the checker-result discrepancy documented above.

## Archival deferred

`/gsd-cleanup` archival of completed v1.0 phase directories was **not run** in this plan. `.planning/ROADMAP.md` places Phase 42 (OTA) in v1.0 scope, running immediately after Phase 41 with gate G-41 checking that Phase 41 is complete on `main` before Phase 42 starts — so the v1.0 milestone is not closing at this phase, and archiving completed phase directories is deferred to the real v1.0 close, after Phase 42 finishes. This matches the default behavior specified in `41-CONTEXT.md`'s DOC-02 decision.

Current `.planning/` size at the time this plan ran (2026-09-28):
- `find .planning -type f | wc -l` → **1645 files**
- `du -sh .planning` → **59M**

(The 2026-09-23 audit ledger's snapshot measured `.planning` at 1198 files / 49 MB; the growth to 1645 files / 59M reflects Phases 33-41's own planning artifacts accumulating since that snapshot — consistent with archival not having happened yet.)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- DOC-02 is complete: the oversized log is compressed in the tree with history intact, the unused illustration draft no longer ships, and attribution/illustration checks and tests pass.
- Phase 41's remaining plans (DOC-01 already done in 41-01/41-02; DOC-03 closing re-audit and REQUIREMENTS.md bookkeeping) are unaffected by this plan's scope.
- Archival of completed v1.0 phase directories remains an explicit open item for whoever closes the v1.0 milestone after Phase 42 merges.

## Self-Check: PASSED

- FOUND: hardware/logs/backoff-powercycle.log.gz
- CONFIRMED ABSENT: hardware/logs/backoff-powercycle.log
- CONFIRMED ABSENT: server/assets/icons/illustrations/_unresolved/air-caraibes-atr72-unused.png
- FOUND commit: 2101217
- FOUND commit: 38d3e88

---
*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Completed: 2026-09-28*
