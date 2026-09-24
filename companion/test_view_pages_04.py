"""Part 04 of the `companion/test_view_pages.py` migration chain
(33-08-PLAN.md): the original harness's check() calls #135-#169, the
chain's LAST slice — Home's French end-to-end render, the status card's
localised health-state timestamps, the Frame/Flight-data tile verdict
contracts, the CSS-only checks for the status grid/recent-flight time
cell/thumbnail treatments, Home's degrade-with-nothing/battery-move
contracts, the day band's own time-scale/night-window/crowding/class
contracts (companion/draw.py) and its Home integration (Paris-day
bucketing, quiet-hours shading, one extra history.db read), the hero
composition proving the ring/band are fed by companion/draw.py's shared
emitters rather than a forked copy, companion.wake/companion.frame_state's
own resolution contracts, companion/frame_state.py's view-free boundary,
and two end-to-end HTTP round trips (the retired /preview page, the
Airlines dialog forms rendering unconditionally) plus the shared
@starting-style lightbox entrance CSS contract.

Every check calls `home_page.render()` / `frame_state`/`wake` functions
directly, or drives a real `companion/app.py` over HTTP
(`make_app_server`/`module_app_server_factory`), with a `tmp_path`-backed
state directory. Checks that used to read `companion/static/style.css`
from disk instead fetch it from a running server
(`module_app_server_factory` + `served_stylesheet()`) and assert on
`companion_markup`'s parsed CSS rules — never a file opened from disk
(TST-12). Two checks that used to read `companion/frame_state.py` /
`companion/battery.py` as text are rewritten per rubric S: the "never
imports X" half becomes a subprocess-import + `sys.modules` proof (the
same technique `companion/test_companion_app_03.py`'s own `battery`/
`draw` import-boundary checks already established), and the "never names
a CSS class literal" half becomes a scan of the module's own already-
imported public string constants — the module's actual returned copy,
never its source text. Two checks that used a syntax-tree walk
(`inspect.getsource()`/`ast.parse()`, banned outright by guard G2) over
`companion/pages/home_page.py` to prove "no forked ring/band markup" are
trimmed to their surviving, already-behavioural assertions: the same
property is proven MORE strongly by `test_breaking_a_shared_emitter_
breaks_the_hero_with_the_page_it_borrowed_it_from` below, which mutates
the shared emitter's own class constant and observes both pages move
together — a forked copy could not do that. See the ledger fragment's
Part 04 note for the full rubric accounting.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest

import companion.battery as battery
import companion.layout as layout
import companion.prefs as prefs
import companion.test_view_pages_helpers as vp
import companion.wake as wake
from companion.pages import health_page, home_page
from companion_app_server import served_stylesheet
from companion_markup import declarations_for, rules_with_selector
from server import history_db

# An arbitrary, fixed epoch second standing in for a Paris midnight — the
# scale under test is pure arithmetic on two numbers in the same unit, so
# nothing here needs a real timezone (companion/draw.py may not import the
# server package, where the one Paris-day conversion lives).
_BAND_DAY_START = 1756000000


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's CSS-only checks
    fetch the served stylesheet from, instead of opening it from disk
    (TST-12)."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


# --- day-band drawing helpers (companion/draw.py's own markup) ----------

def _band_hour(n):
    return _BAND_DAY_START + int(n * 3600)


def _band_shapes(markup, class_name):
    """Every <rect> in `markup` carrying exactly `class_name`.

    The closing quote in the pattern is load-bearing: `drawing-band` is a
    strict prefix of both `drawing-band-span` and `drawing-band-mark`, so
    a `'class="drawing-band"' in element` test would report all three as
    the frame.
    """
    return re.findall(r'<rect class="%s"[^>]*/>' % re.escape(class_name), markup)


def _band_attr(element, name):
    found = re.search(r'\s%s="([^"]*)"' % re.escape(name), element)
    return found.group(1) if found else None


def _band_percent(element, name):
    raw = _band_attr(element, name)
    if raw is None or not raw.endswith("%"):
        return None
    return float(raw[:-1])


# --- Home's own day-band integration helpers ----------------------------

def _home_day_band_section(rendered):
    """The day band's <section> only, or None.

    Sliced out rather than searched for in the whole page because two of
    the assertions below are about what the caption does NOT say, and
    "quiet hours" appears elsewhere on this page in the frame strip's own
    switch. A page-wide `"quiet" not in rendered` would be green only on a
    page that had lost the strip.
    """
    opened = re.search(r'<section class="[^"]*\bday-band\b[^"]*"', rendered)
    if opened is None:
        return None
    end = rendered.index("</section>", opened.start())
    return rendered[opened.start():end + len("</section>")]


def _home_band_marks(section):
    return re.findall(r'<rect class="drawing-band-mark"[^>]*/>', section)


def _home_band_spans(section):
    return re.findall(r'<rect class="drawing-band-span"[^>]*/>', section)


def _home_band_ctx(state_dir, now, checkins, config=None):
    with history_db.open_db(state_dir) as conn:
        for ts in checkins:
            history_db.record_device_health(conn, ts, battery_mv=3750)
    return {
        "state_dir": str(state_dir), "now": now,
        "last_checkin_ts": checkins[-1] if checkins else None,
        "device_config": config or {"wake_interval_s": 900, "display_enabled": True},
        "health_state": {"device_state": "ok", "pipeline_state": "ok",
                         "battery_state": "ok", "device_detail_html": "",
                         "pipeline_html": ""},
        "simple_mode": False,
    }


# --- the hero composition's own containment helper ----------------------

def _home_hero_inner(rendered):
    """The hero container's own inner markup, or None when the page
    renders no hero at all.

    A BALANCED SCAN, never `rendered.index("</div>")`: the hero holds
    sections that hold divs of their own, so the first closing tag after
    the opening one belongs to a descendant.
    """
    opened = re.search(
        r'<div class="[^"]*\b%s\b[^"]*">' % re.escape(home_page.HERO_CLASS), rendered)
    if opened is None:
        return None
    depth = 0
    for token in re.finditer(r"<div\b|</div>", rendered[opened.start():]):
        depth += 1 if token.group(0) == "<div" else -1
        if depth == 0:
            return rendered[opened.end():opened.start() + token.start()]
    return None


def _classes_inside_svg(markup, opening_class):
    """The set of class attributes emitted INSIDE the first <svg> whose
    own class begins with `opening_class`, or None when there is no such
    element.
    """
    svg = re.search(
        r'<svg class="%s[^"]*"[^>]*>(.*?)</svg>' % re.escape(opening_class), markup, re.S)
    if svg is None:
        return None
    return set(re.findall(r'class="([^"]*)"', svg.group(1)))


# --- Home's fully-seeded French render (22-04..22-07-PLAN.md) ----------

def test_home_full_seeded_render_localises_to_french_without_leaking_english(tmp_path):
    """a fully-seeded Home render under lang='fr' shows the French page title, section
    headings, status-row labels and next-update headline with no English string leaking in
    (while the callsign/airline data stays untranslated), and the identical seeded render
    under the default language still carries every pre-existing English needle"""
    now = "2026-08-27T12:00:00+00:00"
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T11:50:00+00:00", "hex": "3c6444", "callsign": "AFR1380",
         "airline": "Air France", "origin": "ORY", "destination": "TLS",
         "confirmed_state": "departing"},
    ])
    with history_db.open_db(tmp_path) as conn:
        history_db.record_device_health(conn, "2026-08-27T11:55:00+00:00", battery_mv=3750)
    ctx = {
        "state_dir": str(tmp_path), "now": now,
        "gallery_entries": ["2026-08-27T11-50-00+00-00.png"],
        "last_checkin_ts": "2026-08-27T11:55:00+00:00",
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "health_state": {"device_state": "ok", "pipeline_state": "warn",
                         "battery_state": "ok",
                         "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
                         "pipeline_html": "<p>A little stale</p>"},
        "simple_mode": False,
    }
    prefs.set_request_prefs(lang="fr")
    try:
        rendered_fr = home_page.render(ctx)
    finally:
        prefs.set_request_prefs(lang="en")
    for needle in (
            ">Accueil<", "Vols récents", "Voir tous les vols", "Cadre", "Batterie",
            "Données de vol", "Au départ"):
        assert needle in rendered_fr, "expected the French %r in the French Home render" % (needle,)
    assert "Prochaine mise à jour" in rendered_fr or "Attendue depuis" in rendered_fr, (
        "expected either French next-update headline wording")
    for english_only in (
            "Recent flights", "See all flights", ">Frame<", ">Battery<", "Departing"):
        assert english_only not in rendered_fr, (
            "expected no English %r leaking into the French render" % (english_only,))
    assert "AFR1380" in rendered_fr and "Air France" in rendered_fr, (
        "expected the callsign/airline data to stay untranslated in French")

    rendered_en = home_page.render(ctx)
    for needle in (
            '<h1 class="page-title">Home</h1>', "Recent flights", "See all flights",
            home_page.FRAME_ROW_LABEL, home_page.BATTERY_ROW_LABEL,
            home_page.DATA_ROW_LABEL, "Next update ≈"):
        assert needle in rendered_en, (
            "expected the English %r in the default-language Home render" % (needle,))


def test_home_status_card_localises_real_health_state_timestamps_under_french(tmp_path):
    """Home's status card, fed a REAL health_page.compute_health_state() result computed under
    lang='fr', fully localises the Frame/Flight-data rows' timestamps (no English month
    abbreviation or ' ago' survives) and the Flight-data row's detail is now a single,
    verdict-free clause — never joined with ' · ', never repeating Health's own verdict
    wording (22-07-PLAN.md Task 1 B2 retarget)"""
    now = "2026-09-12T00:00:00+00:00"
    device_ts = "2026-09-10T23:58:00+00:00"
    with history_db.open_db(tmp_path) as conn:
        history_db.record_device_health(conn, device_ts, battery_mv=3800)
        history_db.set_meta(conn, history_db.META_LAST_PIPELINE_RUN, device_ts)
        history_db.set_meta(conn, history_db.META_LAST_DETECTION, device_ts)
    prefs.set_request_prefs(lang="fr")
    try:
        health_state = health_page.compute_health_state(str(tmp_path), now=now)
        ctx = {
            "state_dir": str(tmp_path), "now": now, "gallery_entries": [],
            "last_checkin_ts": device_ts,
            "device_config": {"wake_interval_s": 900, "display_enabled": True},
            "health_state": health_state, "simple_mode": False,
        }
        rendered = home_page.render(ctx)
    finally:
        prefs.set_request_prefs(lang="en")
    assert "sept." in rendered, "expected the French month abbreviation 'sept.' in the Home render"
    assert " ago" not in rendered, "expected no English ' ago' in the Home render"
    for english_month in (
            "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep",
            "Oct", "Nov", "Dec"):
        assert english_month not in rendered, (
            "expected no English month abbreviation %r in the Home render" % (english_month,))
    # "Données de vol" is companion/i18n_fr/home.py's own French
    # translation of DATA_ROW_LABEL ("Flight data") — the label itself is
    # French text by this point in the render, so the anchor must be too.
    data_row_start = rendered.index("Données de vol")
    data_row_end = rendered.index("</div>", data_row_start)
    data_row = rendered[data_row_start:data_row_end]
    assert data_row.count(" · ") == 0, (
        "expected NO ' · '-joined multi-clause detail in the Flight-data row — the "
        "verdict-free, single-clause pipeline_detail_html replaced the re-embedded 3-clause "
        "pipeline_html (got %r)" % (data_row,))
    assert health_page.PIPELINE_STATE_TEXT["error"] not in data_row, (
        "expected Health's own PIPELINE_STATE_TEXT verdict wording NOT to appear inside "
        "Home's Flight-data row — Home renders its OWN verdict only (B2)")


def test_home_frame_tile_matches_strip_for_the_nightly_held_regression(tmp_path):
    """the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock 02:00
    Europe/Paris): Home's Frame tile and the strip render the SAME clock string, and zero
    warn/error tokens appear anywhere on the page (X2, D-03/CFG-26)"""
    paris = timezone(timedelta(hours=1))
    device_cfg = {
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
    clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
    ctx = {
        "last_checkin_ts": checkin.isoformat(), "device_config": device_cfg,
        "now": clock.isoformat(), "gallery_entries": [],
        "health_state": {"battery_state": "ok", "pipeline_state": "ok"},
        "state_dir": str(tmp_path / "absent" / "nested"),
    }
    rendered = home_page.render(ctx)
    for warn_token in ("dot--warn", "dot--error", "stat-tile--warn", "stat-tile--error"):
        assert warn_token not in rendered, (
            "expected zero %r in a held Home render, found it" % (warn_token,))
    strip_match = re.search(r'time-value time-value--primary">([^<]+)</span>', rendered)
    tile_match = re.search(r'<span class="time-value">([^<]+)</span>', rendered)
    assert strip_match and tile_match, "expected both the strip and the Frame tile to render a clock value"
    assert strip_match.group(1) == tile_match.group(1), (
        "expected the SAME clock string in the strip and the Frame tile, got %r vs %r"
        % (strip_match.group(1), tile_match.group(1)))
    assert home_page.FRAME_STATE_TEXT["off"] in rendered, (
        "expected the held Frame tile's own neutral verdict text")


def test_home_frame_tile_flips_to_late_together_with_the_strip(tmp_path):
    """a late frame flips the strip to 'Expected since'/dot--warn and Home's Frame tile to its
    own late verdict/stat-tile--warn together, at the same threshold — they cannot disagree
    because neither computes anything the other does not (X2)"""
    device_cfg = {"wake_interval_s": 900, "display_enabled": True}
    ctx = {
        "last_checkin_ts": "2026-08-27T11:00:00+00:00", "device_config": device_cfg,
        "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
        "health_state": {"battery_state": "ok", "pipeline_state": "ok"},
        "state_dir": str(tmp_path / "absent" / "nested"),
    }
    rendered = home_page.render(ctx)
    assert "Expected since" in rendered, "expected the strip's own late headline"
    assert "dot--warn" in rendered, "expected the strip's own warn dot for a late frame"
    assert home_page.FRAME_STATE_TEXT["warn"] in rendered, "expected the Frame tile's own late verdict text"
    assert "stat-tile stat-tile--warn" in rendered, "expected the Frame tile's own warn border class"


def test_home_flight_data_tile_one_verdict_verdict_free_detail(tmp_path):
    """Home's Flight-data tile renders exactly one verdict (its own DATA_STATE_TEXT) with
    Health's verdict-free pipeline_detail_html beneath it, never Health's own
    PIPELINE_STATE_TEXT verdict sentence a second time (B2)"""
    ctx = {
        "health_state": {
            "device_state": "ok", "pipeline_state": "warn", "battery_state": "ok",
            "device_detail_html": '<span class="mono">14:00 (5m ago)</span>',
            "pipeline_html": (
                '<p>%s</p><p>10 Sep 23:58 (1d ago)</p>' % health_page.PIPELINE_STATE_TEXT["warn"]),
            "pipeline_detail_html": '<span class="mono">10 Sep 23:58 (1d ago)</span>',
        },
        "device_config": {}, "state_dir": str(tmp_path / "absent" / "nested"),
        "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
    }
    rendered = home_page.render(ctx)
    assert rendered.count(home_page.DATA_STATE_TEXT["warn"]) == 1, (
        "expected Home's own Flight-data verdict exactly once")
    assert health_page.PIPELINE_STATE_TEXT["warn"] not in rendered, (
        "expected Health's own pipeline verdict text NOT to appear on Home — re-embedding it "
        "is the exact double-verdict stacking B2 removes")
    assert "10 Sep 23:58" in rendered, "expected the verdict-free pipeline_detail_html's own timestamp to render"


def test_home_recent_flights_use_display_airline_name_matching_flights(tmp_path):
    """a recent-flight row whose stored airline is an alias ("CCM Airlines") renders the SAME
    display name ("Air Corsica") Flights shows via display_airline_name(), never the raw
    upstream string (X4)"""
    with history_db.open_db(tmp_path) as conn:
        history_db.record_runway_event(
            conn, ts="2026-08-27T11:50:00+00:00", hex="3c6444", callsign="CCM123",
            airline="CCM Airlines", origin="ORY", destination="AJA",
            confirmed_state="departing")
    ctx = {
        "state_dir": str(tmp_path), "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
        "health_state": {}, "device_config": {},
    }
    rendered = home_page.render(ctx)
    assert "Air Corsica" in rendered, "expected the aliased display name 'Air Corsica' on Home"
    assert "CCM Airlines" not in rendered, "expected the raw upstream airline string not to leak onto Home"


def test_home_exactly_one_element_named_frame(tmp_path):
    """exactly one element on a rendered Home page is named 'Frame' (the shared strip's own
    heading) — Home's tile caption is renamed to resolve the X4 collision"""
    ctx = {
        "health_state": {}, "device_config": {}, "state_dir": str(tmp_path / "absent" / "nested"),
        "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
    }
    rendered = home_page.render(ctx)
    assert rendered.count(">Frame<") == 1, (
        "expected exactly one element named 'Frame' (the strip's own heading), got %d"
        % (rendered.count(">Frame<"),))
    assert home_page.FRAME_ROW_LABEL != "Frame", (
        "expected the tile caption to be renamed away from 'Frame' (X4 collision)")
    assert home_page.FRAME_ROW_LABEL in rendered, "expected the renamed tile caption to still render"


