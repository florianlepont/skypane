"""Storage limits for private photos.

The limits are checked by `check`, which the store calls inside the same
write transaction that inserts the row, so concurrent uploads cannot
overshoot. No user-facing text lives here: a refusal carries a stable
machine code that the UI layer maps to English and French.
"""
from __future__ import annotations

import os
import shutil
import sqlite3
import sys

# Same repo-root sys.path bootstrap as server/device_dirs.py.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from server import fleet_db  # noqa: E402

MAX_PHOTOS_PER_FRAME = 20
MAX_BYTES_PER_FRAME = 20_000_000
MAX_BYTES_SERVER = 500_000_000
MIN_FREE_DISK_BYTES = 2_000_000_000

CODE_DISK_LOW = "disk_low"
CODE_FRAME_COUNT = "frame_count"
CODE_FRAME_BYTES = "frame_bytes"
CODE_SERVER_BYTES = "server_bytes"


class QuotaExceeded(Exception):
    """A limit would be crossed; `code` is one of the CODE_* constants and
    `limit` the value that was hit."""

    def __init__(self, code: str, limit: int) -> None:
        super().__init__(code)
        self.code = code
        self.limit = limit


def free_disk_bytes(root: str) -> int:
    return int(shutil.disk_usage(root).free)


def check(
    conn: sqlite3.Connection, device_id: str, new_bytes: int, free_bytes: int
) -> None:
    """Raise QuotaExceeded when storing `new_bytes` more for this frame
    would cross a limit. Precedence: disk_low, frame_count, frame_bytes,
    server_bytes. Landing exactly on a limit is accepted."""
    if free_bytes - new_bytes < MIN_FREE_DISK_BYTES:
        raise QuotaExceeded(CODE_DISK_LOW, MIN_FREE_DISK_BYTES)
    count, used = fleet_db.photo_usage(conn, device_id)
    if count + 1 > MAX_PHOTOS_PER_FRAME:
        raise QuotaExceeded(CODE_FRAME_COUNT, MAX_PHOTOS_PER_FRAME)
    if used + new_bytes > MAX_BYTES_PER_FRAME:
        raise QuotaExceeded(CODE_FRAME_BYTES, MAX_BYTES_PER_FRAME)
    if fleet_db.server_photo_bytes(conn) + new_bytes > MAX_BYTES_SERVER:
        raise QuotaExceeded(CODE_SERVER_BYTES, MAX_BYTES_SERVER)
