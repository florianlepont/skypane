---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 14
subsystem: infra
tags: [github-actions, ci, concurrency, playwright, hash-locking, firmware]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    plan: "01"
    provides: ruff target-version and the CI structure this plan edits
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    plan: "12"
    provides: server/requirements-dev.txt as a hash-locked superset installable with --require-hashes
provides:
  - .github/workflows/ci.yml running Python 3.14, a single hash-enforced dependency install, separate
    test/deploy concurrency groups, a stale-commit guard on deploy, and a cached Playwright headless shell
  - .github/workflows/firmware.yml running firmware/tests/run_host_tests.sh in its own container-free,
    needs-free job
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Job-level concurrency groups instead of one workflow-level group, so a deploy paused on reviewer
       approval never blocks the next push's tests"
    - "Stale-commit guard (git ls-remote origin refs/heads/main vs github.sha) as the replacement for
       cancel-in-progress: true on the deploy job, so a superseded queued deploy is skipped rather than
       killing a running rsync"
    - "actions/cache keyed on the installed tool's own version (read via importlib.metadata at run time),
       not a lockfile hash, when only that one tool's cache-buster matters"

key-files:
  created: []
  modified:
    - .github/workflows/ci.yml
    - .github/workflows/firmware.yml

key-decisions:
  - "firmware.yml's host-test execution moved (not duplicated) from the build job (added by Phase 34's
     merge into this branch) into a new host-tests job, so the check runs exactly once, independently of
     the container-using build steps"
  - "Excluded TST-04 from this plan's requirements.mark-complete call even though it is already checked in
     REQUIREMENTS.md: TST-04 also spans 32-15 (not yet executed), so per this plan's own success criteria
     ('do not mark a requirement complete unless every plan it spans is done') it should not be reconfirmed
     complete from here"

requirements-completed: [TST-05, TST-06, TST-07, TST-08]

# Metrics
duration: ~10min
completed: 2026-09-23
---

# Phase 32 Plan 14: CI hardening — Python 3.14, hash-locked installs, split concurrency, Playwright cache, firmware host tests Summary

**`ci.yml` moves to Python 3.14 with a single `--require-hashes` install of `server/requirements-dev.txt`, splits the workflow-level concurrency group into separate `test`/`deploy` job-level groups (deploy never cancelled mid-rsync, guarded against a stale reviewer approval by a `git ls-remote` check), and caches the Playwright headless shell keyed on its installed version; `firmware.yml` gets a dedicated `host-tests` job that runs `run_host_tests.sh` with no ESP-IDF container and no `needs:`.**

## Performance

- **Duration:** ~10 min (approximate — not captured at spawn)
- **Started:** ~2026-09-23T17:32:20Z (previous plan's completion timestamp)
- **Completed:** 2026-09-23T17:42:10Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `ci.yml`'s `test` job: `python-version: '3.14'` (matches production's distro `python3`) with a
  `python3 --version` log line; dependency install collapsed to one `pip install --require-hashes -r
  server/requirements-dev.txt` (the hash-locked superset from plan 32-12).
- `ci.yml`'s workflow-level `concurrency:` block removed; `test` gets its own `test-${{ github.ref }}` group
  (PR-only cancellation, as before), `deploy` keeps `production-deploy` but with `cancel-in-progress: false`
  — an in-flight rsync is never killed. A new `Skip if this commit is no longer the tip of main` step (id
  `fresh`) compares `github.sha` against `git ls-remote origin refs/heads/main` and gates the SSH-key,
  known_hosts and Deploy steps on `steps.fresh.outputs.stale != 'true'`, replacing the old
  `cancel-in-progress: true` as the stale-deploy defence.
- `ci.yml` Playwright: installed-version read into a step output via `importlib.metadata`, an
  `actions/cache@55cc8345863c7cc4c66a329aec7e433d2d1c52a9 # v6.1.0` step keyed on
  `playwright-${{ runner.os }}-${{ steps.pw.outputs.version }}-headless-shell` over
  `~/.cache/ms-playwright`, and the browser install changed from `install --with-deps chromium` to `install
  --with-deps --only-shell chromium`.
- `firmware.yml`: new `host-tests` job (`runs-on: ubuntu-latest`, `timeout-minutes: 5`, no `needs:`, no
  container) checks out the repo and runs `./firmware/tests/run_host_tests.sh` (plus a `cc --version` log
  line) independently of the `build` job. `run_host_tests.sh` passes locally (8 suites, exit 0). Header
  comments on both files rewritten to explain current behaviour without plan-number history.

## Task Commits

Each task was committed atomically:

1. **Task 1: ci.yml — Python 3.14, hash-locked install, split concurrency, stale-deploy guard, Playwright shell + cache** - `ce66a96` (ci)
2. **Task 2: firmware.yml host-tests job** - `c5964fb` (ci)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `.github/workflows/ci.yml` - Python 3.14; single hash-enforced install; job-level `test`/`deploy`
  concurrency; stale-commit deploy guard; Playwright headless-shell install + version-keyed cache
- `.github/workflows/firmware.yml` - new `host-tests` job (hardware-free, no container); `build` job
  unchanged apart from losing the now-relocated host-test step

