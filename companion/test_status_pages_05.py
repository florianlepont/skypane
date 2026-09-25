"""Part 05 of the `companion/test_status_pages.py` migration chain
(33-29-PLAN.md), first half: the original harness's `check()` calls
#172-#208 (37 of part 05's 73 checks) — Home/the Frame strip going live
from `layout.freshness_line_html()`'s one definition site, the strip's
own next-update countdown (formatting only, never deciding) and the
refreshed picture's src-compared fade, `layout.stat_tile()`'s
`caption_title` tooltip, Health's stat tiles/corroboration rows reading
in plain language with no jargon or requirement id leaking into visible
text, the 52 vendored illustrations' normalized-output contract
(dimensions, byte ceiling, centring), `layout.page_shell()`/
`login_shell()`'s `<html lang>` and the two ordered theme forms, the
French nav labels and the D-17 always-rendered Advanced group, the nav
status reminder's markup/position/dot-class/French-text/None-degrade
contract, `layout.status_row()`/`section_intro_html()`'s markup and
escaping, `_device_timestamp_only()`'s verdict-free fragment, and
`layout.relative_age_text()`/`local_clock_text()`'s French forms.

One check's two source-text sub-clauses are dropped in place (TST-12
rubric S), its structural half kept fully intact: the freshness-line
check's own grep of `companion/pages/health_page.py` and
`companion/layout.py` for a literal `class="page-header__freshness`
substring is redundant with the SAME check's own rendered-equality
proof (both pages already assert `built in rendered` against
`layout.freshness_line_html()`'s own output) — a second, unused
definition of that markup inside `health_page.py` could exist and never
be observed unless it were actually rendered, which the equality check
already rules out.

One check is deleted outright (TST-12 rubric S): "no module anywhere
under companion/ defines its own alpha-threshold constant" grepped
every `.py` file under `companion/` for a second `ALPHA_THRESHOLD`
assignment, with no behaviour behind it beyond what this same module's
own centred/unclipped-bbox checks already prove by calling
`server.plane.render._opaque_bbox()` directly — a stray, unused constant
elsewhere in the package would never change what those checks observe.

One check's `inspect.getsource()` call (TST-12 rubric S) is rewritten as
a behaviour proof: `relative_age_text()`'s positional-vs-keyword call
sites are compared instead of parsing its signature's source text.

The next-update countdown check's `companion/static/*.js` source scan
(TST-12 rubric J) is rewritten to fetch every served script through
`companion/app.py`'s own `*_SCRIPT_ROUTE` registry (enumerated from the
live module's attributes, never a `companion/static` directory listing)
and strip only its comments with this chain's own
`strip_js_line_and_block_comments()` — never
`companion_markup.strip_js_comments_and_strings()`, which would also
erase the very identifiers this check searches for. The picture-fade
check's two source reads (`style.css`, `freshness.js`) are rewritten the
same way plus `companion_markup.keyframes()`/`declarations_for()` for
the stylesheet half (33-FOLLOWUPS.md F-01).

Every other check in this module calls `companion.layout`/
`companion.wake`/`companion.prefs`/`companion.pages.health_page`/
`companion.pages.home_page`/`companion.illustration_normalize` directly,
in-process, seeding fixtures under `tmp_path` via `companion.test_status_
pages_helpers`.
"""
import io
import os
import re
from datetime import datetime, timezone

import pytest
from PIL import Image

import companion.app as app_module
import companion.test_status_pages_helpers as shp
import companion.wake as wake
from companion import illustration_normalize, layout, prefs
from companion.pages import health_page, home_page
from companion_app_server import served_asset, served_stylesheet
from companion_markup import declarations_for, keyframes
from server.plane import illustrations
from server.plane import render as panel_render

_ILLUSTRATION_BYTE_CEILING = 65536
_VENDORED_ILLUSTRATION_FILENAMES = sorted(illustrations.target_filenames())


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


# --- shared helpers, local to this part -------------------------------------

_SCRIPT_ROUTE_NAME_RE = re.compile(r"^[A-Z0-9_]*SCRIPT_ROUTE$")


def _all_static_script_routes():
    """Every companion/app.py `*_SCRIPT_ROUTE` constant's value — the served
    static-JS surface, enumerated from the production module's own
    registered route names rather than a filesystem glob over
    companion/static/*.js (TST-12: no production source is opened as text,
    and this floor tracks whatever app.py itself registers). Mirrors
    companion/test_view_pages_03.py's own `_all_static_script_routes()`."""
    names = [name for name in dir(app_module) if _SCRIPT_ROUTE_NAME_RE.match(name)]
    return sorted({getattr(app_module, name) for name in names})


def _home_ctx(tmp, now):
    """A Home ctx rich enough to render every region Home declares — a
    gallery entry for the picture, a check-in for the strip's own
    next-wake resolution, and a device config for its two switches."""
    return {
        "state_dir": tmp, "now": now,
        "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
        "last_checkin_ts": now,
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "health_state": {"device_state": "ok", "pipeline_state": "ok",
                         "battery_state": "ok",
                         "device_detail_html": "", "pipeline_html": ""},
        "simple_mode": False,
    }


