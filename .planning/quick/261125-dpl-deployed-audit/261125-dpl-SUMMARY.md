---
type: quick
id: 261125-dpl
status: complete
completed: 2026-11-25
---

# Quick 261125-dpl: deployed-site audit record

The owner's administrator-session capture of the production site (176 loaded cells of 200, GET only) is written into the Phase 68.1 folder. No screenshot, matrix or digest is committed; every address, frame and user name is redacted.

## Commits

- 2062d5ed: `68.1-CHECK-C-deployed.md` (coverage, MATCH/DEVIATION per axis, existing rows confirmed or not reproduced, new findings, unverified list).
- 795b99b1: register (`68.1-DEVIATIONS.md`) updated with deployed evidence, DEV-42 to DEV-44 added, counts and routing recomputed (44 rows); CHECK-B CI-needed list updated.

## Results

- New rows: DEV-42 (unnamed search input on Flights and Airlines, FIX-SITE), DEV-43 (80 chart points of 8x8px on the Battery page, RECORD-REASON), DEV-44 (Battery chart labels crossed by the line, OWNER-QUESTION).
- Confirmed on the deployed site: DEV-05, 18 (token values), 26, 27 (measured box), 29, 33, 34 (wider: ellipsis also on Live rows, Users, Fleet System), 36, 37, 39 (14 links, 9 inputs), 40, 41.
- Not reproduced: DEV-32 (FR access dialog 584px, no inner scroll), DEV-38 as "taller than the screen" (fits, scrolls inside; only the owner remark remains).
- Closed CI cells: B1-26, B2-11, B2-25, Home populated, Flights rows at 360, Editor unidentified rows.
- Navigation and the French "Airlines" label match the skill.

## Unverified

Plain-user role (DEV-30), More sheet, sign-in first-visit line, add-illustration dialog, pending frame page, retired header wording, all 1280 layouts (no screenshot), DEV-28/31/35, Location 1280 header text (no row), the Quiet-hours hit area, the identity of the unnamed Editor and Location inputs.

## Deviations from plan

None. No product file, baseline, checkbox, ROADMAP or STATE change.
