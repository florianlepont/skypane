"""companion/ui_time.py: timestamp parsing and the app's relative/absolute
time renderers — the "s/m/h/d" age-bucket ladder (`_age_bucket`) and its
three readings (age, future, duration), the `<time data-relative>` element
`relative_time_html()` builds for companion/static/relative-time.js's
client-side ticker, the absolute-plus-relative timestamp formats, and the
page-header freshness line. Depends only on companion.ui_base (escape_html,
icon_html, LOCAL_TZ, the month-abbreviation tables) plus companion.i18n/
companion.prefs; no import from ui_nav, ui_components, ui_shell or a page
module.
"""
from datetime import datetime
from zoneinfo import ZoneInfo

import companion.i18n as i18n
import companion.prefs as prefs
from companion.ui_base import LOCAL_TZ, _MONTH_ABBR, _MONTH_ABBR_FR, escape_html, icon_html

# Shared "absolute + relative" timestamp helpers, promoted from
# health_page.py's own private copies since one page module may not
# import another. Consumed by every page module that renders a stored
# instant.


def parse_iso(ts):
    """Parse `ts` as an ISO-8601 datetime, or return None.

    Never raises: a non-`str` input or a string `datetime.fromisoformat()`
    cannot parse both degrade to None rather than propagating a
    TypeError/ValueError into a page render.
    """
    if not isinstance(ts, str):
        return None
    try:
        return datetime.fromisoformat(ts)
    except ValueError:
        return None


def age_seconds(ts, now_ts):
    """The number of seconds between `ts` and `now_ts` (both parsed via
    parse_iso()), or None when either side fails to parse — including
    when one side is timezone-naive and the other timezone-aware, which
    parse_iso() alone cannot catch since each string parses fine on its
    own; only the subtraction raises.
    """
    parsed = parse_iso(ts)
    now_parsed = parse_iso(now_ts)
    if parsed is None or now_parsed is None:
        return None
    try:
        return (now_parsed - parsed).total_seconds()
    except TypeError:
        return None


# The French unit-suffix table relative_age_text()'s French branch
# consumes, in the same "fixed dict, membership lookup, documented
# fallback" shape _STATUS_DOT_CLASSES uses. Kept complete even though
# "s" is never reached (the seconds bucket short-circuits to
# "à l'instant" first).
_AGE_UNIT_SUFFIX_FR = {
    "s": "s",
    "m": "min",
    "h": "h",
    "d": "j",
}

# The four wordings relative_age_text()/relative_future_text() pass to
# i18n.t_lang() below, hoisted from inline literals to module-level
# Messages. Each id is owned by companion/i18n_fr/health.py's catalogue
# (untouched by this plan; migrated later), so the id-with-no-BY_ID-entry
# fallback keeps every one of these resolving until then.
_JUST_NOW_TEXT = i18n.msg("health.just_now", "just now")
_AGO_TEXT = i18n.msg("health.ago", "%s ago")
_IN_A_MOMENT_TEXT = i18n.msg("health.in_a_moment", "in a moment")
_IN_QUANTITY_TEXT = i18n.msg("health.in", "in %s")


def _age_bucket(age_seconds):
    """The s/m/h/d bucket a whole number of seconds falls in, as a `(value,
    unit_letter)` pair — the only place in this module the three
    threshold boundaries are written down.

    "3m ago" and "in 3m" are one ladder read in two directions: they
    must never disagree about where a bucket ends, so naming the
    boundaries once here makes that structural. The unit letters are
    the English suffixes themselves, so the English branch formats
    straight from this pair and the French branch maps them through
    _AGE_UNIT_SUFFIX_FR above.

    A negative input (clock skew, or an instant that has already
    elapsed) is clamped to 0 rather than read as a negative bucket —
    both directions inherit that clamp from here.
    """
    age_seconds = max(0, int(age_seconds))
    if age_seconds < 60:
        return age_seconds, "s"
    if age_seconds < 3600:
        return age_seconds // 60, "m"
    if age_seconds < 86400:
        return age_seconds // 3600, "h"
    return age_seconds // 86400, "d"


