# Phase 32 Migration Ledger

**Purpose (32-CONTEXT.md "Migration ledger"):** one row per pre-migration check of the 15
server-side harnesses (`server/test_*.py` ×14 + `stub-server/test_poll_cycle.py`), mapping the
old harness + check label to either a new pytest node id ("ported") or an explicit "deleted"
disposition with a reason. Parametrisation and consolidation are allowed — several old checks
may map to one node id when consolidated — as long as every old check maps to a specific node
id or a documented deletion (parametrised ids count as distinct mappings).

**This file is a scaffold**, written before any of the 15 harnesses has been rewritten
(`32-02-PLAN.md` Task 2). It is regenerated wholesale by `32-13-PLAN.md`, running
`32-ledger-check.py --assemble` once every harness's own migration plan has landed its
`32-ledger/<key>.md` fragment. **Do not hand-edit the status table below once fragments start
landing — `--assemble` overwrites this whole file.**

## Format

Each migrating plan writes its own fragment at `32-ledger/<key>.md` (disjoint per-harness
files, so parallel migration plans in the same wave never conflict on this file). A fragment's
shape:

```
# Ledger: <harness path>

Baseline: 32-BASELINE/<key>.txt (<total> checks)

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | <label copied verbatim from the baseline PASS/FAIL line> | ported | <harness>::<test_function>[<param id>] |
| 2 | <label> | deleted | <concrete reason the check no longer applies> |
```

Rules:
- `Disposition` is one of `ported`, `deleted`, `pending` (`pending` only for a harness migrated
  in stages across more than one plan — none is currently planned; a `pending` row requires
  `--allow-pending` to count as mapped).
- A `ported` cell is the FULL pytest node id, e.g.
  `server/test_dither.py::test_panel_palette_image_is_unpadded`, or a parametrized id,
  e.g. `server/test_config_history.py::test_theme_round_trips[dark]`.
- Several old checks may map to the SAME node id when the migration consolidates them into one
  parametrized test — each old label still gets its own ledger row.
- A `deleted` row's reason must be concrete (why the check no longer applies), never blank.
- `|` inside an "Old check label" or reason cell is escaped as `\|` (labels are copied verbatim
  from the harness's own PASS/FAIL transcript, which can itself contain `|`, e.g. a check
  naming a set like `{0,1,2,3,4,5}` — no `|` occurs in this phase's actual labels, but the
  tool and format support it regardless).

## Verification

Per-harness, once its fragment exists:

```bash
server/.venv/bin/python3 .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger-check.py <harness>
```

This proves: the fragment's row count equals the baseline's check count; every row's label
matches exactly one baseline PASS/FAIL line (and vice versa — no baseline check is left
unmapped); every `ported` node id exists in `pytest --collect-only -q` output; every `deleted`
row carries a non-empty reason; and, once the harness carries ported/deleted rows, its source
no longer contains `EXPECTED_CHECK_COUNT` or `def check(` (the pre-migration idiom this whole
phase replaces).

Once all 15 fragments pass, `32-13-PLAN.md` runs `--assemble` to regenerate this file with the
real per-harness tables in place of the status table below.

## Status

Baseline counts below come from `32-BASELINE/INDEX.md` (captured 2026-09-23,
commit `3a6665c924df8077166e67923d31bca0177214b2`, Python 3.11.15, euid 0 — see that file's own
`## Notes` section for the 2 root-sandbox-only FAILs in `test_manual_resolutions.py`, WR-11,
not migration-relevant defects).

| # | Harness | Baseline checks | Migrating plan | Status |
| --- | --- | ---: | --- | --- |
| 1 | `server/test_dither.py` | 6 | 32-03 | pending |
| 2 | `server/test_runway_config.py` | 15 | 32-03 | pending |
| 3 | `server/test_notify.py` | 8 | 32-03 | pending |
| 4 | `server/test_panel_preview.py` | 11 | 32-03 | pending |
| 5 | `server/test_pipeline_e2e.py` | 7 | 32-03 | pending |
| 6 | `server/test_manual_resolutions.py` | 23 | 32-04 | pending |
| 7 | `server/test_colour_rules.py` | 33 | 32-04 | pending |
| 8 | `server/test_enrich.py` | 60 | 32-04 | pending |
| 9 | `server/test_illustrations.py` | 60 | 32-05 | pending |
| 10 | `server/test_plane_detection.py` | 47 | 32-05 | pending |
| 11 | `stub-server/test_poll_cycle.py` | 46 | 32-06 | pending |
| 12 | `server/test_config_history.py` | 90 | 32-07 | pending |
| 13 | `server/test_calendar_rules.py` | 113 | 32-08 | pending |
| 14 | `server/test_render.py` | 140 | 32-09 | pending |
| 15 | `server/test_poll_loop.py` | 110 | 32-10 | pending |

**Grand total: 769 baseline checks across 15 harnesses**, all currently `pending` (no fragment
exists yet — this scaffold predates every migration plan). "pending" here describes the
scaffold's own status column, distinct from the ledger fragment `Disposition` value of the same
name (32-RESEARCH.md's batch plan: `32-11`/`32-12` handle the remaining CI/lock-file/coverage
work items TST-04 through TST-09 and are not harness-migration plans, so they own no row here).

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Scaffolded: 2026-09-23, before any of the 15 harnesses was rewritten (32-02-PLAN.md Task 2)*
