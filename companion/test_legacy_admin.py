"""The shared-password fallback: its switch, throttle, audit lines, fail-closed
startup rules, and independence from the session store.
"""
import hashlib
import hmac
import os
import subprocess
import sys
import time
import urllib.parse

import pytest

import companion_app_server
from companion import app, auth
from companion_app_server import TEST_PASSWORD, AppServer, http_request, login
from skypane_test_support import child_env

FLAG = "SKYPANE_LEGACY_PASSWORD_LOGIN"
AUTH0_VARS = {
    "SKYPANE_AUTH0_DOMAIN": "tenant.example.com",
    "SKYPANE_AUTH0_CLIENT_ID": "client-id-value",
    "SKYPANE_AUTH0_CLIENT_SECRET": "client-secret-value",
    "SKYPANE_COMPANION_PUBLIC_URL": "https://frame.example.com",
}


def _post(server, password, xff, extra=None):
    data = {"password": password}
    data.update(extra or {})
    return http_request(
        server.url("/login"), method="POST",
        data=urllib.parse.urlencode(data).encode(),
        extra_headers={"X-Forwarded-For": xff})


# --- the switch --------------------------------------------------------------

@pytest.mark.parametrize("flag", [None, "1"])
def test_password_login_works_as_legacy_admin_only(app_server_in_process, monkeypatch, flag):
    if flag is None:
        monkeypatch.delenv(FLAG, raising=False)
    else:
        monkeypatch.setenv(FLAG, flag)
    server = app_server_in_process
    cookie = login(server)
    status, _headers, body = http_request(server.url("/account"), cookie=cookie)
    assert status == 200
    assert b"Administrator (legacy access)" in body
    assert b"banner__pill" in body
    conn = app.fleet_db.connect(server.state_dir)
    try:
        rows = [tuple(r) for r in conn.execute("SELECT principal, user_id FROM sessions")]
    finally:
        conn.close()
    assert rows == [("legacy-admin", None)]


def test_flag_off_hides_the_form_and_refuses_the_post_without_touching_anything(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie = login(server)
    monkeypatch.setenv(FLAG, "0")
    calls = []

    def boom(*_args, **_kwargs):
        calls.append(1)
        raise AssertionError("must not be called")

    monkeypatch.setattr(app.auth, "password_ok", boom)
    for name in ("locked_out", "record_failure", "record_success", "seconds_remaining"):
        monkeypatch.setattr(app.LOGIN_THROTTLE, name, boom)

    status, _headers, body = http_request(server.url("/login"))
    assert status == 200
    assert b'type="password"' not in body

    for _ in range(auth.LOGIN_FAILURE_LIMIT + 2):
        status, _headers, body = _post(server, "whatever", "203.0.113.50")
        assert status == 403
        assert b"Password sign-in is turned off" in body
        assert b'type="password"' not in body
    assert calls == []
    # The right password is refused too, and creates no session.
    assert _post(server, TEST_PASSWORD, "203.0.113.50")[0] == 403

    status, headers, _body = http_request(server.url("/account"), cookie=cookie)
    assert status == 303
    assert headers["Location"].startswith("/login")


def test_flag_off_with_a_flipped_flag_leaves_the_throttle_unlocked(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    monkeypatch.setenv(FLAG, "0")
    for _ in range(auth.LOGIN_FAILURE_LIMIT + 1):
        assert _post(server, "x", "203.0.113.51")[0] == 403
    monkeypatch.setenv(FLAG, "1")
    assert _post(server, TEST_PASSWORD, "203.0.113.51")[0] == 303


# --- throttle and audit ------------------------------------------------------

def test_throttle_locks_after_the_failure_limit_with_a_countdown(app_server_in_process):
    server = app_server_in_process
    for _ in range(auth.LOGIN_FAILURE_LIMIT):
        assert _post(server, "wrong", "203.0.113.60")[0] == 401
    status, _headers, body = _post(server, TEST_PASSWORD, "203.0.113.60")
    assert status == 429
    assert b"try again in" in body


def test_success_and_lockout_each_print_one_audit_line_and_never_the_password(
        app_server_in_process, capsys):
    server = app_server_in_process
    secret_guess = "guess-that-must-not-be-logged"
    for _ in range(auth.LOGIN_FAILURE_LIMIT + 2):
        _post(server, secret_guess, "203.0.113.61")
    assert _post(server, TEST_PASSWORD, "203.0.113.62")[0] == 303
    out = capsys.readouterr().out
    lockouts = [line for line in out.splitlines() if "legacy_login_lockout" in line]
    successes = [line for line in out.splitlines() if "legacy_login_success" in line]
    assert len(lockouts) == 1
    assert len(successes) == 1
    assert "203.0.113.61" in lockouts[0]
    assert "legacy-admin" in successes[0] and "203.0.113.62" in successes[0]
    assert secret_guess not in out
    assert TEST_PASSWORD not in out


# --- startup rules -----------------------------------------------------------

def _run_start(tmp_path, env_extra, password=TEST_PASSWORD):
    env = child_env(dict(os.environ))
    for name in [n for n in env if n.startswith("SKYPANE_COMPANION") or n.startswith(
            "SKYPANE_AUTH0") or n == FLAG]:
        del env[name]
    if password is not None:
        env[auth.PASSWORD_ENV_VAR] = password
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, companion_app_server.APP_PATH, "--port", "0",
         "--state-dir", str(tmp_path)],
        env=env, capture_output=True, text=True, timeout=30)


