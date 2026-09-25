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
# 22-05-PLAN.md Task 2 (D-04) added `from companion import frame_state`
# here: the Frame strip (companion/layout.py, 22-04-PLAN.md) and this
# module's own Quiet hours caption both read frame_state.
# delay_sentence_template() from the SAME wake.next_wake_status()
# triple, so the two could never disagree.
#
# 29-05-PLAN.md Task 2 (CFG-79), 2026-09-21: that import is DELETED —
# this module no longer computes a delay sentence of its own at all
# (see quiet_hours_group()'s own docstring for the full account); the
# Frame strip is now the ONLY reader of frame_state in this codebase's
# render path, and it lives in companion/layout.py, not here. Confirmed
# unused by grep before deleting: every remaining "frame_state" text in
# this module is prose, in a comment or docstring, not executable code.
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
# 29-05-PLAN.md Task 1 (CFG-79): shortened from 14 words to 7 — the
# "nothing here needs changing day to day" reassurance is a REASON
# clause (why the page's contents don't matter day to day), not a fact
# about what the page contains, and CFG-79's floor cuts reason clauses
# on sight. What survives is the one thing this sentence is actually
# for: naming the page's SUBJECT.
DEVICE_PAGE_PURPOSE = "Hardware, data and diagnostics for the frame."
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
# 29-05-PLAN.md Task 1 (CFG-79): shortened from 14 words to 6 — "instead
# of waiting for the next wake" is the apply-timing idea in disguise
# (it is restating what NOT triggering this control means), and CFG-79
# reserves that idea for the Frame strip alone. What survives names
# what the control DOES, distinct on purpose from POLL_SECTION_CAPTION
# below (which names the control itself, not its effect) — an intro
# and its one card's caption saying the same thing at two levels is
# 27-06's own CFG-65 finding, and this cut keeps them apart rather than
# merging them.
DEVICE_POLL_INTRO = "— fetch a new picture right now."
# 19-12-PLAN.md Task 2 (D-23): the conditional screen-type <select> — an
# element id (not a class) because its own <label> targets it via `for`.
SCREEN_SELECTOR_ID = "screen-id-selector"
SCREEN_SELECTOR_LABEL_TEXT = "Screen type"

# 30-04-PLAN.md Task 1 (CFG-85): "Aspect" — the one merged card that
# replaces `_frame_colours_card_html()`'s four-row `colour_usage`
# radiogroup + four usage panels with a native `<details name=
# "aspect-rows">` accordion (30-02/30-03-PLAN.md laid the palette
# renderers and the coverage-gap ledgers this task now spends). The
# `colour_usage` FIELD is retired outright — no radiogroup selects
# which row is SHOWING any more, because a grouped `<details>` set is
# mutually exclusive by construction, natively, with zero script. The
# `COLOUR_USAGE_*` values below survive as `data-usage` attribute
# values on the four rows (and as this card's own internal branch
# keys) — a purely presentational label, never submitted to
# handle_post() — entirely distinct from the three underlying SAVED
# field names (theme/theme_arriving/calendar_theme_id) each row's own
# palette still posts through via `form="settings-form"`.
ASPECT_HEADING = "Aspect"
ASPECT_HEADING_ID = "aspect-heading"
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
# 30-04-PLAN.md Task 1 (CFG-85): the name predates the Aspect rename
# (it named the retired "Frame colours" card's own four rows) and is
# kept deliberately — 30-UI-SPEC.md's Copywriting Contract cites all
# four of its values by this exact constant name, and renaming it
# would churn the French catalogue and every consumer for zero
# behaviour change.
FRAME_COLOURS_ROW_LABELS = {
    COLOUR_USAGE_DEPARTURES: "Departures",
    COLOUR_USAGE_ARRIVALS: "Arrivals",
    COLOUR_USAGE_CALENDAR: "Calendar flights",
    COLOUR_USAGE_RULES: "Per-flight rules",
}
# 30-02-PLAN.md Task 2 (CFG-85): the grouped-<details> `name` attribute
# value every one of the four Aspect accordion rows shares (native
# grouped-disclosure, one-open-at-a-time with zero script) — ONE
# constant so the four rows and every check that addresses them agree,
# rather than four literals that can drift apart.
ASPECT_ROWS_GROUP_NAME = "aspect-rows"
# 30-02-PLAN.md Task 2 (CFG-85): the closed-row `<summary>` format —
# "{row label} — {theme label}", e.g. "Departures — Red" — joining two
# ALREADY-translated strings with an em dash. The em dash is
# punctuation, not copy, so this template itself carries no French
# entry (test_i18n.py's own scan excludes it: stripping its two `%s`
# format specs leaves no letters). Defined once, per 30-UI-SPEC.md's own
# copy table note that this format "must live once rather than four
# times".
ASPECT_ROW_SUMMARY_TEMPLATE = "%s — %s"
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

# 30-04-PLAN.md Task 1 (CFG-85): the carousel this comment block used
# to introduce (D5's scroll-snap strip, its two pagers, its dots row
# and its "See all themes" disclosure) is RETIRED OUTRIGHT — the
# accordion's own wrapping palette grid (30-UI-SPEC.md: "no strip, no
# overflow-x, no scrollbar, no pager buttons, no dot row, no <details>
# disclosure wrapping it") replaces it, and nothing on the page reads
# THEME_CAROUSEL_STRIP_ID*/_WRAPPER_ATTR/_PAGER_*/_SUMMARY/
# _DISCLOSURE_BODY_TEMPLATE/_PREV_LABEL/_NEXT_LABEL or
# COLOUR_USAGE_PANEL_ATTR/_TARGET_ATTR any more — grepped whole-repo
# for a surviving consumer before deletion, per ROADMAP's own carried
# discipline for this phase. `_theme_carousel_html()`/
# `_frame_colours_row_html()`/`_frame_colours_usage_panel_html()` (the
# builders that read these) are retired in the same commit, below.
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
# replaced by a second paragraph. What survived THAT cut was the three
# facts that were always true independent of any drawing — which
# runway, and that the change applies on the next scheduled poll, not
# immediately — which is also why this caption used to read
# consistently with LED_SECTION_CAPTION below it, which ended on that
# identical clause.
#
# 29-05-PLAN.md Task 1 (CFG-79), 2026-09-21: that consistency is now
# consistency in the WRONG direction. "Applies on the next scheduled
# poll" is CFG-79's own named example of a mechanism/apply-timing
# clause repeated under a card when the Frame strip already carries it
# once per page (companion/layout.py's frame_strip_html(), the delay
# caption both the Screen and Quiet-hours switch cells share) — the
# developer's own quoted tour example ("il y a trop de texte descriptif
# qui servent à rien") is this exact caption. BOTH captions lose the
# clause here, not just this one: the "consistency" quick task 260921-
# n2n recorded between them survives as "both keep exactly one fact,
# their own control's subject", not as a shared trailing sentence. What
# remains of this caption is one fact: which runway. 14 words -> 6.
RUNWAY_SECTION_CAPTION = "Which Orly runway the device watches."
# 29-05-PLAN.md Task 1 (CFG-79): 20 words -> 8. Two clauses cut, both
# for the same reason as RUNWAY_SECTION_CAPTION above: "not visible
# from the wall side" is a reason clause (why the placement doesn't
# matter), not a fact about the control, and the closing "Applies on
# the next scheduled poll" is the apply-timing clause the Frame strip
# already carries once per page. What remains names the one fact this
# caption is actually for: when the LED lights up.
LED_SECTION_CAPTION = "Lit only during the device's brief wake window."

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
# 29-05-PLAN.md Task 1 (CFG-79): shortened from 14 words to 5 —
# "instead of waiting for the next scheduled one" is the apply-timing
# idea again, this time framed as what NOT triggering this control
# means, and CFG-79 cuts it for the identical reason DEVICE_POLL_INTRO
# above does. What survives names the CONTROL (a poll cycle), distinct
# from DEVICE_POLL_INTRO's own surviving text, which names the
# control's EFFECT (a new picture) — the supersection intro and this
# one card's caption still say two different things at two levels,
# matching 27-06's own CFG-65 finding that a merge here would be wrong.
POLL_SECTION_CAPTION = "Trigger an immediate poll cycle."
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
# function's own caption_html construction below, unchanged at the
# time). The cut was scoped to THIS explanatory sentence alone: "— the
# Frame strip's Quiet hours switch is what turns it on and off" (the
# mechanism clause) is dropped; "Pauses the frame's wake, poll and
# display cycle during the schedule below" (what the schedule DOES) is
# kept, and the appended delay sentence — computed state, not
# explanation — was untouched by that edit entirely.
#
# 29-05-PLAN.md Task 2 (CFG-79), 2026-09-21: the SECOND sentence this
# comment's own previous paragraph left untouched is now gone
# completely — not shortened, removed. The Frame strip renders the
# identical computed sentence in its own Quiet-hours switch cell on
# both Home and Display (companion/layout.py's frame_strip_html()), and
# 27-08-PLAN.md's CFG-69 already made that cell LINK to this card's own
# heading — so the page's one home for "applies at the next wake" was
# already the strip, and appending it here too was a second, redundant
# copy of the same fact, which is precisely what CFG-79 forbids ("said
# in exactly one place per page"). This caption is now, and stays, the
# ONE sentence below — see quiet_hours_group()'s own docstring for the
# full account of what else this removal took with it (the
# `delay_sentence` parameter, and the two scanner-visibility copies
# immediately below).
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

# 22-05-PLAN.md Task 2 (D-04) added scanner-visibility copies of two of
# companion/frame_state.py's three delay-sentence constants here — byte-
# identical to frame_state.DELAY_DUE/DELAY_HELD, matching companion/
# layout.py's own 22-04-PLAN.md Task 1 precedent exactly (that module's
# own docstring/summary calls this pattern out by name). They existed
# because the D-05 AST i18n completeness scan (companion/test_i18n.py)
# can trace a same-file top-level scalar used directly as an i18n.t()
# argument, but not an imported module's attribute access read through
# a local variable — render()'s own `quiet_hours_delay_template` was
# exactly such a local variable.
#
# 29-05-PLAN.md Task 2 (CFG-79), 2026-09-21: DELETED. Once
# quiet_hours_group() stopped rendering a delay sentence at all (see
# QUIET_HOURS_SECTION_CAPTION's own comment above), these two copies had
# no reader anywhere in this module — `render()`'s own computation that
# used to produce their translated text is deleted at the same call
# site, below. Deleting them does not orphan either CATALOG key:
# companion/layout.py's OWN `_FRAME_DELAY_DUE_TEXT`/`_FRAME_DELAY_HELD_
# TEXT` aliases (byte-identical text, 22-04-PLAN.md) already make both
# keys scanner-visible from that module's own `i18n.t()` calls in
# frame_strip_html() — the harness is the arbiter here, not judgement,
# and companion/test_i18n.py stayed 24/24 after this deletion.

