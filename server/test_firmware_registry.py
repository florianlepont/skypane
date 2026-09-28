"""Behaviour tests for server/firmware_registry.py: the release registry
storage, publish/schedule/cancel, and the pure offer/reconcile/view
functions every other OTA surface uses.

Every assertion is about observable behaviour (return values, files on
disk, registry contents) -- never about the module's source text.
"""
import hashlib
import multiprocessing
import os

import pytest

from server import firmware_registry as registry_mod

RUNNING_VERSION = "fw-v1.0.0"
NEXT_VERSION = "fw-v1.1.0"
OLDER_VERSION = "fw-v1.0.0"  # equal to the floor -- an "older" release still at the floor
BELOW_FLOOR_VERSION = "fw-v0.9.0"
NOW = "2026-09-28T12:00:00+00:00"
LATER = "2026-09-28T12:05:00+00:00"


def _image_bytes(tag=b"firmware-image"):
    return tag + b"-payload"


def _manifest_for(image, version, **overrides):
    manifest = {
        "version": version,
        "sha256": hashlib.sha256(image).hexdigest(),
        "size": len(image),
        "released_at": "2026-09-28",
        "commit": "a" * 40,
        "notes": ["Fixed the thing"],
    }
    manifest.update(overrides)
    return manifest


def _write_image(tmp_path, image, name="image.bin"):
    path = tmp_path / name
    path.write_bytes(image)
    return str(path)


def _publish(tmp_path, version=NEXT_VERSION, image=None, bench=False, now=NOW):
    image = image if image is not None else _image_bytes(version.encode())
    image_path = _write_image(tmp_path, image, name=version + ".bin")
    manifest = _manifest_for(image, version)
    outcome = registry_mod.publish_release(str(tmp_path), manifest, image_path, bench=bench, now=now)
    return outcome, manifest


# --- load_registry / load_device_report tolerant loading -----------------

def test_load_registry_missing_dir_returns_defaults(tmp_path):
    missing = tmp_path / "does-not-exist"
    doc = registry_mod.load_registry(str(missing))
    assert doc == {
        "schema": 1, "floor_version": registry_mod.FLOOR_VERSION,
        "releases": [], "schedule": None, "last_outcome": None,
        "reconciled_seq": 0,
    }


def test_load_registry_empty_file_returns_defaults(tmp_path):
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)))
    with open(registry_mod.registry_path(str(tmp_path)), "w") as fh:
        fh.write("")
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["releases"] == [] and doc["schedule"] is None


def test_load_registry_non_json_returns_defaults(tmp_path):
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)))
    with open(registry_mod.registry_path(str(tmp_path)), "w") as fh:
        fh.write("{not json")
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["releases"] == []


def test_load_registry_wrong_shape_returns_defaults(tmp_path):
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)))
    with open(registry_mod.registry_path(str(tmp_path)), "w") as fh:
        fh.write("[1, 2, 3]")
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc == registry_mod._default_registry()


def test_load_registry_never_raises_on_hostile_release_entries(tmp_path):
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)))
    with open(registry_mod.registry_path(str(tmp_path)), "w") as fh:
        fh.write('{"releases": ["not-a-dict", {"version": "../../etc/passwd"}], "schedule": "nope"}')
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["releases"] == []
    assert doc["schedule"] is None


def test_load_device_report_missing_file_returns_defaults(tmp_path):
    doc = registry_mod.load_device_report(str(tmp_path))
    assert doc == {"schema": 1, "next_seq": 0, "devices": {}}


def test_load_device_report_hostile_content_never_raises(tmp_path):
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)))
    with open(registry_mod.device_report_path(str(tmp_path)), "w") as fh:
        fh.write('{"devices": {"aa": {"events": [1, "x", {"seq": "not-an-int"}]}}}')
    doc = registry_mod.load_device_report(str(tmp_path))
    assert doc["devices"]["aa"]["events"] == []


# --- publish_release -------------------------------------------------------

