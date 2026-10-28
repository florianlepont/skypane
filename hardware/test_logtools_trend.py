"""Behaviour tests for the `sleep-trend` estimator in `logtools.py`.

Every input is synthetic and built in tmp_path or in memory: a battery whose
charge falls at an exactly known current, read back through the repository
curve. No real owner export is needed for the suite to pass.
"""
import datetime
import hashlib
import importlib.util
import json
import os
import re
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
LOGTOOLS = os.path.join(HERE, "logtools.py")
SERVER_DIR = os.path.join(os.path.dirname(HERE), "server")
MODEL_JSON = os.path.join(HERE, "logs", "battery-model.json")
RUN2_REPORT = os.path.join(HERE, "logs", "battery-run2-report.json")

_spec = importlib.util.spec_from_file_location("logtools_trend_under_test", LOGTOOLS)
lt = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lt)

_dp_spec = importlib.util.spec_from_file_location(
    "device_policy_for_trend_tests", os.path.join(SERVER_DIR, "device_policy.py"))
dp = importlib.util.module_from_spec(_dp_spec)
sys.modules[_dp_spec.name] = dp
_dp_spec.loader.exec_module(dp)

UTC = datetime.timezone.utc
# 2026-01-05 is a winter Monday, so Paris is UTC+1 and local times are easy.
START = datetime.datetime(2026, 1, 5, 6, 0, tzinfo=UTC)


def mv_for_fraction(fraction):
    """Inverse of the repository curve: the millivolts that read as `fraction`."""
    target = fraction * 100.0
    knots = dp.BATTERY_DISCHARGE_CURVE
    for (mv_a, pct_a), (mv_b, pct_b) in zip(knots, knots[1:]):
        if pct_a <= target <= pct_b:
            return mv_a + (mv_b - mv_a) * (target - pct_a) / (pct_b - pct_a)
    raise ValueError(fraction)


def synthetic_polls(current_ma, capacity_mah, days=5, interval_s=900,
                    start_fraction=0.80, extra_mv=None, round_mv=True):
    """Polls of a pack drained at exactly `current_ma`. `extra_mv(i, ts, elapsed_h)`
    adds millivolts to a poll (glitches, sag, early drop)."""
    polls = []
    count = int(days * 86400 / interval_s)
    for i in range(count):
        ts = START + datetime.timedelta(seconds=i * interval_s)
        elapsed_h = i * interval_s / 3600.0
        fraction = start_fraction - current_ma * elapsed_h / capacity_mah
        mv = mv_for_fraction(fraction)
        if extra_mv is not None:
            mv += extra_mv(i, ts, elapsed_h)
        polls.append(lt.BatteryPoll(ts, int(round(mv)) if round_mv else mv, ""))
    return polls


def is_paris_night(ts, start="23:30", end="06:00"):
    return dp.seconds_until_quiet_hours_end(ts, start, end) is not None


def estimate(polls, capacity_mah=3000, **kw):
    return lt.estimate_average_current_ma(polls, capacity_mah, **kw)


@pytest.mark.parametrize("capacity,current", [(3000, 3.0), (10000, 9.0)])
def test_constant_current_is_recovered_within_two_percent(capacity, current):
    polls = synthetic_polls(current, capacity)
    result = estimate(polls, capacity)
    assert result["average_ma"] == pytest.approx(current, rel=0.02)


def test_first_24_hours_do_not_change_the_estimate():
    base = synthetic_polls(3.0, 3000)
    dropped = synthetic_polls(3.0, 3000, extra_mv=lambda i, ts, h: -120 if h < 24 else 0)
    assert estimate(dropped)["average_ma"] == estimate(base)["average_ma"]


def test_single_glitch_poll_does_not_move_the_median():
    # a slow fall keeps neighbouring polls within a millivolt, so one 200 mV
    # outlier moves a median by at most a step while a mean would move ~10 mV
    base = synthetic_polls(0.5, 3000)
    glitched = synthetic_polls(0.5, 3000)
    idx = len(glitched) - 40
    assert not is_paris_night(glitched[idx].ts)
    glitched[idx] = lt.BatteryPoll(glitched[idx].ts, glitched[idx].mv - 200, "")
    assert abs(estimate(glitched)["last"]["mv"] - estimate(base)["last"]["mv"]) <= 1


