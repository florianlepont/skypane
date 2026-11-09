# Phase 61 — batch 3 (owner validation feedback)

Source of truth: `61-OWNER-VALIDATION.md` (D27–D30, W6–W17). Mockups live in
the session scratchpad `sketches/` directory; executors read them from the
path given in their prompt. Plans run sequentially on one branch; each ends
green (ruff, mypy, targeted tests, render baseline regenerated, comment
history guard) and is committed on its own.

| Plan | Scope | Owner refs |
|------|-------|-----------|
| 61-36 | Account page and navigation chrome: remove language/theme switches from the sidebar (kept on Account, redesigned as labelled preference rows), Account icon becomes a person | W13, W14, W15 |
| 61-37 | Frame switcher becomes a strip of frame tiles (picture, name, status dot, last-seen word, active outlined, "Add a screen" tile); replaces the dropdown on phone and desktop | D30, W17 |
| 61-38 | Quiet-hours dialog redesigned as sketch C (preset cards, Start/End tiles) | D27 |
| 61-39 | Personalisation: animated secondary navigation, one page per entry, Look page shows the picker as main view | D29, W10 |
| 61-40 | Airline collection: sort/filter bar integrated (auto-submit select, no clipped Apply button, no-script fallback keeps a button), rarity colours on rare airlines and aircraft | W11, W12 |
| 61-42 | Console Fleet: tile strip + frame detail view + System tile, replaces Fleet, Status, Version, Device tabs | D31, W18 |
| 61-43 | Console Users as table (U1), manage modal removed | D32, W19 |
| 61-44 | Console Airlines editor as table (E1) with per-type toggle | D33, W20 |
| 61-41 | Location page rebuilt as sketch V1 (full-screen map, mode switch, bottom sheet / floating left card, derived coordinates and time zone, no-script form kept) | D28 |

Constraints: unchanged from earlier plans (phase-47 files and `hardware/`
untouched, expand-only, no deploy, EN/FR strings in `companion/i18n_fr/`,
360 px, 44 px targets, both themes, behaviour tests, app.py line ceiling).

## Batch 4 (owner validation round 4, 2026-11-05)

Source: `61-OWNER-VALIDATION.md` (W22-W46, D34). Same rules as batch 3, plus:
each plan runs the full suite once after its last code change.

| Plan | Scope | Owner refs |
|------|-------|-----------|
| 61-46 | Phone chrome: slim header (no gear, no Sign out panel), Console / My frame switch becomes the first, set-apart tab-bar button (big switch and More-menu switch removed), compact collapsible textured frame strip (picture + name only) | W22, W23, W38, W39 |
| 61-47 | Users pair their own frame (access matrix, ownership, audit, same limits), "Add a frame" from Account and the strip, zero-frame first sign-in prompt; Console "Add a frame" only in the strip (no duplicate access) | D34, W32, W33 |
| 61-48 | Short texts and Home/Account/Personalisation: shorter Home notification, shorter Special looks texts, bigger preview, single-level tab bar (Departures, Arrivals, Special looks, Calendar), Screen view removed, Look view in two columns on desktop (preview left, settings right), graphic frame preview in Account frames | W24, W26, W27, W30, W47, W48, D35 |
| 61-49 | Airline collection header simplified (sketch w1), badges tile smaller on phone, detail modal fits a phone screen | W28, W29, W46 |
| 61-50 | Location page: usable on phone, bigger desktop map, one search field above the panel (IATA or address), my-position button fixed, no coordinates/time-zone line, no saved-settings disclosure, discreet "i" map credit, centred segments everywhere | W25, W40-W45 |
| 61-51 | Console: no explanatory subtitles or helper captions, Users invite as a button/modal at the start or end of the list (no title overlap), Airlines editor global list (no frame strip), tap image to enlarge, change image in the "..." menu, filters scroll sideways | W33-W37 |

## Batch 5 (visual direction A, "sky and motion", D37)

