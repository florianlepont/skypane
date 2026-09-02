---
phase: quick-260902-req
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - server/plane/render.py
  - server/test_render.py
  - server/test_poll_loop.py
  - .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md
autonomous: false
requirements: [REQ-260902-req-PANEL]
must_haves:
  truths:
    - "The main aircraft's visible (painted) vertical centre lands on one fixed canvas line for every vendored illustration, instead of drifting 120.5px by file."
    - "The developer-confirmed reference render's main aircraft keeps its currently-approved on-glass position — the constant is re-derived to reproduce the approved look, not to redesign it."
    - "A regression harness fails if any future change reintroduces per-file vertical drift of the main illustration."
    - "The panel.bin digest pin is handled through the established CI-authoritative process, never guessed locally."
    - "Production deployment is surfaced to the developer as their action, never executed by the executor."
  artifacts:
    - server/plane/render.py
    - server/test_render.py
  key_links:
    - "_build_active_canvas()'s main_top computation -> _top_for_centered_content() -> _opaque_bbox() (the single shared alpha threshold)"
    - "main_placement.content[3] -> draw_main_text_block()'s top_y (text follows the aircraft, so fixing the aircraft fixes the whole composition)"
---

<objective>
Close the one illustration anchor the `illustration-crop-text-margin` debug session missed: the MAIN illustration's **vertical** placement.

That session converted five of six position anchors from the source rectangle to the painted-content bbox — the main illustration's horizontal centring, the previous card's right-alignment and vertical centring, and both text blocks' vertical gaps. It did not convert `_build_active_canvas()`'s `main_top`, which is still `round(HEIGHT * MAIN_ILLUSTRATION_TOP_FRAC)` applied to the source PNG's rectangle top (render.py:1896).

Measured on this branch, at the real render scale (992px wide, `main_top` = 480), across all 43 vendored files:
- top transparent padding ranges **6px to 124px** (spread 118px)
- the aircraft's visible top edge therefore lands anywhere from y=486 to y=604
- the aircraft's visible vertical **centre** drifts **120.5px** — from 621.0 (`air-caraibes-atr72.png`) to 741.5 (`generic-a330.png`) on a 1600px-tall panel

That is the developer's reported "inconsistent aircraft centering," it is present in the code right now, and it is provable without any production access. The deployment question is therefore secondary, not primary — but it is still open and is handled by Task 3.

Purpose: the frame is an ambient wall piece; a hero element that jumps ~7.5% of panel height depending on which airline flew is the single most visible layout defect left in the composition.
Output: content-anchored main vertical placement, a re-derived design constant, a drift regression harness, and a developer checkpoint covering the digest re-pin and the deploy.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/quick/260902-req-fix-inconsistent-aircraft-centering-acro/260902-req-CONTEXT.md
@server/plane/render.py
@.planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md

