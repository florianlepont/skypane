"""GET /airlines is the read-only Airline collection for an administrator, an
owner and a co-manager alike: progress, badges, filters, cards and a sheet per
card, with no way to edit anything. Real in-process requests, no browser."""
import os
import re
from datetime import datetime, timedelta, timezone

import pytest

import fleet_console_support as fx
from companion import airline_display, auth, device_scope
from companion_app_server import InProcessAppServer, http_request
from server import fleet_db, history_db
from server.plane import illustrations

CO_EMAIL = "co-manager@example.test"
CURATED = [name for name, _shapes in illustrations.target_variants_by_airline()]
RARE_NAME, OCCASIONAL_NAME, REGULAR_NAME = CURATED[0], CURATED[1], CURATED[2]


def _ts(days_ago, offset=0):
    stamp = datetime.now(timezone.utc) - timedelta(days=days_ago, seconds=offset)
    return stamp.isoformat()


class Rig:
    def __init__(self, server, seed, cookies):
        self.server, self.seed, self.cookies = server, seed, cookies
        devices = {d.id: d for d in device_scope.load_devices(server.state_dir)}
        self.owned_dir = devices[seed.owned_id].state_dir
        os.makedirs(self.owned_dir, exist_ok=True)
        self.n = 0

    def event(self, airline, days_ago, **fields):
        self.n += 1
        fields.setdefault("hex", "b%05d" % self.n)
        fields.setdefault("callsign", "TST%04d" % self.n)
        fields.setdefault("confirmed_state", "departing")
        with history_db.open_db(self.owned_dir) as conn:
            history_db.record_runway_event(
                conn, ts=_ts(days_ago, self.n * 120), airline=airline, **fields)

    def seed_history(self):
        self.event(RARE_NAME, 30, aircraft_type="A320")
        for age in (40, 20, 10):
            self.event(OCCASIONAL_NAME, age, aircraft_type="B738")
        for index in range(12):
            self.event(REGULAR_NAME, 60 + index, aircraft_type="A21N")
        self.event("Zed Charter Wings", 2)
        self.event(None, 1)

    def get(self, who, query="", lang="en"):
        cookie = "%s; %s=%s" % (self.cookies[who], auth.UI_LANG_COOKIE_NAME, lang)
        path = "/devices/%s/airlines%s" % (self.seed.owned_id, query)
        status, headers, body = http_request(self.server.url(path), cookie=cookie)
        return status, headers, body.decode("utf-8", "replace")

    def page(self, who="owner", query="", lang="en"):
        status, _headers, body = self.get(who, query, lang)
        assert status == 200
        return body


