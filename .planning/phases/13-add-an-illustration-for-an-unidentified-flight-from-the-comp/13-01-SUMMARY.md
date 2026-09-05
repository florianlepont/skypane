---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
plan: 01
subsystem: api
tags: [python, stdlib-only, json-registry, security, path-traversal]

requires: []
provides:
  - "server/plane/manual_resolutions.py — the project's first runtime-writable identity namespace (D-01/D-05): a state-dir-backed JSON registry mapping a 3-letter ICAO prefix to an operator-supplied airline name"
  - "server/test_manual_resolutions.py — 19/19-check contract harness proving D-08, atomicity, and the hostile-input sweep"
  - "scripts/run-all-tests.sh registers the new harness (17 harnesses total)"
affects: [13-02, 13-03, 13-04, 13-06]

tech-stack:
  added: []
  patterns:
    - "device_config.py's never-raising-load / tmp-write-then-os.replace() file contract, copied structurally for a second JSON registry"
    - "illustrations.set_override_state_dir()'s process-scoped-cache pattern, mirrored as set_manual_registry_state_dir()/airline_name_for_prefix() for once-per-poll-cycle reads"
    - "Two independent layers of path-traversal defence on a user-influenced filesystem key: a positive allowlist on the derived slug (_SAFE_KEY_RE) plus a raw-input hostile-shape check (_HOSTILE_NAME_RE) run before slugging, since normalise_airline_key()'s total ASCII-slug transform otherwise reduces a hostile path-shaped string to a harmless-looking slug"

key-files:
  created:
    - server/plane/manual_resolutions.py
    - server/test_manual_resolutions.py
  modified:
    - scripts/run-all-tests.sh

key-decisions:
  - "Added a second, independent input-safety layer (_HOSTILE_NAME_RE, checked inside illustration_key_for_name() against the raw airline_name before slugging) beyond the plan's literal _SAFE_KEY_RE-on-the-slug spec, because normalise_airline_key()'s existing total ASCII-slug transform always reduces a path-traversal-shaped string (e.g. \"../../etc/passwd\", \"a/b\") to an already-safe-looking slug (\"etc-passwd\", \"a-b\") that would pass _SAFE_KEY_RE unmodified — the plan's own Task 1 <behavior> block and Task 2's hostile-input sweep both require these exact inputs to be rejected, which the literal algorithm as described could not satisfy."

requirements-completed: []

coverage:
  - id: D1
    description: "manual_resolutions.py registry round-trips a manual resolution, degrades to {} on every malformed/hostile input, rejects reserved and traversal-shaped names, and hard-caps at 200 entries"
    verification:
      - kind: unit
        ref: "server/test_manual_resolutions.py (19/19 checks)"
        status: pass
    human_judgment: false
  - id: D2
    description: "delete_entry() provably leaves the override PNG on disk untouched (D-08), pinned to illustrations.override_path_for_key()"
    verification:
      - kind: unit
        ref: "server/test_manual_resolutions.py#_delete_entry_never_touches_override_file"
        status: pass
    human_judgment: false
  - id: D3
    description: "server/plane/illustrations.py remains byte-for-byte unchanged (D-09 standing gate); server/test_illustrations.py still 58/58"
    verification:
      - kind: unit
        ref: "server/test_illustrations.py (58/58 checks); git diff --stat -- server/plane/illustrations.py (empty)"
        status: pass
    human_judgment: false
  - id: D4
    description: "New harness registered in scripts/run-all-tests.sh; full suite (17 harnesses) passes"
    verification:
      - kind: integration
        ref: "scripts/run-all-tests.sh (17/17 harnesses run, 0 failed, coverage threshold met)"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-09-06
status: complete
---

# Phase 13 Plan 01: Manual resolution registry storage contract Summary

**`server/plane/manual_resolutions.py` — a state-dir-backed JSON registry (3-letter ICAO prefix → operator airline name) copying `device_config.py`'s file contract exactly, with a two-layer path-traversal defence and a hard 200-entry cap.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-09-06T00:35Z (context load)
- **Completed:** 2026-09-06T00:55Z
- **Tasks:** 3/3
- **Files modified:** 3 (2 created, 1 modified)

## Accomplishments
- `server/plane/manual_resolutions.py` created: 10 public functions, 7 `ADD_*` result constants, never-raising load, validate-before-write, tmp-write-then-`os.replace()` persistence, a process-scoped cache pair mirroring `illustrations.set_override_state_dir()`.
- `server/test_manual_resolutions.py` created: 19/19 checks, including the three named must-have proofs (D-08 override-survival, atomicity, hostile-input sweep), all as real filesystem assertions rather than source greps.
- `scripts/run-all-tests.sh` updated to run 17 harnesses (was 16); full suite verified green with the new harness in the run.
- `server/plane/illustrations.py` left byte-for-byte unchanged (D-09 standing gate verified every commit); `server/test_illustrations.py` still 58/58; `server/test_enrich.py` still 52/52.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create server/plane/manual_resolutions.py** — `8ee973b` (feat)
2. **Task 2: Create server/test_manual_resolutions.py** — `6bf139c` (test)
3. **Task 3: Register the new harness in scripts/run-all-tests.sh** — `276a2e8` (chore)

**Plan metadata:** committed as part of this summary's own commit.

## Files Created/Modified
- `server/plane/manual_resolutions.py` — the manual-resolution registry module (D-01/D-05/D-08/D-13)
- `server/test_manual_resolutions.py` — its contract harness (19/19 checks)
- `scripts/run-all-tests.sh` — HARNESSES array + self-description bumped to 17 files

