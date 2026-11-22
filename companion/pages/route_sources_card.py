"""The Health page's route directory cards.

Two cards in the platform group, after Identification: the status of each
route directory (VRS standing data, tried first, and adsbdb, the fallback)
and, per flight of the last days, which directory supplied the route that
was shown. Both read counters the poll cycle writes into history.db; nothing
here makes a network request, and a directory that was never asked reads as
"no request yet", never as a fault.

Every dynamic part is escaped; names are fixed catalogue text and numbers are
integers.
"""
from datetime import datetime, timedelta, timezone

from companion import health_rows, i18n
from companion.layout import escape_html
from companion.pages import health_page as hp
from server import history_db

STATUS_WINDOW_HOURS = 24
ANSWER_WINDOW_DAYS = 7

_DIRECTORIES_LABEL = i18n.msg("health.rd_directories", "Route directories")
_ANSWERED_BY = i18n.msg("health.rd_answered_by", "Answered by")

# The service names are the same in every language; only the VRS row carries
# a description.
_ADSBDB = "adsbdb"
_NAMES = {"vrs": i18n.msg("health.rd_vrs_name", "VRS standing data")}
_ANSWER_TOTALS = "VRS %d \u00b7 " + _ADSBDB + " %d"
_NO_SHARE = "\u2014"
_ROLES = {
    "vrs": i18n.msg("health.rd_vrs_role", "Tried first"),
    "adsbdb": i18n.msg("health.rd_adsbdb_role", "Used when the first has no route"),
}
_REACHABLE = i18n.msg("health.rd_reachable", "Reachable")
_NOT_REACHABLE = i18n.msg("health.rd_not_reachable", "Not reachable")
_NO_REQUEST = i18n.msg("health.rd_no_request", "No request yet")
_NO_REQUEST_NOTE = i18n.msg(
    "health.rd_no_request_note",
    "Shown after the first lookup that goes to this directory.")
_LAST_ANSWER = i18n.msg("health.rd_last_answer", "Last answer")
_LAST_24H = i18n.msg("health.rd_last_24h", "Last 24 hours")
_LOOKUPS = i18n.msg("health.rd_lookups", "Lookups %d")
_FOUND = i18n.msg("health.rd_found", "Found a route")
_FAILED = i18n.msg("health.rd_failed", "Failed")
_PERCENT = i18n.msg("health.rd_percent", "%d%%")
_NEVER = i18n.msg("health.rd_never", "never")
_WINDOW = i18n.msg("health.sys_window", "Last %d days: %d flights")
_WINDOW_ONE = i18n.msg("health.sys_window_one", "Last %d days: 1 flight")
_NO_ANSWERS = i18n.msg(
    "health.rd_no_answers", "No route from a directory in the last %d days")
_NO_ANSWERS_NOTE = i18n.msg(
    "health.rd_no_answers_note",
    "Shown once a flight gets its route from one of the directories.")


def read(conn, now_iso):
    """The data both cards show, read from `conn`: the per-directory counters
    of the last day and the flights each directory answered over the last
    days."""
    now = history_db.instant_or_none(now_iso) or datetime.now(timezone.utc)
    since_status = (now - timedelta(hours=STATUS_WINDOW_HOURS)).isoformat(timespec="seconds")
    since_answers = (now - timedelta(days=ANSWER_WINDOW_DAYS)).isoformat(timespec="seconds")
    return {
        "stats": history_db.route_directory_stats(conn, since_status),
        "answers": history_db.route_directory_counts(conn, since_answers),
    }


def _share(part, whole):
    if not whole:
        return _NO_SHARE
    return i18n.t(_PERCENT) % round(part * 100 / whole)


def _directory_row(directory, stats, now):
    """One directory: its name, whether it is reachable, its role and, once it
    has been asked, the last answer and the shares of the last day."""
    name = i18n.t(_NAMES[directory]) if directory in _NAMES else _ADSBDB
    role = health_rows.note_html(i18n.t(_ROLES[directory]))
    row_id = "route-directory-" + directory
    if stats["reachable"] is None:
        return health_rows.row_html(
            row_id, "off", name, i18n.t(_NO_REQUEST), "",
            role + health_rows.note_html(i18n.t(_NO_REQUEST_NOTE)))
    reachable = stats["reachable"]
    lookups = stats["lookups"]
    facts = health_rows.facts_html([
        hp._fact(_LAST_ANSWER, hp._age_html(stats["last_answer_ts"], now, _NEVER)),
        hp._fact(_LAST_24H, escape_html(i18n.t(_LOOKUPS) % lookups)),
        hp._fact(_FOUND, escape_html(_share(stats["found"], lookups))),
        hp._fact(_FAILED, escape_html(_share(stats["failed"], lookups)))])
    return health_rows.row_html(
        row_id, "ok" if reachable else "warn", name,
        i18n.t(_REACHABLE if reachable else _NOT_REACHABLE), "", role + facts)


def _bar_html(vrs, adsbdb):
    """The share bar: one segment per directory, sized by its flight count."""
    label = _ANSWER_TOTALS % (vrs, adsbdb)
    return (
        '<div class="route-bar" role="img" aria-label="%s">'
        '<span class="route-bar__seg route-bar__seg--first" style="--seg: %d"></span>'
        '<span class="route-bar__seg" style="--seg: %d"></span></div>'
    ) % (escape_html(label), vrs, adsbdb)


def _answers_row(answers):
    name = i18n.t(_ANSWERED_BY)
    vrs, adsbdb = answers["vrs"], answers["adsbdb"]
    total = vrs + adsbdb
    if total == 0:
        return health_rows.row_html(
            "route-answers", "off", name, i18n.t(_NO_ANSWERS) % ANSWER_WINDOW_DAYS, "",
            health_rows.note_html(i18n.t(_NO_ANSWERS_NOTE)))
    window = (
        i18n.t(_WINDOW_ONE) % ANSWER_WINDOW_DAYS if total == 1
        else i18n.t(_WINDOW) % (ANSWER_WINDOW_DAYS, total))
    return health_rows.row_html(
        "route-answers", "off", name, _ANSWER_TOTALS % (vrs, adsbdb), "",
        health_rows.note_html(window) + _bar_html(vrs, adsbdb))


def topics(data, now):
    """`(key, label message, row html)` for the two cards. `data` is `read()`'s
    result, `hp._DB_UNAVAILABLE` when the read failed, or None when there is
    nothing to read (no topics)."""
    if data is None:
        return ()
    if data is hp._DB_UNAVAILABLE:
        return (
            ("route-directories", _DIRECTORIES_LABEL,
             hp._unavailable_row("route-directories", i18n.t(_DIRECTORIES_LABEL))),
            ("route-answers", _ANSWERED_BY, hp._unavailable_row("route-answers", i18n.t(_ANSWERED_BY))))
    directories = "".join(
        _directory_row(directory, data["stats"][directory], now)
        for directory in history_db.ROUTE_DIRECTORIES)
    return (
        ("route-directories", _DIRECTORIES_LABEL, directories),
        ("route-answers", _ANSWERED_BY, _answers_row(data["answers"])))
