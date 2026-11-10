"""The Personalisation tab's Layout card and the pairing picker, over a real
in-process server: the frame-level Layout card above the style tabs (once on
every view, not a navigation link, the old address redirecting), the five layout cards with their saved and selected
state, saving a layout through the settings form (CSRF unchanged), the
rejected-value path, the five pairing cards a frame on a giant layout is
offered in place of the eighteen-theme picker, the classic frame's picker
staying as it was, a stored theme that is not a pairing read as the pairing
it maps to without being rewritten, and the help text, in English and
French.
"""
import os

import pytest

from access_matrix_support import (
    ADMIN_EMAIL, OTHER_EMAIL, OWNER_EMAIL, seed_matrix_fleet)
from companion import device_scope, theme_preview
from companion.settings import look
from companion_app_server import (
    InProcessAppServer, http_request, session_cookie_for_state_dir, with_csrf)
from companion_markup import parse_html
from server import device_config, pairings, screen_layouts

PAIRING_IDS = ("grey", "blue_light", "red_light", "yellow_light", "white")
LAYOUT_CARD_NAMES = {
    "en": ["Classic", "A: nose and tail", "B: whole aircraft",
           "C: lettering on top, aircraft at the bottom", "A with diagonal band"],
    "fr": ["Classique", "A : nez et queue", "B : avion entier",
           "C : lettres en haut, avion en bas", "A avec bande diagonale"],
}


class Rig:
    def __init__(self, server, fleet, cookies, state_dirs):
        self.server = server
        self.fleet = fleet
        self.cookies = cookies
        self.state_dirs = state_dirs

    def owner_dir(self):
        return self.state_dirs[self.fleet.owner_device]

    def scope(self):
        return "/devices/%s" % self.fleet.owner_device

    def get(self, who, path, lang=None):
        headers = {"Accept-Language": lang} if lang else None
        status, _response, body = http_request(
            self.server.url(self.scope() + path), cookie=self.cookies[who],
            extra_headers=headers)
        return status, body.decode("utf-8", "replace")

    def post(self, who, form, path="/settings"):
        data = with_csrf(self.cookies[who], form)
        status, response, body = http_request(
            self.server.url(self.scope() + path), method="POST", data=data,
            cookie=self.cookies[who], extra_headers={"Origin": self.server.base_url()})
        return status, response, body.decode("utf-8", "replace")

    def save(self, who="owner", return_to="/display", **fields):
        form = {"scope": "display", "return_to": return_to}
        form.update(fields)
        return self.post(who, form)

    def stored(self):
        return device_config.load_device_config(self.owner_dir())

    def stored_file(self):
        path = device_config.device_config_path(self.owner_dir())
        with open(path, "rb") as handle:
            return handle.read()

    def page(self, path, who="owner", lang=None):
        status, body = self.get(who, path, lang=lang)
        assert status == 200
        return parse_html(body)


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
    }
    for state in state_dirs.values():
        os.makedirs(state, exist_ok=True)
    yield Rig(server, fleet, cookies, state_dirs)
    server.stop()


def _layout_radios(root):
    return root.select('#personalisation-layout input[type="radio"][name="layout"]')


def _checked(root, name):
    return [r.attrs["value"] for r in root.select('input[name="%s"][checked]' % name)]


# --- The Layout card --------------------------------------------------------

CARD_VIEWS = ("/display", "/display/arrivals", "/display/special-looks", "/display/calendar")


def _card_checks(root):
    """The card is present once, sits before the navigation, and holds the five radios."""
    assert len(root.select("section#personalisation-layout")) == 1
    assert len(root.select("[data-layout-card]")) == 1
    page = root.select_one("div.personalisation")
    children = [c for c in page.children if getattr(c, "tag", None)]
    assert children[0].attrs["id"] == "personalisation-layout"
    assert children[1].tag == "nav"