## Decisions Made
- Added `_HOSTILE_NAME_RE` (mirroring `illustrations.py`'s own `_UNSAFE_KEY_RE` shape: `[\\/]|\.\.`) as a second, independent T-13-02 defence layer inside `illustration_key_for_name()`, checked against the **raw** `airline_name` before it is ever slugged. See Deviations below for the full rationale — this was required to satisfy the plan's own explicit behavior spec, not an unplanned scope addition.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug in plan's described algorithm] Path-traversal-shaped airline names would have slugged safely and been accepted, contradicting the plan's own required behavior**
- **Found during:** Task 1, while writing the behavior test for `add_entry(tmp, "AAA", "../../etc/passwd")`.
- **Issue:** The plan's `<action>` describes `illustration_key_for_name()` as rejecting a name only when `illustrations.normalise_airline_key()` returns `None` or the resulting slug fails `_SAFE_KEY_RE`. But `normalise_airline_key()` is a *total* function that strips every non-alphanumeric run down to a single hyphen — so `"../../etc/passwd"` slugs to `"etc-passwd"`, `"a/b"` slugs to `"a-b"`, and `"..\\..\\x"` slugs to `"x"`, all of which are well-formed, non-reserved slugs that pass `_SAFE_KEY_RE` cleanly. Per the literal algorithm, `add_entry()` would have returned `ADD_OK` for all three — directly contradicting Task 1's own `<behavior>` line ("a rejection, never `ADD_OK`") and Task 2's mandatory hostile-input sweep (which lists exactly these three strings and requires an `ADD_REJECTED_*` result for each). The threat model's own T-13-02 mitigation text ("Nothing containing a path separator or a parent-directory sequence can be stored") is also only true if such raw input is rejected outright, since the registry stores the raw (stripped) name as the display `airline_name`, not the derived slug.
- **Fix:** Added `_HOSTILE_NAME_RE = re.compile(r"[\\/]|\.\.")` (identical shape to `illustrations.py`'s own `_UNSAFE_KEY_RE`) and check it against the raw string inside `illustration_key_for_name()`, before calling `normalise_airline_key()`. This makes `illustration_key_for_name()` return `None` for any raw name containing a path separator or a parent-directory sequence, which `add_entry()` then reports as `ADD_REJECTED_NAME_EMPTY` (the existing "collapsed to nothing usable" bucket) and `load_manual_resolutions()` drops on read (defence in depth for a hand-edited file).
- **Files modified:** `server/plane/manual_resolutions.py` (same file, same commit as Task 1 — no separate commit).
- **Verification:** Confirmed via a full manual behavior sweep before writing the harness (all 19 `<behavior>` assertions from Task 1, run interactively) and then via `server/test_manual_resolutions.py`'s own hostile-input-sweep check (#19), which passes.
- **Committed in:** `8ee973b` (Task 1 commit).

**2. [Documented plan-spec inconsistency, no code change] Task 3's acceptance criterion `grep -c "server/test_manual_resolutions.py" ... returns 1` conflicts with the same task's own `<action>` instruction**
- **Found during:** Task 3, after adding the harness to both the `HARNESSES` array and the canonical-enumeration comment (per the explicit instruction to record the addition "matching the way that comment already records the phase-6 and 06.6.2-01 additions").
- **Issue:** Naming the new file explicitly in the comment (as instructed) makes `grep -c "server/test_manual_resolutions.py" scripts/run-all-tests.sh` return `2`, not the `1` the acceptance criteria list states. This is not a new problem: the identical precedent already exists for `companion/test_contrast_check.py` (added by 06.6.2-01) — `grep -c "companion/test_contrast_check.py" scripts/run-all-tests.sh` also returns `2` today, unrelated to this plan's changes.
- **Resolution:** Followed the explicit `<action>` instruction (name the file in the comment, matching established precedent) rather than the stricter literal grep count, since the two are mutually exclusive as written and the precedent this plan was told to match already produces a count of 2. No code change was needed to resolve this — it is a plan-authoring inconsistency, noted here for visibility, not a defect in the shipped file.
- **Files modified:** none beyond the already-planned `scripts/run-all-tests.sh` edit.
- **Committed in:** `276a2e8` (Task 3 commit).

---

**Total deviations:** 1 auto-fixed (Rule 1, security-relevant), 1 documented plan-spec inconsistency (no code impact).
**Impact on plan:** The Rule 1 fix is necessary for correctness against the plan's own explicit behavior spec and threat model claim — without it, a hostile-but-slug-safe airline name would have been silently persisted. No scope creep beyond what the plan's own test requirements demanded.

## Issues Encountered
None beyond the deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `server/plane/manual_resolutions.py`'s full public surface (10 functions, 7 `ADD_*` constants) is available for plan 13-03 (`enrich.py` wiring), 13-02 (health page link), 13-04 (Airlines page management list + upload), and 13-06 (companion route handlers) to build on, exactly as scoped in "Artifacts this phase produces."
- `illustration_key_for_name()` is the single sanctioned seam for turning a stored/candidate airline name into an illustration key — sibling plans should call it rather than re-deriving key logic.
- No blockers. `server/plane/illustrations.py` is untouched; the D-09 standing gate (58/58 `test_illustrations.py` checks, byte-identical file) holds and should continue to be checked in every subsequent plan of this phase.

---
*Phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp*
*Plan: 01*
*Completed: 2026-09-06*

## Self-Check: PASSED

All created files and task commit hashes verified present on disk / in git log.
