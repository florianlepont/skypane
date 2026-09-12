"""companion/frame_state.py — the one frame-state resolution and the one
delay sentence (D-03/D-04, CFG-26/CFG-27, 22-02-PLAN.md Task 2).

Sits beside companion/wake.py, companion/i18n.py and companion/screens.py
in this same package — a shared, page-independent, VIEW-FREE module.
"View-free" is load-bearing, not a style preference: this module returns
a state name and a template-key string, never HTML, never a dot-class
string, never formatted clock text. The Frame strip, Home's status row,
Health's Frame tile and every settings delay caption each render their
OWN markup from this module's plain return values — layout.status_dot()
maps a state to a CSS class, layout.local_clock_text() formats the
clock, companion.i18n.t() translates the template — none of that
happens here. This module therefore imports neither companion.layout
nor any companion.pages module, matching companion/wake.py's and
companion/battery.py's own page-independent boundary.

Consumes `server.wake.next_wake_status()`'s `(next_wake_iso,
effective_interval_s, hold_reason)` triple (via companion/wake.py's
re-export seam — this module never imports server.wake directly) as
its own three of four inputs, `now` being the caller's own clock
reference (real wall-clock time at render, unlike next_wake_status()'s
own last-check-in-relative epoch). Every consumer — the strip, the
tiles, Home, the settings captions (plans 22-04, 22-05, 22-07) — calls
`resolve_state()` and `delay_sentence_template()` against that SAME
triple, so disagreement between them is impossible by construction
(22-UI-SPEC.md §3.3 binding rule 5): there is exactly one place that
decides whether the frame is due, held or late, and exactly one place
that says when a change will reach it.

Three states, encoding 22-UI-SPEC.md §3.3's condition table and its six
binding rules:

  STATE_DUE     `now < next_wake` OR `now < next_wake + 2 * interval` —
                the grace window is INVISIBLE (rule 3): there is no
                third, "slightly late" state and no colour shift inside
                it. One threshold, one flip.
  STATE_HELD    `hold_reason` is `wake.HOLD_QUIET_HOURS`, regardless of
                how much time has elapsed since `next_wake` (rule 4: a
                held frame cannot escalate to late by elapsed time
                alone — lateness is measured against the held-AWARE
                next wake, which `next_wake_status()` already extended
                to the window's own end, so a frame missing its 07:05
                wake is only late at 07:05 + 2 * interval).
  STATE_LATE    `now >= next_wake + 2 * effective_interval_s` AND not
                held.
  STATE_UNKNOWN No check-in recorded yet (no usable next-wake data at
                all) — no dot class is claimed for this state; the
                caller's own fallback applies.

Rule 1 (held uses a neutral dot, never a warning dot) and rule 2 (no
status colour is used as text, in any of the three real states) are
NOT this module's to encode — they are choices a renderer makes from
the state name this module returns; this module never claims a CSS
class or a colour token, which is precisely what keeps rule 1 and rule
2 impossible to violate from here. Rule 6 (the nightly regression: with
quiet hours 23:00-07:00, a last check-in at 22:58 and the clock at
02:00 Europe/Paris, the resolved state is `STATE_HELD` and never
`STATE_LATE`) is pinned by `companion/test_view_pages.py`.

The delay sentence (D-04) is derived from the SAME triple, in exactly
three branches — due, held, unknown — never a fourth "late" branch: a
setting change still lands at the same next real wake regardless of
whether the PREVIOUS wake happened to be reported late, so a late
frame's delay sentence is the same "due" wording. `delay_sentence_template()`
returns the bare English template string (also its own i18n_fr lookup
key, matching every other catalogue in this codebase) with one `%s`
placeholder for the formatted clock text — `companion.i18n.t()` %
already-formatted-clock is the caller's job, not this module's, so this
stays free of any clock-formatting dependency too.

Stdlib-only (datetime). Never raises: every malformed input degrades to
STATE_UNKNOWN / DELAY_UNKNOWN, matching companion/wake.py's and
companion/layout.py's own never-raise idiom for a value that reaches a
page render.
"""
from datetime import datetime, timedelta, timezone

from companion import wake

# --- The three frame states (D-03) --------------------------------------

STATE_DUE = "due"
STATE_HELD = "held"
STATE_LATE = "late"
STATE_UNKNOWN = "unknown"

# --- The three headlines (22-UI-SPEC.md §1 Copywriting Contract) -------
#
# `%s` placeholders only, never f-strings or `.format()`, matching every
# other catalogue in this codebase (companion/layout.py's own
# NEXT_UPDATE_TEMPLATE/EXPECTED_SINCE_TEMPLATE precedent, which these
# constants are the view-free successors of — plans 22-04/22-05 delete
# the layout.py originals in the same commit as their own French
# entries, once their own consumers migrate to this module).

HEADLINE_DUE = "Next update ≈ %s"
HEADLINE_HELD = "Next wake around %s · quiet hours"
HEADLINE_LATE = "Expected since %s"

