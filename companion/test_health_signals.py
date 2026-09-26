"""Tests for `companion/pages/health_page.py`'s markup-free severity path:
`health_signals()`, `safe_health_signals()` and `health_state_from_signals()`.

Every check calls `health_page`/`wake` directly, in-process; `tmp_path`
subpaths keep every state dir writable even when running as root.
"""
from datetime import timedelta

import pytest

import companion.test_status_pages_helpers as shp
from companion.pages import health_page
import companion.wake as wake
from server import history_db

_DEFAULT_DEVICE_WARN_S, _DEFAULT_DEVICE_ERROR_S = wake.device_staleness_thresholds(None)

# compute_health_state()'s historical key set, restated here (not read
# from source) so a silent key drop/rename fails this test rather than
# only a downstream consumer.
_EXPECTED_KEYS = frozenset((
    "now", "source_fault_raw", "registry_rows", "offbox", "wake_interval_s",
    "device_html", "device_state", "device_detail_html",
    "pipeline_html", "pipeline_state", "pipeline_detail_html",
    "battery_html", "battery_state", "battery_caption",
    "corroboration_html", "disagreement_warn", "anomalies", "severity",
))


# --- Eight severity/anomaly-equivalence scenarios --------------------------

def _seed_fresh_ok(state_dir, now):
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})


def _seed_stale_device(state_dir, now):
    stale_ts = shp.iso(now - timedelta(seconds=_DEFAULT_DEVICE_ERROR_S + 60))
    shp.seed_device_health(state_dir, [(stale_ts, 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})


def _seed_stale_pipeline(state_dir, now):
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    stale_ts = shp.iso(now - timedelta(seconds=health_page.STALE_PIPELINE_ERROR_S + 60))
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: stale_ts})


def _seed_source_fault(state_dir, now):
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{
        history_db.META_LAST_PIPELINE_RUN: shp.iso(now),
        history_db.META_SOURCE_FAULT: "True",
    })


def _seed_battery_drop(state_dir, now):
    shp.seed_device_health(state_dir, [
        (shp.iso(now - timedelta(minutes=1)), 4200),
        (shp.iso(now), 4200 - health_page.BATTERY_DROP_WARN_MV),
    ])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})


def _seed_disagreement(state_dir, now):
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(state_dir, [
        {"ts": shp.iso(now), "hex": "abc123", "corroborated": False}])


