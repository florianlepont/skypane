"""One-shot result toast carried across a post-redirect-get by a cookie.

The cookie holds display state only: a registered key and short string
parameters. It is attacker-settable, so rendering looks the key up in a
fixed registry (an unknown key renders nothing), fills parameters into the
registered text without any format-string evaluation, and leaves HTML
escaping to the toast renderer. Never put a code, guess, secret or MAC
secret in a parameter.
"""
import base64
import json
import re

from companion import auth, i18n, layout

COOKIE_NAME = "sp_flash"
MAX_AGE_S = 60
MAX_COOKIE_VALUE_BYTES = 1024
MAX_PARAMS = 8
MAX_PARAM_CHARS = 120

# key -> (tone, title Message, detail Message or None). Filled at import by
# the module that owns each key.
_REGISTRY = {}

_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")


def register_flash(key, tone, title_msg, detail_msg=None):
    """Declare a key. Title and detail are `i18n` Messages that may hold
    `{name}` placeholders, filled from the queued parameters.
    """
    _REGISTRY[key] = (tone, title_msg, detail_msg)


def _encode(payload):
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode(value):
    """The payload dict, or None for anything malformed or oversize."""
    if not value or len(value) > MAX_COOKIE_VALUE_BYTES:
        return None
    try:
        raw = base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
        payload = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _cookie_header(value, max_age):
    return "%s=%s; HttpOnly%s; SameSite=Strict; Path=/; Max-Age=%d" % (
        COOKIE_NAME, value, auth.secure_cookie_flag(), max_age)


def queue_flash(key, **params):
    """The Set-Cookie header value that queues `key` for the next page.
    Parameters are coerced to short strings; a value that would push the
    cookie past its size cap is dropped with the rest of the parameters.
    """
    clean = {
        str(name): str(value)[:MAX_PARAM_CHARS]
        for name, value in list(params.items())[:MAX_PARAMS]}
    encoded = _encode({"k": key, "p": clean})
    if len(encoded) > MAX_COOKIE_VALUE_BYTES:
        encoded = _encode({"k": key, "p": {}})
    return _cookie_header(encoded, MAX_AGE_S)


def clear_cookie_header():
    """The Set-Cookie header value that expires the flash cookie."""
    return _cookie_header("", 0)


def _fill(template, params):
    return _PLACEHOLDER_RE.sub(lambda found: params.get(found.group(1), ""), template)


def _toast_for(payload):
    """The toast markup for a decoded payload, or "" when its key is not
    registered.
    """
    entry = _REGISTRY.get(payload.get("k"))
    if entry is None:
        return ""
    tone, title_msg, detail_msg = entry
    raw_params = payload.get("p")
    params = {
        name: value for name, value in (
            raw_params.items() if isinstance(raw_params, dict) else ())
        if isinstance(name, str) and isinstance(value, str)}
    title = _fill(i18n.t(title_msg), params)
    detail = _fill(i18n.t(detail_msg), params) if detail_msg is not None else None
    return layout.toast_html(
        title, detail or None, tone=tone, dismiss_href=True)


def take_flash(cookie_header):
    """(toast markup, Set-Cookie value that clears the cookie) for a request
    carrying `cookie_header`. Markup is "" and the clear value None when no
    flash cookie came in; a cookie that cannot be rendered is still cleared.
    """
    value = auth.parse_cookies(cookie_header).get(COOKIE_NAME)
    if value is None:
        return "", None
    payload = _decode(value)
    markup = _toast_for(payload) if payload is not None else ""
    return markup, clear_cookie_header()
