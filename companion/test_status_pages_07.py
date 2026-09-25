"""Companion status-page tests, last slice: the tab bar's margin-fit/More-
sheet/French-label contracts, freshness.js's backoff ladder and breathing-
dot mechanism, the Health-tile/Frame-strip agreement, the two server-
rendered switches, and two end-to-end checks.

CSS/JS checks fetch served bytes from companion/app.py; everything else
calls companion.layout/companion.pages.health_page directly, in-process.
"""
import io
import re
from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image

import companion.app as app
import companion.i18n_fr.nav as i18n_fr_nav
import companion.test_status_pages_helpers as shp
from companion import illustration_normalize, layout, prefs
from companion.pages import airlines_page, config_page, health_page, home_page
from companion_app_server import get, login, served_asset, served_stylesheet
from companion_markup import css_rules, custom_properties, declarations_for, rules_with_selector
from server import device_config, history_db
from server.plane import illustrations


# --- module-scoped read-only server, for the served-CSS/JS checks only -----

@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def css_text(_module_server):
    return served_stylesheet(_module_server)


@pytest.fixture(scope="module")
def freshness_js(_module_server):
    return served_asset(_module_server, "/static/freshness.js")


# --- shared constants/helpers, local to this part ---------------------------

_TAB_BAR_MEDIA = ("@media (max-width: 959.98px)",)
_REDUCED_MOTION = ("@media (prefers-reduced-motion: reduce)",)
_NAV_STATUS_DEVICE_CFG = {"display_enabled": True, "quiet_hours_enabled": False}
_PARIS_TZ = timezone(timedelta(hours=1))


def _frame_strip_ctx(last_checkin_ts, device_config_dict, now):
    return {
        "last_checkin_ts": last_checkin_ts, "device_config": device_config_dict, "now": now,
    }


# =============================================================================
# The 2026-09-17 audit measured "Compagnies"
# (10 characters) needing 65px at .tab-bar__label's 11px size, against only
# 62px available in a 78px cell once the pill's old 8px-per-side margin was
# subtracted — the label truncated. This check re-derives every one of
# those numbers from the SERVED stylesheet's own structural declarations
# (never hardcoding 8, 65 or 78) and proves the fit as a RELATIONSHIP, plus
# proves the 78x56px cell itself is untouched by the margin edit, as a
# SEPARATE, independently-mutable assertion.
# =============================================================================

def test_tab_bar_pill_horizontal_margin_lets_the_longest_label_fit(css_text):
    """the .tab-bar__pill's horizontal margin, resolved from style.css's own --space-xs/--space-sm
    tokens, leaves at least the longest NAV_GROUPS label's own required width (a measured
    6.5px/character advance derived from the 2026-09-17 audit's real 'Compagnies' figure, floored
    at that audit's own 65px) inside the tab cell at the app's 360px floor viewport, while
    `.tab-bar__link`'s own 56px height and `flex: 1 1 0` width basis stay byte-identical"""
    tokens = custom_properties(css_text, ":root")
    pill_decls = declarations_for(css_text, ".tab-bar__pill", at_rules=_TAB_BAR_MEDIA)
    margin_value = pill_decls.get("margin")
    assert margin_value, "expected .tab-bar__pill to declare a margin shorthand"
    margin_match = re.search(
        r"var\(--([a-z-]+)\)\s+(?:var\(--([a-z-]+)\)|"
        r"calc\(var\(--([a-z-]+)\)\s*/\s*(\d+)\))",
        margin_value)
    assert margin_match, "could not parse .tab-bar__pill's margin shorthand: %r" % (margin_value,)
    _vertical_token, plain_token, calc_token, divisor = margin_match.groups()
    if plain_token:
        token_name = "--" + plain_token
        assert token_name in tokens, "margin shorthand referenced an unknown token %r" % (plain_token,)
        horizontal_margin_px = float(tokens[token_name][:-2])
    else:
        token_name = "--" + calc_token
        assert token_name in tokens, "margin shorthand referenced an unknown token %r" % (calc_token,)
        horizontal_margin_px = float(tokens[token_name][:-2]) / float(divisor)

    # The cell's own resolved box, asserted independently of the margin
    # above: mutating this must fail on its own, proving the tap-area
    # invariant is not merely a side effect of the fit math.
    link_decls = declarations_for(css_text, ".tab-bar__link", at_rules=_TAB_BAR_MEDIA)
    assert link_decls.get("height") == "56px", (
        "expected .tab-bar__link's own resolved height to stay 56px (the 78x56px cell, unchanged "
        "by the pill's margin edit), got %r" % (link_decls,))
    assert link_decls.get("flex") == "1 1 0", (
        "expected .tab-bar__link's own width basis (flex: 1 1 0) to stay byte-identical to its "
        "pre-task value, got %r" % (link_decls,))

    label_decls = declarations_for(css_text, ".tab-bar__label", at_rules=_TAB_BAR_MEDIA)
    assert label_decls.get("font-size") == "11px", (
        "expected .tab-bar__label's font-size to still resolve to 11px, got %r" % (label_decls,))

    unlabelled_entries = [
        (route, label) for group_label, entries in layout.NAV_GROUPS if not group_label
        for route, label in entries]
    cell_count = len(unlabelled_entries) + 1  # the everyday destinations plus one "More" cell

    # The app's own contract floor (design_direction: "Minimum supported
    # viewport width: 360 px") is the tightest case a smaller viewport
    # gives a smaller cell, so this is the worst width the fit must
    # survive, not merely the audit's own 390px device.
    FLOOR_VIEWPORT_PX = 360
    cell_width_px = FLOOR_VIEWPORT_PX / cell_count
    available_px = cell_width_px - (2 * horizontal_margin_px)

    # The longest label across BOTH shipped languages — read from
    # layout.NAV_GROUPS and companion.i18n_fr.nav.CATALOG, never typed
    # literally, so a future longer label re-runs this same arithmetic
    # rather than silently going unchecked.
    candidate_labels = []
    for _route, label in unlabelled_entries:
        candidate_labels.append(label)
        candidate_labels.append(i18n_fr_nav.CATALOG.get(label, label))
    candidate_labels.append(layout.TAB_BAR_MORE_LABEL)
    candidate_labels.append(
        i18n_fr_nav.CATALOG.get(layout.TAB_BAR_MORE_LABEL, layout.TAB_BAR_MORE_LABEL))
    longest_label = max(candidate_labels, key=len)

    # Per-character advance: MEASURED, not modelled — the audit's own real
    # figure for "Compagnies" (10 characters) needing 65px at this label's
    # 11px font-size gives 65 / 10 = 6.5px/character.
    PER_CHARACTER_ADVANCE_PX = 6.5
    AUDIT_MEASURED_FLOOR_PX = 65  # "Compagnies" at 11px, 2026-09-17 audit
    modelled_requirement_px = PER_CHARACTER_ADVANCE_PX * len(longest_label)
    required_px = max(modelled_requirement_px, AUDIT_MEASURED_FLOOR_PX)

    assert available_px >= required_px, (
        "expected the available label width (%.1fpx = %.1fpx cell [%dpx viewport / %d cells] - "
        "2x%.1fpx margin) to be at least %.1fpx (the longest label %r's own requirement, floored "
        "at the audit's measured %dpx) but it was not (CFG-82, 29-02-PLAN.md)"
        % (available_px, cell_width_px, FLOOR_VIEWPORT_PX, cell_count, horizontal_margin_px,
           required_px, longest_label, AUDIT_MEASURED_FLOOR_PX))


def test_tab_bar_more_sheet_opens_upward_and_reuses_the_dropdown_row(css_text):
    """the More sheet opens upward from the fixed bar (absolute, bottom: 100%, right: 0) on the nav
    surface with the overlay shadow, reuses .mobile-nav__link's 44px/16px geometry rather than
    restating it, and leaves .mobile-nav's in-flow flex-basis push-down untouched. The
    legacy check's own stylesheet-comment assertion ("the stylesheet
    itself records why this is not a reversal of the rejected-overlay verdict") is dropped: guard
    G1 already rules out a CSS comment as a source of behaviour, and the geometry assertions below
    are what the comment was describing."""
    sheet = declarations_for(css_text, ".tab-bar__more-panel", at_rules=_TAB_BAR_MEDIA)
    assert sheet.get("position") == "absolute"
    assert sheet.get("bottom") == "100%"
    assert sheet.get("right") == "0"
    assert sheet.get("background") == "var(--color-secondary)"
    assert sheet.get("box-shadow") == "var(--shadow-card-hover)"
    # The sheet's rows REUSE .mobile-nav__link's geometry rather than
    # restating it — proven structurally: if the panel's OWN rule declared
    # these, they would appear in its own parsed declarations above.
    for redeclared in ("min-height", "font-size"):
        assert redeclared not in sheet, (
            "the sheet must REUSE .mobile-nav__link's geometry, never restate it, found %r" % (redeclared,))

    mobile_nav_decls = declarations_for(css_text, ".mobile-nav")
    assert mobile_nav_decls.get("flex-basis") == "100%", (
        "the dropdown's in-flow push-down mechanism must stay exactly as it is — this plan does "
        "not reopen the 06.6.1-06 verdict")


