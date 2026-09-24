#!/usr/bin/env bash
# SkyPane — VPS-side atomic, verified deploy (SEC-05, D-09/D-10/D-11).
#
# Runs ON THE VPS AS ROOT, invoked over ssh by deploy/deploy.sh, once
# deploy.sh has streamed one git SHA's committed tree into
# releases/.incoming-<sha>/. Idempotent: re-running with the same sha
# while `current` already points at it only restarts the services and
# re-probes — it never re-extracts.
#
# Flow: stage the release -> install/reinstall dependencies if their hash
# changed -> byte-compile -> smoke-test the release's own scripts ->
# render SkyPane's own Caddy site file and validate the whole host config
# with it in place -> install units and swap `current` atomically
# (ln -sfn + mv -T) -> restart services and reload Caddy only if the site
# file actually changed -> probe every unit and both
# HTTP(S) surfaces. Any failure rolls the swap back to the previous
# release (if one exists) and always exits non-zero, so a bad deploy
# leaves a red CI job and the previously-working release still serving
# traffic (T-37-26).
#
# The host's /etc/caddy/Caddyfile is shared with other projects on the
# same VPS, so this script only ever reads and validates it — it never
# writes it. SkyPane owns exactly one file, ${CADDY_SITE_FILE}
# (/etc/caddy/sites/skypane.caddy), which the host Caddyfile pulls in via
# a one-time `import sites/*.caddy` line (deploy/README.md). Backup and
# staging copies live in the same directory under leading-dot names that
# do not end in `.caddy`, so the import glob never loads them.
#
# Every system path below is an overridable variable, not hard-coded, so
# this whole flow can be exercised against a fake root in CI
# (deploy/tests/conftest.py) with no VPS and no real root.
# SKYPANE_ACTIVATE_ALLOW_NONROOT is for that use only — production always
# runs this script as root.
#
# skypane.env is parsed with a strict, anchored `sed` line regex below —
# never `source`d or `.`d. systemd's own EnvironmentFile= syntax is not
# shell syntax, and sourcing the operator's file here would execute it as
# root (T-37-27); a poison line in deploy/tests/conftest.py's fake env
# file proves this script never does that.
#
# Usage: activate.sh <sha> [<incoming-dir>]
set -euo pipefail

SHA="${1:?usage: activate.sh <sha> [<incoming-dir>]}"

SKYPANE_ROOT="${SKYPANE_ROOT:-/opt/skypane}"
INCOMING="${2:-${SKYPANE_ROOT}/releases/.incoming-${SHA}}"
VENV="${VENV:-${SKYPANE_ROOT}/venv}"
ENV_FILE="${ENV_FILE:-${SKYPANE_ROOT}/skypane.env}"
SYSTEMD_UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"
CADDYFILE="${CADDYFILE:-/etc/caddy/Caddyfile}"
CADDY_SITES_DIR="${CADDY_SITES_DIR:-/etc/caddy/sites}"
CADDY_SITE_FILE="${CADDY_SITE_FILE:-${CADDY_SITES_DIR}/skypane.caddy}"
BACKUP_GATE_DIR="${BACKUP_GATE_DIR:-/usr/local/lib/skypane}"
BACKUP_ROOT="${BACKUP_ROOT:-/var/lib/skypane-backup}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
PROBE_TIMEOUT_S="${PROBE_TIMEOUT_S:-30}"
SKYPANE_ACTIVATE_ALLOW_NONROOT="${SKYPANE_ACTIVATE_ALLOW_NONROOT:-0}"

RELEASE_DIR="${SKYPANE_ROOT}/releases/${SHA}"
CURRENT_LINK="${SKYPANE_ROOT}/current"
SITE_FILE_NAME="$(basename "${CADDY_SITE_FILE}")"
SITE_FILE_NEW="${CADDY_SITES_DIR}/.${SITE_FILE_NAME}.new"
SITE_FILE_PREV="${CADDY_SITES_DIR}/.${SITE_FILE_NAME}.prev"
# CADDY_REPLACED: the site file on disk was changed by this run.
# SITE_HAD_PREV: a site file existed before this run (SITE_FILE_PREV
# holds it). CADDY_RELOADED: Caddy has been told about the change — before
# that point a failure must put the old file back so the next unrelated
# reload does not pick up an unvalidated or unreleased config.
CADDY_REPLACED=0
SITE_HAD_PREV=0
CADDY_RELOADED=0

