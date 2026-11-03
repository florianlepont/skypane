# Phase 61 — traceability

What closes each friction, audit note and requirement, and which test proves
it. Sources: `61-WALKTHROUGH.md`, `61-VISUAL-AUDIT-NOTES.md`,
`61-OWNER-DECISIONS.md`, the SUMMARY of each plan. Status words: **closed**
(changed and tested), **closed with a stated limit** (the limit is named),
**owner confirm** (implemented on the spec default, the owner may overrule).

Note on numbering: `61-WALKTHROUGH.md` defines F1 to F11 (F1 to F11 appear in
the document; there is no F12 in it, although `61-CONTEXT.md` and plan 61-12
speak of F1-F12). Decisions D1 to D10 from the walkthrough, D11 to D15 from
the context file are traced after the frictions.

## Frictions F1-F11

| F | Friction | Closed by | Where | Proof |
|---|----------|-----------|-------|-------|
| F1 | FR "Cadres" for the fleet confuses | 61-04 (nav label), 61-06 (page) | `companion/i18n_fr/nav.py` (`nav.fleet` = "Flotte"), `companion/pages/fleet_page.py` | `test_nav_spaces.py`, `test_console_fleet_page.py`, FR title check in `test_browser_overhaul_sweep.py` |
| F2 | Admin console is one tab of the everyday app | 61-04, 61-05 | `companion/ui_nav.py` (Console and My views spaces, space switch), `companion/access.py` (`home_for`) | `test_nav_spaces.py`, `test_browser_nav_spaces.py`, `test_landing.py`, `test_browser_auth0.py` (admin lands on `/fleet`) |
| F3 | Fleet table unreadable | 61-03, 61-06 | `companion/ui_entity_list.py`, `companion/pages/fleet_page.py`, `style.css` | `test_ui_entity_list.py`, `test_browser_fleet_page.py`, no-table and overflow checks in `test_browser_overhaul_sweep.py` |
| F4 | Emails and frame names in large monospace | 61-03, 61-06, 61-08 | entity-list CSS (no monospace), `users_page.py`, `fleet_page.py` | `test_ui_entity_list.py`, `test_browser_users_page.py`, monospace check in the sweep |
| F5 | Invite form at the page bottom | 61-02, 61-08 | `companion/ui_modal.py`, `users_page.py` ("+ Invite a user" dialog) | `test_ui_modal.py`, `test_browser_users_page.py`, `test_browser_overhaul_steps.py` (A2 = 4) |
| F6 | "Register a frame" form always open | 61-06 | form removed from the page; `POST /fleet/register` kept | `test_console_fleet_page.py`, `test_console_pairing.py` (route tests unchanged) |
| F7 | Pairing should be an "Add a frame" button | 61-06 | `fleet_page.py` header action + Add dialog | `test_browser_fleet_dialogs.py`, step test A3 = 4 |
| F8 | Retire / Reassign / Re-activate as inline disclosures | 61-06 | row menu + confirm dialogs | `test_browser_fleet_dialogs.py`, step tests A4 = 3 and 4 |
| F9 | Co-managers card on Home | 61-07 | `co_managers` dialog on Fleet; Home card removed | `test_co_managers_page.py`, `test_browser_co_managers.py` (Home has none), step test A5 = 4 |
| F10 | Co-managers card on the frame page is wrong for users | 61-10 | My frames card on Account: Manage access (owned) or Leave (shared) | `test_account_page.py`, `test_browser_account_frames.py` |
| F11 | Landing on Account after sign-in | 61-05, 61-09 | `access.home_for`, `device_scope.default_frame_for`, 303 from un-prefixed pages | `test_landing.py`, `test_access_matrix.py` (landing rows), step tests U1, U2 |

## Decisions D1-D15

