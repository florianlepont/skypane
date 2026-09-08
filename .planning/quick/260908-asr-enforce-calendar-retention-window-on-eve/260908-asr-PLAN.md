---
phase: quick/260908-asr
plan: 01
type: execute
wave: 1
depends_on: []
branch: claude/t-16-priv-retention   # STAY HERE. Do not create, switch, rebase, or add a worktree.
                                     # We are in worktree test-pipeline-performance-48e44a, based off
                                     # claude/seed-3-roster-highlight (tip 66823a3), which carries all
                                     # of phase 16. Phase 16 is NOT on main.
files_modified:
  - server/plane/calendar_rules.py
  - server/test_calendar_rules.py
  - server/test_poll_loop.py
  - companion/test_config_page.py
autonomous: true
requirements: []           # Decision-point-tracked quick task, the same precedent every 06.x/quick
                           # plan in this repo follows (see STATE.md: "Plan has `requirements: []`
                           # (Decision-ID-tracked phase)"). Traceability is via `decisions` below,
                           # cited inline in every task action.
closes: T-16-PRIV          # .planning/phases/16-calendar-linked-flight-highlighting-a-connected-calendar-sou/16-SECURITY.md
                           # "Open Threats" — open at medium, below the `high` block threshold.

decisions:
  - D-01  # _rebuild_capped_entries() is the ONE place responsible for the window, because it is
          # already the ONE place both load_calendar_registry() and write_calendar_registry()
          # route every entry list through. Two places that both trim is how the invariant drifts.
  - D-02  # select_window_entries() stays the SOLE implementation of the window rule — call it from
          # the helper. Never reimplement, inline, or duplicate its edge computation anywhere.
  - D-03  # Thread an explicit `now` through _rebuild_capped_entries() (required 3rd positional),
          # load_calendar_registry(state_dir, now=None) and
          # write_calendar_registry(..., now=None); None means real current time.
          # Keep the cap-as-you-go loop that bounds work on a hostile file, THEN window survivors.
  - D-04  # refresh_calendar_registry()'s failure path must persist AND return a windowed list, and
          # the returned in-memory result_registry["entries"] must match what was persisted on BOTH
          # paths.
  - D-05  # Update every docstring that states the old contract. This module's docstrings are
          # unusually load-bearing — match their existing voice and depth.

must_haves:
  truths:
    - "An entry that ended 10 days ago is gone from the RAW bytes of {state_dir}/calendar_rules.json after a single failing refresh cycle, and stays gone across three consecutive failing cycles — the exact scenario the security auditor reproduced against shipped code (D-04)"
    - "load_calendar_registry() and write_calendar_registry() agree on the window by construction: for any entry list and any `now`, the entries the loader returns are exactly select_window_entries(list, now) (D-01, D-02)"
    - "select_window_entries() remains the only place the window's two edges are computed — the helper calls it rather than recomputing day-start or the forward edge (D-02)"
    - "A hostile, non-finite, boolean, or absent `now` degrades to real current time and TRIMS the registry, and never silently EMPTIES it (D-03)"
    - "refresh_calendar_registry()'s returned registry['entries'] is byte-equal to the entries readable from the raw file on both the success and the failure path (D-04)"
    - "No harness check depends on the wall clock: every check that persists or loads registry entries passes an explicit `now`"
    - "scripts/run-all-tests.sh is green at 19/19 and server/.venv/bin/ruff check . is clean"
    - "server/plane/calendar_rules.py's AST-derived import set gains exactly one stdlib name and the module stays a leaf"
  artifacts:
    - "server/plane/calendar_rules.py — windowed _rebuild_capped_entries(), `now`-threaded load/write/refresh, updated load-bearing docstrings"
    - "server/test_calendar_rules.py — 4 new checks including the consecutive-failing-refresh on-disk retention check, plus explicit `now` on every persisting check, plus a re-derived EXPECTED_CHECK_COUNT"
    - "server/test_poll_loop.py — explicit `now` on all 8 direct write_calendar_registry() call sites"
    - "companion/test_config_page.py — explicit `now` on both direct write_calendar_registry() call sites"
  key_links:
    - "_rebuild_capped_entries() -> select_window_entries() — the single call that makes load and write agree; if this link is ever removed the invariant silently reverts to today's bug"
    - "refresh_calendar_registry() -> load_calendar_registry(state_dir, now) — because the top-of-function load is now windowed, the failure path's re-persist becomes correct WITHOUT its own trim call. This is the load-bearing consequence of D-01"
    - "the required new check -> json.load() on the raw file, NOT load_calendar_registry() — reading through the now-windowing loader would mask a stale on-disk entry, which is precisely the blind spot that let T-16-PRIV ship"