def relative_age_text(age_seconds, lang=None):
    """"Ns ago"/"Nm ago"/"Nh ago"/"Nd ago" using the s/m/h/d threshold ladder
    `_age_bucket()` defines, shared with relative_future_text() below. A
    negative age (clock skew) is clamped to 0 rather than read as "in the
    future".

    `lang` is a trailing keyword; `None` resolves to prefs.current_lang() and
    the English branch stays byte-for-byte unchanged for every pre-existing
    call site.

    French collapses the whole under-a-minute bucket into one "à l'instant"
    phrase regardless of the exact second count. The minute/hour/day buckets
    carry a real U+00A0 non-breaking space between the number and the unit;
    that copy lives in companion/i18n_fr/health.py, read through
    i18n.t_lang() rather than duplicated as a module literal.
    """
    age_seconds = max(0, int(age_seconds))
    if lang is None:
        lang = prefs.current_lang()
    value, unit = _age_bucket(age_seconds)
    if lang == "fr":
        if unit == "s":
            return i18n.t_lang(_JUST_NOW_TEXT, "fr")
        quantity = "%d %s" % (value, _AGE_UNIT_SUFFIX_FR[unit])
        return i18n.t_lang(_AGO_TEXT, "fr") % quantity
    return "%d%s ago" % (value, unit)


def relative_future_text(seconds_ahead, lang=None):
    """"in Ns"/"in Nm"/"in Nh"/"in Nd" — the forward reading of the same
    ladder relative_age_text() above reads backwards, over the same
    _age_bucket() boundaries.

    This function is formatting, never a verdict: it says how long
    remains until an instant somebody else computed, never
    "late"/"held"/"due" — those words are frame_state's. A `seconds_ahead`
    that has already elapsed resolves to the zero bucket, never a
    negative number or a past-tense string.

    `lang` is the same trailing keyword every sibling carries. French
    collapses the sub-minute bucket into "in a moment"; both strings live
    in companion/i18n_fr/health.py, read through i18n.t_lang().
    """
    value, unit = _age_bucket(seconds_ahead)
    if lang is None:
        lang = prefs.current_lang()
    if lang == "fr":
        if unit == "s":
            return i18n.t_lang(_IN_A_MOMENT_TEXT, "fr")
        quantity = "%d %s" % (value, _AGE_UNIT_SUFFIX_FR[unit])
        return i18n.t_lang(_IN_QUANTITY_TEXT, "fr") % quantity
    return "in %d%s" % (value, unit)


def duration_text(seconds, lang=None):
    """A bare LENGTH of time — "5m"/"5 min", "2h"/"2 h" — over the same
    _age_bucket() ladder the two relative forms above read in their two
    directions.

    The third reading of one ladder: it names a cadence or a measured gap
    with no connector and no tense, unlike its two siblings which state an
    instant relative to now. Only the real U+00A0 between the number and
    its unit is added; the ladder and the French unit suffixes are
    not restated.

    A negative or non-numeric input clamps to the zero bucket through
    _age_bucket(), exactly as both siblings do. Never raises.
    """
    value, unit = _age_bucket(seconds)
    if lang is None:
        lang = prefs.current_lang()
    if lang == "fr":
        return "%d %s" % (value, _AGE_UNIT_SUFFIX_FR[unit])
    return "%d%s" % (value, unit)


# companion/static/relative-time.js rewrites every <time data-relative>
# element once a second, so the four bucket wordings must exist
# client-side. Rendered onto <body> by page_shell() and read back with
# getAttribute(), since several of these elements sit inside
# freshness.js's swap targets.

# One complete wording per bucket per direction, so the script carries no
# language logic. "#" is the quantity's place, not "%s": these reach the
# browser as attribute values, and companion/test_i18n.py's Check 3 scans
# every French render for a stray "%s"/"%d"/"{}" — "#" is not one.