| Plan | Scope |
|------|-------|
| 61-52 | Foundations: sky gradient background tokens (dawn/day/dusk/night, Light theme follows local time of day, Dark theme is always night, Auto follows the system), frosted-glass card surface tokens with a solid fallback and guaranteed contrast, bigger serif titles, motion tokens and a single reduced-motion rule |
| 61-53 | Home: personal greeting title, plane on a trail when a flight is detected, pulsing dot, filling progress bar and badges, staggered card entrance |
| 61-54 | Other pages polish with the same language (flights, collection, location sheet, personalisation, account, Console), view-transition timing, final contrast and performance pass |

Batch 5 rule (D38): the style is applied to the real, current pages. The
sketches are a direction only (colours, glass surfaces, gradients, motion,
type scale); no content, control, route or rule of the current pages is
dropped or redrawn from a sketch.

## Batch 6 (refined direction, D39)

| Plan | Scope |
|------|-------|
| 61-55 | Tokens and safe areas: viewport-fit=cover, theme-color per scheme, canvas colour, svh/dvh; one pale sky (Light) and ink (Dark), no time-of-day skies and no sky flash; graphite/ivory accent tokens; system sans only; one type scale; three radii |
| 61-56 | Surfaces and components: one glass tier, grouped-list component, hero block, section label, remove legacy beige opaque surfaces and tracked uppercase labels, fix Fleet State card overlap and the dark notice slab |
| 61-57 | Navigation chrome: Liquid Glass floating tab bar and phone header, desktop sidebar, frame button top right with popover (sheet on phone) replacing the tile strip and its fold, also in Console |
| 61-58 | User pages migrated to the new components: Home (hero + groups), Flights, Account, Location, Personalisation, Airline collection |
| 61-59 | Console pages: Fleet detail groups, Users table, Airlines editor, Audit; dialogs and empty states; login |
| 61-60 | Final pass: contrast, performance, consistency audit with screenshots, test hardening |

## Batch 7 (owner round 6, 2026-11-06)

| Plan | Scope |
|------|-------|
| 61-61 | Home and header: remove the plane animation, personal greeting title, recent-flights rows no longer all the same link, status-bar band colour continuity (theme-color and top background), "More" menu opaque like the tab bar |
| 61-62 | Flights: centred filter and its labels, merge plane icon and image button; airline collection filter and sort bar merged; Personalisation controls more compact |
| 61-63 | Manage access dialog fixed on phone, frame picture glyph fixed (selector popover and everywhere), co-manager relationship shown on Account |
| 61-64 | Complete audit (desktop and phone): display bugs, UI bugs, UX bugs (task walkthroughs, step counts, empty/error/loading states, flows), and prioritised improvement proposals so the app feels finished, modern, dynamic and simple. Read-only; the owner chooses what to build (D41) |
| 61-65 | Location page: map full-bleed under the header with a soft gradient scrim (W69), compact bottom panel, airport pins for all of France tappable in Airport mode, tap-to-place in My position mode, search suggestions (airports instantly from the local list, addresses as a result list on submit) | W65-W68 |

## Batch 8 (D42, audit decisions)

| Plan | Scope |
|------|-------|
| 61-66 | P01 Fleet save bar, P02 legacy redirects, P12 404 page, P11 i18n sweep |
| 61-67 | P03 phone More sheet, P07 switches and dark contrast, P09 Users page |
| 61-68 | P04 Personalisation selector and lists, P06 Flights search and Load more |
| 61-69 | P05 Location map: centred opening, clusters, runway badge, ORY label |
| 61-70 | P08 unified toast and sheet components, focus trap, error once |
| 61-71 | P10 Fleet phone sub-tabs |

## Batch 9 (D43, motion)

| Plan | Scope |
|------|-------|
| 61-72 | M2 skeletons and blur-up, M4 spring press, M5 sliding tab-bar pill, M8 spring switch |
| 61-73 | M1 live Home, M3 pull to refresh |
| 61-74 | M7 draggable sheets, M9 swipeable toast |
| 61-75 | M6 thumbnail to picture transition (picture alone), M10 airline card unlock |

## Batch 10 (D44, round 8)

| Plan | Scope |
|------|-------|
| 61-76 | Straight fixes: wording, search vs frame button, Location sheet spacing and runway cards, Fleet sub-tab thumb, tab bar flash, picture backdrop, opaque modals, Quiet hours Save reachable, autofill off, Manage access dialog, Account rows, Users own row, Nommer button, Personalisation vocabulary |
| 61-77.. | Decided after the owner answers D-A to D-J (mockups) |

