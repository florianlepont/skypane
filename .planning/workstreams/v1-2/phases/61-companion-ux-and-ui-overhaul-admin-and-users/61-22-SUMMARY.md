---
phase: 61-companion-ux-and-ui-overhaul-admin-and-users
plan: 22
subsystem: companion
tags: [navigation, space-switch, personal-space, parity, home]
requires: [61-21]
provides: [two-segment Console / My frame switch, identical personal space for administrator and user, parity tests]
key-files:
  created:
    - companion/test_space_switch.py
    - companion/test_personal_space_parity.py
    - companion/test_browser_space_switch.py
    - test-support/nav_spaces_support.py
  modified:
    - companion/ui_nav.py
    - companion/ui_shell.py
    - companion/user_view.py
    - companion/pages/home_page.py
    - companion/pages/history_page.py
    - companion/console_locations.py
    - companion/static/style.css
    - companion/i18n_fr/nav.py
    - companion/i18n_fr/flights.py
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-03
---

# Phase 61 Plan 22: Space switch and personal-space parity

The Console / My frame switch is now a two-segment control (strip under the phone header, top of the desktop sidebar), and an administrator's personal pages are identical to a user's, apart from the switch.

## Decision recorded: Home parity (owner V0/D16, option A)

An administrator's Home equals a user's Home. The battery pill, the charging pill and the "Something needs attention" docked toast are gone from the personal Home for every signed-in principal (`user_view.is_personal_view()`; an unset principal in a bare unit render keeps the old body). They stay available on the Console Health page (Battery row with the charging pill). Plan 61-34 adds the amber/red notification for every role. The Home `.home-facts` refresh region stays in the page and is empty until then.

Coverage note: the Home battery dial and Home charging pill are no longer rendered by any served page. Health still renders the battery value and the pill. The Home battery code remains reachable only for a bare render with no principal (unit tests of `home_page`); it is dead in production and a later plan may delete it. Health has no live-refresh marker, so "the freshness loop removes the pill in place" no longer exists for any page; the server-side token test and a next-load browser test cover removal.

## What changed

- **Switch** (`ui_nav.space_switch_html(active)`): `nav.space-switch` (aria-label Space / Espace) with two GET links, Console (`/fleet`, icon-shield) and My frame / Mon cadre (`/`, icon-device). The current segment has `aria-current=page`, an icon-check and the accent fill with `--color-on-accent`. Rendered in `.space-strip` under the header (hidden from 960 px) and at the top of the aside, before the primary nav (the aside is hidden below 960 px). Only for an administrator; the old header text link and its `:has()` rule are gone. Stylesheet accent list names the current segment. The contrast gate gets an explicit pair per theme.
- **Wordmark**: an administrator's personal pages now carry the same wordmark link to Home as a user's (a real navigation difference found by the parity test).
- **Flight history**: the "Name this airline" link, its CSS, its message id and `resolve_prefix_for_callsign` are removed for everyone (ledger R2-17; UI-SPEC 12.2 would show it to an administrator, which contradicts R1; spec inconsistency). The `/airlines?resolve=` redirect from 61-17 is untouched.
- **Display location picker**: an administrator with no location now sees the same "No location chosen." note as a user.
- **Home**: see the decision above.

## Tests

New:
- `test_space_switch.py` (9): switch markup, both copies, hrefs, current marking, FR, strip/sidebar placement, no old classes, never for a user or signed-out, `/fleet` still 404 for a user.
- `test_personal_space_parity.py` (33): for Home, Flight history, Location and detection, Personalisation, Airline collection (the `PERSONAL_PAGES` constant), EN and FR: link set, form-control names and normalised body equal for a user owning F1 and an administrator owning F2 with identical history; Account by link set and control names; no personal page links or labels Health, Device, Fleet, Users, Audit, Releases, Airline editor (EN and FR) or says "Name this airline"; History keeps the unidentified wording without a link.
- `test_browser_space_switch.py` (Chromium, not skipped, 3 runs in a row green with `test_browser_nav_spaces.py`): 360 and 1280 px, EN/FR, light/dark, Console and personal pages: segments 44 px high by hit-testing, no wrap, no overflow, current segment aria-current + check + different fill; strip below header on the phone, switch first in the sidebar on desktop; one tap each way; a user never sees it.
- `test-support/nav_spaces_support.py`: browser helpers shared by the two nav browser modules (a test module may not import another test module).

Rewritten in place (intent kept, expectation moved to the new truth):
- `test_nav_personal_console`, `test_nav_spaces`, `test_console_shell`: the sidebar no longer holds the switch (it is its own landmark before the nav); administrator sidebar equals user sidebar; switch asserted via the strip and the aside.
- `test_browser_nav_spaces`: header-link test became strip-fits-and-navigates; desktop sidebar test asserts the sidebar switch first and the tap through.
- `test_browser_console`: French Console nav read from the sidebar, plus the French switch labels.
- `test_browser_detection::test_accent_budget`: the current switch segment is an allowed accent fill.
- `test_browser_page_title_phone`: the title gap is measured from the space strip when present.
- `test_browser_brand_logo`: the lockup is the one 44 px link to Home on a personal page (no button, same accessible name).
- `test_flights_cards`, `test_view_pages_03` (4 tests): an unresolved airline reads the unknown wording with no link; the resolve-link template test now asserts the History page has no resolve machinery and the Health template is still built from the Airlines route.
- `test_location_picker`: admin without locations sees the same note as a user.
- Home (option A): `test_home_state_card::test_served_home_page_carries_no_inline_style` (no inline style and no dial on Home), `test_user_health` (administrator attention ignores pipeline state like a user), `test_freshness_token` (pill token and removal on Health, no pill on Home), `test_companion_app_04` (no battery tile or attention bar on Home), `test_user_view_http` (both roles: one dot, no battery, no attention bar; battery read on Health), `test_page_context` (health markup builds only on Health), `test_browser_home_state_card` (zones without a battery; late states fit; battery read on Health instead of Home), `test_browser_charging_pill` (Home never shows the pill; Health fit, swap-region and next-load removal), `test_browser_ux_02` (current frame before recent flights; facts region present and empty).
- `render_baseline.json` regenerated; sign-in digests did not move.

## Gates

ruff, mypy (28 modules), comment-history, function size (927 functions, none over 80): clean. Phase 47 freeze: 21 passed. Full `companion test-support stub-server -n auto --no-cov` after the last edit: 6872 passed, 4 skipped, 1 failed: `stub-server/test_ota_offer.py::test_offered_event_recorded_and_schedule_not_cancellable`, a file this plan does not touch; it passes alone twice (flaky under load). `./scripts/run-all-tests.sh` not run (not the last code plan).

## Deviations

1. [Rule 4, decided by the owner] Home content parity, option A (above).
2. [Rule 3] Shared browser helpers moved to `test-support/nav_spaces_support.py` (test-suite guard forbids importing another test module).
3. Wordmark link for an administrator on personal pages and the Display location note (parity findings).

## Known Stubs

None.

## Self-Check: PASSED
