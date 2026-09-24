#!/usr/bin/env python3
"""Part 02 of `companion/test_browser_ux.py` (33-22-PLAN.md, TST-11), the
second of the browser_ux chain's four migration plans (33-21..33-24).

Covers the original file's check() calls #19-#37: both `<dialog>`s'
entrance/exit motion, the live theme preview's crossfade, the image-hold
skeletons, the login card's layout and show-password toggle, the login
lockout countdown, the nav-status reminder's line-breaking, the mobile
nav's close consistency, the restored dirty bar's own clearance geometry,
the Health refresh loop's failure/recovery pill, four B11-class overflow
sweeps (Home, the recent-flight callsign column, Health's disclosure-
gated tables, every `<details>` on every page), the cross-document view-
transition name uniqueness and its reduced-motion opt-out, and the
Health freshness line's live-tab ticking, hidden-tab idling and no-JS
floor.

Every test below drives a real headless Chromium against a real
`companion/app.py` subprocess, through the guarded `page`/`new_context`
fixtures (`companion/conftest.py`), and never constructs or navigates to
any URL outside `server.base_url()` — a `127.0.0.1:<ephemeral-port>`
origin the guarded fixture itself created. A missing/unlaunchable
Chromium is a hard failure under CI / `SKYPANE_REQUIRE_BROWSER=1` (the
`browser` fixture override in `companion/conftest.py`), never a silent
skip.

Read-only checks (none below saves a real setting through Enregistrer;
the one that reveals the dirty bar never clicks it) share one
module-scoped, read-only `server` fixture (33-MIGRATION-RULES.md section
2). The login-lockout check drives the process-global LoginThrottle to
its limit, which would lock out every other check sharing that
subprocess for the rest of the module's run, so it alone gets its own
function-scoped `make_app_server` server.

Loops the original checks ran with no cross-iteration comparison (each
route/width/language/motion-mode combination independently asserted, in
its own context) are converted to `@pytest.mark.parametrize` — the
dirty-bar clearance check, the two-route dialog check, the recent-flight
starvation sweep, the Home overflow sweep, the every-disclosure sweep,
the reduced-motion opt-out check and the no-JS freshness check. The
nav-status check stays a single test: it is a linear three-phase
procedure (a 240px sidebar read, then a 390px dropdown read in the SAME
context, then a Home-specific read in that same context again), not a
loop over independent scenarios.
"""
import pytest

from companion import auth, layout
from companion.pages import history_page
from companion_app_server import TEST_PASSWORD
from server import device_config
from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    VIEWPORT_WIDTHS_ALL, VIEWPORT_WIDTHS_RESPONSIVE,
    VIEW_TRANSITION_NAMES, VIEW_TRANSITION_ROUTES,
    _click_control, _login, _no_js_page, _wait_for_bar, seed_state_dir,
)

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def server(module_app_server_factory):
    """The shared, read-only 22-AUDIT.md-methodology fixture every read-only
    check in this module measures against — module-scoped because none of
    them saves a real setting through Enregistrer.
    """
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)


# ===========================================================================
# 23-10-PLAN.md Task 2 (D3/CFG-32, T-23-36): the panel-lookup dialog's own
# entrance/exit motion, on both routes that trigger it. Each route is
# independently asserted with no comparison across the two, so the
# original two-tuple loop is parametrized.
# ===========================================================================

@pytest.mark.parametrize(
    "route,trigger_sel", [
        ("/history", "[data-view-panel-src]"),
        ("/airlines", "[data-view-panel-src]"),
    ], ids=["history", "airlines"])
def test_both_dialogs_fade_in_and_leave_nothing_behind(new_context, server, route, trigger_sel):
    """both <dialog>s FADE AND ZOOM in — measured mid-flight, two frames after the
    trigger, on History and on the Airlines gallery — settle fully opaque at
    their own scale, and on close() reach display:none with a zero-area box and
    a viewport-centre hit test that lands OUTSIDE them, with no settle wait at
    all, so an invisible click-swallowing sheet cannot hide behind one
    (D3/CFG-32, T-23-36, 23-10-PLAN.md Task 2)"""
    # 23-10-PLAN.md Task 2 (D3/CFG-32, T-23-36). The entrance is a
    # stylesheet fact a source scan can read; the CLOSE is not. A
    # <dialog> that fades out but never reaches `display: none` is an
    # invisible sheet in the top layer that swallows every click on the
    # page beneath it, and the only instrument that can see that is a
    # real hit test. So this check does both: the opening is sampled
    # mid-flight (a real transition is running, opacity below 1 two
    # frames after the trigger), and the close is hit-tested at the
    # viewport centre.
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + route)
        page.wait_for_load_state("networkidle")
        if page.query_selector(trigger_sel) is None:
            raise AssertionError(
                "expected %s to render at least one %s dialog trigger"
                % (route, trigger_sel))
        opening = page.evaluate(
            "sel => new Promise(resolve => {"
            "const d = document.getElementById('panel-lookup-dialog');"
            "if (!d) { resolve({error: 'no dialog'}); return; }"
            "document.querySelector(sel).click();"
            "requestAnimationFrame(() => requestAnimationFrame(() => {"
            "const s = getComputedStyle(d);"
            "resolve({open: d.open, opacity: parseFloat(s.opacity),"
            " dur: s.transitionDuration, props: s.transitionProperty,"
            " transform: s.transform});"
            "}));"
            "})", trigger_sel)
        if opening.get("error"):
            raise AssertionError("%s: %s" % (route, opening["error"]))
        if not opening["open"]:
            raise AssertionError(
                "%s: expected the trigger to open the dialog" % (route,))
        if not (0 <= opening["opacity"] < 1):
            raise AssertionError(
                "%s: expected the dialog to be MID-FADE two frames after "
                "opening (D3: both dialogs fade and zoom in via "
                "@starting-style), got opacity %r with transition %r on %r "
                "— a dialog already fully opaque two frames in is the "
                "instant open this plan replaces"
                % (route, opening["opacity"], opening["dur"], opening["props"]))
        page.wait_for_timeout(600)
        settled = page.evaluate(
            "() => { const d ="
            " document.getElementById('panel-lookup-dialog');"
            "const s = getComputedStyle(d);"
            "return {opacity: parseFloat(s.opacity), transform: s.transform,"
            " display: s.display}; }")
        if settled["opacity"] != 1:
            raise AssertionError(
                "%s: expected the dialog to SETTLE fully opaque, got %r"
                % (route, settled))
        if settled["transform"] not in ("none", "matrix(1, 0, 0, 1, 0, 0)"):
            raise AssertionError(
                "%s: expected the dialog to settle at its own scale, got %r"
                % (route, settled["transform"]))

        page.click("[data-view-panel-close]")
        # Deliberately NO settle wait here: the whole point is that the
        # close is over the instant it happens. A wait would hide
        # exactly the defect this measures.
        after = page.evaluate(
            "() => { const d ="
            " document.getElementById('panel-lookup-dialog');"
            "const r = d.getBoundingClientRect();"
            "const hit = document.elementFromPoint("
            "Math.round(innerWidth / 2), Math.round(innerHeight / 2));"
            "return {open: d.open, display: getComputedStyle(d).display,"
            " area: r.width * r.height,"
            " hit: !!(hit && d.contains(hit)),"
            " hitTag: hit ? hit.tagName + '.' + hit.className : null}; }")
        if after["open"]:
            raise AssertionError(
                "%s: the dialog is still open after close()" % (route,))
        if after["display"] != "none":
            raise AssertionError(
                "%s: expected the closed dialog's display to be 'none', got %r "
                "— a dialog left displayed after close() is an invisible sheet "
                "over the page (T-23-36) (full read %r)"
                % (route, after["display"], after))
        if after["area"] != 0:
            raise AssertionError(
                "%s: the closed dialog still occupies %r px2 — %r"
                % (route, after["area"], after))
        if after["hit"]:
            raise AssertionError(
                "%s: a hit test at the viewport centre still lands INSIDE "
                "the closed dialog (%r) — every click on the page beneath it "
                "is being swallowed (T-23-36)" % (route, after["hitTag"]))
    finally:
        context.close()


def test_the_live_preview_crossfade_settles_correct_through_its_own_listener(new_context, server):
    """the live theme preview CROSSFADES - proven by the opacity transition the
    browser CREATES on the preview image, caught as a transitionrun event rather
    than sampled at a guessed instant, because every other assertion here is
    satisfied by the cut this plan replaces - and settles on the theme that was
    actually selected, fully opaque rather than stuck mid-fade, driven entirely by
    theme-preview.js's OWN delegated listener with no save and no dirty-state.js
    involvement at all (D3/CFG-32, T-23-38, 23-10-PLAN.md Task 2; the Cancel half
    retired by 27-04-PLAN.md Task 2, CFG-63; re-pointed to details.usage-row/
    .palette-chip by 30-08-PLAN.md Task 2, CFG-85)"""
    # 23-10-PLAN.md Task 2 (D3/CFG-32, T-23-38). The stylesheet and the
    # script are each individually correct; this asserts the SETTLED
    # state after the transition, never a frame during it. The live
    # preview follows a chip selection through theme-preview.js's OWN
    # delegated listener on the card, with dirty-state.js never in the
    # loop at all — this check drives no Cancel and no save of any kind.
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, server.base_url())
        page.goto(server.base_url() + "/display")
        page.wait_for_load_state("networkidle")
        read = (
            "() => { const i ="
            " document.querySelector('.theme-live-preview__image');"
            "return {src: i.getAttribute('src'),"
            " opacity: parseFloat(getComputedStyle(i).opacity)}; }")
        page.evaluate(read)  # pre-click baseline; no longer compared (Cancel retired)
        # 30-08-PLAN.md Task 2 (CFG-85): re-pointed from the retired
        # [data-usage-panel-target]/label.theme-chip departures panel to
        # details.usage-row[data-usage="departures"]/label.palette-chip —
        # the crossfade mechanism itself (theme-preview.js's
        # applyPreviewSrc()/FADE_CLASS) is unchanged by the rebuild, so
        # every OTHER clause below is unchanged too.
        target = page.evaluate(
            "() => { const row = document.querySelector("
            "'details.usage-row[data-usage=\"departures\"]');"
            "const chip = [...row.querySelectorAll('label.palette-chip')].find("
            "c => c.getAttribute('data-preview-src')"
            " && !c.querySelector('input[type=radio]').checked);"
            "return chip ? {value: chip.querySelector("
            "'input[type=radio]').value,"
            " src: chip.getAttribute('data-preview-src')} : null; }")
        if not target:
            raise AssertionError("found no unchecked departures palette chip to click")
        # Click, then WAIT FOR THE TRANSITION ITSELF to be created rather
        # than sampling at a guessed instant. `transitionrun` fires when
        # the browser CREATES the transition, before any delay and
        # before the first painted step, so it is independent of frame
        # timing — while a cut creates no transition at all and fires
        # nothing. The listener is on `document` in the CAPTURE phase
        # because the crossfade swaps layer elements: a listener bound
        # to whichever image existed before the click can be watching
        # the wrong one.
        mid = page.evaluate(
            "sel => new Promise(resolve => {"
            "let ran = null;"
            "const onRun = e => {"
            "if (ran) return;"
            "if (e.propertyName !== 'opacity') return;"
            "if (!(e.target instanceof Element)) return;"
            "if (!e.target.matches('.theme-live-preview__image')) return;"
            "const s = getComputedStyle(e.target);"
            "ran = {opacity: parseFloat(s.opacity), dur: s.transitionDuration,"
            " props: s.transitionProperty};"
            "};"
            "document.addEventListener('transitionrun', onRun, true);"
            "document.querySelector(sel).click();"
            "setTimeout(() => {"
            "document.removeEventListener('transitionrun', onRun, true);"
            "const i = document.querySelector('.theme-live-preview__image');"
            "const s = i ? getComputedStyle(i) : null;"
            "resolve({ran: ran, dur: s && s.transitionDuration,"
            " props: s && s.transitionProperty});"
            "}, 400);"
            "})",
            'details.usage-row[data-usage="departures"] '
            'label.palette-chip input[type=radio][value="%s"]' % target["value"])
        if not mid["ran"]:
            raise AssertionError(
                "expected the live preview to CROSSFADE — no opacity transition "
                "was created on .theme-live-preview__image within 400ms of the "
                "chip being selected (the preview's own computed transition is "
                "%r on %r) — a preview that changes with no transition at all is "
                "the CUT this plan replaces, and every other assertion in this "
                "check is satisfied by that cut"
                % (mid["dur"], mid["props"]))
        page.wait_for_timeout(900)
        settled = page.evaluate(read)
        if settled["src"] != target["src"]:
            raise AssertionError(
                "the crossfade settled on the WRONG theme: the preview reads %r "
                "after selecting the chip whose own data-preview-src is %r "
                "(T-23-38)" % (settled["src"], target["src"]))
        if settled["opacity"] != 1:
            raise AssertionError(
                "the crossfade settled INVISIBLE (opacity %r) — a fade-out with "
                "no fade back in is worse than the cut it replaced"
                % (settled["opacity"],))
    finally:
        context.close()