def test_quiet_hours_polls_are_left_out_of_the_end_medians():
    def sag(i, ts, h):
        return -80 if is_paris_night(ts) else 0

    base = synthetic_polls(3.0, 3000)
    sagged = synthetic_polls(3.0, 3000, extra_mv=sag)
    with_quiet = estimate(sagged)
    assert with_quiet["average_ma"] == pytest.approx(estimate(base)["average_ma"], rel=1e-9)
    assert with_quiet["quiet_share"] > 0.2
    without = estimate(sagged, quiet_window=None)
    assert without["average_ma"] != pytest.approx(with_quiet["average_ma"], rel=0.01)
    assert without["quiet_share"] == 0.0


def test_end_point_time_is_the_median_timestamp_of_selected_polls():
    polls = synthetic_polls(3.0, 3000)
    result = estimate(polls, quiet_window=None)
    first_cut = polls[0].ts + datetime.timedelta(hours=24)
    first_sel = [p for p in polls if first_cut <= p.ts < first_cut + datetime.timedelta(hours=12)]
    last_sel = [p for p in polls if p.ts > polls[-1].ts - datetime.timedelta(hours=12)]
    mid_first = first_sel[0].ts + (first_sel[-1].ts - first_sel[0].ts) / 2
    mid_last = last_sel[0].ts + (last_sel[-1].ts - last_sel[0].ts) / 2
    assert result["first"]["ts"] == mid_first
    assert result["last"]["ts"] == mid_last
    assert result["elapsed_hours"] == pytest.approx((mid_last - mid_first).total_seconds() / 3600)
    assert result["first"]["polls"] == len(first_sel)


def test_span_under_48_hours_after_the_cut_is_refused():
    polls = synthetic_polls(3.0, 3000, days=2.9)
    with pytest.raises(lt.RunReportError, match="48"):
        estimate(polls)


def test_too_few_non_quiet_polls_at_an_end_is_refused():
    # one poll per 6 h leaves 2 polls in a 12 h window
    polls = synthetic_polls(3.0, 3000, days=6, interval_s=6 * 3600)
    with pytest.raises(lt.RunReportError, match="at least 5"):
        estimate(polls, quiet_window=None)


def test_non_positive_fall_is_refused_without_a_current():
    polls = synthetic_polls(-1.0, 3000)
    with pytest.raises(lt.RunReportError) as info:
        estimate(polls)
    assert "resolve" in str(info.value)
    assert "no current is claimed" in str(info.value)


def test_hypotheses_come_from_the_committed_json_files():
    with open(MODEL_JSON) as fh:
        model = json.load(fh)
    with open(RUN2_REPORT) as fh:
        report = json.load(fh)
    hyp = lt.trend_hypotheses(model, report, 900, 3000)
    assert hyp["favourable_ma"] == pytest.approx(
        report["energy_normal_window"]["mah_per_cycle"] * 4)
    assert hyp["central_ma"] == pytest.approx(
        model["central_fit"]["standing_ma"] + model["central_fit"]["wake_mah"] * 4)
    assert round(hyp["favourable_ma"], 2) == 1.95
    assert round(hyp["central_ma"], 2) == 8.66
    assert hyp["allowance_ma"] == pytest.approx(3000 / 4320)
    assert lt.trend_hypotheses(model, report, 900, 10000)["allowance_ma"] == pytest.approx(
        10000 / 4320)


def test_missing_hypothesis_inputs_are_refused():
    with pytest.raises(lt.RunReportError):
        lt.trend_hypotheses({}, {}, 900, 3000)


@pytest.mark.parametrize("value,key", [
    (0.5, "at_or_below_allowance"),
    (0.69, "at_or_below_allowance"),
    (1.0, "between_allowance_and_favourable"),
    (1.95, "between_allowance_and_favourable"),
    (4.0, "between_favourable_and_central"),
    (8.66, "between_favourable_and_central"),
    (9.0, "above_central"),
])
def test_band_classification(value, key):
    band, sentence = lt.classify_current_band(value, 0.69, 1.95, 8.66)
    assert band == key
    assert sentence


