#!/bin/sh
# Containerised ESP-IDF v5.3.1 build for the EE02 board profile -- no
# host toolchain install required, and only a real build proves the
# toolchain works.
#
# Build only: flash.sh runs natively on the host (Docker Desktop's macOS
# USB passthrough is unreliable), so build.sh stays containerised.

# Usage: ./build.sh [idf.py-subcommand]
#   SKYPANE_PROFILE=dev ./build.sh              # dev build, http allowed
#   SKYPANE_PROFILE=dev SKYPANE_FAULT=panic ./build.sh   # bench fault hook
#   SKYPANE_RELEASE_TAG=fw-v1.0.0 ./build.sh    # tagged release build
#
# SKYPANE_PROFILE: prod (default) | dev. dev uses its own build directory
# and layers sdkconfig.dev.defaults (CONFIG_SKYPANE_ALLOW_HTTP=y), so a
# dev image can never be confused with a production one.
#
# SKYPANE_FAULT: none (default) | panic | task_wdt | int_wdt | slow_wake |
# nvs -- selects one fault-injection Kconfig choice for bench verification.
# Refused outside SKYPANE_PROFILE=dev; a production image can never carry one.
#
# SKYPANE_RELEASE_TAG: unset (default) | a release tag matching fw-vX.Y.Z.
# When set, HEAD must already carry exactly that tag on a clean tree, and
# the reported version is the tag itself, not a git-describe string -- a
# release build's version can never drift from the tag that names it.
#
# SKYPANE_VERSION_LABEL: unset (default) | a short lowercase/digit label,
# for example "unsigned". Appends "-<label>" to a release version for a
# bench image built from a release tag (fw-v1.0.1-unsigned); the release
# CI job never sets this.
#
# Works from any working directory: resolves its own location first.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ACTION="${1:-build}"
IMAGE="espressif/idf:v5.3.1"

SKYPANE_PROFILE="${SKYPANE_PROFILE:-prod}"
SKYPANE_FAULT="${SKYPANE_FAULT:-none}"

case "${SKYPANE_PROFILE}" in
    prod|dev) ;;
    *)
        echo "ERROR: SKYPANE_PROFILE must be 'prod' or 'dev' (got '${SKYPANE_PROFILE}')" >&2
        exit 2
        ;;
esac

case "${SKYPANE_FAULT}" in
    none|panic|task_wdt|int_wdt|slow_wake|nvs) ;;
    *)
        echo "ERROR: SKYPANE_FAULT must be one of none|panic|task_wdt|int_wdt|slow_wake|nvs (got '${SKYPANE_FAULT}')" >&2
        exit 2
        ;;
esac

if [ "${SKYPANE_PROFILE}" = "prod" ] && [ "${SKYPANE_FAULT}" != "none" ]; then
    echo "ERROR: fault injection is dev-only; set SKYPANE_PROFILE=dev to use SKYPANE_FAULT" >&2
    exit 2
fi

SKYPANE_RELEASE_TAG="${SKYPANE_RELEASE_TAG:-}"
SKYPANE_VERSION_LABEL="${SKYPANE_VERSION_LABEL:-}"

# Checked before anything touches Docker: a malformed tag or label is a
# usage error, not a build failure worth waiting on a container for.
if [ -n "${SKYPANE_RELEASE_TAG}" ]; then
    if ! printf '%s' "${SKYPANE_RELEASE_TAG}" \
        | grep -Eq '^fw-v(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})\.(0|[1-9][0-9]{0,3})$'; then
        echo "ERROR: SKYPANE_RELEASE_TAG '${SKYPANE_RELEASE_TAG}' does not match fw-vMAJOR.MINOR.PATCH" >&2
        exit 2
    fi
fi
if [ -n "${SKYPANE_VERSION_LABEL}" ]; then
    if ! printf '%s' "${SKYPANE_VERSION_LABEL}" | grep -Eq '^[a-z0-9]{1,12}$'; then
        echo "ERROR: SKYPANE_VERSION_LABEL '${SKYPANE_VERSION_LABEL}' must match [a-z0-9]{1,12}" >&2
        exit 2
    fi
fi