---

<objective>
Close T-16-PRIV: enforce the D-03 rolling-window retention bound on every persist and load
path in `server/plane/calendar_rules.py`, not only on the success path of
`refresh_calendar_registry()`.

Purpose: `{state_dir}/calendar_rules.json` holds a named person's near-term work schedule
on a VPS. Today a feed that breaks and stays broken leaves the last successful fetch on
disk indefinitely, re-persisted verbatim every 30 minutes with no expiry — the opposite of
the declared mitigation ("retention is bounded to the current UTC day plus 48 hours").
Impact is privacy-at-rest only and non-blocking, but the declared control is genuinely
unenforced on that path, not merely unproven.

Output: one module change routing the window through the single shared helper both the
loader and the writer already use, the harness churn that change empirically causes, and
the regression check the original goal verification missed.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.claude/CLAUDE.md

The auditor's full write-up — read the "Open Threats / T-16-PRIV" section:
@.planning/phases/16-calendar-linked-flight-highlighting-a-connected-calendar-sou/16-SECURITY.md

The module under change and its harness:
@server/plane/calendar_rules.py
@server/test_calendar_rules.py
</context>

<project_skills>
`.claude/skills/sketch-findings-skypane/` is the companion web app's visual design-system
reference (colour, typography, spacing, cards, control density, navigation, page patterns).
This plan touches `server/plane/calendar_rules.py` and three test harnesses only — zero CSS,
zero markup, zero rendered copy. The skill imposes no rules on this work and needs no update.
Do not edit `companion/static/style.css` or any page module.
</project_skills>

<hard_constraints>
- Stdlib-only server. NO new dependencies. `server/requirements.txt` must stay byte-identical.
- `calendar_rules.py` must stay a LEAF module. It may import `server.device_config`. It must
  not gain an import of any module outside its current AST import set beyond the one stdlib
  name D-03 requires. The four first-party modules its own docstring already names as
  forbidden stay forbidden.
- Every harness carries an `EXPECTED_CHECK_COUNT` ledger and exits non-zero on mismatch.
  Add checks, then RE-DERIVE the count by RUNNING the harness — never by arithmetic.
- Do NOT special-case, weaken, or bypass the window to keep an old check green. If a check
  goes red, either its fixture timestamps belong inside a window it controls, or the check
  is genuinely about retention and the window is right.
</hard_constraints>

<tasks>

<task type="auto">
  <name>Task 1: Route the window through the single shared helper, thread `now`, and repair the harness churn that causes</name>

  <files>
    server/plane/calendar_rules.py
    server/test_poll_loop.py
    companion/test_config_page.py
    server/test_calendar_rules.py
  </files>

  <action>
Implement D-01, D-02, D-03, D-04 and D-05 in `server/plane/calendar_rules.py`, then repair —
empirically, never by assumption — every harness check the change breaks.

**Module change.**

1. Add `time` to the stdlib import block (currently `ipaddress, json, math, os, re, socket,
   sys, threading`, then the `from datetime` / `from urllib.parse` lines). Place it after
   `threading` to keep that block alphabetical. This is the one new name D-03 permits.

2. Add a small private resolver for the retention clock — a function that returns
   `time.time()` when its argument is `None`, a `bool`, not an `int`/`float`, or not
   `math.isfinite()`, and otherwise returns `float(argument)`. Rationale worth stating in
   its docstring: `select_window_entries()` returns `[]` for any `now` it cannot convert to
   a UTC datetime, so an unguarded hostile value would silently ERASE a valid registry
   instead of trimming it. Reuse the module's existing bool-reject plus finite-check
   discipline verbatim — `_normalise_calendar_entry()` already applies exactly this pair and
   explains why in its own comment.

