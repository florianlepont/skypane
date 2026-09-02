---
phase: quick-260902-i1p
plan: 01
subsystem: testing
tags: [python, pytest-style-harness, platform-detection, panel.bin, digest, poll_loop]

requires: []
provides:
  - "server/test_poll_loop.py's _digest_verdict(digest, expected) helper - platform-gated pinned-digest comparison (Linux-strict, non-Linux-informational)"
  - "server/test_poll_loop.py check 30 - hermetic both-branch proof of _digest_verdict()'s platform split"
affects: [server-testing, ci]

tech-stack:
  added: []
  patterns:
    - "Platform-gated test assertions: platform.system() resolved at call time inside the helper body (never hoisted to a module constant), so a monkeypatch of platform.system genuinely exercises the real branch"

key-files:
  created: []
  modified:
    - server/test_poll_loop.py

key-decisions:
  - "Ordered check 30's sub-assertions (b) [forced Linux] before (a) [forced Darwin] so the live inverted-condition demonstration reports FAIL on the security-relevant sub-assertion the threat model names, rather than an earlier, less specific one that would trip first under early-return semantics"

patterns-established: []

requirements-completed: [QUICK-260902-i1p]

coverage:
  - id: D1
    description: "server/test_poll_loop.py's pinned panel.bin digest check is platform-gated: Linux stays a hard FAIL on mismatch, non-Linux degrades to a NOTE line plus a plain PASS"
    requirement: "QUICK-260902-i1p"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py check 10 (_default_config_byte_identity) - local run: poll-loop: 44/44 checks pass, exactly one NOTE line, zero FAIL lines"
        status: pass
    human_judgment: false
  - id: D2
    description: "New check 30 proves both branches of _digest_verdict() by forcing platform.system() against the real helper (not a copy), and the live invert/observe-FAIL/revert demonstration was performed and recorded"
    requirement: "QUICK-260902-i1p"
    verification:
      - kind: unit
        ref: "server/test_poll_loop.py check 30 (_digest_verdict_is_linux_strict_and_non_linux_informational) - passes at 44/44; inverted-condition demonstration observed FAIL on sub-assertion (b) verbatim below, then reverted and re-confirmed green"
        status: pass
    human_judgment: false

duration: ~10min
completed: 2026-09-02
status: complete
---

# Quick Task 260902-i1p: Platform-gate the pinned panel.bin digest check Summary

**`server/test_poll_loop.py`'s pinned `panel.bin` digest check is now platform-gated via a shared `_digest_verdict()` helper - Linux stays a hard FAIL on mismatch, macOS degrades to an informational `NOTE ` line plus a plain PASS, proven both-branch by a new check 30.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-09-02
- **Tasks:** 2/2 completed
- **Files modified:** 1 (`server/test_poll_loop.py`)

## Accomplishments

- Added `import platform` and a module-level `_digest_verdict(digest, expected)` helper (Linux-authoritative/non-Linux-informational split, `platform.system()` resolved at call time - never hoisted to a constant)
- Rewired `_default_config_byte_identity()` (check 10) to delegate to `_digest_verdict()` instead of comparing inline
- Added a dated 2026-09-02 entry to the `_DEFAULT_CONFIG_DIGEST` provenance comment block, explicitly stating this is NOT a re-pin and restating the standing re-pin-only-from-CI rule
- Added check 30, a hermetic (no `run_once()`, no temp dir, no render) proof that `_digest_verdict()`'s two branches are both genuinely preserved, by monkeypatching `platform.system` at call time
- Bumped `EXPECTED_CHECK_COUNT` 43 -> 44
- Performed the mandatory live "invert the condition, observe genuine FAIL, revert" demonstration before staging Task 2's commit

## Task Commits

Both tasks touch only `server/test_poll_loop.py`. See "Deviations from Plan" below for why the commit history looks unusual - a concurrent, unrelated agent process was writing to this same (non-isolated) working tree during execution.

1. **Task 1: Platform-gate the digest comparison behind `_digest_verdict()`, record why in the dated comment block** - content landed inside commit `b9be828` (see deviation below); the `server/test_poll_loop.py` portion of that commit is verified byte-for-byte identical to Task 1's intended diff (`git show b9be828 -- server/test_poll_loop.py`).
2. **Task 2: Add check 30 proving both branches, bump `EXPECTED_CHECK_COUNT` to 44, demonstrate the strict branch's teeth** - `eb67aaa` (test)

## Files Created/Modified
- `server/test_poll_loop.py` - `import platform`; new `_digest_verdict(digest, expected)` helper; `_default_config_byte_identity()` (check 10) rewired to delegate to it; dated 2026-09-02 provenance comment entry; new check 30 (`_digest_verdict_is_linux_strict_and_non_linux_informational`); `EXPECTED_CHECK_COUNT` 43 -> 44

## Decisions Made

