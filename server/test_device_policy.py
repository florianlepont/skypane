#!/usr/bin/env python3
"""Golden-value and fallback tests for server/device_policy.py: the shared,
stdlib-only battery and quiet-hours policy used by the poll cycle, the byos
device endpoint and the companion.

Every battery/quiet-hours assertion here pins a value already reachable
through today's poll_loop/device_config copies (or, for the one merged
invalid-time fallback, the unified behaviour those two copies disagreed
on) - never a source-text check.
"""
import json
import subprocess
import sys
from datetime import datetime, timezone

import pytest

from skypane_test_support import REPO_ROOT, child_env

import server.device_config as device_config
import server.device_policy as device_policy
import server.poll_loop as poll_loop
import server.state_store as state_store
import server.wake as wake

# --- Battery-percent golden table --------------------------------------
#
# mv -> percent, computed once against the now-retired poll_loop copy of
# this estimate (and companion.battery.battery_percent(), which shares the
# identical curve) and hard-coded here as literals.
_BATTERY_PERCENT_GOLDEN = (
    (None, None),
    ("x", None),
    (float("nan"), None),
    (-1, None),
    (0, None),
    (1, 0),
    (2946, 0),
    (3000, 1),
    (3364, 7),
    (3500, 15),
    (3600, 25),
    (3814, 50),
    (4000, 90),
    (4050, 94),
    (4112, 100),
    (5000, 100),
)


def test_battery_percent_golden_table():
    """battery_percent() over the golden mv table matches the now-retired
    poll_loop copy's output, hard-coded as literals."""
    for mv, expected in _BATTERY_PERCENT_GOLDEN:
        got = device_policy.battery_percent(mv)
        if got != expected:
            pytest.fail("battery_percent(%r) returned %r, expected %r" % (mv, got, expected))


def test_battery_fraction_endpoints_and_none():
    """battery_fraction(4112) == 1.0, battery_fraction(2946) == 0.0,
    battery_fraction(None) is None."""
    if device_policy.battery_fraction(4112) != 1.0:
        pytest.fail("battery_fraction(4112) did not return 1.0")
    if device_policy.battery_fraction(2946) != 0.0:
        pytest.fail("battery_fraction(2946) did not return 0.0")
    if device_policy.battery_fraction(None) is not None:
        pytest.fail("battery_fraction(None) did not return None")


# --- Battery hysteresis --------------------------------------------------


def test_apply_battery_hysteresis_none_and_boundaries():
    """apply_battery_hysteresis(): None keeps was_active; the boundary
    values 3500/3600 behave exactly as today's poll_loop copy."""
    if device_policy.apply_battery_hysteresis(None, True) is not True:
        pytest.fail("apply_battery_hysteresis(None, True) did not keep was_active")
    if device_policy.apply_battery_hysteresis(None, False) is not False:
        pytest.fail("apply_battery_hysteresis(None, False) did not keep was_active")
    if device_policy.apply_battery_hysteresis(3500, False) is not True:
        pytest.fail("apply_battery_hysteresis(3500, False) expected True (at-or-below threshold)")
    if device_policy.apply_battery_hysteresis(3600, True) is not False:
        pytest.fail("apply_battery_hysteresis(3600, True) expected False (at-or-above clear)")
    if device_policy.apply_battery_hysteresis(3599, True) is not True:
        pytest.fail("apply_battery_hysteresis(3599, True) expected True (still below clear)")


def test_apply_battery_critical_hysteresis_none_and_boundaries():
    """apply_battery_critical_hysteresis(): None keeps was_active; the
    boundary values 3300/3700 behave exactly as today's poll_loop copy."""
    if device_policy.apply_battery_critical_hysteresis(None, True) is not True:
        pytest.fail("apply_battery_critical_hysteresis(None, True) did not keep was_active")
    if device_policy.apply_battery_critical_hysteresis(None, False) is not False:
        pytest.fail("apply_battery_critical_hysteresis(None, False) did not keep was_active")
    if device_policy.apply_battery_critical_hysteresis(3300, False) is not True:
        pytest.fail("apply_battery_critical_hysteresis(3300, False) expected True (at-or-below critical)")
    if device_policy.apply_battery_critical_hysteresis(3700, True) is not False:
        pytest.fail("apply_battery_critical_hysteresis(3700, True) expected False (at-or-above recover)")
    if device_policy.apply_battery_critical_hysteresis(3699, True) is not True:
        pytest.fail("apply_battery_critical_hysteresis(3699, True) expected True (still below recover)")