# Not a second ladder: the same ladder's own output with the number
# lifted out. test_companion_app.py asserts each wording, filled with the
# quantity _age_bucket() picks, equals relative_age_text()'s/
# relative_future_text()'s own return value, in both languages.
RELATIVE_QUANTITY_MARK = "#"
# Each of the eight bucket wordings below, plus RELATIVE_WAITING_TEXT,
# is a Message: relative_copy_attrs() passes every one to i18n.t_lang(),
# and every id is owned by companion/i18n_fr/health.py's catalogue
# (untouched by this plan; migrated later).
RELATIVE_PAST_SECONDS_TEXT = i18n.msg("health.s_ago", "#s ago")
RELATIVE_PAST_MINUTES_TEXT = i18n.msg("health.m_ago", "#m ago")
RELATIVE_PAST_HOURS_TEXT = i18n.msg("health.h_ago", "#h ago")
RELATIVE_PAST_DAYS_TEXT = i18n.msg("health.d_ago", "#d ago")
RELATIVE_FUTURE_SECONDS_TEXT = i18n.msg("health.in_s", "in #s")
RELATIVE_FUTURE_MINUTES_TEXT = i18n.msg("health.in_m", "in #m")
RELATIVE_FUTURE_HOURS_TEXT = i18n.msg("health.in_h", "in #h")
RELATIVE_FUTURE_DAYS_TEXT = i18n.msg("health.in_d", "in #d")

# What a countdown reads once its instant has passed. Never a warning
# word or colour — a thing which has not happened yet is not a fault;
# this is the app's neutral breathing treatment.
RELATIVE_WAITING_TEXT = i18n.msg("health.waiting", "waiting…")

# Must equal the attribute names companion/static/relative-time.js
# reads, in bucket order (s/m/h/d), matching _age_bucket()'s own unit
# letters. test_companion_app.py pins every one present in that file's
# source.
RELATIVE_PAST_ATTRS = (
    "data-relative-past-s",
    "data-relative-past-m",
    "data-relative-past-h",
    "data-relative-past-d",
)
RELATIVE_FUTURE_ATTRS = (
    "data-relative-future-s",
    "data-relative-future-m",
    "data-relative-future-h",
    "data-relative-future-d",
)
RELATIVE_WAITING_ATTR = "data-relative-waiting"

# The marker relative_time_html() puts on an element that is a
# COUNTDOWN rather than an age (see its `countdown` keyword). Also
# read by companion/static/relative-time.js.
RELATIVE_COUNTDOWN_ATTR = "data-relative-countdown"

# Ordered s/m/h/d, matching the attribute tuples above and
# _age_bucket()'s own unit letters.
_RELATIVE_PAST_TEXTS = (
    RELATIVE_PAST_SECONDS_TEXT, RELATIVE_PAST_MINUTES_TEXT,
    RELATIVE_PAST_HOURS_TEXT, RELATIVE_PAST_DAYS_TEXT,
)
_RELATIVE_FUTURE_TEXTS = (
    RELATIVE_FUTURE_SECONDS_TEXT, RELATIVE_FUTURE_MINUTES_TEXT,
    RELATIVE_FUTURE_HOURS_TEXT, RELATIVE_FUTURE_DAYS_TEXT,
)


def relative_copy_attrs(lang=None):
    """The ticker's own copy as `((attribute name, translated wording), ...)`,
    ready for page_shell() to render onto `<body>`.

    Nine pairs: four past wordings, four future wordings, and the waiting
    phrase an expired countdown reads. Every value goes through
    i18n.t_lang() here, server-side, so companion/static/relative-time.js
    carries no French at all.
    """
    if lang is None:
        lang = prefs.current_lang()
    pairs = []
    for attr, text in zip(RELATIVE_PAST_ATTRS, _RELATIVE_PAST_TEXTS):
        pairs.append((attr, i18n.t_lang(text, lang)))
    for attr, text in zip(RELATIVE_FUTURE_ATTRS, _RELATIVE_FUTURE_TEXTS):
        pairs.append((attr, i18n.t_lang(text, lang)))
    pairs.append(
        (RELATIVE_WAITING_ATTR, i18n.t_lang(RELATIVE_WAITING_TEXT, lang)))
    return tuple(pairs)


# duration_text() above is this app's one length-of-time ladder.
# companion/static/value-controls.js's quiet-hours readout needs a LIVE
# duration after a drag/keyboard step/edit, which never round-trips
# through the server: these wordings are duration_text()'s own output
# with the number lifted back out.

