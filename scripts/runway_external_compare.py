#!/usr/bin/env python3
"""scripts/runway_external_compare.py -- compares recorded runway events with
an independent reference file (flight-tracking history or airport timetable).

Stdlib only. The tool never fetches anything: it reads the snapshot's
runway_events.jsonl and a reference JSON Lines file. Reference row fields:
callsign (or flight), ts (UTC ISO 8601), direction (departing/arriving),
runway, hex (optional), origin/destination (optional), source (host name).

Verdicts per sampled event: match, direction-mismatch, route-mismatch,
unverifiable-no-reference. Reference rows on the tracked runway without any
recorded event are reported separately as missed-aircraft.
"""
import argparse
import collections
import datetime
import json
import random
import sys

EVENT_GAP_MIN = 30
DEFAULT_SAMPLE = 150
DEFAULT_WINDOW_MIN = 15
DEFAULT_SEED = 65
TRACKED_RUNWAY = "3"
LOW_COST_MARKERS = ("transavia", "easyjet", "ryanair", "volotea", "vueling",
                    "wizz", "norwegian", "jet2", "binter", "level", "eurowings")
DIRECTIONS = {"departing": "departing", "arriving": "arriving",
              "departure": "departing", "arrival": "arriving",
              "dep": "departing", "arr": "arriving"}


def parse_ts(value):
    """Parses an ISO 8601 timestamp to an aware UTC datetime."""
    stamp = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=datetime.timezone.utc)
    return stamp


def airline_family(airline):
    """low-cost when the airline name has a known low-cost marker, else legacy."""
    name = (airline or "").lower()
    return "low-cost" if any(m in name for m in LOW_COST_MARKERS) else "legacy"


def hour_band(ts):
    """Four UTC bands of six hours."""
    return parse_ts(ts).hour // 6


def build_events(rows):
    """Collapses repeated rows of one flight (same hex and state, gaps under
    EVENT_GAP_MIN) into a single event carrying the first row."""
    events = []
    last = {}
    for row in sorted(rows, key=lambda r: r["ts"]):
        key = (row.get("hex"), row.get("confirmed_state"))
        stamp = parse_ts(row["ts"])
        prev = last.get(key)
        if prev is None or (stamp - prev).total_seconds() > EVENT_GAP_MIN * 60:
            events.append(dict(row))
        last[key] = stamp
    return events


def _stratum(event):
    return (event["ts"][:10], event.get("confirmed_state"),
            hour_band(event["ts"]), airline_family(event.get("airline")))


def stratified_sample(events, size, seed=DEFAULT_SEED):
    """Seeded sample over day, state, hour band and airline family. One event
    per day is taken first so every day is covered, then strata are drawn
    round-robin."""
    rng = random.Random(seed)
    ordered = sorted(events, key=lambda e: (e["ts"], e.get("hex") or ""))
    by_day = collections.defaultdict(list)
    for event in ordered:
        by_day[event["ts"][:10]].append(event)
    chosen = []
    chosen_ids = set()
    for day in sorted(by_day):
        pick = rng.choice(by_day[day])
        chosen.append(pick)
        chosen_ids.add(id(pick))
    strata = collections.defaultdict(list)
    for event in ordered:
        if id(event) not in chosen_ids:
            strata[_stratum(event)].append(event)
    for bucket in strata.values():
        rng.shuffle(bucket)
    keys = sorted(strata)
    rng.shuffle(keys)
    while len(chosen) < size and any(strata[k] for k in keys):
        for key in keys:
            if strata[key] and len(chosen) < size:
                chosen.append(strata[key].pop())
    return sorted(chosen[:max(size, 0)] if size < len(chosen) else chosen,
                  key=lambda e: e["ts"])


def _norm_call(value):
    return (value or "").replace(" ", "").upper()


def _norm_dir(value):
    return DIRECTIONS.get((value or "").strip().lower(), (value or "").lower())


def _same_aircraft(event, ref):
    ref_hex = (ref.get("hex") or "").lower()
    if ref_hex and ref_hex == (event.get("hex") or "").lower():
        return True
    ref_call = _norm_call(ref.get("callsign") or ref.get("flight"))
    return bool(ref_call) and ref_call == _norm_call(event.get("callsign"))