def _seed_unresolved_registry(state_dir, now):
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_unresolved_prefixes(state_dir, {
        "ABC": {"count": 1, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })


def _seed_db_unavailable(state_dir, now):
    # Seed a real reading first (creating the on-disk database), then
    # overwrite the file with garbage bytes: every subsequent SQLite
    # read maps to health_page._DB_UNAVAILABLE, the same corrupt-file
    # scenario test_status_pages_01.py's own nav-tab-severity check uses.
    _seed_fresh_ok(state_dir, now)
    db_path = history_db.history_db_path(state_dir)
    with open(db_path, "wb") as handle:
        handle.write(b"not a sqlite file at all")


_SCENARIOS = (
    ("fresh_ok", _seed_fresh_ok),
    ("stale_device", _seed_stale_device),
    ("stale_pipeline", _seed_stale_pipeline),
    ("source_fault", _seed_source_fault),
    ("battery_drop", _seed_battery_drop),
    ("disagreement", _seed_disagreement),
    ("unresolved_registry", _seed_unresolved_registry),
    ("db_unavailable", _seed_db_unavailable),
)


@pytest.mark.parametrize("name,seed_fn", _SCENARIOS, ids=[name for name, _fn in _SCENARIOS])
def test_health_signals_severity_and_anomalies_match_compute_health_state(tmp_path, name, seed_fn):
    """For every seeded scenario, health_signals()'s severity and anomaly
    list equal compute_health_state()'s, computed from the same `now`."""
    now = shp.now()
    now_iso = shp.iso(now)
    state_dir = str(tmp_path / name)
    seed_fn(state_dir, now)

    signals = health_page.health_signals(state_dir, now=now_iso)
    state = health_page.compute_health_state(state_dir, now=now_iso)

    assert signals["now"] == now_iso == state["now"], (
        "expected both computations to carry the same `now` for scenario %r" % name)
    assert signals["severity"] == state["severity"], (
        "expected health_signals() and compute_health_state() to agree on severity for "
        "scenario %r, got %r vs %r" % (name, signals["severity"], state["severity"]))
    assert signals["anomalies"] == state["anomalies"], (
        "expected health_signals() and compute_health_state() to agree on anomalies for "
        "scenario %r, got %r vs %r" % (name, signals["anomalies"], state["anomalies"]))


# --- No-markup guarantee ----------------------------------------------------

def _assert_no_markup(value, path):
    if isinstance(value, str):
        assert "<" not in value, (
            "expected no markup anywhere in health_signals()'s return value, found '<' "
            "at %s: %r" % (path, value))
    elif isinstance(value, dict):
        for key, sub in value.items():
            _assert_no_markup(sub, "%s[%r]" % (path, key))
    elif isinstance(value, (list, tuple)):
        for index, sub in enumerate(value):
            _assert_no_markup(sub, "%s[%d]" % (path, index))


def test_health_signals_builds_no_markup(tmp_path, monkeypatch):
    """health_signals() never calls a markup builder: with every _x_section
    builder and *_timestamp_only helper monkeypatched to raise, it still
    returns successfully, and none of its values carries a '<' character."""
    def _boom(*_args, **_kwargs):
        raise AssertionError("health_signals() must never call a markup builder")

    for name in (
        "_device_section", "_pipeline_section", "_battery_section",
        "_corroboration_section", "_device_timestamp_only", "_pipeline_timestamp_only",
    ):
        monkeypatch.setattr(health_page, name, _boom)

    now = shp.now()
    state_dir = str(tmp_path)
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})

    signals = health_page.health_signals(state_dir, now=shp.iso(now))
    _assert_no_markup(signals, "signals")


# --- compute_health_state()'s key set and its composition ------------------

def test_compute_health_state_key_set_and_composition_unchanged(tmp_path):
    """compute_health_state() still returns exactly its historical key set,
    and is exactly health_state_from_signals(health_signals(...))'s output
    — checked on an unseeded state dir, where every section takes its
    deterministic empty/never-ran path with no wall-clock-dependent text."""
    now_iso = shp.iso(shp.now())
    state_dir = str(tmp_path)

    state = health_page.compute_health_state(state_dir, now=now_iso)
    assert set(state.keys()) == _EXPECTED_KEYS, (
        "expected compute_health_state()'s key set to stay %r, got %r"
        % (sorted(_EXPECTED_KEYS), sorted(state.keys())))

    composed = health_page.health_state_from_signals(
        health_page.health_signals(state_dir, now=now_iso))
    assert composed == state, (
        "expected compute_health_state() to equal "
        "health_state_from_signals(health_signals(...)) for the same inputs")


# --- safe_health_signals()'s fail-closed wrapper ----------------------------

def test_safe_health_signals_returns_none_on_read_failure(tmp_path, monkeypatch):
    """safe_health_signals() returns None (never raises) when the one
    underlying read, _read_health_inputs(), raises."""
    def _raise(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(health_page, "_read_health_inputs", _raise)
    assert health_page.safe_health_signals(str(tmp_path)) is None


# --- Frame-strip / freshness-token fields -----------------------------------

def test_health_signals_exposes_next_wake_triple(tmp_path):
    """health_signals() publishes next_wake_iso/effective_interval_s/
    hold_reason directly, the same triple wake.next_wake_status() returns,
    for a caller (the frame strip, and later the freshness token) that
    needs them without building any markup."""
    now = shp.now()
    state_dir = str(tmp_path)
    shp.seed_device_health(state_dir, [(shp.iso(now), 4200)])
    shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})

    signals = health_page.health_signals(state_dir, now=shp.iso(now))
    for key in ("next_wake_iso", "effective_interval_s", "hold_reason"):
        assert key in signals, "expected health_signals() to carry a %r key" % key
