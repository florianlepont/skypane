# Deferred Items — Phase 13

Out-of-scope discoveries logged per the executor's scope-boundary rule
(not fixed here; unrelated to the current task's own changes).

## 13-04: intermittent `scripts/run-all-tests.sh` failure, unrelated to this plan's files

**Discovered during:** 13-04 Task 2 verification (`scripts/run-all-tests.sh`).

**Symptom:** `companion/test_status_pages.py`'s check
`"the battery readout carries its id, role=\"status\", both value/detail
spans ... every chart hit target carries data-when ..."` (Health/Section 1,
`quick task 260901-uzi finding 3, Check 4`) intermittently fails with
`expected one data-when attribute per chart hit target, got 2` when the
harness runs inside `scripts/run-all-tests.sh`'s parallel/coverage-
instrumented run. It does not fail when
`server/.venv/bin/python3 companion/test_status_pages.py` is run standalone
(146/146 pass, repeatedly).

**Confirmed not caused by this plan's changes:** re-ran
`scripts/run-all-tests.sh` with 13-04's Task 2 changes stashed (only
Task 1's already-committed changes present) and the same failure
reproduced identically — the battery-trend chart code
(`companion/pages/health_page.py`) is untouched by 13-04, and this
failure is unrelated to `companion/pages/airlines_page.py`,
`companion/static/style.css`, or `companion/test_status_pages.py`'s own
new phase-13 checks (all of which pass in the same run).

**Likely cause (not investigated further, out of scope):** parallel
harness execution / coverage instrumentation timing affecting the
battery-trend chart's hit-target rendering, or a shared fixture/port
collision between concurrently-running harness subprocesses.

**Action:** none taken here. Flag for a future phase or a dedicated debug
session if it starts failing standalone or blocking CI.
