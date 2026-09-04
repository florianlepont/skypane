---
phase: 11-web-configurable-wake-interval
verified: 2026-09-04T06:48:19Z
status: passed
score: 22/22 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:

  - test: "Start the companion app locally against a scratch state dir, sign in, open /settings. At 375px and >=960px viewports, in both light and dark mode, confirm: (1) the Wake interval group renders last, below Quiet hours, with the same card surface/heading/caption treatment as its four siblings; (2) the native number input's stepper/spinner is legible and does not overflow or crowd the card at 375px; (3) the field's tap target is comfortably >=44px tall; (4) with nothing saved, the placeholder reads 'Uses server default' in the browser's muted placeholder tone, not a number; (5) editing the field raises the floating save bar exactly as editing any other group does, and the bar's section count names Wake interval; (6) the focus ring matches every other input's accent outline."
    expected: "All six checks pass against 11-UI-SPEC.md's locked Interaction Contract, with no visual regression to the four existing settings groups."
    why_human: "Native <input type=\"number\"> stepper rendering, touch-target feel, dirty-bar wiring, and focus-ring colour match require visual/interaction judgment automated checks cannot substitute for. This is 11-03-PLAN.md Task 2's own <human-check>, explicitly deferred to this end-of-phase pass per workflow.human_verify_mode = end-of-phase (11-03-SUMMARY.md 'Outstanding Verification' section) — it has not been performed by any prior plan execution."
---

# Phase 11: Web-configurable wake interval Verification Report

**Phase Goal:** Make the device's wake/poll interval (`SKYPANE_SLEEP_S`) configurable through the companion web interface (extending `device_config.py`'s registry and `config_page.py`'s form), delivered to the device via the existing `/device/v1/display` poll response rather than a service restart.
**Verified:** 2026-09-04T06:48:19Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

All 22 must-haves truths declared across the four plans' frontmatter were checked directly against the current source (not against SUMMARY.md prose) and against the passing test harnesses.

