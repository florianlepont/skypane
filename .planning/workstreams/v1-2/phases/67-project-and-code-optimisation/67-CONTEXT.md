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
