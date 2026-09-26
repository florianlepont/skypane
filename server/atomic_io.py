"""Stdlib-only atomic file writes for every state file this project owns.

Every state file (poll_state.json, panel.bin, the device registry, calendar
secrets, theme preview caches, ...) must never be observed half-written by
a concurrent reader, and a writer killed mid-write must never leave a torn
file in its place. `atomic_write` and `staged_write` give one
same-directory-mkstemp-then-`os.replace()` implementation for that:
every caller that used to do "write to a fixed `path + '.tmp'`, then
`os.replace`" (a fixed name, so two concurrent writers on the same path can
collide on the same temp file) migrates onto this module instead of
repeating the pattern with its own bugs.

Contract: the temp file is created with `tempfile.mkstemp` in the
destination's own directory (so the final `os.replace` is a same-filesystem
rename, atomic on POSIX), the requested mode is set on the temp file's
descriptor before any byte is written and the destination path itself is
never chmod'ed afterwards (a secret written with `mode=0o600` is therefore
never briefly world-readable), the file is fsynced before the rename (not
the directory), and any failure -- an unsupported `data` type, a write
error, a failed `os.replace` -- leaves the destination untouched and no
temp file behind. Callers are expected to have already created the
destination directory.
"""

import contextlib
import os
import tempfile


def _read_umask():
    """Return the process umask without racing another thread's
    umask-sensitive open() the way the `os.umask(0)` / `os.umask(old)`
    read-then-restore pair would. `/proc/self/status`'s `Umask:` line
    (Linux-only) reports it without mutating process state; fall back to
    the racy pair when `/proc` is unavailable (e.g. a non-Linux POSIX
    system).
    """
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("Umask:"):
                    return int(line.split(":", 1)[1].strip(), 8)
    except OSError:
        pass
    old = os.umask(0)
    os.umask(old)
    return old


# `open(path, "w")` on a fresh path has always produced 0o666 & ~umask;
# this is atomic_write's default so migrating a caller from `open()` to
# `atomic_write()` does not silently change its file's mode (mkstemp's own
# default of 0600 would, e.g., drop the group-read bit backups and the
# operator rely on under this project's `UMask=0027` units).
DEFAULT_FILE_MODE = 0o666 & ~_read_umask()


def _encode(data):
    if isinstance(data, str):
        return data.encode("utf-8")
    if isinstance(data, bytes):
        return data
    raise TypeError(
        "atomic_io: data must be bytes or str, got %s" % type(data).__name__
    )


@contextlib.contextmanager
def staged_write(path, data, mode=None):
    """Write `data` (bytes, or str encoded as UTF-8) to a same-directory
    temp file, fsync it, then yield a `commit()` callable that publishes it
    onto `path` with one `os.replace` call. Not calling `commit()` before
    the block exits, or raising inside it, unlinks the temp file and
    leaves `path` untouched.

    Use this directly when a caller must finish preparing a file (hash it,
    validate it, ...) before deciding whether to publish it; `atomic_write`
    is `with staged_write(...) as commit: commit()`.
    """
    payload = _encode(data)  # validated before any filesystem call

    directory = os.path.dirname(path) or "."
    prefix = "." + os.path.basename(path) + "."
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=prefix, suffix=".tmp")
    try:
        os.fchmod(fd, mode if mode is not None else DEFAULT_FILE_MODE)
        with os.fdopen(fd, "wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        # os.fdopen's own `with` already closed fd if it got that far;
        # closing it again raises, which the failed write should not mask.
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise

    committed = False

    def commit():
        nonlocal committed
        os.replace(tmp, path)
        committed = True

    try:
        yield commit
    finally:
        if not committed:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass


def atomic_write(path, data, mode=None):
    """Write `data` (bytes, or str encoded as UTF-8) to `path` so a
    concurrent reader, or a crash, only ever sees the old complete content
    or the new complete content -- never a partial write, and never a
    stray temp file left over.
    """
    with staged_write(path, data, mode=mode) as commit:
        commit()
