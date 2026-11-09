"""The Personalisation calendar connection: one status row plus the connection page.

Served-HTML checks for every state the row can show (not connected, waiting, connected N,
zero flights, stale, last read failed, unparseable timestamp, ignored link), the connection
page's structure, the "the full URL never reaches the browser" guard, and the routes: a
replacement link is read BEFORE it is saved, so a refused or unreachable one leaves the working
link and its flights untouched and returns to the connection page with the error.
"""
import urllib.parse
from datetime import datetime, timedelta

import pytest

import companion.layout as layout
import companion.prefs as prefs
import companion.test_companion_app_helpers as cah
import companion.test_config_page_helpers as cp
from companion.pages import config_page
from companion.settings import calendar as calendar_settings
from companion_app_server import http_request, login, served_asset, with_csrf
from companion_markup import parse_html
from server.plane import calendar_rules

NOW = "2026-09-07T09:12:04+00:00"
NOW_EPOCH = datetime.fromisoformat(NOW).timestamp()


def _iso(seconds_ago):
    return (datetime.fromisoformat(NOW) - timedelta(seconds=seconds_ago)).isoformat(timespec="seconds")


def _ctx(**overrides):
    base = dict(calendar_last_attempt_at=None, calendar_entry_count=0)
    base.update(overrides)
    return dict(cp.CALENDAR_BASE_CTX, **base)


# state key -> ctx overrides, and the (pill dot class, EN pill, EN detail fragment).
_STATES = {
    "none": (
        dict(calendar_configured=False, calendar_last_synced_at=None),
        "dot--off", "Not connected", "Colour the flights from your calendar on screen."),
    "pending": (
        dict(calendar_configured=True, calendar_last_synced_at=None),
        "dot--warn", "Waiting", "First read at the frame's next check"),
    "ok": (
        dict(calendar_configured=True, calendar_last_synced_at=_iso(1560),
             calendar_last_attempt_at=NOW_EPOCH - 1560, calendar_entry_count=3),
        "dot--ok", "Connected", "3 flights in the next 48 h · checked 26m ago"),
    "zero": (
        dict(calendar_configured=True, calendar_last_synced_at=_iso(240),
             calendar_last_attempt_at=NOW_EPOCH - 240, calendar_entry_count=0),
        "dot--warn", "Check", "0 flights found — check it's the right calendar"),
    "stale": (
        dict(calendar_configured=True, calendar_last_synced_at=_iso(3 * 3600),
             calendar_last_attempt_at=NOW_EPOCH - 120, calendar_entry_count=3),
        "dot--warn", "Out of date", "Last read 3h ago"),
    "failed": (
        dict(calendar_configured=True, calendar_last_synced_at=_iso(1500),
             calendar_last_attempt_at=NOW_EPOCH - 120, calendar_entry_count=3),
        "dot--error", "Error", "Couldn't read the calendar · last read 25m ago"),
    "failed_never": (
        dict(calendar_configured=True, calendar_last_synced_at=None,
             calendar_last_attempt_at=NOW_EPOCH - 120),
        "dot--error", "Error", "Couldn't read the calendar"),
    "unknown": (
        dict(calendar_configured=True, calendar_last_synced_at="not-a-real-timestamp"),
        "dot--off", "Connected", ""),
    "ignored": (
        dict(calendar_configured=False, calendar_last_synced_at=None, calendar_drift=True),
        "dot--error", "Ignored", "Saved link ignored"),
}

_STATE_KEY = {"failed_never": "failed"}


def sheet_details(li):
    """Every <details> inside the Calendar row except the look chooser's own `look-edit`."""
    return [node for node in li.select("details") if node.attrs.get("class") != "look-edit"]


def _row(rendered):
    doc = parse_html(rendered)
    row = doc.select_one(".calendar-status")
    assert row is not None, "expected exactly one .calendar-status row"
    return doc, row


