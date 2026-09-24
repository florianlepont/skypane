# Phase 33: Companion tests on pytest — behaviour over source text - Research

**Researched:** 2026-09-24
**Domain:** pytest migration of 9 hand-rolled companion test harnesses (70k lines) + pytest-playwright browser testing + CSS/source-text assertion rewrite + root-safety + migration-ledger parity
**Confidence:** HIGH (every quantitative claim below was produced by actually running the harnesses in this sandbox, not by reading source and estimating)

## Summary

Phase 33 finishes what Phase 32 started. Phase 32 already built and proved the entire
infrastructure this phase reuses verbatim: `conftest.py`'s socket guard and `fake_providers`
fixture, `test-support/skypane_test_support.py` (`child_env`, `FakeProviders`,
`requires_non_root`), `test-support/sitecustomize.py`, the `pyproject.toml` pytest/coverage
config, `scripts/run-all-tests.sh`, and — critically — the `32-ledger-check.py` tool and
migration-ledger format, which this phase copies to `33-ledger-check.py` with a 9-item
`HARNESSES` list instead of 15. Nothing about Phase 33 requires new test infrastructure
design; it requires disciplined, high-volume mechanical migration of ~1,250 checks across
9 files (69,804 lines) plus one genuinely new capability: pytest-playwright.

I captured a **live, verified baseline** of all 9 companion harnesses by running each one
standalone in this sandbox (`server/.venv/bin/python3`, Python 3.11.15, euid 0/root — this
sandbox has no Python 3.14, unlike production/CI; see Environment Availability). Total:
**1,250 checks** (1,247 PASS + 3 FAIL as root in this sandbox). The audit's arithmetic
(2018 − 769 = 1249) is **off by one** from what I measured — flag this explicitly in the
ledger's closing-parity note per CONTEXT.md's own instruction ("if the measured companion
baseline differs from 2018 − 769, the ledger records the reason"). The 3 FAILs are **not**
regressions: they are the exact root-sandbox artifacts Phase 32's own baseline notes and
32-REVIEW IN-05 already documented (2× WR-11 `chmod` checks in `test_companion_app.py`, 1×
`anomaly_active("/nonexistent/...")` in `test_status_pages.py` — I confirmed live that this
call **actually creates `/nonexistent/definitely-not-here` on the host filesystem as root**,
direct, reproduced evidence for TST-13's success criterion 4).

pytest-playwright 0.9.0 is compatible with the pinned `playwright==1.63.0`, `pytest==9.1.1`,
and Python 3.14 (verified: `requires_dist: playwright>=1.18, pytest<10,>=6.2.4`, installed
and exercised under `pytest-xdist` in this sandbox — 4 xdist workers each launched their own
browser instance and ran tests in parallel). `uv pip compile --generate-hashes` regenerates
`server/requirements-dev.txt` cleanly with `pytest-playwright` added, keeping `playwright`
pinned at 1.63.0 exactly as CONTEXT.md requires. One live environment defect was found and
worked around: **this sandbox's `/opt/pw-browsers` cache holds Chromium revision 1194, but
the pinned `playwright==1.63.0` expects revision 1243** — Chromium currently cannot launch
here even with today's already-shipped code (`test_browser_ux.py` correctly prints its `SKIP`
line and exits 0). A fresh `playwright install --only-shell chromium` against a scratch
`PLAYWRIGHT_BROWSERS_PATH` downloads r1243 successfully through the sandbox's proxy and all
three browser harnesses then run for real (75/75, 11/11, 9/9 — see Quantitative Inventory).

**Primary recommendation:** migrate in the order small→large, non-browser→browser
(`test_contrast_check.py`, `test_i18n.py`, `test_view_pages.py`, `test_config_page.py`,
`test_companion_app.py`, `test_status_pages.py`, then the 3 browser files), splitting each of
the 4 huge files into multiple pytest modules per CONTEXT.md's explicit permission, building
the shared app-server fixture once (module-scoped `Harness`-equivalent) in `companion/conftest.py`
before the first migration plan, and copying `32-ledger-check.py` → `33-ledger-check.py` with
one small fix (the `SUMMARY_RE` must tolerate `test_i18n.py`'s summary line, which — uniquely
among the 9 files — has no `"<name>: "` prefix).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Test discovery/execution/parallelism | Test Framework (pytest + xdist) | — | Already Phase 32 infra; this phase adds files, not mechanism |
| App-server-under-test lifecycle (start/stop `companion/app.py`) | Test Framework (fixture) | API/Backend (the real `companion/app.py` process) | The fixture is test-tier plumbing; the thing it drives is the real backend, unmodified |
| HTTP request/response assertions (former `Harness`/`http_request`) | Test Framework | API/Backend | Behaviour observed through the real HTTP surface, never through source text |
| DOM/computed-style assertions (browser checks) | Browser/Client (real Chromium via Playwright) | Test Framework | TST-12's preferred replacement for CSS-as-text checks — real rendering engine, not a parser guess |
| Served-stylesheet structural checks (non-browser harnesses) | API/Backend (the served `/static/style.css` route) | Test Framework | Must fetch via HTTP from the running app, never `open()` the file on disk — the served bytes are the API's own artifact |
| Network isolation / fake ADS-B provider | Test Framework | API/Backend (server/plane/detect.py, enrich.py seams) | Guard and fixture are test-tier; the seam they patch lives in the backend |
| CI browser presence gate | Test Framework / CI | — | A pytest-collection/fixture-level decision, not an app concern |

## Project Constraints (from CLAUDE.md)

- **GSD Workflow Enforcement**: no direct repo edits outside a GSD command — this phase's
  implementation plans must go through `/gsd-execute-phase`.
- **Tests / CI stack row** (already updated by Phase 32, this phase extends it): pytest +
  pytest-xdist + pytest-cov (`./scripts/run-all-tests.sh` wraps `pytest -n auto --cov`), a
  pytest-socket non-loopback guard, **"companion's remaining hand-rolled harnesses run
  through a pytest shim until Phase 33"** — this exact sentence in CLAUDE.md must be updated
  by this phase's closing plan once the shim is retired (TST-14).
  Also lists: ruff, coverage gate at the measured floor, **"Playwright headless shell"**
  (already named — this phase makes it pytest-playwright-driven instead of hand-rolled),
  hash-locked `server/requirements*.txt`, GitHub Actions with firmware host tests.
- **Server stack**: "Python 3.14 (Ubuntu 26.04 distro python3), stdlib + Pillow + requests
  only" — production code is out of scope for new dependencies. `pytest-playwright` and any
  CSS-parsing library (if chosen) are **dev-only** (`server/requirements-dev.in`), never
  touching `server/requirements.txt` — this matches Phase 32's own precedent exactly.
- No conventions/architecture sections populated yet in CLAUDE.md beyond the stack table.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Framework and infrastructure (D-A2, locked; reuse Phase 32 exactly)**
- pytest stays dev-only. Reuse Phase 32's infrastructure as-is: repo-root `conftest.py`,
  `test-support/skypane_test_support.py` (`child_env`, `FakeProviders`, network guard,
  `sitecustomize.py`), the `fake_providers` fixture, `pyproject.toml` pytest/coverage config,
  `scripts/run-all-tests.sh` as the single entry point.
- Any server the tests start (companion `app.py`, byos) is launched with `child_env(...)`.
- New dev dependency `pytest-playwright` (and anything it pulls in) goes into
  `server/requirements-dev.in`; hash lock regenerated with `scripts/lock-deps.sh`. Runtime
  lock `server/requirements.txt` unchanged.

**One shared app-server fixture (TST-10)**
- A single fixture/helper module (e.g. `companion/conftest.py` + a small support module)
  provides: starting `companion/app.py` on a free loopback port with an isolated state dir
  under `tmp_path`/`tmp_path_factory`, password/auth session helpers, a non-redirect-following
  HTTP client, and process-group teardown. Replaces every copied `Harness`, `http_request`,
  `_NoRedirectHandler`.
- Fixture scope is Claude's discretion; tests must not leak state in a way that makes xdist
  distribution order-dependent.

**Behaviour over source text (TST-12, locked)**
- No test may: open a production source file (`*.py`/`*.html`/`*.js`) to grep its text;
  assert on a comment/docstring; read `companion/static/style.css` as raw text; open anything
  under `.planning/` or a UI-SPEC file.
- Rewrite as behaviour (HTTP response, parsed DOM via `html.parser`, rendered-image property,
  real-browser computed style) or **delete** with a stated reason in the ledger.
- CSS/contrast checks: parse the **served** stylesheet structurally (a tokenizer/parser over
  what the app serves, not a regex over the file on disk) OR move to browser computed-style
  checks. Claude's discretion per check.
- A guard (meta-test or CI grep) proves the rule holds.

**Browser tests (TST-11, locked)**
- pytest-playwright, Chromium headless shell (already installed/cached by Phase 32's
  `playwright install --only-shell`).
- Parallelised per test with xdist (no single monolithic browser test).
- A missing browser/Playwright **fails** in CI (`CI=true` or `SKYPANE_REQUIRE_BROWSER=1`).
  Locally it is a visible pytest skip with a reason. Never a silent pass.

**Root safety (TST-13, locked)**
- Permission/`chmod` tests skip under euid 0 (`requires_non_root` marker, reused from Phase 32).
- Every path a test writes is inside `tmp_path`. No `/nonexistent/...` path production code
  might `mkdir` as root.
- Suite passes as root and as non-root.

**Retirements (TST-14, locked)**
- Delete `companion/test_legacy_harness_shim.py` and the legacy lists/collect-ignore in
  `skypane_test_support.py`/`conftest.py` once no legacy harness remains. Every
  `EXPECTED_CHECK_COUNT`, `check()` counter, `main()` runner in companion tests is gone.
- `scripts/run-all-tests.sh` stays a thin pytest wrapper; its comments and
  `HARNESS_TIMEOUT_S` shim reference updated.
- Transition: shim keeps running unmigrated harnesses; each migration plan removes that
  harness from the legacy list in the same commit so the suite stays green after every plan.

**Migration ledger and parity (TST-15, locked)**
- Same format/tooling as Phase 32: per-harness baselines (`33-BASELINE/`), one fragment per
  harness (`33-ledger/<key>.md`), assembled `33-MIGRATION-LEDGER.md`, a checker
  (reuse/extend `32-ledger-check.py` → `33-ledger-check.py`, 9 companion harnesses). Browser
  harness baselines need Chromium available.
- Every row is `ported` → real pytest node id, or `deleted` + non-empty reason. Parametrised
  ids count. Phase 33 total + Phase 32's 769 = 2018 (**research found 1250, not 1249** — see
  Migration Ledger & Baseline Capture below).
