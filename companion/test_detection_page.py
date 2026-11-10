"""The Detection page over a real in-process server: search and pick an
airport and runway without scripts, the validated runway POST, the route x
role x owner outcomes, the French strings and the read-only GET contract.
"""
import html
import json
import os
import re
import urllib.parse

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope
from companion import auth
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from server import device_config, fleet_db

LFPG_RUNWAYS = ("08L/26R", "08R/26L", "09L/27R", "09R/27L")


class Rig:
    def __init__(self, server, fleet, cookies, state_dirs):
        self.server = server
        self.fleet = fleet
        self.cookies = cookies
        self.state_dirs = state_dirs

    def owner_dir(self):
        return self.state_dirs[self.fleet.owner_device]

    def other_dir(self):
        return self.state_dirs[self.fleet.other_device]

    def scope(self):
        return "/devices/%s" % self.fleet.owner_device

    def get(self, who, path, lang=None):
        headers = {"Accept-Language": lang} if lang else None
        status, response, body = http_request(
            self.server.url(path), cookie=self.cookies[who], extra_headers=headers)
        return status, response, body.decode("utf-8", "replace")

    def post(self, who, path, form, lang=None, extra=None, csrf=True):
        headers = {"Origin": self.server.base_url()}
        if lang:
            headers["Accept-Language"] = lang
        headers.update(extra or {})
        cookie = self.cookies[who]
        data = with_csrf(cookie, form) if csrf else urllib.parse.urlencode(form).encode()
        status, response, body = http_request(
            self.server.url(path), method="POST", data=data,
            cookie=cookie, extra_headers=headers)
        return status, response, body.decode("utf-8", "replace")

    def config_bytes(self, state_dir):
        path = device_config.device_config_path(state_dir)
        if not os.path.exists(path):
            return None
        with open(path, "rb") as handle:
            return handle.read()

    def config(self, state_dir):
        raw = self.config_bytes(state_dir)
        return json.loads(raw) if raw else {}


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    fleet = seed_matrix_fleet(state_dir)
    state_dirs = {d.id: d.state_dir for d in device_scope.load_devices(state_dir)}
    cookies = {
        "owner": session_cookie_for_state_dir(state_dir, OWNER_EMAIL, "user"),
        "other": session_cookie_for_state_dir(state_dir, OTHER_EMAIL, "user"),
        "admin": session_cookie_for_state_dir(state_dir, ADMIN_EMAIL, "admin"),
        "anonymous": None,
    }
    for state in state_dirs.values():
        os.makedirs(state, exist_ok=True)
    yield Rig(server, fleet, cookies, state_dirs)
    server.stop()


def _visible_text(markup):
    stripped = re.sub(r"<(script|style)\b.*?</\1>", " ", markup, flags=re.S)
    return html.unescape(re.sub(r"<[^>]+>", " ", stripped))


def _flat_text(markup):
    """The visible text with every run of white space (the gaps the markup leaves between the
    airport's codes and its municipality included) reduced to one space."""
    return re.sub(r"\s+", " ", _visible_text(markup))


def _hrefs(markup):
    return [html.unescape(h) for h in re.findall(r'href="([^"]*)"', markup)]


def _cards(markup):
    """The runway radio cards (the two mode cards share the class but post `mode`)."""
    cards = re.findall(r'<label class="runway-card[^"]*"[^>]*>.*?</label>', markup, flags=re.S)
    return [card for card in cards if 'name="runway"' in card]


def airports_first_runway(icao):
    from server import airports
    return airports.find_airport(icao).runways[0].designator


def _save_lfpg(rig, runway="08L/26R"):
    device_config.save_device_config(
        rig.owner_dir(),
        detection={"mode": "runway", "airport": "LFPG", "runway": runway})


# --- summary --------------------------------------------------------------


def test_default_orly_page_values(rig):
    status, _h, page = rig.get("owner", rig.scope() + "/detection")
    assert status == 200
    text = _visible_text(page)
    assert "Paris-Orly" in text and "LFPO · ORY · Paris" in _flat_text(page)
    assert "Runway 3" in text
    assert "detection-summary" not in page and "Saved setting" not in text


