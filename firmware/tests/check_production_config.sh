#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# Proves the production configuration is what it claims to be: https-only,
# no dev-only fault injection, the ISRG-only CA bundle, and the secret
# partition in the right place. Two independent modes:
#
#   static            - checks the committed config files, no Docker/IDF
#                        needed. Runs first in CI, and locally in seconds.
#   built <build-dir>  - checks a completed idf.py build's generated
#                        sdkconfig and image. Runs after firmware.yml's
#                        build step, against firmware/build-ee02.
#
# A production build failing either mode is a release blocker, not a
# warning - see 34-CONTEXT.md's threat model (T-34-04-02, T-34-04-03).
#
# Usage: ./check_production_config.sh [static|built <build-dir>]

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FIRMWARE_DIR="${SCRIPT_DIR}/.."
MODE="${1:-static}"

# Pinned SHA-256 fingerprints, verified against letsencrypt.org and
# cross-checked against curl.se/ca/cacert.pem (Mozilla store mirror) at
# plan time - see 34-04-SUMMARY.md.
FP_X1="96:BC:EC:06:26:49:76:F3:74:60:77:9A:CF:28:C5:A7:CF:E8:A3:C0:AA:E1:1A:8F:FC:EE:05:C0:BD:DF:08:C6"
FP_X2="69:72:9B:8E:15:A8:6E:FC:17:7A:57:AF:B7:17:1D:FC:64:AD:D2:8C:2F:CA:8C:F1:50:7E:34:45:3C:CB:14:70"

FAIL=0

fail() {
    echo "FAIL: $1"
    FAIL=1
}

