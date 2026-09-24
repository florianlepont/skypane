"""Part 02 of the `companion/test_view_pages.py` migration chain
(33-06-PLAN.md): the original harness's check() calls #38-#96, covering
the icon-only row toggle (22-09-PLAN.md Task 1), the summary/detail row
split's copy buttons and CSS (21-03-PLAN.md), the render-gallery
section's retirement in favour of the per-row View-panel lightbox
(quick task 260903-etm, 06.6.4.1-05/-08), `panel-lookup.js`'s own
DOM/JS contracts (phase 14), and the Airlines gap strip / resolve
dialog through Paris-local time (19-08-PLAN.md, 22-11-PLAN.md).

Every check calls `history_page.render()` / `airlines_page.render()`
directly (never over HTTP) with a `tmp_path`-backed state directory.
Checks that used to `open()` `companion/static/style.css` or a served
JS asset from disk instead fetch them from a running `companion/app.py`
(`module_app_server_factory` + `served_stylesheet()`/`served_asset()`)
and assert on `companion_markup`'s parsed structure or the served text
itself — never a file opened from disk (TST-12).
"""
import html
import re

import pytest

import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
import companion.test_view_pages_helpers as vp
from companion.pages import airlines_page, history_page
from companion_app_server import served_asset, served_stylesheet
from companion_markup import declarations_for, parse_html
from server import device_config
from server.plane import illustrations, manual_resolutions


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's checks fetch
    the served stylesheet/JS assets from, instead of opening them from
    disk (TST-12)."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


@pytest.fixture(scope="module")
def panel_lookup_js(app):
    """companion/static/panel-lookup.js's served text, fetched over
    HTTP instead of opened from disk (TST-12)."""
    return served_asset(app, "/static/panel-lookup.js")


# --- lightbox DOM-contract token classification (phase 14 plan 14-01
# Task 2), scoped to this module: used only by
# test_lightbox_dom_contract_three_file_guard() and
# test_view_panel_attr_constants_all_classified() below. See
# 33-MIGRATION-RULES.md section 3 (S classification) — these are
# server-rendered/served-JS VALUES compared against each other, never a
# read of production .py source. ---------------------------------------

# Must appear in companion/static/panel-lookup.js's served text, the
# rendered History page, and the rendered Airlines page - the vocabulary
# every one of the three genuinely shares today.
_LIGHTBOX_SHARED_TOKENS = (
    history_page.LIGHTBOX_DIALOG_ID,
    "data-view-panel-src",
    "data-view-panel-caption",
    "lightbox__image",
    "lightbox__caption",
    "lightbox__note",
    "data-view-panel-close",
)

# Must appear in panel-lookup.js's served text and in the rendered
# Airlines page, and must be absent from the rendered History page -
# History deliberately renders no replace form and never should.
_LIGHTBOX_AIRLINES_ONLY_TOKENS = (
    "data-view-panel-replace-action",
    "lightbox__replace",
    airlines_page._VIEW_PANEL_HEADING_ATTR,
    airlines_page._VIEW_PANEL_MODE_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_ATTR,
    airlines_page._VIEW_PANEL_SCOPE_ATTR,
    airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR,
    airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_LAST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_COUNT_ATTR,
    airlines_page._VIEW_PANEL_UPLOAD_ACTION_ATTR,
    airlines_page._VIEW_PANEL_DELETE_ACTION_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_NOTE_ATTR,
    airlines_page.LIGHTBOX_HEADING_CLASS,
    airlines_page.LIGHTBOX_MANUAL_NOTE_CLASS,
    airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS,
    airlines_page.LIGHTBOX_DELETE_CLASS,
    airlines_page.RESOLVE_CONTEXT_CLASS,
    airlines_page.RESOLVE_UPLOAD_ZONE_CLASS,
)

# Server-rendered vocabulary the script does not read yet: asserted
# present in the rendered Airlines page only. Stays empty absent a
# future wave introducing a fourth rendered-but-not-yet-scripted token.
_LIGHTBOX_RENDER_ONLY_TOKENS = ()

# The eleven data-view-panel-* attribute name literals 14-02 added to
# the vocabulary, built from the same airlines_page constants already
# threaded into _LIGHTBOX_AIRLINES_ONLY_TOKENS above, never a second
# hand-copied list.
_NEW_VIEW_PANEL_ATTR_NAMES = (
    airlines_page._VIEW_PANEL_HEADING_ATTR,
    airlines_page._VIEW_PANEL_MODE_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_ATTR,
    airlines_page._VIEW_PANEL_SCOPE_ATTR,
    airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR,
    airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_LAST_SEEN_ATTR,
    airlines_page._VIEW_PANEL_COUNT_ATTR,
    airlines_page._VIEW_PANEL_UPLOAD_ACTION_ATTR,
    airlines_page._VIEW_PANEL_DELETE_ACTION_ATTR,
    airlines_page._VIEW_PANEL_MANUAL_NOTE_ATTR,
)

_ISO_INSTANT_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}")


def _row_markup(rendered, tag, group_index):
    """Raw markup slice of the `<tag ... data-filter-group="N">`
    element — a plain regex over RENDERED text (a production function's
    return value, never a file opened from disk). A handful of checks
    below assert byte-for-byte attribute-value equality or substring
    containment across a row's raw markup, which `vp.row_block()`'s
    parsed `companion_markup.Node` has no serializer for.
    """
    match = re.search(
        r'<%s[^>]*data-filter-group="%d"[^>]*>(.*?)</%s>' % (tag, group_index, tag),
        rendered, re.S)
    return match.group(1) if match else None


# ======================================================================
# Section 1b-X5: 22-09-PLAN.md Task 1 - the icon-only row toggle.
# ======================================================================


def test_row_toggle_is_icon_only_and_named_in_both_languages(tmp_path):
    """the rendered Flights table carries zero visible More/Plus/Less/Moins button labels and
    exactly one icon-only toggle button per row, each carrying a translated aria-label that
    swaps with its state and names the picture reachable inside (22-09-PLAN.md Task 1, X5)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "tg01", "callsign": "TOGGLE1"},
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "tg02", "callsign": "TOGGLE2"},
    ])
    rendered_en = history_page.render(vp.history_ctx(tmp_path))
    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = history_page.render(vp.history_ctx(tmp_path))
    finally:
        prefs.set_request_prefs(lang="en")

    for lang, rendered in (("en", rendered_en), ("fr", rendered_fr)):
        table = vp.table_markup(rendered)
        assert table is not None, "could not locate the rendered table (%s)" % lang
        for retired in ("More", "Plus", "Less", "Moins"):
            assert (">%s<" % retired) not in table, (
                "expected zero visible %r button labels in the rendered table (%s)"
                % (retired, lang))
        toggles = re.findall(r"<button[^>]*data-row-toggle[^>]*>(.*?)</button>", table, re.S)
        assert len(toggles) == 2, "lang=%s toggles=%r" % (lang, toggles)
        for inner in toggles:
            assert re.sub(r"<[^>]*>", "", inner).strip() == history_page._TOGGLE_GLYPH
            assert 'aria-hidden="true"' in inner

        show = i18n.t_lang(history_page._TOGGLE_SHOW_LABEL, lang)
        hide = i18n.t_lang(history_page._TOGGLE_HIDE_LABEL, lang)
        if lang == "fr":
            assert show != history_page._TOGGLE_SHOW_LABEL
            assert hide != history_page._TOGGLE_HIDE_LABEL
        for needle in (
                'aria-label="%s"' % layout.escape_html(show),
                '%s="%s"' % (history_page._TOGGLE_SHOW_LABEL_ATTR, layout.escape_html(show)),
                '%s="%s"' % (history_page._TOGGLE_HIDE_LABEL_ATTR, layout.escape_html(hide)),
        ):
            assert table.count(needle) == 2, "lang=%s needle=%r" % (lang, needle)
        for label in (history_page._TOGGLE_SHOW_LABEL, history_page._TOGGLE_HIDE_LABEL):
            assert "picture" in label


def test_aria_expanded_sits_only_on_buttons_never_on_a_tr(tmp_path):
    """in the RENDERED Flights page no <tr> carries aria-expanded and every aria-expanded
    occurrence sits on a <button> (22-09-PLAN.md Task 1, X5 — the state never moves onto
    the row element)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "ae01", "callsign": "ARIAEXP"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert not re.findall(r"<tr[^>]*aria-expanded", rendered)
    for match in re.finditer(r"<([a-z]+)[^>]*\baria-expanded=", rendered):
        assert match.group(1) == "button", (
            "expected every aria-expanded to sit on a <button>, found one on <%s>"
            % match.group(1))
    assert re.search(r"<button[^>]*\baria-expanded=", rendered)


