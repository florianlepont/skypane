"""The flash-message vocabulary and its text/role resolution, moved out
of `companion/app.py`: the FLASH_KEY_* aliases (each defined exactly
once in `companion/pages/config_page.py`, `companion/pages/airlines_page.py`
or `companion/pages/update_page.py`, re-exported here under its
historical name so every existing call site —
and every test assertion against the literal query-string value — stays
unchanged), the FLASH_MESSAGES/FLASH_TONES/FLASH_ROLES tables built
from them, resolve_flash_text(), and flash_toast_html(), which turns a
resolved flash into its toast (tone, role, glyph, optional action and
the no-script dismiss link). poll_cooldown_remaining() lives here too: it is
resolve_flash_text()'s own FLASH_KEY_POLL_COOLDOWN branch's only
in-module caller; `companion/app.py` rebinds it under its historical
name for its other two call sites (the poll-trigger route and the
lazy page-context loader).

Never imports `companion.app` (that would be a cycle — app.py imports
this module).
"""
import time
from urllib.parse import parse_qsl, urlencode, urlsplit

from companion import frame_state, i18n, layout, routes, wake
from companion.pages import airlines_page, config_page, update_page
from server import history_db
from server.plane import calendar_rules, colour_rules

# A double-click guard on POST /poll-now, not an abuse rate-limit.
POLL_COOLDOWN_S = 45

# The flash-key string literals below are defined exactly once, in
# companion/pages/config_page.py or companion/pages/airlines_page.py —
# imported here under their historical FLASH_KEY_* names so every
# existing call site (and its test assertions against the literal
# query-string values) stays unchanged.
FLASH_KEY_SAVED = config_page.FLASH_SAVED
FLASH_KEY_SAVE_FAILED = config_page.FLASH_SAVE_FAILED
FLASH_KEY_POLL_TRIGGERED = config_page.FLASH_POLL_TRIGGERED
FLASH_KEY_POLL_COOLDOWN = config_page.FLASH_POLL_COOLDOWN
FLASH_KEY_POLL_FAILED = config_page.FLASH_POLL_FAILED
FLASH_KEY_POLL_ALREADY_RUNNING = config_page.FLASH_POLL_ALREADY_RUNNING
FLASH_KEY_ILLUSTRATION_REPLACED = airlines_page.FLASH_ILLUSTRATION_REPLACED
FLASH_KEY_ILLUSTRATION_REJECTED = airlines_page.FLASH_ILLUSTRATION_REJECTED
FLASH_KEY_ILLUSTRATION_REPLACE_FAILED = airlines_page.FLASH_ILLUSTRATION_REPLACE_FAILED
FLASH_KEY_MANUAL_RESOLVED = airlines_page.FLASH_MANUAL_RESOLVED
FLASH_KEY_MANUAL_NAME_EMPTY = airlines_page.FLASH_MANUAL_NAME_EMPTY
FLASH_KEY_MANUAL_NAME_TOO_LONG = airlines_page.FLASH_MANUAL_NAME_TOO_LONG
FLASH_KEY_MANUAL_NAME_RESERVED = airlines_page.FLASH_MANUAL_NAME_RESERVED
FLASH_KEY_MANUAL_PREFIX_STALE = airlines_page.FLASH_MANUAL_PREFIX_STALE
FLASH_KEY_MANUAL_REGISTRY_FULL = airlines_page.FLASH_MANUAL_REGISTRY_FULL
FLASH_KEY_MANUAL_SAVE_FAILED = airlines_page.FLASH_MANUAL_SAVE_FAILED
FLASH_KEY_MANUAL_DELETE_FAILED = airlines_page.FLASH_MANUAL_DELETE_FAILED
# Distinguishes a name the operator genuinely typed but that
# add_entry() can't use, from a genuinely empty field.
FLASH_KEY_MANUAL_NAME_UNUSABLE = airlines_page.FLASH_MANUAL_NAME_UNUSABLE
FLASH_KEY_RULE_ADDED = config_page.FLASH_RULE_ADDED
FLASH_KEY_RULE_REPLACED = config_page.FLASH_RULE_REPLACED
FLASH_KEY_RULE_KEY_INVALID = config_page.FLASH_RULE_KEY_INVALID
FLASH_KEY_RULE_REGISTRY_FULL = config_page.FLASH_RULE_REGISTRY_FULL
FLASH_KEY_RULE_SAVE_FAILED = config_page.FLASH_RULE_SAVE_FAILED
FLASH_KEY_RULE_DELETED = config_page.FLASH_RULE_DELETED
FLASH_KEY_RULE_DELETE_FAILED = config_page.FLASH_RULE_DELETE_FAILED
FLASH_KEY_CALENDAR_CONNECTED = config_page.FLASH_CALENDAR_CONNECTED
FLASH_KEY_CALENDAR_SYNC_FAILED = config_page.FLASH_CALENDAR_SYNC_FAILED
FLASH_KEY_CALENDAR_DISCONNECTED = config_page.FLASH_CALENDAR_DISCONNECTED
FLASH_KEY_CALENDAR_SYNC_DEFERRED = config_page.FLASH_CALENDAR_SYNC_DEFERRED
FLASH_KEY_CALENDAR_CONNECT_OK = config_page.FLASH_CALENDAR_CONNECT_OK
FLASH_KEY_CALENDAR_CONNECT_INVALID = config_page.FLASH_CALENDAR_CONNECT_INVALID
FLASH_KEY_UPDATE_SCHEDULE_FAILED = update_page.FLASH_UPDATE_SCHEDULE_FAILED
FLASH_KEY_UPDATE_CANCEL_FAILED = update_page.FLASH_UPDATE_CANCEL_FAILED
FLASH_KEY_UPDATE_BUSY = update_page.FLASH_UPDATE_BUSY

