"""The Home notification for an amber or red dot: what it says per status
key (English and French), the administrator contact (mailto or plain text),
escaping of hostile values, the roles that see it, and that it adds no route.
Asserted on rendered markup (a direct render for the state matrix and the
contact cases, a real server for the roles)."""
import urllib.parse
from datetime import datetime, timedelta, timezone

import pytest

import companion.prefs as prefs
import companion.routes as routes
from companion import device_scope
from companion.pages import home_notice, home_page
from companion_app_server import InProcessAppServer, http_request, session_cookie_for_state_dir
from companion_markup import parse_html
from provisioned_fleet import (
    ADMIN_EMAIL, NAME_A1, USER_A_EMAIL, USER_B_EMAIL, device_dir, provision_fleet)
from server import device_config, fleet_db, history_db

NOW = "2026-08-27T12:00:00+00:00"
FORBIDDEN_WORDS = ("Health", "Device", "Console")
NO_CAUSE_WORDS = ("broken", "down", "failed")


def _users(state_dir, *users):
    conn = fleet_db.connect(str(state_dir))
    try:
        for email, role, disabled in users:
            fleet_db.add_user(conn, email, role, disabled=disabled)
    finally:
        conn.close()


def _checkin(state_dir, minutes_ago, mv=4000):
    stamp = datetime.fromisoformat(NOW) - timedelta(minutes=minutes_ago)
    with history_db.open_db(str(state_dir)) as conn:
        history_db.record_device_health(
            conn, stamp.isoformat(), battery_mv=mv, fw_version="1.0.0",
            boot_reason="wake", rssi="-60")
    return stamp.isoformat()


def _frame(state_dir, name="Orly window"):
    return device_scope.Device(
        "d_00000001", name, "legacy", "auto", str(state_dir), False, 1)


def _render(state_dir, lang="en", last=None, device=None, cfg=None):
    prefs.set_request_prefs(lang=lang)
    try:
        return home_page.render({
            "state_dir": str(state_dir), "now": NOW, "gallery_entries": [],
            "last_checkin_ts": last, "device": device,
            "device_config": dict({"wake_interval_s": 900, "display_enabled": True},
                                  **(cfg or {})),
            "health_state": {"device_state": "ok", "pipeline_state": "ok",
                             "battery_state": "ok"},
        })
    finally:
        prefs.set_request_prefs(lang="en")


def _notice(rendered):
    found = parse_html(rendered).select(".home-notice")
    return found[0] if found else None


def _lines(notice):
    return [node.text() for node in notice.select(".home-notice__line")]


def _seed(state_dir, key):
    """The check-in history that puts a non-live frame in the status `key`."""
    if key == "overdue":
        return _checkin(state_dir, 50), None
    if key == "low_battery":
        return _checkin(state_dir, 1, mv=3381), None
    if key == "no_contact":
        return _checkin(state_dir, 300), "frame"
    return None, None


def _render_key(state_dir, key, lang="en", name="Orly window"):
    last, device = _seed(state_dir, key)
    return _render(state_dir, lang, last=last,
                   device=_frame(state_dir, name) if key == "no_contact" else None)


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("key", ["not_seen", "overdue", "low_battery", "no_contact"])
def test_notification_sits_above_the_hero_that_carries_the_title(tmp_path, key, lang):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    last, _ = _seed(tmp_path, key)
    rendered = _render(tmp_path, lang, last=last,
                       device=_frame(tmp_path) if key == "no_contact" else None)
    facts = rendered.index('<div class="home-facts">')
    notice = rendered.index("home-notice")
    card = rendered.index('aria-labelledby="home-frame-state"')
    assert facts < notice < card
    assert rendered.index("</div>", notice) < card


@pytest.mark.parametrize("lang,words", [
    ("en", {"not_seen": "Not seen yet", "overdue": "Overdue", "low_battery": "Low battery",
            "no_contact": "No contact"}),
    ("fr", {"not_seen": "Pas encore vu", "overdue": "En retard", "low_battery": "Batterie faible",
            "no_contact": "Sans contact"})])
