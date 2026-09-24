#!/usr/bin/env bash
# SkyPane — SSH hardening drop-in writer (SEC-08, D-08).
#
# Runs ON THE VPS AS ROOT, called from deploy/provision.sh (never with
# `|| true` — its failure must fail provisioning, T-37-33). Writes
# /etc/ssh/sshd_config.d/00-skypane.conf. Ubuntu's sshd_config starts with
# "Include /etc/ssh/sshd_config.d/*.conf", and for each keyword the FIRST
# obtained value wins (sshd_config(5)) — "00-" therefore beats cloud-init's
# own "50-cloud-init.conf" drop-in without editing it.
#
# The new drop-in is validated with `sshd -t` BEFORE anything is reloaded.
# On a validation failure the previous drop-in (or its absence) is
# restored and nothing is reloaded — a bad config must never reach a
# running sshd (T-37-33). No AllowUsers (too easy to lock every account
# out at once with one typo) and no Match block (its scoping inside an
# included file is version-dependent — RESEARCH.md Assumption A11); this
# drop-in applies unconditionally to the whole host.
#
# Every path and binary below is an overridable variable so the whole
# flow can run against a fake root and a stub sshd in CI
# (deploy/tests/test_provision.py) with no VPS and no root.
#
# Usage: harden_sshd.sh
set -euo pipefail

SSHD_CONFIG_DIR="${SSHD_CONFIG_DIR:-/etc/ssh/sshd_config.d}"
SSHD_CONFIG="${SSHD_CONFIG:-/etc/ssh/sshd_config}"
SSHD_BIN="${SSHD_BIN:-sshd}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"

DROPIN="${SSHD_CONFIG_DIR}/00-skypane.conf"

echo "==> Checking ${SSHD_CONFIG} includes ${SSHD_CONFIG_DIR}"
if ! grep -Eq '^[[:space:]]*Include[[:space:]]+/etc/ssh/sshd_config\.d/\*\.conf[[:space:]]*$' "${SSHD_CONFIG}"; then
    echo "harden_sshd.sh: ${SSHD_CONFIG} has no 'Include /etc/ssh/sshd_config.d/*.conf' line - the drop-in would be ignored" >&2
    exit 1
fi

mkdir -p "${SSHD_CONFIG_DIR}"

HAD_PREVIOUS=0
BACKUP=""
if [ -f "${DROPIN}" ]; then
    HAD_PREVIOUS=1
    BACKUP="$(mktemp)"
    cp "${DROPIN}" "${BACKUP}"
fi

echo "==> Writing ${DROPIN}"
# sshd -t only reads installed *.conf files, so the new drop-in must
# already be in place (not a staged .new file) for validation to see it.
TMP="$(mktemp)"
printf '%s\n' \
    "PermitRootLogin no" \
    "PasswordAuthentication no" \
    "KbdInteractiveAuthentication no" \
    "PubkeyAuthentication yes" \
    "PermitEmptyPasswords no" \
    "X11Forwarding no" \
    "MaxAuthTries 3" \
    > "${TMP}"
install -m 0644 "${TMP}" "${DROPIN}"
rm -f "${TMP}"

echo "==> Validating with sshd -t"
if ! "${SSHD_BIN}" -t -f "${SSHD_CONFIG}"; then
    echo "harden_sshd.sh: sshd -t rejected the new drop-in - restoring the previous configuration, not reloading" >&2
    if [ "${HAD_PREVIOUS}" = "1" ]; then
        cp "${BACKUP}" "${DROPIN}"
    else
        rm -f "${DROPIN}"
    fi
    rm -f "${BACKUP}"
    exit 1
fi
rm -f "${BACKUP}"

echo "==> Reloading sshd"
# Ubuntu >=22.10 starts sshd via ssh.socket activation, so a not-yet-running
# sshd is fine here too - the next connection picks up the new config.
"${SYSTEMCTL}" try-reload-or-restart ssh.service

echo "==> Effective sshd configuration (filtered):"
"${SSHD_BIN}" -T -f "${SSHD_CONFIG}" 2>/dev/null \
    | grep -Ei '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication|pubkeyauthentication|maxauthtries) ' \
    || true
