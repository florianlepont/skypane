# deploy — SkyPane VPS deployment

Turns the render pipeline built in 02-01 through 02-04 into an always-on,
internet-reachable server: an OVH VPS-1 running Ubuntu 26.04 LTS, Caddy
terminating TLS in front of `stub-server/byos_server.py`, and a systemd
timer driving `server/poll_loop.py` every 30 seconds. This closes ROADMAP
Phase 2 success criterion 4 — the device polls this real server over HTTPS
instead of a laptop-local stub. Phase 37 hardened the operational side of
this same box: an atomic, self-verifying deploy (`activate.sh`), nightly
off-box backups, systemd sandboxing, and SSH hardening.

**Provider note:** the plan (`02-05-PLAN.md`) and its D-P2-06 decision
specify Hetzner CX22; this deployment instead targets OVH VPS-1, an
equivalent box (2 vCPU / 4 GB RAM / 40 GB NVMe, Ubuntu 26.04, always-on)
at the user's explicit request after a live price/locale comparison — see
`02-05-SUMMARY.md`'s Deviations section. Every script and unit file below
is provider-agnostic (they target "a fresh Ubuntu box reachable over
SSH"); only this README's prose and the one-time human steps changed.

**SSH login note:** production logs in as the non-root `ubuntu` user with
passwordless sudo — current Ubuntu cloud images (including this VPS's
26.04 image) disable direct root SSH login by default, and this project's
own SSH hardening (`deploy/harden_sshd.sh`, SEC-08) sets
`PermitRootLogin no` explicitly on top of that once applied. Every example
below uses `ubuntu@<vps-ip>`; a direct root login will simply be refused
after the SSH hardening step has run.

## What each file does

| File | Purpose |
|------|---------|
| `skypane.env.example` | Template for the real, gitignored `skypane.env` — secrets and per-deployment config, read by systemd as root via `EnvironmentFile=` |
| `skypane-byos.service` | Runs `stub-server/byos_server.py` as the `skypane` user, bound to loopback, `--image-url-scheme https` |
| `skypane-poll.service` / `skypane-poll.timer` | A `Type=oneshot` unit invoking `server/poll_loop.py --once`, fired every 30s by the timer |
| `skypane-companion.service` | Runs `companion/app.py` as the `skypane` user, bound to loopback — the companion configuration web interface (06-11-PLAN.md) |
| `skypane-backup.service` / `.timer` | Nightly (03:15 UTC) oneshot snapshot of `/opt/skypane/state` into `/var/lib/skypane-backup/archives` — see "Backups" below |
| `Caddyfile` | Template for SkyPane's own Caddy site file, `/etc/caddy/sites/skypane.caddy` (site blocks only, imported by the shared host Caddyfile — see "Caddy layout" below). Reverse-proxies the public hostname to `127.0.0.1:8642` (device protocol) and a second hostname to `127.0.0.1:8643` (companion interface; `config-<public-host>` by default, or its own domain), both with Caddy's automatic Let's Encrypt HTTPS and HSTS |
| `render_caddyfile.sh` | The one anchored, hostname-validated renderer `activate.sh` uses to turn `Caddyfile` into `/etc/caddy/sites/skypane.caddy` |
| `provision.sh` | Idempotent first-run setup on a fresh Ubuntu VPS: service user, packages, root-owned venv and `releases/`, `/etc/caddy/sites/`, the `skypane-backup` user/directories, ufw, SSH hardening |
| `harden_sshd.sh` | Writes and validates the `/etc/ssh/sshd_config.d/00-skypane.conf` drop-in (SEC-08); called by `provision.sh`, never with its failure swallowed |
| `deploy.sh` | Ships exactly one git SHA's committed tree (`git archive \| ssh`) to the VPS and runs that release's own `activate.sh` there |
| `activate.sh` | Runs on the VPS as root: stages the release, installs units and SkyPane's Caddy site file (never the shared host Caddyfile), swaps `current` atomically, restarts services, probes every unit and both HTTP(S) surfaces, and rolls back automatically on any failure |
| `backup/skypane_backup.py` | The nightly snapshot job itself (runs as `skypane`, invoked by `skypane-backup.service`) |
| `backup/backup_gate.py` | The forced-command gate (`list` / `get NAME` / `ack NAME`) installed for the `skypane-backup` SSH key |
| `backup/install-backup-key.sh` | Installs the Mac's pull key into `skypane-backup`'s `authorized_keys` with the forced command |
| `backup/mac/skypane-backup-pull.sh` + `install-launchagent.sh` | The Mac-side pull client and its one-command launchd installer |

## One-time human steps (dashboard, no CLI equivalent exists)

These require the OVH Manager web console — a single one-off VPS doesn't
warrant OVH API automation, so this is a plain manual step rather than a
scripted one:

1. In the existing OVH Manager account, order/create a **VPS-1** instance
   (2 vCPU / 4 GB RAM / 40 GB NVMe) with an **Ubuntu** image, in the
   **Gravelines** or **Strasbourg** datacenter.
2. Attach the SSH public key (`~/.ssh/id_ed25519.pub`) at creation time, or
   add it to the instance's SSH keys immediately after if the console
   requires a separate step.
3. Note the server's public IPv4 address once provisioning finishes.
4. Determine the public hostname Caddy will request a certificate for.
   OVH VPS instances get a real, stable public DNS name at
   `vps-<id>.vps.ovh.net` (visible in the OVH Manager or via reverse DNS
   lookup on the IP) — prefer that over the nip.io fallback below, since
   it needs no per-deployment hostname substitution and is a real domain
   from day one. If no such name is available, fall back to the nip.io
   pattern: replace the IP's dots with dashes and append `.nip.io` —
   `203.0.113.10` becomes `203-0-113-10.nip.io` (see `Caddyfile`'s comment
   for how nip.io resolution works). Either way, Caddy just needs *a*
   hostname that already resolves to this VPS's IP for the Let's Encrypt
   HTTP-01 challenge to succeed.
5. Decide the companion interface's hostname. By default `provision.sh`
   uses `config-<public-host>`, which resolves by itself only for a nip.io
   host. With a real DNS name, either create a record for
   `config-<public-host>` or give the companion its own name: an A record
   pointing at the VPS's IPv4 (no AAAA unless it is the VPS's real IPv6,
   or the certificate challenge can fail). Production has used
   `skypane.algernon.ovh` for the companion since 2026-09-23.

