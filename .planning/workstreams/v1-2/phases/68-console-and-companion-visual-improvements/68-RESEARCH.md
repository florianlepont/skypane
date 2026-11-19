# Phase 68: Console and Companion Visual Improvements - Research

**Researched:** 2026-11-18
**Domain:** Server-rendered companion UI (Python stdlib HTML builders, hand-written CSS, ES5 scripts), Auth0 invitation flow, access matrix
**Confidence:** HIGH on file maps, tests, gates and the behaviour traces (read in the code). MEDIUM on the visual root causes of R01, R08, R10, R11 and D-07 (not reproduced in a browser: Playwright is not installed in this research environment). LOW on Auth0 tenant-side behaviour (see Assumptions).

<user_constraints>
## User Constraints (from 68-CONTEXT.md)

### Locked Decisions
- **D-01:** Both the administrator console and the companion pages for users are in scope (owner, 2026-11-16).
- **D-02:** No cap on the list size; the list is closed on 2026-11-18 (D-20). The list only grows by the owner's own remarks.
- **D-03:** Home page: apply the approved mockup `68-HOME-MOCKUP.html` (online, sleeping, offline states).
- **D-04:** Fleet page: a retired frame is listed while the owner views another frame; make it clear which frame the page is about.
- **D-05:** Flight history: the search field drops under the title at some narrow widths; fix the header layout.
- **D-06:** "Back to Fleet" from a frame page must return to that frame, not the first one.
- **D-07:** Theme page: switching tab reloads all frame previews. Find whether it is a full navigation or changing preview URLs (previews carry a 5-minute cache in `companion/preview_images.py`) and fix.
- **D-08:** Naming "Flights" (tab) versus "Flight history" (page), W6-08. French tab label "Compagnies" became "Airlines" (PR #453) and stays unless the owner says otherwise. Naming choice goes through the owner, in English and French.
- **D-09:** More sheet width on a tablet (V6-10).
- **D-10:** Yellow Full/Soft-stripe contrast (1.12) on the panel; needs a real-device check.
- **D-11:** More sheet grab handle (A6-09).
- **D-12:** 44 px touch target for the quiet-hours link (V6-07).
- **D-13:** Tapping the active tab (W6-09).
- **D-14:** Hand-built `banner__pill` markup on a few pages: use the catalogue component.
- **D-15:** Airlines page: show the airlines known by name only (no artwork) as read-only rows, with the option to add artwork later. Touches companion files owned by Phase 64: say so before touching them. Mockup first.
- **D-16:** Owner-guided page-by-page walk-through, a screenshot per remark. New remarks only on the owner's say.
- **D-17:** Mockup approved by the owner before code for every visual change. The Home mockup is already approved. Any new pattern is added to `sketch-findings-skypane`.
- **D-18:** English and French both work, phone width works, browser tests cover each visual change (behaviour-over-source), accessibility checks keep passing.
- **D-19:** Owner validates on the deployed companion in English and French. Draft PRs only; production deploys are approved by the owner, never by Claude.
- **D-20:** All remarks R01 to R35 of `68-WALKTHROUGH.md` are in the list ("on fait tout"), including the ones marked "behaviour, outside list" (R02, R23, R26, R28, R29 filter, R30, R32). They still need the access rules of Phases 54, 55 and 60, the golden hashes and `test_phase47_freeze.py` to stay green, and each one a test of the new behaviour.
- **D-21:** R35: a strong, unmissable marker (for example a top banner) on the personal view of a frame that is not the administrator's own. Mockup first.
- **D-22:** R26 includes a workflow question (how a new invited user signs in the first time without a password): research must establish how invitation and sign-in work today (Auth0) and propose options to the owner before any change. Other open points: the word "Marchand" in R29 (ask the owner), R10 (is the More sheet blur different in Safari: check), R34 label choice ("Mon compagnon" or "Mes cadres").
- **D-23:** R12 and R15 are the same as D-06 and D-04; value order is decided at planning, the owner picks mockups one by one.

### Claude's Discretion
- Order of execution of the items and grouping into plans, by value then by shared files.
- Technical way to fix D-06 and D-07 (investigation first).

### Deferred Ideas (OUT OF SCOPE)
- Real-frame check of the landscape hold caption legibility (Phase 64/65).
- Items set aside in Phase 61 and not selected: A5-15, A5-16, A5-20, A5-21, W5-12, W5-13, W5-17, W5-22, X13, P5-*, A6-11; not-planned items (canvas map markers, duplicated airport JSON, Airline editor weight, content-visibility).
- (Not in the owner's list, so out of scope: the two "Route sources" candidates added to `68-CANDIDATE-ITEMS.md` on main by PR #469. They are unselected; see Open Question 6.)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CON-01 | The visual improvements the owner lists for the console and the companion are made within the design system, in English and French and at phone width, with mockups approved first and no behaviour change beyond the list. | Per-remark file and test map (section "Per-Remark Map"), behaviour traces (R02, R23, R26, R28, R30, R32), grouping into plans and waves, Validation Architecture. |
</phase_requirements>

## Summary

Phase 68 is a polish phase over 35 owner remarks plus 14 starting items (D-03 to D-15) on a code base whose rules are strict and mechanical: every companion change has to keep `companion/testdata/render_baseline.json` equal byte for byte (76 page captures plus 97 unauthenticated route records), keep the access matrix complete (every route in the table has a matrix row), stay under 1500 lines per production file and 80 lines per function, keep every string bilingual, and be covered by browser tests that assert behaviour, never source text. The baseline embeds the stylesheet cache-buster `?v=<hash>` of every linked asset, so any edit to `style.css` changes all 76 captures and any edit to an area stylesheet changes the pages that link it. Baseline regeneration is therefore a serial, one-owner step per wave, not something plans can do in parallel.

Most remarks are contained in one page module plus one area stylesheet plus one `i18n_fr` module. Three clusters are heavier. (1) The Fleet frame page (R11 to R15, R35): its pieces live in `console_fleet_view.py`, `fleet_page.py`, `frame_menu.py`, `co_managers_card.py`, `config_page` (embedded) and `style-admin.css`; "Back to Fleet" is a fixed `/fleet` link in `ui_shell.frame_notice_html`, which is the whole cause of D-06/R12 and is also the R35 marker. (2) The Airlines editor (R27 to R31, D-15): `pages/airlines_page.py` is already 1287 lines, so new rows and a filter must go into new modules. (3) The Home rebuild (D-03, R01, R02): the approved mockup introduces a statistics card (per-hour timeline, 7-day bars, most-seen airline) for which no query exists in `server/history_db.py`, and it replaces rows with a preview strip; ten Home browser test modules are rewritten.

The two behaviour questions with real consequences are R26 and R32. R26: the "copy" control copies a pasteable invitation message (text with the app address and the e-mail), not a link, and nothing in the invite flow creates an Auth0 account; with sign-ups disabled in the tenant, an invited person cannot sign in until the administrator creates their Auth0 user by hand (documented in `deploy/README.md` and SEED-012, targeted v1.4). R32: `GET /locations` already redirects to `/fleet` and the nav entry is gone; what is left is `POST /locations/add|{id}/edit|{id}/delete` and the Locations page that a refused POST re-renders. No page in the app posts to them. Removing them is a deliberate, owner-requested change to the route table and the matrix (rows, route-table lists and the unauthenticated baseline all change).

**Primary recommendation:** Serialise by shared files, not by value: one plan per page family, wave-ordered so that `style.css`, `ui_shell.py`/`ui_nav.py` and `render_baseline.json` are each touched by one plan at a time; produce all mockups first (HTML files in the phase directory, owner approves one by one) and keep code plans blocked on their mockup. Merge `origin/main` into the Phase 68 branch before the first code plan (the branch is behind by Phase 65 server work and docs only; no companion diff).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Page markup, copy, French strings | Frontend Server (Python stdlib HTML builders) | — | All pages are server-rendered; scripts only enhance (no-script floor). |
| Styling, tokens, breakpoints | CDN/Static (hand-written CSS in `companion/static/`) | — | One cascade in `style.css` plus area sheets linked per page by `page_styles.py`. |
| Interaction (filter, copy, dialogs, tabs) | Browser (ES5 scripts) | Frontend Server | Always with a no-script fallback; JS files under 1500 lines. |
| Access (route x role x owner) | API/Backend (`routes.py` table, `page_policy`, `access.py`) | — | Default-deny; matrix test asserts every route has a row. |
| Invitation and first sign-in | API/Backend (`console_users`, `sign_in`, `fleet_sessions`) | External IdP (Auth0 tenant) | Local roles in `fleet.db`; identity proof by Auth0; link by verified e-mail. |
| Home statistics (new, D-03) | Database/Storage (`history_db` read queries) | Frontend Server | New aggregate reads only; no new writes. |
| Flight thumbnails / previews | Database/Storage (gallery match rule) | Frontend Server | Existing 90 s / 10 s match rule in `history_page`; reuse for Home strip (R02). |

## Standard Stack

No new dependency. The stack is the shipped one; Phase 68 adds none. [VERIFIED: CLAUDE.md, `server/requirements.txt` policy "stdlib + Pillow + requests only"]

### Core
| Library / tool | Version | Purpose | Why standard here |
|----------------|---------|---------|-------------------|
| Python stdlib `ThreadingHTTPServer` + string builders (`companion/ui_*.py`, `layout.py`) | Python 3.14 in production (3.13 locally) | Server-rendered pages | The project's only UI stack; catalogue helpers: `ui_groups`, `ui_segmented`, `ui_modal`, `ui_components`, `ui_filter`, `ui_entity_list`, `ui_save_bar`. |
| Hand-written CSS, tokens in `style.css` (four theme blocks) | — | All styling | `--space-xs..3xl`, radii 14/22/28/32, `--font-*` tokens; every token edit goes in all four blocks. |
| ES5 scripts in `companion/static/` | — | Enhancement | Vendored Leaflet 1.9.4 on Place only. |
| pytest, pytest-xdist, pytest-cov, pytest-playwright (Chromium headless shell), pytest-socket | per `server/requirements-dev*.txt` | Tests | `SKYPANE_REQUIRE_BROWSER=1` makes a missing browser fail. |

### Supporting
| Tool | Purpose | When to use |
|------|---------|-------------|
| `python test-support/companion_render_snapshot.py --write` | Regenerates `companion/testdata/render_baseline.json` | After each wave's visual changes, by one plan only. [VERIFIED: file read] |
| `scripts/check_function_size.py`, `scripts/check_comment_history.py check`, ruff, mypy (module list in `pyproject.toml`) | CI gates | Every plan. |
| `.claude/skills/sketch-findings-skypane` | Design system; must be updated in the PR that changes a token, nav, component or page layout | Every plan that adds a pattern (R35 banner, frame list, Home stats card, Update panel). Its "as of" line is 2026-11-13 and is already behind main (e.g. Account tab for non-admins, PR #450, Reassign sheet, PR #451). |

### Alternatives Considered
| Instead of | Could use | Tradeoff |
|------------|-----------|----------|
| New chart library for the Home statistics card | Server-drawn inline SVG/CSS (as the cycle ring and quiet dial arc already are) | No dependency, correct without script, matches the mockup, which is plain divs. Use this. |
| Dark map via a tile provider | CSS filter on the Leaflet tile pane in dark theme | No new tile source/terms, no new credits (OSM only). Needs the owner's approval of the look. |

**Installation:** none. **Package Legitimacy Audit:** no external package is recommended; slopcheck not run. Packages removed: none.

## Architecture Patterns

### System Architecture Diagram (where a Phase 68 change lands)

```
Browser (phone 360px .. desktop 1280px, EN/FR, light/dark)
   |  GET page / POST form (CSRF)
   v
routes.py ROUTES table ──> page_policy / access.py (default-deny, role x owner)  <-- matrix test: every route has a row
   |                                   |
   v                                   v
handler (app.py <=1500 lines)     console_*.py (users, fleet, lifecycle, pairing, locations)
   |
   v
pages/*.py builders ── ui_* catalogue helpers ── layout.page_shell (ui_shell.py: frame notice strip, tab bar, More sheet)
   |                                   |
   |                                   v
   |                            i18n.msg + i18n_fr/<area>.py (EN next to code, FR module)
   v
HTML  + <link style.css?v=hash> + <link style-<area>.css?v=hash> + <script ...js?v=hash>
   |
   v
render_baseline.json (byte-equal capture of 19 paths x en/fr x light/dark + 97 unauthenticated route records)
```

### Recommended structure for new code
```
companion/pages/home_stats.py        # D-03 statistics card builder (keeps home_page.py < 1500)
companion/pages/home_recent_strip.py # D-03/R02 preview strip
companion/pages/airline_known_rows.py# D-15 read-only "known by name" rows; R27 compact rows
companion/pages/fleet_frames_list.py # R13/R15 frames list (if the owner approves a list instead of the dropdown)
companion/static/style-*.css         # area sheets; style.css only for shared tokens/shell
.planning/.../68-MOCKUP-<area>.html  # one mockup per visual change, approved before code
```

### Pattern: one fix, one place
`ui_shell.frame_notice_html` is the single builder of the foreign-frame strip for every device-scoped personal page; `style.css` `.frame-notice*` is its single style. R12 and R35 are both changes to this builder, so do them in one plan.

### Anti-patterns to avoid
- **Editing `app.py`:** it is at 1493 of 1500 lines. Any handler change must be net -0 lines or move code out first. R12, R23, R26 and R32 do not need `app.py` edits (see below). [VERIFIED: `wc -l`]
- **Testing source text:** `companion/test_suite_guards.py` fails a test that reads production source, `.planning/` files, or greps the served stylesheet text instead of parsing it (G11). Assert served HTML via `parse_html`, computed style or geometry in a browser.
- **New raw `<button>`:** an un-classed submit button falls to the legacy 30px rule; use `.btn` (44px).
- **Hand-built `banner__pill`** (D-14) in new code; use the catalogue helper.
- **A duration literal in CSS:** `test_companion_app_04.py` enforces the motion-token budget.
- **Comments with plan/phase/decision IDs:** `scripts/check_comment_history.py` fails CI.

## Don't Hand-Roll

| Problem | Don't build | Use instead | Why |
|---------|-------------|-------------|-----|
| Dialogs, sheets, leave dialog | New overlay code | `ui_modal.py` + `modal.js`, `ui_save_bar.py` | Focus, Escape, scrim, no-script `:target` floor are already solved and tested. |
| Filter field and chips | New filter script | `ui_filter.py` + `list-filter.js` (already on Users, Audit, Editor table) | R29's filter is an existing component; adding it to the Editor is wiring. |
| Copy to clipboard | New handler | `copy-button.js` (`data-copy-value`) | Already has execCommand fallback and feedback text. |
| Status dots / pills | Hand-built spans | `frame_status.status_dot_html`, catalogue `pill_html` | D-14. |
| Charts for Home statistics | A chart library | Inline server-drawn SVG/CSS | No dependency; mockup is plain markup. |
| Dark map | A second tile source | CSS filter on Leaflet tile pane in dark | Keeps one tile source and one attribution. |

## Per-Remark Map

Notation: P = page builder, C = CSS, J = script, S = i18n module (`companion/i18n_fr/`), T = tests likely to change or be added. All "browser tests" are Playwright files marked `pytestmark = pytest.mark.browser`. "BASE" means `render_baseline.json` entries change (any CSS/JS version hash or markup change on a captured page: `/`, `/airlines`, `/display*`, `/fleet*`, `/flights`, `/login`, 404, each in 4 variants). Any `style.css` edit changes every one of the 76 captures. [VERIFIED: baseline path list, sample head markup]

### Group A - Frame page, Fleet (R11 to R15, R35, D-04, D-06)

Facts [VERIFIED: code read]:
- The frame page is `GET /fleet?frame=<id>&tab=state|settings|access` built by `console_fleet_view.page_html`/`frame_html`. Sections: State (`health_page.frame_state_html`), Device and version (`update_page.render_parts`), Settings (`config_page.render(... embedded=True)`), Access (`co_managers_card.access_rows_html` + retire row), then **Other frames** (`others_block`, pending and retired frames). Phone shows one section at a time through `fleet-tabs` (`CSS style-admin.css` ~915-950); desktop shows all.
- **R13 selector:** the top-bar "frame menu" (`frame_menu.console_menu_html`) is a native `<details>` popover of every frame (problems first), then System and Add a frame. It scales badly because it is one flat list in a popover.
- **R15/D-04 cause:** `others_block(view.rows)` is rendered inside **every** frame's page (`frame_html`) and lists all non-live frames, retired included, plus the frame menu lists retired frames too (`device_scope.console_frame_entries()` returns every frame). So the page of frame X lists retired frame Y. It also explains the Phase 64 screenshot ("Le Petit Cadre", "Anciennement ...").
- **R12/D-06 cause:** `ui_shell.frame_notice_html` hardcodes `_FLEET_HREF = "/fleet"`; `console_fleet_view.selection` falls back to the first frame when `?frame=` is absent. Fix: `href = "/fleet?frame=<current device id>"` from `device_scope.current_device()` (a validated id from the scope, never request text). No `app.py` change. The existing browser test `test_fleet_to_a_foreign_frame_and_back` asserts `re.search(r"/fleet$", page.url)` and must change to assert the frame is selected on return. [VERIFIED: test file read]
- **R35 (today):** `.frame-notice` is a `--color-secondary` strip, in the content flow (scrolls away), text at label size, "Viewing X's frame" plus a text link "Back to Fleet" (`style.css` ~2244; `ui_shell.py` 373-480; FR in `i18n_fr/nav.py`). It is emitted only for an administrator on a personal page of a frame they neither own nor co-manage (`device_scope.foreign_frame_owner_email`). `ui_shell` also holds the first frame for it with `<link rel="expect" href="#...">` (`strip_expect`), so keep an element id marker if the markup changes.
- **R11 phone toggles:** State/Settings/Access content is the old Health/Device/Manage-access content embedded; the "toggles" are the Settings switch rows (`config_page` embedded, `value-controls.js`, `dirty-state.js` dirty bar) and the `fleet-tabs` segmented control. [ASSUMED: which toggles the owner means; ask with the mockup.]
- **R14 Access text:** copy lives in `co_managers_card.py` (+ `i18n_fr/co_managers.py`, `admin_fleet.py`); the Reassign/Retire sentences (`_RETIRE_SENTENCE`, `_REASSIGN_SENTENCE`, hints) are in `fleet_page.py`.

Files:
- P: `console_fleet_view.py` (303), `pages/fleet_page.py` (453), `frame_menu.py` (224), `pages/co_managers_card.py`, `pages/health_page.py` (1152, only `frame_state_html`), `pages/config_page.py` (embedded), `ui_shell.py`, `device_scope.py`.
- C: `style-admin.css` (2021, tracked size exception), `style-c-console.css`, `style.css` (`.frame-notice`, `.frame-menu`, `.frame-row`).
- J: `modal.js` (menu Escape/outside tap), `dirty-state.js`, `value-controls.js` (only if toggles change).
- S: `nav.py`, `admin_fleet.py`, `co_managers.py`.
- T (affected): browser: `test_browser_admin_personal_scope`, `test_browser_fleet_page`, `test_browser_fleet_sections`, `test_browser_fleet_tabs`, `test_browser_fleet_dialogs`, `test_browser_console_fleet_view`, `test_browser_console_groups`, `test_browser_frame_menu`, `test_browser_device_selector`, `test_browser_row_menu_reach`, `test_browser_access_sheet`, `test_browser_contrast_edges`, `test_browser_overhaul_steps`, `test_browser_overhaul_sweep`, `test_browser_page_opening`, `test_browser_fleet_dirty_bar`, `test_browser_round8_fixes`. Unit: `test_console_fleet_view`, `test_console_fleet_page`, `test_admin_personal_scope`, `test_personal_space_parity`, `test_frame_switcher`, `test_frame_sheet`, `test_device_selector`, `test_co_managers_page`, `test_audit_co_manager_detail`. BASE: `/fleet`, `/fleet?flash=saved`, `/fleet?view=system`. Access matrix unchanged if the frame list is a query on `/fleet` (no new route). A frame list as a new route would add a matrix row.

Suggested design direction (owner decides, mockup first): `/fleet` with no `frame` shows a list of frames (cards or rows with status, owner, last seen; pending and retired in their own groups) and `?frame=<id>` opens the frame page with a compact "all frames" switch (a horizontal chip row or a back link to the list) instead of the dropdown. This answers R13 (scales), R15 (retired frames only in the list) and D-04 (the page names its frame in its header). Note that changing the default of `selection()` from "first frame" to "list" changes the `/fleet` baseline and tests that assume the first frame.

### Group B - Update panel (R16, R17)

- R16: the Device and version card and the version list are `pages/update_page.py` helpers (`_on_the_frame_html`, `_cta_card_html`, `_versions_group_html`, `_history_row_html`, `_summary_html`; 979 lines), CSS `update-*` classes in `style-admin.css`, FR in `i18n_fr/update.py`. The standalone `/update` page keeps older markup (skill "CSS debt"); decide whether the rework also retires it.
- R17: the page after Install is `update_install_confirm_page` (two-step confirm, rendered by `app._handle_update_install_post` when `confirm != "yes"`); after the confirming POST the result is a redirect with a flash. "Revert" goes through the same confirm page. So R17 is the confirm page (a bare `page_header` + paragraph + unstyled button + text link), not a new route. No `app.py` change needed: restyle the builder.
- T: `test_browser_update`, `test_browser_firmware_panel`, `test_update_page`, `test_update_page_non_live`, `test_update_actions`, `test_access_matrix` (routes unchanged). **Golden file:** `companion/testdata/update_page_one_type_golden.json` is compared byte for byte by `test_one_type_page_is_byte_identical_to_the_recorded_render` for the standalone page and the confirm page (EN/FR). Any change to `update_page()` standalone markup or `update_install_confirm_page` requires regenerating that file from `test_update_page.one_type_golden_pages()`; there is no `--write` CLI, so the plan must add a small throwaway script or an explicit regeneration step, and the owner's rule "one-hardware-type page is byte-identical" is re-stated as "identical to the newly approved render". [VERIFIED: test read]

### Group C - Users (R25, R26) - see Behaviour Traces

- R25 files: `pages/users_page.py` (invite dialog `_invite_dialog`, role confirmation `_role_dialog`), `ui_modal.py` (shared dialog frame), `style-admin.css` (`.users-*`) and the shared `.modal*` rules in `style.css` (~6195-6520). Careful: `.modal` margins are shared with every dialog; scope the change with a modifier class or the change widens (affects Fleet dialogs, quiet-hours, leave dialog). Keyboard covering the field: `modal.js` (scroll the focused field into view, `visualViewport`) [ASSUMED: JS not yet read for this].
- T: `test_browser_users_page`, `test_browser_users_rows`, `test_browser_users_cards`, `test_browser_fleet_users_fixes`, `test_browser_delete_user_remove_frame`, `test_console_users`, `test_console_users_delete`, `test_ui_modal`, `test_browser_motion_sheets`, `test_browser_one_toast_one_sheet`.

### Group D - Airlines editor (R27 to R31, D-15) and user Airlines (R04b, R05)

- Editor = `/airlines/manage` (admin), `pages/airlines_page.py` (**1287 lines**), `pages/airline_table.py` (580), `pages/airline_sheet.py` (116), `airline_actions.py`, `resolve_dialog.py`, `style-airlines.css` (973), `list-filter.js`, `airline-types.js`. User Airlines = `/airlines` (`airline_collection_page.py`, 511, `airline_collection.py`), same CSS file. Nav label "Editor".
- Budget: `airlines_page.py` has 213 lines of room. D-15 (known-by-name rows), R27 (Complete/Edit/Rename flows) and R29 (compact rows, filter) must go into new modules (`airline_known_rows.py`, etc.), not into `airlines_page.py`.
- T: `test_airline_editor`, `test_browser_airline_editor`, `test_browser_airline_table`, `test_browser_airline_helpers`, `test_airline_manage_routes`, `test_airline_sheet`, `test_airline_collection(_page)`, `test_browser_airline_collection`, `test_browser_resolve_buttons`, `test_health_resolve_dialog`, `test_browser_ux_04`, `test_status_pages_04/05b/06/07`, `test_view_pages_02..04`, `test_csrf`, `test_post_origin`, `test_access_matrix`. BASE: `/airlines` (user collection).
- D-15 data: names known without artwork are in `_ICAO_AIRLINE_NAMES_WITHOUT_ARTWORK` (`server/plane/enrich.py`). Read-only rows need a read accessor for that table (server file; this is the only item that touches `server/`). Phase 65 is closed on main; enrich.py was changed by #468 (VRS), so re-read after merging main. Phase 64-owned companion files that D-15 touches: `airlines_page.py`, `airline_table.py` (verify with `git log`; both last changed in Phase 61 and PR #453/Phase 64 label work).

### Group E - Account, sign-in, 404, pairing, credits (R18 to R24)

- R18 pair refusal wording: `fleet_page.claim_refused_error`, `user_pairing.py`, `pages/pair_frame_page.py`, `pair_code_cookie.py`, `console_pairing.py`; FR `pair_frame.py`, `admin_fleet.py`. T: `test_user_pairing`, `test_browser_user_pairing`, `test_console_pairing`, `test_refused_post_sign_in`.
- R19 "Manage access" row action, R20 battery as dot only, R21 hide hardware for admin: `pages/account_page.py` (`_frame_action_html`, `_frame_detail_html`, `_frame_line(show_hardware)`; `show_hardware = identity.role == ROLE_ADMIN` in `render`). R20: `frame_status.status_dot_html` and the FrameSummary carries `battery_percent`; the Account row text comes from `_frame_detail_html` (status dot + "Seen ..."). Check where the percentage is printed before removing. T: `test_account_page`, `test_browser_account_frames`, `test_co_managers_page`. FR `account.py`.
- R22 "First visit" block and R23: `login_page.py` (`_login_card_html`, `FIRST_VISIT_HINT_TEXT`, `render_login_page`), `layout.login_shell`; T: `test_sign_in_surfaces`, `test_sign_in_messages`, `test_sign_in_cancelled`, `test_auth0_login`, `test_browser_auth0`, `test_landing`; BASE `/login`.
- R24 404: `login_page.not_found_page` (+ `app._not_found_page`), `.error-actions` CSS; T: `test_status_pages_*`, `test_server_error_page`; BASE `/this-page-does-not-exist`. "More fun" must stay inside the design system: an inline SVG illustration on the existing glass card, no new asset or font.

### Group F - Home (D-03, R01, R02), Flights (R03, D-05, D-08), Style (R06, D-07, D-10), Location (R07 to R09)

- Home: `pages/home_page.py` (775), `home_title.py` (rename pencil), `home_battery_row.py`, `home_notice.py`, `detection_summary.py`, `style-home.css`, `freshness.js`, `relative-time.js`, FR `home.py`. R01: the "i" is `_cadence_info_html` (`info-tip__button`, `style.css`), the pencil is `ui_components.icon_link_html` in the title row. D-03 is a rebuild: hero card with preview, pills (Screen switch, quiet-hours opener, place link, battery pill), Day/Week statistics card, preview strip. **The statistics card is new data**: there is no per-hour or per-day flight count query in `server/history_db.py` (existing aggregates: `route_source_counts`, `corroboration_counts`, `daily_battery_averages`), so `history_db` gets read-only aggregate functions (hours of today with arrival/departure, 7 daily totals, most-seen airline, new airlines). It is a read path with no schema change; flag it to the owner since "daily activity belongs to Health" today. R02 is the mockup's preview strip: reuse the Flights thumbnail rule (render counts only if archived at most 90 s before and 10 s after the detection; `GALLERY_MATCH_BEFORE_S/AFTER_S` in `history_page.py`) so Home and Flights agree; the fallback chain is airline illustration, then plane chip.
  T (rewrite): `test_browser_home_state_card`, `_detection_card`, `_battery_row`, `_notice`, `_title`, `_header_landscape`, `_recent_tiles`, `_signature`, `test_home_state_card`, `test_home_detection_card`, `test_home_notice`, `test_home_recent_tiles`, `test_home_title`, `test_display_detection_card`, `test_browser_frame_preview_shape`, `test_browser_empty_state_scale`, `test_browser_perf_*`, `test_browser_motion*` (ambient rest). BASE `/`. Quiet-hours dialog (`settings/quiet_hours.py`, `value-controls.js` dial) must remain; D-12 (quiet-hours link 44px) disappears into the mockup's pill if it is kept as a pill.
- Flights: `pages/history_page.py` (1128), `history_fragment.py`, `history_query.py`, `history_cache.py`, `style-flights.css` (207), FR `flights.py`. R03 removes the "departing/arriving" words (direction stays drawn and spoken, per the a11y rule "Flights direction is spoken as well as drawn": keep the `visually-hidden` text); D-05 header search wrap. T: `test_flights_cards`, `test_flights_fragment`, `test_flights_search_sort`, `test_flights_unshown_rows`, `test_browser_flights_cards`, `_card_height`, `_search_more`, `_stand_in`, `test_history_cache`, `test_history_shared_fold`. BASE `/flights`. D-08 naming: tab label vs page title lives in `nav.py`/`flights.py` strings and `ui_base.NAV_SHORT_LABELS`; owner chooses EN+FR words (`test_nav_*`, `test_i18n`, `test_browser_french_fit`).
- Style: `settings/layout_picker.py`, `settings/look.py`, `pages/personalisation_cards.py`, `theme_preview.py`, `preview_images.py`, `theme-preview.js`, `ui_save_bar.py`, `dirty-state.js`, `modal.js`, `style-display.css`. R06 leave dialog: `test_browser_style_leave`, `test_browser_leave_dialog_pages`, `test_browser_save_bar`. D-07: Style tabs are separate routes (`/display`, `/display/arrivals`, ...), so a tab switch is a full navigation (page-crossfade view transition) and each tab's previews are `<img>` URLs from `theme_preview.frame_preview_src(...)` served with `cache_seconds=300`. Hypotheses to test first: (a) the picture URLs differ per tab (state/layout query) so nothing is shared; (b) the browser revalidates on navigation; (c) previews are lazy-loaded and re-decoded. Investigation task: browser test counting image requests per tab change and comparing URLs. [ASSUMED: root cause not determined; needs the Wave-1 investigation.] T: `test_preview_cache`, `test_theme_preview_layout`, `test_theme_preview_profile`, `test_browser_theme_switch`, `test_browser_picture_loading`, `test_browser_personalisation*`, `test_browser_display_looks`. BASE `/display*`. D-10 (yellow contrast 1.12) is a theme-picker swatch/preview pair: `test_contrast_check`, `test_sky_contrast`, `test_browser_contrast_edges`; needs a real-device check by the owner (cannot be closed by tests).
- Location: `pages/place_page.py` (1015), `place-*.js` (`place-map.js` 1227), `style-place.css` (1771, tracked exception). R07: the "Position found (about %d m). Check the pin, then save." string (`detection.located`, `place_page.py:124`) is shown after the locate button; remove it and keep the pin move plus the Save bar as the signal (the live region needs a spoken equivalent: keep the text as `visually-hidden` `role="status"`). R08: dark theme copies the light palette over the map (known CSS debt); proposal CSS filter on the tile pane in `html[data-ui-theme=dark]` plus the Auto-dark media query, with the runway overlay recoloured; verify that the overlay is what the owner calls "white runway line" [ASSUMED]. R09: action buttons to icon-only, same space (`.btn` 44px targets, accessible names). T: `test_browser_place_*` (14 files), `test_browser_location_full_bleed`, `test_browser_location_polish`, `test_place_page`, `test_place_save`, `test_location_picker`, `test_browser_web_app_bar`. iPhone standalone behaviour of the map is hand-verified by the owner (`test_browser_place_pins`).

### Group G - Shell and navigation (R04, R10, R23, R34, D-08, D-09, D-11, D-12, D-13) and Console (R32, R33)

- R04 order: `ui_nav._PERSONAL_SIDEBAR_PAGES = (Home, Flights, Place, Style, Airlines)` versus `_PERSONAL_BAR_PAGES = (Home, Flights, Airlines, Style, Place)`. One table for both fixes the "different order" and `navigation.md` already documents the bar order. T: `test_browser_nav_alignment`, `test_nav_spaces`, `test_browser_nav_spaces`, `test_browser_tab_bar_roles`, `test_user_nav`, `test_nav_personal_console`, `test_personal_space_parity`.
- R10 (More sheet in Safari): the sheet panel is opaque (`--glass-solid`); only the **scrim** blurs (`body:has(.tab-bar__more[open])::after`, `backdrop-filter: blur(8px)`, `style.css` ~5886). The scrim uses `:has()`; Safari supports `:has()` since 15.4 and `-webkit-backdrop-filter` is declared, so a difference between Safari and the Home Screen app is not explained by the CSS. It must be checked on the owner's iPhone (the skill already lists the "More-panel dim on every tab" as pending validation). [ASSUMED: no source-level cause found; LOW confidence.] Treat as a verification checklist item, not a code task, unless the owner's screenshot shows otherwise.
- D-09 width on tablet, D-11 grab handle (`.tab-bar__grab`), D-13 active tab tap: `style.css`, `motion.js`/`prefetch.js`/`modal.js`; T: `test_browser_more_sheet`, `test_browser_more_panel_redesign`, `test_browser_more_scrim_cover`, `test_browser_tab_bar_tablet_cap`, `test_browser_tab_bar_float`, `test_browser_tab_pill_transition`, `test_browser_hit_area_settle`.
- R34 label: `ui_nav._PERSONAL_LABEL = "My frame"` (FR "Mon cadre") is the Console More row that switches to the personal space (`_switch_row_html`). Owner picks "Mon compagnon" or "Mes cadres" and the EN equivalent. "Changing space: no jump matters on mobile" is read as: switching space must not move the tab bar/scroll position; check against `test_browser_space_switch`, `test_space_switch`. [ASSUMED reading; ask the owner.]
- R33 Audit: `pages/audit_page.py` (355), `ui_filter.chip_links_html(... tabs="audit")`, `style-c-lists.css`; opened toggles = `<details>` rows (`ul.audit-cards`). T: `test_browser_audit_page`, `test_console_audit_page`, `test_audit_co_manager_detail`, `test_browser_console`.
- R32: see Behaviour Traces.

## Behaviour Traces

### R02 - flight preview on recent flights (Home)
Today `home_page._recent_flight_row_html` shows an icon row with no picture. The approved mockup has a strip of previews (`figure` with the e-ink render and a caption "Arrival - 12 min"). Reuse the Flights thumbnail data (archived render within 90 s before / 10 s after the detection, name stored per flight, else airline illustration, else plane chip) so there is one source of truth; do not render previews on the fly. Test: Home with seeded flights having a matching archived render shows an image in the strip; one without shows the fallback; the strip works with scripts blocked; EN/FR captions. [VERIFIED: page-patterns.md and home_page.py read]

### R23 - credits unreachable once signed in
`/credits` is a PUBLIC route and already renders "Back to Account" or "Back to Home" for a signed-in visitor (`credits_page._back_link_html`, `app._back_target`). The only link to it is on the login card (`login_page.render_login_page`). So the missing piece is an entry point for signed-in people. Options: a "Credits" row on the Account page (reaches non-admins, whose tab is Account, and administrators, whose More sheet has an Account row) and a quiet link in the desktop sidebar footer. Recommend the Account page row (one place, no nav change, no route/matrix change). Credits in the Place map popover exist for map data only. Test: Account page contains a link to `/credits` for user and admin; following it shows "Back to Account"; EN/FR. [VERIFIED: code read]

### R26 - invitation and first sign-in today (Auth0, no password)
Trace [VERIFIED: `console_users.py`, `users_page.py`, `sign_in.py`, `fleet_sessions.py`, `login_page.py`, `deploy/README.md` "Sign-in (Auth0)", SEED-011, SEED-012]:
1. `POST /users/invite` (`console_users.handle_invite`): validates e-mail and role, `fleet_db.add_user(conn, email, role)` and an audit row `user.invite`, in one transaction, then a flash "Invited ... Tell {email} to sign in with this address." **No e-mail is sent and no Auth0 call is made.** The row has no `iss`/`sub` (not linked). Status "Invited, not signed in yet".
2. The copy control on an invited row (`users_page._invite_cell`, `copy-button.js`) copies **a text message**, not a link: "Hello, you have been invited to SkyPane. Open {app_url} and sign in with {email}." (`app_url` derived from the Host header, validated by `_HOST_RE`). On a phone it is a labelled full-width button; from 79.5 rem (the desktop table) it is icon-only (`.users-copy`, 44 px, label visually hidden). The owner saw a copy icon and no link: matches. It carries no secret.
3. The person opens the app, `/login` shows "First visit? Use the email address you were invited with." and a Sign in link to `GET /login/auth0` (PKCE authorization-code flow, `oidc.authorize_url`).
4. Auth0 Universal Login authenticates. The tenant is configured with **sign-ups disabled and no social connection** (`deploy/README.md` step 4; Phase 54 handoff). So a person with no existing Auth0 account **cannot create one** at that screen.
5. On `/callback`, `fleet_sessions.sign_in_user` resolves: an identity already linked (`iss`,`sub`) wins; otherwise `email_verified` must be `true`, else refusal `unverified_email`; then the local row with the same normalised e-mail, not disabled and not yet linked, is linked (`UPDATE users SET iss, sub`), a session is created, and the person lands on Home or Account with a welcome flash. Any other case is the "not invited" refusal page.

Real first-sign-in path today: the administrator creates the Auth0 user by hand in the Auth0 dashboard (e-mail verified), the person sets a password through Auth0's password-change/verification mail, then signs in with the same e-mail. This manual step is what the owner is asking about. It is recorded as SEED-012 ("Make the admin invite create the Auth0 account and send the invitation", dormant, target v1.4) and SEED-011 (distinct unverified-e-mail message, already handled in code: `unverified_email_page`).

Options for the owner (R26 needs a decision before any change beyond removing the misleading control):
- **Option A, minimal (recommended for this phase):** keep the flow; remove or rename the control so it is honest (the owner asked to remove it; alternative is to keep it with a visible label "Copy invitation message" on every width and a preview of the message in the invite-success toast), and make the manual step explicit: after "Invite user" the confirmation says what the administrator must still do (create the Auth0 user, verified) and `deploy/README.md` keeps the checklist. No Auth0 call, no new secret, no matrix change. Scope: `users_page.py`, flash text in `console_users.py`, FR `admin_users.py`.
- **Option B, Auth0 sends the invitation (SEED-012):** the companion calls the Auth0 Management API with a machine-to-machine credential: create the user on the database connection and request a password-change ticket (`POST /api/v2/tickets/password-change`, which accepts `mark_email_as_verified`) so the first sign-in links without a separate verification step. Adds a second Auth0 secret in `skypane.env`, failure handling (local invite must not be left half created), audit of the outcome, tests against `test-support/fake_auth0.py`. It is new behaviour with a security impact (Phase 66 would audit it) and the seed already targets v1.4; recommend deferring unless the owner wants it now. [CITED: auth0.com/docs/api/management/v2/tickets/post-password-change; details on creating the user with verified e-mail not verified, see A3]
- **Option C, let the invited person self-register in Auth0:** enable sign-ups on the database connection with Auth0's e-mail verification. The local invite still gates access (default-deny: an unknown e-mail gets the "not invited" page, an unverified one the verification page), so no companion code changes, and the first-visit hint becomes accurate ("Sign in, or create your account with the invited address"). Trade-off: the tenant then lets anyone create Auth0 accounts (no access to SkyPane without a local invite), which reverses the README's "disable sign-ups" rule and must be an explicit owner/security decision recorded for Phase 66. [ASSUMED: tenant setting and Universal Login "Sign up" tab behaviour.]
- Passwordless e-mail code (Auth0 passwordless connection) is a variant of C for "no password" but changes the `oidc` flow's connection and is a larger change; not recommended here. [ASSUMED]

### R28 - the "ignore" action on unidentified airlines
`airline_table._gap_group_html` renders the unidentified-prefix row as a form with a name field, an optional default aircraft type, **Validate** (submit) and **Ignore**, which is `ui_components.button_html(..., button_type="reset")`: it only **clears the form fields client-side**; nothing is stored and nothing is hidden. So server-side, "ignore" does not exist; the owner's "an ignored airline can no longer be edited" is not reproduced by this code path. Possible causes: a stale state after reset (the `required` name field and `data-autosubmit` handlers in `airline-types.js`/`list-filter.js`), or the row collapsing in the phone layout. [ASSUMED: cause unconfirmed; needs a browser reproduction on the owner's screenshot.] Recommendation: delete the Ignore button and its strings (`airlines.resolve_ignore` EN and FR), keep Validate; unidentified rows stay until resolved. No route, no matrix, no persistence change. Tests: `test_browser_airline_editor` (no Ignore control; Validate resolves the row in place), `test_airline_editor`/`test_health_resolve_dialog` (unchanged resolve route), `test_i18n` (removed id has no orphan French). The "Skip - I'll add artwork later" link of the add-airline step (`airlines_page.STEP_B_SKIP_TEXT`) is a different control; do not touch it.

### R30 - "Revert to default" with no default illustration
In `airline_table`: for an aircraft-type sub-row, `_sub_action_html` shows **Back to the default** (`_delete_art_form(delete=False)`, `MENU_REVERT`) whenever the type has an uploaded override, else **Customise** (`ACTION_CUSTOMISE`, which is `_change_art_form`, the same file-upload control as the menu item **Change artwork** `MENU_CHANGE_ART`); the type menu also offers Delete the illustration (`delete=True`). The docstring of `_delete_art_form` says "Back to the default" and "Delete the illustration" are the same change worded two ways, which is exactly the owner's confusion. The default is "the vendored picture, else the airline's own, else the generic one". Since the owner supplies every image, no vendored default exists; reverting falls back to the airline picture or the generic illustration. Recommendation (to confirm with the owner): one upload entry named **Change illustration** (drop **Customise**), and one removal entry named **Delete the illustration** shown only when an uploaded picture exists; show **Back to the default** only when a vendored (`has_builtin`) picture exists beneath the override. Needs `sub["has_builtin"]` semantics verified against `illustrations` (36 curated airlines have vendored artwork; type sub-rows may not). Tests: menu items per state (own artwork / airline artwork only / vendored), no duplicate upload entry; `test_airline_manage_routes` unchanged (same two POST routes). [VERIFIED: code read; policy ASSUMED]

### R32 - Locations page
Today [VERIFIED: `console_locations.py`, `console_routes.py`, `routes`]: `GET /locations` is ADMIN_ONLY and answers a fixed redirect to `/fleet`; the nav entry is gone (the comment in `console_routes.py` says "The Locations page is gone; the label still titles the page a refused location submission re-renders"). What survives: `POST /locations/add` (SIGNED_IN, csrf, admin and user, user cap 10 per user, throttle), `POST /locations/{id}/edit`, `POST /locations/{id}/delete`. A refused add or edit (validation 400) re-renders the full Locations page through `console_locations._render` (console shell for an administrator, plain shell for a user). **No page in the app posts to these routes** (`locations_page.py` is the only form builder and is only reachable through those renders; the Place page saves through `action=save_place` on its own route). The `locations` table is still used by detection (`detection_actions.py`: `list_locations_for`, `get_location`, `location_id` form field), so the table stays.
Removing the page and the three POST routes means:
- Delete: `console_locations.py`, `pages/locations_page.py`, `i18n_fr/admin_locations.py`, `test_console_locations.py` (595 lines, 34 tests), `test-support/matrix_rows_locations.py`, the `"/locations": ("admin",)` entry in `page_styles.py`, `LOCATIONS_*` in `console_routes.py` and the import, `LOCATIONS_LABEL`/`nav.locations` (check `test_i18n` for orphans), `console_routes.ROUTES` concatenation.
- Matrix and route table: `companion/test_access_matrix.py` (imports `matrix_rows_locations` twice), `test_route_table.py` (lines 39-40, 111-113: the POST shapes and the "signed-in routes" test whose name lists locations) change; the unauthenticated half of `render_baseline.json` loses the 4 `/locations*` records and must be regenerated. This **does** change the route table and the matrix; the phase's criterion 5 ("matrix unchanged") must be read as "unchanged except the owner-requested removal"; record that in the plan and the summary.
- Behaviour after removal: `/locations` and `/locations/*` answer the standard 404 (like any unknown path); tests should assert the 404 for GET and POST for admin, user and anonymous, and that Place/detection saving still works (`test_place_save`, `test_detection_page`).
- Remaining references to keep: audit target kind `"location"` in `console_lifecycle.py:283` (old audit rows still render), `test_user_view_http`/`test_nav_personal_console`/`test_user_nav`/`test_browser_console` references (update to 404).
- Coverage: deleting a module and its 34 tests lowers covered and total lines together; check `fail_under = 93` still holds. Check `test_browser_empty_state_scale`, `test_empty_state_scale`, `test_browser_overhaul_sweep`, `test_account_page` which mention locations.
Alternative (smaller): keep the POST routes and make a refused POST redirect to `/fleet` with a flash instead of rendering the page. Not recommended: it keeps dead, unreachable endpoints on a phase that precedes the security audit.

### R29 filter
`ui_filter.py` + `list-filter.js` (978 lines) already power the Users, Audit and Editor tables (`data-filter-text`, `data-filter-group` appear in `airline_table`); the editor already emits `data-filter-text` per row and group. The filter field for the Editor is therefore wiring plus a design (placement above the table; chips for All / Unidentified / Named by hand / Own artwork). "Marchand" is unclear in the owner's note (possible "Marque", "Marchands", or a mistyped label): ask. Slowness on expand: each airline group renders its type sub-rows in the table (`types_open`, `TYPES_PARAM`) and `airline-types.js` loads fragments lazily; measure before optimising (rows are server-rendered for every airline). [ASSUMED]

### R35 and R12 marker
See Group A. Design fit: build the marker as a full-width **sticky** banner directly under the app bar (below it on a phone, top of the content area on desktop), using accent-filled surface (graphite in light, ivory in dark, on-accent text) or the warn tone via `ui_components.anomaly_banner(..., "warn")`; icon (eye or person) + "Viewing {email}'s frame" at 15-16px (not caption) + a 44px "Back to Fleet" `.btn` that returns to `/fleet?frame=<id>`. Keep the element id for `rel="expect"`, keep a text equivalent for screen readers (`role="status"` is not needed; it is static landmark text), keep contrast checks (accent vs surface is already enforced; warn-as-text on white is 3.19:1 and is an accepted exception only for non-body text, so prefer the accent fill). Add the pattern to `components.md` and the Components page (`pages/components_page.py`, whose `test_components_page` and `test_browser_components_page` enumerate components, EN and FR). T: `test_browser_admin_personal_scope` (font-size 15px assertion, height >= 44, hit target, nav carries the frame prefix), `test_browser_overhaul_sweep`, `test_personal_space_parity`, `test_admin_personal_scope`.

## Common Pitfalls

### Pitfall 1: Baseline churn from parallel plans
**What goes wrong:** two plans each regenerate `render_baseline.json`; the second overwrites or conflicts, or CI fails on a hash from the other's CSS.
**Why:** the baseline embeds `?v=<content hash>` of each linked CSS/JS file; `style.css` links on every page.
**How to avoid:** only one plan per wave regenerates the baseline, after all code plans of the wave merged; every other plan runs `test_render_baseline.py` expecting failure only on its own pages and does not commit the file. Treat `render_baseline.json` as a conflict file in the wave plan.
**Warning signs:** `test_render_baseline` fails with a diff only in `?v=` strings.

### Pitfall 2: `app.py` has 7 lines of headroom
Any plan that adds a handler or import to `app.py` fails `test_structure_guards`. Move code to a mixin/module first or avoid `app.py`.

### Pitfall 3: Shared `.modal` / `.frame-notice` / `.row-menu` CSS
R25, R06, R14 and Fleet dialogs share `.modal*`; changing margins globally changes the leave dialog, quiet-hours, role confirmation and Fleet sheets. Scope with a modifier class.

### Pitfall 4: French fit and i18n tests
Each new string needs `i18n.msg("<id>", "<EN>")` plus a French entry in the matching `i18n_fr` module (`test_i18n`: every id has French; no stray `%s`/`{}`); French uses sentence case, U+2019, U+00A0 before `:;?!`. `test_browser_french_fit` checks 360px. Removed strings (Ignore, the "Position found" line, Customise) must leave no orphan French id.

### Pitfall 5: 44px and `.btn`
Icon-only buttons (R09, R01) still need a 44px hit area, an accessible name and a French name; `test_browser_overhaul_sweep` hit-tests content at 360 and 1280.

### Pitfall 6: Behaviour-over-source guard
No test may read source files or `.planning/`, or regex the served CSS text; assert via served HTML (`parse_html`), computed styles or geometry in a real browser (`new_context`/`page` fixtures from `companion/conftest.py`).

### Pitfall 7: Function and file size gates
Max 80 code lines per function and 1500 lines per production file (CSS exceptions listed in `test_structure_guards`: `style.css`, `style-admin.css`, `style-display.css`, `style-place.css`). Near-limit: `app.py` 1493, `airlines_page.py` 1287, `place-map.js` 1227, `health_page.py` 1152, `history_page.py` 1128, `motion.js` 1089, `place_page.py` 1015, `list-filter.js` 978, `update_page.py` 979.

### Pitfall 8: Branch is behind main
`phase-68-visual-improvements` lacks main's Phase 65 closing commits (server and docs; no `companion/` diff) and the "Route sources" candidate in `68-CANDIDATE-ITEMS.md`. Merge main before the first code plan so that `server/plane/enrich.py` (needed for D-15) is current.

## Parallel Work: Phase 64 and 65 file overlap

[VERIFIED: `git log origin/main`, `gh api pulls?state=open` returned 0 open PRs on 2026-11-18, `git diff HEAD origin/main -- companion` is empty]
- **Phase 64** companion changes are all on main already (PRs #403, #413, #416, #430, #432, #434, #439, #445, #450, #451, #453). No open PR and no live branch carries companion changes (the `gsd/quick-*` branches are squash-merged). Files Phase 64 changed that Phase 68 touches: `pages/update_page.py` (#430), `pages/fleet_page.py` and `ui_modal.py` and `style-admin.css` (#451, #434), `ui_nav.py` and nav tests (#450, #453), `style-home.css` and `pages/home_page.py` (#445, #439), `device_scope.py`, `settings/layout_picker.py`, `settings/theme.py`, `settings/calendar.py`, `style-display.css`, `style.css` (#439), `i18n_fr/{airlines,common,nav,admin_fleet,look}.py`, `routes.py`/`export_api.py` (#413), `testdata/render_baseline.json` (nearly every PR). Phase 64 is "verified with open points" (criterion 7 hardware, not companion), so a new Phase 64 PR on those files is possible but none is open. Say so in each plan before touching them (D-15 asks for it) and re-check `gh api` for open PRs at each wave start.
- **Phase 65** (detection, closed on main by #470) changes `server/` only (`enrich.py`, `poll_cycle.py`, `runway_config.py`, VRS routes, tests, docs, scripts). Overlap with Phase 68: `server/plane/enrich.py` for D-15, nothing in `companion/`. The Phase 68 branch must merge main to see it.
- Any other session editing `render_baseline.json` or `style.css` is the real conflict risk; the wave rule in Pitfall 1 applies.

## Suggested Plans and Waves

Rule: plans in a wave touch disjoint files; `style.css`, `ui_shell.py`/`ui_nav.py`, `ui_modal.py`, `i18n_fr/nav.py` and `render_baseline.json` belong to one plan per wave. Mockup gate: every visual plan has a first task "mockup `68-MOCKUP-<name>.html` approved by the owner" (checkpoint:human-verify) before code; a mockup is a standalone HTML file in the phase directory using the design tokens (as `68-HOME-MOCKUP.html` does), EN and FR copy, phone and desktop frames, light and dark.

**Wave 0 (no visual change, one plan):** 68-01 housekeeping: merge `origin/main`; check open PRs; record the baseline regeneration command and wave rule; add an investigation test harness for D-07 (count preview image requests per Style tab change) and the R28/R10 reproduction notes; update the skill "as of" line to the current main. No baseline change.

**Wave 1 (mockups only, all in parallel; owner approves one by one):** M-A frame page and frames list (R11, R13, R14, R15, D-04) and R35 banner; M-B Update panel and confirm page (R16, R17); M-C Users dialogs (R25) plus the R26 decision; M-D Editor rows, Complete/Edit/Rename, known-by-name rows, filter, "..." menu (R27, R29, R30, R31, D-15); M-E Account, sign-in, 404, pair refusal (R18 to R22, R24); M-F Flights rows (R03, D-05) and user Airlines (R04b, R05); M-G Location buttons and dark map (R08, R09); M-H Style leave dialog (R06); M-I Audit phone navigation (R33); M-J shell items (D-09, D-11, D-13, R10 findings, R34 labels). The Home mockup is already approved (D-03).

**Wave 2 (code, parallel, disjoint file sets):**
- 68-02 Home: D-03, R01, R02, D-12 (home files, `style-home.css`, `history_db` read queries, `freshness`); BASE `/`.
- 68-03 Editor: R27 to R31, D-15 (`airline_*`, `airlines_page` slimming, new modules, `style-airlines.css`, `list-filter.js`); includes R04b/R05 only if no other plan edits `style-airlines.css` (user Airlines shares it). BASE `/airlines`.
- 68-04 Update panel: R16, R17 (`update_page.py`, `style-admin.css` update selectors, golden JSON). Shares `style-admin.css` with 68-05: give the two plans disjoint selector blocks and merge sequentially, or put them in Wave 3.
- 68-05 Location: R07 to R09 (`place_page.py`, `place-*.js`, `style-place.css`). BASE none (Place is not in the baseline list; confirm).
- 68-06 Style: R06, D-07, D-10 (`style-display.css`, `theme-preview.js`, `ui_save_bar.py` or `modal.js` only if the leave dialog needs it). BASE `/display*`.

**Wave 3 (shared-file plans, sequential):**
- 68-07 Shell and navigation: R04, R10 (if needed), R34, D-08, D-09, D-11, D-13, R23 (Account row) (`ui_nav.py`, `ui_shell.py`, `style.css`, `i18n_fr/nav.py`).
- 68-08 Frame page, Fleet: R11 to R15, R35, D-04, D-06 (`ui_shell.frame_notice_html` shared with 68-07, so after it), `console_fleet_view.py`, `fleet_page.py`, `frame_menu.py`, `style-admin.css`.
- 68-09 Users and shared dialogs: R25, R26 (option chosen), `ui_modal.py`/`.modal` scope.
- 68-10 Account, sign-in, 404, pair refusal: R18 to R22, R24 (`account_page.py`, `login_page.py`, pair modules). BASE `/login`, 404.
- 68-11 Flights and Audit: R03, D-05, R33.
- 68-12 Locations removal: R32 (matrix and route-table edits; do not run beside 68-09, which also edits `console_routes`-adjacent tests).

**Wave 4 (closing, one plan):** 68-13 regenerate `render_baseline.json` once, full suite, accessibility sweep (`test_browser_overhaul_sweep`, `test_browser_contrast_edges`), skill update (`components.md`, `page-patterns.md`, `navigation.md`, "as of"), comment-history and size gates, draft PR, owner validation on the deployed companion in EN and FR (D-19). If the baseline is regenerated per wave to keep CI green on the branch, make it the final task of each wave's last plan.

Open items that block planning until the owner answers (put as checkpoints): R26 option A/B/C; R34 label; D-08 naming; R29 "Marchand"; R32 removal vs. refusal redirect; R30 policy wording; the frame list design (R13/R15).

## Code Examples

### R12 fix shape (builder; no `app.py` change)
```python
# Source: companion/ui_shell.py frame_notice_html (current builder, read in this session)
current = device_scope.current_device()
href = "/fleet?frame=%s" % quote(current.id, safe="") if current is not None else _FLEET_HREF
```
The id comes from the request scope's own frame list, never from request text (same rule as `frame_menu`).

### Browser test shape (behaviour-over-source)
```python
# Source: companion/test_browser_admin_personal_scope.py pattern
page.wait_for_function(_OWNS_ITS_CENTRE, arg=".frame-notice a", timeout=10000)
with page.expect_navigation():
    page.locator(".frame-notice a", has_text=words["back"]).click()
assert "frame=" + seed.owned_id in page.url
assert page.locator(".fleet-detail-head").inner_text()  # the frame page names the right frame
```

## State of the Art

| Old | Current | Impact |
|-----|---------|--------|
| Hamburger / `.nav-status`, space-switch cell | One bottom tab bar, Console switch in More, Account tab for non-admin (#450) | Skill text lags; update in the same PRs. |
| Health, Device, Releases pages | Folded into the Fleet frame view; old URLs 303 to it (`fleet_moves.retired_*`) | R11/R16 rework the folded view; `/update` standalone keeps older markup. |
| Locations page | Redirect only; POST routes remain | R32 finishes the removal. |

## Runtime State Inventory (R32 removal, R34/D-08 renames)

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | `locations` table in `fleet.db` still used by detection (`devices.location_id`); audit rows with target kind `location` | None for the table (keep). Old audit rows keep rendering (`console_lifecycle.py:283`). Code edit only. |
| Live service config | None - verified: no external service references `/locations` | None |
| OS-registered state | None - verified by grep of `deploy/` for `locations` routes | None |
| Secrets/env vars | None | None |
| Build artifacts | Static files carry no `/locations` asset; Caddy config does not route it separately (not checked in `deploy/Caddyfile`; verify) | Verify `deploy/` has no explicit path rule. |
Labels: renaming "My frame"/"Flights" changes only i18n ids' texts (keep ids stable, change values) and tests that assert them; no stored data.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The "toggles" of R11 are the Settings switch rows and the State/Settings/Access segmented control | Group A | Mockup solves the wrong thing; confirm at mockup review. |
| A2 | R28's "ignored airline can no longer be edited" is not caused by server persistence (the Ignore button is a form reset) | Behaviour Traces | A JS/layout cause remains after deleting the button; needs a browser repro. |
| A3 | Auth0 lets the Management API create a user and mail a password-change ticket with `mark_email_as_verified` (ticket endpoint cited; user-creation verified flag not confirmed in docs read) | R26 Option B | Option B cost/shape changes. |
| A4 | Enabling sign-ups on the Auth0 database connection plus e-mail verification gives a working first sign-in with no companion change | R26 Option C | Tenant behaviour differs (e.g. verification required before login). |
| A5 | Passwordless e-mail is a larger `oidc` change | R26 | Could be cheaper than thought. |
| A6 | R08's "white runway line" is the runway overlay on the map and a tile-pane CSS filter fixes it | Group F | Needs the owner's screenshot; could be a marker drawn in canvas. |
| A7 | R10 difference between Safari and the Home Screen app has no CSS cause; owner device check needed | Group G | A Safari-only rendering issue stays. |
| A8 | R34's "no jump" means the tab bar/scroll must not move when switching space | Group G | Misread requirement. |
| A9 | The D-07 root cause (full navigation vs URL churn) is not determined; hypotheses listed | Group F | Fix chosen before investigation could be wrong. |
| A10 | R30 policy: show Back to the default only when a vendored picture exists beneath the override | Behaviour Traces | Owner may want removal wording only. |
| A11 | R32: no deploy path rule exists for `/locations` (not read in `deploy/`) | Runtime State | Stale proxy rule (harmless, 404). |
| A12 | JS scroll-into-view for the keyboard covering the invite field (R25) is in `modal.js` | Group C | Fix location differs. |

## Open Questions

1. **R26: which option (A, B, C)?** What we know: no password or Auth0 account is created by the invite; sign-ups disabled; manual dashboard step today. Unclear: whether the owner wants to automate now (SEED-012 targets v1.4). Recommendation: A in this phase; B/C only on the owner's explicit decision.
2. **R13/R15 frame list design?** Recommendation: list at `/fleet`, frame page at `?frame=<id>` (no new route). Needs mockup M-A.
3. **R32: delete the POST routes or keep them with a redirect?** Recommendation: delete (4 routes, matrix rows, tests).
4. **"Marchand" (R29), R34 label, D-08 naming (EN and FR).** Owner.
5. **R30 policy** (see A10).
6. **The "Route sources" candidates (PR #469 on main)** are not in the owner's closed list; the list is closed (D-02, D-20), so they are excluded unless the owner adds them.
7. **R16: retire the standalone `/update` page markup too?** It shares builders and the golden file.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | tests, snapshot | yes | 3.13.18 (prod 3.14) | - |
| pytest, playwright | browser tests | **no** in this research environment (`ModuleNotFoundError: playwright`); `server/.venv` exists | - | Executors run `pip install -r server/requirements-dev*.txt` and `playwright install --only-shell chromium`; CI has them; `SKYPANE_REQUIRE_BROWSER=1` fails when missing. |
| `gh` (REST only; GraphQL blocked) | PR checks | yes | - | `gh api repos/{owner}/{repo}/pulls` |
| Real iPhone/Safari | R10, D-10, map under status bar | owner's device only | - | Owner checklist; not testable in CI. |

**Missing with no fallback:** none for planning. Real-device checks (R10, D-10) are owner tasks.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-xdist + pytest-cov; pytest-playwright (Chromium headless shell) for `@pytest.mark.browser`; pytest-socket loopback guard |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, markers, `[tool.coverage.report] fail_under = 93`) |
| Quick run command | `pytest companion/<test_file>.py -x -q` (set `SKYPANE_REQUIRE_BROWSER=1` for browser files) |
| Full suite command | `./scripts/run-all-tests.sh` (= `pytest -n auto --cov`) |
| Gates | `python scripts/check_function_size.py`, `python scripts/check_comment_history.py check`, ruff, mypy, `companion/test_structure_guards.py`, `companion/test_suite_guards.py` |

### Phase Requirements to Test Map
| Group | Behaviour | Test type | Automated command | File exists? |
|-------|-----------|-----------|-------------------|-------------|
| A R12/D-06 | Back to Fleet returns to `/fleet?frame=<id>` and the page shows that frame | browser | `pytest companion/test_browser_admin_personal_scope.py -x` | yes, update |
| A R35 | Banner visible, sticky, 44px action, EN/FR, light/dark, 360/1280, no overflow | browser | same file + `test_browser_overhaul_sweep.py` | update |
| A R13/R15/D-04 | Retired and pending frames only in the list; frame page names its frame; list works with 30 frames | browser + unit | `pytest companion/test_browser_fleet_page.py companion/test_console_fleet_view.py` | update + new |
| A R11/R14 | Phone sections/toggles; Access text reduced; 44px targets | browser | `test_browser_fleet_sections.py`, `test_browser_fleet_tabs.py` | update |
| B R16/R17 | Panel and confirm page layout EN/FR; Install/Revert still two-step; golden regenerated | unit + browser | `pytest companion/test_update_page.py companion/test_browser_update.py companion/test_browser_firmware_panel.py` | update; golden JSON regen |
| C R25 | Keyboard does not cover the field (visualViewport emulation), no odd margins, role-confirm width | browser | `test_browser_users_page.py` (+ new) | update |
| C R26 | Per chosen option: copy control wording or removal; flash text; (B) Auth0 fake called, local invite not half created | unit/browser | `pytest companion/test_console_users.py companion/test_browser_users_rows.py` | update |
| D R27-R31, D-15 | Collapsed unidentified rows, Complete/Edit/Rename, Ignore gone, filter works, "..." menu, read-only known rows; resolve routes unchanged | browser + unit | `pytest companion/test_browser_airline_editor.py companion/test_airline_editor.py` | update + new |
| D R04b/R05 | Detail sheet no scroll at 360x740; Close not heavy | browser | `test_browser_airline_collection.py` | update |
| E R18-R24 | Wording, Account row changes (no %, no hardware for admin), Credits row reaches `/credits` with Back to Account, login block, 404 | unit + browser | `pytest companion/test_account_page.py companion/test_sign_in_surfaces.py companion/test_status_pages_*.py` | update |
| F D-03/R01/R02 | Three Home states, stats card from seeded flights, strip uses matching renders, no-script floor | browser + unit | `pytest companion/test_browser_home_*.py companion/test_home_*.py` | rewrite |
| F R03/D-05 | Row content, header at 320-1280 widths, direction still spoken | browser | `test_browser_flights_cards.py`, `test_browser_flights_search_more.py` | update |
| F D-07 | Switching Style tab does not refetch unchanged previews (or documented cause) | browser | `test_browser_theme_switch.py` (+ new request-count test) | new |
| F R06 | Leave dialog: one status, clear buttons, equal sizes | browser | `test_browser_style_leave.py` | update |
| F R07-R09 | No "position found" text visible (spoken status kept), icon buttons 44px, dark map contrast | browser | `test_browser_place_page.py` etc. | update |
| G R04/R34/D-08 | Same nav order sidebar and bar; labels EN/FR | browser + unit | `test_browser_nav_alignment.py`, `test_user_nav.py`, `test_i18n.py` | update |
| G D-09/D-11/D-13 | More sheet width at 768/1024, grab handle, active tab tap | browser | `test_browser_more_sheet.py`, `test_browser_tab_bar_tablet_cap.py` | update |
| G R32 | `/locations*` GET and POST answer 404 for admin, user, anonymous; matrix and route-table complete | unit | `pytest companion/test_access_matrix.py companion/test_route_table.py` | update, delete `test_console_locations.py` |
| G R33 | Audit phone navigation and opened rows readable | browser | `test_browser_audit_page.py` | update |
| All | Rendered pages equal baseline | unit | `pytest companion/test_render_baseline.py` | regenerate once per wave |
| All | Legacy render golden hashes and Phase 47 freeze | unit | `pytest server/test_golden_render.py server/test_golden_giant_render.py stub-server/test_phase47_freeze.py` | unchanged, must stay green |
| All | Access rules of Phases 54, 55, 60 | unit | `pytest companion/test_access.py companion/test_access_matrix.py companion/test_co_manager_access.py companion/test_device_scope_owner.py companion/test_admin_personal_scope.py` | unchanged except R32 |

### Sampling Rate
- **Per task commit:** the touched test file(s) from the map plus `companion/test_i18n.py`, `companion/test_structure_guards.py`, `companion/test_suite_guards.py`.
- **Per wave merge:** `./scripts/run-all-tests.sh` (full), function-size and comment-history gates, baseline regenerated and diff reviewed (only expected pages changed).
- **Phase gate:** full suite green with `SKYPANE_REQUIRE_BROWSER=1`; EN/FR x light/dark x 360/1280 sweeps (`test_browser_overhaul_sweep`, `test_browser_french_fit`, `test_browser_contrast_edges`); owner validation on the deployed companion before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] D-07 request-count browser test (new), R28 repro test if the owner's screenshot shows a persistent state.
- [ ] A throwaway regeneration helper for `update_page_one_type_golden.json` (no CLI exists) if Group B changes the standalone page.
- [ ] Mockup files `68-MOCKUP-*.html` (not tests, but the gate for every visual plan).
- [ ] Playwright and Chromium installed in the executor environment (absent here).

## Security Domain

`security_enforcement` is not disabled in config. Phase 68 is presentation plus two behaviour edits; Phase 66 audits the result.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | R26 only (option B/C) | Auth0 authorization-code + PKCE (`oidc.py`), local roles; option B adds a second Auth0 secret (M2M) with narrowest scopes |
| V3 Session Management | no change | Sessions in `fleet.db` (30 d absolute, 7 d idle) |
| V4 Access Control | yes (R32 removes routes; R12/R35 expose a frame id in a link) | Default-deny route table + matrix; the frame id in `/fleet?frame=` comes from the request scope and is validated by `selection()`; 404 for unknown |
| V5 Input Validation | yes (R25 invite form, R27 name fields, R29 filter) | Existing validators (`normalize_email`, shape checks); output through `escape_html`; no request text reaches a path |
| V6 Cryptography | no | none hand-rolled |

### Known Threat Patterns
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Reflected/stored XSS in new markup (owner e-mail in the banner, airline names, frame names) | Tampering | `escape_html` on every dynamic part; behaviour tests with hostile names (existing pattern in `test_audit4_fixes`) |
| IDOR through `?frame=<id>` | Info disclosure | `selection()` only picks among the principal's own scope list; unknown falls back with a warning |
| CSRF on any new POST | Tampering | `csrf_field()` + `csrf=True` route flag; `test_csrf*` |
| Host-header injection into the copied invitation message | Spoofing | `_app_url` validates with `_HOST_RE` (keep when R26 touches it) |
| Dead POST endpoints before the audit (R32) | Elevation | Remove them |
| Invitation automation (R26 B) widening blast radius | Elevation | Narrow M2M scopes; local invite still gates sign-in |

## Sources

### Primary (HIGH confidence, read in this session)
- Repository code: `companion/ui_shell.py`, `ui_nav.py`, `console_fleet_view.py`, `pages/fleet_page.py`, `frame_menu.py`, `console_users.py`, `pages/users_page.py`, `sign_in.py`, `oidc.py`, `login_page.py`, `credits_page.py`, `app.py` (update/credits handlers), `console_locations.py`, `console_routes.py`, `pages/airline_table.py`, `pages/home_page.py`, `pages/account_page.py`, `pages/update_page.py`, `style.css` (frame-notice, tab bar, scrim), `server/fleet_sessions.py`, `test-support/companion_render_snapshot.py`, `companion/test_render_baseline.py`, `test_structure_guards.py`, `test_suite_guards.py`, `test_browser_admin_personal_scope.py`, `test_update_page.py`.
- Planning records: `68-CONTEXT.md`, `68-WALKTHROUGH.md`, `68-CANDIDATE-ITEMS.md`, `68-HOME-MOCKUP.html`, `ROADMAP.md` Phase 68, `REQUIREMENTS.md` CON-01, `SEED-011`, `SEED-012`, `SEED-020`, `deploy/README.md` "Sign-in (Auth0)", `54-HANDOFF.md`, skill `sketch-findings-skypane` (SKILL.md, page-patterns, accessibility, i18n).
- Git: `git log origin/main`, `gh api repos/.../pulls?state=open` (0), `git diff HEAD origin/main -- companion` (empty).

### Secondary (MEDIUM confidence)
- Auth0 Management API: https://auth0.com/docs/api/management/v2/tickets/post-password-change (password-change ticket, `mark_email_as_verified`, ticket TTL 5 days), and https://support.auth0.com/center/s/article/Reseting-Password-sets-Email-Verified-to-True-but-Does-Not-Send-a-Welcome-Email (a password reset marks the e-mail verified).

### Tertiary (LOW confidence)
- Auth0 tenant behaviour for options B and C (A3 to A5); Safari scrim behaviour (A7).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - no new dependency; the stack is the shipped one.
- Architecture and file maps: HIGH - read from code; the test lists come from `grep` of identifiers and may miss a few unit tests that assert incidental markup.
- Pitfalls and gates: HIGH - from the guard tests read directly.
- Visual root causes (R01, R08, R10, R11, D-07): MEDIUM/LOW - need browser reproduction or the owner's screenshots.
- Auth0 options: MEDIUM for the current flow (code plus README), LOW for tenant-side behaviour.

**Research date:** 2026-11-18
**Valid until:** 2026-11-25 (main moves daily; re-check open PRs and `git diff origin/main -- companion` at each wave start)
