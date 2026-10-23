"""Behaviour tests for the `checkin-gaps` subcommand in `logtools.py`.

Every export is synthetic and built in tmp_path: check-ins at known spacings,
judged against the continuity gates the run report already uses.
"""
import datetime
import importlib.util
import json
import os
import re
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
LOGTOOLS = os.path.join(HERE, "logtools.py")

_spec = importlib.util.spec_from_file_location("logtools_gaps_under_test", LOGTOOLS)
lt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lt)

UTC = datetime.timezone.utc
# 2026-01-05 is a winter Monday: Paris is UTC+1, so 22:10 UTC is 23:10 local.
START = datetime.datetime(2026, 1, 5, 6, 0, tzinfo=UTC)


def write_export(tmp_path, times, name="export.jsonl"):
    path = tmp_path / name
    with open(path, "w") as fh:
        for ts in times:
            fh.write(json.dumps({"ts": ts.isoformat(), "battery_mv": 3900,
                                 "fw_version": "fw-test", "boot_reason": "rtc",
                                 "rssi": "-60"}) + "\n")
    return str(path)


def spaced(start, gaps):
    """Timestamps beginning at `start` separated by the given gap seconds."""
    times = [start]
    for g in gaps:
        times.append(times[-1] + datetime.timedelta(seconds=g))
    return times


