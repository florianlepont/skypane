"""Part 02 of the `companion/test_config_page.py` migration chain
(33-10-PLAN.md): the original harness's `check()` calls #34-#84, covering
the quiet-window arithmetic and the quiet-hours dial (span/arc/readout/
handles/pair seam), the remaining render()/runway_fieldset()/dirty-bar
markup checks, poll_trigger_section()'s data-attribute contract and
companion/static/poll-cooldown.js's sink safety, and handle_post()'s
theme/runway/LED/quiet-hours/wake-interval validation paths.

Every check calls `companion.pages.config_page`'s own functions directly,
in-process, against a `tmp_path`-backed state directory — this slice
still needs no running `companion/app.py` server for its handle_post()/
render() checks. The few checks that used to read
`companion/static/style.css` or a served JS asset from disk instead fetch
them from a running `companion/app.py` (`module_app_server_factory` +
`served_stylesheet()`/`served_asset()`) and assert on
`companion_markup`'s parsed CSS structure or the served text itself —
never a file opened from disk (TST-12). Runtime state files this slice
writes under `tmp_path` (never production source) are read back with
`pathlib.Path.read_bytes()`.
"""
import datetime
import math
import re
from pathlib import Path

import pytest

import companion.i18n_fr as i18n_fr
import companion.layout as layout
import companion.prefs as prefs
import companion.test_config_page_helpers as cp
from companion import draw
from companion.layout import escape_html
from companion.pages import config_page
from companion_app_server import served_asset, served_stylesheet
from companion_markup import css_rules, declarations_for
from server import device_config


@pytest.fixture(scope="module")
def app(module_app_server_factory):
    """A read-only companion/app.py server this module's checks fetch the
    served stylesheet/JS assets from, instead of opening them from disk
    (TST-12)."""
    return module_app_server_factory()


@pytest.fixture(scope="module")
def served_css(app):
    """The stylesheet companion/app.py actually serves."""
    return served_stylesheet(app)


@pytest.fixture(scope="module")
def value_controls_js(app):
    """companion/static/value-controls.js's served text, fetched over
    HTTP instead of opened from disk (TST-12)."""
    return served_asset(app, "/static/value-controls.js")


@pytest.fixture(scope="module")
def poll_cooldown_js(app):
    """companion/static/poll-cooldown.js's served text, fetched over HTTP
    instead of opened from disk (TST-12)."""
    return served_asset(app, "/static/poll-cooldown.js")


# ======================================================================
# Section 1: the quiet window's arithmetic and the quiet-hours dial
# (span/arc/readout/handles/pair seam).
# ======================================================================

_DIAL_CIRCLE_RE = re.compile(r"<circle\b[^>]*/>")


def _dial_circle(markup, class_name):
    """The one `<circle>` in `markup` carrying exactly `class_name`, as a
    dict of its attributes, or None.

    Matched on a whole `class="..."` ATTRIBUTE rather than a substring,
    because this component's day-ring class is not a prefix of its arc's
    but a substring test is how a check comes to count two shapes as one
    anyway.
    """
    for tag in _DIAL_CIRCLE_RE.finditer(markup):
        attrs = dict(re.findall(r'([a-zA-Z-]+)="([^"]*)"', tag.group(0)))
        if attrs.get("class") == class_name:
            return attrs
    return None


