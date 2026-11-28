#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""The polling-support modules live in the `server.polling` package; the old
flat module names are sys.modules alias shims. These tests prove every old
name is the very same module object as the new one (so monkeypatch and
mock.patch on the old name reach the moved code) and that the poll loop
entry point still starts from a foreign working directory."""
import importlib
import os
import subprocess
import sys
import tempfile
from unittest import mock

import pytest

from skypane_test_support import REPO_ROOT, child_env

PAIRS = [
    ("server.request_budget", "server.polling.request_budget"),
    ("server.zone_fetch", "server.polling.zone_fetch"),
    ("server.http_fetch", "server.polling.http_fetch"),
    ("server.fleet_zones", "server.polling.fleet_zones"),
    ("server.fleet_cycle", "server.polling.fleet_cycle"),
]


@pytest.mark.parametrize("old,new", PAIRS)
def test_old_name_is_the_new_module(old, new):
    assert importlib.import_module(old) is importlib.import_module(new)


@pytest.mark.parametrize("old,new", PAIRS)
def test_package_attribute_is_the_new_module(old, new):
    from server import polling
    importlib.import_module(old)
    assert getattr(polling, new.rsplit(".", 1)[1]) is importlib.import_module(new)


@pytest.mark.parametrize("old,new", PAIRS)
def test_monkeypatch_through_old_name_reaches_moved_code(monkeypatch, old, new):
    old_mod = importlib.import_module(old)
    new_mod = importlib.import_module(new)
    monkeypatch.setattr(old_mod, "_shim_probe", 42, raising=False)
    assert new_mod._shim_probe == 42


def test_mock_patch_on_old_request_budget_name_reaches_zone_fetch():
    from server.polling import zone_fetch
    sentinel = object()
    with mock.patch("server.request_budget.Ledger", sentinel, create=True):
        assert zone_fetch.request_budget.Ledger is sentinel


def _foreign_run(args):
    with tempfile.TemporaryDirectory() as cwd:
        env = child_env()
        env["PYTHONPATH"] = os.pathsep.join(
            [REPO_ROOT, env.get("PYTHONPATH", "")]).rstrip(os.pathsep)
        return subprocess.run(
            [sys.executable, *args], env=env, cwd=cwd,
            capture_output=True, text=True, timeout=60)


def test_poll_loop_help_from_foreign_cwd():
    result = _foreign_run([os.path.join(REPO_ROOT, "server", "poll_loop.py"), "--help"])
    assert result.returncode == 0, result.stdout + result.stderr


def test_import_old_names_from_foreign_cwd_in_poll_loop_order():
    result = _foreign_run([
        "-c",
        "import server.request_budget as a, server.polling.request_budget as b\n"
        "assert a is b\n"
        "import server.zone_fetch as c, server.polling.zone_fetch as d\n"
        "assert c is d\n"
        "import server.fleet_cycle as e, server.polling.fleet_cycle as f\n"
        "assert e is f\n"])
    assert result.returncode == 0, result.stdout + result.stderr
