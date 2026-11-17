---
quick_id: 261115-ulw
description: Account tab replaces More for non-admin users
---

# Quick plan: Account tab replaces More for non-admin users

Goal: on the phone bottom tab bar, a signed-in non-admin user gets an
"Account" tab as the last cell (a plain link to the Account page, no sheet).
Administrators keep "More" with its full sheet (Account, space switch, theme,
language, Sign out).

Verified first: the Account page itself carries Language, Theme and Sign out,
so the sheet's content stays reachable for a non-admin user (one tap further).

Tasks:
1. Tests first (companion/test_browser_tab_bar_roles.py): user bar ends in
   Account (EN/FR), no `.tab-bar__more`, tap goes to the Account page, Account
   cell active there, Language/Theme/Sign out present on the page; admin keeps
   More and its sheet. Six cells still fit at 320/360/390px.
2. Implement in companion/ui_nav.py `_tab_bar_html`.
3. Full suites, ruff, mypy, function-size and comment-history gates;
   regenerate render baseline if the stylesheet hash changes.
