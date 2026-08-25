# deploy — Ink Frame Phase 2 VPS deployment

Turns the render pipeline built in 02-01 through 02-04 into an always-on,
internet-reachable server: an OVH VPS-1 running Ubuntu 26.04 LTS, Caddy
terminating TLS in front of `stub-server/byos_server.py`, and a systemd
timer driving `server/poll_loop.py` every 30 seconds. This closes ROADMAP
Phase 2 success criterion 4 — the device polls this real server over HTTPS
instead of a laptop-local stub.

**Provider note:** the plan (`02-05-PLAN.md`) and its D-P2-06 decision
specify Hetzner CX22; this deployment instead targets OVH VPS-1, an
equivalent box (2 vCPU / 4 GB RAM / 40 GB NVMe, Ubuntu 26.04, always-on)
at the user's explicit request after a live price/locale comparison — see
`02-05-SUMMARY.md`'s Deviations section. Every script and unit file below
is provider-agnostic (they target "a fresh Ubuntu box reachable over
SSH"); only this README's prose and the one-time human steps changed.

**SSH login note:** current Ubuntu cloud images (including this VPS's
26.04 image) disable direct root SSH login by default; the default
`ubuntu` user has passwordless sudo instead. Both `provision.sh` and
`deploy.sh` work with either a direct-root `SSH_TARGET` or a
passwordless-sudo non-root one — see each script's header comment.

## What each file does

| File | Purpose |
|------|---------|
| `inkframe.env.example` | Template for the real, gitignored `inkframe.env` — secrets and per-deployment config, loaded by systemd's `EnvironmentFile=` |
| `inkframe-byos.service` | Runs `stub-server/byos_server.py` as the `inkframe` user, bound to loopback, `--image-url-scheme https` |
| `inkframe-poll.service` / `inkframe-poll.timer` | A `Type=oneshot` unit invoking `server/poll_loop.py --once`, fired every 30s by the timer |
| `Caddyfile` | Reverse-proxies the public hostname to `127.0.0.1:8642` with Caddy's automatic Let's Encrypt HTTPS |
| `provision.sh` | Idempotent first-run setup on a fresh Ubuntu VPS: user, packages, venv, unit files, ufw, SSH hardening |
| `deploy.sh` | Repeatable code push: rsync, conditional pip install, service restart, journald tail |

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

No OVH API token or credential is needed anywhere in this flow — the VPS
is created by hand in the console, and everything after that point is
either a script Claude/you run once (`provision.sh`), a script run on
every code change (`deploy.sh`), or one manual file written directly on
the VPS (`inkframe.env`, see below) — never a dashboard click.

## First-time provisioning

```bash
# From your laptop, copy this directory to the fresh VPS (or clone the repo
# there directly - either works, provision.sh only needs this directory).
# Direct-root example:
scp -r deploy root@<vps-ip>:/root/deploy
ssh root@<vps-ip>
./deploy/provision.sh <public-host>

# Passwordless-sudo non-root example (e.g. Ubuntu cloud images, which
# disable direct root SSH login by default and use a "ubuntu" user
# instead):
scp -r deploy ubuntu@<vps-ip>:/home/ubuntu/deploy
ssh ubuntu@<vps-ip> "sudo /home/ubuntu/deploy/provision.sh <public-host>"
```

`<public-host>` is the hostname from step 4 above — either the VPS's real
public DNS name (e.g. `<public-host>`) or a nip.io fallback
(e.g. `203-0-113-10.nip.io`).

`provision.sh` is idempotent — re-run it after editing any of the files it
installs (unit files, Caddyfile) to apply the change.

## Write the real env file (once, by hand, on the VPS)

`inkframe.env` is never rsynced, never committed, and never leaves the VPS.
Create it directly there:

```bash
# Direct-root example:
ssh root@<vps-ip>
cp deploy/inkframe.env.example /opt/inkframe/inkframe.env
nano /opt/inkframe/inkframe.env   # fill in a real INK_BYOS_SECRET (openssl rand -hex 32),
                                   # confirm INK_PUBLIC_HOST matches the public host above
chown inkframe:inkframe /opt/inkframe/inkframe.env
chmod 600 /opt/inkframe/inkframe.env

# Passwordless-sudo non-root example (e.g. Ubuntu cloud images):
ssh ubuntu@<vps-ip>
sudo cp /home/ubuntu/deploy/inkframe.env.example /opt/inkframe/inkframe.env
sudo nano /opt/inkframe/inkframe.env   # same fields as above
sudo chown inkframe:inkframe /opt/inkframe/inkframe.env
sudo chmod 600 /opt/inkframe/inkframe.env
```

The `INK_BYOS_SECRET` value written here is the same value Task 3 of
`02-05-PLAN.md` sets `firmware/main/secrets.h`'s `INK_SETUP_SECRET` to on
the device side — it never enters git on either side, matching this
repo's `secrets.h` discipline (T-02-05-02).

## Ship the code

From your laptop, from the repository root:

```bash
deploy/deploy.sh root@<vps-ip>
# or, for a passwordless-sudo non-root SSH_TARGET (e.g. Ubuntu cloud images):
deploy/deploy.sh ubuntu@<vps-ip>
```

Re-run this any time `server/` or `stub-server/` changes. It rsyncs the
code (excluding `.venv`, `state/`, `__pycache__`, and any env file),
reinstalls `server/requirements.txt` only if it changed, restarts
`inkframe-byos.service`, starts `inkframe-poll.timer`, and prints the last
10 journald lines for both units so a bad deploy is visible immediately.
Every remote step routes through `sudo` (see `deploy.sh`'s header comment),
so this works whether `SSH_TARGET` logs in as root directly or as a
non-root user with passwordless sudo.

## Verifying the deployment

```bash
# From outside the VPS (your laptop): TLS + auth gate.
# 401 is the correct, expected result without a bearer token - it proves
# both a valid TLS handshake happened and the auth gate is active.
curl -sI https://<public-host>/device/v1/display

# The app port must NOT be reachable directly (ufw denies it):
curl -sI --connect-timeout 3 http://<vps-ip>:8642/device/v1/display   # expect: refused or timeout

# On the VPS: timer is active and cycling.
ssh root@<vps-ip> systemctl is-active inkframe-poll.timer
ssh root@<vps-ip> journalctl -u inkframe-poll -n 20

# On the VPS: Caddy is terminating TLS and proxying correctly.
ssh root@<vps-ip> journalctl -u caddy -n 20
```

## Reading logs

```bash
ssh root@<vps-ip> journalctl -u inkframe-poll -f     # follow the poll cycle live
ssh root@<vps-ip> journalctl -u inkframe-byos -f     # follow device requests live
ssh root@<vps-ip> journalctl -u caddy -f             # follow TLS/proxy activity live
```

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

Every unit is `Restart=always` (byos) or fails-and-retries-next-cycle
(poll), so a bad `deploy.sh` run that leaves the code broken is recovered
by re-running `deploy.sh` with a working commit checked out locally — there
is no separate rollback mechanism to invoke, since the VPS state is fully
reproducible from this repository's `server/` and `stub-server/` trees plus
the one hand-written `inkframe.env`. To roll back to a previous release,
`git checkout <previous-commit> -- server stub-server` locally, then
re-run `deploy/deploy.sh <ssh-target>`.

## Secrets discipline

No cloud-provider API token is used in this flow (the OVH VPS is created
by hand in the console — see the one-time human steps above), and
`INK_BYOS_SECRET` never enters git — matching this project's
`firmware/main/secrets.h` convention. `inkframe.env.example`
carries placeholders only; the real `inkframe.env` is gitignored
(`deploy/.gitignore`) and lives solely on the VPS. Before any commit
touching this directory, confirm `git status --porcelain` shows no real
env file, private key, or token staged, and that `git log -p` for the
commit contains no secret value.
