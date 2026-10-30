"""End-to-end and live-frame regression for per-hardware OTA.

Two groups of scenarios, both driven through the real publish, schedule,
poll and reconcile code:

* a registry written in the on-disk shape that existed before hardware
  types (no hardware_type, no build) keeps behaving exactly as it did,
  expressed as explicit expected values, and its first rewrite leaves a
  byte-identical registry.json.pre-fleet that later writes never touch;
* two simulated hardware types published through the firmware_cli
  import path, scheduled independently and polled through byos, each
  see only their own release, with wrong binaries and lower builds
  refused.
"""
import hashlib
import importlib.util
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from contextlib import redirect_stderr, redirect_stdout

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
SERVER_PATH = os.path.join(HERE, "byos_server.py")

for _path in (REPO_ROOT, os.path.join(REPO_ROOT, "test-support")):
    if _path not in sys.path:
        sys.path.insert(0, _path)

from server import firmware_cli, firmware_registry, fleet_db, hardware  # noqa: E402 - path bootstrap above must run first
from skypane_fw_image import build_image  # noqa: E402
from skypane_legacy_registry import legacy_release, write_legacy_registry  # noqa: E402
from skypane_test_support import child_env  # noqa: E402

LEGACY_MAC = "aa:bb:cc:dd:ee:01"
LEGACY_TOKEN = "cd" * 32
CLONE_MAC = "aa:bb:cc:dd:ee:02"
CLONE_TOKEN = "ef" * 32
LAND_MAC = "aa:bb:cc:dd:ee:03"
LAND_TOKEN = "12" * 32
CLONE = hardware.SIM_CLONE_KEY
LAND = hardware.SIM_LANDSCAPE_KEY


