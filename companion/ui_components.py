"""companion/ui_components.py: the shared, escaped HTML component library —
banners, status dots/rows, stat tiles, the quick-switch control pair, the
Frame strip (home_page.py's and config_page.py's shared Display summary),
the page header and the generic data table. Depends on companion.ui_base
for escaping/icon lookup and the quick-action/frame-strip constant tables,
and on companion.ui_time for the timestamp parsing and relative-time
element frame_strip_html() renders; no import from ui_nav or ui_shell.
"""
import companion.frame_state as frame_state
import companion.i18n as i18n
import companion.page_context as page_context
import companion.wake as wake
from companion.ui_base import (
    DISPLAY_ROUTE,
    FLASH_SLOT_MARKER,
    FRAME_STRIP_HEADING,
    QUICK_ACTION_OFF_TEXT,
    QUICK_ACTION_ON_TEXT,
    QUICK_ACTION_QUIET_LABEL,
    QUICK_ACTION_QUIET_OFF_TEXT,
    QUICK_ACTION_QUIET_ON_TEMPLATE,
    QUICK_ACTION_SCREEN_LABEL,
    QUICK_STATE_FIELD,
    QUICK_STATE_OFF,
    QUICK_STATE_OFF_ATTR,
    QUICK_STATE_ON,
    QUICK_STATE_ON_ATTR,
    QUICK_SWITCH_CONTROL_ATTR,
    QUICK_SWITCH_QUIET_LABEL_ID,
    QUICK_SWITCH_QUIET_STATE_ID,
    QUICK_SWITCH_REGION_ATTR,
    QUICK_SWITCH_SCREEN_LABEL_ID,
    QUICK_SWITCH_SCREEN_STATE_ID,
    STAT_TILE_ICON_CLASS,
    _CARD_STATUS_SUFFIXES,
    _DEFAULT_STATUS_DOT_CLASS,
    _DEFAULT_STAT_TILE_CLASS,
    _FRAME_DELAY_DUE_TEXT,
    _FRAME_DELAY_HELD_TEXT,
    _FRAME_DELAY_UNKNOWN_TEXT,
    _FRAME_DOT_CLASS_BY_STATE,
    _FRAME_HEADLINE_DUE_TEXT,
    _FRAME_HEADLINE_HELD_TEXT,
    _FRAME_HEADLINE_LATE_TEXT,
    _FRAME_QUIET_SCHEDULE_LINK_TEXT,
    _FRAME_QUIET_SCHEDULE_TARGET_ID,
    _STATUS_DOT_CLASSES,
    _STAT_TILE_BORDER_CLASSES,
    escape_html,
    icon_html,
)
from companion.ui_time import local_clock_text, parse_iso, relative_time_html

_FLASH_ROLES = {"status", "alert"}


def flash_banner(message, role="status"):
    """An accent-bordered confirmation block for a save confirmation.

    `role` is validated against `_FLASH_ROLES` (falling back to "status"),
    rendered as the `<div>`'s ARIA role: `role="alert"` (assertive) for a
    save/poll failure, `role="status"` (polite) otherwise, chosen by the
    caller's severity.
    """
    resolved_role = role if role in _FLASH_ROLES else "status"
    return (
        '<div class="banner banner--flash" role="%s">%s</div>'
        % (resolved_role, escape_html(message)))


def anomaly_banner(message, severity="error"):
    """A warning/destructive-bordered block for anomaly flagging.

    `severity` chooses both the CSS class and ARIA role: `"error"` (default)
    renders `banner--anomaly`/`role="alert"`; `"warn"` renders
    `banner--warn`/`role="status"` — a warning-only state announces politely,
    not as an assertive interruption.
    """
    css_class = "banner--anomaly" if severity == "error" else "banner--warn"
    role = "alert" if severity == "error" else "status"
    return (
        '<div class="banner %s" role="%s">%s</div>'
        % (css_class, role, escape_html(message)))