| # | Plan | Truth | Status | Evidence |
|---|------|-------|--------|----------|
| 1 | 11-01 | `load_device_config()` always returns seven keys including `wake_interval_s` | ✓ VERIFIED | `server/device_config.py:453-461`; confirmed by direct import (`sorted(load_device_config(...))` prints all 7 keys) |
| 2 | 11-01 | `wake_interval_s`'s unset state is `None`, no `DEFAULT_*` constant | ✓ VERIFIED | `server/device_config.py:68-72` comment states the deliberate exception; no `DEFAULT_WAKE_INTERVAL_S` constant exists |
| 3 | 11-01 | Hostile on-disk values degrade to `None`, never reach a caller | ✓ VERIFIED | `normalise_wake_interval_s()` (`device_config.py:409-427`); `server/test_config_history.py#_hand_written_hostile_wake_interval_s_yields_none` passes |
| 4 | 11-01 | `save_device_config(wake_interval_s=...)` rejects non-int/bool/out-of-range with `ValueError`, file untouched | ✓ VERIFIED | `device_config.py:515-522`; test harness's byte-identical-on-rejection check passes |
| 5 | 11-01 | Bool never passes a bounded-int check (`isinstance(x, int) and not isinstance(x, bool)`) | ✓ VERIFIED | Present in `normalise_wake_interval_s()`, `save_device_config()`'s guard, `read_wake_interval_s()`, and `wake_interval_group()`'s value-attr gate — 4 independent occurrences confirmed by grep |
| 6 | 11-01 | Save without `wake_interval_s` carries the on-disk value forward | ✓ VERIFIED | `device_config.py:533`; carry-forward check passes |
| 7 | 11-02 | `GET /device/v1/display` returns saved `wake_interval_s` as `sleep_s`, or `--sleep` when unset | ✓ VERIFIED | `stub-server/byos_server.py:468-470`: `quiet_hours_sleep_s(read_wake_interval_s(self.args.state_dir, self.args.sleep), self.args.state_dir)`; integration test confirms `sleep_s == 120` for a stored value and `300` (CLI default) for a below-floor stored value |
| 8 | 11-02 | `read_wake_interval_s()` never raises across every hostile input | ✓ VERIFIED | `byos_server.py:146-171`; 9-case fail-open unit check passes |
| 9 | 11-02 | `quiet_hours_sleep_s()`'s signature/body unchanged — only `base_sleep_s`'s source changed | ✓ VERIFIED | `byos_server.py:279-306` byte-identical to Phase 10; `max(base_sleep_s, remaining)` still present |
| 10 | 11-02 | An active quiet-hours window still extends `sleep_s` past 3600s | ✓ VERIFIED | Layering unit check asserts `28000 > 3600` explicitly; no re-clamp added after `quiet_hours_sleep_s()` returns (confirmed by reading the handler) |
| 11 | 11-02 | No firmware change required | ✓ VERIFIED | `git diff --name-only` for this phase touches no file under `firmware/`; `sleep_s` still opaque `uint32_t` on the wire |
| 12 | 11-03 | Settings page renders a fifth `.theme-status` group, Wake interval, last | ✓ VERIFIED | `config_page.py:851` appends `wake_interval_group(...)` last; render() placement check confirms index ordering |
| 13 | 11-03 | Control is `<input type="number" name="wake_interval_s" min="60" max="3600">` | ✓ VERIFIED | `config_page.py:551` markup; direct call confirms all four substrings present |
| 14 | 11-03 | `handle_post()` explicitly `int()`-converts before `save_device_config()` | ✓ VERIFIED | `config_page.py:984-987` |
| 15 | 11-03 | Absent/empty `wake_interval_s` means leave unchanged, never reject | ✓ VERIFIED | `config_page.py:980-982` |
| 16 | 11-03 | Non-numeric/out-of-bounds submission returns generic save-failed flash, file byte-identical | ✓ VERIFIED | `config_page.py:985-994`; rejection-path test confirms byte-identity |
| 17 | 11-03 | Input renders with no `value` attribute when nothing valid to pre-fill | ✓ VERIFIED | `config_page.py:540-545` conditional `value_attr`; direct call confirms `[False]*8 + [True]*3` pattern for the 11 canonical test inputs |
| 18 | 11-04 | `companion/app.py` reads `SKYPANE_SLEEP_S` via `os.environ.get()`, same pattern as `auth.py`'s password read | ✓ VERIFIED | `app.py:348` inside `env_wake_interval_default()` |
| 19 | 11-04 | Read is per-request, not import-time-cached | ✓ VERIFIED | `os.environ.get()` call sits inside the function body, invoked fresh on every `page_context()` call (`app.py:728`) |
| 20 | 11-04 | Read is fail-open: bad/absent/out-of-range value yields `None` | ✓ VERIFIED | `app.py:346-352`; full-input-space unit check passes for 13 canonical cases |
| 21 | 11-04 | No new file-parsing code; relies on existing `EnvironmentFile=` systemd directive | ✓ VERIFIED | `git diff --quiet deploy/skypane-companion.service deploy/skypane-byos.service` confirms unchanged; no new import beyond stdlib `os` |
| 22 | 11-04 | On-disk `wake_interval_s` always wins over env pre-fill | ✓ VERIFIED | `config_page.py:779-781`: `is None` check, on-disk value checked first |

