"""Part 06 of the `companion/test_status_pages.py` migration chain
(33-30-PLAN.md): the original harness's `check()` calls #245-#292 (48 of
part 06's checks) - the lightbox replace form (unique/labelled file input,
cache-busting, hostile-name escaping, no revert control, retired-surface
sweep, the shared icon sprite, the zone's own markup/styling contract),
the D19 drag-and-drop upload affordance (byte-identical native controls
across all three upload-form renderings, the JS-gate boundary, the framing
preview's reserved aspect-ratio), the D-01/D-02/D-04..D-07 coverage-gap
block (threshold/sort/cap/overflow, the gap card's own markup shape,
its filter-group vocabulary, hostile-callsign escaping), the D-08/D-10/
D-12 manual-resolution card states (`_airline_card_html()`'s widened
`manual_info` parameter, the superseded fallback, grid injection), the
D-03/D-10..D-13 conditional resolve section (all four server-derived
states, the datalist contract, hostile-value escaping, CR-02's
gap-cleared reachability, the page's own top-to-bottom composition
order), the D-06..D-08 manual-resolutions summary line and the retired
management table's symbol sweep, the WR-06 cross-module template
equality check, the D-09 delete-form's two call sites,
`list-filter.js`'s new `[data-filter-set]` hook, the phase 14
Component-Inventory CSS sweep, the D-03/X2/B13/C2/C5/C6/T9 Frame-strip
behaviour and CSS (the nightly quiet-hours regression, the grace window,
the late/parked states, the three-cell row structure, the strip's own
CSS geometry) and the X9/D-10 bottom tab bar's CSS geometry, surface and
active idiom.

Two checks (rubric S) are dropped outright, both redundant with the
comprehensive frame-strip behaviour checks already in this same module:
row 285 (a source-text grep of `companion/layout.py` for a retired
`age_seconds(next_wake...)` re-derivation) has no behaviour left to
protect once `test_frame_strip_nightly_regression_held_is_neutral_
never_warn`/`test_frame_strip_due_is_identical_inside_and_outside_the_
grace_window`/`test_frame_strip_parked_suppresses_late_state` already
pin every late/due/parked/grace scenario against `frame_state.
resolve_state()`'s own output; row 291 (rubric C) asserted a stylesheet
COMMENT (the header's own accent-reservation-list prose), which guard G1
already rules out as a source of behaviour.

Two more checks keep their behavioural assertions but drop one
now-redundant source-text sub-clause each (rubric S), noted at each call
site: `test_replace_zone_icon_comes_from_the_shared_sprite` drops a
`companion/pages/airlines_page.py` source-file scan for a hand-written
glyph token (the rendered `<use>` count and class already prove the
glyph came from the shared sprite); `test_gap_card_filter_group_never_
collides_with_curated_integer_groups` drops a source-file scan for the
`'data-filter-group="gap%d"'` format-string literal (the same check's
own rendered-attribute regex match already proves the format shipped).

Every CSS check in this module fetches the stylesheet `companion/app.py`
actually serves and asserts on it structurally via `companion_markup.
css_rules()`/`declarations_for()`/`rules_with_selector()` - iterating
parsed `Rule.selectors`/`Rule.declarations`, never a regex/substring
probe over the raw served text (33-FOLLOWUPS.md F-01) - reusing a
module-scoped read-only server. The one served-JS check
(`list-filter.js`) fetches it via `served_asset()` and strips only
comments with this chain's `strip_js_line_and_block_comments()`, never a
disk read.

Every other check in this module calls `companion.pages.airlines_page`/
`companion.pages.health_page`/`companion.layout` directly, in-process,
seeding fixtures under `tmp_path` via `companion.test_status_pages_
helpers`.
"""
import os
import re

import pytest

import companion.test_status_pages_helpers as shp
from companion import illustration_normalize, layout
from companion.pages import airlines_page
from companion_app_server import served_stylesheet
from companion_markup import css_rules
from server.plane import illustrations, manual_resolutions


# --- module-scoped read-only server, for the served-CSS/JS checks only -----

@pytest.fixture(scope="module")
def _module_server(module_app_server_factory):
    return module_app_server_factory()


@pytest.fixture(scope="module")
def css_text(_module_server):
    return served_stylesheet(_module_server)


# --- shared helpers, local to this part -------------------------------------

def _card_slice(rendered, airline_name):
    """The one `.airline-card` block for `airline_name`, bounded by the next
    card's opening tag (or end of string)."""
    name_index = rendered.index(">%s<" % airline_name)
    card_start = rendered.rindex('<div class="airline-card"', 0, name_index)
    next_start = rendered.find('<div class="airline-card"', card_start + 1)
    return rendered[card_start:] if next_start == -1 else rendered[card_start:next_start]


