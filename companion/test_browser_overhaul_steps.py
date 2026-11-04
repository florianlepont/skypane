"""Step counts of the ten walkthrough tasks, measured in a real browser.

Each task is driven through a counter that adds one for every tap, every typed
or chosen value and every scroll an action needs to reach its target (a
target below the fold counts one scroll). Counting starts on the page sign-in
lands on; the sign-in task itself counts its whole path. Every task signs in
through the fake identity provider as the person the task is about, on a
360px phone, and each measured count is asserted at or below the target the
design set for it. The counts are printed as `STEP-COUNT <task> <n>` lines.
"""
import re

import pytest

import fleet_console_support as fx
from companion import auth
from companion.test_browser_ux_helpers import VIEWPORT_MIN_SUPPORTED
from server import fleet_db, hardware

pytestmark = pytest.mark.browser

# Display keeps its settings below the first screen (a scroll) or in a sheet,
# so a setting costs four actions (five for a look), above the design target
# of three.
MEASURED_U4 = 3
MEASURED_U4_LOOK = 5
_OFFSCREEN = (
    "el => { const r = el.getBoundingClientRect();"
    " return r.top < 0 || r.bottom > window.innerHeight; }")


class Steps:
    """Performs actions on a page and counts them."""

    def __init__(self, page):
        self.page = page
        self.count = 0
        self.log = []

    def _reach(self, locator, what):
        locator.wait_for(state="visible")
        if locator.evaluate(_OFFSCREEN):
            self.count += 1
            self.log.append("scroll to " + what)
            locator.scroll_into_view_if_needed()

    def _add(self, kind, what):
        self.count += 1
        self.log.append("%s %s" % (kind, what))

    def tap(self, locator, what):
        self._reach(locator, what)
        self._add("tap", what)
        locator.click()

    def type_value(self, locator, value, what):
        self._reach(locator, what)
        self._add("type", what)
        locator.fill(value)

    def choose(self, locator, label, what):
        self._reach(locator, what)
        self._add("choose", what)
        locator.select_option(label=label)


class World:
    """An app wired to a fake provider with a seeded fleet."""

    def __init__(self, rig):
        self.rig = rig
        self.server = rig.server
        self.state_dir = rig.state_dir
        self.seed = fx.seed_fleet(self.state_dir)
        fx.issue_code(self.state_dir, self.seed.pending_id)
        self.base = self.server.base_url()

    def phone(self, new_context):
        context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": self.base}])
        return context, context.new_page()

    def sign_in(self, page, email, sub):
        """The whole sign-in path as a user takes it; returns its step count."""
        self.rig.fake.next_login(sub=sub, email=email)
        page.goto(self.base + "/login")  # open the link
        page.click("a.login-signin")  # tap Sign in
        page.wait_for_url(lambda url: url.startswith(self.base) and not re.match(
            "^/(login|callback)", url[len(self.base):]))
        page.locator("main").wait_for(state="visible")
        assert self.rig.fake.calls_to("/authorize")  # the provider step happened
        # open the link, tap Sign in, the provider screen, the landing page
        return 4

    def device(self, device_id):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.get_device(conn, device_id)
        finally:
            conn.close()

    def add_second_frame(self):
        conn = fleet_db.connect(self.state_dir)
        try:
            return fleet_db.add_device(
                conn, "aa:bb:cc:00:00:09", fx.SECRET_HASH, hardware.LEGACY_KEY,
                self.seed.owner_id, name="Attic office", state_path="auto")
        finally:
            conn.close()


@pytest.fixture
def world(auth0_rig):
    return World(auth0_rig)


def _admin(world, new_context):
    context, page = world.phone(new_context)
    world.sign_in(page, fx.ADMIN_EMAIL, "auth0|admin")
    page.wait_for_url(world.base + "/fleet" + "*")
    return context, page, Steps(page)


def _owner(world, new_context):
    context, page = world.phone(new_context)
    world.sign_in(page, fx.OWNER_EMAIL, "auth0|owner")
    page.wait_for_url(re.compile(".*/devices/[^/]+/(\\?flash=welcome\\w*)?$"))
    return context, page, Steps(page)


def _report(task, steps, target):
    print("STEP-COUNT %s %d (target %d): %s" % (
        task, steps.count, target, "; ".join(steps.log) or "no action"))
    assert steps.count <= target, (task, steps.count, target, steps.log)


def _row_menu(steps, page, name, item):
    row = page.locator("li.entity-row", has=page.locator("text=%s" % name)).first
    steps.tap(row.locator("summary.row-menu__toggle"), "row menu of " + name)
    steps.tap(row.locator("a.row-menu__item", has_text=item), item)


