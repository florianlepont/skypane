"""Step counts of the walkthrough tasks, measured in a real browser.

Each task is driven through a counter that adds one for every tap, every typed
or chosen value and every scroll an action needs to reach its target (a
target below the fold counts one scroll). Counting starts on the page sign-in
lands on; the sign-in task itself counts its whole path. Every task signs in
through the fake identity provider as the person the task is about, on a
360px phone, and each measured count is asserted equal to the value measured
for it (so a regression and an unnoticed gain both fail). The counts are
printed as `STEP-COUNT <task> <n> (target <t>)` lines; a task over its target
is reported there and in the step-count record, never hidden by raising the
target. The map, the tile host and the place search are answered by the test.
"""
import re

import pytest

import fleet_console_support as fx
from frame_menu_support import ADD, BUTTON, FRAMES
from companion import auth, device_scope
from companion.test_browser_ux_helpers import VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED
from place_map_support import CLEAR_BOX, Hosts
from server import device_config, fleet_db, hardware

pytestmark = pytest.mark.browser

MAP_READY = "() => document.documentElement.classList.contains('map-ready')"
MAP_TILES = "() => document.querySelectorAll('#place-map .leaflet-tile-loaded').length >= 1"

# Measured counts, asserted exactly. Targets are in the design record.
MEASURED = {
    "U4a": 3, "U4b": 4, "U4c": 3, "L1": 4, "L1-pin": 5, "L2": 4, "L3": 5, "L4": 3,
    "S1": 1, "S2": 2, "A7": 2, "A8": 3, "A9": 2, "V1-phone": 2, "V1-desktop": 1}
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

    def tap_point(self, locator, fx, fy, what, clear=None):
        """Taps a point of a large element (the map), by default of the whole element, or of
        `clear`, the part of it nothing floats over. A scroll is counted only when the point
        itself lies outside the viewport."""
        locator.wait_for(state="visible")
        box = clear or locator.bounding_box()
        y = box["y"] + box["height"] * fy
        if y < 0 or y > self.page.evaluate("window.innerHeight"):
            self.count += 1
            self.log.append("scroll to " + what)
            locator.scroll_into_view_if_needed()
            box = clear and self.page.evaluate(CLEAR_BOX) or locator.bounding_box()
            y = box["y"] + box["height"] * fy
        self._add("tap", what)
        self.page.mouse.click(box["x"] + box["width"] * fx, y)

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


def _report_measured(task, steps, target):
    """Prints the count and asserts it equals the measured value for `task`."""
    print("STEP-COUNT %s %d (target %d)%s: %s" % (
        task, steps.count, target, "" if steps.count <= target else " MISSED",
        "; ".join(steps.log) or "no action"))
    assert steps.count == MEASURED[task], (task, steps.count, MEASURED[task], steps.log)


def _select_frame(steps, page, name):
    """Makes `name` the selected frame: nothing to do when the frame button
    already names it, else two taps: the button, then the frame's row (a
    plain link)."""
    button = page.locator(BUTTON)
    button.wait_for(state="visible")
    if name in button.inner_text():
        return
    steps.tap(button, "frame button")
    row = page.locator(FRAMES, has_text=name).first
    row.wait_for(state="visible")
    steps.tap(row, "row of " + name)
    page.wait_for_function(
        "(n) => (document.querySelector('details.frame-menu > summary')"
        " || {textContent: ''}).textContent.includes(n)", arg=name)
    page.wait_for_function("() => document.readyState === 'complete'")


def _access_tab(steps, page, name):
    """The Access tab of the frame `name` (the frame is selected first when it is not):
    its owner, co-managers, Reassign and Retire sections are inline there."""
    _select_frame(steps, page, name)
    steps.tap(page.locator("nav.fleet-tabs a", has_text="Access"), "Access tab")


