---
phase: 37-security-and-operations-hardening
plan: 10
subsystem: infra
tags: [backup, off-box, launchd, restore, production, checkpoint]
requires:
  - phase: 37-security-and-operations-hardening (Plans 37-04, 37-07, 37-09)
    provides: snapshot job, forced-command gate, key installer, Mac pull script, release layout
provides:
  - "Nightly off-box backups pulled by the developer's Mac, freshness on Health, restore rehearsed and documented"
key-files:
  modified:
    - deploy/README.md
    - deploy/backup/mac/skypane-backup-pull.sh
    - deploy/backup/skypane_backup.py
    - deploy/tests/test_mac_pull.py
    - deploy/tests/test_backup.py
requirements-completed: [SEC-04]
completed: 2026-09-24
---

# Plan 37-10 summary: off-box backup in service, restore rehearsed (CP-8..CP-10)

- **CP-8:**
  - A dedicated ed25519 pull key was installed with a forced command; `authorized_keys` is 644 root:root.
  - The first snapshots are 9 MB archives with `.sha256` files, mode 640.
  - The nightly timer is scheduled.
  - From the Mac, `list` works. Reading `skypane.env` is refused, path traversal is refused, and so is a shell. All three exit with code 2.
- **CP-9:**
  - LaunchAgent `com.skypane.backup-pull` is installed.
  - Both archives were pulled, verified and acked, and the VPS marker holds the newest name.
  - The Health card "Sauvegarde hors serveur" is green with the snapshot time.
- **CP-10:**
  - The newest archive was restored into a scratch directory on the Mac. `integrity_check` returned ok.
  - A local companion showed production history, settings, illustrations and gallery.
  - This is recorded in `deploy/README.md` → "Rehearsal log", which meets ROADMAP SC-3.

## Bugs found in production and fixed (PR #116)
1. **`ssh` in the pull loop read the loop's stdin**, which is the archive list. Only the first archive was fetched, and the older one was acked.
   - Fixed with `ssh -n`.
   - The test fake `ssh` now drains stdin unless `-n` is passed, like real ssh does. It reproduced the bug before the fix.
2. **Caddy's rotated access logs** (`caddy-access-<timestamp>.log.gz`) were reported as drift. They are now listed in `KNOWN_EXCLUDED`.

## Notes
- The "-L port forwarding refused" negative test was not run. `authorized_keys` uses `restrict`, which disables forwarding.
- Under zsh, the `K="-i … -o …"` variable does not word-split. The checkpoint commands were rewritten with explicit options.
