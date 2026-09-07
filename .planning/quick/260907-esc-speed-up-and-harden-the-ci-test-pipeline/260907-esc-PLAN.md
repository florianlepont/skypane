---
phase: quick-260907-esc
plan: 01
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - server/panel_format.py
  - server/plane/dither.py
  - server/plane/render.py
  - server/test_render.py
  - scripts/run_all_tests.py
  - scripts/run-all-tests.sh
  - pyproject.toml
  - README.md
  - server/README.md
  - .github/workflows/ci.yml
  - .github/workflows/firmware.yml
autonomous: true
requirements: [QT-esc-01, QT-esc-02, QT-esc-03]
user_setup: []

must_haves:
  truths:
    - "`./scripts/run-all-tests.sh` still runs all 16 harnesses under coverage, still enforces the pyproject.toml threshold, still reports every failure rather than stopping at the first — but finishes in a fraction of the 106 s sequential baseline because the harnesses run concurrently (one worker per CPU) and, on Python 3.12+, under coverage's sysmon core."
    - "The three hot-loop rewrites are byte-identical to the code they replace: `pack_panel()` returns the exact same 960,000 bytes for every canvas, `dithered_state_background()` returns a canvas with the same `tobytes()`, palette, mode and size, and `nibble_counts()` returns the same dict. This is proven by a direct old-vs-new comparison run, not inferred from the harnesses passing."
    - "Every harness's own check count is unchanged (911 total across 16 files) and coverage TOTAL stays at or above 83 % — no harness's check logic, no EXPECTED_CHECK_COUNT, and no coverage threshold is touched."
    - "A hung subprocess server can no longer stall CI until GitHub's 6-hour default kills the job: each harness is capped by HARNESS_TIMEOUT_S (default 600 s), and a timed-out harness is reported as a failure with its own reason line."
    - "`JOBS=1` reproduces the old serial behaviour, so a contributor debugging interleaved output has an escape hatch that does not require editing the runner."
    - "A docs-only push or PR (`.planning/**`, `**/*.md`, `.claude/**`, `LICENSE`) no longer triggers the 6-minute CI job at all, while `hardware/**` and `adsb-test/**` still do — ruff lints Python in both of those directories, so excluding them would silence a real lint gate."
    - "Superseded PR pushes cancel their in-flight CI run, and a newer push to `main` cancels an older deploy run still waiting on the production reviewer — approving a stale run can no longer rsync stale code onto the VPS."
    - "Every job in both workflow files has an explicit `timeout-minutes`, so no job can ever consume GitHub's 6-hour default."
    - "README.md, server/README.md and pyproject.toml describe the runner as it now behaves — 16 harnesses, 911 checks, concurrent by default — with no stale '15 harnesses / 394 checks' claim left anywhere."
    - "`git diff --stat` touches nothing outside scripts/, .github/workflows/, server/panel_format.py, server/plane/dither.py, server/plane/render.py, server/test_render.py, README.md, server/README.md and pyproject.toml."
  artifacts:
    - path: "scripts/run_all_tests.py"
      provides: "New stdlib-only concurrent runner: canonical 16-harness list, ThreadPoolExecutor with JOBS workers, longest-first submission, per-harness timeout, COVERAGE_CORE=sysmon on 3.12+, coverage combine/report, slowest-first timing table, GITHUB_STEP_SUMMARY markdown table"
    - path: "scripts/run-all-tests.sh"
      provides: "Thin wrapper preserving the PYTHON env contract, the exact interpreter-not-found error message, and the entry-point path CI and README both call; execs the Python runner"
    - path: "server/panel_format.py"
      provides: "`_HIGH_NIBBLE_TABLE` / `_LOW_NIBBLE_TABLE` module constants and a translate-plus-big-int-OR `pack_panel()` (0.085 s -> ~0.003 s per panel)"
    - path: "server/plane/dither.py"
      provides: "`_STATE_BACKGROUND_CACHE` memo and a translate-based remap in `dithered_state_background()`, returning `.copy()` on every path"
    - path: "server/plane/render.py"
      provides: "`_illustration_cache` keyed on (path, st_mtime_ns, st_size, target_w), removing ~650 redundant PNG decodes per test_render run"
    - path: "server/test_render.py"
      provides: "`Counter`-based `nibble_counts()` — same dict, one pass over 960,000 bytes in C instead of Python"
    - path: ".github/workflows/ci.yml"
      provides: "Top-level concurrency group, paths-ignore on both triggers, per-job timeout-minutes, a production-deploy concurrency group, and pip caching keyed on server/requirements*.txt"
    - path: ".github/workflows/firmware.yml"
      provides: "timeout-minutes: 30 on the build job"
  key_links:
    - "scripts/run-all-tests.sh -> scripts/run_all_tests.py: the wrapper is the stable entry point .github/workflows/ci.yml and README.md both name. If the wrapper's path or PYTHON contract changes, CI and the README break together — which is exactly why the wrapper survives instead of CI calling the .py directly."
    - "scripts/run_all_tests.py's HARNESSES list -> pyproject.toml [tool.coverage.run] parallel = true: concurrency is only safe because each `coverage run` child writes its own .coverage.* data file. Turning parallel mode off would silently corrupt the merged data. The pyproject comment must say so."
    - "server/panel_format.py's nibble tables -> INDEX_TO_NIBBLE: the tables are built from it at import time, so the two can never drift. The one behavioural difference — an index outside 0..5 now maps to nibble 0 instead of raising KeyError — is covered by the `len(raw) == WIDTH * HEIGHT` assert plus render.py's own `_assert_legal_palette()` and must be documented in the comment."
    - "server/plane/dither.py's `_STATE_BACKGROUND_CACHE` -> the mandatory `.copy()`: callers draw onto the returned canvas. Returning the cached object itself would let one render mutate the next one's background. The copy is the correctness contract, not an optimisation detail."
    - "ci.yml paths-ignore -> `server/.venv/bin/ruff check .`: ruff lints hardware/logtools.py and adsb-test/*.py, so those directories must stay OUT of paths-ignore or the lint gate goes dark for them."
    - "deploy job's `concurrency: production-deploy, cancel-in-progress: true` -> the `environment: production` approval pause: without it, a reviewer approving a queued older run deploys code that main has already moved past."