def test_publish_release_adds_entry_and_copies_image(tmp_path):
    outcome, manifest = _publish(tmp_path)
    assert outcome == "added"
    doc = registry_mod.load_registry(str(tmp_path))
    assert len(doc["releases"]) == 1
    entry = doc["releases"][0]
    assert entry["version"] == NEXT_VERSION
    assert entry["sha256"] == manifest["sha256"]
    assert entry["installed_at"] == []
    image_target = registry_mod.firmware_image_path(str(tmp_path), manifest["sha256"])
    with open(image_target, "rb") as fh:
        assert fh.read() == _image_bytes(NEXT_VERSION.encode())


def test_publish_release_idempotent_same_manifest_returns_exists(tmp_path):
    outcome1, _ = _publish(tmp_path)
    outcome2, _ = _publish(tmp_path)
    assert outcome1 == "added"
    assert outcome2 == "exists"
    doc = registry_mod.load_registry(str(tmp_path))
    assert len(doc["releases"]) == 1


def test_publish_release_rejects_bad_version(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, "not-a-version")
    with pytest.raises(ValueError, match="version"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_rejects_bad_sha256_shape(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION, sha256="not-64-hex")
    with pytest.raises(ValueError, match="sha256"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_rejects_hash_mismatch(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION)
    manifest["sha256"] = hashlib.sha256(b"different-bytes").hexdigest()
    with pytest.raises(ValueError, match="sha256"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_rejects_size_mismatch(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION)
    manifest["size"] = len(image) + 1
    with pytest.raises(ValueError, match="size"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_rejects_oversized_image(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION)
    manifest["size"] = registry_mod.MAX_IMAGE_BYTES + 1
    with pytest.raises(ValueError, match="size"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_rejects_zero_size(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION)
    manifest["size"] = 0
    with pytest.raises(ValueError, match="size"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_rejects_different_sha_same_version(tmp_path):
    _publish(tmp_path)
    other_image = _image_bytes(b"a-completely-different-image")
    other_path = _write_image(tmp_path, other_image, name="other.bin")
    other_manifest = _manifest_for(other_image, NEXT_VERSION)
    with pytest.raises(ValueError, match="version"):
        registry_mod.publish_release(str(tmp_path), other_manifest, other_path)


def test_publish_release_accepts_bench_version_with_suffix(tmp_path):
    image = _image_bytes(b"bench-image")
    image_path = _write_image(tmp_path, image, name="bench.bin")
    manifest = _manifest_for(image, "fw-v1.1.0-bench1")
    outcome = registry_mod.publish_release(str(tmp_path), manifest, image_path, bench=True)
    assert outcome == "added"
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["releases"][0]["bench"] is True


def test_publish_release_rejects_bench_suffix_without_bench_flag(tmp_path):
    image = _image_bytes(b"bench-image-2")
    image_path = _write_image(tmp_path, image, name="bench2.bin")
    manifest = _manifest_for(image, "fw-v1.1.0-bench1")
    with pytest.raises(ValueError, match="version"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path, bench=False)


def test_publish_release_never_deletes_a_release_or_image(tmp_path):
    _publish(tmp_path, version="fw-v1.1.0")
    _publish(tmp_path, version="fw-v1.2.0")
    doc_before = registry_mod.load_registry(str(tmp_path))
    _publish(tmp_path, version="fw-v1.1.0")  # idempotent republish
    doc_after = registry_mod.load_registry(str(tmp_path))
    assert len(doc_after["releases"]) == len(doc_before["releases"])
    for release in doc_before["releases"]:
        image_path = registry_mod.firmware_image_path(str(tmp_path), release["sha256"])
        assert os.path.exists(image_path)


# --- schedule_release / cancel_schedule / acknowledged --------------------

def test_schedule_release_returns_scheduled_and_writes_schedule(tmp_path):
    _publish(tmp_path)
    outcome = registry_mod.schedule_release(str(tmp_path), NEXT_VERSION, RUNNING_VERSION, now=NOW)
    assert outcome == "scheduled"
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["schedule"]["version"] == NEXT_VERSION
    assert doc["schedule"]["state"] == "scheduled"
    assert doc["schedule"]["attempts"] == 0
    assert doc["schedule"]["id"]


def test_schedule_release_unknown_version(tmp_path):
    outcome = registry_mod.schedule_release(str(tmp_path), "fw-v9.9.9", RUNNING_VERSION, now=NOW)
    assert outcome == "unknown"


def test_schedule_release_below_floor(tmp_path):
    image = _image_bytes(b"below-floor")
    image_path = _write_image(tmp_path, image, name="below.bin")
    manifest = _manifest_for(image, BELOW_FLOOR_VERSION)
    registry_mod.publish_release(str(tmp_path), manifest, image_path)
    outcome = registry_mod.schedule_release(str(tmp_path), BELOW_FLOOR_VERSION, "fw-v1.5.0", now=NOW)
    assert outcome == "below_floor"


def test_schedule_release_same_as_running(tmp_path):
    _publish(tmp_path)
    outcome = registry_mod.schedule_release(str(tmp_path), NEXT_VERSION, NEXT_VERSION, now=NOW)
    assert outcome == "same_as_running"


def test_schedule_release_older_release_schedules_successfully(tmp_path):
    image = _image_bytes(b"older-release")
    image_path = _write_image(tmp_path, image, name="older.bin")
    manifest = _manifest_for(image, OLDER_VERSION)  # equals the floor, older than a running fw-v1.2.0
    registry_mod.publish_release(str(tmp_path), manifest, image_path)
    outcome = registry_mod.schedule_release(str(tmp_path), OLDER_VERSION, "fw-v1.2.0", now=NOW)
    assert outcome == "scheduled"


def test_schedule_release_replaces_failed_schedule(tmp_path):
    _publish(tmp_path, version="fw-v1.1.0")
    _publish(tmp_path, version="fw-v1.2.0")
    registry_mod.schedule_release(str(tmp_path), "fw-v1.1.0", RUNNING_VERSION, now=NOW)
    doc = registry_mod.load_registry(str(tmp_path))
    doc["schedule"]["state"] = "failed"
    registry_mod._save_registry(str(tmp_path), doc)
    outcome = registry_mod.schedule_release(str(tmp_path), "fw-v1.2.0", RUNNING_VERSION, now=LATER)
    assert outcome == "scheduled"
    doc2 = registry_mod.load_registry(str(tmp_path))
    assert doc2["schedule"]["version"] == "fw-v1.2.0"


def test_schedule_release_replaces_unacknowledged_schedule(tmp_path):
    _publish(tmp_path, version="fw-v1.1.0")
    _publish(tmp_path, version="fw-v1.2.0")
    registry_mod.schedule_release(str(tmp_path), "fw-v1.1.0", RUNNING_VERSION, now=NOW)
    outcome = registry_mod.schedule_release(str(tmp_path), "fw-v1.2.0", RUNNING_VERSION, now=LATER)
    assert outcome == "scheduled"
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["schedule"]["version"] == "fw-v1.2.0"


def test_schedule_release_busy_when_acknowledged(tmp_path):
    _publish(tmp_path, version="fw-v1.1.0")
    _publish(tmp_path, version="fw-v1.2.0")
    registry_mod.schedule_release(str(tmp_path), "fw-v1.1.0", RUNNING_VERSION, now=NOW)
    doc = registry_mod.load_registry(str(tmp_path))
    schedule_id = doc["schedule"]["id"]
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)), exist_ok=True)
    device_report = {
        "schema": 1, "next_seq": 1,
        "devices": {"aa:bb:cc:dd:ee:ff": {
            "fw_version": RUNNING_VERSION, "reported_at": NOW,
            "events": [{"seq": 1, "at": NOW, "kind": "offered", "schedule_id": schedule_id, "token": None, "version": "fw-v1.1.0"}],
        }},
    }
    import json
    with open(registry_mod.device_report_path(str(tmp_path)), "w") as fh:
        json.dump(device_report, fh)
    outcome = registry_mod.schedule_release(str(tmp_path), "fw-v1.2.0", RUNNING_VERSION, now=LATER)
    assert outcome == "busy"
    doc2 = registry_mod.load_registry(str(tmp_path))
    assert doc2["schedule"]["version"] == "fw-v1.1.0"


def _make_device_report(events, fw_version=RUNNING_VERSION, next_seq=None):
    if next_seq is None:
        next_seq = (max((e["seq"] for e in events), default=0)) + 1
    return {
        "schema": 1, "next_seq": next_seq,
        "devices": {"aa:bb:cc:dd:ee:ff": {
            "fw_version": fw_version, "reported_at": NOW, "events": events,
        }},
    }


def test_acknowledged_offered_event(tmp_path):
    schedule = {"id": "sched1"}
    device_report = _make_device_report([
        {"seq": 1, "at": NOW, "kind": "offered", "schedule_id": "sched1", "token": None, "version": NEXT_VERSION},
    ])
    assert registry_mod.acknowledged(schedule, device_report) is True


def test_acknowledged_result_event_not_deferred(tmp_path):
    schedule = {"id": "sched1"}
    device_report = _make_device_report([
        {"seq": 1, "at": NOW, "kind": "result", "schedule_id": "sched1", "token": "trial", "version": NEXT_VERSION},
    ])
    assert registry_mod.acknowledged(schedule, device_report) is True


def test_acknowledged_no_event(tmp_path):
    schedule = {"id": "sched1"}
    device_report = _make_device_report([])
    assert registry_mod.acknowledged(schedule, device_report) is False


def test_acknowledged_deferred_battery_newest_result(tmp_path):
    schedule = {"id": "sched1"}
    device_report = _make_device_report([
        {"seq": 1, "at": NOW, "kind": "offered", "schedule_id": "sched1", "token": None, "version": NEXT_VERSION},
        {"seq": 2, "at": LATER, "kind": "result", "schedule_id": "sched1", "token": "deferred-battery", "version": NEXT_VERSION},
    ])
    assert registry_mod.acknowledged(schedule, device_report) is False


def test_cancel_schedule_cancels_when_not_acknowledged(tmp_path):
    _publish(tmp_path)
    registry_mod.schedule_release(str(tmp_path), NEXT_VERSION, RUNNING_VERSION, now=NOW)
    outcome = registry_mod.cancel_schedule(str(tmp_path))
    assert outcome == "cancelled"
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["schedule"] is None


def test_cancel_schedule_not_cancellable_when_acknowledged(tmp_path):
    _publish(tmp_path)
    registry_mod.schedule_release(str(tmp_path), NEXT_VERSION, RUNNING_VERSION, now=NOW)
    doc = registry_mod.load_registry(str(tmp_path))
    schedule_id = doc["schedule"]["id"]
    import json
    device_report = _make_device_report([
        {"seq": 1, "at": NOW, "kind": "offered", "schedule_id": schedule_id, "token": None, "version": NEXT_VERSION},
    ])
    with open(registry_mod.device_report_path(str(tmp_path)), "w") as fh:
        json.dump(device_report, fh)
    outcome = registry_mod.cancel_schedule(str(tmp_path))
    assert outcome == "not_cancellable"
    doc2 = registry_mod.load_registry(str(tmp_path))
    assert doc2["schedule"] is not None


def test_cancel_schedule_none_when_nothing_scheduled(tmp_path):
    outcome = registry_mod.cancel_schedule(str(tmp_path))
    assert outcome == "none"


# --- concurrency: no lost update -------------------------------------------

def _publish_worker(state_dir, count):
    for i in range(count):
        version = "fw-v2.%d.0" % i
        image = ("worker-a-image-%d" % i).encode()
        image_path = os.path.join(state_dir, "src-%d.bin" % i)
        with open(image_path, "wb") as fh:
            fh.write(image)
        manifest = {
            "version": version,
            "sha256": hashlib.sha256(image).hexdigest(),
            "size": len(image),
            "released_at": "2026-09-28",
            "commit": "b" * 40,
            "notes": [],
        }
        registry_mod.publish_release(state_dir, manifest, image_path)


def _schedule_worker(state_dir, count):
    versions = ["fw-v1.1.0", "fw-v1.2.0"]
    for i in range(count):
        registry_mod.schedule_release(state_dir, versions[i % 2], RUNNING_VERSION)


def test_concurrent_publish_and_schedule_loses_no_update(tmp_path):
    state_dir = str(tmp_path)
    for seed_version in ("fw-v1.1.0", "fw-v1.2.0"):
        image = ("seed-%s" % seed_version).encode()
        image_path = os.path.join(state_dir, seed_version + "-seed.bin")
        with open(image_path, "wb") as fh:
            fh.write(image)
        manifest = {
            "version": seed_version,
            "sha256": hashlib.sha256(image).hexdigest(),
            "size": len(image),
            "released_at": "2026-09-28",
            "commit": "c" * 40,
            "notes": [],
        }
        registry_mod.publish_release(state_dir, manifest, image_path)

    count = 50
    p1 = multiprocessing.Process(target=_publish_worker, args=(state_dir, count))
    p2 = multiprocessing.Process(target=_schedule_worker, args=(state_dir, count))
    p1.start()
    p2.start()
    p1.join(timeout=60)
    p2.join(timeout=60)
    assert p1.exitcode == 0
    assert p2.exitcode == 0

    doc = registry_mod.load_registry(state_dir)
    assert len(doc["releases"]) == 2 + count
    published_versions = {r["version"] for r in doc["releases"]}
    for i in range(count):
        assert ("fw-v2.%d.0" % i) in published_versions
    assert doc["schedule"] is not None
    assert doc["schedule"]["version"] in ("fw-v1.1.0", "fw-v1.2.0")
    for release in doc["releases"]:
        image_path = registry_mod.firmware_image_path(state_dir, release["sha256"])
        assert os.path.exists(image_path)


# --- additional coverage: small helpers and every tolerant-degrade branch --

def test_firmware_image_path_rejects_non_hex_or_non_string(tmp_path):
    assert registry_mod.firmware_image_path(str(tmp_path), "not-hex") is None
    assert registry_mod.firmware_image_path(str(tmp_path), 12345) is None
    assert registry_mod.firmware_image_path(str(tmp_path), "a" * 64).endswith("a" * 64 + ".bin")


def test_parse_version_rejects_non_string_and_unmatched_pattern():
    assert registry_mod.parse_version(None) is None
    assert registry_mod.parse_version(123) is None
    assert registry_mod.parse_version("not-a-version") is None
    assert registry_mod.parse_version("fw-v" + "9" * 40) is None  # over VERSION_MAX_LEN


def test_at_or_above_floor_unparsable_inputs_return_false():
    assert registry_mod.at_or_above_floor("not-a-version", registry_mod.FLOOR_VERSION) is False
    assert registry_mod.at_or_above_floor(NEXT_VERSION, "also-not-a-version") is False


def _write_registry_json(tmp_path, doc):
    import json
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)), exist_ok=True)
    with open(registry_mod.registry_path(str(tmp_path)), "w") as fh:
        json.dump(doc, fh)


