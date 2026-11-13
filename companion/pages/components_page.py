"""The Components page: every shared UI component in every state, rendered
through the same Python helpers the pages use (never copied markup).

Admin-only reference. Each family lists the helpers it exercises
(`CATALOGUE`), so a helper that is not on the page cannot hide: the catalogue
test calls the page and checks that every listed helper ran, and that every
public helper of the component modules is either listed or named in `EXEMPT`
with the reason it is not a standalone component.

The page follows the reader's theme and language like any other page, so the
light/dark and English/French renders are the same markup.
"""
from typing import NamedTuple

import companion.layout  # noqa: F401  (loads the navigation before the component modules)
from companion import (
    i18n, ui_components, ui_entity_list, ui_filter, ui_groups, ui_modal, ui_save_bar,
    ui_segmented)
from companion import ui_base
from companion.ui_base import escape_html

COMPONENTS_ROUTE = "/components"

TITLE = i18n.msg("components.title", "Components")
PURPOSE = i18n.msg(
    "components.purpose",
    "Every shared interface component in every state. The page follows the theme "
    "and language you have chosen: switch them in the More menu to see the others.")
LINK_TEXT = i18n.msg("components.link", "Interface components")
_INDEX_LABEL = i18n.msg("components.index_label", "Component families")
_HELPERS_LABEL = i18n.msg("components.helpers_label", "Helpers")
_TO_INDEX_LABEL = i18n.msg("components.to_index", "Back to the index")

_DEFAULT = i18n.msg("components.state_default", "Default")
_DISABLED = i18n.msg("components.state_disabled", "Disabled")
_LONG = i18n.msg("components.state_long_text", "Long text")
_ERROR = i18n.msg("components.state_error", "Error")
_EMPTY = i18n.msg("components.state_empty", "Empty")
_ON = i18n.msg("components.state_on", "On")
_OFF = i18n.msg("components.state_off", "Off")
_OPEN = i18n.msg("components.state_open", "Open")
_CLOSED = i18n.msg("components.state_closed", "Closed")

_SAVE = i18n.msg("components.sample_save", "Save changes")
_CANCEL = i18n.msg("components.sample_cancel", "Cancel")
_DELETE = i18n.msg("components.sample_delete", "Delete frame")
_LONG_LABEL = i18n.msg(
    "components.sample_long_label",
    "A deliberately long label that has to fit a phone without clipping")
_SAMPLE_NAME = i18n.msg("components.sample_name", "Frame name")
_SAMPLE_HELP = i18n.msg("components.sample_help", "Up to 40 characters.")
_SAMPLE_ERROR = i18n.msg("components.sample_error", "Enter a name of 1 to 40 characters.")
_SAMPLE_VALUE = i18n.msg("components.sample_value", "Kitchen frame")
_SAMPLE_LONG_VALUE = i18n.msg(
    "components.sample_long_value",
    "The frame in the kitchen next to the window, facing runway three")
_SAMPLE_SEARCH = i18n.msg("components.sample_search", "Search flights")
_SAMPLE_PLACEHOLDER = i18n.msg("components.sample_placeholder", "Callsign, airline or type")
_SAMPLE_CARD = i18n.msg("components.sample_card_title", "Frame settings")
_SAMPLE_ROW = i18n.msg("components.sample_row", "Wake interval")
_SAMPLE_ROW_DETAIL = i18n.msg("components.sample_row_detail", "How often the frame checks for flights")
_SAMPLE_VALUE_TEXT = i18n.msg("components.sample_row_value", "5 minutes")
_SAMPLE_TILE = i18n.msg("components.sample_tile", "Battery")
_SAMPLE_EMPTY_HEADING = i18n.msg("components.sample_empty_heading", "No flights yet")
_SAMPLE_EMPTY_BODY = i18n.msg(
    "components.sample_empty_body", "Flights appear here after the next poll cycle.")
_SAMPLE_FILTER_EMPTY = i18n.msg("components.sample_filter_empty", "No flight matches")
_SAMPLE_FILTER_EMPTY_BODY = i18n.msg(
    "components.sample_filter_empty_body", "Clear the search to see all 42 flights.")
_SAMPLE_TOAST_TITLE = i18n.msg("components.sample_toast_title", "Frame renamed")
_SAMPLE_TOAST_DETAIL = i18n.msg(
    "components.sample_toast_detail", "The new name shows everywhere.")
_SAMPLE_ACTION = i18n.msg("components.sample_toast_action", "Undo")
_SAMPLE_DIALOG = i18n.msg("components.sample_dialog_title", "Rename frame")
_SAMPLE_CONFIRM = i18n.msg("components.sample_confirm_title", "Delete this frame?")
_SAMPLE_CONFIRM_BODY = i18n.msg(
    "components.sample_confirm_body", "This cannot be undone.")
_OPEN_DIALOG = i18n.msg("components.open_dialog", "Open the dialog")
_OPEN_CONFIRM = i18n.msg("components.open_confirm", "Open the confirmation")
_CLOSE = i18n.msg("components.close", "Close")
_SORT = i18n.msg("components.sample_sort", "Sort")
_SORT_NEWEST = i18n.msg("components.sample_sort_newest", "Newest first")
_SORT_OLDEST = i18n.msg("components.sample_sort_oldest", "Oldest first")
_SORT_AIRLINE = i18n.msg("components.sample_sort_airline", "Airline")
_ALL = i18n.msg("components.sample_all", "All")
_DEPARTURES = i18n.msg("components.sample_departures", "Departures")
_ARRIVALS = i18n.msg("components.sample_arrivals", "Arrivals")
_PAIRING = i18n.msg("components.sample_pairing", "Pairing")
_RELEASES = i18n.msg("components.sample_releases", "Releases")
_SAMPLE_ENTITY = i18n.msg("components.sample_entity", "Orly frame")
_SAMPLE_ENTITY_META = i18n.msg("components.sample_entity_meta", "owner@example.test")
_SAMPLE_ENTITY_LONG = i18n.msg(
    "components.sample_entity_long",
    "A frame with a very long name that should wrap inside its own row")
