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
import re

from companion.layout import empty_state, escape_html
import companion.layout as layout
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

# D-09/06.6.3-07: the panel-present caption's "Captured " prefix used to
# live in a module constant (`PREVIEW_CAPTION = "Captured %s"`) applied to
# a plain-text `caption_text` that was then escaped once, at the shared
# `caption_html` line. That structure cannot host
# `layout.concise_timestamp_html()`'s own pre-built <span> markup without
# double-encoding it, so the panel-present branch below now builds
# `caption_html` directly with an inline "Captured %s" format string
# instead — retiring the module constant rather than leaving it pointing
# at dead code. The no-panel branch's own caption text is unaffected and
# still goes through escape_html() exactly as before.

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

# The source panel's real pixel dimensions (server/panel_format.py's
# documented 1200x1600 output size) — reused for both the live-preview
# <img> (UXA-16, eager/above-the-fold) and every gallery thumbnail
# (UXA-16, lazy/off-screen, added by this plan's Task 2). Naming these
# once means the two call sites cannot drift from each other or from the
# real panel size.
_PANEL_WIDTH = 1200
_PANEL_HEIGHT = 1600

# D-22/06.6.3-RESEARCH.md Pitfall 2: server/poll_loop.py::_save_to_gallery()
# names each gallery file `now_iso.replace(":", "-") + ".png"` — sanitising
# every colon in the ISO string, not just the ones in the time portion. A
# naive full-string `.replace("-", ":")` reversal would also mangle the
# DATE portion's own hyphens (e.g. "2026-08-30" -> "2026:08:30"), so the
# reversal below only ever touches the time+offset portion, matched by
# this exact regex against the substring after the first "T".
_GALLERY_TIME_PATTERN = re.compile(
    r"^(\d{2})-(\d{2})-(\d{2})([+-]\d{2})-(\d{2})$")

# D-10: the Gallery heading's own stated display window, read from
# GALLERY_DISPLAY_LIMIT itself rather than a re-typed literal — a future
# change to that constant's value is reflected here automatically.
GALLERY_HEADING = 'Gallery <span class="text-label">— Latest %d renders</span>'


def _gallery_name_to_iso(name):
    """Reverse `_save_to_gallery()`'s ':' -> '-' filename sanitisation, or
    return None (never raising) on any name that doesn't match the exact
    expected shape.

    A manually-dropped or renamed file in the gallery directory is not
    attacker-reachable over the network (T-06.6.3-14), but this function
    must still degrade safely on an unexpected shape: a missing "T"
    separator, or a time+offset portion that doesn't match
    `_GALLERY_TIME_PATTERN`, both return None rather than raising —
    `gallery_tiles()` below falls back to the raw-filename caption in
    either case.
    """
    stem = name[:-4] if name.endswith(".png") else name
    if "T" not in stem:
        return None
    date_part, _, time_part = stem.partition("T")
    match = _GALLERY_TIME_PATTERN.match(time_part)
    if not match:
        return None
    hh, mm, ss, tz_sign_hh, tz_mm = match.groups()
    return "%sT%s:%s:%s%s:%s" % (date_part, hh, mm, ss, tz_sign_hh, tz_mm)


def preview_section(ctx):
    """The live-preview `<section>` body: an `<img>` (inside a bounded,
    centered matte frame, D-18) pointing at the preview route plus a
    captured-at caption when a panel exists, or a short honest sentence
    with no `<img>`/frame at all when it does not — a broken image
    element is worse than an honest sentence. The colour caveat is
    always present, since this section is always shown one way or the
    other.
    """
    mtime_iso = panel_preview.panel_file_mtime_iso(ctx["state_dir"])

    if mtime_iso:
        image_html = (
            '<div class="preview-frame">'
            '<img class="preview-image" src="%s" '
            'width="%d" height="%d" loading="eager" decoding="async" '
            'alt="Current panel preview"></div>'
        ) % (_PREVIEW_IMAGE_ROUTE, _PANEL_WIDTH, _PANEL_HEIGHT)
        # panel_file_mtime_iso() returns a Z-suffixed ISO string while
        # ctx["now"] is +00:00-suffixed; datetime.fromisoformat() parses
        # both into timezone-aware values on this project's interpreter
        # (verified during planning against server/.venv/bin/python3,
        # CPython 3.11.15 — the Z suffix has been accepted since 3.11),
        # so subtracting them raises nothing and no normalising shim is
        # needed. concise_timestamp_html() already returns safe, raw
        # markup (D-09) — interpolated verbatim here, never re-escaped,
        # which is why this branch builds caption_html directly instead
        # of going through a shared escape_html(caption_text) step.
        caption_html = (
            '<p class="text-label mono">Captured %s</p>'
            % layout.concise_timestamp_html(mtime_iso, ctx.get("now")))
    else:
        image_html = ""
        # The no-panel caption carries no markup of its own, so it still
        # goes through escape_html() exactly as before this plan.
        caption_html = (
            '<p class="text-label mono">%s</p>' % escape_html(_NO_PANEL_CAPTION))

    caveat_html = '<p class="text-body">%s</p>' % escape_html(COLOUR_CAVEAT)
    return image_html + caption_html + caveat_html


def gallery_tiles(ctx):
    """The gallery `<section>` body: a capped, newest-first grid of
    thumbnail tiles built only from names in `ctx["gallery_entries"]`
    (the router's own listing helper's return value — T-06-09-02), or
    the render-gallery empty state when that list is empty.

    Each tile's `<img>` carries UXA-16's lazy-loading/sizing hints and is
    wrapped in a same-src `<a>` for native open/zoom (no new route — the
    existing `/gallery/{name}.png` route already serves the full-size
    file). Each caption reads "Captured {concise timestamp}" (D-22) when
    `_gallery_name_to_iso()` can recover a real timestamp from the
    filename, or degrades to the existing raw-filename-derived caption
    (still escaped) when it cannot — never a crash, never a blank
    caption.
    """
    entries = ctx.get("gallery_entries") or []
    limited = entries[:GALLERY_DISPLAY_LIMIT]

    if not limited:
        return empty_state(_NO_RENDERS_HEADING, _NO_RENDERS_BODY)

    tiles = []
    for name in limited:
        escaped_name = escape_html(name)
        href = "%s%s" % (_GALLERY_ROUTE_PREFIX, escaped_name)
        iso = _gallery_name_to_iso(name)
        if iso is not None:
            caption_html = (
                "Captured %s" % layout.concise_timestamp_html(iso, ctx.get("now")))
        else:
            raw_caption = name[:-4] if name.endswith(".png") else name
            caption_html = escape_html(raw_caption)
        tiles.append(
            '<div class="gallery-tile">'
            '<a href="%s">'
            '<img src="%s" width="%d" height="%d" loading="lazy" '
            'decoding="async" alt="Rendered panel %s"></a>'
            '<p class="text-label mono">%s</p>'
            "</div>"
            % (href, href, _PANEL_WIDTH, _PANEL_HEIGHT, escaped_name, caption_html)
        )
    return '<div class="gallery-grid">%s</div>' % "".join(tiles)


def render(ctx):
    return (
        layout.page_header("Preview")
        + '<section class="page-section">'
        '<h2 class="text-heading">Live preview</h2>'
        "%s"
        "</section>"
        '<section class="page-section">'
        '<h2 class="text-heading">%s</h2>'
        "%s"
        "</section>"
    ) % (
        preview_section(ctx), GALLERY_HEADING % GALLERY_DISPLAY_LIMIT,
        gallery_tiles(ctx),
    )
