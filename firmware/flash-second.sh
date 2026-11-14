#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# firmware/flash-second.sh - host-side cable flash of the SECOND hardware
# type (SKYPANE_BOARD=second build) over USB. Native, like flash.sh.
#
# Usage: firmware/flash-second.sh <serial-port>
#
# The live frame is a different device on the same kind of USB cable, and a
# wrong flash is not recoverable by re-running a script. So this script:
#   1. reads the chip MAC from the port and prints it BEFORE anything is
#      written;
#   2. refuses outright when the port equals SKYPANE_LIVE_FRAME_PORT or the
#      MAC equals SKYPANE_LIVE_FRAME_MAC (both optional, set them once in
#      your shell profile; compare MAC case-insensitively);
#   3. otherwise needs the MAC typed back at an interactive prompt, so a
#      piped "yes" or a muscle-memory Enter cannot confirm it. Check the MAC
#      against the label of the evaluation unit and against the record of
#      the live frame first.
#
# The image must already be built and signed (SIGNING.md, "Local signing for
# bench images"): SKYPANE_BOARD=second ./build.sh, with SKYPANE_PROFILE=dev
# for a bench image. SKYPANE_PROFILE here selects the matching directory and
# the key the signature is verified against, exactly as in flash.sh.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

SKYPANE_PROFILE="${SKYPANE_PROFILE:-prod}"
case "${SKYPANE_PROFILE}" in
    prod) BUILD_DIR="${SCRIPT_DIR}/build-second" ;;
    dev) BUILD_DIR="${SCRIPT_DIR}/build-second-dev" ;;
    *)
        echo "ERROR: SKYPANE_PROFILE must be 'prod' or 'dev' (got '${SKYPANE_PROFILE}')" >&2
        exit 2
        ;;
esac

FLASHER_ARGS="${BUILD_DIR}/flasher_args.json"
CHIP="esp32s3"
BAUD="460800"

PORT="${1:-}"
if [ -z "${PORT}" ]; then
    echo "Usage: $0 <serial-port>" >&2
    echo "The port is required and never guessed: list the ports before and" >&2
    echo "after plugging in the evaluation unit; the new entry is the board." >&2
    exit 1
fi

if [ -n "${SKYPANE_LIVE_FRAME_PORT:-}" ] && [ "${PORT}" = "${SKYPANE_LIVE_FRAME_PORT}" ]; then
    echo "REFUSED: ${PORT} is declared as the live frame's port" >&2
    echo "(SKYPANE_LIVE_FRAME_PORT). Nothing was read or written." >&2
    exit 3
fi

if [ ! -f "${FLASHER_ARGS}" ]; then
    echo "ERROR: ${FLASHER_ARGS} not found. Run SKYPANE_BOARD=second firmware/build.sh first." >&2
    exit 1
fi
if ! command -v esptool >/dev/null 2>&1; then
    echo "ERROR: esptool not found on PATH. Install with: brew install esptool" >&2
    exit 1
fi
if ! command -v espsecure.py >/dev/null 2>&1; then
    echo "ERROR: espsecure.py not found on PATH (pip install esptool)." >&2
    exit 1
fi

# Read-only: identifies the chip behind the port before anything is written.
MAC_OUT=$(esptool --chip "${CHIP}" --port "${PORT}" read-mac 2>&1) || {
    echo "ERROR: could not read the chip MAC from ${PORT}:" >&2
    echo "${MAC_OUT}" >&2
    exit 1
}
MAC=$(printf '%s\n' "${MAC_OUT}" \
    | sed -n 's/^[[:space:]]*MAC:[[:space:]]*\([0-9A-Fa-f:]\{17\}\).*/\1/p' | head -n1)
if [ -z "${MAC}" ]; then
    echo "ERROR: no MAC found in the esptool output:" >&2
    echo "${MAC_OUT}" >&2
    exit 1
fi
MAC=$(printf '%s' "${MAC}" | tr 'A-F' 'a-f')
echo "Port: ${PORT}"
echo "Chip MAC: ${MAC}"