echo "==> Root guard"
if [ "${SKYPANE_ACTIVATE_ALLOW_NONROOT}" != "1" ] && [ "$(id -u)" -ne 0 ]; then
    echo "activate.sh must run as root (invoked by deploy.sh over ssh with sudo)" >&2
    exit 1
fi

if ! [[ "${SHA}" =~ ^[0-9a-f]{7,40}$ ]]; then
    echo "activate.sh: invalid sha '${SHA}' (expected 7-40 lowercase hex characters)" >&2
    exit 1
fi

echo "==> Checking prerequisites (deploy/provision.sh must have run first)"
if [ ! -f "${ENV_FILE}" ]; then
    echo "activate.sh: ${ENV_FILE} not found — run deploy/provision.sh first" >&2
    exit 1
fi
if [ ! -x "${VENV}/bin/python3" ]; then
    echo "activate.sh: ${VENV}/bin/python3 not found — run deploy/provision.sh first" >&2
    exit 1
fi
if [ ! -d "${BACKUP_ROOT}/archives" ] || [ ! -d "${BACKUP_ROOT}/pulled" ]; then
    echo "activate.sh: ${BACKUP_ROOT}/{archives,pulled} not found — run deploy/provision.sh first" >&2
    exit 1
fi
if [ ! -d "${CADDY_SITES_DIR}" ]; then
    echo "activate.sh: ${CADDY_SITES_DIR} not found — run deploy/provision.sh first" >&2
    exit 1
fi
if [ ! -f "${CADDYFILE}" ] \
    || ! grep -Eq '^[[:space:]]*import[[:space:]]+(sites|/etc/caddy/sites)/\*\.caddy[[:space:]]*(#.*)?$' "${CADDYFILE}"; then
    echo "activate.sh: ${CADDYFILE} does not import SkyPane's site file —" \
        "add 'import sites/*.caddy' to /etc/caddy/Caddyfile (see deploy/README.md)" >&2
    exit 1
fi

echo "==> Parsing ${ENV_FILE} (strict anchored regex, never sourced)"
_extract_env() {
    # $1 = key. Anchored to column 0 with a fixed key name (no metachars
    # from the key ever reach sed as part of the pattern), one value per
    # match, last match wins — this only ever *reads* the file.
    sed -n "s/^${1}=\\(.*\\)\$/\\1/p" "${ENV_FILE}" | tail -n1
}
SKYPANE_PUBLIC_HOST="$(_extract_env SKYPANE_PUBLIC_HOST)"
SKYPANE_COMPANION_HOST="$(_extract_env SKYPANE_COMPANION_HOST)"
SKYPANE_BYOS_PORT="$(_extract_env SKYPANE_BYOS_PORT)"
SKYPANE_COMPANION_PORT="$(_extract_env SKYPANE_COMPANION_PORT)"

for _host in "${SKYPANE_PUBLIC_HOST}" "${SKYPANE_COMPANION_HOST}"; do
    if [ -z "${_host}" ] || ! [[ "${_host}" =~ ^[A-Za-z0-9.-]+$ ]]; then
        echo "activate.sh: invalid or missing hostname in ${ENV_FILE} ('${_host}')" >&2
        exit 1
    fi
done
for _port in "${SKYPANE_BYOS_PORT}" "${SKYPANE_COMPANION_PORT}"; do
    if [ -z "${_port}" ] || ! [[ "${_port}" =~ ^[0-9]+$ ]]; then
        echo "activate.sh: invalid or missing port in ${ENV_FILE} ('${_port}')" >&2
        exit 1
    fi
done

