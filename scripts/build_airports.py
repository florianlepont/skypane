#!/usr/bin/env python3
"""Build the France runway catalogue from a committed OurAirports subset.

Default mode is offline and deterministic: it reads only the two committed
subset CSV files (and their sha256 pin in ourairports-source.json) and
writes server/data/airports_fr.json plus the exclusion report that lists
every runway row that did not make it into the catalogue.

`--refresh DIR` is the only mode that sees a full OurAirports dump. DIR is a
directory the caller filled with airports.csv and runways.csv; this script
never downloads anything. It writes the filtered subset and the source pin.
The dump is third-party data: run it as `python3 -I` on a copy that lives
outside the repository, and never from inside the data directory.

Usage:
    python3 scripts/build_airports.py
    python3 -I scripts/build_airports.py --refresh DIR --snapshot-date DATE
"""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(HERE, "data")
CATALOGUE_PATH = os.path.join(REPO_ROOT, "server", "data", "airports_fr.json")
EXCLUSIONS_NAME = "ourairports-exclusions.json"
SOURCE_NAME = "ourairports-source.json"
AIRPORTS_SUBSET = "ourairports-fr-airports.csv"
RUNWAYS_SUBSET = "ourairports-fr-runways.csv"

MAX_CSV_BYTES = 20 * 1024 * 1024

BASE_URL = "https://davidmegginson.github.io/ourairports-data/"
LICENCE = (
    "All data is released to the Public Domain, and comes with no guarantee "
    "of accuracy or fitness for use."
)
DATA_DICTIONARY = "https://ourairports.com/help/data-dictionary.html"

# Territories whose airports belong in the catalogue. Overseas airports sit
# under their own iso_country, so metropolitan "FR" alone is not enough.
TERRITORIES = frozenset(
    ["FR", "GF", "GP", "MQ", "RE", "YT", "PM", "BL", "MF", "PF", "NC", "WF", "TF"]
)
# Airports with an LF ident but a different country (for example CN).
FOREIGN_LF_COUNTRIES = frozenset(["CN"])

IDENT_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{2}$")
DESIGNATOR_RE = re.compile(r"^(0[1-9]|[12]\d|3[0-6])([LRC]?)$")
KEPT_AIRPORT_TYPES = frozenset(["small_airport", "medium_airport", "large_airport"])

SURFACES = {
    "ASP": "asphalt", "ASPH": "asphalt", "ASPHALT": "asphalt",
    "CON": "concrete", "CONC": "concrete", "CONCRETE": "concrete",
    "GRASS": "grass", "GRS": "grass", "TURF": "grass",
    "GRVL": "gravel", "GRAVEL": "gravel",
}

COORD_DECIMALS = 6
# Same flat-earth constant detect.runway_axis uses, so corridor geometry
# computed here agrees with the runtime gates.
M_PER_DEG_LAT = 111320.0
M_PER_NM = 1852.0

# Bearing computed from the thresholds may differ from the designator by
# this much before the row is considered wrongly surveyed and dropped.
MAX_DESIGNATOR_DEVIATION_DEG = 20.0
HEADING_WARN_DEG = 10.0
MIN_LENGTH_M = 100.0

# Two runways count as parallel neighbours when their axes differ by at
# most this many degrees. Orly runways 06/24 and 07/25 deviate 12.6 degrees:
# a threshold of 15 degrees or more would pull the gap of that crossing-
# approach pair into the rule and shrink Orly runway 07/25 below 500 m.
PARALLEL_AXIS_DEG = 5.0

DEFAULT_HALF_WIDTH_M = 500.0
# A corridor narrower than this cannot separate runways by position, and a
# value of 0 would be silently replaced by the default at run time.
MIN_HALF_WIDTH_M = 50.0
EXTENSION_M = 2500.0
GROUND_HALF_WIDTH_M = 75.0
# Every corridor corner must stay inside the polling zone around the
# airport reference point.
ZONE_RADIUS_NM = 5.0


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def read_csv(path):
    """Rows of a CSV file as dicts; refuses files above the size cap."""
    if os.path.getsize(path) > MAX_CSV_BYTES:
        raise ValueError("%s is larger than %d bytes" % (path, MAX_CSV_BYTES))
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def parse_coord(text, limit):
    """A coordinate rounded to 6 decimals, or None when the cell is empty.

    Raises ValueError for text that is not a finite number within +-limit.
    The dump stores float32 noise, so rounding comes before any maths.
    """
    text = (text or "").strip()
    if not text:
        return None
    value = float(text)
    if not math.isfinite(value) or abs(value) > limit:
        raise ValueError("coordinate out of range: %r" % text)
    return round(value, COORD_DECIMALS)


