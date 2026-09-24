#!/usr/bin/env python3
"""SkyPane nightly off-box-ready state snapshot (SEC-04, D-03).

Runs on the VPS as user `skypane`, from `skypane-backup.service`
(triggered nightly at 03:15 UTC by `skypane-backup.timer` - see
`deploy/skypane-backup.service` for the exact CLI contract this module
implements). Writes one dated, checksummed `tar.gz` archive of
`/opt/skypane/state` into a local archive directory per run. This job
never leaves the VPS: the off-box copy is a separate pull, over SSH,
driven by the developer's Mac through the narrow forced-command gate in
`deploy/backup/backup_gate.py` - nothing is ever pushed from here.

INCLUDE_FILES/INCLUDE_DIRS below are an ALLOW-list, not a deny-list, on
purpose: a file `state/` grows in some later phase and is never added
here is meant to be *noticed* (a drift line printed to stdout, captured
by journald), not silently carried into every nightly archive from then
on, or - worse - silently left out of one the developer assumes is
complete. `history.db` is handled outside both lists entirely: it is a
live WAL database, never copied byte-for-byte (see `snapshot_db()`
below), so it can never be "just another include file".
"""
import argparse
import fnmatch
import hashlib
import os
import re
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime, timezone

DEFAULT_STATE_DIR = "/opt/skypane/state"
DEFAULT_ARCHIVE_DIR = "/var/lib/skypane-backup/archives"
DEFAULT_KEEP = 14

# Allow-list (RESEARCH.md SEC-04 "State inventory" + D-24: gallery/ IS
# backed up). devices.json is Phase 34 FW-08's per-device enrolment
# registry - included when present; losing it would make byos refuse
# every re-enrolment.
INCLUDE_FILES = (
    "byos_state.json",
    "devices.json",
    "device_config.json",
    "calendar_rules.json",
    "calendar_url.secret",
    "colour_rules.json",
    "manual_resolutions.json",
    "poll_state.json",
    "battery_state.json",
)
INCLUDE_DIRS = (
    "illustration_overrides",
    "gallery",
)

# Known-regenerable/transient entries this job deliberately never
# archives and never reports as drift (RESEARCH.md "Known excluded").
# Matched with fnmatch against each top-level state/ entry name.
KNOWN_EXCLUDED = (
    "panel.bin",
    "theme_previews",
    "caddy-access.log*",
    "history.db",
    "history.db-wal",
    "history.db-shm",
    "*.lock",
    "*.tmp",
    "img",
)

ARCHIVE_RE = re.compile(r"^skypane-state-(\d{8}T\d{6}Z)\.tar\.gz$")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--state-dir",
        default=DEFAULT_STATE_DIR,
        help="Directory to snapshot (default: %s)." % DEFAULT_STATE_DIR,
    )
    parser.add_argument(
        "--archive-dir",
        default=DEFAULT_ARCHIVE_DIR,
        help="Directory to write dated archives into (default: %s)." % DEFAULT_ARCHIVE_DIR,
    )
    parser.add_argument(
        "--keep",
        type=int,
        default=DEFAULT_KEEP,
        help="Number of newest archives to retain locally (default: %d)." % DEFAULT_KEEP,
    )
    return parser


def _is_known_excluded(name):
    return any(fnmatch.fnmatch(name, pattern) for pattern in KNOWN_EXCLUDED)


def _no_symlinks(tarinfo):
    # A symlink could point anywhere, including outside state/ entirely -
    # a restore (`tar -xzf ... -C state`) must only ever recreate regular
    # files/directories under the target directory, never follow a link
    # captured from the source host.
    if tarinfo.issym() or tarinfo.islnk():
        return None
    return tarinfo


def snapshot_db(src_path, dst_path):
    """Copy `history.db` consistently while a writer may hold it open
    under WAL (T-37-18): sqlite3's own backup API copies pages under a
    shared lock rather than a byte-for-byte file copy, so a concurrent
    writer never produces a torn snapshot [CITED: Python sqlite3 docs].
    `PRAGMA integrity_check` runs on the COPY, never the live database
    (that would contend with the same writer) - it is the only proof the
    snapshot itself is sound, not just present.
    """
    src = sqlite3.connect(src_path, timeout=30)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
        row = dst.execute("PRAGMA integrity_check").fetchone()
        if row is None or row[0] != "ok":
            raise RuntimeError("history.db backup failed integrity_check")
    finally:
        dst.close()
        src.close()


