---
phase: 37-security-and-operations-hardening
plan: 02
subsystem: companion
tags: [health-page, i18n, backups, ads-b, pytest, tdd]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    provides: pytest infrastructure (conftest.py, pyproject.toml [tool.pytest.ini_options], no-network socket guard)
provides:
  - "companion/pages/health_page.py: OFFBOX_MARKER_ENV_VAR/OFFBOX_WARN_S constants, offbox_backup_status() marker reader (never raises, fails closed to warn), _offbox_anomaly_text()/_offbox_section_html() rendering helpers, overall_severity()/collect_anomalies()/compute_health_state() widened with a defaulted offbox_state/offbox parameter"
  - "companion/i18n_fr/health.py: FR strings for the off-box card and its two anomaly sentences, plus a new 'never'->'jamais' catalogue entry"
  - "companion/test_health_offbox.py: 25 native pytest tests (marker parsing, severity/anomaly wiring, compute_health_state integration, EN/FR render)"
affects: [37-04 (backup_gate.py's `ack` writes the marker this plan reads), 37-security-and-operations-hardening (SEC-04)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Marker file contract: env var names the file, at most 256 bytes read, strict regex on content, any OSError/ValueError degrades to the same {'state': 'warn', 'snapshot_ts': None} shape as 'never happened' — never an exception"
    - "A signal capped at warn (never error) by passing error_s=float('inf') into the existing staleness_status(age, warn_s, error_s) three-state helper, rather than adding a fourth branch"
    - "One shared _offbox_anomaly_text(offbox) helper feeds both collect_anomalies() (banner) and _offbox_section_html() (inline warn paragraph) so the two can never read different words for the same state"
    - "compute_health_state() reads the marker exactly once per request (via offbox_backup_status(now)) and threads the result through both severity/anomaly computation and the returned dict's 'offbox' key for render() to reuse — no second read"

key-files:
  created:
    - companion/test_health_offbox.py
  modified:
    - companion/pages/health_page.py
    - companion/i18n_fr/health.py
    - companion/test_legacy_harness_shim.py
    - .planning/phases/37-security-and-operations-hardening/deferred-items.md

key-decisions:
  - "offbox_state is appended as the LAST parameter to overall_severity()/collect_anomalies() (after source_fault), matching the existing pattern of each new signal being appended after the ones before it, so every pre-existing call site is unaffected"
  - "The off-box card and its warn paragraph reuse the exact _offbox_anomaly_text() sentence collect_anomalies() computes — one function, two consumers — rather than two independently-worded copies of the same fact"
  - "'never' (the concise_timestamp_html() fallback for a missing marker) is added to the FR catalogue as its own entry rather than inlined, since it is this card's only call site across the app"

requirements-completed: [SEC-04]

# Metrics
duration: 12min
completed: 2026-09-24
---

# Phase 37 Plan 02: Off-box backup freshness on the Health page Summary

**The companion Health page now reads a marker file (SKYPANE_OFFBOX_MARKER) written by the forced-command backup gate, shows "Off-box backup" as an ok or warn nested card with a ticking concise timestamp, and lights the Health nav dot at warn (never error) when the last pull is stale or has never happened — EN/FR complete.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-09-24T07:51:00Z
- **Completed:** 2026-09-24T08:02:29Z (Task 2 commit)
- **Tasks:** 2/2 completed
- **Files modified:** 4 (1 created, 3 modified) + 1 deferred-items.md addendum

## Accomplishments
- `offbox_backup_status(now)` in `companion/pages/health_page.py`: reads `os.environ.get(OFFBOX_MARKER_ENV_VAR)` fresh on every call (never cached), reads at most 256 bytes of the marker, validates it against `^skypane-state-(\d{8}T\d{6}Z)\.tar\.gz$`, converts the archive-name timestamp to an ISO snapshot time, and derives a state capped at `"warn"` via `staleness_status(age, OFFBOX_WARN_S, float("inf"))`. A missing file, path-traversal-shaped content, empty content, binary garbage, or a 10 kB file all degrade to `{"state": "warn", "snapshot_ts": None}` — never an exception (T-37-06/T-37-07).
- `overall_severity()`/`collect_anomalies()` widened with a fully-defaulted `offbox_state`/`offbox` parameter; the warn clause gained `offbox_state == "warn"` with no membership in the error branch, so a stale/never-pulled backup can only ever push the Health nav dot to warn (D-23), never error, and every pre-existing 4..6-argument call site is byte-for-byte unaffected (pinned by the existing `test_status_pages.py` precedence check, still green).
- `compute_health_state()` calls `offbox_backup_status(now)` exactly once per request, publishes it under the returned dict's `"offbox"` key, and feeds it to both `overall_severity()` and `collect_anomalies()` — the same "one snapshot, every consumer reuses it" discipline the function's own WR-04 docstring already states for its other four signals.
- `_offbox_section_html(offbox, now)` renders the card: hidden entirely (`""`) when the env var is unset, otherwise a `page-section page-section--nested` card (reusing `layout.card_status_class()`/`layout.status_dot()`/`layout.concise_timestamp_html()`, the exact pattern the registry card already uses) with an ok/warn status dot, the last-backup concise timestamp (a real `<time data-relative>` element, ticking client-side, fallback "never"/"jamais"), and — only when warn — the identical sentence the anomaly banner uses. Wired into `render()`'s `server_data_section_html`, between the registry card and the resolution-statistics card.
- French strings added to `companion/i18n_fr/health.py` (sentence case, U+2019 apostrophe, real U+00A0 before the unit in "3 jours") — the D-08 mechanical completeness/dead-translation/live-French-render checks in `test_i18n.py` all pass (24/24), including a real French render of `GET /health`.
- `companion/test_health_offbox.py`: 25 native pytest tests across four sections — marker parsing (unit), severity/anomaly wiring (unit), `compute_health_state()` (integration against a real, empty state dir), and the rendered EN/FR card (render). RED (AttributeError on `health_page.offbox_backup_status`) confirmed before GREEN for Task 1's TDD gate.

## Task Commits

Each task was committed atomically:

1. **Task 1: Phase 32 gate, then marker reader and severity wiring (TDD)** - `c514f14` (feat) — RED (20 failing/erroring tests) confirmed, then GREEN.
2. **Task 2: Render the off-box backup card (design system) + French strings** - `cd9d2f8` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `companion/pages/health_page.py` - `OFFBOX_MARKER_ENV_VAR`/`OFFBOX_WARN_S`/`_OFFBOX_MARKER_RE` constants; `offbox_backup_status()`, `_offbox_anomaly_text()`, `_offbox_section_html()`; `overall_severity()`/`collect_anomalies()`/`compute_health_state()` widened; `render()` wired to include the new card; `os`/`re` added to the stdlib import list
- `companion/i18n_fr/health.py` - Six new catalogue entries: the four card strings, the two anomaly sentences, and `"never"` -> `"jamais"`
- `companion/test_health_offbox.py` - New pytest file: 25 tests (marker unit, severity/anomaly unit, compute_health_state integration, EN/FR render)
- `companion/test_legacy_harness_shim.py` - `test_legacy_harness_list_matches_disk` exempts the new native pytest file, the same way 37-01 already exempted `test_login_throttle.py`
- `.planning/phases/37-security-and-operations-hardening/deferred-items.md` - Records a pre-existing, sandbox-local `test_status_pages.py` failure found while verifying (see Issues Encountered)

## Decisions Made
- `offbox_state`/`offbox` are appended as the LAST (newest) defaulted parameter on `overall_severity()`/`collect_anomalies()`, following the same append-only widening `coverage_state`/`source_fault` already established — no existing call site's positional arguments shift.
- `_offbox_anomaly_text(offbox)` is the one shared definition of the off-box anomaly sentence, read by both `collect_anomalies()` (the banner) and `_offbox_section_html()` (the inline warn paragraph) — the same "one definition, two consumers" discipline `PIPELINE_STATE_TEXT` already follows for its own verdict/anomaly pair, so the two surfaces can never read different words for the same state.
- The docstring's literal quoted call `os.environ.get(OFFBOX_MARKER_ENV_VAR)` was reworded to `os.environ` (see the function's own body) specifically so a `grep -c "os.environ.get(OFFBOX_MARKER_ENV_VAR"` finds exactly the one real call site, not a docstring echo of it — matching the plan's own acceptance criterion.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Exempted the new native pytest file from the legacy-harness drift guard**
- **Found during:** Task 1, running the drift-guard test directly
- **Issue:** `test_legacy_harness_shim.py::test_legacy_harness_list_matches_disk` asserts every `test_*.py` file under `companion/` is a registered legacy harness. `companion/test_health_offbox.py` is this plan's own deliverable and a second native pytest file — the guard failed on its mere existence, the identical shape 37-01 already hit and fixed for `test_login_throttle.py`.
- **Fix:** Added `"test_health_offbox.py"` to the same exemption tuple.
- **Files modified:** `companion/test_legacy_harness_shim.py`
- **Verification:** `pytest -q companion/test_legacy_harness_shim.py -k test_legacy_harness_list_matches_disk` passes; full suite re-run confirms no other file lost coverage.
- **Committed in:** `c514f14` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary consequence of adding the plan's own required test file, identical in shape to 37-01's own precedent. No scope creep.

## Issues Encountered

**Two pre-existing, root-euid-only WR-11 legacy check failures (not caused by this plan, not fixed — already documented in `deferred-items.md` by 37-01).** `./scripts/run-all-tests.sh` in this sandbox shows exactly `test_companion_app`/`test_status_pages` failing, unchanged from 37-01's own baseline (809 passed here vs. 784 in 37-01, the +25 delta being exactly this plan's own new tests; coverage 93.25%, above the 93% gate).

