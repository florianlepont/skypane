#!/usr/bin/env python3
"""Turn a sample_window.py run's JSONL files into the viability metrics the
D-02 RTL-SDR-fallback decision is made on.

Stdlib-only. Reads every *.jsonl file in --dir, groups records by the
"provider" field each record already carries (not by filename), and prints
a markdown report: per-provider counts, distinct-aircraft/on-ground/update-gap
metrics, the two-provider overlap, and an explicit PASS/FAIL verdict against
a threshold that is fixed here - before any real data is read - so the
decision this feeds is a reading of a pre-committed test, not a post-hoc
rationalisation (see 01-CONTEXT.md D-01 through D-04, and T-01-04-04 in
01-04-PLAN.md's threat register).

Usage:
    python3 analyze_samples.py --dir /path/to/samples-from-one-run
"""

import argparse
import glob
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# Viability threshold - fixed before the real 90-minute window was sampled.
MIN_DISTINCT_BELOW_CEILING = 6
MIN_DISTINCT_ON_GROUND = 1
MAX_MEDIAN_UPDATE_GAP_S = 15.0

# "Position-update gap" is measured from each aggregator's own `seen_pos`
# field (seconds since the underlying feed last received a real position
# report for that aircraft), not from this project's own polling interval -
# sample_window.py's --interval (default 30s) would otherwise put a floor
# on every measured gap well above the 15s threshold, making the metric
# meaningless. Reconstructed update timestamps (sample_timestamp - seen_pos)
# that land within this many seconds of each other are treated as the same
# underlying message, since repeated polls between two real updates all
# report the same (or near-identical, modulo request-timing jitter) seen_pos
# origin.
UPDATE_DEDUP_EPSILON_S = 1.0


def load_records(directory):
    records = []
    skipped = 0
    for path in sorted(glob.glob(os.path.join(directory, "*.jsonl"))):
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    skipped += 1  # a corrupt line must not kill the whole analysis
    return records, skipped


def group_by_provider(records):
    by_provider = defaultdict(list)
    for r in records:
        by_provider[r.get("provider", "unknown")].append(r)
    return by_provider


def parse_ts(ts):
    # sample_window.py writes datetime.now(timezone.utc).isoformat(), which
    # Python 3.9's datetime.fromisoformat() parses natively (no "Z" suffix
    # to special-case).
    return datetime.fromisoformat(ts)


def median(values):
    values = sorted(values)
    n = len(values)
    if n == 0:
        return None
    mid = n // 2
    if n % 2 == 1:
        return values[mid]
    return (values[mid - 1] + values[mid]) / 2.0


def dedup_update_times(update_times):
    """Collapse reconstructed update timestamps that land within
    UPDATE_DEDUP_EPSILON_S of each other into one representative time -
    repeated polls between two real ADS-B messages all reconstruct to
    (approximately) the same underlying message time.
    """
    ordered = sorted(update_times)
    deduped = []
    for t in ordered:
        if not deduped or (t - deduped[-1]).total_seconds() > UPDATE_DEDUP_EPSILON_S:
            deduped.append(t)
    return deduped


def compute_metrics(provider_records):
    samples = len(provider_records)
    ok_records = [r for r in provider_records if "error" not in r]
    errors = samples - len(ok_records)

    distinct_hex = set()
    distinct_hex_below_ceiling = set()
    distinct_hex_on_ground = set()
    lowest_altitude_ft = None
    hex_sample_count = defaultdict(int)  # our own poll count per hex - picks the "best-tracked" aircraft
    hex_update_times = defaultdict(list)  # reconstructed real message-arrival times per hex

    for r in ok_records:
        ts = r.get("timestamp")
        parsed_ts = parse_ts(ts) if ts else None
        for ac in r.get("in_bbox", []):
            h = ac.get("hex")
            if not h:
                continue
            distinct_hex.add(h)
            hex_sample_count[h] += 1
            if ac.get("below_ceiling"):
                distinct_hex_below_ceiling.add(h)
            if ac.get("on_ground"):
                distinct_hex_on_ground.add(h)
            altitude = ac.get("altitude")
            if isinstance(altitude, (int, float)):
                if lowest_altitude_ft is None or altitude < lowest_altitude_ft:
                    lowest_altitude_ft = altitude

            seen_pos = ac.get("seen_pos")
            if parsed_ts is not None and isinstance(seen_pos, (int, float)):
                hex_update_times[h].append(parsed_ts - timedelta(seconds=seen_pos))

    best_hex = None
    best_count = 0
    for h, count in hex_sample_count.items():
        if count > best_count:
            best_count = count
            best_hex = h

    median_gap_s = None
    max_gap_s = None
    update_count = 0
    if best_hex:
        deduped = dedup_update_times(hex_update_times.get(best_hex, []))
        update_count = len(deduped)
        if update_count >= 2:
            gaps = [(deduped[i + 1] - deduped[i]).total_seconds() for i in range(update_count - 1)]
            median_gap_s = median(gaps)
            max_gap_s = max(gaps)

    return {
        "samples": samples,
        "errors": errors,
        "distinct_hex_in_bbox": distinct_hex,
        "distinct_hex_below_ceiling": len(distinct_hex_below_ceiling),
        "distinct_hex_on_ground": len(distinct_hex_on_ground),
        "best_tracked_hex": best_hex,
        "best_tracked_sample_count": best_count,
        "best_tracked_update_count": update_count,
        "median_update_gap_s": median_gap_s,
        "max_update_gap_s": max_gap_s,
        "lowest_altitude_ft": lowest_altitude_ft,
    }