def test_images_hold_their_place_before_they_arrive(new_context, server):
    """Home's frame picture and a theme chip's preview band each reserve their FINAL
    box before their image arrives — the real request is HELD, the real box is
    measured unloaded (and asserted to be a real box, not a collapsed one, with
    a skeleton painted in it), the request is let through, and the box after the
    decoded image lands is plain-equal to the box before it, at the 360px
    contract floor and at 1280px (D3/CFG-32, T-23-39, 23-10-PLAN.md Task 3)"""
    # 23-10-PLAN.md Task 3 (D3/CFG-32, T-23-39). The only assertion that
    # proves a skeleton did what it was for: the box BEFORE the image
    # resource resolves equals the box AFTER, measured at the 360px
    # contract floor and at 1280px.
    #
    # The image request is HELD by a route handler rather than raced
    # against — "measure quickly and hope" is how this kind of check
    # passes on a fast machine and proves nothing. Nothing is faked: the
    # real request is paused, the real boxes are read, the real request
    # is then let through, and the real decoded image is measured.
    surfaces = (
        ("/", ".preview-frame", ".preview-frame__image", "**/gallery/**", 100, ()),
        # 30-08-PLAN.md Task 2 (CFG-85): the accordion's own
        # .palette-chip renders NO <img> of any kind (a CSS-drawn shape
        # only), so the ONE surviving .theme-chip/.theme-chip__preview
        # pair on Display now lives inside the rules row's own nested,
        # closed-by-default rule-add disclosure — opened here before
        # measuring. 30, because that chip is the COMPACT variant, whose
        # band is 36px rather than the base 56px — measured, not assumed.
        ("/display", ".theme-chip", ".theme-chip__preview",
         "**/theme-preview/**", 30,
         ('details.usage-row[data-usage="rules"] > summary',
          '.rule-add > summary')),
    )
    for width in (VIEWPORT_MIN_SUPPORTED["width"], VIEWPORT_DESKTOP["width"]):
        for route_path, box_sel, img_sel, url_glob, floor, openers in surfaces:
            context = new_context(
                viewport={"width": width, "height": VIEWPORT_DESKTOP["height"]})
            try:
                page = context.new_page()
                _login(page, server.base_url())
                held = []
                page.route(url_glob, lambda route: held.append(route))
                page.goto(server.base_url() + route_path, wait_until="domcontentloaded")
                for opener in openers:
                    page.click(opener)
                page.wait_for_selector(img_sel, state="attached")
                page.wait_for_timeout(400)
                read = (
                    "sels => { const b = document.querySelector(sels[0]);"
                    "const i = document.querySelector(sels[1]);"
                    "if (!b || !i) return null;"
                    "const r = e => { const x = e.getBoundingClientRect();"
                    "return [Math.round(x.width * 100) / 100,"
                    " Math.round(x.height * 100) / 100]; };"
                    "return {box: r(b), img: r(i),"
                    " skeleton: getComputedStyle(i).backgroundImage,"
                    " complete: i.complete, nat: [i.naturalWidth,"
                    " i.naturalHeight]}; }")
                before = page.evaluate(read, [box_sel, img_sel])
                if before is None:
                    raise AssertionError(
                        "%s at %dpx renders no %s/%s to measure"
                        % (route_path, width, box_sel, img_sel))
                if before["nat"][0]:
                    raise AssertionError(
                        "%s at %dpx: the image resolved before it could be "
                        "measured unloaded — the hold did not hold (%r)"
                        % (route_path, width, before))
                if before["img"][1] < floor:
                    raise AssertionError(
                        "%s at %dpx: the UNLOADED image reserves only %r — a "
                        "collapsed box is the layout shift a skeleton exists to "
                        "prevent, and it would make the equality below pass for "
                        "the wrong reason (T-23-39)"
                        % (route_path, width, before["img"]))
                if before["skeleton"] == "none":
                    raise AssertionError(
                        "%s at %dpx: %s paints no skeleton at all while its "
                        "image is still coming — the reserved box is correct and "
                        "completely blank"
                        % (route_path, width, img_sel))
                for route_obj in held:
                    route_obj.continue_()
                page.unroute(url_glob)
                page.wait_for_function(
                    "sel => { const i = document.querySelector(sel);"
                    " return i.complete && i.naturalWidth > 0; }",
                    arg=img_sel, timeout=5000)
                page.wait_for_timeout(200)
                after = page.evaluate(read, [box_sel, img_sel])
                if before["box"] != after["box"]:
                    raise AssertionError(
                        "%s at %dpx: %s moved when its image arrived — %r before, "
                        "%r after. A skeleton whose box differs from its image's "
                        "box IS the layout shift it was added to prevent "
                        "(T-23-39)"
                        % (route_path, width, box_sel, before["box"], after["box"]))
                if before["img"] != after["img"]:
                    raise AssertionError(
                        "%s at %dpx: %s itself resized when it arrived — %r "
                        "before, %r after (T-23-39)"
                        % (route_path, width, img_sel, before["img"], after["img"]))
            finally:
                context.close()


# 30-03-PLAN.md Task 3 (CFG-85): the check that used to live here —
# _the_no_js_floor_holds_for_both_settings_pages — is RETIRED and
# LEDGERED to 30-08 (see the ledger fragment's own R/S-coded row for it).
# A REQUIREMENT-TEXT VS. APPROVED-DESIGN DISCREPANCY was recorded against
# it: CFG-85's own requirement text includes "every row open with
# scripts blocked", but 30-UI-SPEC.md's developer-approved accordion is a
# native `<details name="aspect-rows">` group, mutually exclusive by
# construction — 30-08's own replacement proves the PROPERTY CFG-85 is
# actually protecting (no control unreachable/unsaveable with scripts
# blocked) more strongly than a visible stack ever could.


# ===========================================================================
# 22-13-PLAN.md Task 3 (X3): the login card's own layout and its
# show-password toggle.
# ===========================================================================

def test_login_card_stacks_at_both_widths(new_context, server):
    """at 390px and at 1280px the login card's field and primary are stacked, the
    same width, filling the card's content column, both 44px tall, sharing one
    radius and separated by the one 16px token — never a 225x44 field beside a
    68x30 button, and never glued at a 0px gap (X3, 22-13-PLAN.md Task 3)"""
    # X3's measurement, re-taken by a real layout engine at both ends of
    # the range the audit measured: desktop was a 225x44 r8 field beside
    # a 68x30 r6 button sitting 7px lower, and at 390px the field kept
    # 225 of 278px with the button glued underneath at a 0px gap.
    for width in (390, 1280):
        context = new_context(viewport={"width": width, "height": 844})
        try:
            page = context.new_page()
            page.goto(server.base_url() + "/login")
            field = page.locator(".login-form__input").bounding_box()
            primary = page.locator('.login-card button[type="submit"]').bounding_box()
            form = page.locator(".login-form").bounding_box()
            if not field or not primary or not form:
                raise AssertionError(
                    "%dpx: expected both controls to be laid out" % width)
            if abs(field["width"] - primary["width"]) > 1:
                raise AssertionError(
                    "%dpx: the field and the primary must be the same width, "
                    "measured %.1f vs %.1f" % (width, field["width"], primary["width"]))
            if abs(field["width"] - form["width"]) > 1:
                raise AssertionError(
                    "%dpx: both controls must fill the card's content column "
                    "(%.1f), the field measured %.1f"
                    % (width, form["width"], field["width"]))
            for name, box in (("field", field), ("primary", primary)):
                if abs(box["height"] - 44) > 0.5:
                    raise AssertionError(
                        "%dpx: the %s must be 44px tall, measured %.1f"
                        % (width, name, box["height"]))
            gap = primary["y"] - (field["y"] + field["height"])
            if gap <= 0:
                raise AssertionError(
                    "%dpx: the two controls must be separated, measured a "
                    "%.1fpx gap" % (width, gap))
            if abs(gap - 16) > 1:
                raise AssertionError(
                    "%dpx: the gap must be the one medium spacing token "
                    "(16px), measured %.1f" % (width, gap))
            # Same radius as well as same height — the other half of C4's
            # composition rule, which a bounding box cannot see.
            radii = page.evaluate(
                "() => [getComputedStyle(document.querySelector("
                "'.login-form__input')).borderTopLeftRadius,"
                " getComputedStyle(document.querySelector("
                "'.login-card button[type=\\\"submit\\\"]'))"
                ".borderTopLeftRadius]")
            if radii[0] != radii[1]:
                raise AssertionError(
                    "%dpx: the field and the primary must share a radius, "
                    "measured %r" % (width, radii))
        finally:
            context.close()


