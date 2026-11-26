# deploy — SkyPane VPS deployment

Turns the render pipeline built in 02-01 through 02-04 into an always-on,
internet-reachable server: an OVH VPS-1 running Ubuntu 26.04 LTS, Caddy
terminating TLS in front of `stub-server/byos_server.py`, and a systemd
timer driving `server/poll_loop.py` every 30 seconds. This closes ROADMAP
Phase 2 success criterion 4 — the device polls this real server over HTTPS
instead of a laptop-local stub. Phase 37 hardened the operational side of
this same box: an atomic, self-verifying deploy (`activate.sh`), nightly
off-box backups, systemd sandboxing, and SSH hardening.

**Provider note:** the original plan and its D-P2-06 decision specify
Hetzner CX22; this deployment instead targets OVH VPS-1, an equivalent
box (2 vCPU / 4 GB RAM / 40 GB NVMe, Ubuntu 26.04, always-on) at the
user's explicit request after a live price/locale comparison. Every
script and unit file below is provider-agnostic (they target "a fresh
Ubuntu box reachable over SSH"); only this README's prose and the
one-time human steps changed.

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
| `skypane-companion.service` | Runs `companion/app.py` as the `skypane` user, bound to loopback — the companion configuration web interface |
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
   `skypane.algernon.is` for the companion since 2026-09-23.

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
sudo ./deploy/provision.sh <public-host> skypane.algernon.is
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

The VPS's Caddy also serves another project (`cortege.algernon.is`,
`cortege-files.algernon.is`), so `/etc/caddy/Caddyfile` is **not**
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
#     host, e.g. skypane.algernon.is) - leave every other block alone
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
curl -sI https://cortege.algernon.is | head -1   # expect its usual status line
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
sudo nano /opt/skypane/skypane.env   # fill in the SKYPANE_AUTH0_* values, confirm
                                        # SKYPANE_PUBLIC_HOST and SKYPANE_COMPANION_HOST
                                        # match the public hosts above, and set
                                        # SKYPANE_OFFBOX_MARKER=/var/lib/skypane-backup/pulled/last-pull
