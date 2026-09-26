#!/usr/bin/python3
"""The forced-command gate for the `skypane-backup` pull key.

Wired into `skypane-backup`'s `authorized_keys` as `restrict,command=...
backup_gate.py`, which strips port/agent/X11/PTY forwarding and fixes
this script's own argv, so the only thing the client
(`deploy/backup/mac/skypane-backup-pull.sh`) controls is
`SSH_ORIGINAL_COMMAND`, treated as untrusted input throughout.

Exactly three verbs are recognised by exact (verb, word count) match, no
substring matching, no shell, no `eval`:
  `list`        -> one line per archive: "<name> <size bytes> <sha256>"
  `get NAME`    -> the raw archive bytes on stdout
  `ack NAME`    -> records NAME as the freshness marker
Anything else exits 2 and touches nothing. Stays self-contained (no
imports from `server/`, `companion/` or `skypane_backup.py`), so
`ARCHIVE_RE` is duplicated here.
"""
import argparse
import os
import re
import shlex
import shutil
import stat
import sys
import tempfile

DEFAULT_ARCHIVE_DIR = "/var/lib/skypane-backup/archives"
DEFAULT_PULLED_DIR = "/var/lib/skypane-backup/pulled"

ARCHIVE_RE = re.compile(r"^skypane-state-(\d{8}T\d{6}Z)\.tar\.gz$")


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive-dir", default=DEFAULT_ARCHIVE_DIR)
    parser.add_argument("--pulled-dir", default=DEFAULT_PULLED_DIR)
    return parser


def _fail(reason):
    print("backup_gate: %s" % reason, file=sys.stderr)
    return 2


def _valid_archive_path(archive_dir, name):
    """Return the archive's real path if NAME is safe to touch, else
    None. `ARCHIVE_RE.fullmatch` alone already rejects any name
    containing "/" (a path-traversal attempt can never match the
    pattern), and `os.lstat` + `stat.S_ISREG` refuses a symlink (which
    could point anywhere) without ever following it.
    """
    if not ARCHIVE_RE.fullmatch(name):
        return None
    path = os.path.join(archive_dir, name)
    try:
        st = os.lstat(path)
    except OSError:
        return None
    if not stat.S_ISREG(st.st_mode):
        return None
    return path


def _cmd_list(archive_dir):
    try:
        entries = os.listdir(archive_dir)
    except OSError as exc:
        return _fail("cannot list archive directory: %s" % exc)

    rows = []
    for name in entries:
        path = _valid_archive_path(archive_dir, name)
        if path is None:
            continue
        sha_path = path + ".sha256"
        try:
            with open(sha_path) as fh:
                sha = fh.read().split()[0]
        except (OSError, IndexError):
            # No (or empty) .sha256 - the archive is not yet fully
            # written/checksummed, so it is not offered for pull.
            continue
        rows.append((name, os.lstat(path).st_size, sha))

    rows.sort(key=lambda row: row[0])
    for name, size, sha in rows:
        print("%s %d %s" % (name, size, sha))
    return 0


def _cmd_get(archive_dir, name):
    path = _valid_archive_path(archive_dir, name)
    if path is None:
        return _fail("invalid or unknown archive: %s" % name)
    try:
        with open(path, "rb") as fh:
            shutil.copyfileobj(fh, sys.stdout.buffer, 1 << 20)
    except OSError as exc:
        return _fail("read failed: %s" % exc)
    sys.stdout.buffer.flush()
    return 0


def _cmd_ack(archive_dir, pulled_dir, name):
    """Record NAME as the freshness marker. The temp file is a unique
    `tempfile.mkstemp` name in `pulled_dir` (never the old fixed
    `.last-pull.tmp`, which two concurrent acks could otherwise collide
    on), given mode 0644 on its own descriptor before any byte is
    written, then published onto `last-pull` with one `os.replace`. Any
    `OSError` unlinks the temp file (if it still exists) and falls
    through to the existing `_fail(...)` path.
    """
    path = _valid_archive_path(archive_dir, name)
    if path is None:
        return _fail("invalid or unknown archive: %s" % name)
    tmp = None
    try:
        os.makedirs(pulled_dir, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=pulled_dir, prefix=".last-pull.", suffix=".tmp")
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w") as fh:
            fh.write(name + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        final = os.path.join(pulled_dir, "last-pull")
        os.replace(tmp, final)
    except OSError as exc:
        if tmp is not None and os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        return _fail("ack failed: %s" % exc)
    print("ok")
    return 0


def main(argv=None):
    args = build_parser().parse_args(argv)
    raw = os.environ.get("SSH_ORIGINAL_COMMAND", "")
    try:
        words = shlex.split(raw)
    except ValueError:
        return _fail("unparsable command")
    if not words:
        return _fail("no command given")

    verb = words[0]
    arity = len(words)
    if verb == "list" and arity == 1:
        return _cmd_list(args.archive_dir)
    if verb == "get" and arity == 2:
        return _cmd_get(args.archive_dir, words[1])
    if verb == "ack" and arity == 2:
        return _cmd_ack(args.archive_dir, args.pulled_dir, words[1])
    return _fail("unsupported command")


if __name__ == "__main__":
    sys.exit(main())
