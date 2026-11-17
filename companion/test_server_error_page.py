"""An error no handler expected, over real HTTP: the caller gets a translated
500 page with the app's own chrome and a way back instead of a dropped
connection, the page says nothing about the error itself, the error is logged
once, and the server keeps answering."""
import html
import re

import pytest

import fleet_console_support as fx
from companion import login_page
from companion.pages import users_page
from companion_app_server import http_request
from server import fleet_db

SECRET_DETAIL = "boom-7f3a-not-for-the-page"
TITLE = {"en": "Something went wrong", "fr": "Un problème est survenu"}
PURPOSE = {
    "en": "SkyPane hit an error and could not finish this request.",
    "fr": "SkyPane a rencontré une erreur et n’a pas pu terminer cette demande."}
BACK = {"en": "Back to Home", "fr": "Retour à l’accueil"}


def _boom(*_args, **_kwargs):
    raise RuntimeError(SECRET_DETAIL)


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_users(server.state_dir)
    return server, seed, fx.admin_cookie(server.state_dir)


def _text(markup):
    stripped = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.S)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", stripped)).split())


def _tracebacks(captured):
    return captured.err.count("Traceback (most recent call last)")


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_an_unexpected_error_on_a_page_answers_a_translated_500_page(
        rig, monkeypatch, capsys, lang):
    server, _seed, cookie = rig
    monkeypatch.setattr(users_page, "render", _boom)
    status, headers, body = fx.get(server, cookie, "/users", headers={"Accept-Language": lang})
    assert status == 500
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert "no-store" in headers["Cache-Control"]
    assert "default-src" in headers["Content-Security-Policy"]
    text = _text(body)
    assert TITLE[lang] in text and PURPOSE[lang] in text
    # The app's own chrome and a way back.
    assert '<html lang="%s"' % lang in body
    assert 'href="/fleet"' in body and 'href="/account"' in body, "the navigation is missing"
    link = re.search(r'<a class="error-home-button" href="([^"]+)">([^<]+)</a>', body)
    assert link is not None and link.group(1) == "/"
    assert html.unescape(link.group(2)) == BACK[lang]
    # Nothing about the error itself reaches the page.
    for leaked in (SECRET_DETAIL, "RuntimeError", "Traceback", "users_page"):
        assert leaked not in body
    captured = capsys.readouterr()
    assert _tracebacks(captured) == 1
    assert SECRET_DETAIL in captured.err and "GET /users" in captured.err


def test_an_unexpected_error_on_a_post_answers_the_500_page_and_the_server_lives_on(
        rig, monkeypatch, capsys):
    server, _seed, cookie = rig
    monkeypatch.setattr(fleet_db, "add_user", _boom)
    status, _headers, body = fx.post(
        server, cookie, "/users/invite", {"email": "new@example.test", "role": "user"})
    assert status == 500
    assert TITLE["en"] in _text(body) and SECRET_DETAIL not in body
    captured = capsys.readouterr()
    assert _tracebacks(captured) == 1
    # The typed address and the anti-forgery token are not written to the log.
    assert "new@example.test" not in captured.err and "csrf" not in captured.err.lower()
    monkeypatch.undo()
    status, _headers, page = fx.get(server, cookie, "/users")
    assert status == 200 and "new@example.test" not in page


def test_a_visitor_without_a_session_gets_the_500_page_without_the_navigation(
        app_server_in_process, monkeypatch, capsys):
    server = app_server_in_process
    monkeypatch.setattr(login_page, "render_login_page", _boom)
    status, _headers, raw = http_request(server.url("/login"))
    body = raw.decode("utf-8")
    assert status == 500
    assert TITLE["en"] in _text(body)
    assert 'href="/users"' not in body and 'href="/fleet"' not in body
    link = re.search(r'<a class="error-home-button" href="([^"]+)">', body)
    assert link is not None and link.group(1) == "/login"
    assert SECRET_DETAIL not in body
    assert _tracebacks(capsys.readouterr()) == 1


def test_the_500_page_still_answers_when_its_own_chrome_cannot_be_built(
        rig, monkeypatch, capsys):
    """The failure may be the store itself: the page then comes without the
    signed-in chrome, never as a dropped connection."""
    server, _seed, cookie = rig
    monkeypatch.setattr(fleet_db, "connect", _boom)
    monkeypatch.setattr(fleet_db, "connect_readonly", _boom)
    status, _headers, body = fx.get(server, cookie, "/users")
    assert status in (500, 503)
    assert "<html" in body and SECRET_DETAIL not in body
    capsys.readouterr()