```

**Companion sign-in:** Auth0 is the only sign-in and is required: the
companion refuses to start without all three `SKYPANE_AUTH0_*` variables
(see "Sign-in (Auth0)"). Secrets are written by hand on the VPS only, same
discipline as every other secret in this file.

**Upgrade note:** an existing `skypane.env` that still contains
`SKYPANE_COMPANION_PASSWORD` or `SKYPANE_LEGACY_PASSWORD_LOGIN` keeps
working. Both are ignored and can be deleted at leisure.

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

## Fleet database

Users, locations and devices live in `fleet.db` (SQLite, WAL) in the state
directory, mode 0600, owned by `skypane`. It is created and filled by
`server/fleet_migrate.py`, which `deploy/activate.sh` runs on every deploy
after an automatic backup and a `--dry-run`, before the symlink swap. The
migration never runs at service start.

- **Bootstrap.** The first migration needs the administrator's email.
  Add `SKYPANE_BOOTSTRAP_ADMIN_EMAIL=<address>` to `/opt/skypane/skypane.env`
  once, before the first deploy that carries the fleet database. This is
  the only manual step; without it the dry-run exits 2 and the deploy stops
  with a message saying so. The value is validated before anything changes
  and is ignored once the database is migrated.
- **Idempotent.** `python3 -m server.fleet_migrate --state-dir
  /opt/skypane/state [--owner-email <address>] --dry-run` reports what
  would change and writes nothing; running the real migration twice leaves
  the database as it was.
- **Expand only.** The legacy `devices.json` and `byos_state.json` are never
  modified or removed by the migration and stay valid, so rolling back to
  the previous release works. A later roll-forward reconciles anything
  that was written only to the legacy files in the meantime.
- **Pending frames are skipped.** A legacy MAC that is already a pending
  (or retired) frame in `fleet.db` is not imported as a device, since the
  pairing flow owns it; the migration prints `skip device <mac>: already a
  pending frame`. Once the frame is paired it is an ordinary device.
- **Operator tool.** `stub-server/fleet_cli.py` manages the database:

  ```bash
  FLEET="sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/fleet_cli.py --state-dir /opt/skypane/state"
  ssh <ssh-target> "$FLEET users add --email someone@example.org --role user"
  ssh <ssh-target> "$FLEET users list"
  ssh <ssh-target> "$FLEET locations add --name 'Orly east' --latitude 48.72 --longitude 2.38 --timezone Europe/Paris"
  ssh <ssh-target> "$FLEET devices add --mac <mac> --secret-sha256 <hash> --owner-email someone@example.org --location-id <id>"
  ssh <ssh-target> "$FLEET devices list"
  ssh <ssh-target> "$FLEET hardware list"
  ```

  `devices assign`, `set-location`, `remove`, `revoke-token` and
  `users disable|enable` complete the set. The legacy
  `stub-server/devices_cli.py` still works and mirrors its changes into a
  migrated database.
- **Backup and restore.** `fleet.db` is in every nightly archive as a
  consistent online copy (its `-wal`/`-shm` files are never archived). To
  restore it, stop `skypane-byos`, extract `fleet.db` from the tarball into
  `/opt/skypane/state` (`tar -xzf <archive> -C /opt/skypane/state fleet.db`),
  `chown skypane:skypane` it, `chmod 0600` it, and start `skypane-byos`.
- **Health signal.** byos writes `fleet_status.json` in the state directory
  (`ok`, `absent` or `fault`) for the companion's health signals (the
  navigation dot and the System view). It is derived, so it is not backed up.

## Pairing, retiring and re-activating a frame

A frame can be added to a user from the companion console (the Fleet page,
administrators only) or with `fleet_cli.py`. Nothing here deploys anything.

1. **Provision the frame** over USB with `firmware/provision.sh
   <serial-port>`. It prints the frame's MAC and the SHA-256 of its secret.
2. **Register it as pending** on the VPS with
   `$FLEET devices register-pending --mac <mac> --secret-sha256 <hash>
   [--hardware <type>]`. The console has no form for this step (it only
   pairs frames that are already registered); only the command line
   registers a frame. The frame has no owner yet and no legacy file is
   written for it. `$FLEET devices pending-list` shows pending and retired
   frames.

   For a second hardware type, `fleet_cli.py` reads the second-hardware
   switch from its own environment, not from `skypane.env`. Add the
   variable on the command line, or the command refuses the type:

   ```bash
   ssh <ssh-target> "sudo -u skypane env SKYPANE_ENABLE_SECOND_HARDWARE=1 /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/fleet_cli.py --state-dir /opt/skypane/state devices register-pending --mac <mac> --secret-sha256 <hash> --hardware seeed-ee04-7in3-spectra6"
   ```

   Run it on the VPS, as the example does through `ssh`: the `skypane`
   user does not exist on a laptop. The switch itself is lifted only as
   described under "Lifting the second-hardware switch".
3. **Power the frame.** On its first wake it shows a pairing code on the
   panel and wakes again every 5 minutes. The panel is redrawn only when the
   code changes: a code is valid for 30 minutes and rotates at the next
   wake after it expires, so about every 35 minutes, roughly 40 redraws a
   day.
4. **Pair it in the console**: Fleet, "Pair a frame", type the code shown
   on the panel and choose the owner. The code is single-use and the guesses
   are throttled. A claimed frame that is not the live frame stays white (or on
   its last image) until a poll writes its image; there is no poll-now for
   users.
5. **Retire** a frame from its Fleet row (it keeps its data and its token and
   shows a "retired" image) and **re-activate** it from the pending list; a
   re-activated frame is wiped of its previous owner's data and shows a new
   code. Reassigning a frame to another owner wipes the previous owner's data
   too (the live frame, `state_path` `.`, is never wiped, only re-owned) and
   removes all of the frame's co-managers, each audited.
6. **Hard deletion is CLI-only**: `$FLEET devices remove --mac <mac>` deletes a
   pending or retired frame's row and its pairing directory.

`$FLEET devices assign` now behaves like the console reassign: for a frame
that is not the live frame it wipes the previous owner's data and
re-provisions it. Console actions are written to the append-only audit log
(Audit log page). The pairing and mutation throttles and the one-shot flash
messages are kept in memory and reset when the companion restarts.
Disabling a user (console or `$FLEET users disable`) removes the co-managers
of the frames they own, audited once per user; re-enabling does not restore
them.

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
- Backs up the state directory (the same archive as the nightly job), then
  runs `python3 -m server.fleet_migrate --dry-run` and `python3 -m
  server.fleet_migrate` as `skypane`, in that order and **before the
  swap**. Any non-zero exit aborts the deploy with the previous release
  still current. The migration is idempotent, so redeploying a sha repeats
  both steps without effect. See "Fleet database" below.
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

## Production deploy (started by hand)

Production is deployed by the "Deploy to production" workflow
(`.github/workflows/deploy.yml`), started by the owner only:

```bash
gh workflow run deploy.yml --ref main -f confirm_sha=<first 7 characters of the tip of main>
```

or Actions, Run workflow, branch `main`. A merge to `main` never deploys.

The workflow fails (it never ends as a green skip) when it is started from
a ref other than `main`, when `confirm_sha` is not the first 7 characters
of the tip of `main`, when the commit is not the tip of `main`, or when the
CI check "Lint, test, coverage, attribution" is absent or not successful
for the commit. A tip that touched only Markdown, `.planning`, `.claude`,
LICENSE or 3D model files under `hardware/cad` has no CI run; pass the
optional `ci_sha` input (the full SHA of the commit whose CI run counts)
and the workflow accepts it if no shipped path differs between that commit
and the tip.

### Which commits start CI

Every change runs the whole suite (every shard, the browser tests, the
coverage floor, the executed-test floor and the skipped ceiling) except a
change that touches only Markdown, `.planning`, `.claude`, LICENSE or the
3D model files (`.stl`, `.blend`, `.glb`, `.3mf`) under `hardware/cad`;
that starts no CI run at all. No job has a path condition, so a run that
exists is always the whole run, and the aggregate check "Lint, test,
coverage, attribution" reports on every run that exists.

- The exclusions under `hardware/cad` are by file type: any other file
  added there (a script, a config) runs CI.
- Markdown files that tests read, such as `COMPLIANCE.md` and
  `firmware/SIGNING.md`, are excluded like all Markdown, as before; only
  `deploy/README.md` and the `VENDOR.md` files are re-included.
- GitHub evaluates a path filter against at most the first 300 changed
  files of a push or pull request, so a change set larger than that is
  decided on that sample. `workflow_dispatch` starts the whole suite by
  hand.
- A tip with no CI run is deployed by passing `ci_sha`.

Every deploy imports the published firmware releases (the `Download
firmware releases` step), and the import is idempotent, so a firmware-only
deploy is simply a deploy of the unchanged tip.

The three secrets `DEPLOY_SSH_PRIVATE_KEY`, `DEPLOY_HOST_KEY` and
`DEPLOY_SSH_TARGET` are repository-level secrets, because deployment
environments are not available in private repositories on the Free plan.

**What this does and does not protect.** The confirmation is an
anti-accident control, not access control. On the Free plan any workflow on
any branch of the repository can read repository secrets, so anyone who can
push a branch could write a workflow that uses the deploy key. The
mitigation is a dedicated deploy key used only by this workflow: it can be
revoked by deleting one `authorized_keys` line on the VPS. The break-glass
route is running `deploy/deploy.sh` from the owner's laptop with a locally
held key, which involves no GitHub secret.

## Firmware releases (OTA)

Signed firmware images reach the VPS only through the manual production
deploy, never any other path:

1. A `fw-vMAJOR.MINOR.PATCH` tag on `main` makes
   `.github/workflows/firmware-release.yml` build both boards and upload
   the unsigned images (run artifact `fw-unsigned-<tag>`). CI holds no
   signing key and publishes nothing.
2. The owner signs and publishes on the Mac with
   `scripts/fw_publish_signed.py <tag> --key-file <path>` (run it with
   `--dry-run` first; see "Releasing (signing on the Mac)" in
   `firmware/SIGNING.md`). It publishes the GitHub Release
   (`skypane-<tag>.bin` + `release.json`, content-addressed by SHA-256,
   and the typed assets below) and offers to start the deploy. The deploy
   is `.github/workflows/deploy.yml`, started by hand as described in
   "Production deploy (started by hand)". A firmware release occupies the
   next version number permanently: the registry refuses lower build
   numbers and is never pruned.
3. When the deploy runs, the `Download firmware releases` step lists every
   `fw-v*` GitHub Release and downloads each one's image and manifest
   into `firmware-releases/<tag>/`. `deploy.sh` ships that whole
   directory to the VPS (`SKYPANE_FIRMWARE_DIR=firmware-releases`)
   alongside the code archive, and `activate.sh` imports every release
   with `firmware_cli import-dir` — as the `skypane` user, before the
   `current` symlink swap — into `/opt/skypane/state/firmware/`. A
   release whose bytes do not match its own manifest fails activation
   before the swap, leaving the previous release serving.
4. The import is idempotent: an ordinary code-only deploy (no new tag)
   still re-downloads and re-imports whatever is already published,
   prints `exists <tag>` for each one, and changes nothing. Nothing
   ever prunes `/opt/skypane/state/firmware/` — every release is kept
   forever — and `byos_server.py` serves each image at
   `GET /fw/<sha256>.bin`, content-addressed against the registry.
5. After import, a release is merely **available** (the companion
   Update page's "Available" state) — nothing installs it
   automatically; an operator or the device owner still chooses
   Install from the companion.

### Per-hardware-type releases

The tag, CI build, reviewed deploy and `import-dir` channel above is
unchanged for every hardware type; there is no web upload of binaries.
What changed is what a release carries:

- `release.json` names the `hardware_type` the image is built for and
  its `build` (a single integer derived from the tag, so `fw-v1.10.0`
  ranks above `fw-v1.9.0`). Only legacy-type manifests for tags up to
  `fw-v1.0.2` may omit `hardware_type`.
- The original EE02 type keeps its layout exactly:
  `<tag>/skypane-<tag>.bin` plus `<tag>/release.json`, stored in
  `firmware/registry.json`.
- Every other type adds `<tag>/skypane-<key>-<tag>.bin` plus
  `<tag>/release-<key>.json` in the same tag directory and is stored in
  its own `firmware/registry.<key>.json`. An older importer (for
  example the one in a rollback release) does not know these files and
  ignores them.
- `import-dir` visits tags in ascending build order, not name order, so
  the per-type monotonic build check cannot refuse a lower build
  because of directory sorting. A new release whose build is not above
  the type's newest published build is refused at publish time;
  scheduling an older, already-published release (at or above the
  floor) stays possible from the Update page. A name that is not a
  release tag is reported and sorted last.
- One bad item never stops the others, and an item that is already
  registered is reported without blocking the deploy.

The first time a type's registry is rewritten in the new format the
previous file is kept beside it as `registry.json.pre-fleet`.

Before the first deploy of this change, list what is published and
confirm that no non-bench release is out of version order (a later
published release with a lower version than an earlier one would make
the new build check refuse later tags):

```bash
ssh ubuntu@<vps-ip> "sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec /opt/skypane/venv/bin/python3 -m server.firmware_cli --state-dir /opt/skypane/state list'"
```

Check a file against a hardware type with the same parser publishing
uses, without writing anything (the file must be readable by the
`skypane` user):

```bash
ssh ubuntu@<vps-ip> "sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec /opt/skypane/venv/bin/python3 -m server.firmware_cli check-image --hardware-type <key> <path-to-file.bin>'"
```

`list` and `import-bench` also take `--hardware-type <key>` (default:
the original EE02 type). With only that type holding releases, `list`
prints one line per release as before; with others it prints a
`[<key>]` heading per type, and `list --hardware-type <key>` shows one.

The firmware store lives under `/opt/skypane/state/firmware/`, so it
is included in the nightly backup's allow-list alongside `devices.json`
and `gallery/` (see "Backups" below) — each archive grows by roughly
1 MB per kept release, since every release stays forever.

List what is published on the VPS directly:

```bash
ssh ubuntu@<vps-ip> "sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec /opt/skypane/venv/bin/python3 -m server.firmware_cli --state-dir /opt/skypane/state list'"
```

`-m server.firmware_cli` only resolves from the release directory, and
the `ubuntu` user cannot `cd` into `/opt/skypane/current`, so the `cd`
has to run inside the `skypane` user's shell, as above.

Two different hostnames are involved when you check the firmware by
hand. The device-protocol (byos) hostname, `<public-host>`, serves the
display endpoint and `GET /fw/<sha256>.bin`; the companion hostname,
`<companion-host>`, serves the Update page. They are different names, so
a device-side check such as fetching a firmware image goes to
`<public-host>`, never to the companion name.

`import-bench --file <bin> --version <v>` publishes one locally-built
bench image (marked `bench=True`, with a generated
"Bench image (not a release)" note) — reserved for the hardware
session, never run by a deploy. Add `--hardware-type <key>` to publish
it for another type; bench images are exempt from the build check.

#### Typed release assets and the production switch

Only the type's own key appears in these names. The second hardware
type's key is `seeed-ee04-7in3-spectra6`; the live frame's pair keeps
its original names.

| Type | Image | Manifest |
|------|-------|----------|
| live frame (legacy) | `skypane-<tag>.bin` | `release.json` |
| every other type | `skypane-<key>-<tag>.bin` | `release-<key>.json` |

The deploy job's download step asks `scripts/fw_release_assets.py` which
asset names to fetch for each `fw-v*` release: the legacy pair plus every
typed pair whose key matches `[a-z0-9-]{1,64}`. Nothing else is
downloaded, and a release that carries only the legacy pair is
downloaded exactly as before.

A second hardware type is available to the running servers only when
`SKYPANE_ENABLE_SECOND_HARDWARE` is set to exactly `1` in the production
env file. `activate.sh` reads that one line from
`/opt/skypane/skypane.env` with its own strict parser (the file is never
sourced) and forwards the switch to the `import-dir` step, which runs as
the `skypane` user, only when the value is exactly `1`. An absent,
empty, `0`, `true`, quoted, commented or otherwise different value
means closed.

While the switch is closed, `import-dir` skips every typed release of
that type, exits 0 and prints one notice per skipped release on stderr:

```
skipped <tag> [<key>]: hardware type not available here
```

That notice is expected and not an error: the release stays published
on GitHub and is imported by a later deploy once the type is available.
A typed item with a malformed key, or one that names the legacy key, is
still a failure.

Status: the first typed release is not yet published, and the switch is
closed in production. Nothing in this repository changes that by itself.

#### Lifting the second-hardware switch

The switch is lifted only by the owner, after written confirmation that
the second board has been measured on the bench and the owner accepts
serving it. There is no agent step and no automated job for these steps,
and none may be added to a workflow: no agent performs them.

1. Get the owner's written confirmation and keep it with the release
   records.
2. On the VPS, edit the production env file by hand
   (`sudo -e /opt/skypane/skypane.env`) and add the line
   `SKYPANE_ENABLE_SECOND_HARDWARE=1`, with no quotes and no trailing
   space.
3. Restart the services that read it: `skypane-byos`,
   `skypane-companion` and the poll units (`skypane-poll.service` and
   `skypane-poll.timer`).
4. Run one deploy through `workflow_dispatch` of `deploy.yml` (see
   "Production deploy (started by hand)": run it on `main` with
   `confirm_sha`; there is no approval step).
   The deploy job downloads every published release again and
   `import-dir` now imports the typed releases published earlier, which
   it had skipped while the switch was closed. Restarting alone does not
   import them.
5. Check with `server.firmware_cli list` (see above) that the typed
   type now lists its releases, and that no `skipped` notice remains
   for it in the deploy log.

To close the switch again, remove the `SKYPANE_ENABLE_SECOND_HARDWARE`
line (or set it to anything but `1`), restart the same services and deploy once more. Releases already
imported stay in the state directory and nothing is deleted.

### Fleet-wide airline names and artwork

The airline vocabulary is one per fleet. `manual_resolutions.json` (names
given by hand), `airline_name_overrides.json` (renamed built-in airlines) and
`airline_default_types.json` (default aircraft type) live once, in the state
root, and every frame's editor and poll cycle reads that one file. Before this
release each frame had its own copy under `devices/<id>/`; the live frame's
copy was already the root file.

Uploaded artwork is fleet-wide too. Every picture lives once, in
`<state root>/illustration_overrides/<key>.png` (per-type pictures
`<key>-<slug>.png` included): the live frame's directory was already that
directory, so the poll render path, the Airlines editor, the previews, the
upload and delete routes of every frame all read and write it. Before this
release each other frame kept its pictures under
`devices/<id>/illustration_overrides/`.

The same `fleet_migrate` step that imports `fleet.db` merges the per-frame
files into the root files, before the symlink swap, after the automatic
pre-migration backup (which archives the root and every per-frame file). It
never runs at service start, and a failed write exits 1 and stops the deploy.

- **Conflict rule** (one total order, the same on every run): for a prefix
  named differently on several frames the entry with the newest `created_at`
  wins; on a tie the live frame (root) wins, then the lowest frame id; an
  unparsable stamp counts as the oldest. Default types carry no stamp: root,
  then the lowest frame id. Nothing is discarded: every loser is printed with
  both names and both stamps, and the last 50 are kept in
  `airline_registry_migration.json`. An override that would take the name of
  another built-in airline (or of another airline's override), and entries
  beyond the 200 (names, overrides) or 300 (types) cap, are not merged and
  are printed.
- **Reading the log.** Lines start with `airline names:`. `would merge N
  per-frame file(s)` (dry-run) or `merged N per-frame file(s)` (real run) is
  followed by one `<registry>: A added, R replaced` line per registry, then
  one `conflict <registry> <prefix>: keep '<name>' [frame <id>, <stamp>] over
  '<name>' [frame <id>, <stamp>]` line per conflict and `not merged ...` /
  `skipped ...` lines for refusals (symlinked or oversized or invalid files).
  `airline names: nothing to do` means every per-frame file was merged
  already. An install with no per-frame registry file prints nothing.
- **Idempotent.** The marker `airline_registry_migration.json` records the
  SHA-256 of every per-frame file already merged. A second run changes no
  byte, and a name deleted from the root afterwards is not brought back. A
  per-frame file that changed since (see the rollback caveat) is merged once
  more.
- **Expand only.** The per-frame files are never modified, renamed or deleted
  by this release. They become frozen copies that nothing reads or writes; they
  disappear with their frame. A later release removes them after the rollback
  window.

**Artwork merge.** The same step (before the swap, after the same
pre-migration backup, never at service start) merges every
`devices/<id>/illustration_overrides/` into the fleet directory.

- **Conflict rule.** When the fleet directory and one or more frames hold
  different bytes under the same file name, the file with the latest
  modification time wins; on a tie the fleet file wins, then the lowest frame
  id. Copies keep the source's modification time. Identical bytes are not a
  conflict. Every loser, a replaced fleet file included, is first copied to
  `illustration_conflicts/<frame id or live>/<file name>` (a numeric suffix
  `.1`, `.2` before `.png` keeps an earlier archive of different bytes); no
  page or render reads that folder, and the nightly backup archives it.
- **What is merged.** Only regular files (never symlinks) named `<key>.png`
  (lowercase letters, digits, hyphens), at most 4 MiB, and accepted by the
  same PNG, size and pixel-cap check as an upload. Dot-files and `*.tmp`
  leftovers, symlinked directories and anything else are skipped, reported by
  name and reason, and never deleted. At most 1000 files and 256 MiB are added
  to the fleet directory per run (latest first); the rest stay pending for the
  next run.
- **Reading the log.** Lines start with `artwork:`. `would merge N picture(s)
  from M frame(s) into the fleet directory: A new, R replaced, I identical, C
  conflict(s)` (dry-run) or `merged ...` (real run), then one `conflict
  <file>: keep [frame <id>, <time>, <size>] over [frame <id>, <time>, <size>]`
  line per loser, and `skipped ...` / `not merged ...` lines. `artwork: nothing
  to do` means every per-frame picture was merged already. An install with no
  per-frame pictures prints nothing.
- **Idempotent, expand only.** `illustration_migration.json` records the
  SHA-256 of every per-frame picture merged, so a second run changes nothing
  and a picture deleted from the fleet directory afterwards is not brought
  back. The per-frame image directories are never modified, renamed or
  deleted; they become frozen copies that disappear with their frame, and a
  later release removes them after the rollback window.

### Default aircraft types without a picture

An airline's default aircraft type is only accepted for a type the airline has
a picture for (built in or an upload). Defaults stored before that rule are
cleared once by `server.fleet_migrate`, after the airline-names and artwork
merges, in the same backup, dry-run and real-run steps as the rest.

- **Reading the log.** Lines start with `airline default types:`. `would clear
  N` (dry run) or `cleared N` (real run), then one `<airline key>: <type>` line
  per entry; `airline default types: nothing to do` when none lacks a picture or
  the run already happened. The dry run judges the fleet root as it is before
  the merges of the same run.
- **Nothing is lost.** Each cleared entry is first appended to
  `airline_default_types_cleared.json` (airline key, type, source, time) in the
  state root; `airline_default_types_migration.json` marks the run and is
  written last. Both are in the backup. Only a run that clears something writes
  anything. Per-frame files are never touched.
- **After a deploy.** Check the log for the two lines, open the Editor and see
  that the cleared airlines show no default type, and read the archive file to
  restore any entry on purpose (upload the type's picture first, then set it).

### A default type for every airline with pictures

An airline has no picture of its own: its pictures are its aircraft types' (the
older `{airline}.png` counts as the picture of its airframe type) and one type
is its default, the picture shown for a type it has none of. After the clearing
above, the same run (`server.plane.fleet_set_defaults`, called by
`server.fleet_migrate`) gives every airline that has pictures and no default
type one, by fixed rules and without any Editor choice: (a) a legacy picture
with a known airframe gives that type; (b) otherwise one typed picture gives
that type, several give the most seen type across all frames, a tie or no
sighting the first type code alphabetically; (c) a legacy picture of an unknown
airframe gives the most seen typed picture, or the airline is reported
`unresolved`; (d) an airline with no picture gets nothing. Sightings are the
`runway_events` of the root and of every frame, read-only.

- **Reading the log.** `airline default types: would set N` (dry run) or `set
  N`, then one `<airline key>: <type> (rule a|b|c)` line per entry, then
  `airline default types: unresolved M` and one `unresolved <key>: <reason>`
  line each; `airline default types: nothing to do` once the run has happened
  (the clearing prints its own `nothing to do` line too). Expect about forty
  `rule a` lines on the first deploy: every built-in airline gets its airframe.
  The dry run judges the fleet root as it is before the merges of the same run
  (a picture or default still pending in the per-frame merge is not counted); it
  does count the defaults the clearing is about to remove as gone.
- **Nothing is lost.** Every default set is first appended to
  `airline_default_types_set.json` (airline key, type, rule, time) in the state
  root; `airline_default_types_set_migration.json` marks the run and is written
  last. Both are in the backup. Nothing visible changes on a frame except for an
  airline whose chosen default now wins; a default the owner clears later is not
  set again, the airline's legacy picture still being its effective default.
- **After a deploy.** Check the `set` and `unresolved` lines, open the Editor:
  each airline shows its type rows with the default marked; handle the
  `unresolved` airlines by choosing a default in the Editor.

## Backups

A nightly systemd timer (`skypane-backup.timer`, 03:15 UTC,
`skypane-backup.service` running as `skypane`) archives
`/opt/skypane/state` into `/var/lib/skypane-backup/archives/`. It takes a
consistent online copy of `history.db` and `fleet.db` with SQLite's own backup API
(never a raw copy of the live `-wal`/`-shm` files), and copies everything
else that cannot be regenerated from an **include list** — device
tokens, device/colour/calendar/manual-resolution config, the airline
name overrides, default aircraft types, AI-suggestion cache and the airline merge marker, the calendar
secret, uploaded illustration overrides (and the `illustration_conflicts/` archive and its marker), the poll enrichment cache, and
`gallery/` (the last ~25 rendered panels — kept for the visual history,
per D-24). Regenerable or short-lived files (`panel.bin`, theme and frame preview caches, the shared route
cache, the ADS-B request ledger, the check-interval experiment file, Caddy's access log) are excluded. An unlisted top-level file in `state/` is
logged as drift rather than silently skipped or silently included. Each
run writes a checksummed `skypane-state-<UTC timestamp>.tar.gz` and keeps
the newest 14 on the VPS.

**Per-device directories.** Devices beyond the live frame live in
`<state_dir>/devices/<id>/` (id: `d_` plus 8 lowercase hex characters) with
the same file set as the root; the live frame stays at the root and is never
moved. The backup archives each `devices/<id>/` entry under the same path in
the archive: `device_config.json`, `poll_state.json`, `battery_state.json`,
the calendar, colour, manual-resolution, airline name override and default-type files and `illustration_overrides/` (frozen copies since the airline names and artwork became fleet-wide; the rollback source),
`gallery/` and a WAL-safe snapshot of `history.db`. It does not archive
`panel.bin`, `img/`, lock files, temp files, WAL/SHM files or symlinks. A
directory under `devices/` with a malformed name, or an unexpected file
inside a device directory, is logged as drift. Restoring an archive into an
empty directory recreates every `devices/<id>/`.

**Rollback caveat (expand-only).** The previous release ignores `devices/`
and the `timezone` key: it drops the key on its next save, which reverts
that device to Paris. A device created through the CLI is also written to the
legacy `devices.json` and `byos_state.json`, so the previous release
authenticates it and would serve it the live frame's image. This only affects
devices created after this change; none exist in production yet.

**Rollback caveat (airline names).** The previous release reads the airline
files per frame, so after a rollback every non-live frame sees its own old
names again, and names given or changed after the upgrade exist only in the
root files (the previous release reads them for the live frame only). A later
roll-forward merges again only the per-frame files that changed in the
meantime (their hash differs from the marker), by the same conflict rule,
which can bring back a name that was deleted fleet-wide before the rollback:
re-check the Airlines editor after a roll-forward that followed a rollback.
The merge runs for a few milliseconds before the symlink swap while the
previous release may still write the live frame's root file; the
pre-migration backup exists and a re-run is idempotent.

**Rollback caveat (artwork).** The previous release reads per-frame image
directories, so after a rollback every non-live frame sees its own old
pictures again, and pictures added after the upgrade exist only in the root
directory (visible to the previous release on the live frame only). A later
roll-forward merges again only the per-frame pictures whose hash changed in
the meantime, by the same rule, which can bring back a picture deleted
fleet-wide before the rollback: re-check the Airlines editor after a
roll-forward that followed a rollback.

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

The companion's System view reads that marker and shows "last off-box
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
SKYPANE_AUTH0_DOMAIN=rehearsal.example.test SKYPANE_AUTH0_CLIENT_ID=rehearsal \
    SKYPANE_AUTH0_CLIENT_SECRET=rehearsal \
    SKYPANE_COMPANION_PUBLIC_URL=https://rehearsal.example.test \
    SKYPANE_COMPANION_INSECURE_COOKIES=1 \
    server/.venv/bin/python3 companion/app.py --port 8650 --state-dir "$SCRATCH"
# open http://127.0.0.1:8650 - Flights and Health should show production
# history, Display and Device should show production settings.
```

