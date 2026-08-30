"""companion/pages/preview_page.py — CFG-10 (live panel preview) and
CFG-11 (render gallery), 06-CONTEXT.md D-20.

Completed by plan 06-09. Imports `server.panel_preview` and
`companion.layout` only — this module must never import `companion.app`
(a page importing the router it is rendered by would be a cycle); the
router instead puts the gallery entry list into `ctx["gallery_entries"]`
(`companion.app.Handler.page_context()`), built from the router's own
`gallery_entries()` listing helper. Every gallery URL this page builds is
constructed only from a name that helper returned — the page never joins
a path itself (T-06-09-02).

Deferred idea, explicitly not built here (06-CONTEXT.md's Deferred Ideas
section): a form letting the user type a callsign or force a state to
preview was proposed during discussion and explicitly not selected. This
page contains no such control and no form-input element of any kind — do
not add one back as an "obvious improvement" without re-opening that
discussion.
"""
from companion.layout import absolute_and_relative, empty_state, escape_html
from server import panel_preview

# D-P2-03 / server/panel_preview.py's own module docstring: the preview
# PNG's colours are nominal render-internal swatches, not colour-accurate
# against real Spectra 6 glass — two of the six are still explicitly
# interim pending Phase 7's on-glass calibration. This caveat is not
# optional politeness: without it a user comparing this image to the
# frame on the wall could mistake an expected preview/glass colour
# mismatch for a hardware fault.
COLOUR_CAVEAT = (
    "Colours are nominal render-internal swatches, not colour-accurate "
    "against real Spectra 6 glass.")

_NO_PANEL_CAPTION = "No panel has been rendered yet."
PREVIEW_CAPTION = "Captured %s"

_NO_RENDERS_HEADING = "No renders yet."
_NO_RENDERS_BODY = (
    "Trigger a poll above, or wait for the next scheduled cycle, to "
    "populate the gallery.")

# D-20: "the last several renders" for quick visual QA — a display cap,
# independent of however many files companion.app.gallery_entries()
# itself already limited its own listing to.
GALLERY_DISPLAY_LIMIT = 12

_PREVIEW_IMAGE_ROUTE = "/preview.png"  # Literal, not imported from
# companion.app (that import would be the forbidden cycle) — matches the
# route companion/app.py's PREVIEW_IMAGE_ROUTE constant defines.
_GALLERY_ROUTE_PREFIX = "/gallery/"


def preview_section(ctx):
    """The live-preview `<section>` body: an `<img>` pointing at the
    preview route plus a captured-at caption when a panel exists, or a
    short honest sentence with no `<img>` at all when it does not — a
    broken image element is worse than an honest sentence. The colour
    caveat is always present, since this section is always shown one way
    or the other.
    """
    mtime_iso = panel_preview.panel_file_mtime_iso(ctx["state_dir"])

    if mtime_iso:
        image_html = (
            '<img class="preview-image" src="%s" '
            'alt="Current panel preview">' % _PREVIEW_IMAGE_ROUTE)
        # panel_file_mtime_iso() returns a Z-suffixed ISO string while
        # ctx["now"] is +00:00-suffixed; datetime.fromisoformat() parses
        # both into timezone-aware values on this project's interpreter
        # (verified during planning against server/.venv/bin/python3,
        # CPython 3.11.15 — the Z suffix has been accepted since 3.11),
        # so subtracting them raises nothing and no normalising shim is
        # needed.
        caption_text = PREVIEW_CAPTION % absolute_and_relative(mtime_iso, ctx.get("now"))
    else:
        image_html = ""
        caption_text = _NO_PANEL_CAPTION

    caption_html = '<p class="text-label mono">%s</p>' % escape_html(caption_text)
    caveat_html = '<p class="text-body">%s</p>' % escape_html(COLOUR_CAVEAT)
    return image_html + caption_html + caveat_html


def gallery_tiles(ctx):
    """The gallery `<section>` body: a capped, newest-first grid of
    thumbnail tiles built only from names in `ctx["gallery_entries"]`
    (the router's own listing helper's return value — T-06-09-02), or
    the render-gallery empty state when that list is empty.
    """
    entries = ctx.get("gallery_entries") or []
    limited = entries[:GALLERY_DISPLAY_LIMIT]

    if not limited:
        return empty_state(_NO_RENDERS_HEADING, _NO_RENDERS_BODY)

    tiles = []
    for name in limited:
        escaped_name = escape_html(name)
        caption = name[:-4] if name.endswith(".png") else name
        tiles.append(
            '<div class="gallery-tile">'
            '<img src="%s%s" alt="Rendered panel %s">'
            '<p class="text-label mono">%s</p>'
            "</div>"
            % (_GALLERY_ROUTE_PREFIX, escaped_name, escaped_name,
               escape_html(caption))
        )
    return '<div class="gallery-grid">%s</div>' % "".join(tiles)


def render(ctx):
    return (
        '<h1 class="text-heading">Preview</h1>'
        '<section class="page-section">'
        '<h2 class="text-heading">Live preview</h2>'
        "%s"
        "</section>"
        '<section class="page-section">'
        '<h2 class="text-heading">Gallery</h2>'
        "%s"
        "</section>"
    ) % (preview_section(ctx), gallery_tiles(ctx))