_ONLINE = i18n.msg("components.sample_online", "Online")
_STALE = i18n.msg("components.sample_stale", "Not heard for a while")
_OFFLINE = i18n.msg("components.sample_offline", "Offline")
_COL_AIRLINE = i18n.msg("components.sample_col_airline", "Airline")
_COL_FLIGHTS = i18n.msg("components.sample_col_flights", "Flights")
_COL_LAST = i18n.msg("components.sample_col_last", "Last seen")
_HERO_LINE = i18n.msg("components.sample_hero_line", "A320 landing on runway 3")
_MENU_RENAME = i18n.msg("components.sample_menu_rename", "Rename")
_MENU_REMOVE = i18n.msg("components.sample_menu_remove", "Remove")
_MENU_LABEL = i18n.msg("components.sample_menu_label", "Row actions")
_WAKE = i18n.msg("components.sample_wake", "Wake interval (seconds)")
_QUIET = i18n.msg("components.sample_quiet", "Enable quiet hours")
_SWITCH_LABEL = i18n.msg("components.sample_switch_label", "Screen")
_SWITCH_ON = i18n.msg("components.sample_switch_on", "Screen on")
_SWITCH_OFF = i18n.msg("components.sample_switch_off", "Screen off")
_THEME = i18n.msg("components.sample_theme", "Theme")
_KIND_FLIGHT = i18n.msg("components.sample_kind_flight", "Flight")
_KIND_AIRCRAFT = i18n.msg("components.sample_kind_aircraft", "Aircraft")
_KIND_AIRLINE = i18n.msg("components.sample_kind_airline", "Airline")
_KIND_AIRLINE_LONG = i18n.msg(
    "components.sample_kind_airline_long", "Airline and aircraft family")
_SAMPLE_PILL = i18n.msg("components.sample_pill", "Success")
_SAMPLE_TILE_NEUTRAL = i18n.msg("components.sample_tile_neutral", "Neutral")
_SAMPLE_TILE_OK = i18n.msg("components.sample_tile_ok", "Healthy")
_SAMPLE_TILE_WARN = i18n.msg("components.sample_tile_warn", "Needs attention")
_SAMPLE_TILE_ERROR = i18n.msg("components.sample_tile_error", "Failing")
_BANNER = i18n.msg(
    "components.sample_banner", "The frame has not reported for an hour")
_STATUS_VERDICT = i18n.msg("components.sample_status_verdict", "Reporting normally")
_STATUS_DETAIL = i18n.msg("components.sample_status_detail", "Last report two minutes ago")
_STATUS_LABEL = i18n.msg("components.sample_status_label", "Connection")
_SECTION_HEADING = i18n.msg("components.sample_section_heading", "Display")
_SECTION_DESCRIPTION = i18n.msg(
    "components.sample_section_description", "What the frame shows and when.")
_HEADER_TITLE = i18n.msg("components.sample_header_title", "Flight history")
_HEADER_PURPOSE = i18n.msg(
    "components.sample_header_purpose", "Every plane the frame has shown, newest first.")
_UNSAVED = i18n.msg("components.sample_unsaved", "2 unsaved changes")
_M_STATE_SAVE_BAR_REVEALED = i18n.msg(
    "components.state_save_bar_revealed",
    "Form page bar: hidden until a field changes (type in the field)")

_M_STATE_LINK = i18n.msg("components.state_link", "Link")
_M_STATE_ICON = i18n.msg("components.state_icon", "Icon")
_M_STATE_ICON_LINK = i18n.msg("components.state_icon_link", "Icon link")
_M_STATE_TITLE_ACTION = i18n.msg("components.state_title_action", "Title with icon action")
_RENAME = i18n.msg("components.sample_rename", "Rename frame")
_M_STATE_QUICK_ON = i18n.msg("components.state_quick_on", "Quick switch, on")
_M_STATE_QUICK_OFF = i18n.msg("components.state_quick_off", "Quick switch, off")
_M_STATE_FORM_SWITCH = i18n.msg("components.state_form_switch", "Form field switch")
_M_STATE_BUTTONS = i18n.msg("components.state_buttons", "Buttons that post")
_M_STATE_LINKS = i18n.msg("components.state_links", "Links to pages")
_M_STATE_CHIPS = i18n.msg("components.state_chips", "Filter chips")
_M_STATE_CHIP_LINKS = i18n.msg("components.state_chip_links", "Filter chips as links")
_M_STATE_NUMBER = i18n.msg("components.state_number", "Number")
_M_SAMPLE_NUMBER_HINT = i18n.msg("components.sample_number_hint", "Default")
_M_STATE_SEARCH = i18n.msg("components.state_search", "Search")
_M_STATE_SEARCH_VALUE = i18n.msg("components.state_search_value", "Search with a value")
_M_STATE_ROW_MENU = i18n.msg("components.state_row_menu", "Row actions menu")
_M_STATE_ROWS = i18n.msg("components.state_rows", "Group of rows")
_M_STATE_PANEL = i18n.msg("components.state_panel", "Panel")
_M_STATE_SECTION_LABEL = i18n.msg("components.state_section_label", "Section label")
_M_STATE_SECTION_INTRO = i18n.msg("components.state_section_intro", "Section introduction")
_M_STATE_TILES = i18n.msg("components.state_tiles", "Tiles by status")
_M_STATE_STATUS_ROWS = i18n.msg("components.state_status_rows", "Status rows")
_M_STATE_HERO = i18n.msg("components.state_hero", "Hero")
_M_STATE_LINK_CARD = i18n.msg("components.state_link_card", "Link card")
_M_STATE_LINK_CARD_PLAIN = i18n.msg("components.state_link_card_plain", "Link card, title only")
_SAMPLE_LINK_CARD_SUB = i18n.msg("components.sample_link_card_subtitle", "Fleet, users, audit")
_M_STATE_TABLE = i18n.msg("components.state_table", "Table")
_M_STATE_TABLE_LONG = i18n.msg("components.state_table_long", "Table, long text")
_M_STATE_TABLE_EMPTY = i18n.msg("components.state_table_empty", "Table, empty")
_M_STATE_PILL = i18n.msg("components.state_pill", "Pill")
_M_STATE_DOTS = i18n.msg("components.state_dots", "Status dots")
_M_STATE_CHARGING = i18n.msg("components.state_charging", "Charging pill")
_M_STATE_TOASTS = i18n.msg("components.state_toasts", "Toasts by tone")
_M_STATE_TOAST_ACTIONS = i18n.msg("components.state_toast_actions", "Toasts with an action")
_M_STATE_TOAST_OFFLINE = i18n.msg(
    "components.state_toast_offline", "List not updated (no connection)")
