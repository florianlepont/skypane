"""deploy/tests/test_units.py -- systemd unit hardening + release-layout
paths. Enforces the shared hardening directive table and the measured
offline exposure scores.
"""

import configparser
import shutil
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEPLOY = _REPO_ROOT / "deploy"

_UNITS = [
    "skypane-byos.service",
    "skypane-companion.service",
    "skypane-poll.service",
    "skypane-backup.service",
]

# The directive set every one of the four units must carry. Values are
# compared as strings after configparser's own whitespace handling.
_COMMON_DIRECTIVES = {
    "CapabilityBoundingSet": "",
    "AmbientCapabilities": "",
    "PrivateDevices": "true",
    "DevicePolicy": "closed",
    "ProtectKernelTunables": "true",
    "ProtectKernelModules": "true",
    "ProtectKernelLogs": "true",
    "ProtectControlGroups": "true",
    "ProtectClock": "true",
    "ProtectHostname": "true",
    "ProtectProc": "invisible",
    "ProcSubset": "pid",
    "RestrictNamespaces": "true",
    "RestrictRealtime": "true",
    "RestrictSUIDSGID": "true",
    "LockPersonality": "true",
    "SystemCallArchitectures": "native",
    "MemoryDenyWriteExecute": "true",
    "SystemCallFilter": "@system-service",
    "SystemCallErrorNumber": "EPERM",
    "UMask": "0027",
    "NoNewPrivileges": "true",
    "PrivateTmp": "true",
    "ProtectSystem": "strict",
    "ProtectHome": "true",
}


def _parse_unit(name):
    """Parse a systemd unit file with configparser.

    strict=False allows the repeated [Service]-adjacent comment-only
    lines systemd unit files carry; interpolation=None so a literal '%'
    or '$' in an ExecStart line is never treated as configparser's own
    interpolation syntax.
    """
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    # systemd keys are case-sensitive (SystemCallFilter != systemcallfilter);
    # configparser lower-cases keys by default.
    cp.optionxform = str
    cp.read(_DEPLOY / name)
    return cp


def _execstart_full_command(name):
    """Join a (possibly backslash-continued) ExecStart= value into one line."""
    text = (_DEPLOY / name).read_text()
    lines = text.splitlines()
    out = []
    capture = False
    for line in lines:
        if line.startswith("ExecStart="):
            capture = True
            out.append(line[len("ExecStart="):])
            if not line.rstrip().endswith("\\"):
                break
            continue
        if capture:
            out.append(line.strip())
            if not line.rstrip().endswith("\\"):
                break
    joined = " ".join(part.rstrip("\\").strip() for part in out)
    return joined


@pytest.mark.parametrize("unit", _UNITS)
def test_common_directive_set_present(unit):
    cp = _parse_unit(unit)
    service = cp["Service"]
    for key, expected in _COMMON_DIRECTIVES.items():
        assert key in service, "%s missing %s" % (unit, key)
        assert service[key] == expected, "%s: %s=%r, expected %r" % (
            unit,
            key,
            service[key],
            expected,
        )


@pytest.mark.parametrize(
    "unit,expected",
    [
        ("skypane-byos.service", "AF_INET AF_INET6 AF_UNIX"),
        ("skypane-companion.service", "AF_INET AF_INET6 AF_UNIX"),
        ("skypane-poll.service", "AF_INET AF_INET6 AF_UNIX"),
        ("skypane-backup.service", "AF_UNIX"),
    ],
)
def test_restrict_address_families(unit, expected):
    cp = _parse_unit(unit)
    assert cp["Service"]["RestrictAddressFamilies"] == expected


def test_poll_unit_has_start_timeout():
    # A oneshot's default start timeout is infinity; without one a stuck
    # cycle (a hung upstream, a stuck lock wait) never gets killed.
    cp = _parse_unit("skypane-poll.service")
    assert cp["Service"]["TimeoutStartSec"] == "90s"


def test_backup_unit_has_private_network():
    cp = _parse_unit("skypane-backup.service")
    assert cp["Service"]["PrivateNetwork"] == "true"


@pytest.mark.parametrize("unit", ["skypane-companion.service", "skypane-poll.service"])
def test_companion_and_poll_have_no_ip_filter(unit):
    text = (_DEPLOY / unit).read_text()
    assert "IPAddressDeny" not in text
    assert "IPAddressAllow" not in text


@pytest.mark.parametrize(
    "unit",
    ["skypane-byos.service", "skypane-companion.service", "skypane-poll.service", "skypane-backup.service"],
)
def test_execstart_uses_release_layout_path(unit):
    cmd = _execstart_full_command(unit)
    assert cmd.startswith("/opt/skypane/venv/bin/python3 /opt/skypane/current/"), (
        "%s ExecStart does not start from /opt/skypane/current/: %s" % (unit, cmd)
    )


def test_companion_binds_loopback_only():
    cmd = _execstart_full_command("skypane-companion.service")
    assert "--bind 127.0.0.1" in cmd


def test_companion_and_poll_geofence_uses_release_layout_path():
    for unit in ("skypane-companion.service", "skypane-poll.service"):
        cmd = _execstart_full_command(unit)
        assert "/opt/skypane/current/adsb-test/runway3.json" in cmd
        assert "/opt/skypane/config/" not in cmd


def test_no_unit_references_the_old_config_directory():
    for unit in _UNITS:
        text = (_DEPLOY / unit).read_text()
        assert "/opt/skypane/config/" not in text


def test_backup_service_shape():
    cp = _parse_unit("skypane-backup.service")
    service = cp["Service"]
    assert service["Type"] == "oneshot"
    assert service["User"] == "skypane"
    assert service["Group"] == "skypane"
    read_write = service["ReadWritePaths"].split()
    assert "/opt/skypane/state" in read_write
    assert "/var/lib/skypane-backup/archives" in read_write
    assert "Install" not in cp
    cmd = _execstart_full_command("skypane-backup.service")
    assert "--state-dir /opt/skypane/state" in cmd
    assert "--archive-dir /var/lib/skypane-backup/archives" in cmd
    assert "--keep 14" in cmd


def test_backup_timer_shape():
    cp = _parse_unit("skypane-backup.timer")
    timer = cp["Timer"]
    assert timer["OnCalendar"] == "*-*-* 03:15:00 UTC"
    assert timer["Persistent"] == "true"
    assert timer["RandomizedDelaySec"] == "10m"
    assert timer["Unit"] == "skypane-backup.service"
    assert cp["Install"]["WantedBy"] == "timers.target"


@pytest.mark.parametrize("unit", _UNITS)
def test_offline_security_score_at_or_under_threshold(unit):
    systemd_analyze = shutil.which("systemd-analyze")
    if systemd_analyze is None:
        pytest.skip("systemd-analyze not on PATH")
    help_text = subprocess.run(
        [systemd_analyze, "security", "--help"], capture_output=True, text=True, timeout=10
    ).stdout
    if "--offline" not in help_text:
        pytest.skip("systemd-analyze security does not support --offline on this host")
    result = subprocess.run(
        [systemd_analyze, "security", "--offline=true", "--threshold=20", str(_DEPLOY / unit)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        "%s exceeded the offline exposure threshold:\n%s" % (unit, result.stdout + result.stderr)
    )
