"""The one frame-state resolution and the one delay sentence.

Returns a state name and a template-key string only, never HTML or
formatted text — rendering is the caller's job. Every consumer resolves
state from the same `server.wake.next_wake_status()` triple, so they
can never disagree on due/held/late. Depends only on stdlib plus
companion.wake and companion.i18n (for the six wordings' stable message
ids). Never raises: malformed input degrades to STATE_UNKNOWN/
DELAY_UNKNOWN.
"""
from datetime import datetime, timedelta, timezone

from companion import wake
import companion.i18n as i18n

# --- The three frame states ---------------------------------------------

STATE_DUE = "due"
STATE_HELD = "held"
STATE_LATE = "late"
STATE_UNKNOWN = "unknown"

# --- The three headlines -------------------------------------------------
#
# `%s` placeholders only, never f-strings or `.format()`, matching every
# other catalogue in this codebase. HEADLINE_DUE/HEADLINE_LATE are owned
# by companion/i18n_fr/home.py's catalogue (untouched by this plan;
# migrated later); HEADLINE_HELD is owned by this module's own
# companion/i18n_fr/frame_state.py catalogue, migrated alongside it.

HEADLINE_DUE = i18n.msg("home.next_update", "Next update ≈ %s")
HEADLINE_HELD = i18n.msg(
    "frame_state.next_wake_around_quiet_hours",
    "Next wake around %s · quiet hours")
HEADLINE_LATE = i18n.msg("home.expected_since", "Expected since %s")

# --- The three delay-sentence branches ------------------------------------
#
# One computed sentence in exactly three branches, replacing every
# hard-coded per-control latency caption this codebase used to carry.
# DELAY_UNKNOWN is owned by companion/i18n_fr/display.py's catalogue
# (untouched by this plan; migrated later); DELAY_DUE/DELAY_HELD are
# owned by this module's own catalogue.

DELAY_DUE = i18n.msg(
    "frame_state.applies_at_the_next_wake_around",
    "Applies at the next wake, around %s.")
DELAY_HELD = i18n.msg(
    "frame_state.applies_when_quiet_hours_end_around",
    "Applies when quiet hours end, around %s.")
DELAY_UNKNOWN = i18n.msg(
    "display.applies_the_next_time_the_frame_wakes_up",
    "Applies the next time the frame wakes up.")


def _parse_reference(value):
    """Parse `value` (a datetime, an ISO-8601 string, or anything else)
    into an aware datetime, or None. A naive result is stamped UTC.
    Never raises.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def resolve_state(next_wake_iso, effective_interval_s, hold_reason, now):
    """Resolve DUE/HELD/LATE/UNKNOWN from `next_wake_status()`'s triple
    plus a caller-supplied `now`. `hold_reason` is checked first: a held
    frame can never escalate to late by elapsed time alone, since the
    quiet-hours window is already folded into `next_wake_iso`. LATE
    fires at `next_wake + 2 * interval`. Degrades to UNKNOWN, never
    raises, on falsy/unparseable input.
    """
    if hold_reason == wake.HOLD_QUIET_HOURS:
        return STATE_HELD
    if not next_wake_iso or effective_interval_s is None:
        return STATE_UNKNOWN
    next_wake = _parse_reference(next_wake_iso)
    now_parsed = _parse_reference(now)
    if next_wake is None or now_parsed is None:
        return STATE_UNKNOWN
    grace_cutoff = next_wake + timedelta(seconds=2 * effective_interval_s)
    if now_parsed >= grace_cutoff:
        return STATE_LATE
    return STATE_DUE


def headline_template(state):
    """The headline template for `state`. STATE_UNKNOWN degrades to
    HEADLINE_DUE, like any unrecognised state. Never raises.
    """
    if state == STATE_HELD:
        return HEADLINE_HELD
    if state == STATE_LATE:
        return HEADLINE_LATE
    return HEADLINE_DUE


def delay_sentence_template(next_wake_iso, effective_interval_s, hold_reason, now=None):
    """The delay-sentence template for the same triple `resolve_state()`
    takes — three branches only, never a fourth "late" one: a late
    frame's next real wake is unaffected, so it gets DELAY_DUE too.
    `now` is accepted for signature symmetry but not consulted. Never
    raises.
    """
    if not next_wake_iso or effective_interval_s is None:
        return DELAY_UNKNOWN
    if hold_reason == wake.HOLD_QUIET_HOURS:
        return DELAY_HELD
    return DELAY_DUE
