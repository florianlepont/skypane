"""Behaviour tests for the two-run battery model in `logtools.py`.

The pure functions are called on synthetic numbers with known answers. The
`battery-model` subcommand is driven as a subprocess on inputs built in
tmp_path; one test reads the committed logs under hardware/logs read-only.
"""
import datetime
import hashlib
import importlib.util
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
LOGTOOLS = os.path.join(HERE, "logtools.py")

_spec = importlib.util.spec_from_file_location("logtools_under_test", LOGTOOLS)
lt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lt)


class Poll(object):
    def __init__(self, mv):
        self.mv = mv


def synthetic_runs(energy, standing, gap1, gap2, charge1=1.0, charge2=1.0,
                   energy_run1=None):
    """Return (n1, t1, n2, t2) of two runs that drain exactly their charge."""
    e1 = energy if energy_run1 is None else energy_run1
    n1 = charge1 / (e1 + standing * gap1)
    n2 = charge2 / (energy + standing * gap2)
    return n1, n1 * gap1, n2, n2 * gap2


def close(a, b, rel=1e-9):
    return a == pytest.approx(b, rel=rel)


def test_fit_recovers_known_wake_and_standing():
    energy, standing = 0.0001, 2.5e-6
    n1, t1, n2, t2 = synthetic_runs(energy, standing, 328.0, 74.0)
    fit = lt.fit_two_runs(n1, t1, n2, t2, k=1.0, d=0.0)
    assert close(fit["wake"], energy)
    assert close(fit["standing"], standing)
    assert fit["standing_nonpositive"] is False


def test_charge_cancels_from_ratio_and_autonomy():
    energy, standing = 0.0001, 2.5e-6
    n1, t1, n2, t2 = synthetic_runs(energy, standing, 328.0, 74.0)
    res = lt.ratio_and_ceiling(n1, t1, n2, t2)
    assert close(res["ratio_s"], (t1 - t2) / (n2 - n1))
    assert close(res["ratio_s"], energy / standing)
    assert close(res["ceiling_s"], n1 * res["ratio_s"] + t1)
    assert close(res["ceiling_days"], res["ceiling_s"] / 86400.0)
    fit = lt.fit_two_runs(n1, t1, n2, t2)
    for period in (314, 614, 914, 1814):
        expected = res["ceiling_s"] * period / (res["ratio_s"] + period) / 86400.0
        assert close(lt.autonomy_days(fit["wake"], fit["standing"], period), expected)
    # The same drain measured with a pack of three times the charge, wake and
    # standing scaled with it, gives the same observed counts and autonomy.
    n1b, t1b, n2b, t2b = synthetic_runs(
        energy * 3, standing * 3, 328.0, 74.0, charge1=3.0, charge2=3.0)
    assert close(n1b, n1) and close(t2b, t2)
    scaled = lt.fit_two_runs(n1b, t1b, n2b, t2b)
    assert close(lt.autonomy_days(scaled["wake"], scaled["standing"], 614),
                 lt.autonomy_days(fit["wake"], fit["standing"], 614))


def test_wake_ratio_and_capacity_ratio_are_recovered():
    energy, standing = 0.0001, 2.5e-6
    n1, t1, n2, t2 = synthetic_runs(
        energy, standing, 328.0, 74.0, charge1=1.0, charge2=1.05,
        energy_run1=1.5 * energy)
    fit = lt.fit_two_runs(n1, t1, n2, t2, k=1.5, d=0.05)
    assert close(fit["wake"], energy)
    assert close(fit["standing"], standing)


def test_nonpositive_standing_is_flagged_never_raised():
    n1, t1, n2, t2 = synthetic_runs(0.0001, 2.5e-6, 328.0, 74.0)
    fit = lt.fit_two_runs(n1, t1, n2, t2, k=4.0, d=0.0)
    assert fit["standing_nonpositive"] is True
    assert lt.autonomy_days(fit["wake"], fit["standing"], 600) is None
    degenerate = lt.fit_two_runs(1.0, 1.0, 1.0, 1.0)
    assert degenerate["standing_nonpositive"] is True
    assert degenerate["wake"] is None and degenerate["standing"] is None
    assert lt.autonomy_days(None, None, 600) is None