def _selector_literals(selector):
    """Every literal identifier a CSS selector names — its tags, classes,
    attribute names and quoted attribute values. Used to ask a rendered
    page "do you actually contain the region you declared?" without a DOM
    parser."""
    return [token for token in re.split(r'[.#\[\],"=\s>]+', selector) if token]


def _visible_text_outside_title_attributes(markup):
    # A title="..." attribute IS the sanctioned home for a technical term
    # under D-06 — strip every such attribute's value before scanning for
    # banned jargon, so this guard only ever fires on a real leak into
    # visible text.
    return re.sub(r'\btitle="[^"]*"', "", markup)


# ==========================================================================
# Home and the Frame strip go live, from the same builder and the same
# loop (23-06-PLAN.md Task 2, D1/CFG-35)
# ==========================================================================


def test_23_06_the_freshness_line_has_one_builder_and_three_call_sites(tmp_path):
    """Health's and Home's freshness lines are layout.freshness_line_html()'s own output
    verbatim — ONE definition site — each page renders exactly one data-loaded-at and one
    data-refresh-pill, and the builder emits the dot, the prefix, the clock element and the
    pill in that order with exactly one <time data-relative> (D1/CFG-35, 23-06-PLAN.md Task 2)"""
    now_iso = shp.iso(shp.now())
    built = layout.freshness_line_html(now_iso)
    health = health_page.render(shp.ctx(str(tmp_path / "h"), now_iso))
    home = home_page.render(_home_ctx(str(tmp_path / "o"), now_iso))
    for rendered, name in ((health, "Health"), (home, "Home")):
        assert built in rendered, (
            "expected %s's freshness line to be layout.freshness_line_html()'s own output "
            "verbatim" % (name,))
        assert rendered.count("data-loaded-at") == 1
        assert rendered.count("data-refresh-pill") == 1
    positions = [
        built.index(layout.REFRESH_LIVE_DOT_ATTR),
        built.index(layout.escape_html(health_page.i18n.t(layout.FRESHNESS_PREFIX_TEXT))),
        built.index("data-refresh-clock"),
        built.index("data-refresh-pill"),
    ]
    assert positions == sorted(positions), (
        "expected dot, prefix, clock, pill in that source order, got %r in %r"
        % (positions, built))
    assert built.count("data-relative") == 1


def test_23_06_home_declares_the_regions_it_actually_renders(tmp_path):
    """Home declares the four regions that actually change between polls (the strip, the
    status tiles, the picture, the recent-flights list) plus its freshness line, every
    literal in every one of its selectors appears in the rendered page, and the Display
    scope declares exactly the strip and the freshness line — everything else there is a
    form (D1/CFG-35, 23-06-PLAN.md Task 2)"""
    now_iso = shp.iso(shp.now())
    rendered = home_page.render(_home_ctx(str(tmp_path), now_iso))
    registry = layout.REFRESH_SWAP_SELECTORS_BY_PAGE
    assert layout.REFRESH_PAGE_HOME in registry
    assert layout.REFRESH_PAGE_DISPLAY in registry
    # NOT a closed set: 23-08 adds Flights, and this check must not be the
    # thing that has to change for it to.
    missing = []
    for selector in registry[layout.REFRESH_PAGE_HOME]:
        for token in _selector_literals(selector):
            if token not in rendered:
                missing.append((selector, token))
    assert not missing, (
        "Home declares regions it does not render: %r — a selector that matches nothing is "
        "a region that silently never refreshes" % (missing,))
    home_list = registry[layout.REFRESH_PAGE_HOME]
    for needle in ("frame-strip", "home-status-grid", "preview-frame", "home-flights"):
        assert any(needle in selector for selector in home_list), (
            "expected Home's swap regions to cover %r, got %r" % (needle, home_list))
    assert ".page-header__freshness" in home_list
    # DISPLAY IS DELIBERATELY CONSERVATIVE. Everything else on that page is
    # a form, and a form is the one thing a swap must never touch.
    display_list = registry[layout.REFRESH_PAGE_DISPLAY]
    assert set(display_list) == {".page-header__freshness", ".frame-strip"}, (
        "expected the Display scope to declare exactly the strip and the freshness line, "
        "got %r" % (display_list,))


