"""Companion view-page tests, last slice: Home's French render, the status
card's localised timestamps, the Frame/Flight-data tile verdicts, Home's
degrade-with-nothing contracts, the day band's contracts, and the hero
composition's shared draw.py emitters.

Every check calls `home_page.render()` directly, or drives a real
`companion/app.py` over HTTP; CSS checks assert on it structurally.
"""
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone

import pytest

import companion.battery as battery
import companion.draw as draw
import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.layout as layout
import companion.prefs as prefs
import companion.test_view_pages_helpers as vp
import companion.wake as wake
from companion.pages import airlines_page, health_page, history_page, home_page
from companion_app_server import get, login, served_stylesheet
from companion_markup import declarations_for, parse_html, rules_with_selector
from server import device_config, history_db
from skypane_test_support import REPO_ROOT, child_env

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

# An arbitrary, fixed epoch second standing in for a Paris midnight — the
# scale under test is pure arithmetic on two numbers in the same unit, so
# nothing here needs a real timezone (companion/draw.py may not import the
# server package, where the one Paris-day conversion lives).
_BAND_DAY_START = 1756000000


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's CSS-only checks
    fetch the served stylesheet from, instead of opening it from disk
    ."""
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


# --- Home's fully-seeded French render ----------

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
    wording"""
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
    warn/error tokens appear anywhere on the page (X2)"""
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
# read -----------------------------------------------------------

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
    """
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
    when either the check-in or the wake interval is unknown (moved from the deleted
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
    link (moved to _status_tiles_html() after _status_card_html()'s deletion)"""
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
    """battery_percent() no longer exists on home_page after moving to companion/battery.py"""
    assert not hasattr(home_page, "battery_percent"), (
        "expected home_page.battery_percent to be gone after the D-01 move")


# --- Task 1 : the day band's own time domain -----

def test_day_band_time_scale_places_by_when_not_by_index():
    """draw.percent_time() is a TIME scale and not the index scale beside it: midnight/midday/
    the day's final instant land at 0/50/100%, an hour is 1/24 of the band however many other
    instants are on it (so an outage draws as an outage), a DST day's own length is a parameter
    rather than a hardcoded 86400, and an instant outside the day is REJECTED rather than
    clamped onto an edge where it would invent a check-in"""
    day = draw.SECONDS_PER_DAY
    # Midnight, midday, and the day's own final instant.
    for offset, expected in ((0, 0.0), (day / 2.0, 50.0), (day, 100.0)):
        got = draw.percent_time(_BAND_DAY_START + offset, _BAND_DAY_START)
        assert got is not None and abs(got - expected) <= 1e-9, (
            "expected %+.1fs into the day at %.1f%%, got %r" % (offset, expected, got))
    # Outside the day is REJECTED, never positioned. A clamped instant
    # would put yesterday's check-in at this band's midnight and make
    # today's drawing claim a check-in that never happened .
    for outside in (_BAND_DAY_START - 1, _BAND_DAY_START + day + 1):
        assert draw.percent_time(outside, _BAND_DAY_START) is None, (
            "expected an instant outside the day to be rejected, got %r for %r"
            % (draw.percent_time(outside, _BAND_DAY_START), outside))
    # Totality, because these numbers arrive from stored text.
    for hostile in (None, True, float("nan"), float("inf"), "12:00", [], {}):
        assert draw.percent_time(hostile, _BAND_DAY_START) is None, (
            "expected %r as an instant to be rejected" % (hostile,))
        assert draw.percent_time(_BAND_DAY_START, hostile) is None, (
            "expected %r as a day start to be rejected" % (hostile,))
    assert draw.percent_time(_BAND_DAY_START, _BAND_DAY_START, 0) is None, (
        "expected a zero-length day to be rejected rather than divided by")

    # A Europe/Paris day is 23 or 25 hours twice a year, so the day's
    # length is a parameter and an hour is a share of THAT day, not of a
    # hardcoded 86400.
    short = draw.percent_time(_BAND_DAY_START + 3600, _BAND_DAY_START, 23 * 3600)
    assert short is not None and abs(short - 100.0 / 23) <= 1e-9, (
        "on a 23-hour DST day an hour should be %.4f%% of the band, got %r" % (100.0 / 23, short))

    # THE PROPERTY AN INDEX SCALE DOES NOT HAVE: the distance between two
    # instants an hour apart is the same 1/24 of the band however many
    # other instants are on it. Measured off the drawn band, not off the
    # helper, because the band is what a reader sees.
    hour_percent = 100.0 / 24
    seen = []
    for fillers in ([], [_band_hour(h) for h in (0, 2, 4, 6, 20, 22)]):
        instants = fillers + [_band_hour(8), _band_hour(9)]
        markup, collapsed = draw.day_band(_BAND_DAY_START, day, instants)
        assert not collapsed, (
            "expected no collapsing in a %d-instant series spaced two hours apart, got %d"
            % (len(instants), collapsed))
        marks = [_band_percent(el, "x") for el in _band_shapes(markup, "drawing-band-mark")]
        assert len(marks) == len(instants), (
            "expected one mark per instant (%d), got %d" % (len(instants), len(marks)))
        eight = min(marks, key=lambda p: abs(p - 8 * hour_percent))
        nine = min(marks, key=lambda p: abs(p - 9 * hour_percent))
        seen.append((len(instants), eight, nine))
        assert abs(eight - 8 * hour_percent) <= 0.02, (
            "with %d instants on the band, the 08:00 check-in is drawn at %.2f%% instead of "
            "%.2f%% — that is an INDEX position, not a time position (under draw.percent_x() "
            "it would sit at %.2f%%)" % (
                len(instants), eight, 8 * hour_percent,
                draw.percent_x(sorted(instants).index(_band_hour(8)), len(instants))))
        assert abs((nine - eight) - hour_percent) <= 0.02, (
            "with %d instants on the band, an hour measures %.2f%% of it instead of %.2f%% — "
            "an index scale distributes points evenly whenever they happened, so a six-hour "
            "outage would draw as one ordinary step" % (len(instants), nine - eight, hour_percent))
    assert abs(seen[0][1] - seen[1][1]) <= 0.02 and abs(seen[0][2] - seen[1][2]) <= 0.02, (
        "the same two instants landed at different positions on a 2-instant band %r and an "
        "8-instant band %r — a time scale places an instant by WHEN it happened and nothing "
        "else" % (seen[0][1:], seen[1][1:]))


def test_day_band_night_window_shades_the_night_as_two_spans():
    """the day band renders a wrapping night window (22:00-07:00) as TWO shaded spans covering
    nine hours, one flush to 00:00 and one flush to 24:00 with midday left clear — never one
    inverted span that would shade the middle of the day — while a daytime window stays one
    span and an absent/zero-width/out-of-day/malformed window shades nothing at all"""
    day = draw.SECONDS_PER_DAY
    hour_percent = 100.0 / 24

    # 22:00-07:00 — a NIGHT window, which is what quiet hours normally
    # is, not an edge case.
    markup, _ = draw.day_band(_BAND_DAY_START, day, [], window=(_band_hour(22), _band_hour(7)))
    spans = _band_shapes(markup, "drawing-band-span")
    assert len(spans) == 2, (
        "expected a 22:00-07:00 window to shade TWO spans on a one-day band, got %d — one span "
        "from 22:00 back to 07:00 has a negative width, and the obvious repair (swap them) "
        "shades the whole DAY and leaves the night clear, which looks entirely plausible"
        % (len(spans),))
    widths = [_band_percent(el, "width") for el in spans]
    starts = [_band_percent(el, "x") for el in spans]
    assert None not in widths and None not in starts, "expected every span to carry percentage x/width"
    assert abs(sum(widths) - 9 * hour_percent) <= 0.02, (
        "expected the two spans to cover nine hours (%.2f%%), got %.2f%% — %r"
        % (9 * hour_percent, sum(widths), list(zip(starts, widths))))
    assert abs(min(starts)) <= 1e-9, "expected the leading span to start at the band's own 00:00"
    ends = [s + w for s, w in zip(starts, widths)]
    assert abs(max(ends) - 100.0) <= 0.02, "expected the trailing span to reach the band's own 24:00"
    # And the middle of the day is NOT shaded: the failure this check
    # exists for is a band that shades 07:00-22:00.
    for start, width in zip(starts, widths):
        assert not (start < 12 * hour_percent < start + width), (
            "midday falls inside a shaded span (%.2f%%..%.2f%%) — the night window has been "
            "rendered inverted" % (start, start + width))

    # A daytime window is ONE span, so "always two" is not the fix.
    markup, _ = draw.day_band(_BAND_DAY_START, day, [], window=(_band_hour(9), _band_hour(17)))
    spans = _band_shapes(markup, "drawing-band-span")
    assert len(spans) == 1, "expected a 09:00-17:00 window to shade exactly one span, got %d" % (len(spans),)
    assert abs(_band_percent(spans[0], "x") - 9 * hour_percent) <= 0.02, (
        "expected the span to start at 09:00, got %r" % (spans[0],))
    assert abs(_band_percent(spans[0], "width") - 8 * hour_percent) <= 0.02, (
        "expected the span to be eight hours wide, got %r" % (spans[0],))

    # No window, a zero-width window and a window outside the day all
    # shade nothing. A zero-width window is never ACTIVE
    # (server/device_config.py's seconds_until_quiet_hours_end() says so
    # in as many words), so a hairline of shade would claim a window the
    # device does not honour.
    for label, window in (
            ("absent", None),
            ("zero-width", (_band_hour(9), _band_hour(9))),
            ("outside the day", (_BAND_DAY_START - 7200, _band_hour(7))),
            ("malformed", ("23:00", "07:00")),
            ("not a pair", 3)):
        markup, _ = draw.day_band(_BAND_DAY_START, day, [], window=window)
        spans = _band_shapes(markup, "drawing-band-span")
        assert not spans, "expected a %s window to shade nothing, got %r" % (label, spans)
        assert len(_band_shapes(markup, "drawing-band")) == 1, (
            "expected the band's own frame to survive a %s window" % (label,))


def test_day_band_collapses_crowded_marks_and_reports_exactly_how_many():
    """the day band collapses marks closer than its own stated minimum spacing and returns
    EXACTLY how many it hid — 48 marks at a 30-minute cadence with nothing collapsed, a
    60-second and a 1-second cadence both bounded by the band's width rather than the row
    count, no two kept marks under the minimum apart, and an unplaceable instant
    counted too so a caption built from the number can never claim a total the drawing does
    not reach"""
    day = draw.SECONDS_PER_DAY
    spacing = draw.DAY_BAND_MIN_MARK_SPACING_PERCENT
    ceiling = int(100.0 / spacing) + 1

    # A 30-minute cadence is 48 marks in the band's ~330px at the 360px
    # floor — about 7px apart, which is drawable. Nothing is collapsed
    # and the caller may caption the exact number.
    sparse = [_BAND_DAY_START + 1800 * i for i in range(48)]
    markup, collapsed = draw.day_band(_BAND_DAY_START, day, sparse)
    marks = _band_shapes(markup, "drawing-band-mark")
    assert len(marks) == 48 and collapsed == 0, (
        "expected 48 marks and 0 collapsed at a 30-minute cadence, got %d and %d"
        % (len(marks), collapsed))

    # A 60-second cadence is 1440 marks in the same 330px. Drawing them
    # all would let the reader believe the band shows 1440 things; the
    # emitter collapses and SAYS how many.
    for cadence, total in ((60, 1440), (1, 86400)):
        instants = [_BAND_DAY_START + cadence * i for i in range(total)]
        markup, collapsed = draw.day_band(_BAND_DAY_START, day, instants)
        marks = _band_shapes(markup, "drawing-band-mark")
        assert len(marks) + collapsed == total, (
            "at a %ds cadence %d marks + %d collapsed != the %d instants supplied — the number "
            "the caption is written from has to be exact" % (cadence, len(marks), collapsed, total))
        assert len(marks) <= ceiling, (
            "at a %ds cadence the band drew %d marks, over the %d its own minimum spacing "
            "allows — T-24-06-C is that the element count is bounded by the band's WIDTH, "
            "never by the row count" % (cadence, len(marks), ceiling))
        positions = [_band_percent(el, "x") for el in marks]
        assert positions == sorted(positions), (
            "expected the kept marks in chronological order, got %r" % (positions[:8],))
        tight = [(a, b) for a, b in zip(positions, positions[1:]) if b - a < spacing - 0.011]
        assert not tight, (
            "at a %ds cadence two kept marks sit %.2f%% apart, under the %.2f%% minimum — they "
            "would paint as one smear and the band would show fewer things than it appears to"
            % (cadence, tight[0][1] - tight[0][0], spacing))
        # THE LOWER BOUND, and the half of this check the three
        # assertions above cannot see. They are all CEILINGS — at most
        # `ceiling` marks, none closer than the minimum — and every one
        # of them is satisfied perfectly by a band that draws ONE mark at
        # 00:00 and nothing else. Both assertions below are consequences
        # of the greedy rule rather than chosen thresholds: a candidate
        # lying a full minimum-spacing past the last kept mark is kept BY
        # DEFINITION, so neither an interior gap nor the unmarked tail at
        # the band's end can reach the minimum plus one cadence step.
        # The 0.011 allowance matches the `tight` assertion above and is
        # not slack in the rule: positions are read off the drawing, and
        # an x attribute carries two decimals.
        step_percent = cadence / float(day) * 100
        last_instant = (instants[-1] - _BAND_DAY_START) / float(day) * 100
        assert last_instant - positions[-1] < spacing + 0.011, (
            "at a %ds cadence the kept marks stop at %.2f%% while the instants run to %.2f%% — "
            "a tail of %.2f%% carrying %d check-ins drew nothing, though the greedy rule keeps "
            "anything a full %.2f%% past the last kept mark. The band would say the device "
            "stopped checking in" % (
                cadence, positions[-1], last_instant, last_instant - positions[-1],
                int((last_instant - positions[-1]) / step_percent), spacing))
        slack = [(a, b) for a, b in zip(positions, positions[1:])
                 if b - a > spacing + step_percent + 0.011]
        assert not slack, (
            "at a %ds cadence two kept marks sit %.2f%% apart, over the %.2f%% the greedy rule "
            "allows — instants that had room for a mark of their own were dropped, so the band "
            "shows a gap where the device was checking in normally"
            % (cadence, slack[0][1] - slack[0][0], spacing + step_percent))

    # An instant the band cannot place counts as not-individually-visible
    # too, so a caller captioning from this number can never name a
    # total the drawing does not reach.
    mixed = [_BAND_DAY_START, _BAND_DAY_START - 60, "not a number", None,
             _BAND_DAY_START + day // 2]
    markup, collapsed = draw.day_band(_BAND_DAY_START, day, mixed)
    marks = _band_shapes(markup, "drawing-band-mark")
    assert len(marks) == 2 and collapsed == 3, (
        "expected 2 marks and 3 unplaceable instants reported, got %d and %d" % (len(marks), collapsed))
    # Every mark is centred on its instant rather than hung to the right
    # of it: a 23:59 mark whose LEFT edge were the instant would sit
    # entirely outside the canvas.
    offset = -draw.DAY_BAND_MARK_WIDTH_PX / 2.0
    for element in marks:
        assert _band_attr(element, "transform") == "translate(%.2f 0)" % offset, (
            "expected every mark centred on its instant, got %r" % (element,))

    markup, collapsed = draw.day_band(_BAND_DAY_START, day, 17)
    assert collapsed == 0 and not _band_shapes(markup, "drawing-band-mark"), (
        "expected a non-iterable series to draw no marks and report 0")


def test_day_band_emits_only_registered_classes_and_no_colour():
    """every class the day band emits is one of companion/draw.py's own named constants and is
    registered in DRAWING_CLASSES (so the stylesheet-resolution guard can see it), the markup
    carries no colour literal, no url() reference and no inline style, and a band supplied
    with a label announces itself as a named group rather than being hidden"""
    markup, _ = draw.day_band(
        _BAND_DAY_START, draw.SECONDS_PER_DAY,
        [_band_hour(h) for h in (1, 5, 9, 13, 17, 21)],
        window=(_band_hour(23), _band_hour(7)), label="the day")
    for constant in (draw.DRAWING_BAND_CLASS, draw.DRAWING_BAND_SPAN_CLASS, draw.DRAWING_BAND_MARK_CLASS):
        assert constant in draw.DRAWING_CLASSES, (
            "the band's class %r is not in draw.DRAWING_CLASSES, so the guard that every "
            "emitted class resolves to a real selector cannot see it — a class that exists in "
            "Python and nowhere in CSS paints nothing at all" % (constant,))
    for class_name in re.findall(r'class="([^"]*)"', markup):
        for token in class_name.split():
            assert token in draw.DRAWING_CLASSES, (
                "the band emitted class %r, which is not one of draw.py's own named constants" % (token,))
    for forbidden in ("url(", "#", "rgb(", "style=", "<linearGradient"):
        assert forbidden not in markup, (
            "the band's markup carries %r — a colour decided in Python is correct in one theme "
            "only, and an external reference is banned outright" % (forbidden,))
    assert 'role="group"' in markup and 'aria-label="the day"' in markup, (
        "expected a labelled band: it is the only statement of its data, so it is not "
        "aria-hidden the way the ring beside its own printed percentage is")
    unlabelled, _ = draw.day_band(_BAND_DAY_START, draw.SECONDS_PER_DAY, [])
    assert 'aria-hidden="true"' in unlabelled, "expected an unlabelled band to be hidden rather than an unnamed group"


# --- Task 2 : the day band on Home ----------------

def test_home_day_band_renders_the_day_and_says_what_it_shows(tmp_path):
    """Home's day band draws one mark per check-in at its PARIS clock position, captions the
    Paris day it shows and states the count as text; a day with no check-ins still renders the
    band and its frame with a caption naming the day (an absent section would read as an
    unbuilt feature, an empty band reads as no activity); and with history.db unreadable the
    page renders with no band at all rather than an empty one claiming no check-ins (
    )"""
    # Paris 14:00 on 2026-08-27 (CEST, UTC+2), so the band's day runs
    # 2026-08-26T22:00Z .. 2026-08-27T22:00Z.
    now = "2026-08-27T12:00:00+00:00"
    # 08:00, 12:00 and 13:00 Paris — two of them an hour apart, so the
    # time scale's own property is visible on the real page and not only
    # in the unit check above.
    ctx = _home_band_ctx(tmp_path / "day", now, [
        "2026-08-27T06:00:00+00:00",
        "2026-08-27T10:00:00+00:00",
        "2026-08-27T11:00:00+00:00",
    ])
    rendered = home_page.render(ctx)
    section = _home_day_band_section(rendered)
    assert section is not None, "expected a day-band section on Home, got none"
    marks = _home_band_marks(section)
    assert len(marks) == 3, "expected one mark per check-in (3), got %d" % (len(marks),)
    xs = sorted(float(re.search(r'x="([\d.]+)%"', el).group(1)) for el in marks)
    hour = 100.0 / 24
    for got, want_hour in zip(xs, (8, 12, 13)):
        assert abs(got - want_hour * hour) <= 0.02, (
            "expected the %02d:00 Paris check-in at %.2f%%, got %.2f%% — the band's marks are "
            "placed by the PARIS clock, which is what every other date on this page uses"
            % (want_hour, want_hour * hour, got))
    # The caption names the day it is showing. A band captioned only
    # "today" cannot be checked against the row beneath it.
    assert "2026-08-27" in section, "expected the caption to name the Paris day it draws, got %r" % (section,)
    assert "3" in re.sub(r"<[^>]*>", " ", section), "expected the caption to state the check-in count as text"

    # THE EMPTY DAY IS A STATE, NOT AN ABSENCE.
    empty_ctx = _home_band_ctx(tmp_path / "empty", now, [])
    # A check-in on a DIFFERENT day, so the table is not empty and the
    # emptiness is the band's bucketing rather than an unreadable
    # database.
    with history_db.open_db(tmp_path / "empty") as conn:
        history_db.record_device_health(conn, "2026-08-20T10:00:00+00:00", battery_mv=3700)
    rendered_empty = home_page.render(empty_ctx)
    empty_section = _home_day_band_section(rendered_empty)
    assert empty_section is not None, (
        "expected the band section to survive a day with no check-ins — an absent section "
        "reads as an unbuilt feature, an empty band reads as no activity, and those are "
        "different statements")
    assert not _home_band_marks(empty_section), (
        "expected no marks on an empty day, got %r" % (_home_band_marks(empty_section),))
    assert 'class="drawing-band"' in empty_section, "expected the band's own frame to render on an empty day"
    assert "2026-08-27" in empty_section, "expected the empty band's caption to name the day too"

    # THE COLLAPSE, CAPTIONED . The band above drew three
    # well-separated marks and must NOT carry the merge sentence — a
    # caption that always admitted a collapse would be as untrue as one
    # that never did. A day at a one-minute cadence must carry it,
    # because at that density the band genuinely cannot show each
    # check-in separately and a reader counting marks would otherwise
    # conclude it lost some.
    assert home_page.DAY_BAND_COLLAPSED_TEXT not in section, (
        "the band collapsed nothing (3 marks for 3 check-ins) yet its caption said marks were "
        "merged — a caption that always admits a collapse tells the reader nothing and is "
        "untrue on every sparse day")
    minutes = ["2026-08-27T%02d:%02d:00+00:00" % (6 + i // 60, i % 60) for i in range(300)]
    dense_ctx = _home_band_ctx(tmp_path / "dense", now, minutes)
    dense_section = _home_day_band_section(home_page.render(dense_ctx))
    assert dense_section is not None, "expected a band on a dense day"
    dense_marks = _home_band_marks(dense_section)
    assert len(dense_marks) < len(minutes), (
        "expected a one-minute cadence to collapse (300 check-ins cannot be 300 distinguishable "
        "marks in ~330px), got %d marks" % (len(dense_marks),))
    assert home_page.DAY_BAND_COLLAPSED_TEXT in dense_section, (
        "the band drew %d marks for %d check-ins and its caption did not say they were merged "
        "— the drawing dropping marks silently and the caption printing a total are the two "
        "halves of one lie (T-24-06-B)" % (len(dense_marks), len(minutes)))
    dense_text = re.sub(r"<[^>]*>", " ", dense_section)
    assert str(len(minutes)) in dense_text, (
        "expected the true total still printed as TEXT beside the merge sentence — the count "
        "is honest, only the COUNTING of marks is not")

    # NO DATABASE AT ALL: no band, no raise, a page that still renders
    # .
    #
    # The unreadable database is made unreadable by putting a DIRECTORY
    # where history.db belongs, not by chmod: this harness may run as
    # root, where a 0o500 state dir is not read-only at all. sqlite
    # cannot open a directory whoever you are, so this check measures the
    # same degradation in both environments.
    absent = tmp_path / "nodb"
    absent_ctx = _home_band_ctx(absent, now, [])
    for name in os.listdir(str(absent)):
        path = os.path.join(str(absent), name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)
    os.mkdir(os.path.join(str(absent), "history.db"))
    rendered_absent = home_page.render(absent_ctx)
    assert '<h1 class="page-title">' in rendered_absent, "expected Home to render with history.db absent"
    assert _home_day_band_section(rendered_absent) is None, (
        "expected NO band with history.db unreadable — an empty band there would claim the "
        "device made no check-ins when nothing was read")


def test_home_day_band_shades_quiet_hours_only_when_configured(tmp_path):
    """Home's day band shades the CONFIGURED quiet-hours window — the default 23:00-07:00
    wrapping night window as two spans covering its eight hours, named in the caption — and
    with quiet hours disabled shades nothing and says nothing about them, while still drawing
    the day's check-ins"""
    now = "2026-08-27T12:00:00+00:00"
    checkins = ["2026-08-27T10:00:00+00:00"]
    hour = 100.0 / 24
    # The DEFAULT night window, and the case a naive span renders
    # inverted: 23:00-07:00 wraps midnight.
    ctx = _home_band_ctx(tmp_path / "on", now, checkins, config={
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
    })
    section = _home_day_band_section(home_page.render(ctx))
    assert section is not None, "expected a day-band section"
    spans = _home_band_spans(section)
    assert len(spans) == 2, (
        "expected the default 23:00-07:00 quiet hours to shade TWO spans on a one-day band, "
        "got %d — one span would shade the middle of the DAY and leave the night clear"
        % (len(spans),))
    widths = [float(re.search(r'width="([\d.]+)%"', el).group(1)) for el in spans]
    assert abs(sum(widths) - 8 * hour) <= 0.05, (
        "expected the shaded spans to cover the window's eight hours (%.2f%%), got %.2f%%"
        % (8 * hour, sum(widths)))
    text = re.sub(r"<[^>]*>", " ", section)
    assert "23:00" in text and "07:00" in text, "expected the caption to name the shaded window's own hours, got %r" % (text,)

    # DISABLED: nothing shaded, and the caption does not mention a
    # window the device is not honouring.
    off_ctx = _home_band_ctx(tmp_path / "off", now, checkins, config={
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": False,
        "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
    })
    off_section = _home_day_band_section(home_page.render(off_ctx))
    assert off_section is not None, "expected the band to render with quiet hours disabled"
    assert not _home_band_spans(off_section), (
        "expected zero shaded spans with quiet hours disabled, got %r" % (_home_band_spans(off_section),))
    off_text = re.sub(r"<[^>]*>", " ", off_section).lower()
    assert "quiet" not in off_text and "23:00" not in off_text, (
        "expected the band's caption to say nothing about quiet hours when they are off — a "
        "legend for a span that is not drawn describes a band the reader is not looking at. "
        "Got %r" % (off_text,))
    assert _home_band_marks(off_section), "expected the check-in marks to survive quiet hours being off"


def test_home_day_band_buckets_by_paris_day_and_costs_one_read(tmp_path):
    """Home's day band buckets check-ins by the PARIS day — a 22:30Z check-in (Paris 00:30
    today) is on the band and a 2026-08-27T22:30Z one (Paris 00:30 tomorrow) is not, since
    Paris is never behind UTC — and spans a real 25-hour Paris day so midday lands at 52.00%
    rather than the 54.17% a hardcoded 86400 would give; it costs render() exactly one
    history.db read more than the two it made before, measured, and the frame verdict still
    appears exactly once"""
    now = "2026-08-27T12:00:00+00:00"
    # THE BOUNDARY THIS BREAKS AT IF IT BREAKS. Paris is UTC+1/+2 and so
    # never BEHIND UTC. 00:30 Paris is 22:30 UTC on the PREVIOUS day, so
    # a band bucketed by the UTC date drops it from today and picks up
    # tomorrow's 00:30 instead. Both directions below.
    ctx = _home_band_ctx(tmp_path / "boundary", now, [
        "2026-08-26T21:30:00+00:00",  # Paris 2026-08-26 23:30 — yesterday
        "2026-08-26T22:30:00+00:00",  # Paris 2026-08-27 00:30 — TODAY
        "2026-08-27T22:30:00+00:00",  # Paris 2026-08-28 00:30 — tomorrow
    ])
    section = _home_day_band_section(home_page.render(ctx))
    assert section is not None, "expected a day-band section"
    marks = _home_band_marks(section)
    assert len(marks) == 1, (
        "expected exactly ONE of the three check-ins on the 2026-08-27 Paris band, got %d — "
        "under a UTC date bucket the 22:30Z check-in (Paris 00:30 today) drops off and the "
        "2026-08-27T22:30Z one (Paris 00:30 TOMORROW) appears instead, which is the same count "
        "from the wrong rows" % (len(marks),))
    got = float(re.search(r'x="([\d.]+)%"', marks[0]).group(1))
    want = 0.5 * (100.0 / 24)  # 00:30 Paris
    assert abs(got - want) <= 0.02, "expected the 00:30 Paris check-in at %.2f%%, got %.2f%%" % (want, got)

    # A 25-HOUR PARIS DAY. 2026-10-25 is the EU autumn transition, so the
    # band is 25 hours wide and midday sits at 52.00%, not at the 54.17%
    # a hardcoded 86400 would put it at.
    dst_ctx = _home_band_ctx(
        tmp_path / "dst", "2026-10-25T12:00:00+00:00", ["2026-10-25T11:00:00+00:00"])
    dst_section = _home_day_band_section(home_page.render(dst_ctx))
    dst_marks = _home_band_marks(dst_section or "")
    assert len(dst_marks) == 1, "expected one mark on the DST band, got %d" % (len(dst_marks),)
    dst_got = float(re.search(r'x="([\d.]+)%"', dst_marks[0]).group(1))
    assert abs(dst_got - 52.0) <= 0.02, (
        "on the 25-hour Paris day 2026-10-25 the 12:00 check-in belongs at 52.00%% of the "
        "band, got %.2f%% — a hardcoded 86400 puts it at 54.17%% and leaves an hour of the "
        "band unreachable" % (dst_got,))

    # ONE READ, REUSED, MEASURED. render() made two history.db
    # reads before this change; the band adds exactly one, and a band
    # that re-queried per section would show up here as three or more.
    read_ctx = _home_band_ctx(tmp_path / "reads", now, ["2026-08-27T10:00:00+00:00"])
    opened = []
    real_open = history_db.open_db

    def _counting_open(state_dir):
        opened.append(state_dir)
        return real_open(state_dir)

    history_db.open_db = _counting_open
    try:
        rendered = home_page.render(read_ctx)
    finally:
        history_db.open_db = real_open
    assert len(opened) == 3, (
        "expected render() to make exactly 3 history.db reads — the 2 it made before this "
        "change (recent flights, latest battery) plus the band's one — got %d. 'One read, "
        "reused' is measured here, not assumed" % (len(opened),))
    # The frame verdict still appears exactly once on the page
    # (_status_tiles_html()'s own recorded property, which a new section
    # carrying a state word could quietly break).
    verdicts = [v for v in home_page.FRAME_STATE_TEXT.values() if rendered.count(v)]
    for verdict in verdicts:
        assert rendered.count(verdict) == 1, (
            "expected the frame verdict %r exactly once on Home, got %d" % (verdict, rendered.count(verdict)))
    assert len(verdicts) == 1, "expected exactly one frame verdict rendered on Home, got %r" % (verdicts,)


# --- Task 1 : D4's hero, assembled from calls -----

def test_home_top_is_one_composition_holding_the_ring_and_the_band(tmp_path):
    """Home's top is ONE composition: a single hero container holds the shared Frame strip
    (rendered once, unforked), the three status tiles carrying the battery ring, and the day
    band — the picture row stays outside it, the ring and the band each appear exactly once
    and both inside the hero, and the frame verdict still appears exactly once in BOTH
    languages

    The legacy check also walked companion/pages/home_page.py's own source with
    inspect.getsource() to prove it names no battery-arithmetic literal and no bare
    battery_percent( call — banned outright by guard G2 (no ast/inspect/tokenize over
    production source), and with no directly observable HTTP/DOM consequence beyond what is
    already proven behaviourally: test_battery_percent_moved_out_of_home_page above proves
    home_page carries no local battery_percent() at all, and
    test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from below
    proves — by mutating the shared emitter's own class constant and watching both pages move
    together — that the hero's ring/band are genuinely CALLS into companion/draw.py rather
    than a forked copy of its markup. That mutation proof is strictly stronger than a source
    scan for suspicious literals, so the literal-scan clause is dropped rather than ported
    (rubric S: "no observable consequence beyond what is already covered")."""
    now = "2026-08-27T12:00:00+00:00"
    ctx = _home_band_ctx(tmp_path / "hero", now, [
        "2026-08-27T06:00:00+00:00",
        "2026-08-27T10:00:00+00:00",
    ])
    ctx["gallery_entries"] = ["2026-08-27T11-50-00+00-00.png"]
    rendered = home_page.render(ctx)

    # ONE hero. Two containers would be an earlier naming collision back
    # in a new costume — a second thing called "Frame" had to be
    # renamed on this very page.
    opens = len(re.findall(
        r'<div class="[^"]*\b%s\b[^"]*">' % re.escape(home_page.HERO_CLASS), rendered))
    assert opens == 1, "expected exactly one hero container on Home, got %d" % (opens,)
    inner = _home_hero_inner(rendered)
    assert inner is not None, "expected the hero container to open and close"

    # Its three parts, each still rendered by the builder that owns it.
    # The strip is matched on the class the SHARED helper emits, so a
    # hero that inlined a second rendering of it would have to reproduce
    # that class to pass — and would then fail the count below.
    for label, pattern in (
            ("the shared Frame strip", r'class="frame-strip stat-tile stat-tile--accent"'),
            ("the three status tiles", r'class="dashboard-grid home-status-grid"'),
            ("the day band", r'<section class="[^"]*\bday-band\b')):
        assert re.search(pattern, inner) is not None, (
            "expected %s inside the hero — a composition that does not contain its parts is a "
            "wrapper, not a hero (looked for %r)" % (label, pattern))
    assert rendered.count('class="frame-strip stat-tile stat-tile--accent"') == 1, (
        "expected the shared Frame strip rendered exactly once — the hero wraps the shared "
        "component, it never inlines a second rendering of it")

    # What the hero is NOT. The picture row is the page's own second half
    # and sits after it; a hero that swallowed it would make every
    # stacking measurement below about the whole page instead of the
    # composition.
    for absent in ("home-picture-row", "preview-frame", "recent-flight"):
        assert absent not in inner, (
            "expected %r outside the hero — the hero is Home's TOP, not its whole body" % (absent,))
    assert rendered.index('class="home-columns home-picture-row"') > rendered.index(
        '<div class="%s"' % home_page.HERO_CLASS), "expected the hero to precede the picture row"

    # EXACTLY ONE RING AND EXACTLY ONE BAND, both the hero's. The needles
    # are whole class ATTRIBUTES rather than bare class names: the band
    # frame's own name is a prefix of the span's and the mark's, so a
    # substring test would count three things as the frame.
    for label, needle in (
            ("battery ring value arc", 'class="%s"' % draw.DRAWING_RING_VALUE_CLASS),
            ("day band frame", 'class="%s"' % draw.DRAWING_BAND_CLASS)):
        assert rendered.count(needle) == 1, (
            "expected exactly one %s on Home, got %d" % (label, rendered.count(needle)))
        assert needle in inner, (
            "expected the %s INSIDE the hero — CFG-44's hero is the composition the drawings "
            "feed, not a container beside them" % (label,))

    # THE RECORDED FIXED BUG (Pitfall 3), re-asked in BOTH
    # languages because a hero is precisely the shape that reintroduces
    # it and French is a separate string table that could disagree.
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            page = home_page.render(ctx)
            seen = [i18n.t(v) for v in home_page.FRAME_STATE_TEXT.values() if page.count(i18n.t(v))]
            assert len(seen) == 1, "in %s expected exactly one frame verdict on Home, got %r" % (lang, seen)
            assert page.count(seen[0]) == 1, (
                "in %s expected the frame verdict %r exactly once on Home, got %d — the "
                "duplicated verdict fix removed a whole status-card builder to remove"
                % (lang, seen[0], page.count(seen[0])))
        finally:
            prefs.set_request_prefs(lang="en")


# --- Task 2 : "fed by", proven --------------------

def test_the_heros_ring_is_the_emitter_healths_ring_is(tmp_path):
    """the hero's battery ring is the same emitter Health's ring is — the two pages' rings
    carry one class vocabulary, computed from the markup rather than listed; the hero's day
    band draws three different shapes and not one; and every class either of them emits is a
    constant companion/draw.py itself names

    The legacy check also walked home_page.py's OWN source (and this check's own source) with
    ast.parse()/inspect.getsource() looking for a restated drawing-class string literal —
    banned outright by guard G2. test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_
    it_borrowed_it_from below proves the same "no restated copy" property strictly more
    strongly: it mutates the shared emitter's class constant at runtime and shows BOTH pages
    move together, which a page carrying its own copy of the string could not do. The
    source-literal scan is dropped rather than ported (rubric S)."""
    now = "2026-08-27T12:00:00+00:00"
    ctx = _home_band_ctx(tmp_path / "hero", now, [
        "2026-08-27T06:00:00+00:00",
        "2026-08-27T10:00:00+00:00",
    ], config={
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": device_config.DEFAULT_QUIET_HOURS_START,
        "quiet_hours_end": device_config.DEFAULT_QUIET_HOURS_END,
    })
    rendered = home_page.render(ctx)
    hero = _home_hero_inner(rendered)
    assert hero is not None, "expected a hero container on Home"
    health_tmp = tmp_path / "health"
    with history_db.open_db(health_tmp) as conn:
        for minute, mv in ((50, 3600), (55, 3690)):
            history_db.record_device_health(conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
    health_rendered = health_page.render({"state_dir": str(health_tmp), "now": now})

    # ONE RING, TWO PAGES. The two rings' class vocabularies are
    # COMPUTED from the markup rather than listed here, so this cannot
    # drift into a hand-maintained copy of the emitter's own list.
    hero_ring = _classes_inside_svg(hero, draw.DRAWING_FIGURE_CLASS)
    health_ring = _classes_inside_svg(health_rendered, draw.DRAWING_FIGURE_CLASS)
    assert hero_ring, "found no ring inside Home's hero"
    assert health_ring, "found no ring on Health"
    assert hero_ring == health_ring, (
        "the hero's ring and Health's carry different class vocabularies (%r against %r) — "
        "one drawing at two sizes emits one vocabulary; two vocabularies means two components"
        % (sorted(hero_ring), sorted(health_ring)))

    # THE BAND, AND ITS FLOOR. "Every class is one of the shared module's
    # own" is satisfied by a band that drew nothing but its frame, so the
    # distinct-element floor is asserted alongside it: the frame, the
    # shaded quiet-hours span and the check-in marks are three different
    # shapes, and a band that lost two of them would still pass the
    # vocabulary half on its own.
    hero_band = _classes_inside_svg(hero, draw.DRAWING_CANVAS_CLASS)
    assert hero_band, "found no day band inside Home's hero"
    assert len(hero_band) >= 3, (
        "the hero's band draws only %d kind(s) of shape (%r) — with a quiet-hours window "
        "configured and two check-ins on the day it owes three: its own frame, the shaded "
        "span and the marks" % (len(hero_band), sorted(hero_band)))

    # EVERY ONE OF THEM A NAMED CONSTANT OF THE SHARED MODULE. A forked
    # copy is free to emit any string it likes; this is what refuses the
    # ones draw.py does not own.
    for class_name in sorted(hero_ring | hero_band):
        for token in class_name.split():
            assert token in draw.DRAWING_CLASSES, (
                "the hero emits the drawing class %r, which companion/draw.py does not name — "
                "a class the shared module does not own came from somewhere else" % (token,))


def test_breaking_a_shared_emitter_breaks_the_hero_with_the_page_it_borrowed_it_from(tmp_path):
    """breaking a shared emitter breaks the hero WITH the page it borrowed it from: one class
    constant inside companion/draw.py's ring emitter is replaced at check time and both Home's
    hero and Health's readout change, neither keeping the original string (a hero built from
    its own copy would); the band emitter's own mutation reaches the hero and leaves Health
    byte-identical, proving the mutation is targeted rather than a global perturbation; and
    both pages return to their pre-mutation markup"""
    now = "2026-08-27T12:00:00+00:00"
    ctx = _home_band_ctx(tmp_path / "link", now, [
        "2026-08-27T06:00:00+00:00",
        "2026-08-27T10:00:00+00:00",
    ])
    health_tmp = tmp_path / "link-health"
    # Not a member of DRAWING_CLASSES and not a substring of one, so "the
    # sentinel arrived" and "the original left" are two independent
    # readings rather than one.
    sentinel = "skypane-emitter-under-mutation"
    with history_db.open_db(health_tmp) as conn:
        for minute, mv in ((50, 3600), (55, 3690)):
            history_db.record_device_health(conn, "2026-08-27T11:%d:00+00:00" % minute, battery_mv=mv)
    health_ctx = {"state_dir": str(health_tmp), "now": now}
    home_before = home_page.render(ctx)
    health_before = health_page.render(health_ctx)

    def _mutated(attr):
        """Both pages rendered with one of draw.py's class constants
        replaced, the constant restored afterwards whatever happens."""
        original = getattr(draw, attr)
        setattr(draw, attr, sentinel)
        try:
            return original, home_page.render(ctx), health_page.render(health_ctx)
        finally:
            setattr(draw, attr, original)

    # THE RING: one definition, two pages. A hero built from its own
    # copy would still carry the ORIGINAL class here while Health carried
    # the sentinel — which is exactly the drift is about, and is
    # invisible to any check that only looks at the markup as shipped.
    original, home_after, health_after = _mutated("DRAWING_RING_VALUE_CLASS")
    for label, before, after in (("the hero", home_before, home_after), ("Health", health_before, health_after)):
        assert sentinel in after, "a change inside the shared ring emitter did not reach %s — it draws its own ring, not the shared one" % (label,)
        assert 'class="%s"' % original not in after, (
            "%s still carries the ring's original class after the emitter was changed — part "
            "of that drawing is a copy" % (label,))
        assert after != before, "%s rendered identically under the mutation" % (label,)

    # THE MUTATION WAS TARGETED, not a global perturbation: the band is
    # Home's alone, so changing it must move the hero and leave Health
    # BYTE-IDENTICAL. Without this, "both pages changed" above would be
    # worth much less.
    original, home_after, health_after = _mutated("DRAWING_BAND_MARK_CLASS")
    assert sentinel in home_after, "a change inside the shared band emitter did not reach the hero — its band is a copy"
    assert 'class="%s"' % original not in home_after, (
        "the hero still carries the band mark's original class after the emitter was changed "
        "— part of that drawing is a copy")
    assert health_after == health_before, (
        "changing the band emitter also changed Health, which draws no band — the mutation is "
        "not measuring what it names")

    # THE RESTORE IS PART OF THE CHECK. A mutation left behind would make
    # every later check in this file measure a sabotaged module, and the
    # failure would land somewhere else entirely.
    assert home_page.render(ctx) == home_before, "Home did not return to its pre-mutation markup"
    assert health_page.render(health_ctx) == health_before, "Health did not return to its pre-mutation markup"


# --- Task 3 (S-02): the "Next wake ≈ HH:MM" figure ---

def test_wake_next_wake_at_iso_contract():
    """wake.next_wake_at_iso()/next_wake_status() return None/(None, None, None) for a
    falsy/unparseable ts or an unknown interval, last_checkin + wake_interval_s for a
    screen-on config, last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config (
    screen-off rule), and the quiet-hours-active fixtures: a window opening during the base
    interval wins over the naive candidate, an enabled-but-nowhere-near-active window changes
    nothing, an active window beats a 300s screen-off cadence, and the richer accessor carries
    the same effective interval and hold reason for every fixture above"""
    # None for a falsy/unparseable ts, or no known interval.
    assert wake.next_wake_at_iso(None, {}) is None, "expected None for a falsy last_checkin_ts"
    assert wake.next_wake_at_iso("", {"wake_interval_s": 900}) is None, "expected None for an empty-string last_checkin_ts"
    assert wake.next_wake_at_iso("not-a-timestamp", {"wake_interval_s": 900}) is None, (
        "expected None for an unparseable last_checkin_ts")
    assert wake.next_wake_at_iso("2026-08-27T11:55:00+00:00", {}) is None, (
        "expected None for a config with no known interval and no env fallback")
    # A screen-on config: last_checkin + wake_interval_s. Pre-existing
    # fixture, pinned byte-identical — this config carries no quiet-hours
    # key at all and quiet_hours_status() degrades to (None, None) for it.
    got = wake.next_wake_at_iso(
        "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": True})
    assert got == "2026-08-27T12:10:00+00:00", "expected last_checkin + wake_interval_s, got %r" % (got,)
    # A screen-off config: last_checkin + DISPLAY_OFF_SLEEP_S, the
    # screen-off rule — wins over wake_interval_s regardless of its
    # value. Pre-existing fixture, pinned byte-identical for the same
    # reason.
    got = wake.next_wake_at_iso(
        "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": False})
    expected = (
        datetime(2026, 8, 27, 11, 55, 0, tzinfo=timezone.utc)
        + timedelta(seconds=device_config.DISPLAY_OFF_SLEEP_S)).isoformat()
    assert got == expected, "expected last_checkin + DISPLAY_OFF_SLEEP_S for a screen-off config, got %r" % (got,)

    # Fixture A: quiet hours 23:00-07:00 Europe/Paris, last check-in
    # 22:58 Europe/Paris (a non-DST date), interval 900s. The naive
    # last_checkin + interval candidate (23:13) falls INSIDE the window
    # that opens two minutes after the check-in — the window must win,
    # returning the window's end (07:00 the next day), not 23:13.
    qh_config_a = {
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    checkin_a = datetime(2026, 1, 15, 22, 58, 0, tzinfo=timezone(timedelta(hours=1)))
    got = wake.next_wake_at_iso(checkin_a.isoformat(), qh_config_a)
    expected_a = datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone(timedelta(hours=1))).isoformat()
    assert got == expected_a, (
        "fixture A (quiet hours 23:00-07:00, check-in 22:58, interval 900s): expected the "
        "window's end (%r), not the naive 23:13 candidate, got %r" % (expected_a, got))
    status_a = wake.next_wake_status(checkin_a.isoformat(), qh_config_a)
    assert status_a[0] == expected_a, "fixture A: next_wake_status()'s ISO element disagreed with next_wake_at_iso()"
    assert status_a[2] == wake.HOLD_QUIET_HOURS, "fixture A: expected hold_reason == HOLD_QUIET_HOURS, got %r" % (status_a[2],)
    assert (checkin_a + timedelta(seconds=status_a[1])).isoformat() == expected_a, (
        "fixture A: effective_interval_s (%r) added back to the check-in did not reproduce "
        "the returned ISO string" % (status_a[1],))

    # Fixture B: quiet hours enabled, but nowhere near active at the
    # check-in instant NOR at the check-in-plus-interval candidate —
    # returns the plain interval, unmodified.
    qh_config_b = dict(qh_config_a)
    checkin_b = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    got = wake.next_wake_at_iso(checkin_b.isoformat(), qh_config_b)
    expected_b = (checkin_b + timedelta(seconds=900)).isoformat()
    assert got == expected_b, (
        "fixture B (quiet hours enabled but inactive at check-in and at check-in+interval): "
        "expected the plain interval (%r), got %r" % (expected_b, got))
    status_b = wake.next_wake_status(checkin_b.isoformat(), qh_config_b)
    assert status_b[2] is None, "fixture B: expected hold_reason is None when quiet hours never engages"

    # Fixture C: quiet hours active AND the screen off — the window
    # still wins when its remaining time is longer than
    # DISPLAY_OFF_SLEEP_S (300s).
    qh_config_c = {
        "wake_interval_s": 900, "display_enabled": False,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    checkin_c = datetime(2026, 1, 16, 1, 0, 0, tzinfo=timezone(timedelta(hours=1)))
    got = wake.next_wake_at_iso(checkin_c.isoformat(), qh_config_c)
    expected_c = datetime(2026, 1, 16, 7, 0, 0, tzinfo=timezone(timedelta(hours=1))).isoformat()
    assert got == expected_c, (
        "fixture C (quiet hours active AND screen off): expected the window's end (%r), got "
        "%r — the window must win over the 300s screen-off cadence" % (expected_c, got))
    status_c = wake.next_wake_status(checkin_c.isoformat(), qh_config_c)
    assert status_c[2] == wake.HOLD_QUIET_HOURS, "fixture C: expected hold_reason == HOLD_QUIET_HOURS"

    # Fixture D: the richer accessor's None-triple for the same
    # never-raise edge cases the bare-ISO wrapper already covers.
    assert wake.next_wake_status(None, {}) == (None, None, None), "expected (None, None, None) for a falsy last_checkin_ts"
    assert wake.next_wake_status("2026-08-27T11:55:00+00:00", {}) == (None, None, None), (
        "expected (None, None, None) for a config with no known interval and no env fallback")

    # Fixture E: the richer accessor returns the effective interval and
    # hold reason (None) alongside the ISO string for the two
    # pre-existing, non-quiet-hours fixtures above.
    status_on = wake.next_wake_status(
        "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": True})
    assert status_on == ("2026-08-27T12:10:00+00:00", 900, None), (
        "expected the screen-on fixture's richer result to carry interval=900, "
        "hold_reason=None, got %r" % (status_on,))
    status_off = wake.next_wake_status(
        "2026-08-27T11:55:00+00:00", {"wake_interval_s": 900, "display_enabled": False})
    assert status_off == (expected, device_config.DISPLAY_OFF_SLEEP_S, None), (
        "expected the screen-off fixture's richer result to carry interval=DISPLAY_OFF_SLEEP_S, "
        "hold_reason=None, got %r" % (status_off,))


# --- Task 2 : the one frame-state resolution and
# the one delay sentence -------------------------------------------------

def test_frame_state_resolve_state_contract():
    """companion.frame_state.resolve_state() resolves due/held/late/unknown from a
    (next_wake_iso, effective_interval_s, hold_reason, now) tuple with an invisible grace
    window and a held frame that cannot escalate by elapsed time alone,
    headline_template()/delay_sentence_template() return the matching three-branch copy
    constants, and the nightly regression (quiet hours 23:00-07:00, check-in 22:58, clock
    02:00 Europe/Paris) resolves to STATE_HELD end to end through wake.next_wake_status()
    (§3.3 binding rule 6)"""
    # No check-in recorded at all: unknown, no dot class claimed — this
    # module never returns a dot class in the first place.
    assert frame_state.resolve_state(None, None, None, "2026-01-15T12:00:00+00:00") == frame_state.STATE_UNKNOWN, (
        "expected STATE_UNKNOWN for a falsy next_wake_iso")
    assert frame_state.headline_template(
        frame_state.resolve_state(None, None, None, "2026-01-15T12:00:00+00:00")) == frame_state.HEADLINE_DUE, (
        "expected the unknown state to degrade to HEADLINE_DUE, never None")
    assert frame_state.delay_sentence_template(None, None, None) == frame_state.DELAY_UNKNOWN, (
        "expected DELAY_UNKNOWN when no next_wake_iso is known")

    next_wake = "2026-01-15T12:00:00+00:00"
    interval_s = 900

    # now before next_wake: due.
    now_before = "2026-01-15T11:00:00+00:00"
    assert frame_state.resolve_state(next_wake, interval_s, None, now_before) == frame_state.STATE_DUE, (
        "expected STATE_DUE when now is before next_wake")
    assert frame_state.headline_template(frame_state.STATE_DUE) == frame_state.HEADLINE_DUE, "expected HEADLINE_DUE for STATE_DUE"

    # now between next_wake and next_wake + 2 * interval: still due, same
    # copy — the grace window is invisible (rule 3), no third state, no
    # colour shift.
    now_in_grace = (datetime.fromisoformat(next_wake) + timedelta(seconds=interval_s)).isoformat()
    assert frame_state.resolve_state(next_wake, interval_s, None, now_in_grace) == frame_state.STATE_DUE, (
        "expected STATE_DUE inside the grace window (next_wake + 1 * interval)")

    # now >= next_wake + 2 * interval, no hold: late.
    now_late = (datetime.fromisoformat(next_wake) + timedelta(seconds=2 * interval_s)).isoformat()
    assert frame_state.resolve_state(next_wake, interval_s, None, now_late) == frame_state.STATE_LATE, (
        "expected STATE_LATE at exactly next_wake + 2 * interval")
    assert frame_state.headline_template(frame_state.STATE_LATE) == frame_state.HEADLINE_LATE, "expected HEADLINE_LATE for STATE_LATE"

    # hold reason quiet hours: held, regardless of how far now sits past
    # next_wake + 2 * interval (rule 4: a held frame cannot escalate to
    # late by elapsed time alone).
    far_past = (datetime.fromisoformat(next_wake) + timedelta(days=3)).isoformat()
    assert frame_state.resolve_state(next_wake, interval_s, wake.HOLD_QUIET_HOURS, now_late) == frame_state.STATE_HELD, (
        "expected STATE_HELD when hold_reason is HOLD_QUIET_HOURS")
    assert frame_state.resolve_state(next_wake, interval_s, wake.HOLD_QUIET_HOURS, far_past) == frame_state.STATE_HELD, (
        "expected STATE_HELD to survive 3 days past next_wake + 2 * interval — elapsed time "
        "alone must never escalate a held frame to late")
    assert frame_state.headline_template(frame_state.STATE_HELD) == frame_state.HEADLINE_HELD, "expected HEADLINE_HELD for STATE_HELD"

    # The delay sentence has exactly three branches — due, held, unknown,
    # never a fourth "late" branch.
    assert frame_state.delay_sentence_template(next_wake, interval_s, None) == frame_state.DELAY_DUE, (
        "expected DELAY_DUE for a due (or late) triple")
    assert frame_state.delay_sentence_template(next_wake, interval_s, wake.HOLD_QUIET_HOURS) == frame_state.DELAY_HELD, (
        "expected DELAY_HELD when hold_reason is HOLD_QUIET_HOURS")

    # --- The nightly regression (§3.3 binding rule 6):
    # quiet hours 23:00-07:00, last check-in 22:58, clock 02:00,
    # Europe/Paris (a non-DST date) — the resolved state must be
    # STATE_HELD, never STATE_LATE, end to end through
    # wake.next_wake_status() into frame_state.resolve_state().
    paris = timezone(timedelta(hours=1))
    qh_config = {
        "wake_interval_s": 900, "display_enabled": True,
        "quiet_hours_enabled": True,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00",
    }
    checkin = datetime(2026, 1, 15, 22, 58, 0, tzinfo=paris)
    next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(checkin.isoformat(), qh_config)
    clock = datetime(2026, 1, 16, 2, 0, 0, tzinfo=paris)
    nightly_state = frame_state.resolve_state(next_wake_iso, effective_interval_s, hold_reason, clock.isoformat())
    assert nightly_state == frame_state.STATE_HELD, (
        "the nightly regression: expected STATE_HELD at 02:00 for a 22:58 check-in inside a "
        "23:00-07:00 quiet-hours window, got %r (next_wake=%r, effective_interval_s=%r, "
        "hold_reason=%r) — this is exactly X2's nightly false alarm"
        % (nightly_state, next_wake_iso, effective_interval_s, hold_reason))


def test_frame_state_is_view_free_and_localises_its_own_copy():
    """companion/frame_state.py imports no layout module (view-free) and names no
    CSS dot class among its own exposed copy constants, and each of its six copy constants
    round-trips through companion.i18n's French catalogue unchanged in English

    The legacy check opened companion/frame_state.py from disk to grep for "dot--warn" and
    for a `layout` import — rewritten per rubric S: the import-boundary half is proven by
    importing companion.frame_state fresh in a subprocess and inspecting sys.modules (the same
    technique companion/test_companion_app_03.py's own battery/draw import-boundary checks
    already use), and the CSS-class half is proven against the module's own already-imported
    public string constants — its actual returned copy, never its source text."""
    script = (
        "import sys\n"
        "import companion.frame_state\n"
        "print('companion.layout' in sys.modules)\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], cwd=REPO_ROOT, env=child_env(dict(os.environ)),
        capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "False", (
        "expected companion.frame_state to import no layout module, sys.modules said %s"
        % result.stdout.strip())

    public_copy = [
        value for name, value in vars(frame_state).items()
        if name.isupper() and isinstance(value, str)
    ]
    assert public_copy, "expected companion.frame_state to expose at least one public string constant"
    for value in public_copy:
        assert "dot--warn" not in value, (
            "expected frame_state.py's own exposed copy to never name a CSS dot class, found "
            "it in %r" % (value,))

    # Each of the three headline and three delay-sentence constants
    # round-trips through the French catalogue (either frame_state's own
    # new entries, or the pre-existing entries for the two deliberate
    # collisions) and renders unchanged in English.
    headline_pairs = (
        (frame_state.HEADLINE_DUE, "Prochaine mise à jour ≈ %s"),
        (frame_state.HEADLINE_HELD, "Prochain réveil vers %s · heures calmes"),
        (frame_state.HEADLINE_LATE, "Attendu depuis %s"),
    )
    for english, french in headline_pairs:
        assert i18n.t_lang(english, "en") == english, "expected %r unchanged under lang='en'" % (english,)
        assert i18n.t_lang(english, "fr") == french, (
            "expected %r to translate to %r under lang='fr', got %r" % (english, french, i18n.t_lang(english, "fr")))
    delay_pairs = (
        (frame_state.DELAY_DUE, "S’applique au prochain réveil, vers %s."),
        (frame_state.DELAY_HELD, "S’applique à la fin des heures calmes, vers %s."),
        (frame_state.DELAY_UNKNOWN, "S’applique au prochain réveil du cadre."),
    )
    for english, french in delay_pairs:
        assert i18n.t_lang(english, "en") == english, "expected %r unchanged under lang='en'" % (english,)
        assert i18n.t_lang(english, "fr") == french, (
            "expected %r to translate to %r under lang='fr', got %r" % (english, french, i18n.t_lang(english, "fr")))


# NOTE: "companion/battery.py imports neither companion.pages nor server"
# is not a separate test here — it is IDENTICAL to
# companion/test_companion_app_03.py::
# test_battery_module_imports_neither_a_page_module_nor_the_server_package,
# using the same subprocess + sys.modules technique
# test_frame_state_is_view_free_and_localises_its_own_copy above uses.


# --- End-to-end HTTP round trips -----------------------------------------

def _seed_view_pages_e2e_fixture(state_dir):
    vp.seed_runway_events(state_dir, [
        {"ts": "2026-08-27T10:00:00+00:00", "hex": "e2e001", "callsign": "E2E001"},
    ])
    # A present panel.bin that changes nothing about the markup any more
    # is part of what this check proves.
    vp.write_panel_file(state_dir)
    vp.seed_gallery(state_dir, ["20260827T100002Z.png"])


def test_history_preview_and_gallery_round_trip_over_http(make_app_server):
    """GET /flights returns 200 with its own heading, GET /preview redirects (303) to
    /flights, GET /preview.png now returns 404 (the route is retired), and GET
    /gallery/{name}.png returns 200 image/png with a real PNG signature — proving the route
    the per-row View-panel lightbox now links to genuinely serves full-resolution bytes,
    against a real running service"""
    server = make_app_server(seed=_seed_view_pages_e2e_fixture)
    session_cookie = login(server)

    status, _headers, body = get(server, "/flights", cookie=session_cookie)
    assert status == 200, "expected 200 for /flights, got %d" % status
    assert b"Flights" in body, "expected the 'Flights' heading in /flights's response body"

    status, headers, _body = get(server, "/preview", cookie=session_cookie)
    assert status == 303, "expected a 303 redirect for /preview, got %d" % status
    assert headers.get("Location") == "/flights", "expected /preview to redirect to /flights, got %r" % headers.get("Location")

    status, _headers, _body = get(server, "/preview.png", cookie=session_cookie)
    assert status == 404, "expected 404 for the retired /preview.png route, got %d" % status

    status, headers, body = get(server, "/gallery/20260827T100002Z.png", cookie=session_cookie)
    assert status == 200, "expected 200 for a real /gallery/{name}.png, got %d" % status
    assert body.startswith(_PNG_SIGNATURE), "expected a real PNG signature at the start of the gallery image body"
    content_type = headers.get("Content-Type", "")
    assert content_type == "image/png", "expected Content-Type: image/png, got %r" % content_type


def test_airlines_dialog_forms_render_unconditionally_over_real_http(make_app_server):
    """a real authenticated GET of /airlines renders the dialog's replace, delete and
    upload-zone forms with no query string at all, and a leftover ?edit=1 in a bookmark
    renders identically — against a real running service, proving the removed query
    parameter has no reader anywhere in the real request path"""
    server = make_app_server(seed=_seed_view_pages_e2e_fixture)
    session_cookie = login(server)
    unconditional_tokens = (
        airlines_page.LIGHTBOX_REPLACE_FORM_CLASS,
        airlines_page.LIGHTBOX_DELETE_CLASS,
        airlines_page.RESOLVE_UPLOAD_ZONE_CLASS,
    )
    for query in ("", "?edit=1"):
        status, _headers, body = get(server, "/airlines" + query, cookie=session_cookie)
        assert status == 200, "expected 200 for /airlines%s, got %d" % (query, status)
        body_text = body.decode("utf-8", "replace")
        for token in unconditional_tokens:
            assert ('class="%s"' % token) in body_text, (
                "expected /airlines%s to render a %r form (CFG-81: unconditional now)" % (query, token))


def test_both_dialogs_arrive_through_one_starting_style_entrance(tmp_path, served_css):
    """both <dialog>s fade and zoom in from opacity 0 over var(--motion-fast) through ONE
    @starting-style entrance rule on .lightbox[open] — the two dialogs (History's panel
    lightbox and the Airlines gallery's wide variant) are the same component under two
    classes, so the entrance is declared once and reaches both — with `display`/
    `allow-discrete` deliberately absent so close() ends the dialog outright rather than
    leaving an invisible click-swallowing sheet over the page, and with
    ::backdrop unanimated because the global reduced-motion override cannot reach it
    (D3)"""
    entrance_rules = [
        rule for rule in rules_with_selector(served_css, ".lightbox[open]")
        if rule.at_rules == ("@starting-style",)
    ]
    assert len(entrance_rules) == 1, (
        "expected exactly ONE @starting-style entrance for .lightbox[open] (one rule, two "
        "dialogs — History's and the Airlines gallery's wide variant are the same component "
        "under two classes), got %d" % (len(entrance_rules),))
    entrance_decls = dict(entrance_rules[0].declarations)
    assert entrance_decls.get("opacity") == "0", (
        "expected the @starting-style entrance to start from opacity 0 — an element going "
        "from display:none to displayed has no previous computed value to transition from, "
        "which is the whole job of this block")
    assert "scale(" in (entrance_decls.get("transform") or ""), (
        "expected the @starting-style entrance to start from a scale — both dialogs FADE AND "
        "ZOOM in")

    open_state_rules = [
        rule for rule in rules_with_selector(served_css, ".lightbox[open]")
        if rule.at_rules == ()
    ]
    assert len(open_state_rules) == 1, (
        "expected exactly one %r rule outside @starting-style — one entrance serving BOTH "
        "dialogs, got %d" % (".lightbox[open] {", len(open_state_rules)))

    base = declarations_for(served_css, ".lightbox")
    assert "transition" in base, "expected .lightbox to declare the entrance transition"
    decl = base["transition"]
    for prop in ("opacity", "transform"):
        assert prop in decl, "expected the .lightbox transition to name %r, got %r" % (prop, decl)
    assert "var(--motion-fast)" in decl, "expected the dialog entrance to spend var(--motion-fast), got %r" % (decl,)
    assert "display" not in decl and "allow-discrete" not in decl, (
        "the .lightbox transition must NOT carry `display`/`allow-discrete`: a modal that has "
        "not reached display:none is an invisible sheet over the page that swallows clicks "
        "(T-23-36), and it stays in the tab order and the accessibility tree for the whole of "
        "its exit. Got %r" % (decl,))

    # ::backdrop is deliberately NOT animated, and that is a
    # reduced-motion fact rather than a taste one: the global override
    # matches `*, *::before, *::after`, which are ELEMENT selectors —
    # ::backdrop is in neither.
    backdrop = declarations_for(served_css, ".lightbox::backdrop")
    assert "transition" not in backdrop and "animation" not in backdrop, (
        ".lightbox::backdrop must not be animated — the global reduced-motion override matches "
        "`*, *::before, *::after`, none of which is ::backdrop, so a backdrop transition is "
        "motion a reduced-motion visitor cannot escape")

    # And both dialogs really do render with the class the one rule
    # above is keyed to. History emits its dialog only on a page that has
    # a panel to show, so the fixture has to have one.
    names = ["2026-08-27T10-00-00+00-00.png"]
    vp.seed_gallery(tmp_path, names)
    vp.seed_runway_events(tmp_path, [
        {"ts": "2026-08-27T10:03:00+00:00", "hex": "dlgent1", "callsign": "DLGENT"},
    ])
    history_html = history_page.render(vp.history_ctx(tmp_path, gallery_entries=names))
    airlines_html = airlines_page.render({})
    assert parse_html(history_html).select("dialog.lightbox"), (
        "expected the history page to render a dialog.lightbox so the one .lightbox[open] "
        "entrance reaches it")
    assert parse_html(airlines_html).select("dialog.lightbox.lightbox--wide"), (
        "expected the airlines page to render a dialog.lightbox.lightbox--wide so the one "
        ".lightbox[open] entrance reaches it")
