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
LIGHTBOX_ARIA_LABEL = "Airline illustration"

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

# Phase 14 (14-04-PLAN.md, D-06): the gap block's threshold and cap —
# both locked numeric values from D-06's own text, not a discretion
# call. A prefix must be seen at least GAP_BLOCK_THRESHOLD times before
# it earns a gap card at all, and at most GAP_BLOCK_CAP gap cards ever
# render, head of grid, regardless of how many prefixes clear the
# threshold (see _gap_overflow_html() for what happens to the rest).
GAP_BLOCK_THRESHOLD = 3
GAP_BLOCK_CAP = 12

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

# Phase 13 (13-04-PLAN.md Task 2, D-06/D-07). Phase 14 plan 14-06 Task 2
# retired the standalone management table these constants used to serve
# (MANUAL_SECTION_HEADING/_CAPTION, MANUAL_EMPTY_HEADING/_BODY,
# MANUAL_RESOLUTION_HEADERS, ADD_ARTWORK_LINK_TEXT,
# SUPERSEDED_MARKER_TITLE, SUPERSEDED_CAPTION, SUPERSEDED_STATUS_CLASS —
# all deleted as genuinely unreferenced once that table's six rendering
# functions were). SUPERSEDED_MARKER_TEXT and DELETE_BUTTON_TEXT survive
# below: the chip (`_airline_card_html()`) and the shared delete form
# (`_manual_delete_form_html()`) still consume them.
SUPERSEDED_MARKER_TEXT = "Superseded"
DELETE_BUTTON_TEXT = "Delete"

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