3. `_rebuild_capped_entries(raw_entries, context, now)` — add `now` as a REQUIRED third
   positional parameter, not a defaulted one (per D-03): a future caller must not be able to
   silently skip the window. Keep the existing cap-as-you-go loop and the existing
   drop-count warning exactly as they are, then `return select_window_entries(survivors,
   resolved_now)` where `resolved_now` comes from step 2. Per D-02 this is a CALL to the
   sole implementation — do not recompute the day-start edge, the forward edge, or
   `CALENDAR_WINDOW_FORWARD_S` anywhere in this helper.

   Three consequences to record in the docstring per D-05, because each is a real behaviour
   change a future reader would otherwise trip over:
   - **The window's own drops are deliberately NOT folded into the drop-count warning.**
     That warning classifies an anomaly (malformed, unsafe, or beyond the cap). Routine
     expiry is the designed steady state, and `load_calendar_registry()` runs on every
     companion page render — folding expiry in would flood the journal on every read of a
     file more than a day old and reclassify normal retention as a fault.
   - **Order.** Cap first, then window. The cap bounds work on a hostile file; the window
     then applies to survivors. The accepted cost: a file whose in-window entries sit beyond
     the cap position yields fewer than `CALENDAR_MAX_ENTRIES`. That is the hostile-file
     bound doing its job, not a defect.
   - **Sort.** `select_window_entries()` returns its result sorted ascending by `start_at`,
     so both the loader's output and the persisted file are now sorted. Previously both
     preserved file/caller order.

4. `load_calendar_registry(state_dir, now=None)` and
   `write_calendar_registry(state_dir, entries, last_attempt_at, last_synced_at, now=None)`
   — add the keyword and pass it into `_rebuild_capped_entries()`. In
   `write_calendar_registry()`'s docstring, state that `now` is the RETENTION clock and is
   deliberately not the same thing as `last_attempt_at`, which is the THROTTLE clock and may
   legitimately be `None` or a past value; conflating them would tie expiry to fetch pacing.
   `companion/app.py:1033` calls the loader positionally with one argument — the keyword
   default keeps that call site working unchanged, and it only reads `last_synced_at`, so its
   behaviour is unaffected.

5. `refresh_calendar_registry()` — per D-04, thread `now` into all four registry calls: the
   top-of-function `load_calendar_registry(state_dir, now)`, the failure-path
   `write_calendar_registry(..., now=now)`, the success-path
   `write_calendar_registry(..., now=now)`, and the `except Exception` fallback
   `load_calendar_registry(state_dir, now)`.

   That is the ENTIRE body change. Note in the docstring why, because it is the point of the
   whole design: the failure path's re-persist of `registry["entries"]` becomes correct
   without gaining a trim call of its own, purely because the list it re-persists was already
   windowed by the top-of-function load against the same `now`. One place owns the invariant;
   the failure path inherits it. Both paths therefore satisfy D-04's second half —
   `result_registry["entries"]` matches what was persisted, because the same `now` windowed
   both — with no second implementation and no re-read.

6. Docstrings per D-05. Update `_rebuild_capped_entries`, `load_calendar_registry`,
   `write_calendar_registry` and `refresh_calendar_registry` so they describe the window as
   part of the invariant. In particular `write_calendar_registry`'s existing sentence — that
   a caller can never persist what the loader would only drop again on the next read — is
   currently true for shape and the entry cap and false for the window; make it true.

   Also fix one module-scope claim the change falsifies: `calendar_fetch_is_due()`'s
   docstring asserts that this module defines no clock of its own and that `now` is always
   passed in. After step 2 that is no longer true at module scope. Rewrite that sentence so
   the claim is scoped to `calendar_fetch_is_due()` itself and names the one new default-clock
   seam, rather than leaving a load-bearing docstring asserting something the code no longer
   honours.

**Harness churn — derive it empirically. Run the harnesses, read the failures, then repair.**