def status_dot(state, label, title=None, visually_hide_label=False):
    """A small coloured status indicator plus an escaped text label.

    `state` maps to one of three fixed CSS class suffixes; an unrecognised
    value falls back to the warning class rather than emitting an arbitrary
    class name.

    `title` is optional; when falsy no `title` attribute is emitted (backward
    compatible with two-positional-argument call sites). When truthy it is
    escaped through escape_html() and added as `title="..."` on the label span.

    `visually_hide_label` is a keyword-with-default, byte-identical-when-falsy
    parameter: only Flights' Corroboration cell passes True, which keeps the
    dot and its accessible name/title but hides the visible word so the column
    can shrink to a dot-only width.
    """
    css_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    title_attr = ' title="%s"' % escape_html(title) if title else ""
    label_class = "dot-label visually-hidden" if visually_hide_label else "dot-label"
    # With the label clipped away, a title on that span is unreachable by
    # hover, so it moves onto the dot itself, the only visible element left.
    # Default (label visible) output stays byte-identical.
    dot_title = title_attr if visually_hide_label else ""
    label_title = "" if visually_hide_label else title_attr
    return (
        '<span class="dot %s"%s></span><span class="%s"%s>%s</span>'
        % (css_class, dot_title, label_class, label_title, escape_html(label)))


def stat_tile(caption, content_html, status=None, icon=None, caption_title=None):
    """A status-coloured dashboard card wrapping already-built markup.

    `caption` is escaped here. `content_html` is the caller's own
    already-safe markup, interpolated verbatim with no re-escaping —
    re-encoding it would double-encode already-escaped tags. `status`
    maps to one of three fixed CSS class suffixes; an unrecognised value
    falls back to the neutral class rather than an arbitrary class name.

    `icon` is a whitelisted ICON_IDS id, not markup, passed to
    icon_html() — this function's only other route to raw HTML.
    `caption_title` is an attribute value, escaped through the same
    escape_html() call as `caption`, and added as `title="..."` on the
    caption label.
    """
    css_class = "stat-tile " + _STAT_TILE_BORDER_CLASSES.get(
        status, _DEFAULT_STAT_TILE_CLASS)
    icon_markup = icon_html(icon, extra_class=STAT_TILE_ICON_CLASS) if icon else ""
    if icon_markup:
        caption_html = icon_markup + "<span>%s</span>" % escape_html(caption)
    else:
        caption_html = escape_html(caption)
    title_attr = ' title="%s"' % escape_html(caption_title) if caption_title else ""
    return (
        '<div class="%s">'
        '<p class="text-label stat-tile__caption"%s>%s</p>'
        "%s"
        "</div>"
    ) % (css_class, title_attr, caption_html, content_html)


def quick_switch_html(action, return_to, is_on, label_id, state_id, form_id=None):
    """One real `role="switch"` control, shared verbatim by the Frame
    strip's two switches and the Device page's Diagnostic LED, so their
    markup, ARIA and posts cannot drift. `return_to` is written escaped;
    the server validates it against a whitelist before redirecting.

    `is_on` is the saved value: it sets `aria-checked` and the posted
    `state`, always the opposite — with scripts blocked, a switch must
    post the flip, not re-assert its state. `form_id` is for the one
    caller whose switch cannot contain its own form (nested forms are
    invalid HTML): renders the button only, attached via `form=`.
    """
    button_html = (
        '<button type="submit" class="switch" role="switch" aria-checked="%s"'
        ' aria-labelledby="%s" aria-describedby="%s" %s%s>'
        '<span class="switch__track" aria-hidden="true">'
        '<span class="switch__thumb"></span></span>'
        "</button>"
    ) % (
        "true" if is_on else "false",
        escape_html(label_id), escape_html(state_id),
        QUICK_SWITCH_CONTROL_ATTR,
        (' form="%s"' % escape_html(form_id)) if form_id else "",
    )
    if form_id:
        return button_html
    next_state = QUICK_STATE_OFF if is_on else QUICK_STATE_ON
    return (
        '<form method="post" action="%s" class="quick-action__form" data-quick-switch>'
        '<input type="hidden" name="%s" value="%s">'
        '<input type="hidden" name="return_to" value="%s">'
        "%s"
        "</form>"
    ) % (
        escape_html(action),
        QUICK_STATE_FIELD, escape_html(next_state),
        escape_html(return_to),
        button_html,
    )


