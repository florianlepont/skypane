# Component catalogue

The companion's shared interface components. **Rule: new UI uses a catalogue
component, or extends it and its entry on the admin Components page
(`/components`, `companion/pages/components_page.py`).** Never add a second
class that does a catalogue component's job. A guard test
(`companion/test_components_page.py`) fails when a public helper of the
component modules is neither rendered on that page nor named in its `EXEMPT`
table with a reason, and a browser test (`companion/test_browser_components_page.py`)
checks every family's geometry and contrast at 360 and 1280 px, light and
dark, English and French.

The page renders each family through the same helper the pages call, in every
state (default, selected, disabled, error, long text, empty, open/closed). Open
it from the Fleet page's System view footer. To add a component or a state: add
the helper, add a state or family to `CATALOGUE` with its French strings in
`companion/i18n_fr/components.py`, and run the browser test.

## One contract per family

| Family | Canonical helper | Class and states | Use it when |
|--------|------------------|------------------|-------------|
| Button | `ui_components.button_html`, `icon_button_html` | `.btn` + `.btn--primary` (the page's one main action), `--secondary` (every other action), `--ghost` (quiet text action), `--danger` (destructive), `--icon` (44px square, glyph only); disabled via `disabled` / `aria-disabled` | any action; never style a bare `<button>` or invent a per-page button class |
| Title with icon action | `ui_components.title_action_html`, `icon_link_html`, `pages/home_title.title_html` | `.title-action`: the page `<h1>` (`.title-action__text`, 48px desktop, 28px phone, 24px under 380px) with one quiet icon link (`icon_link_html`) beside it: a 20px glyph (18px under 380px) in the muted text colour, no disc at rest, a light halo only on hover and focus, inside an invisible 44px hit area centred on the title's first line; a long title wraps inside its own box and never pushes the action under it | the page title when it names the thing and one quick action belongs to it (Home: the frame name and its rename pencil) |
| Switch | `ui_components.switch_button_html` (and `quick_switch_html` + `quick_switch_state_html` for a posted switch), `form_switch_html` | `.switch` (`aria-checked`), native checkbox in `.settings-checkbox` drawn as the same switch; 52x32 track, 24px knob, on = accent, off = `--color-switch-off` | a two-state setting; the form form for a value saved with the form |
| Segmented control | `ui_segmented.segmented_radios_html`, `segmented_buttons_html`, `segmented_links_html`; chips: `ui_filter.filter_bar_html`, `chip_links_html` | one track (glass fill, `--seg-edge`), selected = solid `--seg-selected-bg` pill with `--seg-selected-fg` text, idle = `--seg-idle-fg`; 44px segments, centred labels; radios `.theme-form`, links `.personalisation-nav`, chips `.filter-chip` | choosing one of 2-6 options (a value, a page, a filter); the tokens are the only place the look is set |
| Text field | `ui_components.text_field_html`, `ui_modal.field_error_html` | `.modal__field` label + full-width input + help; error adds `aria-invalid`; number input keeps a width that holds its placeholder | any labelled input |
| Search | `ui_filter.filter_title_search_html`, `filter_title_search_form_html` | opens from the title row | filtering a list |
| Menus | `ui_filter.sort_menu_html`, `ui_entity_list.row_menu_html` | closed / open | sort choice, row actions |
| Cards and rows | `ui_groups.group`, `group_panel`, `row`, `section_label`, `chip_html`, `hero`; `ui_components.stat_tile`, `status_row`, `section_intro_html` | glass group, rows with detail / value / trailing control | every page section |
| Lists and tables | `ui_entity_list.entity_list_html`, `entity_row_html`, `count_line_html`; `ui_components.data_table` | long names wrap; empty table renders the empty state | lists of entities, tabular data |
| Badges and status | `ui_components.pill_html`, `status_dot`, `battery_charging_pill_html` | neutral pill; ok / warn / error dot with a text label | a status or count beside a title |
| Toasts and banners | `ui_components.toast_html`, `toast_link_action_html`, `toast_post_action_html`, `anomaly_banner` | five tones; docked banner for a persistent state | an outcome or a standing condition |
| Empty states | `ui_components.empty_state`, `ui_filter.filter_empty_html` | plain, compact, search with no match (counts stay at the whole history's); a compact one inside a flush section card (Fleet State) keeps the card's 16px inner padding | a list with nothing to show |
| Dialogs, save bar | `ui_modal.dialog_html`, `sections_dialog_html`, `trigger_html`; `ui_save_bar.save_bar_html` | closed with a trigger; save bar primary + secondary buttons; the Flights picture dialog is one opaque card holding the picture, its caption and a secondary Close (never a bare image with controls floating over the page) | a focused task; unsaved changes |
| Page header | `ui_components.page_header` | title, purpose, action | every page |

## Rules that came out of unifying the families

- Selected is always a solid pill (>= 3:1 against its track), never a faint
  wash; the track always has a visible edge in light and dark.
- A segmented chip row never scrolls sideways with a cut-off label: link chips
  wrap onto a second row of the track, and a short row shrinks its labels.
- Every control is a 44px target (the sidebar does not keep a compact
  variant any more); a field inside `.modal__field` runs the full card width.
- A new destructive action is `.btn--danger`; the page's one main action is
  `.btn--primary`; everything else is `.btn--secondary`.
- A list row of one line centres its status dot on the title; a row with a second line keeps the dot on the title's line.
- Component colours come from tokens; the `--seg-*` tokens are the only place
  the segmented look changes.

- The Location search's suggestion list ends in one status row
  (`.place-results__status`): a spinner and "Searching…" while the geocoder has
  not answered, then "No place found" or a short failure line; the answer
  replaces it. The spinner is the finite `.place-loading__spinner`.
- On a phone the Location page's nearest-airport offer is a single 44px button
  over the map above the bottom buttons, never a card in the sheet (a card
  lifted the sheet over the pin just dropped).

## Page names (glossary)

One name per page. The page title, the document title, the sidebar entry, the
headings and the Components page use the **full name**. The phone tab bar
(space-limited) shows a **word of that name** (the short form), never a
different word. A phone tab label must fit its cell at 360px (about 52px wide
at 11px: "Location" is the longest). The Components page lists the live table
(family "Page names").

| Page | Full name (EN / FR) | Tab bar (EN / FR) |
|------|---------------------|-------------------|
| Home | Home / Accueil | Home / Accueil |
| Flights | Flight history / Historique des vols | History / Vols |
| Location | Location and detection / Lieu et détection | Location / Lieu |
| Style | Style / Style | Style / Style |
| Airlines | Airlines / Compagnies | (More sheet) |
| Airline editor (Console) | Airline editor / Éditeur de compagnies | Editor / Éditeur |
| Users (Console) | Users / Utilisateurs | Users / Équipe (no shorter form of "Utilisateurs" fits) |

Concept words, EN / FR: frame / cadre (the screen), look / allure (never
"look" in French; "special look" is "allure spéciale"), airline / compagnie,
Style (the page holding the looks and the calendar) is never called
"Personalisation" any more. A new page picks its full name and, only if it must
fit the tab bar, a word of it.

Focus ring: every link and button draws the global 2px ring at a 2px offset around its own box, so a tap target taller than its text is made with a `::after` reaching past the box (never padding plus negative margin), which keeps the ring tight (Home's quiet-hours window link). A dialog closed by pointer or touch returns focus without the keyboard ring; closed from the keyboard it keeps it.