def parse_optional_float(text):
    text = (text or "").strip()
    if not text:
        return None
    value = float(text)
    return value if math.isfinite(value) else None


def designator_number(ident):
    match = DESIGNATOR_RE.match((ident or "").strip())
    return int(match.group(1)) if match else None


def angle_diff(first, second):
    """Smallest absolute difference between two bearings, in degrees."""
    return abs((first - second + 180.0) % 360.0 - 180.0)


def local_xy(lat, lon, ref_lat, ref_lon):
    """Local metres east and north of the reference, flat-earth."""
    scale = M_PER_DEG_LAT * math.cos(math.radians(ref_lat))
    return (lon - ref_lon) * scale, (lat - ref_lat) * M_PER_DEG_LAT


def local_delta(start, end):
    """Metres east and north from start to end, scaled at the mid latitude."""
    scale = M_PER_DEG_LAT * math.cos(math.radians((start[0] + end[0]) / 2.0))
    return (end[1] - start[1]) * scale, (end[0] - start[0]) * M_PER_DEG_LAT


def local_bearing(start, end):
    """True bearing in degrees from start to end, in the runtime's frame."""
    dx, dy = local_delta(start, end)
    return math.degrees(math.atan2(dx, dy)) % 360.0


def local_length(start, end):
    return math.hypot(*local_delta(start, end))


def initial_bearing(start, end):
    """Great-circle initial true bearing from start to end, in degrees."""
    lat0, lat1 = math.radians(start[0]), math.radians(end[0])
    dlon = math.radians(end[1] - start[1])
    y = math.sin(dlon) * math.cos(lat1)
    x = math.cos(lat0) * math.sin(lat1) - math.sin(lat0) * math.cos(lat1) * math.cos(dlon)
    return math.degrees(math.atan2(y, x)) % 360.0


def in_territory(airport):
    country = airport.get("iso_country", "")
    if country in TERRITORIES:
        return True
    return airport.get("ident", "").startswith("LF") and country not in FOREIGN_LF_COUNTRIES


def screen_airport(row, airport):
    """Reason code when the owning airport rules the row out, else None."""
    if not IDENT_RE.match(row.get("airport_ident", "")):
        return "bad_ident"
    if airport is None:
        return "no_airport"
    if airport.get("type") not in KEPT_AIRPORT_TYPES:
        return "airport_type"
    try:
        lat = parse_coord(airport.get("latitude_deg"), 90.0)
        lon = parse_coord(airport.get("longitude_deg"), 180.0)
    except ValueError:
        return "bad_number"
    if lat is None or lon is None:
        return "bad_number"
    return None


def read_thresholds(row):
    """((le_lat, le_lon), (he_lat, he_lon)) or a reason string."""
    try:
        values = [
            parse_coord(row.get("le_latitude_deg"), 90.0),
            parse_coord(row.get("le_longitude_deg"), 180.0),
            parse_coord(row.get("he_latitude_deg"), 90.0),
            parse_coord(row.get("he_longitude_deg"), 180.0),
        ]
    except ValueError:
        return "bad_number"
    if any(value is None for value in values):
        return "missing_threshold"
    return (values[0], values[1]), (values[2], values[3])


def screen_runway(row):
    """Thresholds when the runway row itself is usable, else a reason."""
    thresholds = read_thresholds(row)
    if isinstance(thresholds, str):
        return thresholds
    closed = (row.get("closed") or "").strip()
    if closed not in ("0", "1"):
        return "bad_number"
    if closed == "1":
        return "closed"
    le_num = designator_number(row.get("le_ident"))
    he_num = designator_number(row.get("he_ident"))
    if le_num is None or he_num is None:
        return "designator"
    if (row.get("surface") or "").strip().upper() == "WATER":
        return "water"
    return thresholds


def normalise_pair(row, thresholds):
    """Runway record with the lower runway number first.

    The thresholds travel with their designators when the pair is swapped.
    Raises ValueError when the two numbers are not reciprocal.
    """
    le, he = row["le_ident"].strip(), row["he_ident"].strip()
    le_head = parse_optional_float(row.get("le_heading_degT"))
    he_head = parse_optional_float(row.get("he_heading_degT"))
    first, second = thresholds
    if abs(designator_number(le) - designator_number(he)) != 18:
        raise ValueError(
            "runways of %s are not reciprocal: %s/%s" % (row["airport_ident"], le, he)
        )
    if designator_number(le) > designator_number(he):
        le, he = he, le
        first, second = second, first
        le_head, he_head = he_head, le_head
    return {
        "le": le, "he": he, "thresholds": [first, second],
        "heading": le_head, "row_id": row.get("id", ""),
    }