def test_home_recent_flight_time_one_line_no_mono_class(tmp_path):
    """the recent-flight time cell markup carries no monospace class, and reads the clock
    (.time-value), the existing .cell-inline-sep middle dot and the relative age
    (.time-value__age) as one line (B18)"""
    with history_db.open_db(tmp_path) as conn:
        history_db.record_runway_event(
            conn, ts="2026-08-27T11:35:00+00:00", hex="3c6444", callsign="AFR1380",
            airline="Air France", origin="ORY", destination="TLS",
            confirmed_state="departing")
    ctx = {
        "state_dir": str(tmp_path), "now": "2026-08-27T12:00:00+00:00", "gallery_entries": [],
        "health_state": {}, "device_config": {},
    }
    rendered = home_page.render(ctx)
    start = rendered.index('class="recent-flight__time')
    end = rendered.index("</li>", start)
    time_cell = rendered[start:end]
    assert "mono" not in time_cell, "expected no monospace class in the recent-flight time cell"
    assert 'class="time-value"' in time_cell, "expected the clock to carry the .time-value role"
    assert 'class="cell-inline-sep"' in time_cell, "expected the existing .cell-inline-sep middle dot"
    assert 'class="time-value__age"' in time_cell, "expected the relative age in the .time-value__age muted role"


