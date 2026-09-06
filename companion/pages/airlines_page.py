"""companion/pages/airlines_page.py — an illustration gallery over the
panel renderer's own airline art (D-13 through D-17, 06.6.4.1-CONTEXT.md),
plus (phase 13, 13-04-PLAN.md) the operator-facing "resolve an
unidentified flight" surface and its manual-resolutions management list.

The gallery itself is still presentation-only over exactly one public
accessor, `server.plane.illustrations.target_variants_by_airline()` — it
renders the full static curated list from `_ILLUSTRATION_TARGETS`, never
a detection-history cross-reference, and opens no SQLite database
connection of any kind (06.6.4.1's own D-17 non-goal, unchanged).

Phase 13 narrowly supersedes the OLDER half of that same D-17 sentence
("reads no poll state"): `unresolved_row_for_prefix()` reads
`server.poll_loop.load_poll_state()` — read-only, exactly once per
render, gated behind the presence of `ctx["resolve_prefix"]` — as its
D-11 membership test against the live unresolved-callsign-prefix
registry (13-CONTEXT.md D-11/D-12). This is a deliberate, narrow, new
capability this phase adds, not a reopening of the 06.6.4.1 registry-
migration this module still otherwise honours: no history-database
module and no `sqlite3` import are added, and the unresolved-prefix
registry table/statistics breakdown themselves are still rendered
exactly once, by `health_page.py` alone (D-13 below).

Since quick task 260902-req-02, this page's `<img>` tags are no longer a
bare pointer at the raw vendored PNG: `companion/app.py`'s
`Handler._serve_illustration_image()` now serves the file through
`companion.illustration_normalize`, which re-centres every illustration's
painted content into one shared frame. This module's own contribution to
that fix is cosmetic-but-load-bearing — each `<img>` carries explicit
`width`/`height` attributes matching `illustration_normalize`'s output
size, imported (not hand-typed) from that module's module-level constants,
so the browser reserves the right box before the image loads and the grid
does not reflow as cards stream in (`loading="lazy"` alone does not
prevent that; intrinsic dimensions do).

The unresolved-callsign-prefix registry (formerly CFG-04) and the
resolution-rate statistics breakdown (formerly CFG-08) that used to live
on this page moved to `companion/pages/health_page.py` in this same
phase (06.6.4.1, plan 04, D-11/D-12) — that is now the one page in the
app that RENDERS them (D-13); this module still never shows that
registry table or that statistics breakdown itself. This move is
complete as of 06.6.4.1 plan 06 Task 3: this module still imports no
history-database module and opens no SQLite connection of any kind.
Phase 13 (13-04-PLAN.md Task 1) is the one addition to that otherwise-
unchanged boundary: `import server.poll_loop as poll_loop`, used solely
by `unresolved_row_for_prefix()`'s single read-only membership test —
see that function's own docstring for the full D-11/D-12 reasoning.
"""
import os
import re

from companion.illustration_normalize import (
    ILLUSTRATION_TARGET_HEIGHT,
    ILLUSTRATION_TARGET_WIDTH,
)
from companion.layout import escape_html
import companion.layout as layout
from server.plane import illustrations
# Phase 13 (D-01/D-06/D-11/D-12): `manual_resolutions` and `enrich` are the
# runtime-writable-registry and provenance-seam modules the resolve section
# below reads. `poll_loop` is imported the same way `health_page.py`
# already imports it (`import server.poll_loop as poll_loop`) — that module
# sanctions the crossing point, and `companion/pages/__init__.py` only
# forbids a page module importing another page module, not this. None of
# the three creates an import cycle: none of `manual_resolutions`, `enrich`
# or `poll_loop` imports this page module.
from server.plane import manual_resolutions
from server.plane import enrich
import server.poll_loop as poll_loop

# D-15: this page's illustration image route mirrors companion/app.py's
# own ILLUSTRATION_IMAGE_ROUTE_PREFIX exactly — duplicated, not imported,
# since app.py imports this module (the reverse import would be a
# cycle). Same duplicated-not-imported discipline this codebase already
# uses for its static-script route constants; pinned by a cross-module
# equality check in companion/test_status_pages.py.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"

GALLERY_PURPOSE_TEXT = (
    "Illustration reference for every airline this frame can recognize.")

CARD_IMAGE_ALT_TEMPLATE = "%s illustration"

# quick task 260902-tli: the click-to-enlarge lightbox. This gallery
# reuses History's already-shipped `<dialog>` lightbox and the document-
# level click delegation companion/static/panel-lookup.js already
# performs, rather than inventing a second mechanism — that script keys
# on getElementById("panel-lookup-dialog") and a data-view-panel-src
# ancestor walk, and two pages never render simultaneously, so reusing
# its id and attribute names here creates no duplicate-id condition and
# needs no script change of any kind. The five names below are
# duplicated from companion/pages/history_page.py and from
# panel-lookup.js's own literals, not imported — a page module has no
# import path to a sibling page module (companion/pages/__init__.py's
# boundary) and none at all to a static script — and a cross-module
# equality guard in companion/test_view_pages.py pins all four
# dialog/attribute constants against history_page.py's own values, so a
# drift here would fail loudly instead of leaving the trigger silently
# inert.
LIGHTBOX_DIALOG_ID = "panel-lookup-dialog"
_VIEW_PANEL_SRC_ATTR = "data-view-panel-src"
_VIEW_PANEL_CAPTION_ATTR = "data-view-panel-caption"
_VIEW_PANEL_CLOSE_ATTR = "data-view-panel-close"

# quick task 260903-btu: unlike the four names above, these two have no
# history_page counterpart — History's own dialog deliberately renders
# neither a replace form nor this attribute, so they must never be added
# to test_view_pages.py's _airlines_lightbox_constants_match_history()
# pairs tuple (doing so would fail with an AttributeError, and worse,
# would push this project toward giving History an upload form). Both
# literals are, like the four above, duplicated into
# companion/static/panel-lookup.js rather than imported — one
# getAttribute() literal, one querySelector() literal — and
# LIGHTBOX_REPLACE_FORM_CLASS is additionally duplicated into
# companion/static/style.css's selector. A page module has no import
# path to a static asset, the same duplicated-not-imported discipline
# the four constants above already document; a cross-file guard in
# companion/test_view_pages.py pins all of this (quick task 260903-btu
# Task 4). quick task 260903-df3: the same "no history_page counterpart,
# never add to that pairs tuple" rule extends to
# LIGHTBOX_REPLACE_ZONE_CLASS, REPLACE_HINT_CLASS and REPLACE_ICON_CLASS
# below — three more names with no history_page twin.
_VIEW_PANEL_REPLACE_ACTION_ATTR = "data-view-panel-replace-action"
LIGHTBOX_REPLACE_FORM_CLASS = "lightbox__replace"

# quick task 260903-df3: three more class constants, in this file's own
# `.lightbox__replace*` BEM-ish convention, for the framed action zone
# that wraps the form's contents. Each is, like STAT_TILE_ICON_CLASS in
# companion/layout.py, duplicated (not imported) into
# companion/static/style.css's selectors — a page module has no import
# path to a static asset — and a cross-file guard in
# companion/test_status_pages.py pins the pair. Unlike
# LIGHTBOX_REPLACE_FORM_CLASS above, none of these three appears in
# companion/static/panel-lookup.js — the script does not know about them
# and must not be taught to; it only ever looks up the form itself by
# LIGHTBOX_REPLACE_FORM_CLASS.
LIGHTBOX_REPLACE_ZONE_CLASS = "lightbox__replace-zone"
REPLACE_HINT_CLASS = "lightbox__replace-hint"
REPLACE_ICON_CLASS = "lightbox__replace-icon"

# Phase 14 (14-02-PLAN.md Task 1, 14-UI-SPEC.md § Interaction Contract
# "Attribute vocabulary"): the eleven new `data-view-panel-*` names
# every trigger's widened vocabulary carries, joining the four existing
# _VIEW_PANEL_*_ATTR constants above. Every one of these is read by
# companion/static/panel-lookup.js only from plan 14-05 onward — until
# then they are server-rendered vocabulary the script does not yet
# consume, classified into companion/test_view_pages.py's
# _LIGHTBOX_RENDER_ONLY_TOKENS tuple by this same plan's Task 3.
_VIEW_PANEL_HEADING_ATTR = "data-view-panel-heading"
_VIEW_PANEL_MODE_ATTR = "data-view-panel-mode"
_VIEW_PANEL_MANUAL_ATTR = "data-view-panel-manual"
_VIEW_PANEL_SCOPE_ATTR = "data-view-panel-scope"
_VIEW_PANEL_RESOLVE_PREFIX_ATTR = "data-view-panel-resolve-prefix"
_VIEW_PANEL_FIRST_SEEN_ATTR = "data-view-panel-first-seen"
_VIEW_PANEL_LAST_SEEN_ATTR = "data-view-panel-last-seen"
_VIEW_PANEL_COUNT_ATTR = "data-view-panel-count"
_VIEW_PANEL_UPLOAD_ACTION_ATTR = "data-view-panel-upload-action"
_VIEW_PANEL_DELETE_ACTION_ATTR = "data-view-panel-delete-action"
_VIEW_PANEL_MANUAL_NOTE_ATTR = "data-view-panel-manual-note"