_M_STATE_BANNER_ERROR = i18n.msg("components.state_banner_error", "Banner, error")
_M_STATE_BANNER_WARN = i18n.msg("components.state_banner_warn", "Banner, warning")
_M_STATE_EMPTY_COMPACT = i18n.msg("components.state_empty_compact", "Compact, inside a card")
_M_STATE_EMPTY_SEARCH = i18n.msg("components.state_empty_search", "Search with no match")
_M_STATE_DIALOGS = i18n.msg("components.state_dialogs", "Dialogs (open them)")
_M_STATE_SAVE_BAR = i18n.msg("components.state_save_bar", "Save bar")
_M_STATE_SAVE_BAR_INLINE = i18n.msg(
    "components.state_save_bar_inline", "Save bar, inline in a card (phones)")
_M_STATE_HEADER_FULL = i18n.msg("components.state_header_full", "With purpose and action")
_M_FAMILY_HEADERS = i18n.msg("components.family_headers", "Page header")
_M_FAMILY_HEADERS_DESC = i18n.msg("components.family_headers_desc", "The title, the purpose line and the page's main action.")
_M_FAMILY_BUTTONS = i18n.msg("components.family_buttons", "Buttons")
_M_FAMILY_BUTTONS_DESC = i18n.msg("components.family_buttons_desc", "One button with four variants: primary for the page's main action, secondary for "
                        "everything else, ghost for a quiet action, danger for a destructive one.")
_M_FAMILY_SWITCHES = i18n.msg("components.family_switches", "Switches")
_M_FAMILY_SWITCHES_DESC = i18n.msg("components.family_switches_desc", "One switch: a button that flips at once, and the same drawing on a form checkbox.")
_M_FAMILY_SEGMENTED = i18n.msg("components.family_segmented", "Segmented controls and chips")
_M_FAMILY_SEGMENTED_DESC = i18n.msg("components.family_segmented_desc", "One track, one selected pill. Radios inside a form, buttons that post, links "
                        "between pages and filter chips all share it.")
_M_FAMILY_INPUTS = i18n.msg("components.family_inputs", "Inputs and search")
_M_FAMILY_INPUTS_DESC = i18n.msg("components.family_inputs_desc", "A labelled field runs the full width of its card; search opens from the title row.")
_M_FAMILY_MENUS = i18n.msg("components.family_menus", "Menus and sort")
_M_FAMILY_MENUS_DESC = i18n.msg("components.family_menus_desc", "The sort menu and the row actions menu.")
_M_FAMILY_CARDS = i18n.msg("components.family_cards", "Cards, groups and tiles")
_M_FAMILY_CARDS_DESC = i18n.msg("components.family_cards_desc", "The surfaces pages are built from.")
_M_FAMILY_LISTS = i18n.msg("components.family_lists", "Lists and tables")
_M_FAMILY_LISTS_DESC = i18n.msg("components.family_lists_desc", "Entity rows with a status dot, and the data table.")
_M_FAMILY_BADGES = i18n.msg("components.family_badges", "Badges and status")
_M_FAMILY_BADGES_DESC = i18n.msg("components.family_badges_desc", "Pills, status dots and the charging pill.")
_M_FAMILY_MESSAGES = i18n.msg("components.family_messages", "Toasts and banners")
_M_FAMILY_MESSAGES_DESC = i18n.msg("components.family_messages_desc", "Shown docked here so they stay in the page; a real toast floats and fades.")
_M_FAMILY_EMPTY = i18n.msg("components.family_empty", "Empty states")
_M_FAMILY_EMPTY_DESC = i18n.msg("components.family_empty_desc", "What a list shows when there is nothing to list.")
_M_FAMILY_DIALOGS = i18n.msg("components.family_dialogs", "Dialogs and the save bar")
_M_FAMILY_DIALOGS_DESC = i18n.msg("components.family_dialogs_desc", "Open a dialog to see it; the save bar is shown in flow.")
_M_FAMILY_NAMES = i18n.msg("components.family_names", "Page names")
_M_FAMILY_MOTION = i18n.msg("components.family_motion", "Page opening and tab strips")
_M_FAMILY_MOTION_DESC = i18n.msg(
    "components.family_motion_desc",
    "Every page opens the same way and every tab strip moves the same way. Both are off "
    "under reduced motion.")
_M_STATE_OPENING = i18n.msg("components.state_opening", "Page opening")
_M_STATE_TAB_STRIP = i18n.msg("components.state_tab_strip", "Tab strip with its sliding thumb")
_M_STATE_TAB_CONTENT = i18n.msg("components.state_tab_content", "What a tab switch animates")
_OPENING_NOTE = i18n.msg(
    "components.sample_opening_note",
    "The header enters first, then the filters and the first blocks, one short step apart: "
    "a fade and a small rise. Lists, tables and the map never animate row by row.")
_TAB_CONTENT_NOTE = i18n.msg(
    "components.sample_tab_content_note",
    "A switch that loads another page replays the opening. A switch that changes the list in "
    "place fades the list once. \u201cLoad more\u201d brings its first new items in the same way.")
_M_FAMILY_NAMES_DESC = i18n.msg(
    "components.family_names_desc",
    "One name per page. The title, the document title, the sidebar and the headings use "
    "the full name; the phone tab bar shows a word of that name, never another word.")