def test_the_quiet_window_wraps_midnight_the_short_way_round():
    """the quiet window's span goes FORWARD through midnight — 23:00→07:00 is 480 minutes and
    07:00→23:00 its 960-minute complement, 00:00→00:01 and 23:59→00:00 are both 1, the
    drawn sweep is the returned minute count and never a second computation, the span's
    length is reconstructed from what server.device_config.seconds_until_quiet_hours_end()
    has left at a shared instant rather than pinned, equal ends is the zero-width window
    that server's own docstring calls never-active, and every unparseable input returns the
    render-nothing signal rather than raising or fabricating a zero (CFG-48, 25-04-PLAN.md
    Task 1)"""
    span_of = config_page.quiet_window_span
    day = config_page.QUIET_WINDOW_MINUTES_PER_DAY
    assert day == 1440, "expected a 1440-minute day, got %r" % (day,)

    # THE DEFAULT WINDOW, AND THE COMPLEMENT THAT PROVES DIRECTION.
    # Asserting 480 alone passes against an implementation that returns
    # the SHORTER of the two arcs whichever way round it was asked; the
    # complement is what refuses that.
    for start, end, expected in (
            ("23:00", "07:00", 480),
            ("07:00", "23:00", 960),
            ("00:00", "00:01", 1),
            ("23:59", "00:00", 1),
            ("00:00", "23:59", 1439),
            ("12:00", "12:00", 0)):
        span = span_of(start, end)
        assert span is not None, "expected %s→%s to produce a span, got None" % (start, end)
        assert span.minutes == expected, (
            "%s→%s is %d minutes forward through midnight, and quiet_window_span() "
            "returns %d — an `end - start` implementation returns %d here, which is the "
            "single most likely arithmetic defect in this control"
            % (start, end, expected, span.minutes,
               config_page.quiet_window_minute_of_day(end)
               - config_page.quiet_window_minute_of_day(start)))

    # THE SWEEP IS THE MINUTES, NOT A SECOND COMPUTATION. Asserted over
    # every pair above and a lattice besides, because the defect is a
    # card that prints "8 h" beside an arc covering two thirds of the
    # day, and two agreeing numbers for one case could be a coincidence.
    for start_minute in range(0, 1440, 37):
        for end_minute in range(0, 1440, 53):
            start = "%02d:%02d" % divmod(start_minute, 60)
            end = "%02d:%02d" % divmod(end_minute, 60)
            span = span_of(start, end)
            assert span is not None, "expected %s→%s to parse" % (start, end)
            assert abs(span.sweep_fraction - span.minutes / 1440.0) <= 1e-12, (
                "%s→%s: sweep_fraction %r is not minutes/%d (%r) — the drawn arc and the "
                "printed duration are two computations and can disagree"
                % (start, end, span.sweep_fraction, day, span.minutes / 1440.0))
            assert abs(span.start_fraction - start_minute / 1440.0) <= 1e-12, (
                "%s→%s: start_fraction %r is not %r"
                % (start, end, span.start_fraction, start_minute / 1440.0))
            assert 0.0 <= span.sweep_fraction < 1.0, (
                "%s→%s: sweep_fraction %r left [0, 1)" % (start, end, span.sweep_fraction))
    default_span = span_of("23:00", "07:00")
    assert abs(default_span.sweep_fraction - 1 / 3.0) <= 1e-9, (
        "the default window's sweep is %r turns, not the third of the ring 480 of 1440 "
        "minutes is" % (default_span.sweep_fraction,))

    # AGREEMENT WITH THE SERVER'S OWN AUTHORITY, ON A SHARED CASE.
    # server.device_config.seconds_until_quiet_hours_end() is what
    # actually decides whether the device is inside a wrapping window;
    # this function only draws one. Pinning 480 here and trusting them to
    # stay in step is how two wrapping-window arithmetics drift. So the
    # span's own LENGTH is reconstructed from what the server says is
    # left at a shared instant.
    #
    # BOTH SIDES OF MIDNIGHT, AND THAT IS NOT BELT-AND-BRACES.
    # seconds_until_quiet_hours_end() answers a wrapping window through
    # TWO different branches — one for an instant after the start and
    # before midnight, one for an instant after midnight and before the
    # end — and a probe taken only after midnight leaves the first
    # branch unexercised.
    #
    # Times are Europe/Paris in mid-January, which is UTC+1.
    for start, end, utc_hm, local_minute in (
            ("23:00", "07:00", (1, 0), 2 * 60),
            ("23:00", "07:00", (22, 30), 23 * 60 + 30),
            ("22:30", "06:15", (23, 0), 0),
            ("22:30", "06:15", (21, 45), 22 * 60 + 45),
            ("01:00", "03:00", (1, 0), 2 * 60)):
        now_utc = datetime.datetime(
            2026, 1, 15, utc_hm[0], utc_hm[1], tzinfo=datetime.timezone.utc)
        span = span_of(start, end)
        remaining = device_config.seconds_until_quiet_hours_end(now_utc, start, end)
        assert remaining is not None, (
            "expected server.device_config to place local %02d:%02d inside %s→%s"
            % (local_minute // 60, local_minute % 60, start, end))
        elapsed = (local_minute - config_page.quiet_window_minute_of_day(start)) % 1440
        assert remaining == (span.minutes - elapsed) * 60, (
            "the dial and server.device_config disagree about %s→%s: the server has %d "
            "seconds left at local %02d:%02d, and the dial's %d-minute span with %d "
            "minutes elapsed implies %d"
            % (start, end, remaining, local_minute // 60, local_minute % 60,
               span.minutes, elapsed, (span.minutes - elapsed) * 60))

    # EQUAL ENDS IS ZERO, AND THE SERVER SAYS SO TOO. Its own docstring
    # calls a zero-width window "never active, and that is intentional
    # rather than a bug to 'fix' into an always-active window" — so this
    # is agreement, not a number chosen here.
    zero = span_of("23:00", "23:00")
    assert zero.minutes == 0 and zero.sweep_fraction == 0.0, (
        "expected equal ends to be a ZERO-length window (the reading "
        "seconds_until_quiet_hours_end() implies), got %r" % (zero,))
    for instant_hour in (0, 2, 12, 22, 23):
        probe = datetime.datetime(
            2026, 1, 15, (instant_hour - 1) % 24, 0, tzinfo=datetime.timezone.utc)
        assert device_config.seconds_until_quiet_hours_end(probe, "23:00", "23:00") is None, (
            "server.device_config reports 23:00→23:00 ACTIVE at local %02d:00, so the "
            "zero reading above no longer agrees with it — one of the two has changed "
            "its mind about a zero-width window" % instant_hour)

    # THE RENDER-NOTHING SIGNAL. None, never an exception (T-25-04-C: the
    # Display page renders this) and never a zero, which would draw a
    # real, empty window and claim one is configured.
    for hostile in ("", None, "7:00", "0700", "99:99", "24:00", "23:60", "ab:cd",
                    "23:00 ", 5, True, object(), "<b>23:00</b>"):
        assert span_of(hostile, "07:00") is None, (
            "expected quiet_window_span(%r, '07:00') to be None — the render-nothing "
            "signal, not a fabricated window" % (hostile,))
        assert span_of("23:00", hostile) is None, (
            "expected quiet_window_span('23:00', %r) to be None" % (hostile,))
        assert config_page.quiet_window_minute_of_day(hostile) is None, (
            "expected quiet_window_minute_of_day(%r) to be None" % (hostile,))

    # ONE PARSE DISCIPLINE. Anything the dial is willing to DRAW, the B14
    # 24h sibling must be willing to PRINT — a value that reaches the arc
    # but not the text is a card whose picture and whose words disagree
    # about what is stored.
    for value in ("00:00", "07:00", "23:59", "12:34", "99:99", "7:00", "", "24:00"):
        assert not (config_page.quiet_window_minute_of_day(value) is not None
                    and config_page._normalised_time_html(value) == ""), (
            "quiet_window_minute_of_day(%r) parses but _normalised_time_html(%r) renders "
            "nothing — the arc and B14's visible 24h sibling have drifted into two parse "
            "disciplines" % (value, value))


def test_the_ring_draws_the_saved_window_from_the_emitted_attributes():
    """the quiet dial's arc is recomputed from the attributes the SERVER emitted — 23:00→07:00
    draws a third of the emitted circle and 07:00→23:00 its two thirds, the dash pattern
    adds up to that circle's own circumference, and the arc is rotated by a quarter turn
    plus the window's own start about its own centre (an eight-hour arc drawn from the
    wrong hour is the same length and a different window); the readout names both times and
    the duration the same span implies and is aria-hidden; nothing on the card is a
    role="status"/aria-live region (CFG-52); nothing stored draws no arc and no words
    while the full-day ring still draws; and a hostile submitted value reaches neither
    (T-25-04-B) (CFG-48, 25-04-PLAN.md Task 2)"""
    for start, end, expected_turns in (
            ("23:00", "07:00", 1 / 3.0),
            ("07:00", "23:00", 2 / 3.0),
            ("00:00", "06:00", 0.25),
            ("23:59", "00:00", 1 / 1440.0)):
        markup = config_page.quiet_hours_group(start, end)
        day = _dial_circle(markup, config_page.QUIET_DIAL_DAY_CLASS)
        arc = _dial_circle(markup, config_page.QUIET_DIAL_ARC_CLASS)
        assert day is not None, "%s→%s: the dial emits no full-day ring at all" % (start, end)
        assert arc is not None, "%s→%s: the dial emits no quiet arc" % (start, end)
        assert not (day["r"] != arc["r"] or day["cx"] != arc["cx"] or day["cy"] != arc["cy"]), (
            "%s→%s: the arc is not drawn on the day ring — day %r, arc %r"
            % (start, end, day, arc))
        circumference = 2 * math.pi * float(arc["r"])
        drawn = float(arc["stroke-dasharray"].split()[0])
        gap = float(arc["stroke-dasharray"].split()[1])
        assert abs(drawn + gap - circumference) <= 0.01, (
            "%s→%s: the dash pattern %r does not add up to the circumference %.4f of the "
            "r=%s circle it is painted on" % (start, end, arc["stroke-dasharray"],
                                              circumference, arc["r"]))
        assert abs(drawn / circumference - expected_turns) <= 1e-4, (
            "%s→%s draws %.4f of the ring, not the %.4f its %d-minute span asks for — "
            "recomputed from the emitted r=%s and stroke-dasharray=%r"
            % (start, end, drawn / circumference, expected_turns,
               config_page.quiet_window_span(start, end).minutes,
               arc["r"], arc["stroke-dasharray"]))
        # WHERE THE ARC STARTS, WHICH A LENGTH CHECK IS BLIND TO. An
        # eight-hour arc drawn from 07:00 instead of 23:00 is the same
        # length and a different window.
        span = config_page.quiet_window_span(start, end)
        rotation = re.match(
            r"rotate\((-?[\d.]+) (\d+) (\d+)\)", arc["transform"])
        assert rotation, "%s→%s: unreadable arc transform %r" % (start, end, arc["transform"])
        assert abs(float(rotation.group(1)) - (-90.0 + 360.0 * span.start_fraction)) <= 1e-3, (
            "%s→%s: the arc is rotated %s°, but a window starting at %.6f of the way "
            "round from twelve o'clock needs %.4f° (a quarter turn back from <circle>'s "
            "own three-o'clock dash origin, plus the window's own start)"
            % (start, end, rotation.group(1), span.start_fraction,
               -90.0 + 360.0 * span.start_fraction))
        assert (rotation.group(2), rotation.group(3)) == (arc["cx"], arc["cy"]), (
            "%s→%s: the arc rotates about %r, not its own centre %r"
            % (start, end, rotation.group(2, 3), (arc["cx"], arc["cy"])))

    # THE READOUT SAYS WHAT THE ARC DRAWS, asserted against BOTH at once:
    # the two times it names and the duration the span implies.
    #
    # 27-02-PLAN.md Task 3 (CFG-62): the readout is now THREE children
    # (two `data-value-readout` endpoints plus a duration span), not one
    # text node — so "at rest, byte-identical" is checked against the
    # STRIPPED text (what a visitor reads), and the structural seam is
    # checked separately.
    markup = config_page.quiet_hours_group("23:00", "07:00")
    readout = re.search(
        r'<p class="time-value %s"([^>]*)>(.*?)</p>'
        % re.escape(config_page.QUIET_DIAL_READOUT_CLASS), markup, re.DOTALL)
    assert readout, "the card renders no dial readout"
    span = config_page.quiet_window_span("23:00", "07:00")
    expected_text = "23:00 → 07:00 · %s" % layout.duration_text(span.minutes * 60)
    stripped_text = re.sub(r"<[^>]*>", "", readout.group(2))
    assert stripped_text == expected_text, (
        "the readout reads %r at rest; the span it is drawn from is %d minutes, which "
        "this app's one duration ladder names %r — AT REST this must be byte-identical "
        "to what shipped before the pair seam (27-02-PLAN.md Task 3's own acceptance "
        "bar)" % (stripped_text, span.minutes, expected_text))
    assert 'aria-hidden="true"' in readout.group(1), (
        "the readout is not aria-hidden — both time inputs already announce their own "
        "values natively and this would say the same thing twice (%r)" % readout.group(1))

    # THE THREE CHILDREN, EACH WIRED THROUGH THE EXISTING READOUT SEAM.
    # 28-03-PLAN.md Task 1 (CFG-73 Bug A) widened both halves: the two
    # endpoints now ALSO carry VALUE_CONTROL_READOUT_FORMAT_ATTR="clock"
    # (the readout-scoped clock signal, alongside their existing
    # bare-token template); the duration span no longer carries an EMPTY
    # template at all — it carries its own data-value-readout-base PLUS
    # all four layout.DURATION_ATTRS, each holding a non-empty translated
    # wording, so value-controls.js can compose a live duration from the
    # pair without inventing any language of its own.
    for field, value in (("quiet_hours_start", "23:00"), ("quiet_hours_end", "07:00")):
        endpoint = re.search(
            r'<span %s="%s" %s="%s" %s="%s">%s</span>'
            % (re.escape(layout.VALUE_CONTROL_READOUT_ATTR), re.escape(field),
               re.escape(layout.VALUE_CONTROL_READOUT_FORMAT_ATTR),
               re.escape(layout.VALUE_CONTROL_FORMAT_CLOCK),
               re.escape(layout.VALUE_CONTROL_READOUT_TEXT_ATTR),
               re.escape(layout.VALUE_CONTROL_TEXT_TOKEN), re.escape(value)),
            readout.group(2))
        assert endpoint, (
            "no %s readout span carrying the clock-format attribute and the bare token "
            "template and %r: %r" % (field, value, readout.group(2)))
    duration_span = re.search(
        r'<span %s="quiet_hours_start" %s="(\d+)"((?: %s="[^"]*"){%d})>([^<]*)</span>'
        % (re.escape(layout.VALUE_CONTROL_READOUT_ATTR),
           re.escape(layout.VALUE_CONTROL_READOUT_BASE_ATTR),
           "(?:%s)" % "|".join(re.escape(attr) for attr in layout.DURATION_ATTRS),
           len(layout.DURATION_ATTRS)),
        readout.group(2))
    assert duration_span, (
        "no duration span carrying a data-value-readout-base and all %d "
        "layout.DURATION_ATTRS: %r" % (len(layout.DURATION_ATTRS), readout.group(2)))
    assert int(duration_span.group(1)) == config_page.quiet_window_minute_of_day("23:00"), (
        "the duration span's data-value-readout-base is %s minutes; the saved window's "
        "own start is %d" % (duration_span.group(1),
                              config_page.quiet_window_minute_of_day("23:00")))
    for attr in layout.DURATION_ATTRS:
        assert ('%s="' % attr) in duration_span.group(2), (
            "the duration span is missing %r, one of layout.DURATION_ATTRS: %r"
            % (attr, duration_span.group(2)))
    assert duration_span.group(3) == layout.duration_text(span.minutes * 60), (
        "the duration span's own text is %r at rest, not this app's one duration ladder's "
        "%r" % (duration_span.group(3), layout.duration_text(span.minutes * 60)))

    # CFG-52: NOTHING ON THIS CARD IS A LIVE REGION. Dragging fires
    # continuously and a role="status" here would re-announce the
    # identical phrase on every step — the defect Phase 23 hit with its
    # three switches, and the one this plan exists to avoid.
    for banned in ('role="status"', "aria-live", 'role="alert"', 'role="log"'):
        assert banned not in markup, (
            "the Quiet hours card carries %r — the focused handle's own aria-valuetext "
            "is the native, debounced announcement path and a live region beside it "
            "re-announces the same phrase on every drag step (CFG-52)" % banned)

    # THE FLOOR: NO WINDOW MEANS NO ARC AND NO WORDS, never a full ring
    # and never a zero-length dash (which renders as a dot under a round
    # cap and would read as "a few minutes").
    for start, end, why in (
            ("", "", "nothing stored"),
            ("23:00", "", "half stored"),
            ("99:99", "07:00", "an unparseable start")):
        markup = config_page.quiet_hours_group(start, end)
        assert _dial_circle(markup, config_page.QUIET_DIAL_DAY_CLASS) is not None, (
            "%s: the full-day ring must still draw" % why)
        assert _dial_circle(markup, config_page.QUIET_DIAL_ARC_CLASS) is None, (
            "%s (%r→%r): an arc was emitted anyway — a drawn window claims one is "
            "configured" % (why, start, end))
        assert config_page.QUIET_DIAL_READOUT_CLASS not in markup, (
            "%s (%r→%r): a readout was emitted anyway" % (why, start, end))
    zero = config_page.quiet_hours_group("23:00", "23:00")
    assert _dial_circle(zero, config_page.QUIET_DIAL_ARC_CLASS) is None, (
        "a zero-length window emitted an arc — a zero-length dash is a DOT under a round "
        "cap, so 'no window' would read as a few minutes")
    assert config_page.QUIET_DIAL_READOUT_CLASS in zero, (
        "a zero-length window is a real, stored state (server.device_config calls it "
        "never-active) and its readout must still say so")

    # T-25-04-B: a hostile stored value reaching the arc or readout.
    hostile = config_page.quiet_hours_group(
        "23:00", "07:00",
        submitted={"quiet_hours_start": '"><script>alert(1)</script>',
                   "quiet_hours_end": "07:00"})
    assert "<script>" not in hostile, "an unescaped <script> reached the Quiet hours card"
    assert _dial_circle(hostile, config_page.QUIET_DIAL_ARC_CLASS) is None, (
        "a value that is not a time drew an arc")


def test_the_quiet_dial_readout_carries_clock_format_and_duration_wordings_in_both_languages():
    """quiet_dial_readout_html() carries data-value-readout-format="clock" on both endpoint
    spans and a non-empty value for each of the four layout.DURATION_ATTRS on the duration
    span, in both shipped languages (CFG-73 Bug A, 28-03-PLAN.md Task 3)"""
    # 28-03-PLAN.md Task 3 (CFG-73 Bug A): quiet_dial_readout_html()'s own
    # server-render contract, checked directly rather than only through
    # the byte-identical-at-rest assertion above — both endpoint spans
    # carry the readout-scoped clock-format attribute, and the duration
    # span carries a non-empty value for EVERY one of layout.DURATION_ATTRS,
    # in BOTH shipped languages.
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            markup = config_page.quiet_hours_group("23:00", "07:00")
        finally:
            prefs.set_request_prefs(lang="en")
        readout = re.search(
            r'<p class="time-value %s"([^>]*)>(.*?)</p>'
            % re.escape(config_page.QUIET_DIAL_READOUT_CLASS), markup, re.DOTALL)
        assert readout, "lang=%s: the card renders no dial readout" % lang
        body = readout.group(2)
        clock_count = body.count(
            '%s="%s"' % (layout.VALUE_CONTROL_READOUT_FORMAT_ATTR,
                         layout.VALUE_CONTROL_FORMAT_CLOCK))
        assert clock_count == 2, (
            "lang=%s: expected %s=%r exactly twice (once per endpoint span), found %d "
            "in %r" % (lang, layout.VALUE_CONTROL_READOUT_FORMAT_ATTR,
                       layout.VALUE_CONTROL_FORMAT_CLOCK, clock_count, body))
        for attr in layout.DURATION_ATTRS:
            m = re.search(r'%s="([^"]*)"' % re.escape(attr), body)
            assert m, "lang=%s: the duration span carries no %r: %r" % (lang, attr, body)
            assert m.group(1), (
                "lang=%s: %r is present but EMPTY — every bucket wording must be "
                "non-empty so the client never has to invent one: %r"
                % (lang, attr, body))


def test_the_ring_is_an_addition_and_the_four_controls_are_untouched():
    """the ring is an ADDITION: both native <input type="time"> fields keep their value/
    required/lang/form attributes and are never disabled, B14's visible 24h sibling still
    renders beside each, the three presets keep the data attributes dirty-state.js writes
    through, the one section caption is EXACTLY QUIET_HOURS_SECTION_CAPTION with no
    appended delay sentence (29-05-PLAN.md Task 2, CFG-79), the card's order is
    caption → ring → presets → Start → End with the four controls' own order and adjacency
    untouched and no side-by-side row, and the arc echoes the SUBMITTED window on a
    rejected save rather than the stored one (B14/D-07/CFG-48, 25-04-PLAN.md Task 2)

    CFG-48 (25-04-PLAN.md Task 2): B14 has been broken once already, and
    the two time inputs are the only controls on this card a visitor can
    TYPE into.
    """
    for start, end, submitted in (
            ("23:00", "07:00", None),
            ("08:00", "18:00", None),
            ("", "", None),
            ("23:00", "07:00", {"quiet_hours_start": "07:30",
                                "quiet_hours_end": "zz"})):
        markup = config_page.quiet_hours_group(
            start, end, submitted=submitted,
            errors={"quiet_hours_end": "Bad"} if submitted else None)
        effective_start = config_page._submitted_or_current(
            submitted, "quiet_hours_start", start)
        effective_end = config_page._submitted_or_current(
            submitted, "quiet_hours_end", end)

        # BOTH NATIVE TIME INPUTS, with every attribute the card's own
        # docstring locks — and NEVER `disabled`, which 10-RESEARCH.md's
        # Open Question 2 settled in the affirmative (a window may be
        # pre-configured whether or not quiet hours is currently on).
        for field, effective in (("quiet_hours_start", effective_start),
                                 ("quiet_hours_end", effective_end)):
            tag = re.search(r'<input type="time" name="%s"[^>]*>' % field, markup)
            assert tag, (
                "%r→%r: no <input type=\"time\" name=%r> — the dial is an ADDITION and "
                "the native input is what the form posts" % (start, end, field))
            element = tag.group(0)
            for needed in ('value="%s"' % escape_html(effective), " required",
                           'lang="%s"' % prefs.current_lang(),
                           'form="%s"' % config_page.SETTINGS_FORM_ID):
                assert needed in element, (
                    "%r→%r: %s lost %r — %s" % (start, end, field, needed, element))
            assert "disabled" not in element, (
                "%r→%r: %s is disabled; neither time input may ever be, whatever the "
                "on/off state is — %s" % (start, end, field, element))

        # B14's VISIBLE 24h SIBLING, present verbatim beside each input. A
        # browser in en-US renders the stored "23:00" as "11:00 PM"
        # directly beside a preset labelled "Night (23:00-07:00)"; this
        # element is the fix, and a dial that removed it would reopen a
        # closed defect.
        for field, effective in (("quiet_hours_start", effective_start),
                                 ("quiet_hours_end", effective_end)):
            sibling = config_page._normalised_time_html(effective)
            assert not (sibling and sibling not in markup), (
                "%r→%r: B14's visible 24h sibling for %s (%r) is gone from the card"
                % (start, end, field, sibling))
            assert not (sibling and markup.count(sibling) < 1), (
                "%r→%r: %s's 24h sibling is not rendered" % (start, end, field))

        # THE THREE PRESETS, and the data attributes dirty-state.js writes
        # into the two fields from. The dial reads FROM those same
        # fields, which is what makes a preset move the handles with no
        # code at all.
        presets = re.findall(r'<button type="button" %s[^>]*>'
                             % re.escape(config_page.QUIET_HOURS_PRESET_ATTR), markup)
        assert len(presets) == 3, (
            "%r→%r: expected the three presets, got %d" % (start, end, len(presets)))
        for needed in ('data-preset-start="%s"' % config_page.QUIET_HOURS_PRESET_NIGHT_START,
                       'data-preset-end="%s"' % config_page.QUIET_HOURS_PRESET_NIGHT_END,
                       'data-preset-start="%s"' % config_page.QUIET_HOURS_PRESET_WORKDAY_START,
                       'data-preset-end="%s"' % config_page.QUIET_HOURS_PRESET_WORKDAY_END,
                       'data-preset-enabled="0"'):
            assert needed in markup, "%r→%r: the preset row lost %r" % (start, end, needed)

        # THE CAPTION, exactly one caption element — the one-caption-per-
        # section rule, which a drawing is the obvious way to break.
        #
        # 29-05-PLAN.md Task 2 (CFG-79): retargeted from "starts with the
        # static sentence, then carries something longer" (the computed
        # delay sentence used to be appended here) to exact equality —
        # quiet_hours_group() no longer accepts a `delay_sentence`
        # keyword at all, and the caption is now ONE sentence, full stop.
        # The property that survives — the Frame strip still carries the
        # computed delay sentence — is pinned by its own dedicated checks
        # below, against the Frame strip's own markup, not this card's.
        caption = re.search(
            r'<p class="text-label section-caption" id="%s">([^<]*)</p>'
            % re.escape(config_page.QUIET_HOURS_SECTION_CAPTION_ID), markup)
        assert caption, "%r→%r: the section caption is gone" % (start, end)
        assert markup.count('class="text-label section-caption"') == 1, (
            "%r→%r: the card renders %d section captions; one section, one caption"
            % (start, end, markup.count('class="text-label section-caption"')))
        assert caption.group(1) == escape_html(config_page.QUIET_HOURS_SECTION_CAPTION), (
            "%r→%r: expected the caption to be EXACTLY QUIET_HOURS_SECTION_CAPTION "
            "with no appended delay sentence, got %r"
            % (start, end, caption.group(1)))

        # THE LOCKED ORDER, AND WHERE THE RING JOINS IT. 29-04-PLAN.md
        # Task 1 (CFG-80) re-derives this list: the four controls keep
        # their positions and their adjacency (presets before Start,
        # Start before End), but Start and End are now ONE element in
        # document order — the QUIET_TIMES_ROW_CLASS wrapper — rather
        # than two separately-indexed labels, since that wrapper is what
        # now lays them out side by side. The readout is OMITTED, not
        # fabricated, for an unparseable span (the ("", "", None) case in
        # this very loop) — matching quiet_dial_readout_html()'s own
        # "omit, don't fabricate" rule, so it is only checked for order
        # when it actually rendered.
        positions = [
            ("caption", markup.index('class="text-label section-caption"')),
            ("dial", markup.index('class="%s"' % config_page.QUIET_DIAL_CLASS)),
            ("presets", markup.index('class="%s"' % config_page.QUIET_PRESET_ROW_CLASS)),
            ("times_row", markup.index('class="%s"' % config_page.QUIET_TIMES_ROW_CLASS)),
        ]
        expected_order = ["caption", "dial", "presets", "times_row"]
        if config_page.QUIET_DIAL_READOUT_CLASS in markup:
            positions.insert(2, ("readout", markup.index(config_page.QUIET_DIAL_READOUT_CLASS)))
            expected_order = ["caption", "dial", "readout", "presets", "times_row"]
        assert [name for name, _ in sorted(positions, key=lambda pair: pair[1])] == expected_order, (
            "%r→%r: the card's order is %r — CFG-80 locks caption, dial, readout, "
            "presets, then the Start/End times row, and the ring is an addition between "
            "the caption and the presets, never a reordering"
            % (start, end, sorted(positions, key=lambda pair: pair[1])))
        # Start still precedes End INSIDE the times row, in document
        # order — the wrapper changed the LAYOUT, never the order.
        assert markup.index('name="quiet_hours_start"') < markup.index('name="quiet_hours_end"'), (
            "%r→%r: Start must still precede End in document order" % (start, end))

        # NOT VIA `.theme-status__row`. CFG-80 puts Start and End side by
        # side through its OWN dedicated `.quiet-times-row` grid, never
        # through the shared `.theme-status__row` class this card has
        # never used — a re-check of the same negative
        # 10-UI-SPEC.md/22-05-PLAN.md history originally recorded here
        # kept true on its own narrow terms even though the broader
        # "never side by side" premise it once supported does not (see
        # quiet_hours_group()'s own docstring for the full supersession).
        assert "theme-status__row" not in markup, (
            "%r→%r: the two time fields used the shared row class" % (start, end))

    # THE D-07 ECHO, WHICH IS WHY THE ARC READS THE EFFECTIVE VALUES. On a
    # rejected save the picture must show what the visitor submitted, not
    # what is stored, or the two disagree on exactly the screen where a
    # mistake is being fixed.
    echoed = config_page.quiet_hours_group(
        "23:00", "07:00", errors={"quiet_hours_end": "Bad"},
        submitted={"quiet_hours_start": "09:00", "quiet_hours_end": "17:00"})
    submitted_span = config_page.quiet_window_span("09:00", "17:00")
    arc = _dial_circle(echoed, config_page.QUIET_DIAL_ARC_CLASS)
    assert arc is not None, "the rejected-save render drew no arc at all"
    drawn = float(arc["stroke-dasharray"].split()[0])
    assert abs(drawn / (2 * math.pi * float(arc["r"])) - submitted_span.sweep_fraction) <= 1e-4, (
        "the rejected-save render drew %.4f of the ring; the SUBMITTED 09:00→17:00 "
        "window is %.4f, and the stored 23:00→07:00 one is %.4f — the arc must echo the "
        "submission, the same D-07 rule the two inputs already follow"
        % (drawn / (2 * math.pi * float(arc["r"])), submitted_span.sweep_fraction,
           config_page.quiet_window_span("23:00", "07:00").sweep_fraction))
    # 27-02-PLAN.md Task 3 (CFG-62): the readout is now three children,
    # not one text node, so the echo is checked per span rather than as
    # one contiguous substring.
    echoed_readout = re.search(
        r'<p class="time-value %s"[^>]*>(.*?)</p>'
        % re.escape(config_page.QUIET_DIAL_READOUT_CLASS), echoed, re.DOTALL)
    assert echoed_readout, "the rejected-save render carries no dial readout at all"
    assert ">09:00<" in echoed_readout.group(1) and ">17:00<" in echoed_readout.group(1), (
        "the rejected-save readout does not echo the submitted window: %r"
        % echoed_readout.group(1))


def test_every_class_the_quiet_hours_card_emits_has_a_real_selector(served_css):
    """every class quiet_hours_group() emits — including the new .quiet-preset-row/
    .quiet-times-row wrappers — resolves to a real selector in style.css, scanned off
    the emitted markup rather than a hand-kept list (CFG-80, 29-04-PLAN.md Task 1)"""
    known_classes = set()
    for rule in css_rules(served_css):
        for selector in rule.selectors:
            known_classes.update(re.findall(r"\.([-\w]+)", selector))
    markup = config_page.quiet_hours_group("23:00", "07:00")
    emitted = set()
    for attr in re.findall(r'class="([^"]*)"', markup):
        emitted.update(attr.split())
    missing = sorted(emitted - known_classes)
    assert not missing, (
        "quiet_hours_group() emits class(es) %r with no selector anywhere in the served "
        "stylesheet — they paint nothing at all" % missing)


def test_both_time_fields_and_twins_sit_inside_the_times_row_with_their_own_error_slot():
    """both <input type="time"> elements, both B14 twins and each field's own error
    paragraph all fall inside the .quiet-times-row container's own slice of the markup,
    across a clean render and a rejected save on either field (CFG-80, 29-04-PLAN.md
    Task 1)

    CFG-80: the times-row wrapper's own slice of the markup must contain
    BOTH native time inputs and both twins, and each field's own error
    paragraph must sit inside that SAME field's column — never
    displacing its sibling's.
    """
    field_slugs = (
        ("quiet_hours_start", "quiet-hours-start"),
        ("quiet_hours_end", "quiet-hours-end"))
    for errors, submitted in (
            (None, None),
            ({"quiet_hours_start": "Bad start"},
             {"quiet_hours_start": "bad", "quiet_hours_end": "07:00"}),
            ({"quiet_hours_end": "Bad end"},
             {"quiet_hours_start": "23:00", "quiet_hours_end": "bad"})):
        markup = config_page.quiet_hours_group(
            "23:00", "07:00", errors=errors, submitted=submitted)
        row_open = '<div class="%s">' % config_page.QUIET_TIMES_ROW_CLASS
        assert row_open in markup, "expected the times-row wrapper to render"
        row_start = markup.index(row_open)
        row_end = markup.index("</div></div>", row_start) + len("</div></div>")
        row_slice = markup[row_start:row_end]
        for field, slug in field_slugs:
            assert 'name="%s"' % field in row_slice, (
                "%s: expected the input inside the times row" % field)
            effective = config_page._submitted_or_current(
                submitted, field, "23:00" if field == "quiet_hours_start" else "07:00")
            twin = config_page._normalised_time_html(effective)
            assert not (twin and row_slice.count(twin) != 1), (
                "%s: expected exactly one twin inside the times row" % field)
            error_html = config_page._field_error_html(errors, field, slug)
            assert not (error_html and error_html not in row_slice), (
                "%s: expected its own error paragraph inside the times row" % field)


def test_the_three_preset_buttons_render_short_labels_with_no_colon_in_both_languages():
    """the three preset buttons render the short labels Night/Day/Always on and Nuit/
    Journée/Toujours actif, and NO preset label contains a ':' in either language — the
    hours are spoken once, by the dial's own readout (CFG-80, 29-04-PLAN.md Task 1)

    CFG-80: the hours a preset sets are already spoken by the dial's own
    readout caption — no preset label may spell one, in either language,
    stated as a PROPERTY (no colon character) not as three literal
    string comparisons.
    """
    for lang, labels in (
            ("en", ("Night", "Day", "Always on")),
            ("fr", ("Nuit", "Journée", "Toujours actif"))):
        prefs.set_request_prefs(lang=lang)
        try:
            markup = config_page.quiet_hours_group("23:00", "07:00")
        finally:
            prefs.set_request_prefs(lang="en")
        found = re.findall(
            r'<button type="button" %s[^>]*>([^<]*)</button>'
            % re.escape(config_page.QUIET_HOURS_PRESET_ATTR), markup)
        assert list(found) == list(labels), (
            "%s: expected preset labels %r, got %r" % (lang, labels, found))
        for label in found:
            assert ":" not in label, (
                "%s: preset label %r still spells an hour with a colon" % (lang, label))


def test_the_times_row_rule_declares_exactly_two_grid_tracks(served_css):
    """style.css's .quiet-times-row rule declares display: grid with a
    grid-template-columns of exactly two tracks, parsed from the stylesheet itself
    (CFG-80, 29-04-PLAN.md Task 1)"""
    decl = declarations_for(served_css, ".%s" % config_page.QUIET_TIMES_ROW_CLASS)
    assert decl.get("display") == "grid", (
        "expected .%s to declare display: grid" % config_page.QUIET_TIMES_ROW_CLASS)
    match = re.search(r"repeat\((\d+)", decl.get("grid-template-columns", ""))
    assert match and int(match.group(1)) == 2, (
        "expected .%s's grid-template-columns to declare exactly two tracks, got %r"
        % (config_page.QUIET_TIMES_ROW_CLASS, decl.get("grid-template-columns")))


def test_check_a_the_twin_is_visible_in_the_served_markup_in_both_languages():
    """Check A — the scripts-blocked state, proven from the served markup: rendering
    /display's quiet-hours card in both languages emits exactly two hook-attribute
    spans, each rendering the SAME text as its own field's value attribute (a
    relationship, never a literal), with none carrying hidden/js-gate/style — the
    served HTML IS what a scripts-blocked reader sees (CFG-80, 29-04-PLAN.md Task 3)

    Check A (29-04-PLAN.md Task 3): with no script running, the served
    HTML IS what a scripts-blocked reader sees — so a VISIBLE twin in the
    served HTML, for both fields, in both languages, IS the
    scripts-blocked proof. This asserts a fact about the served markup,
    never about a browser.
    """
    for lang in ("en", "fr"):
        prefs.set_request_prefs(lang=lang)
        try:
            markup = config_page.quiet_hours_group("23:00", "07:00")
        finally:
            prefs.set_request_prefs(lang="en")
        # Broad open-tag match FIRST, deliberately loose about what sits
        # between the hook attribute and the closing `>` — a mutation
        # that inserts `hidden` (or any other attribute) between them
        # must still be CAUGHT here, by name, rather than silently making
        # the narrower two-span count below find zero and report a
        # vaguer failure.
        open_tags = re.findall(
            r'<span class="text-label field-inline-value"[^>]*%s[^>]*>'
            % re.escape(config_page.QUIET_NORMALISED_TIME_ATTR), markup)
        assert len(open_tags) == 2, (
            "%s: expected exactly two hook-attribute spans, got %d: %r"
            % (lang, len(open_tags), open_tags))
        for tag in open_tags:
            # Boundary-anchored: "aria-hidden" (which this tag is
            # SUPPOSED to carry, per B14) contains the substring "hidden"
            # and must not trip this check.
            assert not re.search(r"(?<![-\w])hidden(?![-\w])", tag), (
                "%s: the twin's own tag carries hidden=: %r" % (lang, tag))
            for forbidden in ("js-gate", "style="):
                assert forbidden not in tag, (
                    "%s: the twin's own tag carries %r: %r" % (lang, forbidden, tag))
        hook_spans = re.findall(
            r'<span class="text-label field-inline-value"[^>]*%s[^>]*>([^<]*)</span>'
            % re.escape(config_page.QUIET_NORMALISED_TIME_ATTR), markup)
        for field in ("quiet_hours_start", "quiet_hours_end"):
            field_match = re.search(
                r'<input type="time" name="%s" value="([^"]*)"' % field, markup)
            assert field_match, "%s: no %s input found" % (lang, field)
            value = field_match.group(1)
            assert value in hook_spans, (
                "%s: %s's own field value %r has no matching hook-attribute span "
                "among %r — the twin must render the SAME text as its own field, "
                "as a relationship, not a hardcoded literal"
                % (lang, field, value, hook_spans))


def test_check_b_the_hide_path_is_gated_on_one_strict_condition(value_controls_js):
    """Check B — the hide path is gated, and gated on one thing only: exactly one
    `.hidden = true` assignment on the hook attribute, gated by a strict `hour12 ===
    false` comparison (never a truthiness test), with the Intl/resolvedOptions
    availability guard preceding it, and a vacuity floor on the comment-stripped
    source's own length ratio and hook-literal count (CFG-80, 29-04-PLAN.md Task 3)

    Check B (29-04-PLAN.md Task 3): the hide assignment must be reachable
    through exactly one strict, guarded branch.

    Comment-stripped first, this file's own comments quote the very
    tokens this scan counts.
    """
    raw = value_controls_js
    stripped = re.sub(r"/\*.*?\*/|//[^\n]*", "", raw, flags=re.DOTALL)

    # VACUITY FLOOR. A mangled strip must not let this check pass over
    # nothing — bounded on BOTH sides, not just a lower floor, since this
    # specific file is genuinely comment-dense (measured: ~32% code
    # remains after stripping, because its header alone runs to over a
    # hundred lines of prose). A ratio near 0% means the strip ate real
    # code; a ratio near 100% means the strip did nothing at all (this
    # file's comments quote the very tokens this scan counts, so an
    # unstripped source could pass by matching its OWN prose rather than
    # real code).
    ratio = float(len(stripped)) / float(len(raw)) if raw else 0.0
    assert 0.05 < ratio < 0.95, (
        "comment-stripped source is %d chars of %d raw (%.0f%%) — outside the "
        "[5%%, 95%%] band this file's own real comment density should land in; the "
        "strip looks broken" % (len(stripped), len(raw), ratio * 100.0))
    # This file's own convention (WRAPPER_ATTR, FIELD_ATTR, ...) is the
    # raw string literal ONCE, in a `var NAME = "literal";` declaration,
    # then every other reference by the CONSTANT NAME — so the "hook
    # literal" this vacuity floor counts is the constant's own NAME, not
    # a second copy of the raw string.
    hook_name_count = stripped.count("NORMALISED_TIME_ATTR")
    assert hook_name_count >= 2, (
        "expected the hook constant NORMALISED_TIME_ATTR to appear at least twice "
        "in the comment-stripped source (its own declaration + the selector that "
        "reads it), found %d — the hook may have been renamed on one side only"
        % hook_name_count)

    hidden_assignments = list(re.finditer(r"\.hidden\s*=\s*true\b", stripped))
    assert len(hidden_assignments) == 1, (
        "expected exactly one `.hidden = true` assignment gated on the hook "
        "attribute, found %d — a second, ungated path could otherwise be added "
        "silently" % len(hidden_assignments))
    assign_at = hidden_assignments[0].start()

    # Found from the ASSIGNMENT's own nearest enclosing branch, not from a
    # bare file-wide search for the strict pattern — so a relaxed
    # condition (a truthiness test, `!= true`, a negation) is reported BY
    # ITS OWN TEXT, printed on failure, rather than producing a generic
    # "not found anywhere" message.
    if_before = stripped.rfind("if (", 0, assign_at)
    assert if_before != -1, "the .hidden = true assignment is not inside any if (...) branch"
    condition_text = stripped[if_before:stripped.index(")", if_before) + 1]
    assert re.search(r"hour12\s*===\s*false", condition_text), (
        "the assignment's own nearest enclosing branch condition is %r — not a "
        "strict `hour12 === false` comparison, not a truthiness test, not `!= "
        "true`, not a negation of a truthy read" % condition_text)

    guard_match = re.search(r"resolvedOptions", stripped)
    assert guard_match and guard_match.start() <= if_before, (
        "the Intl/resolvedOptions availability guard does not precede the "
        "hour12 determination (guard at %r, branch at %r)"
        % (guard_match.start() if guard_match else None, if_before))


_DECODE_QUIET_CASES = (
    ("23:00", "07:00", None, None),
    ("08:00", "18:00", None, None),
    ("23:00", "07:00",
     {"quiet_hours_end": "Bad"},
     {"quiet_hours_start": "09:00", "quiet_hours_end": "17:00"}),
)


def _decode_quiet_arc_pair(markup):
    arc = _dial_circle(markup, config_page.QUIET_DIAL_ARC_CLASS)
    if arc is None:
        return None
    transform_match = re.search(r"rotate\(([-\d.]+)\s", arc.get("transform", ""))
    dash = arc.get("stroke-dasharray", "")
    if not transform_match or not dash:
        return None
    deg = float(transform_match.group(1))
    start_fraction = (
        (deg - config_page._QUIET_DIAL_TWELVE_OCLOCK_DEG)
        / config_page._QUIET_DIAL_FULL_TURN_DEG) % 1.0
    r = float(arc["r"])
    drawn = float(dash.split()[0])
    sweep_fraction = drawn / (2 * math.pi * r)
    start_minute = int(round(start_fraction * 1440)) % 1440
    sweep_minute = int(round(sweep_fraction * 1440))
    return (start_minute, (start_minute + sweep_minute) % 1440)


def _decode_quiet_handles_pair(markup):
    def valuenow(field):
        m = re.search(
            r'data-value-field="%s"[^>]*>.*?aria-valuenow="(\d+)"' % re.escape(field),
            markup, re.DOTALL)
        return int(m.group(1)) if m else None
    start, end = valuenow("quiet_hours_start"), valuenow("quiet_hours_end")
    return None if start is None or end is None else (start, end)


def _decode_quiet_readout_pair(markup):
    def clock_text(field):
        m = re.search(
            r'data-value-readout="%s" data-value-readout-format="clock"[^>]*>'
            r'([^<]*)<' % re.escape(field), markup)
        return m.group(1) if m else None
    start_txt, end_txt = clock_text("quiet_hours_start"), clock_text("quiet_hours_end")
    if not start_txt or not end_txt:
        return None
    start = config_page.quiet_window_minute_of_day(start_txt)
    end = config_page.quiet_window_minute_of_day(end_txt)
    return None if start is None or end is None else (start, end)


def _decode_quiet_fields_pair(markup):
    def field_value(field):
        m = re.search(r'name="%s" value="([^"]*)"' % re.escape(field), markup)
        return m.group(1) if m else None
    start_txt = field_value("quiet_hours_start")
    end_txt = field_value("quiet_hours_end")
    if not start_txt or not end_txt:
        return None
    start = config_page.quiet_window_minute_of_day(start_txt)
    end = config_page.quiet_window_minute_of_day(end_txt)
    return None if start is None or end is None else (start, end)


def test_check_c_the_four_server_rendered_surfaces_agree():
    """Check C — the four surfaces still agree, at the render level: for 23:00→07:00
    (midnight-wrapping), 08:00→18:00 (non-wrapping) and a rejected-save echo
    (09:00→17:00 submitted over a 23:00→07:00 stored value), the arc's presentation
    attributes, the two handles' aria-valuenow, the readout's endpoint text and both
    <input type="time"> values all decode to the SAME canonical minute-of-day pair
    (CFG-80/CFG-62, 29-04-PLAN.md Task 3)

    Check C (29-04-PLAN.md Task 3): CFG-62's own surfaces-agree check is
    browser-level and cannot run here — but the SERVER's four surfaces
    (the arc's presentation attributes, the two handles' aria-valuenow,
    the readout's own endpoint text, and both <input type="time"> values)
    are all computed in quiet_hours_group() from the SAME
    effective_start/effective_end pair, and that agreement is provable
    from the rendered markup alone. This is a GUARD against Task 1's own
    markup restructuring silently breaking Phase 27's agreement — it is
    NOT a replacement for the browser-level preset-click check in
    test_browser_ux.py, which this worktree cannot run.
    """
    for start, end, errors, submitted in _DECODE_QUIET_CASES:
        markup = config_page.quiet_hours_group(
            start, end, errors=errors, submitted=submitted)
        decoded = {
            "arc": _decode_quiet_arc_pair(markup),
            "handles": _decode_quiet_handles_pair(markup),
            "readout": _decode_quiet_readout_pair(markup),
            "fields": _decode_quiet_fields_pair(markup),
        }
        distinct = set(decoded.values())
        assert len(distinct) == 1, (
            "%r/%r (errors=%r, submitted=%r): the four surfaces disagree: %r"
            % (start, end, errors, submitted, decoded))


def test_the_dials_paint_resolves_and_decides_nothing_in_python(served_css):
    """the quiet dial's paint resolves — every class the EMITTED markup carries has a real
    selector (scanned off the markup, boundary-anchored), every shape carries a class, an
    explicit fill="none" and a stroke width, the canvas declares its viewBox, its
    intrinsic size, aria-hidden and focusable, no colour is decided in Python, the day
    ring/arc/hour labels each paint from a theme token so both themes are correct from one
    rule, no accent appears anywhere in the component, and no rule declares stroke-width in
    CSS where it would beat the derived presentation attribute (CFG-48/CFG-52,
    25-04-PLAN.md Task 2)

    CFG-48/CFG-52 (25-04-PLAN.md Task 2): the dial's paint, asserted as
    one thing because the parts fail together. A class that exists in
    Python and nowhere in the stylesheet paints nothing at all, and
    nothing else in this codebase would notice.
    """
    markup = config_page.quiet_hours_group("23:00", "07:00")
    # From the dial's own opening tag to the end of its readout — the
    # whole component, handle layer included, so a class added inside
    # the gate is scanned on exactly the same terms as one outside it.
    dial = markup[markup.index('<div class="%s"' % config_page.QUIET_DIAL_CLASS):]
    dial = dial[:dial.index("</p>", dial.index(
        config_page.QUIET_DIAL_READOUT_CLASS)) + len("</p>")]

    # NO COLOUR DECIDED IN PYTHON. A literal here is correct in one theme
    # and invisible in the other, and invisible to the contrast harness
    # too.
    colours = re.findall(r"#[0-9a-fA-F]{3,8}|rgba?\(", dial + " " + markup[
        markup.index(config_page.QUIET_DIAL_READOUT_CLASS):][:400])
    assert not colours, "the dial's emitted markup carries colour literals %r" % (colours,)

    # EVERY CLASS THE EMITTED MARKUP CARRIES RESOLVES TO A REAL SELECTOR,
    # scanned off the markup rather than off a list of constants — the
    # failure being defended against is a class that exists in Python and
    # nowhere in the stylesheet, which a list written by the same hand
    # would share.
    known_classes = set()
    for rule in css_rules(served_css):
        for selector in rule.selectors:
            known_classes.update(re.findall(r"\.([-\w]+)", selector))
    emitted = set()
    for attr in re.findall(r'class="([^"]*)"', dial):
        emitted.update(attr.split())
    emitted.add(config_page.QUIET_DIAL_READOUT_CLASS)
    missing = sorted(emitted - known_classes)
    assert not missing, (
        "the dial emits class(es) %r with no selector anywhere in the served stylesheet "
        "— it paints nothing at all and nothing else in this codebase would notice" % missing)

    # EVERY SHAPE HAS A PAINT ROUTE, and the canvas has a size route.
    for tag in re.finditer(r"<circle\b[^>]*>", dial):
        element = tag.group(0)
        assert 'class="' in element, (
            "an unclassed shape: %r — with neither a class nor a fill it takes the SVG "
            "default black, correct in one theme and invisible in the other" % element)
        assert 'fill="none"' in element, (
            "a stroked shape with no explicit fill: %r — the SVG default is a filled "
            "black disc across the middle of the card" % element)
        assert "stroke-width=" in element, "a stroked shape with no stroke width: %r" % element
    svg = re.search(r"<svg\b[^>]*>", dial).group(0)
    for needed in ('viewBox="0 0 %d %d"' % (config_page.QUIET_DIAL_SIZE,
                                            config_page.QUIET_DIAL_SIZE),
                   'width="%d"' % config_page.QUIET_DIAL_SIZE,
                   'height="%d"' % config_page.QUIET_DIAL_SIZE,
                   'aria-hidden="true"', 'focusable="false"'):
        assert needed in svg, (
            "the dial's canvas is missing %r — an <svg> with neither an intrinsic "
            "attribute nor a CSS rule renders at the format's own 300x150 default: %r"
            % (needed, svg))

    # THE PAINT ITSELF: a theme token, never a literal, so both themes are
    # correct from one rule. Accent is reserved (this file's header
    # comment keeps an exhaustive list) and a dial is not on it, so the
    # ring says what it says in INK.
    for selector, token in ((".quiet-dial__day", "--color-border"),
                            (".quiet-dial__arc", "--color-text"),
                            (".quiet-dial__hour", "--color-text")):
        decl = declarations_for(served_css, selector)
        joined = " ".join(decl.values())
        assert token in joined, (
            "%s paints from %r rather than %s — a paint that does not come from a theme "
            "token is correct in one theme only" % (selector, joined, token))
        assert "--color-accent" not in joined, (
            "%s paints accent; the header comment's accent-reservation list is "
            "exhaustive and a dial is not on it" % selector)
        # The presentation attributes must stay presentation attributes: a
        # CSS stroke-width of any specificity beats one, which would
        # flatten the geometry the constants derive.
        assert "stroke-width" not in decl, (
            "%s declares stroke-width in CSS, which beats the presentation attribute the "
            "emitter derives from its own size constants" % selector)


_WRAPPER_RE = re.compile(
    r'<div class="([^"]*)"([^>]*\bdata-value-control\b[^>]*)>(.*?)</div>', re.DOTALL)


def test_the_two_handles_are_gated_and_hold_no_value_of_their_own(value_controls_js, served_css):
    """the quiet dial's two handles are real <button type="button"> sliders INSIDE 25-01's
    .js gate and nowhere else (every element carrying the wrapper attribute carries the
    gate class itself, and every element carrying the handle attribute is inside a
    wrapper); each carries role/aria-valuemin/aria-valuemax/aria-valuenow and an
    aria-valuetext that is the HH:MM its own input holds rather than a minute count, plus a
    translated aria-label in both languages; each wrapper carries layout's own steering
    attributes including the clock codec, is painted at the fraction its input's value
    implies, and names --value-fraction in all three files it travels through; the
    aria-valuetext token is not one of the format artefacts the i18n harness scans French
    renders for; and an end that does not parse gets no handle at all (CFG-48,
    25-04-PLAN.md Task 3)

    CFG-48 (25-04-PLAN.md Task 3): two real `<button>` sliders, inside
    the gate and nowhere else, announcing the value the two native inputs
    already hold.

    The point every clause below defends: the handles are a LAYER.
    Delete the script and both times are still rendered, still
    validated, still posted and still saved by the two
    `<input type="time">` fields underneath.
    """
    script = value_controls_js
    css = served_css
    markup = config_page.quiet_hours_group("23:00", "07:00")

    wrappers = _WRAPPER_RE.findall(markup)
    assert len(wrappers) == 2, "expected exactly two gated handle wrappers, got %d" % len(wrappers)

    # EVERY element carrying the wrapper attribute carries the gate class
    # ITSELF. A wrapper rendered outside the gate is the control that
    # renders and does nothing: visible with scripts blocked, inert, and
    # competing with the input that works.
    for tag in re.finditer(r"<[a-zA-Z][-\w]*\b[^>]*>", markup):
        text = tag.group(0)
        if not re.search(r"(?<![-\w])%s(?![-\w])"
                         % re.escape(layout.VALUE_CONTROL_ATTR), text):
            continue
        class_match = re.search(r'\bclass="([^"]*)"', text)
        classes = class_match.group(1).split() if class_match else []
        assert layout.JS_GATE_CLASS in classes, (
            "an element carries %s outside the %r gate: %s"
            % (layout.VALUE_CONTROL_ATTR, layout.JS_GATE_CLASS, text))

    # AND NO HANDLE MARKUP OUTSIDE A WRAPPER. The converse of the clause
    # above, and the one a wrapper-only scan is blind to: a
    # <button data-value-handle> rendered beside the gate rather than
    # inside it is a grabbable thing that steers nothing.
    inside = "".join(body for _classes, _attrs, body in wrappers)
    assert markup.count(layout.VALUE_CONTROL_HANDLE_ATTR) == inside.count(
        layout.VALUE_CONTROL_HANDLE_ATTR), (
        "%d element(s) carry %s but only %d are inside a gated wrapper"
        % (markup.count(layout.VALUE_CONTROL_HANDLE_ATTR),
           layout.VALUE_CONTROL_HANDLE_ATTR,
           inside.count(layout.VALUE_CONTROL_HANDLE_ATTR)))

    expected = (("quiet_hours_start", "23:00", 1380, config_page.QUIET_DIAL_START_LABEL),
                ("quiet_hours_end", "07:00", 420, config_page.QUIET_DIAL_END_LABEL))
    for (classes, attrs, body), (field, clock, minute, label) in zip(wrappers, expected):
        assert layout.JS_GATE_CLASS in classes.split(), (
            "the %s wrapper is not gated: %r" % (field, classes))
        # THE STEERING CONTRACT, read off the wrapper. Every name here is
        # companion/layout.py's, never a literal typed twice.
        for attr, value in ((layout.VALUE_CONTROL_FIELD_ATTR, field),
                            (layout.VALUE_CONTROL_FORM_ATTR, config_page.SETTINGS_FORM_ID),
                            (layout.VALUE_CONTROL_MIN_ATTR, "0"),
                            (layout.VALUE_CONTROL_MAX_ATTR, "1439"),
                            (layout.VALUE_CONTROL_STEP_ATTR, "15"),
                            (layout.VALUE_CONTROL_GEOMETRY_ATTR, "angular"),
                            (layout.VALUE_CONTROL_FORMAT_ATTR,
                             layout.VALUE_CONTROL_FORMAT_CLOCK),
                            (layout.VALUE_CONTROL_TEXT_ATTR,
                             layout.VALUE_CONTROL_TEXT_TOKEN)):
            assert ('%s="%s"' % (attr, value)) in attrs, (
                "the %s wrapper does not carry %s=%r: %s" % (field, attr, value, attrs))
        # THE SERVER-PAINTED INITIAL POSITION, without which the handle
        # renders at the top of the ring until something touches it.
        fraction = re.search(r"--value-fraction: ([\d.]+)", attrs)
        assert fraction, "the %s wrapper paints no initial position: %s" % (field, attrs)
        assert abs(float(fraction.group(1))
                   - config_page.quiet_dial_handle_fraction(minute)) <= 1e-6, (
            "the %s handle is painted at %s of a turn; the %d minutes its input holds is "
            "%.6f" % (field, fraction.group(1), minute,
                      config_page.quiet_dial_handle_fraction(minute)))

        # A REAL <button type="button">, never a bare <div>: a button is
        # focusable, activatable and announced with no ARIA at all, and
        # `type="button"` is what stops Enter on a handle from submitting
        # the settings form.
        handle = re.search(r'<button\b[^>]*%s[^>]*>'
                           % re.escape(layout.VALUE_CONTROL_HANDLE_ATTR), body)
        assert handle, "the %s wrapper's handle is not a <button>: %r" % (field, body)
        for needed in ('type="button"', 'role="slider"', 'aria-valuemin="0"',
                       'aria-valuemax="1439"', 'aria-valuenow="%d"' % minute,
                       'aria-valuetext="%s"' % clock,
                       'aria-label="%s"' % escape_html(label)):
            assert needed in handle.group(0), (
                "the %s handle is missing %r — %s" % (field, needed, handle.group(0)))
        # THE ANNOUNCED VALUE IS THE TIME, NOT THE MINUTE COUNT. A screen
        # reader reading "one thousand three hundred and eighty" instead
        # of "23:00" is the whole reason aria-valuetext exists.
        assert 'aria-valuetext="%d"' % minute not in handle.group(0), (
            "the %s handle announces its minute count, not its time" % field)
        # AND IT IS THE VALUE THE INPUT ACTUALLY HOLDS.
        tag = re.search(r'<input type="time" name="%s"[^>]*>' % field, markup)
        assert ('value="%s"' % clock) in tag.group(0), (
            "the %s handle announces %r while its own input holds something else: %s"
            % (field, clock, tag.group(0)))

    # BOTH ENDS OF THE SEAM, PINNED. A rename on either side alone is a
    # control that renders and steers nothing, and nothing else in this
    # tree would notice.
    assert ('"%s"' % layout.VALUE_CONTROL_FORMAT_ATTR) in script, (
        "value-controls.js does not name %r" % layout.VALUE_CONTROL_FORMAT_ATTR)
    for wire in ('=== "%s"' % layout.VALUE_CONTROL_FORMAT_CLOCK, '=== "angular"'):
        assert wire in script, (
            "value-controls.js never compares against %r, so the markup's own value is "
            "read by nothing" % wire)
    # THE PAINTED POSITION, PINNED IN ALL THREE FILES IT TRAVELS THROUGH —
    # the server writes it, the script rewrites it, the stylesheet reads
    # it. It has no Python constant (see companion/layout.py for why), so
    # this is the guard instead.
    for where, source, needle in (
            ("the emitted markup", markup, "--value-fraction:"),
            ("value-controls.js", script, '"--value-fraction"'),
            ("style.css", css, "var(--value-fraction")):
        assert needle in source, (
            "%s does not name --value-fraction (%r) — the handle's position travels on "
            "that property through all three, and a rename in one leaves it pinned at "
            "the start of its own range" % (where, needle))
    # THE TOKEN THAT REACHES A RENDERED PAGE. "{}" here fails
    # companion/test_i18n.py's French-render artefact scan, which is why
    # it is not "{}" any more.
    assert layout.VALUE_CONTROL_TEXT_TOKEN not in ("{}", "%s", "%d"), (
        "layout.VALUE_CONTROL_TEXT_TOKEN is %r, which is one of the format artefacts the "
        "i18n harness scans every French render for — it reaches the browser as an "
        "attribute value on a rendered page" % layout.VALUE_CONTROL_TEXT_TOKEN)
    assert ('"%s"' % layout.VALUE_CONTROL_TEXT_TOKEN) in script, (
        "value-controls.js does not name the token %r" % (layout.VALUE_CONTROL_TEXT_TOKEN,))

    # THE FRENCH ACCESSIBLE NAMES. A handle whose only name is English is
    # a control a French screen-reader user cannot tell apart from the
    # other one.
    prefs.set_request_prefs(lang="fr")
    try:
        french = config_page.quiet_hours_group("23:00", "07:00")
    finally:
        prefs.set_request_prefs(lang="en")
    for label in (config_page.QUIET_DIAL_START_LABEL, config_page.QUIET_DIAL_END_LABEL):
        translated = i18n_fr.CATALOG.get(label)
        assert translated and translated != label, "%r has no French sibling" % label
        assert ('aria-label="%s"' % escape_html(translated)) in french, (
            "the French render does not name the handle %r" % translated)

    # OMIT, DON'T FABRICATE: an end that does not parse gets no handle,
    # because a handle at an invented position claims a value that was
    # never set.
    for start, end, expected_handles in (("23:00", "", 1), ("", "", 0), ("zz", "07:00", 1)):
        partial = config_page.quiet_hours_group(start, end)
        got = len(_WRAPPER_RE.findall(partial))
        assert got == expected_handles, (
            "%r→%r emitted %d handle(s), expected %d"
            % (start, end, got, expected_handles))


def test_the_handle_rides_the_ring_the_emitter_drew(served_css):
    """the quiet dial's handle rides the ring the emitter drew — the stylesheet's dial width
    and handle radius equal config_page.QUIET_DIAL_SIZE and QUIET_DIAL_RADIUS, the shared
    handle rule still follows the shared hit-area rule so the absolute `position` wins at
    equal specificity, both stacked layers are pointer-transparent while the handle itself
    is not, the transform reads both custom properties, no z-index re-decides the
    document-order overlap rule, and the grip paints from theme tokens with no accent
    (CFG-48/CFG-52, 25-04-PLAN.md Task 3)

    Two numbers have to agree across two files here — the dial's rendered
    width and the radius the handle is thrown out to — and two numbers
    that have to agree and live in two files agree until one of them is
    edited.
    """
    dial_decl = declarations_for(served_css, ".quiet-dial")
    width_match = re.search(r"(\d+)px", dial_decl.get("width", ""))
    assert width_match and int(width_match.group(1)) == config_page.QUIET_DIAL_SIZE, (
        "the dial's CSS width is %r and its emitter draws a %dpx canvas — the handle is "
        "positioned against the CSS box and the arc is drawn in the canvas, so a "
        "mismatch puts the grip off the stroke it steers"
        % (dial_decl.get("width"), config_page.QUIET_DIAL_SIZE))
    radius_match = re.search(r"(\d+)px", dial_decl.get("--quiet-dial-radius", ""))
    assert radius_match and int(radius_match.group(1)) == config_page.QUIET_DIAL_RADIUS, (
        "the handle rides a radius of %r; the ring's own stroke centre line is %dpx"
        % (dial_decl.get("--quiet-dial-radius"), config_page.QUIET_DIAL_RADIUS))

    # THE SOURCE-ORDER PIN. The handle wears three classes and two of
    # them declare `position` at equal (0,1,0) specificity, so the later
    # rule wins — and the one that must win is the absolute one, or the
    # handle stops being positioned against the ring at all.
    hit_at = served_css.index(".control-hit-area {")
    handle_at = served_css.index(".value-control__handle {")
    assert handle_at >= hit_at, (
        "the shared .value-control__handle rule now precedes the shared hit-area rule; "
        "both declare `position` at equal specificity, so the relative one would win and "
        "the handle would sit wherever the text flow put it")

    # THE POINTER DISCIPLINE. Two full-size layers are stacked over the
    # ring; without these three declarations the upper one swallows every
    # press meant for the ring or for the other end.
    for selector, expected in ((".quiet-dial__handles", "none"),
                               (".quiet-dial__handle-track", "none"),
                               (".quiet-dial__handle", "auto")):
        decl = declarations_for(served_css, selector)
        assert decl.get("pointer-events") == expected, (
            "%s does not declare `pointer-events: %s` — with two full-size layers "
            "stacked over one ring, the upper one otherwise claims every press"
            % (selector, expected))

    handle_decl = declarations_for(served_css, ".quiet-dial__handle")
    joined = " ".join(handle_decl.values())
    for needed in ("var(--value-fraction", "var(--quiet-dial-radius"):
        assert needed in joined, "the handle's transform does not read %r: %s" % (needed, handle_decl)
    # Z-ORDER IS DOCUMENT ORDER, WHICH IS THE STATED DECISION: the END
    # handle is emitted second and therefore wins a pointer-down in an
    # overlap. A z-index on either would silently re-decide it.
    assert "z-index" not in handle_decl, (
        "the handle declares a z-index; the overlap decision this control records is "
        "document order, and a z-index re-decides it somewhere nobody is looking")
    # Paint from tokens, and no accent — the header comment's reservation
    # list is exhaustive and a dial is not on it.
    assert "--color-accent" not in joined, "the handle paints accent"
    for token in ("var(--color-canvas)", "var(--color-text)"):
        assert token in joined, (
            "the handle does not paint from %s — the shared hit-area class is "
            "transparent and borderless by design, so a handle wearing it and nothing "
            "else is invisible" % token)


def test_the_pair_seam_publishes_both_handles_onto_the_shared_ancestor(value_controls_js, served_css):
    """the pair seam publishes both handles onto the shared ancestor (CFG-62, 27-02-PLAN.md
    Tasks 1-2) — value-controls.js names both data-value-pair* attributes and reuses
    ancestorWith() rather than a second walker (still exactly 2 'while (node' loops); the
    .quiet-dial ancestor carries the pair marker (its own value naming the derived sweep
    property) and all three fractions, computed from the SAME span triple the arc is drawn
    from; the two handles publish under DIFFERENT, correctly-named properties; the arc's own
    presentation attributes are untouched real user-unit values (no pathLength, measured to
    corrupt them); and the .js-scoped override rule reads the three ancestor properties plus
    the existing --quiet-dial-radius, never a radius literal

    CFG-62 (27-02-PLAN.md Tasks 1-2): the ancestor carries the pair
    marker and all three fractions, computed from the SAME span the arc
    is drawn from; each handle names which one is its own; the script
    names both attributes and reuses the existing ancestor walker rather
    than a second one; and the presentation attributes this rule
    overrides stay untouched.
    """
    script = value_controls_js
    css = served_css

    # THE SCRIPT NAMES BOTH ATTRIBUTES, AND REUSES ancestorWith() RATHER
    # THAN A SECOND WALKER. `while (node` is ancestorWith()'s own loop and
    # ancestorForm()'s; a plan that added a second walker would show a
    # THIRD occurrence here.
    for needle in ('"data-value-pair"', '"data-value-pair-property"'):
        assert needle in script, "value-controls.js does not name %s" % needle
    walker_loops = script.count("while (node")
    assert walker_loops == 2, (
        "value-controls.js has %d 'while (node' loops, expected exactly 2 "
        "(ancestorWith() and ancestorForm()) — the pair seam must reuse "
        "ancestorWith() rather than add a second walker" % walker_loops)

    markup = config_page.quiet_hours_group("23:00", "07:00")
    span = config_page.quiet_window_span("23:00", "07:00")
    end_fraction = (span.start_fraction + span.sweep_fraction) % 1.0

    dial_tag = re.search(r"<div class=\"quiet-dial\"[^>]*>", markup)
    assert dial_tag, "no .quiet-dial opening tag in the markup"
    assert ('%s="%s"' % (config_page.QUIET_DIAL_PAIR_ATTR,
                          config_page.QUIET_DIAL_PAIR_PROPERTIES["sweep"])) in dial_tag.group(0), (
        "the .quiet-dial ancestor does not carry %s=%r: %s"
        % (config_page.QUIET_DIAL_PAIR_ATTR,
           config_page.QUIET_DIAL_PAIR_PROPERTIES["sweep"], dial_tag.group(0)))
    for prop, expected in (
            (config_page.QUIET_DIAL_PAIR_PROPERTIES["start"], span.start_fraction),
            (config_page.QUIET_DIAL_PAIR_PROPERTIES["end"], end_fraction),
            (config_page.QUIET_DIAL_PAIR_PROPERTIES["sweep"], span.sweep_fraction)):
        found = re.search(r"%s:\s*([\d.]+)" % re.escape(prop), dial_tag.group(0))
        assert found, (
            "the .quiet-dial ancestor's inline style is missing %s: %s"
            % (prop, dial_tag.group(0)))
        assert abs(float(found.group(1)) - expected) <= 1e-6, (
            "%s is %s on the ancestor; the span it must be computed from (no second "
            "window arithmetic) implies %.6f" % (prop, found.group(1), expected))

    # EACH HANDLE NAMES WHICH PROPERTY IS ITS OWN, AND THE TWO DIFFER.
    wrappers = _WRAPPER_RE.findall(markup)
    assert len(wrappers) == 2, "expected exactly two handle wrappers, got %d" % len(wrappers)
    pair_properties = []
    for _classes, attrs, _body in wrappers:
        found = re.search(
            r'%s="([^"]*)"' % re.escape(config_page.QUIET_DIAL_PAIR_PROPERTY_ATTR), attrs)
        assert found, "a handle wrapper carries no %s: %s" % (
            config_page.QUIET_DIAL_PAIR_PROPERTY_ATTR, attrs)
        pair_properties.append(found.group(1))
    assert pair_properties[0] != pair_properties[1], (
        "both handles publish under the SAME property (%r) — the sweep can only be "
        "derived from two DIFFERENT fractions" % pair_properties[0])
    assert set(pair_properties) == {config_page.QUIET_DIAL_PAIR_PROPERTIES["start"],
                                     config_page.QUIET_DIAL_PAIR_PROPERTIES["end"]}, (
        "the two handles publish %r, not the start/end pair" % (pair_properties,))

    # THE PRESENTATION ATTRIBUTES THIS RULE OVERRIDES ARE UNTOUCHED —
    # still real user-unit values from draw.unit_circle_dash_array(),
    # never pathLength-relative fractions (measured, in this task, to
    # corrupt the no-JS rendering when pathLength="1" is also present;
    # see quiet_dial_svg()'s own docstring).
    arc = _dial_circle(markup, config_page.QUIET_DIAL_ARC_CLASS)
    assert arc is not None, "the dial emits no arc for a real window"
    assert "pathLength" not in arc, (
        "the arc carries pathLength=%r — measured on this tree to corrupt the presentation "
        "attribute's own rendering when combined with real user-unit stroke-dasharray "
        "values (companion/static/style.css's own comment beside the .js override records "
        "the measurement)" % arc.get("pathLength"))
    expected_dash = draw.unit_circle_dash_array(
        span.sweep_fraction, config_page.QUIET_DIAL_RADIUS)
    assert arc["stroke-dasharray"] == expected_dash, (
        "the arc's stroke-dasharray is %r, not %r — the pair seam must not change the "
        "presentation attribute the no-JS floor depends on"
        % (arc["stroke-dasharray"], expected_dash))

    # THE .js-SCOPED OVERRIDE RULE EXISTS, READS THE THREE ANCESTOR
    # PROPERTIES, AND THE EXISTING --quiet-dial-radius (never a radius
    # literal, and never pathLength).
    override = declarations_for(css, ".js .quiet-dial .quiet-dial__arc")
    joined = " ".join(override.values())
    for needle in ("var(--quiet-start-fraction", "var(--quiet-sweep-fraction",
                   "var(--quiet-dial-radius"):
        assert needle in joined, "the .js override rule does not read %r: %s" % (needle, override)
    assert "pathLength" not in joined and "path-length" not in joined, (
        "the .js override rule mentions pathLength: %s" % override)


# ======================================================================
# Section 2: render()'s remaining markup checks, runway_fieldset()'s
# single-root/caption/order proofs, the restored .dirty-bar, and
# poll_trigger_section()'s data-attribute contract.
# ======================================================================


def test_render_exactly_five_dirty_sections_in_order():
    """render() carries exactly five data-dirty-section elements, in document order Runway/
    Diagnostic LED/Quiet hours/Wake interval/Notifications (Theme's own entry retired along
    with theme_fieldset(), 21-05-PLAN.md Task 1 D-06; Calendar's own entry retired from this
    legacy scope by 21-07-PLAN.md Task 1 D-13/Pitfall 2; Display's own entry retired outright
    by 22-05-PLAN.md Task 1 X1/D-04/D-12.1)"""
    rendered = config_page.render({
        "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    found = re.findall(
        r'%s="([^"]*)"' % re.escape(config_page.DIRTY_SECTION_ATTR), rendered)
    expected = [
        "Runway", "Diagnostic LED", "Quiet hours",
        "Wake interval", "Notifications"]
    assert found == expected, "expected %r in document order, got %r" % (expected, found)


def test_runway_fieldset_returns_single_top_level_div():
    """runway_fieldset() returns exactly two div pairs - the top-level .theme-status wrapper
    and the nested .runway-row layout container, not five flat siblings (D-01)"""
    rendered = config_page.runway_fieldset("3")
    assert rendered.startswith('<div class="theme-status"'), (
        "expected runway_fieldset() to start with a single <div class=\"theme-status\"> wrapper")
    assert rendered.endswith("</div>"), (
        "expected runway_fieldset() to end with the wrapper's matching </div>")
    assert rendered.count("<div") == 2 and rendered.count("</div>") == 2, (
        "expected exactly two div pairs - the top-level .theme-status wrapper and the "
        "nested .runway-row layout container")


def test_runway_row_starts_after_caption_and_nothing_follows_it():
    """runway_fieldset() renders RUNWAY_SECTION_CAPTION before .runway-row opens, and no <p
    element after .runway-row closes (quick task 260901-re6)"""
    rendered = config_page.runway_fieldset("3")
    caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
    # 19-11-PLAN.md Task 3 (D-12/A-30): the row now also carries
    # role="radiogroup"/aria-labelledby/aria-describedby, so the opening
    # tag itself is no longer a bare literal; the match still proves
    # there is exactly one .runway-row element.
    row_open = '<div class="runway-row" role="radiogroup"'
    assert rendered.count(row_open) == 1, (
        "expected exactly one <div class=\"runway-row\" role=\"radiogroup\"...> opening tag, "
        "got %d" % rendered.count(row_open))
    caption_pos = rendered.index(caption)
    row_start = rendered.index(row_open)
    assert caption_pos < row_start, "expected RUNWAY_SECTION_CAPTION to render before .runway-row opens"
    row_close = rendered.index("</div>", row_start)
    card_positions = [m.start() for m in re.finditer(r'<label class="runway-card', rendered)]
    assert len(card_positions) == 3, "expected exactly 3 runway-card labels, got %d" % len(card_positions)
    assert all(row_start < pos < row_close for pos in card_positions), (
        "expected all three runway-card labels to fall inside the .runway-row container")
    after_row = rendered[row_close + len("</div>"):]
    assert "<p" not in after_row, (
        "expected no <p element anywhere after .runway-row closes - the retired trailing "
        "helper paragraph must be gone, not merely moved")


def test_runway_section_caption_appears_exactly_once():
    """render() carries RUNWAY_SECTION_CAPTION exactly once (quick task 260901-re6, narrowed by
    21-05-PLAN.md Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired)"""
    rendered = config_page.render({
        "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
    assert rendered.count(runway_caption) == 1, (
        "expected RUNWAY_SECTION_CAPTION exactly once, got %d" % rendered.count(runway_caption))


def test_each_group_emits_exactly_one_caption_between_heading_and_control():
    """runway_fieldset()/led_group() each emit exactly one section-caption <p> element,
    positioned after the group's own naming element and before its control (quick task
    260901-re6, merge of origin/main; narrowed by 21-05-PLAN.md Task 1 D-06 once
    theme_fieldset() is retired)"""
    runway_rendered = config_page.runway_fieldset("3")
    led_rendered = config_page.led_group(True)
    groups = (
        ("runway_fieldset()", runway_rendered, "</h2>", "runway-row", 1),
        # 23-07-PLAN.md Task 2 (D2/CFG-36): the control marker is
        # retargeted in place from "settings-checkbox" to the switch's
        # own class — the LED's control changed, the
        # heading-then-caption-then-control ORDER this row is about did
        # not.
        ("led_group()", led_rendered, "</h2>", 'class="switch"', 1),
    )
    for name, rendered, heading_close_marker, control_marker, expected_p_count in groups:
        assert rendered.count("<p") == expected_p_count, (
            "expected %s to emit exactly %d <p element(s), got %d"
            % (name, expected_p_count, rendered.count("<p")))
        assert rendered.count("section-caption") == 1, (
            "expected %s to emit exactly one section-caption occurrence, got %d"
            % (name, rendered.count("section-caption")))
        heading_close = rendered.index(heading_close_marker)
        caption_pos = rendered.index("section-caption")
        assert heading_close < caption_pos, "expected %s's caption to fall after %s" % (name, heading_close_marker)
        assert control_marker in rendered, "expected %s's control marker %r to be present" % (name, control_marker)
        control_pos = rendered.index(control_marker)
        assert caption_pos < control_pos, (
            "expected %s's caption to fall before its control (%r)" % (name, control_marker))


def test_the_bar_s_save_button_is_the_same_static_fallback_element_relocated():
    """the bar's Save button is the SAME STATIC_SAVE_FALLBACK_ATTR element CFG-64 pins,
    relocated inside .dirty-bar with form="settings-form" — never a second button, and the
    physical <form> itself carries no submit control of its own any more (CFG-77/CFG-78,
    28-08-PLAN.md Task 1)"""
    rendered = config_page.render({
        "device_config": {"theme": "sky", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    assert rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR) == 1, (
        "expected exactly one data-static-save-fallback occurrence, got %d"
        % rendered.count(config_page.STATIC_SAVE_FALLBACK_ATTR))
    button_match = re.search(
        r'<button\b[^>]*%s[^>]*>Save settings</button>'
        % re.escape(config_page.STATIC_SAVE_FALLBACK_ATTR), rendered)
    assert button_match, "expected the fallback attribute on a type=\"submit\" Save settings button"
    assert 'type="submit"' in button_match.group(0), "expected the fallback button to carry type=\"submit\""
    assert 'form="%s"' % config_page.SETTINGS_FORM_ID in button_match.group(0), (
        "expected the relocated fallback button to carry form=%r, preserving native "
        "submission from outside the physical form" % (config_page.SETTINGS_FORM_ID,))
    # THE RELATIONSHIP: the button's own index sits strictly inside
    # `.dirty-bar`'s span, not merely somewhere in the same document.
    bar_open = rendered.index('<div class="dirty-bar"')
    bar_close = rendered.index("</div>", bar_open) + len("</div>")
    attr_pos = rendered.index(config_page.STATIC_SAVE_FALLBACK_ATTR)
    assert bar_open < attr_pos < bar_close, (
        "expected data-static-save-fallback's one occurrence to sit INSIDE the "
        ".dirty-bar element (between its opening tag at %d and its close at %d), got "
        "index %d — a relocation that landed the button outside the bar is not the "
        "relocation CFG-78 asked for" % (bar_open, bar_close, attr_pos))
    # No second submit-shaped control left inside the settings form THAT
    # WOULD ACTUALLY SUBMIT IT, now that the one that did has moved out.
    # The Frame strip's LED quick-switch and the Notifications card's
    # "Send a test" both render a type="submit" button positionally
    # inside this <form>...</form> markup already (D-19/D2's own
    # cross-DOM idiom, predating and unaffected by this plan) — each
    # carries its OWN form= attribute pointing at a DIFFERENT physical
    # form ("quick-led", "notifications-test"), so neither actually
    # submits settings-form despite sitting inside its markup. Only a
    # type="submit" button with NO form= attribute (which would submit
    # its nearest ancestor form — this one) or an explicit
    # form="settings-form" would be a genuine second save affordance for
    # THIS form, and that is what this assertion actually rules out.
    form_open = rendered.index('<form class="config-form"')
    form_close = rendered.index("</form>", form_open) + len("</form>")
    form_markup = rendered[form_open:form_close]
    for tag in re.findall(r'<button\b[^>]*type="submit"[^>]*>', form_markup):
        form_attr_match = re.search(r'\bform="([^"]*)"', tag)
        submits = form_attr_match.group(1) if form_attr_match else config_page.SETTINGS_FORM_ID
        assert submits != config_page.SETTINGS_FORM_ID, (
            "expected the settings <form>...</form> itself to carry NO type=\"submit\" "
            "control that actually submits it any more — the one save affordance now "
            "lives in the bar, outside it — but found %r" % (tag,))


def test_the_dirty_bar_renders_without_hidden_on_every_scope(tmp_path):
    """the restored .dirty-bar renders WITHOUT a hidden attribute on every scope — the no-JS
    floor is the bar's own visible server-rendered state now, not a separate fallback
    button (CFG-77/CFG-78, 28-08-PLAN.md Task 1)

    28-08-PLAN.md Task 1 (CFG-77/CFG-78), 2026-09-16: THE POLARITY
    INVERSION, pinned. The pre-27-04 bar was server-rendered `hidden`
    because a separate always-visible bottom Save button existed as the
    no-JS floor. There is no second button any more — the bar's own
    visible state IS the floor now — so a `hidden` attribute here would
    silently remove the only way a scripts-blocked visitor can save.
    """
    base_ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "state_dir": str(tmp_path), "poll_cooldown_remaining": 0,
    }
    for scope in (config_page.SCOPE_ALL, config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
        rendered = config_page.render(base_ctx, scope=scope)
        bar_open_end = rendered.index(">", rendered.index('<div class="dirty-bar"')) + 1
        bar_open_tag = rendered[rendered.index('<div class="dirty-bar"'):bar_open_end]
        assert "hidden" not in bar_open_tag, (
            "expected NO hidden attribute on .dirty-bar's own opening tag on scope=%r, "
            "got %r — this would silently remove the no-JS save floor" % (scope, bar_open_tag))


def test_nothing_inside_the_bar_is_inert_or_claims_a_dirty_state_that_does_not_exist(tmp_path):
    """no control inside the restored .dirty-bar is inert with scripts blocked (every
    <button>/<input> resolves to type="submit" or type="reset", each form="settings-form"-
    associated, none type="button"), and [data-dirty-count]'s server-rendered content makes
    no claim about unsaved changes existing, in either language (CFG-77/CFG-78,
    28-08-PLAN.md Task 1)

    28-08-PLAN.md Task 1 (CFG-77/CFG-78), 2026-09-16: BLOCKER 4's two
    consequences of the polarity inversion, asserted as one fact because
    both are load-bearing for the identical scripts-blocked visitor.
    """
    base_ctx = {
        "device_config": {"theme": "black", "tracked_runway": "3", "led_enabled": True},
        "state_dir": str(tmp_path), "poll_cooldown_remaining": 0,
    }
    unsaved_claim_strings_en = (
        config_page.DIRTY_BAR_INITIAL_TEXT,
        config_page.DIRTY_UNSAVED_SINGULAR,
        config_page.DIRTY_UNSAVED_PLURAL,
    )
    for scope in (config_page.SCOPE_ALL, config_page.SCOPE_DISPLAY, config_page.SCOPE_DEVICE):
        for lang in ("en", "fr"):
            try:
                prefs.set_request_prefs(lang=lang)
                rendered = config_page.render(base_ctx, scope=scope)
            finally:
                prefs.set_request_prefs(lang="en")
            bar_open = rendered.index('<div class="dirty-bar"')
            bar_close = rendered.index("</div>", bar_open) + len("</div>")
            bar_markup = rendered[bar_open:bar_close]
            # (a) every <button>/<input> inside the bar resolves to
            # type="submit" or type="reset", each form=-associated, and
            # NONE resolves to type="button".
            tags = re.findall(r'<(?:button|input)\b[^>]*>', bar_markup)
            assert tags, (
                "expected at least the Save and Cancel controls inside .dirty-bar on "
                "scope=%r/%s" % (scope, lang))
            for tag in tags:
                type_match = re.search(r'type="([^"]*)"', tag)
                resolved_type = type_match.group(1) if type_match else None
                assert resolved_type != "button", (
                    "expected no control inside .dirty-bar to resolve to type=\"button\" "
                    "on scope=%r/%s — a type=\"button\" control is fully visible and fully "
                    "inert with scripts blocked; got %r" % (scope, lang, tag))
                assert resolved_type in ("submit", "reset"), (
                    "expected every control inside .dirty-bar to resolve to type=\"submit\" "
                    "or type=\"reset\" on scope=%r/%s, got %r in %r" % (scope, lang, resolved_type, tag))
                assert 'form="%s"' % config_page.SETTINGS_FORM_ID in tag, (
                    "expected every control inside .dirty-bar to carry form=%r on "
                    "scope=%r/%s, got %r" % (config_page.SETTINGS_FORM_ID, scope, lang, tag))
            # (b) the count span's server-rendered content makes no claim
            # about unsaved changes existing, in EITHER catalogue's
            # wording — a French render must not leak the English claim
            # either, and vice versa.
            count_start = rendered.index("<span data-dirty-count")
            count_end = rendered.index("</span>", count_start) + len("</span>")
            count_markup = rendered[count_start:count_end]
            for claim_en in unsaved_claim_strings_en:
                claim_fr = layout.i18n.t_lang(claim_en, "fr")
                for claim in (claim_en, claim_fr):
                    assert not (claim and claim in count_markup), (
                        "expected [data-dirty-count]'s server-rendered content to make NO "
                        "claim about unsaved changes on scope=%r/%s, but found %r inside "
                        "%r" % (scope, lang, claim, count_markup))


def test_section_captions_appear_escaped_verbatim_exactly_once():
    """the runway, LED, and poll section captions all appear escaped-verbatim exactly once in
    render()'s output (quick task 260901-re6, quick task 260901-s5o; narrowed by 21-05-PLAN.md
    Task 1 D-06 once THEME_SECTION_CAPTION/theme_fieldset() are retired)"""
    rendered = config_page.render({
        "device_config": {"theme": "black", "tracked_runway": "3"},
        "poll_cooldown_remaining": 0,
    })
    runway_caption = escape_html(config_page.RUNWAY_SECTION_CAPTION)
    led_caption = escape_html(config_page.LED_SECTION_CAPTION)
    poll_caption = escape_html(config_page.POLL_SECTION_CAPTION)
    assert rendered.count(runway_caption) == 1, (
        "expected RUNWAY_SECTION_CAPTION exactly once (escaped-verbatim), got %d"
        % rendered.count(runway_caption))
    assert rendered.count(led_caption) == 1, (
        "expected LED_SECTION_CAPTION exactly once (escaped-verbatim), got %d"
        % rendered.count(led_caption))
    assert rendered.count(poll_caption) == 1, (
        "expected POLL_SECTION_CAPTION exactly once (escaped-verbatim), got %d"
        % rendered.count(poll_caption))


def test_current_theme_and_runway_are_selected():
    """the (non-default) saved runway card is the one marked selected, and this legacy SCOPE_ALL
    render carries zero .theme-chip--selected modifiers now that theme_fieldset(), Calendar's own
    chip grid, and the rules add-form's own chip grid are all retired from it (D-06)"""
    rendered = config_page.render({
        "device_config": {"theme": "black", "tracked_runway": "06-24"},
        "poll_cooldown_remaining": 0,
    })
    # Polish fix 4 (D-14c): each runway radio now also carries an
    # explicit form="settings-form" attribute, inserted between
    # class="visually-hidden" and checked.
    assert ('value="06-24" class="visually-hidden" form="%s" checked'
            % config_page.SETTINGS_FORM_ID) in rendered, (
        "expected the non-default saved runway (06-24) to be marked selected")
    assert ('value="3" class="visually-hidden" form="%s" checked'
            % config_page.SETTINGS_FORM_ID) not in rendered, (
        "expected runway 3 (not the saved value) to NOT be marked selected")
    assert rendered.count("runway-card--selected") == 1, (
        "expected exactly one runway-card--selected modifier")
    # 21-05-PLAN.md Task 1 (D-06): theme_fieldset(), Calendar's own
    # compact chip grid, and the Flight-colours add form's compact chip
    # grid are all retired from this legacy SCOPE_ALL render — zero
    # .theme-chip--selected modifiers remain on this page at all (their
    # replacement, the Frame colours card, only ever renders on the
    # Display scope; its own selection state is covered by its own tests
    # elsewhere in this file).
    assert "theme-chip--selected" not in rendered, (
        "expected zero .theme-chip--selected modifiers on this legacy SCOPE_ALL render, got %d"
        % rendered.count("theme-chip--selected"))


def test_poll_trigger_enabled_at_zero_cooldown():
    """poll_trigger_section(0) renders an enabled button"""
    rendered = config_page.poll_trigger_section(0)
    # UXA-15 (06.6.2-02): scoped to the <button ...> tag itself, not a
    # bare substring search — the zero-cooldown branch's own submit-
    # affordance script now legitimately contains the word "disabled" as
    # a JS property name (`btn.disabled = true;`), which a whole-document
    # substring check would false-positive on.
    button_tag = re.search(r"<button\b[^>]*>", rendered)
    assert button_tag, "expected a <button> tag to extract"
    assert "disabled" not in button_tag.group(0), "expected no disabled attribute at zero cooldown"
    assert "Trigger poll now" in rendered, "expected the Trigger poll now button copy"


def test_poll_trigger_disabled_with_remaining_seconds():
    """poll_trigger_section(17) renders a disabled button and the remaining-seconds copy"""
    rendered = config_page.poll_trigger_section(17)
    assert "disabled" in rendered, "expected a disabled attribute at a non-zero cooldown"
    assert "17" in rendered, "expected the remaining-seconds figure (17) in the visible copy"


def test_poll_section_caption_renders_on_both_branches_under_the_heading():
    """poll_trigger_section() emits POLL_SECTION_CAPTION exactly once on both the enabled and
    disabled branches, before the poll-trigger form, and render() places it directly under the
    Poll <h2> heading (quick task 260901-s5o)"""
    # quick task 260901-s5o: the Poll section's own new caption check —
    # the group Task 1's non-goal explicitly excludes from
    # test_each_group_emits_exactly_one_caption_between_heading_and_control()
    # (Poll's heading lives in render(), not in poll_trigger_section(),
    # and its disabled branch legitimately emits a second <p>).
    poll_caption = escape_html(config_page.POLL_SECTION_CAPTION)
    for cooldown_remaining in (0, 17):
        rendered = config_page.poll_trigger_section(cooldown_remaining)
        assert rendered.count("section-caption") == 1, (
            "expected poll_trigger_section(%d) to emit exactly one "
            "section-caption occurrence, got %d"
            % (cooldown_remaining, rendered.count("section-caption")))
        assert rendered.count(poll_caption) == 1, (
            "expected poll_trigger_section(%d) to carry "
            "POLL_SECTION_CAPTION escaped-verbatim exactly once, got %d"
            % (cooldown_remaining, rendered.count(poll_caption)))
        caption_pos = rendered.index("section-caption")
        trigger_pos = rendered.index('<form method="post" action="/poll-now">')
        assert caption_pos < trigger_pos, (
            "expected poll_trigger_section(%d)'s caption to precede "
            "the poll-trigger form" % cooldown_remaining)

    # The render()-level position proof: the heading is emitted by
    # render(), the caption by poll_trigger_section() — two different
    # functions whose relative order nothing else guards.
    page = config_page.render({
        "device_config": {
            "theme": "sky", "tracked_runway": "3", "led_enabled": True},
        "poll_cooldown_remaining": 0,
    })
    assert page.count(poll_caption) == 1, (
        "expected render() to carry POLL_SECTION_CAPTION "
        "escaped-verbatim exactly once, got %d" % page.count(poll_caption))
    heading_pos = page.index('<h2 class="text-heading">%s</h2>' % config_page.POLL_SECTION_HEADING)
    page_caption_pos = page.index(poll_caption)
    poll_now_pos = page.index('action="/poll-now"')
    assert heading_pos < page_caption_pos < poll_now_pos, (
        "expected the Poll caption to fall between the Poll <h2> "
        "heading and the poll-trigger form's action attribute")


def test_poll_trigger_live_countdown_seeded_from_server_value():
    """poll_trigger_section() emits zero <script> elements and ships the D-01/UXA-15 data-*
    attribute contract companion/static/poll-cooldown.js reads instead, on both the
    disabled and zero-cooldown branches (D-18/A-35, 19-04-PLAN.md)

    D-18/A-35 (19-04-PLAN.md): the disabled branch no longer ships an
    inline <script> at all (that behaviour moved to
    companion/static/poll-cooldown.js, D-01/UXA-15 externalized). This
    check pins the data-* attribute contract the script reads instead:
    id="poll-trigger-btn"/id="poll-cooldown-text", the unchanged
    server-rendered no-JS copy, and every value the script needs exposed
    as an escape_html()-gated data attribute on the button — never a
    hardcoded quoted string, so this check stays correct if the id/token
    constants are ever changed deliberately.
    """
    d17 = config_page.poll_trigger_section(17)
    d5 = config_page.poll_trigger_section(5)
    z = config_page.poll_trigger_section(0)

    assert "<script" not in d17, (
        "expected zero <script occurrences at cooldown=17 (D-18: externalized to poll-cooldown.js)")
    assert "<script" not in z, (
        "expected zero <script occurrences at cooldown=0 (D-18: externalized to poll-cooldown.js)")
    assert ('id="%s"' % config_page.POLL_TRIGGER_BUTTON_ID) in d17, "expected the button's id attribute"
    assert ('id="%s"' % config_page.POLL_COOLDOWN_TEXT_ID) in d17, "expected the paragraph's id attribute"

    visible_copy = escape_html(
        config_page.POLL_COOLDOWN_HELPER_TEXT.format(n=17))
    assert visible_copy in d17, "expected the unchanged, server-rendered no-JS copy"

    template = escape_html(config_page.POLL_COOLDOWN_HELPER_TEXT.format(
        n=config_page.POLL_COOLDOWN_TEMPLATE_TOKEN))
    token = escape_html(config_page.POLL_COOLDOWN_TEMPLATE_TOKEN)
    expected_attrs = [
        'data-cooldown="17"',
        'data-cooldown-text-id="%s"' % escape_html(config_page.POLL_COOLDOWN_TEXT_ID),
        'data-cooldown-template="%s"' % template,
        'data-cooldown-token="%s"' % token,
    ]
    for attr in expected_attrs:
        assert attr in d17, "expected data attribute %r on the disabled branch" % (attr,)

    assert 'data-cooldown="5"' in d5, (
        "expected the seed to come from the argument (5), not a hardcoded value")


def test_poll_trigger_zero_cooldown_ships_submit_affordance_script():
    """poll_trigger_section(0) ships id="poll-trigger-btn" and a data-submit-pending
    attribute with zero <script> elements, while poll_trigger_section(30) carries the
    disabled-branch data-cooldown attribute instead (D-18/A-35, 19-04-PLAN.md)

    D-18/A-35 (19-04-PLAN.md): supersedes the pre-existing "ships its own
    inline <script>" assertion, no longer true by design now that the
    UXA-15 disable-on-submit affordance lives in
    companion/static/poll-cooldown.js. Pins the new contract instead:
    poll_trigger_section(0) carries id="poll-trigger-btn" and a
    data-submit-pending attribute, no <script> anywhere, while
    poll_trigger_section(30) carries the disabled-branch data-cooldown
    attribute set instead.
    """
    rendered = config_page.poll_trigger_section(0)
    assert "Trigger poll now" in rendered, "expected the Trigger poll now button copy"
    # Scoped to the <button ...> tag, not a bare substring search —
    # poll-cooldown.js's own body legitimately contains "disabled" as a
    # JS property name, though that no longer reaches this render()
    # output at all post-externalization.
    button_tag = re.search(r"<button\b[^>]*>", rendered)
    assert button_tag, "expected a <button> tag to extract"
    assert "disabled" not in button_tag.group(0), "expected no disabled attribute at zero cooldown"
    assert ('id="%s"' % config_page.POLL_TRIGGER_BUTTON_ID) in rendered, "expected the button's id attribute"
    assert "<script" not in rendered, (
        "expected zero <script occurrences at zero cooldown (D-18: externalized to poll-cooldown.js)")
    assert 'data-submit-pending="%s"' % escape_html(config_page.POLL_SUBMIT_PENDING_TEXT) in rendered, (
        "expected the data-submit-pending attribute carrying the pending label")

    nonzero = config_page.poll_trigger_section(30)
    assert 'data-cooldown="30"' in nonzero, (
        "expected poll_trigger_section(30) to carry the disabled-branch data-cooldown attribute")


# The whole forbidden-sink family in one place, so a future reader can
# see it at a glance (06.5-01-PLAN.md's own sink-safety gate for
# companion/static/battery-trend.js established this pattern first).
_FORBIDDEN_SCRIPT_SINKS = (
    "innerHTML", "outerHTML", "insertAdjacentHTML",
    "document.write", "eval(", "fetch(", "XMLHttpRequest",
)
_REQUIRED_SCRIPT_OPERATIONS = (
    "use strict", "textContent", "removeAttribute",
    "setInterval", "clearInterval",
)


def test_poll_cooldown_script_has_no_forbidden_sink(poll_cooldown_js):
    """poll_trigger_section(17) carries no <script substring and ships the countdown's
    required data attributes; companion/static/poll-cooldown.js's own source contains
    none of the forbidden HTML-writing/eval/network sinks and does contain strict mode
    plus the permitted DOM/timer operations (retargeted, D-18/A-35)"""
    rendered = config_page.poll_trigger_section(17)
    assert "<script" not in rendered, (
        "expected zero <script occurrences at cooldown=17 (D-18: externalized to poll-cooldown.js)")
    for attr in (
            'data-cooldown="17"',
            'data-cooldown-text-id="%s"' % escape_html(config_page.POLL_COOLDOWN_TEXT_ID)):
        assert attr in rendered, "expected data attribute %r on the disabled branch" % (attr,)
    src = poll_cooldown_js
    for forbidden in _FORBIDDEN_SCRIPT_SINKS:
        assert forbidden not in src, "forbidden sink found in poll-cooldown.js: %r" % (forbidden,)
    for required in _REQUIRED_SCRIPT_OPERATIONS:
        assert required in src, "expected required operation %r in poll-cooldown.js" % (required,)


def test_poll_submit_script_has_no_forbidden_sink(poll_cooldown_js):
    """poll_trigger_section(0) carries no <script substring and ships the data-submit-pending
    attribute; companion/static/poll-cooldown.js's own source contains none of the
    forbidden HTML-writing/eval/network sinks and attaches a submit listener (retargeted,
    D-18/A-35, UXA-15)"""
    rendered = config_page.poll_trigger_section(0)
    assert "<script" not in rendered, (
        "expected zero <script occurrences at cooldown=0 (D-18: externalized to poll-cooldown.js)")
    assert 'data-submit-pending="%s"' % escape_html(config_page.POLL_SUBMIT_PENDING_TEXT) in rendered, (
        "expected the data-submit-pending attribute carrying the pending label")
    src = poll_cooldown_js
    for forbidden in _FORBIDDEN_SCRIPT_SINKS:
        assert forbidden not in src, "forbidden sink found in poll-cooldown.js: %r" % (forbidden,)
    assert "use strict" in src, "expected strict mode"
    assert "addEventListener" in src, "expected a submit event listener"


# ======================================================================
# Section 3: handle_post()'s theme/runway validation, the LED merge, the
# quiet-hours save/reject paths, and wake_interval_s conversion/rejection.
# ======================================================================


def test_valid_save_writes_both_and_returns_saved_key(tmp_path):
    """a post with a valid theme and runway writes both and returns the saved flash key"""
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"theme": "black", "tracked_runway": "06-24"}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    # led_enabled is resolved by handle_post() itself, with checkbox-
    # absent-means-False semantics (never carried forward like theme/
    # runway) — this posted form omits led_enabled entirely, so the
    # persisted value is False, not DEFAULT_LED_ENABLED (True). The theme
    # value itself is "black", matching what the fixture above actually
    # posted. load_device_config() always returns theme_arriving too
    # (None here, since this post carries no arrivals override — None
    # means "same theme as departures", never DEFAULT_THEME_ID) and
    # calendar_theme_id too (None here, no calendar theme has been
    # chosen), and screen_id ("plane-frame", DEFAULT_SCREEN_ID, since
    # this post carries no screen_id field), and notifications too.
    # screens.GROUP_NOTIFICATIONS joins the legacy SCOPE_ALL tuple this
    # un-scoped post resolves to, so its two checkboxes resolve
    # absent-means-False like every other in-scope checkbox this handler
    # owns, rather than DEFAULT_NOTIFICATIONS's own True/True. The topic
    # URL still carries forward the (here, never-set) on-disk value, and
    # lang falls back to "en" (this test's ctx carries no "lang" key).
    # display_enabled is True here (not a hard-coded False) — this posted
    # form omits display_enabled entirely, and that field's absence now
    # means "leave unchanged" UNCONDITIONALLY, so on this fresh state
    # directory it falls through to DEFAULT_DISPLAY_ENABLED (True).
    # quiet_hours_enabled stays False here too, for the same "leave
    # unchanged" reason, and DEFAULT_QUIET_HOURS_ENABLED already IS
    # False. led_enabled is True here for exactly the same reason
    # display_enabled already was: this posted form omits it, and that
    # absence now means "leave unchanged" unconditionally, so on a fresh
    # state directory it falls through to DEFAULT_LED_ENABLED.
    assert on_disk == {
        "theme": "black", "theme_arriving": None, "calendar_theme_id": None,
        "tracked_runway": "06-24", "led_enabled": True, "quiet_hours_enabled": False,
        "quiet_hours_start": "23:00", "quiet_hours_end": "07:00", "display_enabled": True,
        "wake_interval_s": None, "screen_id": "plane-frame",
        "notifications": {"topic_url": None, "battery_low": False, "frame_silent": False, "lang": "en"},
    }, "on-disk config does not match the posted values: %r" % (on_disk,)


def test_nonmember_theme_writes_nothing(tmp_path):
    """a post with a non-member theme writes nothing and returns the save-failure flash key"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"theme": "not-a-real-theme", "tracked_runway": "06-24"}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    assert before == after, "expected device_config.json to be byte-identical, it changed"


def test_nonmember_runway_writes_nothing(tmp_path):
    """a post with a non-member runway writes nothing and returns the save-failure flash key"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"theme": "black", "tracked_runway": "not-a-real-runway"}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    assert before == after, "expected device_config.json to be byte-identical, it changed"


def test_theme_only_post_carries_runway_forward(tmp_path):
    """a post with a theme but no runway field carries the existing runway forward unchanged"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "06-24")
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"theme": "black"}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["tracked_runway"] == "06-24", (
        "expected the existing runway to be carried forward unchanged, got %r" % (on_disk,))


def test_path_traversal_theme_rejected(tmp_path):
    """a post with a directory-traversal-shaped theme value is rejected by the membership test"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"theme": "../../etc/passwd", "tracked_runway": "3"}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for a path-traversal-shaped theme, got %r" % (flash_key,))
    assert before == after, "expected device_config.json to be byte-identical, it changed"


def test_sql_fragment_theme_rejected(tmp_path):
    """a post with a SQL-fragment-shaped theme value is rejected by the membership test"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"theme": "sky'; DROP TABLE flights; --", "tracked_runway": "3"}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for a SQL-shaped theme, got %r" % (flash_key,))
    assert before == after, "expected device_config.json to be byte-identical, it changed"


def test_save_oserror_returns_failure_key_not_raise(tmp_path, monkeypatch):
    """a save that raises OSError returns the save-failure flash key rather than propagating"""
    def _raising_save(*args, **kwargs):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(device_config, "save_device_config", _raising_save)
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post({"theme": "black", "tracked_runway": "3"}, ctx)
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED when save_device_config() raises OSError, got %r" % (flash_key,))


# ------------------------------------------------------------------
# 06.6.4.1 Task 2 (D-05): handle_post() absorbs LED validation as one
# all-or-nothing submission — one check per <behavior> bullet.
# ------------------------------------------------------------------


@pytest.mark.parametrize("stored", [True, False], ids=["led-was-on", "led-was-off"])
def test_handle_post_empty_form_leaves_led_unchanged(tmp_path, stored):
    """handle_post({}, ctx) - the shape a browser sends when nothing is checked and nothing is
    selected - LEAVES the stored led_enabled unchanged in both directions and returns the
    saved flash key (retargeted in place from absent-means-False by 23-07-PLAN.md Task 2)

    Bullet 1: the shape a browser sends when nothing is checked and
    nothing is selected. Absence now means "leave unchanged", so the
    honest assertion is that BOTH a stored True and a stored False
    survive — asserting only the False direction would pass on a handler
    that hard-codes False, which is the very behaviour this change
    removes.
    """
    device_config.save_device_config(str(tmp_path), led_enabled=stored)
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post({}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(str(tmp_path))
    assert on_disk["led_enabled"] is stored, (
        "expected an empty body to LEAVE the stored led_enabled %r unchanged, got %r"
        % (stored, on_disk["led_enabled"]))


def test_handle_post_led_checkbox_value_persists_led_true(tmp_path):
    """handle_post({"led_enabled": LED_CHECKBOX_VALUE}, ctx) persists led_enabled True"""
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"led_enabled": config_page.LED_CHECKBOX_VALUE}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["led_enabled"] is True, "expected led_enabled True on disk, got %r" % (on_disk["led_enabled"],)


def test_handle_post_crafted_led_value_rejected_byte_identical(tmp_path):
    """handle_post({"led_enabled": "<crafted>"}, ctx) returns the save-failed flash key and
    leaves device_config.json byte-identical"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3", led_enabled=True)
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"led_enabled": "<crafted>"}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    assert before == after, "expected device_config.json to be byte-identical, it changed"


def test_handle_post_invalid_theme_rejects_led_half_too(tmp_path):
    """handle_post({"theme": "<not a registered theme>", "led_enabled": LED_CHECKBOX_VALUE}, ctx)
    returns save-failed and leaves the file byte-identical (an invalid theme rejects the LED
    half too)"""
    # Bullet 4: an invalid theme rejects the LED half too - proving the
    # merge stays all-or-nothing across all three fields.
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "sky", "3", led_enabled=False)
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"theme": "not-a-real-theme", "led_enabled": config_page.LED_CHECKBOX_VALUE},
        ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    assert before == after, "expected device_config.json to be byte-identical, it changed"


def test_handle_post_valid_runway_and_led_persist_together_one_call(tmp_path):
    """handle_post({"tracked_runway": <a real runway id>, "led_enabled": LED_CHECKBOX_VALUE}, ctx)
    persists both in one call and returns the saved flash key"""
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"tracked_runway": "06-24", "led_enabled": config_page.LED_CHECKBOX_VALUE},
        ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["tracked_runway"] == "06-24", (
        "expected tracked_runway 06-24 on disk, got %r" % (on_disk["tracked_runway"],))
    assert on_disk["led_enabled"] is True, "expected led_enabled True on disk, got %r" % (on_disk["led_enabled"],)


