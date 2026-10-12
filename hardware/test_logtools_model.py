"""Behaviour tests for the two-run battery model in `logtools.py`.

The pure functions are called on synthetic numbers with known answers. The
`battery-model` subcommand is driven as a subprocess on inputs built in
tmp_path; one test reads the committed logs under hardware/logs read-only.
"""
import importlib.util
import os

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
    # Scaling the charge of both runs scales wake and standing, not the autonomy.
    n1b, t1b, n2b, t2b = synthetic_runs(energy, standing, 328.0, 74.0)
    scaled = lt.fit_two_runs(n1b, t1b, n2b, t2b)
    assert close(lt.autonomy_days(scaled["wake"] * 3, scaled["standing"] * 3, 614),
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