# --- CSS-only checks: the served stylesheet's parsed rules, never a disk
# read (TST-12) -----------------------------------------------------------

def test_home_status_grid_declares_align_items_stretch(served_css):
    """.home-status-grid's own CSS rule declares align-items: stretch (B2)"""
    decls = declarations_for(served_css, ".home-status-grid")
    assert decls.get("align-items") == "stretch", (
        "expected .home-status-grid to declare align-items: stretch, got %r" % (decls,))


def test_recent_flight_time_declares_white_space_nowrap(served_css):
    """.recent-flight__time's own CSS rule declares white-space: nowrap so the clock/age pair
    can never wrap onto a second line (B18)"""
    decls = declarations_for(served_css, ".recent-flight__time")
    assert decls.get("white-space") == "nowrap", (
        "expected .recent-flight__time to declare white-space: nowrap, got %r" % (decls,))


def test_recent_flight_thumbnails_share_the_shipped_treatments(served_css):
    """the real recent-flight thumbnail joins the shared white-backing/hairline/radius rule and
    the placeholder's own rule reuses .airline-card__placeholder's exact dashed/canvas-fill
    values (never a new literal, never sharing that pinned selector), so a missing thumbnail
    matches the real ones in weight (B18)"""
    shared_rules = rules_with_selector(served_css, "img.recent-flight__thumb")
    assert any(".now-showing__image" in rule.selectors for rule in shared_rules), (
        "expected img.recent-flight__thumb to join the shared white-backing/hairline/radius "
        "rule .now-showing__image already carries")

    # .airline-card__placeholder's own selector stays standalone —
    # companion/test_status_pages.py (a sibling harness this plan may not
    # edit) pins it as such.
    placeholder_owner_rules = rules_with_selector(served_css, ".airline-card__placeholder")
    assert len(placeholder_owner_rules) == 1 and placeholder_owner_rules[0].selectors == (
        ".airline-card__placeholder",), (
        "expected .airline-card__placeholder's OWN selector to stay standalone, got %r"
        % (placeholder_owner_rules,))
    placeholder_decls = declarations_for(served_css, ".recent-flight__thumb--placeholder")
    airline_card_decls = dict(placeholder_owner_rules[0].declarations)
    for prop in ("border", "background"):
        assert placeholder_decls.get(prop) == airline_card_decls.get(prop), (
            "expected .recent-flight__thumb--placeholder's own rule to reuse "
            ".airline-card__placeholder's exact %r value (%r), got %r (B18)"
            % (prop, airline_card_decls.get(prop), placeholder_decls.get(prop)))


