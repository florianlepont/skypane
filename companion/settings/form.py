"""Shared settings-form helpers: field-error rendering, the settings
form's own id, the "Current" badge and the dirty-tracking section
attribute, plus the "next wake" caption suffix and the checkbox/value
repopulation helpers a rejected save needs. Every other settings-group
module imports from here; this module never imports a page module or
another settings-group module.
"""
from companion import i18n
from companion.layout import escape_html


# Interpolated twice — the settings <form>'s id and the dirty-bar save
# button's form attribute — and the two must never be re-typed as
# literals, since a mismatch would produce a Save button that looks
# correct in markup and silently submits nothing.
SETTINGS_FORM_ID = "settings-form"

# The "Current" badge's own text, server-rendered onto the saved
# chip/card as `data-current-label` and read back by
# `content: attr(data-current-label)` in style.css.
CURRENT_BADGE_LABEL = i18n.msg("display.current", "Current")
# The attribute the badge's content: attr(...) reads. Written as
# literal text at both the markup site below and in style.css.
CURRENT_BADGE_ATTR = "data-current-label"

# Read by companion/static/dirty-state.js; that static file imports
# nothing from this module, so the two must be kept equal by hand.
DIRTY_SECTION_ATTR = "data-dirty-section"

# This feature can only colour a flight that happens to be the one
# currently on screen — it does not track, watch, follow, monitor,
# notify, or know a flight is happening independently of what is on
# screen, and no string below (nor its sibling
# `companion.settings.calendar.CALENDAR_HOW_IT_WORKS_BODY`) may imply
# otherwise. Shared here because `notifications_group()` reuses this
# same summary label rather than a second, near-duplicate string.
# Owned by companion/i18n_fr/calendar_group.py, not this module's own
# display.py — the Calendar row's own connection block is where this
# label's French sibling lives.
CALENDAR_HOW_IT_WORKS_SUMMARY = i18n.msg("calendar_group.how_it_works", "How it works")

# The "Selected" visually-hidden text beside a chosen palette/runway
# chip's check icon — shared by companion.settings.theme and
# companion.settings.runway_led, declared once here so the two never
# drift onto two different ids for the same word.
SELECTED_LABEL = i18n.msg("display.selected", "Selected")


def _field_error_html(errors, field, control_id):
    """"" when `field` carries no message in `errors`, otherwise a
    single `role="alert"` paragraph rendered after the offending
    control. `control_id` need not match a real DOM id on the control —
    it only builds the stable anchor id `_field_error_attrs()` points
    `aria-describedby` at, so the message is programmatically
    associated with the control, not merely visually adjacent.
    """
    message = errors.get(field) if errors else None
    if not message:
        return ""
    return (
        '<p class="field-error text-label" id="%s-error" role="alert">%s</p>'
    ) % (escape_html(control_id), escape_html(i18n.t(message)))


def _describedby_attr(*ids):
    """The single builder of every `aria-describedby` fragment this
    file emits. Drops every falsy id and joins the survivors with one
    space, in the order given (hint first, then error). Returns "" when
    no id survives, so no control ever emits a bare `aria-describedby=""`.
    """
    present = [control_id for control_id in ids if control_id]
    if not present:
        return ""
    return ' aria-describedby="%s"' % escape_html(" ".join(present))


# The suffix appended to a caption's own apply-timing clause when the
# next-wake value is known — never baked into the caption constant
# itself, so the caption reads unchanged when the value is not known.
NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE = i18n.msg("display.next_wake_2", " (next wake ≈ %s)")


def _with_next_wake(caption, next_wake_clock):
    """`caption` unchanged when `next_wake_clock` is falsy — no
    placeholder, no "unknown" — otherwise `caption` plus
    `NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % next_wake_clock`. The single
    implementation every caption site below uses.

    `caption` is translated by the caller; this function only
    translates its own suffix template, before substituting
    `next_wake_clock` into it.
    """
    if not next_wake_clock:
        return caption
    return caption + (i18n.t(NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE) % next_wake_clock)


def _field_error_attrs(errors, field, control_id, hint_id=None):
    """The ARIA attribute fragment for the control `_field_error_html()`
    built an error anchor for, folding in an optional `hint_id` via
    `_describedby_attr()` — hint first, then the error id.

    Three shapes: no error and no hint -> `""`; no error, a hint ->
    ` aria-describedby="{hint_id}"` alone; an error (hint or not) ->
    ` aria-invalid="true"` plus a combined `aria-describedby`.

    Applied to controls with exactly one natural DOM element to
    decorate; the three radio-group fields render their error the same
    way but skip this fragment entirely, since no single native input
    in a same-named radio group is uniquely "the" control to describe
    — their hint links to the `role="radiogroup"` container instead.
    """
    has_error = bool(errors and errors.get(field))
    error_id = ("%s-error" % control_id) if has_error else None
    describedby = _describedby_attr(hint_id, error_id)
    if has_error:
        return ' aria-invalid="true"%s' % describedby
    return describedby


def _submitted_or_current(submitted, field, current):
    """`submitted[field]` when `field` is present in `submitted` — an
    empty string is a meaningful submitted value, never treated as
    absent — else `current`. `submitted` is `None` for every render()
    call that is not re-rendering a rejected save, so `current` always
    wins then. Never `or`.
    """
    if submitted is not None and field in submitted:
        return submitted[field]
    return current


def _note_error(errors, field, message):
    """No-ops when `errors is None`. Otherwise sets `errors[field]`
    only if that field has no message yet, so a later, more generic
    gate can never overwrite an earlier, more specific one. Shared by
    `companion.settings.form_post`'s per-group resolvers.
    """
    if errors is None:
        return
    if field not in errors:
        errors[field] = message


def _submitted_checkbox_checked(submitted, field, checked_value, current_checked):
    """The rendered `checked` state for one of the absent-means-False
    checkbox fields on a rejected save's re-render.

    When a real submission happened (`submitted is not None`), an
    absent field means unchecked, and a present-but-wrong value also
    renders unchecked (the field's own error message reports the
    problem, never a bogus stuck-on box). `submitted is None` (an
    ordinary page-load render, never a rejected-save re-render) falls
    back to `current_checked` untouched — this is why `render()` must
    not collapse a `None` `submitted` to `{}`.
    """
    if submitted is None:
        return bool(current_checked)
    return submitted.get(field) == checked_value
