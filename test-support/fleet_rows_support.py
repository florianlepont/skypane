"""Helpers for browser tests that reach a Fleet group from 960px, where the groups sit in
dialogs behind summary rows (below 960px they are on the page)."""

WIDE_FROM_PX = 960


def is_wide(page):
    return page.viewport_size["width"] >= WIDE_FROM_PX


def open_dialog(page, name):
    """Open the Fleet dialog `name` (`device`, `versions`, `settings`, `others`) from its summary
    row, and wait for it to be open. A no-op below 960px."""
    if not is_wide(page):
        return
    dialog_id = "dlg-fleet-" + name
    page.locator("a.fleet-sum[href='#%s']" % dialog_id).click()
    page.wait_for_function(
        "id => document.getElementById(id).open", arg=dialog_id, timeout=10000)


def close_dialog(page):
    """Dismiss the open dialog with Escape and wait for it to close. A no-op below 960px."""
    if not is_wide(page):
        return
    page.keyboard.press("Escape")
    page.wait_for_function("() => !document.querySelector('dialog[open]')", timeout=10000)