def test_french_tab_bar_labels_and_landmark():
    """under lang='fr' every tab-bar label reads French — Accueil / Affichage / Vols / Compagnies /
    Plus, with État and Appareil inside the More sheet — and the landmark name is
    'Navigation principale'"""
    device_cfg = {"display_enabled": True, "quiet_hours_enabled": False}
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = layout.page_shell(
            title="T", active="flights", body="", device_config=device_cfg)
    finally:
        prefs.set_request_prefs(lang="en")
    start = rendered.index('<nav class="tab-bar"')
    bar = rendered[start:rendered.index("</nav>", start)]
    assert 'aria-label="Navigation principale"' in bar, (
        "expected the tab bar's landmark name in French (CFG-29 must not regress), got %r"
        % (bar[:120],))
    for english, french in (
            ("Home", "Accueil"), ("Display", "Affichage"), ("Flights", "Vols"),
            ("Airlines", "Compagnies"), ("More", "Plus"),
            ("Health", "État"), ("Device", "Appareil")):
        assert ">%s<" % french in bar, (
            "expected the %r cell to read %r in French, got %r" % (english, french, bar))
        assert ">%s<" % english not in bar, (
            "expected no leftover English %r label under a French request" % (english,))


def test_nav_status_is_a_span_on_home_and_a_link_everywhere_else():
    """the nav state reminder renders as a <span> with no href on Home, announcing ONLY the state,
    and stays an <a href="/" > with its destination-naming label everywhere else — in both nav
    copies, each with its two nowrap segments"""
    home = layout.page_shell(
        title="Home", active="home", body="", ui_theme="auto",
        device_config=_NAV_STATUS_DEVICE_CFG)
    assert home.count('<span class="nav-status text-label"') == 2, (
        "expected the reminder to render as a <span> in BOTH nav copies on Home, got %d"
        % home.count('<span class="nav-status text-label"'))
    assert '<a class="nav-status text-label"' not in home, "expected no <a> reminder anywhere on Home"
    home_label = layout.i18n.t(layout.NAV_STATUS_ARIA_LABEL_TEXT)
    assert home_label not in home, (
        "the destination-naming label must not survive on Home — it is the claim, not the "
        "wording, that is the defect")
    for match in re.finditer(
            r'<span class="nav-status text-label" aria-label="([^"]*)"', home):
        announced = match.group(1)
        expected = "%s%s%s" % (
            layout.i18n.t(layout.NAV_SCREEN_ON_TEXT),
            layout.NAV_STATUS_SEPARATOR_TEXT,
            layout.i18n.t(layout.NAV_QUIET_OFF_TEXT))
        assert announced == expected, (
            "expected the Home reminder to announce only the state (%r), got %r"
            % (expected, announced))

    elsewhere = layout.page_shell(
        title="Display", active="display", body="", ui_theme="auto",
        device_config=_NAV_STATUS_DEVICE_CFG)
    assert elsewhere.count(
        '<a class="nav-status text-label" href="%s"' % layout.HOME_ROUTE) == 2, (
        "expected the reminder to stay a link to Home in both nav copies elsewhere")
    assert '<span class="nav-status text-label"' not in elsewhere, "expected no <span> reminder off Home"
    assert layout.escape_html(layout.i18n.t(layout.NAV_STATUS_ARIA_LABEL_TEXT)) in elsewhere, (
        "expected the destination-naming label off Home")

    # The two segments are separate nowrap spans in both shapes, so the
    # line can only ever break BETWEEN them.
    for rendered, shape in ((home, "span"), (elsewhere, "link")):
        assert rendered.count('<span class="nav-status__segment">') == 4, (
            "expected two segments per nav copy in the %s shape, got %d"
            % (shape, rendered.count('<span class="nav-status__segment">')))


def test_one_open_dropdown_max_height_and_no_dead_dropdown_nav_rule(css_text):
    """exactly ONE open-state max-height governs the dropdown (320px, pinned against a measured
    165px of reduced French content at 390px — both the 420px and 640px values are gone, not
    re-tuned), the dropdown's dead nav selectors are deleted while .mobile-nav__link survives for
    the tab bar's sheet, and .nav-status is a wrapping flex row of nowrap segments whose hover
    underline is anchor-scoped"""
    open_rules = rules_with_selector(css_text, ".js .mobile-nav--open")
    assert len(open_rules) == 1, (
        "T11: expected exactly ONE open-state dropdown rule in the whole file, got %d"
        % len(open_rules))
    open_decls = declarations_for(css_text, ".js .mobile-nav--open")
    assert list(open_decls.keys()) == ["max-height"], (
        "expected exactly one max-height declaration for the open state, got %r" % (open_decls,))
    assert open_decls.get("max-height") == "320px", (
        "expected the measured single value (the reduced French content at 390px measures "
        "165px), got %r" % (open_decls,))

    # The dropdown's own nav region is deleted, not left as a dead
    # selector — its rule and its .nav-group override both go.
    for dead in (".mobile-nav__nav", ".mobile-nav__nav .nav-group"):
        assert not rules_with_selector(css_text, dead), "expected the dead selector %r to be deleted" % (dead,)
    # ...but .mobile-nav__link survives, because the tab bar's More sheet
    # reuses it verbatim.
    assert rules_with_selector(css_text, ".mobile-nav__link"), (
        ".mobile-nav__link must survive — the tab bar's More sheet reuses its 44px/16px geometry")

    # B10's own mechanism, read from the rule rather than assumed.
    status_decls = declarations_for(css_text, ".nav-status")
    assert status_decls.get("display") == "flex"
    assert status_decls.get("flex-wrap") == "wrap"
    assert status_decls.get("gap") == "0 var(--space-xs)"
    segment_decls = declarations_for(css_text, ".nav-status__segment")
    assert segment_decls.get("white-space") == "nowrap", "expected each segment to be nowrap"
    # The hover underline is scoped to the ANCHOR: a <span> that
    # underlines under the pointer claims an interactivity it does not
    # have. Exact selector-string membership (not a substring probe)
    # distinguishes "a.nav-status:hover" from ".nav-status:hover" cleanly
    # — the boundary problem the legacy regex needed a lookaround for.
    assert not rules_with_selector(css_text, ".nav-status:hover"), (
        "expected the hover underline scoped to a.nav-status, not every reminder")
    assert rules_with_selector(css_text, "a.nav-status:hover"), (
        "expected the anchor-scoped hover underline")


def test_style_css_carries_no_stray_comment_terminator(css_text):
    """companion/static/style.css carries zero stray comment terminators and ends outside a comment
    — the structural guard for a real parse-error class that drops whole rules while leaving the
    source text a string-comparison harness reads as correct.

    Guards against a real defect this plan found and fixed: an earlier edit appended a note to an
    existing block comment AFTER that comment's own closing marker, leaving a terminator with no
    opener — everything from it to the next brace then parsed as part of the following selector,
    silently dropping the rule that follows. No parsed-rule assertion could see this: the file
    still contains every declaration such a check asks about. The scan runs over the SERVED
    stylesheet's raw character stream (never a disk read) because this is exactly the shape a real
    CSS parser cannot see through either."""
    pos = 0
    line = 1
    in_comment = False
    strays = []
    while pos < len(css_text):
        ch = css_text[pos]
        if ch == "\n":
            line += 1
            pos += 1
            continue
        if not in_comment and css_text.startswith("/*", pos):
            in_comment = True
            pos += 2
            continue
        if in_comment and css_text.startswith("*/", pos):
            in_comment = False
            pos += 2
            continue
        if not in_comment and css_text.startswith("*/", pos):
            strays.append(line)
            pos += 2
            continue
        pos += 1
    assert not strays, (
        "companion/static/style.css carries %d comment terminator(s) with no opener, at line(s) "
        "%r — everything from each one to the next brace parses as a selector and silently drops "
        "the rule that follows" % (len(strays), strays))
    assert not in_comment, "companion/static/style.css ends inside an unterminated block comment"


