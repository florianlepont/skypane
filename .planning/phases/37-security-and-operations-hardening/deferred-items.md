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

## 37-02: `test_status_pages.py`'s actual 316/317 failure is a stale sandbox
## path, not the WR-11 chmod check named above

**Found during:** 37-02 Task 1, running `companion/test_status_pages.py`
directly as part of verification (before and after this plan's own
`health_page.py` edits, to isolate cause).

**What:** the one failing check in this sandbox is
`"anomaly_active() runs on every page render and must never raise —
missing/empty/file/corrupt-db inputs all degrade safely"`'s first
assertion — `health_page.anomaly_active("/nonexistent/definitely-not-here")`
is expected to return `False` (a genuinely unopenable path degrades to
`_DB_UNAVAILABLE`, which every section builder reads as healthy) but
returns `True` here. Root cause: this sandbox already has a real
`/nonexistent/definitely-not-here/history.db` on disk (created by an
earlier session's run of this same check, root-owned, `sqlite3.connect()`
creating the file the moment the parent directory happens to already
exist) — so the path this check thinks is nonexistent is, in THIS
sandbox, a genuinely empty-but-writable directory instead, which the
check's own comment already documents as legitimately reading `"warn"`,
not `"ok"`.

**Why out of scope:** confirmed by running the check against both the
unmodified (`git show HEAD:`) and this plan's patched
`companion/pages/health_page.py` — identical failure, identical count
(316/317), on both. Not introduced by SEC-04/this plan; not fixable by
editing `health_page.py`, since the defect is stale on-disk sandbox
state from a prior test run using a hardcoded absolute path instead of a
`tempfile`-generated one. The prior 37-01-SUMMARY.md's "316/317, matches
32-REVIEW.md's own record" note conflated this with the WR-11 chmod
failure documented above for `test_companion_app.py` — that specific
chmod pattern does not actually exist in `test_status_pages.py`
(confirmed by grep); the count happened to match by coincidence.

**Action:** none taken (out of scope: fixing the check to use a
`tempfile`-generated definitely-nonexistent path, or cleaning the stale
sandbox directory, is Phase 33 scope alongside the other `run-all-
tests.sh`-under-root gaps already tracked above).
