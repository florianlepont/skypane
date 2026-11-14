#!/bin/bash
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# The hardware key compiled into the firmware (Kconfig default and the EE02
# defaults file) must equal the server's LEGACY_KEY, or the frame would
# announce a type the server does not know. Needs python3 and no ESP-IDF.
set -euo pipefail

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
FIRMWARE_DIR="${SCRIPT_DIR}/.."
REPO_ROOT=$(CDPATH= cd -- "${FIRMWARE_DIR}/.." && pwd)

defaults_key=$(sed -n 's/^CONFIG_SKYPANE_HW_TYPE="\(.*\)"$/\1/p' \
    "${FIRMWARE_DIR}/sdkconfig.ee02.defaults")
kconfig_key=$(awk '
    /^[[:space:]]*config SKYPANE_HW_TYPE[[:space:]]*$/ { in_cfg = 1; next }
    in_cfg && /^[[:space:]]*config / { in_cfg = 0 }
    in_cfg && /^[[:space:]]*default "/ {
        sub(/^[[:space:]]*default "/, ""); sub(/".*$/, ""); print; exit
    }' "${FIRMWARE_DIR}/main/Kconfig.projbuild")
server_key=$(python3 -I -c "import sys; sys.path.insert(0, sys.argv[1]); from server.hardware import LEGACY_KEY; print(LEGACY_KEY)" "${REPO_ROOT}")

fail=0
if ! printf '%s' "${server_key}" | grep -Eq '^[a-z0-9-]{1,64}$'; then
    echo "FAIL: server LEGACY_KEY '${server_key}' does not match ^[a-z0-9-]{1,64}\$"
    fail=1
fi
if [ "${defaults_key}" != "${server_key}" ]; then
    echo "FAIL: sdkconfig.ee02.defaults key '${defaults_key}' != server LEGACY_KEY '${server_key}'"
    fail=1
fi
if [ "${kconfig_key}" != "${server_key}" ]; then
    echo "FAIL: Kconfig default '${kconfig_key}' != server LEGACY_KEY '${server_key}'"
    fail=1
fi
[ "${fail}" -eq 0 ] || exit 1
echo "PASS: hardware key '${server_key}' agrees in Kconfig, defaults and server"
