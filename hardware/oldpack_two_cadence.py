#!/usr/bin/env python3
"""Compare the old-pack battery test at two wake intervals.

Reads the `device_health` export of the test (JSON Lines) and run one's
voltage log, and prints for each cadence segment the fall in millivolts and
two rough current estimates: one from the discharge curve in
`server/device_policy.py`, one by equivalent time on run one's own voltage
trace (curve-free). Both are rough: the capacity (3000 mAh) and the curve are
ratings, and run one's readings near the top are noisy.

    python3 hardware/oldpack_two_cadence.py EXPORT.jsonl RUN1.log

The segment boundaries are the owner's test log: the 900 s segment starts at
the first reading at or below 3999 mV and ends when the gaps become about
3600 s; the 3600 s segment starts three hours later and ends at the last
reading. Quiet-hours polls (23:30 to 06:00 Paris) are left out of the medians.
"""
import datetime as dt
import importlib.util
import json
import os
import re
import statistics
import sys
import zoneinfo

HERE = os.path.dirname(os.path.abspath(__file__))
PARIS = zoneinfo.ZoneInfo("Europe/Paris")
UTC = dt.timezone.utc
CAPACITY_MAH = 3000
EDGE_HOURS = 12
SWITCH_NOT_BEFORE = dt.datetime(2026, 10, 31, 11, 0, tzinfo=UTC)
RUN1_FULL_FRACTION_TO_PARK = 0.94


def _load_curve():
    path = os.path.join(HERE, "..", "server", "device_policy.py")
    spec = importlib.util.spec_from_file_location("device_policy", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.battery_fraction


def _read_export(path):
    points = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("battery_mv"):
                points.append((dt.datetime.fromisoformat(row["ts"]), row["battery_mv"]))
    return points


def _is_quiet(moment):
    local = moment.astimezone(PARIS)
    hour = local.hour + local.minute / 60
    return hour >= 23.5 or hour < 6


def _median_window(points, start, end):
    kept = [(t, mv) for t, mv in points if start <= t < end and not _is_quiet(t)]
    middle = kept[len(kept) // 2][0]
    return statistics.median(mv for _, mv in kept), middle, len(kept)


def _segment(points, label, start, end, battery_fraction):
    edge = dt.timedelta(hours=EDGE_HOURS)
    first = _median_window(points, start, start + edge)
    last = _median_window(points, end - edge, end)
    hours = (last[1] - first[1]).total_seconds() / 3600
    fall = first[0] - last[0]
    charge = (battery_fraction(first[0]) - battery_fraction(last[0])) * CAPACITY_MAH
    print(f"{label}: start median {first[0]:.0f} mV ({first[2]} polls) -> end median "
          f"{last[0]:.0f} mV ({last[2]} polls); {hours:.1f} h; fall {fall:.0f} mV = "
          f"{fall / hours:.3f} mV/h; curve-based {charge / hours:.2f} mA")
    return first[0], last[0], hours


def _read_run_one(path):
    readings = []
    pattern = re.compile(r"\[([^\]]+)\].*X-Battery-Mv=(\d+)")
    with open(path, encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            match = pattern.match(line)
            if match:
                readings.append((dt.datetime.fromisoformat(match.group(1)), int(match.group(2))))
    return readings


class RunOne:
    """Run one's median-of-9 voltage trace, counted from its first reading
    below 4060 mV (the start of the discharge)."""

    def __init__(self, readings):
        self.readings = readings
        self.volts = [mv for _, mv in readings]
        self.start = next(i for i, mv in enumerate(self.volts) if mv < 4060)
        self.origin = readings[self.start][0]

    def _smooth(self, index):
        return statistics.median(self.volts[max(0, index - 4):index + 5])

    def _hours(self, index):
        return (self.readings[index][0] - self.origin).total_seconds() / 3600

    def first_crossing(self, threshold):
        for index in range(self.start, len(self.readings) - 9):
            if self._smooth(index) <= threshold:
                return self._hours(index)
        return None

    def sustained_crossing(self, threshold):
        last = self.start
        for index in range(self.start, len(self.readings) - 9):
            if self._smooth(index) > threshold:
                last = index
        return self._hours(last + 1)


def main(argv):
    export_path, run_one_path = argv
    battery_fraction = _load_curve()
    points = _read_export(export_path)
    gaps = [(points[i][0], (points[i + 1][0] - points[i][0]).total_seconds())
            for i in range(len(points) - 1)]
    switch = next(t for t, gap in gaps if t >= SWITCH_NOT_BEFORE and 3500 < gap < 3700)
    below = next(t for t, mv in points if mv <= 3999)
    print(f"first reading at or below 3999 mV: {below.isoformat()}")
    print(f"first gap of about 3600 s starts: {switch.isoformat()}")
    print(f"last reading: {points[-1][0].isoformat()} {points[-1][1]} mV")
    segments = (
        ("900 s", _segment(points, "900 s segment", below, switch, battery_fraction)),
        ("3600 s", _segment(points, "3600 s segment", switch + dt.timedelta(hours=3),
                            points[-1][0], battery_fraction)),
    )
    run_one = RunOne(_read_run_one(run_one_path))
    to_park = run_one.first_crossing(3300)
    mean_ma = CAPACITY_MAH * RUN1_FULL_FRACTION_TO_PARK / to_park
    print(f"run one: first median-9 crossing of 3300 mV at {to_park:.1f} h, "
          f"mean {mean_ma:.1f} mA (3000 mAh x {RUN1_FULL_FRACTION_TO_PARK})")
    for label, (start_mv, end_mv, hours) in segments:
        for name, crossing in (("first", run_one.first_crossing),
                               ("sustained", run_one.sustained_crossing)):
            equivalent = crossing(end_mv) - crossing(start_mv)
            print(f"  {label}: run-one {name}-crossing time between {start_mv:.0f} and "
                  f"{end_mv:.0f} mV = {equivalent:.1f} h vs {hours:.1f} h in the test -> "
                  f"ratio {equivalent / hours:.2f} -> ~{mean_ma * equivalent / hours:.1f} mA")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1:]))
