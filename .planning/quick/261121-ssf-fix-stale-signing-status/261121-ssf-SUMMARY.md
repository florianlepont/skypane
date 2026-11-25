---
quick_id: 261121-ssf
date: 2026-11-21
status: complete
---

# Quick 261121-ssf: fix the stale signing status paragraph

`firmware/SIGNING.md` "Per-type releases" now carries a dated (2026-11-21) status: the
release workflow builds both boards and publishes the typed pair; `fw-v1.2.0` and
`fw-v1.2.1` carry both; the owner's EE04 was cable-flashed with `fw-v1.2.0`, updated
over the air to `fw-v1.2.1` on 2026-11-15 and runs it in production.

## Confirmed from files in the repository

- `.github/workflows/firmware-release.yml` builds the second board (`SKYPANE_BOARD: second`),
  signs it with the same key, verifies it, generates `release-seeed-ee04-7in3-spectra6.json`,
  copies the image to `skypane-seeed-ee04-7in3-spectra6-${GITHUB_REF_NAME}.bin` and passes
  both to `gh release create`.
- Tags `fw-v1.2.0` and `fw-v1.2.1` exist locally (`git tag -l 'fw-v*'`).

## Rest on the records only (no GitHub or VPS access here)

- That `fw-v1.2.0` carries the typed assets: `64-OWNER-VALIDATION.md` section B ("observed
  by the agent on GitHub", 2026-11-15). That `fw-v1.2.1` does too: the same file's section C
  (second-type frame downloaded `fw/06c18206...bin`, release asset digest) and the deploy
  import; the asset names and its 2026-11-15 date come from the brief and these records.
- The OTA and the production run: owner reports plus the production journal and registry
  pasted by the owner (`64-OWNER-VALIDATION.md` section C), summarised in `64-VERIFICATION.md`.
- The 1118208 byte size of the fw-v1.2.1 asset was NOT confirmed: the only 1118208 in the
  records is the read-back of the dev image cable-flashed on 2026-11-14
  (`hardware/SECOND-HARDWARE-VALIDATION.md`). It is therefore not stated in SIGNING.md.

## Other statements scanned

- Left alone: "Not proven without hardware" and the "Legacy-only earlier evidence" note in
  "Verification status". They concern the bench procedure for the signature decision; the
  Bench results table already records the 2026-11-14 EE04 pass, and rewriting that section is
  a larger editorial change than this status fix. Possibly worth a follow-up.
- No other "not yet published/built" wording in `SIGNING.md`.
- Out of scope, not touched: `deploy/README.md` line ~606 still says "the first typed release
  is not yet published, and the switch is closed in production" (stale for the same reason).
- Out of scope per the brief: `64-VERIFICATION.md` line 45 ("Achieved apart from the stale
  `firmware/SIGNING.md` status paragraph") still mentions the paragraph.

`python3 scripts/check_comment_history.py check` passes.

Files: `firmware/SIGNING.md`, the Phase 64 VERIFICATION (open point 10), root `STATE.md`.