def quick_switch_state_html(state_id, on_text, off_text, is_on, extra_class=""):
    """The visible state beside a switch: both wordings, server-rendered and
    translated, with exactly one `hidden`.

    Keeps companion/static/quick-switch.js free of user-facing copy: an
    optimistic flip and its rollback are a pure attribute change over text the
    server already produced in the reader's own language. `hidden` is honoured
    with or without scripts, so a scripts-blocked reader sees exactly one
    state word.
    """
    css_class = "text-body quick-action__state"
    if extra_class:
        css_class = css_class + " " + extra_class
    return (
        '<span class="%s" id="%s">'
        '<span %s%s>%s</span>'
        '<span %s%s>%s</span>'
        "</span>"
    ) % (
        css_class, escape_html(state_id),
        QUICK_STATE_ON_ATTR, "" if is_on else " hidden", escape_html(on_text),
        QUICK_STATE_OFF_ATTR, " hidden" if is_on else "", escape_html(off_text),
    )


def _frame_strip_cell_html(extra_class, label_row_html, state_row_html, caption_row_html,
                           extra_attrs=""):
    """One Frame-strip cell wrapper: every cell (both switches and the update
    cell) is the same wrapper with the same three-row structure (label,
    state-plus-control, caption); only `extra_class` and each row's content
    differ. A row with nothing to put in it still emits that row's own empty
    div, never an omitted row, so all three cells' rows line up.

    A harness asserts the three cells' row class attributes are
    byte-identical; the outer wrapper's class list legitimately differs —
    only the switch cells carry the `quick-action`/`quick-action--on/off`
    control-state edge.
    """
    cell_class = "frame-strip__cell"
    if extra_class:
        cell_class = cell_class + " " + extra_class
    # `extra_attrs` carries QUICK_SWITCH_REGION_ATTR on the two switch cells and
    # nothing on the update cell — the region companion/static/quick-switch.js
    # marks pending while its fetch is in flight, and freshness.js's swap
    # already skips when it is.
    return (
        '<div class="%s"%s>'
        '<div class="frame-strip__row frame-strip__row--label">%s</div>'
        '<div class="frame-strip__row frame-strip__row--state">%s</div>'
        '<div class="frame-strip__row frame-strip__row--caption">%s</div>'
        "</div>"
    ) % (cell_class, (" " + extra_attrs) if extra_attrs else "",
         label_row_html, state_row_html, caption_row_html)


def _frame_resolved_state(ctx):
    """The one state resolution shared by every cell below: `(resolved_state,
    headline_template_value, delay_template_value, resolved_next_wake_iso,
    next_wake_clock, now_value)`, computed once via wake.next_wake_status()
    against the same fields every caller already reads.

    `battery_critical` is the battery-empty latch, read once per request by
    build_page_context() — never a second read here. Without it, a parked
    frame would cross the warn threshold every wake cycle and wrongly
    announce "late" on a flat battery.

    `ctx` arrives already a `PageContext` — coerced once, by this
    function's own public caller, `frame_strip_html()`.
    """
    device_cfg = ctx.device_config or {}
    now_value = ctx.now
    battery_critical = ctx.battery_critical if ctx.battery_critical is not None else False
    resolved_next_wake_iso, effective_interval_s, hold_reason = wake.next_wake_status(
        ctx.last_checkin_ts, device_cfg, battery_critical=battery_critical)
    resolved_state = frame_state.resolve_state(
        resolved_next_wake_iso, effective_interval_s, hold_reason, now_value)
    headline_template_value = frame_state.headline_template(resolved_state)
    delay_template_value = frame_state.delay_sentence_template(
        resolved_next_wake_iso, effective_interval_s, hold_reason, now_value)
    next_wake_clock = None
    if resolved_next_wake_iso:
        next_wake_parsed = parse_iso(resolved_next_wake_iso)
        if next_wake_parsed is not None:
            next_wake_clock = local_clock_text(next_wake_parsed, now_parsed=parse_iso(now_value))
    return (
        resolved_state, headline_template_value, delay_template_value,
        resolved_next_wake_iso, next_wake_clock, now_value)


