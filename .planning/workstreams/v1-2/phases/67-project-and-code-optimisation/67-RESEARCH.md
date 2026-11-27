# Phase 67: Project and Code Optimisation - Research

**Researched:** 2026-11-27
**Domain:** behaviour-preserving repository cleanup (Python stdlib server, SQLite state, deploy and CI gates, docs)
**Confidence:** HIGH for measurements and code findings (all taken from commands run in this session or from CI run 45993237674); MEDIUM for the flaky-test root cause (read from code, not reproduced: no Chromium here); LOW only where tagged `[ASSUMED]`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Order by value: (1) databases and persistent state, (2) ARCHITECTURE.md, (3) tests and dead code, then the remaining roadmap items (naming/structure, types, scripts, dependencies, README/deploy guide, repository tree, lint/licence headers).
- **D-02:** Phase 66 security results are the baseline: do not reopen audited code or duplicate the access/security review of the databases. Read 66-AUDIT.md, 66-FIX-LEDGER.md, 66-VERIFICATION.md first.
- **D-03:** Module moves are allowed (e.g. grouping `server/` into subpackages), but only as one subpackage per PR, with compatibility import shims where other code, tests, systemd units or deploy scripts still use the old path, and each PR with its own check. No bulk move in one change. (Planner: the deploy path, systemd `ExecStart` lines and `stub-server` imports are the main risk; verify each.)
- **D-04:** Measure before and after; raise the coverage floor to the measured end value (never below the current floor). Other CI gates (lint, mypy, function size, comment history) are not weakened and are raised where safe.
- **D-05:** Behaviour preserved: golden hashes, `stub-server/test_phase47_freeze.py` and the full suite pass unchanged; no test is deleted or skipped to make it pass. The flaky test is fixed at its root (test or code), never skipped or quarantined.
- **D-06:** Persistent-state questions to settle and document: data ownership per store; schema versioning/migration (one mechanism or several); duplicated or contradictory data across the two databases and the JSON files; what the backup covers and misses; connection handling and locking between poll loop, companion and device server; leftover tables/columns.
- **D-07:** A before/after record with measured numbers (lines, modules, largest functions, type coverage, test time) is a deliverable. Render baseline regenerated only with `test-support/companion_render_snapshot.py --write` when the render legitimately changes.
- **D-08:** `ARCHITECTURE.md` already exists at the repository root (555 lines, last touched in Phase 68.1) while `.claude/CLAUDE.md` says the architecture is unmapped: verify it claim by claim against the real modules, update it (data flow ADS-B to frame, data stores, deploy path), and make CLAUDE.md's architecture section point to it.
- **D-09:** Every cleanup is a small reviewable change with its own check, never mixed with a feature. Work on a branch, draft PRs; never approve or run the production deploy.
- **D-10:** The repository stays public until Phase 70.1 closes: no secret, token, key or personal data in any file, commit or PR. Planning-note cleanup must not delete owner decisions or history that other documents reference; when unsure, ask the owner.
- **D-11:** Owner wants short answers in French; written artefacts in English. Browser tests may not run here: rely on CI. Docs-only changes skip heavy CI jobs.

### Claude's Discretion

- Exact PR split, naming choices, which dead code qualifies, and test-suite speed-ups beyond items 1-6 already done in `70-TEST-SPEED-SUMMARY.md`.

### Deferred Ideas (OUT OF SCOPE)

- Comment-history debt: Phase 59 (follows this phase).
- Anything new in behaviour or features: out of scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUAL-01 | The repository, code, tests and documents are cleaned and made consistent, with a measured before and after record, an architecture document, no behaviour change, and no weakened CI gate. | Section "Measured Baseline" (the before record, reproducible commands); "Persistent State Map" (D-06); "ARCHITECTURE.md Drift" (D-08); "Dead Code"; "Module-Move Analysis" (D-03); "Flaky Test Root Cause" (D-05); "Validation Architecture" (how each cleanup is proven behaviour-preserving). |
</phase_requirements>

## Summary

The repository is in better shape than the brief implies: `ruff check` is clean, `mypy` is clean on 51 modules, the function-size gate has no function over 76 lines in `server`/`stub-server`, the main-branch CI run of 2026-11-27 is green with 17,598 tests executed and 0 skipped, coverage 96.15 % against a floor of 93. The mess is concentrated in four places: (1) the persistent-state story is undocumented and partly redundant (two SQLite files with two different migration mechanisms, per-device JSON copies that survive only for rollback, dual-writing of enrolment secrets and tokens to `fleet.db` and the legacy `devices.json`/`byos_state.json`); (2) `ARCHITECTURE.md` is badly stale in exactly the sections the brief names (deployment, data stores, anything after Phase 47: no mention of Auth0, fleet, per-device directories, hardware types, giant layouts, backups, or that deploys are manual `workflow_dispatch`); (3) the tests and CI gates carry slack that hides regressions (the executed-test floor is 12,821 while 17,598 tests run, coverage floor 93 against 96.15 measured, function-size gate does not cover `companion/`, mypy covers 51 of 251 production modules, about 19 % of functions fully annotated); (4) housekeeping (39 remote branches, README/server README drift such as `Pillow==12.3.0` vs the pinned 13.0.0, history-named test files, 9 provably dead functions, a handful of duplicated helpers).

The flaky test has a clear, code-level cause: `panel-lookup.js` opens the Flights picture lightbox only after the trigger's large picture has loaded (`whenPictureReady` waits on an `Image` probe `onload`), while the test samples `dialog.open` immediately after `click()`. For the swapped-in new flight the picture is not yet in the browser cache, so the open is asynchronous. The sibling test `test_browser_ux_01.py` already carries the fix and a comment saying so (`dialog.wait_for(state="visible")` before reading `open`). The fix is test-only and one line.

Module moves are feasible but the blast radius is dominated by tests (hundreds of importers per core module), not by systemd units: the only systemd-visible server path is `server/poll_loop.py`, the only `-m` entry points are `server.fleet_migrate`, `server.firmware_cli`, `server.check_interval` and `server.plane.render`, and every module computes its repo root from `__file__` (17 bootstraps) so a move one level deeper silently breaks `sys.path`. A `sys.modules`-alias shim was verified to keep `monkeypatch`/`mock.patch` working. Recommended: move only the low-fan-in groups, smallest first, and leave `fleet_db`, `history_db`, `device_config`, `poll_loop` in place unless the owner explicitly wants them moved.

**Primary recommendation:** Plan the phase as about 14 to 18 small PRs in D-01 order, starting with a measurement/guard PR (record the baseline, ratchet `MIN_EXECUTED`), then state documentation and leftover removal, then the `ARCHITECTURE.md` rewrite (docs-only, skips heavy CI), then tests/dead code (flaky-test fix first), then types/lint/gates, then at most two or three low-risk module moves, and finish with the coverage-floor ratchet measured on a `main`/dispatch run (pull requests run without coverage).

## Architectural Responsibility Map

