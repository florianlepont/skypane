# SPDX-License-Identifier: AGPL-3.0-only
"""The Battery page's full-page composition, kept for the render-level tests of
the battery row and the charts that the Fleet page still uses. The server
serves the row inside the Fleet page; `render` exists here only so those
builders can be checked in a page-shaped arrangement.
"""
from companion import health_rows, i18n, layout, page_context
from companion.pages import health_page


def render(ctx):
    ctx = page_context.coerce(ctx)
    parts = health_page.battery_view(ctx)
    heading = i18n.t(health_page.ROW_BATTERY_NAME)
    if parts.empty_html:
        return (
            '<div class="status-page">'
            + layout.page_header(heading) + parts.empty_html + "</div>")
    return (
        '<div class="status-page">'
        + layout.page_header(heading)
        + health_rows.card_html(parts.row_html)
        + "</div>")