_M_STATE_NAMES = i18n.msg("components.state_names", "Tab bar label and page name")
_M_STATE_SEARCH_STATUS = i18n.msg(
    "components.state_search_status", "Place search: pending, nothing found, failed")
_COL_TAB = i18n.msg("components.sample_col_tab", "Tab bar")
_COL_PAGE = i18n.msg("components.sample_col_page", "Page name")
_SEARCHING = i18n.msg("components.sample_searching", "Searching\u2026")
_NO_PLACE = i18n.msg("components.sample_no_place", "No place found")
_SEARCH_UNAVAILABLE = i18n.msg("components.sample_search_unavailable", "Search unavailable right now")
_VARIANT_LABELS = {
    "primary": i18n.msg("components.variant_primary", "Primary"),
    "secondary": i18n.msg("components.variant_secondary", "Secondary"),
    "ghost": i18n.msg("components.variant_ghost", "Ghost"),
    "danger": i18n.msg("components.variant_danger", "Destructive"),
}


# Family: its anchor slug, title, description, the helpers it renders (dotted
# `module.function` names of the component modules) and the builder returning
# its states.
Family = NamedTuple("Family", [
    ("slug", str), ("title", object), ("description", object), ("helpers", tuple),
    ("build", object)])

class State(NamedTuple):
    label: object
    html: str


def _t(message):
    return i18n.t(message)


def _esc(value):
    return escape_html(value)


# --- Buttons ---------------------------------------------------------------

def _buttons():
    states = []
    for variant in ui_components.BUTTON_VARIANTS:
        states.append(State(
            _VARIANT_LABELS[variant],
            ui_components.button_html(_t(_SAVE if variant != "danger" else _DELETE), variant)))
    states.append(State(
        _DISABLED, ui_components.button_html(
            _t(_SAVE), "primary", attrs=" disabled")
        + ui_components.button_html(_t(_CANCEL), "secondary", attrs=" disabled")))
    states.append(State(
        _M_STATE_LINK,
        ui_components.button_html(_t(_CANCEL), "secondary", href=COMPONENTS_ROUTE)))
    states.append(State(
        _LONG, ui_components.button_html(_t(_LONG_LABEL), "secondary")))
    states.append(State(
        _M_STATE_ICON,
        ui_components.icon_button_html("icon-close", _t(_CLOSE))
        + ui_components.icon_button_html("icon-close", _t(_CLOSE), "danger")))
    states.append(State(
        _M_STATE_ICON_LINK,
        ui_components.icon_link_html("icon-pencil", _t(_RENAME), COMPONENTS_ROUTE)))
    return states


# --- Switches --------------------------------------------------------------

def _switches():
    label = ('<span id="components-switch-label">%s</span> '
             % _esc(_t(_SWITCH_LABEL)))
    on_state = ui_components.quick_switch_state_html(
        "components-switch-on-state", _t(_SWITCH_ON), _t(_SWITCH_OFF), True)
    off_state = ui_components.quick_switch_state_html(
        "components-switch-off-state", _t(_SWITCH_ON), _t(_SWITCH_OFF), False)
    return [
        State(_ON, ui_components.switch_button_html(
            True, ' aria-label="%s"' % _esc(_t(_SWITCH_LABEL)))),
        State(_OFF, ui_components.switch_button_html(
            False, ' aria-label="%s"' % _esc(_t(_SWITCH_LABEL)))),
        State(_DISABLED, ui_components.switch_button_html(
            True, ' aria-label="%s" disabled' % _esc(_t(_SWITCH_LABEL)))
            + ui_components.switch_button_html(
                False, ' aria-label="%s" disabled' % _esc(_t(_SWITCH_LABEL)))),
        State(_M_STATE_QUICK_ON,
              label + on_state + ui_components.quick_switch_html(
                  "/quiet-hours", "/", True, "components-switch-label",
                  "components-switch-on-state")),
        State(_M_STATE_QUICK_OFF,
              label + off_state + ui_components.quick_switch_html(
                  "/quiet-hours", "/", False, "components-switch-label",
                  "components-switch-off-state")),
        State(_M_STATE_FORM_SWITCH,
              ui_components.form_switch_html("components-form-on", "components_on", _t(_QUIET), True)
              + ui_components.form_switch_html("components-form-off", "components_off", _t(_QUIET))),
    ]


# --- Segmented controls ------------------------------------------------------

def _segmented():
    radios = [
        ("components-kind-%s" % key, "components_kind", key, _t(label), _t(label), key == "flight")
        for key, label in (
            ("flight", _KIND_FLIGHT), ("aircraft", _KIND_AIRCRAFT), ("airline", _KIND_AIRLINE))]
    long_radios = [
        ("components-long-%s" % key, "components_long", key, _t(label), _t(label), key == "airline")
        for key, label in (
            ("flight", _KIND_FLIGHT), ("airline", _KIND_AIRLINE_LONG),
            ("aircraft", _KIND_AIRCRAFT))]
    buttons = [
        ("components_theme", key, _t(label), key == "dark", "", "")
        for key, label in (("auto", _ALL), ("light", _DEPARTURES), ("dark", _ARRIVALS))]
    links = [
        ("#components-segmented", "<span>%s</span>" % _esc(_t(label)), key == "departures", "")
        for key, label in (
            ("departures", _DEPARTURES), ("arrivals", _ARRIVALS), ("pairing", _PAIRING),
            ("releases", _RELEASES))]
    chips = [
        ("", _t(_ALL)), ("departing", _t(_DEPARTURES)), ("arriving", _t(_ARRIVALS))]
    return [
        State(_DEFAULT, ui_segmented.segmented_radios_html(radios)),
        State(_LONG, ui_segmented.segmented_radios_html(long_radios)),
        State(_M_STATE_BUTTONS,
              ui_segmented.segmented_buttons_html(
                  'method="post" action="%s" aria-label="%s"' % (
                      COMPONENTS_ROUTE, _esc(_t(_THEME))), buttons)),
        State(_M_STATE_LINKS,
              ui_segmented.segmented_links_html(links, _t(_INDEX_LABEL))),
        State(_M_STATE_CHIPS,
              ui_filter.filter_bar_html(
                  "components-chips-search", _t(_SAMPLE_SEARCH), _t(_SAMPLE_PLACEHOLDER),
                  "%d of %d", 42, 42, _t(_SAMPLE_FILTER_EMPTY), _t(_SAMPLE_FILTER_EMPTY_BODY),
                  chips=chips, chips_legend=_t(_INDEX_LABEL), search_in_bar=False)),
        State(_M_STATE_CHIP_LINKS,
              ui_filter.chip_links_html(
                  [("#components-segmented", _t(label), index == 0)
                   for index, label in enumerate(
                       (_ALL, _PAIRING, _DEPARTURES, _ARRIVALS, _RELEASES, _SAMPLE_PILL))],
                  _t(_INDEX_LABEL))),
    ]


