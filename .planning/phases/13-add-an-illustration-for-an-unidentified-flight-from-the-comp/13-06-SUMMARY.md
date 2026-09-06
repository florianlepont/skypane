---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
plan: 06
subsystem: api
tags: [python, stdlib-only, http, security, path-traversal, csrf]

requires:
  - phase: 13-01
    provides: "server/plane/manual_resolutions.py's full public surface (load_manual_resolutions()/illustration_key_for_name()/add_entry()/delete_entry()/normalise_prefix())"
  - phase: 13-04
    provides: "companion/pages/airlines_page.py's unresolved_row_for_prefix() (D-11's single membership test), RESOLVE_ROUTE/MANUAL_DELETE_ROUTE_PREFIX/MANUAL_DELETE_ROUTE_SUFFIX/AIRLINES_ROUTE/RESOLVE_QUERY_PARAM, and the eight FLASH_MANUAL_* string constants"
provides:
  - "companion/app.py's _illustration_filenames(state_dir=None) — the widened, per-request union of the vendored target set and server-persisted manual-resolution keys, replacing the import-time module constant (D-09, reopens and re-establishes T-v26-02-01)"
  - "companion/app.py's eight FLASH_KEY_MANUAL_* flash keys, rebound from airlines_page and wired into FLASH_MESSAGES/FLASH_ROLES with 13-UI-SPEC.md's approved copy"
  - "page_context()'s two new ctx keys: resolve_prefix (raw, unvalidated ?resolve= value) and manual_resolutions (the loaded registry, read fresh per request)"
  - "companion/pages/__init__.py documents both new ctx keys in its established bullet style"
  - "Handler._handle_manual_resolve_post() — POST /airlines/resolve, Step A of the two-step resolve flow (D-03/D-07/D-11)"
  - "Handler._handle_manual_resolution_delete(prefix) — POST /airlines/manual-resolutions/{prefix}/delete (D-08)"
affects: []

tech-stack:
  added: []
  patterns:
    - "Per-request membership-set union replacing an import-time frozenset constant — the same validate-then-join shape _serve_illustration_image() already used, now computed fresh each request because its second source (manual_resolutions.json) is mutable, matching device_config.load_device_config()'s own per-request-read posture"
    - "Explicit if/elif branch-per-value result mapping (never a dict.get() lookup) for add_entry()'s ADD_* result constants, so an unrecognised value cannot silently pass through with no flash"
    - "An app.py-owned POST handler (not a page module's handle_post()) for a route that must choose between two redirect targets — sibling to the existing _handle_poll_now()/_handle_illustration_replace() pattern rather than the documented handle_post(form, ctx) -> flash_key contract, which returns only a flash key"

key-files:
  created: []
  modified:
    - companion/app.py
    - companion/pages/__init__.py
    - companion/test_companion_app.py

key-decisions:
  - "companion/pages/__init__.py's ctx-contract test check deliberately excludes the pre-existing 'health_state' key from its documented-keys assertion — that key is real in page_context()'s return but was never added to this docstring's bullet list by an earlier phase; fixing that gap is out of this plan's scope (deviation-rules scope boundary), so the check documents only the two ctx keys this plan itself adds, rather than papering over or silently including an undocumented pre-existing key"
  - "Task 3's rejection-mapping test seeds two ADD_OK entries (D-03's brand-new-name and already-covered-name branches) before filling the registry to its 200-entry cap, and computes the cap-fill count as MANUAL_RESOLUTION_MAX_ENTRIES minus the registry's current size rather than a hardcoded 200 — filling a fixed 200 after two prior successful adds would itself start returning ADD_REJECTED_FULL mid test-setup"

requirements-completed: []