def test_load_registry_filters_individually_malformed_release_fields(tmp_path):
    base = {
        "version": "fw-v9.9.9", "sha256": "a" * 64, "size": 10,
        "released_at": "2026-09-28", "published_at": NOW, "commit": "a" * 40,
        "notes": [], "bench": False, "installed_at": [],
    }
    bad_sha = dict(base, sha256="not-hex")
    bad_size = dict(base, size=0)
    missing_released_at = {k: v for k, v in base.items() if k != "released_at"}
    missing_published_at = {k: v for k, v in base.items() if k != "published_at"}
    missing_commit = {k: v for k, v in base.items() if k != "commit"}
    _write_registry_json(tmp_path, {
        "schema": 1, "floor_version": registry_mod.FLOOR_VERSION,
        "releases": [bad_sha, bad_size, missing_released_at, missing_published_at, missing_commit],
        "schedule": None, "last_outcome": None, "reconciled_seq": 0,
    })
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["releases"] == []


@pytest.mark.parametrize("override", [
    {"id": None},
    {"id": ""},
    {"version": None},
    {"sha256": "not-hex"},
    {"scheduled_at": None},
    {"state": "bogus"},
])
def test_load_registry_schedule_malformed_fields_degrade_to_none(tmp_path, override):
    schedule = dict({
        "id": "sched1", "version": NEXT_VERSION, "sha256": "a" * 64,
        "scheduled_at": NOW, "state": "scheduled", "attempts": 0,
        "failed_at": None, "last_result": None,
    }, **override)
    _write_registry_json(tmp_path, {
        "schema": 1, "floor_version": registry_mod.FLOOR_VERSION,
        "releases": [], "schedule": schedule, "last_outcome": None, "reconciled_seq": 0,
    })
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["schedule"] is None


