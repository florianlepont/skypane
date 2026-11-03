"""Shared by the co-management browser tests: a seeded fleet whose "Kitchen"
frame is owned by a user with a long address and co-managed by another one,
plus the page-opening and overflow helpers both test modules use."""
import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import _set_ui_theme, VIEWPORT_MIN_SUPPORTED
from server import fleet_db

MIN_TAP_PX = 44
SUBPIXEL = 1.0

LONG_OWNER = "owner.with.a.very.long.address.x@example.test"
LONG_CO = "co.manager.with.a.very.long.address@example.test"
INVITED = "invited.person@example.test"
UNKNOWN = "nobody.knows.me@example.test"
SECOND_CO = "second.co@example.test"

class Rig:
    """A seeded fleet whose Orly-less "Kitchen" frame is owned by a user with a
    long address and co-managed by another one."""

    def __init__(self, server):
        self.server = server
        self.state_dir = server.state_dir
        self.seed = fx.seed_fleet(self.state_dir)
        conn = fleet_db.connect(self.state_dir)
        try:
            conn.execute(
                "UPDATE users SET email = ? WHERE id = ?",
                (LONG_OWNER, self.seed.owner_id))
            conn.commit()
            self.co_id = fleet_db.add_user(conn, LONG_CO, "user")
            fleet_db.add_co_manager(conn, self.seed.owned_id, self.co_id, None)
            fleet_db.add_user(conn, INVITED, "user")
        finally:
            conn.close()
        self.path = "/devices/%s/" % self.seed.owned_id

    def url(self, path=None):
        return self.server.base_url() + (path or self.path)

    def cookie(self, who):
        email = {"owner": LONG_OWNER, "co": LONG_CO}.get(who)
        if who == "admin":
            pair = fx.admin_cookie(self.state_dir)
        else:
            pair = fx.user_cookie(self.state_dir, email=email)
        name, value = pair.split("=", 1)
        return {"name": name, "value": value, "url": self.server.base_url(),
                "httpOnly": True, "sameSite": "Strict"}

    def members(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return sorted(
                row["email"] for row in conn.execute(
                    "SELECT u.email FROM device_co_managers c JOIN users u "
                    "ON u.id = c.user_id WHERE c.device_id = ?",
                    (self.seed.owned_id,)))
        finally:
            conn.close()


def _open(new_context, rig, who, path=None, lang="en", theme=None,
          viewport=VIEWPORT_MIN_SUPPORTED, **context_kwargs):
    context = new_context(viewport=viewport, **context_kwargs)
    context.add_cookies([
        rig.cookie(who),
        {"name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": rig.server.base_url()}])
    page = context.new_page()
    page.goto(rig.url(path))
    page.locator("main").wait_for(state="visible")
    if theme is not None:
        _set_ui_theme(page, theme)
    return context, page


def _no_sideways_scroll(page):
    return page.evaluate(
        "document.documentElement.scrollWidth <= document.documentElement.clientWidth")