def _airline_card_html(index, airline_name, shapes, state_dir=None, manual_info=None):
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

    `manual_info` (Phase 14, 14-06-PLAN.md Task 1, D-08/D-10/D-12
    fallback reachability): either `None` (today's plain curated card —
    byte-identical output to before this parameter existed) or the
    three-tuple `(prefix, superseded, needs_artwork)` — the exact
    trailing three fields of one `_manual_resolution_rows()` row, sliced
    by the caller (`render()`) and consumed here, never recomputed
    (RESEARCH.md Pitfall 6). When present: the trigger becomes a real
    `<a href="/airlines?resolve={prefix}">` (the trigger-tag
    generalisation, UI-SPEC's Page Composition), the chip list gains
    "Resolved by hand"/"Superseded", `data-filter-text` gains the
    matching invisible token, and the full `data-view-panel-*`
    attribute vocabulary is populated per UI-SPEC's Interaction
    Contract. A superseded card's `mode`/image always reflect the
    BUILT-IN airline's own current state (UI-SPEC Autonomous Decision
    3) — the built-in name's own single provenance lookup below (see
    that call site) exists purely to interpolate the built-in name into
    `MANUAL_SUPERSEDED_NOTE_TEMPLATE`, never to re-derive the
    `superseded` boolean itself.
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
    # Phase 14 (14-06-PLAN.md Task 1): derive every manual-info-dependent
    # attribute value once, here, from the sliced (prefix, superseded,
    # needs_artwork) triple alone — never re-derived from a second call
    # to enrich/illustrations beyond the one static-name lookup below
    # (RESEARCH.md Pitfall 6).
    has_manual = manual_info is not None
    prefix = superseded = needs_artwork = None
    if has_manual:
        prefix, superseded, needs_artwork = manual_info

    mode = (
        _VIEW_PANEL_MODE_NEEDS_ARTWORK if (has_manual and needs_artwork)
        else _VIEW_PANEL_MODE_ART)
    # Phase 18 (audit, high): a manually-resolved airline with no artwork
    # yet used to emit an <img> whose src 404s — the browser painted the
    # alt text as a broken, link-styled image. Render the same dashed
    # placeholder a gap card uses instead, and hand the dialog an empty
    # src so it hides its image too (panel-lookup.js's own empty-src
    # branch).
    if mode == _VIEW_PANEL_MODE_NEEDS_ARTWORK:
        image_html = '<span class="airline-card__placeholder" aria-hidden="true"></span>'
        busted_image_url = ""
    if has_manual:
        manual_value = (
            _VIEW_PANEL_MANUAL_SUPERSEDED if superseded else _VIEW_PANEL_MANUAL_ACTIVE)
    else:
        manual_value = ""
    resolve_prefix_value = escape_html(prefix) if has_manual else ""

    heading_value = ""
    upload_action_value = ""
    if mode == _VIEW_PANEL_MODE_NEEDS_ARTWORK:
        heading_value = STEP_B_HEADING_TEMPLATE % escape_html(airline_name)
        upload_action_value = "%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key))

    delete_action_value = _manual_delete_action(prefix) if has_manual else ""

    manual_note_value = ""
    if has_manual and superseded:
        # This function's one sanctioned provenance lookup — fetching the
        # built-in airline's own display name for the template's
        # interpolation, never re-deriving the `superseded` boolean
        # itself (that stays sourced from `manual_info`).
        built_in_name = enrich.static_airline_name_for_prefix(prefix) or ""
        escaped_built_in_name = escape_html(built_in_name)
        # RESEARCH.md Pitfall 6's own boundary is about the three
        # BOOLEANS (superseded/needs_artwork and the count they derive)
        # — this function's `airline_name` argument here is already the
        # CARD's display name, which for a superseded card is the
        # built-in name itself (D-10), never the operator's own
        # originally-typed name the note's third %s slot must name
        # ("the name you gave it"). That raw stored string lives only in
        # the registry entry, so it is fetched once here — a plain
        # value read, not a re-derivation of either boolean.
        stored_entry = manual_resolutions.load_manual_resolutions(state_dir).get(prefix) or {}
        operator_name = stored_entry.get("airline_name") or airline_name
        manual_note_value = MANUAL_SUPERSEDED_NOTE_TEMPLATE % (
            escape_html(prefix), escaped_built_in_name,
            escape_html(operator_name), escaped_built_in_name,
        )

    first_seen_value = last_seen_value = count_value = ""
    if mode == _VIEW_PANEL_MODE_NEEDS_ARTWORK:
        gap_row = unresolved_row_for_prefix(state_dir, prefix)
        if gap_row is not None:
            _, gap_count, gap_first_seen, gap_last_seen, _gap_callsign = gap_row
            first_seen_value = escape_html(gap_first_seen)
            last_seen_value = escape_html(gap_last_seen)
            count_value = escape_html(gap_count)

    # D-01's per-prefix scope sentence is a raw-gap-only concept — these
    # cards already show a resolved name.
    scope_value = ""

    # quick task 260902-tli: wraps the image in a real <button> (not the
    # <img> itself) — this codebase's a11y discipline (the global
    # :focus-visible floor, aria-labelled icon buttons elsewhere) makes a
    # non-focusable click target the wrong choice, and panel-lookup.js's
    # click delegation walks ancestors from the event target, so a click
    # on the inner image still resolves to this button. The aria-label
    # deliberately overrides the inner image's alt for the button's own
    # accessible name, so a screen reader announces the action ("Enlarge
    # ... illustration"), not just the picture.
    #
    # Phase 14 (14-02-PLAN.md Task 3, 14-UI-SPEC.md's Interaction
    # Contract "Correctness rule"): every trigger carries the full
    # fifteen-attribute data-view-panel-* vocabulary, not just the four
    # this card actually uses. A plain curated art card sets
    # mode="art" and leaves the other ten new attributes present but
    # EMPTY rather than omitted — an omitted attribute is precisely how
    # a stale value from the previous click would leak onto this one,
    # since panel-lookup.js's `attr || ""` idiom (plan 14-05) copies
    # every attribute on every open.
    #
    # Phase 14 (14-06-PLAN.md Task 1, UI-SPEC's Trigger-tag
    # generalisation): a card carrying a resolve prefix becomes a real
    # `<a href="/airlines?resolve={prefix}">` instead — the no-JS
    # fallback's own `?resolve={prefix}` page section can then already
    # serve it, exactly like a raw gap card. Every `data-view-panel-*`
    # attribute and the `aria-label` are otherwise identical between the
    # two tag variants; only the outer tag name and the presence of
    # `href` differ.
    if resolve_prefix_value:
        opening_tag = '<a href="%s?%s=%s" class="airline-card__zoom" ' % (
            AIRLINES_ROUTE, RESOLVE_QUERY_PARAM, resolve_prefix_value)
        closing_tag = "</a>"
    else:
        opening_tag = '<button type="button" class="airline-card__zoom" '
        closing_tag = "</button>"
    zoom_html = (
        opening_tag +
        '%s="%s" %s="%s" %s="%s" %s="%s" '
        '%s="%s" %s="%s" %s="%s" %s="%s" '
        '%s="%s" %s="%s" %s="%s" %s="%s" '
        '%s="%s" %s="%s" '
        'aria-label="%s">%s%s'
    ) % (
        _VIEW_PANEL_SRC_ATTR, busted_image_url,
        _VIEW_PANEL_CAPTION_ATTR, escape_html(CARD_IMAGE_ALT_TEMPLATE % airline_name),
        _VIEW_PANEL_MODE_ATTR, mode,
        _VIEW_PANEL_REPLACE_ACTION_ATTR, image_url,
        _VIEW_PANEL_HEADING_ATTR, heading_value,
        _VIEW_PANEL_MANUAL_ATTR, manual_value,
        _VIEW_PANEL_SCOPE_ATTR, scope_value,
        _VIEW_PANEL_RESOLVE_PREFIX_ATTR, resolve_prefix_value,
        _VIEW_PANEL_FIRST_SEEN_ATTR, first_seen_value,
        _VIEW_PANEL_LAST_SEEN_ATTR, last_seen_value,
        _VIEW_PANEL_COUNT_ATTR, count_value,
        _VIEW_PANEL_UPLOAD_ACTION_ATTR, upload_action_value,
        _VIEW_PANEL_DELETE_ACTION_ATTR, delete_action_value,
        _VIEW_PANEL_MANUAL_NOTE_ATTR, manual_note_value,
        escape_html(ZOOM_LABEL_TEMPLATE % airline_name),
        image_html,
        closing_tag,
    )
    chip_parts = []
    if shapes:
        chip_parts.extend(
            '<span class="airline-card__chip">%s</span>' % escape_html(variant_chip_label(shape))
            for shape in shapes
        )
    if has_manual:
        chip_text = SUPERSEDED_MARKER_TEXT if superseded else MANUAL_CHIP_ACTIVE_TEXT
        chip_parts.append('<span class="airline-card__chip">%s</span>' % escape_html(chip_text))
    chips_html = '<div class="airline-card__chips">%s</div>' % "".join(chip_parts) if chip_parts else ""
    base_filter_text = (
        airline_name.lower() if isinstance(airline_name, str) else str(airline_name).lower())
    if has_manual:
        base_filter_text += " superseded manual" if superseded else " resolved by hand manual"
    filter_text = escape_html(base_filter_text)
    return (
        '<div class="airline-card" data-filter-text="%s" data-filter-group="%d">'
        "%s"
        '<p class="airline-card__name">%s</p>'
        "%s"
        "</div>"
    ) % (filter_text, index, zoom_html, escape_html(airline_name), chips_html)


