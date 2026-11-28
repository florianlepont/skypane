# SPDX-License-Identifier: AGPL-3.0-only
"""The user-scope pairing routes: any signed-in person adds their own frame
with the code shown on the frame.

Security invariants (the shared ones live in companion/console_pairing.py):
- The owner of the new frame is the signed-in person, except that an
  administrator may choose any other active user. Only an administrator's
  form has an Owner field, and a submitted owner is read only when the
  signed-in role is administrator (checked on the server, never from the
  form): for everyone else it is ignored, so a tampered form cannot assign a
  frame to someone else. An administrator's owner must be an existing active
  user, else the form is refused with a field error. Registration by MAC or
  enrolment secret stays under the administrator-only Fleet routes.
- The same two throttles as the administrator route are checked before any
  code is evaluated, and every refusal gives the one identical answer.
- The optional frame name is validated with the rename rules before the code
  is evaluated (an invalid one is refused and nothing is claimed) and applied
  only after a successful claim; a refused code never stores it. It is echoed
  only into the name input, escaped and capped: from the view on the direct
  answers, from the pairing cookie on the redirect after a refused code.
- The typed code is never stored, audited, put in a URL or a flash. A refused
  code is answered with a redirect back to the form (Post/Redirect/Get, so a
  reload or Back never re-sends it); the code comes back into the field once
  from a two-minute cookie (companion/pair_code_cookie.py), never from the
  address.
- The audit entry is the pairing event with the signed-in person as actor.
"""
from urllib.parse import parse_qs

from companion import (
    access, console_flash, console_pairing, frame_rename, i18n, layout, pair_code_cookie,
    prefs, route_types)
from companion.pages import fleet_page, frame_name_page, pair_frame_page
from server import fleet_ops

PAIR_FRAME_ROUTE = pair_frame_page.PAIR_FRAME_ROUTE
ACCOUNT_ROUTE = "/account"
_MAX_ECHOED_CODE = 32
REFUSED_QUERY = "refused=1"
OWNER_QUERY = "owner"
FLEET_ROUTE = console_pairing.FLEET_PATH


def _respond(h, status, view, set_cookies=()):
    theme = h._resolved_ui_theme()
    page = layout.page_shell(
        title=i18n.t(pair_frame_page.PAIR_TITLE), active=layout.nav_slug(ACCOUNT_ROUTE),
        body=pair_frame_page.render(view), ui_theme=theme, health_alert=None)
    return h.send_html(status, page, set_cookies=set_cookies)


def _echoed(code):
    return code.strip().upper()[:_MAX_ECHOED_CODE]


def _typed_name(form):
    """The typed name with blanks collapsed ("" when blank)."""
    return " ".join(form.get(pair_frame_page.NAME_FIELD, "").split())


def _applied_name(typed):
    """(name to apply or "", error text or ""): a blank name is no name and no
    error; a non-blank one the rename rules refuse is an error."""
    if not typed:
        return "", ""
    name = frame_name_page.normalise_name(typed)
    if name is None:
        return "", i18n.t(frame_name_page.NAME_ERROR)
    return name, ""


def _is_admin(principal):
    return principal.role == access.ADMIN


def _owner_view(h, principal, selected=""):
    """The Owner choices of an administrator's page, with `selected` when it
    is one of them and else the administrator first; empty for anyone else."""
    if not _is_admin(principal):
        return {}
    owners = console_pairing.pairing_owners(h.args.state_dir, principal.user_id)
    chosen = selected if selected in {value for value, _label in owners} else (
        owners[0][0] if owners else "")
    return {"owners": owners, "owner_selected": chosen}


def handle_get(h, m):
    prefs.set_request_prefs(lang=h._lang_from_request())
    principal = h._safe_principal()
    if principal is None or principal.user_id is None:
        return h.send_html(404, h._not_found_page())
    # The kept code is put back once: the cookie is ended by this response.
    code, name, clear = pair_code_cookie.take_with_name(
        h.headers.get("Cookie"), console_pairing.session_key(h))
    error = ""
    # The refusal is shown with the code it blames, once: a reload carries no
    # cookie, so it shows a plain form instead of an error about an empty field.
    query = parse_qs(m.query or "")
    if query.get("refused") == ["1"] and clear:
        error = fleet_page.claim_refused_error()
    # The kept choice is only an id: it is checked against the list below.
    owner = (query.get(OWNER_QUERY) or [""])[0]
    return _respond(
        h, 200, pair_frame_page.PairView(
            code_value=code, code_error=error, name_value=name,
            **_owner_view(h, principal, owner)),
        set_cookies=(clear,) if clear else ())


