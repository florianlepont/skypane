#!/bin/sh
# SkyPane Mac-side off-box backup pull (SEC-04, D-04). Runs nightly from
# launchd (skypane-backup-pull.plist.template), pulling archives through
# the VPS's narrow forced-command gate (deploy/backup/backup_gate.py) -
# it never pushes anything back to the VPS. Safe to run repeatedly:
# already-present, checksum-verified archives are never re-fetched, and a
# partial or corrupted fetch never leaves a bad file behind and never
# advances the freshness marker the companion's Health page reads.
#
# Config: ${SKYPANE_BACKUP_CONF:-$HOME/.config/skypane/backup.conf}, three
# lines: TARGET=user@host, KEY=/path/to/private/key, DEST=/path/to/backups
#
# POSIX sh only - macOS ships /bin/bash 3.2, so this deliberately avoids
# every bash-ism (double-bracket conditionals, arrays, the array-reading
# builtin bash adds, GNU-only flags such as a negative head line count or
# a recursive readlink) and runs equally well under dash.
set -eu

CONF="${SKYPANE_BACKUP_CONF:-$HOME/.config/skypane/backup.conf}"

if [ ! -f "$CONF" ]; then
    echo "skypane-backup-pull: config not found: $CONF" >&2
    exit 1
fi

# The config file is PARSED, never sourced (`.`/`source`) - it is
# operator-editable input, and sourcing it would let an arbitrary line in
# it run as shell code instead of being read as plain key=value text.
_conf_get() {
    sed -n "s/^$1=\\(.*\\)\$/\\1/p" "$CONF" | tail -n 1
}

TARGET=$(_conf_get TARGET)
KEY=$(_conf_get KEY)
DEST=$(_conf_get DEST)

if [ -z "$TARGET" ] || [ -z "$KEY" ] || [ -z "$DEST" ]; then
    echo "skypane-backup-pull: TARGET/KEY/DEST must all be set in $CONF" >&2
    exit 1
fi

mkdir -p "$DEST"

log() {
    printf '==> %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1"
}

ssh_cmd() {
    ssh -o BatchMode=yes -o IdentitiesOnly=yes -o ConnectTimeout=20 \
        -o ServerAliveInterval=15 -i "$KEY" "$TARGET" "$1"
}

list_remote() {
    attempt=1
    while [ "$attempt" -le 3 ]; do
        if list_out=$(ssh_cmd list); then
            printf '%s\n' "$list_out"
            return 0
        fi
        attempt=$((attempt + 1))
        if [ "$attempt" -le 3 ]; then
            sleep "${SKYPANE_PULL_RETRY_SLEEP:-20}"
        fi
    done
    return 1
}

# BSD `date` (macOS, production) understands `-v-11m`; GNU `date` (the
# Linux test environment) understands `-d '11 months ago'` instead -
# tried in that order, silently, so this runs unmodified on both.
cutoff_month() {
    if date -u -v-11m +%Y%m >/dev/null 2>&1; then
        date -u -v-11m +%Y%m
    else
        date -u -d '11 months ago' +%Y%m
    fi
}

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/skypane-backup-pull.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT

ARCHIVE_RE='^skypane-state-[0-9]{8}T[0-9]{6}Z\.tar\.gz$'

log "listing archives on ${TARGET}"
if ! list_remote > "$WORKDIR/list.txt"; then
    echo "skypane-backup-pull: list failed after 3 attempts" >&2
    exit 1
fi

FAILED=0
NEWEST=""
while IFS=' ' read -r name _size sha; do
    [ -z "$name" ] && continue
    if ! printf '%s\n' "$name" | grep -Eq "$ARCHIVE_RE"; then
        continue
    fi
    # POSIX test has no string ordering; archive names sort lexically in
    # time order, so the later of the two is the last line of `sort`.
    if [ -z "$NEWEST" ] || [ "$(printf '%s\n%s\n' "$NEWEST" "$name" | sort | tail -n 1)" = "$name" ]; then
        NEWEST="$name"
    fi
    if [ -f "$DEST/$name" ]; then
        continue
    fi

    log "fetching $name"
    partial="$DEST/.$name.partial"
    if ! ssh_cmd "get $name" > "$partial"; then
        rm -f "$partial"
        log "fetch failed: $name"
        FAILED=1
        continue
    fi
    got_sha=$(shasum -a 256 "$partial" | awk '{print $1}')
    if [ "$got_sha" != "$sha" ]; then
        rm -f "$partial"
        log "checksum mismatch, discarded: $name"
        FAILED=1
        continue
    fi
    mv "$partial" "$DEST/$name"
    log "verified: $name"
done < "$WORKDIR/list.txt"

if [ "$FAILED" -eq 0 ] && [ -n "$NEWEST" ] && [ -f "$DEST/$NEWEST" ]; then
    if ssh_cmd "ack $NEWEST" > /dev/null; then
        log "acked $NEWEST"
    else
        log "ack failed: $NEWEST"
        FAILED=1
    fi
fi

# Retention: keep the 30 newest local archives, plus the oldest local
# archive of each YYYYMM within the last 12 months (RESEARCH.md SEC-04
# "Mac side"). Names sort lexically = chronologically, so
# `sort -r | tail -n +31` finds the deletion candidates without ever
# relying on a GNU-only negative head line count.
for f in "$DEST"/*; do
    [ -f "$f" ] && printf '%s\n' "${f##*/}"
done | grep -E "$ARCHIVE_RE" | sort -r | tail -n +31 > "$WORKDIR/prune-candidates.txt" || true
if [ -s "$WORKDIR/prune-candidates.txt" ]; then
    sort "$WORKDIR/prune-candidates.txt" > "$WORKDIR/prune-candidates-asc.txt"
    CUTOFF=$(cutoff_month)
    SEEN_MONTHS=""
    while IFS= read -r name; do
        [ -z "$name" ] && continue
        month=$(printf '%s\n' "$name" | sed -n 's/^skypane-state-\([0-9]\{6\}\).*/\1/p')
        case " $SEEN_MONTHS " in
            *" $month "*)
                rm -f "$DEST/$name"
                ;;
            *)
                SEEN_MONTHS="$SEEN_MONTHS $month"
                if [ "$month" -lt "$CUTOFF" ]; then
                    rm -f "$DEST/$name"
                fi
                ;;
        esac
    done < "$WORKDIR/prune-candidates-asc.txt"
fi

if [ "$FAILED" -ne 0 ]; then
    log "completed with failures"
    exit 1
fi
log "completed"
exit 0