def _gallery_grid_html(pairs, state_dir=None, gap_cards_html="", manual_info_by_name=None):
    """Wrap one `_airline_card_html()` card per `(airline_name, shapes)`
    pair in the `.illustration-grid` container (06.6.4.1-UI-SPEC.md
    §7.1, companion/static/style.css from plan 01). Skips (renders
    nothing for) any pair whose card comes back empty. `state_dir`
    (quick task 260902-v26, default `None`) is threaded straight through
    to every card — see `_airline_card_html()`'s own docstring.

    `gap_cards_html` (14-04-PLAN.md, D-04/D-05): already-rendered gap
    cards' markup (`render()`'s own `"".join(_gap_card_html(...) for
    ...)` call), prepended inside this same `.illustration-grid`
    wrapper, ahead of the curated cards — one function still owns the
    grid's outer markup, matching this module's "one render function"
    discipline. Defaults to `""` so every existing call site (and every
    existing test calling this function positionally with two arguments)
    keeps rendering byte-identical output with no gap block at all.

    `manual_info_by_name` (14-06-PLAN.md Task 1, D-08/D-10): an optional
    dict mapping an airline's display name to its own
    `(prefix, superseded, needs_artwork)` triple — `render()`'s own
    lookup table, built once there from `_manual_resolution_rows()`,
    never recomputed here. Defaults to `None` (treated as `{}`) so every
    existing call site keeps rendering byte-identical output with no
    manual-resolution state on any card.
    """
    manual_info_by_name = manual_info_by_name or {}
    cards = "".join(
        _airline_card_html(
            index, airline_name, shapes, state_dir,
            manual_info_by_name.get(airline_name))
        for index, (airline_name, shapes) in enumerate(pairs))
    return '<div class="illustration-grid">%s%s</div>' % (gap_cards_html, cards)


