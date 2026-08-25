#!/bin/sh
# firmware/monitor.sh - serial console capture to a timestamped log file
# under hardware/logs/, so a bring-up session is captured rather than
# scrolling away in a terminal.
#
# Usage:
#   firmware/monitor.sh <serial-port> [output-log-path]
#
# The serial port is REQUIRED, same reasoning as flash.sh - never guessed
# or wildcarded. If no output path is given, one is generated under
# hardware/logs/ with a UTC timestamp.
#
# Opens the port at the ESP32-S3 console's default baud rate (115200,
# CONFIG_ESP_CONSOLE_UART_BAUDRATE / CONFIG_MONITOR_BAUD in sdkconfig) and
# tees everything received to the log file, so it is visible live on the
# terminal AND captured on disk. Stop with Ctrl-C.

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "${SCRIPT_DIR}/.." && pwd)
LOG_DIR="${REPO_ROOT}/hardware/logs"
BAUD="115200"

PORT="${1:-}"
if [ -z "${PORT}" ]; then
    echo "Usage: $0 <serial-port> [output-log-path]" >&2
    echo "" >&2
    echo "No serial port given. Find it with:" >&2
    echo "  ls /dev/cu.*        # before plugging in" >&2
    echo "  ls /dev/cu.*        # after plugging in - the new entry is the board" >&2
    exit 1
fi

OUT="${2:-${LOG_DIR}/$(date -u +%Y%m%dT%H%M%SZ).log}"
mkdir -p "$(dirname "${OUT}")"

echo "Monitoring ${PORT} at ${BAUD} baud -> ${OUT}"
echo "(Ctrl-C to stop)"

stty -f "${PORT}" "${BAUD}" cs8 -cstopb -parenb raw -echo

cat "${PORT}" | tee "${OUT}"