check_static() {
    defaults="${FIRMWARE_DIR}/sdkconfig.defaults"
    ee02="${FIRMWARE_DIR}/sdkconfig.ee02.defaults"
    partitions="${FIRMWARE_DIR}/partitions.csv"
    certs_dir="${FIRMWARE_DIR}/main/certs"

    # Dev-only opt-ins must never appear enabled in a production defaults
    # file. Comment lines (leading '#', including Kconfig's own
    # "# CONFIG_X is not set" convention) are not a violation.
    for f in "${defaults}" "${ee02}"; do
        if grep -vE '^[[:space:]]*#' "${f}" | grep -qE '^CONFIG_SKYPANE_ALLOW_HTTP=y'; then
            fail "${f} enables CONFIG_SKYPANE_ALLOW_HTTP"
        fi
        if grep -vE '^[[:space:]]*#' "${f}" | grep -qE '^CONFIG_SKYPANE_FAULT_INJECT_(PANIC|TASK_WDT|INT_WDT|SLOW_WAKE|NVS)=y'; then
            fail "${f} enables a CONFIG_SKYPANE_FAULT_INJECT_* option"
        fi
    done

    # Every production-hardening line landed in sdkconfig.defaults.
    for line in \
        'CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=n' \
        'CONFIG_ESP_TASK_WDT_PANIC=y' \
        'CONFIG_ESP_TASK_WDT_TIMEOUT_S=60' \
        'CONFIG_SPIRAM_MEMTEST=n' \
        'CONFIG_LWIP_DHCP_RESTORE_LAST_IP=y' \
        'CONFIG_LWIP_DHCP_DOES_ARP_CHECK=n' \
        'CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE=y' \
        'CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE=y' \
        'CONFIG_MBEDTLS_CUSTOM_CERTIFICATE_BUNDLE_PATH="main/certs"' \
        'CONFIG_ESP_TLS_CLIENT_SESSION_TICKETS=y' \
        'CONFIG_ESP_HTTP_CLIENT_ENABLE_CUSTOM_TRANSPORT=y' \
    ; do
        if ! grep -qF "${line}" "${defaults}"; then
            fail "sdkconfig.defaults is missing required line: ${line}"
        fi
    done

    # Orphan CONFIG_FP_* symbols must be gone.
    if grep -qE 'CONFIG_FP_API_BASE|CONFIG_FP_DEV_PROVISION_SECRET|CONFIG_FP_PROVISION_TIMEOUT_S|CONFIG_FP_FACTORY_PREP' "${defaults}"; then
        fail "sdkconfig.defaults still has an orphan CONFIG_FP_* line"
    fi

    # Watchdog timeout must stay within the Kconfig ceiling.
    twdt_s=$(grep -E '^CONFIG_ESP_TASK_WDT_TIMEOUT_S=' "${defaults}" | head -n1 | cut -d= -f2)
    if [ -z "${twdt_s}" ]; then
        fail "CONFIG_ESP_TASK_WDT_TIMEOUT_S is not set in sdkconfig.defaults"
    elif [ "${twdt_s}" -lt 1 ] || [ "${twdt_s}" -gt 60 ]; then
        fail "CONFIG_ESP_TASK_WDT_TIMEOUT_S=${twdt_s} is outside the 1..60 Kconfig range"
    fi

    # Exactly the two ISRG roots, nothing else, fingerprints match.
    pem_count=$(find "${certs_dir}" -maxdepth 1 -name '*.pem' 2>/dev/null | wc -l | tr -d ' ')
    if [ "${pem_count}" != "2" ]; then
        fail "main/certs/ has ${pem_count} .pem files, expected exactly 2"
    fi
    if command -v openssl >/dev/null 2>&1; then
        found_fp=$(for f in "${certs_dir}"/*.pem; do
            [ -e "${f}" ] || continue
            openssl x509 -in "${f}" -noout -fingerprint -sha256 2>/dev/null
        done)
        if ! printf '%s\n' "${found_fp}" | grep -qF "${FP_X1}"; then
            fail "main/certs/ is missing a PEM matching the pinned ISRG Root X1 fingerprint"
        fi
        if ! printf '%s\n' "${found_fp}" | grep -qF "${FP_X2}"; then
            fail "main/certs/ is missing a PEM matching the pinned ISRG Root X2 fingerprint"
        fi
    fi

    # The secret partition sits in the free gap without moving nvs.
    if ! grep -qE '^secret, *data, *nvs, *0x13000, *0x3000' "${partitions}"; then
        fail "partitions.csv is missing the secret partition at 0x13000/0x3000"
    fi
    if ! grep -qE '^nvs, *data, *nvs, *0x9000, *0x6000' "${partitions}"; then
        fail "partitions.csv: nvs partition has moved from 0x9000/0x6000"
    fi

    if [ "${FAIL}" -eq 0 ]; then
        echo "production-config static: PASS"
    fi
}

check_built() {
    build_dir="$1"
    sdkconfig="${build_dir}/sdkconfig"
    image="${build_dir}/skypane.bin"
    proj_desc="${build_dir}/project_description.json"

    for f in "${sdkconfig}" "${image}" "${proj_desc}"; do
        if [ ! -f "${f}" ]; then
            fail "missing built artifact: ${f}"
        fi
    done
    [ "${FAIL}" -eq 0 ] || { echo "production-config built: cannot continue, artifacts missing" >&2; return; }

    for line in \
        '# CONFIG_SKYPANE_ALLOW_HTTP is not set' \
        'CONFIG_SKYPANE_FAULT_INJECT_NONE=y' \
        'CONFIG_ESP_TASK_WDT_PANIC=y' \
        '# CONFIG_SPIRAM_MEMTEST is not set' \
        'CONFIG_MBEDTLS_CERTIFICATE_BUNDLE_DEFAULT_NONE=y' \
    ; do
        if ! grep -qF "${line}" "${sdkconfig}"; then
            fail "built sdkconfig is missing: ${line}"
        fi
    done

    # The fault-injection module (plan 34-08) logs this marker only when
    # compiled in; a production build must not contain it at all.
    if grep -a -q "SKYPANE-FAULT-INJECT" "${image}"; then
        fail "skypane.bin contains the SKYPANE-FAULT-INJECT marker"
    fi

    version=$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('project_version', ''))" "${proj_desc}")
    if [ -z "${version}" ]; then
        fail "project_description.json has an empty project_version"
    elif [ "${version}" = "1" ]; then
        fail "project_description.json project_version is \"1\" (ESP-IDF's silent git-describe fallback)"
    fi

    if [ "${FAIL}" -eq 0 ]; then
        echo "production-config built: PASS"
    fi
}

case "${MODE}" in
    static)
        check_static
        ;;
    built)
        build_dir="${2:-}"
        if [ -z "${build_dir}" ]; then
            echo "usage: $0 built <build-dir>" >&2
            exit 2
        fi
        check_built "${build_dir}"
        ;;
    *)
        echo "usage: $0 [static|built <build-dir>]" >&2
        exit 2
        ;;
esac

exit "${FAIL}"
