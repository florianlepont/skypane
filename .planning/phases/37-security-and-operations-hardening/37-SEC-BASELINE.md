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
| skypane-byos.service | 8.3 EXPOSED | 1.5 OK |
| skypane-companion.service | 8.3 EXPOSED | 1.5 OK |
| skypane-poll.service | 8.3 EXPOSED | 1.5 OK |
| skypane-backup.service | — (new) | 0.8 SAFE |

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

Run 2026-09-24 ~20:02 UTC from the laptop with a throwaway local commit
`e6385cd` (companion unit given `--no-such-flag`, never pushed):
- `activate.sh` staged, installed units, swapped `current`, restarted; the
  companion exited with `unrecognized arguments: --no-such-flag`
  (status=2/INVALIDARGUMENT, systemd restart loop) and the probe reported
  `probe failed: unit:skypane-companion.service`.
- `==> Rolling back to releases/e18c5ef…` → `rollback complete`;
  **`deploy-exit=1`** (non-zero, so a CI deploy would be red).
- After: `current` = `releases/e18c5ef923f30428a94fa03df307afc9cd68b9e4`
  (identical to before), byos / companion / poll.timer / caddy all
  `active`, and `grep -c -- --no-such-flag` on the installed companion unit
  = **0** (previous units reinstalled). Throwaway branch deleted locally.
- Cosmetic follow-up: the failure journal tail prints each unit's last 50
  lines regardless of age (the poll timer's go back to August); a
  `--since` bound would make it shorter. The final status line names the
  last probe that ran (`byos-loopback(000000)`, taken during the restart)
  rather than the one that failed first.

## Wave B (CP-11)

Offline score after the Wave B unit change (`systemd-analyze security
--offline=true deploy/skypane-byos.service`, systemd 255.4): **1.3 OK**
(1.5 OK after Wave A; the drop is `IPAddressDeny=any` +
`IPAddressAllow=localhost`). ExecStart now carries `--bind 127.0.0.1` and no
`--secret`.

_Live values pending CP-11 (after the Wave B deploy)._

## Off-box backup pull key (CP-8)

Done 2026-09-24 ~20:10 UTC.
- Dedicated ed25519 key generated on the Mac (`~/.ssh/skypane_backup_ed25519`,
  comment `skypane-backup-pull@mac`); public half installed with
  `install-backup-key.sh` (a first attempt with a mangled pasted line was
  correctly rejected by the key regex; the second was fed from the `.pub` file).
  `/var/lib/skypane-backup/.ssh` 755 root:root, `authorized_keys` 644 root:root.
- `skypane-backup.service` run by hand twice: archives
  `skypane-state-20260924T200545Z.tar.gz` (9 014 744 B) and
  `skypane-state-20260924T200731Z.tar.gz`, each with `.sha256`, mode 640
  `skypane:skypane-backup`. Timer next run 2026-09-25 ~03:17 UTC.
- Journal drift line: `caddy-access-2026-09-12T04-16-18.345-size.log.gz`
  (Caddy's own rotated-log name) — regenerable, now in `KNOWN_EXCLUDED`
  (`caddy-access-*.log*`) so it is no longer reported.
- From the Mac with the pull key: `list` → both archives with size and
  sha256; `cat /opt/skypane/skypane.env` → `backup_gate: unsupported command`
  exit 2; `get ../../../opt/skypane/skypane.env` → `invalid or unknown
  archive` exit 2; no command / no tty → `backup_gate: no command given`
  exit 2. The key can list and fetch archives and nothing else.

## Mac pull agent and Health freshness (CP-9)

Done 2026-09-24 ~20:18 UTC.
- LaunchAgent `com.skypane.backup-pull` installed with
  `install-launchagent.sh`; first run (RunAtLoad, 20:09) fetched and acked
  only the older of the two archives. Root cause: `ssh` inside the
  `while read` loop inherited the loop's stdin (the archive list) and
  swallowed the remaining lines. Fixed with `ssh -n` (PR #116, test fake
  ssh now drains stdin like the real one and reproduced the bug first).
- After reinstalling the fixed script and `launchctl kickstart`: the log
  shows `fetching skypane-state-20260924T200731Z.tar.gz` → `verified` →
  `acked skypane-state-20260924T200731Z.tar.gz` → `completed`; both
  archives present under `~/Library/Application Support/SkyPane/backups/`;
  VPS marker `/var/lib/skypane-backup/pulled/last-pull` =
  `skypane-state-20260924T200731Z.tar.gz`; `last exit code = 0`.
- Companion Health page (FR): card "Sauvegarde hors serveur" green,
  "Sauvegarde hors serveur à jour", "Dernière sauvegarde hors serveur :
  22:07 (il y a 12 min)" — the snapshot time (Paris), not the pull time.

## Restore rehearsal (CP-10)

Done 2026-09-24 by the developer on the Mac: newest pulled archive
`skypane-state-20260924T200731Z.tar.gz` extracted into a `mktemp -d` scratch
directory, `PRAGMA integrity_check` ok, local companion on 127.0.0.1:8650
against that directory showed production flight history, Health, Display
and Device settings, uploaded illustrations and the gallery ("tout est là").
Recorded in `deploy/README.md` → "Rehearsal log". ROADMAP SC-3 met.