| D | Decision | Closed by | Proof / note |
|---|----------|-----------|--------------|
| D1 | Admin space, link to own views, no Admin tab | 61-04, 61-14 | `test_nav_spaces.py`, `test_browser_nav_spaces.py` |
| D2 | Fleet row: name, owner, one status dot | 61-01, 61-06 | `test_frame_status.py`, `test_console_fleet_page.py` |
| D3 | Forms open from a "+" / action button in a dialog | 61-02, 61-06, 61-07, 61-08, 61-10 | `test_ui_modal.py`, dialog browser tests; dialog sweep in `test_browser_overhaul_sweep.py` |
| D4 | "cadre" is the device; fleet page named otherwise | 61-06 | FR strings in `i18n_fr/admin_fleet.py`; ledger row 1 |
| D5, D6 | Manage access per frame (Fleet, My frames) | 61-07, 61-10 | `test_co_managers_page.py`, `test_browser_co_managers.py`, `test_browser_account_frames.py` |
| D7 | User lands on frame Home; switcher on multi-frame | 61-05, 61-09 | `test_landing.py`, `test_frame_switcher.py`, step test U2 |
| D8 | One status dot for a user | 61-01, 61-09 | `test_frame_status.py`, `test_home_state_card.py`, `test_browser_home_state_card.py`, step test U3 |
| D9 | All display settings stay; location and detection merge | 61-10 | `test_display_detection_card.py`. **Owner confirm:** the time zone select stays in the Quiet hours card, not in the merged "Location and detection" card, so the save bar's dirty tracking is unchanged (plan 61-10 deviation 1). |
| D10 | Architecture and visual style unchanged | all | no new runtime dependency; `modal.js` is the only new static script |
| D11 | Fleet page named "Fleet" / "Flotte" | 61-04, 61-06 | ledger row 1; FR title check in the sweep |
| D12 | Fleet list shows no last image | 61-06 | ledger row 2 |
| D13 | User on an un-prefixed page gets a 303 to their frame | 61-05 | `test_landing.py`, `test_access_matrix.py` |
| D14 | Health leaves the user tab bar, reached from the Home dot | 61-04, 61-09 | `test_user_nav.py`, `test_home_state_card.py` |
| D15 | Three audit items in scope | 61-15 | section below |

## Visual audit notes (`61-VISUAL-AUDIT-NOTES.md`)

| Item | Status | Closed by / note |
|------|--------|------------------|
| User view is one page; tab bar offers tabs that 404 | closed | 61-04 (user bar), 61-05 (303 redirects) |
| Fleet desktop table clipped | closed | 61-06 (entity list) |
| Fleet phone cards long; console tabs wrap on two lines | closed | 61-06; 61-04 and 61-14 (one bottom bar, no chip row) |
| Phone nav: Admin tab, More | closed | 61-04 |
| Users phone: email breaks mid-word, wrong "INVITED" badge, role select + Save role per user | closed | 61-08 |
| Pair and Register forms always open | closed | 61-06 |
| Fixed tab bar overlaps content in full-page captures | capture artefact | sweep takes viewport (not full-page) measurements |
| Sidebar has 3 groups / 12 entries; Account missing for admin | closed | 61-04 |
| Device / Update / Releases three names | closed | 61-04, 61-06 (title "Releases") |
| "Detection" on both Display and Device | closed | 61-10 |
| Console section tabs wrap; Audit stacks a second chip row | closed | 61-04, 61-14 |
| "Frame" picker even with a single frame | closed | 61-09 (switcher only with two or more frames) |
| Users: "Invited" badge on signed-in users; truncated last-admin text | closed | 61-08 |
| Locations inputs/selects overflow at 360 px | closed | 61-04 (`max-width: 100%`); `test_browser_nav_spaces.py`; `/locations` at 360 px in the sweep |
| Owner/co-manager actions on Home far from Fleet | closed | 61-07 |
| Home: persistent attention bar | closed with a limit | admin Home keeps the attention bar by design; a plain user's Home has none (61-09) |
| Home: empty states large serif blocks; Current frame card empty | closed with a limit | see "Audit items" below |
| Device: LED switch drawn with an orange box | closed | 61-15 |
| Health: "Has not checked in" three ways | closed | 61-15 |
| User view: serif name + hardware, no frame state | closed | 61-10 (My frames rows with dot) |
| Login card; error and invitation states to capture | closed | 61-11 (outcome pages) |