@pytest.fixture(scope="module")
def byos_module():
    spec = importlib.util.spec_from_file_location("byos_server_fleet_regression", SERVER_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sim_gate(monkeypatch):
    monkeypatch.setenv(hardware.SIM_ENV_VAR, "1")


def read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def seed_devices_json(state_dir, macs):
    with open(os.path.join(state_dir, "devices.json"), "w") as fh:
        json.dump({"devices": {mac: {"secret_sha256": "0" * 64} for mac in macs}}, fh)


def seed_fleet(state_dir, devices):
    conn = fleet_db.connect(state_dir)
    try:
        fleet_db.meta_set(conn, fleet_db.META_MIGRATED, "1")
        owner = fleet_db.add_user(conn, "owner@example.com", "admin")
        for mac, token, hardware_type in devices:
            fleet_db.add_device(
                conn, mac, "1" * 64, hardware_type, owner, token=token,
                environ={hardware.SIM_ENV_VAR: "1"})
    finally:
        conn.close()


def poll(byos_module, state_dir, token, tokens, fw_version="fw-v1.0.0", extra=None):
    headers = {"X-Fw-Version": fw_version, **(extra or {}),
               "Authorization": "Bearer %s" % token}
    return byos_module._record_device_report_and_offer(
        state_dir, {"tokens": tokens}, headers, "http", "example.org")


def report_entry(state_dir, mac):
    return firmware_registry.load_device_report(state_dir)["devices"][mac]


def run_cli(argv):
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = firmware_cli.main(argv)
    return code, out.getvalue(), err.getvalue()


def write_typed_release(base, tag, key, *, image=None, project_name="skypane",
                        chip_id=0x0009, declared_key=None):
    """One <base>/<tag>/ pair for a non-legacy type (names the CLI reads)."""
    subdir = os.path.join(base, tag)
    os.makedirs(subdir, exist_ok=True)
    data = image if image is not None else build_image(
        tag, project_name=project_name, chip_id=chip_id)
    with open(os.path.join(subdir, "skypane-%s-%s.bin" % (key, tag)), "wb") as fh:
        fh.write(data)
    manifest = {
        "version": tag, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
        "released_at": "2026-10-01T00:00:00Z", "commit": "b" * 40, "notes": [],
        "hardware_type": declared_key or key,
    }
    with open(os.path.join(subdir, "release-%s.json" % key), "w") as fh:
        json.dump(manifest, fh)
    return manifest["sha256"]


def write_legacy_dir_release(base, tag):
    subdir = os.path.join(base, tag)
    os.makedirs(subdir, exist_ok=True)
    data = build_image(tag)
    with open(os.path.join(subdir, "skypane-%s.bin" % tag), "wb") as fh:
        fh.write(data)
    manifest = {
        "version": tag, "sha256": hashlib.sha256(data).hexdigest(), "size": len(data),
        "released_at": "2026-10-01T00:00:00Z", "commit": "b" * 40, "notes": [],
        "hardware_type": hardware.LEGACY_KEY,
    }
    with open(os.path.join(subdir, "release.json"), "w") as fh:
        json.dump(manifest, fh)
    return manifest["sha256"]


def snapshot_firmware_dir(state_dir):
    root = firmware_registry.firmware_dir(state_dir)
    return {name: read_bytes(os.path.join(root, name)) for name in sorted(os.listdir(root))}


# --- Live-frame regression: a registry in the pre-change shape ---------------


def legacy_registry_with_images(state_dir):
    """Pre-change shaped registry whose three releases have real image
    files in firmware/<sha>.bin; returns {version: (sha, bytes)}.
    """
    images, entries = {}, []
    for version in ("fw-v1.0.0", "fw-v1.0.1", "fw-v1.0.2"):
        data = build_image(version)
        sha = hashlib.sha256(data).hexdigest()
        images[version] = (sha, data)
        entry = legacy_release(version)
        entry.update(sha256=sha, size=len(data))
        entries.append(entry)
    original = write_legacy_registry(state_dir, releases=entries)
    for sha, data in images.values():
        with open(firmware_registry.firmware_image_path(state_dir, sha), "wb") as fh:
            fh.write(data)
    return images, original


def test_legacy_shaped_registry_loads_and_offers_unchanged(byos_module, tmp_path):
    state_dir = str(tmp_path)
    images, original = legacy_registry_with_images(state_dir)
    seed_devices_json(state_dir, [LEGACY_MAC])
    tokens = {LEGACY_MAC: LEGACY_TOKEN}

    registry = firmware_registry.load_registry(state_dir)
    assert [r["version"] for r in registry["releases"]] == ["fw-v1.0.0", "fw-v1.0.1", "fw-v1.0.2"]
    assert registry["floor_version"] == "fw-v1.0.0"
    assert registry["schedule"] is None
    assert read_bytes(firmware_registry.registry_path(state_dir)) == original
    assert not os.path.exists(firmware_registry.registry_path(state_dir) + ".pre-fleet")

    # Rollback: the frame runs 1.0.2 and 1.0.1 is scheduled.
    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.0.1", "fw-v1.0.2") == "scheduled"
    sha, data = images["fw-v1.0.1"]
    offer = poll(byos_module, state_dir, LEGACY_TOKEN, tokens, fw_version="fw-v1.0.2")
    assert offer == {
        "version": "fw-v1.0.1",
        "url": "http://example.org/fw/" + sha + ".bin",
        "sha256": "sha256:" + sha,
        "size": len(data),
    }
    # A frame already on the scheduled version is offered nothing.
    assert poll(byos_module, state_dir, LEGACY_TOKEN, tokens, fw_version="fw-v1.0.1") is None


def test_legacy_shaped_update_view_is_unchanged(tmp_path):
    state_dir = str(tmp_path)
    legacy_registry_with_images(state_dir)
    seed_devices_json(state_dir, [LEGACY_MAC])
    report = {"schema": 1, "next_seq": 0, "devices": {
        LEGACY_MAC: {"fw_version": "fw-v1.0.2", "reported_at": "2026-10-01T00:00:00+00:00",
                     "events": []}}}

    view = firmware_registry.update_view(
        firmware_registry.load_registry(state_dir), report, "2026-10-02T00:00:00+00:00")

    assert view["running_version"] == "fw-v1.0.2"
    assert view["state"] == "available"
    assert view["cancellable"] is False
    assert view["rollback"] is None
    assert view["target_version"] is None
    by_version = {r["version"]: r for r in view["releases"]}
    assert set(by_version) == {"fw-v1.0.0", "fw-v1.0.1", "fw-v1.0.2"}
    assert by_version["fw-v1.0.2"]["running"] is True
    assert by_version["fw-v1.0.2"]["installable"] is False
    assert by_version["fw-v1.0.1"]["direction"] == "older"
    assert by_version["fw-v1.0.1"]["installable"] is True
    assert by_version["fw-v1.0.0"]["direction"] == "older"


def test_pre_fleet_copy_is_byte_identical_and_written_once(byos_module, tmp_path):
    state_dir = str(tmp_path)
    images, original = legacy_registry_with_images(state_dir)
    seed_devices_json(state_dir, [LEGACY_MAC])
    tokens = {LEGACY_MAC: LEGACY_TOKEN}
    registry_file = firmware_registry.registry_path(state_dir)
    pre_fleet = registry_file + ".pre-fleet"

    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.0.1", "fw-v1.0.2") == "scheduled"
    assert read_bytes(pre_fleet) == original
    after_schedule = read_bytes(registry_file)
    assert after_schedule != original

    assert firmware_registry.cancel_schedule(state_dir) == "cancelled"
    assert read_bytes(pre_fleet) == original

    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.0.1", "fw-v1.0.2") == "scheduled"
    assert poll(byos_module, state_dir, LEGACY_TOKEN, tokens, fw_version="fw-v1.0.2") is not None
    poll(byos_module, state_dir, LEGACY_TOKEN, tokens, fw_version="fw-v1.0.1",
         extra={"X-Ota-Result": "installed;fw-v1.0.1"})
    assert firmware_registry.apply_reconcile_all(state_dir) == [("installed", "fw-v1.0.1", None)]
    assert read_bytes(pre_fleet) == original

    publish_sha = write_legacy_dir_release(os.path.join(state_dir, "tags"), "fw-v1.1.0")
    code, _, _ = run_cli(["--state-dir", state_dir, "import-dir", os.path.join(state_dir, "tags")])
    assert code == 0
    assert read_bytes(pre_fleet) == original
    registry = firmware_registry.load_registry(state_dir)
    assert registry["releases"][-1]["sha256"] == publish_sha

    # The on-disk legacy shape carries no per-release type or build.
    on_disk = json.loads(read_bytes(registry_file))
    assert all("hardware_type" not in r and "build" not in r for r in on_disk["releases"])


def test_legacy_shaped_registry_is_served_over_fw_by_a_real_byos(tmp_path):
    state_dir = str(tmp_path)
    images, _ = legacy_registry_with_images(state_dir)
    seed_devices_json(state_dir, [LEGACY_MAC])
    with open(os.path.join(state_dir, "byos_state.json"), "w") as fh:
        json.dump({"tokens": {LEGACY_MAC: LEGACY_TOKEN}}, fh)
    panel = os.path.join(state_dir, "panel.bin")
    with open(panel, "wb") as fh:
        fh.write(bytes([0x11]) * 960000)
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    log = open(os.path.join(state_dir, "server.log"), "w")
    proc = subprocess.Popen(
        [sys.executable, SERVER_PATH, "--image", panel, "--port", str(port),
         "--sleep", "300", "--state-dir", state_dir],
        stdout=log, stderr=subprocess.STDOUT, env=child_env())
    log.close()
    try:
        deadline = time.time() + 10
        while time.time() < deadline:
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.1)
        else:
            raise RuntimeError("byos did not start")
        for version, (sha, data) in images.items():
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d/fw/%s.bin" % (port, sha), timeout=10) as resp:
                assert resp.status == 200
                assert resp.read() == data, version
    finally:
        proc.terminate()
        proc.wait(timeout=5)


