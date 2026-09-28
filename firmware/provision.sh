#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# firmware/provision.sh - writes a fresh, random per-device enrolment
# secret, the Wi-Fi SSID/password, the API base and an optional static-IP
# set into the "secret" NVS partition over USB. Authenticates POST
# /device/v1/setup for this MAC; never touches the main "nvs" partition
# unless --reset-device-state is passed. Nothing this script writes is
# ever compiled into a firmware image, so a built image is identical for
# every device (see firmware/main/enrol_secret.c's fp_device_creds_load).

# Usage:
#   firmware/provision.sh <serial-port> --wifi-ssid <ssid> --api-base <url>
#       [--static-ip <ip> --static-mask <mask> --static-gw <gw> --static-dns <dns>]
#       [--allow-http-base] [--reset-device-state]
#   firmware/provision.sh --dry-run <mac> --wifi-ssid <ssid> --api-base <url> ...
#
# The serial port is REQUIRED, never guessed (same discipline as flash.sh).
# --wifi-ssid and --api-base are REQUIRED in both modes.
#
# The Wi-Fi password comes from the SKYPANE_WIFI_PASS environment variable
# if set, or a no-echo prompt otherwise (never on the command line, never
# echoed, never logged). An empty password provisions an open network.
#
# --static-ip/--static-mask/--static-gw/--static-dns must all be given
# together, or not at all - a partially-provisioned static IP is refused.
#
# --allow-http-base permits an http:// --api-base for a dev board talking
# to stub-server/ on the LAN; a production device requires https://.
#
# --reset-device-state additionally erases the main "nvs" partition
# (bearer token, image hash, backoff/boot counters, cached DHCP lease) --
# only pass this when the device should also forget who it thinks it is.
#
# --dry-run <mac> generates a secret and prints the registry line,
# registration commands and the secret-partition CSV (Wi-Fi password
# redacted) without touching hardware and without ever prompting for the
# password. Every run (dry or real) generates a NEW enrolment secret, so
# re-running for an already-provisioned device means the registry entry
# must be replaced (--replace below).
#
# Works from any working directory: resolves its own location first.

set -eu

SCRIPT_DIR=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
IMAGE="espressif/idf:v5.3.1"
CHIP="esp32s3"

usage() {
    cat >&2 <<USAGE
Usage:
  firmware/provision.sh <serial-port> --wifi-ssid <ssid> --api-base <url>
      [--static-ip <ip> --static-mask <mask> --static-gw <gw> --static-dns <dns>]
      [--allow-http-base] [--reset-device-state]
  firmware/provision.sh --dry-run <mac> --wifi-ssid <ssid> --api-base <url> ...

<serial-port> is REQUIRED and never guessed. Find it with:
  ls /dev/cu.*        # before plugging in
  ls /dev/cu.*        # after plugging in - the new entry is the board

--wifi-ssid <ssid> and --api-base <url> are REQUIRED in both modes. The
Wi-Fi password comes from \$SKYPANE_WIFI_PASS or a no-echo prompt.

--static-ip/--static-mask/--static-gw/--static-dns: give all four or none.

--allow-http-base permits an http:// --api-base (dev board only).

--reset-device-state additionally erases the main nvs partition (bearer
token, image hash, backoff counter, boot counter, cached DHCP lease).
Only pass this when the device should also forget who it thinks it is.

--dry-run <mac> previews the registry line, registration commands and
the secret-partition CSV (password redacted) for <mac> without touching
any hardware.
USAGE
}

# --- 1. Argument parsing -----------------------------------------------

DRY_RUN=0
RESET_DEVICE_STATE=0
ALLOW_HTTP_BASE=0
PORT=""
MAC=""
WIFI_SSID_SET=0
WIFI_SSID=""
API_BASE_SET=0
API_BASE=""
STATIC_IP_SET=0
STATIC_IP=""
STATIC_MASK_SET=0
STATIC_MASK=""
STATIC_GW_SET=0
STATIC_GW=""
STATIC_DNS_SET=0
STATIC_DNS=""

if [ "$#" -eq 0 ]; then
    usage
    exit 2
fi

case "$1" in
    --dry-run)
        if [ "$#" -lt 2 ]; then
            usage
            exit 2
        fi
        DRY_RUN=1
        MAC="$2"
        shift 2
        ;;
    --*)
        usage
        exit 2
        ;;
    *)
        PORT="$1"
        shift
        ;;
esac

