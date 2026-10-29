#!/usr/bin/env python3
"""The field-validation freeze list, enforced by running code.

stub-server/measured_fields_freeze.json names what the on-wall field
validation measures: wake cadence, battery telemetry, the poll-state fields
and the served image hash. These tests compare that file with a real
stub-server/byos_server.py subprocess, the policy constants and a real poll
cycle, so a deploy that changes a measured field fails here. The list may
only change with the owner's agreement.

The second half replays a poll before and after the fleet migration, with a
new byos process and the same token, and proves the response (image hash,
sleep_s and every other field) is identical, a re-run of the migration
changes nothing, and the frame's credentials survive untouched.

Limit: the replayed state is a sanitised synthetic copy shaped like the
production state directory, because the real VPS state files are not
available to the repository. An owner-exported sanitised copy can replace it
by setting SKYPANE_LIVE_STATE_COPY (see test-support/skypane_live_state.py).
"""
import hashlib
import importlib.util
import json
import os
import re
import sqlite3
import sys
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import efficiency_probe  # noqa: E402
from server import device_policy, fleet_db, fleet_migrate, state_store  # noqa: E402
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state, snapshot_dir  # noqa: E402

FREEZE_PATH = os.path.join(HERE, "measured_fields_freeze.json")
OWNER = "owner@example.com"
POLL_HEADERS = {
    "X-Battery-Mv": "3900",
    "X-Fw-Version": "1.0.0",
    "X-Boot-Reason": "timer",
    "X-Rssi": "-60",
}
LEGACY_IDENTITY_FILES = ("devices.json", "byos_state.json", "device_config.json")
# A raw aggregator-shaped record inside the tracked runway's bounding box,
# climbing fast enough to resolve to a confirmed departure on one cycle.
FLIGHT_RECORD = {
    "hex": "39a1b2", "flight": "AFR123  ", "lat": 48.7233, "lon": 2.3794,
    "alt_baro": 450, "gs": 137.1, "baro_rate": 1500, "seen_pos": 1.0,
}


def load_freeze():
    with open(FREEZE_PATH, encoding="utf-8") as fh:
        return json.load(fh)


FREEZE = load_freeze()


def diff_against_freeze(section_name, frozen, observed):
    """Human-readable differences between a frozen section and the observed
    value; an empty list means they match."""
    note = FREEZE.get(section_name, {}).get("measured_by", "")
    tail = " [measured by: %s; the freeze list changes only with the owner's agreement]" % note
    if isinstance(frozen, dict) and isinstance(observed, dict):
        return _diff_mapping(section_name, frozen, observed, tail)
    if isinstance(frozen, list) and isinstance(observed, list):
        return _diff_sequence(section_name, frozen, observed, tail)
    if frozen != observed:
        return ["%s: frozen %r but observed %r%s" % (section_name, frozen, observed, tail)]
    return []


def _diff_mapping(section_name, frozen, observed, tail):
    out = []
    for key in sorted(set(frozen) | set(observed)):
        if key not in observed:
            out.append("%s: %s was removed%s" % (section_name, key, tail))
        elif key not in frozen:
            out.append("%s: %s was added%s" % (section_name, key, tail))
        elif frozen[key] != observed[key]:
            out.append("%s: %s changed from %r to %r%s"
                       % (section_name, key, frozen[key], observed[key], tail))
    return out


def _diff_sequence(section_name, frozen, observed, tail):
    out = []
    for item in sorted(set(frozen) - set(observed)):
        out.append("%s: %s was removed%s" % (section_name, item, tail))
    for item in sorted(set(observed) - set(frozen)):
        out.append("%s: %s was added%s" % (section_name, item, tail))
    return out


def assert_matches_freeze(section_name, frozen, observed):
    problems = diff_against_freeze(section_name, frozen, observed)
    assert not problems, "\n".join(problems)


