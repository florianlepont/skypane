---
phase: 45-controlled-second-discharge-study
verified: 2026-10-12T00:00:00Z
status: passed
score: 3/3 success criteria verified in the repository; owner-reported physical facts not independently verifiable
gaps: []
human_verification:
  - test: "Owner confirms the physical-run facts that exist only as owner statements"
    result: "Confirmed by the owner in chat on 2026-10-12"
  - test: "Owner accepts 'depleted' as the recorded end_reason for a park end (3296 mV, not 0 %)"
    result: "Accepted by the owner in chat on 2026-10-12, as a park end with the nuance kept in Results"
---

# Phase 45 Verification

Goal: the owner can reproduce a second battery-discharge study whose evidence is comparable to run one and usable for a two-run model.

## Independent re-run
`run-report` on `battery-run2-export.jsonl` with `battery-run2-params.json`, writing to scratchpad: exit 1 (verdict fail, not refusal). Output file is byte-identical to `hardware/logs/battery-run2-report.json` (sha256 f58fbd2e...57bc). Export sha256 540d8f56...efdb matches report and Results. `python3 -m pytest hardware -q` (server/.venv python): 62 passed. No repo files were changed.

## Success criteria
1. Materially different cadence, comparable workload: VERIFIED. Configured 60 s vs run one's 300 s. Effective mean gap 74.04 s (about 4.4x faster than run one's 328 s). Same pack and firmware family; one fw version (fw-v1.0.2) throughout; baseline PASS. Comparability caveats (post-Phase-34 firmware, unknown refresh share) are pre-registered and carried to Phase 46, not hidden.
2. Study identifies cadence, baseline, window, endpoints, raw export: VERIFIED. Results table gives configured/reference/effective gap, fw and server revision, window 2026-10-05T14:08:05Z to 2026-10-12T16:22:02Z (7.093 d), endpoints (first 4106, open 4008.1, close 3415.0, last 3296), export file with sha256. Every number in `## Run 2 Results` was compared to the report and matches (coverage 0.946/6148/6501.8, 5.97, 0.811/6.97, 74.04/418, +5.8 %, 45 parked, 0.488 mAh/cycle, 569.5 mAh/day).
3. Separate continuity and voltage-validity evidence: VERIFIED. Distinct verdict blocks in the report and distinct sections in Results (continuity FAIL, voltage validity PASS, baseline PASS), each with check-level reasons. A failed gate is a legitimate recorded result per protocol. The criterion asks for inspectable evidence, not a pass.

## Plan must_haves (45-04) and protocol integrity
- Results only from tool output: met; owner/diagnosis items are labelled.
- Freeze before verdict: params with `reference_interval_s` 70 committed in 1893ca57, before adbcfaca (report). The later params diff touched only end/restore fields and `end_time_utc`; the reference value is unchanged. Tool check "frozen equals recomputed from first 48 h" PASS.
- Thresholds not retuned (0.95 / 3 / 100 / 3400 in report).
- No two-run model or policy decision written (Phase 46 deferred): met.
- Boot witness: report says "not computable", anticipated as known limitation 3.

## Honesty checks
- End at park, not 0 %: stated explicitly in Run Conditions and Results. `end_reason: depleted` is a tool-enum workaround, justified in text (last 3296 mV <= 3400 mV). Not a gap; flagged for owner acceptance. Consequence: no zero-percent time, so Phase 46 must use the normal-window comparison (which the protocol already prescribes).
- Coverage diagnosis (mean gap +5.8 % over reference, drift per section 4a): consistent with the report (70/74.04 = 0.9455).
- Largest-gap diagnosis, re-derived from the export: 22 gaps above 210 s in the normal window, 13 at 381-383 s and 9 at 416-418 s, max 418 s, 2-7 per day over 2026-10-05..10. Matches the text, and it is labelled as not from the report and a hypothesis. Note, weakly: those 22 gaps explain only part of the +5.8 % mean-gap drift, which the text attributes to drift generally; it does not claim otherwise.
- ROADMAP/STATE vs summaries are consistent: plans 4/4, phase "verification pending", REQUIREMENTS BAT-01/02 still Pending (to be flipped after this verification).

## Minor inconsistencies (non-blocking, warnings)
- `45-VALIDATION.md` frontmatter still says "planned ... 45-03 physical run pending" and its D-11 row says "freeze pending the run". Stale; update to complete.
- ROADMAP phase-level checkbox for Phase 45 and REQUIREMENTS BAT-01/02 remain unchecked/Pending pending this verification.

## Could not verify
Physical-run facts (owner-reported), the VPS-side export query, deployed server revision (read from GitHub Actions), the 48 h export file (kept off-repo, only its hash is recorded), and commit order beyond git history (confirmed via git log).

## Owner acceptance (2026-10-12)
The owner confirmed in chat both human-verification items: the owner-reported physical facts, and `end_reason: depleted` accepted as a park end (last reading 3296 mV, not 0 %). Status moved from human_needed to passed.
