---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 08
subsystem: testing
tags: [pytest, migration-ledger, calendar-rules, ssrf-gate, monkeypatch, dns-guard]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 01)
    provides: pytest/xdist/cov/socket config, conftest.py DNS guard, test-support/skypane_test_support.py
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust (plan 02)
    provides: 32-BASELINE/server__test_calendar_rules.txt transcript, 32-ledger-check.py, 32-ledger/ fragment format
provides:
  - server/test_calendar_rules.py as a real pytest module (113 test functions covering all 113 baseline checks 1:1, 0 deleted)
  - 1 ledger fragment under 32-ledger/ mapping all 113 baseline checks to node ids
  - a worked example of migrating a harness whose checks legitimately need `monkeypatch` for socket.getaddrinfo/os.chmod/os.environ.get/builtins.open spies, plus a fix for a DNS-guard-vs-application-exception-handling interaction (the RFC 2606 ".invalid" unresolvable-hostname check)
affects: [32-09, 32-10, 32-13]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "An AST-based mechanical transform (build main()'s check() call list in true source order via node.lineno - NOT ast.walk()'s traversal order, which is breadth-first and can reorder nested-branch checks relative to their siblings) matched each check(label, fn) call to its target FunctionDef (including the 4 functions nested one level inside an `if/else` branch), replaced every `return False, X` Return node with `pytest.fail(X)` using the RETURN node's own end offset (not the inner expression's end offset, which excludes any grouping parens the developer wrote for line continuation - using the statement's own span and stripping a literal 'return False,' prefix reproduces the original text, including redundant-but-valid double parens, exactly), and dropped every trailing `return True, \"\"`."
    - "`with tempfile.TemporaryDirectory() as tmp:` becomes `tmp = tmp_path` plus a 4-space dedent of the with-block's body (not a variable rename) - preserves every downstream `tmp`-named reference unchanged; a function needing two independent directories (test_environment_is_never_consulted) instead takes `tmp_path_factory` and calls `.mktemp(\"configured\")`/`.mktemp(\"unconfigured\")`."
    - "Manual socket.getaddrinfo/cr.os.chmod/cr.os.open/cr.os.replace/os.environ.get/builtins.open save-restore dances (9 of this harness's 113 checks used this pattern, mostly for _url_is_safe()'s DNS-rebinding proof and save_calendar_url()'s 0600-at-creation-time/never-chmods spies) become `monkeypatch.setattr(...)`, dropping the try/finally wrapper - MR-6 explicitly names socket.getaddrinfo as a global-state example, and dropping the manual restore removes an entire class of test-pollution risk under `-n 4`."
    - "Shared per-check setup that lived as local variables inside main() (the `cr`/`device_config` imports, `fixture_text`, `CAL_THEME`/`CAL_CFG`/`MATCH_NOW`, the `_route()` closure, and the ambiguity fixture's `near_entry`/`far_entry`/`bbb_ory_entries`/`ambiguity_route`) is promoted to module scope under the SAME names the check closures already referenced - zero renaming needed in the 113 ported function bodies, since Python resolves an unbound name in a function body against module globals identically to how it resolved it against an enclosing closure."
    - "A defensive guard-and-skip branch that never fires under the current fixture (`if len(bbb_ory_entries) != 2: check(<setup failure>, ...) else: <4 real checks>`) is NOT a baseline check (it never printed a PASS/FAIL line in 32-BASELINE/server__test_calendar_rules.txt, since the `else` branch always ran) - it becomes a plain module-level `assert` at import time instead of a ported test, correctly keeping the ledger at 113/113 with no phantom 114th row."

key-files:
  created:
    - .planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_calendar_rules.md
  modified:
    - server/test_calendar_rules.py

