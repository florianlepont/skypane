# Phase 61 handoff (2026-11-09)

State when this session ended.

## Branch and PRs
- Branch `milestone/v1.2-phase-61-companion-ux`. Merged: #305-#307, #309, #310, #312, #313.
- PR #313 (round 12: design system and audit 3, plans 61-97 and 61-98) is merged
  (squash 684980b). No PR is open. The production deployments of #310, #312 and #313
  may still wait for the owner: he clicks "Review deployments -> production ->
  Approve and deploy" (the token gets 403).
- After a squash merge: `git fetch origin main && git merge -s ours origin/main`, then
  `git checkout origin/main -- .` and commit; push normally (force push is denied).
  Open a NEW draft PR for new work and subscribe to it.

## Standing rules (owner)
French answers, short messages, one question at a time, mockups before decisions,
no touching phase-47 files or `hardware/`, `stub-server/test_phase47_freeze.py` green,
live frame protocol untouched, tests are behaviour tests, comments carry no plan IDs,
`companion/app.py` <= 1500 lines, JS files <= 1500 lines, new UI uses the component
catalogue (`.claude/skills/sketch-findings-skypane/references/component-catalogue.md`).
Executors: `gsd-executor` agents briefed with the rules in the session scratchpad
(`executor-rules.md`, test cadence), one at a time on the shared branch.

## Open items
1. Home greeting: the owner finds the greeting line above the page ("Bon apres-midi
   Florian", small and grey, alone at the top) poor. Mockups shown: A big title, B date +
   title + summary, C no greeting on desktop, E greeting merged above the big state title
   (closest to what he imagined, but he is not convinced). Waiting for his direction.
2. Location map on iPhone shows dark bands above and below in a Safari tab (iOS 26
   Safari bars). Home Screen web-app mode was enabled in plan 61-93b; the owner has to
   test from the Home Screen icon. Optional: tint the bands to match the map.
3. Needs a real device: blue flash on tab change, bottom shadow, backdrop-filter cost,
   yellow Full/Soft-stripe contrast (1.12) on the panel.
4. Not planned: canvas map markers, duplicated airport JSON, Airline editor page weight
   (695 KB), content-visibility, hand-built `banner__pill` markup on a few pages,
   space-switch and place-modes geometry on the shared segmented control.
5. Phase 61 closes only after the owner's final validation (plan 61-13); then update
   the phase-61 lines in ROADMAP.md, STATE.md and REQUIREMENTS.md (executors must not).

## Reports
Audit 3 (visual 29, performance 26, workflows 272 with 14 partial): published as an
artifact (private) and kept in the session scratchpad only; the decisions are in
`61-OWNER-VALIDATION.md` (D51) and `61-BATCH3-PLAN.md` (batch 15).
