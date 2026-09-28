"""The shared request-body drain behind `companion/app.py`'s
`Handler.read_form()` and `Handler._read_upload_body()`: one capped
read-then-drain loop, so the two callers differ only in their own cap
and degrade value, never in how a body is actually read off the wire.
"""
import socket


def parse_content_length(headers):
    """The request's declared `Content-Length` as an int, or 0 for an
    absent or unparseable header — every caller here treats a 0-or-less
    length identically to "no body at all", so a malformed header
    degrades exactly the same way a genuinely empty one does.
    """
    try:
        return int(headers.get("Content-Length", "0"))
    except (TypeError, ValueError):
        return 0


def drain_capped_body(rfile, length, cap):
    """Read a request body of declared `length` bytes from `rfile`,
    capped at `cap`. Returns `(raw, over_cap)`:

    - at or under the cap, `raw` holds the body's bytes and `over_cap`
      is False;
    - over the cap, `raw` is None and `over_cap` is True — the
      remainder of the declared length is drained first, in fixed-size
      chunks, stopping early on a short read (the client closed the
      connection) so this never loops forever, and so the connection is
      never left mid-body for the caller's next request;
    - a `socket.timeout` while reading — bounded by `Handler.timeout` —
      returns `(None, False)` without draining anything further.
    """
    try:
        raw = rfile.read(min(length, cap + 1))
        if length > cap:
            remaining = length - len(raw)
            while remaining > 0:
                chunk = rfile.read(min(remaining, 65536))
                if not chunk:
                    break
                remaining -= len(chunk)
            return None, True
    except socket.timeout:
        return None, False
    return raw, False
