---
phase: 47-integrated-field-validation-and-decision-record
plan: 03
subsystem: hardware-docs
tags: [validation, owner-steps, battery-pack]
requires: []
provides:
  - hardware/PACK-ACCEPTANCE.md
  - hardware/FIELD-VALIDATION.md
  - hardware/FIELD-VALIDATION-FR.md
affects: [47-04, 47-05, 47-06]
key-files:
  created:
    - hardware/PACK-ACCEPTANCE.md
    - hardware/FIELD-VALIDATION.md
    - hardware/FIELD-VALIDATION-FR.md
metrics:
  completed: 2026-10-23
---

# Phase 47 Plan 03: Owner documents and evidence skeleton Summary

Three documents under `hardware/`: a pack acceptance checklist (status NOT RECEIVED), the evidence record skeleton (VAL-01..03 all pending), and a plain-French step sheet with one pinned export route.

## Commits

- 45cbddf3: PACK-ACCEPTANCE.md and FIELD-VALIDATION.md
- 9756726e: FIELD-VALIDATION-FR.md

Branch: `worktree-agent-a6cde9e53c3868358` (not pushed).

## Results

- Plan verify commands for both tasks pass (15 `A noter` lines in the French sheet).
- `python3 scripts/check_comment_history.py check` exits 0.
- The pytest suites under `hardware` could not be run here: the worktree has no `server/.venv` and the system python has no pytest. The change is documentation only and touches no code or tests.

## Deviations from Plan

None in substance. Notes:

- **Server address not recorded.** The repository records no SSH address for the server. `deploy/README.md` only uses `<vps-ip>`, and `skypane.algernon.ovh` appears only as the companion hostname, not stated as the SSH target. The French sheet therefore keeps the placeholder `<adresse du serveur>` and tells the owner to say so in chat if they no longer have it, so Claude asks for it. Nothing was invented.
- **Route form.** The documented script of `BATTERY-RUN.md` was pasted verbatim, with the ssh line changed to the `ubuntu@` plus `sudo python3 -` form of the 2026-10-08 section (the root form is refused, per `deploy/README.md`) and the redirect to the Desktop file added on the heredoc line. This exact command was not executed by Claude; it was not testable here (no server access).
- **Accents.** The French text uses accents, except the literal marker `A noter` that the plan's verify command greps for.
- The `<since>` value `2026-10-23T04:25:00Z` and the 500 to 550 line expectation are labelled arithmetic by Claude in the sheet. The conversion example in Partie C is labelled as an example with invented times, not the owner's data.
- Check 4 of the pack checklist: the board's charger current against a 10000 mAh pack is not documented in the repository, so the checklist says the check is recorded as `unverified` in that case.

## Known Stubs

`hardware/FIELD-VALIDATION.md` section bodies are intentionally empty ("To be filled by plan 47-0x"); they are the skeleton later plans fill. No result is claimed anywhere.

## Self-Check: PASSED

The three files exist and both commits are on the branch. `hardware/logtools.py` and 47-01 files were not touched.
