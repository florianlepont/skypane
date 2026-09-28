# Deferred items — Phase 42

Out-of-scope discoveries logged during execution, not fixed (per the
executor's scope-boundary rule).

## 42-04: `server/test_fault_screen_mask.py` fails on this sandbox, pre-existing on `origin/main`

**Found during:** 42-04 Task 2 verification.

**Symptom:** `server/.venv/bin/python -m pytest server/test_fault_screen_mask.py`
fails: the committed `firmware/main/fault_screen_mask.h` is not byte-for-byte
reproducible by `firmware/tools/gen_fault_screen.py` in this sandbox. The
generated mask's bounding box is 1px narrower (`FP_FAULT_MASK_W 564` vs the
committed `565`); the rest of the 128,919-byte header matches.

**Proven pre-existing and unrelated to this plan:** checked out a clean,
unmodified `origin/main` worktree (`git worktree add --detach <tmp> origin/main`)
and ran that commit's own `gen_fault_screen.py` against that commit's own
`server/plane/render` package and `fault_screen_mask.h`, in this same
sandbox — the identical mismatch (564 vs 565) reproduces with zero code from
this plan involved. `server/plane/render/glyphs.py`, `style.py` and
`hold_screens.py`'s pre-existing NO CONNECTION lines
(`NO_CONNECTION_*`, `draw_alert_icon`, `_build_no_connection_canvas`,
`_build_hold_canvas`) were not touched by 42-04 — only new, additive code
was inserted. `server/test_render.py`'s full 149-test suite (including its
own NO CONNECTION/ALERT_ICON pixel-precision assertions) passes cleanly in
this same sandbox, so this is not a general font-rendering breakage —
likely a cross-platform Pillow/FreeType text-metric difference between
whatever machine last regenerated and committed `fault_screen_mask.h` and
this sandbox.

**Why not fixed here:** regenerating `fault_screen_mask.h` in this sandbox
would change the committed NO CONNECTION mask's bytes — forbidden by this
plan's own constraint ("the NO CONNECTION screen's output byte-identical")
and by `42-04`'s files_modified list, which does not include
`fault_screen_mask.h`. The new `updating_screen_mask.h` this plan commits
was generated fresh in this same sandbox, so it carries no cross-environment
drift of its own; `server/test_updating_screen_mask.py` passes.

**Suggested follow-up:** regenerate `firmware/main/fault_screen_mask.h` (and
its preview) in whatever environment is authoritative for committed
artifacts (e.g. the `firmware.yml` CI runner), confirm the drift is real
there too or sandbox-only, and either commit the regenerated header or pin
the font-rendering toolchain so the mask is reproducible across machines.

**Resolved — root cause found (orchestrator, 2026-09-28):** not a Pillow or
FreeType version drift but a text *layout engine* difference. Pillow uses
libraqm for layout when the system library is present; the CI runner
(`ubuntu-latest`) has it, this macOS sandbox and a bare `python:3.14-slim`
container do not, and basic layout differs by one pixel of advance. The
committed `fault_screen_mask.h` was generated with raqm, so it passes in CI
and in a `python:3.14` container with `libraqm0` installed, and fails
without raqm. The first `updating_screen_mask.h` commit was generated
without raqm and would have failed in CI; it was regenerated with raqm
(`docker run python:3.14`, `apt-get install libraqm0`, hash-locked
`server/requirements-dev.txt`), and both mask drift tests pass there.
Regenerate any committed mask header the same way. Check locally with
`python -c "from PIL import features; print(features.check('raqm'))"`.

## 42-05: `deploy/tests/test_activate.py` and `test_install_backup_key.py` fail on this sandbox, pre-existing and unrelated to this plan

**Found during:** 42-05 Task 2/3 verification (ran the full `deploy/tests`
directory as an extra check beyond the plan's own targeted verify commands).

**Symptom:** 17 failures across `test_activate.py` (all cases) and two
`test_install_backup_key.py` cases when run natively on this non-root macOS
sandbox. `41-REAUDIT-INT-SEC.md` (Phase 41, plan 6) already documents the
same class of failure for a different pair of files in this exact sandbox
("BSD `mv` lacks `-T`"), and re-runs them inside a plain Linux container
instead of leaving them unproven.

**Why not fixed here:** none of this plan's three files
(`scripts/check_cert_chain.py`, `deploy/tests/test_cert_chain_check.py`,
`.github/workflows/firmware-chain-check.yml`) touch `deploy/activate.sh`,
`deploy/install_backup_key.sh`, or anything either failing test file
exercises — out of this plan's `files_modified` list and scope boundary.
This plan's own targeted verify commands
(`deploy/tests/test_cert_chain_check.py deploy/tests/test_ci_secrets.py`)
pass cleanly; the broader `deploy/tests` run was an extra check, not a
plan requirement.

**Suggested follow-up:** re-run `deploy/tests/test_activate.py` and
`test_install_backup_key.py` inside a Linux container (as 41-06 did) if a
future plan needs to prove them; not needed for this plan's own scope.
