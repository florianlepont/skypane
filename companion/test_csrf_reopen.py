"""The way back from an expired form: the refusal page links to the page the
form came from (reloading would send the same stale request again), and says
so in the caller's language."""
import pytest

from companion_app_server import http_request, login

REOPEN_LABEL = {"en": "Open the page again", "fr": "Rouvrir la page"}


def _expired_page(server, path, lang="en"):
    cookie = login(server)
    return http_request(
        server.url(path), method="POST", cookie=cookie, data=b"x=1",
        extra_headers={"Origin": server.base_url(), "Accept-Language": lang})


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_an_expired_form_links_to_the_page_it_came_from(app_server_in_process, lang):
    status, _h, raw = _expired_page(app_server_in_process, "/frame/name", lang)
    body = raw.decode("utf-8")
    assert status == 403
    assert 'href="/frame/name">%s</a>' % REOPEN_LABEL[lang] in body, (
        "the page offers no way back to the form")
    assert "Reload and try again" not in body and "Rechargez-la" not in body


def test_an_expired_form_with_no_page_of_its_own_offers_only_the_way_home(
        app_server_in_process):
    status, _h, raw = _expired_page(app_server_in_process, "/ui-theme")
    body = raw.decode("utf-8")
    assert status == 403 and REOPEN_LABEL["en"] not in body
    assert 'class="error-home-button"' in body


def test_the_way_back_never_carries_the_query_of_the_refused_request(app_server_in_process):
    server = app_server_in_process
    status, _h, raw = http_request(
        server.url("/frame/name?csrf_token=abc&x=secret"), method="POST",
        cookie=login(server), data=b"x=1", extra_headers={"Origin": server.base_url()})
    assert status == 403 and b"secret" not in raw and b"csrf_token=abc" not in raw