def test_row_toggle_css_reuses_the_copy_btn_icon_only_pattern(tmp_path, served_css):
    """style.css's new .row-toggle rule block reuses .copy-btn's icon-only pattern verbatim
    (same 22x22 box, same radius, the same ::before inset synthesizing 44x44, the same 14px
    glyph) and introduces no new size literal; the pointer cursor is keyed only on the class
    flight-rows.js adds at load (22-09-PLAN.md Task 1, X5)"""
    copy_base = declarations_for(served_css, ".copy-btn")
    toggle_base = declarations_for(served_css, ".row-toggle")
    for prop in ("width", "height", "border-radius"):
        assert copy_base.get(prop) == toggle_base.get(prop), (
            "expected .row-toggle's %s to equal .copy-btn's" % prop)

    copy_before = declarations_for(served_css, ".copy-btn::before")
    toggle_before = declarations_for(served_css, ".row-toggle::before")
    assert "inset" in toggle_before, "expected .row-toggle::before to declare inset"
    assert copy_before.get("inset") == toggle_before.get("inset")

    copy_icon = declarations_for(served_css, ".copy-btn .icon")
    toggle_glyph = declarations_for(served_css, ".row-toggle__glyph")

    def px_sizes(*decl_dicts):
        joined = " ".join(v for decls in decl_dicts for v in decls.values())
        return set(re.findall(r"\d+px", joined))

    copy_sizes = px_sizes(copy_base, copy_before, copy_icon)
    toggle_sizes = px_sizes(toggle_base, toggle_before, toggle_glyph)
    new_sizes = toggle_sizes - copy_sizes
    assert not new_sizes, "expected .row-toggle to introduce no new size literal, found %s" % sorted(new_sizes)
    assert "14px" in toggle_sizes, "expected the .row-toggle glyph to be sized at .copy-btn's own 14px"

    clickable = declarations_for(served_css, ".flight-row--clickable")
    assert clickable.get("cursor") == "pointer"

    # The pointer cursor is keyed ONLY on the class flight-rows.js adds at
    # load — never rendered server-side (the no-JS floor), asserted
    # against a real render() call rather than history_page.py's source.
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "rtc01", "callsign": "ROWTOGCSS"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert "flight-row--clickable" not in rendered, (
        "did not expect the server to render the script's own clickable marker class — a "
        "scripts-blocked page must show no pointer cursor on a row")


def test_flight_rows_js_swaps_the_name_and_delegates_the_row_click(tmp_path, app):
    """companion/static/flight-rows.js reads every attribute name history_page.py renders,
    swaps aria-label instead of a visible label, returns early for an interactive click
    target (T-22-32) and uses no markup-writing sink; the server still renders every detail
    row visible with no collapsing class, no hidden and no inline style (22-09-PLAN.md
    Task 1, X5/D-09)"""
    js = served_asset(app, "/static/flight-rows.js")
    for token in (history_page._TOGGLE_SHOW_LABEL_ATTR, history_page._TOGGLE_HIDE_LABEL_ATTR,
                  "data-flight-row", "data-row-toggle",
                  "flight-detail-row--collapsed", "flight-row--clickable"):
        assert token in js, "expected flight-rows.js to read/write %r" % (token,)
    assert 'setAttribute("aria-label"' in js, "expected flight-rows.js to swap the button's aria-label"
    for retired in ("data-more-text", "data-less-text", "textContent"):
        assert retired not in js, (
            "expected flight-rows.js to stop writing the retired visible label (%r)" % (retired,))
    for tag in ("A:", "BUTTON:", "INPUT:", "SELECT:", "TEXTAREA:", "LABEL:", "SUMMARY:"):
        assert tag in js, "expected flight-rows.js's interactive-target guard to name %s" % tag
    assert "innerHTML" not in js and "insertAdjacentHTML" not in js, (
        "expected flight-rows.js to use no markup-writing DOM sink")

    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "nj01", "callsign": "NOJSFLR"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert "flight-detail-row--collapsed" not in rendered, (
        "expected the server-rendered detail row to carry no collapsing class (the no-JS "
        "floor is a fully visible detail row)")
    detail = re.search(r'<tr class="flight-detail-row"[^>]*>', rendered)
    assert detail is not None, "expected a server-rendered detail row"
    assert "hidden" not in detail.group(0) and "style=" not in detail.group(0), (
        "expected the detail row to carry neither a hidden attribute nor an inline style")
    assert "cursor" not in rendered, "did not expect any cursor declaration in the server's own output"
    assert rendered.count("data-flight-row") == 1, (
        "expected exactly one data-flight-row hook per summary row, found %d"
        % rendered.count("data-flight-row"))


def test_detail_row_carries_hex_iso_runway_not_in_summary_row(tmp_path):
    """the hex, the raw ISO timestamp and the runway render inside the detail row and NOT in
    the summary row's own slice (21-03-PLAN.md Task 2, D-15)"""
    raw_ts = "2026-08-27T10:00:00+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": raw_ts, "hex": "3944F2", "callsign": "DETCONTENT", "tracked_runway": "3"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    summary_match = re.search(r'<tr class="row"[^>]*>(.*?)</tr>', rendered, re.S)
    detail_match = re.search(r'<tr class="flight-detail-row"[^>]*>(.*?)</tr>', rendered, re.S)
    assert summary_match is not None and detail_match is not None, (
        "could not locate the summary/detail row pair")
    summary_block, detail_block = summary_match.group(1), detail_match.group(1)
    runway_label = device_config.runway_label("3")
    for value in ("3944F2", raw_ts, runway_label):
        assert value in detail_block, "expected %r inside the detail row" % (value,)
        assert value not in summary_block, "did not expect %r visible inside the summary row" % (value,)
    assert 'colspan="6"' in detail_block or 'colspan="6"' in rendered, (
        "expected the detail row's <td> to span all 6 columns")


def test_flights_render_has_no_inline_script_or_handler_attribute(tmp_path):
    """a rendered Flights page contains no inline <script> and no on*= handler attribute
    (21-03-PLAN.md Task 2, D-15/R-12)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "ni01", "callsign": "NOINLINE"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    for match in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>", rendered):
        raise AssertionError("expected no inline <script> without a src, found %r" % match.group(0))
    assert not re.search(r'\son[a-z]+="', rendered), "expected no on*= inline handler attribute"


def test_flights_table_padding_rule_uses_space_sm_token_both_axes(served_css):
    """style.css's table.data-table--flights padding rule uses var(--space-sm) on both axes,
    never a literal px value (21-03-PLAN.md Task 3, D-15)"""
    for selector in ("table.data-table--flights td", "table.data-table--flights th"):
        decls = declarations_for(served_css, selector)
        assert decls.get("padding") == "var(--space-sm) var(--space-sm)"


def test_flights_thead_carries_exactly_six_cells_in_both_languages(tmp_path):
    """the rendered Flights table's <thead> carries exactly six <th> cells in both en and fr
    (21-03-PLAN.md Task 3, D-15)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "th01", "callsign": "THEADSIX"},
    ])
    rendered_en = history_page.render(vp.history_ctx(tmp_path))
    doc_en = parse_html(rendered_en)
    assert len(doc_en.select("thead th")) == 6, "expected exactly 6 <th> cells in the English <thead>"

    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = history_page.render(vp.history_ctx(tmp_path))
    finally:
        prefs.set_request_prefs(lang="en")
    doc_fr = parse_html(rendered_fr)
    assert len(doc_fr.select("thead th")) == 6, "expected exactly 6 <th> cells in the French <thead>"


def test_mobile_details_three_copy_buttons(tmp_path):
    """the mobile card's details region contains exactly 3 copy buttons (callsign, hex, full
    timestamp), each immediately followed by its data-copy-feedback sibling"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "cm01", "callsign": "CMONE"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    details_match = re.search(r'<details class="history-card__details">(.*?)</details>', rendered, re.S)
    assert details_match is not None, "expected a history-card__details block"
    details = details_match.group(1)
    assert details.count("data-copy-value") == 3, (
        "expected exactly 3 copy buttons in the mobile details region, got %d"
        % details.count("data-copy-value"))
    feedback_pairs = len(re.findall(r"</button><span[^>]*data-copy-feedback", details))
    assert feedback_pairs == 3, (
        "expected each mobile copy button to be immediately followed by its "
        "data-copy-feedback sibling, found %d pairs" % feedback_pairs)


def test_copy_button_carries_data_copied_text_english_and_french(tmp_path):
    """a Flights render's copy buttons carry data-copied-text="Copied" under the default
    language and data-copied-text="Copié" under lang='fr' (D-06)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "cd01", "callsign": "CDONE"},
    ])
    rendered_en = history_page.render(vp.history_ctx(tmp_path))
    assert 'data-copied-text="Copied"' in rendered_en

    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = history_page.render(vp.history_ctx(tmp_path))
    finally:
        prefs.set_request_prefs(lang="en")
    assert 'data-copied-text="Copié"' in rendered_fr


def test_desktop_copy_reveal_stylesheet_contract(served_css):
    """the desktop copy-button reveal rule lives inside the shared 960px block, is scoped by
    [data-copy-value] (never the bare .copy-btn class), reveals via opacity + pointer-events
    (never visibility: hidden or display: none) on both tr:hover and tr:focus-within
    (quick task 260903-peo, UIR-17)"""
    at_rules = ("@media (min-width: 960px)",)
    rest = declarations_for(served_css, ".data-table tbody tr [data-copy-value]", at_rules=at_rules)
    assert "opacity" in rest
    assert rest.get("visibility") != "hidden"
    assert rest.get("display") != "none"

    for hover_selector in (
            ".data-table tbody tr:hover [data-copy-value]",
            ".data-table tbody tr:focus-within [data-copy-value]"):
        reveal = declarations_for(served_css, hover_selector, at_rules=at_rules)
        assert reveal.get("opacity") == "1", "expected the reveal rule to restore opacity: 1"
        assert reveal.get("visibility") != "hidden"
        assert reveal.get("display") != "none"


