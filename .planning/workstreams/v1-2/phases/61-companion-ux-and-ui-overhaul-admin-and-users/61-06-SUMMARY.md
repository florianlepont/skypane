---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 06
subsystem: companion
tags: [fleet, dialogs, entity-list, console]
requires: [61-02, 61-03, 61-04, 61-14]
provides: [Fleet page as an entity list with add, retire, reassign and re-activate dialogs]
key-files:
  created:
    - companion/test_browser_fleet_dialogs.py
  modified:
    - companion/pages/fleet_page.py
    - companion/console_pairing.py
    - companion/app.py
    - companion/static/style.css
    - companion/static/modal.js
    - companion/i18n_fr/admin_fleet.py
    - companion/i18n_fr/nav.py
    - companion/ui_base.py
    - companion/pages/update_page.py
    - companion/test_console_fleet_page.py
    - companion/test_browser_fleet_page.py
    - companion/test_browser_console.py
    - companion/test_console_pairing.py
    - companion/test_console_lifecycle.py
    - companion/test_i18n.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 06: Fleet list and dialogs Summary

`/fleet` is one `ul.entity-list` (status dot, frame-name link, owner line, row menu) with a header "+ Add a frame" button; pairing, retire, reassign and re-activate confirm in native dialogs that post to the unchanged routes.

## Commits

- 193e055: page, handlers, FR strings, modal.js and CSS fixes, updated unit and browser tests.
- 8a46458: new browser flows for the dialogs.
- Third commit: Update page title aligned with the nav label (golden and render baseline regenerated; only the title changed).

## What changed

- `fleet_page.py` rewritten. Rows: dot from `frame_status` (one per row, accessible name from the shared vocabulary), name link to `/devices/<id>/` (retired and pending rows are plain text), owner line ("Waiting for pairing", "Unassigned", "Formerly %s"), row menu (Open frame, Reassign, Retire; Re-activate for retired; none for pending; no Retire for the served frame). Order: errors, warnings, the rest by name, then pending; retired frames sit in a closed `Retired frames (n)` details. Count line "%d frames · %d need attention" (the attention part is omitted at zero). Compact empty state with the spec copy.
- Dialogs through `ui_modal.dialog_html`: Add a frame (code input mono/max 12/autocapitalize, owner select with "Choose an owner", "no frame is showing a code yet" hint), Retire and Re-activate (confirm-only, destructive, first focus on the dismiss link), Reassign (destructive unless it is the served frame). Titles carry the frame name; dismiss labels per UI-SPEC 2.2.
- A refused pair (unknown code 200, empty field 400, throttled 429) re-renders `/fleet` with the add dialog open (`open_add_dialog`), `aria-invalid`/`aria-describedby` on the field and the typed code escaped. `/fleet?pair=1` also renders the dialog open.
- The register form is gone from the page; `POST /fleet/register` and its tests are untouched. Its 400 refusals now render the messages as `role="alert"` paragraphs above the list (nothing typed is echoed).
- `app._console_page` gained an optional `action_html` argument; `page-header` shows the action beside the title (CSS grid, `.page-header__action` accent button, 44px).
- Owner ledger rows 1, 2, 3, 12: defaults applied (no owner answers recorded).

## Deviations from Plan

1. **[Scope] "Manage access" row-menu item not added.** Plan 61-07 adds the item and its dialog together; a link to a dialog that does not exist would be dead. 61-07 must add the item to `_menu_items` in `fleet_page.py`.
2. **[Rule 1 - Bug] modal.js race.** `openModal` on a server-rendered open dialog called `close()`, whose asynchronous `close` event then fired after `showModal()` and stripped `is-modal` (flaky; the refused-pair dialog was left as a non-modal card). Fixed with a `data-reopening` marker that the close handler consumes. Found by the new refused-pair browser test.
3. **[Rule 1 - Bug] Row menu showed two glyphs.** The global `summary::before` chevron drew next to the kebab icon (61-03 CSS); `.row-menu__toggle::before { content: none }`.
4. **[Rule 3] Files outside the frontmatter:** `companion/app.py` (`_console_page` `action_html`), `companion/test_browser_console.py` (its Fleet steps used the register form and the old table markup; pairing round trip now registers through `fleet_ops.register_frame`, drives the dialog, and the no-dialog guard now exempts `/fleet`), `test_console_pairing.py` and `test_console_lifecycle.py` (markup hooks `data-frame`/`data-kind` and the pair card), `test_i18n.py` (stale `admin_fleet.actions` allow-list entry). `console_lifecycle.py` and `admin_lifecycle.py` needed no edit: reassign/retire/re-activate refusals keep their existing redirect-with-flash behaviour (status unchanged), only pairing re-renders.
5. **FR wording.** Existing keys keep their catalog terms ("Associer le cadre", "Code d’association") so the dialog stays consistent with the rest of the French UI; the spec's "Appairer" was not introduced.
6. **Update page title (orchestrator scope note).** `nav.update` was registered with the same English in `ui_base.py` and `pages/update_page.py`; both now read "Releases" (FR "Versions"), so the page title matches the nav entry. The render baseline moved only for that title.
7. **Orphaned FR keys removed** from `admin_fleet.py` (table headers, badges, register card).

## Gates

ruff, mypy (28 files), check_comment_history, check_function_size (922 functions, none over 80), `stub-server/test_phase47_freeze.py` clean. Full `companion` + `test-support` + freeze suite with `-n auto`: 5833 passed, 3 skipped (root-permission tests), one golden regenerated afterwards (see commit 3) and re-run green. `render_baseline.json` regenerated once (title change); no digest pin moved for the Fleet page (it is not in the baseline).

## Known Stubs

None.

## Threat Flags

None. T-61-06-01 (csrf and ADMIN_ONLY rows unchanged, access matrix green), T-61-06-02 (names and typed code escaped; tests with hostile strings) and T-61-06-03 (register route kept, still ADMIN_ONLY with csrf) hold.

## Self-Check: PASSED