def test_battery_critical_pin_applies():
    """battery_critical_pin_applies(latched, fresh_mv): the pin rule byos
    uses to extend sleep_s while BATTERY EMPTY holds."""
    cases = (
        (True, None, True),
        (True, 3699, True),
        (True, 3700, False),
        (False, 3000, False),
    )
    for latched, fresh_mv, expected in cases:
        got = device_policy.battery_critical_pin_applies(latched, fresh_mv)
        if got != expected:
            pytest.fail(
                "battery_critical_pin_applies(%r, %r) returned %r, expected %r"
                % (latched, fresh_mv, got, expected))


# --- Quiet-hours window ----------------------------------------------------


def test_quiet_hours_window_verified_value():
    """quiet_hours_window() returns the stored (start_hm, end_hm) verbatim
    when both are already valid."""
    config = {"quiet_hours_enabled": True, "quiet_hours_start": "22:15", "quiet_hours_end": "06:45"}
    got = device_policy.quiet_hours_window(config)
    if got != ("22:15", "06:45"):
        pytest.fail("quiet_hours_window(%r) returned %r, expected ('22:15', '06:45')" % (config, got))


def test_quiet_hours_window_none_when_not_enabled():
    """quiet_hours_window() returns None when enabled is False, "yes",
    missing, or config is not a dict."""
    base = {"quiet_hours_start": "22:15", "quiet_hours_end": "06:45"}
    for config in (
        dict(base, quiet_hours_enabled=False),
        dict(base, quiet_hours_enabled="yes"),
        dict(base),
        "not-a-dict",
        None,
        123,
    ):
        got = device_policy.quiet_hours_window(config)
        if got is not None:
            pytest.fail("quiet_hours_window(%r) returned %r, expected None" % (config, got))


def test_quiet_hours_invalid_stored_time_falls_back_to_default_window():
    """The unified invalid-time fallback: with quiet hours enabled and an
    invalid start ("25:99"), an invalid end (7, an int), or a missing
    start, quiet_hours_window() falls back to the server's 23:00-07:00
    defaults - the behaviour both byos and the poll cycle now share,
    replacing byos's old "treat as disabled" fallback."""
    cases = (
        {"quiet_hours_enabled": True, "quiet_hours_start": "25:99", "quiet_hours_end": "07:00"},
        {"quiet_hours_enabled": True, "quiet_hours_start": "23:00", "quiet_hours_end": 7},
        {"quiet_hours_enabled": True, "quiet_hours_end": "07:00"},
    )
    for config in cases:
        got = device_policy.quiet_hours_window(config)
        if got != ("23:00", "07:00"):
            pytest.fail(
                "quiet_hours_window(%r) returned %r, expected the ('23:00', '07:00') fallback"
                % (config, got))


# --- quiet_hours_status -----------------------------------------------------


def test_quiet_hours_status_invalid_start_falls_back_and_holds():
    """quiet_hours_status() for an enabled config with an invalid stored
    start, evaluated at 00:30 Europe/Paris (inside the 23:00-07:00
    fallback window), returns a positive remaining count and end_hm
    "07:00"."""
    config = {"quiet_hours_enabled": True, "quiet_hours_start": "25:99", "quiet_hours_end": "07:00"}
    at_0030_paris = datetime(2023, 11, 15, 0, 30, 0, tzinfo=device_policy.QUIET_HOURS_TZ)
    remaining, end_hm = device_policy.quiet_hours_status(config, at_0030_paris.timestamp())
    if not (isinstance(remaining, int) and remaining > 0):
        pytest.fail("quiet_hours_status() at 00:30 Paris returned remaining=%r, expected a positive int" % (remaining,))
    if end_hm != "07:00":
        pytest.fail("quiet_hours_status() at 00:30 Paris returned end_hm=%r, expected '07:00'" % (end_hm,))


