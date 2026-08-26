#!/bin/sh
# firmware/flash.sh - host-side flash of the EE02 build artifact over USB,
# native (not containerised) - Docker Desktop's macOS USB passthrough is
# unreliable, so build.sh stays containerised while flashing runs on the
# host (see build.sh's own comment).
#
# Usage:
#   firmware/flash.sh <serial-port>
#
# The serial port is REQUIRED and never guessed or wildcarded. Find it
# with `ls /dev/cu.*` before and after plugging the board in - the newly
# appeared entry is the board. Flashing the wrong device is not
# recoverable by re-running this script.
#
# Flash offsets and file names are read from the build's own generated
# flasher_args.json, never hand-typed, so they can never drift from what
# build.sh actually produced. After writing, the application region is
# read back off the device and compared byte-for-byte against
# build-ee02/skypane.bin; a partial or corrupted flash is caught here,
# not misdiagnosed later as a firmware bug (T-01-06-01).

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
BUILD_DIR="${SCRIPT_DIR}/build-ee02"
FLASHER_ARGS="${BUILD_DIR}/flasher_args.json"
CHIP="esp32s3"
BAUD="460800"

PORT="${1:-}"
if [ -z "${PORT}" ]; then
    echo "Usage: $0 <serial-port>" >&2
    echo "" >&2
    echo "No serial port given. Find it with:" >&2
    echo "  ls /dev/cu.*        # before plugging in" >&2
    echo "  ls /dev/cu.*        # after plugging in - the new entry is the board" >&2
    echo "Never pass a wildcard or guess - flashing the wrong device is not" >&2
    echo "recoverable by re-running this script." >&2
    exit 1
fi

if [ ! -f "${FLASHER_ARGS}" ]; then
    echo "ERROR: ${FLASHER_ARGS} not found. Run firmware/build.sh first." >&2
    exit 1
fi

if ! command -v esptool >/dev/null 2>&1; then
    echo "ERROR: esptool not found on PATH. Install with: brew install esptool" >&2
    exit 1
fi

ESPTOOL_VERSION=$(esptool version 2>&1 | head -1)
echo "esptool: ${ESPTOOL_VERSION}"

# Flash settings (mode/freq/size) and the offset->file map, straight out of
# the build's own generated flasher_args.json.
WRITE_FLASH_ARGS=$(python3 - "${FLASHER_ARGS}" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
fs = d["flash_settings"]
print("--flash-mode %s --flash-freq %s --flash-size %s" % (
    fs["flash_mode"], fs["flash_freq"], fs["flash_size"]))
PYEOF
)

FLASH_FILE_LIST=$(python3 - "${FLASHER_ARGS}" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
files = d["flash_files"]
for off in sorted(files, key=lambda x: int(x, 16)):
    print("%s %s" % (off, files[off]))
PYEOF
)

FLASH_PAIRS=""
while IFS=' ' read -r OFFSET RELPATH; do
    [ -z "${OFFSET}" ] && continue
    FLASH_PAIRS="${FLASH_PAIRS} ${OFFSET} ${BUILD_DIR}/${RELPATH}"
done <<EOF
${FLASH_FILE_LIST}
EOF

echo "Flashing ${PORT} (chip=${CHIP}, baud=${BAUD})..."
# shellcheck disable=SC2086
esptool --chip "${CHIP}" --port "${PORT}" --baud "${BAUD}" \
    --before default-reset --after hard-reset \
    write-flash ${WRITE_FLASH_ARGS} ${FLASH_PAIRS}

echo "Flash write complete."

verify_flash() {
    APP_BIN="${BUILD_DIR}/skypane.bin"
    APP_OFFSET=$(python3 -c "import json; print(json.load(open('${FLASHER_ARGS}'))['app']['offset'])")
    APP_SIZE=$(python3 -c "import os; print(os.path.getsize('${APP_BIN}'))")
    READBACK="${BUILD_DIR}/.flash-readback.bin"

    echo "Verifying application region (offset=${APP_OFFSET}, size=${APP_SIZE}) against ${APP_BIN} ..."
    esptool --chip "${CHIP}" --port "${PORT}" \
        read-flash "${APP_OFFSET}" "${APP_SIZE}" "${READBACK}"

    if cmp -s "${APP_BIN}" "${READBACK}"; then
        echo "verify_flash: OK - flashed application region matches ${APP_BIN} byte-for-byte (${APP_SIZE} bytes)"
        rm -f "${READBACK}"
        return 0
    else
        echo "verify_flash: MISMATCH - flashed application region does not match ${APP_BIN}" >&2
        echo "Readback kept at ${READBACK} for inspection." >&2
        return 1
    fi
}

if verify_flash; then
    echo "flash.sh: SUCCESS"
    exit 0
else
    echo "flash.sh: FAILED verification" >&2
    exit 1
fi