key-decisions:
  - "All 113 old checks map 1:1 to 113 new pytest test functions - no consolidation and no parametrization, matching the baseline transcript exactly (every check() call, including the 4 nested inside the ambiguity fixture's `if/else` branch, printed exactly one PASS line)."
  - "test_unresolvable_hostname_refused (baseline check 35) needed a real behavioural fix, not just a mechanical transform: it originally relied on socket.getaddrinfo() raising socket.gaierror for the RFC 2606 \".invalid\" reserved hostname via a genuine (if doomed) DNS lookup. conftest.py's autouse non-loopback DNS guard (plan 32-01) now raises NetworkAccessBlocked before the real resolver is ever reached, and calendar_rules._host_is_safe() only catches (socket.gaierror, UnicodeError, OSError) - not NetworkAccessBlocked - so the guard's exception propagated uncaught and the test failed. Fixed per the documented lesson (\"stub the lookup, never bypass the gate\"): the test now monkeypatches socket.getaddrinfo to raise socket.gaierror directly for the target hostname, exercising the exact code path _host_is_safe() actually depends on, deterministically, without needing any real or blocked DNS lookup."
  - "No @requires_non_root marker anywhere in this file (a deviation from the plan's planner_notes expectation of ~13 os.chmod-line root-safety wraps - see Deviations below): every mode-bit-dependent check in this harness (the umask tests, the 0600-at-creation-time spy, the drifted-permission refusal tests, the ordinary-house-idiom refusal test) asserts on `os.stat().st_mode` read through calendar_secret_mode_is_unsafe()'s own application-level policy check, which reports identically for root and non-root - unlike test_manual_resolutions.py's read-only-directory checks, nothing here depends on the OS actually ENFORCING a permission bit (which root bypasses). Confirmed empirically: the full suite passes both at euid 0 and under `runuser -u nobody`, with 113/113 passing and zero skips either way, matching the baseline's own root-euid capture (113/113, 0 FAIL, no root-sandbox notes)."
  - "Used an AST-based mechanical transform (not hand-editing 2,872 lines) for the same reason as plan 32-07: matched each check(label, fn) call to its helper FunctionDef (built in TRUE SOURCE ORDER via node.lineno sort, not ast.walk()'s traversal order - the first pass ordered the 4 ambiguity-branch checks incorrectly relative to their neighbours, since they are nested one level deeper inside an if/else and ast.walk() visits by tree structure, not physical line order; caught by cross-checking the ordered check-label list against the baseline transcript before writing any ledger row), then hand-wrote the 9 checks needing monkeypatch treatment and the one behavioural DNS-guard fix separately."

requirements-completed: []  # TST-02 spans plans 32-03..32-10 (this is 32-08 of 8; server/test_render.py and server/test_poll_loop.py remain in 32-09..32-10) - not (re-)marked by this plan per the "every plan it spans" rule. TST-03 was already completed by plan 32-01.

# Metrics
duration: ~55min
completed: 2026-09-23
---

# Phase 32 Plan 08: Migrate test_calendar_rules to pytest Summary

**server/test_calendar_rules.py's 113-check RFC 5545 parser/registry/fetch-hardening/matcher/secret-writer contract harness is now 113 real pytest test functions, one per baseline check, with the DNS-rebinding and secret-leak-containment checks converted to `monkeypatch` and one genuine behavioural fix for the autouse DNS guard's interaction with `_url_is_safe()`'s own exception handling.**

## Performance

- **Duration:** ~55 min
- **Tasks:** 1
- **Files modified:** 2 (1 test module + 1 new ledger fragment)

