---
quick_id: 260923-9fe
status: complete
date: 2026-09-23
commits: [363441c, 7c80d72, bd332c2, f61d6ac, 9c90522, ec36873]
---

# Quick 260923-9fe — public-repo hygiene: SUMMARY

Executed inline by the orchestrator (no planner/executor spawn): the audit that
motivated the task had already gathered every fact the plan needed.

## Audit findings (pre-change)

- **Secrets: clean.** All 1,802 commits scanned (`git log --all -p`): no real
  password, token, private key, Wi-Fi SSID/BSSID or ntfy topic — only test
  fixtures and `*.example` placeholders. Hardware logs were already redacted.
- **Exposed, accepted:** the VPS public IP appears (as a `nip.io` hostname) in 8
  files, mostly `.planning/`; commit metadata carries the maintainer's personal
  e-mail on ~1,300 commits. Neither is rewritten (history rewrite judged
  disproportionate); both reported to the user.
- **Licensing gaps:** root LICENSE carried an appended scope note, so GitHub
  reported "Other"; it did not exclude `firmware/` (Apache-2.0); no Apache
  licence copy or NOTICE in-tree; SkyPane-original firmware files carried a YODE
  copyright line; modified vendored files carried no modification notice; two
  files listed as verbatim (`panel_guard.h`, `sdkconfig.ee02.defaults`) had
  drifted from the pinned upstream commit (verified by blob SHA against upstream).
- **Trademarks:** illustrations VENDOR.md wrongly claimed AI generation sidesteps
  trademark constraints.

## Changes

| Commit | What |
|---|---|
| 363441c | Pure MIT `LICENSE`; `firmware/LICENSE` + `firmware/NOTICE`; SPDX headers fixed on 22 files; VENDOR.md licensing section, `led.*`/`test_battery_math.c` listed as originals, two drifted files re-classified as modified |
| 7c80d72 | Public README (preview image `docs/panel-preview.png`, licence table, trademarks, security, AI-assisted note); top-level `NOTICE`; corrected trademark rationale |
| bd332c2 | `SECURITY.md`, `.github/dependabot.yml`, `permissions: contents: read`, all actions SHA-pinned |
| f61d6ac | `.claude/CLAUDE.md` stack section now describes the shipped stack |
| 9c90522 | Kconfig menu renamed to SkyPane; unused `CONFIG_FP_API_BASE` default changed from FlightPortrait's production API to `https://example.invalid`; container build verified, no upstream URL in the image |
| ec36873 | **Relicensed to AGPL-3.0-only + commercial licence** (user decision 2026-09-23: open source is fine, but a private company must not profit for free). Verbatim AGPL text in `LICENSE`; NOTICE/README explain dual licensing and that pre-2026-09-23 versions stay MIT; `CONTRIBUTING.md` adds an inbound licence grant so dual licensing survives outside contributions. Sole-author claim checked: every commit on main is Florian's except one Mistral commit whose `audits/` files were later removed. firmware/ stays Apache-2.0. |

GitHub settings applied via `gh api` (user-approved in chat): Dependabot alerts +
security updates, private vulnerability reporting, fork-PR CI approval for all
external contributors, ruleset "Protect main" (blocks force-push and deletion
only — no required reviews/checks), new description + 11 topics, Wiki and
Projects disabled.

## Open item

- The user wants a dedicated contact e-mail for commercial licensing in README/NOTICE; address not yet provided (GitHub profile used meanwhile).

## Verification

- `scripts/check-attribution.sh`: PASS (68 assets). `ruff check .`: clean.
- `firmware/tests/run_host_tests.sh`: all suites pass.
- Every verbatim-marked firmware file re-verified byte-identical to upstream.
- `./scripts/run-all-tests.sh`: 2 harnesses failed in the parallel run.
  `companion/test_companion_app.py` passes in isolation (BrokenPipe flake).
  `companion/test_browser_ux.py` fails 3/75 checks **identically on the untouched
  base commit efafc89** — pre-existing, unrelated to this task (no companion file
  changed).
- `licenseInfo` = MIT can only be confirmed once merged to `main`.
