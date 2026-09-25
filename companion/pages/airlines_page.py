"""Illustration gallery for every airline the frame recognizes, plus the
operator flow to resolve an unidentified flight and manage manual
resolutions.

Renders the static curated list from
`illustrations.target_variants_by_airline()`; opens no database.
`unresolved_row_for_prefix()` makes one read-only membership check via
`poll_loop.load_poll_state()`, gated on `ctx["resolve_prefix"]`. Each
`<img>` carries `illustration_normalize`'s width/height constants so the
browser reserves space before the image loads.
"""
import html as html_module
import os
import re

from companion.illustration_normalize import (
    ILLUSTRATION_TARGET_HEIGHT,
    ILLUSTRATION_TARGET_WIDTH,
)
import companion.i18n as i18n
from companion.layout import escape_html
import companion.layout as layout
from server.plane import illustrations
# manual_resolutions, enrich and poll_loop import this page module in
# neither direction, so importing them here creates no cycle.
from server.plane import manual_resolutions
from server.plane import enrich
import server.poll_loop as poll_loop

# Mirrors companion/app.py's own ILLUSTRATION_IMAGE_ROUTE_PREFIX,
# duplicated rather than imported since app.py imports this module (the
# reverse import would cycle); pinned by a cross-module equality check
# in companion/test_status_pages.py.
ILLUSTRATION_ROUTE_PREFIX = "/illustration/"

GALLERY_PURPOSE_TEXT = (
    "Illustration reference for every airline this frame can recognize.")

CARD_IMAGE_ALT_TEMPLATE = "%s illustration"

GAP_STRIP_HEADING = "Unidentified airlines"
GAP_STRIP_BODY = "Tap a callsign below to name its airline."

# Reuses History's shared <dialog> lightbox and panel-lookup.js's click
# delegation. These five names are duplicated (not imported) from
# history_page.py and panel-lookup.js — a page module cannot import a
# sibling page or a static script — and a cross-module guard in
# test_view_pages.py pins them against history_page.py's values.
LIGHTBOX_DIALOG_ID = "panel-lookup-dialog"
_VIEW_PANEL_SRC_ATTR = "data-view-panel-src"
_VIEW_PANEL_CAPTION_ATTR = "data-view-panel-caption"
_VIEW_PANEL_CLOSE_ATTR = "data-view-panel-close"

# Unlike the five names above, these have no history_page.py
# counterpart and must never be added to test_view_pages.py's
# cross-module comparison — duplicated (not imported) into
# panel-lookup.js and style.css, the same discipline as above.
_VIEW_PANEL_REPLACE_ACTION_ATTR = "data-view-panel-replace-action"
LIGHTBOX_REPLACE_FORM_CLASS = "lightbox__replace"

# Three more class constants for the framed replace-action zone,
# duplicated (not imported) into style.css only — panel-lookup.js does
# not use them and must not be taught to; it looks up the form only by
# LIGHTBOX_REPLACE_FORM_CLASS.
LIGHTBOX_REPLACE_ZONE_CLASS = "lightbox__replace-zone"
REPLACE_HINT_CLASS = "lightbox__replace-hint"
REPLACE_ICON_CLASS = "lightbox__replace-icon"

# The eleven data-view-panel-* attributes every trigger's vocabulary
# carries. Some are render-only until panel-lookup.js consumes them,
# classified in test_view_pages.py's _LIGHTBOX_RENDER_ONLY_TOKENS.
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

# Value vocabularies: no mode/manual string is ever a bare literal at a
# call site.
_VIEW_PANEL_MODE_ART = "art"
_VIEW_PANEL_MODE_GAP = "gap"
_VIEW_PANEL_MODE_NEEDS_ARTWORK = "needs-artwork"
_VIEW_PANEL_MANUAL_ACTIVE = "active"
_VIEW_PANEL_MANUAL_SUPERSEDED = "superseded"

LIGHTBOX_HEADING_CLASS = "lightbox__heading"
LIGHTBOX_MANUAL_NOTE_CLASS = "lightbox__manual-note"
LIGHTBOX_RESOLVE_NAME_CLASS = "lightbox__resolve-name"
LIGHTBOX_DELETE_CLASS = "lightbox__delete"

# The dialog's single action row: Close on the left, the primary action
# on the right. The primary button is lifted out of its form and
# re-attached via the native form="<id>" attribute, so the no-JS
# fallback's own submit can stay inside its own form
# (_resolve_name_form_html()'s include_submit).
LIGHTBOX_ACTIONS_CLASS = "lightbox__actions"
MANUAL_RESOLVE_FORM_ID = "manual-resolve-form"

RESOLVE_UPLOAD_ZONE_CLASS = "resolve-upload-zone"
RESOLVE_CONTEXT_CLASS = "resolve-context"

# Drag-and-drop affordance and framing preview, layered over the
# existing upload forms: a drop assigns the file to the form's own
# <input type="file"> via DataTransfer, so bytes travel the same
# validated path as a picked file. Names are duplicated into
# style.css/panel-lookup.js and pinned by cross-file guards.
UPLOAD_DROP_CLASS = "upload-drop"
# Carried by the same element as layout.JS_GATE_CLASS, never by an
# ancestor, and used by the no-JS control registry to find each zone.
UPLOAD_DROP_ATTR = "data-upload-drop"
# id of the file input a drop writes into, looked up by
# getElementById() rather than a DOM walk (panel-lookup.js avoids
# Element.closest()).
UPLOAD_DROP_INPUT_ATTR = "data-upload-drop-input"
# companion/app.py's own upload byte cap, rendered here rather than
# retyped in JavaScript — see _max_upload_bytes().
UPLOAD_DROP_MAX_BYTES_ATTR = "data-upload-drop-max-bytes"
# The three refusal messages, already translated server-side — the
# script never invents its own copy.
UPLOAD_DROP_TYPE_ERROR_ATTR = "data-upload-drop-type-error"
UPLOAD_DROP_SIZE_ERROR_ATTR = "data-upload-drop-size-error"
UPLOAD_DROP_MULTIPLE_ERROR_ATTR = "data-upload-drop-multiple-error"
# Drag-over state, set by panel-lookup.js. An attribute rather than
# :hover, since :hover is invisible on touch.
UPLOAD_DROP_ACTIVE_ATTR = "data-upload-drop-active"
UPLOAD_DROP_PREVIEW_CLASS = "upload-drop__preview"
UPLOAD_DROP_IMAGE_CLASS = "upload-drop__image"
UPLOAD_DROP_NOTE_CLASS = "upload-drop__note"
UPLOAD_DROP_MESSAGE_CLASS = "upload-drop__message"
# --upload-preview-ratio is written inline (never a style.css literal)
# so its value comes from illustration_normalize's own output frame
# rather than a retyped number.

