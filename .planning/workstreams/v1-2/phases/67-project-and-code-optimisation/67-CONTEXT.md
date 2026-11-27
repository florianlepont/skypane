# Phase 67: Project and Code Optimisation for a Clean, Industrial Result - Context

**Gathered:** 2026-11-27
**Status:** Ready for planning

<domain>
## Phase Boundary

Make the repository read, build, test and ship like an industrial product: consistent, documented, free of dead code and drift. **No behaviour change.** Requirement QUAL-01. Scope per ROADMAP "Phase 67", including two known items: the flaky browser test `companion/test_browser_ux_03.py::test_a_refresh_keeps_every_picture_action_working`, and the databases and persistent state (history.db, fleet.db, per-device JSON, nightly backup). Phase 59 (comment-history debt) follows.

</domain>

<decisions>
## Implementation Decisions

### Order of work
- **D-01:** Order by value: (1) databases and persistent state, (2) ARCHITECTURE.md, (3) tests and dead code, then the remaining roadmap items (naming/structure, types, scripts, dependencies, README/deploy guide, repository tree, lint/licence headers).
- **D-02:** Phase 66 security results are the baseline: do not reopen audited code or duplicate the access/security review of the databases. Read 66-AUDIT.md, 66-FIX-LEDGER.md, 66-VERIFICATION.md first.

### Structural change (owner chose the more permissive option)
- **D-03:** Module moves are allowed (e.g. grouping `server/` into subpackages), but only as one subpackage per PR, with compatibility import shims where other code, tests, systemd units or deploy scripts still use the old path, and each PR with its own check. No bulk move in one change. (Planner: the deploy path, systemd `ExecStart` lines and `stub-server` imports are the main risk; verify each.)

### Coverage
- **D-04:** Measure before and after; raise the coverage floor to the measured end value (never below the current floor). Other CI gates (lint, mypy, function size, comment history) are not weakened and are raised where safe.

### Fixed by the phase brief (carried as decisions)
- **D-05:** Behaviour preserved: golden hashes, `stub-server/test_phase47_freeze.py` and the full suite pass unchanged; no test is deleted or skipped to make it pass. The flaky test is fixed at its root (test or code), never skipped or quarantined.
- **D-06:** Persistent-state questions to settle and document: data ownership per store; schema versioning/migration (one mechanism or several); duplicated or contradictory data across the two databases and the JSON files; what the backup covers and misses; connection handling and locking between poll loop, companion and device server; leftover tables/columns.
- **D-07:** A before/after record with measured numbers (lines, modules, largest functions, type coverage, test time) is a deliverable. Render baseline regenerated only with `test-support/companion_render_snapshot.py --write` when the render legitimately changes.
- **D-08:** `ARCHITECTURE.md` already exists at the repository root (555 lines, last touched in Phase 68.1) while `.claude/CLAUDE.md` says the architecture is unmapped: verify it claim by claim against the real modules, update it (data flow ADS-B to frame, data stores, deploy path), and make CLAUDE.md's architecture section point to it.
- **D-09:** Every cleanup is a small reviewable change with its own check, never mixed with a feature. Work on a branch, draft PRs; never approve or run the production deploy.
- **D-10:** The repository stays public until Phase 70.1 closes: no secret, token, key or personal data in any file, commit or PR. Planning-note cleanup must not delete owner decisions or history that other documents reference; when unsure, ask the owner.
- **D-11:** Owner wants short answers in French; written artefacts in English. Browser tests may not run here: rely on CI. Docs-only changes skip heavy CI jobs.
- **D-12 (owner decision, 2026-11-27, overrides the provisional defaults):** the owner wants real state changes in this phase, not only documentation: (1) UNIFY the SQLite migration mechanism of history.db and fleet.db (one shared mechanism, keeping the concurrent-open safety of history.db and the refusal of a newer fleet.db); (2) RETIRE the rollback-era duplicates (enrolment secret and token mirrors devices.json and byos_state.json, the per-device copies of the three airline registries and of the artwork, the legacy-admin session principal); (3) REMOVE the leftovers without a writer (META_LAST_POLL_TRIGGER, the write-only wake_epochs table, the three unused fleet_db location helpers). Decisions 3 to 7 of the owner's answers are accepted as in the plans (three module-move groups with shims, function-size gate extension, other defaults kept, 30-run CI repeat for the flaky test, branch deletion only per name in plan 12). Constraints: build on the Phase 66 results (no reopening of the security review); order is unify first, then retire, then remove; every production-data step is additive-then-verify with a backup/restore test, a dry-run, an idempotence test; retiring ends rollback to the previous release, so it is gated on a non-autonomous owner checkpoint (plan 18) that names exactly what is retired and on the owner's pasted read-only check results, never on a guess; no schema change is applied to production by us (deploy is manual by the owner); Phase 47 freeze test and golden hashes pass unchanged. Tests that exercised only the retired code are removed with it and listed by id; D-05's "no test deleted" is relaxed only for those.
- **D-13 (owner answers on D-12, 2026-11-27):**
  - The owner will run the read-only production checks of plan 18 (G1 to G6) and paste the results. Plans 19 to 22 act only on those pasted results.
  - `wake_epochs` is KEPT (G4 = KEEP): the plan 22 table drop does not run. The owner will revisit it only if the link between battery life and wake interval is abandoned.
  - The fleet.db fallback is RETIRED (G1 = approved in principle): the device server reads identity from fleet.db only and refuses to answer if fleet.db is unreadable. Recovery is the nightly backup. The legacy files are quarantined by the owner-run tool, never deleted. Plan 19 still waits for the owner's G1 check result.
  - The end of rollback for fleet.db is ACCEPTED in principle (G3 = approved, confirmed after an explanation of the check): schema 5 drops the `legacy-admin` principal, and the previous release then refuses fleet.db, so recovery is the nightly backup. Plan 21 still waits for the owner's pasted G3 count (`SELECT principal, COUNT(*) FROM sessions GROUP BY principal;`, counts and the words only) and the G6 written confirmation that the rollback period is over. Deploy stays manual.

