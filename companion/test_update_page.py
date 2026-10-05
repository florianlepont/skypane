"""Companion Update page tests: the nav entry/icon/French label, and the
served page itself across every update state, the rollback banner, the
version-history table and both languages.

Nav checks call companion.layout's own renderers directly, in-process,
the same pattern companion/test_companion_app_01.py and
companion/test_companion_app_02.py already use for nav-shape checks —
this is the real production render function's output, never source
text. A couple of checks go through a real running companion/app.py
(companion/conftest.py's module_app_server_factory) for genuine
end-to-end proof.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone

import companion.auth as auth
import companion.i18n as i18n
import companion.layout as layout
import companion.page_context as page_context
import companion.prefs as prefs
from companion.pages import update_page
from companion_app_server import get, login
from companion_markup import parse_html, toast_title_detail
from server import atomic_io
from server import firmware_registry as fr

_NOW = "2026-09-28T12:00:00+00:00"


def _ctx(now=_NOW):
    # update_page() itself never reads ctx.state_dir -- every fixture in
    # this module builds its `view` from firmware_registry.update_view()
    # directly, never from a real state_dir -- so a placeholder value is
    # enough; the two real-server checks near the bottom get a genuine
    # tmp_path-backed one from module_app_server_factory instead.
    return {"state_dir": "unused-state-dir", "now": now}


def _release(version, notes=None, installed_at=None, bench=False, published_at=_NOW):
    return {
        "version": version, "sha256": version.replace(".", "").ljust(64, "0")[:64],
        "size": 10, "released_at": published_at, "published_at": published_at,
        "commit": "a" * 40, "notes": notes or [], "bench": bench,
        "installed_at": installed_at or [],
    }


def _view(releases=(), schedule=None, last_outcome=None, device_entry=None, now=_NOW):
    """A `firmware_registry.update_view()` result built from hand-written
    registry/device_report dicts through the real pure function -- never
    a hand-built view dict -- so every test below proves update_page.py's
    own rendering against the real, documented view-model shape.
    """
    registry = fr._default_registry()
    registry["releases"] = list(releases)
    registry["schedule"] = schedule
    registry["last_outcome"] = last_outcome
    device_report = fr._default_device_report()
    if device_entry is not None:
        device_report["devices"]["dev1"] = device_entry
    return fr.update_view(registry, device_report, now)


def test_compute_next_wake_text_never_shows_a_past_time_and_matches_quiet_hours_wording():
    """compute_next_wake_text() returns ("", False) for an overdue (LATE) wake instead of a
    past clock time, and (text, True) for a wake still deferred by quiet hours (HELD) -- the
    same wake.next_wake_status()/frame_state.resolve_state() triple Home's Frame tile
    resolves from, so the two pages can never disagree on whether the wake is already late"""
    device_cfg = {"wake_interval_s": 900, "display_enabled": True, "quiet_hours_enabled": False}
    ctx = page_context.coerce({
        "last_checkin_ts": "2026-01-01T00:00:00+00:00",
        "device_config": device_cfg,
        "now": "2026-01-15T12:00:00+00:00",
    })
    assert update_page.compute_next_wake_text(ctx) == ("", False)

    # The nightly regression config (quiet hours 23:00-07:00, check-in 22:58, clock 02:00,
    # Europe/Paris) that companion/test_view_pages_04.py's own frame_state contract test
    # resolves to STATE_HELD.
    qh_config = {
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    paris = timezone(timedelta(hours=1))
    checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
    clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
    ctx = page_context.coerce({
        "last_checkin_ts": checkin.isoformat(),
        "device_config": qh_config,
        "now": clock.isoformat(),
    })
    text, held = update_page.compute_next_wake_text(ctx)
    assert held is True
    assert text, "expected a formatted clock time, not an empty string, for a held wake"


def test_scheduled_sentence_swaps_to_quiet_hours_wording_when_held():
    """the Scheduled state's sentence and the install confirm page's sentence both use the
    quiet-hours template when wake_held is True"""
    view = _view(
        releases=[_release("fw-v1.0.0")],
        schedule={
            "id": "s1", "version": "fw-v1.0.0", "sha256": "a" * 64,
            "scheduled_at": _NOW, "state": "scheduled", "attempts": 0,
            "failed_at": None, "last_result": None,
        })
    html = update_page.update_page(_ctx(), view, "07:00", wake_held=True)
    assert (i18n.t(update_page.SCHEDULED_SENTENCE_HELD_TEMPLATE) % "07:00") in html
    assert (i18n.t(update_page.SCHEDULED_SENTENCE_TEMPLATE) % "07:00") not in html

    confirm_html = update_page.update_install_confirm_page(
        _ctx(), "fw-v1.0.0", "07:00", wake_held=True)
    assert (i18n.t(update_page.INSTALL_CONFIRM_SENTENCE_HELD_TEMPLATE) % "07:00") in confirm_html


# ==========================================================================
# Task 2: the Update page body (Status and Version history cards)
# ==========================================================================


def test_empty_registry_shows_no_version_reported_and_no_releases_yet():
    """an empty registry/device report renders "No version reported yet" and the Version
    history card's "No releases yet" empty state, no <table"""
    view = _view()
    html = update_page.update_page(_ctx(), view, "")
    assert i18n.t(update_page.NO_VERSION_REPORTED_TEXT) in html
    assert i18n.t(update_page.EMPTY_RELEASES_HEADING_TEXT) in html
    assert i18n.t(update_page.EMPTY_RELEASES_BODY_TEXT) in html
    assert "<table" not in html