def test_every_disclosure_has_a_marker_and_no_header_claims_to_stick(css_text):
    """every <details> carries an explicit summary::before chevron that rotates on [open] through a
    child combinator — including the bottom tab bar's More summary, where it is taken out of flow
    so a marker cannot narrow the cell, and with its own inverted rotation because that sheet opens
    upward — with the global reduced-motion override covering it and no redundant per-rule block
    added; and no .data-table-wrap th rule survives to claim sticky positioning a wrapper with no
    height could never provide"""
    # --- T3: the marker exists, and it rotates ------------------------
    marker = declarations_for(css_text, "summary::before")
    assert marker.get("content") == '""', "expected an explicit summary::before disclosure marker (T3)"
    assert marker.get("flex") == "none", (
        "expected the marker to declare flex: none — it is a flex item of the summary row and a "
        "long label would otherwise shrink it to a sliver (T3)")
    assert "rotate(" in marker.get("transform", ""), "expected the closed-state marker to be a rotated box (T3)"

    # And the card summary REUSES that marker rather than drawing a
    # second one. A rule of its own that redeclared the geometry would be
    # two chevrons to keep in step, which is the thing the single shared
    # rule exists to prevent.
    card_marker = declarations_for(css_text, ".history-card__summary::before")
    for redeclared in ("content", "width", "height", "border-right", "border-bottom"):
        assert redeclared not in card_marker, (
            "expected the card summary's marker override to change only WHERE the shared "
            "chevron sits, not to redraw it (found %r in %r) — two chevrons is two things to "
            "keep in step (T3)" % (redeclared, card_marker))

    open_marker = declarations_for(css_text, "details[open] > summary::before")
    assert "rotate(" in open_marker.get("transform", ""), "expected the open state to rotate the marker (T3)"
    assert not rules_with_selector(css_text, "details[open] summary::before"), (
        "expected a CHILD combinator on the open-state rule — a descendant one rotates a parent "
        "disclosure's marker when a nested one opens (T3)")

    # The marker reaches the tab bar's "More" summary too, where it is
    # taken out of flow so a 6px marker cannot narrow a 78x56px cell's
    # centred icon-and-label stack.
    tab_marker = declarations_for(
        css_text, ".tab-bar__more > .tab-bar__link::before", at_rules=_TAB_BAR_MEDIA)
    assert tab_marker.get("position") == "absolute", (
        "expected the tab bar's More marker to be positioned out of flow — in flow it is a flex "
        "item beside .tab-bar__pill and compresses the cell (T3)")
    assert rules_with_selector(css_text, ".tab-bar__more[open] > .tab-bar__link::before"), (
        "expected the tab bar's More marker to have its own open state — the sheet opens UPWARD, "
        "so the global right-closed/down-open convention points away from it (T3)")

    # The rotation is a transform and the fade is a transition, both
    # already covered by the single global reduced-motion override — the
    # structural replacement for the legacy raw "count == 2" scan (see
    # this module's own docstring): the ONE global override and the
    # `.js .mobile-nav` opt-out both exist, and summary::before (this
    # task's own subject) carries no third, redundant override of its own.
    reduced_motion_global = declarations_for(css_text, "*", at_rules=_REDUCED_MOTION)
    assert reduced_motion_global.get("transition-duration") == "0.01ms !important", (
        "expected the one global reduced-motion override to still zero every transition, got %r"
        % (reduced_motion_global,))
    mobile_nav_opt_out = declarations_for(css_text, ".js .mobile-nav", at_rules=_REDUCED_MOTION)
    assert mobile_nav_opt_out.get("transition") == "none", (
        "expected the pre-existing .js .mobile-nav transition opt-out to survive, got %r"
        % (mobile_nav_opt_out,))
    assert declarations_for(css_text, "summary::before", at_rules=_REDUCED_MOTION) == {}, (
        "T3 adds no per-rule reduced-motion override for summary::before — the global override "
        "above already covers its transition")

    # --- T4: the false claim is gone -----------------------------------
    assert not rules_with_selector(css_text, ".data-table-wrap th"), (
        "expected NO .data-table-wrap th rule at all — its sticky claim could never engage "
        "inside a wrapper with no height, and its --color-canvas background existed only to "
        "serve that claim (T4)")
    wrap_decls = declarations_for(css_text, ".data-table-wrap")
    for forbidden in ("max-height", "height"):
        assert forbidden not in wrap_decls, (
            "expected .data-table-wrap to gain no height — T4 removes the false sticky claim "
            "rather than adding a second nested vertical scrollbar to four tables")


def test_refresh_loop_retries_with_backoff_and_says_so_neutrally(freshness_js, css_text):
    """freshness.js no longer stops dead on a failure: stopLoop() survives only as its definition and
    its two deliberate background-tab teardowns, a bounded exponential ladder starting AT the normal
    cadence (so a failing server sees a strictly decreasing rate) replaces it, a success resets the
    backoff, an in-flight guard stops two fetches racing, the swap skips unchanged regions and any
    region holding focus, the state badge is .banner__pill with the NEUTRAL .dot--off and no warn
    token anywhere in the file, style.css carries the .banner__pill[hidden] display guard the badge
    depends on, and both strings render onto <body> in both languages matching the script's own
    English fallbacks byte for byte"""
    code = shp.strip_js_line_and_block_comments(freshness_js)

    # --- the silent stop is gone from both failure paths ----------------
    assert code.count("stopLoop") == 3, (
        "expected exactly three stopLoop references in freshness.js code — its definition and its "
        "two DELIBERATE background-tab teardowns. Neither failure path may call it: that was "
        "T13's whole defect, a loop that stopped for the life of the page with nothing visible to "
        "say so. Got %d" % code.count("stopLoop"))
    for handler in ("failAndRetry", "succeed"):
        assert ("function %s(" % handler) in code, "expected freshness.js to define %s() (T13)" % handler

    # --- a real, bounded, DECREASING-rate ladder -------------------------
    assert "RETRY_CEILING_MS" in code and "Math.min(retryDelayMs * 2" in code, (
        "expected an exponential retry delay bounded by a stated ceiling — an unbounded ladder, "
        "or a fixed delay, is not what T-22-56 asks for")
    assert "RETRY_BASE_MS = AUTO_REFRESH_INTERVAL_MS" in code, (
        "expected the ladder to START at the normal cadence, never below it — the whole "
        "mitigation is that a failing server sees a strictly DECREASING request rate")
    assert "retryDelayMs = 0" in code, "expected a success to reset the backoff to zero (T13)"

    # --- the in-flight guard and the targeted swap -----------------------
    assert "var inFlight = false;" in code and "if (inFlight) {" in code, (
        "expected an in-flight guard — without it a slow response and a visibility catch-up can "
        "race, and the LAST to resolve wins the swap (T13)")
    assert "isEqualNode" in code, (
        "expected the swap to skip regions that did not change, compared with isEqualNode() — "
        "replacing an unchanged region destroys any focus inside it")
    assert "existing.contains(active)" in code, (
        "expected the swap to skip any region containing the focused element (T13)")
    for untouched in ("userIsInteracting", "visibilitychange", "AUTO_REFRESH_INTERVAL_MS = 45000"):
        assert untouched in code, "expected %r to survive T13 untouched" % (untouched,)

    # --- neutral, never a warning ---
    assert 'dot.className = "dot dot--off";' in code, (
        "expected the loop-state badge's dot to be the neutral .dot--off — a browser that lost "
        "its connection is not a device fault")
    assert 'badge.className = "banner__pill";' in code, "expected the badge to compose .banner__pill"
    builder_at = code.index("function stateBadge(")
    builder = code[builder_at:code.index("\n  }", builder_at)]
    for warn_token in ("warn", "error", "danger", "alert", "status-"):
        assert warn_token not in builder, (
            "the loop-state badge must be built from neutral classes only, found %r in "
            "stateBadge() — T13's state is never a warning" % (warn_token,))

    # --- the [hidden] guard the badge depends on ---------------------------
    guard = declarations_for(css_text, ".banner__pill[hidden]")
    assert guard.get("display") == "none", (
        "expected .banner__pill[hidden] to hide by display, not visibility — fourth consumer of "
        "this file's [hidden]-vs-display guard, after .dirty-bar, .refresh-pill and .login-reveal")

    # --- the copy, server-rendered, in BOTH languages ---------------------
    assert layout.REFRESH_PAUSED_TEXT == "Paused"
    assert layout.REFRESH_RECONNECTING_TEXT == "Reconnecting…"
    for text in (layout.REFRESH_PAUSED_TEXT, layout.REFRESH_RECONNECTING_TEXT):
        assert layout.i18n.t_lang(text, "fr") != text, "expected a French entry for %r" % (text,)
        assert layout.i18n.t_lang(text, "en") == text, "expected %r to round-trip unchanged in English" % (text,)
        assert ('"%s"' % text) in code, (
            "expected freshness.js's own English fallback for %r to match the server constant "
            "byte for byte" % (text,))
    try:
        for lang, expected_paused in (("en", "Paused"), ("fr", "En pause")):
            prefs.set_request_prefs(lang=lang)
            rendered = layout.page_shell(title="T", active="health", body="<p>x</p>", lang=lang)
            assert ('%s="%s"' % (layout.REFRESH_PAUSED_ATTR, expected_paused)) in rendered, (
                "expected the paused copy on <body> in %s, got neither" % lang)
            assert ('%s="' % layout.REFRESH_RECONNECTING_ATTR) in rendered, (
                "expected the reconnecting copy on <body> in %s" % lang)
    finally:
        prefs.set_request_prefs(lang="en")


def test_resolve_context_hidden_guard_present_after_base_rule(css_text):
    """style.css declares .resolve-context[hidden] { display: none; } after the base rule —
    without it, an author display declaration beats the UA [hidden] rule and every ordinary
    illustration's resolve-context block renders empty instead of hidden (
    Task 2)"""
    guard_rules = rules_with_selector(css_text, ".resolve-context[hidden]")
    assert len(guard_rules) == 1, (
        "expected exactly one .resolve-context[hidden] guard — .resolve-context declares "
        "display: grid, which always beats the user-agent [hidden] rule, so the block would "
        "render (empty) even when hidden, got %d occurrence(s)" % len(guard_rules))

    rules = css_rules(css_text)
    base_index = next(i for i, rule in enumerate(rules) if ".resolve-context" in rule.selectors)
    guard_index = next(i for i, rule in enumerate(rules) if ".resolve-context[hidden]" in rule.selectors)
    assert guard_index > base_index, "expected the .resolve-context[hidden] guard to come AFTER the base rule"

    guard_decls = declarations_for(css_text, ".resolve-context[hidden]")
    assert guard_decls.get("display") == "none", "expected .resolve-context[hidden] to hide by display: none"