def test_quiet_hours_status_outside_window_returns_none_none():
    """quiet_hours_status() outside the fallback window (10:00 Europe/Paris)
    returns (None, None)."""
    config = {"quiet_hours_enabled": True, "quiet_hours_start": "25:99", "quiet_hours_end": "07:00"}
    at_1000_paris = datetime(2023, 11, 15, 10, 0, 0, tzinfo=device_policy.QUIET_HOURS_TZ)
    got = device_policy.quiet_hours_status(config, at_1000_paris.timestamp())
    if got != (None, None):
        pytest.fail("quiet_hours_status() at 10:00 Paris returned %r, expected (None, None)" % (got,))


def test_quiet_hours_status_never_raises_for_hostile_now_epoch():
    """quiet_hours_status() returns (None, None) and never raises for a
    non-numeric string or an infinite now_epoch."""
    config = {"quiet_hours_enabled": True, "quiet_hours_start": "23:00", "quiet_hours_end": "07:00"}
    for hostile in ("x", float("inf")):
        got = device_policy.quiet_hours_status(config, hostile)
        if got != (None, None):
            pytest.fail("quiet_hours_status(config, %r) returned %r, expected (None, None)" % (hostile, got))


# --- seconds_until_quiet_hours_end: same DST/wrap cases as device_config ---


def test_wrap_midnight_window_returns_verified_dst_values():
    """seconds_until_quiet_hours_end() returns the verified wrap-midnight/DST
    anchors: 28000 mid-window, None just past end, 23400 across
    spring-forward (1h less than naive), 30600 across autumn fall-back
    (1h more than naive) - the same cases device_config's own test pins."""
    cases = [
        (1700000000.0, "23:00", "07:00", 28000),  # 2023-11-14T23:13:20+01:00 Paris
        (1700028800.0, "23:00", "07:00", None),  # 07:13:20 Paris, just past end
        (1774737000.0, "23:00", "07:00", 23400),  # spring-forward night
        (1792877400.0, "23:00", "07:00", 30600),  # autumn fall-back night
    ]
    for epoch, start_hm, end_hm, expected in cases:
        now_utc = datetime.fromtimestamp(epoch, timezone.utc)
        got = device_policy.seconds_until_quiet_hours_end(now_utc, start_hm, end_hm)
        if got != expected:
            pytest.fail("seconds_until_quiet_hours_end(epoch=%r, %r, %r) returned %r, expected %r" % (
                epoch, start_hm, end_hm, got, expected,
            ))


def test_same_day_window_and_zero_width_window():
    """seconds_until_quiet_hours_end() handles a same-day (non-wrapping)
    window correctly and returns None for a zero-width start_hm == end_hm
    window."""
    at_1330 = datetime(2023, 11, 14, 12, 30, 0, tzinfo=timezone.utc)
    at_1230 = datetime(2023, 11, 14, 11, 30, 0, tzinfo=timezone.utc)
    got_active = device_policy.seconds_until_quiet_hours_end(at_1330, "13:00", "14:00")
    if got_active != 1800:
        pytest.fail("same-day window at 13:30 Paris returned %r, expected 1800" % (got_active,))
    got_inactive = device_policy.seconds_until_quiet_hours_end(at_1230, "13:00", "14:00")
    if got_inactive is not None:
        pytest.fail("same-day window at 12:30 Paris returned %r, expected None" % (got_inactive,))
    got_zero_width = device_policy.seconds_until_quiet_hours_end(at_1330, "13:00", "13:00")
    if got_zero_width is not None:
        pytest.fail("start_hm == end_hm returned %r, expected None (a zero-width window is never active)" % (got_zero_width,))


# --- Server modules bind the shared objects, they don't re-implement them --


