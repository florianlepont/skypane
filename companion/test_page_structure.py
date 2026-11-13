"""What assistive technology and the browser's history read before anything
else, over real HTTP: the first heading of a page is its h1, the sign-in page
has a main landmark, no heading repeats its parent's text, and the tab or
history title tells one page from another."""
import re

import pytest

import fleet_console_support as fx
from companion_app_server import InProcessAppServer, http_request

VIEW_ROUTES = (
    "/display", "/display/arrivals", "/display/special-looks", "/display/special-looks/new",
    "/display/special-looks/edit?rule_kind=prefix&rule_key=AFR", "/display/calendar",
    "/display/calendar/connect", "/display/calendar-look")


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookie = fx.user_cookie(state_dir, email=fx.OWNER_EMAIL)
    frame = "/devices/%s" % seed.owned_id
    yield server, cookie, frame
    server.stop()


def _page(server, cookie, path, lang="en"):
    status, _headers, raw = http_request(
        server.url(path), cookie=cookie, extra_headers={"Accept-Language": lang})
    assert status == 200, path
    return raw.decode("utf-8")


def _headings(markup):
    body = re.sub(r"<(script|style|svg)\b.*?</\1>", "", markup, flags=re.S)
    return [
        (int(level), re.sub(r"<[^>]+>", "", text).strip())
        for level, text in re.findall(r"<h([1-6])\b[^>]*>(.*?)</h\1>", body, flags=re.S)]


def _title(markup):
    return re.search(r"<title>(.*?)</title>", markup, flags=re.S).group(1)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_home_opens_with_its_h1_before_any_other_heading(rig, lang):
    server, cookie, frame = rig
    levels = [level for level, _ in _headings(_page(server, cookie, frame + "/", lang))]
    assert levels[0] == 1, levels


def test_the_sign_in_page_has_a_main_landmark(app_server_in_process):
    status, _headers, raw = http_request(app_server_in_process.url("/login"))
    assert status == 200
    assert len(re.findall(r"<main\b", raw.decode("utf-8"))) == 1


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_no_heading_repeats_the_text_of_another_on_the_style_pages(rig, lang):
    server, cookie, frame = rig
    for route in VIEW_ROUTES:
        texts = [text for _level, text in _headings(_page(server, cookie, frame + route, lang))]
        repeated = sorted({text for text in texts if texts.count(text) > 1})
        assert not repeated, (route, repeated)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_every_style_page_has_a_title_of_its_own_that_names_the_frame(rig, lang):
    server, cookie, frame = rig
    titles = {route: _title(_page(server, cookie, frame + route, lang)) for route in VIEW_ROUTES}
    assert len(set(titles.values())) == len(VIEW_ROUTES), titles
    for title in titles.values():
        assert "Kitchen" in title and title.endswith("SkyPane")


def test_the_special_looks_title_reads_page_then_section_then_frame(rig):
    server, cookie, frame = rig
    title = _title(_page(server, cookie, frame + "/display/special-looks"))
    assert title == "Special looks - Style - Kitchen - SkyPane"


def test_the_rename_page_title_names_the_frame(rig):
    server, cookie, frame = rig
    title = _title(_page(server, cookie, frame + "/frame/name"))
    assert "Kitchen" in title and title.startswith("Rename frame")