def _write_checksum(archive_path):
    digest = hashlib.sha256()
    with open(archive_path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    name = os.path.basename(archive_path)
    sha_path = archive_path + ".sha256"
    partial = os.path.join(os.path.dirname(archive_path), ".partial-" + name + ".sha256")
    with open(partial, "w") as fh:
        fh.write("%s  %s\n" % (digest.hexdigest(), name))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(partial, sha_path)


def _prune(archive_dir, keep):
    names = sorted(entry for entry in os.listdir(archive_dir) if ARCHIVE_RE.match(entry))
    stale = names[:-keep] if len(names) > keep else []
    for name in stale:
        for path in (os.path.join(archive_dir, name), os.path.join(archive_dir, name + ".sha256")):
            try:
                os.remove(path)
            except OSError:
                pass
    kept = set(names) - set(stale)
    # Second, independent pass: any .sha256 whose archive is gone (pruned
    # just above, or already missing before this run started) and any
    # leftover .partial-* from a previous, interrupted run.
    for entry in list(os.listdir(archive_dir)):
        if entry.endswith(".sha256"):
            base = entry[: -len(".sha256")]
            if ARCHIVE_RE.match(base) and base not in kept:
                try:
                    os.remove(os.path.join(archive_dir, entry))
                except OSError:
                    pass
        elif entry.startswith(".partial-"):
            try:
                os.remove(os.path.join(archive_dir, entry))
            except OSError:
                pass


def backup(state_dir, archive_dir, keep):
    """Build one dated, checksummed archive of `state_dir` into
    `archive_dir`, then prune to the newest `keep`. Returns 0/1 - never
    raises past here (T-37-18): a state directory that does not exist,
    or a `history.db` that fails `integrity_check`, is reported as one
    line and a non-zero return, not a traceback (the systemd timer's own
    journal is the only audience for that line).
    """
    if not os.path.isdir(state_dir):
        print("skypane_backup: state directory not found: %s" % state_dir)
        return 1
    os.makedirs(archive_dir, exist_ok=True)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    name = "skypane-state-%s.tar.gz" % timestamp
    final_path = os.path.join(archive_dir, name)
    partial_path = os.path.join(archive_dir, ".partial-" + name)

    history_db_src = os.path.join(state_dir, "history.db")
    with tempfile.TemporaryDirectory(dir=archive_dir, prefix=".tmp-") as tmp_dir:
        try:
            with tarfile.open(partial_path, "w:gz") as tar:
                if os.path.exists(history_db_src):
                    snap_path = os.path.join(tmp_dir, "history.db")
                    snapshot_db(history_db_src, snap_path)
                    tar.add(snap_path, arcname="history.db", filter=_no_symlinks)

                for filename in INCLUDE_FILES:
                    path = os.path.join(state_dir, filename)
                    if os.path.exists(path):
                        tar.add(path, arcname=filename, filter=_no_symlinks)
                for dirname in INCLUDE_DIRS:
                    path = os.path.join(state_dir, dirname)
                    if os.path.isdir(path):
                        tar.add(path, arcname=dirname, filter=_no_symlinks)
        except Exception as exc:
            try:
                os.remove(partial_path)
            except OSError:
                pass
            print("skypane_backup: snapshot failed: %s: %s" % (type(exc).__name__, exc))
            return 1

        # Drift: a top-level state/ entry that is neither included nor a
        # known-regenerable file is worth a line in the journal, even
        # though this run silently leaves it out either way.
        known = set(INCLUDE_FILES) | set(INCLUDE_DIRS) | {"history.db"}
        for entry in sorted(os.listdir(state_dir)):
            if entry in known or _is_known_excluded(entry):
                continue
            print("skypane_backup: not in include list: %s" % entry)

    with open(partial_path, "rb") as fh:
        os.fsync(fh.fileno())
    os.replace(partial_path, final_path)
    _write_checksum(final_path)
    _prune(archive_dir, keep)
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return backup(args.state_dir, args.archive_dir, args.keep)
    except Exception as exc:
        print("skypane_backup: %s: %s" % (type(exc).__name__, exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