# NOTE: "companion/static/style.css still carries exactly one @supports
# selector(:has(*)) block" (the original harness's next check) is NOT
# ported here — it is IDENTICAL to
# companion/test_companion_app_03.py::test_style_css_carries_exactly_one_has_feature_query_block
# (same served stylesheet, same claim, same F-01-sanctioned served-text
# exception for a property css_rules()'s at_rules tuples cannot express).
# The ledger fragment points this row at that existing test rather than
# duplicating it (33-MIGRATION-RULES.md section 3).


def test_home_catalog_keys_all_present_in_merged_catalog():
    """every key in companion/i18n_fr/home.py's own CATALOG is also a key of the merged
    companion.i18n_fr.CATALOG, proving the auto-merge package picked the module up"""
    import companion.i18n_fr as i18n_fr
    import companion.i18n_fr.home as i18n_fr_home
    missing = [k for k in i18n_fr_home.CATALOG if k not in i18n_fr.CATALOG]
    assert not missing, "keys missing from the merged CATALOG: %r" % (missing,)


def test_home_full_render_has_quick_action_only_inside_strip_and_three_tiles(tmp_path):
    """a rendered Home page carries no status-card__rows/home-hero markup, quick-action markup
    only inside .frame-strip (exactly two cells) and nowhere else, exactly three stat-tile
    elements labelled Frame/Battery/Flight data, and the Frame verdict sentence exactly once
    (D-04/D-05)"""
    ctx = {
        "health_state": {"device_state": "ok", "pipeline_state": "ok", "battery_state": "ok"},
        "device_config": {}, "state_dir": str(tmp_path / "absent" / "nested"),
        "now": "2026-08-27T12:00:00+00:00",
    }
    rendered = home_page.render(ctx)
    assert "status-card__rows" not in rendered and "home-hero" not in rendered, (
        "expected no status-card__rows or home-hero markup on the rebuilt Home page")
    strip_start = rendered.index('class="frame-strip stat-tile stat-tile--accent"')
    tiles_start = rendered.index('class="dashboard-grid home-status-grid"')
    outside_strip = rendered[:strip_start] + rendered[tiles_start:]
    assert "quick-action" not in outside_strip, "expected no quick-action markup anywhere outside .frame-strip"
    strip_segment = rendered[strip_start:tiles_start]
    on_off_count = strip_segment.count("quick-action--on") + strip_segment.count("quick-action--off")
    assert on_off_count == 2, (
        "expected exactly two quick-action--on/off cells inside .frame-strip, got %d" % on_off_count)
    assert rendered.count('class="stat-tile ') == 3, (
        "expected exactly three stat-tile elements, got %d" % (rendered.count('class="stat-tile '),))
    for label in (home_page.FRAME_ROW_LABEL, home_page.BATTERY_ROW_LABEL, home_page.DATA_ROW_LABEL):
        assert label in rendered, "expected the %r tile label" % (label,)
    assert rendered.count(home_page.FRAME_STATE_TEXT["ok"]) == 1, (
        "expected the Frame state sentence to appear exactly once — the duplicated-verdict regression test")