def test_desktop_row_copy_buttons_and_eye_button_discriminator(tmp_path):
    """a real rendered desktop History summary row carries zero copy buttons (21-03-PLAN.md
    Task 1, D-15) and no picture control at all (22-09-PLAN.md Task 2, X5 — it moved into
    the detail row), and that control still never carries data-copy-value — the
    discriminator the desktop reveal rule depends on (quick task 260903-peo, UIR-17)"""
    names = ["2026-08-27T10-00-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "rev01", "callsign": "REVEAL"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    tr_block = _row_markup(rendered, "tr", 0)
    assert tr_block is not None, "could not locate the seeded row's desktop <tr>"
    assert tr_block.count("data-copy-value") == 0, (
        "expected zero copy buttons in the desktop summary row, got %d"
        % tr_block.count("data-copy-value"))
    assert "data-view-panel-src" not in tr_block, (
        "did not expect the picture control in the summary row — it moved into the detail "
        "row (22-09-PLAN.md Task 2, X5)")
    detail_block = vp.detail_row_block(rendered, 0)
    assert detail_block is not None and "data-view-panel-src" in detail_block, (
        "expected the row's picture control to render in the detail row")
    view_panel_start = detail_block.index("data-view-panel-src")
    view_panel_tag = detail_block[
        detail_block.rindex("<", 0, view_panel_start):detail_block.index(">", view_panel_start) + 1]
    assert "data-copy-value" not in view_panel_tag, (
        "the picture control must never carry data-copy-value — that is the sole "
        "discriminator separating it from any copy button the desktop reveal rule targets")


def test_copy_buttons_no_longer_share_one_aria_label(tmp_path):
    """with two differently-named rows, at least two distinct copy-button aria-label values
    render on the page — the '50 identical names' defect closed (A-37/D-20)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "dl01", "callsign": "DISTINCT1"},
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "dl02", "callsign": "DISTINCT2"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    aria_labels = set(re.findall(r'aria-label="([^"]*)"', rendered))
    copy_labels = {
        label for label in aria_labels
        if "Copy callsign" in label or "Copy hex ID" in label or "Copy timestamp" in label}
    assert len(copy_labels) >= 2, (
        "expected at least 2 distinct copy-button aria-labels, got %d: %r"
        % (len(copy_labels), copy_labels))


def test_each_copy_button_aria_label_names_its_own_row(tmp_path):
    """each row's mobile-card callsign copy button carries an aria-label naming that row's
    own callsign, not a shared/generic name (A-37/D-20, retargeted off the desktop row by
    21-03-PLAN.md Task 1)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "or01", "callsign": "OWNROW1"},
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "or02", "callsign": "OWNROW2"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    # Rows render newest-first (history_db.recent_runway_events()'s own
    # ordering) - the later timestamp (OWNROW2) lands at
    # data-filter-group=0, the earlier one (OWNROW1) at 1.
    for index, callsign in ((0, "OWNROW2"), (1, "OWNROW1")):
        li_block = _row_markup(rendered, "li", index)
        assert li_block is not None, "could not locate mobile row block for data-filter-group=%d" % index
        assert callsign in li_block, "expected %r inside its own row's markup" % callsign
        assert ('aria-label="Copy callsign %s"' % callsign) in li_block, (
            "expected row %d's callsign copy button to name its own callsign %r" % (index, callsign))


def test_copy_button_script_propagates_execcommand_success(app):
    """copy-button.js propagates fallbackCopy()'s real document.execCommand(...) result
    instead of discarding it, and stays ES5-safe/sink-free (A-37/D-20)"""
    src = served_asset(app, "/static/copy-button.js")
    assert "return document.execCommand" in src, (
        "expected fallbackCopy() to return document.execCommand(...)'s result")
    banned = ("let ", "const ", "=>", "`", "innerHTML", "insertAdjacentHTML", "document.write", "eval(")
    for token in banned:
        assert token not in src, "copy-button.js must not contain %r" % token


