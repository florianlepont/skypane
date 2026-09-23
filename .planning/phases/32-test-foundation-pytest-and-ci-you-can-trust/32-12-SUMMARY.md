---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
plan: 12
subsystem: infra
tags: [uv, pip-compile, hash-locking, supply-chain, deploy]

# Dependency graph
requires:
  - phase: 32-test-foundation-pytest-and-ci-you-can-trust
    plan: "01"
    provides: the four pytest/xdist/cov/socket dev-only pins this plan's requirements-dev.in carries forward
provides:
  - server/requirements.in and server/requirements-dev.in as the checked-in lock sources (direct pins only)
  - server/requirements.txt (runtime) and server/requirements-dev.txt (dev, superset) hash-locked for
    Python 3.14 / x86_64 Linux, including every transitive package (urllib3, certifi, idna,
    charset-normalizer, coverage's own deps, pytest's own deps, etc.)
  - scripts/lock-deps.sh - the one documented command to regenerate both locks via `uv pip compile
    --generate-hashes --python-version 3.14 --python-platform x86_64-manylinux_2_28`
  - deploy/deploy.sh installing the runtime lock with `pip install --require-hashes`
affects: [32-14]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Lock sources (.in, direct pins only) vs. compiled locks (.txt, hash-locked with transitives) kept as
       separate files; the dev lock is a superset compiled from a .in that starts with `-r requirements.in`,
       so CI installs exactly ONE hash-locked file instead of two separately-compiled files that could
       disagree on a shared transitive pin."
    - "The runtime lock stays at the same path (server/requirements.txt) deploy/deploy.sh already
       referenced twice (sha256sum change-detection + pip install), so the only deploy.sh edit needed was
       adding --require-hashes to the existing install line - no path changes."

key-files:
  created:
    - server/requirements.in
    - server/requirements-dev.in
    - scripts/lock-deps.sh
  modified:
    - server/requirements.txt
    - server/requirements-dev.txt
    - deploy/deploy.sh

key-decisions:
  - "Locks generated for --python-platform x86_64-manylinux_2_28 (accepted directly by uv 0.8.17, no
     fallback to the coarser 'linux' tag needed) since both production (OVH VPS, Ubuntu 26.04) and CI
     (ubuntu-latest) are x86_64 Linux."
  - "Tamper verification flips ALL hashes for one package's requirement block, not just the first line's
     hash - pip's --require-hashes accepts a match against ANY listed hash for a requirement, so flipping
     only one of requests' two hashes let pip silently fall back to the sdist (whose hash was untouched)
     and install anyway. Flipping both hashes for the requests block was needed to force the real rejection
     path and confirm the 'DO NOT MATCH THE HASHES' message."

requirements-completed: [TST-08]

# Metrics
duration: ~20min
completed: 2026-09-23
---

# Phase 32 Plan 12: Hash-lock dependencies for supply-chain integrity Summary

**Runtime and dev dependencies hash-locked for Python 3.14/x86_64 Linux via `uv pip compile --generate-hashes`, with every transitive package pinned (urllib3, certifi, idna, charset-normalizer, execnet, greenlet, pluggy, ...), one regeneration script, and `deploy/deploy.sh` now installing with `pip install --require-hashes` — verified in clean 3.14 venvs including a real tamper rejection.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-23T16:40:00Z (approximate — not captured at spawn)
- **Completed:** 2026-09-23T17:00:37Z
- **Tasks:** 2
- **Files modified:** 6 (2 new `.in` sources, 1 new script, 2 regenerated locks, 1 edited deploy script)

## Accomplishments
- `server/requirements.in` (Pillow==12.3.0, requests==2.34.2) and `server/requirements-dev.in` (`-r
  requirements.in` + the 7 existing dev pins) added as the human-edited lock sources.
- `server/requirements.txt` regenerated: 6 packages total (Pillow, requests, and the 4 transitives —
  urllib3, certifi, idna, charset-normalizer), every one hash-locked, zero dev-only packages present.
- `server/requirements-dev.txt` regenerated as a hash-locked superset: 21 packages, the runtime 6 pins
  byte-identical to the runtime lock plus ruff/coverage/playwright/pytest+xdist+cov+socket and their own
  transitives (execnet, greenlet, pluggy, pyee, pygments, iniconfig, packaging, typing-extensions).
- `scripts/lock-deps.sh` created (executable, `set -euo pipefail`) as the one documented regeneration
  command; both lock file headers name it via `--custom-compile-command`.