def test_23_06_the_strip_countdown_formats_and_never_decides(_module_server):
    """the Frame strip's next-update cell carries a marked <time data-relative-countdown>
    over companion/wake.py's OWN resolved instant, reading the ladder's future form, beside
    a state word that stays frame_state.resolve_state()'s — and no served script names a
    state or a headline template at all (D1/D-03/CFG-26, 23-06-PLAN.md Task 2)"""
    now_iso = "2026-08-27T12:00:00+00:00"
    ctx = {
        "now": now_iso, "last_checkin_ts": "2026-08-27T11:55:00+00:00",
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
    }
    strip = layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
    assert "frame-strip__cell--update" in strip
    cell = strip[strip.index("frame-strip__cell--update"):]
    element = re.search(r"<time ([^>]*)>(.*?)</time>", cell, flags=re.S)
    assert element is not None, (
        "expected a <time data-relative> countdown in the next-update cell")
    attrs, text = element.group(1), element.group(2)
    assert layout.RELATIVE_COUNTDOWN_ATTR in attrs, (
        "expected the countdown to be marked as one (%r)" % (layout.RELATIVE_COUNTDOWN_ATTR,))
    # It ticks toward the SERVER's own instant, not one computed here.
    resolved_iso = wake.next_wake_status(ctx["last_checkin_ts"], ctx["device_config"])[0]
    expected_instant = layout._machine_instant(layout.parse_iso(resolved_iso))
    assert ('datetime="%s"' % layout.escape_html(expected_instant)) in attrs, (
        "expected the countdown to carry companion/wake.py's own resolved next-wake instant "
        "%r, got %r" % (expected_instant, attrs))
    expected_text = layout.escape_html(layout.relative_future_text(
        int((layout.parse_iso(resolved_iso) - layout.parse_iso(now_iso)).total_seconds())))
    assert text == expected_text
    # And the state word is untouched by it: the headline still carries
    # frame_state's own template, rendered whole.
    assert "Next update ≈" in strip, (
        "expected the state word to stay frame_state.resolve_state()'s own — the countdown "
        "formats a duration and decides nothing (D-03/CFG-26)")
    # No served script anywhere computes a frame state.
    for route in _all_static_script_routes():
        js = shp.strip_js_line_and_block_comments(served_asset(_module_server, route))
        for banned in ("resolve_state", "HEADLINE_LATE", "HEADLINE_HELD", "HEADLINE_DUE"):
            assert banned not in js, (
                "%s names %r — whether the frame is due, held or late is server/wake.py's "
                "answer and no script's" % (route, banned))


def test_23_06_the_picture_fades_only_when_the_picture_changed(
        tmp_path, css_text, freshness_js):
    """the refreshed picture fades through a named keyframes block spending
    var(--motion-fast) with no bare literal, the class is applied only after freshness.js
    compares the image's own src (a fade on every swap would flash the page every 45s for no
    information), and the server renders it never (D1+D3/CFG-32, 23-06-PLAN.md Task 2)"""
    assert "skypane-fade-in" in keyframes(css_text), (
        "expected a named fade-in keyframes block for the refreshed picture")
    rule_decls = declarations_for(css_text, ".is-fading-in")
    assert any("var(--motion-fast)" in value for value in rule_decls.values()), (
        "expected the fade to spend 23-01's REACTION token, got %r" % (rule_decls,))
    duration_re = re.compile(r"(?<![\w-])\d+(?:\.\d+)?m?s(?![\w-])")
    assert not any(duration_re.search(value) for value in rule_decls.values()), (
        "expected no bare duration literal in the fade rule (23-01's guard), got %r"
        % (rule_decls,))
    # The JS half: the class is added only after a real src comparison, and
    # only ever by the script.
    code = shp.strip_js_line_and_block_comments(freshness_js)
    fade_at = code.index("function markPictureFade(")
    fade_body = code[fade_at:code.index("\n  }", fade_at)]
    assert '"src"' in fade_body, (
        "expected the fade to compare the picture's own src, got %r" % (fade_body,))
    assert "FADE_CLASS" in fade_body
    assert code.count("FADE_CLASS") >= 2, (
        "the fade class is declared and never applied — a constant that agrees with the "
        "stylesheet and is not consumed proves nothing")
    # The SERVER never renders it: the motion belongs to the loop that
    # knows a new picture arrived, exactly like the breathing dot 23-05
    # shipped.
    rendered = home_page.render(_home_ctx(str(tmp_path), shp.iso(shp.now())))
    assert "is-fading-in" not in rendered, (
        "expected the server to render no fade class at all — a picture that fades in on "
        "every page load is an animation playing, not information")


# ==========================================================================
# layout.stat_tile()'s caption_title tooltip (19-06-PLAN.md Task 1, D-06)
# ==========================================================================


def test_stat_tile_caption_title_byte_identical_when_unused():
    """layout.stat_tile()'s new caption_title parameter is byte-identical to the
    pre-existing output when omitted, None, or '' (19-06-PLAN.md Task 1, D-06)"""
    default_call = layout.stat_tile("C", "<p>x</p>", "ok", None)
    explicit_none = layout.stat_tile("C", "<p>x</p>", "ok", None, caption_title=None)
    explicit_empty = layout.stat_tile("C", "<p>x</p>", "ok", None, caption_title="")
    assert default_call == explicit_none == explicit_empty
    assert "title=" not in default_call


def test_stat_tile_caption_title_renders_as_tooltip_on_caption_only():
    """layout.stat_tile()'s caption_title renders as a title attribute on the caption <p>
    element, and nowhere else (19-06-PLAN.md Task 1, D-06)"""
    markup = layout.stat_tile("Cap", "<p>y</p>", "ok", None, caption_title="Tech Term")
    assert markup.count('title="Tech Term"') == 1
    caption_open = markup.index('<p class="text-label stat-tile__caption"')
    caption_close = markup.index(">", caption_open)
    caption_tag = markup[caption_open:caption_close]
    assert 'title="Tech Term"' in caption_tag, (
        "expected the title attribute on the caption <p> element itself, got %r" % caption_tag)