def test_empty_registry_never_leaks_the_hard_coded_no_reading_yet_fallback():
    """an empty registry (available state, no reported_at, no state_at) never renders
    concise_timestamp_html()'s own hard-coded, untranslated English "no reading yet"
    fallback -- in either language"""
    view = _view()
    assert view["state"] == "available"
    assert view["state_at"] is None
    assert view["reported_at"] is None
    html_en = update_page.update_page(_ctx(), view, "")
    assert "no reading yet" not in html_en
    try:
        prefs.set_request_prefs(lang="fr")
        html_fr = update_page.update_page(_ctx(), view, "")
    finally:
        prefs.set_request_prefs(lang="en")
    assert "no reading yet" not in html_fr


_NBSP = " "


def _schedule(version, state="scheduled", **extra):
    schedule = {
        "id": "s1", "version": version, "sha256": "a" * 64,
        "scheduled_at": _NOW, "state": state, "attempts": 0,
        "failed_at": None, "last_result": None,
    }
    schedule.update(extra)
    return schedule


def _offered(version):
    return {"seq": 1, "at": _NOW, "kind": "offered", "schedule_id": "s1",
            "token": None, "version": version}


def _device(version, events=()):
    return {"fw_version": version, "reported_at": _NOW, "events": list(events)}


def _fr_html(view, now=_NOW):
    try:
        prefs.set_request_prefs(lang="fr")
        return update_page.update_page(_ctx(now), view, "")
    finally:
        prefs.set_request_prefs(lang="en")


def _cta(html):
    return parse_html(html).select_one("section.update-cta")


def _rows(html):
    """The `<details class="update-row">` nodes keyed by their version."""
    rows = {}
    for details in parse_html(html).select("details.update-row"):
        rows[details.select_one(".update-row__version .mono").text()] = details
    return rows


def _forms(node):
    """`(version, button_class, button_text)` for every Install form in `node`."""
    found = []
    for form in node.select('form[action="%s"]' % update_page.INSTALL_ROUTE):
        button = form.select_one("button")
        version = form.select_one('input[name="version"]').attrs["value"]
        found.append((version, button.attrs.get("class", ""), button.text()))
    return found


QUIET = update_page._QUIET_BUTTON_CLASS


def _running_view(extra_releases=(), installed_at=None, running="fw-v1.0.0"):
    releases = [_release("fw-v1.0.0", installed_at=installed_at)] + list(extra_releases)
    return _view(releases=releases, device_entry=_device(running))


def test_each_situation_renders_one_cta_card_with_its_headline_and_tone():
    """the call-to-action card names the one situation the frame is in -- up to date,
    update available, scheduled, installing, failed -- with its own headline and status
    tone, and there is exactly one such card in every state"""
    newer = _release("fw-v1.1.0", published_at="2026-09-29T09:00:00+00:00")
    cases = {
        "up_to_date": (_running_view(installed_at=[_NOW]), "The frame is up to date", "ok"),
        "available": (_running_view([newer]), "Update available", "neutral"),
        "scheduled": (
            _view(releases=[_release("fw-v1.0.0")], schedule=_schedule("fw-v1.0.0"),
                  device_entry=_device("fw-v0.9.0")),
            "Update scheduled", "neutral"),
        "in_progress": (
            _view(releases=[_release("fw-v1.0.0")], schedule=_schedule("fw-v1.0.0"),
                  device_entry=_device("fw-v0.9.0", [_offered("fw-v1.0.0")])),
            "Installing", "warn"),
        "failed": (
            _view(releases=[_release("fw-v1.0.0")],
                  schedule=_schedule("fw-v1.0.0", state="failed", attempts=3, failed_at=_NOW),
                  device_entry=_device("fw-v0.9.0")),
            "Install failed", "error"),
    }
    for situation, (view, headline, tone) in cases.items():
        html = update_page.update_page(_ctx(), view, "08:14")
        assert len(parse_html(html).select("section.update-cta")) == 1, situation
        card = _cta(html)
        assert card.select_one("h2.update-cta__title").text() == headline, situation
        assert "update-cta--%s" % tone in card.attrs["class"].split(), situation
        assert card.attrs["aria-labelledby"] == card.select_one("h2").attrs["id"], situation


def test_up_to_date_card_shows_the_running_version_and_its_install_time_only():
    """the up-to-date card carries the running version in monospace and one relative
    install time (title = the absolute local date), and no install form, no Install button,
    and no "last contact" line"""
    html = update_page.update_page(
        _ctx(), _running_view(installed_at=["2026-09-28T11:00:00+00:00"]), "")
    card = _cta(html)
    assert card.select_one(".mono").text() == "fw-v1.0.0"
    times = card.select("time[data-relative]")
    assert len(times) == 1
    assert times[0].attrs["title"] == "28 Sep 13:00"
    assert "Installed" in card.text()
    assert not card.select("form") and not card.select("button")
    assert "last contact" not in html.lower()
    fr_html = _fr_html(_running_view(installed_at=["2026-09-28T11:00:00+00:00"]))
    assert "Le cadre est à jour" in _cta(fr_html).text()
    assert "Installée" in _cta(fr_html).text()
    assert "dernier contact" not in fr_html.lower()