# A fixed key -> copy dictionary — the flash mechanism only ever renders
# one of these, never a value taken verbatim from the query string.
# FLASH_KEY_POLL_COOLDOWN's "{n}" is filled in with a server-computed
# remaining-seconds figure, never anything client-supplied.
FLASH_KEY_DISPLAY_ON = "display_on"
FLASH_KEY_DISPLAY_OFF = "display_off"
FLASH_KEY_QUIET_ON = "quiet_on"
FLASH_KEY_QUIET_OFF = "quiet_off"
FLASH_KEY_QUICK_FAILED = "quick_failed"
# The LED switch's own two outcomes, worded like the Quiet-hours pair
# rather than the Screen pair — the LED, like quiet hours, takes effect
# on the frame's next wake rather than within about five minutes.
FLASH_KEY_LED_ON = "led_on"
FLASH_KEY_LED_OFF = "led_off"

# Every value below is a Message. Its id is owned by companion/i18n_fr/
# common.py, except the poll-cooldown copy (owned by
# companion/i18n_fr/display.py) and the three firmware-update outcomes
# at the end (owned by companion/i18n_fr/update.py).
FLASH_MESSAGES = {
    FLASH_KEY_DISPLAY_ON: i18n.msg(
        "common.screen_switched_on_the_frame_will_wake_up_and",
        "Screen switched on — the frame will wake up and show a picture "
        "within about five minutes."),
    FLASH_KEY_DISPLAY_OFF: i18n.msg(
        "common.screen_switched_off_the_frame_will_blank_itself",
        "Screen switched off — the frame will blank itself within about "
        "five minutes."),
    FLASH_KEY_QUIET_ON: i18n.msg(
        "common.quiet_hours_turned_on_applies_the_next_time_the",
        "Quiet hours turned on — applies the next time the frame wakes up."),
    FLASH_KEY_QUIET_OFF: i18n.msg(
        "common.quiet_hours_turned_off_applies_the_next_time",
        "Quiet hours turned off — applies the next time the frame wakes up."),
    FLASH_KEY_QUICK_FAILED: i18n.msg(
        "common.couldn_t_change_that_please_try_again",
        "Couldn't change that — please try again."),
    FLASH_KEY_LED_ON: i18n.msg(
        "common.diagnostic_led_turned_on_applies_the_next_time",
        "Diagnostic LED turned on — applies the next time the frame wakes up."),
    FLASH_KEY_LED_OFF: i18n.msg(
        "common.diagnostic_led_turned_off_applies_the_next_time",
        "Diagnostic LED turned off — applies the next time the frame wakes up."),
    # "%s" is filled by resolve_flash_text()'s own frame-state special
    # case below with one computed delay sentence (companion/frame_state.py,
    # via the same wake.next_wake_status() triple the Frame strip and the
    # Quiet hours caption both read).
    FLASH_KEY_SAVED: i18n.msg("common.saved", "Saved — %s"),
    FLASH_KEY_SAVE_FAILED: i18n.msg(
        "common.couldn_t_save_settings_please_try_again_if_this",
        "Couldn't save settings — please try again. If this keeps "
        "happening, check the companion service logs."),
    FLASH_KEY_POLL_TRIGGERED: i18n.msg(
        "common.refresh_requested_server_check_completed",
        "Refresh requested — the server finished checking for new flight data. "
        "The frame may update on a later wake."),
    # Owned by display.py's catalogue (untouched by this plan), not
    # common.py's — the Frame strip's own poll-cooldown copy.
    FLASH_KEY_POLL_COOLDOWN: i18n.msg(
        "display.poll_triggered_recently_try_again_in_n_s",
        "Poll triggered recently — try again in {n}s."),
    FLASH_KEY_POLL_FAILED: i18n.msg(
        "common.poll_trigger_failed_please_try_again_if_this",
        "Poll trigger failed — please try again. If this keeps happening, "
        "check the companion service logs."),
    FLASH_KEY_POLL_ALREADY_RUNNING: i18n.msg(
        "common.a_poll_is_already_in_progress_try_again_in_a",
        "A poll is already in progress — try again in a moment."),
    FLASH_KEY_ILLUSTRATION_REPLACED: i18n.msg(
        "common.illustration_replaced_the_frame_will_use_it",
        "Illustration replaced — the frame will use it next time it wakes and polls."),
    # Actionable, states the real requirements in user terms, and never
    # echoes a server path or any part of the uploaded file back to the
    # client — validate_illustration_file()'s own problem strings go to
    # the service log only, never into this copy.
    FLASH_KEY_ILLUSTRATION_REJECTED: i18n.msg(
        "common.couldn_t_use_that_image_upload_a_transparent",
        "Couldn't use that image — upload a transparent PNG that's at "
        "least 1200 pixels wide and landscape (wider than tall)."),
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED: i18n.msg(
        "common.couldn_t_replace_the_illustration_please_try",
        "Couldn't replace the illustration — please try again. If this "
        "keeps happening, check the companion service logs."),
    # Must not imply the frame changes instantly: the frame only ever
    # picks up a manual resolution on its next wake/poll, bounded by
    # `wake_interval_s` (device_config.py) — never sooner, whatever the
    # copy might otherwise suggest.
    FLASH_KEY_MANUAL_RESOLVED: i18n.msg(
        "common.airline_name_saved_the_frame_will_pick_it_up",
        "Airline name saved — the frame will pick it up next time it "
        "wakes and polls."),
    FLASH_KEY_MANUAL_NAME_EMPTY: i18n.msg(
        "common.enter_an_airline_name_before_saving",
        "Enter an airline name before saving."),
    FLASH_KEY_MANUAL_NAME_TOO_LONG: i18n.msg(
        "common.that_name_s_too_long_airline_names_top_out_at",
        "That name's too long — airline names top out at 100 characters."),
    FLASH_KEY_MANUAL_NAME_RESERVED: i18n.msg(
        "common.that_name_is_reserved_for_the_frame_s_own",
        "That name is reserved for the frame's own fallback artwork — "
        "try the airline's real name instead."),
    FLASH_KEY_MANUAL_PREFIX_STALE: i18n.msg(
        "common.that_coverage_gap_isn_t_there_anymore_check",
        "That coverage gap isn't there anymore — check Health for "
        "current gaps."),
    FLASH_KEY_MANUAL_REGISTRY_FULL: i18n.msg(
        "common.the_manual_resolution_list_is_full_200_entries",
        "The manual-resolution list is full (200 entries) — delete an "
        "old one before adding another."),
    FLASH_KEY_MANUAL_SAVE_FAILED: i18n.msg(
        "common.couldn_t_save_that_resolution_the_frame_s_state",
        "Couldn't save that resolution — the frame's state directory "
        "may not be writable."),
    FLASH_KEY_MANUAL_DELETE_FAILED: i18n.msg(
        "common.couldn_t_delete_that_entry_the_frame_s_state",
        "Couldn't delete that entry — the frame's state directory may "
        "not be writable."),
    # Distinct from FLASH_KEY_MANUAL_NAME_EMPTY above — the operator did
    # type something, it just can't be turned into an illustration key.
    # Never echoes the rejected value back.
    FLASH_KEY_MANUAL_NAME_UNUSABLE: i18n.msg(
        "common.that_name_can_t_be_used_for_an_illustration_try",
        "That name can't be used for an illustration — try a different "
        "spelling, or a name with letters and numbers."),
    # rule_replaced's copy is a template: the {key} placeholder is filled
    # in by resolve_flash_text()'s own second special case below, never
    # interpolated here.
    FLASH_KEY_RULE_ADDED: i18n.msg(
        "common.rule_added_the_frame_will_use_it_next_time_it",
        "Rule added — the frame will use it next time it wakes and polls."),
    FLASH_KEY_RULE_REPLACED: i18n.msg(
        "common.updated_the_rule_for_key_it_replaces_the_one",
        "Updated the rule for {key} — it replaces the one that was "
        "there before, applied next time the frame wakes and polls."),
    FLASH_KEY_RULE_KEY_INVALID: i18n.msg(
        "common.that_doesn_t_match_the_selected_kind_s_format_a",
        "That doesn't match the selected kind's format — a callsign "
        "(e.g. AFR1234), an ICAO24 hex (e.g. 3944F2), or a 3-letter "
        "prefix (e.g. AFR)."),
    # The entry count is a literal; colour_rules.COLOUR_RULE_MAX_ENTRIES
    # is also 200, and the two must be kept equal by hand (a test pins
    # this).
    FLASH_KEY_RULE_REGISTRY_FULL: i18n.msg(
        "common.the_rules_list_is_full_200_entries_delete_an",
        "The rules list is full (200 entries) — delete an old one "
        "before adding another."),
    FLASH_KEY_RULE_SAVE_FAILED: i18n.msg(
        "common.couldn_t_save_that_rule_the_frame_s_state",
        "Couldn't save that rule — the frame's state directory may not "
        "be writable."),
    FLASH_KEY_RULE_DELETED: i18n.msg(
        "common.rule_deleted_the_frame_will_stop_using_it_next",
        "Rule deleted — the frame will stop using it next time it "
        "wakes and polls."),
    FLASH_KEY_RULE_DELETE_FAILED: i18n.msg(
        "common.couldn_t_delete_that_rule_the_frame_s_state",
        "Couldn't delete that rule — the frame's state directory may "
        "not be writable."),
    # "{n}"/"{s}" are filled from a fresh on-disk read at render time,
    # never carried through the redirect's query string.
    FLASH_KEY_CALENDAR_CONNECTED: i18n.msg(
        "common.connected_n_flight_s_from_this_calendar_in_the",
        "Connected — {n} flight{s} from this calendar in the frame's "
        "current window."),
    # Never echoes anything the operator submitted or any exception text.
    FLASH_KEY_CALENDAR_SYNC_FAILED: i18n.msg(
        "common.saved_but_couldn_t_sync_that_calendar_right_now",
        "Saved, but couldn't sync that calendar right now — check the "
        "URL and try again. The frame will keep retrying on its own "
        "schedule."),
    # States both halves of what a disconnect did: the calendar is
    # disconnected, AND the flights it had supplied are gone from disk —
    # a promise the code keeps and the operator has no other way to learn.
    FLASH_KEY_CALENDAR_DISCONNECTED: i18n.msg(
        "common.calendar_disconnected_the_flights_it_supplied",
        "Calendar disconnected — the flights it supplied have been "
        "deleted from the server."),
    # Deliberately not FLASH_KEY_POLL_ALREADY_RUNNING's copy: that string
    # says nothing about whether the save itself succeeded, which would
    # leave the operator unsure their URL was even stored. This key says
    # plainly that the save landed and the sync will happen on the
    # frame's own next scheduled poll.
    FLASH_KEY_CALENDAR_SYNC_DEFERRED: i18n.msg(
        "common.saved_a_poll_was_already_running_so_this",
        "Saved — a poll was already running, so this calendar will "
        "sync on the frame's next scheduled poll."),
    # "{n}" is filled by resolve_flash_text()'s own fourth special case
    # below, read fresh from disk at render time — never carried through
    # the redirect's query string.
    FLASH_KEY_CALENDAR_CONNECT_OK: i18n.msg(
        "common.calendar_connected_n_flights_found",
        "Calendar connected — {n} flights found."),
    FLASH_KEY_CALENDAR_CONNECT_INVALID: i18n.msg(
        "common.paste_a_valid_calendar_feed_url_to_connect_one",
        "Paste a valid calendar feed URL to connect one."),
    # Never echoes the submitted version or any exception text -- the
    # registry's own return code (unknown/below_floor/same_as_running)
    # never leaks into operator-facing copy either. "busy" gets its own
    # key/copy below, since retrying is the one thing that cannot work
    # while an install is already running.
    FLASH_KEY_UPDATE_SCHEDULE_FAILED: update_page.FLASH_UPDATE_SCHEDULE_FAILED_TEXT,
    FLASH_KEY_UPDATE_CANCEL_FAILED: update_page.FLASH_UPDATE_CANCEL_FAILED_TEXT,
    FLASH_KEY_UPDATE_BUSY: update_page.FLASH_UPDATE_BUSY_TEXT,
}

