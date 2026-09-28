"""Cycle-level tests for the firmware reconcile step server/poll_cycle.py
runs every poll cycle: folding server/firmware_registry.py's
apply_reconcile() into the registry, and firing exactly one push
notification per installed/failed outcome.

Every test drives the real run_once() cycle body with display_enabled set
to False, so it takes the display-off hold branch and never needs any
live ADS-B/adsbdb network seam stubbed here - this doubles as the
plan's own requirement that the reconcile step runs inside every hold
branch, parametrised at the end of this file for the other two hold
kinds (quiet hours, battery-empty).
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
import server.poll_cycle as poll_cycle  # noqa: E402

RUNNING_VERSION = "fw-v1.0.0"
NEXT_VERSION = "fw-v1.1.0"
NOW = "2026-09-28T12:00:00+00:00"
_NOTIFY_TOPIC_URL = "https://ntfy.sh/skypane-test-topic"


# The tests below never perform a real POST - every one injects this fake
# in place of server.notify.send_notification, recording each call's
# (topic_url, title, body) rather than reaching a network. Matches
# server/test_poll_loop.py's own _FakeSender idiom.
class _FakeSender:
    def __init__(self, result=True, raises=None):
        self.calls = []
        self.result = result
        self.raises = raises

    def __call__(self, topic_url, title, body, timeout=5, transport=None):
        self.calls.append((topic_url, title, body))
        if self.raises is not None:
            raise self.raises
        return self.result


def _mkdir(base, name):
    path = base / name
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _image_bytes(version):
    return b"firmware-image-" + version.encode()


def _publish(state_dir, version=NEXT_VERSION):
    image = _image_bytes(version)
    image_path = os.path.join(state_dir, version + ".bin")
    with open(image_path, "wb") as fh:
        fh.write(image)
    manifest = {
        "version": version, "sha256": hashlib.sha256(image).hexdigest(),
        "size": len(image), "released_at": "2026-09-28", "commit": "a" * 40,
        "notes": [],
    }
    firmware_registry.publish_release(state_dir, manifest, image_path, now=NOW)


def _schedule(state_dir, version=NEXT_VERSION, running=RUNNING_VERSION):
    _publish(state_dir, version)
    firmware_registry.schedule_release(state_dir, version, running, now=NOW)
    doc = firmware_registry.load_registry(state_dir)
    return doc["schedule"]["id"]


def _write_battery_state(state_dir, mv):
    """Hand-write battery_state.json the way stub-server/byos_server.py's
    save_battery_state() would - matches server/test_poll_loop.py's own
    helper, used here only to force the battery-empty hold branch.
    """
    with open(os.path.join(state_dir, "battery_state.json"), "w") as fh:
        json.dump({"battery_mv": mv, "received_at": 1.0}, fh)


def _write_device_report(state_dir, events, fw_version=RUNNING_VERSION):
    device_report = {
        "schema": 1,
        "next_seq": (max((e["seq"] for e in events), default=0)) + 1,
        "devices": {"aa:bb:cc:dd:ee:ff": {
            "fw_version": fw_version, "reported_at": NOW, "events": events,
        }},
    }
    with open(firmware_registry.device_report_path(state_dir), "w") as fh:
        json.dump(device_report, fh)


def _save_cfg(state_dir, hold_kwargs, topic_url=_NOTIFY_TOPIC_URL, lang="en", notifications=True, battery_low_toggle=True):
    kwargs = dict(hold_kwargs)
    if notifications:
        kwargs["notifications"] = {
            "topic_url": topic_url, "battery_low": battery_low_toggle,
            "frame_silent": True, "lang": lang,
        }
    device_config.save_device_config(state_dir, **kwargs)


# display_enabled=False forces the display-off hold branch on every
# run_once() call below - the reconcile step must still run before that
# branch's own early return.
_DISPLAY_OFF = {"display_enabled": False}


def test_installed_result_updates_registry_and_sends_one_notification(tmp_path, monkeypatch):
    d = _mkdir(tmp_path, "installed")
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "installed", "version": NEXT_VERSION},
    ])
    _save_cfg(d, _DISPLAY_OFF)
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    poll_cycle.run_once(state_dir=d)

    registry = firmware_registry.load_registry(d)
    assert registry["schedule"] is None, "expected the schedule cleared after install, got %r" % (registry["schedule"],)
    assert registry["last_outcome"]["kind"] == "installed"
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one send, got %d: %r" % (len(sender.calls), sender.calls))
    body = sender.calls[0][2]
    assert body == "Firmware fw-v1.1.0 installed", "unexpected install body: %r" % (body,)


def test_installed_result_french_lang_produces_french_body(tmp_path, monkeypatch):
    d = _mkdir(tmp_path, "installed-fr")
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "installed", "version": NEXT_VERSION},
    ])
    _save_cfg(d, _DISPLAY_OFF, lang="fr")
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    poll_cycle.run_once(state_dir=d)

    if len(sender.calls) != 1:
        pytest.fail("expected exactly one send, got %d" % len(sender.calls))
    body = sender.calls[0][2]
    assert body == "Micrologiciel fw-v1.1.0 installé", "unexpected French install body: %r" % (body,)


def test_third_counted_failure_marks_failed_and_notifies_once(tmp_path, monkeypatch):
    d = _mkdir(tmp_path, "failed")
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "fail-hash", "version": NEXT_VERSION},
        {"seq": 2, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "fail-hash", "version": NEXT_VERSION},
        {"seq": 3, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "fail-hash", "version": NEXT_VERSION},
    ])
    _save_cfg(d, _DISPLAY_OFF)
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    poll_cycle.run_once(state_dir=d)

    registry = firmware_registry.load_registry(d)
    assert registry["schedule"]["state"] == "failed"
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one failure send, got %d: %r" % (len(sender.calls), sender.calls))
    body = sender.calls[0][2]
    assert body == "Update failed, back on fw-v1.0.0", "unexpected failure body: %r" % (body,)

    # A second cycle over the same, already-reconciled events sends nothing
    # more (reconciled_seq already covers them).
    sender2 = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender2)
    poll_cycle.run_once(state_dir=d)
    if sender2.calls:
        pytest.fail("expected no repeat send on the second cycle, got %r" % (sender2.calls,))


def test_rollback_result_records_attempt_and_sends_no_notification(tmp_path, monkeypatch):
    d = _mkdir(tmp_path, "rollback")
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "rollback", "version": NEXT_VERSION},
    ])
    _save_cfg(d, _DISPLAY_OFF)
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    poll_cycle.run_once(state_dir=d)

    registry = firmware_registry.load_registry(d)
    assert registry["schedule"]["attempts"] == 1
    assert registry["last_outcome"]["kind"] == "rollback"
    if sender.calls:
        pytest.fail("expected no send on a rollback result, got %r" % (sender.calls,))


def test_notifications_disabled_still_updates_registry_and_sends_nothing(tmp_path, monkeypatch):
    d = _mkdir(tmp_path, "no-notify")
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "installed", "version": NEXT_VERSION},
    ])
    _save_cfg(d, _DISPLAY_OFF, notifications=False)
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    poll_cycle.run_once(state_dir=d)

    registry = firmware_registry.load_registry(d)
    assert registry["schedule"] is None, "the registry must still update with notifications off"
    if sender.calls:
        pytest.fail("expected no send with notifications disabled, got %r" % (sender.calls,))


def test_no_topic_url_still_updates_registry_and_sends_nothing(tmp_path, monkeypatch):
    d = _mkdir(tmp_path, "no-topic")
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "installed", "version": NEXT_VERSION},
    ])
    _save_cfg(d, _DISPLAY_OFF, topic_url=None)
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    poll_cycle.run_once(state_dir=d)

    registry = firmware_registry.load_registry(d)
    assert registry["schedule"] is None, "the registry must still update with no topic_url"
    if sender.calls:
        pytest.fail("expected no send with topic_url=None, got %r" % (sender.calls,))


def test_reconcile_raising_does_not_break_the_cycle(tmp_path, monkeypatch, capsys):
    d = _mkdir(tmp_path, "raise")
    _save_cfg(d, _DISPLAY_OFF)

    def _boom(state_dir, now=None):
        raise RuntimeError("simulated reconcile failure")

    monkeypatch.setattr(poll_cycle.firmware_registry, "apply_reconcile", _boom)

    result = poll_cycle.run_once(state_dir=d)

    assert result is not None and result.get("state") is not None, (
        "run_once() did not complete its normal hold-branch work: %r" % (result,)
    )
    err = capsys.readouterr().err
    assert "firmware reconcile failed: RuntimeError" in err, "expected a one-line exception-type-only log, got %r" % (err,)
    assert "simulated reconcile failure" not in err, "the raw exception text must never be logged"


@pytest.mark.parametrize("hold_kwargs", [
    {"display_enabled": False},
    {"quiet_hours_enabled": True, "quiet_hours_start": "00:00", "quiet_hours_end": "23:59"},
])
def test_reconcile_runs_on_every_hold_branch(tmp_path, monkeypatch, hold_kwargs):
    d = _mkdir(tmp_path, "hold-" + "-".join(str(v) for v in hold_kwargs.values()))
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "installed", "version": NEXT_VERSION},
    ])
    _save_cfg(d, hold_kwargs)
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    result = poll_cycle.run_once(state_dir=d)

    assert result.get("state") is not None, "expected a hold-branch result, got %r" % (result,)
    registry = firmware_registry.load_registry(d)
    assert registry["schedule"] is None, "the reconcile step must run even inside a hold branch"
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one send on the hold branch, got %d" % len(sender.calls))


def test_reconcile_runs_on_battery_empty_hold_branch(tmp_path, monkeypatch):
    d = _mkdir(tmp_path, "hold-battery-empty")
    schedule_id = _schedule(d)
    _write_device_report(d, [
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": schedule_id, "token": "installed", "version": NEXT_VERSION},
    ])
    # battery_low_toggle=False: isolate the firmware notification from
    # the unrelated battery-low transition push this same battery state
    # would otherwise also fire (both go through the same monkeypatched
    # sender below).
    _save_cfg(d, {}, battery_low_toggle=False)  # display enabled, no quiet hours - battery alone forces the hold
    _write_battery_state(d, 3000)  # below device_policy.BATTERY_CRITICAL_MV (3300)
    sender = _FakeSender()
    monkeypatch.setattr(poll_cycle.notify, "send_notification", sender)

    result = poll_cycle.run_once(state_dir=d)

    assert result.get("state") == "battery_empty", "expected the battery-empty hold branch, got %r" % (result,)
    registry = firmware_registry.load_registry(d)
    assert registry["schedule"] is None, "the reconcile step must run even inside the battery-empty hold branch"
    if len(sender.calls) != 1:
        pytest.fail("expected exactly one send on the battery-empty hold branch, got %d" % len(sender.calls))
