# Phase 64: owner validation record (production steps)

Filled from the owner's own reports only. A row is `validated` only with owner
evidence (date and the evidence itself); everything else stays `open`. The agent
never lifts the production switch, never edits the production env file, never
merges and never approves a deploy.

## A. Written lift confirmation (criterion 4)

The agent must not proceed to lift anything without this.

| Field | Value | Status |
|-------|-------|--------|
| Owner's exact words | | open |
| Date | | open |
| Checked first: no second-type row in the production fleet database that should not start being served | | open |
| Lifted by the owner by hand (one line `SKYPANE_ENABLE_SECOND_HARDWARE=1` in the production env file, units restarted) | | open |

## B. First typed release (criterion 2 and 3)

| Field | Value | Status |
|-------|-------|--------|
| Tag | fw-v1.2.0 | observed by the agent on GitHub, 2026-11-15 |
| Release URL | https://github.com/florianlepont/skypane/releases/tag/fw-v1.2.0 | observed by the agent |
| Live frame assets present (`skypane-fw-v1.2.0.bin`, `release.json`) | yes | observed by the agent |
| Second board assets present (`skypane-seeed-ee04-7in3-spectra6-fw-v1.2.0.bin`, `release-seeed-ee04-7in3-spectra6.json`) | yes | observed by the agent |
| Deploy run after the release (workflow_dispatch of ci.yml) | run 43711943313, conclusion success | observed by the agent |
| Import log line for the second type (a "skipped" notice while the switch is closed, none after the lift and a new deploy) | | open |
| `registry.seeed-ee04-7in3-spectra6.json` exists on the VPS after the first deploy following the lift | | open |

## B2. Frame prepared for production

Bench images use throwaway keys and would reject a production-signed OTA.

| Field | Value | Status |
|-------|-------|--------|
| Frame MAC | | open |
| Image flashed carries the production firmware key (how it was obtained and flashed) | | open |
| Production server trusts that key | | open |
| Guarded `provision.sh` run (no refusal, live frame's port and MAC untouched) | | open |
| Paired on the production server; shown as a second-type row in the production fleet database | | open |

## C. Real signed OTA over https (criterion 5)

| Field | Value | Status |
|-------|-------|--------|
| Frame firmware before | | open |
| Version offered and scheduled on the Update page | | open |
| https channel confirmed | | open |
| Frame firmware after | | open |
| Registry `last_outcome` and `installed_at` in `registry.seeed-ee04-7in3-spectra6.json` | | open |
| Result recorded by the production poll (not only by the live frame's cycle) | | open |

## D. Failing update keeps the previous firmware (criterion 5)

| Field | Value | Status |
|-------|-------|--------|
| How the failure was provoked (bench method) | | open |
| Frame stayed on the previous firmware | | open |
| Registry shows the attempt and no `installed_at` | | open |

## E. Open items

(To be listed when the owner reports.)
