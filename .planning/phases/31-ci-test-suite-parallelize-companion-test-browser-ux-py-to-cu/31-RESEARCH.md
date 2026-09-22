# Phase 31: CI test suite — parallelize companion/test_browser_ux.py - Research

**Researched:** 2026-09-22
**Domain:** Python test-harness decomposition / CI wall-clock optimization (no new libraries, no application code change)
**Confidence:** HIGH (all claims below are read directly off the live file at the commit this research was run against, not from CONTEXT.md's summary of it — several CONTEXT.md figures turned out to be stale; see "Corrections to CONTEXT.md" below)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** CI "test" job averages ~5min40. `companion/test_browser_ux.py` alone takes 300-320s (300.9s, 318.7s, 314.4s, 303.4s, 314.2s across 5 runs) — ~88-90% of the job's total. All other harnesses finish in under 32s **combined**. `JOBS=4` on the CI runner already runs every harness concurrently, so the job's total time is bounded by this one file.
- **D-02:** The 300s+ is not explained by fixed sleeps (only 10.6s from `page.wait_for_timeout()`). The real cost is structural: 108 `page.goto()` calls and 184 browser/context/page creations, executed sequentially inside one `main()` sharing a single Playwright `browser` and a single `companion/app.py` subprocess `harness`, accumulating into one global `results` list gated by an `EXPECTED_CHECK_COUNT` invariant.
- **D-03:** `scripts/run_all_tests.py` already documents this file as "the slowest single file by construction" — a known, accepted tradeoff, not a bug. This phase is the first attempt to reduce it.
- **D-04:** Incremental approach — extract the 2-3 largest logical scenario groups (e.g. Vols/Flights, Compagnies/Airlines, Paramètres/Settings — exact grouping is Claude's Discretion) into independently-runnable files, **this phase only**. Do NOT attempt to fully decompose the 16,361-line file in one shot.
- **D-05:** Success gate for a follow-up phase — if this extraction measurably cuts the CI "test" job's wall time by **at least ~30-40%**, open a follow-up phase to finish the decomposition. Below that, stop here.
- **D-06:** No fixed target wall-clock time. "Materially faster than today" is the bar; stop at diminishing returns.
- **D-07:** Extracted files join the existing local worker pool — new entries in `scripts/run_all_tests.py`'s `HARNESSES` list (and `EXPECTED_SLOWEST` ordering). **No GitHub Actions workflow/YAML changes.**

### Claude's Discretion
- Exact scenario-group boundaries for the 2-3 extracted files — "needs the researcher/planner to actually read the file's `check()` call sites, not a decision made blind here." **This document does that reading; see "Scenario Group Map" below.**
- Whether each extracted file gets its own `companion/app.py` subprocess + Playwright `browser` instance (yes — pattern-consistent, confirmed below).
- Whether shared helpers (`_login`, `_wait_for_bar`, `seed_state_dir`, etc.) get factored into a shared module vs. duplicated — **this document found a concrete case (see "Helper Coupling" below) where factoring is not just tidiness but a correctness requirement**, because one helper (`_quiet_arc_minutes`) is called from a check that will stay in the original file AND from checks in a candidate extraction group.
- Each extracted file gets its own `EXPECTED_CHECK_COUNT` (confirmed convention, see Code Examples).
- `pyproject.toml`'s `parallel = true` and `omit` list already support new `companion/test_*.py` files with zero config changes — **confirmed true for files matching the `test_*.py` glob; flagged as a real edge case for a shared *helper* module that does NOT match that glob (see Pitfall 3).**

### Deferred Ideas (OUT OF SCOPE)
- Full decomposition of the remaining scenario groups beyond the 2-3 extracted here — deferred to a follow-up phase, conditional on D-05's measured-gain gate.
- A GitHub Actions matrix strategy (per-shard runners) — considered and rejected for this phase.
- The ~20s/run Playwright Chromium-download caching opportunity — not folded into this phase.
</user_constraints>

<phase_requirements>
## Phase Requirements

No requirement IDs are mapped to this phase (roadmap TBD). Scope is defined entirely by CONTEXT.md's D-01 through D-07 and by this research's scenario-group findings.
</phase_requirements>

## Corrections to CONTEXT.md (verify-against-code findings)

CONTEXT.md's own canonical-refs section states figures "measured live" during context-gathering. Re-reading the actual files at planning time surfaced two places where those figures are now stale — flagging per this project's own established norm (STATE.md repeatedly documents catching stale-vs-code claims; e.g. the `HARNESSES` list's own header comment: *"04-CONTEXT.md's D-07 list is 7 files and is known-stale — do NOT 'correct' this list back down to match it"*).

1. **`HARNESSES` currently has 22 entries, not 18.** CONTEXT.md's canonical-refs section says "`HARNESSES` list (18 entries today — D-04's extraction adds 2-3 more, going to 20-21)". `python3 -c "import ast; ..."` parsing the live `scripts/run_all_tests.py` AST counts 22 elements (14 `server/`, 1 `stub-server/`, 7 `companion/`). The file's own module docstring ("Runs all 18 harnesses…") is *also* stale — the file has drifted from its own docstring before, which is exactly the kind of self-inconsistency this repo's culture flags rather than trusts. **Planner should write "22 entries today, going to 24-25" in the plan, and should also fix the docstring's "18" while touching this file (small, in-scope, avoids leaving a third stale number).**
2. **"Every other `companion/test_*.py` harness already demonstrates the 'launch companion/app.py as its own subprocess on its own port' pattern"** (code_context, Reusable Assets) is not quite accurate as stated: `companion/test_companion_app.py`, `companion/test_config_page.py`, `companion/test_status_pages.py`, `companion/test_view_pages.py`, `companion/test_i18n.py`, and `companion/test_contrast_check.py` all use `Harness` (subprocess-on-free-port) but **none of them import Playwright or drive a real browser** — they compare rendered HTML strings. `companion/test_browser_ux.py`'s own module docstring says this explicitly: *"Every other harness in this repository compares rendered HTML strings… This file is the first harness in the project that drives a real Chromium tab."* So the **subprocess/port pattern** is shared and safe to copy; the **Playwright browser-launch-and-skip-gate pattern** has exactly one precedent in the whole repo — `test_browser_ux.py` itself — and any extracted file must copy *that* file's own skip-gate code (see Code Examples), not some other sibling's.

Neither correction changes D-01 through D-07; both are precision fixes the planner needs to write an accurate plan.

## Summary

`companion/test_browser_ux.py` is not internally organized by page (as CONTEXT.md's discretion note guessed — "flights, airlines, settings/config, health, calendar, theme, uploads, a11y"). Reading all 96 `check()` call sites and their nearest preceding `page.goto()` shows the real shape: a ~3,660-line shared preamble (constants + ~40 helper functions, lines 1-3660, before `main()` even starts) followed by 96 scenario checks, of which **34 are Display-page checks and 7 are Device-page checks, heavily interleaved with each other and with 10 checks that are inherently cross-page** (a handful of checks deliberately visit both `/display` and `/device` in one check body, e.g. the single-affordance audit at line 15700 and the "ONE probe renders BOTH settings pages" check at line 15541). This settings mega-cluster spans roughly lines 4350-15825 — about 70% of the file — and is genuinely not cleanly splittable into 2-3 pieces in one phase, which is exactly what D-04's incremental-not-full-decomposition decision anticipated.

Three groups sit *outside* that entangled mega-cluster with clean, mostly-single-page boundaries:

1. **Health SVG-drawing checks** (battery ring, battery chart, day band, regularity grid — lines 9411-10882, 9 checks, ~1,472 lines) — the cleanest boundary found: two of its nine checks already spin up their **own isolated `Harness()` instance** (`band_harness`, `grid_harness`) rather than reusing the shared one, meaning the original authors already recognized this cluster needed isolation.
2. **Quiet-hours dial + wake-interval slider checks** (lines 11516-13379, 9 checks, ~1,864 lines) — the single largest fully-contiguous block outside the mega-cluster, one widget family, one (fixable) outbound coupling to a helper also used by a check that stays behind (see Helper Coupling).
3. **Flights checks** (two clusters — lines 3689-3959 and 8598-9092, 8 checks total, ~700 lines combined) — smallest of the three but zero coupling found to any other group; the safest, lowest-risk extraction if the planner wants a guaranteed-clean third file.

**Primary recommendation:** Extract group 1 (Health SVG) and group 2 (Quiet-hours/wake-interval) as the two mandatory extractions — they are the largest contiguous, most self-contained candidates and together cover 18 of 96 checks (~19% by count, ~26% by check-body line count, likely higher by wall-time share since both groups run `_in_both_themes()` loops that double page-loads per check, a cost `.goto()`/line-count alone underweights). Add Flights as a third extraction only if D-05's 30-40% wall-time bar is not comfortably cleared by the first two alone — it is the cheapest additional win but the smallest one.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Which scenario groups get extracted into which files | Test harness (Python process) | — | Pure file-organization decision; no runtime app tier is involved |
| Shared assertion/measurement helpers (`_login`, `_assert_hit_target`, `_set_ui_theme`, `_quiet_arc_minutes`, …) | Test harness — new shared helper module | Original `test_browser_ux.py` (remaining checks) + new extracted files | Both the file left behind and the new files call into the same functions; must live somewhere both can import without duplication |
| Per-file subprocess + browser lifecycle (`Harness()`, `sync_playwright()`) | Test harness (one Python process per extracted file) | — | Already the established one-process-per-file pattern every harness in this repo uses |
| Worker scheduling / concurrency | `scripts/run_all_tests.py` (`ThreadPoolExecutor`, `JOBS` env var) | — | Owns which harnesses run and how many run at once; needs zero new mechanism, only new list entries (D-07) |
| CI trigger / step sequencing | `.github/workflows/ci.yml` | — | Calls `./scripts/run-all-tests.sh` unconditionally; D-07 requires this tier stays untouched |
| Coverage measurement scoping | `pyproject.toml` `[tool.coverage.run]` | — | `source`/`omit` glob decides what counts; confirmed to already cover new `test_*.py` files (see Pitfall 3 for the one helper-module edge case) |

## Scenario Group Map

Built by reading all 96 `check(...)` call sites (`grep -n '^\s*check(' companion/test_browser_ux.py`, cross-referenced with the nearest preceding `.goto()` call and with manual reads of each candidate range). Two indentation depths exist: 93 checks at the main `main()` body level, and 3 at one level deeper inside the `artwork_harness` sub-block (93 + 3 = 96 = `EXPECTED_CHECK_COUNT`).

| Group | Line range | Checks | `.goto()` | `new_context()`/`new_page()` | `_in_both_themes()` calls | Own isolated `Harness()`? | Coupling out |
|-------|-----------|--------|-----------|-------------------------------|----------------------------|---------------------------|---------------|
| Flights (early cluster) | 3689-3959 | 3 (row expand/collapse, icon hit-targets, filter count) | 3 | 3/3 | 0 | No (shared `harness`) | None found |
| Airlines | 3976-4105 | 2 (illustration grid @390px, filter count) | 2 | 1/1 | 0 | No | None found — but only 2 checks, too small to extract alone |
| Health metadata/filter | 4137-4352 | 3 | 3 | 2/2 | 0 | No | None found |
| Flights (late cluster) | 8598-9092 | 5 (detection landing, refresh doesn't unfold/undo filter, collapsed-row focus, phone-card tap) | 5 | 4/4 | 0 | No | None found |
| Health freshness/ticker | 7269-7825 | ~6 | 5 | 4/4 | 0 | No | None found, but interleaved page-visibility checks span `/` and `/health` in the same check body in places — verify individually before moving |
| **Health SVG drawings** | **9411-10882** | **9** (battery ring theme tokens, battery ring viewBox, battery ring cost-at-360px, battery chart tokens, battery chart cost-at-360px, day band tokens, day band cost-at-360px, regularity grid tokens, regularity grid cost-at-360px) | 11 | 9/9 | 3 | **Yes — 2 of 9 already use `band_harness`/`grid_harness`** | None found |
| Home refresh/paint/leave-guard | 6153-8492 (excl. health/flights ranges above) | ~21 | 23 | 18/18 | 0 | No | Entangled with dirty-bar/leave-guard machinery shared with the Display mega-cluster — do not extract this phase |
| **Quiet-hours dial + wake-interval slider** | **11516-13379** | **9** | 6 | 7/7 | 3 | No (shared `harness`) | **One: `_quiet_arc_minutes()` (defined line 3213, module-level) is also called from a Display mega-cluster check at lines 15087/15116/15195 — must move to a shared helper module, not into this group's new file alone** |
| Theme/arrivals/calendar carousel + full-settings audits | 13540-15825 | 16 | 14 | 12/12 | 1 | No | Heaviest entanglement in the file: shares `_STRIP_PROBE`/`_CAROUSEL_INSTANCE_PROBE` closures, and at least 2 checks (lines 15541, 15700) deliberately drive **both** `/display` and `/device` in one check body — not a single-page group, do not attempt this phase |
| Login | 5653-5935 | 3 | 5 | 4/4 | 0 | No, but one check uses its own `lockout_harness` (line 5806) | None found; too small to extract alone |
| **Artwork/upload** | 15840-16357 | 3 (own indentation level) | 4 | 2/2 | 2 | **Yes — its own `artwork_harness`, its own `art_dir`** | None found — the single most self-contained block in the file, but only 3 checks (small win) |

Numbers above are a proxy (goto/context-creation counts), not a stopwatch measurement — see Open Questions for how the planner should validate the real wall-time split before committing to the final 2-3 groups.

### Why the mega-cluster (lines ~4350-15825, minus the three clean groups above) is not this phase's target

- It is ~70% of the file's check bodies.
- 34 of 96 checks visit `/display`, 7 visit `/device`, and at least a handful of checks (e.g. lines 15541 "ONE probe renders BOTH settings pages", 15700 "exactly ONE submit-shaped control on the whole settings page") are **written to span both pages in a single check** — these cannot be assigned to a single-page file without either duplicating the check or leaving it in the original file, which is exactly the kind of one-shot-full-decomposition risk D-04 rejected.
- Shared local closures (`_STRIP_PROBE`, `_CAROUSEL_INSTANCE_PROBE`, `_SETTLE_CAROUSEL`, `_TOGGLE_OWN_DISCLOSURE`, defined inline right before the theme-carousel checks) are reused across multiple checks inside this one cluster, meaning even sub-dividing it further inside this phase would require the same helper-extraction work at a much larger scale than the budget for "2-3 groups this phase" implies.

**Recommendation: leave the entire mega-cluster in `companion/test_browser_ux.py` this phase.** It is the natural target for the D-05 follow-up phase, once this phase's measured wall-time gain validates the approach.

## Recommended Extraction (ranked)

1. **`companion/test_browser_ux_health_drawings.py`** (or similar name) — the Health SVG-drawing block, lines 9411-10882, 9 checks. **Rank 1: cleanest boundary in the file** (2 of 9 checks already self-isolate via their own `Harness()`), and the `_in_both_themes()` triple-loop plus per-viewport re-measurement likely makes its wall-time share larger than its line-count share.
2. **`companion/test_browser_ux_quiet_wake.py`** (or similar name) — the quiet-hours dial + wake-interval slider block, lines 11516-13379, 9 checks. **Rank 2: largest fully-contiguous block outside the mega-cluster.** Requires moving (or duplicating into a shared module) `_quiet_arc_minutes()` and its module-level sibling constants/helpers (`_QUIET_ARC_SELECTOR`, `_fraction_to_minute`, `_quiet_caption_minutes`, `_quiet_caption_shape`, `_quiet_duration_span_text`, `_expected_quiet_duration_text`, `_fraction_pair_minutes`) because one of them (`_quiet_arc_minutes`) is called from a check at lines 15087/15116/15195 that must stay in the original file (it's part of the un-splittable mega-cluster's dirty-bar audit).
3. **`companion/test_browser_ux_flights.py`** (optional third file) — both Flights clusters combined, lines 3689-3959 + 8598-9092, 8 checks. **Rank 3: smallest, but zero coupling found anywhere** — the lowest-risk of the three if the planner wants insurance toward the D-05 gate, or can be deferred if groups 1+2 alone measure past 30-40%.

Do not extract Airlines (2 checks) or Login (3 checks) alone this phase — below the "largest logical scenario groups" bar D-04 sets, and folding either into one of the three files above would blur that file's single-responsibility naming.

## Helper Coupling

Read the six helpers CONTEXT.md named plus the ones the chosen groups actually call:

| Helper | Defined at (module level unless noted) | Signature/inputs | Cross-group usage found | Safe to import as-is? |
|--------|------------------------------------------|-------------------|---------------------------|------------------------|
| `_login(page, base_url)` | line 1134 | pure — takes `page`/`base_url`, no module state | Used by nearly every group | Yes |
| `_wait_for_bar(page, timeout=5000)` / `_wait_for_bar_hidden` | 1252 / 1266 | pure — `page` only | Used across Display/Device checks | Yes |
| `seed_state_dir(state_dir, base_ts=SEED_BASE_TS)` | 1044 | pure — writes fixture data via `server/history_db.py`, `server/device_config.py`, `server/plane/manual_resolutions.py`, `server/plane/colour_rules.py`, `server.poll_loop._save_to_gallery()` | Called once per `Harness()` instance (main `harness`, `band_harness`, `grid_harness`, `lockout_harness`, `artwork_harness` all call it) | Yes — already designed to be called once per isolated harness |
| `_set_ui_theme(page, theme)` / `_in_both_themes(page)` | 1392 / 2782 | pure — `page` only, reads/writes `data-ui-theme` | Used by Health SVG group, Quiet-hours/wake group, and the mega-cluster | Yes |
| `_assert_hit_target(page, selector, where, minimum=MIN_HIT_TARGET_PX)` | 2570 | pure — depends on `_hit_area()` (2358) and `MIN_HIT_TARGET_PX` constant | Used everywhere | Yes |
| `_quiet_arc_minutes(page, where, selector=_QUIET_ARC_SELECTOR, radius=None)` | 3228 | depends on module-level `_QUIET_ARC_SELECTOR` (3132) and `config_page.QUIET_DIAL_RADIUS` | **Called from the Quiet-hours/wake group (lines 11881, 12062) AND from the mega-cluster's dirty-bar audit check (lines 15087, 15116, 15195)** | **Only if moved to (or duplicated in) a shared module — it cannot live solely inside the new Quiet-hours file, since a check that stays in the original file also needs it** |
| `_quiet_caption_minutes`, `_quiet_caption_shape`, `_quiet_duration_span_text`, `_expected_quiet_duration_text`, `_fraction_to_minute`, `_fraction_pair_minutes` | 3132-3612 | pure, quiet-dial-specific geometry decoders | `_quiet_caption_minutes` also called at line 12147 (inside the Quiet-hours group) and nowhere outside it; the others (`_quiet_caption_shape`, `_quiet_duration_span_text`, `_expected_quiet_duration_text`, `_fraction_to_minute`, `_fraction_pair_minutes`) are called only from within `_quiet_arc_minutes`/`_quiet_caption_minutes` themselves (lines 3132-3612) — i.e. only from each other | Move all of them together with `_quiet_arc_minutes` into the shared module, since they form one small dependency cluster |
| `_quiet_hours_on_disk()` | 11469 (defined **inside** `main()`, not module level) | closure over `harness` | Used only within the Quiet-hours/wake group | Safe — stays local to the new Quiet-hours file, redefine as its own closure over that file's own `harness` |

**Net recommendation:** factor the entire ~3,660-line preamble (everything before `def main():` at line 3635 — constants, `Harness`-adjacent helpers, hit-target/paint/theme measurement helpers, and the quiet-dial decoder cluster) into one new shared module, e.g. `companion/test_browser_ux_helpers.py`. This is simpler and lower-risk than trying to sub-divide the preamble per extracted group: several helpers (e.g. `_assert_hit_target`, `_in_both_themes`, `_set_ui_theme`) are used by essentially every group including the ones staying behind, and the one concrete cross-group case found (`_quiet_arc_minutes`) proves the preamble cannot be cleanly partitioned along the same lines as the checks. A helper file that's slightly bigger than any single consumer needs is normal and cheap (pure function/constant definitions have no import-time cost worth avoiding); duplicating ~3,660 lines three times would not be.

**Naming/coverage-omit consequence of this choice — see Pitfall 3.**

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Free port allocation for a new `Harness()` per extracted file | A manual port-registry or fixed-port-per-file scheme | `Harness._pick_free_port()` (binds `("127.0.0.1", 0)`, OS assigns an ephemeral free port) — already collision-free by construction | Every extracted file just instantiates its own `Harness()`; the OS guarantees no two concurrently-running harnesses can be handed the same port, confirmed by reading `companion/test_companion_app.py` lines 1216-1294 |
| Skipping cleanly when Playwright/Chromium isn't installed | A new try/except shape, an env-var gate, or a pytest marker | Copy `test_browser_ux.py`'s own two-gate `main()` preamble verbatim (import guard + a throwaway `p.chromium.launch()`/`probe.close()` probe) into each new file | This is the *only* precedent for a Playwright skip-gate in this repo; no sibling harness has one to imitate, since only `test_browser_ux.py` uses Playwright at all (see "Corrections to CONTEXT.md" #2) |
| Coordinating check-result counting per new file | A shared results-aggregation module | The existing per-file `results = []` / `check(name, fn)` closure / `EXPECTED_CHECK_COUNT` gate at the bottom of `main()` — copy this pattern into each new file, one counter per file | Confirmed universal convention across every harness in the repo (04-CONTEXT.md D-07); `scripts/run_all_tests.py` has zero awareness of what's inside a harness beyond its exit code, so there is no cross-file coordination to build |
| Deciding which harnesses run first | A priority queue or new scheduling primitive | Add the new file names near the top of `EXPECTED_SLOWEST` in `scripts/run_all_tests.py` — `_submission_order()` already handles ordering | The mechanism already exists and is exactly what D-07 says to reuse |

**Key insight:** every piece of plumbing this phase needs (port allocation, subprocess lifecycle, skip gate, check accumulator, worker scheduling, coverage parallel-mode) already exists in this repo and has exactly one place it's implemented. The phase's actual work is *moving code between files*, not building new test infrastructure.

## Runtime State Inventory

Not applicable in the sense this section usually means (renamed identifiers leaking into databases/live-service-config/OS registrations). This phase does not rename anything user-facing or change any on-disk data shape — it moves Python function/check definitions between files. Explicitly checked and confirmed "none" for each category:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — `seed_state_dir()`'s fixture writers (`server/history_db.py`, `server/device_config.py`, etc.) are untouched; each extracted file calls the same seeding function against its own fresh `tempfile.mkdtemp()` dir, exactly like every other harness does today | None |
| Live service config | None — no n8n/Datadog/Tailscale/Cloudflare-style out-of-git config exists in this project's test infra | None |
| OS-registered state | None — no Task Scheduler/pm2/launchd/systemd entries reference this file by name | None |
| Secrets/env vars | None — `auth.PASSWORD_ENV_VAR`/`TEST_PASSWORD` are set per-subprocess by `Harness.start()`, unaffected by which file calls it | None |
| Build artifacts | None — no compiled/installed artifact embeds `test_browser_ux.py`'s name; `pyproject.toml`'s `omit` list references it only by the `companion/test_*.py` glob, which any new file matching that glob inherits automatically | None (see Pitfall 3 for the one helper-module naming nuance) |

## Common Pitfalls

### Pitfall 1: `EXPECTED_CHECK_COUNT` drift across multiple files after extraction
**What goes wrong:** The original file's `EXPECTED_CHECK_COUNT = 96` must drop by exactly the number of checks moved out (18 if extracting Health SVG + Quiet-hours/wake, 9+9=18 → new total 78; 26 if Flights is also extracted → 70), and each new file needs its own freshly-derived count.
**Why it happens:** This file's own 45+ years of incrementing `EXPECTED_CHECK_COUNT` (visible in the file's own history comments, e.g. "94 + 2 = 96, re-derived by RUNNING (96/96)") shows the project's own convention: never hand-compute this number, always run the file and read the real pass/fail count off stdout.
**How to avoid:** After moving each group, run the new file standalone and read its own printed `browser-ux: N/N checks pass` line (or equivalent) to set that file's `EXPECTED_CHECK_COUNT`; do the same for the reduced original file. Never subtract by hand from a line-range count — this file's own comments repeatedly warn against exactly that (e.g. "recomputed directly against the real on-disk check(...) call count at execution time... not trusted from"— this phrase appears at nearly every `EXPECTED_CHECK_COUNT` bump in the file, 20+ times).
**Warning signs:** A file whose printed `M/N` doesn't match its own `EXPECTED_CHECK_COUNT` fails loudly by design (`return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1`) — this is a hard CI failure, not silent drift, so it will be caught, but only if the executor actually runs each new file before committing rather than hand-arithmetic-ing the split.

### Pitfall 2: Cross-check state ordering inside the shared `Harness()` state directory
**What goes wrong:** All checks in the *original* file share one `Harness()` (one temp state dir, one `companion/app.py` subprocess) across all 96 checks, executed in file order. Some checks deliberately mutate persisted config (theme, quiet hours, wake interval) and read it back. Splitting a scenario group into its own file gives it its **own** fresh `Harness()` + fresh `seed_state_dir()` call — which is what every other harness in this repo already does, and is almost certainly *more* correct (each group no longer depends on file-order side effects from unrelated earlier checks) — but this needs empirical verification, not just a read-through, because this file is 16,361 lines and no static read can guarantee no check silently depends on state left behind by an earlier check in a *different* group.
**Why it happens:** A single shared `harness.tmpdir` across 96 sequential checks means "starts from the seed fixture" is only true for check #1 — checks 2-96 start from whatever check 1..N-1 left behind, unless each check explicitly restores what it changed (several checks visibly do this — e.g. the pattern `before = X; ...; if after != before: return False, "..."` seen at line ~13376 in the quiet-hours block — but this is not proven universal by a static read).
**How to avoid:** For each candidate extraction group, run it **standalone** (new file, own fresh `Harness()`) and diff its pass/fail output against the same checks' output when run as part of the full original file. If both give identical PASS/FAIL results, the group had no hidden order dependency on anything outside itself. This is the single most important empirical validation step for this phase, and belongs in the plan as an explicit verification task per extracted file, not an assumption.
**Warning signs:** A check that passes inside the full file but fails when run alone in its new file (or vice versa) is exposing a real order dependency that must be fixed (either by seeding the specific state the check needs itself, or by widening the extraction boundary to include whatever produces that state).

### Pitfall 3: Shared helper module naming vs. `pyproject.toml`'s coverage `omit` glob
**What goes wrong:** CONTEXT.md's discretion section states "the `omit` list already excludes `companion/app.py` and the `test_*.py` files themselves… New extracted files are `companion/test_*.py` and are auto-omitted by the existing glob; no coverage config change expected." **This is true only for files matching the `companion/test_*.py` glob.** The shared helper module this phase needs (see Helper Coupling) is not itself a harness — it has no `main()`, no `EXPECTED_CHECK_COUNT`, and per this file's own convention, `run_all_tests.py`/`HARNESSES` only ever executes files explicitly listed there. But the *coverage* `omit` list is a separate, independent glob match against `pyproject.toml`, and a helper module that doesn't match `companion/test_*.py` would be **measured** by coverage — likely at a low, misleading percentage (pure decoder/assertion helpers, many branches only exercised by specific viewport/theme combinations), dragging the project's coverage threshold down for a reason unrelated to a real regression (the exact class of problem `pyproject.toml`'s own comments call out for `stub-server/byos_server.py` and `companion/app.py`, "M5").
**Why it happens:** The omit list is glob-based (`companion/test_*.py`), and the natural, self-documenting name for a *helper* module ("`browser_ux_shared.py`" or similar) would not match that glob.
**How to avoid:** Two options, either is workable — pick one explicitly in the plan rather than leaving it implicit:
  1. Name the shared module with a `test_` prefix anyway (e.g. `companion/test_browser_ux_helpers.py`), so it's auto-covered by the existing `omit` glob with **zero** `pyproject.toml` changes — at the cost of a `test_`-prefixed file with no `main()`/`EXPECTED_CHECK_COUNT`, which needs a one-line module docstring note ("shared helpers, not a harness — do not add to HARNESSES") so a future reader isn't confused by the naming convention mismatch.
  2. Name it without the `test_` prefix (clearer as "not a harness") and add **one** explicit new line to `pyproject.toml`'s `omit` list — a real, minimal, in-scope config change that contradicts CONTEXT.md's "no coverage config change expected" only in this narrow, previously-unconsidered case.
**Warning signs:** A coverage report showing the new helper module at an anomalously low percentage, or the coverage threshold (enforced by `scripts/run_all_tests.py` via `coverage report`) failing after this phase's changes with no corresponding drop in real test coverage — that's this exact issue.

### Pitfall 4: `_in_both_themes()`/multi-viewport checks under-weighted by a `.goto()`-count proxy
**What goes wrong:** The scenario-group map above uses `.goto()` and `new_context()`/`new_page()` counts as a cost proxy (matching D-02's own methodology: 108 `.goto()`, 184 context/page creations across the whole file). But `_in_both_themes()` internally calls `_set_ui_theme()` twice per invocation *without* a new `.goto()` or `new_context()` each time (it re-paints the *same* already-loaded page in two themes) — so a check using `_in_both_themes()` three times looks "cheap" by the goto/context proxy while actually doing 6 extra JS-evaluate round-trips plus CSS custom-property reads. Both of this phase's two primary recommended groups (Health SVG, Quiet-hours/wake) use `_in_both_themes()` 3 times each; the mega-cluster and most other groups use it far less. **This means the proxy in the scenario-group table likely *undercounts* how much wall-time these two groups actually contribute**, which is favorable to the recommendation (they're probably worth even more than the raw numbers suggest) but should not be treated as a substitute for an actual timing measurement.
**Why it happens:** Real per-check cost in a Playwright harness is dominated by page loads and real-browser layout/paint work, which a static call-count grep can only approximate.
**How to avoid:** After implementing the split, the plan's own verification step should re-run `gh run view` on the resulting CI runs (mirroring D-01's own measurement methodology) rather than trusting this research's static proxy for the final go/no-go against D-05's 30-40% bar.

### Pitfall 5: CI runner core count vs. local dev machine core count
**What goes wrong:** `nproc`/`os.cpu_count()` on the GitHub-hosted `ubuntu-latest` runner used by `.github/workflows/ci.yml` is 4 (matches D-01's confirmed "JOBS=4" printed summary). A developer testing this split locally on a machine with more cores (this worktree's host reports 10) will see `JOBS=10` locally, meaning **local wall-time improvements will not be representative of CI's improvement** — with more workers, more of the previously-idle 21-harness pool time is already hidden behind the one slow file locally, understating how much the split actually helps on the 4-core CI runner where contention is tighter.
**How to avoid:** When validating this phase's wall-time gain, either run with `JOBS=4` explicitly set locally (`JOBS=4 ./scripts/run-all-tests.sh`) to mirror CI, or rely on the actual CI run numbers (`gh run view`) rather than local timings, per D-05's own established measurement method.

## Code Examples

### Skip-gate + harness + browser pattern to copy verbatim into each new file
```python
# Source: companion/test_browser_ux.py (this file, lines 3635-3670) — the
# only Playwright-driving harness in this repo; copy its two-gate skip
# pattern and per-file check()/EXPECTED_CHECK_COUNT convention exactly.

def main():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(
            "SKIP companion/test_browser_ux_<group>.py — playwright not installed "
            "(dev-only dependency; run "
            "`pip install -r server/requirements-dev.txt` to enable this harness)")
        return 0

    try:
        with sync_playwright() as p:
            probe = p.chromium.launch()
            probe.close()
    except Exception as exc:
        print(
            "SKIP companion/test_browser_ux_<group>.py — Chromium launch failed (%r); "
            "run `python -m playwright install chromium`" % (exc,))
        return 0

    results = []

    def check(name, fn):
        try:
            ok, reason = fn()
        except Exception as exc:
            ok, reason = False, "exception: %r" % (exc,)
        results.append((name, ok))
        print("PASS %s" % name if ok else "FAIL %s - %s" % (name, reason))

    harness = Harness()          # from companion.test_companion_app import Harness
    seed_state_dir(harness.tmpdir)   # imported from the new shared helper module
    harness.start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            try:
                # ... this group's check() call sites, moved verbatim ...
                pass
            finally:
                browser.close()
    finally:
        harness.stop()
        harness.cleanup()

    total = len(results)
    passed = sum(1 for _, ok in results if ok)
    print("<group>: %d/%d checks pass" % (passed, total))
    return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### `scripts/run_all_tests.py` wiring (exact entries to add)
```python
# Source: scripts/run_all_tests.py, live file, lines 62-113

HARNESSES = [
    # ... existing 22 entries unchanged ...
    "companion/test_browser_ux.py",            # reduced, stays
    "companion/test_browser_ux_health_drawings.py",   # NEW
    "companion/test_browser_ux_quiet_wake.py",         # NEW
    # "companion/test_browser_ux_flights.py",          # NEW, optional 3rd
]

EXPECTED_SLOWEST = (
    "companion/test_browser_ux.py",
    "companion/test_browser_ux_health_drawings.py",   # NEW — place near top,
    "companion/test_browser_ux_quiet_wake.py",         # longest-first, since
    # these will be among the slowest remaining harnesses (each still
    # launches its own Chromium + companion/app.py subprocess)
    "server/test_render.py",
    "server/test_poll_loop.py",
    "companion/test_companion_app.py",
    "stub-server/test_poll_cycle.py",
    "server/test_panel_preview.py",
    "companion/test_status_pages.py",
    "server/test_pipeline_e2e.py",
)
```
No other change to `scripts/run_all_tests.py`, `scripts/run-all-tests.sh`, or `.github/workflows/ci.yml` is needed — `_run_one()`'s subprocess/timeout/coverage-parallel plumbing is already generic over any harness path in `HARNESSES`.

### Port allocation (already collision-free, no new code needed)
```python
# Source: companion/test_companion_app.py, lines 1229-1235
@staticmethod
def _pick_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))   # OS assigns an ephemeral free port
        return s.getsockname()[1]
    finally:
        s.close()
```
Each extracted file's own `Harness()` call gets its own port this way; running 3-4 `Harness()`-owning harnesses concurrently under `JOBS=4` cannot collide, since the OS never double-issues an in-use ephemeral port to a second `bind(0)` call in the same window.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | The recommended file names (`test_browser_ux_health_drawings.py`, `test_browser_ux_quiet_wake.py`, `test_browser_ux_flights.py`) are suggestions, not verified against any project naming-convention document; the planner should confirm against `.claude/skills/*` or existing naming patterns before finalizing | Recommended Extraction, Code Examples | Low — purely cosmetic, easy to rename during planning/execution with no functional impact |
| A2 | The wall-time share attributed to `_in_both_themes()`-heavy checks (Pitfall 4) is a reasoned inference from the pattern (extra JS round-trips, no extra `.goto()`), not a measured number | Pitfall 4, Recommended Extraction | Medium — if wrong, the ranking of Health SVG / Quiet-hours above Flights by "time-savings potential" could be less true than stated; the plan should still validate via actual `gh run view` timing per D-05's own method rather than trust this ranking blindly |
| A3 | No check outside the two recommended groups reads or depends on state left behind by a check *inside* them (Pitfall 2) — verified by grep for the specific named helpers/constants used inside each group, not by exhaustively tracing every one of the file's other 87 checks | Common Pitfalls (Pitfall 2), Helper Coupling | High if wrong — a hidden order dependency would surface as a newly-flaky or newly-failing check after extraction; mitigated by the explicit "run standalone and diff" verification step this research recommends as a required plan task |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **Does extracting groups 1+2 (Health SVG + Quiet-hours/wake, 18 of 96 checks) clear D-05's 30-40% wall-time bar on its own, or is the optional third group (Flights) needed?**
   - What we know: these two groups are ~26% of check-body line count and use proportionally more `_in_both_themes()`-driven page-repaints than the file average, suggesting their wall-time share likely exceeds their line-count share.
   - What's unclear: the exact wall-time split can only be measured by actually running the split in CI (or locally with `JOBS=4`) and reading `gh run view`, mirroring D-01's own methodology — this research cannot produce that number without executing code, which is outside a research pass's remit.
   - Recommendation: the plan should make the third group (Flights) a conditional/optional task, gated on a mid-implementation timing check after groups 1+2 are extracted and running in CI — extract Flights only if the first two don't already comfortably clear the D-05 bar.

2. **Does any check in the 87 checks NOT being extracted this phase quietly depend on state seeded/mutated by a check inside groups 1 or 2, beyond the one `_quiet_arc_minutes()` case already found?**
   - What we know: the one confirmed cross-group coupling (`_quiet_arc_minutes`, called from a mega-cluster dirty-bar-audit check at lines 15087/15116/15195) is resolved by moving it to the shared helper module rather than duplicating or leaving it stranded.
   - What's unclear: whether any *other* helper or persisted-state assumption crosses the group boundary undetected by a static grep of the specific helper names used inside the two recommended groups.
   - Recommendation: the plan's verification step must run each extracted file standalone (fresh seed, fresh harness) and diff its PASS/FAIL output against the same checks' output inside the original full file, per Pitfall 2 — this is the authoritative check, not a second round of static reading.

## Environment Availability

| Dependency | Required By | Available (this worktree) | Version | Fallback |
|------------|--------------|------------------------------|---------|----------|
| Python 3 | Running/validating the split locally | ✓ | 3.14.7 (system) | Project's own `server/.venv` (not yet created in this worktree) targets 3.12 per CI; create via `python3 -m venv server/.venv` before local validation |
| Playwright + Chromium | Running `companion/test_browser_ux*.py` locally | Not confirmed installed in this worktree (`server/.venv` absent) | — | Harness's own skip-gate makes this a soft dependency — a plan/executor without it installed still gets a clean SKIP rather than a failure, but cannot locally validate the split's correctness or timing without it |
| GitHub Actions `ubuntu-latest` runner | CI timing measurement (D-01/D-05 methodology) | N/A locally | 4 vCPUs (confirmed via D-01's own "JOBS=4" printed summary) | Local timing on a machine with a different core count is not representative — see Pitfall 5 |

**Missing dependencies with no fallback:** None — every dependency here has a working fallback or soft-skip already built into the existing harness convention.

**Missing dependencies with fallback:** Playwright/Chromium not confirmed installed locally in this worktree; local validation of the split should first run `server/.venv/bin/pip install -r server/requirements-dev.txt && server/.venv/bin/python -m playwright install chromium` (mirrors `.github/workflows/ci.yml`'s own setup step) before attempting to diff standalone-vs-full-file check output per Pitfall 2's verification requirement.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Hand-rolled `check(name, fn)` / `EXPECTED_CHECK_COUNT` / `main()` convention (no pytest anywhere in this repo) |
| Config file | None — orchestration lives in `scripts/run_all_tests.py`; per-file behavior lives in each file's own `main()` |
| Quick run command | `server/.venv/bin/python3 companion/test_browser_ux_<group>.py` (run one extracted file standalone) |
| Full suite command | `./scripts/run-all-tests.sh` (all `HARNESSES`, `JOBS`-parallel, with coverage) |

### Phase Requirements → Test Map
No REQ-IDs are mapped to this phase (see Phase Requirements above). This phase's own correctness bar is defined by D-04/D-05, restated as verifiable checks:

| Behavior | Test Type | Automated Command | File Exists? |
|----------|-----------|---------------------|--------------|
| Each new extracted file runs standalone, skips cleanly without Playwright/Chromium, and its own `EXPECTED_CHECK_COUNT` matches its own printed pass count | smoke | `server/.venv/bin/python3 companion/test_browser_ux_<group>.py` | ❌ — file created by this phase |
| The reduced `companion/test_browser_ux.py`'s `EXPECTED_CHECK_COUNT` matches its new (smaller) real check count | smoke | `server/.venv/bin/python3 companion/test_browser_ux.py` | ✅ — existing file, edited |
| No check that passed inside the original monolith now fails when run inside its new extracted file (Pitfall 2) | integration/diff | Run original file (pre-split, on a clean checkout) capturing PASS/FAIL per check name; run each new file; diff the two outputs for the checks that moved | ❌ — a one-off validation script/manual diff, not a persisted test file |
| Full suite (`./scripts/run-all-tests.sh`) still passes end-to-end with the new `HARNESSES`/`EXPECTED_SLOWEST` entries, and the coverage threshold still passes | integration | `JOBS=4 ./scripts/run-all-tests.sh` | ✅ — existing orchestration, edited (new list entries only) |
| CI "test" job wall-clock time, measured the same way D-01 measured it (`gh run view` averaged over several runs), drops by ≥30-40% (D-05 gate) | manual/measured, post-merge | `gh run view <run-id>` on the resulting CI runs | N/A — CI measurement, not a repo file |

### Sampling Rate
- **Per task commit:** Run the specific new/edited file(s) standalone (`server/.venv/bin/python3 companion/test_browser_ux_<group>.py`).
- **Per wave merge:** `JOBS=4 ./scripts/run-all-tests.sh` (full suite, matching CI's worker count).
- **Phase gate:** Full suite green locally, then at least one real CI run's `gh run view` timing compared against the D-01 baseline before declaring the D-05 gate met or missed.

### Wave 0 Gaps
- No test-framework infrastructure gap — the convention this phase must follow already exists and is fully specified in Code Examples above. The only new "test infrastructure" this phase creates is the new harness files themselves, which are simultaneously the phase's deliverable and its own test coverage.
- One genuine gap: **no existing tooling in this repo automates the "diff standalone output against full-file output for the moved checks" verification** (Pitfall 2 / Validation Architecture row 3) — this is a one-off manual/scripted comparison the plan should schedule as an explicit task, not something `scripts/run_all_tests.py` does for you.

## Security Domain

`security_enforcement` is enabled in `.planning/config.json`, but this phase changes **zero** application code, endpoints, auth, or input-handling — it only reorganizes test files that already navigate exclusively to `Harness.base_url()` (a `127.0.0.1:<ephemeral-port>` URL the test process itself launched — this file's own module docstring states this as a hard security constraint enforced by its own code: *"No external URL is ever constructed or navigated to anywhere in this file"*). No new attack surface is introduced.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|----------------|---------|---------------------|
| V2 Authentication | No | Unchanged — `_login()`/`TEST_PASSWORD` reused verbatim from `companion.test_companion_app` |
| V3 Session Management | No | Unchanged |
| V4 Access Control | No | Unchanged |
| V5 Input Validation | No | No new inputs; test fixtures are the same deterministic `seed_state_dir()` data |
| V6 Cryptography | No | Unchanged |

### Known Threat Patterns for this stack
None applicable — this phase's only "input" is which Python file a given block of test code lives in.

## Sources

### Primary (HIGH confidence — read directly from the live repository)
- `companion/test_browser_ux.py` (16,361 lines) — full structural read via targeted `grep`/`sed` passes: module docstring (security constraint statement, skip-gate rationale), all 96 `check()` call sites and their names, all `.goto()` call sites, all `Harness()` instantiations (including `band_harness`, `grid_harness`, `lockout_harness`, `artwork_harness`), helper function definitions (`_login`, `_wait_for_bar`/`_wait_for_bar_hidden`, `seed_state_dir`, `_set_ui_theme`, `_in_both_themes`, `_assert_hit_target`, the quiet-dial decoder cluster), `EXPECTED_CHECK_COUNT` history comments, `main()`'s skip-gate and results-accumulator code
- `scripts/run_all_tests.py` (300 lines, read in full) — `HARNESSES` (live AST count: 22), `EXPECTED_SLOWEST`/`_submission_order()`, `_run_one()`'s subprocess/timeout/coverage-parallel invocation contract, `JOBS`/`HARNESS_TIMEOUT_S` env vars
- `companion/test_companion_app.py` (`Harness` class, lines 1216-1294) — port allocation (`_pick_free_port`), subprocess lifecycle (`start`/`stop`/`cleanup`), confirmed no Playwright import anywhere in this file
- `pyproject.toml` `[tool.coverage.run]` (lines 46-96, read in full) — `parallel = true`, `source = ["server", "stub-server", "companion"]`, `omit` list contents verified verbatim (glob-based, `companion/test_*.py` present; no entry for a non-`test_`-prefixed helper module)
- `.github/workflows/ci.yml` (read in full) — `runs-on: ubuntu-latest`, no `JOBS` env override (confirms 4-core default matches D-01's measured "JOBS=4"), Playwright Chromium install step, unconditional `./scripts/run-all-tests.sh` call
- `.planning/phases/31-.../31-CONTEXT.md` — locked decisions D-01 through D-07, discretion items, canonical refs
- `.planning/config.json` — `workflow.nyquist_validation: true`, `workflow.security_enforcement: true` (confirms both optional RESEARCH.md sections above are required, not skippable)

### Secondary (MEDIUM confidence)
- `.planning/STATE.md`/`.planning/REQUIREMENTS.md` grep hits for `test_browser_ux.py` — corroborate the file's growth history (`EXPECTED_CHECK_COUNT` progression 65→81→88→94→96 across phases 22-28) and this project's own stated norm of re-deriving check counts by running rather than trusting a document (repeated phrasing across multiple phase entries)

### Tertiary (LOW confidence)
- None — no web search was needed for this phase; it is entirely internal-repository research with no external library/API decisions.

## Metadata

**Confidence breakdown:**
- Scenario group map / line ranges / check counts: HIGH — derived from direct `grep`/`sed` reads of the live file, cross-checked against `EXPECTED_CHECK_COUNT`'s own 96 total; the check→route attribution used a nearest-preceding-`.goto()` heuristic which is imprecise at the margins (a handful of checks were mis-attributed to "/" when they were actually on a different route reached via a helper) — the three *recommended* groups (Health SVG, Quiet-hours/wake, Flights) were each individually verified by direct line reads, not just the heuristic, so confidence on those three specifically is HIGH; confidence on the exact boundary/count of groups NOT recommended (e.g. "Home refresh/paint" at ~21 checks) is MEDIUM, since those were not individually re-verified by direct read
- Helper coupling (`_quiet_arc_minutes` cross-group case): HIGH — confirmed via `grep -n` for every named helper's call sites across the whole file, not sampled
- `scripts/run_all_tests.py` wiring / coverage omit / port allocation: HIGH — read in full, code confirmed to behave as CONTEXT.md describes (with the two corrections noted)
- Actual wall-time savings from the recommended split: LOW/unmeasured — this is explicitly an open question (see Open Questions #1) requiring execution, not something a research pass can determine

**Research date:** 2026-09-22
**Valid until:** Until `companion/test_browser_ux.py`'s content changes again (it has changed in nearly every recent phase per its own `EXPECTED_CHECK_COUNT` history — treat line numbers in this document as approximate if any other phase lands on this file before Phase 31 is planned/executed; re-grep for `check(` line numbers before writing the plan if more than a few days have passed)
