#!/usr/bin/env python3
"""Two simulated devices through a real BYOS subprocess: each frame is
authenticated to its own fleet.db row and served from its own directory,
while the live frame keeps its exact legacy behaviour."""
import hashlib
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
for _p in (REPO_ROOT, HERE, os.path.join(REPO_ROOT, "test-support")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import byos_server  # noqa: E402
from skypane_frame_server import FrameServer  # noqa: E402
from skypane_live_state import seed_live_like_state as live_state_seed  # noqa: E402
from skypane_live_state import snapshot_dir  # noqa: E402
from skypane_two_device_fleet import device_headers, seed_two_device_fleet  # noqa: E402

from server import device_dirs, history_db, image_container, panel_format  # noqa: E402

FREEZE_PATH = os.path.join(HERE, "measured_fields_freeze.json")
LIVE_PANEL_BYTES = 960000
SIM_ENV = {"SKYPANE_SIM_HARDWARE": "1"}
# Root files a non-live poll legitimately rewrites: the shared OTA device
# report and its lock file, fleet.db status bookkeeping and the harness's own log.
ROOT_REQUEST_FILES = ("firmware/device_report.json", "firmware/registry.lock", "fleet_status.json", "byos.stdout.log")


@pytest.fixture(autouse=True)
def _gate_on(monkeypatch):
    monkeypatch.setenv("SKYPANE_SIM_HARDWARE", "1")


@pytest.fixture
def fleet(tmp_path):
    return seed_two_device_fleet(str(tmp_path), with_landscape=True)


@pytest.fixture
def served(fleet):
    server = FrameServer(fleet.live.state_dir, env_overrides=SIM_ENV)
    server.start()
    yield fleet, server
    server.stop()


def get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def poll(server, device, extra=None):
    headers = dict(device_headers(device))
    headers.pop("Authorization")
    headers.update(extra or {})
    status, doc = server.display(device.token, headers)
    assert status == 200, doc
    return doc


def panel_of(device):
    with open(os.path.join(device.state_dir, "panel.bin"), "rb") as fh:
        return fh.read()


def path_of(doc):
    return "/" + doc["image_url"].split("/", 3)[3]


def fetch(server, doc):
    return get(server.base_url + path_of(doc))


def device_snapshot(device):
    return snapshot_dir(device.state_dir)


def root_snapshot(live):
    snap = snapshot_dir(live.state_dir)
    return {k: v for k, v in snap.items()
            if not k.startswith("devices" + os.sep)
            and not k.startswith("fleet.db")
            and k not in ROOT_REQUEST_FILES}


# ---- per-device image, hash, url -----------------------------------------


def test_each_device_gets_its_own_image_and_hash(served):
    fleet, server = served
    doc_a = poll(server, fleet.dev_a)
    doc_b = poll(server, fleet.dev_b)
    assert doc_a["image_hash"] == "sha256:" + hashlib.sha256(panel_of(fleet.dev_a)).hexdigest()
    assert doc_b["image_hash"] == "sha256:" + hashlib.sha256(panel_of(fleet.dev_b)).hexdigest()
    assert doc_a["image_hash"] != doc_b["image_hash"]
    digest_a = doc_a["image_hash"].split(":")[1]
    assert doc_a["image_url"].endswith("/img/%s/%s.bin" % (fleet.dev_a.id, digest_a))
    status, body = fetch(server, doc_a)
    assert (status, body) == (200, panel_of(fleet.dev_a))
    assert fetch(server, doc_b) == (200, panel_of(fleet.dev_b))


def test_live_unchanged_url_hash_and_keys_with_other_devices(served):
    fleet, server = served
    with open(os.path.join(fleet.live.state_dir, "panel.bin"), "rb") as fh:
        root_panel = fh.read()
    doc = poll(server, fleet.live)
    digest = hashlib.sha256(root_panel).hexdigest()
    assert doc["image_hash"] == "sha256:" + digest
    assert doc["image_url"].endswith("/img/%s.bin" % digest)
    with open(FREEZE_PATH, encoding="utf-8") as fh:
        frozen = json.load(fh)["display_response_keys"]["keys"]
    assert sorted(doc) == sorted(frozen)
    assert doc["sleep_s"] == 1800
    assert get(server.base_url + "/img/%s.bin" % digest) == (200, root_panel)


def test_non_live_poll_leaves_root_state_and_img_untouched(served):
    fleet, server = served
    before = root_snapshot(fleet.live)
    poll(server, fleet.dev_a)
    poll(server, fleet.dev_b)
    assert root_snapshot(fleet.live) == before
    assert not os.path.exists(os.path.join(fleet.live.state_dir, "img"))
    assert os.listdir(os.path.join(fleet.dev_a.state_dir, "img"))


def test_other_device_untouched_by_a_poll(served):
    fleet, server = served
    before = device_snapshot(fleet.dev_b)
    poll(server, fleet.dev_a)
    assert device_snapshot(fleet.dev_b) == before


# ---- 401 / 503 -----------------------------------------------------------


def test_unknown_token_is_401(served):
    _fleet, server = served
    status, doc = server.display("not-a-token")
    assert status == 401
    assert doc == {"detail": "unknown token"}


def test_mac_without_a_row_is_401_while_fleet_db_is_usable(fleet):
    args = SimpleNamespace(
        state_dir=fleet.live.state_dir, image=os.path.join(fleet.live.state_dir, "panel.bin"))
    result = byos_server._device_context(args, None, "aa:bb:cc:dd:ee:ff")
    assert result is byos_server._NO_DEVICE


def test_tampered_state_path_is_503_and_never_the_live_image(fleet):
    conn = sqlite3.connect(os.path.join(fleet.live.state_dir, "fleet.db"))
    conn.execute("UPDATE devices SET state_path = '../x' WHERE id = ?", (fleet.dev_a.id,))
    conn.commit()
    conn.close()
    server = FrameServer(fleet.live.state_dir, env_overrides=SIM_ENV)
    server.start()
    try:
        status, doc = server.display(fleet.dev_a.token, {"X-Battery-Mv": "3900"})
    finally:
        server.stop()
    assert status == 503
    assert doc == {"detail": "device state unavailable"}


def test_missing_panel_is_503_and_never_the_live_image(served):
    fleet, server = served
    os.remove(os.path.join(fleet.dev_a.state_dir, "panel.bin"))
    status, doc = server.display(fleet.dev_a.token, {"X-Battery-Mv": "3900"})
    assert (status, doc) == (503, {"detail": "image unreadable"})
    assert not os.path.exists(os.path.join(fleet.live.state_dir, "img"))


def test_wrong_size_panel_is_503(served):
    fleet, server = served
    with open(os.path.join(fleet.dev_a.state_dir, "panel.bin"), "wb") as fh:
        fh.write(b"\x00" * 100)
    status, doc = server.display(fleet.dev_a.token)
    assert (status, doc) == (503, {"detail": "image wrong size"})


def test_unavailable_hardware_type_is_503_when_gate_is_off(fleet):
    server = FrameServer(
        fleet.live.state_dir, env_overrides={"SKYPANE_SIM_HARDWARE": "0"})
    server.start()
    try:
        status, doc = server.display(fleet.dev_a.token)
        live_status, _ = server.display(fleet.live.token)
    finally:
        server.stop()
    assert (status, doc) == (503, {"detail": "device state unavailable"})
    assert live_status == 200


def _remove_fleet_db(state_dir):
    for name in ("fleet.db", "fleet.db-wal", "fleet.db-shm"):
        path = os.path.join(state_dir, name)
        if os.path.exists(path):
            os.remove(path)


def _corrupt_fleet_db(state_dir):
    _remove_fleet_db(state_dir)
    with open(os.path.join(state_dir, "fleet.db"), "wb") as fh:
        fh.write(b"this is not a sqlite database" * 20)


def _live_digest(fleet):
    with open(os.path.join(fleet.live.state_dir, "panel.bin"), "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def _display_once(fleet, device, extra=None):
    server = FrameServer(fleet.live.state_dir, env_overrides=SIM_ENV)
    server.start()
    try:
        return server.display(device.token, extra or {})
    finally:
        server.stop()


def test_pre_fleet_install_serves_the_live_frame_unchanged(tmp_path):
    state_dir = str(tmp_path)
    seeded = live_state_seed(state_dir)
    server = FrameServer(state_dir, env_overrides=SIM_ENV)
    server.start()
    try:
        status, doc = server.display(seeded.token, {"X-Battery-Mv": "3900"})
    finally:
        server.stop()
    assert status == 200
    with open(os.path.join(state_dir, "panel.bin"), "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    assert doc["image_hash"] == "sha256:" + digest
    assert doc["image_url"].endswith("/img/%s.bin" % digest)
    assert not os.path.exists(os.path.join(state_dir, "devices"))


@pytest.mark.parametrize("damage", [_remove_fleet_db, _corrupt_fleet_db])
def test_unavailable_fleet_db_refuses_a_non_live_device(fleet, damage):
    damage(fleet.live.state_dir)
    before = snapshot_dir(fleet.live.state_dir)
    status, doc = _display_once(fleet, fleet.dev_a, {"X-Battery-Mv": "3123"})
    assert (status, doc) == (503, {"detail": "device state unavailable"})
    assert "image_url" not in doc
    after = snapshot_dir(fleet.live.state_dir)
    changed = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    assert changed <= {"fleet_status.json", "byos.stdout.log"}
    assert "battery_state.json" not in changed


def test_corrupt_fleet_db_still_serves_the_live_frame(fleet):
    _corrupt_fleet_db(fleet.live.state_dir)
    status, doc = _display_once(fleet, fleet.live, {"X-Battery-Mv": "3900"})
    assert status == 200
    digest = _live_digest(fleet)
    assert doc["image_hash"] == "sha256:" + digest
    assert doc["image_url"].endswith("/img/%s.bin" % digest)


def test_unavailable_fleet_db_without_the_live_record_refuses_everyone(fleet):
    _corrupt_fleet_db(fleet.live.state_dir)
    os.remove(os.path.join(fleet.live.state_dir, device_dirs.LIVE_MACS_FILENAME))
    assert _display_once(fleet, fleet.live)[0] == 503
    assert _display_once(fleet, fleet.dev_a)[0] == 503


def test_unavailable_fleet_db_with_an_unreadable_live_record_refuses_everyone(fleet):
    _corrupt_fleet_db(fleet.live.state_dir)
    record = os.path.join(fleet.live.state_dir, device_dirs.LIVE_MACS_FILENAME)
    with open(record, "w", encoding="utf-8") as fh:
        fh.write("{not json")
    assert _display_once(fleet, fleet.live)[0] == 503
    assert _display_once(fleet, fleet.dev_a)[0] == 503


# ---- negotiation and geometry ---------------------------------------------


def test_negotiation_unannounced_device_gets_raw_profile_size(served):
    fleet, server = served
    doc = poll(server, fleet.landscape)
    status, body = fetch(server, doc)
    assert status == 200
    assert len(body) == (800 // 2) * 480
    assert body == panel_of(fleet.landscape)


def test_negotiation_announcing_device_gets_container_with_profile_size(served):
    fleet, server = served
    doc = poll(server, fleet.landscape, {"X-Img-Fmt": "1"})
    status, body = fetch(server, doc)
    assert status == 200
    view = image_container.decode_container(body, 800, 480)
    assert (view.width, view.height) == (800, 480)
    assert doc["image_hash"] == "sha256:" + hashlib.sha256(body).hexdigest()


def test_negotiation_announcing_clone_gets_full_size_container(served):
    fleet, server = served
    doc = poll(server, fleet.dev_a, {"X-Img-Fmt": "1"})
    _status, body = fetch(server, doc)
    view = image_container.decode_container(body, panel_format.WIDTH, panel_format.HEIGHT)
    assert view.width == panel_format.WIDTH


# ---- sleep, quiet hours, battery -------------------------------------------


def write_config(device, **values):
    with open(os.path.join(device.state_dir, "device_config.json"), "w") as fh:
        json.dump(values, fh)


def test_sleep_is_per_device_and_never_leaks(served):
    fleet, server = served
    write_config(fleet.dev_a, wake_interval_s=600)
    write_config(fleet.dev_b, wake_interval_s=900, display_enabled=False)
    assert poll(server, fleet.dev_a)["sleep_s"] == 600
    assert poll(server, fleet.dev_b)["sleep_s"] == byos_server.DISPLAY_OFF_SLEEP_S
    assert poll(server, fleet.live)["sleep_s"] == 1800


def test_led_flag_is_per_device(served):
    fleet, server = served
    write_config(fleet.dev_a, led_enabled=False)
    assert poll(server, fleet.dev_a)["led_enabled"] is False
    assert poll(server, fleet.dev_b)["led_enabled"] is True
    assert poll(server, fleet.live)["led_enabled"] is True


def test_sleep_quiet_hours_use_each_devices_timezone(tmp_path):
    paris = tmp_path / "paris"
    tokyo = tmp_path / "tokyo"
    for directory, zone in ((paris, "Europe/Paris"), (tokyo, "Asia/Tokyo")):
        directory.mkdir()
        (directory / "device_config.json").write_text(json.dumps({
            "quiet_hours_enabled": True, "quiet_hours_start": "23:00",
            "quiet_hours_end": "07:00", "timezone": zone}))
    now = datetime(2026, 1, 15, 22, 0, tzinfo=timezone.utc)  # 23:00 Paris, 07:00 Tokyo+1
    assert byos_server.read_timezone(str(tokyo)) == ZoneInfo("Asia/Tokyo")
    assert byos_server.quiet_hours_sleep_s(60, str(paris), now=now) == 8 * 3600
    assert byos_server.quiet_hours_sleep_s(60, str(tokyo), now=now) == 60


def test_read_timezone_fails_open(tmp_path):
    assert byos_server.read_timezone(str(tmp_path)) == ZoneInfo("Europe/Paris")
    (tmp_path / "device_config.json").write_text("[1]")
    assert byos_server.read_timezone(str(tmp_path)) == ZoneInfo("Europe/Paris")


def test_battery_report_is_written_to_that_devices_state_only(served):
    fleet, server = served
    root_battery = os.path.join(fleet.live.state_dir, "battery_state.json")
    with open(root_battery, "rb") as fh:
        before = fh.read()
    mtime = os.stat(root_battery).st_mtime_ns
    poll(server, fleet.dev_a, {"X-Battery-Mv": "3777"})
    with open(root_battery, "rb") as fh:
        assert fh.read() == before
    assert os.stat(root_battery).st_mtime_ns == mtime
    with open(os.path.join(fleet.dev_a.state_dir, "battery_state.json")) as fh:
        assert json.load(fh)["battery_mv"] == 3777
    assert not os.path.exists(os.path.join(fleet.dev_b.state_dir, "battery_state.json"))


def test_battery_critical_latch_is_read_from_the_device_directory(served):
    fleet, server = served
    with open(os.path.join(fleet.dev_a.state_dir, "poll_state.json"), "w") as fh:
        json.dump({"battery_critical_active": True}, fh)
    low = {"X-Battery-Mv": "3000"}
    assert poll(server, fleet.dev_a, low)["sleep_s"] == byos_server.BATTERY_CRITICAL_SLEEP_S
    assert poll(server, fleet.dev_b, low)["sleep_s"] != byos_server.BATTERY_CRITICAL_SLEEP_S


# ---- authentication timing shape ---------------------------------------------


def test_authenticate_device_visits_every_candidate(monkeypatch):
    calls = []
    real = byos_server.hmac.compare_digest

    def spy(a, b):
        calls.append(b)
        return real(a, b)

    monkeypatch.setattr(byos_server.hmac, "compare_digest", spy)
    state = {"tokens": {"a": "t1", "b": "t2", "c": "t3"}}
    assert byos_server._authenticate_device(
        {"Authorization": "Bearer t1"}, "/nonexistent-state-dir", state) == "a"
    assert len(calls) == 3
    assert byos_server._authenticate_device(
        {"Authorization": "Bearer zz"}, "/nonexistent-state-dir", state) is None
    assert byos_server._authenticate_device({}, "/nonexistent-state-dir", state) is None


# ---- per-device /img route -------------------------------------------------------


def test_img_route_404_for_cross_device_unknown_live_and_malformed(served):
    fleet, server = served
    doc = poll(server, fleet.dev_a)
    digest = doc["image_hash"].split(":")[1]
    base = server.base_url + "/img/"
    assert get(base + "%s/%s.bin" % (fleet.dev_a.id, digest))[0] == 200
    for path in (
        "%s/%s.bin" % (fleet.dev_b.id, digest),
        "d_00000000/%s.bin" % digest,
        "%s/%s.bin" % (fleet.live.id, digest),
        "d_zzzzzzzz/%s.bin" % digest,
        "%s/../%s.bin" % (fleet.dev_a.id, digest),
        "%s/%s.bin?x=1" % (fleet.dev_a.id, digest),
        "%s/%s.bin" % (fleet.dev_a.id, digest.upper()),
    ):
        status, body = get(base + path)
        assert status == 404, path
        # Paths that match the route shape are "unknown image"; paths that
        # do not match it at all fall through to the generic 404.
        assert json.loads(body)["detail"] in ("unknown image", "unknown endpoint")
    for path in ("%s/%s.bin" % (fleet.dev_b.id, digest), "d_00000000/%s.bin" % digest,
                 "%s/%s.bin" % (fleet.live.id, digest)):
        assert json.loads(get(base + path)[1]) == {"detail": "unknown image"}


def test_img_live_path_never_serves_a_non_live_image(served):
    fleet, server = served
    doc = poll(server, fleet.dev_a)
    digest = doc["image_hash"].split(":")[1]
    status, body = get(server.base_url + "/img/%s.bin" % digest)
    assert status == 404
    assert json.loads(body) == {"detail": "unknown image"}


# ---- per-device health ---------------------------------------------------------------


def health_rows(directory):
    with history_db.open_db(directory) as conn:
        return [dict(row) for row in history_db.recent_device_health(conn)]


def test_health_row_lands_in_the_devices_own_history(served):
    fleet, server = served
    poll(server, fleet.dev_a, {"X-Battery-Mv": "3812"})
    rows = health_rows(fleet.dev_a.state_dir)
    assert len(rows) == 1
    assert rows[0]["battery_mv"] == 3812
    assert rows[0]["fw_version"] == "1.0.0"
    assert rows[0]["boot_reason"] == "timer"
    assert int(rows[0]["rssi"]) == -60
    assert not os.path.exists(os.path.join(fleet.dev_b.state_dir, "history.db"))
    assert not os.path.exists(os.path.join(fleet.live.state_dir, "history.db"))


def test_live_poll_writes_no_health_row(served):
    fleet, server = served
    poll(server, fleet.live)
    assert not os.path.exists(os.path.join(fleet.live.state_dir, "history.db"))


def test_health_write_failure_never_changes_the_response(served):
    fleet, server = served
    os.makedirs(os.path.join(fleet.dev_a.state_dir, "history.db"))
    doc = poll(server, fleet.dev_a)
    assert fetch(server, doc)[0] == 200


# ---- logging ------------------------------------------------------------------------------


def test_output_never_prints_tokens_or_secrets(served):
    fleet, server = served
    poll(server, fleet.dev_a)
    server.display("wrong-token")
    out = server.stdout_text()
    for device in (fleet.live, fleet.dev_a, fleet.dev_b):
        assert device.token not in out
        assert device.secret_hex not in out


def test_image_route_audit_other_endpoints_do_not_serve_shared_state(served):
    fleet, server = served
    status, _ = get(server.base_url + "/device/v1/setup")
    assert status == 404
    status, _ = get(server.base_url + "/img/%s.bin" % ("0" * 64))
    assert status == 404