def test_flight_detail_row_grid_margin_never_shrinks_below_cfg70_floor(css_text):
    """style.css's .flight-detail-row__grid margin-bottom is at least 2x .copy-btn::before's own
    inset magnitude — the measured 22px hit-target floor made executable rather than a
    comment; this is the check that would have failed had this task's own source data's
    'reduce to var(--space-md)' suggestion been taken"""
    tokens = custom_properties(css_text, ":root")
    grid_decls = declarations_for(css_text, ".flight-detail-row__grid")
    margin_value = grid_decls.get("margin")
    margin_match = re.search(r"0\s+0\s+var\(--(space-[a-z]+)\)", margin_value or "")
    assert margin_match, "could not parse .flight-detail-row__grid's margin shorthand: %r" % (margin_value,)
    margin_bottom = int(tokens["--" + margin_match.group(1)][:-2])

    before_decls = declarations_for(css_text, ".copy-btn::before")
    inset_match = re.search(r"inset:\s*-(\d+)px", "inset: %s" % before_decls.get("inset", ""))
    assert inset_match, "could not parse .copy-btn::before's inset: %r" % (before_decls,)
    reach = int(inset_match.group(1))

    assert margin_bottom >= 2 * reach, (
        "CFG-70 floor violated: two adjacent synthesized 44x44 pointer targets need their owners' "
        "visual boxes at least 2x%dpx apart; CFG-70 measured the earlier control at 34x26 when "
        "they were not, and .flight-detail-row__grid's margin-bottom is only %dpx — a smaller "
        "margin here silently shrinks a hit target nothing else in the suite would catch"
        % (reach, margin_bottom))


def test_nav_toggle_label_now_describes_the_preferences_panel():
    """the hamburger toggle's accessible name describes the preferences panel it now opens
    ("Account and preferences" / "Compte et préférences"), and the retired "Open menu"
    translation is deleted rather than orphaned"""
    assert layout.NAV_TOGGLE_LABEL == "Account and preferences", (
        "expected the toggle to name what the panel now holds, got %r" % (layout.NAV_TOGGLE_LABEL,))
    assert layout.i18n.t_lang(layout.NAV_TOGGLE_LABEL, "fr") != layout.NAV_TOGGLE_LABEL, (
        "expected a French entry for the renamed toggle label")
    assert layout.i18n.t_lang("Open menu", "fr") == "Open menu", (
        "expected the retired 'Open menu' translation to be deleted, not superseded in place — "
        "it names a menu of pages the panel no longer holds")
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = layout.page_shell(
            title="T", active="display", body="", ui_theme="auto",
            device_config=_NAV_STATUS_DEVICE_CFG)
    finally:
        prefs.set_request_prefs(lang="en")
    assert 'aria-label="Compte et préférences"' in rendered, "expected the French toggle name on a French request"


def test_save_bar_geometry_is_restored_and_the_tab_bar_stacking_survives(css_text):
    """the save bar's own sub-960px geometry and its z-index: 30 at both breakpoints are RESTORED —
    the .dirty-ready marker class is not (this restoration's own clearance mechanism is
    :has(.dirty-bar), which works with scripts blocked) — while the tab bar's own stacking value
    (20) and its own content clearance are unmoved"""
    dirty_bar_rules = rules_with_selector(css_text, ".dirty-bar")
    assert dirty_bar_rules, "expected the restored .dirty-bar base rule to exist in style.css"

    base_decls = declarations_for(css_text, ".dirty-bar")
    assert "position" not in base_decls, "expected the base .dirty-bar rule to declare no position of its own"

    fixed_count = 0
    z30_count = 0
    for at_rules in (("@media (min-width: 960px)",), ("@media (max-width: 959.98px)",)):
        breakpoint_decls = declarations_for(css_text, ".dirty-bar", at_rules=at_rules)
        if breakpoint_decls.get("position") == "fixed":
            fixed_count += 1
        if breakpoint_decls.get("z-index") == "30":
            z30_count += 1
    assert fixed_count == 2, (
        "expected exactly two `.dirty-bar { ... }` rule bodies (one per breakpoint) to set "
        "position: fixed, got %d" % fixed_count)
    assert z30_count == 2, (
        "expected exactly two `.dirty-bar { ... }` rule bodies (one per breakpoint) to set "
        "z-index: 30, got %d" % z30_count)

    assert not rules_with_selector(css_text, ".dirty-ready .dashboard-main"), (
        "expected no .dirty-ready-scoped content-clearance rule to exist — this restoration's own "
        "clearance mechanism is :has(.dirty-bar), which (unlike .dirty-ready) works correctly "
        "with scripts blocked")
    assert not rules_with_selector(css_text, ".dirty-ready .page-content"), (
        "expected no .dirty-ready-scoped content-clearance rule to exist")

    tab_bar_decls = declarations_for(css_text, ".tab-bar", at_rules=_TAB_BAR_MEDIA)
    assert tab_bar_decls.get("z-index") == "20", (
        "expected the tab bar's stacking value to stay at 20, unmoved by the save bar's "
        "restoration, got %r" % (tab_bar_decls.get("z-index"),))

    # The tab bar's own content clearance survives unmoved — it is now ONE
    # of two clearance rules a phone-width settings page needs (the other
    # is the restored bar's own :has()-scoped rule, asserted elsewhere by
    # companion/test_config_page*.py).
    clearance_decls = declarations_for(css_text, ".has-tab-bar .page-content", at_rules=_TAB_BAR_MEDIA)
    assert "padding-bottom" in clearance_decls, "expected .has-tab-bar .page-content to declare padding-bottom"


# =============================================================================
# Health's Frame tile and the nav notification dot read the SAME
# frame_state result the strip does — they cannot disagree, because
# neither re-derives anything.
# =============================================================================

def _health_tile_clock_text(rendered_health):
    """The Frame tile's next-wake clock: moved out of the Emphasis
    .stat-tile__value paragraph into the muted detail slot, and dropped the
    time-value--primary modifier with it."""
    match = re.search(
        r'class="text-label widget-detail"><span class="time-value">'
        r'([^<]+)</span></div>',
        rendered_health)
    return match.group(1) if match else None


def _strip_clock_text(rendered_strip):
    match = re.search(r'class="time-value time-value--primary">([^<]+)</span>', rendered_strip)
    return match.group(1) if match else None


def test_health_nightly_regression_held_agrees_with_strip_dot_unlit_no_warn(tmp_path):
    """the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00 Europe/
    Paris), pinned as ONE named check: the strip renders the held copy with the neutral dot,
    Health's Frame tile renders the SAME clock time, the nav notification dot is unlit, and
    the rendered Health HTML carries zero warn/error dots, zero warn tile/headline modifiers
    and neither 'Expected since' nor 'Attendu depuis'"""
    qh_config = {
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=_PARIS_TZ)
    clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=_PARIS_TZ)
    tmp = str(tmp_path)
    device_config.save_device_config(
        tmp, wake_interval_s=900, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00")
    shp.seed_device_health(tmp, [(checkin.isoformat(), 4200)])
    # The pipeline (flight-detection) signal is a genuinely DIFFERENT
    # system from the frame's own check-in cadence — seeded fresh (at
    # "now") so its own, unrelated staleness thresholds do not confound
    # this check's real subject.
    shp.seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: clock.isoformat()})
    rendered_health = health_page.render(shp.ctx(tmp, now_value=clock.isoformat()))
    for warn_token in (
            "dot--warn", "dot--error", "stat-tile--warn",
            "status-card__headline--warn", "Expected since", "Attendu depuis"):
        assert warn_token not in rendered_health, "expected zero %r in a held Health render" % (warn_token,)
    # The live nav-tab severity path app.py's page_context() calls
    # (health_page.safe_health_state()), which fails closed to "ok" for
    # a None state.
    health_state = health_page.safe_health_state(tmp, now=clock.isoformat())
    severity = health_state["severity"] if health_state else "ok"
    assert severity == "ok", "expected the nav notification dot unlit (severity 'ok'), got %r" % (severity,)

    strip_ctx = _frame_strip_ctx(checkin.isoformat(), qh_config, clock.isoformat())
    rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
    strip_clock = _strip_clock_text(rendered_strip)
    tile_clock = _health_tile_clock_text(rendered_health)
    assert strip_clock and tile_clock, "expected a time-value clock span in both the strip and the tile"
    # The strip's headline keeps the Emphasis modifier; the tile's
    # detail must not have it.
    assert "time-value--primary" in rendered_strip, "expected the strip's own headline to keep time-value--primary"
    assert "time-value--primary" not in rendered_health, (
        "expected zero time-value--primary on Health — the tile's clock is a muted detail, never "
        "a second Emphasis element under its own verdict (X8)")
    assert strip_clock == tile_clock, (
        "expected the strip's and the tile's clock text to be equal, got %r vs %r" % (strip_clock, tile_clock))
    assert "07:00" in tile_clock or "07:0" in tile_clock, (
        "expected the held clock to read the quiet-hours window's own end")


def test_health_inside_grace_window_tile_and_strip_agree_normal(tmp_path):
    """inside the grace window with no hold, the tile reports the normal ('ok') state and the
    strip reports the due copy — they agree"""
    device_cfg = {"wake_interval_s": 900, "display_enabled": True}
    # 11:00 + 900s = 11:15 due; 2x grace = 1800s -> still due until 11:45.
    checkin_iso = "2026-08-27T11:00:00+00:00"
    now_iso = "2026-08-27T11:30:00+00:00"
    tmp = str(tmp_path)
    device_config.save_device_config(tmp, wake_interval_s=900)
    shp.seed_device_health(tmp, [(checkin_iso, 4200)])
    shp.seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: checkin_iso})
    state = health_page.compute_health_state(tmp, now=now_iso)
    assert state["device_state"] == "ok", (
        "expected the tile to report 'ok' inside the grace window, got %r" % (state["device_state"],))
    strip_ctx = _frame_strip_ctx(checkin_iso, device_cfg, now_iso)
    rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
    assert "Next update ≈" in rendered_strip, "expected the strip to report the due copy inside the grace window"
    assert "status-card__headline--warn" not in rendered_strip, "expected no warn modifier inside the grace window"


