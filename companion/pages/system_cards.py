# SPDX-License-Identifier: AGPL-3.0-only
"""The System page's detail cards and warnings banner.

One card per topic (flight data, data sources, identification, the route
directories, off-box backup), built from the same snapshot the tiles read.
A card is a header row (state icon, small label, bold verdict, a short value
at the right), a hairline, then label/value rows, outcome rows or a table.

Every dynamic part is escaped; the `*_html` arguments are the caller's own
already-safe markup.
"""
from companion import health_rows, i18n, layout, ui_components
from companion.layout import escape_html
from companion.pages import health_page as hp

_LAST_DETECTION = i18n.msg("health.sys_last_detection", "Last detection")
_IDENTIFIED = i18n.msg("health.sys_identified", "%s %% of flights identified")
_IDENTIFIED_SHORT = i18n.msg("health.sys_identified_short", "%s %% identified")
_WINDOW = i18n.msg("health.sys_window", "Last %d days: %d flights")
_WINDOW_ONE = i18n.msg("health.sys_window_one", "Last %d days: 1 flight")

# One short sentence per identification source, in the order the table shows.
_SHORT_SOURCES = (
    ("fresh_hit", i18n.msg("health.sys_src_fresh", "Route found just now")),
    ("cache_hit", i18n.msg("health.sys_src_cached", "Route reused from an earlier lookup")),
    ("airline_only", i18n.msg("health.sys_src_airline", "Only the airline is known")),
    ("manual", i18n.msg("health.sys_src_manual", "Named by the owner")),
    ("miss", i18n.msg("health.sys_src_miss", "Nothing found")),
)
_SHORT_OTHER = i18n.msg("health.sys_src_other", "Other cases")

SYSTEM_CARD_CLASS = "sys-card"


def _card(key, state, icon_id, label, verdict, sub_html="", value_html="", body_html=""):
    state = health_rows.resolved_state(state)
    word = escape_html(i18n.t(health_rows.STATE_WORDS[state]))
    head = (
        '<div class="sys-card__head">'
        '<span class="sys-card__icon">%s<span class="visually-hidden">%s</span></span>'
        '<span class="sys-card__who"><span class="sys-card__label">%s</span>'
        '<b class="sys-card__verdict">%s</b>%s</span>%s</div>'
    ) % (layout.icon_html(icon_id, 20), word, escape_html(label), escape_html(verdict),
         sub_html, value_html)
    return '<div class="%s" data-state="%s" id="system-card-%s">%s%s</div>' % (
        SYSTEM_CARD_CLASS, state, key, head, body_html)


def _value(text):
    return '<span class="sys-card__value">%s</span>' % escape_html(text)


def _facts(pairs):
    items = "".join(
        "<div><dt>%s</dt><dd>%s</dd></div>" % (escape_html(i18n.t(label)), value_html)
        for label, value_html in pairs)
    return '<dl class="sys-card__facts">%s</dl>' % items if items else ""


def _note(text):
    return '<p class="sys-card__note">%s</p>' % escape_html(text)


def _unavailable(key, icon_id, label):
    return _card(key, "off", icon_id, label, i18n.t(hp._ROW_UNAVAILABLE_TEXT))


def flight_data(state, now):
    label = i18n.t(hp.ROW_FLIGHT_DATA_NAME)
    inputs = state["inputs"]
    if inputs["pipeline_ts"] is hp._DB_UNAVAILABLE:
        return _unavailable("flight-data", "icon-server", label)
    pipeline_ts = inputs["pipeline_ts"]
    last_detection = hp._available(inputs["last_detection"])
    pipeline_state = state["pipeline_state"]
    if hp._pipeline_never_ran(pipeline_ts, last_detection):
        body = _note(i18n.t(hp.PIPELINE_NEVER_RAN_DETAIL_TEXT))
    else:
        body = _facts([
            (hp._LAST_RUN_TEXT, hp._age_html(pipeline_ts, now)),
            (_LAST_DETECTION, hp._age_html(last_detection, now))])
    return _card(
        "flight-data", pipeline_state, "icon-server", label,
        i18n.t(hp.PIPELINE_STATE_TEXT.get(pipeline_state, hp.PIPELINE_STATE_TEXT["warn"])),
        body_html=body)


def _outcomes(counts):
    statuses = hp.corroboration_status(counts)
    items = []
    for key, label, _state, note in hp._CORROBORATION_ROWS:
        items.append(
            '<li><p class="sys-card__outcome">%s<span class="sys-card__count">%d</span></p>'
            '<p class="sys-card__sentence">%s</p></li>' % (
                layout.status_dot(statuses[key], i18n.t(label)),
                counts.get(key, 0) or 0, escape_html(i18n.t(note))))
    return '<ul class="sys-card__outcomes">%s</ul>' % "".join(items)


def sources(state):
    label = i18n.t(hp.ROW_SOURCES_NAME)
    counts = state["inputs"]["corroboration_counts"]
    if counts is hp._DB_UNAVAILABLE:
        return _unavailable("sources", "icon-radio", label)
    counts = counts or {}
    if not any(counts.values()):
        return _card(
            "sources", "off", "icon-radio", label,
            i18n.t(hp._NOTHING_TO_COMPARE_YET_TEXT),
            body_html=_note(i18n.t(hp._APPEARS_ONCE_RECORDED_TEXT)))
    verdict_state = "warn" if state["disagreement_warn"] else "ok"
    return _card(
        "sources", verdict_state, "icon-radio", label,
        i18n.t(hp.CORROBORATION_STATE_TEXT[verdict_state]),
        value_html=_value(hp._disagreements_text(counts.get("False", 0) or 0)),
        body_html=_outcomes(counts))


