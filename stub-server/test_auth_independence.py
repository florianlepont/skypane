#!/usr/bin/env python3
"""Frame authentication is independent of the companion's sign-in.

A frame authenticates to the byos server with its MAC and provisioning
secret (and the bearer token that exchange returns); the companion
authenticates people with server-side sessions. These tests run both
against one state directory and prove neither credential works on the
other side, and that sign-in activity never changes what a frame sees.
"""
import json
import os
import sys
import urllib.error
import urllib.request

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from companion import auth  # noqa: E402
from companion_app_server import (  # noqa: E402
    InProcessAppServer, auth0_env, http_request, login, login_via_auth0)
from fake_auth0 import FakeAuth0  # noqa: E402
from server import fleet_db, fleet_migrate, fleet_sessions  # noqa: E402
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state  # noqa: E402

OWNER = "owner@example.test"
INVITED = "invited@example.test"


@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)


@pytest.fixture
def world(tmp_path):
    """A migrated live-like state dir, a byos server and a companion on it."""
    live = seed_live_like_state(str(tmp_path / "state"))
    assert fleet_migrate.main(
        ["--state-dir", live.state_dir, "--owner-email", OWNER]) == 0
    frame = FrameServer(live.state_dir)
    frame.start()
    companion = InProcessAppServer(live.state_dir)
    fake = FakeAuth0(
        "test-client-id", "test-client-secret-placeholder",
        companion.base_url() + "/callback",
        allowed_logout_urls=[companion.base_url() + "/login"]).start()
    companion.apply_env(auth0_env(fake, companion.base_url()))
    yield type("World", (), {
        "live": live, "frame": frame, "companion": companion, "fake": fake})
    companion.stop()
    fake.stop()
    frame.stop()


def _device_content(state_dir):
    """Everything fleet.db knows about devices, including token and secret
    hash columns, plus the registry view the byos server consumes.
    """
    conn = fleet_db.connect(state_dir)
    try:
        rows = [tuple(r) for r in conn.execute("SELECT * FROM devices ORDER BY id")]
        return rows, fleet_db.registry_view(conn), fleet_db.tokens_by_mac(conn)
    finally:
        conn.close()


def _frame_view(world):
    status, doc = world.frame.display(world.live.token)
    assert status == 200
    return status, json.dumps(doc, sort_keys=True)


def _bearer_get(url, token=None, cookie=None):
    headers = {}
    if token:
        headers["Authorization"] = "Bearer " + token
    if cookie:
        headers["Cookie"] = cookie
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code


def test_sign_in_activity_leaves_device_content_and_frame_poll_unchanged(world):
    before_content = _device_content(world.live.state_dir)
    before_view = _frame_view(world)

    conn = fleet_db.connect(world.live.state_dir)
    try:
        fleet_db.add_user(conn, INVITED, "user")
    finally:
        conn.close()
    assert login_via_auth0(
        world.companion, world.fake, sub="auth0|invited", email=INVITED).status == 200
    login(world.companion)

    conn = fleet_db.connect(world.live.state_dir)
    try:
        assert fleet_sessions.unlink_identity(conn, INVITED)
        fleet_db.set_user_disabled(conn, INVITED, True)
        user = fleet_db.get_user_by_email(conn, INVITED)
        fleet_sessions.delete_sessions_for_user(conn, user["id"])
    finally:
        conn.close()

    assert _device_content(world.live.state_dir) == before_content
    assert _frame_view(world) == before_view


def test_a_session_cookie_does_not_authenticate_a_frame_request(world):
    cookie = login(world.companion)
    session_token = cookie.split("=", 1)[1]
    display = world.frame.base_url + "/device/v1/display"

    unauthenticated = _bearer_get(display)
    assert unauthenticated == 401
    assert _bearer_get(display, cookie=cookie) == unauthenticated
    assert _bearer_get(display, token=session_token, cookie=cookie) == unauthenticated
    assert world.frame.display(session_token)[0] == unauthenticated
    assert world.frame.display(world.live.token)[0] == 200


def test_frame_authentication_works_with_auth0_unconfigured_or_stopped(world):
    assert world.frame.display(world.live.token)[0] == 200
    world.fake.stop()
    assert world.frame.display(world.live.token)[0] == 200
    world.companion.apply_env({
        "SKYPANE_AUTH0_DOMAIN": None, "SKYPANE_AUTH0_CLIENT_ID": None,
        "SKYPANE_AUTH0_CLIENT_SECRET": None})
    assert world.frame.display(world.live.token)[0] == 200
    status, body = world.frame.setup(world.live.mac, world.live.secret_hex)
    assert status == 200 and body["device_token"]


@pytest.mark.parametrize("route,method", [
    ("/", "GET"), ("/health", "GET"), ("/account", "GET"),
    ("/quick/display", "POST"), ("/settings", "POST"), ("/update/install", "POST"),
])
def test_device_credentials_do_not_authenticate_a_companion_route(
        world, route, method):
    secret_hash_in_registry = _device_content(world.live.state_dir)[1]["devices"][
        world.live.mac]["secret_sha256"]
    credentials = (world.live.token, world.live.secret_hex, secret_hash_in_registry)
    for credential in credentials:
        for cookie, bearer in (
                (auth.SESSION_COOKIE_NAME + "=" + credential, None),
                (None, credential)):
            headers = {"Origin": world.companion.base_url()}
            if bearer:
                headers["Authorization"] = "Bearer " + bearer
            status, response_headers, _body = http_request(
                world.companion.url(route), method=method,
                data=b"" if method == "POST" else None, cookie=cookie,
                extra_headers=headers)
            assert status == 303
            assert response_headers["Location"].startswith("/login")
