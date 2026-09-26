#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# firmware/provision.sh - writes a fresh, random per-device enrolment
# secret into the dedicated "secret" NVS partition over USB.
# The secret authenticates POST /device/v1/setup for this MAC (see
# stub-server/byos_server.py's registry); it is never the byos bearer
# token itself and this script never touches the main "nvs" partition
# (token, image hash, backoff counter, boot counter) unless
# --reset-device-state is explicitly passed.
#
# Usage:
#   firmware/provision.sh <serial-port> [--reset-device-state]
#   firmware/provision.sh --dry-run <mac>
#
# The serial port is REQUIRED and never guessed - find it with
# `ls /dev/cu.*` before and after plugging the board in (same discipline
# as flash.sh; flashing the wrong device is not recoverable by re-running
# this script).
#
# --reset-device-state additionally erases the main "nvs" partition
# (bearer token, image hash, backoff counter, boot counter, cached DHCP
# lease) - only pass this when the device should also forget who it
# thinks it is. Without it, only the "secret" partition is touched.
#
# --dry-run <mac> generates a secret and prints the registry line and
# registration commands without touching any hardware - useful to
# preview what a real run against that MAC would print. Every dry run
# (and every real run) generates a NEW secret, so re-running this script
# for an already-provisioned device means the registry entry must be
# replaced (hence --replace in the printed commands below).
#
# Works from any working directory - resolves its own location first,
# same as build.sh/flash.sh.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
IMAGE="espressif/idf:v5.3.1"
CHIP="esp32s3"

usage() {
    cat >&2 <<USAGE
Usage:
  firmware/provision.sh <serial-port> [--reset-device-state]
  firmware/provision.sh --dry-run <mac>

<serial-port> is REQUIRED and never guessed. Find it with:
  ls /dev/cu.*        # before plugging in
  ls /dev/cu.*        # after plugging in - the new entry is the board

--reset-device-state additionally erases the main nvs partition (bearer
token, image hash, backoff counter, boot counter, cached DHCP lease).
Only pass this when the device should also forget who it thinks it is.

--dry-run <mac> previews the registry line and registration commands
for <mac> without touching any hardware.
USAGE
}

# --- 1. Argument parsing -----------------------------------------------

DRY_RUN=0
RESET_DEVICE_STATE=0
PORT=""
MAC=""

if [ "$#" -eq 0 ]; then
    usage
    exit 2
fi

case "$1" in
    --dry-run)
        if [ "$#" -ne 2 ]; then
            usage
            exit 2
        fi
        DRY_RUN=1
        MAC="$2"
        ;;
    --*)
        usage
        exit 2
        ;;
    *)
        PORT="$1"
        shift
        while [ "$#" -gt 0 ]; do
            case "$1" in
                --reset-device-state)
                    RESET_DEVICE_STATE=1
                    ;;
                *)
                    usage
                    exit 2
                    ;;
            esac
            shift
        done
        ;;
esac

# --- 2. Tool checks ------------------------------------------------------

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "ERROR: '$1' not found on PATH. $2" >&2
        exit 1
    fi
}

require_cmd docker "Install Docker Desktop (macOS) or docker.io (Linux)."
require_cmd python3 "Install Python 3 (python3.org or your OS package manager)."
if [ "${DRY_RUN}" -eq 0 ]; then
    require_cmd esptool "Install with: pip install esptool"
fi

# --- 3. Parse partitions.csv for the secret/nvs offsets and sizes -------
# Never hard-coded: read from the committed partitions.csv so this script
# can never drift from what the flashed image actually uses.

PART_VARS=$(python3 - "${SCRIPT_DIR}/partitions.csv" <<'PYEOF'
import sys

path = sys.argv[1]
rows = {}
with open(path) as f:
    for line in f:
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        fields = [p.strip() for p in line.split(",")]
        if len(fields) < 5:
            continue
        name, type_, subtype, offset, size = fields[:5]
        rows[name] = (type_, subtype, offset, size)


def need(name, type_, subtype):
    if name not in rows:
        print("ERROR: partition '%s' not found in %s" % (name, path), file=sys.stderr)
        sys.exit(1)
    t, st, off, sz = rows[name]
    if t != type_ or st != subtype:
        print("ERROR: partition '%s' is not type=%s subtype=%s" % (name, type_, subtype),
              file=sys.stderr)
        sys.exit(1)
    return off, sz


secret_off, secret_size = need("secret", "data", "nvs")
nvs_off, nvs_size = need("nvs", "data", "nvs")
print("SEC_PART_OFFSET=%s" % secret_off)
print("SEC_PART_SIZE=%s" % secret_size)
print("NVS_OFFSET=%s" % nvs_off)
print("NVS_SIZE=%s" % nvs_size)
PYEOF
)
eval "${PART_VARS}"
SEC_PART_SIZE_DEC=$((SEC_PART_SIZE))

# --- 4. MAC: read from the device outside dry-run, or use the given arg -
# The ESP32-S3 Wi-Fi station MAC equals the base MAC esptool reports here,
# which is exactly what the firmware sends in POST /device/v1/setup.

