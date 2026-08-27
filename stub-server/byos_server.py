#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 YODE PTE LTD
# SPDX-License-Identifier: Apache-2.0
"""Minimal bring-your-own-server for FlightPortrait frames. Stdlib only.

Implements the three device endpoints from docs/PROTOCOL.md well enough
to run a stock frame: point the frame at this host during BLE
provisioning (PROTOCOL.md §5) and it will set up, poll, download, and
display whatever panel image you serve.

    python3 byos_server.py --image path/to/panel.bin [--port 8642]
        [--secret VALUE] [--sleep 3600] [--state-dir DIR]

The image must be exactly 960,000 bytes in the PROTOCOL.md §1 format
(the calibration patterns in first-flash/bins/ work). Swap the file on
disk and the next poll serves the new content — the frame notices via
the hash and refreshes. --secret, when set, must match the structured
BYOS setup secret entered during provisioning; without it any
provision_secret is accepted. Issued device tokens live in
byos_state.json inside --state-dir (default: next to this script), so
restarts don't strand frames.

This is a reference, not a product: no TLS (the frame allows plain http
for hand-set targets), no rate limiting, one image for every frame.

SkyPane local modifications: added --state-dir so a throwaway harness
run (stub-server/test_poll_cycle.py) can isolate its own token state
from the long-running instance the hardware bring-up plans keep alive;
added --image-url-scheme (default: http) so the served image_url can
advertise https when this process runs behind a TLS-terminating
reverse proxy (Phase 2's Caddy-fronted deployment), instead of always
hardcoding http; and added DEVICE-04 X-Battery-Mv validation/persistence
(parse_battery_mv() / save_battery_state()) - an authenticated
/device/v1/display poll carrying a plausible reading writes
battery_state.json ({"battery_mv": int, "received_at": float}) in
--state-dir, the single writer of that file anywhere in this repo (see
stub-server/VENDOR.md). See stub-server/VENDOR.md for the full list of
local changes.
"""
import argparse
import hashlib
import json
import os
import secrets
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

IMAGE_BYTES = 960000
# DEVICE-04 X-Battery-Mv sanity bounds. BATTERY_MV_MIN = 1: PROTOCOL.md §2
# defines "0" as the *unknown* sentinel, so zero must be rejected rather than
# persisted as a real reading. BATTERY_MV_MAX = 10000: a sanity ceiling far
# above any single-cell LiPo (4200 mV full charge), per 05-RESEARCH.md's V5
# Input Validation row.
BATTERY_MV_MIN = 1
BATTERY_MV_MAX = 10000


def state_path(state_dir):
    return os.path.join(state_dir, "byos_state.json")


def load_state(state_dir):
    try:
        with open(state_path(state_dir)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"tokens": {}}


def save_state(state_dir, state):
    tmp = state_path(state_dir) + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(state, fh, indent=1)
    os.replace(tmp, state_path(state_dir))


def battery_state_path(state_dir):
    return os.path.join(state_dir, "battery_state.json")


def parse_battery_mv(raw):
    """Parse a raw X-Battery-Mv header value into a plausible millivolt
    reading, or None. Never raises, never logs the raw value.

    Rejects anything that is not a string; a string whose length is not
    between 1 and 5 characters; and any string containing a character
    outside the literal ASCII digit set below - checked explicitly against
    that set, not via a general digit-classification predicate, which
    would accept non-ASCII decimal digits that int() then either misparses
    or raises on. No whitespace, no sign character - a well-formed device
    sends bare digits and nothing else. Only after those checks does this
    convert to int and reject anything outside BATTERY_MV_MIN..BATTERY_MV_MAX
    inclusive (T-05-02-01).
    """
    if not isinstance(raw, str):
        return None
    if not (1 <= len(raw) <= 5):
        return None
    if any(c not in "0123456789" for c in raw):
        return None
    mv = int(raw)
    if not (BATTERY_MV_MIN <= mv <= BATTERY_MV_MAX):
        return None
    return mv


def save_battery_state(state_dir, mv):
    """Persist {"battery_mv": mv, "received_at": time.time()} to
    battery_state.json in state_dir, atomically (tmp-write then
    os.replace(), mirroring save_state()'s pattern). This function - and
    this process - are the ONLY writer of that file anywhere in the repo;
    server/poll_loop.py only ever reads it (05-RESEARCH.md Pitfall 4: two
    processes doing read-modify-write on one JSON file is a real
    lost-update race, and neither unit takes a lock).
    """
    path = battery_state_path(state_dir)
    tmp = path + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"battery_mv": mv, "received_at": time.time()}, fh, indent=1)
    os.replace(tmp, path)


