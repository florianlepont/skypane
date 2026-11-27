#!/usr/bin/env bash
# SkyPane -- host-side loop that keeps one single-use CI runner available.
#
# Runs on the owner's Mac (under launchd, see com.skypane.ci-runner.plist.example).
# Each iteration asks GitHub for a just-in-time runner configuration, starts
# exactly one runner process inside the Linux VM with it, waits for that one
# job to finish, then wipes the runner work folder and the runner's temporary directory. The runner process in the
# VM never sees the admin token: the token is read from the macOS Keychain,
# handed to curl on its standard input as a config line (so it is on no
# command line and in no environment), and only the single-use runner
# configuration returned by GitHub crosses into the VM.
#
# Environment:
#   SKYPANE_RUNNER_REPO         owner/name of the repository (required)
#   SKYPANE_RUNNER_INDEX        1..N, part of the runner name (default 1)
#   SKYPANE_RUNNER_NAME_PREFIX  runner name prefix (default skypane-mac)
#   SKYPANE_RUNNER_VM           Lima instance name (default skypane-ci)
#   SKYPANE_RUNNER_ONCE         1 = stop after one job (used by the tests)
#
# Written for the bash 3.2 that ships with macOS: no arrays, no mapfile.
set -euo pipefail

KEYCHAIN_SERVICE="skypane-runner-pat"
RUNNER_HOME="/home/runner/actions-runner"
# The tests write their temporary directories here (pytest-of-runner, browser
# profiles), outside the work folder: left alone it grows by gigabytes.
RUNNER_TEMP_HOME="/home/runner/tmp"
LABELS='"self-hosted","skypane-ci"'
RETRY_SECONDS=30

REPO="${SKYPANE_RUNNER_REPO:-}"
INDEX="${SKYPANE_RUNNER_INDEX:-1}"
PREFIX="${SKYPANE_RUNNER_NAME_PREFIX:-skypane-mac}"
VM="${SKYPANE_RUNNER_VM:-skypane-ci}"
ONCE="${SKYPANE_RUNNER_ONCE:-0}"

if ! [[ "${REPO}" =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]; then
    echo "skypane-runner-loop: set SKYPANE_RUNNER_REPO to owner/name" >&2
    exit 2
fi
if ! [[ "${INDEX}" =~ ^[0-9]+$ ]]; then
    echo "skypane-runner-loop: SKYPANE_RUNNER_INDEX must be a number" >&2
    exit 2
fi
if ! [[ "${PREFIX}" =~ ^[A-Za-z0-9._-]+$ ]] || ! [[ "${VM}" =~ ^[A-Za-z0-9._-]+$ ]]; then
    echo "skypane-runner-loop: invalid runner name prefix or VM name" >&2
    exit 2
fi

log() {
    printf '%s skypane-runner-loop[%s]: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "${INDEX}" "$1" >&2
}

# Prints the encoded just-in-time configuration for one runner, or nothing
# when the token or the API call fails. The response body is never logged.
request_jit_config() {
    local name="$1" token body response
    token="$(security find-generic-password -s "${KEYCHAIN_SERVICE}" -w 2>/dev/null)" || return 1
    body="$(printf '{"name":"%s","runner_group_id":1,"labels":[%s],"work_folder":"_work"}' "${name}" "${LABELS}")"
    # printf is a shell builtin, so the token is not in any process's argv.
    response="$(printf 'header = "Authorization: Bearer %s"\n' "${token}" |
        curl --silent --show-error --fail --config - \
            --request POST \
            --header "Accept: application/vnd.github+json" \
            --header "X-GitHub-Api-Version: 2022-11-28" \
            --data "${body}" \
            "https://api.github.com/repos/${REPO}/actions/runners/generate-jitconfig" 2>/dev/null)" || return 1
    printf '%s\n' "${response}" |
        sed -n 's/.*"encoded_jit_config"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p'
}

wipe_work_folder() {
    limactl shell "${VM}" -- sudo -n -u runner -H find "${RUNNER_HOME}/_work" -mindepth 1 -delete || true
    limactl shell "${VM}" -- sudo -n -u runner -H find "${RUNNER_TEMP_HOME}" -mindepth 1 -delete || true
}

run_one_job() {
    local config="$1" status=0
    limactl shell "${VM}" -- sudo -n -u runner -H "${RUNNER_HOME}/run.sh" --jitconfig "${config}" || status=$?
    log "runner exited with status ${status}"
    wipe_work_folder
}

while true; do
    name="${PREFIX}-${INDEX}-$(date +%s)"
    config="$(request_jit_config "${name}")" || config=""
    if [ -z "${config}" ]; then
        log "could not get a runner configuration; retrying in ${RETRY_SECONDS}s"
        sleep "${RETRY_SECONDS}"
        continue
    fi
    log "registered ${name}"
    run_one_job "${config}"
    if [ "${ONCE}" = "1" ]; then
        exit 0
    fi
done
