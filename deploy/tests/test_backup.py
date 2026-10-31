"""deploy/tests/test_backup.py -- the nightly snapshot job. Exercises the
archive-name regex and CLI contract enforced by
deploy/backup/skypane_backup.py, loaded directly by path (importlib)
rather than as a package import, since deploy/backup/ is not itself a
package.
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

from server import fleet_db, history_db

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

    def test_firmware_directory_archived_no_drift_lock_excluded(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)

        firmware = state_dir / "firmware"
        firmware.mkdir()
        (firmware / "registry.json").write_text("{}")
        (firmware / ("a" * 64 + ".bin")).write_bytes(b"image-bytes")
        (firmware / "device_report.json").write_text("{}")
        (firmware / "registry.lock").write_text("")

        rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
        assert rc == 0

        out = capsys.readouterr().out
        assert "not in include list: firmware" not in out

        archive_path = archive_dir / _archive_names(archive_dir)[0]
        members = _members(archive_path)
        assert "firmware/registry.json" in members
        assert "firmware/%s.bin" % ("a" * 64) in members
        assert "firmware/device_report.json" in members
        assert "firmware/registry.lock" not in members

    def test_unlisted_file_is_drift_known_excluded_is_silent(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        (state_dir / "surprise.json").write_text("{}")
        (state_dir / "panel.bin").write_bytes(b"bin")
        rotated = "caddy-access-2026-09-12T04-16-18.345-size.log.gz"
        (state_dir / rotated).write_bytes(b"gz")

        rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
        assert rc == 0

        out = capsys.readouterr().out
        assert "surprise.json" in out
        assert "skypane_backup: not in include list: surprise.json" in out
        assert "panel.bin" not in out
        assert rotated not in out

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


_SECRET = "ab" * 32
_MAC = "aa:bb:cc:dd:ee:01"


_PENDING_MAC = "aa:bb:cc:dd:ee:02"
_RETIRED_MAC = "aa:bb:cc:dd:ee:03"


def _seed_fleet_db(state_dir):
    conn = fleet_db.connect(str(state_dir))
    owner = fleet_db.add_user(conn, "Owner@Example.org", "admin")
    loc = fleet_db.add_location(
        conn, "Orly east", 48.72, 2.38, "Europe/Paris", owner_user_id=owner
    )
    fleet_db.add_device(
        conn, _MAC, _SECRET, "xiao-ee02-13in3-spectra6", owner, location_id=loc, name="Salon"
    )
    fleet_db.register_pending(conn, _PENDING_MAC, _SECRET, "xiao-ee02-13in3-spectra6", owner)
    retired = fleet_db.register_pending(
        conn, _RETIRED_MAC, _SECRET, "xiao-ee02-13in3-spectra6", owner
    )
    conn.execute("UPDATE pending_devices SET status = 'retired' WHERE id = ?", (retired,))
    fleet_db.audit_append(
        conn, fleet_db.AuditActor(owner, "owner@example.org", None),
        "frame.register", "pending", retired, "ok", {"mac": _RETIRED_MAC}, now=1000,
    )
    fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
    conn.close()


_SCHEMA3_TABLES = ("pending_devices", "audit_log", "locations")


def _table_rows(conn, table):
    return [tuple(r) for r in conn.execute("SELECT * FROM %s ORDER BY 1" % table)]


class TestFleetDbBackup:
    def test_restore_into_empty_directory_matches_seeded_rows(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        _seed_fleet_db(state_dir)

        assert skypane_backup.main(
            ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)]
        ) == 0
        archive = archive_dir / _archive_names(archive_dir)[0]
        assert "fleet.db" in _members(archive)

        restored = tmp_path / "restored"
        restored.mkdir()
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(restored, filter="data")
        conn = fleet_db.connect_readonly(str(restored))
        try:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert fleet_db.schema_version(conn) == fleet_db.SCHEMA_VERSION
            (device,) = fleet_db.list_devices(conn)
            assert device["mac"] == _MAC
            assert device["owner_email"] == "owner@example.org"
            assert device["hardware_type"] == "xiao-ee02-13in3-spectra6"
            assert device["location_name"] == "Orly east"
            assert fleet_db.meta_get(conn, fleet_db.META_MIGRATED) == "1"
        finally:
            conn.close()

    def test_restore_carries_pending_audit_and_location_owner(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        _seed_fleet_db(state_dir)
        assert skypane_backup.main(
            ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)]
        ) == 0
        archive = archive_dir / _archive_names(archive_dir)[0]
        restored = tmp_path / "restored"
        restored.mkdir()
        with tarfile.open(archive, "r:gz") as tar:
            tar.extractall(restored, filter="data")

        source = fleet_db.connect_readonly(str(state_dir))
        copy = fleet_db.connect_readonly(str(restored))
        try:
            assert fleet_db.schema_version(copy) == fleet_db.SCHEMA_VERSION
            for table in _SCHEMA3_TABLES:
                assert _table_rows(copy, table) == _table_rows(source, table)
            assert len(_table_rows(copy, "pending_devices")) == 2
            assert len(_table_rows(copy, "audit_log")) == 1
            assert copy.execute(
                "SELECT owner_user_id FROM locations"
            ).fetchone()[0] is not None
            assert [s for s in fleet_db.dump_logical(copy) if s.startswith("CREATE TRIGGER")] == [
                s for s in fleet_db.dump_logical(source) if s.startswith("CREATE TRIGGER")
            ]
            triggers = {
                r[0] for r in copy.execute("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            }
            assert {"audit_log_no_update", "audit_log_no_delete"} <= triggers
        finally:
            source.close()
            copy.close()

    def test_pairing_directory_is_excluded_without_drift(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        _seed_fleet_db(state_dir)
        pairing = state_dir / "pairing" / "p_0123abcd" / "img"
        pairing.mkdir(parents=True)
        (state_dir / "pairing" / "p_0123abcd" / "panel.bin").write_bytes(b"pixels")
        (pairing / ("c" * 64 + ".bin")).write_bytes(b"pixels")

        assert skypane_backup.main(
            ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)]
        ) == 0
        assert "not in include list" not in capsys.readouterr().out
        members = _members(archive_dir / _archive_names(archive_dir)[0])
        assert not any(m == "pairing" or m.startswith("pairing/") for m in members)

    def test_wal_shm_and_status_file_never_archived_nor_drift(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        _seed_fleet_db(state_dir)
        (state_dir / "fleet.db-wal").write_bytes(b"wal")
        (state_dir / "fleet.db-shm").write_bytes(b"shm")
        (state_dir / "fleet_status.json").write_text("{}")

        assert skypane_backup.main(
            ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)]
        ) == 0
        members = _members(archive_dir / _archive_names(archive_dir)[0])
        for excluded in ("fleet.db-wal", "fleet.db-shm", "fleet_status.json"):
            assert excluded not in members
        assert "not in include list" not in capsys.readouterr().out

    def test_corrupt_fleet_db_fails_loudly_without_partial(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        (state_dir / "fleet.db").write_bytes(b"this is not a sqlite database" * 100)

        assert skypane_backup.backup(str(state_dir), str(archive_dir), keep=3) == 1
        out = capsys.readouterr().out
        assert "snapshot failed" in out
        assert "fleet.db" in out
        assert os.listdir(archive_dir) == []

    def test_concurrent_fleet_writer_still_yields_consistent_snapshot(self, tmp_path):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        _seed_fleet_db(state_dir)

        stop = threading.Event()
        written = []

        def writer():
            conn = fleet_db.connect(str(state_dir))
            n = 0
            while not stop.is_set():
                fleet_db.add_user(conn, "u%d@example.org" % n, "user")
                written.append(n)
                n += 1
                time.sleep(0.001)
            conn.close()

        thread = threading.Thread(target=writer)
        thread.start()
        time.sleep(0.02)
        try:
            rc = skypane_backup.main(
                ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)]
            )
        finally:
            stop.set()
            thread.join()
        assert written
        assert rc == 0
        restored = tmp_path / "restored"
        restored.mkdir()
        with tarfile.open(archive_dir / _archive_names(archive_dir)[0], "r:gz") as tar:
            tar.extractall(restored, filter="data")
        conn = fleet_db.connect_readonly(str(restored))
        try:
            assert conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        finally:
            conn.close()

    def test_state_without_fleet_db_backs_up_silently(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        archive_dir = tmp_path / "archives"
        _seed_minimal_state(state_dir)
        (state_dir / "poll_state.json").write_text("{}")

        assert skypane_backup.main(
            ["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)]
        ) == 0
        assert "fleet" not in capsys.readouterr().out
        assert "fleet.db" not in _members(archive_dir / _archive_names(archive_dir)[0])


_DEV = "d_1a2b3c4d"
_DEV2 = "d_deadbeef"


def _seed_device(state_dir, dev_id=_DEV, with_history=True):
    ddir = Path(state_dir) / "devices" / dev_id
    (ddir / "gallery").mkdir(parents=True)
    (ddir / "img").mkdir()
    for name in ("device_config.json", "poll_state.json", "battery_state.json"):
        (ddir / name).write_text('{"id": "%s"}' % dev_id)
    (ddir / "gallery" / "x.png").write_bytes(b"png")
    (ddir / "panel.bin").write_bytes(b"panel")
    (ddir / "img" / "h.bin").write_bytes(b"img")
    (ddir / "poll.lock").write_text("")
    if with_history:
        conn = history_db.connect(str(ddir))
        history_db.record_device_health(conn, "2026-09-24T00:00:00Z", battery_mv=3700)
        conn.close()
    return ddir


def _run_backup(tmp_path):
    state_dir = tmp_path / "state"
    archive_dir = tmp_path / "archives"
    rc = skypane_backup.main(["--state-dir", str(state_dir), "--archive-dir", str(archive_dir)])
    return rc, archive_dir


class TestDeviceDirectories:
    def test_devices_include_list_and_exclusions(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        _seed_minimal_state(state_dir)
        ddir = _seed_device(state_dir)
        for name in ("calendar_rules.json", "calendar_url.secret", "colour_rules.json", "manual_resolutions.json"):
            (ddir / name).write_text("x")
        (ddir / "illustration_overrides").mkdir()
        (ddir / "illustration_overrides" / "a.png").write_bytes(b"o")
        (ddir / "history.db-wal").write_bytes(b"wal")
        (ddir / "history.db-shm").write_bytes(b"shm")
        (ddir / "state.tmp").write_text("t")

        rc, archive_dir = _run_backup(tmp_path)
        assert rc == 0
        members = _members(archive_dir / _archive_names(archive_dir)[0])
        base = "devices/" + _DEV + "/"
        for kept in (
            "device_config.json", "poll_state.json", "battery_state.json", "history.db",
            "gallery/x.png", "calendar_rules.json", "calendar_url.secret",
            "colour_rules.json", "manual_resolutions.json", "illustration_overrides/a.png",
        ):
            assert base + kept in members
        for dropped in ("panel.bin", "img", "img/h.bin", "poll.lock", "history.db-wal", "history.db-shm", "state.tmp"):
            assert base + dropped not in members
        assert "not in include list" not in capsys.readouterr().out

    def test_bad_directory_name_is_drift_not_archived(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        _seed_minimal_state(state_dir)
        _seed_device(state_dir)
        bad = state_dir / "devices" / "D_1A2B3C4D"
        bad.mkdir()
        (bad / "device_config.json").write_text("{}")
        (state_dir / "devices" / "stray.txt").write_text("x")

        rc, archive_dir = _run_backup(tmp_path)
        assert rc == 0
        members = _members(archive_dir / _archive_names(archive_dir)[0])
        assert not any("D_1A2B3C4D" in m or "stray.txt" in m for m in members)
        out = capsys.readouterr().out
        assert "not in include list: devices/D_1A2B3C4D" in out

    def test_unexpected_file_in_device_directory_is_drift(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        _seed_minimal_state(state_dir)
        ddir = _seed_device(state_dir)
        (ddir / "surprise.dat").write_text("x")

        rc, archive_dir = _run_backup(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "not in include list: devices/%s/surprise.dat" % _DEV in out
        assert out.count("not in include list") == 1
        assert "devices/%s/surprise.dat" % _DEV not in _members(archive_dir / _archive_names(archive_dir)[0])

    def test_symlinks_never_archived(self, tmp_path):
        state_dir = tmp_path / "state"
        _seed_minimal_state(state_dir)
        ddir = _seed_device(state_dir)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "device_config.json").write_text("secret")
        (state_dir / "devices" / _DEV2).symlink_to(outside, target_is_directory=True)
        (ddir / "colour_rules.json").symlink_to(outside / "device_config.json")
        (ddir / "gallery" / "link.png").symlink_to(outside / "device_config.json")

        rc, archive_dir = _run_backup(tmp_path)
        assert rc == 0
        members = _members(archive_dir / _archive_names(archive_dir)[0])
        assert not any(_DEV2 in m for m in members)
        assert "devices/%s/colour_rules.json" % _DEV not in members
        assert "devices/%s/gallery/link.png" % _DEV not in members
        assert "devices/%s/gallery/x.png" % _DEV in members

    def test_two_devices_restore_round_trip(self, tmp_path):
        state_dir = tmp_path / "state"
        _seed_minimal_state(state_dir)
        _seed_device(state_dir, _DEV)
        d2 = _seed_device(state_dir, _DEV2, with_history=False)
        conn = history_db.connect(str(d2))
        for i in range(3):
            history_db.record_device_health(conn, "2026-09-24T00:00:%02dZ" % i, battery_mv=3600 + i)
        conn.close()

        rc, archive_dir = _run_backup(tmp_path)
        assert rc == 0
        restored = tmp_path / "restored"
        restored.mkdir()
        with tarfile.open(archive_dir / _archive_names(archive_dir)[0], "r:gz") as tar:
            tar.extractall(restored, filter="data")
        for dev_id, rows in ((_DEV, 1), (_DEV2, 3)):
            rdir = restored / "devices" / dev_id
            assert (rdir / "device_config.json").read_text() == '{"id": "%s"}' % dev_id
            rconn = history_db.connect(str(rdir))
            assert rconn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert rconn.execute("SELECT COUNT(*) FROM device_health").fetchone()[0] == rows
            rconn.close()

    def test_concurrent_device_writer_yields_consistent_snapshot(self, tmp_path):
        state_dir = tmp_path / "state"
        _seed_minimal_state(state_dir)
        ddir = _seed_device(state_dir)

        stop = threading.Event()
        written = []

        def writer():
            conn = history_db.connect(str(ddir))
            n = 0
            while not stop.is_set():
                conn.execute(
                    "INSERT INTO device_health (ts, battery_mv) VALUES (?, ?)",
                    ("2026-09-24T01:00:%02d.%06dZ" % (n % 60, n), 3700),
                )
                conn.commit()
                written.append(n)
                n += 1
                time.sleep(0.001)
            conn.close()

        thread = threading.Thread(target=writer)
        thread.start()
        time.sleep(0.02)
        try:
            rc, archive_dir = _run_backup(tmp_path)
        finally:
            stop.set()
            thread.join()
        assert written
        assert rc == 0
        restored = tmp_path / "restored"
        restored.mkdir()
        with tarfile.open(archive_dir / _archive_names(archive_dir)[0], "r:gz") as tar:
            tar.extractall(restored, filter="data")
        rconn = history_db.connect(str(restored / "devices" / _DEV))
        assert rconn.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        rconn.close()

    def test_corrupt_device_history_fails_loudly_without_partial(self, tmp_path, capsys):
        state_dir = tmp_path / "state"
        _seed_minimal_state(state_dir)
        ddir = _seed_device(state_dir, with_history=False)
        (ddir / "history.db").write_bytes(b"this is not a sqlite database" * 100)

        assert skypane_backup.backup(str(state_dir), str(tmp_path / "archives"), keep=3) == 1
        out = capsys.readouterr().out
        assert "snapshot failed" in out
        assert "history.db" in out
        assert os.listdir(tmp_path / "archives") == []