def verdict_for(metrics):
    below_ceiling_pass = metrics["distinct_hex_below_ceiling"] >= MIN_DISTINCT_BELOW_CEILING
    on_ground_pass = metrics["distinct_hex_on_ground"] >= MIN_DISTINCT_ON_GROUND
    gap_pass = metrics["median_update_gap_s"] is not None and metrics["median_update_gap_s"] <= MAX_MEDIAN_UPDATE_GAP_S
    overall = below_ceiling_pass and on_ground_pass and gap_pass
    return {
        "below_ceiling_pass": below_ceiling_pass,
        "on_ground_pass": on_ground_pass,
        "gap_pass": gap_pass,
        "overall": overall,
    }


def fmt_pass(ok):
    return "PASS" if ok else "FAIL"


def fmt_num(value, suffix=""):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return "%.1f%s" % (value, suffix)
    return "%s%s" % (value, suffix)


def render_report(by_provider, all_metrics, skipped_lines):
    lines = []
    lines.append("## Per-Provider Metrics")
    lines.append("")
    if skipped_lines:
        lines.append("_(%d corrupt JSONL line(s) skipped during analysis)_" % skipped_lines)
        lines.append("")
    lines.append(
        "| Provider | Samples | Errors | Distinct hex in bbox | Distinct hex <=3000ft | "
        "Distinct hex on-ground | Best-tracked hex | Poll samples | Reconstructed updates | "
        "Median update gap (s) | Max update gap (s) | Lowest altitude (ft) |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|---|---|---|")
    for name, metrics in all_metrics.items():
        lines.append(
            "| %s | %d | %d | %d | %d | %d | %s | %d | %d | %s | %s | %s |"
            % (
                name,
                metrics["samples"],
                metrics["errors"],
                len(metrics["distinct_hex_in_bbox"]),
                metrics["distinct_hex_below_ceiling"],
                metrics["distinct_hex_on_ground"],
                metrics["best_tracked_hex"] or "n/a",
                metrics["best_tracked_sample_count"],
                metrics["best_tracked_update_count"],
                fmt_num(metrics["median_update_gap_s"], "s"),
                fmt_num(metrics["max_update_gap_s"], "s"),
                fmt_num(metrics["lowest_altitude_ft"], "ft"),
            )
        )

    lines.append("")
    lines.append("## Viability Verdict")
    lines.append("")
    lines.append(
        "Threshold (fixed before sampling): >=%d distinct aircraft at/below the altitude ceiling, "
        ">=%d distinct on-ground aircraft, median position-update gap <=%ss for the best-tracked aircraft."
        % (MIN_DISTINCT_BELOW_CEILING, MIN_DISTINCT_ON_GROUND, fmt_num(MAX_MEDIAN_UPDATE_GAP_S))
    )
    lines.append(
        "Update gaps are reconstructed from each provider's own `seen_pos` field "
        "(seconds since the underlying feed last received a real position report), "
        "not from this sampler's own polling interval - otherwise the gap floor would "
        "just be whatever --interval was set to, which measures nothing about the feed."
    )
    lines.append("")
    for name, metrics in all_metrics.items():
        v = verdict_for(metrics)
        lines.append("### %s" % name)
        lines.append(
            "- distinct aircraft <=3000ft: %d (threshold %d) -> %s"
            % (metrics["distinct_hex_below_ceiling"], MIN_DISTINCT_BELOW_CEILING, fmt_pass(v["below_ceiling_pass"]))
        )
        lines.append(
            "- distinct on-ground aircraft: %d (threshold %d) -> %s"
            % (metrics["distinct_hex_on_ground"], MIN_DISTINCT_ON_GROUND, fmt_pass(v["on_ground_pass"]))
        )
        lines.append(
            "- median position-update gap for best-tracked aircraft (%s, %d poll samples, "
            "%d reconstructed updates): %s (threshold <=%ss) -> %s"
            % (
                metrics["best_tracked_hex"] or "n/a",
                metrics["best_tracked_sample_count"],
                metrics["best_tracked_update_count"],
                fmt_num(metrics["median_update_gap_s"], "s"),
                fmt_num(MAX_MEDIAN_UPDATE_GAP_S),
                fmt_pass(v["gap_pass"]),
            )
        )
        lines.append("- **Overall: %s**" % fmt_pass(v["overall"]))
        lines.append("")

    provider_names = list(all_metrics.keys())
    if len(provider_names) == 2:
        a, b = provider_names
        set_a = all_metrics[a]["distinct_hex_in_bbox"]
        set_b = all_metrics[b]["distinct_hex_in_bbox"]
        both = set_a & set_b
        only_a = set_a - set_b
        only_b = set_b - set_a
        lines.append("### Overlap")
        lines.append("- Seen by both %s and %s: %d hex" % (a, b, len(both)))
        lines.append("- Seen only by %s: %d hex" % (a, len(only_a)))
        lines.append("- Seen only by %s: %d hex" % (b, len(only_b)))
        lines.append("")

    return "\n".join(lines)


def build_parser():
    parser = argparse.ArgumentParser(description="Analyse a sample_window.py run's JSONL output.")
    parser.add_argument("--dir", required=True, help="Directory containing one run's *.jsonl files.")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    records, skipped = load_records(args.dir)
    by_provider = group_by_provider(records)
    all_metrics = {name: compute_metrics(recs) for name, recs in sorted(by_provider.items())}
    print(render_report(by_provider, all_metrics, skipped))
    return 0


if __name__ == "__main__":
    sys.exit(main())