@pytest.mark.parametrize("legacy,designator,tag,pill", [
    ("06-24", "06/24", "ORY · RWY 06/24", "Runway 4"),
    ("02-20", "02/20", "ORY · RWY 02/20", "Runway 2"),
])
def test_other_legacy_orly_runways_check_their_card(rig, legacy, designator, tag, pill):
    device_config.save_device_config(rig.owner_dir(), tracked_runway=legacy)
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    checked = [c for c in _cards(page) if " checked" in c]
    assert len(checked) == 1 and 'value="%s"' % designator in checked[0]
    assert pill in checked[0]


def test_catalogue_runway_is_checked_and_has_no_pill(rig):
    _save_lfpg(rig)
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    text = _visible_text(page)
    assert "Charles de Gaulle International Airport" in text and "LFPG · CDG ·" in _flat_text(page)
    checked = [c for c in _cards(page) if " checked" in c]
    assert len(checked) == 1 and 'value="08L/26R"' in checked[0]
    assert "banner__pill" not in page


def test_position_setting_without_a_location_shows_the_warning_and_the_orly_runways(rig):
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "position", "radius_km": 9})
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    assert "No usable location" in _visible_text(page)
    assert "toast--docked" in page
    # The airport list is filled by the page script from the map's catalogue.
    assert '["LFPO","ORY","Paris-Orly Airport"' in html.unescape(page)


def test_position_setting_with_a_location_fills_the_place_fields(rig):
    from companion.pages import place_page
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "position", "radius_km": 9})
    ctx = {"device_config": device_config.load_device_config(rig.owner_dir())}
    place = {"id": 1, "name": "Home", "latitude": 48.8566, "longitude": 2.3522,
             "timezone": "Europe/Paris", "shared": False}
    markup = place_page.render(ctx, place=place)
    assert 'id="place-label" name="place_label"' in markup and 'value="Home"' in markup
    assert 'value="48.8566"' in markup and 'value="9"' in markup
    assert "toast--docked" not in markup


def test_mode_card_is_a_radiogroup_with_the_saved_mode_checked(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection")
    assert 'role="radiogroup" aria-label="What the frame follows"' in page
    # A frame with no saved detection opens on My position, the first of the two modes.
    assert re.search(r'id="place-mode-area" value="position"[^>]*checked', page)
    assert not re.search(r'value="runway"[^>]*checked', page)
    assert page.index('id="place-mode-area"') < page.index('id="place-mode-runway"')
    _s, _h, other = rig.get("owner", rig.scope() + "/detection?mode=runway")
    assert re.search(r'id="place-mode-runway" value="runway"[^>]*checked', other)
    modes = other.split("place-modes")[1].split("</div>")[0]
    assert not re.search(r'value="position"[^>]*checked', modes)
    assert rig.config_bytes(rig.owner_dir()) is None
    # A saved runway setting is shown as it is saved.
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "runway", "airport": "LFPO", "runway": "07/25"})
    _s, _h, saved = rig.get("owner", rig.scope() + "/detection")
    assert re.search(r'id="place-mode-runway" value="runway"[^>]*checked', saved)


# --- search ---------------------------------------------------------------