Adapted to this project: tiers are the processes that own state, because the cleanup risk is cross-process ownership, not browser/CDN tiers.

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| ADS-B fetch, detection, render, atomic publish of `panel.bin` | Poll process (`server/poll_loop.py` oneshot, every 30 s) | none | Only consumer of the ADS-B request budget; companion has no route that runs a cycle. [VERIFIED: ARCHITECTURE.md and `server/fleet_cycle.py`, read] |
| Device protocol (`/device/v1/setup|display|log`, `/img/...`, OTA offer) | BYOS (`stub-server/byos_server.py`) | Caddy (TLS) | Reads `panel.bin`, `fleet.db` read-only per request; the only writer of enrolment tokens and `battery_state.json`. [VERIFIED: grep byos_server.py] |
| Users, roles, sessions, audit, pairing, device ownership | Companion (`companion/app.py`) writing `fleet.db` | BYOS (token and secret writes) | `fleet.db` is written by companion (users, roles, sessions, audit, co-managers, pairing), by BYOS (tokens, secrets via `fleet_db.set_device_token`) and by the deploy-time `fleet_migrate`. [VERIFIED: grep of `fleet_db.` callers] |
| Flight history, health trend, poll trace | Poll process writes `history.db`; companion reads (and writes `runway_events` side effects via history helpers) | BYOS (battery telemetry through the Caddy log tailer) | One `history.db` per state directory: the root directory is the live frame, `devices/<id>/` holds one per other frame. [VERIFIED: `history_db_path(state_dir)`, backup `DEVICE_SNAPSHOT_DBS`] |
| Per-frame settings and cross-cycle state (`device_config.json`, `poll_state.json`, `battery_state.json`) | Companion writes config; poll writes poll state; BYOS writes battery | none | JSON, atomic write (`server/atomic_io.py`), locks per file. |
| Fleet-wide registries (airline names, default types, manual resolutions, artwork, calendar rules, colour rules) | Companion writes; poll reads | `fleet_migrate` (one-shot merge) | Live at the fleet root (the live frame's directory) since the Phase 5x registry merge. [VERIFIED: `fleet_registries.py` docstring, `device_dirs.fleet_root_for`] |
| Nightly state snapshot | `deploy/backup/skypane_backup.py` (systemd timer 03:15 UTC) | Mac pull over forced-command gate | Allow-list archive, WAL-safe DB copy via the sqlite3 backup API. [VERIFIED: file read] |
| Code shipping | GitHub Actions `deploy.yml` (manual `workflow_dispatch`, `production` environment) running `deploy/deploy.sh` then `deploy/activate.sh` on the VPS | none | ARCHITECTURE.md still says otherwise (see drift). [VERIFIED: deploy.yml header, deploy.sh header] |

## Measured Baseline (the "before" record, D-07)

All numbers taken in this session on commit `a3bb3b8` (main plus the Phase 67 context commits). Reproduction commands are given so the "after" record is measured the same way. `git ls-files` scope, `.planning/` excluded.

| Metric | Before | Command |
|--------|--------|---------|
| Python lines, tracked, outside `.planning` | 277,257 | `git ls-files '*.py' ':!.planning' \| xargs cat \| wc -l` |
| `server/` Python lines | 68,498 (27,646 production in 82 modules; 40,852 tests in 108 files) | `git ls-files 'server/*.py'` split on `test_` |
| `server/` flat top level only | 34 production modules, 13,841 lines (plus 108 test files). CONTEXT's "54.7k lines in one flat package" is the top-level total including tests (54,693) | `awk -F/ 'NF==2'` |
| `server/` subpackages | `plane/` (17 modules + `render/` 12 + `render/giant/` 13 + `calendar_rules/` 4), `net/` (2) | |
| `companion/` Python lines | 166,963 (45,497 production in 165 modules; 121,466 tests in 380 files, 179 `test_browser_*`) | |
| `stub-server/` | 11,146 lines, 4 production modules (`byos_server.py` 1,891) | |
| `test-support/` / `scripts/` / `deploy/` / `hardware/` Python | 7,887 / 6,629 / 6,765 / 6,886 | |
| CSS / JS in `companion/static` | 20,225 / 12,727 lines (34 JS files, 12 CSS) | |
| Largest production Python files | `server/poll_cycle.py` 1,841; `stub-server/byos_server.py` 1,891; `server/fleet_db.py` 1,611; `companion/app.py` 1,446; `companion/pages/airlines_page.py` 1,375; `server/history_db.py` 1,342; `server/plane/illustrations.py` 1,253; `server/firmware_registry.py` 1,245; `companion/ui_base.py` 1,244; `server/plane/enrich.py` 1,162; `companion/pages/history_page.py` 1,121; `server/plane/detect.py` 1,091 | `wc -l` |
| Largest functions (gate scope `server stub-server`, max 80) | 76 `history_db.init_schema`; 70 `render/layout.build_canvas`; 66 `render/text.draw_previous_text_block`; 65 `calendar_rules.fetch_ics`; 65 `byos Handler._handle_display`; none over 80 (1,270 functions scanned) | `scripts/check_function_size.py report server stub-server` |
| Largest functions outside the gate | `scripts/check_comment_history.py::_js_chunks` 89; `adsb-test/analyze_samples.py::render_report` 85; `companion/ui_shell.page_shell` 78; `companion/page_context.build_page_context` 75; `companion/js_minify.strip_comments` 73 | same, other roots |
| mypy | `Success: no issues found in 51 source files` (3.8 s); 51 of 251 production modules (server 82, stub-server 4, companion 165) are on the list; 30 modules under the strict override | `server/.venv/bin/mypy` |
| Function annotation coverage (own AST count: all params and return annotated) | server 589 of 1,141 (51.6 %); companion 18 of 1,856 (1.0 %); stub-server 0 of 129; overall 607 of 3,126 (19.4 %) | script in session scratch; reproduce with `ast` walk |
| ruff | `All checks passed` (rules E4, E7, E9, F; E402 ignored) | `ruff check .` |
| Tests collected | 17,598 (CI run 45993237674 executed 17,598, 0 failures, 0 skipped) | `pytest --collect-only -q` |
| Coverage (CI combined, main run 45993237674) | 30,488 statements, 1,174 missed, 96 % (96.15 %); gate `fail_under = 93` | `coverage-report.txt` in the job |
| Test wall time (same CI run, hosted runners) | whole workflow 10.4 min; non-browser shards 3:08 each; browser shards 5:08 to 8:57 (shard 5 slowest) | `gh run view 45993237674` |
| Slowest tests (CI, non-browser shard 1) | `hardware/test_wakemodel.py::test_rates_filter_selects_one_device` 24.5 s and `..._mixed_export_is_not_the_owner_export` 19.3 s; five `server/test_check_interval_redraw.py::test_off_states_match_a_run_without_the_experiment[*]` 7.9 to 9.6 s each | log of the same run |
| Local freeze and golden check | `stub-server/test_phase47_freeze.py`, `server/test_golden_render.py`, `server/test_golden_giant_render.py`: 115 passed in 7.5 s (`-n 4 --no-cov`, Python 3.13) | usable as the per-PR fast check |
| Stale-branch count | 39 non-main remote branches, none with 0 commits ahead (squash merges hide whether their content landed) | `gh api repos/<owner>/<repo>/branches`, compare API |
| Tracked files / `.planning` | 3,121 tracked files, 1,692 under `.planning`; `.git` 127 MB | |
| Gates today | executed-test floor `MIN_EXECUTED = 12821`, `MAX_SKIPPED = 0` (`scripts/ci_gates.py`); coverage floor 93; function-size 80 over `server stub-server`; comment-history guard; ruff; mypy list | |

**Environment note:** tests ran on Python 3.13 here; production and CI use 3.14. Browser tests cannot run in this environment (no Chromium); rely on CI. [VERIFIED: `server/.venv/bin/python3 --version`, no `~/.cache/ms-playwright`]

**Important CI fact:** since the 2026-11-26 owner decision, pull requests run with `SKYPANE_COVERAGE=off`; the coverage floor is applied only on pushes to `main` and manual dispatch (`70-MEASUREMENTS.md`, "Coverage only on main"). A coverage-floor raise cannot be validated on a PR. [VERIFIED: `70-MEASUREMENTS.md`, `scripts/run-all-tests.sh`]

## Standard Stack

No new runtime dependencies. Tools already in the repo are the standard; one optional one-off tool.

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest + pytest-xdist + pytest-cov | 9.2.0 / 3.8.0 / 7.1.0 | Test, parallelise, coverage | Already pinned in `server/requirements-dev.in` [VERIFIED: file] |
| ruff | 0.17.6 | Lint gate | Already the gate [VERIFIED] |
| mypy | 2.4.1 | Type gate (module list in `pyproject.toml`) | Already the gate [VERIFIED] |
| `scripts/check_function_size.py`, `scripts/check_comment_history.py`, `scripts/ci_gates.py` | in repo | Size, comment, test-count gates | Existing gates to ratchet, not replace |
| `test-support/companion_render_snapshot.py` | in repo | Render baseline (`--write` only when the render legitimately changes) | D-07 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| vulture | 2.16 | Dead-code candidate finder | One-off analysis only; do not add to the hash-locked requirements (see audit). I installed it into the untracked `server/.venv` for this research. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One shared migration mechanism for both DBs | Keep two, document why | The two mechanisms encode different concurrency contracts (see state map); forcing one is a behaviour risk with no user benefit. Recommend documenting and pinning with tests. |
| `ruff format` repo-wide | Do nothing | `ruff format --check --isolated` would reformat 897 of 2,375 files (`I001` isort would touch 477): a diff that buries every review. Do not adopt in this phase. |
| Mass SPDX header on every `.py` | Gate only | 879 of 900 tracked Python files carry no header; firmware C/H are 100 % SPDX (91 of 91). Adding headers is a one-line-per-file change but touches every file; owner decision (Open Question 4). |

**Installation:** none for the phase. Analysis tool, run from a scratch venv or the existing one: `server/.venv/bin/pip install vulture` (not committed).

**Version verification:** `vulture --version` reported 2.16 after install into `server/.venv`; `pip index versions` was not run (see audit).

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| vulture | PyPI | well-established (long-lived dead-code tool) [ASSUMED] | [ASSUMED] high | github.com/jendrikseipp/vulture [ASSUMED] | not run: the environment denied installing `slopcheck` | `[ASSUMED]`: one-off use only, never added to `requirements-dev.in`. If the planner wants it in CI, gate it behind `checkpoint:human-verify` first. |

**Packages removed due to slopcheck [SLOP] verdict:** none (check not run).
**Packages flagged as suspicious [SUS]:** none known. All other tools in this phase are already pinned and hash-locked in the repo.

*slopcheck was unavailable (install denied by the sandbox), so vulture is tagged `[ASSUMED]`.*

## Architecture Patterns

### System Architecture Diagram (data and state, as actually shipped)

```
 ADS-B (adsb.fi, adsb.lol; airplanes.live opt-in) ---> server/zone_fetch.py  (budget: state/request_ledger.json + flock)
 adsbdb.com / VRS route lookups ---------------------> server/plane/enrich.py (state/adsbdb_shared_cache.json)
                                                              |
 systemd timer 30 s --> server/poll_loop.py --> server/fleet_cycle.run_fleet()
      reads: fleet.db (devices, hardware profile, location), device_config.json per device
      per zone/device -> server/poll_cycle.run_once()  (flock state/poll.lock per device dir)
           writes: <dev>/panel.bin (atomic, only if changed), <dev>/poll_state.json,
                   <dev>/history.db (runway_events, poll_cycles, route_lookups, meta, device_health tail of Caddy log)
                                                              |
 Device (ESP32-S3) --HTTPS--> Caddy --> stub-server/byos_server.py (loopback)
      reads: <dev>/panel.bin, fleet.db (read-only, per request), firmware/registry.json
      writes: fleet.db (token, secret mirror), devices.json + byos_state.json (legacy mirror),
              <dev>/battery_state.json, firmware/device_report.json, fleet_status.json
                                                              |
 Browser --HTTPS--> Caddy (config- host) --> companion/app.py (Auth0 sign-in, sessions in fleet.db)
      reads: history.db, panel previews, poll_state.json; writes: fleet.db (users, roles, audit,
             co-managers, pairing), device_config.json, registries, artwork, gallery, calendar rules
                                                              |
 03:15 UTC timer --> deploy/backup/skypane_backup.py --> /var/lib/skypane-backup/archives/*.tar.gz (+ .sha256)
      --> Mac pull over a forced-command key (deploy/backup/backup_gate.py), disk-encryption check (66 fix)
 Deploy: workflow_dispatch (manual, environment "production") --> deploy/deploy.sh (git archive over ssh)
      --> deploy/activate.sh on the VPS (stage in /opt/skypane/releases/<sha>, atomic swap of `current`, restart, rollback)
```

### Recommended PR sequence (D-01 order, D-09 sizing)

Each row is one PR (or at most two) with its own check. "Docs-only" PRs skip heavy CI (D-11).

| # | Workstream | Change | Own check |
|---|-----------|--------|-----------|
| 0 | Baseline and guard | Add `67-BASELINE.md` (the table above, reproducible commands); raise `MIN_EXECUTED` in `scripts/ci_gates.py` to the measured 17,598 (floor may only go up, protects D-05 for the whole phase) | `test-support/test_ci_gates.py`, full CI |
| 1 | State (docs) | Write the Persistent State Map into `ARCHITECTURE.md` (new section) and `deploy/README.md` cross-reference; pure documentation | docs-only; a deploy/tests docs test if one pins headings (`deploy/tests/test_docs.py`) |
| 2 | State (guard test) | Add a behaviour test that seeds state through the production writers (or a fixture list of every `*_FILENAME` constant) and asserts `skypane_backup` prints no "not in include list" drift line and covers each persistent file | `deploy/tests/test_backup.py` family |
| 3 | State (leftovers) | Remove only provably unreferenced constants/keys (see "Leftovers"); document the rest. No schema change | full suite, freeze test |
| 4 | ARCHITECTURE.md | Claim-by-claim rewrite (drift list below), point CLAUDE.md at it via `.planning/codebase/ARCHITECTURE.md` | docs-only; `scripts/check_comment_history.py` unaffected |
| 5 | Tests | Fix the flaky test (one line); rename/merge history-named test files only if collected ids are provably identical (`pytest --collect-only -q` before and after, `comm`) | collected-id diff, the test itself 20 times in CI |
| 6 | Dead code | Delete the 9 zero-reference functions (list below) | `ruff`, `vulture` before/after, full suite |
| 7 | Duplicated helpers | Collapse identical helpers (list below), one theme per PR | full suite, freeze, golden |
| 8 | Types | Add the 3 modules that already pass mypy; annotate next wave; add them to `pyproject.toml` | `mypy` |
| 9 | Gates | Extend function-size gate to `companion deploy`; split `_js_chunks` then add `scripts`; consider `B` ruff subset | the gates themselves |
| 10 | Hygiene | `server/README.md` drift, README, `CONTRIBUTING.md`, `deploy/README.md` provider note; stale-branch list for the owner | docs-only |
| 11 to 13 | Structure | At most two or three low-fan-in `server/` subpackage moves with shims (see analysis) | per-move import smoke test plus full suite |
| 14 | Ratchet and record | Raise `fail_under` to the measured value on a main/dispatch run; write `67-AFTER.md` | CI run on main with coverage |

### Pattern 1: Persistent State Map (D-06)

State directory layout. The state root (`/opt/skypane/state`; `server/state/` locally) is simultaneously the **fleet root** (fleet-wide files) and the **live frame's directory** (`state_path = "."`); every other frame has `devices/<d_xxxxxxxx>/`. [VERIFIED: `server/device_dirs.py`]

| Store | Where | Writers | Readers | Backed up | Notes |
|-------|-------|---------|---------|-----------|-------|
| `fleet.db` (SQLite, WAL, mode 0600, `user_version` 4) | root | companion (users, roles, sessions, audit, co-managers, pairing, frames), BYOS (token, secret mirror), `fleet_migrate` (deploy step) | companion, BYOS (read-only per request), poll (`fleet_cycle`) | yes, sqlite backup API + `integrity_check` | tables: users, locations, devices, meta, sessions, pending_devices, audit_log, device_co_managers |
| `history.db` (SQLite, WAL, `user_version` 1) | root (live frame) and `devices/<id>/` | poll (events, cycles, route lookups, meta), BYOS-side battery via Caddy log tail (poll process), companion (reads; some helpers write) | companion (Health, History, Home, export), poll | yes, root and per device | tables: runway_events, device_health, meta, wake_epochs, poll_cycles, route_lookups |
| `poll_state.json`, `battery_state.json`, `device_config.json` | root and `devices/<id>/` | poll / BYOS / companion respectively | all | yes (root and per device) | atomic write; `device_config.lock` taken alone |
| Fleet registries: `manual_resolutions.json`, `airline_name_overrides.json`, `airline_default_types.json`, `airline_suggestions.json`, `colour_rules.json`, `calendar_rules.json`(+`calendar_url.secret`) | fleet root (calendar and colour rules also per device) | companion | poll, companion | yes | per-device copies of the first three are leftovers after the merge, kept for rollback |
| Migration markers and archives (`airline_registry_migration.json`, `illustration_migration.json`, `airline_default_types_*`) | root | `fleet_migrate` and `server/plane/fleet_*` | same | yes | idempotency markers; must be restored with the data they guard |
| `devices.json`, `byos_state.json` | root | `devices_cli`, BYOS (mirror) | BYOS fallback when `fleet.db` absent or unmigrated; `fleet_migrate` | yes | legacy identity files: same secrets and tokens as `fleet.db.devices` |
| `live_frame_macs.json` | root | `device_dirs` | BYOS | yes | survives an unreadable `fleet.db` |
| `firmware/registry.json`, `firmware/device_report.json`, `firmware/registry.lock` and images | `firmware/` | `firmware_cli`, BYOS (device report) | BYOS, companion Update page | yes (directory; locks excluded) | |
| `illustration_overrides/`, `illustration_conflicts/`, `gallery/` | root (overrides also per device) | companion, poll (`gallery`) | poll, companion | yes | |
| `request_ledger.json`, `*.lock`, `poll.lock`, `adsbdb_shared_cache.json`, `panel.bin`, `fleet_status.json`, `check_interval_experiment.json`, `pairing/`, `img/`, `theme_previews/`, `frame_previews/`, `caddy-access.log*` | root / device | various | various | deliberately not (KNOWN_EXCLUDED) | regenerable or short-lived |

Findings by question:

- **Ownership written down?** No. `ARCHITECTURE.md` says "there is no separate database" and names only `panel.bin`, `poll_state.json`, `history.db` and `battery_state.json`. `fleet.db`, per-device directories, `devices.json` and the registries are absent. This is the main D-06 deliverable. [VERIFIED: grep of ARCHITECTURE.md]
- **Migration mechanisms: two, deliberately different.**
  - `fleet_db`: ordered tuple `MIGRATIONS = (_migrate_v1 .. _migrate_v4)`, each applied in one transaction with the `PRAGMA user_version` bump, a newer database is refused and never written (`FleetDbTooNew`), foreign keys per connection, `isolation_level=None`, 0600 file mode, run only as an explicit deploy step (`fleet_migrate`) plus on connect. [VERIFIED: `server/fleet_db.py` 117-330]
  - `history_db`: idempotent `CREATE TABLE IF NOT EXISTS` plus guarded `ALTER TABLE ADD COLUMN` (tolerating "duplicate column name" races) run once per process per file identity, then `user_version` is raised never lowered; a newer file is not refused. Reason: companion and poll oneshot may both open a fresh file concurrently. [VERIFIED: `server/history_db.py` 20-24, 146-306]
  - Recommendation: **do not unify.** Document the two contracts and why, and add a pinning test only if none exists. The only shared logic worth extracting (optional, last): busy-timeout constant (both 5000 ms), WAL pragma, `user_version` read. Low value; risk of touching the two hottest modules. `[ASSUMED]` that the owner prefers no refactor here (Open Question 1).
- **Duplicated or contradictory data.**
  1. Enrolment secret hash and device token live in `fleet.db.devices` (and `pending_devices`) **and** in `devices.json` / `byos_state.json`. With a migrated `fleet.db` BYOS reads `fleet.db` (`effective_registry`, `effective_tokens`); `issue_token` writes both and leaves the legacy file untouched when the `fleet.db` write fails; `mirror_to_fleet` pushes `devices_cli` changes one way; `fleet_migrate` reconcile is legacy-wins on secret and token. This is the rollback safety net ("the previous release keeps working"), so it is not removable in a behaviour-preserving phase. Document as intentional, retire only on an owner decision about the end of the rollback period.
  2. Per-device `manual_resolutions.json`, `airline_name_overrides.json`, `airline_default_types.json` and `devices/<id>/illustration_overrides/` are read-only leftovers after `fleet_registries` / `fleet_artwork` merged them into the fleet root; nothing in the runtime reads them (path helpers use `device_dirs.fleet_root_for`). They are still in `DEVICE_INCLUDE_FILES`. Same rollback reasoning.
  3. `META_PROVIDER_LAST_CALL_PREFIX` documents a per-provider last-call bookkeeping in `history.db.meta` as a cross-process mechanism, but the live mechanism is `request_ledger.json` (`request_budget.py`). The constant is never written in production code. Same for `META_LAST_POLL_TRIGGER`. [VERIFIED: grep, only the status-key filter in `history_db.py` references them]
  4. `wake_epochs`: written by `poll_cycle`, read only by `history_db` itself for de-duplication; a test pins "no companion file mentions it; it accrues data for a future phase". Write-only table by design. Leave; ask owner (Open Question 3).
  5. `fleet_db.sessions.principal` still allows `'legacy-admin'` (`PRINCIPAL_LEGACY_ADMIN` unused in production; the shared-password sign-in was removed 2026-10-30). Removing it needs schema v5 and breaks the "previous release runs on the migrated state" rule. Leave and document.
  6. `fleet_db` location helpers `delete_location_if_unused`, `count_locations_owned`, `location_usage_counts` have no production caller since the Locations routes were removed; tests still call them (see Dead Code).
  7. Same-named constants in several modules: `PANEL_FILENAME`, `CONFIG_FILENAME` (`device_dirs`) vs `DEVICE_CONFIG_FILENAME` (`device_config`); `BATTERY_STATE_FILENAME` (`state_store`) vs `_BATTERY_STATE_FILENAME` (`fleet_cycle`); `REGISTRY_FILE = "devices.json"` (`byos_server`) vs `LEGACY_REGISTRY_FILE` (`fleet_migrate`); `_MAC_RE` defined five times (four identical, one case-insensitive in BYOS). The backup script deliberately duplicates the device-id regex (standalone). Consolidate only the pure duplicates; the BYOS variant differs (accepts uppercase).
- **Backup coverage (66 already audited access and at-rest handling; do not redo, D-02).** Covered: both DBs (online copy, integrity check, per device `history.db`), every JSON in `INCLUDE_FILES`/`DEVICE_INCLUDE_FILES`, `firmware/`, `gallery/`, artwork directories, markers. Not covered by design: `skypane.env`, signing key, user photos (none exist yet), Caddy config and certificates. Gaps worth stating in docs, not changing: `caddy-access.log*` is excluded while `history.db.meta.caddy_log_offset` is archived (after a restore the offset may exceed a fresh log; behaviour on that case should be confirmed by test, `[ASSUMED]` benign); `check_interval_experiment.json` excluded (expires in 72 h); the allow-list is protected by a drift line to stdout, not by a test tying every writer to the list (hence PR 2). No restore test for a schema-4 backup into a scratch directory is recorded as done in `60-HANDOFF` ("optional"); `deploy/tests/test_backup.py` has restore round-trip tests for `fleet.db` including pending audit and co-manager data (lines 406 to 435, 674). [VERIFIED]
- **Connection handling and locking.** `fleet_db.connect` opens per call with `busy_timeout=5000`, WAL, FK on, `BEGIN IMMEDIATE` helper `transaction()`; BYOS uses `connect_readonly` per request. `history_db.connection_scope` shares one connection per thread inside a scope, opens per call outside it; read paths use `mode=ro` + `query_only`. File locks (`fcntl.flock` via `atomic_io.exclusive_lock`): `poll.lock` (per device dir), `calendar_rules.lock`, `device_config.lock` (never taken while another is held), `request_ledger.lock`, `registry.lock` (firmware). Documented lock order: threading lock, then `poll.lock`, then `calendar_rules.lock`. No deadlock found by reading; no change recommended. [VERIFIED: grep and `atomic_io.py` docstring]

### Pattern 2: ARCHITECTURE.md Drift (D-08), claim by claim

Method: backticked file names checked against `git ls-files` (64 references, all resolve except runtime artefacts and the git-ignored `secrets.h`); section prose compared with code. Confirmed drift:

| Section | Claim | Reality | Action |
|---------|-------|---------|--------|
| Data-flow diagram | `writes state/panel.bin`, `state/poll_state.json` | Per device: `<state>/devices/<id>/...`; root only for the live frame | Rewrite diagram with fleet cycle, zones, per-device dirs |
| Data-flow diagram, Render | "two-flight poster" (also lines 97, 144) | Giant-lettering layouts and landscape cards (Phases 62, 56); `server/plane/render/giant/` | Update description; verify the render-pipeline subsection (lines ~260-470) against `render/` modules |
| Server render pipeline | module map lists `render/` split as `style/text/glyphs/hold_screens/layout/cli` | Also `giant/`, `landscape*`, `hold_screens`; plus `fleet_*`, `device_dirs`, `hardware`, `firmware_*`, `pairings*`, `history_db`, `wake*`, `request_budget`, `zone_fetch`, `http_fetch` | Regenerate the module map from the real tree |
| Deployment, companion bullet | companion writes `history.db` and `device_config.json`; "never touches `byos_server.py`" | Companion owns `fleet.db` writes, sessions, Auth0, pairing, registries, artwork | Rewrite |
| Deployment, "State" bullet | "there is no separate database" | Two SQLite databases plus ~20 JSON files | Replace with the state map |
| Deployment, "Shipping code" | `deploy.sh` rsyncs `server/`, `stub-server/`, restarts "the two service units", "no separate rollback mechanism exists" | `git archive` over ssh into `/opt/skypane/releases/<sha>`, `activate.sh` swaps `current` atomically, restarts, rolls back on failure; six units; deploy is manual `workflow_dispatch` in the `production` environment, a merge to `main` never deploys | Rewrite the deploy path |
| Deployment, device authentication | registry is `devices.json` | `fleet.db` is the source of truth after migration; `devices.json` is a legacy mirror | Rewrite |
| Missing entirely | Auth0 sign-in, roles, default-deny, co-management, hardware profiles and second hardware, OTA registry and signing, pairing flow, backup, per-device wake interval, request budget (budget is mentioned, correct) | Shipped in Phases 48-65 | Add sections |
| Deliberate constraints | "Single view in v1", "No freshness or stale-data indicator" | Companion has `freshness.js`, `companion/freshness.py`; the RER view remains deferred | Re-check each against v1.2 scope; correct or date-stamp |
| Header | refers to `.planning/research/ARCHITECTURE.md` as history | still true | keep |
| Firmware section (lines 65-146) | wake flow, Log Line Contract, 31.5 s refresh | Not re-verified against `firmware/main` in this research (firmware out of scope for server changes) | Planner: one task to verify firmware claims against `firmware/main/state_machine.c`, `app_main.c` and `firmware/VENDOR.md` |

Facts verified correct and worth keeping: `server/poll_loop.py` invoked by a 30 s timer and handing the fleet to `fleet_cycle.run_fleet()`; `request_ledger.json` and `flock`; `poll.lock`; BYOS routes `/device/v1/setup`, `/device/v1/log`, `/device/v1/display`, `/img/...` (all present in `byos_server.py`); loopback-only BYOS and Caddy; detection corroboration semantics (not re-read line by line here).

CLAUDE.md pointer: the managed block `GSD:architecture-start source:ARCHITECTURE.md` is regenerated by `profile-output.cjs` from `.planning/codebase/ARCHITECTURE.md` (absent), and falls back to "Architecture not yet mapped". A hand edit of the block would be overwritten the next time the generator runs. Create `.planning/codebase/ARCHITECTURE.md` as a short bullet summary that links to the root `ARCHITECTURE.md` (the generator keeps bullet and table lines), then regenerate or edit the block to match. [VERIFIED: `~/.claude/get-shit-done/bin/lib/profile-output.cjs` lines 362-376]

### Pattern 3: Dead code and duplicates

Method: `vulture --min-confidence 60` over production dirs (tests excluded), each candidate re-checked by word-boundary grep over all tracked `.py/.sh/.service/.js/.html/.yml/.md` outside `.planning`. `PILImageModule` imports in `panel_format.py` and `visible_window.py` are `TYPE_CHECKING` string-annotation uses (vulture false positives; ruff is clean).

**Safe to delete: zero references anywhere (code, tests, docs, units):**

| Function | File |
|----------|------|
| `_cards_block` | `companion/console_fleet_view.py:160` |
| `location_scope` | `companion/detection_actions.py:109` |
| `summary_values` | `companion/detection_summary.py:76` |
| `viewer_may_rename_current` | `companion/device_scope.py:386` |
| `is_long_overdue` | `companion/frame_state.py:104` |
| `battery_both_sentences` | `companion/health_signals.py:475` |
| `cached_normalized_png_bytes` | `companion/illustration_normalize.py:94` |
| `_gap_trigger_attrs_html` | `companion/pages/airlines_page.py:722` |
| `trigger_attrs_html` | `companion/resolve_dialog.py:65` |

Also unused local variables vulture rates 100 %: `companion/app.py:1384` and `stub-server/byos_server.py:1825` (`fmt_args` of `log_message` overrides: signature, keep), `companion/pages/airlines_page.py:631` `type_title` (check and drop).

**Production-unused but referenced by tests (do not delete without an owner decision, D-05 and `MIN_EXECUTED`):** `server/fleet_db.py`: `connect_memory`, `delete_location_if_unused`, `count_locations_owned`, `location_usage_counts`, `assign_owner`, `dump_logical`, `clear_pending_code`; `server/fleet_sessions.py`: `create_session`; `server/hardware.py`: `registry_problems`, `provenance_for`; `server/image_container.py`: `decode_container`; `server/device_dirs.py`: `wipe_device_dir`; `server/request_budget.py`: `paused_until`; `companion/draw.py`: `percent_y`, `label_span`, `day_band`, `regularity_grid`; `server/plane/render/giant/*`: `fuselage_median`, `whole_aircraft`, `line_mask`, `assert_giant_palette`; `scripts/fw_release_manifest.py::size_bound`; and others in `cand_refs` (about 30 total). Some are test-support seams (e.g. `connect_memory`, `decode_container`, `dump_logical`). Recommendation: record them in the after-document as "test-only API", delete none.

**Constants vulture flags (60 %), about 50, mostly `companion` i18n label constants and `render/style.py` text constants:** may be consumed by an i18n catalogue scan (`test-support/i18n_ids.py`) or by reflection; do not delete without checking that scan. Definitely-leftover candidates: `META_PROVIDER_LAST_CALL_PREFIX`, `META_LAST_POLL_TRIGGER` (only referenced by the status-key filter), `server/poll_cycle.py:62 POLL_INTERVAL_S`, `server/device_policy.py:136-137 BATTERY_FULL_MV / BATTERY_EMPTY_MV`, `PRINCIPAL_LEGACY_ADMIN` (referenced by `test-support/access_matrix_support.py`, keep).

**Identical helpers (AST-identical bodies in different files):** `_read_umask` (`atomic_io.py` and `byos_server.py`); `escape` (`companion/draw.py`) vs `escape_html` (`companion/ui_base.py`); `_safe_query` (`health_signals.py`, `pages/history_page.py`); `_read_marker` and `_merged_hashes` (`fleet_artwork.py`, `fleet_registries.py`); `_read_json` (`fleet_default_types.py`, `fleet_set_defaults.py`); `_lettering_box` / `lettering_box` (`giant/compose.py`, `giant/compose_c.py`); `_routes`, `_ui` (three companion pages); `owner_choice` (`console_lifecycle.py`, `console_pairing.py`); `utc_now_iso` variants in `fleet_db`, `history_db`, `firmware_registry`, `byos_server`. Consolidate in small PRs; keep `byos_server._read_umask` unless BYOS is allowed to import `atomic_io` privately (it imports `server` already).

### Pattern 4: Module-move analysis (D-03)

Facts:
- Only the **flat** top level is a candidate: 34 production modules, 13.8k lines. The `plane/`, `net/` subpackages already exist; `server/` has no `__init__.py` (namespace package, by design for the test and direct-script modes) and tests are flat in the same directory.
- systemd-visible path: only `/opt/skypane/current/server/poll_loop.py` (poll unit). BYOS, companion and backup units point at `stub-server/`, `companion/`, `deploy/backup/`. [VERIFIED: unit files]
- `-m` entry points that must keep working (docs and scripts name them): `server.fleet_migrate` (deploy README x3, `deploy/tests`, hardware runbook), `server.firmware_cli` (`scripts/fw_publish_signed.py`, deploy README, runbooks), `server.check_interval` (README), `server.plane.render` (README, docs).
- 17 files compute the repo root from their own location (`_REPO_ROOT = dirname(dirname(abspath(__file__)))`); moving one level deeper requires a third `dirname`, else `import server...` fails when run as a script. Affected: `device_config, device_dirs, firmware_image, fleet_db, fleet_migrate, fleet_ops, fleet_sessions, history_db, pairings, poll_loop, themes, plane/detect, plane/enrich, plane/illustrations` (the rest are test files).
- Importers per top-level module (AST count, production/test): `device_config` 40/126, `fleet_db` 25/124, `history_db` 30/102, `hardware` 23/79, `panel_format` 26/29, `state_store` 18/34, `device_dirs` 17/30, `atomic_io` 22/19, `poll_cycle` 6/30, `firmware_registry` 7/20, `airports` 6/18, `detection` 10/11, `fleet_sessions` 4/16, `fleet_ops` 6/12, `pairings` 7/9, `zone_fetch` 4/8, `request_budget` 3/7, `http_fetch` 4/6, `fleet_zones` 4/6, `fleet_cycle` 3/5, `firmware_image` 3/5, `wake` 2/5, `image_container` 1/6, `check_interval` 3/3, `wake_stats` 3/2, `pairing_image` 1/4, `visible_window` 2/2, `fleet_migrate` 0/12, `firmware_cli` 0/2.
- 77 `monkeypatch.setattr(<server module>, ...)` call sites on `history_db, fleet_db, poll_cycle, state_store, firmware_registry, device_config, request_budget`: a shim that re-exports with `from x import *` would break them silently (the patch lands on the shim, the code reads the new module). A `sys.modules` alias shim keeps patching working: **verified experimentally on CPython 3.13** (`import old is new`, `old.X = 5` visible on the new module, `mock.patch('pkg.old.X')` effective). Re-verify on 3.14 in CI. [VERIFIED: scratch experiment]
- Shim shape for library modules:

```python
# server/fleet_zones.py  (compatibility shim, delete after callers are migrated)
import sys
from server.polling import fleet_zones as _moved
sys.modules[__name__] = _moved
```

- Shim shape for CLI modules (`-m` must still run `main()`): a `sys.modules` alias is not enough because `__main__` of the shim never reaches the moved module's `if __name__ == "__main__"`. Either keep a thin file `from server.x import main` with its own `if __name__ == "__main__": sys.exit(main())`, or update the documented call sites in the same PR and leave the shim for one release.

Recommended order (smallest blast radius first; each is one PR with shim):
1. `firmware_*` (`firmware_cli`, `firmware_image`, `firmware_registry`) into `server/firmware/` (about 15 production and 27 test importers; CLI shim needed).
2. Polling support: `request_budget`, `zone_fetch`, `http_fetch`, `fleet_zones`, `fleet_cycle` into `server/polling/` (all low fan-in, production importers inside `server/` and `scripts/` only). Keep `poll_loop.py` (systemd path) and `poll_cycle.py` (31 test importers) where they are, or move `poll_cycle` last with a shim.
3. Pairing: `pairings`, `pairing_code`, `pairing_image` into `server/pairing/`.
Leave in place unless the owner insists: `fleet_db`, `history_db`, `device_config`, `hardware`, `panel_format`, `state_store`, `atomic_io`, `device_dirs` (each 17 to 40 production importers across companion, scripts, stub-server and 30 to 126 tests). Moving them has the largest blast radius for a purely cosmetic gain; their prefix groups (`fleet_`, `history_`) already read as groups. `[ASSUMED]` that this partial restructuring satisfies the owner's "more permissive option" (Open Question 2).

Per-move check: (a) AST scan that no `server.<old>` import remains outside the shim except tests the PR deliberately leaves; (b) `python3 -c "import server.<old>"` and `python3 server/poll_loop.py --help` from a different cwd (existing `server/test_import_boundaries.py` pattern); (c) `-m` smoke for the CLI modules; (d) mypy module-list and override-list paths updated (`pyproject.toml` lists dotted names and file paths, ruff E402 comment lists paths); (e) coverage `source` paths unaffected (it names `server` as a whole); (f) `deploy/tests/test_units.py` and the backup tests unchanged; (g) full suite plus freeze and golden.

### Pattern 5: Flaky Test Root Cause (D-05)

`companion/test_browser_ux_03.py::test_a_refresh_keeps_every_picture_action_working` (lines 314-375). Failure message from PR #454: "expected a swapped-in picture link to open the lightbox", i.e. the last assertion, `page.locator("#panel-lookup-dialog").evaluate("el => el.open")` evaluated immediately after `.first.click()`.

Mechanism (read from `companion/static/panel-lookup.js` lines 655-770):
- The click handler is delegated on `document`. For the Flights picture dialog (`pictureDialog` true) with the dialog closed it does **not** open synchronously: it calls `whenPictureReady(trigger, open)`, which creates `new window.Image()`, sets `probe.src`, and opens only when `probe.complete && probe.naturalWidth > 0` (synchronously, if the picture is already cached) or on `probe.onload`/`onerror` (asynchronously).
- The row clicked is the **new** flight at the top, just swapped in by the refresh with a freshly archived render (`poll_cycle._save_to_gallery`): its large picture URL has never been requested, so the probe is not complete and the dialog opens on a later task. Playwright's `click()` returns after the click event dispatches, so `el.open` can still be false. When the image is served fast or already cached by the thumbnail load, the test passes; under CI load (shard 4) it fails; a re-run passes.
- The dialog opens afterwards via `openWithTransition` or `openFromTrigger`; both call `dialog.showModal()` (inside the same asynchronous callback).
- The sibling test already knows this: `companion/test_browser_ux_01.py` lines 106-109 carry the comment "The lightbox opens once its picture has loaded, so wait for it rather than sampling at once" and use `dialog.wait_for(state="visible")` before reading `open`; line 162-164 does the same.

This is a **test race, not a code defect**: the product behaviour (open after the picture is ready, so the dialog is never an empty box) is intentional. Fix (one test, no product change, no skip):

```python
# companion/test_browser_ux_03.py, end of the test; mirrors test_browser_ux_01.py lines 106-109
page.locator("tr[data-flight-row] a[data-view-panel-src]").first.click()
dialog = page.locator("#panel-lookup-dialog")
# The lightbox opens once its picture has loaded, so wait for it rather than sampling at once.
dialog.wait_for(state="visible")
if not dialog.evaluate("el => el.open"):
    raise AssertionError("expected a swapped-in picture link to open the lightbox")
```

Scan for siblings: the only other picture-link click followed by an immediate `open` read in `test_browser*.py` is already guarded (`test_browser_ux_01.py`). The `fleet_dialogs` and `firmware_panel` direct `open` reads are for dialogs/details that open synchronously (not the picture lightbox). Confidence MEDIUM: not reproduced here (no browser). To prove the cause in CI without waiting for a rare failure, a temporary (uncommitted) variant can delay the picture response with `page.route(...)` for the gallery image URL and show the old assertion failing and the new one passing; or run the fixed test with `--count`/a loop 30 times in a CI job on the PR.

### Pattern 6: Types, lint, gates (raise where safe, D-04)

- **Zero-cost mypy additions** (pass today under the global settings): `server/fleet_cycle.py` (26 of 29 functions annotated), `server/plane/fleet_default_types.py` (6 of 6), `server/plane/render/landscape_common.py` (5 of 5). Verified: `mypy` reports "no issues" on them. Next wave by value (all 0 % annotated today): `history_db` (52 funcs), `firmware_registry` (56), `enrich` (38), `device_config` (25), `detect` (25), `http_fetch` (17), `stub-server/byos_server.py` (85), `fleet_cli` (32). Note the existing `files` list vs strict `overrides` list differ by 21 modules (listed but not strict: `pairing_image`, `pairings`, `fleet_artwork`, `fleet_registries`, `fleet_set_defaults`, all `giant/*`, `poll_cycle`, `screen_layouts`, `visible_window`); some are intentional (`poll_cycle`), others can be promoted if they already satisfy `disallow_untyped_defs`.
- **Function-size gate scope** is `server stub-server`. Measured maxima elsewhere: `companion` 78, `deploy` below 65, `test-support` 62 (tests excluded by the gate), `scripts` 89, `adsb-test` 85. So `companion` and `deploy` can be added to the gate at zero cost; `scripts` after splitting `_js_chunks`. Changing `.github/workflows/ci.yml` line 158 is a CI change: owner awareness (D-09/D-10 do not forbid it; Phase 70 touched CI).
- **Executed-test floor:** `MIN_EXECUTED = 12821` while 17,598 run, so about 4,800 tests could vanish without a red build. Raise to 17,598 in PR 0 ("may only go up").
- **Coverage floor:** 93 vs 96.15 measured. Follow the repo's own derivation (floor of the measured value, comment in `pyproject.toml` records date and measurement): set 96 after a `main` or dispatch run with coverage. Dead-code deletion changes the denominator; take the final measurement after the last code PR. Never below 93.
- **Ruff additions** measured with `--isolated`: rules `B` (without `B905`) show 19 `B904`, 13 `B007`, 4 `B023` (closure over loop variable, worth a look: may be latent bugs), 3 `B026`; `PIE` 10 `PIE810`; `E501` 18,973 and `UP031` 8,496 are not viable (as the pyproject comment already says). `ruff format` would change 897 files: do not adopt.
- **Licence headers:** root `LICENSE` is AGPL-3.0; `NOTICE` lists the exceptions; firmware C/H files all have SPDX (91 of 91); Python has none (879 of 900, excluding `.planning`). A gate or a header sweep is an owner decision.

### Anti-Patterns to Avoid

- **Star-import shims:** break `monkeypatch`; use the `sys.modules` alias.
- **Moving a module without fixing its `_REPO_ROOT` bootstrap:** works under pytest (pythonpath includes `.`) but fails in the systemd and `-m` direct-script modes.
- **Deleting tested-but-unused API to "clean up":** reduces the executed-test count, trips `MIN_EXECUTED`, and arguably breaks D-05.
- **Regenerating render baselines to make a diff go away:** only `companion_render_snapshot.py --write`, only when the render legitimately changes.
- **Mixing a cleanup with a feature** or editing `.github/workflows` while also touching code in the same PR.
- **Reopening audited security code** (D-02): treat access, CSRF, token and file-permission logic as frozen.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic state writes and file locks | new tmp-then-rename or `flock` helpers | `server/atomic_io.py` (`atomic_write`, `staged_write`, `exclusive_lock`) | Already the single implementation; lock order documented there |
| Consistent DB snapshot for backups | `cp` of WAL files | `sqlite3.Connection.backup()` as in `skypane_backup.snapshot_db` | Already used and tested |
| Dead-code detection | home-made grep script | vulture plus grep verification (as done here) | False positives (reflection, fixtures, `TYPE_CHECKING`) need human review anyway |
| Test-count and skip policing | new CI logic | `scripts/ci_gates.py` constants | Already enforced on the aggregate check |
| Function-size measurement | new tool | `scripts/check_function_size.py` | Already the gate; extend roots only |
| Render baselines | hand-edited JSON | `test-support/companion_render_snapshot.py --write` | D-07 |
| Waiting in browser tests | `wait_for_timeout` sleeps | `locator.wait_for(state=...)`, `page.wait_for_function`, `test-support/animation_settle.py` | Existing convention (`70-TEST-SPEED-SUMMARY.md`) |

**Key insight:** this phase should add almost no new machinery. Every needed mechanism exists; the work is documenting, ratcheting thresholds, deleting provably unreferenced code, and making a handful of mechanical moves under shims.

## Runtime State Inventory

Applies to the module-move and any rename workstream (the phase moves modules, and may rename history-named test files).

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | No stored data embeds Python module paths. `fleet.db` and `history.db` store no dotted module names. | None for moves. Renaming test files affects only `scripts/ci_shard_weights.json` (per-file weights): update keys or let the median fallback apply (`scripts/ci_shards.py`). |
| Live service config | systemd units reference `server/poll_loop.py`, `stub-server/byos_server.py`, `companion/app.py`, `deploy/backup/skypane_backup.py` by path. Caddy config not module-dependent. | Do not move or rename those four entry files. `deploy/tests/test_units.py` pins the units. |
| OS-registered state | Units installed from `deploy/*.service` by `activate.sh`/`provision.sh`; a path change needs a unit rewrite and a deploy, which is out of scope. | None if entry files stay put. |
| Secrets / env vars | `skypane.env` keys are read by name; no module path involved. | None. |
| Build artifacts | `/opt/skypane/releases/<sha>` is a full `git archive`; old releases keep the old layout (the rollback target). A rollback release that does not know a moved module still runs its own tree. `.coverage` and `__pycache__` are ignored. Pyproject coverage `source` is directory-level. | The rollback caveat applies only to schema changes, which this phase avoids. |
| Docs and scripts naming `-m server.<x>` | deploy README, hardware runbooks, `scripts/fw_publish_signed.py` | Update in the same PR as a CLI move. |

## Common Pitfalls

### Pitfall 1: Shim that does not alias the module
**What goes wrong:** `from new import *` shim; 77 existing `monkeypatch.setattr(module, ...)` calls patch the shim, production code reads the real module, tests pass for the wrong reason or fail mysteriously.
**How to avoid:** `sys.modules[__name__] = new_module`; add one test per shim asserting `old is new`.
**Warning signs:** a patched attribute not taking effect.

### Pitfall 2: `_REPO_ROOT` computed from `__file__`
**What goes wrong:** a moved file reaches the wrong directory; passes under pytest, fails under `python3 server/poll_loop.py` or `-m`.
**How to avoid:** adjust depth in each moved file with a bootstrap; run the `test_import_boundaries.py` style subprocess smoke from a foreign cwd.

### Pitfall 3: Coverage not measured on PRs
**What goes wrong:** deleting dead code or tests shifts coverage; the floor is only checked on `main`, a red main after merge triggers the deploy guard.
**How to avoid:** trigger a `workflow_dispatch` run with coverage on the branch before the ratchet PR (the workflow supports dispatch measurement per `70-MEASUREMENTS.md`), and ratchet last.

### Pitfall 4: Removing test-only API breaks the test-count floor
**What goes wrong:** the executed-test floor (after PR 0) fails on any deleted test.
**How to avoid:** do not delete tested code; if the owner approves, lower nothing: add replacement tests or document the floor change explicitly (floor "may only go up").

### Pitfall 5: i18n and reflection hides "unused" constants
**What goes wrong:** deleting label constants flagged by vulture breaks the i18n catalogue scan (`test-support/i18n_ids.py`) or the French strings in `companion/i18n_fr/`.
**How to avoid:** confirm with `test-support/test_i18n_ids.py` and `companion/test_i18n.py` before removing any `companion` constant.

### Pitfall 6: Documentation test coupling
**What goes wrong:** `deploy/tests/test_docs.py` pins sections of `deploy/README.md` (e.g. "has restore section and rehearsal log"); a docs rewrite can fail it.
**How to avoid:** run `deploy/tests` after any README edit.

### Pitfall 7: Render baseline churn
**What goes wrong:** a "harmless" change alters pixels; `companion/testdata/render_baseline.json` (4.2 MB) or the golden fixtures differ.
**How to avoid:** these cleanups should not change any render; if one does, it is a behaviour change: stop and investigate rather than regenerate.

### Pitfall 8: Branch deletion
**What goes wrong:** deleting remote branches whose content never landed (squash merges hide it; all 39 show commits ahead of `main`). Several look like live explorations (`explore/photo-mode-v1-3`, `sketch/photo-companion`, `codex/v1.1-*`).
**How to avoid:** produce a list for the owner (name, ahead/behind, last commit date) and delete nothing without written approval (D-10).

## Code Examples

### Reproduce the measurements (before and after)

```bash
# Source: commands run in this research session
git ls-files '*.py' ':!.planning' | xargs cat | wc -l
server/.venv/bin/python3 scripts/check_function_size.py report server stub-server | head -20
server/.venv/bin/mypy
server/.venv/bin/ruff check .
server/.venv/bin/python -m pytest --collect-only -q -p no:cacheprovider | tail -1
SKYPANE_COVERAGE=off JOBS=4 ./scripts/run-all-tests.sh -- stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py   # fast per-PR check, 115 tests
gh run view <main run id> --log | grep -E "^.*TOTAL|total: .* tests"   # CI coverage and executed count
```

### No test removed (D-05 check for any test-file change)

```bash
# Source: same method as 70-TEST-SPEED-SUMMARY.md
pytest --collect-only -q | sort > before.ids   # on main
pytest --collect-only -q | sort > after.ids    # on the branch
comm -23 before.ids after.ids                  # must print nothing (renames excepted, listed explicitly)
```

### Backup drift guard (PR 2 sketch, behaviour-over-source)

```python
# deploy/tests/test_backup.py family: seed state via the production writers, then
rc = skypane_backup.backup(state_dir, archive_dir, keep=1)
assert rc == 0
assert "not in include list" not in capsys.readouterr().out   # no persistent file left unclassified
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Shared-password legacy admin sign-in | Auth0 only; `legacy-admin` session principal left in schema | 2026-10-30 | Schema leftover, documented not removed |
| Per-device airline registries and artwork | One fleet-root registry (merged by `fleet_migrate`) | Phase 5x | Per-device copies are rollback-only |
| Deploy on merge to `main` | Manual `workflow_dispatch` in the `production` environment | Phase 66/70 (2026-11-27) | ARCHITECTURE.md and some `.planning` notes still say otherwise |
| Coverage on every PR | Coverage only on `main` and dispatch | 2026-11-26 | Floor ratchet must be measured on main |
| Two-flight poster | Giant-lettering and landscape layouts | Phases 56 and 62 | ARCHITECTURE.md prose out of date |

**Deprecated/outdated:**
- `.planning/research/STACK.md` (kept as history by CLAUDE.md).
- `server/README.md`: title "SkyPane Phase 2 plane-view server", `Pillow==12.3.0` (pinned is 13.0.0).
- `deploy/README.md` provider note mentions Hetzner CX22 against the OVH target (explained, but historical).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | vulture is a legitimate, long-established PyPI package (slopcheck could not be run) | Package Legitimacy Audit | Low: used as a one-off, not added to lock files |
| A2 | The owner prefers documenting the two SQLite migration mechanisms to unifying them | State map | Medium: if the owner wants one mechanism, a larger PR touching `history_db` and `fleet_db` is needed |
| A3 | Moving only `firmware_*`, polling-support and pairing groups satisfies "module moves allowed" | Module-move analysis | Low to medium: owner may want `fleet_*` and `history_*` grouped too |
| A4 | A restored `history.db` whose `caddy_log_offset` exceeds a fresh Caddy log behaves benignly | State map (backup) | Low: a possible one-time gap in battery telemetry after restore |
| A5 | The flaky failure occurred through the async picture probe (not reproduced; code-read only) | Flaky test | Low to medium: if another race exists the test may still flake; verify with 30 CI repetitions |
| A6 | Firmware sections of ARCHITECTURE.md (lines 65-146) are accurate | ARCHITECTURE drift | Medium: not verified against `firmware/main` here |
| A7 | `sys.modules` alias shims behave identically on Python 3.14 | Module moves | Low: documented import-system behaviour, verified on 3.13 |
| A8 | `workflow_dispatch` runs measure coverage (so a branch can be measured before the ratchet) | Pitfall 3 | Low: `70-MEASUREMENTS.md` says main and dispatch measure; confirm the dispatch inputs allow a non-main ref |

## Open Questions (RESOLVED)

[RESOLVED: provisional default document-not-unify; plan 02 documents, plans 11/12 carry the owner override.] 1. **Unify the two migration mechanisms, or document them?**
   - Known: fleet uses ordered transactional migrations with refusal of newer files; history uses concurrent-safe idempotent steps.
   - Unclear: owner appetite for refactoring two hot, audited modules in a no-behaviour-change phase.
   - Recommendation: document and pin; no unification (A2).
[RESOLVED: three groups with shims in plans 13/14/15; owner override via plans 11/12.] 2. **How far should `server/` be regrouped?**
   - Recommendation: three low-fan-in groups with shims; leave `fleet_db`, `history_db`, `device_config`, `poll_loop` (A3). Ask the owner once at plan time.
[RESOLVED: documented, not retired (plan 02); end-of-rollback date asked in plans 11/12.] 3. **`wake_epochs`, the `legacy-admin` principal, per-device registry copies and the legacy dual-write: retire?**
   - All are rollback safety nets or planned future data; retiring any is a behaviour or schema change (needs schema v5 and ends the "previous release runs on migrated state" guarantee). Recommendation: document; ask the owner for an end date of the rollback period; no code change in this phase.
[RESOLVED: decision only, no mass edit; listed in plan 11, deferred in plan 16.] 4. **Licence headers on 879 Python files (SPDX) or a gate only?** Owner decision; the AGPL root plus NOTICE already covers the files.
[RESOLVED: keep as test seams, delete only the 9 zero-reference functions (plan 06); owner override via plans 11/12.] 5. **Tested-but-unused production API (about 30 functions):** keep and label as test seams (recommended), or delete with their tests (conflicts with D-05 and the executed-test floor)?
[RESOLVED: table in plan 11, deletion only with owner approval in plan 12.] 6. **39 remote branches:** the planner should output a table (name, ahead/behind, last commit) for the owner; no deletion without approval.
[RESOLVED: default yes, listed as an owner item in plan 11; plan 10 only tightens CI.] 7. **Extending the function-size gate to `companion deploy` edits `.github/workflows/ci.yml`:** confirm the owner is fine with a CI edit in this phase (Phase 70 closed CI work).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python (local venv) | all checks | yes | 3.13.18 (prod/CI 3.14) | CI is the 3.14 reference |
| pytest, xdist, cov, ruff, mypy | gates | yes (`server/.venv`) | 9.2.0 / 3.8.0 / 7.1.0 / 0.17.6 / 2.4.1 | none needed |
| Chromium (Playwright) | browser tests, flaky-test verification | no | n/a | rely on CI (D-11); optional `workflow_dispatch` repetition |
| gh CLI (REST only; GraphQL blocked in this environment) | CI run data, branch list | yes | n/a | `gh api repos/...` REST routes work; `gh pr list` does not |
| vulture | dead-code analysis | yes (installed into untracked `server/.venv` during research) | 2.16 | grep-only verification |
| slopcheck | package audit | no (install denied by the sandbox) | n/a | tag `[ASSUMED]`, no new runtime package planned |
| shellcheck | script lint | no | n/a | `bash -n` on the 29 shell scripts passed with no output |

**Missing dependencies with no fallback:** none. Browser verification depends on CI.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.2.0 + pytest-xdist 3.8.0 + pytest-cov 7.1.0 + pytest-socket 0.8.1; pytest-playwright 0.10.0 for browser tests |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`, `[tool.mypy]`), root `conftest.py`, `companion/conftest.py` |
| Quick run command | `SKYPANE_COVERAGE=off JOBS=4 ./scripts/run-all-tests.sh -- stub-server/test_phase47_freeze.py server/test_golden_render.py server/test_golden_giant_render.py` (115 tests, about 8 s here) |
| Full suite command | `./scripts/run-all-tests.sh` (CI runs it in `core` and `browser` groups, 7 shards, aggregate check "Lint, test, coverage, attribution") |

