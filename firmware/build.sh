#!/bin/sh
# Containerised ESP-IDF v5.3.1 build for the EE02 board profile - no host
# toolchain install required (`idf.py --version` answers happily on a
# broken host Python environment, and only a real build is evidence the
# toolchain works).
#
# This script covers BUILD only. Flashing over USB is deliberately left to
# flash.sh and runs natively on the host, because Docker Desktop's USB
# serial passthrough on macOS is unreliable.
#
# Usage:
#   ./build.sh                                    # production build (default)
#   ./build.sh fullclean                          # any idf.py subcommand may be passed through
#   SKYPANE_PROFILE=dev ./build.sh                # dev build, http allowed, separate build dir
#   SKYPANE_PROFILE=dev SKYPANE_FAULT=panic ./build.sh   # dev build with a fault-injection hook compiled in
#
# SKYPANE_PROFILE: prod (default) | dev. dev uses its own build directory
# (build-ee02-dev) and layers sdkconfig.dev.defaults (CONFIG_SKYPANE_ALLOW_HTTP=y)
# on top of the production defaults, so a dev image can never be confused
# with, or accidentally reused as, a production one.
#
# SKYPANE_FAULT: none (default) | panic | task_wdt | int_wdt | slow_wake | nvs.
# Selects one SKYPANE_FAULT_INJECT_* Kconfig choice for bench verification
# of the reset/backoff and deadline paths. Refused outside SKYPANE_PROFILE=dev
# - a production image can never carry a fault hook.
#
# Works from any working directory - the script resolves its own location
# first, so `./build.sh`, `firmware/build.sh` and `bash build.sh` from
# inside firmware/ all behave the same way.

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

VER=$(git -C "${SCRIPT_DIR}" describe --tags --always --dirty 2>/dev/null || true)
[ -z "${VER}" ] && VER="0.0.0-nogit"
[ "${SKYPANE_PROFILE}" = "dev" ] && VER="${VER}-dev"
[ "${SKYPANE_FAULT}" != "none" ] && VER="${VER}-${SKYPANE_FAULT}"
VER=$(printf '%s' "${VER}" | cut -c1-31)

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