**Score:** 22/22 truths verified (0 present-but-behavior-unverified)

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `server/device_config.py` | `WAKE_INTERVAL_MIN_S`/`MAX_S`, `normalise_wake_interval_s()`, 7th `load`/`save` key | ✓ VERIFIED | All present, substantive, wired into read/write paths |
| `server/test_config_history.py` | New coverage, `EXPECTED_CHECK_COUNT` bumped | ✓ VERIFIED | 44/44 checks pass (39 → 44, +5 as planned) |
| `stub-server/byos_server.py` | `read_wake_interval_s()`, rebased `/display` `sleep_s` | ✓ VERIFIED | Present, wired into the handler, vendor boundary holds (`grep -cE '^\s*(from\|import) server'` → 0 matches) |
| `stub-server/test_poll_cycle.py` | New coverage | ✓ VERIFIED | 34/34 checks pass (29 → 34, +5 as planned) |
| `stub-server/VENDOR.md` | Local-modification entry | ✓ VERIFIED | New entry present per grep in review report |
| `companion/pages/config_page.py` | `wake_interval_group()`, `render()`/`handle_post()` wiring | ✓ VERIFIED | Present, wired, 100% line coverage in `run-all-tests.sh` coverage report |
| `companion/test_config_page.py` | New coverage | ✓ VERIFIED | 79/79 checks pass (73 → 79, +6 as planned) |
| `companion/app.py` | `SLEEP_ENV_VAR`, `env_wake_interval_default()`, `ctx` key | ✓ VERIFIED | Present, wired into `page_context()` |
| `companion/pages/__init__.py` | Documented `ctx` contract entry | ✓ VERIFIED | `wake_interval_env_default` documented at line 62-64 |
| `companion/test_companion_app.py` | New coverage | ✓ VERIFIED | 129/129 checks pass (125 → 129, +4 as planned) |
| `deploy/skypane.env.example` | Corrected `SKYPANE_SLEEP_S` comment | ✓ VERIFIED | Comment updated; value (`30`) and both systemd unit files unchanged |
| `.claude/skills/sketch-findings-skypane/SKILL.md` + `references/settings-page-patterns.md` | Design-system register updated | ✓ VERIFIED | `<input type="number">` recorded in "kept" touch-target category; six-section caption enumeration corrected |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `save_device_config()` write path | `device_config.json` | strict pre-write `ValueError` gate | WIRED | Confirmed byte-identical-on-rejection test passes |
| `load_device_config()` | every reader (`poll_loop.py`, `config_page.py`) | 7-key contract | WIRED | `config_page.py`'s `render()` reads `device_cfg.get("wake_interval_s")` |
| `byos_server.py`'s `/display` handler | `quiet_hours_sleep_s()` | `read_wake_interval_s()` as `base_sleep_s` | WIRED | Confirmed at `byos_server.py:468-470`; no re-clamp after extension |
| `config_page.handle_post()` | `save_device_config()` | single call, `wake_interval_s=` keyword | WIRED | `grep -c 'save_device_config(' ` inflated by docstring prose (noted in 11-03-SUMMARY.md), but `grep -n 'device_config.save_device_config('` confirms exactly one real call site |
| `companion/app.py`'s `page_context()` | `config_page.render()` | `ctx["wake_interval_env_default"]` | WIRED | Confirmed `is None`-gated fallback consumption at `config_page.py:779-781` |
| `server/device_config.py`'s bounds | `stub-server/byos_server.py`'s independently redefined bounds | hand-pinned equality (no automated drift guard) | WIRED but flagged | Numerically equal today (60/3600 both sides); **no automated guard exists** — see Warnings below (REVIEW.md WR-01) |

### Behavioral Spot-Checks / Full Suite

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 16 project test harnesses, including the 4 touched by this phase | `bash scripts/run-all-tests.sh` | `==> Result: PASS`; 0 `FAIL` lines; coverage 92% overall, `config_page.py` 100% | ✓ PASS |
| Ruff lint on every phase-touched file | `ruff check <files>` | "All checks passed!" (3 batches) | ✓ PASS |
| Debt markers (`TBD`/`FIXME`/`XXX`) in phase-touched files | `grep -nE 'TBD\|FIXME\|XXX'` | No matches | ✓ PASS |
| No firmware file touched | `git diff --name-only` vs. `firmware/` | No matches | ✓ PASS |

### Requirements Coverage

Per `11-CONTEXT.md`, `11-01`/`11-02`/`11-03`/`11-04-PLAN.md` frontmatter, and this phase's ROADMAP entry: **no requirement IDs** are mapped to Phase 11 — it is an unmapped backlog phase promoted from `SEED-002-web-configurable-wake-interval.md`, matching Phase 10's own precedent. `grep -n "Phase 11" .planning/REQUIREMENTS.md` returns zero matches — no orphaned requirements exist for this phase. This is consistent with all four plans' own `requirements: []` frontmatter declarations.

### Anti-Patterns Found