# ------------------------------------------------------------------
# 10-05-PLAN.md Task 3: handle_post()'s quiet-hours save/reject paths
# (D-03/D-04, 10-UI-SPEC.md's unchecked-checkbox-still-saves-times
# semantics — the resolution of 10-RESEARCH.md Assumption A1).
# ------------------------------------------------------------------


def test_handle_post_quiet_hours_checkbox_on_persists_all_three(tmp_path):
    """handle_post with quiet_hours_enabled=QUIET_HOURS_CHECKBOX_VALUE and both times persists
    all three quiet-hours fields and returns the saved flash key"""
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {
            "quiet_hours_enabled": config_page.QUIET_HOURS_CHECKBOX_VALUE,
            "quiet_hours_start": "22:30", "quiet_hours_end": "06:15",
        },
        ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["quiet_hours_enabled"] is True, (
        "expected quiet_hours_enabled True on disk, got %r" % (on_disk["quiet_hours_enabled"],))
    assert on_disk["quiet_hours_start"] == "22:30" and on_disk["quiet_hours_end"] == "06:15", (
        "expected the submitted times to persist, got %r/%r"
        % (on_disk["quiet_hours_start"], on_disk["quiet_hours_end"]))


def test_handle_post_quiet_hours_checkbox_absent_still_persists_times(tmp_path):
    """handle_post with quiet_hours_enabled absent but both times submitted persists
    quiet_hours_enabled False and the edited times (a user can pre-configure a window before
    enabling it)"""
    # The direct pin of 10-UI-SPEC.md's resolution of 10-RESEARCH.md
    # Assumption A1 / Open Question 2: a user can pre-configure a window
    # before ever turning it on. Must not be dropped or inverted.
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"quiet_hours_start": "22:30", "quiet_hours_end": "06:15"}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["quiet_hours_enabled"] is False, (
        "expected quiet_hours_enabled False on disk (checkbox absent), got %r"
        % (on_disk["quiet_hours_enabled"],))
    assert on_disk["quiet_hours_start"] == "22:30" and on_disk["quiet_hours_end"] == "06:15", (
        "expected the edited times to persist even though the checkbox was left unchecked, "
        "got %r/%r" % (on_disk["quiet_hours_start"], on_disk["quiet_hours_end"]))