- Coverage: record pre-migration figure (Phase 32 gate 93, measured 93.35%); post-migration
  must be ≥ it. `fail_under` may rise, never fall.

**Test location**
- Migrated tests stay in `companion/`. Splitting the very large files
  (`test_status_pages.py` 16k, `test_config_page.py` 13.6k, `test_companion_app.py` 12k)
  into smaller pytest modules is allowed and encouraged for xdist/readability. Ledger maps
  to new node ids either way.

**Coordination with Phase 37 (parallel session)**
- Phase 37 wave A (companion auth throttle, Origin check, ops) may land on `main` during this
  phase. Merge `main` into `claude/phase-33` often. Checks Phase 37 adds in legacy style are
  migrated too (ledger row, reason "added after audit baseline"); checks added natively in
  pytest need no ledger row.

**CI**
- Existing `ci.yml` test job (`SKYPANE_REQUIRE_BROWSER=1`, `--only-shell` cache, 3.14,
  hash-enforced install) stays the gate. Only the dev lock changes (pytest-playwright).

### Claude's Discretion
- Fixture design details/scope, module splits, markers (`browser`, `slow`), whether browser
  tests share one browser per worker (pytest-playwright default) and one app server per module.
- Order/batching of harness migrations across plans (largest harnesses may need several
  plans each).
- Structural CSS parsing approach (small stdlib tokenizer vs. computed style in the browser).
- Whether the "no source-text reads" guard is a pytest meta-test or a CI grep step.

### Deferred Ideas (OUT OF SCOPE)
- The comment purge itself → Phase 35 (unblocked by this phase).
- Companion routes/pages/templates/i18n-key restructuring → Phase 40. Tests written here
  should assert behaviour so they survive that refactor.
- `stub-server/test_devices_registry.py`'s missing `child_env()` (32-VERIFICATION warning) —
  fold in if cheap (same fixture family), otherwise leave for Phase 36.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TST-10 | Companion harnesses migrated to pytest; one app-server fixture replaces every `Harness`/`http_request`/`_NoRedirectHandler` copy | Architecture Patterns (Harness diff table), Code Examples (shared fixture design) |
| TST-11 | pytest-playwright; a missing browser is a CI failure; xdist-parallel per test | pytest-playwright verified compatible & working under xdist; Code Examples (missing-browser fail/skip pattern) |
| TST-12 | Every source-text/comment/`.planning`/style.css-as-text check rewritten as behaviour/DOM/computed-style, or deleted with a reason; ledger records it | Source-Text Inventory (counts, classified examples, line numbers) |
| TST-13 | Permission tests skip under euid 0; every path inside `tmp_path` | Root-Safety Inventory (exact `chmod`/`anomaly_active` sites, live-reproduced host-filesystem side effect) |
| TST-14 | `run_all_tests.py`/hand lists/`EXPECTED_CHECK_COUNT` retired; `run-all-tests.sh` stays thin | Architecture Patterns (shim retirement), CLAUDE.md stack-row note |
| TST-15 | Closing parity: all 2018 pre-migration checks accounted for; coverage ≥ pre-migration | Migration Ledger & Baseline Capture (live 1250-check baseline, discrepancy note), Coverage section |
</phase_requirements>

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.14 | Production/CI parity (D-A4) | ✗ (this sandbox) | 3.11.15 (`server/.venv`, `/usr/bin/python3.10/.11/.12/.13`, no 3.14) | Research/baseline capture done on 3.11.15; actual migration plans should still target 3.14 semantics — nothing found in this research is 3.14-specific, but re-run `33-ledger-check.py --capture` on a 3.14 interpreter if one becomes available before finalizing the ledger, since Phase 32's own verified numbers were captured on 3.14.0rc2 |
| `uv` (dependency locking) | `scripts/lock-deps.sh` | ✓ | 0.8.17 | — |
| pytest / pytest-xdist / pytest-cov / pytest-socket | already pinned, installed in `server/.venv` | ✓ | 9.1.1 / 3.8.0 / 7.1.0 / 0.8.1 | — |
| `playwright` (Python package) | browser harnesses | ✓ | 1.63.0 (already in `server/.venv`) | — |
| `pytest-playwright` | TST-11 | ✗ (not yet installed anywhere) | 0.9.0 latest on PyPI, verified compatible | Install via `server/requirements-dev.in` + `scripts/lock-deps.sh` (proven to work in this sandbox) |
| Chromium headless-shell binary matching `playwright==1.63.0` (revision 1243) | browser harnesses/pytest-playwright `page` fixture | ✗ at `/opt/pw-browsers` (holds **r1194**, stale) | r1243 expected | `PLAYWRIGHT_BROWSERS_PATH=<fresh dir> playwright install --only-shell chromium` downloads r1243 successfully through the sandbox's proxy (verified, 114 MiB); CI is unaffected — GitHub Actions runs `playwright install --with-deps --only-shell chromium` fresh every time key changes, so it will fetch r1243 itself once `requirements-dev.txt` is regenerated. **Flag for the human/planner:** if this sandbox's `/opt/pw-browsers` is reused for the actual execution phase, either point `PLAYWRIGHT_BROWSERS_PATH` at a writable scratch dir and reinstall, or accept the existing shim's `SKIP` behaviour until then |
| `slopcheck` | Package Legitimacy Gate | ✓ (installed this session) | 0.6.1 | — |

**Missing dependencies with no fallback:** none — every gap above has a working fallback proven live in this session.