# Value vocabularies (14-UI-SPEC.md § Interaction Contract): no
# mode/manual string is ever a bare literal at a call site.
_VIEW_PANEL_MODE_ART = "art"
_VIEW_PANEL_MODE_GAP = "gap"
_VIEW_PANEL_MODE_NEEDS_ARTWORK = "needs-artwork"
_VIEW_PANEL_MANUAL_ACTIVE = "active"
_VIEW_PANEL_MANUAL_SUPERSEDED = "superseded"

# Phase 14 dialog element classes (14-UI-SPEC.md § Component Inventory
# "New CSS" table — plan 14-03 adds the actual CSS rules; this plan only
# declares the constants and wires them into markup).
LIGHTBOX_HEADING_CLASS = "lightbox__heading"
LIGHTBOX_MANUAL_NOTE_CLASS = "lightbox__manual-note"
LIGHTBOX_RESOLVE_NAME_CLASS = "lightbox__resolve-name"
LIGHTBOX_DELETE_CLASS = "lightbox__delete"

# Promoted from bare literals already used below (existing values
# unchanged) so this phase's guard can pin them and no second literal
# source of truth survives.
RESOLVE_UPLOAD_ZONE_CLASS = "resolve-upload-zone"
RESOLVE_CONTEXT_CLASS = "resolve-context"

ZOOM_LABEL_TEMPLATE = "Enlarge %s illustration"

# quick task 260902-tli: went through two rounds of live developer
# feedback. Originally named the normalized frame size in the copy
# itself ("Shown at the shared 900x263 frame..."), which real testing
# found meaningless. The reworded, more user-facing version ("This is
# the same artwork the physical panel draws...") was ALSO rejected on
# the same live pass — the developer's call was that no caption is
# wanted here at all, unlike History's own note, which explains a real
# possible discrepancy (a stale render) an Airlines illustration never
# has. So this is the empty string, not a sentence — the element must
# still exist (panel-lookup.js's shared guard clause requires
# .lightbox__note to be present or the whole click handler never
# attaches, for this page or History's), but style.css's
# `.lightbox__note:empty { display: none; }` collapses it to no visible
# space. history_page.LIGHTBOX_NOTE's own naming is kept for the
# constant despite carrying no text, so a future non-empty note needs
# only a value change here, not a markup change.
LIGHTBOX_NOTE = ""

# quick task 260902-v26: the three flash keys `Handler._handle_illustration_
# replace()` (companion/app.py) can redirect with, defined here — not in
# app.py — for the identical reason companion/pages/config_page.py owns
# its own FLASH_SAVED/FLASH_SAVE_FAILED/etc. literals (see that module's
# own comment): app.py already imports this page module, so the reverse
# import would be a cycle. app.py rebinds these under FLASH_KEY_* names,
# adds their copy to FLASH_MESSAGES, and their ARIA role to FLASH_ROLES,
# mirroring config_page.py's own FLASH_* rebinding pattern exactly.
FLASH_ILLUSTRATION_REPLACED = "illustration_replaced"
# "Rejected" means the upload was read and parsed but is not an
# acceptable illustration (not an image, too small, not landscape, no
# transparency, or the request was over the size cap) — a normal,
# expected outcome of validation, not a server malfunction.
FLASH_ILLUSTRATION_REJECTED = "illustration_rejected"
# Distinct from FLASH_ILLUSTRATION_REJECTED: this key means something
# unexpected happened server-side while storing an otherwise-acceptable
# upload (a filesystem error, an unexpected Pillow failure after
# validation already passed) — mirrors FLASH_SAVE_FAILED's own
# genuine-server-failure framing in config_page.py.
FLASH_ILLUSTRATION_REPLACE_FAILED = "illustration_replace_failed"

# Phase 13 (D-11/D-12/D-13, 13-04-PLAN.md Task 1): the resolve-flow flash
# keys. Same reasoning as the FLASH_ILLUSTRATION_* block above (app.py
# already imports this page module, so the reverse import would be a
# cycle) — companion/app.py (plan 13-06) rebinds these under FLASH_KEY_*
# names and adds their copy/ARIA role, mirroring the existing
# FLASH_ILLUSTRATION_* rebinding pattern exactly.
FLASH_MANUAL_RESOLVED = "manual_resolved"
FLASH_MANUAL_NAME_EMPTY = "manual_name_empty"
FLASH_MANUAL_NAME_TOO_LONG = "manual_name_too_long"
FLASH_MANUAL_NAME_RESERVED = "manual_name_reserved"
FLASH_MANUAL_PREFIX_STALE = "manual_prefix_stale"
FLASH_MANUAL_REGISTRY_FULL = "manual_registry_full"
# Planner addition, not in 13-UI-SPEC.md's Full Copy Deck:
# `manual_resolutions.add_entry()` returns ADD_FAILED on an unwritable
# state dir and never raises. Without this key, that failure would
# redirect with no message at all, and 13-CONTEXT.md's governing
# constraint is that the operator is never silently misled. Mirrors
# FLASH_ILLUSTRATION_REPLACE_FAILED's own genuine-server-failure-vs-
# validation-rejection framing exactly.
FLASH_MANUAL_SAVE_FAILED = "manual_save_failed"
# Same justification as FLASH_MANUAL_SAVE_FAILED above, for
# `manual_resolutions.delete_entry()` returning `False` after a write
# failure (as opposed to `False` for an unknown/malformed prefix, which
# needs no flash — the row is simply already gone).
FLASH_MANUAL_DELETE_FAILED = "manual_delete_failed"

# Phase 14 (14-02-PLAN.md Task 1, closing 13-UAT.md's gap G-01): a name
# the operator genuinely typed but which manual_resolutions.py's own
# key-slugger cannot turn into a usable illustration key (e.g. a name
# that slugs to the empty string). (a) This key is declared here,
# beside every other manual flash key this module owns, but is wired
# into companion/app.py's FLASH_KEY_* rebinding and FLASH_MESSAGES/
# FLASH_ROLES by plan 14-07, not by this plan. (b) It closes
# 13-UAT.md's G-01, where such a name was reported back to the operator
# as though they had submitted an EMPTY name (FLASH_MANUAL_NAME_EMPTY)
# — technically accurate about the downstream failure mode, but false
# about what the operator actually did, which 13-CONTEXT.md's governing
# constraint (never silently mislead the operator) forbids. (c) It is a
# deliberate, recorded extension of 14-UI-SPEC.md's Copywriting
# Contract, whose Error-state row scoped this phase to "no new flash
# key" before 14-CONTEXT.md's Deferred Ideas elevated G-01 into this
# phase's scope. Declaring it here and wiring it in 14-07 (a different
# wave) is what lets G-01 be fixed without two plans contending for
# this file in the same wave.
FLASH_MANUAL_NAME_UNUSABLE = "manual_name_unusable"

# Deleting a manual resolution deliberately produces NO success flash:
# 13-UI-SPEC.md's Full Copy Deck has none, and the row disappearing from
# the management list (Task 2) is the confirmation. Only the failure path
# above speaks.

# Phase 13 (D-11/D-12/D-13): route constants for the resolve flow,
# duplicated-not-imported exactly as ILLUSTRATION_ROUTE_PREFIX already is
# above (companion/app.py imports this module, so the reverse import
# would be a cycle) — pinned by a cross-module equality check in
# companion/test_status_pages.py (plan 13-06).
RESOLVE_ROUTE = "/airlines/resolve"
MANUAL_DELETE_ROUTE_PREFIX = "/airlines/manual-resolutions/"
MANUAL_DELETE_ROUTE_SUFFIX = "/delete"
AIRLINES_ROUTE = "/airlines"
RESOLVE_QUERY_PARAM = "resolve"

# Phase 13 copy constants, byte-identical to 13-UI-SPEC.md's Full Copy
# Deck (real U+2014 em dashes, real U+2019 apostrophes, matching every
# other string in this module).
RESOLVE_BACK_LINK_TEXT = "← Back to Health"
RESOLVE_STALE_BODY = (
    "That coverage gap isn’t there anymore — it may already be "
    "resolved. Check Health for current gaps.")
RESOLVE_HEADING = "Resolve an unidentified flight"
# Phase 14 (14-02-PLAN.md Task 1, D-01) reworded this template in place,
# replacing its Phase 13 wording: one template with no callsign clause,
# so it stays true on the CR-02 row-gone path where no sighting data
# survives. This wording is what discharges D-01's obligation that the
# dialog state the per-prefix scope at the moment of acting.
RESOLVE_CAPTION_TEMPLATE = (
    "Every flight using prefix %s will show as this airline once you "
    "save a name.")
RESOLVE_CONTEXT_LABELS = (
    "Prefix", "First seen", "Last seen", "Times seen", "Example callsign")
# Phase 14 (14-02-PLAN.md Task 1): the five per-<dd> hook classes
# 14-UI-SPEC.md's Component Inventory requires, a 5-tuple aligned 1:1
# with RESOLVE_CONTEXT_LABELS above so the two can only ever be zipped,
# never mismatched.
RESOLVE_CONTEXT_DD_CLASSES = (
    "resolve-context__prefix",
    "resolve-context__first-seen",
    "resolve-context__last-seen",
    "resolve-context__count",
    "resolve-context__callsign",
)
NAME_LABEL_TEXT = "Airline name"
NAME_HINT_TEXT = (
    "Start typing — pick a suggestion if the airline already has "
    "artwork, so this reuses it instead of asking for a new upload.")
