#!/usr/bin/env python3
"""Contract tests for server/history_db.py's Caddy access-log battery
tailer: complete-lines-only reading (a partial last line is never parsed
and is re-read once complete), byte-exact offsets across multi-byte UTF-8
content, a guarded stored offset, and a guarded epoch `ts`.
"""
import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)

if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import server.history_db as history_db  # noqa: E402


def _caddy_log_line(uri, ts, headers):
    """One Caddy JSON access-log line, in the assumed shape: the request's
    header map nests under `request.headers`, each value a list of
    strings. Matches server/test_config_history.py's own helper.
    """
    entry = {
        "ts": ts,
        "logger": "http.log.access",
        "msg": "handled request",
        "request": {"method": "GET", "uri": uri, "headers": headers},
        "status": 200,
    }
    return json.dumps(entry)


def test_partial_last_line_is_not_returned_and_is_reread_once_complete(tmp_path):
    """a last line with no trailing newline is not parsed; new_offset stops right after the last '\\n'; completing the line later returns it exactly once"""
    log_path = os.path.join(tmp_path, "caddy-access.log")
    complete_line = _caddy_log_line(
        "/device/v1/display", "2026-09-02T10:00:00Z", {"X-Battery-Mv": ["3700"]}
    )
    partial_line = _caddy_log_line(
        "/device/v1/display", "2026-09-02T10:01:00Z", {"X-Battery-Mv": ["3690"]}
    )
    with open(log_path, "wb") as fh:
        fh.write((complete_line + "\n").encode("utf-8"))
        fh.write(partial_line.encode("utf-8"))  # no trailing newline: mid-write

    readings, offset = history_db.tail_caddy_battery_log(log_path, 0)
    assert len(readings) == 1 and readings[0]["battery_mv"] == 3700, (
        "expected only the complete first line, got %r" % (readings,)
    )
    with open(log_path, "rb") as fh:
        consumed = fh.read(offset)
    assert consumed.endswith(b"\n"), "new_offset must land right after the last complete newline, not mid-partial-line"

    # Complete the partial line (Caddy finishing its write) and re-tail
    # from the offset the first tail returned.
    with open(log_path, "ab") as fh:
        fh.write(b"\n")
    readings2, offset2 = history_db.tail_caddy_battery_log(log_path, offset)
    assert len(readings2) == 1 and readings2[0]["battery_mv"] == 3690, (
        "expected the now-completed second line exactly once, got %r" % (readings2,)
    )

    # And it is never returned a second time.
    readings3, _offset3 = history_db.tail_caddy_battery_log(log_path, offset2)
    assert readings3 == [], "the completed line must not be returned a second time"


def test_multibyte_utf8_header_value_reads_without_error_and_offsets_are_byte_offsets(tmp_path):
    """a multi-byte UTF-8 header value is read without error, and offsets are exact byte offsets - the next tail starts at the right line"""
    log_path = os.path.join(tmp_path, "caddy-access.log")
    ascii_line = _caddy_log_line(
        "/device/v1/display", "2026-09-02T10:00:00Z", {"X-Battery-Mv": ["3700"]}
    )
    # Multi-byte UTF-8 content (several bytes per code point) in a header
    # value - a byte-offset bug that assumed one byte per character would
    # land mid-character on the next seek().
    multibyte_line = _caddy_log_line(
        "/device/v1/display", "2026-09-02T10:01:00Z",
        {"X-Battery-Mv": ["3690"], "X-Boot-Reason": ["batterie faible ⚡️"]},
    )
    with open(log_path, "wb") as fh:
        fh.write((ascii_line + "\n").encode("utf-8"))
        fh.write((multibyte_line + "\n").encode("utf-8"))

    readings, offset = history_db.tail_caddy_battery_log(log_path, 0)
    assert [r["battery_mv"] for r in readings] == [3700, 3690]
    assert readings[1]["boot_reason"] == "batterie faible ⚡️"

    with open(log_path, "rb") as fh:
        total_bytes = len(fh.read())
    assert offset == total_bytes, "offset must be the exact byte length consumed, not a character count"

    # A tail from that exact offset finds nothing new.
    readings2, offset2 = history_db.tail_caddy_battery_log(log_path, offset)
    assert readings2 == [] and offset2 == offset


