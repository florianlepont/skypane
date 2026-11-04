"""Where the retired Health, Device and Update pages and their form
redirects land: the matching view of the Console Fleet page.

Every target is built from literals, a device id that already passed the
route's ownership gate, or an id read back from the request scope's own frame
list; no request text is echoed into a path or query.
"""
from urllib.parse import parse_qs, quote, urlsplit

from companion import device_scope
from companion.ui_base import DEVICE_ROUTE

FLEET = "/fleet"
FRAME_PARAM = "frame"
SYSTEM_QUERY = "?view=system"


def frame_url(frame_id=None):
    """The Fleet page with `frame_id` selected, or the Fleet page itself."""
    return FLEET if not frame_id else "%s?%s=%s" % (FLEET, FRAME_PARAM, quote(frame_id, safe=""))


def with_flash(url, flash_key):
    """`url` carrying the one-shot flash key `flash_key` (a registered
    constant, never request text)."""
    return "%s%sflash=%s" % (url, "&" if "?" in url else "?", quote(flash_key))


def health_target(device_id):
    """/health (platform wide) shows the System view; a frame's own health
    page shows that frame."""
    return frame_url(device_id) if device_id else FLEET + SYSTEM_QUERY


def settings_target(back, route, device):
    """Where a device-settings save returns to: the Fleet view of the frame
    for the Device form, `back` for every other form."""
    return frame_url(device.id) if route == DEVICE_ROUTE else back


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
