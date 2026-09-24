# Phase 33: Companion tests on pytest — behaviour over source text - Context

**Gathered:** 2026-09-24
**Status:** Ready for planning
**Source:** Audit ledger `.planning/audits/2026-09-23-code-audit.md` (TST-10..TST-15, decisions D-A1..D-A6), the Phase 32 artifacts, and the developer's phase brief for this session

<domain>
## Phase Boundary

Phase 33 finishes the pytest migration that Phase 32 started. It migrates the **companion** side:

- The companion harnesses `companion/test_companion_app.py`, `test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`, `test_i18n.py` and `test_contrast_check.py` become native pytest modules (TST-10).
- The browser harnesses `companion/test_browser_ux.py`, `test_browser_ux_health_drawings.py`, `test_browser_ux_quiet_wake.py` (plus the shared helper `test_browser_ux_helpers.py`) become pytest-playwright tests. They run in parallel under xdist, and a missing browser is a CI failure (TST-11).
- One shared app-server fixture replaces the copied `Harness` class (×5), `http_request` (×6) and `_NoRedirectHandler` (×4) (TST-10).
- Every assertion that reads source text, asserts on a comment, reads `style.css` as raw text, or opens a `.planning/` / UI-SPEC file is either rewritten as a behaviour or parsed-DOM assertion, or deleted with a stated reason in the migration ledger (TST-12). This unblocks Phase 35's comment purge, because no test may depend on a comment's wording.
- Root-safe: permission tests skip under euid 0, and nothing is written outside `tmp_path`. This includes `anomaly_active("/nonexistent/...")` creating directories on the host (TST-13).
- Retire `companion/test_legacy_harness_shim.py`, `LEGACY_COMPANION_HARNESSES` / `LEGACY_COMPANION_COLLECT_IGNORE` and the `collect_ignore` wiring, the remaining hand lists, and every `EXPECTED_CHECK_COUNT` (TST-14).
- Closing parity: every pre-migration companion check is accounted for in the ledger (ported, or deleted with a reason). Together with Phase 32's 769 server checks, this covers all 2018 pre-migration checks. Coverage must be ≥ the pre-migration figure (TST-15).

**Not in this phase:** changing companion production behaviour (tests only; a production fix is allowed only when a rewritten behaviour test exposes a real bug, and it must be recorded as a deviation), the comment purge itself (Phase 35), companion architecture (Phase 40), and Phase 37's auth/Origin work (but see Coordination).

</domain>

<decisions>
## Implementation Decisions

### Framework and infrastructure (D-A2, locked; reuse Phase 32 exactly)
- pytest stays dev-only. Reuse Phase 32's infrastructure as it is: the repo-root `conftest.py`, `test-support/skypane_test_support.py` (`child_env`, `FakeProviders`, the network guard and `sitecustomize.py` for children), the `fake_providers` fixture, `pyproject.toml` `[tool.pytest.ini_options]` / coverage config, and `scripts/run-all-tests.sh` as the single entry point (`pytest -n auto --cov`).
- Any server the tests start (companion `app.py`, byos) is launched with `child_env(...)`, so the cross-process no-network guard applies to it. Tests keep using the fake providers wherever a poll path is exercised.
- New dev dependency `pytest-playwright` (and anything it pulls in) goes into `server/requirements-dev.in`, and the hash lock is regenerated with `scripts/lock-deps.sh`. The runtime lock `server/requirements.txt` is unchanged.

### One shared app-server fixture (TST-10)
- A single fixture/helper module (e.g. `companion/conftest.py` plus a small support module) provides: starting `companion/app.py` on a free loopback port with an isolated state dir under `tmp_path` / `tmp_path_factory`, the password/auth session helpers, an HTTP client that does not follow redirects, and teardown that kills the process group. It replaces every copied `Harness`, `http_request` and `_NoRedirectHandler`.
- Fixture scope is Claude's discretion (per-module or per-session server with per-test state reset is fine for speed), but tests must not leak state into one another in a way that makes xdist distribution order-dependent.

