# Phase 68: owner walk-through of the deployed console and companion

Rules: a remark comes only from the owner's own report, one per row, with a screenshot (file name or "to attach"). Columns of context: role (A = administrator, U = user), language (EN/FR), width (desktop / phone). Nothing is added by Claude. Each remark gets a value (high / medium / low) when the owner sorts the list.

## Pages to walk (proposed order)

User pages (bottom tab bar): 1 Home, 2 Flights (history), 3 Airlines, 4 Style (layout, looks, theme), 5 Location, 6 More sheet (account, language, theme, sign out).
Frame pages: 7 Frame page (health, battery, detection, quiet hours), 8 Update / device and version, 9 Pair a frame.
Account and public: 10 Account, 11 Sign-in, 12 Credits, 13 Offline / error pages (403, 404, expired session).
Console (administrator): 14 Fleet, 15 Users (and invite), 16 Editor (airlines), 17 Locations, 18 Audit, 19 Console More.

## Remarks

| # | Page | Role / lang / width | Remark | Screenshot | Value |
|---|------|---------------------|--------|------------|-------|
| 1-4 | carried from Phase 64 | A, EN/FR | See 68-CONTEXT.md D-04 to D-07 | on record in Phase 64 | high |

## Owner walk-through of 2026-11-17/18 (guided questions, 78 answered: 38 OK, 42 with a remark, 1 not applicable)

Source: the owner's answers in the walk-through page (one question per screen, local phone screenshots of the test companion as visuals). Remarks translated from French. "All configs" means the owner left role, language, width and theme unselected or selected all. Screenshots: local test captures only; the owner's own screenshots are not attached.

| # | Page | Remark (owner) | Kind |
|---|------|----------------|------|
| R01 | Home | On phone the "i" refresh icon and the rename pencil are badly placed against their text | visual |
| R02 | Home | Recent flights do not show the flight preview ("refactoring already planned") | behaviour, outside list |
| R03 | Flights | Too much information per row; drop the "departing / arriving" wording. Desktop looks dull next to phone | visual |
| R04 | Airlines | Rarity status hardly visible; navigation items are in a different order on desktop and phone | visual |
| R05 | Airlines | Detail sheet forces scrolling on both; the "Close" button has a heavy black rectangle as if selected | visual |
| R06 | Style | Leave dialog: one status too many, the effect of the two buttons is unclear; button sizes differ on desktop | visual |
| R07 | Location | After the locate button a "position found" text appears; remove it | visual |
| R08 | Location | Dark mode: the white runway line is barely visible because the map stays light (dark map?) | visual |
| R09 | Location | Action buttons are big and badly integrated; icons only, same space | visual |
| R10 | More sheet | "Yes in the web app, not in Safari?" (blur / sheet in Safari to check) | to check |
| R11 | Frame page | Phone: toggles are annoying, information should be more direct, State / Settings / Access all need rework; desktop: whole page and its navigation need rework | visual |
| R12 | Frame page | "Back to Fleet" does not return to the right frame | behaviour, already in list (D-06) |
| R13 | Frame page | Frame selector as a dropdown does not scale with many frames; find something modern | visual |
| R14 | Frame page | Far too much text on the Access tab | visual |
| R15 | Fleet | A retired frame must not appear on another frame's page; it belongs in the list of frames | already in list (D-04) |
| R16 | Update | Device and version card, version list and release notes: "ugly", to rework on phone and desktop | visual |
| R17 | Update | The page shown after Install or Revert is not pretty | visual |
| R18 | Pair | The refusal message could be better worded | visual (wording) |
| R19 | Account | "Manage access": odd margin, could be better integrated without taking more space | visual |
| R20 | Account | Battery: only the state through the dot, not a percentage | visual |
| R21 | Account | As administrator the hardware type is shown and is useless | visual |
| R22 | Sign-in | "First visit" block could be better integrated | visual |
| R23 | Sign-in | Credits are not reachable once signed in | behaviour, outside list |
| R24 | 404 | Could be more fun | visual |
| R25 | Users | Phone: the keyboard covers the field when inviting; odd margins between the title and the explanatory text in the invitation dialog, which is not needed; role-change confirmation has far too wide margins | visual |
| R26 | Users | After an invitation a copy-link icon appears but there is no link, so remove it. Also: how does a new user sign in the first time, no password was created? | behaviour / workflow, outside list |
| R27 | Editor | Phone: unidentified airlines take too much space; enter info behind a Complete / Edit button instead of open fields, same for known airlines; renaming should be an explicit "Rename" option | visual |
| R28 | Editor | The "ignore" action on the unidentified airlines should not exist (an ignored airline can no longer be edited) | behaviour, outside list |
| R29 | Editor | Expanding existing airlines is slow at times and the sub-items take too much space; rows ("marchand"? unclear wording) not optimised; phone "..." menu has margin and presentation defects; no filter | visual (filter is a feature) |
| R30 | Editor | "Customise" and "Change illustration" do the same; "Revert to default" is shown although no default illustration exists (the owner supplies the images) | behaviour, outside list |
| R31 | Editor | Desktop: unknown-airline rows are not pretty; opening an airline overlaps the next information | visual |
| R32 | Console | Locations page should no longer exist | behaviour, outside list |
| R33 | Audit | Phone: navigation by the top tab is "horrible"; opened toggles are hard to read | visual |
| R34 | Console More | "Mon cadre" label: rename to "Mon compagnon" or "Mes cadres"? Changing space: no jump matters on mobile | wording |
| R35 | Frame page (administrator) | Added by the owner after the walk-through: when an administrator opens the personal view of another person's frame, a much stronger visual marker is needed (for example a banner at the top) saying it is not their own frame. A marker exists today but is barely visible | visual |