# --- The three delay-sentence branches (D-04) ---------------------------
#
# Replaces every one of this phase's four retired wordings ("Applies the
# next time the frame wakes up" as a hard-coded per-control literal,
# "Takes effect within about 5 minutes", "Applies on the next scheduled
# poll, which may now be hours away", and the flash variant "Saved —
# will apply on the frame's next scheduled refresh") with one computed
# sentence in exactly three branches.

DELAY_DUE = "Applies at the next wake, around %s."
DELAY_HELD = "Applies when quiet hours end, around %s."
DELAY_UNKNOWN = "Applies the next time the frame wakes up."


def _parse_reference(value):
    """Parse `value` — a datetime already, or an ISO-8601 string, or
    None/anything else — into an aware datetime, or return None. A
    naive result is stamped UTC, matching every other parser in this
    codebase (companion/layout.py's parse_iso(), server/wake.py's own
    last_checkin_ts parsing). Never raises.
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
    """Resolve one of `STATE_DUE`/`STATE_HELD`/`STATE_LATE`/
    `STATE_UNKNOWN` from `server.wake.next_wake_status()`'s own
    `(next_wake_iso, effective_interval_s, hold_reason)` triple plus a
    caller-supplied `now` (a datetime or an ISO-8601 string; real
    wall-clock time at render, unlike the triple's own
    last-check-in-relative inputs).

    `hold_reason` is checked FIRST, before any time arithmetic and even
    before `next_wake_iso`/`now` are parsed (22-UI-SPEC.md §3.3 rule 4):
    a held frame can never escalate to late by elapsed time alone,
    because held-ness is a fact about WHY the wake was scheduled, not
    about how long ago it was supposed to happen. `next_wake_status()`
    already folded the quiet-hours window into `next_wake_iso` itself,
    so this state alone is sufficient — no separate "how long have we
    been held" arithmetic is needed or wanted here.

    Degrades to `STATE_UNKNOWN` — never raises — when `next_wake_iso`
    is falsy, `effective_interval_s` is None, or either `next_wake_iso`
    or `now` fails to parse: exactly the "no check-in recorded yet"
    case and any other degraded input.
    """
    if hold_reason == wake.HOLD_QUIET_HOURS:
        return STATE_HELD
    if not next_wake_iso or effective_interval_s is None:
        return STATE_UNKNOWN
    next_wake = _parse_reference(next_wake_iso)
    now_parsed = _parse_reference(now)
    if next_wake is None or now_parsed is None:
        return STATE_UNKNOWN
    # Rule 3: the grace window is invisible — one threshold, one flip.
    # Between next_wake and next_wake + 2 * effective_interval_s the
    # state stays STATE_DUE with the SAME copy; there is no third,
    # "slightly late" treatment.
    grace_cutoff = next_wake + timedelta(seconds=2 * effective_interval_s)
    if now_parsed >= grace_cutoff:
        return STATE_LATE
    return STATE_DUE


def headline_template(state):
    """The headline template constant for `state` — `HEADLINE_DUE` for
    `STATE_DUE` and `STATE_UNKNOWN` alike (an unknown frame has never
    reported in, so "next update" framing degrades gracefully rather
    than claiming a state this module cannot support), `HEADLINE_HELD`
    for `STATE_HELD`, `HEADLINE_LATE` for `STATE_LATE`. Never raises;
    an unrecognised state string also degrades to `HEADLINE_DUE` rather
    than returning None into a page render.
    """
    if state == STATE_HELD:
        return HEADLINE_HELD
    if state == STATE_LATE:
        return HEADLINE_LATE
    return HEADLINE_DUE


def delay_sentence_template(next_wake_iso, effective_interval_s, hold_reason, now=None):
    """The delay-sentence template constant for the SAME
    `(next_wake_iso, effective_interval_s, hold_reason)` triple
    `resolve_state()` takes — exactly three branches, never a fourth
    "late" branch (D-04): a setting change lands at the same next real
    wake regardless of whether the previous wake happened to be
    reported late, so a late frame's delay sentence is the same "due"
    wording `DELAY_DUE` carries. `now` is accepted for signature
    symmetry with `resolve_state()` but is not itself consulted — the
    delay sentence never depends on how much time has elapsed, only on
    whether a next wake is known at all and whether it is held.

    Returns `DELAY_UNKNOWN` when `next_wake_iso` is falsy or
    `effective_interval_s` is None (no check-in recorded yet, or the
    interval could not be determined), `DELAY_HELD` when `hold_reason`
    is `wake.HOLD_QUIET_HOURS`, otherwise `DELAY_DUE`. Never raises.
    """
    if not next_wake_iso or effective_interval_s is None:
        return DELAY_UNKNOWN
    if hold_reason == wake.HOLD_QUIET_HOURS:
        return DELAY_HELD
    return DELAY_DUE
