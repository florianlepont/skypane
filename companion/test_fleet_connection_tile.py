"""The frame's Connection tile on the Fleet page states the last and the next connection
itself (there is no connection detail page): a frame that never checked in says so once, in the
verdict."""
import datetime
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion_app_server  # noqa: E402
import companion_markup  # noqa: E402
from companion import auth  # noqa: E402
from server import device_config, history_db  # noqa: E402

_LAST_CHECK_IN = {"en": "Last check-in", "fr": "Dernier contact"}
_NEXT_WAKE = {"en": "Next wake", "fr": "Prochain réveil"}
_CONNECTION = {"en": "Connection", "fr": "Connexion"}


def _seed_with_check_in(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    recent = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(minutes=2)
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(
            conn, recent.isoformat(timespec="seconds"), battery_mv=4000)
    device_config.save_device_config(state_dir, wake_interval_s=600)


def _seed_without_check_in(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    with history_db.open_db(state_dir):
        pass


def _connection_tile(make_app_server, seed, lang):
    server = make_app_server(seed=seed)
    cookie = "%s; %s=%s" % (
        companion_app_server.login(server), auth.UI_LANG_COOKIE_NAME, lang)
    # The Update address leads to the frame's page; the tile there holds the connection detail.
    code, headers, _ = companion_app_server.get(server, "/update", cookie=cookie)
    assert code == 303 and headers["Location"].endswith("&view=versions")
    frame_page = headers["Location"].split("&view=")[0]
    code, _, body = companion_app_server.get(server, frame_page, cookie=cookie)
    assert code == 200
    root = companion_markup.parse_html(body.decode("utf-8"))
    for tile in root.select(".fleet-tile"):
        if tile.select_one(".fleet-tile__label").text().strip() == _CONNECTION[lang]:
            return tile
    raise AssertionError("no Connection tile")


def test_the_connection_tile_is_not_a_link_and_has_no_details_mark(make_app_server):
    tile = _connection_tile(make_app_server, _seed_with_check_in, "en")
    assert tile.tag == "div"
    assert tile.select(".fleet-tile__more") == []


def test_no_check_in_is_said_once_in_the_verdict(make_app_server):
    tile = _connection_tile(make_app_server, _seed_without_check_in, "en")
    assert tile.select_one(".fleet-tile__value").text().strip() == (
        "Has not checked in for a while")
    assert tile.select_one(".fleet-tile__meta").text().strip() == ""
    assert _LAST_CHECK_IN["en"] not in tile.text()


def test_no_check_in_tile_in_french_has_no_repeat(make_app_server):
    tile = _connection_tile(make_app_server, _seed_without_check_in, "fr")
    assert tile.select_one(".fleet-tile__value").text().strip()
    assert tile.select_one(".fleet-tile__meta").text().strip() == ""
    assert _LAST_CHECK_IN["fr"] not in tile.text()


def test_a_frame_with_a_check_in_states_the_last_and_the_next_connection(make_app_server):
    tile = _connection_tile(make_app_server, _seed_with_check_in, "en")
    lines = [line.text().strip() for line in tile.select(".fleet-tile__line")]
    assert lines[0].startswith(_LAST_CHECK_IN["en"]) and len(lines[0]) > len(_LAST_CHECK_IN["en"])
    assert lines[1].startswith(_NEXT_WAKE["en"]) and len(lines[1]) > len(_NEXT_WAKE["en"])


def test_the_connection_lines_are_in_french(make_app_server):
    tile = _connection_tile(make_app_server, _seed_with_check_in, "fr")
    lines = [line.text().strip() for line in tile.select(".fleet-tile__line")]
    assert lines[0].startswith(_LAST_CHECK_IN["fr"]) and lines[1].startswith(_NEXT_WAKE["fr"])
