"""The strict multipart reader behind the illustration upload.

The form posts two parts, in this order: the anti-forgery token as a plain
text part named `csrf_token`, then exactly one file part. Nothing else is
accepted: no further parts, no filename on the token part, no token part
after the file. The token is read from the first bytes of the body so it
can be checked before the rest of the upload is read, and so an oversized
upload still gets its own refusal once the token has passed.
"""
import email.message
import re
import socket

from companion import request_body

# Bounds peak memory per upload to a few MB.
MAX_UPLOAD_BYTES = 4 * 1024 * 1024
TOKEN_FIELD = "csrf_token"
# A session token is a SHA-256 hex digest; the ceiling leaves room for a
# longer digest without letting a body inflate the part.
MAX_TOKEN_CHARS = 128
# Boundary line, token part headers, a token at its ceiling and the next
# boundary line fit in this many leading bytes.
HEAD_BYTES = 512
# RFC 2046 boundary length ceiling.
MAX_BOUNDARY_CHARS = 70

_TOKEN_HEADER = re.compile(
    rb'content-disposition:[ \t]*form-data;[ \t]*name="' + TOKEN_FIELD.encode("ascii") + rb'"',
    re.IGNORECASE)
_TOKEN_VALUE = re.compile(rb"[A-Za-z0-9_-]{1,%d}" % MAX_TOKEN_CHARS)


def _boundary(content_type):
    """The multipart boundary as bytes, or None when the header is not a
    well-formed `multipart/form-data` one."""
    message = email.message.Message()
    message["content-type"] = content_type
    if message.get_content_type() != "multipart/form-data":
        return None
    boundary = message.get_param("boundary")
    if not isinstance(boundary, str) or not boundary:
        return None
    boundary_bytes = boundary.encode("ascii")
    if len(boundary_bytes) > MAX_BOUNDARY_CHARS:
        return None
    return boundary_bytes


def _leading_token(delimiter, data):
    """(token, offset): the token text of a body that opens with the token
    part, and the offset of the next delimiter's CRLF in `data`; (None, 0)
    when the body does not open with a token part or the part is malformed
    or not yet complete in `data`."""
    opening = delimiter + b"\r\n"
    if not data.startswith(opening):
        return None, 0
    header_end = data.find(b"\r\n\r\n", len(opening))
    if header_end < 0 or _TOKEN_HEADER.fullmatch(data[len(opening):header_end]) is None:
        return None, 0
    start = header_end + 4
    end = data.find(b"\r\n" + delimiter, start)
    if end < 0 or _TOKEN_VALUE.fullmatch(data[start:end]) is None:
        return None, 0
    return data[start:end].decode("ascii"), end


def leading_token(content_type, head):
    """The anti-forgery token an upload opens with, read from the first bytes
    of the body, or None when it does not open with a well-formed token
    part. Never raises."""
    try:
        boundary = _boundary(content_type)
        if boundary is None:
            return None
        return _leading_token(b"--" + boundary, head)[0]
    except Exception:
        return None


def _file_payload(delimiter, body):
    """The payload of a body holding exactly one part (after an optional
    whitespace preamble), or None."""
    segments = body.split(delimiter)
    # A preamble, the part itself and an epilogue: zero parts, two or more
    # parts and a missing closing delimiter all change the count.
    if len(segments) != 3:
        return None
    preamble, part, epilogue = segments
    if preamble.strip(b"\r\n \t") != b"" or not epilogue.startswith(b"--"):
        return None
    if not part.startswith(b"\r\n"):
        return None
    # The part's own headers (filename, field name, media type) are never
    # read: the destination and the "is this an image" check come from
    # elsewhere, never from this body's claims.
    _headers, separator, payload = part[2:].partition(b"\r\n\r\n")
    if not separator:
        return None
    if payload.endswith(b"\r\n"):
        payload = payload[:-2]
    return payload or None


def parse_upload_form(content_type, body):
    """(payload, token): the file part's raw bytes and the anti-forgery token
    of a body that is one file part, optionally preceded by the token part;
    None for anything else. `token` is None when the body has no token part.
    Never raises."""
    try:
        boundary = _boundary(content_type)
        if boundary is None:
            return None
        delimiter = b"--" + boundary
        token, end = _leading_token(delimiter, body)
        if token is not None:
            # Past the token part, what is left is a one-part body.
            body = body[end + 2:]
        payload = _file_payload(delimiter, body)
        return None if payload is None else (payload, token)
    except Exception:
        return None


def parse_single_uploaded_file(content_type, body):
    """The raw payload of a `multipart/form-data` body that holds exactly one
    file part (a leading token part is allowed), or None. Never raises."""
    parsed = parse_upload_form(content_type, body)
    return None if parsed is None else parsed[0]


def read_upload(handler, cap):
    """Read the upload's body, bounded by `cap` bytes, and return the token it
    opens with (or None). The body is left on `handler.upload_body` as
    `(raw, over_cap)` for the route handler: `raw` is None when it was over
    the cap or unreadable. An oversized body is drained, not kept."""
    handler.upload_body = (None, False)
    length = request_body.parse_content_length(handler.headers)
    if length <= 0:
        return None
    try:
        head = handler.rfile.read(min(length, HEAD_BYTES))
    except socket.timeout:
        return None
    token = leading_token(handler.headers.get("Content-Type"), head)
    rest, over_cap = request_body.drain_capped_body(
        handler.rfile, length - len(head), cap - len(head))
    handler.upload_body = (None if rest is None else head + rest, over_cap)
    return token