**Production restore** (documented here; only run this for real if the
VPS's own state is actually lost or corrupted):

1. `sudo systemctl stop skypane-poll.timer skypane-poll.service skypane-companion skypane-byos`
2. `sudo mv /opt/skypane/state /opt/skypane/state.broken-<date>`
3. `sudo install -d -o skypane -g skypane -m 2775 /opt/skypane/state`
4. `sudo tar -xzf <archive> -C /opt/skypane/state` (this restores
   `fleet.db` too)
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

## Sign-in (Auth0)

The companion signs people in through Auth0 (authorization code flow with
PKCE) and keeps its own roles and sessions in `fleet.db`. Frame
authentication is unchanged: a frame still authenticates with its MAC and
per-device secret, and Auth0 is not involved in any device request.

### Auth0 tenant (owner, once)

In the owner's EU Auth0 tenant:

1. Create a **Regular Web Application** (authorization code flow).
2. **Allowed Callback URLs**: exactly `https://<companion host>/callback`.
3. **Allowed Logout URLs**: exactly `https://<companion host>/login`.
4. On the database connection, **disable sign-ups**, and enable no social
   connection. People are invited from SkyPane, never self-registered.

### Environment variables

Set these in `/opt/skypane/skypane.env` (`root:root 0600`; the secret
lives nowhere else), then `sudo systemctl restart skypane-companion`:

- `SKYPANE_AUTH0_DOMAIN=<your-tenant>.eu.auth0.com`
- `SKYPANE_AUTH0_CLIENT_ID=<auth0-client-id>`
- `SKYPANE_AUTH0_CLIENT_SECRET=<auth0-client-secret>`

The three are required: the companion refuses to start with none or a
partial set, and Auth0 is the only way to sign in. The callback
and logout URLs are derived from `SKYPANE_COMPANION_HOST` (or the optional
`SKYPANE_COMPANION_PUBLIC_URL`); nothing is ever read from the request
Host header.

### Auth0 invitations (machine-to-machine)

Optional. When configured, inviting someone from the companion also creates
their Auth0 database user and shows a one-time link to set a password; the
link is shown once and is never stored or logged. The first link of a person
lasts 5 days; a link created again ("Send a new invitation") lasts 24 hours.
Without it the invitation
stays local and you create the Auth0 user by hand. These steps are the
owner's, in the Auth0 dashboard:

1. Create a **Machine to Machine** application (a separate one from the
   Regular Web Application above).
2. Authorise it for the **Auth0 Management API** with exactly two
   permissions, `create:users` and `create:user_tickets`, and no other (no
   read, update or delete permission).
3. Note the name of the database connection the people are created on
   (Authentication > Database) and its connection id (`con_` followed by 16
   letters or digits, on the same connection's settings page). The id is
   required to send a new invitation to someone who already has an Auth0
   account: without it (or with a malformed one) that action fails closed
   with a message to the administrator and the audit row says
   `user_exists_connection_id_missing` or `connection_id_invalid`. It is not
   a secret, but a real value never goes in this repository.
4. In `/opt/skypane/skypane.env` (`root:root 0600`, the same file and mode
   as the other Auth0 secret) add:

   - `SKYPANE_AUTH0_MGMT_CLIENT_ID=<auth0-mgmt-client-id>`
   - `SKYPANE_AUTH0_MGMT_CLIENT_SECRET=<auth0-mgmt-client-secret>`
   - `SKYPANE_AUTH0_DB_CONNECTION=<auth0-database-connection-name>`
   - `SKYPANE_AUTH0_DB_CONNECTION_ID=<auth0-database-connection-id>`
   - `SKYPANE_AUTH0_CUSTOM_DOMAIN=<auth0-custom-domain>` (only if the tenant
     uses a custom domain: the invitation link is shown only when it is an
     https address on the tenant domain or this one)

   then `sudo systemctl restart skypane-companion`. The values reach the
   service only through the environment file; no unit file carries them.

Rotate: rotate the client secret on the application in the dashboard, edit
the line in the environment file, restart the companion. Revoke: delete the
machine-to-machine application (or remove its Management API
authorisation); the companion then reports invitations as not configured
and keeps working. Sign-ups stay disabled, and an Auth0 account alone
grants nothing: signing in still requires the local invitation.

### Inviting and managing people

```bash
FLEET="sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/fleet_cli.py --state-dir /opt/skypane/state"
ssh <ssh-target> "$FLEET users add --email someone@example.org --role user"
ssh <ssh-target> "$FLEET users unlink-identity --email someone@example.org"
ssh <ssh-target> "$FLEET users disable --email someone@example.org"
```

The person signs in with the same verified email. `unlink-identity` lets
someone who lost their Auth0 account sign in with a new one; `disable`
ends their sessions. Always run the CLI as the `skypane` user: run as
root it leaves a root-owned `fleet.db` or `-wal` file the companion
cannot write, and sign-in then fails closed with a 503.

### Real-tenant smoke test (manual, owner)

1. Sign in through Auth0 and confirm the session and the Account page.
2. Send a token request with a wrong `code_verifier` and confirm Auth0
   rejects it.
3. Sign out and confirm the browser returns to the allowed logout URL,
   and that signing in again prompts for credentials (the Auth0 session
   ended). The logout URL uses `/v2/logout`; on newer tenants verify its
   behaviour here. The URL builder is isolated so it can switch to the
   tenant's `end_session_endpoint`.

### Log redaction

Caddy drops the `code`, `state` and `error_description` query keys from
the companion access log. `caddy validate` runs in `activate.sh`; also
check that a real `/callback` line in `journalctl -u caddy` shows no
query values.

### Schema v3 and rollback

The pairing and console release adds schema 3 (pending frames, the audit
log, a location owner column). The `activate.sh` dry-run prints
`upgrade fleet.db schema 2 -> 3`; the migration runs after the backup and
before the symlink swap, and is expand-only. The previous release's byos
refuses a schema 3 file as too new and falls back to the legacy files;
Health shows a fleet fault until the new release is live again. Frames
claimed after the upgrade have no legacy token, so after a rollback they
fail with 401 and then 403 and back off for up to 6 hours. Frames that
existed before the upgrade keep working from the legacy files. Restoring a
backup taken at schema 3 needs this release or later.

### Schema v4 and rollback

The device co-management release adds schema 4: one table
(`device_co_managers`), one index and two triggers that keep a frame owner
from also being a co-manager of the same frame. No existing table or row
changes, so the live frame's registry entry, files and image are untouched.
The `activate.sh` dry-run prints `upgrade fleet.db schema 3 -> 4`; the
migration runs after the backup and before the symlink swap, and is
expand-only. The previous release (schema 3) refuses a schema 4 `fleet.db`
as too new (`FleetDbTooNew`) and falls back to the legacy files, exactly as
it does for schemas 2 and 3; Health shows a fleet fault until the new
release is live again. While rolled back, co-managers cannot reach the
companion fleet store, and the frame itself keeps polling from the legacy
files. Rolling forward again needs no manual step, because the table and its
rows survive. Restoring a backup taken at schema 4 needs this release or
later.

### Schema v2 and rollback

`fleet_migrate` upgrades `fleet.db` from schema 1 to 2 before the symlink
swap, as the `skypane` user, after the backup. The previous release's byos
refuses a v2 file as too new and serves from the legacy files, so a
rollback keeps the frame working, but Health shows a fleet fault until the
new release is live again. Backups now contain the `sessions` table
(hashes only); restoring one brings back unexpired sessions.

## AI-suggested airline names

In the Airlines editor (`/airlines/manage`, administrators only) each
unidentified callsign prefix can carry a name proposed by a small Claude
model (`claude-haiku-5-5`). The proposal is shown as a "Suggestion" with a
round check; nothing is applied until a person presses the check or types a
name, and the check posts to the same route as manual naming. A suggestion
only fills a gap: "Name it" stays when there is none, when the service is off
or when it fails.

- **Off by default.** The feature exists only while `SKYPANE_ANTHROPIC_API_KEY`
  is set in `/opt/skypane/skypane.env` (`root:root 0600`). Without it the
  editor is exactly the manual flow and no network call is made. To switch it
  off or revoke it, delete the line (and revoke the key in the Anthropic
  console), then `sudo systemctl restart skypane-companion`.
  `SKYPANE_ANTHROPIC_BASE_URL` is a loopback-only test seam; never set it in
  production (a non-loopback host is ignored).
- **What leaves the server.** The three-letter prefix and up to four sample
  callsigns of that prefix, nothing else: no frame, owner, user, location or
  device data. The call is made from the companion's administrator route (one
  request at a time, after the page has rendered), never from the poll timer.
- **Cache.** `airline_suggestions.json` in the state root (`SKYPANE_STATE_DIR`):
  one entry per prefix with the proposed name, the model id and the date. A
  prefix is asked once ever; "no idea", a removed suggestion and a named
  prefix are kept as decisions and never asked again. A failed request is
  retried after 15 minutes (6 hours for an authentication, billing or request
  error). To ask again for one prefix, delete its entry from the file (the
  file is read on each request, no restart needed).
- **Caps.** At most 10 calls per rolling hour and 60 per rolling day across all
  prefixes; over the cap the editor simply shows "Name it". One attempt per
  call, 3.05 s connect and 8 s read timeout.
- **Logs.** A failed call writes one line to the companion's journal:
  `airline_suggest: prefix=OCN reason=http_529 request_id=req_...`. The key,
  the request and the response body are never logged; `request_id` is the
  Anthropic request id for support.

## Read-only battery-history export

The companion can serve the `device_health` table (battery history) as
JSON Lines over HTTPS, so an automated reader can fetch it without SSH.
It is off by default. The route is `GET /api/export/battery-history?since=<UTC time>`,
for example `since=2026-10-23T04:25:00Z`. Each line is one JSON object with
eighteen keys: `ts`, `battery_mv`, `fw_version`, `boot_reason` and `rssi`,
followed by the thirteen wake keys `wake_seq`, `boot_ms`, `wifi_ms`,
`wifi_attempts`, `prev_seq`, `prev_awake_ms`, `prev_request_ms`,
`prev_download_ms`, `prev_draw_ms`, `prev_spi_ms`, `prev_tls_ms`,
`prev_redraw` and `prev_outcome`. All eighteen are always present; the wake
keys are null for a frame that did not send the telemetry header and for
rows from before it existed. The SSH export in
`hardware/FIELD-VALIDATION-FR.md` keeps its five columns. The new columns
are added by the poll oneshot after a deploy; until it has run, the export
returns the five old values with the new keys null. Nothing else is
exposed, and nothing is ever written.

Access is by bearer token only (`Authorization: Bearer <token>`). A session
cookie never grants access. `since` must be a UTC time in that exact format,
at most 400 days old and at most a day ahead; any other query parameter is
refused with 400. More than 100000 matching rows answers 413. Ten failed
attempts in a minute from one client address answer 429 for that client.

To read another frame's battery history (each frame keeps its own
`history.db` under `devices/<id>/`), add one optional parameter to this
route only: `GET /api/export/battery-history?since=<UTC time>&device=<device id>`,
for example `device=d_1a2b3c4d`. Without `device` the answer is the primary
frame's, exactly as before. With it, the rows, columns, `since` rules, 413
cap and line format are the same, read from that frame's own `history.db`
(read-only; nothing is created or written). The id must be a registered
frame in `fleet.db`; a retired frame whose data is still kept stays readable.
Errors: 400 for an id that is not `d_` plus eight lowercase hex digits
(empty, too long, `..`, slashes and encoded forms included), for a missing
`since`, a repeated `device` or any other parameter; 404 for a well-formed id
that is not registered (the body names no id, and no route lists ids); 503
when that frame has no readable `history.db` yet. The same bearer token, a
session cookie that never grants access, and the same failed-attempt
throttle apply. `flights`, `poll-cycles` and `status` still refuse `device`
with 400.