## Audit items brought into scope on 2026-11-03 (plan 61-15)

| Row | Item | Files | Tests | Status |
|-----|------|-------|-------|--------|
| A | Device page Diagnostic LED switch drawn with an orange box (the primary button fill outranked the `.switch` rule) | `companion/static/style.css` (`button.switch` rules) | `companion/test_browser_device_led_switch.py` (both themes, EN/FR, 360 and 1280 px, keyboard focus ring, click toggling) | closed |
| B | Health Frame connection row says "Has not checked in" three ways | `companion/pages/health_page.py` (`_connection_row`) | `companion/test_health_connection_row.py`, `companion/test_user_health.py` | closed |
| C | Empty states drawn as large serif blocks | `companion/static/style.css` (`.empty-state--compact` padding), the `empty_state` callers on Home, Health, Audit, Locations, Update | `companion/test_empty_state_scale.py`, `companion/test_browser_empty_state_scale.py`, `companion/test_status_pages_02.py` | **closed with a stated limit** |

Limit on row C. Plan 61-15 converted Home (no panel, no flights), Health
(device empty, no gaps), Audit (no events), Locations and Update. Large-form
empty states remain, and are not claimed closed, on pages outside that list:
`companion/pages/history_page.py` (2), `companion/pages/detection_page.py` (3),
the My frames empty state in `companion/pages/account_page.py`, and the table
fallback in `companion/ui_components.py`. The sweep asserts the pages that
were converted, and does not assert "no large empty state anywhere". Whether
to convert the rest is left to the owner; plan 61-15 did not list these pages.

## Requirements to plans

| Requirement | Plans | Evidence |
|-------------|-------|----------|
| UX-01 (walkthrough, ranked frictions, reworked navigation and structure) | 61-01 to 61-05, 61-09, 61-14 and the walkthrough record | this file; `61-STEP-COUNTS.md` |
| UX-02 (admin tasks) | 61-02, 61-03, 61-06, 61-07, 61-08, 61-14 | `test_browser_fleet_dialogs.py`, `test_browser_users_page.py`, `test_browser_co_managers.py`, step tests A1-A6. Owner validation on the deployed companion is plan 61-13, not done here. |
| UX-03 (user sees own frames, state at a glance, changes settings) | 61-04, 61-05, 61-09, 61-10 | `test_browser_account_frames.py`, `test_browser_home_state_card.py`, step tests U2-U4. **U4 misses its step target** (4 and 5 against 3): see `61-STEP-COUNTS.md`. Owner validation on a phone is plan 61-13. |
| UX-04 (sign-in clarity) | 61-11 | `test_sign_in_messages.py`, `test_browser_auth0.py` |
| Audit items A-C (D15) | 61-15 | section above |

## Owner-decision ledger state (`61-OWNER-DECISIONS.md`)

All 14 open items and audit rows A-C: no owner answer has been recorded in the
ledger, so rows 1-14 are **defaulted** (the spec default was applied), and rows
A-C are **answered** ("yes, in scope", 2026-11-03). Rows 1, 2, 5 and 10 are
also fixed by D11, D12, D14 and D13. Owner-confirm items beyond the ledger:

| Item | Detail |
|------|--------|
| Time zone select placement | Stays in the Quiet hours card, not in the merged Location and detection card (61-10). Needs the owner's confirmation. |
| Display page length / U4 | Changing one display setting takes 4 actions (5 for a look), one or two over the target of 3, because the settings sit below the first screen or in a sheet. Not addressed in this phase. |
| Remaining large empty states | `history_page.py`, `detection_page.py`, My frames, table fallback (limit on row C). |