@pytest.mark.parametrize("name", sorted(_STATES))
def test_every_state_renders_its_pill_dot_and_detail(name):
    """each state shows the status line (on or off, with the calendar's name when on), its
    verdict in words, a dot that is never green unless the state is a healthy connection, and its
    one-line detail; with nothing connected the detail is the compact empty state's body"""
    overrides, dot, pill, detail_fragment = _STATES[name]
    rendered = config_page.render(_ctx(**overrides), scope=config_page.SCOPE_DISPLAY)
    doc, row = _row(rendered)
    assert row.attrs.get("data-calendar-state") == _STATE_KEY.get(name, name)
    assert len(doc.select(".calendar-status")) == 1
    lead = row.select_one(".calendar-status__lead").text().strip()
    if name == "none":
        assert lead == "Flights in your calendar: off"
        assert not row.select(".calendar-status__pill") and not row.select(".calendar-status__detail")
        empty = doc.select_one("#calendar-row .empty-state--compact")
        assert empty.select_one(".empty-state__heading").text() == "No calendar connected"
        assert empty.select_one(".empty-state__body").text() == detail_fragment
        return
    assert not doc.select("#calendar-row .empty-state")
    assert lead == ("Flights in your calendar: off" if name == "ignored"
                    else "Flights in your calendar: on,"), (name, lead)
    assert row.select_one(".calendar-status__pill").text().strip() == pill
    dot_classes = row.select_one(".calendar-status__pill .dot").attrs.get("class", "").split()
    assert dot in dot_classes, (name, dot_classes)
    if dot != "dot--ok":
        assert "dot--ok" not in dot_classes, "no green dot beside a non-healthy verdict"
    detail = row.select_one(".calendar-status__detail").text().strip()
    assert detail_fragment in detail, (name, detail)
    if name == "unknown":
        assert detail == "", "an unparseable read time has no detail to show"


def test_stale_threshold_is_four_fetch_intervals_and_the_boundary_is_exact():
    """a last success exactly at the threshold still reads connected; one second past reads out
    of date. The threshold derives from the poll cadence, not from a free-standing number"""
    assert calendar_rules.CALENDAR_STALE_AFTER_S == 4 * calendar_rules.CALENDAR_FETCH_INTERVAL_S == 7200
    limit = calendar_rules.CALENDAR_STALE_AFTER_S
    for age, expected in ((limit, "ok"), (limit + 1, "stale")):
        state = calendar_settings.calendar_state(
            True, False, _iso(age), NOW_EPOCH - age, NOW, 2)
        assert state == expected, (age, state)


def test_a_failed_read_never_shows_green_even_with_a_recent_success():
    """an attempt newer than the last success reads Error, not Connected"""
    state = calendar_settings.calendar_state(True, False, _iso(900), NOW_EPOCH - 60, NOW, 3)
    assert state == "failed"
    # A successful read stamps last_synced_at at second precision, a moment before the recorded
    # attempt finished: that gap is not a failure.
    assert calendar_settings.calendar_state(True, False, _iso(30), NOW_EPOCH - 5, NOW, 3) == "ok"


@pytest.mark.parametrize("name", ["none", "ok", "zero", "stale", "failed", "pending", "ignored"])
def test_states_render_in_french_with_the_state_words(name):
    """the same states in French carry the translated pill and detail and no English leftovers"""
    expected = {
        "none": ("Non connecté", "Colorez à l’écran les vols de votre calendrier."),
        "pending": ("En attente", "Première lecture au prochain passage du cadre"),
        "ok": ("Connecté", "3 vols dans les 48 h · vérifié il y a 26 min"),
        "zero": ("À vérifier", "0 vol trouvé — vérifiez que c’est le bon calendrier"),
        "stale": ("Pas à jour", "Dernière lecture il y a 3 h"),
        "failed": ("Erreur", "Lecture impossible · dernière lecture il y a 25 min"),
        "ignored": ("Ignoré", "Lien enregistré ignoré"),
    }[name]
    overrides = _STATES[name][0]
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = config_page.render(_ctx(**overrides), scope=config_page.SCOPE_DISPLAY)
    finally:
        prefs.set_request_prefs(lang="en")
    doc, row = _row(rendered)
    lead = row.select_one(".calendar-status__lead").text().strip()
    assert lead == ("Vols de votre calendrier : désactivés" if name in ("none", "ignored")
                    else "Vols de votre calendrier : activés,"), lead
    if name == "none":
        detail = doc.select_one("#calendar-row .empty-state__body").text().strip()
        assert doc.select_one("#calendar-row .empty-state__heading").text() == "Aucun calendrier connecté"
    else:
        assert row.select_one(".calendar-status__pill").text().strip() == expected[0]
        detail = row.select_one(".calendar-status__detail").text().strip()
    assert expected[1] in detail, detail
    assert row.select_one("a.calendar-manage").text().strip() == (
        "Connecter un calendrier" if name == "none" else "Choisir un calendrier")
    for english in ("Connected", "flights in", "Manage", "Out of date", "Choose calendar",
                    "Connect a calendar"):
        assert english not in row.text()