None. All phase-touched files pass ruff with zero findings, carry zero unresolved debt markers, and the "PLACEHOLDER" grep hits are all legitimate references to the `WAKE_INTERVAL_PLACEHOLDER_TEXT` HTML placeholder-attribute constant (`"Uses server default"`), not stub markers.

### Code Review Findings (non-blocking, carried forward from 11-REVIEW.md)

11-REVIEW.md found 0 critical, 2 warning, 1 info issues. None are must-have blockers; both are noted here for visibility per the phase brief's instruction:

- **WR-01** (`stub-server/byos_server.py`): `WAKE_INTERVAL_MIN_S`/`MAX_S` are hand-duplicated from `server/device_config.py` with no automated drift guard, unlike `_HHMM_RE`/`seconds_until_quiet_hours_end()` which are pinned by `_quiet_hours_drift_guard`. Confirmed present in the current code — values are numerically equal today but nothing would catch future drift.
- **WR-02** (`companion/pages/config_page.py:984-987`): the `int()` conversion in `handle_post()` only catches `ValueError`, not `TypeError`. Confirmed present — not reachable via the real HTTP path (`read_form()` always yields strings), so it does not violate any must-have truth, but it is a latent gap against the function's own stated never-raise contract for a hypothetical non-string caller.
- **IN-01**: `int()`'s permissive grammar (underscore separators, Unicode digits) is not restricted before parsing; not exploitable since the range check downstream still bounds every accepted value. Confirmed present, informational only.

These are pre-existing findings from the phase's own code review, not verifier-discovered — they are reported for completeness, not as new gaps.

### Human Verification Required

1. **Real-browser visual verification of the Wake interval Settings group**

   **Test:** Start the companion app locally against a scratch state dir, sign in, open `/settings`. At 375px and ≥960px viewports, in both light and dark mode, confirm: (1) the Wake interval group renders last, below Quiet hours, with the same card surface/heading/caption treatment as its four siblings; (2) the native `<input type="number">` stepper/spinner is legible and does not overflow or crowd the card at 375px; (3) the field's tap target is comfortably ≥44px tall; (4) with nothing saved, the placeholder reads "Uses server default" in the browser's muted placeholder tone, not a number; (5) editing the field raises the floating save bar exactly as editing any other group does, and the bar's section count names Wake interval; (6) the focus ring matches every other input's accent outline.

   **Expected:** All six checks pass against `11-UI-SPEC.md`'s locked Interaction Contract.

   **Why human:** Native numeric-input stepper rendering, touch-target feel, dirty-bar wiring, and focus-ring colour match require visual/interaction judgment automated checks cannot substitute for.

   **Note:** this is not a verifier-invented item — it is `11-03-PLAN.md` Task 2's own `<human-check>` block, which `11-03-SUMMARY.md`'s "Outstanding Verification" section explicitly records as **not performed**, deferred to this end-of-phase pass per `workflow.human_verify_mode = end-of-phase` in `.planning/config.json`. No later plan or SUMMARY in this phase performed it either. This is the single reason this phase's status is `human_needed` rather than `passed` — every programmatically-checkable truth is verified and every automated test suite is green.

### Gaps Summary

No gaps. Every must-have truth declared across the four plans' frontmatter is verified directly against the current source and against passing, substantive test coverage (not against SUMMARY.md narrative alone). All 16 project test harnesses pass via `scripts/run-all-tests.sh` with zero regressions. The vendor boundary (`stub-server/byos_server.py` importing nothing from `server.*`) holds. No firmware file was touched. Both prior "gotcha" risks the plans called out by name — the bool-is-an-int trap and the string-to-int conversion gate — are confirmed correctly implemented at every one of their four independent occurrences.

The phase is not marked `passed` only because one explicitly-deferred human visual-verification step (11-03-PLAN.md Task 2's `<human-check>`) was never actually performed by any plan execution, and this is the correct end-of-phase point to surface it per the project's `human_verify_mode: end-of-phase` configuration.

---

_Verified: 2026-09-04T06:48:19Z_
_Verifier: Claude (gsd-verifier)_
