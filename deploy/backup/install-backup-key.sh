#!/usr/bin/env bash
# SkyPane -- install the Mac's off-box backup pull key.
#
# Runs ON THE VPS AS ROOT at the human checkpoint where the developer's
# after the developer's Mac has generated its own ed25519 keypair and its
# public key line is pasted here as the one argument. Writes exactly one
# forced-command authorized_keys line (see the printf below for its exact
# shape) to /var/lib/skypane-backup/.ssh/authorized_keys.
# The `restrict,` option strips port-forwarding, agent-forwarding, X11 and
# PTY allocation from the key; the forced command fixes the ONLY program
# this key can ever run, no matter what the client asks for --
# the forced command (deploy/backup/backup_gate.py) then treats
# SSH_ORIGINAL_COMMAND itself as untrusted input.
#
# Idempotent: re-running with a (possibly different) key replaces the
# file's single line rather than appending a second one.
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

# Exactly one ed25519 public key with no leading options (rejects
# ssh-rsa, a line that already starts with command=/restrict, or any
# extra option prefix) and an optional plain-identifier comment field -
# the same character classes also reject a key containing a double
# quote, a newline or a backslash, any of which could otherwise break
# out of the double-quoted command="..." string this script writes
# below.
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
