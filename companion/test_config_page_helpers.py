"""Shared seeding helpers for the `companion/test_config_page*.py` family.
Not a test module itself — `__test__ = False` keeps pytest from
collecting it directly (enforced by test_suite_guards.py's G9 rule).
Tests needing a real `companion/app.py` server get one from
`companion/conftest.py`'s fixtures; every other check calls
`companion.pages.config_page`'s own functions directly, in-process,
against a `tmp_path`-backed state directory.
"""
import contextlib
import html
import json
import os
import re

from companion.pages import config_page
from server import device_config

__test__ = False


def write_device_config(state_dir, theme, tracked_runway, led_enabled=None):
    """Write a minimal device_config.json directly (bypassing
    handle_post(), the code path most checks in this chain exercise) so a
    check can seed a starting on-disk state before calling the function
    under test."""
    state_dir = str(state_dir)
    os.makedirs(state_dir, exist_ok=True)
    doc = {"theme": theme, "tracked_runway": tracked_runway}
    if led_enabled is not None:
        doc["led_enabled"] = led_enabled
    with open(device_config.device_config_path(state_dir), "w") as fh:
        json.dump(doc, fh)


# Every mechanism the Aspect-card accordion rebuild retired outright —
# grepped whole-repo for a surviving consumer before removal.
ASPECT_RETIRED_MARKUP_TOKENS = (
    "theme-carousel", "frame-colours", "colour_usage", "usage-panel",
    "__dots", "theme-chip-grid--strip",
)


def runway_section_start(rendered, after=0):
    """Offset of the opening tag of the Runway section (the card that follows the Aspect card),
    found from its id-anchored heading so it does not depend on the card's wrapper class."""
    heading = rendered.index('id="%s"' % config_page.RUNWAY_GROUP_HEADING_ID, after)
    return rendered.rindex("<div", after, heading)


def aspect_usage_row_bounds(rendered, usage):
    """The `[start, end)` slice of `rendered` covering exactly one look on
    the look card: Departures and Arrivals are the two framed pictures,
    Calendar flights the first Special looks row, and the rules the rest
    of the Special looks list (rule rows plus the "Add a special look"
    form) up to the Runway section's own id-anchored heading.
    """
    if usage == config_page.COLOUR_USAGE_RULES:
        start = rendered.index(
            '<li class="special-row', rendered.index('data-look-usage="calendar"'))
        return start, runway_section_start(rendered, start)
    start = rendered.rindex("<", 0, rendered.index('data-look-usage="%s"' % usage))
    following = {
        config_page.COLOUR_USAGE_DEPARTURES: 'data-look-usage="arrivals"',
        config_page.COLOUR_USAGE_ARRIVALS: 'class="special-looks"',
    }
    if usage in following:
        end = rendered.index(following[usage], start)
    else:
        end = rendered.index('<li class="special-row', start + 1)
    return start, end


def rules_row_segment(rendered):
    """The per-flight rules' own segment of `rendered` (see
    `aspect_usage_row_bounds()`): every rule row and the add form.
    """
    start, end = aspect_usage_row_bounds(rendered, config_page.COLOUR_USAGE_RULES)
    return rendered[start:end]


CALENDAR_BASE_CTX = {
    "device_config": {"theme": "white", "tracked_runway": "3"},
    "poll_cooldown_remaining": 0,
    "now": "2026-09-07T09:12:04+00:00",
}
"""33-12-PLAN.md: the render() context every Calendar-card check in this
chain's parts 04/05 starts from, overridden per check with
calendar_configured/calendar_last_synced_at/etc. Ported here (rather than
re-derived per part) since 33-13's own remaining Calendar checks (further
down the legacy harness's main()) need the identical base context."""


def strip_js_line_and_block_comments(js):
    """Strips `//` line comments and `/* */` block comments from `js`
    WITHOUT touching string/template literals — unlike
    `companion_markup.strip_js_comments_and_strings()`, which a check
    asserting on the literal content of a string (e.g. a quoted event
    name) cannot use, since that would also erase the very string
    literal the check is looking for. Operates on served JS text (fetched
    over HTTP), never a file opened from disk.
    """
    without_block = re.sub(r"/\*.*?\*/", "", js, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", without_block)


def caption_word_count_text(fragment):
    """THE ONE COUNTING RULE the editorial floor applies: strip tags,
    unescape HTML entities, collapse internal whitespace, then strip a
    single leading em dash and its following space -
    layout.section_intro_html()'s own intro sentences legitimately open
    with '- ', and that leading mark is not a WORD by any reading of 'at
    most 12 words'.
    """
    stripped = re.sub(r"<[^>]*>", "", fragment)
    text = html.unescape(stripped).strip()
    if text.startswith("— "):
        text = text[2:]
    return re.sub(r"\s+", " ", text).strip()


@contextlib.contextmanager
def i18n_lang(lang):
    """Render under `lang` for the body of the `with`, then restore English."""
    from companion import prefs
    prefs.set_request_prefs(lang=lang)
    try:
        yield
    finally:
        prefs.set_request_prefs(lang="en")
