---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 01
subsystem: companion
tags: [status-dot, i18n, sprite, css]
requires: []
provides:
  - companion/frame_status.py (frame_status, status_dot_html)
  - icon-more-vertical sprite glyph, .dot--hollow
  - 61-OWNER-DECISIONS.md ledger
affects: [61-04, 61-05, 61-06, 61-07, 61-08, 61-11, 61-15]
key-files:
  created:
    - companion/frame_status.py
    - companion/test_frame_status.py
    - .planning/workstreams/v1-2/phases/61-companion-ux-and-ui-overhaul-admin-and-users/61-OWNER-DECISIONS.md
  modified:
    - companion/ui_base.py
    - companion/static/style.css
    - companion/i18n_fr/frame_state.py
    - companion/test_companion_app_01.py
    - companion/test_status_pages_07.py
    - companion/test_sign_in_surfaces.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 01: Status resolver, glyphs and ledger Summary

One shared `frame_status(row)` resolver (retired, waiting, no contact, not seen, overdue/low battery, resting, up to date) renders a single accessible dot, with the hollow dot rule, the missing `icon-more-vertical` glyph and the owner-decision ledger.

## Tasks

1. Ledger: 14 open items (all "default applies") plus audit rows A-C recorded as in scope (owner, 2026-11-03), owned by 61-15. Commit c88ddef.
2. Resolver: `frame_status()` reads row attributes `kind`, `offline`, `last_seen`, `battery_percent`, `state` (frame_state.STATE_*), `screen_off` via getattr; `status_dot_html()` wraps `status_dot(..., visually_hide_label=True)` and adds `role="img"` and `aria-label`. 15 behaviour tests. Commit 593c64f.
3. Glyphs and CSS: `icon-plus` and `icon-close` already existed; added `icon-more-vertical`; `.dot--hollow` plus a `.home-state__dot.dot--hollow` variant. Commit 97d39e8.

## Deviations from Plan

- **[Rule 3 - Blocking]** Pinned outputs had to move with the new sprite glyph and CSS: sprite count 41 to 42 (two tests), dot modifier set now includes `hollow` (test renamed `..._exactly_five_...`), `companion/testdata/render_baseline.json` regenerated (only the sprite line differs, verified), and the sha256 pins in `test_sign_in_surfaces.py` recomputed. These are pins of generated output, not weakened assertions.
- `ui_base._STATUS_DOT_CLASSES` gained a `"hollow"` entry (additive) so `status_dot` can render the hollow class; the change landed in the resolver commit.
- The shared "Overdue / Low battery" row is two messages (Overdue, Batterie faible/En retard) with the same warn dot, so eight words and keys, not seven.
- `frame_status.status_dot_html` imports `companion.page_context` before `ui_components` on use: `ui_components` fails to import first in a fresh interpreter (existing import cycle).
- Plan frontmatter lists `ui_base.py`'s sprite and `style.css` only; the render-baseline and three test files were added for the reason above.

## Verification

- Full `companion` suite plus `stub-server/test_phase47_freeze.py` (`-n auto`): 5454 passed, 3 skipped (the skips are "root ignores permission bits", pre-existing, not browser tests).
- ruff clean; mypy clean (28 files); check_comment_history clean; check_function_size (max 80) none over.

## Known Stubs

None. The resolver has no callers yet by design (later plans wire it).

## Self-Check: PASSED

Files and commits c88ddef, 593c64f, 97d39e8 exist.
