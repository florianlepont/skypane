---
quick_id: 261004-asp
subsystem: companion
tags: [airlines, names, focus, i18n]
completed: 2026-10-04
---

# Quick 261004-asp: Airline sheet polish

## Focus

- The sheet's name field is never `autofocus`ed. For a sheet open,
  `panel-lookup.js` marks the dialog heading (`tabindex="-1"`, no ring) as
  `autofocus` before `showModal()`, so the phone keyboard never rises; the
  Close button is the fallback when the heading is empty.
- A refused rename (empty, unusable, too long, reserved, taken) reopens the
  sheet with the name field focused: the no-script copy autofocuses it, and
  the script reads `data-sheet-focus-name` from that copy.
- Other dialogs (resolve a flight, upload artwork, delete) keep the browser's
  default placement; the resolve name field keeps its own `autofocus`.

## Collisions

`name_overrides.set_names()` refuses (`SET_NAME_TAKEN`, flash
`airline_rename_taken`, error tone) a name whose `normalise_airline_key`
equals another curated airline's name, or the override of a prefix outside the
airline's own. The check runs under the registry write lock, so a hand-made
POST cannot skip it. An airline's own built-in name stays the reset; re-saving
its own override is allowed. The name field no longer has a datalist.
