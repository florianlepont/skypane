"""The user-scope pairing routes: any signed-in person adds their own frame
with the code shown on the frame.

Security invariants (the shared ones live in companion/console_pairing.py):
- The owner of the new frame is always the signed-in person. The form has no
  owner field and a submitted one is ignored, so nobody can assign a frame to
  someone else here; registration by MAC or enrolment secret stays under the
  administrator-only Fleet routes.
- The same two throttles as the administrator route are checked before any
  code is evaluated, and every refusal gives the one identical answer.
- The typed code is never stored, audited, put in a URL or a flash. A refused
  code is answered with a redirect back to the form (Post/Redirect/Get, so a
  reload or Back never re-sends it) and the code is not echoed.
- The audit entry is the pairing event with the signed-in person as actor.
"""
from urllib.parse import parse_qs

from companion import (
    console_pairing, i18n, layout, prefs, route_types)
from companion.pages import fleet_page, pair_frame_page
from server import fleet_ops

PAIR_FRAME_ROUTE = pair_frame_page.PAIR_FRAME_ROUTE
ACCOUNT_ROUTE = "/account"
_MAX_ECHOED_CODE = 32
REFUSED_QUERY = "refused=1"


def _respond(h, status, view):
    theme = h._resolved_ui_theme()
    page = layout.page_shell(
        title=i18n.t(pair_frame_page.PAIR_TITLE), active=layout.nav_slug(ACCOUNT_ROUTE),
        body=pair_frame_page.render(view), ui_theme=theme, health_alert=None)
    return h.send_html(status, page)


def _echoed(code):
    return code.strip().upper()[:_MAX_ECHOED_CODE]


def handle_get(h, m):
    prefs.set_request_prefs(lang=h._lang_from_request())
    principal = h._safe_principal()
    if principal is None or principal.user_id is None:
        return h.send_html(404, h._not_found_page())
    if parse_qs(m.query or "").get("refused") == ["1"]:
        return _respond(h, 200, pair_frame_page.PairView(
            code_error=fleet_page.claim_refused_error()))
    return _respond(h, 200, pair_frame_page.PairView())


def handle_post(h, m):
    # Before any text is built: the refusal and lockout toasts are translated
    # when they are created.
    prefs.set_request_prefs(lang=h._lang_from_request())
    principal = h._safe_principal()
    if principal is None or principal.user_id is None:
        return h.send_html(404, h._not_found_page())
    code = h.read_form().get(pair_frame_page.CODE_FIELD, "")
    if not code.strip():
        return _respond(h, 400, pair_frame_page.PairView(
            code_error=i18n.t(fleet_page.CLAIM_EMPTY_CODE)))
    key = console_pairing.session_key(h)
    if console_pairing.is_locked(key):
        return _respond(h, 429, pair_frame_page.PairView(
            code_value=_echoed(code), toast_html=console_pairing.docked_toast(
                "warning", fleet_page.CLAIM_THROTTLED_TITLE,
                fleet_page.CLAIM_THROTTLED_DETAIL)))
    try:
        device_id, _name, _email = console_pairing.claim_code(h, code, principal.user_id)
    except fleet_ops.ClaimRefused:
        console_pairing.record_refused_attempt(h, key)
        return h.redirect("%s?%s" % (PAIR_FRAME_ROUTE, REFUSED_QUERY))
    except fleet_ops.OwnerUnavailable:
        return h.send_html(404, h._not_found_page())
    console_pairing.SESSION_THROTTLE.record_success(key)
    return h.redirect("/devices/%s/?flash=%s" % (device_id, pair_frame_page.FLASH_FRAME_PAIRED))


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(PAIR_FRAME_ROUTE), handle_get, route_types.SIGNED_IN),
    route_types.Route(
        "POST", route_types.Exact(PAIR_FRAME_ROUTE), handle_post,
        route_types.SIGNED_IN, csrf=True),
)