## Accomplishments
- Converted `server/test_calendar_rules.py` (2,872 lines, 113 `check()` calls covering `unfold_ics_lines()`/`split_property()`/`parse_ics_events()` parsing, the JSON registry writer/loader and rolling window, the fetch-throttle, `_url_is_safe()`'s SSRF/DNS-rebinding gate, `fetch_ics()`'s redirect/size/secret-leak hardening, `refresh_calendar_registry()`'s orchestration, `match_calendar_theme()`'s truth table and ambiguity handling, and `save_calendar_url()`'s 0600 writer/accessor pair) into 113 standalone pytest test functions, each carrying its old check label verbatim as the docstring.
- Built and ran an AST-based transform: matched each `check(label, fn)` call (collected in true source-line order, correcting a first-pass bug where `ast.walk()`'s breadth-first traversal misordered the 4 checks nested inside an `if/else` ambiguity-fixture branch) to its helper `FunctionDef`, structurally unwrapped `tempfile.TemporaryDirectory()` blocks into `tmp = tmp_path` (or `tmp_path_factory.mktemp()` for the one test needing two independent directories), replaced every `return False, X` with `pytest.fail(X)` using the Return node's own source span (correctly capturing any grouping parens verbatim), and dropped every trailing `return True, ""` - 104 of the 113 checks needed only this mechanical treatment.
- Hand-converted 9 checks that manually saved/restored `socket.getaddrinfo`, `cr.os.chmod`/`cr.os.open`/`cr.os.replace`, `os.environ.get`, or `builtins.open` to use the `monkeypatch` fixture instead (MR-6), dropping their try/finally wrappers.
- Fixed a genuine DNS-guard interaction: `test_unresolvable_hostname_refused` (baseline check 35, RFC 2606 `.invalid`) now stubs `socket.getaddrinfo` to raise `socket.gaierror` directly, since the autouse non-loopback DNS guard (plan 32-01) now intercepts the lookup with `NetworkAccessBlocked` before the real resolver would ever report the failure `_url_is_safe()` actually catches.
- Promoted shared setup (module imports for `cr`/`device_config`, `fixture_text`, `CAL_THEME`/`CAL_CFG`/`MATCH_NOW`, the `_route()` helper, and the ambiguity fixture's `near_entry`/`far_entry`/`bbb_ory_entries`/`ambiguity_route`) from `main()`-local scope to module scope under identical names, so the 113 ported bodies needed zero identifier renaming.
- All 113 baseline checks verified mapped by `32-ledger-check.py`: 113/113, 113 ported, 0 deleted, 0 pending.
- Passes under both `-n 0` and `-n 4` (113 passed), as root and under `runuser -u nobody` (113 passed, 0 skips both ways), `ruff check` clean, legacy-runner bridge (`server/.venv/bin/python3 server/test_calendar_rules.py`) exits 0, zero `EXPECTED_CHECK_COUNT`/`def check(`/`tempfile.` occurrences, zero new untracked files after a fresh run, zero production-code changes, zero `enable_socket` markers.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_calendar_rules** - `effb563` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/test_calendar_rules.py` - 113 `test_*` functions; module docstring trimmed of the ~68-line `EXPECTED_CHECK_COUNT` phase/plan/ticket changelog (MR-10); `cr`/`device_config` now top-level imports; `fixture_text`/`CAL_THEME`/`CAL_CFG`/`MATCH_NOW`/`_route()`/the ambiguity fixture promoted to module scope
- `.planning/phases/32-test-foundation-pytest-and-ci-you-can-trust/32-ledger/server__test_calendar_rules.md` (new) - 113 rows, all `ported`

## Decisions Made
- No consolidation and no parametrization anywhere in this migration - every one of the 113 old checks printed exactly one baseline line and became exactly one node id, matching the plan's ledger 1:1 requirement.
- Chose an AST-driven mechanical transform over hand-editing given the file's size (2,872 lines, the second-largest of the 15 harnesses) and check count (113, third-highest): the transform's correctness was verified structurally (every generated function's `Return` replacement round-tripped from the original AST span) and behaviourally (all 113 tests pass, ledger checker confirms 113/113 label-for-label against the baseline transcript in original order).
- Deviated from the plan's `planner_notes` expectation of needing `@requires_non_root` for "13 os.chmod lines": on inspection, the actual `os.chmod()` call count is 4 (plus a `cr.os.chmod` spy that never really calls it), and every one of them - along with the umask tests - asserts on `os.stat().st_mode` through the module's own `calendar_secret_mode_is_unsafe()` policy function, which is euid-independent. Confirmed by running the full suite under `runuser -u nobody`: 113/113 pass with 0 skips, matching the baseline's own clean euid-0 capture. See `<planner_notes>`'s specific incorrect line count as the likely source of the mismatch.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] test_unresolvable_hostname_refused relied on real DNS resolution behaviour that the new guard shadows**
- **Found during:** Task 1, first full test run (`pytest -n 0`)
- **Issue:** The original check called `cr._url_is_safe("https://this-genuinely-does-not-resolve.invalid/a.ics")` expecting `_url_is_safe()`'s own `except (socket.gaierror, UnicodeError, OSError):` clause to catch the real resolver's failure for the RFC 2606 `.invalid` reserved TLD. Under the migrated test suite, `conftest.py`'s autouse `_block_non_loopback_dns` fixture (plan 32-01) intercepts `socket.getaddrinfo()` for any non-loopback host and raises `skypane_test_support.NetworkAccessBlocked` (a plain `RuntimeError` subclass) BEFORE the real resolver is ever reached - an exception type `_url_is_safe()`'s except clause does not catch, so it propagated uncaught and failed the test.
- **Fix:** Added a `monkeypatch` fixture parameter and stubbed `socket.getaddrinfo` to raise `socket.gaierror` directly for the target hostname - the exact exception type the production code's own except clause is written to handle, deterministically reproducing "this hostname does not resolve" without depending on real (now-blocked) DNS behaviour or bypassing the guard.
- **Files modified:** `server/test_calendar_rules.py`
- **Verification:** `pytest server/test_calendar_rules.py -q -p no:cacheprovider` and `-n 4`, both 113 passed; `runuser -u nobody` run also 113 passed.
- **Committed in:** `effb563` (part of task commit)

## Issues Encountered

None beyond the one auto-fixed DNS-guard interaction above and the ast.walk()-ordering self-correction made before any file was written (see key-decisions).

## Next Phase Readiness
- 8 of 15 server-side harnesses now migrated (7 through 32-07, plus `server/test_calendar_rules.py` from this plan) - 482 of 769 baseline checks. `server/test_render.py` (32-09, 140 checks) and `server/test_poll_loop.py` (32-10, 110 checks) remain.
- The corrected AST-based mechanical-transform approach (check() calls collected in TRUE SOURCE ORDER via `node.lineno`, not `ast.walk()`'s traversal order; Return-node replacement via the statement's own source span) and the monkeypatch-conversion pattern for manual save/restore dances are both reusable by 32-09/32-10 if either harness has similar closures or nested branches.
- No blockers. TST-02 stays "Pending" in REQUIREMENTS.md (2 more harnesses to go); TST-03 was already "Complete" from plan 32-01.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

`server/test_calendar_rules.py`, the ledger fragment, and this summary confirmed present on
disk; task commit hash (`effb563`) confirmed present in `git log --oneline --all`.
