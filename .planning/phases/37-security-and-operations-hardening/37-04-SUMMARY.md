---
phase: 37-security-and-operations-hardening
plan: 04
subsystem: infra
tags: [backups, sqlite, systemd, ssh, forced-command, launchd, posix-sh, pytest, tdd]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest infrastructure (conftest.py, pyproject.toml [tool.pytest.ini_options], no-network socket guard)
provides:
  - "deploy/backup/skypane_backup.py: stdlib nightly snapshot job (main(argv=None) -> int) matching skypane-backup.service's ExecStart contract (Plan 37-03) - allow-listed tar.gz + .sha256 with a WAL-safe sqlite3.Connection.backup() snapshot of history.db"
  - "deploy/backup/backup_gate.py: self-contained, stdlib-only forced-command gate (list/get NAME/ack NAME) for skypane-backup's authorized_keys restrict,command= entry - writes the exact marker format Plan 37-02's companion/pages/health_page.py:offbox_backup_status() parses"
  - "deploy/backup/mac/skypane-backup-pull.sh + skypane-backup-pull.plist.template + install-launchagent.sh: POSIX sh pull client, launchd LaunchAgent (09:30 + RunAtLoad), and a one-command installer"
  - "deploy/tests/{test_backup,test_backup_gate,test_mac_pull}.py: 23 new pytest tests"
