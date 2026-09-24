# Phase 37 — security baseline and before/after record

Single record for every before/after value the Phase 37 checkpoints produce
(ROADMAP SC-5, D-17). No secret value is ever written here.

Code state measured: branch `claude/plan-phase-37` at `b8d74fd` (plans 37-01..37-07 executed).
Pre-phase units: `deploy/skypane-*.service` at `9d38c21` (main before Phase 37).

## Offline scores (CI tool, systemd 255)

`systemd-analyze security --offline=true <unit>` (systemd 255.4), lower is better.

| Unit | Before | After |
|------|--------|-------|
| skypane-byos.service | 8.3 EXPOSED | 1.5 OK |
| skypane-companion.service | 8.3 EXPOSED | 1.5 OK |
| skypane-poll.service | 8.3 EXPOSED | 1.5 OK |
| skypane-backup.service | — (new) | 0.8 SAFE |

## Online scores on the VPS

`sudo systemd-analyze security <unit>` on production.

| Unit | Before (CP-1) | After (CP-6) |
|------|---------------|--------------|
| skypane-byos.service | 8.3 EXPOSED | |
| skypane-companion.service | 8.3 EXPOSED | |
| skypane-poll.service | 8.3 EXPOSED | |
| skypane-backup.service | — (new) | |

## Live Caddyfile diff (CP-1)

Recorded 2026-09-24. **Blocker found:** `/etc/caddy/Caddyfile` on the VPS is
shared with another project. Besides SkyPane's two site blocks
(`vps-1440bce3.vps.ovh.net` → 127.0.0.1:8642 and `skypane.algernon.ovh` →
127.0.0.1:8643, rendered from an older template, no HSTS yet) it serves
`cortege.algernon.ovh` (→ 127.0.0.1:3000) and `cortege-files.algernon.ovh`
(→ 127.0.0.1:9000, `request_body max_size 50MB`). Deploying the whole file
from `deploy/Caddyfile` would take cortege down.

Decision (developer, 2026-09-24): SkyPane owns only its own site file,
`/etc/caddy/sites/skypane.caddy`, imported by the host Caddyfile through one
`import sites/*.caddy` line; the host Caddyfile itself is never written by a
SkyPane deploy.

Live hostnames from `skypane.env`: `SKYPANE_PUBLIC_HOST=vps-1440bce3.vps.ovh.net`,
`SKYPANE_COMPANION_HOST=skypane.algernon.ovh`, ports 8642/8643.
`sudo -n true` works for `ubuntu` (SUDO-OK).

## sshd -T before/after

| Directive | Before (CP-1) | After (CP-3) |
|-----------|---------------|--------------|
| permitrootlogin | prohibit-password | no |
| passwordauthentication | **yes** | no |
| kbdinteractiveauthentication | no | no |
| pubkeyauthentication | yes | yes |
| maxauthtries | 6 | 3 |

Before: `/etc/ssh/sshd_config.d/` holds `50-cloud-init.conf` (root 600) and
`60-cloudimg-settings.conf`. Password authentication is **on** in production
despite `provision.sh`'s old `sed` on the main `sshd_config`: sshd keeps the
first value it reads, and the cloud-init drop-in is read first (the SEC-08
finding, confirmed live). `00-skypane.conf` sorts before it and fixes this.

## skypane.env ownership before/after

| Path | Before (CP-1) | After (CP-3) |
|------|---------------|--------------|
| /opt/skypane | 750 skypane:skypane | 750 root:skypane |
| /opt/skypane/skypane.env | not read (stat ran without sudo) | 600 root:root |
| /opt/skypane/venv | not read (stat ran without sudo) | 755 root:root |

CP-3 (2026-09-24): `provision.sh` ran to completion with session 1 open.
`sshd -t` passed; a second session as `ubuntu@` logged in (`LOGIN-OK`) and
`root@` was refused (`Permission denied (publickey)`). Also after CP-3:
`releases/` 755 root:root, `archives/` 2750 skypane:skypane-backup,
`pulled/` 755 skypane-backup:skypane-backup, `skypane-backup` not in group
`skypane`, `SKYPANE_OFFBOX_MARKER` present once in `skypane.env`, byos /
companion / poll.timer / caddy all `active`.

## GitHub deploy target (CP-2)

Done 2026-09-24 by the developer: `DEPLOY_SSH_TARGET` set to `ubuntu@<vps>` as an
**environment secret of `production`** (the environment page lists only that
one secret; the key and host-key secrets resolve from elsewhere, as the
successful 2026-09-23 12:20 deploy proves). Protection rules: **Required
reviewers = florianlepont**, no wait timer, administrators cannot bypass.

## Services under sandbox (CP-4)

Cutover done 2026-09-24 (~19:55 UTC) by approving the CI deploy of main
`e18c5ef` (green). Before it, the shared host Caddyfile was migrated once:
backup `/etc/caddy/Caddyfile.pre37`; new host file = `import sites/*.caddy` +
the two unchanged cortege blocks (SkyPane's two inline blocks removed).

After the deploy:
- `skypane-byos`, `skypane-companion`, `skypane-poll.timer`, `caddy`,
  `skypane-backup.timer`: all `active`.
- Ports: companion `127.0.0.1:8643` only (`--bind 127.0.0.1` in its argv);
  byos still `0.0.0.0:8642` (Wave B).
- HSTS `max-age=31536000` on both hosts. (`curl -I` returns 501: the stdlib
  servers do not implement HEAD; GET is what the device and browsers use.)
- Cross-origin `POST /login` with `Origin: https://evil.example` → **403**.
- Poll cycles every 30 s complete under the sandbox (`Deactivated
  successfully`); current state `hold_state=battery_empty` — the frame's own
  battery is flat, unrelated to the cutover.
- `/etc/caddy/sites/` holds only `skypane.caddy`; cortege still answers
  (`cortege` 404 / `cortege-files` 400 from the apps themselves, no 502).
- Browser checks confirmed by the developer: login, Poll now, save a
  setting, theme preview, Health (off-box card shows "never" in warn, as
  expected before CP-8/CP-9); cortege opens normally.
- `readlink /opt/skypane/current` (with sudo) =
  `/opt/skypane/releases/e18c5ef923f30428a94fa03df307afc9cd68b9e4`; GET
  `https://<device-host>/device/v1/display` → 401, GET
  `https://skypane.algernon.ovh/login` → 200.
- Cortege health checked from outside: `https://cortege.algernon.ovh/v1/health`
  → 200 `{"status":"ok","service":"cortege-api"}`,
  `https://cortege-files.algernon.ovh/minio/health/live` → 200.
- No hardening directive had to be reverted.

## Deliberate failed deploy (CP-5)

_Pending CP-5 (Plan 37-09)._

## Wave B (CP-11)

_Pending CP-11 (Plan 37-11, after Phase 36)._
