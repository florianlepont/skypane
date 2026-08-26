---
phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests
plan: 01
subsystem: infra
tags: [git, git-filter-repo, gitignore, secrets-hygiene, pre-publish-scrub]

# Dependency graph
requires: []
provides:
  - Repo-root .gitignore enforcing D-06 credential/cruft discipline repo-wide
  - Working tree free of the nested worktree pin and uncommitted cruft (F4/F5)
  - Developer's on-record decision on git-history scrub scope (Category A+B+C)
  - A git history with zero occurrences of the VPS IP/hostname, home Wi-Fi SSID/BSSID/device MAC, and home street address across any ref
  - A verified, restorable pre-rewrite backup bundle outside the repo tree
  - SCRUB-RECORD.md documenting the operation by category/count, never by value
affects: [04-02, 04-03, 04-04, 04-05, 04-06]

# Tech tracking
tech-stack:
  added: [git-filter-repo 2.47.0 (Homebrew, local-only tool, not a runtime dependency)]
  patterns: ["Sensitive literals live only in untracked .git/inkframe-scrub-*.txt files; every verification greps -F -f from the derived literals file, so no plan/summary ever restates a secret", "Angle-bracket placeholder tokens (<vps-ip>, <public-host>, <wifi-ssid>, <wifi-bssid>, <device-mac>, <street-address>, <home-city>) matching deploy/README.md's pre-existing convention"]

key-files:
  created:
    - .gitignore
    - .planning/phases/04-ci-cd-documentation-legal-compliance-github-actions-ci-tests/SCRUB-RECORD.md
  modified:
    - deploy/README.md (placeholder tokens; content unchanged in structure)
    - hardware/logs/first-light.log, hardware/logs/backoff-run.log (Wi-Fi literals replaced)
    - .planning/PROJECT.md, .planning/ROADMAP.md, .planning/STATE.md, and other tracked docs (VPS/address literals replaced across their full history, not just HEAD)

key-decisions:
  - "Developer selected scrub scope a-b-c: Categories A (VPS IP/hostname, D-05) + B (home Wi-Fi SSID/BSSID/device MAC) + C (home street address) all scrubbed in a single irreversible pass"
  - "git filter-repo needed both --replace-text (file/blob content) AND --replace-message (commit message text) — a literal survived in a commit message on the first pass using --replace-text alone; diagnosed and fixed before re-homing"
  - "Deleted the stale, fully-redundant claude/faience-blanche-mate-434eeb branch ref (the removed worktree's branch, F4) before the final prune — it carried zero unique commits over main but would have kept pre-rewrite objects reachable and re-surfaced old content in git log --all"

requirements-completed: [D-03, D-04, D-05, D-06]

coverage:
  - id: D1
    description: "Repo-root .gitignore enforces credential/cruft discipline (D-06), extending the five existing per-subdirectory ignore files without weakening any of them"
    requirement: D-06
    verification:
      - kind: other
        ref: "git check-ignore -q (run per-path individually, see Known Issues) against deploy/inkframe.env, firmware/main/secrets.h, .DS_Store — all ignored; deploy/inkframe.env.example — not ignored"
        status: pass
    human_judgment: false
  - id: D2
    description: "The nested worktree pin and uncommitted tracked/untracked cruft are resolved, leaving a clean tree safe for git reset --hard"
    verification:
      - kind: other
        ref: "git status --porcelain (empty) and git worktree list (1 entry)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Developer's scrub-scope decision recorded on the record before the irreversible rewrite ran"
    requirement: D-05
    verification:
      - kind: manual_procedural
        ref: "AskUserQuestion selection a-b-c, recorded verbatim in this plan's dispatch context and in SCRUB-RECORD.md"
        status: pass
    human_judgment: false
  - id: D4
    description: "Every approved sensitive literal (VPS IP/hostname, home Wi-Fi SSID/BSSID/device MAC, home street address) is absent from all commit diffs across every ref and from the working tree"
    requirement: D-04
    verification:
      - kind: other
        ref: "git log --all -p | grep -a -c -F -f .git/inkframe-scrub-literals.txt => 0; git grep -c -F -f .git/inkframe-scrub-literals.txt HEAD -- . => no matches"
        status: pass
    human_judgment: false
  - id: D5
    description: "A verified, restorable backup of the pre-rewrite history exists outside the repo tree, and the rewrite did not drop any commits"
    verification:
      - kind: other
        ref: "git bundle verify <backup path in SCRUB-RECORD.md> => passed; git rev-list --all --count before/after => 154/154"
        status: pass
    human_judgment: false
  - id: D6
    description: "Post-rewrite documentation reads naturally using the project's pre-existing angle-bracket placeholder convention, not sentinel/REDACTED tokens"
    verification: []
    human_judgment: true
    rationale: "Prose readability is a qualitative judgment; verified by direct read of deploy/README.md and affected .planning/ files during execution, but a human should confirm the final published prose reads naturally before 04-06 pushes it publicly"
  - id: D7
    description: "The rewrite touched documentation prose and log captures only — no executable code was altered — proven by the 9-harness test suite still passing"
    verification:
      - kind: unit
        ref: "server/test_dither.py, server/test_enrich.py, server/test_illustrations.py, server/test_pipeline_e2e.py, server/test_plane_detection.py, server/test_poll_loop.py, server/test_render.py, server/test_runway_config.py, stub-server/test_poll_cycle.py (all under server/.venv/bin/python3)"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-08-26