def _frame_delay_caption_html(delay_template_value, next_wake_clock):
    """The one computed delay sentence, shared verbatim by both switch
    cells' captions (the Quiet cell appends its own schedule link after
    it).
    """
    if delay_template_value == frame_state.DELAY_HELD and next_wake_clock is not None:
        delay_sentence_text = i18n.t(_FRAME_DELAY_HELD_TEXT) % next_wake_clock
    elif delay_template_value == frame_state.DELAY_DUE and next_wake_clock is not None:
        delay_sentence_text = i18n.t(_FRAME_DELAY_DUE_TEXT) % next_wake_clock
    else:
        delay_sentence_text = i18n.t(_FRAME_DELAY_UNKNOWN_TEXT)
    return '<p class="text-label section-caption">%s</p>' % escape_html(delay_sentence_text)


def _frame_display_cell_html(device_cfg, return_to, delay_caption_html):
    """The Screen switch cell: label, state-plus-control row, and the
    shared delay caption.
    """
    display_enabled = device_cfg.get("display_enabled", True)
    is_display_on = display_enabled is not False
    display_label_html = '<span class="text-label quick-action__label" id="%s">%s%s</span>' % (
        QUICK_SWITCH_SCREEN_LABEL_ID,
        icon_html("icon-power", size=16, extra_class="quick-action__icon"),
        escape_html(i18n.t(QUICK_ACTION_SCREEN_LABEL)))
    display_state_row_html = (
        quick_switch_state_html(
            QUICK_SWITCH_SCREEN_STATE_ID,
            i18n.t(QUICK_ACTION_ON_TEXT), i18n.t(QUICK_ACTION_OFF_TEXT), is_display_on)
        + quick_switch_html(
            "/quick/display", return_to, is_display_on,
            QUICK_SWITCH_SCREEN_LABEL_ID, QUICK_SWITCH_SCREEN_STATE_ID))
    return _frame_strip_cell_html(
        "quick-action quick-action--%s" % ("on" if is_display_on else "off"),
        display_label_html, display_state_row_html, delay_caption_html,
        extra_attrs=QUICK_SWITCH_REGION_ATTR)


def _frame_quiet_cell_html(device_cfg, return_to, delay_caption_html):
    """The Quiet hours switch cell: label, state-plus-control row, and the
    shared delay caption plus its own schedule link.

    The link is appended to a COPY of the shared delay sentence, never to
    `delay_caption_html` itself, which is also the Screen cell's own
    caption. Always a real `<a href>`, even when `return_to` is already
    DISPLAY_ROUTE — a same-page fragment link still works with no script.
    """
    quiet_enabled = device_cfg.get("quiet_hours_enabled", False)
    is_quiet_on = quiet_enabled is True
    quiet_start = device_cfg.get("quiet_hours_start") or "23:00"
    quiet_end = device_cfg.get("quiet_hours_end") or "07:00"
    quiet_label_html = '<span class="text-label quick-action__label" id="%s">%s%s</span>' % (
        QUICK_SWITCH_QUIET_LABEL_ID,
        icon_html("icon-moon", size=16, extra_class="quick-action__icon"),
        escape_html(i18n.t(QUICK_ACTION_QUIET_LABEL)))
    quiet_state_row_html = (
        quick_switch_state_html(
            QUICK_SWITCH_QUIET_STATE_ID,
            i18n.t(QUICK_ACTION_QUIET_ON_TEMPLATE) % (quiet_start, quiet_end),
            i18n.t(QUICK_ACTION_QUIET_OFF_TEXT), is_quiet_on)
        + quick_switch_html(
            "/quick/quiet-hours", return_to, is_quiet_on,
            QUICK_SWITCH_QUIET_LABEL_ID, QUICK_SWITCH_QUIET_STATE_ID))
    quiet_schedule_link_html = '<a class="text-link frame-strip__schedule-link" href="%s#%s">%s</a>' % (
        DISPLAY_ROUTE, _FRAME_QUIET_SCHEDULE_TARGET_ID,
        escape_html(i18n.t(_FRAME_QUIET_SCHEDULE_LINK_TEXT)))
    quiet_caption_html = delay_caption_html + quiet_schedule_link_html
    return _frame_strip_cell_html(
        "quick-action quick-action--%s" % ("on" if is_quiet_on else "off"),
        quiet_label_html, quiet_state_row_html, quiet_caption_html,
        extra_attrs=QUICK_SWITCH_REGION_ATTR)


