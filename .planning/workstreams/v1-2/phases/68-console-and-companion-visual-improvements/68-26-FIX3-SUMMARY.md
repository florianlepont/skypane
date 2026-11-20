# Phase 68 Plan 26 FIX3: System in the phone bar, Audit log in More

Owner request (2026-11-19): "System in the bar, Audit in the More menu".

## Change

- `companion/ui_nav.py`: `_console_bar()` is table-driven from `_CONSOLE_BAR_KEYS =
  ("fleet", "users", "editor", "system")`; the More sheet entries are Account then the
  Audit log, followed by the space switch as before. Fleet keeps the severity dot.
- System uses its existing full label ("System" / "Système", `nav.system`); no short
  label was needed. The now-unused `nav.audit_short` message (EN "Audit", FR "Journal")
  was removed from `ui_nav.py`, `i18n_fr/nav.py` and the cognate allowlist in
  `test_i18n.py`, so no orphan id remains.
- Behaviour unchanged: System is current on `/fleet?view=system` and Fleet is not; the
  Audit log row is current on its page and More is then selected; admin-only access is
  untouched; the desktop sidebar order stays Fleet, Users, Editor, Audit log, System.

## Tests updated (no loosening)

Tab-order and sheet-content tests in `test_console_shell`, `test_nav_spaces`,
`test_nav_personal_console`, `test_update_page`, `test_console_fleet_view` (System is a
bar cell and marked there, absent from the sheet), `test_browser_more_sheet`,
`test_browser_tab_bar_roles`, `test_browser_overhaul_steps` (A6 now opens More, then the
Audit log row). New `test_the_console_bar_fits_its_five_cells_with_system_as_the_fourth`
(320/360/390 px, EN and FR: labels unclipped, inside their cell, not touching).
`test_sign_in_surfaces` shell digest updated; per-page comparison against HEAD showed
only the console pages (health, device, update, with a device config) changed, every
personal page is byte-identical. `companion/testdata/render_baseline.json` regenerated once.

## Design-system divergences

- 68-MOCKUP-frame-list.html (and the shell-audit mock) show the phone bar as Fleet, Team,
  Editor, Journal, More (FR: Flotte, Équipe, Éditeur, Journal, Plus) with the sidebar
  Fleet, Users, Editor, Audit log and no System entry. The owner request supersedes the
  bar: System replaces Audit in the bar and Audit moves to More. The mock has no System
  sidebar entry; the shipped sidebar keeps System after Audit log, as before this fix.
- The More sheet's Audit log row uses the full page name ("Audit log" / "Journal
  d’audit"), like the other sheet rows, not a short bar label.
- Mock labels "Team" for Users are the existing short bar label ("Users"/"Équipe") and
  were not touched here.

## Captures

16 full-screen captures (bar and open More sheet; EN and FR; light and dark; 390 and
320 px) in `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/fix3/`.