---

<objective>
Cut the CI test step from ~357 s to a fraction of it, and close three ways the pipeline can waste or misuse time: no per-job timeouts, no path filtering, and no run cancellation.

Purpose: a one-file PR currently pays 373 s of CI, and a docs-only PR pays the same — `main` has no branch protection, so the docs-only run gates nothing at all. The 357 s test step is dominated by four things measured this session: coverage's default tracer (which Python 3.12's sysmon core removes entirely), three pure-Python per-pixel/per-byte hot loops, and a strictly sequential runner on a 4-vCPU box where 15 of the 16 harnesses are short.

Output: a concurrent stdlib-only test runner behind the same `./scripts/run-all-tests.sh` entry point, three byte-identical hot-loop rewrites plus one harness-side one, and two hardened workflow files. No harness check logic, no EXPECTED_CHECK_COUNT, and no coverage threshold changes.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@scripts/run-all-tests.sh
@server/panel_format.py
@server/plane/dither.py
@.github/workflows/ci.yml
@.github/workflows/firmware.yml
</context>

<measurements>

Every number below was measured live during this task's diagnosis. Do NOT re-measure, re-profile, or re-derive any of it. Do not investigate whether a faster approach exists — the algorithms in Task 1 are already verified byte-identical.

**CI (GitHub, 4 vCPU, Python 3.12):** one-file PR = 373 s total; 357 s of it is the "Run full test suite" step. pip install 10 s, lint 0 s, attribution 1 s. Docs-only PRs pay the same 6 min because there is no path filter. `main` has NO branch protection and NO required status checks, so skipping the workflow on docs-only changes blocks nothing.

**Local baseline (M-series Mac, python3.11, sequential, under coverage): 106 s total.** server/test_render.py 59.4 s (56 %), server/test_poll_loop.py 22.8 s (22 %), companion/test_companion_app.py 8.9 s, stub-server/test_poll_cycle.py 3.8 s, server/test_panel_preview.py 3.5 s, companion/test_status_pages.py 2.6 s, server/test_pipeline_e2e.py 2.3 s; the other 9 harnesses < 1 s each. The GitHub runner is ~3.4x slower than this Mac.