def test_copy_button_markup_carries_icon_and_label_spans(tmp_path):
    """every rendered copy button carries exactly one copy-btn__icon span and one empty
    copy-btn__label span, and its data-copy-feedback sibling still immediately follows the
    button (D-20)"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "sp01", "callsign": "SPANS1"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    button_count = rendered.count("data-copy-value")
    assert button_count > 0, "expected at least one copy button to render"
    icon_count = rendered.count('<span class="copy-btn__icon" aria-hidden="true">')
    assert icon_count == button_count, (
        "expected exactly one copy-btn__icon span per copy button, got %d for %d buttons"
        % (icon_count, button_count))
    label_count = rendered.count('<span class="copy-btn__label"></span>')
    assert label_count == button_count, (
        "expected exactly one empty copy-btn__label span per copy button, got %d for %d buttons"
        % (label_count, button_count))
    feedback_pairs = len(re.findall(r"</button><span[^>]*data-copy-feedback", rendered))
    assert feedback_pairs == button_count, (
        "expected every copy button to still be immediately followed by its "
        "data-copy-feedback sibling, found %d pairs for %d buttons" % (feedback_pairs, button_count))


def test_copy_button_script_references_label_class_and_1500ms(app):
    """copy-button.js references the copy-btn__label/copy-btn--copied class names and the
    1.5s (1500ms) feedback window (D-20)"""
    src = served_asset(app, "/static/copy-button.js")
    assert "copy-btn__label" in src
    assert "copy-btn--copied" in src
    assert "1500" in src


def test_style_css_styles_both_copy_feedback_classes(served_css):
    """style.css styles both copy-btn__label and copy-btn--copied (D-20)"""
    assert declarations_for(served_css, ".copy-btn__label")
    assert declarations_for(served_css, ".copy-btn--copied .copy-btn__label")


def test_presentation_labels_in_full_render(tmp_path):
    """confirmed_state/tracked_runway presentation labels (Task 1's format_event_row()
    fixture) also appear correctly through the full render() output"""
    vp.seed_runway_events(tmp_path, [
        {
            "ts": "2026-08-27T10:00:00+00:00", "hex": "pl01", "callsign": "PL1",
            "confirmed_state": "departing", "tracked_runway": "3",
        },
        {
            "ts": "2026-08-27T10:01:00+00:00", "hex": "pl02", "callsign": "PL2",
            "confirmed_state": "taxiing",
        },
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path))
    for expected in ("Departing", device_config.runway_label("3"), "Taxiing"):
        assert expected in rendered, "expected %r in the rendered History page" % expected
    for wrong in ("on_runway", "approaching", 'departed"'):
        assert wrong not in rendered, (
            "did not expect the audit's own incorrect literal state value %r" % wrong)


def test_french_render_translates_the_runway_cell_label(tmp_path):
    """a French Flights render translates the tracked_runway cell's registry label
    ('Runway 3 (07/25)' -> 'Piste 3 (07/25)'), with no English label leaking in
    (Polish fix 5, D-05)"""
    vp.seed_runway_events(tmp_path, [
        {
            "ts": "2026-08-27T10:00:00+00:00", "hex": "pl03", "callsign": "PL3",
            "confirmed_state": "departing", "tracked_runway": "3",
        },
    ])
    prefs.set_request_prefs(lang="fr")
    try:
        rendered = history_page.render(vp.history_ctx(tmp_path))
    finally:
        prefs.set_request_prefs(lang="en")
    assert "Piste 3 (07/25)" in rendered, "expected the French runway label 'Piste 3 (07/25)'"
    assert device_config.runway_label("3") not in rendered, (
        "expected the English runway label to be absent from the French render")


# ======================================================================
# Section 1b: quick task 260903-etm - History's top-of-page render-
# gallery <section> retired outright. The per-row "View panel near this
# time" lightbox (D-20) is the sole surviving way to see a rendered
# panel on this page; the orphaned colour caveat is rehomed into its
# note.
# ======================================================================


def test_history_render_gallery_section_absent_with_content(tmp_path):
    """with 3 gallery entries and one seeded flight row, the rendered page carries zero <h2,
    zero page-section, zero gallery-grid/gallery-tile elements and zero occurrences of the
    retired heading/empty-state text, WHILE the per-row View-panel mechanism (a trigger,
    exactly one lightbox dialog) and History's own card disclosures survive in the same
    render"""
    names = [
        "2026-08-27T10-02-00+00-00.png",
        "2026-08-27T10-01-00+00-00.png",
        "2026-08-27T10-00-00+00-00.png",
    ]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:03:00+00:00", "hex": "notdisc1", "callsign": "NOTDISC"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    assert "<h2" not in rendered
    assert "page-section" not in rendered
    assert 'class="gallery-grid"' not in rendered
    assert 'class="gallery-tile"' not in rendered
    assert "Recent renders" not in rendered
    assert "No renders yet." not in rendered
    assert "data-view-panel-src" in rendered, "expected at least one View-panel trigger to survive"
    assert rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) == 1
    assert '<details class="history-card__details"' in rendered, (
        "expected History's own card disclosures to survive")


def test_history_render_gallery_section_absent_when_empty(tmp_path):
    """with gallery_entries=[], the same absences hold (the section is gone, not merely
    emptied) and, as before, zero View-panel triggers and zero lightbox dialogs render"""
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=[]))
    assert "<h2" not in rendered
    assert "page-section" not in rendered
    assert 'class="gallery-grid"' not in rendered
    assert 'class="gallery-tile"' not in rendered
    assert "Recent renders" not in rendered
    assert "No renders yet." not in rendered
    assert "data-view-panel-src" not in rendered
    assert ('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) not in rendered


def test_view_panel_trigger_is_a_labelled_control_with_the_long_form_as_title(tmp_path):
    """the rendered picture control is a LABELLED text control carrying the translated
    "View picture" text and no aria-label, with "View panel near this time" surviving as its
    title, on both the desktop detail row and the mobile card (22-09-PLAN.md Task 2, X5)"""
    names = ["2026-08-27T10-00-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "vptt01", "callsign": "VPTITLE"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    escaped_label = layout.escape_html(history_page.VIEW_PANEL_LABEL)
    expected_title = 'title="%s"' % escaped_label
    expected_text = '>%s</button>' % layout.escape_html(history_page.VIEW_PICTURE_LABEL)
    detail_block = vp.detail_row_block(rendered, 0)
    li_block = _row_markup(rendered, "li", 0)
    assert detail_block is not None and li_block is not None, (
        "could not locate the detail row / mobile card for row 0")
    for label, block in (("detail <tr>", detail_block), ("mobile <li>", li_block)):
        assert expected_title in block, "expected %s to carry title=%r" % (label, escaped_label)
        assert expected_text in block, (
            "expected %s's picture control to carry the visible label %r"
            % (label, history_page.VIEW_PICTURE_LABEL))
        trigger_start = block.index("data-view-panel-src")
        trigger_tag = block[block.rindex("<", 0, trigger_start):block.index(">", trigger_start) + 1]
        assert "aria-label" not in trigger_tag, (
            "did not expect an aria-label on %s's picture control — the visible label is its "
            "accessible name (WCAG 2.5.3 label-in-name)" % label)


def test_colour_caveat_rehomed_into_lightbox_note(tmp_path):
    """the colour caveat sentence appears exactly once in the rendered page, and that single
    occurrence lies inside the lightbox__note element (the caveat's new, and only, home
    after the render-gallery section's removal)"""
    names = ["2026-08-27T10-00-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "cvt001", "callsign": "CAVEAT"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    assert rendered.count(history_page.COLOUR_CAVEAT) == 1
    note_match = re.search(r'<p class="lightbox__note text-body">(.*?)</p>', rendered, re.S)
    assert note_match is not None, "could not locate the lightbox__note element"
    assert history_page.COLOUR_CAVEAT in note_match.group(1)


def test_render_gallery_no_preview_apparatus_even_with_panel_file(tmp_path):
    """with a real panel.bin on disk and gallery entries seeded, the rendered output contains
    zero occurrences of /preview.png, preview-frame, preview-image, and the old no-panel
    caption sentence - a present panel file changes nothing about the markup any more (this
    check's real subject is quick task 260903-c4o's /preview.png route retirement, not the
    render-gallery section retired by this task; kept in place rather than dropped)"""
    names = ["20260827T100000Z.png"]
    vp.seed_gallery(tmp_path, names)
    vp.write_panel_file(tmp_path)
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    for marker in ("/preview.png", "preview-frame", "preview-image"):
        assert marker not in rendered, "did not expect %r anywhere in the rendered page" % marker
    assert "No panel has been rendered yet." not in rendered


def test_now_showing_no_preview_freshness_apparatus(tmp_path):
    """the rendered History page carries no data-stale-banner and no Refresh link — D-18's
    retired apparatus stays retired — while carrying exactly one data-loaded-at marker,
    built by layout.freshness_line_html(), because D7/CFG-37 puts this page on the refresh
    loop and freshness.js returns at its first guard without one (retargeted in place by
    23-08-PLAN.md Task 1)"""
    rendered = history_page.render(vp.history_ctx(tmp_path))
    assert "data-stale-banner" not in rendered
    assert rendered.count("data-loaded-at") == 1, (
        "expected exactly one data-loaded-at marker on the History page, found %d"
        % rendered.count("data-loaded-at"))
    built = layout.freshness_line_html(vp.history_ctx(tmp_path)["now"])
    assert "data-loaded-at" in built
    marker_at = rendered.index("data-loaded-at")
    around = rendered[max(0, marker_at - 400):marker_at]
    assert "<a " not in around[around.rfind('<p class="page-header__freshness'):], (
        "did not expect a link inside the freshness line — D-18 retired the manual Refresh "
        "control outright and the marker's home is the hidden pill the loop reveals, never "
        "an anchor the reader has to press")


def test_gallery_name_to_iso_fixtures():
    """history_page._gallery_name_to_iso() reverses a well-formed gallery filename and
    returns None (never raising) on a missing 'T' separator or a malformed time+offset
    portion"""
    well_formed = history_page._gallery_name_to_iso("2026-08-30T19-20-42+00-00.png")
    assert well_formed == "2026-08-30T19:20:42+00:00"
    assert history_page._gallery_name_to_iso("not-a-real-name.png") is None
    assert history_page._gallery_name_to_iso("2026-08-30Tgarbage.png") is None


def test_view_panel_trigger_reuses_the_small_grey_secondary_treatment(tmp_path, served_css):
    """a rendered History page's picture control carries no icon glyph at all and reuses
    .calendar-disconnect-btn's small-grey-secondary treatment — that component's second
    consumer, with no .btn family started (22-09-PLAN.md Task 2, X5)"""
    names = ["2026-08-27T10-00-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "vpicon1", "callsign": "VPICON"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    assert "data-view-panel-src" in rendered, "expected at least one View-panel trigger to render"
    trigger_start = rendered.find("data-view-panel-src")
    button_start = rendered.rfind("<button", 0, trigger_start)
    button_end = rendered.find("</button>", trigger_start)
    button_markup = rendered[button_start:button_end]
    assert "<svg" not in button_markup, (
        "did not expect an icon glyph on the picture control — it is a labelled text control "
        "now, not a 16px icon-only eye")
    assert 'class="calendar-disconnect-btn"' in button_markup, (
        "expected the picture control to reuse .calendar-disconnect-btn's small-grey-secondary "
        "treatment, got %r" % button_markup[:120])
    assert "btn--" not in rendered, "did not expect a .btn-- family class to be started"
    assert declarations_for(served_css, "button.calendar-disconnect-btn")


# ======================================================================
# Section 1c: 06.6.4.1-05 Task 2 - server-side nearest-render lookup,
# per-row View-panel buttons, and the shared lightbox (D-20).
# ======================================================================


def test_nearest_gallery_entry_behaviour():
    """nearest_gallery_entry() matches the latest at-or-before entry (inclusive boundary),
    skips an entry with an unrecoverable filename timestamp, and returns None for an empty
    entry list, an empty/unparseable row_ts, or when every recoverable entry is strictly
    after row_ts"""
    entries = [
        "2026-08-27T10-05-00+00-00.png",
        "2026-08-27T10-02-00+00-00.png",
        "2026-08-27T10-00-00+00-00.png",
        "not-a-real-gallery-name.png",  # unparseable - must be skipped
    ]
    assert history_page.nearest_gallery_entry(entries, "2026-08-27T10:03:00+00:00") == (
        "2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00")
    # Exact boundary: row_ts equal to an entry's own recovered timestamp
    # still matches that entry ("at or before" is inclusive).
    assert history_page.nearest_gallery_entry(entries, "2026-08-27T10:02:00+00:00") == (
        "2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00")
    assert history_page.nearest_gallery_entry(entries, "2026-08-27T09:00:00+00:00") is None
    assert history_page.nearest_gallery_entry([], "2026-08-27T10:03:00+00:00") is None
    assert history_page.nearest_gallery_entry(entries, "") is None
    assert history_page.nearest_gallery_entry(entries, "not-a-real-timestamp") is None
    assert history_page.nearest_gallery_entry(entries, None) is None


def test_view_panel_triggers_per_row_full_render(tmp_path):
    """for three gallery entries and three interleaved rows, each row's desktop and mobile
    View-panel trigger carries byte-identical, correctly-targeted
    data-view-panel-src/-caption attributes matching its own nearest gallery entry, and
    exactly one lightbox dialog is emitted"""
    names = [
        "2026-08-27T10-05-00+00-00.png",
        "2026-08-27T10-02-00+00-00.png",
        "2026-08-27T10-00-00+00-00.png",
    ]
    vp.seed_gallery(tmp_path, names)
    # Newest-first row order (history_rows()'s own ordering): VP-C (10:10)
    # -> VP-B (10:03) -> VP-A (10:01).
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "vpa01", "callsign": "VPA"},
        {"ts": "2026-08-27T10:03:00+00:00", "hex": "vpb01", "callsign": "VPB"},
        {"ts": "2026-08-27T10:10:00+00:00", "hex": "vpc01", "callsign": "VPC"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))

    expected_by_group = {
        0: ("2026-08-27T10-05-00+00-00.png", "2026-08-27T10:05:00+00:00"),  # VPC
        1: ("2026-08-27T10-02-00+00-00.png", "2026-08-27T10:02:00+00:00"),  # VPB
        2: ("2026-08-27T10-00-00+00-00.png", "2026-08-27T10:00:00+00:00"),  # VPA
    }
    for index, (expected_name, expected_iso) in expected_by_group.items():
        expected_src = "/gallery/%s" % expected_name
        expected_caption = history_page.lightbox_caption_text(expected_iso)

        # 22-09-PLAN.md Task 2 (X5): the desktop trigger moved from the
        # summary row into its sibling detail row.
        tr_block = vp.detail_row_block(rendered, index)
        li_block = _row_markup(rendered, "li", index)
        assert tr_block is not None and li_block is not None, "could not locate row block for row %d" % index

        for label, block in (("detail <tr>", tr_block), ("mobile <li>", li_block)):
            assert ('data-view-panel-src="%s"' % expected_src) in block, (
                "expected %s for row %d to carry data-view-panel-src=%r" % (label, index, expected_src))
            assert ('data-view-panel-caption="%s"' % expected_caption) in block, (
                "expected %s for row %d to carry data-view-panel-caption=%r" % (label, index, expected_caption))
            assert history_page.VIEW_PANEL_LABEL in block
            assert history_page.VIEW_PICTURE_LABEL in block

        tr_src = re.search(r'data-view-panel-src="([^"]*)"', tr_block).group(1)
        li_src = re.search(r'data-view-panel-src="([^"]*)"', li_block).group(1)
        tr_caption = re.search(r'data-view-panel-caption="([^"]*)"', tr_block).group(1)
        li_caption = re.search(r'data-view-panel-caption="([^"]*)"', li_block).group(1)
        assert tr_src == li_src and tr_caption == li_caption, (
            "expected byte-identical trigger attributes on the desktop and mobile "
            "representations of row %d" % index)

    assert rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) == 1