def test_handle_post_malformed_quiet_hours_time_rejected_byte_identical(tmp_path):
    """handle_post({"quiet_hours_start": "24:00"}, ctx) against a legitimately-saved config
    returns the save-failed flash key and leaves device_config.json byte-identical"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"quiet_hours_start": "24:00"}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for a malformed HH:MM, got %r" % (flash_key,))
    assert before == after, "expected device_config.json to be byte-identical, it changed"


def test_handle_post_crafted_quiet_hours_checkbox_value_rejected(tmp_path):
    """handle_post({"quiet_hours_enabled": "yes"}, ctx) returns the save-failed flash key,
    matching the LED field's own third shape"""
    ctx = {"state_dir": str(tmp_path)}
    flash_key = config_page.handle_post({"quiet_hours_enabled": "yes"}, ctx)
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for a crafted quiet_hours_enabled value, got %r" % (flash_key,))


def test_handle_post_valid_theme_and_malformed_quiet_hours_end_all_or_nothing(tmp_path):
    """a post with a valid theme AND a malformed quiet_hours_end returns save-failed and
    persists neither — the theme on disk is unchanged (all-or-nothing across groups)"""
    tmpdir = str(tmp_path)
    cp.write_device_config(tmpdir, "black", "3")
    before = Path(device_config.device_config_path(tmpdir)).read_bytes()
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post(
        {"theme": "white", "quiet_hours_end": "24:00"}, ctx)
    after = Path(device_config.device_config_path(tmpdir)).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, "expected FLASH_SAVE_FAILED, got %r" % (flash_key,)
    assert before == after, (
        "expected device_config.json to be byte-identical (the theme must not persist either), "
        "it changed")
    on_disk = device_config.load_device_config(tmpdir)
    assert on_disk["theme"] == "black", (
        "expected the pre-existing theme to be unchanged, got %r" % (on_disk["theme"],))


