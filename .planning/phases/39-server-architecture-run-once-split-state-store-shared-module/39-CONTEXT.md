# Phase 39: Server architecture — run_once split, state store, shared modules - Context

**Gathered:** 2026-09-27
**Status:** Ready for planning
**Source:** The developer's planning brief for `/gsd-plan-phase 39`, the audit ledger (`.planning/audits/2026-09-23-code-audit.md`, rows ARC-01..06, decisions D-A1..D-A6), and the Phase 38 code on `claude/plan-phase-38` (this branch's base).

<domain>
## Phase Boundary

Remediate ARC-01..ARC-06: **where code lives and how it is wired**, not what it does. Behaviour must not change. The full pytest suite (Phase 32/33 conventions) is the safety net, plus mypy green on the typed modules.

Phase 38 reshaped the code this phase refactors (one SQLite connection per cycle via `history_db.write_batch`, write-once `poll_state`, per-provider rate state in `history.db` meta, parallel providers, lazy `page_context`, `health_signals`). Every ledger finding is re-located against the current code; the ledger's line numbers are stale.

Current sizes (re-measured on this branch): `server/poll_loop.py` 1594 lines with `_run_once_locked` ≈ 630 lines (`poll_loop.py:907-1540`); `server/plane/render.py` 2049; `server/plane/calendar_rules.py` 1433; `server/device_config.py` 746; `stub-server/byos_server.py` 894 (stdlib-only today, imports nothing from `server/`).

Module-global setters still called every cycle: `illustrations.set_override_state_dir`, `manual_resolutions.set_manual_registry_state_dir`, `colour_rules.set_colour_rules_state_dir` (`poll_loop.py:945-950`).

Companion (non-test) uses of `server.poll_loop`: `companion/app.py` (`run_once`, `PollBusy`, `poll_cycle_lock`, `now_s`, `DEFAULT_STATE_DIR`, `_poll_state_path`), `companion/pages/health_page.py` (`load_poll_state`), `companion/pages/airlines_page.py`.
</domain>

<decisions>
## Implementation Decisions