def test_search_lists_matching_airports_as_links(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=cdg")
    assert page.count(
        'id="airport-results-count" class="text-label" role="status" aria-live="polite"') == 1
    assert rig.scope() + "/detection?airport=LFPG&q=cdg#airport-runways" in _hrefs(page)
    assert "airports found" in page or "1 airport found" in page


@pytest.mark.parametrize("term", ["orly", "ory", "LFPO", "Orly"])
def test_search_finds_orly(rig, term):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=" + term)
    assert "airport=LFPO" in "".join(_hrefs(page))


def test_search_ignores_accents(rig):
    _s, _h, plain = rig.get("owner", rig.scope() + "/detection?q=nimes")
    _s, _h, accent = rig.get(
        "owner", rig.scope() + "/detection?q=" + urllib.parse.quote("nîmes"))
    plain_links = [h for h in _hrefs(plain) if "airport=" in h]
    assert plain_links
    assert [h.split("&q=")[0] for h in plain_links] == [
        h.split("&q=")[0] for h in _hrefs(accent) if "airport=" in h]


def test_search_without_a_match_shows_the_empty_state(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=zzzz")
    text = _visible_text(page)
    assert "No airport found" in text
    assert "No airport matches “zzzz”" in text
    assert page.count('id="airport-results-count"') == 1


def test_search_singular_and_plural_counts(rig):
    _s, _h, one = rig.get("owner", rig.scope() + "/detection?q=LFPG")
    assert "1 airport found" in _visible_text(one)
    _s, _h, many = rig.get("owner", rig.scope() + "/detection?q=paris")
    assert re.search(r"\b[2-9]\d* airports found", _visible_text(many))


def test_search_lists_every_match_without_a_cap(rig):
    from server import airports
    total = airports.search_airports("a", 1000)[1]
    assert total > 20
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=a")
    links = [h for h in _hrefs(page) if "airport=" in h]
    assert len(links) == total
    assert "%d airports found" % total in _visible_text(page)


def test_search_term_is_truncated_and_escaped(rig):
    long_term = "a" * 200
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=" + long_term)
    assert 'value="%s"' % ("a" * 60) in page
    assert "a" * 61 not in page
    payload = urllib.parse.quote('<script>alert(1)</script>"x')
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=" + payload)
    assert "<script>alert(1)" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page


def test_search_never_changes_state(rig):
    before = rig.config_bytes(rig.owner_dir())
    other_before = rig.config_bytes(rig.other_dir())
    for query in ("q=cdg", "airport=LFPG", "airport=LFPG&mode=position&q=x&radius_km=9",
                  "airport=ZZZZ", "mode=runway", "q=%00%01"):
        status, _h, _p = rig.get("owner", rig.scope() + "/detection?" + query)
        assert status == 200
    assert rig.config_bytes(rig.owner_dir()) == before
    assert rig.config_bytes(rig.other_dir()) == other_before


# --- runway cards ---------------------------------------------------------


def test_runway_cards_show_real_designators_for_cdg(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=LFPG")
    cards = _cards(page)
    assert len(cards) == 4
    shown = [
        re.search(r'runway-card__number">([^<]+?)(?: <|</)', card).group(1) for card in cards]
    assert tuple(shown) == LFPG_RUNWAYS
    assert 'value="08L/26R"' in page and 'name="runway"' in page
    text = _visible_text(page)
    assert re.search(r"4,209 m\s+·\s+Asphalt", text)
    assert page.count('role="radiogroup" aria-labelledby="runway-group-heading"') == 1
    assert '<input type="hidden" name="airport" value="LFPG" form="detection-form">' in page
    assert "CDG · 08L/26R" in text
    assert not re.search(r"\brequired\b", page)


def test_runway_cards_for_a_single_runway_airport_are_preselected(rig):
    from server import airports
    single = next(a for a in airports.load_catalogue().values() if len(a.runways) == 1)
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=" + single.icao)
    cards = _cards(page)
    assert len(cards) == 1 and " checked" in cards[0]


def test_runway_cards_preselect_and_badge_the_saved_runway(rig):
    _save_lfpg(rig, "09L/27R")
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=LFPG")
    cards = _cards(page)
    checked = [c for c in cards if " checked" in c]
    assert len(checked) == 1 and 'value="09L/27R"' in checked[0]
    assert 'data-current-label="Current"' in checked[0]
    assert sum("data-current-label" in c for c in cards) == 1
    _s, _h, other = rig.get("owner", rig.scope() + "/detection?airport=LFMN")
    first = [c for c in _cards(other) if " checked" in c]
    assert len(first) == 1 and "data-current-label" not in first[0]
    assert 'value="%s"' % airports_first_runway("LFMN") in first[0]


def test_runway_cards_for_orly_carry_the_legacy_pills(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=LFPO")
    text = _visible_text(page)
    for pill in ("Runway 3", "Runway 4", "Runway 2"):
        assert pill in text
    assert "LFPO · ORY · Paris" in _flat_text(page)


@pytest.mark.parametrize("code", ["ZZZZ", "..%2Fx", "lfpg", "LFPG%20"])
def test_an_unknown_airport_in_the_url_is_ignored(rig, code):
    status, _h, page = rig.get("owner", rig.scope() + "/detection?airport=" + code)
    assert status == 200
    assert "This airport is not in the catalogue." not in _visible_text(page)
    assert sorted(re.search(r'value="([^"]+)"', c).group(1) for c in _cards(page)) == [
        "02/20", "06/24", "07/25"]


def test_an_unknown_airport_in_a_post_is_a_page_state(rig):
    _s, _h, page = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "ZZZZ", "runway": "01/19"})
    assert "This airport is not in the catalogue." in _visible_text(page)
    assert "Choose an airport." in _visible_text(page)
    assert not _cards(page)


# --- POST -----------------------------------------------------------------


def test_post_runway_stores_a_detection_object(rig):
    status, headers, _b = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "LFPG",
        "runway": "08L/26R"})
    assert status == 303
    assert headers["Location"].startswith(rig.scope() + "/detection?flash=detection_saved")
    stored = rig.config(rig.owner_dir())
    assert stored["detection"] == {"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}
    _s, _h, page = rig.get("owner", headers["Location"])
    assert "Detection saved" in _visible_text(page)
    assert rig.config_bytes(rig.other_dir()) is None


@pytest.mark.parametrize("designator,legacy", [
    ("07/25", "3"), ("06/24", "06-24"), ("02/20", "02-20")])
def test_post_runway_orly_stores_the_legacy_id_and_no_detection_key(rig, designator, legacy):
    _save_lfpg(rig)
    status, _h, _b = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "LFPO",
        "runway": designator})
    assert status == 303
    stored = rig.config(rig.owner_dir())
    assert stored["tracked_runway"] == legacy
    assert "detection" not in stored