def test_health_past_grace_window_both_report_late_dot_lights(tmp_path):
    """past the grace window with no hold, both the tile ('warn') and the strip ('Expected
    since') report late, and the nav notification dot lights"""
    device_cfg = {"wake_interval_s": 900, "display_enabled": True}
    checkin_iso = "2026-08-27T11:00:00+00:00"
    now_iso = "2026-08-27T12:00:00+00:00"
    tmp = str(tmp_path)
    device_config.save_device_config(tmp, wake_interval_s=900)
    shp.seed_device_health(tmp, [(checkin_iso, 4200)])
    shp.seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: checkin_iso})
    state = health_page.compute_health_state(tmp, now=now_iso)
    assert state["device_state"] == "warn", (
        "expected the tile to report 'warn' past the grace window, got %r" % (state["device_state"],))
    assert state["severity"] != "ok", "expected the nav notification dot to light past the grace window"
    strip_ctx = _frame_strip_ctx(checkin_iso, device_cfg, now_iso)
    rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
    assert "Expected since" in rendered_strip, "expected the strip to report the late copy past the grace window"


def test_health_held_window_ended_and_grace_elapsed_both_report_late(tmp_path):
    """a frame whose (non-held) next wake has passed and whose own grace has since elapsed is
    reported late by both the tile and the strip — held cannot suppress lateness forever"""
    # A held frame's window has already ended AND its own grace has since
    # elapsed — held cannot suppress lateness forever. The check-in itself
    # is OUTSIDE the quiet-hours window (14:00, not 23:00-07:00), so
    # next_wake_status() resolves hold_reason=None for it — a real device
    # that stopped reporting after an ordinary daytime check-in, not one
    # still inside a currently-active hold.
    device_cfg = {
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    checkin_iso = "2026-08-27T14:00:00+00:00"
    now_iso = "2026-08-28T02:00:00+00:00"
    tmp = str(tmp_path)
    device_config.save_device_config(
        tmp, wake_interval_s=900, quiet_hours_enabled=True,
        quiet_hours_start="23:00", quiet_hours_end="07:00")
    shp.seed_device_health(tmp, [(checkin_iso, 4200)])
    shp.seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: checkin_iso})
    state = health_page.compute_health_state(tmp, now=now_iso)
    assert state["device_state"] == "warn", (
        "expected the tile to report 'warn' once a held-then-elapsed frame is genuinely late, "
        "got %r" % (state["device_state"],))
    strip_ctx = _frame_strip_ctx(checkin_iso, device_cfg, now_iso)
    rendered_strip = layout.frame_strip_html(strip_ctx, return_to=layout.HOME_ROUTE)
    assert "Expected since" in rendered_strip, "expected the strip to also report late for the same fixture"


def test_dot_modifier_classes_are_exactly_four_no_new_class_added(css_text):
    """style.css declares exactly the four .dot--* modifier classes (ok/warn/error/off) and no
    fifth — the structural replacement for the legacy check's own raw `css_source.count("dot--")
    == 9` sub-clause (this module's own docstring explains why: 5 of that count's 9 substring
    occurrences are prose inside comments, and only 4 are real selectors). This plan adds no new
    dot class, which is what the original pinned count was protecting."""
    dot_selector_re = re.compile(r"^\.dot--([a-z]+)$")
    found = set()
    for rule in css_rules(css_text):
        for selector in rule.selectors:
            match = dot_selector_re.match(selector)
            if match:
                found.add(match.group(1))
    assert found == {"ok", "warn", "error", "off"}, (
        "expected exactly the four .dot--* modifier classes (ok/warn/error/off), got %r — a new "
        "one appearing here means this plan (or a later one) added a dot class" % (found,))


# =============================================================================
# The Frame strip is a SHARED
# component — one write site (layout.frame_strip_html()'s quiet cell)
# feeding both Home and Display. The check that proves this is NOT "the
# link exists on Home" plus a second, separate "the link exists on
# Display" — two per-page checks would both pass against a forked
# component (each page's own builder rendering its own copy). The property
# under test is IDENTITY: the same href, read off BOTH real page
# renderers, in ONE check whose failure message names whichever page it
# could not find on, or the two hrefs when they disagree.
# =============================================================================

_QUIET_SCHEDULE_LINK_RE = re.compile(
    r'<a class="text-link frame-strip__schedule-link" href="([^"]+)">')


def _home_ctx(tmp, now_value):
    """A Home ctx rich enough to render every region Home declares — a
    gallery entry for the picture, a check-in for the strip's own
    next-wake resolution, and a device config for its two switches."""
    return {
        "state_dir": tmp, "now": now_value,
        "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
        "last_checkin_ts": now_value,
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "health_state": {"device_state": "ok", "pipeline_state": "ok",
                         "battery_state": "ok",
                         "device_detail_html": "", "pipeline_html": ""},
        "simple_mode": False,
    }


def test_the_quiet_schedule_link_is_one_write_site_reaching_both_pages(tmp_path):
    """the quiet cell's caption link is present on BOTH Home's and Display's own real
    render() output, with the IDENTICAL href on both — asserted as one check whose failure
    names the page missing the link or the two hrefs when they differ, never two separate
    per-page checks"""
    tmp = str(tmp_path)
    now_iso = shp.iso(shp.now())
    home_ctx = _home_ctx(tmp, now_iso)
    display_ctx = {
        "device_config": home_ctx["device_config"], "state_dir": tmp,
        "poll_cooldown_remaining": 0, "now": now_iso,
    }
    rendered_home = home_page.render(home_ctx)
    rendered_display = config_page.render(display_ctx, scope=config_page.SCOPE_DISPLAY)
    # Collected across BOTH pages before returning — a shared write site
    # that is missing entirely fails on both at once, and the message says
    # so by naming every page that lacked it, not only whichever happened
    # to be checked first.
    hrefs = {}
    missing = []
    for rendered, name in ((rendered_home, "Home"), (rendered_display, "Display")):
        match = _QUIET_SCHEDULE_LINK_RE.search(rendered)
        if match:
            hrefs[name] = match.group(1)
        else:
            missing.append(name)
    assert not missing, (
        "expected a.frame-strip__schedule-link on every page that renders the strip — found none "
        "on: %s" % (", ".join(missing),))
    assert hrefs["Home"] == hrefs["Display"], (
        "expected the SAME href on both pages (one write site, D-23) — Home read %r, Display "
        "read %r; two different hrefs is exactly what a forked component would produce"
        % (hrefs["Home"], hrefs["Display"]))
    assert rendered_home.count('frame-strip__schedule-link') == 1, (
        "expected exactly one schedule-link render on Home, got %d"
        % rendered_home.count('frame-strip__schedule-link'))
    assert rendered_display.count('frame-strip__schedule-link') == 1, (
        "expected exactly one schedule-link render on Display, got %d"
        % rendered_display.count('frame-strip__schedule-link'))


# --- The Frame strip's two switches
# become real role="switch" controls, SERVER-rendered from the saved
# value. The role is not a promise the script keeps — it is a description
# of what the button does with scripts blocked too, which is the whole
# reason the accessible state can be asserted here, in a harness that
# runs no JavaScript at all.