def test_card_title_dot_and_notification_agree(tmp_path, lang, words):
    for key, word in words.items():
        state_dir = tmp_path / key
        state_dir.mkdir()
        _users(state_dir, (ADMIN_EMAIL, "admin", False))
        last, _ = _seed(state_dir, key)
        rendered = _render(state_dir, lang, last=last,
                           device=_frame(state_dir) if key == "no_contact" else None)
        assert '<span class="home-state__title">%s</span>' % word in rendered, key
        assert 'role="img" aria-label="%s" title="%s"' % (word, word) in rendered, key
        assert len(parse_html(rendered).select(".home-notice")) == 1, key


@pytest.mark.parametrize("key,tone", [
    ("not_seen", "warning"), ("overdue", "warning"), ("low_battery", "warning"),
    ("no_contact", "error")])
def test_amber_and_red_statuses_show_one_notification(tmp_path, key, tone):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    rendered = _render_key(tmp_path, key)
    notices = parse_html(rendered).select(".home-notice")
    assert len(notices) == 1
    assert "toast--%s" % tone in notices[0].attrs["class"]
    assert len(parse_html(rendered).select(".home-facts .home-notice")) == 1
    assert "role" not in notices[0].attrs
    text = notices[0].text()
    for word in FORBIDDEN_WORDS:
        assert word not in text
    assert "amber" not in text.lower()
    assert len(parse_html(rendered).select(".home-action")) == 0


def test_other_statuses_show_no_notification(tmp_path):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    assert _notice(_render(tmp_path, last=_checkin(tmp_path, 2))) is None
    assert _notice(_render(
        tmp_path, last=_checkin(tmp_path, 2), cfg={"display_enabled": False})) is None


def test_english_lines_and_tips_per_status_key(tmp_path):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    expected = {
        "not_seen": (
            "Your frame has not contacted SkyPane yet.", [],
            "Check it is powered, if it stays silent, contact an administrator."),
        "overdue": (
            "Your frame has not checked in on time.", ["Last check-in 50m ago"],
            "Wait one cycle, if it stays silent, contact an administrator."),
        "low_battery": (
            "Your frame's battery is low.",
            ["Frame battery at 8%"], "Charge it or plug it in."),
        "no_contact": (
            "Your frame has no contact with the server.",
            ["Last contact 5h ago"],
            "Check its power and your Wi-Fi, if it stays silent, contact an "
            "administrator."),
    }
    for key, (title, figures, tip) in expected.items():
        directory = tmp_path / key
        directory.mkdir()
        _users(directory, (ADMIN_EMAIL, "admin", False))
        notice = _notice(_render_key(directory, key))
        assert notice.select(".toast__title")[0].text() == title
        lines = _lines(notice)
        assert lines == figures, key
        assert notice.select(".home-notice__tip")[0].text() == tip
        assert len(notice.select(".toast__title")[0].text().split(". ")) == 1
        assert tip.count(". ") == 0 and tip.count(".") == 1
        text = notice.text()
        for word in NO_CAUSE_WORDS:
            assert word not in text


def test_french_lines_and_tips_per_status_key(tmp_path):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    notice = _notice(_render_key(tmp_path, "no_contact", lang="fr"))
    assert notice.select(".toast__title")[0].text() == (
        "Votre cadre n’est plus en contact avec le serveur.")
    assert _lines(notice)[0].startswith("Dernier contact : il y a 5")
    assert len(_lines(notice)) == 1
    assert notice.select(".home-notice__tip")[0].text() == (
        "Vérifiez son alimentation et votre Wi-Fi, s’il reste muet, contactez "
        "un administrateur.")
    assert notice.select("a.toast__action")[0].text() == (
        "Contacter un administrateur")
    low = tmp_path / "low"
    low.mkdir()
    _users(low, (ADMIN_EMAIL, "admin", False))
    assert "Batterie du cadre à 8 %" in _lines(_notice(_render_key(
        low, "low_battery", lang="fr")))


def test_unknown_figures_drop_their_line(tmp_path):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    # A late frame whose last check-in is unreadable has no age to quote.
    notice = _notice(_render(tmp_path, last="not-a-date"))
    assert notice is None or all("Last check-in" not in line for line in _lines(notice))
    low = _notice(_render_key(tmp_path, "low_battery"))
    assert not any("Charging" in line or "charging" in line for line in _lines(low))
    contact = tmp_path / "contact"
    contact.mkdir()
    _users(contact, (ADMIN_EMAIL, "admin", False))
    assert "Frame battery at" not in _notice(_render_key(contact, "no_contact")).text()