def test_up_to_date_card_prints_no_install_time_for_a_usb_flashed_running_release():
    """a running release with no current OTA install shows the version alone, never an
    overtaken or invented install time"""
    view = _running_view(
        [_release("fw-v0.9.0", installed_at=["2026-09-29T15:27:00+00:00"],
                  published_at="2026-09-29T09:00:00+00:00")],
        installed_at=["2026-09-01T09:00:00+00:00"])
    card = _cta(update_page.update_page(_ctx("2026-09-29T16:00:00+00:00"), view, ""))
    assert card.select_one(".mono").text() == "fw-v1.0.0"
    assert not card.select("time") and "Installed" not in card.text()


def test_no_reported_version_card_says_so_and_offers_nothing():
    view = _view(releases=[_release("fw-v1.0.0", installed_at=[_NOW])])
    card = _cta(update_page.update_page(_ctx(), view, ""))
    assert card.select_one("h2").text() == i18n.t(update_page.NO_VERSION_REPORTED_TEXT)
    assert not card.select("form")


def test_newer_release_gets_the_call_to_action_with_the_one_primary_install_button():
    """a release newer than the running one is offered in the card with the accent primary
    Install button (no quiet class), worded with its version, through the same guarded
    form (data-confirm, hidden version, no confirm field)"""
    newer = _release("fw-v1.1.0", notes=["Fixes the panel refresh"],
                     published_at="2026-09-29T09:00:00+00:00")
    html = update_page.update_page(_ctx(), _running_view([newer]), "")
    card = _cta(html)
    assert card.select_one("h2").text() == "Update available"
    assert card.select_one(".mono").text() == "fw-v1.1.0"
    assert "Fixes the panel refresh" in card.text()
    assert len(card.select("time[data-relative]")) == 1
    assert _forms(card) == [("fw-v1.1.0", "", "Install fw-v1.1.0")]
    form = card.select_one("form")
    assert form.attrs["method"] == "post" and "data-confirm" in form.attrs
    assert not form.select('input[name="confirm"]')
    fr_card = _cta(_fr_html(_running_view([newer])))
    assert fr_card.select_one("h2").text() == "Mise à jour disponible"
    assert _forms(fr_card) == [("fw-v1.1.0", "", "Installer fw-v1.1.0")]


def test_an_offer_still_names_what_the_frame_runs_and_when_it_was_installed():
    """while an update is on offer, scheduled or installing, the card's footer names the
    running version and its install time; the up-to-date card does not repeat it"""
    newer = _release("fw-v1.1.0", published_at="2026-09-29T09:00:00+00:00")
    card = _cta(update_page.update_page(
        _ctx(), _running_view([newer], installed_at=["2026-09-28T11:00:00+00:00"]), ""))
    footer = card.select_one(".update-cta__on")
    assert footer.select_one(".mono").text() == "fw-v1.0.0"
    assert footer.text().startswith("On the frame: fw-v1.0.0")
    assert footer.select_one("time[data-relative]").attrs["title"] == "28 Sep 13:00"
    fr_footer = _cta(_fr_html(_running_view([newer]))).select_one(".update-cta__on")
    assert fr_footer.text().startswith("Sur le cadre : fw-v1.0.0")
    assert not _cta(update_page.update_page(_ctx(), _running_view(), "")).select(".update-cta__on")


def test_the_card_offers_the_newest_installable_release_not_an_older_one():
    releases = [
        _release("fw-v1.1.0", published_at="2026-09-10T09:00:00+00:00"),
        _release("fw-v1.2.0", published_at="2026-09-20T09:00:00+00:00"),
    ]
    html = update_page.update_page(_ctx(), _running_view(releases), "")
    assert [version for version, _c, _t in _forms(_cta(html))] == ["fw-v1.2.0"]


def test_older_release_is_worded_as_a_rollback_on_a_quiet_button():
    """an older release reads "Roll back to <version>" ("Revenir à ...") on the quiet
    button, through the same confirmation form; the card does not offer it"""
    view = _view(
        releases=[_release("fw-v1.0.0", published_at="2026-09-10T09:00:00+00:00"),
                  _release("fw-v1.1.0", installed_at=[_NOW])],
        device_entry=_device("fw-v1.1.0"))
    html = update_page.update_page(_ctx(), view, "")
    assert not _cta(html).select("form")
    row = _rows(html)["fw-v1.0.0"]
    assert _forms(row) == [("fw-v1.0.0", QUIET, "Roll back to fw-v1.0.0")]
    form = row.select_one("form")
    assert form.attrs["action"] == update_page.INSTALL_ROUTE and "data-confirm" in form.attrs
    assert not form.select('input[name="confirm"]')
    fr_row = _rows(_fr_html(view))["fw-v1.0.0"]
    assert _forms(fr_row) == [("fw-v1.0.0", QUIET, "Revenir à fw-v1.0.0")]
    assert "Installer" not in fr_row.select_one("form").text()


