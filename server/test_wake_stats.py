"""Behaviour of the strict X-Wake-Stats parser."""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.wake_stats import (  # noqa: E402
    WAKE_COLUMNS,
    WAKE_STATS_MAX_BYTES,
    parse_wake_stats,
)

FULL = ("v=1;seq=812;bt=420;wf=1900;att=1;p_seq=811;p_aw=1480;p_rq=310;"
        "p_dl=0;p_dr=0;p_sp=0;p_tls=650;p_rd=0;p_out=ok")


def test_full_value_returns_thirteen_columns():
    result = parse_wake_stats(FULL)
    assert result == {
        "wake_seq": 812, "boot_ms": 420, "wifi_ms": 1900, "wifi_attempts": 1,
        "prev_seq": 811, "prev_awake_ms": 1480, "prev_request_ms": 310,
        "prev_download_ms": 0, "prev_draw_ms": 0, "prev_spi_ms": 0,
        "prev_tls_ms": 650, "prev_redraw": 0, "prev_outcome": "ok",
    }
    assert set(result) == set(WAKE_COLUMNS)
    assert "v" not in result


def test_version_and_seq_only_returns_that_one_column():
    assert parse_wake_stats("v=1;seq=7") == {"wake_seq": 7}


def test_ota_wake_without_previous_block_is_accepted():
    assert parse_wake_stats("v=1;seq=900;bt=400;wf=1500;att=1") == {
        "wake_seq": 900, "boot_ms": 400, "wifi_ms": 1500, "wifi_attempts": 1}


@pytest.mark.parametrize("value", [
    "v=1;seq=1;zz=3",
    "v=1;seq=1;seq=2",
    "seq=1",
    "v=2;seq=1",
    "v=;seq=1",
    "v=1;seq=١٢",
    "v=1;seq=+5",
    "v=1;seq=-5",
    "v=1;seq=5x",
    "v=1;seq=",
    "x v=1;seq=5",
    "v=1;seq=5;",
    "v=1;seq=5 ",
    "v=1;;seq=5",
    "v=1;seq=4294967296",
    "v=1;seq=00000000001",
    "v=1;bt=3600001",
    "v=1;att=17",
    "v=1;p_rd=3",
    "v=1;p_out=OK",
    "v=1;p_out=" + "a" * 17,
    "v=1;p_out=",
    "v=1;p_out=a b",
    "",
    "v=1;seq=1" + ";p_out=ok" * 2,
    None,
    42,
    b"v=1;seq=1",
    "v=1;seq=1" + " " * WAKE_STATS_MAX_BYTES,
])
def test_violation_drops_the_whole_header(value):
    assert parse_wake_stats(value) is None


@pytest.mark.parametrize("key, column, good, bad", [
    ("bt", "boot_ms", 3600000, 3600001),
    ("p_aw", "prev_awake_ms", 0, 3600001),
    ("att", "wifi_attempts", 16, 17),
])
def test_bounds(key, column, good, bad):
    assert parse_wake_stats(f"v=1;{key}={good}") == {column: good}
    assert parse_wake_stats(f"v=1;{key}={bad}") is None


def test_worst_case_value_is_accepted_and_one_over_is_refused():
    ms = "3600000"
    worst = ("v=1;seq=4294967295;bt={m};wf={m};att=16;p_seq=4294967295;"
             "p_aw={m};p_rq={m};p_dl={m};p_dr={m};p_sp={m};p_tls={m};"
             "p_rd=2;p_out={o}").format(m=ms, o="a" * 16)
    assert len(worst) == 173
    assert parse_wake_stats(worst) is not None
    padded = "v=1;seq=1;p_out=" + "a" * (WAKE_STATS_MAX_BYTES + 1 - len("v=1;seq=1;p_out="))
    assert len(padded) == WAKE_STATS_MAX_BYTES + 1
    assert parse_wake_stats(padded) is None
