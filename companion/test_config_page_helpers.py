"""Shared seeding helpers for the `companion/test_config_page*.py`
migration chain (33-09..33-13). Not a test module itself — `__test__ =
False` keeps pytest from ever collecting it directly, and
`companion/test_suite_guards.py`'s G9 rule enforces that this marker is
present.

The original `companion/test_config_page.py`'s subprocess-lifecycle
plumbing (the legacy harness class, its HTTP client and its
non-redirect-following opener) is deliberately NOT ported here: migrated
tests that need a real `companion/app.py` server get one from
`companion/conftest.py`'s `app_server` / `module_app_server_factory`
fixtures instead, and every other check in this chain calls
`companion.pages.config_page`'s own functions directly, in-process,
against a `tmp_path`-backed state directory.

`ASPECT_RETIRED_MARKUP_TOKENS` / `aspect_usage_row_bounds()` /
`rules_row_segment()` are ported here (33-11-PLAN.md) rather than into
`companion/test_config_page_03.py` alone, because the legacy harness's
own `main()` still uses its private originals for checks not yet
migrated by parts 04/05 (33-12/33-13) — this module is their shared,
reusable home so a later part imports rather than re-derives them.
"""
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


# 30-05-PLAN.md Task 1 (CFG-85): every mechanism the Aspect-card accordion
# rebuild retired outright — grepped whole-repo for a surviving consumer
# before 30-04-PLAN.md's own commit landed.
ASPECT_RETIRED_MARKUP_TOKENS = (
    "theme-carousel", "frame-colours", "colour_usage", "usage-panel",
    "__dots", "theme-chip-grid--strip",
)


def aspect_usage_row_bounds(rendered, usage):
    """The `[start, end)` slice of `rendered` covering exactly one Aspect
    accordion row (its own `<details ... data-usage="{usage}">` through
    the next row's opening tag, or — for the last row in
    `config_page.COLOUR_USAGES` — through the "What it watches"
    supersection's own id-anchored heading, which always renders
    unconditionally right after the Aspect card (and its sibling calendar
    disconnect form, when present) on the Display scope every caller
    below renders through. 30-05-PLAN.md Task 1 (CFG-85): a shared helper
    so every row-scoped check locates a row the same way, exactly once.

    30-06-PLAN.md Task 3: the last-row fallback is REPOINTED. It used to
    search for the separate Calendar card's own nested-wrapper `<div
    class="page-section page-section--nested" ...>` — that card is
    retired outright (its connection block is now INSIDE this same
    Aspect card's own Calendar row), so nothing on the page matches that
    literal any more; worse, every OTHER Display-scope card (Runway,
    Quiet hours) is wrapped with the `theme-status`/`theme-status--nested`
    base class, never `page-section`, so that literal was never a safe
    "next card" anchor even coincidentally. `DISPLAY_WATCHES_SECTION_ID`
    is a landmark id every caller's own `config_page.render(...,
    scope=config_page.SCOPE_DISPLAY)` render always carries, regardless
    of whether Runway itself is present.
    """
    usages = list(config_page.COLOUR_USAGES)
    idx = usages.index(usage)
    start = rendered.index('data-usage="%s"' % usage)
    if idx + 1 < len(usages):
        end = rendered.index('data-usage="%s"' % usages[idx + 1], start)
    else:
        end = rendered.index('id="%s"' % config_page.DISPLAY_WATCHES_SECTION_ID, start)
    return start, end


def rules_row_segment(rendered):
    """The rules row's own segment of `rendered` (see
    `aspect_usage_row_bounds()`). 30-05-PLAN.md Task 2 (CFG-85): renamed
    from `_rules_panel_segment()` — the retired
    `COLOUR_USAGE_PANEL_TARGET_ATTR` locator is replaced by the rules
    row's own `data-usage` attribute, the same attribute
    `theme-preview.js`'s `openRow()`/`departuresRow()` already key off
    (30-04-PLAN.md Task 3).
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