def test_ratio_refuses_when_faster_run_does_not_have_more_cycles():
    with pytest.raises(lt.RunReportError):
        lt.ratio_and_ceiling(100.0, 5000.0, 100.0, 4000.0)
    with pytest.raises(lt.RunReportError):
        lt.ratio_and_ceiling(100.0, 4000.0, 200.0, 5000.0)


def test_cut_rules_on_a_single_sample_dip():
    mvs = [4000, 3900, 3368, 3292, 3368, 3366, 3340, 3310, 3300, 3296, 3290, 3280]
    polls = [Poll(m) for m in mvs]
    assert lt.first_at_or_below(polls, 3300) == 3
    assert lt.rolling_median_cut(polls, 3300, 5) == 10
    never = [Poll(m) for m in (4000, 3900, 3800, 3700, 3600, 3500)]
    assert lt.first_at_or_below(never, 3300) is None
    assert lt.rolling_median_cut(never, 3300, 5) is None


def envelope_inputs():
    run1_cuts = [("raw", 2992, 980482.0), ("median-5", 3116, 1019952.0),
                 ("median-49", 3139, 1027728.0)]
    run2_counts = [("observed", 6148, 455125.0), ("nominal", 6501.8, 455125.0)]
    overheads = [("run-two", 14.0), ("run-one", 28.0)]
    return run1_cuts, run2_counts, overheads, (300, 600, 900, 1800)


def test_envelope_has_108_scenarios_and_minimum_at_unit_wake_ratio():
    env = lt.build_envelope(*envelope_inputs())
    assert env["scenario_count"] == 108
    assert set(env["intervals"]) == {300, 600, 900, 1800}
    for interval, row in env["intervals"].items():
        assert row["minimum"]["days"] <= row["central"]["days"] <= row["maximum"]["days"]
        assert row["minimum"]["scenario"]["k"] == 1.0
        assert row["nonpositive_count"] == env["nonpositive_count"]
    assert env["nonpositive_count"] > 0
    ok = [s for s in env["scenarios"] if not s["standing_nonpositive"]]
    assert len(ok) + env["nonpositive_count"] == 108


def test_sweeps_cover_the_fixed_grids():
    sw = lt.sweep(2992, 980482.0, 6148, 455125.0, 14.0, (300, 600))
    assert [row["k"] for row in sw["k_sweep"]] == list(lt.MODEL_K_SWEEP)
    assert [row["d"] for row in sw["d_sweep"]] == list(lt.MODEL_D_SWEEP)
    assert all(row["d"] == 0.0 for row in sw["k_sweep"])
    assert all(row["k"] == 1.0 for row in sw["d_sweep"])
    assert set(sw["k_sweep"][0]["days"]) == {300, 600}


# --- battery-model subcommand ------------------------------------------------

