---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 15
subsystem: infra
tags: [ci, deploy, firmware, ota, backup, github-actions]

# Dependency graph
requires:
  - phase: 42-01
    provides: "server.firmware_registry.publish_release(state_dir, manifest, image_path, bench=False, now=None) -> \"added\" | \"exists\" (ValueError on any mismatch)"
  - phase: 42-11
    provides: "firmware-release.yml publishing skypane-<tag>.bin + release.json as GitHub Release assets named <tag>, then dispatching ci.yml on main"
provides:
  - "server/firmware_cli.py: import-dir <dir>, import-bench --file --version, list -- the deploy-time operator CLI over firmware_registry.publish_release"
  - "deploy.sh ships every downloaded firmware release alongside the code archive (SKYPANE_FIRMWARE_DIR); activate.sh imports them into /opt/skypane/state/firmware/ as the skypane user, before the current symlink swap"
  - ".github/workflows/ci.yml: workflow_dispatch trigger, deploy job accepts push or dispatch, a Download firmware releases step pulling every fw-v* GitHub Release"
  - "deploy/backup/skypane_backup.py: firmware/ added to the nightly backup allow-list, KNOWN_EXCLUDED (registry.lock) still filtered inside it"
  - "deploy/README.md documents the full release flow, firmware_cli list, and import-bench"
affects: [42-16]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Deploy-time CLI over an existing pure registry module (firmware_cli wraps firmware_registry.publish_release/load_registry, never touches storage directly) -- same shape as stub-server/devices_cli.py"
    - "Two ordered tar streams over one ssh session in deploy.sh (code, then an optional firmware-releases stream) instead of a second ssh round trip"
    - "A second tarfile filter (_no_symlinks_or_known_excluded) applies the existing KNOWN_EXCLUDED allow/deny distinction inside a directory that is itself allow-listed, so a transient file nested in firmware/ (registry.lock) is still excluded even though tarfile.add() walks the whole tree"

key-files:
  created:
    - server/firmware_cli.py
    - server/test_firmware_cli.py
  modified:
    - deploy/deploy.sh
    - deploy/activate.sh
    - deploy/tests/test_deploy.py
    - deploy/tests/test_activate.py
    - deploy/tests/conftest.py
    - .github/workflows/ci.yml
    - deploy/README.md
    - deploy/backup/skypane_backup.py
    - deploy/tests/test_backup.py

key-decisions:
  - "requirements-completed left empty here on purpose: OTA-10 is shared with plan 16's hardware session and the plan's own verification section defers the first real release import to that plan -- REQUIREMENTS.md is not touched by this plan"
  - "The workflow_dispatch guard reuses the exact same production environment reviewer gate and 'main has moved on' step as an ordinary push -- verified byte-identical against origin/main in that step's diff, so a manually dispatched deploy carries no weaker review than a normal one"
  - "Firmware import runs after the smoke tests but before the current symlink swap in activate.sh, so a release whose bytes fail the manifest check aborts activation with the previous release still serving -- never a half-imported firmware store behind newly swapped code"

requirements-completed: []

coverage:
  - id: D1
    description: "server/firmware_cli.py import-dir/import-bench/list over firmware_registry.publish_release, idempotent, exits 1 on any tag/manifest/symlink mismatch without publishing that subdirectory"
    requirement: "OTA-10"
    verification:
      - kind: unit
        ref: "server/test_firmware_cli.py (20 tests, all pass)"
        status: pass
      - kind: other
        ref: "server/.venv/bin/ruff check server/firmware_cli.py server/test_firmware_cli.py; grep -cE 'os\\.remove|os\\.unlink|shutil\\.rmtree' server/firmware_cli.py == 0"
        status: pass
    human_judgment: false
  - id: D2
    description: "deploy.sh streams SKYPANE_FIRMWARE_DIR's contents alongside the code archive; activate.sh imports them as skypane before the current symlink swap, failing activation (previous release still current) on any import error"
    requirement: "OTA-10"
    verification:
      - kind: unit
        ref: "deploy/tests/test_deploy.py (8/8 pass natively) + deploy/tests/test_activate.py (25/25 pass in a Linux container -- macOS bash mv lacks -T, a pre-existing environment limitation, see Deviations)"
        status: pass
      - kind: other
        ref: "shellcheck deploy/deploy.sh deploy/activate.sh (clean apart from a pre-existing SC2329 info-level note on origin/main's on_exit, unrelated to this plan); grep -c 'firmware_cli import-dir' deploy/activate.sh == 1"
        status: pass
    human_judgment: false
  - id: D3
    description: "ci.yml gains workflow_dispatch and downloads every fw-v* GitHub Release into firmware-releases/<tag>/ for the reviewer-gated deploy job; firmware/ backed up nightly; deploy/README.md documents the flow"
    requirement: "OTA-10"
    verification:
      - kind: unit
        ref: "deploy/tests (whole suite, including test_ci_secrets.py and test_docs.py) pass"
        status: pass
      - kind: other
        ref: "actionlint .github/workflows/ci.yml clean; git diff origin/main -- .github/workflows/ci.yml shows the 'Refuse to deploy if main has moved on' step unchanged; grep -c \"github.event_name == 'workflow_dispatch'\" ci.yml == 1; grep -c '/opt/skypane/state/firmware' deploy/README.md >= 1; grep -c '\"firmware\"' deploy/backup/skypane_backup.py >= 1"
        status: pass
    human_judgment: true
    rationale: "The first real fw-v* release download/import against a live GitHub Release only happens in plan 16's hardware session -- this plan proves the CLI/scripts/tests statically and in a Linux container, not against a real dispatched CI run"

