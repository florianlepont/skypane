#!/usr/bin/env bash
# SkyPane — first-run (and safe-to-re-run) provisioning for a fresh
# Ubuntu 26.04 LTS OVH VPS-1. Run as root (sudo ./provision.sh) on the
# VPS itself, never on a laptop.
#
# Prepares the service user, release-layout directories, the backup pull
# user, SSH hardening and OS packages/firewall. It does NOT install
# systemd units or render the Caddy site file -- deploy/activate.sh does
# that on every deploy, so units and the site always match the running code.

# Usage: ./provision.sh [public-host [companion-host]]
#   public-host    hostname Caddy requests a cert for (reminder only;
#                  activate.sh renders the real value from skypane.env)
#   companion-host defaults to config-<public-host>; pass it explicitly
#                  when the companion has its own DNS name
set -euo pipefail

APP_USER="skypane"
APP_ROOT="/opt/skypane"
STATE_DIR="${APP_ROOT}/state"
BACKUP_USER="skypane-backup"
BACKUP_HOME="/var/lib/skypane-backup"
PUBLIC_HOST="${1:-}"
COMPANION_HOST="${2:-}"
CADDY_SITES_DIR="/etc/caddy/sites"
HOST_CADDYFILE="/etc/caddy/Caddyfile"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "provision.sh must run as root (sudo ./provision.sh [public-host [companion-host]])" >&2
    exit 1
fi

# Only printed below (never interpolated into a shell command), but the
# same strict check as render_caddyfile.sh/activate.sh applies -- a typo
# here should fail loudly, not print a bad suggestion.
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
# APP_ROOT is root:skypane 0750, not skypane-owned, so releases/ and the
# venv stay outside the service user's write reach -- a compromised
# service cannot rewrite its own code or interpreter. Only state/ is
# skypane-writable.
chown "root:${APP_USER}" "${APP_ROOT}"
chmod 0750 "${APP_ROOT}"
chown root:root "${APP_ROOT}/releases"
chmod 0755 "${APP_ROOT}/releases"
chown "${APP_USER}:${APP_USER}" "${STATE_DIR}"

echo "==> Installing Python 3 and python3-venv"
# Installs whatever python3/python3-venv the distro ships (3.14 on
# Ubuntu 26.04); server/requirements.txt is not pinned to it. The
# generic package name tracks whatever the OS provides -- a
# version-pinned name breaks on a release with a newer default.
apt-get update -qq
apt-get install -y python3 python3-venv

echo "==> Installing Caddy from the official Caddy apt repository"
# Official install path (caddyserver.com/docs/install#debian-ubuntu-raspbian):
# signed GPG key over HTTPS, then the repo's own signed apt source list.
# Never via npm -- an unrelated package shares the name "caddy".
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl gnupg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
    gpg --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
    tee /etc/apt/sources.list.d/caddy-stable.list >/dev/null
apt-get update -qq
apt-get install -y caddy

echo "==> Granting caddy read access to the durable access log (CFG-03)"
# server/poll_loop.py (user skypane) tails caddy-access.log for
# X-Battery-Mv telemetry; caddy (user caddy) writes it via Caddyfile's
# `mode 640`. Caddy has no group= option, so adding caddy to group
# skypane plus setgid on STATE_DIR is what lets skypane's group-read bit apply.
usermod -aG "${APP_USER}" caddy
chmod g+ws "${STATE_DIR}"

echo "==> Creating the Python virtualenv (root-owned)"
# Root-owned, not skypane-owned: services must never rewrite their own
# interpreter or packages. activate.sh runs `pip install` as root before
# a deploy that needs it. Re-chowned on every run, so an existing
# skypane-owned venv from an older script version is also narrowed here.
if [ ! -d "${APP_ROOT}/venv" ]; then
    python3 -m venv "${APP_ROOT}/venv"
fi
chown -R root:root "${APP_ROOT}/venv"

