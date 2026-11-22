---
phase: 68-console-and-companion-visual-improvements
plan: 42
subsystem: server, companion, deploy
tags: [artwork, fleet-wide, migration, backup]
requirements: [CON-01]
key-files:
  created:
    - server/plane/fleet_artwork.py
    - server/test_fleet_artwork.py
    - companion/test_fleet_artwork_pages.py
  modified:
    - server/plane/illustrations.py
    - server/fleet_migrate.py
    - server/test_fleet_migrate.py
    - server/test_illustrations.py
    - server/test_poll_loop.py
    - deploy/backup/skypane_backup.py
    - deploy/tests/test_backup.py
    - deploy/README.md
    - companion/test_airline_editor.py
    - companion/test_device_actions.py
    - pyproject.toml
metrics:
  completed: 2026-11-21
---

# Phase 68 Plan 42: Fleet-wide artwork

A picture uploaded for an airline on any frame is now the picture every frame's Airlines editor, preview and poll render use. Existing installs keep every picture through a deploy-time, idempotent, loss-free merge of the per-frame image directories into one fleet directory.

## Commits

- `e166cc6f` Task 1: `override_dir_for_state_dir` resolves to the fleet root (one seam, no caller edited); two-frame tests.
- `589029c4` Task 2: `server/plane/fleet_artwork.py`, hook in `fleet_migrate`, backup list, README section and rollback caveat, `mypy` module list.

## What changed