def test_the_strip_renders_two_server_rendered_switches():
    """layout.frame_strip_html() renders exactly two role=switch controls whose aria-checked is
    the SAVED value in both directions, named by the setting through aria-labelledby and
    described by the state span, over the unchanged <form>/state/return_to/data-quick-switch
    the server already acts on — with the retired action wording gone, both state wordings
    present with exactly one hidden, and one pending-marker region per switch"""
    now_iso = "2026-08-27T10:00:00+00:00"
    checkin_iso = "2026-08-27T09:55:00+00:00"
    # BOTH states, never one: an aria-checked hard-coded to "true"
    # satisfies a single-state assertion perfectly, and is exactly the
    # switch that lies.
    for display_on, quiet_on in ((True, False), (False, True)):
        device_cfg = {
            "display_enabled": display_on, "quiet_hours_enabled": quiet_on,
            "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
            "wake_interval_s": 900,
        }
        rendered = layout.frame_strip_html(
            _frame_strip_ctx(checkin_iso, device_cfg, now_iso),
            return_to=layout.HOME_ROUTE)
        assert rendered.count('role="switch"') == 2, (
            "expected exactly two role=switch controls in the strip, got %d — one control per "
            "setting is X1/D-04 and a switch beside a surviving button is the defect that "
            "decision exists to prevent" % rendered.count('role="switch"'))
        for label_id, state_id, is_on, action in (
                (layout.QUICK_SWITCH_SCREEN_LABEL_ID, layout.QUICK_SWITCH_SCREEN_STATE_ID,
                 display_on, "/quick/display"),
                (layout.QUICK_SWITCH_QUIET_LABEL_ID, layout.QUICK_SWITCH_QUIET_STATE_ID,
                 quiet_on, "/quick/quiet-hours")):
            expected = (
                '<button type="submit" class="switch" role="switch" aria-checked="%s"'
                ' aria-labelledby="%s" aria-describedby="%s" %s>'
                % ("true" if is_on else "false", label_id, state_id,
                   layout.QUICK_SWITCH_CONTROL_ATTR))
            assert expected in rendered, (
                "%s: expected the server to render %r — the accessible STATE comes from the "
                "saved value, and the accessible NAME from the setting rather than the action (a "
                "French action reads 'Éteindre', which cannot double as a state)"
                % (action, expected))
            assert ('id="%s"' % label_id) in rendered, (
                "%s: aria-labelledby points at %r but nothing on the page carries that id — a "
                "dangling reference is an unnamed control, and no browser reports it"
                % (action, label_id))
            assert ('id="%s"' % state_id) in rendered, (
                "%s: aria-describedby points at %r but nothing carries that id" % (action, state_id))
        # The no-JS floor is STRUCTURAL: the switch IS the form that
        # already ships. Every one of these is what the server acts on
        # when the script is not there.
        for token in ('<form method="post" action="/quick/display"',
                      '<form method="post" action="/quick/quiet-hours"',
                      "data-quick-switch",
                      '<input type="hidden" name="state"',
                      '<input type="hidden" name="return_to" value="/"'):
            assert token in rendered, (
                "expected %r to survive the conversion — the script upgrades a control that "
                "already works, it never replaces one" % token)
        # The next-state the form posts must be the OPPOSITE of the
        # rendered state, or pressing the switch with scripts blocked
        # re-asserts the state it is already in.
        display_form = rendered[rendered.index('action="/quick/display"'):]
        display_form = display_form[:display_form.index("</form>")]
        wanted = layout.QUICK_STATE_OFF if display_on else layout.QUICK_STATE_ON
        assert ('name="state" value="%s"' % wanted) in display_form, (
            "the Screen form posts the wrong next state for display_enabled=%r — expected %r"
            % (display_on, wanted))
        # The retired ACTION wording must be gone from the markup. It is
        # the string the accessible name would otherwise have been, and
        # leaving it beside a role=switch is two claims about one control.
        for retired in (layout.QUICK_ACTION_SWITCH_ON_BUTTON,
                        layout.QUICK_ACTION_SWITCH_OFF_BUTTON,
                        layout.QUICK_ACTION_QUIET_TURN_ON_BUTTON,
                        layout.QUICK_ACTION_QUIET_TURN_OFF_BUTTON):
            assert (">%s<" % retired) not in rendered, (
                "the action wording %r is still rendered as the switch's own text — a role=switch "
                "names the SETTING and states itself with aria-checked; an action label beside it "
                "is the second, contradicting claim" % retired)
        # The visible state survives as BOTH wordings, one hidden, so the
        # script never has to carry a word of user-facing copy and the
        # rollback is a pure attribute flip.
        assert rendered.count(layout.QUICK_STATE_ON_ATTR) == 2, (
            "expected one %s span per switch, got %d"
            % (layout.QUICK_STATE_ON_ATTR, rendered.count(layout.QUICK_STATE_ON_ATTR)))
        assert rendered.count(layout.QUICK_STATE_OFF_ATTR) == 2, (
            "expected one %s span per switch, got %d"
            % (layout.QUICK_STATE_OFF_ATTR, rendered.count(layout.QUICK_STATE_OFF_ATTR)))
        assert rendered.count(" hidden>") == 2, (
            "expected exactly one of each switch's two state wordings to be hidden, got %d "
            "hidden spans" % rendered.count(" hidden>"))
        # The pending marker's own host. freshness.js skips a region
        # carrying it OR containing it; this is the region.
        assert rendered.count(layout.QUICK_SWITCH_REGION_ATTR) == 2, (
            "expected one %s region per switch — the element the script marks pending and plan "
            "23-06's swap already skips, got %d"
            % (layout.QUICK_SWITCH_REGION_ATTR, rendered.count(layout.QUICK_SWITCH_REGION_ATTR)))


def test_the_failure_toast_is_transient_translated_and_carries_no_internal():
    """the optimistic switch's failure copy is the app's own generic flash sentence, translated
    on <body> in both languages and carrying no status code, URL or server internal, and the
    shell renders exactly one EMPTY assertive live region for it — a transient toast, never
    a permanent banner"""
    try:
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            expected = layout.i18n.t(layout.QUICK_SWITCH_FAILED_TEXT)
            doc = layout.page_shell(title="T", active="home", body="<p>b</p>", lang=lang)
            body_tag = doc[doc.index("<body"):doc.index(">", doc.index("<body")) + 1]
            marker = '%s="%s"' % (layout.QUICK_SWITCH_FAILED_ATTR, layout.escape_html(expected))
            assert marker in body_tag, (
                "lang=%s: expected the translated failure copy on the rendered <body> tag (%r), "
                "got %r" % (lang, marker, body_tag))
            if lang == "fr":
                assert expected != layout.QUICK_SWITCH_FAILED_TEXT, (
                    "the failure copy is untranslated — it reads %r in both languages" % (expected,))
            # V7: an error message is an information-disclosure surface.
            # The copy is the app's own existing generic flash sentence
            # and must never acquire a status code, a URL or a route.
            for internal in ("500", "http", "/quick/", "Traceback", "Error:"):
                assert internal not in expected, (
                    "lang=%s: the failure copy carries %r — a user-facing failure message names "
                    "no status code, no URL and no server internal (V7, T-23-27)" % (lang, internal))
            # A transient toast, never a permanent banner. The live region
            # is rendered EMPTY and stays in the accessibility tree,
            # because a region added to the tree at announce time is a
            # region screen readers routinely miss.
            toast = '<div class="quick-toast" %s role="alert"></div>' % layout.QUICK_TOAST_ATTR
            assert toast in doc, (
                "lang=%s: expected exactly the empty assertive live region %r in the shell — D2 "
                "asks for a transient toast rather than the permanent banner this app uses for a "
                "flash" % (lang, toast))
            assert doc.count(layout.QUICK_TOAST_ATTR) == 1, (
                "lang=%s: expected exactly one toast region per document, got %d — a second one "
                "is a second place a failure could be announced" % (lang, doc.count(layout.QUICK_TOAST_ATTR)))
    finally:
        prefs.set_request_prefs(lang="en")


# --- The live indicator tells the truth. Three checks: the dot's server-rendered
# markup, the ticking age that replaces the frozen clock, and a served-JS
# behaviour check proving the breathing class is toggled from the loop's
# OWN state rather than from a second state machine beside it.

def test_health_freshness_line_carries_a_neutral_live_dot(tmp_path):
    """Health's freshness line carries exactly one neutral, aria-hidden live dot — the app's own
    off dot with no status or accent token and no breathing class at render time, because the
    motion belongs to the loop that knows whether it is listening"""
    tmp = str(tmp_path)
    rendered = health_page.render(shp.ctx(tmp, now_value=shp.iso(shp.now())))
    start = rendered.index('<p class="page-header__freshness')
    wrapper = rendered[start:rendered.index("</p>", start) + len("</p>")]
    assert wrapper.count(health_page.REFRESH_LIVE_DOT_ATTR) == 1, (
        "expected exactly one %s inside .page-header__freshness, got %d"
        % (health_page.REFRESH_LIVE_DOT_ATTR, wrapper.count(health_page.REFRESH_LIVE_DOT_ATTR)))
    dot_at = wrapper.index(health_page.REFRESH_LIVE_DOT_ATTR)
    tag = wrapper[wrapper.rindex("<", 0, dot_at):wrapper.index(">", dot_at) + 1]
    assert 'class="dot dot--off"' in tag, (
        "expected the live dot to be the app's own NEUTRAL dot and nothing else — a refresh loop "
        "that is listening is not a device verdict and must not borrow one's colour, got %r" % (tag,))
    for verdict in ("dot--ok", "dot--warn", "dot--error", "status-warn", "accent"):
        assert verdict not in tag, "expected no status/accent token on the live dot, found %r in %r" % (verdict, tag)
    assert 'aria-hidden="true"' in tag, (
        "expected the live dot to be aria-hidden — it is decorative, and the loop's real state is "
        "already announced by the Paused/Reconnecting badge beside it")
    # Server-rendered STATIC. The motion is one class
    # companion/static/freshness.js adds, so a scripts-blocked page shows
    # a still dot beside an age that does not move, which is exactly what
    # is true there.
    assert "is-breathing" not in wrapper, (
        "expected the server to render the dot STILL — the breathing class is freshness.js's to "
        "add, and a server-rendered one would breathe on a page with no loop running at all, got "
        "%r" % (wrapper,))


