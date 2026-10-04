---
quick_id: 261004-cb5
subsystem: companion
tags: [home, mobile, cards, css, dedupe, freshness]
key-files:
  created:
    - companion/flight_card.py
    - companion/test_home_recent_tiles.py
    - companion/test_browser_home_recent_tiles.py
  modified:
    - companion/pages/home_page.py
    - companion/pages/history_page.py
    - companion/pages/config_page.py
    - companion/pages/health_page.py
    - companion/static/style.css
    - companion/ui_time.py
    - companion/layout.py
    - companion/i18n_fr/health.py
    - companion/test_view_pages_helpers.py
    - companion/test_browser_ux_02.py
    - companion/test_browser_ux_03.py
    - companion/test_config_page_05.py
    - companion/test_status_pages_04.py
    - companion/test_status_pages_05.py
    - companion/test_view_pages_02.py
    - companion/testdata/render_baseline.json
completed: 2026-10-04
---

# Quick 261004-cb5: Home "Recent flights" as slim boarding-pass tiles

Below 960 px, each recent flight on Home is now one slim tile in the Flights card language.

- **Row 1:** the callsign in mono, then the airline muted beside it. The airline is cut
  with an ellipsis when it is too long; "Airline unknown" shows in italics.
- **Row 2:** a 64x28 artwork plate, or a dashed empty plate, then a compact
  ORY ┄✈┄ IBZ route. The codes are 16 px (22 px on Flights), the home end is
  muted, and the direction label sits under the plane.
- **Right column:** the clock over its live age. It spans both rows.

The tiles share one subgrid, so plates, routes and times line up from tile to tile. I
chose hairline separators over boxed cards: the section is already a card, and five
nested boxes looked heavy. The tiles have no link and no button, the same as Home's rows
before this change. "See all flights" stays. The desktop list at 960 px and above is the
same markup and CSS as before, rendered as a sibling after the tiles and switched at 960 px.

**Reused, not copied.** The Flights card's artwork plate, route line and time column moved
into `companion/flight_card.py`, which both pages import. The Flights markup is
byte-identical: the render baseline shows no /flights change.

## Flights per screen (390x844, same seeded data)

| | Row pitch | Section height (heading to link) | Rows per 787 px screen |
|---|---|---|---|
| Before | 103 px (rows 89-127 px) | 637 px | about 7.6 in theory, about 3-4 in the owner's real view |
| After | 68 px (tiles 62-70 px) | 458 px | about 11.6; all 5 plus the heading fit with room to spare |

At 360 px the "before" rows reached 127 px because of wrapping, against 70 px now.

## The duplicate TVF49NS row

Home's query is a plain `SELECT * FROM runway_events ORDER BY ts DESC, id DESC LIMIT 5`,
with no join, so it cannot produce a duplicate. The two rows are two stored events.

The poll loop writes a new event whenever the hex, the confirmed state or the
**corroborated flag** changes (`_should_record_event`). Concurrent writers are ruled out
because a timer cycle and /poll-now share `poll.lock`. That leaves one cause: when one ADS-B
feed misses a cycle, corroboration goes from True to None and a second row is stored 30 s
later. It has the same hex, callsign, route and direction, so both rows read "10:44".

I could not read the production database to confirm the corroborated values. This is the
only write path that fits the screenshot.

**Fix (Home only, storage untouched).** Home now reads 15 rows and folds a row into the newer
one before it when the pass key (hex, callsign, origin, destination, confirmed state) matches
and the two are under 60 s apart. It then keeps the newest 5 distinct passes. A change of
direction, or a gap of 60 s or more, still shows both.

**Flights still lists every stored event, including such pairs.** Flights is the full event
log, with a filter count and "Show more" paging tied to stored rows. Folding events there is
a separate decision for the owner (see Unresolved).

## Extra request: Display's visible freshness line removed