# "Framed" not "look": shows the whole image inside the frame it will
# occupy; the server may still crop differently and is the only
# authority on that.
UPLOAD_DROP_HINT_TEXT = "Or drag an image onto this card."
UPLOAD_PREVIEW_CAPTION_TEXT = "Framing preview — how it will be framed."
UPLOAD_PREVIEW_ALT_TEXT = "Framing preview of the image you chose"
UPLOAD_DROP_TYPE_ERROR_TEXT = "Only PNG images can be dropped here."
UPLOAD_DROP_MULTIPLE_ERROR_TEXT = "Drop one image at a time."
UPLOAD_DROP_SIZE_ERROR_TEMPLATE = "That image is larger than the %d MB limit."

ZOOM_LABEL_TEMPLATE = "Enlarge %s illustration"

# Empty by design: panel-lookup.js's shared guard clause requires
# .lightbox__note to exist or its click handler never attaches;
# style.css collapses an empty note to no visible space.
LIGHTBOX_NOTE = ""
LIGHTBOX_ARIA_LABEL = "Airline illustration"

# Flash keys are defined here, not in app.py, because app.py already
# imports this module — the reverse import would cycle. app.py rebinds
# them under FLASH_KEY_* names and adds their copy/ARIA role.
FLASH_ILLUSTRATION_REPLACED = "illustration_replaced"
# Upload was read and parsed but rejected (not an image, too small, not
# landscape, no transparency, or over the size cap) — an expected
# validation outcome, not a server failure.
FLASH_ILLUSTRATION_REJECTED = "illustration_rejected"
# Unlike REJECTED: something unexpected happened server-side while
# storing an otherwise-acceptable upload.
FLASH_ILLUSTRATION_REPLACE_FAILED = "illustration_replace_failed"

FLASH_MANUAL_RESOLVED = "manual_resolved"
FLASH_MANUAL_NAME_EMPTY = "manual_name_empty"
FLASH_MANUAL_NAME_TOO_LONG = "manual_name_too_long"
FLASH_MANUAL_NAME_RESERVED = "manual_name_reserved"
FLASH_MANUAL_PREFIX_STALE = "manual_prefix_stale"
FLASH_MANUAL_REGISTRY_FULL = "manual_registry_full"
# add_entry() returns ADD_FAILED on an unwritable state dir and never
# raises; without this key that failure would redirect with no message.
FLASH_MANUAL_SAVE_FAILED = "manual_save_failed"
# Same reasoning as FLASH_MANUAL_SAVE_FAILED, for delete_entry()
# returning False after a write failure.
FLASH_MANUAL_DELETE_FAILED = "manual_delete_failed"

# A name the operator typed but that manual_resolutions.py's slugger
# cannot turn into a usable key (e.g. it slugs to the empty string).
FLASH_MANUAL_NAME_UNUSABLE = "manual_name_unusable"

# Deleting a manual resolution produces no success flash: the row
# disappearing from the management list is the confirmation.

RESOLVE_ROUTE = "/airlines/resolve"
MANUAL_DELETE_ROUTE_PREFIX = "/airlines/manual-resolutions/"
MANUAL_DELETE_ROUTE_SUFFIX = "/delete"
AIRLINES_ROUTE = "/airlines"
RESOLVE_QUERY_PARAM = "resolve"

# A prefix needs at least GAP_BLOCK_THRESHOLD sightings to earn a gap
# card; at most GAP_BLOCK_CAP cards ever render (see
# _gap_overflow_html() for the rest).
GAP_BLOCK_THRESHOLD = 3
GAP_BLOCK_CAP = 12

RESOLVE_BACK_LINK_TEXT = "← Back to Airlines"
RESOLVE_STALE_BODY = (
    "That coverage gap isn’t there anymore — it may already be "
    "resolved. See Health for the complete list of current gaps.")
RESOLVE_HEADING = "Resolve an unidentified flight"
# No callsign clause: this template must stay true even when no
# sighting data survives for the prefix (the row-gone fallback path).
RESOLVE_CAPTION_TEMPLATE = (
    "Every flight using prefix %s will show as this airline.")
RESOLVE_CONTEXT_LABELS = (
    "Prefix", "First seen", "Last seen", "Times seen", "Example callsign")
# 5-tuple aligned 1:1 with RESOLVE_CONTEXT_LABELS so the two can only
# ever be zipped, never mismatched.
RESOLVE_CONTEXT_DD_CLASSES = (
    "resolve-context__prefix",
    "resolve-context__first-seen",
    "resolve-context__last-seen",
    "resolve-context__count",
    "resolve-context__callsign",
)
NAME_LABEL_TEXT = "Airline name"
NAME_HINT_TEXT = "Start typing — pick a suggestion."
SAVE_BUTTON_TEXT = "Save airline name"
STEP_B_HEADING_TEMPLATE = "Add an illustration for %s"
STEP_B_CAPTION = "Saved — add artwork below, or skip for now."
STEP_B_SKIP_TEXT = "Skip — I’ll add artwork later"
# Fourth reachable state: a bookmark or Back press lands on a prefix
# that's still listed as a gap but is already fully resolved.
# RESOLVE_STALE_BODY would be false here.
RESOLVE_ALREADY_DONE_TEMPLATE = (
    "%s is already named for this prefix and has artwork — nothing "
    "more to do here.")

MANUAL_NAME_INPUT_ID = "manual-airline-name"
MANUAL_UPLOAD_INPUT_ID = "manual-illustration-input"
# Suffixed by the same id_suffix its input carries, so the no-JS
# control registry can declare the form association rather than guess
# it.
MANUAL_UPLOAD_FORM_ID = "manual-illustration-form"
MANUAL_DATALIST_ID = "known-airlines"

# SUPERSEDED_MARKER_TEXT and DELETE_BUTTON_TEXT are still consumed by
# _airline_card_html()'s chip and _manual_delete_form_html()'s shared
# form.
SUPERSEDED_MARKER_TEXT = "Superseded"
DELETE_BUTTON_TEXT = "Delete"

GAP_CARD_ARIA_TEMPLATE = "Resolve prefix %s — example callsign %s"
MANUAL_CHIP_ACTIVE_TEXT = "Resolved by hand"
MANUAL_DELETE_CAPTION = (
    "Deleting removes this manual name — any uploaded artwork stays in place.")