def test_view_panel_empty_gallery_zero_triggers_zero_dialog(tmp_path):
    """with an empty gallery entry list, History renders zero View-panel triggers and zero
    lightbox dialog elements, never a disabled or broken control"""
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "vpe01", "callsign": "VPEMPTY"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=[]))
    assert "data-view-panel-src" not in rendered
    assert ('id="%s"' % history_page.LIGHTBOX_DIALOG_ID) not in rendered


def test_lightbox_dom_contract_three_file_guard(tmp_path, panel_lookup_js):
    """the shared, Airlines-only and render-only lightbox token tuples each appear (or, for
    Airlines-only, are absent from History) exactly where their own classification says they
    must, across companion/static/panel-lookup.js and both pages' rendered markup"""
    names = ["2026-08-27T10-00-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:01:00+00:00", "hex": "dc01", "callsign": "DOMCONTRACT"},
    ])
    history_rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    # 29-01-PLAN.md (CFG-81): LIGHTBOX_REPLACE_FORM_CLASS is unconditional
    # now — the page-wide editing mode this guard used to need is deleted
    # — so a plain default render already carries it.
    airlines_rendered = airlines_page.render({})

    for token in _LIGHTBOX_SHARED_TOKENS:
        assert token in panel_lookup_js, "expected shared token %r in panel-lookup.js" % token
        assert token in history_rendered, "expected shared token %r in the rendered History page" % token
        assert token in airlines_rendered, "expected shared token %r in the rendered Airlines page" % token

    for token in _LIGHTBOX_AIRLINES_ONLY_TOKENS:
        assert token in panel_lookup_js, "expected Airlines-only token %r in panel-lookup.js" % token
        assert token in airlines_rendered, "expected Airlines-only token %r in the rendered Airlines page" % token
        assert token not in history_rendered, "did not expect Airlines-only token %r in the rendered History page" % token

    for token in _LIGHTBOX_RENDER_ONLY_TOKENS:
        assert token in airlines_rendered, "expected render-only token %r in the rendered Airlines page" % token


def test_view_panel_attr_constants_all_classified():
    """every airlines_page._VIEW_PANEL_*_ATTR constant's value is classified in exactly one of
    the three lightbox token tuples, discovered by reflection over dir(airlines_page) rather
    than a hand-copied name list"""
    all_tuples = (_LIGHTBOX_SHARED_TOKENS, _LIGHTBOX_AIRLINES_ONLY_TOKENS, _LIGHTBOX_RENDER_ONLY_TOKENS)

    seen = {}
    for tuple_name, tup in (
            ("_LIGHTBOX_SHARED_TOKENS", _LIGHTBOX_SHARED_TOKENS),
            ("_LIGHTBOX_AIRLINES_ONLY_TOKENS", _LIGHTBOX_AIRLINES_ONLY_TOKENS),
            ("_LIGHTBOX_RENDER_ONLY_TOKENS", _LIGHTBOX_RENDER_ONLY_TOKENS)):
        for token in tup:
            assert token not in seen, (
                "token %r is classified in both %s and %s - the three tuples must be pairwise disjoint"
                % (token, seen.get(token), tuple_name))
            seen[token] = tuple_name

    for name in dir(airlines_page):
        if not (name.startswith("_VIEW_PANEL_") and name.endswith("_ATTR")):
            continue
        value = getattr(airlines_page, name)
        memberships = [tup for tup in all_tuples if value in tup]
        assert len(memberships) == 1, (
            "airlines_page.%s = %r must be classified in exactly one of the three lightbox "
            "token tuples, found in %d" % (name, value, len(memberships)))


def test_panel_lookup_never_sets_image_src_to_empty_string(panel_lookup_js):
    """panel-lookup.js never sets image.src to the empty string anywhere in its
    comment-stripped source - D-02/RESEARCH.md Pitfall 1's single riskiest line, the exact
    cross-browser spurious-request bug this phase's imageless-open branch exists to avoid"""
    stripped = vp.strip_js_line_and_block_comments(panel_lookup_js)
    assert 'image.src = ""' not in stripped, (
        'expected zero occurrences of image.src = "" in panel-lookup.js\'s comment-stripped '
        "source (D-02/RESEARCH.md Pitfall 1)")


def test_panel_lookup_remove_attribute_src_is_conditional(panel_lookup_js):
    """panel-lookup.js's image.removeAttribute("src") call is nested inside a conditional
    branch (the src-absent case), never written unconditionally at module scope"""
    needle = 'image.removeAttribute("src")'
    assert needle in panel_lookup_js
    line = next(line for line in panel_lookup_js.splitlines() if needle in line)
    indent = len(line) - len(line.lstrip(" "))
    assert indent > 2, (
        "expected image.removeAttribute(\"src\") indented inside a conditional branch, not "
        "written unconditionally at module scope (indent was %d)" % indent)


def test_panel_lookup_shared_populate_function_two_call_sites(panel_lookup_js):
    """panel-lookup.js's shared populate-and-open function (openFromTrigger) is defined exactly
    once and referenced from at least two call sites - the click listener and the load-time
    auto-open (RESEARCH.md Pitfall 2's mandatory factoring)"""
    def_needle = "function openFromTrigger(trigger)"
    def_count = panel_lookup_js.count(def_needle)
    assert def_count == 1, "expected exactly one openFromTrigger definition, got %d" % def_count
    call_sites = panel_lookup_js.count("openFromTrigger(") - def_count
    assert call_sites >= 2, (
        "expected openFromTrigger referenced (called) from at least two sites, found %d" % call_sites)


def test_panel_lookup_location_search_read_once_outside_click_only_function(panel_lookup_js):
    """panel-lookup.js reads location.search exactly once in its own code, at script init,
    outside openFromTrigger (the one function reachable from a click) and after the click
    listener is already wired"""
    stripped = vp.strip_js_line_and_block_comments(panel_lookup_js)
    code_count = stripped.count("location.search")
    assert code_count == 1, (
        "expected location.search to be read exactly once in panel-lookup.js's own code "
        "(comments excluded), got %d" % code_count)
    func_start = panel_lookup_js.index("function openFromTrigger(trigger)")
    func_end = panel_lookup_js.index("\n  }\n", func_start)
    search_idx = panel_lookup_js.index("location.search")
    click_listener_idx = panel_lookup_js.index('document.addEventListener("click"')
    assert not (func_start < search_idx < func_end), (
        "expected location.search's one read outside openFromTrigger's own body")
    assert search_idx > click_listener_idx, (
        "expected location.search's one read positioned after the click listener is wired")


def test_panel_lookup_eleven_new_attrs_present_in_source(panel_lookup_js):
    """every one of the eleven new data-view-panel-* attribute name literals 14-02 added to the
    vocabulary appears at least once in panel-lookup.js's own source"""
    missing = [name for name in _NEW_VIEW_PANEL_ATTR_NAMES if name not in panel_lookup_js]
    assert not missing, (
        "expected every one of the eleven new data-view-panel-* attribute name literals in "
        "panel-lookup.js's source, missing: %r" % missing)