# One complete wording per bucket, reusing RELATIVE_QUANTITY_MARK ("#")
# for the same attribute-value scanning reason above. The French U+00A0
# between number and unit lives in the i18n_fr catalogue entry, not in
# this module.

# All four buckets ship even though a quiet window's arithmetic can
# never reach "d": "s" is reachable (a zero-length window is real), and
# a ladder with a hole in it is one somebody falls through later.
DURATION_SECONDS_TEXT = "#s"
DURATION_MINUTES_TEXT = "#m"
DURATION_HOURS_TEXT = "#h"
DURATION_DAYS_TEXT = "#d"

# Ordered s/m/h/d, matching _age_bucket()'s own unit letters. Read by
# config_page.py's quiet_dial_readout_html() and by
# companion/static/value-controls.js, which walks these four attributes
# in order to pick the bucket the live window falls in.
DURATION_ATTRS = (
    "data-duration-s",
    "data-duration-m",
    "data-duration-h",
    "data-duration-d",
)


def _machine_instant(parsed):
    """`parsed` as a machine-readable Europe/Paris ISO-8601 instant at
    seconds precision, or "" when it cannot be produced.

    The value `relative_time_html()` puts in a `datetime` attribute —
    never the raw stored string: it carries the same instant converted
    onto the one timezone this app speaks, offset included, so the
    script reading it is unambiguous.

    A naive datetime is taken as UTC, matching `local_clock_text()`'s own
    convention. Never raises: an unconvertible input returns "", and the
    caller renders plain text rather than an element with an empty
    attribute.
    """
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        return parsed.astimezone(LOCAL_TZ).isoformat(timespec="seconds")
    except (ValueError, OverflowError, AttributeError):
        return ""


def relative_time_html(ts, now_ts, fallback="no reading yet", lang=None,
                       countdown=False, static_text=None):
    """`<time datetime="<instant>" data-relative><relative age></time>` — the
    app's one relative-time element. Callers interpolate the return value
    verbatim, never re-escaping it (already escaped here); the no-JS
    rendering is the complete server text, no ticker needed. Returns the
    escaped `fallback` when `ts` is falsy, escaped `ts` on parse failure.

    `countdown` counts toward a future instant, reading
    RELATIVE_WAITING_TEXT once it passes rather than becoming an age.
    `static_text` renders fixed text instead of the ladder's output, for
    the one case where the server rendering must stay true with no
    ticker (e.g. an absolute clock rather than a duration).
    """
    if not ts:
        return escape_html(fallback)
    parsed = parse_iso(ts)
    age = age_seconds(ts, now_ts)
    if parsed is None or age is None:
        return escape_html(ts)
    instant = _machine_instant(parsed)
    if not instant:
        return escape_html(ts)
    if static_text is not None:
        text = static_text
    elif countdown and age >= 0:
        text = i18n.t_lang(
            RELATIVE_WAITING_TEXT,
            lang if lang is not None else prefs.current_lang())
    elif age < 0:
        text = relative_future_text(-age, lang=lang)
    else:
        text = relative_age_text(age, lang=lang)
    marker = " " + RELATIVE_COUNTDOWN_ATTR if countdown else ""
    return '<time datetime="%s" data-relative%s>%s</time>' % (
        escape_html(instant), marker, escape_html(text))


def absolute_and_relative(ts, now_ts, fallback="no reading yet", lang=None):
    """`"<ts> (<relative age> ago)"` — the house "absolute + relative"
    timestamp format, shared by every caller. Returns `fallback` when
    `ts` is falsy; returns `ts` unchanged (absolute only) when
    age_seconds() cannot parse either side — never raising.

    The return value is plain, unescaped text, the same contract
    status_dot()'s `label` carries: every caller must escape it directly
    or hand it to a builder that already escapes (e.g. data_table()).
    Absolute-first ordering (ISO string, then relative age in
    parentheses) is canonical and must not be reversed.

    `lang` defaults to `None`, resolved via relative_age_text()'s own
    default; an explicit `lang` threads through for a caller with no
    request context (e.g. a server-side notification body).
    """
    if not ts:
        return fallback
    age = age_seconds(ts, now_ts)
    if age is None:
        return ts
    return "%s (%s)" % (ts, relative_age_text(age, lang=lang))


