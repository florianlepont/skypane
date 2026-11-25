---
phase: 70-private-repository-and-ci
plan: 04
subsystem: docs
tags: [signing, docs, firmware-release]
requires: [70-01, 70-03]
provides: [Mac signing runbook, manual firmware release steps]
key-files:
  modified: [firmware/SIGNING.md, deploy/README.md, deploy/tests/test_docs.py]
requirements: [PRV-01]
---

# Phase 70 Plan 04: Signing and release docs Summary

SIGNING.md and deploy/README.md now describe the real path (tag, build-only CI, signing and publishing with `scripts/fw_publish_signed.py` on the Mac, deploy started by hand); no text tells the reader to store the key in GitHub.

## Commits

- 75cdf16: SIGNING.md rewrite, `test_signing_md_documents_mac_signing`
- 56bf20d: deploy/README.md "Firmware releases (OTA)" steps 1-2, `test_firmware_releases_section_describes_the_manual_path`

## Details

- SIGNING.md: key custody is the Mac plus the offline backup; new `## Releasing (signing on the Mac)` (six steps, trust model, refusals, only the real flags `--key-file --repo --state-dir --platform --dry-run --yes`); rotation paragraph for a key once held in a secret; decision-record custody lines updated.
- README: steps 1-2 rewritten; permanent version-number sentence added; internal D-xx references in that section dropped.
- All existing pinned phrases kept.

## Deviations

- Beyond the plan's grep, the new test also asserts `firmware-signing` is absent from SIGNING.md (the old environment is gone everywhere in it).
- Two historical decision-record sentences mentioning the environment were reworded to match.

## Not run

No real signing, no `gh`, no workflow, no key touched. The worktree has no `server/.venv`; the main checkout's venv was used.

## Verification

deploy/tests plus stub-server/test_phase47_freeze.py: 398 passed, 1 skipped (pre-existing openssl backdating skip). ruff clean; check_comment_history check clean.
