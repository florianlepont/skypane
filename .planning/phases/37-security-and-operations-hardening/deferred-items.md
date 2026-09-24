# Phase 37 — Deferred items (out of scope for the current plan)

## 37-01: two legacy-harness WR-11 checks fail under a root euid

**Found during:** 37-01 Task 2, running `./scripts/run-all-tests.sh` as part of
verification.

**What:** `companion/test_companion_app.py` (318/320) and
`companion/test_status_pages.py` (316/317) each fail one check that
simulates a write failure with `os.chmod(dir, 0o500)` and expects the
subsequent write to fail. Root ignores permission bits, so the write
succeeds and the check gets the wrong flash key / outcome.

**Why out of scope:** unrelated to SEC-01 (LoginThrottle/`--bind`) — no
code this plan touches is involved. Already discovered and documented in
`32-REVIEW.md` ("Migrated tests handle this with `@requires_non_root`,
but legacy harnesses have no equivalent, so running
`./scripts/run-all-tests.sh` in a root container is red."). The fix
(porting `@requires_non_root`-equivalent skip logic into the two legacy
`check()`/`EXPECTED_CHECK_COUNT` harnesses, or migrating them to pytest
outright) is Phase 33 scope, not this plan's.

**Verified pre-existing, not introduced by 37-01:** the failing check
counts (318/320, 316/317) match `32-REVIEW.md`'s own record exactly.

**Action:** none taken. Left for whichever plan migrates
`test_companion_app.py`/`test_status_pages.py` to native pytest (Phase
33) to add the `requires_non_root` skip in the process.
