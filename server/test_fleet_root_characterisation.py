#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Pins what the fleet-root registries, the fleet-root artwork directory and
`server.fleet_migrate` do on an install that has no per-frame registry or
artwork copies: the readers resolve every frame to the fleet root, and the
migration prints and writes the same on a fresh and on an already migrated
state."""
import json
import os

import server.fleet_migrate as fleet_migrate
from server import device_dirs
from server.plane import airline_default_types, illustrations, manual_resolutions, name_overrides
import skypane_live_state as live

OWNER = "owner@example.com"
DEVICE = "d_0000000a"
ENTRY = {"OCN": {"airline_name": "Oceanic", "created_at": "2026-01-01T00:00:00+00:00"}}
_DEFAULTS = "airline default types: "


def _migrate(state_dir, capsys, *flags):
    capsys.readouterr()
    rc = fleet_migrate.main(["--state-dir", state_dir, "--owner-email", OWNER, *flags])
    return rc, capsys.readouterr().out.splitlines()


def _kinds(lines):
    """The report lines with the per-airline default-type detail dropped."""
    return [ln for ln in lines if not (ln.startswith(_DEFAULTS + "set ") and ": " in ln[len(_DEFAULTS):])
            and not (ln.startswith(_DEFAULTS + "would set ") and ": " in ln[len(_DEFAULTS) + 10:])]


def test_fresh_dry_run_prints_the_import_and_the_defaults_and_writes_nothing(tmp_path, capsys):
    seeded = live.seed_live_like_state(str(tmp_path), migrated=False)
    before = live.snapshot_dir(seeded.state_dir)
    rc, lines = _migrate(seeded.state_dir, capsys, "--dry-run")
    assert rc == 0
    assert live.snapshot_dir(seeded.state_dir) == before
    assert lines[:3] == ["would create the owner as admin", "would ensure the Orly location",
                         "would add device " + seeded.mac]
    assert lines[3] == _DEFAULTS + "nothing to do"
    assert lines[4].startswith(_DEFAULTS + "would set ")
    assert not [ln for ln in lines if ln.startswith(("airline names", "artwork"))]


def test_fresh_apply_imports_sets_the_defaults_and_creates_no_merge_file(tmp_path, capsys):
    seeded = live.seed_live_like_state(str(tmp_path), migrated=False)
    before = set(os.listdir(seeded.state_dir))
    rc, lines = _migrate(seeded.state_dir, capsys)
    assert rc == 0
    assert lines[:4] == ["create the owner as admin", "ensure the Orly location",
                         "add device " + seeded.mac, "migrated 1 legacy device(s)"]
    assert lines[4] == _DEFAULTS + "nothing to do"
    assert not [ln for ln in lines if ln.startswith(("airline names", "artwork"))]
    created = set(os.listdir(seeded.state_dir)) - before
    assert created == {"fleet.db", "airline_default_types.json",
                       "airline_default_types_set.json", "airline_default_types_set_migration.json"}
    with open(os.path.join(seeded.state_dir, "airline_default_types.json"), encoding="utf-8") as fh:
        stored = json.load(fh)
    assert lines[5] == "%sset %d" % (_DEFAULTS, len(stored))
    assert len(lines) == 6 + len(stored)
    assert not os.path.exists(os.path.join(seeded.state_dir, "illustration_overrides"))
    assert not os.path.exists(os.path.join(seeded.state_dir, "illustration_conflicts"))


def test_already_migrated_state_prints_nothing_to_do_and_changes_nothing(tmp_path, capsys):
    seeded = live.seed_live_like_state(str(tmp_path), migrated=False)
    assert _migrate(seeded.state_dir, capsys)[0] == 0
    names = {n: v for n, v in live.snapshot_dir(seeded.state_dir).items()
             if not n.endswith(("-wal", "-shm"))}
    for flags in ((), ("--dry-run",)):
        rc, lines = _migrate(seeded.state_dir, capsys, *flags)
        assert rc == 0
        assert lines == ["nothing to do", _DEFAULTS + "nothing to do", _DEFAULTS + "nothing to do"]
        after = {n: v for n, v in live.snapshot_dir(seeded.state_dir).items()
                 if not n.endswith(("-wal", "-shm"))}
        assert after == names


def test_registries_and_artwork_directory_resolve_to_the_fleet_root(tmp_path):
    root = str(tmp_path)
    frame = device_dirs.provision_device_dir(root, DEVICE, 800, 480)
    with open(os.path.join(root, "manual_resolutions.json"), "w", encoding="utf-8") as fh:
        json.dump(ENTRY, fh)
    with open(os.path.join(root, "airline_name_overrides.json"), "w", encoding="utf-8") as fh:
        json.dump(ENTRY, fh)
    with open(os.path.join(root, "airline_default_types.json"), "w", encoding="utf-8") as fh:
        json.dump({"air-france": "a320"}, fh)
    for state_dir in (root, frame):
        assert manual_resolutions.load_registry_file(manual_resolutions.manual_resolutions_path(state_dir)) == ENTRY
        assert name_overrides.load_name_overrides(state_dir) == ENTRY
        assert airline_default_types.load_default_types(state_dir) == {"air-france": "A320"}
        assert illustrations.override_dir_for_state_dir(state_dir) == os.path.join(
            root, "illustration_overrides")
    assert manual_resolutions.manual_resolutions_path(frame) == os.path.join(root, "manual_resolutions.json")


def test_readers_ignore_files_left_in_a_frame_directory(tmp_path):
    root = str(tmp_path)
    frame = device_dirs.provision_device_dir(root, DEVICE, 800, 480)
    for name in ("manual_resolutions.json", "airline_name_overrides.json"):
        with open(os.path.join(frame, name), "w", encoding="utf-8") as fh:
            json.dump(ENTRY, fh)
    with open(os.path.join(frame, "airline_default_types.json"), "w", encoding="utf-8") as fh:
        json.dump({"air-france": "A320"}, fh)
    os.makedirs(os.path.join(frame, "illustration_overrides"))
    with open(os.path.join(frame, "illustration_overrides", "ocn.png"), "wb") as fh:
        fh.write(b"x")
    for state_dir in (root, frame):
        assert manual_resolutions.load_registry_file(manual_resolutions.manual_resolutions_path(state_dir)) == {}
        assert name_overrides.load_name_overrides(state_dir) == {}
        assert airline_default_types.load_default_types(state_dir) == {}
        assert illustrations.override_path_for_key("ocn", state_dir) == os.path.join(
            root, "illustration_overrides", "ocn.png")
        assert not os.path.exists(illustrations.override_path_for_key("ocn", state_dir))
