---
phase: 53-detection-modes-airport-runway-and-position-radius
reviewed: 2026-10-31T00:00:00Z
depth: standard
files_reviewed: 24
files_reviewed_list:
  - scripts/build_airports.py
  - server/airports.py
  - server/detection.py
  - server/plane/detect.py
  - server/plane/render/style.py
  - server/device_config.py
  - server/fleet_cycle.py
  - server/poll_cycle.py
  - server/fleet_db.py
  - companion/pages/detection_page.py
  - companion/detection_actions.py
  - companion/detection_summary.py
  - companion/pages/config_page.py
  - companion/settings/runway_led.py
  - companion/settings/form_post.py
  - companion/routes.py
  - companion/app.py
  - companion/static/dirty-state.js
  - companion/i18n_fr/detection.py
  - COMPLIANCE.md
  - companion/credits.json
findings:
  blocker: 0
  high: 0
  medium: 2
  low: 7
  total: 9
status: issues_found
---

# Phase 53: Code Review Report

**Depth:** standard. Scope: Phase 53 changes only (main-only code ignored).

## Summary

No blocker or high finding. Points I checked and found sound:

- **Coordinate rounding.** The only place a position Zone is built is
  `detection.position_zone`, which rounds to 2 decimals before `Zone`
  exists. `device_coordinates` -> `FleetDevice.location` ->
  `spec_for` -> `position_zone` is the only path. Provider URLs, the
  `Zone.key` and the ledger therefore carry only rounded values. The
  provider failure log prints `type(exc).__name__: exc`, and the zone in
  any such URL is already rounded. `inside_france` checks the rounded
  values, and rounding twice is idempotent.
- **km to NM.** `round(km/1.852, 2)` is deterministic and the key is
  stable. `-0.0` is normalised both in `round_coordinate` and in `Zone`.
- **Legacy Orly path.** I built the generated legacy documents and the
  kill-switch (file) documents and compared them. For ids "3", "06-24"
  and "02-20", `bbox`, `center`, `radius_nm`, `alt_ceiling_ft` and the
  zone key are value-identical (the file only has extra prose keys).
  The kill switch fires only for exactly "1".
- **Authorisation (`detection_actions`).**
  - The route is `OWNER_DEVICE`, so a user reaches only their own device
    and an admin any device.
  - `subject_for` makes an admin act as the device owner (or as
    themselves when the device has no owner).
  - Position selection requires `location_id` to be in the subject's own
    rows, and `set_device_location_checked` re-checks ownership inside a
    transaction.
  - Location edit re-checks `owner_user_id == subject_id` inside the
    transaction.
  - Ids are `\d{1,9}\Z` with `re.ASCII`, and coordinates are regex-bound
    with no exponent, no NaN or inf, at most 6 decimals.
  - I found no IDOR.
- **Escaping and catalogue.**
  - Every dynamic value in `detection_page` goes through `escape_html`,
    including the search term, the location name and the echoed form
    values.
  - Catalogue lookups are strict-regex then dict or equality lookups, so
    no id reaches a path or query.
- **Expand-only storage.** Legacy Orly ids write only
  `tracked_runway` and clear `detection`. Other runways write one
  `detection` key and leave `tracked_runway`. `detection` is omitted from
  the file when unset, so existing files keep their bytes. The three-state
  save sits inside the existing `_SAVE_LOCK` read-modify-write.
- **Fleet resolver.** `plan_zones` catches OSError, ValueError, KeyError
  and TypeError per device. The standalone `_fetch_standalone` still goes
  through the `RequestLedger`, so there is no second upstream path.

## Medium

### MD-01: A position-mode device with no usable location silently shows Orly runway 3 traffic

**File:** `server/detection.py:253-258, 386-392`; `server/poll_cycle.py:669-670`
**Issue:** `_position_spec` returns None when `location` is None (device
has no location row, or the location was edited out of France), and
`spec_for` then falls to `_legacy_spec("3", ..., fail_safe=True)`.

Failure scenario:
1. A Lyon user sets "Around a location", radius 10.
2. An admin reassigns or clears the device location through the Display
   picker.
3. The frame now polls the Orly zone and displays Orly flights, with the
   Orly tag text, on a wall in Lyon.
4. `history.db` records `tracked_runway="3"`.

`DetectionSpec.fail_safe` is set but never read anywhere in `server/`.
Only the companion page shows a toast, and only to someone who opens
`/detection`. The device owner sees no sign on the frame itself.

**Fix:** Make the frame say so rather than show wrong data. For example,
make `fail_safe` specs render a dedicated empty or "set a location"
heading (a new `empty_heading` branch) and skip the live fetch. At
minimum, consume `spec.fail_safe` in `poll_cycle` to log once per cycle
and to avoid recording a runway-3 history row.

### MD-02: Position save is not atomic and has no rollback

**File:** `companion/detection_actions.py:176-191`
**Issue:** `_store_detection` first assigns the device location in
fleet.db (`set_device_location_checked`) and then writes
`device_config.json` (`apply_position_selection`). If the config write
raises OSError (disk full, permissions), the handler redirects to "save
failed" but the device location has already been reassigned.