def test_show_password_toggle_reveals_itself_and_swaps_its_name(new_context, server):
    """the show-password toggle reveals ITSELF at load (the hidden attribute is
    removed, not overridden), swaps aria-pressed and its translated accessible
    name with the state, keeps .copy-btn's synthesized 44x44 hit area — and
    with scripts blocked it never appears, reserves no gutter, and the form
    still signs in (X3/D-09, 22-13-PLAN.md Task 3)"""
    context = new_context()
    try:
        page = context.new_page()
        page.goto(server.base_url() + "/login")
        toggle = page.locator("[data-login-reveal]")
        toggle.wait_for(state="visible")
        if toggle.get_attribute("hidden") is not None:
            raise AssertionError(
                "login-card.js must remove the server-rendered hidden "
                "attribute, not merely override it in CSS — a visible "
                "control that is still hidden from assistive tech is worse "
                "than the defect")
        show_name = toggle.get_attribute("aria-label")
        if not show_name:
            raise AssertionError("expected the icon-only toggle to carry an aria-label")
        if toggle.get_attribute("aria-pressed") != "false":
            raise AssertionError("expected the toggle to start unpressed")
        if page.locator("#password").get_attribute("type") != "password":
            raise AssertionError("expected the field to start masked")
        # The class-at-load idiom: the gutter is reserved only now that
        # the toggle is there.
        wrapper_class = page.locator(".login-form__field").get_attribute("class")
        if "login-form__field--with-toggle" not in (wrapper_class or ""):
            raise AssertionError(
                "expected login-card.js to append the padding modifier at "
                "load, got %r" % (wrapper_class,))
        # .copy-btn reused verbatim: a 22x22 visual box with the ::before
        # inset synthesizing 44x44.
        hit = toggle.evaluate(
            "el => { var r = el.getBoundingClientRect();"
            " var s = getComputedStyle(el, '::before');"
            " return [r.width - parseFloat(s.left) - parseFloat(s.right),"
            " r.height - parseFloat(s.top) - parseFloat(s.bottom)]; }")
        if not hit or hit[0] < 44 or hit[1] < 44:
            raise AssertionError(
                "expected the toggle's hit area to measure at least 44x44 in "
                "both axes, measured %r" % (hit,))
        toggle.click()
        hide_name = toggle.get_attribute("aria-label")
        if hide_name == show_name or not hide_name:
            raise AssertionError(
                "the accessible name must swap with the state, still %r" % (hide_name,))
        if toggle.get_attribute("aria-pressed") != "true":
            raise AssertionError("expected aria-pressed to flip to true")
        if page.locator("#password").get_attribute("type") != "text":
            raise AssertionError("expected the field to reveal its value")
        toggle.click()
        if toggle.get_attribute("aria-label") != show_name:
            raise AssertionError("expected the accessible name to swap back")
        if page.locator("#password").get_attribute("type") != "password":
            raise AssertionError("expected the field to mask again")
    finally:
        context.close()

    # D-09's floor, asserted at this plan's own commit: with scripts
    # blocked the toggle is not there at all (never a dead control), no
    # gutter is reserved for it, and the form still signs in.
    with _no_js_page(
            new_context, server.base_url(), "/login", sign_in=False) as page:
        if page.locator("[data-login-reveal]").is_visible():
            raise AssertionError(
                "with scripts blocked the toggle must stay hidden — a "
                "control that silently does nothing is worse than no "
                "control")
        wrapper_class = page.locator(".login-form__field").get_attribute("class")
        if "login-form__field--with-toggle" in (wrapper_class or ""):
            raise AssertionError(
                "with scripts blocked the field must reserve no gutter for "
                "a toggle that is not shown")
        page.fill("#password", TEST_PASSWORD)
        with page.expect_navigation():
            page.click('button[type="submit"]')
        if "/login" in page.url:
            raise AssertionError(
                "expected a scripts-blocked sign-in to succeed, landed on %r"
                % page.url)


# ===========================================================================
# 22-13-PLAN.md Task 3 (X3): the login lockout countdown. Driving the
# process-global LoginThrottle to its limit locks THAT subprocess out for
# the whole window, and the lockout branch is checked before the
# password is, so a correct password cannot unlock it over HTTP — an
# isolated, function-scoped server keeps this from locking out any other
# test that shares a server in this module.
# ===========================================================================

def test_a_locked_out_login_page_ticks_down_and_re_enables_the_form(page, make_app_server):
    """a locked-out login page ticks down from the server's own seed, with both
    controls natively disabled, and re-enables them by itself at zero with no
    reload — the message cleared and its aria-describedby dropped with it
    (X3, 22-13-PLAN.md Task 3)"""
    # Playwright's clock API drives the countdown to zero instead of this
    # check sleeping for the real five-minute window. The timer under
    # test is the page's own; only its clock is faked.
    server = make_app_server(seed=seed_state_dir, fake_providers=True)
    base_url = server.base_url()
    page.clock.install()
    page.goto(base_url + "/login")
    for _attempt in range(auth.LOGIN_FAILURE_LIMIT + 1):
        page.fill("#password", "not-the-password")
        with page.expect_navigation():
            page.click('button[type="submit"]')
    seed = page.locator(".login-form").get_attribute("data-lockout-seconds")
    if not seed:
        raise AssertionError(
            "expected the locked-out form to carry the server's own "
            "remaining-seconds seed")
    remaining = int(seed)
    if remaining <= 0:
        raise AssertionError("expected a positive seed, got %r" % (seed,))
    if not page.locator("#password").is_disabled():
        raise AssertionError("expected the password field to be disabled")
    if not page.locator('button[type="submit"]').is_disabled():
        raise AssertionError("expected the primary to be disabled")
    first_text = page.locator("#login-error").inner_text()
    page.clock.run_for(2000)
    ticked_text = page.locator("#login-error").inner_text()
    if ticked_text == first_text:
        raise AssertionError(
            "the countdown must tick — the sentence was still %r after "
            "two seconds" % (first_text,))
    if str(remaining - 2) not in ticked_text:
        raise AssertionError(
            "expected the sentence to count down from the server's own "
            "seed, got %r" % (ticked_text,))
    # All the way to zero: the form re-enables itself with no reload.
    page.clock.run_for((remaining + 2) * 1000)
    if page.locator("#password").is_disabled():
        raise AssertionError("expected the password field to re-enable itself at zero")
    if page.locator('button[type="submit"]').is_disabled():
        raise AssertionError("expected the primary to re-enable itself at zero")
    if page.locator("#login-error").inner_text().strip():
        raise AssertionError("expected the expired lockout sentence to be cleared")
    if page.locator("#password").get_attribute("aria-describedby"):
        raise AssertionError(
            "expected the field to stop pointing at a message that is "
            "no longer there")


# ===========================================================================
# 22-14-PLAN.md Task 2 (B10/X9/D-04): the nav-status reminder's own
# line-breaking, at the 240px sidebar and inside the 390px dropdown, plus
# Home's own non-link rendering of it. One linear, three-phase procedure
# in a single French-language context — never a loop over independent
# scenarios, so it stays one test.
# ===========================================================================

def test_nav_status_segments_never_break_mid_phrase_in_french(new_context, server):
    """in French the two nav-status segments each report exactly ONE client rect at both
    the 240px sidebar and 390px — the line breaks between them, never mid-phrase — the
    reminder stays within 48px, the reduced dropdown opens by at most 220px, and on
    Home the reminder is a <span> with no href whose announced name is the visible
    state and names no destination (B10/X9/D-04, 22-14-PLAN.md Task 2)"""
    # B10 (22-AUDIT.md's own measurement: .nav-status was 207x48 and
    # broke "Screen on · Quiet hours" / "on"; in French "Heures / calmes
    # activées"). The target is getClientRects().length === 1 PER
    # SEGMENT at both the 240px sidebar and a 390px phone — a count only
    # a real layout engine can produce.
    base_url = server.base_url()
    context = new_context(viewport=VIEWPORT_DESKTOP)
    try:
        page = context.new_page()
        _login(page, base_url)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": "fr", "url": base_url}])
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        desktop = page.evaluate(
            "() => {"
            " var aside = document.querySelector('.dashboard-sidebar');"
            " var st = aside.querySelector('.nav-status');"
            " return {"
            "  asideWidth: aside.getBoundingClientRect().width,"
            "  height: st.getBoundingClientRect().height,"
            "  segments: Array.prototype.map.call("
            "    st.querySelectorAll('.nav-status__segment'),"
            "    function (sg) { return [sg.getClientRects().length,"
            "      sg.textContent, sg.getBoundingClientRect().width]; })"
            " };}")
        if round(desktop["asideWidth"]) != 240:
            raise AssertionError(
                "expected the 240px sidebar this contract is measured against, "
                "got %r" % (desktop["asideWidth"],))
        if len(desktop["segments"]) != 2:
            raise AssertionError(
                "expected two state segments, got %r" % (desktop["segments"],))
        for rects, text, width in desktop["segments"]:
            if rects != 1:
                raise AssertionError(
                    "segment %r broke into %d client rects in the 240px sidebar "
                    "— the line may break BETWEEN segments, never inside one"
                    % (text, rects))
            if not any(ch > "\x7f" for ch in text):
                raise AssertionError(
                    "expected the French reminder text, got %r — the English "
                    "segments are shorter and would not exercise the contract"
                    % (text,))
            if width > 207:
                raise AssertionError(
                    "French's longest segment (%r, %rpx) must fit the sidebar's "
                    "207px content column" % (text, width))
        if desktop["height"] > 48:
            raise AssertionError(
                "expected the reminder to stay within B10's 48px ceiling, got %r"
                % (desktop["height"],))
    finally:
        context.close()

    # The same contract at 390px, inside the dropdown.
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, base_url)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": "fr", "url": base_url}])
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        page.click("#site-nav-toggle")
        page.wait_for_timeout(400)
        phone = page.evaluate(
            "() => {"
            " var panel = document.getElementById('mobile-nav');"
            " var st = panel.querySelector('.nav-status');"
            " return {"
            "  tag: st.tagName, href: st.getAttribute('href'),"
            "  height: st.getBoundingClientRect().height,"
            "  panelHeight: panel.getBoundingClientRect().height,"
            "  segments: Array.prototype.map.call("
            "    st.querySelectorAll('.nav-status__segment'),"
            "    function (sg) { return [sg.getClientRects().length,"
            "      sg.textContent]; })"
            " };}")
        for rects, text in phone["segments"]:
            if rects != 1:
                raise AssertionError(
                    "segment %r broke into %d client rects at 390px" % (text, rects))
        if phone["height"] > 48:
            raise AssertionError(
                "expected the reminder within 48px at 390px, got %r" % (phone["height"],))
        if phone["tag"] != "A" or phone["href"] != "/":
            raise AssertionError(
                "off Home the reminder must stay a link to Home, got %r/%r"
                % (phone["tag"], phone["href"]))
        # X9's actual fix: the remaining push, measured.
        if phone["panelHeight"] > 220:
            raise AssertionError(
                "X9's target is a remaining push of at most 220px, measured "
                "%rpx" % (phone["panelHeight"],))

        # And on Home it is not a link at all, so it cannot claim a
        # destination the user occupies.
        page.goto(base_url + "/")
        page.wait_for_load_state("networkidle")
        page.click("#site-nav-toggle")
        page.wait_for_timeout(400)
        home = page.evaluate(
            "() => {"
            " var st = document.getElementById('mobile-nav')"
            "   .querySelector('.nav-status');"
            " return {tag: st.tagName, href: st.getAttribute('href'),"
            "         label: st.getAttribute('aria-label'),"
            "         text: st.textContent};}")
        if home["tag"] != "SPAN" or home["href"] is not None:
            raise AssertionError(
                "on Home the reminder must be a <span> with no href, got %r/%r"
                % (home["tag"], home["href"]))
        if "accueil" in (home["label"] or "").lower():
            raise AssertionError(
                "the Home reminder must not name a destination, got %r"
                % (home["label"],))
        if (home["label"] or "").strip() != (home["text"] or "").strip():
            raise AssertionError(
                "the announced name and the visible state must be the same "
                "words, got %r vs %r" % (home["label"], home["text"]))
    finally:
        context.close()


