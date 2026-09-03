"""companion/pages/airlines_page.py — an illustration gallery over the
panel renderer's own airline art (D-13 through D-17, 06.6.4.1-CONTEXT.md).

Presentation-only: reads exactly one public accessor,
`server.plane.illustrations.target_variants_by_airline()`, and touches no
database and no poll-state file — the gallery renders the full static
curated list from `_ILLUSTRATION_TARGETS`, never a detection-history
cross-reference (D-17: this module opens no database and reads no poll
state).

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
app that renders them (D-13). A reader hunting for that content should
look there, not here. This move is complete as of plan 06 Task 3: this
module no longer imports the history-database module or the poll-state
module, and opens no database connection of any kind.
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
# Task 4).
_VIEW_PANEL_REPLACE_ACTION_ATTR = "data-view-panel-replace-action"
LIGHTBOX_REPLACE_FORM_CLASS = "lightbox__replace"

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

    None of `REPLACE_LABEL_TEXT`, `REPLACE_BUTTON_TEXT` or
    `REPLACE_INPUT_ID` interpolates any external value, so no
    `escape_html()` call is needed here — unlike the retired per-card
    version, nothing hostile can reach this function's output.
    """
    return (
        '<form class="%s" method="post" enctype="multipart/form-data" action="">'
        '<label for="%s">%s</label>'
        '<input type="file" id="%s" name="image" accept="image/png" required>'
        '<button type="submit">%s</button>'
        "</form>"
    ) % (
        LIGHTBOX_REPLACE_FORM_CLASS,
        REPLACE_INPUT_ID,
        REPLACE_LABEL_TEXT,
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
_FILTER_LABEL_TEXT = "Filter by airline name"
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


def render(ctx):
    """The Airlines gallery (D-13 through D-17): the page header, the
    D-16 filter bar, then one card per airline in
    `illustrations.target_variants_by_airline()` order, then the shared
    click-to-enlarge lightbox dialog (quick task 260902-tli). `ctx` is
    accepted for call-site parity with every other page module's
    `render(ctx)` signature; since quick task 260902-v26 it reads exactly
    one optional key, `state_dir`, used only to resolve each card's
    illustration-replace cache buster (see `_illustration_cache_buster()`)
    — this page still opens no database and reads no poll state.

    The filter bar and the lightbox dialog both render only when there
    is at least one card — this codebase's consistent "no chrome with no
    data" rule — though with a static curated list that branch is
    unreachable today; it stays a genuine guard, not a claim that the
    list can ever be empty.
    """
    # ctx.get(), never ctx["state_dir"]: companion/test_view_pages.py:1365
    # calls render({}) with a literal empty dict, and every other caller
    # of this page (companion/app.py's page_context()) does supply
    # state_dir, so this must stay tolerant of both.
    state_dir = ctx.get("state_dir")
    pairs = illustrations.target_variants_by_airline()
    filter_html = _filter_bar_html(len(pairs)) if pairs else ""
    lightbox_html = _lightbox_html() if pairs else ""
    return (
        layout.page_header("Airlines", purpose=GALLERY_PURPOSE_TEXT)
        + filter_html
        + _gallery_grid_html(pairs, state_dir)
        + lightbox_html
    )