# --- Inputs ------------------------------------------------------------------

def _inputs():
    field = ui_components.text_field_html
    error = ui_modal.field_error_html("components", "name", _t(_SAMPLE_ERROR))
    search = ui_filter.filter_title_search_html(
        "components-title-search", _t(_SAMPLE_SEARCH), _t(_SAMPLE_PLACEHOLDER))
    search_form = ui_filter.filter_title_search_form_html(
        "components-search-form-field", _t(_SAMPLE_SEARCH),
        _t(_SAMPLE_PLACEHOLDER), "components-search-form", COMPONENTS_ROUTE, "q",
        _t(_SAMPLE_VALUE), COMPONENTS_ROUTE)
    return [
        State(_DEFAULT, field(
            "components-name", "name", _t(_SAMPLE_NAME), _t(_SAMPLE_VALUE), _t(_SAMPLE_HELP))),
        State(_LONG, field(
            "components-long", "long", _t(_SAMPLE_NAME), _t(_SAMPLE_LONG_VALUE), _t(_SAMPLE_HELP))),
        State(_ERROR, field(
            "components-error", "error", _t(_SAMPLE_NAME), "", "", error,
            ' aria-invalid="true" aria-describedby="%s"' % _esc(
                ui_modal.error_id("components", "name")))),
        State(_DISABLED, field(
            "components-disabled", "disabled", _t(_SAMPLE_NAME), _t(_SAMPLE_VALUE), "",
            input_attrs=" disabled")),
        State(_M_STATE_NUMBER, field(
            "components-number", "wake", _t(_WAKE), "", "", input_type="number",
            input_attrs=' min="30" max="3600" placeholder="%s"' % _esc(
                _t(_M_SAMPLE_NUMBER_HINT)))),
        State(_M_STATE_SEARCH,
              '<div class="page-header">%s</div>' % search),
        State(_M_STATE_SEARCH_VALUE,
              '<div class="page-header">%s</div>' % search_form),
    ]


# --- Menus and sort -----------------------------------------------------------

def _menus():
    values = ((("newest", _SORT_NEWEST), ("oldest", _SORT_OLDEST), ("airline", _SORT_AIRLINE)))
    closed = ui_filter.sort_menu_html("components_sort", values, "newest", _SORT)
    opened = ui_filter.sort_menu_html(
        "components_sort_open", values, "airline", _SORT).replace(
            "<details ", "<details open ", 1)
    menu = ui_entity_list.row_menu_html(
        _t(_MENU_LABEL), [(_t(_MENU_RENAME), COMPONENTS_ROUTE, False),
                          (_t(_MENU_REMOVE), COMPONENTS_ROUTE, True)])
    return [
        State(_CLOSED, '<div class="components-menu-host">%s</div>' % closed),
        State(_OPEN, '<div class="components-menu-host components-menu-host--open">%s</div>' % opened),
        State(_M_STATE_ROW_MENU,
              '<div class="components-menu-host">%s</div>' % menu),
    ]


# --- Cards, groups and tiles --------------------------------------------------

def _cards():
    rows = (
        ui_groups.row(_t(_SAMPLE_ROW), detail=_t(_SAMPLE_ROW_DETAIL), icon="icon-device",
                      value_html=_esc(_t(_SAMPLE_VALUE_TEXT)), href=COMPONENTS_ROUTE)
        + ui_groups.row(_t(_SAMPLE_ROW), value_html=_esc(_t(_SAMPLE_VALUE_TEXT)))
        + ui_groups.row(
            _t(_LONG_LABEL), detail=_t(_SAMPLE_ROW_DETAIL),
            trailing_html=ui_components.switch_button_html(
                True, ' aria-label="%s"' % _esc(_t(_SWITCH_LABEL)))))
    tiles = "".join(
        ui_components.stat_tile(_t(_SAMPLE_TILE), _esc(_t(body)), status=status)
        for status, body in (
            (None, _SAMPLE_TILE_NEUTRAL), ("ok", _SAMPLE_TILE_OK),
            ("warn", _SAMPLE_TILE_WARN), ("error", _SAMPLE_TILE_ERROR)))
    status_rows = "".join(
        ui_components.status_row(_t(_STATUS_LABEL), _t(_STATUS_VERDICT), _t(_STATUS_DETAIL), state)
        for state in ("ok", "warn", "error"))
    return [
        State(_M_STATE_ROWS,
              ui_groups.group(rows, _t(_SAMPLE_CARD), "components-group-label")),
        State(_M_STATE_PANEL,
              ui_groups.group_panel(
                  "<p class=\"text-body\">%s</p>" % _esc(_t(_SAMPLE_ROW_DETAIL)),
                  _t(_SAMPLE_CARD), "components-panel-label")),
        State(_M_STATE_SECTION_LABEL,
              ui_groups.section_label(_t(_SECTION_HEADING)) + ui_groups.chip_html("icon-device")),
        State(_M_STATE_SECTION_INTRO,
              ui_components.section_intro_html(
                  "components-intro", _t(_SECTION_HEADING), _t(_SECTION_DESCRIPTION))),
        State(_M_STATE_TILES,
              '<div class="components-tiles">%s</div>' % tiles),
        State(_M_STATE_STATUS_ROWS, status_rows),
        State(_M_STATE_HERO,
              ui_groups.hero(_esc(_t(_HERO_LINE)))),
        State(_M_STATE_LINK_CARD,
              ui_components.link_card_html(
                  COMPONENTS_ROUTE, "icon-shield", _t(_SAMPLE_CARD),
                  _t(_SAMPLE_LINK_CARD_SUB))
              + ui_components.link_card_html(
                  COMPONENTS_ROUTE, "icon-shield", _t(_LONG_LABEL),
                  _t(_SAMPLE_LONG_VALUE))),
        State(_M_STATE_LINK_CARD_PLAIN,
              ui_components.link_card_html(COMPONENTS_ROUTE, "icon-device", _t(_SAMPLE_CARD))),
    ]