def test_stat_tile_caption_title_is_escaped():
    """layout.stat_tile()'s caption_title is escaped through escape_html(), matching every
    other attribute value this module emits (19-06-PLAN.md Task 1, D-06/T-19-08)"""
    hostile = 'a<b"c'
    markup = layout.stat_tile("Cap", "<p>y</p>", "ok", None, caption_title=hostile)
    assert hostile not in markup
    assert "&lt;" in markup and "&quot;" in markup


# ==========================================================================
# Health's stat tiles and corroboration rows read in plain language
# (19-06-PLAN.md Task 2/3, D-06)
# ==========================================================================


def test_health_tiles_and_rows_read_in_plain_language(tmp_path):
    """Health's stat tiles and corroboration rows read in plain language: 'Corroboration',
    'Single-source (uncorroborated)' and 'pipeline last ran' are all absent from visible
    text, and the Pipeline/Corroboration/Resolution-rate tiles' caption elements each carry
    a title attribute equal to their matching technical constant (19-06-PLAN.md Task 2, D-06)"""
    tmp = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(tmp, [(shp.iso(now), 4200)])
    from server import history_db
    shp.seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_runway_events(tmp, [{"ts": shp.iso(now), "hex": "abc123", "corroborated": True}])
    rendered = health_page.render(shp.ctx(tmp, shp.iso(now)))

    visible = _visible_text_outside_title_attributes(rendered)
    for banned in ("Corroboration", "Single-source (uncorroborated)", "pipeline last ran"):
        assert banned not in visible, (
            "expected %r to be absent from visible text (outside a title attribute)" % banned)

    for label, expected_title in (
            (health_page.PIPELINE_FRESHNESS_LABEL, health_page.PIPELINE_FRESHNESS_TITLE),
            (health_page.CORROBORATION_TILE_LABEL, health_page.CORROBORATION_TILE_TITLE),
            (health_page.RESOLUTION_RATE_LABEL, health_page.RESOLUTION_RATE_TITLE)):
        needle = ">%s<" % layout.escape_html(label)
        at = rendered.index(needle)
        caption_open = rendered.rindex('<p class="text-label stat-tile__caption"', 0, at)
        caption_close = rendered.index(">", caption_open)
        caption_tag = rendered[caption_open:caption_close]
        expected_attr = 'title="%s"' % layout.escape_html(expected_title)
        assert expected_attr in caption_tag, (
            "expected the %r tile's caption element to carry %s, got %r"
            % (label, expected_attr, caption_tag))


def test_health_registry_and_stats_prose_has_no_adsbdb_or_requirement_id(tmp_path):
    """a full Health render with a non-empty unresolved registry and stats rows (every
    branch rendered) contains no 'adsbdb' and no CFG-\\d requirement id outside a title
    attribute (19-06-PLAN.md Task 3, D-06/T-19-24)"""
    tmp = str(tmp_path)
    now = shp.now()
    from server import history_db
    shp.seed_device_health(tmp, [(shp.iso(now), 4200)])
    shp.seed_meta(tmp, **{history_db.META_LAST_PIPELINE_RUN: shp.iso(now)})
    shp.seed_unresolved_prefixes(tmp, {
        "ABC": {"count": 3, "first_seen": shp.iso(now), "last_seen": shp.iso(now),
                "example_callsign": "ABC123"},
    })
    events = []
    for source in ("fresh_hit", "cache_hit", "airline_only", "miss", "manual"):
        events.append({"ts": shp.iso(now), "hex": "abc123", "route_source": source})
    shp.seed_runway_events(tmp, events)
    rendered = health_page.render(shp.ctx(tmp, shp.iso(now)))

    assert health_page.UNRESOLVED_SECTION_HEADING in rendered and "data-filter-input" in rendered, (
        "fixture gap: expected the registry card to actually render")
    assert health_page.STATS_SECTION_HEADING in rendered and "% resolved" in rendered, (
        "fixture gap: expected the resolution-statistics card to actually render")
    assert "adsbdb" not in rendered
    visible = _visible_text_outside_title_attributes(rendered)
    assert not re.search(r"CFG-\d", visible), "expected no requirement id (CFG-\\d) in visible text"


# ==========================================================================
# companion/illustration_normalize.py — the shared opaque-bbox
# normalization helper (quick task 260902-req-02 Task 1). All checks
# below iterate the real vendored files under illustrations.ILLUSTRATION_
# DIR (the same "real project assets, not synthetic fixtures" discipline
# server/test_render.py already uses) except the None-bbox fallback
# check, which needs a synthetic fully-transparent source.
# ==========================================================================


def test_exactly_52_vendored_illustration_files_are_registered():
    """all 52 vendored illustrations normalize to the exact same pixel dimensions
    (illustration_normalize.ILLUSTRATION_TARGET_SIZE)"""
    assert len(_VENDORED_ILLUSTRATION_FILENAMES) == 52, (
        "expected 52 vendored illustration files, got %d" % len(_VENDORED_ILLUSTRATION_FILENAMES))


