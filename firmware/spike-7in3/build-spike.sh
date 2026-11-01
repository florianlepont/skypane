#!/bin/sh
# Containerised ESP-IDF v5.3.1 compile of the 7.3" trial driver. Build only:
# there is no flash action here, and the source tree is mounted read-only.
# The build directory lives outside the repository so no build artefact can
# be committed.
#
# Usage: ./build-spike.sh [build|clean]
#   SPIKE_BUILD_DIR   build directory on the host (default: a fresh mktemp dir)
#   SPIKE_IDF_IMAGE   container image (default: espressif/idf:v5.3.1)
#
# Works from any working directory: resolves its own location first.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ACTION="${1:-build}"
IMAGE="${SPIKE_IDF_IMAGE:-espressif/idf:v5.3.1}"

case "${ACTION}" in
    build|clean) ;;
    *)
        echo "ERROR: only 'build' and 'clean' are supported (got '${ACTION}'); this script never flashes" >&2
        exit 2
        ;;
esac

BUILD_DIR="${SPIKE_BUILD_DIR:-$(mktemp -d)}"
case "$(CDPATH= cd -- "${BUILD_DIR}" && pwd)/" in
    "${SCRIPT_DIR}"/*)
        echo "ERROR: build directory must be outside ${SCRIPT_DIR}" >&2
        exit 2
        ;;
esac

echo "Image: ${IMAGE}"
echo "Build directory: ${BUILD_DIR}"

docker run --rm \
    -v "${SCRIPT_DIR}:/project:ro" \
    -v "${BUILD_DIR}:/build" \
    -w /project \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    "${IMAGE}" \
    idf.py \
        -B /build \
        -DSDKCONFIG=/build/sdkconfig \
        -DIDF_TARGET=esp32s3 \
        "${ACTION}"
