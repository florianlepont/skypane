#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""scripts/export_snapshot.py -- saves the production export routes into a
directory, with a MANIFEST.json (row count and sha256 per file).

Stdlib only. Read-only: three GET requests. No credential is read or written
here; the network proxy adds the Authorization header to requests for the
export path. TLS verification is never relaxed. HTTPS_PROXY and the CA bundle
come from the environment (urllib honours them by default).

The snapshot is evidence: an existing file is never replaced unless
--overwrite is given.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

DEFAULT_BASE_URL = "https://skypane.algernon.is"
DEFAULT_SINCE = "2026-11-01T00:00:00Z"
TIMEOUT_S = 120

# (file name, route, whether the route takes ?since=)
ROUTES = (
    ("runway_events.jsonl", "/api/export/flights", True),
    ("poll_cycles.jsonl", "/api/export/poll-cycles", True),
    ("status.json", "/api/export/status", False),
)


def http_fetch(url):
    """GET `url` and return the body as text; raises on any HTTP/network error."""
    request = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
        return response.read().decode("utf-8")


def count_rows(name, text):
    """JSON Lines: non-empty lines. status.json is a single object: 1 row."""
    if name.endswith(".json"):
        json.loads(text)
        return 1
    return sum(1 for line in text.splitlines() if line.strip())


def run_snapshot(base_url, since, out_dir, fetch, overwrite=False):
    """Fetch every route with `fetch(url) -> text`, write the files and the
    manifest, and return the manifest dict.

    A failing route is recorded as an error and does not stop the others.
    Raises FileExistsError before any request when a target file exists and
    `overwrite` is false.
    """
    os.makedirs(out_dir, exist_ok=True)
    if not overwrite:
        for name, _route, _takes_since in ROUTES:
            if os.path.exists(os.path.join(out_dir, name)):
                raise FileExistsError(
                    f"{name} already exists in {out_dir}; use --overwrite")
    base = base_url.rstrip("/")
    manifest = {
        "fetched_at": datetime.datetime.now(datetime.timezone.utc)
        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "since": since,
        "base_url": base,
        "files": {},
    }
    for name, route, takes_since in ROUTES:
        url = base + route
        if takes_since:
            url += "?" + urllib.parse.urlencode({"since": since})
        entry = {"route": route}
        try:
            text = fetch(url)
            entry["rows"] = count_rows(name, text)
        except Exception as exc:  # recorded, not fatal: other routes still run
            entry["error"] = f"{type(exc).__name__}: {exc}"
        else:
            data = text.encode("utf-8")
            with open(os.path.join(out_dir, name), "wb") as handle:
                handle.write(data)
            entry["sha256"] = hashlib.sha256(data).hexdigest()
        manifest["files"][name] = entry
    with open(os.path.join(out_dir, "MANIFEST.json"), "w",
              encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--since", default=DEFAULT_SINCE,
                        help="UTC time, e.g. 2026-11-01T00:00:00Z")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        manifest = run_snapshot(args.base_url, args.since, args.out,
                                http_fetch, overwrite=args.overwrite)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    failed = False
    for name, entry in manifest["files"].items():
        if "error" in entry:
            failed = True
            print(f"{name}: ERROR {entry['error']}", file=sys.stderr)
        else:
            print(f"{name}: {entry['rows']} rows sha256={entry['sha256']}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