def load_byos_module():
    spec = importlib.util.spec_from_file_location(
        "byos_server_freeze", os.path.join(HERE, "byos_server.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _no_sim(monkeypatch):
    monkeypatch.delenv("SKYPANE_SIM_HARDWARE", raising=False)


@pytest.fixture
def servers():
    started = []

    def make(state_dir):
        server = FrameServer(state_dir)
        started.append(server)
        server.start()
        return server

    yield make
    for server in started:
        server.stop()


def read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path, doc):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(doc, fh)


def sha_of_file(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def fetch_bytes(url):
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


# --- the comparison helper itself ------------------------------------------


def test_every_section_names_its_measurement():
    sections = [name for name in FREEZE if name != "description"]
    assert sections
    for name in sections:
        assert FREEZE[name]["measured_by"].strip(), name
    assert "owner" in FREEZE["description"]


def test_diff_detects_a_removed_added_or_changed_field():
    keys = FREEZE["battery_state_keys"]["keys"]
    removed = diff_against_freeze("battery_state_keys", keys, keys[:-1])
    assert removed and "battery_state_keys" in removed[0] and "owner" in removed[0]
    assert diff_against_freeze("battery_state_keys", keys, keys + ["extra"])
    constants = dict(FREEZE["wake_constants"]["values"])
    assert diff_against_freeze("wake_constants", constants, dict(constants)) == []
    constants["WAKE_INTERVAL_MIN_S"] += 1
    changed = diff_against_freeze(
        "wake_constants", FREEZE["wake_constants"]["values"], constants)
    assert changed and "wake_constants" in changed[0]
    assert diff_against_freeze("display_response_values", True, False)


# --- served display response ------------------------------------------------


@pytest.fixture
def served(tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    return live, servers(live.state_dir)


def test_display_response_keys_equal_the_freeze_list(served):
    live, server = served
    status, doc = server.display(live.token, POLL_HEADERS)
    assert status == 200
    assert_matches_freeze(
        "display_response_keys", FREEZE["display_response_keys"]["keys"], sorted(doc))


def test_display_response_values_and_image_hash(served):
    live, server = served
    frozen = FREEZE["display_response_values"]
    _status, doc = server.display(live.token, POLL_HEADERS)
    image = fetch_bytes(doc["image_url"])
    with open(os.path.join(live.state_dir, "panel.bin"), "rb") as fh:
        assert image == fh.read()
    digest = hashlib.sha256(image).hexdigest()
    observed = {
        "image_hash_prefix": doc["image_hash"][:len(frozen["image_hash_prefix"])],
        "image_hash_is_sha256_of_served_image":
            doc["image_hash"] == frozen["image_hash_prefix"] + digest,
        "image_url_path_template":
            re.sub(r"^https?://[^/]+", "", doc["image_url"]).replace(digest, "{sha256}"),
        "reset": doc["reset"],
        "firmware": doc["firmware"],
        "led_enabled": doc["led_enabled"],
    }
    expected = {k: v for k, v in frozen.items() if k != "measured_by"}
    assert_matches_freeze("display_response_values", expected, observed)


# --- telemetry headers -------------------------------------------------------

PROBE_HEADERS = {
    "X-Battery-Mv": "3900",
    "X-Fw-Version": "1.0.0",
    "X-Boot-Reason": "timer",
    "X-Rssi": "-60",
    "X-Ota-Result": "installed;1.0.0",
    "X-Unlisted-Probe": "zzz",
}


def probe_effects(server, live, header, value):
    """Which stores and the log a single request header reaches."""
    battery_path = os.path.join(live.state_dir, "battery_state.json")
    report_path = os.path.join(live.state_dir, "firmware", "device_report.json")
    before = (sha_of_file(battery_path), sha_of_file(report_path), len(server.stdout_text()))
    assert server.display(live.token, {header: value})[0] == 200
    after_log = server.stdout_text()[before[2]:]
    return {
        "battery_state": sha_of_file(battery_path) != before[0],
        "device_report": sha_of_file(report_path) != before[1],
        "logged": ("%s=%s" % (header, value)) in after_log,
    }


def test_telemetry_headers_reach_exactly_the_frozen_places(served):
    live, server = served
    frozen = FREEZE["telemetry_request_headers"]
    effects = {h: probe_effects(server, live, h, v) for h, v in PROBE_HEADERS.items()}
    parsed = sorted(h for h, e in effects.items() if any(e.values()))
    assert_matches_freeze("telemetry_request_headers", frozen["headers"], parsed)
    for key, field in (("stored_in_battery_state", "battery_state"),
                       ("stored_in_device_report", "device_report")):
        observed = sorted(h for h, e in effects.items() if e[field])
        assert_matches_freeze("telemetry_request_headers", frozen[key], observed)
    logged_only = sorted(
        h for h, e in effects.items()
        if e["logged"] and not e["battery_state"] and not e["device_report"])
    assert_matches_freeze("telemetry_request_headers", frozen["logged_only"], logged_only)
    assert effects["X-Unlisted-Probe"] == {
        "battery_state": False, "device_report": False, "logged": False}


def test_battery_state_has_exactly_the_frozen_keys(served):
    live, server = served
    server.display(live.token, {"X-Battery-Mv": "3900"})
    doc = read_json(os.path.join(live.state_dir, "battery_state.json"))
    assert doc["battery_mv"] == 3900
    assert_matches_freeze(
        "battery_state_keys", FREEZE["battery_state_keys"]["keys"], sorted(doc))


# --- poll state and wake constants ------------------------------------------


def test_poll_state_keys_after_a_detected_flight(tmp_path, fake_providers):
    state_dir = str(tmp_path)
    records = {"adsbfi": [FLIGHT_RECORD], "adsblol": [FLIGHT_RECORD]}
    result = efficiency_probe.cycle_probe(state_dir, latency_s=0, records=records)
    assert result["state"] == "departing"
    observed = sorted(state_store.load_poll_state(state_dir))
    assert_matches_freeze("poll_state_keys", FREEZE["poll_state_keys"]["keys"], observed)


def test_wake_constants_match_policy_and_byos_aliases():
    frozen = FREEZE["wake_constants"]["values"]
    observed = {name: getattr(device_policy, name, None) for name in frozen}
    assert_matches_freeze("wake_constants", frozen, observed)
    byos = load_byos_module()
    aliased = {name: getattr(byos, name) for name in frozen if hasattr(byos, name)}
    assert aliased
    expected = {name: frozen[name] for name in aliased}
    assert_matches_freeze("wake_constants", expected, aliased)


def quiet_window_covering_now():
    now = datetime.now(ZoneInfo("Europe/Paris"))
    return ((now - timedelta(hours=1)).strftime("%H:%M"),
            (now + timedelta(hours=2)).strftime("%H:%M"))


def prepare_scenario(state_dir, scenario):
    config_path = os.path.join(state_dir, "device_config.json")
    config = scenario["device_config"]
    if config is None:
        os.unlink(config_path)
    else:
        config = dict(config)
        if config.pop("quiet_hours_window", None) == "covering_now":
            config["quiet_hours_start"], config["quiet_hours_end"] = quiet_window_covering_now()
        write_json(config_path, config)
    if scenario["poll_state"] is not None:
        state_store.save_poll_state(state_dir, scenario["poll_state"])


@pytest.mark.parametrize(
    "scenario", FREEZE["sleep_scenarios"]["scenarios"], ids=lambda s: s["name"])
def test_sleep_scenarios_serve_the_frozen_sleep_s(scenario, tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    prepare_scenario(live.state_dir, scenario)
    server = servers(live.state_dir)
    status, doc = server.display(live.token, scenario["headers"])
    assert status == 200
    if "expect_sleep_s" in scenario:
        assert_matches_freeze(
            "sleep_scenarios", {scenario["name"]: scenario["expect_sleep_s"]},
            {scenario["name"]: doc["sleep_s"]})
    else:
        minimum = scenario["expect_min_sleep_s"]
        assert doc["sleep_s"] >= minimum, (
            "sleep_scenarios: %s served %r, below the frozen minimum %r [measured by: %s]"
            % (scenario["name"], doc["sleep_s"], minimum, FREEZE["sleep_scenarios"]["measured_by"]))


# --- replay across the fleet migration --------------------------------------


def normalise_display(doc, port):
    """The response with the per-process host and port removed."""
    out = dict(doc)
    out["image_url"] = doc["image_url"].replace("127.0.0.1:%d" % port, "HOST")
    return out


def migrate(state_dir):
    assert fleet_migrate.main(["--state-dir", state_dir, "--owner-email", OWNER]) == 0


def poll_normalised(server, token, headers=POLL_HEADERS):
    status, doc = server.display(token, headers)
    assert status == 200
    return normalise_display(doc, server.port), fetch_bytes(doc["image_url"])


def replay_across_migration(live, servers, headers=POLL_HEADERS):
    """Poll with process A, migrate, poll the same token with a new process B."""
    server_a = servers(live.state_dir)
    before = poll_normalised(server_a, live.token, headers)
    server_a.stop()
    legacy = snapshot_dir(live.state_dir)
    migrate(live.state_dir)
    server_b = servers(live.state_dir)
    after = poll_normalised(server_b, live.token, headers)
    return before, after, legacy, server_b


def test_replay_response_is_identical_after_migration(tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    before, after, legacy, server_b = replay_across_migration(live, servers)
    assert after[0] == before[0]
    assert after[0]["image_hash"] == before[0]["image_hash"]
    assert after[1] == before[1]
    assert not [ln for ln in server_b.stdout_text().splitlines() if ln.startswith("setup:")]
    now = snapshot_dir(live.state_dir)
    for name in LEGACY_IDENTITY_FILES:
        assert now[name] == legacy[name], name


def test_replay_keeps_the_frame_credentials(tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    registry = read_json(live.devices_path)["devices"]
    secret_hash = registry[live.mac]["secret_sha256"]
    replay_across_migration(live, servers)
    conn = fleet_db.connect_readonly(live.state_dir)
    try:
        row = fleet_db.get_device_by_mac(conn, live.mac)
        assert row["secret_sha256"] == secret_hash
        assert row["token"] == live.token
        assert row["state_path"] == "."
    finally:
        conn.close()


@pytest.mark.parametrize("variant", ["saved_interval", "battery_parked"])
def test_replay_sleep_s_survives_migration(variant, tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    if variant == "saved_interval":
        write_json(os.path.join(live.state_dir, "device_config.json"), {"wake_interval_s": 900})
    else:
        state_store.save_poll_state(live.state_dir, {"battery_critical_active": True})
    headers = dict(POLL_HEADERS, **{"X-Battery-Mv": "3200"}) if variant == "battery_parked" else POLL_HEADERS
    before, after, _legacy, _server = replay_across_migration(live, servers, headers)
    assert after[0] == before[0]
    expected = 900 if variant == "saved_interval" else device_policy.BATTERY_CRITICAL_SLEEP_S
    assert after[0]["sleep_s"] == expected


def test_previous_release_readers_still_accept_the_migrated_state(tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    replay_across_migration(live, servers)
    byos = load_byos_module()
    registry = byos.load_registry(live.state_dir)
    assert live.mac in registry["devices"]
    if live.secret_hex is not None:
        assert byos.secret_matches(registry, live.mac, live.secret_hex)
    assert byos.load_state(live.state_dir)["tokens"][live.mac] == live.token


def fleet_db_main_file(state_dir):
    path = fleet_db.fleet_db_path(state_dir)
    return sha_of_file(path), os.stat(path).st_mtime_ns


def test_migration_reruns_change_nothing(tmp_path, servers):
    live = seed_live_like_state(str(tmp_path))
    legacy = snapshot_dir(live.state_dir)
    migrate(live.state_dir)
    server_b = servers(live.state_dir)
    first = poll_normalised(server_b, live.token)
    db_before = fleet_db_main_file(live.state_dir)
    for _ in range(2):
        migrate(live.state_dir)
    now = snapshot_dir(live.state_dir)
    for name in ("devices.json", "byos_state.json"):
        assert now[name] == legacy[name], name
    assert fleet_db_main_file(live.state_dir) == db_before
    assert poll_normalised(server_b, live.token) == first


def test_fleet_db_row_matches_the_legacy_files(tmp_path):
    live = seed_live_like_state(str(tmp_path))
    legacy_hash = read_json(live.devices_path)["devices"][live.mac]["secret_sha256"]
    legacy_token = read_json(live.state_path)["tokens"][live.mac]
    migrate(live.state_dir)
    conn = sqlite3.connect(fleet_db.fleet_db_path(live.state_dir))
    try:
        row = conn.execute(
            "SELECT secret_sha256, token, state_path FROM devices WHERE mac = ?",
            (live.mac,)).fetchone()
    finally:
        conn.close()
    assert row == (legacy_hash, legacy_token, ".")