def _frame_update_cell_html(
        resolved_state, headline_template_value, next_wake_clock,
        resolved_next_wake_iso, now_value):
    """The next-update cell: "" when no next-wake data is available. Three
    states share one dot vocabulary: due `.dot--ok`, held the neutral
    `.dot--off`, late `.dot--warn`, the warn signal carried by wording and
    dot, never text colour.

    The countdown sits beside — never inside — the headline. It is
    formatting and decides nothing: the instant and state word both come
    from `_frame_resolved_state()` above; relative-time.js advances the
    duration without re-deciding due/held/late. `countdown=True` keeps it
    a countdown after its instant passes, reading the waiting wording
    rather than silently becoming an age: "Expected since 14:32 /
    waiting…", never "2m ago" — a second, quieter lateness claim beside
    the headline's.
    """
    if next_wake_clock is None:
        return ""
    dot_class = _FRAME_DOT_CLASS_BY_STATE.get(resolved_state, "dot--ok")
    headline_class = "status-card__headline"
    if headline_template_value == frame_state.HEADLINE_LATE:
        headline_i18n_source = _FRAME_HEADLINE_LATE_TEXT
        headline_class = headline_class + " status-card__headline--warn"
    elif headline_template_value == frame_state.HEADLINE_HELD:
        headline_i18n_source = _FRAME_HEADLINE_HELD_TEXT
    else:
        headline_i18n_source = _FRAME_HEADLINE_DUE_TEXT
    # The clock value is its own `.time-value` element, not baked into the
    # sentence's escaped text: each headline template carries exactly one
    # "%s", so the leading text, the clock span and the trailing text are
    # escaped separately at their own interpolation sites.
    headline_before, headline_after = i18n.t(headline_i18n_source).split("%s", 1)
    headline_text = "%s%s%s" % (
        escape_html(headline_before),
        '<span class="time-value time-value--primary">%s</span>' % escape_html(next_wake_clock),
        escape_html(headline_after),
    )
    update_state_row_html = (
        '<p class="%s"><span class="dot %s"></span>%s</p>'
    ) % (headline_class, dot_class, headline_text)
    countdown_html = (
        '<p class="text-label section-caption">%s</p>'
        % relative_time_html(resolved_next_wake_iso, now_value, countdown=True))
    return _frame_strip_cell_html(
        "frame-strip__cell--update", "", update_state_row_html, countdown_html)


def frame_strip_html(ctx, return_to, next_wake_iso=None):
    """The "Frame" strip: one shared body, called identically by
    home_page.render() and config_page.render()'s Display scope, so both
    pages' switches and headline can never disagree. `return_to` is
    written escaped; the server validates it against a route whitelist
    before using it as a redirect target.

    Both switch forms carry `data-quick-switch`, the hook
    companion/static/dirty-state.js keys its leave-guard on — do not
    delete it as apparently unused. Every value crosses escape_html();
    every string crosses i18n.t().
    """
    ctx = page_context.coerce(ctx)
    device_cfg = ctx.device_config or {}
    (resolved_state, headline_template_value, delay_template_value,
     resolved_next_wake_iso, next_wake_clock, now_value) = _frame_resolved_state(ctx)
    delay_caption_html = _frame_delay_caption_html(delay_template_value, next_wake_clock)
    display_cell_html = _frame_display_cell_html(device_cfg, return_to, delay_caption_html)
    quiet_cell_html = _frame_quiet_cell_html(device_cfg, return_to, delay_caption_html)
    update_cell_html = _frame_update_cell_html(
        resolved_state, headline_template_value, next_wake_clock,
        resolved_next_wake_iso, now_value)
    return (
        '<div class="frame-strip stat-tile stat-tile--accent" aria-labelledby="frame-strip-heading">'
        '<h2 id="frame-strip-heading" class="text-heading">%s</h2>'
        '<div class="frame-strip__cells">%s%s%s</div>'
        "</div>"
    ) % (
        escape_html(i18n.t(FRAME_STRIP_HEADING)),
        display_cell_html, quiet_cell_html, update_cell_html,
    )


