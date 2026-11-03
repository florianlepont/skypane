"""Behaviour tests for the per-wake energy model in `wakemodel.py`.

Every export here is synthetic. `build_export` is the documented generator: it
simulates a pack that drains exactly the truth values below, reads it back
through the rated curve to integer millivolts, and writes one row per wake
with the previous-wake fields a frame would send. The committed fixtures are
written by this same builder and a test checks that they are reproduced byte
for byte. Tests assert returned values, CLI stdout and exit codes only.
"""
import datetime
import importlib.util
import json
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES = os.path.join(HERE, "fixtures")
SCRIPT = os.path.join(HERE, "wakemodel.py")

_spec = importlib.util.spec_from_file_location("wakemodel_under_test", SCRIPT)
wm = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = wm
_spec.loader.exec_module(wm)
lt = wm.lt

# Synthetic truth. The capacity is a rating, not a measurement; it is small so that
# whole-millivolt quantisation is small against each segment's fall.
CAPACITY_MAH = 1000.0
TRUTH = {"standing_ma": 0.60, "nochange_mah": 0.20, "redraw_mah": 1.20}
START_FRACTION = 0.895  # about 3990 mV, inside the calibrated band
NOCHANGE_AWAKE_MS = 5000  # 0.20 mAh over 5 s is about 144 mA
REDRAW_AWAKE_MS = 25000  # 1.20 mAh over 25 s is about 173 mA
T0 = datetime.datetime(2026, 3, 2, 8, 0, 0, tzinfo=datetime.timezone.utc)

# (check-in interval in minutes, redraw share in percent) per 48 h segment
# after the first 24 h; the first 24 h are 60 minutes and 0 percent.
MIXED_PLAN = [(60, 0), (30, 50), (60, 25), (30, 0), (60, 50), (30, 25), (20, 10), (20, 40)]
# One interval and one redraw share in every segment.
COLLINEAR_PLAN = [(30, 25)] * 8
# Mixed cadences for exactly 14 days: 24 h + six 48 h segments + 24 h.
BOUNDARY_PLAN = [(60, 0), (30, 50), (60, 25), (30, 0), (60, 50), (30, 25), (60, 0)]


def _mv_for_fraction(fraction):
    """Integer millivolts whose rated-curve fraction is nearest `fraction`."""
    lo, hi = 3000, 4300
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if lt._trend_fraction(mid) < fraction:
            lo = mid
        else:
            hi = mid
    return min((lo, hi), key=lambda mv: abs(lt._trend_fraction(mv) - fraction))


def build_export(plan, truth=None, hours_total=None, ignore_cadence=60,
                 telemetry=True, start=T0):
    """JSON Lines text of one export row per wake.

    The first 24 h run at `ignore_cadence` minutes with no redraws, then each
    (interval, redraw percent) of `plan` covers 48 h. The pack drains the
    standing draw continuously and each wake's energy right after its row.
    """
    truth = truth or TRUTH
    schedule = ([(24.0, ignore_cadence, 0)] + [(48.0, c, s) for c, s in plan]
                + [(1.0, 60, 0)])  # a closing hour so the last segment is complete
    rows = []
    charge = 0.0  # mAh used so far
    now = start
    seq = 100
    acc = 0
    prev = None
    end = None if hours_total is None else start + datetime.timedelta(hours=hours_total)
    for hours, cadence, share in schedule:
        seg_end = now + datetime.timedelta(hours=hours)
        acc = 0
        while now < seg_end:
            if end is not None and now >= end:
                return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
            acc += share
            redraw = acc >= 100
            if redraw:
                acc -= 100
            fraction = START_FRACTION - charge / CAPACITY_MAH
            row = {"ts": now.isoformat(), "battery_mv": _mv_for_fraction(fraction),
                   "fw_version": "fw-synthetic", "boot_reason": "rtc", "rssi": "-60"}
            row.update(_wake_fields(seq, prev, telemetry))
            rows.append(row)
            prev = (seq, redraw)
            seq += 1
            charge += truth["redraw_mah" if redraw else "nochange_mah"]
            charge += truth["standing_ma"] * cadence / 60.0
            now += datetime.timedelta(minutes=cadence)
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def _wake_fields(seq, prev, telemetry):
    keys = ("wake_seq", "boot_ms", "wifi_ms", "wifi_attempts", "prev_seq",
            "prev_awake_ms", "prev_request_ms", "prev_download_ms", "prev_draw_ms",
            "prev_spi_ms", "prev_tls_ms", "prev_redraw", "prev_outcome")
    out = dict.fromkeys(keys)
    if not telemetry:
        return {}
    out.update({"wake_seq": seq, "boot_ms": 400, "wifi_ms": 1900, "wifi_attempts": 1})
    if prev is not None:
        pseq, redraw = prev
        out.update({
            "prev_seq": pseq, "prev_redraw": 1 if redraw else 0, "prev_outcome": "ok",
            "prev_awake_ms": REDRAW_AWAKE_MS if redraw else NOCHANGE_AWAKE_MS,
            "prev_request_ms": 300, "prev_download_ms": 4000 if redraw else 0,
            "prev_draw_ms": 12000 if redraw else 0, "prev_spi_ms": 9000 if redraw else 0,
            "prev_tls_ms": 650})
    return out