@pytest.mark.parametrize("filename", _VENDORED_ILLUSTRATION_FILENAMES)
def test_all_illustrations_normalize_to_identical_pixel_dimensions(filename):
    """all 52 vendored illustrations normalize to the exact same pixel dimensions
    (illustration_normalize.ILLUSTRATION_TARGET_SIZE)"""
    path = os.path.join(illustrations.ILLUSTRATION_DIR, filename)
    png_bytes = illustration_normalize.normalized_png_bytes(path)
    with Image.open(io.BytesIO(png_bytes)) as out:
        assert out.size == illustration_normalize.ILLUSTRATION_TARGET_SIZE, (
            "%s normalized to %r, expected %r"
            % (filename, out.size, illustration_normalize.ILLUSTRATION_TARGET_SIZE))


@pytest.mark.parametrize("filename", _VENDORED_ILLUSTRATION_FILENAMES)
def test_all_illustrations_serve_well_under_the_byte_ceiling(filename):
    """all 52 vendored illustrations normalize and serve well under 65536 bytes per file,
    the UIR-08 weight fix — a regression that got the dimensions right but left the served
    bytes unchanged would defeat this check"""
    path = os.path.join(illustrations.ILLUSTRATION_DIR, filename)
    png_bytes = illustration_normalize.normalized_png_bytes(path)
    assert len(png_bytes) < _ILLUSTRATION_BYTE_CEILING, (
        "%s normalized to %d bytes, expected under the %d-byte ceiling"
        % (filename, len(png_bytes), _ILLUSTRATION_BYTE_CEILING))


@pytest.mark.parametrize("filename", _VENDORED_ILLUSTRATION_FILENAMES)
def test_all_illustrations_are_centred_and_unclipped(filename):
    """all 52 vendored illustrations normalize with their painted content centred within
    1px on both axes and never clipped"""
    target_w, target_h = illustration_normalize.ILLUSTRATION_TARGET_SIZE
    path = os.path.join(illustrations.ILLUSTRATION_DIR, filename)
    png_bytes = illustration_normalize.normalized_png_bytes(path)
    with Image.open(io.BytesIO(png_bytes)) as out:
        out_rgba = out.convert("RGBA")
    bbox = panel_render._opaque_bbox(out_rgba)
    assert bbox is not None, "%s: normalized output has no opaque bbox at all" % filename
    left, top, right, bottom = bbox
    assert 0 <= left and 0 <= top and right <= target_w and bottom <= target_h, (
        "%s: painted bbox %r is not fully inside the %dx%d output"
        % (filename, bbox, target_w, target_h))
    centre_x, centre_y = (left + right) / 2.0, (top + bottom) / 2.0
    assert abs(centre_x - target_w / 2.0) <= 1.0, (
        "%s: painted centre-x %.2f is more than 1px from the output centre %.2f"
        % (filename, centre_x, target_w / 2.0))
    assert abs(centre_y - target_h / 2.0) <= 1.0, (
        "%s: painted centre-y %.2f is more than 1px from the output centre %.2f"
        % (filename, centre_y, target_h / 2.0))


def test_none_opaque_bbox_falls_back_to_source_image_without_raising(tmp_path):
    """a source image whose opaque bbox is None (nothing painted) falls back to the source
    image instead of raising, and still normalizes to the target output size"""
    fully_transparent_path = str(tmp_path / "fully-transparent.png")
    Image.new("RGBA", (400, 200), (0, 0, 0, 0)).save(fully_transparent_path)
    png_bytes = illustration_normalize.normalized_png_bytes(fully_transparent_path)
    with Image.open(io.BytesIO(png_bytes)) as out:
        assert out.size == illustration_normalize.ILLUSTRATION_TARGET_SIZE, (
            "expected the None-bbox fallback to still normalize to the target size, got %r"
            % (out.size,))


# ==========================================================================
# companion/layout.py: <html lang>, the three-switch nav footer,
# localised nav labels and simple-mode nav suppression (D-01..D-09/
# D-29/D-30, 20-01-PLAN.md Task 3)
# ==========================================================================


def test_page_shell_html_lang_follows_prefs():
    """page_shell() renders <html lang="fr" under prefs.set_request_prefs(lang='fr') and
    <html lang="en" otherwise (D-03)"""
    try:
        prefs.set_request_prefs(lang="fr")
        fr_rendered = layout.page_shell(title="Health", active="health", body="", ui_theme="auto")
        prefs.set_request_prefs(lang="en")
        en_rendered = layout.page_shell(title="Health", active="health", body="", ui_theme="auto")
    finally:
        prefs.set_request_prefs(lang="en")
    assert '<html lang="fr"' in fr_rendered
    assert '<html lang="en"' in en_rendered


def test_login_shell_html_lang_follows_prefs():
    """login_shell() renders <html lang="fr" under prefs.set_request_prefs(lang='fr') and
    <html lang="en" otherwise (D-03)"""
    try:
        prefs.set_request_prefs(lang="fr")
        fr_rendered = layout.login_shell("", ui_theme="auto")
        prefs.set_request_prefs(lang="en")
        en_rendered = layout.login_shell("", ui_theme="auto")
    finally:
        prefs.set_request_prefs(lang="en")
    assert '<html lang="fr"' in fr_rendered
    assert '<html lang="en"' in en_rendered


