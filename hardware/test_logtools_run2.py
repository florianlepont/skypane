"""Behaviour tests for `logtools.py run-report`.

Every export here is synthetic and built in tmp_path; nothing is read from
or written to hardware/logs. The tests drive the CLI as a subprocess and
assert on its exit code, stderr and the JSON report it writes.
"""
import datetime
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
LOGTOOLS = os.path.join(HERE, "logtools.py")
EXAMPLE_PARAMS = os.path.join(HERE, "run2-params.example.json")

START = datetime.datetime(2030, 1, 10, 0, 0, 0, tzinfo=datetime.timezone.utc)
CONFIRMED = "2030-01-09T12:00:00+00:00"
REQUIRED = ("capacity_mah", "interval_s", "protocol_confirmed_utc",
            "disconnect_time_utc", "end_reason", "firmware_version",
            "server_revision")


def make_params(**over):
    params = {
        "capacity_mah": 3000,
        "interval_s": 900,
        "protocol_confirmed_utc": CONFIRMED,
        "disconnect_time_utc": "2030-01-09T23:59:00+00:00",
        "end_reason": "depleted",
        "ceiling_days": 45,
        "firmware_version": "9.9.9-test",
        "server_revision": "synthetic-rev",
        "park_mv": 3300,
        "boot_count_start": 10,
        "boot_count_end": None,
        "production_interval_before_s": 300,
        "production_interval_restored_s": 300,
    }
    params.update(over)
    return params


def make_rows(offsets_and_mv, fw="9.9.9-test", boot_reason="rtc"):
    rows = []
    for offset_s, mv in offsets_and_mv:
        ts = START + datetime.timedelta(seconds=offset_s)
        rows.append({"ts": ts.isoformat(), "battery_mv": mv,
                     "fw_version": fw, "boot_reason": boot_reason,
                     "rssi": "-60"})
    return rows


def regular(count, step_s=900, start_mv=4100, mv_step=1, begin_s=0):
    return [(begin_s + i * step_s, start_mv - i * mv_step) for i in range(count)]


def run(tmp_path, rows, params, extra=()):
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    params_path = tmp_path / "params.json"
    params_path.write_text(json.dumps(params))
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, LOGTOOLS, "run-report", str(rows_path),
         "--params", str(params_path), "--out", str(out)] + list(extra),
        capture_output=True, text=True)
    report = json.loads(out.read_text()) if out.exists() else None
    return proc, report, out


def test_clean_depleted_run_passes_all_three_verdicts(tmp_path):
    rows = make_rows(regular(851))
    params = make_params(boot_count_end=10 + 851)
    proc, report, _ = run(tmp_path, rows, params)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    for name in ("continuity", "voltage_validity", "baseline"):
        assert report["verdicts"][name]["status"] == "PASS"
    rec = report["reconciliation"]
    assert rec["observed_full"] == 851
    assert rec["boot_delta"] == 851
    assert rec["nominal"] > 0
    assert report["cadence"]["configured_interval_s"] == 900
    assert report["cadence"]["effective_mean_gap_s"] == pytest.approx(900, abs=1)


def test_gap_fails_continuity_but_not_voltage(tmp_path):
    offsets = [(i * 900 + (4500 if i >= 200 else 0), 4100 - 2 * i) for i in range(400)]
    proc, report, _ = run(tmp_path, make_rows(offsets), make_params())
    assert proc.returncode == 1
    assert report["verdicts"]["continuity"]["status"] == "FAIL"
    assert report["verdicts"]["voltage_validity"]["status"] == "PASS"


def test_flat_voltage_fails_voltage_but_not_continuity(tmp_path):
    offsets = [(i * 900, 4100) for i in range(400)]
    params = make_params(end_reason="ceiling", ceiling_days=45)
    proc, report, _ = run(tmp_path, make_rows(offsets), params)
    assert proc.returncode == 1
    assert report["verdicts"]["continuity"]["status"] == "PASS"
    assert report["verdicts"]["voltage_validity"]["status"] == "FAIL"