def test_the_accent_primary_button_is_only_for_installing_a_newer_release():
    """with an older and a newer release beside the running one, every Install form of the
    newer release is the accent primary and every other one is the quiet button"""
    view = _view(
        releases=[_release("fw-v1.0.0", published_at="2026-09-10T09:00:00+00:00"),
                  _release("fw-v1.1.0", installed_at=[_NOW], published_at="2026-09-15T09:00:00+00:00"),
                  _release("fw-v1.2.0", published_at="2026-09-20T09:00:00+00:00")],
        device_entry=_device("fw-v1.1.0"))
    html = update_page.update_page(_ctx(), view, "")
    forms = _forms(parse_html(html))
    primary = {version for version, button_class, _text in forms if not button_class}
    quiet = {version for version, button_class, _text in forms if button_class == QUIET}
    assert primary == {"fw-v1.2.0"} and quiet == {"fw-v1.0.0"}
    assert len(forms) == 3, "the card and the row each carry the newer release's form"


def test_a_row_install_button_is_named_by_its_version_for_assistive_technology():
    newer = _release("fw-v1.1.0", published_at="2026-09-29T09:00:00+00:00")
    html = update_page.update_page(_ctx(), _running_view([newer]), "")
    button = _rows(html)["fw-v1.1.0"].select_one("button")
    assert button.text() == "Install"
    assert button.attrs["aria-label"] == "Install fw-v1.1.0"


def test_every_release_is_listed_in_newest_first_order():
    """the version list holds the whole history, no cut-off, newest published first, with
    its count beside the heading"""
    releases = [
        _release("fw-v1.%d.0" % n, published_at="2026-09-%02dT09:00:00+00:00" % (n + 1))
        for n in range(12)]
    view = _view(releases=releases, device_entry=_device("fw-v1.5.0"))
    html = update_page.update_page(_ctx(), view, "")
    doc = parse_html(html)
    versions = [row.select_one(".update-row__version .mono").text()
                for row in doc.select("details.update-row")]
    assert versions == ["fw-v1.%d.0" % n for n in range(11, -1, -1)]
    assert doc.select_one(".update-versions__count").text() == "12"
    assert doc.select_one("section.update-versions h2").text() == "Versions"
    assert len(doc.select("details.update-row.update-row--running")) == 1


def test_rows_are_native_closed_details_with_one_relative_date_and_the_absolute_inside():
    """each row is a native closed <details>; its summary carries one relative date whose
    title is the absolute local date and time, and the opened body repeats the absolute
    date as a plain <time> that never ticks"""
    release = _release("fw-v1.0.0", notes=["First", "Second"], installed_at=[_NOW],
                       published_at="2026-09-20T09:00:00+00:00")
    release["released_at"] = "2026-09-20T09:00:00+00:00"
    view = _view(releases=[release], device_entry=_device("fw-v1.0.0"))
    row = _rows(update_page.update_page(_ctx(), view, ""))["fw-v1.0.0"]
    assert row.tag == "details" and "open" not in row.attrs
    summary = row.select_one("summary")
    times = summary.select("time[data-relative]")
    assert len(times) == 1 and times[0].attrs["title"] == "20 Sep 11:00"
    assert times[0].attrs["datetime"].startswith("2026-09-20T11:00:00")
    body_times = row.select_one(".update-row__body").select("time")
    assert body_times and all("data-relative" not in time.attrs for time in body_times)
    assert body_times[0].text() == "20 Sep 11:00"
    assert "Released" in row.select_one(".update-row__body").text()


def test_a_previously_installed_release_shows_its_last_installation_in_the_opened_row():
    view = _running_view([_release(
        "fw-v1.1.0", installed_at=["2026-09-28T11:00:00+00:00"],
        published_at="2026-09-29T09:00:00+00:00")])
    row = _rows(update_page.update_page(_ctx(), view, ""))["fw-v1.1.0"]
    meta = [p.text() for p in row.select(".update-row__meta")]
    assert "Last installed 28 Sep 13:00" in meta
    fr_html = _fr_html(view)
    fr_meta = [p.text() for p in _rows(fr_html)["fw-v1.1.0"].select(".update-row__meta")]
    assert "Dernière installation : 28 sept. 13:00" in fr_meta
    assert "Dernière installation%s: " % _NBSP in fr_html
    assert "Last installed" not in fr_html


def test_the_running_row_says_installed_and_a_never_installed_row_does_not():
    view = _running_view(
        [_release("fw-v1.1.0", published_at="2026-09-29T09:00:00+00:00")],
        installed_at=["2026-09-28T11:00:00+00:00"])
    rows = _rows(update_page.update_page(_ctx(), view, ""))
    running_meta = [p.text() for p in rows["fw-v1.0.0"].select(".update-row__meta")]
    assert "Installed 28 Sep 13:00" in running_meta
    never_meta = [p.text() for p in rows["fw-v1.1.0"].select(".update-row__meta")]
    assert not any("nstalled" in text for text in never_meta)


def test_running_badge_is_on_the_running_row_only_and_reads_en_cours_in_french():
    view = _running_view([_release("fw-v1.1.0", published_at="2026-09-29T09:00:00+00:00")])
    rows = _rows(update_page.update_page(_ctx(), view, ""))
    assert [badge.text() for badge in rows["fw-v1.0.0"].select(".update-row__badge")] == ["Running"]
    assert not rows["fw-v1.1.0"].select(".update-row__badge")
    assert "update-row--running" in rows["fw-v1.0.0"].attrs["class"].split()
    fr_rows = _rows(_fr_html(view))
    assert [badge.text() for badge in fr_rows["fw-v1.0.0"].select(".update-row__badge")] == ["En cours"]