# ===========================================================================
# 22-14-PLAN.md Task 2 (T5/D-02): the mobile nav's own hidden/aria-expanded
# consistency on both the transitioned close and the reduced-motion,
# no-transition close.
# ===========================================================================

def test_mobile_nav_close_leaves_hidden_and_aria_expanded_consistent(new_context, server):
    """the mobile nav opens and closes leaving the hidden property and aria-expanded
    consistent on both paths — a descendant's transitionend never hides an open panel,
    and a close with no transition applies hidden synchronously rather than waiting for
    an event that never arrives (T5/D-02, 22-14-PLAN.md Task 2)"""
    # T5, and D-02's own minimum-set item 3. Two paths, because the
    # defect had two halves: a transitionend listener with no
    # target/property filter (any child's colour transition could hide
    # an OPEN panel), and a close with no transition at all that never
    # re-applied the hidden property.
    base_url = server.base_url()
    context = new_context(viewport=VIEWPORT_PHONE)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")

        def state():
            return page.evaluate(
                "() => {"
                " var p = document.getElementById('mobile-nav');"
                " var t = document.getElementById('site-nav-toggle');"
                " return {hidden: p.hidden,"
                "         expanded: t.getAttribute('aria-expanded'),"
                "         open: p.classList.contains('mobile-nav--open'),"
                "         height: p.getBoundingClientRect().height};}")

        start = state()
        if not start["hidden"] or start["expanded"] != "false":
            raise AssertionError(
                "expected the panel to start hidden and closed, got %r" % (start,))
        page.click("#site-nav-toggle")
        page.wait_for_timeout(400)
        opened = state()
        if opened["hidden"] or opened["expanded"] != "true" or not opened["open"]:
            raise AssertionError(
                "expected an open panel after the first click, got %r" % (opened,))
        if opened["height"] <= 0:
            raise AssertionError("expected the open panel to have a box")

        # A descendant transition must NOT hide the open panel: fire a
        # transitionend from a child with the very property the listener
        # cares about, which is the strictest form of the target filter.
        page.evaluate(
            "() => {"
            " var p = document.getElementById('mobile-nav');"
            " var child = p.querySelector('button, a, form');"
            " child.dispatchEvent(new TransitionEvent('transitionend',"
            "   {bubbles: true, propertyName: 'max-height'}));}")
        page.wait_for_timeout(50)
        after_child = state()
        if after_child["hidden"] or after_child["expanded"] != "true":
            raise AssertionError(
                "a descendant's transitionend must never hide an OPEN panel, got %r"
                % (after_child,))

        page.click("#site-nav-toggle")
        page.wait_for_timeout(600)
        closed = state()
        if not closed["hidden"] or closed["expanded"] != "false" or closed["open"]:
            raise AssertionError(
                "expected hidden and aria-expanded to agree after a transitioned "
                "close, got %r" % (closed,))
        context.close()

        # The no-transition path: reduced motion, where the stylesheet
        # switches the transition off entirely and no transitionend will
        # ever arrive.
        context = new_context(viewport=VIEWPORT_PHONE, reduced_motion="reduce")
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        page.click("#site-nav-toggle")
        page.click("#site-nav-toggle")
        reduced = page.evaluate(
            "() => {"
            " var p = document.getElementById('mobile-nav');"
            " var t = document.getElementById('site-nav-toggle');"
            " return {hidden: p.hidden,"
            "         expanded: t.getAttribute('aria-expanded'),"
            "         transition: getComputedStyle(p).transitionDuration};}")
        if reduced["expanded"] != "false":
            raise AssertionError("expected aria-expanded=false after the close")
        if not reduced["hidden"]:
            raise AssertionError(
                "with no transition to wait for, hidden must be applied "
                "SYNCHRONOUSLY — got %r" % (reduced,))
    finally:
        context.close()


# ===========================================================================
# 27-04-PLAN.md D-04/CFG-63, retargeted onto the restored bar by
# 28-10-PLAN.md Task 3 (CFG-77/CFG-78): the bar's own clearance geometry
# against the ONE other fixed element each breakpoint has, and against
# the page's own last in-flow element. Independently asserted per
# breakpoint/language combination with no comparison across them, so the
# original nested loop is parametrized on both axes.
# ===========================================================================

def _rects_intersect(a, b):
    return (a["left"] < b["right"] and b["left"] < a["right"]
            and a["top"] < b["bottom"] and b["top"] < a["bottom"])


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize(
    "width,height,fixed_sel,fixed_name", [
        (390, 844, ".tab-bar", "the tab bar"),
        (1280, 900, ".dashboard-sidebar", "the sidebar column"),
    ], ids=["390x844", "1280x900"])
def test_the_dirty_bar_never_overlaps_the_tab_bar_sidebar_or_the_pages_last_element(
        new_context, server, lang, width, height, fixed_sel, fixed_name):
    """the restored bar — genuinely position: fixed at both breakpoints, the
    INVERSE of this check's own retired position: fixed/sticky refusal — never
    intersects the ONE other fixed element each breakpoint has (the tab bar
    under 960px, the sticky sidebar column at and above it) and never covers
    the page's own last in-flow element, measured via resolved
    getBoundingClientRect()es (never a CSS property value) at 390x844 and
    1280x900, in BOTH shipped languages (the longer French copy is what makes
    the bar wrap to two lines) — the scripts-blocked variant of the
    last-in-flow clause is 28-08-PLAN.md Task 2's own acceptance criterion,
    verified LIVE by that plan rather than by an automated check in this file,
    named here rather than assumed covered (CFG-31, 27-04-PLAN.md D-04/CFG-63;
    retargeted onto the restored bar by 28-10-PLAN.md Task 3, CFG-77/CFG-78;
    retired the fixed save-bar-vs-tab-bar geometry D-10/T7, 22-14-PLAN.md Task
    3, this check now measures again)"""
    # 28-10-PLAN.md Task 3 (CFG-77/CFG-78): RETARGETED, not a mechanical
    # swap — this check's own pre-28-08 subject proved the save-status
    # region was NEVER position: fixed/sticky. That is exactly the
    # contract this phase reverses: the restored bar IS position: fixed,
    # at both breakpoints (28-08-PLAN.md Task 2). Retargeted onto the
    # bar, and widened to the case 28-08's own clearance work turns on:
    # the bar must never intersect the ONE other fixed element each
    # breakpoint has, and the page's own last in-flow element must never
    # sit under either.
    #
    # SCOPE NOTE: the scripts-BLOCKED variant of the last-in-flow-element
    # clause is 28-08-PLAN.md Task 2's own acceptance criterion. 28-08's
    # own SUMMARY records it as verified LIVE in a real Chromium tab
    # during that plan's own execution, not as an automated Playwright
    # check in this file — the automated coverage that DOES exist for it
    # (test_config_page.py/test_status_pages.py) reads the CSS SOURCE for
    # the :has(.dirty-bar) clearance rule rather than rendering a
    # scripts-blocked page and measuring it. That gap is named here
    # rather than assumed covered; this check itself only runs with
    # scripts ENABLED.
    base_url = server.base_url()
    context = new_context(viewport={"width": width, "height": height})
    try:
        page = context.new_page()
        _login(page, base_url)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        page.goto(base_url + "/display")
        page.wait_for_load_state("networkidle")
        current = page.eval_on_selector('input[name="theme"]:checked', "el => el.value")
        other = next(t for t in device_config.THEME_IDS if t != current)
        _click_control(page, 'input[name="theme"][value="%s"]' % other)
        _wait_for_bar(page)
        # Well past var(--motion-fast) (180ms): the bar's own entrance
        # animation (skypane-bar-arrive) translates it from
        # var(--space-md) below its resting position — reading geometry
        # mid-flight would measure a frame that is not the settled
        # position this check asserts.
        page.wait_for_timeout(600)

        # SCROLLED TO THE BOTTOM: getBoundingClientRect() is
        # viewport-relative, and both the bar (fixed near the viewport's
        # own foot) and the page's last in-flow element can only ever
        # occupy the SAME region of the viewport once the page is
        # scrolled that far.
        page.evaluate("() => window.scrollTo(0, document.body.scrollHeight)")

        # The bar itself renders as the LAST in-DOM-order child of
        # .dashboard-main — it is taken OUT of flow by its own position:
        # fixed, so the page's own last IN-FLOW element is the bar's
        # last non-fixed PRECEDING sibling, never the bar comparing
        # against itself.
        geom = page.evaluate(
            "sel => {"
            " var bar = document.querySelector('[data-dirty-bar]');"
            " var fixedEl = document.querySelector(sel);"
            " var main = document.querySelector('.dashboard-main');"
            " var last = main ? main.lastElementChild : null;"
            " while (last && getComputedStyle(last).position === "
            "        'fixed') {"
            "   last = last.previousElementSibling;"
            " }"
            " var r = bar.getBoundingClientRect();"
            " var out = {bar: {top: r.top, bottom: r.bottom,"
            "                   left: r.left, right: r.right},"
            "            barPosition: getComputedStyle(bar).position,"
            "            fixedPresent: !!fixedEl, lastPresent: !!last};"
            " if (fixedEl) {"
            "   var f = fixedEl.getBoundingClientRect();"
            "   out.fixedEl = {top: f.top, bottom: f.bottom,"
            "                  left: f.left, right: f.right};"
            "   out.fixedDisplay = getComputedStyle(fixedEl).display;"
            " }"
            " if (last) {"
            "   var l = last.getBoundingClientRect();"
            "   out.last = {top: l.top, bottom: l.bottom,"
            "               left: l.left, right: l.right};"
            " }"
            " return out;}", fixed_sel)

        if geom["barPosition"] != "fixed":
            raise AssertionError(
                "%s/%s: expected the bar to be position: fixed, got %r "
                "— the restored bar IS fixed at both breakpoints "
                "(28-08-PLAN.md Task 2)" % (fixed_name, lang, geom["barPosition"]))
        if not geom["fixedPresent"] or geom.get("fixedDisplay") == "none":
            raise AssertionError(
                "%s/%s: expected %s (%r) visible, got display %r"
                % (fixed_name, lang, fixed_name, fixed_sel, geom.get("fixedDisplay")))
        if _rects_intersect(geom["bar"], geom["fixedEl"]):
            raise AssertionError(
                "%s/%s: the bar and %s must not intersect; bar %r vs "
                "%s %r" % (fixed_name, lang, fixed_name, geom["bar"],
                           fixed_name, geom["fixedEl"]))
        if not geom["lastPresent"]:
            raise AssertionError(
                "%s/%s: expected the page's own last in-flow element "
                "(.dashboard-main's last child) to exist" % (fixed_name, lang))
        if _rects_intersect(geom["bar"], geom["last"]):
            raise AssertionError(
                "%s/%s: the bar must not cover the page's own last "
                "in-flow element; bar %r vs last element %r"
                % (fixed_name, lang, geom["bar"], geom["last"]))
    finally:
        context.close()