echo "==> Securing skypane.env (if it already exists on this box)"
# systemd reads EnvironmentFile= as PID 1, before dropping to the unit's
# own User=, so nothing running as skypane needs to read this file
# directly. root:root 0600 keeps every secret in it unreadable to the
# service user and to any other account on the box.
if [ -f "${APP_ROOT}/skypane.env" ]; then
    chown root:root "${APP_ROOT}/skypane.env"
    chmod 600 "${APP_ROOT}/skypane.env"
fi

echo "==> Creating the skypane-backup pull user and its directories (SEC-04, D-05)"
getent group "${BACKUP_USER}" >/dev/null 2>&1 || groupadd --system "${BACKUP_USER}"
id -u "${BACKUP_USER}" >/dev/null 2>&1 || \
    useradd --system --gid "${BACKUP_USER}" --home-dir "${BACKUP_HOME}" \
        --no-create-home --shell /bin/sh "${BACKUP_USER}"
# '*' (not '!') avoids the "locked account" refusal some PAM stacks apply
# to '!' -- this account only authenticates via the forced-command SSH
# key deploy/backup/install-backup-key.sh installs, never a password.
usermod -p '*' "${BACKUP_USER}"
# skypane-backup must never read live state through group membership --
# state/ is group-writable (g+ws above), so group skypane would hand the
# pull key write access to it. Removed here in case an earlier manual
# fix added it.
if id -nG "${BACKUP_USER}" 2>/dev/null | tr ' ' '\n' | grep -qx "${APP_USER}"; then
    gpasswd -d "${BACKUP_USER}" "${APP_USER}" >/dev/null
fi
# authorized_keys (root:root 0644) is written by install-backup-key.sh,
# not here -- this script only prepares the directories it needs.
install -d -o root -g root -m 0755 "${BACKUP_HOME}"
install -d -o root -g root -m 0755 "${BACKUP_HOME}/.ssh"
install -d -o "${APP_USER}" -g "${BACKUP_USER}" -m 2750 "${BACKUP_HOME}/archives"
install -d -o "${BACKUP_USER}" -g "${BACKUP_USER}" -m 0755 "${BACKUP_HOME}/pulled"

echo "==> Creating SkyPane's Caddy site directory"
# activate.sh writes only ${CADDY_SITES_DIR}/skypane.caddy; the shared host
# Caddyfile imports the directory's *.caddy files.
install -d -o root -g root -m 0755 "${CADDY_SITES_DIR}"

echo "==> Enabling and starting Caddy"
# Units and the Caddyfile are installed by deploy/activate.sh on every
# deploy -- this just enables caddy's package unit so it starts on boot
# before the first deploy.
systemctl enable --now caddy

echo "==> Configuring the firewall (ufw)"
apt-get install -y ufw
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
# Explicit deny for the app port too, beyond ufw's own default-deny
# incoming -- documents intent and survives a careless future "ufw allow".
ufw deny 8642/tcp
# Same discipline for the companion port -- only Caddy should ever reach
# it (deploy/Caddyfile's companion site block).
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
if ! grep -Eq '^[[:space:]]*import[[:space:]]+(sites|/etc/caddy/sites)/\*\.caddy[[:space:]]*(#.*)?$' "${HOST_CADDYFILE}" 2>/dev/null; then
    echo "    ${HOST_CADDYFILE} does not import ${CADDY_SITES_DIR} yet. It is shared with"
    echo "    other sites, so this script leaves it alone - add this line to it by hand"
    echo "    (deploy/README.md, \"Caddy layout\") before the first deploy:"
    echo "        import sites/*.caddy"
fi
echo "    Then, from your laptop: deploy/deploy.sh ubuntu@<host> — it ships the code,"
echo "    installs the units and ${CADDY_SITES_DIR}/skypane.caddy, swaps them in atomically,"
echo "    and starts every service (deploy/activate.sh, SEC-05)."
