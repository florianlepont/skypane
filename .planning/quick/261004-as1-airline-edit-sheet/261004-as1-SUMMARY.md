---
quick_id: 261004-as1
subsystem: companion
tags: [airlines, names, overrides, i18n]
completed: 2026-10-04
---

# Quick 261004-as1: Airline sheet

## Investigation

- **Prefix to name today.** `enrich.resolve_route()` tries adsbdb first
  (route plus its `airline_name`, then the fixed `_AIRLINE_NAME_CORRECTIONS`
  table); on no route it falls back to the built-in `_ICAO_AIRLINE_PREFIXES`
  table (`"airline_only"`), and only on a miss of both to the manual registry
  (`"manual"`, "Resolved by hand"). The static table beats a manual entry for
  the same prefix, which is the "superseded" concept.
- **Artwork key.** Always `illustrations.normalise_airline_key(name)` (ASCII
  slug); `select_illustration()` and every page (Flights, Home, Airlines)
  derive it from the name string, so a name change changes the key and would
  orphan the picture.
- **New precedence (highest first):** owner override, adsbdb after corrections,
  built-in table, manual resolution. The override is by prefix and replaces the
  name whatever the source; the route's source label is unchanged.

## Decisions

- **Registry:** new `{state_dir}/airline_name_overrides.json`, same contract as
  manual resolutions (shared loader/`check_name()` validation: empty, too
  long, reserved, unusable; 200-entry hard cap; atomic write; lock). Separate
  file so stale manual entries for built-in prefixes do not suddenly start
  winning. Reset deletes the entries.
- **Scope change (owner, mid-task): the name applies to stored history too.**
  Chosen: re-resolve at read time, not a row rewrite.
  `history_db.recent_runway_events(..., airline_names=)` swaps the name in by
  callsign prefix as rows are read (Flights, Home recent flights, colour-rule
  suggestions, theme preview). Rows are never modified, so reset restores the
  original (built-in or adsbdb) name for free, no migration, no transaction to
  coordinate with `poll.lock`/WAL, nothing to cap. The poll loop's storage
  format is untouched. Already-archived frame pictures (gallery PNGs) are
  images and keep the text they were rendered with.
- **Artwork follows the name by copy.** On rename the current artwork (base and
  type variants, vendored or owner-uploaded) is copied to the new name's key
  as owner overrides, only if the new key has no artwork at all; never moved.
  The tile shows and edits the artwork of the name now in use; upload and
  serve membership include the renamed keys. Reset returns to the old key,
  whose files were never touched; pictures added under the new name stay
  stored there and reappear if the same name is chosen again.
- **Sheet** is identified by the built-in airline name; the server re-derives
  its prefixes from the built-in table (never from the browser). Prefixes are
  shown read-only; editing or adding prefixes is out of scope (not done).
  Naming a built-in airline with its own built-in name is treated as reset.
  Airlines injected only by a manual resolution keep the existing flow and have
  no sheet.
- **No-script path:** the pencil is a link to `/airlines?sheet=<artwork key>`
  rendering the sheet in page; with script the same URL opens the dialog.
  (`?edit=` is a retired literal guarded by an existing test, hence `sheet`.)
- Vocabulary: five attributes added to every trigger (`airline`, `airline-name`,
  `airline-prefixes`, `renamed`, `sheet-key`), empty where unused; guard tests
  updated. `panel-lookup.js` reads `location.search` once.

## Verification

See the final report for suite counts. Screenshots (390/1280, light/dark,
EN/FR, before and after) are in the session scratchpad `shots-airline-sheet/`.
