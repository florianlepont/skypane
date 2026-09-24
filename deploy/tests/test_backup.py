"""deploy/tests/test_backup.py -- the nightly snapshot job (SEC-04, D-03,
D-24). See RESEARCH.md SEC-04 "State inventory"/"Snapshot job" and the
PLAN's <interfaces> for the archive-name regex and CLI contract this test
enforces. Loads deploy/backup/skypane_backup.py directly by path
(importlib) rather than as a package import, matching the plan's own
instruction and the fact that deploy/backup/ is not itself a package.
"""
import hashlib
import importlib.util
import os
import stat
import tarfile
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server import history_db

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_MODULE_PATH = _REPO_ROOT / "deploy" / "backup" / "skypane_backup.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("skypane_backup", _MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


skypane_backup = _load_module()


def _members(archive_path):
    with tarfile.open(archive_path, "r:gz") as tar:
        return set(tar.getnames())


def _archive_names(archive_dir):
    return sorted(p.name for p in Path(archive_dir).iterdir() if skypane_backup.ARCHIVE_RE.match(p.name))


def _seed_minimal_state(state_dir):
    """A state/ directory with just enough for a run to succeed - no
    history.db at all (the "fresh box" case most other tests build on
    top of by adding one).
    """
    os.makedirs(state_dir, exist_ok=True)


class TestConsistentSnapshot:
    def test_concurrent_writer_produces_consistent_archive(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)

        conn = history_db.connect(str(state_dir))
        start_rows = 20
        for i in range(start_rows):
            history_db.record_device_health(conn, "2026-09-24T00:00:%02dZ" % i, battery_mv=3700 + i)

        conn.close()

        stop = threading.Event()
        written = []

        def writer():
            # A second, independent connection - sqlite3 connections are
            # not shareable across threads (check_same_thread=True), and
            # this is meant to simulate a genuinely separate writer
            # process (poll/companion), not the same connection object.
            writer_conn = history_db.connect(str(state_dir))
            n = start_rows
            while not stop.is_set():
                writer_conn.execute(
                    "INSERT INTO device_health (ts, battery_mv) VALUES (?, ?)",
                    ("2026-09-24T00:01:%02d.%06dZ" % (n % 60, n), 3700),
                )
                writer_conn.commit()
                written.append(n)
                n += 1
                time.sleep(0.001)
            writer_conn.close()

        thread = threading.Thread(target=writer)
        thread.start()
        time.sleep(0.02)  # give the writer a head start before the snapshot
        try:
            rc = skypane_backup.main(
                ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir), "--keep", "14"]
            )
        finally:
            stop.set()
            thread.join()

        assert written  # the writer really did run concurrently with backup()
        assert rc == 0
        names = _archive_names(archive_dir)
        assert len(names) == 1
        archive_path = archive_dir / names[0]

        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(tmp_path / "restored", filter="data")
        restored_db = tmp_path / "restored" / "history.db"
        restored_conn = history_db.connect(str(tmp_path / "restored"))
        row = restored_conn.execute("PRAGMA integrity_check").fetchone()
        assert row[0] == "ok"
        count = restored_conn.execute("SELECT COUNT(*) FROM device_health").fetchone()[0]
        restored_conn.close()
        assert count >= start_rows
        assert restored_db.exists()


