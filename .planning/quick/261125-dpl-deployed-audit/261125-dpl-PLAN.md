---
type: quick
id: 261125-dpl
description: Record the owner-run capture of the deployed site (2026-11-25) in the Phase 68.1 consistency check and deviation register
---

<objective>
DSY-01 needs the design system checked against the deployed site. The owner ran capture_pages.py --remote against https://skypane.algernon.is with an administrator session. Write the result into the phase folder and settle it in the register. Audit documents only: no product file, no baseline, no checkbox.
</objective>

<tasks>
<task type="auto">
  <name>Task 1: 68.1-CHECK-C-deployed.md</name>
  <read_first>68.1-CHECK-A-system.md, 68.1-CHECK-B-pages.md, 68.1-DEVIATIONS.md, the findings list given in the executor prompt, the matrix (scratchpad, read-only)</read_first>
  <action>Write the deployed-site check: coverage (what was and was not visited), a MATCH/DEVIATION table per finding, confirmation or non-reproduction of each local finding, new findings, what remains unverified. Redact every e-mail address, frame name and user name; commit no screenshot, no matrix, no digest.</action>
  <acceptance_criteria>the file exists, contains no "@" character, lists the unverified cells, and every finding names its DEV row</acceptance_criteria>
</task>
<task type="auto">
  <name>Task 2: register and CI-needed cells</name>
  <read_first>68.1-DEVIATIONS.md, 68.1-CHECK-B-pages.md</read_first>
  <action>Add new DEV rows (continuing the numbering) for new findings with where / system says / site does / decision using the plan-03 rules (a visible pixel change is OWNER-QUESTION, never FIX-SITE). Update the existing rows confirmed or not reproduced on the deployed site. Update the CI-needed table of CHECK-B: close the cells now measured, keep the open ones open. Keep the coverage check of plan 03 passing.</action>
  <acceptance_criteria>every new finding has a DEV row with a decision; the register coverage loop still passes; open cells are listed</acceptance_criteria>
</task>
</tasks>
