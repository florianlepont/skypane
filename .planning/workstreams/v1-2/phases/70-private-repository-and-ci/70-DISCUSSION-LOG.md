# Phase 70: Private Repository and CI - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-11-24
**Phase:** 70-private-repository-and-ci
**Areas discussed:** CI location, reduced CI, GitHub plan, firmware signing

---

## CI location

| Option | Description | Selected |
|--------|-------------|----------|
| Runner on the owner's Mac | Free, fast, no extra server; needs isolation | ✓ |
| Second small server | Always on, monthly cost | |
| Hosted + reduced CI only | Nothing to run, but exceeds the quota | |

**User's choice:** asked first how far the quota would be exceeded; after the answer (60 billable minutes per run, 8 to 18 times the quota) accepted the Mac runner.
**Notes:** Overage and the postponed self-hosted charge were quantified in CONTEXT D-05 and D-06.

---

## Reduced CI

| Option | Description | Selected |
|--------|-------------|----------|
| Path-based splitting, no test skipped for code | | ✓ |
| Full CI every time | | |

**User's choice:** Yes (recommended).

---

## GitHub plan

| Option | Description | Selected |
|--------|-------------|----------|
| Stay Free | $0 | ✓ |
| Team + organisation | $4 per user per month; docs conflict on private environments | |

**User's choice:** asked whether an organisation can be personal (yes, one member) and whether Team would remove the overage (no, $18 of compute, about 3,000 minutes); then confirmed Free.

---

## Firmware signing

| Option | Description | Selected |
|--------|-------------|----------|
| A: Team with approvals | | |
| B: Free with repository secret | weaker | |
| C: sign on the Mac | key never leaves the Mac | ✓ |

**User's choice:** depended on the plan question; with Free, option C.

---

## Claude's Discretion

Workflow structure, runner installation, signing script interface, inventory format.

## Deferred Ideas

Team plan with a one-member organisation; second server for the runner.
