"""Server-side sessions over real HTTP: the cookie is an opaque token whose
sha256 is the only thing fleet.db holds, a principal is rebuilt from the
database on every request, and a store failure answers 503.

Runs against `app_server_in_process` so the session clock and the
legacy-login flag can be changed under the live server.
"""
import hashlib
import os
import sqlite3
import urllib.parse

from companion import app, auth, static_files
from companion_app_server import TEST_PASSWORD, cookie_value, http_request, login
from server import fleet_db, fleet_sessions


def _token(cookie):
    return cookie.split("=", 1)[1]


def _hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _session_hashes(state_dir):
    conn = fleet_db.connect(state_dir)
    try:
        return {row["id_hash"] for row in conn.execute("SELECT id_hash FROM sessions")}
    finally:
        conn.close()


def _seed_user_session(state_dir, role="user", disabled=False, token="seeded-token"):
    conn = fleet_db.connect(state_dir)
    try:
        user_id = fleet_db.add_user(conn, "%s@example.com" % role, role, disabled=disabled)
        fleet_sessions.create_session(
            conn, _hash(token), user_id=user_id, principal="user", now=app._now())
    finally:
        conn.close()
    return "sp_session=%s" % token, user_id


def _post_login(server, cookie=None):
    return http_request(
        server.url("/login"), method="POST", cookie=cookie,
        data=urllib.parse.urlencode({"password": TEST_PASSWORD}).encode())


def test_cookie_is_opaque_and_only_its_hash_is_stored(app_server_in_process):
    server = app_server_in_process
    cookie = login(server)
    token = _token(cookie)
    assert token != _hash(token)
    assert _session_hashes(server.state_dir) == {_hash(token)}
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200


def test_login_rotates_the_session(app_server_in_process):
    server = app_server_in_process
    first = login(server)
    _status, headers, _body = _post_login(server, cookie=first)
    second = cookie_value(headers)
    assert second != first
    assert _session_hashes(server.state_dir) == {_hash(_token(second))}
    assert http_request(server.url("/health"), cookie=first)[0] == 303
    assert http_request(server.url("/health"), cookie=second)[0] == 200


def test_logout_deletes_the_row_and_the_old_cookie_is_refused(app_server_in_process):
    server = app_server_in_process
    cookie = login(server)
    status, _headers, _body = http_request(
        server.url("/logout"), method="POST", data=b"", cookie=cookie,
        extra_headers={"Origin": server.base_url()})
    assert status == 303
    assert _session_hashes(server.state_dir) == set()
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303