class TestArchiveMembers:
    def test_include_list_present_known_excluded_absent(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)

        conn = history_db.connect(str(state_dir))
        history_db.record_device_health(conn, "2026-09-24T00:00:00Z", battery_mv=3700)
        conn.close()

        for filename in skypane_backup.INCLUDE_FILES:
            (state_dir / filename).write_text("x")

        gallery = state_dir / "gallery"
        gallery.mkdir()
        (gallery / "0001.png").write_bytes(b"PNG")
        overrides = state_dir / "illustration_overrides"
        overrides.mkdir()
        (overrides / "0001.png").write_bytes(b"PNG")

        # Known-excluded, must never be archived.
        (state_dir / "panel.bin").write_bytes(b"bin")
        (state_dir / "theme_previews").mkdir()
        (state_dir / "theme_previews" / "x.png").write_bytes(b"PNG")
        (state_dir / "caddy-access.log").write_text("log")
        (state_dir / "history.db-wal").write_bytes(b"wal")
        (state_dir / "history.db-shm").write_bytes(b"shm")
        (state_dir / "something.lock").write_text("lock")
        (state_dir / "something.tmp").write_text("tmp")

        rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
        assert rc == 0

        archive_path = archive_dir / _archive_names(archive_dir)[0]
        members = _members(archive_path)

        assert "history.db" in members
        for filename in skypane_backup.INCLUDE_FILES:
            assert filename in members
        assert "gallery/0001.png" in members
        assert "illustration_overrides/0001.png" in members

        for excluded in (
            "panel.bin",
            "theme_previews",
            "theme_previews/x.png",
            "caddy-access.log",
            "history.db-wal",
            "history.db-shm",
            "something.lock",
            "something.tmp",
        ):
            assert excluded not in members

    def test_unlisted_file_is_drift_known_excluded_is_silent(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        (state_dir / "surprise.json").write_text("{}")
        (state_dir / "panel.bin").write_bytes(b"bin")

        rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
        assert rc == 0

        out = capsys.readouterr().out
        assert "surprise.json" in out
        assert "skypane_backup: not in include list: surprise.json" in out
        assert "panel.bin" not in out

        archive_path = archive_dir / _archive_names(archive_dir)[0]
        members = _members(archive_path)
        assert "surprise.json" not in members

    def test_missing_optional_include_files_skipped_without_error(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)

        rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
        assert rc == 0

        archive_path = archive_dir / _archive_names(archive_dir)[0]
        members = _members(archive_path)
        assert members == set()


class TestArchiveNamingAndChecksum:
    def test_name_matches_regex_and_checksum_verifies_no_partials_left(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        (state_dir / "poll_state.json").write_text("{}")

        rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
        assert rc == 0

        names = _archive_names(archive_dir)
        assert len(names) == 1
        name = names[0]
        assert skypane_backup.ARCHIVE_RE.match(name)

        archive_path = archive_dir / name
        sha_path = archive_dir / (name + ".sha256")
        assert sha_path.exists()

        digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        content = sha_path.read_text()
        assert content == "%s  %s\n" % (digest, name)

        for entry in os.listdir(archive_dir):
            assert ".partial-" not in entry

    def test_umask_0027_produces_mode_0640(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)

        old_umask = os.umask(0o027)
        try:
            rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
        finally:
            os.umask(old_umask)
        assert rc == 0

        name = _archive_names(archive_dir)[0]
        archive_mode = stat.S_IMODE((archive_dir / name).stat().st_mode)
        sha_mode = stat.S_IMODE((archive_dir / (name + ".sha256")).stat().st_mode)
        assert archive_mode == 0o640
        assert sha_mode == 0o640


class TestRetention:
    def test_keep_14_of_16_prunes_oldest_and_orphan_sha256(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        archive_dir.mkdir()

        base = datetime(2026, 9, 1, tzinfo=timezone.utc)
        existing_names = []
        for i in range(16):
            ts = (base + timedelta(days=i)).strftime("%Y%m%dT%H%M%SZ")
            name = "skypane-state-%s.tar.gz" % ts
            (archive_dir / name).write_bytes(b"fake")
            (archive_dir / (name + ".sha256")).write_text("deadbeef  %s\n" % name)
            existing_names.append(name)

        # An orphan .sha256 with no matching archive at all.
        (archive_dir / "skypane-state-20260801T000000Z.tar.gz.sha256").write_text("orphan\n")

        rc = skypane_backup.main(
            ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir), "--keep", "14"]
        )
        assert rc == 0

        remaining = _archive_names(archive_dir)
        assert len(remaining) == 14
        # The 3 oldest of the 16 pre-existing archives were pruned (16 + 1
        # new - 14 kept = 3), leaving the newest 13 pre-existing plus the
        # new one.
        assert remaining == sorted(remaining)
        assert set(existing_names[3:]) <= set(remaining)
        for name in existing_names[:3]:
            assert not (archive_dir / name).exists()
            assert not (archive_dir / (name + ".sha256")).exists()
        assert not (archive_dir / "skypane-state-20260801T000000Z.tar.gz.sha256").exists()


class TestErrorHandling:
    def test_missing_state_dir_returns_nonzero_one_line_no_traceback(self, tmp_path, capsys):
        missing = str(tmp_path / "does-not-exist")
        rc = skypane_backup.main(["--state-dir", missing])
        assert rc != 0
        out = capsys.readouterr().out
        lines = [line for line in out.splitlines() if line.strip()]
        assert len(lines) == 1
        assert missing in lines[0]
        assert "Traceback" not in out


class TestFailureAndCleanupPaths:
    def test_symlink_inside_included_dir_is_never_archived(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        included = state_dir / skypane_backup.INCLUDE_DIRS[0]
        included.mkdir()
        (included / "real.txt").write_text("kept")
        os.symlink("/etc/hostname", included / "escape")
        assert skypane_backup.backup(str(state_dir), str(archive_dir), keep=3) == 0
        (name,) = _archive_names(archive_dir)
        members = _members(archive_dir / name)
        assert "%s/real.txt" % skypane_backup.INCLUDE_DIRS[0] in members
        assert "%s/escape" % skypane_backup.INCLUDE_DIRS[0] not in members

    def test_unreadable_history_db_fails_cleanly_without_partial(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        (state_dir / "history.db").write_bytes(b"this is not a sqlite database" * 100)
        assert skypane_backup.backup(str(state_dir), str(archive_dir), keep=3) == 1
        assert "snapshot failed" in capsys.readouterr().out
        assert os.listdir(archive_dir) == []

    def test_prune_removes_orphan_checksums_and_leftover_partials(self, tmp_path):
        archive_dir = tmp_path / "archives"
        archive_dir.mkdir()
        orphan = "skypane-state-20260101T000000Z.tar.gz.sha256"
        leftover = ".partial-skypane-state-20260102T000000Z.tar.gz"
        (archive_dir / orphan).write_text("x")
        (archive_dir / leftover).write_text("x")
        (archive_dir / "unrelated.txt").write_text("x")
        skypane_backup._prune(str(archive_dir), keep=3)
        assert sorted(os.listdir(archive_dir)) == ["unrelated.txt"]

    def test_main_reports_unexpected_errors_as_one_line(self, tmp_path, monkeypatch, capsys):
        def boom(*_args):
            raise OSError("disk gone")
        monkeypatch.setattr(skypane_backup, "backup", boom)
        rc = skypane_backup.main([
            "--state-dir", str(tmp_path / "state"),
            "--archive-dir", str(tmp_path / "archives"),
        ])
        assert rc == 1
        assert capsys.readouterr().out.strip() == "skypane_backup: OSError: disk gone"