# 19-10-PLAN.md (D-14/S-04): three one-tap presets, client-side only - no
# server change (see quiet_hours_group()'s docstring). The Night preset's
# start/end are sourced from server.device_config's own shipped defaults
# rather than retyped literals, so the preset and the default can never
# drift apart. Ranges use a real U+2013 en dash, matching this module's
# real-Unicode punctuation convention (see its em dashes elsewhere) —
# still true of the START/END constants below even though the hours are
# no longer PRINTED anywhere (29-04-PLAN.md Task 1, CFG-80): a preset
# still WRITES this exact pair into the two time fields, and that is
# unchanged.
QUIET_HOURS_PRESET_NIGHT_START = device_config.DEFAULT_QUIET_HOURS_START
QUIET_HOURS_PRESET_NIGHT_END = device_config.DEFAULT_QUIET_HOURS_END
# 29-04-PLAN.md Task 1 (CFG-80): SHORTENED to bare labels — "Night
# (23:00–07:00)" is gone, replaced by "Night" alone. The hours these
# buttons set are already spoken, once, by quiet_dial_readout_html()'s
# own caption directly above this row ("23:00 → 07:00 · 8h"); repeating
# them on a button was the developer's own "pas très joli" complaint
# (29-CONTEXT.md) — four surfaces spelling one value. The 20-07-PLAN.md
# %s-templated form this superseded is gone along with it: there is no
# longer a device-specific time baked into a button label at all, so the
# "translate the template before substituting" reasoning that form
# needed no longer applies to this pair.
#
# QUIET_HOURS_PRESET_NIGHT_START/_END and _WORKDAY_START/_END below are
# UNCHANGED by this cut — they still feed the buttons' own
# data-preset-start/data-preset-end attributes and still come from
# server.device_config's own shipped defaults, so nothing about what a
# preset WRITES changes, only what its own button prints.
QUIET_HOURS_PRESET_NIGHT_LABEL = "Night"
QUIET_HOURS_PRESET_WORKDAY_START = "08:00"
QUIET_HOURS_PRESET_WORKDAY_END = "18:00"
QUIET_HOURS_PRESET_WORKDAY_LABEL = "Day"
# "Always on": this preset UNCHECKS the enable checkbox and leaves
# both times untouched - "off" means the curfew is disabled while the
# configured window stays intact, the pre-configure-before-enabling
# behaviour quiet_hours_group()'s own docstring already locks. Expressed
# via a distinct data-preset-enabled="0" attribute rather than
# overloading the time attributes with a sentinel value. The trailing
# "(off)" clause is dropped by the same 29-04-PLAN.md cut as the other
# two labels — the preset's own data-preset-enabled="0" attribute is
# still what does the work; the label only ever named it a second time.
QUIET_HOURS_PRESET_ALWAYS_ON_LABEL = "Always on"
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
#
# 29-05-PLAN.md Task 1 (CFG-79), 2026-09-21: cut again, 19 words -> 6,
# in the audit's own shape ("Plus court : données plus fraîches,
# batterie plus sollicitée." — 2026-09-17 audit, P1). This is NOT a
# fact lost: the "longer means more battery life" half this sentence
# used to spell out is exactly what THE TWO GAUGES below (CFG-49,
# 25-05-PLAN.md Task 1) already state, in both directions, with real
# measured numbers — WAKE_FRESHNESS_TEXT's own "at most # min later"
# and battery.battery_life_estimate()'s own day count. A caption naming
# the trade-off in prose right above two gauges that COMPUTE it is the
# redundant half; the gauges are the reference material, so nothing
# here needed moving into a disclosure.
WAKE_INTERVAL_SECTION_CAPTION = "Shorter: fresher data, more battery drain."
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
# still has NO PER-WAKE ENERGY COST. DEVICE-05 ran (hardware/
# BATTERY-RUN.md) and is the source of companion/battery.py's
# BATTERY_DISCHARGE_CURVE (SEED-006, quick 260923-gaf), but it measured
# a single wake cadence and left the per-wake versus standing-leakage
# split unresolved. A number invented from an assumed cost, printed next
# to a control a person will act on, is exactly the dishonest state
# Phase 22 spent a whole phase removing. So the figure here comes out of
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
# 29-05-PLAN.md Task 1 (CFG-79): shortened from 15 words to 9. Nothing
# lost: the two triggers this sentence used to spell out by name
# ("the battery runs low", "the frame stops checking in") are the exact
# two checkboxes rendered immediately below (NOTIFICATIONS_BATTERY_
# LABEL = "Battery low", NOTIFICATIONS_SILENT_LABEL = "Frame silent") —
# the caption naming both again in prose was a third surface for the
# same two facts. What survives says there ARE two kinds of alert,
# generically, and the checkboxes name them specifically.
NOTIFICATIONS_SECTION_CAPTION = "Get a push alert about battery or connection issues."
NOTIFICATIONS_SECTION_CAPTION_ID = "notifications-caption"
# D-26 amended (20-CONTEXT.md's Resolutions): write-only, like the
# calendar feed URL — never rendered back, not partially masked. The
# status row reports only whether a URL is stored (T-20-12).
NOTIFICATIONS_STATUS_CONFIGURED_VERDICT = "Configured"
NOTIFICATIONS_STATUS_NOT_CONFIGURED_VERDICT = "Not configured"
NOTIFICATIONS_URL_FIELD_LABEL = "Push topic URL"
# 29-05-PLAN.md Task 1 (CFG-79): 26 words -> 9. This hint carried real
# reference material CFG-79's own rule says must be MOVED, not deleted:
# where the value is stored, that it is never shown back, and that
# pasting a new one replaces the old. That sentence survives verbatim
# in meaning as NOTIFICATIONS_URL_HOW_IT_WORKS_BODY below, reached
# through the same inline "How it works" <details> pattern
# CALENDAR_HOW_IT_WORKS_SUMMARY/_BODY already use (config_page.py's
# calendar_group()) — the identical summary label, reused rather than
# a second one invented for an identical disclosure shape. What stays
# visible here is the one thing a reader needs BEFORE they act: what
# to paste.
NOTIFICATIONS_URL_HINT = "Paste your ntfy.sh topic URL (or a self-hosted one)."
NOTIFICATIONS_URL_HINT_ID = "notifications-url-hint"
# 29-05-PLAN.md Task 1 (CFG-79): the storage/replacement sentence moved
# out of NOTIFICATIONS_URL_HINT above, into the "How it works"
# disclosure body rendered by notifications_group() below — same
# wording, new home, nothing lost.
NOTIFICATIONS_URL_HOW_IT_WORKS_BODY = (
    "Stored on the server and never shown back here — pasting a new "
    "one replaces the old.")
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
#
# 30-06-PLAN.md Task 1 (CFG-85), 2026-09-22: CALENDAR_SECTION_HEADING,
# CALENDAR_HEADING_ID and CALENDAR_CAPTION are RETIRED here — the
# calendar's connection block no longer renders its own
# `<div class="page-section">` with its own `<h2>`/caption; it folds
# directly into the Calendar usage row inside the Aspect card
# (`_calendar_connection_html()`, below), which already has its own
# `<h2 class="text-heading" id="aspect-heading">Aspect</h2>` naming the
# whole card. Real call-site counts before this deletion (git grep,
# code files only): CALENDAR_SECTION_HEADING 8 total mentions / 2 real
# reads (both inside `calendar_group()`'s own now-deleted card_html
# string); CALENDAR_HEADING_ID 4 total / 1 real read (same string);
# CALENDAR_CAPTION 11 total / 1 real read (same string). Zero surviving
# consumers after this commit.
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

# 29-05-PLAN.md Task 3 (CFG-79), 2026-09-21: the editorial floor this
# plan and 29-06 together enforce is site-wide EXCEPT Display's Aspect
# section — ROADMAP.md's Phase 30 entry states in full that it rebuilds
# this card from scratch and owns its copy, including deleting "both
# intro sentences" itself (CFG-79's own rule applied to that card BY
# that phase, since this phase excludes it).
#
# 30-04-PLAN.md Task 1 (CFG-85), 2026-09-22, CORRECTS the "expected to
# become empty" prediction this comment used to make: 30-RESEARCH.md
# read this tuple directly (not from ROADMAP's prose) and found FOUR
# members, not two exemptions-per-caption as the retiring text implied.
# `FRAME_COLOURS_CAPTION` — the one caption this plan's own card
# rebuild deletes — is removed here, in the SAME commit that deletes
# the constant itself. `CALENDAR_CAPTION` is NOT touched by this plan:
# `calendar_group()` keeps rendering its own, separate card, unchanged,
# until 30-06-PLAN.md folds its body into the Calendar accordion row
# and deletes that caption too. `DISPLAY_LOOK_INTRO` (the "Look"
# supersection intro, a different card's concern entirely) and
# `CALENDAR_URL_HINT` (22 words, deliberately over the floor — 30-UI-
# SPEC.md itself says "do not shorten it") are NEVER touched by Phase
# 30 at all and remain permanent members of this tuple, not a step on
# the way to zero.
#
# The tuple lives HERE, in the page module, rather than in the test
# harness: the exemption is a property of the page's own copy, worth
# reviewing beside the strings it exempts rather than as a second,
# harness-side list that could silently drift from this one. A future
# plan naming a new exemption must argue it here, in this comment, not
# merely add a line to a test file.
#
# 30-06-PLAN.md Task 1 (CFG-85), 2026-09-22: `CALENDAR_CAPTION` is
# removed here, in the SAME commit that deletes the constant itself
# (the calendar's connection block no longer has its own caption once
# it folds into the Calendar usage row) — narrowing this tuple to its
# two PERMANENT members, `DISPLAY_LOOK_INTRO` and `CALENDAR_URL_HINT`.
# THIS TUPLE DOES NOT EMPTY THIS PHASE, and never will: those two are
# deliberate, standing carve-outs (a different card's own intro; a
# hint sentence 30-UI-SPEC.md explicitly says never to shorten), not a
# debt any later plan owes. Do not try to reach zero.
ASPECT_CAPTION_EXEMPTIONS = (
    DISPLAY_LOOK_INTRO,
    CALENDAR_URL_HINT,
)
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


def _palette_swatch_html(theme_id, extra_class=""):
    """30-02-PLAN.md Task 1 (CFG-85): the app's first CSS-drawn,
    non-photographic themed swatch — one outer `<span class=
    "palette-swatch">` filled with `_palette_hex(departing_index)`, plus
    an OPTIONAL child `<span class="palette-swatch__band">` carrying
    `_palette_hex(band_index)`. This function reads ONLY those two
    registry keys — `departing_index` and `band_index` — and NOTHING
    ELSE: never `arriving_index` (18/18 registered themes have
    `departing_index == arriving_index`, the already-recorded Phase 25
    finding that is this swatch's own reason to be ONE swatch, not the
    retired two-dot `.theme-chip__dot` pair), never `dithered`, never
    `band_dithered`, never `ink_index`, never `weight`.

    Reading only those two keys makes TWO corrections to the
    developer-approved sketch's own transcribed registry moot by
    construction, rather than by remembering them:
    1. `band_blue_light`/`band_green_light` carry a separate
       `band_dithered` key, not `dithered: True` (the sketch's JS table
       marked both `dithered: true`) — irrelevant here, since this
       function never reads either dithered key.
    2. The sketch's `paintSwatch()` applied `opacity: 0.72` to dithered
       themes; 30-UI-SPEC.md's Swatch Rendering Contract states the
       opposite ("renders their flat ink colour... no dither texture at
       44-64px") — this function never emits an `opacity` style at all.

    The band child is emitted IFF `"band_index" in theme` AND
    `theme["band_index"] != theme["departing_index"]` — both halves
    load-bearing: the second is what keeps `band_blue_field`/
    `band_red_field` solid rather than faking a two-tone band the real
    panel paints as one colour (those two themes have
    `departing_index == band_index` in the live registry).

    The band child's geometry (`top: 33%; height: 34%`) is a stylesheet
    rule (plan 30-07), never inline — only the two colours are
    server-computed here.
    """
    theme = device_config.THEMES[theme_id]
    hex_fill = _palette_hex(theme["departing_index"])
    css_class = "palette-swatch"
    if extra_class:
        css_class += " " + extra_class
    band_html = ""
    if "band_index" in theme and theme["band_index"] != theme["departing_index"]:
        band_html = '<span class="palette-swatch__band" style="background:%s"></span>' % (
            escape_html(_palette_hex(theme["band_index"])))
    return '<span class="%s" aria-hidden="true" style="background:%s">%s</span>' % (
        escape_html(css_class), escape_html(hex_fill), band_html)


