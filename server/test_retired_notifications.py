"""State written by an older version that still carries a stored push-alert
group must keep loading, must never reach a caller, and must be dropped on
the next write; and the poll cycle must never make an outbound push request.

Every check asserts on values a loader returns, bytes on disk or the
recorded calls of a stubbed outbound-request primitive.
"""
import hashlib
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.device_config as device_config  # noqa: E402
import server.firmware_registry as firmware_registry  # noqa: E402
import server.http_fetch as http_fetch  # noqa: E402
import server.net.safe_fetch as safe_fetch  # noqa: E402
import server.poll_cycle as poll_cycle  # noqa: E402
import server.state_store as state_store  # noqa: E402

_LEGACY_TOPIC_URL = "https://push.example/secret-topic"
_LEGACY_GROUP = {
    "topic_url": _LEGACY_TOPIC_URL, "battery_low": True, "frame_silent": True, "lang": "fr"}
_REMAINING_CONFIG_KEYS = 10
RUNNING_VERSION = "fw-v1.0.0"
NEXT_VERSION = "fw-v1.1.0"
NOW = "2026-09-28T12:00:00+00:00"


def _write_config(state_dir, legacy_value):
    with open(device_config.device_config_path(state_dir), "w") as fh:
        json.dump({"theme": "black", "led_enabled": False, "notifications": legacy_value}, fh)


def _read_config_bytes(state_dir):
    with open(device_config.device_config_path(state_dir), "rb") as fh:
        return fh.read()


def _write_poll_state(state_dir, doc):
    with open(os.path.join(state_dir, state_store.POLL_STATE_FILENAME), "w") as fh:
        json.dump(doc, fh)


def _read_poll_state(state_dir):
    with open(os.path.join(state_dir, state_store.POLL_STATE_FILENAME)) as fh:
        return json.load(fh)


@pytest.mark.parametrize("legacy_value", [_LEGACY_GROUP, "a-string", ["a", "list"], 7, None])
def test_a_legacy_device_config_loads_without_surfacing_the_retired_group(tmp_path, legacy_value):
    """a device_config.json still holding a legacy alert value loads with only the ten
    remaining keys, every other stored value intact"""
    _write_config(str(tmp_path), legacy_value)
    cfg = device_config.load_device_config(str(tmp_path))
    assert "notifications" not in cfg, "the legacy group must never reach a caller, got %r" % (cfg,)
    assert len(cfg) == _REMAINING_CONFIG_KEYS, "expected ten keys, got %r" % (sorted(cfg),)
    assert cfg["theme"] == "black"
    assert cfg["led_enabled"] is False


def test_the_next_save_rewrites_the_file_without_the_legacy_group(tmp_path):
    """save_device_config() over a legacy file leaves no legacy key and no stored topic URL
    bytes, while every other field keeps its value"""
    d = str(tmp_path)
    _write_config(d, _LEGACY_GROUP)
    device_config.save_device_config(d, quiet_hours_enabled=True)
    on_disk = _read_config_bytes(d)
    assert b"secret-topic" not in on_disk
    assert b"push.example" not in on_disk
    assert "notifications" not in json.loads(on_disk)
    cfg = device_config.load_device_config(d)
    assert cfg["theme"] == "black"
    assert cfg["led_enabled"] is False
    assert cfg["quiet_hours_enabled"] is True


def test_the_write_path_no_longer_accepts_the_retired_keyword(tmp_path):
    """save_device_config() has no keyword through which the retired group could be written"""
    with pytest.raises(TypeError):
        device_config.save_device_config(str(tmp_path), notifications=dict(_LEGACY_GROUP))


def test_a_legacy_poll_state_loads_cycles_and_is_rewritten_without_the_retired_key(tmp_path):
    """a poll_state.json holding only the legacy dedup sub-dict loads without it, survives a
    hold cycle, and the state the cycle writes leaves that key out"""
    d = str(tmp_path)
    _write_poll_state(d, {"notifications": {"last_battery_sent": True, "last_silent_sent": True}})
    assert "notifications" not in state_store.load_poll_state(d)

    device_config.save_device_config(d, display_enabled=False)
    result = poll_cycle.run_once(state_dir=d)
    assert result is not None
    written = _read_poll_state(d)
    assert written.get("hold_state") == "display_off", "expected the display-off hold, got %r" % (written,)
    assert "notifications" not in written


class _FakeResponse:
    status = 200

    def close(self):
        pass


def _schedule_installed_release(state_dir):
    image = b"firmware-image-" + NEXT_VERSION.encode()
    image_path = os.path.join(state_dir, NEXT_VERSION + ".bin")
    with open(image_path, "wb") as fh:
        fh.write(image)
    manifest = {
        "version": NEXT_VERSION, "sha256": hashlib.sha256(image).hexdigest(),
        "size": len(image), "released_at": "2026-09-28", "commit": "a" * 40, "notes": [],
    }
    firmware_registry.publish_release(state_dir, manifest, image_path, now=NOW)
    firmware_registry.schedule_release(state_dir, NEXT_VERSION, RUNNING_VERSION, now=NOW)
    schedule_id = firmware_registry.load_registry(state_dir)["schedule"]["id"]
    events = [{
        "seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id,
        "token": "installed", "version": NEXT_VERSION}]
    report = {
        "schema": 1, "next_seq": 2,
        "devices": {"aa:bb:cc:dd:ee:ff": {
            "fw_version": RUNNING_VERSION, "reported_at": NOW, "events": events}},
    }
    with open(firmware_registry.device_report_path(state_dir), "w") as fh:
        json.dump(report, fh)


def test_a_cycle_never_makes_an_outbound_push_request(tmp_path, monkeypatch):
    """with the legacy alert group configured, a battery-low transition and a firmware install
    outcome in one cycle produce zero outbound requests, while the battery flag and the
    firmware registry still update"""
    d = str(tmp_path)
    calls = []

    def recorder(*args, **kwargs):
        calls.append((args, kwargs))
        return _FakeResponse()

    # The address gate would otherwise refuse the push before any request was made, which
    # would make this check pass against code that still pushes.
    monkeypatch.setattr(safe_fetch, "url_is_safe", lambda url: True)
    monkeypatch.setattr(http_fetch, "pinned_request", recorder)

    device_config.save_device_config(d, display_enabled=False)
    with open(device_config.device_config_path(d)) as fh:
        stored = json.load(fh)
    stored["notifications"] = dict(_LEGACY_GROUP)
    with open(device_config.device_config_path(d), "w") as fh:
        json.dump(stored, fh)
    with open(os.path.join(d, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": 3400, "received_at": 1.0}, fh)
    _schedule_installed_release(d)

    poll_cycle.run_once(state_dir=d)

    assert calls == [], "expected zero outbound push requests, got %d" % len(calls)
    assert _read_poll_state(d).get("battery_low_active") is True
    registry = firmware_registry.load_registry(d)
    assert registry["schedule"] is None
    assert registry["last_outcome"]["kind"] == "installed"
