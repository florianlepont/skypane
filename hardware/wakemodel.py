#!/usr/bin/env python3
"""Per-wake energy model: fit when the data can separate the unknowns, refuse
when it cannot. Standard library only.

    python3 hardware/wakemodel.py fit EXPORT.jsonl --capacity-mah 3000 [--out FILE]
    python3 hardware/wakemodel.py selftest

Every figure is an energy estimate from voltage and timing on a rated
capacity. None is a current measurement. The rated capacity and the rated
discharge curve are not measurements either; the curve is not calibrated above
4000 mV and a segment that starts there is not used.

The model, per segment of an export (a stretch of rows of fixed length):

    charge used (mAh) = standing_mA * hours
                      + no_change_mAh * no-change wakes
                      + redraw_mAh * redraw wakes

charge used comes from the fall of the rated-curve charge fraction between two
median end points (logtools supplies the curve, the quiet-hour test and the
band limit). The three unknowns are fitted by exact non-negative least
squares. The tool exits 0 for a fit and 2 for a refusal; a refusal prints the
reason and the data that would separate the unknowns, and no wake energy.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURES_DIR = os.path.join(HERE, "fixtures")

_spec = importlib.util.spec_from_file_location(
    "logtools_for_wakemodel", os.path.join(HERE, "logtools.py"))
lt = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = lt
_spec.loader.exec_module(lt)

DEFAULTS = {
    "ignore_hours": 24.0,
    "segment_hours": 48.0,
    "edge_hours": 12.0,
    "min_polls": 5,
    "min_segments": 6,
    "min_share_spread": 0.15,
    "max_condition": 100.0,
    "max_unmodelled_share": 0.25,
    "max_nochange_ma": 500.0,
    "max_redraw_ma": 200.0,
    "quiet_start": lt.TREND_QUIET_START,
    "quiet_end": lt.TREND_QUIET_END,
}

# Two-sided 95 percent Student t quantiles for 1..30 degrees of freedom.
T95 = (
    12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
    2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
    2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042,
)
T95_LARGE = 2.0

UNKNOWNS = ("standing_ma", "nochange_mah", "redraw_mah")
CLASSES = ("nochange", "redraw", "deferred", "failed", "unknown")
TIMING_KEYS = ("prev_awake_ms", "prev_request_ms", "prev_download_ms",
               "prev_draw_ms", "prev_spi_ms", "prev_tls_ms")

ESTIMATE_SENTENCE = (
    "These are energy estimates from voltage and timing on a rated capacity, "
    "not current measurements.")
NO_FIGURE_LINE = "No wake energy figure is given."
NO_TELEMETRY = "no per-wake telemetry in this export"

def assumptions(p):
    return (
        "the battery capacity is the rated value given with --capacity-mah, not a "
        "measurement",
        "the voltage-to-charge curve is the rated discharge curve, not a measurement",
        "readings above %d mV are on an uncalibrated part of the curve; a segment that "
        "starts there is not used" % lt.TREND_CURVE_LIMIT_MV,
        "the first %g h after the first row are ignored (settling after a charge)"
        % p["ignore_hours"],
        "polls in the quiet window %s to %s (Europe/Paris) are left out of the end "
        "points" % (p["quiet_start"], p["quiet_end"]),
        "the 95 percent ranges are approximate: they come from the unconstrained "
        "least-squares covariance and a t table, and ignore curve and capacity error",
    )


class Refusal(Exception):
    """The data cannot support a fit; carries the reasons."""

    def __init__(self, reasons):
        Exception.__init__(self, "; ".join(reasons))
        self.reasons = reasons


# --- Rows, join and classification --------------------------------------------


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _prev_block(row):
    """(redraw, outcome) when the row carries a usable previous-wake block."""
    redraw = row.get("prev_redraw")
    outcome = row.get("prev_outcome")
    if not _is_int(row.get("prev_seq")) or not _is_int(redraw) or redraw not in (0, 1, 2):
        return None
    if not isinstance(outcome, str) or not outcome:
        return None
    return redraw, outcome


def classify(redraw, outcome):
    """no-change, redraw, deferred or failed from the device-reported fields."""
    if redraw == 1:
        return "redraw"
    if redraw == 2:
        return "deferred"
    if outcome == "ok":
        return "nochange"
    return "failed"


def join_wakes(rows, polls):
    """One entry per wake whose record the next row reports, plus unknown and
    missed wakes, as dicts {ts, cls, row} (row is the reporting-wake row index
    or None). A wake's class comes from the next row's previous-wake block when
    that block names this wake's sequence number, never from the time between
    rows. A row without a block, or whose block names another sequence number,
    leaves the wake before it unknown; a jump in sequence numbers adds missed
    wakes, also unknown.
    """
    wakes = []
    for k in range(len(rows) - 1):
        nxt = rows[k + 1]
        seq = rows[k].get("wake_seq")
        seq_next = nxt.get("wake_seq")
        block = _prev_block(nxt)
        cls = "unknown"
        if block is not None and _is_int(seq) and nxt["prev_seq"] == seq:
            cls = classify(*block)
        wakes.append({"ts": polls[k].ts, "cls": cls, "row": k})
        if not (_is_int(seq) and _is_int(seq_next)):
            continue
        missed = seq_next - seq - 1
        if missed > 0 and block is not None and seq < nxt["prev_seq"] < seq_next:
            wakes.append({"ts": polls[k + 1].ts, "cls": classify(*block), "row": None})
            missed -= 1
        wakes.extend({"ts": polls[k + 1].ts, "cls": "unknown", "row": None}
                     for _ in range(max(missed, 0)))
    return wakes


def awake_breakdown(rows):
    """Mean device-reported phase times per wake class over every wake the
    export classifies; a direct measurement, independent of any fit.
    """
    sums = {}
    for k in range(len(rows) - 1):
        nxt = rows[k + 1]
        seq = rows[k].get("wake_seq")
        block = _prev_block(nxt)
        if block is None or not _is_int(seq) or nxt["prev_seq"] != seq:
            continue
        entry = sums.setdefault(classify(*block), {"wakes": 0, "values": {}})
        entry["wakes"] += 1
        for key in TIMING_KEYS:
            if _is_int(nxt.get(key)):
                entry["values"].setdefault(key, []).append(nxt[key])
    out = {}
    for cls in sorted(sums):
        means = {k: statistics.fmean(v) for k, v in sorted(sums[cls]["values"].items())}
        out[cls] = {"wakes": sums[cls]["wakes"], "mean_ms": means}
    return out


# --- Segments -------------------------------------------------------------------


def _edge_point(polls, lo, hi, quiet, min_polls):
    chosen = [p for p in polls if lo <= p.ts < hi and not lt.is_trend_quiet(p.ts, quiet)]
    if len(chosen) < min_polls:
        return None, len(chosen)
    mv, ts, count = lt._median_point(chosen)
    return {"mv": mv, "ts": ts, "polls": count}, count


def _segment_charge(first, last, capacity_mah):
    f_first = lt._trend_fraction(first["mv"])
    f_last = lt._trend_fraction(last["mv"])
    hours = (last["ts"] - first["ts"]).total_seconds() / 3600.0
    return (f_first - f_last) * capacity_mah, hours


def build_segments(polls, wakes, capacity_mah, p):
    """Consecutive full segments after the ignore cut. Returns (used, dropped)
    where dropped lists {index, reason} and used lists the fit rows.
    """
    quiet = (p["quiet_start"], p["quiet_end"])
    seg = datetime.timedelta(hours=p["segment_hours"])
    edge = datetime.timedelta(hours=p["edge_hours"])
    start = polls[0].ts + datetime.timedelta(hours=p["ignore_hours"])
    used, dropped = [], []
    index = 0
    while start + seg <= polls[-1].ts:
        end = start + seg
        first, n_first = _edge_point(polls, start, start + edge, quiet, p["min_polls"])
        last, n_last = _edge_point(polls, end - edge, end + datetime.timedelta(seconds=1),
                                   quiet, p["min_polls"])
        reason = None
        if first is None or last is None:
            reason = ("only %d and %d non-quiet polls in the two %g h end windows; "
                      "at least %d are needed" % (n_first, n_last, p["edge_hours"], p["min_polls"]))
        elif first["mv"] > lt.TREND_CURVE_LIMIT_MV:
            reason = ("starts at %.0f mV, above the %d mV limit of the calibrated curve"
                      % (first["mv"], lt.TREND_CURVE_LIMIT_MV))
        if reason is None:
            charge, hours = _segment_charge(first, last, capacity_mah)
            reason = _segment_row(used, index, first, last, wakes, charge, hours, p)
        if reason:
            dropped.append({"index": index, "reason": reason})
        index += 1
        start = end
    return used, dropped


def _segment_row(used, index, first, last, wakes, charge, hours, p):
    """Append the fit row for a segment or return why it is dropped."""
    counts = dict.fromkeys(CLASSES, 0)
    for w in wakes:
        if first["ts"] <= w["ts"] < last["ts"]:
            counts[w["cls"]] += 1
    total = sum(counts.values())
    if total == 0:
        return "no wakes in the segment"
    unmodelled = counts["unknown"] + counts["deferred"] + counts["failed"]
    if unmodelled / total > p["max_unmodelled_share"]:
        return ("%d of %d wakes are unknown, deferred or failed, above the %g share "
                "the model leaves out" % (unmodelled, total, p["max_unmodelled_share"]))
    if hours <= 0:
        return "the end points are not apart in time"
    if charge <= 0:
        return "no positive voltage fall between the end points"
    modelled = counts["nochange"] + counts["redraw"]
    used.append({
        "index": index, "start": first["ts"].isoformat(), "end": last["ts"].isoformat(),
        "hours": hours, "charge_mah": charge,
        "nochange": counts["nochange"], "redraw": counts["redraw"],
        "unknown": counts["unknown"], "deferred": counts["deferred"],
        "failed": counts["failed"],
        "redraw_share": counts["redraw"] / modelled if modelled else 0.0,
        "first_mv": first["mv"], "last_mv": last["mv"],
    })
    return None


# --- Linear algebra (3 unknowns, by hand) ---------------------------------------


def solve_linear(a, b):
    """Gaussian elimination with partial pivoting; None when singular."""
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-12:
            return None
        m[col], m[piv] = m[piv], m[col]
        for r in range(col + 1, n):
            f = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= f * m[col][c]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = sum(m[i][j] * x[j] for j in range(i + 1, n))
        x[i] = (m[i][n] - s) / m[i][i]
    return x


def invert(a):
    n = len(a)
    cols = []
    for j in range(n):
        col = solve_linear(a, [1.0 if i == j else 0.0 for i in range(n)])
        if col is None:
            return None
        cols.append(col)
    return [[cols[j][i] for j in range(n)] for i in range(n)]


def _jacobi_eigenvalues(a):
    """Eigenvalues of a small symmetric matrix by Jacobi rotations."""
    n = len(a)
    m = [list(r) for r in a]
    for _ in range(60):
        off = max(((abs(m[i][j]), i, j) for i in range(n) for j in range(i + 1, n)))
        if off[0] < 1e-15:
            break
        _, i, j = off
        theta = 0.5 * math.atan2(2 * m[i][j], m[j][j] - m[i][i])
        c, s = math.cos(theta), math.sin(theta)
        for k in range(n):
            mki, mkj = m[k][i], m[k][j]
            m[k][i], m[k][j] = c * mki - s * mkj, s * mki + c * mkj
        for k in range(n):
            mik, mjk = m[i][k], m[j][k]
            m[i][k], m[j][k] = c * mik - s * mjk, s * mik + c * mjk
    return sorted(m[i][i] for i in range(n))


def _design(segments):
    return [[s["hours"], float(s["nochange"]), float(s["redraw"])] for s in segments]


def _column_scales(x):
    scales = []
    for j in range(3):
        norm = math.sqrt(sum(r[j] ** 2 for r in x))
        scales.append(norm if norm > 0 else 1.0)
    return scales


def condition_number(segments):
    """Square root of the eigenvalue ratio of the unit-column-norm normal
    matrix; infinity when the design is singular.
    """
    x = _design(segments)
    scales = _column_scales(x)
    xs = [[r[j] / scales[j] for j in range(3)] for r in x]
    gram = [[sum(r[i] * r[j] for r in xs) for j in range(3)] for i in range(3)]
    lo, _, hi = _jacobi_eigenvalues(gram)
    if lo <= 1e-12 * max(hi, 1e-300):
        return math.inf
    return math.sqrt(hi / lo)


def _ols_subset(xs, y, subset):
    sub = [[r[j] for j in subset] for r in xs]
    gram = [[sum(r[i] * r[j] for r in sub) for j in range(len(subset))]
            for i in range(len(subset))]
    rhs = [sum(r[i] * yv for r, yv in zip(sub, y)) for i in range(len(subset))]
    coef = solve_linear(gram, rhs)
    if coef is None:
        return None
    resid = [yv - sum(c * v for c, v in zip(coef, r)) for r, yv in zip(sub, y)]
    return coef, sum(e * e for e in resid)


def fit_nonnegative(segments):
    """Exact non-negative least squares over the three unknowns: every
    non-empty subset is solved by ordinary least squares with the rest held at
    zero; the feasible solution of least residual wins, ties to fewer
    parameters. Returns (coefficients in original units, residual sum of
    squares) or None.
    """
    x = _design(segments)
    scales = _column_scales(x)
    xs = [[r[j] / scales[j] for j in range(3)] for r in x]
    y = [s["charge_mah"] for s in segments]
    best = None
    for mask in range(1, 8):
        subset = [j for j in range(3) if mask & (1 << j)]
        solved = _ols_subset(xs, y, subset)
        if solved is None or any(c < -1e-12 for c in solved[0]):
            continue
        coef = [0.0, 0.0, 0.0]
        for j, c in zip(subset, solved[0]):
            coef[j] = max(c, 0.0) / scales[j]
        rss = solved[1]
        if best is None or rss < best[1] * (1 - 1e-9) or (
                abs(rss - best[1]) <= 1e-9 * max(best[1], 1e-300)
                and len(subset) < best[2]):
            best = (coef, rss, len(subset))
    if best is None:
        return None
    return best[0], best[1]


def standard_errors(segments):
    """Standard errors of the unconstrained least-squares coefficients, in the
    original units, and the degrees of freedom; None when singular.
    """
    x = _design(segments)
    scales = _column_scales(x)
    xs = [[r[j] / scales[j] for j in range(3)] for r in x]
    y = [s["charge_mah"] for s in segments]
    solved = _ols_subset(xs, y, [0, 1, 2])
    gram = [[sum(r[i] * r[j] for r in xs) for j in range(3)] for i in range(3)]
    inv = invert(gram)
    dof = len(segments) - 3
    if solved is None or inv is None or dof < 1:
        return None
    sigma2 = solved[1] / dof
    return [math.sqrt(max(sigma2 * inv[j][j], 0.0)) / scales[j] for j in range(3)], dof


def t_quantile(dof):
    return T95[dof - 1] if dof <= len(T95) else T95_LARGE


# --- Identifiability and the fit --------------------------------------------------


def _share_spread(segments):
    shares = [s["redraw_share"] for s in segments]
    return max(shares) - min(shares)


def identifiability_reasons(segments, dropped, p):
    """Refusal reasons from the design alone (empty when the design can
    separate the unknowns).
    """
    reasons = []
    if len(segments) < p["min_segments"]:
        extra = ""
        if dropped:
            extra = " (%d dropped: %s)" % (len(dropped), "; ".join(
                "segment %d: %s" % (d["index"], d["reason"]) for d in dropped[:3]))
        reasons.append(
            "only %d usable %g h segment(s), at least %d are needed%s; a longer window "
            "at one interval (at least 14 days) is needed" % (
                len(segments), p["segment_hours"], p["min_segments"], extra))
        return reasons
    spread = _share_spread(segments)
    if spread < p["min_share_spread"]:
        reasons.append(
            "the redraw share barely varies across segments (spread %.3f, at least "
            "%g needed): redraw and no-change wakes are not told apart; a period with a "
            "different redraw share is needed" % (spread, p["min_share_spread"]))
    cond = condition_number(segments)
    if cond > p["max_condition"]:
        reasons.append(
            "the design is ill-conditioned (scaled condition number %s, at most %g allowed): "
            "hours and wake counts are nearly proportional; a window at another check-in "
            "interval, so that hours and wake counts stop being proportional, is needed" % (
                "infinite" if math.isinf(cond) else "%.0f" % cond, p["max_condition"]))
    return reasons


def _interval(point, se, t):
    return {"point": point, "low": max(point - t * se, 0.0), "high": point + t * se}


def fit_segments(segments):
    """Non-negative fit with approximate 95 percent intervals, or None."""
    solved = fit_nonnegative(segments)
    errs = standard_errors(segments)
    if solved is None or errs is None:
        return None
    coef, rss = solved
    se, dof = errs
    t = t_quantile(dof)
    out = {name: _interval(coef[j], se[j], t) for j, name in enumerate(UNKNOWNS)}
    out["residual_mah_rms"] = math.sqrt(rss / len(segments))
    out["degrees_of_freedom"] = dof
    return out


def implied_currents(fit, breakdown):
    """Energy per wake over the device-reported mean awake time, per class."""
    out = {}
    for name, cls in (("nochange_mah", "nochange"), ("redraw_mah", "redraw")):
        ms = breakdown.get(cls, {}).get("mean_ms", {}).get("prev_awake_ms")
        if ms:
            out[cls] = fit[name]["point"] / (ms / 3600000.0)
    return out


def plausibility_reasons(fit, breakdown, p):
    reasons = []
    limits = {"nochange": p["max_nochange_ma"], "redraw": p["max_redraw_ma"]}
    for cls, ma in sorted(implied_currents(fit, breakdown).items()):
        if ma > limits[cls]:
            reasons.append(
                "the implied mean current during awake time for %s wakes is %.0f mA, above "
                "the %g mA limit: the model conflicts with the device-reported timing" % (
                    cls, ma, limits[cls]))
    return reasons


def resolution_reasons(fit):
    r = fit["redraw_mah"]
    if r["point"] <= 0 or r["low"] <= 0:
        return [
            "the redraw wake energy is not resolved above zero (best fit %.4f mAh, 95 "
            "percent range from %.4f to %.4f mAh): more segments, or a period with a "
            "different redraw share, are needed" % (r["point"], r["low"], r["high"])]
    return []


# --- Report ---------------------------------------------------------------------


def _load(raw_text):
    rows, lines, dropped = lt._load_export_rows(raw_text)
    if not lines:
        raise Refusal(["no usable rows in the export"])
    _, polls = lt.parse_battery_lines(lines)
    if len(polls) != len(rows):
        raise Refusal(["rows could not all be timestamped"])
    if any(q.ts.tzinfo is None for q in polls):
        raise Refusal(["row timestamps must carry a timezone offset"])
    for a, b in zip(polls, polls[1:]):
        if b.ts < a.ts:
            raise Refusal(["rows are not in chronological order"])
    return rows, polls, dropped


def build_report(raw, name, capacity_mah, overrides=None):
    """The full report dict for an export (bytes). Never raises for data
    that cannot be fitted: `refused` is true and `reasons` says why.
    """
    p = dict(DEFAULTS)
    p.update(overrides or {})
    report = {
        "inputs": {"export": name, "export_sha256": hashlib.sha256(raw).hexdigest(),
                   "capacity_mah": capacity_mah, "parameters": p},
        "refused": True, "reasons": [], "fit": None,
    }
    try:
        rows, polls, dropped_rows = _load(raw.decode("utf-8", errors="replace"))
    except Refusal as exc:
        report["reasons"] = exc.reasons
        return report
    report["inputs"]["rows"] = len(rows)
    report["inputs"]["rows_dropped"] = dropped_rows
    breakdown = awake_breakdown(rows)
    report["awake_breakdown"] = breakdown
    if not any(_prev_block(r) is not None for r in rows):
        report["reasons"] = [NO_TELEMETRY + ": no row carries a previous-wake record; a "
                             "window from a frame that reports wake telemetry is needed"]
        return report
    wakes = join_wakes(rows, polls)
    counts = dict.fromkeys(CLASSES, 0)
    for w in wakes:
        counts[w["cls"]] += 1
    report["classes"] = counts
    segments, dropped = build_segments(polls, wakes, capacity_mah, p)
    report["segments"] = segments
    report["segments_dropped"] = dropped
    reasons = identifiability_reasons(segments, dropped, p)
    if not reasons:
        fit = fit_segments(segments)
        if fit is None:
            reasons = ["the least-squares problem is singular; more varied segments are needed"]
        else:
            reasons = resolution_reasons(fit) + plausibility_reasons(fit, breakdown, p)
            if not reasons:
                fit["implied_current_ma"] = implied_currents(fit, breakdown)
                report["fit"] = fit
    report["reasons"] = reasons
    report["refused"] = bool(reasons)
    return report


def _round(value):
    if isinstance(value, float):
        if math.isinf(value) or math.isnan(value):
            return None
        return round(value, 6)
    if isinstance(value, dict):
        return {k: _round(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_round(v) for v in value]
    return value


def report_json(report):
    return json.dumps(_round(report), indent=2, sort_keys=True) + "\n"


def _fmt_range(item, unit, digits=4):
    return "%.*f %s (95%% range %.*f to %.*f)" % (
        digits, item["point"], unit, digits, item["low"], digits, item["high"])


def _print_inputs(report, out):
    inp = report["inputs"]
    out("Inputs")
    out("  export: %s (sha256 %s)" % (inp["export"], inp["export_sha256"]))
    out("  rated capacity: %g mAh" % inp["capacity_mah"])
    p = inp["parameters"]
    out("  segments: %g h each, end windows %g h, first %g h ignored" % (
        p["segment_hours"], p["edge_hours"], p["ignore_hours"]))
    out("Assumptions")
    for line in assumptions(p):
        out("  - " + line)


def _print_classes(report, out):
    if "classes" not in report:
        return
    out("Wakes by class (from device-reported fields)")
    for cls in CLASSES:
        out("  %s: %d" % (cls, report["classes"][cls]))
    out("Segments: %d used, %d dropped" % (
        len(report.get("segments", [])), len(report.get("segments_dropped", []))))
    for d in report.get("segments_dropped", []):
        out("  dropped segment %d: %s" % (d["index"], d["reason"]))


def _print_breakdown(report, out):
    out("Device-reported awake time (direct measurement, independent of any fit)")
    breakdown = report.get("awake_breakdown", {})
    if not breakdown:
        out("  none reported")
    for cls, entry in breakdown.items():
        parts = ", ".join("%s %.0f" % (k.replace("prev_", "").replace("_ms", ""), v)
                          for k, v in entry["mean_ms"].items())
        out("  %s (%d wakes), mean ms: %s" % (cls, entry["wakes"], parts or "no timings"))


def _print_fit(report, out):
    fit = report["fit"]
    out("Fitted values")
    s = fit["standing_ma"]
    out("  standing draw: at most %.4f mA (95%% upper bound); best fit %.4f mA, may be zero"
        % (s["high"], s["point"]))
    n = fit["nochange_mah"]
    if n["low"] > 0:
        out("  no-change wake energy: " + _fmt_range(n, "mAh"))
    else:
        out("  no-change wake energy: at most %.4f mAh (95%% upper bound); best fit %.4f mAh"
            % (n["high"], n["point"]))
    out("  redraw wake energy: " + _fmt_range(fit["redraw_mah"], "mAh"))
    out("Residual: %.4f mAh rms over %d segments (%d degrees of freedom)" % (
        fit["residual_mah_rms"], len(report["segments"]), fit["degrees_of_freedom"]))
    for cls, ma in sorted(fit["implied_current_ma"].items()):
        out("  implied mean current during awake time, %s wakes: %.0f mA (energy over "
            "device-reported awake time)" % (cls, ma))


def print_report(report, out=print):
    _print_inputs(report, out)
    _print_classes(report, out)
    if report["refused"]:
        out("REFUSED")
        for reason in report["reasons"]:
            out("  - " + reason)
        out(NO_FIGURE_LINE)
        _print_breakdown(report, out)
    else:
        _print_fit(report, out)
    out(ESTIMATE_SENTENCE)


# --- CLI --------------------------------------------------------------------------


def cmd_fit(args):
    if args.capacity_mah < 1:
        print("--capacity-mah must be at least 1", file=sys.stderr)
        return 1
    try:
        with open(args.export, "rb") as fh:
            raw = fh.read()
    except OSError as exc:
        print("cannot read %s: %s" % (args.export, exc), file=sys.stderr)
        return 1
    try:
        lt.check_trend_quiet_window(args.quiet_start, args.quiet_end)
    except lt.RunReportError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    overrides = {k: getattr(args, k) for k in DEFAULTS}
    report = build_report(raw, os.path.basename(args.export), args.capacity_mah, overrides)
    print_report(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(report_json(report))
    return 2 if report["refused"] else 0


def cmd_selftest(_args):
    script = os.path.abspath(__file__)
    cases = (("wakemodel-synthetic.jsonl", 0), ("wakemodel-collinear.jsonl", 2))
    import subprocess
    ok = True
    for fixture, expected in cases:
        proc = subprocess.run(
            [sys.executable, script, "fit", os.path.join(FIXTURES_DIR, fixture),
             "--capacity-mah", "1000"], capture_output=True, text=True)
        good = proc.returncode == expected
        ok = ok and good
        print("%s %s (exit %d, expected %d)" % (
            "PASS" if good else "FAIL", fixture, proc.returncode, expected))
    return 0 if ok else 1


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    fit = sub.add_parser("fit", help="fit per-wake energy from a battery-history export")
    fit.add_argument("export")
    fit.add_argument("--capacity-mah", type=float, required=True,
                     help="rated pack capacity (a rating, not a measurement)")
    fit.add_argument("--out", help="write the deterministic report JSON here")
    for key, kind in (("ignore_hours", float), ("segment_hours", float),
                      ("edge_hours", float), ("min_polls", int), ("min_segments", int),
                      ("min_share_spread", float), ("max_condition", float),
                      ("max_unmodelled_share", float), ("max_nochange_ma", float),
                      ("max_redraw_ma", float), ("quiet_start", str), ("quiet_end", str)):
        fit.add_argument("--" + key.replace("_", "-"), dest=key, type=kind,
                         default=DEFAULTS[key])
    sub.add_parser("selftest", help="run fit on the committed fixtures")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == "fit":
        return cmd_fit(args)
    return cmd_selftest(args)


if __name__ == "__main__":
    sys.exit(main())
