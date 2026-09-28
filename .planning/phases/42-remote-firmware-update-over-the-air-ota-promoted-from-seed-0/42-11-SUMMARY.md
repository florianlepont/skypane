---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 11
subsystem: infra
tags: [github-actions, ci, firmware-signing, espsecure, ota, release-manifest]

# Dependency graph
requires:
  - phase: 42-01
    provides: server.firmware_registry.publish_release's manifest shape (version, sha256, size, released_at, commit, notes) and MAX_IMAGE_BYTES, which this plan's manifest generator and workflow must produce exactly
  - phase: 42-03
    provides: firmware/build.sh's SKYPANE_RELEASE_TAG release mode, the resolved signed-app-without-secure-boot Kconfig chain, and firmware/SIGNING.md's FW_SIGNING_KEY/firmware-signing environment/public-key-path convention this workflow assumes
  - phase: 42-06
    provides: (not directly read this plan; listed in depends_on as a wave-2 sibling providing byos's device-facing offer surface the published release eventually feeds)
provides:
  - "scripts/fw_release_manifest.py: a stdlib-only manifest generator producing the exact release.json shape server.firmware_registry.publish_release expects, plus an optional Markdown release-notes body, entirely from git and the image file"
  - ".github/workflows/firmware-release.yml: a fw-v* tag-triggered, environment-gated (firmware-signing) workflow that builds, signs, verifies and publishes a GitHub Release, then triggers the reviewer-gated ci.yml deploy"
  - "deploy/tests/test_ci_secrets.py's no-secret-in-run: scan now covers every .github/workflows/*.yml file, not only ci.yml, with a real mutation proof"
affects: [42-15, 42-16, ci-firmware-signing]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Release notes and metadata generated from git, never hand-written (D-07): scripts/fw_release_manifest.py reads git log/rev-list/show only, so a release's changelog can never drift from what was actually committed"
    - "A GitHub environment (firmware-signing) as the sole gate on a secret's release to a job: the private key is bound to secrets.FW_SIGNING_KEY inside that one environment, so the reviewer-approval step is enforced by GitHub itself, not by workflow logic that could be bypassed"

key-files:
  created:
    - scripts/fw_release_manifest.py
    - deploy/tests/test_release_manifest.py
    - .github/workflows/firmware-release.yml
  modified:
    - deploy/tests/test_ci_secrets.py

key-decisions:
  - "previous_tag() orders candidate fw-v* tags by parsed (major, minor, patch), never by git tag creation time -- proven with a dedicated test where the lower-version tag is created after the higher-version one, which a naive 'most recently created tag' implementation would get wrong"
  - "Release asset file names taken verbatim from the plan's own interfaces block, including the exact 'partition-table-<tag>.bin' spelling (not 'partition-<tag>.bin')"
  - "The final 'gh workflow run ci.yml --ref main' step is expected to fail today (ci.yml has no workflow_dispatch trigger yet, added by plan 15) -- left failing loudly rather than masked, since no fw-v* tag is pushed before the hardware session"

requirements-completed: []

coverage:
  - id: D1
    description: "Tag-triggered, environment-gated, signed and verified release workflow publishes a GitHub Release and triggers the deploy job"
    requirement: "OTA-10"
    verification:
      - kind: other
        ref: "actionlint .github/workflows/firmware-release.yml (clean); grep -c 'environment: firmware-signing' == 1; grep -c 'merge-base --is-ancestor' == 1; grep -cE 'espefuse' == 0"
        status: pass
    human_judgment: true
    rationale: "The first real tag push and signing run only happens in plan 16's hardware session -- this plan's own verification section defers that proof; static/lint checks alone cannot confirm the GitHub environment's reviewer gate fires correctly against a live run"
  - id: D2
    description: "Release manifest (version, sha256, size, released_at, commit, notes) generated from git with no hand-written text, notes firmware/-only newest-first no-merges, capped at 60 with a real remaining count, previous release chosen by version order not tag creation time"
    requirement: "OTA-04"
    verification:
      - kind: unit
        ref: "deploy/tests/test_release_manifest.py (12 tests, all pass)"
        status: pass
      - kind: integration
        ref: "deploy/tests/test_release_manifest.py::test_manifest_round_trips_through_firmware_registry_publish_release"
        status: pass
    human_judgment: false
  - id: D3
    description: "The private signing key reaches the job only through env:, lives in a 0600 temp file outside the workspace for the signing step, and is removed by an if: always() step -- never interpolated into run: text"
    requirement: "OTA-10"
    verification:
      - kind: other
        ref: "grep -q 'FW_SIGNING_KEY: ${{ secrets.FW_SIGNING_KEY }}' and grep -q 'if: always()' in .github/workflows/firmware-release.yml; deploy/tests/test_ci_secrets.py::test_no_secrets_expression_inside_any_run_block"
        status: pass
    human_judgment: false
  - id: D4
    description: "A tag that is malformed or not on main fails the job before any build or signing"
    requirement: "OTA-10"
    verification:
      - kind: other
        ref: "workflow step 'Guard the tag shape and that it is on main' runs before the build step, using the same fw-vMAJOR.MINOR.PATCH regex firmware/build.sh and server.firmware_registry.RELEASE_TAG_RE both use, plus git merge-base --is-ancestor against origin/main"
        status: unknown
    human_judgment: true
    rationale: "The guard's regex and ancestor logic are unit-testable in isolation but this plan did not add a dedicated test harness for the workflow's own bash guard step; the hardware-session tag push (plan 16) is the first live proof"
  - id: D5
    description: "Every workflow file under .github/workflows/, not only ci.yml, is covered by the no-secret-in-run: test"
    requirement: "OTA-10"
    verification:
      - kind: unit
        ref: "deploy/tests/test_ci_secrets.py::test_no_secrets_expression_inside_any_run_block, ::test_at_least_two_workflow_files_are_scanned, ::test_firmware_release_passes_signing_key_through_env"
        status: pass
    human_judgment: false

duration: ~40min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 11: Release pipeline (build half) — manifest generator and signed release workflow Summary

**scripts/fw_release_manifest.py generates release.json (and a Markdown notes body) entirely from git log/rev-list/show against the image file, and .github/workflows/firmware-release.yml builds/signs/verifies/publishes a GitHub Release on a fw-v* tag push, gated behind a firmware-signing GitHub environment reviewer**

## Performance

- **Duration:** ~40 min
- **Completed:** 2026-09-28
- **Tasks:** 2 (Task 1 TDD: RED then GREEN; Task 2: one commit)
- **Files modified:** 4 (3 created, 1 modified)

## Accomplishments
- `scripts/fw_release_manifest.py`: a stdlib-only CLI (`--tag`, `--image`, `--out`, `--repo`, `--notes-md`) that hashes the image, walks git history between the previous and current release tag, and writes the exact manifest shape `server.firmware_registry.publish_release` expects — proven with a direct round trip through that real function, not just shape assertions
- Release notes are `firmware/`-only, no-merges, newest-first, capped at 60 entries with a real `"and N earlier commits"` remaining count when more exist, and the previous release tag is chosen by parsed version order among tags reachable from the current tag — **not** by tag creation time, proven with a dedicated test that creates the lower-version tag *after* the higher-version one
- `.github/workflows/firmware-release.yml`: `on: push: tags: ['fw-v*']`, one `release` job gated behind the `firmware-signing` GitHub environment (reviewer approval required before `FW_SIGNING_KEY` is ever released to the run), guards the tag shape and that its commit is an ancestor of `origin/main` before any build, builds with `firmware/build.sh`'s `SKYPANE_RELEASE_TAG` release mode, re-runs the production-config and Log Line Contract checks against the built image, signs with `espsecure.py sign_data` inside the pinned `espressif/idf:v5.3.1` container (key written to a `$RUNNER_TEMP` file under `umask 077`, removed by an `if: always()` step), verifies with `espsecure.py verify_signature` against the committed public key (failing clearly if it is not yet committed), generates the manifest and notes via `fw_release_manifest.py`, stages the five fixed-name release assets, publishes via `gh release create --verify-tag`, and finally triggers `ci.yml`'s reviewer-gated production deploy via `gh workflow run`
- `deploy/tests/test_ci_secrets.py`'s no-`${{ secrets.` -in-`run:` scan now iterates every `.github/workflows/*.yml` file instead of only `ci.yml`, proven with a real mutation: a scratch `zz-scratch-mutation-proof.yml` containing `run: echo ${{ secrets.X }}` was added, made `test_no_secrets_expression_inside_any_run_block` fail with the exact offending file/step name, then removed — see Mutation Proof below
- `actionlint .github/workflows/firmware-release.yml` is clean

## Task Commits

Each task was committed atomically:

1. **Task 1a: Release manifest generator tests (RED)** - `2f95caac` (test)
2. **Task 1b: Release manifest generator implementation (GREEN)** - `dc09c605` (feat)
3. **Task 2: Tag-triggered signed release workflow + secrets test coverage** - `5a1c4194` (feat)

_TDD task: Task 1 has 2 commits (test → feat). No refactor commit — GREEN was clean on the first pass._

## Mutation Proof (test_ci_secrets.py's all-workflows scan)

```
$ cat > .github/workflows/zz-scratch-mutation-proof.yml <<'EOF'
name: scratch
on: push
jobs:
  x:
    runs-on: ubuntu-latest
    steps:
      - name: leak a secret
        run: echo ${{ secrets.X }}
EOF
$ server/.venv/bin/python -m pytest -q deploy/tests/test_ci_secrets.py::test_no_secrets_expression_inside_any_run_block
FAILED deploy/tests/test_ci_secrets.py::test_no_secrets_expression_inside_any_run_block
AssertionError: run: block(s) still interpolate a secret: ['zz-scratch-mutation-proof.yml: leak a secret']
$ rm .github/workflows/zz-scratch-mutation-proof.yml
```

Confirms the broadened scan actually reaches every file under `.github/workflows/`, not just `ci.yml` — a real failure for the right reason, not a vacuous pass. The scratch file was removed before committing; `git status --short .github/workflows/` showed only the real `firmware-release.yml` addition afterward.

## Files Created/Modified
- `scripts/fw_release_manifest.py` - new: stdlib-only release manifest + notes-body generator, argument-list subprocess calls to `git` only (`grep -c 'shell=True'` is 0)
- `deploy/tests/test_release_manifest.py` - new: 12 tests against throwaway git repos built in `tmp_path`, including the version-order-not-creation-time proof, the 60-entry cap, 200-char truncation, malformed-tag/oversized-image exit-2 cases, and the `firmware_registry.publish_release` round trip
- `.github/workflows/firmware-release.yml` - new: the tag-triggered signed release pipeline
- `deploy/tests/test_ci_secrets.py` - extended: `_workflow_files()` iterates `.github/workflows/*.yml`; `test_no_secrets_expression_inside_any_run_block` now scans all of them; added `test_at_least_two_workflow_files_are_scanned` and `test_firmware_release_passes_signing_key_through_env`

## Decisions Made
- **Previous-tag selection is by parsed version order, never tag creation time.** `git tag --list 'fw-v*' --merged <tag>` gives every reachable tag; comparing parsed `(major, minor, patch)` tuples (not iterating in the list's own order) is what makes a bench or backport tag created out of order harmless. Verified with a repo where `fw-v1.0.5` is tagged before `fw-v1.0.2` (a lower version, tagged later) — the correct answer, `fw-v1.0.5`, only comes out if creation time is never consulted.
- **Asset file names taken verbatim from the plan's interfaces block**, including `partition-table-<tag>.bin` (not the shorter `partition-<tag>.bin` a first draft might guess) — matches what plan 15's downloader and plan 16's USB flash will expect.
- **The workflow's own bash guard step (tag shape + ancestor-of-main) has no dedicated CI-level test harness in this plan** — its regex is the same one `firmware/build.sh` and `server.firmware_registry.RELEASE_TAG_RE` already use and are independently tested, and the `git merge-base --is-ancestor` command is a well-understood primitive; the plan's own `<verification>` section explicitly defers the first live proof to plan 16's hardware-session tag push, so this was not treated as a gap requiring an ad hoc workflow-simulation test.

## Deviations from Plan

None - plan executed exactly as written. The one wording collision caught during Task 1 (my own docstring literally contained the substring `shell=True` inside a sentence explaining that the script never uses it, which the `grep -c 'shell=True'` acceptance check would have flagged) was fixed within the same GREEN commit, before it was ever committed — not a deviation from the plan's instructions, just a self-correction during the TDD GREEN step.

## Issues Encountered

The interactive shell environment's `grep` alias wraps `ugrep -G` (basic regex mode), which does not match a literal `${{ ... }}` pattern the way GNU/BSD `grep` does — every acceptance-criteria grep in this plan's `<verify>` blocks had to be re-run via `command grep` to get a real result. This is an artifact of this session's shell configuration, not of the files themselves; confirmed by cross-checking `command grep -q 'FW_SIGNING_KEY: ${{ secrets.FW_SIGNING_KEY }}' .github/workflows/firmware-release.yml` (exit 0) against the aliased `grep` (exit 1, false negative) on the identical file content.

## User Setup Required

None - no external service configuration required. The `firmware-signing` GitHub environment, its reviewer, and the `FW_SIGNING_KEY` secret itself are created in the next (human) plan per `firmware/SIGNING.md` — this plan only writes the workflow that assumes their exact names.

## Next Phase Readiness
- `firmware-release.yml` is ready to receive a real `fw-v*` tag once the signing key exists (next human plan) and the hardware session (plan 16) is reached; until then it has never run for real, only lint- and grep-verified
- `scripts/fw_release_manifest.py` is ready for plan 15's deploy-side consumption of `release.json` and for plan 16's manual bench-image signing workflow
- The final `gh workflow run ci.yml --ref main` step will fail until plan 15 adds a `workflow_dispatch` trigger to `ci.yml` — expected and acceptable per this plan's own action text, since no release tag is pushed before then
- `REQUIREMENTS.md` intentionally left untouched: OTA-04/OTA-10 are shared with later plans in this phase (the device-side apply, the deploy import, the hardware session), matching this project's established convention of only flipping a shared requirement ID at a phase's own close-out or the plan that fully proves it live

---
*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*