# ------------------------------------------------------------------
# 11-03-PLAN.md Task 2: handle_post()'s wake_interval_s conversion,
# rejection, and leave-unchanged checks (D-05, 11-UI-SPEC.md).
# ------------------------------------------------------------------


def test_handle_post_wake_interval_string_converts_to_int_and_persists(tmp_path):
    """handle_post({"wake_interval_s": "120"}, ctx) explicitly string-to-int converts before
    persisting, stores the int (not a string) 120, and returns the saved flash key
    (11-RESEARCH.md Pitfall 1 regression guard)"""
    # The direct regression guard for 11-RESEARCH.md Pitfall 1: a stored
    # string would round-trip through load_device_config() as None
    # (normalise_wake_interval_s() rejects non-int values) and silently
    # look like "unset" instead of like a bug — asserting
    # isinstance(..., int) explicitly is what catches that.
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    flash_key = config_page.handle_post({"wake_interval_s": "120"}, ctx)
    assert flash_key == config_page.FLASH_SAVED, "expected FLASH_SAVED, got %r" % (flash_key,)
    on_disk = device_config.load_device_config(tmpdir)
    assert isinstance(on_disk["wake_interval_s"], int), (
        "expected the submitted string \"120\" to convert to an int, got %r"
        % (on_disk["wake_interval_s"],))
    assert on_disk["wake_interval_s"] == 120, (
        "expected wake_interval_s 120 on disk, got %r" % (on_disk["wake_interval_s"],))


