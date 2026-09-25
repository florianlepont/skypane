"""Part 07 of the `companion/test_status_pages.py` migration chain
(33-31-PLAN.md): the original harness's final `check()` calls #293-#317 —
the LAST slice of the whole status-pages chain (33-04..33-31). Covers the
tab bar's own margin-fit/More-sheet/French-label/dropdown-max-height
contracts, a structural style.css comment-terminator guard, the T3/T4
disclosure-marker and dead-sticky-claim sweep, freshness.js's backoff
ladder and breathing-dot mechanism, the `.resolve-context[hidden]` and
`.flight-detail-row__grid` CSS guards, the renamed hamburger-toggle label,
the restored save-bar geometry beside the tab bar's own untouched
stacking, the Health-tile/Frame-strip agreement across all four
lateness states, the shared quiet-schedule link, the two server-rendered
switches and their optimistic-failure toast, the freshness line's live
dot and ticking clock, and the two end-to-end (real subprocess) checks
that close the file.

Every CSS check in this slice (rubric C) fetches the stylesheet
`companion/app.py` actually serves and asserts on it structurally via
`companion_markup.css_rules()`/`declarations_for()`/`rules_with_selector()`
— never a regex/substring probe over the raw served text (33-FOLLOWUPS.md
F-01) — using the same module-scoped read-only server this chain has used
since 33-26 (`_module_server`/`css_text`). The two served-JS checks
(`freshness.js`) fetch it via `served_asset()` and strip only comments
with this chain's `strip_js_line_and_block_comments()`, never a disk read.

One check (row 298, the stray-comment-terminator structural guard) scans
the SERVED stylesheet's raw text rather than parsing it with
`css_rules()`: the defect it guards against (an unterminated `/* */`
comment silently swallowing the next rule) is exactly the shape a real
CSS parser cannot see through either, so the scan is inherently over the
character stream, not the parsed structure. It still never reads the file
from disk — only the bytes `companion/app.py`'s STYLE_ROUTE actually
serves.

One check (row 299) drops the legacy check's own literal
`css_source.count("@media (prefers-reduced-motion: reduce)") != 2`
sub-clause (rubric C: `css_rules()` records each rule's ENCLOSING at-rule
context, not a raw count of top-level at-rule block occurrences in the
source, so this specific invariant has no structural equivalent). In its
place, the check asserts the two SPECIFIC things that count actually
protected: the one global `*, *::before, *::after` override exists under
that media query, and the one `.js .mobile-nav` opt-out exists under it
too, while `summary::before` (the marker this task's own change touches)
carries no THIRD, redundant per-rule override under the same at-rule —
the real behavioural content the magic number "2" stood in for.

One check (row 309) drops the legacy check's own literal
`css_source.count("dot--") != 9` sub-clause (rubric C): of the raw
served-text's 9 substring occurrences of "dot--", 5 are prose inside
COMMENTS (guard G1 already rules out comment text as a source of
behaviour) and only 4 are real selectors. The structural replacement
asserts the actual invariant the comment-polluted count stood in for:
exactly four `.dot--*` modifier classes exist (ok/warn/error/off) and no
fifth has been added.

Every other check in this module calls `companion.layout`/`companion.
pages.health_page`/`companion.pages.airlines_page`/`companion.i18n`/
`companion.prefs` directly, in-process, seeding fixtures under `tmp_path`.
"""
import re
from datetime import timedelta, timezone

import pytest

import companion.i18n_fr.nav as i18n_fr_nav
import companion.test_status_pages_helpers as shp
from companion import layout, prefs
from companion_app_server import served_asset, served_stylesheet
from companion_markup import css_rules, custom_properties, declarations_for, rules_with_selector


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
# 29-02-PLAN.md (CFG-82): the 2026-09-17 audit measured "Compagnies"
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
    `.tab-bar__link`'s own 56px height and `flex: 1 1 0` width basis stay byte-identical (CFG-82,
    29-02-PLAN.md)"""
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
    restating it, and leaves .mobile-nav's in-flow flex-basis push-down untouched (X9/D-10,
    22-14-PLAN.md Task 1). The legacy check's own stylesheet-comment assertion ("the stylesheet
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
    'Navigation principale' (B16/CFG-29, 22-14-PLAN.md Task 1)"""
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
    copies, each with its two nowrap segments (B10/D-04, 22-14-PLAN.md Task 2)"""
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
    # line can only ever break BETWEEN them (B10).
    for rendered, shape in ((home, "span"), (elsewhere, "link")):
        assert rendered.count('<span class="nav-status__segment">') == 4, (
            "expected two segments per nav copy in the %s shape, got %d"
            % (shape, rendered.count('<span class="nav-status__segment">')))


def test_one_open_dropdown_max_height_and_no_dead_dropdown_nav_rule(css_text):
    """exactly ONE open-state max-height governs the dropdown (320px, pinned against a measured
    165px of reduced French content at 390px — both the 420px and 640px values are gone, not
    re-tuned), the dropdown's dead nav selectors are deleted while .mobile-nav__link survives for
    the tab bar's sheet, and .nav-status is a wrapping flex row of nowrap segments whose hover
    underline is anchor-scoped (T11/B10, 22-14-PLAN.md Task 2)"""
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
    source text a string-comparison harness reads as correct (22-14-PLAN.md Task 2, Rule 1).

    Added by 22-14-PLAN.md Task 2 after a real defect this plan found and fixed: an earlier plan
    appended a note to an existing block comment AFTER that comment's own closing marker, leaving
    a terminator with no opener — everything from it to the next brace then parsed as part of the
    following selector, silently dropping the rule that follows. No parsed-rule assertion could
    see this: the file still contains every declaration such a check asks about. The scan runs
    over the SERVED stylesheet's raw character stream (never a disk read) because this is exactly
    the shape a real CSS parser cannot see through either."""
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
    height could never provide (T3/T4, 22-15-PLAN.md Task 1)"""
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

    # T3 reaches the tab bar's "More" summary too (22-UI-SPEC.md §3.1),
    # where it is taken out of flow so a 6px marker cannot narrow a
    # 78x56px cell's centred icon-and-label stack.
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
    English fallbacks byte for byte (T13, 22-15-PLAN.md Task 2)"""
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

    # --- neutral, never a warning (22-UI-SPEC.md §5 contract 9, T13 row) --
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
    illustration's resolve-context block renders empty instead of hidden (quick task 260921-n2n
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
    inset magnitude — CFG-70's measured 22px hit-target floor made executable rather than a
    comment; this is the check that would have failed had this quick task's own source data's
    'reduce to var(--space-md)' suggestion been taken (quick task 260921-n2n Task 5)"""
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
    translation is deleted rather than orphaned (X9/D-10/B16, 22-14-PLAN.md Task 2)"""
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
    (20) and its own content clearance are unmoved (D-10/T7, 22-14-PLAN.md Task 3; retired by
    27-04-PLAN.md/CFG-63, restored by 28-08-PLAN.md Task 3/CFG-77/CFG-78)"""
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
