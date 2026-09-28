---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 05
subsystem: infra
tags: [openssl, tls, ca-chain, github-actions, ci, ota]

requires:
  - phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
    provides: "gate G-41 (Phase 41 complete on main); firmware/main/certs (ISRG X1/X2 roots, D-34-04)"
provides:
  - "scripts/check_cert_chain.py: an offline `verify` decision (chain PEM -> compiled roots dir) plus a network `fetch`/`check`"
  - "deploy/tests/test_cert_chain_check.py: throwaway-fixture proof of the offline decision, no network"
  - ".github/workflows/firmware-chain-check.yml: daily + dispatch + certs-change CI job that runs `check` against production"
affects: [ota, ci, deploy]

tech-stack:
  added: []
  patterns:
    - "Network-only checks live in their own scheduled/dispatched workflow, never inside pytest (pytest-socket blocks non-loopback connections)"
    - "A CLI script splits into an offline, pure decision function plus a thin network-reaching wrapper, so the decision is unit-testable without touching a socket"

key-files:
  created:
    - scripts/check_cert_chain.py
    - deploy/tests/test_cert_chain_check.py
    - .github/workflows/firmware-chain-check.yml
  modified: []

key-decisions:
  - "verify_chain()'s failure message reports the top (root-most) PEM block's issuer field, which for a foreign-root chain is the actual foreign root's subject -- more informative to the developer than the intermediate's own subject"
  - "The workflow's failure-explanation step is gated on the chain-check step's own outcome (steps.check.outcome == 'failure'), not a blanket if: failure(), so a missing-secret failure and a real chain failure never share one misleading message"

requirements-completed: []

coverage:
  - id: D1
    description: "scripts/check_cert_chain.py verify subcommand: offline pass/fail decision for whether a PEM chain leads to a root in a given directory, with -x509_strict and no partial-chain acceptance"
    requirement: OTA-11
    verification:
      - kind: unit
        ref: "deploy/tests/test_cert_chain_check.py#test_good_chain_under_a_compiled_root_verifies"
        status: pass
      - kind: unit
        ref: "deploy/tests/test_cert_chain_check.py#test_chain_under_a_foreign_root_fails_with_named_reason"
        status: pass
      - kind: unit
        ref: "deploy/tests/test_cert_chain_check.py#test_expired_leaf_fails"
        status: pass
      - kind: unit
        ref: "deploy/tests/test_cert_chain_check.py#test_chain_file_with_no_certificate_fails"
        status: pass
      - kind: unit
        ref: "deploy/tests/test_cert_chain_check.py#test_roots_dir_with_no_pem_file_fails"
        status: pass
    human_judgment: false
  - id: D2
    description: "scripts/check_cert_chain.py fetch subcommand: host-name validated before any network attempt"
    requirement: OTA-11
    verification:
      - kind: unit
        ref: "deploy/tests/test_cert_chain_check.py#test_fetch_rejects_a_malformed_host_name_before_touching_the_network"
        status: pass
    human_judgment: false
  - id: D3
    description: ".github/workflows/firmware-chain-check.yml: schedule/dispatch/certs-change workflow that runs check_cert_chain.py check against the real production host, PRODUCTION_HOST secret never interpolated into run:, missing secret fails loudly"
    requirement: OTA-11
    verification:
      - kind: other
        ref: "actionlint .github/workflows/firmware-chain-check.yml (clean, run locally)"
        status: pass
      - kind: unit
        ref: "deploy/tests/test_ci_secrets.py (still passes; this workflow is not yet in its scan scope, extended in a later plan)"
        status: pass
    human_judgment: true
    rationale: "A live workflow_dispatch run against production, and the developer creating the PRODUCTION_HOST repository secret, are both outside this plan's automated reach -- recorded under User Setup Required below and the phase's own hardware-session checklist."

duration: 11min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 05: Let's Encrypt chain guard Summary

**An offline-provable `openssl verify`-based CA chain checker (`scripts/check_cert_chain.py`), its throwaway-fixture pytest suite, and a daily/dispatch/certs-change GitHub Actions workflow that runs it against the production host.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-09-28T11:44:00Z
- **Completed:** 2026-09-28T11:55:00Z
- **Tasks:** 3
- **Files modified:** 3 (all created)

## Accomplishments
- `scripts/check_cert_chain.py`: `fetch` (openssl s_client, host regex-validated, network), `verify` (openssl verify -x509_strict against a roots-dir CA bundle, offline, no `-partial_chain`), and `check` (fetch then verify) subcommands, all argument-list subprocess calls
- `deploy/tests/test_cert_chain_check.py`: a module-scoped fixture builds two independent throwaway CA hierarchies (root A / intermediate A / leaf A, root B / intermediate B / leaf B) plus an expired leaf reissued under intermediate A, entirely with the `openssl` CLI in `tmp_path` — no committed key material, no network; 7 tests cover the good chain, the foreign-root chain, the expired leaf, an empty chain file, an empty roots directory, and fetch's pre-network host validation
- `.github/workflows/firmware-chain-check.yml`: `schedule` (daily, `17 6 * * *`), `workflow_dispatch`, and `push`-to-main on `firmware/main/certs/**` / the script / the workflow file itself; `permissions: contents: read`; `PRODUCTION_HOST` passed through `env:`, never interpolated into a `run:` script; a missing secret fails the job with an explicit `::error::` instead of passing silently

