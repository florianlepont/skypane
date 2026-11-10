---
phase: 63-fast-ci
plan: 06
status: executed
requirements: [CIS-01, CIS-05]
---

# Plan 63-06 Summary

Five consecutive green runs of the final pipeline, median 9.0 min (6.2 to 9.1) against 27.4 min before; every number is in `63-TIMINGS.md` ("Five consecutive green runs", "Before and after").

- Two of the five runs are manual dispatches of the branch, because documentation-only pushes do not start the workflow; they run the same jobs.
- `CONTRIBUTING.md` documents the layout, the required aggregate check name, the combined floor, the local variables (`SKYPANE_TEST_GROUP`, `SKYPANE_TEST_SHARD`, `SKYPANE_JUNIT_XML`; partial runs always write coverage data only, so there is no separate data-only variable) and how to change a shard count. `deploy/README.md` describes only the deploy job, so it is unchanged. The `ci.yml` header comment was updated (comment only).
- The median is under 10 minutes with little margin; the remaining spread is the `playwright install --with-deps` step (see `63-TIMINGS.md`).
