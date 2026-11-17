"""Shared helpers for the battery-history export tests that need a request,
a bearer header or seeded `device_health` rows."""
import json
import secrets
from datetime import datetime, timezone

from companion_app_server import http_request
from server import history_db

__test__ = False

PATH = "/api/export/battery-history"
TOKEN_ENV = "SKYPANE_EXPORT_TOKEN"
WAKE_KEYS = [
    "wake_seq", "boot_ms", "wifi_ms", "wifi_attempts", "prev_seq",
    "prev_awake_ms", "prev_request_ms", "prev_download_ms", "prev_draw_ms",
    "prev_spi_ms", "prev_tls_ms", "prev_redraw", "prev_outcome"]
KEYS = ["ts", "battery_mv", "fw_version", "boot_reason", "rssi"] + WAKE_KEYS


def new_token(length=48):
    return secrets.token_urlsafe(length)[:length]


def iso(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def now():
    return datetime.now(timezone.utc).replace(microsecond=0)


def bearer(token):
    return {"Authorization": "Bearer " + token}


def stamp(moment):
    # The format the battery-log tailer stores.
    return moment.isoformat(timespec="seconds")


def seed_rows(state_dir, rows):
    conn = history_db.connect(state_dir)
    try:
        for ts, battery_mv, fw, boot, rssi in rows:
            history_db.record_device_health(conn, ts, battery_mv, fw, boot, rssi)
        conn.commit()
    finally:
        conn.close()


def get(server, query="", headers=None, path=PATH):
    return http_request(server.url(path + query), extra_headers=headers or {})


def since_query(moment):
    return "?since=" + iso(moment)


def lines(body):
    return [json.loads(line) for line in body.decode("utf-8").splitlines()]
