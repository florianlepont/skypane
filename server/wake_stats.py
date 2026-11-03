"""Strict parser for the X-Wake-Stats request header.

The value comes from a device and is untrusted: a semicolon-separated
`key=value` list. Any rule violation drops the whole header (None), never
a partial result, so a forged or truncated value can only ever store
NULL wake columns. The raw value is never logged or echoed.

Stdlib only; leaf module.
"""
import re
from typing import Optional

# Single server-side source of truth for the header size cap. The worst case
# with every field at its bound is 173 bytes, so the cap never refuses a
# legitimate frame.
WAKE_STATS_MAX_BYTES = 192

_MS_MAX = 3_600_000
_U32_MAX = 4_294_967_295

# header key -> (column name, inclusive upper bound); the lower bound is 0.
_INT_KEYS: dict[str, tuple[str, int]] = {
    "seq": ("wake_seq", _U32_MAX),
    "bt": ("boot_ms", _MS_MAX),
    "wf": ("wifi_ms", _MS_MAX),
    "att": ("wifi_attempts", 16),
    "p_seq": ("prev_seq", _U32_MAX),
    "p_aw": ("prev_awake_ms", _MS_MAX),
    "p_rq": ("prev_request_ms", _MS_MAX),
    "p_dl": ("prev_download_ms", _MS_MAX),
    "p_dr": ("prev_draw_ms", _MS_MAX),
    "p_sp": ("prev_spi_ms", _MS_MAX),
    "p_tls": ("prev_tls_ms", _MS_MAX),
    "p_rd": ("prev_redraw", 2),
}
_TEXT_KEY = "p_out"
_TEXT_COLUMN = "prev_outcome"

# Column names in contract order, shared with history_db and the export.
WAKE_COLUMNS: tuple[str, ...] = (
    "wake_seq", "boot_ms", "wifi_ms", "wifi_attempts",
    "prev_seq", "prev_awake_ms", "prev_request_ms", "prev_download_ms",
    "prev_draw_ms", "prev_spi_ms", "prev_tls_ms", "prev_redraw",
    "prev_outcome",
)

# ASCII digits only (str.isdigit() accepts other scripts); at most ten, so
# int() never sees an unbounded string.
_DIGITS_RE = re.compile(r"[0-9]{1,10}", re.ASCII)
_TOKEN_RE = re.compile(r"[a-z0-9-]{1,16}", re.ASCII)
_PAIR_RE = re.compile(r"([a-z_]{1,5})=([^;]*)", re.ASCII)


def _parse_pair(
    segment: str, seen: set[str], out: dict[str, object]
) -> Optional[bool]:
    """Apply one `key=value` segment to `out`. Returns the validity of the
    version key (True/False) for `v`, True for any other accepted key, and
    None when the segment violates a rule.
    """
    match = _PAIR_RE.fullmatch(segment)
    if match is None:
        return None
    key, raw = match.group(1), match.group(2)
    if key in seen:
        return None
    seen.add(key)
    if key == "v":
        return raw == "1" or None
    if key == _TEXT_KEY:
        if _TOKEN_RE.fullmatch(raw) is None:
            return None
        out[_TEXT_COLUMN] = raw
        return True
    spec = _INT_KEYS.get(key)
    if spec is None or _DIGITS_RE.fullmatch(raw) is None:
        return None
    value = int(raw)
    if value > spec[1]:
        return None
    out[spec[0]] = value
    return True


def parse_wake_stats(value: object) -> Optional[dict[str, object]]:
    """The wake columns carried by an X-Wake-Stats value, keyed by column
    name for the keys present, or None when any rule is violated. `v` must
    be present and equal to 1; it is validated and not returned.
    """
    if not isinstance(value, str) or not value or not value.isascii():
        return None
    if len(value) > WAKE_STATS_MAX_BYTES:
        return None
    out: dict[str, object] = {}
    seen: set[str] = set()
    for segment in value.split(";"):
        if _parse_pair(segment, seen, out) is None:
            return None
    if "v" not in seen:
        return None
    return out