- **Sub-assertion ordering in check 30:** the plan's `<action>` text lists sub-assertions in order (a) softened-branch-is-real, (b) strict-branch-preserved, (c) not-degenerate. Because `check()` functions in this file use early-return-on-first-failure (the established convention throughout - e.g. check 17's field loop), a literal top-to-bottom (a)/(b)/(c) ordering means that under the plan's specified inversion (`platform.system() != "Linux"`), sub-assertion (a) trips FIRST (forcing "Darwin" now hits the newly-strict branch), never reaching (b). The plan's own text and the threat model (T-quick-01) both specifically name the forced-"Linux" sub-assertion as "the exact assertion an inversion breaks" and require observing FAIL there. Reordered so (b) [forced Linux] executes before (a) [forced Darwin] - confirmed this reproduces the plan's specified observation exactly (see verbatim failure output below).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Task 1's commit landed inside a concurrent, unrelated agent's commit due to a shared-worktree race**
- **Found during:** Attempting to commit Task 1 (`git commit` immediately after `git add server/test_poll_loop.py` returned "nothing to commit")
- **Issue:** This dispatch was explicitly instructed to operate directly on the current working tree/branch (no nested worktree isolation). A concurrent GSD quick-task agent (working on unrelated task `260902-i4f`) was committing to the exact same physical working directory at the same time. Between my `git add server/test_poll_loop.py` and my `git commit` call, that concurrent agent's own commit (`b9be828`, "docs(quick-260902-i4f): complete update-klj-klasjet-confidence-comment-in plan") swept up my already-staged `server/test_poll_loop.py` changes alongside its own unrelated `.planning/STATE.md` and `260902-i4f-SUMMARY.md` files.
- **Fix:** No code change needed - the `server/test_poll_loop.py` diff inside `b9be828` was verified byte-for-byte identical to Task 1's intended change (`git show b9be828 -- server/test_poll_loop.py`, confirmed via direct inspection: exactly the `import platform` line, the dated comment entry, and the `_digest_verdict()` helper + call-site rewire, nothing else). Rather than attempting a history rewrite (amending or rebasing another agent's commit is explicitly prohibited by this workflow's git safety rules), Task 1's work is accepted as correctly landed, and documented here as bundled into an unrelated commit for audit-trail transparency. Task 2 proceeded normally with its own clean, atomic commit (`eb67aaa`).
- **Files modified:** `server/test_poll_loop.py` (content correct; commit attribution shared with an unrelated task)
- **Verification:** `git show b9be828 -- server/test_poll_loop.py` diff matches Task 1's intended change exactly; `git diff --stat b9be828~1 eb67aaa -- server/test_poll_loop.py` (my two logical task changes combined) touches only `server/test_poll_loop.py`, confirming no scope leak from my own work.
- **Committed in:** `b9be828` (shared with unrelated commit, not amendable per this workflow's git safety rules)

---

**Total deviations:** 1 auto-fixed (1 blocking, environmental)
**Impact on plan:** No code or scope deviation - the file content is exactly as planned. The only deviation is a commit-attribution artifact caused by a shared, non-isolated working tree with a concurrent agent, outside this task's control. The "exactly one file modified across both commits" constraint holds for this task's own content changes.

## Issues Encountered

**Inverted-condition demonstration (Task 2, step 3) - performed and verified, as required.**

Before staging Task 2's commit, `_digest_verdict()`'s condition was temporarily changed from `if platform.system() == "Linux":` to `if platform.system() != "Linux":` and the harness was run:

```
$ cd server && .venv/bin/python3 test_poll_loop.py
...
FAIL a default config against the FLIGHT1 fixture reproduces the pinned pre-06-10 panel.bin digest - panel.bin digest 2c511df10225d28137f3381e58cf6e7e05edaab76b2282c5e491e33d7270edd8 != pinned 46c18ea48d711bf62520570367cd019e2144073019dabe1d4282766d3ae4be51
FAIL the pinned-digest verdict is Linux-strict and non-Linux-informational - both branches proven by forcing platform.system() - (b) forced Linux mismatch returned ok=True, expected False
poll-loop: 42/44 checks pass
```

Check 30 genuinely failed on sub-assertion (b) exactly as the plan specifies, with the precise message `(b) forced Linux mismatch returned ok=True, expected False`. (Check 10 also failed under this inversion - an unavoidable side effect of running this exact demonstration on this real macOS machine, where the inversion makes the *local, genuine* digest mismatch strict too. This does not undermine check 30's proof: check 30 is hermetic and uses its own deliberately-different `sample`/`bogus` stand-ins, independent of the real panel.bin digest.)

The condition was then reverted to `if platform.system() == "Linux":` and the harness re-run, confirming:

```
poll-loop: 44/44 checks pass
```

before Task 2's commit was staged. Nothing inverted reached a commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `server/test_poll_loop.py` now reports `poll-loop: 44/44 checks pass` on this macOS machine (was `42/43`), with exactly one `NOTE ` line and zero `FAIL ` lines.
- `_DEFAULT_CONFIG_DIGEST`'s pinned value confirmed byte-unchanged: `46c18ea48d711bf62520570367cd019e2144073019dabe1d4282766d3ae4be51`.
- Linux/CI behavior is provably byte-unchanged: same mismatch reason string, same hard failure - proven in-process by check 30's forced-`"Linux"` sub-assertion, not by inspection.
- `scripts/run-all-tests.sh` should now report a fully green suite locally on macOS for the first time since Phase 8 (optional sanity check, not re-run as part of this quick task since it was explicitly out of scope to modify).

---
*Task: quick-260902-i1p*
*Completed: 2026-09-02*

## Self-Check: PASSED

- FOUND: `server/test_poll_loop.py`
- FOUND: `.planning/quick/260902-i1p-make-test-poll-loop-py-s-pinned-panel-bi/260902-i1p-SUMMARY.md`
- FOUND: commit `b9be828` (Task 1 content, shared with unrelated concurrent commit - see Deviations)
- FOUND: commit `eb67aaa` (Task 2)
