---
phase: 68-console-and-companion-visual-improvements
plan: 22
subsystem: companion
tags: [render-baseline, gate, tests]
requires: ["68-13", "68-14", "68-15", "68-16", "68-17", "68-18", "68-19", "68-20", "68-21", "68-33", "68-36"]
provides:
  - "Render baseline regenerated once for waves 2 and 3"
  - "Full-suite triage of the merged wave 2 and 3 result"
affects: ["68-23"]
key-files:
  modified:
    - companion/testdata/render_baseline.json
    - companion/static/style-home.css
    - companion/test_browser_home_title.py
    - companion/test_browser_console_groups.py
decisions:
  - "The Home pencil and info buttons keep a 44 px hit target (the element) and draw a 28 px opaque disc with ::before."
metrics:
  completed: 2026-11-18
---

# Phase 68 Plan 22: Wave 2 and 3 gate Summary

Render baseline regenerated once and reviewed; the full suite ran once on the merged result: 15805 passed, 44 failed, coverage 96.18 % (gate 93 %). The failures are listed below by owning plan and were not fixed here.

## Owner-requested Home fix (commit dd7dd6d9, `fix(68-13)`)

The round rename pencil and the round "i" were drawn as 44 px discs, bigger than the approved mockup (a 44 px target around a 20 px glyph). The visible disc is now 28 px (`inset: 8px` on `::before`: opaque `--glass-solid`, 1 px border, glass shadow, hover tint), the glyph is 16 px and centred, and the button element stays 44 px so the touch target is unchanged. `test_browser_home_title.py` now asserts a 24 to 30 px round opaque disc plus a 44 px target, and the hover halo test reads the disc. Captures, Home online, 390 px, FR, light and dark: `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p22/home-online-phone-fr-{light,dark}-{BEFORE,AFTER}.png`. Browser tests for Home title, state card and landscape header: 126 passed.

## Baseline (commit in git log: `test(68-22): regenerate the render baseline`)

`PYTHONPATH=. server/.venv/bin/python test-support/companion_render_snapshot.py --write` (needs PYTHONPATH=. from the repo root). Only `companion/testdata/render_baseline.json` changed (76 lines each way). Diff classified:

| Capture | Change | Explained by |
|---------|--------|--------------|
| `/login` (4 variants) | `?v=` stylesheet and script hashes only | 14, 15, 16, 20, 21 (changed stylesheets linked everywhere) |
| every authenticated page | icon sprite: `icon-arrival`, `icon-departure`, `icon-fit` symbols changed | 20 and 13 (direction icons on Flights rows and Home) |
| `/` | page-header block (Home content) | 13 and 33 (Home assembly, statistics, recent strip) |
| `/airlines` | sprite and `?v=` hashes | 14 (editor stylesheet and `list-filter.js`) |
| `/flights` | rows: thumbnail 56x36 instead of 40x40, page header block | 20 |
| `/fleet`, `/fleet?flash=saved` | Device and version block, new `update-question.js` script tag | 16 |
| `/display*` (Style tab: arrivals, calendar, calendar-look, special-looks, special-looks/new, flash variant) | page-header block with previews | 36 |
| `/display/calendar/connect`, `/fleet?view=system`, `/settings/calendar/disconnect`, 404 page | sprite and `?v=` hashes only | shared stylesheets/sprite (14, 16, 20, 21) |
| unauthenticated `GET /locations`, `POST /locations/add`, `/locations/1/edit`, `/locations/1/delete` | 303 to login becomes 404 (8 records) | 17 (route removed) |

No capture is unexplained.

## Test fix

`test_console_tables_have_the_quiet_header_and_tall_rows`: the Airlines table header is 13 px in the approved editor mockup (plan 14); the test now expects 13 px for `.airlines-table` and keeps 12 px for `.users-table`. 8 passed.

## Static gates

ruff clean, mypy clean (46 files), function size (max 80, `server` and `stub-server`) none over, comment-history check passes.

## Full suite (`SKYPANE_REQUIRE_BROWSER=1 ./scripts/run-all-tests.sh`, 45 min)

15805 passed, 8 skipped, 44 failed, coverage 96.18 % (gate 93 %). Golden render tests and `stub-server/test_phase47_freeze.py` are not among the failures.

Known failures on HEAD (listed, not fixed): `test_sign_in_surfaces` (2), `test_config_page_03`, `test_config_page_05`, `test_companion_app_01` (2: sprite integrity, shell sprite once), `test_sky_contrast` glass test, `test_browser_ux_02` crossfade.

Other failures (36), re-run once and all reproduced deterministically, so they are not load flakes. They are tests written against the pre-redesign pages that a Phase 68 plan changed on purpose; none touches the files of this plan:

| Test | Failure | Likely owner |
|------|---------|--------------|
| `test_browser_components_page` buttons_are_centred_readable_targets (8) | `dirty-bar__cancel` sits 15.6 px off its centre | 14 or a shared button change (needs a look) |
| `test_browser_components_page` nothing_overflows (4, 360 px) | six `filter-chip` boxes overflow the 24 to 336 px card | 14 or 20 (filter chips on the components page) |
| `test_browser_round11_fixes` firmware history lines up (4) | first row reads "Running" where the test expects "Installed" | 16 (flat version list) |
| `test_browser_foundations` titles on the type scale (4), radius tokens (2) | Home `h1` size, 5 px radius on `img.preview-frame__image` and `div.home-strip__frame` | 13 and 33 |
| `test_browser_page_opening` (4) | `/airlines/manage` block stagger `[60,120,120]` vs `[60,120,180]`; Flights table column check | 14, 20 |
| `test_browser_motion_live` (4), `test_browser_more_sheet` (1), `test_browser_sky_motion` (2) | Home new-flight slide, countdown, loops and entrance, text node no longer found | 13 |
| `test_browser_ux_03`, `test_browser_ux_04` (2), `test_browser_console` (1) | preview, palette and colour-token checks on the changed Style or Home surfaces | 13, 36 |

These need an owner per plan; fixing them here would mean editing other plans' tests and, for the button and overflow items, possibly their CSS.

Open pull request check (`gh api .../pulls?state=open`) was not run.

## Design-system divergences

- The mockup draws the Home pencil and "i" as bare quiet 44 px ghost glyphs; the owner asked for a visible round button, so a 28 px opaque disc with border and glass shadow is built, with a 44 px target. A visible, opaque surface is the system rule for round buttons; the mockup's bare glyph is not used.
- The glyph inside the disc is 16 px (the mockup glyph is about 20 px) so it fits a 28 px disc with padding.
- No other design-system divergence; baseline and the table-header test follow the approved mockups.

## Deviations from Plan

The plan said to change only the baseline; the owner-requested Home fix and the airlines header test fix were added by instruction. Full-suite failures were reported instead of fixed (the plan says to fix nothing in other plans' files).

## Self-Check: PASSED

Commits found in `git log`: the Home fix, the baseline, the airlines header test.