### How each cleanup is checked

| Cleanup | Behaviour-preservation proof | Automated command |
|---------|------------------------------|-------------------|
| Any code PR | golden hashes, freeze test, full suite unchanged; collected-id list unchanged | quick run above, then CI; `comm -23 before.ids after.ids` empty |
| Render-affecting suspicion | `server/fixtures/golden/*.json`, `companion/testdata/render_baseline.json`; regenerate only with `test-support/companion_render_snapshot.py --write` and only for a legitimate render change | `pytest server/test_golden_render.py server/test_golden_giant_render.py companion/test_render_baseline*.py` (confirm file names with `--collect-only`) |
| Device protocol | `stub-server/test_phase47_freeze.py` + `measured_fields_freeze.json` (wake cadence, battery telemetry, poll state fields) | `pytest stub-server/test_phase47_freeze.py` |
| Dead-code deletion | `vulture` before and after, grep for the name over all tracked files (code, tests, units, deploy, docs), full suite | `vulture server stub-server companion --min-confidence 60 --exclude '*/.venv/*,*/test_*.py'` |
| Module move | import smoke from a foreign cwd, `python3 server/poll_loop.py --help`, `-m` smoke per CLI, `old is new` shim assertion, `deploy/tests/test_units.py`, mypy list updated | `pytest server/test_import_boundaries.py deploy/tests/test_units.py` plus new shim tests |
| Flaky test | test-only change; 30 consecutive CI executions (loop or repeated dispatch) of the one test; no skip, no xfail | CI browser shard containing `test_browser_ux_03.py` |
| State documentation | docs-only; docs tests; backup and fleet migration tests untouched | `pytest deploy/tests/test_docs.py deploy/tests/test_backup.py server/test_fleet_migrate.py` |
| Backup drift guard (new test) | seeds production writers, asserts no unclassified file; additive only | `pytest deploy/tests/test_backup.py` |
| ARCHITECTURE.md | every backticked path resolves (`git ls-files`), every named function/route exists (grep), claims re-read against the module; docs-only | script of the form used here (extract backticked names, check tracked) |
| Types | `mypy` green with the extended `files` list; no `# type: ignore` added without `warn_unused_ignores` agreeing | `server/.venv/bin/mypy` |
| Lint | `ruff check .` green; any added rule family fixed in the same PR, never ignored wholesale | `server/.venv/bin/ruff check .` |
| Function-size gate extension | gate green on the new roots | `python scripts/check_function_size.py check --max 80 server stub-server companion deploy` |
| Executed-test floor | raised to the measured 17,598 in PR 0; never lowered | `scripts/ci_gates.py`, `test-support/test_ci_gates.py` |
| Coverage floor | raised last, to the floor of the value measured on a `main`/dispatch run, never below 93; comment in `pyproject.toml` updated with date and measurement | CI aggregate check; compare `TOTAL` line |
| No secret or personal data | scan every PR diff and new doc for tokens, host addresses, emails | `scripts/exposure_scan.py` (exists; see `scripts/test_exposure_scan.py`), manual diff read |

