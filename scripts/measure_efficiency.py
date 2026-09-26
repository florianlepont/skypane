#!/usr/bin/env python3
"""Prints the phase's before/after efficiency tables in markdown: per-route
byte weight and request time, first-load weight, static-file revalidation,
freshness-tick behaviour, and the poll cycle's wall time/counts across the
research's seven branches.

Stdlib only, plus the same test-support instruments the companion test
suite uses (test-support/efficiency_probe.py, companion_app_server.py,
skypane_test_support.py) - this script and the pytest suite measure
through the exact same seams, so a "before" and an "after" run are
comparable. Never touches the network: installs skypane_test_support's
resolver guard for its whole run, and replaces
server.plane.enrich.default_transport / server.plane.detect.query_provider
with offline fakes before doing anything else. Writes nothing outside its
own temp directory, and removes that directory at exit.
"""
import argparse
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

_HERE = os.path.dirname(os.path.abspath(__file__))  # scripts/
_REPO_ROOT = os.path.dirname(_HERE)
_TEST_SUPPORT_DIR = os.path.join(_REPO_ROOT, "test-support")
for _path in (_REPO_ROOT, _TEST_SUPPORT_DIR):
    if _path not in sys.path:
        sys.path.insert(0, _path)

import companion_app_server  # noqa: E402  (path bootstrap must run first)
import efficiency_probe  # noqa: E402
import skypane_test_support  # noqa: E402

import server.device_config as device_config  # noqa: E402
import server.plane.detect as detect  # noqa: E402
import server.plane.enrich as enrich  # noqa: E402

TAB_ROUTES = ("/", "/display", "/device", "/flights", "/health", "/airlines")
STATIC_REVALIDATION_ROUTES = ("/static/style.css", "/static/freshness.js")
FRESHNESS_ROUTES = ("/", "/display", "/flights", "/health")

# The interfaces block's own record: raw provider-shaped fields (not the
# normalised selection shape detect._normalise_selection() produces), the
# default geofence (runway 3) accepts it.
FLIGHT_RECORD = {
    "hex": "39a1b2", "flight": "AFR123  ", "lat": 48.7233, "lon": 2.3794,
    "alt_baro": 450, "gs": 137.1, "baro_rate": 1500, "seen_pos": 1.0,
}


def install_guards():
    """Block every non-loopback DNS lookup and replace the two seams that
    would otherwise make a real HTTP call, for the whole run - this
    script is not under pytest, so pytest-socket's connect-level guard is
    not installed; the DNS-level guard here is this script's own.
    """
    resolvers = skypane_test_support.guarded_resolvers()
    socket.getaddrinfo = resolvers["getaddrinfo"]
    socket.gethostbyname = resolvers["gethostbyname"]
    socket.gethostbyname_ex = resolvers["gethostbyname_ex"]
    enrich.default_transport = lambda callsign, timeout=None: (404, None)
    detect.query_provider = lambda name, lat, lon, radius_nm, timeout=None: []


def _git_sha():
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=_REPO_ROOT,
            capture_output=True, text=True, timeout=10)
        return result.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def _md_row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def _md_table(headers, rows):
    lines = [_md_row(headers), _md_row(["---"] * len(headers))]
    lines.extend(_md_row(row) for row in rows)
    return "\n".join(lines)


def build_header(args):
    lines = [
        "## Measurement",
        "",
        "- Label: %s" % args.label,
        "- Commit: %s" % _git_sha(),
        "- Machine: %s" % platform.node(),
        "- Platform: %s" % platform.platform(),
        "- Python: %s" % sys.version.split()[0],
        "- Repeats: %d" % args.repeats,
        "- Latency (s): %s" % args.latency,
        "- Timestamp (UTC): %s" % datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    ]
    return "\n".join(lines)


def build_routes_table(server, cookie, repeats):
    """The "Routes" table plus every route_weight() result this run
    computed, keyed by path - build_first_load_table() reuses it rather
    than re-fetching.
    """
    weights_by_route = {}
    rows = []

    def measure(path, use_cookie):
        result = efficiency_probe.route_weight(server, path, cookie=use_cookie, repeats=repeats)
        weights_by_route[path] = result
        rows.append([
            path, result["status"], result["identity_bytes"], result["gzip_bytes"],
            "%.2f" % result["ms"], len(result["script_srcs"]),
            "%.1f" % result["connections"], "%.1f" % result["init_schema"],
            "%.1f" % result["commits"],
        ])
        return result

    seen_scripts = []
    for path in TAB_ROUTES:
        result = measure(path, cookie)
        for src in result["script_srcs"]:
            if src not in seen_scripts:
                seen_scripts.append(src)

    measure("/login", None)
    measure("/static/style.css", None)

    for src in seen_scripts:
        if src not in weights_by_route:
            measure(src, None)

    headers = [
        "route", "status", "identity_bytes", "gzip6_bytes", "mean_ms",
        "script_count", "sqlite_conns", "init_schema", "commits",
    ]
    table = "## Routes\n\n" + _md_table(headers, rows)
    return table, weights_by_route


def build_first_load_table(weights_by_route):
    """Per tab route: HTML + /static/style.css + every script that route's
    own script_srcs named, identity and gzip-6 totals.
    """
    style = weights_by_route.get("/static/style.css")
    rows = []
    for path in TAB_ROUTES:
        html = weights_by_route[path]
        total_identity = html["identity_bytes"] + (style["identity_bytes"] if style else 0)
        total_gzip = html["gzip_bytes"] + (style["gzip_bytes"] if style else 0)
        for src in html["script_srcs"]:
            script_weight = weights_by_route.get(src)
            if script_weight:
                total_identity += script_weight["identity_bytes"]
                total_gzip += script_weight["gzip_bytes"]
        rows.append([path, total_identity, total_gzip])
    headers = ["route", "first_load_identity_bytes", "first_load_gzip6_bytes"]
    return "## First-load weight\n\n" + _md_table(headers, rows)