### Debugging exports

The same token also opens three more read-only routes under `/api/export/`,
so a missed flight or an odd screen can be explained without SSH. They share
the token, the throttle and the 400/401/413/429/503 answers above, and the
cloud-environment secret (path prefix `/api/export/`) already covers them.

| Route | Answers |
|-------|---------|
| `GET /api/export/flights?since=<UTC time>` | JSON Lines of `runway_events`: `ts`, `hex`, `callsign`, `aircraft_type`, `confirmed_state`, `corroborated`, `route_source`, `airline`, `origin`, `destination`, `tracked_runway`, `gallery_name`. Only flights that reached the display have a row. |
| `GET /api/export/poll-cycles?since=<UTC time>` | JSON Lines of the `poll_cycles` trace: one row for each cycle that saw, queued, dropped or drew an aircraft (`detected_*`, `shown_*`, `confirmed_state`, `render_state`, `state_source`, `pending`, `pending_hexes`, `dropped`, `redraw_blocked`, `panel_changed`, `source_fault`, `tracked_runway`; booleans as 0 or 1). Kept for 14 days. |
| `GET /api/export/status` | One JSON object, no parameter: the flight on the panel and its state, the display queue with each entry's age, the previous flight, `last_advance_at`, `last_flight_redraw_at`, a few settings (`wake_interval_s`, `tracked_runway`, `display_enabled`, quiet hours, `timezone`), the check-interval experiment (`null` when inactive) and the pipeline heartbeat. |