### Phase Requirements to Test Map
| Req ID | Behaviour | Test Type | Automated Command | File Exists? |
|--------|-----------|-----------|-------------------|-------------|
| QUAL-01 (no behaviour change) | Golden hashes, freeze, full suite | integration | quick run command above, then CI | yes |
| QUAL-01 (no weakened gate) | Gates only ratchet up | unit/CI | `pytest test-support/test_ci_gates.py test-support/test_check_function_size.py test-support/test_check_comment_history.py` | yes |
| QUAL-01 (architecture document is true) | every referenced path/name exists | script check | extract-and-check script in the PR | add in PR 4 (can be a repo test if the owner wants a lasting guard; behaviour-over-source rule means test the served/real artefact, so prefer a one-off script) |
| QUAL-01 (state backup complete) | no unclassified persistent file | unit | `pytest deploy/tests/test_backup.py` | extend in PR 2 |
| QUAL-01 (before/after record) | numbers reproduced by documented commands | manual/script | commands in "Code Examples" | new `67-BASELINE.md`, `67-AFTER.md` |

### Sampling Rate
- **Per task commit:** quick run command (freeze + goldens, about 8 s) plus the PR's own targeted test.
- **Per wave merge:** full local non-browser suite (`SKYPANE_TEST_GROUP=core ./scripts/run-all-tests.sh`, about 5 min with 4 workers here) plus `ruff`, `mypy`, function-size check.
- **Phase gate:** CI on `main` green with coverage: 17,598 or more executed, 0 skipped, coverage at or above the new floor, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `67-BASELINE.md` with the measured table and commands (this research is the source).
- [ ] Raise `MIN_EXECUTED` to 17,598 (`scripts/ci_gates.py`, adjust `test-support/test_ci_gates.py` if it pins the constant).
- [ ] Save `before.ids` (collected test ids) as a phase artefact (outside the repo or in the baseline doc as a count plus hash) for the `comm` check.
- [ ] Decide whether a `workflow_dispatch` measurement run on the phase branch is possible for the coverage ratchet (A8).

