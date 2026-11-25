"""Where the form redirects land: the matching view of the Console Fleet page
(a frame's Settings or Versions page), and where the Update page sends a
person who has a frame of the requested type.

Every target is built from literals, a device id that already passed the
route's ownership gate, or an id read back from the request scope's own frame
list; no request text is echoed into a path or query.
"""
import re
from urllib.parse import parse_qs, quote, urlsplit

from companion import device_scope
from companion.ui_base import DEVICE_ROUTE

FLEET = "/fleet"
FRAME_PARAM = "frame"


TAB_SETTINGS = "settings"
VIEW_VERSIONS = "versions"


def frame_url(frame_id=None, tab=None, view=None):
    """The Fleet page with `frame_id` selected (a phone brings the section `tab`
    into view; `view` names a detail page: both literals), or the Fleet page
    itself."""
    if not frame_id:
        return FLEET
    url = "%s?%s=%s" % (FLEET, FRAME_PARAM, quote(frame_id, safe=""))
    if view:
        url += "&view=" + view
    return url + "&tab=" + tab if tab else url


def with_flash(url, flash_key):
    """`url` carrying the one-shot flash key `flash_key` (a registered
    constant, never request text)."""
    return "%s%sflash=%s" % (url, "&" if "?" in url else "?", quote(flash_key))


def settings_target(back, route, device):
    """Where a device-settings save returns to: the Fleet view of the frame
    for the Device form, `back` for every other form."""
    return frame_url(device.id, TAB_SETTINGS) if route == DEVICE_ROUTE else back


def frame_for_type(h, hardware_type):
    """The id of the frame to select after an update action on
    `hardware_type`: the frame named by the same-site Referer when it is one
    of this principal's frames of that type, else the first such frame, else
    None."""
    devices = [
        device for device in device_scope.load_devices_for(
            h.args.state_dir, h._safe_principal())
        if device.hardware_type == hardware_type]
    wanted = parse_qs(urlsplit(h.headers.get("Referer") or "").query).get(FRAME_PARAM, [""])[0]
    for device in devices:
        if device.id == wanted:
            return device.id
    return devices[0].id if devices else None


_FLASH_KEY_RE = re.compile(r"\A[a-z0-9_-]{1,64}\Z")


def _carried_flash(url, query):
    """`url` with the one-shot `flash` key of `query` kept when it is shaped
    like a registered key (an unknown key shows no toast)."""
    values = parse_qs(query or "").get("flash", [""])
    return with_flash(url, values[0]) if _FLASH_KEY_RE.match(values[0]) else url


def retired_update_page(h, m, serve):
    """The Update page: the Versions page of the frame named by `?frame=`
    (one of the caller's own), else of the requested firmware type; a type
    with no frame is still served by `serve()`."""
    from companion.pages import update_page
    wanted = parse_qs(m.query or "").get(FRAME_PARAM, [""])[0]
    hardware_type = update_page.posted_type(h._requested_update_type())
    frame = wanted if wanted in {d.id for d in device_scope.current_devices()} else (
        frame_for_type(h, hardware_type) if hardware_type else None)
    if frame is None:
        return serve()
    return h.redirect(_carried_flash(frame_url(frame, view=VIEW_VERSIONS), m.query))