def test_no_running_badge_without_a_reported_version():
    view = _view(releases=[_release("fw-v1.0.0", installed_at=[_NOW])])
    html = update_page.update_page(_ctx(), view, "")
    assert not parse_html(html).select(".update-row__badge")
    assert not parse_html(html).select("details.update-row--running")


def test_the_running_release_row_offers_no_action_and_a_below_floor_row_has_no_button():
    registry = fr._default_registry()
    registry["floor_version"] = "fw-v2.0.0"
    registry["releases"] = [_release("fw-v1.0.0")]
    view = fr.update_view(registry, fr._default_device_report(), _NOW)
    html = update_page.update_page(_ctx(), view, "")
    row = _rows(html)["fw-v1.0.0"]
    assert i18n.t(update_page.NOT_INSTALLABLE_TEXT) in row.text()
    assert not row.select("button") and not row.select("form")
    assert update_page.INSTALL_ROUTE not in html
    running = _rows(update_page.update_page(_ctx(), _running_view(), ""))["fw-v1.0.0"]
    assert not running.select("form") and not running.select("button")
    assert i18n.t(update_page.NOT_INSTALLABLE_TEXT) not in running.text()


def test_bench_releases_are_never_offered_but_a_running_bench_build_is_named():
    """a bench release is absent from the list and the card (no Install form for it) while a
    normal release stays; when the frame runs the bench build the card still names it with
    the Bench badge"""
    view = _view(releases=[
        _release("fw-v1.1.0-bench1", bench=True),
        _release("fw-v1.2.0", bench=False),
    ])
    html = update_page.update_page(_ctx(), view, "")
    assert "fw-v1.1.0-bench1" not in html
    assert 'value="fw-v1.1.0-bench1"' not in html
    assert "fw-v1.2.0" in html
    assert i18n.t(update_page.BENCH_BADGE_TEXT) not in html

    running = _view(
        releases=[_release("fw-v1.1.0-bench1", bench=True), _release("fw-v1.2.0")],
        device_entry=_device("fw-v1.1.0-bench1"))
    running_html = update_page.update_page(_ctx(), running, "")
    on_frame = _cta(running_html).select_one(".update-cta__on")
    assert on_frame.select_one(".mono").text() == "fw-v1.1.0-bench1"
    assert on_frame.select_one(".update-cta__bench").text() == i18n.t(update_page.BENCH_BADGE_TEXT)
    assert "fw-v1.1.0-bench1" not in [
        row.select_one(".mono").text() for row in parse_html(running_html).select("details.update-row")]


def test_scheduled_bench_build_is_named_truthfully_but_not_offered():
    view = _view(
        releases=[_release("fw-v1.1.0-bench1", bench=True), _release("fw-v1.2.0")],
        schedule=_schedule("fw-v1.1.0-bench1"))
    html = update_page.update_page(_ctx(), view, "08:14")
    card = _cta(html)
    assert card.select_one(".mono").text() == "fw-v1.1.0-bench1"
    assert "fw-v1.1.0-bench1" not in [
        row.select_one(".mono").text() for row in parse_html(html).select("details.update-row")]


def test_scheduled_state_shows_the_next_wake_sentence_a_quiet_cancel_and_tags_its_row():
    """a scheduled-and-not-yet-offered state names the target and the "installs at the next
    wake" sentence, offers a Cancel form on the quiet class (never the accent primary), and
    that release's row shows a quiet "Scheduled" label while an unrelated release still has
    its Install form"""
    view = _view(
        releases=[_release("fw-v1.0.0"), _release("fw-v1.2.0")],
        schedule=_schedule("fw-v1.0.0"))
    assert view["cancellable"] is True
    html = update_page.update_page(_ctx(), view, "08:14")
    card = _cta(html)
    assert card.select_one("h2").text() == "Update scheduled"
    assert card.select_one(".mono").text() == "fw-v1.0.0"
    assert (i18n.t(update_page.SCHEDULED_SENTENCE_TEMPLATE) % "08:14") in card.text()
    cancel = card.select_one('form[action="%s"] button' % update_page.CANCEL_ROUTE)
    assert cancel.attrs["class"] == QUIET
    rows = _rows(html)
    assert not rows["fw-v1.0.0"].select("form")
    assert i18n.t(update_page.STATE_LABELS["scheduled"]) in rows["fw-v1.0.0"].text()
    assert [version for version, _c, _t in _forms(rows["fw-v1.2.0"])] == ["fw-v1.2.0"]


def test_in_progress_shows_no_cancel_and_no_install_form_anywhere():
    """once the device has acknowledged the offer no Cancel or Install form renders
    anywhere -- posting could only ever come back "busy" -- and the target's row shows a
    quiet "In progress" label"""
    view = _view(
        releases=[_release("fw-v1.0.0"), _release("fw-v1.2.0")],
        schedule=_schedule("fw-v1.0.0"),
        device_entry=_device("fw-v0.9.0", [_offered("fw-v1.0.0")]))
    assert view["state"] == "in_progress" and view["cancellable"] is False
    html = update_page.update_page(_ctx(), view, "08:14")
    assert not parse_html(html).select("form")
    card = _cta(html)
    assert card.select_one("h2").text() == "Installing"
    assert "fw-v1.0.0 is installing" in card.text()
    assert len(card.select("time[data-relative]")) == 1
    assert i18n.t(update_page.STATE_LABELS["in_progress"]) in _rows(html)["fw-v1.0.0"].text()


