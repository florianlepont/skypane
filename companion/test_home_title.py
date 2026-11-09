"""Home's title: the frame's name is the page's one h1, with a rename pencil
beside it for the people who may rename the frame (its owner and
administrators) and none for a co-manager. Every assertion reads the served
page."""
import pytest

import fleet_console_support as fx
from companion import prefs
from companion_markup import parse_html
from server import fleet_db


@pytest.fixture(autouse=True)
def _english():
    prefs.set_request_prefs(lang="en")
    yield


@pytest.fixture
def rig(app_server_in_process):
    server = app_server_in_process
    seed = fx.seed_fleet(server.state_dir)
    conn = fleet_db.connect(server.state_dir)
    try:
        co = fleet_db.add_user(conn, "co@example.test", "user")
        fleet_db.add_co_manager(conn, seed.owned_id, co, None)
    finally:
        conn.close()
    cookies = {
        "admin": fx.admin_cookie(server.state_dir),
        "owner": fx.user_cookie(server.state_dir, email=fx.OWNER_EMAIL),
        "co": fx.user_cookie(server.state_dir, email="co@example.test")}
    return server, seed, cookies


def _home(server, seed, cookie, lang="en"):
    headers = {"Accept-Language": lang}
    return fx.get(server, cookie, "/devices/%s/" % seed.owned_id, headers=headers)[2]


@pytest.mark.parametrize("who", ["owner", "admin"])
@pytest.mark.parametrize("lang, label, home", [
    ("en", "Rename frame", "Home"), ("fr", "Renommer le cadre", "Accueil")])
def test_the_h1_is_the_frame_name_with_a_rename_pencil(rig, who, lang, label, home):
    server, seed, cookies = rig
    body = _home(server, seed, cookies[who], lang)
    tree = parse_html(body)
    assert len(tree.select("h1")) == 1
    assert tree.select_one("main h1").text().strip() == "Kitchen"
    link = tree.select_one(".title-action a.btn--icon")
    assert link.attrs["href"] == "/devices/%s/frame/name" % seed.owned_id
    assert link.attrs["aria-label"] == label
    assert tree.select_one("title").text().strip().startswith(home)


def test_a_co_manager_sees_the_title_without_the_pencil(rig):
    server, seed, cookies = rig
    tree = parse_html(_home(server, seed, cookies["co"]))
    assert tree.select_one("main h1").text().strip() == "Kitchen"
    assert tree.select(".title-action a") == []
    assert tree.select(".title-action__action") == []


def test_the_greeting_and_the_frame_name_row_are_gone(rig):
    server, seed, cookies = rig
    body = _home(server, seed, cookies["owner"])
    for gone in ("data-greeting", "page-greeting", "home-greeting", "frame-rename",
                 "Frame name"):
        assert gone not in body, gone


def test_the_state_pill_and_the_hero_text_follow_the_title(rig):
    server, seed, cookies = rig
    body = _home(server, seed, cookies["owner"])
    assert body.index("title-action") < body.index("home-state__pill")


def test_a_hostile_frame_name_is_escaped_in_the_title(rig):
    server, seed, cookies = rig
    conn = fleet_db.connect(server.state_dir)
    try:
        conn.execute("UPDATE devices SET name = ? WHERE id = ?", ("<b>x</b>", seed.owned_id))
        conn.commit()
    finally:
        conn.close()
    body = _home(server, seed, cookies["owner"])
    assert "<b>x</b>" not in body and "&lt;b&gt;x&lt;/b&gt;" in body
