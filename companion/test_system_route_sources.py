"""The System view's route directory cards: the status of each directory and
the flights each one answered, read from the counters the poll cycle writes.

Covers the empty, healthy and degraded states in English and French, the
cards' place among the System topics, and that nothing read from the database
reaches the markup unescaped. The cards live on the existing System view, so
no route and no access rule is added.
"""
import datetime
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion_app_server  # noqa: E402
import companion_markup  # noqa: E402
from companion import auth  # noqa: E402
from server import history_db  # noqa: E402

TEXT = {
    "en": {
        "role_vrs": "Tried first", "answered_by": "Answered by",
        "none": "No request yet", "reachable": "Reachable", "down": "Not reachable",
        "empty_answers": "No route from a directory in the last 7 days",
        "answers": "VRS 4 · adsbdb 1", "window": "Last 7 days: 5 flights",
        "facts": ["Last answer", "Last 24 hours", "Found a route", "Failed"],
        "lookups": "Lookups %d", "percent": "%d%%",
    },
    "fr": {
        "role_vrs": "Interrogées en premier", "answered_by": "Répondu par",
        "none": "Aucune requête pour l’instant", "reachable": "Joignable", "down": "Injoignable",
        "empty_answers": "Aucune route d’un annuaire sur les 7 derniers jours",
        "answers": "VRS 4 · adsbdb 1", "window": "7 derniers jours : 5 vols",
        "facts": ["Dernière réponse", "Dernières 24 h", "Route trouvée", "En échec"],
        "lookups": "Recherches %d", "percent": "%d %%",
    },
}


def _ago(**delta):
    return (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(**delta)).isoformat(
        timespec="seconds")


def _check_in(state_dir):
    os.makedirs(state_dir, exist_ok=True)
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(conn, _ago(minutes=2), battery_mv=4000)


def _seed_empty(state_dir):
    _check_in(state_dir)


def _seed_degraded(state_dir):
    """VRS answers (18 found, 1 none, 1 failed, newest answered); adsbdb has
    failed 3 of its 10 requests and its newest one failed."""
    _check_in(state_dir)
    with history_db.open_db(state_dir) as conn:
        vrs = [("vrs", "found")] * 18 + [("vrs", "none"), ("vrs", "failed")]
        history_db.record_route_lookups(conn, _ago(hours=3), vrs)
        history_db.record_route_lookups(conn, _ago(minutes=4), [("vrs", "found")])
        history_db.record_route_lookups(
            conn, _ago(hours=5), [("adsbdb", "found")] * 4 + [("adsbdb", "none")] * 3 + [("adsbdb", "failed")] * 2)
        history_db.record_route_lookups(conn, _ago(hours=2), [("adsbdb", "failed")])
        for directory in ("vrs", "vrs", "vrs", "vrs", "adsbdb", None):
            history_db.record_runway_event(
                conn, ts=_ago(hours=1), callsign="AFR1000", route_directory=directory)
        history_db.record_runway_event(
            conn, ts=_ago(hours=1), callsign="AFR1001", route_directory="<img src=x onerror=alert(1)>")


def _system(make_app_server, seed, lang):
    server = make_app_server(seed=seed)
    cookie = "%s; %s=%s" % (companion_app_server.login(server), auth.UI_LANG_COOKIE_NAME, lang)
    code, _, body = companion_app_server.get(server, "/fleet?view=system", cookie=cookie)
    assert code == 200
    html = body.decode("utf-8")
    return companion_markup.parse_html(html), html


def _plain(text):
    """`text` with each no-break space as a plain one: the markup parser's
    `text()` collapses them."""
    return text.replace("\u00a0", " ")


