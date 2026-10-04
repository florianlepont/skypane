---
quick_id: 261004-asp
type: quick
autonomous: true
branch: claude/airline-sheet-polish
---

# 261004-asp: Airline sheet polish

## Objective

1. Opening the airline sheet must not focus the name field (no phone keyboard
   when only the artwork is wanted); a refused rename reopens it with the name
   field focused.
2. Refuse renaming an airline onto a name another airline already carries.

## Tasks

1. Focus: heading (tabindex -1) takes the dialog's initial focus for the sheet;
   name field only after a refusal; other dialogs untouched.
2. Registry-level collision check in `name_overrides.set_names()` plus flash
   (EN/FR) and route mapping; drop the name field's datalist.
3. Tests (server, routes, served HTML, browser), render baseline, full suite
   and gates.
