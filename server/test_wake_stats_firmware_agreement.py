"""The firmware's X-Wake-Stats formatter and the server parser agree.

Compiles the real firmware formatter (firmware/main/wake_telemetry.c) with
the host C compiler and runs its output through parse_wake_stats, so a
grammar or size-cap drift between the two languages fails here.
"""
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.wake_stats import WAKE_STATS_MAX_BYTES, parse_wake_stats  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIRMWARE_MAIN = os.path.join(ROOT, "firmware", "main")

DRIVER = r"""
#include <stdio.h>
#include "wake_telemetry.h"
int main(void) {
    char out[FP_WAKE_STATS_MAX_LEN + 1];
    fp_wake_record_t r;
    fp_wake_current_t typ = {42, 310, 1180, 1};
    fp_wake_record_encode(&r, 41, 1530, 60, 0, 0, 0, 97, 0, "ok");
    fp_wake_telemetry_format(out, sizeof out, &typ, &r, 1);
    puts(out);
    fp_wake_telemetry_format(out, sizeof out, &typ, NULL, 1);
    puts(out);
    fp_wake_current_t worst = {4294967295u, 4294967295u, 4294967295u, 99};
    fp_wake_record_encode(&r, 4294967295u, 4294967295u, 4294967295u,
                          4294967295u, 4294967295u, 4294967295u, 4294967295u,
                          2, "abcdefghijklmnop");
    fp_wake_telemetry_format(out, sizeof out, &worst, &r, 0);
    puts(out);
    fp_wake_record_encode(&r, 41, 1, 2, 3, 4, 5, 6, 1, "Bad Token!");
    fp_wake_telemetry_format(out, sizeof out, &typ, &r, 1);
    puts(out);
    return 0;
}
"""


@pytest.fixture(scope="module")
def c_headers(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc")
    assert cc, "a host C compiler is required for the firmware cross-check"
    work = tmp_path_factory.mktemp("wake_telemetry")
    src = work / "driver.c"
    src.write_text(DRIVER)
    exe = work / "driver"
    subprocess.run(
        [cc, "-Wall", "-Wextra", "-std=c11", "-I", FIRMWARE_MAIN, str(src),
         os.path.join(FIRMWARE_MAIN, "wake_telemetry.c"), "-o", str(exe)],
        check=True,
    )
    out = subprocess.run([str(exe)], check=True, capture_output=True,
                         text=True).stdout
    return out.splitlines()


def test_cap_matches_the_firmware_constant():
    with open(os.path.join(FIRMWARE_MAIN, "wake_telemetry.h")) as handle:
        match = re.search(r"#define\s+FP_WAKE_STATS_MAX_LEN\s+(\d+)",
                          handle.read())
    assert match is not None
    assert int(match.group(1)) == WAKE_STATS_MAX_BYTES


def test_typical_header_is_accepted_with_previous_wake_values(c_headers):
    parsed = parse_wake_stats(c_headers[0])
    assert parsed is not None
    assert parsed["wake_seq"] == 42 and parsed["prev_seq"] == 41
    assert parsed["prev_awake_ms"] == 1530 and parsed["prev_tls_ms"] == 97
    assert parsed["prev_outcome"] == "ok"


def test_header_without_previous_wake_is_accepted_and_has_no_p_columns(c_headers):
    parsed = parse_wake_stats(c_headers[1])
    assert parsed is not None
    assert set(parsed) == {"wake_seq", "boot_ms", "wifi_ms", "wifi_attempts"}


def test_clamped_worst_case_is_173_bytes_and_accepted(c_headers):
    worst = c_headers[2]
    assert len(worst) == 173 <= WAKE_STATS_MAX_BYTES
    parsed = parse_wake_stats(worst)
    assert parsed is not None
    assert parsed["boot_ms"] == 3_600_000 and parsed["wifi_attempts"] == 16
    assert parsed["prev_outcome"] == "abcdefghijklmnop"


def test_bad_outcome_token_is_sent_as_unknown_and_accepted(c_headers):
    parsed = parse_wake_stats(c_headers[3])
    assert parsed is not None and parsed["prev_outcome"] == "unknown"