coverage:
  - id: D1
    description: "_illustration_filenames() is a per-request union of the static target set and server-persisted manual keys (D-09); both _serve_illustration_image() and _handle_illustration_replace() read it per request; the import-time module constant is gone"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_illustration_filenames_union_contract"
        status: pass
    human_judgment: false
  - id: D2
    description: "An upload for a manual key no prior request registered is impossible in a single request and leaves the override directory unchanged (Pitfall 3's warning sign, made executable); the read path 404s for a registered-but-artless key exactly like an unknown key"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_illustration_manual_key_read_path_states, #_illustration_manual_key_post_unregistered_then_registered"
        status: pass
    human_judgment: false
  - id: D3
    description: "The upload pipeline inside _handle_illustration_replace() is untouched except its membership lookup and the paragraph documenting it; server/plane/illustrations.py remains byte-for-byte unchanged (D-09 standing gate)"
    verification:
      - kind: unit
        ref: "git diff -- companion/app.py (no change to the pipeline's executable lines); server/test_illustrations.py (58/58); git diff --stat -- server/plane/illustrations.py (empty)"
        status: pass
    human_judgment: false
  - id: D4
    description: "All eight FLASH_KEY_MANUAL_* keys resolve to 13-UI-SPEC.md's approved copy byte for byte (the six deck strings) with the correct ARIA role, and no message carries a runtime placeholder except the pre-existing cooldown key"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_flash_manual_keys_complete_and_byte_identical"
        status: pass
    human_judgment: false
  - id: D5
    description: "page_context() supplies resolve_prefix (raw, unvalidated) and manual_resolutions (loaded fresh per request) on a ?resolve=XYZ request; companion/pages/__init__.py documents both, and a harness check keeps that documentation honest against the real ctx dict"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_page_context_supplies_resolve_prefix_and_manual_resolutions"
        status: pass
    human_judgment: false
  - id: D6
    description: "POST /airlines/resolve re-validates the prefix against the live unresolved-prefix registry before writing (D-11), uses only the validated value downstream, maps every add_entry() rejection to its own distinct flash key, and branches its success redirect on whether the named airline already has artwork (D-03)"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_manual_resolve_post_revalidates_prefix_against_live_registry, #_manual_resolve_post_rejection_mapping_and_d03_branch"
        status: pass
    human_judgment: false
  - id: D7
    description: "POST /airlines/manual-resolutions/{prefix}/delete removes the registry entry and leaves the override image on disk (D-08), provably, through the real route; it is idempotent and does not membership-test against the unresolved-prefix registry"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_manual_resolution_delete_route_full_contract"
        status: pass
    human_judgment: false
  - id: D8
    description: "Both new routes sit behind require_session(), checked before any registry read or write; an unauthenticated POST writes nothing to manual_resolutions.json"
    verification:
      - kind: unit
        ref: "companion/test_companion_app.py#_manual_resolve_and_delete_routes_require_auth_and_write_nothing"
        status: pass
    human_judgment: false

duration: 22min
completed: 2026-09-06
status: complete
---

# Phase 13 Plan 06: Wire the resolve surface to storage — widened membership set + two POST routes Summary

**`_illustration_filenames()` becomes a per-request union of the vendored illustration set and `manual_resolutions.json`'s server-persisted keys (D-09), and two new authenticated POST routes — `/airlines/resolve` (D-03/D-11) and `/airlines/manual-resolutions/{prefix}/delete` (D-08) — close the loop between Health's coverage-gap list and Airlines' resolve form, re-establishing threat T-v26-02-01 under a wider closed set instead of relaxing it.**

## Performance

