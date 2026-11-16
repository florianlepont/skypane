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
                 telemetry=True, start=T0, seq_start=100):
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
    seq = seq_start
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


def merge_exports(*texts):
    """One export from several: rows stable-sorted by timestamp."""
    rows = [json.loads(line) for text in texts for line in text.splitlines()]
    rows.sort(key=lambda r: datetime.datetime.fromisoformat(r["ts"]))
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


# --- device filter ------------------------------------------------------------


def two_device_text():
    """The owner frame (wake_seq from 21000) mixed with a second device (wake_seq
    from 500, voltage shifted) and a few rows with no wake_seq and no
    previous-wake block.
    """
    owner = build_export(MIXED_PLAN, seq_start=21000)
    other_rows = [json.loads(line) for line in build_export(
        COLLINEAR_PLAN, seq_start=500, start=T0 + datetime.timedelta(minutes=7)
    ).splitlines()]
    for row in other_rows:
        row["battery_mv"] -= 150
    other = "".join(json.dumps(r, sort_keys=True) + "\n" for r in other_rows)
    owner_rows = [json.loads(line) for line in owner.splitlines()]
    nulls = []
    for row in owner_rows[100:400:100]:
        nulls.append({"ts": (datetime.datetime.fromisoformat(row["ts"])
                             + datetime.timedelta(minutes=3)).isoformat(),
                      "battery_mv": 3900, "fw_version": "fw-other", "boot_reason": "rtc",
                      "rssi": "-70", "wake_seq": None, "prev_seq": None,
                      "prev_redraw": None, "prev_outcome": None})
    null_text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in nulls)
    return merge_exports(owner, other, null_text), len(owner_rows), len(other_rows), len(nulls)


def test_seq_filter_keeps_one_device_and_counts_the_rest():
    text, kept, other, nulls = two_device_text()
    flt = {"seq_min": 20000, "seq_max": 30000, "since": None, "until": None}
    alone = report_for(build_export(MIXED_PLAN, seq_start=21000))
    report = wm.build_report(text.encode(), "export.jsonl", CAPACITY_MAH, None, flt)
    assert not report["refused"], report["reasons"]
    assert report["fit"]["redraw_mah"]["point"] == alone["fit"]["redraw_mah"]["point"]
    assert report["fit"]["standing_ma"]["point"] == alone["fit"]["standing_ma"]["point"]
    info = report["inputs"]["device_filter"]
    assert info["rows_before"] == kept + other + nulls
    assert info["rows_kept"] == kept == report["inputs"]["rows"]
    assert info["outside_seq_range"] == other
    assert info["null_wake_seq"] == nulls
    assert info["outside_time_range"] == 0


def test_without_a_filter_the_mixed_export_is_not_the_owner_export():
    text, *_ = two_device_text()
    report = report_for(text)
    assert "device_filter" not in report["inputs"]
    assert report["refused"] or report["fit"] != report_for(
        build_export(MIXED_PLAN, seq_start=21000))["fit"]


def test_time_filter_keeps_since_inclusive_until_exclusive():
    text = build_export(MIXED_PLAN, seq_start=21000)
    since = T0 + datetime.timedelta(hours=10)
    until = T0 + datetime.timedelta(hours=20)
    rows = [json.loads(line) for line in text.splitlines()]
    polls = _polls(rows)
    flt = {"seq_min": None, "seq_max": None, "since": since, "until": until}
    kept_rows, kept_polls, info = wm.filter_rows(rows, polls, flt)
    assert all(since <= p.ts < until for p in kept_polls)
    assert len(kept_rows) == len(kept_polls) == info["rows_kept"] == 10
    assert info["outside_time_range"] == len(rows) - 10
    assert info["outside_seq_range"] == 0 and info["null_wake_seq"] == 0