def test_live_frame_report_entry_differs_only_by_the_hardware_type(byos_module, tmp_path):
    state_dir = str(tmp_path)
    legacy_registry_with_images(state_dir)
    seed_devices_json(state_dir, [LEGACY_MAC])
    tokens = {LEGACY_MAC: LEGACY_TOKEN}
    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.0.1", "fw-v1.0.2") == "scheduled"

    poll(byos_module, state_dir, LEGACY_TOKEN, tokens, fw_version="fw-v1.0.2")
    entry = report_entry(state_dir, LEGACY_MAC)

    stamped = entry.pop("hardware_type", hardware.LEGACY_KEY)
    assert stamped == hardware.LEGACY_KEY
    assert set(entry) == {"fw_version", "reported_at", "events"}
    assert entry["fw_version"] == "fw-v1.0.2"
    assert [e["kind"] for e in entry["events"]] == ["offered"]
    assert entry["events"][0]["version"] == "fw-v1.0.1"


def test_legacy_frame_without_a_fleet_row_keeps_working_when_fleet_db_is_faulted(
        byos_module, tmp_path, sim_gate):
    state_dir = str(tmp_path)
    legacy_registry_with_images(state_dir)
    seed_devices_json(state_dir, [LEGACY_MAC])
    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.0.1", "fw-v1.0.2") == "scheduled"
    tokens = {LEGACY_MAC: LEGACY_TOKEN, CLONE_MAC: CLONE_TOKEN}
    with open(os.path.join(state_dir, "fleet.db"), "wb") as fh:
        fh.write(b"this is not a sqlite database")

    legacy_offer = poll(byos_module, state_dir, LEGACY_TOKEN, tokens, fw_version="fw-v1.0.2")
    fleet_only_offer = poll(byos_module, state_dir, CLONE_TOKEN, tokens, fw_version="fw-v1.0.2")

    assert legacy_offer is not None and legacy_offer["version"] == "fw-v1.0.1"
    assert fleet_only_offer is None
    assert report_entry(state_dir, CLONE_MAC)["hardware_type"] == firmware_registry.UNRESOLVED_TYPE