Apply one rule everywhere rather than patching case by case: **any check that persists or
loads registry entries must pass an explicit `now` it controls.** No check may depend on the
wall clock. Where a check's real subject is merge/replace/cap/rendering semantics rather than
retention, thread a `now` that brackets the fixture timestamps the check already uses — do
not weaken the window, and do not rewrite the fixtures into "roughly now" values, which would
just push the time bomb further out.

Three known fronts, verified against the tree at plan time. Confirm each by running, and
expect the list to be incomplete:

- `server/test_poll_loop.py` — 8 direct `write_calendar_registry(...)` call sites (around
  `:3030, :3115, :3147, :3178, :3230, :3271, :3317, :3400`). **These WILL break, contrary to
  the initial expectation that this harness would survive.** `CLOCK_BASE = 1_700_000_000.0`
  is 2023-11-14, roughly 2.8 years before real current time — every entry these sites persist
  falls behind the back edge under a real-`now` default. Each site already has the controlled
  clock in scope (`match_time`, `CLOCK["t"]`), so the repair is to pass it as `now=`. The
  cycles that go through `poll_loop.run_once()` are already fine: the harness patches
  `poll_loop.now_s` to read `CLOCK`, so `refresh_calendar_registry()` receives the controlled
  clock and threads it down.
- `companion/test_config_page.py` — 2 direct call sites (around `:3599` and `:3628`) using
  2030-dated entries (`1893456000.0`, `1893484800.0`, `1893500000.0`), which fall past the 48h
  forward edge. Both checks are about the Settings page never surfacing airport codes, airline
  codes, or a derived flight count — retention is not their subject. Pass an explicit `now`
  placing those fixtures inside the window and leave the fixtures themselves as written.
- `server/test_calendar_rules.py` — the persist-path checks using
  `_entry("XX","AAA","ORY",1.0,2.0)`-style 1970-epoch sentinels (around `:449-455`,
  `:481-487`, `:501-504`, `:569`, `:717`). Their subjects are whole-file replacement,
  never-touching-colour_rules.json, the empty write, and the two cap warnings — all
  time-agnostic. Thread an explicit `now` bracketing each check's own sentinels. Leave the
  two stderr drop-count assertions alone; they must still pass, which is itself evidence that
  the decision in step 3 (window drops excluded from that warning) landed correctly.
  The matcher checks from `MATCH_NOW = 1789000000.0` onward (`:1290` and below) build
  in-memory registries and call `match_calendar_theme()` directly without persisting, so they
  need no change — but do not route them through a persisting path later, because
  `MATCH_NOW` is a fixed absolute date and would become wall-clock dependent.

Add no new checks in this task; Task 2 owns those. Repair only. If repairing a check requires
changing what it asserts rather than which clock it uses, stop and say so in the summary
rather than weakening it.

**Known environment caveat.** STATE.md records a pre-existing, already-accepted,
environment-specific macOS Pillow/FreeType `panel.bin` digest mismatch in
`server/test_poll_loop.py`. If that specific failure appears, confirm it is identical before
and after your change (stash, run, unstash, run) before treating it as pre-existing. Any
other failure in that harness is yours.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 server/test_calendar_rules.py; echo "calendar_rules harness exit=$?"</automated>
    <automated>server/.venv/bin/python3 server/test_poll_loop.py; echo "poll_loop harness exit=$?"</automated>
    <automated>server/.venv/bin/python3 companion/test_config_page.py; echo "config_page harness exit=$?"</automated>
    <automated>server/.venv/bin/ruff check .</automated>
    <automated>server/.venv/bin/python3 -c "import ast,sys; t=ast.parse(open('server/plane/calendar_rules.py').read()); n=sorted({(a.module or '').split('.')[0] or a.names[0].name.split('.')[0] for a in ast.walk(t) if isinstance(a,(ast.Import,ast.ImportFrom))} | {al.name.split('.')[0] for a in ast.walk(t) if isinstance(a,ast.Import) for al in a.names}); print(n); bad=[m for m in n if m in ('enrich','colour_rules','manual_resolutions','illustrations')]; sys.exit(1 if bad or 'time' not in n else 0)"</automated>
    <automated>git diff --quiet server/requirements.txt && echo "requirements.txt unchanged"</automated>
    <automated>server/.venv/bin/python3 - << 'PY'