@pytest.mark.parametrize("who", ["owner", "admin"])
@pytest.mark.parametrize("path", CARD_VIEWS)
def test_the_layout_card_offers_the_five_layouts_with_a_preview_each(rig, who, path):
    root = rig.page(path, who)
    _card_checks(root)
    section = root.select_one("#personalisation-layout")
    assert section.attrs["data-dirty-section"] == "Layout"
    radios = _layout_radios(root)
    assert [r.attrs["value"] for r in radios] == list(screen_layouts.LAYOUT_IDS)
    assert all(r.attrs["form"] == "settings-form" for r in radios)
    assert len(_checked(root, "layout")) == 1
    cards = root.select("#personalisation-layout label")
    assert [c.select_one(".look-pick__name").text() for c in cards] == LAYOUT_CARD_NAMES["en"]
    for card, layout_id in zip(cards, screen_layouts.LAYOUT_IDS):
        image = card.select_one("img")
        assert theme_preview.FRAME_PREVIEW_ROUTE_PREFIX in image.attrs["src"]
        assert "layout=%s" % layout_id in image.attrs["src"]
        assert image.attrs["alt"]
    assert root.select_one("#personalisation-layout h2").text() == "Layout"
    assert root.select_one("#personalisation-layout .layout-card__caption").text() == (
        "Applies to the whole frame.")


@pytest.mark.parametrize("path", CARD_VIEWS)
def test_the_navigation_has_four_links_and_none_is_layout(rig, path):
    root = rig.page(path)
    nav_links = root.select("nav.personalisation-nav a")
    assert [a.attrs["href"].split("/devices/")[-1].split("/", 1)[-1] for a in nav_links] == [
        "display", "display/arrivals", "display/special-looks", "display/calendar"]
    assert [a.attrs.get("aria-current") for a in nav_links].count("page") == 1
    assert not [a for a in root.select("a") if a.attrs.get("href", "").endswith("/display/layout")]
    assert "Layout" not in [a.text().strip() for a in nav_links]


def test_the_retired_layout_address_redirects_to_the_display_page(rig):
    status, response, _body = http_request(
        rig.server.url(rig.scope() + "/display/layout"), cookie=rig.cookies["owner"])
    assert status in (301, 302, 303, 307, 308)
    assert response["Location"] == rig.scope() + "/display"


def test_an_absent_layout_shows_the_default_selected_and_says_when_it_repaints(rig):
    assert "layout" not in rig.stored() or rig.stored()["layout"] == screen_layouts.DEFAULT_LAYOUT_ID
    root = rig.page("/display")
    assert _checked(root, "layout") == [screen_layouts.DEFAULT_LAYOUT_ID]
    help_text = root.select_one("#personalisation-layout .layout-card__picker > .section-caption").text()
    assert "next flight or transition" in help_text


def test_the_summary_row_names_the_saved_layout(rig):
    rig.save(layout="c")
    root = rig.page("/display/calendar")
    assert root.select_one("#personalisation-layout [data-layout-name]").text() == (
        LAYOUT_CARD_NAMES["en"][3])
    thumb = root.select_one("#personalisation-layout [data-layout-thumb]")
    assert "layout=c" in thumb.attrs["src"]
    toggle = root.select_one("#personalisation-layout [data-layout-toggle]")
    assert "hidden" in toggle.attrs
    assert toggle.attrs["aria-controls"] == "personalisation-layout-picker"


@pytest.mark.parametrize("path", CARD_VIEWS)
def test_the_layout_card_speaks_french(rig, path):
    root = rig.page(path, lang="fr")
    assert root.select_one("nav.personalisation-nav").attrs["aria-label"] == (
        "Sections de style")
    names = [c.select_one(".look-pick__name").text() for c in root.select("#personalisation-layout label")]
    assert names == [name.replace("\u00a0", " ") for name in LAYOUT_CARD_NAMES["fr"]]
    assert "prochain vol ou à la transition" in (
        root.select_one("#personalisation-layout .layout-card__picker > .section-caption").text())
    assert root.select_one("#personalisation-layout h2").text() == "Disposition"
    assert root.select_one("#personalisation-layout .layout-card__caption").text() == (
        "S’applique à tout le cadre.")
    assert "Tout le cadre" in root.select_one("#personalisation-layout .layout-card__meta").text()
    assert root.select_one("#personalisation-layout [data-layout-toggle]").text() == "Modifier"