def test_shell_has_two_ordered_theme_forms_each_with_aria_label():
    """a rendered shell contains exactly two aria-labelled theme-form forms per footer copy,
    actions /ui-lang, /ui-theme in that document order, and zero /ui-mode forms (D-02/D-17,
    21-UI-SPEC.md §G)"""
    rendered = layout.page_shell(title="Health", active="health", body="", ui_theme="auto")
    actions_in_order = re.findall(
        r'<form class="theme-form" method="post" action="([^"]+)" aria-label="[^"]+"', rendered)
    assert actions_in_order.count("/ui-lang") == 2, (
        "expected exactly 2 /ui-lang forms (sidebar + mobile), got %r"
        % (actions_in_order.count("/ui-lang"),))
    assert actions_in_order.count("/ui-theme") == 2
    # D-17 (21-01-PLAN.md Task 1): the simple-mode switch is deleted —
    # zero /ui-mode forms anywhere in a rendered shell.
    assert actions_in_order.count("/ui-mode") == 0
    assert actions_in_order[:2] == ["/ui-lang", "/ui-theme"], (
        "expected the first footer's forms in order lang/theme, got %r" % (actions_in_order[:2],))


def test_french_shell_nav_reads_the_locked_french_labels():
    """under lang='fr' the nav reads Accueil/Affichage/Vols/Compagnies/Avancé/État/Appareil
    (D-09)"""
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = layout.page_shell(title="Home", active="home", body="", ui_theme="auto")
    finally:
        prefs.set_request_prefs(lang="en")
    for label in ("Accueil", "Affichage", "Vols", "Compagnies", "Avancé", "État", "Appareil"):
        assert label in rendered, "expected the French nav label %r in the rendered shell" % (label,)


def test_advanced_group_always_renders_in_both_nav_copies():
    """the Advanced group (Health, Device) and the nav status dot always render, in both the
    sidebar and the bottom tab bar, on a plain request (D-17; retargeted from the dropdown by
    22-14-PLAN.md Task 2)"""
    rendered = layout.page_shell(
        title="Home", active="home", body="", ui_theme="auto", health_alert="warn",
        device_config={"display_enabled": True, "quiet_hours_enabled": False})
    assert layout.ADVANCED_GROUP_LABEL in rendered
    sidebar = rendered[rendered.index('<nav class="sidebar-nav"'):rendered.index("</aside>")]
    bar_start = rendered.index('<nav class="tab-bar"')
    bar = rendered[bar_start:rendered.index("</nav>", bar_start)]
    for route in (layout.HEALTH_ROUTE, layout.DEVICE_ROUTE):
        assert ('href="%s"' % route) in sidebar, "expected a %s href in the sidebar copy" % route
        assert ('href="%s"' % route) in bar, "expected a %s href in the tab bar copy" % route
    assert layout.NAV_NOTIFICATION_CLASS in rendered


# ==========================================================================
# The nav state reminder (D-03/R-03/R-04, 21-04-PLAN.md Task 2)
# ==========================================================================

_NAV_STATUS_DEVICE_CFG = {"display_enabled": True, "quiet_hours_enabled": False}


def test_nav_status_appears_once_in_each_nav_copy_after_the_brand():
    """the sidebar and the mobile dropdown each contain exactly one .nav-status link, with no
    <form> or <button> inside it, sitting after the brand and before the primary nav list in
    document order (D-03)"""
    rendered = layout.page_shell(
        title="Home", active="home", body="", ui_theme="auto",
        device_config=_NAV_STATUS_DEVICE_CFG)
    assert rendered.count('class="nav-status text-label"') == 2, (
        "expected exactly one .nav-status reminder in the sidebar and one in the mobile "
        "dropdown, got %d" % rendered.count('class="nav-status text-label"'))
    assert rendered.count('<nav class="tab-bar"') == 1
    bar_start = rendered.index('<nav class="tab-bar"')
    assert "nav-status" not in rendered[bar_start:rendered.index("</nav>", bar_start)]
    for match in re.finditer(r'<a class="nav-status text-label"[^>]*>(.*?)</a>', rendered):
        segment = match.group(0)
        assert "<form" not in segment and "<button" not in segment
    brand_pos = rendered.index('<span class="site-title sidebar-title">')
    sidebar_nav_status_pos = rendered.index('class="nav-status text-label"', brand_pos)
    sidebar_nav_list_pos = rendered.index('<nav class="sidebar-nav"', brand_pos)
    assert brand_pos < sidebar_nav_status_pos < sidebar_nav_list_pos
    mobile_panel_pos = rendered.index('<div id="%s" class="mobile-nav">' % layout.MOBILE_NAV_ID)
    mobile_nav_status_pos = rendered.index('class="nav-status text-label"', mobile_panel_pos)
    mobile_footer_pos = rendered.index('class="mobile-nav__footer"', mobile_panel_pos)
    assert mobile_panel_pos < mobile_nav_status_pos < mobile_footer_pos, (
        "expected the mobile dropdown's nav-status to be its first child, before its footer")