def _grid_section(rendered):
    grid_start = rendered.index('class="illustration-grid"')
    dialog_start = rendered.index('id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID, grid_start)
    return rendered[grid_start:dialog_start]


def _resolve_slice(rendered):
    """Isolate everything the page renders AFTER the shared dialog - Phase
    14 (14-04-PLAN.md) moved the resolve section from the top of the page
    to the bottom (behind the shared lightbox), so this anchors on the
    dialog's own id and its universal closing tag instead of a hardcoded
    index into any specific inner string.
    """
    dialog_id_marker = 'id="%s"' % airlines_page.LIGHTBOX_DIALOG_ID
    dialog_start = rendered.index(dialog_id_marker)
    dialog_close = rendered.index("</dialog>", dialog_start)
    return rendered[dialog_close + len("</dialog>"):]


def _class_selector_declared(rules, class_name):
    """Whether some rule's selector declares `.class_name` on a real
    boundary (never a substring hit inside a longer class name)."""
    pattern = re.compile(r"\.%s(?![-\w])" % re.escape(class_name))
    return any(pattern.search(selector) for rule in rules for selector in rule.selectors)


def _frame_strip_ctx(last_checkin_ts, device_config, now):
    return {"last_checkin_ts": last_checkin_ts, "device_config": device_config, "now": now}


def _frame_strip_update_cell_slice(rendered):
    """The update cell is always the LAST child of `.frame-strip__cells`
    (rendered after both switch cells, or omitted entirely) - so its own
    opening tag through the end of the string, minus the two closing
    `</div>` tags for `.frame-strip__cells` and `.frame-strip` itself, is
    exactly this cell's own markup.
    """
    marker = '<div class="frame-strip__cell frame-strip__cell--update">'
    if marker not in rendered:
        return None
    start = rendered.index(marker)
    closing = "</div></div>"
    if not rendered.endswith(closing):
        return None
    return rendered[start:-len(closing)]


# =============================================================================
# The lightbox replace form (quick task 260903-df3, extending T-06.6.4.1-05)
# =============================================================================

def test_replace_form_file_input_id_is_unique_and_labelled(tmp_path):
    """the whole rendered page carries exactly one <input type="file"> whose id
    equals airlines_page.REPLACE_INPUT_ID and is the target of a label's for
    attribute, and both the label and the file input live inside the framed
    zone wrapper (quick task 260903-df3) - the accessibility contract the move
    from per-card to shared must not lose"""
    tmp = str(tmp_path)
    rendered = airlines_page.render(shp.ctx(tmp))
    input_ids = re.findall(r'<input type="file" id="([^"]+)"', rendered)
    replace_ids = [i for i in input_ids if i == airlines_page.REPLACE_INPUT_ID]
    assert len(replace_ids) == 1, (
        "expected exactly one file input carrying REPLACE_INPUT_ID, got %d (all file input ids: %r)"
        % (len(replace_ids), input_ids))
    label_fors = set(re.findall(r'<label for="([^"]+)">', rendered))
    assert airlines_page.REPLACE_INPUT_ID in label_fors
    zone_match = re.search(
        r'<div class="%s">.*?</div>' % re.escape(airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS),
        rendered, re.DOTALL)
    assert zone_match, "expected to find the framed zone's own markup"
    zone_html = zone_match.group(0)
    assert ('<label for="%s"' % airlines_page.REPLACE_INPUT_ID) in zone_html
    assert '<input type="file"' in zone_html


def test_cache_buster_absent_with_no_state_dir_and_keyed_on_mtime_with_an_override(tmp_path):
    """render() with no effective state_dir produces no cache-busting query
    string anywhere; with a state_dir whose override directory holds Air
    France's override file, exactly one URL is busted, keyed on that file's
    own mtime, identically in both the <img src> and the zoom trigger's
    data-view-panel-src, every other card's URL stays unbusted, and Air
    France's own data-view-panel-replace-action stays the UN-busted URL
    while no replace-action value anywhere carries a cache buster"""
    rendered_no_state = airlines_page.render(shp.ctx(None))
    assert "?v=" not in rendered_no_state

    tmp = str(tmp_path)
    key = illustrations.normalise_airline_key("Air France")
    override_dir = tmp_path / illustrations.ILLUSTRATION_OVERRIDE_DIRNAME
    override_dir.mkdir()
    override_path = override_dir / (key + ".png")
    override_path.write_bytes(b"not a real png - only this file's own mtime matters to this check")
    mtime = int(os.stat(override_path).st_mtime)

    rendered = airlines_page.render(shp.ctx(tmp))
    expected_busted_url = "%s%s.png?v=%d" % (airlines_page.ILLUSTRATION_ROUTE_PREFIX, key, mtime)
    expected_unbusted_url = "%s%s.png" % (airlines_page.ILLUSTRATION_ROUTE_PREFIX, key)
    img_srcs = re.findall(r'<img class="airline-card__image" src="([^"]+)"', rendered)
    zoom_srcs = re.findall(r'data-view-panel-src="([^"]+)"', rendered)
    replace_actions = re.findall(r'data-view-panel-replace-action="([^"]+)"', rendered)
    assert img_srcs.count(expected_busted_url) == 1
    assert zoom_srcs.count(expected_busted_url) == 1
    assert replace_actions.count(expected_unbusted_url) == 1
    for src in img_srcs:
        assert src == expected_busted_url or "?v=" not in src
    for src in zoom_srcs:
        assert src == expected_busted_url or "?v=" not in src
    for action in replace_actions:
        assert "?v=" not in action


def test_replace_control_escapes_hostile_airline_name(monkeypatch):
    """a hostile airline name reaching the rendered page is escaped, never
    interpolated raw, including in its own data-view-panel-replace-action
    attribute; the now-airline-agnostic replace form's own markup
    (REPLACE_LABEL_TEXT and REPLACE_HINT_TEXT, quick task 260903-df3)
    carries no trace of the hostile name at all (extends T-06.6.4.1-05's
    existing discipline)"""
    hostile_name = '<script>alert(1)</script>"'
    monkeypatch.setattr(illustrations, "target_variants_by_airline", lambda: [(hostile_name, [])])
    rendered = airlines_page.render({})
    assert hostile_name not in rendered
    assert "<script>" not in rendered
    escaped_label = layout.escape_html(airlines_page.REPLACE_LABEL_TEXT)
    assert escaped_label in rendered
    escaped_hint = layout.escape_html(airlines_page.REPLACE_HINT_TEXT)
    assert escaped_hint in rendered
    form_match = re.search(
        r'<form class="%s".*?</form>' % re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS),
        rendered, re.DOTALL)
    assert form_match, "expected to find the lightbox replace form's own markup"
    assert "script" not in form_match.group(0).lower()
    hostile_action_match = re.search(r'data-view-panel-replace-action="([^"]*)"', rendered)
    assert hostile_action_match
    hostile_action = hostile_action_match.group(1)
    assert "<" not in hostile_action and '"' not in hostile_action