## Decisions Made
- **Adaptation to Phase 34's prior merge (context provided by the orchestrator, not a plan deviation in the
  Rule 1-4 sense):** this plan was written before Phase 34 (already merged into this branch) added
  `run_host_tests.sh`, `check_production_config.sh` (static + built) and `check_log_contract.sh` to
  `firmware.yml`'s single `build` job. Task 2's intent — host tests running in CI without needing the
  ESP-IDF container — was therefore already partially satisfied, just not as a separate job. Rather than
  duplicate the `run_host_tests.sh` invocation (which the orchestrator's guidance explicitly warned against),
  the existing "Run firmware host tests" step was **relocated** (not copied) from `build` into the new
  `host-tests` job, so the check still runs exactly once, in a job with no `needs:` and no container as this
  plan specifies. Phase 34's other two checks (`check_production_config.sh`, `check_log_contract.sh`) were
  left untouched in `build`, exactly where Phase 34 placed them — this plan's scope never covered them.
  Verified locally after the edit: `run_host_tests.sh` (8/8 suites), `check_production_config.sh static`,
  and `check_log_contract.sh` all still exit 0.
- The plan's Task 1 acceptance criterion `grep -c "environment:" .github/workflows/ci.yml` prints 1 was
  already false against the pre-existing file (`git show HEAD:.github/workflows/ci.yml | grep -c
  "environment:"` = 2, because of a `` `environment:` `` backticked mention inside a comment one line above
  the real key) — a stale/inaccurate criterion in the plan itself, not something this plan's edits
  introduced. Reworded that comment to avoid the literal substring (meaning unchanged) so the criterion now
  holds; documented here rather than silently ignored.
- `actions/cache` pinned to `55cc8345863c7cc4c66a329aec7e433d2d1c52a9` (tag `v6.1.0`, confirmed via `git
  ls-remote --tags https://github.com/actions/cache` as the newest SemVer tag — `api.github.com` was not
  reachable from this session, so the `gh api .../releases/latest` route the planner findings suggested was
  replaced with the equivalent `git ls-remote` lookup; same outcome, no API token needed).
- Followed the orchestrator's explicit `TST-04` guidance: excluded it from this plan's
  `requirements.mark-complete` call because it also spans not-yet-executed 32-15, even though it was already
  checked `[x]` in `REQUIREMENTS.md` before this plan ran (apparently marked complete by 32-01's execution
  without accounting for 32-14/32-15 also being in its span). Left that pre-existing checkbox as-is — fixing
  it is out of this plan's scope and not something this executor introduced.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Stale acceptance criterion] `environment:` grep count comment collision**
- **Found during:** Task 1, running the acceptance-criteria checks after the first draft
- **Issue:** The plan's acceptance criterion expects `grep -c "environment:" .github/workflows/ci.yml` to
  print 1, but a pre-existing comment (`` # The `environment:` declaration below... ``, present in the file
  before this plan touched it) already made the true count 2.
- **Fix:** Reworded the comment to describe the same gate without repeating the literal `environment:`
  substring.
- **Files modified:** `.github/workflows/ci.yml`
- **Verification:** `grep -c "environment:" .github/workflows/ci.yml` now prints 1; the YAML behaviour
  (the `environment: { name: production }` key) is unchanged.
- **Committed in:** `ce66a96` (Task 1 commit)

**2. [Rule 3-adjacent — adaptation, not a bug] Relocated Task 2's host-test step instead of duplicating it**
- See "Decisions Made" above for full rationale. Not a Rule 1-4 fix in the strict sense (nothing was
  broken), but recorded here because it changes Task 2's literal instructions ("add a job `host-tests`")
  into "add a job `host-tests` and move the step Phase 34 already added into it" to avoid running the same
  check twice per CI run, per the orchestrator's explicit instruction not to duplicate already-satisfied
  plan intent.
- **Committed in:** `c5964fb` (Task 2 commit)

---

**Total deviations:** 2 (1 auto-fixed stale criterion, 1 adaptation to a prior merge per orchestrator
guidance). **Impact on plan:** Neither weakens or removes any existing check — Phase 34's
`check_production_config.sh` and `check_log_contract.sh` steps are untouched, and `run_host_tests.sh` still
runs on every relevant push, just once and in its own job.

## Issues Encountered
- `api.github.com` (used by the planner's suggested `gh api repos/actions/cache/releases/latest` lookup) was
  not reachable from this session ("GitHub access to this repository is not enabled for this session").
  `git ls-remote --tags https://github.com/actions/cache` (plain git protocol) worked and gave an equivalent,
  verifiable answer (newest tag `v6.1.0`, commit `55cc8345863c7cc4c66a329aec7e433d2d1c52a9`).
- Could not run GitHub Actions itself in this environment — both workflow files were validated locally
  (`python3 -c "import yaml; ..."` parse + every plan-specified `grep`/`grep -c` acceptance criterion, plus
  actually executing `firmware/tests/run_host_tests.sh`, `check_production_config.sh static`, and
  `check_log_contract.sh` on this machine). **Needs the first real CI run to confirm:** the `python3
  --version` log line reads 3.14.x on the runner; the hash-locked install actually succeeds against PyPI
  from a clean GitHub-hosted runner; the Playwright cache step restores/misses correctly and a second run
  shows a cache hit with no Chromium download; the two-push deploy-concurrency behaviour (running deploy
  never shown as cancelled; a superseded pending deploy is either replaced while pending or skipped via the
  stale-commit `::notice::`); and that `host-tests` and `build` report as two separate job results on a
  firmware-touching push.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- TST-05, TST-06, TST-07 and TST-08 (the CI-facing audit findings this plan owns) are code-complete and
  locally verified; TST-08's lock-file half was already complete from 32-12, so marking it complete here
  closes the requirement now that both spanning plans (32-12, 32-14) are done.
- No blockers for 32-15 (subprocess coverage / `fail_under` floor), which is independent of this plan's
  workflow edits.
- First CI run on this branch (or the next push to `main`) should be watched for the items listed under
  "Issues Encountered" above — none are expected to fail based on local verification, but none of them can
  be proven without GitHub Actions actually running.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

Both modified files confirmed present on disk (`.github/workflows/ci.yml`, `.github/workflows/firmware.yml`);
both task commit hashes (`ce66a96`, `c5964fb`) confirmed present in `git log --oneline --all`.