def _minutes(a, b):
    return abs((parse_ts(a) - parse_ts(b)).total_seconds()) / 60.0


def _route_differs(event, ref):
    for field in ("origin", "destination"):
        want = (ref.get(field) or "").upper()
        got = (event.get(field) or "").upper()
        if want and got and want != got:
            return True
    return False


def _on_tracked_runway(ref):
    runway = str(ref.get("runway") or "").strip()
    return runway in ("", TRACKED_RUNWAY, "03", "3L", "3R")


def classify(sample, refs, all_events, window_min=DEFAULT_WINDOW_MIN):
    """Returns {"verdicts": [...], "missed": [...], "totals": {...}}."""
    refs = [r for r in refs if _on_tracked_runway(r)]
    verdicts = []
    for event in sample:
        near = [r for r in refs if _same_aircraft(event, r)
                and _minutes(event["ts"], r["ts"]) <= window_min]
        item = {"ts": event["ts"], "hex": event.get("hex"),
                "callsign": event.get("callsign"),
                "state": event.get("confirmed_state"),
                "route": f"{event.get('origin')}-{event.get('destination')}"}
        if not near:
            item["verdict"] = "unverifiable-no-reference"
            item["reason"] = "no reference row for this aircraft inside the window"
        else:
            same_dir = [r for r in near
                        if _norm_dir(r.get("direction")) == event.get("confirmed_state")]
            if not same_dir:
                ref = near[0]
                item["verdict"] = "direction-mismatch"
                item["reference_direction"] = _norm_dir(ref.get("direction"))
                item["source"] = ref.get("source")
            elif _route_differs(event, same_dir[0]):
                ref = same_dir[0]
                item["verdict"] = "route-mismatch"
                item["reference_route"] = f"{ref.get('origin')}-{ref.get('destination')}"
                item["source"] = ref.get("source")
            else:
                item["verdict"] = "match"
                item["source"] = same_dir[0].get("source")
        verdicts.append(item)
    days = {e["ts"][:10] for e in all_events}
    missed = []
    for ref in refs:
        if ref["ts"][:10] not in days:
            continue
        if not any(_same_aircraft(e, ref) and _minutes(e["ts"], ref["ts"]) <= window_min
                   for e in all_events):
            missed.append({"ts": ref["ts"], "callsign": ref.get("callsign") or ref.get("flight"),
                           "hex": ref.get("hex"), "direction": _norm_dir(ref.get("direction")),
                           "source": ref.get("source")})
    totals = collections.Counter(v["verdict"] for v in verdicts)
    totals["missed-aircraft"] = len(missed)
    return {"verdicts": verdicts, "missed": missed, "totals": dict(totals)}


def _read_jsonl(path):
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", required=True, help="runway_events.jsonl")
    parser.add_argument("--reference", action="append", default=[],
                        help="reference JSONL (repeatable)")
    parser.add_argument("--sample-out", help="write the sample as JSONL here")
    parser.add_argument("--sample-size", type=int, default=DEFAULT_SAMPLE)
    parser.add_argument("--window-min", type=float, default=DEFAULT_WINDOW_MIN)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--json-out", help="write verdicts as JSON here")
    args = parser.parse_args(argv)
    events = build_events(_read_jsonl(args.events))
    sample = stratified_sample(events, args.sample_size, args.seed)
    if args.sample_out:
        with open(args.sample_out, "w", encoding="utf-8") as handle:
            for event in sample:
                handle.write(json.dumps({k: event.get(k) for k in (
                    "ts", "hex", "callsign", "confirmed_state", "origin",
                    "destination", "airline")}) + "\n")
    print(f"events={len(events)} sample={len(sample)} seed={args.seed} "
          f"window_min={args.window_min}")
    if not args.reference:
        return 0
    refs = [r for path in args.reference for r in _read_jsonl(path)]
    out = classify(sample, refs, events, args.window_min)
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as handle:
            json.dump(out, handle, indent=1)
    print("| verdict | count |\n|---|---|")
    for name, count in sorted(out["totals"].items()):
        print(f"| {name} | {count} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
