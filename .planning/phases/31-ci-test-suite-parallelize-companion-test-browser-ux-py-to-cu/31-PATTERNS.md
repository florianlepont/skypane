# Phase 31: CI test suite — parallelize companion/test_browser_ux.py - Pattern Map

**Mapped:** 2026-09-22
**Files analyzed:** 6 (3 new harness files + 1 new shared helper module + 2 modified files; `pyproject.toml` listed as conditional)
**Analogs found:** 6 / 6 (every file has a same-repo analog; no "no analog found" cases — RESEARCH.md already did the heavy lifting of locating source line ranges)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `companion/test_browser_ux_health_drawings.py` (NEW) | test (browser/E2E harness) | request-response (Playwright drives Chromium against a local HTTP subprocess) | `companion/test_browser_ux.py` itself (lines 3635-3670 skip-gate/`main()` shape; lines 9411-10882 for the check bodies to move) | exact — same file is both the skip-gate precedent and the source of the moved code |
| `companion/test_browser_ux_quiet_wake.py` (NEW) | test (browser/E2E harness) | request-response | `companion/test_browser_ux.py` (same skip-gate shape; lines 11516-13379 for check bodies) | exact |
| `companion/test_browser_ux_flights.py` (NEW, optional/conditional) | test (browser/E2E harness) | request-response | `companion/test_browser_ux.py` (same skip-gate shape; lines 3689-3959 + 8598-9092 for check bodies) | exact |
| `companion/test_browser_ux_helpers.py` (NEW, shared module — not a harness) | utility (pure helper module, no `main()`) | transform (DOM measurement / geometry decoding, no I/O of its own) | `companion/test_browser_ux.py` lines 1-3660 (the module-level preamble: constants + ~40 helper functions) — this IS the extraction source, not a separate analog | exact (verbatim relocation) |
| `companion/test_browser_ux.py` (MODIFIED — reduced) | test (browser/E2E harness) | request-response | itself, pre-split (no external analog needed — this is a reduction, not a new pattern) | n/a (self) |
| `scripts/run_all_tests.py` (MODIFIED — new `HARNESSES`/`EXPECTED_SLOWEST` entries) | config/orchestration | batch (subprocess fan-out via `ThreadPoolExecutor`) | itself — the existing `HARNESSES` list entry for `companion/test_browser_ux.py` (lines 62-90) is the literal pattern to replicate for each new entry | exact |
| `pyproject.toml` `[tool.coverage.run]` `omit` (POSSIBLY MODIFIED) | config | n/a | itself — existing `omit` list entries (`companion/app.py`, `stub-server/byos_server.py`) are the precedent for adding a one-off non-`test_*.py` exclusion, only needed if the helper module is NOT named with a `test_` prefix | conditional — only touched if Pitfall 3 option 2 is chosen |

## Pattern Assignments

### `companion/test_browser_ux_health_drawings.py` / `companion/test_browser_ux_quiet_wake.py` / `companion/test_browser_ux_flights.py` (test, request-response)