status: complete
---

# Phase 4 Plan 01: Pre-Publish Secrets & History Scrub Summary

**Repo-root `.gitignore` plus a git-filter-repo history rewrite that removes the VPS IP/hostname, home Wi-Fi SSID/BSSID/device MAC, and home street address from every commit reachable from any ref, verified against a derived literals file and backed by a bundle outside the repo tree.**

## Performance

- **Duration:** ~40 min this continuation dispatch (Task 2 decision recording + Task 3 execution); Task 1 and the pre-work task were completed in an earlier dispatch
- **Started:** 2026-08-26T18:26:00Z (approx, this dispatch)
- **Completed:** 2026-08-26T19:07:00Z
- **Tasks:** 3 of 3 (pre-work, Task 1, Task 2, Task 3 — 4 total units of work across two dispatches)
- **Files modified:** 1 new tracked file this dispatch (`SCRUB-RECORD.md`); the history rewrite itself touched the content of ~13-100 historical commits across 8+ tracked files, without changing which files exist at HEAD

## Accomplishments

- Repo-root `.gitignore` committed (prior dispatch, Task 1) — D-06 satisfied, nested worktree removed, tree cleaned for a safe `git reset --hard`
- Developer decided the full scrub scope (Categories A+B+C) via `AskUserQuestion`; `.git/inkframe-scrub-expressions.txt` built accordingly (Task 2)
- `git-filter-repo` installed, history rewritten in a scratch clone with both `--replace-text` and `--replace-message`, re-homed onto the real repo's `main`, pre-rewrite objects purged locally (Task 3)
- Zero occurrences of any approved literal remain in any commit diff across any ref, or in the working tree — proven by a grep that reads only from the untracked derived literals file
- A verified `git bundle --all` backup exists outside the repo tree as the sole rollback path
- All 9 project test harnesses still pass after the rewrite, confirming only prose/log content changed, not executable code
- `SCRUB-RECORD.md` documents the whole operation by category and count, restating no scrubbed value

## Task Commits

_Note: git history was rewritten during this plan — every pre-scrub commit hash listed here for prior tasks is superseded by a new hash post-rewrite. The hashes below are the current (post-rewrite) hashes._

1. **Pre-work: Resolve pre-rewrite tracked state (F5)** — `b0d7264` (chore) — *pre-rewrite hash `c2deb86` is now stale; content unchanged, hash changed by the Task 3 rewrite*
2. **Task 1: Root `.gitignore`, worktree removal, clean pre-rewrite tree** — `8c89617` (feat) — *pre-rewrite hash `2d34c22` is now stale; content unchanged, hash changed by the Task 3 rewrite*
3. **Task 2: Decide the scrub scope** — no commit (deliberately untracked `.git/inkframe-scrub-expressions.txt` per plan design; decision recorded in this SUMMARY and SCRUB-RECORD.md)
4. **Task 3: Execute and verify the history rewrite** — `353d693` (feat) — adds `SCRUB-RECORD.md`; the rewrite itself is not a single commit but a rewrite of all 154 commits' content in place

