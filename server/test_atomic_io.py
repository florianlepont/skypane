"""Behaviour tests for server/atomic_io.py: atomic_write, staged_write and
exclusive_lock.

Every assertion here is about observable behaviour (final bytes on disk,
file mode, presence/absence of a leftover temp file, exceptions raised) --
never about the module's source text.
"""

import errno
import os
import stat
import subprocess
import sys
import threading
import time

import pytest

from server import atomic_io

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _temp_leftovers(directory):
    return [name for name in os.listdir(directory) if name.endswith(".tmp")]


def _make_payload(tag, i):
    """Deterministic 64 KiB payload distinct per (tag, i), used by both the
    threaded and the multi-process concurrency tests so the final content
    can be checked against the exact set of possible complete writes.
    """
    marker = ("%s-write-%d-" % (tag, i)).encode()
    reps = (65536 // len(marker)) + 1
    return (marker * reps)[:65536]


def test_atomic_write_str_round_trip(tmp_path):
    path = tmp_path / "state.json"
    atomic_io.atomic_write(str(path), "hello")
    assert path.read_bytes() == b"hello"


def test_atomic_write_bytes_round_trip_and_str_is_utf8(tmp_path):
    path = tmp_path / "state.bin"
    atomic_io.atomic_write(str(path), b"\x00\x01binary")
    assert path.read_bytes() == b"\x00\x01binary"

    text_path = tmp_path / "text.json"
    atomic_io.atomic_write(str(text_path), "café")
    assert text_path.read_bytes() == "café".encode("utf-8")


def test_atomic_write_default_mode_matches_umask(tmp_path):
    old = os.umask(0)
    os.umask(old)
    expected = 0o666 & ~old
    assert atomic_io.DEFAULT_FILE_MODE == expected

    path = tmp_path / "state.json"
    atomic_io.atomic_write(str(path), "x")
    assert stat.S_IMODE(path.stat().st_mode) == expected


def test_atomic_write_explicit_mode_sets_temp_before_rename(tmp_path, monkeypatch):
    path = tmp_path / "secret.json"
    seen_modes = []
    real_replace = os.replace

    def spy_replace(src, dst):
        seen_modes.append(stat.S_IMODE(os.stat(src).st_mode))
        return real_replace(src, dst)

    monkeypatch.setattr(atomic_io.os, "replace", spy_replace)
    atomic_io.atomic_write(str(path), "s3cr3t", mode=0o600)

    assert seen_modes == [0o600]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_atomic_write_os_replace_failure_leaves_original_and_no_temp(tmp_path, monkeypatch):
    path = tmp_path / "state.json"
    atomic_io.atomic_write(str(path), "original")

    def failing_replace(src, dst):
        raise OSError("disk full")

    monkeypatch.setattr(atomic_io.os, "replace", failing_replace)

    with pytest.raises(OSError):
        atomic_io.atomic_write(str(path), "new content")

    assert path.read_bytes() == b"original"
    assert _temp_leftovers(str(tmp_path)) == []


def test_atomic_write_rejects_unsupported_data_type(tmp_path):
    path = tmp_path / "state.json"
    with pytest.raises(TypeError):
        atomic_io.atomic_write(str(path), 12345)
    assert not path.exists()
    assert _temp_leftovers(str(tmp_path)) == []


def test_atomic_write_concurrent_threads_write_one_complete_payload(tmp_path):
    path = tmp_path / "shared.bin"
    payloads = {}
    errors = []

    def worker(thread_id):
        try:
            for i in range(50):
                payload = _make_payload("thread%d" % thread_id, i)
                payloads[(thread_id, i)] = payload
                atomic_io.atomic_write(str(path), payload)
        except Exception as exc:  # collected for the assertion below, not swallowed
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert errors == []
    final = path.read_bytes()
    assert final in payloads.values()
    assert _temp_leftovers(str(tmp_path)) == []


_PROCESS_WRITER_TEMPLATE = """
import sys
sys.path.insert(0, {repo_root!r})
from server import atomic_io

path, tag, count = sys.argv[1], sys.argv[2], int(sys.argv[3])


def make_payload(tag, i):
    marker = ("%s-write-%d-" % (tag, i)).encode()
    reps = (65536 // len(marker)) + 1
    return (marker * reps)[:65536]


for i in range(count):
    atomic_io.atomic_write(path, make_payload(tag, i))
"""


def test_atomic_write_concurrent_processes_write_one_complete_payload(tmp_path):
    path = tmp_path / "shared_proc.bin"
    script = tmp_path / "_writer.py"
    script.write_text(_PROCESS_WRITER_TEMPLATE.format(repo_root=REPO_ROOT))

    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT

    procs = [
        subprocess.Popen(
            [sys.executable, str(script), str(path), "proc%d" % pid, "200"],
            cwd=REPO_ROOT,
            env=env,
        )
        for pid in range(2)
    ]
    exit_codes = [p.wait() for p in procs]
    assert exit_codes == [0, 0]

    expected_payloads = {
        _make_payload("proc%d" % pid, i) for pid in range(2) for i in range(200)
    }
    final = path.read_bytes()
    assert final in expected_payloads
    assert _temp_leftovers(str(tmp_path)) == []


def test_staged_write_commit_writes_and_rollback_leaves_untouched(tmp_path):
    path = tmp_path / "staged.json"

    with atomic_io.staged_write(str(path), "committed") as commit:
        commit()
    assert path.read_bytes() == b"committed"
    assert _temp_leftovers(str(tmp_path)) == []

    # Leaving the block without commit() leaves the destination untouched.
    with atomic_io.staged_write(str(path), "not committed"):
        pass
    assert path.read_bytes() == b"committed"
    assert _temp_leftovers(str(tmp_path)) == []

    # Raising inside the block leaves the destination untouched too.
    with pytest.raises(RuntimeError):
        with atomic_io.staged_write(str(path), "also not committed"):
            raise RuntimeError("boom")
    assert path.read_bytes() == b"committed"
    assert _temp_leftovers(str(tmp_path)) == []


_LOCK_HOLDER_TEMPLATE = """
import sys
sys.path.insert(0, {repo_root!r})
from server import atomic_io

lock_path = sys.argv[1]
with atomic_io.exclusive_lock(lock_path, 5):
    print("locked", flush=True)
    sys.stdin.read()  # blocks until the parent closes stdin, releasing the lock
"""


def test_exclusive_lock_blocks_across_processes_and_releases(tmp_path):
    # The lock's parent directory does not exist yet: exclusive_lock must create it.
    lock_path = str(tmp_path / "sub" / "poll.lock")
    script = tmp_path / "_holder.py"
    script.write_text(_LOCK_HOLDER_TEMPLATE.format(repo_root=REPO_ROOT))

    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    child = subprocess.Popen(
        [sys.executable, str(script), lock_path],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        line = child.stdout.readline()
        assert line.strip() == "locked"

        start = time.monotonic()
        with pytest.raises(atomic_io.LockBusy):
            with atomic_io.exclusive_lock(lock_path, 0.3):
                pass
        elapsed = time.monotonic() - start
        assert 0.3 <= elapsed < 2.0

        start = time.monotonic()
        with pytest.raises(atomic_io.LockBusy):
            with atomic_io.exclusive_lock(lock_path, 5, blocking=False):
                pass
        assert time.monotonic() - start < 0.2
    finally:
        child.stdin.close()
        assert child.wait(timeout=5) == 0

    # The child released the lock on exit: the parent now acquires at once.
    with atomic_io.exclusive_lock(lock_path, 1):
        pass


def test_exclusive_lock_excludes_threads(tmp_path):
    lock_path = str(tmp_path / "thread.lock")
    ready = threading.Event()
    release = threading.Event()

    def holder():
        with atomic_io.exclusive_lock(lock_path, 5):
            ready.set()
            release.wait(timeout=5)

    t = threading.Thread(target=holder)
    t.start()
    try:
        assert ready.wait(timeout=5)
        with pytest.raises(atomic_io.LockBusy):
            with atomic_io.exclusive_lock(lock_path, 5, blocking=False):
                pass
    finally:
        release.set()
        t.join(timeout=5)


def test_lock_busy_is_timeout_error_subclass():
    assert issubclass(atomic_io.LockBusy, TimeoutError)


def test_exclusive_lock_creates_parent_dir_and_mode_0600(tmp_path):
    lock_path = tmp_path / "nested" / "dir" / "poll.lock"
    assert not lock_path.parent.exists()
    with atomic_io.exclusive_lock(str(lock_path), 1):
        pass
    assert lock_path.exists()
    assert stat.S_IMODE(lock_path.stat().st_mode) == 0o600


def test_exclusive_lock_releases_on_exception(tmp_path):
    lock_path = str(tmp_path / "err.lock")
    with pytest.raises(RuntimeError):
        with atomic_io.exclusive_lock(lock_path, 1):
            raise RuntimeError("boom")

    # The prior failure released the lock: a fresh non-blocking acquire succeeds at once.
    with atomic_io.exclusive_lock(lock_path, 1, blocking=False):
        pass


# --- Fallback / defensive-branch coverage -----------------------------------
#
# The behaviours below are not in the plan's required behaviour list, but
# each covers a branch that the tests above never reach on this platform
# (Linux, with /proc and fcntl always present): the /proc-unavailable umask
# fallback, a write failure after the temp file is open, an already-deleted
# temp file at cleanup time, the no-fcntl lock fallback, and an unrelated
# OSError propagating out of flock instead of becoming LockBusy.


def test_read_umask_falls_back_without_proc(monkeypatch):
    real_open = open

    def fake_open(path, *args, **kwargs):
        if path == "/proc/self/status":
            raise OSError("no /proc on this platform")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(atomic_io, "open", fake_open, raising=False)
    old = os.umask(0)
    os.umask(old)
    assert atomic_io._read_umask() == old


def test_staged_write_failure_during_write_leaves_no_temp(tmp_path, monkeypatch):
    path = tmp_path / "state.json"

    def failing_fsync(fd):
        raise OSError("write error injected for test")

    monkeypatch.setattr(atomic_io.os, "fsync", failing_fsync)
    with pytest.raises(OSError):
        atomic_io.atomic_write(str(path), "data")

    assert not path.exists()
    assert _temp_leftovers(str(tmp_path)) == []


def test_staged_write_cleanup_tolerates_already_deleted_temp(tmp_path):
    path = tmp_path / "state.json"

    with atomic_io.staged_write(str(path), "data"):
        # Delete the temp file out from under staged_write before it exits
        # the block without commit(): the cleanup unlink must tolerate a
        # temp file that is already gone.
        leftovers = _temp_leftovers(str(tmp_path))
        assert len(leftovers) == 1
        os.unlink(str(tmp_path / leftovers[0]))

    assert not path.exists()
    assert _temp_leftovers(str(tmp_path)) == []


def test_exclusive_lock_without_fcntl_yields_unlocked(tmp_path, monkeypatch):
    monkeypatch.setattr(atomic_io, "fcntl", None)
    lock_path = str(tmp_path / "no-fcntl.lock")
    # No lock file is created and no exception is raised: a documented gap
    # on a platform without fcntl.
    with atomic_io.exclusive_lock(lock_path, 1):
        pass
    assert not os.path.exists(lock_path)


def test_exclusive_lock_propagates_unrelated_oserror(tmp_path, monkeypatch):
    lock_path = str(tmp_path / "odd.lock")

    def failing_flock(fd, flags):
        raise OSError(errno.EINVAL, "unrelated failure")

    monkeypatch.setattr(atomic_io.fcntl, "flock", failing_flock)

    with pytest.raises(OSError) as excinfo:
        with atomic_io.exclusive_lock(lock_path, 1):
            pass
    assert not isinstance(excinfo.value, atomic_io.LockBusy)
