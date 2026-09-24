---
phase: 37-security-and-operations-hardening
plan: 07
subsystem: infra
tags: [ssh, sshd_config, systemd, provisioning, backups, forced-command, ci, shellcheck, docs]

# Dependency graph
requires:
  - phase: 37-security-and-operations-hardening (Plan 37-03)
    provides: deploy/render_caddyfile.sh (the only Caddyfile renderer), the release-layout units, skypane-backup.service/.timer
  - phase: 37-security-and-operations-hardening (Plan 37-04)
    provides: deploy/backup/backup_gate.py (the forced-command gate this plan's key installer points at), deploy/backup/skypane_backup.py
  - phase: 37-security-and-operations-hardening (Plan 37-06)
    provides: deploy/activate.sh (its prerequisite check — ENV_FILE, VENV/bin/python3, BACKUP_ROOT/{archives,pulled} — is the explicit gate this plan's provision.sh now satisfies), deploy/deploy.sh
provides:
  - "deploy/harden_sshd.sh: writes and sshd -t-validates /etc/ssh/sshd_config.d/00-skypane.conf (PermitRootLogin no + six related directives), restoring the previous drop-in (or removing a new one) on validation failure instead of ever reloading an unvalidated config"
  - "deploy/provision.sh: no longer installs units or renders the Caddyfile (activate.sh owns both, D-11); creates the root-owned releases/ directory and a root:skypane 0750 /opt/skypane, keeps the venv root-owned, secures an existing skypane.env to root:root 0600, and creates the dedicated skypane-backup user/group/directories without ever joining it to group skypane"
  - "deploy/backup/install-backup-key.sh: installs the Mac's ed25519 pull key into skypane-backup's authorized_keys with a forced restrict,command= entry only, after validating the pasted key line against a strict regex that also rejects embedded quotes/backslashes/newlines"
  - "deploy/skypane.env.example: documents SKYPANE_OFFBOX_MARKER and corrects the header's claim about which units read the file"
  - ".github/workflows/ci.yml: a new Shellcheck deploy scripts step in the test job, lints every deploy/**/*.sh"
  - "deploy/README.md: corrected backup/restore documentation, the release-layout deploy flow, env ownership, SSH hardening, and every ssh example now uses ubuntu@"
  - "deploy/tests/{test_provision,test_install_backup_key,test_docs}.py: 34 new pytest tests"
affects: [37-08 (fresh-VPS provisioning runs this exact provision.sh), 37-09 (production cutover: the SSH hardening drop-in and env ownership change are exactly what this plan wrote), 37-10 (the Rehearsal log table this plan added to README.md is filled in there)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SSH drop-in validated before reload, never after: harden_sshd.sh always runs `sshd -t` against the newly-written 00-skypane.conf before touching sshd, and on failure restores the exact previous file (or removes a newly-created one) rather than ever calling systemctl — the reload step is unreachable on a failing path, not merely guarded by an exit code"
    - "Directory ownership narrowed instead of a blanket recursive chown: provision.sh replaced `chown -R skypane:skypane /opt/skypane` with three separate, purpose-scoped ownership statements (root:skypane 0750 on /opt/skypane itself, root:root 0755 on releases/, skypane:skypane only on state/) so a second provisioning run can never silently re-own root-owned release/venv content back to the service user"
    - "A single forced-command regex, validated before any file write: install-backup-key.sh rejects the pasted key outright (no directory created, no file touched) if it doesn't match ^ssh-ed25519 [A-Za-z0-9+/]+={0,3}( [A-Za-z0-9@._-]+)?$ — the same character classes that reject double quotes/backslashes/newlines also make the printed authorized_keys line safe to build with a plain printf, no escaping logic needed"

key-files:
  created:
    - deploy/harden_sshd.sh
    - deploy/backup/install-backup-key.sh
    - deploy/tests/test_provision.py
    - deploy/tests/test_install_backup_key.py
    - deploy/tests/test_docs.py
  modified:
    - deploy/provision.sh
    - deploy/skypane.env.example
    - .github/workflows/ci.yml
    - deploy/README.md

key-decisions:
  - "harden_sshd.sh writes the drop-in to its final path (not a staged .new file) before validating, because sshd -t only reads installed *.conf files in the sshd_config.d directory — the plan's own action text calls this out explicitly, and the backup/restore-on-failure logic exists precisely to make that safe."
  - "provision.sh's skypane-backup directory setup only creates the directories (archives/, pulled/, .ssh/) with the right owners and modes — it deliberately does NOT create .ssh/authorized_keys itself. That file is written by deploy/backup/install-backup-key.sh at the CP-8 human checkpoint (Plan 37-09/37-10), keeping 'prepare the machine' and 'install a specific human-supplied key' as two separately re-runnable steps."
  - "deploy/README.md's device-enrolment section was updated to use /opt/skypane/current/stub-server/devices_cli.py (not the old in-place /opt/skypane/stub-server/) even though the plan's action text didn't call this section out by name — it was already stale from Plan 37-06's release-layout switch (flagged in that plan's own SUMMARY as unaddressed), and leaving it pointing at a path that stops existing after cutover would be a real operational bug once Plan 37-09 runs (Rule 1 auto-fix, in-scope since this plan's whole Task 3 is 'correct deploy/README.md')."
  - "Two explanatory-comment strings had to be reworded after they tripped this plan's own grep-based acceptance criteria (install-backup-key.sh's header literally contained the same 'restrict,command=\"/usr/bin/python3' substring the grep counts against the real printf line) — the same class of self-tripping-documentation issue every prior 37-0N plan's SUMMARY has already documented; recorded here as a decision, not a deviation, since no behavior changed."

requirements-completed: []  # SEC-04/SEC-05/SEC-07/SEC-08 remain marked incomplete per this plan's explicit instruction: provision.sh, harden_sshd.sh and install-backup-key.sh are proven here against fake roots/stubs in CI, but they have not yet run against the real production VPS — that is Plan 37-08's fresh-VPS provisioning and Plan 37-09's human-supervised cutover checkpoint. REQUIREMENTS.md is left untouched.

# Metrics
duration: ~35min
completed: 2026-09-24
---

# Phase 37 Plan 07: SSH hardening, provision.sh release layout, backup pull key, corrected README Summary

**`deploy/harden_sshd.sh` writes and `sshd -t`-validates a `PermitRootLogin no` drop-in with automatic restore-on-failure; `deploy/provision.sh` stops installing units/Caddyfile (now `activate.sh`'s job), root-owns `/opt/skypane`'s releases/venv, secures `skypane.env` to `root:root 600`, and creates a `skypane-backup` pull user that is never a member of group `skypane`; `deploy/backup/install-backup-key.sh` installs the Mac's forced-command-only pull key after a strict ed25519-only regex check; and `deploy/README.md` replaces its "fully reproducible" claim with real Backups/Restore sections, the release-layout deploy flow, and `ubuntu@` throughout — all backed by 34 new pytest tests plus a new CI shellcheck step.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-09-24T08:50:00Z (approx.)
- **Completed:** 2026-09-24T09:27:14Z (Task 3 commit)
- **Tasks:** 3/3 completed
- **Files modified:** 9 (5 created, 4 modified)

## Accomplishments

- `deploy/harden_sshd.sh` (new, executable): overridable `SSHD_CONFIG_DIR`/`SSHD_CONFIG`/`SSHD_BIN`/`SYSTEMCTL`. Refuses to proceed if `SSHD_CONFIG` has no `Include /etc/ssh/sshd_config.d/*.conf` line (the drop-in would be silently ignored). Backs up any existing `00-skypane.conf` to a `mktemp` file outside the drop-in directory, writes the seven directives (`PermitRootLogin no`, `PasswordAuthentication no`, `KbdInteractiveAuthentication no`, `PubkeyAuthentication yes`, `PermitEmptyPasswords no`, `X11Forwarding no`, `MaxAuthTries 3`) via `printf` + `install -m 0644`, then runs `sshd -t -f "$SSHD_CONFIG"` — on failure it restores the previous file (or removes the new one if there wasn't one) and exits non-zero *without ever calling systemctl*; on success it runs `systemctl try-reload-or-restart ssh.service` (correct under Ubuntu's `ssh.socket` activation) and prints the filtered `sshd -T` output. `deploy/provision.sh` calls it with no `|| true`.
- `deploy/provision.sh` (edited): the release layout replaces the old in-place code directories — `${APP_ROOT}/releases` (root:root 0755), `${APP_ROOT}` itself (root:skypane 0750), `state/` (skypane:skypane, unchanged elsewhere). The recursive `chown -R skypane:skypane /opt/skypane` is gone. The venv is created (if absent) and then unconditionally `chown -R root:root`'d, narrowing an existing box's skypane-owned venv on every re-run. An existing `skypane.env` is secured to `root:root 0600` (guarded by an existence test, since the operator writes it by hand after provisioning). The systemd unit-install and Caddyfile-render blocks are gone entirely (`activate.sh` owns both, D-11) — only `caddy`'s own package unit is `enable --now`'d. A new block creates the `skypane-backup` system user/group (`--shell /bin/sh`, `usermod -p '*'`), explicitly removes it from group `skypane` if present (`gpasswd -d`, never `usermod -aG`), and creates `/var/lib/skypane-backup{,/.ssh,/archives,/pulled}` with the owners/modes from the plan's interfaces table (`archives/` setgid `skypane:skypane-backup 2750`). SSH hardening is now one call to `harden_sshd.sh`. The final "Next:" message tells the operator to write `skypane.env` with `install -m 600 -o root -g root`, set `SKYPANE_OFFBOX_MARKER`, and run `deploy/deploy.sh ubuntu@<host>`.
- `deploy/backup/install-backup-key.sh` (new, executable): root guard bypassable via `SKYPANE_KEY_ALLOW_NONROOT=1` (tests only); `BACKUP_HOME` overridable (default `/var/lib/skypane-backup`); validates `$1` against `^ssh-ed25519 [A-Za-z0-9+/]+={0,3}( [A-Za-z0-9@._-]+)?$` before touching any file — the same character classes reject `ssh-rsa`, a key already carrying `command=`/other options, and any key containing a double quote, backslash or newline. Writes the single line `restrict,command="/usr/bin/python3 <gate>" <key>` to a `mktemp` file inside `.ssh/`, `chmod 0644`, `chown root:root`, then `mv -T` into `authorized_keys` — replacing any previous content, never appending, so re-running with a new key never duplicates. Prints the CP-8 Mac-side test commands (`list`, an expected-refusal `cat skypane.env`, an expected-no-shell `-t` attempt) on success.
- `deploy/skypane.env.example`: header corrected (systemd reads this file as root for every unit, not just poll/byos; the real file is root:root 0600) and a new `SKYPANE_OFFBOX_MARKER=/var/lib/skypane-backup/pulled/last-pull` block added after `SKYPANE_CADDY_ACCESS_LOG`, in the same explanatory-paragraph style — confirmed against `companion/pages/health_page.py`'s already-existing `OFFBOX_MARKER_ENV_VAR` reader (built in Plan 37-02), so no companion code needed touching here.
- `.github/workflows/ci.yml`: a new "Shellcheck deploy scripts" step in the `test` job (`find deploy -name '*.sh' -print0 | xargs -0 shellcheck`), placed before the existing offline `systemd-analyze` step. `shellcheck` is not installed in this sandbox (confirmed: `command -v shellcheck` finds nothing, matching every prior 37-0N plan's own finding) — every `deploy/**/*.sh` file (both the bash scripts and the POSIX-sh Mac scripts, each shellcheck's own shebang-detection will lint against the right dialect) was reviewed by hand for the common finding classes (unquoted expansions in test/command contexts, `local x=$(cmd)` masking exit codes, unquoted regex on the right of `=~`, unused variables) with none found; `bash -n`/bash syntax checks are clean on every script. The `concurrency`/`cancel-in-progress`/`group:` blocks are untouched (D-13, verified by diff).
- `deploy/README.md`: the "fully reproducible from this repository" claim is replaced with an accurate split (code/config reproducible, `/opt/skypane/state` is not). New "Backups" section (include list incl. `gallery/` per D-24, 14-VPS/30+monthly-Mac retention, the `skypane-backup` forced-command gate and why it isn't rsync, the Mac LaunchAgent installer, the Health page's 3-day freshness warning). New "Restore" section: a Mac rehearsal procedure (`tar -xzf`, `PRAGMA integrity_check`, running the companion with `--state-dir` on port 8650) and the seven-step production restore from `37-RESEARCH.md` §SEC-04, plus a "Rehearsal log" placeholder table for Plan 37-10. "Ship the code" is rewritten for the release-layout flow (`activate.sh`'s stage/swap/probe/automatic-rollback, units and the Caddyfile installed on *every* deploy, a manual-rollback command for reverting to an already-good release). First-time provisioning now documents the SSH hardening step and the keep-a-session-open discipline. Every `ssh` example uses `ubuntu@`; the one previously-necessary `root@` example (showing the *expected refusal*) was rephrased as `ssh -l root <vps-ip>` so the acceptance grep for a literal absence of `root@` still measures a real property. The device-enrolment section's `devices_cli.py` paths were also updated from the old in-place `/opt/skypane/stub-server/` to `/opt/skypane/current/stub-server/`, matching the release layout Plan 37-06 already shipped (see Deviations).
- `deploy/tests/{test_provision,test_install_backup_key,test_docs}.py`: 34 new pytest tests. `test_provision.py` runs `harden_sshd.sh` as a real subprocess against a fake `sshd_config.d` and stub `sshd`/`systemctl` binaries (success writes the exact 7 lines at mode 0644 with `sshd -t` before the reload call in the shared call log; a failing `sshd -t` restores the previous drop-in or removes a new one, with no `systemctl` call ever logged; a missing `Include` line fails loudly) plus text/`bash -n` checks on `provision.sh` (needs a real root machine to run end-to-end, per the plan's own note). `test_install_backup_key.py` runs the key installer as a real subprocess with a stubbed `chown` (the one call needing real root) against a tmp `BACKUP_HOME`, covering the success/idempotent-replace/all-four-rejection-classes behaviors plus the `skypane.env.example`/`ci.yml` text assertions. `test_docs.py` asserts the README's corrected claims by text.

## Task Commits

Each task was committed atomically:

1. **Task 1: Phase 32 gate, harden_sshd.sh and provision.sh changes** - `8f1e400` (feat)
2. **Task 2: install-backup-key.sh, SKYPANE_OFFBOX_MARKER, CI shellcheck step** - `335cf4b` (feat)
3. **Task 3: Correct deploy/README.md** - `857313d` (docs)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `deploy/harden_sshd.sh` - New, executable (0755): validated SSH hardening drop-in writer
- `deploy/provision.sh` - Release layout, root-owned env/venv, skypane-backup user, harden_sshd.sh call
- `deploy/tests/test_provision.py` - New: 13 tests
- `deploy/backup/install-backup-key.sh` - New, executable (0755): forced-command-only pull key installer
- `deploy/tests/test_install_backup_key.py` - New: 12 tests
- `deploy/skypane.env.example` - SKYPANE_OFFBOX_MARKER block, corrected header
- `.github/workflows/ci.yml` - New "Shellcheck deploy scripts" step
- `deploy/README.md` - Backups/Restore sections, rewritten deploy flow, corrected env ownership/SSH/ubuntu@
- `deploy/tests/test_docs.py` - New: 9 tests

## Decisions Made
See `key-decisions` in the frontmatter above (drop-in written to its final path before validation, since `sshd -t` only reads installed files; `install-backup-key.sh` intentionally left out of `provision.sh`'s own directory setup so the human-supplied key stays a separately re-runnable step; `devices_cli.py` paths in README.md corrected to the release layout even though not explicitly named in the plan's action text; two explanatory comments reworded to stop tripping this plan's own acceptance grep).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] `deploy/README.md`'s device-enrolment `devices_cli.py` paths were still the old in-place layout**
- **Found during:** Task 3, rewriting the deploy flow section and re-reading the rest of the file for other stale paths.
- **Issue:** All three `devices_cli.py` invocation examples used `/opt/skypane/stub-server/devices_cli.py`, a path Plan 37-06's release-layout switch already made wrong (the code now lives under `/opt/skypane/current/stub-server/` once a deploy has run) — that plan's own SUMMARY explicitly flagged this section as stale and unaddressed.
- **Fix:** Updated all four commands (add/list/remove/revoke-token) to `/opt/skypane/current/stub-server/devices_cli.py`.
- **Files modified:** `deploy/README.md`
- **Verification:** `grep -c "current/stub-server/devices_cli.py" deploy/README.md` returns `4`; `grep -c "/opt/skypane/stub-server/devices_cli.py" deploy/README.md` returns `0`.
- **Committed in:** `857313d` (Task 3 commit)

**2. [Rule 1 - Bug] `install-backup-key.sh`'s header comment tripped its own file's acceptance grep**
- **Found during:** Task 2, running the plan's own acceptance-criteria grep after writing the script.
- **Issue:** `grep -c 'restrict,command="/usr/bin/python3' deploy/backup/install-backup-key.sh` is meant to prove the script's `printf` writes exactly one such line, but the header comment also spelled out the same literal string in prose, making the count `2` instead of the required `1` — the same class of self-tripping-documentation issue 37-04's SUMMARY already documented for its own comments.
- **Fix:** Reworded the header to describe the line's shape ("see the printf below for its exact shape") without repeating the literal substring.
- **Files modified:** `deploy/backup/install-backup-key.sh`
- **Verification:** the grep now returns `1`; `bash -n` still clean; all 12 `test_install_backup_key.py` tests still pass.
- **Committed in:** `335cf4b` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 real staleness bug in README.md prose, 1 comment-wording fix; no script or test behavior changed by either).
**Impact on plan:** None on scope or acceptance criteria — both fixes make the plan's own stated properties (an accurate README, a script whose acceptance grep measures real behavior) actually hold.

## Issues Encountered

**`shellcheck` is not installed in this sandbox** (`command -v shellcheck` finds nothing), matching every prior 37-0N plan's own finding. The new CI step (`.github/workflows/ci.yml`) has not been exercised locally; every `deploy/**/*.sh` file was instead reviewed by hand for the common finding classes shellcheck flags (unquoted expansions inside `[ ]`/`[[ ]]` tests, `local x=$(cmd)` exit-code masking, quoted regex on the right of `=~`, unused variables) — none found, and `bash -n`/`sh -n`-equivalent syntax checks are clean on every script. Per the plan's own instruction, the first real CI run of this step is the authoritative shellcheck result.

Full `./scripts/run-all-tests.sh` run after all three tasks: 975 passed, 6 skipped (3 root-euid permission-bit skips, 3 Playwright/Chromium-unavailable skips), 2 failed — both the pre-existing, sandbox-root-only `test_companion_app`/`test_status_pages` legacy-harness failures already documented by every prior 37-0N plan and `deferred-items.md` (Phase 33 scope, unrelated to this plan's files). Coverage 93.13%, above the 93% floor. `server/.venv/bin/ruff check .` clean.

## User Setup Required

None in this sandbox — every script this plan wrote or changed only touches fake roots, stub binaries, or tmp directories in its own test suite; nothing here has run against the real production VPS. **Operational note carried forward for the developer:** this plan's `provision.sh` is what Plan 37-08 (fresh-VPS provisioning) and Plan 37-09 (the human-supervised production cutover, CP-3 in `37-RESEARCH.md`) will actually run — including the SSH hardening step, which changes a live sshd's accepted authentication methods. Follow the keep-a-session-open discipline this plan's README section now documents (and CP-3's own exact commands) the first time `provision.sh` runs on the real production VPS. `deploy/backup/install-backup-key.sh` similarly waits for CP-8, once the Mac has generated its own keypair.

## Next Phase Readiness
- `deploy/activate.sh`'s prerequisite check (`ENV_FILE`, `VENV/bin/python3`, `BACKUP_ROOT/{archives,pulled}`) is now exactly what this plan's `provision.sh` creates — Plan 37-08's fresh-VPS provisioning run satisfies it directly, no further script change needed.
- `deploy/backup/install-backup-key.sh` is ready for Plan 37-09/37-10's CP-8 checkpoint once the developer's Mac has generated its ed25519 keypair.
- `deploy/README.md`'s "Rehearsal log" table is an explicit placeholder for Plan 37-10 to fill in after the real restore rehearsal.
- No blockers for the rest of Wave A. REQUIREMENTS.md was deliberately left untouched (no SEC-* row marked complete) — this plan proves its scripts against fake roots and stubs, not against the real VPS.

---
*Phase: 37-security-and-operations-hardening*
*Completed: 2026-09-24*

## Self-Check: PASSED

All 9 files claimed as created/modified (`deploy/harden_sshd.sh`,
`deploy/backup/install-backup-key.sh`, `deploy/tests/test_provision.py`,
`deploy/tests/test_install_backup_key.py`, `deploy/tests/test_docs.py`,
`deploy/provision.sh`, `deploy/skypane.env.example`,
`.github/workflows/ci.yml`, `deploy/README.md`) exist on disk. All three
task commits (`8f1e400`, `335cf4b`, `857313d`) are present in
`git log --oneline --all`.
