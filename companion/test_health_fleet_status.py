"""Tests the Health page's fleet database fallback anomaly.

byos writes fleet_status.json when it falls back to the legacy device
files; the companion reads only that file (never fleet.db) and shows one
bilingual anomaly sentence with a warn severity for the "fault" state.
"""
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion_app_server  # noqa: E402
import companion.prefs as prefs  # noqa: E402
from companion import auth  # noqa: E402
from companion.pages import health_page  # noqa: E402
from server import fleet_db  # noqa: E402
from server import history_db  # noqa: E402

_NOW = "2026-09-21T12:00:00+00:00"
_SENTENCE = "Fleet database unavailable; using the legacy device files."
_FRENCH = "Base de données de la flotte"


def _seed_healthy_device(state_dir):
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(conn, _NOW, battery_mv=4000)


def _seed(state_dir, status):
    """status: None (no file), a fleet_db state, or "malformed"."""
    os.makedirs(state_dir, exist_ok=True)
    _seed_healthy_device(state_dir)
    if status == "malformed":
        path = os.path.join(state_dir, fleet_db.FLEET_STATUS_FILENAME)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("{not json")
    elif status is not None:
        fleet_db.write_status(state_dir, status, "OperationalError")


# --- unit: collect_anomalies / overall_severity ------------------------------

def test_collect_anomalies_default_is_unchanged():
    base = health_page.collect_anomalies("ok", "ok", "ok", False)
    assert base == []
    assert health_page.collect_anomalies(
        "ok", "ok", "ok", False, fleet_fault=False) == base


def test_collect_anomalies_fleet_fault_appends_sentence_last():
    out = health_page.collect_anomalies(
        "warn", "ok", "ok", False, fleet_fault=True)
    assert out[-1] == _SENTENCE
    assert len(out) == 2


def test_collect_anomalies_fleet_fault_french():
    prefs.set_request_prefs(lang="fr")
    try:
        out = health_page.collect_anomalies(
            "ok", "ok", "ok", False, fleet_fault=True)
    finally:
        prefs.set_request_prefs(lang="en")
    assert len(out) == 1
    assert out[0].startswith(_FRENCH)


def test_overall_severity_fleet_fault_warns_and_never_lowers():
    assert health_page.overall_severity(
        "ok", "ok", "ok", False, fleet_fault=True) == "warn"
    assert health_page.overall_severity(
        "error", "ok", "ok", False, fleet_fault=True) == "error"
    assert health_page.overall_severity(
        "ok", "ok", "ok", False, source_fault=True, fleet_fault=True) == "error"
    assert health_page.overall_severity("ok", "ok", "ok", False) == "ok"


# --- state directory ----------------------------------------------------------

@pytest.mark.parametrize("status", [None, "absent", "ok", "malformed"])
def test_quiet_states_raise_no_anomaly(monkeypatch, tmp_path, status):
    monkeypatch.delenv(health_page.OFFBOX_MARKER_ENV_VAR, raising=False)
    _seed(str(tmp_path), status)
    state = health_page.compute_health_state(str(tmp_path), now=_NOW)
    assert state["anomalies"] == []
    assert state["severity"] == "ok"


def test_fault_state_warns_with_sentence(monkeypatch, tmp_path):
    monkeypatch.delenv(health_page.OFFBOX_MARKER_ENV_VAR, raising=False)
    _seed(str(tmp_path), fleet_db.STATUS_FAULT)
    state = health_page.compute_health_state(str(tmp_path), now=_NOW)
    assert state["anomalies"] == [_SENTENCE]
    assert state["severity"] == "warn"


def test_status_read_failure_degrades_to_no_anomaly(monkeypatch, tmp_path):
    monkeypatch.delenv(health_page.OFFBOX_MARKER_ENV_VAR, raising=False)
    _seed(str(tmp_path), None)

    def boom(_state_dir):
        raise RuntimeError("unreadable")

    monkeypatch.setattr(fleet_db, "read_status", boom)
    state = health_page.compute_health_state(str(tmp_path), now=_NOW)
    assert state["anomalies"] == []


# --- served page ---------------------------------------------------------------

def _fetch_health(make_app_server, status, lang="en"):
    server = make_app_server(seed=lambda d: _seed(d, status))
    cookie = companion_app_server.login(server)
    cookie = "%s; %s=%s" % (cookie, auth.UI_LANG_COOKIE_NAME, lang)
    code, _, body = companion_app_server.get(server, "/health", cookie=cookie)
    assert code == 200
    return body.decode("utf-8")


def test_served_health_page_shows_sentence_for_fault(make_app_server):
    html = _fetch_health(make_app_server, fleet_db.STATUS_FAULT)
    assert _SENTENCE in html


@pytest.mark.parametrize("status", [None, "absent", "malformed"])
def test_served_health_page_silent_otherwise(make_app_server, status):
    html = _fetch_health(make_app_server, status)
    assert _SENTENCE not in html


def test_served_health_page_french_for_fault(make_app_server):
    html = _fetch_health(make_app_server, fleet_db.STATUS_FAULT, lang="fr")
    assert _FRENCH in html
    assert _SENTENCE not in html
