---
phase: quick-261109-iva
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - companion/pages/home_page.py
  - companion/pages/home_title.py
  - companion/pages/home_greeting.py
  - companion/pages/home_rename_row.py
  - companion/ui_groups.py
  - companion/ui_components.py
  - companion/static/style.css
  - companion/static/nav-dropdown.js
  - companion/i18n_fr/home.py
  - companion/test_browser_home_greeting.py
  - companion/test_home_greeting.py
autonomous: true
requirements: [QUICK-261109-iva]
must_haves:
  truths:
    - "Home shows the frame picture on the left and, always beside it (also at 360 px), the frame name as the big page title"
    - "A round 44px pencil button named Rename frame (EN/FR) sits next to the title and opens the existing frame-name route; only people who see the Frame name row today see it"
    - "Under the title: a pill (dot + state word) and the freshness text"
    - "The greeting, its JS swap, its CSS and the Frame name row are gone; banner, quick switches and recent flights are unchanged"
    - "The document title and nav label stay Home/Accueil; Home has exactly one h1 (the frame name)"
  artifacts:
    - path: "companion/pages/home_title.py"
      provides: "Hero title row: h1 frame name + rename pencil"
    - path: "companion/test_browser_home_greeting.py"
      provides: "Replaced by hero-title behaviour tests (rename file if clearer, e.g. test_browser_home_title.py)"
  key_links:
    - from: "companion/pages/home_title.py"
      to: "frame_name_page.device_route(device.id)"
      via: "pencil href, gated by device_scope.viewer_may_rename_current()"
      pattern: "viewer_may_rename_current"
---

<objective>
Replace Home's small grey greeting with the owner-validated hero: picture left, always side by side with the text; right side the frame name as h1 with a round rename pencil, under it a state pill and the freshness text. Mockup: /tmp/claude-0/-home-user-skypane/6f861349-4cf1-5b88-9b66-7af3be82a17a/scratchpad/sketches/d2-planche.png (desktop, 390, 360 - view it first).
Purpose: the frame name is the page identity; the rename becomes one tap from the title.
Output: reworked Home hero, new catalogue component, cleaned greeting code/CSS/i18n, updated tests and render baseline.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@CLAUDE.md
@.claude/skills/sketch-findings-skypane/SKILL.md
@.claude/skills/sketch-findings-skypane/references/component-catalogue.md
@companion/pages/home_page.py
@companion/pages/home_greeting.py
@companion/pages/home_rename_row.py
@companion/ui_groups.py
@companion/ui_components.py

<interfaces>
Existing, reuse:
- home_page.render(): builds header via layout.page_header(i18n.t(PAGE_TITLE), freshness_html=layout.refresh_marker_html(now), title_html=home_greeting.title_html(), trail_html=home_greeting.frame_line_html()); then _frame_state_html -> ui_groups.hero(status_line_html, picture_html, lines_html, extra_class, attrs, status_class, heading_html). hero emits `<p class="hero__status ...">` holding today's dot + `.home-state__title` word, then lines (detail, next-update row with cadence info, admin battery dial).
- page_header(title, purpose, freshness_html, action_html, trail_html, title_html): a truthy title_html replaces the h1; empty falls back to the default h1. Signature order must not change (append kwargs only).
- home_rename_row.row_html(): gate = device_scope.current_device() is not None and device_scope.viewer_may_rename_current(); href = frame_name_page.device_route(device.id); label message "home.rename_frame_label"; name = ui_shell.device_display_name(device).
- ui_components.icon_button_html(icon_id, aria_label, variant="ghost", button_type="button", attrs="") (a button; the pencil must be a LINK, so add a link variant next to it, e.g. icon_link_html(icon_id, aria_label, href, ...) using the same `.btn--icon` 44px class, rather than a per-page class). icon id: "icon-pencil".
- _status_dot_html(status) / status.word / status.dot_state (shared frame-status resolver) already give the state dot and word; pill_html(text) exists in ui_components.
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Hero title markup and removal of greeting/rename-row from Home</name>
  <files>companion/pages/home_title.py, companion/pages/home_greeting.py, companion/pages/home_rename_row.py, companion/pages/home_page.py, companion/ui_groups.py, companion/ui_components.py</files>
  <action>