def _href(notice):
    links = notice.select("a.toast__action")
    return links[0].attrs["href"] if links else None


def test_contact_is_the_first_active_administrator(tmp_path):
    _users(
        tmp_path,
        ("plain@example.test", "user", False),
        ("off@example.test", "admin", True),
        ("second@example.test", "admin", False),
        ("third@example.test", "admin", False))
    notice = _notice(_render_key(tmp_path, "not_seen"))
    href = _href(notice)
    assert href.startswith("mailto:second@example.test?subject=")
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
    assert "not seen" in query["subject"][0].lower()
    assert query["body"][0].count("\n") >= 2


def test_mail_subject_and_body_name_the_frame_and_the_known_figures(tmp_path):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    last, _ = _seed(tmp_path, "no_contact")
    notice = _notice(_render(
        tmp_path, last=last, device=_frame(tmp_path, "Orly window")))
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(_href(notice)).query)
    assert query["subject"][0] == "SkyPane: help with the frame Orly window (No contact)"
    assert "Last contact 5h ago" in query["body"][0]
    assert "Orly window" in query["body"][0]


@pytest.mark.parametrize("users", [
    [],
    [("user@example.test", "user", False)],
    [("off@example.test", "admin", True)],
])
def test_no_active_administrator_shows_plain_text_without_link_or_address(tmp_path, users):
    _users(tmp_path, *users)
    notice = _notice(_render_key(tmp_path, "not_seen"))
    assert _href(notice) is None
    assert notice.select("a") == []
    text = notice.text()
    assert "contact an administrator." in text
    assert "@" not in text and "mailto" not in str(notice)


class _FakeConn:
    """Rows as the fleet database would return them, for stored values the
    real insert path refuses."""

    def __init__(self, rows):
        self.rows = rows

    def execute(self, _sql, _params=()):
        return list(self.rows)


@pytest.mark.parametrize("address", [
    "bad address@example.test", "a@b@example.test",
    "x@example.test?bcc=evil@example.test", 'x"<y>@example.test', "x,y@example.test",
    "x@example.test\nBcc: z@example.test", "x@example.test&body=1"])
def test_a_stored_address_of_an_unusable_shape_gives_plain_text(address):
    assert home_notice.administrator_contact(_FakeConn([
        {"id": 1, "email": address, "role": "admin", "disabled": 0}])) is None
    status = home_notice.frame_status.frame_status(type("Row", (), {"last_seen": None})())
    facts = type("Facts", (), {"frame_name": "F", "percent": None, "charging": False,
                               "last_seen": None, "now": NOW})()
    markup = home_notice.notification_html(facts, status, address)
    assert "<a " not in markup and "mailto" not in markup and "bcc" not in markup


def test_an_unreadable_fleet_database_means_no_administrator():
    class Broken:
        def execute(self, *_args):
            raise __import__("sqlite3").DatabaseError("unreadable")
    assert home_notice.administrator_contact(Broken()) is None


def test_missing_fleet_database_shows_plain_text(tmp_path):
    notice = _notice(_render_key(tmp_path, "not_seen"))
    assert _href(notice) is None
    assert "contact an administrator" in notice.text()


def test_hostile_frame_name_is_escaped_in_markup_and_encoded_in_the_link(tmp_path):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    name = 'A"<b>&?x=1%\nBcc: e@e.test'
    last, _ = _seed(tmp_path, "no_contact")
    rendered = _render(tmp_path, last=last, device=_frame(tmp_path, name))
    notice = _notice(rendered)
    href = _href(notice)
    for raw in ('"', "<", ">", " ", "\n"):
        assert raw not in href
    assert href.count("?") == 1 and href.count("&") == 1
    query = urllib.parse.parse_qs(urllib.parse.urlsplit(href).query)
    assert name in query["subject"][0] and name in query["body"][0]
    assert "<b>" not in str(notice)