def run(path, *extra, expect=900):
    proc = subprocess.run(
        [sys.executable, LOGTOOLS, "checkin-gaps", path, "--expect-s", str(expect)] + list(extra),
        capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def test_perfect_cadence_passes(tmp_path):
    times = spaced(START, [914] * 190)
    code, out, _ = run(write_export(tmp_path, times), "--no-quiet-hours")
    assert code == 0
    assert "cadence verdict: PASS" in out
    assert re.search(r"median gap vs expected: 914 s, 1\.016 x expected", out)
    assert "PASS coverage is at least 0.95" in out


def test_three_hour_hole_fails_max_gap(tmp_path):
    gaps = [900] * 100 + [10800] + [900] * 100
    code, out, _ = run(write_export(tmp_path, spaced(START, gaps)), "--no-quiet-hours")
    assert code == 1
    assert "cadence verdict: FAIL" in out
    assert "FAIL no gap between consecutive polls exceeds 3 interval(s)" in out
    assert "gaps above 3 x expected: 1" in out


def test_window_selects_rows_and_refuses_thin_windows(tmp_path):
    times = spaced(START, [900] * 100)
    path = write_export(tmp_path, times)
    code, out, _ = run(path, "--no-quiet-hours",
                       "--from", times[10].isoformat(), "--to", times[20].isoformat())
    assert code == 0
    assert "gaps: 10 " in out
    code, _, err = run(path, "--no-quiet-hours",
                       "--from", times[10].isoformat(), "--to", times[10].isoformat())
    assert code == 2
    assert "refused" in err
    code, _, err = run(path, "--no-quiet-hours", "--from", "2030-01-01T00:00:00+00:00")
    assert code == 2


def test_quiet_gaps_are_set_aside_by_start_time(tmp_path):
    # gap starts: 23:10 judged, 23:40 and 05:50 set aside, 06:10 judged (Paris)
    day = datetime.datetime(2026, 1, 5, tzinfo=UTC)
    starts = [day + datetime.timedelta(hours=22, minutes=10),   # 23:10 Paris
              day + datetime.timedelta(hours=22, minutes=40),   # 23:40 Paris
              day + datetime.timedelta(hours=28, minutes=50),   # 05:50 Paris next day
              day + datetime.timedelta(hours=29, minutes=10),   # 06:10 Paris
              day + datetime.timedelta(hours=29, minutes=25)]
    path = write_export(tmp_path, starts)
    code, out, _ = run(path, expect=900)
    assert "quiet gaps set aside: 2" in out
    assert "gaps: 2 " in out
    code, out, _ = run(path, "--no-quiet-hours", expect=900)
    assert "quiet hours: off, no gap set aside" in out
    assert "gaps: 4 " in out


def test_quiet_flags_conflict_is_refused(tmp_path):
    path = write_export(tmp_path, spaced(START, [900] * 10))
    code, _, err = run(path, "--no-quiet-hours", "--quiet-start", "23:00")
    assert code == 2
    assert "refused" in err


def test_parked_style_window_passes_at_3600_and_fails_at_300(tmp_path):
    path = write_export(tmp_path, spaced(START, [3614] * 40))
    code, out, _ = run(path, "--no-quiet-hours", expect=3600)
    assert code == 0
    code, out, _ = run(path, "--no-quiet-hours", expect=300)
    assert code == 1
    assert "cadence verdict: FAIL" in out


def test_fast_frame_is_visible_in_the_ratio(tmp_path):
    path = write_export(tmp_path, spaced(START, [300] * 40))
    _, out, _ = run(path, "--no-quiet-hours", expect=600)
    assert "median gap vs expected: 300 s, 0.500 x expected" in out


def test_gates_read_run_thresholds_at_call_time(tmp_path, monkeypatch):
    times = spaced(START, [300] * 50 + [600] + [300] * 50)
    path = write_export(tmp_path, times)

    def verdict(**patch):
        for key, value in patch.items():
            monkeypatch.setitem(lt.RUN_THRESHOLDS, key, value)
        rc = lt.main(["checkin-gaps", path, "--expect-s", "300", "--no-quiet-hours"])
        return rc

    assert verdict() == 0
    assert verdict(max_gap_intervals=1) == 1
    monkeypatch.setitem(lt.RUN_THRESHOLDS, "max_gap_intervals", 3)
    assert verdict(min_coverage=0.999) == 1


def test_gate_names_carry_patched_numbers(tmp_path, monkeypatch, capsys):
    path = write_export(tmp_path, spaced(START, [300] * 20))
    monkeypatch.setitem(lt.RUN_THRESHOLDS, "max_gap_intervals", 7)
    monkeypatch.setitem(lt.RUN_THRESHOLDS, "min_coverage", 0.5)
    lt.main(["checkin-gaps", path, "--expect-s", "300", "--no-quiet-hours"])
    out = capsys.readouterr().out
    assert "exceeds 7 interval(s)" in out
    assert "coverage is at least 0.50" in out


def test_skip_first_gaps_sets_aside_the_old_interval_gap(tmp_path):
    gaps = [3600] + [300] * 40
    times = spaced(START, gaps)
    path = write_export(tmp_path, times)
    code, out, _ = run(path, "--no-quiet-hours", expect=300)
    assert code == 1
    code, out, _ = run(path, "--no-quiet-hours", "--skip-first-gaps", "1", expect=300)
    assert code == 0
    assert "first gap(s) set aside: 3600" in out
    code, _, err = run(path, "--no-quiet-hours", "--skip-first-gaps", "99", expect=300)
    assert code == 2


def test_from_after_the_old_gap_makes_skip_remove_a_good_gap(tmp_path):
    times = spaced(START, [3600] + [300] * 40)
    path = write_export(tmp_path, times)
    window = ("--from", times[1].isoformat())
    code, _, _ = run(path, "--no-quiet-hours", *window, expect=300)
    assert code == 0
    code, out, _ = run(path, "--no-quiet-hours", "--skip-first-gaps", "1", *window, expect=300)
    assert code == 0
    assert "first gap(s) set aside: 300" in out


def test_out_json_is_deterministic(tmp_path):
    path = write_export(tmp_path, spaced(START, [900] * 20))
    a, b = str(tmp_path / "a.json"), str(tmp_path / "b.json")
    run(path, "--no-quiet-hours", "--out", a)
    run(path, "--no-quiet-hours", "--out", b)
    assert open(a).read() == open(b).read()
    assert json.load(open(a))["verdict"] == "PASS"
