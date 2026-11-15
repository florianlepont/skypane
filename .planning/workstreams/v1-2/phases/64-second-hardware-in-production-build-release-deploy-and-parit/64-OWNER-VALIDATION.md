# Phase 64: owner validation record (production steps)

Filled from the owner's own reports only. A row is `validated` only with owner
evidence (date and the evidence itself); everything else stays `open`. The agent
never lifts the production switch, never edits the production env file, never
merges and never approves a deploy.

## A. Written lift confirmation (criterion 4)

The agent must not proceed to lift anything without this.

| Field | Value | Status |
|-------|-------|--------|
| Owner's exact words | "Je lève le verrou du second type en production" (French, as typed in the session; recorded verbatim) | given by the owner |
| Date | 2026-11-15 | given by the owner |
| Measured values behind the confirmation | Full refresh time 25 / 27 / 27 s and flash size 16 MB measured on the unit; battery sense, LED, buttons and the separate panel busy waits still provisional (hardware/SECOND-HARDWARE-MEASUREMENTS.md) | recorded by the agent |
| Checked first: no second-type row in the production fleet database that should not start being served | | open |
| Lifted by the owner by hand (one line `SKYPANE_ENABLE_SECOND_HARDWARE=1` in the production env file, units restarted) | Owner reported "oui, c'est fait" (line added and services restarted), 2026-11-15; the deploy log that follows shows the switch was read (typed release imported) | owner-reported, consistent with the deploy log |

## B. First typed release (criterion 2 and 3)

| Field | Value | Status |
|-------|-------|--------|
| Tag | fw-v1.2.0 | observed by the agent on GitHub, 2026-11-15 |
| Release URL | https://github.com/florianlepont/skypane/releases/tag/fw-v1.2.0 | observed by the agent |
| Live frame assets present (`skypane-fw-v1.2.0.bin`, `release.json`) | yes | observed by the agent |
| Second board assets present (`skypane-seeed-ee04-7in3-spectra6-fw-v1.2.0.bin`, `release-seeed-ee04-7in3-spectra6.json`) | yes | observed by the agent |
| Deploy run after the release (workflow_dispatch of ci.yml) | run 43711943313, conclusion success | observed by the agent |
| Import log line for the second type (a "skipped" notice while the switch is closed, none after the lift and a new deploy) | Deploy job "Deploy to production" of CI run 43715715341 (workflow_dispatch, 2026-11-15 12:59 UTC, success): `added fw-v1.2.0 seeed-ee04-7in3-spectra6`; no "skipped" line for the second type | observed by the agent in the job log |
| `registry.seeed-ee04-7in3-spectra6.json` exists on the VPS after the first deploy following the lift | Not seen directly; the import line above implies it. Owner to confirm with `server.firmware_cli list` | open |

## B2. Frame prepared for production

Bench images use throwaway keys and would reject a production-signed OTA.