**Analog:** `companion/test_browser_ux.py` (the only Playwright-driving harness in the repo — copy its skip-gate and `main()` shape verbatim into each new file; do NOT copy any non-Playwright `companion/test_*.py` sibling's harness shape, since those never import Playwright at all — see "Corrections to CONTEXT.md" #2 in RESEARCH.md).

**Imports pattern** (from `companion/test_browser_ux.py` lines 34-53, 94-108 — adapt per new file, only importing what that group's moved checks actually use):
```python
import ast
import hashlib
import hmac
import html
import io
import json
import math
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import tokenize
import urllib.error
import urllib.parse
import urllib.request
# ... (path-setup boilerplate identical to original file, lines ~60-93) ...
from companion import auth, draw, i18n, layout  # noqa: E402
from companion.contrast_check import (  # noqa: E402
    ...
)
from companion.test_companion_app import Harness, TEST_PASSWORD  # noqa: E402
from companion.pages import (  # noqa: E402
    ...
)
from server import device_config, history_db  # noqa: E402
from companion import illustration_normalize  # noqa: E402
from server.plane import colour_rules, illustrations, manual_resolutions  # noqa: E402

# NEW for the split — pull shared helpers from the new module instead of
# defining them inline:
from companion.test_browser_ux_helpers import (
    seed_state_dir, _login, _wait_for_bar, _wait_for_bar_hidden,
    _set_ui_theme, _in_both_themes, _assert_hit_target,
    # + group-specific helpers, e.g. for quiet_wake:
    # _quiet_arc_minutes, _quiet_caption_minutes, _QUIET_ARC_SELECTOR, ...
)
```

**Skip-gate + harness + browser pattern to copy verbatim** (source: `companion/test_browser_ux.py` lines 3635-3670; RESEARCH.md "Code Examples" already extracted this exactly — reproduced here for the planner):
```python
def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "SKIP companion/test_browser_ux_<group>.py — playwright not installed "
            "(dev-only dependency; run "
            "`pip install -r server/requirements-dev.txt` to enable this harness)")
        return 0

    try:
        with sync_playwright() as p:
            probe = p.chromium.launch()
            probe.close()
    except Exception as exc:
        print(
            "SKIP companion/test_browser_ux_<group>.py — Chromium launch failed (%r); "
            "run `python -m playwright install chromium`" % (exc,))
        return 0

    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        print("PASS %s" % name if ok else "FAIL %s - %s" % (name, reason))

    harness = Harness()          # from companion.test_companion_app import Harness
    seed_state_dir(harness.tmpdir)   # imported from the new shared helper module
    harness.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                # ... this group's check() call sites, moved verbatim ...
                pass
            finally:
                browser.close()
    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("<group>: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

**Core pattern (check-body relocation):** move the group's `check("name", lambda: ...)` call sites verbatim, in file order, from `companion/test_browser_ux.py` into the new file's `main()` body, between `browser = p.chromium.launch()` and `browser.close()`. Two groups have their own isolated sub-`Harness()` instances that must move together with their checks:
- Health SVG group (lines 9411-10882): 2 of 9 checks already use `band_harness`/`grid_harness` — these are self-contained sub-blocks, move as-is.
- Quiet-hours/wake group (lines 11516-13379): the closure `_quiet_hours_on_disk()` is defined **inside** `main()` (line 11469), not at module level — redefine it inside the new file's `main()`, closing over that file's own `harness`, not imported from the shared helper module.

**EXPECTED_CHECK_COUNT convention:** each new file gets its own `EXPECTED_CHECK_COUNT = N` module-level constant, set by actually running the file standalone and reading its printed `<group>: M/N checks pass` line — never hand-computed from a line-range count (RESEARCH.md Pitfall 1; this repo's own convention, re-derived at every bump in `test_browser_ux.py`'s own history, e.g. "94 + 2 = 96, re-derived by RUNNING").

**Error handling pattern:** identical to the skip-gate code above — `check()`'s own try/except around each `fn()` call (catches any exception, converts to `FAIL ... - exception: %r`), plus the two top-level skip gates (`ImportError` for missing playwright, generic `Exception` for missing Chromium binary) that return 0 rather than propagating.

---

### `companion/test_browser_ux_helpers.py` (utility module, transform — NEW, no `main()`)

**Analog:** the existing module-level preamble of `companion/test_browser_ux.py` (lines 1-3660, up to `def main():` at line 3635) — this file IS the extracted preamble, not a copy of a different pattern.

**Contents to relocate verbatim:**
- All module-level constants (e.g. `MIN_HIT_TARGET_PX`, `SEED_BASE_TS`, `_QUIET_ARC_SELECTOR`).
- `_login(page, base_url)` (line 1134) — pure, `page`/`base_url` only.
- `_wait_for_bar(page, timeout=5000)` / `_wait_for_bar_hidden` (lines 1252/1266) — pure, `page` only.
- `seed_state_dir(state_dir, base_ts=SEED_BASE_TS)` (line 1044) — writes fixture data via `server/history_db.py`, `server/device_config.py`, `server/plane/manual_resolutions.py`, `server/plane/colour_rules.py`, `server.poll_loop._save_to_gallery()`. Designed to be called once per isolated `Harness()` instance — already used that way by `band_harness`/`grid_harness`/`lockout_harness`/`artwork_harness` in the original file.
- `_set_ui_theme(page, theme)` / `_in_both_themes(page)` (lines 1392/2782) — pure, `page` only.
- `_assert_hit_target(page, selector, where, minimum=MIN_HIT_TARGET_PX)` (line 2570) — depends on `_hit_area()` (2358) and `MIN_HIT_TARGET_PX`, must move together.
- `_quiet_arc_minutes(page, where, selector=_QUIET_ARC_SELECTOR, radius=None)` (line 3228) **must** move here (not into the quiet-wake file alone) — it is called both from the Quiet-hours/wake group (lines 11881, 12062) and from a mega-cluster check that stays in the original file (lines 15087/15116/15195). Its dependency cluster `_quiet_caption_minutes`, `_quiet_caption_shape`, `_quiet_duration_span_text`, `_expected_quiet_duration_text`, `_fraction_to_minute`, `_fraction_pair_minutes` (lines 3132-3612) moves with it as one unit.

**Naming/coverage-omit consequence (RESEARCH.md Pitfall 3, decision needed at plan time, pick one):**
1. Name it `companion/test_browser_ux_helpers.py` (keeps the `test_` prefix) → auto-covered by `pyproject.toml`'s existing `omit` glob `"companion/test_*.py"` with **zero** config changes. Add a one-line module docstring note: "shared helpers, not a harness — do not add to HARNESSES." **Recommended** — matches RESEARCH.md's own stated preference and needs no `pyproject.toml` diff.
2. Name it without a `test_` prefix (e.g. `companion/browser_ux_shared.py`) → requires one new explicit entry in `pyproject.toml`'s `omit` list (see below), justified the same way the existing `companion/app.py` / `stub-server/byos_server.py` entries are justified (measured coverage would be a "structurally unmeasurable / misleading" M5-class false signal, not a real regression).

---

### `companion/test_browser_ux.py` (MODIFIED — reduced)

**Change shape:** remove the moved `check()` call sites and their group-local helper closures (if any); remove the corresponding module-level helper/constant definitions now living in `companion/test_browser_ux_helpers.py`, replacing them with an import from that module (same import-list shape as the new files above); reduce `EXPECTED_CHECK_COUNT` from 96 by exactly the number of checks moved out (18 if extracting Health SVG + Quiet-hours/wake only, giving 78; 26 if Flights is also extracted, giving 70) — **re-derive by actually running the reduced file**, never by hand subtraction (Pitfall 1).

---

### `scripts/run_all_tests.py` (MODIFIED — config/orchestration, batch)

**Analog:** the file's own existing `companion/test_browser_ux.py` entries in `HARNESSES` (lines 62-90) and `EXPECTED_SLOWEST` (lines ~96-113).

**Exact wiring to add** (source: `scripts/run_all_tests.py`, live file — confirmed live AST count is **22** entries today, not RESEARCH.md's cited "18" from a stale docstring; going to 24-25 after this phase; also fix the module docstring's stale "18" count while touching this file):
```python
HARNESSES = [
    # ... existing 22 entries unchanged ...
    "companion/test_browser_ux.py",                   # reduced, stays
    "companion/test_browser_ux_health_drawings.py",    # NEW
    "companion/test_browser_ux_quiet_wake.py",         # NEW
    # "companion/test_browser_ux_flights.py",          # NEW, optional 3rd
]

EXPECTED_SLOWEST = (
    "companion/test_browser_ux.py",
    "companion/test_browser_ux_health_drawings.py",    # NEW — place near top,
    "companion/test_browser_ux_quiet_wake.py",          # longest-first, since
    # these will be among the slowest remaining harnesses (each still
    # launches its own Chromium + companion/app.py subprocess)
    "server/test_render.py",
    "server/test_poll_loop.py",
    "companion/test_companion_app.py",
    "stub-server/test_poll_cycle.py",
    "server/test_panel_preview.py",
    "companion/test_status_pages.py",
    "server/test_pipeline_e2e.py",
)
```
Note the `companion/test_browser_ux.py` entry's own inline comment (lines 82-86 of the current file) documents why it's placed where it is — new entries should carry an analogous one-line comment explaining they're a split-off of that file, per this repo's convention of commenting every `HARNESSES` entry that isn't self-explanatory.

**No other change** to `scripts/run_all_tests.py`'s `_run_one()`, `JOBS` handling, or timeout/SIGKILL logic — that plumbing is already generic over any path in `HARNESSES` (confirmed by reading the file in full per RESEARCH.md Sources).

---

## Shared Patterns

### Playwright skip-gate (the only precedent in the repo)
**Source:** `companion/test_browser_ux.py` lines 3635-3670 (reproduced verbatim above)
**Apply to:** all three new harness files. This is NOT the same pattern as any other `companion/test_*.py` sibling — those (`test_companion_app.py`, `test_config_page.py`, `test_status_pages.py`, `test_view_pages.py`, `test_i18n.py`, `test_contrast_check.py`) all use `Harness` but never import Playwright or drive a real browser (they compare rendered HTML strings). Do not pattern-match the new files against those siblings for the browser-launch/skip-gate portion — only for the `Harness()`/subprocess portion (see below).

### `Harness` subprocess + free-port allocation
**Source:** `companion/test_companion_app.py`, `Harness` class (`_pick_free_port` at lines 1229-1235):
```python
@staticmethod
def _pick_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))   # OS assigns an ephemeral free port
        return s.getsockname()[1]
    finally:
        s.close()