if [ "${SKYPANE_PROFILE}" = "dev" ]; then
    BUILD_DIR="build-ee02-dev"
    SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.ee02.defaults;sdkconfig.dev.defaults"
    if [ "${SKYPANE_FAULT}" != "none" ]; then
        FAULT_UPPER=$(printf '%s' "${SKYPANE_FAULT}" | tr '[:lower:]' '[:upper:]')
        mkdir -p "${SCRIPT_DIR}/${BUILD_DIR}"
        echo "CONFIG_SKYPANE_FAULT_INJECT_${FAULT_UPPER}=y" > "${SCRIPT_DIR}/${BUILD_DIR}/sdkconfig.fault.defaults"
        SDKCONFIG_DEFAULTS="${SDKCONFIG_DEFAULTS};${BUILD_DIR}/sdkconfig.fault.defaults"
    fi
else
    BUILD_DIR="build-ee02"
    SDKCONFIG_DEFAULTS="sdkconfig.defaults;sdkconfig.ee02.defaults"
fi

if [ "${ACTION}" = "build" ]; then
    # Every build regenerates sdkconfig from the committed defaults, so a
    # stale local sdkconfig (e.g. left over from a previous dev/fault
    # build) can never silently carry a dev option into a production image.
    rm -f "${SCRIPT_DIR}/${BUILD_DIR}/sdkconfig"
fi

if [ -n "${SKYPANE_RELEASE_TAG}" ]; then
    # A release build's version can only ever be the tag that names it:
    # require HEAD to already carry exactly that tag (not an ancestor, not
    # a later commit) on a tree with nothing uncommitted, so the built
    # image and the tagged source are provably the same thing.
    HEAD_TAG=$(git -C "${SCRIPT_DIR}" describe --tags --exact-match --match 'fw-v*' HEAD 2>/dev/null || true)
    if [ "${HEAD_TAG}" != "${SKYPANE_RELEASE_TAG}" ]; then
        echo "ERROR: HEAD is not tagged ${SKYPANE_RELEASE_TAG} (git describe --exact-match reports '${HEAD_TAG:-<none>}')" >&2
        exit 2
    fi
    if [ -n "$(git -C "${SCRIPT_DIR}" status --porcelain)" ]; then
        echo "ERROR: working tree is not clean; a release build must match its tag exactly" >&2
        exit 2
    fi
    VER="${SKYPANE_RELEASE_TAG}"
    [ -n "${SKYPANE_VERSION_LABEL}" ] && VER="${VER}-${SKYPANE_VERSION_LABEL}"
    VER=$(printf '%s' "${VER}" | cut -c1-31)
    echo "Release: ${SKYPANE_RELEASE_TAG}"
else
    # --match restricts describe to release tags, so an untagged or
    # dirty build can never print a bare release tag: it is always a
    # commit hash or fw-vX.Y.Z-N-g<hash>[-dirty], distinguishable from
    # a real release version at a glance.
    VER=$(git -C "${SCRIPT_DIR}" describe --tags --always --dirty --match 'fw-v*' 2>/dev/null || true)
    [ -z "${VER}" ] && VER="0.0.0-nogit"
    [ "${SKYPANE_PROFILE}" = "dev" ] && VER="${VER}-dev"
    [ "${SKYPANE_FAULT}" != "none" ] && VER="${VER}-${SKYPANE_FAULT}"
    VER=$(printf '%s' "${VER}" | cut -c1-31)
fi

echo "Firmware version: ${VER}"
echo "Profile: ${SKYPANE_PROFILE} fault=${SKYPANE_FAULT}"

docker run --rm \
    -v "${SCRIPT_DIR}:/project" \
    -w /project \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    "${IMAGE}" \
    idf.py \
        -B "${BUILD_DIR}" \
        -DSDKCONFIG="${BUILD_DIR}/sdkconfig" \
        -DSDKCONFIG_DEFAULTS="${SDKCONFIG_DEFAULTS}" \
        -DPROJECT_VER="${VER}" \
        "${ACTION}"

if [ "${ACTION}" = "build" ]; then
    echo "Artifact: ${SCRIPT_DIR}/${BUILD_DIR}/skypane.bin"
fi
