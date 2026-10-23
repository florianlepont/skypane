"""Behaviour tests for the `sleep-trend` estimator in `logtools.py`.

Every input is synthetic and built in tmp_path or in memory: a battery whose
charge falls at an exactly known current, read back through the repository
curve. No real owner export is needed for the suite to pass.
"""
import datetime
import importlib.util
import json
import os
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
                    start_fraction=0.92, extra_mv=None, round_mv=True):
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
    assert with_quiet["quiet_share"] > 0.3
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
    polls = synthetic_polls(3.0, 3000, days=3.9)
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
    quiet = lambda ts: lt.is_trend_quiet(ts, (lt.TREND_QUIET_START, lt.TREND_QUIET_END))
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