None of them exposes a location, a name, a path or a secret: `status` copies
a fixed list of fields, never whole files. `poll_cycles` appears after the
first poll cycle that runs the new release; until then `poll-cycles` answers
with no lines.

### Enable

1. On your own machine, generate a token (never on a shared screen, never
   in chat):

   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(48))"
   ```

2. On the VPS, add one line to `/opt/skypane/skypane.env` (root-only,
   never committed):

   ```
   SKYPANE_EXPORT_TOKEN=<the token>
   ```

3. Restart the companion: `sudo systemctl restart skypane-companion`.
4. In the claude.ai cloud environment settings, add a network secret: type
   `Bearer`, allowed site = the companion hostname (`SKYPANE_COMPANION_HOST`),
   path prefix `/api/export/`, header `Authorization` with prefix `Bearer`,
   and the token as the value. The platform adds the header to requests to
   that host and path; the reader never sees the token.

The token must be the generated value, exactly as printed: no quotes, no
spaces, nothing else on the line. A stray space or quote means it never
matches and the route answers 401, then 429 after ten tries, which can look
like an attack. Do not choose a token by hand; a short or patterned one
defeats the throttle. If the reader shares an outbound address with other
users, someone else's failed attempts can make the throttle answer 429 to
the reader for up to a minute; the block clears by itself.

### Rotate or revoke

To rotate, repeat steps 1 to 3 with a new token and update the network
secret. To revoke, delete the `SKYPANE_EXPORT_TOKEN` line and restart
`skypane-companion`: the route then answers 404, exactly like an unknown
path. A value shorter than 32 characters also leaves it off.

### Logging

Caddy's access log redacts the `Authorization` header (see the comments in
`deploy/Caddyfile`), and the companion never logs a header. The `since`
query string is logged by Caddy; it is a time, not a secret. No Caddyfile
change is needed for this route.

## Verifying the deployment

```bash
# From outside the VPS (your laptop): TLS + auth gate.
# 401 is the correct, expected result without a bearer token - it proves
# both a valid TLS handshake happened and the auth gate is active.
curl -sI https://<public-host>/device/v1/display