def _refused_view(h, principal, code, owner_raw, typed_name="", **fields):
    return pair_frame_page.PairView(
        code_value=_echoed(code), name_value=typed_name[:pair_frame_page.MAX_NAME_CHARS],
        **dict(_owner_view(h, principal, owner_raw), **fields))


def _paired_frame(h, device_id, frame, name):
    """The frame's name for the flash once `name` (when given) is applied after
    the claim; a name that cannot be stored leaves the claimed name."""
    if name and frame_rename.store_name(h, device_id, name):
        return name
    return frame


def handle_post(h, m):
    # Before any text is built: the refusal and lockout toasts are translated
    # when they are created.
    prefs.set_request_prefs(lang=h._lang_from_request())
    principal = h._safe_principal()
    if principal is None or principal.user_id is None:
        return h.send_html(404, h._not_found_page())
    form = h.read_form()
    code = form.get(pair_frame_page.CODE_FIELD, "")
    # Anyone but an administrator is always the owner: the form's owner is
    # not even read for them.
    admin = _is_admin(principal)
    owner_raw = form.get(pair_frame_page.OWNER_FIELD, "") if admin else ""
    owner_id = console_pairing.owner_choice(owner_raw) if admin else principal.user_id
    typed = _typed_name(form)
    name, name_error = _applied_name(typed)
    code_error = "" if code.strip() else i18n.t(fleet_page.CLAIM_EMPTY_CODE)
    owner_error = i18n.t(fleet_page.CLAIM_EMPTY_OWNER) if owner_id is None else ""
    if code_error or owner_error or name_error:
        return _respond(h, 400, _refused_view(
            h, principal, code, owner_raw, typed, code_error=code_error,
            owner_error=owner_error, name_error=name_error))
    key = console_pairing.session_key(h)
    if console_pairing.is_locked(key):
        return _respond(h, 429, _refused_view(
            h, principal, code, owner_raw, typed, toast_html=console_pairing.docked_toast(
                "warning", fleet_page.CLAIM_THROTTLED_TITLE,
                fleet_page.CLAIM_THROTTLED_DETAIL)))
    if admin and not console_pairing.owner_is_active(h.args.state_dir, owner_id):
        return _respond(h, 400, _refused_view(
            h, principal, code, owner_raw, typed,
            owner_error=i18n.t(fleet_page.CLAIM_OWNER_GONE)))
    try:
        device_id, frame, email = console_pairing.claim_code(h, code, owner_id)
    except fleet_ops.ClaimRefused:
        console_pairing.record_refused_attempt(h, key)
        again = "%s?%s" % (PAIR_FRAME_ROUTE, REFUSED_QUERY)
        if admin:
            again += "&%s=%d" % (OWNER_QUERY, owner_id)
        return h.redirect(again, set_cookie=pair_code_cookie.keep_header(key, code, name))
    except fleet_ops.OwnerUnavailable:
        if admin:
            return _respond(h, 400, _refused_view(
                h, principal, code, owner_raw, typed,
                owner_error=i18n.t(fleet_page.CLAIM_OWNER_GONE)))
        return h.send_html(404, h._not_found_page())
    console_pairing.SESSION_THROTTLE.record_success(key)
    frame = _paired_frame(h, device_id, frame, name)
    if owner_id != principal.user_id:
        return h.redirect(FLEET_ROUTE, set_cookie=console_flash.queue_flash(
            console_pairing.FLASH_PAIRED, frame=frame, email=email))
    return h.redirect("/devices/%s/?flash=%s" % (device_id, pair_frame_page.FLASH_FRAME_PAIRED))


ROUTES = (
    route_types.Route(
        "GET", route_types.Exact(PAIR_FRAME_ROUTE), handle_get, route_types.SIGNED_IN),
    route_types.Route(
        "POST", route_types.Exact(PAIR_FRAME_ROUTE), handle_post,
        route_types.SIGNED_IN, csrf=True),
)