### Locked by the ledger, ROADMAP and brief
- **ARC-01:** the poll cycle reads as named steps — `load_cycle_context` / `decide_hold` / `advance_display_queue` / `render_and_publish` / `persist` / `record` (names may be refined, the shape may not) — over one `CycleContext` dataclass. The render → pack → write → gallery sequence exists once. Success criterion: no function in `server/` over 80 code lines (code lines = non-blank, non-comment, non-docstring); `run_once` cyclomatic complexity measured before and after and recorded in a committed `39-ARC-BASELINE.md` (same pattern as `38-EFF-BASELINE.md`).
- **ARC-02:** `server/state_store.py` owns `poll_state.json` (path, load, serialise, save, persist-if-changed). The companion imports `state_store`, never `server.poll_loop`.
- **ARC-03:** split `server/plane/render.py` into a `render/` package (`layout`, `text`, `hold_screens`, `cli` — refine as the code dictates), `server/plane/calendar_rules.py` into a package (`ics`, `registry`, `match`), move theme logic out of `device_config.py` into `themes.py`, and one shared `net/safe_fetch.py` holding the URL-safety check so `notify.py` stops importing the private `calendar_rules._url_is_safe`.
- **ARC-04:** no module-global setters. State dirs (and any other per-cycle input) are passed explicitly.
- **ARC-05:** quiet hours, battery-critical hysteresis and the battery discharge curve exist **once**, in one shared module used by `server/`, `stub-server/byos_server.py` and `companion/`. The "vendored byos" rationale in `ARCHITECTURE.md` is corrected.
  - **D-4 (developer decision, asked in French 2026-09-27): unify the quiet-hours invalid-config fallback now.** Research found the two current copies disagree on an edge case: with quiet hours enabled and an invalid start/end time on disk, the server falls back to 23:00–07:00 and holds (sleeps) the display, while byos treats quiet hours as disabled and keeps serving fresh data. The developer chose to **merge now, on the server's fallback** (23:00–07:00 + hold) rather than keep both behaviours: byos adopts the same fallback. This is a deliberate, small behaviour change — call it out explicitly in the SUMMARY/PLAN as an intentional deviation from "behaviour unchanged" (the *reachable* current behaviour, i.e. valid config, does not change; only the invalid-config edge case does). Cover the merged fallback with one shared test; retire the test that pinned byos's old "disabled" fallback (retarget it, don't delete the coverage silently — replace the assertion with the new merged behaviour and say so in the plan's commit message).
  - **D-5 (developer decision, asked in French 2026-09-27): the companion theme preview becomes vendored-only.** Removing the module-global illustration-override setter (ARC-04) means the theme preview can no longer see an in-process `/poll-now`'s live override — it only sees the vendored/on-disk illustration set. The developer accepted this as a minor, intentional side effect of explicit injection; document it in the phase SUMMARY.
  - **D-6 (developer decision, asked in French 2026-09-27): the shared module is `server/device_policy.py`, stdlib-only.** It holds quiet hours (D-4's merged behaviour), battery-critical hysteresis and the battery discharge curve. `companion/battery.py`'s existing "imports nothing from `server`" isolation test (`companion/test_companion_app_03.py`) is retargeted to an allowlist: it may import only `server.device_policy` (and nothing else from `server/` or third-party packages). No change to `deploy.sh` or the deploy tests.
- **ARC-06:** type hints on the pure core; mypy added to `server/requirements-dev.in` (lock regenerated through `scripts/lock-deps.sh`, never by hand) and run in CI (`.github/workflows/ci.yml`) on the typed modules; green.
- Behaviour unchanged: no test assertion is weakened or deleted to get green. Tests may be **retargeted** (import path / monkeypatch target moved to where the code now lives) — that is the expected cost of a move, and each retarget keeps the same assertion.
- No new runtime dependency (production stays stdlib + Pillow + requests; mypy is dev-only). Code, comments and docs in English; no phase/plan/requirement IDs in comments (`scripts/check_comment_history.py`). Ruff and coverage gate stay green.

### Claude's Discretion (decided here, not asked)
- **D-1: The poll cycle becomes a library module.** `run_once` and its steps, `PollBusy` and `poll_cycle_lock` move out of the entrypoint into a library module (e.g. `server/poll_cycle.py`, or a `server/cycle/` package if 80-line functions need several files). `server/poll_loop.py` stays the systemd entrypoint (`build_parser`/`main`) so `deploy/skypane-poll.service` does not change. The companion's `/poll-now` imports the library module. This is what "the companion no longer imports `server.poll_loop`" requires.
- **D-2: Keep public import paths stable where cheap.** When `render.py` / `calendar_rules.py` become packages, `server.plane.render` / `server.plane.calendar_rules` stay importable (package `__init__` re-exports the public API), so companion files owned by Phase 40 need no edits for ARC-03. A package must not be named `calendar` if that could shadow the stdlib module on any `sys.path` configuration.
- **D-3: byos imports the shared module via the same repo-root `sys.path` bootstrap the companion and poll loop use.** The deployed layout (`/opt/skypane/current/{server,stub-server,companion}`) already ships `server/` next to `stub-server/`; the byos unit's sandbox must still allow reading it (check `deploy/skypane-byos.service`). The shared module is stdlib-only so byos gains no dependency.
- Exact module names, the `CycleContext` field list, and the mypy strictness (`--strict` on the pure core vs. `disallow_untyped_defs` per module) are the planner's call, documented in the plans.

### Coordination (parallel sessions)
- **This phase owns** `server/`, `stub-server/` and the new shared modules. **Phase 40 owns `companion/`** and is executing in parallel. Companion edits here are limited to the minimal import switches ARC-02/ARC-05 require (`companion/app.py`, `companion/pages/health_page.py`, `companion/pages/airlines_page.py`, `companion/battery.py`, `companion/wake.py` as needed) and their test retargets, each in its **own small commit**, so a merge with Phase 40 stays trivial. Merge `main` often.
- Phase 42 (OTA) later touches `server/poll_loop.py`; do not pre-empt it.
- Base branch: `claude/plan-phase-38` (PR #150, not yet merged into `main` at planning time). Before opening the PR, check #150; if merged, merge `origin/main` and resolve.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/audits/2026-09-23-code-audit.md`: ledger rows ARC-01..06, decisions D-A1..D-A6
- `.planning/phases/38-efficiency-companion-poll-cycle-storage/38-RESEARCH.md`, `38-EFF-BASELINE.md`, `38-VERIFICATION.md`: the code this phase starts from and the baseline-document pattern
- `ARCHITECTURE.md` (the "vendored byos" rationale, to correct)
- `deploy/skypane-byos.service`, `deploy/skypane-poll.service`, `deploy/skypane-companion.service`: entrypoints and sandbox
- `companion/test_suite_guards.py`, `companion/conftest.py`, `test-support/companion_app_server.py`: test conventions
- `.claude/CLAUDE.md`, `scripts/check_comment_history.py`, `scripts/lock-deps.sh`, `scripts/run-all-tests.sh`, `.github/workflows/ci.yml`
</canonical_refs>

<deferred>
## Deferred Ideas

- Companion architecture (routes, pages, templates, i18n keys): Phase 40.
- OTA: Phase 42.
</deferred>

---

*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Context gathered: 2026-09-27 from the developer's brief*
