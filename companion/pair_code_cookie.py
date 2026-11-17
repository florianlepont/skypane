"""Keeps a refused pairing code for the next showing of the form.

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
"""
import re

from companion import auth

COOKIE_NAME = "sp_pair_code"
COOKIE_PATH = "/pair-frame"
MAX_AGE_S = 120
# The form's maxlength; a longer value is cut before it is stored.
MAX_CODE_CHARS = 12
_SESSION_KEY_HEX = 16
_CODE_RE = re.compile(r"[A-Z0-9-]{1,%d}" % MAX_CODE_CHARS)
_VALUE_RE = re.compile(r"([0-9a-f]{%d})\.([A-Z0-9-]*)" % _SESSION_KEY_HEX)


def _header(value, max_age):
    return "%s=%s; HttpOnly%s; SameSite=Strict; Path=%s; Max-Age=%d" % (
        COOKIE_NAME, value, auth.secure_cookie_flag(), COOKIE_PATH, max_age)


def _folded(raw):
    """The typed text as the form would hold it (upper case, no spaces, cut
    to the field's length), or None when it holds anything outside the code
    alphabet and hyphen."""
    text = "".join(raw.split()).upper()[:MAX_CODE_CHARS]
    return text if _CODE_RE.fullmatch(text) else None


def keep_header(session_key, raw_code):
    """The Set-Cookie value that keeps `raw_code` for `session_key`. A text that
    is not a plausible code is not stored: the cookie then holds the session
    alone, which only marks that a refusal is being shown (None when the
    session key itself is malformed)."""
    if not re.fullmatch("[0-9a-f]{%d}" % _SESSION_KEY_HEX, session_key):
        return None
    return _header("%s.%s" % (session_key, _folded(raw_code) or ""), MAX_AGE_S)


def take(cookie_header, session_key):
    """(code, clear): the code kept for `session_key` ("" when none or kept
    for someone else), and the Set-Cookie value that ends the cookie, or None
    when the request carried none. A request that carries the cookie is the
    first showing of a refusal; a reload carries none."""
    value = auth.parse_cookies(cookie_header).get(COOKIE_NAME)
    if value is None:
        return "", None
    found = _VALUE_RE.fullmatch(value)
    code = found.group(2) if found and found.group(1) == session_key else ""
    return (_folded(code) or ""), _header("", 0)
