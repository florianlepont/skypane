#!/usr/bin/env bash
# SkyPane -- install the Mac's off-box backup pull key.
#
# Run ON THE VPS AS ROOT at the human checkpoint where the developer
# pastes the Mac's ed25519 public key as the one argument. Writes exactly
# one forced-command authorized_keys line to
# /var/lib/skypane-backup/.ssh/authorized_keys.

# `restrict,` strips port-forwarding, agent-forwarding, X11 and PTY
# allocation from the key; the forced command fixes the ONLY program this
# key can ever run, no matter what the client asks for. That program
# (deploy/backup/backup_gate.py) then treats SSH_ORIGINAL_COMMAND itself as untrusted input.
#
# Idempotent: re-running with a different key replaces the file's single
# line rather than appending a second one.
#
# Usage: install-backup-key.sh '<ssh-ed25519-public-key-line>'
set -euo pipefail

BACKUP_HOME="${BACKUP_HOME:-/var/lib/skypane-backup}"
GATE="${GATE:-/usr/local/lib/skypane/backup_gate.py}"
SKYPANE_KEY_ALLOW_NONROOT="${SKYPANE_KEY_ALLOW_NONROOT:-0}"

if [ "${SKYPANE_KEY_ALLOW_NONROOT}" != "1" ] && [ "$(id -u)" -ne 0 ]; then
    echo "install-backup-key.sh must run as root on the VPS" >&2
    exit 1
fi

KEY="${1:-}"
if [ -z "${KEY}" ]; then
    echo "install-backup-key.sh: usage: install-backup-key.sh '<ssh-ed25519-public-key-line>'" >&2
    exit 1
fi

# Exactly one ed25519 key, no leading options (rejects ssh-rsa or an
# already-prefixed command=/restrict line) and an optional identifier
# comment. The same character classes also reject a double quote,
# newline or backslash that could break out of the command="..." string below.
KEY_RE='^ssh-ed25519 [A-Za-z0-9+/]+={0,3}( [A-Za-z0-9@._-]+)?$'
if ! [[ "${KEY}" =~ ${KEY_RE} ]]; then
    echo "install-backup-key.sh: rejected key - expected a single 'ssh-ed25519 <base64> [comment]' line with no options" >&2
    exit 1
fi

SSH_DIR="${BACKUP_HOME}/.ssh"
AUTH_KEYS="${SSH_DIR}/authorized_keys"

install -d -m 0755 "${SSH_DIR}"
chown root:root "${SSH_DIR}"

TMP="$(mktemp -p "${SSH_DIR}")"
printf 'restrict,command="/usr/bin/python3 %s" %s\n' "${GATE}" "${KEY}" > "${TMP}"
chmod 0644 "${TMP}"
chown root:root "${TMP}"
mv -T "${TMP}" "${AUTH_KEYS}"

COMMENT="$(printf '%s' "${KEY}" | awk '{print $3}')"
echo "==> Installed pull key${COMMENT:+ for ${COMMENT}} at ${AUTH_KEYS}"
echo "    Test from the Mac (37-RESEARCH.md CP-8):"
echo "        ssh -i <private-key-file> -o IdentitiesOnly=yes skypane-backup@<vps> list"
echo "        ssh -i <private-key-file> -o IdentitiesOnly=yes skypane-backup@<vps> 'cat /opt/skypane/skypane.env'   # expect refusal"
echo "        ssh -i <private-key-file> -o IdentitiesOnly=yes -t skypane-backup@<vps>                              # expect no shell"