affects: [37-06 (activate.sh installs backup_gate.py at /usr/local/lib/skypane), 37-07 (provision.sh creates the skypane-backup user/dirs/key and installs authorized_keys), 37-09 (production cutover enables skypane-backup.timer), 37-10 (production enablement)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Allow-list, not deny-list, for what a backup job archives: an unlisted top-level state/ entry is printed to stdout as drift rather than silently skipped or silently included - so a future phase's new state file is noticed, not lost"
    - "A forced-command SSH gate self-contained on purpose: it runs as /usr/bin/python3 outside the venv and outside any release checkout, so it duplicates the one regex constant it needs (ARCHIVE_RE) rather than importing from deploy/backup/skypane_backup.py"
    - "Config files consumed by a POSIX sh script are parsed line-by-line with sed, never sourced (`.`/`source`) - operator-editable input never becomes executable shell code"
    - "Retention pruning avoids GNU-only flags (no `head -n -N`) by sorting descending and using `tail -n +N` for 'all but the newest N', kept portable to both BSD (macOS, production) and GNU (Linux, CI) coreutils"

key-files:
  created:
    - deploy/backup/skypane_backup.py
    - deploy/backup/backup_gate.py
    - deploy/backup/mac/skypane-backup-pull.sh
    - deploy/backup/mac/skypane-backup-pull.plist.template
    - deploy/backup/mac/install-launchagent.sh
    - deploy/tests/test_backup.py
    - deploy/tests/test_backup_gate.py
    - deploy/tests/test_mac_pull.py
  modified: []

key-decisions:
  - "history.db is handled outside both INCLUDE_FILES/INCLUDE_DIRS entirely (never treated as 'just another include file') because it alone needs the sqlite3 backup API, not a plain copy - keeping that special case visually separate in the code from the allow-list loop"
  - "The .sha256/tar.gz partial files use a `.partial-` PREFIX (not a suffix) on the final name, matching RESEARCH.md's own `archives/.partial-*` wording, so a stale one from an interrupted run is trivially recognisable and prunable by prefix"
  - "The Mac pull script's retention loop reads from temp files via input redirection, never a pipe into `while read`, because piping into a loop runs it in a subshell in POSIX sh (dash) - variables set inside (FAILED, NEWEST, SEEN_MONTHS) would silently fail to propagate to the parent shell otherwise"
  - "12-month retention cutoff tries BSD `date -v-11m` first (macOS, production) and falls back to GNU `date -d '11 months ago'` (the Linux test/CI environment) - one function, tried in order, rather than two code paths or a hard OS check"

requirements-completed: [SEC-04]

# Metrics
duration: 15min
completed: 2026-09-24
---

# Phase 37 Plan 04: Nightly backups, forced-command pull gate, Mac client Summary

**A stdlib nightly snapshot job takes a WAL-safe `sqlite3.Connection.backup()` copy of `history.db` plus an allow-listed archive of the rest of `/opt/skypane/state` (including `gallery/` per D-24) into a checksummed, retained `tar.gz`; a self-contained forced-command gate answers exactly `list`/`get NAME`/`ack NAME` over the `skypane-backup` SSH key; and a POSIX sh Mac client plus a launchd LaunchAgent pull, verify, retain, and acknowledge those archives nightly, with a one-command installer.**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-09-24T08:13:00Z
- **Completed:** 2026-09-24T08:28:04Z (Task 3 commit)
- **Tasks:** 3/3 completed
- **Files modified:** 8 (8 created, 0 modified)

## Accomplishments
- `deploy/backup/skypane_backup.py`: `main(["--state-dir", D, "--archive-dir", D, "--keep", N])` (matches `deploy/skypane-backup.service`'s `ExecStart` exactly, per 37-03). `snapshot_db()` uses `sqlite3.Connection.backup()` + `PRAGMA integrity_check` on the copy (never the live database) so a concurrent writer thread never produces a torn snapshot (D-03, T-37-18) - verified by a test with a genuinely separate writer connection inserting rows throughout the run. `INCLUDE_FILES`/`INCLUDE_DIRS` are an allow-list (D-24's `gallery/`, Phase 34's `devices.json`, and the rest of RESEARCH.md's "State inventory" YES rows); an unlisted top-level file is printed to stdout as drift (`skypane_backup: not in include list: NAME`) while `KNOWN_EXCLUDED` patterns (`panel.bin`, `theme_previews`, `caddy-access.log*`, the WAL/SHM siblings, `*.lock`/`*.tmp`, `img`) stay silent. Archives are written to `.partial-NAME` then `os.fsync` + `os.replace`'d into `skypane-state-YYYYMMDDTHHMMSSZ.tar.gz`, checksummed the same atomic way into a matching `.sha256`, and pruned to the newest `--keep` (default 14), also removing orphan `.sha256`/`.partial-*` entries. Under a test-imposed `os.umask(0o027)`, both files land at `0640` for free (no explicit `chmod`), since neither `tarfile.open()` nor `open()` overrides the umask.
- `deploy/backup/backup_gate.py`: self-contained (no import from `skypane_backup.py` - it runs as `/usr/bin/python3` outside the venv and any release checkout), parses `SSH_ORIGINAL_COMMAND` with `shlex.split` and dispatches on an exact `(verb, word-count)` match against `list`/`get NAME`/`ack NAME` only (D-05, D-25, T-37-17). Every name is checked against a duplicated `ARCHIVE_RE` and `os.lstat` + `stat.S_ISREG` before anything is opened, so a path-traversal-shaped name, an absolute path, or a symlinked archive is rejected outright (T-37-16) - `../../opt/skypane/skypane.env`, `/etc/passwd`, an extra argument, an unknown verb, an unbalanced quote, and a symlink standing in for a real archive all exit 2 with one line on stderr and touch nothing. `ack` writes the archive name via a tmp file + `os.chmod 0o644` + `os.replace` to `pulled-dir/last-pull` - the exact marker format Plan 37-02's `offbox_backup_status()` already parses (confirmed by reading that function's own docstring/regex before writing this task).
- `deploy/backup/mac/skypane-backup-pull.sh` (POSIX sh, `dash -n`-clean): retries `list` up to 3 times, fetches only archives missing from `DEST` to a `.NAME.partial`, verifies each against the checksum `list` reported with `shasum -a 256` before moving it into place (discarding and remembering failure on a mismatch), acks the newest listed name only when nothing failed, then prunes to the 30 newest local archives plus the oldest local archive of each earlier `YYYYMM` still within 12 months (BSD `date -v-11m` tried first, GNU `date -d` as fallback, so the same script runs unmodified on macOS and in CI). The config file is parsed with `sed`, never sourced. Retention specifically reads from temp files via `< file` redirection rather than piping into `while read`, since a pipe would run the loop in a subshell under POSIX sh and silently drop every variable it sets.
- `deploy/backup/mac/skypane-backup-pull.plist.template` + `install-launchagent.sh`: `Label com.skypane.backup-pull`, `StartCalendarInterval {Hour:9, Minute:30}` + `RunAtLoad true` (RunAtLoad covers a Mac that was powered off at 09:30 - `StartCalendarInterval` alone only coalesces one missed run at wake from sleep, per `launchd.plist(5)`). The installer writes the conf (`0600`), copies the script (`0755`) to `~/Library/Application Support/SkyPane/` (refusing `~/Documents`, `~/Desktop`, `~/Downloads` - TCC), renders the plist with absolute paths (no `~` anywhere, verified with `plistlib`), and bootstraps the agent via `launchctl`, tolerating a first-install `bootout` failure.
- `deploy/tests/{test_backup,test_backup_gate,test_mac_pull}.py`: 23 new pytest tests. `test_backup.py` builds a real WAL `history.db` via `server.history_db` with a genuinely separate writer connection running concurrently with the snapshot. `test_backup_gate.py` runs the gate as a real subprocess with `SSH_ORIGINAL_COMMAND` set the way sshd would. `test_mac_pull.py` runs both shell scripts as real `/bin/sh` subprocesses with a fake `ssh` on `PATH` that execs the real `backup_gate.py`, so the pull script's SSH-option handling, checksum verification, retry loop, and retention math are all exercised against the actual gate contract, not a mock.