def test_health_freshness_clock_is_a_ticking_age_over_the_loaded_at_instant(tmp_path):
    """Health's freshness line is a <time data-relative> over the same instant data-loaded-at
    carries whose SERVER text is the clock — never the ladder's zero bucket, which is the
    frozen age A-20 removed — with the absolute timestamp still in the element's tooltip,
    exactly one data-loaded-at and one data-refresh-pill page-wide, and the wrapper still a
    swap target"""
    tmp = str(tmp_path)
    now_iso = shp.iso(shp.now())
    rendered = health_page.render(shp.ctx(tmp, now_value=now_iso))
    start = rendered.index('<p class="page-header__freshness')
    wrapper = rendered[start:rendered.index("</p>", start) + len("</p>")]
    # The element, over the SAME instant data-loaded-at carries — not a
    # second instant computed beside it.
    clock_text = layout.local_clock_text(
        layout.parse_iso(now_iso), now_parsed=layout.parse_iso(now_iso))
    expected = layout.relative_time_html(now_iso, now_iso, static_text=clock_text)
    assert expected in wrapper, (
        "expected the freshness line's value to be layout.relative_time_html() over the same "
        "instant data-loaded-at carries (%r), got %r" % (expected, wrapper))
    # THE ANTI-VACUITY HALF, and the reason this check is not satisfied by
    # "an element is present": what a WRONG implementation does here is
    # render an age that nothing can advance. So the element's own server
    # text is asserted to BE the clock and asserted NOT to be the ladder's
    # zero bucket, in both languages.
    element = re.search(r"<time ([^>]*)>(.*?)</time>", wrapper, flags=re.S)
    assert element is not None, "expected a <time> element in the freshness line, got %r" % (wrapper,)
    attrs, element_text = element.group(1), element.group(2)
    assert "data-relative" in attrs and "datetime=" in attrs, (
        "expected the freshness element to stay a <time datetime=... data-relative> — the clock "
        "is the server's floor and the ticker's hook is what upgrades it, got %r" % (attrs,))
    assert element_text == layout.escape_html(clock_text), (
        "expected the SERVER to render the clock %r inside the <time> element — a scripts-blocked "
        "reader has nothing to advance an age, got %r" % (clock_text, element_text))
    for lang in ("en", "fr"):
        frozen_zero = layout.escape_html(layout.relative_age_text(0, lang=lang))
        assert element_text != frozen_zero, (
            "the freshness line server-renders the ladder's ZERO bucket (%r) — that is A-20's own "
            "frozen zero, true at load and never again for a reader with no scripts" % (frozen_zero,))
    # data-loaded-at stays exactly once, page-wide: freshness.js reads it
    # with a single querySelector and a second would silently win.
    assert rendered.count("data-loaded-at") == 1, (
        "expected exactly one data-loaded-at page-wide, got %d" % rendered.count("data-loaded-at"))
    assert rendered.count("data-refresh-pill") == 1, (
        "expected exactly one data-refresh-pill page-wide, got %d" % rendered.count("data-refresh-pill"))
    # Nothing lost: the full Europe/Paris local timestamp is still on the
    # clock span's title (22-16's / conversion), and the raw ISO
    # still does not survive.
    expected_title = layout.escape_html(health_page._full_local_timestamp_text(now_iso))
    assert ('title="%s"' % expected_title) in wrapper, (
        "expected the absolute timestamp to stay available in the element's tooltip (%r), got %r"
        % (expected_title, wrapper))
    # The <time> element is INSIDE the .page-header__freshness wrapper,
    # which is one of REFRESH_SWAP_SELECTORS' own entries — so the value a
    # swap replaces and the value the ticker advances are the same one.
    assert ".page-header__freshness" in health_page.REFRESH_SWAP_SELECTORS, (
        "expected .page-header__freshness to still be a swap target — the ticking age is honest "
        "between swaps and reset by them")


def test_freshness_js_breathes_only_from_the_loops_own_state(freshness_js, css_text):
    """freshness.js DERIVES the breathing class from its own interval handle and state badge in
    one function, called from exactly the four places its state already changes, carries no
    status vocabulary, leaves 22-15's retry ladder/ceiling/in-flight guard/targeted swap
    untouched, and agrees with both the Python hook and the CSS rule"""
    # A dot that breathes while the page is not actually
    # listening is a lie the user has no way to check. The mitigation is
    # structural rather than careful — the class is DERIVED from the
    # loop's own two state variables inside one function, and that
    # function is called from the four places the loop's state already
    # changes. There is no second timer and no second variable tracking
    # liveness.
    js = freshness_js
    assert "function syncLiveDot()" in js, (
        "expected freshness.js to derive the breathing class in ONE function — two sources for "
        "one claim is this codebase's most repeated defect")
    assert "intervalHandle !== null && currentState === null" in js, (
        "expected the breathing class to be DERIVED from the loop's own interval handle AND its "
        "own state badge — either half alone lets the dot breathe while the page is paused or "
        "failing (T-23-15)")
    # Called from every function that changes either half, and from
    # nowhere else. setState() covers both paused and reconnecting;
    # clearState() covers recovery and return-from-hidden; start/stop
    # cover the interval itself, including tick()'s own belt-and-braces
    # stop in a background tab.
    for owner, body_end in (
            ("function setState(state) {", "function clearState()"),
            ("function clearState() {", "23-05-PLAN.md Task 2"),
            ("function startLoop() {", "function stopLoop()"),
            ("function stopLoop() {", "document.addEventListener")):
        assert owner in js, "expected %r in freshness.js" % (owner,)
        region = js[js.index(owner):js.index(body_end, js.index(owner))]
        assert "syncLiveDot()" in region, (
            "expected syncLiveDot() to be called from %s — the breathing class must change where "
            "the loop's own state changes, never from a second state machine beside it" % (owner,))
    assert js.count("syncLiveDot();") == 4, (
        "expected exactly four syncLiveDot() call sites (setState, clearState, startLoop, "
        "stopLoop), got %d — a fifth caller is a second state machine" % js.count("syncLiveDot();"))
    # The loop still never paints its own failure as a device fault.
    for verdict in ("dot--warn", "dot--error", "status-warn"):
        assert verdict not in js, (
            "freshness.js must carry no status vocabulary — a browser that lost its connection is "
            "not a device fault, found %r" % (verdict,))
    # 22-15's own work, byte-for-byte present: the ladder, its ceiling and
    # the in-flight guard are NOT re-implemented here.
    for untouched in ("RETRY_BASE_MS", "RETRY_CEILING_MS = 600000",
                      "function failAndRetry()", "inFlight", "isEqualNode"):
        assert untouched in js, (
            "expected 22-15's own %r to survive untouched — this plan adds the two things T13 "
            "deliberately left for Phase 23 and re-implements none of it" % (untouched,))
    # The dot's own selector and class must agree with the Python that
    # renders the element and the CSS that animates it.
    assert health_page.REFRESH_LIVE_DOT_ATTR in js, (
        "freshness.js does not name %r — health_page.py renders the hook and this file is the "
        "only thing that toggles it" % (health_page.REFRESH_LIVE_DOT_ATTR,))
    assert rules_with_selector(css_text, ".is-breathing"), (
        "expected companion/static/style.css to declare the breathing rule freshness.js toggles "
        "— a class with no rule is motion nobody ever sees")


# =============================================================================
# Section 3: two end-to-end checks — a real companion/app.py subprocess,
# logged in, fetching real routes against a seeded database.
# =============================================================================