_SUCCESS = layout.TOAST_TONE_SUCCESS
_INFO = layout.TOAST_TONE_INFO
_WARNING = layout.TOAST_TONE_WARNING
_ERROR = layout.TOAST_TONE_ERROR
_PENDING = layout.TOAST_TONE_PENDING

# Every FLASH_KEY_* -> the tone its toast takes, so a failure and a
# success never look alike. "pending" is a change that is saved but
# only reaches the frame on its next wake; it never hides on its own.
FLASH_TONES = {
    FLASH_KEY_SAVED: _PENDING,
    FLASH_KEY_SAVE_FAILED: _ERROR,
    FLASH_KEY_POLL_TRIGGERED: _INFO,
    FLASH_KEY_POLL_COOLDOWN: _INFO,
    FLASH_KEY_POLL_FAILED: _ERROR,
    # Informational, not itself a failure: a different session/tab is
    # already legitimately running a poll.
    FLASH_KEY_POLL_ALREADY_RUNNING: _INFO,
    FLASH_KEY_ILLUSTRATION_REPLACED: _PENDING,
    # The file the user picked was refused: their input needs changing.
    FLASH_KEY_ILLUSTRATION_REJECTED: _ERROR,
    FLASH_KEY_ILLUSTRATION_REPLACE_FAILED: _ERROR,
    FLASH_KEY_MANUAL_RESOLVED: _PENDING,
    FLASH_KEY_MANUAL_NAME_EMPTY: _ERROR,
    FLASH_KEY_MANUAL_NAME_TOO_LONG: _ERROR,
    FLASH_KEY_MANUAL_NAME_RESERVED: _ERROR,
    # Nothing was wrong with the input; the gap simply closed meanwhile.
    FLASH_KEY_MANUAL_PREFIX_STALE: _WARNING,
    FLASH_KEY_MANUAL_REGISTRY_FULL: _WARNING,
    FLASH_KEY_MANUAL_SAVE_FAILED: _ERROR,
    FLASH_KEY_MANUAL_DELETE_FAILED: _ERROR,
    FLASH_KEY_MANUAL_NAME_UNUSABLE: _ERROR,
    FLASH_KEY_RULE_ADDED: _PENDING,
    FLASH_KEY_RULE_REPLACED: _PENDING,
    FLASH_KEY_RULE_KEY_INVALID: _ERROR,
    FLASH_KEY_RULE_REGISTRY_FULL: _WARNING,
    FLASH_KEY_RULE_SAVE_FAILED: _ERROR,
    FLASH_KEY_RULE_DELETED: _PENDING,
    FLASH_KEY_RULE_DELETE_FAILED: _ERROR,
    FLASH_KEY_CALENDAR_CONNECTED: _SUCCESS,
    # Half done: the URL is saved, the sync is not.
    FLASH_KEY_CALENDAR_SYNC_FAILED: _WARNING,
    FLASH_KEY_CALENDAR_DISCONNECTED: _SUCCESS,
    FLASH_KEY_CALENDAR_SYNC_DEFERRED: _INFO,
    FLASH_KEY_CALENDAR_CONNECT_OK: _SUCCESS,
    FLASH_KEY_CALENDAR_CONNECT_INVALID: _ERROR,
    FLASH_KEY_UPDATE_SCHEDULE_FAILED: _ERROR,
    FLASH_KEY_UPDATE_CANCEL_FAILED: _ERROR,
    FLASH_KEY_UPDATE_BUSY: _INFO,
    # The screen switch reaches the frame within about five minutes, at
    # its next wake; quiet hours and the LED wait for the next wake too.
    FLASH_KEY_DISPLAY_ON: _PENDING,
    FLASH_KEY_DISPLAY_OFF: _PENDING,
    FLASH_KEY_QUIET_ON: _PENDING,
    FLASH_KEY_QUIET_OFF: _PENDING,
    FLASH_KEY_LED_ON: _PENDING,
    FLASH_KEY_LED_OFF: _PENDING,
    FLASH_KEY_QUICK_FAILED: _ERROR,
}