def write_fixtures():
    """Regenerate the committed fixtures (called by a test, not at import)."""
    os.makedirs(FIXTURES, exist_ok=True)
    for name, plan in (("wakemodel-synthetic.jsonl", MIXED_PLAN),
                       ("wakemodel-collinear.jsonl", COLLINEAR_PLAN)):
        with open(os.path.join(FIXTURES, name), "w", encoding="utf-8") as fh:
            fh.write(build_export(plan))


def run_cli(args, cwd=None):
    return subprocess.run([sys.executable, SCRIPT] + args, capture_output=True,
                          text=True, cwd=cwd)


def fit_text(tmp_path, text, extra=None, name="export.jsonl", capacity=CAPACITY_MAH):
    path = tmp_path / name
    path.write_text(text)
    return run_cli(["fit", str(path), "--capacity-mah", str(capacity)] + (extra or []))


def report_for(text, overrides=None, capacity=CAPACITY_MAH):
    return wm.build_report(text.encode(), "export.jsonl", capacity, overrides)


@pytest.fixture(scope="module")
def mixed_text():
    return build_export(MIXED_PLAN)


def within(value, truth, tol=0.10):
    return abs(value - truth) <= tol * truth


# --- recovery -----------------------------------------------------------------


def test_recovers_truth_within_ten_percent(mixed_text):
    report = report_for(mixed_text)
    assert not report["refused"], report["reasons"]
    for name, truth in TRUTH.items():
        assert within(report["fit"][name]["point"], truth), (name, report["fit"][name])


def test_ranges_contain_the_truth_in_most_shifted_scenarios():
    # The ranges are approximate 95 percent ranges, so containment is a
    # statistical property: it is checked over four shifted starts, not forced
    # on one export.
    hits = total = 0
    for shift_h in (0, 1, 2, 3):
        start = T0 + datetime.timedelta(hours=shift_h, minutes=7 * shift_h)
        report = report_for(build_export(MIXED_PLAN, start=start))
        assert not report["refused"], report["reasons"]
        for name, truth in TRUTH.items():
            item = report["fit"][name]
            assert within(item["point"], truth), (shift_h, name, item)
            total += 1
            hits += item["low"] <= truth <= item["high"]
    assert hits / total >= 0.75, (hits, total)


def test_cli_fit_exit_zero_and_prints_ranges(tmp_path, mixed_text):
    proc = fit_text(tmp_path, mixed_text)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "standing draw: at most" in proc.stdout
    assert "best fit" in proc.stdout and "may be zero" in proc.stdout
    assert "redraw wake energy:" in proc.stdout and "95% range" in proc.stdout


