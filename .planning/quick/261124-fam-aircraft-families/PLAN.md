# Quick 261124-fam: aircraft families and the "Other" slot

Goal: every aircraft type seen can receive an illustration in the airline editor.

Owner decisions (2026-11-24): FAMILIES.md tiers 1 to 3 (17 new families) plus one catch-all
"other" slot; tier 4 and every unmapped code fall into "other"; ATR 42 stays with ATR 72; 737 MAX/NG
and A320/A321 stay merged; helicopters one slot; Embraer E2 stays in `embraer`; business jets three
slots (falcon, bizjetlarge, bizjet); light GA, gliders, military and rare types go to "other".
Source table: `FAMILIES.md` (fixes: BE9L -> `kingair`, B190 -> `beechcraft1900d`, E135/E145/E45X/E35L
-> `erj145`).

Tasks
1. `server/plane/illustrations.py`: `SHAPE_SLUGS` (7 + 17 + `other`), family code table, `slot_slug`,
   other-slot fallback in `select_illustration` and `type_artwork_keys`.
2. `companion/pages/airline_table.py`, `airline_families.py`: one "Other" row per airline, always with
   an upload control; EN/FR family labels.
3. Labels for every newly mapped code (`render/text.py`).
4. Placeholder `generic-<slug>.png` for every new family.
5. Tests and render baseline.