def test_the_calendar_row_meta_no_longer_repeats_the_verdict():
    """the Special looks row's meta line names the look only: 'Connected' lives in the status
    row's pill, once"""
    overrides = _STATES["ok"][0]
    rendered = config_page.render(_ctx(**overrides), scope=config_page.SCOPE_DISPLAY)
    doc = parse_html(rendered)
    meta = doc.select_one("#calendar-row .special-row__meta")
    assert meta is not None
    assert "Connected" not in meta.text()
    assert "·" not in meta.text()


def _connect_page(**overrides):
    return parse_html(config_page.render(
        _ctx(**overrides), scope=config_page.SCOPE_DISPLAY, view="calendar-connect"))


def test_the_list_carries_one_button_that_opens_the_connection_page_and_no_dialog():
    """the list's connection block is a single link to the connection page: no <details>, no
    inline URL field, no dialog and no Disconnect button"""
    for name, label in (("ok", "Choose calendar"), ("none", "Connect a calendar")):
        rendered = config_page.render(_ctx(**_STATES[name][0]), scope=config_page.SCOPE_DISPLAY)
        doc = parse_html(rendered)
        row = doc.select_one(".calendar-status")
        opener = row.select_one("a.calendar-manage")
        assert opener.text().strip() == label
        assert opener.attrs["href"] == "/display/calendar/connect"
        li = doc.select_one("#calendar-row")
        assert not row.select("details") and not sheet_details(li), (
            "no disclosure toggle in the connection block")
        assert not li.select("dialog") and not li.select('input[name="calendar_url"]')
        assert not li.select(".calendar-danger") and not li.select("a.form-page__danger")


def test_a_refused_paste_shows_the_explicit_error_on_the_page_and_nothing_is_echoed():
    """error codes render the matching inline error, aria-linked to the field; nothing is echoed
    back into the field"""
    for code, message in (
            ("invalid", "That isn't a calendar link: it must start with https:// or webcal://."),
            ("unreachable", "That link doesn't answer. Nothing was changed.")):
        doc = _connect_page(calendar_sheet_error=code, **_STATES["ok"][0])
        error = doc.select_one("#calendar-connect-url-error")
        assert error.attrs.get("role") == "alert"
        assert message in error.text()
        field = doc.select_one('input[name="calendar_url"]')
        assert field.attrs.get("aria-invalid") == "true"
        assert "calendar-connect-url-error" in field.attrs.get("aria-describedby", "")
        assert "value" not in field.attrs
    assert _connect_page(**_STATES["ok"][0]).select("#calendar-connect-url-error") == []