# ===========================================================================
# 22-15-PLAN.md Task 2 (T13): Health's refresh loop must not stop on a
# failing endpoint — it retries with a visible neutral pill, and recovers
# cleanly.
# ===========================================================================

def test_refresh_loop_shows_a_neutral_pill_on_failure_and_clears_on_recovery(page, server):
    """when Health's refresh endpoint starts failing the loop does NOT stop: it schedules a
    backed-off retry and shows a visible NEUTRAL .dot--off badge carrying no warn token
    while the 'Updating' pill stands down, and when the endpoint recovers the next
    attempt succeeds and the badge goes away and computes display: none through the
    .banner__pill[hidden] guard (T13, 22-15-PLAN.md Task 2)"""
    # T13 (22-15-PLAN.md Task 2). The defect was that any non-OK response
    # stopped the loop for the life of the page with NO visible sign - a
    # frozen page and a live one looked identical.
    #
    # Playwright's clock is what makes this a fast check rather than a
    # two-minute one: freshness.js's cadence is 45s and its first retry
    # rung is another 45s, so real time would cost 90s of wall clock per
    # run. install() is called AFTER login so the login navigation runs
    # on a real clock.
    base_url = server.base_url()
    _login(page, base_url)
    page.clock.install()
    page.goto(base_url + "/health")
    page.wait_for_load_state("networkidle")

    badge = "[data-refresh-state-pill]"
    if page.locator(badge).count() != 0:
        raise AssertionError(
            "expected no loop-state badge on a healthy page load - the badge "
            "exists only while the loop is retrying or deliberately idle")

    # Break the endpoint the loop polls. The route is added after the
    # initial navigation, so only the script's own fetch is affected.
    failing = {"on": True}

    def _health_route(route):
        if failing["on"]:
            route.abort()
        else:
            route.continue_()

    page.route("**/health", _health_route)

    # Fire one interval tick: the fetch fails, the ladder schedules a
    # retry and the badge appears.
    page.clock.run_for(46000)
    page.wait_for_selector(badge + ":not([hidden])", timeout=10000)
    state = page.evaluate(
        "() => {"
        " var el = document.querySelector('[data-refresh-state-pill]');"
        " var dot = el.querySelector('.dot');"
        " var cs = getComputedStyle(el);"
        " return {cls: el.getAttribute('class'),"
        "         dot: dot ? dot.getAttribute('class') : null,"
        "         text: el.textContent.trim(),"
        "         display: cs.display,"
        "         updating: document.querySelector("
        "           '[data-refresh-pill]').hidden};}")
    if "dot--off" not in (state["dot"] or ""):
        raise AssertionError(
            "the loop-state badge must carry the NEUTRAL .dot--off dot - a "
            "browser that lost its connection is not a device fault - got %r"
            % (state["dot"],))
    for warn_token in ("warn", "error", "danger"):
        if warn_token in (state["cls"] or "") or warn_token in (state["dot"] or ""):
            raise AssertionError(
                "the loop-state badge must carry no warn token at all, got "
                "class %r dot %r" % (state["cls"], state["dot"]))
    if not state["text"]:
        raise AssertionError("expected visible copy in the loop-state badge")
    if not state["updating"]:
        raise AssertionError(
            "expected the 'Updating' pill to be hidden while the state badge "
            "shows - exactly one pill is ever visible")

    # Recover. The first rung is another 45s; the next attempt succeeds
    # and the badge clears.
    failing["on"] = False
    page.clock.run_for(46000)
    page.wait_for_function(
        "() => {"
        " var el = document.querySelector('[data-refresh-state-pill]');"
        " return !el || el.hidden === true;}",
        timeout=10000)

    # The [hidden]-versus-display collision: the badge composes
    # .banner__pill, whose own rule declares display: inline-flex, and
    # an author display always beats the user-agent [hidden] { display:
    # none } regardless of source order. Without style.css's own guard
    # the badge would still be painted right here.
    hidden_display = page.evaluate(
        "() => {"
        " var el = document.querySelector('[data-refresh-state-pill]');"
        " return el ? getComputedStyle(el).display : 'absent';}")
    if hidden_display not in ("none", "absent"):
        raise AssertionError(
            "a hidden loop-state badge must compute display: none - the "
            ".banner__pill[hidden] guard is what makes the native hidden "
            "attribute work on this component, got %r" % (hidden_display,))


# 28-10-PLAN.md Task 1 (CFG-77/CFG-78): REMOVED outright —
# _a_double_fire_of_change_before_the_first_save_resolves_coalesces_to_one_
# follow_up and its own _hold_posts() helper (27-04-PLAN.md Task 4,
# T-27-04-C/D, CFG-63) tested that two rapid `change` commits arriving
# while a fetch was still in flight coalesced into exactly one follow-up
# POST. That entire subject no longer exists: the restored bar issues no
# request at all until the user clicks Enregistrer, once, and a native
# form submission has no "in flight" window for a second commit to race
# against. Removed rather than retargeted; its subject ceased to exist
# with the auto-save model.


# ===========================================================================
# Quick task 260913-bjy (B11's fourth and last surface): nothing on Home
# paints outside the viewport or outside its own recent-flight rows.
# Independently asserted per width/language with no cross-comparison, so
# parametrized on both axes.
# ===========================================================================

@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", [390, 1280])
def test_home_paints_nothing_outside_the_viewport_or_its_cards(new_context, server, width, lang):
    """Home paints nothing outside the viewport and nothing outside its own
    recent-flight rows, measured in BOTH languages at 390px and at 1280px:
    documentElement.scrollWidth never exceeds the viewport, no element's right
    edge clears it, and no row's content escapes its own box (B11's fourth and
    last surface, quick task 260913-bjy)"""
    # B11 (quick task 260913-bjy) — the audit's "no horizontal scrollbar
    # at 390px" closed on its FOURTH and last surface. Flights (22-09),
    # Airlines (22-11) and Health (22-12) were each measured and closed;
    # Home is the page nobody re-measured after 22-07 put the
    # recent-flight time on one line, and it had been scrolling sideways
    # ever since.
    #
    # Written to catch the CLASS on this page rather than the one
    # selector that happened to cause it: every element is measured
    # against the viewport, and every recent-flights descendant against
    # its own row box. The second half is not redundant: the cause was a
    # percentage width cap resolving against a content-sized `auto` grid
    # track, so it clamped the box to 60% of its own content at EVERY
    # width — scrollWidth alone is blind to the desktop half of the same
    # defect.
    probe = (
        "() => {"
        "  const vw = window.innerWidth;"
        "  const escaped = [], spilled = [];"
        "  document.querySelectorAll('*').forEach(el => {"
        "    const r = el.getBoundingClientRect();"
        "    if (r.width > 0 && r.right > vw + 0.5)"
        "      escaped.push(el.className.toString() || el.tagName);"
        "  });"
        "  document.querySelectorAll('.recent-flight').forEach(row => {"
        "    const rr = row.getBoundingClientRect();"
        "    row.querySelectorAll('*').forEach(el => {"
        "      const r = el.getBoundingClientRect();"
        "      if (r.width > 0 && (r.right > rr.right + 0.5 || r.left < rr.left - 0.5))"
        "        spilled.push(el.className.toString() || el.tagName);"
        "    });"
        "  });"
        "  return {sw: document.documentElement.scrollWidth,"
        "          cw: document.documentElement.clientWidth,"
        "          rows: document.querySelectorAll('.recent-flight').length,"
        "          escaped: [...new Set(escaped)],"
        "          spilled: [...new Set(spilled)]};"
        "}")
    context = new_context(viewport={"width": width, "height": 844})
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        page.goto(base_url + "/")
        page.locator(".recent-flight").first.wait_for(state="visible")
        seen = page.evaluate(probe)
        if page.viewport_size["width"] != width:
            raise AssertionError("expected the measurement to be taken at %dpx" % (width,))
        if not seen["rows"]:
            raise AssertionError(
                "expected the seeded recent-flight rows to render at "
                "%dpx/%s — with none, this check measures nothing" % (width, lang))
        if seen["sw"] > width:
            raise AssertionError(
                "Home scrolls sideways at %dpx/%s: documentElement."
                "scrollWidth %d against a client width of %d, painted "
                "past the right edge by %r (B11)"
                % (width, lang, seen["sw"], seen["cw"], seen["escaped"]))
        if seen["escaped"]:
            raise AssertionError(
                "expected nothing on Home to paint right of the %dpx "
                "viewport in %s, got %r (B11)" % (width, lang, seen["escaped"]))
        if seen["spilled"]:
            raise AssertionError(
                "expected every recent-flight row to contain its own "
                "content at %dpx/%s, but %r painted outside its row box "
                "— the half of this defect no scrollWidth can see (B11)"
                % (width, lang, seen["spilled"]))
    finally:
        context.close()


# ===========================================================================
# Quick task 260913-dgh: the recent-flight callsign column must never be
# starved by the time column beside it. Independently asserted per
# width/language with no cross-comparison, so parametrized on both axes.
# ===========================================================================

