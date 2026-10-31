# Phase 52: Discussion Log

Human reference only; not consumed by downstream agents.

| Area | Question | Chosen |
|------|----------|--------|
| Corroboration | Providers per zone | Both always (D-04) |
| Provider failure | Behaviour after failure | Persisted ~60 s pause (D-06) |
| Priority | Order when over capacity | Live-frame zone first, then oldest-served (D-07) |
| Inactive devices | Budget for silent devices | Skipped after 7 days (D-08) |
| Poll now | No slot free | Owner: remove poll now entirely (D-10) |
| Poll now | Cooldown | Removed with the feature |
| Poll now removal | Scope | Complete removal; FLT-02 amended |
| Poll now removal | Conflicts with Phase 55 | Do it last, separate commit (D-11) |
| Zone key | Grouping | Exact centre + radius (D-12) |
| adsbdb | Phase 52 role | Deduplicate, cache unchanged (D-13) |