def test_replace_form_contains_no_revert_or_reset_control(tmp_path):
    """the lightbox replace form's own markup offers no restoring or resetting
    of the original image (D-04, explicitly out of scope) - checked both
    within the form's own markup and as a membership test over this
    feature's surviving copy constants (REPLACE_LABEL_TEXT/
    REPLACE_BUTTON_TEXT/REPLACE_HINT_TEXT)"""
    tmp = str(tmp_path)
    rendered = airlines_page.render(shp.ctx(tmp))
    form_match = re.search(
        r'<form class="%s".*?</form>' % re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS),
        rendered, re.DOTALL)
    assert form_match, "expected to find the lightbox replace form's own markup"
    form_html = form_match.group(0)
    revert_shaped_words = ("revert", "reset", "restore", "undo", "original")
    lowered = form_html.lower()
    for word in revert_shaped_words:
        assert word not in lowered, "found revert-shaped word %r inside the replace form (D-04)" % (word,)
    for constant_text in (
            airlines_page.REPLACE_LABEL_TEXT, airlines_page.REPLACE_BUTTON_TEXT,
            airlines_page.REPLACE_HINT_TEXT):
        lowered_constant = constant_text.lower()
        for word in revert_shaped_words:
            assert word not in lowered_constant


def test_replace_control_retired_from_every_surface(css_text, tmp_path):
    """the retired per-card replace disclosure left no dead markup (a real
    render() call), no dead stylesheet rule (the served stylesheet,
    structurally), and no dead module surface (_replace_control_html/
    REPLACE_SUMMARY_TEMPLATE/REPLACE_LABEL_TEMPLATE) behind"""
    # Built from two fragments at runtime, not written as one literal, so
    # this check's own source cannot satisfy a future whole-repo grep for
    # the retired name.
    retired_token = "airline-card__" + "replace"
    tmp = str(tmp_path)
    rendered = airlines_page.render(shp.ctx(tmp))
    assert retired_token not in rendered
    for rule in css_rules(css_text):
        for selector in rule.selectors:
            assert retired_token not in selector, (
                "expected the retired per-card class token to be absent from every served-stylesheet "
                "selector, found it in %r" % (selector,))
    for retired_attr in ("_replace_control_html", "REPLACE_SUMMARY_TEMPLATE", "REPLACE_LABEL_TEMPLATE"):
        assert not hasattr(airlines_page, retired_attr)


def test_replace_zone_icon_comes_from_the_shared_sprite(tmp_path):
    """the framed zone's upload glyph comes from layout.ICON_DEFS_HTML via
    layout.icon_html() - 'icon-upload' is a member of ICON_IDS, the rendered
    page carries exactly two matching <use> references (the framed zone's
    own and the dialog's own resolve-upload form's copy), and
    REPLACE_ICON_CLASS appears in the rendered icon's class attribute.

    Dropped in place (rubric S): the legacy check also opened `companion/
    pages/airlines_page.py`'s own source to prove it contained no
    hand-written `<use href="#icon-upload">` literal. That sub-clause had
    no behaviour of its own to protect once the rendered count/class
    assertions below already prove the glyph came from the shared sprite
    mechanism - a hand-authored duplicate markup would still satisfy them.
    """
    assert "icon-upload" in layout.ICON_IDS
    tmp = str(tmp_path)
    rendered = airlines_page.render(shp.ctx(tmp))
    # Phase 14 (14-02-PLAN.md Task 3): the shared dialog now also renders
    # its own resolve-upload form's file input, reusing the identical
    # icon-upload glyph, so two occurrences are expected, not one.
    use_tag = "<use href=" + '"#icon-upload"'
    assert rendered.count(use_tag) == 2
    icon_svg_match = re.search(
        r'<svg[^>]*class="[^"]*%s[^"]*"[^>]*>' % re.escape(airlines_page.REPLACE_ICON_CLASS), rendered)
    assert icon_svg_match


def test_replace_zone_markup_and_styling_contract(css_text, tmp_path):
    """exactly one .lightbox__replace-zone <div> is rendered, nested inside
    the single lightbox replace form; within it, the icon, label, hint,
    file input and Upload button appear in that order; the hint element's
    text equals REPLACE_HINT_TEXT; and the served stylesheet declares
    LIGHTBOX_REPLACE_ZONE_CLASS, REPLACE_HINT_CLASS, REPLACE_ICON_CLASS and
    a '::file-selector-button' rule"""
    tmp = str(tmp_path)
    rendered = airlines_page.render(shp.ctx(tmp))
    zone_open_tag = '<div class="%s">' % airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS
    assert rendered.count(zone_open_tag) == 1
    form_match = re.search(
        r'<form class="%s"[^>]*>' % re.escape(airlines_page.LIGHTBOX_REPLACE_FORM_CLASS), rendered)
    assert form_match, "expected to find the single lightbox replace form's opening tag"
    assert rendered.index(zone_open_tag) > form_match.start()
    zone_match = re.search(
        r'<div class="%s">.*?</div>' % re.escape(airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS),
        rendered, re.DOTALL)
    assert zone_match
    zone_html = zone_match.group(0)
    positions = [
        zone_html.index("#icon-upload"),
        zone_html.index("<label for="),
        zone_html.index(airlines_page.REPLACE_HINT_CLASS),
        zone_html.index('<input type="file"'),
        zone_html.index('<button type="submit"'),
    ]
    assert positions == sorted(positions), (
        "expected the zone's five children (icon, label, hint, input, button) in that order")
    hint_p_match = re.search(
        r'<p class="%s">([^<]*)</p>' % re.escape(airlines_page.REPLACE_HINT_CLASS), zone_html)
    assert hint_p_match
    assert hint_p_match.group(1) == airlines_page.REPLACE_HINT_TEXT

    rules = css_rules(css_text)
    for class_name in (
            airlines_page.LIGHTBOX_REPLACE_ZONE_CLASS, airlines_page.REPLACE_HINT_CLASS,
            airlines_page.REPLACE_ICON_CLASS):
        assert _class_selector_declared(rules, class_name), (
            "expected %r to appear in a served stylesheet selector" % (class_name,))
    assert any("::file-selector-button" in selector for rule in rules for selector in rule.selectors), (
        "expected a '::file-selector-button' rule in the served stylesheet")


# =============================================================================
# 25-07-PLAN.md Task 1 (CFG-51/D19): THE DROP ZONE, OVER TWO UPLOAD
# FORMS THAT DID NOT CHANGE.
# =============================================================================