# A `now_parsed` guaranteed to fall on a different calendar day than
# any real timestamp, forcing local_clock_text()'s cross-day "D Mon
# HH:MM" branch — how concise_timestamp_html()'s `title` below becomes a
# full local timestamp, reusing local_clock_text() rather than a second
# implementation.
_FULL_TIMESTAMP_SENTINEL_NOW = datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


def concise_timestamp_html(ts, now_ts, fallback="no reading yet", lang=None):
    """`<span class="mono" title="<D Mon HH:MM local>"><HH:MM local>
    (<relative>)</span>` — the concise-timestamp-by-default format,
    absolute-first per absolute_and_relative()'s ordering. `title` is
    always a full, day-qualified local timestamp, never the raw ISO
    string.

    Callers interpolate the return value verbatim, never re-escaping it.
    Returns the escaped `fallback` when `ts` is falsy; on a parse
    failure, returns a span with the raw value in both slots rather than
    raising. absolute_and_relative() remains the right choice for any
    plain-text-only call site. `lang` defaults to `None`, resolved via
    local_clock_text()'s/relative_age_text()'s own default.
    """
    if not ts:
        return escape_html(fallback)
    parsed = parse_iso(ts)
    age = age_seconds(ts, now_ts)
    if parsed is None or age is None:
        return '<span class="mono" title="%s">%s</span>' % (
            escape_html(ts), escape_html(ts))
    full_local = local_clock_text(parsed, _FULL_TIMESTAMP_SENTINEL_NOW, lang=lang)
    # The parenthesised relative half is relative_time_html()'s element,
    # not a bare escaped string, so every caller inherits the convention.
    # The parentheses stay OUTSIDE the element — punctuation, not part of
    # the age — so the ticker rewriting the element's text need not
    # reproduce them.
    return '<span class="mono" title="%s">%s (%s)</span>' % (
        escape_html(full_local),
        escape_html(local_clock_text(parsed, parse_iso(now_ts), lang=lang)),
        relative_time_html(ts, now_ts, lang=lang))


def month_abbr(month, lang=None):
    """The language-aware abbreviated month name, for callers that build
    their own "D Mon" labels (the Health battery chart's X axis) — the
    same tables local_clock_text() below selects between, exposed once
    instead of copied. `lang` defaults to the request's resolved
    language; `month` is 1..12.
    """
    if lang is None:
        lang = prefs.current_lang()
    table = _MONTH_ABBR_FR if lang == "fr" else _MONTH_ABBR
    return table[month - 1]


def local_clock_text(parsed, now_parsed=None, lang=None):
    """`parsed` (aware or naive) rendered on LOCAL_TZ: "HH:MM" when it falls
    on the same local day as `now_parsed` (or when no `now` is supplied),
    otherwise "D Mon HH:MM". A naive datetime is taken as UTC. Never
    raises.

    `lang` defaults to `None`, resolved to prefs.current_lang(): under a
    French request the month abbreviation comes from _MONTH_ABBR_FR
    instead; the clock itself stays 24-hour Europe/Paris in both
    languages.
    """
    try:
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=ZoneInfo("UTC"))
        local = parsed.astimezone(LOCAL_TZ)
        clock = local.strftime("%H:%M")
        if now_parsed is not None:
            if now_parsed.tzinfo is None:
                now_parsed = now_parsed.replace(tzinfo=ZoneInfo("UTC"))
            if now_parsed.astimezone(LOCAL_TZ).date() == local.date():
                return clock
            if lang is None:
                lang = prefs.current_lang()
            return "%d %s %s" % (local.day, month_abbr(local.month, lang), clock)
        return clock
    except (ValueError, OverflowError, AttributeError):
        return parsed.strftime("%H:%M") if hasattr(parsed, "strftime") else ""
# The freshness line: one definition site with three call sites, so markup
# read by two scripts and pinned by test harnesses cannot drift between
# copies. companion/pages/health_page.py imports these names from here rather
# than redefining them. Both Messages below are owned by health.py's
# catalogue (untouched by this plan; migrated later).
REFRESH_PILL_TEXT = i18n.msg("health.updating", "Updating…")