Read before touching anything:
- `server/plane/render.py` lines 313-330 (`MAIN_ILLUSTRATION_TOP_FRAC`, `PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC` and its 0.76 -> 0.7528 re-derivation comment — that comment is the exact precedent this plan follows)
- `server/plane/render.py` lines 981-1110 (`ILLUSTRATION_ALPHA_THRESHOLD`, `_threshold_alpha()`, `_opaque_bbox()`, `IllustrationPlacement`, `_top_for_centered_content()`)
- `server/plane/render.py` lines 1892-1945 (`_build_active_canvas()`'s main + previous illustration placement — the previous card at line 1942 already does correctly what the main card at line 1896 does not)
- `.planning/debug/knowledge-base.md`, `illustration-crop-text-margin` entry
- `server/test_poll_loop.py` lines 92-250 (`_DEFAULT_CONFIG_DIGEST` and its comment history — the re-pin discipline)

Test harnesses in this repo are stdlib-only scripts run under the project venv, exiting 0/1:
`server/.venv/bin/python3 server/test_render.py`. Full suite: `./scripts/run-all-tests.sh`.
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Pin the per-file vertical drift with a failing regression check</name>
  <files>server/test_render.py</files>
  <behavior>
    - Over every real file in server/assets/icons/illustrations/, resize to the same main_w the render path uses, take _opaque_bbox(), and compute where the painted vertical centre would land given the current main_top.
    - Assert the spread (max centre minus min centre) across all files is within a small tolerance of zero.
    - RED on the current code: the spread is 120.5px (621.0 for air-caraibes-atr72.png, 741.5 for generic-a330.png), so the check must fail before Task 2 and pass after it.
    - The check derives main_w and the anchor from render.py's own constants, never from hardcoded copies, so it keeps measuring the real render path if those constants move.
  </behavior>
  <action>
    Add a drift check to `server/test_render.py` following that harness's existing style (stdlib only, a named check function called from `main()`, any failure exits 1, nothing swallowed into a pass).

    Recompute `main_w` exactly as `_build_active_canvas()` does — inner width from `WIDTH` and `FRAME_INSET_FRAC`, times `MAIN_ILLUSTRATION_WIDTH_FRAC`, rounded — rather than hardcoding 992, so the check cannot silently drift away from the render path. Iterate every PNG under `server/assets/icons/illustrations/`, call `_resize_illustration()` then `_opaque_bbox()`, skip any file whose bbox is None (documented fallback case, not a failure), and compute the painted vertical midpoint in absolute canvas coordinates under whatever vertical anchor `_build_active_canvas()` currently applies.

    Set the tolerance to 2px — enough to absorb per-file rounding on a single rounded anchor, far tighter than the 120.5px defect. Name the tolerance as a module constant with a comment recording the pre-fix measurement (spread 120.5px, extremes named) so a future reader can tell a regression from a rounding wobble.

    Assert on the SPREAD, not on each file's absolute position: absolute position is the design constant Task 2 re-derives, and pinning it here would force this check to be edited in lockstep, which is exactly the "the test moved with the bug" failure mode. The spread is the invariant that must hold no matter what the constant becomes.

    Run it now and confirm it FAILS with the 120.5px spread before writing any render.py change.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 server/test_render.py; test $? -ne 0 && echo "RED as expected"</automated>
  </verify>
  <done>The new check runs, reports the real ~120.5px spread, and exits non-zero on unmodified render.py.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Anchor the main illustration's vertical position to its painted pixels</name>
  <files>server/plane/render.py, server/test_render.py, .planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md</files>
  <behavior>
    - _build_active_canvas() positions the main illustration with _top_for_centered_content(), the same helper the previous card already uses, instead of applying a raw fraction to the source rectangle's top.
    - Task 1's spread check passes (spread within 2px, down from 120.5px).
    - The developer-confirmed reference render's main aircraft keeps its current visible position: the re-derived constant reproduces the approved look rather than moving it.
    - Every other existing check in server/test_render.py still passes.
  </behavior>
  <action>
    Replace the rectangle-top anchor with a content-centre anchor.

    In `_build_active_canvas()`, `main_top` currently applies `MAIN_ILLUSTRATION_TOP_FRAC` to the source rectangle's top edge before the file is even loaded. Move the computation to after `main_resized` is available and route it through the existing `_top_for_centered_content()` helper — the exact helper the previous card uses at line 1942. Do not write a new helper: `_top_for_centered_content()` already reads `_opaque_bbox()`, already falls back to the full rectangle when nothing is painted, and already never raises. Reusing it is what keeps layout and painting provably on one threshold, which is the whole lesson of the originating debug session.

    Retire `MAIN_ILLUSTRATION_TOP_FRAC` and introduce `MAIN_ILLUSTRATION_CENTER_Y_FRAC` in its place, so the constant's name states which edge it means — the same naming move `PREVIOUS_ILLUSTRATION_CENTER_Y_FRAC` already made. Grep for every remaining reader of the old name before deleting it; if any other call site (text anchors, badge anchors, containment guards) reads it, convert or leave it deliberately and say which in the comment.

    Re-derive the new constant's VALUE from the developer-confirmed reference render recorded in 03-UI-SPEC.md, reproducing the approved on-glass look rather than redesigning it — this is the discipline the previous card's 0.76 -> 0.7528 correction already established, and its comment is the template. Measured values on this branch to derive from: with the current anchor, `air-france.png`'s painted centre sits at y=641.0 (frac 0.40063), `lot-polish-airlines.png` at 641.5 (0.40094), `air-caraibes.png` at 630.5 (0.39406), and the 43-file median at 649.5 (0.40594). If 03-UI-SPEC.md names `air-france.png` as the reference (it is this project's canonical reference file and heads test_render.py's own asset list), 0.4006 holds that file exactly where it renders today and moves no other file more than ~92px, most far less. Record the chosen value, the reference file it came from, and the measurement in the constant's own comment.

    Update the constant's comment to state why the fraction means the painted centre and not the rectangle top, citing the 118px top-padding spread (6px to 124px) and the 120.5px centre drift as the measured motivation — the same evidence-in-the-comment style lines 322-326 already use.

    Update `.planning/phases/03-visual-polish-on-real-glass/03-UI-SPEC.md`'s corresponding design-constant record so the spec and the code agree, exactly as the originating debug session did for its own constants.

    Note explicitly in the code comment that SIZING still derives from `.rect` (unchanged, line 1919-1931's reasoning stands) and only POSITION follows painted pixels — so a later reader does not "fix" the sizing to match.

    Do NOT touch `server/test_poll_loop.py`'s `_DEFAULT_CONFIG_DIGEST` in this task. This change moves real pixels, so that pin will now mismatch; Task 3 handles it through the established process.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 server/test_render.py</automated>
  </verify>
  <done>
    server/test_render.py exits 0. The drift spread is within 2px (was 120.5px). The reference file's main aircraft sits where it sat before the change. server/plane/render.py contains no remaining reader of the retired constant name.
  </done>
</task>

<task type="checkpoint:human-verify" gate="blocking-human">
  <what-built>
    The main illustration's vertical anchor now follows the aircraft's painted pixels, so its visible centre is fixed across all 43 vendored files instead of drifting 120.5px. A regression harness in server/test_render.py pins that invariant.
  </what-built>
  <how-to-verify>
    Two items need YOU, not the executor — neither may be performed by an agent.

    1. **panel.bin digest re-pin.** This change moves real rendered pixels, so `_DEFAULT_CONFIG_DIGEST` in `server/test_poll_loop.py` (currently `46c18ea48d711bf62520570367cd019e2144073019dabe1d4282766d3ae4be51`) will now mismatch. Per that constant's own documented discipline, the replacement value must be read from a **real CI run's FAIL output on this PR**, never computed locally — this repo has already recorded three distinct platform-dependent digests for identical code, so a locally-computed pin is known to be wrong. Push the branch, let CI fail, take the digest CI itself computed, and update the pin with a comment recording that this change is why it moved (a new digest is expected here, not a regression).

    2. **Deployment.** `.github/workflows/ci.yml`'s `deploy` job runs `deploy/deploy.sh` on push to `main`, gated behind the `production` environment's required reviewer — so production only updates when you approve that job. Two things to check:
       - Confirm whether the ORIGINAL fix (commit `cea4984`, "anchor flight text to the illustration's opaque pixels, not its rectangle", 2026-08-28) ever actually reached the VPS: open the Actions tab, find the `deploy` job for the main-branch run containing that commit, and check it was approved and succeeded rather than sitting pending. If it never ran, that is a second, independent reason the glass still looked wrong.
       - Once this plan's change merges, approve the new `production` deploy so the fix reaches the frame.

    The executor must not run `deploy/deploy.sh`, must not SSH to the VPS, and must not run `sudo systemctl` there — those are yours to run or approve.

    3. **On glass.** After the deploy lands, look at the frame across several different airlines and confirm the aircraft no longer jumps vertically between them. This is the confirmation the original debug session never got.
  </how-to-verify>
  <resume-signal>Type "approved" once the digest is re-pinned from CI and you have checked the deploy state, or describe what you found.</resume-signal>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| vendored asset -> renderer | PNG files under server/assets/icons/illustrations/ are repo-controlled, not user-supplied; already guarded by `_illustration_over_pixel_cap()` and `_load_illustration_safely()` |
| repo -> production VPS | `deploy/deploy.sh`, reachable only through the CI `deploy` job behind the `production` environment's required reviewer |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-260902req-01 | Tampering | production VPS via deploy.sh | high | mitigate | Executor is forbidden from running deploy.sh, SSH, or systemctl; deployment happens only through the CI job the developer approves (Task 3) |
| T-260902req-02 | Tampering | `_DEFAULT_CONFIG_DIGEST` integrity gate | medium | mitigate | Re-pin only from a real CI FAIL output, never a local computation — a locally-guessed pin would silently disarm the panel.bin integrity check |
| T-260902req-03 | Denial of Service | oversized illustration decode | low | accept | Unchanged by this plan; assets are repo-controlled and `_illustration_over_pixel_cap()` already bounds them |

No new external input crosses a trust boundary in this plan — it changes an internal layout constant and an anchor expression only. No package installs.
</threat_model>

<verification>
- `server/.venv/bin/python3 server/test_render.py` exits 0.
- The drift check reports a spread within 2px across all 43 vendored files.
- `server/.venv/bin/ruff check .` is clean.
- `./scripts/run-all-tests.sh` — the panel.bin digest check is EXPECTED to fail here until Task 3's CI-sourced re-pin; every other harness must pass.
</verification>

<success_criteria>
- The main aircraft's painted vertical centre is fixed across all 43 illustrations (was drifting 120.5px).
- The developer-confirmed reference render's aircraft position is unchanged.
- A regression harness fails if the drift returns.
- render.py and 03-UI-SPEC.md agree on the new constant.
- The digest re-pin and the production deploy are handed to the developer, not performed by the executor.
</success_criteria>

<output>
Create `.planning/quick/260902-req-fix-inconsistent-aircraft-centering-acro/260902-req-SUMMARY.md` when done.
Record: the chosen constant value and which reference file it was derived from, the pre/post drift spread, and the developer's findings on whether cea4984 had ever actually deployed.
</output>
