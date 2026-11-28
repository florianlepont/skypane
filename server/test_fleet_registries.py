"""The frame directory listing: the root first, then valid device directories
in sorted id order; links, odd names and plain files are skipped."""
import os

from server import device_dirs
from server.plane import fleet_registries as fr

A, B = "d_0000000a", "d_0000000b"


def test_the_root_comes_first_then_valid_frame_directories_in_id_order(tmp_path):
    for device_id in (B, A):
        device_dirs.provision_device_dir(str(tmp_path), device_id, 800, 480)
    listing = fr.frame_state_dirs(str(tmp_path))
    assert listing[0] == (fr.LIVE_LABEL, str(tmp_path))
    assert [label for label, _d in listing[1:]] == [A, B]
    assert all(os.path.isdir(directory) for _label, directory in listing)


def test_a_root_without_devices_lists_only_itself(tmp_path):
    assert fr.frame_state_dirs(str(tmp_path)) == [(fr.LIVE_LABEL, str(tmp_path))]


def test_a_symlinked_frame_directory_and_bad_names_are_skipped(tmp_path):
    device_dirs.provision_device_dir(str(tmp_path), A, 800, 480)
    outside = tmp_path / "outside"
    outside.mkdir()
    devices = os.path.join(str(tmp_path), "devices")
    os.symlink(str(outside), os.path.join(devices, B))
    os.makedirs(os.path.join(devices, "not-an-id"))
    os.makedirs(os.path.join(devices, "d_0000000D"))
    with open(os.path.join(devices, "d_0000000c"), "w") as fh:
        fh.write("not a directory")
    assert [label for label, _d in fr.frame_state_dirs(str(tmp_path))] == [fr.LIVE_LABEL, A]