def test_panel_lookup_mode_hidden_toggles_before_showmodal(panel_lookup_js):
    """the mode-governed elements' (resolveNameForm/resolveUploadZone/replaceForm) hidden
    assignments all occur, textually, before openFromTrigger's own dialog.showModal() call
    (RESEARCH.md Pitfall 3 - showModal()'s one-time autofocus placement must see the final,
    already-toggled subtree)"""
    func_start = panel_lookup_js.index("function openFromTrigger(trigger)")
    show_modal_idx = panel_lookup_js.index("dialog.showModal();", func_start)
    func_body = panel_lookup_js[func_start:show_modal_idx]
    for needle in (
            'resolveNameForm.hidden = (mode !== "gap")',
            'resolveUploadZone.hidden = (mode !== "needs-artwork")',
            'replaceForm.hidden = (mode !== "art")'):
        assert needle in func_body, (
            "expected %r to occur, textually, before openFromTrigger's own dialog.showModal() call"
            % needle)


def test_panel_lookup_prevent_default_once_correctly_positioned(panel_lookup_js):
    """panel-lookup.js's evt.preventDefault() appears exactly once, inside the click listener,
    positioned after the trigger-null-check and before the showModal()-reaching
    openFromTrigger() call (D-12's <a> interception)"""
    src = panel_lookup_js
    click_idx = src.index('document.addEventListener("click"')
    # 25-07-PLAN.md Task 2 (CFG-51/D19): D-12's clause is about the CLICK
    # path specifically - exactly one interception there, plus the
    # dragover/drop pair the drop zone needs of its own (without them an
    # element is not a drop target, and the browser navigates away from
    # the dropped file).
    assert src.count("evt.preventDefault()") == 3, (
        "expected evt.preventDefault() exactly three times (the click interception, plus the "
        "dragover/drop pair that makes an element a drop target and stops the browser navigating "
        "to the dropped file), got %d" % src.count("evt.preventDefault()"))
    drop_block = src[src.index("function wireUploadDropZone("):click_idx]
    assert drop_block.count("evt.preventDefault()") == 2, (
        "expected exactly two evt.preventDefault() calls inside wireUploadDropZone(), got %d"
        % drop_block.count("evt.preventDefault()"))
    for handler in ('zone.addEventListener("dragover"', 'zone.addEventListener("drop"'):
        handler_idx = drop_block.index(handler)
        assert "evt.preventDefault()" in drop_block[handler_idx:drop_block.index("});", handler_idx)], (
            "expected an evt.preventDefault() inside %s's own handler — without it that half of "
            "the gesture does not work at all" % (handler,))
    assert src[click_idx:].count("evt.preventDefault()") == 1, (
        "expected exactly one evt.preventDefault() at or after the click listener, got %d"
        % src[click_idx:].count("evt.preventDefault()"))
    null_check_idx = src.index("if (!trigger) {", click_idx)
    prevent_idx = src.index("evt.preventDefault()", click_idx)
    open_call_idx = src.index("openFromTrigger(trigger)", click_idx)
    assert click_idx < null_check_idx < prevent_idx < open_call_idx, (
        "expected evt.preventDefault() positioned after the trigger-null-check and before "
        "openFromTrigger() (the one showModal()-reaching call) inside the click listener")


def test_panel_lookup_single_dialog_lookup_single_click_listener(panel_lookup_js):
    """panel-lookup.js still contains exactly one
    document.getElementById("panel-lookup-dialog") and exactly one
    document.addEventListener("click", ...) - this plan extended the existing single mechanism
    rather than adding a second one (D-03's own rejected alternative)"""
    dialog_count = panel_lookup_js.count('document.getElementById("panel-lookup-dialog")')
    click_count = panel_lookup_js.count('document.addEventListener("click"')
    assert dialog_count == 1, (
        'expected exactly one document.getElementById("panel-lookup-dialog"), got %d' % dialog_count)
    assert click_count == 1, (
        'expected exactly one document.addEventListener("click", ...), got %d' % click_count)


def test_panel_lookup_context_callsign_write_gated_on_count(panel_lookup_js):
    """panel-lookup.js's contextCallsign.textContent is assigned exactly once, gated on the same
    `count` that gates resolveContext.hidden, so an ordinary illustration's own caption can
    never be printed under the 'Example callsign' label (quick task 260921-n2n Task 2)"""
    n = panel_lookup_js.count("contextCallsign.textContent")
    assert n == 1, (
        "expected exactly one contextCallsign.textContent assignment in panel-lookup.js, got %d "
        "— an ungated second write would print an illustration's own caption under the "
        "'Example callsign' label again" % n)
    assert 'contextCallsign.textContent = count ? captionText : "";' in panel_lookup_js, (
        "expected contextCallsign.textContent's one assignment to be gated on the same `count` "
        "that gates resolveContext.hidden — an ungated assignment prints the picture's own "
        "caption under the 'Example callsign' label on every ordinary illustration")


def test_airlines_lightbox_constants_match_history():
    """airlines_page's LIGHTBOX_DIALOG_ID and its three _VIEW_PANEL_*_ATTR constants each equal
    history_page's own values (the duplicated-not-imported shared-lightbox contract)"""
    pairs = (
        ("LIGHTBOX_DIALOG_ID", airlines_page.LIGHTBOX_DIALOG_ID, history_page.LIGHTBOX_DIALOG_ID),
        ("_VIEW_PANEL_SRC_ATTR", airlines_page._VIEW_PANEL_SRC_ATTR, history_page._VIEW_PANEL_SRC_ATTR),
        ("_VIEW_PANEL_CAPTION_ATTR", airlines_page._VIEW_PANEL_CAPTION_ATTR,
            history_page._VIEW_PANEL_CAPTION_ATTR),
        ("_VIEW_PANEL_CLOSE_ATTR", airlines_page._VIEW_PANEL_CLOSE_ATTR, history_page._VIEW_PANEL_CLOSE_ATTR),
    )
    for name, airlines_value, history_value in pairs:
        assert airlines_value == history_value, (
            "expected airlines_page.%s (%r) to equal history_page.%s (%r)"
            % (name, airlines_value, name, history_value))


def test_history_lightbox_carries_zero_replace_markup(tmp_path):
    """a real, seeded history_page.render() call (real gallery entry, real runway event) renders
    its lightbox dialog exactly once, and carries zero occurrences of airlines_page's
    replace-form class, replace-action attribute, <form>, file input, enctype, or the framed
    zone's three class constants (quick task 260903-df3) anywhere (quick task 260903-btu)"""
    names = ["2026-08-27T10-05-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:06:00+00:00", "hex": "dc02", "callsign": "NOREPLACE"},
    ])
    rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    dialog_count = rendered.count('id="%s"' % history_page.LIGHTBOX_DIALOG_ID)
    assert dialog_count == 1, (
        "expected the History dialog exactly once (proves the absence checks below mean "
        "something), got %d" % dialog_count)
    for token, label in (
            (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, "airlines_page.LIGHTBOX_REPLACE_FORM_CLASS"),
            (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, "airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR"),
            ("<form", "<form"),
            ('<input type="file"', '<input type="file"'),
            ("enctype", "enctype"),
            (airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS, "airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS"),
            (airlines_page.REPLACE_HINT_CLASS, "airlines_page.REPLACE_HINT_CLASS"),
            (airlines_page.REPLACE_ICON_CLASS, "airlines_page.REPLACE_ICON_CLASS")):
        count = rendered.count(token)
        assert count == 0, (
            "expected zero occurrences of %s in a real, seeded history_page.render() output, "
            "got %d" % (label, count))


def test_replace_lightbox_names_appear_in_three_files_never_in_history(tmp_path, panel_lookup_js, served_css):
    """airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR and airlines_page.LIGHTBOX_REPLACE_FORM_CLASS
    each appear in companion/static/panel-lookup.js's source and in a real
    airlines_page.render({}) call, the exact '.lightbox__replace' selector (not merely a
    substring, which the newer '.lightbox__replace-zone' selector could otherwise satisfy)
    appears in companion/static/style.css standalone or as the head of the phase-14 three-way
    group, and neither token appears in a real, seeded history_page.render() call (quick task
    260903-btu; these two constants have no history_page counterpart by design and must never
    join _airlines_lightbox_constants_match_history()'s pairs tuple; pattern retargeted in
    place by phase 14 plan 14-03 Task 2)"""
    # 29-01-PLAN.md (CFG-81): LIGHTBOX_REPLACE_FORM_CLASS is unconditional
    # now (see the DOM-contract guard's own identical retarget above) - a
    # plain default render already carries it.
    airlines_rendered = airlines_page.render({})
    names = ["2026-08-27T10-07-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:08:00+00:00", "hex": "dc03", "callsign": "TOKENGONE"},
    ])
    history_rendered = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))

    for token in (airlines_page._VIEW_PANEL_REPLACE_ACTION_ATTR, airlines_page.LIGHTBOX_REPLACE_FORM_CLASS):
        assert token in panel_lookup_js, "expected %r in companion/static/panel-lookup.js" % (token,)
        assert token in airlines_rendered, "expected %r in a real airlines_page.render({}) call" % (token,)
        assert token not in history_rendered, (
            "expected %r to never appear in a real, seeded history_page.render() call" % (token,))
    # 14-08 on-glass fix: the exact selector carries `:not([hidden])`
    # immediately after the class name, as the head of a three-way group
    # (.lightbox__replace:not([hidden]), .lightbox__resolve-name:not(
    # [hidden]), .lightbox__delete:not([hidden]) { ... }) — the exact
    # form, built from the constant, never a bare substring that the
    # newer '-zone' selector could also satisfy.
    exact_selector = ".%s:not([hidden])" % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS
    assert declarations_for(served_css, exact_selector), (
        "expected a %r selector (not merely a '-zone' prefix match) in companion/static/style.css "
        "— the fourth file in the chain, and the one whose drift would leave the form functional "
        "but unstyled" % (exact_selector,))