def test_post_runway_works_for_an_admin_on_the_owners_device(rig):
    status, _h, _b = rig.post("admin", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "LFMN",
        "runway": "04L/22R"})
    assert status == 303
    assert rig.config(rig.owner_dir())["detection"]["airport"] == "LFMN"


REJECTIONS = [
    ({"action": "save_detection"}, "Choose a detection mode."),
    ({"action": "save_detection", "mode": "sideways"}, "Choose a detection mode."),
    ({"action": "save_detection", "mode": "position"}, "Choose a location."),
    ({"mode": "runway", "airport": "LFPG", "runway": "08L/26R"}, "Choose a detection mode."),
    ({"action": "save_detection", "mode": "runway"}, "Choose an airport."),
    ({"action": "save_detection", "mode": "runway", "airport": "ZZZZ", "runway": "08L/26R"},
     "Choose an airport."),
    ({"action": "save_detection", "mode": "runway", "airport": "LFPG"}, "Choose a runway."),
    ({"action": "save_detection", "mode": "runway", "airport": "LFPG", "runway": "01/19"},
     "This runway does not exist at this airport. Choose one from the list."),
    ({"action": "save_detection", "mode": "runway", "airport": "LFPG", "runway": "../x"},
     "This runway does not exist at this airport. Choose one from the list."),
]


@pytest.mark.parametrize("form,message", REJECTIONS)
def test_post_rejections_rerender_with_the_inline_error_and_write_nothing(rig, form, message):
    _save_lfpg(rig)
    before = rig.config_bytes(rig.owner_dir())
    status, _h, page = rig.post("owner", rig.scope() + "/detection", form)
    assert status == 200
    assert message in _visible_text(page)
    assert 'role="alert"' in page
    assert rig.config_bytes(rig.owner_dir()) == before


def test_post_rejection_echoes_the_submitted_airport(rig):
    _s, _h, page = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "LFPG", "runway": "01/19"})
    assert len(_cards(page)) == 4
    assert '<input type="hidden" name="airport" value="LFPG"' in page


