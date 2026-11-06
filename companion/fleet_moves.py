"""Where the retired Health, Device and Update pages and their form
redirects land: the matching view of the Console Fleet page.

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
SYSTEM_QUERY = "?view=system"


TAB_SETTINGS = "settings"


def frame_url(frame_id=None, tab=None):
    """The Fleet page with `frame_id` selected (on the phone sub-tab `tab`, a
    literal), or the Fleet page itself."""
    if not frame_id:
        return FLEET
    url = "%s?%s=%s" % (FLEET, FRAME_PARAM, quote(frame_id, safe=""))
    return url + "&tab=" + tab if tab else url


def with_flash(url, flash_key):
    """`url` carrying the one-shot flash key `flash_key` (a registered
    constant, never request text)."""
    return "%s%sflash=%s" % (url, "&" if "?" in url else "?", quote(flash_key))


def health_target(device_id, tab=None):
    """/health (platform wide) shows the System view; a frame's own health
    page shows that frame."""
    return frame_url(device_id, tab) if device_id else FLEET + SYSTEM_QUERY


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


def retired_frame_page(h, m):
    """303 target of the retired Health and Device pages: the Fleet view of the
    frame the request resolved to (`/devices/<id>/health`, or the frame named
    by `?frame=` among the caller's own), the System view when there is none."""
    wanted = parse_qs(m.query or "").get(FRAME_PARAM, [""])[0]
    own = {device.id for device in device_scope.current_devices()}
    frame_id = wanted if wanted in own else (m.device.id if m.device else None)
    tab = TAB_SETTINGS if m.path.rstrip("/").endswith(DEVICE_ROUTE) else None
    return h.redirect(_carried_flash(health_target(frame_id, tab), m.query))


def retired_update_page(h, m, serve):
    """The retired Update page: the Fleet view of the frame named by `?frame=`
    (one of the caller's own), else of the requested
    firmware type; a type with no frame is still served by `serve()`."""
    from companion.pages import update_page
    wanted = parse_qs(m.query or "").get(FRAME_PARAM, [""])[0]
    hardware_type = update_page.posted_type(h._requested_update_type())
    frame = wanted if wanted in {d.id for d in device_scope.current_devices()} else (
        frame_for_type(h, hardware_type) if hardware_type else None)
    if frame is None:
        return serve()
    return h.redirect(_carried_flash(frame_url(frame), m.query))
