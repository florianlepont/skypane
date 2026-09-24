---
phase: 37-security-and-operations-hardening
plan: 08
subsystem: infra
tags: [production, checkpoint, baseline, ssh, provisioning]
requires:
  - phase: 37-security-and-operations-hardening (Plans 37-01..37-07)
    provides: hardened units, activate.sh, provision.sh, harden_sshd.sh
provides:
  - "37-SEC-BASELINE.md: CP-1 before values, CP-2 deploy target, CP-3 provision results"
affects: [37-09, 37-10]
key-files:
  created: [.planning/phases/37-security-and-operations-hardening/37-SEC-BASELINE.md]
  modified: [deploy/activate.sh, deploy/provision.sh, deploy/README.md (via PR #114)]
requirements-completed: [SEC-07, SEC-08]
completed: 2026-09-24
---

# Plan 37-08 summary: production preflight (CP-1..CP-3)

All three checkpoints were run by the developer on 2026-09-24; every value is
recorded in `37-SEC-BASELINE.md`.

- **CP-1 baseline:**
  - Online `systemd-analyze security` score was 8.3 EXPOSED for byos, companion and poll.
  - `passwordauthentication yes` was live in production, because cloud-init's `50-` drop-in won over `provision.sh`'s old `sed`. This confirmed the SEC-08 finding.
  - **Blocker found:** `/etc/caddy/Caddyfile` is shared with another project (cortege). `activate.sh` would have overwritten it.
  - Fixed in PR #114 (developer decision, D-11 deviation). SkyPane now owns only `/etc/caddy/sites/skypane.caddy`, which the host file imports with `import sites/*.caddy`. The host Caddyfile is validated but never written.
- **CP-2:**
  - `DEPLOY_SSH_TARGET` = `ubuntu@<vps>`, stored as a `production` environment secret.
  - Required reviewer: florianlepont.
- **CP-3:**
  - `provision.sh` ran to completion.
  - `skypane.env` is now 600 root:root; venv and releases are root-owned.
  - The `skypane-backup` user and its directories exist; the user is not in the `skypane` group.
  - `sshd -T` now reports `permitrootlogin no`, `passwordauthentication no` and `maxauthtries 3`.
  - A second session logged in as `ubuntu`; `root` was refused.

## Deviations
- **Shared host Caddyfile:** handled as above (PR #114), with tests proving the host file stays byte-identical across a deploy and a rollback.
- **CP-1 stat lines:** they ran without `sudo`, so `skypane.env` and venv ownership before CP-3 went unrecorded. The after values are recorded.
