---
phase: 37-security-and-operations-hardening
plan: 09
subsystem: infra
tags: [production, checkpoint, cutover, rollback, systemd-analyze]
requires:
  - phase: 37-security-and-operations-hardening (Plan 37-08)
    provides: provisioned VPS
provides:
  - "Production on the release layout with hardened units; rollback proven live; after-scores recorded"
affects: [37-10, 37-11]
requirements-completed: [SEC-01, SEC-02, SEC-03, SEC-05]
completed: 2026-09-24
---

# Plan 37-09 summary: cutover, failed-deploy proof, after-scores (CP-4..CP-6)

- **CP-4 cutover (2026-09-24 ~19:55 UTC):**
  - Host Caddyfile migrated once: backed up to `Caddyfile.pre37`, then reduced to `import sites/*.caddy` plus the unchanged cortege blocks.
  - CI deploy of `e18c5ef` approved; it went green. `current` → `releases/e18c5ef…`.
  - All five units active.
  - Companion listens on `127.0.0.1:8643` only (`--bind 127.0.0.1`).
  - HSTS is present on both hosts.
  - A cross-origin POST to `/login` gets 403.
  - Poll cycles run fine under the sandbox.
  - Cortege health endpoints return 200.
  - The developer confirmed in the browser: login, Poll now, saving a setting, theme preview and Health.
- **CP-5:**
  - A local throwaway commit made the companion fail at start.
  - `activate.sh` detected the failed probe, rolled back to `e18c5ef` and exited with `deploy-exit=1`.
  - The previous units were reinstalled (`--no-such-flag` count 0), and all services were active afterwards.
  - This meets ROADMAP SC-4.
- **CP-6:** online scores went 8.3 → **1.5 OK** for byos, companion and poll; skypane-backup scores **0.8 SAFE**. This meets the "before/after" part of SC-5.

## Follow-ups (cosmetic, not blocking)
- The failure journal tail prints each unit's last 50 lines regardless of age; a `--since` bound would shorten it.
- `activate.sh`'s final status line names the last probe that ran, not the first one that failed.
- `curl -I` returns 501: the stdlib servers do not implement HEAD. GET is what the device and browsers use.