@pytest.mark.parametrize("override", [
    {"kind": "bogus"},
    {"version": None},
    {"at": None},
])
def test_load_registry_last_outcome_malformed_fields_degrade_to_none(tmp_path, override):
    last_outcome = dict({"kind": "installed", "version": NEXT_VERSION, "back_on": None, "at": NOW}, **override)
    _write_registry_json(tmp_path, {
        "schema": 1, "floor_version": registry_mod.FLOOR_VERSION,
        "releases": [], "schedule": None, "last_outcome": last_outcome, "reconciled_seq": 0,
    })
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["last_outcome"] is None


def test_load_device_report_event_kind_and_at_validation(tmp_path):
    import json
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)), exist_ok=True)
    doc = {
        "schema": 1, "next_seq": 3,
        "devices": {"aa:bb:cc:dd:ee:ff": {
            "fw_version": RUNNING_VERSION, "reported_at": NOW,
            "events": [
                {"seq": 1, "at": NOW, "kind": "bogus-kind"},
                {"seq": 2, "at": 12345, "kind": "result"},
            ],
        }},
    }
    with open(registry_mod.device_report_path(str(tmp_path)), "w") as fh:
        json.dump(doc, fh)
    loaded = registry_mod.load_device_report(str(tmp_path))
    assert loaded["devices"]["aa:bb:cc:dd:ee:ff"]["events"] == []