def _gap_rows_for_grid(state_dir, manual_registry=None):
    """The gap block's own source, sort, threshold and cap (D-04, D-05,
    D-06): every prefix in the live unresolved-callsign-prefix registry
    with `count >= GAP_BLOCK_THRESHOLD`, sorted `(-count, prefix)`, split
    into `(shown, overflow_count)` where `shown` is at most
    `GAP_BLOCK_CAP` rows and `overflow_count` is how many eligible rows
    the cap hides.

    Reads `poll_loop.load_poll_state(state_dir)`'s own
    `unresolved_prefixes` dict directly — this module already imports
    `poll_loop` for `unresolved_row_for_prefix()` above — duplicating
    `health_page.unresolved_rows()`'s own malformed-entry-skip discipline
    and sort key byte for byte (skip a non-dict entry, skip a non-int or
    bool `count`, sort by count descending then prefix ascending) rather
    than importing it: a page module has no import path to a sibling
    page module (companion/pages/__init__.py's boundary), the same
    duplicated-not-imported discipline this module already applies to
    its own route constants (RESEARCH.md's Don't-Hand-Roll table).

    Returns rows in the exact five-field shape `unresolved_row_for_
    prefix()` already returns them (`prefix, count, first_seen,
    last_seen, example_callsign`), so a future caller can treat both
    functions' rows identically. Never raises — a falsy `state_dir` (this
    function, unlike `unresolved_row_for_prefix()`, is called
    unconditionally by `render()`, not gated behind a truthy
    `resolve_prefix`) or a missing/unreadable poll state both yield
    `([], 0)` rather than crashing a page render, mirroring
    `_illustration_cache_buster()`'s own no-`state_dir` short-circuit.

    14-08 on-glass fix (2026-09-06, D-13/D-14 real-browser check): skips
    any prefix that already has a `manual_resolutions.json` entry, even
    though `poll_state.json`'s own `unresolved_prefixes` still lists it —
    the two files are updated by different owners on different
    schedules (the companion writes the manual entry immediately;
    `server/poll_loop.py`'s D-14 cleanup only clears the gap entry on
    the device's *next* wake-and-poll cycle, exactly what the save
    confirmation flash tells the operator: "the frame will pick it up
    next time it wakes and polls"). Without this exclusion, saving a
    name for a still-unresolved gap rendered TWO `data-view-panel-
    resolve-prefix="{prefix}"` elements simultaneously for one wake
    (the stale gap card plus the new manual/needs-artwork card) —
    confirmed live in a real browser — and `panel-lookup.js`'s
    `document.querySelector()` auto-open (a single-match lookup, by
    design, since exactly one match is the invariant every other mode
    relies on) silently grabbed whichever rendered first in DOM order
    (the gap card, since D-05 sorts gaps to the head of the grid),
    reopening the dialog on the wrong (Step A) form after the operator
    had just completed Step A. The manual registry is authoritative the
    moment a name is saved — this function's OWN eligibility list is
    the right and only place to encode that, not a client-side
    disambiguation panel-lookup.js would have no principled way to make
    (it has no way to know which of two matches is "newer").

    `manual_registry` (code review fix, 2026-09-06, WR-02): optional,
    defaults to `None`. When omitted, this function loads it fresh via
    `manual_resolutions.load_manual_resolutions(state_dir)` exactly as
    before — preserving the standalone-callable shape
    `companion/test_status_pages.py`'s own direct calls already rely
    on. `render()` instead passes in the SAME registry dict it already
    resolved for `_manual_resolution_rows()` a few lines below this
    function's own call site, rather than letting this function load
    it a second, independent time. Two independent reads of
    `manual_resolutions.json` within one `ThreadingHTTPServer` request
    (this function's own internal read, plus `render()`'s separate
    read for the manual-card injection logic) opened a narrow race: a
    concurrent write landing between the two could reproduce, within
    that single request, the exact "prefix missing from both blocks"
    failure this function's own D-13/D-14 fix above was written to
    close. One read per render, threaded through, closes it —
    matching this codebase's own repeatedly-stated "single read per
    cycle" discipline (`poll_loop.py`'s own comment on this exact
    principle).
    """
    if not state_dir:
        return [], 0
    state = poll_loop.load_poll_state(state_dir)
    registry = state.get("unresolved_prefixes")
    if not isinstance(registry, dict):
        return [], 0
    if manual_registry is None:
        manual_registry = manual_resolutions.load_manual_resolutions(state_dir)
    eligible = []
    for prefix, entry in registry.items():
        if prefix in manual_registry:
            continue
        if not isinstance(entry, dict):
            continue
        count = entry.get("count")
        if not isinstance(count, int) or isinstance(count, bool):
            continue
        if count < GAP_BLOCK_THRESHOLD:
            continue
        eligible.append((
            prefix,
            count,
            entry.get("first_seen") or "",
            entry.get("last_seen") or "",
            entry.get("example_callsign") or "",
        ))
    eligible.sort(key=lambda row: (-row[1], row[0]))
    shown = eligible[:GAP_BLOCK_CAP]
    overflow_count = max(0, len(eligible) - GAP_BLOCK_CAP)
    return shown, overflow_count


