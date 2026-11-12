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


def save_bar_html(form_id, carried_href=None, cancel_href=None, title=None,
                  save_attrs=None, inline=False, reveal_on_change=False, shown=False):
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
    """
    modifier = " dirty-bar--inline" if inline else ""
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
            '<div class="dirty-bar%s"%s role="region" aria-label="%s">'
            '<span class="dirty-bar__message">%s</span>'
            '<a class="btn btn--secondary dirty-bar__cancel" href="%s">%s</a>'
            '<button type="submit" class="btn btn--primary dirty-bar__save" form="%s" %s>%s</button>'
            "</div>"
        ) % (modifier, tracking, label, label, escape_html(cancel_href), cancel, form,
             save_attrs, save)
    carried = (
        ' data-dirty-carried="%s"' % escape_html(carried_href)
        if carried_href is not None else " " + WAIT_ATTR)
    return (
        '<div class="dirty-bar%s" data-dirty-bar%s role="region" aria-label="%s" '
        'data-dirty-several="%s" data-dirty-saving="%s" data-dirty-initial-text="%s">'
        '<span class="dirty-bar__message" data-dirty-count role="status"></span>'
        '<button type="reset" form="%s" class="btn btn--secondary dirty-bar__cancel" data-dirty-cancel>%s</button>'
        '<button type="submit" class="btn btn--primary dirty-bar__save" form="%s" %s>%s</button>'
        "</div>"
    ) % (
        modifier, carried, escape_html(i18n.t(UNSAVED_TEXT)),
        escape_html(i18n.t(UNSAVED_IN_TEXT)), escape_html(i18n.t(SAVING_TEXT)),
        escape_html(i18n.t(UNSAVED_TEXT)),
        form, cancel, form, save_attrs, save)
