# Quick 261003-uzj: restore the phone page title, tighten the top spacing

Owner doubt on 261003-tq4: the hidden title may have been the wrong fix; the gap above it was the problem.

1. Revert the tabbed visually-hidden title (page_header parameter, class, CSS, call sites, tests).
2. Phones (< 960px): .site-header margin-bottom 32 -> 16, .page-content padding-top 32 -> 16, so the app-bar-to-title gap goes 64 -> 32px. Desktop untouched.
3. Retarget the browser test: title visible on all seven pages at 360/390/1280, phone gap <= 32, no overflow.
4. Regenerate render_baseline.json after checking the diff is only the class removal; run the full suite and gates.
5. Screenshots before/after at 390/360, light/dark, EN/FR (outside the repo).