SAVE_BUTTON_TEXT = "Save airline name"
STEP_B_HEADING_TEMPLATE = "Add an illustration for %s"
STEP_B_CAPTION = (
    "Saved. This airline doesn’t have artwork yet — add one "
    "below, or skip for now.")
STEP_B_SKIP_TEXT = "Skip — I’ll add artwork later"
# Planner addition, not in 13-UI-SPEC.md's Full Copy Deck: the fourth
# reachable state (a bookmark or a Back press landing on a prefix that is
# still listed as a gap but is already fully resolved — a manual entry
# names an airline that already has artwork). The deck enumerated three
# states; this is the fourth. Saying "that gap isn't there anymore" here
# (RESOLVE_STALE_BODY) would be false, and false is the one thing
# 13-CONTEXT.md forbids.
RESOLVE_ALREADY_DONE_TEMPLATE = (
    "%s is already named for this prefix and has artwork — nothing "
    "more to do here.")

MANUAL_NAME_INPUT_ID = "manual-airline-name"
MANUAL_UPLOAD_INPUT_ID = "manual-illustration-input"
MANUAL_DATALIST_ID = "known-airlines"

# Phase 13 (13-04-PLAN.md Task 2, D-06/D-07): the manual-resolutions
# management list's copy constants, byte-identical to 13-UI-SPEC.md's
# Full Copy Deck.
MANUAL_SECTION_HEADING = "Manually resolved prefixes"
MANUAL_SECTION_CAPTION = (
    "Airlines you’ve named by hand for a prefix the frame couldn’t "
    "otherwise identify.")
MANUAL_EMPTY_HEADING = "No manual resolutions yet."
MANUAL_EMPTY_BODY = (
    "Resolve an unidentified flight from Health’s coverage-gap list "
    "to add one here.")
MANUAL_RESOLUTION_HEADERS = ("Prefix", "Airline name", "Added", "Status", "Delete")
SUPERSEDED_MARKER_TEXT = "Superseded"
SUPERSEDED_MARKER_TITLE = (
    "The frame’s built-in airline list now also recognizes this "
    "prefix — its entry wins, and this manual name is no longer used.")
SUPERSEDED_CAPTION = (
    "A prefix is marked Superseded once the frame’s built-in list "
    "also recognizes it — the built-in entry wins. Delete and re-add "
    "to point it somewhere else.")
DELETE_BUTTON_TEXT = "Delete"
SUPERSEDED_STATUS_CLASS = "manual-resolution__status--superseded"

# Phase 14 (14-02-PLAN.md Task 1, 14-UI-SPEC.md's Full Copy Deck): new
# copy for the gap card, the dialog's manual-state chip/note, the
# shared delete form's caption, the gap-overflow line and the
# manual-resolutions summary line. Every constant here is read by both
# the no-JS fallback and the dialog's static markup, through the shared
# rendering functions plan 14-02's Task 2 introduces.
GAP_CARD_ARIA_TEMPLATE = "Resolve prefix %s — example callsign %s"
MANUAL_CHIP_ACTIVE_TEXT = "Resolved by hand"
MANUAL_DELETE_CAPTION = (
    "Deleting removes only this manual name — any uploaded artwork "
    "stays in place.")
# %s arity: prefix, built-in name, operator's name, built-in name again.
MANUAL_SUPERSEDED_NOTE_TEMPLATE = (
    "SkyPane’s built-in list now recognizes prefix %s as “%s” — its "
    "entry wins over the name you gave it (“%s”), so that artwork is "
    "no longer shown. Add artwork for “%s” below, or delete this "
    "entry.")
# Two constants, not one: only the tail is the <a>'s own text; their
# concatenation must equal 14-UI-SPEC.md's single deck string
# byte-for-byte (asserted in plan 14-04's own harness check).
MANUAL_OVERFLOW_TEMPLATE = "%d other unresolved prefixes — "
MANUAL_OVERFLOW_LINK_TEXT = "see the full list"
# With-superseded and no-superseded forms (D-11) — %d arity: manual
# count, then superseded count (with-superseded form only).
MANUAL_SUMMARY_TEMPLATE = "%d manual resolutions, %d superseded"
MANUAL_SUMMARY_TEMPLATE_NONE = "%d manual resolutions"

# CR-02 fix (13-REVIEW.md): the only route into Step B is
# ?resolve={prefix}, and D-14 clears a resolved prefix from the live gap
# registry on the very next poll cycle — including the cycle right
# after Step A itself saves a name for it. Health's per-row deep link
# (D-10) is gone by the time an operator would look for it again, and
# without an entry point here an active entry with no artwork became a
# dead end (and, per D-07, so did the delete-and-re-add correction
# path — POST /airlines/resolve for a prefix no longer in the gap
# registry returns manual_prefix_stale). This management list already
# renders every manual entry (D-07), so it gets the entry point: a
# per-row link into the identical ?resolve={prefix} URL
# `_resolve_section_html()` now serves this state from regardless of
# live-gap membership (see that function's own CR-02 docstring
# paragraph). Rendered only for an ACTIVE entry whose key currently has
# no resolved artwork — never for a superseded entry, and never
# alongside the Superseded marker (the status cell holds exactly one of:
# nothing, this link, or that marker).
ADD_ARTWORK_LINK_TEXT = "Add artwork"

# quick task 260902-v26 (D-04 is explicitly a negative requirement: no
# revert-to-original control is in scope, anywhere, for this feature).
# The replace-image control's own copy, each its own module-level
# constant so the harness can assert against the constant rather than a
# duplicated literal.
#
# quick task 260903-btu: REPLACE_SUMMARY_TEMPLATE and
# REPLACE_LABEL_TEMPLATE (both %s-airline-name templates) are gone. The
# shared lightbox that now hosts this form is emitted once per page, so
# at render time there is no single airline name to interpolate into
# either template's %s slot — and the dialog already names the airline
# through its own caption (written from data-view-panel-caption at click
# time), so a generic label sitting directly under that caption reads
# unambiguously. REPLACE_LABEL_TEXT replaces both: it absorbs the job
# the old <summary> used to do (naming the action), since there is no
# <summary> disclosure any more. REPLACE_BUTTON_TEXT carries over
# byte-identical — already-approved copy whose meaning still fits
# exactly. REPLACE_INPUT_ID is now a single static id, correct and
# sufficient since exactly one file input exists on the whole page — the
# old per-key id derivation has nothing left to disambiguate.
REPLACE_LABEL_TEXT = "Replace this illustration"
REPLACE_BUTTON_TEXT = "Upload"
REPLACE_INPUT_ID = "airline-replace-input"

# quick task 260903-df3: forward-looking guidance, stating the app's own
# real validation rule before the upload rather than only after it — the
# positive twin of companion/app.py's FLASH_KEY_ILLUSTRATION_REJECTED
# ("Couldn't use that image — upload a transparent PNG that's at least
# 1200 pixels wide and landscape (wider than tall)."). Keep the two
# describing the same rule if either ever changes. This copy must contain
# none of the words revert/reset/restore/undo/original — D-04's
# no-revert-control membership scan in test_status_pages.py treats any of
# them inside this form as a failure.
REPLACE_HINT_TEXT = "Transparent PNG, at least 1200px wide, landscape."

# variant_chip_label()'s two shape-domain patterns. An alphanumeric type
# code is a letter prefix immediately followed by digits, optionally with
# a hyphenated numeric suffix ("a320", "atr72", "a330", "b737",
# "a350-1000"). Anything else is a word-form manufacturer shape
# ("embraer", "beechcraft1900d") — see variant_chip_label()'s own
# docstring for the domain-mismatch trap neither pattern may fall into.
_TYPE_CODE_RE = re.compile(r"^[a-z]+\d[\d-]*$")
_WORD_MODEL_RE = re.compile(r"^([a-z]+)(\d.*)$")


def variant_chip_label(shape):
    """Display transform for one fleet-variant chip
    (06.6.4.1-UI-SPEC.md §7.1). `shape` is a free-text filename suffix
    from `_ILLUSTRATION_TARGETS`, reached only through
    `illustrations.target_variants_by_airline()` — e.g. `"a350-1000"` —
    a DIFFERENT domain from `illustrations.SHAPE_SLUGS`' seven-member
    ICAO-type classification.

    TRAP: this function must never validate `shape` against
    `SHAPE_SLUGS` membership before deciding how (or whether) to render
    it — `"a350-1000"` is a real, live entry that such a check would
    silently drop, since it is not itself a `SHAPE_SLUGS` member (only
    its un-suffixed `"a350"` root is). The branch below is derived from
    the shape string's own form, never from that tuple.

    An alphanumeric type code upper-cases verbatim (`"a320"` ->
    `"A320"`, `"atr72"` -> `"ATR72"`, `"a330"` -> `"A330"`, `"b737"` ->
    `"B737"`, `"a350-1000"` -> `"A350-1000"`). A word-form manufacturer
    shape title-cases instead (`"embraer"` -> `"Embraer"`), splitting a
    trailing digit-led model number into its own word
    (`"beechcraft1900d"` -> `"Beechcraft 1900D"`).
    """
    if not isinstance(shape, str) or not shape:
        return ""
    if _TYPE_CODE_RE.match(shape):
        return shape.upper()
    word_match = _WORD_MODEL_RE.match(shape)
    if word_match:
        word, model = word_match.groups()
        return "%s %s" % (word.title(), model.upper())
    return shape.title()


