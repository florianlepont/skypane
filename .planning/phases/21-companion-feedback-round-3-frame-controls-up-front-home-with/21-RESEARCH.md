# Phase 21: Frame controls up front, Home with three tiles, one Frame colours view, calendar tile, compact flights table, simple mode removed, artwork upload restored - Research

**Researched:** 2026-09-12
**Domain:** Python stdlib HTTP service (`companion/`), server-rendered HTML, ES5 vanilla JS static assets, restructuring six already-shipped surfaces (frame strip/nav, theme-picker consolidation, calendar card fusion, flights table compaction, simple-mode/pause-button removal, artwork-upload gate relaxation) — no new external dependency in any of the six areas, no server/API seam changes (all routes and validators this phase touches already exist since phases 16-20)
**Confidence:** HIGH — every claim below is grounded in a direct `Read`/`Grep` of the live code (commit `614d41e`, branch `claude/web-companion-audit-ux-refactor-bqx7si`) or a live inspection of the running-app headless-sweep scripts already in the session scratchpad; no library/API research was needed anywhere in this phase

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

Every decision below is locked (it comes from the PRD, which records the developer's own requests verbatim and the orchestrator's proposal the developer approved for points 2/3/8, 4/5 and 6/7). Full text of D-01..D-20 is in `21-CONTEXT.md` and is not repeated verbatim here — only the letter-groups and headline claims are named for cross-reference; the planner MUST read `21-CONTEXT.md` directly for the exact wording.

- **A. Frame controls up front** (D-01..D-05, CFG-19) — a shared "Frame" strip (Screen switch, Quiet hours switch, next update as the largest text) at the top of Home and Display; a state-only reminder link in the nav; Home rebuilt as strip → three phase-19 stat tiles → picture and recent flights side by side; the phase 20 single status card deleted.
- **B. One "Frame colours" view** (D-06..D-12, CFG-20) — the four theme chip grids (departures, arrivals, calendar, rules) become one card: live preview left, four-row assignment radiogroup right, one chip grid for the selected row, "Same as departures" chips for arrivals and calendar, the rule list and add form under the rules row; `theme-preview.js` extended (ES5, no HTML sink); a no-JS floor that still saves every value.
- **C. Calendar in one tile** (D-13..D-14, CFG-21) — status + URL field/connect button in one card; once connected a masked URL, a "Replace the feed URL" `<details>` link and a small grey "Disconnect" secondary button that still confirms.
- **D. Compact Flights table** (D-15..D-16, CFG-22) — five merged columns that fit 1280 px in FR and EN; hex, ISO timestamp, runway and copy button in an expandable detail row; phone cards unchanged.
- **E. Simple mode and the Health pause button removed** (D-17..D-18, CFG-23) — prefs/cookie/route/nav switch/gates/tests/catalogue entries deleted; `freshness.js` pause branch deleted.
- **F. Artwork upload restored in the resolve flow** (D-19..D-20, CFG-24) — the step-B upload zone is unconditional again; "Change pictures" keeps only replace/delete of existing artwork.

### Claude's Discretion
- Exact CSS class names and internal layout of the strip and the Frame colours card, within the design-system skill's tokens and the phase 21 UI-SPEC.
- Whether the strip helper lives in `companion/layout.py` or a new `companion/pages/frame_strip.py` — one write site is the requirement.
- Whether the flights detail-row toggle is a new ES5 file or an extension of an existing static script — the six-touch-point contract applies to a new file.
- How the four no-JS chip grids are collapsed to one by script (a class the script adds at load, matching the D-15 pattern, is the expected shape).
- Which existing tests are retargeted versus deleted when the simple-mode checks go, as long as every `EXPECTED_CHECK_COUNT` pin is updated and no behaviour outside D-17 loses coverage.

### Deferred Ideas (OUT OF SCOPE)
- Any further Home widgets (the developer wants Home glanceable, not busy).
- Per-screen state directories (the `screen_id` seam from phase 19 stays as is).
- A third UI language.
- Any change to the frame firmware or to the panel renderer's output.
- Runway, Screen on/off (beyond moving the instant switch into the strip) and Quiet hours behaviour.
- The battery chart, the poll countdown, the "State" read-aloud text, per-browser persistence of language/theme choice, notifications, the Device page, the theme preview renderer, the panel renderer, the on-disk state layout, any change to how the catalogue works.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description (REQUIREMENTS.md) | Research Support |
|----|-------------|------------------|
| CFG-19 | Frame strip (Screen, Quiet hours, next update) at top of Home/Display; nav state reminder; Home = strip + 3 tiles + picture/recent-flights row | Area A below: exact `quick-action-slot` markup to extract (`config_page.py:1732`/`2098`), `_handle_quick_toggle`'s hardcoded redirect target (`app.py:2787-2826`) vs. the already-shipped `_referring_tab()` pattern, the phase-19 three-tile shape (`git show 614d41e~1`), `layout.status_dot()`/`stat_tile()` signatures |
| CFG-20 | One "Frame colours" card (preview left, 4-row assignment list right) replaces the 4 chip grids; no-JS floor still saves every value | Area B below: every `_theme_chip_grid_html()` call site, `theme_fieldset()`'s two-grid structure, the checkbox-driven `theme_arriving` resolution `handle_post()` must lose, the rules section's own card and chip grid |
| CFG-21 | Calendar status + URL in one card; connected state shows masked URL, "Replace" link, small grey "Disconnect" | Area C below: `calendar_group()`/`calendar_connect_section()`/`calendar_disconnect_section()` are three separate render calls today, fused visually only by a `:has(+ .calendar-disconnect-form)` CSS rule — genuine restructuring required |
| CFG-22 | 5-column Flights table fits 1280px in both languages; hex/ISO/runway/copy move to an expandable detail row; phone cards unchanged | Area D below: current 6-header table (`_HEADERS`, `history_page.py:141`), the real available width arithmetic (880px, not 1280px), the `<details>`-inside-`<table>` impossibility that forces a new `data-row-toggle` script |
| CFG-23 | Simple/full mode switch, cookie, route, every gate, and the Health pause button all removed | Area E below: full `simple_mode`/`MODE_*`/`ui-mode`/pause grep inventory with file:line, the ~16+ test checks and 2 catalogue-orphaning risks this creates |
| CFG-24 | Upload zone unconditional again in resolve-flow step B; "Change pictures" keeps only replace/delete | Area F below: the exact two `if edit_mode` guards to drop (`airlines_page.py:1733`/`1228`) vs. the two guards that must stay (`airlines_page.py:1727`/`1229`/`1230`) |
</phase_requirements>

## Summary

This phase is entirely a restructuring of code that phases 18-20 already shipped — there is no new library, API, or protocol to learn, and the server-side validators/routes this phase touches (quick-toggle routes, calendar connect/disconnect, theme fields, rules routes) are all unchanged in shape. The real risk, exactly like phase 20's own research found twice, is **a locked decision's plain-English description colliding with an HTML/JS constraint the current markup already has baked in** — this phase has at least four of that shape, found by direct read:

1. **D-01's "redirect back to the page they were pressed on" is not what `_handle_quick_toggle` does today.** Both `/quick/display` and `/quick/quiet-hours` hardcode `layout.DISPLAY_ROUTE` as their redirect target (`app.py:2814`, `:2826`) — never the referer. The exact mechanism D-01 needs already exists one function away: `_referring_tab()` (`app.py:2376-2383`), which `_handle_theme_post()`/`_handle_lang_post()`/`_handle_mode_post()` already call. `_handle_quick_toggle` must be changed to call it too.
2. **D-09's "server-side semantics are unchanged" undersells a real handler rewrite.** `theme_arriving`'s clear-vs-set distinction is derived today from a checkbox field (`theme_arriving_enabled`) that D-09 deletes outright — `handle_post()`'s resolution block (`config_page.py:3941-3960`) is keyed on that checkbox, not on `theme_arriving`'s own value, "specifically because" (the code's own docstring) a present `theme_arriving` can never by itself mean "clear". With the checkbox gone, the empty-string "Same as departures" chip must become the clear signal instead — but the membership check five lines earlier (`config_page.py:3918-3923`) currently rejects `""` as `ERROR_INVALID_CHOICE` before the resolution block ever runs. Both sites must change together, or this phase ships an option that always fails to save.
3. **D-13's "one Calendar card" is two `<form>`s plus a third confirmed-disconnect form, fused only by CSS.** `calendar_group()` (status + chip grid, `config_page.py:2143-2292`), `calendar_connect_section()` (URL field, its own `<form>`, `:2295-2369`) and `calendar_disconnect_section()` (its own `<form>`, `:2372-2418`) are three separate `render()` return-value concatenations today, visually joined only by `.page-section:has(+ .calendar-disconnect-form)` (`style.css:2193`) and `.calendar-disconnect-form`'s own border-radius hack (`style.css:5369-5381`). D-13/D-14 require literally merging their markup into one `<div>`/card, which means retiring both CSS fusion rules and re-deriving the visual result from real nesting instead.
4. **D-15's five-column table must fit ~880px, not 1280px.** `.dashboard-shell`'s sidebar column is 240px plus a 32px gap (`style.css:4112-4117`); `.dashboard-main` then adds 64px of horizontal padding on each side (`style.css:4171-4177`). At a 1280px viewport with the sidebar open, the real content column is `1280 - 240 - 32 - 64 - 64 = 880px` — the exact number a pre-existing code comment already names ("a 1,305px table that had to fit an 880px column", `history_page.py:696-699`). The acceptance criterion's "1280 px" is the viewport, not the budget.

Beyond these four, D-17's simple-mode removal is large but entirely mechanical: a complete `grep` inventory (below) finds every reference across `companion/` — one route, one cookie, one prefs module, ~16 checks in `test_companion_app.py` plus 1 each in `test_config_page.py`/`test_i18n.py`, and two FR catalogue entries (`CALENDAR_HOW_IT_WORKS_SIMPLE`, `RULES_HOW_RULES_COMBINE_SIMPLE`) that become "dead translations" the moment the English constants they translate are deleted — `test_i18n.py`'s own `_check_d08_no_dead_translations()` (`test_i18n.py:777-797`) will fail on exactly these two unless the FR entries are deleted in the same commit.

**Primary recommendation:** Sequence the six areas so B (Frame colours) and C (Calendar) — both of which touch `config_page.py`'s theme/calendar machinery and `render()`'s Display-scope assembly — do not land in the same wave as a naive parallel split; A (frame strip) also touches `config_page.py`'s `display_group()`/`quiet_hours_group()` (to strip the quick-action markup out) and `layout.py`'s nav renderers, so it shares files with B/C too. D (Flights table) and E (simple mode) are the most independent pair — the table lives entirely in `history_page.py`, and E's deletions are cross-cutting but touch different call sites than A/B/C's additions. F (artwork upload) is a two-line change in `airlines_page.py`, safely parallel with everything else. See the file-overlap matrix in the Cross-Cutting section.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Frame strip (Screen/Quiet-hours switches, next-update text) | API/Backend (`companion/layout.py` or new `frame_strip.py`, server-rendered) | Browser (native form POST, no JS) | Every value comes from `ctx["device_config"]`/`ctx["last_checkin_ts"]`, already resolved server-side; the switches are plain forms posting to existing routes |
| Nav state reminder | API/Backend (`companion/layout.py`'s nav renderers) | — | Text and dot colours computed server-side from the same `ctx["device_config"]` the strip reads; explicitly "no script" per D-03 |
| Frame colours selection UI (radiogroup → chip grid swap, preview swap) | Browser (`companion/static/theme-preview.js`, extended) | API/Backend (server renders every no-JS fallback state) | The script only ever toggles visibility/targets already-rendered markup; the server is the source of truth for every value it manipulates (D-08's no-JS floor requirement) |
| Calendar connect/disconnect/replace | API/Backend (`companion/pages/config_page.py`, three existing dedicated routes) | Browser (`<details>` for the inline reveal, `confirm-submit.js` for the disconnect misclick guard) | All three routes and their validators already exist (phase 16/19/20); this phase only changes how their markup nests, never their POST semantics |
| Flights table detail-row expansion | Browser (a new/extended ES5 static script toggling a class) | API/Backend (`companion/pages/history_page.py` renders both `<tr>`s always) | `<details>` cannot wrap a second `<tr>` inside a `<tbody>` — this is a genuine JS requirement, not a "don't hand-roll" violation, because there is no HTML-native disclosure primitive for table rows |
| Simple-mode removal | API/Backend (delete-only: `companion/prefs.py`, `companion/auth.py`, `companion/app.py`, `companion/layout.py`, page modules) | Browser (`freshness.js`'s pause branch) | Presentation-only feature being removed; no data migration, no access-control implication (D-30 already documented it as "never access control") |
| Artwork upload gating | API/Backend (`companion/pages/airlines_page.py`, two guards relaxed, two kept) | — | Purely a server-side conditional-rendering change; no route or validator changes |

## Standard Stack

No new library, framework, or package is introduced by this phase — confirmed by the full decision set (D-01..D-20): every mechanism is either already-shipped code being moved/merged/deleted, or a small ES5 extension to an already-shipped static script. Python stdlib only (`companion/` has no external runtime dependency beyond what's already installed); the one new JS behaviour (D-15's row-toggle) is a `data-*`-attribute-driven vanilla-JS addition following the codebase's own established "six-touch-point static-script contract" (see Cross-Cutting below).

**Package Legitimacy Audit:** Not applicable — zero external packages installed by this phase in any ecosystem.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Redirect-back-to-referring-page | A new per-route referer-parsing helper | `Handler._referring_tab()` (`app.py:2376-2383`) — already used by `_handle_theme_post()`/`_handle_lang_post()`/`_handle_mode_post()` | One function, already whitelist-validated against `layout.NAV_TABS`, already the exact behaviour D-01 asks for |
| Status-coloured row/tile markup | A new coloured-row component | `layout.status_row()` (`layout.py:1551-1597`) / `layout.stat_tile()` (`layout.py:1460-1517`) / `layout.status_dot()` (`layout.py:1435-1457`) | All three already exist from phases 18-20 and already whitelist the `state` string against `_STATUS_DOT_CLASSES` — reuse, do not add a fourth status-colour primitive |
| Section heading + one-sentence intro | A new markup helper | `layout.section_intro_html(section_id, heading, description)` (`layout.py:1600+`) — already used by Display's three supersections | Exact shape the Frame colours card's own intro line needs, if the UI-SPEC wants one |
| Segmented control (radiogroup styled as pill row) | New CSS for the colour_usage 4-row picker | `.theme-form`/`.theme-option` (native radios hidden, styled `<label>`s) — already the third consumer for `_rule_kind_radio_html()` (`config_page.py:2581-2605`) and the language/theme/(soon-removed)mode nav-footer switches | This is the exact "native radio + visually-hidden + styled label" idiom the codebase uses everywhere a small segmented choice is needed; the Frame colours radiogroup is the fourth consumer, not a new pattern |
| Chip grid rendering (theme swatches, selectable cards) | A new grid builder for the Frame colours card | `_theme_chip_grid_html()` (`config_page.py:966-1070`) — already parameterised for compact/regular, `radio_form_id`, `extra_class`/`extra_attr`/`chip_extra_class` | Already the single shared builder for departures/arrivals/calendar/rules grids; the "one chip grid, shown for whichever usage is selected" requirement is this same function called with a different `field_name`, not a new one |
| Misclick confirmation on a destructive form | A new confirm dialog | `data-confirm`/`companion/static/confirm-submit.js` (already generic — any `form[data-confirm]`) | The Disconnect button already uses this exact mechanism (`calendar_disconnect_section()`, `config_page.py:2406-2418`) — the small/grey/secondary restyling changes nothing about the confirm wiring |
| Inline expand/collapse with no script | `<details>`/`<summary>` | Already used for "Replace the feed URL" (D-14, needs this exact element), "How it works"/"How rules combine" disclosures, and the mobile Flights card's "More details" (`history_page.py:952-963`) | D-15's own text says a `<details>`-free implementation is impossible *inside a table* — this constraint is real (HTML forbids `<details>` as a `<tr>`'s wrapper), but everywhere else in this phase `<details>` remains the right no-JS-cost primitive |

**Key insight:** every visual/interaction primitive this phase's six decisions need already exists somewhere in this codebase from phases 18-20 — the work is "reuse the existing primitive on a new surface" or "delete an existing surface cleanly," almost never "invent something new." The one genuine exception is D-15's table row-toggle, which needs new JS specifically because `<details>` cannot legally wrap a table row.

## Package Legitimacy Audit

Not applicable — this phase installs zero external packages in any ecosystem.

## Area A: Frame controls up front (D-01..D-05, CFG-19)

### A.1 — The quick-action-slot markup to extract

Both instant switches are built inline, today, inside the two group builders D-02 says must lose them:

- **Quiet hours switch:** `quiet_hours_group()` (`companion/pages/config_page.py:1597-1789`). The `quick_action_html` block is built at lines **1718-1754**; it posts to `/quick/quiet-hours`, reads `current_enabled`/`current_start`/`current_end` (all three are the group's own function parameters, already threaded from `render()`), and is interpolated into the card's return string as the `%s` right after the caption (line 1764/1776 in the format tuple).
- **Screen switch:** `display_group()` (`companion/pages/config_page.py:2033-2140`). The `quick_action_html` block is built at lines **2090-2120**; it posts to `/quick/display`, reads `current_display_enabled`, interpolated the same way (line 2125/2135).
- Both blocks share one exact structure — `.quick-action-slot` > `.quick-action.quick-action--on|off` > (`.quick-action__text` with icon+label+state) + `.quick-action__form` (a real `<form method="post" action="/quick/…">` with a hidden `state` input and a submit button) — plus a shared `<p class="text-label section-caption">` reading `QUICK_ACTION_APPLIES_SENTENCE` ("Applies the next time the frame wakes up."). This is exactly the content D-01 wants moved into the shared strip.
- Constants: `QUICK_ACTION_SCREEN_LABEL`/`_ON_TEXT`/`_OFF_TEXT`/`_SWITCH_ON_BUTTON`/`_SWITCH_OFF_BUTTON`/`QUICK_ACTION_QUIET_LABEL`/`_QUIET_ON_TEMPLATE`/`_QUIET_OFF_TEXT`/`_QUIET_TURN_ON_BUTTON`/`_QUIET_TURN_OFF_BUTTON`/`QUICK_ACTION_APPLIES_SENTENCE` all live at `config_page.py:433-446`. These can move to the shared strip helper's own module (or stay in `config_page.py` and be imported by `home_page.py` — **not possible**: `companion/pages/__init__.py` forbids one page module importing another. This is why D-01 itself proposes either a new `companion/pages/frame_strip.py` or a function in `companion/layout.py` — either is a legal import target for both `home_page.py` and `config_page.py`).

### A.2 — `_handle_quick_toggle`'s redirect target (the real gap in D-01)

```python
# companion/app.py:2787-2826 (current)
def _handle_quick_toggle(self, field):
    form = self.read_form()
    state = form.get(layout.QUICK_STATE_FIELD)
    if state not in (layout.QUICK_STATE_ON, layout.QUICK_STATE_OFF):
        return self.redirect(
            "%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(FLASH_KEY_QUICK_FAILED)))
    enabled = state == layout.QUICK_STATE_ON
    if field == "display_enabled":
        kwargs = {"display_enabled": enabled}
        flash_key = FLASH_KEY_DISPLAY_ON if enabled else FLASH_KEY_DISPLAY_OFF
    else:
        kwargs = {"quiet_hours_enabled": enabled}
        flash_key = FLASH_KEY_QUIET_ON if enabled else FLASH_KEY_QUIET_OFF
    try:
        device_config.save_device_config(self.args.state_dir, **kwargs)
    except (ValueError, OSError):
        flash_key = FLASH_KEY_QUICK_FAILED
    return self.redirect("%s?flash=%s" % (layout.DISPLAY_ROUTE, quote(flash_key)))
```

Every one of the three `self.redirect(...)` calls hardcodes `layout.DISPLAY_ROUTE`. D-01 requires "redirect back to the page they were pressed on" (Home or Display). The exact, already-shipped mechanism to reuse is `_referring_tab()`:

```python
# companion/app.py:2376-2383 (existing, used by theme/lang/mode POST handlers)
def _referring_tab(self):
    referer = self.headers.get("Referer", "")
    try:
        path = urlsplit(referer).path
    except ValueError:
        path = ""
    allowed = {route for route, _ in layout.NAV_TABS}
    return path if path in allowed else HOME_ROUTE
```

**Task shape:** replace all three `layout.DISPLAY_ROUTE` literals in `_handle_quick_toggle` with `self._referring_tab()`. No new route, no new validator — confirmed safe because `_referring_tab()` already whitelists against `layout.NAV_TABS` (Home is a member).

### A.3 — Nav state reminder (D-03)

The two nav renderers are `sidebar_nav()` (`layout.py:906-967`) and `_mobile_nav_html()` (`layout.py:1057-1126`); both are driven by `_nav_groups(active)` (`layout.py:826-858`), which itself calls `_nav_links()`. Neither renderer currently reads `ctx["device_config"]` at all — they take `active`/`health_alert` only. D-03's reminder line needs a **third** parameter threaded to both renderers (mirroring how `health_alert` was added later, `layout.py:916-919`'s own docstring precedent for a keyword-with-default addition that doesn't break the ~40 existing call sites). `status_dot()` (`layout.py:1435-1457`) is the exact primitive for the two dots ("Screen on"/"Quiet hours off"); the reminder wraps the whole line in `<a href="/">` per D-03.

Where does `layout.py` get `device_config` from, given a page module cannot import another page module? `app.py`'s `page_context()` (`app.py:1240` onward) already loads `device_cfg = device_config.load_device_config(state_dir)` once (`app.py:1290`) and stores it as `ctx["device_config"]` (`app.py:1305`) — but `layout.py`'s nav renderers are called from `_page_shell_for()`/`page_shell()`, not given `ctx` directly today. **Pitfall:** `page_shell()`'s signature (`layout.py:1202-1204`) takes `title, active, body, ui_theme, flash, banner, health_alert, lang` — no `device_config`. Either `page_shell()` gains a new parameter (screen-state summary strings, pre-computed by the caller) or the reminder text/dots are computed by `app.py`'s `_page_shell_for()`/`_render_tab()` and passed through as two new strings. Given `layout.py` already imports `server.device_config` is NOT confirmed — check before assuming; the safer shape is computing the reminder's text/state in `app.py` (which already has `device_cfg`) and passing a pre-built HTML fragment into `page_shell()`, mirroring how `flash`/`banner` are already pre-built fragments passed in.

### A.4 — Home rebuild target shape (D-04)

The phase-19 three-tile shape to restore is preserved verbatim in git history:

```python
# git show 614d41e~1:companion/pages/home_page.py, lines 166-218 (_status_tiles_html, phase 19 shape)
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

The CURRENT (phase 20) shape to delete is `home_page._status_card_html()` (`home_page.py:239-317`, the single status card headlined by the next-update text, built on `layout.status_row()` — three rows, not three tiles). D-04 explicitly re-adopts the tile shape but **keeps** phase 20's wording constants (`FRAME_STATE_TEXT`/`BATTERY_STATE_TEXT`/`DATA_STATE_TEXT`, already at `home_page.py:99-113`) and phase-20's bugfix for the duplicated verdict (already fixed — `_status_card_html()` builds `frame_verdict`/`frame_detail` from two independently-sourced, non-duplicating strings, `home_page.py:276-277` — this fix must survive the tile-shape rebuild, i.e. do NOT resurrect the old `_status_tiles_html()` verbatim, which had the duplicated-verdict bug; use its STRUCTURE (three `stat_tile()` calls) with the CURRENT (phase 20) content-derivation logic).

The current `render()` (`home_page.py:414-429`) is two rows: `.home-hero` (picture + status card) then recent flights. D-04 wants: strip (new) → three-tile grid (restored shape) → two-column row of (picture, recent flights) — i.e. the picture and the status/tiles change places relative to phase 20: today the picture sits BESIDE the status card; D-04 wants the picture BESIDE recent flights, with the tiles as their own full-width row above both. This is a real layout reorder, not just a swap of `status_card` for `stat_tile`s.

The "next update" text (now living in the strip, not the tiles) is `home_page.NEXT_UPDATE_TEMPLATE`/`EXPECTED_SINCE_TEMPLATE` (`home_page.py:96-97`), computed in `_status_card_html()` at lines 254-274 via `wake.next_wake_at_iso()` + `layout.local_clock_text()` + `layout.age_seconds()` for the past-time branch. This exact computation moves to the strip helper (shared by Home and Display).

### A.5 — "Pretty," accent surface (D-05)

`stat-tile--accent` already exists (`style.css:3033`, and referenced in the skill's accent-reservation list: "a neutral stat tile's icon tint and top accent" — check whether `--accent` is currently reserved for a NEUTRAL tile only, since D-05 wants it for the CONTROL strip specifically; the skill's own accent-reservation contract lives in `style.css`'s header comment and must be extended there first if the strip is a new accent consumer, per the skill's own documented process).

## Area B: One "Frame colours" view (D-06..D-12, CFG-20)

### B.1 — Every chip-grid call site today

`_theme_chip_grid_html(field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="", radio_form_id=None)` (`config_page.py:966-1070`) is already the ONE shared builder — good news for D-06, since B is "make one thing render four times" become "let one rendering happen, driven by a selector," not "write four builders into one."

Current call sites:
1. `theme_fieldset()` — departures grid, `field_name="theme"` (`config_page.py:1293-1294`).
2. `theme_fieldset()` — arrivals grid, `field_name="theme_arriving"`, behind `theme_arriving_enabled` checkbox + CSS `:has()` reveal (`config_page.py:1313-1315`).
3. `calendar_group()` — `field_name="calendar_theme_id"`, `extra_class="theme-chip-grid--compact"` (`config_page.py:2252-2261`).
4. `_rule_add_form_html()` — `field_name="rule_theme_id"`, `extra_class="theme-chip-grid--compact"` (`config_page.py:2646-2649`).

Each already carries a `data-preview-src="/theme-preview/{id}.png?live=1"` attribute on its wrapping `<label>` (`config_page.py:1041`), which `theme-preview.js` reads today — this is D-12's mechanism, already half-built.

### B.2 — `theme_fieldset()`'s current structure to unwind

`theme_fieldset()` (`config_page.py:1138-1356`) renders the LIVE preview (`_theme_live_preview_html()`, `:1073-1135`) directly above the departures grid, then the arrivals-override checkbox + second grid, ALL inside one `.theme-status` card. D-06/D-07 want this card retired as the "Theme" group entirely — its preview and its "departures" grid become row 1 of the new Frame colours card, and its "arrivals" apparatus (checkbox + `THEME_ARRIVING_TOGGLE_ID`/`THEME_ARRIVING_CHECKBOX_LABEL`/the CSS `:has()` reveal at `style.css:2178-2184`) is retired outright, replaced by the "Same as departures" chip (D-09).

### B.3 — CRITICAL pitfall: `theme_arriving`'s clear-signal moves from a checkbox to an empty radio value, and TWO code sites must change together

**What goes wrong if only one site is fixed:** `handle_post()`'s validation gate (`config_page.py:3918-3923`) runs BEFORE the resolution block (`:3941-3960`):

```python
# config_page.py:3918-3923 (validation — runs first)
if (
    submitted_theme_arriving is not None
    and submitted_theme_arriving not in device_config.THEME_IDS
):
    _note_error(errors, "theme_arriving", ERROR_INVALID_CHOICE)
    return FLASH_SAVE_FAILED

# config_page.py:3941-3960 (resolution — runs second, keyed on the CHECKBOX)
if screens.GROUP_THEME not in in_scope:
    theme_arriving = None
elif submitted_theme_arriving_enabled is None:          # <- checkbox absent
    theme_arriving = device_config.CLEAR_THEME_ARRIVING
elif submitted_theme_arriving_enabled == ARRIVING_CHECKBOX_VALUE:  # <- checkbox checked
    theme_arriving = submitted_theme_arriving
else:
    _note_error(errors, "theme_arriving_enabled", ERROR_UNEXPECTED_SWITCH_VALUE)
    return FLASH_SAVE_FAILED
```

D-09 deletes the checkbox (`theme_arriving_enabled`) entirely and replaces it with a "Same as departures" chip that submits `theme_arriving=""`. If the validation gate at 3918-3923 is left unchanged, a submitted `theme_arriving=""` is rejected outright — `"" not in device_config.THEME_IDS"` is true, `_note_error` fires, the WHOLE settings save is rejected (`return FLASH_SAVE_FAILED`) — the user can never save "Same as departures" for arrivals. The resolution block at 3941-3960 also needs a genuine rewrite since `submitted_theme_arriving_enabled` no longer exists as a form field: the new logic must derive `CLEAR_THEME_ARRIVING` from `submitted_theme_arriving == ""` and pass the value through otherwise, e.g.:

```python
if screens.GROUP_THEME not in in_scope:
    theme_arriving = None
elif submitted_theme_arriving is None:
    theme_arriving = None            # field absent entirely (hostile/legacy request) -> carry forward
elif submitted_theme_arriving == "":
    theme_arriving = device_config.CLEAR_THEME_ARRIVING
else:
    theme_arriving = submitted_theme_arriving   # already membership-checked, once "" is carved out above
```

...and the validation gate at 3918-3923 must exempt the empty string from the membership check (`submitted_theme_arriving not in ("",) + device_config.THEME_IDS` or equivalent). `server/device_config.py`'s `normalise_theme_arriving()` (`device_config.py:503-523`) and `save_device_config()`'s own `CLEAR_THEME_ARRIVING` sentinel contract (`device_config.py:95-111`, `:890-895`) do NOT need to change — they already do exactly what D-09 promises ("`theme_arriving=""` → `None`"); the gap is entirely in `config_page.py`'s `handle_post()`, which is the one place still assuming a checkbox exists.

D-09's parallel claim for `calendar_theme_id` is lower-risk: that field has **never** had a checkbox (`normalise_calendar_theme_id()`'s own docstring, `device_config.py:526-547`, explicitly says "no clear-sentinel of CLEAR_THEME_ARRIVING's kind for this key" because the old `<select>` was always `required`). Today `calendar_theme_id`'s validation (`config_page.py:3912-3917`) already rejects any non-member string including `""` — this ALSO needs the same empty-string exemption once the "Same as departures" chip becomes calendar's own clear mechanism, but there is no second (checkbox-reading) resolution block to rewrite for this field — `submitted_calendar_theme_id if submitted_calendar_theme_id is not None else current[...]` (implied elsewhere in the save call) already passes `""` straight through if the validation gate is fixed to allow it, and `normalise_calendar_theme_id("")` already returns `None` per its own contract.

### B.4 — Rules row: keep the existing form/list, relocate the trigger

`_rules_section_html(ctx)` (`config_page.py:2805-2869`) already builds: heading, caption, `_rule_add_form_html()` (`:2608-2685`, its own compact chip grid for `rule_theme_id`), suggestion chips, the rule list or empty state, and the "How rules combine" `<details>`. D-10 says this stays almost exactly as-is; only the OUTER "Flight colours" card heading/caption is retired (the row selection in the Frame colours list becomes the only way to reach it) — `RULES_SECTION_HEADING` ("Flight colours") and its own `<section class="page-section">` wrapper (`:2864`/`:2868`) either get folded into the Frame colours card's "Per-flight rules" row body, or (simpler) stay a separate `<section>` that is shown/hidden by the radiogroup selection alongside the chip-grid-or-not branching. Given D-10's own text ("under the list... instead of a chip grid"), the rules content needs to render in the SAME DOM slot the chip grid would otherwise occupy — i.e. `_rules_section_html()`'s return value needs to be selectable as one of four bodies under the Frame colours card, not rendered as an independent sibling card any more.

### B.5 — `theme-preview.js`'s single-grid assumption breaks the moment there are multiple `.theme-chip-grid` elements on the page

```javascript
// companion/static/theme-preview.js:41-42 (current)
var preview = document.querySelector(".theme-live-preview img");
var grid = document.querySelector(".theme-chip-grid");
```

`document.querySelector()` returns the FIRST match only. Today this is safe because Display only ever has ONE `.theme-live-preview` (inside `theme_fieldset()`) and the script's grid listener is scoped to the departures grid specifically (the arrivals grid's chip clicks are not currently wired to swap the live preview at all — confirmed by reading the whole file, 81 lines, no second `querySelector`). Once B ships:
- The no-JS floor renders (per D-08) FOUR stacked chip grids, each carrying `class="theme-chip-grid"` (plus the rules row's own compact grid, a FIFTH `.theme-chip-grid` element if it is not somehow excluded) — `document.querySelector(".theme-chip-grid")` would bind its one "change" listener to whichever grid is FIRST in DOM order, silently ignoring clicks in the other three/four.
- The JS-enhanced mode needs the script to know WHICH of the four `colour_usage` rows is currently selected, swap the visible chip grid's target (`theme_id`/`theme_arriving`/`calendar_theme_id`), AND swap the preview `src` to that usage's OWN theme (not always the departures grid's).

This is a genuine rewrite of `theme-preview.js`'s selector/event-delegation strategy, not an additive change — the script needs either: (a) to scope its listeners inside a single Frame-colours-card container element and read a `data-usage` attribute the server renders on each radiogroup row, or (b) `querySelectorAll` + per-usage bookkeeping. D-08's own text ("it reads `data-usage`/`data-preview-src` attributes the server rendered... toggles which hidden input the visible chips write to") already anticipates a real rewrite, not a patch — flag this explicitly in the plan so it is not underscoped as "extend theme-preview.js" when it is closer to "replace theme-preview.js's core logic, keep the file/route/contract."

### B.6 — Existing pinned CSS-block-count check

`style.css:2178-2198` and `:5356-5368`'s own comments state: `companion/test_config_page.py` "pins the whole file to exactly two feature-query blocks" (`@supports selector(:has(*))`) — one for the live-selection-state chip/runway-card treatment, one for the Calendar-card fusion. If D-13 retires the Calendar-card fusion CSS (see Area C below) and/or D-08's four-grid collapse needs its own `:has()` block, this pinned count changes — find and retarget that check explicitly (grep `test_config_page.py` for `feature-query` or `:has(` — not read in full during this research pass, flagged as a Wave-0 task).

## Area C: Calendar in one tile (D-13..D-14, CFG-21)

### C.1 — Today's three-piece structure

1. **`calendar_group()`** (`config_page.py:2143-2292`) — heading, caption, `layout.status_row("", verdict, detail, state)` status line (D-14b already shipped this shape), the compact `calendar_theme_id` chip grid (must be REMOVED per D-06), the "How it works" `<details>`/simple-mode-collapsed sentence. Wrapped in `<div class="page-section">`.
2. **`calendar_connect_section(configured, errors=None)`** (`config_page.py:2295-2369`) — its OWN `<form method="post" action="/settings/calendar/connect">`, the write-only URL field (never pre-filled — T-16-SECRET contract, `:2311-2320`), wrapped in `<details><summary>Replace the feed URL</summary>` when `configured` is true (this is ALREADY D-14's exact "Replace the feed URL" `<details>` — just not merged into the same card as the status). Wrapped in its OWN `<div class="page-section">`.
3. **`calendar_disconnect_section(configured, drift)`** (`config_page.py:2372-2418`) — its OWN `<form>`, a bare `<button type="submit">` with `data-confirm`/`data-confirm-value` (no size/colour modifier class today — plain quiet-button geometry). No wrapping `<div>` — it IS the `<form class="calendar-disconnect-form">` element itself.

`render()` (`config_page.py:3327-3332`) emits these as three SEPARATE, sequential pieces on the Display scope: `display_calendar_card_html` (the nested-wrapped `calendar_group()`), then `calendar_connect_html`, then `calendar_disconnect_html` — see the full assembly at `:3334-3399`.

### C.2 — The CSS fusion this phase must retire or repurpose

```css
/* style.css:2193-2197 */
.page-section:has(+ .calendar-disconnect-form) {
  border-bottom-left-radius: 0;
  border-bottom-right-radius: 0;
  margin-bottom: 0;
}

/* style.css:5369-5381 */
.calendar-disconnect-form {
  margin: 0 0 var(--space-lg);
  padding: var(--space-sm) var(--space-md);
  background: var(--color-dominant);
  border: 1px solid var(--color-border);
  border-top: none;
  border-top-left-radius: 0;
  border-top-right-radius: 0;
  border-bottom-left-radius: var(--radius-control);
  border-bottom-right-radius: var(--radius-control);
  display: flex;
  justify-content: flex-end;
}
```

This is the CURRENT "visual fusion" mechanism — `:has(+ .calendar-disconnect-form)` squares off `calendar_connect_section()`'s bottom corners specifically because `calendar_disconnect_section()`'s own `<form>` immediately follows it in the DOM, faking one continuous card out of two/three real ones. D-13/D-14 want them to be ONE ACTUAL card (one `<div>`), so this whole mechanism is now unnecessary complexity to remove, not a foundation to build on. Since `test_config_page.py` pins "exactly two feature-query blocks" (see B.6 above), removing this block changes that count — coordinate with whatever B does to the OTHER pinned block.

### C.3 — D-14's small grey secondary button has no existing CSS class to reuse

Grepped the whole stylesheet (5600 lines): **there is no `.btn`, `.btn--secondary`, or `.btn--small` class family anywhere in this codebase.** Button geometry is controlled entirely by bare-element selectors (`button` = quiet/near-invisible-at-rest, `button[type="submit"]` = accent-filled primary) plus a handful of one-off named classes (`.copy-btn`, `.dirty-bar__cancel`, `.rule-suggestion-chip`) — never a BEM-style `btn`/`btn--modifier` pair. D-14's literal text ("`btn btn--secondary btn--small`") describes an aspirational shape the PRD/CONTEXT authors wrote, not existing markup. **This is a genuine new-CSS need**, explicitly inside Claude's Discretion ("exact CSS class names... within the tokens and idioms"), but the planner must not assume `btn--secondary`/`btn--small` already exist and just need a class attribute added — a real new selector (or a new modifier on the existing bare-`button` rule, scoped by a new class) must be designed and reviewed against the design-system skill's touch-target register (`control-density.md`) before landing. Today's Disconnect button (`config_page.py:2406-2418`) renders with ZERO extra classes; it inherits the base `button` quiet-wash treatment at whatever size the responsive rule currently gives (30px ≥960px / 36px below). D-14 wants it visually smaller/quieter/grey and right-aligned on the SAME line as the "Replace the feed URL" link — this is new layout (a flex row containing both a `<details><summary>` and a `<form><button>`), not an existing one.

### C.4 — Masking: "masked feed URL (host + '…')" is a NEW capability, not a rewording

The write-only contract today (`calendar_connect_section()`'s own docstring, `config_page.py:2311-2320`) is explicit: the URL field NEVER renders a value, in EITHER state — "nothing derived from the stored URL" (T-16-SECRET/T-17-SECRET). Phase 20's own research flagged the identical ambiguity for the Notifications topic URL and resolved it as "write-only, not masked" (`20-RESEARCH.md` Assumption A5) because no masking scheme exists anywhere in this codebase. D-14 (this phase) explicitly asks for something DIFFERENT and NEW: a masked URL showing "host + '…'" — this requires the server to actually READ BACK the stored URL's host component (parse it, extract the scheme+host, discard the path/query/token) and render that fragment, which is a capability `calendar_group()`/`calendar_connect_section()` do NOT have today (the whole point of write-only was "never derive anything from the stored URL for display"). **This is a deliberate scope change from the write-only convention, locked by D-14 itself** — flag it as a real new piece of server logic (parse the stored `calendar_url`, extract `urlsplit(url).netloc` or equivalent, degrade to a generic "Connected" string on any parse failure) needing its own validation that the masked fragment can never leak path/query/token content (a naive `url[:20] + "…"` would NOT be safe — the mask must be host-only, computed from a real URL parse, never a byte-offset truncation of the raw secret string).

## Area D: Compact Flights table (D-15..D-16, CFG-22)

### D.1 — Current 6-column structure

`_HEADERS = ("Timestamp", "Callsign", "Type", "Route", "State", "Corroboration")` (`history_page.py:141-143`). Built by `_history_table_html(formatted_rows, now)` (`:772-825` roughly, exact body around `807`+). Column builders:
- Timestamp: `_clock_cell_html(raw_ts, now)` (`:750-772`) — clock-only, NO relative-age suffix (deliberately removed by A-36/D-19 in an earlier phase specifically because the suffix made the table too wide — see its own comment, "A-36/D-19: mirrors... with no relative-age suffix at all"). D-15's "12 min ago" second line REINTRODUCES exactly what an earlier phase removed for width — do not treat this as free; it is a deliberate width trade the earlier phase already tried and reverted once.
- Callsign: `_callsign_hex_cell(callsign, hex_value)` (`:644-687` roughly) — merges Callsign+Hex on one line via `_merged_cell()`, PLUS a copy button after each of callsign and hex (D-23 from an earlier phase).
- Type: `_type_airline_cell(row)` (`:703-724` roughly) — merges aircraft type + airline via `_merged_cell()`, plus an "unresolved airline" link when applicable.
- Route/State: plain escaped cells.
- Corroboration: `layout.status_dot()`, dot only + label + title.

Row height/data available per row (`format_event_row()`'s output dict, referenced throughout): `raw_ts` (full ISO), `callsign`, `hex`, `aircraft_type_label`, `airline_label`, `route_label`, `confirmed_state`, `corroboration_status`/`_label`/`_title`, `tracked_runway` (currently shown ONLY as the `<tr title="...">` attribute, dropped as a visible column by an earlier phase's A-36/D-19).

### D.2 — The real available width (arithmetic)

- `.dashboard-shell`'s sidebar column is `240px` with a `32px` (`--space-xl`) gap (`style.css:4112-4117`).
- `.dashboard-main` adds `48px`/`64px` (`--space-2xl`/`--space-3xl`) padding — the relevant axis is horizontal, `64px` EACH side (`style.css:4171-4177`).
- At a 1280px viewport: `1280 - 240 (sidebar) - 32 (gap) - 64 - 64 (main padding) = 880px`.
- A pre-existing code comment (`history_page.py`, near `_HEADERS`) already states this exact number for the PREVIOUS 9→7-column merge: "one runway is tracked at a time... 90px of a 1,305px table that had to fit an 880px column." **880px, not 1280px, is D-15's real budget.**
- French label lengths matter for exactly this reason: `_HEADERS` values run through `i18n.t()` at render time (`_history_table_html`'s `header_cells` build, `"<th>%s</th>" % escape_html(i18n.t(h))`); "Corroboration" → FR is likely longer, "When"/"Quand" is a wash, but "Flight"/"Vol" and "Route"/"Itinéraire" (if that's the FR word chosen) can differ meaningfully — measure both languages against the SAME 880px box, not against 1280px.

### D.3 — Why the detail row needs new JS, not `<details>`

The mobile card's existing `<details class="history-card__details">` (`history_page.py:952-963`) is the exact CONTENT shape D-15 wants moved off the desktop table (hex + copy button, aircraft type + airline, corroboration dot, runway, full ISO timestamp + copy button) — but `<details>` cannot wrap a `<tr>` as a child of `<tbody>` (HTML's content model forbids it; a browser would either move it out of the table entirely or drop it). D-15's own text already states this ("a `<details>`-free implementation is not possible inside a table") — confirmed correct. The mechanism must be: each primary `<tr>` gets a "More"/"Plus" `<button>` (or similarly inert-without-JS element) with a `data-row-toggle` attribute; a second `<tr class="…detail-row">` immediately follows in markup, containing the same dt/dd-shaped content the mobile card's `<details>` already has; a new/extended ES5 script toggles a class that shows/hides the detail row, with the no-JS floor being **detail rows visible by default**, hidden by a class the script adds at load (matching the CONTEXT's own stated pattern) — i.e. the JS makes the page MORE compact, never less functional, when absent.

### D.4 — Six-touch-point contract, using `theme-preview.js` as the worked recent example

If the row-toggle becomes a NEW static script (Claude's Discretion allows either a new file or an extension of an existing one — `list-filter.js`/`copy-button.js` are both plausible hosts since they already run on this exact page), it must follow the exact six-touch-point pattern `theme-preview.js` already demonstrates:
1. Route constant: `companion/app.py:187` (`THEME_PREVIEW_SCRIPT_ROUTE = "/static/theme-preview.js"`).
2. Serve delegate: `companion/app.py:1672` (`_serve_theme_preview_script`).
3. `do_GET()` dispatch line: `companion/app.py:2479-2480`.
4. Matching `layout.py` constant: `companion/layout.py:167` (`THEME_PREVIEW_SCRIPT_SRC`, MUST equal the route string exactly — the two are duplicated-not-imported, per the codebase's own documented convention to avoid an app.py↔layout.py import cycle).
5. `page_shell()`'s script-tag list: `companion/layout.py:1392`.
6. A cross-file "route equals src" test in `companion/test_companion_app.py` (grep `THEME_PREVIEW_SCRIPT_ROUTE.*THEME_PREVIEW_SCRIPT_SRC` or similar for the exact existing assertion to mirror).

### D.5 — Mobile cards stay untouched (D-16)

`_history_cards_html()` (`history_page.py:867-991`) already carries the full detail set (D-16 confirms "unchanged"); the filter bar (`_filter_bar_html()`) and the View-panel lightbox (`_lightbox_html()` at the bottom of `render()`) are also unaffected — only `_history_table_html()` and `_HEADERS` change.

## Area E: Simple mode and the Health pause button removed (D-17..D-18, CFG-23)

### E.1 — Complete `simple_mode`/`MODE_*`/`ui-mode` inventory (grouped by file, with line numbers)

Full inventory from `grep -rn "simple_mode\|MODE_CHOICES\|ui-mode\|ui_mode\|UI_MODE\|_MODE_CTX\|DEFAULT_MODE\|Simple mode\|HOW_IT_WORKS_SIMPLE\|COMBINE_SIMPLE" companion server`:

**`companion/prefs.py`** — the whole mode mechanism's home:
- `MODE_CHOICES = ("simple", "full")` (line 34), `DEFAULT_MODE = "full"` (35), `_MODE_CTX = contextvars.ContextVar(...)` (38), `set_request_prefs(..., mode=...)`'s mode-setting branch (49), `simple_mode()` function (58-61).
- **Do NOT delete** the `mode=` parameter of `set_request_prefs()` without checking every call site first — `app.py:1276` calls it with both `lang=`/`mode=` in one call; deleting the parameter (per D-17's own instruction) means that call site loses its `mode=` argument too.

**`companion/auth.py:64`** — `UI_MODE_COOKIE_NAME = "sp_ui_mode"`.

**`companion/app.py`**:
- `MODE_ROUTE = "/ui-mode"` (220).
- Cookie read: `_mode_from_request()`-equivalent method, `app.py:1156-1165` (`cookie_value = cookies.get(auth.UI_MODE_COOKIE_NAME)`, `if cookie_value in prefs.MODE_CHOICES: return cookie_value`, `return prefs.DEFAULT_MODE`).
- `page_context()`: `"simple_mode": prefs.simple_mode()` (1304), and the `prefs.set_request_prefs(lang=..., mode=...)` call (1275-1276) needs its `mode=` argument dropped.
- `_handle_mode_post()` (2857-2869) — the whole handler, byte-for-byte sibling of `_handle_theme_post()`/`_handle_lang_post()`.
- `do_POST()` dispatch: `if path == MODE_ROUTE: ... return self._handle_mode_post()` (2915-2918).

**`companion/layout.py`**:
- `_mode_form_html(resolved_mode)` (1010-1030) — the whole nav-footer "Simple/Full" switch builder.
- `_nav_groups(active)`'s `simple = prefs.simple_mode()` read and the `if simple and group_label == ADVANCED_GROUP_LABEL: continue` branch (841-856) — this is the mechanism that hides the Advanced nav group; D-17 says the gate goes, meaning the Advanced group (Health, Device) is ALWAYS shown now.
- `page_shell()`'s `resolved_mode = "simple" if prefs.simple_mode() else "full"` (1230) and whatever downstream use it feeds (passing `mode_form_html` to `_mobile_nav_html()`/sidebar footer — check both renderers' footer-assembly call sites for the `mode_form_html` parameter and its removal).
- `_mobile_nav_html()`'s `mode_form_html=""` parameter and its inclusion in `footer_html` (1117-1119) — needs the parameter removed, not just defaulted, per D-17's full-removal instruction.

**`companion/pages/home_page.py:300`** — `if not ctx.get("simple_mode"):` gating the "See details on Health" link in `_status_card_html()`. **This function itself is being replaced by the D-04 tile rebuild (Area A)** — coordinate: whichever plan does the Home rebuild should simply never re-add this gate, rather than adding-then-removing it in two different plans.

**`companion/pages/config_page.py`**:
- `CALENDAR_HOW_IT_WORKS_SIMPLE = "It only colours a flight already on screen."` (670) and its use in `calendar_group()` (2263-2266, the `if simple_mode:` branch).
- `RULES_HOW_RULES_COMBINE_SIMPLE = "The most specific match wins."` (575) and its use in `_rules_section_html()` (2844-2847).
- `calendar_group()`'s own `simple_mode=False` parameter (2146) and its caller in `render()`'s builders dict (`simple_mode=ctx.get("simple_mode")`, 3200).
- `_rules_section_html(ctx)`'s `ctx.get("simple_mode")` reads (2828, 2844) — since this function takes `ctx` directly (not a parameter), only the two read sites need deleting, not a signature change.

**`companion/pages/airlines_page.py`**:
- `_edit_toggle_html(ctx, edit_mode)`'s `if ctx.get("simple_mode"): return ""` gate (1849-1850) — **D-20 explicitly says the button is "always visible now that simple mode is gone"** — delete this whole early-return, not just its condition.

**Tests** (exact counts, confirmed by direct grep):
- `companion/test_companion_app.py` — 88 occurrences of the searched terms. The bulk is one contiguous block, `test_companion_app.py:7100-7345`, containing 12 check-function definitions (two of which — `_make_simple_mode_nav_hidden_check`/`_make_full_mode_nav_shown_check` — are FACTORIES invoked in a loop over routes, which is why the CONTEXT's own estimate of "about 16 checks" is accurate even though only 12 `def`s exist). A SEPARATE, smaller pair (`_ui_mode_post_round_trip`/`_ui_mode_post_without_session_redirects_to_login`, lines 4223-4270) tests the `/ui-mode` route mechanics directly and must also be deleted. `EXPECTED_CHECK_COUNT = 267` (line 433) will drop by the exact number of deleted `check(...)` call sites — count them precisely at execution time, do not estimate.
- `companion/test_config_page.py` — 3 occurrences, all one check: `_rules_simple_mode_collapses_disclosure_to_one_sentence` (4322-4343). `EXPECTED_CHECK_COUNT = 212` (line 464) drops by 1.
- `companion/test_status_pages.py` — 7 occurrences: `_simple_mode_omits_advanced_group_and_health_dot` (6485-6517) plus the `/ui-mode` nav-footer-switch-order assertions inside a DIFFERENT check that ALSO asserts `/ui-lang`/`/ui-theme` order (lines 6453-6464) — this second one needs care: it currently asserts "exactly 2 `/ui-mode` forms" and a THREE-element `first_three` order list including `/ui-mode`; once the mode switch is deleted, this becomes a two-element list and a "0 forms" assertion, not a deleted check. `EXPECTED_CHECK_COUNT = 213` (line 502) — confirm whether this is a retarget (no count change) or a deletion (count drops by 1) once the exact check boundaries are read.
- `companion/test_view_pages.py` — 28 occurrences across several distinct checks: the two Airlines `_edit_toggle_html` simple-mode checks (`_airlines_simple_mode_render_has_no_toggle_or_caption`, `_airlines_simple_mode_and_edit_mode_still_renders_lightbox_forms`, lines 2992-3025) and the Home status-card health-link gating check (`_home_status_card_health_link_gated_by_simple_mode`, 3846-3862) are the check FUNCTIONS to delete; several OTHER `"simple_mode": False` dict literals (lines 3503, 3658, 3729, 3782) are just test-fixture ctx keys for UNRELATED checks and can either be deleted (the key no longer exists in `ctx`) or left as harmless extra dict keys — confirm `render(ctx)` call sites still work with an extra unused key before deciding (Python dicts tolerate extra keys fine; deleting them is cosmetic cleanup, not required for correctness). `EXPECTED_CHECK_COUNT = 107` (line 352) drops by exactly the number of deleted check FUNCTIONS (3, from the two named above plus the health-link one), not by 28.
- `companion/test_i18n.py` — 10 occurrences: two check functions test `prefs.simple_mode()` directly (`_check_prefs_unknown_mode_leaves_simple_mode_false`, `_check_prefs_simple_mode_true_for_simple`, lines 628-654). `EXPECTED_CHECK_COUNT = 24` (line 44) drops by 2. **Additionally**, `test_i18n.py`'s own `_check_d08_no_dead_translations()` (777-797) will start failing the moment `CALENDAR_HOW_IT_WORKS_SIMPLE`/`RULES_HOW_RULES_COMBINE_SIMPLE` are deleted from `config_page.py` UNLESS their matching FR catalogue entries (in `companion/i18n_fr/calendar_group.py` and `companion/i18n_fr/rules.py` — both files have a comment block literally headed "`--- Simple mode's collapsed disclosure sentence (D-30) ---`") are deleted in the SAME commit. This is the "may fail on unused keys" risk the task brief warned about, and it is real and specific: two named catalogue entries, two named files.
- `companion/i18n_fr/nav.py:34` — `"Simple mode": "Mode simple"` — this catalogue entry becomes dead the moment `_mode_form_html()`'s `i18n.t("Simple mode")` call site is deleted; same dead-translation risk, same fix (delete the entry).

**Stale cookie handling:** D-17's own text — "A stale `sp_ui_mode` cookie in a browser is simply ignored" — requires NO code (once `_handle_mode_post`/the cookie-reading method/`UI_MODE_COOKIE_NAME` are all deleted, nothing ever reads that cookie name again; a browser that still sends it is simply never asked about it). No migration, no explicit-ignore code path needed.

### E.2 — Health pause button removal (D-18)

`REFRESH_PAUSE_TEXT = "Pause updates"` / `REFRESH_RESUME_TEXT = "Resume updates"` (`health_page.py:343-344`). The button itself (`toggle_html`, `health_page.py:2909-2925`) is one of four fragments concatenated into `freshness_html` at `health_page.py:2947-2949` — the other three (`FRESHNESS_PREFIX_TEXT`, `clock_html`, `pill_html`) are UNRELATED and must stay (the countdown/"Updating…" pill are explicitly out of scope, point 11/CFG accepted). Deleting `toggle_html`'s construction and its slot in the `%`-format tuple is a clean, isolated edit.

`companion/static/freshness.js`'s pause mechanism to delete: the module-level `var paused = false;` (line 163), `setToggleVisual()` (320-325), `wireToggle()` (327-341) and its two call sites (`applySwap()`'s `wireToggle();` at 350, and the bottom-of-file `wireToggle();` at 476), the `if (paused) { return; }` guard inside `tick()` (428-430), and the `if (paused) { return; }` guard inside the `visibilitychange` listener (458-462, including its own explanatory comment about surviving a visibility round-trip). **Do NOT touch** `stopLoop()`/`startLoop()`/`intervalHandle`/the `document.hidden` branches — those are the tab-visibility mechanism (unrelated to the user-facing pause button) and must survive untouched; `tick()`'s `if (document.hidden) { stopLoop(); return; }` guard stays.

Tests: `data-pause-text`/`data-resume-text` attribute assertions in `test_status_pages.py`/`test_view_pages.py`'s script-contract checks — grep both files for `data-pause-text`/`REFRESH_PAUSE_TEXT`/`data-refresh-toggle` to find the exact pinned checks (not fully enumerated in this research pass — Wave-0 task).

## Area F: Artwork upload restored in the resolve flow (D-19..D-20, CFG-24)

### F.1 — The two guards to relax

```python
# companion/pages/airlines_page.py:1727 (STAYS gated — D-20 keeps delete behind edit_mode)
delete_form = _manual_delete_form_html(_manual_delete_action(prefix)) if edit_mode else ""

# companion/pages/airlines_page.py:1733 (DROP the guard — D-19)
upload_zone = _resolve_upload_form_html(upload_action, "") if edit_mode else ""
# becomes:
upload_zone = _resolve_upload_form_html(upload_action, "")
```

This is inside `_resolve_section_html(ctx, edit_mode=False)` (`:1608-1743`), the no-JS fallback panel's Step-B branch (name saved, no artwork yet).

### F.2 — The lightbox's matching guard

```python
# companion/pages/airlines_page.py:1160-1230 (_lightbox_html)
resolve_upload_html = _resolve_upload_form_html("", "-dialog") if edit_mode else ""  # DROP the guard (D-19)
replace_html = _lightbox_replace_form_html() if edit_mode else ""                    # STAYS gated (D-20)
delete_html = _manual_delete_form_html("") if edit_mode else ""                      # STAYS gated (D-20)
```

D-19's own text ("The lightbox's upload affordance for an airline with no artwork yet follows the same rule") confirms only `resolve_upload_html`'s guard drops; `replace_html`/`delete_html` (both "existing artwork" affordances) stay exactly as D-20 requires. `panel-lookup.js` needs NO change — its own docstring (`_lightbox_html()`'s comment, `:1193-1200`) already states all three lookups are behind their own `if (form)`-style guards and tolerate total absence; making the upload form unconditionally present (rather than unconditionally absent or present depending on `edit_mode`) is well inside its existing tolerance.

### F.3 — `_edit_toggle_html`'s own gate (cross-reference with Area E)

D-20 says "The button is always visible now that simple mode is gone (D-17)" — this is the SAME `if ctx.get("simple_mode"): return ""` early-return already identified in Area E (`airlines_page.py:1849-1850`). This is one delete, serving both D-17 and D-20 — do not schedule it as two separate tasks in two different plans; whichever plan removes `simple_mode` gates should remove this one too, and F's own plan should not also touch it (file-overlap risk, see Cross-Cutting below).

### F.4 — Test inventory (not fully read in this pass — Wave-0 task)

Referenced by the task brief as "phase 19 plan 19-08/19-09 checks" — grep `test_view_pages.py`/`test_companion_app.py` for `edit_mode.*upload` or `_resolve_upload_form_html`/`upload_zone` assertions asserting the upload zone's ABSENCE when `edit_mode` is falsy; these need retargeting to assert PRESENCE unconditionally. Not enumerated exhaustively here; budget a Wave-0 grep pass before writing D-19/D-20's plan.

## Cross-Cutting

### How new English strings are registered

`companion/i18n_fr/` is a package (`__init__.py`, 47 lines) that auto-discovers sibling modules via `pkgutil.iter_modules()`, merges each module's own `CATALOG` dict, and raises `ValueError` on a duplicate key across modules (`i18n_fr/__init__.py:29-44`). Existing per-page modules: `airlines.py`, `calendar_group.py`, `common.py`, `display.py`, `flights.py`, `health.py`, `home.py`, `nav.py`, `notifications.py`, `registry.py`, `rules.py`. A new page-level string goes into whichever module already owns that page (e.g. a new Home strip string → `home.py`; a new Frame-colours string → `display.py`; a new Flights-table string → `flights.py`). No shared registration list to edit — this is the whole point of the package's auto-discovery design (stated explicitly in its own docstring: "no plan ever has to edit a shared registration list, so no two plans in one wave can conflict over one").

### `EXPECTED_CHECK_COUNT` current values (only the LAST assignment in each file is live — confirmed by grep, matching the "only the last assignment is live" convention named in the task brief)

| Harness | Current EXPECTED_CHECK_COUNT | Line |
|---|---|---|
| `companion/test_companion_app.py` | 267 | 433 |
| `companion/test_config_page.py` | 212 | 464 |
| `companion/test_status_pages.py` | 213 | 502 |
| `companion/test_view_pages.py` | 107 | 352 |
| `companion/test_i18n.py` | 24 | 44 |
| `companion/test_contrast_check.py` | 39 | 61 |

Every plan that adds/deletes a `check(...)` call site in one of these files must re-derive and update that file's LAST `EXPECTED_CHECK_COUNT` assignment (append a new one after the existing last, per this codebase's own established convention — do not edit the line in place, add a new one below it with a comment explaining the delta, matching every prior phase's own pattern visible throughout these files' history).

### Headless sweep mechanism (already proven in this session's scratchpad)

`/tmp/.../scratchpad/shots20.js` (Playwright, `chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome' })`) drives the ALREADY-RUNNING companion server at `http://127.0.0.1:8643`, logs in with `test1234`, switches language via the real `form[action="/ui-lang"] button[value="fr"]` control, then for each of `/`, `/display`, `/device`, `/flights`, `/airlines`, `/health` takes a full-page screenshot at both `{width:1280,height:900}` and `{width:390,height:844}` viewports, and asserts: no `document.documentElement.scrollWidth > window.innerWidth` (horizontal overflow), no `script:not([src])`/`[onclick]`/`[onchange]`/`[onsubmit]`/`[oninput]` matches (inline-script/handler CSP violation), no HTTP status ≥ 400. `companion/app.py` has a stdlib `argparse`-based CLI entry (`app.py:3027-3048`) used to start the server against a seeded state directory (`/tmp/.../scratchpad/state-main/` and siblings already contain a seeded `device_config.json`/`history.db`/`manual_resolutions.json`/`poll_state.json`/`theme_previews/`/`gallery/` — reuse this seed rather than re-deriving one). `probe-ovf.js`/`probe-ovf-fr.js` are narrower single-page overflow probes already written for the EN/FR overflow check specifically — a natural starting point for D-15's own "no horizontal scroll at 1280px in both languages" verification. This exact mechanism (adapted for the new/changed pages: Home's strip+tiles layout, Display's Frame-colours card, the Flights table) is what phase 21's own headless sweep should reuse, not reinvent.

### File-overlap matrix (for wave-splitting)

| File | A (strip) | B (Frame colours) | C (Calendar) | D (Flights table) | E (simple mode) | F (upload) |
|---|---|---|---|---|---|---|
| `companion/pages/config_page.py` | Yes — extracts quick-action markup from `display_group()`/`quiet_hours_group()` | Yes — retires `theme_fieldset()`'s arrivals apparatus, rewrites `handle_post()`'s theme_arriving block, moves rules-row trigger | Yes — merges 3 render calls into 1 | — | Yes — deletes 2 simple_mode gates + 1 parameter | — |
| `companion/layout.py` | Yes — nav reminder, possibly `page_shell()` signature, strip helper (if here not `frame_strip.py`) | — | — | — | Yes — deletes `_mode_form_html()`, `_nav_groups()`'s gate, footer parameter | — |
| `companion/app.py` | Yes — `_handle_quick_toggle`'s redirect target | — | — | — | Yes — deletes `MODE_ROUTE`, `_handle_mode_post`, cookie read, `do_POST` dispatch line, `page_context()`'s `mode=` arg | — |
| `companion/pages/home_page.py` | Yes — full rebuild | — | — | — | Yes — the health-link gate this rebuild should simply not resurrect (coordinate, don't double-handle) | — |
| `companion/static/style.css` | Yes — strip layout, accent surface | Yes — Frame colours card layout, `:has()` block count | Yes — retires 2 fusion rules, adds small/grey button styling | Yes — table column widths | Yes — deletes mode-switch-specific rules if any | — |
| `companion/pages/airlines_page.py` | — | — | — | — | Yes — `_edit_toggle_html`'s simple_mode gate | Yes — 2 upload guards |
| `companion/pages/history_page.py` | — | — | — | Yes — full table rebuild | — | — |
| `companion/pages/health_page.py` | — | — | — | — | Yes — pause button removal | — |
| `companion/static/freshness.js` | — | — | — | — | Yes — pause branch removal | — |
| `companion/static/theme-preview.js` | — | Yes — core rewrite | — | — | — | — |
| `companion/prefs.py`/`auth.py` | — | — | — | — | Yes | — |
| `companion/i18n_fr/*` | additive | additive | additive | additive | deletive (2 entries + orphan check) | — |
| Test harnesses | per-area, listed above | per-area | per-area | per-area | per-area (heaviest) | per-area |

**Two-executor conflict risk:** A and E both touch `config_page.py`, `layout.py`, `app.py`, `home_page.py`, and `airlines_page.py` — if A and E run in the same wave with two different executors, both may edit `airlines_page.py`'s `_edit_toggle_html` (A doesn't need to, but a careless split could assign the "always visible" half of D-20 to A's plan by mistake — it belongs to E/F). B and C both touch `config_page.py`'s Display-scope `render()` assembly and the `.theme-status:has(...)`/Calendar-fusion CSS blocks — sequence B before C (or vice versa) rather than parallel, since both rewrite adjacent slices of the same `render()` return-value concatenation. D (history_page.py + a static script) and E (mode/pause removal, spanning config_page/layout/app/home_page/airlines_page/health_page/freshness.js) share almost no files and are the safest pair to run fully in parallel.

## Common Pitfalls

### Pitfall 1 (CRITICAL): D-09's server-side rewrite is bigger than "server semantics unchanged" implies
See Area B.3 above in full. **What goes wrong:** treating D-09 as a pure markup change (add a "Same as departures" chip, done) leaves `handle_post()`'s checkbox-keyed resolution block and its preceding membership-validation gate both broken — a submitted empty-string "Same as departures" selection is REJECTED by the validation gate before the resolution block (which no longer has a checkbox to read anyway) ever runs. **How to avoid:** treat D-09 as touching `config_page.py:3918-3923` AND `:3941-3960` together, in the SAME task, with new test coverage asserting `theme_arriving=""` saves successfully and resolves to `None` on read-back.

### Pitfall 2 (CRITICAL): D-13's "one card" requires retiring two CSS fusion rules, not adding a third
See Area C.2 above. **What goes wrong:** a plan that treats the Calendar card as "just move the connect form's markup inside `calendar_group()`'s return string" while leaving `.calendar-disconnect-form`/`.page-section:has(+ .calendar-disconnect-form)` in the stylesheet ships dead CSS that no longer matches anything (the disconnect form is no longer a page-section's NEXT SIBLING once it's nested inside the same card) — or worse, subtly wrong styling if the disconnect button's `<form>` is left as a real sibling `<form>` element for HTML-forms-can't-nest reasons while everything else merges, silently leaving the OLD fusion rule half-applicable. **How to avoid:** delete both CSS rules explicitly as part of this task, and design the new one-card markup with the disconnect form as a real DOM child of the outer calendar `<div>` (not a `<form id="settings-form">` descendant — HTML forbids nested forms, and the disconnect form still needs its own POST target) — the same "form-as-sibling-with-form= attribute-back-in" idiom `quiet_hours_group()`/`display_group()` already use for their OWN instant-switch forms is the precedent to reuse here for whichever piece needs to stay a separate `<form>`.

### Pitfall 3: `theme-preview.js`'s single-`querySelector` assumption silently breaks with 4-5 chip grids on one page
See Area B.5 above in full. **Warning sign:** a plan task titled "extend theme-preview.js" that describes adding attributes/logic without mentioning `querySelector` → `querySelectorAll` or a scoped-container rewrite — this under-scopes real work.

### Pitfall 4: D-15's "12 min ago" second line reopens a width problem an earlier phase already fixed once
**What goes wrong:** the desktop Timestamp column's relative-age suffix was REMOVED specifically because it made the table too wide for its 880px column (A-36/D-19, an earlier phase). D-15 reintroduces it as a second stacked line rather than an inline suffix — this is NOT the same change being undone (a stacked two-line cell costs vertical space, not horizontal, so it is compatible with the width goal), but a plan that doesn't realize this history could mistakenly reach for the OLD inline-suffix shape (`concise_timestamp_html()`, one line, `"HH:MM (12m ago)"`) instead of the NEW stacked shape (`cell-primary`/`cell-secondary`, two lines) D-15 explicitly specifies. **How to avoid:** use `_merged_cell()`'s existing primary/secondary two-line pattern (already proven at 880px for the Callsign/Type columns), not `concise_timestamp_html()`'s one-line pattern.

### Pitfall 5: Deleting simple-mode's English constants without deleting their FR catalogue entries fails `test_i18n.py`'s dead-translation check
See Area E.1's `test_i18n.py` entry above. **Warning sign:** a diff that deletes `CALENDAR_HOW_IT_WORKS_SIMPLE`/`RULES_HOW_RULES_COMBINE_SIMPLE`/"Simple mode" from their Python source files but doesn't touch `companion/i18n_fr/calendar_group.py`/`rules.py`/`nav.py` in the same commit — `_check_d08_no_dead_translations()` (`test_i18n.py:777-797`) will name exactly these keys as orphaned.

### Pitfall 6: `_edit_toggle_html`'s simple_mode gate is one delete serving two decisions (D-17 and D-20) — do not schedule it twice
See Area F.3. A plan-check pass should confirm exactly one plan owns `airlines_page.py:1849-1850`'s deletion.

## Code Examples

### The `form=` attribute idiom every sibling-of-a-form control in this file already uses (needed if Area C's disconnect form stays a real `<form>` inside the merged calendar card)
```python
# companion/pages/config_page.py — the established precedent (quick task 260901-re6),
# reused by quiet_hours_group()/display_group()'s own instant-switch forms and by
# runway_fieldset()'s/calendar_group()'s chip-grid radios:
'<input type="checkbox" name="quiet_hours_enabled" value="%s"%s form="%s"%s> %s'
# form="settings-form" lets a control OUTSIDE <form id="settings-form"> still submit into it.
```

### The chip-grid builder's existing extension seams (relevant to B's "one chip grid for whichever usage is selected")
```python
# companion/pages/config_page.py:966-968 (signature, already parameterised)
def _theme_chip_grid_html(
        field_name, selected_theme_id, extra_class="", extra_attr="", chip_extra_class="",
        radio_form_id=None):
```
Calling this ONE function with `field_name` swapped between `"theme"`/`"theme_arriving"`/`"calendar_theme_id"`/`"rule_theme_id"` per the selected `colour_usage` row is the whole of D-08's "one chip grid" requirement — no new grid-rendering code needed, only new logic around WHICH call happens and how the "Same as departures" first chip is injected (a new parameter, e.g. `same_as_departures_label=None`, prepending one extra `<label>` before the loop over `device_config.THEME_IDS` when set).

## Runtime State Inventory

Not applicable — this phase is not a rename/refactor/migration. Confirmed: no decision renames an on-disk key, a database column, an env var, or a secrets-file key. `device_config.json`'s `theme_arriving`/`calendar_theme_id` keys keep their exact names and exact `None`-vs-sentinel semantics (D-09's own text); only the FORM FIELD NAMES an HTTP POST carries for `theme_arriving`'s clear-signal change shape (checkbox → empty-string radio value), never the persisted config schema. No migration script needed.

## Environment Availability

Not applicable in the "external tool" sense — this phase's only environment dependency is the already-running companion server + Playwright/Chromium combination already proven working in this session's scratchpad (see Cross-Cutting's Headless sweep mechanism entry above). No new external tool, service, or runtime is introduced.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | stdlib-only, hand-rolled `check(name, fn)` harness convention — no pytest, no unittest runner |
| Config file | none — `scripts/run-all-tests.sh` → `scripts/run_all_tests.py` is the canonical list |
| Quick run command | `PYTHON=/home/user/skypane/server/.venv/bin/python /home/user/skypane/server/.venv/bin/python3 companion/<file>.py` (each file is directly executable and self-reports `N/M checks pass`) |
| Full suite command | `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CFG-19 | Frame strip renders on Home+Display, redirect returns to referring page, nav shows state reminder | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` (quick-toggle redirect), `companion/test_view_pages.py` (Home strip/tiles) | Yes (extend both) |
| CFG-20 | One Frame colours card, radiogroup selection swaps grid+preview, no-JS floor saves every value | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py` | Yes (extend) |
| CFG-21 | Calendar one card, masked URL, small Disconnect button, confirm step intact | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_config_page.py` | Yes (extend) |
| CFG-22 | 5-column table fits 880px real box, detail row toggle works, mobile cards unchanged | in-process + real-HTTP + headless screenshot | `server/.venv/bin/python3 companion/test_view_pages.py`/`test_companion_app.py` (History page ownership — confirm exact file at Wave 0, mirroring phase 20's own "confirm Home's test-file ownership" precedent) | Confirm ownership |
| CFG-23 | No simple_mode/`ui-mode` reference anywhere; no Pause button; freshness loop runs unconditionally | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_companion_app.py` + `companion/test_i18n.py` (dead-translation check) | Yes (delete-heavy) |
| CFG-24 | Upload zone unconditional in step B (both no-JS panel and lightbox); replace/delete still edit-gated | in-process + real-HTTP | `server/.venv/bin/python3 companion/test_view_pages.py` | Yes (retarget) |

### Sampling Rate
- **Per task commit:** the single most relevant harness for the file(s) touched.
- **Per wave merge:** `PYTHON=/home/user/skypane/server/.venv/bin/python bash scripts/run-all-tests.sh` (full suite).
- **Phase gate:** full suite green (excluding the 5 documented pre-existing root-sandbox failures) before `/gsd:verify-work`, plus `ruff check .` clean, plus a headless EN/FR × 1280/390 sweep (adapt `shots20.js`/`probe-ovf.js`/`probe-ovf-fr.js` from the scratchpad) reporting no overflow, no inline script, no 404.

### Wave 0 Gaps
- [ ] Confirm which test file owns History/Flights-page checks before D's plan starts (mirrors phase 20's own unresolved "which file owns Home" question, now resolved for Home but open for Flights — grep `test_view_pages.py`/`test_companion_app.py`/`test_status_pages.py` for `history_page`/`GET /flights` references).
- [ ] Read `test_config_page.py`'s exact two pinned `@supports selector(:has(*))` block-count assertions (referenced by `style.css`'s own comments at lines 2190-2192 and 5359-5362 but not directly read in this pass) — needed before B/C's CSS restructuring lands.
- [ ] Enumerate every `test_status_pages.py` check asserting nav-footer switch ORDER/COUNT (`/ui-lang`, `/ui-theme`, `/ui-mode`) precisely — the 3-element-to-2-element retarget at lines 6453-6464 needs its exact boundaries read before deletion.
- [ ] Enumerate `test_view_pages.py`/`test_companion_app.py`'s exact `edit_mode`-gated-upload-absence checks referenced by "phase 19 plan 19-08/19-09" (Area F.4) — not read in this pass.
- [ ] Enumerate `health_page.py`'s/`freshness.js`'s exact pinned pause-button checks in `test_status_pages.py`/`test_view_pages.py` (Area E.2) — not read in this pass.

## Security Domain

### Applicable ASVS Categories (Level 1, block on high — per `.planning/config.json`)

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No change | Every route this phase touches already exists and is already `require_session()`-gated; deleting `/ui-mode` removes one gated route, adds none |
| V4 Access Control | Yes (removal only) | Deleting `simple_mode` removes a PRESENTATION-only gate that D-30 (phase 20) already documented as "never access control" — no access-control regression is possible from its removal, since `/health`/`/device` were already reachable by URL regardless of the cookie |
| V5 Input Validation | Yes | The `theme_arriving`/`calendar_theme_id` empty-string handling (Pitfall 1) is the one genuinely new input-shape this phase introduces at the HTTP layer — must be validated exactly like every other membership-tested field (reject anything that is neither `""` nor a real `THEME_IDS` member) |
| V14 Configuration | No change | No new cookie, no new config key; `theme_arriving`/`calendar_theme_id`'s on-disk semantics are unchanged (D-09's own claim, verified true at the storage layer in Area B.3) |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A crafted `theme_arriving=""` or `calendar_theme_id=""` POST bypassing the intended UI (Area B.3) | Tampering | Both fields already run through `server/device_config.py`'s `normalise_theme_arriving()`/`normalise_calendar_theme_id()` at the STORAGE layer, which already degrade any non-member string (including `""`) to `None`/no-op safely — the risk is purely at the `config_page.py` HTTP-validation layer rejecting the save outright, not a security hole; still worth an explicit test for "a crafted empty string never crashes or writes garbage," matching this codebase's existing discipline for every other membership-tested field |
| A masked calendar URL fragment leaking more than the host (Area C.4, the new "host + '…'" masking capability) | Information Disclosure | The mask MUST be derived from a real URL parse (`urlsplit(url).netloc` or equivalent), never a byte-offset string truncation — a truncation-based mask on a URL like `https://calendar.google.com/private/basic/abc123secret...` could leak path/token characters depending on host length; validate this explicitly with a test asserting the masked output never contains any character from the URL's path/query/fragment components |
| Nav reminder text (D-03) reflecting `device_config` values with no escaping | Tampering (XSS) | `device_config`'s `quiet_hours_start`/`_end`/`display_enabled` are already validated at write time (`server/device_config.py`'s own gates) and are not raw user-text fields — but the reminder's OWN new render site must still route every interpolated value through `escape_html()` exactly like every other page-module builder in this codebase, with zero exceptions, matching the site-wide discipline this project already enforces everywhere else |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | D-01's strip helper needs `layout.py`'s `page_shell()` (or a new parameter/pre-built-fragment pattern) to reach `ctx["device_config"]`, since the current nav renderers (`sidebar_nav()`/`_mobile_nav_html()`) are called from `page_shell()` with no device-config parameter today | Area A.3 | If assumed away, the nav reminder either can't be built where the planner expects, or a page module import cycle is accidentally introduced trying to read device_config from inside `layout.py` directly |
| A2 | `theme-preview.js` needs a genuine rewrite (querySelectorAll/scoped-container strategy), not an additive extension, once 4-5 `.theme-chip-grid` elements can coexist on one page | Area B.5 | If under-scoped as "add a few lines," the script silently binds to the wrong grid and the Frame colours card's chip-click behaviour breaks for 3 of its 4 usages, likely undetected by a check that only tests the FIRST grid |
| A3 | D-14's "small grey secondary button" needs genuinely new CSS (no `.btn`/`.btn--secondary`/`.btn--small` class family exists anywhere in `style.css` today) | Area C.3 | If assumed to already exist, the plan writes markup referencing classes that render as plain unstyled `<button>`s — a visible, easily-missed-in-code-review defect |
| A4 | D-14's "masked feed URL (host + '…')" is a genuinely NEW capability (reading back and parsing the stored URL for display), not a rewording of the existing write-only convention every other secret-URL field in this codebase uses | Area C.4 | If implemented as a naive substring/byte-truncation of the raw URL rather than a real `urlsplit()`-based host extraction, path/query/token characters could leak into the rendered page |
| A5 | The `_edit_toggle_html` simple_mode gate (`airlines_page.py:1849-1850`) is exactly one delete site serving both D-17 and D-20 — not two independent changes that could be scheduled in two different plans and conflict | Area F.3/Pitfall 6 | Low risk if wrong (a merge conflict is loud, not silent), but worth flagging explicitly for wave-planning |

**If this table is empty:** not applicable — every entry above stems from direct code reads (file:line evidence given), not from unverified training-data assumptions about the codebase; these are flagged as "assumptions" only in the sense of "an inference from the evidence that the planner should double-check," not "an unverified claim."

## Open Questions

1. **Where does the Frame strip helper live, and how does it reach `ctx["device_config"]` from within `layout.py`'s existing nav/shell renderers?**
   - What we know: D-01 offers either a new `companion/pages/frame_strip.py` or a function in `companion/layout.py`; `page_shell()`'s current signature has no device-config parameter; `home_page.py`/`config_page.py` both already have `ctx["device_config"]` directly.
   - What's unclear: whether the strip is rendered by each page module directly (both `home_page.render()` and `config_page.render()` call the shared helper themselves, passing their own `ctx`) — which sidesteps the `page_shell()` question entirely — versus rendered by `page_shell()`/`app.py` itself, which needs new plumbing.
   - Recommendation: the simplest-to-verify shape is "each page module calls the shared helper with its own `ctx`, exactly like D-01's own text already says ('both Home and Display call with the same `ctx`')" — this needs NO `page_shell()` change at all, only the nav-reminder (a separate, smaller D-03 concern) needs new plumbing into `layout.py`'s renderers. Treat these as two separate design questions, not one.

2. **Does the nav state reminder (D-03) need `page_shell()`'s signature to grow, or can `app.py` pre-build the reminder HTML fragment and pass it through exactly like `flash`/`banner` already are?**
   - What we know: `flash`/`banner` are already pre-built-fragment parameters on `page_shell()`; `app.py`'s `_page_shell_for()` already has `ctx["device_config"]` available at its call site.
   - What's unclear: whether the reminder's dots/text should be computed once in `app.py` (cheap, consistent with existing `flash`/`banner` pattern) or via a shared `layout.py` function both `_page_shell_for()` and the strip helper (from Q1) can call, to guarantee the two "always consistent" as D-03 requires without risking drift between two independent computations.
   - Recommendation: one function (in `layout.py`, since both `app.py` and the strip helper need to call it and neither can import the other page module), called by both the strip helper and `_page_shell_for()`/`page_shell()`'s new reminder-fragment parameter — this satisfies D-03's "always consistent with it" requirement by construction rather than by discipline.

3. **Does the Frame colours card's no-JS floor really render FOUR stacked chip grids (departures/arrivals/calendar/rules), or three grids plus the rules list/form (as D-10 separately describes)?**
   - What we know: D-08's own text says "the four rows are plain radios and the card shows four stacked chip grids (one per usage, each `<fieldset>` labelled by its row)". D-10 separately says selecting the rules row shows "the existing rule list... and the existing 'add a rule' form... with its own compact chip grid for `rule_theme_id`" — i.e. NOT a bare chip grid, a whole list+form.
   - What's unclear: whether D-08's "four stacked chip grids" is loose phrasing that actually means "four stacked USAGE SECTIONS, the fourth of which is the rule list+form (which happens to contain its own chip grid), not literally four bare grids."
   - Recommendation: read D-08 and D-10 together as: no-JS floor = three bare `<fieldset>`-wrapped chip grids (departures/arrivals/calendar) PLUS the existing rules section (list + add-form, unchanged in its own internal shape) stacked as a fourth block — this reconciles both decisions without contradiction, but the orchestrator should confirm this reading with the developer/PRD author before the UI-SPEC locks it, since "four stacked chip grids" read overly literally would require inventing a chip-grid-shaped rendering for the rules usage that D-10 explicitly says should NOT be a chip grid.

4. **Is Home's rebuilt three-tile row (D-04) required to reuse `home_page._status_card_html()`'s CURRENT (phase-20, bug-fixed) content-derivation logic inside three `stat_tile()` calls, or does it fully revert to the phase-19 `_status_tiles_html()` body (which had the duplicated-verdict bug)?**
   - What we know: D-04 cites the phase-19 STRUCTURE (`git 614d41e~1`, three `stat_tile()` calls) explicitly, and separately says to keep "the phase 20 wording of `FRAME_STATE_TEXT`/`BATTERY_STATE_TEXT`/`DATA_STATE_TEXT`" — both dicts already exist unchanged in the current file, so this is satisfied either way. It does NOT explicitly say to keep the phase-20 BUG FIX (avoiding `health_state["device_html"]`'s double-verdict problem).
   - What's unclear: whether the planner should treat "restore the phase 19 shape" as license to copy phase-19's `_status_tiles_html()` body verbatim (reintroducing the bug byte-for-byte) or as "restore the three-tile LAYOUT, keeping every phase-20 content fix."
   - Recommendation: restore the LAYOUT (three `stat_tile()` calls in a grid) using the CURRENT, bug-fixed content-derivation (the same verdict/detail split `_status_card_html()`'s `status_row()` calls already use, just packaged into `stat_tile()`'s `content_html` parameter instead of `status_row()`'s markup) — never resurrect the byte-for-byte phase-19 function body, which is known-buggy. Flag this explicitly in the plan so a "restore from git history" instruction is not read as "copy-paste the old function."

## Sources

### Primary (HIGH confidence — direct source read, 2026-09-12)
- `companion/pages/home_page.py` (full read, current + phase-19 historical via `git show 614d41e~1`) — every constant and function, both versions
- `companion/pages/config_page.py` (targeted, near-full read of every function named in the task brief: `scope_groups()`, `theme_fieldset()`, `_theme_chip_grid_html()`, `_theme_live_preview_html()`, `quiet_hours_group()`, `display_group()`, `calendar_group()`, `calendar_connect_section()`, `calendar_disconnect_section()`, `calendar_disconnect_confirm_page()`, `_rule_kind_radio_html()`, `_rule_add_form_html()`, `_rule_suggestion_chips_html()`, `_rule_row_html()`, `_rule_list_html()`, `_rules_section_html()`, `_nested_wrapper_html()`, `_display_groups_html()`, `render()`, `handle_post()`'s theme/calendar/rules validation and resolution blocks) — 4091 lines total, ~1800 read directly
- `companion/pages/history_page.py` (targeted read: header/module docstring, `_HEADERS`, `_merged_cell()`, `_filter_text_attr()`, `_copy_button_html()`, `_callsign_hex_cell()`, `_unresolved_link_html()`, `_type_airline_cell()`, `_filter_bar_html()`, `_clock_cell_html()`, `_history_table_html()`, `_history_cards_html()`, `render()`) — 1058 lines total, ~500 read directly
- `companion/pages/health_page.py` (targeted: `REFRESH_PAUSE_TEXT`/`REFRESH_RESUME_TEXT`, the pause-toggle render block, `freshness_html`'s assembly)
- `companion/pages/airlines_page.py` (targeted: `_resolve_section_html()`, `_manual_resolution_rows()`, `_manual_summary_html()`, `_edit_toggle_html()`, `_lightbox_html()`)
- `companion/app.py` (targeted: route constants, `_handle_quick_toggle()`, `_handle_theme_post()`/`_handle_lang_post()`/`_handle_mode_post()`, `do_POST()`'s dispatch table, `_referring_tab()`, `_page_shell_for()`, `page_context()`)
- `companion/layout.py` (targeted: `NAV_GROUPS`/`NAV_TABS`, `_nav_groups()`, `sidebar_nav()`, `_theme_form_html()`/`_lang_form_html()`/`_mode_form_html()`, `_logout_form_html()`, `_mobile_nav_html()`, `login_shell()`, `page_shell()`, `status_dot()`, `stat_tile()`, `card_status_class()`, `status_row()`, script-src constants)
- `companion/prefs.py` (full read, 61 lines)
- `companion/i18n_fr/__init__.py` (full read, 47 lines)
- `companion/test_i18n.py` (targeted: module docstring, catalogue/dead-translation check bodies, simple-mode-specific checks)
- `server/device_config.py` (targeted: `normalise_theme_arriving()`, `normalise_calendar_theme_id()`, `CLEAR_THEME_ARRIVING` sentinel contract, `save_device_config()`'s theme_arriving resolution)
- `companion/static/theme-preview.js` (full read, 81 lines), `companion/static/freshness.js` (targeted, ~200 of 489 lines), `companion/static/dirty-state.js` (targeted, header only), `companion/static/style.css` (targeted greps + direct reads across ~15 regions: nav/sidebar, stat-tile, home-hero/status-card, quick-action, rule-list/row, theme-chip-grid, calendar fusion, data-table-wrap, dashboard-shell/main breakpoints, details/summary)
- Live grep of every simple_mode/MODE_*/ui-mode reference across `companion/` and `server/` (the exact command the task brief specified)
- `git show 614d41e~1:companion/pages/home_page.py` — the phase-19 three-tile shape, verified byte-for-byte
- `/tmp/.../scratchpad/shots20.js` and directory listing — the exact headless-sweep mechanism already proven in this session
- `.planning/phases/21-.../21-CONTEXT.md`, `21-PRD.md` — every D-01..D-20 decision's exact wording
- `.planning/phases/20-.../20-RESEARCH.md`, `20-CONTEXT.md` — the prior phase's document shape, the code facts it established (which this research re-verified directly rather than trusting), and its own three CRITICAL-pitfall pattern (reused as the template for this phase's own pitfalls)
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the design-system contract (tokens, accent-reservation list, touch-target register, card/nav idioms)
- `.planning/STATE.md`, `.planning/ROADMAP.md` — phase 20 closure confirmation, phase 21's own ROADMAP entry (0 plans, depends on Phase 20)
- `.planning/REQUIREMENTS.md` — CFG-19..CFG-24's exact wording, CFG-18's withdrawal note

### Secondary (MEDIUM confidence)
- None — this phase is entirely internal-codebase research; no library, framework, or external API needed investigation.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new dependencies, confirmed by reading every file this phase's six decisions name
- Architecture: HIGH — every decision's landing site verified by file:line read, not inferred from summaries; four structural conflicts (Pitfalls 1-4 above) found by direct code trace
- Pitfalls: HIGH — every pitfall is grounded in a specific, quoted source line or a direct arithmetic/grep confirming its scope (e.g. the 880px column-width derivation, the exact `handle_post()` validation-then-resolution ordering, the confirmed absence of any `.btn` class family)
- Test inventory (Area E, F): HIGH for the counted/located checks; MEDIUM for the five Wave-0 Gaps items explicitly flagged as "not read in this pass" (test-file ownership for History/Flights, the exact `:has()` block-count pin, the exact nav-footer-switch-order check boundaries, the exact edit_mode-upload-absence checks, the exact pause-button checks) — these need a direct read before their respective plans are written, not before this research is accepted

**Research date:** 2026-09-12
**Valid until:** This research is tied to the exact commit state read on 2026-09-12 (branch `claude/web-companion-audit-ux-refactor-bqx7si`); re-verify file:line references and `EXPECTED_CHECK_COUNT` values if planning is delayed more than a few days past this date or if any other phase/quick-task touches the same files first.
