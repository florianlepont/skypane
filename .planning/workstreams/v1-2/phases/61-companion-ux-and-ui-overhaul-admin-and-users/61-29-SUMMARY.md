---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 29
subsystem: companion
tags: [personalisation, special-looks, calendar, confirm-dialog, empty-states]
requires: [61-28]
provides: [Special looks card with Remove confirm dialog, Calendar card with status line and Choose calendar, compact empty states]
key-files:
  created:
    - companion/test_personalisation_special_looks.py
    - companion/test_browser_personalisation_cards.py
  modified:
    - companion/settings/rules.py
    - companion/settings/calendar.py
    - companion/pages/personalisation_cards.py
    - companion/pages/config_page.py
    - companion/i18n_fr/rules.py
    - companion/i18n_fr/calendar_group.py
    - companion/i18n_fr/display.py
    - companion/i18n_fr/look.py
    - companion/static/style.css
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-04
---

# Phase 61 Plan 29: Special looks and Calendar cards

Remove on a special look now confirms in a named-dismiss dialog, "+ New special look" is the card's primary action, and the Calendar card reads as one status line with a single "Choose calendar" button. Three commits (e1c0e60, 6e21878, e8632c2).

## What changed

- **Special looks** (`settings/rules.py`): each rule row keeps "kind tag, key, look sentence" and ends with a 44px Remove hash link (`data-modal-open`) opening a per-rule `ui_modal` dialog "Remove this special look?" (FR "Supprimer ce look spécial ?"). Primary destructive "Remove special look" posts to the unchanged delete route with the page's csrf token; the dismiss "Keep special look" / "Garder le look spécial" carries `autofocus` (confirm-only dialog). Dialog ids are `remove-look-<kind>-<10 hex of sha256(value)>` through `ui_modal.validated_slug`; text and action are escaped, and a row whose kind or value does not survive the colour-rules normaliser is not rendered. The old inline `data-confirm` delete form is gone; `confirm-submit.js` stays because the Device page and the update page still use it.
- **Add**: the add form, its fields and route are untouched. Its disclosure summary now reads "New special look" (`look.new_special_look`, reusing the existing string; the old "Add a special look" id and FR entry were removed) and is styled as the card's accent primary action while closed.
- **Empty state**: with no rules the shared `empty_state(compact=True)` shows "No special looks yet" and "Create one when a particular airline or plane should look different." (EN/FR), above the add action.
- **Calendar** (`settings/calendar.py`): the status row's title is now one line "Flights in your calendar: on, NAME" (or "off"), followed by the verdict pill (omitted when nothing is connected) and the unchanged detail line (flight count, last read, errors, drift). The one button reads "Choose calendar" / "Choisir un calendrier" (primary while nothing is connected) and opens the same sheet (same routes, focus, Esc, no-script address, URL gate messages, disconnect confirmation). With no calendar connected the compact empty state "No calendar connected" with the existing lead sentence shows above the row. The status block now leads the Calendar row; the look-of-calendar-flights row follows under a hairline and is retitled "Look of calendar flights" (the old title duplicated the status line). On a phone (< 700 px) the button spans the row under the text because the longer label left too little width beside it.
- **Strings**: new EN/FR ids under `rules.*` and `display.*`; removed now-unused `calendar_group.manage`, `calendar_group.no_calendar`, `look.add_a_special_look`, `rules.remove_this_rule`.

## Tests

- New `test_personalisation_special_looks.py` (8): dialog structure, named dismiss with autofocus, French strings, one slug id per rule, csrf-less POST refused, delete and idempotent second delete, rule count and primary action, EN/FR compact empty states, hostile stored rule not rendered.
- New `test_browser_personalisation_cards.py` (13, Chromium, not skipped): at 360 and 1280 px, EN/FR, light/dark: no overflow, Remove / New special look / Choose calendar at least 44x44 and owning their centre; dialog opens on Keep special look (waited for), Tab stays inside, Esc closes and focus returns to Remove; Keep changes nothing; Remove special look deletes the rule and shows the "Rule deleted" notice; with scripts blocked the hash link shows the dialog and its POST removes the rule.
- `test_personalisation_page.py`: R22 control-name and label check, both languages, administrator and user, plus card order.
- Moved in place (subject changed): `test_config_page_03/04`, `test_display_looks`, `test_calendar_sheet`, `test_browser_calendar_row` (phone: full-width button under the text; desktop: unchanged beside the text), `test_browser_calendar_sheet` docstrings.
- `render_baseline.json` moved for the 8 Display entries only; sign-in digests did not move.
- Stress: new and changed browser files run 4 times in parallel (61 passed each).

## Decisions

- Edit: no edit route exists and no row offered a way to change a rule's look, so Remove then "+ New special look" (adding an existing key replaces its look) is the path.
- The status "on" means a link is saved and honoured (any state except none and ignored).

## Deviations from Plan

1. **Four cards, not five (R22).** The plan and UI-SPEC list a Refresh card; owner decision D23 (ledger R2-20, applied in 61-28) made the wake interval administrator-only on the Console Device page, so Personalisation has Look, Special looks, Calendar, Screen. R22 is asserted for that order, with no place, runway, time zone, quiet-hours or refresh control.
2. **Card titles** keep the existing serif settings-card style (recorded in 61-28).
3. **Empty-state duplication**: the card's "Current: ..." line and the compact empty state both say "No special looks yet" / "No calendar connected", as the spec lists both.
4. **Calendar look row retitled** and moved under the status line; the plan said to keep it, but its title repeated the new status line.

## Known Stubs

None.

## Gates

ruff, mypy (29 modules), comment-history, function size (931, none over 80), Phase 47 freeze: clean. Full companion + test-support + stub-server run (`-n auto --no-cov`) after the last code commit: 7289 passed, 4 skipped (root-only permission-bit tests), 0 failed.

## Self-Check: PASSED