def test_nav_status_dot_classes_follow_the_four_on_off_combinations():
    """nav_status_html()'s two dots follow all four Screen/Quiet-hours on/off combinations
    (dot--ok for on, dot--off for off) (D-03)"""
    for display_enabled, quiet_hours_enabled, screen_dot, quiet_dot in (
            (True, False, "dot--ok", "dot--off"),
            (False, False, "dot--off", "dot--off"),
            (True, True, "dot--ok", "dot--ok"),
            (False, True, "dot--off", "dot--ok")):
        rendered = layout.nav_status_html(
            {"display_enabled": display_enabled, "quiet_hours_enabled": quiet_hours_enabled})
        first_dot = re.search(r'<span class="dot ([^"]+)"></span>', rendered).group(1)
        second_dot = re.findall(r'<span class="dot ([^"]+)"></span>', rendered)[1]
        assert (first_dot, second_dot) == (screen_dot, quiet_dot), (
            "display_enabled=%r quiet_hours_enabled=%r: expected dots (%r, %r), got (%r, %r)"
            % (display_enabled, quiet_hours_enabled, screen_dot, quiet_dot, first_dot, second_dot))


def test_french_nav_status_reads_ecran_allume_heures_calmes_desactivees():
    """under lang='fr' the reminder reads 'Écran allumé' and 'Heures calmes désactivées' —
    fully French, never 'Heures calmes off' (R-04)"""
    try:
        prefs.set_request_prefs(lang="fr")
        rendered = layout.nav_status_html(_NAV_STATUS_DEVICE_CFG)
    finally:
        prefs.set_request_prefs(lang="en")
    assert "Écran allumé" in rendered and "Heures calmes désactivées" in rendered
    labels = re.findall(r'<span class="dot-label">([^<]*)</span>', rendered)
    for label in labels:
        assert "off" not in label.lower(), (
            "expected no leftover English 'off' in a visible label, got %r" % (label,))


def test_nav_status_html_none_or_falsy_device_config_renders_nothing():
    """nav_status_html(None) and nav_status_html({}) both return '', and page_shell(...,
    device_config=None) — the default, used by login/404/error pages — renders no
    .nav-status at all (D-03)"""
    assert layout.nav_status_html(None) == ""
    assert layout.nav_status_html({}) == ""
    rendered = layout.page_shell(title="Home", active="home", body="", ui_theme="auto")
    assert "nav-status" not in rendered


def test_login_shell_carries_no_nav_status_and_is_unchanged():
    """login_shell() — which never takes a device_config parameter — carries no .nav-status
    markup, unchanged by this task (D-03)"""
    rendered = layout.login_shell("", ui_theme="auto")
    assert "nav-status" not in rendered


# ==========================================================================
# layout.status_row()/section_intro_html(), and health_page.py's
# verdict-free _device_timestamp_only()/device_detail_html (D-21/D-17/
# §C, 20-03-PLAN.md Task 1)
# ==========================================================================


def test_status_row_renders_dot_label_verdict_detail():
    """status_row('Frame', 'Checking in normally', 'Last check-in 2m ago', 'ok') carries
    status-row--ok, dot--ok, all three texts and exactly one status-row__label (D-21)"""
    rendered = layout.status_row("Frame", "Checking in normally", "Last check-in 2m ago", "ok")
    assert "status-row--ok" in rendered
    assert "dot--ok" in rendered
    for text in ("Frame", "Checking in normally", "Last check-in 2m ago"):
        assert text in rendered
    assert rendered.count("status-row__label") == 1


def test_status_row_empty_label_omits_the_label_span():
    """status_row('', ..., 'warn') omits the status-row__label span entirely, not merely its
    text (D-21, 20-UI-SPEC.md Section Anatomy A)"""
    rendered = layout.status_row("", "Not connected", "checked 10 min ago", "warn")
    assert "status-row__label" not in rendered


def test_status_row_unrecognised_state_falls_back_safely():
    """status_row(..., state='nonsense') falls back to the default dot class and emits no
    status-row--nonsense class (T-20-18)"""
    rendered = layout.status_row("Frame", "Verdict", "Detail", "nonsense")
    assert "status-row--nonsense" not in rendered
    assert layout._DEFAULT_STATUS_DOT_CLASS in rendered