def test_filter_that_leaves_no_row_refuses(tmp_path):
    proc = fit_text(tmp_path, build_export(MIXED_PLAN, seq_start=21000),
                    ["--seq-min", "1", "--seq-max", "5"])
    assert proc.returncode == 2
    assert "no row left after the device filter" in proc.stdout


def test_cli_filter_prints_counts_and_fits(tmp_path):
    text, kept, other, nulls = two_device_text()
    proc = fit_text(tmp_path, text, ["--seq-min", "20000", "--seq-max", "30000"])
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "device filter: kept %d of %d rows" % (kept, kept + other + nulls) in proc.stdout
    assert "%d outside the wake_seq range, %d with null wake_seq" % (other, nulls) in proc.stdout


@pytest.mark.parametrize("args", [
    ["--since", "not-a-date"],
    ["--since", "2026-03-03T00:00:00Z", "--until", "2026-03-02T00:00:00Z"],
    ["--seq-min", "9", "--seq-max", "3"],
])
def test_bad_filter_values_are_usage_errors(tmp_path, args):
    proc = fit_text(tmp_path, build_export(MIXED_PLAN), args)
    assert proc.returncode == 1, proc.stdout + proc.stderr


# --- relative mode ------------------------------------------------------------

RATES_TRUTH = {"s": 0.05, "C": 0.01, "R": 0.06}  # mV per hour, mV per check, mV per redraw
RATES_REGIMES = [("a", 300, 10, 48), ("b", 300, 60, 48), ("c", 600, 30, 48)]
RATES_COLLINEAR = [("a", 300, 10, 48), ("b", 300, 60, 48), ("c", 300, 30, 48)]
RATES_RESETS = [(20, "poweron"), (78, "ota")]


def build_rates_export(regimes, truth, start, seq_start=21000, start_mv=4120, resets=()):
    """JSON Lines text for the relative mode, one compact row per wake.

    `regimes` is a list of (name, check_s, redraw_min, hours); redraw_min None
    means no redraw. A wake every check_s seconds is a redraw when it is the first
    wake at or after each redraw_min boundary (counted from the regime start),
    otherwise a check. The true voltage falls truth["s"] mV per hour,
    truth["C"] mV after each check wake and truth["R"] mV after each redraw
    wake. The written battery_mv is round(v) + ((seq * 37) % 7) - 3, a
    deterministic quantisation-like jitter of +-3 mV. A closing row at the end of the
    last regime reports the last wake. `resets` is a list of (hours from start,
    kind): "poweron" sets boot_reason "poweron" on the first row at or after that
    time, "ota" changes fw_version from that row on; both drop that row's
    previous-wake block.
    """
    rows = []
    volts = float(start_mv)
    now = start
    seq = seq_start
    prev = None
    pending = sorted(resets)
    fw = "fw-synthetic"
    total = sum(r[3] for r in regimes)
    end = start + datetime.timedelta(hours=total)
    boundaries = []
    t = start
    for _, check_s, redraw_min, hours in regimes:
        boundaries.append((t, t + datetime.timedelta(hours=hours), check_s, redraw_min))
        t += datetime.timedelta(hours=hours)
    for lo, hi, check_s, redraw_min in boundaries:
        step = datetime.timedelta(seconds=check_s)
        next_redraw = lo
        now = lo
        last_regime = hi == end
        while now < hi or (last_regime and now == end):
            boot, block = "rtc", prev
            while pending and now >= start + datetime.timedelta(hours=pending[0][0]):
                _, kind = pending.pop(0)
                block = None
                if kind == "poweron":
                    boot = "poweron"
                else:
                    fw = fw + "-2"
            row = {"ts": now.isoformat(), "battery_mv": round(volts) + ((seq * 37) % 7) - 3,
                   "fw_version": fw, "boot_reason": boot, "rssi": "-60", "wake_seq": seq,
                   "prev_seq": None, "prev_redraw": None, "prev_outcome": None,
                   "prev_awake_ms": None}
            if block is not None:
                row.update({"prev_seq": block[0], "prev_redraw": block[1],
                            "prev_outcome": "ok",
                            "prev_awake_ms": REDRAW_AWAKE_MS if block[1] else NOCHANGE_AWAKE_MS})
            rows.append(row)
            if now == end:
                break
            redraw = redraw_min is not None and now >= next_redraw
            if redraw:
                while next_redraw <= now:
                    next_redraw += datetime.timedelta(minutes=redraw_min)
            prev = (seq, 1 if redraw else 0)
            seq += 1
            volts -= truth["s"] * check_s / 3600.0 + (truth["R"] if redraw else truth["C"])
            now += step
    return "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)


