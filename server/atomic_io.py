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

`exclusive_lock` gives one cross-process, cross-thread lock over
`fcntl.flock`, generalising the pattern already proven by
`calendar_rules._calendar_registry_lock`. Lock order used across this
codebase: an in-process `threading.Lock` first (each subsystem keeps its
own fast path for same-process contention, since `flock` alone is a
fragile substitute for one), then `poll.lock`, then `calendar_rules.lock`.
`device_config.lock` is never taken while another of these file locks is
held, so the poll cycle and the companion cannot deadlock on each other.
This order is documented here for callers of `exclusive_lock` to respect;
this module does not enforce it. Note also that a `flock` lock belongs to
the *open file description*, not the path or the process: two threads in
one process that each open the lock file independently still exclude each
other on Linux (a fresh open() call makes a fresh open file description),
which is why `exclusive_lock` alone is enough to add cross-thread
exclusion on top of cross-process exclusion.
"""

import contextlib
import errno
import os
import tempfile
import time

try:
    import fcntl
except ImportError:  # pragma: no cover - not exercised on this project's targets
    fcntl = None


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


class LockBusy(TimeoutError):
    """Raised by `exclusive_lock` when the lock could not be acquired
    within `timeout_s`, or at once with `blocking=False`. A `TimeoutError`
    subclass so an existing `except TimeoutError` caller keeps working.
    """


# Poll interval for a blocking exclusive_lock wait, matching the interval
# already tuned in calendar_rules's own cross-process lock.
LOCK_POLL_S = 0.05


@contextlib.contextmanager
def exclusive_lock(lock_path, timeout_s, blocking=True):
    """Cross-process, cross-thread advisory lock over `fcntl.flock`.
    Creates `lock_path`'s parent directory and the lock file itself (mode
    0600) if missing. With `blocking=True` (the default) a busy lock is
    retried every `LOCK_POLL_S` until `timeout_s` has elapsed since the
    first attempt, then raises `LockBusy`; with `blocking=False` a busy
    lock raises `LockBusy` at once. Any other `OSError` from `flock`
    propagates. The lock is always released (and the file descriptor
    closed) in a `finally`, including when the caller's block raises.

    POSIX-only (see the `fcntl` import guard above); on a platform without
    `fcntl` this yields without locking -- a documented gap, matching
    `calendar_rules`'s existing one.
    """
    if fcntl is None:
        yield
        return

    directory = os.path.dirname(lock_path) or "."
    os.makedirs(directory, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        deadline = time.monotonic() + timeout_s
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if not blocking or time.monotonic() >= deadline:
                    raise LockBusy(
                        "atomic_io: lock at %r is busy" % (lock_path,)
                    ) from exc
                time.sleep(LOCK_POLL_S)
        try:
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