## Task Commits

Each task was committed atomically:

1. **Task 1: Phase 32 gate, then the nightly snapshot job (TDD)** - `f0ed4c4` (feat) — RED (`FileNotFoundError` importing the not-yet-created module) confirmed, then GREEN.
2. **Task 2: The forced-command gate (list/get/ack) (TDD)** - `80ab977` (feat) — RED (3 subprocess-call failures) confirmed, then GREEN.
3. **Task 3: Mac pull script, LaunchAgent template and installer** - `b0bcdf3` (feat) — RED (6 subprocess-call failures) confirmed, then GREEN.

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `deploy/backup/skypane_backup.py` - Nightly snapshot job: WAL-safe `history.db` backup, allow-listed archive, checksum, retention
- `deploy/backup/backup_gate.py` - Self-contained forced-command gate: `list`/`get NAME`/`ack NAME`
- `deploy/backup/mac/skypane-backup-pull.sh` - POSIX sh Mac pull client: fetch, verify, ack, retain
- `deploy/backup/mac/skypane-backup-pull.plist.template` - launchd LaunchAgent template
- `deploy/backup/mac/install-launchagent.sh` - One-command installer: conf, script, plist, bootstrap
- `deploy/tests/test_backup.py` - New: 8 tests
- `deploy/tests/test_backup_gate.py` - New: 8 tests
- `deploy/tests/test_mac_pull.py` - New: 7 tests

## Decisions Made
See `key-decisions` in the frontmatter above (history.db kept visually separate from the allow-list loop; `.partial-` as a name PREFIX per RESEARCH.md's own wording; retention reads from temp files to dodge the POSIX-sh pipe-into-`while`-is-a-subshell trap; BSD-then-GNU `date` fallback for the 12-month cutoff, one function tried in order rather than two code paths).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Two explanatory comments reworded to avoid tripping this plan's own grep-based acceptance criteria**
- **Found during:** Task 3, running the acceptance-criteria grep after GREEN
- **Issue:** `grep -Ec '\[\[|mapfile|declare -A|head -n -' deploy/backup/mac/skypane-backup-pull.sh` is meant to prove the script contains no bash-isms in actual code, but two of the script's own header/retention comments *described* those exact bash-isms in prose ("avoids... `[[ ]]`, arrays, mapfile... `head -n -N`") so as to explain why the script is written the way it is - the same shape 37-03's SUMMARY already documented for `skypane.env`/`IPAddressDeny`.
- **Fix:** Reworded both comments to describe the same avoided constructs without using their literal substrings (e.g. "double-bracket conditionals" instead of `[[ ]]`, "a GNU-only negative head line count" instead of `head -n -N`).
- **Files modified:** `deploy/backup/mac/skypane-backup-pull.sh`
- **Verification:** `grep -Ec '\[\[|mapfile|declare -A|head -n -' deploy/backup/mac/skypane-backup-pull.sh` now returns `0`; `sh -n`/`dash -n` still clean; all 7 `test_mac_pull.py` tests still pass.
- **Committed in:** `b0bcdf3` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug in comment text, not behavior)
**Impact on plan:** No behavior changed - purely documentation wording, and necessary for the plan's own acceptance criteria to measure what they intend (actual code, not prose describing avoided code).

