"""Behaviour tests for the optional frozen reference interval of
`logtools.py run-report` and for `logtools.py reference-interval`.

Every export is synthetic and built in tmp_path; nothing is read from or
written to hardware/logs. The CLI is driven as a subprocess.
"""
import datetime
import hashlib
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
LOGTOOLS = os.path.join(HERE, "logtools.py")
START = datetime.datetime(2030, 1, 10, 0, 0, 0, tzinfo=datetime.timezone.utc)
DAY = 86400


def make_params(**over):
    params = {
        "capacity_mah": 3000,
        "interval_s": 60,
        "protocol_confirmed_utc": "2030-01-09T12:00:00+00:00",
        "disconnect_time_utc": "2030-01-09T23:59:00+00:00",
        "end_reason": "depleted",
        "ceiling_days": 21,
        "firmware_version": "9.9.9-test",
        "server_revision": "synthetic-rev",
        "park_mv": 3300,
        "boot_count_start": None,
        "boot_count_end": None,
        "production_interval_before_s": 30,
        "production_interval_restored_s": 30,
    }
    params.update(over)
    return params


def steady(gap_s, days=5, start_mv=4100, end_mv=3390):
    """Offsets and millivolts for a run with a constant poll-to-poll gap."""
    count = int(days * DAY / gap_s) + 1
    return [(i * gap_s, start_mv - (start_mv - end_mv) * i // (count - 1))
            for i in range(count)]


def make_rows(offsets_and_mv):
    return [{"ts": (START + datetime.timedelta(seconds=o)).isoformat(),
             "battery_mv": mv, "fw_version": "9.9.9-test",
             "boot_reason": "rtc", "rssi": "-60"} for o, mv in offsets_and_mv]


def write_rows(tmp_path, rows, name="rows.jsonl"):
    path = tmp_path / name
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def run_report(tmp_path, offsets_and_mv, params):
    rows_path = write_rows(tmp_path, make_rows(offsets_and_mv))
    params_path = tmp_path / "params.json"
    params_path.write_text(json.dumps(params))
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, LOGTOOLS, "run-report", str(rows_path),
         "--params", str(params_path), "--out", str(out)],
        capture_output=True, text=True)
    report = json.loads(out.read_text()) if out.exists() else None
    return proc, report, out


def reference_params(value, **over):
    return make_params(reference_interval_s=value,
                       reference_interval_source="synthetic test freeze", **over)


def by_prefix(report, prefix):
    found = [c for c in report["verdicts"]["continuity"]["checks"]
             if c["name"].startswith(prefix)]
    assert len(found) == 1, prefix
    return found[0]


def helper(tmp_path, offsets_and_mv, interval_s=60):
    rows_path = write_rows(tmp_path, make_rows(offsets_and_mv), "export.jsonl")
    return subprocess.run(
        [sys.executable, LOGTOOLS, "reference-interval", str(rows_path),
         "--interval-s", str(interval_s)], capture_output=True, text=True)


def helper_value(proc):
    assert proc.returncode == 0, proc.stdout + proc.stderr
    line = next(ln for ln in proc.stdout.splitlines()
                if ln.startswith("reference_interval_s:"))
    return int(line.split(":")[1])


# --- run-report: field absent --------------------------------------------


def test_absent_reference_interval_leaves_the_report_unchanged(tmp_path):
    proc, report, _ = run_report(tmp_path, steady(88), make_params())
    assert proc.returncode == 1
    assert "reference_interval" not in report
    assert "reference interval" not in proc.stdout
    coverage = by_prefix(report, "coverage is at least")
    assert coverage["name"] == "coverage is at least 0.95"
    assert coverage["status"] == "FAIL"
    assert not [c for c in report["verdicts"]["continuity"]["checks"]
                if "reference" in c["name"]]
    assert report["reconciliation"]["nominal"] == pytest.approx(5 * DAY / 60, rel=1e-3)


# --- run-report: field present -------------------------------------------


def test_reference_interval_drives_the_gates_and_60s_is_informational(tmp_path):
    proc, report, _ = run_report(tmp_path, steady(88), reference_params(88))
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert report["verdicts"]["continuity"]["status"] == "PASS"
    coverage = by_prefix(report, "coverage is at least")
    assert coverage["status"] == "PASS"
    assert "88 s reference interval" in coverage["name"]
    assert "88 s reference interval" in by_prefix(report, "no gap between")["name"]
    ref = report["reference_interval"]
    assert ref["reference_interval_s"] == 88
    assert ref["reference_interval_source"] == "synthetic test freeze"
    info = ref["informational_vs_configured"]
    assert info["configured_interval_s"] == 60
    assert info["coverage"] == pytest.approx(0.68, abs=0.01)
    assert info["max_gap_intervals"] == pytest.approx(88 / 60, abs=0.01)
    assert ref["judged_against"]["coverage"] == "reference_interval_s"
    assert ref["recomputed_from_first_48h"]["reference_interval_s"] == 88
    assert report["thresholds"]["min_coverage"] == 0.95
    assert report["thresholds"]["max_gap_intervals"] == 3
    assert "judged against 88 s" in proc.stdout
    assert "coverage=0.68" in proc.stdout
    # The informational 60 s figure alone would have failed the gate.
    _, plain, _ = run_report(tmp_path, steady(88), make_params())
    assert plain["verdicts"]["continuity"]["status"] == "FAIL"