# --- Lists and tables ----------------------------------------------------------

def _lists():
    dot = ui_components.status_dot
    rows = (
        ui_entity_list.entity_row_html(
            dot("ok", _t(_ONLINE), visually_hide_label=True), _t(_SAMPLE_ENTITY),
            _t(_SAMPLE_ENTITY_META), ui_components.pill_html(_t(_SAMPLE_PILL)),
            ui_entity_list.row_menu_html(
                _t(_MENU_LABEL), [(_t(_MENU_RENAME), COMPONENTS_ROUTE, False)]),
            href=COMPONENTS_ROUTE)
        + ui_entity_list.entity_row_html(
            dot("warn", _t(_STALE), visually_hide_label=True), _t(_SAMPLE_ENTITY_LONG),
            _t(_SAMPLE_ENTITY_META), "", ""))
    table = ui_components.data_table(
        [_t(_COL_AIRLINE), _t(_COL_FLIGHTS), _t(_COL_LAST)],
        [["Air France", "12", "10:42"], ["Transavia France", "7", "09:15"]],
        mono_columns=(1,))
    long_table = ui_components.data_table(
        [_t(_COL_AIRLINE), _t(_COL_FLIGHTS), _t(_COL_LAST)],
        [[_t(_SAMPLE_ENTITY_LONG), "1204", "10:42"]], mono_columns=(1,))
    return [
        State(_DEFAULT, ui_entity_list.entity_list_html(
            rows, ui_entity_list.count_line_html("2 frames"))),
        State(_M_STATE_TABLE, table),
        State(_M_STATE_TABLE_LONG, long_table),
        State(_M_STATE_TABLE_EMPTY,
              ui_components.data_table([_t(_COL_AIRLINE)], [])),
        State(_M_STATE_SEARCH_STATUS, _search_status_html()),
    ]


def _search_status_html():
    """The last row of the Location search's suggestion list, in its three
    states, in the markup the page script builds."""
    def row(kind, spinner, message):
        return (
            '<li class="place-results__status text-label" role="presentation" data-status="%s">'
            '%s%s</li>') % (
                kind, '<span class="place-loading__spinner" aria-hidden="true"></span>'
                if spinner else "", _esc(_t(message)))
    return '<ul class="place-results__list">%s%s%s</ul>' % (
        row("searching", True, _SEARCHING), row("none", False, _NO_PLACE),
        row("failed", False, _SEARCH_UNAVAILABLE))


def _motion():
    """The shared page opening and the shared tab strip, as the pages use them."""
    links = [
        ("#components-motion", "<span>%s</span>" % _esc(_t(label)), index == 0, "")
        for index, label in enumerate((_DEPARTURES, _ARRIVALS, _RELEASES))]
    return [
        State(_M_STATE_OPENING, '<p class="text-body">%s</p>' % _esc(_t(_OPENING_NOTE))),
        State(_M_STATE_TAB_STRIP, ui_segmented.segmented_links_html(
            links, _t(_INDEX_LABEL), nav_attrs=' data-tabs="components-motion"')),
        State(_M_STATE_TAB_CONTENT, '<p class="text-body">%s</p>' % _esc(_t(_TAB_CONTENT_NOTE))),
    ]


def _names():
    """Every personal and frame-tool page with the label its phone tab shows
    (the full name when it fits) beside its page name, in the current language."""
    rows = []
    for _group, entries in ui_base.NAV_GROUPS:
        for route, label in entries:
            short = ui_base.NAV_SHORT_LABELS.get(ui_base.nav_slug(route), label)
            rows.append([_t(short), _t(label)])
    return [State(_M_STATE_NAMES, ui_components.data_table(
        [_t(_COL_TAB), _t(_COL_PAGE)], rows))]


# --- Badges and pills --------------------------------------------------------------

def _badges():
    dots = "".join(
        '<p class="text-body">%s</p>' % ui_components.status_dot(state, _t(label))
        for state, label in (("ok", _ONLINE), ("warn", _STALE), ("error", _OFFLINE)))
    return [
        State(_M_STATE_PILL,
              ui_components.pill_html(_t(_SAMPLE_PILL))),
        State(_M_STATE_DOTS, dots),
        State(_M_STATE_CHARGING,
              ui_components.battery_charging_pill_html()),
    ]


# --- Messages -----------------------------------------------------------------------

def _messages():
    toast = ui_components.toast_html
    tones = "".join(
        toast(_t(_SAMPLE_TOAST_TITLE), _t(_SAMPLE_TOAST_DETAIL), tone=tone, role="", docked=True)
        for tone in ui_components.TOAST_TONES)
    link_action = toast(
        _t(_SAMPLE_TOAST_TITLE), _t(_SAMPLE_TOAST_DETAIL), role="", docked=True,
        action_html=ui_components.toast_link_action_html(COMPONENTS_ROUTE, _t(_SAMPLE_ACTION)))
    post_action = toast(
        _t(_SAMPLE_TOAST_TITLE), _t(_SAMPLE_TOAST_DETAIL), role="", docked=True,
        action_html=ui_components.toast_post_action_html(
            COMPONENTS_ROUTE, (("components", "1"),), _t(_SAMPLE_ACTION)))
    # What a server-answered list shows when its request gets no answer: the
    # toast its hidden template holds, shown docked here.
    offline_title, offline_detail = ui_components.split_toast_message(
        _t(ui_filter.LIST_OFFLINE_TEXT))
    offline = toast(
        offline_title, offline_detail, tone=ui_components.TOAST_TONE_ERROR, role="", docked=True)
    return [
        State(_M_STATE_TOASTS, tones),
        State(_M_STATE_TOAST_ACTIONS, link_action + post_action),
        State(_M_STATE_TOAST_OFFLINE, offline + ui_filter.list_offline_template_html()),
        State(_M_STATE_BANNER_ERROR,
              ui_components.anomaly_banner(_t(_BANNER))),
        State(_M_STATE_BANNER_WARN,
              ui_components.anomaly_banner(_t(_BANNER), "warn")),
    ]