echo "==> Staging release ${SHA}"
if [ ! -d "${RELEASE_DIR}" ]; then
    if [ ! -d "${INCOMING}" ]; then
        echo "activate.sh: incoming release not found: ${INCOMING}" >&2
        exit 1
    fi
    mv -T "${INCOMING}" "${RELEASE_DIR}"
else
    # Redeploying a sha already staged (a re-run job) - the freshly
    # streamed duplicate is discarded, never re-extracted.
    rm -rf "${INCOMING}"
fi
chown -R root:root "${RELEASE_DIR}"
chmod -R go-w "${RELEASE_DIR}"

echo "==> Checking requirements hash"
REQ_FILE="${RELEASE_DIR}/server/requirements.txt"
HASH_FILE="${VENV}/.requirements.sha256"
NEW_HASH="$(sha256sum "${REQ_FILE}" | awk '{print $1}')"
OLD_HASH="$(cat "${HASH_FILE}" 2>/dev/null || :)"
if [ "${NEW_HASH}" != "${OLD_HASH}" ]; then
    echo "    requirements changed - installing"
    "${VENV}/bin/pip" install --require-hashes --quiet -r "${REQ_FILE}"
    echo "${NEW_HASH}" > "${HASH_FILE}"
else
    echo "    requirements unchanged - skipping pip install"
fi

echo "==> Byte-compiling release (services cannot write __pycache__ under ProtectSystem=strict)"
"${VENV}/bin/python3" -m compileall -q "${RELEASE_DIR}"

echo "==> Smoke-testing release scripts"
if ! "${VENV}/bin/python3" "${RELEASE_DIR}/companion/app.py" --help >/dev/null 2>&1 \
    || ! "${VENV}/bin/python3" "${RELEASE_DIR}/server/poll_loop.py" --help >/dev/null 2>&1 \
    || ! "${VENV}/bin/python3" "${RELEASE_DIR}/stub-server/byos_server.py" --help >/dev/null 2>&1 \
    || ! "${VENV}/bin/python3" "${RELEASE_DIR}/deploy/backup/skypane_backup.py" --help >/dev/null 2>&1; then
    echo "activate.sh: smoke check failed for release ${SHA} - not swapping" >&2
    exit 1
fi

restore_site_file() {
    if [ "${SITE_HAD_PREV}" = "1" ]; then
        mv -f "${SITE_FILE_PREV}" "${CADDY_SITE_FILE}"
    else
        rm -f "${CADDY_SITE_FILE}"
    fi
    CADDY_REPLACED=0
}

# Invoked only through the EXIT trap below.
# shellcheck disable=SC2317
on_exit() {
    local _rc=$?
    rm -f "${SITE_FILE_NEW}"
    if [ "${_rc}" -ne 0 ] && [ "${CADDY_REPLACED}" = "1" ] && [ "${CADDY_RELOADED}" != "1" ]; then
        restore_site_file || :
    fi
}
trap on_exit EXIT

echo "==> Rendering SkyPane's Caddy site file and validating the host config"
"${RELEASE_DIR}/deploy/render_caddyfile.sh" "${RELEASE_DIR}/deploy/Caddyfile" \
    "${SKYPANE_PUBLIC_HOST}" "${SKYPANE_COMPANION_HOST}" > "${SITE_FILE_NEW}"
chmod 0644 "${SITE_FILE_NEW}"
if cmp -s "${SITE_FILE_NEW}" "${CADDY_SITE_FILE}" 2>/dev/null; then
    echo "    ${CADDY_SITE_FILE} unchanged - no Caddy reload needed"
    rm -f "${SITE_FILE_NEW}"
else
    if [ -f "${CADDY_SITE_FILE}" ]; then
        cp -p "${CADDY_SITE_FILE}" "${SITE_FILE_PREV}"
        SITE_HAD_PREV=1
    fi
    mv -f "${SITE_FILE_NEW}" "${CADDY_SITE_FILE}"
    CADDY_REPLACED=1
    # The site file is only meaningful inside the host config that imports
    # it (another project's blocks, global options), so the whole host
    # Caddyfile is what gets validated, not the snippet on its own.
    if ! runuser -u caddy -- caddy validate --config "${CADDYFILE}" --adapter caddyfile; then
        restore_site_file
        echo "activate.sh: Caddy config validation failed - site file restored, not swapping" >&2
        exit 1
    fi