def test_failed_state_names_the_release_the_frame_stays_on_and_offers_a_retry():
    view = _view(
        releases=[_release("fw-v0.9.0", installed_at=[_NOW]), _release("fw-v1.0.0")],
        schedule=_schedule("fw-v1.0.0", state="failed", attempts=3, failed_at=_NOW),
        device_entry=_device("fw-v0.9.0"))
    assert view["state"] == "failed"
    card = _cta(update_page.update_page(_ctx(), view, "08:14"))
    assert card.select_one("h2").text() == "Install failed"
    assert "fw-v1.0.0 could not be installed." in card.text()
    assert "The frame stays on fw-v0.9.0." in card.text()
    assert _forms(card) == [("fw-v1.0.0", "", "Install fw-v1.0.0")]


def test_scheduled_sentence_swaps_to_quiet_hours_wording_in_the_card():
    view = _view(releases=[_release("fw-v1.0.0")], schedule=_schedule("fw-v1.0.0"))
    card = _cta(update_page.update_page(_ctx(), view, "07:00", wake_held=True))
    assert (i18n.t(update_page.SCHEDULED_SENTENCE_HELD_TEMPLATE) % "07:00") in card.text()


def test_a_rollback_outcome_toast_sits_above_the_card():
    view = _view(
        releases=[_release("fw-v1.3.0", installed_at=[_NOW])],
        last_outcome={
            "kind": "rollback", "version": "fw-v1.4.0", "back_on": "fw-v1.3.0", "at": _NOW},
        device_entry=_device("fw-v1.3.0"))
    html = update_page.update_page(_ctx(), view, "")
    assert html.index("update-rollback") < html.index("update-cta")


def test_notes_summarise_in_the_row_and_list_in_full_when_opened():
    """the closed row shows the first note on its own line; the opened body lists every
    note; a release with no notes renders an empty summary line, never a stray bullet list"""
    notes = ["First note", "Second note", "Third note"]
    view = _view(releases=[_release("fw-v1.0.0", notes=notes), _release(
        "fw-v1.1.0", notes=[], published_at="2026-09-29T09:00:00+00:00")])
    rows = _rows(update_page.update_page(_ctx(), view, ""))
    row = rows["fw-v1.0.0"]
    assert row.select_one("summary .update-row__note").text() == "First note"
    assert [li.text() for li in row.select(".update-row__notes li")] == notes
    empty = rows["fw-v1.1.0"]
    assert empty.select_one("summary .update-row__note").text() == ""
    assert not empty.select(".update-row__notes")


def test_a_long_note_is_kept_whole_for_the_opened_row():
    note = " ".join(["wordy"] * 60)
    view = _view(releases=[_release("fw-v1.0.0", notes=[note])])
    row = _rows(update_page.update_page(_ctx(), view, ""))["fw-v1.0.0"]
    assert row.select_one(".update-row__notes li").text() == note
    assert "…" not in row.text(), "truncation is the stylesheet's job, never the markup's"


def test_notes_and_versions_are_escaped_and_versions_are_monospace():
    hostile = "<script>alert(1)</script>"
    notes = [hostile, 'x" onmouseover="alert(2)']
    html = update_page.update_page(
        _ctx(), _view(releases=[_release("fw-v1.0.0", notes=notes)]), "")
    assert "<script>" not in html and 'onmouseover="alert' not in html
    assert html.count("&lt;script&gt;alert(1)&lt;/script&gt;") == 2
    assert '<span class="mono">fw-v1.0.0</span>' in html


def test_cleaned_release_notes_render_as_plain_sentences():
    """notes cleaned at the source reach the page as the plain sentences they are"""
    notes = ["Refuse to USB-flash an unsigned image", "Report the Wi-Fi RSSI with every check-in"]
    view = _view(releases=[_release("fw-v1.0.0", notes=notes)])
    row = _rows(update_page.update_page(_ctx(), view, ""))["fw-v1.0.0"]
    assert [li.text() for li in row.select(".update-row__notes li")] == notes


def test_empty_registry_shows_the_no_releases_empty_state_and_no_list():
    html = update_page.update_page(_ctx(), _view(), "")
    assert i18n.t(update_page.EMPTY_RELEASES_HEADING_TEXT) in html
    assert not parse_html(html).select("ul.update-rows")
    assert not parse_html(html).select(".update-versions__count")


def test_french_render_translates_every_new_string():
    """under lang="fr" every state/copy string reads in French and no "%s" placeholder is
    left unfilled"""
    view = _view(
        releases=[_release("fw-v1.0.0"), _release("fw-v1.2.0")],
        schedule=_schedule("fw-v1.0.0"))
    html = _fr_html(view)
    for text in ("Mise à jour planifiée", "Planifiée", "Annuler", "Versions", "Installer"):
        assert text in html, text
    assert "%s" not in html
    for english in ("Update scheduled", "Cancel"):
        assert english not in parse_html(html).text()