def test_connection_page_controls_connected_vs_not_connected():
    """connected: masked host, 'New link', Replace and Disconnect (a confirmation dialog that
    says what happens to the flights). Not connected: 'Calendar link', Connect, the one
    how-it-works line and no Disconnect. Save and Cancel are the floating bar"""
    connected = _connect_page(**_STATES["ok"][0])
    submit = connected.select_one(".dirty-bar button[data-pending-label]")
    assert submit.text().strip() == "Save" and submit.attrs["data-pending-label"] == "Checking…"
    assert submit.attrs["form"] == "calendar-connect-form"
    assert connected.select_one("form#calendar-connect-form").attrs["action"] == (
        "/settings/calendar/connect")
    assert connected.select_one("a.dirty-bar__cancel").attrs["href"] == "/display/calendar"
    trigger = connected.select_one("a.form-page__danger")
    dialog = connected.select_one("dialog.modal")
    assert trigger.attrs["href"] == "#" + dialog.attrs["id"]
    assert "the flights it supplied are deleted" in dialog.text()
    form = dialog.select_one("form")
    assert form.attrs["action"] == "/settings/calendar/disconnect"
    assert form.select_one('input[name="confirm"]').attrs.get("value") == "yes"
    assert "autofocus" in dialog.select_one("a.modal__dismiss").attrs
    assert "New link" in connected.text()
    assert "does not track" not in connected.text()

    fresh = _connect_page(**_STATES["none"][0])
    assert not fresh.select("dialog") and not fresh.select("a.form-page__danger")
    assert "Connect a calendar" in fresh.text()
    assert "does not track" in fresh.text()
    assert fresh.select_one(".dirty-bar button[data-pending-label]").text().strip() == "Save"


def test_the_connection_page_is_titled_for_the_task_and_follows_the_list():
    """the page is one card titled for what it does (no look picture over it) and sits under the
    Calendar tab"""
    doc = _connect_page(**_STATES["ok"][0])
    assert doc.select_one(".form-page__title").text()
    assert not doc.select(".form-page__preview")
    assert not doc.select(".look-frame__image")
    assert doc.select_one("a.form-back").attrs["href"] == "/display/calendar"
    assert doc.select_one('nav.personalisation-nav a[aria-current="page"]').attrs[
        "data-pers-view"] == "calendar"


def test_drift_offers_disconnect_and_a_fresh_paste():
    """an ignored (group-readable) link has no valid host to show but can be replaced or removed"""
    doc = _connect_page(**_STATES["ignored"][0])
    assert doc.select_one("a.form-page__danger") is not None
    assert doc.select_one('input[name="calendar_url"]') is not None
    assert not doc.select(".calendar-masked-url")


def test_provider_name_derives_from_the_host_and_falls_back_to_it():
    """iCloud hosts read 'iCloud', unknown hosts show themselves, junk shows nothing"""
    name = calendar_settings._provider_name
    assert name("https://p56-caldav.icloud.com/published/2/TOKEN") == "iCloud"
    assert name("webcal://calendar.google.com/calendar/ical/x/basic.ics") == "Google Calendar"
    assert name("https://cal.example.org/feed.ics?token=T") == "cal.example.org"
    assert name("not a url") == ""
    assert name("") == ""


def test_the_full_url_never_reaches_the_browser_in_any_state(tmp_path):
    """a connected, refused-paste, stale and failed render never carry the token, the path, the
    query parameter name or the whole URL: only 'host…' appears, on the connection page"""
    token, host, path, param = "TOKEN-9fq2zz", "p56-caldav.icloud.com", "published/2/PATHSEG", "auth_key"
    url = "https://%s/%s?%s=%s" % (host, path, param, token)
    state = str(tmp_path)
    assert calendar_rules.save_calendar_url(state, url)
    for name in ("ok", "stale", "failed", "zero", "pending"):
        for extra in ({}, {"calendar_sheet_error": "unreachable"}):
            overrides = dict(_STATES[name][0], **extra)
            ctx = _ctx(state_dir=state, **overrides)
            rendered = config_page.render(
                ctx, scope=config_page.SCOPE_DISPLAY, view="calendar-connect")
            assert "%s…" % host in rendered
            listed = config_page.render(ctx, scope=config_page.SCOPE_DISPLAY)
            for needle in (token, path, param, url):
                assert needle not in rendered, (name, extra, needle)
                assert needle not in listed, (name, extra, needle)
            assert "copy" not in rendered.lower().split('class="form-page__card"', 1)[1]