def test_airlines_render_empty_ctx_still_contains_gallery_grid():
    """airlines_page.render({}) with a literal empty dict still succeeds and its output still
    contains the gallery grid (quick task 260902-v26's ctx.get("state_dir") tolerance)"""
    rendered = airlines_page.render({})
    assert "illustration-grid" in rendered, (
        "expected render({}) to still contain the .illustration-grid gallery container")


# ======================================================================
# 19-08-PLAN.md Task 1 (D-21/A-38): the "Unidentified airlines" gap
# strip. 29-02-PLAN.md (CFG-82) supersedes the order this section's own
# check pins: the strip now renders AFTER the filter bar and the
# gallery grid, not before them.
# ======================================================================


def test_airlines_gap_strip_renders_after_the_gallery_with_heading_and_no_grid_placeholder(tmp_path):
    """a render with an eligible gap emits the "Unidentified airlines" strip with its exact
    heading and sentence after the filter bar and the gallery grid, and the curated artwork
    grid holds no gap card (D-21/A-38, 19-08-PLAN.md Task 1, order superseded by CFG-82,
    29-02-PLAN.md)"""
    vp.seed_unresolved_prefixes(tmp_path, {
        "XYZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
    })
    rendered = airlines_page.render({"state_dir": str(tmp_path)})
    assert airlines_page.GAP_STRIP_HEADING in rendered
    assert airlines_page.GAP_STRIP_BODY in rendered
    strip_index = rendered.index(airlines_page.GAP_STRIP_HEADING)
    filter_bar_index = rendered.index('class="filter-bar')
    gallery_index = rendered.index('class="illustration-grid"')
    assert strip_index > filter_bar_index, "expected the gap strip to render after the filter bar (CFG-82, 29-02-PLAN.md)"
    assert strip_index > gallery_index, "expected the gap strip to render after the gallery grid (CFG-82, 29-02-PLAN.md)"
    assert "airline-card__placeholder" not in rendered[:strip_index], (
        "expected the curated artwork grid to hold no gap card placeholder")


def test_airlines_gap_strip_absent_with_no_gaps(tmp_path):
    """a render with no eligible gaps emits no "Unidentified airlines" strip and no empty
    section (D-21, 19-08-PLAN.md Task 1)"""
    rendered = airlines_page.render({"state_dir": str(tmp_path)})
    assert airlines_page.GAP_STRIP_HEADING not in rendered
    assert '<section class="page-section">' not in rendered


# ======================================================================
# 29-02-PLAN.md (CFG-82): the page's whole section order, asserted as a
# chain of relationships (never a literal offset).
# ======================================================================


def test_airlines_section_order_is_title_then_filter_then_gallery_then_gapstrip_then_lightbox(tmp_path):
    """on a render with both an eligible gap and at least one curated gallery card, the page's
    own sections chain title < filter bar < gallery grid < "Unidentified airlines" strip < the
    lightbox dialog, each literal occurring exactly once (CFG-82, 29-02-PLAN.md)"""
    vp.seed_unresolved_prefixes(tmp_path, {
        "XYZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
    })
    rendered = airlines_page.render({"state_dir": str(tmp_path)})

    literals = (
        ("title", '<h1 class="page-title"'),
        ("filter", 'class="filter-bar"'),
        ("gallery", 'class="illustration-grid"'),
        ("gapstrip", airlines_page.GAP_STRIP_HEADING),
        ("lightbox", '<dialog class="lightbox'),
    )
    indices = {}
    for name, literal in literals:
        occurrences = rendered.count(literal)
        assert occurrences == 1, "expected exactly one occurrence of %r (the %s section), found %d" % (literal, name, occurrences)
        indices[name] = rendered.index(literal)

    order = ["title", "filter", "gallery", "gapstrip", "lightbox"]
    for earlier, later in zip(order, order[1:]):
        assert indices[earlier] < indices[later], (
            "expected %s before %s, but got indices %r (CFG-82, 29-02-PLAN.md)" % (earlier, later, indices))


def test_airlines_no_chrome_gate_survives_the_reorder(tmp_path):
    """the reorder does not touch render()'s own no-chrome gate: a render with gap cards but no
    curated pairs still shows the filter bar, and a render with neither shows no filter bar at
    all (CFG-82, 29-02-PLAN.md)"""
    original_target_variants_by_airline = illustrations.target_variants_by_airline
    tmp_a = tmp_path / "gap-only"
    tmp_a.mkdir()
    try:
        vp.seed_unresolved_prefixes(tmp_a, {
            "XYZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
        })
        illustrations.target_variants_by_airline = lambda: []
        rendered_gap_only = airlines_page.render({"state_dir": str(tmp_a)})
    finally:
        illustrations.target_variants_by_airline = original_target_variants_by_airline
    assert 'class="filter-bar"' in rendered_gap_only, (
        "expected the filter bar to still render when there are gap cards but no curated pairs "
        "(the gate is `pairs or gap_shown`, CFG-82, 29-02-PLAN.md)")

    tmp_b = tmp_path / "neither"
    tmp_b.mkdir()
    try:
        illustrations.target_variants_by_airline = lambda: []
        rendered_neither = airlines_page.render({"state_dir": str(tmp_b)})
    finally:
        illustrations.target_variants_by_airline = original_target_variants_by_airline
    assert 'class="filter-bar"' not in rendered_neither, (
        "expected no filter bar at all when there is nothing to filter (the no-chrome-with-no-data "
        "gate, CFG-82, 29-02-PLAN.md)")


# ======================================================================
# 19-08-PLAN.md Task 2 (D-21/A-38): the resolve panel's back link now
# names and targets Airlines, not Health.
# ======================================================================


def test_airlines_resolve_panel_back_link_names_and_targets_airlines(tmp_path):
    """the resolve panel's back link renders exactly once, named "← Back to Airlines" and
    targeting airlines_page.AIRLINES_ROUTE, superseding the Phase 13 Copy Deck's "Back to
    Health" (D-21, A-38, 19-08-PLAN.md Task 2)"""
    rendered = airlines_page.render({"state_dir": str(tmp_path), "resolve_prefix": "XYZ"})
    matches = re.findall(
        r'<a class="text-label" href="([^"]*)">%s</a>' % re.escape(airlines_page.RESOLVE_BACK_LINK_TEXT),
        rendered)
    assert len(matches) == 1, "expected exactly one resolve-panel back link, found %d" % (len(matches),)
    assert matches[0] == airlines_page.AIRLINES_ROUTE


# ======================================================================
# 29-01-PLAN.md (CFG-81): the shared lightbox's replace, upload and
# delete forms all render unconditionally now — the page-wide editing
# mode that used to gate replace/delete behind an exact ?edit=1 is
# deleted outright.
# ======================================================================


def test_airlines_default_render_always_has_the_dialogs_forms():
    """a default airlines_page.render({}) call (no query parameter involved) carries exactly
    one each of the dialog's replace form, delete form and upload zone — the page-wide editing
    mode that used to gate replace/delete behind an exact ?edit=1 is deleted (CFG-81,
    29-01-PLAN.md)"""
    rendered = airlines_page.render({})
    for token in (
            airlines_page.LIGHTBOX_REPLACE_FORM_CLASS,
            airlines_page.LIGHTBOX_DELETE_CLASS,
            airlines_page.RESOLVE_UPLOAD_ZONE_CLASS):
        count = rendered.count('class="%s"' % token)
        assert count == 1, (
            "expected exactly one %r in a default render (no page-wide editing mode gates this "
            "dialog form any more, CFG-81), got %d" % (token, count))


def test_airlines_default_render_step_b_upload_zone_unconditional(tmp_path):
    """a render of a Step-B entry (name saved, no artwork yet) contains exactly two upload
    zones and two manual-delete forms (the no-JS fallback panel's own copy plus the lightbox's,
    both unconditional per CFG-81), and exactly one replace form (the dialog's own copy — this
    no-JS fallback panel has none of its own) (D-19, 21-06-PLAN.md Task 1; retargeted by
    29-01-PLAN.md)"""
    result = manual_resolutions.add_entry(str(tmp_path), "NEW", "Totally Novel Airline")
    assert result == manual_resolutions.ADD_OK, "test setup failure: add_entry returned %r" % (result,)
    rendered = airlines_page.render({"state_dir": str(tmp_path), "resolve_prefix": "NEW"})
    upload_count = rendered.count('class="%s"' % airlines_page.RESOLVE_UPLOAD_ZONE_CLASS)
    assert upload_count == 2, (
        "expected exactly two %r (fallback panel + lightbox) in a Step-B render, got %d"
        % (airlines_page.RESOLVE_UPLOAD_ZONE_CLASS, upload_count))
    delete_count = rendered.count('class="%s"' % airlines_page.LIGHTBOX_DELETE_CLASS)
    assert delete_count == 2, (
        "expected exactly two %r (fallback panel + lightbox) in a Step-B render, got %d"
        % (airlines_page.LIGHTBOX_DELETE_CLASS, delete_count))
    replace_count = rendered.count('class="%s"' % airlines_page.LIGHTBOX_REPLACE_FORM_CLASS)
    assert replace_count == 1, (
        "expected exactly one %r (the dialog's own copy — this no-JS fallback panel has none of "
        "its own) in a Step-B render, got %d" % (airlines_page.LIGHTBOX_REPLACE_FORM_CLASS, replace_count))