def test_estimate_exactly_on_a_reference_falls_in_the_lower_band():
    assert lt.classify_current_band(0.7, 0.7, 2.0, 8.0)[0] == "at_or_below_allowance"
    assert lt.classify_current_band(2.0, 0.7, 2.0, 8.0)[0] == "between_allowance_and_favourable"
    assert lt.classify_current_band(8.0, 0.7, 2.0, 8.0)[0] == "between_favourable_and_central"


def test_band_sentence_names_the_two_references():
    _, sentence = lt.classify_current_band(4.0, 0.69, 1.95, 8.66)
    assert "1.95" in sentence and "8.66" in sentence


def test_band_is_not_applicable_when_the_allowance_is_not_below_favourable():
    band, sentence = lt.classify_current_band(3.0, 2.31, 1.95, 8.66)
    assert band == "not_applicable"
    for number in ("2.31", "1.95", "8.66"):
        assert number in sentence


def test_default_quiet_window_is_the_production_window_not_the_code_default():
    def local(h, m):
        # winter: Paris = UTC+1
        return datetime.datetime(2026, 1, 5, h - 1, m, tzinfo=UTC)

    assert lt.TREND_QUIET_START == "23:30" and lt.TREND_QUIET_END == "06:00"
    def quiet(ts):
        return lt.is_trend_quiet(ts, (lt.TREND_QUIET_START, lt.TREND_QUIET_END))

    assert not quiet(local(23, 10))
    assert quiet(local(23, 40))
    assert quiet(datetime.datetime(2026, 1, 6, 4, 50, tzinfo=UTC))  # 05:50 Paris
    assert not quiet(datetime.datetime(2026, 1, 6, 5, 10, tzinfo=UTC))  # 06:10 Paris
    assert not lt.is_trend_quiet(local(23, 40), None)


def test_sensitivity_per_10_mv_matches_the_curve():
    polls = synthetic_polls(3.0, 3000)
    result = estimate(polls)
    for end in ("first", "last"):
        mv = result[end]["mv"]
        step = (dp.battery_fraction(mv + 10) - dp.battery_fraction(mv)) * 3000
        assert result["sensitivity_ma_per_10mv"][end] == pytest.approx(
            step / result["elapsed_hours"])


# --- top of the curve --------------------------------------------------------

def top_of_curve_report(tmp_path, start_mv, end_mv, days=5):
    """Run build_sleep_trend_report on a straight fall from start_mv to end_mv."""
    count = int(days * 86400 / 900)
    polls = []
    for i in range(count):
        ts = START + datetime.timedelta(seconds=i * 900)
        mv = start_mv + (end_mv - start_mv) * i / (count - 1)
        polls.append(lt.BatteryPoll(ts, int(round(mv)), ""))
    export = write_export(tmp_path / "top.jsonl", polls)
    with open(MODEL_JSON) as fh:
        model = json.load(fh)
    with open(RUN2_REPORT) as fh:
        run2 = json.load(fh)
    params = {"capacity_mah": 3000, "interval_s": 900, "ignore_hours": 24.0,
              "edge_hours": 12.0, "quiet_window": ("23:30", "06:00"), "start_utc": None}
    return lt.build_sleep_trend_report(export.read_bytes(), params, model, run2), export


def test_top_of_curve_limit_is_the_4000_mv_knot():
    assert lt.TREND_CURVE_LIMIT_MV == 4000
    assert (4000, 90) in dp.BATTERY_DISCHARGE_CURVE


def test_end_points_above_4000_mv_give_no_band(tmp_path):
    # the situation of the 900 s owner export: end medians near 4022 and 4008 mV,
    # an estimate far below the allowance that the curve cannot support
    report, _ = top_of_curve_report(tmp_path, 4026, 4004)
    assert report["estimate"]["first"]["mv"] > 4000
    assert report["estimate"]["average_ma"] < report["hypotheses"]["allowance_ma"]
    assert report["band"] == "not_applicable"
    assert "not calibrated" in report["band_sentence"]
    assert report["estimate"]["curve_calibrated"] is False
    assert any("4000 mV" in item for item in report["does_not_measure"])


