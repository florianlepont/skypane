"""The Update card and version history of a frame that is not the live one:
the registry and the device report live in the root state directory (where
byos and the firmware CLI keep them), while the frame's own directory holds
only its own files. Served HTML is the assertion surface."""
import hashlib
import json
import os

import pytest

import companion.page_context as page_context
import companion.prefs as prefs
from companion.pages import update_page
from companion_markup import parse_html
from server import atomic_io
from server import firmware_registry as fr
from server import hardware

_NOW = "2026-09-28T12:00:00+00:00"
_SECOND_TYPE = "seeed-ee04-7in3-spectra6"


def _release(version, published_at=_NOW):
    return {
        "version": version, "sha256": hashlib.sha256(version.encode()).hexdigest(),
        "size": 10, "released_at": published_at, "published_at": published_at,
        "commit": "a" * 40, "notes": [], "bench": False, "installed_at": [],
    }


def _write_registry(state_dir, hardware_type, versions):
    doc = fr._default_registry(hardware_type)
    doc["releases"] = [_release(version) for version in versions]
    fr._save_registry(state_dir, doc, hardware_type)


def _write_device_report(state_dir, hardware_type, fw_version):
    fr._ensure_firmware_dir(state_dir)
    report = {"schema": 1, "next_seq": 0, "devices": {"dev1": {
        "fw_version": fw_version, "reported_at": _NOW, "events": [],
        "hardware_type": hardware_type}}}
    atomic_io.atomic_write(fr.device_report_path(state_dir), json.dumps(report))


def _served(root, frame_dir, hardware_type):
    ctx = page_context.coerce({
        "state_dir": frame_dir, "root_state_dir": root, "now": _NOW})
    try:
        prefs.set_request_prefs(lang="en")
        device_html, versions_html, _summary = update_page.render_parts(
            ctx, hardware_type, "Model X")
    finally:
        prefs.set_request_prefs(lang="en")
    return device_html + versions_html


@pytest.fixture
def second_type_enabled(monkeypatch):
    monkeypatch.setenv(hardware.SECOND_ENV_VAR, "1")


def test_non_live_frame_card_reads_the_root_registry_and_report(
        tmp_path, second_type_enabled):
    """a frame with its own directory still shows the releases and the firmware version
    that the root state directory holds for its hardware type"""
    root = str(tmp_path)
    frame_dir = os.path.join(root, "devices", "frame2")
    os.makedirs(frame_dir)
    _write_registry(root, _SECOND_TYPE, ["fw-v1.2.0", "fw-v1.2.1"])
    _write_device_report(root, _SECOND_TYPE, "fw-v1.2.0")
    text = _served(root, frame_dir, _SECOND_TYPE)
    doc = parse_html(text)
    versions = [node.text() for node in doc.select("li.update-item .update-item__version")]
    assert sorted(versions) == ["fw-v1.2.0", "fw-v1.2.1"]
    assert doc.select_one(".update-sum__version").text() == "fw-v1.2.0"
    assert "No version reported yet" not in text
    assert "No releases yet" not in text
    assert "Update available" in text


def test_live_frame_output_is_the_same_whichever_directory_is_named(tmp_path):
    """for the live frame the root and the frame directory are one directory, so the
    served card is identical to what it was before the root directory was read"""
    root = str(tmp_path)
    _write_registry(root, hardware.LEGACY_KEY, ["fw-v1.0.0", "fw-v1.1.0"])
    _write_device_report(root, hardware.LEGACY_KEY, "fw-v1.0.0")
    same = _served(root, root, hardware.LEGACY_KEY)
    ctx = page_context.coerce({"state_dir": root, "now": _NOW})
    prefs.set_request_prefs(lang="en")
    without_root = "".join(update_page.render_parts(ctx, hardware.LEGACY_KEY, "Model X")[:2])
    assert same == without_root
    assert "fw-v1.1.0" in same
