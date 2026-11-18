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
            ctx, hardware_type)
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
    assert doc.select_one("li.update-item--running .update-item__version").text() == "fw-v1.2.0"
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
    without_root = "".join(update_page.render_parts(ctx, hardware.LEGACY_KEY)[:2])
    assert same == without_root
    assert "fw-v1.1.0" in same


def _write_two_type_report(root, live_version, second_version):
    fr._ensure_firmware_dir(root)
    report = {"schema": 1, "next_seq": 0, "devices": {
        "live": {"fw_version": live_version, "reported_at": _NOW, "events": [],
                 "hardware_type": hardware.LEGACY_KEY},
        "frame2": {"fw_version": second_version, "reported_at": _NOW, "events": [],
                   "hardware_type": _SECOND_TYPE}}}
    atomic_io.atomic_write(fr.device_report_path(root), json.dumps(report))


def _two_type_root(tmp_path):
    root = str(tmp_path)
    frame_dir = os.path.join(root, "devices", "frame2")
    os.makedirs(frame_dir)
    _write_registry(root, hardware.LEGACY_KEY, ["fw-v1.0.0", "fw-v1.1.0"])
    _write_registry(root, _SECOND_TYPE, ["fw-v1.2.0", "fw-v1.2.1"])
    _write_two_type_report(root, "fw-v1.1.0", "fw-v1.2.0")
    return root, frame_dir


def _versions(text):
    doc = parse_html(text)
    return sorted(node.text() for node in doc.select("li.update-item .update-item__version"))


def test_live_frame_page_has_no_chooser_and_only_its_own_type(tmp_path, second_type_enabled):
    """with releases and reports for two types the live frame's page names no second
    type, lists only its releases and shows its own reported version"""
    root, _frame_dir = _two_type_root(tmp_path)
    text = _served(root, root, hardware.LEGACY_KEY)
    doc = parse_html(text)
    assert doc.select(".update-type-chooser") == []
    assert hardware.get_profile(_SECOND_TYPE).label not in text
    assert _versions(text) == ["fw-v1.0.0", "fw-v1.1.0"]
    assert doc.select_one("li.update-item--running .update-item__version").text() == "fw-v1.1.0"
    assert "fw-v1.2.0" not in text


def test_second_type_frame_page_has_no_chooser_and_only_its_own_type(
        tmp_path, second_type_enabled):
    """a non-live second-type frame shows only its own releases and no tab for the
    first type"""
    root, frame_dir = _two_type_root(tmp_path)
    text = _served(root, frame_dir, _SECOND_TYPE)
    doc = parse_html(text)
    assert doc.select(".update-type-chooser") == []
    assert hardware.get_profile(hardware.LEGACY_KEY).label not in text
    assert _versions(text) == ["fw-v1.2.0", "fw-v1.2.1"]
    assert doc.select_one("li.update-item--running .update-item__version").text() == "fw-v1.2.0"
    assert "fw-v1.1.0" not in text


def test_frame_whose_type_has_no_releases_shows_its_own_empty_state(
        tmp_path, second_type_enabled):
    """a second-type frame without releases shows the empty state, not the first type's list"""
    root = str(tmp_path)
    frame_dir = os.path.join(root, "devices", "frame2")
    os.makedirs(frame_dir)
    _write_registry(root, hardware.LEGACY_KEY, ["fw-v1.0.0", "fw-v1.1.0"])
    text = _served(root, frame_dir, _SECOND_TYPE)
    assert "No releases yet" in text
    assert _versions(text) == []
    assert parse_html(text).select(".update-type-chooser") == []


@pytest.mark.parametrize("lang,label", [("en", "Hardware type"), ("fr", "Type de matériel")])
def test_standalone_page_keeps_the_chooser_with_two_types(
        tmp_path, second_type_enabled, lang, label):
    """the standalone Update page still offers one tab per relevant type"""
    root, _frame_dir = _two_type_root(tmp_path)
    ctx = page_context.coerce({"state_dir": root, "root_state_dir": root, "now": _NOW})
    try:
        prefs.set_request_prefs(lang=lang)
        text = update_page.render(ctx, None)
    finally:
        prefs.set_request_prefs(lang="en")
    doc = parse_html(text)
    tabs = [(b.attrs["value"], b.attrs["aria-pressed"])
            for b in doc.select('form[method="get"] button[name="type"]')]
    assert tabs == [(hardware.LEGACY_KEY, "true"), (_SECOND_TYPE, "false")]
    assert label in text