@pytest.mark.parametrize("lang", ["fr", "en"])
@pytest.mark.parametrize("width", list(VIEWPORT_WIDTHS_ALL))
def test_recent_flight_callsigns_are_never_starved(new_context, server, width, lang):
    """no recent-flight callsign is ever starved by the time column - its box is
    never narrower than its own text at 320, 360, 390, 768 or 1280px in EITHER
    language, Home still never scrolls sideways at any of them, and at 768px
    the callsign and the time still share one line (quick task 260913-dgh)"""
    # Quick task 260913-dgh. The Home check above measures every element
    # against the VIEWPORT and every row descendant against its own ROW
    # box, and is structurally blind to this defect: the starved
    # element's own box stays well inside the row — it is the box itself
    # that collapses, and the TEXT paints out of it, straight over the
    # time beside it.
    #
    # The 768px assertion is the other half, and it is what stops the
    # fix being "give the time its own line everywhere": with 686px of
    # row there, the callsign and the time must still share the first
    # line. It is deliberately NOT asserted at 1280px, where the growing
    # age string will legitimately wrap one day — that is the fix
    # working, not failing.
    probe = (
        "() => {"
        "  const rows = document.querySelectorAll('.recent-flight');"
        "  const starved = [];"
        "  let cells = 0, sameLine = 0, twoLine = 0;"
        "  rows.forEach(row => {"
        "    const cs = row.querySelector('.recent-flight__callsign');"
        "    const tm = row.querySelector('.recent-flight__time');"
        "    if (!cs) return;"
        "    cells += 1;"
        "    const box = cs.getBoundingClientRect().width;"
        "    const range = document.createRange();"
        "    range.selectNodeContents(cs);"
        "    const text = range.getBoundingClientRect().width;"
        "    if (text > box + 0.5)"
        "      starved.push(cs.textContent + ': box ' + box.toFixed(2)"
        "        + 'px for ' + text.toFixed(2) + 'px of content');"
        "    if (tm) {"
        # Two items share a flex line when their boxes overlap
        # VERTICALLY. Equal tops would be the wrong test: the row is
        # baseline-aligned and the time renders at the smaller label
        # size, so the two tops differ by 3px on the SAME line.
        "      const a = cs.getBoundingClientRect();"
        "      const b = tm.getBoundingClientRect();"
        "      if (a.bottom > b.top + 0.5 && b.bottom > a.top + 0.5) sameLine += 1;"
        "      else twoLine += 1;"
        "    }"
        "  });"
        "  return {rows: rows.length, cells: cells, starved: starved,"
        "          sameLine: sameLine, twoLine: twoLine,"
        "          sw: document.documentElement.scrollWidth,"
        "          cw: document.documentElement.clientWidth};"
        "}")
    context = new_context(viewport={"width": width, "height": 844})
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        page.goto(base_url + "/")
        page.locator(".recent-flight").first.wait_for(state="visible")
        seen = page.evaluate(probe)
        if page.viewport_size["width"] != width:
            raise AssertionError("expected the measurement to be taken at %dpx" % (width,))
        if not seen["rows"] or seen["cells"] != seen["rows"]:
            raise AssertionError(
                "expected every seeded recent-flight row to carry a "
                "callsign at %dpx/%s, got %d callsigns in %d rows — "
                "with a mismatch this check measures nothing"
                % (width, lang, seen["cells"], seen["rows"]))
        if seen["starved"]:
            raise AssertionError(
                "the recent-flight callsign column is STARVED at "
                "%dpx/%s — its box is narrower than its own text, so "
                "the callsign paints out of it and over the time "
                "beside it: %r" % (width, lang, seen["starved"]))
        if seen["sw"] > width:
            raise AssertionError(
                "Home scrolls sideways at %dpx/%s (documentElement."
                "scrollWidth %d against a client width of %d) — a "
                "callsign column that refuses to yield must not buy "
                "that by pushing the row past the viewport (B11)"
                % (width, lang, seen["sw"], seen["cw"]))
        if width == 768 and (seen["twoLine"] or not seen["sameLine"]):
            raise AssertionError(
                "expected the callsign and the time to share the first "
                "line at 768px/%s, where the row is 686px wide, but %d "
                "of %d rows put the time on its own line — the fix must "
                "not cost a line where there is room"
                % (lang, seen["twoLine"], seen["cells"]))
    finally:
        context.close()


# ===========================================================================
# Quick task 260913-cz6: Health's tables must fit their own
# .data-table-wrap with every disclosure forced open — the readings
# table is reachable only through a closed-by-default disclosure, so no
# page-level scan ever laid it out. Independently asserted per language,
# so parametrized.
# ===========================================================================

@pytest.mark.parametrize("lang", ["en", "fr"])
def test_health_tables_fit_their_wraps_with_every_disclosure_open(new_context, server, lang):
    """Health's tables each fit inside their own .data-table-wrap at 390px in BOTH
    languages with EVERY <details> on the page forced open — the readings table
    is reachable only through a closed-by-default disclosure, and its wrap
    scrolls while documentElement.scrollWidth never moves, so no page-level
    assertion can see it (B12's cause on its third table, quick task 260913-cz6)"""
    # Measured before the fix, at 390px: the readings .data-table-wrap
    # was 308px against a 432px (FR) / 369px (EN) table — 124px of
    # overflow, its own horizontal scrollbar, and a completely still
    # page. Written for the CLASS, not that one selector: it opens EVERY
    # <details> on the page and measures EVERY .data-table-wrap.
    #
    # 23-08-PLAN.md Task 3: this context REQUESTS REDUCED MOTION on
    # purpose. Setting `details.open = true` and measuring in the same
    # task is sound only while nothing animates; Health carries four
    # disclosures and a box measured mid-transition is narrower than its
    # final box. Reduced motion makes the final state the IMMEDIATE
    # state through the app's own global override, so this is
    # deterministic prophylaxis rather than a weakened measurement.
    probe = (
        "() => {"
        "  document.querySelectorAll('details').forEach(d => { d.open = true; });"
        "  const over = [];"
        "  const wraps = document.querySelectorAll('.data-table-wrap');"
        "  let rows = 0;"
        "  wraps.forEach(w => {"
        "    const t = w.querySelector('table');"
        "    if (t) rows += t.querySelectorAll('tbody tr').length;"
        "    if (w.scrollWidth > w.clientWidth + 0.5) {"
        "      const cells = t ? t.querySelectorAll('tbody tr:first-child td') : [];"
        "      over.push({cls: (t ? t.className : w.className).toString(),"
        "                 wrap: w.clientWidth, table: Math.round(w.scrollWidth),"
        "                 cols: [...cells].map("
        "                   c => Math.round(c.getBoundingClientRect().width))});"
        "    }"
        "  });"
        "  return {wraps: wraps.length, rows: rows, over: over,"
        "          docSW: document.documentElement.scrollWidth,"
        "          docCW: document.documentElement.clientWidth};"
        "}")
    width = 390
    context = new_context(viewport={"width": width, "height": 844}, reduced_motion="reduce")
    try:
        page = context.new_page()
        base_url = server.base_url()
        _login(page, base_url)
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])
        page.goto(base_url + "/health")
        page.locator("details.readings-disclosure").first.wait_for(state="attached")
        seen = page.evaluate(probe)
        if page.viewport_size["width"] != width:
            raise AssertionError("expected the measurement to be taken at %dpx" % (width,))
        # Both guards exist so this check cannot pass by measuring an
        # empty page: the seeded fixture renders the readings table, and
        # a render that stops emitting it must fail here rather than
        # quietly measure nothing.
        if not seen["wraps"]:
            raise AssertionError(
                "expected at least one .data-table-wrap on Health at %dpx/%s "
                "with every disclosure open — with none, this check measures "
                "nothing" % (width, lang))
        if not seen["rows"]:
            raise AssertionError(
                "expected the seeded tables to render body rows at %dpx/%s — "
                "with none, this check measures nothing" % (width, lang))
        if seen["over"]:
            raise AssertionError(
                "a table inside a disclosure overflows its own wrap at "
                "%dpx/%s, giving it a horizontal scrollbar the page itself "
                "never shows (documentElement.scrollWidth %d against a client "
                "width of %d): %r — each entry is the table's class, its "
                "wrap's clientWidth, the table's scrollWidth and the first "
                "row's column widths (B12's cause, quick task 260913-cz6)"
                % (width, lang, seen["docSW"], seen["docCW"], seen["over"]))
    finally:
        context.close()


# ===========================================================================
# Quick task 260913-eab: the general form of the check above — EVERY
# <details> on EVERY authenticated page (plus the login page, which
# renders none) opens without overflowing anything. Independently
# asserted per width/language, so parametrized on both axes; the inner
# per-page sweep stays a loop within each combination (one session, one
# sign-in, all pages measured in turn — not independent scenarios).
# ===========================================================================

_DISCLOSURE_SWEEP_PROBE = (
    "() => {"
    "  const all = [...document.querySelectorAll('details')];"
    "  const closedBefore = all.filter(d => !d.open).length;"
    "  all.forEach(d => { d.open = true; });"
    "  const vw = window.innerWidth;"
    "  const escaped = [], scrolled = [];"
    "  document.querySelectorAll('*').forEach(el => {"
    "    const r = el.getBoundingClientRect();"
    "    if (r.width > 0 && r.right > vw + 0.5)"
    "      escaped.push(el.className.toString() || el.tagName);"
    "    const ox = getComputedStyle(el).overflowX;"
    "    if ((ox === 'auto' || ox === 'scroll')"
    "        && el.scrollWidth > el.clientWidth + 0.5) {"
    "      const kid = el.firstElementChild;"
    "      scrolled.push({box: el.className.toString() || el.tagName,"
    "                     boxWidth: el.clientWidth,"
    "                     content: Math.round(el.scrollWidth),"
    "                     firstChild: kid ? (kid.className.toString()"
    "                                        || kid.tagName) : null});"
    "    }"
    "  });"
    "  return {n: all.length, closedBefore: closedBefore,"
    "          sw: document.documentElement.scrollWidth,"
    "          cw: document.documentElement.clientWidth,"
    "          escaped: [...new Set(escaped)].slice(0, 12),"
    "          scrolled: scrolled};"
    "}")


def _assert_disclosure_sweep_clean(seen, where, width):
    if seen["sw"] > width:
        raise AssertionError(
            "%s scrolls sideways with every disclosure open: "
            "documentElement.scrollWidth %d against a client width of %d, "
            "painted past the right edge by %r"
            % (where, seen["sw"], seen["cw"], seen["escaped"]))
    # The scroll-container diagnostic is reported BEFORE the viewport
    # one, and not by accident: when a container overflows, every
    # descendant's layout rect extends past the viewport too, so
    # `escaped` fires as well and reports a list of tag names. Naming
    # the container, its box and its content width first is what
    # actually points at the cause.
    if seen["scrolled"]:
        raise AssertionError(
            "%s gives a scroll container its own horizontal scrollbar with "
            "every disclosure open, which the page itself never shows "
            "(documentElement.scrollWidth %d against a client width of %d): "
            "%r — each entry is the container's class, its clientWidth, its "
            "scrollWidth and its first child (the readings-table class, "
            "quick task 260913-eab)"
            % (where, seen["sw"], seen["cw"], seen["scrolled"]))
    if seen["escaped"]:
        raise AssertionError(
            "%s lays %r out right of the viewport with every disclosure "
            "open, while the page itself never scrolls sideways "
            "(documentElement.scrollWidth %d against a client width of %d) "
            "and no scroll container reports overflow either — so this is "
            "content escaping with nothing offering a way to reach it"
            % (where, seen["escaped"], seen["sw"], seen["cw"]))


