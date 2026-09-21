"""companion/pages/config_page.py — CFG-01 (theme picker), CFG-12 (runway
picker), and CFG-07's "Trigger poll now" control (06-CONTEXT.md).

Both `render()` and `handle_post()` are real and live as of this plan
(06-07): the Theme and Runway fieldsets render from `server.device_config`'s
own registries with the current values pre-selected, and a POST validates
both fields against those same registries — server-side — before ever
calling `device_config.save_device_config()`. The "Trigger poll now"
control below is unrelated plumbing owned by companion/app.py (plan
06-05): its POST /poll-now target, cooldown gate, and in-process
server.poll_loop.run_once() call all live there, not here — this module
only renders the button/copy for it.
"""
import collections  # 25-04-PLAN.md Task 1 (CFG-48): QuietWindowSpan, the
# named triple the quiet dial's duration text and its drawn sweep are
# BOTH read off, so the words and the picture cannot disagree.
import re
from datetime import timedelta  # 25-05-PLAN.md Task 1 (CFG-49): the
# battery sentence's own look-back window, the same shape health_page's
# _cutoff_iso() uses for the identical read.
from urllib.parse import urlsplit

from companion import i18n  # D-05, 20-07-PLAN.md Task 1: the Display page's
# three supersection headings/intros render through i18n.t() (Task 3
# widens this to every user-visible string in this file).
from companion import theme_preview
from companion import battery  # 25-05-PLAN.md Task 1 (CFG-49): the ONE
# battery estimator (references/data-density.md's two-allow-listed-homes
# rule). Imported as a MODULE and called qualified — a bare
# `from companion.battery import battery_life_estimate` would make the
# estimate read as this page's own, which is the drift 19-01 created
# that module to prevent.
from companion import draw  # 25-04-PLAN.md Task 2 (CFG-48): the shared
# SVG geometry/emission primitives the quiet-hours dial's shapes come
# from (27-05-PLAN.md Task 2, CFG-66, retired the runway map's own use
# of this import). stdlib-only by its own contract, so importing it
# here adds no dependency edge this module did not already have.
from companion.layout import escape_html
import companion.layout as layout
from companion import frame_state  # 22-05-PLAN.md Task 2 (D-04): the one
# frame-state resolution and the one delay sentence — the Frame strip
# (companion/layout.py, 22-04-PLAN.md) and this module's own Quiet hours
# caption both read frame_state.delay_sentence_template() from the SAME
# wake.next_wake_status() triple, so the two can never disagree.
from companion import prefs  # 22-10-PLAN.md Task 2 (B14): the resolved
# site language, set as `lang` on both native time inputs.
from companion import screens
from companion import wake
# 20-07-PLAN.md Task 3 (D-36): the former EDIT_QUERY_PARAM import (19-12-
# PLAN.md Task 2's Device-page "Edit artwork" link) is gone along with
# that link itself — 20-10 renders the replacement "Change pictures"
# button directly on airlines_page.py, which already owns
# EDIT_QUERY_PARAM; nothing here needs it any more.
#
# 20-09-PLAN.md Task 3 (D-15c): the former DELETE_BUTTON_TEXT import
# (airlines_page.py's "Delete") is gone too — the rebuilt rule row's own
# Remove button carries its own distinct copy (RULE_REMOVE_BUTTON_TEXT
# below), matching the UI-SPEC copy table's own "Remove"/"Retirer"
# wording rather than reusing the airlines gallery's "Delete".
#
# 20-09-PLAN.md Task 1 (D-15e): history_db.recent_runway_events() is the
# same call home_page._recent_flights() already makes (companion/pages/
# __init__.py forbids importing that page module directly, so this is a
# second, independent import of the same shared server-side helper, not
# a page-to-page import).
from server import device_config, history_db, panel_format
from server.plane import calendar_rules, colour_rules

# The single definition of this route prefix in the repository (06.4).
# companion/app.py rebinds it (RUNWAY_IMAGE_ROUTE_PREFIX =
# config_page.RUNWAY_IMAGE_ROUTE_PREFIX) rather than re-typing the
# literal, exactly as it already does for the FLASH_KEY_* constants —
# app.py imports this module, so the reverse import would be a cycle.
RUNWAY_IMAGE_ROUTE_PREFIX = "/runway-image/"
RUNWAY_IMAGE_ALT_TEMPLATE = "Airport diagram for %s"

# 06.6.4.1.1-05: same one-definition-site discipline as
# RUNWAY_IMAGE_ROUTE_PREFIX above, with the definition site inverted —
# the mechanism module (companion/theme_preview.py) owns the prefix and
# alt-text template here, not this emitter module, because both this
# module and companion/app.py need to rebind the same constant. The
# literal is still typed exactly once in the repository, in
# theme_preview.py.
THEME_PREVIEW_ROUTE_PREFIX = theme_preview.THEME_PREVIEW_ROUTE_PREFIX
THEME_PREVIEW_ALT_TEMPLATE = theme_preview.THEME_PREVIEW_ALT_TEMPLATE

# 20-11-PLAN.md Task 2 (D-22..D-24, 20-UI-SPEC.md Section Anatomy H/copy
# table E): the live preview's own alt text and caption strings, and its
# `<img>` width/height — taken from the render pipeline's real served
# dimensions (theme_preview.THEME_PREVIEW_SIZE), never a CSS
# `aspect-ratio` guess (matching the chip grid's own UIR-07-informed
# discipline). The live preview shares the identical crop/size the chip
# grid's own `<img>` uses — only the rendered SCENE differs (the last
# real runway event instead of the fixed fixture).
THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT = theme_preview.THEME_PREVIEW_SIZE
THEME_LIVE_PREVIEW_ALT_TEMPLATE = "Live preview of the %s theme"
THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE = "Preview with your last flight: %s"
THEME_LIVE_PREVIEW_CAPTION_SAMPLE = "Preview with a sample flight"

# The single definition of this route in the repository (06.6.4.1, D-05/
# D-26). companion/app.py rebinds its own SETTINGS_ROUTE constant to this
# value rather than re-typing the literal (06.6.4.1-07), mirroring
# RUNWAY_IMAGE_ROUTE_PREFIX's own rebinding discipline above — app.py
# imports this module, so the reverse import would be a cycle. The old
# "/config" path is retired: it 404s by design, no redirect (D-26).
SETTINGS_ROUTE = "/settings"

# quick task 260901-re6: this value is interpolated twice — once as the
# settings <form>'s id, once as the dirty-bar save button's form
# attribute — and the two must never be re-typed as literals, because a
# mismatch produces a Save button that looks correct in markup and
# silently submits nothing. Same one-definition-site discipline as
# RUNWAY_IMAGE_ROUTE_PREFIX/SETTINGS_ROUTE above.
SETTINGS_FORM_ID = "settings-form"

# --- Phase 18 (companion audit / UX refactor): page scopes -------------
#
# The one settings form used to render every group on a single
# "/settings" page. It now renders as two pages sharing the same POST
# route and the same handle_post(): the everyday "Display" page (theme,
# quiet hours, screen on/off) and the advanced "Device" page (runway,
# diagnostic LED, wake interval, calendar, colour rules, manual
# refresh). Which groups land on which page is declared per screen type
# in companion/screens.py, not hard-coded here.
#
# `render(ctx)` with no scope keeps rendering the whole legacy page —
# every group, in the historical order — so existing harness checks
# against the full form stay meaningful. companion/app.py never uses
# that scope for a live route any more.
SCOPE_ALL = "all"
SCOPE_DISPLAY = "display"
SCOPE_DEVICE = "device"
SCOPES = (SCOPE_ALL, SCOPE_DISPLAY, SCOPE_DEVICE)

# Hidden form fields a scoped page submits so handle_post() knows which
# groups were on the page (absent checkbox => "leave unchanged" for a
# group that was never rendered, never "switch it off") and where to
# redirect back to.
SCOPE_FIELD_NAME = "scope"
RETURN_TO_FIELD_NAME = "return_to"

DISPLAY_PAGE_TITLE = "Display"
# 20-07-PLAN.md Task 1 (D-12): the Display page now carries every
# everyday group (Look/What it watches/When it is on), so its purpose
# sentence widens from "how the frame looks" to the whole page's scope.
DISPLAY_PAGE_PURPOSE = "Everything about what the frame shows and when."
DEVICE_PAGE_TITLE = "Device"
DEVICE_PAGE_PURPOSE = (
    "Hardware, data and diagnostics for the frame. Nothing here needs "
    "changing day to day.")
SCREEN_CAPTION_TEMPLATE = "Screen: %s"

# 20-07-PLAN.md Task 1 (D-12, 20-UI-SPEC.md Section Anatomy C): the
# three headed supersections Display's own groups render under, in this
# locked order. Each heading/intro pair is rendered through the shared
# section-intro helper layout.py promoted from health_page.py's own
# former private copy (20-03-PLAN.md).
DISPLAY_LOOK_SECTION_ID = "display-look"
DISPLAY_LOOK_HEADING = "Look"
DISPLAY_LOOK_INTRO = (
    "— the theme, flight colours and calendar that decide how the "
    "picture looks.")
DISPLAY_WATCHES_SECTION_ID = "display-watches"
DISPLAY_WATCHES_HEADING = "What it watches"
DISPLAY_WATCHES_INTRO = "— which Orly runway the frame is watching."
DISPLAY_ON_SECTION_ID = "display-on"
DISPLAY_ON_HEADING = "When it is on"
DISPLAY_ON_INTRO = "— when the screen is lit and when it stays quiet."
# 28-04-PLAN.md Task 1 (CFG-72): Device's own two supersections, the same
# `section_intro_html()` shape as the three above — "When it wakes" over
# Wake interval alone, "How it tells you" over Diagnostic LED and
# Notifications together. The LED/Notifications pairing is a real shared
# subject, not a bucket invented so a wrapper class would have somewhere
# to live: both cards are the frame's SIGNALLING channels — the LED
# reports what the device is doing on the device itself, notifications
# report it on the reader's phone. A third supersection, "When you
# can't wait", introduces the fourth Device card (Manual refresh / Poll,
# built outside `builders` entirely — see `poll_section_html` below) on
# its own: it is the one Device control that acts immediately rather
# than on a schedule, the manual counterpart to "When it wakes", and a
# one-card supersection has precedent in "What it watches" above.
DEVICE_WAKES_SECTION_ID = "device-wakes"
DEVICE_WAKES_HEADING = "When it wakes"
DEVICE_WAKES_INTRO = "— how often the frame wakes up to fetch a new picture."
DEVICE_TELLS_SECTION_ID = "device-tells"
DEVICE_TELLS_HEADING = "How it tells you"
DEVICE_TELLS_INTRO = "— the light on the frame and the alerts on your phone."
DEVICE_POLL_SECTION_ID = "device-poll"
DEVICE_POLL_HEADING = "When you can't wait"
DEVICE_POLL_INTRO = (
    "— fetch a new picture right now instead of waiting for the next "
    "wake.")
# 19-12-PLAN.md Task 2 (D-23): the conditional screen-type <select> — an
# element id (not a class) because its own <label> targets it via `for`.
SCREEN_SELECTOR_ID = "screen-id-selector"
SCREEN_SELECTOR_LABEL_TEXT = "Screen type"

# 21-05-PLAN.md Task 1 (D-06..D-12, 21-UI-SPEC.md §D): the "Frame
# colours" card that replaces the four separate theme chip grids
# (departures/arrivals/calendar/rules) with one live preview plus a
# four-row `colour_usage` assignment radiogroup and four usage panels.
# The usage values below are this card's own radiogroup values — a
# purely client-side/display concern, never submitted to handle_post()
# (no `form=` attribute on the colour_usage radios themselves) and
# entirely distinct from the three underlying SAVED field names
# (theme/theme_arriving/calendar_theme_id) each usage's own chip grid
# still posts through via `form="settings-form"`.
FRAME_COLOURS_HEADING = "Frame colours"
FRAME_COLOURS_HEADING_ID = "frame-colours-heading"
FRAME_COLOURS_CAPTION = (
    "Choose the colour theme for departures, arrivals, calendar "
    "flights and your own rules.")
COLOUR_USAGE_FIELD_NAME = "colour_usage"
COLOUR_USAGE_DEPARTURES = "departures"
COLOUR_USAGE_ARRIVALS = "arrivals"
COLOUR_USAGE_CALENDAR = "calendar"
COLOUR_USAGE_RULES = "rules"
# Locked order (D-07) — every row-building loop below walks this exact
# tuple, so the row order and the no-JS floor's stacked-panel order can
# never drift apart.
COLOUR_USAGES = (
    COLOUR_USAGE_DEPARTURES, COLOUR_USAGE_ARRIVALS, COLOUR_USAGE_CALENDAR,
    COLOUR_USAGE_RULES)
FRAME_COLOURS_ROW_LABELS = {
    COLOUR_USAGE_DEPARTURES: "Departures",
    COLOUR_USAGE_ARRIVALS: "Arrivals",
    COLOUR_USAGE_CALENDAR: "Calendar flights",
    COLOUR_USAGE_RULES: "Per-flight rules",
}
# 22-10-PLAN.md Task 1 (X6): the one-line legend that names every chip's
# two `.theme-chip__dot` swatches, rendered ONCE UNDER each grid rather
# than once per chip — 22-AUDIT.md X6's "two unexplained square swatches
# per chip/row" is a naming defect, not a density one, so the fix is a
# single line of text, not eighteen.
#
# COPY DEVIATION, recorded here rather than in a commit message so it
# survives: 22-UI-SPEC.md §2's X6 row prescribes the literal copy
# "Background · Ink" / "Fond · Encre". That copy names the wrong two
# values. The dots are `_palette_hex(theme["departing_index"])` and
# `_palette_hex(theme["arriving_index"])` — the ink a theme paints a
# DEPARTURE and an ARRIVAL in. A theme's background is not drawn as a
# dot at all, and its `ink_index` (a real, separate THEMES key) is not
# either. Shipping the spec's copy would have replaced two unexplained
# swatches with two mislabelled ones, which is a worse defect than the
# one X6 reports. The words chosen instead are the usage panels' own
# labels above, so the legend and the panel a user is looking at name
# the same two things.
#
# 27-07-PLAN.md Task 3 (CFG-70): "Departures · Arrivals" — a middle dot
# between the two words, the SAME separator the disclosure elsewhere on
# this card would use to name two genuinely different things — reads as
# a promise that the two dots are two different colours. They are not:
# every one of the eighteen themes has `departing_index ==
# arriving_index` (measured while writing `_theme_carousel_html()`,
# 25-06-PLAN.md Task 2, and unchanged since), so the two dots are always
# the same ink. A middle-dot legend over two identical swatches is X6's
# OWN "unexplained swatches" defect wearing different words: it now
# explains a distinction the registry does not carry. The copy is
# joined into ONE phrase instead — no separator, naming what the single
# shared colour is FOR rather than implying two colours to tell apart.
# `companion/test_config_page.py`'s own check computes the expected
# label count FROM THE REGISTRY at check time (never a restated
# literal), so if a future theme ever does give departures and arrivals
# different inks, that check starts demanding two labels again and
# fails against this one-phrase copy until it is split back apart.
THEME_CHIP_SWATCH_LEGEND = "Departures & arrivals"
# 22-10-PLAN.md Task 1 (T10/B16/D-06): the "Current" badge's own text.
# It used to be a hard-coded English `content: "Current"` literal inside
# companion/static/style.css (twice), which no catalogue can reach; it is
# now server-rendered onto the saved chip/card as `data-current-label`
# and read back by `content: attr(data-current-label)`. The pseudo-element
# itself is unchanged — see that rule's own four-point justification for
# why this is not a <span>.
CURRENT_BADGE_LABEL = "Current"
# The attribute the badge's `content: attr(...)` reads. Written as
# literal text at both the markup site below and in style.css, matching
# this file's established convention for a cross-file attribute contract
# (see CALENDAR_DISCONNECT_FORM_ID's own comment) — the constant exists
# so test_config_page.py can reference the name without retyping it.
CURRENT_BADGE_ATTR = "data-current-label"

# --- 25-06-PLAN.md Task 2/3 (CFG-50): D5's theme carousel -------------
#
# 27-07-PLAN.md Task 2 (CFG-68): the DEPARTURES chip grid was, until
# this plan, the only one presented as a horizontal scroll-snap strip.
# Arrivals and calendar now fold the same way — the brief names exactly
# "arrivals, departures, calendar flights" — leaving only the rule-add
# form's own grid deliberately untouched (it lives inside the "règles
# par vol" view the brief explicitly defers). See
# `_theme_chip_grid_html()`'s own docstring for the full reasoning and
# the rule-add form's own call site for the recorded ground.
#
# `theme-carousel-strip` is both the DEPARTURES strip's `id` (so the two
# pagers' `aria-controls` names something real) and the element
# `companion/static/theme-preview.js` scrolls — the script resolves it
# through the button's OWN `aria-controls`, so the accessibility
# contract and the script contract are one contract rather than two that
# can drift apart. Arrivals and calendar carry their OWN ids below,
# derived from the SAME `COLOUR_USAGE_*` constants that already
# distinguish these usages elsewhere on this card, rather than three
# invented literals — see `_theme_carousel_html()`'s own docstring
# (Task 1) for why a shared id is exactly the trap this had to avoid.
THEME_CAROUSEL_STRIP_ID = "theme-carousel-strip"
# 27-07-PLAN.md Task 2 (CFG-68): two more strip ids, one per usage this
# plan folds into a carousel. Departures keeps its own bare
# THEME_CAROUSEL_STRIP_ID above unchanged — it predates this plan and
# nothing depends on it changing — these two are purely additive.
THEME_CAROUSEL_STRIP_ID_ARRIVALS = THEME_CAROUSEL_STRIP_ID + "-" + COLOUR_USAGE_ARRIVALS
THEME_CAROUSEL_STRIP_ID_CALENDAR = THEME_CAROUSEL_STRIP_ID + "-" + COLOUR_USAGE_CALENDAR
# The gated wrapper's own attribute, and the one
# companion/test_companion_app.py's `_NO_JS_CONTROL_REGISTRY` names for
# this control. It is on the WRAPPER only, never on a button — that
# registry asserts that EVERY element carrying it also carries the
# `.js` gate class, which is the whole point of it.
THEME_CAROUSEL_WRAPPER_ATTR = "data-theme-carousel"
# Each pager's own direction, read by theme-preview.js. A separate name
# rather than a value of the wrapper attribute above, so neither scan
# can ever match the other by prefix.
THEME_CAROUSEL_PAGER_ATTR = "data-theme-pager"
THEME_CAROUSEL_PAGER_PREV = "prev"
THEME_CAROUSEL_PAGER_NEXT = "next"
THEME_CAROUSEL_SUMMARY = "See all themes"
# The disclosure's own body, and it says the one thing a reader of this
# control most needs to know: NOTHING IS HIDDEN BEHIND IT. See
# `_theme_carousel_html()` for why this disclosure governs the layout of
# the grid that follows it instead of containing a second copy of it.
THEME_CAROUSEL_DISCLOSURE_BODY_TEMPLATE = (
    "Opening this lays all %d themes out at once. They are all in the "
    "strip either way — it scrolls, and the arrow keys move through it.")
THEME_CAROUSEL_PREV_LABEL = "Previous theme"
THEME_CAROUSEL_NEXT_LABEL = "Next theme"
# The attribute-as-CSS-hook/JS-hook contract theme-preview.js (Task 3)
# reads: each row's own radio names which usage panel it selects, and
# each panel carries the matching target.
COLOUR_USAGE_PANEL_ATTR = "data-usage-panel"
COLOUR_USAGE_PANEL_TARGET_ATTR = "data-usage-panel-target"
# D-09/R-07: the leading "Same as departures" chip Arrivals/Calendar's
# own grids gain, submitting the empty string (the clear signal
# handle_post() now maps to device_config.CLEAR_THEME_ARRIVING/None,
# Task 2) — reused verbatim as both the chip's own label and the row's
# own "no override" meta text (21-UI-SPEC.md §D copy table).
SAME_AS_DEPARTURES_LABEL = "Same as departures"
# D-07: the rules row's own meta text — singular/plural/empty, mirroring
# this file's own %d-template convention elsewhere (e.g.
# POLL_COOLDOWN_HELPER_TEXT's "{n}" — this one uses a plain %d instead,
# matching 21-UI-SPEC.md's own copy table literally).
FRAME_COLOURS_RULES_COUNT_SINGULAR = "1 rule"
FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE = "%d rules"
FRAME_COLOURS_RULES_EMPTY_META = "No rules yet"
# 20-07-PLAN.md Task 3 (D-36): the Device page's own artwork-editing
# link and its former builder function are deleted outright — the
# developer did not understand it. See airlines_page.py, where 20-10
# renders the replacement "Change pictures" button at the top of the
# gallery instead.


def scope_groups(scope, screen_id=None):
    """The ordered tuple of settings-group ids the given scope renders
    for the given screen type. SCOPE_ALL preserves the historical
    single-page order; the two live scopes read the screen type's own
    declaration in companion/screens.py.
    """
    screen = screens.screen_type(screen_id)
    if scope == SCOPE_DISPLAY:
        return tuple(screen["everyday_groups"])
    if scope == SCOPE_DEVICE:
        return tuple(screen["advanced_groups"])
    # 20-11-PLAN.md Task 1 (D-26): screens.GROUP_NOTIFICATIONS joins this
    # legacy tuple too — every registered group must appear somewhere in
    # SCOPE_ALL's fixed order, since render()/handle_post()'s own tests
    # pin the invariant that the two live scopes' groups are disjoint and
    # their union equals this tuple's own set exactly.
    #
    # 22-05-PLAN.md Task 1 (D-12.2): screens.GROUP_DISPLAY is removed from
    # this hand-maintained tuple in the SAME commit that removes it from
    # companion/screens.py's own registry — leaving it here even one
    # commit longer would fail the pinned
    # _scope_groups_follow_the_screen_registry union invariant
    # immediately, which is the point of that check.
    return (
        screens.GROUP_THEME, screens.GROUP_RUNWAY, screens.GROUP_LED,
        screens.GROUP_QUIET_HOURS, screens.GROUP_WAKE_INTERVAL,
        screens.GROUP_CALENDAR, screens.GROUP_NOTIFICATIONS)


def submitted_scope(form):
    """The scope a submitted settings form was rendered with — SCOPE_ALL
    when the field is absent (the legacy single-page form) or carries
    anything outside SCOPES (a crafted value degrades to the widest,
    most conservative reading rather than being rejected: every group's
    own validation still runs).
    """
    value = form.get(SCOPE_FIELD_NAME)
    return value if value in SCOPES else SCOPE_ALL


def submitted_return_route(form):
    """Where a settings POST redirects back to: the page it came from,
    validated byte-for-byte against the two scoped page routes, else
    the Display page. Never a raw form value.
    """
    value = form.get(RETURN_TO_FIELD_NAME)
    if value in (layout.DISPLAY_ROUTE, layout.DEVICE_ROUTE):
        return value
    return layout.DISPLAY_ROUTE

# The sole accepted submitted value for the LED checkbox (D-01) — shared
# by led_group()'s markup and handle_post()'s validator so the two can
# never drift apart.
LED_CHECKBOX_VALUE = "on"

# The sole accepted submitted value for the Quiet hours enable checkbox
# (10-05-PLAN.md), mirroring LED_CHECKBOX_VALUE's own rationale exactly:
# shared by quiet_hours_group()'s markup and handle_post()'s validator so
# the two can never drift apart.
QUIET_HOURS_CHECKBOX_VALUE = "on"

# The sole accepted submitted value for the Display enable checkbox
# (12-UI-SPEC.md), mirroring LED_CHECKBOX_VALUE's/QUIET_HOURS_CHECKBOX_VALUE's
# own rationale exactly: shared by display_group()'s markup and
# handle_post()'s validator so the two can never drift apart.
DISPLAY_CHECKBOX_VALUE = "on"

# 21-05-PLAN.md Task 1 (D-06..D-12): the arrivals-theme-override
# checkbox and its five own constants (the checkbox's accepted
# submitted value, its toggle element id, the revealed grid's own CSS
# hook, its locked label copy, and the direction label above that
# grid) are all retired outright — D-09 replaces the whole apparatus
# with a "Same as departures" leading chip inside the Frame colours
# card's arrivals usage panel, which submits the empty string instead
# of gating a second grid's visibility behind a checkbox. See
# _frame_colours_card_html() below.

# quick task 260901-re6: each settings group used to render a description
# sentence above its control (THEME_SECTION_DESCRIPTION/
# RUNWAY_SECTION_DESCRIPTION, D-02 06.6.4.1) AND a helper sentence below
# it (THEME_HELPER_TEXT/RUNWAY_HELPER_TEXT/LED_HELPER_TEXT) — Theme and
# Runway rendered both, LED escaped the doubling but kept its lone
# paragraph un-muted and positioned after its control instead of before.
# All five of those constants are retired outright. Each group now
# carries exactly one caption, rendered once, directly under the group
# heading and before the control, styled as a single muted sentence via
# a CSS modifier class in companion/static/style.css. The LED group is
# the odd one out only in that it never had a pair to merge — its single
# paragraph is reworded and relocated, not merged with anything.
#
# quick task 260901-s5o: a fourth caption, POLL_SECTION_CAPTION, joins
# the three above. Poll was never part of the description/helper merge
# those three came out of — it is a `<section class="page-section">`,
# not a `.theme-status` group, and had no paragraph of its own to merge.
# It was simply skipped, leaving the page's fourth section as the only
# one with a bare heading. This caption is new copy, validated against
# the Settings Save Bar Sketch, not merged from anything. Unlike the
# other three, it is consumed by a two-branch renderer
# (poll_trigger_section()), so it must be interpolated on both branches
# or it would silently vanish for the whole cooldown window.
# Quick task 260921-n2n Task 3: the developer's 2026-09-21 tour quoted
# this caption as his example of useless descriptive text. Phase 27's
# CFG-66 removed the runway diagram outright, but this caption still
# described it — the two schematic-drawing clauses a prior revision
# added here (see git history for the exact wording, deliberately not
# quoted again) had been describing a picture that no longer exists
# since CFG-66 shipped. The one-caption-per-section rule above still
# holds: this stays ONE caption, shortened in place rather than
# replaced by a second paragraph. What survives is the three facts
# that were always true independent of any drawing — which runway,
# and that the change applies on the next scheduled poll, not
# immediately — which is also why this caption now reads consistently
# with LED_SECTION_CAPTION below it, which ends on that identical
# clause.
RUNWAY_SECTION_CAPTION = (
    "Which Orly runway the device watches. Applies on the next "
    "scheduled poll, not immediately.")
LED_SECTION_CAPTION = (
    "Lit only during the device's brief wake window, not visible from "
    "the wall side. Applies on the next scheduled poll.")

# 19-11-PLAN.md Task 3 (D-12/A-30): stable DOM ids for the group headings
# a radiogroup's aria-labelledby points at, and for each hint paragraph
# an aria-describedby points at — constants here, never a literal at a
# render site, matching this file's own convention (see e.g.
# RUNWAY_IMAGE_ROUTE_PREFIX above). Only the groups that actually gain
# `role="radiogroup"` (the two theme chip grids and the runway row) get
# a *_GROUP_HEADING_ID; every hint below gets a *_CAPTION_ID/*_HINT_ID
# regardless, since a hint can describe a single-control field too (a
# checkbox, a time/number input, a <select>) with no radiogroup at all.
RUNWAY_SECTION_CAPTION_ID = "runway-caption"
RUNWAY_GROUP_HEADING_ID = "runway-group-heading"
LED_SECTION_CAPTION_ID = "led-caption"
POLL_SECTION_HEADING = "Manual refresh"
POLL_SECTION_CAPTION = (
    "Manually trigger an immediate poll cycle instead of waiting for "
    "the next scheduled one.")
# D-05 (06.6.4.1): the LED group's new user-facing heading, once it moves
# from its own <fieldset>/<legend> into a sibling <h2>-headed group of
# the merged form — see led_group() below.
LED_SECTION_HEADING = "Diagnostic LED"

# 10-05-PLAN.md / 10-UI-SPEC.md Copywriting Contract, superseded by
# 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the "could now be hours away"
# duration caveat this caption used to restate directly is retired along
# with its own on/off checkbox below - the Frame strip is now the ONLY
# on/off control, so this caption states enable-by-schedule semantics
# instead (the schedule below is what the strip's switch turns on and
# off). 22-05-PLAN.md Task 2 appends the one computed delay sentence
# (companion/frame_state.py) as this caption's second sentence, replacing
# the retired "which may now be hours away" wording with a real, computed
# time rather than a fixed literal.
QUIET_HOURS_SECTION_HEADING = "Quiet hours"
# 27-06-PLAN.md Task 3 (CFG-67): shortened from 27-01-SUMMARY.md's
# measured 188-char baseline (this caption plus its own computed delay
# sentence, appended at render time by quiet_hours_group() — see that
# function's own caption_html construction below, unchanged). The cut
# is scoped to THIS explanatory sentence alone: "— the Frame strip's
# Quiet hours switch is what turns it on and off" (the mechanism
# clause) is dropped; "Pauses the frame's wake, poll and display cycle
# during the schedule below" (what the schedule DOES) is kept, and the
# appended delay sentence — computed state, not explanation — is
# untouched by this edit entirely.
QUIET_HOURS_SECTION_CAPTION = (
    "Pauses the frame's wake, poll and display cycle during the "
    "schedule below.")
# 19-11-PLAN.md Task 3 (D-12/A-30): see THEME_SECTION_CAPTION_ID's own
# comment above.
QUIET_HOURS_SECTION_CAPTION_ID = "quiet-hours-caption"
# 27-08-PLAN.md Task 1 (CFG-69): the card's own heading id, the same
# "id on the group's <h2>" convention RUNWAY_GROUP_HEADING_ID already
# uses (runway_group() below) — added here because nothing on this card
# carried a stable id before this task. `DIRTY_SECTION_ATTR` (still
# emitted on this same card's wrapper) is not it: that is a `data-*`
# attribute 27-04 left in place for reasons unrelated to navigation, and
# a `data-*` attribute is not a fragment an `<a href="#...">` can ever
# resolve to. This is the Frame strip's own link target (companion/
# layout.py's frame_strip_html(), 27-08 Task 2) — a fragment identifier
# naming the card a reader is sent to, not a new control and not a
# change to anything that posts.
QUIET_HOURS_GROUP_HEADING_ID = "quiet-hours-group-heading"

# 22-05-PLAN.md Task 2 (D-04): scanner-visibility copies of two of
# companion/frame_state.py's three delay-sentence constants — byte-
# identical to frame_state.DELAY_DUE/DELAY_HELD, matching companion/
# layout.py's own 22-04-PLAN.md Task 1 precedent exactly (that module's
# own docstring/summary calls this pattern out by name). The D-05 AST
# i18n completeness scan (companion/test_i18n.py) can trace a same-file
# top-level scalar used directly as an i18n.t() argument, but not an
# imported module's attribute access read through a local variable —
# render()'s own `quiet_hours_delay_template` is exactly such a local
# variable. The DECISION (which of the three branches applies) still
# comes from frame_state.delay_sentence_template() alone; only the
# wording's scanner-visible home is local. frame_state.DELAY_UNKNOWN
# needs no copy here: companion/layout.py's own
# `_FRAME_DELAY_UNKNOWN_TEXT` alias already makes that one key scanner-
# visible (22-04-PLAN.md), so a second copy here would only duplicate,
# never newly "produce", the same CATALOG key.
_QUIET_HOURS_DELAY_DUE_TEXT = "Applies at the next wake, around %s."
_QUIET_HOURS_DELAY_HELD_TEXT = "Applies when quiet hours end, around %s."

# 19-10-PLAN.md (D-14/S-04): three one-tap presets, client-side only - no
# server change (see quiet_hours_group()'s docstring). The Night preset's
# start/end are sourced from server.device_config's own shipped defaults
# rather than retyped literals, so the preset and the default can never
# drift apart. Ranges use a real U+2013 en dash, matching this module's
# real-Unicode punctuation convention (see its em dashes elsewhere).
QUIET_HOURS_PRESET_NIGHT_START = device_config.DEFAULT_QUIET_HOURS_START
QUIET_HOURS_PRESET_NIGHT_END = device_config.DEFAULT_QUIET_HOURS_END
# 20-07-PLAN.md Task 3 (D-05): the %s-templated form, translated through
# i18n.t() BEFORE substitution (this codebase's established pattern,
# health_page.py's SOURCE_FAULT_BODY_TEMPLATE, 20-03-PLAN.md) — never an
# already-formatted string translated as one opaque catalogue key, which
# would bake this specific device's own configured times into the
# French entry forever.
QUIET_HOURS_PRESET_NIGHT_LABEL_TEMPLATE = "Night (%s–%s)"
QUIET_HOURS_PRESET_NIGHT_LABEL = QUIET_HOURS_PRESET_NIGHT_LABEL_TEMPLATE % (
    QUIET_HOURS_PRESET_NIGHT_START, QUIET_HOURS_PRESET_NIGHT_END)
QUIET_HOURS_PRESET_WORKDAY_START = "08:00"
QUIET_HOURS_PRESET_WORKDAY_END = "18:00"
QUIET_HOURS_PRESET_WORKDAY_LABEL_TEMPLATE = "Work day (%s–%s)"
QUIET_HOURS_PRESET_WORKDAY_LABEL = QUIET_HOURS_PRESET_WORKDAY_LABEL_TEMPLATE % (
    QUIET_HOURS_PRESET_WORKDAY_START, QUIET_HOURS_PRESET_WORKDAY_END)
# "Always on (off)": this preset UNCHECKS the enable checkbox and leaves
# both times untouched - "off" means the curfew is disabled while the
# configured window stays intact, the pre-configure-before-enabling
# behaviour quiet_hours_group()'s own docstring already locks. Expressed
# via a distinct data-preset-enabled="0" attribute rather than
# overloading the time attributes with a sentinel value.
QUIET_HOURS_PRESET_ALWAYS_ON_LABEL = "Always on (off)"
QUIET_HOURS_PRESET_ATTR = "data-quiet-preset"

# 11-UI-SPEC.md Copywriting Contract, locked verbatim (D-05). The caption's
# closing sentence deliberately reuses the same "Applies on the next
# scheduled poll" clause every sibling caption ends on (D-06 — no new
# apply-timing mechanism exists for this field either). The placeholder is
# a legitimate empty state (D-07: "never explicitly set"), not an error
# state — it names the fallback behavior instead of showing a fabricated
# number.
WAKE_INTERVAL_SECTION_HEADING = "Wake interval"
# 27-06-PLAN.md Task 3 (CFG-67): shortened from 27-01-SUMMARY.md's
# measured 220-char baseline — the mechanism sentence ("How often the
# frame wakes to poll for updates.") and the apply-timing sentence
# ("Applies on the next scheduled poll.") are both cut; the derived
# "(next wake ≈ ...)" suffix _with_next_wake() appends already states
# the apply timing with a real timestamp, making the generic sentence
# redundant. What is kept is the one sentence a reader needs to ACT:
# what a shorter/longer number trades off.
WAKE_INTERVAL_SECTION_CAPTION = (
    "Shorter means fresher info and more battery drain; longer means "
    "more battery life and staler info at a glance.")
WAKE_INTERVAL_PLACEHOLDER_TEXT = "Uses server default"
# 22-10-PLAN.md Task 3 (B17): the unit, rendered as a SIBLING beside the
# number input — never a placeholder (the field already has one, and a
# placeholder vanishes the moment a value is typed) and never text inside
# the control (a number input has no such affordance).
#
# NOT routed through i18n.t(), and the reason is stated rather than
# assumed: "s" is the SI symbol for a second, which is the same symbol in
# French. It is a unit symbol, not prose — the same "data, not
# translated" call RULE_SUGGESTIONS_LABEL's neighbouring separator
# already makes (20-UI-SPEC.md Copywriting Contract §A). Routing it
# through the catalogue would need a FR entry whose value equalled its
# key, which companion/test_i18n.py rejects outright, by design. The
# unit's meaning is carried for assistive technology by the field's own
# label ("Wake interval (seconds)"), which IS translated; this span is
# aria-hidden precisely because that label already says it.
WAKE_INTERVAL_UNIT_LABEL = "s"
# The id the wake-interval label points at, now that the label is its own
# element above the control rather than a wrapper around it (B17).
WAKE_INTERVAL_INPUT_ID = "wake-interval-s"
# 19-11-PLAN.md Task 3 (D-12/A-30): see THEME_SECTION_CAPTION_ID's own
# comment above.
WAKE_INTERVAL_SECTION_CAPTION_ID = "wake-interval-caption"

# --- 25-05-PLAN.md Task 1 (CFG-49): THE TWO GAUGES --------------------
#
# The wake interval is a trade-off the card never showed either side of:
# a smaller number means the frame notices a plane sooner AND that the
# battery empties sooner. These two sentences are those two sides, and
# the interesting thing about them is that ONLY ONE OF THEM CAN BE
# HONEST TODAY.
#
# FRESHNESS is true by construction, as long as it says "at most". The
# frame learns about a plane at its next wake, so a plane that passes
# one instant after a wake shows up one whole interval later and no
# later than that. State it as a BOUND and it is the interval restated
# the way a person experiences it; drop the "at most" and it becomes a
# claim about TYPICAL behaviour, which nothing in this project measures.
#
# BATTERY LIFE cannot state an absolute figure from first principles,
# and this is the constraint the whole card is built around. Computing
# "≈ 38 days remaining" needs a per-wake energy cost, and this project
# has NEVER MEASURED ONE — DEVICE-05's multi-day discharge run is still
# open. A number invented from an assumed cost, printed next to a
# control a person will act on, is exactly the dishonest state Phase 22
# spent a whole phase removing. So the figure here comes out of
# companion/battery.py's `battery_life_estimate()`, which derives it
# from this device's OWN OBSERVED discharge slope or refuses to derive
# it at all — and when it refuses, WAKE_BATTERY_UNKNOWN_TEXT is a real
# rendered state, not a blank.
#
# NO DAYS-REMAINING ARITHMETIC LIVES IN THIS MODULE. Every figure below
# is `battery.battery_life_estimate()`'s own return, called QUALIFIED
# (`references/data-density.md`: a bare `from companion.battery import
# ...` makes the estimator read as the page's own). 19-01 created that
# module to stop exactly this drift.
# The name the form posts this setting under, in ONE place: the number
# input's own `name`, the gauges' `data-value-readout`, the slider's
# `data-value-field` and the no-JS control contract's registry row all
# have to be the same string, and three of those four are attributes a
# string comparison would never catch drifting.
WAKE_INTERVAL_FIELD_NAME = "wake_interval_s"
WAKE_GAUGE_CLASS = "wake-gauge"
WAKE_GAUGE_FRESHNESS_ID = "wake-gauge-freshness"
WAKE_GAUGE_BATTERY_ID = "wake-gauge-battery"
# The gauges speak in minutes; the field holds seconds. One name, so the
# ceiling division below and the scale attribute the script reads are
# provably the same number.
WAKE_GAUGE_SECONDS_PER_MINUTE = 60
# How much history the battery sentence is allowed to look back over.
# Deliberately SHORTER than health_page's own 3-month trend window: this
# sentence says "recent", and a slope measured from a point three months
# and one charge ago is not recent behaviour. Two weeks is comfortably
# more than battery.LIFE_MIN_OBSERVED_SPAN_DAYS and still recent enough
# for the word to be true.
WAKE_BATTERY_WINDOW_DAYS = 14
# THE QUANTITY'S PLACE IS "#", never "%s"/"%d"/"{}" — every template
# below reaches the browser as an ATTRIBUTE VALUE on a rendered page
# (companion/static/value-controls.js substitutes into it live), and
# companion/test_i18n.py's Check 3 scans every French render for a stray
# format artefact. layout.VALUE_CONTROL_TEXT_TOKEN and
# layout.RELATIVE_QUANTITY_MARK both record that lesson; this is the
# third consumer of it, and a check asserts every template here carries
# that exact token.
#
# THE UNIT IS "min" AND THE QUANTITY IS WHOLE MINUTES, which keeps these
# sentences free of a plural form in both languages and free of the
# s/m/h/d ladder: the configured band is 60..3600 s, which is 1..60 min,
# so the unit never changes mid-sweep. layout.duration_text() is the
# app's one ladder and is used below for the ONE fixed cadence that is
# not the field's own value (the screen-off one), where no live update
# has to reproduce it in a second language of source.
# 27-06-PLAN.md Task 3 (CFG-67): shortened from 27-01-SUMMARY.md's
# measured 254-char combined baseline (this template + the battery
# templates below). "at most" is UNCHANGED — it is the whole claim, not
# decoration (WAKE_FRESHNESS_TEXT's own check in test_config_page.py
# pins it) — only the trailing "after it passes" mechanism clause is
# cut in favour of the shorter, equally exact "later".
WAKE_FRESHNESS_TEXT = (
    "A plane reaches the frame at most # min later.")
# The two absolute-figure wordings. Only ever rendered when
# battery.battery_life_estimate() says the OBSERVED history supports a
# figure, and carrying this app's own "≈" honesty marker (the battery
# percentage already wears it) plus the source of the claim, so it can
# never be read as a datasheet number. 27-06-PLAN.md Task 3 (CFG-67):
# "at this interval" is cut (the sentence sits directly beside the
# interval control it is about); "from this frame's own recent
# readings" — the honesty attribution itself — is UNCHANGED.
WAKE_BATTERY_DAY_TEXT = (
    "≈ # day of battery left, from this frame's own recent readings.")
WAKE_BATTERY_DAYS_TEXT = (
    "≈ # days of battery left, from this frame's own recent readings.")
# THE NAMED "NOT ENOUGH HISTORY YET" STATE. A rendered sentence, never a
# blank and never a zero: a card that silently drops the battery half
# whenever it cannot compute one reads as a card that has nothing to say
# about battery at all. 27-06-PLAN.md Task 3 (CFG-67): the trailing
# reason clause ("— this frame has never measured what one wake costs")
# is cut; the refusal itself ("Not enough battery history yet to say
# how long a charge lasts") is UNCHANGED — this is D18's honesty
# contract and this task shortens wording, never conditions.
WAKE_BATTERY_UNKNOWN_TEXT = (
    "Not enough battery history yet to say how long a charge lasts.")
# The clause that keeps BOTH sentences from over-claiming: neither the
# bound nor the battery figure is in force while the screen is off,
# because device_config.DISPLAY_OFF_SLEEP_S is pinned independently of
# this field then (server/wake.py's effective_wake_interval_s(),
# precedence rule 1). A visitor who has turned the screen off would
# otherwise read a claim that does not apply to their frame. 27-06-
# PLAN.md Task 3 (CFG-67): ", whatever this is set to" is cut — "instead"
# already carries the override; the cadence itself stays named.
WAKE_BATTERY_SCREEN_OFF_TEXT = (
    "While the screen is off, the frame wakes every %s instead.")
# The RELATIVE half, and the only half companion/static/value-controls.js
# may recompute while the slider moves. It names TWO CADENCES and no
# ratio: it is arithmetic on the two cadences and nothing else, which is
# the one thing battery.battery_life_estimate()'s `relative_factor`
# docstring is emphatic can be said honestly on day one — and it is
# carefully NOT a multiplier on the lifetime, which those two would only
# be if every joule this device spends went into waking.
#
# "%d" is the SAVED cadence, written in server-side and fixed for the
# life of the page; "#" is the proposed one, which is the only thing
# that moves and therefore the only thing the script substitutes.
WAKE_BATTERY_INSTEAD_TEXT = (
    "This setting wakes the frame every # min instead of every %d min.")

# --- 25-05-PLAN.md Task 2 (CFG-49/CFG-52): the gated range -----------
WAKE_SLIDER_CLASS = "wake-slider"
WAKE_SLIDER_INPUT_CLASS = "wake-slider__input"
# One minute, which is WAKE_INTERVAL_MIN_S itself and the unit both
# gauges speak in — so every position the slider can reach is a whole
# number of minutes and neither sentence ever has to round.
WAKE_SLIDER_STEP_S = 60
# The range's own accessible name. It needs one of its own: the number
# input's label ("Wake interval (seconds)") names THAT control, and two
# controls sharing one accessible name is how a screen-reader visitor
# loses track of which of them they are on.
WAKE_SLIDER_LABEL = "Wake interval slider"

# 20-11-PLAN.md Task 1 (D-26/D-28, 20-UI-SPEC.md Section Anatomy J/copy
# table G): the Notifications group's own copy — a Device-only sixth
# sibling of LED/Wake interval inside <form id="{SETTINGS_FORM_ID}">,
# built against led_group()'s exact fieldset-free idiom.
NOTIFICATIONS_SECTION_HEADING = "Notifications"
NOTIFICATIONS_SECTION_CAPTION = (
    "Get a push alert when the battery runs low or the frame stops "
    "checking in.")
NOTIFICATIONS_SECTION_CAPTION_ID = "notifications-caption"
# D-26 amended (20-CONTEXT.md's Resolutions): write-only, like the
# calendar feed URL — never rendered back, not partially masked. The
# status row reports only whether a URL is stored (T-20-12).
NOTIFICATIONS_STATUS_CONFIGURED_VERDICT = "Configured"
NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT = "Not configured"
NOTIFICATIONS_URL_FIELD_LABEL = "Push topic URL"
NOTIFICATIONS_URL_HINT = (
    "Paste your ntfy.sh topic URL (or a self-hosted one). Stored on "
    "the server and never shown back here — pasting a new one "
    "replaces the old.")
NOTIFICATIONS_URL_HINT_ID = "notifications-url-hint"
NOTIFICATIONS_REPLACE_URL_SUMMARY = "Replace the URL"
# A shape bound against an absurd paste, matching CALENDAR_URL_MAX_LEN's
# own established rationale exactly — the one arbiter of an acceptable
# topic URL stays server/notify.py's send-time _url_is_safe() gate, not
# a second definition here.
NOTIFICATIONS_URL_MAX_LEN = 2048
NOTIFICATIONS_BATTERY_LABEL = "Battery low"
NOTIFICATIONS_SILENT_LABEL = "Frame silent"
NOTIFICATIONS_TEST_BUTTON_TEXT = "Send a test"
# The sole accepted submitted value for each checkbox (D-01), mirroring
# LED_CHECKBOX_VALUE/QUIET_HOURS_CHECKBOX_VALUE/DISPLAY_CHECKBOX_VALUE's
# own rationale exactly: shared by notifications_group()'s markup and
# handle_post()'s validator so the two can never drift apart.
NOTIFICATIONS_BATTERY_CHECKBOX_VALUE = "on"
NOTIFICATIONS_SILENT_CHECKBOX_VALUE = "on"
# companion/app.py rebinds this rather than retyping the literal,
# mirroring CALENDAR_CONNECT_ROUTE's own rebinding convention (app.py
# imports this module, so the reverse import would be a cycle). Unlike
# the calendar Connect route, this one is a pure immediate action with
# no field of its own to validate — see _handle_notifications_test_
# post()'s own docstring in companion/app.py.
NOTIFICATIONS_TEST_ROUTE = "/settings/notifications/test"
ERROR_NOTIFICATIONS_URL_TOO_LONG = "That link is too long."

# 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): DISPLAY_SECTION_HEADING,
# DISPLAY_SECTION_CAPTION and DISPLAY_SECTION_CAPTION_ID (12-UI-SPEC.md's
# former Copywriting Contract, D-02, 12-CONTEXT.md) are retired outright
# along with display_group() below - the Frame strip is now the ONLY
# on/off control for the screen, and its own caption (companion/layout.py,
# 22-04-PLAN.md) is the one place that states when the change lands,
# computed from companion/frame_state.py rather than a fixed "within
# about 5 minutes" literal the audit could not substantiate (22-RESEARCH.md).
# DISPLAY_CHECKBOX_VALUE (above) stays defined: handle_post() still
# validates an explicit legacy/crafted display_enabled value against it.

# 20-07-PLAN.md Task 2 (D-19): the Screen on/off and Quiet hours routes
# the strip's switches still post to. Home's own (module-private, on
# the Home page) route constants are byte-for-byte duplicates, never
# imported (a page module may never import another page module,
# companion/pages/__init__.py's own boundary). The instant-switch
# `<form>`s' own action attributes are written as literal path text,
# not a `%s` interpolation of these constants (this file's own
# acceptance gate greps the literal form-action text) — but the two
# constants stay defined here, equal to those same paths, for
# companion/test_config_page.py's own checks to reference without
# retyping either path a third time.
#
# 21-04-PLAN.md Task 1 (D-01/D-02/R-01): the eleven constants naming
# the switches' own labels/state text/button text, and the markup
# blocks that used to build each switch, both moved out of this
# module entirely — the shared strip helper in companion/layout.py is
# now their one write site, since the Screen/Quiet-hours instant switches render in the
# shared Frame strip at the top of Home and Display, not inside these
# two scheduled-controls cards any more.
QUICK_DISPLAY_ROUTE = "/quick/display"
QUICK_QUIET_HOURS_ROUTE = "/quick/quiet-hours"

# Read elsewhere, not just here — this module's existing
# duplicated-not-imported must-equal discipline (matches
# OPEN_CLASS/MOBILE_NAV_OPEN_CLASS's own precedent): DIRTY_SECTION_ATTR
# is read by companion/static/dirty-state.js (D-32's PLACEHOLDER doc
# comment below explains its current, narrower use), and STATIC_SAVE_
# FALLBACK_ATTR is read by a `.js`-gated rule in companion/static/
# style.css (`.js [data-static-save-fallback] { display: none; }`,
# landed by 06.6.4.1-01). Neither file imports this module — the values
# must be kept equal by hand.
#
# 27-04-PLAN.md (D-06/CFG-63): DIRTY_SECTION_ATTR's own former READER —
# dirty-state.js's dirtySectionLabels(), which built the retired dirty
# bar's "Runway and Quiet hours changed" copy — is deleted along with
# the bar. The attribute itself is left standing, unread by any script
# today: every wrapper below still marks the settings groups a reader
# (sighted or not) can already see as one visual unit, which is true
# independent of whatever save model sits on top, and re-threading every
# one of its seven emission sites to remove it is no part of what this
# plan was asked to change.
#
# SUPERSEDED by 28-08-PLAN.md (CFG-77/CFG-78), 2026-09-16: both
# paragraphs above described a state that held for one phase, not a
# permanent fact — the developer asked for the dirty bar back, twice
# confirmed (ROADMAP.md's Phase 28 addendum, "CFG-63 reversed"), having
# seen real Safari Network tab evidence that the auto-save fetch it
# replaced worked correctly the whole time. DIRTY_SECTION_ATTR's reader
# is restored: dirty-state.js's dirtySectionLabels() is back, and it is
# once again what walks every wrapper below to build the bar's
# section-naming copy. STATIC_SAVE_FALLBACK_ATTR's own reader also
# changes — the `.js`-hide rule this comment names is deleted
# (28-08-PLAN.md Task 2), because the button it used to hide is now the
# restored bar's own visible Save, relocated into the bar's markup below
# with a `form="%s"` attribute rather than hidden by CSS. Both constants
# keep their pre-existing values; only the mechanism reading them moved.
DIRTY_SECTION_ATTR = "data-dirty-section"
STATIC_SAVE_FALLBACK_ATTR = "data-static-save-fallback"

# 28-08-PLAN.md (CFG-77), 2026-09-16: the seven words dirty-state.js's
# updateBar()/dirtySectionLabels() carry as translated data-* attributes
# on the bar itself — restored verbatim (constant names, English values
# and French catalogue entries alike) from their pre-27-04 shape at
# commit 6dea46a, because 27-04 deleted them along with the bar it
# removed and the developer has now asked for that bar back. Same
# data-*-attribute-with-an-English-fallback idiom as quick-switch.js's
# own data-quick-failed-text: each constant's own English value is also
# dirty-state.js's documented `|| "English fallback"` literal, so the
# two can never silently disagree about what a bar rendered WITHOUT the
# attribute says.
#
# DIRTY_BAR_INITIAL_TEXT's ROLE CHANGED from its pre-27-04 shape, and
# this is the plan's most important non-obvious decision, stated here
# too: it is no longer [data-dirty-count]'s server-rendered SEED. The
# bar itself is no longer server-rendered `hidden` (Task 1's no-JS-floor
# inversion — see render()'s own comment at the bar's emission site), so
# seeding the count span with this text would announce a false "Unsaved
# changes" claim, via `role="status"`, to every scripts-blocked visitor
# on every page load before they have touched anything. It is carried
# as a data-* attribute only, for dirty-state.js to write when — and
# only when — countDifferences() actually finds one. A future reader
# re-seeding the span with this constant's own value reintroduces
# exactly the bug this restoration refused to ship.
DIRTY_BAR_INITIAL_TEXT = "Unsaved changes"
DIRTY_CHANGED_SUFFIX = " changed"
DIRTY_AND = " and "
DIRTY_LIST_AND = ", and "
DIRTY_UNSAVED_SINGULAR = "1 unsaved change"
DIRTY_UNSAVED_PLURAL = " unsaved changes"
# 28-08-PLAN.md: this constant's PRODUCER changes back from the
# now-removed auto-save status region's own progress constant to this
# restored name — the English value and the French catalogue entry it
# maps to ("Enregistrement…") are byte-identical, so the move changes
# nothing a reader ever sees.
#
# The ellipsis is the single U+2026 character, matching this module's
# own "Polling…" and layout.py's "Reconnecting…" — never three periods.
DIRTY_SAVING_TEXT = "Saving…"

# 27-04-PLAN.md Task 3 (D-04/D-06/CFG-63): the auto-save status region's
# two translated words, replacing the seven the retired dirty bar used
# to carry (DIRTY_BAR_INITIAL_TEXT, DIRTY_CHANGED_SUFFIX, DIRTY_AND,
# DIRTY_LIST_AND, DIRTY_UNSAVED_SINGULAR, DIRTY_UNSAVED_PLURAL and
# DIRTY_SAVING_TEXT — all deleted with dirty_bar_html() itself). Same
# data-*-attribute-with-an-English-fallback idiom as the bar's own words
# were, and as quick-switch.js's data-quick-failed-text still is: each
# constant's own English value is also dirty-state.js's documented
# fallback literal, so the two can never silently disagree about what a
# region rendered WITHOUT the attribute says.
#
# SUPERSEDES this module's former "There is deliberately no 'Saved'
# counterpart" paragraph (D-04/D-06, pre-27-04): that reasoning held
# only while saving WAS a full-document POST — the region reporting the
# finished state does not exist any more by the time a real navigation
# lands. Saving is no longer a navigation at all (27-04-PLAN.md Task 2's
# fetch-based auto-save); the region that said "Enregistrement…" is
# still the region on screen when the fetch resolves, so it is now the
# right place to say "Enregistré" too, and no second source of truth is
# introduced by doing so — the word is written by the same page that
# already holds the value, from the same response that already confirms
# it landed.
#
# SUPERSEDED IN TURN by 28-08-PLAN.md (CFG-77/CFG-78), 2026-09-16: the
# developer rejected the auto-save MODEL this whole region existed to
# report on, not just its missing feedback — real Safari Network tab
# evidence showed the fetch-based save worked correctly the entire time
# (ROADMAP.md's Phase 28 addendum). Saving is a real navigation again,
# so the region's own premise ("no navigation left to report a finished
# state after") is gone. The region's own attribute constant, its two
# text-word constants, and _save_status_region_html() itself, are
# DELETED — along with the "Saved"/"Enregistré" catalogue entry the
# progress-word constant above was the only producer of.
# "Saving…"/"Enregistrement…" SURVIVES: DIRTY_SAVING_TEXT (above) is its
# new, restored producer — the same constant that
# produced it before 27-04 ever ran, with the identical English value
# and the identical French translation.

# Matches 06-UI-SPEC.md's Copywriting Contract "Poll-trigger cooldown"
# row verbatim (D-17); "{n}" is filled in with a server-computed
# remaining-seconds figure, never anything client-supplied. This text is
# intentionally the *button-adjacent* copy shown while the trigger is
# disabled — a separate rendering site from companion/app.py's own
# FLASH_MESSAGES entry for the same event (the post-redirect flash
# banner), not a shared constant, since a page module must never import
# companion/app.py (that would be a cycle: app.py already imports this
# module).
POLL_COOLDOWN_HELPER_TEXT = "Poll triggered recently — try again in {n}s."

# DOM ids the D-01 live countdown script (companion/static/
# poll-cooldown.js as of 19-04-PLAN.md/D-18) hooks with
# document.getElementById() — shared between poll_trigger_section()'s
# markup and the script so the two can never drift apart.
POLL_TRIGGER_BUTTON_ID = "poll-trigger-btn"
POLL_COOLDOWN_TEXT_ID = "poll-cooldown-text"

# UXA-15: the enabled (zero-cooldown) branch's button label while a
# submit is pending, swapped in by companion/static/poll-cooldown.js
# (19-04-PLAN.md/D-18) via the button's data-submit-pending attribute.
# Cosmetic only — companion/app.py's _POLL_LOCK is the actual
# correctness boundary, this is purely the immediate-feedback
# affordance.
POLL_SUBMIT_PENDING_TEXT = "Polling…"

# The placeholder the client substitutes the live second count into. The
# countdown reuses POLL_COOLDOWN_HELPER_TEXT with this token standing in
# for the "{n}" slot precisely so the ticking copy stays word-identical to
# the static, server-rendered copy above and to companion/app.py's
# FLASH_MESSAGES[FLASH_KEY_POLL_COOLDOWN] post-redirect banner. The copy
# exists in one place (this constant) and is formatted twice — once with
# a real integer for the no-JS render, once with this token for the
# script template — never rewritten or duplicated.
POLL_COOLDOWN_TEMPLATE_TOKEN = "__N__"

# The four flash keys this module's handle_post() can return, defined
# here — the single source of truth companion/app.py's own flash-key
# constants and FLASH_MESSAGES dict reference, per this plan's Task 2
# ("the key strings exist in exactly one place"). Values match
# companion/app.py's pre-existing FLASH_KEY_* string literals exactly, so
# a redirect's ?flash= query parameter round-trips through
# app.py's FLASH_MESSAGES lookup unchanged.
FLASH_SAVED = "saved"
FLASH_SAVE_FAILED = "save_failed"
FLASH_POLL_TRIGGERED = "poll_triggered"
FLASH_POLL_COOLDOWN = "poll_cooldown"
# Distinct from FLASH_SAVE_FAILED (2026-08-28 fix): a run_once() exception
# inside POST /poll-now used to redirect with FLASH_SAVE_FAILED, showing
# "Couldn't save settings" for a failure that has nothing to do with
# saving settings — confusing and actively misleading about what broke.
FLASH_POLL_FAILED = "poll_failed"
# Distinct from FLASH_POLL_COOLDOWN (UXA-15 fix): the cooldown key means
# "wait, you already triggered one recently" (a stale, seconds-old fact
# checked against history_db). This key means "a poll is executing on
# this exact request, right now, in another thread" — companion/app.py's
# non-blocking `_POLL_LOCK.acquire(blocking=False)` failing is the only
# thing that ever produces it, closing the TOCTOU window where two
# requests arriving before the first finishes could both observe zero
# cooldown and both call `poll_loop.run_once()`.
FLASH_POLL_ALREADY_RUNNING = "poll_already_running"

# Phase 15 D-10/D-11 (15-05-PLAN.md): the per-flight colour-rules editor's
# route constants, mirroring how airlines_page.py owns RESOLVE_ROUTE/
# MANUAL_DELETE_ROUTE_PREFIX/_SUFFIX and companion/app.py rebinds them
# rather than re-typing the literals. Add and delete are immediate POSTs
# on their own routes, outside SETTINGS_ROUTE and the settings form's
# unsaved-changes dirty bar — a rule is a one-step immediate act, not a
# pending edit.
RULES_ADD_ROUTE = "/settings/rules/add"
RULES_DELETE_ROUTE_PREFIX = "/settings/rules/"
RULES_DELETE_ROUTE_SUFFIX = "/delete"

# 19-11-PLAN.md Task 1 (D-08/A-26): the calendar disconnect action's own
# route, following RULES_ADD_ROUTE's exact naming/rebinding convention
# immediately above — companion/app.py rebinds this rather than
# retyping the literal, since app.py imports this module (the reverse
# import would be a cycle). An immediate, session-gated POST outside
# SETTINGS_ROUTE and the settings form's dirty bar, for the identical
# reason a colour rule's add/delete are: this is a one-step act, not a
# pending settings edit.
CALENDAR_DISCONNECT_ROUTE = "/settings/calendar/disconnect"

# 20-09-PLAN.md Task 3 (D-15a..e): renamed from "Per-flight colour
# rules" — caption through t() at the render site. The old precedence/
# replace-on-add sentence moves into a <details> disclosure
# (RULES_HOW_RULES_COMBINE_*, below). D-17 (21-01-PLAN.md Task 2): that
# disclosure no longer has a collapsed one-sentence variant — it always
# renders in full. 21-05-PLAN.md Task 1 (D-06/D-10): the standalone
# "Flight colours" card and its own heading constant are retired
# outright — this content now renders inside the Frame colours
# card's own "Per-flight rules" usage panel, named by that panel's own
# <legend>, never by a second heading of its own. The caption survives,
# unchanged, as the panel's own lead-in sentence.
RULES_SECTION_CAPTION = "Give one flight, one aircraft or one airline its own theme."
RULES_HOW_RULES_COMBINE_SUMMARY = "How rules combine"
RULES_HOW_RULES_COMBINE_BODY = (
    "The most specific match wins — a flight rule beats an aircraft "
    "rule, which beats an airline rule — and adding a key that's "
    "already in use replaces the existing rule for it.")
# D-17 (21-01-PLAN.md Task 2): the one-sentence collapsed disclosure
# variant is deleted along with the display mode that selected it —
# the "How rules combine" <details> below always renders in full now.
# D-15b: the segmented "Match by" control's own visually-hidden group
# label — kept distinct from each segment's own visible text
# (RULE_KIND_LABELS) and technical title (RULE_KIND_TITLES) below.
RULE_KIND_FIELD_LABEL = "Match by"
RULE_VALUE_FIELD_LABEL = "Value"
RULE_ADD_BUTTON_TEXT = "Add rule"
# D-15b: the plain-language segment labels shown to everyone — used by
# BOTH the add form's segment text and the rule-row kind badge, so the
# two can never disagree (mirrors 15-UI-SPEC.md's own "never abbreviated
# differently in the list than in the form" rule, carried over verbatim
# for the new wording).
RULE_KIND_LABELS = {
    colour_rules.RULE_KIND_CALLSIGN: "Flight",
    colour_rules.RULE_KIND_HEX: "Aircraft",
    colour_rules.RULE_KIND_PREFIX: "Airline",
}
# D-15b: "the technical term kept as each option's title" — a SEPARATE
# mapping from RULE_KIND_LABELS above, read only for each segment's own
# `title` attribute, never shown as the visible label text. Phase 15's
# original wording, unchanged.
RULE_KIND_TITLES = {
    colour_rules.RULE_KIND_CALLSIGN: "Callsign",
    colour_rules.RULE_KIND_HEX: "ICAO24 hex",
    colour_rules.RULE_KIND_PREFIX: "Callsign prefix",
}
# D-15b: per-segment placeholders ("AFR1234"/"3944F2"/"AFR") are a
# progressive enhancement no script in this phase implements — this
# section ships no new client-side script at all (20-UI-SPEC.md
# Structural Note 5's native-radio resolution) — deliberately omitted,
# not forgotten. One static placeholder covers the always-valid default
# kind (callsign).
RULE_VALUE_PLACEHOLDER = "AFR1234"
RULES_EMPTY_HEADING = "No flight colours yet."
RULES_EMPTY_BODY = (
    "Add one above to give a flight, aircraft or airline its own theme.")
# D-15c: distinct from airlines_page.DELETE_BUTTON_TEXT ("Delete") —
# this list's own Remove button, per the UI-SPEC copy table's own
# wording, no longer the airlines gallery's "Delete".
RULE_REMOVE_BUTTON_TEXT = "Remove"
# D-15e: the suggestion chips' own label prefix — the joined callsign
# list itself is data, never translated (matches the flight one-liner
# separator's own "data, not translated" precedent, 20-UI-SPEC.md
# Copywriting Contract §A).
RULE_SUGGESTIONS_LABEL = "Recent:"
# aria-labelledby targets for the two radiogroups the add form carries —
# the segmented "Match by" control and the compact theme-chip grid.
RULE_KIND_HEADING_ID = "rule-kind-heading"
RULE_THEME_HEADING_ID = "rule-theme-heading"
# D-15c (LOCKED): the Remove form's own native-confirm question — kept
# despite 20-UI-SPEC.md's Destructive-confirmations table proposing to
# drop it as an immediately-reversible action (re-adding the same key
# restores it); D-15c's own locked text wins over that proposal. This is
# a one-line change (drop the data-confirm attribute below) if the
# developer later prefers the spec's reading.
RULE_REMOVE_CONFIRM_QUESTION = "Remove this rule?"

# The seven flash keys this module's rule-add/rule-delete routes (owned by
# companion/app.py, Task 2) can produce, defined here for the identical
# reason FLASH_SAVED/FLASH_SAVE_FAILED/etc. above are: companion/app.py
# rebinds each under its own FLASH_KEY_RULE_* name and owns the message
# text/ARIA role, mirroring the FLASH_MANUAL_* rebinding pattern
# airlines_page.py already establishes.
FLASH_RULE_ADDED = "rule_added"
FLASH_RULE_REPLACED = "rule_replaced"
FLASH_RULE_KEY_INVALID = "rule_key_invalid"
FLASH_RULE_REGISTRY_FULL = "rule_registry_full"
FLASH_RULE_SAVE_FAILED = "rule_save_failed"
FLASH_RULE_DELETED = "rule_deleted"
FLASH_RULE_DELETE_FAILED = "rule_delete_failed"

# Phase 16 (16-05-PLAN.md, 16-UI-SPEC.md Copywriting Contract) - verbatim,
# do not paraphrase. Every string below is written against
# .planning/ROADMAP.md's Phase 16 measured finding 3: on the one measured
# duty day, none of the calendar owner's three flights were among the
# frame's 201 detections. This feature can only colour a flight that
# happens to be the one currently on screen - it does not track, watch,
# follow, monitor, notify, or know a flight is happening independently of
# what is on screen, and no string here may imply otherwise.
CALENDAR_SECTION_HEADING = "Calendar"
# 20-09-PLAN.md Task 1 (D-14d): the compact chip grid's own
# aria-labelledby target — the card's own <h2> already names the
# subject, so no second visually-hidden label is needed (20-UI-SPEC.md
# §E).
CALENDAR_HEADING_ID = "calendar-heading"
# D-14a: one plain sentence, no lecture — the two-sentence disclaimer
# and the "applies on the next poll" note move into the "How it works"
# disclosure below.
CALENDAR_CAPTION = "Flights from your calendar get their own colour on the frame."
CALENDAR_HOW_IT_WORKS_SUMMARY = "How it works"
CALENDAR_HOW_IT_WORKS_BODY = (
    "It can only colour a flight that happens to be on screen — it "
    "does not track or announce anything on its own. Applies on the "
    "frame's next scheduled poll, not immediately.")
# D-17 (21-01-PLAN.md Task 2): the one-sentence collapsed disclosure
# variant is deleted along with the display mode that selected it —
# the "How it works" <details> below always renders in full now.
# D-14b: the status-row verdict/detail pair replaces the old, one-piece
# CALENDAR_STATUS_* sentences this plan retires. "Not connected" covers
# both the never-configured and the permission-drifted states — a
# drifted stored link is not usably connected either (D-02).
CALENDAR_STATUS_CONNECTED_VERDICT = "Connected"
CALENDAR_STATUS_NOT_CONNECTED_VERDICT = "Not connected"
# 22-10-PLAN.md Task 3 (D-06/B16/CFG-29): the singular form. This string
# used to read "1 upcoming flights" whenever the feed held exactly one.
# 22-08-PLAN.md found it and deliberately left it because that plan does
# not own this file; this plan does, so it lands here. Selection follows
# this file's own established shape (FRAME_COLOURS_RULES_COUNT_SINGULAR /
# _PLURAL_TEMPLATE): singular at exactly 1, plural otherwise.
CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE = "1 upcoming flight · checked %s"
CALENDAR_STATUS_DETAIL_TEMPLATE = "%d upcoming flights · checked %s"
# D-14b/T-20-30: a fixed dict keyed on a category DERIVED from existing
# fields (last_attempt_at newer than any usable last_synced_at) — never
# the fetch's own caught exception text, which server/plane/
# calendar_rules.py does not persist anywhere this module could read it
# from in the first place.
CALENDAR_STATUS_FETCH_FAILED_DETAIL = "The feed could not be read"

# D-14c: the Connect/Replace mini-form's own copy — its own dedicated
# route (CALENDAR_CONNECT_ROUTE below) means this action never shares a
# flash key or a validation path with the settings Save button.
CALENDAR_CONNECT_BUTTON_TEXT = "Connect calendar"
CALENDAR_REPLACE_URL_SUMMARY = "Replace the feed URL"
# 21-07-PLAN.md Task 1 (D-14, Structural Note 6): the SAME form/route
# posts the URL field in both states, but the button reads shorter once
# a feed is already stored — "Connect calendar" only ever applies to a
# first-time paste. Two constants, not one text swapped in place, so
# each stays a plain, greppable literal like every other button label
# in this module.
CALENDAR_REPLACE_BUTTON_TEXT = "Replace"
# 20-09-PLAN.md Task 2 (D-14c): companion/app.py rebinds this rather
# than retyping the literal, mirroring CALENDAR_DISCONNECT_ROUTE's own
# rebinding convention immediately above (app.py imports this module,
# so the reverse import would be a cycle).
CALENDAR_CONNECT_ROUTE = "/settings/calendar/connect"

# Phase 17 plan 03 (D-01/D-02/D-07) — Claude's-discretion wording, final
# once written, matching the locked Phase 16 register above: plain,
# honest, no surveillance verb, no promise the frame cannot keep. The
# file the URL is stored in is never named anywhere below — the
# developer pushed back explicitly on being shown implementation
# mechanics without being told they were mechanics (17-CONTEXT.md
# Specifics).
CALENDAR_URL_FIELD_LABEL = "Calendar feed URL"
CALENDAR_URL_HINT = (
    "Your calendar's private iCal link. Stored on the server and never "
    "shown back here — pasting a new one replaces the old.")
CALENDAR_URL_HINT_ID = "calendar-url-hint"
# 21-07-PLAN.md Task 1 (D-14): the merged card's own small grey button
# reads the short "Disconnect" — never the long checkbox-era sentence a
# now-retired constant used to carry (that sentence survives, unchanged,
# as the confirmation page's own fuller copy below; only the button
# label shortened). A cross-DOM `form=` attribute (CALENDAR_DISCONNECT_
# FORM_ID) is what lets this button submit a <form> that is never its
# own DOM ancestor — the same idiom the dirty bar's own Save button
# already uses for the identical HTML-forms-can't-nest reason.
CALENDAR_DISCONNECT_BUTTON_TEXT = "Disconnect"
CALENDAR_DISCONNECT_FORM_ID = "calendar-disconnect-form"
# Matches the shape of LED_CHECKBOX_VALUE/QUIET_HOURS_CHECKBOX_VALUE/
# DISPLAY_CHECKBOX_VALUE and the now-retired arrivals-override
# checkbox's own former value above. 19-11-PLAN.md
# (D-08/A-26): the checkbox markup that used to submit this value is
# retired, but the value itself is NOT — submitted_calendar_signal()'s
# gates 1-3 below still compare a submitted calendar_disconnect field
# against it, kept deliberately reachable for a hostile client crafting
# that field into a /settings POST (19-RESEARCH.md Pitfall 7). The
# dedicated CALENDAR_DISCONNECT_ROUTE below never reads this value at
# all — it always means "disconnect", once its own confirm gate passes.
CALENDAR_DISCONNECT_CHECKBOX_VALUE = "on"

# 19-11-PLAN.md Task 1 (D-08/A-26): the dedicated disconnect route's own
# confirm gate — the single definition site the markup (the merged
# calendar_group()'s own disconnect form/calendar_disconnect_confirm_
# page() below), the client-side misclick guard (companion/static/
# confirm-submit.js, Task 2), and the handler
# (companion/app.py's _handle_calendar_disconnect_post()) all read,
# rather than each retyping the field name/accepted value as a literal.
# Deliberately a different field name from calendar_disconnect above —
# the two routes' confirm semantics must never be conflated: this field
# means "the confirmation step passed", that one meant "the in-form
# checkbox was ticked".
CALENDAR_DISCONNECT_CONFIRM_FIELD = "confirm"
CALENDAR_DISCONNECT_CONFIRM_VALUE = "yes"
# The question companion/static/confirm-submit.js passes to
# window.confirm() (a misclick guard only — see that file's own header
# comment) — carried to the browser via the merged calendar_group()'s
# own disconnect form's data-confirm attribute, never duplicated in the
# script itself.
CALENDAR_DISCONNECT_CONFIRM_QUESTION = (
    "Disconnect this calendar and delete the flights it supplied?")
# The server-rendered two-step confirmation page's own copy
# (calendar_disconnect_confirm_page() below) — what a no-JS or
# CSP-blocked browser sees instead of the native dialog above. States
# the same consequence in a full sentence, since there is no button
# label length constraint here the way there is on the standalone
# button.
CALENDAR_DISCONNECT_CONFIRM_HEADING = "Disconnect calendar?"
CALENDAR_DISCONNECT_CONFIRM_SENTENCE = (
    "This disconnects your calendar and deletes the flights it "
    "supplied from the server. This can't be undone — you'd need to "
    "paste the feed URL again to reconnect.")
CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT = "Disconnect calendar"
CALENDAR_DISCONNECT_CANCEL_TEXT = "Cancel"
# D-02's fourth status state: the one string in this interface permitted
# to reference "the server", because it is the one case where the
# operator has to act there. Names no path, no filename, no part of the
# URL. Deliberately carries no apostrophe/quote/ampersand — calendar_
# group() interpolates every status string through escape_html(), and a
# literal-substring check against the raw constant (this module's own
# Task 1 verification) would otherwise be comparing against a character
# escape_html() rewrites (the same apostrophe-escaping surprise plan
# 17-02 recorded for CALENDAR_STATUS_NOT_CONFIGURED).
CALENDAR_STATUS_PERMISSION_UNSAFE = (
    "Connected, but ignored — its saved link on the server became "
    "readable beyond this frame. Paste the feed URL again below to "
    "store it safely.")
# A shape bound against an absurd paste, not a definition of an
# acceptable URL. The single arbiter of whether a URL is acceptable
# stays the existing server-side safety gate (calendar_rules._url_is_
# safe()) and the fetch itself; a second definition here would drift
# from that one and start refusing feeds the fetch would accept.
CALENDAR_URL_MAX_LEN = 2048

# Phase 17 plan 04 (D-06/D-09): the four flash keys the save-triggered
# immediate sync can produce, defined here for the identical reason
# FLASH_SAVED/FLASH_POLL_TRIGGERED/etc. above are — companion/app.py
# rebinds each under its own FLASH_KEY_CALENDAR_* name and owns the
# message text/ARIA role, mirroring that same rebinding pattern exactly.
FLASH_CALENDAR_CONNECTED = "calendar_connected"
FLASH_CALENDAR_SYNC_FAILED = "calendar_sync_failed"
FLASH_CALENDAR_DISCONNECTED = "calendar_disconnected"
FLASH_CALENDAR_SYNC_DEFERRED = "calendar_sync_deferred"
# 20-09-PLAN.md Task 2 (D-14c): the two outcomes only
# POST /settings/calendar/connect can produce — companion/app.py rebinds
# both, mirroring the four rebindings immediately above. The failure
# path reuses FLASH_CALENDAR_SYNC_FAILED itself rather than earning a
# third calendar failure message (this task's own explicit instruction:
# "the existing sync-failure flash key").
FLASH_CALENDAR_CONNECT_OK = "calendar_connect_ok"
FLASH_CALENDAR_CONNECT_INVALID = "calendar_connect_invalid"

# 20-11-PLAN.md Task 1 (D-26): the two outcomes POST /settings/
# notifications/test can produce — companion/app.py rebinds both,
# mirroring FLASH_CALENDAR_CONNECT_OK/_INVALID's own rebinding pattern
# immediately above.
FLASH_NOTIFICATIONS_TEST_OK = "notifications_test_ok"
FLASH_NOTIFICATIONS_TEST_FAILED = "notifications_test_failed"


def _field_error_html(errors, field, control_id):
    """D-07 (19-07-PLAN.md Task 2): the empty string when `field` carries
    no message in `errors` (which is `None` or `{}` for every render()
    call this plan does not itself add — every existing call site keeps
    emitting nothing here), otherwise a single `role="alert"` paragraph
    rendered immediately after the offending control:
    `<p class="field-error text-label" id="{control_id}-error"
    role="alert">{escaped message}</p>`. `control_id` need not match any
    real DOM `id` already on the control — it exists solely to build a
    stable anchor id that `_field_error_attrs()` below points
    `aria-describedby` at from that SAME control, so the message is
    programmatically associated, not merely visually adjacent. The
    message is interpolated through `escape_html()`, this file's
    universal escaping choke point, matching every other dynamic string
    in this module (T-19-26: never into a script or style context).
    """
    message = errors.get(field) if errors else None
    if not message:
        return ""
    return (
        '<p class="field-error text-label" id="%s-error" role="alert">%s</p>'
    ) % (escape_html(control_id), escape_html(i18n.t(message)))


def _describedby_attr(*ids):
    """19-11-PLAN.md Task 3 (D-12/A-30): the single builder of every
    `aria-describedby` attribute fragment this file emits. Drops every
    falsy id — so a caller can pass a hint id and an error id (which is
    often `None`/`""`) side by side with no conditional of its own — and
    joins the survivors with ONE space, in the order given (this file's
    own convention below is always hint first, then error). Returns the
    empty string when no id survives, so no control this file renders
    ever emits a bare `aria-describedby=""`.
    """
    present = [control_id for control_id in ids if control_id]
    if not present:
        return ""
    return ' aria-describedby="%s"' % escape_html(" ".join(present))


# 19-12-PLAN.md Task 3 (D-13): the suffix template appended to a
# caption's own "Applies on the next scheduled poll" clause when the
# next-wake value is known — never baked into the caption constant
# itself (D-13 says "where the value is known", so the caption must
# read exactly as it does today when it is not).
NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE = " (next wake ≈ %s)"


def _with_next_wake(caption, next_wake_clock):
    """`caption` unchanged when `next_wake_clock` is falsy (D-13: no
    placeholder, no "unknown" — the caption reads exactly as it did
    before this plan); otherwise `caption` plus
    `NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE % next_wake_clock`, appended at
    RENDER time. The single implementation every caption site below
    uses, so none hand-concatenates its own suffix.

    `DISPLAY_SECTION_CAPTION` deliberately never calls this: it states
    its own honest ~5-minute screen-off latency instead of the generic
    "next scheduled poll" clause (12-CONTEXT.md D-01), and appending a
    wake-interval-derived figure there would contradict that sentence —
    see `render()`'s own comment at that group for the same exception.

    20-07-PLAN.md Task 3 (D-05): `caption` is translated by the CALLER
    (every call site below passes `i18n.t(SOME_CAPTION_CONSTANT)`) — this
    function only translates its OWN suffix template, and does so BEFORE
    substituting `next_wake_clock` into it, matching this codebase's
    established "%-template translated first, formatted second" pattern
    (health_page.py's SOURCE_FAULT_BODY_TEMPLATE, 20-03-PLAN.md).
    """
    if not next_wake_clock:
        return caption
    return caption + (i18n.t(NEXT_WAKE_CAPTION_SUFFIX_TEMPLATE) % next_wake_clock)


def _field_error_attrs(errors, field, control_id, hint_id=None):
    """The ARIA attribute fragment for the control `_field_error_html()`
    above just built an error anchor for, folding in an optional
    `hint_id` (19-11-PLAN.md Task 3, D-12/A-30) via `_describedby_attr()`
    above — hint first, then the error id, matching that helper's own
    documented order. `hint_id` defaults to `None` so every pre-Task-3
    call site (which never passed it) keeps emitting byte-identical
    output: with no error and no hint, this still returns `""`.

    Three shapes, depending on what's present:
      - no error, no `hint_id`: `""` (unchanged since 19-07-PLAN.md).
      - no error, a `hint_id`: ` aria-describedby="{hint_id}"` alone —
        no `aria-invalid`, since there is nothing invalid to report.
      - an error (`hint_id` present or not): ` aria-invalid="true"`
        plus a combined `aria-describedby` naming the hint (if given)
        and `{control_id}-error` (`_field_error_html()`'s own anchor
        id), in that order.

    Applied to controls that have exactly one natural DOM element to
    decorate (a text/number/time input, a checkbox, or a `<select>`);
    the three radio-group fields (theme, theme_arriving, tracked_runway)
    render their error message the same way but skip this attribute
    fragment entirely — no single native input in a same-named radio
    group is uniquely "the" control to describe, and (Task 3) their
    hint linking instead lands on the `role="radiogroup"` CONTAINER via
    a direct `_describedby_attr(hint_id)` call at each of those two call
    sites, never through this function.
    """
    has_error = bool(errors and errors.get(field))
    error_id = ("%s-error" % control_id) if has_error else None
    describedby = _describedby_attr(hint_id, error_id)
    if has_error:
        return ' aria-invalid="true"%s' % describedby
    return describedby


def _submitted_or_current(submitted, field, current):
    """This file's explicit-`is None` fallback idiom (see the
    current_wake_interval_s comment inside render() below), applied to a
    rejected save's repopulation: `submitted[field]` when `field` is
    PRESENT in `submitted` — an empty string is a meaningful submitted
    value, never treated as absent — else `current`. `submitted` is
    `None` for every render() call that is not re-rendering a rejected
    save (nothing to repopulate from, so `current` — the on-disk/ctx
    value — always wins). Never `or`.
    """
    if submitted is not None and field in submitted:
        return submitted[field]
    return current


def _submitted_checkbox_checked(submitted, field, checked_value, current_checked):
    """The rendered `checked` state for one of the absent-means-False
    checkbox fields (led_enabled/quiet_hours_enabled/display_enabled/
    the two Notifications checkboxes) on a rejected save's re-render.

    When a real submission happened (`submitted is not None` — always a
    dict, even an empty one, once a POST reaches this module:
    companion/app.py's `read_form()` never returns `None`), an absent
    field means unchecked — the identical absent-means-False semantics
    `handle_post()` itself just applied to the same submission — and a
    present-but-wrong value still renders unchecked (the field's own
    error message is what reports the problem, never a bogus stuck-on
    box). `submitted is None` (every ordinary page-load render(), never
    a rejected-save re-render) falls back to `current_checked`
    untouched — this is why `render()` below must NOT collapse a `None`
    `submitted` to `{}`: doing so would make every ordinary page load
    render every checkbox in this family unchecked, since an ordinary
    load never real-submits any of them either.
    """
    if submitted is None:
        return bool(current_checked)
    return submitted.get(field) == checked_value


def _palette_hex(index):
    """`#RRGGBB`, computed from `server.panel_format.PALETTE_RGB`'s flat
    int list at palette index `index` — never a hardcoded hex literal, so
    a future re-tuning of the physical panel ink (07-01-PLAN.md's own
    real-glass Blue/Green correction precedent) automatically updates
    every swatch that calls this helper.
    """
    r, g, b = panel_format.PALETTE_RGB[index * 3: index * 3 + 3]
    return "#%02X%02X%02X" % (r, g, b)


def _theme_chip_grid_html(
        field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="",
        radio_form_id=None, leading_chip_html=""):
    """Phase 15 D-05: the ONE chip-grid renderer, called once per usage
    panel inside the Frame colours card (21-05-PLAN.md Task 1, D-06..
    D-12) — departures (`field_name="theme"`), arrivals
    (`field_name="theme_arriving"`), calendar flights
    (`field_name="calendar_theme_id"`) and the rule-add form
    (`field_name="rule_theme_id"`). They differ ONLY in the radio
    group's `name`, which chip is marked `checked`/`--selected`, this
    grid's own wrapper class/attribute, and (arrivals/calendar) a
    leading non-theme chip — everything else (the hidden-radio
    selectable-card idiom, the `/theme-preview/{id}.png` source, the
    `_palette_hex()` swatch dots, the check glyph) is one shared
    definition.

    21-05-PLAN.md Task 1 (D-09, Structural Note 3): `leading_chip_html`
    is a fourth, additive, purely-interpolated seam — a pre-built HTML
    fragment (typically one "Same as departures" chip submitting the
    empty string) inserted before the loop over `device_config.
    THEME_IDS`. Defaults to `""`, so every call that omits it (the
    departures grid, the rule-add form's own compact grid) renders
    byte-identical to before this addition.

    20-09-PLAN.md Task 1/3 (D-14d/D-15b): `chip_extra_class` is a THIRD,
    independent seam — distinct from `extra_class` (the grid wrapper's
    own modifier) — applied to EVERY chip's own `<label>` class
    attribute. This is what actually shrinks each chip to the compact
    104px geometry (`companion/static/style.css`'s `.theme-chip--compact`
    rules key off the CHIP's own class, per 20-UI-SPEC.md §G's markup:
    "N .theme-chip.theme-chip--compact entries") — the grid-level
    `theme-chip-grid--compact` modifier alone has no chip-shrinking rule
    of its own and would silently do nothing without this.

    20-11-PLAN.md Task 2 (D-24): every chip's own `<label>` ALSO gains one
    new attribute naming the theme's own live-render path (the exact
    attribute name `companion/static/theme-preview.js`, 20-08, already
    reads off the changed radio input's parent `<label>`). Added
    additively, on every grid this function renders (the compact variant
    included, D-24's own "additive" instruction): the script's own guard
    clause returns early on any page with no `.theme-live-preview`, so a
    page that only has the compact grid (Calendar, the rules add-form)
    inherits the new attribute harmlessly. The chip's own `<img>` src is
    UNCHANGED — still the fixed, non-live preview, still lazily loaded —
    only the new attribute is added; the live theme preview's own image
    (a sibling element `theme_fieldset()` renders above the grid) is
    what that new attribute is ever read to update.

    D-12 fix (20-REVIEW.md verification gap): `radio_form_id`, when
    given, adds an explicit `form="{radio_form_id}"` attribute to every
    radio input this grid renders — the SAME `form=` idiom
    `runway_fieldset()`'s own radios and `display_group()`/
    `quiet_hours_group()`'s scheduled inputs already use (Polish fix 4,
    D-19/Pitfall 1), so this grid keeps posting through the physical
    settings form even when `render()` renders its enclosing card as a
    sibling of that form rather than a literal descendant. Defaults to
    `None` (no attribute at all, byte-identical to before this fix) —
    Theme's own two always-in-form grids and the rule-add-form's grid
    never pass it.

    25-06-PLAN.md Task 2 (CFG-50): the DEPARTURES call site now passes a
    second grid-level modifier (`theme-chip-grid--strip`) and an `id`,
    and `_theme_carousel_html()` wraps what this function returns. THIS
    FUNCTION IS UNCHANGED BY THAT — the carousel is a presentation
    around its output, deliberately not a sixth seam and emphatically
    not a fork: four call sites share this function, and a second
    renderer is exactly how the arrivals grid and the departures grid
    come to disagree about what a selected chip looks like.

    27-07-PLAN.md Task 2 (CFG-68): ARRIVALS AND CALENDAR NOW FOLD THE
    SAME WAY, each with its OWN strip id from `_theme_carousel_html()`'s
    now-required `strip_id` argument (Task 1) — the brief names exactly
    "arrivals, departures, calendar flights", so this is not the
    research's four-grid scope but the brief's three-grid one. Only the
    RULE-ADD FORM'S GRID stays unconverted, and that is a recorded scope
    decision rather than an oversight for a later reader to "finish": it
    lives inside the "règles par vol" view the brief explicitly defers
    as too vague to plan against, and wrapping a control inside a view
    that is about to be redesigned would spend work twice — see that
    call site's own comment for the ground, PROVISIONAL and one more
    call to this same helper away if the developer wants it folded too.
    Three carousels share the file's ONE `@supports selector(:has(*))`
    block (a `:has()` rule scoped per-`.theme-carousel` instance, not
    one rule per carousel — see that rule's own comment in style.css),
    so this does NOT multiply that risk by three; it was written and
    measured to stay at exactly one block.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    chips = []
    for theme_id in device_config.THEME_IDS:
        selected = theme_id == selected_theme_id
        checked = " checked" if selected else ""
        chip_class = "theme-chip"
        current_attr_html = ""
        if selected:
            chip_class += " theme-chip--selected"
            # 22-10-PLAN.md Task 1 (T10): emitted ONLY on the saved chip,
            # because `.theme-chip--selected:not(:has(input:checked))::after`
            # is the only selector that can ever read it. A translated
            # constant, escaped at its attribute site like every other
            # attribute on this page — never user input (T-22-35).
            current_attr_html = ' %s="%s"' % (
                CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
        if chip_extra_class:
            chip_class += " " + chip_extra_class
        theme = device_config.THEMES[theme_id]
        # Polish fix 5 (D-05): device_config.theme_label()'s registry
        # text ("White", "Band Blue Field", …) is translated at THIS
        # display site via i18n.t() — the ids themselves (theme_id)
        # never change, and server/device_config.py's own English
        # THEMES["label"] values stay untranslated at the source
        # (companion/i18n_fr/registry.py supplies the French entries).
        label = i18n.t(device_config.theme_label(theme_id))
        escaped_id = escape_html(theme_id)
        departing_hex = _palette_hex(theme["departing_index"])
        arriving_hex = _palette_hex(theme["arriving_index"])
        chips.append(
            '<label class="%s" data-preview-src="%s%s.png?live=1"%s>'
            '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
            # 23-10-PLAN.md Task 3 (D3/CFG-32): background-COLOR, not
            # the `background` shorthand it used to be. Same rendered
            # placeholder, same value, and the change is load-bearing:
            # the shorthand resets background-image to none, and an
            # inline style beats every author rule, so style.css's
            # skeleton sheen for this band was unreachable while this
            # said `background`. The band's own box is already reserved
            # (width: 100%, height: 56px, both definite), so this is the
            # decoration half only.
            '<img class="theme-chip__preview" src="%s%s.png" alt="%s" '
            'width="320" height="120" loading="lazy" style="background-color:%s">'
            '<span class="theme-chip__body">'
            '<span class="theme-chip__name">%s</span>'
            '<span class="theme-chip__swatches" aria-hidden="true">'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            '<span class="theme-chip__dot" style="background:%s"></span>'
            "</span>"
            "</span>"
            '<span class="theme-chip__check">%s<span class="visually-hidden">%s</span></span>'
            "</label>"
            % (
                chip_class, THEME_PREVIEW_ROUTE_PREFIX, escaped_id, current_attr_html,
                escape_html(field_name), escaped_id, form_attr_html, checked,
                THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
                escape_html(i18n.t(THEME_PREVIEW_ALT_TEMPLATE) % label),
                escape_html(departing_hex),
                escape_html(label),
                escape_html(departing_hex), escape_html(arriving_hex),
                layout.icon_html("icon-check"),
                escape_html(i18n.t("Selected")),
            )
        )
    grid_class = "theme-chip-grid"
    if extra_class:
        grid_class = grid_class + " " + extra_class
    attr_html = (" %s" % extra_attr) if extra_attr else ""
    # 22-10-PLAN.md Task 1 (X6): the swatch legend, one line UNDER the
    # grid and OUTSIDE it — outside so it is not a child of the element
    # carrying `role="radiogroup"`, where a stray non-radio child would
    # be announced inside the group.
    #
    # It carries `.text-label section-caption`'s exact declaration set
    # and no class of its own. A legend under a CONTROL is not the
    # section's caption: `references/settings-page-patterns.md`'s
    # one-caption-per-section rule is about the caption that follows a
    # section HEADING, and each usage panel's own caption (the rules
    # panel's `RULES_SECTION_CAPTION`) is untouched by this. Stating that
    # here rather than leaving a reviewer to infer it.
    legend_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        i18n.t(THEME_CHIP_SWATCH_LEGEND))
    return '<div class="%s"%s>%s%s</div>%s' % (
        grid_class, attr_html, leading_chip_html, "".join(chips), legend_html)


def _theme_carousel_html(grid_html, strip_id):
    """25-06-PLAN.md Task 2 (CFG-50): D5's carousel, as a PRESENTATION
    wrapped around `_theme_chip_grid_html()`'s existing output — never a
    second chip renderer.

    27-07-PLAN.md Task 1 (CFG-68): `strip_id` is REQUIRED, not an
    optional parameter with a shared default — THE TRAP this plan exists
    to close. Before this task the strip's `id` and both pagers'
    `aria-controls` all read the same module constant
    (`THEME_CAROUSEL_STRIP_ID`) directly; calling this function a second
    time for a second grid would render two elements sharing one `id`
    (invalid HTML) and leave every pager on the page driving only the
    FIRST strip, silently. Making the id a required argument — derived
    ONCE per call site and threaded through both the grid's own `id`
    attribute (set by the caller, outside this function — see
    `_frame_colours_card_html()`) and this function's two
    `aria-controls` — makes that collision structurally impossible
    rather than merely untested: there is no code path left in which two
    carousels can agree to share an id by omission. Departures, the one
    caller that predates this parameter, passes its own
    `THEME_CAROUSEL_STRIP_ID` explicitly and renders byte-identical
    except for the reorder below.

    `grid_html` arrives already built and is interpolated UNCHANGED: the
    same eighteen `.theme-chip` labels, the same visually-hidden native
    radios, the same check glyphs, the same `role="radiogroup"`, and the
    same swatch legend glued underneath the grid and outside it. This
    function adds a wrapper, a row of colour dots, and (Task 3) a
    disclosure and two gated pagers. It emits no chip.

    THE CAROUSEL IS THE RADIO GROUP, NOT A THING BESIDE IT. The strip is
    the grid laid out with CSS scroll-snap, which is what makes swipe
    native; arrow keys already move selection inside a radiogroup and a
    browser already scrolls a focused label into view. That is why this
    control needs almost no script, and it is why nothing here has a
    "current slide" distinct from "selected theme" — in a radio group
    those are the same thing, and a second state is how
    `style.css`'s one feature query comes to have a sibling.

    THE DOTS ROW CARRIES EACH THEME'S OWN COLOUR AND NO SELECTION STATE
    AT ALL, and that is a decision rather than an omission. A dots row
    that tracked the current slide would need either a `:has()` chain
    reaching from a checked radio in the grid to one dot in a sibling
    row (eighteen rules, inside the one feature query whose arithmetic
    is marked "verified, not to be re-derived") or a script; with
    neither, a server-rendered "active dot" would be marking the SAVED
    theme and would be visibly wrong the instant a chip is clicked with
    scripts blocked. So each dot is that theme's own
    `_palette_hex(departing_index)` — the identical per-theme inline
    mechanism the chips' own `.theme-chip__dot` swatches already use,
    never a colour literal in the stylesheet — and the row is
    `aria-hidden`, because the chips themselves already announce all of
    this in real text and eighteen dots after eighteen radios is noise.

    MEASURED WHILE WRITING THIS, AND RECORDED BECAUSE IT SURPRISED:
    every one of the eighteen themes has `departing_index ==
    arriving_index`, and the eighteen resolve to only SEVEN distinct
    hexes. So this row is a palette overview, not an identifier of
    individual themes, and the chips' own two swatch dots — the ones the
    "Departures & arrivals" legend names (27-07-PLAN.md Task 3, CFG-70:
    joined into one phrase, since a middle-dot separator between two
    identical swatches was itself naming a distinction that is not
    there) — are the same colour as each other in every theme this app
    ships. That is a registry fact, not a
    defect introduced here, and nothing in this plan changes it.
    """
    dots = "".join(
        '<span class="theme-chip__dot" style="background:%s"></span>' % escape_html(
            _palette_hex(device_config.THEMES[theme_id]["departing_index"]))
        for theme_id in device_config.THEME_IDS)
    dots_html = (
        '<div class="theme-carousel__dots theme-chip__swatches" aria-hidden="true">%s</div>'
        % dots)
    # A NATIVE <details>, NOT A <dialog>, AND THAT IS A DELIBERATE
    # DEVIATION FROM 22-AUDIT.md's OWN WORDING (D5: "full grid behind
    # 'See all themes' in a dialog"). A <dialog> has no way to open
    # without script — `showModal()` is the only thing that opens one —
    # so eighteen themes behind a dialog is eighteen themes behind a
    # control that does nothing whatever with scripts blocked, which is
    # the exact defect this phase exists to prevent. <details> opens
    # natively, already has this app's shipped chevron treatment
    # (22-15 T3) and already sits in the harness's disclosure sweep.
    #
    # AND IT GOVERNS THE GRID THAT PRECEDES IT RATHER THAN CONTAINING
    # ONE. This is the part a later reader will want explained, so:
    # there is exactly ONE set of eighteen radios on this page (per
    # usage), and the strip and the full grid are the same set. That
    # forces this shape. A <details> hides its own non-summary children
    # when closed, so a disclosure that CONTAINED the grid would hide
    # all eighteen themes whenever it was shut — there would be no strip
    # at all — and the only way to have both an always-visible strip and
    # a full-grid disclosure while keeping one set of radios is for the
    # disclosure to change the layout of a grid it does not contain.
    #
    # 27-07-PLAN.md Task 1 (CFG-68/D-20): the disclosure used to render
    # BEFORE the strip (an adjacent-sibling `[open] + .theme-chip-grid
    # --strip` rule reached forward from it) — "Voir tous les thèmes"
    # sat above the strip it discloses, which the developer read as
    # backwards: a way OUT belongs below the thing it expands, not above
    # it. It now renders LAST in this wrapper (see the return statement
    # below), so the adjacent-sibling selector can no longer reach
    # forward to a grid that now precedes it in the DOM. style.css
    # replaces it with a `:has()` rule scoped to the WRAPPING
    # `.theme-carousel` element instead — `.theme-carousel:has(
    # .theme-carousel__all[open]) .theme-chip-grid--strip` — which reads
    # "this carousel contains an open disclosure" rather than "this
    # disclosure is immediately followed by a strip", and so does not
    # care which of the two comes first. It joins the file's existing
    # `@supports selector(:has(*))` block rather than opening a second
    # one (the file's own pinned block-count convention); a browser
    # without `:has()` keeps the strip in its scrolling, one-row form
    # even with the disclosure open — an accepted degradation, since
    # the disclosure's own body copy already says "They are all in the
    # strip either way — it scrolls."
    #
    # The alternative — two sets of eighteen radios — was rejected, and
    # not on tidiness grounds: they would share a name and a form, so a
    # browser would treat them as ONE radio group and keep exactly one
    # checked, but the page would then carry two places showing a
    # selection, two `--selected` chips, and two copies of every chip
    # image, for a setting that has one value (T-25-06-B).
    #
    # Nothing is hidden behind this control at any time, so the body
    # says so in real, translated text rather than leaving a reader to
    # discover it.
    disclosure_html = (
        '<details class="theme-carousel__all">'
        "<summary>%s</summary>"
        '<p class="text-body">%s</p>'
        "</details>"
    ) % (
        escape_html(i18n.t(THEME_CAROUSEL_SUMMARY)),
        escape_html(
            i18n.t(THEME_CAROUSEL_DISCLOSURE_BODY_TEMPLATE)
            % len(device_config.THEME_IDS)),
    )
    # The two pagers, and NOTHING ELSE, sit behind 25-01's `.js` gate —
    # they are the only part of this control that cannot work without a
    # script. The gate class is on the wrapper ITSELF (not an ancestor),
    # which is what companion/test_companion_app.py's no-JS control
    # registry asserts for every element carrying
    # THEME_CAROUSEL_WRAPPER_ATTR.
    #
    # Real <button>s with real labels, never aria-hidden decorations,
    # and `aria-controls` naming the strip — which is also how
    # theme-preview.js finds the element to scroll, so the accessibility
    # contract and the script contract are ONE contract. Neither button
    # listens for a key of any kind: a pager that captured ArrowLeft
    # would break the native radiogroup selection the whole no-JS path
    # depends on.
    #
    # `.control-hit-area` is 25-01's shared 22x22-box-plus-44x44-::before
    # synthesis, which is `.copy-btn`'s own values verbatim — not a
    # fourth set of numbers. The glyph is drawn in CSS rather than
    # written as a "◀"/"▶" character, following `summary::before`'s own
    # recorded reasoning: a `content` string is the hard-coded-English
    # hazard T10 had to unpick, and an arrow glyph's rendering varies by
    # installed font.
    pager_template = (
        '<button type="button" class="control-hit-area theme-carousel__pager%s"'
        ' %s="%s" aria-controls="%s" aria-label="%s"></button>')
    # BOTH pagers' aria-controls derive from `strip_id` — the ONE
    # argument this call was given — rather than from
    # THEME_CAROUSEL_STRIP_ID directly. That is the whole fix: a second
    # carousel built from this function with its own `strip_id` gets
    # pagers that drive ITS OWN strip, never the first one built.
    pagers_html = (
        '<div class="theme-carousel__pagers %s" %s>%s%s</div>'
    ) % (
        escape_html(layout.JS_GATE_CLASS), THEME_CAROUSEL_WRAPPER_ATTR,
        pager_template % (
            " theme-carousel__pager--prev", THEME_CAROUSEL_PAGER_ATTR,
            THEME_CAROUSEL_PAGER_PREV, escape_html(strip_id),
            escape_html(i18n.t(THEME_CAROUSEL_PREV_LABEL))),
        pager_template % (
            "", THEME_CAROUSEL_PAGER_ATTR, THEME_CAROUSEL_PAGER_NEXT,
            escape_html(strip_id),
            escape_html(i18n.t(THEME_CAROUSEL_NEXT_LABEL))),
    )
    # 27-07-PLAN.md Task 1 (CFG-68/D-20): grid, pagers, dots, disclosure
    # — the disclosure LAST, so "Voir tous les thèmes"/"See all themes"
    # reads as a way OUT below the strip it expands rather than a
    # preamble above it. See the disclosure's own comment above for why
    # style.css no longer reaches the grid through a forward
    # adjacent-sibling selector once the disclosure trails it.
    return '<div class="theme-carousel">%s%s%s%s</div>' % (
        grid_html, pagers_html, dots_html, disclosure_html)


def _theme_live_preview_html(current_theme_id, state_dir, extra_class=""):
    """The `<figure class="theme-live-preview">` the Frame colours
    card (21-05-PLAN.md Task 1) renders as the left column of its own
    two-column layout (D-22..D-24, 20-11-PLAN.md Task 2, 20-UI-SPEC.md
    Section Anatomy H/copy table E; 21-UI-SPEC.md §D). `extra_class`
    (additive, defaulting to `""`) lets the one live call site add its
    own `frame-colours__preview` layout modifier without a second,
    duplicated figure builder.

    The `<img src>` is `{THEME_PREVIEW_ROUTE_PREFIX}{theme_id}.png?live=1`
    for the SAVED theme (`current_theme_id`, membership-tested against
    `device_config.THEMES` before ever reaching a path component —
    T-20-14, the same discipline `theme_fieldset()`'s own single-theme
    branch already applies), eagerly loaded (the one eagerly-loaded
    image on this page — every chip's own preview stays lazily loaded)
    and explicit `width`/`height` from the render pipeline's real
    served dimensions (`theme_preview.THEME_PREVIEW_SIZE`), never a
    CSS `aspect-ratio` guess. Without JavaScript this `<img>` never
    changes — `companion/static/theme-preview.js` (20-08) is what swaps
    it on chip selection; the server-rendered `src` here IS D-24's
    documented no-JS floor.

    The caption reads the most recent runway event's callsign through
    the SAME connection helper `_rule_suggestion_chips_html()` already
    uses (`history_db.open_db()`/`recent_runway_events(limit=1)`) —
    never a second, independently-opened connection this page does not
    already make — degrading to the sample-flight wording on absolutely
    any exception (a missing/locked history.db, no rows at all), never
    raising and never a 500. This read never affects the `<img>` itself:
    the `?live=1` route resolves the event server-side on its own, so a
    failed read here only changes which caption sentence renders.
    `state_dir` may be falsy (matching every other optional-state_dir
    call site in this file, e.g. `runway_fieldset()`'s own `ctx.get(
    "runway_images")` pattern) — this degrades to the sample caption
    exactly like a genuine read failure would.
    """
    live_theme_id = (
        current_theme_id if current_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    # Polish fix 5 (D-05): translated at this display site, same as
    # _theme_chip_grid_html()'s own label above.
    label = i18n.t(device_config.theme_label(live_theme_id))
    callsign = None
    if state_dir:
        try:
            with history_db.open_db(state_dir) as conn:
                rows = history_db.recent_runway_events(conn, limit=1)
            if rows:
                callsign = rows[0].get("callsign")
        except Exception:
            callsign = None
    if callsign:
        caption_text = i18n.t(THEME_LIVE_PREVIEW_CAPTION_WITH_FLIGHT_TEMPLATE) % callsign
    else:
        caption_text = i18n.t(THEME_LIVE_PREVIEW_CAPTION_SAMPLE)
    figure_class = "theme-live-preview"
    if extra_class:
        figure_class = figure_class + " " + extra_class
    return (
        '<figure class="%s">'
        '<img class="theme-live-preview__image" src="%s%s.png?live=1" '
        'width="%d" height="%d" loading="eager" alt="%s">'
        '<figcaption class="text-label">%s</figcaption>'
        "</figure>"
    ) % (
        figure_class,
        THEME_PREVIEW_ROUTE_PREFIX, escape_html(live_theme_id),
        THEME_LIVE_PREVIEW_WIDTH, THEME_LIVE_PREVIEW_HEIGHT,
        escape_html(i18n.t(THEME_LIVE_PREVIEW_ALT_TEMPLATE) % label),
        escape_html(caption_text),
    )


def _same_as_departures_chip_html(field_name, checked, radio_form_id=None):
    """21-05-PLAN.md Task 1 (D-09): the leading, non-theme chip
    Arrivals'/Calendar's own usage panels prepend to their chip grid
    via `_theme_chip_grid_html()`'s `leading_chip_html` seam — submits
    the EMPTY STRING for `field_name` (R-07's clear signal), never a
    real theme id. Reuses `.theme-chip`/`.theme-chip__body`/
    `.theme-chip__check`'s own markup shape (21-UI-SPEC.md §D: "reuses
    .theme-chip's own markup shape with no <img> preview") — a
    swatch-less name-only body, never a fabricated theme-coloured
    preview for "no override".
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    chip_class = "theme-chip theme-chip--placeholder"
    current_attr_html = ""
    if checked:
        chip_class += " theme-chip--selected"
        # 22-10-PLAN.md Task 1 (T10): this chip can be the saved one too
        # (Arrivals/Calendar left on "Same as departures" is the DEFAULT
        # state), so it needs the badge attribute for the same reason
        # every other --selected chip does. Omitting it here would have
        # rendered an EMPTY badge on the commonest saved value of all.
        current_attr_html = ' %s="%s"' % (
            CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
    return (
        '<label class="%s"%s>'
        '<input type="radio" name="%s" value="" class="visually-hidden"%s%s>'
        '<span class="theme-chip__body theme-chip__body--placeholder">'
        '<span class="theme-chip__name">%s</span>'
        "</span>"
        '<span class="theme-chip__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        chip_class, current_attr_html,
        escape_html(field_name), form_attr_html, " checked" if checked else "",
        escape_html(i18n.t(SAME_AS_DEPARTURES_LABEL)),
        layout.icon_html("icon-check"), escape_html(i18n.t("Selected")),
    )


def _frame_colours_row_html(usage, checked, label, meta_text, departing_hex, arriving_hex):
    """21-05-PLAN.md Task 1 (D-07/D-08): one `<li><label class=
    "frame-colours__row">` pair of the four-row `colour_usage`
    radiogroup — the visually-hidden native radio supplies the group's
    real selection semantics (the whole row IS its label, the
    `.runway-card`/`.theme-chip` idiom's fourth/fifth consumer);
    `data-usage-panel` names the usage panel this row shows — the same
    id as the radio's own `value`, which is what theme-preview.js
    actually reads (`input.value`); the attribute is the server-side
    statement of that pairing for tests and readers (21-REVIEW.md
    WR-02), not a second script contract. This
    radio carries no `form=` attribute and is NEVER submitted to
    `handle_post()` — it is a pure display-selection control, always
    defaulting to `departures` checked, matching 21-UI-SPEC.md §D's own
    static markup.
    """
    return (
        '<li><label class="frame-colours__row">'
        '<input type="radio" name="%s" value="%s" class="visually-hidden"%s %s="%s">'
        '<span class="frame-colours__swatch theme-chip__swatches" aria-hidden="true">'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        "</span>"
        '<span class="frame-colours__label">%s</span>'
        '<span class="frame-colours__meta">%s</span>'
        "</label></li>"
    ) % (
        COLOUR_USAGE_FIELD_NAME, escape_html(usage), " checked" if checked else "",
        COLOUR_USAGE_PANEL_ATTR, escape_html(usage),
        escape_html(departing_hex), escape_html(arriving_hex),
        escape_html(label), escape_html(meta_text),
    )


def _frame_colours_usage_panel_html(usage, label, inner_html):
    """21-05-PLAN.md Task 1 (D-08, locked no-JS floor): one
    `<fieldset class="frame-colours__usage-panel">` per usage, carrying
    `data-usage-panel-target` (theme-preview.js's own collapse-at-load
    hook, Task 3) — the server NEVER emits `hidden` here; a script-free
    page shows all four fieldsets, each with a real, VISIBLE `<legend>`
    matching its own row's label, so a no-JS reader sees four clearly
    labelled stacked sections in the same order as the radiogroup above
    them, and every control inside still submits its real value.
    """
    return (
        '<fieldset class="frame-colours__usage-panel" %s="%s">'
        '<legend class="frame-colours__panel-legend">%s</legend>'
        "%s"
        "</fieldset>"
    ) % (COLOUR_USAGE_PANEL_TARGET_ATTR, escape_html(usage), escape_html(label), inner_html)


def _frame_colours_card_html(
        ctx, current_theme_id, current_theme_arriving, current_calendar_theme_id,
        errors=None, submitted=None, state_dir=None):
    """21-05-PLAN.md Task 1 (D-06..D-12): the ONE "Frame colours" card
    that replaces `theme_fieldset()` (departures/arrivals), the
    Calendar card's own compact `calendar_theme_id` grid, and the
    retired standalone "Flight colours" card — one live preview, a
    four-row `colour_usage` assignment radiogroup (D-07/D-08), and four
    usage panels (departures/arrivals/calendar chip grids plus the
    rules row's own list-and-add-form, D-10), rendered as a SIBLING of
    `<form id="settings-form">` (Structural Note 2) — every saved
    control inside still cross-submits via `form="settings-form"`.

    `errors`/`submitted` repopulate the three chip grids from a
    rejected save exactly like the retired `theme_fieldset()` did;
    `colour_usage` itself is never submitted (no `form=` attribute on
    those radios) and is therefore never repopulated — it always
    defaults to `departures` checked, matching 21-UI-SPEC.md §D's own
    static markup.
    """
    live_preview_html = _theme_live_preview_html(
        current_theme_id, state_dir, extra_class="frame-colours__preview")

    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    # 25-06-PLAN.md Task 2 (CFG-50): the `id` is added HERE rather than
    # inside the renderer, because it is a property of this ONE call
    # site — an id emitted by a function with four call sites would be
    # four identical ids on one page.
    departures_grid_attr = 'role="radiogroup" aria-labelledby="%s" id="%s"' % (
        escape_html(FRAME_COLOURS_HEADING_ID), escape_html(THEME_CAROUSEL_STRIP_ID))
    # 22-10-PLAN.md Task 1 (X6): the departures grid was this page's LAST
    # full-size chip grid — eighteen 160x108 chips against the same
    # eighteen themes rendered at ~104px in the Arrivals, Calendar and
    # Rules panels, i.e. one control in two shapes on one page. It joins
    # the compact density here, so the Display page has exactly one chip
    # size. The chips are a PICKER; this card's real preview is the large
    # live preview rendered above them, so a 160px chip bought nothing
    # and cost ~1500px of page.
    #
    # `.theme-chip--compact` is a SIZE-ONLY modifier and inherits every
    # selected-state rule automatically (references/control-density.md),
    # so no selection logic changes here and none was touched.
    #
    # X6's OTHER half — "grid folded behind the big preview (dialog/
    # drawer)" — was D5, and 25-06-PLAN.md Task 2 (CFG-50) is where it
    # lands: the SECOND grid-level modifier below lays this one grid out
    # as a scroll-snap strip, and `_theme_carousel_html()` wraps its
    # output. Both are additive; the chips, their radios, their check
    # glyphs and the swatch legend are byte-for-byte what they were.
    # 27-07-PLAN.md Task 2 (CFG-68): arrivals and calendar below now
    # fold the same way, each with its OWN strip id — only the rule-add
    # form's grid, further down, stays untouched (see its own call
    # site's comment for the ground).
    departures_grid = _theme_chip_grid_html(
        "theme", effective_theme_id, extra_attr=departures_grid_attr,
        extra_class="theme-chip-grid--compact theme-chip-grid--strip",
        chip_extra_class="theme-chip--compact",
        radio_form_id=SETTINGS_FORM_ID)
    # 27-07-PLAN.md Task 1 (CFG-68): the SAME id used above to build the
    # grid's own `id=` attribute, passed straight through — one Python
    # name, read twice, rather than two literals that could drift apart.
    departures_carousel = _theme_carousel_html(departures_grid, THEME_CAROUSEL_STRIP_ID)
    theme_error_html = _field_error_html(errors, "theme", "theme")
    departures_safe_id = (
        effective_theme_id if effective_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    departures_theme = device_config.THEMES[departures_safe_id]
    departures_dep_hex = _palette_hex(departures_theme["departing_index"])
    departures_arr_hex = _palette_hex(departures_theme["arriving_index"])
    departures_meta = i18n.t(device_config.theme_label(departures_safe_id))
    departures_panel = _frame_colours_usage_panel_html(
        COLOUR_USAGE_DEPARTURES, i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_DEPARTURES]),
        departures_carousel + theme_error_html)

    effective_arriving = _submitted_or_current(submitted, "theme_arriving", current_theme_arriving)
    arrivals_same_checked = not effective_arriving
    arrivals_leading_chip = _same_as_departures_chip_html(
        "theme_arriving", arrivals_same_checked, radio_form_id=SETTINGS_FORM_ID)
    # 27-07-PLAN.md Task 2 (CFG-68): the `id` is added HERE, at this ONE
    # call site, matching 25-06 Task 2's own reasoning for departures —
    # and it is THIS SAME NAME, read twice, that is passed to
    # `_theme_carousel_html()` below, rather than two literals that
    # could drift apart.
    arrivals_grid_attr = 'role="radiogroup" aria-labelledby="%s" id="%s"' % (
        escape_html(FRAME_COLOURS_HEADING_ID), escape_html(THEME_CAROUSEL_STRIP_ID_ARRIVALS))
    arrivals_grid = _theme_chip_grid_html(
        "theme_arriving", effective_arriving,
        extra_class="theme-chip-grid--compact theme-chip-grid--strip",
        chip_extra_class="theme-chip--compact",
        extra_attr=arrivals_grid_attr, radio_form_id=SETTINGS_FORM_ID,
        leading_chip_html=arrivals_leading_chip)
    arrivals_carousel = _theme_carousel_html(arrivals_grid, THEME_CAROUSEL_STRIP_ID_ARRIVALS)
    theme_arriving_error_html = _field_error_html(errors, "theme_arriving", "theme-arriving")
    if arrivals_same_checked:
        arrivals_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        arrivals_dep_hex, arrivals_arr_hex = departures_dep_hex, departures_arr_hex
    else:
        arrivals_safe_id = (
            effective_arriving if effective_arriving in device_config.THEMES
            else departures_safe_id)
        arrivals_theme = device_config.THEMES[arrivals_safe_id]
        arrivals_dep_hex = _palette_hex(arrivals_theme["departing_index"])
        arrivals_arr_hex = _palette_hex(arrivals_theme["arriving_index"])
        arrivals_meta = i18n.t(device_config.theme_label(arrivals_safe_id))
    arrivals_panel = _frame_colours_usage_panel_html(
        COLOUR_USAGE_ARRIVALS, i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_ARRIVALS]),
        arrivals_carousel + theme_arriving_error_html)

    effective_calendar = _submitted_or_current(
        submitted, "calendar_theme_id", current_calendar_theme_id)
    calendar_same_checked = not effective_calendar
    calendar_leading_chip = _same_as_departures_chip_html(
        "calendar_theme_id", calendar_same_checked, radio_form_id=SETTINGS_FORM_ID)
    # 27-07-PLAN.md Task 2 (CFG-68): same reasoning as arrivals above —
    # one Python name, built once, read at both the grid's own `id=` and
    # the carousel's `strip_id` argument.
    calendar_grid_attr = 'role="radiogroup" aria-labelledby="%s" id="%s"' % (
        escape_html(FRAME_COLOURS_HEADING_ID), escape_html(THEME_CAROUSEL_STRIP_ID_CALENDAR))
    calendar_grid = _theme_chip_grid_html(
        "calendar_theme_id", effective_calendar,
        extra_class="theme-chip-grid--compact theme-chip-grid--strip",
        chip_extra_class="theme-chip--compact",
        extra_attr=calendar_grid_attr, radio_form_id=SETTINGS_FORM_ID,
        leading_chip_html=calendar_leading_chip)
    calendar_carousel = _theme_carousel_html(calendar_grid, THEME_CAROUSEL_STRIP_ID_CALENDAR)
    calendar_theme_error_html = _field_error_html(errors, "calendar_theme_id", "calendar-theme")
    if calendar_same_checked:
        calendar_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        calendar_dep_hex, calendar_arr_hex = departures_dep_hex, departures_arr_hex
    else:
        calendar_safe_id = (
            effective_calendar if effective_calendar in device_config.THEMES
            else departures_safe_id)
        calendar_theme = device_config.THEMES[calendar_safe_id]
        calendar_dep_hex = _palette_hex(calendar_theme["departing_index"])
        calendar_arr_hex = _palette_hex(calendar_theme["arriving_index"])
        calendar_meta = i18n.t(device_config.theme_label(calendar_safe_id))
    calendar_panel = _frame_colours_usage_panel_html(
        COLOUR_USAGE_CALENDAR, i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_CALENDAR]),
        calendar_carousel + calendar_theme_error_html)

    # D-10: the rules row's own panel — the existing rule list (or the
    # empty state), the existing add form (its own <form>, a legal
    # descendant of this <fieldset> since neither is a <form>), and the
    # "How rules combine" disclosure, relocated verbatim from the
    # retired standalone Flight-colours card — only that outer card and
    # its own heading are gone; every inner piece is unchanged.
    registry = ctx.get("colour_rules")
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    rule_rows = colour_rules.rule_rows(registry)
    rules_caption_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        i18n.t(RULES_SECTION_CAPTION))
    rules_add_form_html = _rule_add_form_html()
    rules_suggestions_html = _rule_suggestion_chips_html(ctx.get("state_dir"))
    rules_how_combine_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_SUMMARY)),
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_BODY)),
    )
    if not rule_rows:
        rules_body_html = (
            '<div class="empty-state-plain"><p class="text-label">%s %s</p></div>'
        ) % (escape_html(i18n.t(RULES_EMPTY_HEADING)), escape_html(i18n.t(RULES_EMPTY_BODY)))
        rules_meta = i18n.t(FRAME_COLOURS_RULES_EMPTY_META)
    else:
        rules_body_html = _rule_list_html(rule_rows)
        rule_count = len(rule_rows)
        if rule_count == 1:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_SINGULAR)
        else:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE) % rule_count
    rules_panel_inner = (
        rules_caption_html + rules_add_form_html + rules_suggestions_html
        + rules_body_html + rules_how_combine_html)
    rules_panel = _frame_colours_usage_panel_html(
        COLOUR_USAGE_RULES, i18n.t(FRAME_COLOURS_ROW_LABELS[COLOUR_USAGE_RULES]),
        rules_panel_inner)

    # The rules row's own swatch: there is no single "current" theme for
    # a whole registry of per-flight rules, so its two dots read a
    # neutral, border-toned value (an existing CSS variable, not a new
    # colour literal) rather than fabricating a false per-flight colour.
    # A function-local variable, not a module constant — this raw CSS
    # token is never real, translatable prose, and test_i18n.py's own
    # D-08 completeness scan only walks module-level ALL_CAPS constants.
    rules_row_swatch_hex = "var(--color-border)"
    rows_data = (
        (COLOUR_USAGE_DEPARTURES, departures_dep_hex, departures_arr_hex, departures_meta),
        (COLOUR_USAGE_ARRIVALS, arrivals_dep_hex, arrivals_arr_hex, arrivals_meta),
        (COLOUR_USAGE_CALENDAR, calendar_dep_hex, calendar_arr_hex, calendar_meta),
        (COLOUR_USAGE_RULES, rules_row_swatch_hex, rules_row_swatch_hex, rules_meta),
    )
    list_items = "".join(
        _frame_colours_row_html(
            usage, usage == COLOUR_USAGE_DEPARTURES,
            i18n.t(FRAME_COLOURS_ROW_LABELS[usage]), meta_text, dep_hex, arr_hex)
        for usage, dep_hex, arr_hex, meta_text in rows_data)

    panels_html = departures_panel + arrivals_panel + calendar_panel + rules_panel

    return (
        '<div class="page-section frame-colours" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<div class="frame-colours__layout">'
        "%s"
        '<div class="frame-colours__assign">'
        '<ul class="frame-colours__list" role="radiogroup" aria-labelledby="%s">%s</ul>'
        "</div>"
        # Phase 21 polish: the usage panels (one chip grid per usage, the
        # rules block) sit in a full-width third grid cell under the
        # preview/rows pair, so the chips flow across the whole card
        # instead of stacking two per row inside the right-hand column.
        '<div class="frame-colours__panels">%s</div>'
        "</div>"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(FRAME_COLOURS_HEADING)),
        escape_html(FRAME_COLOURS_HEADING_ID), escape_html(i18n.t(FRAME_COLOURS_HEADING)),
        escape_html(i18n.t(FRAME_COLOURS_CAPTION)),
        live_preview_html,
        escape_html(FRAME_COLOURS_HEADING_ID), list_items,
        panels_html,
    )


def runway_fieldset(
        current_runway_id, images_available=(), errors=None, submitted=None,
        next_wake_clock=None):
    """D-05: one selectable `.runway-card` per `device_config.RUNWAYS`
    entry (exactly three today), in registry order — the entire card
    (`<label>`) is the hit target, wrapping a visually-hidden (never
    `display:none`) native radio input so keyboard/no-JS selection still
    works natively. `current_runway_id` marks the matching card
    `runway-card--selected`, computed server-side from the same
    membership comparison the radio's own `checked` attribute uses —
    never a client-side `:has()` CSS trick.

    Each card also carries a `runway-card__check` icon-check glyph,
    present in every card's markup — CSS shows it only on the selected
    card via the `runway-card--selected` modifier, so no second
    server-side conditional is needed for the icon itself.

    When `runway_id` is a member of `images_available` (the
    `ctx["runway_images"]` set companion/app.py computes — this module
    never touches the filesystem itself), an `<img>` pointing at the
    session-gated `/runway-image/{id}.png` route is also rendered.
    `images_available` defaults to `()` — "no images available" — the
    safe D-03 fallback, which is also what every pre-06.4 single-argument
    call site still gets. The single muted `RUNWAY_SECTION_CAPTION`
    sentence (quick task 260901-re6) renders once, directly under the
    heading, before the card list.

    The whole return value is wrapped in a single `<div class="theme-status"
    data-dirty-section="Runway">` — the same wrapping idiom
    `theme_fieldset()`'s read-only branch already uses, reused verbatim
    (D-01, 06.6.4.1): the group used to return five flat top-level
    siblings (an `<h2>`, N cards, a `<p>`) with no container at all, which
    was the actual root cause of Settings' broken Runway layout once it
    sat inside a two-column grid. That grid is now deleted, but the
    wrapper stays — it is what makes this group, like Theme and the new
    LED group, a single top-level element `dirty-state.js`'s
    `data-dirty-section` walk can address as one unit, and what carries
    the caption paragraph (`RUNWAY_SECTION_CAPTION`) directly under the
    `<h2 class="text-heading">Runway</h2>` heading.
    The group is named by that `<h2>`, not a `<legend>`, because D-04/D-05
    (06.6.3) already dropped the `<fieldset>` wrapper from both the Theme
    and Runway groups, and a `<legend>` outside a `<fieldset>` is invalid
    markup with no accessible group semantics — `<h2 class="text-heading">`
    is the role the Poll section and the new LED group both use too, so
    every group in this form reads at one consistent heading level.

    The cards themselves are further wrapped in a nested `<div
    class="runway-row">` (quick task 260901-qif), sitting directly after
    the caption paragraph — only the cards go in, the `<h2>` and the `<p>`
    stay outside it. Nothing renders after the row closes (quick task
    260901-re6 retired the trailing helper paragraph that used to sit
    there — the two-paragraph shape this docstring used to describe is
    gone). The cards used to be bare siblings of the heading and both
    paragraphs inside `.theme-status`, so each block-level card took a
    full line and the group rendered as three stacked full-width bars
    instead of the validated row-of-three. The row is a layout container
    only — it carries no visual treatment of its own, and the cards keep
    theirs.

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate the selected card from the
    submission and render `tracked_runway`'s error message once, after
    the card row. `tracked_runway` is a membership-test field, like
    `theme` above — no single radio in the group gains
    `aria-invalid`/`aria-describedby`, for the identical reason
    `theme_fieldset()`'s own docstring already gives.

    19-11-PLAN.md Task 3 (D-12/A-30): the `.runway-row` wrapper itself
    gains `role="radiogroup"` plus `aria-labelledby` (pointing at this
    group's own `<h2>`, `RUNWAY_GROUP_HEADING_ID`) and `aria-describedby`
    (pointing at `RUNWAY_SECTION_CAPTION_ID`'s hint) — the identical
    compatible-with-zero-`<fieldset>` pattern `theme_fieldset()` applies
    to its two chip grids, for the identical reason (see that function's
    own Task 3 docstring paragraph and this file's standing
    fieldset-free-design rationale above).

    Polish fix 4 (D-14c): each radio now also carries an explicit
    `form="{SETTINGS_FORM_ID}"` attribute — the SAME `form=` idiom
    `display_group()`/`quiet_hours_group()` already use for their own
    scheduled inputs (D-19/Pitfall 1). On the legacy SCOPE_ALL render
    (where this group is still a literal descendant of
    `<form id="{SETTINGS_FORM_ID}">`), the attribute is a harmless
    no-op — the browser's explicit `form=` association resolves to the
    exact enclosing form either way. On the Display scope, `render()`
    now renders this group as a SIBLING of `<form id="{SETTINGS_FORM_
    ID}">` (never nested inside it), which is what lets the merged
    Calendar card's own connect/replace `<form>` (21-07-PLAN.md Task 1)
    sit between the Calendar card and this group in document order
    without ever nesting one `<form>` inside another.

    27-05-PLAN.md Task 2 (CFG-66) RETIRED the schematic map 25-03
    (CFG-47) drew into each card: the developer's own review found it
    taught him nothing his own paper schematics did not already
    ("Je comprends pas l'intérêt de ces cartes des pistes, elles
    représentent la même chose que mes schémas."). The map was a drawing
    wrapped around a native radiogroup that already worked, so removing
    it changed NOTHING about the control: the three radios keep their
    `name`, their `value`s, their `class="visually-hidden"` (never
    `display: none`, which would drop them from the tab order and break
    keyboard selection), their `form=` association and their `checked`
    computation; the row keeps `role="radiogroup"`, `aria-labelledby`
    and `aria-describedby` with the same ids. This group ships ZERO
    JavaScript and needs none of 25-01's `.js` gate, exactly as it did
    with the map — a control that needed no enhancement before still
    needs none.

    THE PHOTOGRAPHS STAY, AND STAY WHERE THEY WERE. `images_available`
    is untouched, the session-gated `/runway-image/{id}.png` route is
    untouched, and the three PNGs on disk are untouched. The `<img>`
    keeps its existing slot below the card's number, so
    `.runway-card__image`'s own rule and the two-of-three availability
    behaviour need no edit at all — the map and the photograph always
    answered different questions (where this runway is, and what it
    looks like), and removing the former leaves the latter's slot exactly
    where it was.
    """
    effective_runway_id = _submitted_or_current(
        submitted, "tracked_runway", current_runway_id)
    cards = []
    for runway_id in device_config.RUNWAY_IDS:
        selected = runway_id == effective_runway_id
        checked = " checked" if selected else ""
        card_class = (
            "runway-card runway-card--selected" if selected else "runway-card")
        # 22-10-PLAN.md Task 1 (T10): the badge's own translated text,
        # emitted only on the saved card — the same contract
        # _theme_chip_grid_html() above documents.
        current_attr_html = (
            ' %s="%s"' % (CURRENT_BADGE_ATTR, escape_html(i18n.t(CURRENT_BADGE_LABEL)))
            if selected else "")
        # Polish fix 5 (D-05): device_config.runway_label()'s registry
        # text ("Runway 3 (07/25)", …) is translated at this display
        # site via i18n.t() — the id (runway_id) itself never changes;
        # companion/i18n_fr/registry.py supplies the French entries.
        label = i18n.t(device_config.runway_label(runway_id))
        escaped_id = escape_html(runway_id)
        image_html = ""
        if runway_id in images_available:
            image_html = (
                '<img class="runway-card__image" src="%s%s.png" alt="%s">'
                % (
                    RUNWAY_IMAGE_ROUTE_PREFIX, escaped_id,
                    escape_html(i18n.t(RUNWAY_IMAGE_ALT_TEMPLATE) % label),
                )
            )
        cards.append(
            '<label class="%s"%s>'
            '<input type="radio" name="tracked_runway" value="%s" class="visually-hidden" '
            'form="%s"%s>'
            '<span class="runway-card__number">%s</span>'
            "%s"
            '<span class="runway-card__check">%s<span class="visually-hidden">%s</span></span>'
            "</label>"
            % (
                card_class, current_attr_html,
                escaped_id, SETTINGS_FORM_ID, checked,
                escape_html(label),
                image_html, layout.icon_html("icon-check"),
                escape_html(i18n.t("Selected")),
            )
        )
    runway_error_html = _field_error_html(errors, "tracked_runway", "tracked-runway")
    row_attr = 'role="radiogroup" aria-labelledby="%s"%s' % (
        escape_html(RUNWAY_GROUP_HEADING_ID), _describedby_attr(RUNWAY_SECTION_CAPTION_ID))
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<div class="runway-row" %s>%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t("Runway")),
        escape_html(RUNWAY_GROUP_HEADING_ID),
        escape_html(i18n.t("Runway")),
        escape_html(RUNWAY_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(RUNWAY_SECTION_CAPTION), next_wake_clock)),
        row_attr,
        "".join(cards),
        runway_error_html,
    )


def led_group(current_led_enabled, errors=None, submitted=None, next_wake_clock=None):
    """The Diagnostic LED settings group (D-05, 06.6.4.1): a sibling of the
    Theme and Runway groups inside the single merged `<form
    action="{SETTINGS_ROUTE}">`, wrapped in the same `.theme-status`
    container idiom those two groups use — the `theme-status` class name
    is reused verbatim, not a third wrapper class invented for this group.

    Deliberately carries no `<fieldset>`/`<legend>` of its own, unlike
    the retired pre-06.6.4.1 `led_fieldset()`/`led_section()` pair
    (removed 06.6.4.1-07, D-05: their own separate `POST /config-led`
    route no longer exists either). The old `<fieldset>` existed because
    the LED control used to live in its own independently-submittable
    `<form>`, and a `<legend>` only has accessible-name semantics inside
    a `<fieldset>`. Now that this group
    is a sibling of two `<h2>`-headed groups in one single-column stack
    (Theme's and Runway's own `<fieldset>` wrappers were already dropped
    by D-04/D-05 in 06.6.3), it is named the same way they are — an `<h2
    class="text-heading">` — so all three groups read at one consistent
    heading level, matching the Poll section's own heading role.

    19-11-PLAN.md Task 3 (D-12/A-30): this checkbox has exactly one
    natural DOM element, so it needs no `role="radiogroup"` of its own
    (unlike Theme's two chip grids and the Runway row) — but the
    fieldset-free design this whole file follows stands on the same
    reasoning stated here and at `theme_fieldset()`'s/
    `runway_fieldset()`'s own Task 3 paragraphs: D-12 supplies missing
    group semantics via ARIA attributes (`aria-describedby` here,
    `role="radiogroup"` + `aria-labelledby` there) rather than ever
    reaching for a literal `<fieldset>`/`<legend>`.

    quick task 260901-re6: `LED_SECTION_CAPTION` is a single muted
    caption, styled and positioned identically to Theme's and Runway's
    own captions — directly under the heading, before the control. It
    used to render as an un-muted `<p class="text-label">` AFTER the
    `<label>` instead, which this task fixes; the docstring previously
    asserted it "already renders directly under the heading here", which
    was never true of the shipped markup and is the reason this position
    drift went unnoticed.

    The `<label>` carries `class="settings-checkbox"` (quick task
    260901-qif; a rename of this group's own original checkbox-
    normalization class, by 10-05-PLAN.md Task 2, once the Quiet hours
    group became a second consumer of the identical pattern): unclassed,
    it fell through to the global `input, select`
    rule written for text inputs and selects, painting an oversized 44x44
    filled, bordered, rounded box instead of a normal small checkbox. The
    class scopes a normalization rule that shrinks the checkbox to its
    native 16px size while relocating the 44px touch-target floor onto
    this label — the input's own `type`/`name`/`value`/`checked`
    attribute sequence is untouched.

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate this checkbox's `checked`
    state from the submission (absent-means-unchecked, matching
    `handle_post()`'s own resolution of this exact field) and render its
    "unexpected switch value" error, anchored on the checkbox itself.

    19-11-PLAN.md Task 3 (D-12/A-30): this checkbox — a single-control
    group, unlike Theme/Runway's radio groups above — gains
    `aria-describedby` pointing at `LED_SECTION_CAPTION_ID`'s hint
    directly, via `_field_error_attrs()`'s own `hint_id` parameter;
    combined with any error id in one space-separated value (hint
    first), never a second, competing `aria-describedby`.
    """
    is_on = current_led_enabled is True
    error_html = _field_error_html(errors, "led_enabled", "led-enabled")
    # D-12/A-30's hint-then-error order, preserved across the conversion.
    # The switch describes itself with its own state span first, then the
    # group's caption (the hint the checkbox used to carry through
    # _field_error_attrs()'s hint_id), then the error anchor when there
    # is one — three ids on one attribute, never one overwriting another.
    described_by = QUICK_LED_STATE_ID + " " + LED_SECTION_CAPTION_ID
    if errors and errors.get("led_enabled"):
        described_by = described_by + " led-enabled-error"
    return (
        '<div class="theme-status" %s="%s" %s>'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        '<div class="settings-switch-row">%s%s</div>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(LED_SECTION_HEADING)),
        layout.QUICK_SWITCH_REGION_ATTR,
        escape_html(QUICK_LED_LABEL_ID), escape_html(i18n.t(LED_SECTION_HEADING)),
        escape_html(LED_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(LED_SECTION_CAPTION), next_wake_clock)),
        layout.quick_switch_state_html(
            QUICK_LED_STATE_ID,
            i18n.t(layout.QUICK_ACTION_ON_TEXT), i18n.t(layout.QUICK_ACTION_OFF_TEXT), is_on),
        layout.quick_switch_html(
            "", "", is_on, QUICK_LED_LABEL_ID,
            described_by, form_id=QUICK_LED_FORM_ID),
        error_html,
    )


QUICK_LED_FORM_ID = "quick-led"
QUICK_LED_LABEL_ID = "quick-switch-led-label"
QUICK_LED_STATE_ID = "quick-switch-led-state"


def quick_led_form_html(current_led_enabled):
    """The Diagnostic LED switch's own `<form method="post"
    action="/quick/led">` (D2/CFG-36, 23-07-PLAN.md Task 2) — EMPTY, and
    a sibling of `<form id="{SETTINGS_FORM_ID}">`.

    Exactly `notifications_test_section()`'s shape, for exactly its
    reason: `led_group()` renders INSIDE the settings form, and a
    `<form>` can never nest inside another `<form>` — a browser silently
    drops the inner one, and the switch would then submit the SETTINGS
    form instead. That is not a cosmetic failure: a fetch-driven partial
    `POST /settings` is the precise shape T-23-25/D-12.1 is about. The
    button therefore stays in the card and reaches this element across
    the DOM through `form="{QUICK_LED_FORM_ID}"`, the same cross-DOM
    idiom the save bar and the Send-a-test button already use.

    The action attribute is written as literal path text, not a `%s`
    interpolation of a route constant, matching the established
    convention of every other immediate-action form in this module
    (this module's acceptance gate greps the literal form-action text).

    `return_to` is `layout.DEVICE_ROUTE`: the LED switch renders on the
    Device page and nowhere else. `companion/app.py` validates it by
    MEMBERSHIP against that route's own single-member whitelist before
    ever using it as a redirect target (T-21-12/T-23-24) — this function
    has no opinion on validity, exactly like `frame_strip_html()`.

    The posted `state` is the OPPOSITE of the stored one, so a press with
    scripts blocked switches the LED rather than re-asserting the state
    it is already in. `companion/static/quick-switch.js` keeps that field
    inverted after an optimistic flip; with the script absent, this
    server-rendered value is the whole mechanism.

    `data-quick-switch` is the D-04 handshake both
    `companion/static/dirty-state.js` and
    `companion/static/quick-switch.js` key on. Do not delete it as
    apparently unused from this module's own perspective.
    """
    next_state = (
        layout.QUICK_STATE_OFF if current_led_enabled is True else layout.QUICK_STATE_ON)
    return (
        '<form method="post" action="/quick/led" id="%s" '
        'class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="state" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        "</form>"
    ) % (
        escape_html(QUICK_LED_FORM_ID),
        escape_html(next_state),
        escape_html(layout.DEVICE_ROUTE),
    )


# --- 25-04-PLAN.md Task 1 (CFG-48): the wrapping-midnight arithmetic ---
#
# Settled BEFORE anything is drawn, because the defect it exists to
# prevent is a picture that is confidently wrong: 23:00 to 07:00 is eight
# hours going forward through midnight and sixteen going the other way,
# and an `end - start` implementation draws the sixteen while the card
# says eight. The shipped default window is exactly that case, so this is
# not a boundary somebody might one day reach — it is the value the
# device leaves the factory with.
#
# ONE PARSE DISCIPLINE, NOT TWO. `_normalised_time_html()` below already
# owned an inline `^\d{2}:\d{2}$`; it is lifted to the constant here and
# both read it, so a future loosening cannot apply to the text and not to
# the geometry (or the reverse) — which would be a card whose printed 24h
# sibling and whose drawn arc disagree about what a stored value means.
_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")

QUIET_WINDOW_MINUTES_PER_DAY = 24 * 60

# `start_fraction` and `sweep_fraction` are turns of the ring, in the
# convention companion/draw.py's `unit_point_on_circle()` and
# `unit_circle_dash_array()` already share: 0 at twelve o'clock, growing
# CLOCKWISE. `minutes` is the same span in whole minutes.
#
# The sweep is DERIVED FROM `minutes` inside the one function below and
# nowhere else. That is the whole reason this is a named triple rather
# than two separate helpers: a duration computed here and a sweep
# computed at the drawing site is exactly how a card comes to print
# "8h" beside an arc covering two thirds of the day.
QuietWindowSpan = collections.namedtuple(
    "QuietWindowSpan", "start_fraction sweep_fraction minutes")


def quiet_window_minute_of_day(value):
    """`value` ("HH:MM") as whole minutes since local midnight, or `None`
    when it is not a real time of day. Never raises.

    `None` IS THE "RENDER NOTHING" SIGNAL, matching
    `_normalised_time_html()`'s own omit-don't-fabricate convention
    directly below — an unset or unparseable stored window must draw no
    arc at all rather than a plausible-looking one starting at midnight.
    The values reaching here are already server-validated HH:MM by
    `handle_post()`; this is the second gate, not the first.

    The shape regex alone is not enough and the range check is not
    decoration: `^\\d{2}:\\d{2}$` accepts "99:99", which would become
    minute 5,999 of a 1,440-minute day and send every fraction below off
    the ring.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return None
    hours, minutes = (int(part) for part in str(value).split(":"))
    if hours > 23 or minutes > 59:
        return None
    return hours * 60 + minutes


def quiet_window_span(start_hm, end_hm):
    """The quiet window as a `QuietWindowSpan`, or `None` when either end
    does not parse. Never raises (T-25-04-C: an unparseable stored window
    must not take the whole Display page down).

    ALWAYS FORWARD FROM `start_hm`, THROUGH MIDNIGHT IF NECESSARY, which
    is a modulo and not a subtraction. 23:00 to 07:00 is 480 minutes;
    07:00 to 23:00 is its complement, 960. Both are legitimate windows
    and the pair is what proves direction is honoured rather than
    accidentally symmetric.

    THE THREE DEGENERATE CASES, STATED RATHER THAN DISCOVERED:

      EQUAL START AND END IS A ZERO-LENGTH WINDOW, NOT A WHOLE DAY.
      `server.device_config.seconds_until_quiet_hours_end()` is the
      authority here and its docstring already settles it out loud: "when
      `start_hm == end_hm` the window is zero-width and this always
      returns `None` for every instant - a zero-width window is never
      active, and that is intentional rather than a bug to 'fix' into an
      always-active window." `(end - start) % 1440` returns 0 for that
      input, so this function agrees with the server by construction
      rather than by coincidence, and a check asserts the two agree on a
      shared instant instead of pinning a number in isolation.

      A 24-HOUR WINDOW IS UNREACHABLE THROUGH TWO HH:MM VALUES, and that
      follows from the paragraph above rather than being a separate rule:
      the only pair whose forward distance could be 1440 is a pair with
      equal ends, and that pair is already spoken for as zero. The
      largest window this control can express is therefore 1439 minutes
      (23:59), which is what the dial's own `aria-valuemax` says too.

      AN UNPARSEABLE END RENDERS NOTHING. `None` propagates out of
      `quiet_window_minute_of_day()` and out of here; it is never a zero
      span, because a zero span draws a real (empty) window and would
      claim the device has one configured.
    """
    start = quiet_window_minute_of_day(start_hm)
    end = quiet_window_minute_of_day(end_hm)
    if start is None or end is None:
        return None
    minutes = (end - start) % QUIET_WINDOW_MINUTES_PER_DAY
    return QuietWindowSpan(
        start / float(QUIET_WINDOW_MINUTES_PER_DAY),
        minutes / float(QUIET_WINDOW_MINUTES_PER_DAY),
        minutes)


def _normalised_time_html(value):
    """B14 (22-AUDIT.md, 22-10-PLAN.md Task 2): the normalised 24h value
    rendered as a VISIBLE sibling beside a native `<input type="time">`.

    A native time control formats itself from the browser's own locale,
    so a browser in en-US renders the stored "23:00" as "11:00 PM" —
    directly beside a preset button this same group labels
    "Night (23:00-07:00)". One value, two notations, no way to tell they
    are the same. The audit's fix is to SHOW the stored 24h text; this is
    it.

    Not a placeholder (a time input never shows one) and not a `title`
    (invisible until hovered, and unreachable by touch) — a real, visible
    element, which is what the fix column asks for.

    `aria-hidden`: the input's own value is already announced natively,
    in the user's own notation, by the control itself. Repeating it in
    the accessibility tree would announce the same value twice with no
    added information. The visual duplication is the whole point of this
    element and the aural duplication is not.

    Renders nothing at all for a falsy/unparseable value rather than
    fabricating one, matching this file's "omit, don't fabricate"
    convention. The value is already server-validated HH:MM by
    `handle_post()`; this only ever echoes it back.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return ""
    return ' <span class="text-label field-inline-value" aria-hidden="true">%s</span>' % escape_html(
        value)


# --- 25-04-PLAN.md Task 2 (CFG-48): the server-drawn 24 h ring --------
#
# Class names as constants rather than literals at the emission site: a
# class that exists in Python and nowhere in companion/static/style.css
# paints nothing at all, and a check scans the EMITTED markup's classes
# against the stylesheet for exactly that.
QUIET_DIAL_CLASS = "quiet-dial"
QUIET_DIAL_RING_CLASS = "quiet-dial__ring"
# The full circumference: the whole 24 hours, always drawn.
QUIET_DIAL_DAY_CLASS = "quiet-dial__day"
# The quiet window itself, drawn on top of the day.
QUIET_DIAL_ARC_CLASS = "quiet-dial__arc"
QUIET_DIAL_HOUR_CLASS = "quiet-dial__hour"
QUIET_DIAL_READOUT_CLASS = "quiet-dial__readout"

# User units, and CSS pixels — the aspect-locked `unit_*` scheme
# companion/draw.py documents, with an explicit intrinsic size so the
# <svg> can never fall back to the format's own 300x150 default.
QUIET_DIAL_SIZE = 176
# Chosen so the arithmetic below lands on whole numbers: 176 - 14 - 3 = 78,
# i.e. QUIET_DIAL_SIZE // 2 - QUIET_DIAL_STROKE // 2 - QUIET_DIAL_CLEARANCE.
# A radius carrying a rounding tail would make every recomputed-from-the-
# markup check invent a tolerance to hide it. (27-02-PLAN.md: this comment
# used to read "64 - 7 - 3 = 54", a stale figure from before the ring grew
# to its current 176px size — the arithmetic and the shipped radius were
# always correct, only the comment beside them was not.)
QUIET_DIAL_STROKE = 14
# Clear space between the stroke's OUTER edge and the viewBox edge. A
# stroked arc extends half its stroke width past the nominal radius,
# which is the usual way a ring clips itself on its own box.
QUIET_DIAL_CLEARANCE = 3
QUIET_DIAL_RADIUS = QUIET_DIAL_SIZE // 2 - QUIET_DIAL_STROKE // 2 - QUIET_DIAL_CLEARANCE

# --- 27-02-PLAN.md Task 1/2 (CFG-62): THE PAIR SEAM's three property
# names, decided here because every property name value-controls.js's
# generic pair seam reads or writes is a SERVER decision — the same
# reason FIELD_ATTR/GEOMETRY_ATTR/FORMAT_ATTR's values are decided in
# companion/layout.py rather than invented in the script that consumes
# them. `QUIET_DIAL_PAIR_ATTR`'s own VALUE is the name of the derived
# sweep property — value-controls.js's `paintSweep()` writes the sweep
# under whatever name the ancestor's own marker attribute carries, so
# there is exactly one place this name is chosen.
QUIET_DIAL_PAIR_ATTR = "data-value-pair"
QUIET_DIAL_PAIR_PROPERTY_ATTR = "data-value-pair-property"

# A DICT rather than three separate top-level ALL-CAPS names, and that
# is not stylistic: a top-level string CONSTANT whose value begins with
# "--" trips companion/test_i18n.py's D-05 scan — measured, running the
# full suite after this task's first draft named them
# QUIET_DIAL_START_FRACTION_PROPERTY et al. A leading "--" is not a
# valid identifier start, so rule (a)'s lowercase-identifier exclusion
# (which the FIELD_ATTR-shaped constants above all rely on) never
# reaches it; companion/layout.py's own FRACTION_PROPERTY comment
# already records this exact trap as the reason NO Python constant
# exists there for "--value-fraction" at all. A DICT VALUE is scanned
# under a narrower, SEPARATE exclusion (hyphenated-lowercase-identifier)
# that DOES reach a leading "--" — companion/layout.py's own
# `{"ok": "--ok", "warn": "--warn", "error": "--error"}` dict already
# relies on exactly this path. So the one constant this plan's own
# acceptance bar asks for ("the three property names exist as module
# constants, not as literals at the call site") lives here, as three
# dict values under one name, rather than as three names the scanner
# cannot tell apart from prose.
QUIET_DIAL_PAIR_PROPERTIES = {
    "start": "--quiet-start-fraction",
    "end": "--quiet-end-fraction",
    "sweep": "--quiet-sweep-fraction",
}

# The four anchor hours, and four rather than twenty-four on purpose.
# These are the quarter turns: they are the only hours whose position a
# reader resolves at a GLANCE rather than by counting round from one that
# is labelled, and twenty-four labels on a 128px ring is illegible at the
# 360px contract floor either way. 00 is the one that has to be there —
# the whole defect this control's arithmetic exists to prevent is about
# what happens at midnight, so midnight is marked.
#
# Each hour is PAIRED with the modifier class that places it rather than
# templated from a single "quiet-dial__hour--%d" constant. That is not a
# stylistic choice: companion/test_i18n.py strips a literal's format
# specs before deciding whether it is a bare identifier, so the templated
# form reads to the D-05 scanner as untranslated user-facing copy and
# fails Check 1 — measured on this tree. A class name is not copy, and
# the paired form is the shape that says so.
QUIET_DIAL_LABELLED_HOURS = (
    (0, "quiet-dial__hour--0"),
    (6, "quiet-dial__hour--6"),
    (12, "quiet-dial__hour--12"),
    (18, "quiet-dial__hour--18"),
)

# "23:00 → 07:00 · 8h". No letters of its own (the duration's unit comes
# from layout.duration_text(), which speaks both languages), so it needs
# no catalogue entry — see quiet_dial_readout_html() below.
QUIET_DIAL_READOUT_TEMPLATE = "%s → %s · %s"

# A full turn in degrees, and the quarter turn that moves <circle>'s own
# three-o'clock dash origin to twelve o'clock — the same correction
# companion/draw.py's ring_gauge() applies, restated here because this
# drawing additionally rotates by the window's own start.
_QUIET_DIAL_FULL_TURN_DEG = 360.0
_QUIET_DIAL_TWELVE_OCLOCK_DEG = -90.0


def quiet_dial_svg(span):
    """The 24 h ring as one `<svg>`: a full-circumference day, plus the
    quiet arc when `span` describes one. Never raises.

    SERVER-DRAWN, AND THAT IS THE POINT OF THE WHOLE CONTROL. With
    scripts blocked the visitor still sees a correct picture of the saved
    window — only the DRAGGING is script, and only the dragging is behind
    the `.js` gate. A dial whose arc needed a script would be a card that
    renders an empty ring to anybody whose script failed.

    `span` is `quiet_window_span()`'s return value, which already decided
    the wrap; this function does no window arithmetic of its own and must
    not grow any. The arc's sweep is `span.sweep_fraction` and its start
    is `span.start_fraction`, both read straight off the one triple, so
    the drawing cannot disagree with the duration printed beside it.

    NO ARC AT ALL for `span is None` (nothing parseable is stored) and
    for a zero-length window. Those are two different facts with the same
    drawing, and that is correct: neither is a window, and neither may be
    drawn as one. The empty-dash case is refused for
    `ring_gauge()`'s own recorded reason — a zero-length dash renders as
    a DOT under a round cap, so "no window" would read as "a few
    minutes".

    THE DASH ROUTE, NOT AN ARC PATH, again following `ring_gauge()`: an
    arc <path> whose sweep is the whole circle is degenerate in SVG and
    draws nothing. This control cannot reach a full turn (see
    `quiet_window_span()`'s docstring), but the dash route also needs no
    large-arc-flag reasoning and no trigonometry, and
    `draw.unit_circle_dash_array()` already owns it.

    `aria-hidden="true" focusable="false"`, and hand-written rather than
    `draw.unit_canvas()` for the one reason: that helper emits the
    viewBox, the intrinsic size and `aria-hidden`, but not `focusable`.
    Every SHAPE still comes from
    draw.py's own primitives, so the escaping and the
    refuse-a-paint-decided-in-Python guard apply to all of them.

    Both shapes carry `fill="none"` as a presentation ATTRIBUTE: a
    stroked circle with no fill declared takes the format's default
    black, which is a filled black disc over the middle of the card.
    `stroke-width` is a presentation attribute too, and deliberately not
    a stylesheet declaration — a CSS stroke-width of any specificity
    beats a presentation attribute, which would flatten the geometry the
    constants above derive.

    27-02-PLAN.md Task 2 (CFG-62): the `.js`-scoped stylesheet rule that
    overrides this circle's `stroke-dasharray`/`transform` once script is
    running reads the SAME `QUIET_DIAL_RADIUS` this function divides by
    — via `--quiet-dial-radius`, the custom property the handle's own
    transform already reads (companion/static/style.css) — rather than
    a `pathLength="1"` attribute. `pathLength="1"` was tried first and
    measured, not assumed, to be the wrong shape here: with this
    circle's dasharray left in real user units (the STATED requirement
    below — the presentation attribute is the saved value and the no-JS
    floor, and must not change), adding `pathLength="1"` reinterprets
    those same numbers on a SECOND, pathLength-scaled coordinate system
    and a headless-browser measurement of this exact ring painted a
    second, spurious dash on the far side of it. `stroke-dasharray`/
    `transform` are UNCHANGED here either way: they are still the saved
    value, computed the same way, and still what a scripts-blocked
    visitor sees. See companion/static/style.css's own comment beside
    the override rule for the full measurement.
    """
    centre = QUIET_DIAL_SIZE // 2
    shapes = [draw.circle(QUIET_DIAL_DAY_CLASS, centre, centre, QUIET_DIAL_RADIUS, attrs={
        "fill": "none",
        "stroke-width": QUIET_DIAL_STROKE,
    })]
    if span is not None and span.minutes > 0:
        shapes.append(draw.circle(
            QUIET_DIAL_ARC_CLASS, centre, centre, QUIET_DIAL_RADIUS, attrs={
                "fill": "none",
                "stroke-width": QUIET_DIAL_STROKE,
                "stroke-dasharray": draw.unit_circle_dash_array(
                    span.sweep_fraction, QUIET_DIAL_RADIUS),
                # Twelve o'clock plus the window's own start, clockwise —
                # <circle>'s dash origin is three o'clock and grows
                # clockwise already.
                "transform": "rotate(%.4f %d %d)" % (
                    _QUIET_DIAL_TWELVE_OCLOCK_DEG
                    + _QUIET_DIAL_FULL_TURN_DEG * span.start_fraction,
                    centre, centre),
            }))
    return (
        '<svg class="%s" viewBox="0 0 %d %d" width="%d" height="%d" '
        'aria-hidden="true" focusable="false">%s</svg>'
    ) % (
        escape_html(QUIET_DIAL_RING_CLASS), QUIET_DIAL_SIZE, QUIET_DIAL_SIZE,
        QUIET_DIAL_SIZE, QUIET_DIAL_SIZE, "".join(shapes),
    )


def quiet_dial_html(span, handles_html=""):
    """The ring and its four anchor-hour labels, as one positioned block.

    THE LABELS ARE HTML OUTSIDE THE `<svg>`, NOT `<text>` INSIDE IT, and
    that is structural rather than stylistic: companion/draw.py's
    drawing contract owes a viewBox that contains the bounding box of any
    text drawn inside it, and the only honest way to prove that in this
    codebase is a real browser measurement. Keeping the labels out of the
    canvas makes the defect unreachable by construction, and keeps them
    at a constant CSS size instead of scaling with the box — the same
    reason `draw.label_span()`'s own docstring gives.

    `handles_html` is the `.js`-gated handle layer (25-04 Task 3) and is
    empty for every caller that has none. It is rendered LAST so document
    order is paint order: the handles sit above the ring they steer.

    27-02-PLAN.md Task 2 (CFG-62): THE PAIR SEAM'S SHARED ANCESTOR. This
    `<div>` is where the two handles' own fractions get published a
    second time (see `quiet_dial_handles_html()`), and where their
    derived sweep lands — `QUIET_DIAL_PAIR_ATTR`'s own VALUE names that
    third property, so value-controls.js's generic pair seam writes it
    under whatever name THIS FUNCTION chose, never a name of its own
    invention. The three fractions are computed from the SAME `span`
    triple `quiet_dial_svg()` draws from — no second window arithmetic
    anywhere — so at rest the CSS-driven geometry and the presentation-
    attribute geometry describe the identical picture. `span is None`
    (nothing parseable stored) carries none of this: there is no pair to
    publish for a window that does not exist.
    """
    hours_html = "".join(
        '<span class="text-label %s %s" aria-hidden="true">%02d</span>' % (
            escape_html(QUIET_DIAL_HOUR_CLASS), escape_html(modifier_class), hour)
        for hour, modifier_class in QUIET_DIAL_LABELLED_HOURS)
    pair_attrs = ""
    if span is not None:
        end_fraction = (span.start_fraction + span.sweep_fraction) % 1.0
        pair_attrs = (
            ' %s="%s" style="%s: %.6f; %s: %.6f; %s: %.6f;"'
        ) % (
            QUIET_DIAL_PAIR_ATTR, escape_html(QUIET_DIAL_PAIR_PROPERTIES["sweep"]),
            QUIET_DIAL_PAIR_PROPERTIES["start"], span.start_fraction,
            QUIET_DIAL_PAIR_PROPERTIES["end"], end_fraction,
            QUIET_DIAL_PAIR_PROPERTIES["sweep"], span.sweep_fraction,
        )
    return '<div class="%s"%s>%s%s%s</div>' % (
        escape_html(QUIET_DIAL_CLASS), pair_attrs, quiet_dial_svg(span), hours_html, handles_html)


# --- 25-04-PLAN.md Task 3 (CFG-48): the two handles, gated ------------
#
# Everything below renders INSIDE 25-01's `.js` gate and nothing else
# does. The ring, the readout, the three presets and both time inputs
# all survive with scripts blocked; only the dragging is script, and
# only the dragging is hidden when script does not run.
QUIET_DIAL_HANDLE_LAYER_CLASS = "quiet-dial__handles"
QUIET_DIAL_HANDLE_CLASS = "quiet-dial__handle"
# The box value-controls.js measures the pointer angle against. It is the
# ring's own square, so the angle is measured about the ring's centre.
QUIET_DIAL_HANDLE_TRACK_CLASS = "quiet-dial__handle-track"

# The steering range, in minutes since local midnight.
#
# THE MAXIMUM IS 1439, NOT 1440, and the difference is a real one: 1440
# would make 00:00 and "24:00" two values for one instant, and the End
# key would write a time no <input type="time"> accepts. 1439 is 23:59 —
# the last minute of the day — and `clampToStep()`'s round-then-clamp
# order reaches it exactly even though it is not on a step boundary.
QUIET_DIAL_HANDLE_MIN = 0
QUIET_DIAL_HANDLE_MAX = QUIET_WINDOW_MINUTES_PER_DAY - 1

# THE KEYBOARD MODEL, AND IT IS THE NATIVE <input type="range"> ONE
# RATHER THAN A NEW INVENTION. value-controls.js owns it: arrows move one
# step, Page keys move ten steps, Home and End go to the two ends. With
# this step that is arrows ±15 min, Page ±150 min and Home/End to
# 00:00/23:59.
#
# 25-04-PLAN.md's own behaviour line asked for Page ±60. It is ±150 here,
# deliberately, because the same plan's binding constraint — "it must
# match the native <input type="range"> model 25-05 will inherit" — is
# the stronger of the two, and the two cannot both hold: ten steps of 15
# minutes is 10.4% of the day, which is exactly what a native range
# control's Page keys do. A per-control page size would have been a
# second keyboard model on the second settings page, which is the drift
# this phase's one script exists to prevent.
QUIET_DIAL_HANDLE_STEP = 15

# The two ends, each with the field it steers and the accessible name
# that says WHICH end it is. aria-valuetext carries the time itself and
# nothing else (layout.VALUE_CONTROL_TEXT_TOKEN alone, no sentence around
# it): a screen reader reading "one thousand three hundred and eighty"
# instead of "23:00" is the whole reason aria-valuetext exists, and
# repeating the label on every arrow press is noise, not information.
QUIET_DIAL_START_LABEL = "Quiet hours start"
QUIET_DIAL_END_LABEL = "Quiet hours end"


def quiet_dial_handle_fraction(minute):
    """`minute` as the 0..1 fraction of a turn the stylesheet positions
    the handle from — and DELIBERATELY the same formula
    value-controls.js's own `paint()` uses, `(value - min) / (max - min)`,
    rather than the `minute / 1440` the arc is drawn from.

    The two differ by at most 0.25 degrees (1439/1440 of a turn against
    1439/1439 at the far end), which is a quarter of a pixel at this
    ring's radius. Matching the script exactly is worth that: the server
    paints the handle once and the script repaints it on every step, and
    two formulas that agree in theory are how a handle comes to JUMP
    imperceptibly on the first arrow press and then never quite line up
    with the arc it is steering.
    """
    return minute / float(QUIET_DIAL_HANDLE_MAX)


def quiet_dial_handles_html(start_hm, end_hm):
    """The two drag handles, each in its own `.js`-gated wrapper.

    EACH HANDLE IS A REAL `<button type="button">`, never a bare `<div>`.
    A button is focusable, activatable and announced with no ARIA at all;
    everything below only refines it. `type="button"` because a bare
    `<button>` inside a form defaults to submit, and a handle that posted
    the settings form on Enter would save on a keystroke meant to adjust
    a value.

    DRIVEN FROM THE TWO NATIVE INPUTS, NEVER FROM STATE OF ITS OWN. The
    server renders each handle's position from the same effective value
    the matching input is populated with, and value-controls.js re-reads
    that input on every steer. That is what makes the three existing
    presets move the handles with no code at all — they already write
    into these two fields — and it is the cheapest available proof that
    there is one source of truth.

    NO HANDLE AT ALL for an end that does not parse: a handle at a
    fabricated position claims a value that was never set, which is the
    same omit-don't-fabricate rule `_normalised_time_html()` and
    `quiet_dial_svg()` already follow.

    WHEN THE TWO ENDS ARE CLOSE ENOUGH TO OVERLAP, WHICH IS A DECISION
    AND NOT AN EMERGENT BEHAVIOUR:

      * There is NO minimum separation in the value. A zero-length window
        is a real, defined state — `server.device_config`'s own
        arithmetic calls it never-active and means it — and refusing it
        here would make a state reachable by typing unreachable by
        dragging, which is a worse card, not a safer one.
      * Z-ORDER IS DOCUMENT ORDER, and document order is paint order in
        HTML: the END handle is emitted second and therefore sits above
        the start handle. Neither carries a `z-index`.
      * SO THE END HANDLE WINS A POINTER-DOWN IN THE OVERLAP. That is
        sufficient rather than arbitrary: recovering from an overlap
        needs only ONE end to be draggable, and moving it separates the
        pair, after which both are independently grabbable again. The
        start handle is never unreachable meanwhile — it stays its own
        tab stop whatever it is painted under, and both times stay
        typable in the two native inputs below.
      * The separation at which BOTH handles are independently grabbable
        is a measured consequence of the shared 44px hit target rather
        than a number chosen here: the targets stop overlapping at about
        22px of chord, which on this ring is about 94 minutes.
        companion/test_browser_ux.py measures both handles at a window
        narrower than that and records the result.
    """
    handles = []
    for value, field, label, pair_property in (
            (start_hm, "quiet_hours_start", QUIET_DIAL_START_LABEL,
             QUIET_DIAL_PAIR_PROPERTIES["start"]),
            (end_hm, "quiet_hours_end", QUIET_DIAL_END_LABEL,
             QUIET_DIAL_PAIR_PROPERTIES["end"])):
        minute = quiet_window_minute_of_day(value)
        if minute is None:
            continue
        handles.append((
            '<div class="value-control %s %s" %s %s="%s" %s="%s" %s="%d" %s="%d" %s="%d"'
            ' %s="angular" %s="%s" %s="%s" %s="%s" style="--value-fraction: %.6f">'
            '<span class="value-control__track %s" %s></span>'
            '<button type="button" class="value-control__handle control-hit-area %s" %s'
            ' role="slider" aria-valuemin="%d" aria-valuemax="%d" aria-valuenow="%d"'
            ' aria-valuetext="%s" aria-label="%s"></button>'
            "</div>"
        ) % (
            escape_html(QUIET_DIAL_HANDLE_LAYER_CLASS), escape_html(layout.JS_GATE_CLASS),
            layout.VALUE_CONTROL_ATTR,
            layout.VALUE_CONTROL_FIELD_ATTR, escape_html(field),
            layout.VALUE_CONTROL_FORM_ATTR, escape_html(SETTINGS_FORM_ID),
            layout.VALUE_CONTROL_MIN_ATTR, QUIET_DIAL_HANDLE_MIN,
            layout.VALUE_CONTROL_MAX_ATTR, QUIET_DIAL_HANDLE_MAX,
            layout.VALUE_CONTROL_STEP_ATTR, QUIET_DIAL_HANDLE_STEP,
            layout.VALUE_CONTROL_GEOMETRY_ATTR,
            layout.VALUE_CONTROL_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
            layout.VALUE_CONTROL_TEXT_ATTR, escape_html(layout.VALUE_CONTROL_TEXT_TOKEN),
            # 27-02-PLAN.md Task 2 (CFG-62): THE PAIR SEAM. Names which of
            # quiet_dial_html()'s ancestor properties this handle
            # publishes its own fraction under — the ancestor itself is
            # the nearest ancestor carrying QUIET_DIAL_PAIR_ATTR, found by
            # value-controls.js's existing ancestorWith().
            QUIET_DIAL_PAIR_PROPERTY_ATTR, escape_html(pair_property),
            quiet_dial_handle_fraction(minute),
            escape_html(QUIET_DIAL_HANDLE_TRACK_CLASS), layout.VALUE_CONTROL_TRACK_ATTR,
            escape_html(QUIET_DIAL_HANDLE_CLASS), layout.VALUE_CONTROL_HANDLE_ATTR,
            QUIET_DIAL_HANDLE_MIN, QUIET_DIAL_HANDLE_MAX, minute,
            escape_html(value), escape_html(i18n.t(label)),
        ))
    return "".join(handles)


# 28-03-PLAN.md Task 1 (CFG-73 Bug A): layout.DURATION_ATTRS' own four
# English wordings, in the SAME s/m/h/d order — quiet_dial_readout_html()
# below zips this against that tuple so the attribute name and its
# translated wording are always written together.
_QUIET_DIAL_DURATION_TEXTS = (
    layout.DURATION_SECONDS_TEXT, layout.DURATION_MINUTES_TEXT,
    layout.DURATION_HOURS_TEXT, layout.DURATION_DAYS_TEXT,
)


def quiet_dial_readout_html(start_hm, end_hm, span):
    """"23:00 → 07:00 · 8h" — the window in words, or nothing at all when
    `span` is None.

    `aria-hidden="true"`, AND THAT IS THE SAME REASONING
    `_normalised_time_html()` ABOVE ALREADY RECORDS, written out here so
    a later reader does not "fix" it into a live region. Both time inputs
    announce their own values natively, in the visitor's own notation;
    repeating them here would say the same thing twice with nothing
    added. The visual duplication is this element's whole job and the
    aural duplication is not.

    IT IS SPECIFICALLY NOT A `role="status"` / `aria-live` REGION, and
    that is CFG-52 rather than a preference. Dragging a handle fires
    continuously, and a live region would re-announce the identical
    phrase on every step — the exact defect Phase 23 hit with its three
    switches. The focused handle's own `aria-valuetext` is the native,
    debounced announcement path and it is enough.

    The duration comes from `layout.duration_text()`, this app's ONE
    length-of-time ladder, rather than a second set of boundaries
    invented here. It is COARSE by construction — it names the largest
    unit that fits, so a 90-minute window reads "1h" — and that is
    accepted rather than worked around: the two exact endpoints are
    printed immediately beside it, and a second duration ladder in a page
    module is precisely the drift that ladder exists to prevent.

    Escaped once, after formatting, matching this file's
    "translate first, escape once" convention. Both times are already
    known to be real HH:MM here (a `span` exists), so this escaping is
    the convention holding rather than a live need — T-25-04-B.

    27-02-PLAN.md Task 3 (CFG-62): THREE CHILDREN, NOT ONE TEXT NODE, so
    the sentence can follow the pair the way the arc now does. AT REST
    (this function's own return value, always) the visible text is
    BYTE-IDENTICAL to what shipped before this task — the paragraph's
    class and `aria-hidden` are unchanged and the three children,
    concatenated with the same " → "/" · " connectors the old
    single template used, spell out exactly the same sentence.

    THE TWO ENDPOINTS carry the existing `data-value-readout` seam,
    named by the field whose handle moves them (`quiet_hours_start`/
    `quiet_hours_end`), with a bare token template — so they follow the
    handles for free, through the shipped mechanism, substituting the
    one number value-controls.js already reads back off each field.
    Nothing here writes copy: the substituted value is a number, and the
    template holding its place is server-rendered. **28-03-PLAN.md
    Task 1 (CFG-73 Bug A)** additionally marks both endpoint spans
    `data-value-readout-format="clock"` — the readout-scoped sibling of
    the wrapper's own `data-value-format="clock"` — so
    `value-controls.js`'s `paintReadouts()` substitutes zero-padded
    "HH:MM" through the SAME codec the native time input already uses
    (`numberToField()`'s own formatting body) rather than the raw
    minute-of-day number it used to write.

    THE DURATION CHILD — SUPERSEDED 28-03-PLAN.md Task 1 (CFG-73 Bug A).
    Kept below, legible, because it explains a real decision this task
    inverts on purpose rather than by accident:

        "THE DURATION CHILD NEVER SHOWS A SCRIPT-COMPUTED SENTENCE, and
        this is the honesty contract (D18's battery gauge, applied to a
        different sentence) made structural rather than trusted: its own
        `data-value-readout-text` is the EMPTY template. paintReadouts()'s
        shipped substitution therefore always resolves to "" the moment
        this element is next painted — whether or not the pair still
        matches `data-value-readout-base` — which is deliberately the
        SAFE side of the "blanks when equal to base" rule this seam was
        built for (25-05-PLAN.md Task 2): that rule blanks a sentence
        when nothing changed (a comparison against itself is noise) and
        shows one once something did, which is the OPPOSITE of what a
        duration that cannot be recomputed in script needs. An empty
        template makes both of that rule's branches resolve to ""
        rather than ever risking the SHOWN branch substituting a bare,
        unrelated minute count where a duration phrase belongs.
        `data-value-readout-base` is still recorded, both because a
        later, smarter blank-only-when-different rule could read it and
        because CFG-62's own acceptance bar asks for it; today it is
        inert given the empty template, and that is written here rather
        than left for a reader to have to prove. The server RE-RENDERS
        the true figure on the very next load, which is the only path
        back to a stated duration."

    WHAT REPLACED IT: the developer's own report (28-CONTEXT.md,
    CFG-73) is that the empty template's honesty came at too high a
    cost — a permanently blank duration after any interaction reads as
    "still buggy", not as honest. The fix is not to let the client
    invent a sentence; it is to hand the client the SAME ladder's own
    words, already translated, the way `relative-time.js`'s ticker has
    carried its four bucket wordings since Phase 23. The duration span
    below now carries all four `layout.DURATION_ATTRS`, each filled with
    `i18n.t()` of the matching `layout.DURATION_*_TEXT` wording —
    `value-controls.js` substitutes a quantity into whichever one
    `_age_bucket()`'s own boundaries select and writes no language logic
    of its own. `data-value-readout-base` stops being inert: the pair
    seam it names is exactly what the client-side duration is computed
    from. `data-value-readout-text` is no longer emitted on this span at
    all — there is nothing left for it to hold an empty value for. The
    span's own VISIBLE, server-rendered content is unchanged: still
    `layout.duration_text(span.minutes * 60)`, still byte-identical to
    what shipped before this task, so a fresh load or a scripts-blocked
    page reads exactly as it always has.
    """
    if span is None:
        return ""
    duration_attrs_html = "".join(
        ' %s="%s"' % (attr, escape_html(i18n.t(text)))
        for attr, text in zip(layout.DURATION_ATTRS, _QUIET_DIAL_DURATION_TEXTS))
    return (
        '<p class="time-value %s" aria-hidden="true">'
        '<span %s="quiet_hours_start" %s="%s" %s="%s">%s</span>'
        ' → '
        '<span %s="quiet_hours_end" %s="%s" %s="%s">%s</span>'
        ' · '
        '<span %s="quiet_hours_start" %s="%d"%s>%s</span>'
        "</p>"
    ) % (
        escape_html(QUIET_DIAL_READOUT_CLASS),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(start_hm),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_FORMAT_ATTR, escape_html(layout.VALUE_CONTROL_FORMAT_CLOCK),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(layout.VALUE_CONTROL_TEXT_TOKEN), escape_html(end_hm),
        layout.VALUE_CONTROL_READOUT_ATTR,
        layout.VALUE_CONTROL_READOUT_BASE_ATTR, quiet_window_minute_of_day(start_hm),
        duration_attrs_html,
        escape_html(layout.duration_text(span.minutes * 60)),
    )


def quiet_hours_group(current_start, current_end, errors=None, submitted=None, delay_sentence=None):
    """The Quiet hours settings group (10-05-PLAN.md, 10-UI-SPEC.md;
    restructured by 20-07-PLAN.md Task 2, D-19/Pitfall 1; its own on/off
    checkbox retired outright by 22-05-PLAN.md Task 1, X1/D-04/D-12.1):
    this card is a SIBLING of `<form id="{SETTINGS_FORM_ID}">`, never a
    literal descendant. Both time inputs keep submitting with the shared
    Save via a `form="{SETTINGS_FORM_ID}"` attribute on each, the same
    cross-DOM idiom Runway's own radios and the screen-type `<select>`
    already use.

    Same `.theme-status` wrapper idiom, same `<h2 class="text-heading">`
    naming as before this task (no `<fieldset>`/`<legend>`, for the
    identical reason `led_group()`'s own docstring already documents).

    Controls render in this locked order: heading, caption, the three
    presets, then a "Start" `<input type="time">`, then an "End"
    `<input type="time">`, each its own full-width line. They are
    deliberately NOT wrapped in `.theme-status__row` or any other
    side-by-side layout — 10-UI-SPEC.md rejects that explicitly, both to
    avoid two native time pickers wrapping at a narrow (320-375px)
    viewport and to stay consistent with 06.6.4.1 (D-01)'s removal of this
    page's two-column grid.

    22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the `current_enabled`/
    `quiet_hours_enabled` checkbox this function used to render here is
    gone outright — the Frame strip is now the ONLY control for turning
    Quiet hours on or off (T-22-16), matching Screen on/off's own fate
    (`display_group()`, retired in the same commit). Neither time input
    is ever given a `disabled` attribute tied to that on/off state — they
    stay fully interactive regardless, resolving 10-RESEARCH.md's Open
    Question 2 / Assumption A1 in the affirmative: a user can
    pre-configure a window whether or not Quiet hours is currently on.
    `handle_post()`'s own `quiet_hours_enabled` resolution is unaffected
    by this markup change — it already treats an absent field as "leave
    unchanged" (D-12.1), so removing this checkbox does not, by itself,
    change what an unrelated settings save persists.

    22-05-PLAN.md Task 2 (D-04): `delay_sentence` is one fully i18n.t()-
    translated, already-clock-formatted sentence — the caller (`render()`)
    computes it once from `wake.next_wake_status()`'s own triple via
    `companion.frame_state.delay_sentence_template()`, the SAME triple the
    Frame strip's own captions read (22-04-PLAN.md), so the two can never
    disagree. Appended as the caption's own second sentence, replacing
    the retired "Applies on the next scheduled poll, which may now be
    hours away" wording with a real computed time. Defaults to `None`,
    which degrades to `frame_state.DELAY_UNKNOWN`'s own translated text —
    the same degrade every direct call site that does not pass this
    keyword (a page load with no computed wake data at all) already
    needs.

    Every interpolated current value — the heading, the caption, and
    both current times — is routed through `escape_html()`, matching
    this file's universal escaping discipline.

    19-07-PLAN.md Task 2 (D-07/A-25): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate both time controls from the
    submission and render each field's own error message directly after
    it. Both time inputs additionally gain a `required` attribute — a
    client-side convenience only (D-07's explicit instruction); the
    server-side HH:MM gate `handle_post()` runs before this render is
    ever reached is the real control.

    19-10-PLAN.md (D-14/S-04): three `type="button"` presets (Night, Work
    day, Always on) render between the caption and the Start input — a
    CLIENT-SIDE affordance only, with NO server change. Each button
    carries `data-preset-start`/`data-preset-end`/`data-preset-enabled`
    attributes that `companion/static/dirty-state.js` reads and writes
    into this same form's `quiet_hours_start`/`quiet_hours_end` fields
    (and, when a `quiet_hours_enabled` element still exists in the DOM —
    it no longer does on this page — the Always-on preset's own
    `data-preset-enabled="0"`) — `handle_post()`'s validation of the two
    time fields is completely untouched. On a no-JS browser the three
    buttons are simply inert (they carry no `type="submit"`, so they
    cannot even accidentally submit the form); both time inputs remain
    fully usable either way, an acceptable degradation matching this
    page's established graceful-degradation convention.

    27-08-PLAN.md Task 1 (CFG-69): the `<h2>` now carries
    `id="{QUIET_HOURS_GROUP_HEADING_ID}"` — a fragment target for the
    Frame strip's own Quiet hours caption link (companion/layout.py's
    frame_strip_html(), Task 2 of the same plan), the same "id on the
    group's own heading" convention `runway_group()` already uses. Not a
    control and not part of anything that posts.
    """
    # 19-11-PLAN.md Task 3 (D-12/A-30): the group's single hint links to
    # BOTH time inputs (there is no separate per-field hint for Start vs
    # End) via `_field_error_attrs()`'s `hint_id` parameter.
    effective_start = _submitted_or_current(submitted, "quiet_hours_start", current_start)
    start_error_attrs = _field_error_attrs(
        errors, "quiet_hours_start", "quiet-hours-start", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    start_error_html = _field_error_html(errors, "quiet_hours_start", "quiet-hours-start")

    effective_end = _submitted_or_current(submitted, "quiet_hours_end", current_end)
    end_error_attrs = _field_error_attrs(
        errors, "quiet_hours_end", "quiet-hours-end", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    end_error_html = _field_error_html(errors, "quiet_hours_end", "quiet-hours-end")

    # 19-10-PLAN.md (D-14/S-04): the preset row. Reuses .runway-row -
    # style.css's existing generic flex/wrap/gap row - rather than
    # declaring a new CSS rule; that class is not scoped to the runway
    # picker's markup, only to its layout shape, and nothing here asserts
    # its absence from quiet_hours_group()'s own output (unlike
    # .theme-status__row, which a pinned check requires stay absent from
    # this group specifically). The three buttons are bare `type="button"`
    # elements with no new class, inheriting the existing quiet-button
    # treatment (base `button` selector) untouched.
    preset_row_html = (
        '<div class="runway-row">'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-enabled="0">%s</button>'
        "</div>"
    ) % (
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_NIGHT_START), escape_html(QUIET_HOURS_PRESET_NIGHT_END),
        escape_html(
            i18n.t(QUIET_HOURS_PRESET_NIGHT_LABEL_TEMPLATE)
            % (QUIET_HOURS_PRESET_NIGHT_START, QUIET_HOURS_PRESET_NIGHT_END)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_WORKDAY_START), escape_html(QUIET_HOURS_PRESET_WORKDAY_END),
        escape_html(
            i18n.t(QUIET_HOURS_PRESET_WORKDAY_LABEL_TEMPLATE)
            % (QUIET_HOURS_PRESET_WORKDAY_START, QUIET_HOURS_PRESET_WORKDAY_END)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(i18n.t(QUIET_HOURS_PRESET_ALWAYS_ON_LABEL)),
    )

    # 21-04-PLAN.md Task 1 (D-01/D-02): the instant switch that used to
    # render here, above a hairline and the shared "applies on next
    # wake" sentence, is gone — it now renders once, in the shared
    # Frame strip at the top of Home and Display (the shared strip
    # helper in companion/layout.py), never a second time in this card.
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): the scheduled on/off
    # checkbox that used to render next is retired outright too — the
    # presets, both time inputs and the Save button are unchanged.
    # 22-05-PLAN.md Task 2 (D-04): the caption's own second sentence is
    # the one computed delay sentence, already translated/formatted by
    # the caller — this is the ONE place it is escaped, alongside the
    # caption's own first sentence, in a single combined string (matching
    # this file's "translate first, escape once" convention).
    # 22-10-PLAN.md Task 2 (B14): the site's own resolved language, set
    # on both <input type="time"> elements. `<html lang>` already carries
    # it, but a native time control formats itself from the BROWSER's
    # locale, not the document's — so this attribute is the standards-
    # level request, and the visible sibling below is the fix that
    # actually holds when a browser ignores it (a Chromium in en-US
    # renders "11:00 PM" either way).
    # 25-04-PLAN.md Task 2 (CFG-48): the server-drawn ring, rendered
    # between the caption and the presets. WHERE IT GOES, AND WHY IT IS
    # NOT A REORDERING: 10-UI-SPEC.md locks the order of the four
    # CONTROLS — presets, then Start, then End, each on its own
    # full-width line — and all four keep their positions and their
    # adjacency. The ring is not a control; it is a picture of what is
    # currently set, so it reads before the things that change it
    # (what this is now, then how to change it), and putting it after
    # the End field would separate the picture from the caption that
    # introduces it while pushing it below the fold at 360px.
    #
    # Drawn from the SAME effective values the two inputs are populated
    # from, never from `current_start`/`current_end` directly. That is
    # D-07's echo rule, which the inputs already follow: on a rejected
    # save the arc must show what the visitor actually submitted, not
    # what is stored, or the picture and the fields disagree on exactly
    # the screen where a mistake is being fixed.
    dial_span = quiet_window_span(effective_start, effective_end)
    dial_html = quiet_dial_html(
        dial_span, quiet_dial_handles_html(effective_start, effective_end))
    readout_html = quiet_dial_readout_html(effective_start, effective_end, dial_span)

    site_lang = prefs.current_lang()
    effective_delay_sentence = (
        delay_sentence if delay_sentence is not None else i18n.t(frame_state.DELAY_UNKNOWN))
    caption_html = "%s %s" % (i18n.t(QUIET_HOURS_SECTION_CAPTION), effective_delay_sentence)
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s%s"
        "%s"
        '<label>%s <input type="time" name="quiet_hours_start" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>'
        "%s"
        '<label>%s <input type="time" name="quiet_hours_end" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>'
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_GROUP_HEADING_ID),
        escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_SECTION_CAPTION_ID),
        escape_html(caption_html),
        dial_html, readout_html,
        preset_row_html,
        escape_html(i18n.t("Start")),
        escape_html(effective_start), escape_html(site_lang), SETTINGS_FORM_ID, start_error_attrs,
        _normalised_time_html(effective_start),
        start_error_html,
        escape_html(i18n.t("End")),
        escape_html(effective_end), escape_html(site_lang), SETTINGS_FORM_ID, end_error_attrs,
        _normalised_time_html(effective_end),
        end_error_html,
    )


def wake_gauge_interval_s(current_wake_interval_s, submitted=None):
    """The interval the two gauges describe, as an int inside
    `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]`, or `None` when there is
    no such value — in which case NOTHING this plan adds renders at all.

    THE SAME OMIT-DON'T-FABRICATE RULE THE `value` ATTRIBUTE BELOW
    ALREADY FOLLOWS, and the same one `quiet_dial_handles_html()` applies
    to a handle whose end does not parse: a gauge for a value that was
    never set claims a fact about the frame that is not true (D-07), and
    a slider pre-positioned at a fabricated point is worse still,
    because dragging it saves that fabrication.

    D-07's ECHO RULE IS HONOURED WHERE IT CAN BE, AND ONLY THERE. On a
    rejected save `submitted` carries the raw string the visitor typed,
    and the gauges describe THAT rather than the stored value — the
    identical rule 25-04 applied to the quiet arc, for the identical
    reason: on exactly the screen where a mistake is being fixed, the
    picture and the field must not disagree. But a raw submission is
    where the out-of-range values live ("7", "99999", "abc"), and a
    gauge for 7 seconds would describe a cadence this device cannot be
    configured to use. So an echo that is not a usable interval renders
    no gauge rather than a gauge about nothing.

    Total by construction: a non-string, a non-numeric string, a float
    string, a bool and `None` all resolve to `None` and nothing raises.
    """
    if submitted is not None and "wake_interval_s" in submitted:
        raw = submitted["wake_interval_s"]
        try:
            candidate = int(str(raw).strip())
        except (TypeError, ValueError):
            return None
    elif isinstance(current_wake_interval_s, int) and not isinstance(
            current_wake_interval_s, bool):
        candidate = current_wake_interval_s
    else:
        return None
    if device_config.WAKE_INTERVAL_MIN_S <= candidate <= device_config.WAKE_INTERVAL_MAX_S:
        return candidate
    return None


def _wake_minutes(interval_s):
    """`interval_s` as a whole number of minutes, ROUNDED UP.

    The ONE expression both gauges and companion/static/value-controls.js
    read the minute count off — the script divides by the same scale the
    markup hands it and takes the same ceiling, so the sentence and the
    field cannot disagree by construction rather than by agreement.

    Up rather than down, because both sentences are claims about a
    BOUND: a 90-second cadence bounds the wait at a minute and a half,
    and `90 // 60` would print "at most 1 min", which is FALSE. The
    ceiling prints "at most 2 min", which is true and merely loose.
    Every value this control can produce is a whole number of minutes
    anyway (its step is a minute); the ceiling exists for the values
    already ON DISK from before this control existed.
    """
    return -(-int(interval_s) // WAKE_GAUGE_SECONDS_PER_MINUTE)


def wake_freshness_text(interval_s):
    """"A plane reaches the frame at most 5 min after it passes." — the
    bound, or `""` when there is no interval to bound.

    THE WORD "AT MOST" IS THE WHOLE SENTENCE. The frame learns about a
    plane at its next wake, so a plane that passes one instant after a
    wake appears one whole interval later and never later than that —
    true for every interval, by construction. Drop those two words and
    the same sentence becomes a claim about TYPICAL behaviour, which
    nothing in this project measures.

    The minute count is `_wake_minutes()`'s, shared with the relative
    clause and with the script, so the sentence and the field cannot
    disagree.
    """
    if interval_s is None:
        return ""
    return i18n.t(WAKE_FRESHNESS_TEXT).replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(_wake_minutes(interval_s)))


def wake_battery_observed_text(interval_s, battery_rows=None):
    """The battery half: an absolute figure ONLY when this frame's own
    observed history supports one, and the named "not enough history
    yet" sentence in every other case. `""` when there is no interval.

    NAMED FOR WHAT IT IS — a SENTENCE about the observed series, not a
    life computation — and the name matters beyond taste. The first
    draft was called `wake_battery_life_text()` and
    `test_companion_app.py`'s one-home guard failed it by name:
    *"companion/pages/config_page.py defines wake_battery_life_text() —
    a second battery-LIFE computation"*. That guard is deliberately
    blunt and it was right to object to the NAME; the answer is not to
    allow-list the name (which would let a real second estimate in under
    it later), it is to stop claiming to compute a lifetime. Nothing
    here computes one: the only arithmetic in this function is choosing
    between a singular and a plural wording.

    THE FIGURE IS `battery.battery_life_estimate()`'s, NEVER THIS
    MODULE'S. There is no division anywhere in this file that could
    produce a days-remaining number, deliberately, and a check scans
    `companion/pages/` for one. Four of that function's five named
    trends carry no figure at all (no reading, not enough history, a
    RISING series — a charged device has a positive slope and dividing
    by it yields a negative or infinite lifetime — and a flat one), and
    all four land on the same honest sentence here.

    `battery_rows` is a daily-average series in
    `server/history_db.py`'s row shape; `None`/`()` is the ordinary
    state of a fresh deployment and produces the unknown sentence rather
    than an empty card.
    """
    if interval_s is None:
        return ""
    estimate = battery.battery_life_estimate(
        battery_rows or (), interval_s, interval_s)
    days = estimate["days_remaining"]
    if (estimate["trend"] == battery.LIFE_TREND_FALLING
            and isinstance(days, int) and not isinstance(days, bool)):
        template = WAKE_BATTERY_DAY_TEXT if days == 1 else WAKE_BATTERY_DAYS_TEXT
        return i18n.t(template).replace(
            layout.VALUE_CONTROL_TEXT_TOKEN, str(days))
    return i18n.t(WAKE_BATTERY_UNKNOWN_TEXT)


def wake_screen_off_text():
    """"While the screen is off the frame wakes every 5m instead,
    whatever this is set to."

    Rendered unconditionally beside the battery sentence rather than
    hidden behind a `display_enabled` read: the clause is true whichever
    way that switch is set, and a qualifier that appears only once the
    screen is already off is a qualifier nobody reads in time.

    The cadence goes through `layout.duration_text()` — this app's ONE
    duration ladder — because it is a fixed constant no script has to
    reproduce. The two sentences above deliberately do not, for the
    opposite reason: their number changes as the slider moves, and a
    ladder that switches unit at an hour cannot be recomputed in the
    browser without a second copy of it in JavaScript.
    """
    return i18n.t(WAKE_BATTERY_SCREEN_OFF_TEXT) % layout.duration_text(
        device_config.DISPLAY_OFF_SLEEP_S)


def wake_battery_relative_template(saved_interval_s):
    """The relative clause's TEMPLATE, with the saved cadence already
    written into it and `#` left standing for the proposed one — or `""`
    when there is no usable saved cadence to compare against.

    "This setting wakes the frame every # min instead of every 10 min."

    TWO CADENCES NAMED IN FULL, NOT A RATIO, and the reason is a
    language one rather than a taste one. A ratio needs a decimal
    ("≈ 1.5× more often"), a decimal needs a decimal MARK, and French
    writes it with a comma — so a ratio recomputed in the browser would
    either print an English decimal on a French page or need the mark
    handed to the script as one more attribute. Two whole minute counts
    need neither: they are integers in both languages, the "instead of"
    says the direction without a second wording for each side, and the
    reader does not have to remember what the saved value was in order
    to read the sentence. The half-up/half-to-even rounding trap that a
    shared decimal would have carried between Python and JavaScript
    disappears with it.

    THE SAVED CADENCE IS BAKED IN HERE, server-side, because it is fixed
    for the life of the page: only the PROPOSED one moves, so only the
    proposed one is left as the quantity mark. That is what keeps the
    script to one substitution and keeps this sentence out of
    JavaScript.

    Routed through `battery.battery_life_estimate()`'s own
    `relative_factor` for its GUARD rather than for a number: that
    function already refuses a bool cadence, a non-numeric one, a
    non-positive one and an absurd one, and a clause built on a cadence
    it would have refused is a clause about nothing.
    """
    estimate = battery.battery_life_estimate(
        (), saved_interval_s, saved_interval_s)
    if estimate["relative_factor"] is None:
        return ""
    return i18n.t(WAKE_BATTERY_INSTEAD_TEXT) % _wake_minutes(saved_interval_s)


def wake_battery_relative_text(proposed_interval_s, saved_interval_s):
    """The relative clause as the SERVER would render it for a given
    proposal — `""` when the two cadences are the same, which is what
    every real page render produces.

    The clause exists for companion/static/value-controls.js to fill
    while a drag is in flight; the server renders the saved interval
    against itself, and "this setting wakes the frame every 10 min
    instead of every 10 min" would be noise on every page load. `""`
    rather than a hidden element, so there is nothing to un-hide and no
    second visibility mechanism.

    It is nonetheless a real function with a real return, because it is
    the ONE definition of this sentence in Python: companion/
    test_browser_ux.py drives the slider in a browser and compares the
    script's own output against this, so "the script says what the
    server would have said" is measured rather than assumed.

    IT NEVER CARRIES A DAYS FIGURE, and that is the whole division of
    labour with `wake_battery_observed_text()` above. This half is
    arithmetic on two cadences and is therefore always available and
    always live; the absolute half comes out of observed history and is
    server-rendered once. A script that could recompute the absolute
    half would be a script that could invent one — which is the defect
    this split makes unreachable rather than merely unlikely.
    """
    template = wake_battery_relative_template(saved_interval_s)
    if not template:
        return ""
    estimate = battery.battery_life_estimate(
        (), saved_interval_s, proposed_interval_s)
    factor = estimate["relative_factor"]
    if factor is None or factor == 1.0:
        return ""
    return template.replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(_wake_minutes(proposed_interval_s)))


def wake_battery_rows(state_dir, now=None):
    """`WAKE_BATTERY_WINDOW_DAYS` of daily battery averages for the
    battery sentence, or `()` on any read failure or absent state dir.

    Never raises, matching `_rule_suggestion_chips_html()`'s and
    `_theme_live_preview_html()`'s own fail-soft contract for the
    identical class of read in this same module: a settings page that
    500s because a battery history table could not be opened would be a
    far worse defect than a card that says it has no history yet — which
    is exactly what `wake_battery_observed_text()` renders from `()`.

    Read here rather than threaded through `ctx`: this is the only card
    in the app that needs the series, it renders on one scope of one
    page, and `companion/app.py`'s `page_context()` runs on EVERY
    authenticated render.
    """
    if not state_dir:
        return ()
    try:
        with history_db.open_db(state_dir) as conn:
            return history_db.daily_battery_averages(
                conn, since=_wake_battery_cutoff_iso(now))
    except Exception:
        return ()


def _wake_battery_cutoff_iso(now):
    """The `since=` bound for the read above, or `None` when `now` does
    not parse — in which case `daily_battery_averages()` degrades to an
    UNBOUNDED read, health_page's own documented choice for the one
    input it does not control: more history rather than none.
    """
    parsed = layout.parse_iso(now)
    if parsed is None:
        return None
    return (parsed - timedelta(days=WAKE_BATTERY_WINDOW_DAYS)).isoformat(
        timespec="seconds")


def wake_gauges_html(interval_s, battery_rows=None):
    """The two gauges, as two muted sentences — or `""` when there is no
    interval for them to describe.

    SERVER-RENDERED, AND OUTSIDE THE `.js` GATE ENTIRELY. This is the
    same split 25-04's dial made: with scripts blocked a visitor can
    still type an interval, still read what it means for freshness and
    for battery, and still save it. Only the slider is gated, because a
    slider with no script is a control that drags and shows nothing.
    Rendering these server-side is also what gives the script something
    to UPDATE rather than something to create — so a failed script
    leaves correct sentences rather than empty ones.

    Both wear `.text-label .section-caption`, the app's existing muted
    voice, and neither is a live region: they change on every step of a
    drag, and an `aria-live` region here would re-announce the same
    phrase continuously — the defect Phase 23 hit with its three
    switches, and the same call 25-04 made for its readout (CFG-52). The
    range announces itself natively instead, and points at these two by
    `aria-describedby`.
    """
    if interval_s is None:
        return ""
    # THE FRESHNESS SENTENCE IS ENTIRELY LIVE and the battery one is
    # only PARTLY live, and that split is the honesty rule made
    # structural. The freshness paragraph is itself the readout: its
    # whole text is arithmetic on the value, so the script may rewrite
    # all of it. The battery paragraph's figure came out of observed
    # history, so the script may not touch it — only the trailing span,
    # whose template names two cadences and contains no days figure at
    # all. A script cannot become braver than the server was, because
    # there is no template here through which it could.
    return (
        '<p class="text-label section-caption %s" id="%s" %s="%s" %s="%s" %s="%d">%s</p>'
        '<p class="text-label section-caption %s" id="%s">%s %s '
        '<span %s="%s" %s="%s" %s="%d" %s="%d">%s</span></p>'
    ) % (
        escape_html(WAKE_GAUGE_CLASS), escape_html(WAKE_GAUGE_FRESHNESS_ID),
        layout.VALUE_CONTROL_READOUT_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(i18n.t(WAKE_FRESHNESS_TEXT)),
        layout.VALUE_CONTROL_READOUT_SCALE_ATTR, WAKE_GAUGE_SECONDS_PER_MINUTE,
        escape_html(wake_freshness_text(interval_s)),

        escape_html(WAKE_GAUGE_CLASS), escape_html(WAKE_GAUGE_BATTERY_ID),
        escape_html(wake_battery_observed_text(interval_s, battery_rows)),
        escape_html(wake_screen_off_text()),
        layout.VALUE_CONTROL_READOUT_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_READOUT_TEXT_ATTR,
        escape_html(wake_battery_relative_template(interval_s)),
        layout.VALUE_CONTROL_READOUT_SCALE_ATTR, WAKE_GAUGE_SECONDS_PER_MINUTE,
        # THE BASE: the readout says nothing at all while the proposed
        # value is the saved one, which is every page load and every
        # scripts-blocked render.
        layout.VALUE_CONTROL_READOUT_BASE_ATTR, interval_s,
        escape_html(wake_battery_relative_text(interval_s, interval_s)),
    )


def wake_slider_html(interval_s):
    """The range input, inside 25-01's `.js` gate — or `""` when there is
    no saved interval for it to start from.

    IT CARRIES NO `name`, AND THAT IS THE WHOLE DESIGN. "Why does this
    input have no name" is exactly the question a later editor answers
    wrongly by adding one, so: a named range would post a SECOND value
    for `wake_interval_s` on every save, and whichever arrived last
    would win, silently. The `<input type="number">` above is the only
    control on this card that posts, and this one only ever writes into
    it through companion/static/value-controls.js.

    NO `role="slider"` EITHER. A native range input already exposes
    slider semantics, a native `aria-valuenow` and the keyboard model
    (arrows one step, Page ten, Home and End to the ends) that
    value-controls.js implements by hand for a `<div>` handle — adding
    the role on top is the classic double-role error. It gets an
    `aria-label` naming it (the number input's own label already names
    that control) and an `aria-describedby` pointing at the two gauges,
    which is what makes the trade-off audible rather than only visible.

    GATED, because a range with no script is a control that drags and
    shows the visitor nothing — 25-RESEARCH.md's "renders but does
    nothing", in its purest form. The two gauges and the number input
    are NOT gated: with scripts blocked a visitor still reads what the
    interval means and still types and saves one.

    `min`/`max` come from `device_config`, never re-typed — the same
    cross-file convention the number input already follows, so one
    control can never accept what the other (and
    `save_device_config()`'s own server-side re-check) rejects.

    NO INITIAL `--value-fraction`, unlike 25-04's handles: a native
    range paints its own thumb from its own value, so there is no
    geometry here for the stylesheet to place. The property is still
    written by the script's shared paint and is simply unused.
    """
    if interval_s is None:
        return ""
    return (
        '<div class="%s %s" %s %s="%s" %s="%s" %s="%d" %s="%d" %s="%d">'
        '<input type="range" class="%s" %s value="%d" min="%d" max="%d" step="%d"'
        ' aria-label="%s" aria-describedby="%s %s">'
        "</div>"
    ) % (
        escape_html(WAKE_SLIDER_CLASS), escape_html(layout.JS_GATE_CLASS),
        layout.VALUE_CONTROL_ATTR,
        layout.VALUE_CONTROL_FIELD_ATTR, escape_html(WAKE_INTERVAL_FIELD_NAME),
        layout.VALUE_CONTROL_FORM_ATTR, SETTINGS_FORM_ID,
        layout.VALUE_CONTROL_MIN_ATTR, device_config.WAKE_INTERVAL_MIN_S,
        layout.VALUE_CONTROL_MAX_ATTR, device_config.WAKE_INTERVAL_MAX_S,
        layout.VALUE_CONTROL_STEP_ATTR, WAKE_SLIDER_STEP_S,
        escape_html(WAKE_SLIDER_INPUT_CLASS), layout.VALUE_CONTROL_INPUT_ATTR,
        interval_s,
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        WAKE_SLIDER_STEP_S,
        escape_html(i18n.t(WAKE_SLIDER_LABEL)),
        escape_html(WAKE_GAUGE_FRESHNESS_ID), escape_html(WAKE_GAUGE_BATTERY_ID),
    )


def wake_interval_group(current_wake_interval_s, errors=None, submitted=None, next_wake_clock=None,
                        battery_rows=None):
    """The Wake interval settings group (11-UI-SPEC.md, 11-RESEARCH.md
    Pattern 4): a fifth sibling of the Theme/Runway/Diagnostic LED/Quiet
    hours groups inside the single merged `<form action="{SETTINGS_ROUTE}">`,
    built against `led_group()`'s exact structure — same `.theme-status`
    wrapper idiom, same `<h2 class="text-heading">` naming (no
    `<fieldset>`/`<legend>`, for the identical reason `led_group()`'s own
    docstring already documents: a `<legend>` only has accessible-name
    semantics inside a `<fieldset>`, which these sibling groups
    deliberately do not have). Unlike `quiet_hours_group()`, this group has
    no checkbox gate — a plain `<label>` wraps a single
    `<input type="number">`, this codebase's first (D-05), not
    `class="settings-checkbox"` — that class normalises a checkbox and
    would mis-size a text-like input; the global `input, select` rule
    already supplies the 44px touch-target floor with no type-specific
    override needed, exactly like `<input type="time">`'s own precedent.

    `min`/`max` are interpolated from `device_config.WAKE_INTERVAL_MIN_S`/
    `WAKE_INTERVAL_MAX_S`, read from the module rather than re-typed as
    literals, so the two can never drift apart from `save_device_config()`'s
    own server-side re-check of the identical bounds.

    The `value` attribute is the one place this function does real work:
    it is emitted only when `current_wake_interval_s` is an `int` that is
    not a `bool` and falls within the inclusive
    `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]` range; otherwise no
    `value` attribute is emitted at all, and the placeholder
    (`WAKE_INTERVAL_PLACEHOLDER_TEXT`) carries the empty state. Two
    reasons this guard is load-bearing, not decorative: a fabricated
    number would lie to the user about a setting that was never made
    (D-07), and — more sharply — an out-of-range `value` on a native
    numeric input fails HTML5 constraint validation, which blocks
    submission of the *entire* Settings form, not just this field. That is
    a live risk, not hypothetical: `deploy/skypane.env.example` currently
    sets `SKYPANE_SLEEP_S=30`, below the 60s floor, and plan 11-04 feeds
    that environment value in as the pre-fill fallback. The bool exclusion
    is mandatory for the same reason it is everywhere else in this phase —
    `isinstance(True, int)` is true in Python.

    The heading, the caption and the placeholder are routed through
    `escape_html()`, matching this file's universal escaping discipline;
    the numeric value needs no escaping because `%d` cannot emit anything
    but digits and a sign.

    19-07-PLAN.md Task 2 (D-07): when a real submission is being
    repopulated (`submitted is not None`) and it actually carries this
    field, the RAW submitted string is echoed back verbatim (escaped),
    deliberately bypassing the in-range/non-bool-int guard above — that
    guard exists only for the ordinary ctx-sourced int
    (`current_wake_interval_s`), never for a rejected save's own echoed
    input. "7" is a string, not an int, and would otherwise never get a
    `value` attribute at all, silently discarding exactly what D-07
    requires be shown back to the user. Native HTML5 min/max constraint
    validation still applies on the user's NEXT submit attempt (nothing
    here suppresses it) — that is a feature, not a bug: it is what
    prompts them to fix the value before it can be saved.

    25-05-PLAN.md Task 1 (CFG-49): `battery_rows` is the daily-average
    battery series the battery gauge is derived from, `()` by default —
    every pre-existing call site keeps producing its previous output for
    the input, the label, the unit sibling and the error block, which
    are UNTOUCHED by this plan and asserted so. The two gauges are
    APPENDED after the error block, never interleaved with it: they are
    what the setting MEANS, so they read after the control that sets it,
    and appending is also what makes "the rest of the card is
    byte-identical" a structural fact rather than a careful edit.
    """
    if submitted is not None and "wake_interval_s" in submitted:
        raw_submitted = submitted["wake_interval_s"]
        value_attr = ' value="%s"' % escape_html(raw_submitted) if raw_submitted else ""
    else:
        value_attr = (
            ' value="%d"' % current_wake_interval_s
            if (
                isinstance(current_wake_interval_s, int)
                and not isinstance(current_wake_interval_s, bool)
                and device_config.WAKE_INTERVAL_MIN_S <= current_wake_interval_s <= device_config.WAKE_INTERVAL_MAX_S
            ) else "")
    error_attrs = _field_error_attrs(
        errors, "wake_interval_s", "wake-interval-s", hint_id=WAKE_INTERVAL_SECTION_CAPTION_ID)
    error_html = _field_error_html(errors, "wake_interval_s", "wake-interval-s")
    # ONE resolution of the gauges' and the slider's subject, so the
    # three of them can never describe different values — and so
    # "everything this plan adds renders together or not at all" is a
    # property of the code rather than of three matching conditions.
    gauge_interval_s = wake_gauge_interval_s(current_wake_interval_s, submitted)
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        # 22-10-PLAN.md Task 3 (B17): the label is its own element ABOVE
        # the control, pointing at it by `for=`, instead of wrapping it.
        # A wrapping <label> put its text and the input on ONE line, which
        # is why this field's input started at x=515 while every other
        # Device field's started at x=361. This is the shape the
        # Notifications topic-URL field (and every other field on this
        # page) already uses.
        '<label for="%s">%s</label>'
        '<input type="number" id="%s" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="%s"%s%s>'
        # The unit as a SIBLING. aria-hidden because the label above
        # already names the unit ("... (seconds)") - repeating it in the
        # accessibility tree would announce the same fact twice, while the
        # visible duplication is exactly the point for a sighted user
        # reading a 96px-wide box. Same reasoning as
        # _normalised_time_html()'s own sibling (B14).
        '<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
        "%s"
        # 25-05-PLAN.md Tasks 1 and 2 (CFG-49): the gated slider and then
        # the two gauges, APPENDED. Every element above this line is
        # byte-identical to its pre-plan output, in all six argument
        # shapes, and a check diffs them.
        #
        # The slider sits AFTER the field's own error message rather than
        # between the two: an error has to read as attached to the
        # control it is about, and a control inserted between them breaks
        # that adjacency. The gauges come last because they are what the
        # setting MEANS — the control first, its consequences after.
        "%s%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(i18n.t(WAKE_INTERVAL_SECTION_HEADING)),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION_ID),
        escape_html(_with_next_wake(i18n.t(WAKE_INTERVAL_SECTION_CAPTION), next_wake_clock)),
        escape_html(WAKE_INTERVAL_INPUT_ID), escape_html(i18n.t("Wake interval (seconds)")),
        escape_html(WAKE_INTERVAL_INPUT_ID),
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        escape_html(i18n.t(WAKE_INTERVAL_PLACEHOLDER_TEXT)),
        value_attr, error_attrs,
        escape_html(WAKE_INTERVAL_UNIT_LABEL),
        error_html,
        wake_slider_html(gauge_interval_s),
        wake_gauges_html(gauge_interval_s, battery_rows),
    )


def notifications_group(
        configured, current_battery_low, current_frame_silent,
        errors=None, submitted=None):
    """The Notifications settings group (D-26/D-28, 20-11-PLAN.md Task 1,
    20-UI-SPEC.md Section Anatomy J/copy table G): a sixth sibling of
    the LED/Wake interval groups inside `<form id="{SETTINGS_FORM_ID}">`,
    Device-only (`screens.GROUP_NOTIFICATIONS` is never a member of
    Display's `everyday_groups` or the legacy SCOPE_ALL tuple) — built
    against `led_group()`'s exact `.theme-status`/`<h2 class=
    "text-heading">` fieldset-free idiom.

    **Write-only URL — never masked, unlike the Calendar card's own
    connect/replace field (T-20-12)**: `configured` is a bare bool —
    never the URL itself, never a masked fragment of it, in any state.
    `layout.status_row("", verdict, "", state)` reports only whether a
    topic URL is stored; the text input always renders with NO `value`
    attribute and nothing derived from the stored URL, in both states.
    Wrapped in `<details><summary>Replace the URL</summary>` while
    `configured` is true, unwrapped otherwise — the identical disclosure
    shape the merged Calendar card's own connect/replace form uses
    (`calendar_group()`, 21-07-PLAN.md Task 1) for the identical reason.
    This field deliberately does NOT follow Calendar's own D-14/R-10
    widening (host + "…" once connected) — no equivalent developer
    request exists for Notifications, and this docstring is the one
    place recording that the two write-only-looking fields are no
    longer identical in what they show once connected.

    Unlike the Calendar card's own connect/replace form, this field is
    NOT a dedicated route: it is a plain member of the tracked settings
    form, waiting on the page-wide Save exactly like every other Device
    field (the plan's own explicit instruction — "All three controls are
    part of #settings-form and wait on Save"). Only the "Send a test"
    button (`notifications_test_section()` below) is its own immediate-
    POST form, a sibling of `#settings-form` — mirroring the Calendar
    Connect form's/the rules add-form's own reasoning for that identical
    shape: an immediate action must never wait on, or nest inside, the
    page-wide Save form (D-19/Pitfall 1).

    19-07-PLAN.md Task 2 (D-07): `errors`/`submitted` (both fully
    defaulted) let a rejected save repopulate both checkboxes from the
    submission and render each field's own error message — the topic
    URL has no repopulation (nothing to repopulate; a write-only field),
    matching the merged Calendar card's own connect/replace field's
    identical omission.
    """
    status_html = layout.status_row(
        "",
        i18n.t(
            NOTIFICATIONS_STATUS_CONFIGURED_VERDICT if configured
            else NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT),
        "",
        "ok" if configured else "warn")

    url_error_attrs = _field_error_attrs(
        errors, "notifications_topic_url", "notifications-topic-url",
        hint_id=NOTIFICATIONS_URL_HINT_ID)
    url_error_html = _field_error_html(
        errors, "notifications_topic_url", "notifications-topic-url")
    field_html = (
        '<div class="rule-add-form__field">'
        '<label for="notifications-topic-url">%s</label>'
        '<input type="text" id="notifications-topic-url" '
        'name="notifications_topic_url" autocomplete="off" '
        'spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(NOTIFICATIONS_URL_FIELD_LABEL)),
        NOTIFICATIONS_URL_MAX_LEN, url_error_attrs,
        escape_html(NOTIFICATIONS_URL_HINT_ID), escape_html(i18n.t(NOTIFICATIONS_URL_HINT)),
        url_error_html,
    )
    if configured:
        field_html = (
            '<details class="calendar-url-disclosure"><summary>%s</summary>%s</details>'
        ) % (escape_html(i18n.t(NOTIFICATIONS_REPLACE_URL_SUMMARY)), field_html)

    battery_checked = _submitted_checkbox_checked(
        submitted, "notifications_battery", NOTIFICATIONS_BATTERY_CHECKBOX_VALUE,
        current_battery_low)
    battery_error_attrs = _field_error_attrs(
        errors, "notifications_battery", "notifications-battery")
    battery_error_html = _field_error_html(
        errors, "notifications_battery", "notifications-battery")

    silent_checked = _submitted_checkbox_checked(
        submitted, "notifications_silent", NOTIFICATIONS_SILENT_CHECKBOX_VALUE,
        current_frame_silent)
    silent_error_attrs = _field_error_attrs(
        errors, "notifications_silent", "notifications-silent")
    silent_error_html = _field_error_html(
        errors, "notifications_silent", "notifications-silent")

    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "%s"
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="notifications_battery" value="%s"%s%s> %s'
        "</label>"
        "%s"
        '<label class="settings-checkbox">'
        '<input type="checkbox" name="notifications_silent" value="%s"%s%s> %s'
        "</label>"
        "%s"
        # 22-10-PLAN.md Task 3 (B8): "Send a test" renders HERE, inside
        # the card whose setting it tests, instead of as an orphan button
        # floating between this card and the next. It is attached to its
        # own empty <form> — rendered as a sibling of #settings-form by
        # notifications_test_section() below — through the cross-DOM
        # `form=` attribute, which is the FIFTH consumer of that idiom on
        # this page (the theme/runway/quiet-hours radios and inputs, the
        # calendar disconnect button, and now this). Deliberate pattern
        # reuse, not a workaround: an immediate-action form can never
        # nest inside the page-wide settings form (see render()'s own
        # docstring), and form ownership is decided by the browser from
        # this attribute rather than from DOM proximity (T-22-34), so the
        # button's action and its server-side handler are untouched by
        # the move.
        '<button type="submit" form="notifications-test">%s</button>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(NOTIFICATIONS_SECTION_HEADING)),
        escape_html(i18n.t(NOTIFICATIONS_SECTION_HEADING)),
        escape_html(NOTIFICATIONS_SECTION_CAPTION_ID), escape_html(i18n.t(NOTIFICATIONS_SECTION_CAPTION)),
        status_html,
        field_html,
        escape_html(NOTIFICATIONS_BATTERY_CHECKBOX_VALUE), " checked" if battery_checked else "",
        battery_error_attrs, escape_html(i18n.t(NOTIFICATIONS_BATTERY_LABEL)),
        battery_error_html,
        escape_html(NOTIFICATIONS_SILENT_CHECKBOX_VALUE), " checked" if silent_checked else "",
        silent_error_attrs, escape_html(i18n.t(NOTIFICATIONS_SILENT_LABEL)),
        silent_error_html,
        escape_html(i18n.t(NOTIFICATIONS_TEST_BUTTON_TEXT)),
    )


def notifications_test_section():
    """The "Send a test" button (D-26, 20-11-PLAN.md Task 1): its own
    small `<form method="post" action="{NOTIFICATIONS_TEST_ROUTE}">`, a
    sibling of `<form id="{SETTINGS_FORM_ID}">` — mirroring the merged
    Calendar card's own connect/replace form's/the rules add-form's own
    reasoning for the identical shape (D-19/Pitfall 1: an immediate
    action's own `<form>` must never nest inside the settings form).
    `render()` renders this immediately after `</form>` closes, on the
    Device scope only (`screens.GROUP_NOTIFICATIONS` is never a member
    of `scope_groups(SCOPE_DISPLAY)` or the legacy SCOPE_ALL tuple, so
    this section is correctly omitted from both).

    The action attribute below is written as literal path text, not a
    `%s` interpolation of `NOTIFICATIONS_TEST_ROUTE` — matching the
    merged Calendar card's own connect/replace form's established
    convention for the identical class of grep (this module's
    acceptance gate greps the literal form-action text).

    Carries no `data-confirm`: sending a test push is neither
    destructive nor state-changing on this side — the handler
    (`companion/app.py`'s `_handle_notifications_test_post()`) reads the
    stored URL from disk and never trusts the request body (T-20-13),
    which is the real mitigation, not a confirmation dialog.
    """
    # 22-10-PLAN.md Task 3 (B8): the <form> is now EMPTY. Its button moved
    # into the Notifications card (notifications_group() above) and
    # reaches this element across the DOM through
    # `form="notifications-test"`. The id below is written as literal
    # text for the same reason the action is — this module's acceptance
    # gate greps the literal attribute text.
    #
    # The form itself must stay a sibling of #settings-form rather than
    # move into the card: the card is rendered inside `<form
    # id="settings-form">`, and a <form> can never nest inside another
    # <form> (see render()'s own docstring on this exact constraint).
    # The empty form keeps its own action, its own handler and its own
    # server-side validation; only the button's DOM position changed.
    return (
        '<form method="post" action="/settings/notifications/test" '
        'id="notifications-test" class="notifications-test-form"></form>'
    )


# 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): display_group() is retired
# outright — it used to render the Screen on/off card (a checkbox plus
# its own instant-switch slot, the latter already moved to the shared
# Frame strip by 21-04-PLAN.md Task 1). The Frame strip is now the ONLY
# control for the screen's on/off state, so this settings page no
# longer has anything left to render for it: no schedule, no checkbox,
# no card at all. screens.GROUP_DISPLAY has no entry in `builders`
# below any more (matching screens.GROUP_THEME/screens.GROUP_CALENDAR's
# own precedent for a group with no generic per-group renderer), and it
# is no longer a member of any screen type's own group tuple
# (companion/screens.py) or of `scope_groups()`'s legacy SCOPE_ALL tuple
# (D-12.2) either.


def _masked_calendar_url(url):
    """host + "…" — never the path, query, fragment or userinfo of the
    stored calendar feed URL (21-07-PLAN.md Task 2, D-14/R-10).

    Parses with `urlsplit()` and returns ONLY its `netloc` plus an
    ellipsis — a real URL parse, never a byte-offset truncation of the
    raw secret string (a naive `url[:20] + "…"` would NOT be safe: a
    short host could still leak leading path/query/token characters
    depending on its length). On ANY failure — a falsy `url`, a
    `ValueError` from `urlsplit()`, or a netloc that parses out empty —
    this returns the empty string, and the caller omits its whole
    masked-URL line entirely rather than render a fabricated placeholder
    (21-UI-SPEC.md's own "omit, don't fabricate" Empty/Error
    convention).

    This is a deliberate, narrow widening of this module's write-only
    convention for secret URLs (T-16-SECRET/T-17-SECRET): every OTHER
    secret-URL field in this file (the Calendar card's own connect/
    replace field, Notifications' topic-URL field) never reads its
    stored value back for display at all. D-14/R-10 explicitly asks for
    "host + '…'" once connected, which requires reading the value back
    — this helper is the ONE place in the whole codebase that does, and
    it is scoped as tightly as the requirement allows: host only, never
    the path, query, fragment or userinfo, and only ever reached by
    `calendar_group()`'s own connected-state branch below.
    """
    if not url:
        return ""
    try:
        netloc = urlsplit(url).netloc
    except ValueError:
        return ""
    if not netloc:
        return ""
    return "%s…" % netloc


def calendar_group(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None):
    """The Calendar card (21-07-PLAN.md Task 1, 21-UI-SPEC.md Section
    Anatomy E; D-13/D-14): ONE `<div class="page-section">`, in the
    "Look" supersection, after the Frame colours card (D-06, 21-05-
    PLAN.md Task 1). Retires the three-piece split (a status-only card,
    a separate connect/replace mini-form card, and a standalone
    disconnect form) a run of earlier plans (20-04/20-07/20-09) built up
    — D-13 wants genuine nesting, not three DOM siblings visually glued
    by a `:has()` CSS trick (21-RESEARCH.md Pitfall 2).

    In document order: the status row, then a state branch (below), then
    the "How it works" disclosure — always inside this one wrapper. The
    disconnect action's own confirmed `<form>` is the ONE piece that
    still cannot live inside this div (HTML forbids a `<form>` nested in
    another `<form>`, and this card's own connect/replace form is
    itself a `<form>`) — it renders as a second, data-only fragment,
    concatenated onto this function's return value as a plain sibling,
    never as a second value the caller has to remember to place. Every
    caller therefore gets both pieces, correctly ordered, from one call.

    21-05-PLAN.md Task 1 (D-06): the compact `calendar_theme_id` chip
    grid this card used to render (D-14d) is retired outright — it now
    lives inside the Frame colours card's own "Calendar flights" usage
    panel, alongside a "Same as departures" leading chip (D-09).
    `current_calendar_theme_id`/`current_theme_id`/`errors["calendar_
    theme_id"]` are therefore no longer this function's concern.
    `errors`/`submitted` stay: `errors` reaches the write-only URL
    field's own error message (the one field this merged card still
    validates); `submitted` stays fully defaulted, unused, purely for
    call-site symmetry with every other group builder — there is
    nothing else here to repopulate.

    21-07-PLAN.md Task 2 (D-14/R-10): `state_dir` (fully defaulted,
    `None` when the caller has none to give) is the ONE new parameter
    this task adds — it is read exactly once, only in the connected
    branch below, purely to compute the masked feed-URL line via
    `_masked_calendar_url()` (`calendar_rules.configured_calendar_url(
    state_dir)`). This is the single call site in this module that
    reads a stored calendar secret back for display; every other
    reader of `configured` never touches the value itself.

    D-12 fix (carried forward): this card renders as a SIBLING of
    `<form id="settings-form">`, not a literal descendant — nothing
    inside it posts through the physical form any more.

    **D-14b — the status row.** `layout.status_row("", verdict, detail,
    state)`: label is `""` because the card's own `<h2>Calendar</h2>`
    already names the subject. Four branches, `drift` first — a
    permission-drifted stored link (D-02) wins over everything else,
    because `configured` is already `False` in that state (D-08 —
    `calendar_is_configured()`'s own bool contract) and a later check
    would therefore never see the drift branch at all. Then not
    configured. Then configured: "usable" (a parseable, age-computable
    `last_synced_at`) renders the entry count plus the language-aware
    relative age (D-07, `layout.relative_age_text()`) as the detail, with
    a genuinely fresh verdict word ("Connected"). Configured but never
    usable branches on whether an attempt has ever been recorded
    (`last_attempt_at is not None`): at least one attempt with no usable
    sync yet is the ONE derivable failed-fetch category this module has
    fields for (T-20-30) — the fixed, mapped `CALENDAR_STATUS_FETCH_
    FAILED_DETAIL` sentence, never a caught exception's own text. No
    attempt recorded yet is the ordinary "just connected" wait state.

    **D-13/D-14 — the state branch.** `configured` picks between two
    shapes: not connected (including the drifted case, since `drift`
    forces `configured` False) renders the write-only feed-URL field
    inside its own `<form method="post" action="{CALENDAR_CONNECT_
    ROUTE}">` with the primary "Connect calendar" button, unwrapped;
    connected renders a masked-URL line (host + "…", via `_masked_
    calendar_url()` — 21-07-PLAN.md Task 2, D-14/R-10; OMITTED
    entirely, not fabricated, when the mask cannot
    be computed) followed by a `<p class="calendar-actions">` holding
    the SAME connect form — now labelled "Replace" (`CALENDAR_REPLACE_
    BUTTON_TEXT`) — behind a `<details class="calendar-url-disclosure">
    <summary class="text-link">Replace the feed URL</summary>`
    disclosure, plus the small grey Disconnect button, right-aligned on
    the same line. The write-only contract is unchanged in either
    state: the input never carries a `value` attribute (T-16-SECRET/
    T-17-SECRET/T-20-12) — the masked line is a wholly separate, host-
    only fragment, never derived from or fed back into that field.

    The drifted state additionally gets its own small Disconnect button
    (no Replace disclosure — drift's own verdict already reads "Not
    connected", so there is no successfully-connected feed to
    "replace") so a drifted, unreadable stored link can still be
    cleared without first pasting a new one over it — the identical
    `configured or drift` predicate the retired standalone disconnect
    form used (D-02: a drifted file still exists and still holds a URL).

    **D-14 — the cross-form Disconnect button.** The disconnect
    `<form id="{CALENDAR_DISCONNECT_FORM_ID}">` is a genuinely separate
    DOM element (a data-only sibling of this card's own outer `<div>`,
    concatenated onto the return value below) carrying only its hidden,
    EMPTY confirm field — a bare POST of that form therefore submits no
    confirm value at all, landing on `_handle_calendar_disconnect_post()`
    's own server-rendered confirmation page (`calendar_disconnect_
    confirm_page()` below) rather than erasing anything. That page IS
    the real control; the visible button (rendered inline, wherever this
    function's state branch puts it) additionally carries `data-
    confirm`/`data-confirm-value` attributes `companion/static/
    confirm-submit.js` reads to show one native `confirm()` dialog and,
    on acceptance only, fill this same hidden field with `CALENDAR_
    DISCONNECT_CONFIRM_VALUE` before letting the submit proceed — a
    misclick guard layered on top, never a substitute for the server-
    side gate. The button reaches the form it does not contain via a
    `form="{CALENDAR_DISCONNECT_FORM_ID}"` attribute — the same cross-
    DOM submission idiom the dirty bar's own Save button already uses,
    required here because HTML forbids nesting this `<form>` inside the
    card's own connect/replace `<form>` or inside the card's outer
    `<div>` sitting next to one.

    **D-14a — the "How it works" disclosure.** Always renders in full,
    at the bottom of the card, in every state.
    """
    # Drift first (D-02): a drifted file makes `configured` already
    # False (D-08), so checking `not configured` before `drift` would
    # make the drift state unreachable and indistinguishable from a
    # calendar that was never connected.
    if drift:
        verdict = i18n.t(CALENDAR_STATUS_NOT_CONNECTED_VERDICT)
        detail = i18n.t(CALENDAR_STATUS_PERMISSION_UNSAFE)
        state = "error"
    elif not configured:
        verdict = i18n.t(CALENDAR_STATUS_NOT_CONNECTED_VERDICT)
        detail = ""
        state = "warn"
    else:
        usable = (
            bool(last_synced_at)
            and layout.parse_iso(last_synced_at) is not None
            and layout.age_seconds(last_synced_at, now) is not None)
        verdict = i18n.t(CALENDAR_STATUS_CONNECTED_VERDICT)
        if usable:
            age = layout.age_seconds(last_synced_at, now)
            if entry_count == 1:
                detail = i18n.t(CALENDAR_STATUS_DETAIL_SINGULAR_TEMPLATE) % (
                    layout.relative_age_text(age),)
            else:
                detail = i18n.t(CALENDAR_STATUS_DETAIL_TEMPLATE) % (
                    entry_count, layout.relative_age_text(age))
            state = "ok"
        elif last_attempt_at is not None:
            detail = i18n.t(CALENDAR_STATUS_FETCH_FAILED_DETAIL)
            state = "error"
        else:
            detail = ""
            state = "warn"
    status_html = layout.status_row("", verdict, detail, state)

    error_attrs = _field_error_attrs(
        errors, "calendar_url", "calendar-connect-url", hint_id=CALENDAR_URL_HINT_ID)
    error_html = _field_error_html(errors, "calendar_url", "calendar-connect-url")
    field_html = (
        '<div class="rule-add-form__field">'
        '<label for="calendar-connect-url">%s</label>'
        '<input type="text" id="calendar-connect-url" name="calendar_url" '
        'autocomplete="off" spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(CALENDAR_URL_FIELD_LABEL)),
        CALENDAR_URL_MAX_LEN, error_attrs,
        escape_html(CALENDAR_URL_HINT_ID), escape_html(i18n.t(CALENDAR_URL_HINT)),
        error_html,
    )
    # The cross-DOM form= attribute below is written as literal id
    # text, not a %s interpolation of CALENDAR_DISCONNECT_FORM_ID —
    # matching this file's own established convention for the instant-
    # switch forms' own action attributes (see CALENDAR_CONNECT_ROUTE's
    # comment below): this module's acceptance gate greps the literal
    # attribute text, and the constant itself stays defined for the
    # disconnect <form>'s own id attribute below and for test_config_
    # page.py's own checks to reference.
    disconnect_button_html = (
        '<button type="submit" form="calendar-disconnect-form" class="calendar-disconnect-btn">%s</button>'
    ) % escape_html(i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT))
    # The action attribute below is written as literal path text, not a
    # %s interpolation of CALENDAR_CONNECT_ROUTE — matching this file's
    # own established convention for the instant-switch forms' own
    # action attributes (see QUICK_DISPLAY_ROUTE's comment above): this
    # module's acceptance gate greps the literal form-action text, and
    # the constant itself stays defined for companion/app.py's
    # rebinding and companion/test_config_page.py's own checks to
    # reference without retyping the path a third time.
    if configured:
        # 21-07-PLAN.md Task 2 (D-14/R-10): the ONE call site in this
        # module that reads a stored calendar secret back for display —
        # host-only, via _masked_calendar_url()'s own real URL parse.
        # `calendar_rules.configured_calendar_url()` already applies its
        # own permission-drift guard (calendar_secret_mode_is_unsafe()),
        # but `configured` being True here means that guard already
        # passed upstream (calendar_is_configured()'s identical check),
        # so this second read is consistent with the state this branch
        # is already committed to rendering.
        masked_url = _masked_calendar_url(
            calendar_rules.configured_calendar_url(state_dir) if state_dir else "")
        masked_url_html = (
            '<p class="text-body calendar-masked-url">%s</p>' % escape_html(masked_url)
            if masked_url else "")
        replace_form_html = (
            '<form method="post" action="/settings/calendar/connect" class="rule-add-form">'
            "%s"
            '<button type="submit">%s</button>'
            "</form>"
        ) % (
            field_html,
            escape_html(i18n.t(CALENDAR_REPLACE_BUTTON_TEXT)),
        )
        disclosure_html = (
            '<details class="calendar-url-disclosure"><summary class="text-link">%s</summary>%s</details>'
        ) % (escape_html(i18n.t(CALENDAR_REPLACE_URL_SUMMARY)), replace_form_html)
        actions_html = (
            '<p class="calendar-actions">%s%s</p>' % (disclosure_html, disconnect_button_html))
        state_branch_html = masked_url_html + actions_html
    else:
        connect_form_html = (
            '<form method="post" action="/settings/calendar/connect" class="rule-add-form">'
            "%s"
            '<button type="submit">%s</button>'
            "</form>"
        ) % (
            field_html,
            escape_html(i18n.t(CALENDAR_CONNECT_BUTTON_TEXT)),
        )
        if drift:
            drift_actions_html = (
                '<p class="calendar-actions calendar-actions--solo">%s</p>'
                % disconnect_button_html)
        else:
            drift_actions_html = ""
        state_branch_html = connect_form_html + drift_actions_html

    how_it_works_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_SUMMARY)),
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_BODY)),
    )

    card_html = (
        '<div class="page-section" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "%s"
        "%s"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(CALENDAR_SECTION_HEADING)),
        escape_html(CALENDAR_HEADING_ID), escape_html(i18n.t(CALENDAR_SECTION_HEADING)),
        escape_html(i18n.t(CALENDAR_CAPTION)),
        status_html,
        state_branch_html,
        how_it_works_html,
    )

    if configured or drift:
        disconnect_form_html = (
            '<form id="%s" method="post" action="%s" data-confirm="%s" '
            'data-confirm-value="%s">'
            '<input type="hidden" name="%s" value="" data-confirm-field>'
            "</form>"
        ) % (
            escape_html(CALENDAR_DISCONNECT_FORM_ID),
            CALENDAR_DISCONNECT_ROUTE,
            escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_QUESTION)),
            escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
            CALENDAR_DISCONNECT_CONFIRM_FIELD,
        )
    else:
        disconnect_form_html = ""

    return card_html + disconnect_form_html


def calendar_disconnect_confirm_page(ctx):
    """19-11-PLAN.md Task 1 (D-08/A-26): the two-step server-rendered
    confirmation `_handle_calendar_disconnect_post()` (companion/app.py)
    renders at 200 whenever the posted confirm field is not exactly
    `CALENDAR_DISCONNECT_CONFIRM_VALUE` — including a bare POST with no
    confirm field at all. This page IS the security-relevant control: it
    holds with JavaScript disabled, with the script blocked by CSP, or
    against a hand-crafted request that skips
    `companion/static/confirm-submit.js`'s native `confirm()` entirely.

    The form posts back to the SAME route with the confirm field
    pre-filled to the accepted value and a real, plain submit button —
    the one and only way this page itself can cause a disconnect. The
    cancel path is a plain link back to the Display page (20-07-PLAN.md
    Task 1, D-11: Calendar moved from Device to Display this phase, so
    this is the page the disconnect action itself now lives on), never a
    second form (nothing to submit, nothing to confirm). Every dynamic
    value passes through `escape_html()`, matching this file's universal
    escaping discipline; `ctx` is accepted (unused today) for the same
    reason `render()`'s own scoped builders all take it — so a future
    reader adding a ctx-derived detail here never has to widen this
    function's own signature to do it.
    """
    return (
        layout.page_header(i18n.t(CALENDAR_DISCONNECT_CONFIRM_HEADING))
        + '<p class="text-body">%s</p>'
        '<form method="post" action="%s">'
        '<input type="hidden" name="%s" value="%s">'
        '<button type="submit">%s</button>'
        "</form>"
        '<p><a class="text-label" href="%s">%s</a></p>'
    ) % (
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_SENTENCE)),
        CALENDAR_DISCONNECT_ROUTE,
        CALENDAR_DISCONNECT_CONFIRM_FIELD, escape_html(CALENDAR_DISCONNECT_CONFIRM_VALUE),
        escape_html(i18n.t(CALENDAR_DISCONNECT_CONFIRM_BUTTON_TEXT)),
        layout.DISPLAY_ROUTE, escape_html(i18n.t(CALENDAR_DISCONNECT_CANCEL_TEXT)),
    )


def poll_trigger_section(cooldown_remaining):
    """The CFG-07 manual-trigger control: an enabled button when
    `cooldown_remaining` is zero, or a native-disabled button plus the
    D-17 remaining-seconds copy otherwise.

    D-18/A-35 (19-04-PLAN.md): this function emits ZERO `<script>`
    elements on either branch. The D-01 live countdown and the UXA-15
    disable-on-submit affordance both moved into
    `companion/static/poll-cooldown.js`, served pre-auth from
    `companion/app.py`'s `POLL_COOLDOWN_SCRIPT_ROUTE`, so
    `companion/app.py`'s Content-Security-Policy can set
    `script-src 'self'` with no `'unsafe-inline'` and no nonce. What
    used to be Python-interpolated through the now-removed
    `_js_literal()` is instead exposed as `data-*` attributes on the
    button, every one routed through `escape_html()` here:
      `data-cooldown` — the disabled branch's server-computed remaining
        seconds (D-01: `poll_cooldown_remaining()`'s history_db-
        persisted figure, so it survives a service restart and stays
        correct across multiple tabs — never re-derived client-side
        from `POLL_COOLDOWN_S`), absent on the enabled branch;
      `data-cooldown-text-id` / `data-cooldown-template` /
        `data-cooldown-token` — the disabled branch's countdown-paragraph
        id and its `POLL_COOLDOWN_HELPER_TEXT` template plus
        substitution token, both formatted here exactly as before;
      `data-submit-pending` — the enabled branch's UXA-15
        `POLL_SUBMIT_PENDING_TEXT` label, swapped in client-side on
        submit.
    A browser with JavaScript disabled still sees exactly the same
    server-rendered copy and markup as before this change; the
    countdown/disable-on-submit affordances are UX only, never a trust
    boundary — companion/app.py's `_handle_poll_now()` independently
    re-checks the cooldown server-side, and its `_POLL_LOCK`
    independently serializes execution, before it would ever call
    `poll_loop.run_once()`.

    quick task 260901-s5o: the section's single muted caption
    (`POLL_SECTION_CAPTION`) renders first on both branches, landing
    directly under the `<h2 class="text-heading">Poll</h2>` heading that
    `render()` — not this function — emits immediately before this
    function's output. A caption emitted on only one branch would
    silently disappear for the whole cooldown window, which is why
    `caption_html` is computed once above the branch rather than inline
    in each return.
    """
    # `> 0`, not truthy: must agree with companion/static/poll-cooldown.js's
    # own `remaining > 0` guard (after its `parseInt()`/`isNaN()` gate), or
    # a negative value would take this branch (natively disabling the
    # button) while the script inertly no-ops, leaving no way to
    # re-enable it client-side.
    caption_html = (
        '<p class="text-label section-caption">%s</p>'
        % escape_html(i18n.t(POLL_SECTION_CAPTION)))
    if cooldown_remaining > 0:
        translated_helper_text = i18n.t(POLL_COOLDOWN_HELPER_TEXT)
        cooldown_text = translated_helper_text.format(n=cooldown_remaining)
        template = translated_helper_text.format(n=POLL_COOLDOWN_TEMPLATE_TOKEN)
        return (
            "%s"
            '<form method="post" action="/poll-now">'
            '<button type="submit" id="%s" disabled '
            'data-cooldown="%s" data-cooldown-text-id="%s" '
            'data-cooldown-template="%s" data-cooldown-token="%s">'
            "%s</button>"
            "</form>"
            '<p class="text-body" id="%s">%s</p>'
        ) % (
            caption_html,
            POLL_TRIGGER_BUTTON_ID,
            escape_html(str(cooldown_remaining)),
            escape_html(POLL_COOLDOWN_TEXT_ID),
            escape_html(template),
            escape_html(POLL_COOLDOWN_TEMPLATE_TOKEN),
            escape_html(i18n.t("Trigger poll now")),
            POLL_COOLDOWN_TEXT_ID,
            escape_html(cooldown_text),
        )
    return (
        "%s"
        '<form method="post" action="/poll-now">'
        '<button type="submit" id="%s" data-submit-pending="%s">'
        "%s</button>"
        "</form>"
    ) % (
        caption_html,
        POLL_TRIGGER_BUTTON_ID,
        escape_html(i18n.t(POLL_SUBMIT_PENDING_TEXT)),
        escape_html(i18n.t("Trigger poll now")),
    )


# ---------------------------------------------------------------------
# Phase 15 D-10/D-11 (15-05-PLAN.md): the per-flight colour-rules editor —
# an add form (its own immediate POST route) plus an always-present list
# (empty state, or a cards-then-table pairing) with a plain per-row Delete
# button (its own immediate POST route). Mirrors airlines_page.py's own
# manual-resolutions management-list decomposition one-for-one: a delete-
# action URL builder, a row/table/card-list renderer trio, and a section
# assembler.
# ---------------------------------------------------------------------


def _rule_delete_action(kind, value):
    """The delete form's `action` attribute for `(kind, value)` — the
    two-segment shape `/settings/rules/{kind}/{value}/delete` (D-09's
    store key is `(kind, value)`, so the delete action must identify
    both). Both segments are already-normalised, already-allowlisted
    uppercase alphanumerics by the time a row reaches this function
    (`colour_rules.rule_rows()`'s own contract, re-checked again at read
    time by `load_colour_rules()`), so `escape_html()` on each segment is
    the only encoding needed — mirrors `airlines_page._manual_delete_
    action()`'s own one-string-builder-for-both-renderers discipline, so
    the desktop `<tr>` and the mobile `<li>` can never diverge into
    building two different strings for the same row.
    """
    return "%s%s/%s%s" % (
        RULES_DELETE_ROUTE_PREFIX, escape_html(kind), escape_html(value),
        RULES_DELETE_ROUTE_SUFFIX,
    )


def _rule_kind_radio_html(kind, checked):
    """One native radio + `<label>` pair for the "Match by" segmented
    control (D-15b, 20-UI-SPEC.md Structural Note 5's own resolution:
    native radios styled as the existing `.theme-form`/`.theme-option`
    segmented control, chosen over three JS-driven `<button>`s — zero
    degraded state, which is why this section ships no new client-side
    script at all). The radio is visually hidden
    (`companion/static/style.css`'s
    `.theme-form input[type="radio"] + label` rule styles the adjacent
    `<label>` at the segmented control's own geometry); the plain-
    language word (`RULE_KIND_LABELS`) is the visible label text, and
    the technical term (`RULE_KIND_TITLES`) is the label's own `title`
    attribute — a sighted mouse user who hovers still finds the exact
    vocabulary phase 15 shipped, never conflated with the visible label.
    """
    radio_id = "rule-kind-%s" % kind
    return (
        '<input type="radio" name="rule_kind" id="%s" value="%s" '
        'class="visually-hidden"%s>'
        '<label for="%s" title="%s">%s</label>'
    ) % (
        escape_html(radio_id), escape_html(kind), " checked" if checked else "",
        escape_html(radio_id), escape_html(i18n.t(RULE_KIND_TITLES[kind])),
        escape_html(i18n.t(RULE_KIND_LABELS[kind])),
    )


def _rule_add_form_html(errors=None, submitted=None):
    """The one-line add form (D-15b, 20-UI-SPEC.md Section Anatomy F):
    a `role="radiogroup"` of three NATIVE radio inputs styled as the
    segmented control (`_rule_kind_radio_html()` above — the THIRD
    consumer of `.theme-form`/`.theme-option`, after the UI-theme picker
    and this same phase's language switch), a value input, the compact
    theme-chip grid (`_theme_chip_grid_html()`'s `extra_class=
    "theme-chip-grid--compact"` — the SECOND consumer of that modifier,
    after Calendar's own grid) and an "Add rule" button — one `<form
    method="post">` targeting `RULES_ADD_ROUTE`, styled to read as one
    line via `.rule-add-form--inline` rather than `_rule_add_form_html()`'s
    old column-stack `.rule-add-form`.

    Per-segment placeholders ("AFR1234"/"3944F2"/"AFR") are a
    progressive enhancement this phase does not ship (D-15b) — naming
    the omission here so it stays greppable and deliberate rather than
    forgotten: no script exists to swap the placeholder on selection, so
    one static placeholder (`RULE_VALUE_PLACEHOLDER`) covers the
    always-valid default kind (callsign/"Flight"). Validation errors
    render under the field (phase 19 D-07 idiom), keeping the typed
    value — `errors`/`submitted` are both fully defaulted so the one
    live call site (the rules usage panel built by
    `frame_colours_section_html()`, since 21-05) keeps calling this
    with neither, unaffected by this addition.
    """
    selected_kind = _submitted_or_current(
        submitted, "rule_kind", colour_rules.RULE_KIND_CALLSIGN)
    kind_radios = "".join(
        _rule_kind_radio_html(kind, kind == selected_kind)
        for kind in colour_rules.RULE_KINDS)
    kind_error_html = _field_error_html(errors, "rule_kind", "rule-kind")

    submitted_value = submitted.get("rule_key", "") if submitted is not None else ""
    value_error_attrs = _field_error_attrs(errors, "rule_key", "rule-key")
    value_error_html = _field_error_html(errors, "rule_key", "rule-key")

    selected_theme_id = _submitted_or_current(
        submitted, "rule_theme_id", device_config.THEME_IDS[0])
    theme_error_html = _field_error_html(errors, "rule_theme_id", "rule-theme")
    # 27-07-PLAN.md Task 2 (CFG-68): DELIBERATELY NOT WRAPPED IN
    # `_theme_carousel_html()`, unlike departures/arrivals/calendar above
    # — recorded here, greppable, so this reads as a decision and not an
    # oversight for a later plan to "finish". This grid lives inside the
    # per-flight rules ADD FORM, part of the "règles par vol" view the
    # brief explicitly defers as too vague to plan against; folding a
    # control into a view that is about to be redesigned spends work
    # twice and pre-commits a decision the deferred conversation is
    # supposed to make. PROVISIONAL: if the developer wants this grid
    # folded too, it is one more call to `_theme_carousel_html()` with
    # one more id — the helper already supports it (Task 1).
    chip_grid_html = _theme_chip_grid_html(
        "rule_theme_id", selected_theme_id,
        extra_class="theme-chip-grid--compact", chip_extra_class="theme-chip--compact",
        extra_attr='role="radiogroup" aria-labelledby="%s"' % escape_html(RULE_THEME_HEADING_ID))

    return (
        '<form method="post" action="%s" class="rule-add-form rule-add-form--inline">'
        '<div class="rule-add-form__field rule-add-form__field--kind" role="radiogroup" '
        'aria-labelledby="%s">'
        '<span id="%s" class="visually-hidden">%s</span>'
        '<div class="theme-form">%s</div>'
        "%s"
        "</div>"
        '<div class="rule-add-form__field">'
        '<label for="rule-key" class="visually-hidden">%s</label>'
        '<input type="text" id="rule-key" name="rule_key" maxlength="8" '
        'required autocomplete="off" placeholder="%s" value="%s"%s>'
        "%s"
        "</div>"
        '<div class="rule-add-form__field">'
        '<span id="%s" class="visually-hidden">%s</span>'
        "%s"
        "%s"
        "</div>"
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        RULES_ADD_ROUTE,
        escape_html(RULE_KIND_HEADING_ID),
        escape_html(RULE_KIND_HEADING_ID), escape_html(i18n.t(RULE_KIND_FIELD_LABEL)),
        kind_radios,
        kind_error_html,
        escape_html(i18n.t(RULE_VALUE_FIELD_LABEL)),
        escape_html(RULE_VALUE_PLACEHOLDER), escape_html(submitted_value), value_error_attrs,
        value_error_html,
        escape_html(RULE_THEME_HEADING_ID), escape_html(i18n.t("Theme")),
        chip_grid_html,
        theme_error_html,
        escape_html(i18n.t(RULE_ADD_BUTTON_TEXT)),
    )


def _rule_suggestion_chips_html(state_dir):
    """Up to five distinct recent callsigns as suggestion chips (D-15e,
    20-UI-SPEC.md Section Anatomy F): `history_db.recent_runway_events()`
    — the SAME call `home_page._recent_flights()` already makes
    (`companion/pages/__init__.py` forbids importing that page module
    directly, so this is an independent second call to the same shared
    server-side helper, never a page-to-page import). `<button
    type="button">` elements, inert without JS — this phase ships no
    script to wire them (D-15e's own stated no-JS floor: "with no JS the
    chips are plain text", meaning the fill-on-click behaviour is inert,
    not that the markup disappears — matching the segmented control's
    own "degrades to inert, never to invisible" convention above).

    Returns "" when there are no recent events, or on any read failure —
    never raises, matching `home_page._safe_query()`'s own fail-soft
    contract for the identical class of read.
    """
    try:
        with history_db.open_db(state_dir) as conn:
            rows = history_db.recent_runway_events(conn, limit=20)
    except Exception:
        return ""
    seen = []
    for row in rows:
        callsign = row.get("callsign")
        if callsign and callsign not in seen:
            seen.append(callsign)
        if len(seen) >= 5:
            break
    if not seen:
        return ""
    chips = " · ".join(
        '<button type="button" class="rule-suggestion-chip" data-kind="callsign" '
        'data-value="%s">%s</button>' % (escape_html(cs), escape_html(cs))
        for cs in seen)
    return '<p class="text-label rule-suggestions">%s %s</p>' % (
        escape_html(i18n.t(RULE_SUGGESTIONS_LABEL)), chips)


def _rule_row_html(kind, value, theme_id):
    """One `<li class="rule-row">` (D-15c, 20-UI-SPEC.md Section
    Anatomy F): the theme's two palette dots drawn as `.theme-chip__dot`
    spans inside a `.rule-row__swatch theme-chip__swatches` wrapper
    (reusing the exact dot markup the compact chip grid already draws,
    never a second swatch component), the key in `.mono`, a
    `.rule-row__kind` badge composing `.banner__pill` verbatim with the
    plain-language kind word (never colour-coded — colour stays reserved
    for the swatch column only, 20-UI-SPEC.md §F's own explicit
    instruction), the theme's display name, and a Remove form.

    The Remove form's `data-confirm` (D-15c, LOCKED): `companion/static/
    confirm-submit.js` already handles any `form[data-confirm]`
    generically and degrades to a plain, uneventful submit with no
    `data-confirm-field`/`data-confirm-value` present — `_handle_rule_
    delete()` (companion/app.py) requires no confirm value of its own,
    so this is a misclick guard only, matching this list's own
    "immediately reversible, re-adding the same key restores it"
    classification (20-UI-SPEC.md's Destructive-confirmations table);
    D-15c's own locked text keeps the attribute anyway. `_rule_delete_
    action()`'s URL builder is unchanged.
    """
    departing_hex = _palette_hex(device_config.THEMES[theme_id]["departing_index"])
    arriving_hex = _palette_hex(device_config.THEMES[theme_id]["arriving_index"])
    swatch_html = (
        '<span class="rule-row__swatch theme-chip__swatches" aria-hidden="true">'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        '<span class="theme-chip__dot" style="background:%s"></span>'
        "</span>"
    ) % (escape_html(departing_hex), escape_html(arriving_hex))
    delete_form = (
        '<form method="post" action="%s" data-confirm="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        _rule_delete_action(kind, value),
        escape_html(i18n.t(RULE_REMOVE_CONFIRM_QUESTION)),
        escape_html(i18n.t(RULE_REMOVE_BUTTON_TEXT)),
    )
    return (
        '<li class="rule-row">'
        "%s"
        '<span class="rule-row__key mono">%s</span>'
        '<span class="rule-row__kind banner__pill">%s</span>'
        '<span class="rule-row__theme">%s</span>'
        "%s"
        "</li>"
    ) % (
        swatch_html,
        escape_html(value),
        escape_html(i18n.t(RULE_KIND_LABELS.get(kind, kind))),
        # Polish fix 5 (D-05): translated at this display site, same as
        # _theme_chip_grid_html()'s own label above.
        escape_html(i18n.t(device_config.theme_label(theme_id))),
        delete_form,
    )


def _rule_list_html(rows):
    """`<ul class="rule-list">`, one `.rule-row` per row (D-15c) —
    replaces the retired table/card split outright: the row shape is
    already responsive at every viewport, so there is no longer a
    `>=960px`/`<960px` split to maintain. `colour_rules.rule_rows()`
    already orders `rows` most-specific first (callsign, then hex, then
    prefix) and alphabetically within each kind — no re-sort needed
    here. Returns "" for an empty list; the rules usage panel
    (`frame_colours_section_html()`, 21-05) renders
    the empty state instead in that case (never called on the empty
    branch in practice, kept total for the same reason its two retired
    predecessors were).
    """
    if not rows:
        return ""
    items = "".join(
        _rule_row_html(kind, value, theme_id)
        for kind, value, theme_id, _created_at in rows)
    return '<ul class="rule-list">%s</ul>' % items


def _nested_wrapper_html(html_fragment, base_class, nested_class):
    """Appends the `--nested` modifier to a group builder's own outer
    wrapper class (20-07-PLAN.md Task 1, 20-UI-SPEC.md Section Anatomy
    C): a card rendered under one of Display's three supersections
    carries `theme-status--nested`/`page-section--nested` so its own
    `<h2>` renders one rung below the supersection's own heading (the
    extended `.theme-status--nested > h2`/`.page-section--nested > h2`
    selector, 20-04-PLAN.md Task 1) rather than the un-nested 22px serif
    tier Device's own groups keep. `nested_class` is passed as a literal
    string by every call site (never derived from `base_class` at
    runtime) so the modifier this function actually emits stays
    grep-visible in this file's own source, matching every sibling
    class-literal already written out in full throughout this module.

    Every group builder in this file emits its outer wrapper's class
    attribute exactly once, as the literal substring `class="{base_class}"`
    (grep-confirmed above, each function) — never as a second, inner
    occurrence — so a single, count-limited `str.replace()` is the whole
    mechanism: no builder's own signature or internals change, matching
    this task's own "relocates and re-wraps, never rebuilds" scope.
    """
    needle = 'class="%s"' % base_class
    replacement = 'class="%s %s"' % (base_class, nested_class)
    return html_fragment.replace(needle, replacement, 1)


def _display_groups_html(builders, groups):
    """The Display scope's two remaining headed supersections (D-12,
    21-UI-SPEC.md Section Anatomy C, restructured by 21-05-PLAN.md Task
    1 D-06 and 21-07-PLAN.md Task 1): "What it watches" over Runway,
    "When it is on" over Screen on/off and Quiet hours — each grouped
    card gains the `--nested` modifier (`_nested_wrapper_html()` above).
    Replaces the flat `"".join(builders[g]() ...)` join the Device and
    legacy all-scope paths still use unchanged (this task's own
    instruction: leave those two untouched).

    Returns a 2-tuple `(watches_supersection_html, on_supersection_
    html)`.

    21-05-PLAN.md Task 1 (D-06, Structural Note 2): the "Look" intro
    heading and the Frame colours card that replaces Theme are no
    longer this function's concern at all — `render()`'s own Display
    branch builds that pair directly (it needs `ctx`/`errors`/
    `submitted`/`state_dir`, none of which this function receives), as
    a sibling of `<form id="{SETTINGS_FORM_ID}">` positioned BEFORE
    Calendar. The physical form therefore now wraps zero visible
    content on the Display scope (only `render()`'s own hidden scope
    fields) — every saved control that used to live inside it (the
    departures/arrivals/calendar theme radios) now cross-submits via
    `form="{SETTINGS_FORM_ID}"` from outside it instead, exactly as
    Calendar's own chip grid already did before this task retired it
    (D-06) and as Runway/Screen/Quiet hours already do.

    21-07-PLAN.md Task 1 (D-13/Pitfall 2): the Calendar card is ALSO no
    longer this function's concern, and — unlike Frame colours — it is
    also no longer a member of the generic `builders` dict at all
    (`render()` calls the merged `calendar_group()` directly). The
    merged card now embeds its own connect/replace `<form>` in every
    state (D-13's "not connected" branch always shows one), which would
    nest inside `<form id="{SETTINGS_FORM_ID}">` on the legacy SCOPE_ALL
    render if `calendar_group()` stayed in `builders` — the same reason
    Frame colours left that dict in 21-05. `render()` builds the merged
    card directly, as a sibling of the physical form, exactly like Frame
    colours; SCOPE_ALL (never served) simply loses Calendar content, the
    same accepted, documented consequence 21-05-PLAN.md Task 1 already
    established for Theme.

    20-07-PLAN.md Task 2 (D-19/Pitfall 1): Screen on/off and Quiet hours
    are no longer literal descendants of `<form id="{SETTINGS_FORM_ID}">`
    (their own instant-switch `<form>`s would otherwise nest inside it,
    which HTML forbids), so "When it is on"'s own header and both its
    cards must render as a unit AFTER `</form>` closes.

    Polish fix 4 (D-14c), still true: "What it watches" (Runway) is ALSO
    not a literal descendant of `<form id="{SETTINGS_FORM_ID}">` — its
    own radio inputs instead carry an explicit
    `form="{SETTINGS_FORM_ID}"` attribute (`runway_fieldset()`'s own
    docstring). `render()` emits the Frame colours section, then the
    merged Calendar card, then this function's `watches_supersection_
    html`, then `on_supersection_html`, in that order — keeping the
    locked Look/What it watches/When it is on reading order across the
    form boundary.
    """
    runway_html = (
        _nested_wrapper_html(builders[screens.GROUP_RUNWAY](), "theme-status", "theme-status--nested")
        if screens.GROUP_RUNWAY in groups else "")
    # Polish fix 4 (D-14c), unchanged by the D-06 restructure above:
    # "What it watches" (Runway) renders AFTER `<form id=
    # "{SETTINGS_FORM_ID}">` closes — a sibling, not a literal
    # descendant.
    watches_supersection_html = (
        layout.section_intro_html(
            DISPLAY_WATCHES_SECTION_ID, i18n.t(DISPLAY_WATCHES_HEADING),
            i18n.t(DISPLAY_WATCHES_INTRO))
        + runway_html
    )
    # 20-07-PLAN.md Task 2: quiet_hours_group() is called here (still,
    # exactly as before this task — the same dict-of-lambdas `builders`
    # this function has always read from), but its OWN return value is a
    # card that carries scheduled inputs bound to SETTINGS_FORM_ID via
    # the form= attribute, never itself joined into anything rendered
    # inside the physical form. 22-05-PLAN.md Task 1 (X1/D-04/D-12.1):
    # display_group()/screens.GROUP_DISPLAY are gone outright — the
    # Frame strip is the only Screen on/off control left, so this
    # supersection now renders only the Quiet hours schedule card.
    quiet_hours_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_QUIET_HOURS](), "theme-status", "theme-status--nested")
        if screens.GROUP_QUIET_HOURS in groups else "")
    on_supersection_html = (
        layout.section_intro_html(
            DISPLAY_ON_SECTION_ID, i18n.t(DISPLAY_ON_HEADING), i18n.t(DISPLAY_ON_INTRO))
        + quiet_hours_html
    )
    return watches_supersection_html, on_supersection_html


def _device_groups_html(builders, groups):
    """28-04-PLAN.md Task 1 (CFG-72): the Device scope's own two headed
    supersections, mirroring `_display_groups_html()`'s shape — "When it
    wakes" over Wake interval alone, "How it tells you" over Diagnostic
    LED and Notifications together (the grouping argument is recorded
    on the module constants above this function). Replaces the flat
    `"".join(builders[g]() for g in groups if g in builders)` join the
    Device branch used before this task; the legacy SCOPE_ALL branch's
    own byte-identical copy of that flat join is untouched — this
    helper is Device-scope-only, called from nowhere else.

    Unlike `_display_groups_html()` above (whose two supersection
    headings always render, even when their one card is itself absent),
    this helper omits a supersection's own heading entirely when EVERY
    card it would introduce is absent — an intro sentence introducing
    nothing is worse than the flat join it replaces. The check is `g in
    builders`, preserving the original flat join's own tolerance: a
    group missing from `builders` (not merely absent from `groups`)
    renders neither its card nor an orphaned heading.
    """
    wake_interval_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_WAKE_INTERVAL](), "theme-status", "theme-status--nested")
        if screens.GROUP_WAKE_INTERVAL in groups and screens.GROUP_WAKE_INTERVAL in builders
        else "")
    wakes_supersection_html = (
        (layout.section_intro_html(
            DEVICE_WAKES_SECTION_ID, i18n.t(DEVICE_WAKES_HEADING), i18n.t(DEVICE_WAKES_INTRO))
         + wake_interval_html)
        if wake_interval_html else "")

    led_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_LED](), "theme-status", "theme-status--nested")
        if screens.GROUP_LED in groups and screens.GROUP_LED in builders else "")
    notifications_html = (
        _nested_wrapper_html(
            builders[screens.GROUP_NOTIFICATIONS](), "theme-status", "theme-status--nested")
        if screens.GROUP_NOTIFICATIONS in groups and screens.GROUP_NOTIFICATIONS in builders
        else "")
    tells_cards_html = led_html + notifications_html
    tells_supersection_html = (
        (layout.section_intro_html(
            DEVICE_TELLS_SECTION_ID, i18n.t(DEVICE_TELLS_HEADING), i18n.t(DEVICE_TELLS_INTRO))
         + tells_cards_html)
        if tells_cards_html else "")

    return wakes_supersection_html + tells_supersection_html


# 28-08-PLAN.md Task 1 (CFG-77/CFG-78), 2026-09-16: _save_status_region_
# html() — the auto-save status region's own builder, its `role="status"`
# + `aria-live="polite"` shape, and its EMPTY-at-rest, data-*-attribute-
# carried-words construction — is DELETED outright along with the region
# it built. The developer asked for the pre-27-04 dirty save bar back,
# not a reporting region beside a fetch that no longer exists. See the
# region's own former constants' superseded comment above (beside
# DIRTY_SAVING_TEXT) for the full account of what replaced it and why.


def render(ctx, scope=SCOPE_ALL, errors=None, submitted=None):
    """Render one settings page (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE).

    19-07-PLAN.md Task 2 (D-07/A-25): `errors` and `submitted` are both
    fully-defaulted keyword parameters placed last, so every one of the
    46 pre-Phase-19 call sites keeps producing byte-identical output.
    `companion/app.py`'s `_handle_settings_post()` is the sole caller
    that passes both, on a rejected save: `errors` is the dict
    `config_page.handle_post()` just filled, and `submitted` is the raw
    form dict, threaded straight through to every group builder via the
    `builders` dict below so each control can repopulate its own field
    and render its own error message.

    `errors` is normalised to `{}` here (harmless either way — every
    lookup below already treats `None`/`{}` identically). `submitted` is
    deliberately NOT collapsed to `{}`: `None` (every ordinary page-load
    render) and an actual dict (a real, possibly-empty submission being
    repopulated) mean different things to the absent-means-unchecked
    checkbox fields (`_submitted_checkbox_checked()`) — collapsing that
    distinction away would render every checkbox in that family
    unchecked on every ordinary page load, since an ordinary load never
    "submits" any of them either.
    """
    if errors is None:
        errors = {}
    device_cfg = ctx.get("device_config") or {}
    current_theme_id = device_cfg.get("theme", device_config.DEFAULT_THEME_ID)
    # Phase 15 D-04: an explicit `.get()` with no `or` fallback and no
    # default — `None` is a meaningful value here (no arrivals-theme
    # override, same as the departures theme), the same reasoning
    # current_wake_interval_s's own read below already carries.
    current_theme_arriving = device_cfg.get("theme_arriving")
    current_runway_id = device_cfg.get(
        "tracked_runway", device_config.DEFAULT_RUNWAY_ID)
    current_led_enabled = device_cfg.get(
        "led_enabled", device_config.DEFAULT_LED_ENABLED)
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): current_quiet_enabled is no
    # longer read here — quiet_hours_group() no longer renders an on/off
    # checkbox at all (the Frame strip is the only control for it), so
    # there is nothing left on this page to pre-fill from that value.
    current_quiet_start = device_cfg.get(
        "quiet_hours_start", device_config.DEFAULT_QUIET_HOURS_START)
    current_quiet_end = device_cfg.get(
        "quiet_hours_end", device_config.DEFAULT_QUIET_HOURS_END)
    # D-07 (11-UI-SPEC.md): an explicit `is None` test, not `or` — `0` is
    # never a valid wake_interval_s (WAKE_INTERVAL_MIN_S is 60), but `or`
    # would still be the wrong idiom to reach for here even so. Falls back
    # to ctx["wake_interval_env_default"], the deployed SKYPANE_SLEEP_S
    # value plan 11-04 reads out of the companion process's own environment
    # (systemd injects it via the same EnvironmentFile=/opt/skypane/
    # skypane.env directive skypane-byos.service uses). That key is absent
    # — resolving to None, i.e. the placeholder empty state — on any local
    # or dev run without the systemd unit.
    current_wake_interval_s = device_cfg.get("wake_interval_s")
    if current_wake_interval_s is None:
        current_wake_interval_s = ctx.get("wake_interval_env_default")
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): current_display_enabled is no
    # longer read here either — display_group() is retired outright, and
    # the Frame strip (companion/layout.py, fed straight from device_cfg
    # itself) is the only remaining renderer of the screen's on/off state.
    # Phase 16 (16-05-PLAN.md): read fresh per request, matching every
    # other ctx-threaded value in this function. An explicit `.get()` with
    # no `or` fallback — `None` is meaningful here (no calendar theme
    # chosen yet, default to the base theme), the same reasoning
    # current_theme_arriving's own read above already carries.
    current_calendar_theme_id = device_cfg.get("calendar_theme_id")
    calendar_configured = ctx.get("calendar_configured")
    calendar_last_synced_at = ctx.get("calendar_last_synced_at")
    # 20-09-PLAN.md Task 1 (D-14b): two new context keys, read fresh per
    # request exactly like calendar_last_synced_at above (companion/
    # app.py's page_context() computes both from the SAME load_calendar_
    # registry() call already made for calendar_last_synced_at, never a
    # second read). last_attempt_at is what distinguishes "just
    # connected, no sync yet" from "has been failing" — entry_count is
    # the status row's own detail template's flight count.
    calendar_last_attempt_at = ctx.get("calendar_last_attempt_at")
    calendar_entry_count = ctx.get("calendar_entry_count") or 0
    # Phase 17 plan 03 (D-02): plan 17-04 supplies this context key
    # (calendar_rules.calendar_secret_mode_is_unsafe(state_dir)). Until
    # then this degrades to a falsy default rather than raising, matching
    # how calendar_configured/calendar_last_synced_at above already read.
    calendar_drift = ctx.get("calendar_drift")
    # 20-11-PLAN.md Task 1 (D-26/D-28): read fresh from the SAME device_cfg
    # dict already loaded above, mirroring current_led_enabled's own
    # .get()-with-a-documented-default shape — a device_config.json
    # predating this field (or a genuinely absent one) resolves through
    # server.device_config.DEFAULT_NOTIFICATIONS, never a KeyError.
    current_notifications = device_cfg.get("notifications") or device_config.DEFAULT_NOTIFICATIONS
    notifications_configured = bool(current_notifications.get("topic_url"))
    current_notifications_battery = current_notifications.get(
        "battery_low", device_config.DEFAULT_NOTIFICATIONS["battery_low"])
    current_notifications_silent = current_notifications.get(
        "frame_silent", device_config.DEFAULT_NOTIFICATIONS["frame_silent"])
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)
    # 19-12-PLAN.md Task 3 (D-13): the same next-wake + layout.
    # local_clock_text() pipeline home_page.py's Frame tile uses,
    # computed once here and threaded into every caption site below via
    # _with_next_wake() plus rendered again in the Device header slot.
    # None when the value is unknown (no check-in yet, or no known
    # interval) — every consumer already treats a falsy value as "omit
    # the suffix/line entirely" (D-13: "where the value is known").
    #
    # 22-05-PLAN.md Task 2 (D-04): reads wake.next_wake_status()'s full
    # `(next_wake_iso, effective_interval_s, hold_reason)` triple now,
    # not just next_wake_at_iso()'s bare ISO string — `next_wake_iso`
    # itself is byte-identical either way (next_wake_at_iso() is a thin
    # wrapper over this same call, 22-02-PLAN.md Task 1), so every
    # existing reader of `next_wake_iso`/`next_wake_clock` below is
    # unaffected. The two new elements feed `frame_state.
    # delay_sentence_template()` (below) for the Quiet hours caption's
    # own computed delay sentence — the SAME triple the Frame strip's
    # own captions already read (22-04-PLAN.md), so the two can never
    # disagree; this is the file's own single next-wake call for this
    # value (comment at the frame_strip_html() call site below).
    next_wake_clock = None
    next_wake_iso, next_wake_effective_interval_s, next_wake_hold_reason = wake.next_wake_status(
        ctx.get("last_checkin_ts"), device_cfg)
    if next_wake_iso:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = layout.local_clock_text(
                next_wake_parsed, now_parsed=layout.parse_iso(ctx.get("now")))
    # 22-05-PLAN.md Task 2 (D-04): the ONE computed delay sentence for
    # Quiet hours' own caption, chosen by frame_state's three branches
    # from the SAME triple above — never a second, independent
    # computation. Degrades to DELAY_UNKNOWN's own translated text
    # (rather than emitting a literal "%s") on the rare case where the
    # template names a clock but none could be resolved above.
    quiet_hours_delay_template = frame_state.delay_sentence_template(
        next_wake_iso, next_wake_effective_interval_s, next_wake_hold_reason)
    # Branches on frame_state's own return value for equality, then
    # translates one of THIS module's own scanner-visible local copies —
    # never the imported constant directly — matching companion/
    # layout.py's identical pattern (see the constants' own comment
    # above for why).
    if quiet_hours_delay_template == frame_state.DELAY_DUE:
        quiet_hours_delay_sentence = i18n.t(_QUIET_HOURS_DELAY_DUE_TEXT)
    elif quiet_hours_delay_template == frame_state.DELAY_HELD:
        quiet_hours_delay_sentence = i18n.t(_QUIET_HOURS_DELAY_HELD_TEXT)
    else:
        quiet_hours_delay_sentence = i18n.t(frame_state.DELAY_UNKNOWN)
    if "%s" in quiet_hours_delay_sentence:
        if next_wake_clock:
            quiet_hours_delay_sentence = quiet_hours_delay_sentence % next_wake_clock
        else:
            quiet_hours_delay_sentence = i18n.t(frame_state.DELAY_UNKNOWN)

    # D-05 (06.6.4.1): the LED group used to be a sibling page-section,
    # appended AFTER the Poll section, rather than a third fieldset
    # inside this form — 06.3-UI-SPEC.md line 181 locked a 2-column grid
    # over this form's fieldsets at >=960px, and a third fieldset there
    # would have become a silent 2+1 orphan row. That grid is deleted
    # outright by 06.6.4.1-01 (D-01) — the premise this comment used to
    # describe no longer exists, so the LED group (led_group(), below) is
    # now a third sibling group inside this same <form>, after Runway,
    # before the bottom Save settings button. Do not restore the
    # separate section by reading a stale rationale.
    #
    # D-03: data-dirty-form is a JS-only enhancement layered on top of
    # this always-server-rendered form — dirty-state.js reads it to find
    # the form the restored bar (below) now watches.
    #
    # 27-04-PLAN.md Task 3 (D-04/D-06/CFG-63): the dirty save bar that
    # used to render here — quick task 260901-re6's own account of why it
    # was a SIBLING of this form, positioned `fixed` — was superseded by
    # this plan's own auto-save status region, ALWAYS-empty-at-rest,
    # placed beside the page's own heading.
    #
    # SUPERSEDED IN TURN by 28-08-PLAN.md (CFG-77/CFG-78), 2026-09-16:
    # the developer asked for the bar back (ROADMAP.md's Phase 28
    # addendum). The status region this paragraph described is deleted;
    # its replacement is the `.dirty-bar` markup built below and emitted
    # LAST in render()'s own return tuple, after `</form>` and after the
    # Poll section — a SIBLING of this form again, exactly where
    # `6dea46a` put it and for the identical reason its own comment gave
    # (a `position: fixed` bar nested inside this short form would get
    # the form's own box as its containing block and visibly detach —
    # see Task 2's style.css comment for the CSS half of that argument).
    #
    # The native fallback Save button (STATIC_SAVE_FALLBACK_ATTR) is the
    # SAME element as 27-03's own construction (CFG-64's AST-level proof
    # still pins it to render()'s one unconditional return, unedited) —
    # it MOVES, from a slot inside this `<form>...</form>` to a slot
    # inside the bar's own markup below, with a `form="%s"` attribute
    # added so it keeps submitting this form natively from outside it.
    # It is not a second button: CFG-78 requires exactly one save
    # affordance, and this relocation is what keeps that true while also
    # making it the bar's own visible Save.
    #
    # THE VISIBILITY POLARITY INVERTS, and this is the plan's most
    # important non-obvious decision (stated once here, in full, then
    # referenced by name everywhere else it matters). The pre-27-04 bar
    # was server-rendered `hidden`, because a no-JS visitor still had a
    # SEPARATE always-visible bottom Save button to fall back to. That
    # second button no longer exists — the fallback Save IS the bar's
    # Save now — so the bar's own server-rendered state must BE the
    # no-JS floor: it renders VISIBLE by default, and dirty-state.js
    # hides it at init once it has proven itself live, then reveals it
    # whenever countDifferences() > 0. A future reader who copies
    # `6dea46a`'s `hidden` back onto this markup would silently remove
    # the only way a scripts-blocked visitor can save — do not do that.
    #
    # Two consequences of the inversion, both first-class here because a
    # scripts-blocked visitor now sees EVERYTHING inside the bar, so
    # everything inside it must WORK without script or say nothing:
    #   1. Cancel (below) is a native `<button type="reset"
    #      form="%s">`, never `type="button"` — a `type="button"` with
    #      no script is a fully visible, fully inert control that does
    #      literally nothing when clicked, with no explanation. A native
    #      reset restores every field with zero script; dirty-state.js
    #      then layers its own enhancement on top (Task 3) rather than
    #      BEING the behaviour.
    #   2. `[data-dirty-count]` renders EMPTY — `<span
    #      data-dirty-count></span>`, no seeded text of any kind. Seeding
    #      it with DIRTY_BAR_INITIAL_TEXT (the pre-27-04 shape, when the
    #      bar around it was `hidden` and nobody saw the seed) would now
    #      show "Unsaved changes"/"Modifications non enregistrées" to
    #      every scripts-blocked visitor on every fresh page load, and
    #      `role="status"` would have an assistive-tech reader announce
    #      it — a permanent, loudly-announced false claim, and the exact
    #      opposite of this plan's own "the no-JS floor got STRONGER"
    #      objective. dirty-state.js is the count span's only writer,
    #      and it writes only once countDifferences() > 0.
    #
    # Every translated word below is computed once here, before the
    # single `return` — none of these seven local variables is
    # STATIC_SAVE_FALLBACK_ATTR itself, so none of this precomputation
    # touches the AST invariant `_the_native_submit_is_emitted_
    # unconditionally_on_every_render()` pins (that check requires
    # STATIC_SAVE_FALLBACK_ATTR to reach render()'s own return as a bare
    # name — see that button's own args in the return's tuple, below).
    dirty_changed_suffix_html = escape_html(i18n.t(DIRTY_CHANGED_SUFFIX))
    dirty_and_html = escape_html(i18n.t(DIRTY_AND))
    dirty_list_and_html = escape_html(i18n.t(DIRTY_LIST_AND))
    dirty_unsaved_singular_html = escape_html(i18n.t(DIRTY_UNSAVED_SINGULAR))
    dirty_unsaved_plural_html = escape_html(i18n.t(DIRTY_UNSAVED_PLURAL))
    dirty_saving_html = escape_html(i18n.t(DIRTY_SAVING_TEXT))
    dirty_initial_text_html = escape_html(i18n.t(DIRTY_BAR_INITIAL_TEXT))

    # 21-05-PLAN.md Task 1 (D-06, Structural Note 2): the per-flight
    # rules editor is no longer a standalone sibling section at all — it
    # relocated, verbatim, into the Frame colours card's own "Per-flight
    # rules" usage panel (see _frame_colours_card_html()'s own
    # docstring). Every existing group's DOM nesting above stays
    # byte-identical; only Theme's own former slot is gone.
    screen_id = screens.current_screen_id(ctx)
    screen = screens.screen_type(screen_id)
    if scope not in SCOPES:
        scope = SCOPE_ALL
    groups = scope_groups(scope, screen_id)

    # 21-05-PLAN.md Task 1 (D-06): screens.GROUP_THEME has no entry in
    # this dict any more — theme_fieldset() is retired outright, and its
    # replacement (_frame_colours_card_html(), below) is built directly
    # by render()'s own Display branch rather than through this generic
    # per-group dict, because it needs ctx/errors/submitted/state_dir
    # AND because its own rules panel contains real <form> elements that
    # must never render as a literal descendant of <form id=
    # "{SETTINGS_FORM_ID}"> (the same constraint that already kept
    # Flight colours out of this dict). 21-07-PLAN.md Task 1 (D-13/
    # Pitfall 2): screens.GROUP_CALENDAR has no entry here either any
    # more, for the identical reason — the merged calendar_group() now
    # embeds its own connect/replace <form> in EVERY state, which would
    # nest inside <form id="{SETTINGS_FORM_ID}"> on the legacy SCOPE_ALL
    # render if left in this dict. render()'s own Display branch calls
    # calendar_group() directly instead, as a sibling of the physical
    # form, exactly like Frame colours. On the legacy SCOPE_ALL/Device
    # paths below, `groups_html`'s own `"".join(builders[g]() for g in
    # groups if g in builders)` loop simply skips screens.GROUP_THEME/
    # screens.GROUP_CALENDAR now (both are still members of
    # `scope_groups(SCOPE_ALL)`'s fixed tuple, just no longer present in
    # `builders`) — SCOPE_ALL is the legacy, never-served whole-page
    # render, so this is a deliberate, documented behaviour change to
    # that path, not an oversight.
    builders = {
        screens.GROUP_RUNWAY: lambda: runway_fieldset(
            current_runway_id, ctx.get("runway_images") or (),
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock),
        screens.GROUP_LED: lambda: led_group(
            current_led_enabled, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock),
        screens.GROUP_QUIET_HOURS: lambda: quiet_hours_group(
            current_quiet_start, current_quiet_end,
            errors=errors, submitted=submitted, delay_sentence=quiet_hours_delay_sentence),
        # 25-05-PLAN.md Task 1 (CFG-49): the battery series is read
        # INSIDE the lambda, so it is read only on a scope that actually
        # renders this group (Device and the legacy SCOPE_ALL) and never
        # on Display — `builders` is a dict of thunks precisely so an
        # entry costs nothing until its group is in scope.
        screens.GROUP_WAKE_INTERVAL: lambda: wake_interval_group(
            current_wake_interval_s, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock,
            battery_rows=wake_battery_rows(ctx.get("state_dir"), ctx.get("now"))),
        # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1): screens.GROUP_DISPLAY has
        # no entry here any more — display_group() is retired outright,
        # matching screens.GROUP_THEME/screens.GROUP_CALENDAR's own
        # precedent for a group with no generic per-group renderer.
        screens.GROUP_NOTIFICATIONS: lambda: notifications_group(
            notifications_configured, current_notifications_battery,
            current_notifications_silent, errors=errors, submitted=submitted),
    }
    # 20-11-PLAN.md Task 1 (D-19/Pitfall 1): "Send a test" is its own
    # immediate-POST form and must never nest inside <form id=
    # "settings-form"> — rendered as a sibling, after </form> closes,
    # exactly like the merged Calendar card's own disconnect form below.
    # screens.GROUP_NOTIFICATIONS is never a member of scope_groups(
    # SCOPE_DISPLAY) or the legacy SCOPE_ALL tuple, so this is correctly
    # "" on both of those scopes.
    notifications_test_html = (
        notifications_test_section() if screens.GROUP_NOTIFICATIONS in groups else "")
    # 23-07-PLAN.md Task 2 (D2/CFG-36): the LED switch's own form, for
    # the identical reason and in the identical position as the
    # Send-a-test form above — an immediate-action <form> can never nest
    # inside <form id="settings-form">, so it renders after </form>
    # closes and its button reaches it across the DOM. "" on every scope
    # that does not render the LED group.
    quick_led_html = (
        quick_led_form_html(current_led_enabled) if screens.GROUP_LED in groups else "")
    # 19-12-PLAN.md Task 2 (D-23): the conditional selector joins the
    # screen caption in BOTH scoped headers' action_html slot — with
    # today's single-member registry it renders as "", so both headers
    # stay byte-identical to their pre-D-23 output.
    if scope == SCOPE_DISPLAY:
        # 23-06-PLAN.md Task 2 (D1/CFG-35): the Display scope refreshes
        # itself, because it renders the Frame strip and a stale claim
        # about the frame's state costs most there. The freshness line is
        # the shared builder's — the same one Health and Home call — and
        # it carries `data-loaded-at`, which companion/static/
        # freshness.js requires before it does anything.
        #
        # What this page declares as swappable is the strip and this line
        # and nothing else (layout.REFRESH_SWAP_SELECTORS_BY_PAGE's own
        # comment says why): everything below is a <form>, and a swap
        # that lands on a half-edited form is B1 with a new cause. The
        # loop additionally stands the whole cycle down while the save
        # bar reports unsaved edits.
        header = layout.page_header(
            i18n.t(DISPLAY_PAGE_TITLE), purpose=i18n.t(DISPLAY_PAGE_PURPOSE),
            freshness_html=layout.freshness_line_html(ctx.get("now")),
            action_html=_screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors))
        # 21-04-PLAN.md Task 1 (D-02/R-01): the shared Frame strip, once,
        # directly after the page header and before the "Look"
        # supersection's own section_intro_html() (the first thing
        # groups_html renders, below) — the exact same next_wake_iso
        # already computed above for next_wake_clock feeds it, so there
        # is no second wake.next_wake_at_iso() call for the same value.
        frame_strip_section_html = layout.frame_strip_html(
            ctx, return_to=layout.DISPLAY_ROUTE, next_wake_iso=next_wake_iso)
        hidden_html = _scope_fields_html(scope, layout.DISPLAY_ROUTE)
        # 20-07-PLAN.md Task 1 (D-10/D-11), narrowed by 21-05-PLAN.md
        # Task 1 (D-06): the calendar-disconnect form moves to Display
        # with its group; Poll (Manual refresh) stays Device-only,
        # unaffected by this move. Flight colours is no longer a
        # standalone section at all (its own show_rules flag is gone
        # along with _rules_section_html() — see frame_colours_section_
        # html below).
        show_poll = False
        # 21-05-PLAN.md Task 1 (D-06, Structural Note 2): the "Look"
        # intro heading plus the Frame colours card render here, as a
        # SIBLING of <form id="{SETTINGS_FORM_ID}"> — not through the
        # generic per-group `builders` dict (see its own comment above)
        # — because the rules panel it now holds contains real <form>
        # elements. `groups_html` (the form's own visible content) is
        # therefore empty on this scope: every saved theme radio now
        # cross-submits from outside the form via `form=
        # "{SETTINGS_FORM_ID}"`, exactly like Runway/Calendar already
        # do (Structural Note 2's own "the physical form becomes a pure
        # submission target").
        frame_colours_section_html = (
            layout.section_intro_html(
                DISPLAY_LOOK_SECTION_ID, i18n.t(DISPLAY_LOOK_HEADING), i18n.t(DISPLAY_LOOK_INTRO))
            + _nested_wrapper_html(
                _frame_colours_card_html(
                    ctx, current_theme_id, current_theme_arriving, current_calendar_theme_id,
                    errors=errors, submitted=submitted, state_dir=ctx.get("state_dir")),
                "page-section frame-colours", "page-section--nested")
            if screens.GROUP_THEME in groups else "")
        # 21-07-PLAN.md Task 1 (D-13/Pitfall 2): the merged Calendar card
        # is built directly here — never through the generic `builders`
        # dict (see that dict's own comment above) — because it embeds
        # its own connect/replace <form> in every state; nested-wrapped
        # exactly like Runway used to be through _display_groups_html().
        display_calendar_card_html = (
            _nested_wrapper_html(
                calendar_group(
                    calendar_configured, calendar_drift, calendar_last_synced_at,
                    calendar_last_attempt_at, ctx.get("now"), calendar_entry_count,
                    errors=errors, submitted=submitted, state_dir=ctx.get("state_dir")),
                "page-section", "page-section--nested")
            if screens.GROUP_CALENDAR in groups else "")
        groups_html = ""
        (display_watches_supersection_html,
            display_on_supersection_html) = _display_groups_html(builders, groups)
    elif scope == SCOPE_DEVICE:
        # 19-12-PLAN.md Task 3 (D-13): "Home and Device show" — the
        # Next-wake line joins the screen caption/selector in the same
        # action_html slot (Display instead carries the per-caption
        # suffixes via next_wake_clock threaded into the builders dict
        # above).
        # 20-07-PLAN.md Task 3 (D-36): the Edit-artwork link that used to
        # join this same slot is gone outright.
        header = layout.page_header(
            i18n.t(DEVICE_PAGE_TITLE), purpose=i18n.t(DEVICE_PAGE_PURPOSE),
            action_html=(
                _screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors)
                + _next_wake_caption_html(next_wake_clock)))
        hidden_html = _scope_fields_html(scope, layout.DEVICE_ROUTE)
        # 21-04-PLAN.md Task 1 (D-01/D-02): the Frame strip renders only
        # on Home and Display — never on Device.
        frame_strip_section_html = ""
        # 20-07-PLAN.md Task 1 (D-10/D-11): the Calendar group (and its
        # merged disconnect form) is no longer a Device concern at all —
        # it moved to Display's everyday_groups this phase, and
        # 21-07-PLAN.md Task 1 removed screens.GROUP_CALENDAR from
        # `builders` entirely, so Device's own render never builds it.
        # 21-05-PLAN.md Task 1 (D-06): Flight colours is no longer a
        # standalone section anywhere — its own show_rules flag is gone
        # along with _rules_section_html().
        show_poll = bool(screen.get("has_manual_poll"))
        # 20-07-PLAN.md Task 1 (D-10): Device's own advanced_groups no
        # longer includes GROUP_DISPLAY/GROUP_QUIET_HOURS at all (both
        # moved to Display's everyday_groups), so this flat join never
        # calls display_group()/quiet_hours_group() on this scope —
        # their own instant-switch <form> never has a chance to nest
        # inside this scope's <form id="settings-form">. screens.
        # GROUP_THEME is also never a member of Device's advanced_groups
        # (only ever Display's everyday_groups/SCOPE_ALL's legacy
        # tuple), so its absence from `builders` (above) changes
        # nothing here either.
        # 28-04-PLAN.md Task 1 (CFG-72): the flat join is replaced by
        # `_device_groups_html()`, which wraps each card exactly like
        # Display's own cards are wrapped and introduces them under two
        # named supersections — see that function's own docstring and
        # the module constants above it for the grouping argument. The
        # legacy SCOPE_ALL branch below keeps its own, byte-identical
        # copy of the flat join this replaces; that copy is deliberately
        # untouched.
        groups_html = _device_groups_html(builders, groups)
        frame_colours_section_html = ""
        display_calendar_card_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""
    else:
        header = layout.page_header(i18n.t("Settings"))
        hidden_html = ""
        # 21-04-PLAN.md Task 1 (D-01/D-02): SCOPE_ALL is the legacy,
        # never-served whole-page render (see its own comment two lines
        # below) — it never carried the Screen/Quiet-hours instant
        # switches even before this task, so it carries no Frame strip
        # either.
        frame_strip_section_html = ""
        show_poll = True
        # SCOPE_ALL is the legacy whole-page render, kept byte-identical
        # to its own pre-Phase-19 output for existing harness checks
        # against the full form — never used by a live app.py route
        # (render()'s own module comment). The disconnect action's own
        # confirmed-form flow is new surface Task 1 adds only to the two
        # live scoped pages; SCOPE_ALL stays exactly as it was.
        # 21-05-PLAN.md Task 1 (D-06): screens.GROUP_THEME is still a
        # member of scope_groups(SCOPE_ALL)'s own fixed tuple, but this
        # flat join now silently skips it (it has no entry in `builders`
        # any more) — SCOPE_ALL's legacy render loses its own former
        # Theme content as a direct, documented consequence of retiring
        # theme_fieldset() outright; Flight colours (which this scope
        # used to render as a separate sibling section) is gone the
        # same way, for the same reason. 21-07-PLAN.md Task 1 (D-13/
        # Pitfall 2): the Calendar group is gone from SCOPE_ALL for the
        # identical reason — screens.GROUP_CALENDAR has no entry in
        # `builders` any more either.
        groups_html = "".join(builders[g]() for g in groups if g in builders)
        frame_colours_section_html = ""
        display_calendar_card_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""

    poll_section_html = (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>" % (escape_html(i18n.t(POLL_SECTION_HEADING)), poll_trigger_section(cooldown_remaining))
        if show_poll else "")
    # 28-04-PLAN.md Task 1 (CFG-72): the fourth Device card, wrapped with
    # the Poll card's OWN modifier below (the wrapper this card actually
    # emits is a `.page-section`, not a `.theme-status`) under its own
    # one-card supersection, "When you can't wait" — DEVICE-SCOPE-ONLY.
    # Computed here rather than gating `poll_section_html` itself, so
    # the legacy SCOPE_ALL branch's own `poll_section_html` (built once,
    # above, shared by both scopes via the identical `show_poll` gate)
    # reaches the return tuple below byte-identical to its pre-task
    # output.
    poll_supersection_html = (
        (layout.section_intro_html(
            DEVICE_POLL_SECTION_ID, i18n.t(DEVICE_POLL_HEADING), i18n.t(DEVICE_POLL_INTRO))
         + _nested_wrapper_html(poll_section_html, "page-section", "page-section--nested"))
        if scope == SCOPE_DEVICE and poll_section_html else "")

    return (
        header
        # 21-04-PLAN.md Task 1 (D-02/R-01): the shared Frame strip
        # renders immediately after the page header and before the
        # form (whose own groups_html opens with the "Look"
        # supersection's own section_intro_html()) — "" on Device and
        # SCOPE_ALL.
        + frame_strip_section_html
        + '<form class="config-form" id="%s" data-dirty-form method="post" action="%s">'
        "%s"
        "%s"
        "</form>"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        # 28-08-PLAN.md Task 1 (CFG-77/CFG-78), 2026-09-16: the restored
        # `.dirty-bar` — LAST in this tuple, after `</form>` and after
        # the Poll section, exactly where `6dea46a` put it (see the
        # comment above this return's own local-variable block for the
        # full reasoning: sticky/fixed positioning needs a containing
        # block wider than this short form). Emitted on every scope
        # (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE), matching data-dirty-
        # form's own scope-independent emission.
        #
        # NO `hidden` attribute — the no-JS-floor inversion this
        # function's own comment above explains in full: this bar's
        # server-rendered visible state IS the floor now, because there
        # is no second, separate fallback button any more.
        #
        # `[data-dirty-count]` is `<span data-dirty-count></span>` —
        # EMPTY, no seeded text — for the identical reason: a seeded
        # claim would be a false, `role="status"`-announced "Unsaved
        # changes" shown to every scripts-blocked visitor on every fresh
        # load.
        #
        # Inside, in order: the count span, the Save button, the Cancel
        # button — matching `6dea46a`'s own document order.
        #
        # The Save button is `STATIC_SAVE_FALLBACK_ATTR`'s OWN element,
        # relocated here from its former slot inside `<form>...</form>`
        # above (never a second button — CFG-78 requires exactly one).
        # `form="%s"` is what lets it keep submitting the physical form
        # natively from outside it, the same `form=` idiom Runway/
        # Calendar's own cross-tree controls already use. Kept NAMELESS
        # (no `name=` attribute) — a named submitter would contribute an
        # entry to the form's own data set, and dirty-state.js's Task 3
        # relabelSubmitter() stands down on any submitter that carries
        # one.
        #
        # The Cancel button is a NATIVE `type="reset"`, never
        # `type="button"` — `6dea46a` used `type="button"` and relied
        # entirely on script, which was safe only because its own bar
        # was `hidden` without one. With the polarity inverted, a
        # `type="button"` here would be a fully visible, fully inert
        # control for every scripts-blocked visitor. A native reset,
        # `form=`-associated the same way the Save is, restores every
        # field to its last-rendered value with zero script;
        # dirty-state.js's Task 3 enhancement then layers the three
        # things a native reset alone cannot do (hide the bar, suppress
        # the leave-guard, refresh the theme preview and repaint the
        # quiet-hours dial) on top of that native behaviour, rather than
        # reimplementing it.
        '<div class="dirty-bar" data-dirty-bar role="status" '
        'data-dirty-changed-suffix="%s" data-dirty-and="%s" '
        'data-dirty-list-and="%s" data-dirty-unsaved-singular="%s" '
        'data-dirty-unsaved-plural="%s" data-dirty-saving="%s" '
        'data-dirty-initial-text="%s">'
        "<span data-dirty-count></span>"
        '<button type="submit" class="dirty-bar__save" form="%s" %s>%s</button>'
        '<button type="reset" form="%s" class="dirty-bar__cancel" data-dirty-cancel>%s</button>'
        "</div>"
    ) % (
        SETTINGS_FORM_ID,
        SETTINGS_ROUTE,
        hidden_html,
        groups_html,
        # 21-05-PLAN.md Task 1 (D-06, Structural Note 2): the "Look"
        # intro heading plus the Frame colours card now render
        # immediately after `</form>` closes, BEFORE the Calendar card
        # — restoring the locked Look-heading -> Frame colours ->
        # Calendar reading order, now entirely outside the physical
        # form. Always "" on the Device/SCOPE_ALL paths (both set it to
        # "" explicitly above).
        frame_colours_section_html,
        # 21-07-PLAN.md Task 1 (D-13/Pitfall 2): the merged Calendar
        # card, nested-wrapped exactly like Runway, now renders here —
        # after the Frame colours section — carrying its own connect/
        # replace form and, when connected or drifted, its own data-only
        # disconnect form as a trailing sibling fragment, both already
        # concatenated into this one string by calendar_group() itself.
        # Always "" on Device/SCOPE_ALL (computed above).
        display_calendar_card_html,
        # 20-07-PLAN.md Task 1 (D-12), restructured by the D-12 fix
        # above: "What it watches"'s own header plus the Runway card —
        # always "" on the Device/SCOPE_ALL paths (both set it to ""
        # explicitly above), so this addition changes nothing for
        # either. On Display, this now renders AFTER the Calendar card
        # above, so Runway still follows Calendar in document order even
        # though neither is any longer a literal descendant of the same
        # <form>.
        display_watches_supersection_html,
        # 20-11-PLAN.md Task 1 (D-19/Pitfall 1): "" on Display/SCOPE_ALL
        # (computed above), so this addition changes nothing for either
        # — only the Device scope's own render gains this sibling form,
        # positioned right after the Notifications card's own in-form
        # content (inside groups_html above) and before Manual refresh.
        notifications_test_html,
        # 23-07-PLAN.md Task 2 (D2/CFG-36): the LED switch's own empty
        # form, a sibling of the settings form for the same reason the
        # Send-a-test form above is one. "" on Display/SCOPE_ALL.
        quick_led_html,
        # 20-07-PLAN.md Task 2 (D-19/Pitfall 1): "When it is on"'s own
        # header plus the Screen on/off and Quiet hours cards — always ""
        # on the Device/SCOPE_ALL paths (both set it to "" explicitly
        # above), so this addition changes nothing for either.
        display_on_supersection_html,
        # 28-04-PLAN.md Task 1 (CFG-72): the Device scope renders the
        # wrapped, supersection-introduced form of the Poll card
        # (`poll_supersection_html`); the legacy SCOPE_ALL branch (and
        # Display, which never sets `show_poll`) renders the original
        # bare `poll_section_html` unchanged — `poll_supersection_html`
        # is "" on both of those scopes by construction above.
        poll_supersection_html if scope == SCOPE_DEVICE else poll_section_html,
        # The bar's own seven data-* words, precomputed above this
        # return (see this function's own local-variable block for why
        # that precomputation does not touch the AST invariant).
        dirty_changed_suffix_html,
        dirty_and_html,
        dirty_list_and_html,
        dirty_unsaved_singular_html,
        dirty_unsaved_plural_html,
        dirty_saving_html,
        dirty_initial_text_html,
        # The Save button: form=, then STATIC_SAVE_FALLBACK_ATTR (a bare
        # name, directly inside this return's own args tuple — the
        # invariant `_the_native_submit_is_emitted_unconditionally_on_
        # every_render()` pins), then its label.
        SETTINGS_FORM_ID,
        STATIC_SAVE_FALLBACK_ATTR,
        escape_html(i18n.t("Save settings")),
        # The Cancel button: form=, then its label.
        SETTINGS_FORM_ID,
        escape_html(i18n.t("Cancel")),
    )


def _screen_caption_html(screen):
    """The small "Screen: Plane frame" line under a scoped page's title —
    the visible end of the companion/screens.py seam. Rendered as an
    already-safe block for page_header()'s `action_html` slot.
    """
    # Polish fix 5 (D-05): screen["label"] (device_config-adjacent
    # registry text, e.g. "Plane frame") is translated at this display
    # site via i18n.t() — the screen id itself never changes;
    # companion/i18n_fr/registry.py supplies the French entry ("Cadre
    # avion").
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(i18n.t(SCREEN_CAPTION_TEMPLATE) % i18n.t(screen["label"])))


NEXT_WAKE_HEADER_LABEL = "Next wake"
NEXT_WAKE_HEADER_VALUE_TEMPLATE = "≈ %s"


def _next_wake_caption_html(next_wake_clock):
    """The Device page header's own "Next wake ≈ HH:MM" line (D-13/S-02:
    "Home and Device show" — this is the Device half; Home's own copy
    lives in companion/pages/home_page.py). Returns the EMPTY STRING
    when `next_wake_clock` is falsy — no placeholder, no "unknown" —
    matching `_with_next_wake()`'s identical omit-when-unknown contract
    for the per-group caption suffixes.
    """
    if not next_wake_clock:
        return ""
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(
            "%s %s" % (
                i18n.t(NEXT_WAKE_HEADER_LABEL),
                i18n.t(NEXT_WAKE_HEADER_VALUE_TEMPLATE) % next_wake_clock)))


def _screen_selector_html(current_screen_id, errors=None):
    """A `<select name="screen_id">` letting the operator switch which
    registered screen type this settings page edits — 19-12-PLAN.md Task
    2 (D-23)'s explicit condition: returns the EMPTY STRING when
    `len(screens.SCREEN_IDS) <= 1` (a one-option "choice" has no real
    decision value, the same reasoning `theme_fieldset()`'s single-theme
    branch already applies), so with today's single-screen registry the
    Display/Device headers stay byte-identical to their pre-D-23 output.

    Rendered inside `layout.page_header()`'s `action_html` slot — i.e.
    visually and structurally BEFORE `<form id="{SETTINGS_FORM_ID}">`
    opens — but it must still submit with that form. The
    `form="{SETTINGS_FORM_ID}"` attribute is what makes that possible,
    the same "control lives outside the form's own DOM nesting but
    submits with it anyway" idiom `render()`'s own dirty-bar Save button
    already uses (see its own comment above).

    Every option's value and label are escaped at their interpolation
    point (labels come from the fixed `screens.SCREEN_TYPES` registry,
    never request data, but this file's universal escaping discipline
    applies with no exceptions). A visually-hidden `<label for=...>`
    supplies the control's accessible name, matching this file's
    settings-checkbox `<label>` convention rather than an `aria-label`
    attribute.

    `errors` (D-07, WR-01 follow-up: every sibling field this plan
    touches renders its own `_field_error_html()` message; this was the
    one field that did not) carries the D-23 gate's rejected-`screen_id`
    message, if any, rendered via `_field_error_html()` immediately after
    the `<select>` — no `submitted` repopulation parameter is needed
    here, unlike the text/select fields elsewhere in this file, because
    `current_screen_id` passed in above is already resolved by the
    caller (`screens.current_screen_id(ctx)`), the same "current value
    already reflects the rejected submission" reasoning `render()`'s own
    call sites rely on for every field.
    """
    if len(screens.SCREEN_IDS) <= 1:
        return ""
    options = []
    for screen_id in screens.SCREEN_IDS:
        selected = " selected" if screen_id == current_screen_id else ""
        label = screens.screen_type(screen_id)["label"]
        options.append(
            '<option value="%s"%s>%s</option>'
            % (escape_html(screen_id), selected, escape_html(label)))
    error_html = _field_error_html(errors, "screen_id", SCREEN_SELECTOR_ID)
    return (
        '<label class="visually-hidden" for="%s">%s</label>'
        '<select name="screen_id" id="%s" form="%s">%s</select>'
        "%s"
    ) % (
        SCREEN_SELECTOR_ID, escape_html(i18n.t(SCREEN_SELECTOR_LABEL_TEXT)),
        SCREEN_SELECTOR_ID, SETTINGS_FORM_ID, "".join(options),
        error_html,
    )


def _scope_fields_html(scope, return_route):
    return (
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="%s" value="%s">'
    ) % (
        SCOPE_FIELD_NAME, escape_html(scope),
        RETURN_TO_FIELD_NAME, escape_html(return_route),
    )


# Phase 17 plan 03 (D-07): the four outcomes of the submitted calendar
# fields' three-way resolution. Plain strings, never rendered and never
# travel in a URL. Kept as four distinct sentinels (not e.g. two bools)
# so a caller cannot mistake one outcome for another by falsy-comparing
# the wrong pair.
CALENDAR_URL_SIGNAL_CARRY_FORWARD = "carry_forward"
CALENDAR_URL_SIGNAL_SET = "set"
CALENDAR_URL_SIGNAL_CLEAR = "clear"
CALENDAR_URL_SIGNAL_INVALID = "invalid"

# D-07 (19-07-PLAN.md, A-25): handle_post()'s per-field error messages —
# one constant per rejected field, matching this file's
# constants-at-the-top convention, so the copy exists in exactly one
# place and _note_error() below never inlines a string literal. Sentence
# case, no requirement ids, no stack-trace vocabulary, matching the
# label voice every other user-facing string in this file already uses.
ERROR_INVALID_CHOICE = "That is not one of the available choices."
ERROR_UNEXPECTED_SWITCH_VALUE = "That switch sent an unexpected value."
ERROR_WAKE_INTERVAL_RANGE = "Enter a whole number of seconds between 60 and 3600."
ERROR_QUIET_HOURS_TIME_SHAPE = "Enter a time as HH:MM, for example 23:00."
# Covers both the over-length and the contradictory-submission
# (calendar_url + calendar_disconnect together) cases
# submitted_calendar_signal() folds into CALENDAR_URL_SIGNAL_INVALID —
# deliberately worded to never echo any part of the submitted URL back.
ERROR_CALENDAR_URL_INVALID = (
    "That link is too long, or conflicts with the disconnect option below.")

# A LOCAL copy of server/device_config.py's private `_HHMM_RE` (24-hour,
# zero-padded "HH:MM") — deliberately NOT an import of that name, which
# is private to that module (D-07's own read_first instruction). This is
# a UX pre-check only: save_device_config()'s own identical gate remains
# the authoritative one, and companion/test_config_page.py pins the two
# patterns against the same table of inputs so they cannot silently
# drift apart.
_QUIET_HOURS_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")


def _note_error(errors, field, message):
    """No-ops when `errors is None` — every existing caller of
    handle_post()/render() before this plan, and any future caller that
    still doesn't care about field-level errors. Otherwise sets
    `errors[field] = message` only if that field has no message yet:
    first error per field wins, so a later, more generic gate can never
    overwrite an earlier, more specific one.
    """
    if errors is None:
        return
    if field not in errors:
        errors[field] = message


def submitted_calendar_signal(form):
    """The single definition of what a submitted `calendar_url` +
    `calendar_disconnect` pair means. Both `handle_post()` below and plan
    17-04's request handler call this — never reimplement the logic — so
    the two can never drift into disagreeing about what a given
    submission meant.

    Resolution order, each a real gate a caller must clear before the
    next is even considered:

    1. A `calendar_disconnect` present with any value other than
       `CALENDAR_DISCONNECT_CHECKBOX_VALUE` is a crafted request shape,
       not a user mistake — the same treatment every other checkbox on
       this handler already gives a non-member value. Resolves invalid.
    2. A `calendar_disconnect` present together with a non-empty
       (stripped) `calendar_url` is contradictory: the operator has
       asked to disconnect and to connect in the same submission, and
       there is no defensible guess at which one they meant. Resolves
       invalid rather than picking one.
    3. A `calendar_disconnect` present (and clearing gate 2) resolves
       clear.
    4. An empty (or whitespace-only, or absent) `calendar_url` with no
       checkbox resolves carry-forward — THE branch the whole checkbox
       exists to make possible (D-07). D-01/D-02 make the field
       write-only, so it renders empty on EVERY page load regardless of
       state; an unrelated Settings save (changing a theme, say) would
       therefore submit it empty too. Treating that as a disconnect
       signal would disconnect the calendar on every save that doesn't
       touch the calendar at all — this is the exact defect D-07 exists
       to correct in D-04's original wording.
    5. A stripped `calendar_url` longer than `CALENDAR_URL_MAX_LEN`
       resolves invalid — a shape bound against an absurd paste, not a
       second definition of an acceptable URL (see CALENDAR_URL_MAX_LEN's
       own comment).
    6. Otherwise resolves set.

    Never raises, and never itself calls `calendar_rules.save_calendar_
    url()` — resolving the signal and acting on it are deliberately two
    separate steps so `handle_post()` can gate the persistence call
    behind the OTHER fields' validation first (the all-or-nothing
    contract) without this function needing to know about them.

    19-11-PLAN.md (D-08/A-26, 19-RESEARCH.md Pitfall 7): the in-form
    `calendar_disconnect` checkbox this function's gates 1-3 above were
    built to interpret is now RETIRED from `calendar_group()`'s own
    markup — disconnecting is `CALENDAR_DISCONNECT_ROUTE`'s own dedicated
    route (`companion/app.py`'s `_handle_calendar_disconnect_post()`),
    which never calls this function at all: that route always means
    "disconnect", once its own confirm gate passes, so consulting this
    resolver there would be dead weight. Gates 1-3 are DELIBERATELY LEFT
    IN PLACE rather than deleted, even though the ordinary rendered form
    can no longer produce a `calendar_disconnect` field: a hostile client
    can still craft that field directly into a `/settings` POST body, and
    `handle_post()`'s existing all-or-nothing rejection (via this
    function's `invalid` outcome) is what continues to cover that shape.
    Deleting the gates would not remove any real capability — it would
    just make a crafted request's outcome unspecified instead of
    correctly rejected.
    """
    # Phase 18: a page that never rendered the Calendar group cannot
    # have meant anything by the field's absence — carry forward before
    # any other gate is consulted.
    if screens.GROUP_CALENDAR not in scope_groups(submitted_scope(form)):
        return CALENDAR_URL_SIGNAL_CARRY_FORWARD
    raw_url = form.get("calendar_url")
    stripped_url = raw_url.strip() if isinstance(raw_url, str) else ""
    disconnect = form.get("calendar_disconnect")

    if disconnect is not None and disconnect != CALENDAR_DISCONNECT_CHECKBOX_VALUE:
        return CALENDAR_URL_SIGNAL_INVALID
    if disconnect is not None and stripped_url:
        return CALENDAR_URL_SIGNAL_INVALID
    if disconnect is not None:
        return CALENDAR_URL_SIGNAL_CLEAR
    if not stripped_url:
        return CALENDAR_URL_SIGNAL_CARRY_FORWARD
    if len(stripped_url) > CALENDAR_URL_MAX_LEN:
        return CALENDAR_URL_SIGNAL_INVALID
    return CALENDAR_URL_SIGNAL_SET


def handle_post(form, ctx, errors=None):
    """Validate the submitted theme/runway/LED/quiet-hours/wake-interval/
    display state against `device_config`'s own registries and validators —
    server-side, before any value is used anywhere — and persist all
    eight fields in a single `save_device_config()` call (D-05, 06.6.4.1:
    this handler absorbed what the now-retired `handle_led_post()` used to
    do on its own separate `POST /config-led` route — removed outright in
    06.6.4.1-07 once this route became the sole settings-writing path;
    10-05-PLAN.md extended the same single-call contract to the three
    quiet-hours fields, 11-03-PLAN.md extended it again to
    wake_interval_s, and 12-05-PLAN.md extends it again to
    display_enabled, rather than adding a second write path).

    Deliberately does NOT call any of `device_config`'s read-path
    normalising helpers (the ones an unrecognised on-disk value silently
    degrades through to the default): those implement the *read* path's
    forgiving behaviour, whereas a *write* of an unrecognised value is a
    real client error that must be reported back to the user, not
    silently coerced — the asymmetry is deliberate (06-CONTEXT.md
    D-06/D-07, 06-RESEARCH.md's V5 threat control). Instead, each
    submitted field is checked explicitly before it is ever used as a
    dict key or passed onward: `theme`/`tracked_runway` by membership
    test against `device_config.THEME_IDS`/`RUNWAY_IDS`, `led_enabled`/
    `quiet_hours_enabled`/`display_enabled` by exact equality against
    `LED_CHECKBOX_VALUE`/`QUIET_HOURS_CHECKBOX_VALUE`/
    `DISPLAY_CHECKBOX_VALUE`. `quiet_hours_start`/`quiet_hours_end`
    are passed straight through, unchecked, to `save_device_config()`
    itself — deliberately not pre-validated here against the HH:MM
    shape-gate regex `device_config` keeps as a private module-level
    name — because that function already validates both fields strictly
    against that same regex and raises `ValueError` before it ever
    touches the file, which this handler's existing
    `except (ValueError, OSError)` below already maps to the generic
    save-failed flash. All-or-nothing rejection holds because that
    validation happens before any write.

    Three properties are load-bearing here, not incidental:

    First (rewritten by 22-05-PLAN.md Task 1, X1/D-04/D-12.1, T-22-16;
    EXTENDED to the third flag by 23-07-PLAN.md Task 2, D2/CFG-36,
    T-23-25): all three checkbox flags now resolve absent -> `None`
    (leave unchanged), and the asymmetry this paragraph used to describe
    is GONE. `led_enabled` was the last field still resolving absent to
    `False`, which was correct only while its checkbox was still
    rendered on the Device page; that checkbox is replaced by a
    `role="switch"` posting to `/quick/led`, so no settings page renders
    a control for any of the three. `display_enabled` and
    `quiet_hours_enabled` reached the same place first (the Frame
    strip's own quick-toggle route, `companion/app.py`'s
    `_handle_quick_toggle()`, is the sole normal writer of both), so a
    field's absence from a `/settings` POST body no longer means "the
    user unticked a box that was on the page" — it means "this form
    never had a control for it at all".
    Resolving that to `False` (the pre-22-05 behaviour) was a real,
    severe bug hiding behind a since-retired UI affordance: it silently
    switched the physical screen and quiet hours OFF on every settings
    save that happened to omit the field — which, for two fields with no
    checkbox left anywhere, was EVERY settings save, including a save
    that only changed the theme. The frame going dark after a household
    member merely changes their theme is the exact regression this
    fix — and its own pinned four-starting-combination check — exists to
    prevent (22-RESEARCH.md's own named "blast radius severe enough to
    warrant the same rigor" risk, T-22-16). Both fields now resolve
    absent to `None` (leave unchanged) UNCONDITIONALLY: an explicit value
    still reaching this handler (a crafted request, or a legacy
    submission that still names the field) is still validated by exact
    equality against `DISPLAY_CHECKBOX_VALUE`/`QUIET_HOURS_CHECKBOX_VALUE`
    and still honoured when it matches, and an unexpected value still
    rejects the whole submission exactly as the third shape always has.
    So, for all three checkboxes, now symmetrically: absent -> `None`
    (unchanged), equal to the field's own `*_CHECKBOX_VALUE` -> `True`,
    anything else -> reject. The two notification checkboxes below are
    the only fields left with the in-scope-absent-means-False
    resolution, and they keep it because their checkboxes are still
    rendered — which is exactly the condition that made it correct for
    `led_enabled` until now.

    Second, an explicit `quiet_hours_start`/`quiet_hours_end` value still
    persists even when `quiet_hours_enabled` itself is absent or resolves
    to `False`/unchanged — this resolves 10-RESEARCH.md's Assumption A1 /
    Open Question 2 in the affirmative, per 10-UI-SPEC.md's locked
    Interaction Contract: a user can pre-configure a window whether or
    not Quiet hours is currently on. This is a decision, not an
    oversight.

    Third, rejection stays all-or-nothing across all eight fields, now more
    so than before the merge: because there is still one form and one
    `save_device_config()` call, a crafted or invalid value in ANY field
    aborts before that call, never persisting the valid remainder —
    applying only the valid half would leave the on-disk state out of
    sync with what the page would redisplay on the very next load.

    Fourth, `wake_interval_s` needs an explicit string-to-int conversion
    gate that `quiet_hours_start`/`quiet_hours_end` deliberately do not:
    those two fields are strings end-to-end and are correctly passed
    through unconverted, but `wake_interval_s` is an int end-to-end in
    `device_config.py`, so the same pass-through habit here would make
    `save_device_config()`'s type check reject every legitimate
    submission (11-RESEARCH.md Pitfall 1 — the single highest-risk
    copy-paste mistake in this phase). An absent or empty-string
    `wake_interval_s` resolves to `None`, meaning leave unchanged — a
    numeric input a user clears mid-edit is an incomplete edit, not an
    invalid one, and the all-or-nothing contract above is about invalid
    values (11-RESEARCH.md Open Question 2). Anything else is passed to
    `int()` inside a `try`, whose `ValueError` returns `FLASH_SAVE_FAILED`
    before any write; `save_device_config()`'s own range check raises
    `ValueError` for an out-of-bounds int, already mapped to the same
    generic flash by the `except (ValueError, OSError)` clause below — no
    field-specific error copy is added (11-UI-SPEC.md's Copywriting
    Contract locks reuse of the existing generic flash).

    Fifth (19-07-PLAN.md, D-07/A-25): `errors` is an optional
    caller-supplied dict, filled in place via `_note_error()` at every
    `FLASH_SAVE_FAILED` return site below, keyed on the submitted form
    field that failed. It is purely additive — the all-or-nothing
    rejection contract above is unchanged, and the return value is
    unchanged (still a bare flash-key string, never a tuple) — so every
    existing caller that does not pass `errors` behaves byte-identically
    to before this plan. Three new pre-checks join the existing gates
    below so a real user error (a malformed quiet-hours time, an
    out-of-range wake interval, an invalid calendar submission) is
    reported at that field instead of falling through to the generic
    `except (ValueError, OSError)` clause.

    On success, the frame's next scheduled poll cycle (server/poll_loop.py,
    D-06/D-28) is the first place any of the eight changes actually take
    effect — no push mechanism exists, and none is added here. The caller
    (companion/app.py) redirects back to `SETTINGS_ROUTE`, whose banner
    then renders the FLASH_SAVED confirmation copy — as of 22-05-PLAN.md
    Task 2 (D-04), one computed delay sentence derived from the same
    `wake.next_wake_status()` triple the Frame strip and every quiet-hours
    caption read, rather than a fixed literal — telling the user their
    change was saved but has not yet reached the physical frame. No
    quiet-hours-specific or display-specific flash message exists — saving
    reuses FLASH_SAVED/FLASH_SAVE_FAILED verbatim, per 10-UI-SPEC.md's/
    12-UI-SPEC.md's Copywriting Contract.

    Phase 16 (16-05-PLAN.md) adds one more form field, `calendar_theme_id`
    — a plain tracked field with no checkbox. It is validated by the
    identical membership test `theme`/`tracked_runway` already use (now
    also exempting the empty string, 21-05-PLAN.md Task 2 below) and
    passed through as one more keyword argument on the same,
    still-singular `save_device_config()` call.

    21-05-PLAN.md Task 2 (D-09/R-07, superseding Phase 15 D-04/D-05):
    the arrivals-override checkbox and its checkbox-keyed resolution
    are retired outright along with the Frame colours card's own
    leading "Same as departures" chip (Task 1) — the clear signal moves
    from that checkbox's absence to an empty submitted `theme_arriving`
    value.
    `theme_arriving`'s own membership gate now exempts the empty string
    in addition to a real theme id (`("",) + device_config.THEME_IDS`),
    and the resolution block derives `CLEAR_THEME_ARRIVING` directly
    from `submitted_theme_arriving == ""` — see the inline comment at
    that branch for the full three-way shape (out of scope -> `None`;
    absent -> `None`, carry forward; `""` -> the clear sentinel; a
    membership-checked id -> that id). `calendar_theme_id`'s own gate
    gets the identical `("",) + device_config.THEME_IDS` exemption
    (Pitfall 1: both gates change together, in the same commit, or the
    "Same as departures" option can never actually be saved) but needs
    no second resolution block of its own — it never had a checkbox,
    and `normalise_calendar_theme_id("")`'s own existing `None`-degrade
    contract already does the right thing once its gate stops
    rejecting `""` outright. The result is passed as one more keyword
    argument on the same, still-singular persistence call below; the
    all-or-nothing rejection contract is unchanged.

    Phase 17 plan 03 (D-01/D-02/D-07) adds `calendar_url` and
    `calendar_disconnect`, resolved by `submitted_calendar_signal()`
    above into exactly one of four outcomes rather than inline here, so
    plan 17-04's request handler can share the identical resolution. An
    `invalid` outcome joins the other membership gates below and rejects
    the whole save before `save_device_config()` is ever called — same
    all-or-nothing contract. The other three outcomes are acted on only
    AFTER that call succeeds, and only `set`/`clear` ever call
    `calendar_rules.save_calendar_url()` — `carry_forward` calls it not
    at all, because every successful call to that writer erases the
    fetched calendar registry (D-04/D-05), and calling it on a save that
    never touched the calendar field would silently wipe the calendar's
    flights on every unrelated settings change.

    `calendar_disconnect` is rendered unchecked always and its PRESENCE
    means clear — the deliberately safe direction, doing nothing by
    default — because D-01/D-02 make the calendar URL field write-only,
    so it is empty on every single page load regardless of state; an
    absent-means-clear checkbox here would disconnect the calendar on
    every save that doesn't touch it.

    The device-config write goes first, unchanged from every save that
    touches no calendar field, and the secret write is layered after it
    deliberately: this leaves a narrow window in which the device config
    has been written but the secret write then fails, but the operator
    sees the generic failure flash and can simply retry, and the
    alternative — writing the secret first — would perturb the ordering
    of every save in this handler, existing or new, to close a window
    that only opens when the state directory is already failing.

    19-12-PLAN.md Task 2 (D-23) adds one more form field, `screen_id`,
    submitted only by `_screen_selector_html()`'s `<select>` (itself
    only rendered once a second screen type is registered). It follows
    the exact membership-test-before-use shape every other
    hostile-request-shape gate above already uses: a non-`None` value
    outside `screens.SCREEN_IDS` rejects the whole save via
    `FLASH_SAVE_FAILED` before `save_device_config()` is ever called,
    and the validated value is passed through as one more keyword
    argument on the SAME, still-singular `save_device_config()` call —
    never a second write path. With today's single-member registry the
    field is never actually submitted by the real form, so this gate is
    exercised only by a crafted request.

    20-11-PLAN.md Task 1 (D-26/D-28) adds a fourth group,
    `screens.GROUP_NOTIFICATIONS`, and three more form fields:
    `notifications_topic_url`, `notifications_battery`,
    `notifications_silent`. The two checkboxes keep the
    in-scope-absent-means-False resolution `led_enabled` used to share
    (23-07-PLAN.md Task 2 narrows it to these two alone: all three of
    `display_enabled`/`quiet_hours_enabled`/`led_enabled` now resolve
    absent to `None` unconditionally, per this docstring's own First
    paragraph above). They keep it because their checkboxes are STILL
    RENDERED — 23-07 deliberately did not convert them, since they share
    a card with a Save-governed topic-URL field and no locked decision
    covers a card where some controls apply instantly and one waits for
    Save. A crafted value rejects the whole save, same as every sibling
    checkbox gate. The
    topic URL is genuinely different from every scalar field above: an
    empty (stripped) submission means "leave the stored URL unchanged"
    (this codebase's established empty-numeric-input convention,
    `wake_interval_s`'s own precedent), never "clear it" — there is no
    UI affordance to clear a configured topic URL in this plan, mirroring
    the calendar feed URL's own identical write-only "replace only"
    contract. Because `save_device_config(notifications=...)` REPLACES
    the whole sub-dict rather than merging per sub-key (unlike every
    scalar field, which the write path itself carries forward when
    `None`), this handler reads the CURRENT on-disk group via
    `device_config.load_device_config(state_dir)` and builds the
    complete replacement dict itself — `lang` is written from
    `ctx["lang"]`, the session's resolved language at save time (D-28:
    there is no language-picking control for this group anywhere on the
    page, because the poll loop has no browser to ask, 20-RESEARCH.md
    Pitfall 6).
    When `screens.GROUP_NOTIFICATIONS` is not in scope (every Display
    render, and the legacy SCOPE_ALL), `notifications` stays `None` and
    `save_device_config()` carries the current on-disk group forward
    unchanged, exactly like every field this handler does not own on
    that scope.
    """
    state_dir = ctx["state_dir"]
    # Phase 18: which groups were actually on the submitted page. A
    # checkbox belonging to a group that was NOT rendered is absent from
    # the body for a structural reason, not because the user unticked
    # it — so for those groups absence resolves to None (carry the
    # on-disk value forward), never to False.
    scope = submitted_scope(form)
    in_scope = set(scope_groups(scope, screens.current_screen_id(ctx)))
    submitted_theme = form.get("theme")
    submitted_theme_arriving = form.get("theme_arriving")
    submitted_runway = form.get("tracked_runway")
    submitted_led = form.get("led_enabled")
    submitted_qh_enabled = form.get("quiet_hours_enabled")
    submitted_qh_start = form.get("quiet_hours_start")
    submitted_qh_end = form.get("quiet_hours_end")
    submitted_wake_interval = form.get("wake_interval_s")
    submitted_display = form.get("display_enabled")
    submitted_calendar_theme_id = form.get("calendar_theme_id")
    submitted_calendar_url = form.get("calendar_url")
    submitted_screen_id = form.get("screen_id")
    submitted_notifications_topic_url = form.get("notifications_topic_url")
    submitted_notifications_battery = form.get("notifications_battery")
    submitted_notifications_silent = form.get("notifications_silent")
    calendar_signal = submitted_calendar_signal(form)

    if submitted_theme is not None and submitted_theme not in device_config.THEME_IDS:
        _note_error(errors, "theme", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # 19-12-PLAN.md Task 2 (D-23): the same membership-test-before-use
    # shape every sibling gate here already uses.
    if submitted_screen_id is not None and submitted_screen_id not in screens.SCREEN_IDS:
        _note_error(errors, "screen_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # Phase 17 plan 03 (D-07): the resolver's own `invalid` outcome joins
    # every other membership/shape gate here, before any write — a
    # crafted checkbox value, a contradictory URL+checkbox submission,
    # and an over-length URL are all rejected the identical way.
    if calendar_signal == CALENDAR_URL_SIGNAL_INVALID:
        _note_error(errors, "calendar_url", ERROR_CALENDAR_URL_INVALID)
        return FLASH_SAVE_FAILED
    # 20-11-PLAN.md Task 1 (D-26): a shape bound against an absurd paste,
    # mirroring CALENDAR_URL_SIGNAL_INVALID's own over-length check above
    # — only checked when the field is actually in scope (an out-of-scope
    # submission is structural, never a real user mistake, matching every
    # other in-scope gate below).
    if (
        screens.GROUP_NOTIFICATIONS in in_scope
        and submitted_notifications_topic_url
        and len(submitted_notifications_topic_url.strip()) > NOTIFICATIONS_URL_MAX_LEN
    ):
        _note_error(errors, "notifications_topic_url", ERROR_NOTIFICATIONS_URL_TOO_LONG)
        return FLASH_SAVE_FAILED
    # Phase 16 (16-05-PLAN.md, T-16-TAMPER's HTTP-layer half): same
    # membership-test shape as theme/theme_arriving above. A non-member
    # value is a hostile-request shape, not a genuine user mistake
    # (16-UI-SPEC.md Flash messages) — reuse the existing generic
    # save-failed flash, no new flash constant.
    # 21-05-PLAN.md Task 2 (D-09/R-07, Pitfall 1): both gates exempt the
    # empty string in addition to a real theme id — the Frame colours
    # card's own "Same as departures" leading chip (Task 1) submits ""
    # for exactly this field, and a gate that still rejected it would
    # reject the WHOLE save the instant a user picks that option. Every
    # other non-member value (a crafted id, a path-traversal-shaped
    # payload, a SQL-shaped payload) is still rejected exactly as before
    # — the empty string is carved out, the gate is not weakened.
    if (
        submitted_calendar_theme_id is not None
        and submitted_calendar_theme_id not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "calendar_theme_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if (
        submitted_theme_arriving is not None
        and submitted_theme_arriving not in ("",) + device_config.THEME_IDS
    ):
        _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if submitted_runway is not None and submitted_runway not in device_config.RUNWAY_IDS:
        _note_error(errors, "tracked_runway", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    # 19-07-PLAN.md Task 1 (D-07): a PRESENT-but-invalid quiet-hours time
    # is a real user error, reported at that field rather than falling
    # through to the generic save-failed flash via
    # save_device_config()'s own exception path below. Field ABSENT
    # (`None`) still means "leave unchanged" — including the structural
    # absence a scoped page that never rendered this group produces — so
    # only a submitted-but-malformed value (the empty string counts as
    # submitted) is checked here.
    if submitted_qh_start is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_start):
        _note_error(errors, "quiet_hours_start", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    if submitted_qh_end is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_end):
        _note_error(errors, "quiet_hours_end", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    # 21-05-PLAN.md Task 2 (D-09/R-07): the clear signal is now the
    # EMPTY STRING submitted for theme_arriving itself (the Frame
    # colours card's own leading "Same as departures" chip, Task 1) —
    # never a separate checkbox field, which no longer exists as a form
    # field at all. Three shapes only: out of scope -> `None`; the
    # field genuinely absent from the submission (a hostile/legacy
    # request missing it entirely) -> `None`, carry forward; `""` ->
    # `device_config.CLEAR_THEME_ARRIVING`; anything else has already
    # passed the membership gate above, so it is a real theme id.
    if screens.GROUP_THEME not in in_scope:
        theme_arriving = None
    elif submitted_theme_arriving is None:
        theme_arriving = None
    elif submitted_theme_arriving == "":
        theme_arriving = device_config.CLEAR_THEME_ARRIVING
    else:
        theme_arriving = submitted_theme_arriving
    # 23-07-PLAN.md Task 2 (D2/CFG-36, D-12.1, T-23-25): led_enabled now
    # resolves absent -> None (leave unchanged) UNCONDITIONALLY, the
    # identical shape quiet_hours_enabled below already has, and for the
    # identical reason. The Diagnostic LED's control is about to become
    # the Frame-strip-style switch on its own /quick/led route, so no
    # settings form renders a checkbox for this field any more —
    # absence from THIS body therefore means "this form never had a
    # control for it", not "the user unticked a box".
    #
    # THIS COMMIT LANDS BEFORE THE CONTROL MOVES, deliberately, so that
    # no commit in this repository's history has an LED checkbox absent
    # from the form while an absent field still means False. The reverse
    # order is not untidy, it is the live defect: every unrelated
    # settings save — a theme change, a wake-interval edit — would carry
    # no led_enabled and would silently switch the LED off. That is the
    # regression D-12.1 records and 22-05 already fixed twice, and the
    # eight-combination guard in companion/test_config_page.py now
    # covers all three flags rather than two.
    #
    # The scope test is gone with it: it was load-bearing only while the
    # absent branch resolved to False (it stopped a Display-scope save,
    # which never rendered the LED checkbox, from switching the LED off).
    # With absent meaning "unchanged" the scope makes no difference to
    # the outcome, so keeping the branch would be a condition that can
    # never change an answer — exactly the shape a later reader mistakes
    # for a live rule.
    if submitted_led is None:
        led_enabled = None
    elif submitted_led == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        _note_error(errors, "led_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1, T-22-16): quiet_hours_enabled
    # is no longer a form control ANY scope renders — the Frame strip is
    # the only place left that switches it, via its own separate quick-
    # toggle route (companion/app.py's _handle_quick_toggle(), an
    # entirely different write path that already passes an explicit
    # `quiet_hours_enabled=True/False` straight to
    # `device_config.save_device_config()`). Absence from THIS form's
    # body therefore means "this page never had a way to change it",
    # not "the user unticked a box" — resolving to `None` (leave
    # unchanged) UNCONDITIONALLY, regardless of scope, is what closes
    # the "a settings save switches quiet hours off" regression
    # (22-RESEARCH.md Pitfall 1). An explicit value — from a crafted or
    # legacy submission that still names this field — is still honoured,
    # and an unexpected value still rejects the whole save exactly as
    # before; only the "absent" branch's outcome changed.
    if submitted_qh_enabled is None:
        quiet_hours_enabled = None
    elif submitted_qh_enabled == QUIET_HOURS_CHECKBOX_VALUE:
        quiet_hours_enabled = True
    else:
        _note_error(errors, "quiet_hours_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    if submitted_wake_interval is None or submitted_wake_interval == "":
        wake_interval_s = None
    else:
        try:
            wake_interval_s = int(submitted_wake_interval)
        except ValueError:
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
        # 19-07-PLAN.md Task 1 (D-07): a syntactically valid but
        # out-of-range integer ("7") used to reach save_device_config()'s
        # own bounded-range ValueError and surface only as the generic
        # flash — reported at this field instead, before any write.
        if not (
            device_config.WAKE_INTERVAL_MIN_S
            <= wake_interval_s
            <= device_config.WAKE_INTERVAL_MAX_S
        ):
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
    # 22-05-PLAN.md Task 1 (X1/D-04/D-12.1, T-22-16): display_enabled
    # follows the identical unconditional-absent-means-unchanged
    # resolution quiet_hours_enabled's own comment above documents in
    # full — the Frame strip's quick-toggle route is the only remaining
    # writer of this field via a real settings-page control, and no
    # scope has ever rendered a display_enabled checkbox since
    # display_group() was retired in this same commit.
    if submitted_display is None:
        display_enabled = None
    elif submitted_display == DISPLAY_CHECKBOX_VALUE:
        display_enabled = True
    else:
        _note_error(errors, "display_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    # 20-11-PLAN.md Task 1 (D-26/D-28): the two checkboxes follow the
    # identical in-scope-absent-means-False resolution every sibling
    # checkbox gate above already uses. The topic URL is resolved
    # separately below, once both checkboxes have cleared this gate,
    # because building the replacement dict needs the CURRENT on-disk
    # group (save_device_config() REPLACES the whole notifications
    # sub-dict rather than merging it per key, unlike every scalar field
    # above) — see this function's own docstring paragraph on this field.
    if screens.GROUP_NOTIFICATIONS not in in_scope:
        notifications = None
    else:
        if submitted_notifications_battery is None:
            notifications_battery = False
        elif submitted_notifications_battery == NOTIFICATIONS_BATTERY_CHECKBOX_VALUE:
            notifications_battery = True
        else:
            _note_error(errors, "notifications_battery", ERROR_UNEXPECTED_SWITCH_VALUE)
            return FLASH_SAVE_FAILED
        if submitted_notifications_silent is None:
            notifications_silent = False
        elif submitted_notifications_silent == NOTIFICATIONS_SILENT_CHECKBOX_VALUE:
            notifications_silent = True
        else:
            _note_error(errors, "notifications_silent", ERROR_UNEXPECTED_SWITCH_VALUE)
            return FLASH_SAVE_FAILED
        # D-26: an empty (stripped) submission means "leave the stored
        # URL unchanged", never "clear it" — this codebase's established
        # empty-numeric-input convention (wake_interval_s's own
        # precedent above), read fresh from disk rather than trusted
        # from ctx, so this resolution is correct even when a caller's
        # own ctx dict carries a stale or absent "device_config" key.
        current_notifications_on_disk = device_config.load_device_config(
            state_dir)["notifications"]
        stripped_notifications_url = (submitted_notifications_topic_url or "").strip()
        notifications_topic_url = (
            stripped_notifications_url if stripped_notifications_url
            else current_notifications_on_disk.get("topic_url"))
        notifications = {
            "topic_url": notifications_topic_url,
            "battery_low": notifications_battery,
            "frame_silent": notifications_silent,
            # D-28: written silently from the session's resolved
            # language at save time — no language-picking control for
            # this group exists anywhere on the page (the poll loop has
            # no browser to ask, 20-RESEARCH.md Pitfall 6).
            "lang": ctx.get("lang") or device_config.DEFAULT_NOTIFICATIONS["lang"],
        }

    try:
        device_config.save_device_config(
            state_dir, theme=submitted_theme, theme_arriving=theme_arriving,
            tracked_runway=submitted_runway,
            led_enabled=led_enabled, quiet_hours_enabled=quiet_hours_enabled,
            quiet_hours_start=submitted_qh_start, quiet_hours_end=submitted_qh_end,
            wake_interval_s=wake_interval_s, display_enabled=display_enabled,
            calendar_theme_id=submitted_calendar_theme_id,
            screen_id=submitted_screen_id, notifications=notifications)
    except (ValueError, OSError):
        return FLASH_SAVE_FAILED

    # Phase 17 plan 03 (D-01/D-02/D-04/D-05/D-07): the secret write is
    # layered AFTER the device-config write above, and only on the two
    # outcomes that actually touch the calendar URL. `carry_forward`
    # calls calendar_rules.save_calendar_url() not at all — every
    # successful call to it erases the fetched calendar registry, so
    # calling it on a save that never touched the calendar field would
    # silently wipe the calendar's flights on every unrelated settings
    # change (T-17-PRIV). This ordering leaves a narrow window in which
    # the device config has been written but this call then fails; the
    # operator sees the generic failure flash and can retry, which is
    # the cheaper trade against perturbing the ordering of every save in
    # this handler to close a window that only opens when the state
    # directory is already failing.
    if calendar_signal == CALENDAR_URL_SIGNAL_CLEAR:
        if not calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return FLASH_SAVE_FAILED
    elif calendar_signal == CALENDAR_URL_SIGNAL_SET:
        if not calendar_rules.save_calendar_url(
                state_dir, submitted_calendar_url.strip()):
            return FLASH_SAVE_FAILED
    # calendar_signal == CALENDAR_URL_SIGNAL_CARRY_FORWARD: no call at
    # all (see docstring/comment above).

    return FLASH_SAVED
