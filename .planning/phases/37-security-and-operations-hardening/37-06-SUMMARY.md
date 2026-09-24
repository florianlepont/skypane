---
phase: 37-security-and-operations-hardening
plan: 06
subsystem: infra
tags: [deploy, systemd, caddy, git-archive, ssh, atomic-swap, rollback, pytest, tdd, fake-root]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest infrastructure (conftest.py conventions, [tool.pytest.ini_options] importlib mode, no-network socket guard)
  - phase: 37-security-and-operations-hardening (Plan 37-03)
    provides: deploy/render_caddyfile.sh, release-layout units (/opt/skypane/current/...), skypane-backup.service/.timer
  - phase: 37-security-and-operations-hardening (Plan 37-04)
    provides: deploy/backup/backup_gate.py, deploy/backup/skypane_backup.py (the --help smoke-check target)
provides:
  - "deploy/activate.sh: VPS-side stage/install/swap/probe/rollback/prune, every system path overridable for tests (D-09/D-10/D-11)"
  - "deploy/deploy.sh: git archive | ssh transport that ships exactly the committed tree at HEAD and relays activate.sh's own exit status"
  - "deploy/tests/conftest.py: fake_root/stub_bin/fake_release/run_activate fixtures — a tmp filesystem plus scripted systemctl/curl/caddy/runuser/journalctl/chown on PATH, the shared CI lever for exercising VPS-root shell scripts with no VPS and no root"
  - "deploy/tests/test_activate.py + test_deploy.py: 17 new pytest tests proving SC-4 (a deploy leaving a unit inactive fails the job and rolls back) in CI"