def card_status_class(base_class, status):
    """`base_class + "--ok"/"--warn"/"--error"` for a whitelisted status; the
    empty string for `None` or anything unrecognised.

    `status` is looked up in a fixed three-key whitelist, the same discipline
    status_dot()/stat_tile() use — an unrecognised value can never become an
    arbitrary, attacker-influenceable class name. `base_class` is expected to
    be a module constant or call-site literal, never derived from data.

    The fallback deliberately differs from stat_tile()'s: stat_tile()'s base
    rule already declares a coloured top border that needs some colour, while
    a page-level card's base rule declares a plain hairline, so "no status"
    here means "no modifier, keep the neutral edge" — the absence of a
    coloured edge is itself the "no verdict" signal.
    """
    suffix = _CARD_STATUS_SUFFIXES.get(status)
    return base_class + suffix if suffix else ""


def status_row(label, verdict, detail, state):
    """`<div class="status-row status-row--ok|warn|error">`: one shared row
    primitive (dot + optional label + verdict + detail), used by Home's
    status card and the Calendar status row alike. `label` falsy omits
    the `<span>` entirely, not just its text.

    `state` maps through the same `_STATUS_DOT_CLASSES` fallback
    status_dot()/stat_tile() use, and through card_status_class()'s
    whitelist for the outer modifier — never a bare interpolation, so an
    unrecognised value degrades to the default dot rather than an
    attacker-influenceable class name. `verdict`/`detail`/`label` are
    escaped here; the caller translates them through i18n.t() first.
    """
    dot_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    modifier = card_status_class("status-row", state)
    css_class = "status-row" + ((" " + modifier) if modifier else "")
    label_html = (
        '<span class="status-row__label text-label">%s</span>' % escape_html(label)
        if label else "")
    return (
        '<div class="%s">'
        '<span class="dot %s"></span>%s'
        '<span class="status-row__verdict">%s</span>'
        '<span class="status-row__detail">%s</span>'
        "</div>"
    ) % (css_class, dot_class, label_html, escape_html(verdict), escape_html(detail))


def section_intro_html(section_id, heading, description):
    """A `<div class="section-intro">` wrapping one id-anchored `<h2>` plus a
    muted one-sentence description on the same baseline.

    Shared across page modules since `companion/pages/__init__.py` forbids
    one page module importing another. The `<h2 id="..." class="text-heading">`
    keeps the exact attribute order and escape_html() call
    health_page.py's structural checks pin — this builder must never drift
    from that shape.

    `section_id` is escaped too, like every other string this file
    interpolates into an attribute or text node: every current call site
    passes a fixed module constant, but this helper is shared going forward
    and must not be the one place a caller is trusted.
    """
    return (
        '<div class="section-intro">'
        '<h2 id="%s" class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        "</div>"
    ) % (escape_html(section_id), escape_html(heading), escape_html(description))