def _illustration_cache_buster(key, state_dir):
    """Return a `"?v={mtime}"` query suffix for `key`'s override file, or
    the empty string when there is no `state_dir` or no override exists
    yet (quick task 260902-v26).

    Why this is needed at all: the illustration route
    (`companion/app.py`'s `Handler._serve_illustration_image()`, via
    `Handler.send_bytes(..., cache_seconds=300)`) serves `Cache-Control:
    private, max-age=300`. Without a URL change, a freshly-replaced image
    would keep showing the stale, pre-upload image in the developer's
    browser for up to five minutes after a successful upload — reading as
    "the upload didn't work" rather than as a cache artifact. Keying the
    suffix on the override file's own mtime means the URL changes exactly
    when the bytes change, and never otherwise: rendering this page again
    before the next upload reproduces the identical suffix, so the
    browser's cache is otherwise left alone.

    Resolved through `illustrations.override_path_for_key(key, state_dir)`
    — the one place the state_dir/override-dirname join lives
    (T-v26-01-01) — never rebuilt here, and `ILLUSTRATION_OVERRIDE_DIRNAME`
    is never reached for directly. Wrapped in `try`/`except` so a vanished
    or unreadable file (a race with a concurrent upload, a permissions
    error) degrades to no cache buster rather than raising — the same
    never-raises posture `companion/app.py`'s `runway_images_available()`
    documents for its own per-request `os.path.isfile()` probe.
    """
    if not state_dir:
        return ""
    override_path = illustrations.override_path_for_key(key, state_dir)
    if not override_path:
        return ""
    try:
        mtime = int(os.stat(override_path).st_mtime)
    except OSError:
        return ""
    return "?v=%d" % mtime


def _lightbox_replace_form_html():
    """The replace-image control (originally quick task 260902-v26,
    relocated here by quick task 260903-btu): a plain, JavaScript-free
    upload form, wired to plan 02's `POST /illustration/{key}.png` route
    (`companion/app.py`'s `Handler._handle_illustration_replace()`),
    living inside the shared click-to-enlarge lightbox rather than under
    each grid card. Takes no arguments and is emitted exactly once per
    page by `_lightbox_html()` — there is no longer a per-card copy to
    parametrise.

    `action=""` is a real, present placeholder attribute, never omitted:
    `companion/static/panel-lookup.js` overwrites it on every trigger
    click with that card's own `_VIEW_PANEL_REPLACE_ACTION_ATTR` value,
    writing an existing attribute rather than creating one. With
    JavaScript unavailable, this placeholder means "submit to the
    current page's own URL", i.e. `POST /airlines` — a route this app's
    POST dispatch does not handle and answers with a 404. That is a
    clean, harmless degradation (no write to a wrong key, no
    unauthenticated path) and is deliberately accepted rather than
    engineered around, matching this codebase's existing JS-free-
    degradation posture (`list-filter.js`'s early return,
    `panel-lookup.js`'s own guards). No JavaScript submit logic exists
    anywhere here: this stays a real native multipart POST that
    navigates the browser away and closes the dialog by page reload.

    `accept="image/png"` below is a browser-side file-picker hint only,
    never trusted server-side: plan 02's route decides what an image is
    by parsing the real PNG header, and this attribute exists purely to
    save the developer scrolling past their photo library.

    Renders no revert/reset/restore-original control (D-04) — a
    deliberate scope decision, not an omission. The vendored original is
    never modified by this feature and stays recoverable (by deleting the
    override file), but no user-facing revert is in scope for this task.

    None of `REPLACE_LABEL_TEXT`, `REPLACE_BUTTON_TEXT`,
    `REPLACE_HINT_TEXT` or `REPLACE_INPUT_ID` interpolates any external
    value, so no `escape_html()` call is needed here — unlike the retired
    per-card version, nothing hostile can reach this function's output.

    quick task 260903-df3: this changed presentation only — a
    `LIGHTBOX_REPLACE_ZONE_CLASS` wrapper `<div>` around the label/hint/
    input/button (Option 2, "Framed action area") replaces the old
    cramped inline divider row. The form's own opening tag (class,
    `method`, `enctype`, `action=""`) and every existing child element's
    own attributes are byte-identical to before — the zone is a styling
    wrapper, not a markup or route change. The upload glyph is produced
    only via `layout.icon_html("icon-upload", ...)`; this module hand-rolls
    no glyph markup of its own.
    """
    icon_html = layout.icon_html("icon-upload", extra_class=REPLACE_ICON_CLASS)
    return (
        '<form class="%s" method="post" enctype="multipart/form-data" action="">'
        '<div class="%s">'
        "%s"
        '<label for="%s">%s</label>'
        '<p class="%s">%s</p>'
        '<input type="file" id="%s" name="image" accept="image/png" required>'
        '<button type="submit">%s</button>'
        "</div>"
        "</form>"
    ) % (
        LIGHTBOX_REPLACE_FORM_CLASS,
        LIGHTBOX_REPLACE_ZONE_CLASS,
        icon_html,
        REPLACE_INPUT_ID,
        REPLACE_LABEL_TEXT,
        REPLACE_HINT_CLASS,
        REPLACE_HINT_TEXT,
        REPLACE_INPUT_ID,
        REPLACE_BUTTON_TEXT,
    )


def _airline_card_html(index, airline_name, shapes, state_dir=None):
    """One `.airline-card` (06.6.4.1-UI-SPEC.md §7.1): an image pointing
    at the session-gated `/illustration/{key}.png` route, wrapped in a
    `.airline-card__zoom` click-to-enlarge trigger (quick task
    260902-tli), the airline's name, and one chip per fleet-type variant
    — the chips container is omitted entirely (not rendered empty) when
    `shapes` is empty. Every interpolated value — the key inside the
    URL, the name, each chip label, and the alt text — goes through
    `escape_html()` exactly once, at the point of interpolation
    (T-06.6.4.1-05). Returns the empty string (skips the card, never
    crashes) for an airline whose normalised key comes back falsy,
    mirroring `illustrations.target_filenames()`'s own documented skip
    discipline.

    `index` becomes the card's `data-filter-group` value (D-16/D-20):
    this page renders one representation per airline (no mobile-card
    pairing like History), but `companion/static/list-filter.js` counts
    distinct groups rather than raw elements, so every filterable card
    still needs its own group. `data-filter-text` carries the lower-cased
    airline name, escaped before interpolation into the attribute — the
    same discipline the old registry rows applied to their prefix value.

    `state_dir` (quick task 260902-v26, default `None`): threaded down
    from `render(ctx)` only to resolve `_illustration_cache_buster()`. It
    changes nothing else — the vendored-fallback image URL, with no
    override present, is byte-identical to what this function produced
    before this parameter existed. (Quick task 260903-btu: this
    parameter no longer also feeds a per-card replace form — the shared
    lightbox's single form is not built here at all.)
    """
    key = illustrations.normalise_airline_key(airline_name)
    if not key:
        return ""
    # Built once, interpolated into both the <img src> and the zoom
    # trigger's data-view-panel-src below (plus, since quick task
    # 260902-v26, the cache-busting suffix appended to both — see
    # _illustration_cache_buster()), so the two can never drift apart into
    # pointing at different images.
    image_url = "%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key))
    # This zoom trigger's own _VIEW_PANEL_REPLACE_ACTION_ATTR below
    # (quick task 260903-btu) deliberately uses this UN-busted image_url,
    # not busted_image_url — a query string on a POST target is
    # pointless and would make that attribute and data-view-panel-src
    # look gratuitously different for no reason. image_url is already
    # escaped once above; do not escape it again when interpolating it
    # below, which would double-encode.
    busted_image_url = image_url + _illustration_cache_buster(key, state_dir)
    image_html = (
        '<img class="airline-card__image" src="%s" '
        'width="%d" height="%d" '
        'loading="lazy" decoding="async" alt="%s">'
    ) % (
        busted_image_url,
        ILLUSTRATION_TARGET_WIDTH, ILLUSTRATION_TARGET_HEIGHT,
        escape_html(CARD_IMAGE_ALT_TEMPLATE % airline_name),
    )
    # quick task 260902-tli: wraps the image in a real <button> (not the
    # <img> itself) — this codebase's a11y discipline (the global
    # :focus-visible floor, aria-labelled icon buttons elsewhere) makes a
    # non-focusable click target the wrong choice, and panel-lookup.js's
    # click delegation walks ancestors from the event target, so a click
    # on the inner image still resolves to this button. The aria-label
    # deliberately overrides the inner image's alt for the button's own
    # accessible name, so a screen reader announces the action ("Enlarge
    # ... illustration"), not just the picture.
    zoom_html = (
        '<button type="button" class="airline-card__zoom" %s="%s" %s="%s" %s="%s" '
        'aria-label="%s">%s</button>'
    ) % (
        _VIEW_PANEL_SRC_ATTR, busted_image_url,
        _VIEW_PANEL_CAPTION_ATTR, escape_html(CARD_IMAGE_ALT_TEMPLATE % airline_name),
        _VIEW_PANEL_REPLACE_ACTION_ATTR, image_url,
        escape_html(ZOOM_LABEL_TEMPLATE % airline_name),
        image_html,
    )
    chips_html = ""
    if shapes:
        chips = "".join(
            '<span class="airline-card__chip">%s</span>' % escape_html(variant_chip_label(shape))
            for shape in shapes
        )
        chips_html = '<div class="airline-card__chips">%s</div>' % chips
    filter_text = escape_html(
        airline_name.lower() if isinstance(airline_name, str) else str(airline_name).lower())
    return (
        '<div class="airline-card" data-filter-text="%s" data-filter-group="%d">'
        "%s"
        '<p class="airline-card__name">%s</p>'
        "%s"
        "</div>"
    ) % (filter_text, index, zoom_html, escape_html(airline_name), chips_html)