def _facts(card):
    return {
        item.select_one("dt").text(): item.select_one("dd").text()
        for item in card.select(".sys-card__facts > div")}


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_directory_never_asked_says_so_and_a_failure_is_not_implied(make_app_server, lang):
    root, _html = _system(make_app_server, _seed_empty, lang)
    for directory in ("vrs", "adsbdb"):
        card = root.select_one("#system-card-route-directory-" + directory)
        assert card.attrs["data-state"] == "off"
        assert card.select_one(".sys-card__value").text() == TEXT[lang]["none"]
        assert card.select(".sys-card__facts") == []
    answers = root.select_one("#system-card-route-answers")
    assert answers.select_one(".sys-card__verdict").text() == TEXT[lang]["empty_answers"]
    assert answers.select(".route-bar") == []


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_healthy_directory_shows_its_last_answer_and_its_shares(make_app_server, lang):
    root, _html = _system(make_app_server, _seed_degraded, lang)
    text = TEXT[lang]
    card = root.select_one("#system-card-route-directory-vrs")
    assert card.attrs["data-state"] == "ok"
    assert card.select_one(".sys-card__verdict").text() == {
        "en": "VRS standing data", "fr": "Données VRS"}[lang]
    assert card.select_one(".sys-card__value").text() == text["reachable"]
    assert card.select_one(".sys-card__label").text() == text["role_vrs"]
    facts = _facts(card)
    assert list(facts) == [_plain(label) for label in text["facts"]]
    assert facts[_plain(text["facts"][1])] == text["lookups"] % 21
    assert facts[_plain(text["facts"][2])] == _plain(text["percent"] % 90)
    assert facts[_plain(text["facts"][3])] == _plain(text["percent"] % 5)
    assert facts[_plain(text["facts"][0])]


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_a_directory_whose_last_request_failed_needs_attention(make_app_server, lang):
    root, _html = _system(make_app_server, _seed_degraded, lang)
    text = TEXT[lang]
    card = root.select_one("#system-card-route-directory-adsbdb")
    assert card.attrs["data-state"] == "warn"
    assert card.select_one(".sys-card__verdict").text() == "adsbdb"
    assert card.select_one(".sys-card__value").text() == text["down"]
    facts = _facts(card)
    # Requests of the last 24 hours: 4 found, 3 none, 3 failed.
    assert facts[_plain(text["facts"][1])] == text["lookups"] % 10
    assert facts[_plain(text["facts"][2])] == _plain(text["percent"] % 40)
    assert facts[_plain(text["facts"][3])] == _plain(text["percent"] % 30)


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_flights_are_split_by_the_directory_that_answered(make_app_server, lang):
    root, _html = _system(make_app_server, _seed_degraded, lang)
    card = root.select_one("#system-card-route-answers")
    assert card.select_one(".sys-card__verdict").text() == TEXT[lang]["answers"]
    assert card.select_one(".sys-card__label").text() == TEXT[lang]["answered_by"]
    assert _plain(TEXT[lang]["window"]) in card.text()
    bar = card.select_one(".route-bar")
    assert bar.attrs["role"] == "img" and bar.attrs["aria-label"] == TEXT[lang]["answers"]
    assert [seg.attrs["style"] for seg in bar.select(".route-bar__seg")] == ["--seg: 4", "--seg: 1"]


def test_the_topics_follow_identification_and_precede_the_backup(make_app_server):
    root, _html = _system(make_app_server, _seed_degraded, "en")
    ids = [card.attrs["id"] for card in root.select(".sys-card")]
    assert ids.index("system-card-identification") < ids.index("system-card-route-directory-vrs")
    assert ids.index("system-card-route-directory-vrs") < ids.index("system-card-route-directory-adsbdb")
    assert ids.index("system-card-route-directory-adsbdb") < ids.index("system-card-route-answers")
    backup = "system-card-backup"
    if backup in ids:
        assert ids.index("system-card-route-answers") < ids.index(backup)


def test_the_route_topics_are_not_on_the_battery_view(make_app_server):
    server = make_app_server(seed=_seed_degraded)
    cookie = companion_app_server.login(server)
    _code, headers, _ = companion_app_server.get(server, "/health", cookie=cookie)
    code, _, body = companion_app_server.get(server, headers["Location"], cookie=cookie)
    assert code == 200
    page = body.decode("utf-8")
    assert "route-directory" not in page and "route-answers" not in page


def test_a_value_stored_in_the_database_never_reaches_the_markup_raw(make_app_server):
    _root, html = _system(make_app_server, _seed_degraded, "en")
    assert "onerror=alert" not in html
    assert "<img src=x" not in html