@pytest.mark.parametrize("bad_value", ["abc", "1.5", "59", "3601", "-1"], ids=[
    "abc-not-an-int", "1-5-not-an-int", "59-below-floor", "3601-above-ceiling",
    "negative-1-below-zero",
])
def test_handle_post_wake_interval_rejection_paths_byte_identical(tmp_path, bad_value):
    """handle_post rejects "abc"/"1.5" (handler's int() gate) and "59"/"3601"/"-1"
    (save_device_config()'s bounded-range check), each returning the save-failed flash key
    and leaving a pre-existing device_config.json byte-identical"""
    # "abc"/"1.5" fail at this handler's own int() gate; "59"/"3601"/"-1"
    # are syntactically valid ints but fail inside save_device_config()'s
    # bounded-range check. Each bad value gets its own freshly-seeded
    # tmp_path here (rather than one shared seed reused across a
    # sequential loop, the legacy shape) — equivalent, since a rejection
    # is asserted to leave state untouched regardless of what else has or
    # has not been rejected before it.
    tmpdir = str(tmp_path)
    ctx = {"state_dir": tmpdir}
    seed_flash = config_page.handle_post({"wake_interval_s": "120"}, ctx)
    assert seed_flash == config_page.FLASH_SAVED, "expected the seeding save to succeed, got %r" % (seed_flash,)
    config_path = device_config.device_config_path(tmpdir)
    before = Path(config_path).read_bytes()
    flash_key = config_page.handle_post({"wake_interval_s": bad_value}, ctx)
    after = Path(config_path).read_bytes()
    assert flash_key == config_page.FLASH_SAVE_FAILED, (
        "expected FLASH_SAVE_FAILED for wake_interval_s=%r, got %r" % (bad_value, flash_key))
    assert before == after, (
        "expected device_config.json to stay byte-identical after rejecting "
        "wake_interval_s=%r" % (bad_value,))
