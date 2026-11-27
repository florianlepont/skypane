---
phase: 67-project-and-code-optimisation
plan: 07
subsystem: server
tags: [dedup, refactor, fleet]
requirements: [QUAL-01]
key-files:
  modified:
    - server/plane/fleet_artwork.py
    - server/plane/fleet_set_defaults.py
---

# Phase 67 Plan 07: Server helper dedup Summary

Two server helpers were collapsed to one definition each; two others were
AST-compared and deliberately left alone.

## Merged

- `_merged_hashes`: defined in `fleet_registries`, imported by `fleet_artwork` under the same name (commit 790b6757).
- `_read_json`: defined in `fleet_default_types`, imported by `fleet_set_defaults` under the same name (commit 3194c4a3).

Both bodies were AST-identical (`ast.dump` equal after normalising the name) and use no module-level globals, so the merge cannot change behaviour.

## Left unmerged

- `_read_marker` (fleet_artwork vs fleet_registries): AST-identical, but each reads its own module-level `MARKER_FILENAME` (`illustration_migration.json` vs `airline_registry_migration.json`). Merging made `test_fleet_migrate` fail (artwork idempotency), so it was reverted. Not a true duplicate.
- `_lettering_box` (giant/compose.py) vs `lettering_box` (giant/compose_c.py): not AST-identical; compose_c's version has a docstring. Merging would change the AST, and the plan allows identical bodies only.

## Verification

- Collected test ids before (origin/main) and after: 17602 each, `comm -23 before after` empty.
- Fleet/migration subset: 439 passed. ruff and mypy green. Full server + stub-server suite: 4374 passed, 4 skipped (root-only permission tests); freeze and golden render tests included.
- No golden, fixture or baseline files touched.

## Deviations

[Rule 1] `_read_marker` merge attempted, broke tests, reverted (see above). Nothing else.