# --- Empty states ---------------------------------------------------------------------

def _empty_states():
    return [
        State(_EMPTY, ui_components.empty_state(
            _t(_SAMPLE_EMPTY_HEADING), _t(_SAMPLE_EMPTY_BODY))),
        State(_M_STATE_EMPTY_COMPACT,
              ui_components.empty_state(
                  _t(_SAMPLE_EMPTY_HEADING), _t(_SAMPLE_EMPTY_BODY), compact=True)),
        State(_M_STATE_EMPTY_SEARCH,
              ui_filter.filter_empty_html(
                  _t(_SAMPLE_FILTER_EMPTY), _t(_SAMPLE_FILTER_EMPTY_BODY),
                  ui_components.button_html(
                      _t(ui_filter.FILTER_CLEAR_TEXT), "secondary", href=COMPONENTS_ROUTE),
                  "")),
    ]


# --- Dialogs and the save bar -----------------------------------------------------------

def _dialogs():
    field = ui_components.text_field_html(
        "components-dialog-name", "name", _t(_SAMPLE_NAME), _t(_SAMPLE_VALUE), _t(_SAMPLE_HELP))
    dialog = ui_modal.dialog_html(
        "components-dialog", _t(_SAMPLE_DIALOG), COMPONENTS_ROUTE, ui_components.csrf_field(),
        field, _t(_SAVE), _t(_CANCEL), COMPONENTS_ROUTE)
    confirm = ui_modal.dialog_html(
        "components-confirm", _t(_SAMPLE_CONFIRM), COMPONENTS_ROUTE, ui_components.csrf_field(),
        '<p class="text-body">%s</p>' % _esc(_t(_SAMPLE_CONFIRM_BODY)), _t(_DELETE), _t(_CANCEL),
        COMPONENTS_ROUTE, destructive=True, confirm_only=True)
    sections = ui_modal.sections_dialog_html(
        "components-sections", _t(_SAMPLE_DIALOG), "", "<p class=\"text-body\">%s</p>" % _esc(
            _t(_SAMPLE_CONFIRM_BODY)), _t(_CLOSE), COMPONENTS_ROUTE)
    triggers = (
        ui_modal.trigger_html(
            "components-dialog", _esc(_t(_OPEN_DIALOG)), "btn btn--secondary")
        + ui_modal.trigger_html(
            "components-confirm", _esc(_t(_OPEN_CONFIRM)), "btn btn--danger")
        + ui_modal.trigger_html(
            "components-sections", _esc(_t(_SAMPLE_DIALOG)), "btn btn--ghost"))
    bar = ui_save_bar.save_bar_html(
        "components-bar-form", cancel_href=COMPONENTS_ROUTE, title=_t(_UNSAVED))
    inline_bar = ui_save_bar.save_bar_html(
        "components-bar-form", cancel_href=COMPONENTS_ROUTE, title=_t(_UNSAVED), inline=True)
    revealed_bar = ui_save_bar.save_bar_html(
        "components-page-bar-form", cancel_href=COMPONENTS_ROUTE, title=_t(_UNSAVED),
        reveal_on_change=True)
    revealed = (
        '<form id="components-page-bar-form" method="post" action="%s" class="components-page-bar">'
        '%s%s</form><div class="components-save-bar">%s</div>' % (
            COMPONENTS_ROUTE, ui_components.csrf_field(),
            ui_components.text_field_html(
                "components-page-bar-field", "sample", _t(_SAMPLE_VALUE), "", "",
                "", ' autocomplete="off"'),
            revealed_bar))
    return [
        State(_M_STATE_SAVE_BAR_REVEALED, revealed),
        State(_M_STATE_DIALOGS,
              '<div class="components-triggers">%s</div>%s%s%s' % (
                  triggers, dialog, confirm, sections)),
        State(_M_STATE_SAVE_BAR,
              '<div class="components-save-bar">%s</div>' % bar),
        State(_M_STATE_SAVE_BAR_INLINE,
              '<div class="components-save-bar components-save-bar--inline">'
              '<p class="text-body">%s</p>%s</div>' % (_esc(_t(_SAMPLE_VALUE)), inline_bar)),
    ]


# --- Page header --------------------------------------------------------------------------

def _headers():
    return [
        State(_DEFAULT, ui_components.page_header(_t(_HEADER_TITLE)).replace(
            ui_components.FLASH_SLOT_MARKER, "")),
        State(_M_STATE_HEADER_FULL,
              ui_components.page_header(
                  _t(_HEADER_TITLE), _t(_HEADER_PURPOSE),
                  action_html=ui_components.button_html(_t(_SAVE), "primary")).replace(
                      ui_components.FLASH_SLOT_MARKER, "")),
        State(_M_STATE_TITLE_ACTION,
              ui_components.title_action_html(
                  _t(_SAMPLE_VALUE),
                  ui_components.icon_link_html(
                      "icon-pencil", _t(_RENAME), COMPONENTS_ROUTE))),
    ]


