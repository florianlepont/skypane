# SPDX-License-Identifier: AGPL-3.0-only
"""The build id shown on Account: a 7-hex short id taken from the release directory the code
runs from (through its real path, since the service runs from a `current` symlink), else from
`SKYPANE_BUILD`, else `dev`. Nothing but hex ever comes out."""
import os

import pytest

from companion import build_info

SHA = "3f9c1ab" + "0" * 33


def _release(tmp_path, sha=SHA):
    root = tmp_path / "opt" / "skypane"
    code = root / "releases" / sha / "companion"
    code.mkdir(parents=True)
    module = code / "build_info.py"
    module.write_text("")
    return root, module


def test_a_symlinked_release_directory_gives_the_target_sha(tmp_path):
    root, _module = _release(tmp_path)
    os.symlink(root / "releases" / SHA, root / "current")
    through_link = str(root / "current" / "companion" / "build_info.py")
    assert build_info.build_id(through_link, environ={}) == "3f9c1ab"


def test_a_release_path_without_a_symlink_gives_the_sha(tmp_path):
    _root, module = _release(tmp_path)
    assert build_info.build_id(str(module), environ={}) == "3f9c1ab"


def test_the_release_name_wins_over_the_environment(tmp_path):
    _root, module = _release(tmp_path)
    assert build_info.build_id(str(module), environ={"SKYPANE_BUILD": "abcdef1"}) == "3f9c1ab"


@pytest.mark.parametrize("value,expected", [
    ("abcdef1", "abcdef1"),
    ("ABCDEF1234", "abcdef1"),
    ("a" * 40, "aaaaaaa"),
])
def test_the_environment_is_used_outside_a_release(tmp_path, value, expected):
    path = tmp_path / "checkout" / "companion" / "build_info.py"
    assert build_info.build_id(str(path), environ={"SKYPANE_BUILD": value}) == expected


@pytest.mark.parametrize("value", [
    "", "abc12", "xyz1234", "<b>12345</b>", "abcdef1\"onclick=", "a" * 41, " abcdef1",
    "abcdef1\n"])
def test_anything_else_gives_dev(tmp_path, value):
    path = tmp_path / "checkout" / "companion" / "build_info.py"
    assert build_info.build_id(str(path), environ={"SKYPANE_BUILD": value}) == "dev"


def test_no_environment_value_gives_dev(tmp_path):
    path = tmp_path / "checkout" / "companion" / "build_info.py"
    assert build_info.build_id(str(path), environ={}) == "dev"


def test_a_non_hex_release_name_is_not_a_release(tmp_path):
    _root, module = _release(tmp_path, sha="z" * 40)
    assert build_info.build_id(str(module), environ={}) == "dev"
