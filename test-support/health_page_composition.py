"""The retired Health page's full-page composition, kept for the render-level
tests of the row and banner builders that the Fleet page
still uses. The server no longer serves this page: `render` exists here only
so those builders can be checked in the arrangement they used to be shown in.
"""
from companion import console_routes, layout, page_context
from companion import i18n
from companion.pages import health_page


def render(ctx):
    from companion import health_rows
    ctx = page_context.coerce(ctx)
    parts = health_page._page_parts(ctx)
    heading = i18n.t(console_routes.HEALTH_LABEL)
    if parts is None:
        return (
            '<div class="status-page">'
            + layout.page_header(heading)
            + health_page._never_seen_html()
            + "</div>")
    rows_card_html = health_rows.card_html(
        health_rows.group_html(
            health_page.SCREEN_SECTION_ID, i18n.t(health_page.SCREEN_SECTION_HEADING),
            parts["screen_rows"])
        + parts["server_group_html"])
    return (
        '<div class="status-page">'
        + layout.page_header(heading)
        + parts["source_fault_html"]
        + parts["unreachable_html"] + parts["banner_html"]
        + rows_card_html
        + "</div>"
    )