def test_both_tabs_ok_end_to_end(make_app_server):
    """GET /health, GET /airlines and GET /history all return 200 with their own page heading against a
    real running service, /health's real HTTP response body carries the page purpose, both section
    descriptions, no duplicated freshness label, the auto-refresh pill (hidden) and zero stale-banner
    markers, the nested modifier twice, the prose modifier once, both readout spans, no raw ISO in
    the readout's own slice, and the desc-class cells at their expected count after the
    Resolution-statistics heading, /airlines' real HTTP response body carries zero occurrences of
    the retired per-card replace class, exactly one lightbox replace form and one action="" and
    one file input, and at least one un-busted replace-action trigger attribute, /history's real
    HTTP response body carries zero occurrences of the replace-form class, replace-action attribute,
    enctype or file input, and the real served stylesheet
    (STYLE_ROUTE) carries the description-column rule, the demotion rule's new bottom margin and the
    prose rhythm rule's selector, and the real served freshness script (FRESHNESS_SCRIPT_ROUTE)
    carries the interval constant, the visibility-change listener, the [data-loaded-at]/
    [data-refresh-pill] attribute hooks, carries zero occurrences of the deleted
    data-pause-text/wireToggle pause-branch hooks, and every
    health_page.REFRESH_SWAP_SELECTORS entry verbatim"""

    def _seed(state_dir):
        now = shp.now()
        # Two readings, not one — the
        # readout element and its chart only render when at least two
        # numeric battery rows exist; a single-reading fixture would make
        # the check below fail to find the readout at all, for a reason
        # unrelated to the fix it is checking.
        shp.seed_device_health(state_dir, [
            (shp.iso(now - timedelta(minutes=1)), 4200),
            (shp.iso(now), 4190),
        ])
        shp.seed_meta(state_dir, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
        shp.seed_unresolved_prefixes(state_dir, {
            "ABC": {"count": 2, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                    "example_callsign": "ABC123"},
        })
        # A resolved runway event so resolution_stats()'s total is
        # non-zero and _stats_table_html() actually renders a table.
        shp.seed_runway_events(state_dir, [
            {"ts": shp.iso(now), "hex": "abc123", "route_source": "fresh_hit"}])

    server = make_app_server(seed=_seed)
    session_cookie = login(server)

    for path, heading in (
            ("/health", "Health"), ("/airlines", "Airlines"),
            # /history added so the served-HTML twin of the render-level
            # History guard above runs against a real running service,
            # not only an in-process render() call.
            ("/flights", "Flights")):
        status, _headers, body = get(server, path, cookie=session_cookie)
        assert status == 200, "expected 200 for %s, got %d" % (path, status)
        assert heading.encode() in body, "expected the %r heading in %s's response body" % (heading, path)
        if path == "/health":
            body_text = body.decode("utf-8", errors="replace")
            for constant in (
                    health_page.PAGE_PURPOSE_TEXT,
                    health_page.SCREEN_SECTION_DESCRIPTION,
                    health_page.SERVER_DATA_SECTION_DESCRIPTION):
                escaped = layout.escape_html(constant)
                assert escaped in body_text, "expected %r in the real /health HTTP response body" % (constant,)
            for label in (health_page.DEVICE_FRESHNESS_LABEL, health_page.PIPELINE_FRESHNESS_LABEL):
                label_count = body_text.count(label)
                assert label_count == 1, (
                    "expected %r exactly once in the real /health HTTP response body, got %d"
                    % (label, label_count))

            assert body_text.count("data-refresh-pill") == 1, (
                "expected the pill marker exactly once in the real /health HTTP response body, "
                "got %d" % body_text.count("data-refresh-pill"))
            pill_start = body_text.index("data-refresh-pill")
            pill_tag = body_text[
                body_text.rindex("<", 0, pill_start):body_text.index(">", pill_start) + 1]
            assert " hidden" in pill_tag, "expected the real /health response's pill to carry the bare hidden attribute"
            assert "data-stale-banner" not in body_text, "expected zero stale-banner markers in the real /health HTTP response body"

            nested_count = body_text.count("page-section--nested")
            assert nested_count == 2, (
                "expected page-section--nested exactly twice in the real /health HTTP response "
                "body, got %d" % nested_count)
            prose_count = body_text.count("data-table--prose")
            assert prose_count == 1, (
                "expected data-table--prose exactly once in the real /health HTTP response body, "
                "got %d" % prose_count)
            assert "battery-readout__value" in body_text, "expected the readout's value span in the real /health HTTP response body"
            assert "battery-readout__detail" in body_text, "expected the readout's detail span in the real /health HTTP response body"
            readout_start = body_text.index('<p id="%s"' % health_page.BATTERY_READOUT_ID)
            readout_end = body_text.index("</p>", readout_start) + len("</p>")
            readout_slice = body_text[readout_start:readout_end]
            visible = re.sub(r"<[^>]*>", "", readout_slice)
            assert not re.search(r"\d{4}-\d{2}-\d{2}T", visible), (
                "expected no raw ISO string in the real /health response's readout own slice, "
                "got %r" % (visible,))

            desc_count = body_text.count('<td class="desc">')
            expected_desc = len(health_page._SOURCE_ROWS)
            assert desc_count == expected_desc, (
                "expected exactly %d desc-class cells in the real /health HTTP response body, "
                "got %d" % (expected_desc, desc_count))
            stats_at = body_text.index(health_page.STATS_SECTION_HEADING)
            first_desc_at = body_text.index('<td class="desc">')
            assert first_desc_at >= stats_at, (
                "expected the desc-class cells to fall after the Resolution-statistics heading in "
                "the real /health HTTP response body")

        elif path == "/airlines":
            body_text = body.decode("utf-8", errors="replace")
            retired_token = "airline-card__" + "replace"
            assert retired_token not in body_text, "expected zero occurrences of the retired per-card class token in the real /airlines HTTP response body"
            replace_form_count = body_text.count('class="%s"' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS)
            assert replace_form_count == 1, (
                "expected airlines_page.LIGHTBOX_REPLACE_FORM_CLASS exactly once in the real "
                "/airlines HTTP response body, got %d" % replace_form_count)
            replace_actions = re.findall(
                r'%s="([^"]+)"' % re.escape(airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR), body_text)
            assert replace_actions, (
                "expected at least one %r attribute in the real /airlines HTTP response body"
                % (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR,))
            for action in replace_actions:
                assert "?v=" not in action, (
                    "expected no data-view-panel-replace-action value to carry a cache buster in "
                    "the real /airlines HTTP response body, found one on %r" % (action,))
            # The shared dialog carries three real empty-action forms
            # (replace, resolve-upload, delete); the resolve-name form's
            # own action is never empty. A leading space isolates the
            # real HTML attribute from a hyphenated data-attribute name
            # ending in "-action" (which has no space immediately before
            # "action").
            assert body_text.count(' action=""') == 3, (
                "expected ' action=\"\"' exactly 3 times (replace/resolve-upload/delete forms) in "
                "the real /airlines HTTP response body, got %d" % body_text.count(' action=""'))
            assert body_text.count('<input type="file"') == 2, (
                "expected <input type=\"file\" exactly twice (replace form, resolve-upload form) "
                "in the real /airlines HTTP response body, got %d" % body_text.count('<input type="file"'))

        elif path == "/flights":
            body_text = body.decode("utf-8", errors="replace")
            for token, label in (
                    (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, "airlines_page.LIGHTBOX_REPLACE_FORM_CLASS"),
                    (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR"),
                    ("enctype", "enctype"),
                    ('<input type="file"', '<input type="file"')):
                count = body_text.count(token)
                assert count == 0, (
                    "expected zero occurrences of %s in the real /history HTTP response body, "
                    "got %d" % (label, count))

    # The real served stylesheet, asserted structurally against the
    # process actually handing it to a browser — never a regex/substring
    # probe over the raw served text (33-FOLLOWUPS.md F-01).
    css_status, _css_headers, css_body = get(server, app.STYLE_ROUTE, cookie=session_cookie)
    assert css_status == 200, "expected 200 for %s, got %d" % (app.STYLE_ROUTE, css_status)
    served_css_text = css_body.decode("utf-8", errors="replace")
    assert rules_with_selector(served_css_text, ".data-table td.desc"), (
        "expected the description-column rule (.data-table td.desc) in the real %s response body"
        % (app.STYLE_ROUTE,))
    nested_heading_decls = declarations_for(served_css_text, ".page-section--nested > h2")
    assert nested_heading_decls.get("margin-bottom") == "var(--space-md)", (
        "expected the demotion rule's new bottom margin in the real %s response body, got %r"
        % (app.STYLE_ROUTE, nested_heading_decls))
    assert rules_with_selector(served_css_text, ".page-section--nested > p.text-body"), (
        "expected the prose rhythm rule's selector in the real %s response body" % (app.STYLE_ROUTE,))

    # The real served freshness script — a real fetch of this same
    # running service, proving the process hands a browser the new loop,
    # not only that the on-disk file says so. Comment-stripped per this
    # module's own JS convention, never raw source on disk.
    js_status, _js_headers, js_body = get(server, app.FRESHNESS_SCRIPT_ROUTE, cookie=session_cookie)
    assert js_status == 200, "expected 200 for %s, got %d" % (app.FRESHNESS_SCRIPT_ROUTE, js_status)
    js_text = shp.strip_js_line_and_block_comments(js_body.decode("utf-8", errors="replace"))
    for needle, label in (
            ("AUTO_REFRESH_INTERVAL_MS", "the named interval constant"),
            ("visibilitychange", "the visibility-change listener registration"),
            ("[data-loaded-at]", "the loaded-at attribute hook"),
            ("[data-refresh-pill]", "the refresh-pill attribute hook")):
        assert needle in js_text, "expected %s (%r) in the real %s response body" % (label, needle, app.FRESHNESS_SCRIPT_ROUTE)
    for forbidden in ("data-pause-text", "wireToggle"):
        assert forbidden not in js_text, (
            "expected zero occurrences of %r in the real %s response body — the pause branch "
            "must not come back through the served file (D-18)" % (forbidden, app.FRESHNESS_SCRIPT_ROUTE))
    for selector in health_page.REFRESH_SWAP_SELECTORS:
        assert selector in js_text, (
            "expected health_page.REFRESH_SWAP_SELECTORS entry %r verbatim in the real %s "
            "response body" % (selector, app.FRESHNESS_SCRIPT_ROUTE))


def test_illustration_route_serves_normalized_bytes_end_to_end(make_app_server):
    """GET /illustration/{key}.png against a real running service serves normalized bytes that differ
    from the raw vendored file and decode to illustration_normalize.ILLUSTRATION_TARGET_SIZE, and an
    unknown key still 404s"""
    server = make_app_server()
    session_cookie = login(server)

    key = illustrations.normalise_airline_key("Air France")
    path = illustrations.illustration_path_for_key(key)
    with open(path, "rb") as fh:
        raw_bytes = fh.read()

    status, _headers, served_bytes = get(
        server, app.ILLUSTRATION_IMAGE_ROUTE_PREFIX + key + ".png", cookie=session_cookie)
    assert status == 200, "expected 200 for a known illustration key, got %d" % status
    assert served_bytes != raw_bytes, "expected the served bytes to differ from the raw file bytes (normalization ran)"
    with Image.open(io.BytesIO(served_bytes)) as decoded:
        assert decoded.size == illustration_normalize.ILLUSTRATION_TARGET_SIZE, (
            "expected the served image to decode to %r, got %r"
            % (illustration_normalize.ILLUSTRATION_TARGET_SIZE, decoded.size))

    unknown_status, _unknown_headers, _unknown_body = get(
        server, app.ILLUSTRATION_IMAGE_ROUTE_PREFIX + "not-a-real-airline-key.png", cookie=session_cookie)
    assert unknown_status == 404, "expected 404 for an unknown illustration key, got %d" % unknown_status
