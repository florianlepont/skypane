#!/usr/bin/env python3
"""The pairing modules live in the `server.pairing` package; the old flat
module names are sys.modules alias shims. These tests prove every old name is
the very same module object as the new one, so monkeypatch and mock.patch on
the old name reach the moved code."""
import importlib
import os
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

from skypane_test_support import REPO_ROOT, child_env

PAIRS = [
    ("server.pairings", "server.pairing.pairings"),
    ("server.pairing_code", "server.pairing.code"),
    ("server.pairing_image", "server.pairing.image"),
]


@pytest.mark.parametrize("old,new", PAIRS)
def test_old_name_is_the_new_module(old, new):
    assert importlib.import_module(old) is importlib.import_module(new)


@pytest.mark.parametrize("old,new", PAIRS)
def test_package_attribute_is_the_new_module(old, new):
    from server import pairing
    importlib.import_module(old)
    assert getattr(pairing, new.rsplit(".", 1)[1]) is importlib.import_module(new)


@pytest.mark.parametrize("old,new", PAIRS)
def test_monkeypatch_through_old_name_reaches_moved_code(monkeypatch, old, new):
    old_mod = importlib.import_module(old)
    new_mod = importlib.import_module(new)
    monkeypatch.setattr(old_mod, "_shim_probe", 42, raising=False)
    assert new_mod._shim_probe == 42


def test_mock_patch_on_old_code_name_reaches_pairing_image():
    from server.pairing import image
    sentinel = object()
    with mock.patch("server.pairing_code.format_code", sentinel):
        assert image.pairing_code.format_code is sentinel


def test_import_old_names_from_foreign_cwd():
    with tempfile.TemporaryDirectory() as cwd:
        env = child_env()
        env["PYTHONPATH"] = os.pathsep.join(
            [REPO_ROOT, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        result = subprocess.run(
            [sys.executable, "-c",
             "import server.pairings as a, server.pairing.pairings as b\n"
             "assert a is b\n"
             "import server.pairing_image as c, server.pairing.image as d\n"
             "assert c is d\n"],
            env=env, cwd=cwd, capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