```
**Apply to:** all three new harness files, via `from companion.test_companion_app import Harness, TEST_PASSWORD` (same import line as `companion/test_browser_ux.py` line 103) — no new port-allocation code needed, each `Harness()` instantiation already gets a collision-free ephemeral port, safe under `JOBS=4` concurrent execution.

### `check(name, fn)` / `EXPECTED_CHECK_COUNT` / `main()` convention
**Source:** established repo-wide in `04-CONTEXT.md` D-07; every harness including `companion/test_browser_ux.py` follows it.
**Apply to:** all three new harness files AND the reduced `companion/test_browser_ux.py` — one `results = []` / `check()` closure / `EXPECTED_CHECK_COUNT` gate per file, each independently derived by running the file, never shared or hand-computed across files.

### Coverage `omit` glob
**Source:** `pyproject.toml` `[tool.coverage.run]` `omit` (lines 68-96), entry `"companion/test_*.py"`.
**Apply to:** all three new harness files automatically (no config change needed, they match the glob). The shared helper module needs an explicit naming decision — see "Naming/coverage-omit consequence" above; only touch `pyproject.toml` if option 2 is chosen.

## No Analog Found

None. Every file in this phase's scope has a same-repo, same-commit analog (RESEARCH.md's own deep read already located exact source line ranges for every file to be created).

## Metadata

**Analog search scope:** `companion/*.py`, `scripts/run_all_tests.py`, `pyproject.toml` — all read directly from the live repository (no web search needed; this is a pure internal-repo pattern-mapping task).
**Files scanned:** `companion/test_browser_ux.py` (targeted reads: lines 1-53, 94-108 imports; 3635-3670 skip-gate; scenario-group line ranges per RESEARCH.md), `companion/test_companion_app.py` (imports + `Harness._pick_free_port`), `scripts/run_all_tests.py` (`HARNESSES`/`EXPECTED_SLOWEST`, lines 62-113), `pyproject.toml` (`[tool.coverage.run]`, lines 46-96).
**Pattern extraction date:** 2026-09-22
</content>