**Missing dependencies with fallback:** Python 3.14, pytest-playwright, matching Chromium revision — see table.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest-playwright | 0.9.0 | pytest fixtures (`page`, `browser`, `context`) driving real Chromium for TST-11 | Official Playwright-org package for pytest integration; confirmed via `playwright.dev/python/docs/intro` [CITED: playwright.dev]; requires `playwright>=1.18`, `pytest<10,>=6.2.4`, Python `>=3.10` — all satisfied by the pinned `playwright==1.63.0` / `pytest==9.1.1` / Python 3.14 [VERIFIED: PyPI JSON API + live install in this sandbox] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| tinycss2 | 1.5.1 | Optional: real CSS tokenizer for structural stylesheet checks (TST-12's "parse the served stylesheet structurally" option) | Only if the hand-written stdlib tokenizer (see Code Examples) proves too fragile for a specific check's needs — CONTEXT.md's own phrasing ("small stdlib tokenizer") suggests preferring no new dependency; keep this as a fallback, not the default [CITED: pypi.org/project/tinycss2, requires_python >=3.10] |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-written stdlib CSS declaration extractor (regex over comment-stripped served CSS, same technique `_css_without_comments()` already uses today, just re-sourced from HTTP instead of `open()`) | `tinycss2` (real parser) | The existing harnesses' own `.index("{")`/`.index("}")` substring slicing is fragile (breaks on nested braces, `@media`, minification) but every current check only needs ONE declaration block per selector — a stdlib regex tokenizer that finds `selector { ... }` blocks and splits `prop: value;` pairs covers 100% of observed usage without a new dependency. `tinycss2` is safer for anything more complex (e.g. `@media` queries, comma-separated selectors) if a future check needs it |
| Server-side CSS text parsing entirely | Move CSS/contrast checks into the browser harnesses as computed-style assertions (`test_browser_ux_helpers.py`'s own `_computed_paint`/`_resolved_property`/`_set_ui_theme` helpers, already proven) | Computed-style checks are strictly stronger (they catch cascade/specificity bugs a raw-text parse cannot) but require a live browser — not available to the 6 non-browser harnesses without adding a Playwright dependency to files that don't otherwise need one. Recommendation: migrate contrast/computed-color checks that are ALREADY conceptually about rendering (i.e. currently in `test_contrast_check.py`, which does WCAG math on hex values pulled from `companion/contrast_check.py`, not from style.css text) unchanged; migrate the ~40-47 raw `style.css`-as-text reads in `test_status_pages.py`/`test_companion_app.py`/`test_view_pages.py` to the served-stylesheet structural parser (not to the browser, since those 3 files don't otherwise need Playwright) |

**Installation:**
```bash
# server/requirements-dev.in gains one line:
echo "pytest-playwright==0.9.0" >> server/requirements-dev.in
scripts/lock-deps.sh   # regenerates both hash-locked .txt files; playwright stays 1.63.0
```

**Version verification:** confirmed live in this sandbox —
```
$ pip index versions pytest-playwright   # 0.9.0 (latest)
$ curl -s https://pypi.org/pypi/pytest-playwright/0.9.0/json | jq .info.requires_dist
["playwright>=1.18", "pytest<10.0.0,>=6.2.4", "pytest-base-url<3.0.0,>=1.0.0", "python-slugify<9.0.0,>=6.0.0"]
$ uv pip compile --generate-hashes --python-version 3.14 --python-platform x86_64-manylinux_2_28 \
    server/requirements-dev.in -o /tmp/scratch-requirements-dev.txt
# succeeded; playwright==1.63.0 unchanged; new transitive pins: pytest-base-url==2.1.0,
# python-slugify==8.0.4, text-unidecode==1.3, typing-extensions==4.16.0 (typing-extensions
# was likely already present transitively; slugify chain is new)
```

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|--------------|-----------|-------------|
| pytest-playwright | PyPI | Official Playwright-org package, many years old | high (millions/mo transitively via Playwright's own ecosystem) | github.com/microsoft/playwright-python | [OK] | Approved |
| pytest-base-url | PyPI | established (pytest-dev ecosystem package) | moderate | github.com/pytest-dev/pytest-base-url | [OK] | Approved (transitive of pytest-playwright) |
| python-slugify | PyPI | established | high | github.com/un33k/python-slugify | [OK] — slopcheck noted "Name starts with 'python-' — classic LLM naming pattern... but package is established" | Approved (transitive of pytest-playwright) |
| text-unidecode | PyPI | established | high | github.com/kmike/text-unidecode | [OK] | Approved (transitive of python-slugify) |
| tinycss2 (optional, not yet added) | PyPI | established (part of the `cssutils`/`weasyprint`/`courlan` ecosystem lineage) | high | github.com/Kozea/tinycss2 | [OK] | Approved if the planner chooses this path over the stdlib tokenizer; not required |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.

All packages above ran through `slopcheck install <pkg> --json`-equivalent (`slopcheck` 0.6.1
does not support `--json`; ran without it, output parsed manually) in this session and scored
`[OK]`. `pytest-playwright`'s name/purpose was independently confirmed against official
documentation (`playwright.dev/python/docs/intro`), satisfying the `[VERIFIED]` bar (official
docs + slopcheck OK), not merely `[ASSUMED]`.

## Architecture Patterns

### Recommended Project Structure

No new top-level directories — CONTEXT.md's "Test location" decision keeps migrated tests in
`companion/`. A new `companion/conftest.py` (does not exist today) is where the shared
app-server fixture lives:

```
companion/
├── conftest.py                    # NEW — shared app_server / page-in-app fixtures
├── test_companion_app.py          # migrate + likely split (12.3k lines)
├── test_config_page.py            # migrate + likely split (13.6k lines)
├── test_status_pages.py           # migrate + likely split (16.3k lines)
├── test_view_pages.py             # migrate (9.4k lines, still large — split optional)
├── test_i18n.py                   # migrate (1.3k lines, straightforward)
├── test_contrast_check.py         # migrate (0.5k lines, pure unit tests, no server)
├── test_browser_ux.py             # migrate to pytest-playwright (9.6k lines)
├── test_browser_ux_health_drawings.py   # migrate to pytest-playwright (2.1k lines)
├── test_browser_ux_quiet_wake.py  # migrate to pytest-playwright (2.1k lines)
├── test_browser_ux_helpers.py     # becomes a shared pytest helper module (not collected directly)
└── test_legacy_harness_shim.py    # DELETED once the list above is empty (TST-14)
```

### System Architecture Diagram

```
pytest -n auto (xdist controller)
        │
        ├─ worker gw0..gwN (one process each)
        │      │
        │      ├─ companion/conftest.py: app_server fixture
        │      │      → subprocess.Popen(companion/app.py, env=child_env(fake_providers=...))
        │      │      → poll until 127.0.0.1:<port> accepts a connection
        │      │      → yield Harness-like object (base_url, tmp_path state dir)
        │      │      → teardown: terminate() / wait() / kill() on timeout
        │      │
        │      ├─ [non-browser tests] http.client / urllib request → app_server.base_url()
        │      │      → assert on status code / Set-Cookie / parsed DOM (html.parser)
        │      │      → assert on SERVED /static/style.css bytes (structural parse), never
        │      │        the on-disk file
        │      │
        │      └─ [browser tests] pytest-playwright `browser` fixture (session-scoped,
        │             one Chromium instance per xdist worker) → `page` fixture (function-
        │             scoped) → page.goto(app_server.base_url() + route)
        │             → real DOM/CSS-cascade/JS assertions via page.evaluate()/
        │               get_by_role()/expect() — the ONLY place computed-style checks belong
        │
        └─ pytest-cov: patch=["subprocess"] + sigterm=true (Phase 32 infra, unchanged)
               → measures companion/app.py inside the child, combined at session end
```

### Pattern 1: The 4 duplicated `Harness`/`http_request`/`_NoRedirectHandler` triads

**What:** `test_companion_app.py`, `test_config_page.py`, `test_status_pages.py`, and
`test_view_pages.py` each define their OWN byte-for-byte-near-identical `Harness` class
(subprocess lifecycle: pick free port, `subprocess.Popen(companion/app.py, ...)`, poll until
listening, `terminate()`/`kill()` teardown, `cleanup()` via `shutil.rmtree`), their OWN
`http_request()` function (`urllib.request` wrapper using a shared `_NoRedirectHandler`), and
their OWN `_NoRedirectHandler(urllib.request.HTTPRedirectHandler)` class. `test_i18n.py`
imports (does not redefine) `http_request`/`_InProcessHarness` from `test_companion_app` via
`from companion import test_companion_app as _tca`. The 3 browser harnesses import (do not
redefine) `Harness`/`TEST_PASSWORD` from `test_companion_app`.

**Confirmed structural drift between the 4 copies** [VERIFIED: direct read, all 4 files]:
only `test_companion_app.py`'s `Harness.start()` was updated by Phase 32 plan 32-11 to call
`child_env(dict(os.environ), fake_providers=FakeProviders(), state_dir=self.tmpdir)` and
carries a `fake_provider_calls()` helper and an `extra_args=()` constructor parameter. The
other 3 copies (`test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`) still do
`env = dict(os.environ)` directly — **this is not a live bug**: because each of these files
is itself launched as a subprocess by `companion/test_legacy_harness_shim.py` with
`env=child_env()`, the `SKYPANE_TEST_NO_NETWORK=1` var is already present in `os.environ`
when the harness's own `Harness.start()` copies it forward to `companion/app.py`'s env — the
guard is inherited transitively. None of these 3 files exercise `/poll-now`'s real network
path, so they were correctly left without `FakeProviders()`, per 32-11-PLAN.md's own comment
("a harness that reaches a provider without asking for the fake fails loudly instead of
silently succeeding"). The new shared fixture in `companion/conftest.py` should offer BOTH
behaviours (guard always on, `fake_providers` opt-in per test) rather than assuming every
test needs the fake.

**Prefixes for the 4 `tempfile.mkdtemp()` calls** (cosmetic only, useful for the fixture's own
diagnostics): `"skypane-companion-"`, `"skypane-config-page-"`,
`"skypane-status-pages-e2e-"`, `"skypane-view-pages-e2e-"`.

**A 5th, distinct pattern — `_InProcessHarness`** [VERIFIED]: `test_companion_app.py` also
defines `class _InProcessHarness` (a real `ThreadingHTTPServer` running `companion/app.py`'s
own handler class **inside the pytest process**, not a subprocess) — used by ~24 calendar/
`/poll-now`-adjacent checks in `test_companion_app.py` and re-used by `test_i18n.py`
(`_tca._InProcessHarness()`). The shared fixture design should offer this as a second,
lighter-weight variant (no subprocess startup latency) for checks that only need to observe
in-process state (e.g. call logs, direct Python object inspection) rather than exercise the
real subprocess-isolation boundary.

**When to use:** the new `companion/conftest.py` fixture(s) should collapse ALL FIVE of the
above (4× subprocess `Harness`, 1× `_InProcessHarness`) into one or two fixtures. A
reasonable design (Claude's discretion per CONTEXT.md):

```python
# companion/conftest.py (sketch — not verified against a real branch, illustrative only)
import os, socket, subprocess, sys, time
import pytest
from skypane_test_support import child_env, FakeProviders

APP_PATH = os.path.join(os.path.dirname(__file__), "app.py")
TEST_PASSWORD = "companion-test-password-please-ignore"
STARTUP_DEADLINE_S = 10.0

class AppServer:
    def __init__(self, base_url, state_dir, fake_providers=None):
        self.base_url = base_url
        self.state_dir = state_dir
        self.fake_providers = fake_providers

@pytest.fixture
def app_server(tmp_path, monkeypatch):
    """Function-scoped by default (simplicity over speed — Phase 32's own
    15 server-side migrations mostly kept 1:1 subprocess-per-test too;
    promote to module scope with a reset-between-tests helper only if
    profiling shows the startup cost matters under xdist)."""
    port = _pick_free_port()
    fake = FakeProviders()
    env = child_env(dict(os.environ), fake_providers=fake, state_dir=str(tmp_path))
    env["SKYPANE_COMPANION_PASSWORD"] = TEST_PASSWORD  # actual var name: auth.PASSWORD_ENV_VAR
    proc = subprocess.Popen(
        [sys.executable, APP_PATH, "--port", str(port), "--state-dir", str(tmp_path)],
        env=env, start_new_session=True,
    )
    _wait_until_listening(port, proc, STARTUP_DEADLINE_S)
    try:
        yield AppServer("http://127.0.0.1:%d" % port, str(tmp_path), fake)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
```

### Pattern 2: Missing-browser — CI hard-fail, local visible skip (TST-11)

**Verified live in this sandbox:** pytest-playwright's own `browser`/`page` fixtures, used
un-wrapped, already fix WR-04's defect class structurally — a missing/mismatched browser
executable raises inside fixture setup and pytest reports it as an **ERROR** (not a silent
pass), for every test that requests the fixture:

```
$ PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers python -m pytest test_pw.py -v
E    playwright._impl._errors.Error: BrowserType.launch: Executable doesn't exist at ...
ERROR test_pw.py::test_basic[chromium] - playwright._impl._errors.Error: Brow...
=========================== 1 error in 0.45s ===========================
```

This alone satisfies "never a silent pass." To additionally satisfy "locally a VISIBLE SKIP,
in CI a hard failure" (rather than an opaque ERROR everywhere), override the `browser` fixture
in `companion/conftest.py`:

```python
import os
import pytest

def _browser_required():
    return (os.environ.get("SKYPANE_REQUIRE_BROWSER") == "1"
            or os.environ.get("CI", "").lower() == "true")

@pytest.fixture(scope="session")
def browser(playwright):
    try:
        b = playwright.chromium.launch()
    except Exception as exc:
        if _browser_required():
            pytest.fail("Chromium could not launch (SKYPANE_REQUIRE_BROWSER=1): %r" % (exc,))
        pytest.skip("Chromium could not launch: %r — run `playwright install --only-shell chromium`" % (exc,))
    yield b
    b.close()
```
(Fixture-overriding is pytest-playwright's documented mechanism — the plugin's own
`browser` fixture is a normal pytest fixture and can be shadowed by a same-named one in a
`conftest.py` at a narrower scope, exactly like any other pytest fixture override.)

### Pattern 3: xdist + pytest-playwright — one browser instance per worker

**Verified live:** ran 5 tests across 4 xdist workers; each worker (`gw0`..`gw3`) launched
and reused its OWN Chromium instance (pytest-playwright's `browser` fixture defaults to
session scope, and "session" means "this xdist worker's own process session" since each
worker is a separate Python process):
```
created: 4/4 workers
[gw2] PASSED test_pw2.py::test_b[chromium]
[gw1] PASSED test_pw2.py::test_a[chromium]
[gw3] PASSED test_pw2.py::test_c[chromium]
[gw0] PASSED test_pw.py::test_basic[chromium]
[gw0] PASSED test_pw2.py::test_d[chromium]
============================== 5 passed in 1.38s ==============================
```
This matches CONTEXT.md's discretion note ("whether browser tests share one browser per
worker — pytest-playwright's default session-scoped browser") — the default already does
this; no custom fixture needed for that part.

**Default browser/channel resolution — verified important detail:** with NO
`--browser-channel` flag, pytest-playwright's default `page`/`browser` fixtures launch
Chromium headless by default, and (on this playwright version) headless-by-default resolves
to the **headless-shell** binary automatically — the exact artifact `playwright install
--only-shell chromium` downloads. CI's existing install step therefore needs **no change**
beyond what Phase 32 already does; do not add `--browser-channel=chromium-headless-shell` —
it is unnecessary and (verified) actually tries to launch a DIFFERENT revision path
(`chromium-1243/chrome-linux/chrome`, the full browser, not the shell) when passed explicitly
as `--browser-channel chromium`.

### Pattern 4: `test_browser_ux_helpers.py`'s already-correct computed-style precedent

**What it provides** (41 functions, verified via `grep '^def '`): `seed_state_dir`,
`_login(page, base_url)`, `_no_js_page` (scripts-blocked rendering), `_click_control`,
`_guard_armed`, `_wait_for_bar`/`_wait_for_bar_hidden`/`_bar_text`/`_save_via_bar`,
`_commit_field`, `_set_ui_theme`, **`_computed_paint(page, selector, props=...)`**,
`_assert_no_page_overflow`, `_persist_without_js`/`_upload_without_js`/`_persist_once`,
`_operate_with_keyboard`, `_hit_area`/`_assert_hit_target`, `_drop_files`/`_drop_zone_paint`,
`_assert_js_gate`, `_in_both_themes`, `_display_page_height`,
`_canonical_surface_value`/`_assert_surfaces_agree`, **`_resolved_property(page, selector,
property_name, where)`**, quiet-hours arc/caption geometry helpers.

**Use this as the reference implementation** for TST-12's "browser computed-style" migration
path: every comment in this file that mentions `style.css` (9 occurrences, all verified to be
PROSE explaining WHY a check reads computed style instead of the file — never an actual
`open()` call) demonstrates the target end-state other harnesses should converge toward.
`_computed_paint`/`_resolved_property` are the exact functions a migrated CSS-token check
should call instead of `css_source.index(".some-selector {")`.

### Anti-Patterns to Avoid

- **Re-reading `style.css`/`*.js` from disk with `open()` inside a migrated pytest test:**
  the served copy (via `app_server.base_url() + "/static/style.css"`) is the thing under
  test; the on-disk file is an implementation detail this phase must stop asserting on.
- **A self-referential "ledger" check that `open()`s the TEST FILE ITSELF to verify a
  plan-history bookkeeping table** — found in 2 files (`test_config_page.py:1658`,
  `test_browser_ux.py` — both implement `_every_aspect_repin_ledger_row_names_a_live_or_owed_replacement()`,
  reading `os.path.join(HERE, "test_{file}.py")` and regex-searching for `def <name>(`
  patterns tied to specific plan IDs like `"30-05"`/`"30-06"`). This is textbook TST-12
  deletion material: it is pure plan-history bookkeeping with no user-facing behaviour, and
  it literally does what TST-12 forbids (`open()`s a `.py` file to grep text). Delete with
  reason: "self-referential CFG-85 aspect-repin ledger; asserts internal plan-tracking
  metadata, not behaviour; contradicts TST-12's no-source-grep rule."
- **`--browser-channel chromium`** (explicit) when the default (no flag) already resolves to
  the correct headless-shell binary that matches the `--only-shell` install — passing the
  flag explicitly changes which binary Playwright looks for (verified: it looked for the
  FULL Chromium build's revision path when the flag was given).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Detecting "browser missing → fail in CI, skip locally" | A custom `try/except launch(): print SKIP` wrapper duplicated per browser harness (today's pattern, 3 copies, the exact WR-04 defect) | pytest-playwright's real `browser`/`page` fixtures + one small `conftest.py` override (Pattern 2 above) | The hand-rolled version silently turns ~90 checks into a vacuous pass on any launch failure (missing shell, missing OS deps, sandbox/permission issue) — proven exploitable this exact phase (this sandbox's own stale `/opt/pw-browsers` cache would have silently "passed" 95 checks under the old pattern) |
| Subprocess app-server lifecycle (free port, poll-until-listening, terminate/kill teardown) | A 5th/6th hand-copied `Harness` class | The ONE shared `companion/conftest.py` fixture (Pattern 1) | Exactly the defect this phase's TST-10 exists to fix — 4 copies already drifted (fake-provider support present in only 1 of 4) |
| CSS declaration extraction | A full custom CSS engine, or continuing the existing `css_source.index("{")...index("}")` substring slicing (already proven fragile: no `@media`/nesting/comment-inside-value handling) | A minimal stdlib tokenizer (regex-based, ~30 lines, operating on the SERVED stylesheet) for the common case; `tinycss2` (a real, small, pure-Python parser) if a check's needs exceed that | Hand-rolled brace-counting breaks silently on any CSS feature the original author didn't anticipate; a real (if small) parser or a documented-scope tokenizer is auditable |
| WCAG contrast math | Re-deriving contrast ratio formulas | `companion/contrast_check.py` (already exists, already imported by `test_contrast_check.py`) — this file needs NO source-text changes, it does pure numeric assertions on values imported as Python objects, not text | Already correct; do not touch |

**Key insight:** every hand-rolled pattern this phase must retire (`Harness` ×4,
`http_request` ×4, `_NoRedirectHandler` ×4, the browser-skip try/except ×3, the CSS
substring-slice idiom ×dozens) exists because the original harness-per-file design had no
shared-fixture mechanism. pytest's fixture system is the tool this problem has always needed;
Phase 32 already proved the pattern for `server/`, this phase just extends it to `companion/`.

## Quantitative Harness Inventory

**Method:** every row below was produced by actually running
`server/.venv/bin/python3 companion/<file>.py` standalone in this sandbox (git commit
`6d4d741`, branch `claude/phase-33`, euid 0/root, Python 3.11.15 — **not** 3.14; see
Environment Availability) and reading the real PASS/FAIL transcript and wall-clock time, per
this phase's own required baseline-capture method (never grep source for `check(` call
counts — some are loop-emitted). Full transcripts are NOT included in this document (they are
the actual future `33-BASELINE/*.txt` content, thousands of lines each) but were captured to
disk this session and can be regenerated identically by the same command.

| Harness | Lines | Launches `app.py`? | PASS | FAIL (root) | Total | Wall time | Structure |
|---|---:|---|---:|---:|---:|---:|---|
| `test_contrast_check.py` | 524 | No — pure import of `companion/contrast_check.py`, numeric WCAG math | 49 | 0 | 49 | <1s | Flat `check(name, fn)` list, no loops, no server |
| `test_i18n.py` | 1,289 | Partial — most checks are AST/regex source scans of `companion/i18n_fr.py`/`static/*.js`; a handful use `_tca._InProcessHarness()` (imported, not subprocess) | 24 | 0 | 24 | <1s | `check(name, fn)`; summary line is `"%d/%d checks pass"` — **no name prefix**, unlike all 8 siblings (`"%s: %d/%d checks pass"`) — the ledger tool's `SUMMARY_RE` must be widened for this one file |
| `test_view_pages.py` | 9,353 | Yes — own `Harness` copy | 169 | 0 | 169 | 1.7s | `check(name, fn)`, several checks group into single fn bodies per route |
| `test_config_page.py` | 13,620 | Yes — own `Harness` copy | 276 | 0 | 276 | 1.3s | Same idiom; contains the `_ASPECT_REPIN_LEDGER` self-referential source-read pattern (delete candidate) |
| `test_companion_app.py` | 12,267 | Yes — own `Harness` copy (the ONLY one with `child_env(fake_providers=...)`, per Phase 32 plan 32-11) + `_InProcessHarness` (5 checks group around calendar/poll-now) | 318 | 2 | 320 | 26.6s | Largest check-density-per-line; 2 FAILs are the documented root-sandbox WR-11 `chmod` artifacts (lines ~10336, ~10386) |
| `test_status_pages.py` | 16,279 | Yes — own `Harness` copy | 316 | 1 | 317 | 14.1s | Largest file; 1 FAIL is the live-reproduced `anomaly_active("/nonexistent/...")` root-mkdir artifact (line 8201, confirmed unchanged from audit) |
| `test_browser_ux_health_drawings.py` | 2,092 | Yes — imports `Harness` from `test_companion_app` + real Chromium | 11 | 0 | 11 | 21.6s (needs fresh Chromium r1243) | `check(name, fn)`; `sync_playwright()` block wraps whole `main()` |
| `test_browser_ux_quiet_wake.py` | 2,073 | Yes — same pattern | 9 | 0 | 9 | 26.8s (needs fresh Chromium r1243) | Same |
| `test_browser_ux.py` | 9,595 | Yes — same pattern, largest browser file | 75 | 0 | 75 | 201.7s (3m22s; needs fresh Chromium r1243) | ONE `Harness()` + ONE `sync_playwright()` browser shared across ALL 75 checks — matches CONTEXT.md's "one app server per module" discretion note exactly |
| `test_browser_ux_helpers.py` | 2,712 | N/A — shared helper module, not itself runnable | — | — | — | — | 41 helper functions (see Pattern 4) |
| **TOTAL (9 runnable harnesses)** | **69,804** (+2,712 helpers) | | **1,247** | **3** | **1,250** | ~296s serial, single-threaded, no xdist | |

**Companion legacy-harness shim's own contract** [VERIFIED against `companion/test_legacy_harness_shim.py`]: `LEGACY_COMPANION_HARNESSES` (9 entries) must exactly match `os.listdir("companion/")`'s `test_*.py` files minus the shim itself and minus `test_browser_ux_helpers.py` — `test_legacy_harness_list_matches_disk()` already enforces this and will need updating (shrinking the list) after every migration plan in the same commit, per CONTEXT.md's transition rule.

## Migration Ledger & Baseline Capture

**Reuse, don't rewrite, `32-ledger-check.py`.** Its architecture (parse a baseline transcript
→ parse a ledger fragment's markdown table → `validate_fragment()` pure-function matching →
`--assemble` concatenation) is entirely file-list-driven (`HARNESSES = [...]`,
`harness_key()`, `PHASE_DIR`/`BASELINE_DIR`/`LEDGER_DIR` derived from `__file__`). Copy it to
`33-ledger-check.py` in this phase's directory and change exactly:
1. `HARNESSES` → the 9 companion files (see table above, same order is fine).
2. The docstring's `"15 server-side harnesses"` references → 9 / companion.
3. **`SUMMARY_RE`** currently requires a `"<name>: "` prefix
   (`r"^(?P<name>.+): (?P<passed>\d+)/(?P<total>\d+) checks pass\s*$"`). `test_i18n.py`'s own
   summary line is `"24/24 checks pass"` with **no prefix at all** — confirmed live this
   session (`cat -A` shows the line ends `24/24 checks pass$`, no colon anywhere in it). The
   regex must be widened to make the `name: ` group optional, e.g.
   `r"^(?:(?P<name>.+): )?(?P<passed>\d+)/(?P<total>\d+) checks pass\s*$"`, or the `--capture`
   step will record `total=None` for this one harness (the row-count-based validation in
   `validate_fragment()` would likely still work since it counts PASS/FAIL lines directly,
   but the INDEX.md summary table's "Total" column would be blank/wrong for this file — fix
   the regex rather than rely on that).
4. Nothing else needs changing — `parse_baseline`, `label_matches`, `parse_fragment_rows`,
   `validate_fragment`, `escape_label` are all format-driven and already proven correct
   against the exact `check()`/`EXPECTED_CHECK_COUNT` idiom every companion harness shares
   with the 15 server-side ones Phase 32 already migrated.

**Capture command** (same shape as Phase 32's, adjusted paths):
```bash
for f in companion/test_contrast_check.py companion/test_i18n.py companion/test_view_pages.py \
         companion/test_config_page.py companion/test_companion_app.py companion/test_status_pages.py; do
    server/.venv/bin/python3 "$f" > "33-BASELINE/$(basename "$f" .py).txt" 2>&1
done
# Browser harnesses need a REAL Chromium — either fix /opt/pw-browsers' stale cache or point
# PLAYWRIGHT_BROWSERS_PATH at a scratch dir first (see Environment Availability):
for f in companion/test_browser_ux.py companion/test_browser_ux_health_drawings.py \
         companion/test_browser_ux_quiet_wake.py; do
    PLAYWRIGHT_BROWSERS_PATH=<working-cache-dir> server/.venv/bin/python3 "$f" \
        > "33-BASELINE/$(basename "$f" .py).txt" 2>&1
done
```

**Closing-parity discrepancy, found live, must be recorded in `33-MIGRATION-LEDGER.md`'s
closing note:** CONTEXT.md's own math is 2018 − 769 = **1249** expected companion checks. This
research's live capture totals **1250** (1247 PASS + 3 root-only FAIL, all 9 files summed —
see table above). This is a real +1 discrepancy, not a counting error on my part (each
per-file total was cross-checked against that file's own printed `"N/M checks pass"` line AND
an independent `grep -c "^PASS "`/`grep -c "^FAIL "`). Likely explanation per CONTEXT.md's own
anticipated cause: Phase 34 or the Phase 32-continuation commits landed on `main` after the
2026-09-23 audit's baseline was measured (`git log` shows Phase 34's full 15-plan firmware
work and Phase 32's plans 32-11..32-15 both landed AFTER the audit commit) — one of those
likely added exactly one companion check. **Recommendation for the plan that captures
`33-BASELINE/`:** run `git log --oneline -- companion/test_*.py` since the audit's commit
(`2808f8a`) to find the exact commit that added the +1 check, and cite it by hash/plan-id in
the ledger's closing note rather than leaving the discrepancy unexplained.

## Root-Safety Inventory

**Exhaustive** (all `os.chmod` and hardcoded-nonexistent-path sites across all 9 harnesses,
verified via `grep -n "os.chmod\|nonexistent" companion/test_*.py` then read in context):

| File | Line(s) | Pattern | Root-unsafe? | Fix |
|---|---|---|---|---|
| `test_companion_app.py` | 10336, 10344 | `os.chmod(manual_harness.tmpdir, 0o500)` / restore `0o700` around a POST that should fail on an unwritable state dir (WR-11: `add_entry()` read-only test) | Yes — root ignores the permission bit, write succeeds, check FAILs (confirmed live: this is 1 of the 2 FAILs this session) | `@requires_non_root` (already exists in `test-support/skypane_test_support.py`, reused verbatim, Phase 32 precedent at `server/test_manual_resolutions.py`); `manual_harness.tmpdir` → `tmp_path` |
| `test_companion_app.py` | 10386, 10392 | Same pattern, `delete_entry()`'s WR-11 mirror case | Yes — the 2nd FAIL this session | Same fix |
| `test_status_pages.py` | 8201 | `health_page.anomaly_active("/nonexistent/definitely-not-here")` — **not a chmod check, a literal nonexistent path fed to a function that calls `server/history_db.connect()` → `os.makedirs(state_dir, exist_ok=True)`** | Yes, and worse than a permission-bit no-op: **this line creates real directories on the host filesystem** (`/nonexistent/definitely-not-here`), confirmed live this session — `ls -la /nonexistent` after running this harness shows `drwxr-xr-x definitely-not-here` freshly created at test time, owned by root. This is TST-13's success-criterion-4 violation in its most literal form: a test writing OUTSIDE `tmp_path`, onto the host `/` itself | Replace the literal `"/nonexistent/definitely-not-here"` with a path guaranteed absent INSIDE `tmp_path` (e.g. `tmp_path / "does-not-exist" / "nested"`), so any accidental `os.makedirs()` side effect lands inside pytest's own auto-cleaned temp tree instead of the host root. The check's actual assertion (`anomaly_active()` returns `False`/doesn't raise for a nonexistent dir) is unaffected by using a `tmp_path`-scoped nonexistent path instead |
| `test_config_page.py` | 6078-6080 | `nonexistent = os.path.join(tmpdir, "does-not-exist")` — **already correctly scoped inside a tmpdir**, not a host-root path | No — already safe, just needs `tmpdir` → `tmp_path` | No behavioural change, only fixture-based cleanup |
| `test_companion_app.py` | 3873, 3878, 10865 | `"/nonexistent-state-dir-fixture"`, `"/nonexistent"`, `"/nonexistent/no-such-geofence.json"` passed as arguments to `_resolve_flash_text()` / `Harness(extra_args=["--geofence", ...])` | Needs verification per call site whether the receiving function ever calls `os.makedirs`/`open(..., "w")` on the path (unlike `anomaly_active`, `_resolve_flash_text` looked like pure string handling — worth a explicit check during migration, not confirmed clean or unclean in this research pass) | Same general fix: prefer a `tmp_path`-scoped "guaranteed absent" path over a literal host-root string, even when the current function is believed to only read |

**Live-reproduced host-filesystem side effect (this session):**
```
$ server/.venv/bin/python3 companion/test_status_pages.py   # (ran earlier for baseline capture)
$ ls -la /nonexistent
drwxr-xr-x  2 root root 4096 <today>  definitely-not-here
```
I attempted to clean this up (`rm -rf /nonexistent`) and the removal was blocked by this
session's own safety tooling ("critical system directory... requires explicit approval").
**The directory `/nonexistent/definitely-not-here` is still present on this host's
filesystem** as a direct, unforced artifact of running the CURRENT (unmigrated) test suite —
flag this to the developer; it is empty and harmless but should be removed manually
(`rm -rf /nonexistent`) once confirmed nothing else on the host uses that path.

**Root-run behavior confirmed:** running the full companion suite as root (as this sandbox
always is) surfaces exactly 3 FAILs total, matching Phase 32's own baseline notes and
32-REVIEW IN-05 finding precisely ("test_companion_app reported 318/320... test_status_pages
reported 316/317"). No other harness (config_page, view_pages, i18n, contrast_check, or any
of the 3 browser harnesses) has a root-sensitivity issue — they were all clean (276/276,
169/169, 24/24, 49/49, 75/75, 11/11, 9/9) even under root in this session.

## Coverage

Phase 32 already measured and gated companion coverage: `[tool.coverage.report] fail_under =
93` in `pyproject.toml`, derived from a full-suite run at 93.35% (companion `app.py` 92%,
`stub-server/byos_server.py` 94%, `make_test_panel.py` 98%) — documented in the file's own
derivation comment and independently confirmed in `32-VERIFICATION.md`'s Behavioral
Spot-Checks table [CITED: pyproject.toml `[tool.coverage.report]` comment, 32-VERIFICATION.md
line "Full run (nobody, clean 3.14 venv): app.py 92%, byos_server.py 94%,
make_test_panel.py 98%, TOTAL 93.35%"]. This research did not re-run the full-suite coverage
measurement (would require running all 9 companion harnesses PLUS all 15 already-migrated
server/stub-server tests together under `pytest --cov`, ~5+ minutes, not obviously
information-bearing before any migration has happened — the pre-migration figure is already
recorded). **Recommendation:** the phase's closing plan re-measures coverage exactly as
32-13/32-15 did (full `./scripts/run-all-tests.sh` run, non-root, on the actual CI Python
version if available) and raises `fail_under` to the new measured floor if migration happens
to touch previously-unreached code paths (e.g. rewriting a source-text check into an HTTP
behaviour check may exercise a response-handling branch the old check never reached).

## Wall-Clock / xdist Parallelism

Serial (no `-n auto`) wall time measured this session, summed: **~296 seconds** for all 9
harnesses run one after another (contrast_check + i18n <1s each, view_pages 1.7s, config_page
1.3s, companion_app 26.6s, status_pages 14.1s, browser_ux_health_drawings 21.6s,
browser_ux_quiet_wake 26.8s, browser_ux 201.7s). The audit's own measured baseline says the
FULL pre-Phase-32 suite (all 24 original harnesses, server + companion) took **~221s wall**
under the OLD serial-per-file runner — meaning `test_browser_ux.py` alone (202s in this
session) already accounted for the vast majority of that 221s figure, consistent with the
audit's own note ("`test_browser_ux.py` alone sets the wall time"). Splitting
`test_browser_ux.py`'s 75 checks into individually-collected pytest test functions and running
them under `-n auto` should reduce this dramatically, since xdist can distribute the 75 tests
across all available workers instead of running them serially inside one Python process's
`sync_playwright()` block — this is the single largest wall-clock win available in this phase,
and CONTEXT.md's "parallelised per test with xdist (no single monolithic browser test)"
requirement directly targets it.

**Caution for the shared browser-fixture design:** today's ONE-Harness-ONE-browser-for-75-checks
pattern means all 75 checks currently share ONE `companion/app.py` process's mutable state
(seeded once via `seed_state_dir(harness.tmpdir)` at the top of `main()`). Splitting into
independent pytest tests distributed across xdist workers means each worker needs its OWN
seeded app-server instance (module- or session-scoped per worker, not per individual test, to
avoid the startup-cost regression CONTEXT.md warns about) — CONTEXT.md's own discretion note
("one app server per module... tests must not leak state in a way that makes xdist
distribution order-dependent") is directly about this exact tradeoff.

## Common Pitfalls

### Pitfall 1: Assuming `open("style.css")` and "reading the served stylesheet" are equivalent
**What goes wrong:** A naive migration keeps `open(os.path.join(HERE, "static", "style.css"))`
but just moves the assertion logic around — TST-12 is not satisfied, because the check still
depends on the FILE on disk rather than what the running app actually serves at
`STYLE_ROUTE = "/static/style.css"` (`companion/app.py:156`).
**Why it happens:** every one of the ~40-47 existing CSS-text checks per large file already
does exactly this, so it is the path of least resistance during migration.
**How to avoid:** fetch via the app-server fixture's HTTP client (`app_server.base_url() +
"/static/style.css"`) and parse THAT response body.
**Warning signs:** a migrated test still imports `HERE`/`os.path.join(..., "static", ...)`.

### Pitfall 2: `test_i18n.py`'s non-conforming summary line breaks naive ledger tooling
**What goes wrong:** copying `32-ledger-check.py`'s `SUMMARY_RE` unchanged silently produces
`total=None` for this one harness during `--capture`.
**Why it happens:** `test_i18n.py`'s `main()` prints `"%d/%d checks pass"` (no name),
diverging from all 8 siblings' `"%s: %d/%d checks pass"`.
**How to avoid:** widen the regex (shown in Migration Ledger section) before running
`--capture` for the first time.
**Warning signs:** `33-BASELINE/INDEX.md`'s row for `test_i18n.py` shows a blank/wrong Total
column.

### Pitfall 3: This sandbox's stale Chromium cache silently degrades to "SKIP" during research/execution
**What goes wrong:** any command that doesn't override `PLAYWRIGHT_BROWSERS_PATH` will use
`/opt/pw-browsers`'s r1194 build, which does NOT match `playwright==1.63.0`'s expected r1243 —
every browser harness/test prints `SKIP`/errors out rather than actually exercising Chromium.
**Why it happens:** the sandbox's pre-baked browser cache predates the current `playwright`
pin (or was baked for a different pin).
**How to avoid:** `playwright install --only-shell chromium` against a writable
`PLAYWRIGHT_BROWSERS_PATH` before trusting ANY browser-harness result, local or ledger.
**Warning signs:** a browser check exits 0 suspiciously fast, or prints a `SKIP ...Chromium
launch failed...` line — this is EXACTLY the WR-04 defect class TST-11 exists to eliminate,
so treat any observed SKIP as "unverified," never as "passing."

### Pitfall 4: Treating the 4 `Harness` copies' minor differences as bugs to "fix" rather than history to understand
**What goes wrong:** "fixing" `test_config_page.py`/`test_status_pages.py`/`test_view_pages.py`'s
`Harness` to match `test_companion_app.py`'s `fake_providers=FakeProviders()` call changes
their behaviour (those 3 files have never needed the real-network guard to matter, because
they don't call `/poll-now`) — this isn't broken, it's simply not what those 3 harnesses need.
**Why it happens:** looks like an obvious "copy drift" cleanup during migration.
**How to avoid:** make the new shared fixture support BOTH modes (with/without fake
providers) explicitly, don't silently force one onto every test.
**Warning signs:** a migrated test starts failing on network-guard assertions it never had
before.

## Code Examples

### Structural CSS parse over the SERVED stylesheet (TST-12, stdlib-only option)
```python
# Illustrative — not lifted from any existing file. Operates on bytes fetched
# from the running app, not the file on disk (satisfies TST-12's "served by
# the app" requirement even without a third-party CSS parser dependency).
import re

_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)

def declarations_for_selector(css_text, selector):
    """{property: value} for the FIRST `selector { ... }` block in css_text.
    Handles the common case every current check needs; does not handle
    @media-nested rules or comma-separated selector lists — extend with
    tinycss2 if a future check needs that.
    """
    stripped = _COMMENT_RE.sub(" ", css_text)
    needle = selector + " {"
    start = stripped.index(needle) + len(needle)
    end = stripped.index("}", start)
    body = stripped[start:end]
    return {
        prop.strip(): value.strip()
        for prop, _, value in (
            decl.partition(":") for decl in body.split(";") if decl.strip()
        )
    }

# In a migrated test:
def test_section_caption_declares_exactly_one_muted_colour_mix(app_server, http_get):
    css = http_get(app_server.base_url + "/static/style.css").text
    decls = declarations_for_selector(css, ".section-caption")
    assert decls == {"color": "color-mix(in srgb, var(--color-text) 70%, transparent)"}
```

### Computed-style equivalent, when a live browser is already in play (preferred where available)
```python
# Adapted from the ALREADY-PROVEN pattern in companion/test_browser_ux_helpers.py
# (_resolved_property / _computed_paint) — reuse those helpers directly rather
# than reimplementing, in any migrated test that already has a `page` fixture.
def test_section_caption_colour_reads_muted(page, app_server):
    page.goto(app_server.base_url + "/health")
    colour = page.eval_on_selector(".section-caption", "el => getComputedStyle(el).color")
    assert colour  # real cascade-resolved value, not the raw custom-property text
```

### Deletable pattern: self-referential test-file ledger read (TST-12)
```python
# BEFORE (test_config_page.py:1652, test_browser_ux.py — near-identical copy):
def _every_aspect_repin_ledger_row_names_a_live_or_owed_replacement():
    with open(os.path.join(HERE, "test_config_page.py")) as fh:
        own_source = fh.read()
    for row in _ASPECT_REPIN_LEDGER:
        ...  # regex-searches own_source for `def <name>(` per plan-tracking row
# AFTER: DELETED. Ledger reason: "self-referential CFG-85 aspect-repin
# bookkeeping table tracking plan-history repayment across phases 30-05..08;
# asserts internal test-authoring metadata, not product behaviour; the check
# itself opens a .py file to grep text, which is exactly what TST-12 forbids."
```

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The +1 discrepancy between the measured 1250 companion checks and CONTEXT.md's expected 1249 is caused by a check added in a post-audit commit (Phase 32-continuation or Phase 34), not a miscount on my part | Migration Ledger & Baseline Capture | Low — I independently verified each per-file total two ways (the harness's own printed summary line AND `grep -c` on PASS/FAIL lines); if wrong, the actual root cause still needs identifying before the ledger's closing note can be written, but the number itself (1250) is solid |
| A2 | `tinycss2` is an acceptable dev-only dependency if the planner chooses the "real parser" path over the stdlib tokenizer | Standard Stack / Don't Hand-Roll | Low-medium — CONTEXT.md's exact phrase "small stdlib tokenizer" suggests a preference against a new dependency; if the planner or reviewer reads this as a hard constraint rather than a suggestion, `tinycss2` should not be added at all — treat the stdlib tokenizer as the default and `tinycss2` as a documented fallback only |
| A3 | `_resolve_flash_text("/nonexistent-state-dir-fixture", ...)` and the two `Harness(extra_args=["--geofence", "/nonexistent/..."])` call sites (test_companion_app.py:3873,3878,10865) do not themselves create host-filesystem side effects the way `anomaly_active()` does | Root-Safety Inventory | Medium — I read `_resolve_flash_text`'s docstring/call shape but did not trace its full implementation or `--geofence`'s consumer inside `companion/app.py` to confirm neither ever calls something like `os.makedirs`/`open(path, "w")` on the literal path; the migration plan touching these sites should explicitly verify this rather than assume it from this research alone |
| A4 | Chromium revision r1243 (freshly downloaded to a scratch `PLAYWRIGHT_BROWSERS_PATH`) behaves identically to whatever CI's own `playwright install --with-deps --only-shell chromium` step downloads, for the purpose of capturing an accurate browser-harness baseline in this sandbox | Environment Availability, Migration Ledger | Low — both are the same `playwright==1.63.0` pin resolving to the same upstream CDN build; only the LOCAL cache path differs |

## Open Questions

1. **Exact commit that added the +1 companion check since the 2026-09-23 audit**
   - What we know: `git log` shows Phase 34 (firmware, `companion/` untouched by most of it)
     and Phase 32-continuation plans (32-11..32-15, which DID touch
     `companion/test_companion_app.py`'s `/poll-now` section per CONTEXT.md's own note) landed
     after the audit's `2808f8a` commit.
   - What's unclear: whether 32-11's targeted `/poll-now` fake-provider edit added exactly
     one NEW check (rather than just modifying an existing one), or whether Phase 37's
     wave-A work already landed a companion check before this research session (CONTEXT.md
     says Phase 37 "may land on main during this phase" — check `git log` again at
     migration-plan time, not just at research time).
   - Recommendation: `git log -p --oneline -- companion/test_companion_app.py` since
     `2808f8a`, grep for a NEW `check(` call site (not a modified one), during the actual
     `33-BASELINE/` capture plan.

2. **Whether `/opt/pw-browsers`'s stale cache will be fixed before execution, or whether every
   execution plan needs its own `PLAYWRIGHT_BROWSERS_PATH` override**
   - What we know: a fresh `playwright install --only-shell chromium` against a scratch dir
     works cleanly through this sandbox's proxy.
   - What's unclear: whether the execution environment (a later session) will have the same
     stale `/opt/pw-browsers`, a fixed one, or a different sandbox entirely.
   - Recommendation: the browser-harness migration plans should NOT hardcode an assumption
     either way — verify `playwright.chromium.launch()` works at the start of that plan's
     session, and if not, run the install command shown in this research before capturing
     baselines or writing new pytest-playwright tests.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 + pytest-xdist 3.8.0 + pytest-cov 7.1.0 + pytest-socket 0.8.1 (all already installed/pinned; `pytest-playwright` 0.9.0 to be added) |
| Config file | `pyproject.toml` (`[tool.pytest.ini_options]`, `[tool.coverage.*]`) — already exists, Phase 32 |
| Quick run command | `server/.venv/bin/python3 -m pytest companion/test_<file>.py -v` (single migrated module, no coverage gate) |
| Full suite command | `./scripts/run-all-tests.sh` (unchanged entry point; enforces the coverage gate only with zero extra args) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TST-10 | Every companion test passes through the ONE shared app-server fixture; no `Harness`/`http_request`/`_NoRedirectHandler` duplication remains | grep/AST guard (meta-test) | `grep -c "^class Harness" companion/test_*.py` → must be 0 outside `conftest.py` | ❌ Wave 0 — write the guard test |
| TST-11 | A missing Chromium fails CI, skips locally | integration (fixture behaviour) | `PLAYWRIGHT_BROWSERS_PATH=/nonexistent pytest companion/ -k browser` (CI=1) → nonzero exit; (CI unset) → skip reported | ❌ Wave 0 — needs the fixture override from Pattern 2 first |
| TST-12 | No companion test opens `.planning/`, a UI-SPEC file, or a production `.py`/`.js`/`.css` source file as text | grep/AST guard (meta-test or CI step) | `grep -rn "\.planning\|open(.*\.py\"\|open(.*style\.css" companion/test_*.py` → must be empty (excluding the guard's own test file) | ❌ Wave 0 |
| TST-13 | Suite passes as root and non-root; nothing written outside `tmp_path` | integration, both euids | `pytest companion/` (root) and `runuser -u nobody -- pytest companion/` both green; `git status --porcelain` clean after either run | ✅ mechanism exists (`requires_non_root`, Phase 32 precedent) — companion tests just need it applied |
| TST-14 | `test_legacy_harness_shim.py`, `LEGACY_COMPANION_HARNESSES`, every `EXPECTED_CHECK_COUNT` gone | static check | `grep -rn "EXPECTED_CHECK_COUNT\|LEGACY_COMPANION" companion/ test-support/ conftest.py` → empty | ❌ closing plan only |
| TST-15 | `33-ledger-check.py --all` returns 0; coverage ≥ 93 | ledger tool + coverage gate | `python3 .planning/phases/33-.../33-ledger-check.py --all` (rc 0); `./scripts/run-all-tests.sh` (coverage gate) | ❌ needs `33-ledger-check.py` created (copy of `32-ledger-check.py`, see Migration Ledger section) |

### Sampling Rate
- **Per task commit:** `server/.venv/bin/python3 -m pytest companion/test_<just-migrated>.py -v` (fast, no coverage gate)
- **Per wave merge:** `./scripts/run-all-tests.sh` (full suite, coverage gate enforced)
- **Phase gate:** Full suite green + `33-ledger-check.py --all` rc 0 before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `companion/conftest.py` — the shared `app_server` fixture (does not exist today; Pattern 1)
- [ ] `.planning/phases/33-.../33-ledger-check.py` — copy of `32-ledger-check.py` with the `HARNESSES` list and `SUMMARY_RE` fix (Migration Ledger section)
- [ ] A "no source-text reads" guard test/CI step (TST-12's success criterion 3 mechanism — Claude's discretion whether meta-test or CI grep)
- [ ] The missing-browser fixture override in `companion/conftest.py` (Pattern 2)
- [ ] `33-BASELINE/` capture (needs a working Chromium — see Environment Availability)

## Security Domain

`security_enforcement: true`, ASVS level 1 (`.planning/config.json`). This phase changes test
code only — CONTEXT.md's "Not in this phase" explicitly excludes companion production-behaviour
changes (a production fix is allowed ONLY when a rewritten test exposes a real bug, recorded
as a deviation) — so most ASVS categories are not newly applicable here.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | No (no new auth code) | Existing `TEST_PASSWORD`/`auth.PASSWORD_ENV_VAR` pattern reused unchanged from Phase 32/pre-existing harnesses |
| V3 Session Management | No | Unchanged — the shared fixture reuses the existing cookie-based session helper (`_login()`) pattern |
| V4 Access Control | No | Unchanged |
| V5 Input Validation | No (test code, not a new input-handling surface) | N/A |
| V6 Cryptography | No | N/A |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A test-only hardcoded password (`TEST_PASSWORD = "companion-test-password-please-ignore"`) leaking into a real deployment | Information Disclosure | Already mitigated: `deploy/deploy.sh` never installs `server/requirements-dev.txt` or copies `test-support/`/`companion/test_*.py` to the VPS; this phase does not change deploy scope |
| A migrated test accidentally reaching a real external host (real ADS-B/adsbdb providers) because the new `pytest-playwright` browser context doesn't inherit the same network guard as `requests`/`urllib` | Tampering / Information Disclosure (real, rate-limited external services touched by test runs) | The existing `pytest-socket --disable-socket --allow-hosts=127.0.0.1,::1,localhost` guard (`pyproject.toml`) applies at the OS `socket` level, which a Playwright-launched Chromium process's own network stack also goes through when running IN THIS SAME MACHINE — but Playwright browser processes are subprocesses of the pytest worker, and MUST be launched with (or inherit) `child_env()`'s guard vars for `sitecustomize.py` to apply inside them too, exactly like `companion/app.py`. **Verify this explicitly during the browser-harness migration** — a real Chromium tab navigating to a non-loopback URL is a distinct risk surface from `requests`/`urllib`, and pytest-socket's guard is documented as covering `socket.socket` at the Python level, not necessarily a separate browser process's own network stack unless that process is also guarded (loopback-only navigation is already this project's own stated invariant per `test_browser_ux.py`'s header comment: "every check below navigates ONLY to `Harness.base_url()`" — preserve this invariant explicitly in the migrated tests, don't rely on it being incidental) |

## Sources

### Primary (HIGH confidence)
- Direct execution of all 9 companion harnesses in this repository/sandbox (git commit
  `6d4d741`, branch `claude/phase-33`) — baseline PASS/FAIL counts, wall-clock times, live
  reproduction of the `/nonexistent` host-filesystem side effect
- Direct reads of `conftest.py`, `test-support/skypane_test_support.py`,
  `test-support/sitecustomize.py`, `pyproject.toml`, `scripts/run-all-tests.sh`,
  `scripts/lock-deps.sh`, `server/requirements-dev.in`, `.github/workflows/ci.yml`,
  `companion/test_legacy_harness_shim.py`, and all 9 companion `test_*.py` files (targeted
  reads + full-file greps)
- `.planning/audits/2026-09-23-code-audit.md` (TST-10..15 rows, D-A1..D-A6, measured baseline)
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-PATTERNS.md`,
  `32-VERIFICATION.md`, `32-REVIEW.md`, `32-ledger-check.py`, `32-MIGRATION-LEDGER.md`,
  `32-BASELINE/INDEX.md`
- `playwright.dev/python/docs/intro` [CITED via WebFetch] — confirms `pytest-playwright` is
  the official package name/installation method
- PyPI JSON API (`pypi.org/pypi/pytest-playwright/0.9.0/json`,
  `pypi.org/pypi/tinycss2/json`) [VERIFIED via curl] — `requires_dist`/`requires_python`
- Live `uv pip compile --generate-hashes` run against a scratch copy of
  `server/requirements-dev.in` with `pytest-playwright==0.9.0` added
- `slopcheck` 0.6.1 run against `pytest-playwright`, `pytest-base-url`, `python-slugify`,
  `text-unidecode`, `tinycss2` — all `[OK]`

### Secondary (MEDIUM confidence)
- None beyond the above — every claim in this document was either executed live in this
  session or read directly from the repository's own source.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack (pytest-playwright compatibility): HIGH — verified via official docs, PyPI
  metadata, and a live install/run in this sandbox
- Quantitative harness inventory (line counts, check counts, wall times): HIGH — every number
  came from actually running the code, not from reading source and estimating
- Source-text inventory counts (the "309/77" audit figures vs. this research's own grep-based
  per-file counts): MEDIUM — the audit's aggregate totals are cited, not independently
  re-derived to the exact check; this research verified representative samples (the 2 named
  audit sites plus several more discovered independently) and provided a reusable method
  (AST scan script + grep patterns) for the planner's Wave 0 to get the exhaustive count,
  rather than hand-classifying all ~386 checks in this research pass — that volume of
  classification is itself migration-plan work, not research
- Root-safety inventory: HIGH — exhaustive grep across all 9 files, every hit read in context,
  one finding (the `/nonexistent` mkdir) independently reproduced live on the host filesystem

**Research date:** 2026-09-24
**Valid until:** 30 days for the pytest-playwright/tooling findings (stable ecosystem); the
live baseline counts (1250 checks) should be treated as valid only until the next commit
touches `companion/test_*.py` (Phase 37 coordination note in CONTEXT.md already anticipates
this — re-capture before finalizing the ledger, not before planning)