def test_saving_a_layout_persists_it_and_every_view_shows_it_selected(rig):
    status, response, _body = rig.save(layout="a_diagonal", return_to="/display/calendar")
    assert status == 303
    assert response["Location"].startswith(rig.scope() + "/display/calendar")
    assert rig.stored()["layout"] == "a_diagonal"
    for path in CARD_VIEWS:
        root = rig.page(path)
        assert _checked(root, "layout") == ["a_diagonal"]
        saved = root.select("#personalisation-layout label.runway-card--selected input")
        assert [r.attrs["value"] for r in saved] == ["a_diagonal"]


def test_saving_classic_is_kept_and_the_default_is_not_written(rig):
    rig.save(layout="classic")
    assert rig.stored()["layout"] == "classic"
    rig.save(layout=screen_layouts.DEFAULT_LAYOUT_ID)
    assert rig.stored()["layout"] == screen_layouts.DEFAULT_LAYOUT_ID
    assert b'"layout"' not in rig.stored_file()


def test_a_bogus_layout_is_refused_redrawn_with_the_card_and_not_echoed(rig):
    rig.save(layout="a")
    before = rig.stored_file()
    status, _response, body = rig.save(layout="bogus<script>")
    assert status == 200
    assert "bogus" not in body
    root = parse_html(body)
    _card_checks(root)
    assert [c.attrs["id"] for c in root.select("div.personalisation__view > section")] == [
        "personalisation-look"]
    assert root.select_one("#personalisation-layout .field-error") is not None
    assert _checked(root, "layout") == ["a"]
    assert rig.stored_file() == before


def test_a_layout_post_from_another_origin_is_not_saved(rig):
    data = with_csrf(rig.cookies["owner"], {"scope": "display", "layout": "a"})
    http_request(
        rig.server.url(rig.scope() + "/settings"), method="POST", data=data,
        cookie=rig.cookies["owner"], extra_headers={"Origin": "https://evil.example"})
    assert rig.stored().get("layout") != "a"


def test_another_user_cannot_save_a_layout_on_this_frame(rig):
    status, _response, _body = rig.save(who="other", layout="a")
    assert status in (403, 404)
    assert rig.stored().get("layout") != "a"


def test_saving_the_layout_changes_no_other_setting(rig):
    device_config.save_device_config(
        rig.owner_dir(), theme="band_red_field", theme_arriving="black", wake_interval_s=900)
    before = rig.stored()
    rig.save(layout="c")
    after = rig.stored()
    assert after.pop("layout") == "c"
    before.pop("layout", None)
    assert after == before


# --- The pairing picker for the new layouts --------------------------------

@pytest.mark.parametrize("layout_id", ["a", "b", "c", "a_diagonal"])
def test_a_giant_layout_offers_five_pairing_cards_instead_of_the_theme_picker(rig, layout_id):
    device_config.save_device_config(rig.owner_dir(), layout=layout_id, theme="grey")
    root = rig.page("/display")
    radios = root.select('input[type="radio"][name="theme"]')
    assert [r.attrs["value"] for r in radios] == list(PAIRING_IDS)
    assert all(r.attrs["form"] == "settings-form" for r in radios)
    assert not root.select("[data-look-sheet]")
    assert not root.select("table.look-table")
    for card in root.select("#personalisation-look label.look-pick__card"):
        src = card.select_one("img").attrs["src"]
        assert "layout=%s" % layout_id in src
    assert _checked(root, "theme") == ["grey"]


def test_the_pairing_cards_are_named_in_english_and_french(rig):
    device_config.save_device_config(rig.owner_dir(), layout="b")
    names = {
        "en": ["Grey", "Light blue", "Light red", "Light yellow", "White"],
        "fr": ["Gris", "Bleu clair", "Rouge clair", "Jaune clair", "Blanc"],
    }
    for lang, expected in names.items():
        root = rig.page("/display", lang=lang)
        assert [c.select_one(".look-pick__name").text()
                for c in root.select("#personalisation-look label.look-pick__card")] == expected