while [ "$#" -gt 0 ]; do
    case "$1" in
        --reset-device-state)
            RESET_DEVICE_STATE=1
            shift
            ;;
        --allow-http-base)
            ALLOW_HTTP_BASE=1
            shift
            ;;
        --wifi-ssid)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            WIFI_SSID="$2"
            WIFI_SSID_SET=1
            shift 2
            ;;
        --api-base)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            API_BASE="$2"
            API_BASE_SET=1
            shift 2
            ;;
        --static-ip)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            STATIC_IP="$2"
            STATIC_IP_SET=1
            shift 2
            ;;
        --static-mask)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            STATIC_MASK="$2"
            STATIC_MASK_SET=1
            shift 2
            ;;
        --static-gw)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            STATIC_GW="$2"
            STATIC_GW_SET=1
            shift 2
            ;;
        --static-dns)
            [ "$#" -ge 2 ] || { usage; exit 2; }
            STATIC_DNS="$2"
            STATIC_DNS_SET=1
            shift 2
            ;;
        *)
            usage
            exit 2
            ;;
    esac
done

if [ "${WIFI_SSID_SET}" -ne 1 ]; then
    echo "ERROR: --wifi-ssid is required" >&2
    exit 2
fi
if [ "${API_BASE_SET}" -ne 1 ]; then
    echo "ERROR: --api-base is required" >&2
    exit 2
fi

STATIC_COUNT=$((STATIC_IP_SET + STATIC_MASK_SET + STATIC_GW_SET + STATIC_DNS_SET))
if [ "${STATIC_COUNT}" -ne 0 ] && [ "${STATIC_COUNT}" -ne 4 ]; then
    echo "ERROR: --static-ip/--static-mask/--static-gw/--static-dns must" \
         "all be given together, or not at all" >&2
    exit 2
fi

# --- 2. Credential validation --------------------------------------------
# Mirrors firmware/main/creds.c's rules exactly, so a value this script
# accepts is a value the device will accept too.

reject_comma_or_newline() {
    name="$1"
    val="$2"
    case "${val}" in
        *,*)
            echo "ERROR: ${name} must not contain a comma" >&2
            exit 2
            ;;
    esac
    if [ "$(printf '%s' "${val}" | wc -l | tr -d ' ')" -ne 0 ]; then
        echo "ERROR: ${name} must not contain a newline" >&2
        exit 2
    fi
}

validate_ssid() {
    ssid="$1"
    len=$(printf '%s' "${ssid}" | wc -c | tr -d ' ')
    if [ "${len}" -lt 1 ] || [ "${len}" -gt 32 ]; then
        echo "ERROR: --wifi-ssid must be 1-32 bytes (got ${len})" >&2
        exit 2
    fi
    if printf '%s' "${ssid}" | LC_ALL=C grep -q '[[:cntrl:]]'; then
        echo "ERROR: --wifi-ssid must not contain a control character" >&2
        exit 2
    fi
    reject_comma_or_newline "--wifi-ssid" "${ssid}"
}

validate_pass() {
    pass="$1"
    len=$(printf '%s' "${pass}" | wc -c | tr -d ' ')
    if [ "${len}" -eq 0 ]; then
        return 0 # "" is a valid open network
    fi
    if [ "${len}" -lt 8 ] || [ "${len}" -gt 63 ]; then
        echo "ERROR: the Wi-Fi password must be empty or 8-63 bytes" \
             "(got ${len})" >&2
        exit 2
    fi
    if printf '%s' "${pass}" | LC_ALL=C grep -q '[^ -~]'; then
        echo "ERROR: the Wi-Fi password must be printable ASCII" >&2
        exit 2
    fi
    reject_comma_or_newline "the Wi-Fi password" "${pass}"
}

validate_api_base() {
    base="$1"
    case "${base}" in
        https://?*) ;;
        http://?*)
            if [ "${ALLOW_HTTP_BASE}" -ne 1 ]; then
                echo "ERROR: --api-base must be https:// (pass" \
                     "--allow-http-base for a dev board)" >&2
                exit 2
            fi
            ;;
        *)
            echo "ERROR: --api-base must start with https:// (or" \
                 "http:// with --allow-http-base)" >&2
            exit 2
            ;;
    esac
    reject_comma_or_newline "--api-base" "${base}"
}