def rates_text(kind="3regime"):
    if kind == "collinear":
        return build_rates_export(RATES_COLLINEAR, RATES_TRUTH, T0)
    owner = build_rates_export(RATES_REGIMES, RATES_TRUTH, T0, resets=RATES_RESETS)
    if kind == "3regime":
        return owner
    other = build_rates_export([("x", 600, None, 144)], RATES_TRUTH,
                               T0 + datetime.timedelta(minutes=3), seq_start=500, start_mv=3950)
    nulls = "".join(json.dumps({
        "ts": (T0 + datetime.timedelta(hours=h, minutes=1)).isoformat(), "battery_mv": 4000,
        "fw_version": "fw-other", "boot_reason": "rtc", "rssi": "-70", "wake_seq": None,
        "prev_seq": None, "prev_redraw": None, "prev_outcome": None, "prev_awake_ms": None},
        sort_keys=True) + "\n" for h in range(6, 144, 6))
    return merge_exports(owner, other, nulls)


def write_rates_fixtures():
    """Regenerate the committed relative-mode fixtures (called by a test)."""
    os.makedirs(FIXTURES, exist_ok=True)
    for name, kind in (("wakemodel-rates-3regime.jsonl", "3regime"),
                       ("wakemodel-rates-collinear.jsonl", "collinear"),
                       ("wakemodel-two-device.jsonl", "two-device")):
        with open(os.path.join(FIXTURES, name), "w", encoding="utf-8") as fh:
            fh.write(rates_text(kind))


def window_args(names=("a", "b", "c"), starts=(0, 48, 96), length=48):
    out = []
    for name, h in zip(names, starts):
        lo = T0 + datetime.timedelta(hours=h)
        out += ["--window", "%s=%s,%s" % (
            name, lo.isoformat(), (lo + datetime.timedelta(hours=length)).isoformat())]
    return out


def rates_cli(tmp_path, text, extra=None, windows=None, name="rates.jsonl"):
    path = tmp_path / name
    path.write_text(text)
    return run_cli(["rates", str(path)] + (window_args() if windows is None else windows)
                   + (extra or []))


def check_wording(out):
    assert wm.RELATIVE_SENTENCE in out
    assert "measured current" not in out.lower()
    for line in out.splitlines():
        if line == wm.RELATIVE_SENTENCE:
            continue
        assert "mAh" not in line and " mA" not in line and "capacity" not in line, line


def rates_json(tmp_path, text, extra=None, windows=None):
    out = tmp_path / "rates-out.json"
    proc = rates_cli(tmp_path, text, (extra or []) + ["--out", str(out)], windows)
    return proc, json.loads(out.read_text())