# --- routes -----------------------------------------------------------------

_OLD_URL = "https://old-calendar.example/feed.ics?token=OLDTOKEN"
_NEW_URL = "https://new-calendar.example/feed.ics?token=NEWTOKEN"


def _seed_connected(server, hostnames=("old-calendar.example",)):
    body = cah.ics_body([("AF1234", "CDG", "ORY", 2), ("BA5678", "LHR", "CDG", 4)])
    with cah.stubbed_calendar_transport(cah.make_calendar_transport(body=body)):
        for host in hostnames:
            with cah.fake_public_hostname(host):
                assert calendar_rules.save_calendar_url(server.state_dir, _OLD_URL)
                code, _registry = calendar_rules.refresh_calendar_registry(
                    server.state_dir, datetime.now().timestamp(), min_interval_s=0)
                assert code == calendar_rules.FETCH_OK
    return calendar_rules.load_calendar_registry(server.state_dir)


def _post_connect(server, session, url, transport):
    with cah.stubbed_calendar_transport(transport), cah.fake_public_hostname("new-calendar.example"):
        return http_request(
            server.base_url() + config_page.CALENDAR_CONNECT_ROUTE, method="POST",
            data=urllib.parse.urlencode({"calendar_url": url}).encode(), cookie=session)


def test_replace_reads_the_new_link_before_anything_is_saved(app_server_in_process):
    """the candidate is fetched while the stored link and registry still belong to the old
    calendar; only after it answers is the new link stored and the flights replaced"""
    server = app_server_in_process
    session = login(server)
    _seed_connected(server)
    seen = {}
    new_body = cah.ics_body([("AF9999", "ORY", "NCE", 3)])
    inner = cah.make_calendar_transport(body=new_body)

    def spying_transport(url, timeout):
        seen["stored_during_fetch"] = calendar_rules.configured_calendar_url(server.state_dir)
        seen["entries_during_fetch"] = len(calendar_rules.load_calendar_registry(server.state_dir)["entries"])
        return inner(url, timeout)

    status, headers, _b = _post_connect(server, session, _NEW_URL, spying_transport)
    assert status == 303
    assert "flash=calendar_connect_ok" in headers["Location"]
    assert seen["stored_during_fetch"] == _OLD_URL, "the old link must survive until the new one answered"
    assert seen["entries_during_fetch"] == 2
    assert calendar_rules.configured_calendar_url(server.state_dir) == _NEW_URL
    registry = calendar_rules.load_calendar_registry(server.state_dir)
    assert len(registry["entries"]) == 1 and registry["last_synced_at"]


def test_a_failed_replace_leaves_the_old_link_and_flights_untouched(app_server_in_process):
    """an unreachable replacement redirects back to the connection page with an inline error and
    changes nothing on disk"""
    server = app_server_in_process
    session = login(server)
    before = _seed_connected(server)
    status, headers, _b = _post_connect(
        server, session, _NEW_URL, cah.make_calendar_transport(raise_exc=ConnectionError("boom")))
    assert status == 303
    location = headers["Location"]
    assert location.startswith("/display/calendar/connect?")
    assert "flash=calendar_connect_failed" in location
    assert "calendar_error=unreachable" in location
    assert calendar_rules.configured_calendar_url(server.state_dir) == _OLD_URL
    assert calendar_rules.load_calendar_registry(server.state_dir) == before
    status2, _h2, page = http_request(server.base_url() + location, cookie=session)
    assert status2 == 200
    text = page.decode()
    assert 'aria-invalid="true"' in text
    assert "That link doesn&#x27;t answer. Nothing was changed." in text
    for needle in ("NEWTOKEN", "OLDTOKEN", _NEW_URL, _OLD_URL):
        assert needle not in text