def _gap_card_html(index, row):
    """One coverage-gap card (D-01, D-02, D-04, D-05, D-12,
    14-UI-SPEC.md's "Gap-card markup shape"): the whole `<a
    class="airline-card">` element IS the click-to-resolve trigger — no
    `<img>` at all (D-02: the placeholder is pure CSS,
    `.airline-card__placeholder`, already styled by plan 14-03) and no
    nested `.airline-card__zoom` button (D-12: "an `<a>` needs only
    `preventDefault()`").

    `row` is one of `_gap_rows_for_grid()`'s own five-field tuples
    (`prefix, count, first_seen, last_seen, example_callsign`) — the
    same shape `unresolved_row_for_prefix()` returns. `index` is this
    card's position among the shown gap cards (0-based), used only to
    build its `data-filter-group` value.

    `escaped_prefix`/`escaped_callsign` are each computed exactly once
    here and reused across every attribute/text site that needs them
    (T-06.6.4.1-05, T-14-16) — never re-escaped. `data-view-panel-src`
    and `data-view-panel-manual` both stay the empty string: a raw gap
    has no image and no manual-resolution history yet (that state
    belongs to plan 14-06's manual/superseded cards, not here).
    `data-view-panel-first-seen`/`-last-seen`/`-count` carry the escaped
    RAW registry values, never run through
    `layout.concise_timestamp_html()` — that helper returns markup
    unsuited to an attribute value, and `panel-lookup.js` can only ever
    textContent-copy whatever raw string the attribute carries; this is
    a deliberate, documented asymmetry with the no-JS fallback's own
    concise rendering, not a defect.

    `data-filter-group` is a string-prefixed `"gap%d"`, never a bare
    integer, so it can never collide with the curated grid's own
    `enumerate(pairs)` sequence sharing the same attribute name
    (RESEARCH.md Pitfall 4, T-14-17).

    Code review fix (2026-09-06, WR-03): `example_callsign` is a JSON
    *value*, not a dict key like `prefix` — a hand-edited
    `poll_state.json` can hold a number, list, or other non-string
    there, and `_gap_rows_for_grid()`'s own `entry.get(...) or ""`
    fallback does not catch it (a truthy non-string value passes
    through unchanged). Every other use of these two values already
    goes through `escape_html()`, which coerces via `str()` and never
    raises — but the `.lower()` call below runs on the raw value
    first, ahead of that safety net, and `.lower()` on a non-string
    raises `AttributeError`, contradicting this function's own
    "never raises" framing and crashing the whole `/airlines` render.
    `prefix` itself needs no equivalent guard — it is a dict key
    straight from `json.load()`, and JSON object keys are always
    strings. `health_page.unresolved_rows()` carries the identical
    unguarded `or ""` pattern for the same field, inherited from the
    "byte for byte" duplication this function's own docstring already
    describes — harmless there only because that page never calls a
    string-only method on the value. Left unfixed there: out of this
    phase's scope (a different page module, no `.lower()`-shaped risk
    reachable in its own current code).
    """
    prefix, count, first_seen, last_seen, example_callsign = row
    if not isinstance(example_callsign, str):
        example_callsign = str(example_callsign)
    escaped_prefix = escape_html(prefix)
    escaped_callsign = escape_html(example_callsign)
    filter_text = escape_html("%s %s" % (example_callsign.lower(), prefix.lower()))
    return (
        '<a class="airline-card" href="%s?%s=%s" '
        '%s="" %s="%s" %s="%s" %s="%s" '
        '%s="" %s="%s" %s="%s" '
        '%s="%s" %s="%s" %s="%s" '
        'data-filter-text="%s" data-filter-group="gap%d" '
        'aria-label="%s">'
        '<span class="airline-card__placeholder" aria-hidden="true"></span>'
        '<p class="airline-card__name mono">%s</p>'
        "</a>"
    ) % (
        AIRLINES_ROUTE, RESOLVE_QUERY_PARAM, escaped_prefix,
        _VIEW_PANEL_SRC_ATTR,
        _VIEW_PANEL_CAPTION_ATTR, escaped_callsign,
        _VIEW_PANEL_HEADING_ATTR, RESOLVE_HEADING,
        _VIEW_PANEL_MODE_ATTR, _VIEW_PANEL_MODE_GAP,
        _VIEW_PANEL_MANUAL_ATTR,
        _VIEW_PANEL_SCOPE_ATTR, RESOLVE_CAPTION_TEMPLATE % escaped_prefix,
        _VIEW_PANEL_RESOLVE_PREFIX_ATTR, escaped_prefix,
        _VIEW_PANEL_FIRST_SEEN_ATTR, escape_html(first_seen),
        _VIEW_PANEL_LAST_SEEN_ATTR, escape_html(last_seen),
        _VIEW_PANEL_COUNT_ATTR, escape_html(count),
        filter_text, index,
        GAP_CARD_ARIA_TEMPLATE % (escaped_prefix, escaped_callsign),
        escaped_callsign,
    )


def _gap_overflow_html(overflow_count):
    """The gap block's overflow line (D-07), rendered only when
    `_gap_rows_for_grid()`'s own cap hides at least one eligible prefix
    — `""` otherwise. `MANUAL_OVERFLOW_TEMPLATE`'s `%d` slot is
    `overflow_count`; `MANUAL_OVERFLOW_LINK_TEXT` is the only text
    wrapped by the `<a href="/health">` anchor — the trailing period
    sits outside it, matching 14-UI-SPEC.md's Gap-block composition
    literal exactly.
    """
    if not overflow_count:
        return ""
    return '<p class="text-label section-caption">%s<a href="/health">%s</a>.</p>' % (
        MANUAL_OVERFLOW_TEMPLATE % overflow_count, MANUAL_OVERFLOW_LINK_TEXT)


