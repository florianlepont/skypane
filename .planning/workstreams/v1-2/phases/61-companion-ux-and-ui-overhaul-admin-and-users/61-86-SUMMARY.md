# Phase 61 Plan 86: Tab bar, More menu, Console switch alignment, one h1 per page Summary

Owner decisions D47 R9-4 and R9-5 (W129 to W134) plus the 61-85 accessibility follow-up: an opaque floating tab bar with a strong active pill, an opaque More sheet in the owner's order, identical chrome in the Console and in My frame, and exactly one h1 on every page.

## What changed

- **R9-4 Tab bar.** The bar is one solid token surface (`--glass-solid`), no blur, no translucency anywhere (the glass rule for the bar and the sheet and the transparent-over-the-map override are gone). It sits 6px above the bottom safe area (`--tab-bar-gap` 6px) with 8px side margins (`--tab-bar-side`), a solid `--bar-border` edge (new hex tokens in all four theme blocks) and a shadow that stays inside the 6px gap below and is cast upward (`--bar-shadow`). The active cell is a solid accent pill (`--color-accent`, on-accent ink; the sliding pill and the server-rendered pill use the same fill, so a script failure never leaves a tab without its pill). `--bar-pill-bg` is removed.
- **More sheet.** Opaque, the same colour and edge as the bar, with an upward-only shadow (`--bar-sheet-shadow`, new token) so it never darkens the bar; the dim/blur scrim behind it is unchanged. Order, top to bottom: page rows (Companies for a user or an administrator in My frame), separator, Account (with the e-mail), Theme, Language (label and control on one row), Sign out. On the Account page the sheet still holds the links alone.
- **R9-5 Alignment.** `.brand` is 44px high whether or not it is a link, so the logo, the space switch and everything under it sit at the same place in both views (desktop sidebar and phone header). The Console bar gains the audit log tab (French "Journal", English "Audit"): six cells in both views, the space switch a fixed 68px cell (same shape in both views), the other five equal. The More sheet in the Console holds only Account, since every Console page is in the bar.
- **One h1.** Home's page heading is a visually hidden `h1` naming the page (`class="page-title visually-hidden"`); the greeting is a quiet `p.page-greeting` (no longer a heading). The visible Home title stays the state headline.

## Tests

New: `companion/test_browser_nav_alignment.py` (bounding boxes of brand, logo, switch track and segments at 1280; header brand, logo, bar and every tab cell at 360 and 390, in EN and FR, Console against My frame: equal; verified to fail without the 44px brand rule). Restored: the foundations type-scale check now covers Home with no exclusion and asserts exactly one `main h1` on every page; the overhaul sweep h1 check has no greeting exclusion.

Changed in place (subject changed deliberately): bar and sheet pins (opaque, 6px gap, 8px margins, accent pill with on-accent ink, upward shadow, six Console cells, sheet order), the sky-contrast token test (opaque bar, pill 3:1, ink 4.5:1), the tab-bar float and More sheet browser tests, place-sheet and sky-motion bar glass checks, accent budget (the current tab pill is allowed), the step-count test A6 (Audit is now one tap), Home greeting and h1 pins, the page-title test (on Home the hidden h1 names the page and the state headline is the visible title). Render baseline rewritten, shell digest unchanged.

Screenshots: `scratchpad/shots86/` (bars and More sheet for admin in My frame and Console, light and dark, owner, desktop Console and My frame, 360px bars).

## Deviations

- The admin first-cell shape test tolerance widened from 8px to 16px (a fixed 68px switch beside five equal cells of about 54px at 360px); the five destination cells are now asserted equal to 1px.
- The tab bar side margin is 8px (the mockup showed 10px) and the switch cell 68px (mockup 72px): at 360px the French "Membres" label would otherwise be clipped.
- Home's visible title is not the h1 element: the state headline is a `p`-hosted span used by many pins, so Home carries a visually hidden h1 (an option the owner offered).
- `61-STEP-COUNTS.md` still records A6 as 2 steps; the test now asserts 1 (not edited, planning file).

## Tests run

ruff, mypy, check_comment_history, check_function_size, stub-server/test_phase47_freeze.py, render snapshot rewritten; non-browser companion tests mentioning nav, tab bar, sheet, switch, brand, greeting, h1 plus test_page_scripts, test_stylesheet_structure, test_suite_guards, test_sign_in_surfaces, test_render_baseline, test_companion_app_0*; whole browser files that mention the changed surfaces plus test_browser_overhaul_sweep and test_browser_foundations; the new alignment test run repeatedly.
