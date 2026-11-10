"""The personal space is identical for an administrator and a user: for the same
frame state, every personal page carries the same navigation links, the same
form controls and the same body, whoever looks at it. The space switch and the
foreign-frame notice are the only things an administrator adds. Real in-process
requests, no browser."""
import hashlib
import re

import pytest

from companion import app, auth
from companion_app_server import http_request
from server import device_dirs, fleet_db, fleet_sessions, hardware, history_db

# One constant so later plans extend the list of compared pages.
PERSONAL_PAGES = ("/", "/flights", "/detection", "/display", "/airlines")

FORBIDDEN_LABELS = ("Health", "Device", "Fleet", "Users", "Audit", "Releases", "Airline editor")
FORBIDDEN_LABELS_FR = (
    "État", "Appareil", "Flotte", "Utilisateurs", "Audit", "Versions",
    "Éditeur de compagnies")
FORBIDDEN_PATHS = ("/health", "/device", "/fleet", "/users", "/audit", "/update", "/airlines/manage")
NAME_THIS_AIRLINE = ("Name this airline", "Nommer cette compagnie")

USER_EMAIL = "user@parity.test"
ADMIN_EMAIL = "admin@parity.test"
MAC_USER = "aa:bb:cc:dd:ee:11"
MAC_ADMIN = "aa:bb:cc:dd:ee:12"


def _seed_identical_history(state_dir):
    with history_db.open_db(state_dir) as conn:
        for i, airline in enumerate(("Air France", None)):
            history_db.record_runway_event(
                conn, ts="2026-10-01T09:0%d:00+00:00" % i, hex="39a1b%d" % i,
                callsign="AFR12%d" % i if airline else "XYZ98%d" % i,
                aircraft_type="A320", confirmed_state="departure",
                corroborated=True, route_source="fresh_hit", airline=airline,
                origin="ORY", destination="JFK", tracked_runway="3")


@pytest.fixture
def parity(app_server_in_process):
    """A user owning frame F1 and an administrator owning frame F2, both with
    the same history, plus one session cookie per principal."""
    server = app_server_in_process
    conn = fleet_db.connect(server.state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        user_id = fleet_db.add_user(conn, USER_EMAIL, "user")
        admin_id = fleet_db.add_user(conn, ADMIN_EMAIL, "admin")
        frames = {}
        for who, owner_id, mac, secret in (
                ("user", user_id, MAC_USER, "a" * 64),
                ("admin", admin_id, MAC_ADMIN, "b" * 64)):
            device_id = fleet_db.add_device(
                conn, mac, secret, hardware.LEGACY_KEY, owner_id, state_path="auto")
            frames[who] = device_id
        cookies = {}
        for who, owner_id in (("user", user_id), ("admin", admin_id)):
            token = "tok-parity-" + who
            fleet_sessions.create_session(
                conn, hashlib.sha256(token.encode()).hexdigest(), user_id=owner_id,
                principal="user", now=app._now())
            cookies[who] = "sp_session=" + token
        rows = {row["id"]: row for row in fleet_db.list_devices(conn)}
    finally:
        conn.close()
    for who, device_id in frames.items():
        state_dir = device_dirs.resolve_state_dir(
            server.state_dir, rows[device_id]["state_path"])
        _seed_identical_history(state_dir)
    server.frames = frames
    server.cookies = cookies
    return server


def _get(server, who, path, lang="en"):
    prefix = "/devices/%s" % server.frames[who]
    status, _headers, body = http_request(
        server.url(prefix + ("" if path == "/" else path) + ("/" if path == "/" else "")),
        cookie="%s; %s=%s" % (server.cookies[who], auth.UI_LANG_COOKIE_NAME, lang))
    assert status == 200, (who, path, status)
    return body.decode("utf-8")


def _strip_switch_and_notice(markup):
    markup = re.sub(r'<nav class="space-switch".*?</nav>', "", markup, flags=re.S)
    markup = re.sub(
        r'<a class="[^"]*tab-bar__link--switch[^"]*"[^>]*>.*?</a>', "", markup, flags=re.S)
    markup = re.sub(
        r'<div class="[^"]*frame-notice[^"]*".*?</div>', "", markup, flags=re.S)
    return markup


def _normalise(markup, server):
    """The page with the two principals' own ids, emails and tokens replaced by
    fixed placeholders, and the switch and foreign-frame notice removed."""
    markup = re.sub(r"\n\s*\n", "\n", _strip_switch_and_notice(markup))
    for name in ("user", "admin"):
        markup = markup.replace(server.frames[name], "DEVICE")
    markup = re.sub(r"(?:(?<![A-Za-z_])|(?<=%2F))d[_-][0-9a-f]{8}\b", "DEVICE", markup)
    markup = markup.replace(USER_EMAIL, "OWNER").replace(ADMIN_EMAIL, "OWNER")
    markup = re.sub(r'(name="csrf_token"[^>]*value=")[^"]*', r"\1TOKEN", markup)
    markup = re.sub(r'(value=")[0-9a-f]{32,}(")', r"\1TOKEN\2", markup)
    markup = re.sub(r"(refresh|token|nonce)=[0-9A-Za-z_\-]{16,}", r"\1=TOKEN", markup)
    markup = re.sub(r'(data-refresh-token=")[0-9a-f]+', r"\1TOKEN", markup)
    markup = re.sub(r'(<meta name="csrf[^>]*content=")[^"]*', r"\1TOKEN", markup)
    # Both renders are fetched a moment apart, so any clock reading the page
    # carries (a <time> element's instant and its relative wording) is not a
    # difference between the two principals.
    markup = re.sub(r'(<time\b[^>]*\bdatetime=")[^"]*(")', r"\1INSTANT\2", markup)
    markup = re.sub(r"(<time\b[^>]*>)[^<]*(</time>)", r"\1CLOCK\2", markup)
    markup = re.sub(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:[+-]\d{2}:\d{2}|Z)?",
        "INSTANT", markup)
    return markup