@pytest.mark.parametrize("standing", [0.0, 0.05])
def test_near_zero_standing_draw_is_an_upper_bound_not_a_refusal(tmp_path, standing):
    truth = dict(TRUTH, standing_ma=standing)
    text = build_export(MIXED_PLAN, truth)
    report = report_for(text)
    assert not report["refused"], report["reasons"]
    bound = report["fit"]["standing_ma"]
    assert bound["high"] >= standing
    assert bound["point"] >= 0 and bound["low"] >= 0
    assert within(report["fit"]["redraw_mah"]["point"], TRUTH["redraw_mah"])
    proc = fit_text(tmp_path, text)
    assert proc.returncode == 0
    assert "standing draw: at most" in proc.stdout
    assert "-" not in "".join(
        line.split(":", 1)[1] for line in proc.stdout.splitlines()
        if line.strip().startswith(("standing draw", "no-change wake", "redraw wake")
                                   )).replace("95% range", "").replace(" to ", "")


def test_no_negative_value_in_report_json(mixed_text):
    text = build_export(MIXED_PLAN, dict(TRUTH, standing_ma=0.0))
    fit = report_for(text)["fit"]
    for name in wm.UNKNOWNS:
        assert min(fit[name].values()) >= 0.0


# --- refusals -----------------------------------------------------------------


def test_collinear_export_refuses_and_prints_no_energy_figure(tmp_path):
    text = build_export(COLLINEAR_PLAN)
    proc = fit_text(tmp_path, text)
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "REFUSED" in proc.stdout
    assert "redraw share barely varies" in proc.stdout
    assert wm.NO_FIGURE_LINE in proc.stdout
    assert "Fitted values" not in proc.stdout
    assert "standing draw: at most" not in proc.stdout
    assert "mAh (95% range" not in proc.stdout


def test_constant_interval_with_varied_share_is_ill_conditioned():
    text = build_export([(30, s) for s in (0, 50, 25, 75, 10, 40, 60, 20)])
    report = report_for(text)
    assert report["refused"] and report["fit"] is None
    assert any("ill-conditioned" in r and "another check-in interval" in r
               for r in report["reasons"])


def test_too_few_segments_refuses_with_what_is_needed():
    report = report_for(build_export(MIXED_PLAN[:4]))
    assert report["refused"] and report["fit"] is None
    assert "only 4 usable 48 h segment(s)" in report["reasons"][0]
    assert "at least 14 days" in report["reasons"][0]


def test_export_without_per_wake_fields_refuses(tmp_path):
    text = build_export(MIXED_PLAN, telemetry=False)
    proc = fit_text(tmp_path, text)
    assert proc.returncode == 2
    assert wm.NO_TELEMETRY in proc.stdout
    assert wm.NO_FIGURE_LINE in proc.stdout


def test_committed_old_pack_export_refuses_for_missing_telemetry(tmp_path):
    export = os.path.join(HERE, "logs", "oldpack-test-export-2026-11-03.jsonl")
    proc = run_cli(["fit", export, "--capacity-mah", "1000"])
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert wm.NO_TELEMETRY in proc.stdout
    assert wm.NO_FIGURE_LINE in proc.stdout
    assert "Fitted values" not in proc.stdout


def test_redraw_energy_unresolved_refuses():
    # A redraw that costs nothing more than nothing: the fit sets it to zero.
    truth = dict(TRUTH, redraw_mah=0.0)
    report = report_for(build_export(MIXED_PLAN, truth))
    assert report["refused"] and report["fit"] is None
    assert any("not resolved above zero" in r for r in report["reasons"])


def test_unresolved_redraw_is_refused_when_data_is_noise():
    segments = [{"hours": 48.0, "nochange": 50 + i, "redraw": 10 * (i % 3),
                 "charge_mah": 30.0 + (i % 2) * 0.01, "redraw_share": 0.3 * (i % 3)}
                for i in range(6)]
    fit = wm.fit_segments(segments)
    assert wm.resolution_reasons(fit)


def test_implausible_implied_current_demotes_the_fit_to_a_refusal():
    text = build_export(MIXED_PLAN)
    report = report_for(text, {"max_redraw_ma": 50.0})
    assert report["refused"] and report["fit"] is None
    assert any("conflicts with the device-reported timing" in r for r in report["reasons"])
    ok = report_for(text, {"max_redraw_ma": 500.0, "max_nochange_ma": 500.0})
    assert not ok["refused"]