def test_turning_the_legacy_flag_off_refuses_an_existing_legacy_session(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie = login(server)
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200
    monkeypatch.setenv(auth.LEGACY_LOGIN_ENV_VAR, "0")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303


def test_a_legacy_session_refused_while_the_flag_was_off_stays_gone(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie = login(server)
    monkeypatch.setenv(auth.LEGACY_LOGIN_ENV_VAR, "0")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303
    assert _session_hashes(server.state_dir) == set()
    monkeypatch.setenv(auth.LEGACY_LOGIN_ENV_VAR, "1")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303


def test_a_malformed_legacy_flag_does_not_delete_legacy_sessions(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie = login(server)
    monkeypatch.setenv(auth.LEGACY_LOGIN_ENV_VAR, "maybe")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303
    monkeypatch.setenv(auth.LEGACY_LOGIN_ENV_VAR, "1")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200


def test_a_password_change_does_not_end_a_legacy_session(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie = login(server)
    monkeypatch.setenv(auth.PASSWORD_ENV_VAR, "a-new-shared-password")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200


def test_a_malformed_legacy_flag_fails_closed(app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie = login(server)
    monkeypatch.setenv(auth.LEGACY_LOGIN_ENV_VAR, "maybe")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303


def test_a_disabled_user_is_cut_off_on_the_next_request(app_server_in_process):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="admin")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200
    conn = fleet_db.connect(server.state_dir)
    try:
        assert fleet_db.set_user_disabled(conn, "admin@example.com", True)
    finally:
        conn.close()
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303


def test_an_admin_user_session_reaches_admin_pages(app_server_in_process):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="admin")
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200


def test_expired_and_idle_sessions_are_refused(app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie = login(server)
    start = app._now()

    monkeypatch.setattr(app, "_now", lambda: start + fleet_sessions.IDLE_TIMEOUT_S + 1)
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303

    monkeypatch.setattr(app, "_now", lambda: start)
    cookie = login(server)
    # Stay active so only the absolute limit applies.
    for day in range(1, 31):
        monkeypatch.setattr(app, "_now", lambda day=day: start + day * 86400 - 60)
        assert http_request(server.url("/health"), cookie=cookie)[0] == 200
    monkeypatch.setattr(app, "_now", lambda: start + fleet_sessions.ABSOLUTE_LIFETIME_S + 1)
    assert http_request(server.url("/health"), cookie=cookie)[0] == 303


def test_set_cookie_attributes(app_server_in_process):
    _status, headers, _body = _post_login(app_server_in_process)
    attributes = [part.strip() for part in headers["Set-Cookie"].split(";")]
    assert attributes[0].startswith("sp_session=")
    assert "HttpOnly" in attributes
    assert "SameSite=Strict" in attributes
    assert "Path=/" in attributes
    assert "Max-Age=2592000" in attributes


def test_an_unreadable_fleet_db_answers_503_on_gated_routes_only(app_server_in_process):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="admin")
    with open(fleet_db.fleet_db_path(server.state_dir), "wb") as handle:
        handle.write(b"this is not a database" * 100)
    for path in ("/health", "/"):
        status, headers, _body = http_request(server.url(path), cookie=cookie)
        assert status == 503
        assert "Location" not in headers
    status, _headers, body = http_request(server.url("/login"), cookie=cookie)
    assert status == 200
    assert b"password" in body.lower()


def test_a_static_asset_request_does_not_create_fleet_db(app_server_in_process):
    server = app_server_in_process
    route = next(iter(static_files.STATIC_ROUTES))
    assert http_request(server.url(route))[0] == 200
    assert not os.path.exists(fleet_db.fleet_db_path(server.state_dir))


def test_a_user_role_session_gets_the_unknown_path_404_on_admin_routes(app_server_in_process):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="user")
    unknown = http_request(server.url("/no-such-page"), cookie=cookie)
    for path in ("/health", "/airlines"):
        status, _headers, body = http_request(server.url(path), cookie=cookie)
        assert status == 404
        assert body == unknown[2]
    status, _headers, body = http_request(
        server.url("/poll-now"), method="POST", data=b"", cookie=cookie,
        extra_headers={"Origin": server.base_url()})
    assert status == 404
    assert body == unknown[2]
    assert b"nav-dot" not in body
    anonymous = http_request(server.url("/health"))
    assert anonymous[0] == 303


def test_a_user_session_may_use_the_signed_in_routes(app_server_in_process):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="user")
    status, headers, _body = http_request(
        server.url("/ui-theme"), method="POST", cookie=cookie,
        data=urllib.parse.urlencode({"ui_theme": "dark"}).encode(),
        extra_headers={"Origin": server.base_url()})
    assert status == 303
    assert headers["Set-Cookie"].startswith("sp_ui_theme=dark")


def test_an_unknown_token_is_refused(app_server_in_process):
    server = app_server_in_process
    assert http_request(server.url("/health"), cookie="sp_session=nope")[0] == 303


def _unwritable_state_dir(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise sqlite3.OperationalError("attempt to write a readonly database")

    monkeypatch.setattr(fleet_db, "connect", refuse)
    monkeypatch.setattr(fleet_db, "_state_dir_writable", lambda _state_dir: False)


def test_unwritable_state_dir_reads_sessions_and_logs_the_fallback(
        app_server_in_process, monkeypatch, capfd):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="admin")
    _unwritable_state_dir(monkeypatch)
    capfd.readouterr()
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200
    assert "state directory is not writable" in capfd.readouterr().out


def test_unwritable_state_dir_with_pending_wal_answers_503(
        app_server_in_process, monkeypatch, capfd):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="admin")
    _unwritable_state_dir(monkeypatch)
    with open(fleet_db.fleet_db_path(server.state_dir) + "-wal", "wb") as handle:
        handle.write(b"unmerged frames")
    capfd.readouterr()
    status, headers, _body = http_request(server.url("/health"), cookie=cookie)
    assert status == 503
    assert "Location" not in headers
    assert "fallback refused" in capfd.readouterr().out


def test_unwritable_state_dir_with_empty_wal_still_reads(
        app_server_in_process, monkeypatch):
    server = app_server_in_process
    cookie, _user_id = _seed_user_session(server.state_dir, role="admin")
    _unwritable_state_dir(monkeypatch)
    open(fleet_db.fleet_db_path(server.state_dir) + "-wal", "wb").close()
    assert http_request(server.url("/health"), cookie=cookie)[0] == 200