# %s arity: prefix, built-in name, operator's own name, built-in name
# again. A status message about a real naming conflict, not a caption
# — LIGHTBOX_MANUAL_NOTE_CLASS never composes with the site-wide
# caption-length selector.
MANUAL_SUPERSEDED_NOTE_TEMPLATE = (
    "SkyPane’s built-in list now recognizes prefix %s as “%s” — its "
    "entry wins over the name you gave it (“%s”), so that artwork is "
    "no longer shown. Add artwork for “%s” below, or delete this "
    "entry.")
# Two constants because only the tail is the <a>'s own text; their
# concatenation must equal the copy deck's single string byte-for-byte.
MANUAL_OVERFLOW_TEMPLATE = "%d other unresolved prefixes — "
MANUAL_OVERFLOW_LINK_TEXT = "see the full list"
# With-superseded and no-superseded forms; %d arity is manual count
# then superseded count.
MANUAL_SUMMARY_TEMPLATE = "%d manual resolutions, %d superseded"
MANUAL_SUMMARY_TEMPLATE_NONE = "%d manual resolutions"
# Singular variants avoid "1 manual resolutions" — French and English
# don't agree on the plural boundary, so each language's catalogue
# owns its own singular string.
MANUAL_SUMMARY_TEMPLATE_SINGULAR = "%d manual resolution, %d superseded"
MANUAL_SUMMARY_TEMPLATE_NONE_SINGULAR = "%d manual resolution"

# No revert-to-original control is in scope for this feature.
REPLACE_LABEL_TEXT = "Replace this illustration"
REPLACE_BUTTON_TEXT = "Upload"
# A single static id: exactly one file input exists on the page, so
# there's nothing to disambiguate.
REPLACE_INPUT_ID = "airline-replace-input"
# Single static id, for the same reason REPLACE_INPUT_ID is one: this
# form renders exactly once per page.
REPLACE_FORM_ID = "airline-replace-form"

# Must not contain revert/reset/restore/undo/original — a no-revert-
# control scan in test_status_pages.py checks this form for those words.
REPLACE_HINT_TEXT = "Transparent PNG, at least 1200px wide, landscape."

# variant_chip_label()'s two shape-domain patterns: an alphanumeric
# type code is a letter prefix immediately followed by digits,
# optionally with a hyphenated numeric suffix; anything else is a
# word-form manufacturer shape.
_TYPE_CODE_RE = re.compile(r"^[a-z]+\d[\d-]*$")
_WORD_MODEL_RE = re.compile(r"^([a-z]+)(\d.*)$")