def test_airlines_default_render_keeps_exactly_one_resolve_name_form():
    """a default airlines_page.render({}) call still contains exactly one
    lightbox__resolve-name form - naming a prefix stays the everyday action (D-22, 19-08-PLAN.md
    Task 3)"""
    rendered = airlines_page.render({})
    count = rendered.count('class="%s"' % airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS)
    assert count == 1, (
        "expected exactly one %r form in a default render (the everyday naming path), got %d"
        % (airlines_page.LIGHTBOX_RESOLVE_NAME_CLASS, count))


def test_airlines_no_page_wide_editing_mode_survives():
    """the deleted page-wide editing toggle (its class literal) and the deleted ?edit= query
    parameter (its literal form) never render again, in either language, whether the query
    string is absent or carries an arbitrary unrelated value (CFG-81, 29-01-PLAN.md)"""
    try:
        for lang in ("en", "fr"):
            prefs.set_request_prefs(lang=lang)
            for rendered in (
                    airlines_page.render({}),
                    airlines_page.render({"resolve_prefix": "not-a-real-prefix"})):
                assert 'class="airlines-edit-toggle"' not in rendered, (
                    "expected no airlines-edit-toggle anchor to ever render again (lang=%r)" % (lang,))
                assert "?edit=" not in rendered, (
                    "expected no ?edit= query literal to ever render again (lang=%r)" % (lang,))
    finally:
        prefs.set_request_prefs(lang="en")


# ======================================================================
# 20-10-PLAN.md Task 2 (D-05): the rest of Airlines through i18n.t(),
# with companion/i18n_fr/airlines.py's own French catalogue.
# ======================================================================


def test_airlines_french_render_translates_headings_not_data():
    """a French render of Airlines shows the French page title, filter label and lightbox
    aria-label, while a real airline name ('Air France') stays untranslated data (D-05,
    20-10-PLAN.md Task 2; the toggle-text needle retired by 29-01-PLAN.md/CFG-81)"""
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = airlines_page.render({})
    finally:
        prefs.set_request_prefs(lang="en")
    for needle in (">Compagnies<", "Filtrer par compagnie ou indicatif", "Illustration de la compagnie"):
        assert needle in rendered, "expected the French %r in a French Airlines render" % (needle,)
    assert "Air France" in rendered, "expected the seeded/curated airline name 'Air France' to stay untranslated data"


def test_airlines_full_seeded_render_french_end_to_end(tmp_path):
    """a fully-seeded Airlines render under lang='fr' shows the French gap-strip
    heading/sentence and resolve-panel copy with no English leaking in, the seeded example
    callsign stays untranslated data, and the identical seeded render under the default
    language still carries every pre-existing English needle (D-05, 20-10-PLAN.md Task 2; the
    toggle-label needle retired by 29-01-PLAN.md/CFG-81)"""
    import companion.i18n_fr.airlines as i18n_fr_airlines

    vp.seed_unresolved_prefixes(tmp_path, {
        "XYZ": {
            "count": 5, "first_seen": "2026-01-01T00:00:00+00:00",
            "last_seen": "2026-01-02T00:00:00+00:00", "example_callsign": "XYZ123",
        },
    })
    try:
        prefs.set_request_prefs(lang="fr")
        rendered_fr = airlines_page.render({"state_dir": str(tmp_path)})
        resolve_fr = airlines_page.render({"state_dir": str(tmp_path), "resolve_prefix": "XYZ"})
    finally:
        prefs.set_request_prefs(lang="en")
    # 29-06-PLAN.md Task 2 (CFG-79): the needle names the CURRENT French
    # translation via the module's own CATALOG lookup, never a hand-typed
    # literal that would silently go stale on the next edit.
    for needle in (">Compagnies<", "Compagnies non identifiées",
                   i18n_fr_airlines.CATALOG[airlines_page.GAP_STRIP_BODY]):
        assert needle in rendered_fr, "expected the French %r in the French Airlines render" % (needle,)
    for needle in ("Identifier un vol non reconnu", "Nom de la compagnie",
                   "Enregistrer le nom de la compagnie"):
        assert needle in resolve_fr, "expected the French %r in the French resolve-panel render" % (needle,)
    assert "XYZ123" in rendered_fr or "XYZ123" in resolve_fr, (
        "expected the seeded example callsign to stay untranslated data")

    rendered_en = airlines_page.render({"state_dir": str(tmp_path)})
    for needle in ('<h1 class="page-title">Airlines</h1>', airlines_page.GAP_STRIP_HEADING,
                   airlines_page.GAP_STRIP_BODY):
        assert needle in rendered_en, "expected the English %r in the default-language Airlines render" % (needle,)


def test_airlines_catalog_keys_all_present_in_merged_catalog():
    """every key in companion/i18n_fr/airlines.py's own CATALOG is also a key of the merged
    companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up
    (20-10-PLAN.md Task 2)"""
    import companion.i18n_fr as i18n_fr
    import companion.i18n_fr.airlines as i18n_fr_airlines

    missing = [k for k in i18n_fr_airlines.CATALOG if k not in i18n_fr.CATALOG]
    assert not missing, "keys missing from the merged CATALOG: %r" % (missing,)


# ======================================================================
# 22-11-PLAN.md Task 1 (D-05, B5): the resolve dialog reads in Paris
# local time.
# ======================================================================


def test_resolve_dialog_seen_attributes_carry_formatted_paris_local_text(tmp_path):
    """the resolve dialog's data-view-panel-first-seen/-last-seen carry FORMATTED Europe/Paris
    text byte-identical to the no-JS path's own rendered <dd> text for the same row (15:49 UTC
    reading 17:49), and neither render carries a single ISO-8601 timestamp anywhere (B5/D-05,
    22-11-PLAN.md Task 1)"""
    now = "2026-09-13T09:00:00+00:00"
    first_seen = "2026-09-09T15:49:27+00:00"
    last_seen = "2026-09-11T06:05:00+00:00"
    vp.seed_unresolved_prefixes(tmp_path, {
        "XYZ": {"count": 7, "first_seen": first_seen, "last_seen": last_seen, "example_callsign": "XYZ123"},
    })
    rendered = airlines_page.render({"state_dir": str(tmp_path), "now": now})
    fallback = airlines_page.render({"state_dir": str(tmp_path), "now": now, "resolve_prefix": "XYZ"})

    attrs = {}
    for name, attr in (("first", airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR),
                       ("last", airlines_page._VIEW_PANEL_LAST_SEEN_ATTR)):
        values = [v for v in re.findall(r'%s="([^"]*)"' % re.escape(attr), rendered) if v]
        assert len(values) == 1, (
            "expected exactly one non-empty %s attribute for the one seeded gap, found %r" % (attr, values))
        attrs[name] = html.unescape(values[0])

    texts = {}
    for name, dd_class in (("first", "resolve-context__first-seen"), ("last", "resolve-context__last-seen")):
        bodies = [b for b in re.findall(
            r'<dd class="%s[^"]*"[^>]*>(.*?)</dd>' % dd_class, fallback, re.S) if b.strip()]
        assert len(bodies) == 1, (
            "expected exactly one populated %s <dd> in the no-JS fallback, found %r" % (dd_class, bodies))
        texts[name] = html.unescape(re.sub(r"<[^>]*>", "", bodies[0]))

    for name in ("first", "last"):
        assert attrs[name] == texts[name], (
            "expected the JS path's %s-seen attribute to equal the no-JS path's rendered text "
            "byte for byte, got %r and %r" % (name, attrs[name], texts[name]))
        assert not _ISO_INSTANT_RE.search(attrs[name]), (
            "expected no raw ISO-8601 in the %s-seen attribute, got %r" % (name, attrs[name]))
    # D-05's "Paris local time everywhere": 15:49 UTC is 17:49 in Paris on
    # that date, so an unconverted value would still read "15:49" here
    # and pass every shape check above.
    assert "17:49" in attrs["first"], (
        "expected the 15:49 UTC sighting to render as 17:49 Europe/Paris, got %r" % (attrs["first"],))
    # 23-03-PLAN.md Task 1 (D14/CFG-34): with ONE exemption, stated rather
    # than silently widened - layout.relative_time_html()'s <time
    # datetime="..." data-relative> element carries a machine-readable
    # instant in the attribute HTML defines for exactly that purpose.
    for label, page in (("gallery", rendered), ("resolve fallback", fallback)):
        page = re.sub(r'<time datetime="[^"]*" data-relative>', "<time data-relative>", page)
        leaks = _ISO_INSTANT_RE.findall(page)
        assert not leaks, "expected zero ISO-8601 timestamps in the %s render, found %r" % (label, leaks)