1. Add `icon_link_html` (round 44px icon-only link, `.btn btn--icon`, aria-label escaped) to ui_components.py beside icon_button_html; reuse its CSS, no new button style.
2. Create companion/pages/home_title.py (git mv home_greeting.py and home_rename_row.py content into it; delete both old modules; no leftover first_name/prefs-email logic, but leave prefs.py alone unless its comment about the greeting becomes false - then fix the comment). It exposes `title_html(device)`: a `.title-action` wrapper (new catalogue component, styled in Task 2) holding `<h1 class="page-title title-action__text">` with the frame name (device_display_name(device); when there is no current device fall back to the plain page name i18n.t(PAGE_TITLE)) and, only when device_scope.viewer_may_rename_current() is true (exactly today's Frame name row gate, per task spec), the pencil link to frame_name_page.device_route(device.id) with EN/FR aria-label "Rename frame" / "Renommer le cadre" (new message id home.rename_frame_action in i18n_fr/home.py). Use the single-frame and multi-frame cases identically: the name is the title in all cases.
3. home_page.py: stop using home_greeting/home_rename_row; `_switches_html` gets only the battery row (no rename row). Make the h1 live inside the hero: extend ui_groups.hero with an optional `title_html=""` rendered first inside `.hero__body` (above the status line) and have `_frame_state_html` pass home_title.title_html. Since the page may carry only one h1, call page_header with a new appended kwarg (e.g. `omit_title=True`) that emits no h1 while still emitting freshness_html (the silent refresh marker must remain so freshness.js keeps refreshing Home) and the flash slot; do not rely on a hidden dummy element. The document title and nav label stay Home/Accueil (PAGE_TITLE untouched).
4. Hero text column order: title row (h1 + pencil), then a state pill (the existing _status_dot_html dot inside `.home-state__pill` plus the status.word text, using pill_html/catalogue pill look; keep dot colour/pulse classes and home-state--{dot_state} tint), then the freshness text (`_next_update_html` output plus the held-state detail sentence and, for administrators, the battery dial as today). The old `.home-state__title` big word line is replaced by the pill; keep say_once behaviour (notice present -> no next-update line). The picture/ring column is unchanged.
5. Update the module docstring of home_page.py to match (no phase/plan IDs in comments). Keep home_page.py functions under 80 lines and app.py untouched.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -m ruff check companion && server/.venv/bin/python3 -m mypy && server/.venv/bin/python3 scripts/check_function_size.py check && server/.venv/bin/python3 scripts/check_comment_history.py check</automated>
  </verify>
  <done>Home HTML has one h1 (frame name) inside the hero with a rename link only for those allowed to rename; no data-greeting / page-greeting / home-greeting__frame / frame-rename markup; imports of the removed modules are gone everywhere (grep clean).</done>
</task>

<task type="auto">
  <name>Task 2: CSS, catalogue component, JS and i18n cleanup</name>
  <files>companion/static/style.css, companion/static/nav-dropdown.js, companion/i18n_fr/home.py, companion/ui_components.py</files>
  <action>
1. style.css: add `.title-action` (flex row, align center, gap var(--space-sm), min-width 0; the h1 takes `flex: 0 1 auto; min-width: 0` and the pencil `flex: none` so a long name wraps/ellipsises inside its own column and never pushes the pencil under it: use `overflow-wrap: anywhere` on the text and `flex-wrap: nowrap` on the row). Title size via existing font tokens: 48px at desktop, 28px up to the phone breakpoint, 24px below 380px (media queries, display face, same weight/tracking tokens the old `.home-state__headline` used). Hero layout: `.hero` row keeps picture and body side by side at every width including 360 (picture about 104px wide on phone via the existing `.hero__picture` rules; remove any rule that stacks it). Style `.home-state__pill` (dot + word, small, token colours, readable in both themes per the existing contrast tests) and remove the now unused `.home-state__title`/headline-size rules only if nothing else uses them (grep first), plus `.page-greeting` (~line 759), `.home-greeting__frame` (~13153) and the `.frame-rename` rules; fix the comment near line 5250 that mentions the greeting. No tokens invented: reuse the existing ones; never use px colours.
2. nav-dropdown.js: delete the data-greeting lookup and swap block (lines ~23-36) and its header comment mention; keep the document marker logic (test_companion_app_02 asserts the marker precedes the old selector - update that test in Task 3).
3. i18n_fr/home.py: remove home.greeting_* entries (grep that no other module uses them: the only users were home_greeting.py and its tests), remove home.rename_frame_label if no longer used, add home.rename_frame_action = "Renommer le cadre". Keep ordering/format of the file.
4. Add the new component to the Components catalogue: row in .claude/skills/sketch-findings-skypane/references/component-catalogue.md ("Title with icon action", `.title-action`, helper `home_title.title_html`/`icon_link_html`, when to use) and its entry on the admin Components page (find with grep for an existing entry such as icon_button_html under companion/pages) rendering the title plus pencil link.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -m pytest companion/test_i18n.py companion/test_companion_app_02.py -q -x -n auto -p no:cacheprovider 2>&1 | tail -15</automated>
  </verify>
  <done>No greeting code left in CSS/JS/i18n; the hero is styled to the three sizes; the Components page and catalogue document the new component; i18n tests (EN/FR parity, unused-id guards) green.</done>
</task>

<task type="auto">
  <name>Task 3: Tests and render baseline</name>
  <files>companion/test_browser_home_greeting.py, companion/test_home_greeting.py, companion/test_companion_app_02.py, companion/test_companion_app_04.py, companion/test_home_notice.py, companion/test_browser_home_battery_row.py, companion/test_browser_home_state_card.py, companion/test_browser_audit3_fixes.py, companion/testdata/render_baseline.json</files>
  <action>
Tests assert served HTML/CSS/JS or a real browser, never source text. Browser tests need a Chromium launch arg executable_path from /opt/pw-browsers/chromium_headless_shell-1243/*/chrome-headless-shell when the default is missing.
1. Replace test_home_greeting.py with test_home_title.py (served-HTML tests, EN + FR via the lang cookie/i18n override): the h1 is the frame name and is the only h1 on Home; a viewer who may rename gets a link whose href is /devices/<id>/frame/name (via the device scope used by the fixtures) with aria-label "Rename frame"/"Renommer le cadre"; a viewer who may not (co-manager/user per today's viewer_may_rename_current rules) gets no pencil; the page <title> still starts with Home/Accueil; no data-greeting, page-greeting or "Frame name" row anywhere in Home.
2. Rewrite test_browser_home_greeting.py (rename to test_browser_home_title.py with git mv) around the hero: at 1280, 390 and 360 the picture and the title column are side by side (picture right edge <= title left edge, same top band), title font-size 48/28/28 and 24 at a width below 380 (use a 360 viewport for 24... 360 is below 380 so 360 -> 24, 390 -> 28), the pencil box is >= 44x44 and stays on the h1's line (pencil top < h1 bottom, pencil left >= h1 right) with a long frame name, no sideways page overflow (_assert_no_page_overflow), pill shows dot + state word, empty-state picture still renders as `.preview-frame--empty`, no plane animation (keep that test), the cards-come-in-one-after-another test, and the tab-bar legibility test unchanged. Clicking the pencil navigates to the frame-name page. Drop the hour/greeting-swap tests.
3. Fix the other tests that referenced removed things: test_companion_app_02 (greeting selector/marker ordering: assert the served nav-dropdown.js still sets the document marker and contains no greeting swap; the served body assertion at ~1511 must target something real, e.g. the hero's `title-action`), test_companion_app_04 (~486), test_home_notice (~97: order is now notice then hero), test_browser_home_battery_row (~231: assert the title is larger than the pill/freshness text instead of the greeting size), test_browser_home_state_card (~584 reveal list: replace `.page-greeting` with `.title-action`) and test_browser_audit3_fixes (~57-76: the long frame name is cut/wrapped inside the title column and never covers the logo; the pencil stays beside it). Grep for any test asserting `.home-state__title`, `.frame-rename` or h1 text "Home" on Home and update to the new behaviour.
4. Regenerate the render baseline the repo uses (companion/testdata/render_baseline.json; find the regenerate command in the test or scripts that reads it, e.g. grep render_baseline) and review the diff contains only Home-related changes.
5. Run gates: ruff, mypy, scripts/check_comment_history.py check, scripts/check_function_size.py check, the touched tests plus companion/test_suite_guards.py, companion Components-page tests, and stub-server/test_phase47_freeze.py. Do not touch phase 47 files or hardware/; do not push.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -m pytest companion/test_home_title.py companion/test_browser_home_title.py companion/test_companion_app_02.py companion/test_companion_app_04.py companion/test_home_notice.py companion/test_browser_home_battery_row.py companion/test_browser_home_state_card.py companion/test_browser_audit3_fixes.py companion/test_suite_guards.py stub-server/test_phase47_freeze.py -q -n auto -p no:cacheprovider 2>&1 | tail -20</automated>
  </verify>
  <done>All listed tests and the freeze test pass; ruff, mypy, comment-history, function-size gates green; the baseline is regenerated; app.py is under 1500 lines and no JS file exceeds 1500.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| stored frame name -> Home HTML | user-supplied text rendered in the h1 |
| viewer -> rename link | only owners/administrators may rename |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-iva-01 | Tampering (XSS) | home_title.title_html frame name | mitigate | escape_html on name and aria-label/href values |
| T-iva-02 | Elevation of privilege | rename pencil | mitigate | pencil rendered only when device_scope.viewer_may_rename_current() (unchanged gate); the rename route keeps its own server-side check, tested for a non-renamer |
| T-iva-03 | Information disclosure | removed greeting | accept | the e-mail-derived first name is no longer rendered anywhere |
</threat_model>

<verification>
Targeted test list in Task 3 green; ruff, mypy, check_comment_history, check_function_size green; view Home at 1280/390/360 in a browser screenshot against the d2-planche mockup.
</verification>

<success_criteria>
Home shows picture-left, frame-name h1 + rename pencil + pill + freshness at all widths; greeting, its JS/CSS/i18n and the Frame name row are gone; one h1; document title still Home/Accueil; new component catalogued; tests and baseline updated; nothing pushed.
</success_criteria>

<output>
Create `.planning/quick/261109-iva-home-title-frame-name-hero-with-rename-p/261109-iva-SUMMARY.md` when done
</output>