def geometry_reason(pair):
    """Reason code when the surveyed thresholds contradict the designator."""
    start, end = pair["thresholds"]
    if local_length(start, end) < MIN_LENGTH_M:
        return "too_short"
    expected = designator_number(pair["le"]) * 10.0
    if angle_diff(local_bearing(start, end), expected) > MAX_DESIGNATOR_DEVIATION_DEG:
        return "bearing_mismatch"
    return None


def heading_warning(ident, pair):
    heading = pair["heading"]
    if heading is None:
        return None
    start, end = pair["thresholds"]
    if angle_diff(local_bearing(start, end), heading) > HEADING_WARN_DEG:
        return "warning: %s %s/%s stated heading %.1f disagrees with thresholds" % (
            ident, pair["le"], pair["he"], heading,
        )
    return None


def extended_segment(start, end, ref_lat, ref_lon):
    """Runway centreline in local metres, extended at both ends."""
    x0, y0 = local_xy(start[0], start[1], ref_lat, ref_lon)
    x1, y1 = local_xy(end[0], end[1], ref_lat, ref_lon)
    length = math.hypot(x1 - x0, y1 - y0)
    ux, uy = (x1 - x0) / length, (y1 - y0) / length
    return (
        (x0 - ux * EXTENSION_M, y0 - uy * EXTENSION_M),
        (x1 + ux * EXTENSION_M, y1 + uy * EXTENSION_M),
    )


def point_segment_distance(point, seg):
    (ax, ay), (bx, by) = seg
    abx, aby = bx - ax, by - ay
    t = ((point[0] - ax) * abx + (point[1] - ay) * aby) / (abx * abx + aby * aby)
    t = max(0.0, min(1.0, t))
    return math.hypot(point[0] - (ax + t * abx), point[1] - (ay + t * aby))


def _orientation(p, q, r):
    return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])


def segments_cross(seg_a, seg_b):
    p1, p2 = seg_a
    p3, p4 = seg_b
    d1, d2 = _orientation(p3, p4, p1), _orientation(p3, p4, p2)
    d3, d4 = _orientation(p1, p2, p3), _orientation(p1, p2, p4)
    return d1 * d2 < 0 and d3 * d4 < 0


def segment_distance(seg_a, seg_b):
    """Minimum distance between two segments, 0 when they cross."""
    if segments_cross(seg_a, seg_b):
        return 0.0
    return min(
        point_segment_distance(seg_a[0], seg_b),
        point_segment_distance(seg_a[1], seg_b),
        point_segment_distance(seg_b[0], seg_a),
        point_segment_distance(seg_b[1], seg_a),
    )


def axes_parallel(first, second):
    """True when two axis bearings (mod 180) differ by the parallel limit."""
    return angle_diff(first, second) <= PARALLEL_AXIS_DEG or (
        angle_diff(first, second + 180.0) <= PARALLEL_AXIS_DEG
    )


def half_widths(pairs, ref_lat, ref_lon):
    """Corridor half-width in metres for each runway pair of one airport.

    A parallel neighbour narrows the corridor to half the gap between the
    two centrelines (each extended by the corridor extension), bounded to
    [MIN_HALF_WIDTH_M, DEFAULT_HALF_WIDTH_M]. No neighbour keeps the default.
    """
    segments = [extended_segment(p["thresholds"][0], p["thresholds"][1], ref_lat, ref_lon)
                for p in pairs]
    axes = [local_bearing(p["thresholds"][0], p["thresholds"][1]) % 180.0 for p in pairs]
    result = []
    for i in range(len(pairs)):
        gaps = [
            segment_distance(segments[i], segments[j])
            for j in range(len(pairs))
            if j != i and axes_parallel(axes[i], axes[j])
        ]
        if not gaps:
            result.append(DEFAULT_HALF_WIDTH_M)
            continue
        bounded = min(DEFAULT_HALF_WIDTH_M, min(gaps) / 2.0)
        result.append(round(max(MIN_HALF_WIDTH_M, bounded), 1))
    return result