def variant_chip_label(shape):
    """Display transform for one fleet-variant chip. `shape` is a
    free-text filename suffix from `_ILLUSTRATION_TARGETS`, a different
    domain from `illustrations.SHAPE_SLUGS`'s ICAO-type classification
    — this function must never validate `shape` against `SHAPE_SLUGS`
    membership, since values like `"a350-1000"` are real but not
    members themselves.

    An alphanumeric type code upper-cases verbatim (`"a320"` ->
    `"A320"`); a word-form manufacturer shape title-cases, splitting a
    trailing digit-led model number (`"beechcraft1900d"` ->
    `"Beechcraft 1900D"`).
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
    `""` when there's no `state_dir` or no override yet.

    The illustration route serves `Cache-Control: private, max-age=300`;
    keying the suffix on the override file's mtime means the URL changes
    exactly when the bytes change, so a browser cache doesn't show a
    stale image for up to five minutes after a replace. Degrades to no
    cache buster on a vanished or unreadable file rather than raising.
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


def _max_upload_bytes():
    """companion/app.py's `MAX_ILLUSTRATION_UPLOAD_BYTES`, read from that
    module rather than retyped here.

    Imported inside the function because companion/app.py imports this
    module at import time; a module-level import would cycle. The
    client-side cap this feeds is a courtesy only — the server's own
    pre-read cap is the actual gate.
    """
    from companion.app import MAX_ILLUSTRATION_UPLOAD_BYTES
    return MAX_ILLUSTRATION_UPLOAD_BYTES


def _upload_drop_html(input_id):
    """Drag-and-drop affordance and framing preview for the file input
    `input_id`, wrapped in `layout.JS_GATE_CLASS` so a blocked-script
    visitor sees exactly today's form. One definition, three call sites,
    so drop zones cannot render differently in two places.

    The preview box reserves its aspect ratio via an inline
    `--upload-preview-ratio` property — the only way a stylesheet with
    no import path to Python can hold that number. No `<div>` in this
    markup: `test_status_pages.py`'s replace-zone regex matches
    non-greedily and a nested `<div>` would truncate it.
    """
    max_bytes = _max_upload_bytes()
    size_message = i18n.t(UPLOAD_DROP_SIZE_ERROR_TEMPLATE) % (max_bytes // (1024 * 1024))
    return (
        '<section class="%s %s" %s %s="%s" %s="%d" %s="%s" %s="%s" %s="%s">'
        '<p class="%s">%s</p>'
        '<figure class="%s" style="--upload-preview-ratio: %d / %d">'
        '<img class="%s" alt="%s" hidden>'
        "</figure>"
        '<p class="%s">%s</p>'
        '<p class="%s" role="status"></p>'
        "</section>"
    ) % (
        UPLOAD_DROP_CLASS, layout.JS_GATE_CLASS,
        UPLOAD_DROP_ATTR,
        UPLOAD_DROP_INPUT_ATTR, escape_html(input_id),
        UPLOAD_DROP_MAX_BYTES_ATTR, max_bytes,
        UPLOAD_DROP_TYPE_ERROR_ATTR, escape_html(i18n.t(UPLOAD_DROP_TYPE_ERROR_TEXT)),
        UPLOAD_DROP_SIZE_ERROR_ATTR, escape_html(size_message),
        UPLOAD_DROP_MULTIPLE_ERROR_ATTR, escape_html(i18n.t(UPLOAD_DROP_MULTIPLE_ERROR_TEXT)),
        UPLOAD_DROP_NOTE_CLASS, escape_html(i18n.t(UPLOAD_DROP_HINT_TEXT)),
        UPLOAD_DROP_PREVIEW_CLASS,
        ILLUSTRATION_TARGET_WIDTH, ILLUSTRATION_TARGET_HEIGHT,
        UPLOAD_DROP_IMAGE_CLASS, escape_html(i18n.t(UPLOAD_PREVIEW_ALT_TEXT)),
        UPLOAD_DROP_NOTE_CLASS, escape_html(i18n.t(UPLOAD_PREVIEW_CAPTION_TEXT)),
        UPLOAD_DROP_MESSAGE_CLASS,
    )


def _lightbox_replace_form_html():
    """The replace-image control: a plain, JavaScript-free upload form
    wired to `POST /illustration/{key}.png`, living inside the shared
    lightbox and emitted once per page.

    `action=""` is a real, present placeholder — panel-lookup.js
    overwrites it on each trigger click with that card's own action URL;
    with JavaScript unavailable it submits to the current page (a 404),
    a clean, harmless degradation. `accept="image/png"` is a browser-side
    hint only; the route validates by parsing the real PNG header.
    """
    icon_html = layout.icon_html("icon-upload", extra_class=REPLACE_ICON_CLASS)
    return (
        '<form class="%s" id="%s" method="post" enctype="multipart/form-data" action="">'
        '<div class="%s">'
        "%s"
        '<label for="%s">%s</label>'
        '<p class="%s">%s</p>'
        '<input type="file" id="%s" name="image" accept="image/png" required>'
        '<button type="submit">%s</button>'
        "%s"
        "</div>"
        "</form>"
    ) % (
        LIGHTBOX_REPLACE_FORM_CLASS,
        REPLACE_FORM_ID,
        LIGHTBOX_REPLACE_ZONE_CLASS,
        icon_html,
        REPLACE_INPUT_ID,
        i18n.t(REPLACE_LABEL_TEXT),
        REPLACE_HINT_CLASS,
        i18n.t(REPLACE_HINT_TEXT),
        REPLACE_INPUT_ID,
        i18n.t(REPLACE_BUTTON_TEXT),
        _upload_drop_html(REPLACE_INPUT_ID),
    )


# A tag-stripper over layout.concise_timestamp_html()'s own markup, so
# the same call that renders the no-JS path can also fill a data-*
# attribute — never a second date formatter.
_MARKUP_TAG_RE = re.compile(r"<[^>]*>")


def _seen_attribute_text(value, now):
    """The Paris-local text `data-view-panel-first-seen`/`-last-seen`
    carry — the same string the no-JS `<dd>` renders, derived from that
    one formatter call rather than composed a second time.

    Strips the `<span>` wrapper off `layout.concise_timestamp_html(value,
    now, fallback="")`; do not hand-compose a second formatter, which can
    drift from this one. `html.unescape()` runs first since the source is
    pre-escaped; the caller escapes once more at its own attribute site.
    Returns `""` for a falsy `value`; never raises.
    """
    markup = layout.concise_timestamp_html(value, now, fallback="")
    return html_module.unescape(_MARKUP_TAG_RE.sub("", markup))


def _airline_card_html(index, airline_name, shapes, state_dir=None, manual_info=None,
                       now=None):
    """One `.airline-card`: an image behind a click-to-enlarge trigger, the
    airline's name, and one chip per fleet-type variant. Every value is
    escaped exactly once, at its point of interpolation. Returns `""` for
    an airline whose normalised key is falsy.

    `index` becomes `data-filter-group`; `state_dir` resolves the
    illustration cache buster. `manual_info`, when present, is the
    `(prefix, superseded, needs_artwork)` triple sliced by the caller,
    turning the trigger into a resolve link with the manual-state chip.
    """
    key = illustrations.normalise_airline_key(airline_name)
    if not key:
        return ""
    # Built once and reused for both the <img src> and the zoom
    # trigger's data-view-panel-src, plus the cache-busting suffix, so
    # the two cannot point at different images.
    image_url = "%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key))
    # The replace-action attribute deliberately uses the un-busted
    # image_url — a query string on a POST target is pointless. Already
    # escaped once above; do not escape it again here.
    busted_image_url = image_url + _illustration_cache_buster(key, state_dir)
    image_html = (
        '<img class="airline-card__image" src="%s" '
        'width="%d" height="%d" '
        'loading="lazy" decoding="async" alt="%s">'
    ) % (
        busted_image_url,
        ILLUSTRATION_TARGET_WIDTH, ILLUSTRATION_TARGET_HEIGHT,
        escape_html(i18n.t(CARD_IMAGE_ALT_TEMPLATE) % airline_name),
    )
    # Every manual-info-dependent value is derived once here from the
    # sliced (prefix, superseded, needs_artwork) triple, never
    # re-derived from a second lookup.
    has_manual = manual_info is not None
    prefix = superseded = needs_artwork = None
    if has_manual:
        prefix, superseded, needs_artwork = manual_info

    mode = (
        _VIEW_PANEL_MODE_NEEDS_ARTWORK if (has_manual and needs_artwork)
        else _VIEW_PANEL_MODE_ART)
    # A manually-resolved airline with no artwork yet would otherwise
    # render an <img> whose src 404s; use the same dashed placeholder a
    # gap card uses, and an empty src so the dialog hides its image too.
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
        heading_value = i18n.t(STEP_B_HEADING_TEMPLATE) % escape_html(airline_name)
        upload_action_value = "%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key))

    delete_action_value = _manual_delete_action(prefix) if has_manual else ""

    manual_note_value = ""
    if has_manual and superseded:
        # The one sanctioned provenance lookup: the built-in airline's
        # display name for the note template — never re-derives the
        # `superseded` boolean itself.
        built_in_name = enrich.static_airline_name_for_prefix(prefix) or ""
        escaped_built_in_name = escape_html(built_in_name)
        # For a superseded card, `airline_name` is already the built-in
        # name; the operator's own originally-typed name for the note
        # comes from the stored registry entry instead.
        stored_entry = manual_resolutions.load_manual_resolutions(state_dir).get(prefix) or {}
        operator_name = stored_entry.get("airline_name") or airline_name
        manual_note_value = i18n.t(MANUAL_SUPERSEDED_NOTE_TEMPLATE) % (
            escape_html(prefix), escaped_built_in_name,
            escape_html(operator_name), escaped_built_in_name,
        )

    first_seen_value = last_seen_value = count_value = ""
    if mode == _VIEW_PANEL_MODE_NEEDS_ARTWORK:
        gap_row = unresolved_row_for_prefix(state_dir, prefix)
        if gap_row is not None:
            _, gap_count, gap_first_seen, gap_last_seen, _gap_callsign = gap_row
            # Formatted Paris-local text, never the raw registry ISO —
            # see _seen_attribute_text().
            first_seen_value = escape_html(_seen_attribute_text(gap_first_seen, now))
            last_seen_value = escape_html(_seen_attribute_text(gap_last_seen, now))
            count_value = escape_html(gap_count)

    # The per-prefix scope sentence is a raw-gap-only concept; these
    # cards already show a resolved name.
    scope_value = ""

    # A real <button>, not the <img>, is the click target for keyboard
    # focus; panel-lookup.js's delegation still resolves an image click to
    # it. Every trigger carries the full data-view-panel-* vocabulary, with
    # unused attributes left empty rather than omitted, since an omitted
    # attribute is how a stale value could leak from a previous click. A
    # resolve-prefix card becomes a real <a href="?resolve={prefix}"> instead.
    if resolve_prefix_value:
        opening_tag = '<a href="%s?%s=%s" class="airline-card__zoom" ' % (
            AIRLINES_ROUTE, RESOLVE_QUERY_PARAM, resolve_prefix_value)
        closing_tag = "</a>"
    else:
        opening_tag = '<button type="button" class="airline-card__zoom" '
        closing_tag = "</button>"
    # Built once into a variable: the edit-mode Replace control below is
    # a second trigger for the same dialog and must carry an identical
    # vocabulary, or panel-lookup.js's attr-copy idiom would blank the
    # dialog's mode and forms on that second trigger.
    panel_attrs = (
        '%s="%s" %s="%s" %s="%s" %s="%s" '
        '%s="%s" %s="%s" %s="%s" %s="%s" '
        '%s="%s" %s="%s" %s="%s" %s="%s" '
        '%s="%s" %s="%s" '
    ) % (
        _VIEW_PANEL_SRC_ATTR, busted_image_url,
        _VIEW_PANEL_CAPTION_ATTR, escape_html(i18n.t(CARD_IMAGE_ALT_TEMPLATE) % airline_name),
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
    )
    zoom_html = (
        opening_tag + panel_attrs + 'aria-label="%s">%s%s'
    ) % (
        escape_html(i18n.t(ZOOM_LABEL_TEMPLATE) % airline_name),
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
        chip_text = i18n.t(SUPERSEDED_MARKER_TEXT) if superseded else i18n.t(MANUAL_CHIP_ACTIVE_TEXT)
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


def _gallery_grid_html(pairs, state_dir=None, gap_cards_html="", manual_info_by_name=None,
                       now=None):
    """Wraps one `_airline_card_html()` card per `(airline_name, shapes)`
    pair in the `.illustration-grid` container; skips a pair whose card
    comes back empty.

    `gap_cards_html` (default `""`) is prepended inside the same wrapper —
    kept only for call-site parity; a caller should use
    `_gap_strip_html()` instead. `manual_info_by_name` maps a display name
    to its `(prefix, superseded, needs_artwork)` triple, built once by
    `render()`.
    """
    manual_info_by_name = manual_info_by_name or {}
    cards = "".join(
        _airline_card_html(
            index, airline_name, shapes, state_dir,
            manual_info_by_name.get(airline_name), now=now)
        for index, (airline_name, shapes) in enumerate(pairs))
    return '<div class="illustration-grid">%s%s</div>' % (gap_cards_html, cards)


def _gap_rows_for_grid(state_dir, manual_registry=None):
    """Eligible gap rows: every prefix in the live unresolved-callsign-prefix
    registry with `count >= GAP_BLOCK_THRESHOLD`, sorted `(-count, prefix)`,
    capped at `GAP_BLOCK_CAP` shown rows. Never raises.

    Skips a prefix with a manual resolution entry already: the poll state
    and the manual registry update on different schedules, so without this
    exclusion a just-resolved prefix could render two resolve-prefix
    elements, letting the dialog's single-match auto-open grab the stale
    one. `manual_registry`, passed by `render()`, avoids a second read of
    the same file.
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