def test_status_row_escapes_hostile_verdict_and_detail():
    """status_row() with a hostile <script>-shaped verdict/detail comes back escaped, never
    raw markup (T-20-03)"""
    rendered = layout.status_row(
        "Frame", "<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "error")
    assert "<script>" not in rendered and "<img " not in rendered
    assert "&lt;script&gt;" in rendered


def test_section_intro_html_is_byte_identical_to_the_promoted_markup():
    """layout.section_intro_html() emits the byte-identical markup health_page.py's own
    former private _section_intro_html() rendered before the promotion (20-UI-SPEC.md
    Section Anatomy C)"""
    rendered = layout.section_intro_html("test-id", "Heading", "Description")
    expected = (
        '<div class="section-intro">'
        '<h2 id="test-id" class="text-heading">Heading</h2>'
        '<p class="text-label section-caption">Description</p>'
        "</div>")
    assert rendered == expected


def test_section_intro_html_escapes_hostile_section_id():
    """layout.section_intro_html() escapes a hostile section_id argument, never writing it
    raw into the id="..." attribute (WR-03, 20-REVIEW.md)"""
    rendered = layout.section_intro_html('"><script>alert(1)</script>', "Heading", "Description")
    assert "<script>" not in rendered
    assert "&lt;script&gt;" in rendered


def test_health_page_no_longer_defines_section_intro_html():
    """health_page no longer defines its own _section_intro_html — layout.section_intro_html
    is the one definition"""
    assert not hasattr(health_page, "_section_intro_html")


def test_device_timestamp_only_carries_no_verdict_text():
    """_device_timestamp_only() emits no widget-verdict class and no DEVICE_STATE_TEXT
    value, while _device_section() still carries exactly one (D-17)"""
    now = shp.iso(shp.now())
    ts = shp.ago(120)
    detail_only = health_page._device_timestamp_only({"ts": ts}, now)
    assert "widget-verdict" not in detail_only
    for verdict_text in health_page.DEVICE_STATE_TEXT.values():
        assert verdict_text not in detail_only
    full_row, _state = health_page._device_section({"ts": ts}, now)
    verdict_occurrences = sum(
        1 for verdict_text in health_page.DEVICE_STATE_TEXT.values() if verdict_text in full_row)
    assert verdict_occurrences == 1, (
        "expected _device_section() to still carry exactly one DEVICE_STATE_TEXT verdict, "
        "got %d" % verdict_occurrences)


def test_compute_health_state_carries_device_detail_html(tmp_path):
    """compute_health_state()'s returned dict carries a device_detail_html key holding the
    verdict-free fragment also embedded (once) inside device_html (D-17)"""
    tmp = str(tmp_path)
    now = shp.now()
    shp.seed_device_health(tmp, [(shp.ago(120), 3800)])
    state = health_page.compute_health_state(tmp, now=shp.iso(now))
    assert "device_detail_html" in state
    detail_only = state["device_detail_html"]
    assert "widget-verdict" not in detail_only
    for verdict_text in health_page.DEVICE_STATE_TEXT.values():
        assert verdict_text not in detail_only
    assert detail_only in state["device_html"], (
        "expected device_detail_html to be the exact verdict-free fragment embedded inside "
        "device_html")


# ==========================================================================
# companion/layout.py's language-aware relative_age_text()/
# local_clock_text() (D-07, 20-03-PLAN.md Task 2)
# ==========================================================================


def test_relative_age_text_french_seconds_bucket_reads_a_linstant():
    """under lang='fr', relative_age_text(30) reads 'à l’instant' and relative_age_text(90000)
    reads 'il y a 1\\u00a0j' (D-07)"""
    try:
        prefs.set_request_prefs(lang="fr")
        thirty_s = layout.relative_age_text(30)
        one_day = layout.relative_age_text(90000)
    finally:
        prefs.set_request_prefs(lang="en")
    assert thirty_s == "à l’instant"
    assert one_day.startswith("il y a 1")
    assert " " in one_day, "expected a real U+00A0 between the number and the unit (D-09)"


def test_relative_age_text_english_unchanged_under_default_lang():
    """under lang='en' (the default), relative_age_text()'s English output is byte-for-byte
    unchanged — '30s ago'/'1d ago' (D-07)"""
    try:
        prefs.set_request_prefs(lang="en")
        thirty_s = layout.relative_age_text(30)
        one_day = layout.relative_age_text(90000)
    finally:
        prefs.set_request_prefs(lang="en")
    assert thirty_s == "30s ago"
    assert one_day == "1d ago"


def test_local_clock_text_french_month_abbreviation():
    """local_clock_text() on a September timestamp reads 'sept.' under fr and 'Sep' under en,
    with an identical HH:MM in both (D-07)"""
    try:
        prefs.set_request_prefs(lang="fr")
        september = datetime(2026, 9, 10, 11, 53, tzinfo=timezone.utc)
        now = datetime(2026, 9, 11, 12, 0, tzinfo=timezone.utc)
        fr_rendered = layout.local_clock_text(september, now)
        prefs.set_request_prefs(lang="en")
        en_rendered = layout.local_clock_text(september, now)
    finally:
        prefs.set_request_prefs(lang="en")
    assert "sept." in fr_rendered
    assert "Sep" in en_rendered
    assert fr_rendered.rsplit(" ", 1)[-1] == en_rendered.rsplit(" ", 1)[-1], (
        "expected an identical HH:MM in both languages")


def test_relative_age_text_first_positional_argument_is_age_seconds():
    """relative_age_text()'s positional signature (age_seconds first) is untouched — lang is
    a trailing keyword only"""
    # TST-12 rubric S: the legacy check parsed inspect.getsource(relative_age_text)'s first
    # line for the parameter order. Rewritten as a behaviour proof instead: a positional call
    # in the pinned order (age_seconds, lang) must equal the same call spelled out with both
    # parameter names — a signature that quietly swapped the two would still satisfy the
    # keyword call but not the positional one.
    assert layout.relative_age_text(30, "fr") == layout.relative_age_text(age_seconds=30, lang="fr")
