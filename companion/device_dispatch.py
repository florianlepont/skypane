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
        if route_match.device_id is None:
            devices = device_scope.load_devices(root)
            device = devices[0]
        else:
            device = device_scope.find_device(root, route_match.device_id)
            if device is None:
                return self.send_html(404, self._not_found_page())
            devices = device_scope.load_devices(root)
        device_scope.set_request_scope(device, devices)
        if route.method == "GET" and route.device_scoped:
            location = device_scope.switch_target(
                route_match.path, route_match.query, devices)
            if location == device_scope.SWITCH_UNKNOWN:
                return self.send_html(404, self._not_found_page())
            if location is not None:
                return self.redirect(location)
        with history_db.connection_scope(device.state_dir):
            return route.handler(self, route_match._replace(device=device))

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
            return access.home_for(principal)
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