@pytest.mark.parametrize("lang", ["en", "fr"])
@pytest.mark.parametrize("width", list(VIEWPORT_WIDTHS_RESPONSIVE))
def test_every_disclosure_on_every_page_opens_without_overflow(new_context, server, width, lang):
    """EVERY <details> on EVERY page opens without overflowing anything — all six
    authenticated pages plus the login page, at 360px, 390px and 1280px, in BOTH
    languages, with every disclosure on the page forced open: documentElement.
    scrollWidth never exceeds the viewport, nothing paints right of it, and no
    scroll container's content is wider than its own box (the readings-table
    class, which no page-level assertion can see). Each page asserts a minimum
    disclosure count and that at least one was closed beforehand, so a selector
    change makes this fail rather than silently measure nothing (quick task
    260913-eab)"""
    # Quick task 260913-eab. The general form of the check immediately
    # above: a COLLAPSED <details> has its contents not laid out at all,
    # so every sweep elsewhere in this repo measured pages in their
    # DEFAULT state, and everything asleep inside a disclosure was
    # invisible to measurement BY CONSTRUCTION. This one opens EVERY
    # <details> on EVERY page, so it covers the disclosures that exist
    # today AND any added later without editing this file.
    #
    # (route, minimum <details> the page must render). Every
    # authenticated page, in nav order. Each route's own floor is its
    # page-specific disclosure count plus the ONE shared
    # `<details class="tab-bar__more">` every authenticated page
    # renders. 29-03-PLAN.md (CFG-83): /flights' floor is derived from
    # history_page.FLIGHTS_PAGE_SIZE, the page's own default page size,
    # not the seeded fixture's own flight count, since Vols is paginated.
    pages = (("/", 1), ("/display", 3),
             ("/flights", history_page.FLIGHTS_PAGE_SIZE + 1),
             ("/airlines", 1), ("/health", 4), ("/device", 1))
    base_url = server.base_url()
    context = new_context(
        viewport={"width": width, "height": 844}, reduced_motion="reduce")
    try:
        page = context.new_page()
        context.add_cookies([{
            "name": auth.UI_LANG_COOKIE_NAME, "value": lang, "url": base_url}])

        # The login page is measured FIRST, in this same context, while
        # it is still the real unauthenticated page — after _login()
        # below, /login is a 303 to /. It renders no nav and so carries
        # no <details> at all: its own "this measured something" guard
        # is the password field, not a disclosure count.
        page.goto(base_url + "/login")
        page.locator("#password").wait_for(state="visible")
        seen = page.evaluate(_DISCLOSURE_SWEEP_PROBE)
        if page.viewport_size["width"] != width:
            raise AssertionError("expected the measurement to be taken at %dpx" % (width,))
        _assert_disclosure_sweep_clean(
            seen, "/login at %dpx/%s" % (width, lang), width)

        _login(page, base_url)
        for route, want in pages:
            page.goto(base_url + route)
            page.locator("main").first.wait_for(state="visible")
            seen = page.evaluate(_DISCLOSURE_SWEEP_PROBE)
            where = "%s at %dpx/%s" % (route, width, lang)
            if seen["n"] < want:
                raise AssertionError(
                    "expected at least %d <details> on %s, found %d — "
                    "with fewer, this check measures a state that is no "
                    "longer there, so it must fail rather than pass on an "
                    "empty selector (quick task 260913-eab)"
                    % (want, where, seen["n"]))
            if not seen["closedBefore"]:
                raise AssertionError(
                    "expected at least one of %s's %d <details> to be "
                    "CLOSED before being forced open on %s — with none, "
                    "this check measures the same state every other sweep "
                    "in this file already measures, and adds nothing"
                    % (route, seen["n"], where))
            _assert_disclosure_sweep_clean(seen, where, width)
    finally:
        context.close()


# ===========================================================================
# 23-04-PLAN.md Task 2 (D10/CFG-33): the two ways a cross-document view
# transition fails silently.
# ===========================================================================

def test_view_transition_names_are_unique_on_every_route(page, server):
    """every view-transition name the served stylesheet declares resolves to AT MOST
    one element on each of the six authenticated routes, counted from the
    COMPUTED value on every element of the real document — the sidebar and the
    page title on all six, Home's frame picture on Home only, and the declared
    set itself pinned so a dropped declaration fails rather than emptying the
    measurement. A name matching twice (two navigation landmarks share every
    authenticated DOM, and a bare `nav` selector reaches both) makes the browser
    drop the whole transition with no error anywhere, and no source scan can see
    it (D10/CFG-33, 23-04-PLAN.md Task 2)"""
    # WHY THIS IS COUNTED IN A BROWSER AND FROM COMPUTED VALUES. A
    # stylesheet scan can prove that a name is DECLARED once; it cannot
    # prove that its selector MATCHES once. companion/layout.py puts two
    # navigation landmarks into every authenticated document at the same
    # time — the sidebar's vertical one and the bottom tab bar — and the
    # 960px media query decides only which is VISIBLE, never how many
    # exist. A name hung on a class those share — or on the bare `nav`
    # element — is declared exactly once in style.css, passes every
    # source scan, and resolves to two elements in the DOM, at which
    # point the browser drops the entire transition with no error, no
    # console warning and no visual difference. Only a real document can
    # see that.
    #
    # Three anti-vacuity guards, because "no name appears twice" is
    # trivially satisfied by a page that declares no names at all:
    #   1. the set of names the SERVED stylesheet declares must equal
    #      VIEW_TRANSITION_NAMES's keys;
    #   2. every name must resolve to EXACTLY one element on each route
    #      its entry lists — zero is a failure, not a pass;
    #   3. and to zero elements on the routes it does not.
    probe = (
        "() => {"
        "  const declared = [];"
        "  const walk = (rules) => {"
        "    for (const r of rules) {"
        "      if (r.style && r.style.viewTransitionName)"
        "        declared.push(r.style.viewTransitionName);"
        "      if (r.cssRules) walk(r.cssRules);"
        "    }"
        "  };"
        "  for (const sheet of document.styleSheets) {"
        "    try { walk(sheet.cssRules); } catch (e) {}"
        "  }"
        "  const counts = {}, where = {};"
        "  const all = document.querySelectorAll('*');"
        "  all.forEach(el => {"
        "    const v = getComputedStyle(el).viewTransitionName;"
        "    if (!v || v === 'none') return;"
        "    counts[v] = (counts[v] || 0) + 1;"
        "    (where[v] = where[v] || []).push("
        "      el.tagName.toLowerCase() + '.' + (el.className.toString() || '-'));"
        "  });"
        "  return {declared: declared, counts: counts, where: where,"
        "          elements: all.length};"
        "}")
    base_url = server.base_url()
    _login(page, base_url)
    for route in VIEW_TRANSITION_ROUTES:
        page.goto(base_url + route)
        page.locator("main").first.wait_for(state="visible")
        seen = page.evaluate(probe)
        if seen["elements"] < 20:
            raise AssertionError(
                "expected a rendered document on %s, found %d elements — "
                "with fewer, this check measures nothing"
                % (route, seen["elements"]))
        declared = sorted(set(seen["declared"]))
        if declared != sorted(VIEW_TRANSITION_NAMES):
            raise AssertionError(
                "the stylesheet served to %s declares the view-transition "
                "names %r, but this file pins %r (VIEW_TRANSITION_NAMES) — a "
                "name added, renamed or dropped in companion/static/style.css "
                "must be a deliberate edit here too, because every assertion "
                "below is empty for a name nobody declares"
                % (route, declared, sorted(VIEW_TRANSITION_NAMES)))
        # Duplicates FIRST, and over every computed name rather than
        # only the declared three: the browser's own `root` name on the
        # document element counts here too.
        for name, count in sorted(seen["counts"].items()):
            if count > 1:
                raise AssertionError(
                    "the view-transition name %r resolves to %d elements on "
                    "%s (%r) — names must be unique per rendered document or "
                    "the browser drops the transition silently; if this is a "
                    "navigation selector, note that more than one navigation "
                    "landmark is in the DOM of every authenticated page at "
                    "once, hidden from each other only by a media query"
                    % (name, count, route, seen["where"][name]))
        for name, routes in sorted(VIEW_TRANSITION_NAMES.items()):
            got = seen["counts"].get(name, 0)
            if route in routes and got != 1:
                raise AssertionError(
                    "expected exactly one element carrying the view-transition "
                    "name %r on %s, found %d — its selector matches nothing "
                    "there any more, so the transition it names is gone and "
                    "every uniqueness assertion about it is vacuous"
                    % (name, route, got))
            if route not in routes and got:
                raise AssertionError(
                    "the view-transition name %r now resolves on %s, which "
                    "VIEW_TRANSITION_NAMES does not list for it — widening a "
                    "named selector is a deliberate edit, not a side effect"
                    % (name, route))


@pytest.mark.parametrize("reduced,want_match", [(True, False), (False, True)],
                          ids=["reduced-motion", "no-preference"])
def test_the_view_transition_is_off_under_reduced_motion(new_context, server, reduced, want_match):
    """the cross-document view transition is genuinely OPT-OUT: its at-rule is the
    only one in the CSSOM, declares navigation: auto, and is nested inside a
    media rule whose own conditionText — read off the at-rule's parent, never
    from a bare matchMedia() call, which would pass with the at-rule unwrapped —
    evaluates FALSE in a reduced_motion='reduce' context and TRUE in a default
    one, so a visitor who asked for less motion never has the transition set up
    at all rather than having one set up and run fast (D3+D10/CFG-33,
    23-04-PLAN.md Task 2)"""
    # ASKING THE CSSOM, NOT WATCHING THE PIXELS. A visual assertion here
    # would be a timing test on the slowest file in the suite, and an
    # intermittently red check teaches people to ignore it. AND NOT
    # matchMedia() ON ITS OWN, which would be the vacuous version of this
    # check: `matchMedia('(prefers-reduced-motion: no-preference)')
    # .matches` is false in a reduce context no matter what this app's
    # stylesheet says, so it would pass with the at-rule sitting
    # unwrapped at the top level. The condition evaluated below is read
    # OFF THE AT-RULE'S OWN PARENT RULE, so the check fails unless the
    # at-rule is genuinely nested inside a media rule whose condition is
    # false under reduced motion and true otherwise.
    probe = (
        "() => {"
        "  const found = [];"
        "  const walk = (rules, parent) => {"
        "    for (const r of rules) {"
        "      if (r.constructor.name === 'CSSViewTransitionRule') {"
        "        const cond = parent && parent.conditionText"
        "          ? parent.conditionText : null;"
        "        found.push({nav: r.navigation, text: r.cssText,"
        "                    parent: parent ? parent.constructor.name : null,"
        "                    cond: cond,"
        "                    matches: cond === null"
        "                      ? null : matchMedia(cond).matches});"
        "      }"
        "      if (r.cssRules) walk(r.cssRules, r);"
        "    }"
        "  };"
        "  for (const sheet of document.styleSheets) {"
        "    try { walk(sheet.cssRules, null); } catch (e) {}"
        "  }"
        "  return found;"
        "}")
    base_url = server.base_url()
    extra = {"reduced_motion": "reduce"} if reduced else {}
    context = new_context(**extra)
    try:
        page = context.new_page()
        _login(page, base_url)
        page.goto(base_url + "/")
        page.locator("main").first.wait_for(state="visible")
        found = page.evaluate(probe)
        where = ("a reduced_motion='reduce' context" if reduced
                 else "a default (no-preference) context")
        if len(found) != 1:
            raise AssertionError(
                "expected exactly one view-transition at-rule in the CSSOM of "
                "the stylesheet served to %s, found %d (%r) — zero means the "
                "feature is gone, more than one means two rules disagree about "
                "whether navigations animate" % (where, len(found), found))
        rule = found[0]
        if rule["nav"] != "auto":
            raise AssertionError(
                "the view-transition at-rule declares navigation %r in %s — "
                "only 'auto' actually animates a navigation" % (rule["nav"], where))
        if rule["parent"] != "CSSMediaRule" or not rule["cond"]:
            raise AssertionError(
                "the view-transition at-rule sits at the top level of the "
                "stylesheet in %s (parent rule %r) rather than inside a media "
                "rule — so it is LIVE UNDER REDUCED MOTION: style.css's global "
                "`*, *::before, *::after` override matches ELEMENTS and never "
                "reaches the ::view-transition pseudo-element tree, which is "
                "why this wrapper is the opt-out and not a duplicate of it"
                % (where, rule["parent"]))
        if "prefers-reduced-motion" not in rule["cond"]:
            raise AssertionError(
                "the view-transition at-rule is nested in `@media %s` in %s, "
                "which says nothing about motion preference — the wrapper "
                "exists to prevent the transition being SET UP for a visitor "
                "who asked for less motion" % (rule["cond"], where))
        if rule["matches"] is not want_match:
            raise AssertionError(
                "the media condition guarding the view-transition at-rule "
                "(`%s`) evaluates to %r in %s, expected %r — under reduced "
                "motion the transition must never be set up, and under "
                "no-preference it must be, or the feature is wrapped into "
                "something nobody ever sees"
                % (rule["cond"], rule["matches"], where, want_match))
    finally:
        context.close()