# --- Two simulated hardware types, end to end --------------------------------


@pytest.fixture
def two_type_fleet(byos_module, tmp_path, sim_gate):
    """Legacy registry with the pre-change releases plus two simulated
    types and one fleet.db device of each of the three types.
    """
    state_dir = str(tmp_path / "state")
    os.makedirs(state_dir)
    legacy_registry_with_images(state_dir)
    seed_fleet(state_dir, [(LEGACY_MAC, LEGACY_TOKEN, hardware.LEGACY_KEY),
                           (CLONE_MAC, CLONE_TOKEN, CLONE),
                           (LAND_MAC, LAND_TOKEN, LAND)])
    return state_dir, {LEGACY_MAC: LEGACY_TOKEN, CLONE_MAC: CLONE_TOKEN, LAND_MAC: LAND_TOKEN}


def import_tags(state_dir, base, tags_by_key):
    """Write per-type tag directories in build order and import them."""
    shas = {}
    for tag, keys in tags_by_key:
        for key in keys:
            shas[(tag, key)] = write_typed_release(base, tag, key)
    code, out, err = run_cli(["--state-dir", state_dir, "import-dir", base])
    return code, out, err, shas


def test_two_types_publish_schedule_and_poll_independently(byos_module, tmp_path, two_type_fleet):
    state_dir, tokens = two_type_fleet
    base = str(tmp_path / "tags")
    code, out, err, shas = import_tags(
        state_dir, base,
        [("fw-v1.2.0", [CLONE, LAND]), ("fw-v1.10.0", [CLONE]), ("fw-v1.3.0", [LAND])])
    assert code == 0, err
    assert "added fw-v1.2.0 %s" % CLONE in out
    assert "added fw-v1.10.0 %s" % CLONE in out

    clone_versions = [r["version"] for r in firmware_registry.load_registry(state_dir, CLONE)["releases"]]
    assert clone_versions == ["fw-v1.2.0", "fw-v1.10.0"]
    legacy_versions = [r["version"] for r in firmware_registry.load_registry(state_dir)["releases"]]
    assert legacy_versions == ["fw-v1.0.0", "fw-v1.0.1", "fw-v1.0.2"]

    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.10.0", None, hardware_type=CLONE) == "scheduled"
    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.2.0", None, hardware_type=LAND) == "scheduled"

    clone_offer = poll(byos_module, state_dir, CLONE_TOKEN, tokens)
    land_offer = poll(byos_module, state_dir, LAND_TOKEN, tokens)
    legacy_offer = poll(byos_module, state_dir, LEGACY_TOKEN, tokens)

    assert clone_offer["version"] == "fw-v1.10.0"
    assert clone_offer["sha256"] == "sha256:" + shas[("fw-v1.10.0", CLONE)]
    assert land_offer["version"] == "fw-v1.2.0"
    assert land_offer["sha256"] == "sha256:" + shas[("fw-v1.2.0", LAND)]
    assert legacy_offer is None
    assert report_entry(state_dir, CLONE_MAC)["hardware_type"] == CLONE
    assert report_entry(state_dir, LAND_MAC)["hardware_type"] == LAND
    assert report_entry(state_dir, LEGACY_MAC)["hardware_type"] == hardware.LEGACY_KEY

    # An offered schedule is acknowledged, hence not cancellable, and the
    # refusal is per type: the legacy document has nothing to cancel.
    assert firmware_registry.cancel_schedule(state_dir, hardware_type=LAND) == "not_cancellable"
    assert firmware_registry.cancel_schedule(state_dir) == "none"
    assert poll(byos_module, state_dir, CLONE_TOKEN, tokens)["version"] == "fw-v1.10.0"


