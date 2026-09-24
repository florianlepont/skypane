#!/usr/bin/python3
"""The forced-command gate for the `skypane-backup` pull key (SEC-04, D-05,
D-25, T-37-16/T-37-17).

Installed at `/usr/local/lib/skypane` (Plan 37-06) and wired into
`skypane-backup`'s `authorized_keys` as
`restrict,command="/usr/bin/python3 /usr/local/lib/skypane/backup_gate.py" ssh-ed25519 ...`
(Plan 37-07). `restrict,` already strips port-forwarding, agent
forwarding, X11 and PTY allocation from the key. `command=` means this
script's own argv (`--archive-dir`/`--pulled-dir`) is fixed by root at
install time - the ONLY thing the client (the developer's Mac,
`deploy/backup/mac/skypane-backup-pull.sh`) controls is the string SSH
puts in `SSH_ORIGINAL_COMMAND`, which this script treats as untrusted
input from the moment it is read.

Exactly three verbs are recognised, dispatched on an EXACT (verb, word
count) match - no substring/prefix matching, no shell, no `eval`:
  `list`        -> one line per archive: "<name> <size bytes> <sha256>"
  `get NAME`    -> the raw archive bytes on stdout
  `ack NAME`    -> records NAME as the freshness marker
Anything else - an empty/unset command, a bare shell, a semicolon-joined
command, an unbalanced quote, a name that does not match `ARCHIVE_RE`, or
a name whose target is not a regular file inside `--archive-dir` (a
symlink included) - exits 2 with one line on stderr and touches nothing.
This script never opens a path outside `--archive-dir`/`--pulled-dir`,
and it must stay self-contained: it runs as `/usr/bin/python3` outside
the project's venv and outside any release checkout, so it cannot import
anything from `server/`, `companion/`, or even `deploy/backup/
skypane_backup.py` - `ARCHIVE_RE` is intentionally duplicated here rather
than shared.
"""
import argparse
import os
import re
import shlex
import shutil
import stat
import sys

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
    path = _valid_archive_path(archive_dir, name)
    if path is None:
        return _fail("invalid or unknown archive: %s" % name)
    try:
        os.makedirs(pulled_dir, exist_ok=True)
        tmp = os.path.join(pulled_dir, ".last-pull.tmp")
        final = os.path.join(pulled_dir, "last-pull")
        with open(tmp, "w") as fh:
            fh.write(name + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, final)
    except OSError as exc:
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