fi

# prev is read *before* the swap below, so both the rollback path and the
# redeploy short-circuit can use it. A missing `current` (the very first
# deploy after cutover) makes readlink fail - the only spot in this
# script where a failure is deliberately swallowed instead of handled by
# an if/case, matching the plan's own reference implementation.
PREV_TARGET="$(readlink "${CURRENT_LINK}" || true)"
REDEPLOY=0
if [ -n "${PREV_TARGET}" ] && [ "${PREV_TARGET}" = "releases/${SHA}" ]; then
    REDEPLOY=1
fi

if [ "${REDEPLOY}" != "1" ]; then
    echo "==> Installing units and the off-box backup gate"
    for _unit_file in "${RELEASE_DIR}"/deploy/skypane-*.service "${RELEASE_DIR}"/deploy/skypane-*.timer; do
        [ -e "${_unit_file}" ] || continue
        install -m 0644 "${_unit_file}" "${SYSTEMD_UNIT_DIR}/$(basename "${_unit_file}")"
    done
    install -D -m 0755 "${RELEASE_DIR}/deploy/backup/backup_gate.py" "${BACKUP_GATE_DIR}/backup_gate.py"
    chown root:root "${BACKUP_GATE_DIR}/backup_gate.py"
    systemctl daemon-reload
    systemctl enable skypane-byos.service skypane-companion.service skypane-poll.timer skypane-backup.timer

    echo "==> Swapping current -> releases/${SHA}"
    ln -sfn "releases/${SHA}" "${SKYPANE_ROOT}/.current.tmp"
    mv -T "${SKYPANE_ROOT}/.current.tmp" "${CURRENT_LINK}"
else
    echo "==> Redeploying already-current sha ${SHA} - restart and probe only"
fi

echo "==> Restarting services"
systemctl restart skypane-byos.service
systemctl restart skypane-companion.service
systemctl restart skypane-poll.timer
systemctl start skypane-backup.timer

if [ "${CADDY_REPLACED}" = "1" ]; then
    CADDY_RELOADED=1
    systemctl reload caddy
fi

probe_once() {
    FAILED_PROBE=""
    for _unit in skypane-byos.service skypane-companion.service skypane-poll.timer caddy.service; do
        if ! systemctl is-active --quiet "${_unit}"; then
            FAILED_PROBE="unit:${_unit}"
            return 1
        fi
    done

    local _code
    _code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${SKYPANE_BYOS_PORT}/device/v1/display" 2>/dev/null || echo 000)"
    if [ "${_code}" != "401" ]; then
        FAILED_PROBE="http:byos-loopback(${_code})"
        return 1
    fi

    _code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:${SKYPANE_COMPANION_PORT}/login" 2>/dev/null || echo 000)"
    if [ "${_code}" != "200" ]; then
        FAILED_PROBE="http:companion-loopback(${_code})"
        return 1
    fi

    local _out
    _out="$(curl -sS -o /dev/null -D - -w '%{http_code}' --resolve "${SKYPANE_PUBLIC_HOST}:443:127.0.0.1" "https://${SKYPANE_PUBLIC_HOST}/device/v1/display" 2>/dev/null || echo 000)"
    _code="$(printf '%s' "${_out}" | tail -n1)"
    if [ "${_code}" != "401" ] || ! printf '%s' "${_out}" | grep -qi '^Strict-Transport-Security:'; then
        FAILED_PROBE="https:byos(${_code})"
        return 1
    fi

    _out="$(curl -sS -o /dev/null -D - -w '%{http_code}' --resolve "${SKYPANE_COMPANION_HOST}:443:127.0.0.1" "https://${SKYPANE_COMPANION_HOST}/login" 2>/dev/null || echo 000)"
    _code="$(printf '%s' "${_out}" | tail -n1)"
    if [ "${_code}" != "200" ] || ! printf '%s' "${_out}" | grep -qi '^Strict-Transport-Security:'; then
        FAILED_PROBE="https:companion(${_code})"
        return 1
    fi

    return 0
}