def _gap_card_html(index, row, now=None):
    """One coverage-gap card: the whole `<a class="airline-card">` element is
    itself the click-to-resolve trigger — no `<img>`, no nested button.

    `row` is one of `_gap_rows_for_grid()`'s five-field tuples; `index`
    becomes `data-filter-group` as `"gap%d"`, string-prefixed so it can't
    collide with the curated grid's integer groups. `example_callsign` is
    coerced to `str()` before `.lower()` runs on it, since a hand-edited
    `poll_state.json` can hold a non-string value there and `.lower()`
    would raise on it uncoerced.
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
        _VIEW_PANEL_HEADING_ATTR, i18n.t(RESOLVE_HEADING),
        _VIEW_PANEL_MODE_ATTR, _VIEW_PANEL_MODE_GAP,
        _VIEW_PANEL_MANUAL_ATTR,
        _VIEW_PANEL_SCOPE_ATTR, i18n.t(RESOLVE_CAPTION_TEMPLATE) % escaped_prefix,
        _VIEW_PANEL_RESOLVE_PREFIX_ATTR, escaped_prefix,
        _VIEW_PANEL_FIRST_SEEN_ATTR, escape_html(_seen_attribute_text(first_seen, now)),
        _VIEW_PANEL_LAST_SEEN_ATTR, escape_html(_seen_attribute_text(last_seen, now)),
        _VIEW_PANEL_COUNT_ATTR, escape_html(count),
        filter_text, index,
        i18n.t(GAP_CARD_ARIA_TEMPLATE) % (escaped_prefix, escaped_callsign),
        escaped_callsign,
    )


def _gap_overflow_html(overflow_count):
    """Overflow line for the gap block, rendered only when
    `_gap_rows_for_grid()`'s cap hid at least one eligible prefix.

    Links to `/health`, not `/airlines`, even though this line renders
    inside Airlines' own gap strip: only Health's unresolved-prefix
    registry table lists every hidden prefix.
    """
    if not overflow_count:
        return ""
    return '<p class="text-label section-caption">%s<a href="/health">%s</a>.</p>' % (
        i18n.t(MANUAL_OVERFLOW_TEMPLATE) % overflow_count, i18n.t(MANUAL_OVERFLOW_LINK_TEXT))


def _gap_strip_html(gap_cards_html, overflow_html):
    """Wraps the coverage-gap cards in their own `<section class="page-section">`
    with `GAP_STRIP_HEADING`/`GAP_STRIP_BODY`, matching
    `health_page.py`'s heading/body constant convention.

    Returns `""` when `gap_cards_html` is empty — no empty section renders
    with no data. `overflow_html` alone can never make this non-empty,
    since `_gap_overflow_html()` only returns non-empty when
    `_gap_rows_for_grid()`'s cap actually hid a row, which cannot happen
    without `gap_cards_html` also being non-empty.
    """
    if not gap_cards_html:
        return ""
    return (
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<div class="illustration-grid illustration-grid--gap">%s</div>'
        "%s"
        "</section>"
    ) % (
        escape_html(i18n.t(GAP_STRIP_HEADING)),
        escape_html(i18n.t(GAP_STRIP_BODY)),
        gap_cards_html,
        overflow_html,
    )


def _lightbox_html():
    """The single shared click-to-enlarge `<dialog>`, emitted once per page
    when at least one card carries a zoom trigger. Mirrors
    `history_page._lightbox_html()`'s element order and classes, plus
    `lightbox--wide` and this module's own `LIGHTBOX_NOTE`.

    Every optional child is a real, present placeholder — empty rather
    than omitted — so `panel-lookup.js` can find and fill it. Neither form
    is emitted `hidden`: which of the replace/delete forms is visible on
    a given open is decided entirely client-side from the trigger's data
    attributes, never here.
    """
    resolve_context_html = _resolve_context_html(None, None, id_suffix="-dialog")
    resolve_name_html = _resolve_name_form_html("", "-dialog", include_submit=False)
    resolve_upload_html = _resolve_upload_form_html("", "-dialog")
    # Both forms are always in the document; panel-lookup.js decides
    # which one a given open shows — see this function's own docstring.
    replace_html = _lightbox_replace_form_html()
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
        '<div class="%s">'
        '<button type="button" %s>%s</button>'
        '<button type="submit" form="%s">%s</button>'
        "</div>"
        "</dialog>"
    ) % (
        LIGHTBOX_DIALOG_ID, escape_html(i18n.t(LIGHTBOX_ARIA_LABEL)), escape_html(i18n.t(LIGHTBOX_NOTE)),
        LIGHTBOX_HEADING_CLASS,
        LIGHTBOX_MANUAL_NOTE_CLASS,
        resolve_context_html,
        resolve_name_html,
        resolve_upload_html,
        replace_html,
        delete_html,
        LIGHTBOX_ACTIONS_CLASS,
        _VIEW_PANEL_CLOSE_ATTR, escape_html(i18n.t("Close")),
        MANUAL_RESOLVE_FORM_ID + "-dialog", escape_html(i18n.t(SAVE_BUTTON_TEXT)),
    )


# Filter-bar copy, driven client-side by list-filter.js's shared
# [data-filter-input]/[data-filter-count]/[data-filter-clear]/
# [data-filter-empty] attribute contract. The Clear control is a real
# <button> (not an anchor), since this gallery carries no read-only
# constraint.
_FILTER_INPUT_ID = "airlines_gallery_filter_input"
_FILTER_LABEL_TEXT = "Filter by airline or callsign"
_FILTER_EMPTY_HEADING = "No matching airlines"
_FILTER_EMPTY_BODY_TEMPLATE = (
    "Try a different search, or Clear filter to see all %d airlines.")


def _filter_bar_html(total, summary_html=""):
    """Filter bar over the gallery, entirely inert without JS —
    list-filter.js's early-return guard leaves the full unfiltered grid
    usable if the script never loads.

    `summary_html` (`_manual_summary_html()`'s rendered control, or `""`)
    sits inside this bar because it's a filter control: clicking it sets
    the bar's own input and reruns `applyFilter()`. The count and Clear
    control are siblings inside one `.filter-bar__meta` group so they wrap
    as a unit rather than separately.
    """
    count_text = i18n.t("%d of %d shown") % (total, total)
    empty_body = i18n.t(_FILTER_EMPTY_BODY_TEMPLATE) % total
    return (
        '<div class="filter-bar">'
        '<label class="text-label" for="%s">%s</label>'
        '<div class="filter-bar__field">'
        "%s"
        # Same Safari contact-autofill fix as history_page.py's
        # _filter_bar_html() — see that file for the attribute explanation.
        '<input type="search" id="%s" autocomplete="off" spellcheck="false" autocapitalize="characters" data-filter-input>'
        "</div>"
        "%s"
        '<div class="filter-bar__meta">'
        '<span class="filter-bar__count" data-filter-count>%s</span>'
        '<button type="button" data-filter-clear>%s</button>'
        "</div>"
        "</div>"
        '<div class="empty-state" data-filter-empty hidden>'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (
        _FILTER_INPUT_ID, escape_html(i18n.t(_FILTER_LABEL_TEXT)),
        layout.icon_html("icon-search"),
        _FILTER_INPUT_ID,
        summary_html,
        escape_html(count_text),
        escape_html(i18n.t("Clear")),
        escape_html(i18n.t(_FILTER_EMPTY_HEADING)),
        escape_html(empty_body),
    )


def unresolved_row_for_prefix(state_dir, prefix):
    """Is `prefix` a real, live member of the unresolved-callsign-prefix
    registry right now? Public because companion/app.py's POST handler
    re-runs this exact function as its own membership check, so the read
    path and the write path can never diverge.

    Validate-then-join over a closed, server-written set: every displayed
    value comes from the tuple this function returns, never from the
    caller's raw query-string value. `prefix` is normalised
    (`manual_resolutions.normalise_prefix()`) at this function's own
    boundary — the one shared membership test, so normalising elsewhere
    would risk disagreement for the same input.

    Returns `None` unless the entry is a well-formed dict with an `int`,
    non-`bool` `count`; otherwise the five-tuple `(prefix, count,
    first_seen, last_seen, example_callsign)`, with `prefix` being the
    normalised value. Never raises.
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
    """The five-row `<dl>` sighting-context block, shared by Step A, Step B
    and the dialog's static copy — one definition, multiple call sites.

    `row=None` (the dialog's call) renders five empty `<dd>`s, filled by
    panel-lookup.js at click time; `now` may then also be `None`, since
    `concise_timestamp_html()` short-circuits on a falsy timestamp first.
    First seen/Last seen render through `concise_timestamp_html()`'s
    already-safe markup, interpolated verbatim; every other value goes
    through `escape_html()` exactly once.
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
        '<dt class="text-label">%s</dt>%s' % (escape_html(i18n.t(label)), dd)
        for label, dd in zip(RESOLVE_CONTEXT_LABELS, pairs)
    )
    return '<dl class="%s">%s</dl>' % (RESOLVE_CONTEXT_CLASS, items)


def _known_airlines_datalist_html(id_suffix=""):
    """A native `<datalist>` offering one `<option>` per
    `illustrations.target_airline_names()`, each `value` escaped once. No
    script is involved.

    `id_suffix` is appended to `MANUAL_DATALIST_ID` so the no-JS
    fallback's copy and the dialog's copy never collide when both render
    at once.
    """
    options = "".join(
        '<option value="%s">' % escape_html(name)
        for name in illustrations.target_airline_names()
    )
    return '<datalist id="%s">%s</datalist>' % (MANUAL_DATALIST_ID + id_suffix, options)


def _resolve_name_form_html(prefix_value, id_suffix, include_submit=True):
    """Step A's name-entry form — one definition, two call sites: the no-JS
    fallback calls this with the real prefix and `id_suffix=""`; the
    dialog calls it with `prefix_value=""` and `id_suffix="-dialog"`, since
    panel-lookup.js fills the hidden prefix input at click time.

    `id_suffix` keeps every emitted id unique between the two simultaneous
    renders. `include_submit` is `True` for the no-JS fallback and `False`
    for the dialog, whose submit lives in the shared `.lightbox__actions`
    row, reattached via `form="manual-resolve-form-dialog"`.
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
        name_input_id, i18n.t(NAME_LABEL_TEXT),
        name_input_id, MANUAL_DATALIST_ID + id_suffix,
        datalist_html,
        i18n.t(NAME_HINT_TEXT),
    )
    submit_html = (
        '<button type="submit">%s</button>' % i18n.t(SAVE_BUTTON_TEXT)
        if include_submit else "")
    return (
        '<form class="%s" id="%s" method="post" action="%s">'
        '<input type="hidden" name="prefix" value="%s">'
        '<p class="lightbox__resolve-scope"></p>'
        "%s"
        "%s"
        "</form>"
        # A permanently empty resolve-scope paragraph: panel-lookup.js
        # writes data-view-panel-scope into it client-side on every open.
    ) % (
        LIGHTBOX_RESOLVE_NAME_CLASS, MANUAL_RESOLVE_FORM_ID + id_suffix, RESOLVE_ROUTE,
        escape_html(prefix_value),
        name_field,
        submit_html,
    )


