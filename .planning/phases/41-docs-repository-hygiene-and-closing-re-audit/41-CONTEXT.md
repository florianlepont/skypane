# Phase 41: Docs, repository hygiene and closing re-audit - Context

**Gathered:** 2026-09-28
**Status:** Ready for planning
**Source:** Orchestrator brief (audit remediation, last phase of v1.0) + developer answer (AskUserQuestion, 2026-09-28)

<domain>
## Phase Boundary

This is the last phase of the 2026-09-23 code audit's remediation arc
(Phases 32–41, milestone v1.0). Phases 32–40 are complete on `main`. This
phase closes the arc: DOC-01 (doc drift), DOC-02 (repository hygiene),
DOC-03 (closing re-audit of all 82 findings), plus three REQUIREMENTS.md
bookkeeping items surfaced in a 2026-09-2X audit-gap review.

The audit ledger (`.planning/audits/2026-09-23-code-audit.md`) lists known
DOC-01 examples from the *original* 2026-09-23 snapshot, but the codebase
has changed substantially across phases 34–40. Every doc claim must be
verified against the **current** code, not the ledger's original line
numbers or examples — the ledger names the *kind* of drift to hunt for
(bind address, "persists nothing", harness counts, file modes, state
paths, single-writer claims), not an exhaustive or current list.

This phase must NOT touch `firmware/` or the OTA-01..12 requirements —
Phase 42 (OTA, already planned, 16 plans/4 waves) owns that, and its gate
G-41 checks Phase 41 is complete on `main` before starting. Finishing this
phase cleanly and merging to `main` is the unblock for Phase 42.

</domain>

<decisions>
## Implementation Decisions

### DOC-01 — Doc/code alignment
- Read every doc the ledger names (`ARCHITECTURE.md`, `COMPLIANCE.md`,
  `README.md`, `.claude/CLAUDE.md`, `deploy/README.md`,
  `firmware/VENDOR.md` — firmware doc content only, no firmware code
  changes, `deploy/skypane.env.example`, `deploy/Caddyfile`, `ci.yml`) and
  cross-check every factual claim (bind addresses, "persists nothing" /
  "unmodified" claims, harness/check counts, file modes, state file paths,
  single-writer claims, and anything else found to have drifted) against
  the code as it stands now, after phases 32–40.
- Known starting points from the ledger's DOC-01 row (verify current
  status of each, don't assume the ledger's snapshot still applies):
  byos bind address (`ARCHITECTURE.md:47`, `deploy/README.md:30` claimed
  loopback vs actual bind), "persists nothing / unmodified"
  (`ARCHITECTURE.md:409-414`, `Caddyfile:52-56`, `skypane.env.example:86-89`
  vs `battery_state.json` existing), "single writer" claim
  (`poll_loop.py:1116` area — Phase 36/39 changed the writer model with
  `state_store.py` and `fcntl.flock`, re-check the claim's truth value
  after that), "18 harnesses" (`ci.yml` — obsolete after the pytest
  migration in Phase 32/33), log file mode (640 doc vs 660 actual, or
  whatever the current mode is), env path
  (`skypane.env.example:3`).
- Every correction must cite the current code location it was checked
  against (file:line or equivalent), not just restate the ledger.

### DOC-02 — Repository hygiene
- `hardware/logs/backoff-powercycle.log` (15.4 MB in the ledger's
  snapshot): gzip it **in the working tree only**. No git-history rewrite
  (decision D-A6 — the uncompressed blob stays reachable in past commits;
  only the current tree changes). Any doc/script/reference to this log's
  path or expected format must be checked and updated if the `.gz`
  extension changes how it's read/referenced.
- `_unresolved/air-caraibes-atr72-unused.png`: remove it from what gets
  deployed/shipped. Verify first whether it's still actually unused
  (grep all references) before deleting — the audit's snapshot may be
  stale.
- Archiving completed v1.0 phase directories via `/gsd-cleanup`: only do
  this if the milestone is actually being closed as part of this phase.
  Since Phase 42 (OTA) is already planned as part of the same v1.0
  roadmap arc and is meant to start right after this phase merges, this
  milestone is likely NOT being closed yet. Default to **not** running
  `/gsd-cleanup` and instead note archiving as the explicit next step in
  this phase's SUMMARY.md — unless research turns up clear evidence v1.0
  is closing now (e.g. Phase 42 is actually the *next* milestone rather
  than late in this one). Confirm the ROADMAP.md milestone boundary
  before deciding either way.

### DOC-03 — Closing re-audit
- Go through **every one of the 82 findings** (TST/FW/HYG/INT/SEC/EFF/
  ARC/CMP/DOC IDs) in `.planning/audits/2026-09-23-code-audit.md` AND
  their corresponding rows in `.planning/REQUIREMENTS.md`, and verify each
  is genuinely closed against the **current** code — not just that a
  checkbox is ticked or a phase SUMMARY.md claims it.