def build_static_revalidation_table(server):
    rows = []
    for path in STATIC_REVALIDATION_ROUTES:
        url = server.url(path)
        status1, headers1, _ = companion_app_server.http_request(url)
        etag = headers1.get("ETag")
        extra = {"If-None-Match": etag} if etag else None
        status2, _headers2, body2 = companion_app_server.http_request(url, extra_headers=extra)
        rows.append([
            path, etag, headers1.get("Last-Modified"), headers1.get("Cache-Control"),
            status2, len(body2),
        ])
    headers = [
        "path", "etag", "last_modified", "cache_control",
        "revalidate_status", "revalidate_bytes",
    ]
    return "## Static revalidation\n\n" + _md_table(headers, rows)


def build_freshness_table(server, cookie):
    rows = []
    for path in FRESHNESS_ROUTES:
        url = server.url(path)
        status1, headers1, _ = companion_app_server.http_request(url, cookie=cookie)
        extra = {"X-Requested-With": "freshness"}
        etag = headers1.get("ETag")
        if etag:
            extra["If-None-Match"] = etag
        status2, _headers2, body2 = companion_app_server.http_request(
            url, cookie=cookie, extra_headers=extra)
        rows.append([path, status2, len(body2)])
    headers = ["route", "freshness_status", "freshness_bytes"]
    return "## Freshness tick\n\n" + _md_table(headers, rows)


def _poll_cycle_row(label, result):
    return [
        label, "%.3f" % result["wall_s"], result["sleeps"], result["connections"],
        result["init_schema"], result["commits"], result["poll_state_writes"],
        result["poll_state_bytes"], result["state"],
    ]


def build_poll_cycle_table(state_dir, latency_s):
    """The research's seven branches, in order, all against the SAME
    fresh `state_dir` so each branch sees the previous one's persisted
    poll_state.json - exactly what "repeat"/"held"/"hold entry"/"hold
    repeat" mean here. `MIN_SECONDS_BETWEEN_CALLS` is left unpatched: this
    is a before/after measurement of the real cadence, not a probe-only
    test.
    """
    empty_records = {}
    flight_records = {"adsbfi": [FLIGHT_RECORD], "adsblol": [FLIGHT_RECORD]}

    rows = []
    for label, records in (
        ("empty sky (first)", empty_records),
        ("empty sky (repeat)", empty_records),
        ("flight detected", flight_records),
        ("same flight again", flight_records),
        ("nothing new, flight on screen", empty_records),
    ):
        result = efficiency_probe.cycle_probe(state_dir, latency_s=latency_s, records=records)
        rows.append(_poll_cycle_row(label, result))

    device_config.save_device_config(state_dir, display_enabled=False)
    for label in ("display_off hold entry", "display_off hold repeat"):
        result = efficiency_probe.cycle_probe(state_dir, latency_s=latency_s, records=empty_records)
        rows.append(_poll_cycle_row(label, result))
    device_config.save_device_config(state_dir, display_enabled=True)

    headers = [
        "branch", "wall_s", "sleeps", "connections", "init_schema", "commits",
        "poll_state_writes", "poll_state_bytes", "state",
    ]
    table = "## Poll cycle\n\n" + _md_table(headers, rows)

    fresh_dir = tempfile.mkdtemp(prefix="skypane-eff-empty0-")
    try:
        os.makedirs(fresh_dir, exist_ok=True)
        zero_latency = efficiency_probe.cycle_probe(fresh_dir, latency_s=0, records=empty_records)
    finally:
        shutil.rmtree(fresh_dir, ignore_errors=True)
    extra_line = "Empty-sky wall time at latency 0 (fresh state dir): %.4f s" % zero_latency["wall_s"]

    return table + "\n\n" + extra_line


def build_parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--label", default="measurement",
        help="Free-text label recorded in the header (e.g. before / after).")
    parser.add_argument(
        "--repeats", type=int, default=5,
        help="Timed requests per route_weight() call (default: 5).")
    parser.add_argument(
        "--latency", type=float, default=0.25,
        help="Simulated per-provider ADS-B latency in seconds for the poll-cycle table "
             "(default: 0.25).")
    return parser


def main(argv=None):
    args = build_parser().parse_args(argv)
    install_guards()

    scratch_dir = tempfile.mkdtemp(prefix="skypane-eff-")
    try:
        state_dir = os.path.join(scratch_dir, "companion-state")
        os.makedirs(state_dir, exist_ok=True)
        efficiency_probe.seed_history(state_dir, n=30)

        server = companion_app_server.InProcessAppServer(state_dir)
        try:
            cookie = companion_app_server.login(server)
            routes_table, weights_by_route = build_routes_table(server, cookie, args.repeats)
            first_load_table = build_first_load_table(weights_by_route)
            static_revalidation_table = build_static_revalidation_table(server)
            freshness_table = build_freshness_table(server, cookie)
        finally:
            server.stop()

        cycle_state_dir = os.path.join(scratch_dir, "cycle-state")
        os.makedirs(cycle_state_dir, exist_ok=True)
        poll_cycle_section = build_poll_cycle_table(cycle_state_dir, args.latency)

        sections = [
            build_header(args),
            routes_table,
            first_load_table,
            static_revalidation_table,
            freshness_table,
            poll_cycle_section,
        ]
        print("\n\n".join(sections))
    finally:
        shutil.rmtree(scratch_dir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