The location carries a timezone and drives zone selection, so the device
now behaves differently from what the user was told. `config_page`
undoes the equivalent assignment (`undo_device_location`) for exactly
this reason, and the detection POST does not.

**Fix:** Write the config first (validate radius, which cannot fail
after `validate`) and assign the location second. Or capture the previous
`location_id` and restore it in an `except (OSError, sqlite3.Error)`
block before returning the failure redirect.

## Low

### LW-01: The `fail_safe` field and `is_fail_safe` helper are dead code

**File:** `server/detection.py:93, 270, 312-347`; `companion/detection_summary.py:38`
**Issue:** `DetectionSpec.fail_safe` is never consumed in non-test code
(see MD-01). `detection_summary.is_fail_safe` appears unused, because the
page recomputes `saved_mode == MODE_POSITION and location_name is None`
at `detection_page.py:261`. There are three independent copies of the
"is fail-safe" rule, so they can drift apart.
**Fix:** Route all three through one function, or delete the unused
ones.

### LW-02: Position mode rejects aircraft with a slightly negative barometric altitude

**File:** `server/plane/detect.py:577-579, 603-605`
**Issue:** `0.0 <= alt <= ceiling_ft` drops airborne aircraft reporting
`alt_baro` of -25 to -50 ft. This happens near sea-level fields in low
pressure (Calais, Le Touquet, Mediterranean coast). Those are the lowest
aircraft, which are exactly the ones the feature selects.
**Fix:** Use a lower bound such as `-1000.0`, or drop the lower bound,
since `on_ground` and the `"ground"` string are already excluded.

### LW-03: Mid-cycle config change can pair a device with another zone's fetch

**File:** `server/poll_cycle.py:884-890`; `server/fleet_cycle.py:269-277, 376-392`
**Issue:** The fleet resolver builds a spec at plan time and `run_once`
builds its own at run time. If the user saves a new detection setting or
location in between, the cycle gates `fetched.results` of the old zone
using the new spec. The result is one cycle of an empty or wrong frame
(for example, Orly data gated against LFPG).
**Fix:** In `_select_from_zone`, compare `ctx.zone_fetch`'s zone with
`spec.zone`. Pass the zone into `run_device` and skip the device (status
"stale zone") on mismatch.

### LW-04: An admin can attach a location owned by user A to a device owned by user B

**File:** `server/fleet_db.py:709`; `companion/detection_actions.py:226-239`
**Issue:** `set_device_location_checked` lets an admin assign any
location. The detection page only offers the owner's rows, but another
admin surface can create the cross-owner link.

User A's "edit location" then moves user B's frame without B's
knowledge. `scope_for` also shows B the name of A's location through
`device_location_name`.
**Fix:** Either refuse cross-owner assignment (compare
`loc.owner_user_id` with the device owner for non-NULL owners), or make
the edit path block when `location_usage_counts` shows devices of other
owners.

### LW-05: Editing a location silently rewrites its timezone

**File:** `companion/pages/detection_page.py:709-747`; `companion/detection_actions.py:218`
**Issue:** `_location_form_state` loads `row["timezone"]` into `values`,
but `location_form_html` ignores it. It always renders the single
Europe/Paris option as selected. Validation also accepts only that value.
Any location holding another timezone (admin-created) is silently
rewritten to Europe/Paris on any name or coordinate edit. That changes
quiet hours or calendar time for every device using it.
**Fix:** Render the stored timezone when it is not the curated one, or
leave the timezone untouched on edit (do not pass it to `update_location`
unless it changed).

### LW-06: Detection POST relies on SameSite and Origin only

**File:** `companion/routes.py:219-221`; `companion/pages/detection_page.py:391-399, 716-725`
**Issue:** The detection and location forms carry no CSRF token and the
route has `csrf=False`. This matches `/settings`, but this diff adds
`csrf_field()` to other forms (calendar, rules). The Origin gate allows
requests with no `Origin` header (`auth.py` rule 2). This is consistent
with the existing design, but it leaves a state-changing endpoint that
can add, edit and assign locations (home coordinates) without a token.
**Fix:** Set `csrf=True` on the route and add `layout.csrf_field()` to
both forms.

### LW-07: Unicode digits in shape regexes; asserts used for validation; cross-field search matches

**File:** `server/airports.py:27, 208`; `server/device_config.py:99-100`; `server/detection.py:361, 406, 429`; `server/airports.py:149`
**Issue:** There are three small defects.
1. `_DESIGNATOR_RE` and `_DESIGNATOR_PAIR_RE` use `\d` without
   `re.ASCII`. Arabic-Indic digits pass the shape check, and are
   rejected only later by the dict or equality lookup.
2. `assert isinstance(...)` is used after validation. It is stripped
   under `python -O`, though the earlier lookups already guarantee the
   types.
3. The search index joins ICAO, IATA, name and city with spaces into one
   string, so a query such as "g cdg" can match across the field
   boundary.
**Fix:**
1. Use `[0-9]`, or compile with `re.ASCII`.
2. Replace the asserts with explicit `if not isinstance(...)` raises.
3. Match each field separately.