def _links(markup):
    markup = _strip_switch_and_notice(markup).replace(
        USER_EMAIL, "OWNER").replace(ADMIN_EMAIL, "OWNER")
    return sorted(
        (re.sub(r"(?:(?<![A-Za-z_])|(?<=%2F))d[_-][0-9a-f]{8}\b", "DEVICE", href),
         re.sub(r"(?:(?<![A-Za-z_])|(?<=%2F))d[_-][0-9a-f]{8}", "DEVICE",
                re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", inner)).strip()))
        for href, inner in re.findall(r'<a [^>]*href="([^"]+)"[^>]*>(.*?)</a>', markup, re.S))


def _control_names(markup):
    markup = _strip_switch_and_notice(markup)
    return sorted(set(re.findall(
        r'<(?:input|select|textarea|button)\b[^>]*\bname="([^"]+)"', markup)))


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("page", PERSONAL_PAGES)
def test_a_personal_page_is_identical_for_an_administrator_and_a_user(parity, page, lang):
    user_page = _get(parity, "user", page, lang)
    admin_page = _get(parity, "admin", page, lang)

    assert _links(admin_page) == _links(user_page)
    assert _control_names(admin_page) == _control_names(user_page)
    assert _normalise(admin_page, parity) == _normalise(user_page, parity)


def test_only_an_administrator_is_offered_the_space_switch(parity):
    for page in PERSONAL_PAGES:
        assert 'class="space-switch"' in _get(parity, "admin", page)
        assert "space-switch" not in _get(parity, "user", page)


HARDWARE_LABEL = hardware.REGISTRY[hardware.LEGACY_KEY].label


def test_account_navigation_and_controls_match_for_both_principals(parity):
    status = {}
    pages = {}
    for who in ("user", "admin"):
        code, _headers, body = http_request(
            parity.url("/account"), cookie=parity.cookies[who])
        status[who] = code
        pages[who] = body.decode("utf-8")
    assert status == {"user": 200, "admin": 200}
    assert _control_names(pages["admin"]) == _control_names(pages["user"])
    # The account page itself is not frame-scoped, so only the frame prefix
    # of the navigation differs by who owns which frame; identity rows differ
    # by design.
    # An administrator's frame row also names the hardware model; a person's does not.
    def unscoped(markup, email):
        return sorted(
            (href.replace("/devices/DEVICE", ""), text.replace(HARDWARE_LABEL, ""))
            for href, text in _links(markup) if text != email)
    assert unscoped(pages["admin"], ADMIN_EMAIL) == unscoped(pages["user"], USER_EMAIL)


@pytest.mark.parametrize("lang,forbidden", [
    ("en", FORBIDDEN_LABELS), ("fr", FORBIDDEN_LABELS_FR)])
@pytest.mark.parametrize("who", ["user", "admin"])
@pytest.mark.parametrize("page", PERSONAL_PAGES)
def test_no_personal_page_offers_an_admin_control(parity, who, page, lang, forbidden):
    markup = _strip_switch_and_notice(_get(parity, who, page, lang))
    for href, text in _links(markup):
        path = re.sub(r"^/devices/DEVICE", "", href).split("?")[0] or "/"
        assert path not in FORBIDDEN_PATHS, (who, page, href)
        assert text not in forbidden, (who, page, text)
    for label in NAME_THIS_AIRLINE:
        assert label not in markup


def test_flight_history_keeps_the_unidentified_wording_without_a_link(parity):
    for who in ("user", "admin"):
        markup = _get(parity, who, "/flights")
        assert "Airline unknown" in markup
        assert "?resolve=" not in markup


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("who", ["user", "admin"])
def test_the_airline_collection_is_read_only_and_counts_the_same_history(parity, who, lang):
    markup = _get(parity, who, "/airlines", lang)
    main = re.search(r"<main\b.*?</main>", markup, flags=re.S).group(0)
    assert 'type="file"' not in main
    assert not re.search(r"<form\b[^>]*method=\"post\"", main, flags=re.I)
    assert not re.search(r"(?:action|href)=\"[^\"]*/airlines/", main)
    assert not re.search(r"(?:rename|resolve|delete|replace)", main.lower().replace("unresolved", ""))
    assert ("Seen once" if lang == "en" else "Vue une fois") in main
    assert ("1 of " if lang == "en" else "1 compagnie repérée sur ") in main