### Behaviour over source text (TST-12, locked)
- No test may: open a production source file (`*.py`, `*.html` templates, `*.js`) to grep its text; assert on a comment or docstring; read `companion/static/style.css` (or any CSS) as raw text; or open anything under `.planning/` or any UI-SPEC file.
- Each such check is **rewritten** as a behaviour assertion (HTTP response, parsed DOM with the stdlib `html.parser` or equivalent, a rendered-image property, the computed style in a real browser via Playwright), or **deleted** with a stated reason in the ledger (e.g. "asserted plan history in a comment; no behaviour").
- CSS-token/contrast checks: parse the served stylesheet structurally (a tokenizer/parser over the CSS served by the app, not a regex over the file on disk) or move them to the browser tests as computed-style assertions. Claude's discretion which one, per check.
- A guard (a meta-test or ruff/grep CI check) proves the rule holds: no companion test opens `.planning/`, and no companion test reads a production source file as text.

### Browser tests (TST-11, locked)
- pytest-playwright, Chromium headless shell (already installed and cached in CI by Phase 32's `playwright install --only-shell`).
- Parallelised per test with xdist (no single monolithic browser test).
- A missing browser or Playwright **fails** in CI (`CI=true` or `SKYPANE_REQUIRE_BROWSER=1`). Locally it is a visible pytest skip with a reason. It never passes silently.

### Root safety (TST-13, locked)
- Permission/`chmod` tests are marked to skip under euid 0 (reuse the `requires_non_root` marker Phase 32 introduced).
- Every path a test writes is inside `tmp_path`. No `/nonexistent/...` path that production code might `mkdir` as root: use a `tmp_path` subpath that is guaranteed absent, or a read-only `tmp_path` dir when non-root.
- The suite passes both as root and as a non-root user.

### Retirements (TST-14, locked)
- Delete `companion/test_legacy_harness_shim.py` and the legacy lists/collect-ignore in `skypane_test_support.py` / `conftest.py` once no legacy harness is left. Every `EXPECTED_CHECK_COUNT`, `check()` counter and `main()` runner in the companion tests is gone.
- `scripts/run-all-tests.sh` stays a thin pytest wrapper. Its comments and the `HARNESS_TIMEOUT_S` reference to the shim are updated.
- Transition: while migration is in flight, the shim keeps running whichever legacy harnesses are not yet migrated. Each plan that migrates a harness removes it from the legacy list in the same commit, so the suite is green after every plan.

### Migration ledger and parity (TST-15, locked)
- Same format and tooling as Phase 32: capture per-harness baselines from the harness's own PASS/FAIL stdout **before** rewriting (`33-BASELINE/`), one fragment per harness (`33-ledger/<key>.md`), an assembled `33-MIGRATION-LEDGER.md`, and a checker. Reuse or copy/extend `32-ledger-check.py` into `33-ledger-check.py` with the 9 companion harnesses. The browser harnesses need a baseline captured with Chromium available.
- Every ledger row is `ported` → a real pytest node id, or `deleted` + a non-empty reason. Parametrised ids count. Phase 33 total + Phase 32's 769 = 2018. If the measured companion baseline differs from 2018 − 769, the ledger records the reason (e.g. checks added by Phases 34/37 since the audit).
- Coverage: record the pre-migration figure (the Phase 32 gate is 93, measured 93.35 %) and prove the post-migration run is ≥ it. `fail_under` may be raised to the new measured floor, never lowered.

### Test location
- Migrated companion tests stay in `companion/` (Phase 32 precedent). Splitting the very large files (`test_status_pages.py` 16k lines, `test_config_page.py` 13.6k, `test_companion_app.py` 12k) into several smaller pytest modules is allowed and encouraged when it helps xdist and readability. The ledger maps to the new node ids either way.

### Coordination with Phase 37 (parallel session)
- Phase 37 wave A (companion auth throttle, Origin check, ops) may land on main during this phase and add companion tests. Merge main into `claude/phase-33` often. If both sides touch the same test file, keep both behaviours. Checks added by Phase 37 in legacy style are migrated too (ledger rows, reason "added after audit baseline"), and checks added natively in pytest need no ledger row.

### CI
- The existing `ci.yml` test job (`SKYPANE_REQUIRE_BROWSER=1`, `--only-shell` Chromium cache, 3.14, hash-enforced install) stays the gate. Only the dev lock changes (pytest-playwright). Commit per plan, push to `claude/phase-33`, open a draft PR, drive CI to green.

### Claude's Discretion
- Fixture design details and scope, module splits, markers (`browser`, `slow`), whether browser tests share one browser per worker (pytest-playwright's default session-scoped browser) and one app server per module.
- Order and batching of harness migrations across plans (the largest harnesses may need several plans each).
- Structural CSS parsing approach (small stdlib tokenizer vs computed style in the browser).
- Whether the "no source-text reads" guard is a pytest meta-test or a CI grep step.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit and requirements
- `.planning/audits/2026-09-23-code-audit.md` — TST-10..TST-15 findings/evidence/remediation, D-A1..D-A6, measured baseline (2018 checks, 93 % coverage)
- `.planning/REQUIREMENTS.md` — TST-10..TST-15
- `.planning/ROADMAP.md` — Phase 33 goal and the 5 success criteria

### Phase 32 (infrastructure to reuse)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-CONTEXT.md` — decisions (shim transition, guard, ledger)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-PATTERNS.md` — migration patterns (check() → test functions, parametrisation, fixtures)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-VERIFICATION.md` — what shipped; warning about `stub-server/test_devices_registry.py` lacking `child_env()`
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-REVIEW.md` — open IN-01..IN-05 items (IN-05: companion harnesses red as root)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-MIGRATION-LEDGER.md`, `32-ledger-check.py`, `32-BASELINE/`, `32-ledger/` — ledger format and checker
- `conftest.py`, `test-support/skypane_test_support.py`, `test-support/sitecustomize.py`, `test-support/test_test_support.py`
- `companion/test_legacy_harness_shim.py` — the shim to retire
- `pyproject.toml`, `scripts/run-all-tests.sh`, `scripts/lock-deps.sh`, `server/requirements-dev.in` / `.txt`, `.github/workflows/ci.yml`

### Harnesses to migrate
- `companion/test_companion_app.py`, `test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`, `test_i18n.py`, `test_contrast_check.py`
- `companion/test_browser_ux.py`, `test_browser_ux_health_drawings.py`, `test_browser_ux_quiet_wake.py`, `test_browser_ux_helpers.py`
- Phase 31 (`.planning/phases/31-ci-test-suite-parallelize-companion-test-browser-ux-py-to-cu/`) — prior browser-test parallelisation work and baseline-checks format

### Design system (for any rewritten UI assertion)
- `.claude/skills/sketch-findings-skypane/SKILL.md` — tokens, contrast rules (the behaviour the contrast/CSS tests protect)

</canonical_refs>

<specifics>
## Specific Ideas

- Evidence spots named by the audit: `test_status_pages.py:8394` (comment contains a ticket ID), `test_status_pages.py:8401-8412` and `test_config_page.py:8595-8628` (read `.planning/*.md` / UI-SPEC), `test_status_pages.py:8201` (`anomaly_active("/nonexistent/...")` mkdir as root), `test_browser_ux.py:22-29` (SKIP counts as PASS). Line numbers may have drifted.
- Audit counts: 309 checks read source files, 77 read `style.css` as text.
- Success criterion 3 must be provable mechanically: a guard test/CI step fails if a companion test opens `.planning/`, a UI-SPEC, or a production source file as text.
- Success criterion 4: run the full suite once as root and once as a non-root user (e.g. `runuser -u nobody`), and prove nothing is written outside `tmp_path` (e.g. `git status --porcelain` clean and no new files under `/nonexistent` or the repo after a run).

</specifics>

<deferred>
## Deferred Ideas

- The comment purge itself → Phase 35 (unblocked by this phase).
- Companion routes/pages/templates/i18n-keys restructuring → Phase 40. Tests written here should assert behaviour so they survive that refactor.
- `stub-server/test_devices_registry.py` `child_env()` warning from 32-VERIFICATION: fold in if cheap (same fixture family), otherwise leave for Phase 36.

</deferred>

---

*Phase: 33-companion-tests-on-pytest-behaviour-over-source-text*
*Context gathered: 2026-09-24 from the audit ledger, Phase 32 artifacts and the developer's phase brief*