RUNWAY_FORM = {
    "action": "save_detection", "mode": "runway", "airport": "LFPG", "runway": "08L/26R"}


def test_post_without_the_token_is_refused_and_writes_nothing(rig):
    status, _h, _b = rig.post("owner", rig.scope() + "/detection", RUNWAY_FORM, csrf=False)
    assert status == 403
    assert rig.config_bytes(rig.owner_dir()) is None


def test_post_with_another_sessions_token_is_refused_and_writes_nothing(rig):
    cookie = rig.cookies["owner"]
    foreign = with_csrf(rig.cookies["other"], RUNWAY_FORM)
    status, _h, _b = http_request(
        rig.server.url(rig.scope() + "/detection"), method="POST", data=foreign,
        cookie=cookie, extra_headers={"Origin": rig.server.base_url()})
    assert status == 403
    assert rig.config_bytes(rig.owner_dir()) is None


def test_location_form_post_without_the_token_is_refused(rig):
    status, _h, _b = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_location", "location_name": "Lyon", "latitude": "45.76",
        "longitude": "4.84", "timezone": "Europe/Paris", "location_id": ""}, csrf=False)
    assert status == 403


def test_the_save_form_carries_exactly_one_token_of_the_signed_in_session(rig):
    token = auth.csrf_token(rig.cookies["owner"].split("=", 1)[1])
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?mode=position")
    forms = [
        inner for opening, inner in re.findall(r"(<form[^>]*>)(.*?)</form>", page, re.S)
        if 'method="post"' in opening and "/detection" in opening]
    assert len(forms) == 1
    for inner in forms:
        assert re.findall(r'name="csrf_token" value="([^"]*)"', inner) == [token]


def test_post_with_a_foreign_origin_is_refused_and_writes_nothing(rig):
    status, _h, _b = rig.post(
        "owner", rig.scope() + "/detection",
        {"action": "save_detection", "mode": "runway", "airport": "LFPG", "runway": "08L/26R"},
        extra={"Origin": "https://evil.example"})
    assert status == 403
    assert rig.config_bytes(rig.owner_dir()) is None


# --- access ---------------------------------------------------------------


def test_scoped_anonymous_goes_to_sign_in(rig):
    status, headers, _p = rig.get("anonymous", rig.scope() + "/detection")
    assert status == 303 and headers["Location"].startswith("/login")
    status, headers, _p = rig.post(
        "anonymous", rig.scope() + "/detection", {"action": "save_detection"})
    assert status == 303 and headers["Location"].startswith("/login")


def test_scoped_unprefixed_form_follows_the_frame_rule(rig):
    status, headers, _body = rig.get("owner", "/detection")
    assert status == 303
    assert headers["Location"] == rig.scope() + "/detection"
    # The administrator owns no frame here, so the account page; any frame is
    # still open by its id.
    status, headers, _body = rig.get("admin", "/detection")
    assert (status, headers["Location"]) == (303, "/account")
    assert rig.get("admin", rig.scope() + "/detection")[0] == 200


def test_other_users_device_404_on_get_and_post_and_nothing_is_written(rig):
    path = rig.scope() + "/detection"
    assert rig.get("other", path)[0] == 404
    status, _h, _b = rig.post("other", path, {
        "action": "save_detection", "mode": "runway", "airport": "LFPG",
        "runway": "08L/26R"})
    assert status == 404
    assert rig.config_bytes(rig.owner_dir()) is None
    assert rig.config_bytes(rig.other_dir()) is None


@pytest.mark.parametrize("device_id", [
    "d_00000000", "d_ZZZZZZZZ", "d_0000000", "..", "d_" + "0" * 40])
def test_other_users_device_404_for_unknown_and_malformed_ids(rig, device_id):
    path = "/devices/%s/detection" % device_id
    assert rig.get("owner", path)[0] == 404
    assert rig.post("owner", path, {"action": "save_detection"})[0] == 404


