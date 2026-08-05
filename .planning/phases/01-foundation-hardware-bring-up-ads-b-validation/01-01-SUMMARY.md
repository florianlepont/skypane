---
phase: 01-foundation-hardware-bring-up-ads-b-validation
plan: 01
subsystem: infra
tags: [hardware, bom, procurement, seeed, xiao-esp32s3, ee02, kubii]

# Dependency graph
requires: []
provides:
  - "Priced, budget-checked Phase 1 bill of materials at hardware/BOM.md"
  - "Verified battery connector pitch (JST 2.0mm) and polarity (negative near USB-C) for the XIAO ESP32-S3 Plus board"
  - "Placed orders: Seeed Studio EE02 kit (order <seeed-order-ref>) and Kubii battery+cable bundle (order <kubii-order-ref>)"
  - "Documented hardware Unblock Date (2026-08-26) gating plans 01-06 and 01-07"
affects: [01-06-first-light, 01-07-backoff-validation]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: [hardware/BOM.md]
  modified: [hardware/BOM.md]

key-decisions:
  - "EE02 bundle (board + panel on one Seeed SKU) ordered as a single unit rather than sub-items separately — no cheaper unbundled path exists on Seeed's site"
  - "Battery pack and USB-C cable counted inside the EUR 300 display+compute ceiling (conservative choice) even though they are technically accessories"
  - "Battery connector pitch (JST 2.0mm) and polarity (negative pin nearest USB-C) verified against two independent Seeed wiki sources before ordering, per the plan's irreversible-mistake guard"
  - "EE02 kit delivery estimate recorded as a working-day-derived calendar window (2026-08-14 to 2026-08-26) rather than a single date, since the vendor quoted a 7-15 working-day range at checkout"
  - "Unblock Date corrected to name only 01-06 and 01-07 as hardware-gated, not 01-05 — 01-05 was already completed via a containerized ESP-IDF build with no physical-hardware dependency"

requirements-completed: [DEVICE-05]

coverage:
  - id: D1
    description: "Phase 1 BOM (hardware/BOM.md) prices and budget-checks the exact XIAO ESP32-S3 Plus + EE02 kit, battery, and cable, with battery connector polarity verified against Seeed's own documentation"
    requirement: "DEVICE-05"
    verification:
      - kind: other
        ref: "grep -qF 'EE02' hardware/BOM.md && grep -qE '300' hardware/BOM.md && grep -qiE 'polarit' hardware/BOM.md && grep -qF 'D-04' hardware/BOM.md"
        status: pass
    human_judgment: false
  - id: D2
    description: "Hardware orders placed (Seeed EE02 kit order <seeed-order-ref>, Kubii battery+cable order <kubii-order-ref>) with order numbers and delivery estimates recorded in hardware/BOM.md Order Tracking, plus an Unblock Date section naming the plans it gates"
    requirement: "DEVICE-05"
    verification:
      - kind: other
        ref: "grep -A20 '## Order Tracking' hardware/BOM.md shows no remaining PENDING for order number/estimated delivery on the EE02 kit and battery rows; grep -q '## Unblock Date' hardware/BOM.md"
        status: pass
    human_judgment: true
    rationale: "Confirming the actual orders were placed with a real vendor and real payment is a human action Claude cannot verify independently of the developer's report — the developer's confirmation (order numbers, payment accepted) is the source of truth recorded here."

duration: 12min
completed: 2026-08-05
status: complete
---

# Phase 1 Plan 1: Hardware Bill of Materials & Orders Summary

**Priced, budget-checked BOM for the XIAO ESP32-S3 Plus + EE02 kit and LiPo battery, with both orders placed and tracked (Seeed <seeed-order-ref>, Kubii <kubii-order-ref>), unblocking plans 01-06/01-07 by 2026-08-26**

## Performance

- **Duration:** 12 min (Task 2 continuation session)
- **Started:** 2026-08-05T00:00:00Z (approx, continuation of prior session)
- **Completed:** 2026-08-05
- **Tasks:** 2 (Task 1 completed in a prior session; Task 2 completed in this session)
- **Files modified:** 1 (`hardware/BOM.md`)

