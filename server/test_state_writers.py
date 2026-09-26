#!/usr/bin/env python3
"""Behaviour tests proving server/device_config.py, server/plane/colour_rules.py
and server/plane/manual_resolutions.py write their state files through
server/atomic_io.py: no lost update on a concurrently-saved
device_config.json, unique per-call temp names (no leftover '*.tmp'), a
propagated failure leaving the prior file intact, and the on-disk file
mode matching atomic_io's own default.

Every assertion is about observable behaviour (final file contents,
exceptions, file mode, directory listing) - never about source text.
"""
import json
import os
import stat
import subprocess
import sys
import threading
import time

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server import atomic_io, device_config  # noqa: E402
from server.plane import colour_rules, manual_resolutions  # noqa: E402


def _tmp_leftovers(directory):
    return [name for name in os.listdir(directory) if name.endswith(".tmp")]


# --- No-lost-update: 12 threads x 20 saves, one distinct field each ------

_QUIET_START_A, _QUIET_START_B = "22:00", "23:30"
_QUIET_END_A, _QUIET_END_B = "06:00", "07:30"


def _field_plans():
    """One (values, expected_final) pair per save_device_config() keyword,
    each cycling between two (or, for tracked_runway, three) valid values
    over 20 iterations - only the final iteration's value is asserted, but
    the earlier ones give the writer thread real work to interleave with
    every other thread's own field.
    """
    return {
        "theme": (
            ["white" if i % 2 == 0 else "blue" for i in range(20)], "blue"),
        "theme_arriving": (
            ["yellow" if i % 2 == 0 else "red" for i in range(20)], "red"),
        "tracked_runway": (
            [device_config.RUNWAY_IDS[i % len(device_config.RUNWAY_IDS)] for i in range(20)],
            device_config.RUNWAY_IDS[19 % len(device_config.RUNWAY_IDS)]),
        "led_enabled": (
            [i % 2 == 0 for i in range(20)], False),
        "quiet_hours_enabled": (
            [i % 2 == 0 for i in range(20)], False),
        "quiet_hours_start": (
            [_QUIET_START_A if i % 2 == 0 else _QUIET_START_B for i in range(20)], _QUIET_START_B),
        "quiet_hours_end": (
            [_QUIET_END_A if i % 2 == 0 else _QUIET_END_B for i in range(20)], _QUIET_END_B),
        "wake_interval_s": (
            [120 if i % 2 == 0 else 600 for i in range(20)], 600),
        "display_enabled": (
            [i % 2 == 0 for i in range(20)], False),
        "calendar_theme_id": (
            ["" if i % 2 == 0 else "green" for i in range(20)], "green"),
        "screen_id": (
            [device_config.DEFAULT_SCREEN_ID for _ in range(20)], device_config.DEFAULT_SCREEN_ID),
        "notifications": (
            [
                {"topic_url": None, "battery_low": True, "frame_silent": True, "lang": "en"}
                if i % 2 == 0 else
                {"topic_url": "https://ntfy.example/skypane", "battery_low": False, "frame_silent": False, "lang": "fr"}
                for i in range(20)
            ],
            {"topic_url": "https://ntfy.example/skypane", "battery_low": False, "frame_silent": False, "lang": "fr"},
        ),
    }