def corridor_corners(pair, half_width):
    """Latitude/longitude of the four corridor corners of a runway."""
    (lat0, lon0), (lat1, lon1) = pair["thresholds"]
    scale = M_PER_DEG_LAT * math.cos(math.radians((lat0 + lat1) / 2.0))
    dx, dy = (lon1 - lon0) * scale, (lat1 - lat0) * M_PER_DEG_LAT
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    corners = []
    for along in (-EXTENSION_M, length + EXTENSION_M):
        for across in (-half_width, half_width):
            x = ux * along - uy * across
            y = uy * along + ux * across
            corners.append((lat0 + y / M_PER_DEG_LAT, lon0 + x / scale))
    return corners


def corners_within_zone(pair, half_width, arp):
    for lat, lon in corridor_corners(pair, half_width):
        dx, dy = local_xy(lat, lon, arp[0], arp[1])
        if math.hypot(dx, dy) / M_PER_NM > ZONE_RADIUS_NM:
            return False
    return True


def runway_record(pair, half_width):
    start, end = pair["thresholds"]
    surface = SURFACES.get(pair.get("surface", "").strip().upper())
    return {
        "designator": "%s/%s" % (pair["le"], pair["he"]),
        "le": pair["le"],
        "he": pair["he"],
        "thresholds": [{"lat": p[0], "lon": p[1]} for p in (start, end)],
        "length_m": int(round(local_length(start, end))),
        "bearing_deg": round(initial_bearing(start, end), 2),
        "surface": surface,
        "half_width_m": half_width,
        "ground_half_width_m": min(GROUND_HALF_WIDTH_M, half_width),
    }


def collect_pairs(airports, runway_rows, warnings):
    """Kept runway pairs per airport ident and the exclusion list."""
    by_ident = {row["ident"]: row for row in airports}
    kept = {}
    exclusions = []
    seen = set()
    for row in runway_rows:
        ident = row.get("airport_ident", "")
        label = "%s/%s" % (row.get("le_ident", ""), row.get("he_ident", ""))
        reason = screen_airport(row, by_ident.get(ident))
        thresholds = None
        if reason is None:
            thresholds = screen_runway(row)
            reason = thresholds if isinstance(thresholds, str) else None
        pair = None
        if reason is None:
            pair = normalise_pair(row, thresholds)
            pair["surface"] = row.get("surface") or ""
            reason = geometry_reason(pair)
        if reason is not None:
            exclusions.append({
                "ident": ident, "designator": label,
                "row": row.get("id", ""), "reason": reason,
            })
            continue
        key = (ident, pair["le"], pair["he"])
        if key in seen:
            raise ValueError("duplicate runway %s %s/%s" % (ident, pair["le"], pair["he"]))
        seen.add(key)
        warning = heading_warning(ident, pair)
        if warning:
            warnings.append(warning)
        kept.setdefault(ident, []).append(pair)
    return kept, exclusions


def airport_record(airport, pairs):
    lat = parse_coord(airport["latitude_deg"], 90.0)
    lon = parse_coord(airport["longitude_deg"], 180.0)
    pairs = sorted(pairs, key=lambda p: (p["le"], p["he"]))
    widths = half_widths(pairs, lat, lon)
    runways = []
    for pair, width in zip(pairs, widths):
        if not width > 0:
            raise ValueError("non-positive half width at %s" % airport["ident"])
        if not corners_within_zone(pair, width, (lat, lon)):
            raise ValueError(
                "%s %s/%s corridor leaves the %.1f NM zone"
                % (airport["ident"], pair["le"], pair["he"], ZONE_RADIUS_NM)
            )
        runways.append(runway_record(pair, width))
    return {
        "icao": airport["ident"],
        "iata": (airport.get("iata_code") or "").strip(),
        "name": airport.get("name", ""),
        "municipality": airport.get("municipality", ""),
        "lat": lat,
        "lon": lon,
        "runways": runways,
    }


def build_catalogue(airports, runway_rows, snapshot, warnings=None):
    """(catalogue dict, sorted exclusion list) from parsed subset rows."""
    warnings = warnings if warnings is not None else []
    kept, exclusions = collect_pairs(airports, runway_rows, warnings)
    by_ident = {row["ident"]: row for row in airports}
    records = [airport_record(by_ident[ident], pairs) for ident, pairs in kept.items()]
    records.sort(key=lambda record: record["icao"])
    exclusions.sort(key=lambda e: (e["ident"], e["designator"], e["row"], e["reason"]))
    return {"snapshot": snapshot, "airports": records}, exclusions


def serialise_catalogue(catalogue):
    return json.dumps(
        catalogue, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ) + "\n"