@pytest.fixture
def rig(tmp_path):
    state_dir = str(tmp_path / "state")
    server = InProcessAppServer(state_dir)
    seed = fx.seed_fleet(state_dir)
    cookies = {
        "owner": fx.user_cookie(state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(state_dir, email=CO_EMAIL),
        "admin": fx.admin_cookie(state_dir),
    }
    conn = fleet_db.connect(state_dir)
    try:
        co_id = fleet_db.get_user_by_email(conn, CO_EMAIL)["id"]
        fleet_db.add_co_manager(conn, seed.owned_id, co_id, None)
    finally:
        conn.close()
    yield Rig(server, seed, cookies)
    server.stop()


def _main(page):
    """The page's own content, without the shell's language, theme and
    sign-out forms."""
    return re.search(r"<main\b.*?</main>", page, flags=re.S).group(0)


def _cards(body):
    return re.findall(r'<li class="collection-item"[^>]*>.*?</li>', body, flags=re.S)


def _card_for(body, name):
    return next(card for card in _cards(body) if ">%s<" % name in card)


def _text(markup):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", markup)).strip()


@pytest.mark.parametrize("who", ("owner", "co", "admin"))
def test_every_role_gets_the_same_read_only_collection(rig, who):
    rig.seed_history()
    page = rig.page(who)
    body = _main(page)
    assert re.search(r"<h1[^>]*>Airlines</h1>", body)
    assert "Every airline your frame has spotted." not in body
    assert "1 more for the 5 badge" in body
    # The seeded charter is outside the curated list: it is listed, so it counts in the total.
    assert 'aria-label="4 of %d airlines spotted"' % (len(CURATED) + 1) in body
    assert '<progress class="collection-progress__bar" value="4"' in body
    assert body.count('class="collection-badges"') == 1
    assert ">1/5<" in body
    assert 'title="Earned: First sighting; Locked: spot 5 airlines;' in body
    assert 'class="visually-hidden">Collection badges: 1/5. Earned: First sighting. Locked: spot 5 airlines.' in body
    assert 'type="file"' not in body
    assert "<form" in body
    for form in re.findall(r"<form\b[^>]*>", body):
        assert 'method="get"' in form
    assert not re.search(r"(?:action|href)=\"[^\"]*/airlines/", body)
    for control in ("rename", "resolve", "delete", "replace"):
        assert control not in body.lower().replace("unresolved", "")


def test_the_three_roles_see_the_same_cards(rig):
    rig.seed_history()
    cards = {who: _cards(rig.page(who)) for who in ("owner", "co", "admin")}
    assert cards["owner"] == cards["co"] == cards["admin"]


def test_counts_rarity_and_new_come_from_the_seeded_history(rig):
    rig.seed_history()
    body = rig.page()
    rare = _text(_card_for(body, RARE_NAME))
    occasional = _text(_card_for(body, OCCASIONAL_NAME))
    regular = _text(_card_for(body, REGULAR_NAME))
    assert "Seen once" in rare and "Rare" in rare and "New" not in rare
    assert "Seen 3 times" in occasional and "Occasional" in occasional
    assert "Seen 12 times" in regular and "Regular" in regular
    zed = _text(_card_for(body, "Zed Charter Wings"))
    assert "Seen once" in zed and "Rare" in zed and "New" in zed


def test_a_flight_stored_twice_is_seen_once(rig):
    for offset in (0, 30):
        with history_db.open_db(rig.owned_dir) as conn:
            history_db.record_runway_event(
                conn, ts=_ts(3, offset), hex="abc123", callsign="AFR1",
                airline=RARE_NAME, confirmed_state="arriving")
    assert "Seen once" in _text(_card_for(rig.page(), RARE_NAME))


def test_unseen_cards_are_dimmed_and_say_not_seen_yet(rig):
    rig.seed_history()
    body = rig.page()
    unseen = [card for card in _cards(body) if "collection-card--unseen" in card]
    assert len(unseen) == len(CURATED) - 3
    for card in unseen:
        text = _text(card)
        assert text in {airline_display.shown_name(name) for name in CURATED}, text
        assert "Not seen yet" not in text and "Seen once" not in text
        assert "Rare" not in text and "times" not in text


def test_the_empty_history_shows_the_start_state_and_only_unseen_cards(rig):
    body = rig.page()
    assert "Your collection starts with the first plane" in body
    assert "Airlines show up here as your frame sees them." in body
    assert "0 of %d airlines spotted" % len(CURATED) in body
    assert len(_cards(body)) == len(CURATED)
    assert all("collection-card--unseen" in card for card in _cards(body))
    assert ">0/5<" in body


def test_a_sheet_per_card_is_read_only_and_reached_by_a_hash_link(rig):
    rig.seed_history()
    body = rig.page()
    sheets = re.findall(r'<dialog class="modal collection-sheet".*?</dialog>', body, flags=re.S)
    assert len(sheets) == len(CURATED) + 1
    for card in _cards(body):
        target = re.search(r'href="#(dlg-airline-[a-z0-9-]+)" class="[^"]*" data-modal-open', card)
        assert target and 'id="%s"' % target.group(1) in body
    for sheet in sheets:
        assert "<form" not in sheet and "<input" not in sheet and "<button" not in sheet
        assert "/airlines/" not in sheet
    regular = next(s for s in sheets if "dlg-airline-%s" % illustrations.normalise_airline_key(
        REGULAR_NAME) in s)
    text = _text(regular)
    for fact in ("Times seen 12", "First seen", "Last seen", "Aircraft types seen",
                 "Rarity Regular", "Recent callsigns"):
        assert fact in text
    assert "Rarity depends on how often your frame has seen an airline." in text
    assert 'class="type-chip mono"' in regular


def test_rare_airlines_and_aircraft_carry_a_tier_class_and_a_word(rig):
    rig.seed_history()
    body = rig.page()
    assert "collection-card--rare" in _card_for(body, RARE_NAME)
    assert "collection-card__rarity--rare" in _card_for(body, RARE_NAME)
    assert "Seen once \u00b7 " in _text(_card_for(body, RARE_NAME))
    assert "collection-card--occasional" in _card_for(body, OCCASIONAL_NAME)
    assert "collection-card--regular" in _card_for(body, REGULAR_NAME)
    legend = _text(re.search(r'<ul class="rarity-legend".*?</ul>', body, flags=re.S).group(0))
    for word in ("Regular", "Occasional", "Rare", "10 or more sightings", "3 to 9 sightings",
                 "Fewer than 3 sightings"):
        assert word in legend
    sheets = re.findall(r'<dialog class="modal collection-sheet".*?</dialog>', body, flags=re.S)
    types = " ".join(re.findall(r'<span class="type-chip type-chip--[a-z]+">.*?</span>(?: </span>)?', "".join(sheets)))
    assert re.search(r'type-chip--rare">A320 <span class="type-chip__tag">Rare</span>', types)
    assert re.search(r'type-chip--occasional">737-800 <span class="type-chip__tag">Occasional</span>', types)
    assert re.search(r'type-chip--regular">A321neo</span>', types)


def test_the_legend_sits_behind_one_info_button_in_the_bar(rig):
    rig.seed_history()
    body = _main(rig.page())
    form = re.search(r'<form class="filter-bar collection-controls".*?</form>', body, flags=re.S).group(0)
    menu = re.search(r'<details class="row-menu collection-legend">.*?</details>', form, flags=re.S)
    assert menu and 'aria-label="Rarity of airlines and aircraft"' in menu.group(0)
    assert menu.group(0).count('<ul class="rarity-legend"') == 1
    assert body.count('class="rarity-legend"') == 1
    assert "Airlines: %d" % (len(CURATED) + 1) in form
    assert 'class="visually-hidden" role="status" data-filter-count' in form


def test_the_sheet_lays_short_facts_two_per_row_and_long_ones_across(rig):
    rig.seed_history()
    sheet = re.search(r'<dialog class="modal collection-sheet".*?</dialog>', rig.page(), flags=re.S).group(0)
    assert sheet.count('<div class="collection-facts__wide">') == 2
    assert sheet.index("Times seen") < sheet.index("Rarity") < sheet.index("First seen")


def test_the_bar_is_one_form_with_sort_and_count_and_a_no_script_apply(rig):
    rig.seed_history()
    body = _main(rig.page())
    form = re.search(r'<form class="filter-bar collection-controls".*?</form>', body, flags=re.S).group(0)
    assert form.count("<form") == 1
    for part in ('name="q"', 'name="show"', 'collection-controls__apply', 'data-filter-count'):
        assert part in form
    # The sort is a menu of radio rows (a no-script Apply sends the choice), not a select.
    assert "<select" not in form
    sort = re.search(r'<details class="row-menu collection-sort">.*?</details>', form, flags=re.S).group(0)
    assert re.findall(r'<input type="radio"[^>]*name="sort" value="(\w+)"', sort) == [
        "most", "rarest", "latest", "az"]
    assert sort.count(" checked") == 1 and 'value="most" checked' in sort
    assert 'aria-label="Sort by: Most seen"' in sort
    # Line one holds the field, the sort and the legend; the segments come after them.
    assert form.index('name="q"') < form.index("collection-sort") < form.index(
        "collection-legend") < form.index("filter-bar__chips")
    assert "Airlines: %d" % (len(CURATED) + 1) in form
    assert "Airlines: 1<" in _main(rig.page(query="?q=zed"))
    fr = _main(rig.page(lang="fr", query="?q=zed"))
    assert "Compagnies\u00a0: 1<" in fr and "Moins de 3 passages" in fr


def test_filter_chips_sort_and_text_are_applied_by_the_server(rig):
    rig.seed_history()
    spotted = _cards(rig.page(query="?show=spotted"))
    assert len(spotted) == 4
    assert len(_cards(rig.page(query="?show=unseen"))) == len(CURATED) - 3
    most = [_text(card) for card in _cards(rig.page(query="?show=spotted&sort=most"))]
    assert "Seen 12 times" in most[0] and "Seen 3 times" in most[1]
    az = _cards(rig.page(query="?show=spotted&sort=az"))
    names = [re.search(r'collection-card__name">([^<]*)<', c).group(1) for c in az]
    assert names == sorted(names, key=str.casefold)
    rarest = [_text(card) for card in _cards(rig.page(query="?sort=rarest"))]
    assert "Seen once" in rarest[0] and "Seen 12 times" in rarest[3]
    assert "Seen" not in rarest[-1]
    latest = _cards(rig.page(query="?show=spotted&sort=latest"))
    assert "Zed Charter Wings" in latest[0]
    only = _cards(rig.page(query="?q=zed"))
    assert len(only) == 1 and "Zed Charter Wings" in only[0]


def test_unknown_values_fall_back_and_text_is_capped_and_escaped(rig):
    rig.seed_history()
    body = rig.page(query="?show=bogus&sort=bogus")
    assert len(_cards(body)) == len(CURATED) + 1
    hostile = rig.page(query="?q=%22%3E%3Cscript%3Ealert(1)%3C/script%3E")
    assert "<script>alert(1)</script>" not in hostile
    assert "No matching airlines" in hostile
    long_text = rig.page(query="?q=" + "a" * 500)
    assert 'value="%s"' % ("a" * 60) in long_text and "a" * 61 not in long_text


def test_hostile_stored_text_is_escaped(rig):
    rig.event("<img src=x onerror=alert(1)>", 1, callsign="<b>CS</b>", aircraft_type="<i>t</i>")
    body = rig.page()
    assert "<img src=x onerror=alert(1)>" not in body
    assert "&lt;img src=x onerror=alert(1)&gt;" in body
    assert "<b>CS</b>" not in body and "<i>t</i>" not in body
    assert 'id="dlg-airline-img-src-x-onerror-alert-1"' in body


def test_the_page_is_french_with_french_strings(rig):
    rig.seed_history()
    body = rig.page(lang="fr")
    for text in (">Compagnies</h1>", "encore 1 pour le badge 5",
                 "4 compagnies repérées sur %d" % (len(CURATED) + 1), "Vue 12 fois", "Vue une fois",
                 "Habituelle", "Occasionnelle", "Nouveau",
                 "Première observation", "Appliquer", "Les plus vues", "Pas encore vues"):
        assert text in body
    assert "Seen once" not in body and "Not seen yet" not in body


@pytest.mark.parametrize("who", ("owner", "co"))
def test_resolve_is_ignored_for_everyone_but_an_administrator(rig, who):
    status, _headers, body = rig.get(who, "?resolve=XYZ")
    assert status == 200 and "<h1" in body and "Airlines" in body


def test_an_administrator_resolve_link_goes_to_the_editor(rig):
    status, headers, _body = rig.get("admin", "?resolve=XYZ")
    assert status == 303
    assert headers["Location"] == "/devices/%s/airlines/manage?resolve=XYZ" % rig.seed.owned_id


def test_an_owner_cannot_post_to_the_editing_routes(rig):
    cookie = rig.cookies["owner"]
    from companion_app_server import with_csrf
    status, _h, _b = http_request(
        rig.server.url("/devices/%s/airlines/rename" % rig.seed.owned_id), method="POST",
        cookie=cookie, data=with_csrf(cookie, {"airline": RARE_NAME, "airline_name": "X"}),
        extra_headers={"Origin": rig.server.base_url()})
    assert status == 404


def test_the_spotted_count_is_plural_aware_in_both_languages(rig):
    rig.event(RARE_NAME, 30, aircraft_type="A320")
    one_en = _text(_main(rig.page("owner", lang="en")))
    one_fr = _text(_main(rig.page("owner", lang="fr")))
    assert "1 airlines" not in one_en
    assert "1 of %d airline spotted" % len(CURATED) in one_en
    assert "1 compagnies" not in one_fr
    assert "1 compagnie repérée sur %d" % len(CURATED) in one_fr


def test_zero_spotted_is_plural_in_english_and_singular_in_french(rig):
    empty_en = _text(_main(rig.page("owner", lang="en")))
    empty_fr = _text(_main(rig.page("owner", lang="fr")))
    assert "0 of %d airlines spotted" % len(CURATED) in empty_en
    assert "0 compagnie repérée sur %d" % len(CURATED) in empty_fr


def test_the_progress_sentence_counts_against_every_listed_airline(rig):
    """an airline outside the curated list still counts as spotted, so the progress total is
    the number of airlines the page lists (its cards), never fewer than the spotted count"""
    rig.event(RARE_NAME, 30, aircraft_type="A320")
    rig.event("Zzyzx Air Charter", 20, aircraft_type="A320")
    for lang in ("en", "fr"):
        page = _main(rig.page("owner", lang=lang))
        main = _text(page)
        sentence = re.search(
            r"(\d+) (?:of|compagnies? repérées? sur) (\d+)", main)
        assert sentence, main
        spotted, total = int(sentence.group(1)), int(sentence.group(2))
        assert spotted <= total == len(_cards(page)) == len(CURATED) + 1
