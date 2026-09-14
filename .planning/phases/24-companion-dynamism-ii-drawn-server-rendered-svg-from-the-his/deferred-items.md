# Deferred items — phase 24

Out-of-scope discoveries logged rather than fixed, per the executor's
scope boundary. Nothing here was caused by the plan that recorded it.

## 24-05: two timing-sensitive checks in companion/test_browser_ux.py

Both appeared during 24-05's MUTATION runs (where a mutated stylesheet
shifts frame timing) and in neither of that plan's clean runs, which were
59/59 twice. Neither check touches the battery chart.

1. `...the reminder stays within 48px...` (B10/X9/D-04, 22-14-PLAN.md
   Task 2) — failed once with `got 48.1875`, i.e. 0.19px over a hard
   48px ceiling. A sub-pixel text-metric boundary, not a layout change.

2. `the live theme preview CROSSFADES...` (D3/CFG-32, T-23-38,
   23-10-PLAN.md Task 2) — failed once with `got opacity 1 with
   transition '0.18s'`, i.e. the "two frames after selection" sample
   landed before the transition started rather than mid-fade.

Both read as boundary/timing flakes. Whoever owns the next sweep should
decide whether to widen the sample window (2) and the ceiling's tolerance
(1), or to accept them; 24-05 did not touch either and did not fix them.