- `deploy/deploy.sh`'s remote install line changed to `pip install --require-hashes --quiet -r
  ${APP_ROOT}/server/requirements.txt`; the `sha256sum` change-detection path and every other line
  untouched (3-line diff: install line + 2 echo strings).
- Verified in throwaway `uv venv --python 3.14` environments (no VPS needed): runtime lock installs clean
  and imports PIL/requests with no dev packages present; dev lock installs clean and `pytest --version`
  reports 9.1.1; a hash-tampered copy of the runtime lock is rejected by pip with "THESE PACKAGES DO NOT
  MATCH THE HASHES FROM THE REQUIREMENTS FILE".

## Task Commits

Each task was committed atomically:

1. **Task 1: .in sources, hash-locked lock files, regeneration script** - `c120d1a` (feat)
2. **Task 2: deploy.sh enforces hashes; clean-venv and tamper verification on 3.14** - `380bc3c` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/requirements.in` (new) - direct runtime pins, lock source
- `server/requirements-dev.in` (new) - `-r requirements.in` + direct dev pins, lock source
- `server/requirements.txt` - regenerated, hash-locked runtime lock (6 packages incl. transitives)
- `server/requirements-dev.txt` - regenerated, hash-locked dev lock (21 packages, superset of runtime)
- `scripts/lock-deps.sh` (new) - regenerates both locks via `uv pip compile --generate-hashes
  --python-version 3.14 --python-platform x86_64-manylinux_2_28`
- `deploy/deploy.sh` - remote pip install now uses `--require-hashes`; two echo lines call out
  "(hash-locked)"

## Decisions Made
- Hardcoded `--python-version 3.14` and `--python-platform x86_64-manylinux_2_28` as literals in
  `scripts/lock-deps.sh` rather than shell variables, so the script's own source is self-documenting and
  greppable for the exact target.
- `x86_64-manylinux_2_28` was accepted directly by uv 0.8.17 (confirmed via `uv pip compile --help`); the
  plan's documented fallback to the coarser `linux` platform tag was not needed.
- Verified the tamper-rejection claim by corrupting **both** hashes in the `requests` block, not just the
  first — pip's hash-checking mode treats multiple `--hash` entries per requirement as "any one match is
  sufficient" (they represent alternate acceptable artifacts, e.g. wheel + sdist), so a single-hash flip
  let pip silently fall back to the sdist build and install successfully. This is worth remembering for any
  future tamper test against a multi-hash package.

## Deviations from Plan

None requiring the Rule 1-4 framework. One in-flight correction during Task 1, not a deviation from intent:
`scripts/lock-deps.sh`'s first draft used shell variables (`PYTHON_VERSION="3.14"`,
`PYTHON_PLATFORM="x86_64-manylinux_2_28"`) interpolated into the `uv pip compile` invocation, which produced
correct lock output but made the acceptance-criteria grep (`grep -c "python-version 3.14"
scripts/lock-deps.sh`, expecting the literal substring) return 0 instead of the required 2. Rewritten to
pass `--python-version 3.14` and `--python-platform x86_64-manylinux_2_28` as literals before running the
verification suite or committing — caught by the plan's own acceptance criteria before any commit, so no
separate fix-commit was needed.

## Issues Encountered

The first tamper-test attempt (flip one hex digit of the *first* `--hash=sha256:` entry in the `requests`
block) did not reproduce a rejection: pip fell back to the untouched second hash (the sdist build) and
installed successfully. Root-caused before concluding the test: pip's `--require-hashes` mode accepts a
download whose digest matches *any* of the hashes listed for that requirement (normal support for a
requirement resolving to multiple valid artifacts, e.g. one hash per wheel/sdist). Re-ran the test flipping
every hash in the `requests` block, which reproduced the documented rejection message. No code or lock
files were affected — this was purely a verification-methodology correction, resolved before recording the
results above.

## Next Phase Readiness
- `scripts/lock-deps.sh` is ready for 32-14 (CI workflow) to either call directly in a lock-freshness check,
  or simply rely on the two `.txt` files already being hash-locked when CI installs
  `server/requirements-dev.txt` with `--require-hashes`.
- No blockers. `deploy/deploy.sh`'s next real deploy to the VPS will see `requirements.txt`'s content hash
  change (the file went from 2 lines to hash-locked form) and reinstall once, as the plan's
  `Pitfall 5` note anticipated — this is expected, not a regression.

---
*Phase: 32-test-foundation-pytest-and-ci-you-can-trust*
*Completed: 2026-09-23*

## Self-Check: PASSED

All 6 created/modified files confirmed present on disk; both task commit hashes (`c120d1a`, `380bc3c`)
confirmed present in `git log --oneline --all`.
