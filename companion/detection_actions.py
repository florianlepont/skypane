"""POST /detection: store a device's detection choice.

The route's access policy has already decided that the caller owns the
device (or is an admin) before this runs. Everything posted is untrusted:
only a fixed set of fields is read, each is stripped of control characters
and length-capped, and the airport and runway are validated against the
committed catalogue before anything is written. A rejected post re-renders
the page at 200 with the exact inline errors and writes nothing; a write
only ever targets the device the dispatcher bound to the request.
"""
from urllib.parse import quote

from companion import device_scope, flash
from companion.pages import detection_page
from server import detection

# Posted fields the handler reads; anything else is dropped.
FORM_FIELDS = ("action", "mode", "airport", "runway")
FIELD_CAP = 64


def clean_form(raw):
    """The known fields of `raw`, control characters removed, capped."""
    return {
        name: detection_page.clean_text(raw.get(name), FIELD_CAP)
        for name in FORM_FIELDS if name in raw}


def _runway_errors(form):
    """Field -> message for a runway-mode post; empty when it is valid."""
    airport = form.get("airport", "")
    if not airport:
        return {"airport": detection_page.ERROR_AIRPORT}
    if not form.get("runway"):
        return {"runway": detection_page.ERROR_RUNWAY_MISSING}
    try:
        detection.validate_runway_selection(airport, form["runway"])
    except ValueError as exc:
        code = exc.args[0] if exc.args else ""
        if code == "airport":
            return {"airport": detection_page.ERROR_AIRPORT}
        return {"runway": detection_page.ERROR_RUNWAY_UNKNOWN}
    return {}


def validate(form):
    """Field -> message for a post; empty when it can be stored."""
    if form.get("action") != detection_page.ACTION_SAVE_DETECTION:
        return {"mode": detection_page.ERROR_MODE}
    if form.get("mode") == detection_page.MODE_RUNWAY:
        return _runway_errors(form)
    return {"mode": detection_page.ERROR_MODE}


def _redirect_with(handler, flash_key):
    back = device_scope.scoped(detection_page.DETECTION_ROUTE)
    return handler.redirect("%s?flash=%s" % (back, quote(flash_key)))


def handle_post(handler, device):
    """Validate and store, then 303 back to the page; or re-render at 200
    with inline errors."""
    form = clean_form(handler.read_form())
    ctx = handler.page_context(device)
    errors = validate(form)
    if errors:
        body = detection_page.render(ctx, errors=errors, submitted=form)
        return handler.send_html(
            200, handler._page_shell_for(detection_page.DETECTION_ROUTE, body, ctx))
    try:
        detection.apply_runway_selection(ctx.state_dir, form["airport"], form["runway"])
    except OSError:
        return _redirect_with(handler, flash.FLASH_KEY_SAVE_FAILED)
    return _redirect_with(handler, flash.FLASH_KEY_DETECTION_SAVED)

