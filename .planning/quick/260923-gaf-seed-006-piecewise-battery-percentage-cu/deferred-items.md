# Deferred items — quick 260923-gaf

Out-of-scope discoveries logged per the executor's SCOPE BOUNDARY rule
(only auto-fix issues directly caused by this task's own changes).

## companion/test_browser_ux.py — 2 pre-existing check failures, unrelated to SEED-006

`./scripts/run-all-tests.sh` reports `companion/test_browser_ux.py` as the
sole failing harness (73/75), both in the full suite run and standalone.
Neither failing check touches battery, the discharge curve, or anything
this quick task modified:

1. `expected the typed value to be held by the field before any commit`
   (~line 2223) — the leave-guard/dirty-state check.
2. `expected the field to echo back the user's own rejected input '30',
   got '301800'` (~line 8234) — the wake-interval-s server-validation
   echo check. The got-value `'301800'` looks like the typed `'30'` was
   appended to, rather than replacing, the field's prior `'1800'`
   content — a field-clear/fill timing issue in the check itself or in
   the page under test, not a battery-percentage regression.

**Confirmed pre-existing:** re-ran `companion/test_browser_ux.py` against
this quick task's own commit `e3ce343` (Task 1, "replace linear battery
estimate with SEED-006 piecewise curve") in a throwaway detached
worktree — the SAME two checks fail there, byte-identically, before any
of Task 2's comment-only edits existed. Both runs (twice against the
working tree, once against e3ce343) produced the identical 73/75 with
the identical two failure messages, so this is reproducible rather than
a one-off flake, but it predates this quick task entirely and is out of
scope to fix here (config_page.py's wake_interval_s validation path and
the dirty-state bar are untouched by SEED-006).

Left unfixed, per the SCOPE BOUNDARY rule. Someone should open a
follow-up seed/quick task to investigate `_save_via_bar()`'s field-fill
sequencing (or the field's own `value` handling) around the
wake-interval-s inline-error path.