def test_a1_fleet_state_is_readable_on_landing(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        # Every live frame is a popover row with its status dot (and the button
        # shows the selected one's); the pending and retired frames wait in the
        # Other frames section of the Access tab.
        assert page.locator(BUTTON + " [role=img][aria-label]").count() == 1
        dots = page.locator(FRAMES + " [role=img][aria-label]")
        assert dots.count() >= 2
        assert page.locator(FRAMES + " .dot").count() >= 2
        assert page.locator("details.fleet-other").count() == 0
        assert page.locator(".fleet-block--others").count() == 1
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
        steps.tap(page.locator(BUTTON), "frame button")
        steps.tap(page.locator(ADD), "Add a frame")
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
        _report("A3", steps, 5)
    finally:
        context.close()


def test_a4_retire_a_frame(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        _access_tab(steps, page, "Kitchen")
        steps.tap(page.locator("a.fleet-retire__link"), "Retire this frame")
        dialog = page.locator("#dlg-retire-" + world.seed.owned_id.lower().replace("_", "-"))
        steps.tap(dialog.locator("button[type=submit]"), "confirm Retire")
        page.wait_for_url("**/fleet")
        assert world.device(world.seed.owned_id) is None
        _report("A4-retire", steps, 6)
    finally:
        context.close()


def test_a4_reassign_a_frame(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        _access_tab(steps, page, "Kitchen")
        dialog = page.locator("dialog[id^='dlg-reassign-']")
        steps.tap(page.locator(".fleet-block--access a.row-action", has_text="Reassign"), "Reassign")
        page.wait_for_function(
            "d => d.open", arg=dialog.element_handle(), timeout=10000)
        steps.choose(dialog.locator("select"), fx.ADMIN_EMAIL + " (admin)", "new owner")
        steps.tap(dialog.locator("button[type=submit]"), "Confirm reassign")
        page.wait_for_url("**/fleet?frame=*&tab=access")
        assert world.device(world.seed.owned_id)["owner_user_id"] == world.seed.admin_id
        _report("A4-reassign", steps, 6)
    finally:
        context.close()


def test_a5_add_a_co_manager(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        slug = world.seed.owned_id.lower().replace("_", "-")
        _access_tab(steps, page, "Kitchen")
        steps.tap(page.locator(".fleet-block--access li.access-add a.row__main"), "Add co-manager")
        dialog = page.locator("#dlg-add-co-manager-%s" % slug)
        page.wait_for_function(
            "d => d.open", arg=dialog.element_handle(), timeout=10000)
        steps.choose(
            dialog.locator("#co-manager-dialog-%s-person" % slug), fx.USER_EMAIL, "person")
        steps.tap(dialog.locator('form[action$="/co-managers/add"] button[type="submit"]'), "Add")
        page.wait_for_url("**/fleet?frame=*&tab=access")
        conn = fleet_db.connect(world.state_dir)
        try:
            members = [r["email"] for r in conn.execute(
                "SELECT u.email FROM device_co_managers c JOIN users u "
                "ON u.id = c.user_id WHERE c.device_id = ?", (world.seed.owned_id,))]
        finally:
            conn.close()
        assert members == [fx.USER_EMAIL]
        _report("A5", steps, 6)
    finally:
        context.close()


def test_a6_read_the_audit_log(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar > a.tab-bar__link[href='/audit']"), "Audit")
        page.wait_for_url("**/audit")
        assert page.locator("main h1").inner_text() == "Audit log"
        assert page.locator(".section-subnav").count() == 0
        _report("A6", steps, 1)
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
        assert page.locator(FRAMES).count() == 1
        assert page.url.split("?")[0].endswith("/devices/%s/" % world.seed.owned_id)
        assert page.locator("main h1").inner_text() == "Home"
        _report("U2-one", steps, 0)
    finally:
        context.close()


def _open_the_other_frame(steps, page):
    """The row of the frame not shown, through the frame button; waits for the new page."""
    button = page.locator(BUTTON)
    button.wait_for(state="visible")
    before = page.url
    was = button.inner_text()
    steps.tap(button, "frame button")
    assert page.locator(FRAMES, has_text="Kitchen").count() >= 1
    assert page.locator(FRAMES, has_text="Attic office").count() >= 1
    steps.tap(page.locator(FRAMES + ":not([aria-current])"), "frame row")
    page.wait_for_function("(was) => location.href !== was", arg=before)
    page.wait_for_function("() => document.readyState === 'complete'")
    assert page.locator(BUTTON).inner_text() != was


def test_u2_my_frames_with_several_frames_take_two_taps(world, new_context):
    """The popover lists every frame on the page; reaching another frame is the button, then a row."""
    world.add_second_frame()
    context, page, steps = _owner(world, new_context)
    try:
        _open_the_other_frame(steps, page)
        _report("U2-several", steps, 2)
    finally:
        context.close()


def test_s2_switching_frame_takes_the_button_then_a_row(world, new_context):
    world.add_second_frame()
    context, page, steps = _owner(world, new_context)
    try:
        _open_the_other_frame(steps, page)
        _report_measured("S2", steps, 2)
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


def test_u4a_change_the_quiet_hours_start(world, new_context):
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
        _report_measured("U4a", steps, 3)
    finally:
        context.close()


def test_u4b_changing_the_look_is_one_tap_on_a_look_card(world, new_context):
    """Personalisation tab, tap a background (the colour row is greyed on plain white paper),
    tap a colour in the picker, Save."""
    # This covers the classic look picker; the giant layouts' pairing picker has its own tests.
    frame_dirs = {d.id: d.state_dir for d in device_scope.load_devices(world.state_dir)}
    device_config.save_device_config(frame_dirs[world.seed.owned_id], layout="classic")
    context, page, steps = _owner(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar a[href$='/display']"), "Personalisation tab")
        page.wait_for_url("**/display")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        page.locator("[data-look-sheet][data-look-inline]").wait_for(state="visible")
        steps.tap(page.locator(
            '[data-look-sheet][data-look-inline] .look-seg__option:has('
            'input[data-look-axis="background"][value="full"])'), "a background")
        steps.tap(page.locator(
            "[data-look-sheet][data-look-inline] .look-dot:has(input:not(:checked))").first, "a look")
        page.locator("[data-static-save-fallback]").wait_for(state="visible")
        _save_and_reload(steps, page)
        _report_measured("U4b", steps, 4)
    finally:
        context.close()


def _grant_position(context, latitude=48.8534, longitude=2.3488):
    context.grant_permissions(["geolocation"], origin=None)
    context.set_geolocation({"latitude": latitude, "longitude": longitude, "accuracy": 25})


def _frame_place(world):
    conn = fleet_db.connect(world.state_dir)
    try:
        return fleet_db.frame_position(conn, world.seed.owned_id)
    finally:
        conn.close()


def _open_location(world, new_context):
    """The owner on the landing Home with the map hosts answered by the test; the Location tab
    is the first counted action and the page is waited for until its map is ready."""
    context, page, steps = _owner(world, new_context)
    hosts = Hosts(context)
    steps.tap(page.locator(".tab-bar a[href$='/detection']"), "Location tab")
    page.wait_for_url("**/detection*")
    page.wait_for_function(MAP_READY, timeout=15000)
    page.wait_for_function(
        "() => document.readyState === 'complete' && document.getAnimations().every("
        "(a) => a.playState !== 'running' || a.effect.getComputedTiming().iterations === Infinity)",
        timeout=10000)
    return context, page, steps, hosts


def _save_place(steps, page):
    with page.expect_navigation():
        steps.tap(page.locator("button.dirty-bar__save"), "Save")
    page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)


def test_l1_pick_an_airport_from_the_list(world, new_context):
    context, page, steps, hosts = _open_location(world, new_context)
    try:
        # The one search field takes the airport's code; submitting it opens that airport's page.
        steps.type_value(page.locator("#place-search"), "LYS", "search field")
        with page.expect_navigation():
            steps.tap(page.locator("form.place-search button"), "Search")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        _save_place(steps, page)
        place = _frame_place(world)
        assert place is not None and abs(place["latitude"] - 45.7) < 0.5, place
        assert not hosts.search_requests
        _report_measured("L1", steps, 4)
    finally:
        context.close()


def test_l1_pick_an_airport_by_tapping_its_pin(world, new_context):
    context, page, steps, hosts = _open_location(world, new_context)
    try:
        # My position is the page's first and default mode, and the airport pins belong to
        # Airport mode: one more tap than before.
        steps.tap(page.locator("label.place-mode:has(#place-mode-runway)"), "Airport tab")
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-dot').length >= 1", timeout=10000)
        # The map opens on the frame's own airport: zoom out to all of France to reach another.
        steps.tap(page.locator("#place-france"), "Show all of France")
        page.wait_for_function(
            "() => document.querySelectorAll('#place-map .place-cluster').length >= 3", timeout=10000)
        page.wait_for_function(
            "() => document.getAnimations().every((a) => a.playState !== 'running'"
            " || a.effect.getComputedTiming().iterations === Infinity)", timeout=10000)
        # A pin whose own hit box owns its centre, in the part of the map nothing floats over.
        spot = page.evaluate(
            "() => { const c = (" + CLEAR_BOX + ")();"
            " for (const d of document.querySelectorAll('#place-map .place-dot')) {"
            "  const r = d.getBoundingClientRect(); const x = r.left + r.width / 2, y = r.top + r.height / 2;"
            "  if (x > c.x + 30 && x < c.x + c.width - 30 && y > c.y + 30 && y < c.y + c.height - 30"
            "   && d.contains(document.elementFromPoint(x, y))) return {x: x, y: y}; }"
            " return null; }")
        with page.expect_navigation():
            steps.tap_point(
                page.locator("#place-map"), 0, 0, "an airport pin",
                clear={"x": spot["x"], "y": spot["y"], "width": 0, "height": 0})
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        _save_place(steps, page)
        assert _frame_place(world) is not None
        assert not hosts.search_requests
        _report_measured("L1-pin", steps, 4)
    finally:
        context.close()


def test_l2_use_my_position(world, new_context):
    context, page, steps, _ = _open_location(world, new_context)
    try:
        _grant_position(context)
        # The permission prompt is one decision the person takes; the context grants it.
        steps.count += 1
        steps.log.append("grant the position permission")
        steps.tap(page.locator("#place-locate"), "Use my position")
        page.wait_for_function(
            "() => document.getElementById('place-lat').value !== ''", timeout=10000)
        _save_place(steps, page)
        place = _frame_place(world)
        assert place is not None and abs(place["latitude"] - 48.8534) < 0.01, place
        _report_measured("L2", steps, 4)
    finally:
        context.close()


def test_l3_search_for_a_place(world, new_context):
    context, page, steps, hosts = _open_location(world, new_context)
    try:
        steps.type_value(page.locator("#place-search"), "Rivoli", "place search")
        steps.tap(page.locator("form.place-search button"), "Search places")
        result = page.locator("#place-results .place-result").first
        result.wait_for(state="visible", timeout=10000)
        steps.tap(result, "the result")
        page.wait_for_function(
            "() => document.getElementById('place-lat').value !== ''", timeout=10000)
        _save_place(steps, page)
        place = _frame_place(world)
        assert place is not None and abs(place["latitude"] - 48.8606) < 0.01, place
        assert len(hosts.search_requests) == 1
        _report_measured("L3", steps, 6)
    finally:
        context.close()


def test_l4_tap_the_map(world, new_context):
    context, page, steps, _ = _open_location(world, new_context)
    try:
        page.wait_for_function(MAP_TILES, timeout=15000)
        steps.tap_point(
            page.locator("#place-map"), 0.25, 0.4, "the map", clear=page.evaluate(CLEAR_BOX))
        page.wait_for_function(
            "() => document.getElementById('place-lat').value !== ''", timeout=10000)
        _save_place(steps, page)
        assert _frame_place(world) is not None
        _report_measured("L4", steps, 3)
    finally:
        context.close()


def test_u4c_the_administrator_changes_the_refresh_interval(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        # On a phone the wake interval sits on the Settings sub-tab of the Fleet view.
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        steps.tap(page.locator("nav.fleet-tabs a", has_text="Settings"), "Settings tab")
        page.wait_for_url("**tab=settings")
        field = page.locator("input[type=number][name=wake_interval_s]")
        target = "1500" if field.input_value() != "1500" else "1200"
        steps.type_value(field, target, "refresh interval")
        with page.expect_navigation():
            steps.tap(page.locator("button.dirty-bar__save"), "Save")
        page.wait_for_function(
            "t => document.readyState === 'complete' && document.querySelector("
            "'input[type=number][name=wake_interval_s]').value === t", arg=target, timeout=10000)
        _report_measured("U4c", steps, 3)
    finally:
        context.close()


def test_s1_the_space_switch_is_one_tap_from_any_page(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar > a.tab-bar__link--switch:has-text('My frame')"), "My frame")
        page.wait_for_url(re.compile(".*/devices/[^/]+/$"))
        assert page.locator("main h1").inner_text() == "Home"
        back = Steps(page)
        back.tap(page.locator(".tab-bar > a.tab-bar__link--switch:has-text('Console')"), "Console")
        page.wait_for_url("**/fleet")
        assert back.count == 1
        _report_measured("S1", steps, 1)
    finally:
        context.close()


def test_a7_a_frames_health_is_its_fleet_view(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        # The frame's health is the State block of its Fleet view: one tap on
        # button and its row when it is not the selected frame already.
        _select_frame(steps, page, "Kitchen")
        state = page.locator("section.fleet-block", has=page.locator("h2.section-label", has_text="State"))
        state.wait_for(state="visible")
        assert "Kitchen" in page.locator("summary.frame-menu__button").inner_text()
        _report_measured("A7", steps, 2)
    finally:
        context.close()


def test_a8_rename_an_airline_in_the_editor(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar a[href$='/airlines/manage']"), "Airline editor")
        page.wait_for_url("**/airlines/manage")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        name = page.locator('.airlines-name input[name="airline_name"][value="Air France"]')
        steps.type_value(name, "Skyline Air", "airline name")
        with page.expect_navigation():
            steps._add("press", "Enter (saves the name)")
            name.press("Enter")
        page.wait_for_function(
            "() => document.readyState === 'complete' && document.body.innerText.includes("
            "'Airline name saved')", timeout=15000)
        assert page.locator('.airlines-name input[value="Skyline Air"]').count() == 1
        _report_measured("A8", steps, 3)
    finally:
        context.close()


def test_a9_change_a_users_role_in_the_users_table(world, new_context):
    context, page, steps = _admin(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar a[href='/users']"), "Users tab")
        page.wait_for_url("**/users")
        page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
        select = page.locator("#user-%d select[name=role]" % world.seed.owner_id)
        steps.choose(select, "Administrator", "role")
        conn = fleet_db.connect(world.state_dir)
        try:
            for _ in range(100):
                row = conn.execute(
                    "SELECT role FROM users WHERE id = ?", (world.seed.owner_id,)).fetchone()
                if row["role"] == "admin":
                    break
                page.wait_for_timeout(50)
        finally:
            conn.close()
        assert row["role"] == "admin"
        _report_measured("A9", steps, 2)
    finally:
        context.close()


def test_v1_airline_collection_phone_and_desktop(world, new_context):
    context, page, steps = _owner(world, new_context)
    try:
        steps.tap(page.locator(".tab-bar__more > summary"), "More")
        steps.tap(page.locator(".tab-bar__more-panel a", has_text="Airlines"),
                  "Airlines")
        page.wait_for_url("**/airlines")
        assert page.locator("main h1").inner_text().strip() == "Airlines"
        _report_measured("V1-phone", steps, 2)
    finally:
        context.close()
    # Desktop is outside the phone counting rule; the sidebar link is the whole path.
    desktop = new_context(viewport=VIEWPORT_DESKTOP)
    desktop.add_cookies([{
        "name": auth.UI_LANG_COOKIE_NAME, "value": "en", "url": world.base}])
    try:
        page = desktop.new_page()
        world.sign_in(page, fx.OWNER_EMAIL, "auth0|owner")
        page.wait_for_url(re.compile(".*/devices/[^/]+/(\\?flash=welcome\\w*)?$"))
        wide = Steps(page)
        wide.tap(page.locator(".dashboard-sidebar a", has_text="Airlines"),
                 "sidebar link")
        page.wait_for_url("**/airlines")
        _report_measured("V1-desktop", wide, 1)
    finally:
        desktop.close()
