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
import re

import pytest

import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
import companion.test_view_pages_helpers as vp
from companion.pages import history_page
from companion_app_server import served_asset, served_stylesheet
from companion_markup import declarations_for, parse_html
from server import device_config


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