def test_park_window_splits_normal_cadence_from_parked(tmp_path):
    normal = regular(801)
    last_s = normal[-1][0]
    parked = [(last_s + (k + 1) * 3600, 3299 - k) for k in range(20)]
    rows = make_rows(normal + parked)
    proc, report, _ = run(tmp_path, rows, make_params())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert report["verdicts"]["continuity"]["status"] == "PASS"
    rec = report["reconciliation"]
    assert rec["observed_normal"] == 801
    assert rec["observed_full"] == 821
    assert rec["parked_polls"] == 20
    assert report["window"]["normal_window_end_ts"] == rows[800]["ts"]
    assert report["cadence"]["effective_mean_gap_s"] == pytest.approx(900, abs=1)

    # Judged on the full window the same rows would break the gap gate.
    no_park = make_params(park_mv=0)
    proc2, report2, _ = run(tmp_path, rows, no_park)
    assert proc2.returncode == 1
    assert report2["verdicts"]["continuity"]["status"] == "FAIL"


def test_boot_witness_is_computable_only_when_both_counts_exist(tmp_path):
    rows = make_rows(regular(851))
    _, with_boot, _ = run(tmp_path, rows, make_params(boot_count_end=10 + 851))
    assert with_boot["reconciliation"]["boot_delta_status"] == "computable"
    assert with_boot["reconciliation"]["boot_delta"] == 851

    proc, without, _ = run(tmp_path, rows, make_params(boot_count_start=None))
    assert proc.returncode == 0
    rec = without["reconciliation"]
    assert rec["boot_delta"] is None
    assert rec["boot_delta_status"].startswith("not computable")
    assert "boot_count_start" in rec["boot_delta_status"]


def test_boot_counter_far_above_polls_fails_continuity(tmp_path):
    rows = make_rows(regular(851))
    params = make_params(boot_count_end=10 + 5000)
    proc, report, _ = run(tmp_path, rows, params)
    assert proc.returncode == 1
    assert report["verdicts"]["continuity"]["status"] == "FAIL"


def test_ceiling_end_is_a_bound_not_a_failure(tmp_path):
    rows = make_rows(regular(400, mv_step=1))
    params = make_params(end_reason="ceiling", ceiling_days=45)
    proc, report, _ = run(tmp_path, rows, params)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    voltage = report["verdicts"]["voltage_validity"]
    assert voltage["status"] == "PASS"
    statuses = {c["name"]: c for c in voltage["checks"]}
    skipped = [c for c in statuses.values() if c["status"] == "SKIP"]
    assert skipped and "bound" in skipped[0]["reason"]


def test_span_beyond_ceiling_fails(tmp_path):
    rows = make_rows(regular(400, mv_step=1))
    params = make_params(end_reason="ceiling", ceiling_days=2)
    proc, report, _ = run(tmp_path, rows, params)
    assert proc.returncode == 1
    names = [c["name"] for c in report["verdicts"]["continuity"]["checks"]
             if c["status"] == "FAIL"]
    assert any("ceiling" in n for n in names)


def test_baseline_mismatch_and_mixed_firmware_fail(tmp_path):
    rows = make_rows(regular(851), fw="0.0.1-other")
    proc, report, _ = run(tmp_path, rows, make_params())
    assert proc.returncode == 1
    assert report["verdicts"]["baseline"]["status"] == "FAIL"
    assert report["verdicts"]["continuity"]["status"] == "PASS"

    mixed = make_rows(regular(851))
    for row in mixed[400:]:
        row["fw_version"] = "9.9.10-test"
    proc, report, _ = run(tmp_path, mixed, make_params())
    assert proc.returncode == 1
    assert report["verdicts"]["baseline"]["status"] == "FAIL"


def test_boot_reasons_are_reported_verbatim_and_do_not_gate(tmp_path):
    rows = make_rows(regular(851))
    rows[0]["boot_reason"] = "power-on"
    proc, report, _ = run(tmp_path, rows, make_params())
    assert proc.returncode == 0
    counts = report["baseline"]["boot_reason_counts"]
    assert counts == {"power-on": 1, "rtc": 850}
    assert report["baseline"]["fw_versions_seen"] == ["9.9.9-test"]
    assert report["baseline"]["server_revision"] == "synthetic-rev"


@pytest.mark.parametrize("key", REQUIRED)
def test_missing_or_null_required_param_is_refused(tmp_path, key):
    rows = make_rows(regular(851))
    for variant in ("null", "absent"):
        params = make_params()
        if variant == "null":
            params[key] = None
        else:
            del params[key]
        proc, report, out = run(tmp_path, rows, params)
        assert proc.returncode == 2
        assert key in proc.stderr
        assert not out.exists()