- Display now renders the same silent marker as Home and Flights: the hidden pill carrying
  `data-loaded-at` inside `.page-header__freshness`. Its swap registry entry and background
  refresh are unchanged.
- `freshness_line_html()`, `FRESHNESS_PREFIX_TEXT` and the "health.updated" string ("Updated" /
  "Mis à jour") had no remaining user, so I removed them, along with the FR entry and
  health_page's re-export.
- **Pages checked in the served HTML, EN and FR:** /, /display, /device, /flights, /health,
  /airlines, /update. None renders a visible freshness line (no `data-refresh-clock`, no live
  dot). Home, Display and Flights carry the silent marker.
- freshness.js still has a null-safe `syncLiveDot()` for a dot no page renders any more. I left
  it alone (harmless dead branch).

## Commits

- 90c4ecab feat: shared flight_card module, Home tiles markup, pass de-duplication
- 0e9e03a2 feat: compact tile stylesheet (subgrid, 960 px toggle)
- 828c3b88 feat: Display drops its visible freshness line (tests retargeted)
- 104399c5 test: Home tile served-HTML and browser checks, Display marker check, baseline regenerated

## Tests

- **New served-HTML checks** (`test_home_recent_tiles.py`):
  - tile structure and order;
  - tiles placed before the unchanged desktop list;
  - no link, button, tabindex or style attribute;
  - the artwork, no-artwork, unresolved, arrival and no-route variants, in EN and FR;
  - the duplicate folded in both lists;
  - 59 s repeats folded, while 90 s and changed-direction repeats are kept.
- **New browser checks** (`test_browser_home_recent_tiles.py`):
  - 390/360 in EN/FR, light and dark: no overflow, content inside each tile, two rows, height
    at most 80 px, codes on one row, airline on one line with the long name ellipsised;
  - five tiles inside one 390x844 screen;
  - no-JS rendering;
  - desktop list unchanged at 1280 (tiles hidden, flex rows, 40x40 thumbnails);
  - Display at 390/1280 in EN/FR: no "Updated" / "Mis à jour", no dot or clock, hidden
    marker present.
- **Retargeted, none skipped:**
  - test_browser_ux_02's Home overflow and callsign-starvation checks now measure the visible
    list for the width (tiles below 960, rows above);
  - the Display freshness tests in status_pages_04/05, config_page_05, view_pages_02 and
    browser_ux_03 now assert the silent marker.
- **Render baseline:** I inspected the diff before regenerating. It contains exactly the new
  `ul.recent-flight-tiles` markup on the four Home keys (additions only) and the visible line
  replaced by the silent marker on the eight /display keys. There is no Flights change and no
  unauthenticated change.

## Verification

- ruff, mypy, `check_comment_history.py check` and `check_function_size.py check --max 80
  server stub-server` are all green.
- `./scripts/run-all-tests.sh` (SKYPANE_REQUIRE_BROWSER=1) ran after the baseline
  regeneration; see the final result in the hand-off report.
- Screenshots are in the session scratchpad `shots-cb5/` (before-*, v1-*, v2-*, after-*): Home
  at 390/360 in light/dark and EN/FR, plus 1280, and Display at 390/1280.

## Deviations

1. **[Rule 3] Shared working tree.** Mid-task, another agent checked out
   `claude/flights-filter-chips` in /home/user/skypane with uncommitted edits. My commits were
   already on `claude/home-recent-flights`. I finished verification, docs and the push from a
   separate git worktree in the scratchpad, without touching the other agent's tree. The first
   full-suite run was contaminated by those edits and is discarded.
2. **Empty plate text hidden on the tile.** "No illustration" does not fit a 64 px plate, so the
   dashed outline carries the meaning. The words stay in the markup for screen readers.

## Unresolved

- Flights still shows both rows of a corroboration-flip pair. The owner should decide whether
  the Flights log should fold them too, or whether the poll loop should stop recording a
  corroboration-only change as a new event (a storage-side change).

## Self-Check: PASSED
