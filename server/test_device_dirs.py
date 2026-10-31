#!/usr/bin/env python3
"""Tests for server/device_dirs.py: state_path shape checks, containment
and idempotent provisioning."""
import os

import pytest

from server import device_dirs, panel_format

DEV = "d_1a2b3c4d"

BAD_PATHS = [
    "",
    "..",
    "/etc",
    "devices",
    "devices/",
    "devices/..",
    "devices/d_1A2B3C4D",
    "devices/d_1a2b3c4",
    "devices/d_1a2b3c4d/x",
    "devices/d_1a2b3c4d\n",
    "./devices/d_1a2b3c4d",
]


def test_live_path_resolves_to_root(tmp_path):
    assert device_dirs.resolve_state_dir(str(tmp_path), ".") == str(tmp_path)


def test_device_path_resolves_under_devices(tmp_path):
    got = device_dirs.resolve_state_dir(str(tmp_path), "devices/" + DEV)
    assert got == os.path.join(str(tmp_path), "devices", DEV)


@pytest.mark.parametrize("bad", BAD_PATHS)
def test_bad_shapes_are_rejected(tmp_path, bad):
    assert device_dirs.valid_state_path(bad) is False
    with pytest.raises(ValueError):
        device_dirs.resolve_state_dir(str(tmp_path), bad)


def test_valid_state_path_accepts_only_the_two_shapes():
    assert device_dirs.valid_state_path(".")
    assert device_dirs.valid_state_path("devices/" + DEV)


def test_symlinked_device_dir_escaping_devices_is_rejected(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (tmp_path / "devices").mkdir()
    os.symlink(str(outside), str(tmp_path / "devices" / DEV))
    with pytest.raises(ValueError):
        device_dirs.resolve_state_dir(str(tmp_path), "devices/" + DEV)


def test_symlinked_device_dir_inside_devices_is_rejected(tmp_path):
    (tmp_path / "devices" / "d_00000000").mkdir(parents=True)
    os.symlink(str(tmp_path / "devices" / "d_00000000"),
               str(tmp_path / "devices" / DEV))
    with pytest.raises(ValueError):
        device_dirs.resolve_state_dir(str(tmp_path), "devices/" + DEV)


def test_state_path_for_validates_the_id():
    assert device_dirs.state_path_for(DEV) == "devices/" + DEV
    with pytest.raises(ValueError):
        device_dirs.state_path_for("../x")
    assert device_dirs.is_valid_device_id(DEV)
    assert not device_dirs.is_valid_device_id(DEV + "\n")


def test_provision_seeds_config_and_white_panel_only(tmp_path):
    d = device_dirs.provision_device_dir(str(tmp_path), DEV, 8, 4)
    assert d == os.path.join(str(tmp_path), "devices", DEV)
    assert sorted(os.listdir(d)) == ["device_config.json", "panel.bin"]
    with open(os.path.join(d, "device_config.json")) as fh:
        assert fh.read().strip() == "{}"
    white = (panel_format.WHITE << 4) | panel_format.WHITE
    with open(os.path.join(d, "panel.bin"), "rb") as fh:
        assert fh.read() == bytes([white]) * ((8 // 2) * 4)


def test_provision_never_touches_live_root_files(tmp_path):
    (tmp_path / "panel.bin").write_bytes(b"live")
    device_dirs.provision_device_dir(str(tmp_path), DEV, 8, 4)
    assert (tmp_path / "panel.bin").read_bytes() == b"live"
    assert sorted(os.listdir(tmp_path)) == ["devices", "panel.bin"]


def test_provision_is_idempotent_and_keeps_existing_files(tmp_path):
    d = device_dirs.provision_device_dir(str(tmp_path), DEV, 8, 4, fill=0x22)
    with open(os.path.join(d, "panel.bin"), "wb") as fh:
        fh.write(b"custom")
    with open(os.path.join(d, "device_config.json"), "w") as fh:
        fh.write('{"a": 1}')
    device_dirs.provision_device_dir(str(tmp_path), DEV, 8, 4, fill=0x33)
    with open(os.path.join(d, "panel.bin"), "rb") as fh:
        assert fh.read() == b"custom"
    with open(os.path.join(d, "device_config.json")) as fh:
        assert fh.read() == '{"a": 1}'


def test_provision_rejects_bad_id(tmp_path):
    with pytest.raises(ValueError):
        device_dirs.provision_device_dir(str(tmp_path), "../evil", 8, 4)
    assert not (tmp_path / "devices").exists()


def test_distinct_fills_give_distinct_panels(tmp_path):
    a = device_dirs.provision_device_dir(str(tmp_path), "d_00000001", 8, 4, fill=0x22)
    b = device_dirs.provision_device_dir(str(tmp_path), "d_00000002", 8, 4, fill=0x33)
    with open(os.path.join(a, "panel.bin"), "rb") as fa, \
            open(os.path.join(b, "panel.bin"), "rb") as fb:
        pa, pb = fa.read(), fb.read()
    assert pa == bytes([0x22]) * 16
    assert pb == bytes([0x33]) * 16


def test_wipe_removes_the_whole_tree_and_allows_reprovision(tmp_path):
    root = str(tmp_path)
    directory = device_dirs.provision_device_dir(root, DEV, 4, 2)
    with open(os.path.join(directory, "future_file.bin"), "wb") as fh:
        fh.write(b"x")
    device_dirs.wipe_device_dir(root, "devices/" + DEV)
    assert not os.path.exists(directory)
    device_dirs.wipe_device_dir(root, "devices/" + DEV)  # already gone: no error
    again = device_dirs.provision_device_dir(root, DEV, 4, 2)
    assert sorted(os.listdir(again)) == [
        device_dirs.CONFIG_FILENAME, device_dirs.PANEL_FILENAME
    ]


def test_wipe_refuses_the_live_path_and_keeps_root_files(tmp_path):
    (tmp_path / "panel.bin").write_bytes(b"live")
    with pytest.raises(ValueError):
        device_dirs.wipe_device_dir(str(tmp_path), ".")
    assert (tmp_path / "panel.bin").read_bytes() == b"live"


@pytest.mark.parametrize("bad", ["..", "devices/..", "../x", "/etc", "devices/d_1a2b3c4d/x"])
def test_wipe_refuses_bad_shapes(tmp_path, bad):
    with pytest.raises(ValueError):
        device_dirs.wipe_device_dir(str(tmp_path), bad)


def test_wipe_refuses_a_symlinked_directory_and_spares_the_target(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "keep.txt").write_text("keep")
    (tmp_path / "devices").mkdir()
    os.symlink(str(outside), str(tmp_path / "devices" / DEV))
    with pytest.raises(ValueError):
        device_dirs.wipe_device_dir(str(tmp_path), "devices/" + DEV)
    assert (outside / "keep.txt").read_text() == "keep"
