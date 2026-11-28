#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""The firmware modules live in the `server.firmware` package; the old flat
module names are sys.modules alias shims. These tests prove every old name
is the very same module object as the new one (so monkeypatch and
mock.patch on the old name reach the moved code) and that the documented
`-m server.firmware_cli` and foreign-cwd imports still work."""
import importlib
import os
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

from skypane_test_support import REPO_ROOT, child_env

PAIRS = [
    ("server.firmware_cli", "server.firmware.cli"),
    ("server.firmware_image", "server.firmware.image"),
    ("server.firmware_registry", "server.firmware.registry"),
]


@pytest.mark.parametrize("old,new", PAIRS)
def test_old_name_is_the_new_module(old, new):
    assert importlib.import_module(old) is importlib.import_module(new)


@pytest.mark.parametrize("old,new", PAIRS)
def test_package_attribute_is_the_new_module(old, new):
    from server import firmware
    importlib.import_module(old)
    assert getattr(firmware, new.rsplit(".", 1)[1]) is importlib.import_module(new)


@pytest.mark.parametrize("old,new", PAIRS)
def test_monkeypatch_through_old_name_reaches_moved_code(monkeypatch, old, new):
    old_mod = importlib.import_module(old)
    new_mod = importlib.import_module(new)
    monkeypatch.setattr(old_mod, "_shim_probe", 42, raising=False)
    assert new_mod._shim_probe == 42


def test_mock_patch_on_old_registry_name_changes_what_moved_code_reads():
    from server.firmware import registry
    with mock.patch("server.firmware_registry.VERSION_MAX_LEN", 3):
        assert registry.VERSION_MAX_LEN == 3


def test_mock_patch_on_old_cli_name_changes_repo_root():
    from server.firmware import cli
    with mock.patch("server.firmware_cli._repo_root", lambda: "/nowhere"):
        assert cli._repo_root() == "/nowhere"


def test_repo_root_bootstrap_points_at_the_repository_root():
    from server.firmware import cli, image
    assert os.path.samefile(cli._repo_root(), REPO_ROOT)
    assert os.path.samefile(image._REPO_ROOT, REPO_ROOT)


def _foreign_run(args):
    with tempfile.TemporaryDirectory() as cwd:
        env = child_env()
        env["PYTHONPATH"] = os.pathsep.join(
            [REPO_ROOT, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        return subprocess.run(
            [sys.executable, *args], env=env, cwd=cwd,
            capture_output=True, text=True, timeout=60)


def test_dash_m_firmware_cli_help_from_foreign_cwd():
    result = _foreign_run(["-m", "server.firmware_cli", "--help"])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "usage" in result.stdout.lower()


def test_import_old_registry_from_foreign_cwd():
    result = _foreign_run([
        "-c",
        "import server.firmware_registry as a, server.firmware.registry as b\n"
        "assert a is b\n"
        "import server.firmware_image as c, server.firmware.image as d\n"
        "assert c is d\n"])
    assert result.returncode == 0, result.stdout + result.stderr