## Security Domain

`security_enforcement` is `true` (ASVS level 1, block on high) in `.planning/config.json`; `nyquist_validation` is `true`. [VERIFIED: file read]

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (frozen by Phase 66) | do not touch `companion/oidc.py`, `sign_in.py`, session code |
| V3 Session Management | no (frozen) | `fleet_sessions` stays as is; `legacy-admin` principal left in schema |
| V4 Access Control | no (frozen) | route x role x owner matrix tests must pass unchanged |
| V5 Input Validation | indirectly (moves must not change validators) | existing validators (`device_dirs` shape check, `fleet_registries` validators) |
| V6 Cryptography | no | no hand-rolled crypto introduced |
| V8 Data Protection / Backup | indirectly | 0600 mode of `fleet.db`, symlink refusal in backup, disk-encryption gate: keep all tests |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret or personal data committed during doc cleanup (repo is public until 70.1) | Information disclosure | Diff read of every PR, `scripts/exposure_scan.py`; use placeholders (`<public-host>`, `<vps-ip>`) as the docs do |
| Deleting an audit or owner-decision note referenced elsewhere | Repudiation | No `.planning` deletion without owner approval (D-10) |
| Import-path change loads a different module than the one patched or audited | Tampering | `sys.modules` alias shim with identity test |
| Path traversal weakened by a move of `device_dirs` | Tampering | `device_dirs` not moved in this plan; its security tests stay |
| Widened file modes through a refactor of connection helpers | Information disclosure | `fleet_db` creates 0600 before SQLite touches the file; keep its test |