def serialise_exclusions(exclusions):
    if not exclusions:
        return "[]\n"
    lines = [json.dumps(e, sort_keys=True, ensure_ascii=False) for e in exclusions]
    return "[\n" + ",\n".join(lines) + "\n]\n"


def file_sha256(path):
    with open(path, "rb") as handle:
        return sha256_bytes(handle.read())


def load_snapshot(data_dir):
    """Snapshot block for the catalogue, after checking the subset pin."""
    with open(os.path.join(data_dir, SOURCE_NAME), encoding="utf-8") as handle:
        source = json.load(handle)
    airports_sha = file_sha256(os.path.join(data_dir, AIRPORTS_SUBSET))
    runways_sha = file_sha256(os.path.join(data_dir, RUNWAYS_SUBSET))
    pinned = source["subset"]
    if pinned["airports"]["sha256"] != airports_sha or pinned["runways"]["sha256"] != runways_sha:
        raise ValueError("subset files do not match the sha256 pin in %s" % SOURCE_NAME)
    return {
        "date": source["snapshot_date"],
        "airports_sha256": airports_sha,
        "runways_sha256": runways_sha,
    }


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def build(data_dir, catalogue_path, exclusions_path):
    """Offline build from the committed subset; returns warning lines."""
    snapshot = load_snapshot(data_dir)
    airports = read_csv(os.path.join(data_dir, AIRPORTS_SUBSET))
    runway_rows = read_csv(os.path.join(data_dir, RUNWAYS_SUBSET))
    warnings = []
    catalogue, exclusions = build_catalogue(airports, runway_rows, snapshot, warnings)
    write_text(catalogue_path, serialise_catalogue(catalogue))
    write_text(exclusions_path, serialise_exclusions(exclusions))
    return warnings


def write_csv(path, header, rows):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=header, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def csv_header(path):
    with open(path, newline="", encoding="utf-8-sig") as handle:
        return next(csv.reader(handle))


def describe_file(path, url=None):
    with open(path, "rb") as handle:
        data = handle.read()
    entry = {"bytes": len(data), "sha256": sha256_bytes(data)}
    if url is not None:
        entry["url"] = url
    return entry


def refresh_subset(dump_dir, data_dir, snapshot_date):
    """Filter a full dump into the committed subset and rewrite the pin."""
    airports_path = os.path.join(dump_dir, "airports.csv")
    runways_path = os.path.join(dump_dir, "runways.csv")
    airports = read_csv(airports_path)
    runway_rows = read_csv(runways_path)
    scoped = {row["ident"]: row for row in airports if in_territory(row)}
    kept_runways = [r for r in runway_rows if r.get("airport_ident") in scoped]
    owners = {r["airport_ident"] for r in kept_runways}
    kept_airports = [row for row in airports if row["ident"] in owners]
    os.makedirs(data_dir, exist_ok=True)
    subset_airports = os.path.join(data_dir, AIRPORTS_SUBSET)
    subset_runways = os.path.join(data_dir, RUNWAYS_SUBSET)
    write_csv(subset_airports, csv_header(airports_path), kept_airports)
    write_csv(subset_runways, csv_header(runways_path), kept_runways)
    source = {
        "snapshot_date": snapshot_date,
        "licence": LICENCE,
        "data_dictionary": DATA_DICTIONARY,
        "full": {
            "airports": describe_file(airports_path, BASE_URL + "airports.csv"),
            "runways": describe_file(runways_path, BASE_URL + "runways.csv"),
        },
        "subset": {
            "airports": describe_file(subset_airports),
            "runways": describe_file(subset_runways),
        },
    }
    text = json.dumps(source, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    write_text(os.path.join(data_dir, SOURCE_NAME), text)


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--refresh", metavar="DIR",
                        help="filter the full dump in DIR into the committed subset")
    parser.add_argument("--snapshot-date", help="date of the dump (required with --refresh)")
    parser.add_argument("--data-dir", default=DATA_DIR)
    parser.add_argument("--catalogue", default=CATALOGUE_PATH)
    parser.add_argument("--exclusions", default=None)
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.refresh:
        if not args.snapshot_date:
            print("--snapshot-date is required with --refresh", file=sys.stderr)
            return 2
        refresh_subset(args.refresh, args.data_dir, args.snapshot_date)
    exclusions = args.exclusions or os.path.join(args.data_dir, EXCLUSIONS_NAME)
    for line in build(args.data_dir, args.catalogue, exclusions):
        print(line, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