def test_a_flag_value_other_than_zero_or_one_refuses_to_start(tmp_path):
    result = _run_start(tmp_path, {FLAG: "yes"})
    assert result.returncode != 0
    assert FLAG in result.stderr
    assert "yes" not in result.stderr.replace(FLAG, "")


def test_flag_on_without_a_password_refuses_to_start(tmp_path):
    result = _run_start(tmp_path, {}, password=None)
    assert result.returncode != 0
    assert auth.PASSWORD_ENV_VAR in result.stderr


def test_flag_off_without_auth0_has_no_sign_in_method(tmp_path):
    result = _run_start(tmp_path, {FLAG: "0"})
    assert result.returncode != 0
    assert "no sign-in method" in result.stderr


@pytest.mark.parametrize("present", [
    ["SKYPANE_AUTH0_DOMAIN"],
    ["SKYPANE_AUTH0_DOMAIN", "SKYPANE_AUTH0_CLIENT_ID"],
])
def test_a_partial_auth0_setup_names_the_missing_variables_only(tmp_path, present):
    env = {name: AUTH0_VARS[name] for name in present}
    result = _run_start(tmp_path, env)
    assert result.returncode != 0
    missing = [n for n in AUTH0_VARS if n.startswith("SKYPANE_AUTH0") and n not in present]
    for name in missing:
        assert name in result.stderr
    for name in present:
        assert AUTH0_VARS[name] not in result.stderr


def test_flag_off_with_full_auth0_starts(tmp_path):
    server = AppServer(str(tmp_path / "state"), env_overrides=dict(AUTH0_VARS, **{FLAG: "0"}))
    try:
        server.start()
        status, _headers, body = http_request(server.url("/login"))
        assert status == 200
        assert b'type="password"' not in body
    finally:
        server.stop()


def test_flag_unset_without_auth0_starts(app_server):
    assert http_request(app_server.url("/login"))[0] == 200


# --- sessions never depend on the password ------------------------------------

def test_a_session_survives_a_restart_with_a_different_password(tmp_path):
    server = AppServer(str(tmp_path / "state"))
    try:
        server.start()
        cookie = login(server)
        assert http_request(server.url("/account"), cookie=cookie)[0] == 200
        server.stop()
        server.password = "a-different-shared-password"
        server.start()
        assert http_request(server.url("/account"), cookie=cookie)[0] == 200
        expiry = str(time.time_ns() + 3600 * 10 ** 9)
        for key in (server.password, TEST_PASSWORD):
            signature = hmac.new(key.encode(), expiry.encode(), hashlib.sha256).hexdigest()
            forged = "sp_session=%s.%s" % (expiry, signature)
            status, headers, _body = http_request(server.url("/account"), cookie=forged)
            assert status == 303
            assert headers["Location"].startswith("/login")
    finally:
        server.stop()