# Every FLASH_KEY_* -> its toast's ARIA role, derived from its tone:
# "alert" (assertive) for a warning or error, "status" (polite)
# otherwise. build_page_context() resolves this into ctx.flash_role.
FLASH_ROLES = {key: layout.TOAST_ROLES[tone] for key, tone in FLASH_TONES.items()}

# A confirmed deletion keeps its success tone but shows a bin, so it does
# not read like something was added.
_FLASH_GLYPHS = {FLASH_KEY_CALENDAR_DISCONNECTED: layout.TOAST_GLYPH_TRASH}

# The three instant switches' outcomes offer an Undo: a real POST of the
# opposite state to the same route, so it works with scripts blocked.
_FLASH_UNDO = {
    FLASH_KEY_DISPLAY_ON: (routes.QUICK_DISPLAY_ROUTE, layout.QUICK_STATE_OFF),
    FLASH_KEY_DISPLAY_OFF: (routes.QUICK_DISPLAY_ROUTE, layout.QUICK_STATE_ON),
    FLASH_KEY_QUIET_ON: (routes.QUICK_QUIET_HOURS_ROUTE, layout.QUICK_STATE_OFF),
    FLASH_KEY_QUIET_OFF: (routes.QUICK_QUIET_HOURS_ROUTE, layout.QUICK_STATE_ON),
    FLASH_KEY_LED_ON: (routes.QUICK_LED_ROUTE, layout.QUICK_STATE_OFF),
    FLASH_KEY_LED_OFF: (routes.QUICK_LED_ROUTE, layout.QUICK_STATE_ON),
}

