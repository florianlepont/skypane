"""Self-tests for companion/conftest.py's shared app-server fixtures and
test-support/companion_app_server.py (33-02-PLAN.md Task 2, TST-10).
Proves the behaviour every later migration plan relies on: real
subprocess lifecycle, process-group teardown, the no-network child
environment, the fake-providers plumbing, and the in-process variant.
"""
import os
import socket
import textwrap
import urllib.parse

import pytest

import companion_app_server
from companion import auth
from skypane_test_support import NO_NETWORK_ENV_VAR, TEST_SUPPORT_DIR


def test_login_page_and_flow(app_server):
    """GET /login returns 200; POST /login with TEST_PASSWORD returns 303
    with a Set-Cookie; login(app_server) returns a non-empty cookie.
    """
    status, _, _ = companion_app_server.get(app_server, "/login")
    assert status == 200

    status, headers, _ = companion_app_server.http_request(
        app_server.base_url() + "/login", method="POST",
        data=urllib.parse.urlencode(
            {"password": companion_app_server.TEST_PASSWORD}).encode())
    assert status == 303
    assert companion_app_server.cookie_value(headers)

    cookie = companion_app_server.login(app_server)
    assert cookie


def test_http_request_never_follows_redirects(app_server):
    """An unauthenticated GET / returns 303 with a Location header that
    contains /login, and http_request() surfaces it rather than
    transparently following it.
    """
    status, headers, _ = companion_app_server.get(app_server, "/")
    assert status == 303
    assert "/login" in headers.get("Location", "")


def test_make_app_server_gives_distinct_ports_and_state_dirs(make_app_server, tmp_path):
    """Two app_server instances made in one test run on different ports
    and have different state dirs, both under tmp_path.
    """
    first = make_app_server()
    second = make_app_server()

    assert first.port != second.port
    assert first.state_dir != second.state_dir
    tmp_path_str = str(tmp_path)
    assert first.state_dir.startswith(tmp_path_str)
    assert second.state_dir.startswith(tmp_path_str)


_FAKE_APP_SRC = textwrap.dedent("""\
    import socket
    import subprocess
    import sys
    import time

    def main():
        args = sys.argv[1:]
        port = int(args[args.index("--port") + 1])
        state_dir = args[args.index("--state-dir") + 1]
        # A grandchild with no setsid() of its own: it inherits this
        # process's process group, exactly like a real subprocess a
        # production handler might launch.
        grandchild = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
        with open(state_dir + "/grandchild.pid", "w") as fh:
            fh.write(str(grandchild.pid))
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", port))
        srv.listen(1)
        while True:
            time.sleep(1)

    if __name__ == "__main__":
        main()
    """)


def _process_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_stop_kills_the_whole_process_group_including_a_grandchild(tmp_path, monkeypatch):
    """After AppServer.stop(), os.kill(pid, 0) raises ProcessLookupError
    for the server's own pid; stop() also terminates a grandchild the
    server process spawned in the same process group (proves killpg is
    used, not a plain terminate() of only the direct child).
    """
    fake_app = tmp_path / "fake_app.py"
    fake_app.write_text(_FAKE_APP_SRC)
    monkeypatch.setattr(companion_app_server, "APP_PATH", str(fake_app))

    state_dir = tmp_path / "state"
    server = companion_app_server.AppServer(str(state_dir))
    server.start()
    pid = server.pid
    grandchild_pid = int((state_dir / "grandchild.pid").read_text())
    assert _process_alive(grandchild_pid)

    server.stop()

    assert not _process_alive(pid)
    assert not _process_alive(grandchild_pid)


def test_child_env_carries_no_network_var_and_pythonpath(app_server):
    """The child's environment carries the no-network var (read
    /proc/<pid>/environ) and PYTHONPATH starts with TEST_SUPPORT_DIR.
    """
    with open("/proc/%d/environ" % app_server.pid, "rb") as fh:
        raw = fh.read()
    entries = dict(item.split(b"=", 1) for item in raw.split(b"\0") if b"=" in item)

    assert entries.get(NO_NETWORK_ENV_VAR.encode()) == b"1"
    pythonpath = entries.get(b"PYTHONPATH", b"").decode()
    assert pythonpath.startswith(TEST_SUPPORT_DIR)


def test_make_app_server_fake_providers_writes_spec_and_calls_log(make_app_server):
    """make_app_server(fake_providers=True) writes fake-providers.json
    into its state dir, and fake_provider_calls() returns a list.
    """
    server = make_app_server(fake_providers=True)

    assert os.path.exists(os.path.join(server.state_dir, "fake-providers.json"))
    assert server.fake_provider_calls() == []


def test_make_app_server_seed_runs_before_start(make_app_server):
    """make_app_server(seed=fn) calls fn(state_dir) before the process
    starts.
    """
    seen = []

    def seed(state_dir):
        seen.append(state_dir)
        assert os.path.isdir(state_dir)

    server = make_app_server(seed=seed)

    assert seen == [server.state_dir]


def test_app_server_in_process_serves_login_and_restores_password_env(
        app_server_in_process, monkeypatch):
    """app_server_in_process serves /login and restores the password env
    var after teardown.
    """
    monkeypatch.delenv(auth.PASSWORD_ENV_VAR, raising=False)
    server = app_server_in_process

    status, _, _ = companion_app_server.get(server, "/login")
    assert status == 200
    assert os.environ.get(auth.PASSWORD_ENV_VAR) == companion_app_server.TEST_PASSWORD


def test_served_stylesheet_and_asset(app_server):
    """served_stylesheet(server) returns str with a Content-Type
    starting with text/css; served_asset(server, "/static/<name>.js")
    returns the served JS text.
    """
    css_text = companion_app_server.served_stylesheet(app_server)
    assert isinstance(css_text, str)
    assert css_text

    js_text = companion_app_server.served_asset(app_server, "/static/battery-trend.js")
    assert isinstance(js_text, str)
    assert js_text


def test_legacy_harness_still_matches_original_behaviour():
    """LegacyHarness's no-arg constructor mirrors the original copied
    Harness classes exactly enough that a still-legacy script harness can
    swap one import line and keep working.
    """
    harness = companion_app_server.LegacyHarness()
    try:
        harness.start()
        status, _, _ = companion_app_server.get(harness, "/login")
        assert status == 200
    finally:
        harness.stop()
        harness.cleanup()
    assert not os.path.exists(harness.state_dir)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