def test_scoped_flows_stay_under_the_device_prefix(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=cdg")
    assert page.count('action="%s/detection"' % rig.scope()) == 3
    assert all(
        h.startswith(rig.scope() + "/detection?airport=")
        for h in _hrefs(page) if "airport=" in h)


# --- French and units -----------------------------------------------------


def test_french_page_uses_the_catalogue_strings(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?q=cdg", lang="fr")
    text = _visible_text(page)
    assert "Lieu et détection" in text
    assert "Rechercher des aéroports" in text
    assert "Rechercher un aéroport ou une adresse" in text
    assert "Aéroports français" in text
    assert "LFPO · ORY · Paris" in _flat_text(page)
    assert re.search(r"\d+ aéroports? trouvés?", text)


def test_french_runway_cards_and_errors(rig):
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?airport=LFPG", lang="fr")
    text = _visible_text(page)
    assert "Piste à suivre" in text
    assert re.search(r"4\s209 m\s+·\s+Asphalte", text)
    _s, _h, rejected = rig.post("owner", rig.scope() + "/detection", {
        "action": "save_detection", "mode": "runway", "airport": "LFPG",
        "runway": "01/19"}, lang="fr")
    assert "Cette piste n’existe pas dans cet aéroport." in _visible_text(rejected)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_no_nm_text(rig, lang):
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "position", "radius_km": 9})
    for query in ("", "?q=cdg", "?airport=LFPG", "?mode=position"):
        _s, _h, page = rig.get("owner", rig.scope() + "/detection" + query, lang=lang)
        text = _visible_text(page)
        assert not re.search(r"\bNM\b|\bnm\b|nautical", text)


# --- carried values and page-local navigation -------------------------------


def test_carried_values_render_as_defaults_with_a_visible_dirty_bar(rig):
    path = "%s/detection?mode=position&radius_km=12" % rig.scope()
    status, _h, page = rig.get("owner", path)
    assert status == 200
    assert re.search(r'name="radius_km"[^>]*value="12"', page)
    assert re.search(r'id="place-mode-area" value="position"[^>]*checked', page)
    bar = re.search(r'<div class="dirty-bar dirty-bar--inline"[^>]*>', page).group(0)
    assert 'data-dirty-carried="%s/detection"' % rig.scope() in bar
    assert " hidden" not in bar


def test_carried_values_absent_when_nothing_differs(rig):
    path = "%s/detection?mode=runway&radius_km=9" % rig.scope()
    _s, _h, page = rig.get("owner", path)
    assert "data-dirty-carried" not in page


def test_carried_values_filter_form_holds_them_as_hidden_inputs(rig):
    path = "%s/detection?mode=runway&radius_km=12" % rig.scope()
    _s, _h, page = rig.get("owner", path)
    form = re.search(r'<form method="get".*?</form>', page, re.S).group(0)
    assert '<input type="hidden" name="radius_km" value="12">' in form
    assert '<input type="hidden" name="mode" value="runway">' in form
    assert "data-detection-nav" in form


def test_airport_links_carry_the_radius(rig):
    path = "%s/detection?q=paris&mode=runway&radius_km=12" % rig.scope()
    _s, _h, page = rig.get("owner", path)
    rows = [h for h in _hrefs(page) if "airport=" in h]
    assert rows
    for href in rows:
        query = urllib.parse.parse_qs(urllib.parse.urlsplit(html.unescape(href)).query)
        assert query["radius_km"] == ["12"]
        assert query["q"] == ["paris"]


def test_invalid_carried_radius_ignored(rig):
    path = rig.scope() + "/detection?mode=position&radius_km=%3Cscript%3E"
    _s, _h, page = rig.get("owner", path)
    assert "<script>" not in page.replace('<script src', '')
    assert re.search(r'name="radius_km"[^>]*value="9"', page)
    _s, _h, page = rig.get("owner", rig.scope() + "/detection?mode=position&radius_km=abc")
    assert re.search(r'name="radius_km"[^>]*value="9"', page)


def test_carried_values_never_change_stored_files(rig):
    before = rig.config_bytes(rig.owner_dir())
    rig.get("owner", "%s/detection?mode=position&radius_km=12" % rig.scope())
    assert rig.config_bytes(rig.owner_dir()) == before


# --- co-manager ------------------------------------------------------------