def test_home_status_card_headline_next_update_or_expected_since(tmp_path):
    """the Frame strip's headline reads 'Next update ≈ HH:MM' for a future next-update,
    'Expected since HH:MM' in the warn treatment for a past one, and renders no headline at all
    when either the check-in or the wake interval is unknown (D-01, moved from the deleted
    _status_card_html())"""
    base_ctx = {
        "device_config": {"wake_interval_s": 900, "display_enabled": True},
        "health_state": {}, "state_dir": str(tmp_path / "absent" / "nested"),
    }

    def _strip_html(ctx):
        next_wake_iso = wake.next_wake_at_iso(ctx.get("last_checkin_ts"), ctx.get("device_config"))
        return layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE, next_wake_iso=next_wake_iso)

    future_ctx = dict(
        base_ctx, last_checkin_ts="2026-08-27T11:55:00+00:00", now="2026-08-27T12:00:00+00:00")
    rendered_future = _strip_html(future_ctx)
    # 11:55 UTC + 15 minutes = 12:10 UTC = 14:10 Europe/Paris (CEST,
    # UTC+2, in effect in late August) — still AFTER the 12:00 UTC "now",
    # so this is the not-yet-due branch. The clock is its own
    # <span class="time-value time-value--primary"> element, so "Next
    # update ≈ 14:10" is not one contiguous substring — checked as two.
    assert "Next update ≈" in rendered_future and "14:10" in rendered_future, (
        "expected the future next-update headline")
    assert "status-card__headline--warn" not in rendered_future, "expected no warn modifier for a future next-update"

    past_ctx = dict(
        base_ctx, last_checkin_ts="2026-08-27T11:00:00+00:00", now="2026-08-27T12:00:00+00:00")
    rendered_past = _strip_html(past_ctx)
    # 11:00 UTC + 15 minutes = 11:15 UTC, already BEFORE the 12:00 UTC
    # "now" — the overdue, warn-treatment branch.
    assert "Expected since" in rendered_past, "expected the overdue headline wording"
    assert "status-card__headline--warn" in rendered_past, "expected the warn modifier for an overdue next-update"

    missing_checkin = dict(base_ctx, last_checkin_ts=None, now="2026-08-27T12:00:00+00:00")
    assert "status-card__headline" not in _strip_html(missing_checkin), (
        "expected no headline at all when there is no check-in yet")
    missing_interval = dict(
        base_ctx, device_config={}, last_checkin_ts="2026-08-27T11:55:00+00:00",
        now="2026-08-27T12:00:00+00:00")
    assert "status-card__headline" not in _strip_html(missing_interval), (
        "expected no headline at all when the wake interval is unknown")