## Accomplishments
- Filled in `hardware/BOM.md`'s `## Order Tracking` table with real order numbers, order dates, and estimated delivery windows for both the Seeed EE02 kit and the Kubii battery+cable order
- Documented that the single Kubii order (<kubii-order-ref>) covers both the battery pack and USB-C cable together, rather than treating them as two separate orders
- Converted Seeed's checkout-stated "7-15 working days" shipping estimate into a calendar delivery window (2026-08-14 to 2026-08-26) anchored to the 2026-08-05 order date
- Appended a `## Unblock Date` section naming 2026-08-26 as the hardware unblock date and correctly scoping it to only the plans still gated by physical hardware arrival (01-06, 01-07) — explicitly correcting the plan's original text, which had also named 01-05 as gated, since 01-05 was completed in the interim without needing physical hardware

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the priced, budget-checked bill of materials** - `928942b` (feat) — completed in a prior session
2. **Task 2: Place the hardware orders and record delivery estimates** - `8bc5f41` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `hardware/BOM.md` - Order Tracking table populated with real Seeed and Kubii order numbers/dates/delivery estimates; new `## Unblock Date` section appended

## Decisions Made
- Recorded the EE02 kit's delivery estimate as a range (2026-08-14 to 2026-08-26), not a single date, because the vendor's own checkout language ("7-15 working days") is a range, not a fixed commitment — collapsing it to one date would overstate certainty
- Treated 2026-08-26 (the later/conservative end of the EE02 window) as the phase Unblock Date, since it is later than the Kubii order's 2026-08-08 estimate and thus the actual binding constraint
- Corrected the Unblock Date section's plan list from the plan's original {01-05, 01-06, 01-07} to {01-06, 01-07} only, reflecting that 01-05 (device firmware) was completed via containerized build + host tests with no physical-hardware dependency, per `01-05-SUMMARY.md`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug/Inaccuracy] Corrected the plan's stated Unblock Date plan list**
- **Found during:** Task 2 (Unblock Date section authoring)
- **Issue:** The plan's `<action>` text for Task 2 instructed naming plans 01-05, 01-06, and 01-07 as gated by the hardware Unblock Date. That assumption was accurate when the plan was written but became stale — plan 01-05 was completed and committed in the interim (see `.planning/phases/01-foundation-hardware-bring-up-ads-b-validation/01-05-SUMMARY.md`), and it never actually depended on physical hardware arriving (only a containerized ESP-IDF build and host-side tests). Listing 01-05 as still hardware-gated would have been factually wrong and could mislead future session planning.
- **Fix:** Wrote the `## Unblock Date` section naming only 01-06 and 01-07 as gated, with an explicit "Correction to the plan's original assumption" paragraph explaining why 01-05 was dropped and citing the SUMMARY that proves it's already done.
- **Files modified:** `hardware/BOM.md`
- **Verification:** `grep -q '## Unblock Date' hardware/BOM.md` succeeds; section text names only 01-06/01-07 as gated and cites `01-05-SUMMARY.md`.
- **Committed in:** `8bc5f41` (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 correction of a stale plan assumption)
**Impact on plan:** Necessary for accuracy — leaving the stale 01-05 reference in place would have misrepresented phase status to anyone reading the BOM later. No scope creep; this was documentation correction directly within Task 2's own action, not new work.

## Issues Encountered
None.

## User Setup Required
None - the developer already completed the external purchase actions (placing the Seeed and Kubii orders) before this session; this session only recorded the results in git.

## Next Phase Readiness
- Both hardware orders are placed and tracked; the phase has a documented, conservative unblock date (2026-08-26) for 01-06 and 01-07
- 01-05 is already complete and does not need to wait on this date
- Plan 01-05's arrival checkpoint (if any) should fill in the `Arrived on` column of `## Order Tracking` once hardware physically arrives — currently `PENDING`
- No blockers introduced by this plan; budget headroom (~€93 vs the €300 ceiling) remains as computed in Task 1

---
*Phase: 01-foundation-hardware-bring-up-ads-b-validation*
*Completed: 2026-08-05*

## Self-Check: PASSED

- FOUND: hardware/BOM.md
- FOUND: .planning/phases/01-foundation-hardware-bring-up-ads-b-validation/01-01-SUMMARY.md
- FOUND commit: 928942b (Task 1)
- FOUND commit: 8bc5f41 (Task 2)
- Order Tracking table: Order number and Estimated delivery columns fully populated for both vendor orders (no remaining PENDING); only the `Arrived on` column retains PENDING, as expected per plan design (filled by a later arrival checkpoint)