## Issues Encountered

**`shellcheck` is not installed in this sandbox** (`command -v shellcheck` found nothing), so the plan's own `--shell=sh` lint step could not run here. `sh -n`/`dash -n` (POSIX syntax check) passed clean on both `deploy/backup/mac/*.sh`. Per the plan's own verification note, the shellcheck lint runs in CI via Plan 37-07's step - not a gap this plan introduces, and consistent with `deferred-items.md`'s existing entries from 37-01/37-02/37-03.

**No new pre-existing-failure findings.** A full `./scripts/run-all-tests.sh` run after all three tasks shows exactly the same two sandbox-root-only legacy-harness failures already documented by 37-01/37-02/37-03 (`test_companion_app`, `test_status_pages`) - 873 passed vs. 850 (37-03's own baseline) + 23 (this plan's new tests) = 873, confirming no regression. Coverage 93.13%, above the 93% floor (`deploy/backup` now measured: `skypane_backup.py` 83%, `backup_gate.py` 94% - both driven mostly by the happy-path/rejection tests above; the uncovered lines are mostly the `OSError` fallback branches in `_prune`/`_cmd_list`/`_cmd_ack`, which are defensive against filesystem races that are not independently exercised).

## User Setup Required

None - no external service configuration required. This plan's scripts are not installed anywhere yet: the `skypane-backup` user/directories/SSH key (Plan 37-07), the gate's install location at `/usr/local/lib/skypane` (Plan 37-06), and the backup timer's production enablement (Plan 37-09/37-10) are all later plans' work. Nothing in this plan is reachable from production until then.

## Next Phase Readiness
- `deploy/backup/skypane_backup.py`'s CLI already matches `deploy/skypane-backup.service`'s `ExecStart` (37-03) exactly - no further script change needed for that unit to work once installed.
- `deploy/backup/backup_gate.py` is ready for Plan 37-06's `activate.sh` to install at `/usr/local/lib/skypane/backup_gate.py`, and for Plan 37-07's `provision.sh` to reference in the `skypane-backup` user's `authorized_keys` `restrict,command=` entry.
- `deploy/backup/mac/install-launchagent.sh` is ready for the developer to run by hand on their Mac once the VPS-side key exists (D-21 human checkpoint, owned by a later plan).
- The marker format `backup_gate.py ack` writes (`NAME + "\n"`, mode `0644`, at `pulled-dir/last-pull`) was verified directly against Plan 37-02's `offbox_backup_status()` regex/parsing contract before this plan's Task 2 was written - no follow-up needed there.
- No blockers for the rest of Wave A.

---
*Phase: 37-security-and-operations-hardening*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 8 files claimed as created (`deploy/backup/skypane_backup.py`,
`deploy/backup/backup_gate.py`, `deploy/backup/mac/skypane-backup-pull.sh`,
`deploy/backup/mac/skypane-backup-pull.plist.template`,
`deploy/backup/mac/install-launchagent.sh`, `deploy/tests/test_backup.py`,
`deploy/tests/test_backup_gate.py`, `deploy/tests/test_mac_pull.py`) exist
on disk. All three task commits (`f0ed4c4`, `80ab977`, `b0bcdf3`) are
present in `git log --oneline --all`.