- **Duration:** ~22 min
- **Started:** 2026-09-06T00:30Z (context load, following 13-04/13-05's completion)
- **Completed:** 2026-09-06T00:52Z
- **Tasks:** 3/3
- **Files modified:** 3 (`companion/app.py`, `companion/pages/__init__.py`, `companion/test_companion_app.py`)

## Accomplishments

- `_illustration_filenames(state_dir=None)` (Task 1): the module-level `_ILLUSTRATION_FILENAMES` constant, memoised once at import time, is gone. The function now returns a `frozenset` union of `illustrations.target_filenames()` and one `"{key}.png"` per valid entry in `manual_resolutions.load_manual_resolutions(state_dir)` — computed fresh on every call, because the second source is mutable. Both `_serve_illustration_image()` and `_handle_illustration_replace()` call it per request. The rewritten docstring documents the security argument in full: the manual half is read from state a *prior*, authenticated Step A request durably persisted — never derived from the current request — which is what re-establishes `T-v26-02-01` under a wider set rather than relaxing it.
- `_handle_illustration_replace()`'s ordered security steps are untouched — the plan's own acceptance-criteria grep (matching every executable line of the upload pipeline against the pre-phase diff) confirms only the membership lookup and its documenting paragraph changed.
- `page_context()` (Task 2) gains `resolve_prefix` (the raw `?resolve=` value, deliberately unvalidated — validation is `airlines_page.unresolved_row_for_prefix()`'s job, shared by the render and write paths) and `manual_resolutions` (the registry, loaded fresh per request — never the poll cycle's process-scoped cache). No third query parameter was introduced and no illustration key ever travels in a URL. `companion/pages/__init__.py` documents both.
- Eight `FLASH_KEY_MANUAL_*` keys rebound from `airlines_page`, wired into `FLASH_MESSAGES` (the six UI-SPEC deck strings byte-identical, plus two planner-added failure keys in `FLASH_KEY_ILLUSTRATION_REPLACE_FAILED`'s own voice) and `FLASH_ROLES` ("status" for the one success key, "alert" for the other seven).
- `Handler._handle_manual_resolve_post()` (Task 3, POST `/airlines/resolve`): re-validates the hidden `prefix` field against the live unresolved-prefix registry via `unresolved_row_for_prefix()` before touching `add_entry()` — a stale/never-live prefix writes nothing. Every `add_entry()` rejection maps to its own flash key through an explicit branch (never a dict-driven lookup, so an unrecognised result can't silently pass through with no flash). On success, the illustration key is recomputed from the name that was *just persisted* (re-read from storage, never the form value) and the redirect branches on whether that airline already has artwork (D-03: no upload is ever asked for when the ladder already resolves).
- `Handler._handle_manual_resolution_delete(prefix)` (POST `/airlines/manual-resolutions/{prefix}/delete`): calls `delete_entry()` and nothing else — deliberately never membership-tests against the unresolved-prefix registry, since D-14 removes a resolved prefix from that registry the moment it starts working, which would otherwise make an entry undeletable exactly when D-08 needs it deletable. Idempotent on a second, identical delete.
- Both new `do_POST()` dispatch branches sit behind `require_session()` first, before any registry read or write — matching every other authenticated branch in the file. Neither route carries a CSRF token, following the file's single documented `SameSite=Strict` posture rather than inventing a second mechanism.
- `companion/test_companion_app.py` grew from 148 to 157 checks across the three tasks: the union contract, the manual-key read-path state machine, Pitfall 3's warning sign made executable, flash completeness, the ctx contract, the auth gate on both new routes (state dir provably unchanged, not only status codes), D-11 re-validation on write, the full rejection-to-flash mapping plus the D-03 branch, and D-08 through the real delete route.
- Standing gates held throughout: `server/plane/illustrations.py` untouched (`test_illustrations.py` still 58/58), `companion/test_status_pages.py` still 146/146, zero JavaScript, zero new dependencies, and `scripts/run-all-tests.sh` green across all 17 harnesses with the coverage threshold met.

## Task Commits

Each task was committed atomically:

1. **Task 1: Widen the illustration membership set to a per-request union of server-persisted keys (D-09)** — `278ca9a` (feat)
2. **Task 2: Thread three ctx keys and eight flash keys, and update the page-module contract** — `ba088a3` (feat)
3. **Task 3: Add POST /airlines/resolve and the manual-resolution delete route (D-03, D-07, D-08, D-11)** — `459d5d7` (feat)

**Plan metadata:** committed as part of this summary's own commit.

## Files Created/Modified

- `companion/app.py` — `_illustration_filenames(state_dir=None)` (widened union, replacing the import-time constant); eight `FLASH_KEY_MANUAL_*` rebindings + `FLASH_MESSAGES`/`FLASH_ROLES` entries; `page_context()`'s `resolve_prefix`/`manual_resolutions` ctx keys; `Handler._handle_manual_resolve_post()`; `Handler._handle_manual_resolution_delete()`; two new `do_POST()` dispatch branches; `_handle_illustration_replace()`'s docstring updated at its membership-test step only
- `companion/pages/__init__.py` — documents `resolve_prefix` and `manual_resolutions` in the module's established ctx-bullet style
- `companion/test_companion_app.py` — 148 → 157 checks (3 + 2 + 4 across the three tasks); new `_seed_unresolved_prefixes()` helper mirroring `test_status_pages.py`'s own; `EXPECTED_CHECK_COUNT` ledger extended per the file's established discipline

## Decisions Made

- The ctx-contract test (`_page_context_supplies_resolve_prefix_and_manual_resolutions`) deliberately omits the pre-existing `health_state` ctx key from its documented-keys assertion list, since that key is genuinely undocumented in `companion/pages/__init__.py` from an earlier phase and fixing that gap is out of this plan's scope — the check verifies only the ctx keys this plan itself adds and documents, per the deviation-rules scope boundary (fix only what the current task's changes caused).
- Task 3's rejection-mapping/D-03-branch test seeds two `ADD_OK` entries before filling the registry to its 200-entry cap, and computes the cap-fill count dynamically (`MANUAL_RESOLUTION_MAX_ENTRIES` minus the registry's current size) rather than assuming a fresh 200-entry fill — the two prior successful adds would otherwise make a fixed-200 fill loop itself hit `ADD_REJECTED_FULL` mid test-setup.
- The Task 1/3 illustration- and manual-resolution-writing checks each spin up their own isolated `Harness()` (mirroring the pre-existing `broken_harness`/`concurrent_harness` pattern) rather than reusing the shared Section-3 harness, since they write real files/JSON registries that would otherwise pollute assertions an unrelated, pre-existing check makes about the shared harness's state dir (e.g. "exactly one file in the override directory").

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A prose mention of `require_session()` in a new dispatch-branch comment inflated the acceptance-criteria's literal grep count**
- **Found during:** Task 3, while verifying the acceptance criterion `grep -c "require_session" companion/app.py` returns exactly `23` (21 pre-phase + 2, one per new dispatch branch).
- **Issue:** The first draft of the `POST /airlines/resolve` dispatch branch's comment used the literal substring "require_session()" in prose ("... — require_session() first, before any registry read or write ..."), which made the file-wide count `24` instead of the expected `23` — the comment's own mention counted as a third occurrence beyond the two real call sites.
- **Fix:** Reworded the comment to "the session gate runs first" (same meaning, no literal substring match), bringing the count back to exactly `23`.
- **Files modified:** `companion/app.py`.
- **Verification:** `grep -c "require_session" companion/app.py` returns `23`.
- **Committed in:** `459d5d7` (Task 3 commit).

**2. [Rule 1 - Bug] Task 1's two new illustration-manual-key checks initially wrote into the shared Section-3 harness's state dir, breaking a pre-existing, unrelated check**
- **Found during:** Task 1, first full test run.
- **Issue:** The initial draft of `_illustration_manual_key_read_path_states` and `_illustration_manual_key_post_unregistered_then_registered` used the shared `harness`/`session_cookie` (matching the surrounding illustration-route checks' own style), writing `skyward-air.png`/`boreal-wings.png` into `{harness.tmpdir}/illustration_overrides/`. This broke the pre-existing, correct check `"the upload was written to {state_dir}/illustration_overrides/air-france.png, and nothing else was created in that directory"`, which asserts the override directory holds exactly one file after the earlier D-03 round-trip check in the same section.
- **Fix:** Rewrote both new checks to spin up their own isolated `Harness()` instance (mirroring the file's own pre-existing `broken_harness`/`concurrent_harness` pattern for exactly this kind of state-polluting check), so neither touches the shared harness's state dir at all.
- **Files modified:** `companion/test_companion_app.py`.
- **Verification:** Full suite re-run: all 151 checks pass, including the previously-broken directory-exactly-one-file assertion.
- **Committed in:** `278ca9a` (Task 1 commit).

**3. [Rule 1 - Bug] Task 3's rejection/D-03-branch test filled the registry to a fixed 200 entries after two prior successful adds, over-filling the cap mid-setup**
- **Found during:** Task 3, first full test run.
- **Issue:** The initial draft generated exactly `MANUAL_RESOLUTION_MAX_ENTRIES` (200) new "Y??" prefixes to fill the registry to its cap, but the same check had already persisted two entries ("NEW" and "OLD") via the D-03-branch assertions immediately before the fill loop — bringing the total to 202, which made the loop's own `add_entry()` calls return `ADD_REJECTED_FULL` for its last two iterations instead of the expected `ADD_OK`, failing the test's own setup assertion.
- **Fix:** Reordered the D-03-branch assertions to run before the cap-fill (documented inline as required, since a full-cap registry cannot accept any further distinct prefix), and computed the cap-fill count as `MANUAL_RESOLUTION_MAX_ENTRIES` minus the registry's actual current size, so the fill always reaches exactly the cap regardless of how many entries earlier assertions in the same check already persisted.
- **Files modified:** `companion/test_companion_app.py`.
- **Verification:** Full suite re-run: all 157 checks pass, including the rejection-mapping/D-03-branch check.
- **Committed in:** `459d5d7` (Task 3 commit).

---

**Total deviations:** 3 auto-fixed (all Rule 1 — test/comment bugs caught and fixed before the task's own commit, no production-code defects).
**Impact on plan:** All three fixes were necessary for the plan's own acceptance criteria and test correctness. No scope creep — each fix stayed inside the file the triggering task already modified.

## Issues Encountered

None beyond the deviations above. The pre-existing, unrelated intermittent Health battery-chart flake (`companion/test_status_pages.py`, logged in `.planning/phases/13-.../deferred-items.md` by plan 13-04) was not encountered during this plan's test runs.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 13's full resolve flow is now wired end to end: Health's Resolve link → Airlines' Step A form (`POST /airlines/resolve`) → Step B upload (existing `POST /illustration/{key}.png`, now validated against the widened membership set) → the management list's delete control (`POST /airlines/manual-resolutions/{prefix}/delete`). This was the phase's last plan per `13-06-PLAN.md`'s own "Artifacts this phase produces" table — no sibling plan remains outstanding.
- `server/plane/illustrations.py` is untouched; the D-09 standing gate (58/58 `test_illustrations.py` checks, byte-identical file) held through every task and commit of this plan.
- No blockers. `scripts/run-all-tests.sh` reports all 17 harnesses green with the `pyproject.toml` coverage threshold met, confirming the whole phase's automated verification surface is intact.
- One pre-existing, out-of-scope documentation gap noted but not fixed (see Decisions Made): `companion/pages/__init__.py`'s ctx docstring does not document the `health_state` key that `page_context()` has returned since an earlier phase. A future housekeeping pass could add that bullet; it does not block anything phase 13 delivers.

---
*Phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp*
*Plan: 06*
*Completed: 2026-09-06*

## Self-Check: PASSED

All modified files (`companion/app.py`, `companion/pages/__init__.py`, `companion/test_companion_app.py`) and all three task commit hashes (`278ca9a`, `ba088a3`, `459d5d7`) verified present on disk / in git log.