def test_refusal_still_prints_the_device_reported_breakdown(tmp_path):
    proc = fit_text(tmp_path, build_export(COLLINEAR_PLAN))
    assert "Device-reported awake time" in proc.stdout
    assert "redraw (" in proc.stdout and "awake 25000" in proc.stdout


def test_capacity_above_the_calibrated_band_is_not_fitted():
    high = build_export(MIXED_PLAN)
    rows = [json.loads(line) for line in high.splitlines()]
    for row in rows:
        row["battery_mv"] += 200
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    report = report_for(text)
    assert report["refused"]
    assert any("above the 4000 mV limit" in d["reason"] for d in report["segments_dropped"])


# --- the 14-day boundary ------------------------------------------------------


def test_exactly_fourteen_days_gives_six_segments_and_is_fitted(tmp_path):
    text = build_export(BOUNDARY_PLAN, hours_total=14 * 24)
    report = report_for(text)
    assert len(report["segments"]) == 6, report["segments_dropped"]
    assert not report["refused"], report["reasons"]
    assert all(s["first_mv"] <= 4000 for s in report["segments"])
    assert fit_text(tmp_path, text).returncode == 0


def test_one_day_shorter_gives_five_segments_and_refuses():
    text = build_export(BOUNDARY_PLAN, hours_total=13 * 24)
    report = report_for(text)
    assert len(report["segments"]) == 5
    assert report["refused"]
    assert "only 5 usable 48 h segment(s)" in report["reasons"][0]


def test_edge_windows_on_quiet_hours_drop_segments_and_can_refuse():
    # Rows start at 07:00 Paris; segment edges then sit at the same time of
    # day, so a 5 h end window starting at 00:00 holds only quiet polls.
    start = datetime.datetime(2026, 3, 2, 22, 0, 0, tzinfo=datetime.timezone.utc)
    text = build_export(BOUNDARY_PLAN, hours_total=14 * 24, start=start)
    report = report_for(text, {"edge_hours": 5.0})
    assert report["refused"]
    assert report["segments_dropped"]
    assert all("non-quiet polls" in d["reason"] for d in report["segments_dropped"])
    assert "dropped" in report["reasons"][0]


# --- join and classification --------------------------------------------------


def _rows(text):
    return [json.loads(line) for line in text.splitlines()]


def _polls(rows):
    text = "".join(json.dumps(r) + "\n" for r in rows)
    _, polls = lt.parse_battery_lines(lt._load_export_rows(text)[1])
    return polls


def _counts(wakes, lo=0, hi=None):
    out = dict.fromkeys(wm.CLASSES, 0)
    for w in wakes[lo:hi]:
        out[w["cls"]] += 1
    return out


def test_classes_come_from_device_fields_not_from_the_gap():
    rows = _rows(build_export([(30, 50)], hours_total=40))
    wakes = wm.join_wakes(rows, _polls(rows))
    flags = [r["prev_redraw"] for r in rows[1:]]
    assert [w["cls"] for w in wakes] == [
        "redraw" if f == 1 else "nochange" for f in flags]
    rows[5]["prev_outcome"] = "download"
    rows[5]["prev_redraw"] = 0
    rows[6]["prev_redraw"] = 2
    classes = [w["cls"] for w in wm.join_wakes(rows, _polls(rows))]
    assert classes[4] == "failed" and classes[5] == "deferred"


def test_first_wake_after_an_ota_and_a_seq_gap_are_unknown_not_zero():
    rows = _rows(build_export([(30, 50)], hours_total=40))
    base = _counts(wm.join_wakes(rows, _polls(rows)))
    j = 10
    before_class = "redraw" if rows[j]["prev_redraw"] == 1 else "nochange"
    for key in ("prev_seq", "prev_awake_ms", "prev_request_ms", "prev_download_ms",
                "prev_draw_ms", "prev_spi_ms", "prev_tls_ms", "prev_redraw",
                "prev_outcome"):
        rows[j][key] = None
    for row in rows[j:]:
        row["wake_seq"] += 3
        if row["prev_seq"] is not None and row is not rows[j]:
            row["prev_seq"] += 3
    after = _counts(wm.join_wakes(rows, _polls(rows)))
    # the wake before the record-less row, plus the three missed sequence numbers
    assert after["unknown"] == base["unknown"] + 4
    assert after[before_class] == base[before_class] - 1
    other = "redraw" if before_class == "nochange" else "nochange"
    assert after[other] == base[other]
    assert after["failed"] == 0 and after["deferred"] == 0