def test_reference_interval_does_not_rescue_a_bad_run(tmp_path):
    hiccup = [(o + (700 if o >= 2 * DAY else 0), mv) for o, mv in steady(88)]
    proc, report, _ = run_report(tmp_path, hiccup, reference_params(88))
    assert proc.returncode == 1
    gap = by_prefix(report, "no gap between")
    assert gap["status"] == "FAIL"
    assert "interval(s)" in gap["reason"]
    assert report["verdicts"]["voltage_validity"]["status"] == "PASS"


def test_reference_interval_still_fails_low_coverage(tmp_path):
    # After the first 48 h every fifth row is missing, so the observed polls
    # fall well below 95 % of the reference count while every gap stays
    # under three intervals.
    offsets = [(o, mv) for i, (o, mv) in enumerate(steady(88))
               if o < 2 * DAY or i % 5 != 0]
    proc, report, _ = run_report(tmp_path, offsets, reference_params(88))
    assert proc.returncode == 1
    coverage = by_prefix(report, "coverage is at least")
    assert coverage["status"] == "FAIL"
    assert float(coverage["reason"].split()[2]) < 0.95
    assert by_prefix(report, "no gap between")["status"] == "PASS"


def test_frozen_value_must_match_the_first_48_hours(tmp_path):
    proc, report, _ = run_report(tmp_path, steady(88), reference_params(95))
    assert proc.returncode == 1
    check = by_prefix(report, "frozen reference interval")
    assert check["status"] == "FAIL"
    assert "95" in check["reason"] and "88" in check["reason"]