No OVH API token or credential is needed anywhere in this flow — the VPS
is created by hand in the console, and everything after that point is
either a script Claude/you run once (`provision.sh`), a script run on
every code change (`deploy.sh`), or one manual file written directly on
the VPS (`skypane.env`, see below) — never a dashboard click.

## First-time provisioning

```bash
scp -r deploy ubuntu@<vps-ip>:/home/ubuntu/deploy
ssh ubuntu@<vps-ip> "sudo /home/ubuntu/deploy/provision.sh <public-host> [<companion-host>]"
```

`<public-host>` is the hostname from step 4 above — either the VPS's real
public DNS name (e.g. `<public-host>`) or a nip.io fallback
(e.g. `203-0-113-10.nip.io`). `<companion-host>` is the name from step 5;
leave it out to get `config-<public-host>`. Production:

```bash
sudo ./deploy/provision.sh <public-host> skypane.algernon.ovh
```

`provision.sh` prepares the machine only — the service user, a root-owned
`releases/` directory and Python venv, the `/etc/caddy/sites/` directory
(root:root 0755), the `skypane-backup` pull user and its directories, ufw,
and the SSH hardening drop-in below. It does **not** install the systemd
units or render SkyPane's Caddy site file: `deploy.sh`'s `activate.sh`
does that on every deploy, so the units and the site file always match whatever code is actually running (see "Ship the code"
below). It never edits the host `/etc/caddy/Caddyfile` either — that file
is shared with other sites (see "Caddy layout" below) — and prints a
reminder instead if the one-time `import sites/*.caddy` line is still
missing. It is idempotent — re-run it after editing `provision.sh` or
`harden_sshd.sh` themselves to apply the change.

## Caddy layout (host Caddyfile shared with other projects)

The VPS's Caddy also serves another project (`cortege.algernon.ovh`,
`cortege-files.algernon.ovh`), so `/etc/caddy/Caddyfile` is **not**
SkyPane's file and no SkyPane script ever writes it:

| Path | Owner | Written by |
|------|-------|-----------|
| `/etc/caddy/Caddyfile` | shared host config: global options, other projects' sites, one `import sites/*.caddy` line | hand-edited by the operator only |
| `/etc/caddy/sites/skypane.caddy` | SkyPane's two site blocks (device + companion) | `activate.sh`, on every deploy |
| `/etc/caddy/sites/.skypane.caddy.prev` | the previous site file, for restore/rollback | `activate.sh` (the leading dot and `.prev` suffix keep it out of the `*.caddy` import glob) |

The host Caddyfile needs exactly one line, added once by hand (a relative
`import` resolves against `/etc/caddy/`; `import /etc/caddy/sites/*.caddy`
works too):

```caddyfile
import sites/*.caddy
```

`activate.sh` refuses to deploy — before touching anything — if that line
or `/etc/caddy/sites/` is missing, with a message pointing here. On every
deploy it renders `sites/skypane.caddy`, and if the result differs from
the file already there it backs up the old one, moves the new one in,
and validates the **whole** host config
(`caddy validate --config /etc/caddy/Caddyfile`). A validation failure
restores the previous site file (or removes the new one if there was
none) and stops before the release swap; Caddy is only reloaded after the
swap, and an unchanged site file means no reload at all.

### One-time migration of an existing host

A host provisioned before this layout still carries SkyPane's two site
blocks inline in `/etc/caddy/Caddyfile`. Migrate it once, by hand, before
the first release-layout deploy:

```bash
ssh ubuntu@<vps-ip>
sudo cp /etc/caddy/Caddyfile /etc/caddy/Caddyfile.pre37    # backup first
sudo install -d -o root -g root -m 0755 /etc/caddy/sites   # provision.sh also does this
sudoedit /etc/caddy/Caddyfile
#   - delete SkyPane's two site blocks (the device host and the companion
#     host, e.g. skypane.algernon.ovh) - leave every other block alone
#   - add the line:  import sites/*.caddy
# Do NOT reload Caddy yet: until activate.sh writes sites/skypane.caddy,
# a reload would drop SkyPane's sites.
```

Then run the first deploy (`deploy/deploy.sh ubuntu@<vps-ip>` or the CI
workflow): `activate.sh` writes `/etc/caddy/sites/skypane.caddy`,
validates the whole host config and reloads Caddy. Afterwards check both
SkyPane and the other project still answer:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://<public-host>/device/v1/display   # expect 401
curl -sI https://cortege.algernon.ovh | head -1   # expect its usual status line
```

To revert the migration, put the old host file back and reload:

```bash
ssh ubuntu@<vps-ip> "sudo cp /etc/caddy/Caddyfile.pre37 /etc/caddy/Caddyfile \
    && sudo rm -f /etc/caddy/sites/skypane.caddy \
    && sudo systemctl reload caddy"
```

The restored `.pre37` file carries SkyPane's blocks inline and no import
line; `skypane.caddy` is removed too so a later re-added import line can
never define the same site addresses twice (Caddy refuses to load that).

**SSH hardening runs as part of this step.** `provision.sh` calls
`harden_sshd.sh`, which writes `/etc/ssh/sshd_config.d/00-skypane.conf`
(`PermitRootLogin no`, password/keyboard-interactive/empty-password
authentication all disabled, `MaxAuthTries 3`), validates the *whole*
resulting configuration with `sshd -t` before reloading anything, and
restores the previous drop-in (or removes a newly-written one) if
validation fails — a bad drop-in is never allowed to reach a running
sshd. Even so, the standard discipline for any live SSH change applies:
**keep your current session open** while you run `provision.sh`, and only
close it after confirming a second session can still log in:

```bash
# Session 1 (keep open): run provision.sh as above.
# Session 2, from your laptop, once provision.sh has finished:
ssh -o PreferredAuthentications=publickey ubuntu@<vps-ip> true && echo LOGIN-OK
ssh -l root <vps-ip> true    # expect: Permission denied (PermitRootLogin no)
sudo sshd -T | grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|maxauthtries) '
```

To change the companion or device hostname later, edit
`SKYPANE_PUBLIC_HOST`/`SKYPANE_COMPANION_HOST` in `/opt/skypane/skypane.env`
on the VPS and run `deploy/deploy.sh ubuntu@<vps-ip>` again — `activate.sh`
re-renders `/etc/caddy/sites/skypane.caddy` from those values and
validates it on every deploy, so there is no SkyPane Caddy config to
hand-edit. Users log in again once,
since the session cookie belongs to the old hostname.

## Write the real env file (once, by hand, on the VPS)

`skypane.env` is never shipped by `deploy.sh`, never committed, and never
leaves the VPS. Create it directly there, root-owned and mode 600 —
systemd reads `EnvironmentFile=` as root, before dropping privileges to
each unit's own `User=`, and no service process reads this file directly
as the `skypane` user (confirmed by grepping every `os.environ` read in
this codebase — SEC-07, D-19):

```bash
ssh ubuntu@<vps-ip>
sudo install -m 600 -o root -g root deploy/skypane.env.example /opt/skypane/skypane.env
sudo nano /opt/skypane/skypane.env   # fill in a real SKYPANE_COMPANION_PASSWORD
                                        # (openssl rand -hex 32), confirm
                                        # SKYPANE_PUBLIC_HOST and SKYPANE_COMPANION_HOST
                                        # match the public hosts above, and set
                                        # SKYPANE_OFFBOX_MARKER=/var/lib/skypane-backup/pulled/last-pull