**Coverage tracing overhead:** test_render 36.4 s uninstrumented / 60.3 s default core / **36.5 s with COVERAGE_CORE=sysmon on 3.12** — the overhead vanishes. test_poll_loop 10.9 / 16.0 / 10.9. pyproject.toml uses line coverage only (no `branch = true`), which sysmon fully supports on coverage 7.15.4.

**cProfile, test_render (48 s under profiler):** render.py build_canvas 29 s, of which dither.dithered_state_background 13.3 s (154 calls; 7.9 s of that is the pure-Python listcomp remap, the rest the deterministic 1200x1600 Floyd-Steinberg quantize); illustration load+resize 11 s (650 calls of `_resize_illustration` re-opening the same PNGs); panel_format.pack_panel 7.9 s (66 calls, 0.085 s/call); and the harness's own nibble_counts 9 s (40 calls). **cProfile, test_poll_loop:** pack_panel 10.7 s of 15.3 s (90 calls).

**Concurrency safety:** all 16 harnesses already use `mkdtemp` state dirs and OS-assigned free ports (socket bind to port 0) for their subprocess servers, and coverage already runs in parallel mode (one `.coverage.*` file per process). They are safe to run concurrently — this was checked, not assumed.

**Lint scope:** `ruff check .` covers the whole repo including hardware/logtools.py and adsb-test/*.py.

**Verified-identical prototype:** `/private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-test-pipeline-performance-48e44a/76df2e4b-3c66-40fa-8d82-5002e8a2bc70/scratchpad/proto.py` contains runnable old-vs-new comparisons for all three of Task 1's rewrites, verified byte-identical across 12 real canvases (4 themes x 3 states) plus a random 6-index canvas. Read it and copy the algorithms from it rather than re-deriving them.

**Interpreters (no venv exists inside this worktree — always pass PYTHON explicitly):**
- 3.11: `/Users/florian/Projects/skypane/server/.venv/bin/python3` (also provides `ruff` and `coverage`)
- 3.12: `/private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-test-pipeline-performance-48e44a/76df2e4b-3c66-40fa-8d82-5002e8a2bc70/scratchpad/venv312/bin/python3`

</measurements>

<tasks>

<task type="auto">
  <name>Task 1: Byte-identical hot-loop rewrites (pack_panel, dithered background, illustration cache, nibble_counts)</name>
  <files>server/panel_format.py, server/plane/dither.py, server/plane/render.py, server/test_render.py</files>
  <read_first>
    - `/private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-test-pipeline-performance-48e44a/76df2e4b-3c66-40fa-8d82-5002e8a2bc70/scratchpad/proto.py` — the verified prototypes; copy the algorithms from here.
    - `server/panel_format.py` — INDEX_TO_NIBBLE (line 70), WIDTH/HEIGHT/ROW_BYTES/IMAGE_BYTES (lines 13-16), pack_panel (~line 107).
    - `server/plane/dither.py` — dithered_state_background (line 54).
    - `server/plane/render.py` — the existing `_font_cache` pattern (~line 515) to match style; `_resize_illustration` (~line 996); `_load_illustration_safely` (~line 942), which is the only caller.
    - `server/test_render.py` — nibble_counts / dominant_nibble (~lines 108-118) and the import block at the top.
  </read_first>
  <action>
Four independent rewrites, all four of which must preserve output exactly. Do not change any harness's check logic, any EXPECTED_CHECK_COUNT, or the coverage threshold.

**(a) server/panel_format.py — pack_panel().** Add two module-level 256-entry translation tables immediately below INDEX_TO_NIBBLE: `_HIGH_NIBBLE_TABLE` built as `bytes(INDEX_TO_NIBBLE.get(i, 0) << 4 for i in range(256))` and `_LOW_NIBBLE_TABLE` as `bytes(INDEX_TO_NIBBLE.get(i, 0) for i in range(256))`. Rewrite the body to: take `raw = canvas.tobytes()` — a "P"-mode canvas's tobytes() is exactly one palette-index byte per pixel, row-major, the same sequence getdata() yielded; assert `len(raw) == WIDTH * HEIGHT`; slice `raw[0::2]` (the left pixel of every pair) and `.translate(_HIGH_NIBBLE_TABLE)`, slice `raw[1::2]` and `.translate(_LOW_NIBBLE_TABLE)`; combine with `(int.from_bytes(high, "big") | int.from_bytes(low, "big")).to_bytes(len(high), "big")`. Keep `assert len(out) == IMAGE_BYTES` and keep the docstring's wire-format contract (1600 rows x 600 bytes, 2 px per byte, LEFT pixel in the HIGH nibble) intact. Add a comment covering three things: why the big-integer OR is a per-byte OR (the two operands are equal-length big-endian integers and no bit position carries, because high nibbles and low nibbles never overlap); the measured 0.085 s -> ~0.003 s per panel; and the one behavioural difference — the old dict lookup raised KeyError for a palette index outside 0..5, whereas the tables map any unknown index to nibble 0. Note that the `len(raw) == WIDTH * HEIGHT` assert plus render.py's existing `_assert_legal_palette()` dominance check are what keep that from being a silent hole.

**(b) server/plane/dither.py — dithered_state_background().** Replace the `local_indices = dithered.getdata()` plus `canvas.putdata([...])` remap with a translate: build `remap = bytes([bg_idx, pf.IDX_WHITE] + [0] * 254)` and construct `canvas = Image.frombytes("P", (WIDTH, HEIGHT), dithered.tobytes().translate(remap))`, then `canvas.putpalette(pf.padded_palette())` exactly as before. Update the comment above it that currently describes the getdata/putdata remap so it describes the translate instead — the reason for the remap (local indices 0/1 onto the canvas's real index space) is unchanged and must be kept. Then memoize: module-level `_STATE_BACKGROUND_CACHE = {}` keyed by `(bg_idx, lighten_fraction)`; on a hit return `cached.copy()`; on a miss compute, store, and return `.copy()`. The copy is mandatory on BOTH paths — callers draw onto the returned canvas with ImageDraw, so handing back the cached object itself would let one render mutate the next one's background. Note in the comment that the function is pure (a flat field through Floyd-Steinberg against a fixed 2-entry palette is deterministic), which is what makes the memo sound.

**(c) server/plane/render.py — `_resize_illustration()`.** Add a module-level `_illustration_cache = {}` in the same style as the existing `_font_cache`. Key on `(path, st.st_mtime_ns, st.st_size, target_w)` obtained from `os.stat(path)`; if `os.stat` raises OSError, fall through to the uncached load path unchanged (the caller `_load_illustration_safely()` already has its own try/except ladder and must keep seeing the same exceptions). Cache the resized RGBA image and return `.copy()` on both hit and miss — the caller composites onto it. Comment: production `poll_loop.py` is a oneshot process per systemd timer so this is a no-op there; it exists to remove ~650 redundant PNG decodes in test_render and to speed up the long-lived companion's panel previews.

**(d) server/test_render.py — nibble_counts().** Add `from collections import Counter` to the import block. Count byte values once with `Counter(buf)`, then expand each distinct byte value into its two nibbles weighted by that byte's count, accumulating into the same `{nibble: count}` dict shape the old loop produced. `dominant_nibble()` is unchanged.
  </action>
  <verify>
    <automated>
Write an old-vs-new comparison script into the scratchpad (NOT into the repo — the diff must stay clean), adapted from proto.py: inline the four PRE-change implementations verbatim, import the four post-change ones, and compare across all 6 legal background indices for the dither path, 12 real canvases (4 themes x 3 states via render.build_canvas) plus one random 6-index canvas for pack_panel, and the packed bytes of each for nibble_counts. It must print an all-identical verdict.

PY=/Users/florian/Projects/skypane/server/.venv/bin/python3
cd /Users/florian/Projects/skypane/.claude/worktrees/test-pipeline-performance-48e44a
$PY /private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-test-pipeline-performance-48e44a/76df2e4b-3c66-40fa-8d82-5002e8a2bc70/scratchpad/verify_identity.py
for h in server/test_render.py server/test_dither.py server/test_panel_preview.py server/test_pipeline_e2e.py server/test_poll_loop.py server/test_illustrations.py; do $PY "$h" || echo "FAILED $h"; done
$PY -m ruff check . 2>/dev/null || /Users/florian/Projects/skypane/server/.venv/bin/ruff check .
    </automated>
  </verify>
  <done>
The comparison script reports every canvas identical. render 127/127, dither 6/6, panel-preview 11/11, pipeline-e2e 6/6, poll-loop 51/51, illustrations 58/58 — all exit 0 with unchanged counts. ruff clean. `git diff --name-only` lists exactly the four files. Commit: `perf(quick-esc): vectorise panel packing, dithered backgrounds and nibble counting`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Concurrent Python test runner behind the existing shell entry point, plus docs</name>
  <files>scripts/run_all_tests.py, scripts/run-all-tests.sh, pyproject.toml, README.md, server/README.md</files>
  <read_first>
    - `scripts/run-all-tests.sh` in full — the 16-harness array (lines 42-59) is the single source of truth and moves verbatim, comment and all; the PYTHON contract (lines 25-31), the "no `set -e`, report every failure" rationale (lines 14-18), and the coverage combine/report/cleanup sequence (lines 76-91) all carry over.
    - `pyproject.toml` `[tool.coverage.run]` — the `parallel = true` comment that says "15 independent processes".
    - `README.md` Tests section (~lines 84-97).
    - `server/README.md` "Running the tests" (~lines 28-40).
  </read_first>
  <action>
**New `scripts/run_all_tests.py`** — stdlib only (os, sys, subprocess, time, tempfile, threading, concurrent.futures, shutil). Must stay clean under ruff's E4/E7/E9/F selection.

Structure:
- Module docstring carrying over the shell script's header intent: single entry point for the whole suite, one list in one place, no drift between local and CI.
- `HARNESSES` — the canonical 16-file list copied verbatim from the bash array, in the same readable alphabetical-by-directory order, carrying over the M1 comment about it being the single source of truth CI and README both defer to (including the note that 04-CONTEXT.md's D-07 7-file list is known-stale and must not be "corrected" back down to).
- A separate `EXPECTED_SLOWEST` tuple (or small dict of measured seconds) used ONLY for submission ordering, so the canonical list itself stays readable: server/test_render.py, server/test_poll_loop.py, companion/test_companion_app.py, stub-server/test_poll_cycle.py, server/test_panel_preview.py, companion/test_status_pages.py, server/test_pipeline_e2e.py, then everything else in list order. Longest-first submission puts the critical path in flight immediately.
- Worker count: `int(os.environ.get("JOBS") or os.cpu_count() or 1)`. JOBS=1 gives the old serial behaviour.
- Repo root resolved from this file's location; every subprocess runs with `cwd` = repo root.
- Child env: a copy of `os.environ`; if `sys.version_info >= (3, 12)` and "COVERAGE_CORE" is not already in os.environ, set `env["COVERAGE_CORE"] = "sysmon"`. Comment it with the measured numbers (test_render 60 s -> 36 s; the whole tracing overhead disappears), and state both guards explicitly: the variable is left alone on older interpreters where the sysmon core does not exist, and an explicit COVERAGE_CORE from the caller always wins.
- Each harness runs as `[sys.executable, "-m", "coverage", "run", harness]` via `subprocess.Popen`, with stdout and stderr both redirected to a per-harness file inside one `tempfile.mkdtemp()` directory (a file, not a pipe — a pipe can deadlock a chatty harness against a full OS buffer). Wait with `timeout=float(os.environ.get("HARNESS_TIMEOUT_S", "600"))`; on `subprocess.TimeoutExpired` call `proc.kill()` then `proc.wait()` and record the harness as failed with reason "timed out after N s". Comment that this timeout is what stops a hung subprocess server from stalling CI until GitHub's 6-hour default.
- Concurrency via `concurrent.futures.ThreadPoolExecutor(max_workers=workers)` — threads, not processes, because every worker just waits on a child process.
- Per-completion reporting, guarded by a `threading.Lock` so blocks never interleave. Do NOT print a "starting" line per harness. On success print `==> PASS  <harness>  (<wall>s)` followed by the harness's last non-empty output line (its own "name: N/N checks pass" summary). On failure or timeout print `==> FAIL  <harness>  (<wall>s, exit <code>)` followed by the harness's FULL captured output — a contributor debugging a break gets the whole picture in one run.
- Before starting: delete `.coverage` and every `.coverage.*` in the repo root (the old `rm -f .coverage .coverage.*`). After all harnesses finish: run `coverage combine` then `coverage report` through `sys.executable -m coverage`, capture the report's exit status as COVERAGE_STATUS (the threshold comes from pyproject.toml and is never restated here), then delete the data files again.
- Carry over the shell script's warning that `--append` must never be passed alongside parallel mode — coverage.py rejects the combination outright.
- Print a slowest-first timing table (harness, wall seconds, status), the total wall time, and the worker count. If `os.environ.get("GITHUB_STEP_SUMMARY")` is set, append the same table to that file as a Markdown table.
- Exit code: 1 if any harness failed or timed out OR COVERAGE_STATUS is non-zero, else 0. Print `==> Result: PASS` / `==> Result: FAIL` and list the failed harnesses exactly as the old script did. Every harness always runs — never abort early on the first failure.
- Remove the temp directory at the end (`shutil.rmtree`).
- No argument parsing beyond `if __name__ == "__main__": sys.exit(main())`; all configuration is env vars (PYTHON, JOBS, HARNESS_TIMEOUT_S, COVERAGE_CORE).

**`scripts/run-all-tests.sh` becomes a thin wrapper.** Keep the header comment's intent (single entry point; CI and README both call this, not the file list), updated to say the harness list and orchestration now live in run_all_tests.py alongside it and why (the concurrency, timeout and reporting logic outgrew bash). Keep `set -uo pipefail`, keep resolving HERE and REPO_ROOT and `cd "${REPO_ROOT}"`, keep the identical `PYTHON="${PYTHON:-${REPO_ROOT}/server/.venv/bin/python3}"` default and the byte-identical three-line "interpreter not found or not executable" error block including both follow-up hint lines and `exit 1`. Then `exec "${PYTHON}" "${HERE}/run_all_tests.py" "$@"`. Keep the file executable.

**`pyproject.toml`** `[tool.coverage.run]`: change "15 independent processes" to 16, and extend that comment to say the processes now run concurrently and that parallel mode — one data file per process — is precisely what makes concurrent execution safe. Leave `parallel`, `source`, `omit` and `fail_under` values untouched.

**`README.md`** Tests section: keep "This is the **exact same command CI runs**" and the no-pytest-by-design paragraph. Correct the stale count to 16 harnesses and 911 checks total. Add that the runner executes them concurrently by default (one worker per CPU), that `JOBS=1` reproduces the old serial output, that `HARNESS_TIMEOUT_S` caps any single harness, and that the slowest-first timing table printed at the end is how to spot slow-test creep.

**`server/README.md`**: adjust only if it describes the runner's behaviour. Its "Running the tests" section documents running individual harnesses directly, which is still exactly true — if nothing there is now false, leave it alone and say so in the summary rather than editing for the sake of it.
  </action>
  <verify>
    <automated>
cd /Users/florian/Projects/skypane/.claude/worktrees/test-pipeline-performance-48e44a
time PYTHON=/Users/florian/Projects/skypane/server/.venv/bin/python3 ./scripts/run-all-tests.sh
time PYTHON=/private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-test-pipeline-performance-48e44a/76df2e4b-3c66-40fa-8d82-5002e8a2bc70/scratchpad/venv312/bin/python3 ./scripts/run-all-tests.sh
JOBS=1 PYTHON=/Users/florian/Projects/skypane/server/.venv/bin/python3 ./scripts/run-all-tests.sh
PYTHON=/nonexistent/python3 ./scripts/run-all-tests.sh; echo "expect exit 1, got $?"
/Users/florian/Projects/skypane/server/.venv/bin/ruff check .
    </automated>
  </verify>
  <done>
All three suite runs exit 0 with 16/16 harnesses PASS and these exact counts: companion-app 148/148, config-history 44/44, config-page 87/87, contrast-check 36/36, dither 6/6, enrich 52/52, illustrations 58/58, panel-preview 11/11, pipeline-e2e 6/6, plane-detection 47/47, poll-cycle 34/34, poll-loop 51/51, render 127/127, runway-config 14/14, status-pages 136/136, view-pages 54/54; coverage TOTAL at or above 83 % in each. The 3.12 run exercises the sysmon branch CI will take. The bad-PYTHON run prints the unchanged error message and exits 1. ruff clean. Record the concurrent wall time against the 106 s sequential baseline. Commit: `perf(quick-esc): run the 16 harnesses concurrently under a Python runner`.
  </done>
</task>

<task type="auto">
  <name>Task 3: Workflow hardening — path filters, concurrency groups, job timeouts, pip cache</name>
  <files>.github/workflows/ci.yml, .github/workflows/firmware.yml</files>
  <read_first>
    - `.github/workflows/ci.yml` in full — the header comment's existing rationale (one file two jobs; why not the two-file split; why firmware lives separately) is kept and extended, not replaced. Note the stale "all 9 harnesses" phrase on line 3.
    - `.github/workflows/firmware.yml` — the `build` job.
  </read_first>
  <action>
**`.github/workflows/ci.yml`:**
- Add a top-level `concurrency` block: group `ci-${{ github.ref }}`, `cancel-in-progress: ${{ github.event_name == 'pull_request' }}`. Superseded PR pushes cancel the previous run; a push to main is never cancelled at this level, because its deploy job may be sitting on the production approval.
- Add `paths-ignore` under BOTH the `push` and the `pull_request` triggers, listing `'**/*.md'`, `'.planning/**'`, `'.claude/**'`, `'LICENSE'`. Do NOT add `hardware/**` or `adsb-test/**` — `ruff check .` lints Python in both, and excluding them would silence a real gate. Note in the comment that this is safe specifically because `main` has no branch protection and no required status checks, so a skipped run blocks nothing.
- Add `timeout-minutes: 20` to the `test` job and `timeout-minutes: 30` to the `deploy` job.
- Add a job-level `concurrency` block on `deploy`: group `production-deploy`, `cancel-in-progress: true`, so a newer push to main cancels an older run still waiting for the reviewer. Comment why: approving a stale queued run would rsync code main has already moved past onto the production VPS.
- On the `actions/setup-python@v5` step add `cache: pip` and `cache-dependency-path: server/requirements*.txt`.
- Update the header comment to describe all of the above while keeping every bit of its existing rationale. While there, correct the stale "all 9 harnesses" to 16.
- Change nothing else: the deploy job's `environment: production`, the known_hosts handling, and the `./deploy/deploy.sh` invocation stay exactly as they are.

**`.github/workflows/firmware.yml`:** add `timeout-minutes: 30` to the `build` job. Nothing else changes.
  </action>
  <verify>
    <automated>
cd /Users/florian/Projects/skypane/.claude/worktrees/test-pipeline-performance-48e44a
PY=/Users/florian/Projects/skypane/server/.venv/bin/python3
$PY - <<'EOF'
import sys
try:
    import yaml
except ImportError:
    sys.exit("PyYAML unavailable - validate with: gh workflow view / actionlint instead")
for f in (".github/workflows/ci.yml", ".github/workflows/firmware.yml"):
    d = yaml.safe_load(open(f))
    print(f, "jobs:", list(d["jobs"]))
    for name, job in d["jobs"].items():
        assert "timeout-minutes" in job, (f, name, "missing timeout-minutes")
    print("  all jobs have timeout-minutes")
EOF
grep -n 'paths-ignore' -A 6 .github/workflows/ci.yml
grep -n 'concurrency' -A 3 .github/workflows/ci.yml
grep -n 'cache' .github/workflows/ci.yml
git diff --stat
    </automated>
  </verify>
  <done>
Both workflow files parse as YAML (or, if PyYAML is unavailable in that venv, validate with `actionlint` or `gh workflow view` and say which was used). Every job in both files has `timeout-minutes`. ci.yml has a top-level concurrency group keyed on the ref with PR-only cancellation, `paths-ignore` on both triggers containing exactly the four documented entries and neither `hardware/**` nor `adsb-test/**`, a `production-deploy` concurrency group on the deploy job, and pip caching on the setup-python step. `git diff --stat` for the whole task set touches nothing outside scripts/, .github/workflows/, server/panel_format.py, server/plane/dither.py, server/plane/render.py, server/test_render.py, README.md, server/README.md and pyproject.toml. Commit: `ci(quick-esc): add path filters, concurrency groups and job timeouts`.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| CI runner -> production VPS | The deploy job holds an SSH key and rsyncs onto the live host; what it deploys is whatever commit the run was queued for |
| Harness subprocess -> runner process | 16 child processes now run concurrently, each writing its own captured output file and its own coverage data file |
| Repo tree -> `ruff check .` | The lint gate's coverage is defined by which paths trigger the workflow at all |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-esc-01 | Tampering | ci.yml deploy job | high | mitigate | Job-level `concurrency: production-deploy, cancel-in-progress: true` — a reviewer approving a stale queued run can no longer rsync a superseded commit over the VPS (Task 3) |
| T-esc-02 | Denial of Service | scripts/run_all_tests.py | medium | mitigate | Per-harness `HARNESS_TIMEOUT_S` (default 600 s) with `proc.kill()` + `proc.wait()`, plus `timeout-minutes` on every job — a hung subprocess server can no longer hold a runner for GitHub's 6-hour default (Tasks 2, 3) |
| T-esc-03 | Repudiation | ci.yml paths-ignore | medium | mitigate | `hardware/**` and `adsb-test/**` deliberately excluded from paths-ignore so `ruff check .` keeps gating the Python in them; only `.md`, `.planning/**`, `.claude/**` and `LICENSE` skip CI (Task 3) |
| T-esc-04 | Tampering | server/panel_format.py pack_panel | medium | accept | The new translation tables map an out-of-range palette index to nibble 0 where the old dict raised KeyError. Accepted because the tables are derived from INDEX_TO_NIBBLE at import time, `len(raw) == WIDTH * HEIGHT` is asserted, and render.py's `_assert_legal_palette()` already rejects illegal indices upstream — but the divergence is documented in the code comment rather than left for a reader to discover (Task 1) |
| T-esc-05 | Information Disclosure | concurrent coverage data | low | accept | Concurrency is only safe because every harness already uses mkdtemp state dirs and port-0 binds and coverage runs in parallel mode; verified during diagnosis, and the pyproject comment now records the dependency (Task 2) |
| T-esc-SC | Tampering | package installs | n/a | accept | No new dependency is added by any task — the runner is stdlib-only and the rewrites use Pillow and stdlib APIs already in use. No package legitimacy gate applies |
</threat_model>

<verification>
Run from the worktree root, `/Users/florian/Projects/skypane/.claude/worktrees/test-pipeline-performance-48e44a`:

1. `PYTHON=/Users/florian/Projects/skypane/server/.venv/bin/python3 ./scripts/run-all-tests.sh` — Python 3.11, no sysmon branch. 16/16 PASS, counts as listed in Task 2's `<done>`, coverage TOTAL >= 83 %.
2. `PYTHON=/private/tmp/claude-501/-Users-florian-Projects-skypane--claude-worktrees-test-pipeline-performance-48e44a/76df2e4b-3c66-40fa-8d82-5002e8a2bc70/scratchpad/venv312/bin/python3 ./scripts/run-all-tests.sh` — Python 3.12, exercises the COVERAGE_CORE=sysmon branch CI will take. Same pass/counts/threshold.
3. `JOBS=1 ... ./scripts/run-all-tests.sh` — serial mode still works.
4. `/Users/florian/Projects/skypane/server/.venv/bin/ruff check .` — clean.
5. Report the new runner's wall time against the 106 s sequential baseline, for both interpreters.
6. `git diff --stat` touches nothing outside scripts/, .github/workflows/, server/panel_format.py, server/plane/dither.py, server/plane/render.py, server/test_render.py, README.md, server/README.md, pyproject.toml.
</verification>

<success_criteria>
- Three atomic commits, one per task.
- All 16 harnesses pass under both interpreters with the exact check counts above and coverage at or above 83 %.
- The old-vs-new comparison run reports byte-identical output for pack_panel, dithered_state_background and nibble_counts.
- Concurrent wall time is a large fraction below 106 s and is reported explicitly for both interpreters.
- ruff clean; `git diff --stat` confined to the nine permitted paths.
- No harness check logic, no EXPECTED_CHECK_COUNT, and no coverage threshold was modified.
</success_criteria>

<output>
Create `.planning/quick/260907-esc-speed-up-and-harden-the-ci-test-pipeline/260907-esc-SUMMARY.md` when done.
</output>
