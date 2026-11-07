# Phase 61 Plan 68: Personalisation selector and list views, Flights title-row search and Load more Summary

Personalisation navigation is one segmented control that fits 360px in English and French; Special looks and Calendar are one glass group of rows with a dashed add row; the Flights search opens inside the 44px title row without moving the list, and a Load more link appends the next 50 flights with or without scripts.

**Requirements:** D42 (P04, P06), audit findings F03, F04, F23, F26, F29.

## What changed

- **P04 / F04, F26, F29** (`static/style.css`, `static/theme-preview.js`, `pages/personalisation_cards.py`, `settings/rules.py`, `settings/calendar.py`):
  - `.personalisation-nav` is a track (same recipe as the Flights direction chips) of four 44px link segments with no sideways scroll; labels use the caption size on a phone, glyphs are hidden, a label would ellipsize rather than overflow. Markup, classes, `aria-label`, `aria-current` and the plain links are unchanged; the sliding thumb now sits 3px inside its segment.
  - Special looks and Calendar views lose the card chrome: the section title stays for assistive technology and the save bar; the rows are one glass group (`ul.special-list`), the "New special look" disclosure is a dashed add row under it (a separate `ul.special-list--add`), and while no calendar is connected the button reads "Connect a calendar" / "Connecter un calendrier" as a dashed add row (connected: still "Choose calendar"). All forms, dialogs, endpoints and field names are untouched.
  - French "Special looks" is now "Looks spéciaux" (was "Allures spéciales") as in the mockup.
- **P06 / F03, F23** (`ui_filter.py`, `layout.py`, `pages/history_page.py`, `page_context.py`, `static/style.css`):
  - The Flights search field moves into the page header (`filter_title_search_html`, the chip bar is built with `search_in_bar=False`). On a phone with scripts it is a 44px magnifier at the title row's right edge that opens over the row in place; the title keeps its box, so the direction control and list tops are identical before, while open, while typing and after closing (measured at 360 and 390, EN and FR). From 960px it is always open at the right of the title row. Without a script it is the plain field beside the title.
  - `?more=N` (plain link, clamped 0..19, bad values mean 0) shows the newest (N+1)*50 flights; `history_rows_page` fetches one extra row to decide whether a "N flights shown" line and the Load more link appear. The link returns to the first new row (`#flights-new`). `history_db` and the live frame are untouched.

## Tests

- New: `companion/test_browser_personalisation_selector.py` (fits 360 in EN/FR, both themes, every view, labelled nav and keyboard operation, group and dashed add rows, Connect a calendar opens the sheet, desktop), `companion/test_browser_flights_search_more.py` (no layout shift at 360/390 EN/FR, Load more appends, works without scripts, absent when everything fits, bad `?more=`).
- Updated in place (subject changed): `test_calendar_sheet.py`, `test_config_page_03.py`, `test_config_page_04.py`, `test_config_page_05.py`, `test_display_looks.py`, `test_personalisation_page.py` (FR label, card class, Connect label), `test_browser_flights_cards.py` (desktop search in the title row), `test_browser_segment_centring.py` (search in the title row), `test_browser_personalisation.py` (nav fits instead of scrolling, thumb inset), `test_browser_surfaces.py` (nav track is a glass track), `test_browser_overhaul_sweep.py` (card-less list views). Render baseline regenerated.

## Deviations from Plan

- **No switches in the list rows.** The mockup shows an on/off switch per row, but no enable/disable endpoint or field exists and the brief keeps endpoints and fields as they are; rows keep their Remove link (44px). A later plan can add it with a backend field.
- The add row keeps the existing wording "New special look" / "Nouvelle allure spéciale" (tests pin it); only the Calendar add row uses the mockup's "Connect a calendar".
- Load more is a full page load (link), not an in-page append; the filter text and chip counts cover the loaded rows only.
- The shown line says "N flights shown" (no total), to avoid an extra count query.

## Screenshots

`scratchpad/shots68/` (before_*, after_*, flights_rest_*, flights_search_*).

## Self-Check: PASSED