def _resolve_upload_form_html(action, id_suffix):
    """Step B's upload-zone form — one definition, two call sites: the no-JS
    fallback calls this with the real `/illustration/{key}.png` action and
    `id_suffix=""`; the dialog calls it with `action=""` and
    `id_suffix="-dialog"`, and panel-lookup.js overwrites `action` via
    `setAttribute`.

    `action=""` on the dialog's call is a real, present placeholder, never
    omitted. The drop zone sits inside the `<form>`, since it writes into
    that form's own input.
    """
    upload_input_id = MANUAL_UPLOAD_INPUT_ID + id_suffix
    icon_html = layout.icon_html("icon-upload", extra_class=REPLACE_ICON_CLASS)
    return (
        '<div class="%s">'
        "%s"
        '<label for="%s">%s</label>'
        '<p class="%s">%s</p>'
        '<form id="%s" method="post" enctype="multipart/form-data" action="%s">'
        '<input type="file" id="%s" name="image" accept="image/png" required>'
        '<button type="submit">%s</button>'
        "%s"
        "</form>"
        "</div>"
    ) % (
        RESOLVE_UPLOAD_ZONE_CLASS,
        icon_html,
        upload_input_id, i18n.t("Choose an image"),
        REPLACE_HINT_CLASS, i18n.t(REPLACE_HINT_TEXT),
        MANUAL_UPLOAD_FORM_ID + id_suffix,
        action,
        upload_input_id,
        i18n.t(REPLACE_BUTTON_TEXT),
        _upload_drop_html(upload_input_id),
    )