CO_EMAIL = "co-manager@example.test"


def _db(rig, fn):
    conn = fleet_db.connect(rig.server.state_dir)
    try:
        return fn(conn)
    finally:
        conn.close()


def _co_rig(rig):
    """Make a user a co-manager of the owner's frame; returns the user id and
    the ids of the owner's, the co-manager's and a third party's location."""
    rig.cookies["co"] = session_cookie_for_state_dir(
        rig.server.state_dir, CO_EMAIL, "user")

    def seed(conn):
        co_id = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, rig.fleet.owner_device, co_id, None)
        return co_id, (
            fleet_db.add_location(
                conn, "Owner Town", 48.7, 2.3, "Europe/Paris", rig.fleet.owner_id),
            fleet_db.add_location(
                conn, "Co Town", 48.8, 2.4, "Europe/Paris", co_id),
            fleet_db.add_location(
                conn, "Third Town", 48.9, 2.5, "Europe/Paris", rig.fleet.other_id))
    return _db(rig, seed)


def _location_rows(rig):
    return _db(rig, lambda conn: [
        tuple(r) for r in conn.execute(
            "SELECT id, name, owner_user_id FROM locations ORDER BY id")])


@pytest.mark.parametrize("who", ["owner", "admin", "co"])
def test_no_saved_locations_ui_for_anyone(rig, who):
    _co_rig(rig)
    for lang in (None, "fr"):
        status, _h, body = rig.get(who, rig.scope() + "/detection", lang=lang)
        assert status == 200
        text = _visible_text(body)
        for gone in ("Owner Town", "Co Town", "Third Town", "Your locations", "Add a location",
                     "Vos lieux", "Ajouter un lieu", "Edit location", "managed by the frame owner"):
            assert gone not in text, (who, gone)
        for gone in ('id="location-form"', 'name="location_name"', 'name="location_id"',
                     'id="detection-location"', "location-picker"):
            assert gone not in body, (who, gone)


@pytest.mark.parametrize("edit", [False, True])
def test_a_crafted_location_post_by_a_co_manager_writes_nothing(rig, edit):
    _co_id, (owner_loc, _co_loc, _third) = _co_rig(rig)
    before = _location_rows(rig)
    form = {
        "action": "save_location", "location_name": "Evil", "latitude": "48.7",
        "longitude": "2.3", "timezone": "Europe/Paris",
        "location_id": str(owner_loc) if edit else ""}
    status, _h, body = rig.post("co", rig.scope() + "/detection", form)
    assert status == 200
    assert "Couldn" in _visible_text(body) and "Evil" not in body
    assert _location_rows(rig) == before


def test_a_co_manager_selects_an_owner_location_but_not_other_locations(rig):
    _co_id, (owner_loc, co_loc, third) = _co_rig(rig)
    path = rig.scope() + "/detection"
    status, _h, _b = rig.post("co", path, {
        "action": "save_detection", "mode": "position",
        "location_id": str(owner_loc), "radius_km": "10"})
    assert status == 303
    assert _db(rig, lambda c: fleet_db.get_device(
        c, rig.fleet.owner_device)["location_id"]) == owner_loc
    for foreign in (co_loc, third):
        status, _h, body = rig.post("co", path, {
            "action": "save_detection", "mode": "position",
            "location_id": str(foreign), "radius_km": "10"})
        assert status == 200
        assert _db(rig, lambda c: fleet_db.get_device(
            c, rig.fleet.owner_device)["location_id"]) == owner_loc


def test_a_co_manager_sees_the_current_location_name_of_the_owner(rig):
    _co_id, (owner_loc, _c, _t) = _co_rig(rig)
    _db(rig, lambda c: fleet_db.set_device_location_checked(
        c, rig.fleet.owner_device, owner_loc, rig.fleet.owner_id, False))
    device_config.save_device_config(
        rig.owner_dir(), detection={"mode": "position", "radius_km": 10})
    _s, _h, body = rig.get("co", rig.scope() + "/detection")
    assert 'name="place_label"' in body and 'value="Owner Town"' in body
