"""The HTTP methods a page does not serve, over real HTTP: HEAD answers like
GET without a body (uptime checks and link previews use it); any other
method answers 405 with the app's own page and an Allow header, never the
standard library's English error page."""
import pytest

import fleet_console_support as fx
from companion_app_server import http_request


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    fx.seed_users(server.state_dir)
    return server, fx.admin_cookie(server.state_dir)


@pytest.mark.parametrize("path", ["/account", "/", "/missing-page"])
def test_head_answers_like_get_without_a_body(rig, path):
    server, cookie = rig
    got_status, got_headers, got_body = http_request(server.url(path), cookie=cookie)
    status, headers, body = http_request(server.url(path), "HEAD", cookie=cookie)
    assert status == got_status
    assert body == b""
    assert headers["Content-Type"] == got_headers["Content-Type"]
    assert headers.get("Location") == got_headers.get("Location")
    assert headers["Content-Length"] == str(len(got_body))


def test_head_of_a_page_behind_the_sign_in_does_not_leak_it(rig):
    server, _cookie = rig
    status, _headers, body = http_request(server.url("/account"), "HEAD")
    assert status in (302, 303, 401, 403)
    assert body == b""


@pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH", "OPTIONS"])
def test_other_methods_answer_405_with_the_apps_own_page(rig, method):
    server, cookie = rig
    status, headers, body = http_request(server.url("/account"), method, cookie=cookie)
    assert status == 405
    assert "GET" in headers["Allow"] and "POST" in headers["Allow"]
    text = body.decode("utf-8")
    assert "<title>Error response" not in text
    assert "Request refused" in text and 'class="error-home-button"' in text


def test_a_refused_method_is_answered_in_the_callers_language(rig):
    server, cookie = rig
    status, _headers, body = http_request(
        server.url("/account"), "DELETE", cookie=cookie,
        extra_headers={"Accept-Language": "fr"})
    assert status == 405
    assert "Requête refusée" in body.decode("utf-8")