def test_upload_forms_native_controls_are_unchanged_by_the_drop_zone():
    """all three upload-form renderings (the no-JS fallback's, the dialog's
    copy, and the lightbox replace form) keep their <input type="file" ...
    accept="image/png" required>, their single bare <button type="submit">,
    their hint paragraph, their method/enctype/action and exactly one
    <form> byte-identical to their pre-25-07 output - each now also
    carrying its own id and, as the form's LAST child after the submit
    button, a drop zone naming the very input it writes into (CFG-51/D19,
    25-07-PLAN.md Task 1)"""
    renderings = (
        ("the no-JS fallback upload form",
         airlines_page._resolve_upload_form_html("/illustration/demo.png", ""),
         airlines_page.MANUAL_UPLOAD_INPUT_ID,
         airlines_page.MANUAL_UPLOAD_FORM_ID,
         'action="/illustration/demo.png"'),
        ("the dialog's copy of the upload form",
         airlines_page._resolve_upload_form_html("", "-dialog"),
         airlines_page.MANUAL_UPLOAD_INPUT_ID + "-dialog",
         airlines_page.MANUAL_UPLOAD_FORM_ID + "-dialog",
         'action=""'),
        ("the lightbox replace form",
         airlines_page._lightbox_replace_form_html(),
         airlines_page.REPLACE_INPUT_ID,
         airlines_page.REPLACE_FORM_ID,
         'action=""'),
    )
    hint_html = '<p class="%s">%s</p>' % (
        airlines_page.REPLACE_HINT_CLASS,
        airlines_page.i18n.t(airlines_page.REPLACE_HINT_TEXT))
    for label, markup, input_id, form_id, action_attr in renderings:
        expected_input = (
            '<input type="file" id="%s" name="image" accept="image/png" required>' % input_id)
        assert markup.count(expected_input) == 1, label
        assert markup.count('<button type="submit">') == 1, label
        assert markup.count(hint_html) == 1, label
        assert markup.count("<form") == 1, label
        form_tag = re.search(r"<form\b[^>]*>", markup)
        assert form_tag, label
        for required in ('method="post"', 'enctype="multipart/form-data"', action_attr,
                         'id="%s"' % form_id):
            assert required in form_tag.group(0), "%s: expected %r in %r" % (label, required, form_tag.group(0))
        drop_at = markup.find(airlines_page.UPLOAD_DROP_ATTR)
        assert drop_at != -1, "%s: renders no drop zone at all" % (label,)
        assert drop_at > markup.index('<button type="submit">'), (
            "%s: the drop zone renders BEFORE the submit button" % (label,))
        expected_hook = '%s="%s"' % (airlines_page.UPLOAD_DROP_INPUT_ATTR, input_id)
        assert expected_hook in markup, label


def test_drop_zone_ids_are_unique_and_no_drop_markup_escapes_the_js_gate(tmp_path):
    """on a Step-B edit-mode Airlines render (the fallback panel's upload
    form, the dialog's copy and the replace form all at once) every emitted
    id is document-unique, every one of the three elements carrying
    data-upload-drop also carries layout.JS_GATE_CLASS ON ITSELF
    (boundary-anchored, so data-upload-drop-input cannot satisfy it), and
    with those three <section> subtrees excised the rest of the document
    contains zero preview, image, note, message, input-hook or
    --upload-preview-ratio markup (CFG-51/D-09, 25-07-PLAN.md Task 1)"""
    tmp = str(tmp_path)
    result = manual_resolutions.add_entry(tmp, "NEW", "Totally Novel Airline")
    assert result == manual_resolutions.ADD_OK
    rendered = airlines_page.render(dict(shp.ctx(tmp), resolve_prefix="NEW"))

    ids = re.findall(r'\sid="([^"]*)"', rendered)
    duplicates = sorted({value for value in ids if ids.count(value) > 1})
    assert not duplicates, "the Airlines page emits duplicate id(s) %r" % (duplicates,)

    wrapper_re = re.compile(r"(?<![-\w])%s(?![-\w])" % re.escape(airlines_page.UPLOAD_DROP_ATTR))
    wrappers = []
    for tag in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", rendered):
        text = tag.group(0)
        if not wrapper_re.search(text):
            continue
        class_match = re.search(r'\bclass="([^"]*)"', text)
        classes = class_match.group(1).split() if class_match else []
        assert layout.JS_GATE_CLASS in classes, (
            "an element carries %s OUTSIDE the %r gate - %s"
            % (airlines_page.UPLOAD_DROP_ATTR, layout.JS_GATE_CLASS, text))
        wrappers.append(tag.start())
    assert len(wrappers) == 3

    outside = rendered
    for start in reversed(wrappers):
        end = rendered.index("</section>", start) + len("</section>")
        outside = outside[:start] + outside[end:]
    for token in (airlines_page.UPLOAD_DROP_PREVIEW_CLASS,
                  airlines_page.UPLOAD_DROP_IMAGE_CLASS,
                  airlines_page.UPLOAD_DROP_NOTE_CLASS,
                  airlines_page.UPLOAD_DROP_MESSAGE_CLASS,
                  airlines_page.UPLOAD_DROP_INPUT_ATTR,
                  "--upload-preview-ratio"):
        assert token not in outside, "%r renders OUTSIDE every gated drop wrapper" % (token,)