# The hook companion/static/freshness.js toggles its breathing class on.
# Duplicated rather than imported, since freshness.js is a static asset, not a
# Python module.
REFRESH_LIVE_DOT_ATTR = "data-refresh-live-dot"

FRESHNESS_PREFIX_TEXT = i18n.msg("health.updated", "Updated ")

# A `now_parsed` guaranteed to fall on a different Europe/Paris calendar day
# than any real device reading, forcing local_clock_text()'s cross-day
# "D Mon HH:MM" branch instead of duplicating that format elsewhere.
FULL_TIMESTAMP_SENTINEL_NOW = datetime(1970, 1, 1, tzinfo=ZoneInfo("UTC"))


def full_local_timestamp_text(ts):
    """`"D Mon HH:MM"` in Europe/Paris: the full local timestamp used for
    `title`/`aria-label`/`data-when` attributes on a stored instant.

    Falls back to the raw `ts` string, never raising, if it fails to parse.
    """
    parsed = parse_iso(ts)
    if parsed is None:
        return ts or ""
    return local_clock_text(parsed, now_parsed=FULL_TIMESTAMP_SENTINEL_NOW)


def freshness_line_html(now, lang=None):
    """The page-header freshness line: a neutral live dot, the "Updated " prefix,
    the clock and the hidden "Updating…" pill (carrying `data-loaded-at`),
    inside one block-level wrapper.

    Returns "" when `now` is falsy, so there is no honest instant to render;
    with no `data-loaded-at` marker, companion/static/freshness.js's loop never
    starts.

    Callers interpolate the return value verbatim (RAW markup); every piece is
    already escaped internally via escape_html().
    """
    if not now:
        return ""
    # escape_html() is required on `now`: i18n.t(REFRESH_PILL_TEXT) is not
    # pre-escaped.

    # No ARIA role on the pill: a live region announces on content
    # mutation, not visibility. Known gap: a reload while a screen
    # reader has focus resets its virtual cursor.
    pill_html = (
        '<span class="refresh-pill" data-refresh-pill data-loaded-at="%s" hidden>%s%s</span>'
        % (escape_html(now), icon_html("icon-refresh"), escape_html(i18n.t(REFRESH_PILL_TEXT))))
    # Server-rendered static and neutral; the breathing motion is a class
    # freshness.js adds/removes, so a scripts-blocked page shows a still
    # dot beside a static age. `.dot--off` carries no verdict colour —
    # a loop's live/paused state is not a device verdict.
    dot_html = (
        '<span class="dot dot--off" %s aria-hidden="true"></span>'
        % REFRESH_LIVE_DOT_ATTR)
    # The clock is local_clock_text() with `now_parsed` set to the same
    # instant, forcing its same-day "HH:MM" branch. `data-loaded-at` on
    # the pill carries the machine-readable instant freshness.js reads;
    # the `title` is tooltip only.

    # `.time-value`, not `.mono`: monospace is reserved for identifiers,
    # not a wall-clock time; `.time-value` keeps tabular numerals so the
    # digits hold their column as the clock ticks.
    _now_parsed = parse_iso(now)
    _clock_text = (
        local_clock_text(_now_parsed, now_parsed=_now_parsed)
        if _now_parsed is not None else now)
    clock_html = (
        '<span class="time-value" data-refresh-clock title="%s">%s</span>'
        % (escape_html(full_local_timestamp_text(now)),
           relative_time_html(now, now, static_text=_clock_text)))
    # One block-level wrapper for prefix+clock+pill: `.page-header` is a
    # block box, and a bare inline pill span would force an anonymous
    # block box, producing an extra gap.

    # This element is a REFRESH_SWAP_SELECTORS_BY_PAGE entry: freshness.js
    # replaces it wholesale, so a render-time value is honest only until
    # the next swap.
    freshness_html = (
        '<p class="page-header__freshness text-label">%s%s%s%s</p>'
        % (dot_html, escape_html(i18n.t(FRESHNESS_PREFIX_TEXT)),
           clock_html, pill_html))
    return freshness_html