def test_missed_wakes_are_counted_unknown_in_the_segment_row():
    text = build_export(MIXED_PLAN)
    clean = report_for(text)
    rows = [r for i, r in enumerate(_rows(text)) if not 150 <= i < 153]
    damaged = report_for("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    # the wake before the hole, plus the two missed ones whose own row is lost
    # (the third is classified from the next row's previous-wake block)
    assert damaged["classes"]["unknown"] == clean["classes"]["unknown"] + 3


# --- wording and determinism --------------------------------------------------


def test_fit_output_order_and_wording(tmp_path, mixed_text):
    out = fit_text(tmp_path, mixed_text).stdout
    order = ["Inputs", "Assumptions", "Wakes by class", "Fitted values", "Residual:",
             wm.ESTIMATE_SENTENCE]
    positions = [out.index(item) for item in order]
    assert positions == sorted(positions)
    assert "sha256" in out
    assert "uncalibrated" in out and "rated discharge curve" in out
    assert "not current measurements" in out
    lowered = out.lower()
    assert "measured current" not in lowered


def test_refusal_prints_reason_and_no_figure_line(tmp_path):
    out = fit_text(tmp_path, build_export(COLLINEAR_PLAN)).stdout
    assert out.index("REFUSED") < out.index(wm.NO_FIGURE_LINE)
    assert wm.ESTIMATE_SENTENCE in out


def test_out_json_is_deterministic_across_runs_and_directories(tmp_path, mixed_text):
    export = tmp_path / "e.jsonl"
    export.write_text(mixed_text)
    other = tmp_path / "elsewhere"
    other.mkdir()
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    assert run_cli(["fit", str(export), "--capacity-mah", "1000", "--out", str(first)]).returncode == 0
    assert run_cli(["fit", str(export), "--capacity-mah", "1000", "--out", str(second)],
                   cwd=str(other)).returncode == 0
    assert first.read_bytes() == second.read_bytes()
    assert str(tmp_path) not in first.read_text()


def test_committed_fixtures_are_reproduced_by_the_builder(tmp_path):
    for name, plan in (("wakemodel-synthetic.jsonl", MIXED_PLAN),
                       ("wakemodel-collinear.jsonl", COLLINEAR_PLAN)):
        with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
            assert fh.read() == build_export(plan)


def test_committed_output_json_is_reproduced_byte_for_byte(tmp_path):
    fixture = os.path.join(FIXTURES, "wakemodel-synthetic.jsonl")
    out = tmp_path / "out.json"
    proc = run_cli(["fit", fixture, "--capacity-mah", "1000", "--out", str(out)])
    assert proc.returncode == 0, proc.stdout
    with open(os.path.join(FIXTURES, "wakemodel-synthetic-output.json"), "rb") as fh:
        assert out.read_bytes() == fh.read()


def test_selftest_passes():
    proc = run_cli(["selftest"])
    assert proc.returncode == 0, proc.stdout
    assert proc.stdout.count("PASS") == 2


def test_bad_capacity_and_missing_file_are_errors_not_refusals(tmp_path):
    assert run_cli(["fit", str(tmp_path / "none.jsonl"), "--capacity-mah", "1000"]).returncode == 1
    path = tmp_path / "x.jsonl"
    path.write_text("{}\n")
    assert run_cli(["fit", str(path), "--capacity-mah", "0"]).returncode == 1


def test_hostile_rows_are_refused_not_crashed(tmp_path):
    proc = fit_text(tmp_path, "not json\n[1,2]\n{\"ts\": 5}\n")
    assert proc.returncode == 2
    assert wm.NO_FIGURE_LINE in proc.stdout