# The security auditor's own reproduction, run against the patched module.
# Seeds an entry that ended ~10 days ago via a legitimate past write, then drives three
# consecutive FAILING refresh cycles and reads the RAW file back each time.
import json, os, sys, tempfile
sys.path.insert(0, os.path.abspath("."))
import server.plane.calendar_rules as cr

seed_now = 1_780_000_000.0
stale = {"airline_iata": "XX", "origin_iata": "AAA", "destination_iata": "ORY",
         "start_at": seed_now, "end_at": seed_now + 7200.0}
os.environ[cr.CALENDAR_URL_ENV_VAR] = "https://93.184.216.34/feed.ics"
with tempfile.TemporaryDirectory() as tmp:
    assert cr.write_calendar_registry(tmp, [stale], seed_now, "2026-01-01T00:00:00+00:00",
                                      now=seed_now), "seed write failed"
    raw = json.load(open(cr.calendar_rules_path(tmp)))
    assert len(raw["entries"]) == 1, "seed entry should be in-window at seed_now"
    later = seed_now + 10 * 86400.0
    for cycle in range(3):
        now = later + cycle * (cr.CALENDAR_FETCH_INTERVAL_S + 1.0)
        code, reg = cr.refresh_calendar_registry(tmp, now, transport=lambda url, timeout: None)
        raw = json.load(open(cr.calendar_rules_path(tmp)))
        assert raw["entries"] == [], "cycle %d: stale entry survives on disk: %r" % (cycle, raw["entries"])
        assert reg["entries"] == raw["entries"], "cycle %d: returned registry != on-disk" % cycle
        assert raw["last_attempt_at"] == now, "cycle %d: last_attempt_at did not move" % cycle
print("T-16-PRIV reproduction now trims on disk across 3 failing cycles: OK")
PY</automated>
  </verify>

  <done>
All three harnesses exit 0 at their existing `EXPECTED_CHECK_COUNT` (76 for
`test_calendar_rules.py` — Task 1 adds no checks). `ruff check .` is clean. The AST probe
prints an import set containing `time` and none of the four forbidden first-party modules.
`server/requirements.txt` is unchanged. The auditor's reproduction prints its OK line: the
entry that ended 10 days ago is absent from the raw file after every one of three
consecutive failing refresh cycles, and the returned registry matches the raw file each time.
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add the regression check the original goal verification missed, plus three anti-drift checks</name>

  <files>
    server/test_calendar_rules.py
  </files>

  <behavior>
    - Three consecutive FAILING refresh cycles trim a 10-day-stale entry from the RAW on-disk file, and the returned registry matches the raw file on every cycle
    - A hand-written file mixing one out-of-window and one in-window entry loads to the in-window entry only, and the read does not rewrite the file
    - A write containing a stale entry and a current entry puts only the current entry in the raw file
    - For any list and any `now`, the loader's entries are exactly `select_window_entries(list, now)`
  </behavior>

  <action>
Add four checks to `server/test_calendar_rules.py`, appended in the harness's existing
numbered-comment style, following the shape of the neighbouring refresh checks (around
`:1035-1265`) verbatim for environment and transport setup rather than inventing a new one —
in particular, `refresh_calendar_registry()` returns `FETCH_SKIPPED_UNCONFIGURED` and makes no
write unless `os.environ[cr.CALENDAR_URL_ENV_VAR]` is set to a URL that passes the module's
own safety gate, and every existing refresh check saves and restores the prior env value.
Every one of the four passes an explicit `now`; none may read the wall clock.

**Check A — the required regression check (this is the verification the original goal check
missed; it is the reason T-16-PRIV shipped).**

Drive a failing refresh across several consecutive cycles and assert the ON-DISK entries are
trimmed:
- Seed an entry that ended ~10 days ago the realistic way — a legitimate
  `write_calendar_registry(..., now=seed_now)` at a `seed_now` where the entry is genuinely
  in-window (this reproduces the real production sequence: one successful fetch, then a feed
  that breaks). Assert the seed landed, so the check cannot pass vacuously on an empty file.