- For FW-* findings specifically: verification is READ-ONLY against
  firmware code (confirm the finding was addressed in Phase 34's actual
  commits) — do not modify anything under `firmware/`.
- Any finding that is NOT actually fixed, or is fixed differently than
  the ledger/REQUIREMENTS.md describes, must be flagged explicitly in the
  written closing report, not silently ticked or left ambiguous.
- Produce a written closing report (e.g. `41-CLOSING-AUDIT.md` in the
  phase directory, or folded into SUMMARY.md/VERIFICATION.md — planner's
  discretion on exact file, but it must exist as a reviewable artifact)
  that states, per finding ID: verified-closed / flagged-as-open /
  flagged-as-different-than-described, with the evidence checked.

### REQUIREMENTS.md bookkeeping (developer-confirmed, 2026-09-28 AskUserQuestion)
- **CFG-72**: tick the checkbox to `[x]` at REQUIREMENTS.md:98. Already
  documented as complete in the Phase 28 coverage table (REQUIREMENTS.md
  line ~353) — verify that entry still holds against current code, then
  just correct the checkbox to match.
- **CFG-73**: tick the checkbox to `[x]` at REQUIREMENTS.md:99. Same
  situation — already documented complete at line ~354, verify then
  correct the checkbox.
- **CFG-74**: leave completely as-is. Its checkbox stays `[ ]` and its
  text stays unchanged — it already explicitly documents its own
  "SUPERSEDED before implementation, never built" status in the
  requirement's own prose (REQUIREMENTS.md:100) and in the Phase 28
  coverage table (line ~355). The developer explicitly chose NOT to
  apply strikethrough or any other visual/textual change to this row.
  Do not touch it.
- **Do NOT touch CFG-34, CFG-37, CFG-39, CFG-42, CFG-50, CFG-52, CFG-65**
  — these need larger product decisions the developer hasn't made yet.
  Leave them exactly as they are, including their checkbox state.

### Out of scope (hard fence)
- Nothing under `firmware/` may be modified (docs referencing firmware
  behavior can be corrected; firmware source/config/tests cannot).
- No OTA-01..12 requirement work.
- No CFG-34/37/39/42/50/52/65 changes of any kind.
- This is a hygiene/verification phase: no new features, no refactors
  beyond what DOC-01/02/03 require.

### Closing out the phase
- Commit per plan, push to `claude/phase-41`, open a draft PR.
- Drive CI to green.
- Close the phase normally (SUMMARY.md, VERIFICATION.md).
- Because this closes the whole v1.0 audit-remediation arc (Phases
  32–41), the closing PR description must briefly summarize the full
  32–41 journey for the developer: what shipped per phase, and what is
  now provably closed per the DOC-03 closing report.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/audits/2026-09-23-code-audit.md` — the full ledger, all 82
  findings, decisions D-A1..D-A6, measured baseline
- `.planning/REQUIREMENTS.md` — CFG-72/73/74 rows and their Phase 28
  coverage-table entries (~lines 98-100, ~353-355); the audit remediation
  section for TST/FW/HYG/INT/SEC/EFF/ARC/CMP/DOC IDs
- `.planning/ROADMAP.md` — Phase 41 success criteria, milestone v1.0
  boundary, Phase 42 gate G-41
- `.planning/phases/32-*/` through `.planning/phases/40-*/` — SUMMARY.md
  and VERIFICATION.md of every phase in this arc, needed to verify DOC-03
  claims against what was actually built (not assumed)
- `.claude/CLAUDE.md` — conventions (English-only comments, no plan/
  ticket IDs in comments, stack table)
- `ARCHITECTURE.md`, `COMPLIANCE.md`, `README.md`, `deploy/README.md`,
  `firmware/VENDOR.md`, `deploy/skypane.env.example`, `deploy/Caddyfile`,
  `.github/workflows/ci.yml` — the doc surface DOC-01 must correct

</canonical_refs>

<specifics>
## Specific Ideas

- For DOC-03, an efficient approach is one pass per phase (32 through
  40), reading that phase's own SUMMARY.md/VERIFICATION.md plus the
  ledger rows it claims to close, then spot-checking the actual code —
  rather than 82 independent lookups with no grouping.
- `scripts/check_comment_history.py check` and the coverage/CI gates are
  themselves evidence sources for several TST-* and HYG-* rows — run them
  rather than re-deriving by hand where possible.

</specifics>

<deferred>
## Deferred Ideas

- Archiving v1.0 phase directories via `/gsd-cleanup` — deferred unless
  research shows the milestone is closing now (see DOC-02 decision above).
- CFG-34/37/39/42/50/52/65 — deferred to a future phase pending product
  decisions.

</deferred>

---

*Phase: 41-docs-repository-hygiene-and-closing-re-audit*
*Context gathered: 2026-09-28 from orchestrator brief + developer answer*
