---
phase: 70-private-repository-and-ci
plan: 06
subsystem: ci-runner
tags: [github-actions, self-hosted-runner, lima, launchd]
requires: [70-01]
provides:
  - "runs-on from CI_RUNS_ON with a GitHub-hosted default"
  - "Mac runner kit: JIT loop, Lima VM definition, launchd template, runbook"
affects: [70-07]
key-files:
  created:
    - deploy/tests/test_ci_runner.py
    - deploy/runner/skypane-runner-loop.sh
    - deploy/runner/com.skypane.ci-runner.plist.example
    - deploy/runner/lima-skypane-ci.yaml
    - deploy/runner/README.md
    - deploy/tests/test_runner_loop.py
  modified:
    - .github/workflows/ci.yml
    - .github/workflows/firmware.yml
    - scripts/lock-deps.sh
key-decisions:
  - "No path-based test skipping was added; docs-only skip kept, savings come from the runner"
  - "One Lima VM per runner slot (skypane-ci-N) so a work-folder wipe never touches a sibling job"
requirements-completed: [PRV-02]
completed: 2026-11-25
---

# Phase 70 Plan 06: Runner kit Summary

CI is runner-agnostic through the repository variable `CI_RUNS_ON` (unset means `ubuntu-latest`), with fork-PR job guards, hosted-only sudo/apt/setup-python steps, and a tested Mac launcher kit (single-use JIT runners in Lima VMs). No test or gate was skipped or weakened.

## Branch note
Plan 70-01 (open PR 589) removes the deploy job from ci.yml. I merged `origin/phase-70-01-manual-deploy-pr` into this branch (merge commit 9342b8a) so the ci.yml edits apply on top of it. When 70-01 lands on main, this branch's diff reduces to the two task commits.

## Commits
- 9342b8a: merge of origin/phase-70-01-manual-deploy-pr
- a5a5389: ci.yml and firmware.yml runs-on from CI_RUNS_ON, guards, lock-deps.sh comment, test_ci_runner.py
- d5f6843: runner kit (loop, plist example, Lima yaml, README) and test_runner_loop.py

## Verification (repo venv python, run from the worktree)
- test_ci_runner.py, test_ci_secrets.py, test_install_backup_key.py, test_firmware_partition_bound.py: 28 passed
- test_runner_loop.py: 7 passed
- deploy/tests plus stub-server/test_phase47_freeze.py: 375 passed, 1 skipped (openssl cannot backdate a certificate, pre-existing)
- ruff clean; check_comment_history clean; check_function_size (max 80) clean; ci_shards check ok (535 files, new tests are in shards)
- `bash -n` on the loop script ok

## Not run
- No workflow run (hosted or self-hosted), so the `runner.environment` conditions and the self-hosted steps are verified by text-scan tests only.
- shellcheck is not installed here; CI runs it over `deploy/*.sh` (the loop script was written for it, bash 3.2 compatible, but is unchecked).
- Lima, the VM provision script, the Ubuntu 26.04 image URLs and package names (t64 variants), launchd, the macOS Keychain and a real GitHub JIT call were not exercised; the loop is tested against shims. The README tells the owner to compare the package list with `playwright install-deps --dry-run chromium`.
- The aarch64 wheel claim in the lock-deps.sh comment comes from the plan's research; I did not re-run the `pip download` check.
- Full scripts/run-all-tests.sh was not run.

## Deviations from Plan
- The server venv does not exist inside the worktree, so I used `/home/user/skypane/server/.venv/bin/python` (read only use) from the worktree directory.
- The loop runs the runner and the work-folder wipe through `sudo -n -u runner -H` inside the VM, because `limactl shell` otherwise runs as the Lima default user, not the unprivileged `runner` user. The wipe uses `find ... -mindepth 1 -delete` rather than `rm -rf`.
- One Lima VM per runner slot (not one shared VM), because the loop wipes `_work` and a shared VM would let one runner's wipe hit another's running job.
- D-07 deviation is as stated in the plan: no `changes` job, no path-based test skipping (asserted by test_ci_runner.py).

## Known Stubs
None.

## Threat Flags
None beyond the plan's threat model. Note for the owner: the runner user is in the VM's docker group (root-equivalent inside the VM only).