SEE_HEALTH_TEXT = i18n.msg("common.see_health", "See Health")
_FLASH_LINKS = {FLASH_KEY_MANUAL_PREFIX_STALE: (layout.HEALTH_ROUTE, SEE_HEALTH_TEXT)}

# The query parameters a flash rides on; the dismiss link drops them.
_FLASH_QUERY_PARAMS = ("flash", "rule")


def flash_dismiss_href(request_path):
    """The same page without its flash: the request's own path with every
    other query parameter kept (`?resolve=` survives). A path that is not
    a plain local path (e.g. `//host`) falls back to "/", so the link can
    never leave this site.
    """
    parsed = urlsplit(request_path or "/")
    path = parsed.path if parsed.path.startswith("/") and not parsed.path.startswith("//") else "/"
    kept = [(name, value) for name, value in parse_qsl(parsed.query, keep_blank_values=True)
            if name not in _FLASH_QUERY_PARAMS]
    return path + ("?" + urlencode(kept) if kept else "")


def _flash_action_html(flash_key, return_to):
    if flash_key in _FLASH_UNDO:
        route, state = _FLASH_UNDO[flash_key]
        return layout.toast_post_action_html(
            route, ((layout.QUICK_STATE_FIELD, state), ("return_to", return_to)),
            i18n.t(layout.TOAST_UNDO_TEXT))
    if flash_key in _FLASH_LINKS:
        href, label = _FLASH_LINKS[flash_key]
        return layout.toast_link_action_html(href, i18n.t(label))
    return ""