def _source_table(stats):
    """The by-source rows as flat bordered rows: Source, Count, short description."""
    shorts = {key: text for key, text in _SHORT_SOURCES}
    known = [key for key, _label, _gloss in hp._SOURCE_ROWS]
    by_key = {key: (row[0], row[2]) for key, row in zip(known, stats["rows"])}
    ordered = [(by_key[key][0], by_key[key][1], i18n.t(shorts[key]))
               for key, _text in _SHORT_SOURCES if key in by_key]
    if len(stats["rows"]) > len(known):
        other = stats["rows"][len(known)]
        ordered.append((other[0], other[2], i18n.t(_SHORT_OTHER)))
    head = "".join(
        "<th>%s</th>" % escape_html(i18n.t(text)) for text in (
            hp.health_sections_module._STATS_HEADERS[0],
            hp.health_sections_module._STATS_HEADERS[2],
            hp.health_sections_module._STATS_HEADERS[1]))
    rows = "".join(
        '<tr><td>%s</td><td class="sys-card__num">%s</td><td>%s</td></tr>' % (
            escape_html(name), escape_html(count), escape_html(desc))
        for name, count, desc in ordered)
    return ('<table class="sys-card__table"><thead><tr>%s</tr></thead>'
            '<tbody>%s</tbody></table>' % (head, rows))


def identification(stats, unresolved_count):
    label = i18n.t(hp.STATS_SECTION_HEADING)
    if stats is hp._DB_UNAVAILABLE:
        return _unavailable("identification", "icon-nav-airlines", label)
    to_resolve = (
        ui_components.pill_html(i18n.t(hp._TO_RESOLVE_TEMPLATE) % unresolved_count)
        if unresolved_count
        else _value(i18n.t(hp._NOTHING_TO_RESOLVE_TEXT)))
    if stats["total"] == 0:
        return _card(
            "identification", "off", "icon-nav-airlines", label,
            i18n.t(hp._NO_STATS_HEADING) % hp.RESOLUTION_WINDOW_DAYS,
            value_html=to_resolve, body_html=_note(i18n.t(hp._NO_STATS_BODY)))
    shown = hp._percent_text(
        min(stats["resolved_pct"], 99.9) if unresolved_count else stats["resolved_pct"])
    window = (_WINDOW_ONE if stats["total"] == 1 else _WINDOW)
    window_text = (
        i18n.t(window) % hp.RESOLUTION_WINDOW_DAYS if stats["total"] == 1
        else i18n.t(window) % (hp.RESOLUTION_WINDOW_DAYS, stats["total"]))
    return _card(
        "identification", "off", "icon-nav-airlines", label,
        i18n.t(_IDENTIFIED) % shown,
        sub_html='<span class="sys-card__sub">%s</span>' % escape_html(window_text),
        value_html=to_resolve, body_html=_source_table(stats))


def backup(offbox, now):
    """The off-box backup card, or "" when no marker is configured."""
    if offbox is None:
        return ""
    backup_state = offbox["state"]
    body = _facts([(hp._LAST_OFFBOX_BACKUP_TEXT, hp._age_html(offbox["snapshot_ts"], now))])
    anomaly = hp._offbox_anomaly_text(offbox)
    if anomaly:
        body += _note(anomaly)
    return _card(
        "backup", backup_state, "icon-cloud-upload", i18n.t(hp._OFFBOX_BACKUP_TEXT),
        i18n.t(hp.BACKUP_STATE_TEXT.get(backup_state, hp.BACKUP_STATE_TEXT["warn"])),
        body_html=body)


def topics(state, stats, registry_rows, now, route_topics=()):
    """(key, section label, card html) per topic; a topic with no card (no
    backup marker) is left out. `route_topics` are the route directory topics
    (already in this shape, label translated), placed after identification."""
    cards = (
        ("flight-data", hp.ROW_FLIGHT_DATA_NAME, flight_data(state, now)),
        ("sources", hp.ROW_SOURCES_NAME, sources(state)),
        ("identification", hp.STATS_SECTION_HEADING,
         identification(stats, len(registry_rows))))
    backup_card = ("backup", hp._OFFBOX_BACKUP_TEXT, backup(state.get("offbox"), now))
    translated = [(key, i18n.t(label), html) for key, label, html in cards if html]
    return (
        translated + list(route_topics)
        + [(key, i18n.t(label), html) for key, label, html in (backup_card,) if html])


def banner(severity, anomalies):
    """The warnings banner: a bordered card with the count, one outlined pill
    per failing category and the sentence pointing at the cards below."""
    noun = i18n.t(hp._SEVERITY_BANNER_NOUNS.get(severity, hp._SEVERITY_BANNER_ISSUE_TEXT))
    count = len(anomalies)
    title = hp._label_colon("%d %s%s" % (count, noun, "" if count == 1 else "s"))
    pills = "".join(
        '<span class="sys-banner__pill">%s</span>' % escape_html(text)
        for text in hp._anomaly_category_labels(anomalies))
    return (
        '<div class="sys-banner %s" data-severity="%s" role="%s">'
        '<b class="sys-banner__title">%s</b><span class="sys-banner__pills">%s</span>'
        '<span class="sys-banner__tail">%s</span></div>' % (
            hp.HEALTH_ANOMALY_CLASS, "error" if severity == "error" else "warn",
            "alert" if severity == "error" else "status",
            escape_html(title), pills, escape_html(i18n.t(hp.ANOMALY_BANNER_TEXT))))