if [ "${DRY_RUN}" -eq 0 ]; then
    MAC_OUTPUT=$(esptool --chip "${CHIP}" --port "${PORT}" --after no-reset read-mac)
    MAC=$(printf '%s\n' "${MAC_OUTPUT}" \
        | grep -oE '([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}' \
        | head -1 \
        | tr 'A-F' 'a-f')
fi
MAC=$(printf '%s' "${MAC}" | tr 'A-F' 'a-f')

if ! printf '%s' "${MAC}" | grep -Eq '^[0-9a-f]{2}(:[0-9a-f]{2}){5}$'; then
    echo "ERROR: '${MAC}' is not a MAC address (aa:bb:cc:dd:ee:ff)" >&2
    exit 1
fi

# --- 5. Private, self-cleaning work directory ----------------------------

umask 077
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT INT TERM

# --- 6/7. Generate the secret and write the NVS source CSV --------------
# The secret lives only in this shell variable and inside $WORK for the
# lifetime of this script - never echoed, never written anywhere else.

SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

printf 'key,type,encoding,value\n' > "${WORK}/secret.csv"
printf 'skypane,namespace,,\n' >> "${WORK}/secret.csv"
printf 'enrol_secret,data,string,%s\n' "${SECRET}" >> "${WORK}/secret.csv"

# --- 8. Generate the NVS partition image in the pinned container --------

docker run --rm \
    -v "${WORK}:/work" \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    "${IMAGE}" \
    sh -c "python \"\$IDF_PATH/components/nvs_flash/nvs_partition_generator/nvs_partition_gen.py\" generate /work/secret.csv /work/secret.bin ${SEC_PART_SIZE_DEC}"

GENERATED_SIZE=$(python3 -c "import os; print(os.path.getsize('${WORK}/secret.bin'))")
if [ "${GENERATED_SIZE}" != "${SEC_PART_SIZE_DEC}" ]; then
    echo "ERROR: generated secret.bin is ${GENERATED_SIZE} bytes, expected ${SEC_PART_SIZE_DEC}" >&2
    exit 1
fi

# --- 9. Write only the secret partition, verify by read-back ------------
# parttool.py needs serial access from inside the container, which this
# project avoids on macOS (see flash.sh's own comment). Writing the single
# partition's byte range with host esptool, at the offset read from
# partitions.csv above, is the same non-destructive operation.

if [ "${DRY_RUN}" -eq 0 ]; then
    echo "Writing secret partition (offset=${SEC_PART_OFFSET}, size=${SEC_PART_SIZE_DEC}) to ${PORT} ..."
    esptool --chip "${CHIP}" --port "${PORT}" --after no-reset \
        write-flash "${SEC_PART_OFFSET}" "${WORK}/secret.bin"

    esptool --chip "${CHIP}" --port "${PORT}" --after no-reset \
        read-flash "${SEC_PART_OFFSET}" "${SEC_PART_SIZE_DEC}" "${WORK}/readback.bin"

    if ! cmp -s "${WORK}/secret.bin" "${WORK}/readback.bin"; then
        echo "ERROR: read-back of the secret partition does not match what was written" >&2
        exit 1
    fi
    echo "Secret partition verified byte-for-byte."

    if [ "${RESET_DEVICE_STATE}" -eq 1 ]; then
        echo "Erasing main nvs partition (offset=${NVS_OFFSET}, size=${NVS_SIZE}) -" \
             "this drops the bearer token, last image hash, backoff counter," \
             "boot counter and cached DHCP lease."
        esptool --chip "${CHIP}" --port "${PORT}" --after no-reset \
            erase-region "${NVS_OFFSET}" "${NVS_SIZE}"
    fi

    esptool --chip "${CHIP}" --port "${PORT}" --after hard-reset read-mac >/dev/null
fi

# --- 10. Registry hash, then drop the secret from this shell ------------

HASH=$(printf '%s' "${SECRET}" | python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.read().encode("ascii")).hexdigest())')
unset SECRET

# --- 11. Report --------------------------------------------------------

if [ "${DRY_RUN}" -eq 1 ]; then
    echo "Dry run for ${MAC} (nothing written)"
else
    echo "Provisioned ${MAC}"
fi
echo "Registry line: ${MAC} ${HASH}"
echo ""
echo "Register on the local stub server:"
echo "  python3 stub-server/devices_cli.py --state-dir <state-dir> add --mac ${MAC} --secret-sha256 ${HASH} --replace"
echo ""
echo "Register on the VPS:"
echo "  ssh <ssh-target> \"sudo -u skypane /opt/skypane/venv/bin/python3 /opt/skypane/current/stub-server/devices_cli.py --state-dir /opt/skypane/state add --mac ${MAC} --secret-sha256 ${HASH} --replace\""
echo ""
echo "Note: re-running this script generates a NEW secret for ${MAC}, so the" \
     "registry entry must be replaced - that is why --replace is in both" \
     "commands above."
