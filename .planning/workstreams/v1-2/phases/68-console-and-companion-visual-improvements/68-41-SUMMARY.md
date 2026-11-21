---
phase: 68-console-and-companion-visual-improvements
plan: 41
subsystem: server, companion, deploy
tags: [airline-names, fleet-wide, migration, rename, access-matrix, backup]
requirements: [CON-01]
key-files:
  created:
    - server/plane/fleet_registries.py
    - server/test_fleet_registries.py
    - companion/test_fleet_airline_names.py
    - companion/test_airline_rename_manual.py
    - companion/test_browser_airline_rename_manual.py
  modified:
    - server/device_dirs.py
    - server/plane/manual_resolutions.py
    - server/plane/name_overrides.py
    - server/plane/airline_default_types.py
    - server/fleet_migrate.py
    - companion/airline_actions.py
    - companion/post_actions.py
    - companion/routes.py
    - companion/pages/airlines_page.py
    - companion/pages/airline_table.py
    - companion/pages/airline_rows.py
    - companion/pages/audit_page.py
    - companion/i18n_fr/airlines.py
    - companion/i18n_fr/admin_lifecycle.py
    - deploy/backup/skypane_backup.py
    - deploy/README.md
    - companion/testdata/render_baseline.json
metrics:
  completed: 2026-11-21
---

# Phase 68 Plan 41: Fleet-wide airline names and a real Rename for hand-named airlines