- Run `refresh_calendar_registry()` with a transport returning `None` for 3 consecutive
  cycles, advancing `now` by more than `CALENDAR_FETCH_INTERVAL_S` each cycle so the throttle
  genuinely lets each attempt through rather than short-circuiting at
  `FETCH_SKIPPED_THROTTLED`. Assert each cycle's result code is `FETCH_FAILED` — a check that
  silently took the throttled path would otherwise prove nothing.
- Read the RAW file back with `json.load()` after each cycle. **Do not read it through
  `load_calendar_registry()`.** The loader now windows on read, so it would return a trimmed
  list even from an untrimmed file — masking exactly the on-disk state this check exists to
  observe. That masking is the specific blind spot that let the gap ship.
- Assert the stale entry is absent from the raw file; that `reg["entries"]` equals the raw
  file's entries on every cycle (D-04's second half); that `last_attempt_at` moved each cycle;
  and that `last_synced_at` did not move (a failing feed must not read as fresh).

**Check B — the loader applies the window on read.** Hand-write a raw JSON file with
`json.dump()` (bypassing the write path, which is the module's own modelled trust boundary
for a hand-edited file) holding one out-of-window entry and one in-window entry for a chosen
`now`. Assert `load_calendar_registry(tmp, now)` returns only the in-window entry, and that
the file's bytes are unchanged by the read — the loader must trim what it returns without
rewriting on read.

**Check C — the writer refuses to persist what the loader would drop.** Call
`write_calendar_registry()` with one stale and one current entry at a chosen `now`, then read
the RAW file and assert only the current entry is there. This is the extended form of that
function's own documented invariant, now covering the window and not just shape and the cap.

**Check D — the anti-drift guard (D-02).** For a mixed list spanning both edges and a chosen
`now`, assert the entries `load_calendar_registry()` returns are exactly equal to
`select_window_entries(list, now)`. This is a behavioural equivalence assertion, not a source
grep: it goes red the moment a second window implementation appears anywhere on the load or
write path and starts disagreeing with the sole implementation.

Then re-derive `EXPECTED_CHECK_COUNT` by RUNNING the harness and reading the reported total —
never by adding 4 to 76. Extend the existing header comment block above the constant with one
sentence naming this quick task and what its checks cover, matching the voice of the phase-16
entries already there.
  </action>

  <verify>
    <automated>server/.venv/bin/python3 server/test_calendar_rules.py; echo "exit=$?"</automated>
    <automated>server/.venv/bin/python3 -c "
import re
src = open('server/test_calendar_rules.py').read()
m = re.search(r'^EXPECTED_CHECK_COUNT = (\d+)', src, re.M)
assert m, 'EXPECTED_CHECK_COUNT not found'
assert int(m.group(1)) > 76, 'count was not raised above the pre-change 76'
print('EXPECTED_CHECK_COUNT =', m.group(1))
"</automated>
    <automated>scripts/run-all-tests.sh</automated>
    <automated>server/.venv/bin/ruff check .</automated>
  </verify>

  <done>