def empty_state(heading, body, compact=False):
    """The escaped two-part empty-state block used for the flight log,
    the gallery, and the unresolved-prefix list.

    `compact` falsy is byte-identical to this function's pre-existing
    output. Why it exists: an empty state inside a `.stat-tile` put a
    22px serif heading inside a card whose own caption is 12px, an
    inverted hierarchy. Compact drops the heading to the Emphasis role
    and the body to the label size, matching a filled tile's verdict and
    detail rows through its own class names, never by borrowing
    `.widget-verdict`/`.widget-detail` — an empty state's heading is not
    a verdict.
    """
    if compact:
        return (
            '<div class="empty-state empty-state--compact">'
            '<p class="empty-state__heading text-body">%s</p>'
            '<p class="empty-state__body text-label section-caption">%s</p>'
            "</div>"
        ) % (escape_html(heading), escape_html(body))
    return (
        '<div class="empty-state">'
        '<p class="empty-state__heading text-heading">%s</p>'
        '<p class="empty-state__body text-body">%s</p>'
        "</div>"
    ) % (escape_html(heading), escape_html(body))


def page_header(title, purpose=None, freshness_html=None, action_html=None):
    """The shared page-header component every authenticated page's
    render() opens with, in place of a bare <h1>. This exact signature
    and parameter order is called across many page modules — do not
    rename or reorder.

    `title`/`purpose` are escaped here. `freshness_html`/`action_html`,
    when truthy, are the caller's own already-safe markup, interpolated
    verbatim with no escape_html() call — callers must escape any
    user-influenced data before passing it through either parameter.

    Blocks concatenate title, then freshness/action, then purpose last.
    The returned string ends with FLASH_SLOT_MARKER, which page_shell()
    is the only consumer of.
    """
    purpose_html = (
        '<p class="page-header__purpose text-body">%s</p>' % escape_html(purpose)
        if purpose else "")
    freshness_block = freshness_html if freshness_html else ""
    action_block = action_html if action_html else ""
    return (
        '<div class="page-header">'
        '<h1 class="page-title">%s</h1>'
        "%s%s%s"
        "</div>"
        "%s"
    ) % (
        escape_html(title), freshness_block, action_block, purpose_html,
        FLASH_SLOT_MARKER,
    )


def data_table(headers, rows, mono_columns=(), raw_columns=(), desc_columns=(), prose=False,
               modifier=None):
    """A header row plus alternating body rows, every value escaped.
    Returns empty_state()'s output instead of an empty table when `rows`
    is empty. `mono_columns` names zero-based indices that get the
    monospace class.
    `raw_columns` names indices whose value is already-safe, pre-built
    HTML, interpolated without escape_html() — only place the output of
    a builder that already escapes internally, never a bare string: that
    reopens the XSS-shaped defect this module's escaping discipline
    otherwise closes. `desc_columns` names indices that get the
    description-role class; all three name sets are orthogonal.

    `prose` releases a table from the shared no-wrap/no-crop floor, for
    full-sentence columns. `modifier` appends one `data-table--<modifier>`
    class; pass the bare stem, never the full class name.
    """
    if not rows:
        return empty_state("No data yet.", "Nothing to show here yet.")

    header_cells = "".join(
        "<th>%s</th>" % escape_html(header) for header in headers)

    body_rows = []
    for row_index, row in enumerate(rows):
        row_class = "row-alt" if row_index % 2 else "row"
        cells = []
        for column_index, cell in enumerate(row):
            # mono is joined first so a mono-only cell's attribute string stays
            # byte-identical to the pre-desc_columns output; test_view_pages.py pins
            # that shape.
            cell_roles = []
            if column_index in mono_columns:
                cell_roles.append("mono")
            if column_index in desc_columns:
                cell_roles.append("desc")
            cell_class = ' class="%s"' % " ".join(cell_roles) if cell_roles else ""
            cell_html = cell if column_index in raw_columns else escape_html(cell)
            cells.append("<td%s>%s</td>" % (cell_class, cell_html))
        body_rows.append('<tr class="%s">%s</tr>' % (row_class, "".join(cells)))

    table_class = "data-table data-table--prose" if prose else "data-table"
    if modifier:
        table_class += " data-table--%s" % modifier
    return (
        '<div class="data-table-wrap">'
        '<table class="%s">'
        "<thead><tr>%s</tr></thead>"
        "<tbody>%s</tbody>"
        "</table>"
        "</div>"
    ) % (table_class, header_cells, "".join(body_rows))