def test_home_status_card_always_shows_health_link(tmp_path):
    """a default Home render always carries the status tiles section's 'See details on Health'
    link (D-17, moved to _status_tiles_html() after _status_card_html()'s deletion)"""
    ctx = {
        "health_state": {}, "device_config": {},
        "state_dir": str(tmp_path / "absent" / "nested"), "now": "2026-08-27T12:00:00+00:00",
    }
    rendered = home_page._status_tiles_html(ctx)
    assert home_page.HEALTH_LINK_TEXT in rendered, "expected the Health link to always render (D-17)"


def test_home_page_render_degrades_with_nothing():
    """home_page.render({}) degrades to its empty states without raising, battery.battery_percent()
    clamps and rejects bad input, and the gallery filename parser round-trips or returns None"""
    rendered = home_page.render({})
    for needle in (home_page.NO_FLIGHTS_HEADING, home_page.NO_PANEL_HEADING, home_page.NO_READING_TEXT):
        assert needle in rendered, "expected %r for an empty ctx" % needle
    assert (
        battery.battery_percent(battery.BATTERY_FULL_MV) == 100
        and battery.battery_percent(4200) == 100
        and battery.battery_percent(battery.BATTERY_EMPTY_MV) == 0
        and battery.battery_percent(2900) == 0), (
        "expected the percentage estimate to clamp at BATTERY_FULL_MV/4200 -> 100 and "
        "BATTERY_EMPTY_MV/2900 -> 0 (SEED-006 curve endpoints)")
    assert battery.battery_percent("x") is None and battery.battery_percent(0) is None, (
        "expected a non-numeric or zero reading to yield None")
    assert home_page._gallery_name_to_iso("2026-09-10T21-38-48+00-00.png") == "2026-09-10T21:38:48+00:00", (
        "expected the gallery filename to round-trip to its ISO timestamp")
    assert home_page._gallery_name_to_iso("junk.png") is None and home_page._gallery_name_to_iso(None) is None, (
        "expected an unparseable gallery name to yield None")


def test_battery_percent_moved_out_of_home_page():
    """battery_percent() no longer exists on home_page after moving to companion/battery.py (D-01)"""
    assert not hasattr(home_page, "battery_percent"), (
        "expected home_page.battery_percent to be gone after the D-01 move")