def test_the_arrivals_view_offers_the_pairings_with_a_nudge_until_one_is_picked(rig):
    device_config.save_device_config(rig.owner_dir(), layout="b", theme="red_light")
    root = rig.page("/display/arrivals")
    radios = root.select('input[type="radio"][name="theme_arriving"]')
    assert [r.attrs["value"] for r in radios] == ["", *PAIRING_IDS]
    assert _checked(root, "theme_arriving") == [""]
    assert not root.select('input[name="theme"]')
    nudge = root.select_one(".look-pairings > .section-caption").text()
    assert "Pick an arrivals colour" in nudge
    status, _response, _body = rig.save(return_to="/display/arrivals", theme_arriving="blue_light")
    assert status == 303
    assert rig.stored()["theme_arriving"] == "blue_light"
    root = rig.page("/display/arrivals")
    assert _checked(root, "theme_arriving") == ["blue_light"]
    for card in root.select("#personalisation-look label.look-pick__card"):
        assert "state=arriving" in card.select_one("img").attrs["src"]


def test_the_arrivals_nudge_is_french_too(rig):
    device_config.save_device_config(rig.owner_dir(), layout="b")
    root = rig.page("/display/arrivals", lang="fr")
    assert "Choisissez une couleur d’arrivée" in (
        root.select_one(".look-pairings > .section-caption").text())


def test_picking_a_pairing_stores_exactly_its_theme_id(rig):
    device_config.save_device_config(rig.owner_dir(), layout="c")
    for pairing_id in PAIRING_IDS:
        status, _response, _body = rig.save(return_to="/display", theme=pairing_id)
        assert status == 303
        assert rig.stored()["theme"] == pairing_id
        assert _checked(rig.page("/display"), "theme") == [pairing_id]


@pytest.mark.parametrize("stored_theme", ["band_green_light", "green", "black", "band_black"])
def test_a_stored_theme_that_is_no_pairing_shows_its_pairing_and_is_not_rewritten(rig, stored_theme):
    device_config.save_device_config(rig.owner_dir(), layout="b", theme=stored_theme)
    before = rig.stored_file()
    root = rig.page("/display")
    expected = pairings.pairing_for_theme(stored_theme).id
    assert _checked(root, "theme") == [expected]
    assert rig.stored()["theme"] == stored_theme
    assert rig.stored_file() == before


def test_a_stored_theme_changes_only_when_a_different_card_is_saved(rig):
    device_config.save_device_config(rig.owner_dir(), layout="b", theme="band_green_light")
    rig.save(return_to="/display", theme="red_light")
    assert rig.stored()["theme"] == "red_light"


def test_a_rejected_theme_redraws_the_pairing_cards_without_losing_the_layout(rig):
    device_config.save_device_config(rig.owner_dir(), layout="b", theme="grey")
    status, _response, body = rig.save(return_to="/display", theme="not-a-theme")
    assert status == 200
    root = parse_html(body)
    assert [r.attrs["value"] for r in root.select('input[name="theme"]')] == list(PAIRING_IDS)
    assert rig.stored()["theme"] == "grey"


def test_a_classic_frame_keeps_the_eighteen_theme_picker(rig):
    device_config.save_device_config(rig.owner_dir(), layout="classic", theme="band_red_field")
    root = rig.page("/display")
    radios = root.select('#personalisation-look input[type="radio"][name="theme"]')
    assert sorted(r.attrs["value"] for r in radios) == sorted(device_config.THEME_IDS)
    assert root.select("[data-look-sheet]")
    assert _checked(root, "theme") == ["band_red_field"]
    assert not root.select(".look-pairings")


def test_the_special_looks_and_calendar_pickers_still_offer_every_theme(rig):
    device_config.save_device_config(rig.owner_dir(), layout="b")
    root = rig.page("/display/calendar-look")
    radios = [r for r in root.select('input[name="calendar_theme_id"]') if r.attrs.get("value")]
    assert sorted(r.attrs["value"] for r in radios) == sorted(device_config.THEME_IDS)


# --- Units ------------------------------------------------------------------

def test_offered_pairing_ids_follow_the_pairing_registry_order():
    assert look.offered_pairing_ids() == PAIRING_IDS
    assert tuple(pairings.PAIRINGS) == PAIRING_IDS