def _manual_delete_form_html(action):
    """The shared delete form — one definition, two call sites: real pages
    call this with `_manual_delete_action(prefix)`; the dialog calls it
    with `action=""`, overwritten by panel-lookup.js via `setAttribute`.

    Carries no `id_suffix`: its output names no id at all, so two copies
    (dialog + fallback) can coexist with zero collision risk. Do not add
    one it doesn't need.
    """
    return (
        '<form class="%s" method="post" action="%s">'
        '<p class="text-label section-caption">%s</p>'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (LIGHTBOX_DELETE_CLASS, action, i18n.t(MANUAL_DELETE_CAPTION), i18n.t(DELETE_BUTTON_TEXT))


def _resolve_section_html(ctx):
    """The conditional resolve section: `""` when `ctx.get("resolve_prefix")`
    is falsy; otherwise one of several states, decided from server-side
    data alone, never from the raw query-string value past the first
    membership check. Its markup comes from the shared rendering functions
    above, as their no-JS-fallback call site (the dialog is their second).

    A missing live gap row does not mean "nothing to resolve": the
    registry's own cleanup removes a resolved prefix from the live gap
    registry on the next poll cycle, including one a manual entry itself
    just resolved. This function re-validates the prefix and falls through
    to the same manual-registry-driven derivation used when the row is
    still live, with an empty sighting context. Only a prefix with neither
    a live gap nor a manual entry shows the stale sentence. The
    manual-delete form renders only for the two branches that reached a
    stored entry.
    """
    prefix_raw = ctx.get("resolve_prefix")
    if not prefix_raw:
        return ""
    state_dir = ctx.get("state_dir")
    now = ctx.get("now")
    back_link = '<a class="text-label" href="%s">%s</a>' % (
        AIRLINES_ROUTE, i18n.t(RESOLVE_BACK_LINK_TEXT))

    row = unresolved_row_for_prefix(state_dir, prefix_raw)
    if row is not None:
        prefix = row[0]
        context_html = _resolve_context_html(row, now)
    else:
        prefix = manual_resolutions.normalise_prefix(prefix_raw)
        context_html = ""

    if prefix is None:
        body = '<p class="text-body">%s</p>' % i18n.t(RESOLVE_STALE_BODY)
        return '<div class="page-section" data-resolve-fallback>%s%s</div>' % (back_link, body)

    escaped_prefix = escape_html(prefix)

    registry = manual_resolutions.load_manual_resolutions(state_dir)
    entry = registry.get(prefix)

    if entry is None:
        if row is None:
            # Genuinely nothing to resolve: no live gap and no manual entry.
            body = '<p class="text-body">%s</p>' % i18n.t(RESOLVE_STALE_BODY)
            return '<div class="page-section" data-resolve-fallback>%s%s</div>' % (back_link, body)
        # Step A: name not yet saved, so no entry exists and no delete form.
        heading = '<h2 class="text-heading">%s</h2>' % i18n.t(RESOLVE_HEADING)
        caption = '<p class="text-label section-caption">%s</p>' % (
            i18n.t(RESOLVE_CAPTION_TEMPLATE) % escaped_prefix)
        form = _resolve_name_form_html(prefix, "")
        return '<div class="page-section" data-resolve-fallback>%s%s%s%s%s</div>' % (
            back_link, heading, caption, context_html, form)

    # Recompute the key from the stored name — never from the query
    # string, and never re-derive the slug locally.
    airline_name = entry.get("airline_name")
    key = manual_resolutions.illustration_key_for_name(airline_name)
    if not key:
        # Corrupt-file case: a stored name that no longer slugs must
        # not render a form.
        body = '<p class="text-body">%s</p>' % i18n.t(RESOLVE_STALE_BODY)
        return '<div class="page-section" data-resolve-fallback>%s%s</div>' % (back_link, body)

    escaped_name = escape_html(airline_name)
    heading = '<h2 class="text-heading">%s</h2>' % (i18n.t(STEP_B_HEADING_TEMPLATE) % escaped_name)
    # An entry exists past this point in every remaining branch, so the
    # delete form is eligible in both.
    delete_form = _manual_delete_form_html(_manual_delete_action(prefix))

    if illustrations.resolved_illustration_path(key, state_dir) is None:
        # Step B: name already saved, no artwork exists yet.
        caption = '<p class="text-label section-caption">%s</p>' % i18n.t(STEP_B_CAPTION)
        upload_action = "%s%s.png" % (ILLUSTRATION_ROUTE_PREFIX, escape_html(key))
        upload_zone = _resolve_upload_form_html(upload_action, "")
        skip_link = '<a class="text-label" href="%s">%s</a>' % (
            AIRLINES_ROUTE, i18n.t(STEP_B_SKIP_TEXT))
        return '<div class="page-section" data-resolve-fallback>%s%s%s%s%s%s%s</div>' % (
            back_link, heading, caption, context_html, upload_zone, skip_link, delete_form)

    # Already resolved: a bookmark or a Back press landed on a prefix
    # still listed as a gap, but a manual entry already names an airline
    # that has artwork. No controls except delete.
    body = '<p class="text-body">%s</p>' % (i18n.t(RESOLVE_ALREADY_DONE_TEMPLATE) % escaped_name)
    return '<div class="page-section" data-resolve-fallback>%s%s%s%s</div>' % (back_link, heading, body, delete_form)


def _manual_delete_action(prefix):
    """The delete form's `action` attribute for `prefix`, built once here
    so the desktop `<tr>` and the mobile `<li>` can never diverge into
    building two different strings for the same row.
    """
    return "%s%s%s" % (MANUAL_DELETE_ROUTE_PREFIX, escape_html(prefix), MANUAL_DELETE_ROUTE_SUFFIX)


def _manual_resolution_rows(state_dir, registry):
    """`(prefix, airline_name, created_at, superseded, needs_artwork)`
    tuples from an already-loaded `registry`, via
    `manual_resolutions.entry_rows()` (prefix-ascending).

    `superseded` is set when the static table already has an entry for
    `prefix`, whose entry wins at runtime; nothing here mutates the
    registry. `needs_artwork` is `True` only for an active entry whose
    stored name has no resolved artwork yet.
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
    """The summary that replaces the retired standalone management table:
    `""` when `manual_rows` is empty, otherwise a single clickable button
    naming the total count and, if any entry is superseded, the
    superseded count too.

    `manual_rows` is `_manual_resolution_rows()`'s own tuples, passed in by
    `render()`, never recomputed here. `data-filter-set="manual"` is read
    by list-filter.js's `[data-filter-set]` hook: clicking sets the filter
    input to `"manual"` and reruns the existing filter function.
    """
    if not manual_rows:
        return ""
    total = len(manual_rows)
    superseded_count = sum(1 for row in manual_rows if row[3])
    # The singular is chosen off `total`, the only count whose noun
    # inflects here — "%d superseded" is an adjective and reads correctly
    # at every value in both languages.
    singular = (total == 1)
    if superseded_count:
        template = (
            MANUAL_SUMMARY_TEMPLATE_SINGULAR if singular else MANUAL_SUMMARY_TEMPLATE)
        summary_text = i18n.t(template) % (total, superseded_count)
    else:
        template = (
            MANUAL_SUMMARY_TEMPLATE_NONE_SINGULAR if singular else MANUAL_SUMMARY_TEMPLATE_NONE)
        summary_text = i18n.t(template) % total
    return (
        '<button type="button" class="airline-card__chip manual-summary" '
        'data-filter-set="manual">%s</button>') % summary_text


def render(ctx):
    """The Airlines page: page header, then the filter bar (carrying the
    manual-resolutions summary), one card per airline in
    `illustrations.target_variants_by_airline()` order plus any injected
    manual-only card, the "Unidentified airlines" gap strip, the shared
    lightbox dialog, and the conditional resolve section.

    Reads `state_dir`, `now`, `resolve_prefix` and `manual_resolutions`
    from `ctx` with `ctx.get()`, never `ctx[...]` — `render({})` must
    still render the plain gallery. Opens no database; the filter bar and
    lightbox render whenever at least one card exists, and the manual
    summary has its own independent empty-registry gate.
    """
    # ctx.get(): test_view_pages.py calls render({}) with a literal
    # empty dict, and every real caller supplies state_dir.
    state_dir = ctx.get("state_dir")
    # Read once and threaded into every card builder, so the JS path's
    # data-* text and the no-JS path's rendered text come from one value
    # and cannot disagree.
    now = ctx.get("now")
    resolve_html = _resolve_section_html(ctx)
    pairs = illustrations.target_variants_by_airline()

    # Loaded once here and threaded into _gap_rows_for_grid() below, so
    # one render() call reads manual_resolutions.json exactly once.
    registry = ctx.get("manual_resolutions")
    if registry is None:
        registry = manual_resolutions.load_manual_resolutions(state_dir) if state_dir else {}
    manual_rows = _manual_resolution_rows(state_dir, registry)

    gap_shown, gap_overflow_count = _gap_rows_for_grid(state_dir, registry)
    gap_cards_html = "".join(
        _gap_card_html(i, row, now=now) for i, row in enumerate(gap_shown))
    overflow_html = _gap_overflow_html(gap_overflow_count)
    gap_strip_html = _gap_strip_html(gap_cards_html, overflow_html)

    # manual_info_by_name maps a card's display name to its own
    # (prefix, superseded, needs_artwork) triple — a superseded row's name
    # is the built-in airline's name, an active row's is its own stored
    # name; only the first occurrence of a name is kept. An entry only
    # earns an injected card when its stored name still resolves to a key.
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
    lightbox_html = _lightbox_html() if (pairs or gap_shown) else ""
    summary_html = _manual_summary_html(manual_rows)
    filter_html = _filter_bar_html(total, summary_html) if (pairs or gap_shown) else ""
    return (
        layout.page_header(i18n.t("Airlines"), purpose=i18n.t(GALLERY_PURPOSE_TEXT))
        + filter_html
        + _gallery_grid_html(
            pairs, state_dir, manual_info_by_name=manual_info_by_name, now=now)
        + gap_strip_html
        + lightbox_html
        + resolve_html
    )
