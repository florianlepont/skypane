"""companion/ui_save_bar.py: the one floating Cancel and Save bar.

Every page with something to save renders this bar and nothing else: the
settings pages and the Fleet settings, the Location page and the form pages
of Personalisation. One structure (a message, then Cancel, then Save), one
stylesheet block (`.dirty-bar`) and one script (`static/dirty-state.js`).

Two modes share the markup:

* tracked: `form_id` names a `data-dirty-form` form. The bar is in the page
  without script (a plain, always visible Save, the no-script floor);
  dirty-state.js hides it until a field differs and writes the message.
* page: `cancel_href` makes the bar a fixture of a page that is itself the
  edit: Cancel is a link back, the message is the page title. It is always
  shown, or with `reveal_on_change` only once a field of the form differs.
"""
import companion.i18n as i18n
from companion import ui_modal
from companion.ui_base import escape_html

SAVE_TEXT = i18n.msg("look.save", "Save")
CANCEL_TEXT = i18n.msg("display.cancel", "Cancel")
UNSAVED_TEXT = i18n.msg("display.unsaved_changes", "Unsaved changes")
# Followed by the list of the areas that changed, joined with ", " by the script.
UNSAVED_IN_TEXT = i18n.msg("display.unsaved_changes_in", "Unsaved changes:")
SAVING_TEXT = i18n.msg("display.saving", "Saving…")

# Marker on the Save button of the tracked bar: the one control a visitor
# without script saves with.
SAVE_FALLBACK_ATTR = "data-static-save-fallback"
# Marker on a bar that only shows once something changed. With scripts on the
# stylesheet keeps a marked bar out of the first paint and dirty-state.js
# removes the mark when it takes the bar over; without scripts the bar shows.
# Must equal static/dirty-state.js's WAIT_ATTR.
WAIT_ATTR = "data-dirty-wait"

# The unsaved-changes question every page with this bar carries, so leaving
# one through an in-app link asks instead of dropping the edit. The shell
# renders it once per page; dirty-state.js finds it by LEAVE_DIALOG_HOOK and
# reads the addresses the page's own save may return to off the bar.
LEAVE_DIALOG_ID = "unsaved-changes"
LEAVE_DIALOG_HOOK = "leave-dialog"
LEAVE_RETURNS_ATTR = "data-leave-returns"
LEAVE_TITLE = i18n.msg("display.leave_title", "Unsaved changes")
LEAVE_TEXT = i18n.msg(
    "display.leave_text", "You have changes that are not saved. What do you want to do?")
LEAVE_SAVE = i18n.msg("display.leave_save", "Save and continue")
LEAVE_DISCARD = i18n.msg("display.leave_discard", "Discard")
LEAVE_STAY = i18n.msg("display.leave_stay", "Stay here")


def leave_dialog_html():
    """The closed dialog a script opens when a page with a save bar is left
    through an in-app link while something on it is unsaved."""
    return ui_modal.choice_dialog_html(
        LEAVE_DIALOG_ID, i18n.t(LEAVE_TITLE), i18n.t(LEAVE_TEXT), i18n.t(LEAVE_SAVE),
        i18n.t(LEAVE_DISCARD), i18n.t(LEAVE_STAY), LEAVE_DIALOG_HOOK)


def save_bar_html(form_id, carried_href=None, cancel_href=None, title=None,
                  save_attrs=None, inline=False, reveal_on_change=False, shown=False,
                  return_routes=()):
    """The bar markup for the form `form_id`.

    `carried_href`: the bar is shown from the start for unsaved values that
    came with the page; Cancel returns there. `cancel_href` and `title`
    select the page mode. `save_attrs` is raw attribute text for the Save
    button (a caller escapes what it passes); the tracked bar defaults to the
    fallback marker. `inline` adds the modifier that, on a phone, turns the bar
    into the two buttons of the card that holds it (no strip of its own; the
    message stays in the page for assistive technology only). `reveal_on_change`
    makes a page-mode bar appear only once a field of its form differs from the
    value it loaded with (the bar stays in the page without script, so a visitor
    without script can still save); `shown` keeps it visible from the start, for a
    page redrawn with a refused value that has to be corrected and saved.
    `return_routes` are the addresses this page's save accepts as its return
    target: the unsaved-changes dialog's "Save and continue" names one of them
    and the save lands there, and for any other destination it saves and stays.
    """
    modifier = " dirty-bar--inline" if inline else ""
    returns = (
        ' %s="%s"' % (LEAVE_RETURNS_ATTR, escape_html(" ".join(return_routes)))
        if return_routes else "")
    save = escape_html(i18n.t(SAVE_TEXT))
    cancel = escape_html(i18n.t(CANCEL_TEXT))
    form = escape_html(form_id)
    if save_attrs is None:
        save_attrs = "" if cancel_href is not None else SAVE_FALLBACK_ATTR
    if cancel_href is not None:
        label = escape_html(title)
        tracking = (
            " data-dirty-page" + (" data-dirty-keep" if shown else " " + WAIT_ATTR)
            if reveal_on_change else "")
        return (
            '<div class="dirty-bar%s"%s%s role="region" aria-label="%s">'
            '<span class="dirty-bar__message">%s</span>'
            '<a class="btn btn--secondary dirty-bar__cancel" href="%s">%s</a>'
            '<button type="submit" class="btn btn--primary dirty-bar__save" form="%s" %s>%s</button>'
            "</div>"
        ) % (modifier, tracking, returns, label, label, escape_html(cancel_href), cancel,
             form, save_attrs, save)
    carried = (
        ' data-dirty-carried="%s"' % escape_html(carried_href)
        if carried_href is not None else " " + WAIT_ATTR)
    return (
        '<div class="dirty-bar%s" data-dirty-bar%s%s role="region" aria-label="%s" '
        'data-dirty-several="%s" data-dirty-saving="%s" data-dirty-initial-text="%s">'
        '<span class="dirty-bar__message" data-dirty-count role="status"></span>'
        '<button type="reset" form="%s" class="btn btn--secondary dirty-bar__cancel" data-dirty-cancel>%s</button>'
        '<button type="submit" class="btn btn--primary dirty-bar__save" form="%s" %s>%s</button>'
        "</div>"
    ) % (
        modifier, carried, returns, escape_html(i18n.t(UNSAVED_TEXT)),
        escape_html(i18n.t(UNSAVED_IN_TEXT)), escape_html(i18n.t(SAVING_TEXT)),
        escape_html(i18n.t(UNSAVED_TEXT)),
        form, cancel, form, save_attrs, save)