## Task Commits

Each task was committed atomically:

1. **Task 1: Gate G-41 (Phase 41 complete on main)** - read-only, no commit (all three checks passed against `origin/main`; `git status --porcelain` showed no change)
2. **Task 2: Chain checker with offline fixture tests** - `9c4a5a92` (feat)
3. **Task 3: Scheduled chain-guard workflow** - `f2e285f1` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `scripts/check_cert_chain.py` - `fetch`/`verify`/`check` subcommands; the offline `verify_chain()` decision function and the network `fetch_chain_to_file()` wrapper
- `deploy/tests/test_cert_chain_check.py` - throwaway-fixture pytest suite proving the offline decision (good chain, foreign root, expired leaf, empty chain, empty roots dir, pre-network host validation)
- `.github/workflows/firmware-chain-check.yml` - the scheduled/dispatched/certs-change CI job

## Decisions Made
- **Failure-message issuer choice:** `verify_chain()` reports the *top* PEM block's issuer field on a foreign-root failure. For a two-certificate chain (leaf + intermediate), the top block is the intermediate, and its issuer is the root that actually signed it — so the message names the real foreign root's subject, not the intermediate's own subject, without needing to walk any further up a chain the checker was never given.
- **Failure-explanation step scoping:** the workflow's human-readable `::error::` guidance step is gated on `steps.check.outcome == 'failure'` rather than a blanket `if: failure()`. A missing `PRODUCTION_HOST` secret already emits its own specific `::error::` in the preceding step; gating this way keeps the two failure modes from producing one conflated, partly-wrong message.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comments containing the literal strings `shell=True` and `partial_chain` tripped the plan's own acceptance-criteria grep**
- **Found during:** Task 2, running the plan's own acceptance checks (`grep -c 'shell=True' scripts/check_cert_chain.py` / `grep -c 'partial_chain' scripts/check_cert_chain.py`)
- **Issue:** The script's docstring and inline comments explained the security posture by naming the exact strings the acceptance grep was checking for the *absence* of (`never shell=True`, `never -partial_chain`), so the grep matched the comment text, not any actual usage — both counts came back nonzero even though no `shell=True` call and no `-partial_chain` flag exist in the file
- **Fix:** Reworded the three comments to describe the same behaviour without using either literal substring (e.g. "with no shell interpretation of any input", "openssl's own flag that would accept stopping partway there is deliberately never passed")
- **Files modified:** `scripts/check_cert_chain.py`
- **Verification:** `grep -c 'shell=True' scripts/check_cert_chain.py` and `grep -c 'partial_chain' scripts/check_cert_chain.py` both print `0`; `server/.venv/bin/python -m pytest -q deploy/tests/test_cert_chain_check.py` still 7 passed
- **Committed in:** `9c4a5a92` (part of Task 2 commit — caught before commit, not a follow-up)

**2. [Rule 3 - Blocking] Test assertion named the wrong certificate's subject**
- **Found during:** Task 2, first pytest run of the new suite
- **Issue:** `test_chain_under_a_foreign_root_fails_with_named_reason` initially asserted the failure message contains `"Test Intermediate B"`, but `verify_chain()` reports the *issuer* of the top (root-most) block in the chain, which for `leaf-B + intermediate-B` is `"Test Root B"` (the certificate that signed the intermediate), not the intermediate's own subject
- **Fix:** Corrected the assertion to `"Test Root B"`, matching the actual (and more useful) behaviour described in Decisions Made above
- **Files modified:** `deploy/tests/test_cert_chain_check.py`
- **Verification:** `server/.venv/bin/python -m pytest -q deploy/tests/test_cert_chain_check.py` — 7 passed
- **Committed in:** `9c4a5a92` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug in comment wording vs. the plan's literal-grep acceptance check, 1 blocking test-assertion correction)
**Impact on plan:** Both fixes are cosmetic/test-only; no change to the checker's actual security behaviour. No scope creep.

## Issues Encountered
None beyond the two auto-fixed items above.

## User Setup Required

**A repository secret must be created before the new workflow can pass.** The developer must add `PRODUCTION_HOST` as a GitHub Actions repository secret (Settings → Secrets and variables → Actions), set to the byos public host name — the same value `deploy/render_caddyfile.sh`'s `<public-host>` argument and `SKYPANE_PUBLIC_HOST` in `/opt/skypane/skypane.env` already use (for example `203-0-113-10.nip.io`, substituting the real VPS IP). Until this secret exists, every run of `.github/workflows/firmware-chain-check.yml` fails immediately at the "Confirm the PRODUCTION_HOST secret is set" step with `::error::PRODUCTION_HOST secret is not set`, rather than silently passing.

After the secret is created, per this plan's own `<verification>` section, a manual `workflow_dispatch` run against production should be triggered once and confirmed green — deferred to the phase's hardware-session final checklist per the plan text, not performed by this executor (no network access to trigger a real GitHub Actions run from this sandbox).

## Next Phase Readiness
- The chain guard is proven offline and syntax-clean (`actionlint`); it needs the one-time `PRODUCTION_HOST` secret and one live `workflow_dispatch` run to be fully proven end to end — both are developer/hardware-session actions, not blockers for later plans in this phase.
- No other plan in this phase reads `scripts/check_cert_chain.py`; it is a standalone operational safeguard (D-19) with no downstream code dependency.

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED
