# Components

The companion's shared interface components. **Rule: new UI uses a catalogue component, or
extends it and its entry on the admin Components page (`/components`,
`companion/pages/components_page.py`).** Never add a second class that does a catalogue
component's job, and never style a bare `<button>`.

Guards: `companion/test_components_page.py` fails when a public helper of the component
modules is neither rendered on that page nor named in its `EXEMPT` table with a reason;
`companion/test_browser_components_page.py` checks every family's geometry and contrast at
360 and 1280px, light and dark, English and French. The page renders each family through
the helper the pages call, in every state (default, selected, disabled, error, long text,
empty, open/closed). It is linked from the Fleet page's System view footer
(`console_fleet_view.py`). To add a component or state: add the helper, add a family or
state to `CATALOGUE` with French strings in `companion/i18n_fr/components.py`, run the
browser test. Tokens: `tokens-and-theming.md`.

## One contract per family

| Family | Canonical helper | Class and states | Use it when |
|--------|------------------|------------------|-------------|
| Button | `ui_components.button_html`, `icon_button_html`, `icon_link_html` | `.btn` (44px min height, 15px/600, radius 14px) + `--primary` (the page's one main action, graphite/ivory), `--secondary` (every other action, glass), `--ghost` (quiet text action), `--danger` (destructive), `--icon` (44px square); disabled via `disabled` / `aria-disabled` | any action |
| Title with icon action | `ui_components.title_action_html`, `pages/home_title.title_html` | `.title-action`: the page `<h1>` with one quiet icon link; hit area 44px centred on the first line; a long title wraps inside its box | the title names the thing and one quick action belongs to it (Home: frame name + rename pencil) |
| Switch | `switch_button_html`, `quick_switch_html` + `quick_switch_state_html` (posted switch), `form_switch_html` | `.switch` (`aria-checked`), 52x32 track, 24px knob, on = accent, off = `--color-switch-off`; the button is the 44px target; a native checkbox in `.settings-checkbox` is drawn as the same switch | a two-state setting |
| Segmented control | `ui_segmented.segmented_radios_html`, `segmented_buttons_html`, `segmented_links_html`; chips `ui_filter.filter_bar_html`, `chip_links_html` | one glass track with `--seg-edge`; selected = solid `--seg-selected-bg` pill; 44px segments; label then count on one line; links `.personalisation-nav`, chips `.filter-chip` | choosing one of 2-6 options |
| Text field | `ui_components.text_field_html`, `ui_modal.field_error_html` | `.modal__field` label + full-width 44px input + help; error adds `aria-invalid` | any labelled input |
| Search, menus | `ui_filter.filter_title_search_html`, `sort_menu_html`, `ui_entity_list.row_menu_html` | search opens from the title row; sort is a 44px round icon button opening a `<details class="row-menu">` of radio rows | filtering and sorting a list; row actions |
| Groups and rows | `ui_groups.group`, `group_panel`, `row`, `section_label`, `chip_html`, `hero` | `h2.section-label` (13px) over one glass `ul.group` of rows (min 54px, hairline between rows, 32px icon chip, label, detail, value, chevron, trailing control); `group_panel` holds free content; a group never contains a group | every list of settings, facts, entities |
| Cards | `ui_components.stat_tile`, `status_row`, `section_intro_html`; `.page-section` | glass free-content card; `.stat-tile` survives on Health and the Components page only | free content that cannot be rows |
| Lists and tables | `ui_entity_list.entity_list_html`, `entity_row_html`, `count_line_html`; `ui_components.data_table` | glass table wrapper (header 12px/600, not uppercase, rows min 56px); cards or groups below 70rem where the page says so; empty table renders the empty state | entities, tabular data |
| Pills, dots | `ui_components.pill_html(text, tone)`, `status_dot`, `battery_charging_pill_html` | neutral pill, tones `ok` / `info` / `warn` (`PILL_TONES`); ok / warn / error / off dots plus `.dot--hollow`, always with a text label | a status or count beside a title |
| Toasts, banners | `toast_html`, `toast_link_action_html`, `toast_post_action_html`, `anomaly_banner` | five tones; `.toast--docked` for a persistent state; see Toast below | an outcome or a standing condition |
| Empty states | `empty_state` (plain, compact), `ui_filter.filter_empty_html` | compact inside a flush card keeps 16px inner padding; search with no match keeps counts at the whole history's | a list with nothing to show |
| Dialogs, sheets | `ui_modal.dialog_html`, `sections_dialog_html`, `choice_dialog_html`, `trigger_html`; `modal.js` | see Dialogs below | a focused task or a question |
| Save bar | `ui_save_bar.save_bar_html`, `leave_dialog_html` | see Save bar below | unsaved changes |
| Link card | `ui_components.link_card_html` | a glass card row with glyph, title, subtitle (the More panel's Console card) | a prominent link to another area |
| Page header | `ui_components.page_header` | title, optional purpose, action | every page |

## Toast

`ui_components.toast_html`, `companion/flash.py` (`FLASH_TONES`), `static/toast.js`.
- Inverse slab; 28px tone disc with glyph; bold title and muted detail split at ` — `;
  optional action (a real POST form such as Undo, or a link) and a 44px dismiss. Tone is
  never colour alone (glyph + hidden spoken prefix). Role `status` for success / info /
  pending, `alert` for warning / error.
- Auto-hide only success / info (`--motion-toast-dwell` 6s) and pending
  (`--motion-toast-dwell-long` 12s, `data-toast-autohide="long"`); the timer pauses on hover,
  focus and a hidden document. Warning and error never auto-hide.
- Placement: floating regions `.toast-region--flash` and `.toast-region--live` (z-index 40)
  under `@media (scripting: enabled)`: top centre on desktop, above the tab bar and above
  the Save bar on a phone. A floating toast is dismissed by a sideways swipe past 80px or a
  flick (`is-swiping`, `is-returning`, `is-leaving`). Without script a flash is an in-flow banner
  whose dismiss link reloads without `?flash=`.
- Persistent states (health anomaly, update rollback, Home attention) use `.toast--docked`:
  glass, in flow, no dismiss, no timer.
- Live failures (quick switch, expired session) are cloned from a `<template>` into the live
  region (`session-guard.js`, `ui_shell.py`). The Users Active switch answers with an
  `X-Quick-Switch-Result` header and a toast.

## Dialogs and sheets

`ui_modal.dialog_html` renders a `<dialog class="modal">` opened by `modal.js` from a trigger.
- Opaque surface over a dimmed page, not glass. On a phone a bottom sheet with 28px top
  radius and a grabber; the dialog container draws no focus ring (its controls do).
- `dialog.modal.access-sheet` (Manage access): fixed head (title, frame name, 44px close), body that scrolls
  inside (`max-height: 85dvh`, `overscroll-behavior: contain`), one labelled group of
  rows, a full-width primary Add and a secondary Done.
- `choice_dialog_html`: a question with three buttons (the unsaved-changes dialog).
- A dialog closed by pointer or touch returns focus without the keyboard ring; closed by
  keyboard it keeps it.
- The Flights picture dialog is one opaque card (picture, caption, secondary Close),
  never a bare image with floating controls.

## Save bar and unsaved changes

One producer, `ui_save_bar.save_bar_html`: a floating bar (message, Cancel, Save), one CSS
block `.dirty-bar`, one script `static/dirty-state.js`. Every page with something to save
uses it (settings, Fleet settings, Place, the Style form pages).
- Tracked mode (`form_id` of a `data-dirty-form` form): rendered with `data-dirty-wait`;
  with script the stylesheet keeps it out of the first paint and `dirty-state.js` shows it
  when a field differs; without script it is a plain, always visible Save
  (`data-static-save-fallback`). Cancel is a native `type="reset"`; focus returns to the
  last changed control. Message: "Unsaved changes", or "Unsaved changes:" plus the changed
  areas when several differ.
- Page mode (`cancel_href`): Cancel is a link back, the message is the page title; always
  shown, or `reveal_on_change`, or `shown` for a redraw with a refused value.
- `inline=True`: on a phone the two buttons of the card that holds the bar (the Place sheet);
  the message is read aloud only.
- Leave guard: `page_shell` renders `leave_dialog_html()` ("Save and continue" / "Discard" /
  "Stay here", `LEAVE_DIALOG_ID = "unsaved-changes"`) once on any page with a bar. Any in-app
  link, including the bottom tab bar, opens it while something is unsaved. "Save and continue"
  lands on a destination listed in `return_routes`, otherwise it saves and stays. Style also
  asks before leaving a sub-tab with an unsaved layout.

## App bar, frame menu

- Phone app bar: transparent over the sky (no fill, no border, no blur), padded by `--safe-top`
  (+ `--app-bar-drop` in an iPhone Home Screen app), brand left, frame button right.
  Desktop collapses `.site-header` to the frame button.
- Frame menu (`companion/frame_menu.py`, native `details.frame-menu`): a glass button naming the
  frame in view (top bar on a phone, top right of the content on desktop) opening a popover
  (300px wide, rows 52px) with one row per frame, an "Add a frame" row and, in the Console, a
  "System" row. Rows are plain links; `modal.js` adds Escape, outside tap and focus return.
  Test: `companion/test_browser_frame_menu.py`.

## Rules that hold across families

- Motion is opacity and translate only on at most a screenful of blocks (see `motion.md`).
- Selected is a solid pill, >= 3:1 against its track; the track always shows an edge in both
  themes. Chip rows never scroll sideways with a cut-off label (link chips wrap, short rows
  shrink their labels).
- Every control is a 44px target; a field inside `.modal__field` runs the full card width.
- A destructive action is `.btn--danger`; the one main action `.btn--primary`; the rest
  `.btn--secondary`.
- A one-line list row centres its status dot on the title; a row with a second line keeps the
  dot on the title's line.
- Colours come from tokens; the `--seg-*` tokens are the only place the segmented look changes.
- Focus ring: the global 2px ring at 2px offset around the element's own box. A tap target
  taller than its text uses an `::after` reaching past the box (never padding plus negative
  margin) so the ring stays tight. An icon-only button (the `.copy-btn`, 22px box) draws its
  44px hit area with `::before`.
- Place search results end in one status row (`.place-results__status`: spinner while the
  geocoder has not answered, then "No place found" or a failure line). On a phone the
  nearest-airport offer is one 44px button over the map, not a card in the sheet.

## Legacy still in the code (do not copy)

A bare `button { height: 30px }` and `button[type="submit"]` accent fill remain as a base
that `.btn` overrides. Some pages still render raw buttons (`airlines_page.py`,
`co_managers_card.py`, `locations_page.py`, `pair_frame_page.py`, `update_page.py`) and
legacy class names (`.runway-card` for the Style look picker, `.mobile-nav__link` for the
More Account row). New code uses `.btn` and the helpers above.