CATALOGUE = (
    Family("headers", _M_FAMILY_HEADERS,
           _M_FAMILY_HEADERS_DESC,
           ("ui_components.page_header", "ui_components.title_action_html"), _headers),
    Family("buttons", _M_FAMILY_BUTTONS,
           _M_FAMILY_BUTTONS_DESC,
           ("ui_components.button_html", "ui_components.icon_button_html",
            "ui_components.icon_link_html"), _buttons),
    Family("switches", _M_FAMILY_SWITCHES,
           _M_FAMILY_SWITCHES_DESC,
           ("ui_components.switch_button_html", "ui_components.quick_switch_html",
            "ui_components.quick_switch_state_html", "ui_components.form_switch_html"), _switches),
    Family("segmented", _M_FAMILY_SEGMENTED,
           _M_FAMILY_SEGMENTED_DESC,
           ("ui_segmented.segmented_radios_html", "ui_segmented.segmented_buttons_html",
            "ui_segmented.segmented_links_html", "ui_filter.filter_bar_html",
            "ui_filter.chip_links_html"), _segmented),
    Family("inputs", _M_FAMILY_INPUTS,
           _M_FAMILY_INPUTS_DESC,
           ("ui_components.text_field_html", "ui_modal.field_error_html",
            "ui_filter.filter_title_search_html", "ui_filter.filter_title_search_form_html"), _inputs),
    Family("menus", _M_FAMILY_MENUS,
           _M_FAMILY_MENUS_DESC,
           ("ui_filter.sort_menu_html", "ui_entity_list.row_menu_html"), _menus),
    Family("cards", _M_FAMILY_CARDS,
           _M_FAMILY_CARDS_DESC,
           ("ui_groups.group", "ui_groups.group_panel", "ui_groups.row", "ui_groups.section_label",
            "ui_groups.chip_html", "ui_groups.hero", "ui_components.section_intro_html",
            "ui_components.stat_tile", "ui_components.status_row",
            "ui_components.link_card_html"), _cards),
    Family("lists", _M_FAMILY_LISTS,
           _M_FAMILY_LISTS_DESC,
           ("ui_entity_list.entity_list_html", "ui_entity_list.count_line_html",
            "ui_entity_list.entity_row_html", "ui_components.data_table"), _lists),
    Family("badges", _M_FAMILY_BADGES,
           _M_FAMILY_BADGES_DESC,
           ("ui_components.pill_html", "ui_components.status_dot",
            "ui_components.battery_charging_pill_html"), _badges),
    Family("messages", _M_FAMILY_MESSAGES,
           _M_FAMILY_MESSAGES_DESC,
           ("ui_components.toast_html", "ui_components.toast_link_action_html",
            "ui_components.toast_post_action_html", "ui_filter.list_offline_template_html",
            "ui_components.anomaly_banner"), _messages),
    Family("empty", _M_FAMILY_EMPTY,
           _M_FAMILY_EMPTY_DESC,
           ("ui_components.empty_state", "ui_filter.filter_empty_html"), _empty_states),
    Family("dialogs", _M_FAMILY_DIALOGS,
           _M_FAMILY_DIALOGS_DESC,
           ("ui_modal.dialog_html", "ui_modal.sections_dialog_html", "ui_modal.trigger_html",
            "ui_save_bar.save_bar_html"), _dialogs),
    Family("motion", _M_FAMILY_MOTION, _M_FAMILY_MOTION_DESC, (), _motion),
    Family("names", _M_FAMILY_NAMES, _M_FAMILY_NAMES_DESC, (), _names),
)

# Public helpers of the component modules that are not standalone components,
# with the reason: the catalogue test requires every other public helper to be
# listed in a family above.
EXEMPT = {
    "ui_components.card_status_class": "returns a CSS class name for a status, no markup",
    "ui_components.csrf_field": "a hidden form field, used inside the dialogs above",
    "ui_components.csrf_query": "the same anti-forgery token carried in an upload form action URL; no markup of its own",
    "ui_components.flash_banner": "floats over the page by design; its toast is shown docked",
    "ui_components.frame_strip_html": "needs a live frame context; built from the switches above",
    "ui_components.split_toast_message": "a text splitter for toast copy",
    "ui_components.toast_dismiss_button_html": "a part of toast_html",
    "ui_components.toast_dismiss_html": "a part of toast_html",
    "ui_components.toast_icon_html": "a part of toast_html",
    "ui_components.toast_text_html": "a part of toast_html",
    "ui_modal.error_id": "an id builder for field_error_html",
    "ui_modal.validated_slug": "a slug check used by the dialog helpers",
}

COMPONENT_MODULES = (
    "ui_components", "ui_entity_list", "ui_filter", "ui_groups", "ui_modal", "ui_save_bar",
    "ui_segmented")


def catalogued_helpers():
    """Every dotted helper name the catalogue renders."""
    return {helper for family in CATALOGUE for helper in family.helpers}


def _state_html(state):
    return (
        '<div class="components-state"><p class="components-state__label text-label">%s</p>'
        '<div class="components-state__sample">%s</div></div>'
    ) % (_esc(_t(state.label)), state.html)


def _family_html(family):
    helpers = " ".join("<code>%s</code>" % _esc(name) for name in family.helpers)
    return (
        '<section class="components-family" id="components-%s" aria-labelledby="components-%s-title">'
        '<h2 class="text-heading" id="components-%s-title">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<p class="components-helpers text-label"><span>%s</span> %s</p>%s'
        '<p class="components-family__top"><a class="text-link" href="#components-index">%s</a></p>'
        "</section>"
    ) % (
        family.slug, family.slug, family.slug, _esc(_t(family.title)),
        _esc(_t(family.description)), _esc(_t(_HELPERS_LABEL)), helpers,
        "".join(_state_html(state) for state in family.build()), _esc(_t(_TO_INDEX_LABEL)))


def render():
    """The page body: an index of anchors and one section per family."""
    index = "".join(
        '<li><a class="components-index__link" href="#components-%s">%s</a></li>' % (
            family.slug, _esc(_t(family.title)))
        for family in CATALOGUE)
    return (
        '<nav class="components-index" id="components-index" aria-label="%s"><ul>%s</ul></nav>' % (
            _esc(_t(_INDEX_LABEL)), index)
        + "".join(_family_html(family) for family in CATALOGUE))