def _gallery_grid_html(pairs, state_dir=None):
    """Wrap one `_airline_card_html()` card per `(airline_name, shapes)`
    pair in the `.illustration-grid` container (06.6.4.1-UI-SPEC.md
    §7.1, companion/static/style.css from plan 01). Skips (renders
    nothing for) any pair whose card comes back empty. `state_dir`
    (quick task 260902-v26, default `None`) is threaded straight through
    to every card — see `_airline_card_html()`'s own docstring.
    """
    cards = "".join(
        _airline_card_html(index, airline_name, shapes, state_dir)
        for index, (airline_name, shapes) in enumerate(pairs))
    return '<div class="illustration-grid">%s</div>' % cards


def _lightbox_html():
    """The single shared click-to-enlarge `<dialog>` (quick task
    260902-tli), emitted once per page — never once per card — by
    `render()`, only when at least one card actually carries a zoom
    trigger. Mirrors `history_page._lightbox_html()` element-for-element
    and class-for-class (same order, same three `lightbox__*` elements,
    same close-attribute button), with exactly three differences: this
    dialog also carries the `lightbox--wide` class (the enlarged
    illustration needs more room than History's 480px default); the note
    is this module's own `LIGHTBOX_NOTE`; and this dialog carries the
    replace form `_lightbox_replace_form_html()` returns, which History
    deliberately never renders (quick task 260903-btu).

    Element order inside the dialog: image, then caption, then note,
    then the replace form, then the Close button. Close stays last so
    the dismissal affordance is the stable bottom-most control and the
    tab order reads "look, act, dismiss" — `panel-lookup.js` finds the
    close button by attribute, not by position, so this order matters
    only to a human, never to the script.

    `companion/static/panel-lookup.js` writes the image src/alt, the
    caption text, and this form's `action` attribute on click; this
    function only emits the static note and the form's `action=""`
    placeholder, neither of which the script writes on page load — only
    on the next click.
    """
    return (
        '<dialog class="lightbox lightbox--wide" id="%s">'
        '<img class="lightbox__image" src="" alt="">'
        '<p class="lightbox__caption text-label mono"></p>'
        '<p class="lightbox__note text-body">%s</p>'
        "%s"
        '<button type="button" %s>Close</button>'
        "</dialog>"
    ) % (
        LIGHTBOX_DIALOG_ID, escape_html(LIGHTBOX_NOTE),
        _lightbox_replace_form_html(),
        _VIEW_PANEL_CLOSE_ATTR,
    )


# D-16 (06.6.4.1-UI-SPEC.md §7.2): the gallery's filter-bar copy, driven
# client-side by companion/static/list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract — the same script History's own
# _filter_bar_html() already consumes, no script change needed here.
# Unlike the retired diagnostics page, this gallery carries no read-only
# constraint, so the Clear control below is a real <button>, matching
# History's variant rather than the old Airlines page's anchor-link one.
_FILTER_INPUT_ID = "airlines-gallery-filter-input"
# Phase 14 (14-02-PLAN.md Task 1) reworded this label in place: the
# search behaviour genuinely broadens once gap cards are filterable by
# callsign/prefix too (14-UI-SPEC.md Autonomous Decision #2).
_FILTER_LABEL_TEXT = "Filter by airline or callsign"
_FILTER_EMPTY_HEADING = "No matching airlines"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d airlines.")


def _filter_bar_html(total):
    """D-16's filter bar over the gallery — History's `<button
    type="button" data-filter-clear>Clear</button>` variant
    (06.6.4.1-UI-SPEC.md §7.2), not the old read-only Airlines page's
    `<a href="#...">` variant: that anchor existed only because the old
    diagnostics page was forbidden any button element (D-16, retired),
    and this gallery carries no such constraint. Entirely inert without
    JS — `companion/static/list-filter.js`'s own early-return guard
    means the full unfiltered card grid underneath stays completely
    usable if the script never loads.
    """
    count_text = "%d of %d shown" % (total, total)
    empty_body = _FILTER_EMPTY_BODY_TEMPLATE % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        '<input type="search" id="%s" data-filter-input>'
        "</div>"
        '<span class="filter-bar__count" data-filter-count>%s</span>'
        '<button type="button" data-filter-clear>Clear</button>'
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(_FILTER_LABEL_TEXT),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        escape_html(count_text),
        escape_html(_FILTER_EMPTY_HEADING),
        escape_html(empty_body),
    )


# ---------------------------------------------------------------------
# Phase 13 (13-04-PLAN.md Task 1): the conditional "resolve an
# unidentified flight" section (D-03, D-10 through D-13).
# ---------------------------------------------------------------------


def unresolved_row_for_prefix(state_dir, prefix):
    """D-11's whole membership test: is `prefix` a real, live member of
    the unresolved-callsign-prefix registry right now? Public because
    `companion/app.py`'s POST handler (plan 13-06) imports and re-runs
    this exact function as its own D-11 check, rather than
    re-implementing it — the read path (this function) and the write
    path can never diverge.

    This is validate-then-join over a closed, server-written set — the
    identical shape `illustrations.py`'s `_serve_illustration_image()`
    already uses against its own closed filename set — applied here to
    the unresolved-prefix registry, which is server-written from
    genuinely detected ADS-B traffic rather than a fixed table. Every
    displayed value comes from the tuple this function returns, never
    from the caller's own raw query-string value (D-12).

    WR-04 fix: `prefix` is normalised through
    `manual_resolutions.normalise_prefix()` (strip + upper-case + shape
    check) right here, at this function's own boundary, rather than by
    each caller separately — this is the single D-11 membership test the
    render path and the write path both share, so normalising anywhere
    else would risk the two answering differently for the same input
    again. Callers must pass the raw value through unmodified.

    Reads through `poll_loop.load_poll_state(state_dir)` — never a direct
    file open, never a re-derivation of `server/plane/enrich.py`'s own
    registry-writer's shape logic — mirroring
    `health_page.unresolved_rows()`'s exact field-handling discipline,
    just for one prefix instead of every row. Returns `None` unless:
    `prefix` normalises to a real 3-letter prefix
    (`manual_resolutions.normalise_prefix()`), the `unresolved_prefixes`
    value is a dict, the entry for it is itself a dict, and its `count`
    is an `int` that is not a `bool`. Otherwise returns the five-tuple
    `(prefix, count, first_seen, last_seen, example_callsign)` — `prefix`
    here is the NORMALISED value, not necessarily byte-identical to the
    argument — with the last three defaulting to `""`. Never raises — a
    missing or unreadable poll state, or a hand-edited malformed entry,
    yields `None` rather than crashing a page render.
    """
    prefix = manual_resolutions.normalise_prefix(prefix)
    if prefix is None:
        return None
    state = poll_loop.load_poll_state(state_dir)
    registry = state.get("unresolved_prefixes")
    if not isinstance(registry, dict):
        return None
    entry = registry.get(prefix)
    if not isinstance(entry, dict):
        return None
    count = entry.get("count")
    if not isinstance(count, int) or isinstance(count, bool):
        return None
    return (
        prefix,
        count,
        entry.get("first_seen") or "",
        entry.get("last_seen") or "",
        entry.get("example_callsign") or "",
    )