### Claude's Discretion
- Exact PR split, naming choices, which dead code qualifies, and test-suite speed-ups beyond items 1-6 already done in `70-TEST-SPEED-SUMMARY.md`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope
- `.planning/workstreams/v1-2/ROADMAP.md` — section "Phase 67"
- `.planning/workstreams/v1-2/REQUIREMENTS.md` — QUAL-01
- `.claude/CLAUDE.md` — conventions, CI gates, stack

### Prior phases to build on
- `.planning/workstreams/v1-2/phases/66-security-audit/66-AUDIT.md`, `66-FIX-LEDGER.md`, `66-VERIFICATION.md` — what was fixed, accepted, deferred (incl. backups at rest)
- `.planning/workstreams/v1-2/phases/70-*/70-TEST-SPEED-SUMMARY.md` — items 1-6 done
- Phase 48 plans/summaries (fleet.db schema, migrations, backup and restore test)

### Code and docs in scope
- `server/history_db.py`, `server/fleet_db.py`, `server/fleet_migrate.py`, `server/state_store.py`, `server/atomic_io.py`, `server/device_dirs.py`
- `ARCHITECTURE.md`, `README.md`, `deploy/README.md`, `CONTRIBUTING.md`
- `pyproject.toml` (`[tool.mypy]`), `scripts/` (function-size and comment-history gates, `run-all-tests.sh`)
- `stub-server/test_phase47_freeze.py`, `test-support/companion_render_snapshot.py`
- `companion/test_browser_ux_03.py` (flaky test)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Both databases already use `PRAGMA user_version` migrations, `busy_timeout` and WAL, but through separate code (`history_db.py`, `fleet_db.py`): candidate for one shared mechanism, to be confirmed by the researcher.
- `server/` is ~54.7k lines in one flat package; module groups visible by prefix (`fleet_*`, `giant_*`, `firmware_*`, `history_*`).

### Established Patterns
- Gates in CI: ruff, mypy module list, function size ≤ 80 lines, comment-history guard, coverage floor, behaviour-over-source test rule.

### Integration Points
- systemd units, `deploy/` scripts and `stub-server/byos_server.py` import `server` modules by flat path: constrains D-03.

</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the roadmap section and the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- Comment-history debt: Phase 59 (follows this phase).
- Anything new in behaviour or features: out of scope.

</deferred>
