#!/usr/bin/env bash
# Ink Frame — first-run (and safe-to-re-run) provisioning for a fresh
# Ubuntu 26.04 LTS OVH VPS-1. Run as root (or via sudo) on the VPS
# itself, never on a laptop. Works whether the box allows direct root
# SSH login or (as on current Ubuntu cloud images, which disable it by
# default) only a passwordless-sudo non-root user - either way, invoke
# this script itself with `sudo`.
#
# Usage:
#   ./provision.sh [public-host]
#
# public-host: the hostname Caddy should request a certificate for, e.g.
#   203-0-113-10.nip.io (see deploy/Caddyfile's comment for the nip.io
#   pattern) or a real owned domain. If omitted, the Caddyfile's checked-in
#   placeholder hostname is installed as-is and must be edited by hand
#   before Caddy can obtain a valid certificate.
#
# Idempotent: every step below is safe to re-run (useradd/mkdir/apt/tee
# all no-op or overwrite cleanly on a second run), so re-running this
# script after a config change is the supported way to apply it.
set -euo pipefail

APP_USER="inkframe"
APP_ROOT="/opt/inkframe"
STATE_DIR="${APP_ROOT}/state"
PUBLIC_HOST="${1:-}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$(id -u)" -ne 0 ]; then
    echo "provision.sh must run as root (sudo ./provision.sh [public-host])" >&2
    exit 1
fi

echo "==> Creating service user and directory layout"
id -u "${APP_USER}" >/dev/null 2>&1 || \
    useradd --system --home-dir "${APP_ROOT}" --create-home \
        --shell /usr/sbin/nologin "${APP_USER}"
mkdir -p "${APP_ROOT}/server" "${APP_ROOT}/stub-server" "${STATE_DIR}"
chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}"

echo "==> Installing Python 3 and python3-venv"
# Installs whatever python3 + python3-venv the distro's own repos ship
# (server/README.md records the development target as CPython 3.12, but
# nothing in server/requirements.txt is version-pinned to it - Pillow
# 12.3.0 and requests 2.34.2 are both pure-python/wheel-portable across
# recent CPython 3.x). Pinning the package name to python3.12 breaks on
# any Ubuntu release that ships a newer default (e.g. 26.04 ships 3.14
# as python3/python3-venv, with no python3.12 package in its repos at
# all) - using the generic package name tracks whatever the OS provides.
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

echo "==> Creating the Python virtualenv"
if [ ! -d "${APP_ROOT}/venv" ]; then
    python3 -m venv "${APP_ROOT}/venv"
    chown -R "${APP_USER}:${APP_USER}" "${APP_ROOT}/venv"
fi
# server/requirements.txt is installed by deploy.sh once the code has been
# rsynced here - this script only creates the venv itself, since the
# provision/deploy split keeps "set up the machine" and "ship the code"
# independently re-runnable.

echo "==> Installing systemd unit files"
install -m 644 "${HERE}/inkframe-byos.service" /etc/systemd/system/inkframe-byos.service
install -m 644 "${HERE}/inkframe-poll.service" /etc/systemd/system/inkframe-poll.service
install -m 644 "${HERE}/inkframe-poll.timer" /etc/systemd/system/inkframe-poll.timer

echo "==> Installing the Caddyfile"
if [ -n "${PUBLIC_HOST}" ]; then
    sed "s/203-0-113-10\.nip\.io/${PUBLIC_HOST}/" "${HERE}/Caddyfile" > /etc/caddy/Caddyfile
    echo "    Caddyfile installed with public host: ${PUBLIC_HOST}"
else
    cp "${HERE}/Caddyfile" /etc/caddy/Caddyfile
    echo "    WARNING: no public-host argument given - /etc/caddy/Caddyfile" \
        "still has the placeholder hostname (203-0-113-10.nip.io)." \
        "Edit it by hand, then: systemctl reload caddy"
fi

echo "==> Reloading systemd and enabling units"
systemctl daemon-reload
# Enabled for boot, not started yet - inkframe-byos/poll need server/ and
# stub-server/ code in place first, which deploy.sh rsyncs and then starts.
systemctl enable inkframe-byos.service
systemctl enable inkframe-poll.timer
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
ufw --force enable

echo "==> Hardening SSH (key-only access)"
if [ -f /etc/ssh/sshd_config ]; then
    sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
    sed -i 's/^#\?KbdInteractiveAuthentication.*/KbdInteractiveAuthentication no/' /etc/ssh/sshd_config
    systemctl reload ssh || systemctl reload sshd || true
fi

echo "==> Provisioning complete."
echo "    Next: write ${APP_ROOT}/inkframe.env by hand (copy deploy/inkframe.env.example"
echo "    as a template, fill in real values, place it at ${APP_ROOT}/inkframe.env on this"
echo "    VPS only), then run deploy.sh from your laptop to ship the code and start the"
echo "    inkframe-byos / inkframe-poll units."