echo "==> Probing (timeout ${PROBE_TIMEOUT_S}s)"
PROBE_OK=0
_start_ts="$(date +%s)"
while :; do
    if probe_once; then
        PROBE_OK=1
        break
    fi
    _now_ts="$(date +%s)"
    if [ $(( _now_ts - _start_ts )) -ge "${PROBE_TIMEOUT_S}" ]; then
        break
    fi
    sleep 1
done

if [ "${PROBE_OK}" != "1" ]; then
    echo "activate.sh: probe failed: ${FAILED_PROBE}" >&2
    for _unit in skypane-byos.service skypane-companion.service skypane-poll.timer skypane-backup.timer; do
        journalctl -u "${_unit}" -n 50 --no-pager || :
    done

    if [ -z "${PREV_TARGET}" ]; then
        echo "activate.sh: no previous release to roll back to" >&2
        exit 1
    fi

    echo "==> Rolling back to ${PREV_TARGET}"
    PREV_RELEASE_DIR="${SKYPANE_ROOT}/${PREV_TARGET}"

    ln -sfn "${PREV_TARGET}" "${SKYPANE_ROOT}/.current.tmp"
    mv -T "${SKYPANE_ROOT}/.current.tmp" "${CURRENT_LINK}"

    for _unit_file in "${PREV_RELEASE_DIR}"/deploy/skypane-*.service "${PREV_RELEASE_DIR}"/deploy/skypane-*.timer; do
        [ -e "${_unit_file}" ] || continue
        install -m 0644 "${_unit_file}" "${SYSTEMD_UNIT_DIR}/$(basename "${_unit_file}")"
    done
    systemctl daemon-reload

    # Only SkyPane's own site file is restored; the shared host Caddyfile
    # was never written. With no earlier site file (the first
    # release-layout deploy), the new one stays: the previous release has
    # no other way to be served over HTTPS.
    if [ "${CADDY_REPLACED}" = "1" ] && [ "${SITE_HAD_PREV}" = "1" ]; then
        restore_site_file
        systemctl reload caddy || :
    fi

    systemctl restart skypane-byos.service || :
    systemctl restart skypane-companion.service || :
    systemctl restart skypane-poll.timer || :

    probe_once || :
    echo "activate.sh: rollback complete, last probe status: ${FAILED_PROBE:-ok}" >&2
    exit 1
fi

echo "==> Pruning old releases (keep ${KEEP_RELEASES})"
CURRENT_SHA="${SHA}"
PREV_SHA="${PREV_TARGET#releases/}"

declare -A _KEEP=()
_KEEP["${CURRENT_SHA}"]=1
if [ -n "${PREV_SHA}" ]; then
    _KEEP["${PREV_SHA}"]=1
fi

_RELEASE_LIST=()
while IFS= read -r _name; do
    _RELEASE_LIST+=("${_name}")
done < <(find "${SKYPANE_ROOT}/releases" -maxdepth 1 -mindepth 1 -type d -not -name '.incoming-*' -printf '%T@ %f\n' | sort -rn | awk '{print $2}')

for _name in "${_RELEASE_LIST[@]}"; do
    if [ "${#_KEEP[@]}" -ge "${KEEP_RELEASES}" ]; then
        break
    fi
    _KEEP["${_name}"]=1
done

for _name in "${_RELEASE_LIST[@]}"; do
    if [ -z "${_KEEP[${_name}]:-}" ]; then
        rm -rf "${SKYPANE_ROOT}/releases/${_name}"
    fi
done

find "${SKYPANE_ROOT}/releases" -maxdepth 1 -mindepth 1 -type d -name '.incoming-*' -exec rm -rf {} +

echo "==> Deploy of ${SHA} complete."
exit 0
