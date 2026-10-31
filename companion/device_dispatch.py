"""Device resolution for a request and the Referer-based redirect target,
moved out of `companion/app.py`'s `Handler`. Packaged as a
`DeviceDispatchMixin` `Handler` inherits, like `SignInMixin`.

Never imports `companion.app` (that would be a cycle). The few facts it
needs from the handler (`self.args`, `self.headers`, `self.redirect()`,
`self.send_html()`, `self._not_found_page()`, `self._safe_principal()`)
are provided by `Handler`.
"""
from urllib.parse import urlsplit

from companion import access, device_scope, layout, routes
from companion.sign_in import ACCOUNT_ROUTE
from server import history_db

# Pages that are never under a device prefix.
_GLOBAL_PAGES = (layout.UPDATE_ROUTE, ACCOUNT_ROUTE)


def _user_pages():
    """The device pages a user may open: nav tabs whose route is
    device-scoped and not admin-only."""
    pages = set()
    for route, _label in layout.NAV_TABS:
        found = routes.match("GET", route, "")
        if (found is not None and found[0].device_scoped
                and access.RANK[found[0].access.min_role] <= access.RANK[access.USER]):
            pages.add(route)
    return pages


class DeviceDispatchMixin:
    def _dispatch_for_device(self, route, route_match):
        """Resolve the request's device after the access decision, store it
        for this request, and run the handler inside one
        `history_db.connection_scope()` on that device's directory: every
        `history_db.open_db()` the handler makes on this thread shares one
        connection, opened lazily on the first database read. An unknown
        id is the 404 page, never the live frame.
        """
        root = self.args.state_dir
        principal = self._safe_principal()
        devices = device_scope.load_devices_for(root, principal)
        if route_match.device_id is None:
            # A user holds no un-prefixed device route (the gate refuses it),
            # so an empty list only reaches a global route: no device scope.
            device = devices[0] if devices else None
        else:
            device = device_scope.find_device(root, route_match.device_id)
            if device is None:
                return self.send_html(404, self._not_found_page())
        device_scope.set_request_scope(device, devices)
        if route.method == "GET" and route.device_scoped:
            location = device_scope.switch_target(
                route_match.path, route_match.query, devices)
            if location == device_scope.SWITCH_UNKNOWN:
                return self.send_html(404, self._not_found_page())
            if location is not None:
                return self.redirect(location)
        state_dir = root if device is None else device.state_dir
        with history_db.connection_scope(state_dir):
            return route.handler(self, route_match._replace(device=device))

    def _user_referring_tab(self, path):
        """A user's redirect target: the Referer's page of one of their own
        frames, else the first owned frame's Home, else the account page.
        Only a well-formed prefix naming a frame in this request's own
        device list and a page a user may open is honoured."""
        if path == ACCOUNT_ROUTE:
            return ACCOUNT_ROUTE
        owned = {device.id for device in device_scope.current_devices()}
        matched = routes.DEVICE_PREFIX_RE.match(path)
        if matched is not None and matched.group(1) in owned:
            page = matched.group(2) or layout.HOME_ROUTE
            if page in _user_pages():
                return "/devices/" + matched.group(1) + page
        for device in device_scope.current_devices():
            return device_scope.target_path(layout.HOME_ROUTE, device)
        return ACCOUNT_ROUTE

    def _referring_tab(self, any_device=False):
        """The page the Referer names, as a path to redirect to: a
        member of `layout.NAV_TABS` (an exact membership test) or the
        account page, under this request's device prefix for a device
        page, else Home. A signed-in `user` goes to their own landing
        page. A Referer under another device's prefix is moved to this
        device, unless `any_device` (the global theme and language
        switches) keeps the Referer's own well-formed prefix.
        """
        referer = self.headers.get("Referer", "")
        try:
            path = urlsplit(referer).path
        except ValueError:
            path = ""
        principal = self._safe_principal()
        if principal is not None and principal.role == access.USER:
            return self._user_referring_tab(path)
        prefix = ""
        matched = routes.DEVICE_PREFIX_RE.match(path)
        if matched is not None:
            prefix = "/devices/" + matched.group(1)
            path = matched.group(2) or layout.HOME_ROUTE
        allowed = {route for route, _ in layout.NAV_TABS} | {ACCOUNT_ROUTE}
        if path not in allowed:
            path = layout.HOME_ROUTE
        if path in _GLOBAL_PAGES:
            return path
        if not any_device or not prefix:
            prefix = device_scope.current_prefix()
        return prefix + path