def test_bench_install_confirm_page_shows_bench_note():
    """the confirm page adds a "This is a bench build" note when is_bench=True, and omits it
    otherwise"""
    with_note = update_page.update_install_confirm_page(
        _ctx(), "fw-v1.1.0-bench1", "08:14", is_bench=True)
    assert i18n.t(update_page.BENCH_CONFIRM_NOTE_TEXT) in with_note
    without_note = update_page.update_install_confirm_page(
        _ctx(), "fw-v1.2.0", "08:14", is_bench=False)
    assert i18n.t(update_page.BENCH_CONFIRM_NOTE_TEXT) not in without_note


def test_rollback_outcome_shows_the_warn_alert_banner():
    """a rollback outcome renders the role="alert" warn banner naming both versions"""
    view = _view(
        releases=[_release("fw-v1.3.0", installed_at=[_NOW])],
        last_outcome={
            "kind": "rollback", "version": "fw-v1.4.0", "back_on": "fw-v1.3.0", "at": _NOW},
        device_entry={"fw_version": "fw-v1.3.0", "reported_at": _NOW, "events": []})
    html = update_page.update_page(_ctx(), view, "")
    expected = i18n.t(update_page.ROLLBACK_SENTENCE_TEMPLATE) % ("fw-v1.4.0", "fw-v1.3.0")
    toast = parse_html(html).select_one(".toast." + update_page.ROLLBACK_TOAST_CLASS)
    assert toast_title_detail(toast) == layout.split_toast_message(expected)
    assert toast.attrs.get("role") == "alert"
    classes = toast.attrs["class"].split()
    assert "toast--warning" in classes and "toast--docked" in classes, (
        "expected a docked warning toast (a persistent state, never the error tone), got %r"
        % classes)



def _seed_update_state(state_dir):
    """A real, disk-backed registry (via firmware_registry.publish_release/
    schedule_release, never a hand-rolled JSON literal) plus a hand-written
    device_report.json -- byos-owned in production, so this module writes
    it directly rather than through firmware_registry's own API."""
    os.makedirs(str(state_dir), exist_ok=True)
    image_path = os.path.join(str(state_dir), "fixture.bin")
    image_bytes = b"fake-firmware-image-bytes"
    with open(image_path, "wb") as fh:
        fh.write(image_bytes)
    manifest = {
        "version": "fw-v1.0.0", "sha256": hashlib.sha256(image_bytes).hexdigest(),
        "size": len(image_bytes), "released_at": _NOW, "commit": "a" * 40,
        "notes": ["initial release"],
    }
    fr.publish_release(str(state_dir), manifest, image_path, now=_NOW)
    fr.schedule_release(str(state_dir), "fw-v1.0.0", None, now=_NOW)
    device_report = {
        "schema": 1, "next_seq": 1,
        "devices": {"dev1": {"fw_version": "fw-v0.9.0", "reported_at": _NOW, "events": []}},
    }
    atomic_io.atomic_write(
        fr.device_report_path(str(state_dir)), json.dumps(device_report))


def test_get_update_without_a_session_redirects_to_login(module_app_server_factory):
    """GET /update without a session redirects to login like every other page"""
    server = module_app_server_factory()
    status, headers, _body = get(server, layout.UPDATE_ROUTE)
    assert status == 303
    assert headers.get("Location", "").startswith("/login")


def test_get_update_end_to_end_renders_the_scheduled_state(module_app_server_factory):
    """a real GET /update, seeded through firmware_registry's own write API plus a
    hand-written device_report.json, serves the Scheduled state with a Cancel form"""
    server = module_app_server_factory(seed=_seed_update_state)
    cookie = login(server)
    status, _headers, body = get(server, layout.UPDATE_ROUTE, cookie=cookie)
    assert status == 200
    text = body.decode("utf-8")
    assert i18n.t(update_page.STATE_LABELS["scheduled"]) in text
    assert 'action="%s"' % update_page.CANCEL_ROUTE in text
    assert "fw-v1.0.0" in text

# ==========================================================================
# Task 1: navigation entry, icon and French nav label
# ==========================================================================


def test_advanced_group_lists_health_device_update_in_order():
    """layout.NAV_GROUPS' Advanced group holds Health, Device, Update, in that order"""
    advanced_routes = [route for route, _label in layout.NAV_GROUPS[1][1]]
    assert advanced_routes == [layout.HEALTH_ROUTE, layout.DEVICE_ROUTE, layout.UPDATE_ROUTE]


def test_sidebar_advanced_group_renders_the_update_link():
    """sidebar_nav() renders an Update link inside the Advanced group, after Health and Device"""
    markup = layout.sidebar_nav("flights")
    group_start = markup.index('class="nav-group nav-group--advanced"')
    group = markup[group_start:]
    assert ('href="%s"' % layout.UPDATE_ROUTE) in group
    health_idx = group.index('href="%s"' % layout.HEALTH_ROUTE)
    device_idx = group.index('href="%s"' % layout.DEVICE_ROUTE)
    update_idx = group.index('href="%s"' % layout.UPDATE_ROUTE)
    assert health_idx < device_idx < update_idx, (
        "expected Health, then Device, then Update inside the Advanced group")


