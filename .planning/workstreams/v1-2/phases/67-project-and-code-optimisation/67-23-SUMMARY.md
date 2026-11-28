---
phase: 67-project-and-code-optimisation
plan: 23
subsystem: docs
tags: [architecture, deploy-runbook, first-pass]
requires: ["67-17", "67-18"]
affects: ["ARCHITECTURE.md", "deploy/README.md"]
key-files:
  modified: [ARCHITECTURE.md, deploy/README.md]
metrics:
  tasks: 1
  completed: 2026-11-28
---

# Phase 67 Plan 23: Documentation update (FIRST PASS, to be completed after plans 19 to 22)

Docs only. Plans 19 to 22 (the retirements) have not run, so only what is real on main is documented.

## What changed

- `ARCHITECTURE.md`, "Persistent state" / "Migrations": rewritten for the shared module `server/sqlite_migrations.py` (policies `immediate`/`refuse` for fleet.db, `idempotent`/`keep` for history.db, shared busy timeout) and the read-only `report` command with its statuses and exit codes. The "documented, not unified" decision is removed.
- `ARCHITECTURE.md`, "Duplicated or overlapping data": intro rewritten. Every item stays described as still in place; the owner has asked for retirement of items 1, 2, 3, 5, 6, gated on production checks recorded in the gate document; `wake_epochs` (item 4) is kept by decision. The seven items themselves are unchanged.
- `deploy/README.md`: new section "Retiring the rollback-era data (owner runbook)" with five ordered steps (deploy the release with the report command, run the report command, run the gate checks, paste results, what happens next). It references the gate document by path and the commands by name; no production path is repeated.

## Paragraphs plan 23 must revisit after plans 19 to 22

1. `ARCHITECTURE.md` "Duplicated or overlapping data", intro paragraph: replace with what was actually retired and what the owner kept.
2. Same section, item 1 (legacy identity mirror, plan 19): rewrite or delete if G1 was approved and executed.
3. Same section, item 2 (per-frame registry and artwork copies, plan 20): same, if G2 approved.
4. Same section, item 5 (`legacy-admin` principal, plan 21): same, if G3/G6 approved (schema 5; the `user_version` 4 mention in the Stores table, the `sessions` notes and the "Schema v3/v4 and rollback" parts of `deploy/README.md` then need a schema 5 counterpart).
5. Same section, items 3 and 6 (`META_LAST_POLL_TRIGGER`, unused location helpers; plan 22): same.
6. Item 4 (`wake_epochs`): stays as kept by decision; adjust wording only if the owner changes it.
7. Stores table rows: `devices.json`/`byos_state.json` ("legacy identity files"), the Fleet registries and `illustration_overrides/` rows ("leftovers"), the `fleet.db` row (`user_version` 4, tables), the `history.db` row (`wake_epochs`, meta keys) and the "Migration markers" row.
8. `ARCHITECTURE.md` "Backup coverage": the per-frame copies and their backup-list entries if plan 20 removes them.
9. `deploy/README.md`: the whole new runbook section (convert to a record of what was done, or delete), the "Fleet database" bullets "Expand only" and "Pending frames are skipped" and the `devices_cli` mirroring sentence, the "Schema v3 and rollback" / "Schema v4 and rollback" sections, and "Rolling back".
10. The Technology Stack and Architecture text of `.claude/CLAUDE.md` if any retirement changes it.

## Checks

- `deploy/tests/test_docs.py`: 23 passed.
- Every backticked repository path in the added text resolves in `git ls-files` (the gate document is on main since PR #659).
- Exposure scan of the added lines (IPv4-like strings, e-mail-like strings, token/secret assignments): no match. No owner name.
- `scripts/check_comment_history.py check`: clean.

## Deviations

None to the plan's scope. Note: a stale script in the scratchpad (same file name as one I meant to create) was run once by mistake and touched `companion/test_companion_app_02.py`; the change was reverted before any commit, nothing of it is in this branch.

## Self-Check: PASSED