class Handler(BaseHTTPRequestHandler):
    server_version = "flightportrait-byos-example"
    args = None
    state = None

    def send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_body_json(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(n).decode())
        except (ValueError, UnicodeDecodeError):
            return None

    def bearer_ok(self):
        auth = self.headers.get("Authorization", "")
        return (auth.startswith("Bearer ") and
                auth[7:] in self.state["tokens"].values())

    def log_telemetry(self):
        parts = []
        for h in ("X-Fw-Version", "X-Boot-Reason", "X-Rssi",
                  "X-Battery-Mv"):
            v = self.headers.get(h)
            if v:
                parts.append("%s=%s" % (h, v))
        if parts:
            print("  telemetry:", " ".join(parts))

    def do_POST(self):
        if self.path == "/device/v1/setup":
            body = self.read_body_json()
            if not isinstance(body, dict) or "mac" not in body:
                return self.send_json(422, {"detail": "bad body"})
            if (self.args.secret and
                    body.get("provision_secret") != self.args.secret):
                return self.send_json(401, {"detail": "bad secret"})
            token = secrets.token_hex(32)
            self.state["tokens"][body["mac"]] = token
            save_state(self.args.state_dir, self.state)
            print("setup: %s enrolled (hw_rev=%s)"
                  % (body["mac"], body.get("hw_rev", "?")))
            # No pairing block: account pairing is a first-party
            # extension this example does not implement (PROTOCOL.md §2).
            return self.send_json(200, {"device_token": token})
        if self.path == "/device/v1/log":
            if not self.bearer_ok():
                return self.send_json(401, {"detail": "unknown token"})
            body = self.read_body_json()
            if not isinstance(body, dict) or \
                    not isinstance(body.get("logs"), list):
                return self.send_json(422, {"detail": "bad body"})
            self.log_telemetry()
            for entry in body["logs"]:
                print("  frame log [%s] %s (ts=%s)"
                      % (entry.get("level", "error"),
                         entry.get("message", ""), entry.get("ts")))
            return self.send_json(200, {"ok": True})
        return self.send_json(404, {"detail": "unknown endpoint"})

    def do_GET(self):
        if self.path == "/device/v1/display":
            if not self.bearer_ok():
                return self.send_json(401, {"detail": "unknown token"})
            self.log_telemetry()
            # DEVICE-04: strictly after the bearer_ok() gate above, so an
            # unauthenticated/wrong-token caller can never pin a victim
            # frame's panel into a permanent low-battery warning
            # (T-05-02-04). A telemetry side-effect must never turn a
            # healthy panel poll into a 500 - a full or read-only state
            # directory degrades to "no battery signal", which
            # poll_loop.py already treats as legitimate (single-writer
            # rule: this is the only place battery_state.json is written).
            battery_mv = parse_battery_mv(self.headers.get("X-Battery-Mv"))
            if battery_mv is not None:
                try:
                    save_battery_state(self.args.state_dir, battery_mv)
                except OSError:
                    pass
            try:
                with open(self.args.image, "rb") as fh:
                    image = fh.read()
            except OSError:
                return self.send_json(503, {"detail": "image unreadable"})
            if len(image) != IMAGE_BYTES:
                return self.send_json(503, {"detail": "image wrong size"})
            digest = hashlib.sha256(image).hexdigest()
            host = self.headers.get("Host", "localhost")
            return self.send_json(200, {
                "image_url": "%s://%s/img/%s.bin" % (
                    self.args.image_url_scheme, host, digest),
                "image_hash": "sha256:" + digest,
                "sleep_s": self.args.sleep,
                "firmware": None,
                "reset": False,
            })
        if self.path.startswith("/img/"):
            try:
                with open(self.args.image, "rb") as fh:
                    image = fh.read()
            except OSError:
                return self.send_json(503, {"detail": "image unreadable"})
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(image)))
            self.end_headers()
            self.wfile.write(image)
            return None
        return self.send_json(404, {"detail": "unknown endpoint"})

    def log_message(self, fmt, *fmt_args):
        print("%s %s" % (self.command, self.path))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--image", required=True,
                    help="960,000-byte panel image to serve")
    ap.add_argument("--port", type=int, default=8642)
    ap.add_argument("--secret", default="",
                    help="require this BYOS setup secret (default: any)")
    ap.add_argument("--sleep", type=int, default=3600,
                    help="sleep_s handed to the frame (default 3600)")
    ap.add_argument("--state-dir", default=None,
                    help="parent directory for byos_state.json "
                         "(default: the directory containing this script)")
    ap.add_argument("--image-url-scheme", choices=["http", "https"],
                    default="http",
                    help="scheme advertised in the /device/v1/display "
                         "response's image_url (default: http). Leave at "
                         "http for the local Phase 1 stub flow on the LAN; "
                         "set to https for a deployment fronted by a "
                         "TLS-terminating reverse proxy (e.g. Caddy), so "
                         "the panel download is not silently downgraded "
                         "to plaintext.")
    args = ap.parse_args()
    if not os.path.exists(args.image):
        sys.exit("no such image: %s" % args.image)
    if args.state_dir is None:
        args.state_dir = os.path.dirname(os.path.abspath(__file__))
    sys.stdout.reconfigure(line_buffering=True)

    Handler.args = args
    Handler.state = load_state(args.state_dir)
    server = ThreadingHTTPServer(("0.0.0.0", args.port), Handler)
    print("serving %s on port %d — point the frame at http://<this-host>:%d"
          % (args.image, args.port, args.port))
    server.serve_forever()


if __name__ == "__main__":
    main()
