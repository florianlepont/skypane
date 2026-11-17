"""Tests for scripts/export_snapshot.py: manifest writer and fetch-error handling.

No network is opened: the fetch callable is injected.
"""
import hashlib
import json
import os
import sys

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import export_snapshot  # noqa: E402

JSONL = '{"ts": "a", "hex": "1"}\n{"ts": "b", "hex": "2"}\n{"ts": "c", "hex": "3"}\n'
STATUS = '{"wake_interval_s": 60, "tracked_runway": "3"}'


def _fetch_ok(url):
    if url.endswith("/status"):
        return STATUS
    return JSONL


def _manifest(out):
    with open(os.path.join(out, "MANIFEST.json"), encoding="utf-8") as handle:
        return json.load(handle)


def test_jsonl_file_is_stored_unchanged_with_rows_and_sha256(tmp_path):
    export_snapshot.run_snapshot("https://example.test", "2026-11-01T00:00:00Z",
                                 str(tmp_path), _fetch_ok)
    stored = (tmp_path / "runway_events.jsonl").read_text(encoding="utf-8")
    assert stored == JSONL
    entry = _manifest(str(tmp_path))["files"]["runway_events.jsonl"]
    assert entry["rows"] == 3
    assert entry["sha256"] == hashlib.sha256(JSONL.encode()).hexdigest()
    assert entry["route"] == "/api/export/flights"
    assert _manifest(str(tmp_path))["since"] == "2026-11-01T00:00:00Z"


def test_status_is_one_object_with_row_count_one(tmp_path):
    export_snapshot.run_snapshot("https://example.test", "2026-11-01T00:00:00Z",
                                 str(tmp_path), _fetch_ok)
    entry = _manifest(str(tmp_path))["files"]["status.json"]
    assert entry["rows"] == 1
    assert json.loads((tmp_path / "status.json").read_text()) == json.loads(STATUS)


def test_fetch_failure_is_recorded_and_keeps_other_files(tmp_path):
    def fetch(url):
        if "poll-cycles" in url:
            raise OSError("proxy said 403")
        return _fetch_ok(url)

    export_snapshot.run_snapshot("https://example.test", "2026-11-01T00:00:00Z",
                                 str(tmp_path), fetch)
    files = _manifest(str(tmp_path))["files"]
    assert "proxy said 403" in files["poll_cycles.jsonl"]["error"]
    assert "sha256" not in files["poll_cycles.jsonl"]
    assert not (tmp_path / "poll_cycles.jsonl").exists()
    assert (tmp_path / "runway_events.jsonl").read_text() == JSONL
    assert files["runway_events.jsonl"]["rows"] == 3


def test_existing_file_is_not_overwritten_without_flag(tmp_path):
    export_snapshot.run_snapshot("https://example.test", "2026-11-01T00:00:00Z",
                                 str(tmp_path), _fetch_ok)
    with pytest.raises(FileExistsError):
        export_snapshot.run_snapshot("https://example.test",
                                     "2026-11-01T00:00:00Z", str(tmp_path),
                                     lambda url: "x\n")
    assert (tmp_path / "runway_events.jsonl").read_text() == JSONL


def test_overwrite_flag_replaces_existing_files(tmp_path):
    export_snapshot.run_snapshot("https://example.test", "2026-11-01T00:00:00Z",
                                 str(tmp_path), _fetch_ok)
    export_snapshot.run_snapshot("https://example.test", "2026-11-01T00:00:00Z",
                                 str(tmp_path), lambda url: '{"a": 1}\n',
                                 overwrite=True)
    assert (tmp_path / "runway_events.jsonl").read_text() == '{"a": 1}\n'


def test_since_is_url_encoded_in_requests(tmp_path):
    seen = []

    def fetch(url):
        seen.append(url)
        return _fetch_ok(url)

    export_snapshot.run_snapshot("https://example.test/", "2026-11-01T00:00:00Z",
                                 str(tmp_path), fetch)
    assert "https://example.test/api/export/flights?since=2026-11-01T00%3A00%3A00Z" in seen
    assert "https://example.test/api/export/status" in seen
