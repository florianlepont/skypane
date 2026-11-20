"""The System page's tiles (Server, Data sources, Identification, Off-box backup), served by the
real app and read as markup."""
import datetime
import html
import re

import pytest

import fleet_console_support as fx
from companion import auth, health_signals, prefs
from companion.test_view_pages_helpers import seed_runway_events
from server import history_db

PATH = "/fleet?view=system"


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


def _seed(server, tmp_path, monkeypatch, disagree=True, backup=True):
    fx.seed_fleet(server.state_dir)
    now = datetime.datetime.now(datetime.timezone.utc)
    events = [dict(
        ts=(now - datetime.timedelta(minutes=10 + 20 * i)).isoformat(), hex="39%04x" % i,
        callsign="AFR%03d" % i, aircraft_type="A320", confirmed_state="confirmed",
        corroborated=False if (disagree and i % 5 == 0) else True, route_source="adsb",
        airline="Air France", origin="LFPO", destination="LFPG") for i in range(20)]
    seed_runway_events(server.state_dir, events)
    with history_db.open_db(server.state_dir) as conn:
        history_db.set_meta(
            conn, history_db.META_LAST_PIPELINE_RUN,
            (now - datetime.timedelta(seconds=40)).isoformat())
    if backup:
        stamp = (now - datetime.timedelta(hours=2)).strftime("%Y%m%dT%H%M%SZ")
        marker = tmp_path / "marker"
        marker.write_text("skypane-state-%s.tar.gz" % stamp)
        monkeypatch.setenv(health_signals.OFFBOX_MARKER_ENV_VAR, str(marker))
    else:
        monkeypatch.delenv(health_signals.OFFBOX_MARKER_ENV_VAR, raising=False)
    return fx.admin_cookie(server.state_dir)


def _page(server, cookie, lang="en"):
    status, _h, body = fx.get(server, cookie + "; %s=%s" % (auth.UI_LANG_COOKIE_NAME, lang), PATH)
    assert status == 200
    return body if isinstance(body, str) else body.decode("utf-8")


def _tiles(page):
    section = re.search(r'<ul class="fleet-tiles fleet-tiles--system">.*?</ul>', page, re.S).group(0)
    found = []
    for tile in re.findall(r'<a class="fleet-tile".*?</a>', section, re.S):
        def part(name):
            m = re.search(r'<span class="fleet-tile__%s">(.*?)</span>(?=<)' % name, tile, re.S)
            return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else ""
        found.append((part("label"), part("value"), part("meta"),
                      re.search(r'href="([^"]+)"', tile).group(1),
                      re.search(r'data-state="(\w+)"', tile).group(1)))
    return found


def test_four_tiles_state_their_topic_and_link_to_its_block(app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch))
    tiles = _tiles(page)
    assert [t[0] for t in tiles] == ["Server", "Data sources", "Identification", "Off-box backup"]
    assert [t[3] for t in tiles] == [
        "#system-topic-flight-data", "#system-topic-sources", "#system-topic-identification",
        "#system-topic-backup"]
    server_tile, sources, _ident, backup = tiles
    assert server_tile[1] == "Running on schedule" and server_tile[2].startswith("Last run")
    assert sources[1] == "Sources disagreed recently" and sources[4] == "warn"
    assert sources[2] == "4 disagreements"
    assert backup[1] == "Up to date" and backup[4] == "ok"
    for _label, _value, _meta, href, _state in tiles:
        assert 'id="%s"' % href[1:] in page
    # The state is a visually hidden word, not colour alone.
    assert "Needs attention" in re.search(
        r'<a class="fleet-tile" data-state="warn".*?</a>', page, re.S).group(0)


def test_the_backup_tile_is_left_out_with_its_block_when_no_marker_is_configured(
        app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch, disagree=False, backup=False))
    assert [t[0] for t in _tiles(page)] == ["Server", "Data sources", "Identification"]
    assert 'id="system-topic-backup"' not in page
    assert _tiles(page)[1][1] == "Sources agree"


def test_the_page_has_no_unresolved_airlines_link_and_a_subtitle(
        app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch))
    assert "Unresolved airlines" not in page
    assert "The server behind every frame. Visible to administrators." in page