def test_a_non_https_or_empty_paste_is_refused_without_fetching(app_server_in_process):
    """a link the safety gate refuses never reaches the network and changes nothing"""
    server = app_server_in_process
    session = login(server)
    before = _seed_connected(server)
    calls = []
    for url in ("http://new-calendar.example/feed.ics", "ftp://new-calendar.example/x", "", "   ", "not a url"):
        status, headers, _b = _post_connect(
            server, session, url, cah.make_calendar_transport(body=b"", calls=calls))
        assert status == 303
        assert "flash=calendar_connect_invalid" in headers["Location"], url
        assert "calendar_error=invalid" in headers["Location"], url
    assert calls == [], "a refused link is never fetched"
    assert calendar_rules.configured_calendar_url(server.state_dir) == _OLD_URL
    assert calendar_rules.load_calendar_registry(server.state_dir) == before


def test_connecting_a_first_calendar_with_zero_flights_succeeds_and_reads_as_zero(app_server_in_process):
    """a valid feed with no flights connects (the page then shows the zero-flight warning)"""
    server = app_server_in_process
    session = login(server)
    status, headers, _b = _post_connect(
        server, session, _NEW_URL,
        cah.make_calendar_transport(body=b"BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n"))
    assert status == 303 and "flash=calendar_connect_ok" in headers["Location"]
    status2, _h, page = http_request(server.base_url() + "/display/calendar", cookie=session)
    assert 'data-calendar-state="zero"' in page.decode()


def test_the_secret_cannot_be_stored_so_nothing_changes(app_server_in_process, monkeypatch):
    """if the new secret cannot be written after the link answered, the old connection is kept
    and the failure is reported as unreachable-style (nothing changed)"""
    server = app_server_in_process
    session = login(server)
    before = _seed_connected(server)
    monkeypatch.setattr(calendar_rules, "save_calendar_url", lambda *a, **k: False)
    status, headers, _b = _post_connect(
        server, session, _NEW_URL, cah.make_calendar_transport(body=cah.ics_body([("AF1", "CDG", "ORY", 2)])))
    assert status == 303 and "flash=calendar_connect_failed" in headers["Location"]
    monkeypatch.undo()
    assert calendar_rules.configured_calendar_url(server.state_dir) == _OLD_URL
    assert calendar_rules.load_calendar_registry(server.state_dir) == before


def test_disconnect_still_needs_the_server_side_confirmation(app_server_in_process):
    """the no-script path is unchanged: a bare POST renders the confirmation page and keeps the
    link; confirm=yes disconnects and deletes the flights"""
    server = app_server_in_process
    session = login(server)
    _seed_connected(server)
    status, _h, body = http_request(
        server.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE, method="POST",
        data=with_csrf(session), cookie=session)
    assert status == 200 and calendar_rules.calendar_is_configured(server.state_dir)
    status, headers, _b = http_request(
        server.base_url() + config_page.CALENDAR_DISCONNECT_ROUTE, method="POST",
        data=with_csrf(session, {"confirm": "yes"}), cookie=session)
    assert status == 303 and "flash=calendar_disconnected" in headers["Location"]
    assert not calendar_rules.calendar_is_configured(server.state_dir)
    assert calendar_rules.load_calendar_registry(server.state_dir)["entries"] == []


def test_the_connection_page_loads_calendar_connect_js_and_it_is_es5_and_sink_free(
        app_server_in_process):
    """the script is served, loaded on the connection page, ES5-safe, writes no markup and never
    fetches"""
    server = app_server_in_process
    session = login(server)
    _s, _h, page = http_request(server.base_url() + "/display/calendar/connect", cookie=session)
    assert layout.CALENDAR_CONNECT_SCRIPT_SRC in page.decode()
    src = served_asset(server, layout.CALENDAR_CONNECT_SCRIPT_SRC)
    assert src.count('"use strict"') == 1
    for token in ("let ", "const ", "=>", "`", "fetch(", "XMLHttpRequest", "setTimeout", "setInterval",
                  "innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval(",
                  "location.href", "location.assign"):
        assert token not in src, token
    for token in ("data-calendar-connect", "data-pending-label"):
        assert token in src, token
    for token in ("showModal", "data-calendar-confirm", "data-confirm-value"):
        assert token not in src, token
