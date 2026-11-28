#!/usr/bin/env python3
"""Tests for server/retire_legacy_state.py: dry run by default, move only
with --apply after a parity check against fleet.db, never delete, idempotent,
and output that names files and counts only."""
import json
import os
import stat

import pytest

import server.fleet_db as fleet_db
import server.retire_legacy_state as retire
import skypane_live_state as live

DAY = "2030-01-02"
EXTRA_MAC = "aa:bb:cc:dd:ee:77"
EXTRA_HASH = "7" * 64


@pytest.fixture
def seeded(tmp_path):
    return live.seed_live_like_state(str(tmp_path))


def _secrets(seeded):
    return [seeded.mac, seeded.token, seeded.secret_hex,
            live.secret_hash(seeded.secret_hex), EXTRA_MAC, EXTRA_HASH]


def _tree(root):
    """Content digests of every file; SQLite's own -wal/-shm bookkeeping
    files, which a read-only open of fleet.db may create, are not state."""
    return {name: stamp for name, stamp in live.snapshot_dir(root).items()
            if not name.endswith(("-wal", "-shm"))}


def _run(seeded, capsys, *flags):
    code, lines = retire.run(seeded.state_dir, "--apply" in flags, today=DAY)
    return code, "\n".join(lines)


def _write(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


def _quarantine(seeded):
    return os.path.join(seeded.state_dir, retire.QUARANTINE_DIRNAME, DAY)


def test_dry_run_changes_nothing_and_prints_no_value(seeded, capsys):
    before = _tree(seeded.state_dir)
    code, out = _run(seeded, capsys)
    assert code == 0
    assert "dry run: would move devices.json, byos_state.json" in out
    assert "legacy devices: 1, legacy tokens: 1" in out
    assert "lacks: 0" in out
    assert _tree(seeded.state_dir) == before
    for value in _secrets(seeded):
        assert value not in out


def test_main_defaults_to_the_dry_run(seeded, capsys):
    before = _tree(seeded.state_dir)
    assert retire.main(["--state-dir", seeded.state_dir]) == 0
    assert "dry run" in capsys.readouterr().out
    assert _tree(seeded.state_dir) == before


def test_apply_moves_both_files_keeping_bytes_and_mode(seeded, capsys):
    originals = {}
    for name in retire.LEGACY_FILES:
        path = os.path.join(seeded.state_dir, name)
        os.chmod(path, 0o600)
        with open(path, "rb") as fh:
            originals[name] = fh.read()
    db_before = _tree(seeded.state_dir)["fleet.db"]
    code, out = _run(seeded, capsys, "--apply")
    assert code == 0
    assert "moved devices.json, byos_state.json into retired-legacy/%s" % DAY in out
    for name, data in originals.items():
        assert not os.path.exists(os.path.join(seeded.state_dir, name))
        moved = os.path.join(_quarantine(seeded), name)
        with open(moved, "rb") as fh:
            assert fh.read() == data
        assert stat.S_IMODE(os.stat(moved).st_mode) == 0o600
    assert _tree(seeded.state_dir)["fleet.db"] == db_before
    for value in _secrets(seeded):
        assert value not in out


def test_second_apply_has_nothing_to_do(seeded, capsys):
    assert _run(seeded, capsys, "--apply")[0] == 0
    after_first = _tree(seeded.state_dir)
    code, out = _run(seeded, capsys, "--apply")
    assert code == 0
    assert out.startswith("nothing to do")
    assert _tree(seeded.state_dir) == after_first


def test_apply_without_fleet_db_is_refused_and_moves_nothing(tmp_path, capsys):
    unmigrated = live.seed_live_like_state(str(tmp_path), migrated=False)
    before = _tree(unmigrated.state_dir)
    code, out = _run(unmigrated, capsys, "--apply")
    assert code == 2
    assert "refused" in out
    assert _tree(unmigrated.state_dir) == before


def test_fleet_db_without_marker_is_refused(tmp_path, capsys):
    unmigrated = live.seed_live_like_state(str(tmp_path), migrated=False)
    fleet_db.connect(unmigrated.state_dir).close()
    before = _tree(unmigrated.state_dir)
    assert _run(unmigrated, capsys, "--apply")[0] == 2
    assert _tree(unmigrated.state_dir) == before


def test_a_legacy_device_missing_from_fleet_db_is_refused(seeded, capsys):
    registry = os.path.join(seeded.state_dir, "devices.json")
    doc = json.load(open(registry, encoding="utf-8"))
    doc["devices"][EXTRA_MAC] = {"secret_sha256": EXTRA_HASH}
    _write(registry, doc)
    before = _tree(seeded.state_dir)
    code, out = _run(seeded, capsys, "--apply")
    assert code == 2
    assert "lacks: 1" in out
    assert "refused: fleet.db does not hold every legacy device" in out
    assert _tree(seeded.state_dir) == before
    assert EXTRA_MAC not in out and EXTRA_HASH not in out
    assert _run(seeded, capsys)[0] == 2


def test_values_that_differ_do_not_block_the_move(seeded, capsys):
    conn = fleet_db.connect(seeded.state_dir)
    try:
        with fleet_db.transaction(conn):
            fleet_db.set_device_secret(conn, seeded.mac, "8" * 64)
            fleet_db.set_device_token(conn, seeded.mac, "newer-token")
    finally:
        conn.close()
    code, out = _run(seeded, capsys, "--apply")
    assert code == 0
    assert "1 secret(s), 1 token(s)" in out
    assert "newer-token" not in out and "8" * 64 not in out
    assert os.path.exists(os.path.join(_quarantine(seeded), "devices.json"))


def test_an_existing_target_is_never_overwritten(seeded, capsys):
    os.makedirs(_quarantine(seeded))
    target = os.path.join(_quarantine(seeded), "byos_state.json")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write("older quarantine")
    before = _tree(seeded.state_dir)
    code, out = _run(seeded, capsys, "--apply")
    assert code == 2
    assert "already exists in the quarantine directory" in out
    assert _tree(seeded.state_dir) == before
    with open(target, encoding="utf-8") as fh:
        assert fh.read() == "older quarantine"


def test_one_remaining_legacy_file_is_moved_alone(seeded, capsys):
    os.unlink(os.path.join(seeded.state_dir, "byos_state.json"))
    code, out = _run(seeded, capsys, "--apply")
    assert code == 0
    assert "moved devices.json into" in out
    assert os.listdir(_quarantine(seeded)) == ["devices.json"]


@pytest.mark.parametrize("name", ["devices.json", "byos_state.json"])
def test_an_unreadable_legacy_file_is_refused(seeded, capsys, name):
    with open(os.path.join(seeded.state_dir, name), "w", encoding="utf-8") as fh:
        fh.write("{not json")
    before = _tree(seeded.state_dir)
    code, out = _run(seeded, capsys, "--apply")
    assert code == 2
    assert "refused" in out
    assert _tree(seeded.state_dir) == before


def test_the_quarantine_directory_is_in_the_backup_allow_list():
    import importlib.util
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "deploy", "backup", "skypane_backup.py")
    spec = importlib.util.spec_from_file_location("skypane_backup_for_retire", path)
    assert spec is not None and spec.loader is not None
    backup = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(backup)
    assert retire.QUARANTINE_DIRNAME in backup.INCLUDE_DIRS
    for name in retire.LEGACY_FILES:
        assert name in backup.INCLUDE_FILES
