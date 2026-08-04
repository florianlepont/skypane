#!/bin/sh
# Containerised ESP-IDF v5.3.1 build for the EE02 board profile - no host
# toolchain install required (01-RESEARCH.md Pitfall 4: `idf.py --version`
# answers happily on a broken host Python environment, and only a real
# build is evidence the toolchain works).
#
# This script covers BUILD only. Flashing over USB is deliberately left to
# plan 01-06 and runs natively on the host, because Docker Desktop's USB
# serial passthrough on macOS is unreliable.
#
# Usage:
#   ./build.sh            # idf.py build (default)
#   ./build.sh fullclean   # any idf.py subcommand may be passed through
#
# Works from any working directory - the script resolves its own location
# first, so `./build.sh`, `firmware/build.sh` and `bash build.sh` from
# inside firmware/ all behave the same way.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ACTION="${1:-build}"
BUILD_DIR="build-ee02"
IMAGE="espressif/idf:v5.3.1"

docker run --rm \
    -v "${SCRIPT_DIR}:/project" \
    -w /project \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    "${IMAGE}" \
    idf.py \
        -B "${BUILD_DIR}" \
        -DSDKCONFIG="${BUILD_DIR}/sdkconfig" \
        -DSDKCONFIG_DEFAULTS=sdkconfig.defaults \
        "${ACTION}"

if [ "${ACTION}" = "build" ]; then
    echo "Artifact: ${SCRIPT_DIR}/${BUILD_DIR}/inkframe.bin"
fi