def flash_toast_html(flash_key, text, request_path):
    """The rendered flash toast for one resolved flash, or None when there
    is no text. `flash_key` picks tone, role, glyph and action; an
    unknown key degrades to an info toast with no action.
    """
    if not text:
        return None
    dismiss_href = flash_dismiss_href(request_path)
    return layout.flash_banner(
        text, role=FLASH_ROLES.get(flash_key), tone=FLASH_TONES.get(flash_key, _INFO),
        dismiss_href=dismiss_href,
        action_html=_flash_action_html(flash_key, urlsplit(dismiss_href).path),
        glyph=_FLASH_GLYPHS.get(flash_key))


def poll_cooldown_remaining(state_dir):
    """Seconds remaining before another `POST /poll-now` is allowed, or 0
    when the cooldown has elapsed. Server-global and persisted in
    `history.db`'s meta table (not the session cookie), so a second
    browser tab cannot bypass it and a service restart does not reset it.
    """
    with history_db.open_db(state_dir) as conn:
        value = history_db.get_meta(conn, history_db.META_LAST_POLL_TRIGGER)
    if not value:
        return 0
    try:
        last_triggered = int(value)
    except (TypeError, ValueError):
        return 0
    remaining = POLL_COOLDOWN_S - (time.time() - last_triggered)
    return int(remaining) if remaining > 0 else 0