_REMOVED_POLL_LOOP_NAMES = (
    "BATTERY_LOW_THRESHOLD_MV",
    "BATTERY_LOW_CLEAR_MV",
    "BATTERY_CRITICAL_MV",
    "BATTERY_CRITICAL_RECOVER_MV",
    "apply_battery_hysteresis",
    "apply_battery_critical_hysteresis",
    "_NOTIFY_BATTERY_DISCHARGE_CURVE",
    "_NOTIFY_BATTERY_FULL_MV",
    "_NOTIFY_BATTERY_EMPTY_MV",
    "_battery_percent_estimate",
    "_poll_state_path",
    "load_poll_state",
    "_HOLD_KINDS",
    "_hold_state",
    "load_battery_state",
    "_serialize_poll_state",
    "save_poll_state",
    "_persist_poll_state",
)


def test_server_modules_use_the_shared_policy_objects():
    """device_config, wake and poll_loop bind the shared device_policy/
    state_store objects rather than keeping their own copies: identity
    (`is`), not mere equality, and the moved poll_loop names no longer
    exist at all."""
    if device_config.seconds_until_quiet_hours_end is not device_policy.seconds_until_quiet_hours_end:
        pytest.fail("device_config.seconds_until_quiet_hours_end is not the shared device_policy object")
    if device_config.quiet_hours_status is not device_policy.quiet_hours_status:
        pytest.fail("device_config.quiet_hours_status is not the shared device_policy object")
    if device_config.normalise_quiet_hours_time is not device_policy.normalise_quiet_hours_time:
        pytest.fail("device_config.normalise_quiet_hours_time is not the shared device_policy object")
    if device_config._HHMM_RE is not device_policy.HHMM_RE:
        pytest.fail("device_config._HHMM_RE is not the shared device_policy.HHMM_RE object")
    if device_config.QUIET_HOURS_TZ is not device_policy.QUIET_HOURS_TZ:
        pytest.fail("device_config.QUIET_HOURS_TZ is not the shared device_policy.QUIET_HOURS_TZ object")
    if wake.read_battery_critical is not state_store.read_battery_critical:
        pytest.fail("wake.read_battery_critical is not the shared state_store object")
    # poll_loop.device_policy is device_policy: the identical module object,
    # not merely an equal one.
    if poll_loop.device_policy is not device_policy:
        pytest.fail("poll_loop.device_policy is not the shared device_policy module")
    if poll_loop.state_store is not state_store:
        pytest.fail("poll_loop.state_store is not the shared state_store module")
    for name in _REMOVED_POLL_LOOP_NAMES:
        if hasattr(poll_loop, name):
            pytest.fail("poll_loop.%s still exists - should have moved to device_policy/state_store" % name)


# --- Import isolation --------------------------------------------------


def test_device_policy_import_pulls_in_no_extra_server_module_and_no_third_party_package():
    """Importing server.device_policy in a subprocess leaves no `server.*`
    module in sys.modules other than `server` and `server.device_policy`
    itself, and no PIL or requests - proven by a fresh subprocess import,
    never by reading source text. The pre-import snapshot excludes
    modules the test harness's own sitecustomize.py/child_env() pulled in
    (e.g. `requests`, for the network guard) before any application code
    ran - those are the harness's footprint, not device_policy's."""
    script = (
        "import json, sys\n"
        "before = set(sys.modules)\n"
        "import server.device_policy\n"
        "after = set(sys.modules) - before\n"
        "banned = sorted(\n"
        "    m for m in after\n"
        "    if (m.startswith('server.') and m != 'server.device_policy')\n"
        "    or m in ('PIL', 'requests')\n"
        "    or m.startswith('PIL.') or m.startswith('requests.')\n"
        ")\n"
        "print(json.dumps(banned))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], env=child_env(), cwd=REPO_ROOT,
        capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    banned = json.loads(result.stdout.strip().splitlines()[-1])
    assert banned == [], (
        "importing server.device_policy pulled %r into sys.modules - this module "
        "is stdlib-only on purpose" % (banned,))
