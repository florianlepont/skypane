# companion/conftest.py: the ONE shared companion/app.py test-server
# fixture family every companion test module builds on, instead of
# copying its own Harness class.
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


# --- Missing-browser policy and loopback-only browser guard --------------

def _browser_required():
    """True in CI (GitHub sets CI=true) or with SKYPANE_REQUIRE_BROWSER=1:
    there, a harness that could not launch Chromium is a failure, not a
    skip. Locally it stays a visible pytest skip.
    """
    return (
        os.environ.get("SKYPANE_REQUIRE_BROWSER") == "1"
        or os.environ.get("CI", "").lower() == "true"
    )


@pytest.fixture(scope="session", autouse=True)
def _playwright_driver_tmpdir(tmp_path_factory):
    """Points TMPDIR at a session temp dir under pytest's basetemp for the
    whole session. Playwright's Node driver inherits the environment when
    pytest-playwright's session `playwright` fixture starts it, and makes
    its per-launch `playwright-artifacts-*` / `playwright_chromiumdev_profile-*`
    dirs under that TMPDIR — without this they land in the system /tmp
    (33-FOLLOWUPS.md F-03). Autouse at session scope, so it is set up before
    any requested session fixture, `playwright` included.
    """
    driver_tmp = str(tmp_path_factory.mktemp("playwright-driver-tmp"))
    saved = os.environ.get("TMPDIR")
    os.environ["TMPDIR"] = driver_tmp
    yield driver_tmp
    if saved is None:
        os.environ.pop("TMPDIR", None)
    else:
        os.environ["TMPDIR"] = saved


@pytest.fixture(scope="session")
def browser(browser_type, browser_type_launch_args):
    """Overrides pytest-playwright's own session-scoped `browser` fixture
    (built on its `launch_browser`/`browser_type`/`browser_type_launch_args`
    chain): a missing/unlaunchable Chromium is a hard pytest.fail() when a
    browser is required (CI / SKYPANE_REQUIRE_BROWSER=1), and a visible
    pytest.skip() otherwise — it never passes silently.
    Do not pass --browser-channel: the default resolution
    matches the --only-shell-installed binary.
    """
    try:
        b = browser_type.launch(**browser_type_launch_args)
    except Exception as exc:
        if _browser_required():
            pytest.fail(
                "Chromium could not launch (CI / SKYPANE_REQUIRE_BROWSER=1): %r"
                % (exc,))
        pytest.skip(
            "Chromium could not launch: %r - run "
            "`playwright install --only-shell chromium`" % (exc,))
    yield b
    b.close()


# Requests continued through the loopback-only guard without inspection:
# data:/blob:/about: never reach a real network, and the loopback hosts
# are companion/app.py's own AppServer instances a browser test drives.
_ALWAYS_ALLOWED_SCHEMES = ("data", "blob", "about")
_ALWAYS_ALLOWED_HOSTS = ("127.0.0.1", "localhost", "::1")


def _make_route_guard(blocked):
    def handler(route, request):
        from urllib.parse import urlsplit

        parsed = urlsplit(request.url)
        if parsed.scheme in _ALWAYS_ALLOWED_SCHEMES or (
                parsed.hostname in _ALWAYS_ALLOWED_HOSTS):
            route.continue_()
            return
        blocked.append(request.url)
        route.abort()

    return handler


@pytest.fixture
def blocked_requests():
    """The per-test list of non-loopback URLs the browser guard aborted.
    A test that deliberately triggers one of these must .clear() it
    before the test ends, or the new_context teardown below fails the
    test naming the recorded URL(s).
    """
    return []


@pytest.fixture
def new_context(new_context, blocked_requests):
    """Overrides pytest-playwright's own function-scoped `new_context`
    factory fixture. The plugin's own `context`/`page` fixtures are built
    on `new_context`, so both are covered by this override too.
    Every context this factory returns gets a route guard
    that continues loopback/data/blob/about requests and aborts
    everything else, recording the aborted URL in `blocked_requests`.
    Guard rule G10: a test that needs an extra viewport/context calls
    THIS fixture (`new_context(viewport=...)`), never
    `browser.new_context(...)` directly — only this fixture installs the
    guard.
    """
    def factory(**kwargs):
        ctx = new_context(**kwargs)
        ctx.route("**/*", _make_route_guard(blocked_requests))
        return ctx

    yield factory

    if blocked_requests:
        pytest.fail(
            "browser test made non-loopback request(s), blocked: %r"
            % (blocked_requests,))