def test_rates_recovers_the_three_regime_truth(tmp_path):
    proc, report = rates_json(tmp_path, rates_text())
    assert proc.returncode == 0, proc.stdout + proc.stderr
    fit = report["fit"]
    for key, name in (("standing_mv_per_h", "s"), ("check_mv_per_wake", "C"),
                      ("redraw_mv_per_wake", "R")):
        item = fit[key]
        assert item["low"] <= RATES_TRUTH[name] <= item["high"], (key, item)
    assert abs(fit["standing_mv_per_h"]["point"] - RATES_TRUTH["s"]) <= 0.03
    assert within(fit["check_mv_per_wake"]["point"], RATES_TRUTH["C"], 0.15)
    assert within(fit["redraw_mv_per_wake"]["point"], RATES_TRUTH["R"], 0.15)
    for key in ("redraw_over_check", "redraw_over_reference"):
        assert fit[key]["low"] <= fit[key]["point"] <= fit[key]["high"]
    assert within(fit["redraw_over_check"]["point"], RATES_TRUTH["R"] / RATES_TRUTH["C"], 0.25)
    assert "R/C:" in proc.stdout and "R / fall of window a:" in proc.stdout
    check_wording(proc.stdout)


def test_rates_windows_table_has_the_per_window_figures(tmp_path):
    proc = rates_cli(tmp_path, rates_text())
    for name in "abc":
        line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("  %s: " % name))
        for part in ("usable hours", "fall ", "95% range", "checks ", "redraws ",
                     "unknown ", "median "):
            assert part in line, line
    assert "voltage band: 60 mV" in proc.stdout


def test_rates_collinear_check_interval_is_refused(tmp_path):
    proc = rates_cli(tmp_path, rates_text("collinear"))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "REFUSED" in proc.stdout
    assert "rank-deficient or ill-conditioned" in proc.stdout
    assert "a window at another check interval is needed" in proc.stdout
    assert wm.NO_RATES_FIGURE_LINE in proc.stdout
    assert "Fit (mV per hour" not in proc.stdout
    assert "R/C" not in proc.stdout
    check_wording(proc.stdout)


def test_rates_two_windows_give_the_ratio_and_say_nothing_can_be_separated(tmp_path):
    proc, report = rates_json(tmp_path, rates_text(), windows=window_args(("a", "b"), (0, 48)))
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert wm.NO_SEPARATION_LINE in proc.stdout
    assert "ratio of fall a to fall b" in proc.stdout and "95% range" in proc.stdout
    ratio = report["two_window_ratio"]
    assert ratio["low"] < ratio["point"] < ratio["high"]
    assert within(ratio["point"], 0.467 / 0.222, 0.1)
    assert report["fit"] is None
    check_wording(proc.stdout)


def test_rates_windows_apart_in_voltage_are_refused_naming_the_band(tmp_path):
    rows = [json.loads(line) for line in rates_text().splitlines()]
    cut = T0 + datetime.timedelta(hours=96)
    for row in rows:
        if datetime.datetime.fromisoformat(row["ts"]) >= cut:
            row["battery_mv"] -= 100
    text = "".join(json.dumps(r, sort_keys=True) + "\n" for r in rows)
    proc = rates_cli(tmp_path, text)
    assert proc.returncode == 2
    assert "more than the 60 mV band" in proc.stdout
    assert "windows closer in time or voltage are needed" in proc.stdout
    wide = rates_cli(tmp_path, text, ["--band-mv", "200"])
    assert wide.returncode == 0, wide.stdout
    assert "voltage band: 200 mV" in wide.stdout


def test_rates_short_window_and_unresolved_slope_are_refused(tmp_path):
    proc = rates_cli(tmp_path, rates_text(), windows=window_args(("a", "b", "c"), (0, 48, 96), 10))
    assert proc.returncode == 2
    assert "usable hours, at least 24 needed" in proc.stdout


def test_rates_filter_selects_one_device(tmp_path):
    flt = ["--seq-min", "20000", "--seq-max", "30000"]
    alone, alone_report = rates_json(tmp_path, rates_text(), flt)
    both, both_report = rates_json(tmp_path, rates_text("two-device"), flt)
    assert alone.returncode == both.returncode == 0, both.stdout
    assert both_report["windows"] == alone_report["windows"]
    assert both_report["fit"] == alone_report["fit"]
    info = both_report["inputs"]["device_filter"]
    assert info["outside_seq_range"] > 0 and info["null_wake_seq"] == 23
    assert "device filter: kept" in both.stdout and "with null wake_seq" in both.stdout
    unfiltered = rates_cli(tmp_path, rates_text("two-device"))
    assert unfiltered.stdout != both.stdout