def test_reconcile_moves_only_the_owning_types_schedule(byos_module, tmp_path, two_type_fleet):
    state_dir, tokens = two_type_fleet
    code, _, err, _ = import_tags(
        state_dir, str(tmp_path / "tags"), [("fw-v1.2.0", [CLONE, LAND])])
    assert code == 0, err
    for key in (CLONE, LAND):
        assert firmware_registry.schedule_release(
            state_dir, "fw-v1.2.0", None, hardware_type=key) == "scheduled"
    assert firmware_registry.schedule_release(
        state_dir, "fw-v1.0.1", "fw-v1.0.2") == "scheduled"
    legacy_before = read_bytes(firmware_registry.registry_path(state_dir))
    land_before = read_bytes(firmware_registry.registry_path(state_dir, LAND))
    assert poll(byos_module, state_dir, CLONE_TOKEN, tokens) is not None

    poll(byos_module, state_dir, CLONE_TOKEN, tokens, fw_version="fw-v1.2.0",
         extra={"X-Ota-Result": "installed;fw-v1.2.0"})
    outcomes = firmware_registry.apply_reconcile_all(state_dir)

    assert outcomes == [("installed", "fw-v1.2.0", None)]
    clone = firmware_registry.load_registry(state_dir, CLONE)
    assert clone["schedule"] is None and clone["last_outcome"]["kind"] == "installed"
    assert read_bytes(firmware_registry.registry_path(state_dir)) == legacy_before
    assert read_bytes(firmware_registry.registry_path(state_dir, LAND)) == land_before
    assert firmware_registry.load_registry(state_dir, LAND)["schedule"]["version"] == "fw-v1.2.0"


def test_wrong_binaries_and_lower_builds_are_refused_with_no_registry_change(
        tmp_path, two_type_fleet):
    state_dir, _ = two_type_fleet
    base = str(tmp_path / "tags")
    code, _, err, _ = import_tags(state_dir, base, [("fw-v1.2.0", [CLONE])])
    assert code == 0, err
    before = snapshot_firmware_dir(state_dir)

    cases = {
        "fw-v1.1.0": dict(),  # lower build than the registered 1.2.0
        "fw-v1.3.0": dict(chip_id=0x0005),  # wrong chip
        "fw-v1.4.0": dict(project_name="other-project"),  # wrong project name
    }
    for tag, kwargs in cases.items():
        write_typed_release(base, tag, CLONE, **kwargs)
        code, _, err = run_cli(["--state-dir", state_dir, "import-dir", base])
        assert code != 0, tag
        assert "[%s]" % CLONE in err and tag in err, (tag, err)
        assert snapshot_firmware_dir(state_dir) == before, tag
        shutil.rmtree(os.path.join(base, tag))

    # A manifest that declares a different type than its file name is refused too.
    write_typed_release(base, "fw-v1.5.0", CLONE, declared_key=LAND)
    code, _, err = run_cli(["--state-dir", state_dir, "import-dir", base])
    assert code != 0 and "hardware_type" in err
    assert snapshot_firmware_dir(state_dir) == before


def test_import_dir_is_idempotent(tmp_path, two_type_fleet):
    state_dir, _ = two_type_fleet
    base = str(tmp_path / "tags")
    code, _, err, _ = import_tags(
        state_dir, base, [("fw-v1.2.0", [CLONE, LAND]), ("fw-v1.3.0", [CLONE])])
    assert code == 0, err
    before = snapshot_firmware_dir(state_dir)

    code, out, err = run_cli(["--state-dir", state_dir, "import-dir", base])

    assert code == 0, err
    assert "added" not in out
    assert snapshot_firmware_dir(state_dir) == before


def test_each_type_image_is_served_by_fw_route_membership(byos_module, tmp_path, two_type_fleet):
    state_dir, tokens = two_type_fleet
    code, _, err, shas = import_tags(
        state_dir, str(tmp_path / "tags"), [("fw-v1.2.0", [CLONE, LAND])])
    assert code == 0, err
    for key in (CLONE, LAND):
        assert byos_module._is_registered_release(state_dir, shas[("fw-v1.2.0", key)])
    assert not byos_module._is_registered_release(state_dir, "b" * 64)
