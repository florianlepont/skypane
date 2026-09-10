---
phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh
plan: 01
subsystem: server
tags: [os.open, file-permissions, secrets, calendar, security]

requires:
  - phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
    provides: "calendar_rules.py's registry (write_calendar_registry, load_calendar_registry), fetch and match machinery this plan's writer sits beside"
provides:
  - "save_calendar_url(state_dir, value, now=None) — creates/replaces/clears the calendar feed URL at a dedicated 0600 file, erasing the fetched registry on every call"
  - "calendar_secret_path(state_dir), CALENDAR_SECRET_FILENAME, CLEAR_CALENDAR_URL sentinel"
  - "calendar_secret_mode_is_unsafe(state_dir) — narrow predicate for a drifted (group/other-readable) secret file"
affects: [17-02, 17-03, 17-04]

tech-stack:
  added: []
  patterns:
    - "os.open(tmp, O_WRONLY|O_CREAT|O_EXCL, 0o600) + os.fdopen() for a secret file, instead of this codebase's usual open(tmp, 'w') tmp-write idiom — mode is a creation-time argument, never a follow-up os.chmod()"
    - "three-valued private helper (None/True/False) distinguishing 'absent' from 'safe' from 'unsafe' permission state, consumed by a narrow public bool predicate compared with `is False`, never a bare negation"

key-files:
  created: []
  modified:
    - server/plane/calendar_rules.py
    - server/test_calendar_rules.py

key-decisions:
  - "Deferred the plan's instructed `import stat` from Task 1 to Task 2, where it is first used — Task 1 alone would otherwise leave an unused-import ruff F401 finding, violating the hard 'ruff clean before every commit' constraint"
  - "Strengthened the plan's suggested os.replace()-wrapper mid-write check by additionally spying on os.open()'s own mode argument and adding a dedicated never-calls-os.chmod() check — verified by mutation that the os.replace()-only approach cannot distinguish 'created at 0600' from 'created wide, chmod'ed to 0600 before the rename', both of which read 0600 by rename time"

requirements-completed: []

coverage:
  - id: D1
    description: "save_calendar_url() creates the secret file at mode 0600, set at creation (os.open's own mode argument), never via a follow-up chmod, and this holds under umask 022, under umask 027, and when the rename lands on a pre-existing group-readable file"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py — 'passes 0o600 as os.open()'s own mode argument...', '...never calls os.chmod()...', '...umask of 022', '...umask of 027', '...pre-existing group-readable file'"
        status: pass
    human_judgment: false
  - id: D2
    description: "calendar_secret_mode_is_unsafe() flags a file created through the codebase's ordinary umask-inheriting idiom (0o644, 0o640, 0o604, 0o660) as unsafe, reports 0o600/0o400 as safe, and reports False (not a permission problem) for an absent file"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py — 'reports True for a file created through this codebase's ordinary umask-inheriting house idiom...', '...is a genuine bool False...on a state dir with no secret file'"
        status: pass
    human_judgment: false
  - id: D3
    description: "Every successful save_calendar_url() call (set, replace, clear) erases the fetched calendar registry before touching the secret file, so no previous calendar's flights survive a change (D-04/D-05)"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py — 'erases the fetched registry...on setting a URL for the first time or replacing one...(D-05)', '...erases the fetched registry and removes the secret file in the same call (D-04)'"
        status: pass
    human_judgment: false
  - id: D4
    description: "save_calendar_url() never raises and returns True/False for every combination of clear sentinel, valid URL, None, empty string, whitespace-only string and non-string value, leaving an existing secret file and registry byte-identical on rejection"
    verification:
      - kind: unit
        ref: "server/test_calendar_rules.py — 'returns False and leaves an existing secret file's bytes and mode, and a seeded registry, untouched...', 'no file matching the temporary-name shape remains...', 'strips leading/trailing whitespace...', 'the literal string...takes the ordinary write branch...'"
        status: pass
    human_judgment: false

patterns-established:
  - "A secret file's mode must be proven by spying on the creating syscall's own mode argument (or a never-calls-chmod assertion), not merely by re-stating the file's mode at some later point — the latter cannot distinguish a correct creation-time mode from a permission-widening window later 'fixed' before anything else observes it"

duration: ~35min
completed: 2026-09-09
status: complete
---

# Phase 17 Plan 01: The 0600 secret writer, its drift guard, and the erase-on-change behaviour Summary

**`save_calendar_url()` writes the operator's calendar feed URL to a dedicated file created at `os.open(..., 0o600)` — never chmod'ed afterwards — erasing the fetched flight registry before every set/replace/clear, plus a narrow `calendar_secret_mode_is_unsafe()` guard that flags (never repairs) a drifted mode.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 3/3
- **Files modified:** 2