def _palette_chip_html(field_name, theme_id, selected, radio_form_id=None):
    """30-02-PLAN.md Task 2 (CFG-85): one palette entry — a `<label
    class="palette-chip">` wrapping a visually-hidden native radio, this
    theme's own `_palette_swatch_html()` (no `<img>`, no photo, no
    `theme-preview` route call per chip), and a caption. Mirrors
    `_theme_chip_grid_html()`'s hidden-radio-inside-`<label>` idiom (same
    four field names, same `form=` cross-submit seam) but drops the
    `<img>`, the two `.theme-chip__dot` spans and the swatch legend
    entirely — there is now ONE swatch per theme (`departing_index ==
    arriving_index` for all 18 registered themes), so there is nothing
    left for a two-dot legend to name.

    THE ATTRIBUTE THAT MUST NOT BE DROPPED: `data-preview-src` on the
    `<label>` itself — `theme-preview.js` (D-24) resolves the live
    preview source off the CHANGED radio input's `parentNode`. Dropping
    it silently stops the live preview from following selection.

    Deliberately does NOT emit the `--selected` server class or
    `CURRENT_BADGE_ATTR` "Current" badge `_theme_chip_grid_html()`
    carries — those belong to the big photo chip's quiet saved-state
    marker; this chip's selected state is the live `:has(input:checked)`
    treatment (plan 30-07), which is what the accent-reservation list's
    re-keyed entry already covers. A third selected-state signal on one
    control would be redundant.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    escaped_id = escape_html(theme_id)
    label = i18n.t(device_config.theme_label(theme_id))
    check_html = ""
    if selected:
        check_html = (
            '<span class="palette-chip__check">%s'
            '<span class="visually-hidden">%s</span></span>'
        ) % (layout.icon_html("icon-check"), escape_html(i18n.t("Selected")))
    return (
        '<label class="palette-chip" data-preview-src="%s%s.png?live=1">'
        '<input type="radio" name="%s" value="%s" class="visually-hidden"%s%s>'
        "%s"
        '<span class="palette-chip__name">%s</span>'
        "%s"
        "</label>"
    ) % (
        THEME_PREVIEW_ROUTE_PREFIX, escaped_id,
        escape_html(field_name), escaped_id, form_attr_html,
        " checked" if selected else "",
        _palette_swatch_html(theme_id, extra_class="palette-chip__swatch"),
        escape_html(label),
        check_html,
    )


def _palette_grid_html(
        field_name, selected_theme_id, radio_form_id=None, leading_html="",
        labelled_by=""):
    """30-02-PLAN.md Task 2 (CFG-85): the wrapping 18-entry palette grid
    — `<div class="palette" role="radiogroup">`, looping
    `device_config.THEME_IDS` in registry order (never a literal list,
    never a re-sort) and interpolating `leading_html` BEFORE the 18
    chips, so a caller can prepend `_same_as_departures_chip_html()`'s
    output unchanged.

    No `id` attribute: this function has three call sites on one page
    (departures/arrivals/calendar), and an `id` emitted inside a
    multi-call renderer is the exact trap `_theme_carousel_html()`'s own
    docstring records (CFG-68) — a second call would either collide or
    silently go un-controlled by anything.
    """
    labelled_by_html = ' aria-labelledby="%s"' % escape_html(labelled_by) if labelled_by else ""
    chips = [
        _palette_chip_html(
            field_name, theme_id, theme_id == selected_theme_id,
            radio_form_id=radio_form_id)
        for theme_id in device_config.THEME_IDS
    ]
    return '<div class="palette" role="radiogroup"%s>%s%s</div>' % (
        labelled_by_html, leading_html, "".join(chips))


def _usage_row_summary_html(usage, theme_id, meta_text=None):
    """30-02-PLAN.md Task 2 (CFG-85): one Aspect accordion row's
    `<summary>` — the row's swatch, then a `<span class="usage-row__
    name">` carrying the translated row label, wrapping a NESTED `<span
    class="usage-row__meta">` — 30-UI-SPEC.md's Typography table's own
    "trailing detail" tier (14px, muted) — so the two segments can carry
    different weight/size while the row still reads, visually and to
    assistive tech, as one continuous phrase: "{row label} — {meta}".

    That em-dash join is computed from `ASPECT_ROW_SUMMARY_TEMPLATE`
    ("%s — %s") EXACTLY ONCE per call — never a second, hand-typed em
    dash — and then sliced back into its own "— {meta}" tail for the
    nested meta span, so the dash itself has exactly one source even
    though it renders inside a different element than the row label.

    `meta_text`, when omitted, is derived from
    `i18n.t(device_config.theme_label(theme_id))` — the row's own
    currently-selected/saved theme name. The Rules row passes its own
    `meta_text` explicitly (the translated rule count / empty-state
    string) and its own `theme_id=None` — it has no single theme of its
    own to swatch, so no swatch element renders at all for that row.
    """
    if meta_text is None:
        meta_text = i18n.t(device_config.theme_label(theme_id))
    row_label = i18n.t(FRAME_COLOURS_ROW_LABELS[usage])
    escaped_row_label = escape_html(row_label)
    escaped_meta = escape_html(meta_text)
    joined = ASPECT_ROW_SUMMARY_TEMPLATE % (escaped_row_label, escaped_meta)
    meta_suffix_html = joined[len(escaped_row_label):]
    swatch_html = (
        _palette_swatch_html(theme_id, extra_class="usage-row__swatch")
        if theme_id is not None else ""
    )
    return (
        "<summary>%s"
        '<span class="usage-row__name">%s'
        '<span class="usage-row__meta">%s</span>'
        "</span>"
        "</summary>"
    ) % (swatch_html, escaped_row_label, meta_suffix_html)


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


# 30-04-PLAN.md Task 1 (CFG-85): `_theme_carousel_html(grid_html,
# strip_id)` is RETIRED OUTRIGHT. It rendered D5's scroll-snap strip
# (a presentation wrapped around `_theme_chip_grid_html()`'s output),
# its dots row and its "See all themes" full-grid disclosure with two
# gated pagers — the whole mechanism 30-UI-SPEC.md's Structural
# Contract names as gone: "no strip, no overflow-x, no scrollbar, no
# pager buttons, no dot row, no <details> disclosure wrapping it".
# `_aspect_card_html()` below replaces every one of its three call
# sites (departures/arrivals/calendar) with `_palette_grid_html()`
# (30-02-PLAN.md), the wrapping, always-visible 18-entry grid that
# needs none of this. Pre-delete consumer grep (repo-wide, before this
# commit): 4 hits, all inside `_frame_colours_card_html()` itself
# (also retired below) — zero surviving consumers.
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
    Arrivals'/Calendar's own rows prepend to their palette grid via
    `_palette_grid_html()`'s `leading_html` seam (30-02-PLAN.md) —
    submits the EMPTY STRING for `field_name` (R-07's clear signal),
    never a real theme id.

    30-04-PLAN.md Task 1 (CFG-85), RESTYLED per 30-UI-SPEC.md's
    Structural Contract and the plan's own `<locked_markup_contract>`:
    class `leading-option` (was `theme-chip theme-chip--placeholder`),
    inner name span `leading-option__name` (was `theme-chip__name`
    inside `theme-chip__body`). The RADIO ITSELF — its `name`, its
    empty-string `value`, its `form=` attribute, its `checked` logic —
    is BYTE-IDENTICAL to before this restyle: that is the mechanism the
    no-JS control contract depends on, and 30-UI-SPEC.md explicitly
    forbids regressing it to the sketch's script-dependent `<button
    aria-pressed>`. The `CURRENT_BADGE_ATTR` "Current" badge emission is
    DROPPED (also per the locked contract) — the live `:has(input:
    checked)` treatment plan 30-07 adds to `.leading-option` is the one
    selected-state signal this control needs; a second, server-rendered
    one would be two sources of truth for one state.
    """
    form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
    return (
        '<label class="leading-option">'
        '<input type="radio" name="%s" value="" class="visually-hidden"%s%s>'
        '<span class="leading-option__name">%s</span>'
        '<span class="theme-chip__check">%s<span class="visually-hidden">%s</span></span>'
        "</label>"
    ) % (
        escape_html(field_name), form_attr_html, " checked" if checked else "",
        escape_html(i18n.t(SAME_AS_DEPARTURES_LABEL)),
        layout.icon_html("icon-check"), escape_html(i18n.t("Selected")),
    )


def _usage_row_html(usage, summary_html, body_html, is_open=False, extra_class=""):
    """30-04-PLAN.md Task 1 (CFG-85): one Aspect accordion row —
    `<details class="usage-row{ extra_class}" name="{ASPECT_ROWS_
    GROUP_NAME}" data-usage="{usage}"{ open}>{summary_html}{body_html}
    </details>`. The row is a container ONLY: `summary_html` (built by
    `_usage_row_summary_html()`, 30-02-PLAN.md) and `body_html` (a
    caller-built fragment — a palette grid plus its field error, or the
    rules row's own list/add-form/how-combine stack) arrive already
    built, so `_aspect_card_html()`'s own call site can show all four
    rows' shapes side by side rather than hiding them inside four
    branches here.

    Grouped `<details name="...">` is native, mutually-exclusive-by-
    construction accordion behaviour — zero script, zero server-side
    "which row is open" state beyond `is_open` itself, which is a
    property of ONE row (row 1/Departures ships `open`; the other three
    never do — see `<two_recorded_deviations>` item 2 in this plan for
    why "every row open" is met by a stronger property instead of the
    literal, browser-impossible reading).
    """
    row_class = "usage-row"
    if extra_class:
        row_class = row_class + " " + extra_class
    return (
        '<details class="%s" name="%s" data-usage="%s"%s>'
        "%s%s"
        "</details>"
    ) % (
        escape_html(row_class), escape_html(ASPECT_ROWS_GROUP_NAME), escape_html(usage),
        " open" if is_open else "",
        summary_html, body_html,
    )


def _aspect_card_html(
        ctx, current_theme_id, current_theme_arriving, current_calendar_theme_id,
        errors=None, submitted=None, state_dir=None,
        calendar_configured=False, calendar_drift=False, calendar_last_synced_at=None,
        calendar_last_attempt_at=None, now=None, calendar_entry_count=0):
    """30-04-PLAN.md Task 1 (CFG-85): "Aspect" — the ONE tile that
    replaces `_frame_colours_card_html()`'s four-row `colour_usage`
    radiogroup + four usage panels with a native `<details name=
    "aspect-rows">` accordion: one live preview above four grouped
    `_usage_row_html()` rows, in `COLOUR_USAGES`' own locked order
    (departures/arrivals/calendar/rules).

    30-06-PLAN.md Task 1 (CFG-85), 2026-09-22: THE CALENDAR ROW'S
    CONNECTION BLOCK IS NOW HERE. `calendar_group()` is retired outright
    — its body (status row, connect/replace/disconnect, "How it works")
    is built by `_calendar_connection_html()` (below) and threaded into
    the Calendar row directly beneath its palette and field error, per
    30-UI-SPEC.md's Structural Contract row 3 and §6 (no third "Gérer"
    wrapper — see that function's own docstring). The six new keyword
    parameters above (`calendar_configured`/`calendar_drift`/
    `calendar_last_synced_at`/`calendar_last_attempt_at`/`now`/
    `calendar_entry_count`) carry the exact names `calendar_group()`'s
    own call site in `render()` already used for its local variables —
    this is a merge, not a re-interface. `errors`/`submitted`/
    `state_dir` were already this function's own parameters (they
    repopulate the theme palettes on a rejected save) and now double as
    `_calendar_connection_html()`'s own arguments of the same names —
    the calendar URL field's own error/submitted-echo behaviour is
    unchanged by the merge.

    `errors`/`submitted` repopulate the three palette grids from a
    rejected save exactly like the retired `_frame_colours_card_html()`
    did; `departures_safe_id` (and its arrivals/calendar equivalents)
    keep an unregistered stored/submitted theme id from ever reaching
    `device_config.THEMES[...]`, carried verbatim from that function.
    """
    effective_theme_id = _submitted_or_current(submitted, "theme", current_theme_id)
    # 30-04-PLAN.md's own <locked_markup_contract>: the live preview is
    # keyed off `effective_theme_id` (the same repopulation value every
    # palette grid below uses), not the bare saved `current_theme_id` —
    # on an ordinary page load (`submitted is None`) the two are
    # identical, so this changes nothing there; only a rejected save's
    # re-render can tell the two apart.
    live_preview_html = _theme_live_preview_html(
        effective_theme_id, state_dir, extra_class="aspect-card__preview")

    # `departures_safe_id` is `_frame_colours_card_html()`'s own guard,
    # carried verbatim: an unregistered stored/submitted theme id never
    # reaches `device_config.THEMES[...]` — it resolves to
    # `DEFAULT_THEME_ID` before any swatch or label is computed. Also
    # the fallback swatch/label source for Arrivals/Calendar's own
    # "Same as departures" state, computed once here rather than at
    # each of those two call sites.
    departures_safe_id = (
        effective_theme_id if effective_theme_id in device_config.THEMES
        else device_config.DEFAULT_THEME_ID)
    departures_row = _usage_row_html(
        COLOUR_USAGE_DEPARTURES,
        _usage_row_summary_html(COLOUR_USAGE_DEPARTURES, departures_safe_id),
        _palette_grid_html(
            "theme", effective_theme_id, radio_form_id=SETTINGS_FORM_ID,
            labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "theme", "theme"),
        is_open=True)

    effective_arriving = _submitted_or_current(
        submitted, "theme_arriving", current_theme_arriving)
    arrivals_same_checked = not effective_arriving
    arrivals_leading = _same_as_departures_chip_html(
        "theme_arriving", arrivals_same_checked, radio_form_id=SETTINGS_FORM_ID)
    # Carried verbatim from `_frame_colours_card_html()`: "Same as
    # departures" falls back to the DEPARTURES theme's own swatch/label
    # for this row's summary, never a blank/neutral placeholder — a
    # scripts-blocked reader closing this row still sees which colour
    # it actually resolves to.
    if arrivals_same_checked:
        arrivals_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        arrivals_swatch_id = departures_safe_id
    else:
        arrivals_safe_id = (
            effective_arriving if effective_arriving in device_config.THEMES
            else departures_safe_id)
        arrivals_meta = i18n.t(device_config.theme_label(arrivals_safe_id))
        arrivals_swatch_id = arrivals_safe_id
    arrivals_row = _usage_row_html(
        COLOUR_USAGE_ARRIVALS,
        _usage_row_summary_html(
            COLOUR_USAGE_ARRIVALS, arrivals_swatch_id, meta_text=arrivals_meta),
        _palette_grid_html(
            "theme_arriving", effective_arriving, radio_form_id=SETTINGS_FORM_ID,
            leading_html=arrivals_leading, labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "theme_arriving", "theme-arriving"))

    effective_calendar = _submitted_or_current(
        submitted, "calendar_theme_id", current_calendar_theme_id)
    calendar_same_checked = not effective_calendar
    calendar_leading = _same_as_departures_chip_html(
        "calendar_theme_id", calendar_same_checked, radio_form_id=SETTINGS_FORM_ID)
    if calendar_same_checked:
        calendar_meta = i18n.t(SAME_AS_DEPARTURES_LABEL)
        calendar_swatch_id = departures_safe_id
    else:
        calendar_safe_id = (
            effective_calendar if effective_calendar in device_config.THEMES
            else departures_safe_id)
        calendar_meta = i18n.t(device_config.theme_label(calendar_safe_id))
        calendar_swatch_id = calendar_safe_id
    # 30-06-PLAN.md Task 1 (CFG-85): the calendar's connection block —
    # status row, masked-URL/Replace/Disconnect actions, "How it works"
    # — nests directly beneath this row's palette and field error, per
    # 30-UI-SPEC.md's Structural Contract row 3 ("directly beneath the
    # palette, not behind any further disclosure"). The disconnect
    # `<form>` returned alongside it is NOT part of the row body — it is
    # a sibling fragment of the whole `.aspect-card` div, concatenated
    # onto this function's own return value below (Pattern 2,
    # 30-PATTERNS.md; matches `calendar_group()`'s own retired shape).
    calendar_connection_row_html, calendar_disconnect_form_html = _calendar_connection_html(
        calendar_configured, calendar_drift, calendar_last_synced_at,
        calendar_last_attempt_at, now, calendar_entry_count,
        errors=errors, submitted=submitted, state_dir=state_dir)
    calendar_row = _usage_row_html(
        COLOUR_USAGE_CALENDAR,
        _usage_row_summary_html(
            COLOUR_USAGE_CALENDAR, calendar_swatch_id, meta_text=calendar_meta),
        _palette_grid_html(
            "calendar_theme_id", effective_calendar, radio_form_id=SETTINGS_FORM_ID,
            leading_html=calendar_leading, labelled_by=ASPECT_HEADING_ID)
        + _field_error_html(errors, "calendar_theme_id", "calendar-theme")
        + calendar_connection_row_html)

    # D-10: the rules row's own body — the existing rule list (or the
    # empty state), the existing add form (its own <form>, a legal
    # descendant of this <details> since neither is a <form>) and the
    # existing suggestion chips (add-affordances, useless beside a
    # list, so both now sit INSIDE a nested `<details class="rule-add">`
    # disclosure the sketch/30-UI-SPEC.md's row-4 paragraph calls for),
    # and the "How rules combine" disclosure OUTSIDE the rule-add
    # disclosure — it explains the LIST, not the form. Every inner
    # piece is unchanged from `_frame_colours_card_html()`; only the
    # wrapping shape (one more nested disclosure) is new.
    registry = ctx.get("colour_rules")
    if not isinstance(registry, dict):
        registry = {kind: {} for kind in colour_rules.RULE_KINDS}
    rule_rows = colour_rules.rule_rows(registry)
    # RULES_SECTION_CAPTION stays: it is not one of the two captions
    # CFG-85 deletes outright (the former FRAME_COLOURS_CAPTION,
    # 30-04-PLAN.md, and CALENDAR_CAPTION, 30-06-PLAN.md — see
    # ASPECT_CAPTION_EXEMPTIONS above) and already meets CFG-79's word
    # floor on its own.
    rules_caption_html = '<p class="text-label section-caption">%s</p>' % escape_html(
        i18n.t(RULES_SECTION_CAPTION))
    rules_how_combine_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_SUMMARY)),
        escape_html(i18n.t(RULES_HOW_RULES_COMBINE_BODY)),
    )
    if not rule_rows:
        rules_list_html = (
            '<div class="empty-state-plain"><p class="text-label">%s %s</p></div>'
        ) % (escape_html(i18n.t(RULES_EMPTY_HEADING)), escape_html(i18n.t(RULES_EMPTY_BODY)))
        rules_meta = i18n.t(FRAME_COLOURS_RULES_EMPTY_META)
    else:
        rules_list_html = _rule_list_html(rule_rows)
        rule_count = len(rule_rows)
        if rule_count == 1:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_SINGULAR)
        else:
            rules_meta = i18n.t(FRAME_COLOURS_RULES_COUNT_PLURAL_TEMPLATE) % rule_count
    # The rule-add disclosure's own <summary> reuses RULE_ADD_BUTTON_
    # TEXT rather than inventing a new summary string — 30-UI-SPEC.md's
    # copy table adds no such string, and new copy outside the approved
    # contract is not this plan's to invent. FLAGGED FOR THE DEVELOPER
    # in the SUMMARY: the disclosure and its own submit button then read
    # the same words ("Add rule" / "Ajouter la règle"), which is honest
    # but worth a look.
    rule_add_html = (
        '<details class="rule-add"><summary>%s</summary>%s%s</details>'
    ) % (
        escape_html(i18n.t(RULE_ADD_BUTTON_TEXT)),
        _rule_add_form_html(),
        _rule_suggestion_chips_html(ctx.get("state_dir")),
    )
    rules_row = _usage_row_html(
        COLOUR_USAGE_RULES,
        _usage_row_summary_html(COLOUR_USAGE_RULES, None, meta_text=rules_meta),
        rules_caption_html + rules_list_html + rule_add_html + rules_how_combine_html,
        extra_class="usage-row--secondary")

    rows_html = departures_row + arrivals_row + calendar_row + rules_row
    card_html = (
        '<div class="page-section aspect-card" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        "%s"
        "%s"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(ASPECT_HEADING)),
        escape_html(ASPECT_HEADING_ID), escape_html(i18n.t(ASPECT_HEADING)),
        live_preview_html,
        rows_html,
    )
    # 30-06-PLAN.md Task 1 (CFG-85), Pattern 2 (30-PATTERNS.md): the
    # disconnect `<form>` is a data-only sibling of the WHOLE
    # `.aspect-card` div, never nested inside it or inside the Calendar
    # `<details>` row — matching `calendar_group()`'s own retired
    # `card_html + disconnect_form_html` shape exactly.
    return card_html + calendar_disconnect_form_html


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
    """The Diagnostic LED switch's own empty `<form>`, a sibling of
    `<form id="{SETTINGS_FORM_ID}">` — `led_group()` renders inside the
    settings form, and a `<form>` can never nest inside another, so the
    button reaches this element across the DOM via
    `form="{QUICK_LED_FORM_ID}"`.

    `return_to` is `layout.DEVICE_ROUTE`; `companion/app.py` validates
    it by membership before using it as a redirect target — this
    function has no opinion on validity.

    The posted `state` is the opposite of the stored one, so a press
    with scripts blocked switches the LED rather than re-asserting its
    current state; `companion/static/quick-switch.js` keeps that field
    inverted after an optimistic flip.

    `data-quick-switch` is the handshake both `dirty-state.js` and
    `quick-switch.js` key on — not apparently-unused from this module's
    perspective.
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


# The quiet window always runs forward from start, through midnight if
# necessary: 23:00 to 07:00 is eight hours going forward and sixteen
# going the other way, and an `end - start` implementation would draw
# the wrong one. The shipped default window is exactly this case.
#
# The same shape regex feeds both the text and the drawn geometry, so a
# future loosening cannot apply to one and not the other.
_HHMM_RE = re.compile(r"^\d{2}:\d{2}$")

QUIET_WINDOW_MINUTES_PER_DAY = 24 * 60

# `start_fraction`/`sweep_fraction` are turns of the ring (0 at twelve
# o'clock, growing clockwise, matching companion/draw.py's circle
# helpers); `minutes` is the same span in whole minutes, the single
# source both a card's printed duration and its drawn arc read from.
QuietWindowSpan = collections.namedtuple(
    "QuietWindowSpan", "start_fraction sweep_fraction minutes")


def quiet_window_minute_of_day(value):
    """`value` ("HH:MM") as whole minutes since local midnight, or `None`
    when it is not a real time of day. Never raises.

    `None` is the "render nothing" signal: an unset or unparseable
    stored window must draw no arc rather than a plausible-looking one
    starting at midnight. Values reaching here are already
    server-validated by `handle_post()`; this is the second gate.

    The shape regex alone is not enough: `^\\d{2}:\\d{2}$` accepts
    "99:99", which would become minute 5,999 of a 1,440-minute day.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return None
    hours, minutes = (int(part) for part in str(value).split(":"))
    if hours > 23 or minutes > 59:
        return None
    return hours * 60 + minutes


def quiet_window_span(start_hm, end_hm):
    """The quiet window as a `QuietWindowSpan`, or `None` when either end
    does not parse. Never raises.

    Always forward from `start_hm`, through midnight if necessary (a
    modulo, not a subtraction): 23:00 to 07:00 is 480 minutes, and
    07:00 to 23:00 is its complement, 960.

    Equal start and end is a zero-length window, not a whole day —
    matching `server.device_config.seconds_until_quiet_hours_end()`'s
    own contract, since `(end - start) % 1440` is 0 for that input. A
    24-hour window is therefore unreachable through two HH:MM values:
    the only pair whose forward distance could be 1440 is the equal
    pair already claimed by zero, so the largest expressible window is
    1439 minutes, matching the dial's own `aria-valuemax`.

    An unparseable end renders nothing (`None`, never a zero span,
    which would draw a real empty window and claim one is configured).
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
    """The normalised 24h value rendered as a visible sibling beside a
    native `<input type="time">`.

    A native time control formats itself from the browser's own locale,
    so an en-US browser renders the stored "23:00" as "11:00 PM" —
    directly beside a preset button labelled "Night (23:00-07:00)". One
    value, two notations, with no way to tell they are the same without
    showing the stored 24h text.

    `aria-hidden`: the input's own value is already announced natively
    by the control itself; repeating it would announce the same value
    twice with no added information.

    Renders nothing for a falsy/unparseable value rather than
    fabricating one. The value is already server-validated by
    `handle_post()`; this only echoes it back.

    The span also carries `QUIET_NORMALISED_TIME_ATTR`, a stable hook
    `value-controls.js` reads to decide whether to hide it on a browser
    that is already unambiguous — server-visible, script-hidden, so a
    scripts-blocked or forced-12h browser always keeps the fallback.
    """
    if not value or not _HHMM_RE.match(str(value)):
        return ""
    return (
        ' <span class="text-label field-inline-value" %s aria-hidden="true">%s</span>'
    ) % (QUIET_NORMALISED_TIME_ATTR, escape_html(value))


# Class names as constants rather than literals at the emission site: a
# class that exists in Python and nowhere in style.css paints nothing,
# and a check scans emitted markup against the stylesheet for exactly
# that.
QUIET_DIAL_CLASS = "quiet-dial"
QUIET_DIAL_RING_CLASS = "quiet-dial__ring"
QUIET_DIAL_DAY_CLASS = "quiet-dial__day"
QUIET_DIAL_ARC_CLASS = "quiet-dial__arc"
QUIET_DIAL_HOUR_CLASS = "quiet-dial__hour"
QUIET_DIAL_READOUT_CLASS = "quiet-dial__readout"

QUIET_PRESET_ROW_CLASS = "quiet-preset-row"
QUIET_TIMES_ROW_CLASS = "quiet-times-row"

# The stable hook _normalised_time_html() marks its own span with, so
# value-controls.js can find and hide only it, never the wake-interval
# unit sibling that shares .field-inline-value but carries no hook.
QUIET_NORMALISED_TIME_ATTR = "data-normalised-time"

# CSS pixels, with an explicit intrinsic size so the <svg> never falls
# back to the format's own 300x150 default.
QUIET_DIAL_SIZE = 176
# 176 - 14 - 3 = 78 (SIZE // 2 - STROKE // 2 - CLEARANCE): chosen so the
# radius lands on a whole number, since a rounding tail would make every
# recomputed-from-markup check invent a tolerance to hide it.
QUIET_DIAL_STROKE = 14
# Clear space between the stroke's outer edge and the viewBox edge: a
# stroked arc extends half its stroke width past the nominal radius.
QUIET_DIAL_CLEARANCE = 3
QUIET_DIAL_RADIUS = QUIET_DIAL_SIZE // 2 - QUIET_DIAL_STROKE // 2 - QUIET_DIAL_CLEARANCE

# The three property names value-controls.js's generic pair seam reads
# or writes, decided here since every such name is a server decision.
QUIET_DIAL_PAIR_ATTR = "data-value-pair"
QUIET_DIAL_PAIR_PROPERTY_ATTR = "data-value-pair-property"

# A dict rather than three top-level string constants: a constant whose
# value begins with "--" trips test_i18n.py's untranslated-string scan
# (a leading "--" is not a valid identifier start, so the scanner's
# bare-identifier exclusion never reaches it); a dict value is scanned
# under a separate exclusion that does reach it.
QUIET_DIAL_PAIR_PROPERTIES = {
    "start": "--quiet-start-fraction",
    "end": "--quiet-end-fraction",
    "sweep": "--quiet-sweep-fraction",
}

# Four anchor hours, not twenty-four: the quarter turns are the only
# hours a reader resolves at a glance, and twenty-four labels on this
# ring is illegible at the contract's minimum width. 00 is marked
# because midnight is the case this control's arithmetic exists for.
#
# Each hour is paired with its own modifier class rather than templated
# from one "quiet-dial__hour--%d" constant: test_i18n.py strips a
# literal's format specs before checking whether it is a bare
# identifier, so the templated form would read as untranslated
# user-facing copy and fail that scan.
QUIET_DIAL_LABELLED_HOURS = (
    (0, "quiet-dial__hour--0"),
    (6, "quiet-dial__hour--6"),
    (12, "quiet-dial__hour--12"),
    (18, "quiet-dial__hour--18"),
)

# "23:00 → 07:00 · 8h". No letters of its own (the duration's unit
# comes from layout.duration_text(), which speaks both languages), so
# it needs no catalogue entry.
QUIET_DIAL_READOUT_TEMPLATE = "%s → %s · %s"

# A full turn in degrees, and the quarter turn that moves <circle>'s
# three-o'clock dash origin to twelve o'clock (the same correction
# draw.py's ring_gauge() applies, restated here since this drawing
# additionally rotates by the window's own start).
_QUIET_DIAL_FULL_TURN_DEG = 360.0
_QUIET_DIAL_TWELVE_OCLOCK_DEG = -90.0


def quiet_dial_svg(span):
    """The 24h ring as one `<svg>`: a full-circumference day, plus the
    quiet arc when `span` describes one. Never raises.

    Server-drawn: with scripts blocked the visitor still sees a correct
    picture of the saved window — only dragging the handle is script.

    `span` is `quiet_window_span()`'s return value, which already
    decided the wrap; this function does no window arithmetic of its
    own. No arc at all for `span is None` or a zero-length window — a
    zero-length dash would render as a dot under a round cap, reading
    as "a few minutes" rather than "no window".

    The dash route, not an arc path: an arc `<path>` whose sweep is the
    whole circle is degenerate in SVG and draws nothing. This control
    cannot reach a full turn (see `quiet_window_span()`), and the dash
    route needs no large-arc-flag reasoning or trigonometry.

    `fill="none"` is a presentation attribute on both shapes: a stroked
    circle with no fill takes the format's default black. `stroke-width`
    is a presentation attribute too, deliberately not a stylesheet
    declaration, since any CSS stroke-width would beat it and flatten
    the geometry the constants above derive.

    The `.js`-scoped override of this circle's `stroke-dasharray`/
    `transform` reads the same `QUIET_DIAL_RADIUS` via a custom
    property rather than a `pathLength="1"` attribute: a headless
    measurement showed `pathLength="1"` painting a second, spurious
    dash, because it reinterprets the saved-value dasharray on a second,
    rescaled coordinate system.
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

    The labels are HTML outside the `<svg>`, not `<text>` inside it,
    since a viewBox must contain the bounding box of any text drawn
    inside it, and keeping labels out of the canvas makes that defect
    unreachable by construction while keeping them at a constant CSS
    size instead of scaling with the box.

    `handles_html` is the `.js`-gated handle layer, empty when there is
    none, rendered last so document order is paint order.

    This `<div>` is the pair seam's shared ancestor: the two handles'
    fractions and their derived sweep publish here, under the property
    name `QUIET_DIAL_PAIR_ATTR` names, computed from the same `span`
    triple `quiet_dial_svg()` draws from so the CSS-driven and
    presentation-attribute geometry never disagree. `span is None`
    publishes no pair, since there is no window to publish one for.
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


# Everything below renders inside the `.js` gate; the ring, the
# readout, the three presets and both time inputs all survive with
# scripts blocked, and only the dragging is hidden without script.
QUIET_DIAL_HANDLE_LAYER_CLASS = "quiet-dial__handles"
QUIET_DIAL_HANDLE_CLASS = "quiet-dial__handle"
# The box value-controls.js measures the pointer angle against: the
# ring's own square, so the angle is measured about the ring's centre.
QUIET_DIAL_HANDLE_TRACK_CLASS = "quiet-dial__handle-track"

# The steering range, in minutes since local midnight. The maximum is
# 1439, not 1440: 1440 would make 00:00 and "24:00" the same instant
# with two values, and the End key would write a time no
# <input type="time"> accepts.
QUIET_DIAL_HANDLE_MIN = 0
QUIET_DIAL_HANDLE_MAX = QUIET_WINDOW_MINUTES_PER_DAY - 1

# The native <input type="range"> keyboard model: arrows move one step,
# Page keys move ten steps, Home/End go to the two ends. Ten steps of
# 15 minutes is 10.4% of the day, matching a native range control's
# Page-key proportion rather than a fixed value — a per-control page
# size would be a second keyboard model on the second settings page.
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
    the handle from — deliberately the same formula value-controls.js's
    `paint()` uses, `(value - min) / (max - min)`, rather than the
    `minute / 1440` the arc is drawn from. The server paints the handle
    once and the script repaints it on every step; using a formula that
    only agrees in theory would make it jump imperceptibly on the first
    arrow press and never quite line up with the arc again.
    """
    return minute / float(QUIET_DIAL_HANDLE_MAX)


def quiet_dial_handles_html(start_hm, end_hm):
    """The two drag handles, each in its own `.js`-gated wrapper.

    Each handle is a real `<button type="button">`, never a bare `<div>`
    — focusable and announced with no extra ARIA. `type="button"`
    because a bare `<button>` in a form defaults to submit, and a
    handle that posted the settings form on Enter would save on a
    keystroke meant to adjust a value.

    Driven from the two native inputs, never from state of its own: the
    server renders each handle from the same value the matching input
    holds, and value-controls.js re-reads that input on every steer —
    which is why the existing presets already move the handles with no
    code of their own.

    No handle at all for an end that does not parse, matching the
    omit-don't-fabricate rule `_normalised_time_html()`/`quiet_dial_svg()`
    follow.

    No minimum separation between the two ends: a zero-length window is
    a real, defined state, and refusing it here would make a state
    reachable by typing unreachable by dragging. Z-order is document
    order (the end handle is emitted second, so it sits on top with no
    `z-index`), so the end handle wins a pointer-down where they
    overlap; moving it separates the pair, after which both are
    independently grabbable again. `test_browser_ux.py` measures both
    handles at the width where the shared 44px hit targets stop
    overlapping (about 94 minutes on this ring).
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
            # Names which of quiet_dial_html()'s ancestor properties
            # this handle publishes its fraction under; value-controls.js
            # finds that ancestor via ancestorWith().
            QUIET_DIAL_PAIR_PROPERTY_ATTR, escape_html(pair_property),
            quiet_dial_handle_fraction(minute),
            escape_html(QUIET_DIAL_HANDLE_TRACK_CLASS), layout.VALUE_CONTROL_TRACK_ATTR,
            escape_html(QUIET_DIAL_HANDLE_CLASS), layout.VALUE_CONTROL_HANDLE_ATTR,
            QUIET_DIAL_HANDLE_MIN, QUIET_DIAL_HANDLE_MAX, minute,
            escape_html(value), escape_html(i18n.t(label)),
        ))
    return "".join(handles)


# layout.DURATION_ATTRS' four English wordings, in the same s/m/h/d
# order, zipped against that tuple below so an attribute name and its
# translated wording are always written together.
_QUIET_DIAL_DURATION_TEXTS = (
    layout.DURATION_SECONDS_TEXT, layout.DURATION_MINUTES_TEXT,
    layout.DURATION_HOURS_TEXT, layout.DURATION_DAYS_TEXT,
)


def quiet_dial_readout_html(start_hm, end_hm, span):
    """"23:00 → 07:00 · 8h" — the window in words, or "" when `span` is
    None.

    `aria-hidden="true"`: both time inputs already announce their own
    values natively, so repeating them here would say the same thing
    twice. Not a `role="status"`/`aria-live` region either: dragging a
    handle fires continuously, and a live region would re-announce the
    identical phrase on every step — the focused handle's own
    `aria-valuetext` is the debounced announcement path.

    The duration comes from `layout.duration_text()`, this app's one
    length-of-time ladder, rather than a second boundary set invented
    here — coarse by construction (a 90-minute window reads "1h"), which
    is acceptable since the two exact endpoints are printed beside it.

    Three children, not one text node, so the sentence can follow the
    pair the way the arc does. The two endpoint spans carry the
    `data-value-readout` seam (named by the field whose handle moves
    them) with `data-value-readout-format="clock"`, so
    `value-controls.js` substitutes zero-padded "HH:MM" through the same
    codec the native time input uses. The duration span carries all four
    `layout.DURATION_ATTRS`, each filled with `i18n.t()` of the matching
    wording, so the client substitutes a quantity into whichever bucket
    applies with no language logic of its own — its own visible,
    server-rendered content stays `layout.duration_text(span.minutes * 60)`.
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


def quiet_hours_group(current_start, current_end, errors=None, submitted=None):
    """The Quiet hours settings card: a sibling of
    `<form id="{SETTINGS_FORM_ID}">`, never a literal descendant. Both
    time inputs keep submitting with the shared Save via a
    `form="{SETTINGS_FORM_ID}"` attribute on each.

    Controls render in this order: heading, caption, dial, readout, the
    three presets, then Start and End (side by side in a two-column
    grid, next to the dial they mirror). Neither time input is ever
    `disabled`: they stay fully interactive whether or not Quiet hours
    is currently on, so a user can pre-configure a window either way —
    the Frame strip is the only control for turning it on or off, and
    `handle_post()` already treats an absent checkbox as unchanged.

    The three presets are a client-side-only affordance: `type="button"`
    elements carrying `data-preset-start`/`data-preset-end` attributes
    that `dirty-state.js` reads and writes into the two time fields,
    inert (never submitting) with no script.

    `errors`/`submitted` repopulate both time controls and their error
    messages on a rejected save. Both inputs also carry a `required`
    attribute as a client-side convenience only; the server-side HH:MM
    gate in `handle_post()` is the real control.

    The `<h2>` carries `id="{QUIET_HOURS_GROUP_HEADING_ID}"`, a
    fragment target for the Frame strip's own Quiet hours caption link.
    """
    # The group's single hint links to both time inputs (there is no
    # separate per-field hint for Start vs End).
    effective_start = _submitted_or_current(submitted, "quiet_hours_start", current_start)
    start_error_attrs = _field_error_attrs(
        errors, "quiet_hours_start", "quiet-hours-start", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    start_error_html = _field_error_html(errors, "quiet_hours_start", "quiet-hours-start")

    effective_end = _submitted_or_current(submitted, "quiet_hours_end", current_end)
    end_error_attrs = _field_error_attrs(
        errors, "quiet_hours_end", "quiet-hours-end", hint_id=QUIET_HOURS_SECTION_CAPTION_ID)
    end_error_html = _field_error_html(errors, "quiet_hours_end", "quiet-hours-end")

    # The preset row is a segmented control with no selected state:
    # these buttons are momentary actions that write into the time
    # fields, not a persistent choice.
    preset_row_html = (
        '<div class="%s">'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-start="%s" data-preset-end="%s">%s</button>'
        '<button type="button" %s data-preset-enabled="0">%s</button>'
        "</div>"
    ) % (
        QUIET_PRESET_ROW_CLASS,
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_NIGHT_START), escape_html(QUIET_HOURS_PRESET_NIGHT_END),
        escape_html(i18n.t(QUIET_HOURS_PRESET_NIGHT_LABEL)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(QUIET_HOURS_PRESET_WORKDAY_START), escape_html(QUIET_HOURS_PRESET_WORKDAY_END),
        escape_html(i18n.t(QUIET_HOURS_PRESET_WORKDAY_LABEL)),
        QUIET_HOURS_PRESET_ATTR,
        escape_html(i18n.t(QUIET_HOURS_PRESET_ALWAYS_ON_LABEL)),
    )

    # `<html lang>` already carries the site's language, but a native
    # time control formats itself from the browser's own locale, not
    # the document's — this attribute is the standards-level request;
    # `_normalised_time_html()` is the fallback that holds when a
    # browser ignores it.
    #
    # The ring reads before the controls that change it (a picture of
    # what is set, then how to change it), so it renders between the
    # caption and the presets rather than after the fields.
    #
    # Drawn from the same effective values the two inputs are populated
    # from, never from `current_start`/`current_end` directly, so on a
    # rejected save the arc shows what was submitted, not what is
    # stored.
    dial_span = quiet_window_span(effective_start, effective_end)
    dial_html = quiet_dial_html(
        dial_span, quiet_dial_handles_html(effective_start, effective_end))
    readout_html = quiet_dial_readout_html(effective_start, effective_end, dial_span)

    site_lang = prefs.current_lang()
    caption_html = i18n.t(QUIET_HOURS_SECTION_CAPTION)
    # Each field gets its own unclassed grid cell holding its label and
    # its own error paragraph together, so an error never displaces its
    # sibling column under the two-column grid.
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading" id="%s">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s%s"
        "%s"
        '<div class="%s">'
        '<div><label>%s <input type="time" name="quiet_hours_start" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>%s</div>'
        '<div><label>%s <input type="time" name="quiet_hours_end" value="%s" required'
        ' lang="%s" form="%s"%s>%s</label>%s</div>'
        "</div>"
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_GROUP_HEADING_ID),
        escape_html(i18n.t(QUIET_HOURS_SECTION_HEADING)),
        escape_html(QUIET_HOURS_SECTION_CAPTION_ID),
        escape_html(caption_html),
        dial_html, readout_html,
        preset_row_html,
        QUIET_TIMES_ROW_CLASS,
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
    no such value — in which case nothing renders at all, matching this
    file's omit-don't-fabricate rule.

    Honours the echo rule where it can: on a rejected save `submitted`
    carries the raw typed string, and the gauges describe that rather
    than the stored value, so the picture and the field never disagree
    on the screen where a mistake is being fixed. But a raw submission
    is also where out-of-range values live ("7", "99999", "abc"), so an
    echo outside the valid range still renders no gauge.

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
    """`interval_s` as a whole number of minutes, rounded up.

    Both sentences are claims about a bound: a 90-second cadence bounds
    the wait at a minute and a half, and `90 // 60` would print "at
    most 1 min", which is false. The ceiling prints "at most 2 min",
    true and merely loose. This control's own step is a whole minute;
    the ceiling matters for values already on disk from before it
    existed.
    """
    return -(-int(interval_s) // WAKE_GAUGE_SECONDS_PER_MINUTE)


def wake_freshness_text(interval_s):
    """"A plane reaches the frame at most 5 min after it passes." — the
    bound, or `""` when there is no interval to bound.

    "At most" is the whole sentence: the frame learns about a plane at
    its next wake, so a plane that passes one instant after a wake
    appears one whole interval later and never later — true for every
    interval, by construction, unlike a claim about typical behaviour.
    """
    if interval_s is None:
        return ""
    return i18n.t(WAKE_FRESHNESS_TEXT).replace(
        layout.VALUE_CONTROL_TEXT_TOKEN, str(_wake_minutes(interval_s)))


def wake_battery_observed_text(interval_s, battery_rows=None):
    """The battery half: an absolute figure only when this frame's own
    observed history supports one, and the named "not enough history
    yet" sentence in every other case. `""` when there is no interval.

    The figure is `battery.battery_life_estimate()`'s, never computed
    here: this function only chooses between a singular and a plural
    wording. Four of that estimator's five named trends carry no figure
    at all (no reading, not enough history, a rising series — a
    positive slope divides to a negative or infinite lifetime — and a
    flat one), and all four land on the same honest sentence here.

    `battery_rows` is a daily-average series in `history_db.py`'s row
    shape; `None`/`()` is the ordinary state of a fresh deployment and
    produces the unknown sentence rather than an empty card.
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

    Rendered unconditionally beside the battery sentence, not gated on
    `display_enabled`: the clause is true whichever way that switch is
    set, and a qualifier shown only once the screen is off is one
    nobody reads in time.

    The cadence goes through `layout.duration_text()` since it is a
    fixed constant; the two sentences above do not, since their number
    changes as the slider moves and would need a second copy of the
    ladder in JavaScript to recompute client-side.
    """
    return i18n.t(WAKE_BATTERY_SCREEN_OFF_TEXT) % layout.duration_text(
        device_config.DISPLAY_OFF_SLEEP_S)


def wake_battery_relative_template(saved_interval_s):
    """The relative clause's template, with the saved cadence already
    written into it and `#` left standing for the proposed one — or `""`
    when there is no usable saved cadence to compare against.

    "This setting wakes the frame every # min instead of every 10 min."

    Two whole cadences named in full, not a ratio: a ratio needs a
    decimal mark, and French writes it with a comma, so recomputing a
    ratio client-side would either print an English decimal on a French
    page or need the mark handed over as an attribute. Two integers
    need neither, and the saved cadence is baked in server-side (fixed
    for the life of the page), leaving only the proposed one as the
    script's one substitution.

    Routed through `battery.battery_life_estimate()`'s
    `relative_factor` for its guard, not for a number: that function
    already refuses a bool, non-numeric, non-positive or absurd cadence,
    and a clause built on a cadence it would refuse is about nothing.
    """
    estimate = battery.battery_life_estimate(
        (), saved_interval_s, saved_interval_s)
    if estimate["relative_factor"] is None:
        return ""
    return i18n.t(WAKE_BATTERY_INSTEAD_TEXT) % _wake_minutes(saved_interval_s)


def wake_battery_relative_text(proposed_interval_s, saved_interval_s):
    """The relative clause as the server would render it for a given
    proposal — `""` when the two cadences are the same, which is what
    every real page render produces (the server always renders the
    saved interval against itself, and echoing "every 10 min instead of
    every 10 min" would be noise).

    This is nonetheless a real function with a real return: it is the
    one definition of this sentence in Python, and `test_browser_ux.py`
    drives the slider in a browser and compares the script's own output
    against it.

    It never carries a days figure: that half comes from observed
    history and is server-rendered once, deliberately unreachable from
    script, so a script that could recompute it could also invent one.
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
    Never raises: a settings page that 500s because a battery history
    table could not be opened would be worse than a card that says it
    has no history yet.

    Read here rather than threaded through `ctx`: this is the only card
    that needs the series, and `page_context()` runs on every
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

    Server-rendered and outside the `.js` gate entirely: with scripts
    blocked a visitor can still type an interval, read what it means,
    and save it. Only the slider is gated, since a slider with no
    script is a control that drags and shows nothing. Rendering these
    server-side also gives the script something to update rather than
    create, so a failed script leaves correct sentences, not empty ones.

    Neither is a live region: they change on every step of a drag, and
    an `aria-live` region would re-announce the same phrase
    continuously. The range announces itself natively and points at
    these two via `aria-describedby`.
    """
    if interval_s is None:
        return ""
    # The freshness paragraph is entirely live (its whole text is
    # arithmetic on the value); the battery paragraph's figure came
    # from observed history, so only its trailing span (two cadences,
    # no days figure) may be rewritten by script.
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
        # The base: the readout says nothing while the proposed value
        # is still the saved one (every page load and no-JS render).
        layout.VALUE_CONTROL_READOUT_BASE_ATTR, interval_s,
        escape_html(wake_battery_relative_text(interval_s, interval_s)),
    )


def wake_slider_html(interval_s):
    """The range input, inside the `.js` gate — or `""` when there is
    no saved interval for it to start from.

    Carries no `name`: a named range would post a second value for
    `wake_interval_s` on every save, and whichever arrived last would
    win silently. The `<input type="number">` above is the only control
    on this card that posts; this one only writes into it through
    `value-controls.js`.

    No `role="slider"` either: a native range input already exposes
    slider semantics and the keyboard model value-controls.js
    implements by hand for a `<div>` handle, so adding the role would
    be a double-role error. It gets an `aria-label` and an
    `aria-describedby` pointing at the two gauges.

    Gated, since a range with no script is a control that drags and
    shows nothing; the two gauges and the number input are not gated,
    since a visitor with scripts blocked can still type and save one.

    `min`/`max` come from `device_config`, never re-typed, so this
    control can never accept what `save_device_config()`'s own
    server-side re-check would reject.
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
    """The Wake interval settings group. Unlike `quiet_hours_group()`,
    this group has no checkbox gate: a plain `<label>` wraps a single
    `<input type="number">`, not `class="settings-checkbox"`, which
    normalises a checkbox and would mis-size a text-like input.

    `min`/`max` are read from `device_config` rather than re-typed, so
    they can never drift apart from `save_device_config()`'s own
    server-side re-check.

    The `value` attribute is emitted only when `current_wake_interval_s`
    is an `int`, not a `bool`, within `[WAKE_INTERVAL_MIN_S,
    WAKE_INTERVAL_MAX_S]`; otherwise none is emitted and the placeholder
    carries the empty state. An out-of-range `value` on a native numeric
    input fails HTML5 constraint validation and blocks submission of
    the whole form, not just this field — a live risk, since
    `deploy/skypane.env.example` ships `SKYPANE_SLEEP_S=30`, below the
    60s floor, as the pre-fill fallback.

    On a rejected save (`submitted` carries this field), the raw
    submitted string is echoed back verbatim, deliberately bypassing
    the in-range/non-bool-int guard above, since that guard exists only
    for the ordinary ctx-sourced int — a rejected value like "7" would
    otherwise silently lose the echo the user needs to see. Native
    HTML5 min/max validation still applies on the next submit attempt.

    `battery_rows` is the daily-average series the battery gauge
    derives from, `()` by default. The two gauges append after the
    error block rather than interleaving with it, since they describe
    what the setting means and read after the control that sets it.
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
    # One resolution of the gauges' and the slider's subject, so the
    # three can never describe different values.
    gauge_interval_s = wake_gauge_interval_s(current_wake_interval_s, submitted)
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        # The label is its own element above the control (for=), not a
        # wrapping <label> — a wrapping label put its text and the
        # input on one line, misaligning this field against every
        # sibling field on the page.
        '<label for="%s">%s</label>'
        '<input type="number" id="%s" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="%s"%s%s>'
        # The unit as a sibling, aria-hidden: the label above already
        # names the unit, so repeating it would announce the fact twice.
        '<span class="text-label field-inline-value" aria-hidden="true">%s</span>'
        "%s"
        # The slider sits after the error message, not between it and
        # the field, so the error stays adjacent to the control it is
        # about. The gauges come last, since they describe what the
        # setting means, after the control that sets it.
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
    """The Notifications settings card (Device scope only): battery-low
    and frame-silent checkboxes plus a write-only push-topic URL field.

    `configured` is a bare bool, never the URL or a masked fragment of
    it — the status row and the input (no `value` attribute, ever)
    never reveal the stored secret, in either state.

    The URL field waits on the page-wide Save like every other Device
    field. Only "Send a test" (`notifications_test_section()`) is its
    own immediate-POST form, a sibling of `#settings-form`, since an
    immediate action must never nest inside the page-wide Save form.

    `errors`/`submitted` repopulate both checkboxes and their error
    messages on a rejected save; the URL field has nothing to
    repopulate, being write-only.
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
    # Reuses the Calendar card's "How it works" summary label rather
    # than a second, near-duplicate string. Unconditional: the
    # storage/replacement fact is true whether or not a URL is stored yet.
    how_it_works_html = (
        '<details><summary>%s</summary><p class="text-body">%s</p></details>'
    ) % (
        escape_html(i18n.t(CALENDAR_HOW_IT_WORKS_SUMMARY)),
        escape_html(i18n.t(NOTIFICATIONS_URL_HOW_IT_WORKS_BODY)),
    )
    field_html = (
        '<div class="rule-add-form__field">'
        '<label for="notifications-topic-url">%s</label>'
        '<input type="text" id="notifications-topic-url" '
        'name="notifications_topic_url" autocomplete="off" '
        'spellcheck="false" maxlength="%s"%s>'
        '<p class="text-label section-caption" id="%s">%s</p>'
        "%s"
        "%s"
        "</div>"
    ) % (
        escape_html(i18n.t(NOTIFICATIONS_URL_FIELD_LABEL)),
        NOTIFICATIONS_URL_MAX_LEN, url_error_attrs,
        escape_html(NOTIFICATIONS_URL_HINT_ID), escape_html(i18n.t(NOTIFICATIONS_URL_HINT)),
        url_error_html,
        how_it_works_html,
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
        # Cross-DOM form= binds this button to the sibling
        # notifications-test form (notifications_test_section() below).
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
    """The "Send a test" button's own empty `<form>`, a sibling of
    `<form id="{SETTINGS_FORM_ID}">` — an immediate action must never
    nest inside the page-wide Save form. `render()` emits this after
    `</form>` closes, on the Device scope only.

    Carries no `data-confirm`: the handler reads the stored URL from
    disk and never trusts the request body, which is the real
    mitigation, not a confirmation dialog.
    """
    # The action and id are literal path/attribute text, not a %s
    # interpolation: this module's acceptance gate greps them.
    # The form stays a sibling of #settings-form, since a <form> can
    # never nest inside another <form>; the button reaches it via
    # form="notifications-test".
    return (
        '<form method="post" action="/settings/notifications/test" '
        'id="notifications-test" class="notifications-test-form"></form>'
    )


def _masked_calendar_url(url):
    """host + "…" — never the path, query, fragment or userinfo of the
    stored calendar feed URL.

    Uses a real `urlsplit()` parse rather than a byte-offset truncation:
    a naive `url[:20] + "…"` would not be safe, since a short host could
    still leak leading path/query/token characters.

    Returns "" on any failure (falsy url, unparsable, empty netloc); the
    caller omits the masked-URL line entirely rather than fabricate one.
    This is the only place in the module that reads a stored secret URL
    back for display — every other secret-URL field stays write-only.
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


def _calendar_connection_html(
        configured, drift, last_synced_at, last_attempt_at, now, entry_count,
        errors=None, submitted=None, state_dir=None):
    """Calendar's connection block inside the Aspect card's Calendar
    row: status, connect/replace form or masked URL, and the cross-DOM
    Disconnect button. Returns `(row_body_html, disconnect_form_html)`
    — the disconnect form is returned separately because HTML forbids
    nesting it inside the row's own connect/replace form; the caller
    places each piece where it belongs.

    The feed URL field is write-only: never a `value` attribute, and
    only a masked `host + "…"` (`_masked_calendar_url()`) is shown once
    connected. Drift (an unreadable stored link) is checked before
    `configured`, since a drifted link already forces `configured`
    False.

    Disconnect posts an empty confirm field to a two-step,
    server-rendered confirm page (`calendar_disconnect_confirm_page()`
    below); the client-side `data-confirm` dialog is a misclick guard
    only, never the real gate.
    """
    # Drift first: it already forces `configured` False, so checking
    # `not configured` first would make this branch unreachable.
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
    # Literal id/action text, not a %s interpolation: this module's
    # acceptance gate greps the attribute text directly.
    disconnect_button_html = (
        '<button type="submit" form="calendar-disconnect-form" class="calendar-disconnect-btn">%s</button>'
    ) % escape_html(i18n.t(CALENDAR_DISCONNECT_BUTTON_TEXT))
    if configured:
        # configured=True here already means calendar_is_configured()'s
        # own drift guard passed upstream, so this second read is safe.
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

    # No wrapping element: the caller places this fragment directly
    # inside the Calendar <details> row.
    row_body_html = status_html + state_branch_html + how_it_works_html

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

    return row_body_html, disconnect_form_html


def calendar_disconnect_confirm_page(ctx):
    """Two-step disconnect confirmation, rendered whenever the posted
    confirm field does not exactly match the expected value (including
    a bare POST with none). This page is the actual security control:
    it works with JavaScript disabled, blocked by CSP, or against a
    hand-crafted request that skips the client-side confirm dialog.

    The form re-posts to the same route with the confirm field
    pre-filled; cancel is a plain link back to Display, never a second
    form. `ctx` is accepted but unused today, matching every other
    scoped builder's signature.
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
    """The manual poll-trigger control: an enabled button, or a
    native-disabled button with remaining-seconds copy while a cooldown
    is active.

    Emits zero `<script>` elements: the live countdown and
    disable-on-submit behaviour live in `companion/static/
    poll-cooldown.js`, driven by `data-*` attributes here, so the CSP
    can require `script-src 'self'` with no inline/nonce exception.
    Those affordances are UX only, never a trust boundary —
    `_handle_poll_now()` independently re-checks the cooldown
    server-side and serializes execution before ever polling.

    The caption is computed once, above both branches, so it never
    disappears for the whole cooldown window.
    """
    # `> 0`, not truthy: must agree with poll-cooldown.js's own
    # `remaining > 0` guard, or a negative value would disable the
    # button natively while the script no-ops, with no way to re-enable
    # it client-side.
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


# The per-flight colour-rules editor: an add form (its own immediate
# POST route) plus an always-present list with a plain per-row Delete
# button (its own immediate POST route).


def _rule_delete_action(kind, value):
    """The delete form's `action` for `(kind, value)`:
    `/settings/rules/{kind}/{value}/delete` — both segments are already
    normalised, allowlisted uppercase alphanumerics by the time a row
    reaches here, so `escape_html()` is the only encoding needed. One
    builder for both the desktop and mobile row renderers, so they can
    never diverge into building two different strings for the same row.
    """
    return "%s%s/%s%s" % (
        RULES_DELETE_ROUTE_PREFIX, escape_html(kind), escape_html(value),
        RULES_DELETE_ROUTE_SUFFIX,
    )


def _rule_kind_radio_html(kind, checked):
    """One native radio + `<label>` pair for the "Match by" segmented
    control. The radio is visually hidden and styled via the adjacent
    label (`.theme-form input[type="radio"] + label`); the plain-
    language word is the visible label text, and the technical term is
    the label's own `title` attribute, so a hovering mouse user still
    finds the exact vocabulary without it cluttering the visible label.
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
    """The one-line add-rule form: a `role="radiogroup"` of native
    radios styled as a segmented control, a value input, a compact
    theme-chip grid and an "Add rule" button, one `<form>` targeting
    `RULES_ADD_ROUTE`.

    No per-segment placeholder swap on selection (no script wires it):
    one static placeholder covers the always-valid default kind only.
    Validation errors render under the field, keeping the typed value.
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
    """Up to five distinct recent callsigns as suggestion chips, from
    `history_db.recent_runway_events()` (a second, independent call to
    the same shared helper `home_page._recent_flights()` uses, since
    page modules never import each other directly). The `<button
    type="button">` chips ship with no script to wire them in this
    phase, so they degrade to inert, never to invisible.

    Returns "" when there are no recent events, or on any read failure
    — never raises.
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
    """One `<li class="rule-row">`: the theme's two palette dots, the
    key, a kind badge, the theme's display name, and a Remove form.

    The Remove form's `data-confirm` is a misclick guard only: deleting
    a rule is immediately reversible (re-adding the same key restores
    it), and the server-side handler requires no confirm value.
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
        escape_html(i18n.t(device_config.theme_label(theme_id))),
        delete_form,
    )


def _rule_list_html(rows):
    """`<ul class="rule-list">`, one `.rule-row` per row.
    `colour_rules.rule_rows()` already orders rows most-specific first
    (callsign, then hex, then prefix) and alphabetically within each
    kind, so no re-sort is needed here. Returns "" for an empty list;
    the caller renders its own empty state in that case.
    """
    if not rows:
        return ""
    items = "".join(
        _rule_row_html(kind, value, theme_id)
        for kind, value, theme_id, _created_at in rows)
    return '<ul class="rule-list">%s</ul>' % items


def _nested_wrapper_html(html_fragment, base_class, nested_class):
    """Appends a `--nested` modifier class to a group builder's own
    outer wrapper, so a card rendered under a supersection heading
    renders one heading rung below it instead of Device's un-nested tier.

    `nested_class` is a literal string at every call site, never
    derived from `base_class`, so it stays grep-visible. Each builder
    emits its wrapper class exactly once as `class="{base_class}"`, so a
    single count-limited `str.replace()` is the whole mechanism.
    """
    needle = 'class="%s"' % base_class
    replacement = 'class="%s %s"' % (base_class, nested_class)
    return html_fragment.replace(needle, replacement, 1)


def _display_groups_html(builders, groups):
    """Display scope's two headed supersections: "What it watches"
    (Runway) and "When it is on" (Quiet hours) — each card gets the
    `--nested` modifier (`_nested_wrapper_html()`). Returns
    `(watches_html, on_html)`.

    Both cards render as siblings of the settings `<form>`, not inside
    it: their own inputs cross-submit via `form="{SETTINGS_FORM_ID}"`,
    since their instant-switch controls would otherwise need to nest a
    `<form>` inside another `<form>`, which HTML forbids.
    """
    runway_html = (
        _nested_wrapper_html(builders[screens.GROUP_RUNWAY](), "theme-status", "theme-status--nested")
        if screens.GROUP_RUNWAY in groups else "")
    watches_supersection_html = (
        layout.section_intro_html(
            DISPLAY_WATCHES_SECTION_ID, i18n.t(DISPLAY_WATCHES_HEADING),
            i18n.t(DISPLAY_WATCHES_INTRO))
        + runway_html
    )
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
    """Device scope's two headed supersections: "When it wakes" (Wake
    interval alone) and "How it tells you" (Diagnostic LED and
    Notifications together).

    Unlike `_display_groups_html()`, a supersection's heading is
    omitted entirely when every card under it is absent — an intro
    sentence introducing nothing is worse than no heading at all.
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


def render(ctx, scope=SCOPE_ALL, errors=None, submitted=None):
    """Render one settings page (SCOPE_ALL/SCOPE_DISPLAY/SCOPE_DEVICE).

    `errors`/`submitted` are optional keyword parameters, passed
    together only by a rejected save: `errors` is the dict
    `handle_post()` filled, `submitted` is the raw form dict, threaded
    into each group builder so a field can repopulate itself and show
    its own error.

    `submitted` is deliberately not defaulted to `{}`: `None` (an
    ordinary page load) and an actual dict (a repopulated submission)
    mean different things to `_submitted_checkbox_checked()` —
    collapsing that distinction would render every checkbox unchecked
    on every ordinary load, since an ordinary load never "submits" any
    of them either.
    """
    if errors is None:
        errors = {}
    device_cfg = ctx.get("device_config") or {}
    current_theme_id = device_cfg.get("theme", device_config.DEFAULT_THEME_ID)
    # Explicit `.get()`, no `or` fallback: `None` is a meaningful value
    # (no arrivals-theme override), not an oversight.
    current_theme_arriving = device_cfg.get("theme_arriving")
    current_runway_id = device_cfg.get(
        "tracked_runway", device_config.DEFAULT_RUNWAY_ID)
    current_led_enabled = device_cfg.get(
        "led_enabled", device_config.DEFAULT_LED_ENABLED)
    current_quiet_start = device_cfg.get(
        "quiet_hours_start", device_config.DEFAULT_QUIET_HOURS_START)
    current_quiet_end = device_cfg.get(
        "quiet_hours_end", device_config.DEFAULT_QUIET_HOURS_END)
    # `is None`, not `or`: 0 is never a valid wake_interval_s. Falls back
    # to the deployed SKYPANE_SLEEP_S env default when device_config has
    # no value yet (e.g. a fresh install with no systemd unit).
    current_wake_interval_s = device_cfg.get("wake_interval_s")
    if current_wake_interval_s is None:
        current_wake_interval_s = ctx.get("wake_interval_env_default")
    # Explicit `.get()`, no `or` fallback: `None` means no calendar
    # theme chosen yet, defaulting to the base theme.
    current_calendar_theme_id = device_cfg.get("calendar_theme_id")
    calendar_configured = ctx.get("calendar_configured")
    calendar_last_synced_at = ctx.get("calendar_last_synced_at")
    # last_attempt_at distinguishes "just connected, no sync yet" from
    # "has been failing"; entry_count feeds the status detail template.
    calendar_last_attempt_at = ctx.get("calendar_last_attempt_at")
    calendar_entry_count = ctx.get("calendar_entry_count") or 0
    calendar_drift = ctx.get("calendar_drift")
    # A device_config.json predating this field resolves through
    # device_config.DEFAULT_NOTIFICATIONS, never a KeyError.
    current_notifications = device_cfg.get("notifications") or device_config.DEFAULT_NOTIFICATIONS
    notifications_configured = bool(current_notifications.get("topic_url"))
    current_notifications_battery = current_notifications.get(
        "battery_low", device_config.DEFAULT_NOTIFICATIONS["battery_low"])
    current_notifications_silent = current_notifications.get(
        "frame_silent", device_config.DEFAULT_NOTIFICATIONS["frame_silent"])
    cooldown_remaining = ctx.get("poll_cooldown_remaining", 0)
    # next_wake_clock is the shared next-wake clock string threaded into
    # every group's caption and the Device header slot; None when
    # unknown (no check-in yet, or no known interval), and every
    # consumer omits the suffix/line in that case rather than show a
    # placeholder.
    next_wake_clock = None
    next_wake_iso, _, _ = wake.next_wake_status(
        ctx.get("last_checkin_ts"), device_cfg)
    if next_wake_iso:
        next_wake_parsed = layout.parse_iso(next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = layout.local_clock_text(
                next_wake_parsed, now_parsed=layout.parse_iso(ctx.get("now")))

    # data-dirty-form marks the form dirty-state.js watches to drive the
    # save bar below. The native Save button (STATIC_SAVE_FALLBACK_ATTR)
    # is the one save affordance on the page — an AST check pins it
    # reaching this function's own return as a bare name, so it can
    # never accidentally duplicate or vanish.
    #
    # No `hidden` attribute: this bar is the only save affordance for a
    # scripts-blocked visitor, so it must render visible by default.
    # dirty-state.js hides it at init and reveals it on real changes.
    # Cancel is a native `type="reset"` (works without script);
    # `[data-dirty-count]` starts empty to avoid a false "Unsaved
    # changes" announcement on every fresh, unscripted page load.
    dirty_changed_suffix_html = escape_html(i18n.t(DIRTY_CHANGED_SUFFIX))
    dirty_and_html = escape_html(i18n.t(DIRTY_AND))
    dirty_list_and_html = escape_html(i18n.t(DIRTY_LIST_AND))
    dirty_unsaved_singular_html = escape_html(i18n.t(DIRTY_UNSAVED_SINGULAR))
    dirty_unsaved_plural_html = escape_html(i18n.t(DIRTY_UNSAVED_PLURAL))
    dirty_saving_html = escape_html(i18n.t(DIRTY_SAVING_TEXT))
    dirty_initial_text_html = escape_html(i18n.t(DIRTY_BAR_INITIAL_TEXT))

    screen_id = screens.current_screen_id(ctx)
    screen = screens.screen_type(screen_id)
    if scope not in SCOPES:
        scope = SCOPE_ALL
    groups = scope_groups(scope, screen_id)

    # screens.GROUP_THEME/GROUP_CALENDAR have no entry here: their own
    # renderer (the Aspect card, built by render()'s Display branch)
    # contains real <form> elements that must never render as a literal
    # descendant of <form id="{SETTINGS_FORM_ID}">.
    builders = {
        screens.GROUP_RUNWAY: lambda: runway_fieldset(
            current_runway_id, ctx.get("runway_images") or (),
            errors=errors, submitted=submitted, next_wake_clock=next_wake_clock),
        screens.GROUP_LED: lambda: led_group(
            current_led_enabled, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock),
        screens.GROUP_QUIET_HOURS: lambda: quiet_hours_group(
            current_quiet_start, current_quiet_end,
            errors=errors, submitted=submitted),
        # Read inside the lambda so it costs nothing unless this group
        # is actually in scope.
        screens.GROUP_WAKE_INTERVAL: lambda: wake_interval_group(
            current_wake_interval_s, errors=errors, submitted=submitted,
            next_wake_clock=next_wake_clock,
            battery_rows=wake_battery_rows(ctx.get("state_dir"), ctx.get("now"))),
        screens.GROUP_NOTIFICATIONS: lambda: notifications_group(
            notifications_configured, current_notifications_battery,
            current_notifications_silent, errors=errors, submitted=submitted),
    }
    # Its own immediate-POST form; must render after </form> closes so
    # it never nests inside the settings form.
    notifications_test_html = (
        notifications_test_section() if screens.GROUP_NOTIFICATIONS in groups else "")
    # The LED switch's own instant-toggle form, for the same reason.
    quick_led_html = (
        quick_led_form_html(current_led_enabled) if screens.GROUP_LED in groups else "")
    if scope == SCOPE_DISPLAY:
        # The strip and this freshness line are the only elements this
        # page declares swappable (layout.REFRESH_SWAP_SELECTORS_BY_PAGE);
        # everything else here is a <form>, and a swap mid-edit would
        # corrupt it. The refresh loop also stands down while the save
        # bar reports unsaved edits.
        header = layout.page_header(
            i18n.t(DISPLAY_PAGE_TITLE), purpose=i18n.t(DISPLAY_PAGE_PURPOSE),
            freshness_html=layout.freshness_line_html(ctx.get("now")),
            action_html=_screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors))
        frame_strip_section_html = layout.frame_strip_html(
            ctx, return_to=layout.DISPLAY_ROUTE, next_wake_iso=next_wake_iso)
        hidden_html = _scope_fields_html(scope, layout.DISPLAY_ROUTE)
        show_poll = False
        # groups_html stays empty on Display: every saved control here
        # cross-submits from outside the form via
        # form="{SETTINGS_FORM_ID}".
        # submits from outside the form via `form="{SETTINGS_FORM_ID}"`,
        # exactly like Runway/Calendar already do (Structural Note 2's
        # own "the physical form becomes a pure submission target").
        #
        # Gated on GROUP_THEME alone: safe only because
        # companion/screens.py's one registered screen type lists
        # GROUP_THEME and GROUP_CALENDAR together (always both true or
        # both false today). A future screen type with only one of the
        # two must split this gate.
        aspect_section_html = (
            layout.section_intro_html(
                DISPLAY_LOOK_SECTION_ID, i18n.t(DISPLAY_LOOK_HEADING), i18n.t(DISPLAY_LOOK_INTRO))
            + _nested_wrapper_html(
                _aspect_card_html(
                    ctx, current_theme_id, current_theme_arriving, current_calendar_theme_id,
                    errors=errors, submitted=submitted, state_dir=ctx.get("state_dir"),
                    calendar_configured=calendar_configured, calendar_drift=calendar_drift,
                    calendar_last_synced_at=calendar_last_synced_at,
                    calendar_last_attempt_at=calendar_last_attempt_at, now=ctx.get("now"),
                    calendar_entry_count=calendar_entry_count),
                "page-section aspect-card", "page-section--nested")
            if screens.GROUP_THEME in groups else "")
        groups_html = ""
        (display_watches_supersection_html,
            display_on_supersection_html) = _display_groups_html(builders, groups)
    elif scope == SCOPE_DEVICE:
        header = layout.page_header(
            i18n.t(DEVICE_PAGE_TITLE), purpose=i18n.t(DEVICE_PAGE_PURPOSE),
            action_html=(
                _screen_caption_html(screen) + _screen_selector_html(screen_id, errors=errors)
                + _next_wake_caption_html(next_wake_clock)))
        hidden_html = _scope_fields_html(scope, layout.DEVICE_ROUTE)
        # The Frame strip renders only on Home and Display, never Device.
        frame_strip_section_html = ""
        show_poll = bool(screen.get("has_manual_poll"))
        groups_html = _device_groups_html(builders, groups)
        aspect_section_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""
    else:
        header = layout.page_header(i18n.t("Settings"))
        hidden_html = ""
        frame_strip_section_html = ""
        show_poll = True
        # SCOPE_ALL is the legacy, never-served whole-page render, kept
        # byte-identical to its pre-existing output for harness checks
        # against the full form; no live app.py route uses it.
        groups_html = "".join(builders[g]() for g in groups if g in builders)
        aspect_section_html = ""
        display_watches_supersection_html = ""
        display_on_supersection_html = ""

    poll_section_html = (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>" % (escape_html(i18n.t(POLL_SECTION_HEADING)), poll_trigger_section(cooldown_remaining))
        if show_poll else "")
    # Device-scope-only: wraps the Poll card under its own supersection,
    # "When you can't wait". "" on Display/SCOPE_ALL, which never set
    # show_poll for this branch.
    poll_supersection_html = (
        (layout.section_intro_html(
            DEVICE_POLL_SECTION_ID, i18n.t(DEVICE_POLL_HEADING), i18n.t(DEVICE_POLL_INTRO))
         + _nested_wrapper_html(poll_section_html, "page-section", "page-section--nested"))
        if scope == SCOPE_DEVICE and poll_section_html else "")

    return (
        header
        # The Frame strip renders after the header and before the
        # form; "" on Device and SCOPE_ALL.
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
        # The dirty bar is last, after </form> and the Poll section, so
        # its position: fixed sits outside the short settings form.
        # A native type="reset" Cancel and an empty-until-JS count span
        # keep this bar usable with no script (see local-variable
        # comment above).
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
        # "" on the Device/SCOPE_ALL paths (both set it to "" above).
        aspect_section_html,
        display_watches_supersection_html,
        notifications_test_html,
        quick_led_html,
        display_on_supersection_html,
        poll_supersection_html if scope == SCOPE_DEVICE else poll_section_html,
        dirty_changed_suffix_html,
        dirty_and_html,
        dirty_list_and_html,
        dirty_unsaved_singular_html,
        dirty_unsaved_plural_html,
        dirty_saving_html,
        dirty_initial_text_html,
        # STATIC_SAVE_FALLBACK_ATTR must reach here as a bare name for
        # the AST invariant checked elsewhere.
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
    # screen["label"] is translated at this display site (i18n.t());
    # the screen id itself never changes.
    return (
        '<p class="page-header__screen text-label">%s</p>'
        % escape_html(i18n.t(SCREEN_CAPTION_TEMPLATE) % i18n.t(screen["label"])))


NEXT_WAKE_HEADER_LABEL = "Next wake"
NEXT_WAKE_HEADER_VALUE_TEMPLATE = "≈ %s"


def _next_wake_caption_html(next_wake_clock):
    """The Device page header's "Next wake ≈ HH:MM" line (Home's own
    copy lives in `home_page.py`). Returns "" when `next_wake_clock` is
    falsy — no placeholder, no "unknown".
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
    """A `<select name="screen_id">` for switching which registered
    screen type this settings page edits. Returns "" when only one
    screen type is registered, since a one-option choice has no real
    decision value.

    Rendered inside `page_header()`'s action slot, visually before
    `<form id="{SETTINGS_FORM_ID}">` opens, but must still submit with
    it — the `form="{SETTINGS_FORM_ID}"` attribute makes that possible.

    `errors` renders a rejected `screen_id` message; no `submitted`
    repopulation is needed, since `current_screen_id` already reflects
    any rejected submission.
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


# The four outcomes of resolving the submitted calendar fields. Plain
# strings, never rendered and never travel in a URL. Four distinct
# sentinels (not e.g. two bools) so a caller cannot mistake one outcome
# for another by falsy-comparing the wrong pair.
CALENDAR_URL_SIGNAL_CARRY_FORWARD = "carry_forward"
CALENDAR_URL_SIGNAL_SET = "set"
CALENDAR_URL_SIGNAL_CLEAR = "clear"
CALENDAR_URL_SIGNAL_INVALID = "invalid"

# handle_post()'s per-field error messages, one constant per rejected
# field, so the copy exists in exactly one place. Sentence case, no
# stack-trace vocabulary, matching this file's label voice.
ERROR_INVALID_CHOICE = "That is not one of the available choices."
ERROR_UNEXPECTED_SWITCH_VALUE = "That switch sent an unexpected value."
ERROR_WAKE_INTERVAL_RANGE = "Enter a whole number of seconds between 60 and 3600."
ERROR_QUIET_HOURS_TIME_SHAPE = "Enter a time as HH:MM, for example 23:00."
# Covers both the over-length and the contradictory (calendar_url +
# calendar_disconnect together) cases; deliberately never echoes any
# part of the submitted URL back.
ERROR_CALENDAR_URL_INVALID = (
    "That link is too long, or conflicts with the disconnect option below.")

# A local copy of device_config's private HH:MM pattern — not imported,
# since it is private to that module. UX pre-check only:
# save_device_config()'s own identical gate is authoritative; a test
# pins the two patterns against the same input table so they cannot
# silently drift apart.
_QUIET_HOURS_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)\Z")


def _note_error(errors, field, message):
    """No-ops when `errors is None`. Otherwise sets `errors[field]`
    only if that field has no message yet, so a later, more generic
    gate can never overwrite an earlier, more specific one.
    """
    if errors is None:
        return
    if field not in errors:
        errors[field] = message


def submitted_calendar_signal(form):
    """The single definition of what a submitted `calendar_url` +
    `calendar_disconnect` pair means. Both `handle_post()` and the
    calendar-connect route call this, so the two can never disagree.

    An absent/empty URL with no checkbox resolves to carry-forward, not
    disconnect: the write-only URL field renders empty on every load
    regardless of state, so treating an ordinary save's empty
    submission as "disconnect" would silently wipe the calendar on
    every unrelated save.

    Never raises, and never itself persists — resolving the signal and
    acting on it are separate steps, so the caller can gate persistence
    behind other fields' validation first.

    The in-form checkbox these gates interpret no longer renders
    (disconnecting is its own route now), but a crafted request can
    still send it, so the gates stay to keep `handle_post()`'s
    all-or-nothing rejection covering that shape.
    """
    # A page that never rendered the Calendar group cannot have meant
    # anything by the field's absence.
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
    display/calendar/notifications state against `device_config`'s own
    registries and validators, then persist all fields in one
    `save_device_config()` call. Rejection is all-or-nothing: a crafted
    or invalid value in any field aborts before any write, so the
    on-disk state never falls out of sync with what the next page load
    would redisplay.

    Every checkbox not rendered on the current scope resolves absent
    -> `None` (leave unchanged), never `False` — a scope whose page
    never had a control for a field must not silently turn it off on
    an unrelated save. The two Notifications checkboxes are the
    exception: their card is always in scope when rendered, so absent
    there still means unchecked.

    `wake_interval_s` needs an explicit string-to-int conversion that
    `quiet_hours_start`/`quiet_hours_end` deliberately skip: those two
    are strings end-to-end in `device_config`, but the interval is an
    int there.

    `errors` is an optional dict, filled in place via `_note_error()`
    so a real user error is reported at its own field instead of
    falling through to the generic save-failed flash.

    The calendar secret write is layered after the device-config write,
    and only for the `set`/`clear` signals — `carry_forward` never
    calls it, since every call erases the fetched calendar registry.
    """
    state_dir = ctx["state_dir"]
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
    if submitted_screen_id is not None and submitted_screen_id not in screens.SCREEN_IDS:
        _note_error(errors, "screen_id", ERROR_INVALID_CHOICE)
        return FLASH_SAVE_FAILED
    if calendar_signal == CALENDAR_URL_SIGNAL_INVALID:
        _note_error(errors, "calendar_url", ERROR_CALENDAR_URL_INVALID)
        return FLASH_SAVE_FAILED
    # A shape bound against an absurd paste, checked only when the field
    # is actually in scope.
    if (
        screens.GROUP_NOTIFICATIONS in in_scope
        and submitted_notifications_topic_url
        and len(submitted_notifications_topic_url.strip()) > NOTIFICATIONS_URL_MAX_LEN
    ):
        _note_error(errors, "notifications_topic_url", ERROR_NOTIFICATIONS_URL_TOO_LONG)
        return FLASH_SAVE_FAILED
    # Both gates below exempt "" in addition to a real theme id: the
    # "Same as departures" chip submits "" for this field, and rejecting
    # it would reject the whole save whenever a user picks that option.
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
    # A malformed value here is a real user error, reported at this
    # field; absent still means unchanged (including structural absence
    # on a scope that never rendered this group).
    if submitted_qh_start is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_start):
        _note_error(errors, "quiet_hours_start", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    if submitted_qh_end is not None and not _QUIET_HOURS_TIME_RE.match(submitted_qh_end):
        _note_error(errors, "quiet_hours_end", ERROR_QUIET_HOURS_TIME_SHAPE)
        return FLASH_SAVE_FAILED
    # theme_arriving: out of scope or genuinely absent -> unchanged; ""
    # -> CLEAR_THEME_ARRIVING; anything else has already passed the
    # membership gate above, so it is a real theme id.
    if screens.GROUP_THEME not in in_scope:
        theme_arriving = None
    elif submitted_theme_arriving is None:
        theme_arriving = None
    elif submitted_theme_arriving == "":
        theme_arriving = device_config.CLEAR_THEME_ARRIVING
    else:
        theme_arriving = submitted_theme_arriving
    if submitted_led is None:
        led_enabled = None
    elif submitted_led == LED_CHECKBOX_VALUE:
        led_enabled = True
    else:
        _note_error(errors, "led_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
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
        # A syntactically valid but out-of-range value would otherwise
        # only surface via save_device_config()'s own generic
        # ValueError; checked here to report it at this field.
        if not (
            device_config.WAKE_INTERVAL_MIN_S
            <= wake_interval_s
            <= device_config.WAKE_INTERVAL_MAX_S
        ):
            _note_error(errors, "wake_interval_s", ERROR_WAKE_INTERVAL_RANGE)
            return FLASH_SAVE_FAILED
    if submitted_display is None:
        display_enabled = None
    elif submitted_display == DISPLAY_CHECKBOX_VALUE:
        display_enabled = True
    else:
        _note_error(errors, "display_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
        return FLASH_SAVE_FAILED
    # Unlike the fields above, these two checkboxes DO resolve absent ->
    # False: their card is always in scope when rendered (see docstring).
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
        # An empty submission means leave the stored URL unchanged,
        # never clear it — there is no UI affordance to clear a
        # configured topic URL. Read fresh from disk rather than from
        # ctx, so this is correct even with a stale ctx.
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
            # Written from the session's resolved language at save
            # time; there is no language-picking control for this
            # group (the poll loop has no browser to ask).
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

    if calendar_signal == CALENDAR_URL_SIGNAL_CLEAR:
        if not calendar_rules.save_calendar_url(
                state_dir, calendar_rules.CLEAR_CALENDAR_URL):
            return FLASH_SAVE_FAILED
    elif calendar_signal == CALENDAR_URL_SIGNAL_SET:
        if not calendar_rules.save_calendar_url(
                state_dir, submitted_calendar_url.strip()):
            return FLASH_SAVE_FAILED

    return FLASH_SAVED
