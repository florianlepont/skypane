"""A sign-in cancelled at the identity provider ends on the sign-in page at an
address of its own, so a reload or Back shows the same calm message instead of
the error a consumed attempt would give."""
import urllib.parse

import companion_markup
from companion_app_server import http_request, http_request_full, login_via_auth0, named_cookie

CANCELLED = ("Sign-in was cancelled", "Press Sign in whenever you are ready.")


def _toast(body):
    doc = companion_markup.parse_html(body.decode("utf-8"))
    nodes = doc.select(".toast--docked")
    return companion_markup.toast_title_detail(nodes[0]) if nodes else None


def _cancel(rig, next_route=None):
    rig.invite("user@example.test", "user")
    rig.fake.set_knob("redirect_error", "access_denied")
    return login_via_auth0(rig.server, rig.fake, next_route=next_route)


def test_a_cancelled_callback_redirects_to_the_sign_in_page(auth0_rig):
    result = _cancel(auth0_rig)
    assert result.status == 303
    assert result.headers["Location"] == "/login?error=cancelled"
    assert result.session_cookie is None
    assert named_cookie(result.headers, "sp_oidc") == "sp_oidc="
    assert auth0_rig.session_count() == 0


def test_the_cancelled_message_survives_a_reload(auth0_rig):
    result = _cancel(auth0_rig)
    url = auth0_rig.server.url(result.headers["Location"])
    for _ in range(3):
        status, _headers, body = http_request(url)
        assert status == 200
        assert _toast(body) == CANCELLED


def test_the_cancelled_page_is_in_the_readers_language(auth0_rig):
    result = _cancel(auth0_rig)
    _status, _headers, body = http_request(
        auth0_rig.server.url(result.headers["Location"]),
        extra_headers={"Accept-Language": "fr"})
    assert _toast(body)[0] != CANCELLED[0]
    assert _toast(body)[0] == "La connexion a été annulée"


def test_the_destination_the_person_wanted_is_kept(auth0_rig):
    result = _cancel(auth0_rig, next_route="/account")
    location = result.headers["Location"]
    assert urllib.parse.parse_qs(urllib.parse.urlsplit(location).query) == {
        "error": ["cancelled"], "next": ["/account"]}
    _status, _headers, body = http_request(auth0_rig.server.url(location))
    assert 'next=%2Faccount' in body.decode("utf-8") or "next=/account" in body.decode("utf-8")


def test_an_unknown_error_code_on_the_sign_in_page_says_nothing(auth0_rig):
    for code in ("whatever", "<script>alert(1)</script>", ""):
        status, _headers, body = http_request(
            auth0_rig.server.url("/login?error=" + urllib.parse.quote(code)))
        assert status == 200
        assert _toast(body) is None
        assert b"alert(1)" not in body


def test_the_callback_opened_without_an_attempt_is_still_refused(auth0_rig):
    status = http_request_full(auth0_rig.server.url("/callback?error=access_denied"))[0]
    assert status == 400