def test_one_end_point_above_4000_mv_is_enough(tmp_path):
    report, _ = top_of_curve_report(tmp_path, 4020, 3960)
    assert report["estimate"]["first"]["mv"] > 4000 >= report["estimate"]["last"]["mv"]
    assert report["band"] == "not_applicable"


def test_both_end_points_below_4000_mv_keep_a_normal_band(tmp_path):
    report, _ = top_of_curve_report(tmp_path, 3990, 3930)
    assert report["estimate"]["first"]["mv"] <= 4000
    assert report["estimate"]["curve_calibrated"] is True
    assert report["band"] in ("at_or_below_allowance", "between_allowance_and_favourable",
                              "between_favourable_and_central", "above_central")
    assert "not calibrated" not in report["band_sentence"]


def test_cli_labels_the_estimate_unreliable_above_4000_mv(tmp_path):
    _, export = top_of_curve_report(tmp_path, 4026, 4004)
    out = run_trend(*standard_args(export)).stdout.decode()
    assert re.findall(r"^band: (\S+)$", out, re.M) == ["not_applicable"]
    assert re.search(r"average current: [0-9.]+ mA \(unreliable", out)
    assert "not calibrated" in out


# --- CLI ---------------------------------------------------------------------

BAND_FIXTURES = [
    ("at_or_below_allowance", 0.4, 3000),
    ("between_allowance_and_favourable", 1.2, 3000),
    ("between_favourable_and_central", 4.0, 3000),
    ("above_central", 12.0, 3000),
    ("not_applicable", 3.0, 10000),
]


def write_export(path, polls):
    lines = []
    for p in polls:
        lines.append(json.dumps({
            "ts": p.ts.isoformat(), "battery_mv": p.mv, "fw_version": "fw-v1.0.2",
            "boot_reason": "rtc", "rssi": "-57"}))
    path.write_text("\n".join(lines) + "\n")
    return path


def run_trend(*args, stdin=None):
    return subprocess.run(
        [sys.executable, LOGTOOLS, "sleep-trend", *args],
        input=stdin, capture_output=True, timeout=60)


def sag_at_night(i, ts, h):
    return -60 if is_paris_night(ts) else 0


def standard_args(export, capacity=3000):
    return [str(export), "--capacity-mah", str(capacity), "--interval-s", "900"]


def test_cli_prints_estimate_caveats_and_band(tmp_path):
    export = write_export(tmp_path / "e.jsonl",
                          synthetic_polls(2.0, 3000, extra_mv=sag_at_night))
    done = run_trend(*standard_args(export))
    out = done.stdout.decode()
    assert done.returncode == 0, done.stderr.decode()
    match = re.search(r"average current: ([0-9.]+) mA", out)
    assert match and float(match.group(1)) == pytest.approx(2.0, rel=0.05)
    assert "rated, not measured" in out
    assert "What this estimate does not measure" in out
    assert "first 24 h" in out
    assert "180-day allowance" in out
    assert "favourable" in out and "central" in out
    assert re.search(r"^band: between_favourable_and_central$", out, re.M)
    assert "export sha256: " + hashlib.sha256(export.read_bytes()).hexdigest() in out
    for bias in ("Rest-voltage creep", "1 mV", "Quiet-hours wakes", "single interval"):
        assert bias in out


@pytest.mark.parametrize("key,current,capacity", BAND_FIXTURES)
def test_cli_prints_one_band_key_per_fixture(tmp_path, key, current, capacity):
    export = write_export(tmp_path / "e.jsonl", synthetic_polls(current, capacity))
    done = run_trend(*standard_args(export, capacity))
    out = done.stdout.decode()
    assert done.returncode == 0, done.stderr.decode()
    assert re.findall(r"^band: (\S+)$", out, re.M) == [key]
    assert not re.search(r"finding", out, re.I)


def test_cli_refuses_a_short_export(tmp_path):
    export = write_export(tmp_path / "e.jsonl", synthetic_polls(3.0, 3000, days=1.25))
    done = run_trend(*standard_args(export))
    assert done.returncode == 2
    assert done.stderr.decode().startswith("sleep-trend: refused: ")
    assert done.stdout == b""