@pytest.mark.parametrize("stored", ["abc", "-5", ""])
def test_bad_stored_offset_resets_to_zero_without_raising(tmp_path, stored):
    """a stored offset of 'abc', '-5' or '' is treated as 0 by ingest_caddy_battery_log, never raising"""
    log_path = os.path.join(tmp_path, "caddy-access.log")
    line = _caddy_log_line("/device/v1/display", "2026-09-02T10:00:00Z", {"X-Battery-Mv": ["3700"]})
    with open(log_path, "w") as fh:
        fh.write(line + "\n")

    with history_db.open_db(tmp_path) as conn:
        history_db.set_meta(conn, history_db.META_CADDY_LOG_OFFSET, stored)
        inserted = history_db.ingest_caddy_battery_log(conn, log_path)

    assert inserted == 1, (
        "a bad stored offset (%r) must reset to 0 and still ingest the whole file, got %d rows" % (stored, inserted)
    )


def test_out_of_range_and_nan_ts_are_skipped_valid_ts_is_ingested_no_raise(tmp_path):
    """ts=1e20 and ts=NaN (a token json.loads accepts) are skipped; a line with a valid float ts is ingested; nothing raises"""
    log_path = os.path.join(tmp_path, "caddy-access.log")
    lines = [
        json.dumps({
            "ts": 1e20,
            "request": {"method": "GET", "uri": "/device/v1/display", "headers": {"X-Battery-Mv": ["1111"]}},
        }),
        json.dumps({
            "ts": float("nan"),
            "request": {"method": "GET", "uri": "/device/v1/display", "headers": {"X-Battery-Mv": ["2222"]}},
        }),
        json.dumps({
            "ts": 1798000000.0,
            "request": {"method": "GET", "uri": "/device/v1/display", "headers": {"X-Battery-Mv": ["3333"]}},
        }),
    ]
    with open(log_path, "w") as fh:
        fh.write("\n".join(lines) + "\n")

    readings, _offset = history_db.tail_caddy_battery_log(log_path, 0)
    assert [r["battery_mv"] for r in readings] == [3333], (
        "expected only the valid-ts line to be ingested, got %r" % (readings,)
    )


def test_invalid_utf8_bytes_in_a_line_never_raise(tmp_path):
    """invalid-UTF-8 bytes inside a complete line never raise - skipped or decoded with replacement, and the valid neighbouring line still surfaces"""
    log_path = os.path.join(tmp_path, "caddy-access.log")
    valid_line = _caddy_log_line(
        "/device/v1/display", "2026-09-02T10:00:00Z", {"X-Battery-Mv": ["3700"]}
    ).encode("utf-8")
    # A lone continuation byte + an unpaired start byte: not valid UTF-8
    # by itself, embedded inside an otherwise well-formed JSON line.
    bad_line = (
        b'{"ts": "2026-09-02T10:01:00Z", "request": {"method": "GET", '
        b'"uri": "/device/v1/display", "headers": {"X-Battery-Mv": ["\xff\xfe"]}}}'
    )
    with open(log_path, "wb") as fh:
        fh.write(valid_line + b"\n")
        fh.write(bad_line + b"\n")
    with open(log_path, "rb") as fh:
        total_bytes = len(fh.read())

    readings, offset = history_db.tail_caddy_battery_log(log_path, 0)
    battery_values = [r["battery_mv"] for r in readings]
    assert 3700 in battery_values, "expected the valid line's reading to survive, got %r" % (readings,)
    assert offset == total_bytes, (
        "a complete line (even one with invalid UTF-8 bytes replaced) must be consumed once, not re-read forever"
    )


def test_shrunk_file_still_resets_offset_to_zero(tmp_path):
    """a file that shrank below the stored offset (a Caddy rotation) still resets to 0 and re-ingests from the start"""
    log_path = os.path.join(tmp_path, "caddy-access.log")
    long_line = _caddy_log_line(
        "/device/v1/display", "2026-09-02T10:00:00Z",
        {"X-Battery-Mv": ["3700"], "X-Fw-Version": ["1.2.3-a-long-build-identifier"]},
    )
    with open(log_path, "w") as fh:
        fh.write(long_line + "\n")

    with history_db.open_db(tmp_path) as conn:
        first = history_db.ingest_caddy_battery_log(conn, log_path)
        assert first == 1

        # Caddy rotated: the file is replaced by something shorter than
        # the stored offset.
        short_line = _caddy_log_line(
            "/device/v1/display", "2026-09-02T11:00:00Z", {"X-Battery-Mv": ["3600"]}
        )
        with open(log_path, "w") as fh:
            fh.write(short_line + "\n")

        second = history_db.ingest_caddy_battery_log(conn, log_path)
        assert second == 1, (
            "a rotated (shrunk) file must reset the offset to 0 and re-ingest from the start, got %d rows" % second
        )
