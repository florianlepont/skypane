"""The Health Frame connection row says a frame has not checked in once: in the verdict, not
again in the value cell or in a Last check-in fact."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion_app_server  # noqa: E402
import companion_markup  # noqa: E402
from companion import auth  # noqa: E402
from server import history_db  # noqa: E402

_NOW = "2026-09-21T12:00:00+00:00"
_NO_CHECK_IN = {"en": "No check-in yet", "fr": "Aucune connexion pour l’instant"}
_LAST_CHECK_IN = {"en": "Last check-in", "fr": "Dernière connexion"}


def _seed_with_check_in(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(conn, _NOW, battery_mv=4000)


def _seed_without_check_in(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    with history_db.open_db(state_dir):
        pass


def _connection_row(make_app_server, seed, lang):
    server = make_app_server(seed=seed)
    cookie = "%s; %s=%s" % (
        companion_app_server.login(server), auth.UI_LANG_COOKIE_NAME, lang)
    code, _, body = companion_app_server.get(server, "/fleet", cookie=cookie)
    assert code == 200
    root = companion_markup.parse_html(body.decode("utf-8"))
    row = root.select_one("#health-row-connection")
    assert row is not None
    return row


def test_no_check_in_is_said_once_in_the_verdict(make_app_server):
    row = _connection_row(make_app_server, _seed_without_check_in, "en")
    assert row.select_one(".health-row__verdict").text().strip() == (
        "Has not checked in for a while")
    assert row.select_one(".health-row__value").text().strip() == ""
    assert _NO_CHECK_IN["en"] not in row.text()
    assert _LAST_CHECK_IN["en"] not in row.text()


def test_no_check_in_row_in_french_has_no_repeat(make_app_server):
    row = _connection_row(make_app_server, _seed_without_check_in, "fr")
    assert row.select_one(".health-row__verdict").text().strip()
    assert row.select_one(".health-row__value").text().strip() == ""
    assert _NO_CHECK_IN["fr"] not in row.text()
    assert _LAST_CHECK_IN["fr"] not in row.text()


def test_a_frame_with_a_check_in_keeps_value_and_facts(make_app_server):
    row = _connection_row(make_app_server, _seed_with_check_in, "en")
    assert row.select_one(".health-row__value").text().strip() != ""
    assert _LAST_CHECK_IN["en"] in row.text()
    assert _NO_CHECK_IN["en"] not in row.text()
