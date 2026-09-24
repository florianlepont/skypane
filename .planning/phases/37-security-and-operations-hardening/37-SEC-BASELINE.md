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
| permitrootlogin | prohibit-password | |
| passwordauthentication | **yes** | |
| kbdinteractiveauthentication | no | |
| pubkeyauthentication | yes | |
| maxauthtries | 6 | |

Before: `/etc/ssh/sshd_config.d/` holds `50-cloud-init.conf` (root 600) and
`60-cloudimg-settings.conf`. Password authentication is **on** in production
despite `provision.sh`'s old `sed` on the main `sshd_config`: sshd keeps the
first value it reads, and the cloud-init drop-in is read first (the SEC-08
finding, confirmed live). `00-skypane.conf` sorts before it and fixes this.

## skypane.env ownership before/after

| Path | Before (CP-1) | After (CP-3) |
|------|---------------|--------------|
| /opt/skypane | 750 skypane:skypane | |
| /opt/skypane/skypane.env | not read (stat ran without sudo) | |
| /opt/skypane/venv | not read (stat ran without sudo) | |

## GitHub deploy target (CP-2)

Done 2026-09-24 by the developer: `DEPLOY_SSH_TARGET` set to `ubuntu@<vps>` as an
**environment secret of `production`** (the environment page lists only that
one secret; the key and host-key secrets resolve from elsewhere, as the
successful 2026-09-23 12:20 deploy proves). Protection rules: **Required
reviewers = florianlepont**, no wait timer, administrators cannot bypass.

## Services under sandbox (CP-4)

_Pending CP-4 (Plan 37-09)._

## Deliberate failed deploy (CP-5)

_Pending CP-5 (Plan 37-09)._

## Wave B (CP-11)

_Pending CP-11 (Plan 37-11, after Phase 36)._