`server/test_calendar_rules.py` exits 0 with a re-derived `EXPECTED_CHECK_COUNT` above 76 and
`passed == total`. `scripts/run-all-tests.sh` prints `==> Result: PASS` across all 19
harnesses. `ruff check .` is clean. Check A fails if the module change is reverted — confirm
this by hand once (revert the `now=` threading in `refresh_calendar_registry()`'s failure
path, watch Check A go red, restore) so the check is proven non-vacuous rather than assumed
to be.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| `{state_dir}/calendar_rules.json` at rest → anyone with VPS access | The file holds a named person's near-term work schedule; group/world-readable at 0644 per UF-16-02 |
| hand-edited `{state_dir}/calendar_rules.json` → `load_calendar_registry()` | An operator-inspectable file becomes the candidate set every displayed flight is compared against |
| caller-supplied `now` → `select_window_entries()` → the persisted entry list | A single scalar now decides how much of the registry survives a write |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-16-PRIV | Information Disclosure | `refresh_calendar_registry()` failure path; `load_calendar_registry()` | medium | mitigate | The threat this plan closes. The window moves into `_rebuild_capped_entries()`, the one helper both the loader and the writer already route every entry list through (D-01), so a permanently failing feed can no longer leave the last successful window on disk indefinitely. Proven by Task 2's Check A reading the RAW file across three consecutive failing cycles. |
| T-Q-01 | Denial of Service / Tampering | the new `now` parameter on `load_calendar_registry()` / `write_calendar_registry()` | medium | mitigate | `select_window_entries()` returns `[]` for any `now` it cannot convert to a UTC datetime, so a `None`, `bool`, `NaN`, `inf`, or non-numeric `now` reaching the writer would silently ERASE the registry rather than trim it — turning a privacy fix into data loss. Task 1 step 2 adds a resolver that bool-rejects, finite-checks, and degrades to `time.time()`, reusing the exact discipline `_normalise_calendar_entry()` already applies to `start_at`/`end_at` and for the same documented reason. |
| T-Q-02 | Tampering (of test evidence) | the three harnesses' registry fixtures | medium | mitigate | Windowing against real current time makes any check with fixed absolute fixture timestamps wall-clock dependent — green today, red on some future date, with the failure looking like a regression in the module rather than in the fixture. Task 1 applies one rule instead of case-by-case patches: every check that persists or loads entries passes an explicit `now` it controls. Called out specifically for `MATCH_NOW = 1789000000.0`, a fixed absolute date that is safe only because its checks never persist. |
| T-Q-03 | Denial of Service | `_rebuild_capped_entries()`'s drop-count warning | low | mitigate | Folding routine window expiry into the malformed/cap warning would print on every read of a file older than a day, and `load_calendar_registry()` runs on every companion page render — flooding `journalctl -u skypane-companion` and reclassifying normal retention as a fault. Task 1 step 3 keeps the warning scoped to anomalies and documents why; the two existing stderr drop-count assertions staying green is the evidence it landed. |
| T-16-SC | Tampering | npm/pip/cargo installs | n/a | accept | Zero package installs. The only new import is stdlib `time`. Verified by the AST probe in Task 1's verify block plus `git diff --quiet server/requirements.txt`. Same rationale as ACC-16-01 in `16-SECURITY.md`; no legitimacy checkpoint is required because no package is added. |
</threat_model>

<verification>
1. `scripts/run-all-tests.sh` prints `==> Result: PASS` — 19/19 harnesses.
2. `server/.venv/bin/ruff check .` is clean.
3. `server/plane/calendar_rules.py`'s AST-derived import set gains exactly `time` and stays a leaf.
4. `git diff --quiet server/requirements.txt` — no dependency change.
5. `git diff --name-only` against the plan's start lists exactly the four files in `files_modified`
   (plus `.planning/` artifacts). In particular, zero files under `companion/static/`,
   `companion/pages/`, or `firmware/`.
6. The auditor's reproduction from Task 1's verify block prints its OK line.
</verification>

<success_criteria>
- T-16-PRIV's gap is closed on the path where it was open: an entry that ended 10 days ago is
  absent from the raw `calendar_rules.json` bytes after a single failing refresh cycle, and
  after three consecutive ones.
- The window has exactly one implementation (`select_window_entries()`) and exactly one
  enforcement point (`_rebuild_capped_entries()`), with a behavioural check that goes red if a
  second one ever appears.
- No harness check depends on the wall clock.
- `scripts/run-all-tests.sh` green at 19/19 and `ruff check .` clean.
</success_criteria>

<output>
Create `.planning/quick/260908-asr-enforce-calendar-retention-window-on-eve/260908-asr-SUMMARY.md` when done.

Record in it, beyond the standard template:
- The re-derived `EXPECTED_CHECK_COUNT` and the exact command whose output established it.
- The COMPLETE, empirically derived list of harness checks the module change broke, and how
  each was repaired — including any front not anticipated by Task 1's three known ones.
- The result of the Check A non-vacuity confirmation in Task 2's `<done>`.
- A note that `16-SECURITY.md`'s T-16-PRIV row and its "Open Threats" section still read
  `open` and should be reconciled to `closed` by a follow-up `/gsd-secure-phase 16` run — this
  plan does not edit that file, so the audit trail stays the auditor's own record.
</output>