def test_address_is_percent_encoded_and_shape_checked():
    assert home_notice.usable_address("a.b+c@example.test") == "a.b+c@example.test"
    for bad in (None, "", "no-at", "a@b", "a b@example.test", "a@b@example.test",
                "a,b@example.test", "<a@example.test>", 'a"@example.test',
                "a@example.test?bcc=x@example.test", "a@exa mple.test",
                "a@example.test\r\nBcc: x", "é@example.test", "x" * 300 + "@example.test"):
        assert home_notice.usable_address(bad) is None, bad
    status = home_notice.frame_status.frame_status(
        type("Row", (), {"last_seen": None})())
    facts = type("Facts", (), {"frame_name": "F", "percent": None, "charging": False,
                               "last_seen": None, "now": NOW})()
    href = home_notice.mailto_href("a+b%c@example.test", facts, status)
    assert href.startswith("mailto:a%2Bb%25c@example.test?subject=")


def test_notification_disappears_once_the_frame_recovers(tmp_path):
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    assert _notice(_render(tmp_path, last=None)) is not None
    assert _notice(_render(tmp_path, last=_checkin(tmp_path, 2))) is None


def test_no_route_was_added_and_nothing_new_is_requested(tmp_path):
    for route in routes.ROUTES:
        text = repr(route.matcher).lower()
        assert "contact" not in text and "notice" not in text and "mail" not in text
    _users(tmp_path, (ADMIN_EMAIL, "admin", False))
    html = _render_key(tmp_path, "not_seen")
    hrefs = [a.attrs["href"] for a in parse_html(html).select(".home-notice a")]
    assert [h for h in hrefs if not h.startswith("mailto:")] == []


class _Rig:
    def __init__(self, state_dir):
        self.state_dir = str(state_dir)
        self.server = InProcessAppServer(self.state_dir)
        self.fleet = provision_fleet(self.state_dir)
        self.cookies = {
            "owner": session_cookie_for_state_dir(self.state_dir, USER_A_EMAIL, "user"),
            "admin": session_cookie_for_state_dir(self.state_dir, ADMIN_EMAIL),
            "other": session_cookie_for_state_dir(self.state_dir, USER_B_EMAIL, "user"),
        }

    def home(self, who):
        status, _headers, body = http_request(
            self.server.url("/devices/%s/" % self.fleet.a1), cookie=self.cookies[who])
        assert status == 200
        return body.decode("utf-8")

    def stop(self):
        self.server.stop()


@pytest.fixture
def rig(tmp_path):
    built = _Rig(tmp_path / "state")
    yield built
    built.stop()


def _real_checkin(state_dir, device_id, minutes_ago, mv=4000):
    stamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    with history_db.open_db(device_dir(state_dir, device_id)) as conn:
        history_db.record_device_health(
            conn, stamp.isoformat(), battery_mv=mv, fw_version="1.0.0",
            boot_reason="wake", rssi="-60")


@pytest.mark.parametrize("who", ["owner", "admin"])
def test_owner_and_administrator_see_the_not_seen_notification(rig, who):
    notice = _notice(rig.home(who))
    assert notice is not None
    assert _href(notice).startswith("mailto:%s?subject=" % ADMIN_EMAIL)
    subject = urllib.parse.parse_qs(urllib.parse.urlsplit(_href(notice)).query)["subject"][0]
    assert NAME_A1 in subject


def test_co_manager_sees_the_notification_too(rig):
    conn = fleet_db.connect(rig.state_dir)
    try:
        fleet_db.add_co_manager(conn, rig.fleet.a1, rig.fleet.b_id, rig.fleet.a_id)
    finally:
        conn.close()
    rig.cookies["co"] = session_cookie_for_state_dir(rig.state_dir, USER_B_EMAIL, "user")
    assert _notice(rig.home("co")) is not None


def test_the_notification_follows_the_frame_over_http(rig):
    _real_checkin(rig.state_dir, rig.fleet.a1, 300)
    notice = _notice(rig.home("owner"))
    assert "toast--error" in notice.attrs["class"]
    assert "no contact" in notice.text().lower()
    _real_checkin(rig.state_dir, rig.fleet.a1, 1, mv=4000)
    assert _notice(rig.home("owner")) is None
    _real_checkin(rig.state_dir, rig.fleet.a1, 0, mv=3381)
    assert "Frame battery at" in _notice(rig.home("owner")).text()
    assert device_config.load_device_config(device_dir(rig.state_dir, rig.fleet.a1))