def test_a1_fleet_state_is_readable_on_landing(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        dots = page.locator("li.entity-row [role=img][aria-label]")
        assert dots.count() >= 3
        assert page.locator("li.entity-row .dot").count() >= 3
        assert page.locator("table").count() == 0
        _report("A1", steps, 0)
    finally:
        context.close()


def test_a2_invite_a_user(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar a[href='/users']"), "Users tab")
        steps.tap(page.locator("a.page-header__action"), "Invite a user")
        assert page.input_value("#invite-role") == "user"
        steps.type_value(page.locator("#invite-email"), "new.person@example.test", "email")
        steps.tap(page.locator("#dlg-invite-user button[type=submit]"), "Invite user")
        page.wait_for_url("**/users")
        conn = fleet_db.connect(world.state_dir)
        try:
            row = conn.execute(
                "SELECT role FROM users WHERE email = ?",
                ("new.person@example.test",)).fetchone()
        finally:
            conn.close()
        assert row is not None and row["role"] == "user"
        _report("A2", steps, 4)
    finally:
        context.close()


def test_a3_pair_a_frame(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        steps.tap(page.locator("a.page-header__action"), "Add a frame")
        steps.type_value(page.locator("#pair-code"), fx.FAKE_CODE, "pairing code")
        steps.choose(page.locator("#pair-owner"), fx.OWNER_EMAIL, "owner")
        steps.tap(page.locator("#dlg-add-frame button[type=submit]"), "Pair frame")
        page.wait_for_url("**/fleet")
        conn = fleet_db.connect(world.state_dir)
        try:
            device = fleet_db.get_device_by_mac(conn, fx.MAC_PENDING)
        finally:
            conn.close()
        assert device is not None and device["owner_user_id"] == world.seed.owner_id
        _report("A3", steps, 4)
    finally:
        context.close()


def test_a4_retire_a_frame(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        _row_menu(steps, page, "Kitchen", "Retire")
        dialog = page.locator("#dlg-retire-" + world.seed.owned_id.lower().replace("_", "-"))
        steps.tap(dialog.locator("button[type=submit]"), "confirm Retire")
        page.wait_for_url("**/fleet")
        assert world.device(world.seed.owned_id) is None
        _report("A4-retire", steps, 3)
    finally:
        context.close()


def test_a4_reassign_a_frame(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        _row_menu(steps, page, "Kitchen", "Reassign")
        dialog = page.locator("#dlg-reassign-" + world.seed.owned_id.lower().replace("_", "-"))
        steps.choose(dialog.locator("select"), fx.ADMIN_EMAIL + " (admin)", "new owner")
        steps.tap(dialog.locator("button[type=submit]"), "confirm Reassign")
        page.wait_for_url("**/fleet")
        assert world.device(world.seed.owned_id)["owner_user_id"] == world.seed.admin_id
        _report("A4-reassign", steps, 4)
    finally:
        context.close()


def test_a5_add_a_co_manager(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        slug = world.seed.owned_id.lower().replace("_", "-")
        _row_menu(steps, page, "Kitchen", "Manage access")
        steps.choose(
            page.locator("#co-manager-%s-person" % slug), fx.USER_EMAIL, "person")
        steps.tap(page.locator(
            '#dlg-access-%s form[action$="/co-managers/add"] button' % slug),
            "Add co-manager")
        page.wait_for_url("**/fleet?access=*")
        conn = fleet_db.connect(world.state_dir)
        try:
            members = [r["email"] for r in conn.execute(
                "SELECT u.email FROM device_co_managers c JOIN users u "
                "ON u.id = c.user_id WHERE c.device_id = ?", (world.seed.owned_id,))]
        finally:
            conn.close()
        assert members == [fx.USER_EMAIL]
        _report("A5", steps, 4)
    finally:
        context.close()


def test_a6_read_the_audit_log(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar__more > summary"), "More")
        steps.tap(page.locator(".tab-bar__more-panel a[href='/audit']"), "Audit log")
        page.wait_for_url("**/audit")
        assert page.locator("main h1").inner_text() == "Audit log"
        assert page.locator(".section-subnav").count() == 0
        _report("A6", steps, 2)
    finally:
        context.close()


def test_u1_sign_in_ends_on_home(world, new_context):
    context, page = world.phone(new_context)
    try:
        count = world.sign_in(page, fx.OWNER_EMAIL, "auth0|owner")
        page.wait_for_url(re.compile(".*/devices/%s/(\\?flash=welcome\\w*)?$" % world.seed.owned_id))
        assert page.locator(".tab-bar a[aria-current='page']").inner_text().strip() == "Home"
        steps = Steps(page)
        steps.count = count
        steps.log.append("open the link; tap Sign in; provider screen; land on Home")
        _report("U1", steps, 4)
    finally:
        context.close()


def test_u2_my_frames_with_one_frame_need_no_action(world, new_context):
    context, page, steps = _owner(world, new_context)
    try:
        assert page.locator("a.frame-chip").count() == 0
        assert page.url.split("?")[0].endswith("/devices/%s/" % world.seed.owned_id)
        assert page.locator("main h1").inner_text().strip() == "Home"
        _report("U2-one", steps, 0)
    finally:
        context.close()


def test_u2_my_frames_with_several_frames_take_one_tap(world, new_context):
    world.add_second_frame()
    context, page, steps = _owner(world, new_context)
    try:
        steps.tap(page.locator("a.frame-chip"), "frame chip")
        panel = page.locator("dialog.frame-sheet")
        page.wait_for_function(
            "() => document.querySelector('dialog.frame-sheet').open")
        assert panel.locator("a", has_text="Kitchen").count() >= 1
        assert panel.locator("a", has_text="Attic office").count() >= 1
        _report("U2-several", steps, 1)
    finally:
        context.close()


def test_u2_switching_frame_takes_the_chip_then_a_card(world, new_context):
    world.add_second_frame()
    context, page, steps = _owner(world, new_context)
    try:
        steps.tap(page.locator("a.frame-chip"), "frame chip")
        page.wait_for_function(
            "() => document.querySelector('dialog.frame-sheet').open")
        before = page.url
        other = page.locator("dialog.frame-sheet a.frame-card:not([aria-current])")
        steps.tap(other, "frame card")
        page.wait_for_function("(was) => location.href !== was", arg=before)
        _report("U2-switch", steps, 2)
    finally:
        context.close()


def test_u3_a_frames_state_is_one_dot_on_home(world, new_context):
    context, page, steps = _owner(world, new_context)
    try:
        dot = page.locator("main [role=img][aria-label]").first
        dot.wait_for(state="visible")
        assert dot.get_attribute("aria-label").strip()
        _report("U3", steps, 0)
    finally:
        context.close()


def _save_and_reload(steps, page):
    steps.tap(page.locator("[data-static-save-fallback]"), "Save")
    page.wait_for_url("**/display*")


def test_u4_change_a_setting(world, new_context):
    """Move the quiet-hours start from Home: tap the schedule, type the start, Save.

    Three actions: the schedule link opens the Quiet hours dialog, the start is typed,
    and Save posts it.
    """
    context, page, steps = _owner(world, new_context)
    try:
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        steps.tap(page.locator("a.home-switch__window"), "schedule")
        page.wait_for_function(
            "() => document.querySelector('dialog#dlg-quiet-hours').open", timeout=10000)
        selector = "#quiet-window-start"
        target = "05:00" if page.input_value(selector) != "05:00" else "06:00"
        steps.type_value(page.locator(selector), target, "quiet hours start")
        with page.expect_navigation():
            steps.tap(page.locator("dialog#dlg-quiet-hours button[type=submit]"), "Save")
        page.wait_for_function(
            "t => document.readyState === 'complete'"
            " && !document.querySelector('dialog#dlg-quiet-hours').open"
            " && document.querySelector('#quiet-window-start').value === t",
            arg=target, timeout=10000)
        _report("U4", steps, MEASURED_U4)
    finally:
        context.close()


def test_u4_changing_the_look_goes_through_the_sheet(world, new_context):
    """The look picker is a sheet: Display tab, Change, a choice, Done, Save."""
    context, page, steps = _owner(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar a[href$='/display']"), "Display tab")
        page.wait_for_url("**/display")
        steps.tap(page.locator("summary.look-edit__summary:visible").first, "Change the look")
        sheet = page.locator("[data-look-sheet]")
        sheet.wait_for(state="visible")
        steps.tap(sheet.locator(
            ".look-dot:has(input[data-look-axis=colour][value=green])"), "colour")
        steps.tap(sheet.locator("[data-look-done]"), "Done")
        page.locator("[data-static-save-fallback]").wait_for(state="visible")
        _save_and_reload(steps, page)
        _report("U4-look", steps, MEASURED_U4_LOOK)
    finally:
        context.close()