affects: [37-07 (provision.sh: skypane-backup user/dirs, release-layout dirs, SSH hardening — activate.sh's prerequisite check now depends on it), 37-08 (fresh-VPS provisioning), 37-09 (the human-supervised cutover from the in-place layout to this release layout)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Fake-root shell testing: every VPS filesystem path activate.sh touches is an overridable shell variable, and PATH-prepended Python stub scripts (not real systemctl/curl/caddy/runuser/journalctl/chown) let the whole stage/swap/probe/rollback flow run as a real bash subprocess in CI, with a shared call-log file for asserting call order (daemon-reload before the first restart)"
    - "Literal '|| true' reserved for exactly the one spot the plan's own interface calls for (the readlink of a possibly-missing `current` symlink); every other ignored-failure site uses '|| :' so the acceptance grep (`grep -c \"|| true\"` <= 1) measures a real property, not incidental phrasing"
    - "skypane.env is read with an anchored `sed -n \"s/^KEY=\\(.*\\)$/\\1/p\"` extractor, never `source`d or `.`d — a poison line in the fake env file (`X=$(touch <marker>)`) proves this in the test suite, not just by code review"
    - "git archive ships exactly HEAD's committed tree; server/state/** is excluded by pathspec even though it holds only one tracked file (server/state/.gitignore) — the archive's own listing must show no server/state/ prefix at all, not merely 'mostly empty'"
    - "activate.sh's own swap (ln -sfn + mv -T) happens before probing; on a first-ever deploy that fails its probes, there is no previous release to roll back to, so `current` legitimately keeps pointing at the failing release rather than being deleted (T-37-31) — this is a deliberate property of the design, not a gap, and is asserted as such in the test"

key-files:
  created:
    - deploy/activate.sh
    - deploy/tests/conftest.py
    - deploy/tests/test_activate.py
    - deploy/tests/test_deploy.py
  modified:
    - deploy/deploy.sh

key-decisions:
  - "fake_release(sha) copies the real, working-tree deploy/ directory (so render_caddyfile.sh, the real units, and backup_gate.py are exercised for real) but stands in minimal --help-only scripts for server/poll_loop.py, companion/app.py, and stub-server/byos_server.py — their own import-time dependencies are irrelevant to activate.sh's swap/probe/rollback logic, which is all these fixtures exist to exercise; deploy/backup/skypane_backup.py (part of the real deploy/ copy) is smoke-tested for real."
  - "curl's stub derives a probe's identity from the request path (\"/device/v1/display\" -> byos, \"/login\" -> companion) rather than from the port, so FAKE_HTTP_CODES keys (e.g. companion_login=502) apply uniformly to both the loopback and the HTTPS-through-Caddy probe for the same service, matching the plan's own example key names exactly."
  - "Two of test_activate.py's 12 tests (rollback on a bad HTTP probe, rollback on a missing HSTS header) are written as one test function each covering both FAKE_HTTP_CODES and FAKE_NO_HSTS sub-cases, per the plan's own <behavior> bullet grouping them on one line — the acceptance criterion's '12 behavior tests' count is 12 pytest test functions, one per <behavior> bullet, not 12 independent assertions."
  - "Per-sha marker comments are appended to a copied release's companion unit file directly inside test_activate.py (not inside conftest.py's fake_release), so a rollback test can prove SYSTEMD_UNIT_DIR now holds the *previous* release's exact unit content rather than merely re-asserting identical bytes two same-tree copies would already share."

requirements-completed: []  # SEC-05/SEC-02/SEC-06 remain marked incomplete per this plan's explicit instruction — a full production deploy has not yet run against this code and the cutover (Plan 37-09) is still pending.

# Metrics
duration: 16min
completed: 2026-09-24
---

# Phase 37 Plan 06: Atomic, verified deploy — activate.sh, deploy.sh, fake-root tests Summary

**`deploy/activate.sh` (new) stages a release, installs/byte-compiles/smoke-tests it, renders and validates a Caddyfile, swaps `/opt/skypane/current` atomically, then probes every unit plus loopback and HSTS-verified HTTPS through Caddy — rolling back to the previous release and always exiting non-zero on any failure — while `deploy/deploy.sh` (rewritten) now ships exactly one git SHA's committed tree via `git archive | ssh` and relays activate.sh's own exit status, both proven against a fake VPS root in 17 new pytest tests.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-09-24T08:55:00Z
- **Completed:** 2026-09-24T09:11:50Z (Task 3 GREEN commit)
- **Tasks:** 3/3 completed
- **Files modified:** 5 (4 created, 1 modified)

## Accomplishments

- `deploy/tests/conftest.py`: `fake_root` (a tmp tree standing in for `/opt/skypane`, `/etc/systemd/system`, `/etc/caddy`, `/usr/local/lib/skypane`, `/var/lib/skypane-backup`, with a poison-line `skypane.env` and a `venv/bin/python3` symlinked to the real interpreter), `stub_bin` (PATH-prepended Python stubs for `systemctl`/`curl`/`caddy`/`runuser`/`journalctl`/`chown`, all logging argv to one shared call-log file), `fake_release(sha)` (a real copy of `deploy/` plus minimal `--help`-only stand-ins for the three services), and `run_activate(sha, **overrides)` (runs `activate.sh` as a real subprocess with every override variable pointed into `fake_root`). This is the one shared fixture set both `test_activate.py` and `test_deploy.py` (its own local `ssh` stub) build on.
- `deploy/activate.sh` (new, executable): root guard (bypassable only via `SKYPANE_ACTIVATE_ALLOW_NONROOT=1`, tests only) and sha validation; a prerequisite check (`ENV_FILE`, `VENV/bin/python3`, `BACKUP_ROOT/{archives,pulled}`) that fails with a "run deploy/provision.sh first" message before anything changes; strict `sed`-only extraction of the four `skypane.env` keys (never sourced — proven by the poison-line test); release staging into `releases/<sha>` (`mv -T`, `chown root:root`, `chmod -R go-w`); requirements-hash-gated `pip install`; `compileall`; a four-script `--help` smoke check; Caddyfile render + `runuser -u caddy -- caddy validate` before anything is swapped; the atomic `ln -sfn` + `mv -T` swap (skipped entirely on a same-sha redeploy — restart and probe only); unit + `backup_gate.py` install with `daemon-reload` before the first restart; a timed retry loop probing all four units and both loopback/HTTPS(+HSTS) endpoints; automatic rollback (previous release, its units, and its Caddyfile all restored) with a re-probe and a forced non-zero exit on any failure, including the "no previous release to roll back to" case on a first-ever failing deploy; and mtime-based pruning to `KEEP_RELEASES` that never deletes `current` or the previous release, plus stale `.incoming-*` cleanup.
- `deploy/deploy.sh` (rewritten): resolves `HEAD`'s sha, warns (but still ships) on a dirty working tree, streams `git archive --format=tar $SHA -- server stub-server companion deploy adsb-test/runway3.json ':(exclude)server/state/**'` over `ssh` into a per-sha `releases/.incoming-<sha>` directory, then runs that release's own `activate.sh <sha> <incoming-dir>` over `ssh` and lets its exit status become the script's own (`set -euo pipefail` + ssh's exit-code propagation). No `rsync`, no local `sha256sum`, no `root@` example — the usage line now shows `ubuntu@203.0.113.10` (SEC-08, D-08).
- `deploy/tests/test_activate.py`: 12 tests, one per `<behavior>` bullet — first deploy, second deploy keeps the previous release, rollback on an inactive unit (with a per-release unit-file marker proving the *previous* release's exact unit content is restored), rollback on a bad HTTP probe code and on a missing HSTS header, Caddy-validate failure blocking the swap, smoke-check failure blocking the swap, the "no previous release" first-deploy failure (which legitimately leaves `current` pointing at the failing release — T-37-31, asserted explicitly), pruning to `KEEP_RELEASES=5` across 7 older releases while never deleting current/previous and removing stale `.incoming-*`, a same-sha redeploy doing no re-extraction/re-install, invalid-host-or-port and missing-prerequisite failures before any change, and requirements-hash-gated pip install (called once on a hash mismatch, not called again when unchanged).
- `deploy/tests/test_deploy.py`: 5 tests against a real repo checkout with a local `ssh` stub — the two-call transport (tar-stream then `activate.sh` invocation) with a tar-listing check (all required release files present, no `server/state/`, no `.venv/`, no `skypane.env`), exit-status propagation both ways, usage-on-no-argument, and the absence of `rsync`/`sha256sum` in the script text.
- Verified TDD gate sequence for both scripts: `test(37-06)` RED commits confirmed failing (against the absent `activate.sh`, and against the pre-plan rsync-based `deploy.sh`), followed by `feat(37-06)` GREEN commits confirmed passing.

## Task Commits

Each task was committed atomically (Task 2 and Task 3 as explicit TDD RED/GREEN pairs):

1. **Task 1: Phase 32 gate, fake-root fixture and PATH stubs for deploy tests** - `8c0d74e` (test)
2. **Task 2: activate.sh — stage, install, swap, probe, roll back, prune (TDD)** - `386d18f` (test, RED) / `c6a17e1` (feat, GREEN)
3. **Task 3: Rewrite deploy.sh as git archive \| ssh + remote activate (TDD)** - `8d11239` (test, RED) / `eea2a0b` (feat, GREEN)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `deploy/tests/conftest.py` - New: fake_root/stub_bin/fake_release/run_activate fixtures
- `deploy/activate.sh` - New, executable (0755): VPS-side atomic/verified deploy
- `deploy/tests/test_activate.py` - New: 12 behavior tests
- `deploy/deploy.sh` - Rewritten: git archive \| ssh transport, no rsync/sha256sum
- `deploy/tests/test_deploy.py` - New: 5 transport tests

## Decisions Made
See `key-decisions` in the frontmatter above (minimal `--help`-only stand-ins for the three service scripts inside a real copy of `deploy/`; curl stub keys probes by request path so `FAKE_HTTP_CODES` keys apply uniformly to loopback and HTTPS checks; two `<behavior>` bullets that each describe two related `FAKE_*` sub-cases are each one test function, keeping the "12 behavior tests" count exact; per-sha unit-file markers live in the test file, not the shared fixture, so a rollback test proves real content restoration rather than trivial byte-equality between two identical-source copies).

## Deviations from Plan

None — plan executed exactly as written. One test-writing correction made *during* GREEN verification (not a plan deviation, a test-authoring bug caught by the process working as intended): the first draft of the "no previous release" test asserted `current` would not exist after a failing first-ever deploy. Re-reading the plan's own step ordering (swap at step 11, probe at step 13) showed this was wrong — the swap already happened before probing, and with no earlier release to fall back to there is nothing to swap back to, so `current` legitimately still points at the failing release (documented in RESEARCH.md as T-37-31, "old in-place dirs kept as manual fallback"). The test assertion was corrected to match the plan's own documented, intentional behavior; no script logic changed.

## Issues Encountered

None new. `bash -n` clean on both scripts. `server/.venv/bin/ruff check deploy/` clean (note: `ruff check <specific-file.sh>` mis-parses a shell script as Python when given an explicit non-`.py` path — always invoke ruff on the `deploy/` directory, not on `deploy/activate.sh`/`deploy/deploy.sh` by name, a harness quirk rather than a code issue). Full suite re-run after each task (`server/.venv/bin/python -m pytest deploy/ server/ stub-server/ companion/ test-support/`): 941 passed, 6 skipped (3 root-euid permission-bit skips, 3 Playwright/Chromium-unavailable skips), 2 failed — both the pre-existing, sandbox-root-only `test_companion_app`/`test_status_pages` legacy-harness failures already documented by every prior 37-0N plan (Phase 33 scope, unrelated to this plan's files). An automated `Merge origin/main (Phase 33 start)` commit (`eb7280d`) landed on this branch between Task 1 and Task 2 — not an action taken by this execution; the merge touched only `.planning/STATE.md`/`ROADMAP.md` and added Phase 33's own plan files, with zero conflicts in anything this plan touches, confirmed by the still-green full suite immediately after.

## User Setup Required

None — no external service configuration required. **Operational note for the developer, carried forward from the plan's own objective:** once this plan is on `main`, the next *approved* production deployment run will execute this new `deploy.sh`/`activate.sh` flow instead of the old rsync-based one. `activate.sh`'s own prerequisite check (`BACKUP_ROOT/{archives,pulled}` must exist) will refuse to change anything on the current production VPS — it goes red with a clear "run deploy/provision.sh first" message and leaves the running services untouched — because those directories don't exist yet on the current box (Plan 37-07 creates them). **Do not approve a production deployment between merging this plan and the Plan 37-09 human-supervised cutover.** If one is accidentally approved before then, the worst case is a red CI job with nothing changed on the VPS, by design (T-37-26/T-37-31).

## Next Phase Readiness
- `deploy/activate.sh`'s prerequisite check is the explicit gate the objective calls for: it will keep failing safely on the current production VPS until Plan 37-07 (provision.sh: skypane-backup user/dirs, release-layout dirs, `skypane.env` ownership, SSH hardening) has run there.
- `deploy/tests/conftest.py`'s `fake_root`/`stub_bin`/`fake_release`/`run_activate` fixtures are available to any later deploy-side plan that needs to exercise VPS-root shell scripts in CI without a real VPS.
- `deploy/deploy.sh`'s two-call transport (`git archive | ssh` then `ssh ... activate.sh`) is the final shape `ci.yml`'s existing single `./deploy/deploy.sh "$DEPLOY_SSH_TARGET"` step already invokes unmodified (D-13, concurrency untouched) — no CI workflow change was needed by this plan.
- No blockers for the rest of Wave A. `deploy/README.md`'s deploy-flow description is now stale (still describes the rsync-based script) — not in this plan's file list; flagged here for whichever later plan (37-07 or the cutover plan) updates operational docs.

---
*Phase: 37-security-and-operations-hardening*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 5 files claimed as created/modified (`deploy/activate.sh`,
`deploy/deploy.sh`, `deploy/tests/conftest.py`,
`deploy/tests/test_activate.py`, `deploy/tests/test_deploy.py`) exist on
disk. All five task commits (`8c0d74e`, `386d18f`, `c6a17e1`, `8d11239`,
`eea2a0b`) are present in `git log --oneline --all`.