def test_french_labels(app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch), "fr")
    assert [t[0] for t in _tiles(page)] == [
        "Serveur", "Sources de données", "Identification", "Sauvegarde hors serveur"]
    assert "Détails" in page and "Le serveur derrière chaque cadre." in page


def _cards(page):
    found = {}
    for key in ("flight-data", "sources", "identification", "backup"):
        m = re.search(r'<div class="sys-card" data-state="(\w+)" id="system-card-%s">(.*?)</div></li>'
                      % key, page, re.S)
        if m:
            found[key] = (m.group(1), html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", m.group(2)))))
    return found


def test_section_labels_are_visible_and_each_card_has_a_header_and_right_aligned_rows(
        app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch))
    for label in ("Flight data", "Data sources", "Identification", "Off-box backup"):
        assert re.search(r'<h2 class="section-label" id="system-\w[\w-]*">%s</h2>' % label, page)
    cards = _cards(page)
    assert set(cards) == {"flight-data", "sources", "identification", "backup"}
    assert "Last run" in cards["flight-data"][1] and "Last detection" in cards["flight-data"][1]
    assert "Last off-box backup" in cards["backup"][1]
    assert page.count('class="sys-card__head"') == 4
    assert page.count('<dl class="sys-card__facts">') == 2


def test_sources_outcomes_are_three_rows_with_one_short_sentence(
        app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch))
    outcomes = re.search(r'<ul class="sys-card__outcomes">(.*?)</ul>', page, re.S).group(1)
    assert outcomes.count("<li>") == 3
    assert "Only one of the two sources returned an aircraft this cycle." in outcomes
    assert "The two sources picked different aircraft." in outcomes
    assert "4 disagreements" in _cards(page)["sources"][1]


def test_identification_header_window_and_flat_table(app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch))
    text = _cards(page)["identification"][1].replace("\xa0", " ")
    assert "of flights identified" in text and "Last 30 days: 20 flights" in text
    assert "Description" in text and "Route found just now" in text and "Other cases" in text
    assert "<table" in page and "data-table" not in re.search(
        r'id="system-card-identification">.*?</table>', page, re.S).group(0)
    assert "Unresolved airlines" not in page


def test_warnings_banner_is_a_card_with_pills_and_the_sentence(
        app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch))
    banner = re.search(r'<div class="sys-banner health-anomaly".*?</div>', page, re.S).group(0)
    assert re.search(r"\d warnings?:", banner)
    assert "sys-banner__pill" in banner
    assert "Something needs attention" in banner


def test_french_cards_use_the_french_sentences(app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch), "fr")
    cards = _cards(page)
    assert "Dernière détection" in cards["flight-data"][1]
    assert "Une seule des deux sources a renvoyé un avion à ce cycle." in cards["sources"][1]
    assert "des vols identifiés" in cards["identification"][1]
    assert "derniers jours" in cards["identification"][1]


def test_french_verdicts_use_the_shared_wording(app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch), "fr")
    assert _tiles(page)[1][1] == "Les sources ont divergé récemment"
    assert "Les sources ont divergé récemment" in _cards(page)["sources"][1]
    banner = re.search(r'<div class="sys-banner health-anomaly".*?</div>', page, re.S).group(0)
    assert ">Les sources ont divergé récemment<" in banner
    assert "Quelque chose demande votre attention — vérifiez les lignes ci-dessous." in banner
    assert "contredites" not in page


def test_topic_glyphs_on_tiles_and_cards(app_server_in_process, tmp_path, monkeypatch):
    server = app_server_in_process
    page = _page(server, _seed(server, tmp_path, monkeypatch))
    section = re.search(r'<ul class="fleet-tiles fleet-tiles--system">.*?</ul>', page, re.S).group(0)
    for glyph in ("icon-server", "icon-radio", "icon-cloud-upload"):
        assert 'href="#%s"' % glyph in section
        assert 'id="%s"' % glyph in page
    for key, glyph in (("flight-data", "icon-server"), ("sources", "icon-radio"),
                       ("backup", "icon-cloud-upload")):
        card = re.search(r'id="system-card-%s">(.*?)</div></li>' % key, page, re.S).group(1)
        assert 'href="#%s"' % glyph in card
