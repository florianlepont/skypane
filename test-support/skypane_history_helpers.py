"""Convenience helpers for exercising the history log ingestion API."""
from server.history_db import read_caddy_battery_log, apply_caddy_battery_log


def ingest_caddy_battery_log(conn, log_path):
    """Read and apply in one call - `read_caddy_battery_log()` followed by
    `apply_caddy_battery_log()` - for a caller with no reason to split the
    file read from the DB write (a script, a test, or any writer not
    itself inside a shared multi-write transaction). Returns rows
    actually inserted; 0 for a missing log file.
    """
    result = read_caddy_battery_log(conn, log_path)
    if result is None:
        return 0
    readings, new_offset = result
    return apply_caddy_battery_log(conn, readings, new_offset)