**Plan metadata:** (this commit, following SUMMARY.md write)

## Files Created/Modified

- `.gitignore` — repo-root ignore rules (D-06), Task 1
- `.planning/phases/04-ci-cd-documentation-legal-compliance-github-actions-ci-tests/SCRUB-RECORD.md` — audit record of the scrub, Task 3
- `.git/inkframe-scrub-expressions.txt`, `.git/inkframe-scrub-literals.txt` — untracked, never committed; the only place approved literals and their replacements exist as plaintext
- History-wide (not HEAD-only): `deploy/README.md`, `.planning/PROJECT.md`, `.planning/STATE.md`, `.planning/ROADMAP.md`, `hardware/logs/first-light.log`, `hardware/logs/backoff-run.log`, and several `.planning/phases/*` documents — all now read with placeholder tokens in place of the approved sensitive literals, across every historical commit that ever contained them

## Decisions Made

- Developer chose to scrub Categories A+B+C in full (not the D-05-only option), removing the home Wi-Fi SSID/BSSID/device MAC and home street address alongside the locked VPS IP/hostname — see SCRUB-RECORD.md for the full rationale trail
- Replacement tokens follow `deploy/README.md`'s pre-existing angle-bracket convention (`<vps-ip>`, `<public-host>`) rather than sentinel `REDACTED`-style tokens, extended consistently for the new categories (`<wifi-ssid>`, `<wifi-bssid>`, `<device-mac>`, `<street-address>`, `<home-city>`)
- Used both `--replace-text` and `--replace-message` in the filter-repo invocation after discovering one literal only appeared in a commit message body, not in any file content

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `--replace-text` alone missed a literal that only appeared in a commit message**
- **Found during:** Task 3, Step 6 (verify in the scratch clone)
- **Issue:** The first scratch-clone rewrite pass used only `--replace-text`, which rewrites blob (file) content but not commit/tag message text. One approved literal (a Category B item) appeared only in a commit message body describing a hardware flash verification, and survived that first pass — `git log --all -p | grep -a -c -F -f <literals>` returned `1` instead of `0`.
- **Fix:** Deleted the scratch clone, re-cloned fresh from the real repo, and re-ran `git filter-repo` with both `--replace-text <expressions>` and `--replace-message <expressions>` pointed at the same expressions file.
- **Files modified:** none tracked (scratch-clone-only operation); the re-homed history in the real repo now has zero matches
- **Verification:** Re-ran the Step 6 verify command in the corrected scratch clone — `0` matches; re-verified again post-re-home in the real repo — `0` matches
- **Committed in:** n/a (history rewrite, not a discrete commit; documented in `353d693`'s SCRUB-RECORD.md)

**2. [Rule 3 - Blocking] Deleted a stale branch ref that would have defeated the object purge and re-verification**
- **Found during:** Task 3, between Step 7 (re-home) and Step 8 (purge)
- **Issue:** `refs/heads/claude/faience-blanche-mate-434eeb` — the branch the Task 1 worktree removal (F4) had detached from — still existed in the real repo, pointing at the pre-rewrite history. Confirmed it carried zero unique commits beyond `main` (`git log main..claude/faience-blanche-mate-434eeb` = 0) and that it was fully captured in the pre-rewrite backup bundle. Left in place, it would have kept pre-rewrite objects reachable (defeating `git gc --prune`, the same failure mode F4 describes for the worktree pin) and caused the post-rewrite `git log --all -p` re-verification to still show pre-rewrite content via that ref.
- **Fix:** `git branch -D claude/faience-blanche-mate-434eeb` after re-homing `main` (Step 7) and before the reflog expire / gc (Step 8).
- **Files modified:** none (ref deletion only)
- **Verification:** Post-deletion, `git log --all -p | grep -a -c -F -f <literals>` = 0; `git for-each-ref` shows only `main` and an unrelated automation checkpoint tree ref (confirmed to contain none of the scrubbed literals and, being a non-commit ref, never traversed by `git log --all`)
- **Committed in:** n/a (ref deletion, not a file change)

**3. [Verify-script portability note, not a plan defect] The plan's literal `git log --all -p | grep -c -F -f` verify string needs `-a` on this machine**
- **Found during:** Task 3 final verify, and re-confirmed against the plan's exact top-level `<verification>` step 3 wording
- **Issue:** `git log --all -p | grep -c -F -f .git/inkframe-scrub-literals.txt` (exactly as the plan's Task 3 `<verify>` and the plan's own top-level `<verification>` section write it, without `-a`) intermittently printed **nothing** instead of `0` on a fully-scrubbed, verified-clean history. Root cause: this repo's history includes binary diffs (vendored font blobs), and GNU/BSD `grep` treats the whole piped stream as binary once it encounters them, silently suppressing the `-c` count line — it is not evidence of a remaining match.
- **Fix:** None to the repo — confirmed the true result with `grep -a` (treat as text), which reliably printed `0`. Documented as a verify-script portability note in `SCRUB-RECORD.md`, in the same spirit as Task 1's already-known `git check-ignore -q` multi-path issue.
- **Files modified:** none
- **Verification:** `git log --all -p | grep -a -c -F -f .git/inkframe-scrub-literals.txt` => `0`, run in both the scratch clone and the real repo, both before and after the object purge
- **Committed in:** n/a (documented, no code change)

---

**Total deviations:** 3 (1 execution-approach bug fixed before proceeding, 1 blocking-issue ref cleanup, 1 verify-script portability note carried into SCRUB-RECORD.md)
**Impact on plan:** All three were necessary to make the plan's own stated invariant ("zero occurrences in any commit diff of any ref") actually true and actually provable. No scope creep — the approved Category A+B+C literal set was not expanded or reduced.

## Issues Encountered

None beyond the deviations above — no unresolved blockers.

## User Setup Required

None — no external service configuration required. The one manual step left for the developer is unrelated to setup: `SCRUB-RECORD.md` documents the backup bundle's path (`/Users/florian/ink-frame-backups/ink-frame-pre-scrub-20260826T185603Z.bundle`, outside the repo tree) in case a rollback is ever needed before this history is pushed publicly in plan 04-06.

## Next Phase Readiness

- The repository is now safe to push publicly with respect to D-04/D-05: no commit reachable from any ref contains the VPS IP/hostname, home Wi-Fi identifiers, or home street address.
- D-03's clean-history claim was independently re-confirmed during planning (`stub-server/byos_state.json` never committed) and remains true post-rewrite.
- D-06's credential/cruft `.gitignore` discipline is in place and machine-verified.
- Downstream plans (04-02 through 04-06) can proceed; 04-04 in particular should re-run the same derived-literals-file verification pattern established here before its own gate, per this plan's `key_links`.
- The stale worktree-agent branch cleanup (deviation 2) means the repo now has exactly one ref of substance (`main`) plus one unrelated automation checkpoint ref — a simpler starting point for 04-06's public-push plan.

---

*Phase: 04-ci-cd-documentation-legal-compliance-github-actions-ci-tests*
*Completed: 2026-08-26*

## Self-Check: PASSED

- FOUND: `.gitignore`
- FOUND: `.planning/phases/04-ci-cd-documentation-legal-compliance-github-actions-ci-tests/SCRUB-RECORD.md`
- FOUND: `.planning/phases/04-ci-cd-documentation-legal-compliance-github-actions-ci-tests/04-01-SUMMARY.md`
- FOUND: commit `b0d7264` (pre-work, post-rewrite hash)
- FOUND: commit `8c89617` (Task 1, post-rewrite hash)
- FOUND: commit `353d693` (Task 3, SCRUB-RECORD.md)
- Confirmed: `04-01-SUMMARY.md` and `SCRUB-RECORD.md` contain zero matches against `.git/inkframe-scrub-literals.txt`