def _lightbox_html():
    """The single shared click-to-enlarge `<dialog>` (quick task
    260902-tli), emitted once per page — never once per card — by
    `render()`, only when at least one card actually carries a zoom
    trigger. Mirrors `history_page._lightbox_html()` element-for-element
    and class-for-class for its image/caption/note prefix (same order,
    same three `lightbox__*` elements, same close-attribute button),
    with the `lightbox--wide` class (the enlarged illustration needs
    more room than History's 480px default) and this module's own
    `LIGHTBOX_NOTE`, then (Phase 14, 14-02-PLAN.md Task 3) every
    element the three view modes (art/gap/needs-artwork) plus the
    orthogonal manual state (active/superseded) can need, all
    server-rendered once through the same shared functions
    `_resolve_section_html()` (the no-JS fallback) also calls —
    Claude's Discretion #1, one definition per form, two call sites.

    Element order inside the dialog: image, caption, note, heading,
    manual-note, resolve-context, resolve-name form, resolve-upload
    zone, replace form, delete form, then Close. Close stays last so
    the dismissal affordance is the stable bottom-most control and the
    tab order reads "look, act, dismiss" — `panel-lookup.js` finds the
    close button by attribute, not by position, so this order matters
    only to a human, never to the script.

    Every optional child here is a real, present placeholder — heading
    and manual-note are emitted empty (their own `:empty` CSS collapse
    rule is plan 14-03's job, not this function's); the resolve-context
    `<dl>` is built from `row=None` (five empty `<dd>`s); the
    resolve-name/resolve-upload/delete forms all carry `id_suffix=
    "-dialog"` (or, for the id-less delete form, just `action=""`) so
    their ids never collide with the no-JS fallback section's own
    identically-shaped, unsuffixed ids when both render at once. No
    element is emitted `hidden` from the server — the initial
    visibility state is `panel-lookup.js`'s to set (plan 14-05), and
    RESEARCH.md Pitfall 3 requires that state be final *before*
    `showModal()` runs, a runtime ordering concern this function does
    not own. Every optional form's own primary control keeps whatever
    `autofocus` attribute the shared function itself emits — neither
    stripped nor duplicated — so the no-JS fallback path's own focus
    behaviour is untouched.

    `companion/static/panel-lookup.js` writes the image src/alt, the
    caption text, and the replace form's `action` attribute on click
    today; this function only emits the static note and every form's
    `action=""`/empty placeholder, none of which the script writes on
    page load — only on the next click (and, from plan 14-05 onward,
    every other attribute in the vocabulary too).
    """
    resolve_context_html = _resolve_context_html(None, None, id_suffix="-dialog")
    resolve_name_html = _resolve_name_form_html("", "-dialog")
    resolve_upload_html = _resolve_upload_form_html("", "-dialog")
    delete_html = _manual_delete_form_html("")
    return (
        '<dialog class="lightbox lightbox--wide" id="%s" aria-label="%s">'
        '<img class="lightbox__image" src="" alt="">'
        '<p class="lightbox__caption text-label mono"></p>'
        '<p class="lightbox__note text-body">%s</p>'
        '<h2 class="%s"></h2>'
        '<p class="%s text-body"></p>'
        "%s"
        "%s"
        "%s"
        "%s"
        "%s"
        '<button type="button" %s>Close</button>'
        "</dialog>"
    ) % (
        LIGHTBOX_DIALOG_ID, escape_html(LIGHTBOX_ARIA_LABEL), escape_html(LIGHTBOX_NOTE),
        LIGHTBOX_HEADING_CLASS,
        LIGHTBOX_MANUAL_NOTE_CLASS,
        resolve_context_html,
        resolve_name_html,
        resolve_upload_html,
        _lightbox_replace_form_html(),
        delete_html,
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

    Plan 14-06-external gap-closure (2026-09-06, per 14-05-SUMMARY.md's
    own documented "Known Limitations" finding): also emits an empty,
    always-present `<p class="lightbox__resolve-scope"></p>` — the
    element 14-UI-SPEC.md's Copy Deck names as `RESOLVE_CAPTION_
    TEMPLATE`'s destination inside the dialog. `panel-lookup.js`
    (plan 14-05, already finished) reads `data-view-panel-scope` from
    every trigger and writes it into this exact class on every open;
    until this element existed, that write had nowhere to land and
    D-01's per-prefix scope sentence never appeared in the dialog. No
    server-side text is put here — the value is always written
    client-side — and it is emitted unconditionally (not gated on
    `id_suffix`) so the shared function keeps one output shape at both
    call sites; a permanently-empty paragraph in the no-JS fallback's
    own copy is harmless (nothing reads it there, the fallback's own
    separate `<p class="text-label section-caption">` already carries
    the real text).
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
        '<p class="lightbox__resolve-scope"></p>'
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
        return '<div class="page-section" data-resolve-fallback>%s%s</div>' % (back_link, body)

    escaped_prefix = escape_html(prefix)

    registry = manual_resolutions.load_manual_resolutions(state_dir)
    entry = registry.get(prefix)

    if entry is None:
        if row is None:
            # No live gap AND no manual entry for this prefix: genuinely
            # nothing to resolve here.
            body = '<p class="text-body">%s</p>' % RESOLVE_STALE_BODY
            return '<div class="page-section" data-resolve-fallback>%s%s</div>' % (back_link, body)
        # Step A — name not yet saved. No entry exists yet, so no
        # delete form (D-09 amendment).
        heading = '<h2 class="text-heading">%s</h2>' % RESOLVE_HEADING
        caption = '<p class="text-label section-caption">%s</p>' % (
            RESOLVE_CAPTION_TEMPLATE % escaped_prefix)
        form = _resolve_name_form_html(prefix, "")
        return '<div class="page-section" data-resolve-fallback>%s%s%s%s%s</div>' % (
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
        return '<div class="page-section" data-resolve-fallback>%s%s</div>' % (back_link, body)

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
        return '<div class="page-section" data-resolve-fallback>%s%s%s%s%s%s%s</div>' % (
            back_link, heading, caption, context_html, upload_zone, skip_link, delete_form)

    # Already resolved: a bookmark or a Back press landed on a prefix
    # still listed as a gap, but a manual entry already names an airline
    # that has artwork. No controls except delete.
    body = '<p class="text-body">%s</p>' % (RESOLVE_ALREADY_DONE_TEMPLATE % escaped_name)
    return '<div class="page-section" data-resolve-fallback>%s%s%s%s</div>' % (back_link, heading, body, delete_form)


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
    returns `None`) — this is what drives a card's `needs-artwork` mode
    (`_airline_card_html()`'s own `manual_info`-derived branch, phase
    14 plan 14-06), the grid's own entry point into Step B now that a
    resolved prefix's live-gap deep link (D-10/Health) can be gone
    (D-14) before the operator ever uploads anything. Always `False`
    for a superseded entry (the built-in table already owns that
    prefix; uploading under the operator's own name would not change
    what the frame displays) and for a name whose key no longer slugs
    (corrupt-file defence, mirrors `_resolve_section_html()`'s own
    guard).
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


def _manual_summary_html(manual_rows):
    """The D-11 summary line that replaces the retired standalone
    management table: `""` when `manual_rows` is empty (no chrome with
    no data — not even a heading, UI-SPEC's Copywriting Contract),
    otherwise a single clickable `<button>` naming the total count and,
    when at least one entry is superseded, the superseded count too.

    `manual_rows` is `_manual_resolution_rows()`'s own already-computed
    tuples — passed in by `render()`, never recomputed here (this
    module's "consume, don't re-derive" discipline for that function's
    three booleans, RESEARCH.md Pitfall 6). No `escape_html()` call is
    needed on the interpolated counts themselves: both are integers
    interpolated via `%d`, matching this module's existing discipline
    for count-only cells (`_gap_overflow_html()`'s own identical
    choice).

    `data-filter-set="manual"` is read by `list-filter.js`'s plan-14-03
    `[data-filter-set]` hook — clicking this button sets the filter
    input's value to `"manual"` and re-runs the page's one existing
    filter function, matching every card's own invisible `"manual"`
    `data-filter-text` token (`_airline_card_html()`'s chip/filter-text
    extension) — never a second filtering mechanism.
    """
    if not manual_rows:
        return ""
    total = len(manual_rows)
    superseded_count = sum(1 for row in manual_rows if row[3])
    summary_text = (
        MANUAL_SUMMARY_TEMPLATE % (total, superseded_count) if superseded_count
        else MANUAL_SUMMARY_TEMPLATE_NONE % total)
    return '<button type="button" class="manual-summary" data-filter-set="manual">%s</button>' % summary_text


def render(ctx):
    """The Airlines page (D-13 through D-17, extended by phase 13's
    D-03/D-06/D-07/D-10 through D-13, and by phase 14's coverage-gap
    grid, manual-resolution absorption, and page-order reversal): the
    page header, the D-16 filter bar, the D-11 manual-resolutions
    summary line (only when the registry has at least one entry), the
    D-04/D-05/D-06/D-07 gap block (gap cards prepended head-of-grid,
    plus D-07's overflow line), one card per airline in
    `illustrations.target_variants_by_airline()` order (plus any
    injected manual-only card, D-08), the shared click-to-enlarge
    lightbox dialog (quick task 260902-tli), then (phase 14, moved from
    the top of the page) the conditional resolve section. `ctx` is
    accepted for call-site parity with every other page module's
    `render(ctx)` signature.

    Since quick task 260902-v26 this reads `state_dir` (used to resolve
    each card's illustration-replace cache buster, see
    `_illustration_cache_buster()`, by both phase-13 sections below as
    their own state-dir source, and by `_gap_rows_for_grid()` above).
    Phase 13 (13-04-PLAN.md) adds three more `ctx.get()` reads:
    `resolve_prefix` (the `?resolve={prefix}` query value,
    presence-gating `_resolve_section_html()`), `now` (threaded to every
    rendered timestamp in both new sections), and `manual_resolutions`
    (an already-loaded registry dict, this function's own preferred
    source for `_manual_resolution_rows()` — plan 13-06 threads this in;
    absent, it falls back to loading fresh from `state_dir`). Every one
    of these four keys is read with `ctx.get()`, never `ctx[...]` —
    `companion/test_view_pages.py`'s existing `render({})` call with a
    literal empty dict must keep rendering the unchanged gallery, no gap
    cards, no manual summary, no resolve section. This page still opens
    no database.

    The filter bar and the lightbox dialog both render whenever there is
    at least one card of EITHER kind (gap or curated) — this codebase's
    consistent "no chrome with no data" rule, widened here so a state
    with gaps but zero curated pairs still gets its filter bar and
    dialog. The manual-resolutions summary line has its own,
    independent gate (`_manual_summary_html()` returns `""` on an empty
    registry) and is never tied to the gallery having any cards — the
    same "reference/cleanup material, not the page's purpose" framing
    the retired management table's own empty state used to carry
    (UI-SPEC Autonomous Decision 2).
    """
    # ctx.get(), never ctx["state_dir"]: companion/test_view_pages.py:1365
    # calls render({}) with a literal empty dict, and every other caller
    # of this page (companion/app.py's page_context()) does supply
    # state_dir, so this must stay tolerant of both.
    state_dir = ctx.get("state_dir")
    resolve_html = _resolve_section_html(ctx)
    pairs = illustrations.target_variants_by_airline()

    # Phase 14 (14-06-PLAN.md Task 1, D-08/D-10/D-12 fallback
    # reachability): the identical registry-loading fallback the retired
    # management-table section used to use. `manual_rows` is
    # `_manual_resolution_rows()`'s own tuples — consumed here, never
    # re-derived, and reused as-is by `_manual_summary_html()` below
    # (Task 2) rather than recomputed a second time.
    #
    # Code review fix (2026-09-06, WR-02): this registry load moved
    # ABOVE `_gap_rows_for_grid()`'s own call, and its result is now
    # threaded into that call, so one render() only ever reads
    # manual_resolutions.json once — see that function's own
    # docstring for the narrow same-request race this closes.
    registry = ctx.get("manual_resolutions")
    if registry is None:
        registry = manual_resolutions.load_manual_resolutions(state_dir) if state_dir else {}
    manual_rows = _manual_resolution_rows(state_dir, registry)

    gap_shown, gap_overflow_count = _gap_rows_for_grid(state_dir, registry)
    gap_cards_html = "".join(_gap_card_html(i, row) for i, row in enumerate(gap_shown))
    overflow_html = _gap_overflow_html(gap_overflow_count)

    # manual_info_by_name maps a CARD's display name to its own
    # (prefix, superseded, needs_artwork) triple. A superseded row's
    # display name is the BUILT-IN airline's own name (D-10: the card
    # that gains the chip/note is the one the frame actually renders
    # under, which is already a curated card by construction — UI-SPEC's
    # "a superseded entry needs no injection"), never the operator's own
    # orphaned stored name. An active row's display name is its own
    # stored `airline_name`, whether already curated or newly injected
    # below. Only the FIRST occurrence of a given display name is kept
    # (manual_rows arrive prefix-ascending, so lowest-prefix wins —
    # UI-SPEC's documented "Known limitation").
    # Code review fix (2026-09-06, WR-04): a manual entry only earns an
    # injected card when its own stored name still resolves to a usable
    # illustration key. `add_entry()` already requires
    # `manual_resolutions.illustration_key_for_name()` to succeed before
    # persisting, so this can never fail for a row at the moment it is
    # written — the review raised a LATER-drift scenario instead: a
    # future change to `illustrations.py`'s reserved-name list or
    # slugging rules making an already-persisted name stop resolving.
    #
    # Traced through before applying this fix: `registry` (this
    # function's own parameter, and `_gap_rows_for_grid()`'s
    # `manual_registry` above — both always the SAME dict in `render()`,
    # by construction) is only ever populated one way in this codebase,
    # `manual_resolutions.load_manual_resolutions(state_dir)`
    # (`companion/app.py`'s `page_context()` is the sole `ctx
    # ["manual_resolutions"]` writer) — and that loader's own contract
    # already re-validates `illustration_key_for_name()` on EVERY load,
    # dropping any entry that fails it, "not only against one submitted
    # through add_entry()". So the drift scenario the review named
    # cannot actually reach this loop or `_gap_rows_for_grid()`'s own
    # exclusion through any real path: the entry would already be gone
    # from `registry` by the time either function sees it, and
    # `_gap_rows_for_grid()`'s `if prefix in manual_registry` check is
    # therefore already safe without a matching change there. This
    # guard stays anyway as explicit defence in depth — the same
    # posture `illustrations.py`'s own path-safety functions take
    # ("so the boundary holds even if a future caller forgets") — for a
    # hand-built or differently-sourced registry dict this loop cannot
    # rule out forever, not because the reviewed scenario is reachable
    # today.
    curated_names = {name for name, _shapes in pairs}
    manual_info_by_name = {}
    injected_pairs = []
    injected_names = set()
    for prefix, airline_name, _created_at, superseded, needs_artwork in manual_rows:
        if not superseded and not manual_resolutions.illustration_key_for_name(airline_name):
            continue
        display_name = (
            enrich.static_airline_name_for_prefix(prefix) if superseded else airline_name)
        if display_name and display_name not in manual_info_by_name:
            manual_info_by_name[display_name] = (prefix, superseded, needs_artwork)
        if (not superseded and airline_name not in curated_names
                and airline_name not in injected_names):
            injected_pairs.append((airline_name, []))
            injected_names.add(airline_name)
    pairs = pairs + injected_pairs

    total = len(gap_shown) + len(pairs)
    filter_html = _filter_bar_html(total) if (pairs or gap_shown) else ""
    lightbox_html = _lightbox_html() if (pairs or gap_shown) else ""
    # Phase 14 (14-06-PLAN.md Task 2, D-11): UI-SPEC's binding
    # top-to-bottom order is filter_bar, then manual-summary, then
    # gap-overflow, then grid — the standalone management table
    # (`_manual_resolutions_section_html()`, deleted this task) is gone;
    # this one-line summary takes its place, reusing `manual_rows`
    # computed above rather than recomputing it.
    summary_html = _manual_summary_html(manual_rows)
    return (
        layout.page_header("Airlines", purpose=GALLERY_PURPOSE_TEXT)
        + filter_html
        + summary_html
        + overflow_html
        + _gallery_grid_html(pairs, state_dir, gap_cards_html, manual_info_by_name)
        + lightbox_html
        + resolve_html
    )