if [ -n "${SKYPANE_LIVE_FRAME_MAC:-}" ]; then
    LIVE_MAC=$(printf '%s' "${SKYPANE_LIVE_FRAME_MAC}" | tr 'A-F' 'a-f')
    if [ "${MAC}" = "${LIVE_MAC}" ]; then
        echo "REFUSED: ${MAC} is the live frame (SKYPANE_LIVE_FRAME_MAC). Nothing was written." >&2
        exit 3
    fi
fi

echo "This will overwrite the firmware of the device above."
echo "It must be the evaluation unit, never the live frame."
printf 'Type the MAC shown above to confirm: '
CONFIRM=""
read -r CONFIRM || true
CONFIRM=$(printf '%s' "${CONFIRM}" | tr 'A-F' 'a-f')
if [ "${CONFIRM}" != "${MAC}" ]; then
    echo "REFUSED: confirmation did not match. Nothing was written." >&2
    exit 3
fi

# Signature check, as in flash.sh: an unsigned image aborts at every boot,
# a wrongly signed one can never verify an OTA update.
APP_BIN="${BUILD_DIR}/skypane.bin"
PUBKEY="${SCRIPT_DIR}/signing/skypane-signing-pubkey.pem"
if [ "${SKYPANE_PROFILE}" = "dev" ] && [ -n "${SKYPANE_BENCH_PUBKEY:-}" ]; then
    PUBKEY="${SKYPANE_BENCH_PUBKEY}"
fi
if [ ! -f "${PUBKEY}" ]; then
    echo "ERROR: ${PUBKEY} not found; cannot verify the image is signed." >&2
    exit 1
fi
if ! espsecure.py verify_signature --version 2 --keyfile "${PUBKEY}" \
        "${APP_BIN}" >/dev/null 2>&1; then
    echo "ERROR: ${APP_BIN} has no valid signature for ${PUBKEY}." >&2
    echo "Refusing to flash it; see firmware/SIGNING.md, \"Local signing for bench images\"." >&2
    exit 1
fi
echo "Signature check: ${APP_BIN} verified against ${PUBKEY}"

# Flash settings and the offset->file map come from the build's own
# flasher_args.json, never hand-typed.
WRITE_FLASH_ARGS=$(python3 - "${FLASHER_ARGS}" <<'PYEOF'
import json, sys
fs = json.load(open(sys.argv[1]))["flash_settings"]
print("--flash-mode %s --flash-freq %s --flash-size %s" % (
    fs["flash_mode"], fs["flash_freq"], fs["flash_size"]))
PYEOF
)
FLASH_FILE_LIST=$(python3 - "${FLASHER_ARGS}" <<'PYEOF'
import json, sys
files = json.load(open(sys.argv[1]))["flash_files"]
for off in sorted(files, key=lambda x: int(x, 16)):
    print("%s %s" % (off, files[off]))
PYEOF
)
FLASH_PAIRS=""
while IFS=' ' read -r OFFSET RELPATH; do
    [ -z "${OFFSET}" ] && continue
    FLASH_PAIRS="${FLASH_PAIRS} ${OFFSET} ${BUILD_DIR}/${RELPATH}"
done <<LIST
${FLASH_FILE_LIST}
LIST

echo "Flashing ${PORT} (chip=${CHIP}, mac=${MAC}, baud=${BAUD})..."
# shellcheck disable=SC2086
esptool --chip "${CHIP}" --port "${PORT}" --baud "${BAUD}" \
    --before default-reset --after hard-reset \
    write-flash ${WRITE_FLASH_ARGS} ${FLASH_PAIRS}
echo "Flash write complete."

APP_OFFSET=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1]))['app']['offset'])" "${FLASHER_ARGS}")
APP_SIZE=$(python3 -c "import os,sys; print(os.path.getsize(sys.argv[1]))" "${APP_BIN}")
READBACK="${BUILD_DIR}/.flash-readback.bin"
echo "Verifying application region (offset=${APP_OFFSET}, size=${APP_SIZE}) ..."
esptool --chip "${CHIP}" --port "${PORT}" read-flash "${APP_OFFSET}" "${APP_SIZE}" "${READBACK}"
if cmp -s "${APP_BIN}" "${READBACK}"; then
    rm -f "${READBACK}"
    echo "flash-second.sh: SUCCESS (mac ${MAC})"
else
    echo "flash-second.sh: FAILED verification; readback kept at ${READBACK}" >&2
    exit 1
fi
