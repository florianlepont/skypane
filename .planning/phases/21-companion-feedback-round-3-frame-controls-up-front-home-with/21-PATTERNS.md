# Phase 21: Frame controls up front, Home with three tiles, one Frame colours view, calendar tile, compact flights table, simple mode removed, artwork upload restored — Pattern Map

**Mapped:** 2026-09-12
**Files analyzed:** 13 new/substantially-rewritten units across 9 files, plus 6 test harnesses and the i18n_fr catalogue package
**Analogs found:** 13 / 13 — every unit this phase introduces or rewrites lands beside an existing, already-precedented builder/script in the same file or module; there is no "no analog" bucket (same shape phases 19/20's own pattern maps found).

This map reuses `20-PATTERNS.md`'s format verbatim (file classification → pattern assignments → shared patterns → file-overlap/test-harness tables → no-analog bucket). All line numbers below were read live from the current tree on 2026-09-12 (same commit state `21-RESEARCH.md` was written against) — re-verify if planning is delayed.

## File Classification

| New/Rewritten Unit | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `layout.frame_strip_html(ctx, return_to)` (new) | shared view helper | transform (HTML assembly) | `config_page.quiet_hours_group()`'s/`display_group()`'s `quick_action_html` blocks (`config_page.py:1731-1754`, `:2097-2120`) + `home_page._status_card_html()`'s next-update headline (`home_page.py:254-274`) | exact (relocation + merge of two existing blocks) |
| `layout.nav_status_html(device_cfg)` (new) | shared view helper | transform | `layout._health_alert_markup()` (`layout.py:871-903`) for the dot+label append idiom; `layout.sidebar_nav()`/`_mobile_nav_html()` (`layout.py:906-967`, `:1057-1126`) for the "one function, two call sites, can never drift" contract | exact |
| `layout.page_shell()` gaining `device_config=None` | shared view helper | transform | `page_shell()`'s own `health_alert=None`/`lang=None` keyword-with-default precedent (`layout.py:1202-1239`) | exact |
| `app._handle_quick_toggle()`'s `return_to` validation | HTTP controller | request-response | `app._referring_tab()` (`app.py:2376-2383`) for the membership-test-then-fallback shape; every other client-controlled-enum gate in `handle_post()` (`config_page.py:3912-3926`) | exact |
| `home_page._status_tiles_html()` (rebuilt) | page module | request-response (read) | itself, phase-19 shape via `git show 614d41e~1:companion/pages/home_page.py:166-218`, content-derivation reused from current `_status_card_html()` (`home_page.py:239-317`) | exact |
| Frame colours card assembly in `config_page.py` (new) | page module | request-response (form CRUD) | `_theme_chip_grid_html()` (`config_page.py:966-1070`), `theme_fieldset()` (`:1138-1356`), `_rule_kind_radio_html()`'s segmented-radio idiom (`:2581-2605`), `_theme_live_preview_html()` (`:1073-1135`) | exact |
| `config_page.handle_post()`'s `theme_arriving`/`calendar_theme_id` empty-string handling (rewritten) | page module | request-response | the existing resolution block itself (`config_page.py:3900-3960`), `device_config.normalise_theme_arriving()`/`normalise_calendar_theme_id()` (`server/device_config.py`) | exact (in-place rewrite, not a new shape) |
| Merged Calendar card in `config_page.py` (rewritten) | page module | request-response (form CRUD) | `calendar_group()` (`:2143-2292`), `calendar_connect_section()` (`:2295-2369`), `calendar_disconnect_section()` (`:2372-2418`) — three existing builders merged into one card | exact |
| `companion/static/flight-detail-toggle.js` (new) | static asset (browser behaviour) | event-driven (DOM) | `companion/static/theme-preview.js` (full file, 81 lines) for the six-touch-point contract + guard-clause/event-delegation idiom; `companion/static/freshness.js`'s `data-pause-text`/`data-resume-text` idiom (deleted this phase, but the pattern survives) for the `data-more-text`/`data-less-text` swap | exact |
| `history_page._history_table_html()`/`_HEADERS` (compacted, rewritten) | page module | request-response (read) | itself — `_merged_cell()` (`:565-589`), `_callsign_hex_cell()` (`:644-687`), `_clock_cell_html()` (`:777-805`), `_history_cards_html()`'s `<details>` shape (`:867-991`) | exact |
| `layout.status_dot(..., visually_hide_label=False)` (new keyword) | shared view helper | transform | `stat_tile()`'s own `caption_title=None`/`icon=None` keyword-with-default precedent (`layout.py:1460-1517`) — "byte-identical when falsy" contract | exact |
| Simple-mode/pause-button deletions across `prefs.py`/`auth.py`/`app.py`/`layout.py`/page modules/`freshness.js` | deletion-only | n/a | phase 20's own additions being reversed — see file:line inventory below | exact (research already enumerated every site; this map cross-references it) |
| `airlines_page._resolve_section_html()`/`_lightbox_html()` guard removal | page module | request-response (read + resolve-write) | the two guards themselves (`:1727`/`:1733`, `:1228-1230`) — a one-line gate deletion, not a new component | exact |

## Pattern Assignments

### `layout.frame_strip_html(ctx, return_to)` (new, `companion/layout.py`)

**Analogs:**
- `config_page.quiet_hours_group()`'s quick-action block — `companion/pages/config_page.py:1718-1754`
- `config_page.display_group()`'s quick-action block — `companion/pages/config_page.py:2062-2120`
- `home_page._status_card_html()`'s headline computation — `companion/pages/home_page.py:254-274`

**Why these three, not one:** the strip is literally these two existing `quick_action_html` blocks (byte-identical `.quick-action`/`.quick-action--on|off` markup) plus the third existing headline block, combined into one shared function. Copy the markup shape verbatim; do not redesign it.

**Quiet-hours quick-action markup to copy verbatim** (`config_page.py:1731-1754`):
```python
quick_action_html = (
    '<div class="quick-action-slot">'
    '<div class="quick-action quick-action--%s">'
    '<div class="quick-action__text">'
    '<span class="text-label quick-action__label">%s%s</span>'
    '<span class="text-body quick-action__state">%s</span>'
    "</div>"
    '<form method="post" action="/quick/quiet-hours" class="quick-action__form">'
    '<input type="hidden" name="%s" value="%s">'
    '<button type="submit">%s</button>'
    "</form>"
    "</div>"
    '<p class="text-label section-caption">%s</p>'
    "</div>"
) % (
    "on" if is_on else "off",
    layout.icon_html("icon-moon", size=16, extra_class="quick-action__icon"),
    escape_html(i18n.t(QUICK_ACTION_QUIET_LABEL)),
    escape_html(state_text),
    layout.QUICK_STATE_FIELD, escape_html(next_state),
    escape_html(i18n.t(
        QUICK_ACTION_QUIET_TURN_OFF_BUTTON if is_on else QUICK_ACTION_QUIET_TURN_ON_BUTTON)),
    escape_html(i18n.t(QUICK_ACTION_APPLIES_SENTENCE)),
)
```
Screen's own sibling block (`config_page.py:2097-2120`) is byte-for-byte the same shape with `action="/quick/display"`, `icon-power`, `QUICK_ACTION_SCREEN_LABEL`/`ON_TEXT`/`OFF_TEXT`/`SWITCH_ON_BUTTON`/`SWITCH_OFF_BUTTON`. The strip helper needs **one new hidden field** neither block currently carries — `<input type="hidden" name="return_to" value="%s">` — per Structural Note 1 (21-UI-SPEC.md). All the `QUICK_ACTION_*` constants (`config_page.py:433-446`) must move to (or be re-declared in) `layout.py`, since `companion/pages/__init__.py` forbids one page module importing another and both `home_page.py` and `config_page.py` need them — this is the exact reason 21-CONTEXT.md's R-01 puts the helper in `layout.py`.

**Next-update headline to copy verbatim** (`home_page.py:254-274`):
```python
headline_html = ""
next_wake_iso = wake.next_wake_at_iso(
    ctx.get("last_checkin_ts"), ctx.get("device_config"))
if next_wake_iso:
    next_wake_parsed = layout.parse_iso(next_wake_iso)
    if next_wake_parsed is not None:
        next_wake_clock = layout.local_clock_text(
            next_wake_parsed, now_parsed=layout.parse_iso(now))
        age = layout.age_seconds(next_wake_iso, now)
        is_past = age is not None and age >= 0
        if is_past:
            headline_text = escape_html(
                i18n.t(EXPECTED_SINCE_TEMPLATE) % next_wake_clock)
            headline_html = (
                '<p class="status-card__headline status-card__headline--warn">'
                '<span class="dot dot--warn"></span>%s</p>'
            ) % headline_text
        else:
            headline_text = escape_html(
                i18n.t(NEXT_UPDATE_TEMPLATE) % next_wake_clock)
            headline_html = '<p class="status-card__headline">%s</p>' % headline_text
```
`layout.py` already has `wake` imported? — **check at plan time**; if not, `layout.py` needs `from server import wake` (already legal per `server/wake.py`'s move in phase 20 — `server/` importing FROM `companion/` is forbidden, the reverse is fine). `NEXT_UPDATE_TEMPLATE`/`EXPECTED_SINCE_TEMPLATE` stay owned by `home_page.py` (per 21-UI-SPEC.md Copywriting Contract §A, "reused") — the strip helper takes them as arguments or imports the two template strings; do not fork a second copy of the template text into `layout.py`.

**Card wrapper:** the whole strip is `<div class="frame-strip stat-tile stat-tile--accent">` per 21-UI-SPEC.md §A — `stat_tile()`'s CSS classes are reused, but the strip is a **hand-built `<div>`, not a `stat_tile()` call** (the UI-SPEC is explicit about this: the strip's own `<h2>` needs the Section-heading role, not `stat_tile()`'s smaller caption role). Do not attempt to route this through `layout.stat_tile()`.

---

### `layout.nav_status_html(device_cfg)` (new, `companion/layout.py`)

**Analog:** `layout._health_alert_markup(severity)` (`companion/layout.py:871-903`) for the "one shared dot+label builder, called from both `sidebar_nav()` and `_mobile_nav_html()`" contract; `status_dot()` (`layout.py:1435-1457`) for the dot-plus-escaped-label markup itself (though the new function does NOT call `status_dot()` directly — it needs two dot+label pairs joined by a separator, a new small composition, not a second `status_dot()` call site reused verbatim, since `status_dot()`'s `dot-label` span is a *visible* label here, matching the UI-SPEC's markup in §B exactly).

**Docstring convention to copy** (`layout.sidebar_nav()`, `layout.py:906-936`): state which two call sites this function feeds, and that they "can never disagree" because they share one function body — this is the load-bearing sentence every dual-consumer builder in this file states explicitly; carry it into `nav_status_html()`'s own docstring.

**New CSS-class register entry needed:** `.dot--off` (21-UI-SPEC.md §B) is a genuinely new dot state — reuse the exact `color-mix(in srgb, var(--color-text) 30%, transparent)` value `.quick-action--off`'s own left-edge rule already uses (`style.css`), per the UI-SPEC's own instruction — do not invent a new colour literal.

**Call sites:** both `sidebar_nav(active, health_alert=None)` and `_mobile_nav_html(active, theme_form_html, health_alert=None, ...)` need a new parameter (e.g. `device_config=None`) threaded through from `page_shell()`, mirroring `health_alert`'s own keyword-with-default addition precedent (`layout.py:916-919`'s docstring: "keyword-with-default so no existing positional call site changes meaning"). `page_shell()` itself needs the same new keyword, per Structural Note in 21-CONTEXT.md R-03 — see next entry.

---

### `layout.page_shell()` gaining `device_config=None`

**Analog:** `page_shell()`'s own `health_alert=None`/`lang=None` parameters (`layout.py:1202-1239`) — the exact precedent for "a new keyword, placed after existing ones, defaulted to `None`, so all ~40 existing call sites are unaffected; `None` means 'no request context available' (login, 404) and degrades to no reminder rendered at all," matching `health_alert`'s own documented degrade-to-nothing contract verbatim.

```python
def page_shell(
        title, active, body, ui_theme="auto", flash=None, banner=None,
        health_alert=None, lang=None, device_config=None):
    ...
    sidebar_html = sidebar_nav(active, health_alert=health_alert, device_config=device_config)
    ...
    mobile_nav_html = _mobile_nav_html(
        active, theme_form_html, health_alert=health_alert,
        lang_form_html=lang_form_html, mode_form_html=mode_form_html,
        device_config=device_config)
```
`app.py`'s `_page_shell_for()` (`app.py:2385-2405`) is the one call site that must pass `device_config=ctx["device_config"]` — this is the exact function `_handle_settings_post()`'s D-07 rejected-save branch also calls (per its own docstring, `app.py:2386-2397`), so passing the new keyword through here covers both the GET and the rejected-POST-redisplay path in one edit.

---

### `app._handle_quick_toggle()`'s `return_to` validation

**Analog:** `app._referring_tab()` (`app.py:2376-2383`) for the exact "membership-test against a route whitelist, fall back to a known-safe default" shape:
```python
def _referring_tab(self):
    referer = self.headers.get("Referer", "")
    try:
        path = urlsplit(referer).path
    except ValueError:
        path = ""
    allowed = {route for route, _ in layout.NAV_TABS}
    return path if path in allowed else HOME_ROUTE
```
21-CONTEXT.md's R-02 explicitly rejects reusing `_referring_tab()` itself (Referer-header-based) in favour of a **hidden form field**, but the validation *shape* — build a small whitelist set, test membership, fall back to a known-safe route — is the one to copy:
```python
def _handle_quick_toggle(self, field):
    form = self.read_form()
    return_to = form.get("return_to")
    if return_to not in (layout.HOME_ROUTE, layout.DISPLAY_ROUTE):
        return_to = layout.DISPLAY_ROUTE  # unchanged pre-phase-21 behaviour
    state = form.get(layout.QUICK_STATE_FIELD)
    if state not in (layout.QUICK_STATE_ON, layout.QUICK_STATE_OFF):
        return self.redirect(
            "%s?flash=%s" % (return_to, quote(FLASH_KEY_QUICK_FAILED)))
    ...
    return self.redirect("%s?flash=%s" % (return_to, quote(flash_key)))
```
All three `self.redirect(...)` call sites inside `_handle_quick_toggle()` (`app.py:2810-2826`) change from the `layout.DISPLAY_ROUTE` literal to the resolved `return_to` — this is the exact "membership-test-before-any-use" discipline `handle_post()`'s own `calendar_theme_id`/`theme_arriving`/`tracked_runway` gates already apply (`config_page.py:3912-3926`), reused here for a route string instead of a theme id.

---

### `home_page._status_tiles_html()` (rebuilt to restore the phase-19 shape)

**Analog:** the phase-19 function itself, via `git show 614d41e~1:companion/pages/home_page.py:166-218` (structure only — see Pitfall below), and the CURRENT `_status_card_html()` (`home_page.py:239-317`) for the bug-fixed content-derivation to keep.

**Structure to restore** (phase-19 shape, three `stat_tile()` calls):
```python
tiles = (
    layout.stat_tile(FRAME_TILE_LABEL, frame_html, device_state, icon="icon-device")
    + layout.stat_tile(BATTERY_TILE_LABEL, battery_html, battery_state, icon="icon-battery")
    + layout.stat_tile(DATA_TILE_LABEL, data_html, pipeline_state, icon="icon-pipeline")
)
return (
    '<section class="home-section" aria-labelledby="home-status">'
    '<h2 class="text-heading" id="home-status">%s</h2>'
    '<div class="dashboard-grid home-status-grid">%s</div>'
    '<p class="text-label"><a href="/health">%s</a></p>'
    "</section>"
) % (escape_html(STATUS_HEADING), tiles, escape_html(HEALTH_LINK_TEXT))
```

**CRITICAL — do not resurrect the phase-19 function body verbatim** (research Pitfall 3 / CONTEXT R-06). The phase-19 body built `frame_body` by concatenating `FRAME_STATE_TEXT[device_state]` with `health["device_html"]` verbatim — a **duplicated verdict**, because `health["device_html"]`'s own `verdict` paragraph (built by `health_page._device_section()`) repeats byte-identical text. The CURRENT, bug-fixed derivation lives in `_status_card_html()` (`home_page.py:276-297`):
```python
frame_verdict = i18n.t(FRAME_STATE_TEXT.get(device_state, FRAME_STATE_TEXT["warn"]))
frame_detail = _plain_text_from_markup(health.get("device_detail_html"))
# ... same pattern for battery_verdict/battery_detail, data_verdict/data_detail
```
Rebuild the three tiles' `content_html` from THIS verdict/detail pair — e.g. `content_html = '<p class="text-body">%s</p><p class="text-label">%s</p>' % (escape_html(frame_verdict), escape_html(frame_detail))` — never from `health["device_html"]` wholesale. The `HEALTH_LINK_TEXT` link (`home_page.py:299-305`) loses its `if not ctx.get("simple_mode")` gate outright — D-17 removes `simple_mode` — so it renders unconditionally now, and this plan should simply never re-add the gate (per 21-RESEARCH.md's own note: "coordinate, don't double-handle" with whichever plan deletes `simple_mode`).

**`render()` reorder** (`home_page.py:414-429`): the picture and recent-flights columns move from sharing a row with the status card to sharing their own row, with the tiles as a separate full-width section above them:
```python
return (
    header
    + layout.frame_strip_html(ctx, return_to=layout.HOME_ROUTE)
    + _status_tiles_html(ctx)
    + '<div class="home-columns home-picture-row">'
    + _hero_figure_html(ctx, current_flight_row)
    + _recent_flights_html(rows, now, ctx.get("state_dir"))
    + "</div>"
)
```
`_hero_figure_html()`/`_recent_flights_html()` bodies are unchanged (`home_page.py:319-411`) — only `render()`'s own assembly order changes, and `.home-hero`/`_status_card_html()` are deleted outright.

---

### Frame colours card assembly (new, `companion/pages/config_page.py`)

**Analogs:**
- `_theme_chip_grid_html(field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="", radio_form_id=None)` — `config_page.py:966-1070` — the ONE chip-grid renderer, already the third/fourth consumer pattern (departures/arrivals/calendar/rules); D-08's "one chip grid for the selected usage" is this same function called with `field_name` swapped, never a new grid builder.
- `_theme_live_preview_html(current_theme_id, state_dir)` — `config_page.py:1073-1135` — the live preview `<figure>`, reused verbatim as the card's left column.
- `_rule_kind_radio_html(kind, checked)` — `config_page.py:2581-2605` — the exact "visually-hidden native radio + styled `<label>`, plain-language visible text + technical `title` attribute" idiom the 4-row `colour_usage` radiogroup should copy (a fourth consumer of the same segmented-control pattern, per `_rule_add_form_html()`'s own docstring naming it "the THIRD consumer... after the UI-theme picker and this same phase's language switch").
- `_rule_list_html(rows)` / `_rule_add_form_html()` / `_rules_section_html()` — `config_page.py:2785-2869` — relocate verbatim into the "Per-flight rules" usage panel; do not rewrite their internals.

**Chip-grid extension point** (`config_page.py:966-1070`, docstring already anticipates this): add one new parameter, e.g. `leading_chip_html=""` (per 21-UI-SPEC.md Structural Note 3), interpolated before the loop over `device_config.THEME_IDS`:
```python
def _theme_chip_grid_html(
        field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="",
        radio_form_id=None, leading_chip_html=""):
    ...
    grid_class = "theme-chip-grid"
    if extra_class:
        grid_class = grid_class + " " + extra_class
    attr_html = (" %s" % extra_attr) if extra_attr else ""
    return '<div class="%s"%s>%s%s</div>' % (
        grid_class, attr_html, leading_chip_html, "".join(chips))
```
Arrivals'/Calendar's calls build a `"Same as departures"` chip fragment (submitting the empty string, per D-09) and pass it as `leading_chip_html`; departures'/rules' calls pass nothing — additive, byte-identical for every existing call site.

**`form="settings-form"` cross-DOM idiom** — already the exact mechanism `calendar_group()`'s own `radio_form_id=SETTINGS_FORM_ID` call already uses (`config_page.py:2261`); every one of the three theme radiogroups in the new card keeps this, unchanged in shape:
```python
form_attr_html = ' form="%s"' % escape_html(radio_form_id) if radio_form_id else ""
```

**Docstring convention to copy for the new card-assembly function:** every existing group builder in this file (`theme_fieldset()`, `calendar_group()`, `quiet_hours_group()`) opens its docstring by naming the decision IDs it implements, the exact card wrapper class, and which existing constants/functions it reuses versus rewrites — follow this shape for the new `_frame_colours_card_html(ctx, ...)`-style function, citing D-06..D-12 by number.

---

### `handle_post()`'s `theme_arriving`/`calendar_theme_id` empty-string handling (rewritten in place)

**Analog:** the existing validation-then-resolution block itself — this is a **rewrite of an existing pattern**, not a new one; the pattern to preserve is "membership-test gate runs before the resolution block; the resolution block derives the persisted value from validated submission state," already the shape every other field in `handle_post()` follows.

**Current validation gate to fix** (`config_page.py:3912-3923`) — must exempt `""`:
```python
if (
    submitted_calendar_theme_id is not None
    and submitted_calendar_theme_id not in device_config.THEME_IDS
):
    _note_error(errors, "calendar_theme_id", ERROR_INVALID_CHOICE)
    return FLASH_SAVE_FAILED
if (
    submitted_theme_arriving is not None
    and submitted_theme_arriving not in device_config.THEME_IDS
):
    _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
    return FLASH_SAVE_FAILED
```
Becomes (both gates need the identical fix — copy the `("",) + device_config.THEME_IDS` shape to both, do not fix only one):
```python
if (
    submitted_calendar_theme_id is not None
    and submitted_calendar_theme_id not in (("",) + device_config.THEME_IDS)
):
    _note_error(errors, "calendar_theme_id", ERROR_INVALID_CHOICE)
    return FLASH_SAVE_FAILED
if (
    submitted_theme_arriving is not None
    and submitted_theme_arriving not in (("",) + device_config.THEME_IDS)
):
    _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
    return FLASH_SAVE_FAILED
```

**Current checkbox-keyed resolution block to delete** (`config_page.py:3952-3960`) — the `theme_arriving_enabled` checkbox no longer exists as a form field (D-09 deletes it):
```python
if screens.GROUP_THEME not in in_scope:
    theme_arriving = None
elif submitted_theme_arriving_enabled is None:
    theme_arriving = device_config.CLEAR_THEME_ARRIVING
elif submitted_theme_arriving_enabled == ARRIVING_CHECKBOX_VALUE:
    theme_arriving = submitted_theme_arriving
else:
    _note_error(errors, "theme_arriving_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
    return FLASH_SAVE_FAILED
```
Replaced by (empty-string-is-the-clear-signal, matching `device_config.CLEAR_THEME_ARRIVING`'s own sentinel contract, `server/device_config.py`'s `normalise_theme_arriving()`):
```python
if screens.GROUP_THEME not in in_scope:
    theme_arriving = None
elif submitted_theme_arriving is None:
    theme_arriving = None
elif submitted_theme_arriving == "":
    theme_arriving = device_config.CLEAR_THEME_ARRIVING
else:
    theme_arriving = submitted_theme_arriving
```
`calendar_theme_id` needs no equivalent second resolution block — it never had a checkbox; once its gate above exempts `""`, the existing pass-through (`submitted_calendar_theme_id if ... is not None else current[...]`) plus `normalise_calendar_theme_id("")`'s own existing `None`-degrade contract (`server/device_config.py`) already does the right thing. `ARRIVING_CHECKBOX_VALUE`/`THEME_ARRIVING_TOGGLE_ID`/`THEME_ARRIVING_CHECKBOX_LABEL` constants (`config_page.py:222-234`) are deleted along with the checkbox markup in `theme_fieldset()` (superseded by the Frame colours card).

---

### Merged Calendar card (rewritten, `companion/pages/config_page.py`)

**Analogs:** the three existing builders being fused —
- `calendar_group(configured, drift, last_synced_at, ...)` — `config_page.py:2143-2292` — status row (`layout.status_row("", verdict, detail, state)`, `:2244`) and the "How it works" `<details>` (`:2263-2273`) relocate verbatim; the chip grid (`:2252-2261`) is deleted from this card (moves to Frame colours, D-06).
- `calendar_connect_section(configured, errors=None)` — `config_page.py:2295-2369` — the write-only URL field's contract (`:2311-2320`'s docstring: "the input always renders with no `value` attribute... nothing derived from the stored URL") must be preserved verbatim in the merged markup; the `<details>` wrap for "Replace the feed URL" (`:2363-2366`) is the exact element 21-UI-SPEC.md §E asks for — reuse, do not rebuild.
- `calendar_disconnect_section(configured, drift)` — `config_page.py:2372-2418` — the `data-confirm`/`data-confirm-value`/hidden-confirm-field mechanism (`:2404-2418`) is unchanged; only its button's surrounding markup (now inline on the same line as "Replace the feed URL", via a `form="calendar-disconnect-form"` cross-DOM attribute per 21-UI-SPEC.md §E) changes.

**New masked-URL helper** (genuinely new capability, not a rewording — research Area C.4 / CONTEXT R-10): no existing analog in this codebase does this; the closest structural cousin for the "parse then render a derived fragment, never raw" discipline is `server/device_config.py`'s own `normalise_*()` family's "membership test, degrade safely" contract. Implementation must use a real URL parse, never a byte-offset truncation:
```python
def _masked_calendar_url(url):
    """host + '…' — never the path/query/token. A parse failure (or an
    absent url) degrades to a generic fallback, never raises, matching
    every other calendar-secret-adjacent helper's fail-soft contract
    (calendar_connect_section()'s own write-only docstring)."""
    try:
        netloc = urlsplit(url).netloc
    except ValueError:
        return CALENDAR_MASKED_URL_FALLBACK
    return "%s…" % netloc if netloc else CALENDAR_MASKED_URL_FALLBACK
```
This is the ONE new piece of server logic in this phase that reads back a stored secret for display — flag it in review; test it explicitly for "never contains a path/query/fragment character" (Security Domain table, 21-CONTEXT.md/RESEARCH.md Area C.4).

**Two button-text constants, not one** (Structural Note 6, 21-UI-SPEC.md): `CALENDAR_CONNECT_BUTTON_TEXT` (existing, `"Connect calendar"`) stays for the not-connected state; a new `CALENDAR_REPLACE_BUTTON_TEXT` (`"Replace"`/`"Remplacer"`) is needed for the connected-state disclosure's button — `calendar_connect_section()`'s merged replacement picks between them based on `configured`, mirroring how it already picks the wrap-in-`<details>`-or-not branch on the same flag.

---

### `companion/static/flight-detail-toggle.js` (new)

**Analog:** `companion/static/theme-preview.js` (full file, 81 lines) for the IIFE guard-clause/event-delegation shape and the six-touch-point registration contract; `companion/static/freshness.js`'s (deleted this phase, but the idiom survives) `data-pause-text`/`data-resume-text` attribute-swap idiom for the More/Less text swap.

**Guard-clause + no-fetch/no-timer header convention to copy** (`theme-preview.js:1-45`):
```javascript
/*
 * SkyPane companion service — flight-detail-toggle.js.
 *
 * D-15 (21-CONTEXT.md): reveals/collapses a Flights table row's detail
 * <tr> (hex, full ISO timestamp, runway, copy button) on click of its
 * own "More"/"Plus" button. ES5-safe subset only (no let/const/arrow
 * functions/template literals/backticks) — no build step, no bundler,
 * matching every other file in companion/static/. Served by
 * companion/app.py's FLIGHT_DETAIL_TOGGLE_SCRIPT_ROUTE.
 *
 * No-JS floor (D-15, locked): every .flight-detail-row renders WITHOUT
 * the collapsing class on the server — this script adds the class at
 * load. A page where this specific script is blocked (but others run)
 * must still show every detail row; keying off a page-wide ".js" class
 * would defeat that. See 21-UI-SPEC.md §F for the full reasoning.
 */
(function () {
  "use strict";
  var rows = document.querySelectorAll(".flight-detail-row");
  var toggles = document.querySelectorAll("[data-row-toggle]");
  if (!rows.length || !toggles.length) {
    return;
  }
  ...
})();
```
**Six-touch-point registration** (worked example, `theme-preview.js`'s own triplet — copy the SAME six sites, substituting names):
1. Route constant — `companion/app.py:187`: `THEME_PREVIEW_SCRIPT_ROUTE = "/static/theme-preview.js"` → add `FLIGHT_DETAIL_TOGGLE_SCRIPT_ROUTE = "/static/flight-detail-toggle.js"`.
2. Path constant + serve delegate — `companion/app.py:582`, `:1672-1678`:
   ```python
   _FLIGHT_DETAIL_TOGGLE_JS_PATH = os.path.join(_HERE, "static", "flight-detail-toggle.js")

   def _serve_flight_detail_toggle_script(self):
       return self._serve_script_file(_FLIGHT_DETAIL_TOGGLE_JS_PATH)
   ```
3. `do_GET()` dispatch — `companion/app.py:2479-2480`:
   ```python
   if path == FLIGHT_DETAIL_TOGGLE_SCRIPT_ROUTE:
       return self._serve_flight_detail_toggle_script()
   ```
4. Matching `layout.py` constant (duplicated, never imported — the documented cross-module convention every sibling constant states) — `companion/layout.py:167`: `THEME_PREVIEW_SCRIPT_SRC = "/static/theme-preview.js"` → add `FLIGHT_DETAIL_TOGGLE_SCRIPT_SRC = "/static/flight-detail-toggle.js"`.
5. `page_shell()`'s script-tag list — `companion/layout.py:1392`: append `FLIGHT_DETAIL_TOGGLE_SCRIPT_SRC` to the tuple.
6. Cross-file "route equals src" test in `companion/test_companion_app.py` — grep the file for the existing `THEME_PREVIEW_SCRIPT_ROUTE`/`THEME_PREVIEW_SCRIPT_SRC` agreement check (one of the `check(...)` sites in the 2900-3100 range covering the static-script contract loop) and add the same pattern for the new pair.

**`list-filter.js` one-line extension** (Structural Note 5, both docs): `applyFilter()`'s existing per-row loop (`list-filter.js:82-93`) sets `row.hidden = !matched;` keyed on `data-filter-group`; add one line inside the same loop to also hide the sibling `<tr class="flight-detail-row" id="flight-detail-{group}">` for the same group when `matched` is false — the sibling row does not itself carry `data-filter-text`, so it must be looked up by the shared group id and hidden in lockstep, never independently filtered.

---

### `history_page._history_table_html()`/`_HEADERS` (compacted, rewritten)

**Analogs:** `_merged_cell(primary, secondary)` (`history_page.py:565-589`) for the two-line primary/secondary cell shape the new "When" and "Flight" columns both need (per research Pitfall 4: use THIS pattern, never `layout.concise_timestamp_html()`'s one-line inline-suffix shape, which an earlier phase already reverted for width); `_callsign_hex_cell()` (`:644-687`) for the copy-button-after-value idiom, now relocated into the detail row; `_clock_cell_html()` (`:777-805`) for the clock-only cell, now the "When" column's primary line.

**`_HEADERS` change** (`history_page.py:141-143`):
```python
_HEADERS = (
    "Timestamp", "Callsign", "Type", "Route", "State", "Corroboration",
)
```
becomes 5 visible headers + one visually-hidden "Details" header (per 21-UI-SPEC.md §F's markup), e.g.:
```python
_HEADERS = ("When", "Flight", "Route", "State", "Corroboration")
```
(the sixth `<th>` for the toggle column carries `<span class="visually-hidden">Details</span>` directly in `_history_table_html()`, not via `_HEADERS`, since it has no data column to escape through the existing `i18n.t(h)` loop).

**New "When" cell** — reuse `_merged_cell()`'s exact two-`<span>` shape, fed from `_clock_cell_html()`'s own parsing (`local_clock_text()`) for the primary line and `layout.relative_age_text(age)` for the secondary line — do NOT reintroduce `concise_timestamp_html()`'s inline-suffix shape (Pitfall 4).

**New "Flight" cell** — same `_merged_cell()` shape: primary = callsign (mono), secondary = `"%s · %s" % (airline_label, aircraft_type_label)`. The copy buttons that used to live inline on this cell (`_callsign_hex_cell()`'s `_copy_button_html()` calls, `:670-684`) relocate into the detail row instead — this column no longer carries them.

**Corroboration, dot-only** — `layout.status_dot()` call (`history_page.py:834-836`) gains the new `visually_hide_label=True` keyword (see next entry) — the ONLY call site in the codebase to pass `True`; Health's own `status_dot()` calls stay unchanged (default `False`).

**Detail row** — one new `<tr class="flight-detail-row" id="flight-detail-{n}">` per main row, built from the SAME fields `_history_cards_html()`'s own `<details>` disclosure already renders (`history_page.py:952-978`: Hex + copy button, full ISO timestamp, Runway) — reuse those `<dt>`/`<dd>` pairs' exact escaping and copy-button calls, just re-wrapped in a `<dl class="flight-detail-row__grid">` instead of inside a `<details>` (which cannot wrap a `<tr>`, per D-15's own stated HTML constraint).

---

### `layout.status_dot(state, label, title=None, visually_hide_label=False)` (new keyword)

**Analog:** `stat_tile()`'s own `icon=None`/`caption_title=None` keyword-with-default precedent (`layout.py:1460-1517`) — "byte-identical when falsy" is the exact contract to restate:
```python
def status_dot(state, label, title=None, visually_hide_label=False):
    css_class = _STATUS_DOT_CLASSES.get(state, _DEFAULT_STATUS_DOT_CLASS)
    title_attr = ' title="%s"' % escape_html(title) if title else ""
    label_class = "dot-label visually-hidden" if visually_hide_label else "dot-label"
    return (
        '<span class="dot %s"></span><span class="%s"%s>%s</span>'
        % (css_class, label_class, title_attr, escape_html(label)))
```
Fully defaulted `False` so Health's own call sites (the only other consumer) render byte-identical output — only Flights' desktop-table corroboration cell passes `True` (21-UI-SPEC.md Structural Note 4).

---

### Simple mode / Health pause button removal (deletion-only)

No new pattern — this is deletion of phase-20's own additions. File:line inventory (already fully enumerated in `21-RESEARCH.md` Area E.1/E.2 and cross-verified live in this pass):

| File | Site | Action |
|---|---|---|
| `companion/prefs.py:34-61` | `MODE_CHOICES`, `DEFAULT_MODE`, `_MODE_CTX`, `simple_mode()`, `set_request_prefs()`'s `mode=` param | delete |
| `companion/auth.py:64` | `UI_MODE_COOKIE_NAME` | delete |
| `companion/app.py:220` | `MODE_ROUTE` | delete |
| `companion/app.py:1155-1165` | `_mode_from_request()` | delete |
| `companion/app.py:1275-1276,1304` | `prefs.set_request_prefs(..., mode=...)` call's `mode=` arg; `page_context()`'s `"simple_mode":` key | delete |
| `companion/app.py:2857-2869` | `_handle_mode_post()` | delete |
| `companion/app.py` `do_POST()` | `if path == MODE_ROUTE: ...` dispatch line | delete |
| `companion/layout.py:1010-1030` | `_mode_form_html()` | delete |
| `companion/layout.py:826-858` | `_nav_groups()`'s `simple = prefs.simple_mode()` read + `if simple and group_label == ADVANCED_GROUP_LABEL: continue` | delete gate, keep the loop |
| `companion/layout.py:1057-1126` | `_mobile_nav_html()`'s `mode_form_html=""` param + its footer slot | remove param, not just default |
| `companion/layout.py:1202-1274` (page_shell) | `resolved_mode`, `mode_form_html` build + both footer assemblies | remove; footer becomes `lang_form_html + theme_form_html + _logout_form_html()` |
| `companion/pages/home_page.py:300` | `if not ctx.get("simple_mode"):` gating the Health link | delete gate (coordinate with the D-04 rebuild — do not re-add after) |
| `companion/pages/config_page.py:670,2263-2266` | `CALENDAR_HOW_IT_WORKS_SIMPLE` + its `if simple_mode:` branch in `calendar_group()` | delete; keep only the `<details>` branch |
| `companion/pages/config_page.py:2146,3200` (approx, `calendar_group`'s own `simple_mode=False` param + its `render()` caller) | drop the parameter | delete |
| `companion/pages/config_page.py:575,2828,2844-2847` | `RULES_HOW_RULES_COMBINE_SIMPLE` + `_rules_section_html()`'s two `ctx.get("simple_mode")` reads | delete |
| `companion/pages/airlines_page.py:1849-1850` | `_edit_toggle_html()`'s `if ctx.get("simple_mode"): return ""` | delete (serves BOTH D-17 and D-20 — one deletion site, not two — Pitfall 6) |
| `companion/pages/health_page.py:343-344,2909-2925,2947-2949` | `REFRESH_PAUSE_TEXT`/`_RESUME_TEXT`, `toggle_html` build, its slot in `freshness_html`'s format tuple | delete |
| `companion/static/freshness.js:163,307-341,350,428-430,458-462,476` | `paused` var, `setToggleVisual()`, `wireToggle()`, both call sites, both `if (paused)` guards | delete (do NOT touch `stopLoop()`/`startLoop()`/the `document.hidden` branches) |
| `companion/i18n_fr/nav.py:34` | `"Simple mode": "Mode simple"` | delete (dead-translation risk) |
| `companion/i18n_fr/calendar_group.py`, `companion/i18n_fr/rules.py` | the two "Simple mode's collapsed disclosure sentence (D-30)" entries | delete in the SAME commit as their English constants (Pitfall 5) |

---

### `airlines_page._resolve_section_html()`/`_lightbox_html()` guard removal

**Analog:** the two guards themselves — a one-line gate deletion, not a new component (D-19/D-20, 21-UI-SPEC.md §H).

```python
# companion/pages/airlines_page.py:1733 — DROP the guard
upload_zone = _resolve_upload_form_html(upload_action, "") if edit_mode else ""
# becomes:
upload_zone = _resolve_upload_form_html(upload_action, "")

# companion/pages/airlines_page.py:1228 — DROP the identical guard
resolve_upload_html = _resolve_upload_form_html("", "-dialog") if edit_mode else ""
# becomes:
resolve_upload_html = _resolve_upload_form_html("", "-dialog")
```
`companion/pages/airlines_page.py:1727` (`delete_form = ... if edit_mode else ""`) and `:1229-1230` (`replace_html`/`delete_html`) **stay gated** — D-20 keeps replace/delete behind `?edit=1`. Do not touch these three sites.

---

## Shared Patterns

### `escape_html()` — universal escaping choke point
**Source:** `companion/layout.py`'s single `escape_html()` definition, imported by every page module. **Apply to:** every new dynamic string this phase interpolates, including the new masked-URL fragment, the nav reminder's dot-label text, and every `i18n.t(...)` call's return value (translated text is still plain text, never pre-escaped — the same explicit warning `20-PATTERNS.md`'s own Shared Patterns section states for `t()`).

### `check(name, fn)` test-harness convention
**Source:** `companion/test_companion_app.py:848` (`def check(name, fn): ...`), unchanged since phase 19/20. **Apply to:** every new/retargeted assertion in all 6 harnesses this phase touches.

### `EXPECTED_CHECK_COUNT` re-derivation
**Live baseline, verified 2026-09-12 (last assignment in each file):**

| File | Line | Current value |
|---|---|---|
| `companion/test_companion_app.py` | 433 | 267 |
| `companion/test_config_page.py` | 464 | 212 |
| `companion/test_status_pages.py` | 502 | 213 |
| `companion/test_view_pages.py` | 352 | 107 |
| `companion/test_i18n.py` | 44 | 24 |
| `companion/test_contrast_check.py` | 61 | 39 |

**Apply to:** after editing a harness, run it directly (`server/.venv/bin/python3 companion/<file>.py`), read the printed `N/M checks pass` line, and **append** a new `EXPECTED_CHECK_COUNT = M` assignment below the existing last one, with a comment citing this phase's plan/task number and the delta — never edit the old line in place, matching every prior phase's own convention (visible in the table of superseded assignments each file already carries).

### Duplicated-not-imported static-route contract (six touch points)
**Source:** `companion/app.py:187,582,1672-1678,2479-2480`; `companion/layout.py:167,1392`; the cross-file "route equals src" check family in `companion/test_companion_app.py`. **Apply to:** `companion/static/flight-detail-toggle.js` (new) — worked example above.

### `form="{form_id}"` cross-DOM submission idiom
**Source:** `companion/pages/config_page.py:1762,2127` (quick-action checkboxes), `:2261` (calendar's compact chip grid's `radio_form_id=SETTINGS_FORM_ID`). **Apply to:** every theme radiogroup inside the new Frame colours card (all three post through the physical `<form id="settings-form">` even though the card itself renders as that form's sibling — Structural Note 2), and the Calendar card's inline Disconnect button (`form="calendar-disconnect-form"`, 21-UI-SPEC.md §E).

### Fixed-class-lookup-with-fallback (`_STATUS_DOT_CLASSES` idiom)
**Source:** `companion/layout.py:182` (`_STATUS_DOT_CLASSES`), reused by `status_dot()`, `stat_tile()`, `status_row()`, `card_status_class()`. **Apply to:** the new `.dot--off` state (§B) is an ADDITIVE entry to this same dict/CSS register, never a second independent status-colour vocabulary.

### Native-hidden-radio + styled-`<label>` selectable-card idiom
**Source:** `.runway-card`, `.theme-chip` (`_theme_chip_grid_html()`), `.theme-option` (`_rule_kind_radio_html()`/`_theme_form_html()`). **Apply to:** the Frame colours card's 4-row `colour_usage` radiogroup (`.frame-colours__row`) — the fourth/fifth consumer of this one idiom, never a new selectable-card mechanism.

### Module docstring / decision-ID citation convention
**Source:** every group builder in `config_page.py`, every static script's header comment. **Apply to:** every new function this phase adds — open with the decision IDs (D-01..D-20) it implements, name the exact existing analog it reuses/relocates, and state the fallback/degrade contract for every new optional keyword.

---

## File-Overlap Table (waves, per R-14)

| File | A: Strip/Home/Nav | B: Frame colours | C: Calendar | D: Flights table | E: Simple mode/pause | F: Upload restore |
|---|---|---|---|---|---|---|
| `companion/pages/config_page.py` | extracts quick-action markup from `display_group()`/`quiet_hours_group()` | retires `theme_fieldset()`'s arrivals apparatus; rewrites `handle_post()`'s theme_arriving/calendar_theme_id block; relocates rules-row trigger | merges 3 calendar builders into 1 | — | deletes 2 `simple_mode` gates + 1 parameter | — |
| `companion/layout.py` | nav reminder, `page_shell()` signature, strip helper | — | — | — | deletes `_mode_form_html()`, `_nav_groups()`'s gate, footer parameter | — |
| `companion/app.py` | `_handle_quick_toggle()`'s redirect target/`return_to` | — | — | six-touch-point registration for the new script | deletes `MODE_ROUTE`, `_handle_mode_post`, cookie read, dispatch line, `page_context()`'s `mode=` arg | — |
| `companion/pages/home_page.py` | full rebuild (strip + tiles + reordered columns) | — | — | — | the health-link gate this rebuild must not resurrect | — |
| `companion/static/style.css` | strip layout, accent surface, `.dot--off` | Frame colours card layout, `:has()` block count | retires 2 fusion rules, adds `.text-link`/small-grey-button rules | table column widths, `.flight-detail-row*` | deletes mode-switch-specific rules if any | — |
| `companion/pages/airlines_page.py` | — | — | — | — | `_edit_toggle_html()`'s simple_mode gate (ONE deletion serves both E and F — Pitfall 6) | 2 upload guards |
| `companion/pages/history_page.py` | — | — | — | full table rebuild | — | — |
| `companion/static/list-filter.js` | — | — | — | one-line sibling-row-hide extension | — | — |
| `companion/pages/health_page.py` | — | — | — | — | pause button removal | — |
| `companion/static/freshness.js` | — | — | — | — | pause branch removal | — |
| `companion/static/theme-preview.js` | — | core rewrite (querySelectorAll/scoped-container) | — | — | — | — |
| `companion/prefs.py`/`auth.py` | — | — | — | — | deletion | — |
| `companion/i18n_fr/*` | additive (`nav.py` reminder strings; mostly relocated, no growth per §A) | additive (`display.py`) | additive (`display.py`) | additive (`flights.py`) | deletive (2 entries in `calendar_group.py`/`rules.py` + `nav.py`'s "Simple mode" entry) | — |
| Test harnesses | per-area | per-area | per-area | per-area | per-area (heaviest — 4 files) | per-area |

**Sequencing implication (unchanged from 21-RESEARCH.md):** B and C both rewrite adjacent slices of `config_page.py`'s Display-scope `render()` assembly and the `:has()`-block-count-pinned CSS — sequence, do not parallelize. A also touches `config_page.py`'s `display_group()`/`quiet_hours_group()` (to strip the quick-action markup out) — a third writer of the same file, so A should land before or in the same single-writer wave as B/C's `config_page.py` edits, not interleaved with a second executor. D and E share almost no files and are the safest fully-parallel pair. F is a two-line change, safely parallel with everything except the one shared `_edit_toggle_html()` deletion site (own it in E, not F — Pitfall 6).

---

## Test Harness Check Names Pinned by This Phase (grep `check("`/`def _`, grouped by area)

### Area A (strip / Home rebuild / nav reminder)
- `companion/test_view_pages.py`:
  - the `.preview-frame`-before-`.status-card` document-order check (~line 3595-3603, "expected .preview-frame before .status-card in document order (D-18)") — **must be rewritten**: `.status-card`/`.home-hero` no longer exist; retarget to assert the new strip → tiles → picture/flights order.
  - `home_page._status_card_html()`'s direct-call checks (~lines 3812-3838: the `status-card__headline`/`--warn` future/past/missing-checkin/missing-interval checks) — retarget to call the new strip helper instead of `_status_card_html()` (which is deleted).
  - the `FRAME_ROW_LABEL`/`BATTERY_ROW_LABEL`/`DATA_ROW_LABEL`/`FRAME_STATE_TEXT` count checks (~lines 3683-3684, 3789-3793) — content-derivation is preserved, so these should still pass once retargeted at the tile markup instead of the status-row markup.
  - `_home_status_card_health_link_gated_by_simple_mode` (~3846-3862) — **delete outright** (D-17 removes the gate; do not re-add as an "always shown" check unless a plan wants explicit coverage).
- `companion/test_companion_app.py`:
  - the quick-toggle redirect-target checks (grep `_handle_quick_toggle`/`QUICK_DISPLAY_ROUTE`/`QUICK_QUIET_HOURS_ROUTE` in the 2900-2965 range) — retarget to assert `return_to` round-trips to `/` when posted from Home and to `/display` when posted from Display, plus the fallback-to-Display behavior when `return_to` is absent/invalid.
- New checks needed (no existing analog to retarget): the nav-reminder text/dot-state check (both languages), the `page_shell(device_config=...)` degrade-to-no-reminder-when-`None` check.

### Area B (Frame colours)
- `companion/test_config_page.py`:
  - `_theme_arriving_markup_both_grids_copy_and_checkbox_present` (~3327), `_theme_arriving_override_preselects_second_grid_and_checks_the_box` (~3394) — **delete/rewrite**: the checkbox is gone.
  - `_handle_post_theme_arriving_checked_persists_chosen_id` (~3416), `_handle_post_theme_arriving_checkbox_absent_clears_previous_override` (~3440) — **rewrite**: the clear signal is now `theme_arriving=""`, not checkbox-absence.
  - `_handle_post_crafted_theme_arriving_checkbox_value_rejected` (~3476) — **delete**: no checkbox value to craft against; add a new "crafted empty-string-adjacent value still membership-tested" check if coverage is wanted.
  - `_handle_post_nonmember_theme_arriving_rejected` (~3498) — keep, but confirm `""` is explicitly exempted from this rejection (new assertion).
  - `_handle_post_theme_arriving_partial_post_still_carries_other_fields` (~3527), `_theme_arriving_clearable_contract_full_round_trip` (~3558) — retarget to the new empty-string clear mechanism.
  - `_settings_form_raw_post_no_js_clears_and_sets_theme_arriving` (~6164) — retarget.
  - `_calendar_theme_chip_grid_exactly_one_compact_radiogroup_populated_in_order` (~4656), `_calendar_theme_chip_grid_saved_value_is_checked` (~4683), `_calendar_theme_chip_grid_defaults_to_base_theme_when_unset` (~4702) — **move/rewrite**: this grid no longer lives in `calendar_group()`'s own card; retarget at the Frame colours card's "calendar" usage panel.
  - the two pinned `@supports selector(:has(*))` block-count checks (grep `test_config_page.py` for `feature-query`/`:has(`) — **re-derive the count**, per `style.css:2190-2192`/`:5359-5362`'s own comments (Wave-0 gap, not yet read to exact line in this pass — read before landing B).
- `companion/test_i18n.py`: no existing check to retarget; add new completeness coverage for the 6+ new English keys in §D's copy table (Frame colours heading, 4 row labels, meta strings, chip label).

### Area C (Calendar merge)
- `companion/test_config_page.py`:
  - `_calendar_placement_after_display_before_form_close_with_dirty_attr` (~4719), `_calendar_group_no_inline_js_and_chip_grid_within_form` (~4748) — **rewrite**: no chip grid in this card any more; the "before form close" placement claim needs re-verifying against the merged single-card shape.
  - `_calendar_connect_field_never_carries_value_in_either_state` (~4872), `_calendar_connect_wraps_in_details_only_when_configured` (~4893) — keep, retarget at the merged card's markup location.
  - `_calendar_containment_at_the_renderer_five_needles` (~4913) — **rewrite the needle count/shape**: the card boundary moves.
  - `_calendar_disconnect_checkbox_never_appears_in_calendar_group` (~4945), `_calendar_disconnect_section_appears_only_when_expected` (~4963) — retarget at the merged card + the new inline `form="calendar-disconnect-form"` button.
  - `_calendar_disconnect_form_is_not_inside_settings_form_on_display_scope` (~5014) — keep the assertion, retarget its DOM-location expectation.
  - `_calendar_connect_form_appears_before_the_runway_card_on_display_scope` (~5036) — verify still true after the merge; retarget if the document order shifts.
  - `_calendar_secret_never_reaches_render_function`/`_calendar_secret_never_reaches_served_http_bytes` (~4543, ~6325) — **keep and extend**: also assert the new masked-URL fragment never contains a path/query/token character (Security Domain requirement).
  - the two CSS `:has()`-fusion-rule-referencing checks (if any pin `.calendar-disconnect-form`'s own border-radius rule) — delete along with the CSS rule itself (Pitfall 2).

### Area D (Flights table)
- Ownership confirmation needed first (Wave-0 gap, both docs flag this): grep `history_page`/`GET /flights` in `test_view_pages.py`/`test_companion_app.py`/`test_status_pages.py` to find the live owner before retargeting.
- Any check asserting `_HEADERS`' current 6-tuple content (`"Timestamp", "Callsign", "Type", ...`) — rewrite to the new 5-header set.
- Any check asserting the desktop table's column count or the absence of a runway/hex/full-timestamp column — rewrite to assert their presence in the NEW detail row instead.
- New checks needed: the `visually_hide_label=True` corroboration cell (assert no visible dot-label text, but the accessible name/title unchanged); the detail-row toggle's `aria-expanded`/`aria-controls` pair; the six-touch-point registration triplet for `flight-detail-toggle.js`; `list-filter.js`'s sibling-detail-row-hide behavior (real-HTTP or a dedicated JS-behavior note, since this harness suite is Python-only — flag if this needs a headless-sweep assertion instead).

### Area E (simple mode / pause button — heaviest)
- `companion/test_companion_app.py`: `_ui_mode_post_round_trip` (4223), `_ui_mode_post_without_session_redirects_to_login` (4254), `_make_simple_mode_nav_hidden_check` factory (7130) + its loop-generated checks (7150-7155), `_home_hides_health_link_in_simple_mode` (7157), `_airlines_hides_change_pictures_button_in_simple_mode` (7170), `_display_disclosures_collapse_to_one_sentence_in_simple_mode` (7183), `_display_still_carries_all_six_everyday_groups_in_simple_mode` (7203), `_health_and_device_still_reachable_by_url_in_simple_mode` (7221), `_flights_and_airlines_keep_their_full_content_in_simple_mode` (7235), `_simple_mode_survives_three_sequential_requests` (7250), `_make_full_mode_nav_shown_check` factory (7269) + its loop-generated checks (7287-7292) — **delete all** (the mechanism they test no longer exists).
- `companion/test_config_page.py`: `_rules_simple_mode_collapses_disclosure_to_one_sentence` (4322) — **delete**.
- `companion/test_status_pages.py`: `_shell_has_three_ordered_theme_forms_each_with_aria_label`'s own body (the check function around line ~6420-6466, asserting exactly 2 `/ui-mode` forms and a 3-element `lang/theme/mode` order) — **rewrite**: becomes exactly 2 `/ui-lang` + 2 `/ui-theme` forms and a 2-element `["/ui-lang", "/ui-theme"]` order, not a deletion of the whole check. `_simple_mode_omits_advanced_group_and_health_dot` (6485) — **delete** (the mechanism it tests, `prefs.simple_mode()`-gated Advanced-group omission, is gone; the Advanced group is now always shown).
- `companion/test_view_pages.py`: `_airlines_simple_mode_render_has_no_toggle_or_caption` (2992), `_airlines_simple_mode_and_edit_mode_still_renders_lightbox_forms` (3004) — **delete**. `_home_status_card_health_link_gated_by_simple_mode` (3846) — **delete** (cross-referenced in Area A above — one deletion, not two).
- `companion/test_i18n.py`: `_check_prefs_unknown_mode_leaves_simple_mode_false`, `_check_prefs_simple_mode_true_for_simple` (~628-654) — **delete**. `_check_d08_no_dead_translations()` (777-797) — **keep, but verify green**: it will fail unless `CALENDAR_HOW_IT_WORKS_SIMPLE`/`RULES_HOW_RULES_COMBINE_SIMPLE`'s FR catalogue entries are deleted in the same commit as their English constants (Pitfall 5).
- Health pause-button checks: grep `test_status_pages.py`/`test_view_pages.py` for `data-pause-text`/`REFRESH_PAUSE_TEXT`/`data-refresh-toggle` (Wave-0 gap, not yet located to exact line in this pass) — delete once found.

### Area F (Airlines upload restore)
- `companion/test_view_pages.py`: `_airlines_default_render_has_no_edit_only_forms` (2903-2916) — **rewrite**: currently asserts `airlines_page.RESOLVE_UPLOAD_ZONE_CLASS` is absent from a default (`edit_mode` absent) render; per D-19 this token must now be **present** unconditionally in Step B (name saved, no artwork) — drop `RESOLVE_UPLOAD_ZONE_CLASS` from this check's asserted-absent tuple, and add a new check asserting its presence in a default render whose entry has a saved name and no artwork.
- `companion/test_view_pages.py`: `_airlines_edit_mode_render_has_exactly_one_of_each_edit_only_form` (2932-2951) — verify `RESOLVE_UPLOAD_ZONE_CLASS`'s count expectation still holds (it should — this checks `edit_mode=True`, which is unaffected; the upload zone was already present there).
- `companion/test_view_pages.py`: the lightbox-dialog equivalent check (grep for `_resolve_upload_form_html("", "-dialog")`/dialog-suffixed class names near lines 2394-2398, 2725-2727) — same rewrite as above, for the lightbox's own upload affordance.
- `_edit_toggle_html`'s simple-mode gate is tested by Area E's own checks (`_airlines_simple_mode_and_edit_mode_still_renders_lightbox_forms`, etc.) — do not add a second F-owned check for the same deletion (Pitfall 6).

---

## No Analog Found

None — every unit this phase introduces or rewrites is a relocation, merge, or additive-keyword extension of a builder/script that already exists in this exact codebase from phases 15-20. The one genuinely new piece of logic (the masked-calendar-URL helper, Area C) still follows an existing module's fail-soft/never-raise convention family even though no prior function does exactly this.

## Metadata

**Analog search scope:** `companion/layout.py`, `companion/app.py`, `companion/pages/config_page.py`, `companion/pages/home_page.py`, `companion/pages/history_page.py`, `companion/pages/health_page.py`, `companion/pages/airlines_page.py`, `companion/static/theme-preview.js`, `companion/static/freshness.js`, `companion/static/list-filter.js`, `companion/i18n_fr/__init__.py`, `companion/i18n_fr/home.py`, `companion/test_companion_app.py`, `companion/test_config_page.py`, `companion/test_status_pages.py`, `companion/test_view_pages.py`, `companion/test_i18n.py`, `server/device_config.py` (referenced, not modified).
**Files/ranges read directly (Read/Grep), 2026-09-12:** `layout.py` (status_dot/stat_tile/card_status_class/status_row/section_intro_html, `_nav_groups`/`sidebar_nav`/`_theme_form_html`/`_lang_form_html`/`_mode_form_html`/`_logout_form_html`/`_mobile_nav_html`/`login_shell`/`page_shell` in full); `app.py` (`_lang_from_request`/`_mode_from_request`/`page_context`/`_referring_tab`/`_page_shell_for`/`_render_tab`/`_handle_quick_toggle`/`_handle_theme_post`/`_handle_lang_post`/`_handle_mode_post` in full, plus the six-touch-point constants for `theme-preview.js`); `config_page.py` (`quiet_hours_group`/`display_group` in full, `_theme_chip_grid_html`/`_theme_live_preview_html`/`theme_fieldset` in full, `calendar_group`/`calendar_connect_section`/`calendar_disconnect_section` in full, `_rule_kind_radio_html`/`_rule_add_form_html`/`_rule_suggestion_chips_html`/`_rule_row_html`/`_rule_list_html`/`_rules_section_html` in full, `handle_post()`'s theme/calendar validation+resolution block); `home_page.py` (`_status_card_html`/`_hero_figure_html`/`_recent_flight_thumb_html`/`_recent_flights_html`/`render` in full); `history_page.py` (`_HEADERS`, `_merged_cell`/`_copy_button_html`/`_callsign_hex_cell`/`_type_airline_cell`/`_filter_bar_html`/`_clock_cell_html`/`_history_table_html`/`_history_cards_html`); `health_page.py` (pause-button constants/build sites); `airlines_page.py` (the four upload/replace/delete guards, `_edit_toggle_html`); `theme-preview.js` (full, 81 lines); `freshness.js` (pause mechanism grep); `list-filter.js` (`applyFilter()` in full); `i18n_fr/__init__.py` (full), `i18n_fr/home.py` (header); `test_companion_app.py`/`test_config_page.py`/`test_status_pages.py`/`test_view_pages.py`/`test_i18n.py` (targeted greps for `EXPECTED_CHECK_COUNT`, simple-mode/ui-mode/theme_arriving/calendar/edit_mode/upload check names).
**Pattern extraction date:** 2026-09-12
**Valid until:** tied to the exact commit state read above; re-verify file:line references and `EXPECTED_CHECK_COUNT` values if planning is delayed more than a few days, matching `21-RESEARCH.md`'s own validity note.

## Wave-0 gaps resolved by the orchestrator (2026-09-12)

- **Flights/History checks live in `companion/test_view_pages.py`** (152 `history_page.` references; the other harnesses hold one reference each — the route smoke in `test_companion_app.py`, the i18n completeness enumeration in `test_i18n.py`, one shell check in `test_status_pages.py`). Area D's retargeting is owned by whichever plan edits `history_page.py`, in `test_view_pages.py`.
- **The `@supports selector(:has(*))` block-count pin** is the check around `companion/test_config_page.py:3712-3760` (`supports_marker = "@supports selector(:has(*)) {"`, `_rule_body(".theme-chip:has(input:checked) {")`), with its history in the pin comment at lines 172 and 215. Retiring the calendar fusion rules (R-08) changes the count of `@supports selector(:has(*))` blocks; the Area C plan re-derives that check's expected count in the same task.