validate_ipv4() {
    name="$1"
    ip="$2"
    if ! printf '%s' "${ip}" | grep -Eq '^([0-9]{1,3}\.){3}[0-9]{1,3}$'; then
        echo "ERROR: ${name} is not a dotted-quad IPv4 address (aa.bb.cc.dd)" >&2
        exit 2
    fi
    old_ifs=${IFS}
    IFS=.
    # shellcheck disable=SC2086  # deliberate word-split of a regex-validated dotted quad
    set -- ${ip}
    IFS=${old_ifs}
    for octet in "$1" "$2" "$3" "$4"; do
        if [ "${#octet}" -gt 1 ]; then
            first=${octet%"${octet#?}"}
            if [ "${first}" = "0" ]; then
                echo "ERROR: ${name} has a leading zero in an octet (${octet})" >&2
                exit 2
            fi
        fi
        if [ "${octet}" -gt 255 ]; then
            echo "ERROR: ${name} has an octet greater than 255 (${octet})" >&2
            exit 2
        fi
    done
}

validate_ssid "${WIFI_SSID}"
validate_api_base "${API_BASE}"
if [ "${STATIC_COUNT}" -eq 4 ]; then
    validate_ipv4 "--static-ip" "${STATIC_IP}"
    validate_ipv4 "--static-mask" "${STATIC_MASK}"
    validate_ipv4 "--static-gw" "${STATIC_GW}"
    validate_ipv4 "--static-dns" "${STATIC_DNS}"
fi

# --- 3. Wi-Fi password: environment, or a no-echo prompt ----------------
# Read before any hardware or Docker activity, and before the private
# work directory even exists - never on the command line (visible in
# `ps`/shell history), never echoed to the terminal, never logged.

if [ "${SKYPANE_WIFI_PASS+set}" = "set" ]; then
    WIFI_PASS="${SKYPANE_WIFI_PASS}"
elif [ "${DRY_RUN}" -eq 1 ]; then
    WIFI_PASS="" # --dry-run never prompts and never needs the password
else
    STTY_ORIG=$(stty -g)
    trap 'stty "${STTY_ORIG}"' EXIT INT TERM
    printf 'Wi-Fi password for %s (empty for an open network): ' "${WIFI_SSID}" >&2
    stty -echo
    IFS= read -r WIFI_PASS
    stty "${STTY_ORIG}"
    trap - EXIT INT TERM
    printf '\n' >&2
fi
validate_pass "${WIFI_PASS}"

# --- 4. Tool checks ------------------------------------------------------

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

# --- 5. Parse partitions.csv for the secret/nvs offsets and sizes -------
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

# --- 6. MAC: read from the device outside dry-run, or use the given arg -
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

# --- 7. Private, self-cleaning work directory ----------------------------

umask 077
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT INT TERM

# --- 8/9. Generate the secret and write the NVS source CSV --------------
# The secret and the Wi-Fi password live only in this shell and inside
# $WORK for the lifetime of this script - never echoed, never written
# anywhere else.

SECRET=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

{
    printf 'key,type,encoding,value\n'
    printf 'skypane,namespace,,\n'
    printf 'enrol_secret,data,string,%s\n' "${SECRET}"
    printf 'wifi_ssid,data,string,%s\n' "${WIFI_SSID}"
    printf 'wifi_pass,data,string,%s\n' "${WIFI_PASS}"
    printf 'api_base,data,string,%s\n' "${API_BASE}"
    if [ "${STATIC_COUNT}" -eq 4 ]; then
        printf 'static_ip,data,string,%s\n' "${STATIC_IP}"
        printf 'static_mask,data,string,%s\n' "${STATIC_MASK}"
        printf 'static_gw,data,string,%s\n' "${STATIC_GW}"
        printf 'static_dns,data,string,%s\n' "${STATIC_DNS}"
    fi
} > "${WORK}/secret.csv"

if [ "${DRY_RUN}" -eq 1 ]; then
    echo "Secret-partition CSV (Wi-Fi password redacted):"
    sed 's/^wifi_pass,data,string,.*/wifi_pass,data,string,<redacted>/' \
        "${WORK}/secret.csv"
    echo ""
fi

unset WIFI_PASS

# --- 10. Generate the NVS partition image in the pinned container -------

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

# --- 11. Write only the secret partition, verify by read-back -----------
# parttool.py needs serial access from inside the container, which this
# project avoids on macOS (flash.sh's own comment); writing the single
# partition's byte range with host esptool at the partitions.csv offset
# is the same non-destructive operation.

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

# --- 12. Registry hash, then drop the secret from this shell ------------

HASH=$(printf '%s' "${SECRET}" | python3 -c 'import hashlib,sys; print(hashlib.sha256(sys.stdin.read().encode("ascii")).hexdigest())')
unset SECRET

# --- 13. Report -----------------------------------------------------------

if [ "${DRY_RUN}" -eq 1 ]; then
    echo "Dry run for ${MAC} (nothing written)"
else
    echo "Provisioned ${MAC} (Wi-Fi SSID, API base and enrolment secret" \
         "written to its secret partition)"
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
