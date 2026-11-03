---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 02
subsystem: companion
tags: [modal, dialog, css, javascript]
requires: [61-01]
provides:
  - companion/ui_modal.py (dialog_html, trigger_html, field_error_html, error_id, validated_slug)
  - companion/static/modal.js (modal, row-menu and switcher dismissal), layout.MODAL_SCRIPT_SRC
  - dialog.modal CSS (centred card, phone bottom sheet, no-script fallback)
affects: [61-06, 61-07, 61-08, 61-09, 61-10]
key-files:
  created:
    - companion/ui_modal.py
    - companion/static/modal.js
    - companion/test_ui_modal.py
  modified:
    - companion/static/style.css
    - companion/static_files.py
    - companion/app.py
    - companion/ui_base.py
    - companion/ui_shell.py
    - companion/layout.py
    - companion/i18n_fr/common.py
    - companion/test_companion_app_03.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 02: Shared modal component Summary

One `dialog.modal` component: server-rendered native `<dialog>` with hash-link triggers, a first-party `modal.js` upgrade, and a no-script `:target` card, so later dialogs are a single helper call.

## Tasks

1. Helpers (commit d9090c3): `dialog_html(...)` follows the UI-SPEC 2 markup contract; `trigger_html`, `field_error_html`, `error_id` for callers. Dialog and field ids go through a lowercase-slug validator (ValueError, never rendered); title, subtitle, labels and URLs are escaped. A confirm-only dialog marks the dismiss link `autofocus`; any other dialog autofocuses the invalid control, else the first visible control, else the submit button. Destructive submit uses `calendar-disconnect-btn`. EN/FR "Close"/"Fermer".
2. modal.js and registration (commit 39e3c54): ES5, delegated clicks, no inline script, no HTML sinks, no network. Opens via `showModal` (adds `is-modal`), closes on Esc / close / dismiss links, backdrop click only for dialogs without fields, returns focus to the opener (its row-menu summary when the menu closed, else `#main-content h1`), upgrades a server-rendered `open` dialog and a hash-targeted dialog on load, clears the hash on close, and closes open `details.row-menu` / `details.frame-switcher` on outside tap or Esc. Added to `SHELL_SCRIPT_ORDER` and `GLOBAL_PAGE_SCRIPTS`; route in `static_files`.
3. CSS (commit 6f9b985): additive, tokens only, no new keyframes. Card from 700px (`min(480px, calc(100% - 48px))`, `--shadow-pop`, `--radius-card`); bottom sheet below (full width, 88vh, 18px top radius, 40x4 handle, safe-area padding); 44px controls; actions stacked on phone, right-aligned row on desktop; `@starting-style` entrance on `.is-modal` only; `.modal:target:not(.is-modal)` and `.modal[open]:not(.is-modal)` fixed card over a 100vmax shadow scrim.
4. Pins (commits bfdd707, 2666d51): `test_sign_in_surfaces.py` 404/403/bare-shell sha256 pins recomputed (only the added script tag changed the output); render baseline: regenerated; the only difference on every authenticated page is the added modal.js tag.

## Verification

- 20 behaviour tests in `companion/test_ui_modal.py` (helper contract, escaping, hostile ids, focus rules, served modal.js and CSS).
- Throwaway Chromium probe (not committed; no harness page added): at 360 and 1280 px the dialog opens as sheet/card, focus lands on the first field, Esc closes and returns focus to the trigger, the confirm-only dialog focuses its dismiss link, controls measure 44 px, no horizontal overflow, and with JS off the hash link shows the card.
- ruff, mypy (28 files), comment-history, function-size (none over 80) clean. Full companion suite plus `stub-server/test_phase47_freeze.py` (`-n auto`): 5547 passed, 3 skipped (root-ignores-permission-bits, pre-existing, not browser tests).

## Deviations from Plan

- **[Rule 3 - Blocking]** Pinned outputs moved with the new shell script: `test_companion_app_03.py` script-count pin 15 to 16 (test renamed `test_sixteen_deferred_scripts_before_closing_body`, modal.js added to its expected tags and login-shell exclusion list) and `companion/testdata/render_baseline.json` regenerated (only the modal.js tag differs). Files outside the plan frontmatter: `static_files.py`, `app.py`, `ui_base.py`, `layout.py` (the script constant, route and re-export that `ui_shell` needs).
- Hostile ids raise ValueError instead of being escaped, per the plan's "validated slug" rule.
- Selector is `.modal:target:not(.is-modal)` (not bare `.modal:target`) so a hash-opened dialog promoted by modal.js does not also draw the scrim shadow over `::backdrop`.

## Known Stubs

None. The component has no page adopters yet by design; browser behaviour on a real page is asserted by plan 61-06.

## Threat Flags

None. T-61-02-01 (escaping, slug ids, hostile-input tests), T-61-02-02 (first-party script, no eval or inline script, CSP unchanged) and T-61-02-03 (confirm-only focuses dismiss) are mitigated as planned.

## Self-Check: PASSED

Files exist; commits d9090c3, 39e3c54, 6f9b985, bfdd707, 2666d51 exist.
