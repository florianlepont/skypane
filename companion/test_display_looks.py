"""Behaviour tests for the Display page's look card: the colour x style
reading of the theme registry, the served no-script tables, the look
sheet's model, the full-frame preview route and its cache, and real
HTTP save round trips for every look.

Everything is asserted on rendered or served output, or on the public
functions that produce it - never on source text.
"""
import io
import json
import os
import urllib.parse

import pytest
from PIL import Image

from companion import i18n, prefs, theme_preview
from companion.pages import config_page
from companion.settings import look
from companion_app_server import get, http_request, login
from companion_markup import parse_html
from server import device_config
from server.plane import colour_rules


_DISPLAY_CTX = {
    "device_config": {"theme": "band_red_field", "tracked_runway": "3"},
    "colour_rules": {kind: {} for kind in colour_rules.RULE_KINDS},
    "poll_cooldown_remaining": 0,
}


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def cookie(server):
    return login(server)


def _render(lang="en", ctx=None):
    prefs.set_request_prefs(lang=lang)
    try:
        return config_page.render(ctx or _DISPLAY_CTX, scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")


def _model(rendered):
    sheet = parse_html(rendered).select_one("div.look-sheet")
    return json.loads(sheet.attrs["data-look-model"])


# --- The registry read as three choices --------------------------------------

def test_every_registered_theme_is_exactly_one_cell_of_the_three_choices():
    """the 18 registry themes map onto distinct (colour, background, stripe) cells, plain paper
    under every colour, and resolve() maps each cell back to the same id"""
    cells = {}
    for theme_id in device_config.THEME_IDS:
        axes = look.theme_axes(theme_id)
        assert axes not in cells, (theme_id, cells.get(axes))
        cells[axes] = theme_id
        colour, background, stripe = axes
        for any_colour in ([colour] if colour else look.COLOURS):
            assert look.resolve(any_colour, background, stripe) == theme_id
    assert len(cells) == len(device_config.THEME_IDS) == 18


def test_combinations_with_no_theme_are_gaps_with_the_right_reason():
    """a stripe on a full background, a soft stripe on a soft background and any yellow stripe
    are gaps with their own reason, the remaining missing cells say the frame has no theme yet,
    and no real theme cell ever carries a reason"""
    for colour in look.COLOURS:
        for background in look.BACKGROUNDS:
            for stripe in look.STRIPES:
                reason = look.gap_reason(colour, background, stripe)
                theme_id = look.resolve(colour, background, stripe)
                assert (reason is None) == (theme_id is not None)
                if background == look.BACKGROUND_FULL and stripe != look.STRIPE_NONE:
                    assert reason == look.REASON_STRIPE_ON_FULL
                elif background == look.BACKGROUND_SOFT and stripe == look.STRIPE_SOFT:
                    assert reason == look.REASON_SOFT_ON_SOFT
                elif colour == look.COLOUR_YELLOW and stripe != look.STRIPE_NONE:
                    assert reason == look.REASON_YELLOW_STRIPE
    assert look.gap_reason("green", "paper", "solid") == look.REASON_NO_THEME
    assert look.gap_reason("black", "paper", "soft") == look.REASON_NO_THEME


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_sheet_model_names_every_cell_and_every_gap_in_the_page_language(lang):
    """the served look sheet's data model lists every real theme cell with its id, every other
    combination with a translated reason, every theme's read-back and its three choices"""
    model = _model(_render(lang))
    total = len(look.COLOURS) * len(look.BACKGROUNDS) * len(look.STRIPES)
    assert len(model["cells"]) + len(model["reasons"]) == total
    assert set(model["cells"].values()) == set(device_config.THEME_IDS)
    assert set(model["axes"]) == set(device_config.THEME_IDS) == set(model["sentences"])
    prefs.set_request_prefs(lang=lang)
    try:
        expected = i18n.t(look.REASON_MESSAGES[look.REASON_YELLOW_STRIPE])
        assert model["reasons"]["yellow|paper|solid"] == expected
        assert model["sentences"]["band_red_field"] == look.look_sentence("band_red_field")
    finally:
        prefs.set_request_prefs(lang="en")
    if lang == "fr":
        assert model["sentences"]["band_red_field"] == "Rouge, bande sur fond clair"


# --- Served markup -------------------------------------------------------------

@pytest.mark.parametrize("field", ["theme", "theme_arriving", "calendar_theme_id"])
def test_served_page_offers_every_theme_through_native_radios_without_scripts(server, cookie, field):
    """the served Display page offers all 18 theme ids for each look as native radios that post
    through the settings form, inside a <details> a scripts-blocked browser can open, with the
    saved look checked"""
    status, _headers, body = get(server, "/display", cookie=cookie)
    assert status == 200
    root = parse_html(body.decode("utf-8"))
    radios = [
        node for node in root.find_all("input")
        if node.attrs.get("name") == field and node.attrs.get("value")]
    assert sorted(node.attrs["value"] for node in radios) == sorted(device_config.THEME_IDS)
    for node in radios:
        assert node.attrs.get("form") == config_page.SETTINGS_FORM_ID
        ancestor = node.parent
        while ancestor is not None and ancestor.tag != "details":
            ancestor = ancestor.parent
        assert ancestor is not None and "look-edit" in ancestor.attrs.get("class", "")


def test_the_look_card_carries_no_style_attribute_and_no_inline_script(server, cookie):
    """the look card (pictures, tables, sheet, special looks) carries no style attribute and no
    inline script: colours are SVG presentation attributes only"""
    _status, _headers, body = get(server, "/display", cookie=cookie)
    root = parse_html(body.decode("utf-8"))
    card = root.select_one("div.look-card")
    for node in [card] + card.find_all():
        assert "style" not in node.attrs, node
        assert node.tag != "script"
        assert not any(name.startswith("on") for name in node.attrs), node


def test_the_sheet_is_a_hidden_labelled_dialog_with_script_only_controls():
    """the look sheet ships hidden, as a modal dialog labelled by its own title, and none of its
    controls belongs to a form or posts anything; its "same as departures" control is a switch
    button, never a checkbox"""
    root = parse_html(_render())
    sheet = root.select_one("div.look-sheet")
    assert "hidden" in sheet.attrs
    assert sheet.attrs["role"] == "dialog" and sheet.attrs["aria-modal"] == "true"
    assert root.select_one("#" + sheet.attrs["aria-labelledby"])
    for node in sheet.find_all("input"):
        assert "form" not in node.attrs
        assert node.attrs["name"].startswith("look_")
    same = sheet.select_one("button.switch")
    assert same.attrs["role"] == "switch" and same.attrs["aria-checked"] == "false"
    stripes = [node for node in sheet.find_all("input") if node.attrs.get("data-look-axis") == "stripe"]
    assert [node.attrs["value"] for node in stripes] == list(look.STRIPES)
    why = sheet.select_one("p.look-axis__why")
    assert why.attrs.get("aria-live") == "polite"


@pytest.mark.parametrize("lang, words", [
    ("en", ("How your frame looks", "Special looks", "Plain paper", "Stripe on soft",
            "Add a special look", "Change")),
    ("fr", ("L’allure de votre cadre", "Allures spéciales", "Papier uni",
            "Bande sur fond clair", "Ajouter une allure spéciale", "Modifier")),
])
def test_the_look_card_speaks_the_page_language(lang, words):
    """every visible look-card word renders in the page language"""
    rendered = _render(lang)
    text = parse_html(rendered).select_one("div.look-card").text()
    for word in words:
        assert word in text, (lang, word)


def test_each_picture_shows_its_saved_look_in_its_own_state():
    """the departures picture shows the saved departures look departing; the arrivals picture
    shows the departures look arriving while arrivals follow departures, and its own override
    once set; each picture's read-back names the look"""
    root = parse_html(_render())
    images = root.find_all("img", cls="look-frame__image")
    assert [img.attrs["src"] for img in images] == [
        theme_preview.frame_preview_src("band_red_field", "departing", "large"),
        theme_preview.frame_preview_src("band_red_field", "arriving", "large"),
    ]
    sentences = [node.text() for node in root.find_all("span", cls="look-frame__sentence")]
    assert sentences == ["Red, stripe on soft", "Same as departures"]
    ctx = dict(_DISPLAY_CTX, device_config=dict(
        _DISPLAY_CTX["device_config"], theme_arriving="band_blue_field"))
    root = parse_html(_render(ctx=ctx))
    images = root.find_all("img", cls="look-frame__image")
    assert images[1].attrs["src"] == theme_preview.frame_preview_src(
        "band_blue_field", "arriving", "large")
    assert root.find_all("span", cls="look-frame__sentence")[1].text() == "Blue, stripe on soft"


# --- Saving every look -----------------------------------------------------------

@pytest.mark.parametrize("theme_id", device_config.THEME_IDS)
def test_each_theme_saves_through_the_existing_form_post(make_app_server, theme_id):
    """posting any registry theme for departures, arrivals and calendar flights through the
    unchanged settings route persists all three, and the served page then checks it in all
    three tables"""
    server = make_app_server()
    session = login(server)
    form = {
        "scope": config_page.SCOPE_DISPLAY, "return_to": "/display",
        "theme": theme_id, "theme_arriving": theme_id, "calendar_theme_id": theme_id,
        "tracked_runway": "3", "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    status, headers, _ = http_request(
        server.base_url() + config_page.SETTINGS_ROUTE, method="POST", cookie=session,
        data=urllib.parse.urlencode(form).encode())
    assert status == 303 and "flash=saved" in headers.get("Location", ""), headers
    saved = device_config.load_device_config(server.state_dir)
    assert (saved["theme"], saved["theme_arriving"], saved["calendar_theme_id"]) == (
        theme_id, theme_id, theme_id)
    _s, _h, body = get(server, "/display", cookie=session)
    root = parse_html(body.decode("utf-8"))
    for field in ("theme", "theme_arriving", "calendar_theme_id"):
        checked = [
            node.attrs["value"] for node in root.find_all("input")
            if node.attrs.get("name") == field and "checked" in node.attrs]
        assert checked == [theme_id], (field, checked)


def test_same_as_departures_and_an_unknown_id_keep_their_existing_meaning(make_app_server):
    """the empty value still clears the arrivals and calendar overrides, and a theme id outside
    the registry is still refused by the server, writing nothing"""
    server = make_app_server()
    session = login(server)
    base = {"scope": config_page.SCOPE_DISPLAY, "return_to": "/display", "theme": "red",
            "tracked_runway": "3", "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}

    def post(extra):
        data = urllib.parse.urlencode(dict(base, **extra)).encode()
        return http_request(
            server.base_url() + config_page.SETTINGS_ROUTE, method="POST", cookie=session, data=data)

    post({"theme_arriving": "blue", "calendar_theme_id": "yellow"})
    post({"theme_arriving": "", "calendar_theme_id": ""})
    saved = device_config.load_device_config(server.state_dir)
    assert saved["theme_arriving"] is None and not saved["calendar_theme_id"]
    status, _headers, body = post({"theme": "red_stripe_on_full"})
    assert status == 200 and b"field-error" in body
    assert device_config.load_device_config(server.state_dir)["theme"] == "red"


def test_a_special_look_posts_through_the_rules_route_with_its_theme(make_app_server):
    """the "New special look" form posts the unchanged rule_kind/rule_key/rule_theme_id fields
    to the rules route; its extra script-only choices are ignored, and the saved rule shows in
    the list with its look read back"""
    server = make_app_server()
    session = login(server)
    form = {
        "rule_kind": colour_rules.RULE_KIND_PREFIX, "rule_key": "vlg",
        "rule_theme_id": "band_blue_light",
        "rule_look_colour": "blue", "rule_look_background": "paper", "rule_look_stripe": "soft",
    }
    status, headers, _ = http_request(
        server.base_url() + config_page.RULES_ADD_ROUTE, method="POST", cookie=session,
        data=urllib.parse.urlencode(form).encode())
    assert status == 303 and "flash=rule_added" in headers.get("Location", ""), headers
    rows = colour_rules.rule_rows(colour_rules.load_colour_rules(server.state_dir))
    assert [row[:3] for row in rows] == [(colour_rules.RULE_KIND_PREFIX, "VLG", "band_blue_light")]
    _s, _h, body = get(server, "/display", cookie=session)
    row = parse_html(body.decode("utf-8")).select_one("li.rule-row")
    assert "VLG" in row.text() and "Blue, soft stripe" in row.text()


# --- The full-frame preview route ------------------------------------------------

@pytest.mark.parametrize("state", theme_preview.FRAME_PREVIEW_STATES)
@pytest.mark.parametrize("size", theme_preview.FRAME_PREVIEW_SIZES)
def test_frame_preview_serves_a_whole_canvas_png_per_state_and_size(server, cookie, state, size):
    """GET /frame-preview/{theme}.png?state=&size= serves a PNG of the whole 3:4 canvas at the
    size's real pixel dimensions, privately cacheable"""
    status, headers, body = get(
        server, theme_preview.frame_preview_src("band_red_field", state, size), cookie=cookie)
    assert status == 200 and headers.get("Content-Type") == "image/png"
    assert "private" in headers.get("Cache-Control", "")
    image = Image.open(io.BytesIO(body))
    assert image.size == theme_preview.FRAME_PREVIEW_PIXEL_SIZES[size]


@pytest.mark.parametrize("path", [
    "/frame-preview/midnight.png",
    "/frame-preview/white.png?state=empty",
    "/frame-preview/white.png?size=huge",
    "/frame-preview/..%2Fwhite.png",
])
def test_frame_preview_refuses_anything_outside_its_allow_lists(server, cookie, path):
    """an unknown theme id, state or size is a 404, never a guess or a path built from it"""
    status, _headers, _body = get(server, path, cookie=cookie)
    assert status == 404


def test_frame_preview_needs_a_session(server):
    """the preview route answers an anonymous request with the login redirect"""
    status, headers, _body = get(server, "/frame-preview/white.png")
    assert status == 303 and "/login" in headers.get("Location", "")


def test_frame_preview_cache_writes_once_and_reuses_the_file(tmp_path, monkeypatch):
    """a cold variant renders once and is written under the state directory; the next read is a
    disk hit that renders nothing; each state and size has its own file"""
    calls = []
    real = theme_preview.frame_preview_png_bytes

    def counting(theme_id, state, size):
        calls.append((theme_id, state, size))
        return real(theme_id, state, size)

    monkeypatch.setattr(theme_preview, "frame_preview_png_bytes", counting)
    state_dir = str(tmp_path)
    first = theme_preview.cached_frame_preview_bytes(state_dir, "grey", "arriving", "small")
    second = theme_preview.cached_frame_preview_bytes(state_dir, "grey", "arriving", "small")
    assert first == second and calls == [("grey", "arriving", "small")]
    theme_preview.cached_frame_preview_bytes(state_dir, "grey", "departing", "small")
    directory = os.path.join(state_dir, theme_preview.FRAME_PREVIEW_CACHE_DIRNAME)
    assert len([name for name in os.listdir(directory) if name.endswith(".png")]) == 2
    assert theme_preview.cached_frame_preview_bytes(state_dir, "nope", "arriving", "small") is None
    assert theme_preview.cached_frame_preview_bytes(state_dir, "grey", "empty", "small") is None
