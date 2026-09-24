#!/usr/bin/env bash
# SkyPane — first-run (and safe-to-re-run) provisioning for a fresh
# Ubuntu 26.04 LTS OVH VPS-1. Run as root (or via sudo) on the VPS
# itself, never on a laptop. Works whether the box allows direct root
# SSH login or (as on current Ubuntu cloud images, which disable it by
# default) only a passwordless-sudo non-root user - either way, invoke
# this script itself with `sudo`.
#
# Prepares the machine for the release-layout deploy flow (SEC-05, D-09):
# the service user, the root-owned releases/ directory and venv,
# root:root 600 ownership of skypane.env, the dedicated skypane-backup
# pull user and its directories (SEC-04, D-05), SSH hardening (SEC-08),
# and the OS packages/firewall. It does NOT install systemd unit files or
# render the Caddyfile any more - deploy/activate.sh (Plan 37-06) does
# that on every deploy, so units and the Caddyfile always match the code
# actually running (D-11). Run this once before the first deploy, and
# again after any change to this script itself.
#
# Usage:
#   ./provision.sh [public-host [companion-host]]
#
# public-host: the hostname the device reaches, which Caddy requests a
#   certificate for, e.g. 203-0-113-10.nip.io (see deploy/Caddyfile's
#   comment for the nip.io pattern) or a real owned domain. Only used
#   below to remind you what to put in skypane.env - activate.sh renders
#   the Caddyfile from that file's own SKYPANE_PUBLIC_HOST/
#   SKYPANE_COMPANION_HOST values, not from these arguments.
#
# companion-host: the hostname of the companion web interface (the
#   Caddyfile's second site block). Defaults to config-<public-host>, which
#   only works when that name resolves (always true for nip.io). Pass it
#   explicitly when the companion has its own DNS name - production uses
#   skypane.algernon.ovh since 2026-09-23.
#
# Idempotent: every step below is safe to re-run (useradd/mkdir/apt/
# install/chown all no-op or overwrite cleanly on a second run), so
# re-running this script after a config change is the supported way to
# apply it.
set -euo pipefail

APP_USER="skypane"
APP_ROOT="/opt/skypane"
STATE_DIR="${APP_ROOT}/state"
BACKUP_USER="skypane-backup"
BACKUP_HOME="/var/lib/skypane-backup"
PUBLIC_HOST="${1:-}"
COMPANION_HOST="${2:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "provision.sh must run as root (sudo ./provision.sh [public-host [companion-host]])" >&2
    exit 1
fi

# Both hostnames are only printed below (never interpolated into a shell
# command), but the same strict check as render_caddyfile.sh/activate.sh
# still applies - a typo here should fail loudly, not print a bad
# suggestion.
for host in "${PUBLIC_HOST}" "${COMPANION_HOST}"; do
    if [ -n "${host}" ] && ! [[ "${host}" =~ ^[A-Za-z0-9.-]+$ ]]; then
        echo "provision.sh: invalid hostname '${host}' (letters, digits, dots and dashes only)" >&2
        exit 1
    fi
done
if [ -z "${PUBLIC_HOST}" ] && [ -n "${COMPANION_HOST}" ]; then
    echo "provision.sh: companion-host needs a public-host before it" >&2
    exit 1
fi

echo "==> Creating service user and the release-layout directories"
id -u "${APP_USER}" >/dev/null 2>&1 || \
    useradd --system --home-dir "${APP_ROOT}" --create-home \
        --shell /usr/sbin/nologin "${APP_USER}"
mkdir -p "${APP_ROOT}/releases" "${STATE_DIR}"
# APP_ROOT itself is root:skypane 0750, not skypane-owned: releases/ and
# the venv (below) must stay out of the service user's write reach so a
# compromised service cannot rewrite its own code or interpreter
# (T-37-37). Only state/ is skypane-writable.
chown "root:${APP_USER}" "${APP_ROOT}"
chmod 0750 "${APP_ROOT}"
chown root:root "${APP_ROOT}/releases"
chmod 0755 "${APP_ROOT}/releases"
chown "${APP_USER}:${APP_USER}" "${STATE_DIR}"

echo "==> Installing Python 3 and python3-venv"
# Installs whatever python3 + python3-venv the distro's own repos ship
# (the project targets the distro python3 - 3.14 on Ubuntu 26.04 - but
# nothing in server/requirements.txt is version-pinned to it - Pillow
# 12.3.0 and requests 2.34.2 are both pure-python/wheel-portable across
# recent CPython 3.x). Pinning the package name to a specific minor
# version breaks on any Ubuntu release that ships a newer default (e.g.
# 26.04 ships 3.14 as python3/python3-venv, with no python3.12 package in
# its repos at all) - using the generic package name tracks whatever the
# OS provides.
apt-get update -qq
apt-get install -y python3 python3-venv

echo "==> Installing Caddy from the official Caddy apt repository"
# Official documented install path (caddyserver.com/docs/install#debian-ubuntu-raspbian):
# a signed GPG key over HTTPS, then the repo's own signed apt source list.
# Never installed via npm - an unrelated, irrelevant low-download npm
# package shares the name "caddy" (02-RESEARCH.md Package Legitimacy note).
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
    gpg --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
    tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
apt-get update -qq
apt-get install -y caddy