START1 = datetime.datetime(2030, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
START2 = datetime.datetime(2030, 2, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
HEADINGS = (
    "Inputs (like-for-like, both runs to the first reading at or below 3300 mV)",
    "Autonomy to the BATTERY EMPTY park",
    "Assumptions",
    "Uncertainty",
    "What this model does not measure",
)
COMMITTED = os.path.join(HERE, "logs")


def run1_log_text(count=170, gap_s=328, start_mv=4100, step_mv=6):
    lines = []
    for i in range(count):
        ts = START1 + datetime.timedelta(seconds=i * gap_s)
        lines.append("[%s]   telemetry: X-Battery-Mv=%d\n" %
                     (ts.isoformat(), start_mv - i * step_mv))
    return "".join(lines)


def run2_rows(count=430, gap_s=74, start_mv=4100, step_mv=2):
    rows = []
    for i in range(count):
        ts = START2 + datetime.timedelta(seconds=i * gap_s)
        rows.append({"ts": ts.isoformat(), "battery_mv": start_mv - i * step_mv,
                     "fw_version": "fw-test", "boot_reason": "rtc", "rssi": "-60"})
    return rows


def make_report(export_bytes, rows):
    cut = next(i for i, r in enumerate(rows) if r["battery_mv"] <= 3300)
    return {
        "export": {"sha256": hashlib.sha256(export_bytes).hexdigest(),
                   "row_count": len(rows), "dropped_rows": 0},
        "window": {"first_ts": rows[0]["ts"],
                   "normal_window_end_ts": rows[cut]["ts"]},
        "reconciliation": {"observed_normal": cut + 1, "nominal": cut + 21.5},
        "cadence": {"configured_interval_s": 60, "effective_mean_gap_s": 74.0,
                    "max_gap_s": 74.0},
        "reference_interval": {"reference_interval_s": 70},
        "verdicts": {"continuity": {"status": "FAIL", "checks": [
            {"name": "coverage is at least 0.95", "status": "FAIL",
             "reason": "coverage is 0.946, synthetic reason text"},
            {"name": "run spans at least 1 day(s)", "status": "PASS", "reason": ""}]}},
        "baseline": {"firmware_version": "fw-test"},
    }


def build_inputs(tmp_path, report_edit=None, run1_text=None, rows=None):
    rows = rows if rows is not None else run2_rows()
    export_bytes = "".join(json.dumps(r) + "\n" for r in rows).encode()
    report = make_report(export_bytes, rows)
    if report_edit:
        report_edit(report)
    (tmp_path / "run1.log").write_text(run1_text if run1_text is not None else run1_log_text())
    (tmp_path / "run2.jsonl").write_bytes(export_bytes)
    (tmp_path / "report.json").write_text(json.dumps(report))
    return tmp_path / "run1.log", tmp_path / "run2.jsonl", tmp_path / "report.json"


def run_model(run1, export, report, extra=(), capacity="3000"):
    return subprocess.run(
        [sys.executable, LOGTOOLS, "battery-model", str(run1),
         "--run2-export", str(export), "--run2-report", str(report),
         "--capacity-mah", capacity] + list(extra),
        capture_output=True, text=True)


def model_json(tmp_path, **kw):
    run1, export, report = build_inputs(tmp_path, **kw)
    out = tmp_path / "model.json"
    proc = run_model(run1, export, report, ["--out", str(out)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    return proc, json.loads(out.read_text())


def refused(proc, out):
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert proc.stderr.startswith("battery-model: refused:"), proc.stderr
    assert not out.exists()


def test_happy_path_prints_every_block_once_and_writes_json(tmp_path):
    proc, data = model_json(tmp_path)
    lines = [ln.strip() for ln in proc.stdout.splitlines()]
    for heading in HEADINGS:
        assert lines.count(heading) == 1, heading
    for interval in (300, 600, 900, 1800):
        rows = [ln for ln in lines if ln.split() and ln.split()[0] == str(interval)]
        assert len(rows) == 1, interval
    assert set(data) >= {"inputs", "central_fit", "autonomy", "envelope", "sweeps",
                         "assumptions", "does_not_measure", "warnings",
                         "rated_capacity"}
    assert [row["configured_s"] for row in data["autonomy"]] == [300, 600, 900, 1800]
    for row in data["autonomy"]:
        assert row["min_days"] <= row["central_days"] <= row["max_days"]


def test_labels_continuity_and_extrapolation_warning(tmp_path):
    proc, data = model_json(tmp_path)
    assert "rated, not measured" in proc.stdout
    assert "continuity verdict: FAIL" in proc.stdout
    assert "coverage is 0.946, synthetic reason text" in proc.stdout
    flags = {row["configured_s"]: row["outside_observed_range"] for row in data["autonomy"]}
    assert flags == {300: False, 600: True, 900: True, 1800: True}
    assert "observed gap range" in proc.stdout
    assert data["rated_capacity"]["mah"] == 3000
    assert "rated, not measured" in data["rated_capacity"]["label"]


def test_refuses_run_one_with_fewer_than_two_polls(tmp_path):
    run1, export, report = build_inputs(tmp_path, run1_text=run1_log_text(count=1))
    out = tmp_path / "o.json"
    refused(run_model(run1, export, report, ["--out", str(out)]), out)


def test_refuses_run_one_that_never_reaches_the_cut(tmp_path):
    run1, export, report = build_inputs(
        tmp_path, run1_text=run1_log_text(count=50, step_mv=1))
    out = tmp_path / "o.json"
    refused(run_model(run1, export, report, ["--out", str(out)]), out)


def test_refuses_missing_run_one_log(tmp_path):
    run1, export, report = build_inputs(tmp_path)
    out = tmp_path / "o.json"
    refused(run_model(tmp_path / "absent.log", export, report, ["--out", str(out)]), out)


def test_refuses_export_hash_differing_from_report(tmp_path):
    def edit(rep):
        rep["export"]["sha256"] = "0" * 64
    run1, export, report = build_inputs(tmp_path, report_edit=edit)
    out = tmp_path / "o.json"
    refused(run_model(run1, export, report, ["--out", str(out)]), out)


def edit_observed_count(rep):
    rep["reconciliation"]["observed_normal"] += 1


def edit_cut_timestamp(rep):
    rep["window"]["normal_window_end_ts"] = "2030-02-01T00:00:00+00:00"


@pytest.mark.parametrize("edit", [edit_observed_count, edit_cut_timestamp])
def test_refuses_recomputed_window_differing_from_report(tmp_path, edit):
    run1, export, report = build_inputs(tmp_path, report_edit=edit)
    out = tmp_path / "o.json"
    refused(run_model(run1, export, report, ["--out", str(out)]), out)


def test_refuses_report_missing_a_read_key(tmp_path):
    def edit(rep):
        del rep["cadence"]["configured_interval_s"]
    run1, export, report = build_inputs(tmp_path, report_edit=edit)
    out = tmp_path / "o.json"
    refused(run_model(run1, export, report, ["--out", str(out)]), out)


def test_refuses_when_faster_run_has_no_more_cycles(tmp_path):
    rows = run2_rows(count=100, step_mv=10)
    run1, export, report = build_inputs(tmp_path, rows=rows)
    out = tmp_path / "o.json"
    refused(run_model(run1, export, report, ["--out", str(out)]), out)


@pytest.mark.parametrize("bad", ["300,0", "300,-5", "300,abc", "300,1.5", ""])
def test_refuses_bad_interval_lists(tmp_path, bad):
    run1, export, report = build_inputs(tmp_path)
    out = tmp_path / "o.json"
    refused(run_model(run1, export, report, ["--out", str(out), "--intervals", bad]), out)


def test_output_is_deterministic_and_carries_no_paths(tmp_path):
    outs = []
    for n in range(2):
        sub = tmp_path / ("d%d" % n)
        sub.mkdir()
        run1, export, report = build_inputs(sub)
        out = sub / "m.json"
        assert run_model(run1, export, report, ["--out", str(out)]).returncode == 0
        outs.append(out.read_bytes())
    assert outs[0] == outs[1]
    text = outs[0].decode()
    assert str(tmp_path) not in text
    assert "run1.log" in text and "run2.jsonl" in text and "report.json" in text
    assert hashlib.sha256((tmp_path / "d0" / "run2.jsonl").read_bytes()).hexdigest() in text


def test_committed_inputs_reproduce_the_recorded_counts(tmp_path):
    run1 = os.path.join(COMMITTED, "battery-run-server.log")
    export = os.path.join(COMMITTED, "battery-run2-export.jsonl")
    report = os.path.join(COMMITTED, "battery-run2-report.json")
    out = tmp_path / "committed.json"
    proc = run_model(run1, export, report, ["--out", str(out)])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    inputs = json.loads(out.read_text())["inputs"]
    raw = inputs["run1"]["raw_cut"]
    assert (raw["polls"], raw["elapsed_s"], raw["cut_mv"]) == (2992, 980481, 3292)
    assert inputs["run2"]["window"]["polls"] == 6148
    assert inputs["run2"]["window"]["elapsed_s"] == 455125
    assert "3366, 3372, 3368, 3292, 3368, 3372, 3366" in proc.stdout
    assert "What this model does not measure" in proc.stdout


def test_tool_selects_neither_interval_nor_pack(tmp_path):
    proc, data = model_json(tmp_path)
    blob = proc.stdout + json.dumps(data)
    assert "recommended_interval" not in blob
    assert "chosen" not in blob
    assert "owner's choice" in proc.stdout