def resolve_flash_text(
        flash_key, state_dir, rule_key=None, last_checkin_ts=None, device_cfg=None,
        battery_critical=False):
    """Build this flash's already-translated message text, or None if
    flash_key is unknown.

    rule_key: re-normalised before interpolation — never trusted raw;
    a failed check degrades to the generic FLASH_KEY_RULE_ADDED copy.
    last_checkin_ts/device_cfg/battery_critical: feed the one computed
    delay sentence via the same wake.next_wake_status() triple every
    other reader shares, so they can never disagree.
    """
    if flash_key not in FLASH_MESSAGES:
        return None
    # Translate first, fill placeholders after, so the French template
    # controls where the value lands. One expression, so test_i18n.py's
    # scanner sees FLASH_MESSAGES as a real i18n.t() consumer.
    template = i18n.t(FLASH_MESSAGES[flash_key])
    if flash_key == FLASH_KEY_SAVED:
        next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
            last_checkin_ts, device_cfg or {}, battery_critical=battery_critical)
        delay_template = frame_state.delay_sentence_template(
            next_wake_iso, effective_interval_s, hold_reason)
        delay_text = i18n.t(delay_template)
        if "%s" in delay_text:
            next_wake_parsed = layout.parse_iso(next_wake_iso)
            clock = (
                layout.local_clock_text(next_wake_parsed)
                if next_wake_parsed is not None else None)
            delay_text = (
                delay_text % clock if clock else i18n.t(frame_state.DELAY_UNKNOWN))
        # Kept capitalised: the toast shows it as its own detail line
        # under the "Saved" title, a standalone sentence.
        return template % delay_text
    if flash_key == FLASH_KEY_POLL_COOLDOWN:
        return template.format(n=poll_cooldown_remaining(state_dir))
    if flash_key == FLASH_KEY_CALENDAR_CONNECTED:
        # Read fresh from disk, on this redirect target's own render —
        # never carried through the redirect's query string, which is
        # client-supplied on the way back in. load_calendar_registry() is
        # contractually never-raising, which is what makes it safe to
        # call unconditionally here on every render that carries this key.
        count = len(calendar_rules.load_calendar_registry(state_dir)["entries"])
        return template.format(n=count, s="" if count == 1 else "s")
    if flash_key == FLASH_KEY_CALENDAR_CONNECT_OK:
        count = len(calendar_rules.load_calendar_registry(state_dir)["entries"])
        return template.format(n=count)
    if flash_key == FLASH_KEY_RULE_REPLACED:
        normalised_key = colour_rules.normalise_rule_callsign(rule_key)
        if normalised_key is None:
            # Goes through i18n.t() like every other return path here —
            # an invalid rule_key must not silently produce an
            # untranslated English banner under a French request.
            return i18n.t(FLASH_MESSAGES[FLASH_KEY_RULE_ADDED])
        return template.format(key=normalised_key)
    return template