| Field | Value | Status |
|-------|-------|--------|
| Frame MAC | 84:c7:bb:70:b2:7c | owner-reported (flash-second.sh and provision.sh output) |
| Image flashed carries the production firmware key (how it was obtained and flashed) | Production-signed `skypane-seeed-ee04-7in3-spectra6-fw-v1.2.0.bin` of release fw-v1.2.0 copied over the local build's skypane.bin, flashed with `firmware/flash-second.sh /dev/cu.usbmodem101` (prod profile, verifies against `firmware/signing/skypane-signing-pubkey.pem`); owner reported `SUCCESS 84:c7:bb:70:b2:7c`, 2026-11-15 | owner-reported |
| Production server trusts that key | Not applicable on the server side (the frame verifies the image against the public key built into its firmware); the production-signed image passed the pre-flash signature check and the frame woke, enrolled and paired | owner-reported |
| Guarded `provision.sh` run (no refusal, live frame's port and MAC untouched) | Owner ran `firmware/provision.sh /dev/cu.usbmodem101 --wifi-ssid ... --api-base https://vps-1440bce3.vps.ovh.net` with the live frame unplugged; output: "Provisioned 84:c7:bb:70:b2:7c ... Secret partition verified byte-for-byte"; the live-frame variables were not set (typed MAC only) | owner-reported |
| Paired on the production server; shown as a second-type row in the production fleet database | Registered as pending on the VPS with `fleet_cli devices register-pending --hardware seeed-ee04-7in3-spectra6` ("registered 84:c7:bb:70:b2:7c as pending, pending id p_1e8a1894"; the console has no register form, so the CLI was used); the owner then paired it in the companion with the code shown on the panel ("j'ai apparié avec le code") | owner-reported |

## C. Real signed OTA over https (criterion 5)

| Field | Value | Status |
|-------|-------|--------|
| Frame firmware before | fw-v1.2.0 (the production-signed image cable-flashed; shown on the frame's Fleet page) | owner-reported |
| Version offered and scheduled on the Update page | fw-v1.2.1 (published and imported 2026-11-15; no firmware change, version number only), scheduled by the owner for the second-type frame and, by the owner's choice, for the 13.3 inch live frame too | owner-reported |
| https channel confirmed | Not observed directly. The frame was provisioned with `--api-base https://vps-1440bce3.vps.ovh.net` and a production image refuses an http offer, so the install over that channel implies https | inferred, open |
| Frame firmware after | fw-v1.2.1 on the second-type frame ("C'est bon il est à jour aussi") and on the live frame ("Cadre 13 pouces installé"), 2026-11-15, after the Update-page fix of the Fleet view was deployed | owner-reported |
| Registry `last_outcome` and `installed_at` in `registry.seeed-ee04-7in3-spectra6.json` | Owner pasted the file from the VPS: `last_outcome` = {kind: installed, version: fw-v1.2.1, at: 2026-11-15T15:00:20.569685+00:00}; release fw-v1.2.1 has `installed_at` = [2026-11-15T15:00:20.569685+00:00]; `schedule` null; fw-v1.2.0 has no `installed_at` (it was cable-flashed) | owner-reported, seen in the pasted registry |
| Journal of the install on the production server (`journalctl -u skypane-byos`, pasted by the owner) | Second-type frame: `GET /fw/06c18206...bin` at 14:53:46 (the sha256 in its registry entry and in the release asset digest), `X-Fw-Version=fw-v1.2.1 ... X-Ota-Result=trial;fw-v1.2.1` at 14:54:46, `installed;fw-v1.2.1` at 15:00:17; the registry `installed_at` is 15:00:20, three seconds later. Live frame, same channel: `fw-v1.2.0` download 13:32:53, trial 13:33:54, installed 13:35:32; `fw-v1.2.1` download 14:50:03 (asset 16ea770b...), trial 14:51:04, installed 14:52:42 | owner-reported, seen in the pasted journal |
| Result recorded by the production poll (not only by the live frame's cycle) | The result is in the second type's own registry file (`reconciled_seq` 54); which cycle wrote it is not visible in the file | open |

## D. Failing update keeps the previous firmware (criterion 5)

| Field | Value | Status |
|-------|-------|--------|
| How the failure was provoked (bench method) | Not provoked in production, by the owner's decision (2026-11-15): the recorded bench evidence on this same unit is used instead. On 2026-11-14 (dev profile, throwaway keys, bench server) a wrongly signed image `fw-v1.0.7-bench2` was downloaded and rejected on the device (see `firmware/SIGNING.md`, "Bench results") | bench evidence, not production |
| Frame stayed on the previous firmware | Bench: yes, the unit kept reporting `fw-v1.0.6-bench1` and kept polling; no boot loop | bench evidence, not production |
| Registry shows the attempt and no `installed_at` | Not observed in a production registry (no failing update was provoked in production). The rule is covered by the automated reconcile tests of the second type | open for production |

## E. Open items

- The deploy README (Device enrolment, and Pairing, retiring and re-activating a frame) tells the administrator to use the console's "Register a frame" form, which the current console does not offer (only the POST route `/fleet/register` exists). The frame was registered with `fleet_cli devices register-pending`. The README needs a correction.
- `fleet_cli` reads the second-hardware switch from its own environment: it needs `SKYPANE_ENABLE_SECOND_HARDWARE=1` on the command line to accept the type. To be written in the README.
- Section C: the registry values (`last_outcome`, `installed_at` in `registry.seeed-ee04-7in3-spectra6.json`), the https channel and the production poll's recording are not yet seen directly; only the owner's report that both frames show fw-v1.2.1.
- The live frame also installed fw-v1.2.0 and fw-v1.2.1 by OTA from the production channel (owner-scheduled), which is a further observation for the live frame's release path.
- Section D (failing update) is not done yet.
- Two defects of the Fleet view for a non-live frame were found and fixed while preparing this step: the Update card read the per-frame directory instead of the root state dir, and a frame's page showed the other type's tab (PR #430).
