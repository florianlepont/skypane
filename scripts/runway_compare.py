"""Read-only internal-consistency analysis of an exported runway snapshot.

Reads runway_events.jsonl and poll_cycles.jsonl from a snapshot directory
(see export_snapshot.py) and reports where the recorded history contradicts
itself. It opens no network connection and writes only to --out when given.

Join: a runway_events row is joined to the poll_cycles rows with the same hex
(detected_hex) whose ts lies within JOIN_WINDOW_S seconds of the event ts.

Classes:
  held-carry-over      a poll_cycles row with state_source "held" and no
                       vertical rate whose state equals the state of the last
                       earlier row for a different detected hex: the previous
                       aircraft's state was carried to the new one.
  state-contradiction  a departing event whose joined cycles show a rate at or
                       below DESCEND_THRESHOLD_FPM, or an arriving event whose
                       joined cycles show a rate at or above
                       CLIMB_THRESHOLD_FPM. Events outside the poll_cycles
                       coverage, or with no joined cycle, are counted as
                       not_testable, never as passing.
  stateless            a runway_events row with an empty confirmed_state.
  rotating-route       one callsign with two or more distinct complete
                       (origin, destination) pairs on one UTC day.
  no-route             a callsign seen on at least no_route_min_days distinct
                       days whose every row has an empty origin or
                       destination. not_testable when the data spans fewer
                       days than that.
  flip-flop            one hex recorded as departing and as arriving within
                       FLIP_FLOP_WINDOW_S seconds.
  route-direction-mismatch
                       a row with a complete route that does not fit its state:
                       departing needs origin AIRPORT and a different
                       destination, arriving needs destination AIRPORT and a
                       different origin. Points at a stale or reused-callsign
                       route.

Supplementary (not a class): pending-rate-contradicts-shown-state counts
poll_cycles rows whose detected (pending) aircraft has a vertical rate that
contradicts the state of the aircraft on screen. That is expected while an
aircraft waits in the queue and is reported only to size the effect.

The report's "coverage" field gives the first and last ts and the row count
of each input, so a class that needs poll_cycles is visibly limited to it.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from server.plane.runway_config import (  # noqa: E402
    CLIMB_THRESHOLD_FPM,
    DESCEND_THRESHOLD_FPM,
)

AIRPORT = "ORY"
JOIN_WINDOW_S = 120
FLIP_FLOP_WINDOW_S = 600
NO_ROUTE_MIN_DAYS = 30
EXAMPLE_LIMIT = 20
CLASS_NAMES = (
    "held-carry-over",
    "state-contradiction",
    "stateless",
    "rotating-route",
    "no-route",
    "flip-flop",
    "route-direction-mismatch",
)


def _read_jsonl(path):
    if not os.path.exists(path):
        return []
    rows = []
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _epoch(ts):
    return datetime.fromisoformat(ts).timestamp()


def _coverage(rows):
    stamps = sorted(row["ts"] for row in rows)
    return {
        "rows": len(rows),
        "first": stamps[0] if stamps else None,
        "last": stamps[-1] if stamps else None,
    }


def _result(rows, **extra):
    result = {"count": len(rows), "rows": rows[:EXAMPLE_LIMIT]}
    result.update(extra)
    return result


def _per_day(events):
    days = {}
    for event in events:
        day = event["ts"][:10]
        entry = days.setdefault(day, {"departing": 0, "arriving": 0, "stateless": 0})
        state = event.get("confirmed_state")
        entry[state if state in ("departing", "arriving") else "stateless"] += 1
    return dict(sorted(days.items()))


def _held_carry_over(cycles):
    found = []
    last_for_other = None
    previous = None
    for cycle in sorted(cycles, key=lambda row: row["ts"]):
        hex_ = cycle.get("detected_hex")
        if not hex_:
            continue
        if previous is not None and previous["hex"] != hex_:
            last_for_other = previous
        if (
            cycle.get("state_source") == "held"
            and cycle.get("detected_rate_fpm") is None
            and last_for_other is not None
            and last_for_other["hex"] != hex_
            and cycle.get("confirmed_state")
            and cycle.get("confirmed_state") == last_for_other["state"]
        ):
            found.append(
                {
                    "hex": hex_,
                    "ts": cycle["ts"],
                    "callsign": cycle.get("detected_callsign"),
                    "state": cycle["confirmed_state"],
                    "carried_from_hex": last_for_other["hex"],
                }
            )
        previous = {"hex": hex_, "state": cycle.get("confirmed_state")}
    return _result(found)


def _contradicts(state, rate):
    if rate is None:
        return False
    if state == "departing":
        return rate <= DESCEND_THRESHOLD_FPM
    if state == "arriving":
        return rate >= CLIMB_THRESHOLD_FPM
    return False


def _state_contradiction(events, cycles):
    by_hex = defaultdict(list)
    for cycle in cycles:
        if cycle.get("detected_hex"):
            by_hex[cycle["detected_hex"]].append((_epoch(cycle["ts"]), cycle))
    found = []
    not_testable = 0
    for event in events:
        state = event.get("confirmed_state")
        if state not in ("departing", "arriving"):
            continue
        when = _epoch(event["ts"])
        joined = [
            cycle
            for stamp, cycle in by_hex.get(event["hex"], ())
            if abs(stamp - when) <= JOIN_WINDOW_S
        ]
        if not joined:
            not_testable += 1
            continue
        bad = [c for c in joined if _contradicts(state, c.get("detected_rate_fpm"))]
        if bad:
            found.append(
                {
                    "hex": event["hex"],
                    "ts": event["ts"],
                    "callsign": event.get("callsign"),
                    "state": state,
                    "rate_fpm": bad[0]["detected_rate_fpm"],
                }
            )
    return _result(found, not_testable=not_testable)


def _stateless(events):
    rows = [
        {"hex": e.get("hex"), "ts": e["ts"], "callsign": e.get("callsign")}
        for e in events
        if not e.get("confirmed_state")
    ]
    return _result(rows)


def _rotating_route(events):
    pairs = defaultdict(set)
    first_ts = {}
    for event in events:
        origin, destination = event.get("origin"), event.get("destination")
        callsign = event.get("callsign")
        if not (callsign and origin and destination):
            continue
        key = (callsign, event["ts"][:10])
        pairs[key].add((origin, destination))
        first_ts.setdefault(key, (event["ts"], event.get("hex")))
    rows = [
        {
            "callsign": key[0],
            "day": key[1],
            "ts": first_ts[key][0],
            "hex": first_ts[key][1],
            "routes": sorted("%s-%s" % pair for pair in values),
        }
        for key, values in sorted(pairs.items(), key=lambda item: item[0][1])
        if len(values) > 1
    ]
    return _result(rows)


def _no_route(events, no_route_min_days):
    days = defaultdict(set)
    routed = set()
    first = {}
    for event in events:
        callsign = event.get("callsign")
        if not callsign:
            continue
        days[callsign].add(event["ts"][:10])
        first.setdefault(callsign, event)
        if event.get("origin") and event.get("destination"):
            routed.add(callsign)
    span = len({e["ts"][:10] for e in events})
    if span < no_route_min_days:
        return _result([], not_testable=True, days_in_data=span)
    rows = [
        {
            "callsign": callsign,
            "ts": first[callsign]["ts"],
            "hex": first[callsign].get("hex"),
            "days": len(seen),
        }
        for callsign, seen in sorted(days.items())
        if callsign not in routed and len(seen) >= no_route_min_days
    ]
    return _result(rows, not_testable=False, days_in_data=span)


def _flip_flop(events):
    by_hex = defaultdict(list)
    for event in events:
        if event.get("confirmed_state") in ("departing", "arriving"):
            by_hex[event["hex"]].append((_epoch(event["ts"]), event))
    found = []
    for hex_, items in by_hex.items():
        items.sort(key=lambda item: item[0])
        for (t1, e1), (t2, e2) in zip(items, items[1:]):
            if e1["confirmed_state"] != e2["confirmed_state"] and (
                t2 - t1 <= FLIP_FLOP_WINDOW_S
            ):
                found.append(
                    {
                        "hex": hex_,
                        "ts": e1["ts"],
                        "callsign": e1.get("callsign"),
                        "states": [e1["confirmed_state"], e2["confirmed_state"]],
                        "second_ts": e2["ts"],
                    }
                )
                break
    found.sort(key=lambda row: row["ts"])
    return _result(found)


def _route_fits(event):
    origin, destination = event.get("origin"), event.get("destination")
    if not (origin and destination):
        return True
    state = event.get("confirmed_state")
    if state == "departing":
        return origin == AIRPORT and destination != AIRPORT
    if state == "arriving":
        return destination == AIRPORT and origin != AIRPORT
    return True


def _route_direction_mismatch(events):
    rows = [
        {
            "hex": e.get("hex"),
            "ts": e["ts"],
            "callsign": e.get("callsign"),
            "state": e["confirmed_state"],
            "route": "%s-%s" % (e["origin"], e["destination"]),
            "route_source": e.get("route_source"),
        }
        for e in events
        if not _route_fits(e)
    ]
    return _result(rows)


def _pending_contradiction(cycles):
    rows = [
        {
            "hex": c["detected_hex"],
            "ts": c["ts"],
            "callsign": c.get("detected_callsign"),
            "state": c.get("confirmed_state"),
            "rate_fpm": c["detected_rate_fpm"],
        }
        for c in sorted(cycles, key=lambda row: row["ts"])
        if c.get("detected_hex")
        and c.get("detected_hex") != c.get("shown_hex")
        and _contradicts(c.get("confirmed_state"), c.get("detected_rate_fpm"))
    ]
    return _result(rows)


def analyse(data_dir, no_route_min_days=NO_ROUTE_MIN_DAYS):
    """Return the JSON-serialisable report for the snapshot in data_dir."""
    events = _read_jsonl(os.path.join(data_dir, "runway_events.jsonl"))
    cycles = _read_jsonl(os.path.join(data_dir, "poll_cycles.jsonl"))
    events.sort(key=lambda row: row["ts"])
    classes = {
        "held-carry-over": _held_carry_over(cycles),
        "state-contradiction": _state_contradiction(events, cycles),
        "stateless": _stateless(events),
        "rotating-route": _rotating_route(events),
        "no-route": _no_route(events, no_route_min_days),
        "flip-flop": _flip_flop(events),
        "route-direction-mismatch": _route_direction_mismatch(events),
    }
    return {
        "coverage": {
            "runway_events": _coverage(events),
            "poll_cycles": _coverage(cycles),
        },
        "per_day": _per_day(events),
        "classes": classes,
        "supplementary": {
            "pending-rate-contradicts-shown-state": _pending_contradiction(cycles)
        },
    }


def format_table(report):
    lines = ["day         departing arriving stateless"]
    for day, entry in report["per_day"].items():
        lines.append(
            "%s %9d %8d %9d"
            % (day, entry["departing"], entry["arriving"], entry["stateless"])
        )
    lines.append("")
    for name in CLASS_NAMES:
        entry = report["classes"][name]
        note = ""
        if entry.get("not_testable") is True:
            note = " (not testable: too few days)"
        elif entry.get("not_testable"):
            note = " (%d events not testable)" % entry["not_testable"]
        lines.append("%-20s %d%s" % (name, entry["count"], note))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("data_dir")
    parser.add_argument("--out", help="write the JSON report here")
    parser.add_argument("--no-route-min-days", type=int, default=NO_ROUTE_MIN_DAYS)
    args = parser.parse_args(argv)
    report = analyse(args.data_dir, args.no_route_min_days)
    text = json.dumps(report, indent=2, sort_keys=True)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
    else:
        print(text)
    print(format_table(report), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