- One seam: `illustrations.override_dir_for_state_dir(state_dir)` returns `<fleet_root_for(state_dir)>/illustration_overrides` (still `None` for a falsy argument, still never creates the directory). The render path, the editor pages, upload and delete routes, the picture route, the cache buster, the previews and plan 41's artwork carry all go through it, so nothing else changed. `server.plane.illustrations` now imports the leaf `server.device_dirs` (no cycle).
- Merge (`fleet_artwork.plan_merge` / `apply_merge`, called by `fleet_migrate.migrate` beside plan 41's registry merge on every path, dry-run and real): the latest `st_mtime_ns` wins per file name; a tie goes to the fleet file, then the lowest device id; copies keep the source's atime/mtime; identical bytes are no conflict. Every loser (a replaced fleet file included) is copied first to `illustration_conflicts/<device id or live>/<file>` (numeric suffix `.1`, `.2` before `.png`, same bytes already archived are not archived twice). Marker `illustration_migration.json` (SHA-256 per `<device id>/<file>`, first 50 conflicts) is written last; an unchanged source is never merged again (no resurrection), a changed one is merged once more. A write failure raises `OSError` (deploy exits 1 before the swap).
- Safety kept: regular files only (`lstat`), name `^[a-z0-9][a-z0-9-]*\.png$` and `override_path_for_key` guard, size at most the upload cap (`MAX_UPLOAD_BYTES`, a duplicated constant; a test asserts it equals `companion.upload_form.MAX_UPLOAD_BYTES`), `validate_illustration_file` (header-only PNG, dimension and pixel cap). Dot-files and `*.tmp` are reported as skipped, symlinked image directories, symlinked or oddly named `devices/<id>`, and a symlinked fleet directory are skipped and reported. Caps `MAX_MERGED_FILES = 1000`, `MAX_MERGED_BYTES = 256 MiB` per run (latest first; the rest stay pending, not marked merged).
- Per-device image directories are opened read-only and never modified (tests compare bytes and mtimes before and after).
- Backup: `INCLUDE_DIRS` gains `illustration_conflicts`, `INCLUDE_FILES` gains `illustration_migration.json`; the root and per-device `illustration_overrides` entries stay.
- README: "Fleet-wide airline names and artwork" section (storage, conflict rule, archive, log reading, caps), updated per-device backup paragraph, and the artwork rollback caveat next to plan 41's.

## Divergences

1. Plan 41 helper names: `fleet_registries.frame_state_dirs(root)` (root first, then valid `devices/<id>`), `MARKER_FILENAME` (`airline_registry_migration.json`), and the `plan_merge` / `apply_merge(root, plan, now=None)` / `report_lines(plan, dry_run)` split were reused as is. `fleet_artwork` takes only `frame_state_dirs` and `LIVE_LABEL` from it. `fleet_artwork.plan_merge` returns an `ArtworkPlan` with `needs_write`, `report_lines` and `apply_merge` mirroring plan 41.
2. Theme preview cache key: `theme_preview.preview_signature` does NOT include an artwork stamp (nor the airline names); previews are cached per frame state directory and keyed on theme, crop, version, layout and the live event id. A new picture therefore shows in a cached preview of the same flight only once the key changes (new flight or cache version). Behaviour is unchanged by this plan; flagged for the owner.
3. Dry-run on a realistic state (two frames, one conflict against the fleet file, one conflict between frames, one oversized file):

```
artwork: would merge 4 picture(s) from 2 frame(s) into the fleet directory: 2 new, 1 replaced, 0 identical, 2 conflict(s)
artwork: skipped huge.png of frame d_0000000b: over the 4194304-byte upload cap
artwork: conflict air-france.png: keep [frame d_0000000a, 2024-03-09T16:00:00+00:00, 2889 bytes] over [frame live, 2023-11-14T22:13:20+00:00, 2888 bytes]
artwork: conflict oceanic.png: keep [frame d_0000000b, 2024-01-11T19:06:40+00:00, 2890 bytes] over [frame d_0000000a, 2023-11-14T22:13:20+00:00, 2888 bytes]
```

   The real run printed the same with `merged`; a second run printed `artwork: nothing to do` (plus the still-skipped `huge.png` line) and changed no byte. "4 picture(s)" counts per-frame files settled by the run (one per frame file), not distinct names.
4. Callers that did not go through `override_dir_for_state_dir`: none found. All other tests that seeded a per-device image directory were few: `companion/test_airline_editor.py` (`_override`, `Rig.stored`) and `companion/test_device_actions.py` (the upload test, now `test_illustration_upload_lands_in_the_fleet_directory_only`) were updated to the fleet root. Tests that seed at `server.state_dir` were already at the root and unchanged.
5. Open pull requests at the time: #510 (plan 41, the base), #511 (`fix-fleet-migrate-pending-frames`, touches `deploy/README.md`, `server/fleet_migrate.py`, `server/test_fleet_migrate.py`: expect a textual merge conflict in those three files, no logical conflict, `migrate()` and the test module's end are where this plan adds), #481 (dependabot). No Phase 64 file is edited by this plan.
6. `companion/testdata/render_baseline.json`: unchanged (`companion/test_render_baseline.py` passes without regeneration; no rendering changed).
7. Plan listed pixel-cap, truncated PNG etc. under Test 4 of Task 2 as "skipped with a reason"; the reason printed for an invalid PNG is the first validation problem, truncated to 80 characters. The "not a regular file" and "symlink" reasons are printed for non-regular entries.
8. `deploy/tests/test_docs.py` passes unchanged with the README edit (part of the core run).
9. Archiving does not count against the per-run caps (only copies into the fleet directory do): a frame can only contribute files that pass the upload-size check, and each is archived at most once.

## Deferred (not built)

ART-10: after the rollback window a later release deletes the frozen per-device `illustration_overrides/` directories (and plan 41's frozen registry copies), with the `DEVICE_INCLUDE_DIRS` entry and README caveats. To be recorded for plan 32 and STATE.md's deferred list (not edited here).

## Tests

Final tree, `SKYPANE_REQUIRE_BROWSER=1`, through `scripts/run-all-tests.sh`:

- Core group: 12453 passed, 7 skipped (permission-bit tests under root), 0 failed (plan 41 had 12413; 40 new tests).
- Browser group shards 0 to 4 of 5: 1197 passed; 700 passed, 1 skipped; 920 passed; 666 passed; 603 passed; 0 failed. Shard 1 failed once on the first pass (`test_browser_space_switch.py::test_one_tap_on_the_more_panel_switch_moves_between_the_two_spaces`, a Playwright timing error under load, unrelated to artwork: `Cannot read properties of null (reading 'open')`); the file passes alone (32 passed) and the whole shard passed on a re-run. Nothing was changed, skipped or loosened.
- Gates: `ruff check .`, `mypy` (49 files, `server/plane/fleet_artwork.py` added), `check_function_size.py check --max 80 server stub-server` (1220 functions, none over), `check_comment_history.py check` exit 0, `companion/app.py` 1496 lines (untouched), no JS or `server/requirements.*` change, no `enable_socket`.

New tests: `server/test_fleet_artwork.py` (20: no-conflict merge with bytes and mtimes and untouched frame files, latest time wins with archive of every loser, tie order over all six listing orders, fleet-file tie, numeric archive suffix, identical bytes, idempotence and no resurrection and re-merge of a changed source, dry-run plan writes nothing, hostile and invalid candidates, live directory never a source, symlinked fleet directory, file and byte caps, upload-cap equality with the companion, write failure), `server/test_fleet_migrate.py` (4: dry-run writes nothing then real run then idempotent, silent without pictures, one report with the registry merge, write failure exits 1), `companion/test_fleet_artwork_pages.py` (12: seam, upload on one frame listed, served and cache-busted on another, delete from another frame, "Known by name only" to table row, six refusals writing nothing, rename carry visible on another frame, owner refused), `server/test_poll_loop.py` and `server/test_illustrations.py` (one each), `deploy/tests/test_backup.py` (one).

## Deploy checklist for the owner

`deploy/activate.sh` needs no edit: pre-migration backup (archives the root and every per-device image directory, the only copy of the data being merged), `python3 -m server.fleet_migrate --dry-run`, the real run, all before the symlink swap; never at service start. Ship plans 41 and 42 in the same deploy.

1. Read the dry-run log in the deploy output. Lines start with `artwork:`: `would merge N picture(s) from M frame(s) ...: A new, R replaced, I identical, C conflict(s)`; one `conflict <file>: keep [...] over [...]` per loser (frame `live` is the root); `skipped ...` / `not merged ...` for refused files and cap overflow; nothing when no frame has pictures; `artwork: nothing to do` when everything was merged earlier.
2. The real run prints the same with `merged`; a failure prints `error: OSError` and exits 1 before the swap.
3. Afterwards: `illustration_migration.json` exists in the state root; `illustration_overrides/` holds the union; each conflict's loser sits in `illustration_conflicts/<frame>/` (restore one by copying it back, or by uploading it again); open the Airlines editor on two frames and see the same pictures; run the migration again (or deploy again) and see `artwork: nothing to do`; the next nightly backup shows no drift line.
4. Rollback: see the README caveat; do not edit or delete the per-device image directories.

## Open owner questions

- Archive folder name `illustration_conflicts` and the caps (1000 files, 256 MiB) went in as agreed.
- Theme previews are not invalidated by a new picture (divergence 2): say if you want an artwork stamp in the preview key.
- #511 overlaps `fleet_migrate.py`, its test and the README: whichever merges second resolves the three-file conflict.