def test_cli_refuses_a_rising_voltage(tmp_path):
    export = write_export(tmp_path / "e.jsonl", synthetic_polls(-2.0, 3000, start_fraction=0.5))
    done = run_trend(*standard_args(export))
    assert done.returncode == 2
    assert "no current is claimed" in done.stderr.decode()


def test_cli_refuses_an_unreadable_input(tmp_path):
    done = run_trend(*standard_args(tmp_path / "missing.jsonl"))
    assert done.returncode == 2
    assert "sleep-trend: refused: " in done.stderr.decode()


def test_cli_out_is_deterministic_and_written_only_on_success(tmp_path):
    export = write_export(tmp_path / "e.jsonl", synthetic_polls(2.0, 3000))
    before = export.read_bytes()
    out_a, out_b = tmp_path / "a.json", tmp_path / "b.json"
    assert run_trend(*standard_args(export), "--out", str(out_a)).returncode == 0
    assert run_trend(*standard_args(export), "--out", str(out_b)).returncode == 0
    assert out_a.read_bytes() == out_b.read_bytes()
    text = out_a.read_text()
    assert text.endswith("\n") and text.startswith("{\n  ")
    report = json.loads(text)
    assert report["export_sha256"] == hashlib.sha256(before).hexdigest()
    assert report["band"] == "between_favourable_and_central"
    assert export.read_bytes() == before
    short = write_export(tmp_path / "short.jsonl", synthetic_polls(2.0, 3000, days=1))
    refused = tmp_path / "refused.json"
    assert run_trend(*standard_args(short), "--out", str(refused)).returncode == 2
    assert not refused.exists()


def test_cli_reads_stdin(tmp_path):
    export = write_export(tmp_path / "e.jsonl", synthetic_polls(2.0, 3000))
    done = run_trend("--capacity-mah", "3000", "--interval-s", "900",
                     stdin=export.read_bytes())
    assert done.returncode == 0, done.stderr.decode()
    assert "average current:" in done.stdout.decode()


def test_cli_start_utc_drops_earlier_rows_and_prints_the_cut(tmp_path):
    # 2 days of a charge-like rise, then a clean 5-day fall
    early = synthetic_polls(-3.0, 3000, days=2, start_fraction=0.5)
    late = synthetic_polls(2.0, 3000)
    shift = datetime.timedelta(days=2)
    late = [lt.BatteryPoll(p.ts + shift, p.mv, "") for p in late]
    export = write_export(tmp_path / "e.jsonl", early + late)
    cut = (START + shift).isoformat()
    done = run_trend(*standard_args(export), "--start-utc", cut)
    out = done.stdout.decode()
    assert done.returncode == 0, done.stderr.decode()
    assert "rows before " + cut in out
    match = re.search(r"average current: ([0-9.]+) mA", out)
    assert float(match.group(1)) == pytest.approx(2.0, rel=0.05)


def test_cli_no_quiet_hours_flag_and_bad_quiet_time(tmp_path):
    export = write_export(tmp_path / "e.jsonl", synthetic_polls(2.0, 3000))
    done = run_trend(*standard_args(export), "--no-quiet-hours")
    assert done.returncode == 0
    assert "quiet hours: off" in done.stdout.decode()
    bad = run_trend(*standard_args(export), "--quiet-start", "25:00")
    assert bad.returncode == 2
    both = run_trend(*standard_args(export), "--no-quiet-hours", "--quiet-start", "23:00")
    assert both.returncode == 2


def test_help_lists_band_keys_without_finding_letters():
    done = run_trend("--help")
    text = done.stdout.decode()
    assert done.returncode == 0
    for key in ("at_or_below_allowance", "between_favourable_and_central", "above_central"):
        assert key in text
    assert not re.search(r"finding|\([abc]\)", text, re.I)


def test_suite_runs_without_any_committed_owner_export(tmp_path):
    # every fixture above lives in tmp_path; nothing under hardware/logs is read
    # except the two committed analysis JSON files the hypotheses come from
    export = write_export(tmp_path / "e.jsonl", synthetic_polls(2.0, 3000))
    assert run_trend(*standard_args(export)).returncode == 0
