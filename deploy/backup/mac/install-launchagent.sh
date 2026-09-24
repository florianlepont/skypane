#!/bin/sh
# SkyPane Mac-side backup pull installer (SEC-04, D-04, D-21). Installs
# the pull script, its config file, and a launchd LaunchAgent that runs
# it nightly at 09:30 local time (skypane-backup-pull.plist.template).
# Run once per Mac, by hand, after the VPS-side skypane-backup user/key
# already exist (Plan 37-07's provision.sh, a human checkpoint).
#
# Usage:
#   install-launchagent.sh <user@host> <private-key-path> [destination]
#
# destination defaults to
#   "$HOME/Library/Application Support/SkyPane/backups"
set -eu

usage() {
    echo "usage: install-launchagent.sh <user@host> <private-key-path> [destination]" >&2
    exit 1
}

[ $# -ge 2 ] || usage
[ $# -le 3 ] || usage

TARGET="$1"
KEY="$2"
DEST="${3:-$HOME/Library/Application Support/SkyPane/backups}"

# macOS privacy controls (TCC) can silently deny a background agent
# access to these three folders without Full Disk Access - refuse here
# rather than fail mysteriously on the very first real run.
case "$DEST" in
    "$HOME/Documents"/* | "$HOME/Documents")
        echo "install-launchagent.sh: refusing a destination under ~/Documents (TCC)" >&2
        exit 1
        ;;
    "$HOME/Desktop"/* | "$HOME/Desktop")
        echo "install-launchagent.sh: refusing a destination under ~/Desktop (TCC)" >&2
        exit 1
        ;;
    "$HOME/Downloads"/* | "$HOME/Downloads")
        echo "install-launchagent.sh: refusing a destination under ~/Downloads (TCC)" >&2
        exit 1
        ;;
esac

HERE="$(cd "$(dirname "$0")" && pwd)"

APP_SUPPORT="$HOME/Library/Application Support/SkyPane"
SCRIPT_DEST="$APP_SUPPORT/skypane-backup-pull.sh"
CONF_DIR="$HOME/.config/skypane"
CONF_PATH="$CONF_DIR/backup.conf"
LOG_PATH="$HOME/Library/Logs/skypane-backup-pull.log"
LAUNCHAGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_PATH="$LAUNCHAGENTS_DIR/com.skypane.backup-pull.plist"

mkdir -p "$APP_SUPPORT" "$CONF_DIR" "$(dirname "$LOG_PATH")" "$LAUNCHAGENTS_DIR" "$DEST"

cp "$HERE/skypane-backup-pull.sh" "$SCRIPT_DEST"
chmod 0755 "$SCRIPT_DEST"

cat > "$CONF_PATH" <<EOF
TARGET=$TARGET
KEY=$KEY
DEST=$DEST
EOF
chmod 0600 "$CONF_PATH"

# sed delimiter is "|" (not "/"): SCRIPT_DEST/LOG_PATH are absolute paths
# that themselves contain "/".
sed -e "s|@SCRIPT_PATH@|$SCRIPT_DEST|g" -e "s|@LOG_PATH@|$LOG_PATH|g" \
    "$HERE/skypane-backup-pull.plist.template" > "$PLIST_PATH"

UID_NUM=$(id -u)

# Re-installing over an already-loaded agent: bootout first so bootstrap
# does not fail with "already loaded". A first-time install has nothing
# to boot out - that failure is the one tolerated case (CP-9).
launchctl bootout "gui/$UID_NUM/com.skypane.backup-pull" 2>/dev/null || true
launchctl bootstrap "gui/$UID_NUM" "$PLIST_PATH"

echo "Installed com.skypane.backup-pull. Useful commands (CP-9):"
echo "  launchctl kickstart -k gui/$UID_NUM/com.skypane.backup-pull"
echo "  launchctl print gui/$UID_NUM/com.skypane.backup-pull"
echo "  tail -f \"$LOG_PATH\""
