---
quick_id: 261005-hrd
type: quick
autonomous: true
branch: claude/health-resolve-dialog
---

# 261005-hrd: Health's Resolve opens the shared resolve dialog in place

## Objective

Owner request: a click on "Résoudre" in Health's unidentified-airlines table should open a
dedicated pop-up rather than navigate to the Airlines page and show a temporary frame.

## Design

- Each Resolve link on Health (table row and phone card) stays a real
  `<a href="/airlines?resolve=<prefix>">` and gains the full `data-view-panel-*` trigger
  vocabulary of an Airlines gap card plus `data-view-panel-return="health"`. With script,
  `panel-lookup.js` opens the same shared `<dialog>` in place; without, the link works as before.
- Health emits the dialog once (only when the table has rows or a step-B trigger) and loads
  `panel-lookup.js`.
- Return target: the dialog's name form carries a hidden `return` field filled from the trigger;
  the artwork step carries `?return=health` on its upload action. Both go through
  `airlines_page.return_route()`, an allow-list of one name (`health`); anything else means
  Airlines, so Airlines' own flow is unchanged and nothing is an open redirect.
- After a saved name with no artwork yet the server redirects to `/health?resolve=<prefix>`;
  Health renders a hidden step-B trigger (only for a prefix with an active manual entry still
  lacking artwork) and the existing `?resolve=` auto-open reopens the dialog on step B.
  A refusal redirects the same way and reopens step A with the field focused. Unknown values
  render nothing.
- Health's table no longer lists a prefix that already has a manual entry, so a resolved row
  disappears at once instead of waiting for the next poll to prune the registry.

## Tasks

1. `airlines_page`: return allow-list, trigger attribute builders, step-B trigger, shared dialog
   with optional return field.
2. `post_actions`: resolve and upload handlers redirect to the allow-listed return page.
3. `health_sections`/`health_page`/`app`: triggers on both Resolve links, dialog, script, table
   filter.
4. `panel-lookup.js`: copy the trigger's return target into the name form.
5. Tests: served HTML, routes, Playwright at 390 and 1280 (EN/FR, light/dark, no-JS).