def test_value_taken_from_the_whole_run_is_caught(tmp_path):
    # 88 s for two days then 62 s: the first 48 h say 88, the whole run ~68.
    first = steady(88, days=2)
    tail = [(first[-1][0] + (i + 1) * 62, 3600 - i // 40) for i in range(6 * DAY // 62)]
    proc, report, _ = run_report(tmp_path, first + tail, reference_params(68))
    assert proc.returncode == 1
    assert by_prefix(report, "frozen reference interval")["status"] == "FAIL"
    _, good, _ = run_report(tmp_path, first + tail, reference_params(88))
    assert by_prefix(good, "frozen reference interval")["status"] == "PASS"
    drift = good["reference_interval"]["normal_window_mean_gap_vs_reference"]
    assert drift < -0.1


def test_export_shorter_than_48_hours_cannot_carry_a_frozen_value(tmp_path):
    proc, report, _ = run_report(tmp_path, steady(88, days=1.5), reference_params(88))
    assert proc.returncode == 1
    check = by_prefix(report, "frozen reference interval")
    assert check["status"] == "FAIL"
    assert "48 h" in check["reason"]


def test_export_hash_is_recorded_when_supplied(tmp_path):
    digest = hashlib.sha256(b"x").hexdigest()
    params = reference_params(88, reference_interval_export_sha256=digest)
    proc, report, _ = run_report(tmp_path, steady(88), params)
    assert proc.returncode == 0
    assert report["reference_interval"]["reference_interval_export_sha256"] == digest


# --- run-report: validation ----------------------------------------------


@pytest.mark.parametrize("override", [
    {"reference_interval_s": 0},
    {"reference_interval_s": -88},
    {"reference_interval_s": 59},
    {"reference_interval_s": 88.5},
    {"reference_interval_s": "88"},
    {"reference_interval_s": True},
    {"reference_interval_s": 181},
    {"reference_interval_s": 10 ** 9},
    {"reference_interval_s": 88, "reference_interval_source": None},
    {"reference_interval_s": 88, "reference_interval_source": "  "},
    {"reference_interval_s": 88, "reference_interval_export_sha256": "abc"},
    {"reference_interval_s": None, "reference_interval_source": "orphan note"},
])
def test_bad_reference_values_are_refused(tmp_path, override):
    params = make_params(reference_interval_source="synthetic test freeze")
    params.update(override)
    proc, _, out = run_report(tmp_path, steady(88), params)
    assert proc.returncode == 2, proc.stdout
    assert "reference_interval" in proc.stderr
    assert not out.exists()


def test_reference_bounds_are_inclusive(tmp_path):
    for value in (60, 180):
        proc, _, _ = run_report(tmp_path, steady(88), reference_params(value))
        assert proc.returncode in (0, 1), proc.stderr


# --- reference-interval helper -------------------------------------------


def test_helper_prints_value_and_gap_counts(tmp_path):
    proc = helper(tmp_path, steady(88, days=3))
    assert helper_value(proc) == 88
    assert "gaps used: 1963, excluded (above 180 s): 0" in proc.stdout
    raw = (tmp_path / "export.jsonl").read_bytes()
    assert hashlib.sha256(raw).hexdigest() in proc.stdout


def test_helper_reads_only_the_first_48_hours(tmp_path):
    early = steady(88, days=2)
    end = early[-1][0]
    fast = [(end + 62 * (i + 1), 3600 - i) for i in range(2000)]
    slow = [(end + 300 * (i + 1), 3600 - i) for i in range(2000)]
    values = {helper_value(helper(tmp_path, early + [(end + 88, 3600)])),
              helper_value(helper(tmp_path, early + fast)),
              helper_value(helper(tmp_path, early + slow))}
    assert values == {88}


def test_helper_excludes_gaps_above_three_intervals(tmp_path):
    offsets = [(i * 80, 4000 - i // 20) for i in range(2000)]
    # One 700 s hiccup inside the window is excluded, not averaged in.
    offsets = [(o + (620 if o >= 40000 else 0), mv) for o, mv in offsets]
    offsets.append((2 * DAY + 100, 3000))
    proc = helper(tmp_path, offsets)
    assert helper_value(proc) == 80
    assert "excluded (above 180 s): 1" in proc.stdout


def test_helper_rounds_to_whole_seconds_half_up(tmp_path):
    def value_for(gaps):
        offsets, t = [(0, 4000)], 0
        for g in gaps:
            t += g
            offsets.append((t, 4000 - len(offsets)))
        offsets.append((2 * DAY + 10, 3000))
        return helper_value(helper(tmp_path, offsets))
    assert value_for([88, 89] * 500) == 89  # mean 88.5
    assert value_for([88] * 600 + [89] * 400) == 88  # mean 88.4
    assert value_for([88] * 400 + [89] * 600) == 89  # mean 88.6


def test_helper_refuses_an_export_shorter_than_48_hours(tmp_path):
    proc = helper(tmp_path, steady(88, days=1.9))
    assert proc.returncode == 2
    assert "less than the 48 h" in proc.stderr
    assert "reference_interval_s" not in proc.stdout


def test_helper_refuses_when_too_few_gaps_remain(tmp_path):
    sparse = [(i * 800, 4000 - i) for i in range(200)]
    sparse.append((2 * DAY + 5, 3000))
    proc = helper(tmp_path, sparse)
    assert proc.returncode == 2
    assert "need at least 100" in proc.stderr


def test_helper_refuses_unordered_or_empty_exports(tmp_path):
    rows = make_rows(steady(88, days=3))
    rows[10], rows[11] = rows[11], rows[10]
    path = write_rows(tmp_path, rows, "unordered.jsonl")
    proc = subprocess.run(
        [sys.executable, LOGTOOLS, "reference-interval", str(path),
         "--interval-s", "60"], capture_output=True, text=True)
    assert proc.returncode == 2
    assert "chronolog" in proc.stderr
    empty = write_rows(tmp_path, [], "empty.jsonl")
    proc = subprocess.run(
        [sys.executable, LOGTOOLS, "reference-interval", str(empty),
         "--interval-s", "60"], capture_output=True, text=True)
    assert proc.returncode == 2


def test_helper_value_feeds_run_report_unchanged(tmp_path):
    offsets = steady(88)
    value = helper_value(helper(tmp_path, offsets))
    proc, report, _ = run_report(tmp_path, offsets, reference_params(value))
    assert proc.returncode == 0, proc.stdout
    assert by_prefix(report, "frozen reference interval")["status"] == "PASS"


def test_missing_boot_counts_are_not_computable_and_never_estimated(tmp_path):
    params = reference_params(88, boot_count_start=None, boot_count_end=None)
    proc, report, _ = run_report(tmp_path, steady(88), params)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    rec = report["reconciliation"]
    assert rec["boot_delta"] is None
    assert rec["boot_delta_status"] == (
        "not computable: boot_count_start and boot_count_end not recorded")
    assert rec["boot_vs_observed_full"] is None
    assert rec["nominal"] == pytest.approx(5 * DAY / 88, rel=1e-3)
    assert rec["observed_normal"] == report["export"]["row_count"]
    assert not [c for c in report["verdicts"]["continuity"]["checks"]
                if "boot-counter" in c["name"]]
    assert "boot-delta=not computable" in proc.stdout