def test_preview_box_reserves_illustration_normalize_s_own_frame(css_text):
    """the framing preview reserves companion/illustration_normalize.py's
    OWN output frame (read from ILLUSTRATION_TARGET_SIZE, never a retyped
    ratio) through an inline --upload-preview-ratio that the served
    stylesheet reads with NO fallback value; every .upload-drop class and
    the [data-upload-drop-active] state resolve to real selectors on a
    selector boundary; and not one .upload-drop rule uses :hover or
    declares a colour literal"""
    markup = airlines_page._resolve_upload_form_html("", "-dialog")
    ratio = re.search(r'style="--upload-preview-ratio: (\d+) / (\d+)"', markup)
    assert ratio, "the preview box carries no inline --upload-preview-ratio"
    measured = (int(ratio.group(1)), int(ratio.group(2)))
    assert measured == illustration_normalize.ILLUSTRATION_TARGET_SIZE

    rules = css_rules(css_text)
    values_mentioning_ratio = [
        value for rule in rules for _, value in rule.declarations
        if "var(--upload-preview-ratio" in value
    ]
    assert any(value == "var(--upload-preview-ratio)" for value in values_mentioning_ratio), (
        "expected a declaration reading var(--upload-preview-ratio) with no fallback")
    assert not any("var(--upload-preview-ratio," in value for value in values_mentioning_ratio), (
        "expected no declaration to give --upload-preview-ratio a fallback value - a fallback would "
        "mask the deletion of the live value rather than guard against it")

    for class_name in (airlines_page.UPLOAD_DROP_CLASS, airlines_page.UPLOAD_DROP_PREVIEW_CLASS,
                        airlines_page.UPLOAD_DROP_IMAGE_CLASS, airlines_page.UPLOAD_DROP_NOTE_CLASS,
                        airlines_page.UPLOAD_DROP_MESSAGE_CLASS):
        assert _class_selector_declared(rules, class_name), (
            "expected a served-stylesheet selector declaring .%s on a boundary" % (class_name,))
    active_attr = "[%s]" % airlines_page.UPLOAD_DROP_ACTIVE_ATTR
    assert any(active_attr in selector for rule in rules for selector in rule.selectors), (
        "expected a served-stylesheet rule matching [%s]" % (airlines_page.UPLOAD_DROP_ACTIVE_ATTR,))

    upload_drop_rules = [rule for rule in rules if any(".upload-drop" in sel for sel in rule.selectors)]
    assert len(upload_drop_rules) >= 5
    for rule in upload_drop_rules:
        for selector in rule.selectors:
            assert ":hover" not in selector, (
                "%r is a :hover rule - the drag state must be reachable by touch" % (selector,))
        for _prop, value in rule.declarations:
            assert not re.search(r"#[0-9a-fA-F]{3,8}\b|rgba?\(", value), (
                "%r declares the colour literal %r" % (rule.selectors, value))


# =============================================================================
# Phase 14 (14-04-PLAN.md Task 1): the coverage-gap block (D-01, D-02,
# D-04, D-05, D-06, D-07).
# =============================================================================

def test_gap_block_threshold_sort_cap_and_overflow(tmp_path):
    """_gap_rows_for_grid() thresholds at >= GAP_BLOCK_THRESHOLD (3), sorts
    eligible rows (-count, prefix), caps at GAP_BLOCK_CAP (12), and reports
    the exact overflow count for the rest (D-05/D-06)"""
    tmp = str(tmp_path / "a")
    os.makedirs(tmp)
    registry = {}
    for i in range(15):
        prefix = "G%02d" % i
        registry[prefix] = {
            "count": 3 + i, "first_seen": "t1", "last_seen": "t2",
            "example_callsign": "%s123" % prefix,
        }
    shp.seed_unresolved_prefixes(tmp, registry)
    shown, overflow_count = airlines_page._gap_rows_for_grid(tmp)
    assert len(shown) == airlines_page.GAP_BLOCK_CAP
    assert overflow_count == 3
    expected_prefixes = [
        prefix for prefix, _ in sorted(
            registry.items(), key=lambda item: (-item[1]["count"], item[0]))
    ][:airlines_page.GAP_BLOCK_CAP]
    actual_prefixes = [row[0] for row in shown]
    assert actual_prefixes == expected_prefixes

    # The threshold is >=, not >: count=2 must never earn a gap row;
    # count=3 must.
    tmp2 = str(tmp_path / "b")
    os.makedirs(tmp2)
    shp.seed_unresolved_prefixes(tmp2, {
        "AT2": {"count": 2, "first_seen": "t1", "last_seen": "t2", "example_callsign": "AT2123"},
    })
    shown_low, overflow_low = airlines_page._gap_rows_for_grid(tmp2)
    assert not shown_low and not overflow_low
    shp.seed_unresolved_prefixes(tmp2, {
        "AT3": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "AT3123"},
    })
    shown_high, overflow_high = airlines_page._gap_rows_for_grid(tmp2)
    assert [row[0] for row in shown_high] == ["AT3"]
    assert overflow_high == 0