def test_rates_restart_rows_exclude_reset_hours(tmp_path):
    _, report = rates_json(tmp_path, rates_text())
    excluded = {w["name"]: w["reset_excluded_hours"] for w in report["windows"]}
    assert excluded == {"a": 3.0, "b": 3.0, "c": 0.0}
    _, none = rates_json(tmp_path, rates_text(), ["--reset-hours", "0"])
    assert all(w["reset_excluded_hours"] == 0.0 for w in none["windows"])


def test_rates_output_is_deterministic_and_has_no_path(tmp_path):
    export = tmp_path / "e.jsonl"
    export.write_text(rates_text())
    other = tmp_path / "elsewhere"
    other.mkdir()
    first, second = tmp_path / "a.json", tmp_path / "b.json"
    args = ["rates", str(export)] + window_args()
    assert run_cli(args + ["--out", str(first)]).returncode == 0
    assert run_cli(args + ["--out", str(second)], cwd=str(other)).returncode == 0
    assert first.read_bytes() == second.read_bytes()
    assert str(tmp_path) not in first.read_text()


def test_rates_export_without_telemetry_refuses(tmp_path):
    rows = [json.loads(line) for line in rates_text().splitlines()]
    for row in rows:
        row.update({"wake_seq": None, "prev_seq": None, "prev_redraw": None,
                    "prev_outcome": None})
    proc = rates_cli(tmp_path, "".join(json.dumps(r) + "\n" for r in rows))
    assert proc.returncode == 2
    assert wm.NO_TELEMETRY in proc.stdout
    check_wording(proc.stdout)


def test_rates_hostile_rows_are_refused_not_crashed(tmp_path):
    proc = rates_cli(tmp_path, "not json\n[1,2]\n{\"ts\": 5}\n")
    assert proc.returncode == 2
    assert wm.RELATIVE_SENTENCE in proc.stdout


@pytest.mark.parametrize("extra,windows", [
    ([], ["--window", "a"]),
    ([], ["--window", "a=2026-03-03T00:00:00Z,2026-03-02T00:00:00Z"]),
    ([], ["--window", "a=2026-03-02T00:00:00Z,2026-03-03T00:00:00Z",
          "--window", "a=2026-03-03T00:00:00Z,2026-03-04T00:00:00Z"]),
    (["--reference", "zzz"], ["--window", "a=2026-03-02T00:00:00Z,2026-03-03T00:00:00Z"]),
    ([], ["--window", "a=nope,2026-03-03T00:00:00Z"]),
    (["--quiet-start", "25:00"], ["--window", "a=2026-03-02T00:00:00Z,2026-03-03T00:00:00Z"]),
])
def test_rates_usage_errors_exit_one(tmp_path, extra, windows):
    proc = rates_cli(tmp_path, rates_text(), extra, windows)
    assert proc.returncode == 1, proc.stdout + proc.stderr


def test_rates_unreadable_file_is_a_usage_error(tmp_path):
    proc = run_cli(["rates", str(tmp_path / "none.jsonl")] + window_args())
    assert proc.returncode == 1


def test_committed_rates_fixtures_are_reproduced_by_the_builder():
    for name, kind in (("wakemodel-rates-3regime.jsonl", "3regime"),
                       ("wakemodel-rates-collinear.jsonl", "collinear"),
                       ("wakemodel-two-device.jsonl", "two-device")):
        with open(os.path.join(FIXTURES, name), encoding="utf-8") as fh:
            assert fh.read() == rates_text(kind), name


def test_fit_and_selftest_are_unaffected_by_the_rates_mode():
    assert "rates" not in wm.DEFAULTS and "band_mv" not in wm.DEFAULTS
