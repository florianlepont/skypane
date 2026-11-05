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