def _resolve_context_html(row, now, id_suffix=""):
    """The five-row `<dl>` sighting-context block (its class is
    RESOLVE_CONTEXT_CLASS) shared by Step A and Step B (D-12), and now
    also by the dialog's static copy (14-UI-SPEC.md's Component
    Inventory — one definition, two call sites): one `dt`/`dd` pair per
    `RESOLVE_CONTEXT_LABELS` entry, each `<dd>` additionally carrying
    its own hook class from `RESOLVE_CONTEXT_DD_CLASSES` in both call
    modes, so the dialog's copy has stable JS hooks (plan 14-05) and the
    two copies stay structurally identical.

    `row=None` (the dialog's own call) renders five empty `<dd>`s — the
    placeholder copy `panel-lookup.js` fills at click time; `now` may
    then safely also be `None`, since `layout.concise_timestamp_html()`
    short-circuits on a falsy timestamp before ever touching `now`.

    `id_suffix` is accepted for call-shape parity with the other three
    shared rendering functions this module now has (the resolve-name
    form, the resolve-upload form, the manual-delete form, below); this
    particular `<dl>` emits no id-bearing child in either mode, so the
    parameter has no effect on this function's own output today.

    First seen/Last seen render through
    `layout.concise_timestamp_html(value, now, fallback="")`, whose
    return value is already-safe markup and is interpolated verbatim,
    never re-escaped — the same discipline
    `health_page._registry_row_html()` documents for its own identical
    call. Every other value (the prefix, the count, the example
    callsign) goes through `escape_html()` exactly once.
    """
    del id_suffix  # accepted for signature parity only — see docstring.
    if row is None:
        prefix, count, first_seen, last_seen, example_callsign = "", "", "", "", ""
    else:
        prefix, count, first_seen, last_seen, example_callsign = row
    first_seen_html = layout.concise_timestamp_html(first_seen, now, fallback="")
    last_seen_html = layout.concise_timestamp_html(last_seen, now, fallback="")
    pairs = (
        ('<dd class="%s text-body mono">%s</dd>' % (
            RESOLVE_CONTEXT_DD_CLASSES[0], escape_html(prefix))),
        ('<dd class="%s text-body">%s</dd>' % (
            RESOLVE_CONTEXT_DD_CLASSES[1], first_seen_html)),
        ('<dd class="%s text-body">%s</dd>' % (
            RESOLVE_CONTEXT_DD_CLASSES[2], last_seen_html)),
        ('<dd class="%s text-body">%s</dd>' % (
            RESOLVE_CONTEXT_DD_CLASSES[3], escape_html(count))),
        ('<dd class="%s text-body mono">%s</dd>' % (
            RESOLVE_CONTEXT_DD_CLASSES[4], escape_html(example_callsign))),
    )
    items = "".join(
        '<dt class="text-label">%s</dt>%s' % (escape_html(label), dd)
        for label, dd in zip(RESOLVE_CONTEXT_LABELS, pairs)
    )
    return '<dl class="%s">%s</dl>' % (RESOLVE_CONTEXT_CLASS, items)


def _known_airlines_datalist_html(id_suffix=""):
    """D-13's whole mechanism, and it is native: a `<datalist>` offering
    one `<option>` per `illustrations.target_airline_names()` (27 today),
    each `value` escaped exactly once. Choosing a suggestion is what
    guarantees the slug derived downstream from the stored name lands on
    art the fallback ladder already ships; typing anything else stays
    available for a genuinely new carrier. No script is involved and
    none may be added.

    `id_suffix` (Phase 14, 14-02-PLAN.md Task 2): appended to
    `MANUAL_DATALIST_ID` so the no-JS fallback's copy (`id_suffix=""`,
    byte-identical to Phase 13) and the dialog's copy
    (`id_suffix="-dialog"`) never collide when both render at once
    (14-UI-SPEC.md's "why two ids, not one").
    """
    options = "".join(
        '<option value="%s">' % escape_html(name)
        for name in illustrations.target_airline_names()
    )
    return '<datalist id="%s">%s</datalist>' % (MANUAL_DATALIST_ID + id_suffix, options)


def _resolve_name_form_html(prefix_value, id_suffix):
    """Step A's name-entry form (D-11/D-12/D-13) — one definition, two
    call sites (14-UI-SPEC.md's Component Inventory, Claude's
    Discretion #1): `_resolve_section_html()` (the no-JS fallback) calls
    this with the real prefix and `id_suffix=""` — every emitted id is
    then byte-identical to what Phase 13's own inline block produced,
    so no existing `<label for>` association or check breaks. The
    dialog (`_lightbox_html()`) calls this with `prefix_value=""` and
    `id_suffix="-dialog"` — `panel-lookup.js` fills the hidden prefix
    input's own `.value` at click time.

    `id_suffix` is appended to `MANUAL_NAME_INPUT_ID` (in both the `id`
    and `for` positions) and threaded into `_known_airlines_datalist_
    html()` (the `id`/`list` positions), so the two calls' ids never
    collide inside the same DOM when the dialog and the fallback
    section render simultaneously.

    `prefix_value` interpolates through `escape_html()` exactly once,
    into the hidden `prefix` input's `value` — the dialog's own call
    passes `""` here since the script overwrites that value at click
    time, exactly like `_lightbox_replace_form_html()`'s own `action=""`
    placeholder discipline.

    The outer `<form>` carries `LIGHTBOX_RESOLVE_NAME_CLASS`
    (`lightbox__resolve-name`) in both calls — a shared function cannot
    render two different wrapper tags for the same output, and the
    no-JS fallback simply carries a spacing class style.css only ever
    selects from inside `.lightbox` (14-UI-SPEC.md's Component
    Inventory "New CSS" table).
    """
    name_input_id = MANUAL_NAME_INPUT_ID + id_suffix
    datalist_html = _known_airlines_datalist_html(id_suffix)
    name_field = (
        '<div class="resolve-name-field">'
        '<label for="%s">%s</label>'
        '<input type="text" id="%s" name="airline_name" list="%s" '
        'maxlength="100" required autocomplete="off" autofocus>'
        "%s"
        '<p class="text-label section-caption">%s</p>'
        "</div>"
    ) % (
        name_input_id, NAME_LABEL_TEXT,
        name_input_id, MANUAL_DATALIST_ID + id_suffix,
        datalist_html,
        NAME_HINT_TEXT,
    )
    return (
        '<form class="%s" method="post" action="%s">'
        '<input type="hidden" name="prefix" value="%s">'
        "%s"
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        LIGHTBOX_RESOLVE_NAME_CLASS, RESOLVE_ROUTE,
        escape_html(prefix_value),
        name_field,
        SAVE_BUTTON_TEXT,
    )


def _resolve_upload_form_html(action, id_suffix):
    """Step B's upload-zone form (D-11/D-12/D-13) — one definition, two
    call sites: `_resolve_section_html()` (the no-JS fallback) calls
    this with the real `/illustration/{key}.png` action and
    `id_suffix=""` (existing id `manual-illustration-input` unchanged).
    The dialog calls this with `action=""` and `id_suffix="-dialog"`
    (new id `manual-illustration-input-dialog`) — `panel-lookup.js`
    overwrites `action` via `setAttribute`, exactly like the existing
    replace form.

    `action=""` is a real, present placeholder attribute on the
    dialog's call, never omitted — the same rule `_lightbox_replace_
    form_html()`'s own docstring states, for the same reason (the
    script overwrites an existing attribute rather than creating one).

    The outer wrapper stays `RESOLVE_UPLOAD_ZONE_CLASS`
    (`resolve-upload-zone`), already generic and already reused
    byte-identical from Phase 13 — no `lightbox__*` class is added
    here (unlike the resolve-name and manual-delete forms): this div's
    own spacing is `.resolve-upload-zone`'s existing rule, shared
    verbatim across all three consumers per 14-UI-SPEC.md's Component
    Inventory.
    """
    upload_input_id = MANUAL_UPLOAD_INPUT_ID + id_suffix
    icon_html = layout.icon_html("icon-upload", extra_class=REPLACE_ICON_CLASS)
    return (
        '<div class="%s">'
        "%s"
        '<label for="%s">Choose an image</label>'
        '<p class="%s">%s</p>'
        '<form method="post" enctype="multipart/form-data" action="%s">'
        '<input type="file" id="%s" name="image" accept="image/png" required>'
        '<button type="submit">%s</button>'
        "</form>"
        "</div>"
    ) % (
        RESOLVE_UPLOAD_ZONE_CLASS,
        icon_html,
        upload_input_id,
        REPLACE_HINT_CLASS, REPLACE_HINT_TEXT,
        action,
        upload_input_id,
        REPLACE_BUTTON_TEXT,
    )