## Batch 11 (D45)

| Plan | Scope |
|------|-------|
| 61-77 | D-A Compagnies page, D-G More menu, D-B Fleet desktop summary rows and dialogs |
| 61-78 | D-K Home signature: S1 Respiration + S3 Cycle |
| 61-79 | D-E Location rework, D-H Special looks and Calendar as pages |
| 61-80 | D-C airline editor, D-D audit log |
| 61-81 | D-I delete user, D-J owner removes a frame |
| 61-82 | D-F opening splash (concept to choose) and loading indicators |
| 61-83 | D-L battery row on Home (Frame group), for all users |

## Batch 12 (D46, round 9)

| Plan | Scope |
|------|-------|
| 61-84 | Straight fixes: toggle reload, Always on removed, picture dialog glitch, calendar bug, duplicate Save, aircraft size, floating Save label, tab pill and footer flash, Users menu and table panel, airline resolve fields, audit id, Airlines header and counter |
| 61-85.. | After the owner answers the mockup decisions |

## Batch 13 (D47)

| Plan | Scope |
|------|-------|
| 61-85 | R9-1 Home status wording and battery line, R9-2 Quiet hours compact, R9-3 Flights rows |
| 61-86 | R9-4 tab bar and More menu, R9-5 Console switch alignment and Journal tab |
| 61-87 | R9-6 Fleet desktop single column of sections |
| 61-88 | R9-7 Location full-bleed, loading state, airport pick in place |

## Batch 14 (D49, audit 2)

| Plan | Scope |
|------|-------|
| 61-89 | One SaveBar component for all pages (W147, F04, F21) |
| 61-90 | Flights: empty state, Load more in place, search over all history; Airlines empty search (W142, W143, F02, F03, F18, F19) |
| 61-91 | Personalisation: Calendar sheet visible, full look matrix, caption removed, looks rows on phone (W145, W146, W148, W153, F01, F06, F07, F12, F23, F24, F25) |
| 61-92 | Fleet and Users: Access forms and reassign button, versions with direct rollback, pending frames on phone, table overflows (W149, W150, W151, F08-F11, F15, F29, F30 and workflow findings) |
| 61-93 | Location search and radius, accessibility, naming glossary, tab bar labels, 360 overflows, type scale, time format (W144, F05, F13, F14, F16, F17, F20, F27, F28, F31, F32) |
| 61-94 | Performance quick wins (PERF P01-P11, P16) |
| 61-95 | Splash at every site opening, page preloading, session-expiry feedback (W154, W155, workflow findings) |
| 61-91a | W146: server theme catalogue with all colour x background x stripe combinations (before 61-91) |
| 61-93b | W152: Location phone map full-bleed (needs a fresh iPhone capture) |
| 61-90 (add) | Flights sort control (date, airline, direction) |
| 61-92 (add) | Rename a frame (owner and administrators) via the common SaveBar |

## Batch 15 (D51, audit 3)

| Plan | Content |
|------|---------|
| 61-97 | Design system: admin-only Components page (all components, all states, both themes and languages), one component test, unify switch / select / segmented control / chips / buttons / cards / tables / dialogs, fix the audit-3 component-driven findings |
| 61-98 | Remaining audit-3 visual findings (V01, V02, V05, V08-V25 not covered by 61-97), workflow findings (login ?next= for all routes, session-expired message on login, owner Rename entry, CSRF on settings and quick routes, pairing id, special-look error keeps input, no-JS upload buttons, unsaved-changes guard), performance quick wins (N01 folded-history cache, N03 JS comments, N02 idle prefetch limits, P16 Display previews, N06 ETag) |

## Batch 16 (D52, remaining audit points)

| Plan | Content |
|------|---------|
| 61-99 | Remaining UX points: V15, V19, V22, V27, V28, nearest-airport offer on phones, /ui-theme and /ui-lang CSRF, naming glossary, Safari band tint on the Location map, 14 partial workflow items |
| 61-100 | Remaining performance items: P07, P08, P09, P12, P13-P15, N04, N05, N07-N09 |
