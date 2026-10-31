"""Auth0 is the only sign-in: startup requires a complete configuration,
retired variables are ignored, and legacy session rows and POST /login are
inert.
"""
import os
import sqlite3
import subprocess
import sys
import time

import pytest

import access_matrix_support
import companion_app_server
from companion import sign_in_config
from companion_app_server import AppServer, http_request, login
from server import fleet_db, fleet_sessions
from skypane_test_support import child_env

AUTH0_VARS = {
    "SKYPANE_AUTH0_DOMAIN": "tenant.example.com",
    "SKYPANE_AUTH0_CLIENT_ID": "client-id-value",
    "SKYPANE_AUTH0_CLIENT_SECRET": "client-secret-value",
    "SKYPANE_COMPANION_PUBLIC_URL": "https://frame.example.com",
}
RETIRED = {
    "SKYPANE_COMPANION_PASSWORD": "retired-shared-password",
    "SKYPANE_LEGACY_PASSWORD_LOGIN": "0",
}


def _run_start(tmp_path, env_extra):
    env = child_env(dict(os.environ))
    for name in [n for n in env if n.startswith(("SKYPANE_COMPANION", "SKYPANE_AUTH0", "SKYPANE_LEGACY"))]:
        del env[name]
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, companion_app_server.APP_PATH, "--port", "0",
         "--state-dir", str(tmp_path)],
        env=env, capture_output=True, text=True, timeout=30)


def test_no_auth0_configuration_is_refused_naming_variables_only():
    with pytest.raises(sign_in_config.SignInConfigError) as excinfo:
        sign_in_config.validate_sign_in_config({})
    message = str(excinfo.value)
    for name in ("SKYPANE_AUTH0_DOMAIN", "SKYPANE_AUTH0_CLIENT_ID", "SKYPANE_AUTH0_CLIENT_SECRET"):
        assert name in message


def test_a_complete_configuration_is_accepted_and_retired_variables_are_ignored():
    sign_in_config.validate_sign_in_config(AUTH0_VARS)
    sign_in_config.validate_sign_in_config(dict(AUTH0_VARS, **RETIRED))


def test_startup_without_auth0_exits_before_serving(tmp_path):
    result = _run_start(tmp_path, RETIRED)
    assert result.returncode == 1
    assert "SKYPANE_AUTH0_DOMAIN" in result.stderr
    assert "serving on" not in result.stdout
    assert RETIRED["SKYPANE_COMPANION_PASSWORD"] not in result.stderr


@pytest.mark.parametrize("present", [
    ["SKYPANE_AUTH0_DOMAIN"],
    ["SKYPANE_AUTH0_DOMAIN", "SKYPANE_AUTH0_CLIENT_ID"],
])
def test_a_partial_auth0_setup_names_the_missing_variables_only(tmp_path, present):
    env = {name: AUTH0_VARS[name] for name in present}
    result = _run_start(tmp_path, env)
    assert result.returncode == 1
    missing = [n for n in AUTH0_VARS if n.startswith("SKYPANE_AUTH0") and n not in present]
    for name in missing:
        assert name in result.stderr
    for name in present:
        assert AUTH0_VARS[name] not in result.stderr


def test_retired_variables_alongside_a_complete_configuration_start_normally(tmp_path):
    server = AppServer(str(tmp_path / "state"), env_overrides=dict(AUTH0_VARS, **RETIRED))
    try:
        server.start()
        status, _headers, body = http_request(server.url("/login"))
        assert status == 200
        assert b"/login/auth0" in body
        assert b'type="password"' not in body
    finally:
        server.stop()


def test_the_login_page_offers_only_auth0(app_server):
    status, _headers, body = http_request(app_server.url("/login"))
    assert status == 200
    assert b'href="/login/auth0"' in body
    for needle in (b'type="password"', b"login-legacy", b"shared password"):
        assert needle not in body


def test_post_login_is_not_routed_and_creates_nothing(app_server):
    status, headers, _body = http_request(
        app_server.url("/login"), method="POST", data=b"password=anything",
        extra_headers={"Origin": app_server.base_url()})
    assert status in (404, 405)
    assert "Set-Cookie" not in headers
    conn = sqlite3.connect(os.path.join(app_server.state_dir, "fleet.db"))
    try:
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    finally:
        conn.close()


def test_a_second_login_gives_a_second_valid_cookie(app_server):
    first, second = login(app_server), login(app_server)
    assert first != second
    for cookie in (first, second):
        assert http_request(app_server.url("/account"), cookie=cookie)[0] == 200


@pytest.mark.parametrize("retired_flag", [None, "1"])
def test_a_legacy_session_row_never_authenticates_and_is_deleted(
        app_server_in_process, monkeypatch, retired_flag):

    if retired_flag is not None:
        monkeypatch.setenv("SKYPANE_LEGACY_PASSWORD_LOGIN", retired_flag)
    server = app_server_in_process
    conn = fleet_db.connect(server.state_dir)
    try:
        cookie = access_matrix_support.session_cookie_for(
            server.state_dir, fleet_sessions.PRINCIPAL_LEGACY_ADMIN, None,
            int(time.time()))
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 1
        status, headers, body = http_request(server.url("/settings"), cookie=cookie)
        assert status == 303
        assert headers["Location"].startswith("/login")
        assert b"Settings" not in body
        assert conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0] == 0
    finally:
        conn.close()