```

**Companion password:** generate `SKYPANE_COMPANION_PASSWORD` with
`openssl rand -hex 32`. It is the single shared password gating the
companion configuration web interface (D-01/D-02) — there are no
per-user accounts — and is written by hand on the VPS only, same
discipline as every other secret in this file.

Device enrolment no longer has a secret to fill in here — see the next
section.

## Device enrolment (per-device secret)

Each frame carries its own enrolment secret in flash, never a value
shared across devices. This VPS stores only the SHA-256 hash of that
secret, in a small registry file (`devices.json` in
`${SKYPANE_STATE_DIR}`), managed with `stub-server/devices_cli.py`.
`POST /device/v1/setup` issues a fresh bearer token only when the MAC
is registered and the presented secret hashes to the value on file; a
wrong secret (including a stale shared one, or another device's) is
refused and the device's existing token keeps working.

1. **Provision a frame.** Connect it over USB and run
   `firmware/provision.sh <serial-port>` — it generates a random secret,
   writes it into the device's flash, and prints the frame's MAC and the
   secret's SHA-256 hash.

2. **Register it on the VPS**, using the MAC and hash `provision.sh`
   just printed:

   ```bash
   ssh <ssh-target> "sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/devices_cli.py --state-dir /opt/skypane/state add --mac <mac> --secret-sha256 <hash>"
   ```

   Takes effect immediately — `byos_server.py` re-reads the registry on
   every setup request, so no restart is needed.

3. **List or remove devices** the same way:

   ```bash
   ssh <ssh-target> "sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/devices_cli.py --state-dir /opt/skypane/state list"
   ssh <ssh-target> "sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/devices_cli.py --state-dir /opt/skypane/state remove --mac <mac>"
   ```

4. **Force a re-enrolment** (e.g. a suspected leaked token) with
   `revoke-token`. Stop `skypane-byos` first — the running process keeps
   tokens in memory and would otherwise overwrite the edit with its own
   copy on its next write — then start it again after:

   ```bash
   ssh <ssh-target> "sudo systemctl stop skypane-byos && sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/devices_cli.py --state-dir /opt/skypane/state revoke-token --mac <mac> && sudo systemctl start skypane-byos"
   ```

   The frame re-enrols with its own secret on its next wake, with no
   reflash and no other operator action.

## Ship the code

From your laptop, from the repository root:

```bash
deploy/deploy.sh ubuntu@<vps-ip>
```

Re-run this any time `server/`, `stub-server/`, `companion/`, `deploy/`, or
`adsb-test/runway3.json` changes. `deploy.sh` ships exactly the committed
tree at the current git SHA (`git archive`, no local edits, no untracked
files, never `state/`, `.venv/` or `skypane.env`) into
`/opt/skypane/releases/.incoming-<sha>/` and then runs that release's own
`deploy/activate.sh <sha>` on the VPS as root, which does everything else:

- Stages the release into `/opt/skypane/releases/<sha>/` (root-owned,
  read-only to everyone else), byte-compiles it, and re-installs
  `server/requirements.txt` only if its hash changed since the last
  deploy.
- Renders SkyPane's own site file, `/etc/caddy/sites/skypane.caddy`, from
  `SKYPANE_PUBLIC_HOST`/`SKYPANE_COMPANION_HOST` in `skypane.env`,
  validates the whole host config with it (`caddy validate`) and installs
  every `deploy/skypane-*.service`/`.timer` unit — **units and the site
  file are installed on every deploy**, not just the first one,
  so they can never silently drift from the code that shipped them.
- Atomically swaps `/opt/skypane/current` (a symlink) to point at the new
  release and restarts `skypane-byos`/`skypane-companion`/
  `skypane-poll.timer`.
- Probes every unit's `systemctl is-active` state plus a loopback and an
  HTTPS-through-Caddy request for both the device and companion
  endpoints (checking for the `Strict-Transport-Security` header too).
  If any probe fails within 30 seconds, it automatically swaps `current`
  back to the previous release, reinstalls that release's units, restores
  the previous `sites/skypane.caddy` (the host Caddyfile is never
  touched), restarts and re-probes, prints the failing unit's last 50
  journal lines, and exits non-zero — so a bad deploy never leaves the
  broken code running, and the CI job goes red.
- Prunes old releases, keeping the 5 most recent (`current` and the
  previous release are never pruned, even if that leaves more than 5).
- Before any of the above, checks that `deploy/provision.sh` has already
  run on this box (`skypane.env` exists, the venv has a `python3`, and
  `/var/lib/skypane-backup/{archives,pulled}` exist) and that the host
  Caddyfile carries the `import sites/*.caddy` line with
  `/etc/caddy/sites/` present — refusing to touch anything if not.

**Manual rollback:** normally you don't need one — a failing deploy rolls
itself back automatically. To deliberately revert to an already-deployed,
already-probed-good release (for example, a behavioural regression only
noticed after a deploy that itself probed fine), point `current` at it
directly and restart:

```bash
ssh ubuntu@<vps-ip> 'ls -1t /opt/skypane/releases | head -5'   # pick the sha to roll back to
ssh ubuntu@<vps-ip> "sudo ln -sfn releases/<previous-sha> /opt/skypane/current \
    && sudo systemctl restart skypane-byos skypane-companion skypane-poll.timer"
```

## Backups

A nightly systemd timer (`skypane-backup.timer`, 03:15 UTC,
`skypane-backup.service` running as `skypane`) archives
`/opt/skypane/state` into `/var/lib/skypane-backup/archives/`. It takes a
consistent online copy of `history.db` with SQLite's own backup API
(never a raw copy of the live `-wal`/`-shm` files), and copies everything
else that cannot be regenerated from an **include list** — device
tokens, device/colour/calendar/manual-resolution config, the calendar
secret, uploaded illustration overrides, the poll enrichment cache, and
`gallery/` (the last ~25 rendered panels — kept for the visual history,
per D-24). Regenerable files (`panel.bin`, theme preview caches, Caddy's
access log) are excluded. An unlisted top-level file in `state/` is
logged as drift rather than silently skipped or silently included. Each
run writes a checksummed `skypane-state-<UTC timestamp>.tar.gz` and keeps
the newest 14 on the VPS.

**The off-box copy is pulled, not pushed.** A dedicated `skypane-backup`
system user (never a member of the `skypane` group, so it can never write
live state) authenticates only through one SSH key restricted to a forced
command (`deploy/backup/backup_gate.py`, installed via
`deploy/backup/install-backup-key.sh`) that answers exactly three verbs —
`list`, `get NAME`, `ack NAME` — over the archives directory. It is not
rsync: a small, self-auditable Python dispatcher is easier to reason
about than trusting an rsync server-arguments allow-list (`rrsync`) with
an rsync client whose exact protocol behaviour on macOS is unverified.

Your Mac pulls nightly via a launchd LaunchAgent
(`deploy/backup/mac/install-launchagent.sh <user@host> <private-key-path>`,
installed once — see "Restore" below for the full checkpoint). It fetches
only archives it doesn't already have, verifies each against the checksum
the gate reported, keeps the 30 newest plus one per calendar month for 12
months, and acknowledges the newest successfully verified archive — which
writes `/var/lib/skypane-backup/pulled/last-pull` on the VPS, the
freshness marker `SKYPANE_OFFBOX_MARKER` in `skypane.env` points at.
Useful commands: `launchctl kickstart -k gui/$(id -u)/com.skypane.backup-pull`
to run it immediately, and `tail -f ~/Library/Logs/skypane-backup-pull.log`
to watch it.

The companion Health page reads that marker and shows "last off-box
backup N ago", turning into a warning once the archive's own snapshot
timestamp is more than 3 days old, or if no pull has ever happened.

## Restore

**Rehearsal (do this once, on the Mac, into a scratch directory — never
against your live state):**

```bash
SCRATCH=$(mktemp -d)
tar -xzf ~/Library/Application\ Support/SkyPane/backups/<newest>.tar.gz -C "$SCRATCH"
python3 -c "import sqlite3,sys; print(sqlite3.connect(sys.argv[1]).execute('PRAGMA integrity_check').fetchone())" "$SCRATCH/history.db"
# expect: ('ok',)
SKYPANE_COMPANION_PASSWORD=rehearsal SKYPANE_COMPANION_INSECURE_COOKIES=1 \
    server/.venv/bin/python3 companion/app.py --port 8650 --state-dir "$SCRATCH"
# open http://127.0.0.1:8650 - Flights and Health should show production
# history, Display and Device should show production settings.
```

**Production restore** (documented here; only run this for real if the
VPS's own state is actually lost or corrupted):

1. `sudo systemctl stop skypane-poll.timer skypane-poll.service skypane-companion skypane-byos`
2. `sudo mv /opt/skypane/state /opt/skypane/state.broken-<date>`
3. `sudo install -d -o skypane -g skypane -m 2775 /opt/skypane/state`
4. `sudo tar -xzf <archive> -C /opt/skypane/state`
5. `sudo chown -R skypane:skypane /opt/skypane/state`
6. Recreate `/opt/skypane/skypane.env` from the password manager if the
   box itself was lost, not just its state (root:root 0600, see above).
7. `sudo systemctl start skypane-byos skypane-companion skypane-poll.timer`,
   then confirm with the "Verifying the deployment" checks below (the
   same probes `activate.sh` runs on every deploy).

### Rehearsal log

| Date | Archive | Result |
|------|---------|--------|
| 2026-09-24 | skypane-state-20260924T200731Z.tar.gz | integrity_check ok; restored into a scratch dir on the Mac and served by a local companion: flight history, Health, Display/Device settings, uploaded illustrations and the gallery all present. No gap found. |

## Verifying the deployment

```bash
# From outside the VPS (your laptop): TLS + auth gate.
# 401 is the correct, expected result without a bearer token - it proves
# both a valid TLS handshake happened and the auth gate is active.
curl -sI https://<public-host>/device/v1/display

# The app port must NOT be reachable directly (ufw denies it):
curl -sI --connect-timeout 3 http://<vps-ip>:8642/device/v1/display   # expect: refused or timeout

# On the VPS: timer is active and cycling.
ssh ubuntu@<vps-ip> systemctl is-active skypane-poll.timer
ssh ubuntu@<vps-ip> journalctl -u skypane-poll -n 20

# On the VPS: Caddy is terminating TLS and proxying correctly.
ssh ubuntu@<vps-ip> journalctl -u caddy -n 20

# The companion interface answers over TLS on its own hostname, and an
# unauthenticated request redirects to the login page rather than serving
# content (302/303 to /login, not 200):
curl -sI https://<companion-host>/ | head -1

# The companion port must NOT be reachable directly either (ufw denies it,
# same as the app port above):
curl -sI --connect-timeout 3 http://<vps-ip>:8643/   # expect: refused or timeout
```

### Assumption A3 (Caddy log field nesting) — confirmed 2026-08-28

`server/history_db.py`'s battery-log tailer assumes Caddy's JSON access log
nests request headers at `request.headers.<Header-Name>` (a list of
strings). Confirmed against a real captured line on the live host
(`request.headers` includes `"X-Battery-Mv":["4010"]` exactly as read) —
no correction needed to the extraction logic.

What *did* need fixing, found during this same live pass: the log file
itself was unreadable by the process that needs to read it. Caddy's
default file mode is owner-only (`caddy` user), while `server/poll_loop.py`
runs as the `skypane` user — and separately, nothing in production ever
called `history_db.ingest_caddy_battery_log()` at all (built and
unit-tested in plan 06-01, never wired to a caller). Both are fixed: the
log's `mode 660` directive plus `provision.sh`'s `caddy` → `skypane` group
membership and setgid on `state/` make it group-writable *and*
group-readable regardless of which of the two users last touched it, and
`server/poll_loop.py --caddy-log` now ingests on every cycle. Verified live:
real `device_health` rows with plausible millivolt values are landing in
the deployed database.

## Reading logs

```bash
ssh ubuntu@<vps-ip> journalctl -u skypane-poll -f       # follow the poll cycle live
ssh ubuntu@<vps-ip> journalctl -u skypane-byos -f       # follow device requests live
ssh ubuntu@<vps-ip> journalctl -u skypane-companion -f  # follow companion interface activity live
ssh ubuntu@<vps-ip> journalctl -u caddy -f               # follow TLS/proxy activity live

# Which ICAO prefixes has the panel failed to name recently, and how often
# (within journald's retention window)?
ssh ubuntu@<vps-ip> journalctl -u skypane-poll | grep -o 'unknown_prefix=[A-Z]\{3\}' | sort | uniq -c | sort -rn

# The same question, answered from the durable record instead - survives
# past journald's retention window (quick task 260827-oz9). Streams
# poll_state.json off the VPS and reads its unresolved_prefixes key,
# sorted by count (most-recurring first); count is per poll cycle, not per
# distinct flight. Uses python3, not jq - the VPS is provisioned with a
# Python interpreter because it runs the poll loop, and jq is not in
# provision.sh's install list.
ssh ubuntu@<vps-ip> cat /opt/skypane/state/poll_state.json | python3 -c "import json, sys; reg = json.load(sys.stdin).get('unresolved_prefixes', {}); [print(prefix, e.get('count'), e.get('first_seen'), e.get('last_seen'), e.get('example_callsign')) for prefix, e in sorted(reg.items(), key=lambda kv: -kv[1].get('count', 0))]"
```

A prefix appearing repeatedly is a carrier serving this airport the panel
cannot yet name; the fix is to confirm it against a real callsign via
adsbdb and add a row to the airline-prefix table in `server/plane/enrich.py`,
following that table's existing sourcing discipline. Remember the count is
poll cycles, not distinct flights — an aircraft held on the runway across
several cycles inflates the number for that one arrival.

## Known vendored behaviour: byos_server.py binds 0.0.0.0

`stub-server/byos_server.py` hardcodes `ThreadingHTTPServer(("0.0.0.0", ...))`
— it does not itself restrict to loopback. This repository deliberately
does not patch that (see `stub-server/VENDOR.md`'s minimal-diff discipline);
instead the loopback restriction is enforced at the network layer:
`ufw deny 8642/tcp` (plus ufw's own default-deny-incoming policy) blocks any
external connection to the app port, and Caddy is the only process
forwarding traffic to it, from `127.0.0.1`. The net effect is the same as
if the app bound loopback only — verified by the "external request to the
app port is refused or times out" acceptance criterion.

## Rolling back

See "Ship the code" above: `activate.sh` already rolls a *failing* deploy
back to the previous release automatically, and prints the manual command
for deliberately reverting to an older, already-working release. Code and
configuration are reproducible from this repository at any commit — but
`/opt/skypane/state` (flight history, device tokens, settings, uploaded
illustrations, `gallery/`) is not, which is exactly why it is backed up
nightly and pulled off-box (see "Backups" and "Restore" above).

## Secrets discipline

No cloud-provider API token is used in this flow (the OVH VPS is created
by hand in the console — see the one-time human steps above). Each
frame's enrolment secret lives only in that frame's own flash; this VPS
stores only its SHA-256 hash, in `devices.json` under
`${SKYPANE_STATE_DIR}`. `skypane.env.example` carries placeholders only
for what remains a real secret there (`SKYPANE_COMPANION_PASSWORD`); the
real `skypane.env` is root:root 0600, gitignored (`deploy/.gitignore`),
and lives solely on the VPS, same as `devices.json`. The `skypane-backup`
pull key is restricted by its forced command to `list`/`get`/`ack` over
the archives directory only — it can never read `skypane.env` or open a
shell (see "Backups" above). Before any commit touching this directory,
confirm `git status --porcelain` shows no real env file, private key, or
token staged, and that `git log -p` for the commit contains no secret
value.