def _manual_delete_form_html(action):
    """The shared delete form (D-09 amendment, 2026-09-06) — one
    definition, two call sites: `_resolve_section_html()`'s own two
    entry-bearing branches (Step B, already-resolved) call this with
    the real `_manual_delete_action(prefix)` URL; the dialog calls this
    with `action=""`, and `panel-lookup.js` overwrites it via
    `setAttribute`, exactly like the existing replace form.

    Deliberately carries **no** `id_suffix` parameter, unlike the
    resolve-name and resolve-upload forms above: its output names no
    id at all — no `<label for>`, no `<input id>`,
    no `<datalist>` — nothing that HTML requires to be document-unique,
    so two copies of this exact markup can coexist on the page (dialog
    + fallback) with zero collision risk. A future editor must not "fix"
    this asymmetry by adding a suffix parameter it does not need
    (14-UI-SPEC.md's Component Inventory states this reasoning
    explicitly).
    """
    return (
        '<form class="%s" method="post" action="%s">'
        '<p class="text-label section-caption">%s</p>'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (LIGHTBOX_DELETE_CLASS, action, MANUAL_DELETE_CAPTION, DELETE_BUTTON_TEXT)


def _resolve_section_html(ctx):
    """The conditional resolve section (D-03, D-10 through D-13):
    `""` when `ctx.get("resolve_prefix")` is falsy, otherwise one of the
    server-derived states below. Every branch reads `state_dir`/`now`
    from `ctx` but decides which state to render from server-side data
    alone (`unresolved_row_for_prefix()`,
    `manual_resolutions.load_manual_resolutions()`,
    `illustrations.resolved_illustration_path()`) — never from the raw
    `resolve_prefix` query-string value once past the first membership
    check (D-12).

    Its markup now comes from the four shared rendering functions above
    — the resolve-name form, the resolve-upload form, the
    sighting-context block and the manual-delete form — this function
    (the no-JS fallback) is their first call site; the shared dialog
    (`_lightbox_html()`) is their second (14-UI-SPEC.md's Component
    Inventory, Claude's Discretion #1). This function's own
    four-branch derivation logic (the CR-02 fallthrough, the `prefix is
    None` guard, the corrupt-key guard) is unchanged from Phase 13 —
    only the markup emission moved into those shared functions.

    CR-02 fix: `unresolved_row_for_prefix()` returning `None` no longer
    means "render the stale sentence and stop". D-14's
    `enrich.clear_resolved_unresolved_prefix()` deletes a prefix from the
    LIVE gap registry on the very next poll cycle after it resolves —
    including via a manual entry Step A itself just saved — so the gap
    being gone is the *expected*, immediate outcome of a successful
    Step A, not evidence there is nothing left to do. Losing the live
    row must not also lose reachability of Step B (upload artwork) or of
    D-07's delete-and-re-add correction path. When the row is absent,
    this function instead re-validates `resolve_prefix` on its own
    (`manual_resolutions.normalise_prefix()` — the identical D-11 shape
    gate `unresolved_row_for_prefix()` itself applies, so this remains
    validate-then-join over server-side state, never a query-string
    value used unchecked) and falls through to the same manual-registry-
    driven Step A/Step B/already-done derivation used when the row is
    still live — the only difference is there is no sighting context
    left to show (the gap entry that carried first-seen/last-seen/count
    is gone), so `context_html` is the empty string on this path rather
    than `_resolve_context_html()`'s `<dl>`. A prefix with neither a live
    gap NOR a manual entry still renders the stale sentence — there is
    genuinely nothing to resolve.

    D-09 amendment (2026-09-06): the shared manual-delete form renders
    in exactly the two branches below that have reached an `entry`
    (Step B, already-resolved), and in neither of the two entry-less
    branches
    (stale/invalid, Step A) — the same rule the dialog encodes via
    `manual` being `active`/`superseded`, i.e. whenever an entry exists.
    One rule, two render sites, not two rules.
    """
    prefix_raw = ctx.get("resolve_prefix")
    if not prefix_raw:
        return ""
    state_dir = ctx.get("state_dir")
    now = ctx.get("now")
    back_link = '<a class="text-label" href="/health">%s</a>' % RESOLVE_BACK_LINK_TEXT

    row = unresolved_row_for_prefix(state_dir, prefix_raw)
    if row is not None:
        prefix = row[0]
        context_html = _resolve_context_html(row, now)
    else:
        prefix = manual_resolutions.normalise_prefix(prefix_raw)
        context_html = ""

    if prefix is None:
        body = '<p class="text-body">%s</p>' % RESOLVE_STALE_BODY
        return '<div class="page-section">%s%s</div>' % (back_link, body)

    escaped_prefix = escape_html(prefix)

    registry = manual_resolutions.load_manual_resolutions(state_dir)
    entry = registry.get(prefix)

    if entry is None:
        if row is None:
            # No live gap AND no manual entry for this prefix: genuinely
            # nothing to resolve here.
            body = '<p class="text-body">%s</p>' % RESOLVE_STALE_BODY
            return '<div class="page-section">%s%s</div>' % (back_link, body)
        # Step A — name not yet saved. No entry exists yet, so no
        # delete form (D-09 amendment).
        heading = '<h2 class="text-heading">%s</h2>' % RESOLVE_HEADING
        caption = '<p class="text-label section-caption">%s</p>' % (
            RESOLVE_CAPTION_TEMPLATE % escaped_prefix)
        form = _resolve_name_form_html(prefix, "")
        return '<div class="page-section">%s%s%s%s%s</div>' % (
            back_link, heading, caption, context_html, form)

    # Entry present. Recompute the key server-side from the *stored* name
    # — never take a key from the query string, and never derive a slug
    # locally (this module owns no slug logic of its own).
    airline_name = entry.get("airline_name")
    key = manual_resolutions.illustration_key_for_name(airline_name)
    if not key:
        # A stored entry whose name no longer slugs is a corrupt-file
        # case that must not render a form.
        body = '<p class="text-body">%s</p>' % RESOLVE_STALE_BODY
        return '<div class="page-section">%s%s</div>' % (back_link, body)

    escaped_name = escape_html(airline_name)
    heading = '<h2 class="text-heading">%s</h2>' % (STEP_B_HEADING_TEMPLATE % escaped_name)
    # D-09 amendment: an entry exists past this point in every remaining
    # branch, so the delete form renders in both of them.
    delete_form = _manual_delete_form_html(_manual_delete_action(prefix))

    if illustrations.resolved_illustration_path(key, state_dir) is None:
        # Step B — name already saved, no artwork exists yet.
        caption = '<p class="text-label section-caption">%s</p>' % STEP_B_CAPTION
        upload_action = "%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key))
        upload_zone = _resolve_upload_form_html(upload_action, "")
        skip_link = '<a class="text-label" href="%s">%s</a>' % (
            AIRLINES_ROUTE, STEP_B_SKIP_TEXT)
        return '<div class="page-section">%s%s%s%s%s%s%s</div>' % (
            back_link, heading, caption, context_html, upload_zone, skip_link, delete_form)

    # Already resolved: a bookmark or a Back press landed on a prefix
    # still listed as a gap, but a manual entry already names an airline
    # that has artwork. No controls except delete.
    body = '<p class="text-body">%s</p>' % (RESOLVE_ALREADY_DONE_TEMPLATE % escaped_name)
    return '<div class="page-section">%s%s%s%s</div>' % (back_link, heading, body, delete_form)


# ---------------------------------------------------------------------
# Phase 13 (13-04-PLAN.md Task 2): the always-present manual-resolutions
# management list (D-06, D-07, D-08).
# ---------------------------------------------------------------------


def _manual_delete_action(prefix):
    """The delete form's `action` attribute for `prefix`, built once here
    so the desktop `<tr>` and the mobile `<li>` can never diverge into
    building two different strings for the same row.
    """
    return "%s%s%s" % (MANUAL_DELETE_ROUTE_PREFIX, escape_html(prefix), MANUAL_DELETE_ROUTE_SUFFIX)


def _manual_superseded_marker_html():
    """The `<span class="manual-resolution__status--superseded">`
    marker, carrying text (`SUPERSEDED_MARKER_TEXT`) and a `title`
    explanation (`SUPERSEDED_MARKER_TITLE`) — never colour alone, this
    app's Label-voice convention and the UI-SPEC's no-colour-only-signal
    rule.
    """
    return '<span class="%s" title="%s">%s</span>' % (
        SUPERSEDED_STATUS_CLASS,
        escape_html(SUPERSEDED_MARKER_TITLE),
        escape_html(SUPERSEDED_MARKER_TEXT),
    )


def _manual_add_artwork_link_html(prefix):
    """CR-02's management-list entry point into Step B: a plain `<a>`
    into the same `?resolve={prefix}` URL Health's per-row deep link
    (D-10) already uses. `_resolve_section_html()`'s own CR-02 fix
    renders Step B for a manual entry with no artwork yet regardless of
    whether `prefix` is still a live gap-registry member, so this link
    stays live even after D-14 clears the gap. No illustration key
    travels in this URL — only the prefix, exactly like every other
    resolve deep link in this app.
    """
    return '<a href="%s?%s=%s">%s</a>' % (
        AIRLINES_ROUTE, RESOLVE_QUERY_PARAM, escape_html(prefix), ADD_ARTWORK_LINK_TEXT)


def _manual_resolution_rows(state_dir, registry):
    """`(prefix, airline_name, created_at, superseded, needs_artwork)`
    tuples from an already-loaded `registry` dict, via
    `manual_resolutions.entry_rows()` (prefix-ascending).

    `superseded` is set from `enrich.static_airline_name_for_prefix(prefix)`
    — D-06's oracle: the static table has caught up, so its entry wins at
    runtime and the operator's uploaded art is no longer reachable under
    this prefix. Nothing here mutates the registry — flagging is the
    whole of D-06's UI obligation; repairing is delete-and-re-add.

    `needs_artwork` (CR-02) is `True` for an ACTIVE (non-superseded)
    entry whose stored name's illustration key currently has no
    resolved artwork (`illustrations.resolved_illustration_path()`
    returns `None`) — this is what drives the per-row "Add artwork" link
    (`_manual_add_artwork_link_html()`), the management list's own entry
    point into Step B now that a resolved prefix's live-gap deep link
    (D-10/Health) can be gone (D-14) before the operator ever uploads
    anything. Always `False` for a superseded entry (the built-in table
    already owns that prefix; uploading under the operator's own name
    would not change what the frame displays) and for a name whose key
    no longer slugs (corrupt-file defence, mirrors
    `_resolve_section_html()`'s own guard).
    """
    rows = []
    for prefix, airline_name, created_at in manual_resolutions.entry_rows(registry):
        superseded = bool(enrich.static_airline_name_for_prefix(prefix))
        needs_artwork = False
        if not superseded:
            key = manual_resolutions.illustration_key_for_name(airline_name)
            needs_artwork = bool(key) and illustrations.resolved_illustration_path(key, state_dir) is None
        rows.append((prefix, airline_name, created_at, superseded, needs_artwork))
    return rows


def _manual_resolution_row_html(index, prefix, airline_name, created_at, superseded, needs_artwork, now):
    """One `<tr>` for the management table: `row`/`row-alt` by index
    parity, prefix/name/added/status/delete cells. `created_at` renders
    through `layout.concise_timestamp_html()`, interpolated verbatim as
    already-safe markup — never re-escaped, matching this module's own
    `_resolve_context_html()` discipline. The status cell holds exactly
    one of: nothing (an active entry with artwork — the normal state
    gets no visual noise, matching `layout.card_status_class()`'s own
    documented "absence is the signal" discipline), the superseded
    marker, or (CR-02) the "Add artwork" link for an active entry still
    missing it.
    """
    row_class = "row-alt" if index % 2 else "row"
    if superseded:
        status_html = _manual_superseded_marker_html()
    elif needs_artwork:
        status_html = _manual_add_artwork_link_html(prefix)
    else:
        status_html = ""
    delete_form = (
        '<form method="post" action="%s">'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (_manual_delete_action(prefix), DELETE_BUTTON_TEXT)
    cells = (
        '<td class="mono">%s</td>' % escape_html(prefix),
        "<td>%s</td>" % escape_html(airline_name),
        "<td>%s</td>" % layout.concise_timestamp_html(created_at, now, fallback=""),
        "<td>%s</td>" % status_html,
        "<td>%s</td>" % delete_form,
    )
    return '<tr class="%s">%s</tr>' % (row_class, "".join(cells))


def _manual_resolution_table_html(rows, now):
    """The management table, hand-rolled to match
    `health_page._registry_table_html()`'s own `.data-table-wrap`/
    `.data-table`/`thead`/`tbody` structure for visual consistency.
    """
    header_cells = "".join(
        "<th>%s</th>" % escape_html(h) for h in MANUAL_RESOLUTION_HEADERS)
    body_rows = [
        _manual_resolution_row_html(index, prefix, airline_name, created_at, superseded, needs_artwork, now)
        for index, (prefix, airline_name, created_at, superseded, needs_artwork) in enumerate(rows)
    ]
    return (
        '<div class="data-table-wrap">'
        '<table class="data-table">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (header_cells, "".join(body_rows))


def _manual_resolution_cards_html(rows, now):
    """The mobile `.data-cards` representation of the management list —
    one `<li class="data-card">` per row, no `data-filter-text`/
    `data-filter-group` attributes at all: this list has no filter bar
    (UI-SPEC Autonomous Decision 3), and `list-filter.js`'s distinct-
    group counting must not be invited to see a list it does not drive.
    Returns `""` for an empty list, matching `_manual_resolution_table_
    html()`'s own no-chrome-with-no-data rule.
    """
    if not rows:
        return ""
    items = []
    for prefix, airline_name, created_at, superseded, needs_artwork in rows:
        if superseded:
            marker_html = _manual_superseded_marker_html()
        elif needs_artwork:
            marker_html = _manual_add_artwork_link_html(prefix)
        else:
            marker_html = ""
        primary = (
            '<div class="data-card__primary">'
            '<span class="cell-primary mono">%s</span>'
            '<span class="data-card__value">%s</span>'
            "%s"
            "</div>"
        ) % (escape_html(prefix), escape_html(airline_name), marker_html)
        secondary = (
            '<div class="data-card__secondary">'
            '<span class="data-card__label">%s</span>%s'
            "</div>"
        ) % (
            escape_html(MANUAL_RESOLUTION_HEADERS[2]),
            layout.concise_timestamp_html(created_at, now, fallback=""),
        )
        delete_form = (
            '<form method="post" action="%s">'
            '<button type="submit">%s</button>'
            "</form>"
        ) % (_manual_delete_action(prefix), DELETE_BUTTON_TEXT)
        items.append('<li class="data-card">%s%s%s</li>' % (primary, secondary, delete_form))
    return '<ul class="data-cards">%s</ul>' % "".join(items)


def _manual_resolutions_section_html(ctx):
    """The always-present manual-resolutions management list (D-07): its
    own `.page-section` card, heading, caption, then either
    `layout.empty_state()` or the table/card-list pairing, plus — only
    when at least one row is superseded — the trailing explanatory
    caption. UI-SPEC Autonomous Decision 2: this list sits at the
    bottom of the page (after the lightbox) because it is reference/
    cleanup material, not the page's purpose.

    Reads the registry from `ctx.get("manual_resolutions")` when
    present (plan 13-06 threads this in), falling back to
    `manual_resolutions.load_manual_resolutions(state_dir)` when the key
    is absent and `state_dir` is truthy, and to `{}` otherwise — so
    `render({})` still works.
    """
    state_dir = ctx.get("state_dir")
    now = ctx.get("now")
    registry = ctx.get("manual_resolutions")
    if registry is None:
        registry = manual_resolutions.load_manual_resolutions(state_dir) if state_dir else {}

    heading = '<h2 class="text-heading">%s</h2>' % escape_html(MANUAL_SECTION_HEADING)
    caption = '<p class="text-label section-caption">%s</p>' % escape_html(MANUAL_SECTION_CAPTION)

    rows = _manual_resolution_rows(state_dir, registry)
    if not rows:
        body = layout.empty_state(MANUAL_EMPTY_HEADING, MANUAL_EMPTY_BODY)
        return '<div class="page-section">%s%s%s</div>' % (heading, caption, body)

    # Cards render before the table — style.css's `.data-cards ~
    # .data-table-wrap` sibling-combinator toggle (the same mechanism
    # health_page._registry_section() documents for itself) depends on
    # this exact DOM order; do not reorder these two calls.
    cards_html = _manual_resolution_cards_html(rows, now)
    table_html = _manual_resolution_table_html(rows, now)
    superseded_caption = ""
    if any(row[3] for row in rows):
        superseded_caption = '<p class="text-label section-caption">%s</p>' % escape_html(SUPERSEDED_CAPTION)
    return '<div class="page-section">%s%s%s%s%s</div>' % (
        heading, caption, cards_html, table_html, superseded_caption)


def render(ctx):
    """The Airlines page (D-13 through D-17, extended by phase 13's
    D-03/D-06/D-07/D-10 through D-13): the page header, the conditional
    resolve section, the D-16 filter bar, one card per airline in
    `illustrations.target_variants_by_airline()` order, the shared
    click-to-enlarge lightbox dialog (quick task 260902-tli), then the
    always-present manual-resolutions management list (D-07). `ctx` is
    accepted for call-site parity with every other page module's
    `render(ctx)` signature.

    Since quick task 260902-v26 this reads `state_dir` (used to resolve
    each card's illustration-replace cache buster, see
    `_illustration_cache_buster()`, and by both new phase-13 sections
    below as their own state-dir source). Phase 13 (13-04-PLAN.md) adds
    three more `ctx.get()` reads: `resolve_prefix` (the `?resolve=
    {prefix}` query value, presence-gating `_resolve_section_html()`),
    `now` (threaded to every rendered timestamp in both new sections),
    and `manual_resolutions` (an already-loaded registry dict,
    `_manual_resolutions_section_html()`'s preferred source — plan
    13-06 threads this in; absent, it falls back to loading fresh from
    `state_dir`). Every one of these four keys is read with `ctx.get()`,
    never `ctx[...]` — `companion/test_view_pages.py`'s existing
    `render({})` call with a literal empty dict must keep rendering the
    unchanged gallery, no resolve section, and the management list's own
    empty state. This page still opens no database.

    The filter bar and the lightbox dialog both render only when there
    is at least one card — this codebase's consistent "no chrome with no
    data" rule — though with a static curated list that branch is
    unreachable today; it stays a genuine guard, not a claim that the
    list can ever be empty. The management list has its own,
    independent empty state (`layout.empty_state()`) and is never
    gated on the gallery having any cards — UI-SPEC Autonomous Decision
    2: it is reference/cleanup material, not the page's purpose, so it
    sits last, below the gallery.
    """
    # ctx.get(), never ctx["state_dir"]: companion/test_view_pages.py:1365
    # calls render({}) with a literal empty dict, and every other caller
    # of this page (companion/app.py's page_context()) does supply
    # state_dir, so this must stay tolerant of both.
    state_dir = ctx.get("state_dir")
    resolve_html = _resolve_section_html(ctx)
    pairs = illustrations.target_variants_by_airline()
    filter_html = _filter_bar_html(len(pairs)) if pairs else ""
    lightbox_html = _lightbox_html() if pairs else ""
    manual_section_html = _manual_resolutions_section_html(ctx)
    return (
        layout.page_header("Airlines", purpose=GALLERY_PURPOSE_TEXT)
        + resolve_html
        + filter_html
        + _gallery_grid_html(pairs, state_dir)
        + lightbox_html
        + manual_section_html
    )