# ===========================================================================
# 23-05-PLAN.md Task 3 (D14/CFG-34): the ticker, proven in a browser. The
# claim is "the user sees it change, and a background tab costs nothing"
# — so every assertion below reads element TEXT twice with a real wait
# between the reads, never a timer internal.
# ===========================================================================

TICK_SETTLE_MS = 2200
FRESHNESS_AGE = ".page-header__freshness time[data-relative]"


def test_the_relative_age_ticks_in_a_real_tab(page, server):
    """the Health freshness line's <time data-relative> text ADVANCES within ~2s in
    a real visible tab, starting from text the server already rendered, ending
    on something that is no longer the server's own clock (the enhancement
    really did take over), carrying no raw quantity placeholder, and leaving the
    prefix and pill beside it untouched (D14/CFG-34, 23-05-PLAN.md Task 3; the
    clock-to-age half added by 23-06-PLAN.md)"""
    base_url = server.base_url()
    _login(page, base_url)
    page.goto(base_url + "/health")
    page.locator(FRESHNESS_AGE).first.wait_for(state="attached")
    first = page.eval_on_selector(FRESHNESS_AGE, "el => el.textContent")
    # The server-rendered floor: the element already reads something
    # correct before any script runs.
    if not first or not first.strip():
        raise AssertionError(
            "expected the freshness age to be rendered by the SERVER before "
            "anything ticks — the no-JS floor is this element's own text, "
            "got %r" % (first,))
    if "#" in first:
        raise AssertionError(
            "expected the rendered age to carry no quantity placeholder — "
            "the wordings are filled server-side and by the script, never "
            "shown raw, got %r" % (first,))
    page.wait_for_timeout(TICK_SETTLE_MS)
    second = page.eval_on_selector(FRESHNESS_AGE, "el => el.textContent")
    if first == second:
        raise AssertionError(
            "expected the freshness age to ADVANCE within %dms in a visible "
            "tab, read %r then %r — a page that says 'Updated 14:32' is "
            "telling the truth about a moment and saying nothing about now "
            "(D14/D22)" % (TICK_SETTLE_MS, first, second))
    if "#" in second:
        raise AssertionError("the ticked text carries a raw quantity placeholder: %r" % (second,))
    # 23-06-PLAN.md: the other half of the same contract the no-JS check
    # below states. The server renders a CLOCK here; with scripts on the
    # ticker must have replaced it with a live age, so the settled text
    # must NOT still be the clock the element's own datetime resolves
    # to. The FIRST read is deliberately not pinned to the clock: the
    # ticker's first repaint lands one second after load and this
    # harness cannot promise to read faster than that.
    instant = page.eval_on_selector(FRESHNESS_AGE, "el => el.getAttribute('datetime')")
    parsed = layout.parse_iso(instant or "")
    if parsed is None:
        raise AssertionError(
            "expected a machine-readable datetime for the ticker to read, "
            "got %r" % (instant,))
    clock = layout.local_clock_text(parsed, now_parsed=parsed)
    if second == clock:
        raise AssertionError(
            "expected the ticker to have replaced the server's clock %r with "
            "a live age within %dms — the clock is the no-JS floor, the age "
            "is the enhancement over it (D14/D22)" % (clock, TICK_SETTLE_MS))
    # It rewrote ONE element's text and nothing else: the prefix and the
    # pill beside it are untouched.
    wrapper = page.eval_on_selector(".page-header__freshness", "el => el.textContent")
    if "Updated" not in wrapper:
        raise AssertionError(
            "expected the freshness line's own prefix to survive the tick — "
            "the ticker writes textContent on the <time> element and must "
            "never rewrite a sibling, got %r" % (wrapper,))


def test_a_hidden_tab_does_no_work_and_catches_up_on_return(page, server):
    """a page reporting itself hidden runs no ticker work at all — its age is
    byte-identical across ~2s, against a control proving the same age DOES move
    while visible — and on becoming visible again it is repainted immediately
    rather than after waiting out an interval (T-23-14, 23-05-PLAN.md Task 3;
    the visibility mechanism and its limits are stated in this check's own
    comment)"""
    # WHICH MECHANISM, AND WHY THIS ONE. Two real ways to hide a page
    # were tried in this harness first and neither works: a second page
    # in the same context taking focus leaves the first page's
    # document.visibilityState at "visible" in headless Chromium, and
    # CDP's Emulation.setPageVisibilityOverride is not present in this
    # Chromium at all. So the page's own visibility state is overridden
    # in-page and a real `visibilitychange` Event is dispatched on
    # document — which is what the browser itself dispatches. What that
    # simulates is the BROWSER'S REPORT; what it exercises is the
    # shipped script's own listener and its own document.hidden reads,
    # unmodified.
    base_url = server.base_url()
    _login(page, base_url)
    page.goto(base_url + "/health")
    page.locator(FRESHNESS_AGE).first.wait_for(state="attached")
    read = "() => document.querySelector(%r).textContent" % FRESHNESS_AGE
    # CONTROL FIRST. Without this the check passes on a page whose
    # element never changes for any reason at all.
    control_before = page.evaluate(read)
    page.wait_for_timeout(TICK_SETTLE_MS)
    control_after = page.evaluate(read)
    if control_before == control_after:
        raise AssertionError(
            "control: the age did not move in a VISIBLE tab (%r twice), so "
            "the hidden-tab assertion below would measure nothing"
            % (control_before,))
    page.evaluate(
        "() => {"
        "  Object.defineProperty(document, 'hidden',"
        "    {configurable: true, get: () => true});"
        "  Object.defineProperty(document, 'visibilityState',"
        "    {configurable: true, get: () => 'hidden'});"
        "  document.dispatchEvent(new Event('visibilitychange'));"
        "}")
    hidden_before = page.evaluate(read)
    page.wait_for_timeout(TICK_SETTLE_MS)
    hidden_after = page.evaluate(read)
    if hidden_before != hidden_after:
        raise AssertionError(
            "expected the age NOT to change while the page reports itself "
            "hidden, read %r then %r over %dms — a once-a-second timer in "
            "every background tab forever is the one real cost this file "
            "carries (T-23-14)" % (hidden_before, hidden_after, TICK_SETTLE_MS))
    # Back in view: the repaint happens IMMEDIATELY, well inside one
    # tick. A tab returning after a long hidden stretch showing a stale
    # age is the same defect this file exists to remove, just later on.
    page.evaluate(
        "() => {"
        "  Object.defineProperty(document, 'hidden',"
        "    {configurable: true, get: () => false});"
        "  Object.defineProperty(document, 'visibilityState',"
        "    {configurable: true, get: () => 'visible'});"
        "  document.dispatchEvent(new Event('visibilitychange'));"
        "}")
    returned = page.evaluate(read)
    if returned == hidden_after:
        raise AssertionError(
            "expected the age to be repainted IMMEDIATELY on becoming "
            "visible again rather than after waiting out an interval, still "
            "read %r" % (returned,))


@pytest.mark.parametrize("lang", ["en", "fr"])
def test_the_relative_age_is_server_rendered_and_static_without_scripts(new_context, server, lang):
    """with scripts blocked at 360px, in BOTH languages, the freshness line still
    renders exactly one <time data-relative> carrying the server's own CLOCK —
    derived from the element's own datetime, never the ladder's zero bucket and
    never any age, because nothing there can advance one — and it does NOT
    change over ~2s, which is what separates an intact no-JS floor from an
    enhancement that quietly took over (CFG-38, 23-05-PLAN.md Task 3; the
    frozen-zero half reversed by 23-06-PLAN.md)"""
    base_url = server.base_url()
    # 25-02-PLAN.md: needs the UI-language cookie set before the first
    # navigation, which is what _no_js_page()'s own `cookies` parameter
    # is for.
    with _no_js_page(
            new_context, base_url, "/health",
            viewport=VIEWPORT_MIN_SUPPORTED,
            cookies=[{
                "name": auth.UI_LANG_COOKIE_NAME,
                "value": lang, "url": base_url}]) as page:
        found = page.locator(FRESHNESS_AGE).count()
        if found != 1:
            raise AssertionError(
                "lang=%s: expected exactly one server-rendered <time "
                "data-relative> in the freshness line with scripts blocked, "
                "found %d" % (lang, found))
        seen = page.eval_on_selector(
            FRESHNESS_AGE, "el => [el.textContent, el.getAttribute('datetime')]")
        first, instant = seen[0], seen[1]
        # 23-06-PLAN.md (23-05's own finding 2): this assertion is
        # REVERSED on purpose. 23-05 required the ladder's zero bucket
        # here, which is what a page with no ticker freezes on —
        # "Updated 0s ago", true at load and false one second later. The
        # server now renders the CLOCK as this element's text and the
        # ticker replaces it with the live age when it runs. The
        # expected value is derived from the element's OWN datetime
        # attribute rather than from a wall clock read in this process,
        # so the assertion cannot flake across a minute boundary.
        parsed = layout.parse_iso(instant or "")
        if parsed is None:
            raise AssertionError(
                "lang=%s: expected a machine-readable datetime on the "
                "freshness element for the ticker to read, got %r" % (lang, instant))
        expected = layout.local_clock_text(parsed, now_parsed=parsed)
        if first != expected:
            raise AssertionError(
                "lang=%s: expected the scripts-blocked page to read the "
                "server's own clock %r — a value that stays true with no "
                "script to advance it — got %r" % (lang, expected, first))
        frozen_zero = layout.relative_age_text(0, lang=lang)
        if first == frozen_zero:
            raise AssertionError(
                "lang=%s: the scripts-blocked page reads the ladder's zero "
                "bucket %r, which nothing here can ever advance — that is "
                "A-20's frozen zero, not a no-JS floor" % (lang, frozen_zero))
        if " ago" in first or "il y a" in first:
            raise AssertionError(
                "lang=%s: the scripts-blocked page reads a relative age "
                "(%r); an age is a claim about NOW and only the ticker can "
                "keep it true" % (lang, first))
        if "#" in first:
            raise AssertionError(
                "lang=%s: a raw quantity placeholder reached the page: %r" % (lang, first))
        # PRESENCE ALONE IS NOT THE CHECK. An element that is present AND
        # changing would mean the enhancement had silently taken over in
        # a context that is supposed to have none.
        page.wait_for_timeout(TICK_SETTLE_MS)
        second = page.eval_on_selector(FRESHNESS_AGE, "el => el.textContent")
        if first != second:
            raise AssertionError(
                "lang=%s: the age CHANGED on a scripts-blocked page (%r -> "
                "%r) — no script can be running there, so something else is "
                "rewriting it" % (lang, first, second))
        if page.viewport_size["width"] != VIEWPORT_MIN_SUPPORTED["width"]:
            raise AssertionError("expected the measurement at the 360px contract floor")
