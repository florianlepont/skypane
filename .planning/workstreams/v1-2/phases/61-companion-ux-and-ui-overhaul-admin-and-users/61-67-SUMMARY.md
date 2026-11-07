# Phase 61 Plan 67: More sheet, switches and dark contrast, Users page, bottom shadow Summary

The phone More sheet now holds Theme (Auto/Light/Dark) and Language (FR/EN) as one-tap segmented controls plus Account (with the signed-in e-mail), Sign out and the other destinations; switch tracks and thumbs hold 3:1 in both themes; the Users page cuts long e-mails with an ellipsis, shows Active/Invited/Disabled and You pills, explains the locked switch, counts co-managed frames and offers a Copy invitation message button; and the floating tab bar's shadow no longer reaches beyond the gap under it.

**Requirements:** D42 (P03, P07, P09), W70, audit findings F06, F08, F09, F11, F22, F24, F30.

## What changed

- **P03 / F09, F22, F24** (`companion/ui_nav.py`, `ui_shell.py`, `static/style.css`, `i18n_fr/nav.py`):
  - The More panel is a sheet as wide as the bar (floating just above it, scrolls inside on a short screen). It holds Theme and Language (the existing `/ui-theme` and `/ui-lang` POST forms, so they work without script and redirect back to the page), then the other destinations (Airline collection or Audit log), the Account row (page name over the e-mail, shown through the link's `data-email` so the link text stays "Account"), and Sign out. Theme or language = open the sheet and one tap; Sign out = two taps.
  - On the Account page the sheet holds only its links (the page already carries all three controls), and at 960px and wider the Account card's Sign out is hidden because the sidebar footer has one: exactly one visible Sign out on the administrator's Account page at every width. The space switch marks neither space current on that page.
  - Tab labels are 12px. The French Users label is "Membres" and the French airline label "Cies" (new key `nav.users_short`), so neighbouring labels never touch and none is clipped at 360px; the cells stay equal. The admin switch cell keeps its 68px width and outline (owner-validated earlier and pinned by tests); its height, label size and pill margin now match the other cells.
  - The closed sheet takes no box (`display: none` unless open).
- **P07 / F06, F11** (`static/style.css`):
  - New tokens `--color-switch-off` (#7C8799 light, #6B7589 dark) and `--color-switch-thumb-on` (white light, #14171F dark) in the four theme blocks: the off track is 3.6:1 (light) and 3.4:1 (dark) against the card, thumbs hold 3:1 against the track in both states.
  - The map's airport label (IATA code) is a solid chip (`--glass-solid`, hairline, chip radius) instead of a text halo; the `...` menu panel is opaque (`--color-dominant`) instead of glass, which was the source of the 4.0:1 "Re-activate" in dark.
  - The Location sheet header wraps (name on one line, codes and municipality under it) instead of ellipsizing, and the desktop runway chip detail wraps; the sheet stays capped at 28dvh and the phone chips keep length/surface in the title and for assistive technology.
- **P09 / F08, F30** (`pages/users_page.py`, `console_users.py`, `server/fleet_db.py`, `i18n_fr/admin_users.py`):
  - `.users-email` is one line with an ellipsis and the full address as title. Each row has one status pill (Active once signed in, Invited, Disabled) and the signed-in administrator also a You pill, in the battery/charging pill recipe (status colour mixed toward the text colour on a tint), 4.5:1 in both themes. The disabled switch of the own row (and of the last administrator) carries `aria-describedby` to the visible sentence ("This is you. You cannot disable or demote yourself.").
  - The frame count adds co-managed frames ("1 frame · co-manager"); `list_users_with_frame_counts` gains a `co_managed_count` column (expand-only).
  - "Copy invitation message" on every Invited row reuses `copy-button.js` (Clipboard API `writeText` from the click handler, selection and `execCommand` fallback, "Copied" feedback, hidden without script). The message names the app URL (from the request Host header, validated, https except loopback) and the invited address; no secret. EN and FR. On the 70rem table it is an icon-only 44px button.
- **W70** (`static/style.css`): see the root cause below.

## W70 root cause (bottom shadow with the floating Safari toolbar)

Not reproducible in this sandbox (no iOS WebKit); the cause below comes from reading the stylesheet and measuring what the bar paints in Chromium, and needs one check on the phone.

`--bar-shadow` was `0 18px 40px -12px` (plus a 4px layer): a drop shadow reaching about 46px below the bar. The bar sits `12px + safe-area-inset-bottom` above the screen edge, so most of that shadow extended below the bar's own box, past the gap and into the strip that iOS 26 Safari fills with its floating toolbar and its bottom edge effect, and (with the inset at 0) it was cut by the bottom of the viewport. The bar's glass also carries `backdrop-filter: blur(26px) saturate(200%)` on the same layer. Beneath a floating toolbar that samples the page and fixed elements near the edge, a large soft shadow plus a saturated blur under it paints a pale or dark wash that ends exactly at the viewport/toolbar edge: a full-width horizontal edge. Nothing else in the stylesheet paints a full-width layer at the bottom (`html` carries the sky gradient, `body` is transparent, no fixed full-width element), so the shadow was the only candidate in our control.

Fix: `--bar-shadow` now reaches exactly the gap (1px + 6px + 14px - 8px = 12px = `--tab-bar-gap`), in all four theme blocks, so it is soft, bounded to the bar and never leaves the strip between the bar and the screen edge. The browser test hides the bar and compares screenshots with `--safe-bottom` forced to 34px and 60px: nothing below the bar's gap, and nothing in the 3px screen-edge margin, may differ. That test fails (6 cases) with the old shadow. If a pale band remains on a real iPhone, the next suspects are the blur layer and the `--safe-bottom` inset value iOS reports with the floating toolbar; the screenshot from the phone would settle it.

## Deviations from Plan

**1. [Rule 3 - existing structure tests updated in place, subject changed]** Tab label size pins (11px to 12px, `test_status_pages_06/07`) and the sheet geometry pin (`bottom: calc(100% + var(--space-sm))`, `left: 0`); `test_sign_in_surfaces` shell digest (the no-principal shell's sheet changed); `test_console_users` (`.users-email` is an ellipsis, row class `users-row users-row--menu`); `test_nav_personal_console` (French Users label "Membres", airline label "Cies"); `test_personal_space_parity` (`_links` masks the principal's e-mail like `_normalise` already does); `test_browser_theme_switch` (the phone More sheet is now a navigation surface that holds the forms; sidebar and header still hold none); `test_browser_users_page` (long e-mail is an ellipsis with a title instead of wrapping); `test_browser_auth0` (signs out with the visible Sign out control: the sidebar footer on a desktop Account page), `test_browser_console` (the colour-reuse probe adds the three status pill classes, built from existing status tokens). Render baseline regenerated.

**2. [Rule 1 - plan wording] Account row without the person glyph.** The sheet's Account row shows the page name over the e-mail and a CSS chevron but no icon: several pinned tests read every `href="..."` in the sheet and an SVG `<use href>` would change them all. The e-mail is CSS-generated from `data-email` for the same reason (link text stays "Account"; parity of administrator and user pages).

**3. [Rule 1] Switch cell kept at 68px with its outline** rather than made identical to the other cells, because the personal bar of an administrator has six cells and a test pins the first cell at 68px and the outline as the owner-validated "set apart" marker. Equal-width cells and no clipped label at 360px in French are asserted by the new test on the console pages.

**4. French "Cies".** "Compagnies" needs 71px at 12px and the cells are 65-66px; a shorter label was the only way to keep equal cells and 12px. The page and sidebar keep "Compagnies" and "Éditeur de compagnies".

## Tests added

- `companion/test_browser_more_sheet.py`: theme and language in one tap and kept after a reload (360 and 390), scripts blocked, Sign out as a POST two taps away (its own session; the provider's logout address is answered by the test), the sheet's rows and 44px targets inside the viewport and above the bar, French and English tab labels 12px, whole and at least 4px apart on `/users`, `/fleet`, `/audit` at 360, the admin first cell's shape, one visible Sign out and a neutral space switch on the Account page (phone and desktop).
- `companion/test_browser_users_cards.py`: ellipsis on one line with the full title (360 and 1280, EN and FR), pills and their 4.5:1 ink read from screenshot pixels (both themes), the explained disabled switch, co-manager count (EN, FR), copy button (Clipboard API, selection fallback, hidden without script, desktop column).
- `companion/test_browser_contrast_edges.py`: switch track against card and thumb against track at 3:1 in both states and both themes (screenshot pixels), the map label and the `...` menu item at 4.5:1 on opaque surfaces, the Location header not cut and the sheet at most 28dvh, the bar shadow bounded (two insets, both themes) and its reach no larger than the gap.
- The three new files passed 4 times in 4 parallel processes (45 tests each).

## Verification

Per the test cadence (targeted tests only; CI runs the full suite): ruff, mypy, `check_comment_history`, `check_function_size` (931 functions, none over 80), `stub-server/test_phase47_freeze.py`, render snapshot regenerated, and the targeted test set listed in the hand-back. `companion/app.py` is 1477 lines.

Screenshots: `/tmp/claude-0/-home-user-skypane/4b1e4fdb-1c1f-5685-9cba-073edbf39a04/scratchpad/shots67/` (`before_*` and `after_*`: More sheet FR and EN, Users page 360 and 1280 in both themes, Location sheet dark, bar bottom with the inset forced to 34px).

## Known Stubs

None.

## Self-Check: PASSED
