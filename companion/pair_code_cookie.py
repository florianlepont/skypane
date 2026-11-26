"""Keeps a refused pairing code, and the frame name typed with it, for the
next showing of the form.

A refused code is answered with a redirect back to the form; so the person
only corrects a typo, the code rides in a cookie that lives for about two
minutes and is put back in the field once. The code is a secret until it is
accepted, so the cookie is never a URL, a log line or a redirect target:

- HttpOnly, SameSite=Strict, Secure wherever the app sets Secure elsewhere,
  and a Path of the pairing form alone, so no other request carries it;
- set only on a refused code (a text outside the code alphabet is not stored
  at all: the cookie then only marks the refusal), and cleared the first time the form is shown;
- bound to the signed-in session that typed it, so another person using the
  same browser never sees it;
- limited to the form's own length and alphabet before it is stored, and
  checked again when it is read back.

The optional frame name rides in the same cookie as the lower-case hex of its
UTF-8 bytes, so the value stays cookie-safe and inert whatever was typed. It
is stored only when the rename rules accept it and re-checked on the way out.
"""
import re

from companion import auth
from companion.pages import frame_name_page

COOKIE_NAME = "sp_pair_code"
COOKIE_PATH = "/pair-frame"
MAX_AGE_S = 120
# The form's maxlength; a longer value is cut before it is stored.
MAX_CODE_CHARS = 12
_SESSION_KEY_HEX = 16
_CODE_RE = re.compile(r"[A-Z0-9-]{1,%d}" % MAX_CODE_CHARS)
# Hex characters of the longest name: two per byte, at most four bytes per character.
_MAX_NAME_HEX = frame_name_page.MAX_NAME_CHARS * 4 * 2
_VALUE_RE = re.compile(
    r"([0-9a-f]{%d})\.([A-Z0-9-]*)(?:\.([0-9a-f]{0,%d}))?" % (_SESSION_KEY_HEX, _MAX_NAME_HEX))


def _header(value, max_age):
    return "%s=%s; HttpOnly%s; SameSite=Strict; Path=%s; Max-Age=%d" % (
        COOKIE_NAME, value, auth.secure_cookie_flag(), COOKIE_PATH, max_age)


def _folded(raw):
    """The typed text as the form would hold it (upper case, no spaces, cut
    to the field's length), or None when it holds anything outside the code
    alphabet and hyphen."""
    text = "".join(raw.split()).upper()[:MAX_CODE_CHARS]
    return text if _CODE_RE.fullmatch(text) else None


def _encoded_name(name):
    """The hex of a name the rename rules accept; "" for anything else."""
    tidy = frame_name_page.normalise_name(name)
    return tidy.encode("utf-8").hex() if tidy is not None else ""


def _decoded_name(hex_text):
    """The name a stored hex text holds, re-checked; "" when it is not one."""
    try:
        text = bytes.fromhex(hex_text or "").decode("utf-8")
    except ValueError:
        return ""
    return frame_name_page.normalise_name(text) or ""


def keep_header(session_key, raw_code, name=""):
    """The Set-Cookie value that keeps `raw_code` (and `name`, when the rename
    rules accept it) for `session_key`. A text that is not a plausible code is
    not stored: the cookie then holds the session alone, which only marks that
    a refusal is being shown (None when the session key itself is malformed)."""
    if not re.fullmatch("[0-9a-f]{%d}" % _SESSION_KEY_HEX, session_key):
        return None
    value = "%s.%s" % (session_key, _folded(raw_code) or "")
    kept = _encoded_name(name)
    if kept:
        value += "." + kept
    return _header(value, MAX_AGE_S)


def take_with_name(cookie_header, session_key):
    """(code, name, clear): the code and name kept for `session_key` ("" when
    none or kept for someone else), and the Set-Cookie value that ends the
    cookie, or None when the request carried none. A request that carries the
    cookie is the first showing of a refusal; a reload carries none."""
    value = auth.parse_cookies(cookie_header).get(COOKIE_NAME)
    if value is None:
        return "", "", None
    found = _VALUE_RE.fullmatch(value)
    mine = found is not None and found.group(1) == session_key
    code = (_folded(found.group(2)) or "") if mine else ""
    name = _decoded_name(found.group(3)) if mine else ""
    return code, name, _header("", 0)


def take(cookie_header, session_key):
    """(code, clear): the code kept for `session_key` ("" when none or kept
    for someone else), and the Set-Cookie value that ends the cookie, or None
    when the request carried none."""
    code, _name, clear = take_with_name(cookie_header, session_key)
    return code, clear
