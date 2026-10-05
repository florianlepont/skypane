---
quick_id: 261006-dat
type: quick
autonomous: true
branch: claude/drop-airline-types-js
---

# 261006-dat: Drop the dead airline-types.js companion script

## Objective

261006-alr replaced the Airlines carousel with a list and a per-type switcher handled by
`panel-lookup.js`, and left `companion/static/airline-types.js` in place. Remove it.

## Tasks

1. Verify nothing depends on it: no markup, script or stylesheet references `data-airline-types`,
   `data-airline-type`, `data-airline-type-dot`, `data-airline-types-ready` or
   `.airline-card__track`; the script defines no global.
2. Remove the file, its static route and path (`static_files.py`), the `AIRLINE_TYPES_SCRIPT_SRC`
   constant (`ui_base.py`, `ui_shell.py`, `layout.py`), the `AIRLINE_TYPES_SCRIPT_ROUTE` alias
   (`app.py`), its entry in the Airlines page script set, and its entry in the render snapshot
   route list.
3. Update the script-count test (17 -> 16 non-global shell scripts).
4. Regenerate the render baseline and check that only the script tag is gone.