echo "==> Granting caddy read access to the durable access log (CFG-03)"
# server/poll_loop.py (user skypane) tails ${STATE_DIR}/caddy-access.log
# every cycle for X-Battery-Mv telemetry (--caddy-log); caddy (user caddy)
# is the one writing it via deploy/Caddyfile's `mode 640` log directive.
# 640 alone is not enough - group ownership matters too, and Caddy's
# FileWriter has no group= option of its own to set it explicitly. Adding
# caddy to the skypane group plus setgid on STATE_DIR is what closes the
# loop: setgid makes every new/rotated log file inherit group skypane
# regardless of which user created it, and membership is what lets skypane
# actually use that group-read bit.
usermod -aG "${APP_USER}" caddy
chmod g+ws "${STATE_DIR}"

echo "==> Creating the Python virtualenv (root-owned)"
# Root-owned, not skypane-owned: services must never be able to rewrite
# their own interpreter or installed packages (T-37-37). activate.sh runs
# `pip install` as root before every deploy that needs it. A venv created
# by an earlier version of this script (skypane-owned) is re-chowned here
# on every re-run, so provisioning an existing box also narrows it.
if [ ! -d "${APP_ROOT}/venv" ]; then
    python3 -m venv "${APP_ROOT}/venv"
fi
chown -R root:root "${APP_ROOT}/venv"

echo "==> Securing skypane.env (if it already exists on this box)"
# systemd reads EnvironmentFile= as PID 1, before dropping privileges to
# the unit's own User=, so nothing running as skypane needs to read this
# file directly (confirmed by grep across server/companion/stub-server -
# see 37-RESEARCH.md SEC-07). root:root 0600 keeps every secret in it
# unreadable to the service user and to any other account on the box.
if [ -f "${APP_ROOT}/skypane.env" ]; then
    chown root:root "${APP_ROOT}/skypane.env"
    chmod 600 "${APP_ROOT}/skypane.env"
fi

echo "==> Creating the skypane-backup pull user and its directories (SEC-04, D-05)"
getent group "${BACKUP_USER}" >/dev/null 2>&1 || groupadd --system "${BACKUP_USER}"
id -u "${BACKUP_USER}" >/dev/null 2>&1 || \
    useradd --system --gid "${BACKUP_USER}" --home-dir "${BACKUP_HOME}" \
        --no-create-home --shell /bin/sh "${BACKUP_USER}"
# '*' (not '!') avoids the "locked account" refusal path some PAM stacks
# apply to '!' - the account still authenticates only through the
# forced-command SSH key installed by deploy/backup/install-backup-key.sh,
# never a password.
usermod -p '*' "${BACKUP_USER}"
# skypane-backup must never read live state through group membership -
# state/ is group-writable (g+ws above), so joining group skypane would
# hand the pull key write access to it (37-RESEARCH.md Pitfall 2).
# Removed here in case an earlier manual fix added it.
if id -nG "${BACKUP_USER}" 2>/dev/null | tr ' ' '\n' | grep -qx "${APP_USER}"; then
    gpasswd -d "${BACKUP_USER}" "${APP_USER}" >/dev/null
fi
# authorized_keys itself (root:root 0644) is written by
# deploy/backup/install-backup-key.sh, not here - this script only
# prepares the directories it needs.
install -d -o root -g root -m 0755 "${BACKUP_HOME}"
install -d -o root -g root -m 0755 "${BACKUP_HOME}/.ssh"
install -d -o "${APP_USER}" -g "${BACKUP_USER}" -m 2750 "${BACKUP_HOME}/archives"
install -d -o "${BACKUP_USER}" -g "${BACKUP_USER}" -m 0755 "${BACKUP_HOME}/pulled"

echo "==> Enabling and starting Caddy"
# Units and the Caddyfile itself are installed by deploy/activate.sh on
# every deploy (D-11) - caddy's own package-provided unit just needs to
# be enabled so it comes up on boot even before the first deploy.
systemctl enable --now caddy

echo "==> Configuring the firewall (ufw)"
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
# Explicit deny for the app port, in addition to ufw's own default-deny
# incoming policy - documents intent and survives a future accidental
# "ufw allow" for something else being added carelessly.
ufw deny 8642/tcp
# Same discipline, for the companion configuration interface's own
# loopback port - Caddy is the only thing that should ever reach it
# (deploy/Caddyfile's companion site block).
ufw deny 8643/tcp
ufw --force enable

echo "==> Hardening SSH (key-only access, PermitRootLogin no)"
"${HERE}/harden_sshd.sh"

echo "==> Provisioning complete."
echo "    Next: write ${APP_ROOT}/skypane.env by hand, root:root 0600, on this VPS only:"
echo "        install -m 600 -o root -g root deploy/skypane.env.example ${APP_ROOT}/skypane.env"
echo "        nano ${APP_ROOT}/skypane.env   # fill in real values"
if [ -n "${PUBLIC_HOST}" ]; then
    COMPANION_HOST="${COMPANION_HOST:-config-${PUBLIC_HOST}}"
    echo "    Set SKYPANE_PUBLIC_HOST=${PUBLIC_HOST} and SKYPANE_COMPANION_HOST=${COMPANION_HOST}"
else
    echo "    No public-host argument was given - fill in SKYPANE_PUBLIC_HOST and"
    echo "    SKYPANE_COMPANION_HOST by hand before the first deploy."
fi
echo "    Set SKYPANE_OFFBOX_MARKER=${BACKUP_HOME}/pulled/last-pull"
echo "    Then, from your laptop: deploy/deploy.sh ubuntu@<host> — it ships the code,"
echo "    installs the units and the rendered Caddyfile, swaps them in atomically,"
echo "    and starts every service (deploy/activate.sh, SEC-05)."