def test_load_device_report_non_dict_device_entry_skipped(tmp_path):
    import json
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)), exist_ok=True)
    doc = {"schema": 1, "next_seq": 0, "devices": {"aa:bb:cc:dd:ee:ff": ["not", "a", "dict"]}}
    with open(registry_mod.device_report_path(str(tmp_path)), "w") as fh:
        json.dump(doc, fh)
    loaded = registry_mod.load_device_report(str(tmp_path))
    assert loaded["devices"] == {}


def test_load_device_report_non_dict_top_level_returns_default(tmp_path):
    os.makedirs(registry_mod.firmware_dir(str(tmp_path)), exist_ok=True)
    with open(registry_mod.device_report_path(str(tmp_path)), "w") as fh:
        fh.write("[1, 2, 3]")
    loaded = registry_mod.load_device_report(str(tmp_path))
    assert loaded == {"schema": 1, "next_seq": 0, "devices": {}}


def test_acknowledged_none_schedule_returns_false():
    assert registry_mod.acknowledged(None, _make_device_report([])) is False


def test_acknowledged_unknown_event_kind_returns_false():
    schedule = {"id": "sched1"}
    device_report = _make_device_report([
        {"seq": 1, "at": NOW, "kind": "mystery", "schedule_id": "sched1", "token": None, "version": NEXT_VERSION},
    ])
    assert registry_mod.acknowledged(schedule, device_report) is False


def test_publish_release_rejects_non_dict_manifest(tmp_path):
    image_path = _write_image(tmp_path, _image_bytes())
    with pytest.raises(ValueError, match="manifest"):
        registry_mod.publish_release(str(tmp_path), ["not", "a", "dict"], image_path)


def test_publish_release_rejects_missing_released_at(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION)
    del manifest["released_at"]
    with pytest.raises(ValueError, match="released_at"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_rejects_bad_commit(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION, commit="too-short")
    with pytest.raises(ValueError, match="commit"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


def test_publish_release_defaults_missing_notes_to_empty_list(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION)
    del manifest["notes"]
    outcome = registry_mod.publish_release(str(tmp_path), manifest, image_path)
    assert outcome == "added"
    doc = registry_mod.load_registry(str(tmp_path))
    assert doc["releases"][0]["notes"] == []


def test_publish_release_rejects_non_string_notes(tmp_path):
    image = _image_bytes()
    image_path = _write_image(tmp_path, image)
    manifest = _manifest_for(image, NEXT_VERSION, notes=["fine", 42])
    with pytest.raises(ValueError, match="notes"):
        registry_mod.publish_release(str(tmp_path), manifest, image_path)