Naming, renaming or deleting a hand-given airline name, setting a name override or a default aircraft type is now visible on every frame (one registry per fleet), existing installs keep every name through an idempotent deploy-time merge, and an administrator can rename a hand-named airline from its row menu without losing its artwork or default type. Task 5 (owner's visual review) is captures only; the owner has not answered yet.

## Commits

- `5b3e8e8d` Task 1: `device_dirs.fleet_root_for` and the three `*_path` functions resolve to the fleet root; stale guard on `/airlines/resolve`.
- `91fe24ce` Task 2: `server/plane/fleet_registries.py`, hook in `fleet_migrate`, marker in the backup include list, README section and rollback caveat.
- `aa4ea062` Task 3: `POST /airlines/rename/manual`, Rename item and dialog, shared artwork carry-over, audit label, access matrix rows.
- `5c919ee8` Task 4: route-list tests, the hand-named dialog test, the one render baseline regeneration.

## What changed

- One seam, no caller edited: `manual_resolutions_path`, `name_overrides_path` and `default_types_path` join their file name onto `device_dirs.fleet_root_for(state_dir)` (pure shape check: parent `devices`, leaf `d_` plus 8 hex; the result is the input or the input minus two trailing segments). `git diff` shows no change in `poll_cycle.py`, `page_context.py`, `freshness.py` or any loader call site. The three modules create `dirname(path)` before writing. `airline_default_types.load_default_types_file(path)` is the path-based reader the migration uses (state-dir loaders would return the fleet file).
- Stale guard (`_handle_manual_resolve_post`): a prefix already in the fleet registry is refused with the existing stale flash, so a stale unidentified row on another frame cannot overwrite a name.
- Merge (`fleet_registries.plan_merge` / `apply_merge`, called from `fleet_migrate.migrate` on every path, including the fleet.db "nothing to do" one): newest `created_at` wins, then the root (live frame), then the lowest frame id; unparsable stamp = oldest; default types: root, then lowest frame id. Losers are printed (prefix, both names, both stamps, frame ids) and the last 50 recorded in `airline_registry_migration.json`, which also stores the SHA-256 of each per-frame file merged (an unchanged file is not merged again, so a name deleted afterwards is not resurrected; a changed one is merged once more). Per-frame files are opened read-only and never modified; the marker is written last; a write failure raises `OSError` (deploy exits 1 before the symlink swap). Refusals (printed, nothing deleted): override names equal to another built-in airline's name or another airline's override, entries beyond the 200/300 caps, symlinked or non-`d_xxxxxxxx` directories, symlinked or oversized (over 1 MiB) or invalid-JSON per-frame files.
- Rename: `manual_resolutions.rename_entries(state_dir, prefixes, name, taken_keys)` (one atomic write under `_WRITE_LOCK`, fresh `created_at`, refusals write nothing); `airline_actions.handle_manual_rename` (ADMIN_DEVICE, `csrf=True`, in `_ACTION_KEYS`) re-validates the prefix against the fleet registry, renames every prefix whose stored name has the same artwork key, refuses names held by a built-in airline, an override or a manual entry outside the group, carries artwork and default type, writes the audit row `airline.rename_manual` (target = new artwork key, detail = old and new names). `app.py` untouched (1496 lines).
- Artwork carry-over is one function, `airline_actions.carry_artwork_to_new_name(state_dir, from_name, to_name, suffixes)`, used by both the new rename and the built-in rename (`post_actions._carry_artwork_to_new_name` keeps its signature and delegates). It copies, never moves, only when the new key has no artwork, into the acting frame's `state_dir` (plan 42 makes that directory the fleet one). Default type: copied to the new key when it has none, old entry stays.
- UI: `airline_table._menu_parts` (the single menu builder for table rows and known-by-name rows) shows the existing `row-menu__item` "Rename" link before "Delete my name" for a hand-named row, and returns a dialog from `airline_rows.manual_rename_dialog_html`, which shares one private helper with the built-in dialog (same id scheme, title, field, Save, Cancel, `ui_modal.dialog_html`); only the hidden field (`prefix` instead of `airline`) and the subtitle differ. New string `airlines.rename_manual_hint` with its French. No new CSS.
- Backup: #507 had already put the three airline files and `airline_suggestions.json` in the root list and the two override/default-type files in the per-device list; this plan only added `airline_registry_migration.json` (root) and extended the tests.

## Decisions

- Storage stays JSON-file-per-concern, one location per file (the fleet root).
- `RENAME_NAME_TAKEN` is the same string as `name_overrides.SET_NAME_TAKEN` (the latter now aliases the former) so one vocabulary maps onto flash keys.
- `airlines_page.manual_prefix_renamable(prefix)` is the one predicate for "this hand-named prefix can be renamed" (not named by the static table and not a known-by-name built-in); the menu and the handler both use it.
- Merge size guard added: a per-frame file over 1 MiB is skipped and reported (the existing loaders read whole files, so the plan's "bounded by the same loaders" did not hold by itself).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Existing tests encoded the per-frame model.** `companion/test_device_actions.py` asserted that a registry write on one frame left the other untouched; rewritten to assert the fleet file at the root, no registry file in a frame directory, and that the artwork carry reaches only the acting frame (until plan 42). `test_airline_sheet`, `test_device_routes`, `test_route_table`, `test_csrf`, `test_access_matrix`, `test_airline_known_rows` and `deploy/tests/test_backup.py` were updated for the new route, the hand-named dialog and the marker.

**2. [Rule 1 - Bug] "name-only" prefixes.** The plan says a prefix named by the built-in "known by name only" table is superseded and gets its own built-in Rename. The page does not render it that way (its `superseded` flag only looks at the static prefix table; a manual name for such a prefix, for example KLM, shows as a separate hand-named row although the built-in name wins at runtime). To avoid offering a rename that changes nothing, both the menu and the handler refuse it (stale) through `manual_prefix_renamable`. The page's own `superseded` flag was not changed (plan 40's domain).

**3. Override-collision approximation.** Entries already in the root are never removed by the merge; a merged override that collides with a built-in name or with a root/already-accepted override is skipped (newest first among device candidates). The "older one loses" rule is therefore exact between device candidates and approximate against the root.

## Design-system divergences

The Skill tool was not available in this run; `.claude/skills/sketch-findings-skypane` was not loaded through it. I reused the existing CSS and tokens only and added no rule.

Before/after captures (1440 and 390 px; EN light and FR dark) are in `/tmp/claude-0/-home-user-skypane/1ebaf6ab-90c3-5997-a366-609c87d2992c/scratchpad/p41/{before,after}/`, named `{width}-{lang}-{theme}-{editor-full,menu-known-view,menu-known-full,menu-table-view,menu-table-full,dialog,dialog-full,success,success-full}.png` (`before` has no dialog or success: the item did not exist). The owner-review set (all four language/theme pairs at 1440, 390 and 360) is in `.../scratchpad/p41/checkpoint/` with the same names. The capture script is `.../scratchpad/p41/tools/capture.py`.

Divergences between before and after, each with its reason:

1. The "..." menu of a hand-named row gains "Rename" as its first item, above the "Delete my name" caption and form. Reason: the request; same `row-menu__item` link markup as the built-in rows' Rename, same panel.
2. The dialog is the built-in Rename dialog (title "Rename the airline" / "Renommer la compagnie", field, Save, Cancel, centred on desktop, bottom sheet on phone) with a different subtitle: "The new name applies to every frame. Flights already stored keep their name." (FR: "Le nouveau nom s’applique à tous les cadres. Les vols déjà enregistrés gardent leur nom."). Reason: owner wording; the built-in subtitle ("replaces the original on the companion and on the frame") would be wrong for a name with no original.
3. On a hand-named row whose menu panel opens near the bottom of the viewport, the panel is cut by the viewport in the view captures (existing behaviour of the panel, unchanged; the full-page captures show it complete).
4. A superseded hand-named row (the seeded RYR one) still shows only "Delete my name": no Rename (see deviation 2). Unidentified rows have no menu, as before.
5. Pixel diff of the closed editor page before versus after differs only in the aircraft thumbnail column (image decode timing); no layout, spacing or text moved.
6. The success flash is the existing "Airline name saved — Flights and Home show it now, and the frame will use it once it next wakes and polls." (the built-in rename's text); the plan listed `FLASH_KEY_RENAMED` and no new text.

## Rollback caveat for the owner

The per-frame registry files are never modified, renamed or deleted by this release, so rolling back to the previous release works. After a rollback every non-live frame sees its own old names again, and names given or changed after the upgrade exist only in the root files (visible to the previous release on the live frame only). A later roll-forward merges again only the per-frame files that changed meanwhile (hash differs from the marker), by the same conflict rule, which can bring back a name that was deleted fleet-wide before the rollback: re-check the Airlines editor after a roll-forward that followed a rollback. The frozen per-frame copies are removed by a later release after the rollback window (owner: yes, later; not built here; to be recorded as an item for plan 32 and STATE.md's deferred list, neither edited by this plan).

## Deploy checklist

What `deploy/activate.sh` does at deploy (no edit to the script): pre-migration backup (archives the root files and every per-frame file, the only copy of the data being merged), `python3 -m server.fleet_migrate --dry-run`, the real run, all before the symlink swap; never at service start.

1. Before deploy: nothing to configure. Ship plans 41 and 42 in the same deploy (or 42 right after): until 42, a rename carries artwork only into the acting frame's directory.
2. Read the dry-run log in the deploy output. Lines start with `airline names:`:
   - `would merge N per-frame file(s) into the fleet registry`, then one `would merge <registry>: A added, R replaced` per registry (`manual_resolutions`, `name_overrides`, `default_types`);
   - one `conflict <registry> <prefix>: keep '<name>' [frame <id>, <stamp>] over '<name>' [frame <id>, <stamp>]` per conflict (the first name wins; frame `live` is the root);
   - `not merged ...` (override refused, cap reached) and `skipped ...` (symlink, oversized, invalid JSON) lines;
   - nothing at all when no frame has a per-frame registry file; `airline names: nothing to do` when everything was merged earlier.
3. The real run prints the same lines with `merged`; a failure prints `error: OSError` and exits 1 (the deploy stops before the swap).
4. Afterwards verify: `airline_registry_migration.json` exists in the state root and lists each merged per-frame file; open the Airlines editor on two frames and confirm the same hand-named airlines; check each conflict line's winner is the name you want (a loser can be restored by Rename); run the migration again (or the next deploy) and confirm `nothing to do`; nightly backup shows no drift line for the airline files.
5. Rollback: see the caveat above; do not edit or delete the per-frame files.

Sample dry-run on a realistic copy (frame b newer name wins; root older):

```
airline names: would merge 4 per-frame file(s) into the fleet registry
airline names: would merge manual_resolutions: 1 added, 1 replaced
airline names: would merge name_overrides: 0 added, 0 replaced
airline names: would merge default_types: 0 added, 0 replaced
airline names: conflict manual_resolutions OCN: keep 'Oceanic Airways' [frame d_0000000b, 2026-03-01T00:00:00+00:00] over 'Oceanic' [frame d_0000000a, 2026-02-01T00:00:00+00:00]
airline names: conflict manual_resolutions OCN: keep 'Oceanic Airways' [frame d_0000000b, 2026-03-01T00:00:00+00:00] over 'Oceanic Air' [frame live, 2026-01-01T00:00:00+00:00]
airline names: not merged name_overrides AFR from frame d_0000000a: 'Transavia France' is the name of the built-in airline Transavia France
airline names: conflict default_types air-france: keep 'A320' [frame live] over 'A321' [frame d_0000000b]
```

The real run printed the same with `merged`; a second run printed `airline names: nothing to do` and changed no byte; the per-frame files' hashes were identical before and after.

Note: the existing loader prints `manual_resolutions: N entry/entries will be dropped from <path> on the next write` when a file holds invalid entries. For a per-frame file this only means those entries were not merged (the file is never written); for the root file it means the rewrite drops them.

## Tests

Run locally on the final tree (`5c919ee8`), `SKYPANE_REQUIRE_BROWSER=1`, `server/.venv/bin/python`, through `scripts/run-all-tests.sh`:

- Core group: 12413 passed, 7 skipped (permission-bit tests under root), 0 failed.
- Browser group, shards 0 to 4 of 5: 1197 passed; 700 passed, 1 skipped; 920 passed; 666 passed; 603 passed; 0 failed.
- An earlier core run (before the route-table tests were updated) had 5 failures, all caused by this plan and fixed: `test_airline_sheet::test_manual_only_and_unidentified_rows_have_no_rename_dialog` (a hand-named row now has a dialog), `test_device_routes::...test_flagged_routes_equal_the_explicit_list` and `test_route_table` (two tests, the new route), and `test_render_baseline` (the new unauthenticated sample).
- Gates: `ruff check .`, `mypy` (48 files, `server/plane/fleet_registries.py` added), `check_function_size.py check --max 80 server stub-server` (1197 functions, none over), `check_comment_history.py check` exit 0, `companion/app.py` 1496 lines, largest JS file 1227 lines, no change to `server/requirements.*`, no `enable_socket`.

New tests: `server/test_fleet_registries.py` (15: merge without conflict, newest wins with logged losers, tie order, unparsable stamp, listing-order independence, idempotence and no resurrection, changed source merged once, override invariants, default types, caps, hostile entries, symlink and bad-name cases, invalid and oversized files, live files never a source, write failure); `server/test_fleet_migrate.py` (dry-run writes nothing and per-frame files byte-identical, real run, second run unchanged, silent without frame files, reported on the fleet.db "nothing to do" path, write failure exits 1); `server/test_device_dirs.py`, `test_manual_resolutions.py`, `test_name_overrides.py`, `test_airline_default_types.py` (seam, path-based loaders, `rename_entries`); `server/test_poll_loop.py` (a name and an override given through frame A reach frame B's own poll cycle, each file read once; a rename reaches B's next flight); `companion/test_fleet_airline_names.py` (name, override and default type visible on another frame; stale-row guard); `companion/test_airline_rename_manual.py` (route, group rename, audit row, 11 refusals writing nothing, CSRF, artwork and default type carried and not overwritten, copy failure, built-in rename unchanged, owner/co-manager/anonymous refusals, GET not routed, row menu, hostile name escaped); `companion/test_browser_airline_rename_manual.py` (12: menu order, dialog, 44 px, no overflow, 100-character name, 390 and 1440 px, EN light and FR dark, submit and flash, Escape and Cancel send no request); `deploy/tests/test_backup.py`; access matrix and CSRF flag rows.

## Open owner questions and notes

- Task 5: review the captures in `.../scratchpad/p41/checkpoint/` (item order, subtitle wording, 44 px targets, nothing else changed). No answer yet.
- Open PRs at the time of the run: #506 (plan 28, Users, branch `phase-68-visual-improvements-13`) and #481 (dependabot, playwright). #503 and #507 are merged. #506 and this work do not touch the same files except possibly `companion/pages/audit_page.py` and `companion/i18n_fr/admin_lifecycle.py` (one added line each here) and `companion/testdata/render_baseline.json`. My baseline change is one entry (the unauthenticated sample `POST /airlines/rename/manual`, `/login?expired=1`, 303); whichever of #506 and this merges second regenerates it with `PYTHONPATH=.:test-support server/.venv/bin/python test-support/companion_render_snapshot.py --write`. Phase 64 files edited (`airlines_page.py`, `airline_table.py`) have no open PR on them.
- Build was not split (one run).
- The venv is Python 3.13 (production is 3.14); mypy runs with `python_version = "3.14"` as configured.
- Permission-bit tests skip under root (7 skips, same as before this plan).
- Deferred cleanup of the frozen per-frame registry files (and the `DEVICE_INCLUDE_FILES` entries and README caveat) is not built; record it for plan 32 and STATE.md's deferred list.