# The app port must NOT be reachable directly (ufw denies it):
curl -sI --connect-timeout 3 http://<vps-ip>:8642/device/v1/display   # expect: refused or timeout
# (byos listens on 127.0.0.1 only and ufw denies the port.)

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

## byos listens on loopback only

`skypane-byos.service` starts `stub-server/byos_server.py` with
`--bind 127.0.0.1` (the flag defaults to `0.0.0.0` for the LAN stub flow)
and carries `IPAddressDeny=any` + `IPAddressAllow=localhost`: byos makes
no outbound connections and Caddy on loopback is its only client.
`ufw deny 8642/tcp` (plus ufw's own default-deny-incoming policy) stays
as a second layer. byos takes no secret on its command line or in its
environment — enrolment uses the per-device registry (`devices.json`,
see "Device enrolment (per-device secret)" above). To check on the VPS:

```bash
sudo ss -ltnp | grep -E ':8642 '   # expect 127.0.0.1:8642 only
pgrep -af byos_server.py           # expect --bind 127.0.0.1 and no --secret
```

## Rolling back

See "Ship the code" above: `activate.sh` already rolls a *failing* deploy
back to the previous release automatically, and prints the manual command
for deliberately reverting to an older, already-working release. Code and
configuration are reproducible from this repository at any commit — but
`/opt/skypane/state` (flight history, device tokens, settings, uploaded
illustrations, `gallery/`) is not, which is exactly why it is backed up
nightly and pulled off-box (see "Backups" and "Restore" above).

## Private repository (GitHub Free plan)

Once the repository is private it sits on a personal account with no
collaborators, on the GitHub Free plan. The Free plan does not provide
branch protection, rulesets, deployment environments, secret scanning or
push protection for private repositories, and nothing in this setup relies
on any of them.

Where each control lives instead:

| Concern | Where it lives now |
|---------|--------------------|
| Production deploy | Manual `deploy.yml` (see "Production deploy (started by hand)"): main only, `confirm_sha`, a green CI run for the commit. It uses a dedicated deploy key, and the owner has decided to rely on that key alone, with no server-side restriction of it. |
| Firmware signing | The owner's Mac, with `scripts/fw_publish_signed.py` (see `firmware/SIGNING.md`). GitHub holds no signing key; CI only builds unsigned images. |
| CI | The self-hosted runner kit in `deploy/runner/README.md`, selected by the repository variable `CI_RUNS_ON`. The kit exists, but the runner is still to be installed and `CI_RUNS_ON` is still unset, so CI runs on GitHub-hosted runners until the owner completes the install steps in that file. |
| Secret handling | Repository-level secrets only; the old environments are no longer used, and the signing secret was deleted from GitHub. The owner may delete the unused environments. |

Three consequences to remember:

- Repository secrets are readable by a workflow on any branch of the
  repository, so anyone who can push a branch can use the deploy key.
  Write access to the repository is therefore the ability to dispatch
  `deploy.yml` and read those secrets.
- Branches pushed by assistant sessions run their code on the Mac runner
  once it is live, inside its isolated VM.
- Environment settings cannot be edited once the repository is private, so
  any change to an environment or its secrets has to be made before the
  visibility changes.

Dependabot is hosted and free. Its pull requests run CI on the runner
selected by `CI_RUNS_ON`; its "run on self-hosted runners" setting stays
off.

Hosted fallback: delete the repository variable (`gh variable delete
CI_RUNS_ON`) and every job runs on GitHub-hosted `ubuntu-latest` again. A
private repository gets the smaller 2-vCPU runner and a monthly allowance
of free minutes, so a full CI run is slower than on a public repository and
can use up the allowance.

Watched risk: GitHub announced, then postponed with no date, a per-minute
charge for self-hosted runners. Re-check the GitHub Actions changelog
before relying on the free runner.

### Checking after a change

After changing visibility, the runner or the tokens, check in this order:

1. A session can clone, push a branch, open a draft pull request through
   the REST API and read the CI status and job logs (its token is valid).
2. A pull request run goes green on the selected runner, and the hosted
   fallback works once.
3. Dependabot: "Check for updates" opens a pull request and its CI runs.
4. The nightly backup pull still succeeds (it uses SSH to the VPS, not
   GitHub).
5. A `deploy.yml` run from main downloads the firmware releases with
   `gh release download` and the import reports each tag as existing.
6. A firmware release dry run with `scripts/fw_publish_signed.py --dry-run`
   verifies and publishes nothing.

## Secrets discipline

No cloud-provider API token is used in this flow (the OVH VPS is created
by hand in the console — see the one-time human steps above). Each
frame's enrolment secret lives only in that frame's own flash; this VPS
stores only its SHA-256 hash, in `devices.json` under
`${SKYPANE_STATE_DIR}`. `skypane.env.example` carries placeholders only
for what remains a real secret there (the Auth0 client secret); the
real `skypane.env` is root:root 0600, gitignored (`deploy/.gitignore`),
and lives solely on the VPS, same as `devices.json`. The `skypane-backup`
pull key is restricted by its forced command to `list`/`get`/`ack` over
the archives directory only — it can never read `skypane.env` or open a
shell (see "Backups" above). Before any commit touching this directory,
confirm `git status --porcelain` shows no real env file, private key, or
token staged, and that `git log -p` for the commit contains no secret
value.
