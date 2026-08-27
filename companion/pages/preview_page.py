"""companion/pages/preview_page.py — CFG-10 (live panel preview) and
CFG-11 (render gallery), 06-CONTEXT.md.

This plan (06-05) ships the <img> element pointing at companion/app.py's
real, live-wired GET /preview.png route (server.panel_preview already
exists per plan 06-03) plus the CFG-11 gallery empty state as a
contract-complete stub; plan 06-09 replaces the gallery section with a
real listing built from companion/app.py's gallery_entries().
"""
from companion.layout import empty_state

_NO_RENDERS_HEADING = "No renders yet."
_NO_RENDERS_BODY = (
    "Trigger a poll above, or wait for the next scheduled cycle, to "
    "populate the gallery.")

# D-P2-03 (server/panel_preview.py's own module docstring): the preview
# PNG's colours are nominal render-internal swatches, not colour-accurate
# against real Spectra 6 glass — this caption carries that caveat forward
# to the one place a human actually looks at the image.
_COLOUR_CAVEAT_TEXT = (
    "Colours are nominal render-internal swatches, not colour-accurate "
    "against real Spectra 6 glass.")


def render(ctx):
    return (
        '<h1 class="text-heading">Preview</h1>'
        '<section class="page-section">'
        '<h2 class="text-heading">Live preview</h2>'
        '<img class="preview-image" src="/preview.png" '
        'alt="Current panel preview">'
        '<p class="text-label">%s</p>'
        "</section>"
        '<section class="page-section">'
        '<h2 class="text-heading">Gallery</h2>'
        "%s"
        "</section>"
    ) % (_COLOUR_CAVEAT_TEXT, empty_state(_NO_RENDERS_HEADING, _NO_RENDERS_BODY))