## Accomplishments
- `save_calendar_url(state_dir, value, now=None)` in `server/plane/calendar_rules.py`: creates the calendar URL secret file at mode `0o600` set at the moment of creation (`os.open(tmp, O_WRONLY|O_CREAT|O_EXCL, 0o600)` + `os.fdopen`), never via a later permission change; erases the fetched registry (`write_calendar_registry(state_dir, [], None, None, now=now)`) FIRST on every branch (set, replace, clear); never acquires `_WRITE_LOCK` itself (avoiding a deadlock against `write_calendar_registry()`'s own acquisition); never raises.
- `CLEAR_CALENDAR_URL = object()` — identity-compared clear sentinel, `device_config.CLEAR_THEME_ARRIVING`'s shape verbatim.
- `calendar_secret_path(state_dir)` — fixed-filename join, mirroring `calendar_rules_path()`; the filename is never derived from caller input.
- `_calendar_secret_mode_is_safe(path)` / `calendar_secret_mode_is_unsafe(state_dir)`: a three-valued private helper (absent/safe/unsafe) behind a narrow public predicate, compared with `is False` (never a bare negation, since `not None` is `True` in Python and would misreport an absent file as a permission problem). Never opens the file's contents. Deliberately does not repair a drifted mode.
- 14 new checks in `server/test_calendar_rules.py` (80 → 94), every permission assertion reading `stat.S_IMODE(os.stat(path).st_mode)` against an explicit octal literal — never an owner-relative readability test.

## Task Commits

Each task was committed atomically:

1. **Task 1: The 0600 writer, its sentinel, and the registry erase that rides every change** - `f3cb4c1` (feat)
2. **Task 2: The permission guard and its narrow public predicate** - `44f58ae` (feat)
3. **Task 3: Permission-bit checks, the negative guard check, and the erase-on-change checks** - `36937e5` (test)

_No plan-metadata commit yet — this executor does not update STATE.md/ROADMAP.md; the orchestrator owns that write and its own final commit._

## Files Created/Modified
- `server/plane/calendar_rules.py` - `CALENDAR_SECRET_FILENAME`, `CLEAR_CALENDAR_URL`, `calendar_secret_path()`, `save_calendar_url()`, `_calendar_secret_mode_is_safe()`, `calendar_secret_mode_is_unsafe()`. `import stat` added (placed in Task 2, see deviation below). `calendar_is_configured()`, `configured_calendar_url()`, `refresh_calendar_registry()` and everything else are byte-identical to before this plan (verified via `git diff` grep for those function names — no hits).
- `server/test_calendar_rules.py` - 14 new checks; `EXPECTED_CHECK_COUNT` raised 80 → 94.

## Decisions Made
- **Deferred `import stat` from Task 1 to Task 2.** The plan's Task 1 action explicitly asked for `import stat` to be added there "since it is needed by Task 2 and belongs with this task's edit," but Task 1 alone doesn't use `stat`, so `server/.venv/bin/ruff check server/plane/calendar_rules.py` — which Task 1's own `<verify>` block runs — fails with `F401 imported but unused`. Since ruff-clean-before-every-commit is a hard constraint from this executor's operating instructions (and CI runs it as a separate blocking job per the plan's own stated Phase 15 precedent), the import was added in Task 2 instead, where `_calendar_secret_mode_is_safe()` first consumes it. Both tasks' own `<verify>` commands pass exactly as specified; only the physical location of one `import` line differs from the plan's literal instruction.
- **Strengthened the mid-write mode check beyond the plan's literal suggestion.** `17-01-PLAN.md`'s Task 3 action item 1 suggested wrapping `os.replace()` and reading the source file's mode at that point. Building that check first and mutation-testing it (per this executor's `<verify_your_own_work>` requirement) showed it does NOT catch the "move the mode to a post-write permission change" mutation the plan's own verification instructions ask to test: a file opened at the umask default, then `os.chmod()`'ed to `0o600` *before* the rename, still reads `0o600` at the moment `os.replace()` runs — indistinguishable from the correct implementation by that check alone. Replaced it with a check that spies on `os.open()`'s own `mode` argument (proving the mode is passed to the *creating* call, not merely present by the time of the rename) and added a second, dedicated check that `save_calendar_url()` never calls `os.chmod()` at all. This is a strictly stronger proof of D-01 than the plan's suggested shape and is the reason the final check count (94) is one higher than the plan's own worked example arithmetic (93) would suggest.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Deferred `import stat` to Task 2 to keep ruff clean per-commit**
- **Found during:** Task 1 verification (`server/.venv/bin/ruff check server/plane/calendar_rules.py`)
- **Issue:** Plan's Task 1 action instructed adding `import stat` in Task 1 even though nothing in Task 1 uses it, producing an F401 unused-import finding that fails Task 1's own `<verify>` command and the harness's hard "ruff clean before every commit" requirement.
- **Fix:** Added `import stat` in Task 2 instead, at the point of first use.
- **Files modified:** `server/plane/calendar_rules.py`
- **Verification:** `server/.venv/bin/ruff check server/plane/calendar_rules.py` is clean after both Task 1 and Task 2 commits individually.
- **Committed in:** `f3cb4c1` (Task 1, import omitted), `44f58ae` (Task 2, import added)