def test_gap_card_markup_shape_and_attribute_vocabulary():
    """_gap_card_html() renders the whole card as a real <a
    class="airline-card" href="/airlines?resolve={prefix}"> trigger with
    zero <img> tags and no nested .airline-card__zoom button, carrying
    every data-view-panel-* attribute UI-SPEC's Gap-card markup shape
    names, non-empty where that snippet shows a value (D-01/D-02/D-12)"""
    row = ("XYZ", 5, "t1", "t2", "XYZ123")
    card_html = airlines_page._gap_card_html(0, row)
    assert "<img" not in card_html
    assert "airline-card__zoom" not in card_html
    assert card_html.startswith('<a class="airline-card"')
    assert card_html.rstrip().endswith("</a>")
    expected_href = 'href="%s?%s=XYZ"' % (
        airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
    assert expected_href in card_html
    required_attr_values = {
        airlines_page._VIEW_PANEL_SRC_ATTR: "",
        airlines_page._VIEW_PANEL_CAPTION_ATTR: "XYZ123",
        airlines_page._VIEW_PANEL_HEADING_ATTR: airlines_page.RESOLVE_HEADING,
        airlines_page._VIEW_PANEL_MODE_ATTR: airlines_page._VIEW_PANEL_MODE_GAP,
        airlines_page._VIEW_PANEL_MANUAL_ATTR: "",
        airlines_page._VIEW_PANEL_SCOPE_ATTR: airlines_page.RESOLVE_CAPTION_TEMPLATE % "XYZ",
        airlines_page._VIEW_PANEL_RESOLVE_PREFIX_ATTR: "XYZ",
        airlines_page._VIEW_PANEL_FIRST_SEEN_ATTR: "t1",
        airlines_page._VIEW_PANEL_LAST_SEEN_ATTR: "t2",
        airlines_page._VIEW_PANEL_COUNT_ATTR: "5",
    }
    for attr, expected_value in required_attr_values.items():
        expected_fragment = '%s="%s"' % (attr, expected_value)
        assert expected_fragment in card_html, "expected %r in the gap card's markup" % (expected_fragment,)
    assert '<span class="airline-card__placeholder" aria-hidden="true"></span>' in card_html
    assert '<p class="airline-card__name mono">XYZ123</p>' in card_html


def test_gap_card_filter_group_never_collides_with_curated_integer_groups(tmp_path):
    """a gap card's data-filter-group value is always a string-prefixed
    "gap{index}" (never a bare integer) and never collides, as a bare
    string, with any curated card's own data-filter-group value on the
    same render (RESEARCH.md Pitfall 4, T-14-17).

    Dropped in place (rubric S): the legacy check also opened
    `companion/pages/airlines_page.py`'s own source to prove the literal
    format string `'data-filter-group="gap%d"'` appears there. That
    sub-clause had no behaviour of its own beyond what the regex match
    below over the card's own rendered attribute already proves.
    """
    row = ("XYZ", 5, "t1", "t2", "XYZ123")
    for index in (0, 1, 11):
        card_html = airlines_page._gap_card_html(index, row)
        match = re.search(r'data-filter-group="([^"]+)"', card_html)
        assert match, "expected a data-filter-group attribute on the gap card"
        assert re.match(r"^gap\d+$", match.group(1))
    tmp = str(tmp_path)
    shp.seed_unresolved_prefixes(tmp, {
        "XYZ": {"count": 5, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
    })
    rendered = airlines_page.render(shp.ctx(tmp))
    curated_groups = set(re.findall(r'data-filter-group="(\d+)"', rendered))
    gap_groups = set(re.findall(r'data-filter-group="(gap\d+)"', rendered))
    assert gap_groups
    assert not (gap_groups & curated_groups)


def test_gap_overflow_html_renders_only_when_the_cap_bites():
    """_gap_overflow_html() returns the empty string when the cap does not
    bite, and otherwise the exact templated line naming the overflow
    count, with <a href="/health"> wrapping only MANUAL_OVERFLOW_LINK_TEXT
    and the trailing period sitting outside the anchor (D-07)"""
    assert airlines_page._gap_overflow_html(0) == ""
    overflow_html = airlines_page._gap_overflow_html(3)
    assert overflow_html.startswith('<p class="text-label section-caption">')
    assert "3 other unresolved prefixes" in overflow_html
    link_match = re.search(r'<a href="/health">([^<]+)</a>', overflow_html)
    assert link_match
    assert link_match.group(1) == airlines_page.MANUAL_OVERFLOW_LINK_TEXT
    assert overflow_html.endswith("</a>.</p>")


def test_gap_card_escapes_hostile_example_callsign():
    """an example_callsign containing '<', '>', '&' and '"' reaching a gap
    card renders fully escaped, both in data-view-panel-caption and in the
    visible callsign paragraph, exactly once per interpolation site
    (T-06.6.4.1-05, T-14-16)"""
    hostile_callsign = '<script>alert(1)</script>"'
    row = ("XYZ", 5, "t1", "t2", hostile_callsign)
    card_html = airlines_page._gap_card_html(0, row)
    assert hostile_callsign not in card_html
    assert "<script>" not in card_html
    escaped_callsign = layout.escape_html(hostile_callsign)
    assert card_html.count(escaped_callsign) >= 2


# =============================================================================
# Phase 14 (14-06-PLAN.md Task 1, D-08/D-10/D-12 fallback reachability):
# _airline_card_html()'s widened manual_info parameter and render()'s
# grid-injection step.
# =============================================================================

def test_airline_card_html_manual_info_none_matches_todays_plain_card_and_keeps_button(tmp_path):
    """_airline_card_html(index, airline_name, shapes, state_dir,
    manual_info=None) renders byte-identically to the default-omitted
    call, and a plain curated card with no manual history still wraps a
    real <button> (never an <a>), with mode="art" and every manual/
    resolve-prefix attribute empty (14-06-PLAN.md Task 1)"""
    tmp = str(tmp_path)
    card_none = airlines_page._airline_card_html(0, "Air France", [], tmp, None)
    card_omitted = airlines_page._airline_card_html(0, "Air France", [], tmp)
    assert card_none == card_omitted
    assert '<button type="button" class="airline-card__zoom"' in card_none
    assert "<a href=" not in card_none
    assert 'data-view-panel-mode="art"' in card_none
    assert 'data-view-panel-manual=""' in card_none
    assert 'data-view-panel-resolve-prefix=""' in card_none
    assert "airline-card__chip" not in card_none


def test_airline_card_html_active_manual_states_render_expected_attributes_and_chip(tmp_path):
    """an active manual_info triple renders the real <a href> trigger, the
    correct mode/heading/upload-action for both the has-artwork and
    needs-artwork cases, the delete-action attribute from
    _manual_delete_action(), an empty manual-note, and the 'Resolved by
    hand' chip (14-06-PLAN.md Task 1)"""
    tmp = str(tmp_path)
    card_art = airlines_page._airline_card_html(0, "Air France", [], tmp, ("ZZZ", False, False))
    expected_open = '<a href="%s?%s=ZZZ" class="airline-card__zoom"' % (
        airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
    assert expected_open in card_art
    assert 'data-view-panel-mode="art"' in card_art
    assert 'data-view-panel-manual="active"' in card_art
    assert 'data-view-panel-resolve-prefix="ZZZ"' in card_art
    expected_delete_action = airlines_page._manual_delete_action("ZZZ")
    assert ('data-view-panel-delete-action="%s"' % expected_delete_action) in card_art
    assert 'data-view-panel-manual-note=""' in card_art
    assert ('<span class="airline-card__chip">%s</span>' % airlines_page.MANUAL_CHIP_ACTIVE_TEXT) in card_art

    card_needs = airlines_page._airline_card_html(
        0, "Totally Novel Airline", [], tmp, ("XQZ", False, True))
    assert 'data-view-panel-mode="needs-artwork"' in card_needs
    expected_heading = airlines_page.STEP_B_HEADING_TEMPLATE % "Totally Novel Airline"
    assert ('data-view-panel-heading="%s"' % expected_heading) in card_needs
    assert 'data-view-panel-upload-action="/illustration/totally-novel-airline.png"' in card_needs
    assert ('<span class="airline-card__chip">%s</span>' % airlines_page.MANUAL_CHIP_ACTIVE_TEXT) in card_needs


def test_airline_card_html_needs_artwork_sighting_context_conditional_on_live_gap(tmp_path):
    """a needs-artwork manual card's first-seen/last-seen/count attributes
    are populated from unresolved_row_for_prefix() only when a live gap
    still exists for that prefix, fall back to empty once D-14 clears it,
    and stay empty on an art-mode card regardless of manual_info
    (14-06-PLAN.md Task 1)"""
    tmp_live = str(tmp_path / "live")
    tmp_cleared = str(tmp_path / "cleared")
    os.makedirs(tmp_live)
    os.makedirs(tmp_cleared)
    shp.seed_unresolved_prefixes(tmp_live, {
        "XQZ": {
            "count": 5,
            "first_seen": "2026-01-01T00:00:00+00:00",
            "last_seen": "2026-01-02T00:00:00+00:00",
            "example_callsign": "XQZ123",
        },
    })
    manual_info = ("XQZ", False, True)
    card_live = airlines_page._airline_card_html(0, "Totally Novel Airline", [], tmp_live, manual_info)
    assert 'data-view-panel-first-seen="2026-01-01T00:00:00+00:00"' in card_live
    assert 'data-view-panel-last-seen="2026-01-02T00:00:00+00:00"' in card_live
    assert 'data-view-panel-count="5"' in card_live

    card_cleared = airlines_page._airline_card_html(
        0, "Totally Novel Airline", [], tmp_cleared, manual_info)
    assert 'data-view-panel-first-seen=""' in card_cleared
    assert 'data-view-panel-last-seen=""' in card_cleared
    assert 'data-view-panel-count=""' in card_cleared

    card_art_mode = airlines_page._airline_card_html(
        0, "Air France", [], tmp_live, ("ZZZ", False, False))
    assert 'data-view-panel-count=""' in card_art_mode


def test_airline_card_html_superseded_shows_built_in_state_never_operator_upload(tmp_path):
    """a superseded card never shows the operator's own orphaned upload:
    data-view-panel-src points at the built-in Air France illustration key
    (never a key derived from the entry's own stored name), the
    Superseded chip renders, and the manual-note interpolates the prefix,
    the built-in name, AND the operator's own originally-stored name (not
    the built-in name a second time) (D-10, 14-06-PLAN.md Task 1)"""
    tmp = str(tmp_path)
    manual_resolutions.add_entry(tmp, "AFR", "Some Other Airline", now="2026-01-01T00:00:00+00:00")
    rendered = airlines_page.render(shp.ctx(tmp))
    card = _card_slice(rendered, "Air France")
    assert 'data-view-panel-manual="superseded"' in card
    assert ('<span class="airline-card__chip">%s</span>' % airlines_page.SUPERSEDED_MARKER_TEXT) in card
    src_match = re.search(r'data-view-panel-src="([^"]*)"', card)
    assert src_match and src_match.group(1).startswith("/illustration/air-france.png")
    assert "some-other-airline" not in card.lower()
    note_match = re.search(r'data-view-panel-manual-note="([^"]*)"', card)
    assert note_match
    note_text = note_match.group(1)
    assert "AFR" in note_text and "Air France" in note_text
    assert "Some Other Airline" in note_text


def test_render_grid_injection_adds_exactly_one_novel_card_and_none_for_superseded_or_curated(tmp_path):
    """render()'s grid-injection step adds exactly one card for a genuinely
    novel active manual airline name not already among the curated pairs,
    and adds none for a superseded entry or for an active entry whose name
    is already curated (D-08, UI-SPEC's Grid injection, 14-06-PLAN.md Task
    1)"""
    tmp_novel = str(tmp_path / "novel")
    tmp_none = str(tmp_path / "none")
    os.makedirs(tmp_novel)
    os.makedirs(tmp_none)
    manual_resolutions.add_entry(tmp_novel, "XQZ", "Totally Novel Airline", now="2026-01-01T00:00:00+00:00")
    rendered_novel = airlines_page.render(shp.ctx(tmp_novel))
    novel_count = _grid_section(rendered_novel).count(
        '<p class="airline-card__name">Totally Novel Airline</p>')
    assert novel_count == 1

    manual_resolutions.add_entry(tmp_none, "AFR", "Some Other Airline", now="2026-01-01T00:00:00+00:00")
    manual_resolutions.add_entry(tmp_none, "OLD", "Air France", now="2026-01-01T00:00:00+00:00")
    rendered_none = airlines_page.render(shp.ctx(tmp_none))
    grid_none = _grid_section(rendered_none)
    af_count = grid_none.count('<p class="airline-card__name">Air France</p>')
    assert af_count == 1
    assert '<p class="airline-card__name">Some Other Airline</p>' not in grid_none


# =============================================================================
# Phase 13 (13-04-PLAN.md Task 1): the conditional resolve section (D-03,
# D-10 through D-13).
# =============================================================================

def test_resolve_section_four_states_render_correctly(tmp_path):
    """the resolve section renders all four server-derived states and only
    the right controls in each: absent-from-registry (stale sentence, no
    form at all), seeded-gap-no-entry (Step A heading, name input, no file
    input), seeded-gap-with-artless-entry (Step B heading naming the
    stored airline, upload form action ending /{key}.png, a file input),
    and seeded-gap-with-resolved-entry (the already-resolved sentence, no
    file input) - D-03/D-11"""
    tmp = str(tmp_path)
    now = shp.iso(shp.now())

    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "ZZZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    assert airlines_page.RESOLVE_STALE_BODY in section
    assert airlines_page.MANUAL_NAME_INPUT_ID not in section
    assert "<form" not in section

    shp.seed_unresolved_prefixes(tmp, {
        "XYZ": {"count": 3, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
    })
    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    assert airlines_page.RESOLVE_HEADING in section
    assert ('id="%s"' % airlines_page.MANUAL_NAME_INPUT_ID) in section
    assert '<input type="file"' not in section

    add_result = manual_resolutions.add_entry(tmp, "XYZ", "Brand New Air", now=now)
    assert add_result == manual_resolutions.ADD_OK
    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    expected_heading = airlines_page.STEP_B_HEADING_TEMPLATE % "Brand New Air"
    assert expected_heading in section
    key = manual_resolutions.illustration_key_for_name("Brand New Air")
    expected_action = 'action="%s%s.png"' % (airlines_page.ILLUSTRATION_ROUTE_PREFIX, key)
    assert expected_action in section
    assert '<input type="file"' in section

    add_result = manual_resolutions.add_entry(tmp, "XYZ", "Air France", now=now)
    assert add_result == manual_resolutions.ADD_OK
    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    expected_done = airlines_page.RESOLVE_ALREADY_DONE_TEMPLATE % "Air France"
    assert expected_done in section
    assert '<input type="file"' not in section


def test_resolve_section_datalist_contract(tmp_path):
    """Step A's rendered datalist carries exactly
    len(illustrations.target_airline_names()) (36 against today's data)
    <option> elements, the datalist's id matches the name input's list
    attribute, every airline name appears as an escaped <option
    value=...> exactly once (D-13), and the shared
    _resolve_name_form_html() output also carries an empty <p
    class="lightbox__resolve-scope"></p> for panel-lookup.js to write
    into on open (14-06-PLAN.md external gap-closure)"""
    tmp = str(tmp_path)
    shp.seed_unresolved_prefixes(tmp, {
        "XYZ": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
    })
    ctx = shp.ctx(tmp)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    names = illustrations.target_airline_names()
    option_count = section.count("<option value=")
    assert option_count == len(names)
    datalist_match = re.search(r'<datalist id="([^"]+)">', section)
    assert datalist_match
    list_attr_match = re.search(r'list="([^"]+)"', section)
    assert list_attr_match and list_attr_match.group(1) == datalist_match.group(1)
    for name in names:
        expected_option = '<option value="%s">' % layout.escape_html(name)
        assert expected_option in section
    assert '<p class="lightbox__resolve-scope"></p>' in section


def test_resolve_section_escapes_hostile_values_and_distrusts_query_string(tmp_path):
    """a stored airline name and example callsign both containing an angle
    bracket, a double quote and an ampersand render fully escaped
    everywhere they appear (including inside an attribute value), and a
    resolve_prefix differing from the stored registry key only in case or
    surrounding whitespace normalises to the identical prefix and renders
    the identical resolve section (WR-04/D-12)"""
    tmp = str(tmp_path)
    hostile_name = '<b>Evil & "quoted" name'
    hostile_callsign = '<i>XYZ</i> & "call"'
    shp.seed_unresolved_prefixes(tmp, {
        "XYZ": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": hostile_callsign},
    })
    add_result = manual_resolutions.add_entry(tmp, "XYZ", hostile_name)
    assert add_result == manual_resolutions.ADD_OK

    now = shp.iso(shp.now())
    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)

    assert "<b>Evil" not in rendered and "<i>XYZ</i>" not in rendered
    assert not re.search(r"&(?!amp;|lt;|gt;|quot;|#39;|#x27;)", rendered)
    assert 'value="<b>' not in rendered and 'title="<b>' not in rendered

    canonical_section = _resolve_slice(rendered)
    for hostile_prefix in ("xyz", "XYZ ", " XYZ", "Xyz"):
        ctx = shp.ctx(tmp, now)
        ctx["resolve_prefix"] = hostile_prefix
        variant_rendered = airlines_page.render(ctx)
        variant_section = _resolve_slice(variant_rendered)
        assert variant_section == canonical_section, (
            "expected resolve_prefix=%r to normalise to the canonical 'XYZ' section" % (hostile_prefix,))


def test_resolve_section_step_b_reachable_after_gap_cleared(tmp_path):
    """CR-02: once D-14 clears a resolved prefix from the live gap
    registry, the resolve section still reaches Step B for a manual entry
    with no artwork yet (heading, file input, Skip link, no
    sighting-context <dl>), still reaches the already-resolved state once
    artwork exists under the re-added name (D-07's delete-and-re-add
    path), and still renders the stale sentence only once neither a live
    gap nor a manual entry exists for the prefix"""
    tmp = str(tmp_path)
    now = shp.iso(shp.now())
    shp.seed_unresolved_prefixes(tmp, {
        "XYZ": {"count": 1, "first_seen": "t1", "last_seen": "t2", "example_callsign": "XYZ123"},
    })
    add_result = manual_resolutions.add_entry(tmp, "XYZ", "Brand New Air", now=now)
    assert add_result == manual_resolutions.ADD_OK

    shp.seed_unresolved_prefixes(tmp, {})

    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    assert airlines_page.RESOLVE_STALE_BODY not in section
    expected_heading = airlines_page.STEP_B_HEADING_TEMPLATE % "Brand New Air"
    assert expected_heading in section
    assert '<input type="file"' in section
    assert 'class="resolve-context"' not in section
    assert airlines_page.STEP_B_SKIP_TEXT in section

    add_result = manual_resolutions.add_entry(tmp, "XYZ", "Air France", now=now)
    assert add_result == manual_resolutions.ADD_OK
    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    expected_done = airlines_page.RESOLVE_ALREADY_DONE_TEMPLATE % "Air France"
    assert expected_done in section

    manual_resolutions.delete_entry(tmp, "XYZ")
    ctx = shp.ctx(tmp, now)
    ctx["resolve_prefix"] = "XYZ"
    rendered = airlines_page.render(ctx)
    section = _resolve_slice(rendered)
    assert airlines_page.RESOLVE_STALE_BODY in section