**One additional, previously-mischaracterized `test_status_pages.py` finding, documented but not fixed.** While isolating whether this plan's `health_page.py` edits changed that file's pass count, direct execution of `companion/test_status_pages.py` (both before, via `git show HEAD:`, and after this plan's edits) showed the identical single failure — `anomaly_active("/nonexistent/definitely-not-here")` returning `True` instead of `False` — caused by stale sandbox state: an earlier session already created a real `/nonexistent/definitely-not-here/history.db` on disk (root-owned), so the path the check assumes is nonexistent is, in this sandbox, a genuinely empty-but-writable directory instead, which the check's own comment documents as legitimately warn. Confirmed identical on the unmodified module — not introduced by SEC-04, not the WR-11 chmod pattern 37-01 documented for the same file (grep confirms no `chmod`/`0o500` pattern exists in `test_status_pages.py` at all). Recorded in `deferred-items.md` as Phase 33 scope (the check should generate its "nonexistent" path via `tempfile` rather than a hardcoded absolute path).

## User Setup Required

None - no external service configuration required. (The marker this plan reads is written by Plan 37-04's `backup_gate.py`, not by this plan.)

## Next Phase Readiness

- `OFFBOX_MARKER_ENV_VAR = "SKYPANE_OFFBOX_MARKER"` and the marker's exact contract (archive-name regex, at most 256 bytes, optional trailing newline) are the stable interface Plan 37-04's `backup_gate.py ack` and `deploy/skypane.env.example` must produce against.
- No blockers for the rest of Wave A (SEC-01/02/03/05/06/07/08 minus byos).

---
*Phase: 37-security-and-operations-hardening*
*Completed: 2026-09-24*

## Self-Check: PASSED

All files claimed as created/modified exist on disk (`companion/pages/health_page.py`,
`companion/i18n_fr/health.py`, `companion/test_health_offbox.py`,
`companion/test_legacy_harness_shim.py`, `deferred-items.md`, this file). Both task
commits (`c514f14`, `cd9d2f8`) are present in `git log --oneline --all`.