**2. [Rule 1 - Bug] Strengthened a test check that mutation testing showed was vacuous against the exact mutation the plan asks to guard against**
- **Found during:** Task 3's mandated mutation-testing pass (`<verify_your_own_work>`)
- **Issue:** The plan's suggested "wrap `os.replace()` and observe the source file's mode" check for T-17-MODE does not fail when the mode is applied via a post-write `os.chmod()` immediately before the rename — both the correct implementation and this anti-pattern read `0o600` by the time `os.replace()` runs. A check that passes against this specific mutation would certify the exact bug D-01 exists to prevent.
- **Fix:** Rewrote the check to spy on `os.open()`'s own `mode` argument (proving the mode is an argument to the *creating* call) and added a second, dedicated check asserting `save_calendar_url()` never calls `os.chmod()` at all.
- **Files modified:** `server/test_calendar_rules.py`
- **Verification:** Both new checks fail against the `os.open(tmp, "w")` + `os.chmod(tmp, 0o600)` mutation (see Mutation Testing below) and pass against the correct implementation.
- **Committed in:** `36937e5` (Task 3)

---

**Total deviations:** 2 auto-fixed (1 blocking/ruff-cleanliness, 1 bug/vacuous-check). Both are process corrections within Task 3's own mandated self-verification step and Task 1's own `<verify>` requirement — no scope creep, no architectural change, no file outside the plan's declared `files_modified` touched.

## Mutation Testing

Two deliberate mutations were applied to `server/plane/calendar_rules.py`, run against the harness, and reverted (`git diff` against the pre-mutation commit confirmed byte-identical restoration each time):

1. **`0o600` → `0o644`** in the `os.open()` call. Caught by 6 checks: the os.open()-mode-argument check, both umask checks (022 and 027), the pre-existing-group-readable-destination check, the clear-branch-idempotency check's setup assertion, and the content-round-trip check's trailing mode assertion. Result: `87/93` (pre-strengthening) then `88/94` (post-strengthening) — i.e. every mode-adjacent check went red.
2. **Move the mode to a post-write permission change** (`open(tmp, "w")` + `os.chmod(tmp, 0o600)` instead of `os.open(tmp, O_CREAT|O_EXCL, 0o600)`). This is the mutation that motivated the Task 3 deviation above: the originally-planned os.replace()-wrapper check did NOT fail against it (both record `0o600` at rename time). After strengthening, two checks fail: "passes 0o600 as os.open()'s own mode argument..." (`os.open()` is never called at all — the file uses the builtin `open()`) and "never calls os.chmod() at all" (records exactly one `os.chmod()` call on the temporary file). Result: `92/94`.

Both mutations were reverted; the harness returns to `94/94` and `git diff` against the committed state is empty before proceeding to the next task/final verification.

## Issues Encountered
None beyond the two deviations documented above, both discovered and resolved within this plan's own verification steps.

## User Setup Required
None - no external service configuration required. This plan is purely additive; nothing is wired to the new functions yet (per the plan's own objective — the accessors, poll loop, and Settings page are untouched).

## Next Phase Readiness
- `save_calendar_url()`, `calendar_secret_path()`, `CALENDAR_SECRET_FILENAME`, `CLEAR_CALENDAR_URL`, `_calendar_secret_mode_is_safe()` and `calendar_secret_mode_is_unsafe()` exist, are tested, and are ready for plan 17-02 (the read path: `calendar_is_configured()` / `configured_calendar_url()` swap from the environment variable to this file, threading `state_dir` through every call site, and wiring the mode guard into the read path) per `17-CONTEXT.md`'s D-02/D-03/D-08.
- `calendar_is_configured()`, `configured_calendar_url()`, `CALENDAR_URL_ENV_VAR`, `refresh_calendar_registry()`, `server/poll_loop.py` and everything under `companion/`/`deploy/` are confirmed untouched by this plan (verified via targeted `git diff` grep for each name — zero hits).
- Full suite green: `bash scripts/run-all-tests.sh` reports `Result: PASS` across all 18 harnesses at 92% coverage. `server/.venv/bin/ruff check .` is clean repo-wide.
- No blockers for 17-02.

## Self-Check: PASSED

- FOUND: server/plane/calendar_rules.py
- FOUND: server/test_calendar_rules.py
- FOUND: .planning/phases/17-connect-a-calendar-from-the-companion-instead-of-over-ssh/17-01-SUMMARY.md
- FOUND: f3cb4c1
- FOUND: 44f58ae
- FOUND: 36937e5
- FOUND: 2b0e2dc

---
*Phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh*
*Completed: 2026-09-09*
