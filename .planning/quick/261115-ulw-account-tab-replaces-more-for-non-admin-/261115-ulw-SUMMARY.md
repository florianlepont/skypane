# Quick 261115-ulw: Account tab replaces More for non-admin users

On the phone bottom tab bar, a signed-in plain user now gets "Account" (Compte)
as the sixth cell, a direct link to the Account page, instead of a "More" cell
that opened a sheet. Administrators keep "More" and its full sheet.

## Verified before coding

- The More sheet held, for a user: the Account row, Theme (Auto/Light/Dark),
  Language (FR/EN) and Sign out (on the Account page the sheet is the Account
  row alone).
- The rendered Account page carries Language, Theme and Sign out itself
  (asserted in a browser test), so nothing became unreachable and no Account
  page change was needed.
- Pages with a user bar checked in-process: Home, pair-a-frame, Account,
  Credits, 404s all end in Account; Account is the active cell on Account and
  pair-a-frame. The foreign-frame state exists for administrators only (they
  keep More). Signed-out pages render no bar, as before.

## Change

- `companion/ui_nav.py`: `_tab_bar_html` appends the Account cell
  (`_tab_bar_cell_link`, person icon, active state and `aria-current` from the
  existing entry) for a user and returns; the nav wrapper is factored into
  `_tab_bar_nav_html`. No CSS change, so the stylesheet hash and render
  baseline are unchanged.

## Tests (updated on purpose)

- New/changed in `test_browser_tab_bar_roles.py`: user bar ends in Account (EN/FR),
  no `.tab-bar__more`, tap goes to /account, Account active there, Theme,
  Language and Sign out on the page; admin keeps More; six cells still fit at
  320/360/390 for both roles.
- Old behaviour asserted elsewhere, now the new behaviour: `test_user_nav`,
  `test_nav_personal_console`, `test_browser_nav_spaces`, `test_browser_console`,
  `test_browser_more_panel_redesign` (sheet tests now admin only),
  `test_personal_space_parity` and `test_browser_overhaul_sweep` (the bar's last
  cell is excluded from the admin-equals-user comparison, by design).

## Deviations

- The worktree given at start was removed mid-task; work continued in a new
  worktree of the same branch under the scratchpad directory.