# Metrics
duration: ~2h (two sessions: initial executor stopped on an API rate limit after Task 3's ci.yml/backup edits; this continuation verified, fixed a grep-matching regression, wrote the README section, and closed out)
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 15: Firmware release deploy pipeline Summary

**A published fw-v* GitHub Release reaches `/opt/skypane/state/firmware/` only through the existing reviewer-gated deploy: `server/firmware_cli.py import-dir` over `firmware_registry.publish_release`, `deploy.sh`/`activate.sh` shipping and importing releases before the code swap, and `ci.yml`'s `workflow_dispatch` + `gh release download` step feeding it**

## Performance

- **Duration:** ~2h across two sessions (continuation after an API rate limit, not a code failure)
- **Completed:** 2026-09-28
- **Tasks:** 3
- **Files modified:** 11 (2 created, 9 modified)

## Accomplishments

- `server/firmware_cli.py` (`import-dir <dir>`, `import-bench --file --version`, `list`), all over `--state-dir`, defaulting to the production state dir constant every other server entry point uses: `import-dir` publishes every tag-named subdirectory idempotently (`added <tag>` / `exists <tag>`), rejects a bad tag name, a missing/oversized `release.json`, or a symlinked image without touching the other valid subdirectories, and never accepts `--bench` (that's `import-bench`, reserved for the hardware session, recording `bench=True` and a generated "Bench image (not a release)" note)
- `deploy.sh`: when `SKYPANE_FIRMWARE_DIR` names an existing directory, a second `tar` stream (after the code archive, over the same `ssh` session) ships it to `releases/.incoming-<sha>/firmware-releases/`; a set-but-missing directory fails before any `ssh` call; unset, nothing changes
- `activate.sh`: ensures `${STATE_DIR}/firmware` exists (mode 0750, owner `skypane`), then — after the smoke tests, before the `current` symlink swap — runs `runuser -u skypane -- python3 -m server.firmware_cli import-dir <staged dir> --state-dir <STATE_DIR>` when a staged `firmware-releases` directory is present; a non-zero import exit aborts activation with the previous release still current; no staged directory logs a skip line and changes nothing else
- `.github/workflows/ci.yml`: `workflow_dispatch:` trigger; the `deploy` job's `if:` now accepts `push` or `workflow_dispatch` (still gated to `refs/heads/main`, still behind the unchanged `production` environment reviewer and the unchanged "main has moved on" guard); a new `Download firmware releases` step lists every `fw-v*` GitHub Release via `gh release list`/`gh release download` into `firmware-releases/<tag>/` (zero releases is a no-op), passed to `deploy.sh` via `SKYPANE_FIRMWARE_DIR` in the `Deploy` step's `env:`
- `deploy/backup/skypane_backup.py`: `"firmware"` added to `INCLUDE_DIRS`; a new `_no_symlinks_or_known_excluded` filter applies the existing `KNOWN_EXCLUDED` glob (so `registry.lock` stays out) even though `tarfile.add()` walks the whole allow-listed directory recursively
- `deploy/README.md`: a new "Firmware releases (OTA)" section documents the end-to-end flow (tag → `firmware-signing` review → CI dispatched on `main` → `production` review → import → "Available" in the companion → Install), the ~1 MB/release backup growth note, `firmware_cli list` on the VPS, and `import-bench`'s hardware-session-only scope

## Task Commits

Each task was committed atomically:

1. **Task 1a: firmware_cli tests (RED)** - `d78c3c9c` (test)
2. **Task 1b: firmware_cli import-dir/import-bench/list (GREEN)** - `9a113c4b` (feat)
3. **Task 2a: deploy.sh/activate.sh firmware import tests (RED)** - `35b6150d` (test)
4. **Task 2b: deploy.sh ships releases, activate.sh imports before swap (GREEN)** - `16b1e4a6` (feat)
5. **Task 3: CI deploy job downloads releases, backup allow-list, README** - `425fd473` (feat)
6. **Post-verification fix: keep `firmware_cli import-dir` on one line in activate.sh** - `b1157435` (fix)

_Task 1 and Task 2 are each `tdd="true"`: test → feat, no refactor commit needed (GREEN was clean on the first pass). Task 3 is a single non-TDD commit. The final fix commit closes a deviation found during this continuation's own verification pass (see below)._

## Files Created/Modified
- `server/firmware_cli.py` - new: deploy-time operator CLI over `firmware_registry.publish_release` (`import-dir`, `import-bench`, `list`)
- `server/test_firmware_cli.py` - new: 20 tests against a tmp state dir
- `deploy/deploy.sh` - streams `SKYPANE_FIRMWARE_DIR`'s contents as a second tar stream when set
- `deploy/activate.sh` - ensures `STATE_DIR/firmware`, imports staged releases before the `current` swap
- `deploy/tests/test_deploy.py`, `deploy/tests/test_activate.py`, `deploy/tests/conftest.py` - extended fake-root/fake-ssh coverage for the firmware stream/import
- `.github/workflows/ci.yml` - `workflow_dispatch`, dispatch-aware deploy `if:`, `Download firmware releases` step, `SKYPANE_FIRMWARE_DIR` env
- `deploy/backup/skypane_backup.py` - `firmware` added to `INCLUDE_DIRS`, nested-exclusion filter
- `deploy/tests/test_backup.py` - one new test proving firmware is archived with no drift and `registry.lock` excluded
- `deploy/README.md` - new "Firmware releases (OTA)" section

## Decisions Made
- `requirements-completed` left empty: OTA-10 is shared with plan 16's hardware session, which performs the first real tag/release/import; the project's own instructions for this plan say not to mark it complete in REQUIREMENTS.md here, and this plan's own `<verification>` section already defers that proof to plan 16.
- Verified the `workflow_dispatch` addition changes nothing about the review gate: `git diff origin/main -- .github/workflows/ci.yml` shows the "Refuse to deploy if main has moved on" step byte-identical, and the `production` environment/reviewer requirement is untouched.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `firmware_cli import-dir` split across a line-wrapped shell continuation in activate.sh**
- **Found during:** this continuation's own verification pass, re-running every acceptance-criteria command from the plan
- **Issue:** the prior session's commit `16b1e4a6` wrapped the `runuser` command as `... -m server.firmware_cli \` / `                import-dir ...` on the next line. The command itself was correct, but the plan's own acceptance criterion `grep -c 'firmware_cli import-dir' deploy/activate.sh == 1` matched 0, since the literal string never appears on one line.
- **Fix:** re-wrapped so `server.firmware_cli import-dir` sits on the same line; the line break moved one token later. No behaviour change.
- **Files modified:** `deploy/activate.sh`
- **Verification:** `grep -c 'firmware_cli import-dir' deploy/activate.sh` now returns 1; re-ran 25/25 `deploy/tests/test_activate.py` in the Linux container (all pass, including the 4 new firmware tests)
- **Committed in:** `b1157435`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Cosmetic-only fix to satisfy the plan's own literal acceptance-criteria grep; the underlying deploy/activate behaviour was already correct before the fix.

## Issues Encountered

- **macOS `bash mv` lacks `-T`:** every fake-root `deploy/tests/test_activate.py` test (20 pre-existing + 4 new firmware ones) fails natively on this Mac with `mv: illegal option -- T`, a pre-existing, documented environment limitation (BSD `mv` vs. GNU `mv`, unrelated to any code in this plan). Proved the 4 new firmware-import tests pass in a Linux container (`python:3.14` image, matching CI): `25 passed in ~11s` for the whole `test_activate.py` file. Added the 4 new test names to the session's `known-env-fail.txt` allowlist so `fullcheck.sh` reports no new failures; this is a scratchpad artifact, not a repo file.
- **`shellcheck` SC2329 on `on_exit`:** shellcheck flags `on_exit() { ... }` in `activate.sh` as "never invoked" (an info-level false positive — it's invoked indirectly via a `trap`). Confirmed pre-existing on `origin/main` (same warning, same line count, before this plan's changes) — out of scope for this plan, left untouched.
- **`scripts/check_comment_history.py check` reports unrelated findings** in `companion/test_browser_update.py` / `companion/test_update_actions.py` (D-id/plan-artifact style comments) — pre-existing on this branch from the 42-14 plan, not touched by this plan's `files_modified` list, out of scope per the scope-boundary rule. Not fixed here.
- **Docker container git-worktree artifact:** running `deploy/tests/test_deploy.py` inside the Linux container (via a read-only bind mount + `cp -r`) fails 5/8 tests with `fatal: not a git repository`, because the copied `.git` file still points at this Mac's absolute worktree gitdir path, which doesn't exist inside the container. This is a container-copy artifact, not a real regression: all 8 `test_deploy.py` tests pass natively on macOS (git works fine there, unlike the `mv -T` issue), so `test_deploy.py` was verified natively instead.

## User Setup Required

None - no external service configuration required. The first real `fw-v*` tag push, signed release, and live import happen in plan 16's hardware session.

## Next Phase Readiness

- Plan 16 (hardware session) can push a real `fw-v*` tag: `firmware-release.yml` (plan 11) will build/sign/publish it, `ci.yml`'s `workflow_dispatch` dispatch (plan 11's `gh workflow run ci.yml --ref main`) will trigger a reviewed deploy, and that deploy will download, ship and import the release into `/opt/skypane/state/firmware/` via the machinery built here — closing OTA-10 end to end.
- No blockers. `firmware_cli list` is available on the VPS today (returns "(no releases published)" until the first import).

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*