## Sources

### Primary (HIGH confidence)
- Repository files read in this session: `server/fleet_db.py`, `server/history_db.py`, `server/fleet_migrate.py`, `server/device_dirs.py`, `server/atomic_io.py`, `deploy/backup/skypane_backup.py`, `stub-server/byos_server.py` (state and registry sections), `companion/static/panel-lookup.js`, `companion/test_browser_ux_03.py`, `companion/test_browser_ux_01.py`, `ARCHITECTURE.md`, `pyproject.toml`, `scripts/ci_gates.py`, `scripts/run-all-tests.sh`, `deploy/*.service`, `deploy/deploy.sh`, `.github/workflows/deploy.yml` (header), `.claude/CLAUDE.md`.
- Planning documents: `67-CONTEXT.md`, `ROADMAP.md` Phase 67, `REQUIREMENTS.md` QUAL-01, `66-AUDIT.md`, `66-FIX-LEDGER.md`, `66-VERIFICATION.md`, `70-TEST-SPEED-SUMMARY.md`, `70-MEASUREMENTS.md`.
- GitHub Actions run 45993237674 (main, 2026-11-27, success): jobs, per-shard pytest summaries, durations, `TOTAL 30488 1174 96%`, `total: 17598 tests, 0 failures, 0 errors, 0 skipped, 17598 executed`.
- Commands run locally: `ruff check .`, `mypy` (51 files), `check_function_size.py`, `pytest --collect-only` (17,598), freeze and golden tests (115 passed), vulture 2.16, AST analyses (type coverage, importer graph, identical bodies), shim identity experiment on CPython 3.13.
- GSD tooling: `~/.claude/get-shit-done/bin/lib/profile-output.cjs` (architecture section generation).

### Secondary (MEDIUM confidence)
- GitHub REST API for branch list and compare (ahead/behind), 39 non-main branches.

### Tertiary (LOW confidence)
- vulture provenance (A1), 3.14 shim behaviour (A7), caddy offset restore behaviour (A4).

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH (no new dependencies; all tools pinned in repo).
- Architecture (state map, drift, move analysis): HIGH for what was read and measured; MEDIUM for firmware-section accuracy (not checked).
- Pitfalls: HIGH (each tied to a verified mechanism or CI fact).
- Flaky root cause: MEDIUM (code-level cause confirmed by a sibling test's comment, not reproduced).

**Research date:** 2026-11-27
**Valid until:** about 2026-12-11 (the tree is moving: Phase 68/70 landed days ago; re-run the measurement commands at plan time and before the "after" record)