@pytest.mark.parametrize("override", [
    {"interval_s": 0}, {"capacity_mah": -3}, {"end_reason": "other"},
    {"capacity_mah": "3000"}, {"protocol_confirmed_utc": "2030-01-09T12:00:00"},
    {"end_reason": "ceiling", "ceiling_days": None},
])
def test_wrong_typed_params_are_refused(tmp_path, override):
    proc, _, out = run(tmp_path, make_rows(regular(100)), make_params(**override))
    assert proc.returncode == 2
    assert not out.exists()


def test_unreadable_params_json_is_refused(tmp_path):
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text(json.dumps(make_rows(regular(5))[0]) + "\n")
    params_path = tmp_path / "params.json"
    params_path.write_text("{not json")
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, LOGTOOLS, "run-report", str(rows_path),
         "--params", str(params_path), "--out", str(out)],
        capture_output=True, text=True)
    assert proc.returncode == 2
    assert not out.exists()


def test_empty_or_all_dropped_rows_are_refused(tmp_path):
    proc, _, out = run(tmp_path, [], make_params())
    assert proc.returncode == 2
    assert not out.exists()
    junk = [{"ts": "", "battery_mv": 3900}, {"ts": "2030-01-10T00:00:00Z",
                                              "battery_mv": None}]
    proc, _, out = run(tmp_path, junk, make_params())
    assert proc.returncode == 2
    assert not out.exists()


def test_export_predating_the_confirmation_is_refused(tmp_path):
    rows = make_rows(regular(100))
    params = make_params(protocol_confirmed_utc="2030-01-10T06:00:00+00:00")
    proc, _, out = run(tmp_path, rows, params)
    assert proc.returncode == 2
    assert "predates" in proc.stderr
    assert not out.exists()


def test_rows_after_end_time_or_out_of_order_are_refused(tmp_path):
    rows = make_rows(regular(100))
    params = make_params(end_time_utc="2030-01-10T01:00:00+00:00")
    proc, _, out = run(tmp_path, rows, params)
    assert proc.returncode == 2
    assert not out.exists()

    shuffled = make_rows(regular(100))
    shuffled[10], shuffled[11] = shuffled[11], shuffled[10]
    proc, _, out = run(tmp_path, shuffled, make_params())
    assert proc.returncode == 2
    assert "chronolog" in proc.stderr
    assert not out.exists()


def test_naive_row_timestamps_are_refused(tmp_path):
    rows = make_rows(regular(100))
    for row in rows:
        row["ts"] = row["ts"][:19]
    proc, _, out = run(tmp_path, rows, make_params())
    assert proc.returncode == 2
    assert not out.exists()


def test_summary_prints_three_separate_verdicts_and_the_export_hash(tmp_path):
    rows = make_rows(regular(851))
    proc, report, out = run(tmp_path, rows, make_params())
    assert proc.returncode == 0
    lines = proc.stdout.splitlines()
    for name in ("continuity", "voltage_validity", "baseline"):
        assert any(line.startswith(name) and "PASS" in line for line in lines)
    digest = report["export"]["sha256"]
    assert len(digest) == 64
    assert digest in proc.stdout
    text = out.read_text()
    assert text.endswith("\n")
    assert list(json.loads(text)) == sorted(json.loads(text))
    assert report["export"]["row_count"] == 851
    assert report["export"]["dropped_rows"] == 0
    assert report["restore"]["recorded"] is True


def test_dropped_rows_are_counted(tmp_path):
    rows = make_rows(regular(851))
    rows.insert(5, {"ts": "2030-01-10T00:00:00Z", "battery_mv": None})
    proc, report, _ = run(tmp_path, rows, make_params())
    assert proc.returncode == 0
    assert report["export"]["dropped_rows"] == 1
    assert report["export"]["row_count"] == 851


def test_shipped_example_params_file_is_refused(tmp_path):
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text("".join(json.dumps(r) + "\n" for r in make_rows(regular(100))))
    out = tmp_path / "report.json"
    proc = subprocess.run(
        [sys.executable, LOGTOOLS, "run-report", str(rows_path),
         "--params", EXAMPLE_PARAMS, "--out", str(out)],
        capture_output=True, text=True)
    assert proc.returncode == 2
    assert not out.exists()


def test_thresholds_cannot_be_retuned_from_the_command_line(tmp_path):
    proc, _, _ = run(tmp_path, make_rows(regular(100)), make_params(),
                     extra=("--min-coverage", "0.1"))
    assert proc.returncode == 2