def test_tab_bar_more_sheet_lists_exactly_health_device_update():
    """the bottom tab bar's More sheet holds exactly the Advanced group's three links, in order"""
    device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    doc = layout.page_shell(
        title="T", active="flights", body="<p>b</p>", device_config=device_cfg)
    bar_start = doc.index('<nav class="tab-bar"')
    bar = doc[bar_start:doc.index("</nav>", bar_start)]
    sheet_start = bar.index('<div class="tab-bar__more-panel">')
    sheet = bar[sheet_start:]
    sheet_links = re.findall(r'<a class="mobile-nav__link[^"]*" href="([^"]+)"', sheet)
    advanced_routes = [route for route, _label in layout.NAV_GROUPS[1][1]]
    assert sheet_links == advanced_routes, (
        "expected the More sheet to hold exactly the Advanced group %r, got %r"
        % (advanced_routes, sheet_links))
    # The tab bar still has its existing fixed cells: Update joined the
    # More sheet, it did not become a sixth tab-bar cell.
    everyday_routes = [route for route, _label in layout.NAV_GROUPS[0][1]]
    tab_links = re.findall(r'<a class="tab-bar__link[^"]*" href="([^"]+)"', bar)
    assert tab_links == everyday_routes


def test_update_link_carries_active_state_only_on_the_update_page():
    """the Update link carries the active class and aria-current only when active="update",
    in both the sidebar and the tab bar's More sheet, and only there"""
    device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    doc = layout.page_shell(
        title="Update", active="update", body="<p>b</p>", device_config=device_cfg)
    sidebar_start = doc.index('<nav class="sidebar-nav"')
    sidebar = doc[sidebar_start:doc.index("</nav>", sidebar_start)]
    update_tag_start = sidebar.index('href="%s"' % layout.UPDATE_ROUTE)
    tag_start = sidebar.rfind("<a", 0, update_tag_start)
    tag_end = sidebar.index(">", update_tag_start)
    update_tag = sidebar[tag_start:tag_end]
    assert "sidebar-link--active" in update_tag
    assert 'aria-current="page"' in update_tag
    assert sidebar.count("sidebar-link--active") == 1

    bar_start = doc.index('<nav class="tab-bar"')
    bar = doc[bar_start:doc.index("</nav>", bar_start)]
    summary_start = bar.index("<summary")
    summary_tag = bar[summary_start:bar.index(">", summary_start)]
    assert "tab-bar__link--active" in summary_tag, (
        "expected the More summary to wear the active pill on the Update page")
    assert bar.count('aria-current="page"') == 1


def test_header_dropdown_preferences_panel_gains_no_update_link():
    """the hamburger dropdown's preferences panel holds no /update destination link"""
    doc = layout.page_shell(
        title="T", active="health", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    panel_start = doc.index('id="%s"' % layout.MOBILE_NAV_ID)
    panel = doc[panel_start:doc.index("</header>")]
    assert ('href="%s"' % layout.UPDATE_ROUTE) not in panel
    assert "mobile-nav__link" not in panel


def test_french_nav_label_reads_mise_a_jour():
    """under lang="fr" the Update nav label reads "Mise à jour", never the English "Update", in
    both the sidebar and the tab bar's More sheet"""
    device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    try:
        prefs.set_request_prefs(lang="fr")
        doc = layout.page_shell(
            title="T", active="flights", body="", device_config=device_cfg)
    finally:
        prefs.set_request_prefs(lang="en")
    assert ">Mise à jour<" in doc
    assert ">Update<" not in doc


def test_icon_sprite_has_icon_nav_update_symbol_and_the_link_uses_it():
    """the served icon sprite carries <symbol id="icon-nav-update"> and the Update link's <svg>
    references it via <use href="#icon-nav-update">"""
    doc = layout.page_shell(
        title="T", active="flights", body="<p>b</p>",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    assert '<symbol id="icon-nav-update"' in doc
    sidebar_start = doc.index('<nav class="sidebar-nav"')
    sidebar = doc[sidebar_start:doc.index("</nav>", sidebar_start)]
    update_link_start = sidebar.rfind("<a", 0, sidebar.index('href="%s"' % layout.UPDATE_ROUTE))
    update_link_end = sidebar.index("</a>", update_link_start)
    update_link = sidebar[update_link_start:update_link_end]
    assert 'href="#icon-nav-update"' in update_link


def test_update_route_is_the_third_advanced_entry_end_to_end(module_app_server_factory):
    """a real GET /health (already-live route) served by a real companion/app.py shows the
    Advanced group's sidebar as Health, Device, Update, both in English and in French"""
    server = module_app_server_factory()
    cookie = login(server)
    status, _headers, body = get(server, layout.HEALTH_ROUTE, cookie=cookie)
    assert status == 200
    text = body.decode("utf-8")
    group_start = text.index('class="nav-group nav-group--advanced"')
    group = text[group_start:]
    health_idx = group.index('href="%s"' % layout.HEALTH_ROUTE)
    device_idx = group.index('href="%s"' % layout.DEVICE_ROUTE)
    update_idx = group.index('href="%s"' % layout.UPDATE_ROUTE)
    assert health_idx < device_idx < update_idx

    fr_cookie = cookie + "; %s=fr" % auth.UI_LANG_COOKIE_NAME
    status, _headers, fr_body = get(server, layout.HEALTH_ROUTE, cookie=fr_cookie)
    assert status == 200
    fr_text = fr_body.decode("utf-8")
    assert ">Mise à jour<" in fr_text
