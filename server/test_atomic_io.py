"""Behaviour tests for server/atomic_io.py's atomic_write and staged_write.

Every assertion here is about observable behaviour (final bytes on disk,
file mode, presence/absence of a leftover temp file, exceptions raised) --
never about the module's source text.
"""

import os
import stat
import subprocess
import sys
import threading

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
