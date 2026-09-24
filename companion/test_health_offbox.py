"""companion/test_health_offbox.py — SEC-04/D-07/D-23 (37-02-PLAN.md):
the companion Health page's off-box backup freshness card.

Native pytest (Phase 32's conftest.py fixtures and no-network socket
guard apply automatically to this module) — the same shape
companion/test_login_throttle.py established as the first native
pytest test module under companion/ (37-01-PLAN.md).

Section 1 covers offbox_backup_status() (the marker reader) in
isolation. Section 2 covers the severity/anomaly wiring
(overall_severity()/collect_anomalies()) in isolation. Section 3
covers compute_health_state() end to end against a real (empty)
state directory. Section 4 (Task 2) covers the rendered off-box
backup card, once companion/pages/health_page.py grows
_offbox_section_html().
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import companion.prefs as prefs  # noqa: E402
from companion.pages import health_page  # noqa: E402
from server import history_db  # noqa: E402

OFFBOX_ENV_VAR = health_page.OFFBOX_MARKER_ENV_VAR

_NOW = "2026-09-21T12:00:00+00:00"
_FRESH_MARKER = "skypane-state-20260920T031500Z.tar.gz\n"
_FRESH_SNAPSHOT_TS = "2026-09-20T03:15:00+00:00"
_STALE_NOW = "2026-09-23T04:15:00+00:00"  # snapshot age exactly 3d1h


# --- Section 1: offbox_backup_status() (unit) -----------------------------

def test_offbox_backup_status_none_when_env_unset(monkeypatch):
    monkeypatch.delenv(OFFBOX_ENV_VAR, raising=False)
    assert health_page.offbox_backup_status(_NOW) is None


def test_offbox_backup_status_none_when_env_empty(monkeypatch):
    monkeypatch.setenv(OFFBOX_ENV_VAR, "")
    assert health_page.offbox_backup_status(_NOW) is None


def test_offbox_backup_status_missing_file_warns(monkeypatch, tmp_path):
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(tmp_path / "does-not-exist"))
    assert health_page.offbox_backup_status(_NOW) == {
        "state": "warn", "snapshot_ts": None,
    }


def test_offbox_backup_status_fresh_marker_is_ok(monkeypatch, tmp_path):
    marker = tmp_path / "last-pull"
    marker.write_text(_FRESH_MARKER)
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    assert health_page.offbox_backup_status(_NOW) == {
        "state": "ok", "snapshot_ts": _FRESH_SNAPSHOT_TS,
    }


def test_offbox_backup_status_stale_marker_warns(monkeypatch, tmp_path):
    marker = tmp_path / "last-pull"
    marker.write_text(_FRESH_MARKER)
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    assert health_page.offbox_backup_status(_STALE_NOW) == {
        "state": "warn", "snapshot_ts": _FRESH_SNAPSHOT_TS,
    }


def test_offbox_backup_status_path_traversal_content_warns(monkeypatch, tmp_path):
    marker = tmp_path / "last-pull"
    marker.write_text("../../etc/passwd")
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    assert health_page.offbox_backup_status(_NOW) == {
        "state": "warn", "snapshot_ts": None,
    }


def test_offbox_backup_status_empty_content_warns(monkeypatch, tmp_path):
    marker = tmp_path / "last-pull"
    marker.write_text("")
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    assert health_page.offbox_backup_status(_NOW) == {
        "state": "warn", "snapshot_ts": None,
    }


def test_offbox_backup_status_binary_garbage_warns(monkeypatch, tmp_path):
    marker = tmp_path / "last-pull"
    marker.write_bytes(bytes(range(256)))
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    assert health_page.offbox_backup_status(_NOW) == {
        "state": "warn", "snapshot_ts": None,
    }


def test_offbox_backup_status_huge_file_warns(monkeypatch, tmp_path):
    marker = tmp_path / "last-pull"
    marker.write_bytes(b"a" * 10_000)
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    assert health_page.offbox_backup_status(_NOW) == {
        "state": "warn", "snapshot_ts": None,
    }


def test_offbox_backup_status_reads_env_every_call_not_cached(monkeypatch, tmp_path):
    # D-23 fail-closed contract: the marker path must never be resolved
    # once at import time — a test (or a systemd unit reload) that
    # changes the env var between two calls must see the change.
    monkeypatch.delenv(OFFBOX_ENV_VAR, raising=False)
    assert health_page.offbox_backup_status(_NOW) is None
    marker = tmp_path / "last-pull"
    marker.write_text(_FRESH_MARKER)
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    assert health_page.offbox_backup_status(_NOW) is not None


# --- Section 2: severity/anomaly wiring (unit) -----------------------------

def test_overall_severity_offbox_warn_widens_ok_baseline():
    assert health_page.overall_severity(
        "ok", "ok", "ok", False, offbox_state="warn") == "warn"


def test_overall_severity_offbox_warn_does_not_downgrade_error():
    assert health_page.overall_severity(
        "error", "ok", "ok", False, offbox_state="warn") == "error"
    assert health_page.overall_severity(
        "ok", "ok", "ok", False, source_fault=True, offbox_state="warn") == "error"


def test_overall_severity_default_offbox_state_keeps_prior_results():
    # Every pre-existing 4..6-argument call keeps its exact prior result
    # once offbox_state defaults to "ok".
    assert health_page.overall_severity("ok", "ok", "ok", False) == "ok"
    assert health_page.overall_severity("warn", "ok", "ok", False) == "warn"
    assert health_page.overall_severity("error", "ok", "ok", False) == "error"


def test_collect_anomalies_offbox_stale_with_snapshot():
    anomalies = health_page.collect_anomalies(
        "ok", "ok", "ok", False,
        offbox={"state": "warn", "snapshot_ts": _FRESH_SNAPSHOT_TS})
    assert anomalies == ["No off-box backup in the last 3 days."]


def test_collect_anomalies_offbox_never_pulled():
    anomalies = health_page.collect_anomalies(
        "ok", "ok", "ok", False,
        offbox={"state": "warn", "snapshot_ts": None})
    assert anomalies == ["No off-box backup has been pulled yet."]


def test_collect_anomalies_offbox_ok_is_silent():
    anomalies = health_page.collect_anomalies(
        "ok", "ok", "ok", False,
        offbox={"state": "ok", "snapshot_ts": _FRESH_SNAPSHOT_TS})
    assert anomalies == []


def test_collect_anomalies_offbox_unset_is_silent():
    assert health_page.collect_anomalies("ok", "ok", "ok", False, offbox=None) == []
    assert health_page.collect_anomalies("ok", "ok", "ok", False) == []


# --- Section 3: compute_health_state() (integration) -----------------------

def _seed_healthy_device(state_dir):
    """A single fresh device_health reading at `_NOW`, so device_state
    resolves to "ok" — isolating the off-box signal's own contribution
    to `severity` from the unrelated "no device has ever checked in"
    warning an entirely empty state dir would otherwise carry."""
    with history_db.open_db(state_dir) as conn:
        history_db.record_device_health(conn, _NOW, battery_mv=4000)


def test_compute_health_state_carries_offbox_key_when_unset(monkeypatch, tmp_path):
    monkeypatch.delenv(OFFBOX_ENV_VAR, raising=False)
    _seed_healthy_device(str(tmp_path))
    state = health_page.compute_health_state(str(tmp_path), now=_NOW)
    assert state["offbox"] is None
    assert state["severity"] == "ok"


def test_compute_health_state_offbox_stale_marker_is_warn_never_error(monkeypatch, tmp_path):
    _seed_healthy_device(str(tmp_path))
    marker = tmp_path / "last-pull"
    marker.write_text("skypane-state-20260101T000000Z.tar.gz\n")
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    state = health_page.compute_health_state(str(tmp_path), now=_NOW)
    assert state["offbox"]["state"] == "warn"
    assert state["severity"] == "warn"
    assert "No off-box backup in the last 3 days." in state["anomalies"]


def test_compute_health_state_offbox_fresh_marker_is_ok(monkeypatch, tmp_path):
    _seed_healthy_device(str(tmp_path))
    marker = tmp_path / "last-pull"
    marker.write_text(_FRESH_MARKER)
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    state = health_page.compute_health_state(str(tmp_path), now=_NOW)
    assert state["offbox"]["state"] == "ok"
    assert state["severity"] == "ok"
    assert state["anomalies"] == []


# --- Section 4: rendered off-box backup card (render) -----------------------

def _render(tmp_path):
    return health_page.render({"state_dir": str(tmp_path), "now": _NOW})


def test_render_offbox_hidden_when_env_unset(monkeypatch, tmp_path):
    monkeypatch.delenv(OFFBOX_ENV_VAR, raising=False)
    _seed_healthy_device(str(tmp_path))
    rendered = _render(tmp_path)
    assert "Off-box backup" not in rendered


def test_render_offbox_fresh_marker_ok_card(monkeypatch, tmp_path):
    _seed_healthy_device(str(tmp_path))
    marker = tmp_path / "last-pull"
    marker.write_text(_FRESH_MARKER)
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    rendered = _render(tmp_path)
    assert "Off-box backup" in rendered
    assert "page-section--ok" in rendered
    assert "dot--ok" in rendered
    assert "<time " in rendered
    assert "No off-box backup" not in rendered


def test_render_offbox_stale_marker_warn_card(monkeypatch, tmp_path):
    _seed_healthy_device(str(tmp_path))
    marker = tmp_path / "last-pull"
    marker.write_text("skypane-state-20260101T000000Z.tar.gz\n")
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    rendered = _render(tmp_path)
    assert "page-section--warn" in rendered
    assert "dot--warn" in rendered
    assert "No off-box backup in the last 3 days." in rendered


def test_render_offbox_missing_marker_warn_card_never_text(monkeypatch, tmp_path):
    _seed_healthy_device(str(tmp_path))
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(tmp_path / "does-not-exist"))
    rendered = _render(tmp_path)
    assert "page-section--warn" in rendered
    assert "dot--warn" in rendered
    assert "No off-box backup has been pulled yet." in rendered
    assert "never" in rendered


def test_render_offbox_french(monkeypatch, tmp_path):
    _seed_healthy_device(str(tmp_path))
    marker = tmp_path / "last-pull"
    marker.write_text(_FRESH_MARKER)
    monkeypatch.setenv(OFFBOX_ENV_VAR, str(marker))
    prefs.set_request_prefs(lang="fr")
    try:
        rendered = _render(tmp_path)
    finally:
        prefs.set_request_prefs(lang="en")
    assert "Sauvegarde hors serveur" in rendered
    assert "Off-box backup" not in rendered