def test_concurrent_save_device_config_loses_no_field(tmp_path):
    state_dir = str(tmp_path)
    plans = _field_plans()
    assert set(plans) == {
        "theme", "theme_arriving", "tracked_runway", "led_enabled",
        "quiet_hours_enabled", "quiet_hours_start", "quiet_hours_end",
        "wake_interval_s", "display_enabled", "calendar_theme_id",
        "screen_id", "notifications",
    }, "test setup: expected exactly the twelve save_device_config() keywords"

    errors = []

    def worker(field, values):
        try:
            for value in values:
                device_config.save_device_config(state_dir, **{field: value})
        except Exception as exc:  # collected, never swallowed
            errors.append((field, repr(exc)))

    threads = [
        threading.Thread(target=worker, args=(field, values))
        for field, (values, _expected) in plans.items()
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
        assert not t.is_alive(), "a worker thread did not finish in time"

    assert not errors, "worker exception(s): %r" % (errors,)

    final = device_config.load_device_config(state_dir)
    for field, (_values, expected) in plans.items():
        assert final[field] == expected, (
            "lost update on field %r: expected %r, got %r" % (field, expected, final[field])
        )

    assert _tmp_leftovers(state_dir) == []


# --- Cross-process file lock ---------------------------------------------

_LOCK_HOLDER_TEMPLATE = """
import sys
sys.path.insert(0, {repo_root!r})
from server import atomic_io, device_config

state_dir = sys.argv[1]
lock_path = state_dir + "/" + device_config.DEVICE_CONFIG_LOCK_FILENAME
with atomic_io.exclusive_lock(lock_path, 5):
    print("locked", flush=True)
    sys.stdin.read()  # blocks until the parent closes stdin, releasing the lock
"""


def test_save_device_config_waits_for_cross_process_lock(tmp_path):
    state_dir = str(tmp_path)
    os.makedirs(state_dir, exist_ok=True)
    script = tmp_path / "_holder.py"
    script.write_text(_LOCK_HOLDER_TEMPLATE.format(repo_root=REPO_ROOT))

    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT
    child = subprocess.Popen(
        [sys.executable, str(script), state_dir],
        cwd=REPO_ROOT,
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        line = child.stdout.readline()
        assert line.strip() == "locked"

        done = threading.Event()
        result = {}

        def save():
            try:
                device_config.save_device_config(state_dir, theme="blue")
            except Exception as exc:  # pragma: no cover - failure path asserted below
                result["error"] = exc
            done.set()

        saver = threading.Thread(target=save)
        saver.start()

        # The child still holds the lock: the save must not have landed yet.
        time.sleep(0.3)
        assert not done.is_set(), "save_device_config() returned while the file lock was held"
        assert device_config.load_device_config(state_dir)["theme"] == device_config.DEFAULT_THEME_ID
    finally:
        child.stdin.close()
        assert child.wait(timeout=5) == 0

    # The child released the lock: the waiting save now lands.
    assert done.wait(timeout=8), "save_device_config() never completed after the lock was released"
    saver.join(timeout=1)
    assert "error" not in result, "save_device_config() raised: %r" % (result.get("error"),)
    assert device_config.load_device_config(state_dir)["theme"] == "blue"


# --- No leftover temp files, and unchanged JSON shape --------------------

def test_no_stray_tmp_files_after_every_writer(tmp_path):
    state_dir = str(tmp_path)

    device_config.save_device_config(state_dir, theme="blue")
    assert _tmp_leftovers(state_dir) == []
    with open(device_config.device_config_path(state_dir)) as fh:
        json.load(fh)  # parses cleanly

    add_result = colour_rules.add_rule(state_dir, "callsign", "AFR1234", "white")
    assert add_result == colour_rules.ADD_OK_NEW
    assert _tmp_leftovers(state_dir) == []
    with open(colour_rules.colour_rules_path(state_dir)) as fh:
        json.load(fh)

    delete_result = colour_rules.delete_rule(state_dir, "callsign", "AFR1234")
    assert delete_result is True
    assert _tmp_leftovers(state_dir) == []

    add_entry_result = manual_resolutions.add_entry(state_dir, "AFR", "Air France")
    assert add_entry_result == manual_resolutions.ADD_OK
    assert _tmp_leftovers(state_dir) == []
    with open(manual_resolutions.manual_resolutions_path(state_dir)) as fh:
        json.load(fh)

    delete_entry_result = manual_resolutions.delete_entry(state_dir, "AFR")
    assert delete_entry_result is True
    assert _tmp_leftovers(state_dir) == []


# --- Forced write failure leaves the prior file intact -------------------

def _raise_oserror(*args, **kwargs):
    raise OSError("injected atomic_write failure")


def test_add_rule_failure_returns_failed_and_leaves_file_intact(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    add_result = colour_rules.add_rule(state_dir, "callsign", "AFR1234", "white")
    assert add_result == colour_rules.ADD_OK_NEW
    path = colour_rules.colour_rules_path(state_dir)
    before = open(path, "rb").read()

    monkeypatch.setattr(colour_rules.atomic_io, "atomic_write", _raise_oserror)
    assert colour_rules.add_rule(state_dir, "hex", "3946A1", "black") == colour_rules.ADD_FAILED
    assert open(path, "rb").read() == before
    assert _tmp_leftovers(state_dir) == []


def test_delete_rule_failure_returns_false_and_leaves_file_intact(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    assert colour_rules.add_rule(state_dir, "callsign", "AFR1234", "white") == colour_rules.ADD_OK_NEW
    path = colour_rules.colour_rules_path(state_dir)
    before = open(path, "rb").read()

    monkeypatch.setattr(colour_rules.atomic_io, "atomic_write", _raise_oserror)
    assert colour_rules.delete_rule(state_dir, "callsign", "AFR1234") is False
    assert open(path, "rb").read() == before
    assert _tmp_leftovers(state_dir) == []


def test_add_entry_failure_returns_failed_and_leaves_file_intact(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    assert manual_resolutions.add_entry(state_dir, "AFR", "Air France") == manual_resolutions.ADD_OK
    path = manual_resolutions.manual_resolutions_path(state_dir)
    before = open(path, "rb").read()

    monkeypatch.setattr(manual_resolutions.atomic_io, "atomic_write", _raise_oserror)
    assert manual_resolutions.add_entry(state_dir, "BAW", "British Airways") == manual_resolutions.ADD_FAILED
    assert open(path, "rb").read() == before
    assert _tmp_leftovers(state_dir) == []


def test_save_device_config_propagates_oserror_from_write(tmp_path, monkeypatch):
    state_dir = str(tmp_path)
    device_config.save_device_config(state_dir, theme="white")
    path = device_config.device_config_path(state_dir)
    before = open(path, "rb").read()

    monkeypatch.setattr(device_config.atomic_io, "atomic_write", _raise_oserror)
    with pytest.raises(OSError):
        device_config.save_device_config(state_dir, theme="blue")
    assert open(path, "rb").read() == before
    assert _tmp_leftovers(state_dir) == []


# --- File mode -------------------------------------------------------------

def test_device_config_file_mode_matches_atomic_io_default(tmp_path):
    state_dir = str(tmp_path)
    device_config.save_device_config(state_dir, theme="blue")
    path = device_config.device_config_path(state_dir)
    assert stat.S_IMODE(os.stat(path).st_mode) == atomic_io.DEFAULT_FILE_MODE
