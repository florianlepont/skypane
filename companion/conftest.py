# companion/conftest.py: the ONE shared companion/app.py test-server
# fixture family (33-02-PLAN.md, TST-10) every companion test module
# builds on, instead of copying its own Harness class.
#
# Scope rationale: `app_server` and `make_app_server` are function-scoped
# because they isolate each test by default — a test that POSTs or
# otherwise mutates server state must never see another test's leftover
# state, and xdist may run tests in any order across workers.
# `module_app_server_factory` is module-scoped, for a module's own
# read-only server shared across several GET-only tests in that module
# (cheaper than starting a fresh subprocess per test, safe only because
# nothing in that module mutates the shared server's state — see
# 33-MIGRATION-RULES.md section 2).
import os
import sys

# This file is collected before any companion/test_*.py module, so
# test-support/ (companion_app_server, skypane_test_support) must be on
# sys.path before any fixture below imports from it — mirrors the
# repo-root conftest.py's own bootstrap.
_TEST_SUPPORT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "test-support")
if _TEST_SUPPORT_DIR not in sys.path:
    sys.path.insert(0, _TEST_SUPPORT_DIR)

import pytest  # noqa: E402

import companion_app_server  # noqa: E402


# --- Real subprocess server fixtures --------------------------------------

@pytest.fixture
def app_server(tmp_path):
    """A running companion/app.py subprocess, no fake providers, its own
    state dir under tmp_path. Function-scoped: a fresh server per test.
    """
    server = companion_app_server.AppServer(str(tmp_path / "state"))
    server.start()
    yield server
    server.stop()


def _server_factory(base_dir):
    """Shared implementation behind make_app_server / module_app_server_factory:
    a factory that starts a new AppServer per call, each under its own
    numbered subdirectory of base_dir, and stops every server it started
    at fixture teardown.
    """
    servers = []
    counter = {"n": 0}

    def factory(seed=None, extra_args=(), fake_providers=False, env_overrides=None):
        counter["n"] += 1
        state_dir = os.path.join(str(base_dir), "state-%d" % counter["n"])
        os.makedirs(state_dir, exist_ok=True)
        if seed is not None:
            seed(state_dir)
        server = companion_app_server.AppServer(
            state_dir, extra_args=extra_args, fake_providers=fake_providers,
            env_overrides=env_overrides)
        server.start()
        servers.append(server)
        return server

    return factory, servers


@pytest.fixture
def make_app_server(tmp_path):
    """A factory fixture: make_app_server(seed=None, extra_args=(),
    fake_providers=False, env_overrides=None) -> AppServer. Each call
    gets its own state dir under tmp_path/state-<n>; seed(state_dir), if
    given, runs before the server starts. Every server made is stopped
    at teardown. Function-scoped.
    """
    factory, servers = _server_factory(tmp_path)
    yield factory
    for server in servers:
        server.stop()


@pytest.fixture(scope="module")
def module_app_server_factory(tmp_path_factory):
    """Same factory contract as make_app_server, module-scoped: for a
    module's own read-only server(s) shared across several GET-only tests
    in that module. See the scope rationale above this file's imports.
    """
    base_dir = tmp_path_factory.mktemp("companion-module")
    factory, servers = _server_factory(base_dir)
    yield factory
    for server in servers:
        server.stop()


@pytest.fixture
def app_server_in_process(tmp_path):
    """A companion/app.py ThreadingHTTPServer running in THIS process's
    own thread (see InProcessAppServer's docstring for why). Function-scoped.
    """
    server = companion_app_server.InProcessAppServer(str(tmp_path / "state"))
    yield server
    server.stop()
